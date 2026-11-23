#!/usr/bin/env python3
"""Download one immutable public Aureon model revision and verify its bytes.

The server separately repeats the weight integrity check before loading. This
stage never falls back to ``main``, another model, or a CPU-only substitute.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
import time
from pathlib import Path

from training.aureon_chat_server import (
    EXPECTED_WEIGHT_SHA256,
    EXPECTED_WEIGHT_SIZE,
    verify_weight_file,
)

MODEL_REPOSITORY = "GaryLeckey/aureon-7b"
MODEL_FILES = (
    "config.json",
    "generation_config.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "model.safetensors",
    "aureon_export.json",
    "preparation_receipt.json",
    "evaluation_summary.json",
)
REVISION_RE = re.compile(r"^[0-9a-f]{40}$")


def require_revision(value: str) -> str:
    revision = str(value or "").strip()
    if not REVISION_RE.fullmatch(revision):
        raise ValueError("AUREON_MODEL_REVISION must be one full lowercase Hub commit SHA")
    return revision


def _load_object(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected a JSON object: {path.name}")
    return value


def _receipt_weight_hash(receipt: dict) -> str:
    value = receipt.get("source_hashes", {}).get("model.safetensors")
    if isinstance(value, dict):
        value = value.get("sha256")
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value.lower()):
        raise RuntimeError("preparation receipt has no valid model.safetensors SHA-256")
    return value.lower()


def verify_download(model_dir: Path, revision: str) -> dict:
    revision = require_revision(revision)
    for name in MODEL_FILES:
        if not (model_dir / name).is_file():
            raise RuntimeError(f"immutable model snapshot is missing {name}")
    receipt_path = model_dir / "preparation_receipt.json"
    receipt = _load_object(receipt_path)
    if _receipt_weight_hash(receipt) != EXPECTED_WEIGHT_SHA256:
        raise RuntimeError("downloaded preparation receipt names a different source weight")
    integrity = verify_weight_file(
        model_dir,
        expected_sha256=EXPECTED_WEIGHT_SHA256,
        expected_size=EXPECTED_WEIGHT_SIZE,
    )
    config = _load_object(model_dir / "config.json")
    if config.get("vocab_size") != 65_536:
        raise RuntimeError("downloaded model vocabulary mismatch")
    if config.get("eos_token_id") != 1 or config.get("bos_token_id") != 1:
        raise RuntimeError("downloaded model EOS/BOS metadata mismatch")
    return {
        "schema_version": 1,
        "repository": MODEL_REPOSITORY,
        "revision": revision,
        "weight_sha256": integrity["sha256"],
        "weight_size_bytes": integrity["size_bytes"],
        "preparation_receipt_sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
        "files": list(MODEL_FILES),
        "verified_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def write_receipt(path: Path, receipt: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = (json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    descriptor, temporary_name = tempfile.mkstemp(prefix=".model-receipt-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except Exception:
        try:
            Path(temporary_name).unlink()
        except OSError:
            pass
        raise


def download_model(
    model_dir: Path,
    revision: str,
    *,
    receipt_path: Path,
) -> dict:
    """Populate a reusable local directory, then verify the complete candidate."""

    revision = require_revision(revision)
    from huggingface_hub import snapshot_download

    model_dir.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id=MODEL_REPOSITORY,
        repo_type="model",
        revision=revision,
        local_dir=model_dir,
        allow_patterns=list(MODEL_FILES),
        max_workers=4,
    )
    receipt = verify_download(model_dir, revision)
    write_receipt(receipt_path, receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--revision", default=os.environ.get("AUREON_MODEL_REVISION", ""))
    parser.add_argument("--receipt", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        receipt = download_model(
            arguments.model_dir,
            arguments.revision,
            receipt_path=arguments.receipt,
        )
    except Exception as exc:  # noqa: BLE001 - nonzero startup with a safe diagnostic
        print(f"Aureon model bootstrap failed: {type(exc).__name__}: {exc}", flush=True)
        return 1
    print(json.dumps({
        "model_ready_to_load": True,
        "repository": receipt["repository"],
        "revision": receipt["revision"],
        "weight_sha256": receipt["weight_sha256"],
        "weight_size_bytes": receipt["weight_size_bytes"],
    }, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
