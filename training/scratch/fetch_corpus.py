"""Stage pretraining data for Aureon's from-scratch model.

Pulls parquet shards straight from the Hub rather than re-encoding text, so
560 GB is written once instead of twice. Only the login node has outbound
network, so this always runs there.

    fetch_corpus.py --list
    fetch_corpus.py --source fineweb-edu --limit-gb 300 --out /projects/u6vs/pretrain/data
    fetch_corpus.py --source fineweb     --limit-gb 300 --out /projects/u6vs/pretrain/data

Downloads use curl rather than hf_hub_download on purpose: on 2026-10-26 a hub
download stalled with a zero-byte `.incomplete` file and an open TLS socket
that delivered nothing, and it sat there forever instead of retrying. curl
gives `-C -` resume, `--retry-all-errors`, and a speed floor that aborts a
dead stream after 60 s so the retry can actually fire.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
import time

SOURCES = {
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

    return HfApi()


def shard_list(hf, repo: str, prefer: str | None,
               exts: tuple[str, ...] = (".parquet",)) -> list[tuple[str, int]]:
    info = hf.repo_info(repo, repo_type="dataset", files_metadata=True)
    files = [
        (s.rfilename, int(s.size or 0))
        for s in info.siblings
        if s.rfilename.endswith(exts)
    ]
    if prefer:
        matched = [f for f in files if prefer in f[0]]
        if matched:
            files = matched
    files.sort()
    return files


def show_sizes(spec: dict) -> None:
    repo = spec["repo"]
    exts = tuple(spec.get("exts", (".parquet",)))
    try:
        files = shard_list(api(), repo, spec.get("prefer"), exts)
    except Exception as exc:
        print(f"{repo}: unavailable ({type(exc).__name__}: {exc})")
        return
    total = sum(size for _, size in files)
    print(
        f"{repo}: {len(files)} shards, {total / 1e9:.1f} GB "
        f"(~{total / CHARS_PER_TOKEN / 1e9:.1f}B tokens)"
    )
    if files:
        print(f"    first: {files[0][0]}  ({files[0][1] / 1e9:.2f} GB)")


def curl_shard(repo: str, name: str, out: pathlib.Path, expect: int) -> tuple[bool, float]:
    """Download one shard, resuming where a previous run left off."""
    dest = out / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    if expect and dest.exists() and dest.stat().st_size == expect:
        # Already complete. Resuming a finished file makes the server answer
        # 416 and curl exits non-zero, which would abort the whole run.
        return True, 0.0
    if dest.exists() and expect and dest.stat().st_size != expect:
        # A same-named shard from a different repo, or a torn download. curl -C -
        # would append to it, producing a file built from two datasets whose
        # length only looks plausible. Start over instead.
        dest.unlink()

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


def fetch(repo: str, files: list[tuple[str, int]], out: pathlib.Path,
          limit_gb: float, manifest_path: pathlib.Path) -> dict:
    limit = int(limit_gb * 1e9) if limit_gb > 0 else 0
    done = 0
    fetched = []
    failed = []
    for i, (name, size) in enumerate(files, 1):
        if limit and done >= limit:
            break
        ok, rate = curl_shard(repo, name, out, size)
        if not ok:
            # One bad shard must not look like a finished source: on 2026-10-26
            # a single failure ended the fineweb run at 135 of 150 shards while
            # the caller saw exit 0 and moved on to the next source.
            print(f"[{i}] FAILED {name}", flush=True)
            failed.append(name)
            continue
        done += size
        fetched.append({"repo": repo, "file": name, "bytes": size})
        print(
            f"[{i}/{len(files)}] {name}  {size / 1e9:.2f} GB  "
            f"{rate / 1e6:.1f} MB/s  total {done / 1e9:.1f} GB",
            flush=True,
        )
        manifest_path.write_text(
            json.dumps(
                {
                    "repo": repo,
                    "bytes": done,
                    "est_tokens_b": round(done / CHARS_PER_TOKEN / 1e9, 2),
                    "shards": fetched,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    return {"repo": repo, "bytes": done, "shards": len(fetched),
            "failed": len(failed), "failed_files": failed[:10]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="fineweb-edu", choices=sorted(SOURCES))
    ap.add_argument("--out", default="data")
    ap.add_argument("--limit-gb", type=float, default=0.0, help="0 means everything")
    ap.add_argument("--all", action="store_true", help="list every source and exit")
    ap.add_argument("--list", action="store_true", help="report sizes and exit")
    args = ap.parse_args()

    if args.list or args.all:
        for name in (sorted(SOURCES) if args.all else [args.source]):
            show_sizes(SOURCES[name])
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
        files = shard_list(api(), spec["repo"], spec.get("prefer"), exts)
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
    result = fetch(repo, files, out, args.limit_gb, manifest)

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
            result = fetch(repo, files, out, args.limit_gb, manifest)

    print(json.dumps(result, indent=2), flush=True)
    # Non-zero on any failed shard so the caller retries instead of treating a
    # partial source as complete and moving on.
    return 0 if result["shards"] and not result.get("failed") else 1


if __name__ == "__main__":
    sys.exit(main())
