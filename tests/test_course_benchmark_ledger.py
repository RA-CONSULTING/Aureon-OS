from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aureon.operator.course_benchmark_ledger import (
    GENESIS_HASH,
    CourseBenchmarkLedger,
    LedgerIntegrityError,
    verify_ledger,
)

FIXED_NOW = datetime(2026, 8, 16, 12, 0, 0, tzinfo=UTC)


def _ledger(path: Path) -> CourseBenchmarkLedger:
    return CourseBenchmarkLedger(
        path,
        actor="aureon-test-operator",
        runtime_id="runtime-local-test",
        build_id="build-deadbeef",
        run_id="run-authorized-sandbox",
        now=lambda: FIXED_NOW,
    )


def _transition(*, typed_text: str | None = None, text_class: str = "ordinary") -> dict[str, object]:
    params: dict[str, object]
    action_name: str
    if typed_text is None:
        action_name = "left_click"
        params = {"x": 10, "y": 20}
    else:
        action_name = "type_text"
        params = {"text": typed_text, "text_class": text_class}
    return {
        "step": 1,
        "before_sha256": hashlib.sha256(b"before").hexdigest(),
        "after_sha256": hashlib.sha256(b"after").hexdigest(),
        "action": {"name": action_name, "params": params},
        "result": {"ok": True, "code": "executed"},
        "screen_changed": True,
        "observation_fresh": True,
        "verified": True,
    }


def test_ledger_appends_hash_chained_newline_terminated_jsonl(tmp_path: Path):
    path = tmp_path / "course-ledger.jsonl"
    ledger = _ledger(path)

    first = ledger.record_transition(_transition())
    second = ledger.record_terminal(
        status="completed",
        reason="Sandbox provider completion marker verified",
        verified_changed_transitions=1,
        success_predicate={"kind": "ocr_contains", "value": "Course complete"},
    )

    assert first["previous_hash"] == GENESIS_HASH
    assert second["previous_hash"] == first["entry_hash"]
    assert path.read_bytes().endswith(b"\n")
    verified = verify_ledger(path)
    assert [entry["sequence"] for entry in verified] == [1, 2]
    assert all(entry["actor"] == "aureon-test-operator" for entry in verified)
    assert all(entry["runtime_id"] == "runtime-local-test" for entry in verified)
    assert all(entry["build_id"] == "build-deadbeef" for entry in verified)


def test_reopening_valid_chain_continues_sequence_instead_of_rewriting(tmp_path: Path):
    path = tmp_path / "course-ledger.jsonl"
    first_ledger = _ledger(path)
    first = first_ledger.record_transition(_transition())
    bytes_before = path.read_bytes()

    reopened = _ledger(path)
    second = reopened.append("checkpoint", {"status": "still_running"})

    assert path.read_bytes().startswith(bytes_before)
    assert second["sequence"] == 2
    assert second["previous_hash"] == first["entry_hash"]
    assert len(verify_ledger(path)) == 2


def test_reopen_rejects_cross_run_identity_mixing(tmp_path: Path):
    path = tmp_path / "identity-bound.jsonl"
    _ledger(path).append("checkpoint", {"status": "running"})

    with pytest.raises(LedgerIntegrityError, match="run_id"):
        CourseBenchmarkLedger(
            path,
            actor="aureon-test-operator",
            runtime_id="runtime-local-test",
            build_id="build-deadbeef",
            run_id="different-run",
            now=lambda: FIXED_NOW,
        )


@pytest.mark.parametrize("text_class", ["credential", "assessment_answer"])
def test_typed_credentials_and_answers_are_never_written_in_plaintext(
    tmp_path: Path,
    text_class: str,
):
    path = tmp_path / "redacted.jsonl"
    secret = "do-not-write-this-answer-or-password"
    _ledger(path).record_transition(_transition(typed_text=secret, text_class=text_class))

    raw = path.read_text(encoding="utf-8")
    entry = json.loads(raw)
    params = entry["payload"]["action"]["params"]
    assert secret not in raw
    assert params["text"] == "[REDACTED:TYPED_TEXT]"
    assert params["text_length"] == len(secret)
    assert params["redacted"] is True


def test_sensitive_answer_fields_are_recursively_redacted(tmp_path: Path):
    path = tmp_path / "redacted-answer.jsonl"
    answer = "private quiz selection"
    _ledger(path).append(
        "planner_note",
        {"nested": {"answer": answer, "quiz_answer": answer}, "safe": "kept"},
    )
    raw = path.read_text(encoding="utf-8")
    assert answer not in raw
    payload = json.loads(raw)["payload"]
    assert payload["nested"]["answer"] == "[REDACTED:SENSITIVE]"
    assert payload["safe"] == "kept"


def test_model_authored_predicate_text_is_hash_only_in_ledger(tmp_path: Path):
    path = tmp_path / "redacted-predicate.jsonl"
    visible_text = "Potentially personal provider screen content"
    entry = _ledger(path).record_terminal(
        status="completion_rejected",
        reason="predicate failed",
        verified_changed_transitions=0,
        success_predicate={"kind": "vision_contains", "value": visible_text},
    )

    raw = path.read_text(encoding="utf-8")
    predicate = entry["payload"]["success_predicate"]
    assert visible_text not in raw
    assert predicate["value"] == "[REDACTED:PREDICATE_TEXT]"
    assert predicate["value_sha256"] == hashlib.sha256(visible_text.encode()).hexdigest()
    assert predicate["value_length"] == len(visible_text)


def test_tampering_breaks_hash_verification_and_blocks_reopen(tmp_path: Path):
    path = tmp_path / "tampered.jsonl"
    _ledger(path).append("checkpoint", {"status": "original"})
    original = path.read_text(encoding="utf-8")
    path.write_text(original.replace("original", "tampered"), encoding="utf-8", newline="\n")

    with pytest.raises(LedgerIntegrityError, match="hash does not match"):
        verify_ledger(path)
    with pytest.raises(LedgerIntegrityError):
        _ledger(path)


def test_completed_terminal_record_requires_predicate_and_changed_state(tmp_path: Path):
    ledger = _ledger(tmp_path / "terminal.jsonl")
    with pytest.raises(ValueError, match="success predicate"):
        ledger.record_terminal(
            status="completed",
            reason="unsupported",
            verified_changed_transitions=1,
        )
    with pytest.raises(ValueError, match="changed-state"):
        ledger.record_terminal(
            status="completed",
            reason="unsupported",
            verified_changed_transitions=0,
            success_predicate={"kind": "ocr_contains", "value": "Complete"},
        )
    assert not ledger.path.exists()


@pytest.mark.parametrize("artifact_kind", ["certificate", "download"])
@pytest.mark.parametrize(
    "authorization_label",
    ["sandbox_test", "provider_authorized_test"],
)
def test_artifact_proof_hashes_real_nonempty_authorized_local_file(
    tmp_path: Path,
    artifact_kind: str,
    authorization_label: str,
):
    artifact = tmp_path / "certificate.pdf"
    artifact.write_bytes(b"authorized sandbox certificate bytes")
    ledger = _ledger(tmp_path / "artifact-ledger.jsonl")

    entry = ledger.record_artifact_proof(
        artifact,
        artifact_kind=artifact_kind,
        authorization_label=authorization_label,
        provider="sandbox-course-provider",
    )

    payload = entry["payload"]
    assert payload["authorization_label"] == authorization_label
    assert payload["proof_status"] == "verified_authorized_local_file"
    assert payload["sha256"] == hashlib.sha256(artifact.read_bytes()).hexdigest()
    assert payload["size_bytes"] == artifact.stat().st_size
    assert Path(payload["local_path"]).resolve() == artifact.resolve()
    assert verify_ledger(ledger.path)[0]["entry_hash"] == entry["entry_hash"]


def test_artifact_proof_rejects_runtime_only_owner_benchmark_label(
    tmp_path: Path,
) -> None:
    artifact = tmp_path / "certificate.pdf"
    artifact.write_bytes(b"owner benchmark certificate bytes")
    ledger = _ledger(tmp_path / "artifact-ledger.jsonl")

    with pytest.raises(ValueError, match="authorization_label"):
        ledger.record_artifact_proof(
            artifact,
            artifact_kind="certificate",
            authorization_label="owner_benchmark_test",
            provider="owner-authorized-benchmark",
        )

    assert not ledger.path.exists()


def test_artifact_proof_rejects_missing_empty_or_unlabelled_files(tmp_path: Path):
    ledger = _ledger(tmp_path / "artifact-ledger.jsonl")
    missing = tmp_path / "missing.pdf"
    with pytest.raises(FileNotFoundError):
        ledger.record_artifact_proof(
            missing,
            artifact_kind="certificate",
            authorization_label="sandbox_test",
            provider="sandbox",
        )

    empty = tmp_path / "empty.pdf"
    empty.write_bytes(b"")
    with pytest.raises(ValueError, match="non-empty"):
        ledger.record_artifact_proof(
            empty,
            artifact_kind="certificate",
            authorization_label="sandbox_test",
            provider="sandbox",
        )

    actual = tmp_path / "actual.pdf"
    actual.write_bytes(b"content")
    with pytest.raises(ValueError, match="authorization_label"):
        ledger.record_artifact_proof(
            actual,
            artifact_kind="certificate",
            authorization_label="unverified",
            provider="sandbox",
        )
    assert not ledger.path.exists()


def test_transition_requires_real_before_after_hashes_and_result_shape(tmp_path: Path):
    ledger = _ledger(tmp_path / "invalid-transition.jsonl")
    with pytest.raises(ValueError, match="before_sha256"):
        ledger.record_transition(
            {
                "before_sha256": "not-a-hash",
                "after_sha256": hashlib.sha256(b"after").hexdigest(),
                "action": {"name": "left_click", "params": {"x": 1, "y": 2}},
                "result": {"ok": True},
            }
        )
    assert not ledger.path.exists()
