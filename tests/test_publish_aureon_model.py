"""Offline safety tests for the canonical Aureon model publisher."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from huggingface import publish_aureon_model as publisher

WEIGHT = b"canonical-weight"
REVISION_ZERO = "0" * 40


def test_isambard_defaults_select_the_complete_reviewed_overlay() -> None:
    assert Path(
        "/projects/u6vs/hnc-organism/runs/aureon-7b-sft-label-fix/hf"
    ) == publisher.CANONICAL_SOURCE
    assert Path("/projects/u6vs/aureon-hf-release/model-overlay") == publisher.DEFAULT_OVERLAY
    document = (Path(__file__).parents[1] / "huggingface" / "PUBLISH.md").read_text(encoding="utf-8")
    assert document.count(
        "--overlay /projects/u6vs/aureon-hf-release/model-overlay"
    ) == 3


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git_blob(data: bytes) -> str:
    digest = hashlib.sha1()
    digest.update(f"blob {len(data)}\0".encode("ascii"))
    digest.update(data)
    return digest.hexdigest()


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def _entry(path: str, data: bytes, *, lfs: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        path=path,
        type="file",
        size=len(data),
        blob_id="git-lfs-pointer" if lfs else _git_blob(data),
        lfs={"oid": _sha256(data), "size": len(data)} if lfs else None,
    )


class FakeOperation:
    def __init__(self, *, path_in_repo: str, path_or_fileobj: Path):
        self.path_in_repo = path_in_repo
        self.path_or_fileobj = path_or_fileobj


class FakeHub:
    def __init__(self) -> None:
        self.remote: dict[str, SimpleNamespace] = {}
        self.revision = REVISION_ZERO
        self.private = True
        self.commits: list[list[str]] = []
        self.create_calls: list[dict[str, Any]] = []
        self.visibility_calls: list[bool] = []
        self.drop_after_commit: str | None = None

    def create_repo(self, repo_id: str, **kwargs: Any) -> None:
        assert repo_id == publisher.MODEL_REPOSITORY
        self.create_calls.append(kwargs)

    def repo_info(self, repo_id: str, **kwargs: Any) -> SimpleNamespace:
        assert repo_id == publisher.MODEL_REPOSITORY
        assert kwargs == {"repo_type": "model"}
        return SimpleNamespace(sha=self.revision, private=self.private)

    def list_repo_tree(self, repo_id: str, **kwargs: Any) -> list[SimpleNamespace]:
        assert repo_id == publisher.MODEL_REPOSITORY
        assert kwargs["repo_type"] == "model"
        assert kwargs["recursive"] is True
        assert kwargs["expand"] is True
        if "revision" in kwargs:
            assert kwargs["revision"] == self.revision
        return list(self.remote.values())

    def create_commit(self, *, repo_id: str, operations: list[FakeOperation], **kwargs: Any):
        assert repo_id == publisher.MODEL_REPOSITORY
        assert kwargs["repo_type"] == "model"
        self.commits.append([operation.path_in_repo for operation in operations])
        for operation in operations:
            assert operation.path_in_repo in publisher.ALLOWED_FILES
            data = operation.path_or_fileobj.read_bytes()
            self.remote[operation.path_in_repo] = _entry(
                operation.path_in_repo,
                data,
                lfs=operation.path_in_repo == "model.safetensors",
            )
        if self.drop_after_commit:
            self.remote.pop(self.drop_after_commit, None)
        self.revision = f"{len(self.commits):040x}"
        return SimpleNamespace(oid=self.revision)

    def update_repo_visibility(self, repo_id: str, *, private: bool, repo_type: str) -> None:
        assert repo_id == publisher.MODEL_REPOSITORY
        assert repo_type == "model"
        self.private = private
        self.visibility_calls.append(private)

    def seed(self, path: str, data: bytes) -> None:
        self.remote[path] = _entry(path, data, lfs=path == "model.safetensors")


@pytest.fixture(autouse=True)
def tiny_weight_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(publisher, "EXPECTED_WEIGHT_SIZE", len(WEIGHT))
    monkeypatch.setattr(publisher, "EXPECTED_WEIGHT_SHA256", _sha256(WEIGHT))


@pytest.fixture
def candidate(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "source"
    overlay = tmp_path / "overlay"
    source.mkdir()
    overlay.mkdir()
    (source / "model.safetensors").write_bytes(WEIGHT)
    documents = {
        "config.json": {"vocab_size": 65_536, "eos_token_id": 1, "bos_token_id": 1},
        "generation_config.json": {"eos_token_id": 1, "bos_token_id": 1},
        "tokenizer.json": {"model": {"type": "BPE", "vocab": {"<eos>": 1}}},
        "tokenizer_config.json": {"eos_token": "<eos>"},
        "aureon_export.json": {"model_name": "aureon-7b"},
        "preparation_receipt.json": {
            "source_hashes": {"model.safetensors": _sha256(WEIGHT)},
        },
        "evaluation_summary.json": {"model": publisher.MODEL_REPOSITORY},
    }
    for name, value in documents.items():
        _write_json(overlay / name, value)
    (overlay / "README.md").write_text("# Aureon 7B\n", encoding="utf-8")
    return source, overlay


def _publish(
    source: Path,
    overlay: Path,
    hub: FakeHub,
    receipt: Path,
) -> dict[str, Any]:
    return publisher.publish_model(
        source,
        overlay,
        api=hub,
        commit_operation_add=FakeOperation,
        acknowledge_execution=publisher.EXECUTION_ACK,
        receipt_path=receipt,
    )


def test_dry_run_is_safe_exact_allowlist_and_does_not_import_hub(
    candidate: tuple[Path, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, overlay = candidate
    (source / "unapproved.safetensors").write_bytes(b"not a release candidate")
    (overlay / "unexpected.py").write_text("raise RuntimeError\n", encoding="utf-8")
    monkeypatch.setenv("HF_TOKEN", "not-for-manifest")

    def unexpected_import(_name: str):
        raise AssertionError("dry-run must not import huggingface_hub")

    monkeypatch.setattr(publisher.importlib, "import_module", unexpected_import)
    manifest = publisher.dry_run(source, overlay)

    assert manifest["dry_run"] is True
    assert manifest["repository"] == "GaryLeckey/aureon-7b"
    assert manifest["staging_visibility"] == "private"
    assert manifest["weight_staged_locally"] is False
    assert [item["path"] for item in manifest["files"]] == list(publisher.MODEL_FILES)
    assert "unexpected.py" not in json.dumps(manifest)
    assert "unapproved.safetensors" not in json.dumps(manifest)
    assert str(tmp_path) not in json.dumps(manifest)
    assert "not-for-manifest" not in json.dumps(manifest)
    assert manifest["files"][4]["size_bytes"] == len(WEIGHT)


@pytest.mark.parametrize("failure", ["size", "SHA-256"])
def test_weight_size_and_hash_refusal_happen_before_any_remote_or_receipt_write(
    candidate: tuple[Path, Path], tmp_path: Path, failure: str
) -> None:
    source, overlay = candidate
    changed = b"wrong-length" if failure == "size" else b"different-weight"
    assert (failure == "size") == (len(changed) != len(WEIGHT))
    (source / "model.safetensors").write_bytes(changed)
    hub = FakeHub()
    receipt = tmp_path / "receipt.json"

    with pytest.raises(publisher.PublicationError, match=failure):
        _publish(source, overlay, hub, receipt)

    assert hub.create_calls == []
    assert hub.commits == []
    assert not receipt.exists()


@pytest.mark.parametrize(
    ("name", "value", "message"),
    [
        ("config.json", {"vocab_size": 32_000, "eos_token_id": 1, "bos_token_id": 1}, "vocabulary"),
        ("config.json", {"vocab_size": 65_536, "eos_token_id": 2, "bos_token_id": 1}, "EOS/BOS"),
        (
            "preparation_receipt.json",
            {"source_hashes": {"model.safetensors": "0" * 64}},
            "different source weight",
        ),
    ],
)
def test_overlay_identity_matches_bootstrap_checks(
    candidate: tuple[Path, Path], name: str, value: dict, message: str
) -> None:
    source, overlay = candidate
    _write_json(overlay / name, value)

    with pytest.raises(publisher.PublicationError, match=message):
        publisher.build_plan(source, overlay)


def test_execution_ack_and_token_are_independent_required_gates(
    candidate: tuple[Path, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source, overlay = candidate
    receipt = tmp_path / "receipt.json"
    monkeypatch.delenv("HF_TOKEN", raising=False)
    monkeypatch.delenv("HUGGING_FACE_HUB_TOKEN", raising=False)
    base = ["--source", str(source), "--overlay", str(overlay), "--execute", "--receipt", str(receipt)]

    assert publisher.main(base) == 1
    assert "execution requires acknowledgement" in capsys.readouterr().out
    assert not receipt.exists()

    assert publisher.main([*base, "--acknowledge-execution", publisher.EXECUTION_ACK]) == 1
    assert "HF_TOKEN or HUGGING_FACE_HUB_TOKEN is required" in capsys.readouterr().out
    assert not receipt.exists()


def test_execution_errors_redact_raw_and_trimmed_environment_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HF_TOKEN", "  hf_test_secret  ")
    monkeypatch.setenv("HUGGING_FACE_HUB_TOKEN", "hf_other_secret")

    message = publisher._safe_error(
        RuntimeError("failed hf_test_secret and hf_other_secret"),
        execution=True,
    )

    assert "hf_test_secret" not in message
    assert "hf_other_secret" not in message
    assert message.count("[redacted]") == 2


def test_publish_uses_exact_repo_private_commit_and_exact_revision_receipt(
    candidate: tuple[Path, Path], tmp_path: Path
) -> None:
    source, overlay = candidate
    hub = FakeHub()
    receipt_path = tmp_path / "output" / "receipt.json"

    receipt = _publish(source, overlay, hub, receipt_path)

    assert hub.create_calls == [
        {"repo_type": "model", "private": True, "exist_ok": True},
    ]
    assert hub.commits == [list(publisher.MODEL_FILES)]
    assert hub.visibility_calls == []
    assert receipt["repository"] == publisher.MODEL_REPOSITORY
    assert receipt["revision"] == f"{1:040x}"
    assert receipt["visibility"] == "private"
    assert receipt["uploaded_files"] == list(publisher.MODEL_FILES)
    assert receipt["skipped_files"] == []
    assert receipt["weight_sha256"] == _sha256(WEIGHT)
    assert receipt["weight_size_bytes"] == len(WEIGHT)
    assert json.loads(receipt_path.read_text(encoding="utf-8")) == receipt
    assert str(tmp_path) not in receipt_path.read_text(encoding="utf-8")


def test_resume_skips_matching_remote_files_and_second_run_skips_all(
    candidate: tuple[Path, Path], tmp_path: Path
) -> None:
    source, overlay = candidate
    hub = FakeHub()
    hub.seed("config.json", (overlay / "config.json").read_bytes())
    receipt = tmp_path / "receipt.json"

    first = _publish(source, overlay, hub, receipt)

    assert first["skipped_files"] == ["config.json"]
    assert first["uploaded_files"] == [
        name for name in publisher.MODEL_FILES if name != "config.json"
    ]
    assert len(hub.commits) == 1

    second = _publish(source, overlay, hub, receipt)

    assert len(hub.commits) == 1
    assert second["revision"] == first["revision"]
    assert second["uploaded_files"] == []
    assert second["skipped_files"] == list(publisher.MODEL_FILES)


def test_preexisting_remote_mismatch_is_not_overwritten(
    candidate: tuple[Path, Path], tmp_path: Path
) -> None:
    source, overlay = candidate
    hub = FakeHub()
    hub.seed("config.json", b"{}")
    receipt = tmp_path / "receipt.json"

    with pytest.raises(publisher.PublicationError, match="mismatch"):
        _publish(source, overlay, hub, receipt)

    assert hub.commits == []
    assert not receipt.exists()
    assert hub.remote["config.json"].size == 2


def test_incomplete_post_commit_reconciliation_fails_without_receipt(
    candidate: tuple[Path, Path], tmp_path: Path
) -> None:
    source, overlay = candidate
    hub = FakeHub()
    hub.drop_after_commit = "README.md"
    receipt = tmp_path / "receipt.json"

    with pytest.raises(publisher.PublicationError, match="incomplete remote upload.*README.md"):
        _publish(source, overlay, hub, receipt)

    assert len(hub.commits) == 1
    assert not receipt.exists()


def test_post_commit_hash_mismatch_fails_without_receipt(
    candidate: tuple[Path, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, overlay = candidate
    hub = FakeHub()
    original_match = publisher._remote_match

    def mismatched_readme(record, entry):
        if record.path == "README.md" and hub.commits:
            return False
        return original_match(record, entry)

    monkeypatch.setattr(publisher, "_remote_match", mismatched_readme)
    receipt = tmp_path / "receipt.json"

    with pytest.raises(publisher.PublicationError, match="mismatch.*README.md"):
        _publish(source, overlay, hub, receipt)

    assert not receipt.exists()


def test_public_visibility_is_separate_and_requires_both_acknowledgements(
    candidate: tuple[Path, Path], tmp_path: Path
) -> None:
    source, overlay = candidate
    hub = FakeHub()
    _publish(source, overlay, hub, tmp_path / "private.json")
    public_receipt = tmp_path / "public.json"

    with pytest.raises(publisher.PublicationError, match="public visibility requires acknowledgement"):
        publisher.make_model_public(
            source,
            overlay,
            api=hub,
            acknowledge_execution=publisher.EXECUTION_ACK,
            acknowledge_public=None,
            receipt_path=public_receipt,
        )
    assert hub.visibility_calls == []
    assert not public_receipt.exists()

    result = publisher.make_model_public(
        source,
        overlay,
        api=hub,
        acknowledge_execution=publisher.EXECUTION_ACK,
        acknowledge_public=publisher.PUBLIC_ACK,
        receipt_path=public_receipt,
    )

    assert hub.visibility_calls == [False]
    assert len(hub.commits) == 1
    assert result["visibility"] == "public"
    assert result["revision"] == f"{1:040x}"
    assert result["uploaded_files"] == []
    assert result["skipped_files"] == list(publisher.MODEL_FILES)


def test_public_visibility_refuses_incomplete_or_mismatched_remote(
    candidate: tuple[Path, Path], tmp_path: Path
) -> None:
    source, overlay = candidate
    hub = FakeHub()
    hub.seed("config.json", b"{}")
    receipt = tmp_path / "public.json"

    with pytest.raises(publisher.PublicationError, match="mismatch"):
        publisher.make_model_public(
            source,
            overlay,
            api=hub,
            acknowledge_execution=publisher.EXECUTION_ACK,
            acknowledge_public=publisher.PUBLIC_ACK,
            receipt_path=receipt,
        )

    assert hub.visibility_calls == []
    assert not receipt.exists()


def test_receipt_cannot_be_written_inside_read_only_inputs(
    candidate: tuple[Path, Path],
) -> None:
    source, overlay = candidate
    hub = FakeHub()

    with pytest.raises(publisher.PublicationError, match="outside source and overlay"):
        _publish(source, overlay, hub, source / "receipt.json")

    assert hub.create_calls == []
    assert not (source / "receipt.json").exists()


def test_unexpected_remote_file_blocks_upload_and_public_visibility(
    candidate: tuple[Path, Path], tmp_path: Path
) -> None:
    source, overlay = candidate
    hub = FakeHub()
    hub.seed("unexpected.txt", b"requires review")

    with pytest.raises(publisher.PublicationError, match="unexpected remote model files"):
        _publish(source, overlay, hub, tmp_path / "private.json")

    assert hub.commits == []
    assert hub.visibility_calls == []


def test_overlay_secret_is_refused_without_echoing_value(
    candidate: tuple[Path, Path]
) -> None:
    source, overlay = candidate
    secret = "hf_" + "s" * 32
    (overlay / "README.md").write_text(f"do not publish {secret}\n", encoding="utf-8")

    with pytest.raises(publisher.PublicationError, match="Hugging Face token") as caught:
        publisher.build_plan(source, overlay)

    assert secret not in str(caught.value)


def test_conflicting_token_environment_is_refused_before_hub_import(
    monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HF_TOKEN", "first-token")
    monkeypatch.setenv("HUGGING_FACE_HUB_TOKEN", "second-token")

    with pytest.raises(publisher.PublicationError, match="disagree"):
        publisher._api_from_environment()
