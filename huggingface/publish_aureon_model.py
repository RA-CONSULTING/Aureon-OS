#!/usr/bin/env python3
"""Publish only the verified canonical Aureon 7B model to its fixed Hub repo.

The default action is an offline dry-run which emits a path-safe manifest. An
upload is private, requires explicit acknowledgement, and reads the Hub token
only at execution time. Public visibility is a separate, independently gated
operation. Source exports and metadata overlays are never modified, and the
weight is uploaded in place rather than copied to a staging directory.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import importlib
import json
import os
import re
import stat
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

MODEL_REPOSITORY = "GaryLeckey/aureon-7b"
CANONICAL_SOURCE = Path(
    "/projects/u6vs/hnc-organism/runs/aureon-7b-sft-label-fix/hf"
)
DEFAULT_OVERLAY = Path(__file__).with_name("aureon-7b")
EXPECTED_WEIGHT_SIZE = 13_990_806_664
EXPECTED_WEIGHT_SHA256 = "48487f800623474ab99371d71b369694cae64f8ebc4ef038019c7e60da3d45bb"
OVERLAY_FILES = (
    "config.json",
    "generation_config.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "aureon_export.json",
    "preparation_receipt.json",
    "evaluation_summary.json",
    "README.md",
)
MODEL_FILES = (
    "config.json",
    "generation_config.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "model.safetensors",
    "aureon_export.json",
    "preparation_receipt.json",
    "evaluation_summary.json",
    "README.md",
)
ALLOWED_FILES = frozenset(MODEL_FILES)
TOKEN_ENV_NAMES = ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN")
EXECUTION_ACK = "PUBLISH_AUREON_7B_TO_PRIVATE_STAGING"
PUBLIC_ACK = "MAKE_GARYLECKEY_AUREON_7B_PUBLIC"
REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
SECRET_PATTERNS = (
    ("private key", re.compile(br"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("Hugging Face token", re.compile(br"(?<![A-Za-z0-9])hf_[A-Za-z0-9]{24,}(?![A-Za-z0-9])")),
    ("GitHub token", re.compile(br"(?<![A-Za-z0-9])(?:ghp|github_pat)_[A-Za-z0-9_]{24,}")),
    ("AWS access key", re.compile(br"(?<![A-Z0-9])(?:AKIA|ASIA)[A-Z0-9]{16}(?![A-Z0-9])")),
)


class PublicationError(RuntimeError):
    """A local candidate or remote repository failed a release safety check."""


@dataclass(frozen=True)
class FileRecord:
    path: str
    local_path: Path
    origin: str
    size_bytes: int
    sha256: str
    git_blob_sha1: str
    fingerprint: tuple[int, int, int, int, int]

    def manifest_entry(self) -> dict[str, Any]:
        """Return public metadata, deliberately excluding the local path."""

        return {
            "path": self.path,
            "origin": self.origin,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "git_blob_sha1": self.git_blob_sha1,
        }


@dataclass(frozen=True)
class PublicationPlan:
    source: Path
    overlay: Path
    files: tuple[FileRecord, ...]

    def manifest(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "repository": MODEL_REPOSITORY,
            "repo_type": "model",
            "staging_visibility": "private",
            "weight_staged_locally": False,
            "files": [record.manifest_entry() for record in self.files],
        }


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def require_revision(value: Any) -> str:
    revision = str(value or "").strip()
    if not REVISION_RE.fullmatch(revision):
        raise PublicationError("Hub result did not contain one full lowercase commit SHA")
    return revision


def _absolute(path: str | os.PathLike[str]) -> Path:
    # abspath normalizes without resolving or following symbolic links.
    return Path(os.path.abspath(os.fspath(path)))


def _require_directory(path: Path, label: str) -> None:
    try:
        mode = path.lstat().st_mode
    except OSError as exc:
        raise PublicationError(f"{label} is not an accessible directory: {path}") from exc
    if not stat.S_ISDIR(mode):
        raise PublicationError(f"{label} must be a real directory, not a symlink: {path}")


def _fingerprint(value: os.stat_result) -> tuple[int, int, int, int, int]:
    # Windows can report a synthetic fstat ctime that differs from lstat for
    # an unchanged file. These five fields are stable across both APIs.
    return (
        value.st_dev,
        value.st_ino,
        value.st_size,
        value.st_mtime_ns,
        value.st_mode,
    )


def _regular_stat(path: Path) -> os.stat_result:
    try:
        value = path.lstat()
    except OSError as exc:
        raise PublicationError(f"required release file is missing or unreadable: {path.name}") from exc
    if not stat.S_ISREG(value.st_mode):
        raise PublicationError(f"release file must be a regular non-symlink file: {path.name}")
    return value


def _open_readonly_nofollow(path: Path) -> int:
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        return os.open(path, flags)
    except OSError as exc:
        raise PublicationError(f"cannot open release file without following symlinks: {path.name}") from exc


def _hash_file(path: Path) -> tuple[str, str, os.stat_result]:
    before = _regular_stat(path)
    descriptor = _open_readonly_nofollow(path)
    sha256 = hashlib.sha256()
    git_blob = hashlib.sha1()
    git_blob.update(f"blob {before.st_size}\0".encode("ascii"))
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or _fingerprint(opened) != _fingerprint(before):
            raise PublicationError(f"release file changed before it could be read: {path.name}")
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
                sha256.update(chunk)
                git_blob.update(chunk)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    after = _regular_stat(path)
    if _fingerprint(after) != _fingerprint(before):
        raise PublicationError(f"release file changed while it was being hashed: {path.name}")
    return sha256.hexdigest(), git_blob.hexdigest(), before


def _record(path: str, local_path: Path, origin: str) -> FileRecord:
    if path not in ALLOWED_FILES:
        raise PublicationError(f"refusing non-allowlisted release path: {path}")
    sha256, git_blob_sha1, metadata = _hash_file(local_path)
    return FileRecord(
        path=path,
        local_path=local_path,
        origin=origin,
        size_bytes=metadata.st_size,
        sha256=sha256,
        git_blob_sha1=git_blob_sha1,
        fingerprint=_fingerprint(metadata),
    )


def _scan_text_record(record: FileRecord) -> None:
    """High-confidence secret gate for the public text/JSON overlay."""

    descriptor = _open_readonly_nofollow(record.local_path)
    try:
        opened = os.fstat(descriptor)
        if _fingerprint(opened) != record.fingerprint:
            raise PublicationError(f"release file changed before secret scanning: {record.path}")
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            content = handle.read()
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if _fingerprint(_regular_stat(record.local_path)) != record.fingerprint:
        raise PublicationError(f"release file changed during secret scanning: {record.path}")
    for label, pattern in SECRET_PATTERNS:
        if pattern.search(content):
            raise PublicationError(f"possible {label} in release overlay file: {record.path}")


def _load_object(path: Path) -> dict[str, Any]:
    _regular_stat(path)
    descriptor = _open_readonly_nofollow(path)
    try:
        with os.fdopen(descriptor, "r", encoding="utf-8") as handle:
            descriptor = -1
            value = json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PublicationError(f"cannot read JSON object: {path.name}") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if not isinstance(value, dict):
        raise PublicationError(f"expected a JSON object: {path.name}")
    return value


def _receipt_weight_hash(receipt: Mapping[str, Any]) -> str:
    hashes = receipt.get("source_hashes")
    value = hashes.get("model.safetensors") if isinstance(hashes, Mapping) else None
    if isinstance(value, Mapping):
        value = value.get("sha256")
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value.lower()):
        raise PublicationError("preparation receipt has no valid model.safetensors SHA-256")
    return value.lower()


def _validate_overlay_identity(overlay: Path) -> None:
    """Apply the same receipt and config identity checks as model_bootstrap."""

    receipt = _load_object(overlay / "preparation_receipt.json")
    if _receipt_weight_hash(receipt) != EXPECTED_WEIGHT_SHA256:
        raise PublicationError("preparation receipt names a different source weight")
    config = _load_object(overlay / "config.json")
    if config.get("vocab_size") != 65_536:
        raise PublicationError("model vocabulary mismatch")
    if config.get("eos_token_id") != 1 or config.get("bos_token_id") != 1:
        raise PublicationError("model EOS/BOS metadata mismatch")


def build_plan(
    source_directory: str | os.PathLike[str],
    overlay_directory: str | os.PathLike[str],
) -> PublicationPlan:
    """Read and verify the complete local candidate without writing anything."""

    source = _absolute(source_directory)
    overlay = _absolute(overlay_directory)
    _require_directory(source, "source export")
    _require_directory(overlay, "metadata overlay")

    # The canonical weight is always checked before any caller can write a
    # manifest, create a repository, or upload an overlay file.
    weight_path = source / "model.safetensors"
    weight_size = _regular_stat(weight_path).st_size
    if weight_size != EXPECTED_WEIGHT_SIZE:
        raise PublicationError(
            f"model.safetensors size mismatch: expected {EXPECTED_WEIGHT_SIZE}, got {weight_size}"
        )
    weight = _record("model.safetensors", weight_path, "source-export")
    if not hmac.compare_digest(weight.sha256, EXPECTED_WEIGHT_SHA256):
        raise PublicationError("model.safetensors SHA-256 mismatch")

    by_name = {weight.path: weight}
    for name in OVERLAY_FILES:
        by_name[name] = _record(name, overlay / name, "metadata-overlay")
        _scan_text_record(by_name[name])
    _validate_overlay_identity(overlay)
    files = tuple(by_name[name] for name in MODEL_FILES)
    if {record.path for record in files} != ALLOWED_FILES or len(files) != len(ALLOWED_FILES):
        raise PublicationError("internal release allowlist is incomplete")
    return PublicationPlan(source=source, overlay=overlay, files=files)


def dry_run(
    source_directory: str | os.PathLike[str] = CANONICAL_SOURCE,
    overlay_directory: str | os.PathLike[str] = DEFAULT_OVERLAY,
) -> dict[str, Any]:
    manifest = build_plan(source_directory, overlay_directory).manifest()
    manifest["dry_run"] = True
    return manifest


def _entry_value(entry: Any, name: str, default: Any = None) -> Any:
    if isinstance(entry, Mapping):
        return entry.get(name, default)
    return getattr(entry, name, default)


def _entry_path(entry: Any) -> str:
    value = _entry_value(entry, "path") or _entry_value(entry, "rfilename")
    if not value:
        raise PublicationError("Hub metadata entry has no repository path")
    return str(value)


def _lfs_oid(entry: Any) -> str | None:
    lfs = _entry_value(entry, "lfs")
    if not lfs:
        return None
    oid = _entry_value(lfs, "oid") or _entry_value(lfs, "sha256")
    if not oid:
        return None
    return str(oid).removeprefix("sha256:").lower()


def _remote_match(record: FileRecord, entry: Any) -> bool:
    lfs_oid = _lfs_oid(entry)
    remote_blob = _entry_value(entry, "blob_id") or _entry_value(entry, "oid")
    expected = record.sha256 if lfs_oid else record.git_blob_sha1
    actual = lfs_oid or remote_blob
    remote_size = _entry_value(entry, "size")
    if not expected or not actual or remote_size is None:
        return False
    try:
        size_matches = int(remote_size) == record.size_bytes
    except (TypeError, ValueError):
        return False
    return size_matches and hmac.compare_digest(expected, str(actual).lower())


def _remote_entries(api: Any, revision: str | None = None) -> dict[str, Any]:
    arguments: dict[str, Any] = {
        "repo_id": MODEL_REPOSITORY,
        "repo_type": "model",
        "recursive": True,
        "expand": True,
    }
    if revision is not None:
        arguments["revision"] = revision
    entries = api.list_repo_tree(**arguments)
    result: dict[str, Any] = {}
    for entry in entries:
        if _entry_value(entry, "type") in {"directory", "folder"}:
            continue
        path = _entry_path(entry)
        if path in result:
            raise PublicationError(f"Hub returned duplicate metadata for {path}")
        result[path] = entry
    return result


def _reconciliation(
    plan: PublicationPlan, entries: Mapping[str, Any]
) -> tuple[list[FileRecord], list[FileRecord], list[str]]:
    verified: list[FileRecord] = []
    missing: list[FileRecord] = []
    mismatched: list[str] = []
    for record in plan.files:
        entry = entries.get(record.path)
        if entry is None:
            missing.append(record)
        elif _remote_match(record, entry):
            verified.append(record)
        else:
            mismatched.append(record.path)
    return verified, missing, mismatched


def _check_no_mismatch(mismatched: Sequence[str]) -> None:
    if mismatched:
        raise PublicationError(
            "remote hash/size mismatch; refusing to overwrite: " + ", ".join(sorted(mismatched))
        )


def _check_no_unexpected_remote(entries: Mapping[str, Any]) -> None:
    unexpected = sorted(set(entries) - ALLOWED_FILES - {".gitattributes"})
    if unexpected:
        raise PublicationError(
            "unexpected remote model files require accountable review: " + ", ".join(unexpected)
        )


def _check_complete(plan: PublicationPlan, entries: Mapping[str, Any]) -> list[FileRecord]:
    _check_no_unexpected_remote(entries)
    verified, missing, mismatched = _reconciliation(plan, entries)
    _check_no_mismatch(mismatched)
    if missing:
        raise PublicationError(
            "incomplete remote upload; missing: " + ", ".join(record.path for record in missing)
        )
    if len(verified) != len(plan.files):
        raise PublicationError("remote reconciliation did not verify the complete allowlist")
    return verified


def _check_private(info: Any) -> None:
    if _entry_value(info, "private") is not True:
        raise PublicationError("canonical model repository is not private staging")


def _check_unchanged_local_files(plan: PublicationPlan) -> None:
    for record in plan.files:
        if _fingerprint(_regular_stat(record.local_path)) != record.fingerprint:
            raise PublicationError(f"local release file changed before upload: {record.path}")


def _ensure_output_outside_inputs(path: Path, plan: PublicationPlan) -> None:
    output = _absolute(path)
    for root in (plan.source, plan.overlay):
        if output == root or output.is_relative_to(root):
            raise PublicationError("manifest and receipt outputs must be outside source and overlay directories")


def _write_json_atomic(path: str | os.PathLike[str], value: Mapping[str, Any]) -> None:
    destination = _absolute(path)
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        content = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
        )
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, destination)
        except Exception:
            try:
                Path(temporary_name).unlink()
            except OSError:
                pass
            raise
    except OSError as exc:
        raise PublicationError(f"cannot write release output: {destination.name}") from exc


def _require_execution_ack(value: str | None) -> None:
    if value != EXECUTION_ACK:
        raise PublicationError(f"execution requires acknowledgement {EXECUTION_ACK}")


def _require_public_ack(value: str | None) -> None:
    if value != PUBLIC_ACK:
        raise PublicationError(f"public visibility requires acknowledgement {PUBLIC_ACK}")


def publish_model(
    source_directory: str | os.PathLike[str],
    overlay_directory: str | os.PathLike[str],
    *,
    api: Any,
    commit_operation_add: Any,
    acknowledge_execution: str | None,
    receipt_path: str | os.PathLike[str],
) -> dict[str, Any]:
    """Upload missing files to private staging and return an exact revision receipt."""

    _require_execution_ack(acknowledge_execution)
    plan = build_plan(source_directory, overlay_directory)
    receipt_destination = _absolute(receipt_path)
    _ensure_output_outside_inputs(receipt_destination, plan)

    api.create_repo(MODEL_REPOSITORY, repo_type="model", private=True, exist_ok=True)
    initial_info = api.repo_info(MODEL_REPOSITORY, repo_type="model")
    _check_private(initial_info)
    initial_revision_value = _entry_value(initial_info, "sha") or _entry_value(initial_info, "oid")
    initial_revision = (
        str(initial_revision_value)
        if initial_revision_value and REVISION_RE.fullmatch(str(initial_revision_value))
        else None
    )
    remote = _remote_entries(api, initial_revision)
    _check_no_unexpected_remote(remote)
    verified, missing, mismatched = _reconciliation(plan, remote)
    _check_no_mismatch(mismatched)
    skipped = [record.path for record in verified]

    if missing:
        _check_unchanged_local_files(plan)
        operations = [
            commit_operation_add(path_in_repo=record.path, path_or_fileobj=record.local_path)
            for record in missing
        ]
        result = api.create_commit(
            repo_id=MODEL_REPOSITORY,
            repo_type="model",
            operations=operations,
            commit_message="Publish verified canonical Aureon 7B release",
        )
        revision = require_revision(
            _entry_value(result, "oid") or _entry_value(result, "sha")
        )
    else:
        revision = require_revision(initial_revision_value)

    final_remote = _remote_entries(api, revision)
    _check_complete(plan, final_remote)
    final_info = api.repo_info(MODEL_REPOSITORY, repo_type="model")
    _check_private(final_info)
    if require_revision(_entry_value(final_info, "sha") or _entry_value(final_info, "oid")) != revision:
        raise PublicationError("repository HEAD changed during upload reconciliation")

    receipt = plan.manifest()
    receipt.update({
        "dry_run": False,
        "visibility": "private",
        "revision": revision,
        "verified_utc": _utc_now(),
        "uploaded_files": [record.path for record in missing],
        "skipped_files": skipped,
        "weight_sha256": EXPECTED_WEIGHT_SHA256,
        "weight_size_bytes": EXPECTED_WEIGHT_SIZE,
    })
    _write_json_atomic(receipt_destination, receipt)
    return receipt


def make_model_public(
    source_directory: str | os.PathLike[str],
    overlay_directory: str | os.PathLike[str],
    *,
    api: Any,
    acknowledge_execution: str | None,
    acknowledge_public: str | None,
    receipt_path: str | os.PathLike[str],
) -> dict[str, Any]:
    """Independently verify the complete private release, then make it public."""

    _require_execution_ack(acknowledge_execution)
    _require_public_ack(acknowledge_public)
    plan = build_plan(source_directory, overlay_directory)
    receipt_destination = _absolute(receipt_path)
    _ensure_output_outside_inputs(receipt_destination, plan)

    before = api.repo_info(MODEL_REPOSITORY, repo_type="model")
    _check_private(before)
    revision = require_revision(_entry_value(before, "sha") or _entry_value(before, "oid"))
    remote = _remote_entries(api, revision)
    _check_no_unexpected_remote(remote)
    _check_complete(plan, remote)

    api.update_repo_visibility(MODEL_REPOSITORY, private=False, repo_type="model")
    after = api.repo_info(MODEL_REPOSITORY, repo_type="model")
    if _entry_value(after, "private") is not False:
        raise PublicationError("Hub did not confirm public repository visibility")
    if require_revision(_entry_value(after, "sha") or _entry_value(after, "oid")) != revision:
        raise PublicationError("repository revision changed during public visibility update")

    receipt = plan.manifest()
    receipt.update({
        "dry_run": False,
        "visibility": "public",
        "revision": revision,
        "verified_utc": _utc_now(),
        "uploaded_files": [],
        "skipped_files": [record.path for record in plan.files],
        "weight_sha256": EXPECTED_WEIGHT_SHA256,
        "weight_size_bytes": EXPECTED_WEIGHT_SIZE,
    })
    _write_json_atomic(receipt_destination, receipt)
    return receipt


def _api_from_environment() -> tuple[Any, Any]:
    """Construct the Hub client only for an acknowledged execution request."""

    values = [os.environ.get(name, "").strip() for name in TOKEN_ENV_NAMES]
    if all(values) and values[0] != values[1]:
        raise PublicationError("HF_TOKEN and HUGGING_FACE_HUB_TOKEN disagree; set only one")
    token = next((value for value in values if value), None)
    if not token:
        raise PublicationError("HF_TOKEN or HUGGING_FACE_HUB_TOKEN is required for execution")
    hub = importlib.import_module("huggingface_hub")
    return hub.HfApi(token=token), hub.CommitOperationAdd


def _safe_error(error: BaseException, *, execution: bool) -> str:
    message = f"{type(error).__name__}: {error}"
    if execution:
        for name in TOKEN_ENV_NAMES:
            raw_value = os.environ.get(name, "")
            for value in {raw_value, raw_value.strip()}:
                if value:
                    message = message.replace(value, "[redacted]")
    return message[:2000]


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=CANONICAL_SOURCE)
    parser.add_argument("--overlay", type=Path, default=DEFAULT_OVERLAY)
    parser.add_argument("--manifest", type=Path, help="optional dry-run manifest output")
    parser.add_argument("--receipt", type=Path, help="required execution receipt output")
    parser.add_argument("--execute", action="store_true", help="perform the acknowledged operation")
    parser.add_argument("--acknowledge-execution")
    parser.add_argument(
        "--make-public",
        action="store_true",
        help="only change a fully reconciled private release to public",
    )
    parser.add_argument("--acknowledge-public")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _argument_parser().parse_args(argv)
    execution = bool(args.execute or args.make_public)
    try:
        if args.make_public and not args.execute:
            raise PublicationError("public visibility also requires --execute and its acknowledgement")
        if execution and not args.receipt:
            raise PublicationError("execution requires --receipt outside the source and overlay")
        if not execution and args.receipt:
            raise PublicationError("--receipt is valid only with --execute")
        if execution and args.manifest:
            raise PublicationError("--manifest is a dry-run output; use --receipt for execution")
        if not execution and (args.acknowledge_execution or args.acknowledge_public):
            raise PublicationError("acknowledgements are valid only with an execution request")

        if not execution:
            plan = build_plan(args.source, args.overlay)
            manifest = plan.manifest()
            manifest["dry_run"] = True
            if args.manifest:
                _ensure_output_outside_inputs(_absolute(args.manifest), plan)
                _write_json_atomic(args.manifest, manifest)
            result = manifest
        else:
            _require_execution_ack(args.acknowledge_execution)
            if args.make_public:
                _require_public_ack(args.acknowledge_public)
            api, commit_operation_add = _api_from_environment()
            if args.make_public:
                result = make_model_public(
                    args.source,
                    args.overlay,
                    api=api,
                    acknowledge_execution=args.acknowledge_execution,
                    acknowledge_public=args.acknowledge_public,
                    receipt_path=args.receipt,
                )
            else:
                result = publish_model(
                    args.source,
                    args.overlay,
                    api=api,
                    commit_operation_add=commit_operation_add,
                    acknowledge_execution=args.acknowledge_execution,
                    receipt_path=args.receipt,
                )
    except Exception as exc:  # noqa: BLE001 - operational CLI must not leak a Hub traceback
        print(json.dumps({"error": _safe_error(exc, execution=execution)}, sort_keys=True))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
