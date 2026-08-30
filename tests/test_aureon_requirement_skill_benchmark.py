from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from aureon.code_architect.requirement_skill_benchmark import (
    BENCHMARK_SKILL_NAME,
    RECEIPT_FILE,
    _atomic_write_receipt,
    build_benchmark,
    verify_benchmark,
)
from aureon.code_architect.skill import SkillStatus
from aureon.code_architect.skill_library import SkillLibrary

_HASH_KEY = re.compile(r"sha256$")
_HEX_64 = re.compile(r"^[0-9a-f]{64}$")
_FORBIDDEN_PUBLIC_KEYS = {
    "code",
    "description",
    "library_path",
    "name",
    "path",
    "plan",
    "requirement",
    "source",
    "state_dir",
}


def _assert_hashes_and_statuses_only(result: dict, secret_fragment: str = "") -> None:
    assert not (_FORBIDDEN_PUBLIC_KEYS & set(result))
    for key, value in result.items():
        if _HASH_KEY.search(key):
            assert isinstance(value, str)
            assert _HEX_64.fullmatch(value)
    serialized = json.dumps(result, sort_keys=True)
    if secret_fragment:
        assert secret_fragment not in serialized


def test_build_stages_hash_bound_skill_pending_and_live_disabled(tmp_path: Path) -> None:
    state_dir = tmp_path / "isolated-state"

    result = build_benchmark(state_dir)

    assert result["ok"] is True
    assert result["operation_status"] == "built_and_verified"
    assert result["benchmark_status"] == "validated_pending_approval"
    assert result["skill_status"] == "validated"
    assert result["approval_status"] == "pending_explicit_approval"
    assert result["live_execution_status"] == "disabled"
    assert result["compile_status"] == "passed"
    assert result["static_status"] == "passed"
    assert result["simulation_status"] == "passed"
    _assert_hashes_and_statuses_only(result)

    library = SkillLibrary(storage_dir=state_dir / "skills")
    skill = library.get(BENCHMARK_SKILL_NAME)
    assert skill is not None
    assert skill.status is SkillStatus.VALIDATED
    assert "requires_explicit_approval" in skill.tags
    assert "live_execution_disabled" in skill.tags
    assert not any(tag.startswith("approved_by:") for tag in skill.tags)
    assert "execute_shell" not in skill.code
    assert "execute_powershell" not in skill.code
    assert skill.execution_count == 0

    receipt = json.loads((state_dir / RECEIPT_FILE).read_text(encoding="utf-8"))
    assert "receipt_sha256" not in receipt
    assert "state_dir" not in receipt
    assert "requirement" not in receipt
    assert "code" not in receipt


def test_verify_is_read_only_and_second_build_rejects_existing_state(tmp_path: Path) -> None:
    state_dir = tmp_path / "readback-state"
    built = build_benchmark(state_dir)
    library_path = state_dir / "skills" / SkillLibrary.LIBRARY_FILE
    receipt_path = state_dir / RECEIPT_FILE
    library_before = library_path.read_bytes()
    receipt_before = receipt_path.read_bytes()

    verified = verify_benchmark(state_dir)
    repeated = build_benchmark(state_dir)

    assert verified["ok"] is True
    assert verified["operation_status"] == "verified_readback"
    assert repeated["ok"] is False
    assert repeated["operation_status"] == "state_directory_already_exists"
    assert verified["source_sha256"] == built["source_sha256"]
    assert library_path.read_bytes() == library_before
    assert receipt_path.read_bytes() == receipt_before


def test_verify_detects_library_and_policy_tampering(tmp_path: Path) -> None:
    state_dir = tmp_path / "tamper-state"
    assert build_benchmark(state_dir)["ok"] is True
    library_path = state_dir / "skills" / SkillLibrary.LIBRARY_FILE
    payload = json.loads(library_path.read_text(encoding="utf-8"))
    record = next(item for item in payload["skills"] if item["name"] == BENCHMARK_SKILL_NAME)
    record["status"] = "approved"
    record["tags"].append("approved_by:tamper")
    library_path.write_text(json.dumps(payload), encoding="utf-8")

    result = verify_benchmark(state_dir)

    assert result["ok"] is False
    assert result["operation_status"] == "library_hash_mismatch"
    assert result["approval_status"] == "not_approved"
    assert result["live_execution_status"] == "disabled"
    _assert_hashes_and_statuses_only(result)


def test_verify_rejects_coordinated_receipt_and_extra_skill_tampering(tmp_path: Path) -> None:
    state_dir = tmp_path / "coordinated-tamper-state"
    assert build_benchmark(state_dir)["ok"] is True
    library_path = state_dir / "skills" / SkillLibrary.LIBRARY_FILE
    receipt_path = state_dir / RECEIPT_FILE
    payload = json.loads(library_path.read_text(encoding="utf-8"))
    extra = dict(payload["skills"][0])
    extra["name"] = "unexpected_approved_skill"
    extra["status"] = "approved"
    payload["skills"].append(extra)
    payload["count"] = 2
    library_path.write_text(json.dumps(payload), encoding="utf-8")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["library_sha256"] = hashlib.sha256(library_path.read_bytes()).hexdigest()
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    result = verify_benchmark(state_dir)

    assert result["ok"] is False
    assert result["operation_status"] == "library_policy_mismatch"
    assert result["approval_status"] == "not_approved"


def test_verify_binds_every_material_skill_record_field(tmp_path: Path) -> None:
    state_dir = tmp_path / "record-tamper-state"
    assert build_benchmark(state_dir)["ok"] is True
    library_path = state_dir / "skills" / SkillLibrary.LIBRARY_FILE
    receipt_path = state_dir / RECEIPT_FILE
    payload = json.loads(library_path.read_text(encoding="utf-8"))
    payload["skills"][0]["entry_function"] = "different_entry_function"
    library_path.write_text(json.dumps(payload), encoding="utf-8")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["library_sha256"] = hashlib.sha256(library_path.read_bytes()).hexdigest()
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    result = verify_benchmark(state_dir)

    assert result["ok"] is False
    assert result["operation_status"] == "skill_record_hash_mismatch"
    assert result["skill_status"] == "not_verified"


def test_verify_detects_receipt_status_tampering(tmp_path: Path) -> None:
    state_dir = tmp_path / "receipt-tamper-state"
    assert build_benchmark(state_dir)["ok"] is True
    receipt_path = state_dir / RECEIPT_FILE
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["approval_status"] = "approved"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    result = verify_benchmark(state_dir)

    assert result["ok"] is False
    assert result["operation_status"] == "receipt_policy_mismatch"
    assert result["approval_status"] == "not_approved"
    assert result["live_execution_status"] == "disabled"


def test_module_cli_emits_one_secret_free_json_result_for_build_and_verify(tmp_path: Path) -> None:
    secret_fragment = "private-password-state-name"
    state_dir = tmp_path / secret_fragment
    repo_root = Path(__file__).resolve().parents[1]

    build_process = subprocess.run(
        [
            sys.executable,
            "-m",
            "aureon.code_architect.requirement_skill_benchmark",
            "build",
            "--state-dir",
            str(state_dir),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert build_process.stderr == ""
    assert len(build_process.stdout.strip().splitlines()) == 1
    built = json.loads(build_process.stdout)
    assert build_process.returncode == 0, built["operation_status"]
    assert built["operation_status"] == "built_and_verified"
    _assert_hashes_and_statuses_only(built, secret_fragment)

    verify_process = subprocess.run(
        [
            sys.executable,
            "-m",
            "aureon.code_architect.requirement_skill_benchmark",
            "verify",
            "--state-dir",
            str(state_dir),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert verify_process.returncode == 0
    assert verify_process.stderr == ""
    assert len(verify_process.stdout.strip().splitlines()) == 1
    verified = json.loads(verify_process.stdout)
    assert verified["operation_status"] == "verified_readback"
    _assert_hashes_and_statuses_only(verified, secret_fragment)


def test_verify_missing_artifacts_returns_only_hashes_and_status(tmp_path: Path) -> None:
    state_dir = tmp_path / "missing-state"

    result = verify_benchmark(state_dir)

    assert result["ok"] is False
    assert result["operation_status"] == "benchmark_artifacts_missing"
    assert not state_dir.exists()
    _assert_hashes_and_statuses_only(result)


def test_verify_rejects_nested_skills_link_that_escapes_state_directory(tmp_path: Path) -> None:
    state_dir = tmp_path / "linked-state"
    outside = tmp_path / "outside"
    state_dir.mkdir()
    outside.mkdir()
    try:
        os.symlink(outside, state_dir / "skills", target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlink unavailable: {type(exc).__name__}")

    result = verify_benchmark(state_dir)

    assert result["ok"] is False
    assert result["operation_status"] == "artifact_path_escape_rejected"
    assert not (outside / SkillLibrary.LIBRARY_FILE).exists()


def test_build_rejects_preexisting_state_with_predictable_library_temp_link(tmp_path: Path) -> None:
    state_dir = tmp_path / "preseeded-state"
    skills_dir = state_dir / "skills"
    outside = tmp_path / "outside-sentinel.json"
    skills_dir.mkdir(parents=True)
    outside.write_text("sentinel", encoding="utf-8")
    try:
        os.symlink(outside, skills_dir / "skill_library.json.tmp")
    except OSError as exc:
        pytest.skip(f"file symlink unavailable: {type(exc).__name__}")

    result = build_benchmark(state_dir)

    assert result["ok"] is False
    assert result["operation_status"] == "state_directory_already_exists"
    assert outside.read_text(encoding="utf-8") == "sentinel"


def test_atomic_receipt_write_retries_transient_windows_permission_error(
    tmp_path: Path,
    monkeypatch,
) -> None:
    path = tmp_path / "receipt.json"
    real_replace = os.replace
    attempts = 0

    def transient_replace(source, target) -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise PermissionError("transient file lock")
        real_replace(source, target)

    monkeypatch.setattr(os, "replace", transient_replace)

    _atomic_write_receipt(path, {"benchmark_status": "test"})

    assert attempts == 2
    assert json.loads(path.read_text(encoding="utf-8")) == {"benchmark_status": "test"}
