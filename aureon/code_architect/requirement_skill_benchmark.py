"""Fully local benchmark for Aureon's governed requirement-to-skill path.

The benchmark has two operations:

``build``
    Deterministically stage one provider-neutral GUI skill in a caller-owned
    state directory.  RequirementSkillBuilder performs compile, static, and
    simulated validation.  The resulting skill remains VALIDATED, pending an
    explicit approval, and live-disabled.

``verify``
    Read the receipt and skill library back from disk without compiling or
    executing the skill.  Every material artifact is bound to the canonical
    benchmark specification with SHA-256.

The public result and receipt contain lifecycle statuses and hashes only.  No
requirement text, generated source, state path, provider data, or secret value
is emitted.
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
from typing import Any, Mapping, Sequence

from aureon.code_architect.requirement_skill_builder import RequirementSkillBuilder
from aureon.code_architect.skill import Skill, SkillLevel, SkillStatus
from aureon.code_architect.skill_library import SkillLibrary

SCHEMA_VERSION = "aureon-requirement-skill-benchmark-v1"
BENCHMARK_SKILL_NAME = "provider_neutral_sandbox_gui_probe"
RECEIPT_FILE = "requirement_skill_benchmark_receipt.json"

_BENCHMARK_REQUIREMENT = (
    "Create a deterministic provider-neutral sandbox GUI probe using only bounded "
    "mouse, keyboard, and observation primitives."
)
_BENCHMARK_DESCRIPTION = "Exercise bounded observation, pointer, click, and keyboard GUI primitives."
_HEX_64 = re.compile(r"^[0-9a-f]{64}$")
_EXPECTED_STATUSES = {
    "benchmark_status": "validated_pending_approval",
    "skill_status": SkillStatus.VALIDATED.value,
    "approval_status": "pending_explicit_approval",
    "live_execution_status": "disabled",
    "compile_status": "passed",
    "static_status": "passed",
    "simulation_status": "passed",
}
_HASH_FIELDS = {
    "state_dir_sha256",
    "skill_name_sha256",
    "requirement_sha256",
    "plan_sha256",
    "source_sha256",
    "skill_record_sha256",
    "library_sha256",
}
_RECEIPT_KEYS = {"schema_version", *_EXPECTED_STATUSES, *_HASH_FIELDS}


def _benchmark_plan() -> dict[str, Any]:
    """Return a fresh canonical plan; no service or GUI provider is named."""

    return {
        "name": BENCHMARK_SKILL_NAME,
        "description": _BENCHMARK_DESCRIPTION,
        "steps": [
            {"primitive": "screenshot", "params": {}},
            {"primitive": "get_screen_size", "params": {}},
            {"primitive": "mouse_move", "params": {"x": 160, "y": 120}},
            {"primitive": "left_click", "params": {"x": 160, "y": 120}},
            {"primitive": "press_key", "params": {"key": "escape"}},
            {"primitive": "get_cursor_position", "params": {}},
        ],
        "sample_inputs": {},
    }


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_text(value: str) -> str:
    return _sha256_bytes(value.encode("utf-8"))


def _resolve_state_dir(state_dir: str | Path) -> Path:
    value = str(state_dir or "").strip()
    if not value:
        raise ValueError("state_directory_required")
    absolute = Path(os.path.abspath(Path(value).expanduser()))
    if not _path_chain_is_link_free(absolute):
        raise ValueError("state_directory_link_rejected")
    return absolute.resolve()


def _base_expected_hashes(root: Path) -> dict[str, str]:
    plan = _benchmark_plan()
    source = RequirementSkillBuilder._render_source(plan)
    return {
        "state_dir_sha256": _sha256_text(os.path.normcase(str(root))),
        "skill_name_sha256": _sha256_text(BENCHMARK_SKILL_NAME),
        "requirement_sha256": _sha256_text(_BENCHMARK_REQUIREMENT),
        "plan_sha256": _sha256_text(_canonical_json(plan)),
        "source_sha256": _sha256_text(source),
    }


def _expected_skill(base_hashes: Mapping[str, str]) -> Skill:
    return Skill(
        skill_id=base_hashes["source_sha256"][:8],
        name=BENCHMARK_SKILL_NAME,
        description=_BENCHMARK_DESCRIPTION,
        level=SkillLevel.TASK,
        category="requirement_generated",
        code=RequirementSkillBuilder._render_source(_benchmark_plan()),
        entry_function=BENCHMARK_SKILL_NAME,
        params_schema={
            "type": "object",
            "properties": {"session_id": {"type": "string"}},
            "additionalProperties": False,
        },
        dependencies=[],
        created_at=0.0,
        created_by="requirement_skill_builder",
        observation_sources=[f"requirement_sha256:{base_hashes['requirement_sha256']}"],
        status=SkillStatus.VALIDATED,
        target="vm",
        tags=[
            "requirement_generated",
            "requires_explicit_approval",
            "live_execution_disabled",
            f"plan_sha256:{base_hashes['plan_sha256']}",
        ],
    )


def _expected_hashes(root: Path) -> dict[str, str]:
    expected = _base_expected_hashes(root)
    expected["skill_record_sha256"] = _sha256_text(
        _canonical_json(_expected_skill(expected).to_dict())
    )
    return expected


def _path_is_within(root: Path, candidate: Path) -> bool:
    try:
        candidate.resolve().relative_to(root)
        return True
    except (OSError, ValueError):
        return False


def _path_is_link(path: Path) -> bool:
    try:
        is_junction = getattr(path, "is_junction", None)
        return path.is_symlink() or bool(is_junction and is_junction())
    except OSError:
        return True


def _path_chain_is_link_free(path: Path) -> bool:
    for candidate in (path, *path.parents):
        try:
            if candidate.exists() and _path_is_link(candidate):
                return False
        except OSError:
            return False
    return True


def _artifact_paths_are_isolated(root: Path) -> bool:
    skills_dir = root / "skills"
    library_path = skills_dir / SkillLibrary.LIBRARY_FILE
    library_temp_path = library_path.with_suffix(".json.tmp")
    receipt_path = root / RECEIPT_FILE
    candidates = (root, skills_dir, library_path, library_temp_path, receipt_path)
    try:
        return all(
            _path_chain_is_link_free(path) and _path_is_within(root, path)
            for path in candidates
        )
    except OSError:
        return False


def _failure(root: Path, status: str) -> dict[str, Any]:
    return {
        "ok": False,
        "schema_version": SCHEMA_VERSION,
        "operation_status": str(status),
        "benchmark_status": "not_verified",
        "skill_status": "not_verified",
        "approval_status": "not_approved",
        "live_execution_status": "disabled",
        **_expected_hashes(root),
    }


def _atomic_write_receipt(path: Path, receipt: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(dict(receipt), sort_keys=True, indent=2) + "\n").encode("utf-8")
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        for attempt in range(3):
            try:
                os.replace(temp_name, path)
                break
            except PermissionError:
                if attempt == 2:
                    raise
                time.sleep(0.05 * (attempt + 1))
    finally:
        Path(temp_name).unlink(missing_ok=True)


def _public_success(
    receipt: Mapping[str, Any],
    *,
    operation_status: str,
    receipt_sha256: str,
) -> dict[str, Any]:
    return {
        "ok": True,
        "operation_status": operation_status,
        **dict(receipt),
        "receipt_sha256": receipt_sha256,
    }


def _valid_receipt_shape(receipt: Any) -> bool:
    if not isinstance(receipt, dict) or set(receipt) != _RECEIPT_KEYS:
        return False
    if receipt.get("schema_version") != SCHEMA_VERSION:
        return False
    if any(receipt.get(key) != value for key, value in _EXPECTED_STATUSES.items()):
        return False
    return all(isinstance(receipt.get(key), str) and _HEX_64.fullmatch(receipt[key]) for key in _HASH_FIELDS)


def verify_benchmark(state_dir: str | Path) -> dict[str, Any]:
    """Verify the receipt and library by read-back; never execute the skill."""

    try:
        root = _resolve_state_dir(state_dir)
    except Exception:
        root = Path.cwd().resolve()
        return _failure(root, "state_directory_invalid")

    receipt_path = root / RECEIPT_FILE
    library_path = root / "skills" / SkillLibrary.LIBRARY_FILE
    if not _artifact_paths_are_isolated(root):
        return _failure(root, "artifact_path_escape_rejected")
    if not receipt_path.is_file() or not library_path.is_file():
        return _failure(root, "benchmark_artifacts_missing")

    try:
        receipt_bytes = receipt_path.read_bytes()
        receipt = json.loads(receipt_bytes.decode("utf-8"))
    except Exception:
        return _failure(root, "receipt_read_failed")
    if not _artifact_paths_are_isolated(root):
        return _failure(root, "artifact_path_escape_rejected")
    if not _valid_receipt_shape(receipt):
        return _failure(root, "receipt_policy_mismatch")

    expected = _expected_hashes(root)
    if any(receipt.get(key) != value for key, value in expected.items()):
        return _failure(root, "specification_hash_mismatch")

    try:
        library_bytes = library_path.read_bytes()
    except Exception:
        return _failure(root, "library_read_failed")
    if not _artifact_paths_are_isolated(root):
        return _failure(root, "artifact_path_escape_rejected")
    if receipt.get("library_sha256") != _sha256_bytes(library_bytes):
        return _failure(root, "library_hash_mismatch")

    try:
        library_payload = json.loads(library_bytes.decode("utf-8"))
        if (
            not isinstance(library_payload, dict)
            or set(library_payload) != {"version", "saved_at", "count", "skills"}
            or library_payload.get("version") != 1
            or library_payload.get("count") != 1
        ):
            return _failure(root, "library_policy_mismatch")
        records = library_payload.get("skills")
        if not isinstance(records, list) or len(records) != 1 or not isinstance(records[0], dict):
            return _failure(root, "skill_record_mismatch")
        record = records[0]
        expected_record = _expected_skill(expected).to_dict()
        if (
            _sha256_text(_canonical_json(record)) != expected["skill_record_sha256"]
            or _canonical_json(record) != _canonical_json(expected_record)
        ):
            return _failure(root, "skill_record_hash_mismatch")
        skill = Skill.from_dict(record)
    except Exception:
        return _failure(root, "skill_readback_failed")

    policy_ok = (
        skill.status is SkillStatus.VALIDATED
        and skill.created_by == "requirement_skill_builder"
        and skill.category == "requirement_generated"
        and skill.target == "vm"
        and skill.tags == _expected_skill(expected).tags
        and not any(str(tag).startswith("approved_by:") for tag in skill.tags or [])
        and f"requirement_sha256:{expected['requirement_sha256']}" in skill.observation_sources
        and _sha256_text(skill.code) == expected["source_sha256"]
    )
    if not policy_ok:
        return _failure(root, "skill_policy_mismatch")

    return _public_success(
        receipt,
        operation_status="verified_readback",
        receipt_sha256=_sha256_bytes(receipt_bytes),
    )


def build_benchmark(state_dir: str | Path) -> dict[str, Any]:
    """Build and validate the canonical skill without approving or running it live."""

    try:
        root = _resolve_state_dir(state_dir)
    except Exception:
        root = Path.cwd().resolve()
        return _failure(root, "state_directory_invalid")

    receipt_path = root / RECEIPT_FILE
    library_path = root / "skills" / SkillLibrary.LIBRARY_FILE
    if root.exists():
        return _failure(root, "state_directory_already_exists")
    if not root.parent.is_dir() or not _path_chain_is_link_free(root.parent):
        return _failure(root, "state_directory_parent_invalid")

    try:
        root.mkdir(exist_ok=False)
        if not _artifact_paths_are_isolated(root):
            return _failure(root, "artifact_path_escape_rejected")
        (root / "skills").mkdir(exist_ok=False)
        if not _artifact_paths_are_isolated(root):
            return _failure(root, "artifact_path_escape_rejected")
        library = SkillLibrary(storage_dir=root / "skills")
        builder = RequirementSkillBuilder(library=library)
        result = builder.build(_BENCHMARK_REQUIREMENT, plan=_benchmark_plan())
    except Exception:
        return _failure(root, "local_build_failed")
    if result.get("ok") is not True or result.get("status") != "validated_pending_approval":
        return _failure(root, "governed_build_rejected")
    if not _artifact_paths_are_isolated(root):
        return _failure(root, "artifact_path_escape_rejected")

    expected = _expected_hashes(root)
    validation = result.get("validation") if isinstance(result.get("validation"), dict) else {}
    skill = library.get(BENCHMARK_SKILL_NAME)
    if (
        skill is None
        or skill.status is not SkillStatus.VALIDATED
        or "requires_explicit_approval" not in skill.tags
        or "live_execution_disabled" not in skill.tags
        or result.get("plan_digest") != expected["plan_sha256"]
        or result.get("source_digest") != expected["source_sha256"]
        or validation.get("compile_ok") is not True
        or validation.get("static_safe") is not True
        or validation.get("simulation_ok") is not True
    ):
        return _failure(root, "post_build_policy_mismatch")

    canonical_skill = _expected_skill(expected)
    skill.skill_id = canonical_skill.skill_id
    skill.created_at = canonical_skill.created_at
    committed, _rolled_back, _error = builder._persist_skill_transaction(skill)
    if not committed:
        cleanup = builder.reject_skill(
            BENCHMARK_SKILL_NAME,
            reviewer="aureon:requirement_skill_benchmark",
            reason="canonical_skill_persist_failed",
        )
        status = "canonical_skill_persist_failed_rolled_back" if cleanup.get("ok") else "canonical_skill_persist_failed"
        return _failure(root, status)
    if not _artifact_paths_are_isolated(root):
        return _failure(root, "artifact_path_escape_rejected")

    try:
        library_bytes = library_path.read_bytes()
        library_payload = json.loads(library_bytes.decode("utf-8"))
        records = library_payload.get("skills", []) if isinstance(library_payload, dict) else []
        if (
            not isinstance(records, list)
            or len(records) != 1
            or _canonical_json(records[0]) != _canonical_json(canonical_skill.to_dict())
        ):
            return _failure(root, "canonical_skill_persist_failed")
        library_sha256 = _sha256_bytes(library_bytes)
    except Exception:
        return _failure(root, "library_read_after_build_failed")
    receipt = {
        "schema_version": SCHEMA_VERSION,
        **_EXPECTED_STATUSES,
        **expected,
        "library_sha256": library_sha256,
    }
    try:
        _atomic_write_receipt(receipt_path, receipt)
    except Exception as exc:
        cleanup = builder.reject_skill(
            BENCHMARK_SKILL_NAME,
            reviewer="aureon:requirement_skill_benchmark",
            reason="receipt_write_failed",
        )
        exception_status = re.sub(r"[^a-z0-9]+", "_", type(exc).__name__.casefold()).strip("_")
        status = f"receipt_write_failed_{exception_status}"
        if cleanup.get("ok"):
            status += "_rolled_back"
        return _failure(root, status)
    if not _artifact_paths_are_isolated(root):
        return _failure(root, "artifact_path_escape_rejected")

    verified = verify_benchmark(root)
    if verified.get("ok") is not True:
        return verified
    verified["operation_status"] = "built_and_verified"
    return verified


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Aureon's fully local requirement-skill benchmark.")
    subparsers = parser.add_subparsers(dest="operation", required=True)
    for operation in ("build", "verify"):
        command = subparsers.add_parser(operation)
        command.add_argument("--state-dir", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    result = (
        build_benchmark(args.state_dir)
        if args.operation == "build"
        else verify_benchmark(args.state_dir)
    )
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if result.get("ok") is True else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = [
    "BENCHMARK_SKILL_NAME",
    "RECEIPT_FILE",
    "SCHEMA_VERSION",
    "build_benchmark",
    "main",
    "verify_benchmark",
]
