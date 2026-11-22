"""Focused tests for immutable Hugging Face model bootstrap behavior."""

from __future__ import annotations

import hashlib
import json
import sys
import types
from unittest import mock

import pytest

from deploy.huggingface import model_bootstrap as bootstrap

REVISION = "a" * 40


def _write_json(path, value: dict) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def _snapshot(tmp_path):
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    for name in bootstrap.MODEL_FILES:
        (model_dir / name).write_bytes(b"{}")
    _write_json(model_dir / "config.json", {
        "vocab_size": 65_536,
        "eos_token_id": 1,
        "bos_token_id": 1,
    })
    _write_json(model_dir / "preparation_receipt.json", {
        "source_hashes": {"model.safetensors": bootstrap.EXPECTED_WEIGHT_SHA256},
    })
    return model_dir


def _integrity() -> dict:
    return {
        "sha256": bootstrap.EXPECTED_WEIGHT_SHA256,
        "size_bytes": bootstrap.EXPECTED_WEIGHT_SIZE,
        "verified": True,
    }


@pytest.mark.parametrize("revision", ["", "main", "a" * 39, "a" * 41, "g" * 40, "A" * 40])
def test_require_revision_rejects_non_immutable_values(revision: str) -> None:
    with pytest.raises(ValueError, match="full lowercase Hub commit SHA"):
        bootstrap.require_revision(revision)


def test_require_revision_accepts_one_full_hex_commit() -> None:
    assert bootstrap.require_revision(f"  {REVISION}  ") == REVISION


def test_download_uses_exact_repository_revision_and_allowlist(tmp_path, monkeypatch) -> None:
    hub = types.ModuleType("huggingface_hub")
    hub.snapshot_download = mock.Mock()
    monkeypatch.setitem(sys.modules, "huggingface_hub", hub)
    monkeypatch.setattr(bootstrap, "verify_download", mock.Mock(return_value={
        "repository": bootstrap.MODEL_REPOSITORY,
        "revision": REVISION,
        "weight_sha256": bootstrap.EXPECTED_WEIGHT_SHA256,
        "weight_size_bytes": bootstrap.EXPECTED_WEIGHT_SIZE,
    }))
    model_dir = tmp_path / "model"
    receipt_path = tmp_path / "receipts" / "model.json"

    receipt = bootstrap.download_model(model_dir, REVISION, receipt_path=receipt_path)

    hub.snapshot_download.assert_called_once_with(
        repo_id="GaryLeckey/aureon-7b",
        repo_type="model",
        revision=REVISION,
        local_dir=model_dir,
        allow_patterns=list(bootstrap.MODEL_FILES),
        max_workers=4,
    )
    bootstrap.verify_download.assert_called_once_with(model_dir, REVISION)
    assert json.loads(receipt_path.read_text(encoding="utf-8")) == receipt


def test_verify_download_returns_pinned_identity_and_receipt_digest(tmp_path, monkeypatch) -> None:
    model_dir = _snapshot(tmp_path)
    monkeypatch.setattr(bootstrap, "verify_weight_file", mock.Mock(return_value=_integrity()))

    receipt = bootstrap.verify_download(model_dir, REVISION)

    assert receipt["repository"] == bootstrap.MODEL_REPOSITORY
    assert receipt["revision"] == REVISION
    assert receipt["weight_sha256"] == bootstrap.EXPECTED_WEIGHT_SHA256
    assert receipt["weight_size_bytes"] == bootstrap.EXPECTED_WEIGHT_SIZE
    assert receipt["preparation_receipt_sha256"] == hashlib.sha256(
        (model_dir / "preparation_receipt.json").read_bytes()
    ).hexdigest()
    assert receipt["files"] == list(bootstrap.MODEL_FILES)
    bootstrap.verify_weight_file.assert_called_once_with(
        model_dir,
        expected_sha256=bootstrap.EXPECTED_WEIGHT_SHA256,
        expected_size=bootstrap.EXPECTED_WEIGHT_SIZE,
    )


def test_verify_download_rejects_receipt_for_different_source_weight(tmp_path) -> None:
    model_dir = _snapshot(tmp_path)
    _write_json(model_dir / "preparation_receipt.json", {
        "source_hashes": {"model.safetensors": "0" * 64},
    })

    with pytest.raises(RuntimeError, match="different source weight"):
        bootstrap.verify_download(model_dir, REVISION)


@pytest.mark.parametrize("failure", ["SHA-256", "size"])
def test_verify_download_propagates_independent_weight_integrity_failures(
    tmp_path, monkeypatch, failure: str
) -> None:
    model_dir = _snapshot(tmp_path)
    monkeypatch.setattr(
        bootstrap,
        "verify_weight_file",
        mock.Mock(side_effect=RuntimeError(f"weight {failure} mismatch")),
    )

    with pytest.raises(RuntimeError, match=f"weight {failure} mismatch"):
        bootstrap.verify_download(model_dir, REVISION)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("vocab_size", 32_000, "vocabulary mismatch"),
        ("eos_token_id", 2, "EOS/BOS metadata mismatch"),
        ("bos_token_id", 2, "EOS/BOS metadata mismatch"),
    ],
)
def test_verify_download_rejects_wrong_model_metadata(
    tmp_path, monkeypatch, field: str, value: int, message: str
) -> None:
    model_dir = _snapshot(tmp_path)
    config = json.loads((model_dir / "config.json").read_text(encoding="utf-8"))
    config[field] = value
    _write_json(model_dir / "config.json", config)
    monkeypatch.setattr(bootstrap, "verify_weight_file", mock.Mock(return_value=_integrity()))

    with pytest.raises(RuntimeError, match=message):
        bootstrap.verify_download(model_dir, REVISION)
