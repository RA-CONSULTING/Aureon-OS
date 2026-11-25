"""Stage pretraining data for Aureon's from-scratch model.

Pulls parquet shards straight from the Hub rather than re-encoding text, so
560 GB is written once instead of twice. Only the login node has outbound
network, so this always runs there.

    fetch_corpus.py --list
    fetch_corpus.py --source fineweb-edu --limit-gb 300 --out /projects/u6vs/pretrain/data
    fetch_corpus.py --source fineweb     --limit-gb 300 --out /projects/u6vs/pretrain/data

    fetch_corpus.py --verify --source code --max-files 1 --out /projects/u6vs/pretrain/data
    fetch_corpus.py --audit --source fineweb-edu --out /projects/u6vs/pretrain/data

    # Bounded repair, not an implicit bulk download:
    fetch_corpus.py --source fineweb-edu --max-files 1 --out /projects/u6vs/pretrain/data

Downloads use the Hub library for revision-pinned metadata and LFS SHA256 content
digests. ``--verify``/``--audit`` download nothing; audit does not change the live
acquisition manifest. Existing corrupt files are quarantined as ``.invalid``.
HF_TOKEN or the protected Hub token store supplies optional authentication; tokens
never enter manifests. Run inside the Isambard NGC container so pyarrow is present.

Downloads use curl rather than hf_hub_download on purpose: on 2026-10-26 a hub
download stalled with a zero-byte `.incomplete` file and an open TLS socket
that delivered nothing, and it sat there forever instead of retrying. curl
gives `-C -` resume, `--retry-all-errors`, and a speed floor that aborts a
dead stream after 60 s so the retry can actually fire.
"""

from __future__ import annotations

import argparse
import contextlib
import gzip
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time
from typing import Any

if sys.platform != "win32":
    import fcntl
from urllib.parse import quote

if sys.platform != "win32":
    import fcntl

SOURCES: dict[str, dict[str, Any]] = {
    "fineweb-edu": {
        "repo": "HuggingFaceFW/fineweb-edu",
        "prefer": "sample/100BT",
        "note": "educational web text, ~100B tokens in this config",
    },
    "fineweb": {
        "repo": "HuggingFaceFW/fineweb",
        "prefer": "sample/100BT",
        "note": "raw web text, the second half of the token budget",
    },
    "code": {
        "repo": "codeparrot/codeparrot-clean",
        "prefer": None,
        "exts": [".json.gz"],
        "note": "ungated Python; gzip JSONL, not parquet",
    },
    "code-python-edu": {
        "repo": "HuggingFaceTB/smollm-corpus",
        "prefer": "python-edu/",
        "note": "educational Python subset, ungated",
    },
    "code-stack-dedup": {
        "repo": "bigcode/the-stack-dedup",
        "prefer": "/python/",
        "note": "gated: HEAD 401 without HF_TOKEN; 28.6 GB Python subset",
    },
}

CHARS_PER_TOKEN = 4.0  # measured on the Aureon holdout with our own tokenizer


def api():
    from huggingface_hub import HfApi

    # Library-managed auth supports HF_TOKEN and the protected Hub token store.
    # No token is placed on a command line, in a URL, or in an acquisition manifest.
    return HfApi(token=os.environ.get("HF_TOKEN") or None)


def shard_list(hf: Any, repo: str, prefer: str | None,
               exts: tuple[str, ...] = (".parquet",)) -> list[tuple[str, int]]:
    _revision, records = shard_records(hf, repo, prefer, exts)
    return [(str(record["file"]), int(record["bytes"])) for record in records]


def shard_records(hf: Any, repo: str, prefer: str | None,
                  exts: tuple[str, ...] = (".parquet",),
                  revision: str = "main") -> tuple[str, list[dict]]:
    """Return one immutable dataset revision and validated shard descriptors."""
    info = hf.repo_info(
        repo, repo_type="dataset", files_metadata=True, revision=revision,
    )
    resolved = str(getattr(info, "sha", "") or "")
    if not re.fullmatch(r"[0-9a-f]{40}", resolved):
        raise ValueError(f"{repo}: Hub did not resolve a full commit SHA")
    files: list[dict[str, Any]] = []
    for sibling in info.siblings:
        name = str(sibling.rfilename)
        if not name.endswith(exts):
            continue
        if prefer and prefer not in name:
            continue
        size = int(getattr(sibling, "size", 0) or 0)
        if size <= 0:
            raise ValueError(f"{repo}/{name}: positive shard size required")
        lfs = getattr(sibling, "lfs", None)
        sha256 = str(getattr(lfs, "sha256", "") or "")
        if sha256 and not re.fullmatch(r"[0-9a-f]{64}", sha256):
            raise ValueError(f"{repo}/{name}: malformed Hub content digest")
        files.append({
            "repo": repo,
            "file": name,
            "bytes": size,
            "sha256": sha256 or None,
            # This identifies the repository object; it is NOT a content hash.
            "blob_id": str(getattr(sibling, "blob_id", "") or "") or None,
        })
    files.sort(key=lambda item: str(item["file"]))
    if prefer and not files:
        raise ValueError(f"{repo}: no {', '.join(exts)} shards matched {prefer!r}")
    return resolved, files


def write_json_atomic(path: pathlib.Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    try:
        temp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


@contextlib.contextmanager
def shard_lock(path: pathlib.Path):
    """One process may mutate a shard; other workers fail rather than interleave."""
    lock = path.with_name(f"{path.name}.lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open("a+b") as stream:
        try:
            if os.name == "nt":
                import msvcrt

                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)  # type: ignore[name-defined]
        except (OSError, BlockingIOError) as exc:
            raise RuntimeError(f"shard_locked:{path.name}") from exc
        try:
            yield
        finally:
            if os.name == "nt":
                import msvcrt

                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)  # type: ignore[name-defined]


def show_sizes(spec: dict, revision: str = "main") -> None:
    repo = spec["repo"]
    exts = tuple(spec.get("exts", (".parquet",)))
    try:
        resolved, records = shard_records(api(), repo, spec.get("prefer"), exts, revision)
        files = [(item["file"], item["bytes"]) for item in records]
    except Exception as exc:
        print(f"{repo}: unavailable ({type(exc).__name__}: {exc})")
        return
    print(f"{repo}: pinned revision {resolved}")
    total = sum(size for _, size in files)
    print(
        f"{repo}: {len(files)} shards, {total / 1e9:.1f} GB "
        f"(~{total / CHARS_PER_TOKEN / 1e9:.1f}B tokens)"
    )
    if files:
        print(f"    first: {files[0][0]}  ({files[0][1] / 1e9:.2f} GB)")


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def valid_container(path: pathlib.Path) -> tuple[bool, str]:
    """Validate container structure without parsing every training document."""
    try:
        if path.name.endswith(".parquet"):
            import pyarrow.parquet as pq

            with pq.ParquetFile(path) as parquet:
                names = set(parquet.schema_arrow.names)
                if not names & {"text", "content", "raw_content"}:
                    return False, "missing_text_column"
                # Read every row-group's text column. Metadata alone would not
                # detect the truncated page streams found in the original corpus.
                for index in range(parquet.num_row_groups):
                    parquet.read_row_group(index, columns=[next(iter(names & {
                        "text", "content", "raw_content",
                    }))])
        elif path.name.endswith((".json.gz", ".jsonl.gz")):
            with gzip.open(path, "rt", encoding="utf-8", errors="replace") as stream:
                for line_number, line in enumerate(stream, 1):
                    if not line.strip():
                        continue
                    record = json.loads(line)
                    if not isinstance(record, dict) or not any(
                        record.get(key) for key in ("text", "content", "raw_content")
                    ):
                        return False, f"missing_text_at_line:{line_number}"
        else:
            return False, "unsupported_container"
    except Exception as exc:  # noqa: BLE001 - exact type retained in local audit
        return False, f"{type(exc).__name__}: {exc}"[:1000]
    return True, "ok"


def verify_shard(path: pathlib.Path, record: dict, *, checksum: bool) -> tuple[bool, str]:
    if not path.is_file():
        return False, "missing"
    actual = path.stat().st_size
    if actual != record["bytes"]:
        return False, f"size_mismatch:{actual}!={record['bytes']}"
    if checksum and record.get("sha256") and sha256_file(path) != record["sha256"]:
        return False, "sha256_mismatch"
    return valid_container(path)


def curl_shard(
    repo: str, name: str, out: pathlib.Path, expect: int,
    *, revision: str = "main", sha256: str | None = None,
) -> tuple[bool, float, str | None]:
    """Download one shard, resuming where a previous run left off.

    The final string is the verified content digest on success, otherwise the
    bounded failure reason. Rate is measured against actual bytes downloaded.
    """
    if pathlib.PurePosixPath(name).is_absolute() or ".." in pathlib.PurePosixPath(name).parts:
        return False, 0.0, "unsafe_shard_path: name must stay within the source directory"
    dest = out / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    with shard_lock(dest):
        record = {"file": name, "bytes": expect, "sha256": sha256}
        if dest.exists():
            ok, reason = verify_shard(dest, record, checksum=True)
            if ok:
                # A complete valid file never needs another HTTP request.
                return True, 0.0, sha256
            # Preserve corrupt evidence outside the tokenizer's ingestion path.
            quarantine = dest.with_name(dest.name + ".invalid")
            dest.replace(quarantine)
            print(f"    quarantined invalid existing shard as {quarantine.name}: {reason}")
        part = dest.with_name(dest.name + ".part")
        if part.exists() and part.stat().st_size >= expect:
            # A completed-size .part must be verified, never extended forever.
            ok, reason = verify_shard(part, record, checksum=True)
            if ok:
                part.replace(dest)
                return True, 0.0, sha256
            part.unlink()
        url = (
            f"https://huggingface.co/datasets/{repo}/resolve/"
            f"{quote(revision, safe='')}/{quote(name, safe='/')}"
        )
        cmd = [
            "curl", "-fL", "-C", "-",
            "--retry", "8", "--retry-delay", "5", "--retry-all-errors",
            # Abort a stream delivering under 1 KB/s for 60 s: a dead socket
            # otherwise hangs forever, which is what the hub client did.
            "--speed-limit", "1024", "--speed-time", "60",
            "--connect-timeout", "30",
            "-o", str(part), url,
        ]
        token = os.environ.get("HF_TOKEN")
        if token:
            cmd[-1:-1] = ["-H", f"Authorization: Bearer {token}"]

        t0 = time.time()
        proc = subprocess.run(cmd, capture_output=True, text=True)
        elapsed = max(time.time() - t0, 1e-6)
        if proc.returncode != 0:
            print(f"    curl exit {proc.returncode}: {proc.stderr.strip()[:200]}", flush=True)
            return False, 0.0, f"curl_exit:{proc.returncode}"
        ok, reason = verify_shard(part, record, checksum=True)
        if not ok:
            print(f"    validation failed: {reason}", flush=True)
            return False, 0.0, reason
        actual_sha256 = sha256_file(part)
        part.replace(dest)
        return True, expect / elapsed, actual_sha256

    # Write to .part and rename only on a verified size. Otherwise an
    # interrupted transfer sits at the final path and the size check above
    # treats it as a finished shard on the next run.
    part = dest.with_name(dest.name + ".part")
    if part.exists() and expect and part.stat().st_size >= expect:
        # A .part at or beyond the shard size can never become correct by
        # appending, and -C - keeps growing it, so the size check fails on
        # every pass: 011_00005 sat at 2350273296 of 2147259152 bytes and
        # failed each attempt. Drop it and start this shard clean.
        part.unlink()
    url = f"https://huggingface.co/datasets/{repo}/resolve/main/{name}"
    cmd = [
        "curl", "-fL", "-C", "-",
        "--retry", "8", "--retry-delay", "5", "--retry-all-errors",
        # Abort a stream delivering under 1 KB/s for 60 s: a dead socket
        # otherwise hangs forever, which is what the hub client did.
        "--speed-limit", "1024", "--speed-time", "60",
        "--connect-timeout", "30",
        "-o", str(part), url,
    ]
    token = os.environ.get("HF_TOKEN")
    if token:
        cmd[-1:-1] = ["-H", f"Authorization: Bearer {token}"]

    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = max(time.time() - t0, 1e-6)
    if proc.returncode != 0:
        print(f"    curl exit {proc.returncode}: {proc.stderr.strip()[:200]}", flush=True)
        return False, 0.0

    got = part.stat().st_size if part.exists() else 0
    if expect and got != expect:
        print(f"    size mismatch: {got} of {expect} bytes", flush=True)
        return False, got / elapsed
    part.replace(dest)
    return True, got / elapsed


def fetch(
    repo: str, files: list[dict[str, Any]], out: pathlib.Path, limit_gb: float,
    manifest_path: pathlib.Path, *, revision: str = "main", audit: bool = False,
    verify_only: bool = False, max_files: int = 0,
) -> dict:
    """Audit, verify, or download a bounded subset of a pinned dataset revision.

    Audit mode never limits by byte budget: it reports the whole selected source.
    A partial ordinary download succeeds only if its selected shards all pass.
    The manifest's verified_bytes never includes a failed or unverified shard.
    """
    if verify_only and audit:
        raise ValueError("audit_and_verify_only_are_mutually_exclusive")
    if limit_gb < 0 or max_files < 0:
        raise ValueError("nonnegative_download_limits_required")
    # Preserve a legacy receipt once, never as evidence of current validity.
    prior = None
    if not audit and not verify_only and manifest_path.is_file():
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))
        if previous.get("schema") != "aureon.hf-corpus-acquisition.v2":
            prior = manifest_path.with_name(f"{manifest_path.stem}.legacy.json")
            if prior.exists():
                raise FileExistsError(f"legacy manifest already preserved: {prior}")
            write_json_atomic(prior, previous)
    completed: dict[str, dict[str, Any]] = {}
    if not audit and not verify_only and manifest_path.is_file():
        saved = json.loads(manifest_path.read_text(encoding="utf-8"))
        if saved.get("schema") == "aureon.hf-corpus-acquisition.v2" and saved.get("revision") == revision:
            assert saved.get("repo") == repo, "manifest_repo_mismatch"
            # A bounded run extends the same immutable corpus revision. A
            # different revision cannot inherit its predecessor's verification.
            completed = {
                str(item["file"]): item for item in saved.get("shards") or []
                if isinstance(item, dict) and isinstance(item.get("file"), str)
            }
    failures: list[dict[str, str]] = []
    if audit:
        selected = files
    else:
        candidates = files[:max_files or None]
        selected = []
        if limit_gb > 0:
            accumulated = 0
            for record in candidates:
                if selected and accumulated >= int(limit_gb * 1e9):
                    break
                selected.append(record)
                accumulated += int(record["bytes"])
        else:
            selected = list(candidates)
    for index, record in enumerate(selected, 1):
        path = out / record["file"]
        if audit or verify_only:
            ok, reason = verify_shard(path, record, checksum=True)
            if ok:
                completed[record["file"]] = {
                    **record,
                    "sha256": sha256_file(path),
                    "validation": "size_sha256_container",
                }
            else:
                failures.append({"file": record["file"], "reason": reason})
            print(f"[{index}/{len(selected)}] {'PASS' if ok else 'FAIL'} {record['file']}", flush=True)
        else:
            try:
                ok, rate, outcome = curl_shard(
                    repo, record["file"], out, record["bytes"],
                    revision=revision, sha256=record.get("sha256"),
                )
            except Exception as exc:  # noqa: BLE001 - one shard must not stop inventory
                ok, rate, outcome = False, 0.0, f"{type(exc).__name__}: {exc}"
            if not ok:
                completed.pop(record["file"], None)
                print(f"[{index}/{len(selected)}] FAILED {record['file']}", flush=True)
                failures.append({"file": record["file"], "reason": outcome or "download_failed"})
            else:
                completed[record["file"]] = {
                    **record, "sha256": outcome, "validation": "size_sha256_container",
                }
                print(
                    f"[{index}/{len(selected)}] {record['file']} "
                    f"{record['bytes'] / 1e9:.2f} GB {rate / 1e6:.1f} MB/s",
                    flush=True,
                )
        verified = [completed[key] for key in sorted(completed)]
        payload = {
            "schema": "aureon.hf-corpus-acquisition.v2",
            "repo": repo,
            "revision": revision,
            "selection": "selected_shards" if not audit else "all_selected_source_shards",
            "verified_bytes": sum(item["bytes"] for item in verified),
            "verified_shards": len(verified),
            "expected_shards": len(selected),
            "complete": not failures and len(verified) == len(files),
            "bytes": sum(item["bytes"] for item in verified),
            "est_tokens_b": round(sum(item["bytes"] for item in verified) / CHARS_PER_TOKEN / 1e9, 2),
            "shards": verified,
            "failures": failures,
            "prior_manifest": prior.name if prior else None,
        }
        if not audit and not verify_only:
            write_json_atomic(manifest_path, payload)
    return {
        "repo": repo, "revision": revision,
        "bytes": payload["verified_bytes"], "shards": len(verified),
        "complete": payload["complete"], "expected_shards": len(selected),
        "failed": len(failures), "failed_files": [item["file"] for item in failures[:50]],
        "mode": "audit" if audit else "verify" if verify_only else "download",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="fineweb-edu", choices=sorted(SOURCES))
    ap.add_argument("--out", default="data")
    ap.add_argument("--limit-gb", type=float, default=0.0, help="0 means everything")
    ap.add_argument("--max-files", type=int, default=0, help="bound a download to its first N shards")
    ap.add_argument("--audit", action="store_true", help="validate all local shards; download nothing")
    ap.add_argument("--verify", action="store_true", help="validate the bounded selection; download nothing")
    ap.add_argument("--revision", default="main", help="Hub branch or commit; resolved commit is recorded")
    ap.add_argument("--all", action="store_true", help="list every source and exit")
    ap.add_argument("--list", action="store_true", help="report sizes and exit")
    args = ap.parse_args()

    if args.list or args.all:
        for name in (sorted(SOURCES) if args.all else [args.source]):
            show_sizes(SOURCES[name], args.revision)
        return 0

    spec = SOURCES[args.source]
    # One directory per source. fineweb-edu and fineweb both publish
    # sample/100BT/<name>.parquet, so a shared output directory lets one source's
    # shards be counted as another's. That is what happened on 2026-10-26: 140
    # fineweb-edu shards and 150 fineweb shards went into one directory and left
    # a 130/20 mixture, while both manifests claimed a complete set.
    out = pathlib.Path(args.out) / args.source
    out.mkdir(parents=True, exist_ok=True)
    manifest = out / f"manifest-{args.source}.json"

    exts = tuple(spec.get("exts", (".parquet",)))
    try:
        resolved, records = shard_records(
            api(), spec["repo"], spec.get("prefer"), exts, args.revision,
        )
        files = [(record["file"], record["bytes"]) for record in records]
    except Exception as exc:
        print(f"{spec['repo']} unavailable ({type(exc).__name__}: {exc})")
        files = []

    repo = spec["repo"]
    if not files and spec.get("fallback"):
        repo = spec["fallback"]["repo"]
        exts = tuple(spec["fallback"].get("exts", (".parquet",)))
        print(f"falling back to {repo}", flush=True)
        files = shard_list(api(), repo, spec["fallback"].get("prefer"), exts)

    if not files:
        print("no shards found; set HF_TOKEN if the dataset is gated")
        return 1

    print(
        f"{repo}: {len(files)} shards available, "
        f"{sum(s for _, s in files) / 1e9:.1f} GB",
        flush=True,
    )
    result = fetch(
        repo, records, out, args.limit_gb, manifest,
        revision=resolved, audit=args.audit, verify_only=args.verify,
        max_files=args.max_files,
    )

    # A gated repo lists its shards happily and then refuses every download with
    # HTTP 401 (curl exit 22). The listing check cannot see that, so the
    # fallback has to be decided on the fetch result as well -- otherwise the
    # code source silently stages zero bytes and calls it a finished run.
    if result["shards"] == 0 and spec.get("fallback"):
        fb = spec["fallback"]
        print(f"staged nothing from {repo}; trying {fb['repo']}", flush=True)
        try:
            files = shard_list(api(), fb["repo"], fb.get("prefer"))
        except Exception as exc:
            print(f"{fb['repo']} unavailable ({type(exc).__name__}: {exc})")
            files = []
        if files:
            repo = fb["repo"]
            result = fetch(
                repo, records, out, args.limit_gb, manifest,
                revision=resolved, audit=args.audit, verify_only=args.verify,
                max_files=args.max_files,
            )

    print(json.dumps(result, indent=2), flush=True)
    # Empty or partial sources are failures; callers cannot mistake them for closure.
    return 0 if result["complete"] and not result["failed"] else 1


if __name__ == "__main__":
    sys.exit(main())
