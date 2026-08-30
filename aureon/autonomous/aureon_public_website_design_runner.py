"""Resumable, source-bound delivery runner for staged Aureon website candidates.

This runner is deliberately a *candidate* orchestrator.  It derives one
exact route and allow-list from a passing Design Evidence Brief, consumes the
existing reconciliation and staged-candidate controls, and writes immutable
local receipts.  It never mutates ``website/``, promotes a candidate, builds a
package, accesses credentials, backs up hosting, owner-gates, or deploys.

The terminal success state is ``awaiting-owner-promotion``.  It is evidence
that a staged candidate has passed its bounded local controls and named visual
review; it is not a permission to make the candidate canonical or live.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import threading
import time
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence, cast

from aureon.operator import design_candidate_test_evidence as _test_evidence_module
from aureon.operator import design_motion_performance_budget as _motion_budget_module
from aureon.operator import secure_immutable_artifact as _secure_immutable_artifact_module
from aureon.operator.design_candidate_control import (
    CANDIDATE_SCHEMA,
    CONTROLLED_BINARY_EXTENSIONS,
    CONTROLLED_TEXT_EXTENSIONS,
    DEFAULT_CANDIDATE_ROOT,
    TRUSTED_EDITORIAL_IMPORT_EXTENSIONS,
    DesignCandidateControlError,
    create_design_work_order,
    stage_design_candidate,
    validate_design_candidate,
    verify_design_work_order,
    verify_staged_candidate_receipt,
    write_design_candidate_receipt,
    write_design_work_order,
)
from aureon.operator.design_candidate_initial_gate import (
    INITIAL_GATE_SCHEMA,
    DesignCandidateInitialGateError,
    evaluate_initial_candidate_gate,
    write_initial_candidate_gate,
)
from aureon.operator.design_candidate_test_evidence import (
    DesignCandidateTestEvidenceError,
    execute_candidate_test_evidence,
    verify_candidate_test_evidence_receipt,
    write_candidate_test_evidence_receipt,
)
from aureon.operator.design_candidate_visual_review import (
    VISUAL_REVIEW_SCHEMA,
    DesignCandidateVisualReviewError,
    validate_candidate_visual_review,
    write_candidate_visual_review,
)
from aureon.operator.design_editorial_asset_candidate_importer import (
    DEFAULT_RECEIPT_NAME as EDITORIAL_IMPORT_RECEIPT_NAME,
)
from aureon.operator.design_editorial_asset_candidate_importer import (
    DesignEditorialAssetCandidateImporterError,
    import_editorial_assets_to_candidate,
    verify_candidate_editorial_asset_import,
)
from aureon.operator.design_editorial_asset_provenance import (
    DesignEditorialAssetProvenanceError,
    audit_design_editorial_asset_provenance_file,
)
from aureon.operator.design_evidence_brief import (
    AUDIT_SCHEMA as BRIEF_AUDIT_SCHEMA,
)
from aureon.operator.design_evidence_brief import (
    DesignEvidenceBriefError,
    audit_design_evidence_brief_file,
)
from aureon.operator.design_investor_copy_repair import (
    CONTRACT_SCHEMA as INVESTOR_COPY_REPAIR_CONTRACT_SCHEMA,
)
from aureon.operator.design_investor_copy_repair import (
    DEFAULT_CONTRACT_ROOT as INVESTOR_COPY_REPAIR_ROOT,
)
from aureon.operator.design_investor_copy_repair import (
    EVALUATION_SCHEMA as INVESTOR_COPY_REPAIR_EVALUATION_SCHEMA,
)
from aureon.operator.design_investor_copy_repair import (
    InvestorCopyRepairError,
    create_investor_copy_repair_contract,
    evaluate_investor_copy_repair_candidate,
    preflight_investor_copy_repair_contract,
    preflight_investor_copy_repair_work_order,
    verify_investor_copy_repair_contract,
    write_investor_copy_repair_contract,
)
from aureon.operator.design_motion_performance_budget import (
    DesignMotionPerformanceBudgetError,
    audit_motion_performance_budget,
    snapshot_static_tree,
    snapshot_static_tree_dual_hash,
    validate_motion_performance_receipt,
)
from aureon.operator.design_research_refresh import DEFAULT_SOURCE_DECLARATION_PATH
from aureon.operator.design_stakeholder_feedback import DEFAULT_FEEDBACK_PATH
from aureon.operator.secure_immutable_artifact import (
    SecureImmutableArtifactError,
    write_new_file,
)

DELIVERY_JOB_SCHEMA = "aureon.public-website-design-delivery-job.v2"
LEGACY_DELIVERY_JOB_SCHEMA = "aureon.public-website-design-delivery-job.v1"
DELIVERY_VERIFICATION_SCHEMA = "aureon.public-website-design-delivery-verification.v2"
CANDIDATE_QA_SCHEMA = "aureon.public-website-design-candidate-qa.v2"
CANDIDATE_QA_CLAIM_SCHEMA = "aureon.public-website-design-candidate-qa-claim.v2"
MOTION_POLICY_COMPILER_VERIFICATION_SCHEMA = "aureon.design-candidate-motion-config-verification.v2"
TEST_POLICY_COMPILER_VERIFICATION_SCHEMA = "aureon.design-candidate-test-policy-verification.v2"
MOTION_POLICY_COMPILER_VERIFICATION_SCOPE = (
    "exact fixed path and bytes, deterministic compiler replay, and motion-control configuration acceptance"
)
TEST_POLICY_COMPILER_VERIFICATION_SCOPE = (
    "exact file bytes plus deterministic compiler replay and test-evidence parser acceptance"
)
TEST_POLICY_COMPILER_DEFERRED_SOURCE_IDS = ("v28-composite-visual-release-gate",)
MOTION_POLICY_COMPILER_DOCTRINE_SHA256 = "BD51BE9B2A8F48BDFE12EDC7A75DF234C0BEDEABE047DD093938ACEA7E289D4D"
COMPILER_SOURCE_POLICY_FILE_SHA256 = "3956D6AACC2B122086D8E2AC1FBB93AB9D01750CAE9B693D2C6DB6148F31741D"
MOTION_POLICY_COMPILER_AUTHORITY = {
    "scope": "fixed local candidate motion-config compilation and replay only",
    "executable_source_ingress": (
        "sealed only by direct compiler-file execution; imported API is drift-check-only"
    ),
    "worker_threshold_selection": "none",
    "audit_execution_authority": "none",
    "canonical_website_mutation": "none",
    "candidate_mutation": "none",
    "candidate_validation_authority": "none",
    "promotion_authority": "none",
    "package_authority": "none",
    "release_authority": "none",
    "deployment_authority": "none",
    "credential_access": "none",
}
TEST_POLICY_COMPILER_AUTHORITY = {
    "scope": "deterministic compilation and replay of one exact local candidate test policy",
    "executable_source_ingress": (
        "sealed only by direct compiler-file execution; imported API is drift-check-only"
    ),
    "worker_command_selection": "none",
    "test_execution_authority": "none",
    "canonical_website_mutation": "none",
    "candidate_validation_authority": "none",
    "promotion_authority": "none",
    "package_authority": "none",
    "release_authority": "none",
    "deployment_authority": "none",
    "credential_access": "none",
    "composite_visual_gate": "deferred-not-passed",
}
SEALED_COMPILER_PYTHON_FLAGS = ("-I", "-S", "-B")
SEALED_COMPILER_TIMEOUT_SECONDS = 300
SEALED_COMPILER_MAX_OUTPUT_BYTES = 64 * 1024
EDITORIAL_AUTHORING_CONTRACT_SCHEMA = "aureon.public-website-editorial-authoring-contract.v1"
INVESTOR_COPY_WORKER_CONTEXT_SCHEMA = "aureon.public-website-investor-copy-worker-context.v1"
DEFAULT_DELIVERY_ROOT = DEFAULT_CANDIDATE_ROOT / "design-delivery-runs"
DEFAULT_WORK_ORDER_ROOT = DEFAULT_CANDIDATE_ROOT / "work-orders"

AUTHORITY = {
    "scope": "local source-bound staged website-candidate delivery orchestration only",
    "canonical_website_mutation": "never by this runner or a design agent",
    "release_eligible": False,
    "package_authority": "none",
    "deployment_authority": "none",
    "credential_access": "none",
    "human_visual_acceptance": "required for material brand changes",
    "release_authority": "WebsiteOperator owner gate only",
}

_RUN_ID = re.compile(r"[a-z0-9][a-z0-9._-]{2,80}")
_SHA256 = re.compile(r"[A-F0-9]{64}")
_RECEIPT_FILE = re.compile(r"(?P<sequence>0*[1-9][0-9]*)-(?P<state>[a-z0-9-]+)\.json\Z")
_JOB_STATES = frozenset(
    {
        "work-order-ready",
        "candidate-staged",
        "candidate-assets-ready",
        "candidate-validated",
        "candidate-repair-required",
        "candidate-qa-verified",
        "candidate-qa-repair-required",
        "initial-gate-rejected",
        "awaiting-browser-evidence",
        "visual-review-repair-required",
        "awaiting-owner-promotion",
    }
)
_ALLOWED_STATE_TRANSITIONS = {
    "work-order-ready": frozenset({"candidate-staged"}),
    "candidate-staged": frozenset(
        {"candidate-assets-ready", "candidate-validated", "candidate-repair-required"}
    ),
    "candidate-assets-ready": frozenset({"candidate-validated", "candidate-repair-required"}),
    "candidate-validated": frozenset({"candidate-qa-verified", "candidate-qa-repair-required"}),
    "candidate-qa-verified": frozenset({"awaiting-browser-evidence", "initial-gate-rejected"}),
    "awaiting-browser-evidence": frozenset({"awaiting-owner-promotion", "visual-review-repair-required"}),
}
_LEGACY_JOB_STATES = _JOB_STATES.difference({"candidate-qa-verified", "candidate-qa-repair-required"})
_LEGACY_ALLOWED_STATE_TRANSITIONS = {
    "work-order-ready": frozenset({"candidate-staged"}),
    "candidate-staged": frozenset(
        {"candidate-assets-ready", "candidate-validated", "candidate-repair-required"}
    ),
    "candidate-assets-ready": frozenset({"candidate-validated", "candidate-repair-required"}),
    "candidate-validated": frozenset({"awaiting-browser-evidence", "initial-gate-rejected"}),
    "awaiting-browser-evidence": frozenset({"awaiting-owner-promotion", "visual-review-repair-required"}),
}
_CANDIDATE_STATES = frozenset(
    {
        "candidate-staged",
        "candidate-assets-ready",
        "candidate-validated",
        "candidate-repair-required",
        "candidate-qa-verified",
        "candidate-qa-repair-required",
        "initial-gate-rejected",
        "awaiting-browser-evidence",
        "visual-review-repair-required",
        "awaiting-owner-promotion",
    }
)
_VALIDATED_CANDIDATE_STATES = _CANDIDATE_STATES.difference({"candidate-staged", "candidate-assets-ready"})
_PASSING_CANDIDATE_STATES = _VALIDATED_CANDIDATE_STATES.difference({"candidate-repair-required"})
_QA_STATES = frozenset(
    {
        "candidate-qa-verified",
        "candidate-qa-repair-required",
        "initial-gate-rejected",
        "awaiting-browser-evidence",
        "visual-review-repair-required",
        "awaiting-owner-promotion",
    }
)
_PASSING_QA_STATES = _QA_STATES.difference({"candidate-qa-repair-required"})
_INITIAL_GATE_STATES = frozenset(
    {
        "initial-gate-rejected",
        "awaiting-browser-evidence",
        "visual-review-repair-required",
        "awaiting-owner-promotion",
    }
)
_PASSING_INITIAL_GATE_STATES = _INITIAL_GATE_STATES.difference({"initial-gate-rejected"})
_VISUAL_REVIEW_STATES = frozenset({"visual-review-repair-required", "awaiting-owner-promotion"})
_CANDIDATE_QA_FIELDS = frozenset(
    {
        "schema",
        "status",
        "attempt_consumed",
        "attempt",
        "candidate",
        "canonical_website",
        "trusted_toolchain",
        "motion_config_compiler",
        "test_policy_compiler",
        "motion",
        "tests",
        "authority",
        "release_eligible",
        "package_authority",
        "deployment_authority",
    }
)
_CANDIDATE_QA_CLAIM_FIELDS = frozenset(
    {
        "schema",
        "state",
        "claimed_at",
        "run_id",
        "delivery_receipt",
        "candidate",
        "canonical_website",
        "trusted_toolchain",
        "motion_config",
        "motion_config_compiler",
        "test_policy",
        "test_policy_compiler",
        "authority",
        "release_eligible",
        "package_authority",
        "deployment_authority",
        "claim_payload_sha256",
    }
)
_CANDIDATE_QA_CANDIDATE_FIELDS = frozenset(
    {
        "root",
        "website_path",
        "validation_tree_sha256",
        "candidate_tree_algorithm",
        "motion_tree_sha256",
        "motion_tree_algorithm",
        "captured_manifest_sha256",
        "validation_receipt",
    }
)
_MOTION_POLICY_COMPILER_VERIFICATION_FIELDS = frozenset(
    {
        "schema",
        "state",
        "passed",
        "verification_scope",
        "compiler_replayed",
        "origin_attested",
        "candidate_receipt_path",
        "candidate_tree_sha256",
        "candidate_tree_algorithm",
        "motion_tree_sha256",
        "motion_tree_algorithm",
        "captured_manifest_sha256",
        "doctrine_sha256",
        "source_policy_sha256",
        "config_path",
        "config_id",
        "config_file_sha256",
        "config_json_sha256",
        "thresholds_sha256",
        "authority",
    }
)
_TEST_POLICY_COMPILER_VERIFICATION_FIELDS = frozenset(
    {
        "schema",
        "state",
        "passed",
        "verification_scope",
        "compiler_replayed",
        "origin_attested",
        "candidate_receipt_path",
        "candidate_tree_sha256",
        "source_policy_file_sha256",
        "policy_path",
        "policy_id",
        "policy_content_core_sha256",
        "policy_file_sha256",
        "policy_json_sha256",
        "required_command_ids",
        "deferred_source_ids",
        "authority",
    }
)
_CANDIDATE_QA_AUTHORITY = {
    "scope": "trusted one-attempt staged candidate QA orchestration only",
    "canonical_website_mutation": "none",
    "candidate_mutation": "none",
    "worker_qa_authority": "none",
    "threshold_override_authority": "none",
    "test_selection_authority": "none",
    "retry_authority": "none",
    "promotion_authority": "none",
    "package_authority": "none",
    "release_authority": "none",
    "deployment_authority": "none",
    "credential_access": "none",
}
_IMMUTABLE_JOB_FIELDS = frozenset(
    {
        "schema",
        "created_at",
        "run_id",
        "goal",
        "brief_binding",
        "work_order",
        "asset_requirement",
        "delivery_contract",
        "investor_copy_repair",
        "authority",
        "release_eligible",
        "package_authority",
        "deployment_authority",
    }
)


class PublicWebsiteDesignRunnerError(ValueError):
    """A staged delivery job is invalid, stale, or outside its authority."""


@dataclass(frozen=True)
class _BoundedProcessResult:
    returncode: int
    stdout: bytes
    stderr: bytes
    stdout_sha256: str
    stderr_sha256: str
    stdout_bytes: int
    stderr_bytes: int


def _sealed_compiler_environment() -> dict[str, str]:
    """Build a fixed compiler environment without inheriting caller state."""

    environment = {
        "AUREON_OFFLINE_INTENT": "1",
        "AUREON_OS_NETWORK_SANDBOX": "0",
        "CI": "1",
        "NO_COLOR": "1",
    }
    if os.name == "nt":
        windows_root = Path(sys.executable).anchor + "Windows"
        environment.update(
            {
                "PATH": str(Path(windows_root) / "System32"),
                "SYSTEMROOT": windows_root,
                "WINDIR": windows_root,
            }
        )
    else:
        environment["PATH"] = "/usr/bin:/bin"
    return environment


def _stop_sealed_process(process: subprocess.Popen[bytes]) -> None:
    """Terminate one child and escalate to kill; never retry or respawn."""

    if process.poll() is not None:
        process.wait(timeout=5)
        return
    try:
        process.terminate()
    except OSError:
        pass
    try:
        process.wait(timeout=1)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        process.kill()
    except OSError:
        pass
    process.wait(timeout=5)


def _run_bounded_sealed_process(
    command: Sequence[str],
    *,
    cwd: Path,
    environment: Mapping[str, str],
    timeout_seconds: int,
    label: str,
) -> _BoundedProcessResult:
    """Run once while retaining at most 64 KiB across both process pipes."""

    try:
        process = subprocess.Popen(
            list(command),
            cwd=cwd,
            env=dict(environment),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
        )
    except OSError as exc:
        raise PublicWebsiteDesignRunnerError(f"{label} could not start; no retry is allowed.") from exc
    if process.stdout is None or process.stderr is None:
        _stop_sealed_process(process)
        raise PublicWebsiteDesignRunnerError(
            f"{label} did not expose bounded byte streams; no retry is allowed."
        )

    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    digests = {"stdout": hashlib.sha256(), "stderr": hashlib.sha256()}
    byte_counts = {"stdout": 0, "stderr": 0}
    retained_total = 0
    state_lock = threading.Lock()
    wake_event = threading.Event()
    output_limit_exceeded = threading.Event()
    reader_errors: list[str] = []

    def drain(name: str, stream: Any) -> None:
        nonlocal retained_total
        try:
            while True:
                block = stream.read(4096)
                if not block:
                    return
                if not isinstance(block, bytes):
                    raise TypeError("process stream returned non-byte output")
                digests[name].update(block)
                byte_counts[name] += len(block)
                with state_lock:
                    stream_room = SEALED_COMPILER_MAX_OUTPUT_BYTES - len(buffers[name])
                    total_room = SEALED_COMPILER_MAX_OUTPUT_BYTES - retained_total
                    retained = min(len(block), max(0, stream_room), max(0, total_room))
                    if retained:
                        buffers[name].extend(block[:retained])
                        retained_total += retained
                    if retained != len(block):
                        output_limit_exceeded.set()
                        wake_event.set()
        except (OSError, TypeError) as exc:
            with state_lock:
                reader_errors.append(f"{name}:{type(exc).__name__}")
            wake_event.set()

    threads = [
        threading.Thread(target=drain, args=("stdout", process.stdout), daemon=True),
        threading.Thread(target=drain, args=("stderr", process.stderr), daemon=True),
    ]
    for thread in threads:
        thread.start()

    deadline = time.monotonic() + timeout_seconds
    timed_out = False
    while process.poll() is None:
        if output_limit_exceeded.is_set() or reader_errors:
            break
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            timed_out = True
            break
        wake_event.wait(min(remaining, 0.01))
        wake_event.clear()

    if timed_out or output_limit_exceeded.is_set() or reader_errors:
        try:
            _stop_sealed_process(process)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise PublicWebsiteDesignRunnerError(
                f"{label} child cleanup failed after a bounded-process stop condition."
            ) from exc
    else:
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired as exc:
            try:
                _stop_sealed_process(process)
            except (OSError, subprocess.TimeoutExpired):
                pass
            raise PublicWebsiteDesignRunnerError(
                f"{label} child cleanup exceeded its bounded wait; no retry is allowed."
            ) from exc

    for thread in threads:
        thread.join(timeout=5)
    if any(thread.is_alive() for thread in threads):
        process.stdout.close()
        process.stderr.close()
        for thread in threads:
            thread.join(timeout=1)
        raise PublicWebsiteDesignRunnerError(f"{label} pipe cleanup did not complete; no retry is allowed.")
    process.stdout.close()
    process.stderr.close()

    stdout_sha256 = digests["stdout"].hexdigest().upper()
    stderr_sha256 = digests["stderr"].hexdigest().upper()
    observation = (
        f"stdout_sha256={stdout_sha256}; stdout_bytes={byte_counts['stdout']}; "
        f"stderr_sha256={stderr_sha256}; stderr_bytes={byte_counts['stderr']}"
    )
    if output_limit_exceeded.is_set():
        raise PublicWebsiteDesignRunnerError(
            f"{label} output exceeded the {SEALED_COMPILER_MAX_OUTPUT_BYTES}-byte "
            f"aggregate/per-stream bound; {observation}; no retry is allowed."
        )
    if timed_out:
        raise PublicWebsiteDesignRunnerError(
            f"{label} timed out after {timeout_seconds} seconds; {observation}; no retry is allowed."
        )
    if reader_errors:
        raise PublicWebsiteDesignRunnerError(
            f"{label} byte-stream collection failed ({','.join(reader_errors)}); "
            f"{observation}; no retry is allowed."
        )
    if process.returncode is None:
        raise PublicWebsiteDesignRunnerError(f"{label} ended without an exit status.")
    return _BoundedProcessResult(
        returncode=process.returncode,
        stdout=bytes(buffers["stdout"]),
        stderr=bytes(buffers["stderr"]),
        stdout_sha256=stdout_sha256,
        stderr_sha256=stderr_sha256,
        stdout_bytes=byte_counts["stdout"],
        stderr_bytes=byte_counts["stderr"],
    )


def _hash_source_file(value: str | Path | None, *, label: str) -> str:
    if not isinstance(value, (str, Path)) or not str(value):
        raise RuntimeError(f"{label} has no source-file identity.")
    return hashlib.sha256(Path(value).read_bytes()).hexdigest().upper()


_QA_TOOLCHAIN_PATHS = {
    "runner": "aureon/autonomous/aureon_public_website_design_runner.py",
    "test_evidence": "aureon/operator/design_candidate_test_evidence.py",
    "motion_policy_compiler": "aureon/operator/design_candidate_motion_policy_compiler.py",
    "test_policy_compiler": "aureon/operator/design_candidate_test_policy_compiler.py",
    "motion_budget": "aureon/operator/design_motion_performance_budget.py",
    "secure_immutable_artifact": "aureon/operator/secure_immutable_artifact.py",
}
_SOURCE_REPO_ROOT = Path(__file__).resolve().parents[2]
_QA_SOURCE_FILE_SHA256 = {
    "runner": _hash_source_file(__file__, label="Delivery runner"),
    "test_evidence": _hash_source_file(
        _test_evidence_module.__file__,
        label="Candidate test-evidence module",
    ),
    "motion_policy_compiler": _hash_source_file(
        _SOURCE_REPO_ROOT / _QA_TOOLCHAIN_PATHS["motion_policy_compiler"],
        label="Candidate motion-policy compiler",
    ),
    "test_policy_compiler": _hash_source_file(
        _SOURCE_REPO_ROOT / _QA_TOOLCHAIN_PATHS["test_policy_compiler"],
        label="Candidate test-policy compiler",
    ),
    "motion_budget": _hash_source_file(
        _motion_budget_module.__file__,
        label="Motion-performance module",
    ),
    "secure_immutable_artifact": _hash_source_file(
        _secure_immutable_artifact_module.__file__,
        label="Secure immutable-artifact writer",
    ),
}


def _utc_iso(value: datetime | None = None) -> str:
    return (value or datetime.now(UTC)).astimezone(UTC).isoformat().replace("+00:00", "Z")


def _find_repo_root(start: Path | None = None) -> Path:
    candidate = (start or Path.cwd()).resolve()
    for root in (candidate, *candidate.parents):
        if (root / "pyproject.toml").is_file() and (root / "aureon").is_dir():
            return root
    raise PublicWebsiteDesignRunnerError(
        "Could not locate an Aureon repository with pyproject.toml and aureon/."
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _json_sha256(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest().upper()


def _relative_to_repo(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise PublicWebsiteDesignRunnerError(
            "Delivery evidence must stay inside the Aureon repository."
        ) from exc


def _is_link_or_reparse_point(path: Path) -> bool:
    """Inspect the raw filesystem entry without following a link or junction."""

    try:
        details = path.lstat()
    except FileNotFoundError:
        return False
    return stat.S_ISLNK(details.st_mode) or bool(
        getattr(details, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    )


def _reject_link_ancestors(root: Path, target: Path, *, label: str) -> None:
    """Reject links/reparse points before resolving a repository-relative path."""

    raw_root = root.absolute()
    raw_target = target.absolute()
    if _is_link_or_reparse_point(raw_root) or not raw_root.is_dir():
        raise PublicWebsiteDesignRunnerError(f"{label} repository root must be a regular existing directory.")
    try:
        relative = raw_target.relative_to(raw_root)
    except ValueError as exc:
        raise PublicWebsiteDesignRunnerError(f"{label} must stay under the Aureon repository.") from exc
    cursor = raw_root
    for part in relative.parts:
        cursor = cursor / part
        if cursor.exists() and _is_link_or_reparse_point(cursor):
            raise PublicWebsiteDesignRunnerError(
                f"{label} must not traverse a symbolic link or reparse point."
            )


def _artifact_root(root: Path, relative: Path, *, label: str) -> Path:
    """Resolve an artifact root without allowing a symlink to leave the repo."""

    repository = root.resolve()
    raw_candidate = repository / relative
    _reject_link_ancestors(repository, raw_candidate, label=label)
    candidate = raw_candidate.resolve()
    try:
        candidate.relative_to(repository)
    except ValueError as exc:
        raise PublicWebsiteDesignRunnerError(f"{label} must resolve inside the Aureon repository.") from exc
    return candidate


def _safe_run_id(value: object) -> str:
    if not isinstance(value, str) or not _RUN_ID.fullmatch(value):
        raise PublicWebsiteDesignRunnerError(
            "Delivery run id must be a stable lowercase slug (3-81 characters)."
        )
    return value


def _mapping(value: object, *, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise PublicWebsiteDesignRunnerError(f"{label} must be an object.")
    return dict(value)


def _regular_file_under(root: Path, value: object, *, label: str, allowed_root: Path) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise PublicWebsiteDesignRunnerError(f"{label} must be a non-empty repository-relative path.")
    repository = root.resolve()
    approved_root = allowed_root.resolve()
    try:
        approved_root.relative_to(repository)
    except ValueError as exc:
        raise PublicWebsiteDesignRunnerError(
            f"{label} approved artifact root must stay inside the Aureon repository."
        ) from exc
    raw_candidate = repository / value
    _reject_link_ancestors(repository, raw_candidate, label=label)
    candidate = raw_candidate.resolve()
    try:
        candidate.relative_to(approved_root)
        candidate.relative_to(repository)
    except ValueError as exc:
        raise PublicWebsiteDesignRunnerError(f"{label} must stay below its approved artifact root.") from exc
    try:
        details = candidate.lstat()
    except OSError as exc:
        raise PublicWebsiteDesignRunnerError(f"{label} must be a regular existing file.") from exc
    if _is_link_or_reparse_point(candidate) or not stat.S_ISREG(details.st_mode) or details.st_nlink != 1:
        raise PublicWebsiteDesignRunnerError(
            f"{label} must be a regular, single-link, reparse-free existing file."
        )
    return candidate


def _regular_directory_under(root: Path, value: object, *, label: str, allowed_root: Path) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise PublicWebsiteDesignRunnerError(f"{label} must be a non-empty repository-relative path.")
    repository = root.resolve()
    approved_root = allowed_root.resolve()
    try:
        approved_root.relative_to(repository)
    except ValueError as exc:
        raise PublicWebsiteDesignRunnerError(
            f"{label} approved artifact root must stay inside the Aureon repository."
        ) from exc
    raw_candidate = repository / value
    _reject_link_ancestors(repository, raw_candidate, label=label)
    candidate = raw_candidate.resolve()
    try:
        candidate.relative_to(approved_root)
        candidate.relative_to(repository)
    except ValueError as exc:
        raise PublicWebsiteDesignRunnerError(f"{label} must stay below its approved artifact root.") from exc
    if not candidate.is_dir() or candidate.is_symlink():
        raise PublicWebsiteDesignRunnerError(f"{label} must be a regular existing directory.")
    return candidate


def _read_json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PublicWebsiteDesignRunnerError(f"{label} is not valid JSON: {path}") from exc
    return _mapping(value, label=label)


def _require_advancing_v2(job: Mapping[str, Any], *, operation: str) -> None:
    if job.get("schema") != DELIVERY_JOB_SCHEMA:
        raise PublicWebsiteDesignRunnerError(
            f"{operation} is available only to {DELIVERY_JOB_SCHEMA}; "
            f"{LEGACY_DELIVERY_JOB_SCHEMA} is historical read-only evidence."
        )


def _pinned_file_binding(
    root: Path,
    path: Path,
    expected_sha256: str,
    *,
    label: str,
) -> tuple[Path, dict[str, str]]:
    if not isinstance(expected_sha256, str) or _SHA256.fullmatch(expected_sha256) is None:
        raise PublicWebsiteDesignRunnerError(
            f"{label} externally pinned file hash must be one upper-case SHA-256."
        )
    value = _relative_to_repo(root, path if path.is_absolute() else root / path)
    absolute = _regular_file_under(
        root,
        value,
        label=label,
        allowed_root=root,
    )
    observed = _sha256_file(absolute)
    if observed != expected_sha256:
        raise PublicWebsiteDesignRunnerError(f"{label} no longer matches its externally pinned file hash.")
    return absolute, {"path": value, "sha256": observed}


def _trusted_qa_toolchain_binding(root: Path) -> dict[str, dict[str, str]]:
    """Prove current QA source files still equal this runner's startup capture."""

    binding: dict[str, dict[str, str]] = {}
    for name, relative in _QA_TOOLCHAIN_PATHS.items():
        path = _regular_file_under(
            root,
            relative,
            label=f"Trusted QA {name} module",
            allowed_root=root / "aureon",
        )
        observed = _sha256_file(path)
        if observed != _QA_SOURCE_FILE_SHA256[name]:
            raise PublicWebsiteDesignRunnerError(
                f"Trusted QA {name} module changed after runner startup; execution is withheld."
            )
        binding[name] = {"path": relative, "sha256": observed}
    return binding


def _strict_compiler_json_object(raw: bytes, *, label: str) -> dict[str, Any]:
    """Accept exactly one canonical compact JSON object from a sealed compiler."""

    if not isinstance(raw, bytes) or not raw:
        raise PublicWebsiteDesignRunnerError(f"{label} returned no JSON object.")
    if len(raw) > SEALED_COMPILER_MAX_OUTPUT_BYTES:
        raise PublicWebsiteDesignRunnerError(
            f"{label} output exceeded {SEALED_COMPILER_MAX_OUTPUT_BYTES} bytes."
        )
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PublicWebsiteDesignRunnerError(f"{label} output is not strict UTF-8.") from exc

    def object_from_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate object key: {key}")
            result[key] = value
        return result

    def reject_non_finite(value: str) -> None:
        raise ValueError(f"non-finite JSON value: {value}")

    try:
        value = json.loads(
            text,
            object_pairs_hook=object_from_pairs,
            parse_constant=reject_non_finite,
        )
    except (json.JSONDecodeError, ValueError) as exc:
        raise PublicWebsiteDesignRunnerError(f"{label} output is not one strict JSON object.") from exc
    if not isinstance(value, dict):
        raise PublicWebsiteDesignRunnerError(f"{label} output must be one JSON object.")
    canonical = (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )
    if raw != canonical:
        raise PublicWebsiteDesignRunnerError(
            f"{label} output is not canonical compact JSON with one LF terminator."
        )
    return value


def _is_upper_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None


def _motion_compiler_verification_matches(
    value: Mapping[str, Any],
    *,
    candidate_receipt_path: object,
    candidate_tree_sha256: object,
    candidate_tree_algorithm: object,
    motion_tree_sha256: object,
    motion_tree_algorithm: object,
    captured_manifest_sha256: object,
    config_path: object,
    config_file_sha256: object,
) -> bool:
    return (
        set(value) == _MOTION_POLICY_COMPILER_VERIFICATION_FIELDS
        and value.get("schema") == MOTION_POLICY_COMPILER_VERIFICATION_SCHEMA
        and value.get("state") == "pass"
        and value.get("passed") is True
        and value.get("verification_scope") == MOTION_POLICY_COMPILER_VERIFICATION_SCOPE
        and value.get("compiler_replayed") is True
        and value.get("origin_attested") is False
        and value.get("authority") == MOTION_POLICY_COMPILER_AUTHORITY
        and value.get("candidate_receipt_path") == candidate_receipt_path
        and value.get("candidate_tree_sha256") == candidate_tree_sha256
        and _is_upper_sha256(candidate_tree_sha256)
        and value.get("candidate_tree_algorithm") == candidate_tree_algorithm
        and isinstance(candidate_tree_algorithm, str)
        and bool(candidate_tree_algorithm)
        and value.get("motion_tree_sha256") == motion_tree_sha256
        and _is_upper_sha256(motion_tree_sha256)
        and value.get("motion_tree_algorithm") == motion_tree_algorithm
        and isinstance(motion_tree_algorithm, str)
        and bool(motion_tree_algorithm)
        and value.get("captured_manifest_sha256") == captured_manifest_sha256
        and _is_upper_sha256(captured_manifest_sha256)
        and value.get("doctrine_sha256") == MOTION_POLICY_COMPILER_DOCTRINE_SHA256
        and value.get("source_policy_sha256") == COMPILER_SOURCE_POLICY_FILE_SHA256
        and value.get("config_path") == config_path
        and value.get("config_file_sha256") == config_file_sha256
        and _is_upper_sha256(config_file_sha256)
        and value.get("config_id") == f"candidate-motion-v2-{str(config_file_sha256).lower()}"
        and _is_upper_sha256(value.get("config_json_sha256"))
        and _is_upper_sha256(value.get("thresholds_sha256"))
    )


def _test_compiler_verification_matches(
    value: Mapping[str, Any],
    *,
    candidate_receipt_path: object,
    candidate_tree_sha256: object,
    policy_path: object,
    policy_content_core_sha256: object,
    policy_file_sha256: object,
    required_command_ids: object,
) -> bool:
    return (
        set(value) == _TEST_POLICY_COMPILER_VERIFICATION_FIELDS
        and value.get("schema") == TEST_POLICY_COMPILER_VERIFICATION_SCHEMA
        and value.get("state") == "pass"
        and value.get("passed") is True
        and value.get("verification_scope") == TEST_POLICY_COMPILER_VERIFICATION_SCOPE
        and value.get("compiler_replayed") is True
        and value.get("origin_attested") is False
        and value.get("authority") == TEST_POLICY_COMPILER_AUTHORITY
        and value.get("candidate_receipt_path") == candidate_receipt_path
        and value.get("candidate_tree_sha256") == candidate_tree_sha256
        and _is_upper_sha256(candidate_tree_sha256)
        and value.get("source_policy_file_sha256") == COMPILER_SOURCE_POLICY_FILE_SHA256
        and value.get("policy_path") == policy_path
        and value.get("policy_content_core_sha256") == policy_content_core_sha256
        and _is_upper_sha256(policy_content_core_sha256)
        and value.get("policy_id") == f"candidate-suite-v2-{str(policy_content_core_sha256).lower()}"
        and value.get("policy_file_sha256") == policy_file_sha256
        and _is_upper_sha256(policy_file_sha256)
        and _is_upper_sha256(value.get("policy_json_sha256"))
        and value.get("required_command_ids") == required_command_ids
        and isinstance(required_command_ids, list)
        and bool(required_command_ids)
        and all(isinstance(item, str) and bool(item) for item in required_command_ids)
        and len(required_command_ids) == len(set(required_command_ids))
        and value.get("deferred_source_ids") == list(TEST_POLICY_COMPILER_DEFERRED_SOURCE_IDS)
    )


def _run_sealed_compiler_verification(
    root: Path,
    *,
    toolchain_name: str,
    verify_flag: str,
    input_path: Path,
    expected_hash_flag: str,
    expected_sha256: str,
    candidate_receipt_path: Path,
    label: str,
) -> dict[str, Any]:
    """Run one read-only compiler verifier in a fresh isolated interpreter."""

    relative = _QA_TOOLCHAIN_PATHS.get(toolchain_name)
    if relative is None:
        raise PublicWebsiteDesignRunnerError(f"{label} has no reviewed compiler path.")
    compiler_path = _regular_file_under(
        root,
        relative,
        label=f"{label} executable",
        allowed_root=root / "aureon" / "operator",
    )
    if _sha256_file(compiler_path) != _QA_SOURCE_FILE_SHA256[toolchain_name]:
        raise PublicWebsiteDesignRunnerError(f"{label} executable changed after runner startup.")
    command = [
        sys.executable,
        *SEALED_COMPILER_PYTHON_FLAGS,
        str(compiler_path),
        verify_flag,
        str(input_path),
        expected_hash_flag,
        expected_sha256,
        "--candidate-receipt",
        str(candidate_receipt_path),
    ]
    completed = _run_bounded_sealed_process(
        command,
        cwd=root,
        environment=_sealed_compiler_environment(),
        timeout_seconds=SEALED_COMPILER_TIMEOUT_SECONDS,
        label=label,
    )
    stdout = completed.stdout
    stderr = completed.stderr
    if not isinstance(stdout, bytes) or not isinstance(stderr, bytes):
        raise PublicWebsiteDesignRunnerError(f"{label} returned a non-byte process stream.")
    if completed.returncode != 0:
        raise PublicWebsiteDesignRunnerError(
            f"{label} blocked with exit {completed.returncode}; "
            f"stdout_sha256={completed.stdout_sha256}; stderr_sha256={completed.stderr_sha256}."
        )
    if stderr:
        raise PublicWebsiteDesignRunnerError(f"{label} wrote unexpected stderr on a successful verification.")
    return _strict_compiler_json_object(stdout, label=label)


def _verify_compiled_candidate_motion_config_file_sealed(
    config_path: Path,
    *,
    expected_config_sha256: str,
    candidate_receipt_path: Path,
    repo_root: Path,
) -> dict[str, Any]:
    return _run_sealed_compiler_verification(
        repo_root,
        toolchain_name="motion_policy_compiler",
        verify_flag="--verify-config",
        input_path=config_path,
        expected_hash_flag="--expected-config-sha256",
        expected_sha256=expected_config_sha256,
        candidate_receipt_path=candidate_receipt_path,
        label="Sealed candidate motion-config verifier",
    )


def _verify_compiled_candidate_test_policy_file_sealed(
    policy_path: Path,
    *,
    expected_policy_sha256: str,
    candidate_receipt_path: Path,
    repo_root: Path,
) -> dict[str, Any]:
    return _run_sealed_compiler_verification(
        repo_root,
        toolchain_name="test_policy_compiler",
        verify_flag="--verify-policy",
        input_path=policy_path,
        expected_hash_flag="--expected-policy-sha256",
        expected_sha256=expected_policy_sha256,
        candidate_receipt_path=candidate_receipt_path,
        label="Sealed candidate test-policy verifier",
    )


def _qa_claim_path(candidate_root: Path) -> Path:
    target = candidate_root / "candidate-qa" / "attempt.v2.json"
    _reject_link_ancestors(candidate_root, target, label="Candidate QA attempt")
    resolved = target.resolve()
    try:
        resolved.relative_to(candidate_root.resolve())
    except ValueError as exc:
        raise PublicWebsiteDesignRunnerError(
            "Candidate QA attempt receipt escapes its staged candidate root."
        ) from exc
    return resolved


def _static_tree_binding(
    root: Path,
    source: Path,
    *,
    expected_kind: str,
    label: str,
) -> dict[str, Any]:
    try:
        raw = snapshot_static_tree(source, repo_root=root)
    except DesignMotionPerformanceBudgetError as exc:
        raise PublicWebsiteDesignRunnerError(f"{label} snapshot failed closed: {exc}") from exc
    binding = _mapping(raw, label=f"{label} snapshot")
    if (
        binding.get("kind") != expected_kind
        or not isinstance(binding.get("root"), str)
        or _SHA256.fullmatch(str(binding.get("tree_sha256") or "")) is None
        or not isinstance(binding.get("file_count"), int)
        or isinstance(binding.get("file_count"), bool)
        or not isinstance(binding.get("total_bytes"), int)
        or isinstance(binding.get("total_bytes"), bool)
    ):
        raise PublicWebsiteDesignRunnerError(f"{label} snapshot is malformed.")
    return binding


def _candidate_qa_tree_binding(
    root: Path,
    source: Path,
    *,
    label: str,
) -> dict[str, Any]:
    """Capture both historical tree hashes from one immutable byte manifest."""

    try:
        raw = snapshot_static_tree_dual_hash(source, repo_root=root)
    except DesignMotionPerformanceBudgetError as exc:
        raise PublicWebsiteDesignRunnerError(f"{label} snapshot failed closed: {exc}") from exc
    binding = _mapping(raw, label=f"{label} snapshot")
    expected_fields = {
        "kind",
        "root",
        "candidate_tree_sha256",
        "candidate_tree_algorithm",
        "motion_tree_sha256",
        "motion_tree_algorithm",
        "captured_manifest_sha256",
        "file_count",
        "total_bytes",
    }
    if (
        set(binding) != expected_fields
        or binding.get("kind") != "staged-static-tree"
        or not isinstance(binding.get("root"), str)
        or _SHA256.fullmatch(str(binding.get("candidate_tree_sha256") or "")) is None
        or binding.get("candidate_tree_algorithm") != _motion_budget_module.CANDIDATE_TREE_ALGORITHM
        or _SHA256.fullmatch(str(binding.get("motion_tree_sha256") or "")) is None
        or binding.get("motion_tree_algorithm") != _motion_budget_module.TREE_ALGORITHM
        or _SHA256.fullmatch(str(binding.get("captured_manifest_sha256") or "")) is None
        or not isinstance(binding.get("file_count"), int)
        or isinstance(binding.get("file_count"), bool)
        or not isinstance(binding.get("total_bytes"), int)
        or isinstance(binding.get("total_bytes"), bool)
    ):
        raise PublicWebsiteDesignRunnerError(
            f"{label} dual-hash snapshot is malformed or uses an unreviewed algorithm."
        )
    return binding


def _asset_requirement(order: Mapping[str, Any]) -> dict[str, Any]:
    raw_paths = order.get("allowed_paths")
    if not isinstance(raw_paths, list) or not all(isinstance(path, str) and path for path in raw_paths):
        raise PublicWebsiteDesignRunnerError("Work order lacks its exact candidate path allow-list.")
    binary_paths = sorted(
        path for path in raw_paths if Path(path).suffix.casefold() in CONTROLLED_BINARY_EXTENSIONS
    )
    unsupported = sorted(
        path
        for path in binary_paths
        if Path(path).suffix.casefold() not in TRUSTED_EDITORIAL_IMPORT_EXTENSIONS
    )
    if unsupported:
        raise PublicWebsiteDesignRunnerError(
            "Runner-managed autonomous binary paths must be trusted WebP imports: " + ", ".join(unsupported)
        )
    return {
        "required": bool(binary_paths),
        "declared_binary_paths": binary_paths,
        "trusted_import_extensions": sorted(TRUSTED_EDITORIAL_IMPORT_EXTENSIONS),
        "import_operation": (
            "runner-only-trusted-editorial-importer" if binary_paths else "not-required-text-only"
        ),
        "receipt_replay_required": bool(binary_paths),
    }


def _text_mutation_contract(order: Mapping[str, Any]) -> dict[str, Any]:
    raw_paths = order.get("allowed_paths")
    if not isinstance(raw_paths, list):
        raise PublicWebsiteDesignRunnerError("Work order lacks its exact candidate path allow-list.")
    text_paths = sorted(
        str(path)
        for path in raw_paths
        if isinstance(path, str) and Path(path).suffix.casefold() in CONTROLLED_TEXT_EXTENSIONS
    )
    return {
        "text_write_paths": text_paths,
        "binary_read_authority": "none",
        "binary_write_authority": "none",
        "binary_import_authority": "none",
        "canonical_write_authority": "none",
    }


def _investor_copy_contract_reference(
    *,
    root: Path,
    contract: Mapping[str, Any],
    contract_path: Path,
) -> dict[str, Any]:
    """Bind one immutable copy-repair contract without projecting its source."""

    design_cycle = _mapping(
        contract.get("design_cycle"),
        label="Investor-copy contract design-cycle binding",
    )
    contract_id = contract.get("contract_id")
    task_id = design_cycle.get("task_id")
    if (
        contract.get("schema") != INVESTOR_COPY_REPAIR_CONTRACT_SCHEMA
        or not isinstance(contract_id, str)
        or not contract_id
        or not isinstance(task_id, str)
        or not task_id
        or not isinstance(design_cycle.get("task_sha256"), str)
        or not _SHA256.fullmatch(str(design_cycle["task_sha256"]))
        or not isinstance(design_cycle.get("receipt_sha256"), str)
        or not _SHA256.fullmatch(str(design_cycle["receipt_sha256"]))
    ):
        raise PublicWebsiteDesignRunnerError(
            "Investor-copy repair contract lost its schema, id, or exact task binding."
        )
    return {
        "schema": INVESTOR_COPY_REPAIR_CONTRACT_SCHEMA,
        "required": True,
        "contract_id": contract_id,
        "path": _relative_to_repo(root, contract_path),
        "sha256": _sha256_file(contract_path),
        "task_id": task_id,
        "task_sha256": design_cycle.get("task_sha256"),
        "design_cycle_receipt_sha256": design_cycle.get("receipt_sha256"),
    }


def _load_investor_copy_contract(
    *,
    root: Path,
    job: Mapping[str, Any],
    route: Mapping[str, Any],
    work_order_ref: Mapping[str, Any],
    now: datetime | None,
) -> tuple[dict[str, Any], Path] | None:
    """Revalidate an optional copy contract against the current sealed route."""

    raw_reference = job.get("investor_copy_repair")
    if raw_reference is None:
        return None
    reference = _mapping(
        raw_reference,
        label="Delivery job investor-copy repair binding",
    )
    if set(reference) != {
        "schema",
        "required",
        "contract_id",
        "path",
        "sha256",
        "task_id",
        "task_sha256",
        "design_cycle_receipt_sha256",
    } or (
        reference.get("schema") != INVESTOR_COPY_REPAIR_CONTRACT_SCHEMA
        or reference.get("required") is not True
        or not isinstance(reference.get("contract_id"), str)
        or not reference["contract_id"]
        or not isinstance(reference.get("task_id"), str)
        or not reference["task_id"]
        or not isinstance(reference.get("sha256"), str)
        or not _SHA256.fullmatch(str(reference["sha256"]))
        or not isinstance(reference.get("task_sha256"), str)
        or not _SHA256.fullmatch(str(reference["task_sha256"]))
        or not isinstance(reference.get("design_cycle_receipt_sha256"), str)
        or not _SHA256.fullmatch(str(reference["design_cycle_receipt_sha256"]))
    ):
        raise PublicWebsiteDesignRunnerError("Delivery job investor-copy repair binding is malformed.")
    contract_path = _regular_file_under(
        root,
        reference.get("path"),
        label="Investor-copy repair contract",
        allowed_root=(root / INVESTOR_COPY_REPAIR_ROOT).resolve(),
    )
    contract = _read_json(
        contract_path,
        label="Investor-copy repair contract",
    )
    contract_design = _mapping(
        contract.get("design_cycle"),
        label="Investor-copy contract design-cycle binding",
    )
    contract_order = _mapping(
        contract.get("work_order"),
        label="Investor-copy contract work-order binding",
    )
    contract_route = _mapping(
        contract.get("route"),
        label="Investor-copy contract route binding",
    )
    capsule = _mapping(
        route.get("claim_capsule"),
        label="Delivery job route claim capsule",
    )
    verification = verify_investor_copy_repair_contract(
        contract,
        route_claim_capsule=capsule,
        repo_root=root,
        as_of=now,
    )
    expected_reference = _investor_copy_contract_reference(
        root=root,
        contract=contract,
        contract_path=contract_path,
    )
    if (
        reference != expected_reference
        or verification.get("passed") is not True
        or contract_order.get("path") != work_order_ref.get("path")
        or contract_order.get("sha256") != work_order_ref.get("sha256")
        or contract_order.get("run_id") != work_order_ref.get("run_id")
        or contract_design.get("task_id") != reference.get("task_id")
        or contract_design.get("task_sha256") != reference.get("task_sha256")
        or contract_design.get("receipt_sha256") != reference.get("design_cycle_receipt_sha256")
        or contract_route.get("route") != route.get("route")
        or contract_route.get("path") != route.get("local_path")
    ):
        raise PublicWebsiteDesignRunnerError(
            "Investor-copy repair contract no longer binds the current task, work order, source, policy, route, or claim capsule."
        )
    return contract, contract_path


def _investor_copy_worker_context(
    *,
    reference: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    """Project only privacy-minimised authoring controls to a staged worker."""

    source_audit = _mapping(
        contract.get("source_audit"),
        label="Investor-copy contract source audit",
    )
    claim_control = _mapping(
        contract.get("claim_control"),
        label="Investor-copy contract claim control",
    )
    route = _mapping(
        contract.get("route"),
        label="Investor-copy contract route",
    )
    acceptance = _mapping(
        contract.get("acceptance"),
        label="Investor-copy contract acceptance",
    )
    return {
        "schema": INVESTOR_COPY_WORKER_CONTEXT_SCHEMA,
        "required": True,
        "contract_id": reference["contract_id"],
        "contract_file_sha256": reference["sha256"],
        "contract_json_sha256": _json_sha256(contract),
        "task_id": reference["task_id"],
        "task_sha256": reference["task_sha256"],
        "route": route["route"],
        "path": route["path"],
        "source_audit": {
            "findings_sha256": source_audit["findings_sha256"],
            "rule_histogram": list(source_audit["rule_histogram"]),
            "finding_count": source_audit["finding_count"],
            "blocker_count": source_audit["blocker_count"],
            "warning_count": source_audit["warning_count"],
            "target_blocker_count": source_audit["target_blocker_count"],
            "target_warning_count": source_audit["target_warning_count"],
        },
        "claim_control": {
            "route_claim_capsule_sha256": claim_control["route_claim_capsule_sha256"],
            "required_claim_ids": list(claim_control["required_claim_ids"]),
            "required_concept_groups_sha256": claim_control["required_concept_groups_sha256"],
            "satisfied_concept_ids": list(claim_control["satisfied_concept_ids"]),
        },
        "acceptance": dict(acceptance),
        "authority": {
            "workspace": "exact staged HTML path only",
            "canonical_write_authority": "none",
            "claim_register_mutation": "none",
            "package_authority": "none",
            "deployment_authority": "none",
            "credential_access": "none",
        },
    }


def _investor_copy_evaluations_equal(
    current: Mapping[str, Any],
    stored: Mapping[str, Any],
) -> bool:
    """Compare a replay while retaining the immutable original audit clock."""

    current_value = deepcopy(dict(current))
    stored_value = dict(stored)
    current_value["evaluated_at"] = stored_value.get("evaluated_at")
    current_audit = current_value.get("candidate_audit")
    stored_audit = stored_value.get("candidate_audit")
    if isinstance(current_audit, Mapping) and isinstance(stored_audit, Mapping):
        normalised_audit = dict(current_audit)
        normalised_audit["audited_at"] = stored_audit.get("audited_at")
        current_value["candidate_audit"] = normalised_audit
    return current_value == stored_value


def _safe_site_relative_path(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PublicWebsiteDesignRunnerError(f"{label} must be a non-empty website-relative path.")
    normalised = value.replace("\\", "/")
    path = Path(normalised)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise PublicWebsiteDesignRunnerError(f"{label} must remain a safe website-relative path.")
    return path.as_posix()


def _editorial_authoring_contract(
    *,
    root: Path,
    order: Mapping[str, Any],
    receipt: Mapping[str, Any],
    as_of: datetime | None,
) -> dict[str, Any]:
    """Project only exact route authoring fields from trusted import evidence."""

    control = _mapping(
        order.get("editorial_asset_control"),
        label="Work-order editorial asset control",
    )
    manifest_reference = control.get("provenance_manifest_path")
    if not isinstance(manifest_reference, str) or not manifest_reference:
        raise PublicWebsiteDesignRunnerError("Editorial work order lost its provenance manifest reference.")
    try:
        audit = audit_design_editorial_asset_provenance_file(
            Path(manifest_reference),
            repo_root=root,
            as_of=as_of,
        )
    except DesignEditorialAssetProvenanceError as exc:
        raise PublicWebsiteDesignRunnerError(f"Editorial authoring provenance replay failed: {exc}") from exc
    receipt_provenance = _mapping(
        receipt.get("provenance"),
        label="Editorial import provenance",
    )
    receipt_summary = _mapping(
        receipt.get("summary"),
        label="Editorial import summary",
    )
    manifest_binding = _mapping(
        audit.get("manifest"),
        label="Editorial provenance manifest binding",
    )
    selected_asset_ids = sorted(
        str(value)
        for value in receipt_provenance.get("candidate_ready_asset_ids", [])
        if isinstance(value, str) and value
    )
    if (
        not selected_asset_ids
        or selected_asset_ids != sorted(set(selected_asset_ids))
        or manifest_binding.get("sha256") != receipt_provenance.get("manifest_file_sha256")
    ):
        raise PublicWebsiteDesignRunnerError(
            "Editorial authoring provenance no longer matches the trusted import."
        )

    raw_asset_capsules = audit.get("asset_capsules")
    if not isinstance(raw_asset_capsules, list):
        raise PublicWebsiteDesignRunnerError("Editorial provenance lost its candidate-safe asset capsules.")
    selected_asset_capsules = sorted(
        [
            dict(item)
            for item in raw_asset_capsules
            if isinstance(item, Mapping) and str(item.get("asset_id") or "") in selected_asset_ids
        ],
        key=lambda item: str(item.get("asset_id") or ""),
    )
    if {str(item.get("asset_id") or "") for item in selected_asset_capsules} != set(
        selected_asset_ids
    ) or _json_sha256(selected_asset_capsules) != receipt_provenance.get("selected_asset_capsules_sha256"):
        raise PublicWebsiteDesignRunnerError(
            "Editorial authoring asset capsules drifted from the trusted import."
        )

    layout = _mapping(
        order.get("candidate_layout"),
        label="Editorial authoring candidate layout",
    )
    candidate_site_prefix = str(layout.get("website_path") or "").rstrip("/") + "/"
    raw_imports = receipt.get("imports")
    if not isinstance(raw_imports, list) or not raw_imports:
        raise PublicWebsiteDesignRunnerError("Editorial import receipt lost its exact public import rows.")
    imported_public_paths: set[str] = set()
    import_scope_by_asset: dict[str, dict[str, set[str]]] = {}
    for raw_import in raw_imports:
        imported = _mapping(
            raw_import,
            label="Editorial import row",
        )
        asset_id = str(imported.get("asset_id") or "")
        target = str(imported.get("target") or "")
        if asset_id not in selected_asset_ids or not target.startswith(candidate_site_prefix):
            raise PublicWebsiteDesignRunnerError(
                "Editorial import row escaped its selected asset or candidate website."
            )
        public_path = _safe_site_relative_path(
            target.removeprefix(candidate_site_prefix),
            label="Imported editorial public path",
        )
        imported_public_paths.add(public_path)
        scope = import_scope_by_asset.setdefault(
            asset_id,
            {"routes": set(), "destinations": set(), "surface_ids": set()},
        )
        for key, source_key in (
            ("routes", "route_scopes"),
            ("destinations", "destination_paths"),
            ("surface_ids", "surface_ids"),
        ):
            raw_values = imported.get(source_key)
            if not isinstance(raw_values, list) or not all(
                isinstance(value, str) and value for value in raw_values
            ):
                raise PublicWebsiteDesignRunnerError(
                    "Editorial import row lost its exact route-surface scope."
                )
            scope[key].update(raw_values)

    requirement = _asset_requirement(order)
    if imported_public_paths != set(requirement["declared_binary_paths"]):
        raise PublicWebsiteDesignRunnerError(
            "Editorial authoring variants no longer equal the trusted imported batch."
        )
    raw_allowed_paths = order.get("allowed_paths")
    raw_routes = order.get("routes")
    if not isinstance(raw_allowed_paths, list) or not isinstance(raw_routes, list):
        raise PublicWebsiteDesignRunnerError("Editorial authoring work order lost its route allow-list.")
    allowed_paths = {
        _safe_site_relative_path(value, label="Editorial allowed path") for value in raw_allowed_paths
    }
    routes = {str(value) for value in raw_routes if isinstance(value, str)}

    raw_route_capsules = audit.get("route_asset_capsules")
    if not isinstance(raw_route_capsules, list):
        raise PublicWebsiteDesignRunnerError("Editorial provenance lost its route-bound asset capsules.")
    selected_route_capsules: list[dict[str, Any]] = []
    surfaces: list[dict[str, Any]] = []
    seen_surfaces: set[tuple[str, str]] = set()
    covered_assets: set[str] = set()
    covered_public_paths: set[str] = set()
    for raw_capsule in raw_route_capsules:
        if not isinstance(raw_capsule, Mapping):
            raise PublicWebsiteDesignRunnerError("Editorial provenance contains a malformed route capsule.")
        asset_id = str(raw_capsule.get("asset_id") or "")
        placement = raw_capsule.get("placement")
        route_scope = str(raw_capsule.get("route_scope") or "")
        if asset_id not in selected_asset_ids or not isinstance(
            placement,
            Mapping,
        ):
            continue
        destination = str(placement.get("destination_path") or "")
        if not destination.startswith("website/"):
            raise PublicWebsiteDesignRunnerError("Editorial route capsule escaped the website root.")
        destination_relative = _safe_site_relative_path(
            destination.removeprefix("website/"),
            label="Editorial authoring destination",
        )
        surface_id = str(placement.get("surface_id") or "")
        asset_scope = import_scope_by_asset.get(asset_id)
        if (
            route_scope not in routes
            or destination_relative not in allowed_paths
            or not surface_id
            or asset_scope is None
            or route_scope not in asset_scope["routes"]
            or destination_relative not in asset_scope["destinations"]
            or surface_id not in asset_scope["surface_ids"]
        ):
            continue
        route_capsule = dict(raw_capsule)
        capsule_sha256 = str(route_capsule.pop("route_asset_capsule_sha256", ""))
        if not _SHA256.fullmatch(capsule_sha256) or capsule_sha256 != _json_sha256(route_capsule):
            raise PublicWebsiteDesignRunnerError("Editorial route capsule hash no longer verifies.")
        route_capsule["route_asset_capsule_sha256"] = capsule_sha256

        raw_variants = raw_capsule.get("website_variants")
        if not isinstance(raw_variants, list) or not raw_variants:
            raise PublicWebsiteDesignRunnerError("Editorial route capsule lost its exact variants.")
        variants: list[dict[str, Any]] = []
        seen_roles: set[str] = set()
        for raw_variant in raw_variants:
            variant = _mapping(
                raw_variant,
                label="Editorial route variant",
            )
            role = str(variant.get("role") or "")
            path_value = str(variant.get("path") or "")
            if role not in {"small", "large"} or role in seen_roles or not path_value.startswith("website/"):
                raise PublicWebsiteDesignRunnerError("Editorial route variant role or path is malformed.")
            public_path = _safe_site_relative_path(
                path_value.removeprefix("website/"),
                label="Editorial route public path",
            )
            width = variant.get("width")
            height = variant.get("height")
            media_type = variant.get("media_type")
            if (
                public_path not in imported_public_paths
                or not isinstance(width, int)
                or isinstance(width, bool)
                or width <= 0
                or not isinstance(height, int)
                or isinstance(height, bool)
                or height <= 0
                or media_type != "image/webp"
            ):
                raise PublicWebsiteDesignRunnerError(
                    "Editorial route variant no longer matches its trusted WebP import."
                )
            seen_roles.add(role)
            covered_public_paths.add(public_path)
            variants.append(
                {
                    "role": role,
                    "public_path": public_path,
                    "media_type": media_type,
                    "width": width,
                    "height": height,
                }
            )
        variants.sort(key=lambda item: str(item["role"]))

        public_post_url = raw_capsule.get("public_post_url")
        alt = placement.get("alt")
        caption = placement.get("caption")
        credit = placement.get("credit")
        if not all(
            isinstance(value, str) and value.strip()
            for value in (
                public_post_url,
                alt,
                caption,
                credit,
            )
        ):
            raise PublicWebsiteDesignRunnerError(
                "Editorial route capsule lost its public post URL or safe copy."
            )
        surface_key = (destination_relative, surface_id)
        if surface_key in seen_surfaces:
            raise PublicWebsiteDesignRunnerError(
                "Editorial authoring contract contains a duplicate route surface."
            )
        seen_surfaces.add(surface_key)
        covered_assets.add(asset_id)
        selected_route_capsules.append(route_capsule)
        surfaces.append(
            {
                "route": route_scope,
                "destination": destination_relative,
                "surface_id": surface_id,
                "public_post_url": public_post_url,
                "variants": variants,
                "alt": alt,
                "caption": caption,
                "credit": credit,
            }
        )

    selected_route_capsules.sort(
        key=lambda item: (
            str(item.get("route_scope") or ""),
            str(item.get("asset_id") or ""),
            str(
                _mapping(
                    item.get("placement"),
                    label="Editorial route placement",
                ).get("destination_path")
                or ""
            ),
            str(
                _mapping(
                    item.get("placement"),
                    label="Editorial route placement",
                ).get("surface_id")
                or ""
            ),
        )
    )
    surfaces.sort(
        key=lambda item: (
            str(item["route"]),
            str(item["destination"]),
            str(item["surface_id"]),
        )
    )
    if (
        not surfaces
        or covered_assets != set(selected_asset_ids)
        or covered_public_paths != imported_public_paths
    ):
        raise PublicWebsiteDesignRunnerError(
            "Editorial authoring contract does not exactly cover the trusted import."
        )

    trusted_evidence = {
        "import_receipt_payload_sha256": str(receipt.get("receipt_payload_sha256") or ""),
        "imports_sha256": str(receipt_summary.get("imports_sha256") or ""),
        "provenance_manifest_sha256": str(receipt_provenance.get("manifest_file_sha256") or ""),
        "selected_asset_capsules_sha256": str(receipt_provenance.get("selected_asset_capsules_sha256") or ""),
        "selected_route_asset_capsules_sha256": _json_sha256(selected_route_capsules),
    }
    if not all(_SHA256.fullmatch(value) for value in trusted_evidence.values()):
        raise PublicWebsiteDesignRunnerError("Editorial authoring evidence hashes are malformed.")
    contract: dict[str, Any] = {
        "schema": EDITORIAL_AUTHORING_CONTRACT_SCHEMA,
        "state": "trusted-route-bound",
        "surfaces": surfaces,
        "surfaces_sha256": _json_sha256(surfaces),
        "trusted_evidence": trusted_evidence,
        "trusted_evidence_sha256": _json_sha256(trusted_evidence),
    }
    contract["contract_sha256"] = _json_sha256(contract)
    return contract


def _asset_import_binding(
    *,
    root: Path,
    order: Mapping[str, Any],
    receipt: Mapping[str, Any],
    now: datetime | None,
) -> dict[str, Any]:
    """Build a redacted deterministic job binding from the current replay."""

    try:
        verification = verify_candidate_editorial_asset_import(
            receipt,
            repo_root=root,
            as_of=now,
            verified_at=now,
        )
    except DesignEditorialAssetCandidateImporterError as exc:
        raise PublicWebsiteDesignRunnerError(f"Editorial asset import replay failed: {exc}") from exc
    if verification.get("passed") is not True:
        raise PublicWebsiteDesignRunnerError("Editorial asset import replay did not pass.")
    control = _mapping(
        order.get("editorial_asset_control"),
        label="Work-order editorial asset control",
    )
    receipt_path = _regular_file_under(
        root,
        control.get("receipt_path"),
        label="Editorial asset import receipt",
        allowed_root=(root / DEFAULT_CANDIDATE_ROOT).resolve(),
    )
    receipt_provenance = _mapping(
        receipt.get("provenance"),
        label="Editorial import redacted provenance",
    )
    receipt_summary = _mapping(
        receipt.get("summary"),
        label="Editorial import summary",
    )
    receipt_work_order = _mapping(
        receipt.get("work_order"),
        label="Editorial import work-order binding",
    )
    expected_requirement = _asset_requirement(order)
    raw_imports = receipt.get("imports")
    if not isinstance(raw_imports, list):
        raise PublicWebsiteDesignRunnerError("Editorial import receipt lost its exact import rows.")
    imported_targets = sorted(str(item.get("target")) for item in raw_imports if isinstance(item, Mapping))
    authoring_contract = _editorial_authoring_contract(
        root=root,
        order=order,
        receipt=receipt,
        as_of=now,
    )
    return {
        "required": True,
        "state": "candidate-assets-ready",
        "receipt": {
            "path": _relative_to_repo(root, receipt_path),
            "file_sha256": _sha256_file(receipt_path),
            "payload_sha256": str(receipt.get("receipt_payload_sha256") or ""),
        },
        "verification": {
            "schema": verification.get("schema"),
            "state": verification.get("state"),
            "imports_sha256": receipt_summary.get("imports_sha256"),
            "binary_delta_sha256": receipt_summary.get("imports_sha256"),
            "work_order_json_sha256": receipt_work_order.get("json_sha256"),
            "baseline_tree_sha256": receipt_work_order.get("baseline_tree_sha256"),
        },
        "provenance": {
            "manifest_file_sha256": receipt_provenance.get("manifest_file_sha256"),
            "selected_asset_capsules_sha256": receipt_provenance.get("selected_asset_capsules_sha256"),
            "route_asset_capsules_sha256": authoring_contract["trusted_evidence"][
                "selected_route_asset_capsules_sha256"
            ],
            "candidate_ready_asset_ids": sorted(
                str(value)
                for value in receipt_provenance.get(
                    "candidate_ready_asset_ids",
                    [],
                )
            ),
        },
        "declared_binary_paths": expected_requirement["declared_binary_paths"],
        "imported_targets": imported_targets,
        "authoring_contract": authoring_contract,
        "assets_ready": True,
        "release_eligible": False,
        "package_authority": "none",
        "deployment_authority": "none",
    }


def _atomic_write_json(path: Path, value: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (
        json.dumps(
            dict(value),
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )
    try:
        write_new_file(path, encoded)
    except SecureImmutableArtifactError as exc:
        raise PublicWebsiteDesignRunnerError(
            f"Refusing to overwrite immutable delivery evidence: {path}"
        ) from exc
    return path


def _delivery_directory(root: Path, run_id: str) -> Path:
    delivery_root = _artifact_root(root, DEFAULT_DELIVERY_ROOT, label="Delivery-run artifact root")
    raw_target = delivery_root / run_id
    _reject_link_ancestors(root, raw_target, label="Delivery-run artifact")
    target = raw_target.resolve()
    try:
        target.relative_to(delivery_root)
        target.relative_to(root.resolve())
    except ValueError as exc:
        raise PublicWebsiteDesignRunnerError("Delivery-run artifact escapes its approved root.") from exc
    if target.exists() and (not target.is_dir() or target.is_symlink()):
        raise PublicWebsiteDesignRunnerError("Delivery-run artifact must be a regular directory.")
    return target


def _work_order_path(root: Path, run_id: str) -> Path:
    work_order_root = _artifact_root(root, DEFAULT_WORK_ORDER_ROOT, label="Work-order artifact root")
    raw_target = work_order_root / f"{run_id}.v4.json"
    _reject_link_ancestors(root, raw_target, label="Work-order artifact")
    target = raw_target.resolve()
    try:
        target.relative_to(work_order_root)
        target.relative_to(root.resolve())
    except ValueError as exc:
        raise PublicWebsiteDesignRunnerError("Work-order artifact escapes its approved root.") from exc
    if target.exists() and target.is_symlink():
        raise PublicWebsiteDesignRunnerError("Work-order artifact must not be a symbolic link.")
    return target


def _receipt_sequence(path: Path) -> int:
    match = _RECEIPT_FILE.fullmatch(path.name)
    return int(match.group("sequence")) if match else -1


def _receipt_records(root: Path, run_id: str) -> list[tuple[int, str, Path]]:
    """Return the complete contiguous immutable receipt chain for one run."""

    directory = _delivery_directory(root, run_id)
    if not directory.exists():
        return []
    records: list[tuple[int, str, Path]] = []
    for path in directory.glob("*.json"):
        try:
            details = path.lstat()
        except OSError as exc:
            raise PublicWebsiteDesignRunnerError("Delivery receipts must be readable regular files.") from exc
        if _is_link_or_reparse_point(path) or not stat.S_ISREG(details.st_mode) or details.st_nlink != 1:
            raise PublicWebsiteDesignRunnerError(
                "Delivery receipts must be regular, single-link, reparse-free JSON files."
            )
        match = _RECEIPT_FILE.fullmatch(path.name)
        if match is None or match.group("state") not in _JOB_STATES:
            raise PublicWebsiteDesignRunnerError(
                "Delivery receipt file names must contain a positive sequence and known state."
            )
        records.append((int(match.group("sequence")), match.group("state"), path.resolve()))
    records.sort(key=lambda item: item[0])
    expected_sequences = list(range(1, len(records) + 1))
    if [item[0] for item in records] != expected_sequences:
        raise PublicWebsiteDesignRunnerError(
            "Delivery receipt sequences must be contiguous from 1 without gaps or duplicates."
        )
    return records


def _validate_receipt_lineage(root: Path, job: Mapping[str, Any]) -> bool:
    """Bind a job to its complete on-disk predecessor chain when it exists."""

    try:
        run_id = _safe_run_id(job.get("run_id"))
        state = str(job.get("state") or "")
        records = _receipt_records(root, run_id)
        if not records:
            return state == "work-order-ready" and job.get("previous_receipt") is None
        current = _read_json(records[-1][2], label="Latest delivery receipt")
        if current != dict(job):
            return False
        previous_state: str | None = None
        previous_path: Path | None = None
        immutable_binding: dict[str, Any] | None = None
        lineage_schema: str | None = None
        candidate_qa_binding: dict[str, Any] | None = None
        for sequence, filename_state, path in records:
            receipt = _read_json(path, label="Delivery receipt")
            receipt_schema = str(receipt.get("schema") or "")
            if lineage_schema is None:
                lineage_schema = receipt_schema
            allowed_states = _JOB_STATES if lineage_schema == DELIVERY_JOB_SCHEMA else _LEGACY_JOB_STATES
            if (
                receipt_schema != lineage_schema
                or lineage_schema not in {DELIVERY_JOB_SCHEMA, LEGACY_DELIVERY_JOB_SCHEMA}
                or receipt.get("run_id") != run_id
                or receipt.get("state") != filename_state
                or filename_state not in allowed_states
            ):
                return False
            current_immutable_binding = {field: receipt.get(field) for field in _IMMUTABLE_JOB_FIELDS}
            if immutable_binding is None:
                immutable_binding = current_immutable_binding
            elif current_immutable_binding != immutable_binding:
                return False
            if sequence == 1:
                if filename_state != "work-order-ready" or receipt.get("previous_receipt") is not None:
                    return False
            else:
                transitions = (
                    _ALLOWED_STATE_TRANSITIONS
                    if lineage_schema == DELIVERY_JOB_SCHEMA
                    else _LEGACY_ALLOWED_STATE_TRANSITIONS
                )
                if previous_state is None or filename_state not in transitions.get(
                    previous_state, frozenset()
                ):
                    return False
                previous = receipt.get("previous_receipt")
                if not isinstance(previous, Mapping) or previous_path is None:
                    return False
                expected_previous = {
                    "path": _relative_to_repo(root, previous_path),
                    "sha256": _sha256_file(previous_path),
                }
                if dict(previous) != expected_previous:
                    return False
            if lineage_schema == DELIVERY_JOB_SCHEMA and filename_state in _QA_STATES:
                current_qa = _mapping(
                    receipt.get("candidate_qa"),
                    label="Delivery candidate QA binding",
                )
                if candidate_qa_binding is None:
                    candidate_qa_binding = current_qa
                elif current_qa != candidate_qa_binding:
                    return False
            elif "candidate_qa" in receipt:
                return False
            previous_state = filename_state
            previous_path = path
        return True
    except (OSError, PublicWebsiteDesignRunnerError):
        return False


def _write_next_job(root: Path, job: Mapping[str, Any]) -> Path:
    run_id = _safe_run_id(job.get("run_id"))
    state = str(job.get("state") or "")
    _require_advancing_v2(job, operation="Delivery receipt advancement")
    if state not in _JOB_STATES:
        raise PublicWebsiteDesignRunnerError("Delivery job state is not recognised.")
    directory = _delivery_directory(root, run_id)
    existing = _receipt_records(root, run_id)
    if existing and not _validate_receipt_lineage(
        root, _read_json(existing[-1][2], label="Latest delivery receipt")
    ):
        raise PublicWebsiteDesignRunnerError("Existing delivery receipt chain does not verify.")
    if not existing and (state != "work-order-ready" or job.get("previous_receipt") is not None):
        raise PublicWebsiteDesignRunnerError(
            "A delivery receipt chain must begin with a work-order-ready job."
        )
    if existing:
        _, previous_state, previous_path = existing[-1]
        expected_previous = {
            "path": _relative_to_repo(root, previous_path),
            "sha256": _sha256_file(previous_path),
        }
        if (
            state not in _ALLOWED_STATE_TRANSITIONS.get(previous_state, frozenset())
            or job.get("previous_receipt") != expected_previous
        ):
            raise PublicWebsiteDesignRunnerError(
                "Delivery job does not extend the immutable receipt lifecycle."
            )
    sequence = len(existing) + 1
    target = directory / f"{sequence:02d}-{state}.json"
    return _atomic_write_json(target, job)


def _latest_job_path(root: Path, run_id: str) -> Path:
    records = _receipt_records(root, _safe_run_id(run_id))
    if not records:
        raise PublicWebsiteDesignRunnerError("No delivery receipt exists for this run id.")
    return records[-1][2]


def load_latest_delivery_job(run_id: str, *, repo_root: Path | None = None) -> tuple[dict[str, Any], Path]:
    """Load the newest immutable local receipt for one delivery run."""

    root = _find_repo_root(repo_root)
    path = _latest_job_path(root, run_id)
    job = _read_json(path, label="Delivery job")
    if job.get("schema") not in {
        DELIVERY_JOB_SCHEMA,
        LEGACY_DELIVERY_JOB_SCHEMA,
    }:
        raise PublicWebsiteDesignRunnerError("Delivery receipt schema does not match this runner.")
    match = _RECEIPT_FILE.fullmatch(path.name)
    if match is None or job.get("run_id") != run_id or job.get("state") != match.group("state"):
        raise PublicWebsiteDesignRunnerError(
            "Delivery receipt contents do not match its immutable file identity."
        )
    return job, path


def _route_binding(audit: Mapping[str, Any], *, route_id: str) -> dict[str, Any]:
    if audit.get("schema") != BRIEF_AUDIT_SCHEMA or audit.get("passed") is not True:
        raise PublicWebsiteDesignRunnerError(
            "A currently passing canonical design-evidence brief is required before candidate scope is derived."
        )
    routes = audit.get("route_plan")
    capsules = audit.get("route_claim_capsules")
    feedback_capsules = audit.get("route_feedback_capsules")
    if (
        not isinstance(routes, list)
        or not isinstance(capsules, list)
        or not isinstance(feedback_capsules, list)
    ):
        raise PublicWebsiteDesignRunnerError(
            "Brief audit lacks a route plan, route claim capsules or route feedback capsules."
        )
    route_matches = [item for item in routes if isinstance(item, Mapping) and item.get("id") == route_id]
    capsule_matches = [
        item for item in capsules if isinstance(item, Mapping) and item.get("route_id") == route_id
    ]
    feedback_matches = [
        item for item in feedback_capsules if isinstance(item, Mapping) and item.get("route_id") == route_id
    ]
    if len(route_matches) != 1 or len(capsule_matches) != 1 or len(feedback_matches) != 1:
        raise PublicWebsiteDesignRunnerError(
            "Requested delivery route must occur exactly once in the audited brief."
        )
    route = dict(route_matches[0])
    capsule = dict(capsule_matches[0])
    feedback_capsule = dict(feedback_matches[0])
    allowed_paths = route.get("allowed_paths")
    claim_ids = route.get("claim_ids")
    claims = capsule.get("claims")
    signals = feedback_capsule.get("signals")
    if (
        not isinstance(route.get("route"), str)
        or not isinstance(route.get("local_path"), str)
        or not isinstance(allowed_paths, list)
        or not allowed_paths
        or not all(isinstance(path, str) for path in allowed_paths)
        or not isinstance(claim_ids, list)
        or not claim_ids
        or not isinstance(claims, list)
        or {item.get("id") for item in claims if isinstance(item, Mapping)} != set(claim_ids)
        or feedback_capsule.get("route") != route.get("route")
        or not isinstance(signals, list)
        or not all(isinstance(item, Mapping) for item in signals)
    ):
        raise PublicWebsiteDesignRunnerError(
            "Audited route needs one exact route, allow-list and complete selected claim capsule."
        )
    return {
        "id": route_id,
        "route": route["route"],
        "local_path": route["local_path"],
        "allowed_paths": list(allowed_paths),
        "claim_ids": list(claim_ids),
        "content_order": list(route.get("content_order") or []),
        "claim_capsule": capsule,
        "claim_capsule_sha256": _json_sha256(capsule),
        "feedback_capsule": feedback_capsule,
        "feedback_capsule_sha256": _json_sha256(feedback_capsule),
    }


def _research_refresh_binding(audit: Mapping[str, Any]) -> dict[str, Any]:
    """Keep only the current redacted refresh binding in an immutable job.

    A worker does not need source URLs, evidence snapshots, local receipt
    locations, or artwork metadata.  The job only needs enough information to
    fail closed if the canonical redacted declaration changes, becomes stale,
    or loses its not-cleared artwork boundary.
    """

    refresh = _mapping(audit.get("research_refresh"), label="Brief audit research refresh")
    expected_fields = {
        "declaration_path",
        "declaration_sha256",
        "state",
        "passed",
        "artwork",
    }
    if set(refresh) != expected_fields:
        raise PublicWebsiteDesignRunnerError(
            "Brief audit research refresh must retain exactly the redacted binding fields."
        )
    declaration_path = refresh.get("declaration_path")
    declaration_sha256 = refresh.get("declaration_sha256")
    artwork = _mapping(refresh.get("artwork"), label="Brief audit research refresh artwork")
    if (
        declaration_path != DEFAULT_SOURCE_DECLARATION_PATH.as_posix()
        or not isinstance(declaration_sha256, str)
        or not _SHA256.fullmatch(declaration_sha256)
        or refresh.get("state") != "current"
        or refresh.get("passed") is not True
        or set(artwork) != {"state", "cleared_for_use"}
        or artwork.get("state") != "not-cleared"
        or artwork.get("cleared_for_use") is not False
    ):
        raise PublicWebsiteDesignRunnerError(
            "A currently passing not-cleared redacted research refresh is required before a delivery job can bind a brief."
        )
    return {
        "declaration_path": declaration_path,
        "declaration_sha256": declaration_sha256,
        "state": "current",
        "passed": True,
        "artwork": {"state": "not-cleared", "cleared_for_use": False},
    }


def _stakeholder_feedback_binding(audit: Mapping[str, Any]) -> dict[str, Any]:
    """Keep only the code-only stakeholder binding in an immutable job."""

    feedback = _mapping(
        audit.get("stakeholder_feedback"),
        label="Brief audit stakeholder feedback",
    )
    expected_fields = {
        "feedback_id",
        "path",
        "sha256",
        "state",
        "passed",
        "signal_ids",
        "signal_capsules_sha256",
    }
    if set(feedback) != expected_fields:
        raise PublicWebsiteDesignRunnerError(
            "Brief audit stakeholder feedback must retain exactly the privacy-safe binding fields."
        )
    signal_ids = feedback.get("signal_ids")
    if (
        feedback.get("path") != DEFAULT_FEEDBACK_PATH.as_posix()
        or not isinstance(feedback.get("feedback_id"), str)
        or not feedback["feedback_id"]
        or not isinstance(feedback.get("sha256"), str)
        or not _SHA256.fullmatch(feedback["sha256"])
        or feedback.get("state") != "current"
        or feedback.get("passed") is not True
        or not isinstance(signal_ids, list)
        or not signal_ids
        or not all(isinstance(item, str) and item for item in signal_ids)
        or len(set(signal_ids)) != len(signal_ids)
        or not isinstance(feedback.get("signal_capsules_sha256"), str)
        or not _SHA256.fullmatch(feedback["signal_capsules_sha256"])
    ):
        raise PublicWebsiteDesignRunnerError(
            "A currently passing privacy-safe stakeholder feedback binding is required before a delivery job can bind a brief."
        )
    return {
        "feedback_id": feedback["feedback_id"],
        "path": feedback["path"],
        "sha256": feedback["sha256"],
        "state": "current",
        "passed": True,
        "signal_ids": list(signal_ids),
        "signal_capsules_sha256": feedback["signal_capsules_sha256"],
    }


def _brief_binding(audit: Mapping[str, Any], *, route_id: str) -> dict[str, Any]:
    brief = _mapping(audit.get("brief"), label="Brief audit brief binding")
    research_refresh = _research_refresh_binding(audit)
    stakeholder_feedback = _stakeholder_feedback_binding(audit)
    claim_control = _mapping(audit.get("claim_control"), label="Brief audit claim control")
    source_inputs = audit.get("source_inputs")
    if not isinstance(source_inputs, list):
        raise PublicWebsiteDesignRunnerError("Brief audit source inputs are unavailable.")
    return {
        "audit_schema": str(audit.get("schema") or ""),
        "brief": {
            "id": str(brief.get("brief_id") or ""),
            "path": str(brief.get("path") or ""),
            "sha256": str(brief.get("sha256") or ""),
            "refresh_by": str(brief.get("refresh_by") or ""),
        },
        "research_refresh": research_refresh,
        "stakeholder_feedback": stakeholder_feedback,
        "claim_control": {
            "register_path": str(claim_control.get("register_path") or ""),
            "register_sha256": str(claim_control.get("register_sha256") or ""),
            "claim_ids": list(claim_control.get("claim_ids") or []),
        },
        "source_inputs_sha256": _json_sha256(source_inputs),
        "all_route_claim_capsules_sha256": str(audit.get("route_claim_capsules_sha256") or ""),
        "all_route_feedback_capsules_sha256": str(audit.get("route_feedback_capsules_sha256") or ""),
        "route": _route_binding(audit, route_id=route_id),
    }


def _claim_surface_context(job: Mapping[str, Any]) -> dict[str, Any]:
    """Return the minimal exact route capsule a worker must satisfy for new copy.

    This is deliberately derived from the runner's immutable brief binding,
    never supplied by the worker.  ``validate_design_candidate`` rechecks its
    hash and route identity before a candidate can become validated.
    """

    binding = _mapping(job.get("brief_binding"), label="Delivery job brief binding")
    route = _mapping(binding.get("route"), label="Delivery job route claim binding")
    capsule = _mapping(route.get("claim_capsule"), label="Delivery job route claim capsule")
    allowed_paths = (
        [route.get("local_path")] if _delivery_contract_is_copy(job) else route.get("allowed_paths")
    )
    capsule_sha256 = route.get("claim_capsule_sha256")
    if (
        not isinstance(route.get("id"), str)
        or not route["id"]
        or not isinstance(route.get("route"), str)
        or not route["route"].startswith("/")
        or not isinstance(allowed_paths, list)
        or not allowed_paths
        or not all(isinstance(item, str) and item for item in allowed_paths)
        or not isinstance(capsule_sha256, str)
        or not _SHA256.fullmatch(capsule_sha256)
        or _json_sha256(capsule) != capsule_sha256
    ):
        raise PublicWebsiteDesignRunnerError("Delivery job lacks a sealed exact route claim-surface context.")
    return {
        "id": route["id"],
        "route": route["route"],
        "allowed_paths": list(allowed_paths),
        "claim_capsule": capsule,
        "claim_capsule_sha256": capsule_sha256,
    }


def _stakeholder_feedback_context(job: Mapping[str, Any]) -> dict[str, Any]:
    """Return the exact route-scoped code-only feedback capsule for a worker."""

    binding = _mapping(job.get("brief_binding"), label="Delivery job brief binding")
    route = _mapping(binding.get("route"), label="Delivery job route feedback binding")
    capsule = _mapping(
        route.get("feedback_capsule"),
        label="Delivery job route feedback capsule",
    )
    capsule_sha256 = route.get("feedback_capsule_sha256")
    signals = capsule.get("signals")
    if (
        capsule.get("route_id") != route.get("id")
        or capsule.get("route") != route.get("route")
        or not isinstance(signals, list)
        or not all(isinstance(item, Mapping) for item in signals)
        or not isinstance(capsule_sha256, str)
        or not _SHA256.fullmatch(capsule_sha256)
        or _json_sha256(capsule) != capsule_sha256
    ):
        raise PublicWebsiteDesignRunnerError(
            "Delivery job lacks a sealed exact route stakeholder-feedback context."
        )
    return {
        "id": route["id"],
        "route": route["route"],
        "feedback_capsule": capsule,
        "feedback_capsule_sha256": capsule_sha256,
    }


def _check(identifier: str, passed: bool, message: str, **evidence: Any) -> dict[str, Any]:
    return {"id": identifier, "passed": bool(passed), "message": message, "evidence": evidence}


def _delivery_contract_is_copy(job: Mapping[str, Any]) -> bool:
    """Return the immutable delivery mode or fail on downgrade ambiguity."""

    contract = _mapping(
        job.get("delivery_contract"),
        label="Delivery job contract kind",
    )
    if set(contract) != {"kind", "copy_repair_required"}:
        raise PublicWebsiteDesignRunnerError("Delivery job contract kind is malformed.")
    kind = contract.get("kind")
    copy_required = contract.get("copy_repair_required")
    if (
        kind == "investor-copy-repair"
        and copy_required is True
        and job.get("investor_copy_repair") is not None
    ):
        return True
    if kind == "route-bounded-design" and copy_required is False and job.get("investor_copy_repair") is None:
        return False
    raise PublicWebsiteDesignRunnerError("Delivery job contract kind and investor-copy binding disagree.")


def _copy_for_next_state(
    job: Mapping[str, Any],
    *,
    previous_path: Path,
    root: Path,
    state: str,
    now: datetime | None,
    next_required_stage: str,
) -> dict[str, Any]:
    next_job = deepcopy(dict(job))
    history = list(next_job.get("state_history") or [])
    history.append({"state": state, "recorded_at": _utc_iso(now), "actor": "PublicWebsiteDesignRunner"})
    next_job.update(
        {
            "state": state,
            "updated_at": _utc_iso(now),
            "state_history": history,
            "previous_receipt": {
                "path": _relative_to_repo(root, previous_path),
                "sha256": _sha256_file(previous_path),
            },
            "next_required_stage": next_required_stage,
            "release_eligible": False,
            "package_authority": "none",
            "deployment_authority": "none",
            "authority": dict(AUTHORITY),
        }
    )
    return next_job


def _candidate_qa_binding_verifies(
    *,
    root: Path,
    job: Mapping[str, Any],
    state: str,
    candidate_root: Path,
    candidate_website: Path,
    candidate_validation: Mapping[str, Any],
) -> tuple[bool, str]:
    if job.get("schema") == LEGACY_DELIVERY_JOB_SCHEMA:
        if "candidate_qa" in job:
            return False, "Historical V1 delivery evidence cannot carry V2 candidate QA."
        return True, ""
    if state not in _QA_STATES:
        if "candidate_qa" in job:
            return False, "A pre-QA delivery state cannot carry candidate QA evidence."
        claim_path = _qa_claim_path(candidate_root)
        if state == "candidate-validated" and claim_path.exists():
            return (
                False,
                "The one allowed candidate QA attempt was claimed but no advancing QA receipt exists.",
            )
        return True, ""
    try:
        qa = _mapping(job.get("candidate_qa"), label="Candidate QA binding")
        if (
            set(qa) != _CANDIDATE_QA_FIELDS
            or qa.get("schema") != CANDIDATE_QA_SCHEMA
            or qa.get("attempt_consumed") is not True
            or qa.get("authority") != _CANDIDATE_QA_AUTHORITY
            or qa.get("release_eligible") is not False
            or qa.get("package_authority") != "none"
            or qa.get("deployment_authority") != "none"
        ):
            raise PublicWebsiteDesignRunnerError("Candidate QA authority or shape is malformed.")
        expected_passed = state in _PASSING_QA_STATES
        if qa.get("status") != ("verified" if expected_passed else "repair-required"):
            raise PublicWebsiteDesignRunnerError("Candidate QA status contradicts the delivery state.")
        candidate_receipt_path = _regular_file_under(
            root,
            candidate_validation.get("path"),
            label="Candidate validation receipt",
            allowed_root=candidate_root,
        )
        candidate_receipt_candidate = _mapping(
            _read_json(
                candidate_receipt_path,
                label="Candidate validation receipt",
            ).get("candidate"),
            label="Candidate validation receipt candidate",
        )
        candidate = _mapping(qa.get("candidate"), label="Candidate QA candidate")
        candidate_snapshot = _candidate_qa_tree_binding(
            root,
            candidate_website,
            label="Candidate QA staged tree",
        )
        if (
            candidate_snapshot.get("candidate_tree_sha256") != candidate_receipt_candidate.get("tree_sha256")
            or candidate_snapshot.get("file_count") != candidate_receipt_candidate.get("file_count")
            or candidate_snapshot.get("total_bytes") != candidate_receipt_candidate.get("total_bytes")
        ):
            raise PublicWebsiteDesignRunnerError(
                "The candidate validation receipt and single captured QA manifest disagree."
            )
        expected_candidate = {
            "root": _relative_to_repo(root, candidate_root),
            "website_path": _relative_to_repo(root, candidate_website),
            "validation_tree_sha256": candidate_snapshot["candidate_tree_sha256"],
            "candidate_tree_algorithm": candidate_snapshot["candidate_tree_algorithm"],
            "motion_tree_sha256": candidate_snapshot["motion_tree_sha256"],
            "motion_tree_algorithm": candidate_snapshot["motion_tree_algorithm"],
            "captured_manifest_sha256": candidate_snapshot["captured_manifest_sha256"],
            "validation_receipt": {
                "path": candidate_validation.get("path"),
                "sha256": candidate_validation.get("sha256"),
            },
        }
        if set(candidate) != _CANDIDATE_QA_CANDIDATE_FIELDS or candidate != expected_candidate:
            raise PublicWebsiteDesignRunnerError(
                "Candidate QA evidence belongs to a different candidate or validation receipt."
            )
        if candidate_snapshot.get("root") != candidate.get("website_path"):
            raise PublicWebsiteDesignRunnerError("The staged candidate changed after its QA attempt.")
        canonical = _mapping(
            qa.get("canonical_website"),
            label="Candidate QA canonical website",
        )
        current_canonical = _static_tree_binding(
            root,
            root / "website",
            expected_kind="canonical-static-tree",
            label="Candidate QA canonical website",
        )
        if canonical != current_canonical:
            raise PublicWebsiteDesignRunnerError(
                "The canonical website changed after the candidate QA attempt."
            )
        trusted_toolchain = _mapping(
            qa.get("trusted_toolchain"),
            label="Candidate QA trusted toolchain",
        )
        if trusted_toolchain != _trusted_qa_toolchain_binding(root):
            raise PublicWebsiteDesignRunnerError(
                "Candidate QA source files no longer equal the runner startup capture."
            )

        attempt = _mapping(qa.get("attempt"), label="Candidate QA attempt")
        if set(attempt) != {"path", "sha256", "claim_payload_sha256"}:
            raise PublicWebsiteDesignRunnerError("Candidate QA attempt binding is malformed.")
        claim_path = _regular_file_under(
            root,
            attempt.get("path"),
            label="Candidate QA attempt",
            allowed_root=candidate_root,
        )
        claim = _read_json(claim_path, label="Candidate QA attempt")
        claim_payload = dict(claim)
        claim_payload_sha256 = claim_payload.pop("claim_payload_sha256", None)
        if (
            set(claim) != _CANDIDATE_QA_CLAIM_FIELDS
            or attempt.get("sha256") != _sha256_file(claim_path)
            or claim_payload_sha256 != _json_sha256(claim_payload)
            or attempt.get("claim_payload_sha256") != claim_payload_sha256
            or claim.get("schema") != CANDIDATE_QA_CLAIM_SCHEMA
            or claim.get("state") != "qa-execution-claimed"
            or claim.get("run_id") != job.get("run_id")
            or claim.get("candidate") != candidate
            or claim.get("canonical_website") != canonical
            or claim.get("trusted_toolchain") != trusted_toolchain
            or claim.get("authority") != _CANDIDATE_QA_AUTHORITY
            or claim.get("release_eligible") is not False
            or claim.get("package_authority") != "none"
            or claim.get("deployment_authority") != "none"
        ):
            raise PublicWebsiteDesignRunnerError(
                "Candidate QA attempt claim is stale, substituted, or authority-bearing."
            )

        motion = _mapping(qa.get("motion"), label="Candidate QA motion evidence")
        if set(motion) != {
            "config",
            "state",
            "receipt",
            "eligible_for_next_local_gate",
            "replayed",
        }:
            raise PublicWebsiteDesignRunnerError("Candidate QA motion evidence is malformed.")
        motion_config = _mapping(
            motion.get("config"),
            label="Candidate QA motion configuration",
        )
        if (
            motion_config != claim.get("motion_config")
            or motion.get("state") not in {"passed", "blocked"}
            or motion.get("replayed") is not True
        ):
            raise PublicWebsiteDesignRunnerError("Candidate QA motion configuration or replay seal drifted.")
        config_path, current_config = _pinned_file_binding(
            root,
            Path(str(motion_config.get("path") or "")),
            str(motion_config.get("sha256") or ""),
            label="Candidate QA motion configuration",
        )
        if current_config != motion_config:
            raise PublicWebsiteDesignRunnerError("Candidate QA motion configuration binding is stale.")
        motion_compiler_binding = _mapping(
            qa.get("motion_config_compiler"),
            label="Candidate QA motion-config compiler verification",
        )
        if motion_compiler_binding != claim.get("motion_config_compiler"):
            raise PublicWebsiteDesignRunnerError(
                "Candidate QA motion-config compiler binding drifted from the consumed attempt."
            )
        motion_compiler_replay = _verify_compiled_candidate_motion_config_file_sealed(
            config_path,
            expected_config_sha256=str(motion_config.get("sha256") or ""),
            candidate_receipt_path=candidate_receipt_path,
            repo_root=root,
        )
        if motion_compiler_binding != motion_compiler_replay or not _motion_compiler_verification_matches(
            motion_compiler_binding,
            candidate_receipt_path=candidate_validation.get("path"),
            candidate_tree_sha256=candidate.get("validation_tree_sha256"),
            candidate_tree_algorithm=candidate.get("candidate_tree_algorithm"),
            motion_tree_sha256=candidate.get("motion_tree_sha256"),
            motion_tree_algorithm=candidate.get("motion_tree_algorithm"),
            captured_manifest_sha256=candidate.get("captured_manifest_sha256"),
            config_path=motion_config.get("path"),
            config_file_sha256=motion_config.get("sha256"),
        ):
            raise PublicWebsiteDesignRunnerError(
                "Candidate QA motion configuration no longer equals the fixed compiler result."
            )
        motion_receipt = _mapping(
            motion.get("receipt"),
            label="Candidate QA motion receipt",
        )
        if set(motion_receipt) != {"path", "sha256", "receipt_sha256"}:
            raise PublicWebsiteDesignRunnerError("Candidate QA motion receipt binding is malformed.")
        motion_path = _regular_file_under(
            root,
            motion_receipt.get("path"),
            label="Candidate QA motion receipt",
            allowed_root=(root / "artifacts" / "website-operator" / "motion-performance-budget").resolve(),
        )
        replayed_motion = validate_motion_performance_receipt(
            motion_path,
            repo_root=root,
        )
        decision = _mapping(
            replayed_motion.get("decision"),
            label="Candidate QA motion decision",
        )
        source = _mapping(
            replayed_motion.get("source"),
            label="Candidate QA motion source",
        )
        config_receipt = _mapping(
            replayed_motion.get("config"),
            label="Candidate QA motion receipt configuration",
        )
        motion_passed = (
            decision.get("status") == "pass" and decision.get("eligible_for_next_local_gate") is True
        )
        if (
            motion_receipt.get("sha256") != _sha256_file(motion_path)
            or motion_receipt.get("receipt_sha256") != replayed_motion.get("receipt_sha256")
            or config_receipt.get("path") != _relative_to_repo(root, config_path)
            or config_receipt.get("sha256") != motion_config.get("sha256")
            or source.get("kind") != "staged-static-tree"
            or source.get("root") != candidate.get("website_path")
            or source.get("observed_tree_sha256") != candidate.get("motion_tree_sha256")
            or motion.get("state") != ("passed" if motion_passed else "blocked")
            or motion.get("eligible_for_next_local_gate") is not motion_passed
        ):
            raise PublicWebsiteDesignRunnerError(
                "Candidate QA motion receipt is stale, cross-run, or contradictory."
            )

        tests = _mapping(qa.get("tests"), label="Candidate QA test evidence")
        if set(tests) != {
            "policy",
            "state",
            "receipt",
            "evidence_passed",
            "ordered_command_ids_sha256",
            "command_count",
            "trusted_same_process_execution_write",
            "structural_verification_origin_attested",
            "replayed",
            "candidate_tree_sha256",
            "canonical_website_tree_sha256",
        }:
            raise PublicWebsiteDesignRunnerError("Candidate QA test evidence is malformed.")
        test_policy = _mapping(
            tests.get("policy"),
            label="Candidate QA test policy",
        )
        if test_policy != claim.get("test_policy"):
            raise PublicWebsiteDesignRunnerError(
                "Candidate QA test policy drifted from the consumed attempt."
            )
        policy_path, current_policy = _pinned_file_binding(
            root,
            Path(str(test_policy.get("path") or "")),
            str(test_policy.get("sha256") or ""),
            label="Candidate QA test policy",
        )
        if current_policy != test_policy:
            raise PublicWebsiteDesignRunnerError("Candidate QA test policy binding is stale.")
        policy = _read_json(policy_path, label="Candidate QA test policy")
        command_ids = policy.get("required_command_ids")
        command_count = len(command_ids) if isinstance(command_ids, list) else -1
        policy_content_core_sha256 = policy.get("content_core_sha256")
        compiler_binding = _mapping(
            qa.get("test_policy_compiler"),
            label="Candidate QA test-policy compiler verification",
        )
        if compiler_binding != claim.get("test_policy_compiler"):
            raise PublicWebsiteDesignRunnerError(
                "Candidate QA test-policy compiler binding drifted from the consumed attempt."
            )
        compiler_replay = _verify_compiled_candidate_test_policy_file_sealed(
            policy_path,
            expected_policy_sha256=str(test_policy.get("sha256") or ""),
            candidate_receipt_path=candidate_receipt_path,
            repo_root=root,
        )
        if (
            compiler_binding != compiler_replay
            or not _test_compiler_verification_matches(
                compiler_binding,
                candidate_receipt_path=candidate_validation.get("path"),
                candidate_tree_sha256=candidate.get("validation_tree_sha256"),
                policy_path=test_policy.get("path"),
                policy_content_core_sha256=policy_content_core_sha256,
                policy_file_sha256=test_policy.get("sha256"),
                required_command_ids=command_ids,
            )
            or tests.get("ordered_command_ids_sha256") != _json_sha256(command_ids)
            or tests.get("command_count") != command_count
            or tests.get("structural_verification_origin_attested") is not False
        ):
            raise PublicWebsiteDesignRunnerError("Candidate QA ordered test-policy seal is malformed.")
        command_ids = cast(list[str], command_ids)
        if not motion_passed:
            tests_ok = (
                tests.get("state") == "not-run-motion-blocked"
                and tests.get("receipt") is None
                and tests.get("evidence_passed") is False
                and tests.get("trusted_same_process_execution_write") is False
                and tests.get("replayed") is False
                and tests.get("candidate_tree_sha256") is None
                and tests.get("canonical_website_tree_sha256") is None
            )
            if not tests_ok or expected_passed:
                raise PublicWebsiteDesignRunnerError(
                    "Blocked motion must consume QA without running or passing tests."
                )
        else:
            test_receipt = _mapping(
                tests.get("receipt"),
                label="Candidate QA test receipt",
            )
            if set(test_receipt) != {
                "path",
                "sha256",
                "receipt_payload_sha256",
            }:
                raise PublicWebsiteDesignRunnerError("Candidate QA test receipt binding is malformed.")
            test_path = _regular_file_under(
                root,
                test_receipt.get("path"),
                label="Candidate QA test receipt",
                allowed_root=candidate_root,
            )
            test_verification = verify_candidate_test_evidence_receipt(
                test_path,
                expected_receipt_file_sha256=str(test_receipt.get("sha256") or ""),
                policy_path=policy_path,
                expected_policy_sha256=str(test_policy.get("sha256") or ""),
                repo_root=root,
            )
            evidence_passed = test_verification.get("evidence_passed") is True
            if (
                test_receipt.get("sha256") != _sha256_file(test_path)
                or test_receipt.get("receipt_payload_sha256")
                != test_verification.get("receipt_payload_sha256")
                or test_verification.get("origin_attested") is not False
                or test_verification.get("candidate_tree_sha256") != candidate.get("validation_tree_sha256")
                or test_verification.get("candidate_tree_sha256") != tests.get("candidate_tree_sha256")
                or test_verification.get("canonical_website_tree_sha256")
                != tests.get("canonical_website_tree_sha256")
                or test_verification.get("policy_file_sha256") != test_policy.get("sha256")
                or test_verification.get("schema") != _test_evidence_module.VERIFICATION_SCHEMA
                or tests.get("state") != ("passed" if evidence_passed else "failed")
                or tests.get("evidence_passed") is not evidence_passed
                or tests.get("trusted_same_process_execution_write") is not True
                or tests.get("replayed") is not True
                or expected_passed is not evidence_passed
            ):
                raise PublicWebsiteDesignRunnerError(
                    "Candidate QA test evidence is stale, cross-run, worker-asserted, or contradictory."
                )
        return True, ""
    except (
        DesignCandidateTestEvidenceError,
        DesignMotionPerformanceBudgetError,
        OSError,
        PublicWebsiteDesignRunnerError,
        TypeError,
        ValueError,
    ) as exc:
        return False, str(exc)


def verify_design_delivery_job(
    job: Mapping[str, Any], *, repo_root: Path | None = None, now: datetime | None = None
) -> dict[str, Any]:
    """Revalidate a job's brief binding and immutable work order without release authority."""

    root = _find_repo_root(repo_root)
    checks: list[dict[str, Any]] = []
    checks.append(
        _check(
            "schema-and-authority",
            job.get("schema") in {DELIVERY_JOB_SCHEMA, LEGACY_DELIVERY_JOB_SCHEMA}
            and job.get("authority") == AUTHORITY
            and job.get("release_eligible") is False
            and job.get("package_authority") == "none"
            and job.get("deployment_authority") == "none",
            "Delivery jobs must retain their non-authoritative staged-candidate boundary.",
            compatibility=(
                "current-v2" if job.get("schema") == DELIVERY_JOB_SCHEMA else "historical-v1-read-only"
            ),
        )
    )
    try:
        run_id = _safe_run_id(job.get("run_id"))
        state = job.get("state")
        identity_ok = state in _JOB_STATES
    except PublicWebsiteDesignRunnerError:
        run_id = ""
        state = ""
        identity_ok = False
    checks.append(
        _check(
            "identity-and-state",
            identity_ok,
            "Delivery jobs need a safe run id and a recognised pre-owner lifecycle state.",
            run_id=run_id,
            state=state,
        )
    )
    try:
        copy_mode = _delivery_contract_is_copy(job)
        delivery_contract_ok = True
        delivery_contract_error = ""
    except PublicWebsiteDesignRunnerError as exc:
        copy_mode = False
        delivery_contract_ok = False
        delivery_contract_error = str(exc)
    checks.append(
        _check(
            "delivery-contract-kind",
            delivery_contract_ok,
            "Every run must retain one immutable generic-design or required investor-copy contract kind.",
            copy_repair_required=copy_mode,
            error=delivery_contract_error,
        )
    )

    binding_ok = False
    binding_error = ""
    try:
        binding = _mapping(job.get("brief_binding"), label="Delivery job brief binding")
        route = _mapping(binding.get("route"), label="Delivery job route binding")
        route_id = route.get("id")
        if not isinstance(route_id, str) or not route_id:
            raise PublicWebsiteDesignRunnerError("Delivery job route id is unavailable.")
        current_audit = audit_design_evidence_brief_file(repo_root=root, as_of=now)
        binding_ok = binding == _brief_binding(current_audit, route_id=route_id)
        if not binding_ok:
            binding_error = (
                "The canonical brief, redacted research refresh, stakeholder signals, claim capsules or selected route changed "
                "after this job was issued."
            )
    except (DesignEvidenceBriefError, PublicWebsiteDesignRunnerError) as exc:
        binding_error = str(exc)
    checks.append(
        _check(
            "current-brief-binding",
            binding_ok,
            "The job must exactly match a currently passing canonical brief, exact route claim capsule and code-only stakeholder capsule.",
            error=binding_error,
        )
    )

    work_order_ok = False
    work_order_error = ""
    order: dict[str, Any] | None = None
    work_order_path: Path | None = None
    work_order_ref: dict[str, Any] | None = None
    route_binding: dict[str, Any] | None = None
    try:
        work_order_ref = _mapping(job.get("work_order"), label="Delivery job work order")
        work_order_path = _regular_file_under(
            root,
            work_order_ref.get("path"),
            label="Delivery job work order",
            allowed_root=(root / DEFAULT_WORK_ORDER_ROOT).resolve(),
        )
        order = _read_json(work_order_path, label="Delivery job work order")
        order_verification = verify_design_work_order(order, repo_root=root)
        route_binding = _mapping(
            _mapping(job.get("brief_binding"), label="Brief binding").get("route"), label="Route binding"
        )
        expected_allowed_paths = (
            [route_binding.get("local_path")]
            if copy_mode
            else sorted(route_binding.get("allowed_paths") or [])
        )
        work_order_ok = (
            work_order_ref.get("sha256") == _sha256_file(work_order_path)
            and work_order_ref.get("run_id") == run_id
            and order.get("run_id") == run_id
            and order.get("routes") == [route_binding.get("route")]
            and order.get("allowed_paths") == expected_allowed_paths
            and order_verification.get("passed") is True
        )
        if not work_order_ok:
            work_order_error = (
                "The immutable work order no longer matches the job binding or current control."
            )
    except (DesignCandidateControlError, PublicWebsiteDesignRunnerError) as exc:
        work_order_error = str(exc)
    checks.append(
        _check(
            "current-work-order-binding",
            work_order_ok,
            "The job must retain one current verified exact-path staged work order derived from its audited route.",
            error=work_order_error,
        )
    )

    investor_copy_contract: dict[str, Any] | None = None
    investor_copy_ok = delivery_contract_ok and not copy_mode and job.get("investor_copy_repair") is None
    investor_copy_error = ""
    if copy_mode:
        try:
            if not work_order_ok or work_order_ref is None or route_binding is None:
                raise PublicWebsiteDesignRunnerError(
                    "Current route and work order are unavailable for investor-copy contract replay."
                )
            loaded_contract = _load_investor_copy_contract(
                root=root,
                job=job,
                route=route_binding,
                work_order_ref=work_order_ref,
                now=now,
            )
            if loaded_contract is None:
                raise PublicWebsiteDesignRunnerError("Investor-copy repair binding disappeared.")
            investor_copy_contract, _ = loaded_contract
            investor_copy_ok = True
        except (
            InvestorCopyRepairError,
            PublicWebsiteDesignRunnerError,
            OSError,
            TypeError,
            ValueError,
        ) as exc:
            investor_copy_ok = False
            investor_copy_error = str(exc)
    checks.append(
        _check(
            "investor-copy-contract-binding",
            investor_copy_ok,
            "Optional DESIGN-COPY jobs must retain one current immutable task, source, policy, route, work-order, and claim-capsule contract.",
            required=copy_mode,
            error=investor_copy_error,
        )
    )

    asset_requirement: dict[str, Any] | None = None
    asset_requirement_ok = False
    asset_requirement_error = ""
    try:
        if order is None:
            raise PublicWebsiteDesignRunnerError(
                "Current work order is unavailable for asset requirement binding."
            )
        asset_requirement = _asset_requirement(order)
        stored_requirement = _mapping(
            job.get("asset_requirement"),
            label="Delivery job asset requirement",
        )
        asset_requirement_ok = stored_requirement == asset_requirement
        if not asset_requirement_ok:
            asset_requirement_error = (
                "The runner asset requirement no longer matches the exact v4 work order."
            )
    except PublicWebsiteDesignRunnerError as exc:
        asset_requirement_error = str(exc)
        asset_requirement_ok = False
    checks.append(
        _check(
            "asset-requirement-binding",
            asset_requirement_ok,
            "Every delivery job must derive its trusted binary requirement from the exact v4 path allow-list.",
            error=asset_requirement_error,
        )
    )

    candidate_root: Path | None = None
    candidate_website: Path | None = None
    candidate_validation: dict[str, Any] | None = None
    candidate_binding_ok = state not in _CANDIDATE_STATES
    candidate_binding_error = ""
    if state in _CANDIDATE_STATES:
        try:
            if order is None or work_order_path is None:
                raise PublicWebsiteDesignRunnerError(
                    "Current work order is unavailable for candidate binding."
                )
            layout = _mapping(order.get("candidate_layout"), label="Work-order candidate layout")
            staged = _mapping(job.get("candidate"), label="Staged candidate")
            candidate_root = _regular_directory_under(
                root,
                layout.get("root"),
                label="Staged candidate root",
                allowed_root=_artifact_root(root, DEFAULT_CANDIDATE_ROOT, label="Candidate artifact root"),
            )
            candidate_website = _regular_directory_under(
                root,
                layout.get("website_path"),
                label="Staged candidate website",
                allowed_root=candidate_root,
            )
            expected_staged = {
                "candidate_root": _relative_to_repo(root, candidate_root),
                "candidate_website": _relative_to_repo(root, candidate_website),
                "staged_claim_register": str(layout.get("staged_claim_register_path") or ""),
                "work_order": _relative_to_repo(root, work_order_path),
            }
            candidate_binding_ok = staged == expected_staged
            if not candidate_binding_ok:
                candidate_binding_error = (
                    "The staged workspace no longer matches the deterministic work-order layout."
                )
            if state in _VALIDATED_CANDIDATE_STATES:
                candidate_validation = _mapping(
                    job.get("candidate_validation"), label="Candidate validation binding"
                )
                candidate_receipt_path = _regular_file_under(
                    root,
                    candidate_validation.get("path"),
                    label="Candidate validation receipt",
                    allowed_root=candidate_root,
                )
                candidate_receipt = _read_json(candidate_receipt_path, label="Candidate validation receipt")
                expected_passed = state in _PASSING_CANDIDATE_STATES
                control_passed = candidate_validation.get(
                    "control_passed",
                    candidate_validation.get("passed"),
                )
                candidate_binding_ok = candidate_binding_ok and (
                    candidate_validation.get("sha256") == _sha256_file(candidate_receipt_path)
                    and candidate_validation.get("passed") is expected_passed
                    and isinstance(control_passed, bool)
                    and candidate_receipt.get("schema") == CANDIDATE_SCHEMA
                    and candidate_receipt.get("passed") is control_passed
                    and _mapping(candidate_receipt.get("candidate"), label="Candidate receipt candidate")
                    == {
                        "root": _relative_to_repo(root, candidate_root),
                        "website_path": _relative_to_repo(root, candidate_website),
                        "tree_sha256": _mapping(
                            candidate_receipt.get("candidate"), label="Candidate receipt candidate"
                        ).get("tree_sha256"),
                        "file_count": _mapping(
                            candidate_receipt.get("candidate"), label="Candidate receipt candidate"
                        ).get("file_count"),
                        "total_bytes": _mapping(
                            candidate_receipt.get("candidate"), label="Candidate receipt candidate"
                        ).get("total_bytes"),
                    }
                    and _mapping(
                        candidate_receipt.get("work_order"), label="Candidate receipt work order"
                    ).get("run_id")
                    == run_id
                )
                if control_passed is True:
                    candidate_binding_ok = candidate_binding_ok and (
                        verify_staged_candidate_receipt(candidate_receipt, repo_root=root).get("passed")
                        is True
                    )
                if not candidate_binding_ok and not candidate_binding_error:
                    candidate_binding_error = (
                        "Candidate validation evidence no longer binds the unchanged staged workspace."
                    )
        except (DesignCandidateControlError, PublicWebsiteDesignRunnerError):
            candidate_binding_ok = False
            candidate_binding_error = (
                "Candidate workspace or validation evidence is missing, stale, or out of scope."
            )
    checks.append(
        _check(
            "candidate-workspace-and-validation-binding",
            candidate_binding_ok,
            "Every staged state must retain its exact deterministic candidate workspace and hash-bound validation evidence.",
            error=candidate_binding_error,
        )
    )

    investor_copy_evaluation_ok = investor_copy_ok
    investor_copy_evaluation_error = ""
    copy_required = copy_mode
    if not copy_required:
        investor_copy_evaluation_ok = "investor_copy_evaluation" not in job
        if not investor_copy_evaluation_ok:
            investor_copy_evaluation_error = (
                "A generic delivery job cannot claim an investor-copy candidate evaluation."
            )
    elif state not in _VALIDATED_CANDIDATE_STATES:
        investor_copy_evaluation_ok = investor_copy_ok and "investor_copy_evaluation" not in job
        if not investor_copy_evaluation_ok:
            investor_copy_evaluation_error = (
                "Pre-validation copy jobs cannot carry candidate evaluation evidence."
            )
    else:
        try:
            if (
                not investor_copy_ok
                or investor_copy_contract is None
                or candidate_root is None
                or candidate_website is None
                or candidate_validation is None
            ):
                raise PublicWebsiteDesignRunnerError(
                    "Current contract and candidate evidence are unavailable for investor-copy evaluation replay."
                )
            stored_evaluation = _mapping(
                job.get("investor_copy_evaluation"),
                label="Investor-copy candidate evaluation",
            )
            current_evaluation = evaluate_investor_copy_repair_candidate(
                investor_copy_contract,
                candidate_website_root=candidate_website,
                route_claim_capsule=_mapping(
                    route_binding.get("claim_capsule") if route_binding else None,
                    label="Delivery job route claim capsule",
                ),
                repo_root=root,
                as_of=now,
            )
            control_passed = candidate_validation.get(
                "control_passed",
                candidate_validation.get("passed"),
            )
            combined_passed = control_passed is True and stored_evaluation.get("passed") is True
            investor_copy_evaluation_ok = (
                stored_evaluation.get("schema") == INVESTOR_COPY_REPAIR_EVALUATION_SCHEMA
                and isinstance(stored_evaluation.get("passed"), bool)
                and _investor_copy_evaluations_equal(
                    current_evaluation,
                    stored_evaluation,
                )
                and stored_evaluation.get("contract_id")
                == _mapping(
                    job.get("investor_copy_repair"),
                    label="Investor-copy repair binding",
                ).get("contract_id")
                and stored_evaluation.get("contract_sha256") == _json_sha256(investor_copy_contract)
                and candidate_validation.get("passed") is combined_passed
                and combined_passed == (state in _PASSING_CANDIDATE_STATES)
            )
            if not investor_copy_evaluation_ok:
                investor_copy_evaluation_error = "Stored investor-copy evaluation no longer equals the current exact candidate, contract, policy, or combined validation state."
        except (
            InvestorCopyRepairError,
            PublicWebsiteDesignRunnerError,
            OSError,
            TypeError,
            ValueError,
        ) as exc:
            investor_copy_evaluation_ok = False
            investor_copy_evaluation_error = str(exc)
    checks.append(
        _check(
            "investor-copy-candidate-evaluation-binding",
            investor_copy_evaluation_ok,
            "DESIGN-COPY candidates must retain one immutable current full-policy re-audit; generic jobs cannot claim one.",
            required=copy_required,
            state=state,
            error=investor_copy_evaluation_error,
        )
    )

    asset_import_ok = asset_requirement_ok
    asset_import_error = ""
    asset_import_required = bool(asset_requirement and asset_requirement.get("required") is True)
    asset_import_states = _CANDIDATE_STATES.difference({"candidate-staged"})
    if asset_import_ok and not asset_import_required:
        asset_import_ok = state != "candidate-assets-ready" and "asset_import" not in job
        if not asset_import_ok:
            asset_import_error = "A text-only delivery job cannot claim candidate asset readiness."
    elif asset_import_ok and asset_import_required:
        if state in {"work-order-ready", "candidate-staged"}:
            asset_import_ok = "asset_import" not in job
            if not asset_import_ok:
                asset_import_error = "Pre-import delivery state cannot carry an adopted asset receipt."
        elif state in asset_import_states:
            try:
                if order is None:
                    raise PublicWebsiteDesignRunnerError(
                        "Current work order is unavailable for asset import replay."
                    )
                stored_asset_import = _mapping(
                    job.get("asset_import"),
                    label="Delivery job asset import",
                )
                control = _mapping(
                    order.get("editorial_asset_control"),
                    label="Work-order editorial asset control",
                )
                receipt_path = _regular_file_under(
                    root,
                    control.get("receipt_path"),
                    label="Editorial asset import receipt",
                    allowed_root=(root / DEFAULT_CANDIDATE_ROOT).resolve(),
                )
                receipt = _read_json(
                    receipt_path,
                    label="Editorial asset import receipt",
                )
                current_asset_import = _asset_import_binding(
                    root=root,
                    order=order,
                    receipt=receipt,
                    now=now,
                )
                asset_import_ok = stored_asset_import == current_asset_import
                if not asset_import_ok:
                    asset_import_error = (
                        "The stored asset-ready binding no longer equals the current "
                        "receipt, binary delta, provenance capsules, or v4 work order."
                    )
            except (
                DesignEditorialAssetCandidateImporterError,
                PublicWebsiteDesignRunnerError,
                OSError,
                TypeError,
                ValueError,
            ) as exc:
                asset_import_ok = False
                asset_import_error = str(exc)
        else:
            asset_import_ok = False
            asset_import_error = (
                "Binary-bearing delivery jobs must enter candidate-assets-ready before validation."
            )
    checks.append(
        _check(
            "asset-import-replay-binding",
            asset_import_ok,
            "Binary-bearing jobs must retain a runner-adopted immutable importer receipt and current provenance replay; text-only jobs cannot claim asset readiness.",
            required=asset_import_required,
            state=state,
            error=asset_import_error,
        )
    )

    candidate_qa_ok = state not in _CANDIDATE_STATES
    candidate_qa_error = ""
    if state in _VALIDATED_CANDIDATE_STATES:
        if candidate_root is None or candidate_website is None or candidate_validation is None:
            candidate_qa_ok = False
            candidate_qa_error = "Current candidate validation is unavailable for candidate QA replay."
        else:
            candidate_qa_ok, candidate_qa_error = _candidate_qa_binding_verifies(
                root=root,
                job=job,
                state=str(state),
                candidate_root=candidate_root,
                candidate_website=candidate_website,
                candidate_validation=candidate_validation,
            )
    elif state in _CANDIDATE_STATES:
        candidate_qa_ok = "candidate_qa" not in job
        if not candidate_qa_ok:
            candidate_qa_error = "A pre-validation state cannot carry candidate QA evidence."
    checks.append(
        _check(
            "candidate-qa-binding",
            candidate_qa_ok,
            "V2 post-validation states must replay one consumed motion-first trusted QA attempt for the exact unchanged candidate, policy, canonical tree and receipts.",
            error=candidate_qa_error,
        )
    )

    initial_gate_ok = state not in _INITIAL_GATE_STATES
    initial_gate_error = ""
    if state in _INITIAL_GATE_STATES:
        try:
            if candidate_root is None or candidate_website is None or candidate_validation is None:
                raise PublicWebsiteDesignRunnerError(
                    "Candidate validation is unavailable for initial-gate binding."
                )
            initial_gate = _mapping(job.get("initial_gate"), label="Initial-gate binding")
            initial_gate_path = _regular_file_under(
                root,
                initial_gate.get("path"),
                label="Initial-gate receipt",
                allowed_root=candidate_root,
            )
            initial_gate_receipt = _read_json(initial_gate_path, label="Initial-gate receipt")
            expected_initial_passed = state in _PASSING_INITIAL_GATE_STATES
            gate_candidate = _mapping(initial_gate_receipt.get("candidate"), label="Initial-gate candidate")
            initial_gate_ok = (
                initial_gate.get("sha256") == _sha256_file(initial_gate_path)
                and initial_gate.get("passed") is expected_initial_passed
                and initial_gate.get("state") == initial_gate_receipt.get("state")
                and initial_gate_receipt.get("schema") == INITIAL_GATE_SCHEMA
                and initial_gate_receipt.get("passed") is expected_initial_passed
                and initial_gate_receipt.get("release_eligible") is False
                and initial_gate_receipt.get("package_authority") == "none"
                and initial_gate_receipt.get("deployment_authority") == "none"
                and _mapping(gate_candidate.get("receipt"), label="Initial-gate candidate receipt")
                == {
                    "path": candidate_validation.get("path"),
                    "sha256": candidate_validation.get("sha256"),
                }
                and gate_candidate.get("root") == _relative_to_repo(root, candidate_root)
                and gate_candidate.get("website_path") == _relative_to_repo(root, candidate_website)
            )
            if not initial_gate_ok:
                initial_gate_error = "Initial-gate evidence no longer binds the validated staged candidate."
        except PublicWebsiteDesignRunnerError:
            initial_gate_ok = False
            initial_gate_error = (
                "Initial-gate evidence is missing, stale, or outside the staged candidate root."
            )
    checks.append(
        _check(
            "initial-gate-binding",
            initial_gate_ok,
            "Every post-gate state must retain hash-bound no-release initial browser evidence for the exact validated candidate.",
            error=initial_gate_error,
        )
    )

    visual_review_ok = state not in _VISUAL_REVIEW_STATES
    visual_review_error = ""
    if state in _VISUAL_REVIEW_STATES:
        try:
            if candidate_root is None or candidate_website is None or candidate_validation is None:
                raise PublicWebsiteDesignRunnerError(
                    "Candidate validation is unavailable for visual-review binding."
                )
            visual_review = _mapping(job.get("visual_review"), label="Visual-review binding")
            visual_review_path = _regular_file_under(
                root,
                visual_review.get("path"),
                label="Visual-review receipt",
                allowed_root=candidate_root,
            )
            visual_review_receipt = _read_json(visual_review_path, label="Visual-review receipt")
            expected_review_passed = state == "awaiting-owner-promotion"
            review_candidate = _mapping(
                visual_review_receipt.get("candidate"), label="Visual-review candidate"
            )
            visual_review_ok = (
                visual_review.get("sha256") == _sha256_file(visual_review_path)
                and visual_review.get("passed") is expected_review_passed
                and visual_review.get("state") == visual_review_receipt.get("state")
                and visual_review_receipt.get("schema") == VISUAL_REVIEW_SCHEMA
                and visual_review_receipt.get("passed") is expected_review_passed
                and visual_review_receipt.get("release_eligible") is False
                and visual_review_receipt.get("package_authority") == "none"
                and visual_review_receipt.get("deployment_authority") == "none"
                and _mapping(review_candidate.get("receipt"), label="Visual-review candidate receipt")
                == {
                    "path": candidate_validation.get("path"),
                    "sha256": candidate_validation.get("sha256"),
                }
                and review_candidate.get("root") == _relative_to_repo(root, candidate_root)
                and review_candidate.get("website_path") == _relative_to_repo(root, candidate_website)
            )
            if not visual_review_ok:
                visual_review_error = "Visual-review evidence no longer binds the validated staged candidate."
        except PublicWebsiteDesignRunnerError:
            visual_review_ok = False
            visual_review_error = (
                "Visual-review evidence is missing, stale, or outside the staged candidate root."
            )
    checks.append(
        _check(
            "visual-review-binding",
            visual_review_ok,
            "Every visual-review state must retain hash-bound no-release review evidence for the exact validated candidate.",
            error=visual_review_error,
        )
    )

    chain_ok = _validate_receipt_lineage(root, job)
    checks.append(
        _check(
            "immutable-receipt-chain",
            chain_ok,
            "Every advanced delivery state must retain one contiguous hash-bound predecessor chain in the same run directory.",
        )
    )

    passed = all(check["passed"] for check in checks)
    return {
        "schema": DELIVERY_VERIFICATION_SCHEMA,
        "verified_at": _utc_iso(now),
        "state": "pass" if passed else "blocked",
        "passed": passed,
        "compatibility": (
            "current-v2" if job.get("schema") == DELIVERY_JOB_SCHEMA else "historical-v1-read-only"
        ),
        "release_eligible": False,
        "package_authority": "none",
        "deployment_authority": "none",
        "checks": checks,
    }


def create_design_delivery_job(
    *,
    goal: str,
    route_id: str,
    reconciliation_receipt: Path,
    owner_source_decision: Path | None = None,
    backup_receipt: Path | None = None,
    design_cycle_receipt: Path | None = None,
    design_copy_task_id: str | None = None,
    run_id: str,
    repo_root: Path | None = None,
    now: datetime | None = None,
) -> tuple[dict[str, Any], Path]:
    """Create an immutable brief-bound work-order job without staging a candidate.

    Supplying both ``design_cycle_receipt`` and ``design_copy_task_id`` selects
    the stricter investor-copy path: the v4 work order is reduced to the
    audited route's one HTML document and a current source/policy/claim-bound
    copy contract is required before the initial job can be issued.
    """

    root = _find_repo_root(repo_root)
    resolved_run_id = _safe_run_id(run_id)
    copy_requested = design_cycle_receipt is not None or design_copy_task_id is not None
    if copy_requested and (
        design_cycle_receipt is None or not isinstance(design_copy_task_id, str) or not design_copy_task_id
    ):
        raise PublicWebsiteDesignRunnerError(
            "Investor-copy delivery requires both an exact design-cycle receipt and DESIGN-COPY task id."
        )
    planned_work_order_path = _work_order_path(root, resolved_run_id)
    if _delivery_directory(root, resolved_run_id).exists() or planned_work_order_path.exists():
        raise PublicWebsiteDesignRunnerError(
            "Delivery run id already has immutable evidence; use a new run id."
        )
    audit = audit_design_evidence_brief_file(repo_root=root, as_of=now)
    binding = _brief_binding(audit, route_id=route_id)
    route = _mapping(binding.get("route"), label="Audited route binding")
    allowed_paths = list(route["allowed_paths"])
    if copy_requested:
        local_path = route.get("local_path")
        if (
            not isinstance(local_path, str)
            or Path(local_path).suffix.casefold() not in {".html", ".htm"}
            or local_path not in allowed_paths
        ):
            raise PublicWebsiteDesignRunnerError(
                "Investor-copy delivery requires the audited route's exact declared HTML document."
            )
        allowed_paths = [local_path]
        assert design_cycle_receipt is not None
        assert design_copy_task_id is not None
        try:
            copy_preflight = preflight_investor_copy_repair_contract(
                design_cycle_receipt=design_cycle_receipt,
                task_id=design_copy_task_id,
                route_claim_capsule=_mapping(
                    route.get("claim_capsule"),
                    label="Audited route claim capsule",
                ),
                required_claim_ids=list(route["claim_ids"]),
                repo_root=root,
                as_of=now,
            )
        except InvestorCopyRepairError as exc:
            raise PublicWebsiteDesignRunnerError(
                f"Investor-copy repair preflight failed closed: {exc}"
            ) from exc
        preflight_route = _mapping(
            copy_preflight.get("route"),
            label="Investor-copy repair preflight route",
        )
        if copy_preflight.get("passed") is not True or preflight_route != {
            "route": route.get("route"),
            "path": local_path,
        }:
            raise PublicWebsiteDesignRunnerError(
                "Investor-copy repair preflight does not match the exact audited route and HTML path."
            )
    try:
        work_order = create_design_work_order(
            goal=goal,
            allowed_paths=allowed_paths,
            routes=[str(route["route"])],
            reconciliation_receipt=reconciliation_receipt,
            owner_source_decision=owner_source_decision,
            backup_receipt=backup_receipt,
            run_id=resolved_run_id,
            repo_root=root,
            now=now,
        )
    except DesignCandidateControlError as exc:
        raise PublicWebsiteDesignRunnerError(str(exc)) from exc
    if copy_requested:
        assert design_cycle_receipt is not None
        assert design_copy_task_id is not None
        try:
            preflight_investor_copy_repair_work_order(
                design_cycle_receipt=design_cycle_receipt,
                task_id=design_copy_task_id,
                work_order=work_order,
                planned_work_order_path=planned_work_order_path,
                route_claim_capsule=_mapping(
                    route.get("claim_capsule"),
                    label="Audited route claim capsule",
                ),
                required_claim_ids=list(route["claim_ids"]),
                repo_root=root,
                as_of=now,
            )
        except InvestorCopyRepairError as exc:
            raise PublicWebsiteDesignRunnerError(
                f"Investor-copy selected-source preflight failed closed: {exc}"
            ) from exc
    work_order_path = write_design_work_order(work_order, planned_work_order_path, repo_root=root)
    copy_reference: dict[str, Any] | None = None
    if copy_requested:
        assert design_cycle_receipt is not None
        assert design_copy_task_id is not None
        try:
            copy_contract = create_investor_copy_repair_contract(
                design_cycle_receipt=design_cycle_receipt,
                task_id=design_copy_task_id,
                work_order=work_order_path,
                route_claim_capsule=_mapping(
                    route.get("claim_capsule"),
                    label="Audited route claim capsule",
                ),
                required_claim_ids=list(route["claim_ids"]),
                repo_root=root,
                now=now,
            )
            copy_contract_path = write_investor_copy_repair_contract(
                copy_contract,
                repo_root=root,
            )
            copy_reference = _investor_copy_contract_reference(
                root=root,
                contract=copy_contract,
                contract_path=copy_contract_path,
            )
        except InvestorCopyRepairError as exc:
            raise PublicWebsiteDesignRunnerError(
                f"Investor-copy repair contract failed closed: {exc}"
            ) from exc
    asset_requirement = _asset_requirement(work_order)
    recorded_at = _utc_iso(now)
    job: dict[str, Any] = {
        "schema": DELIVERY_JOB_SCHEMA,
        "created_at": recorded_at,
        "updated_at": recorded_at,
        "run_id": resolved_run_id,
        "goal": str(goal).strip(),
        "state": "work-order-ready",
        "state_history": [
            {"state": "evidence-bound", "recorded_at": recorded_at, "actor": "PublicWebsiteDesignRunner"},
            {"state": "brief-ready", "recorded_at": recorded_at, "actor": "PublicWebsiteDesignRunner"},
            {"state": "reconciled", "recorded_at": recorded_at, "actor": "PublicWebsiteDesignRunner"},
            {"state": "work-order-ready", "recorded_at": recorded_at, "actor": "PublicWebsiteDesignRunner"},
        ],
        "brief_binding": binding,
        "work_order": {
            "path": _relative_to_repo(root, work_order_path),
            "sha256": _sha256_file(work_order_path),
            "run_id": resolved_run_id,
        },
        "asset_requirement": asset_requirement,
        "delivery_contract": {
            "kind": ("investor-copy-repair" if copy_reference is not None else "route-bounded-design"),
            "copy_repair_required": copy_reference is not None,
        },
        "authority": dict(AUTHORITY),
        "release_eligible": False,
        "package_authority": "none",
        "deployment_authority": "none",
        "next_required_stage": "stage the exact bounded candidate; no canonical website mutation is authorised",
    }
    if copy_reference is not None:
        job["investor_copy_repair"] = copy_reference
        job["next_required_stage"] = (
            "stage the exact one-HTML copy-repair candidate; no CSS, script, canonical, package, "
            "credential, or deployment authority is granted"
        )
    verification = verify_design_delivery_job(job, repo_root=root, now=now)
    if verification["passed"] is not True:
        failed = [item["id"] for item in verification["checks"] if item["passed"] is not True]
        raise PublicWebsiteDesignRunnerError("Cannot issue an invalid delivery job: " + "; ".join(failed))
    return job, _write_next_job(root, job)


def stage_design_delivery_job(
    run_id: str, *, repo_root: Path | None = None, now: datetime | None = None
) -> tuple[dict[str, Any], Path]:
    """Stage a candidate from a valid delivery job, never from canonical mutation."""

    root = _find_repo_root(repo_root)
    job, previous_path = load_latest_delivery_job(run_id, repo_root=root)
    _require_advancing_v2(job, operation="Candidate staging")
    if job.get("state") != "work-order-ready":
        raise PublicWebsiteDesignRunnerError("Only a work-order-ready job may stage a candidate.")
    verification = verify_design_delivery_job(job, repo_root=root, now=now)
    if verification["passed"] is not True:
        raise PublicWebsiteDesignRunnerError(
            "Delivery job no longer verifies; issue a fresh job before staging."
        )
    try:
        staged = stage_design_candidate(Path(str(job["work_order"]["path"])), repo_root=root)
    except (DesignCandidateControlError, KeyError, TypeError) as exc:
        raise PublicWebsiteDesignRunnerError(str(exc)) from exc
    next_job = _copy_for_next_state(
        job,
        previous_path=previous_path,
        root=root,
        state="candidate-staged",
        now=now,
        next_required_stage=(
            "run the trusted editorial asset importer and adopt its current "
            "receipt before exposing any worker context"
            if _mapping(
                job.get("asset_requirement"),
                label="Delivery job asset requirement",
            ).get("required")
            is True
            else "give the worker only the staged text workspace context, then validate one bounded diff"
        ),
    )
    next_job["candidate"] = staged
    return next_job, _write_next_job(root, next_job)


def prepare_design_delivery_assets(
    run_id: str,
    *,
    repo_root: Path | None = None,
    now: datetime | None = None,
) -> tuple[dict[str, Any], Path]:
    """Import or adopt one complete trusted WebP batch before text-worker access."""

    root = _find_repo_root(repo_root)
    job, previous_path = load_latest_delivery_job(run_id, repo_root=root)
    _require_advancing_v2(job, operation="Candidate asset preparation")
    if job.get("state") != "candidate-staged":
        raise PublicWebsiteDesignRunnerError(
            "Only a newly staged binary-bearing candidate may enter asset preparation."
        )
    verification = verify_design_delivery_job(job, repo_root=root, now=now)
    if verification["passed"] is not True:
        raise PublicWebsiteDesignRunnerError("Delivery job no longer verifies; asset import is withheld.")
    requirement = _mapping(
        job.get("asset_requirement"),
        label="Delivery job asset requirement",
    )
    if requirement.get("required") is not True:
        raise PublicWebsiteDesignRunnerError("Text-only candidates do not enter candidate-assets-ready.")
    work_order_ref = _mapping(
        job.get("work_order"),
        label="Delivery job work order",
    )
    work_order_path = _regular_file_under(
        root,
        work_order_ref.get("path"),
        label="Delivery job work order",
        allowed_root=(root / DEFAULT_WORK_ORDER_ROOT).resolve(),
    )
    order = _read_json(
        work_order_path,
        label="Delivery job work order",
    )
    control = _mapping(
        order.get("editorial_asset_control"),
        label="Work-order editorial asset control",
    )
    receipt_path = root / str(control.get("receipt_path") or "")
    if receipt_path.name != EDITORIAL_IMPORT_RECEIPT_NAME:
        raise PublicWebsiteDesignRunnerError(
            "V4 work order lost its fixed candidate-local editorial receipt path."
        )
    try:
        if receipt_path.exists() or receipt_path.is_symlink():
            receipt = _read_json(
                receipt_path,
                label="Existing editorial asset import receipt",
            )
        else:
            receipt = import_editorial_assets_to_candidate(
                work_order_path,
                repo_root=root,
                as_of=now,
                now=now,
            )
        binding = _asset_import_binding(
            root=root,
            order=order,
            receipt=receipt,
            now=now,
        )
    except (
        DesignEditorialAssetCandidateImporterError,
        PublicWebsiteDesignRunnerError,
        OSError,
        TypeError,
        ValueError,
    ) as exc:
        raise PublicWebsiteDesignRunnerError(f"Candidate asset preparation failed closed: {exc}") from exc
    next_job = _copy_for_next_state(
        job,
        previous_path=previous_path,
        root=root,
        state="candidate-assets-ready",
        now=now,
        next_required_stage=(
            "give the worker only the sealed text-mutation context, then replay "
            "the trusted binary receipt during candidate validation"
        ),
    )
    next_job["asset_import"] = binding
    return next_job, _write_next_job(root, next_job)


def worker_context_for_delivery_job(
    run_id: str, *, repo_root: Path | None = None, now: datetime | None = None
) -> dict[str, Any]:
    """Return the worker's least-privilege staged-only context for one job."""

    root = _find_repo_root(repo_root)
    job, _ = load_latest_delivery_job(run_id, repo_root=root)
    _require_advancing_v2(job, operation="Worker-context issuance")
    requirement = _mapping(
        job.get("asset_requirement"),
        label="Delivery job asset requirement",
    )
    expected_state = "candidate-assets-ready" if requirement.get("required") is True else "candidate-staged"
    if job.get("state") != expected_state:
        raise PublicWebsiteDesignRunnerError(
            "Worker context is withheld until text-only staging or the runner's "
            "trusted candidate-assets-ready transition is current."
        )
    verification = verify_design_delivery_job(job, repo_root=root, now=now)
    if verification["passed"] is not True:
        raise PublicWebsiteDesignRunnerError("Delivery job no longer verifies; worker context is withheld.")
    candidate = _mapping(job.get("candidate"), label="Staged candidate")
    binding = _mapping(job.get("brief_binding"), label="Brief binding")
    route = _mapping(binding.get("route"), label="Route binding")
    feedback_context = _stakeholder_feedback_context(job)
    work_order_ref = _mapping(
        job.get("work_order"),
        label="Delivery job work order",
    )
    work_order_path = _regular_file_under(
        root,
        work_order_ref.get("path"),
        label="Delivery job work order",
        allowed_root=(root / DEFAULT_WORK_ORDER_ROOT).resolve(),
    )
    order = _read_json(
        work_order_path,
        label="Delivery job work order",
    )
    mutation_contract = _text_mutation_contract(order)
    investor_copy_context: dict[str, Any] | None = None
    if _delivery_contract_is_copy(job):
        try:
            loaded_copy = _load_investor_copy_contract(
                root=root,
                job=job,
                route=route,
                work_order_ref=work_order_ref,
                now=now,
            )
            if loaded_copy is None:
                raise PublicWebsiteDesignRunnerError(
                    "Investor-copy contract disappeared before worker context projection."
                )
            investor_copy_contract, _ = loaded_copy
            investor_copy_context = _investor_copy_worker_context(
                reference=_mapping(
                    job.get("investor_copy_repair"),
                    label="Investor-copy repair binding",
                ),
                contract=investor_copy_contract,
            )
        except InvestorCopyRepairError as exc:
            raise PublicWebsiteDesignRunnerError(str(exc)) from exc
    if requirement.get("required") is True:
        asset_import_context = dict(
            _mapping(
                job.get("asset_import"),
                label="Delivery job asset import",
            )
        )
    else:
        asset_import_context = {
            "required": False,
            "state": "not-required-text-only",
            "assets_ready": False,
            "release_eligible": False,
            "package_authority": "none",
            "deployment_authority": "none",
        }
    website_value = candidate.get("candidate_website")
    if not isinstance(website_value, str):
        raise PublicWebsiteDesignRunnerError("Staged candidate workspace is unavailable.")
    raw_website_path = root / website_value
    raw_candidate_root = root / str(candidate.get("candidate_root") or "")
    _reject_link_ancestors(root, raw_website_path, label="Staged candidate website")
    _reject_link_ancestors(root, raw_candidate_root, label="Staged candidate root")
    website_path = raw_website_path.resolve()
    candidate_root = raw_candidate_root.resolve()
    try:
        website_path.relative_to(candidate_root)
        candidate_root.relative_to((root / DEFAULT_CANDIDATE_ROOT).resolve())
    except ValueError as exc:
        raise PublicWebsiteDesignRunnerError(
            "Staged candidate workspace escapes its approved artifact root."
        ) from exc
    if not website_path.is_dir() or website_path.is_symlink():
        raise PublicWebsiteDesignRunnerError("Staged candidate website must be a regular directory.")
    context: dict[str, Any] = {
        "schema": "aureon.public-website-design-worker-context.v1",
        "run_id": job["run_id"],
        "workspace": {"candidate_website": website_value},
        "work_order": dict(job["work_order"]),
        "asset_requirement": dict(requirement),
        "asset_import": asset_import_context,
        "mutation_contract": mutation_contract,
        "route": {
            "id": route["id"],
            "route": route["route"],
            "allowed_paths": list(mutation_contract["text_write_paths"]),
            "claim_capsule": route["claim_capsule"],
            "claim_capsule_sha256": route["claim_capsule_sha256"],
            "feedback_capsule": feedback_context["feedback_capsule"],
            "feedback_capsule_sha256": feedback_context["feedback_capsule_sha256"],
        },
        "authority": dict(AUTHORITY),
        "release_eligible": False,
        "deployment_authority": "none",
        "prohibited_operations": [
            "canonical website mutation",
            "candidate promotion",
            "package creation",
            "backup",
            "owner gate",
            "deployment",
            "credential access",
            "binary asset read",
            "binary asset write",
            "binary asset import",
        ],
    }
    if investor_copy_context is not None:
        context["investor_copy_repair"] = investor_copy_context
    return context


def validate_design_delivery_job(
    run_id: str,
    *,
    claim_impacts: Sequence[Mapping[str, Any]],
    claim_surface_manifest: Sequence[Mapping[str, Any]] = (),
    repo_root: Path | None = None,
    now: datetime | None = None,
) -> tuple[dict[str, Any], Path]:
    """Validate one staged candidate once; failures require a successor run."""

    root = _find_repo_root(repo_root)
    job, previous_path = load_latest_delivery_job(run_id, repo_root=root)
    _require_advancing_v2(job, operation="Candidate validation")
    requirement = _mapping(
        job.get("asset_requirement"),
        label="Delivery job asset requirement",
    )
    expected_state = "candidate-assets-ready" if requirement.get("required") is True else "candidate-staged"
    if job.get("state") != expected_state:
        raise PublicWebsiteDesignRunnerError(
            "Candidate validation requires an untouched staged candidate: "
            "text-only staging or a current runner-produced "
            "candidate-assets-ready binding."
        )
    verification = verify_design_delivery_job(job, repo_root=root, now=now)
    if verification["passed"] is not True:
        raise PublicWebsiteDesignRunnerError(
            "Delivery job no longer verifies; candidate validation is withheld."
        )
    try:
        claim_surface_context = _claim_surface_context(job)
        candidate_receipt = validate_design_candidate(
            Path(str(job["work_order"]["path"])),
            claim_impacts=claim_impacts,
            claim_surface_context=claim_surface_context,
            claim_surface_manifest=claim_surface_manifest,
            repo_root=root,
            now=now,
        )
        candidate_root = (root / str(candidate_receipt["candidate"]["root"])).resolve()
    except (DesignCandidateControlError, KeyError, TypeError) as exc:
        raise PublicWebsiteDesignRunnerError(str(exc)) from exc
    control_passed = candidate_receipt.get("passed") is True
    copy_evaluation_record: dict[str, Any] | None = None
    copy_passed = True
    if _delivery_contract_is_copy(job):
        try:
            route_binding = _mapping(
                _mapping(
                    job.get("brief_binding"),
                    label="Delivery job brief binding",
                ).get("route"),
                label="Delivery job route binding",
            )
            work_order_ref = _mapping(
                job.get("work_order"),
                label="Delivery job work order",
            )
            loaded_copy = _load_investor_copy_contract(
                root=root,
                job=job,
                route=route_binding,
                work_order_ref=work_order_ref,
                now=now,
            )
            if loaded_copy is None:
                raise PublicWebsiteDesignRunnerError(
                    "Investor-copy contract disappeared during candidate validation."
                )
            investor_copy_contract, _ = loaded_copy
            candidate_website = (root / str(candidate_receipt["candidate"]["website_path"])).resolve()
            copy_evaluation = evaluate_investor_copy_repair_candidate(
                investor_copy_contract,
                candidate_website_root=candidate_website,
                route_claim_capsule=_mapping(
                    route_binding.get("claim_capsule"),
                    label="Delivery job route claim capsule",
                ),
                repo_root=root,
                as_of=now,
            )
            if copy_evaluation.get("schema") != INVESTOR_COPY_REPAIR_EVALUATION_SCHEMA or not isinstance(
                copy_evaluation.get("passed"), bool
            ):
                raise PublicWebsiteDesignRunnerError("Investor-copy evaluator returned a malformed result.")
            copy_evaluation_record = dict(copy_evaluation)
            copy_passed = copy_evaluation.get("passed") is True
        except (
            InvestorCopyRepairError,
            PublicWebsiteDesignRunnerError,
            OSError,
            KeyError,
            TypeError,
            ValueError,
        ) as exc:
            raise PublicWebsiteDesignRunnerError(
                f"Investor-copy candidate evaluation failed closed: {exc}"
            ) from exc
    try:
        candidate_path = write_design_candidate_receipt(
            candidate_receipt,
            candidate_root / "candidate.v1.json",
            repo_root=root,
        )
    except DesignCandidateControlError as exc:
        raise PublicWebsiteDesignRunnerError(str(exc)) from exc
    passed = control_passed and copy_passed
    state = "candidate-validated" if passed else "candidate-repair-required"
    next_stage = (
        "evaluate one focused initial browser gate against the unchanged validated candidate"
        if passed
        else "preserve this failed candidate and issue a fresh exact-path successor work order; do not overwrite it"
    )
    next_job = _copy_for_next_state(
        job,
        previous_path=previous_path,
        root=root,
        state=state,
        now=now,
        next_required_stage=next_stage,
    )
    next_job["candidate_validation"] = {
        "path": _relative_to_repo(root, candidate_path),
        "sha256": _sha256_file(candidate_path),
        "control_passed": control_passed,
        "passed": passed,
    }
    if copy_evaluation_record is not None:
        next_job["investor_copy_evaluation"] = copy_evaluation_record
    return next_job, _write_next_job(root, next_job)


def evaluate_delivery_candidate_qa(
    run_id: str,
    *,
    motion_config: Path,
    expected_motion_config_sha256: str,
    test_policy: Path,
    expected_test_policy_sha256: str,
    repo_root: Path | None = None,
    now: datetime | None = None,
) -> tuple[dict[str, Any], Path]:
    """Consume one trusted motion-first QA attempt for one validated candidate.

    The runner accepts only the exact fixed compiler output and externally
    pinned configuration bytes. It does not compile policies, select commands,
    accept worker results, relax thresholds or retry. An immutable claim is
    written before either QA engine executes, so a crash or rejection still
    consumes this run's sole attempt.
    """

    root = _find_repo_root(repo_root)
    job, previous_path = load_latest_delivery_job(run_id, repo_root=root)
    _require_advancing_v2(job, operation="Candidate QA")
    if job.get("state") != "candidate-validated":
        raise PublicWebsiteDesignRunnerError(
            "Candidate QA is a one-attempt transition from candidate-validated only."
        )
    verification = verify_design_delivery_job(job, repo_root=root, now=now)
    if verification["passed"] is not True:
        raise PublicWebsiteDesignRunnerError("Delivery job no longer verifies; candidate QA is withheld.")

    trusted_toolchain = _trusted_qa_toolchain_binding(root)
    motion_path, motion_config_binding = _pinned_file_binding(
        root,
        motion_config,
        expected_motion_config_sha256,
        label="Candidate QA motion configuration",
    )
    policy_path, test_policy_binding = _pinned_file_binding(
        root,
        test_policy,
        expected_test_policy_sha256,
        label="Candidate QA test policy",
    )

    staged = _mapping(job.get("candidate"), label="Staged candidate")
    candidate_root = _regular_directory_under(
        root,
        staged.get("candidate_root"),
        label="Staged candidate root",
        allowed_root=_artifact_root(
            root,
            DEFAULT_CANDIDATE_ROOT,
            label="Candidate artifact root",
        ),
    )
    candidate_website = _regular_directory_under(
        root,
        staged.get("candidate_website"),
        label="Staged candidate website",
        allowed_root=candidate_root,
    )
    for pinned_path, label in (
        (motion_path, "motion configuration"),
        (policy_path, "test policy"),
    ):
        try:
            pinned_path.relative_to(candidate_website)
        except ValueError:
            pass
        else:
            raise PublicWebsiteDesignRunnerError(
                f"Candidate QA {label} must stay outside the hash-bound candidate website tree."
            )
    candidate_validation = _mapping(
        job.get("candidate_validation"),
        label="Candidate validation binding",
    )
    candidate_receipt_path = _regular_file_under(
        root,
        candidate_validation.get("path"),
        label="Candidate validation receipt",
        allowed_root=candidate_root,
    )
    candidate_receipt = _read_json(
        candidate_receipt_path,
        label="Candidate validation receipt",
    )
    candidate_receipt_binding = _mapping(
        candidate_receipt.get("candidate"),
        label="Candidate validation receipt candidate",
    )
    candidate_snapshot = _candidate_qa_tree_binding(
        root,
        candidate_website,
        label="Candidate QA staged tree",
    )
    if (
        candidate_validation.get("passed") is not True
        or candidate_validation.get("sha256") != _sha256_file(candidate_receipt_path)
        or candidate_receipt_binding.get("root") != _relative_to_repo(root, candidate_root)
        or candidate_receipt_binding.get("website_path") != _relative_to_repo(root, candidate_website)
        or candidate_receipt_binding.get("tree_sha256") != candidate_snapshot.get("candidate_tree_sha256")
        or candidate_receipt_binding.get("file_count") != candidate_snapshot.get("file_count")
        or candidate_receipt_binding.get("total_bytes") != candidate_snapshot.get("total_bytes")
        or verify_staged_candidate_receipt(
            candidate_receipt,
            repo_root=root,
        ).get("passed")
        is not True
    ):
        raise PublicWebsiteDesignRunnerError(
            "Candidate QA requires the exact unchanged passed candidate validation receipt."
        )
    canonical_snapshot = _static_tree_binding(
        root,
        root / "website",
        expected_kind="canonical-static-tree",
        label="Candidate QA canonical website",
    )
    candidate_binding = {
        "root": _relative_to_repo(root, candidate_root),
        "website_path": _relative_to_repo(root, candidate_website),
        "validation_tree_sha256": candidate_snapshot["candidate_tree_sha256"],
        "candidate_tree_algorithm": candidate_snapshot["candidate_tree_algorithm"],
        "motion_tree_sha256": candidate_snapshot["motion_tree_sha256"],
        "motion_tree_algorithm": candidate_snapshot["motion_tree_algorithm"],
        "captured_manifest_sha256": candidate_snapshot["captured_manifest_sha256"],
        "validation_receipt": {
            "path": candidate_validation["path"],
            "sha256": candidate_validation["sha256"],
        },
    }
    try:
        motion_compiler_verification = _verify_compiled_candidate_motion_config_file_sealed(
            motion_path,
            expected_config_sha256=motion_config_binding["sha256"],
            candidate_receipt_path=candidate_receipt_path,
            repo_root=root,
        )
    except PublicWebsiteDesignRunnerError as exc:
        raise PublicWebsiteDesignRunnerError(
            f"Candidate QA rejected a non-fixed or stale compiled motion configuration: {exc}"
        ) from exc
    if not _motion_compiler_verification_matches(
        motion_compiler_verification,
        candidate_receipt_path=candidate_validation.get("path"),
        candidate_tree_sha256=candidate_binding["validation_tree_sha256"],
        candidate_tree_algorithm=candidate_binding["candidate_tree_algorithm"],
        motion_tree_sha256=candidate_binding["motion_tree_sha256"],
        motion_tree_algorithm=candidate_binding["motion_tree_algorithm"],
        captured_manifest_sha256=candidate_binding["captured_manifest_sha256"],
        config_path=motion_config_binding["path"],
        config_file_sha256=motion_config_binding["sha256"],
    ):
        raise PublicWebsiteDesignRunnerError(
            "Candidate QA motion configuration does not equal the complete fixed compiler result."
        )
    try:
        test_compiler_verification = _verify_compiled_candidate_test_policy_file_sealed(
            policy_path,
            expected_policy_sha256=test_policy_binding["sha256"],
            candidate_receipt_path=candidate_receipt_path,
            repo_root=root,
        )
    except PublicWebsiteDesignRunnerError as exc:
        raise PublicWebsiteDesignRunnerError(
            f"Candidate QA rejected a non-fixed or stale compiled test policy: {exc}"
        ) from exc
    policy = _read_json(policy_path, label="Candidate QA test policy")
    command_ids = policy.get("required_command_ids")
    policy_content_core_sha256 = policy.get("content_core_sha256")
    if not _test_compiler_verification_matches(
        test_compiler_verification,
        candidate_receipt_path=candidate_validation.get("path"),
        candidate_tree_sha256=candidate_binding["validation_tree_sha256"],
        policy_path=test_policy_binding["path"],
        policy_content_core_sha256=policy_content_core_sha256,
        policy_file_sha256=test_policy_binding["sha256"],
        required_command_ids=command_ids,
    ):
        raise PublicWebsiteDesignRunnerError(
            "Candidate QA test policy does not equal the complete fixed compiler result."
        )
    command_ids = cast(list[str], command_ids)
    if _trusted_qa_toolchain_binding(root) != trusted_toolchain:
        raise PublicWebsiteDesignRunnerError(
            "Trusted QA source files changed before the attempt could be claimed."
        )

    motion_receipt_path = (
        root
        / "artifacts"
        / "website-operator"
        / "motion-performance-budget"
        / f"{_safe_run_id(run_id)}-candidate-qa.v2.json"
    )
    test_receipt_path = candidate_root / "candidate-qa" / "candidate-test-evidence.v2.json"
    claim_path = _qa_claim_path(candidate_root)
    for output, label in (
        (motion_receipt_path, "motion receipt"),
        (test_receipt_path, "test receipt"),
        (claim_path, "attempt claim"),
    ):
        _reject_link_ancestors(root, output, label=f"Candidate QA {label}")
        if output.exists() or output.is_symlink():
            raise PublicWebsiteDesignRunnerError(
                f"Candidate QA {label} already exists; thresholds, policies and attempts cannot be retried."
            )

    claim: dict[str, Any] = {
        "schema": CANDIDATE_QA_CLAIM_SCHEMA,
        "state": "qa-execution-claimed",
        "claimed_at": _utc_iso(now),
        "run_id": _safe_run_id(run_id),
        "delivery_receipt": {
            "path": _relative_to_repo(root, previous_path),
            "sha256": _sha256_file(previous_path),
        },
        "candidate": candidate_binding,
        "canonical_website": canonical_snapshot,
        "trusted_toolchain": trusted_toolchain,
        "motion_config": motion_config_binding,
        "motion_config_compiler": motion_compiler_verification,
        "test_policy": test_policy_binding,
        "test_policy_compiler": test_compiler_verification,
        "authority": dict(_CANDIDATE_QA_AUTHORITY),
        "release_eligible": False,
        "package_authority": "none",
        "deployment_authority": "none",
    }
    claim["claim_payload_sha256"] = _json_sha256(claim)
    _atomic_write_json(claim_path, claim)
    claim_binding = {
        "path": _relative_to_repo(root, claim_path),
        "sha256": _sha256_file(claim_path),
        "claim_payload_sha256": claim["claim_payload_sha256"],
    }

    try:
        motion_result = audit_motion_performance_budget(
            motion_path,
            repo_root=root,
            output_path=motion_receipt_path,
        )
        motion_disk = _read_json(
            motion_receipt_path,
            label="Candidate QA motion receipt",
        )
        motion_replay = validate_motion_performance_receipt(
            motion_receipt_path,
            repo_root=root,
        )
    except (DesignMotionPerformanceBudgetError, OSError) as exc:
        raise PublicWebsiteDesignRunnerError(
            f"The consumed candidate QA motion attempt failed closed: {type(exc).__name__}: {exc}"
        ) from exc
    if motion_result != motion_disk or motion_disk != motion_replay:
        raise PublicWebsiteDesignRunnerError(
            "The consumed candidate QA motion receipt failed exact write/read/replay."
        )
    motion_decision = _mapping(
        motion_replay.get("decision"),
        label="Candidate QA motion decision",
    )
    motion_source = _mapping(
        motion_replay.get("source"),
        label="Candidate QA motion source",
    )
    motion_receipt_config = _mapping(
        motion_replay.get("config"),
        label="Candidate QA motion receipt configuration",
    )
    motion_passed = (
        motion_decision.get("status") == "pass"
        and motion_decision.get("eligible_for_next_local_gate") is True
    )
    if (
        motion_receipt_config.get("path") != motion_config_binding["path"]
        or motion_receipt_config.get("sha256") != motion_config_binding["sha256"]
        or motion_source.get("kind") != "staged-static-tree"
        or motion_source.get("root") != candidate_binding["website_path"]
        or motion_source.get("observed_tree_sha256") != candidate_binding["motion_tree_sha256"]
    ):
        raise PublicWebsiteDesignRunnerError(
            "The consumed motion receipt is stale, substituted, or belongs to another candidate."
        )
    motion_binding = {
        "config": motion_config_binding,
        "state": "passed" if motion_passed else "blocked",
        "receipt": {
            "path": _relative_to_repo(root, motion_receipt_path),
            "sha256": _sha256_file(motion_receipt_path),
            "receipt_sha256": motion_replay.get("receipt_sha256"),
        },
        "eligible_for_next_local_gate": motion_passed,
        "replayed": True,
    }

    test_binding: dict[str, Any]
    evidence_passed = False
    if not motion_passed:
        test_binding = {
            "policy": test_policy_binding,
            "state": "not-run-motion-blocked",
            "receipt": None,
            "evidence_passed": False,
            "ordered_command_ids_sha256": _json_sha256(command_ids),
            "command_count": len(command_ids),
            "trusted_same_process_execution_write": False,
            "structural_verification_origin_attested": False,
            "replayed": False,
            "candidate_tree_sha256": None,
            "canonical_website_tree_sha256": None,
        }
    else:
        receipt_id = "qa-" + hashlib.sha256(_safe_run_id(run_id).encode("utf-8")).hexdigest()[:24]
        try:
            test_result = execute_candidate_test_evidence(
                policy_path,
                expected_policy_sha256=test_policy_binding["sha256"],
                command_ids=command_ids,
                repo_root=root,
                receipt_id=receipt_id,
                now=now,
            )
            if test_result.get("schema") != _test_evidence_module.RECEIPT_SCHEMA:
                raise PublicWebsiteDesignRunnerError(
                    "Candidate QA execution returned an obsolete or substituted evidence schema."
                )
            write_candidate_test_evidence_receipt(
                test_result,
                test_receipt_path,
                policy_path=policy_path,
                expected_policy_sha256=test_policy_binding["sha256"],
                repo_root=root,
            )
            test_disk = _read_json(
                test_receipt_path,
                label="Candidate QA test receipt",
            )
            if test_disk != test_result:
                raise PublicWebsiteDesignRunnerError(
                    "Candidate QA test receipt changed during immutable write/read."
                )
            test_receipt_sha256 = _sha256_file(test_receipt_path)
            test_replay = verify_candidate_test_evidence_receipt(
                test_receipt_path,
                expected_receipt_file_sha256=test_receipt_sha256,
                policy_path=policy_path,
                expected_policy_sha256=test_policy_binding["sha256"],
                repo_root=root,
            )
        except (
            DesignCandidateTestEvidenceError,
            OSError,
            PublicWebsiteDesignRunnerError,
        ) as exc:
            raise PublicWebsiteDesignRunnerError(
                f"The consumed candidate QA test attempt failed closed: {type(exc).__name__}: {exc}"
            ) from exc
        evidence_passed = test_replay.get("evidence_passed") is True
        if (
            test_replay.get("schema") != _test_evidence_module.VERIFICATION_SCHEMA
            or test_disk.get("schema") != _test_evidence_module.RECEIPT_SCHEMA
            or test_replay.get("origin_attested") is not False
            or test_replay.get("policy_file_sha256") != test_policy_binding["sha256"]
            or test_replay.get("candidate_tree_sha256") != candidate_binding["validation_tree_sha256"]
            or test_replay.get("receipt_payload_sha256") != test_result.get("receipt_payload_sha256")
        ):
            raise PublicWebsiteDesignRunnerError(
                "The consumed test evidence is stale, cross-run, or lacks the trusted runner seal."
            )
        test_binding = {
            "policy": test_policy_binding,
            "state": "passed" if evidence_passed else "failed",
            "receipt": {
                "path": _relative_to_repo(root, test_receipt_path),
                "sha256": test_receipt_sha256,
                "receipt_payload_sha256": test_replay["receipt_payload_sha256"],
            },
            "evidence_passed": evidence_passed,
            "ordered_command_ids_sha256": _json_sha256(command_ids),
            "command_count": len(command_ids),
            "trusted_same_process_execution_write": True,
            "structural_verification_origin_attested": False,
            "replayed": True,
            "candidate_tree_sha256": test_replay["candidate_tree_sha256"],
            "canonical_website_tree_sha256": test_replay["canonical_website_tree_sha256"],
        }

    if (
        _candidate_qa_tree_binding(
            root,
            candidate_website,
            label="Post-QA staged tree",
        )
        != candidate_snapshot
        or _static_tree_binding(
            root,
            root / "website",
            expected_kind="canonical-static-tree",
            label="Post-QA canonical website",
        )
        != canonical_snapshot
        or _trusted_qa_toolchain_binding(root) != trusted_toolchain
    ):
        raise PublicWebsiteDesignRunnerError(
            "Candidate, canonical website, or trusted QA source bytes changed during the consumed QA attempt."
        )

    qa_passed = motion_passed and evidence_passed
    qa_binding = {
        "schema": CANDIDATE_QA_SCHEMA,
        "status": "verified" if qa_passed else "repair-required",
        "attempt_consumed": True,
        "attempt": claim_binding,
        "candidate": candidate_binding,
        "canonical_website": canonical_snapshot,
        "trusted_toolchain": trusted_toolchain,
        "motion_config_compiler": motion_compiler_verification,
        "test_policy_compiler": test_compiler_verification,
        "motion": motion_binding,
        "tests": test_binding,
        "authority": dict(_CANDIDATE_QA_AUTHORITY),
        "release_eligible": False,
        "package_authority": "none",
        "deployment_authority": "none",
    }
    next_job = _copy_for_next_state(
        job,
        previous_path=previous_path,
        root=root,
        state=("candidate-qa-verified" if qa_passed else "candidate-qa-repair-required"),
        now=now,
        next_required_stage=(
            "evaluate one focused initial browser gate against the unchanged QA-verified candidate"
            if qa_passed
            else "preserve the consumed QA failure and issue a separately authorised successor run; do not retry or relax thresholds"
        ),
    )
    next_job["candidate_qa"] = qa_binding
    return next_job, _write_next_job(root, next_job)


def evaluate_delivery_initial_gate(
    run_id: str,
    *,
    visual_receipt: Path,
    route_name: str,
    engine_name: str = "chromium",
    repo_root: Path | None = None,
    now: datetime | None = None,
) -> tuple[dict[str, Any], Path]:
    """Bind one focused staged browser gate; a rejection cannot be retried in this run."""

    root = _find_repo_root(repo_root)
    job, previous_path = load_latest_delivery_job(run_id, repo_root=root)
    _require_advancing_v2(job, operation="Initial browser gate")
    if job.get("state") != "candidate-qa-verified":
        raise PublicWebsiteDesignRunnerError(
            "Only a candidate-qa-verified validated staged candidate may enter an initial browser gate."
        )
    verification = verify_design_delivery_job(job, repo_root=root, now=now)
    if verification["passed"] is not True:
        raise PublicWebsiteDesignRunnerError("Delivery job no longer verifies; browser gate is withheld.")
    candidate_validation = _mapping(job.get("candidate_validation"), label="Candidate validation binding")
    try:
        gate = evaluate_initial_candidate_gate(
            Path(str(candidate_validation.get("path") or "")),
            visual_receipt,
            route_name=route_name,
            engine_name=engine_name,
            repo_root=root,
            now=now,
        )
        candidate_root = (root / str(gate["candidate"]["root"])).resolve()
        gate_path = write_initial_candidate_gate(
            gate, candidate_root / "initial-gate.v1.json", repo_root=root
        )
    except (DesignCandidateInitialGateError, DesignCandidateControlError, KeyError, TypeError) as exc:
        raise PublicWebsiteDesignRunnerError(str(exc)) from exc
    passed = gate.get("passed") is True
    state = "awaiting-browser-evidence" if passed else "initial-gate-rejected"
    next_stage = (
        "bind the complete staged browser capture, named manual review and separate named visual acceptance"
        if passed
        else "preserve the rejected initial gate and issue a separately authorised successor; do not retry-seek a pass"
    )
    next_job = _copy_for_next_state(
        job,
        previous_path=previous_path,
        root=root,
        state=state,
        now=now,
        next_required_stage=next_stage,
    )
    next_job["initial_gate"] = {
        "path": _relative_to_repo(root, gate_path),
        "sha256": _sha256_file(gate_path),
        "passed": passed,
        "state": gate.get("state"),
    }
    return next_job, _write_next_job(root, next_job)


def record_delivery_visual_review(
    run_id: str,
    *,
    capture_receipt: Path,
    manual_review: Path,
    human_acceptance: Path,
    repo_root: Path | None = None,
    now: datetime | None = None,
) -> tuple[dict[str, Any], Path]:
    """Record existing staged visual evidence; it remains pre-owner evidence only."""

    root = _find_repo_root(repo_root)
    job, previous_path = load_latest_delivery_job(run_id, repo_root=root)
    _require_advancing_v2(job, operation="Visual-review recording")
    if job.get("state") != "awaiting-browser-evidence":
        raise PublicWebsiteDesignRunnerError("Complete visual review follows only a passing initial gate.")
    verification = verify_design_delivery_job(job, repo_root=root, now=now)
    if verification["passed"] is not True:
        raise PublicWebsiteDesignRunnerError("Delivery job no longer verifies; visual review is withheld.")
    candidate_validation = _mapping(job.get("candidate_validation"), label="Candidate validation binding")
    try:
        review = validate_candidate_visual_review(
            Path(str(candidate_validation.get("path") or "")),
            capture_receipt,
            manual_review,
            human_acceptance,
            repo_root=root,
            now=now,
        )
        candidate_root = (root / str(review["candidate"]["root"])).resolve()
        review_path = write_candidate_visual_review(
            review,
            candidate_root / "visual-review" / "prepromotion-review.v1.json",
            repo_root=root,
        )
    except (DesignCandidateVisualReviewError, DesignCandidateControlError, KeyError, TypeError) as exc:
        raise PublicWebsiteDesignRunnerError(str(exc)) from exc
    passed = review.get("passed") is True
    state = "awaiting-owner-promotion" if passed else "visual-review-repair-required"
    next_stage = (
        "await an owner-controlled canonical promotion proof; this runner cannot promote, package or deploy"
        if passed
        else "preserve the failed review and issue a separately scoped successor candidate if repair is authorised"
    )
    next_job = _copy_for_next_state(
        job,
        previous_path=previous_path,
        root=root,
        state=state,
        now=now,
        next_required_stage=next_stage,
    )
    next_job["visual_review"] = {
        "path": _relative_to_repo(root, review_path),
        "sha256": _sha256_file(review_path),
        "passed": passed,
        "state": review.get("state"),
    }
    return next_job, _write_next_job(root, next_job)


def _load_claim_impacts(path: Path, root: Path) -> list[Mapping[str, Any]]:
    candidate = path if path.is_absolute() else root / path
    candidate = candidate.resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise PublicWebsiteDesignRunnerError("Claim-impact input must stay inside the repository.") from exc
    raw = _read_json(candidate, label="Claim-impact input")
    declarations = raw.get("claim_impacts")
    if not isinstance(declarations, list) or not all(isinstance(item, Mapping) for item in declarations):
        raise PublicWebsiteDesignRunnerError("Claim-impact input must contain a claim_impacts object list.")
    return [dict(item) for item in declarations]


def _load_claim_surface_manifest(path: Path, root: Path) -> list[Mapping[str, Any]]:
    candidate = path if path.is_absolute() else root / path
    candidate = candidate.resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise PublicWebsiteDesignRunnerError("Claim-surface input must stay inside the repository.") from exc
    raw = _read_json(candidate, label="Claim-surface input")
    manifest = raw.get("claim_surface_manifest")
    if not isinstance(manifest, list) or not all(isinstance(item, Mapping) for item in manifest):
        raise PublicWebsiteDesignRunnerError(
            "Claim-surface input must contain a claim_surface_manifest object list."
        )
    return [dict(item) for item in manifest]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aureon-public-website-design-runner",
        description="Run source-bound, staged-only Aureon website design delivery states.",
    )
    parser.add_argument("--repo-root", type=Path)
    subparsers = parser.add_subparsers(dest="action", required=True)
    create = subparsers.add_parser("create")
    create.add_argument("--goal", required=True)
    create.add_argument("--route-id", required=True)
    create.add_argument("--reconciliation", type=Path, required=True)
    create.add_argument("--owner-source-decision", type=Path)
    create.add_argument("--backup", type=Path)
    create.add_argument(
        "--design-cycle-receipt",
        type=Path,
        help="Exact WebsiteOperator design-cycle receipt for a bounded DESIGN-COPY task.",
    )
    create.add_argument(
        "--design-copy-task-id",
        help="Exact DESIGN-COPY-NNN task id; requires --design-cycle-receipt.",
    )
    create.add_argument("--run-id", required=True)
    for action in ("stage", "import-assets", "context", "status"):
        item = subparsers.add_parser(action)
        item.add_argument("--run-id", required=True)
    validate = subparsers.add_parser("validate")
    validate.add_argument("--run-id", required=True)
    validate.add_argument("--claim-impacts", type=Path, required=True)
    validate.add_argument(
        "--claim-surfaces",
        type=Path,
        help="Hash-only public claim-surface manifest; required when a changed text rendering surface adds copy.",
    )
    candidate_qa = subparsers.add_parser("candidate-qa")
    candidate_qa.add_argument("--run-id", required=True)
    candidate_qa.add_argument("--motion-config", type=Path, required=True)
    candidate_qa.add_argument("--motion-config-sha256", required=True)
    candidate_qa.add_argument("--test-policy", type=Path, required=True)
    candidate_qa.add_argument("--test-policy-sha256", required=True)
    initial = subparsers.add_parser("initial-gate")
    initial.add_argument("--run-id", required=True)
    initial.add_argument("--visual-receipt", type=Path, required=True)
    initial.add_argument("--route-name", required=True)
    initial.add_argument("--engine", default="chromium")
    review = subparsers.add_parser("visual-review")
    review.add_argument("--run-id", required=True)
    review.add_argument("--capture-receipt", type=Path, required=True)
    review.add_argument("--manual-review", type=Path, required=True)
    review.add_argument("--human-acceptance", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    try:
        root = _find_repo_root(args.repo_root)
        if args.action == "create":
            job, path = create_design_delivery_job(
                goal=args.goal,
                route_id=args.route_id,
                reconciliation_receipt=args.reconciliation,
                owner_source_decision=args.owner_source_decision,
                backup_receipt=args.backup,
                design_cycle_receipt=args.design_cycle_receipt,
                design_copy_task_id=args.design_copy_task_id,
                run_id=args.run_id,
                repo_root=root,
            )
            payload: Mapping[str, Any] = {"job": job, "receipt": _relative_to_repo(root, path)}
        elif args.action == "stage":
            job, path = stage_design_delivery_job(args.run_id, repo_root=root)
            payload = {"job": job, "receipt": _relative_to_repo(root, path)}
        elif args.action == "import-assets":
            job, path = prepare_design_delivery_assets(
                args.run_id,
                repo_root=root,
            )
            payload = {"job": job, "receipt": _relative_to_repo(root, path)}
        elif args.action == "context":
            payload = worker_context_for_delivery_job(args.run_id, repo_root=root)
        elif args.action == "validate":
            job, path = validate_design_delivery_job(
                args.run_id,
                claim_impacts=_load_claim_impacts(args.claim_impacts, root),
                claim_surface_manifest=(
                    _load_claim_surface_manifest(args.claim_surfaces, root)
                    if args.claim_surfaces is not None
                    else []
                ),
                repo_root=root,
            )
            payload = {"job": job, "receipt": _relative_to_repo(root, path)}
        elif args.action == "candidate-qa":
            job, path = evaluate_delivery_candidate_qa(
                args.run_id,
                motion_config=args.motion_config,
                expected_motion_config_sha256=args.motion_config_sha256,
                test_policy=args.test_policy,
                expected_test_policy_sha256=args.test_policy_sha256,
                repo_root=root,
            )
            payload = {"job": job, "receipt": _relative_to_repo(root, path)}
        elif args.action == "initial-gate":
            job, path = evaluate_delivery_initial_gate(
                args.run_id,
                visual_receipt=args.visual_receipt,
                route_name=args.route_name,
                engine_name=args.engine,
                repo_root=root,
            )
            payload = {"job": job, "receipt": _relative_to_repo(root, path)}
        elif args.action == "visual-review":
            job, path = record_delivery_visual_review(
                args.run_id,
                capture_receipt=args.capture_receipt,
                manual_review=args.manual_review,
                human_acceptance=args.human_acceptance,
                repo_root=root,
            )
            payload = {"job": job, "receipt": _relative_to_repo(root, path)}
        else:
            job, path = load_latest_delivery_job(args.run_id, repo_root=root)
            payload = {
                "job": job,
                "receipt": _relative_to_repo(root, path),
                "verification": verify_design_delivery_job(job, repo_root=root),
            }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    except (
        DesignCandidateControlError,
        DesignCandidateInitialGateError,
        DesignCandidateTestEvidenceError,
        DesignMotionPerformanceBudgetError,
        DesignCandidateVisualReviewError,
        DesignEvidenceBriefError,
        PublicWebsiteDesignRunnerError,
        OSError,
    ) as exc:
        print(json.dumps({"state": "blocked", "error": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
