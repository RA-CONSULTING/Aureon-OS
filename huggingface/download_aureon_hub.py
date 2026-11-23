#!/usr/bin/env python3
"""Anonymously download and verify the pinned public Aureon Hub release."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from publish_aureon_model import MODEL_FILES

HUB_REPOSITORY = "GaryLeckey/aureon-7b"
HUB_REVISION = "0757a7bdc36b190e9641a4cf421f89b9c66fab05"
PUBLIC_RECEIPT = Path("/projects/u6vs/aureon-hf-release/model-public-receipt.json")


class DownloadError(RuntimeError):
    """A fresh Hub download or publication receipt failed verification."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise DownloadError(message)


def _value(item: Any, name: str, default: Any = None) -> Any:
    if isinstance(item, Mapping):
        return item.get(name, default)
    return getattr(item, name, default)


def confirm_public_head(api: Any) -> None:
    """Require anonymous access to an ungated public repo at the pinned HEAD."""

    info = api.repo_info(
        repo_id=HUB_REPOSITORY,
        repo_type="model",
        revision="main",
        token=False,
    )
    require(_value(info, "private") is False, "Hub repository is not public")
    require(_value(info, "gated") in (None, False), "Hub repository is gated")
    require(
        _value(info, "sha") == HUB_REVISION,
        f"Hub HEAD is not the required revision {HUB_REVISION}",
    )


def _expected_files(receipt_path: Path) -> dict[str, tuple[int, str]]:
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DownloadError(f"cannot read public receipt {receipt_path}: {exc}") from exc
    require(isinstance(receipt, dict), "public receipt must be a JSON object")
    require(receipt.get("repository") == HUB_REPOSITORY, "public receipt repository mismatch")
    require(receipt.get("revision") == HUB_REVISION, "public receipt revision mismatch")
    require(receipt.get("visibility") == "public", "public receipt does not attest public release")
    entries = receipt.get("files")
    require(isinstance(entries, list), "public receipt has no files list")

    expected: dict[str, tuple[int, str]] = {}
    for entry in entries:
        require(isinstance(entry, dict), "public receipt file entry must be an object")
        path = entry.get("path")
        size = entry.get("size_bytes")
        digest = entry.get("sha256")
        require(
            isinstance(path, str) and path in MODEL_FILES,
            "public receipt contains a non-allowlisted path",
        )
        require(path not in expected, f"public receipt repeats {path}")
        require(
            isinstance(size, int) and not isinstance(size, bool) and size >= 0,
            f"public receipt has invalid size for {path}",
        )
        require(
            isinstance(digest, str) and len(digest) == 64,
            f"public receipt has invalid SHA-256 for {path}",
        )
        require(
            all(character in "0123456789abcdef" for character in digest),
            f"public receipt SHA-256 for {path} must be lowercase hexadecimal",
        )
        expected[path] = (size, digest)
    require(set(expected) == set(MODEL_FILES), "public receipt does not contain all nine files")
    return expected


def _hash_regular_file(path: Path) -> tuple[int, str]:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise DownloadError(f"missing downloaded file: {path.name}") from exc
    require(
        stat.S_ISREG(metadata.st_mode),
        f"downloaded file must be regular and non-symlink: {path.name}",
    )
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise DownloadError(f"cannot open downloaded file without symlinks: {path.name}") from exc
    digest = hashlib.sha256()
    size = 0
    try:
        require(stat.S_ISREG(os.fstat(descriptor).st_mode), f"not a regular file: {path.name}")
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
                size += len(chunk)
                digest.update(chunk)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    return size, digest.hexdigest()


def download_fresh_model(
    download_directory: Path,
    public_receipt: Path,
    *,
    api: Any,
    download_file: Callable[..., str],
) -> dict[str, Any]:
    """Create a new directory, fetch only the allowlist, and verify every file."""

    download_directory = Path(download_directory)
    expected = _expected_files(Path(public_receipt))
    try:
        download_directory.mkdir()
    except FileExistsError as exc:
        raise DownloadError("download directory already exists; a new empty path is required") from exc
    except OSError as exc:
        raise DownloadError(f"cannot create download directory: {exc}") from exc

    confirm_public_head(api)
    for name in MODEL_FILES:
        destination = download_directory / name
        downloaded = download_file(
            repo_id=HUB_REPOSITORY,
            repo_type="model",
            filename=name,
            revision=HUB_REVISION,
            local_dir=download_directory,
            local_dir_use_symlinks=False,
            local_files_only=False,
            token=False,
        )
        require(
            Path(os.path.abspath(os.fspath(downloaded)))
            == Path(os.path.abspath(os.fspath(destination))),
            f"Hub returned an unexpected download path for {name}",
        )
        actual_size, actual_hash = _hash_regular_file(destination)
        expected_size, expected_hash = expected[name]
        require(
            actual_size == expected_size,
            f"downloaded size mismatch for {name}: {actual_size} != {expected_size}",
        )
        require(
            actual_hash == expected_hash,
            f"downloaded SHA-256 mismatch for {name}",
        )
    return {
        "fresh_hub_download": True,
        "repository": HUB_REPOSITORY,
        "revision": HUB_REVISION,
        "files": list(MODEL_FILES),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download-dir", type=Path, required=True)
    parser.add_argument("--public-receipt", type=Path, default=PUBLIC_RECEIPT)
    arguments = parser.parse_args(argv)
    try:
        hub = importlib.import_module("huggingface_hub")
        result = download_fresh_model(
            arguments.download_dir,
            arguments.public_receipt,
            api=hub.HfApi(token=False),
            download_file=hub.hf_hub_download,
        )
    except Exception as exc:  # noqa: BLE001 - concise operational failure for Slurm logs
        print(f"fresh Hub download failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
