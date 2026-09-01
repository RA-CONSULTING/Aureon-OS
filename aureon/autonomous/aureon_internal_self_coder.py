"""Aureon-owned entrypoint for bounded, receipt-backed self-coding.

The operator supplies a goal. Aureon's Architecture brain selects one clean,
tracked Python target from a deterministic repository shortlist, every coding
seat and process deliberates, and the Implementation Worker authors the diff.
The candidate is validated, transiently HNC-sealed, and then burned; only
metadata and commitments are retained. This module never mutates the repository
or executes generated code.

Codex is deliberately absent from target selection and authoring.  A successful
local authoring experiment can prove only a transient HNC seal.  It is not a
recoverable proposal and cannot enter senior review until a durable authenticated
proposal vault and production Plumber/Magic Star boundary exist.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any, Sequence

from aureon.autonomous.aureon_agent_company_brain_fabric import (
    company_brain_fabric_report,
)
from aureon.autonomous.aureon_cloud_brain_composition import (
    TruthAuthorityBundle,
    build_local_confidential_self_coder_thought_path,
)
from aureon.autonomous.aureon_internal_coding_workforce import (
    LOCAL_SELF_CODER_PROVIDER_MODE,
    SELF_CODER_TRANSPORT_PREFLIGHT_SCHEMA,
    OllamaSwitchboardBrainResolver,
    WorkforceHold,
)
from aureon.autonomous.aureon_internal_patch_loop import (
    InternalPatchHold,
    build_patch_request,
    run_internal_patch_cycle,
)
from aureon.autonomous.aureon_internal_work_ledger import (
    DurableInternalWorkLedger,
    WorkLedgerError,
)
from aureon.autonomous.aureon_safe_code_control import SafeCodeControl
from aureon.autonomous.aureon_ten_nine_one_thought_path import (
    SELF_CODER_CONFIDENTIAL_PREFLIGHT_SCHEMA,
)
from aureon.autonomous.aureon_truth_gated_ten_nine_one import (
    TruthGatedTenNineOneThoughtPath,
)
from aureon.harmonic.hnc_quantum_packet_crypto import packet_master_key_from_env
from aureon.plumber.os_protection import LocalOSProtectionBoundary
from aureon.plumber.proposal_forge import LocalProposalForge

SCHEMA_VERSION = "aureon-internal-self-coder-v2"
DEFAULT_LEDGER_PATH = Path("state/aureon_internal_coding_work_ledger.json")
DEFAULT_PROPOSAL_PATH = Path("state/aureon_internal_patch_proposals.json")
DEFAULT_EVIDENCE_PATH = Path("state/aureon_internal_self_coder_last_run.json")
MAX_CANDIDATES = 12
MAX_CANDIDATE_BYTES = 256 * 1024
MAX_PROPOSAL_STATE_BYTES = 2 * 1024 * 1024
SELF_CODER_FORGE_ID = "aureon-internal-self-coder-proposal-forge-v1"
SELF_CODER_BOUNDARY_ID = "aureon-internal-self-coder-os-boundary-v1"
_CLI_REQUIRED_FALSE_FIELDS = frozenset(
    {
        "action_eligible",
        "applied",
        "aureon_evidence_raw_goal_retained",
        "aureon_evidence_raw_suggested_test_commands_retained",
        "client_external_model_egress_attempted",
        "codex_implementation",
        "durable_proposal_vault_available",
        "economic_eligible",
        "effect_attempted",
        "generated_code_execution_authorized",
        "generated_code_execution_implemented",
        "local_model_nonretention_verified",
        "local_model_server_downstream_egress_verified",
        "pending_senior_review",
        "production_magic_star_release_available",
        "production_ready",
        "proposal_created",
        "proposal_quarantined",
        "proposal_recoverable",
        "proposal_reviewable",
        "release_authorized",
        "repository_mutation_authorized",
        "repository_mutation_implemented",
        "subprocess_test_execution_implemented",
        "test_commands_executed",
    }
)
_CLI_RECURSIVE_FALSE_FIELDS = _CLI_REQUIRED_FALSE_FIELDS | {
    "execution_authorized",
    "filesystem_mutation_attempted",
    "final_applier_invoked",
}
OPENAI_ADVISER_ID = "openai:codex-senior-adviser-not-independently-attested"
OPENAI_REVIEWER_ID = "openai:codex-senior-reviewer-not-independently-attested"
OPENAI_ADVISER_EVIDENCE_SHA256 = hashlib.sha256(
    b"openai-adviser-evidence-not-independently-attested"
).hexdigest()
EXCLUDED_PARTS = {
    ".git",
    ".venv",
    "archive",
    "build",
    "dist",
    "docs",
    "frontend",
    "imports",
    "node_modules",
    "site-packages",
    "tests",
    "vendor",
}
SENSITIVE_TOKENS = {
    "auth",
    "billing",
    "credential",
    "economic",
    "exchange",
    "filing",
    "order",
    "payment",
    "secret",
    "security",
    "trading",
    "wallet",
}
STOP_WORDS = {
    "a",
    "and",
    "for",
    "in",
    "of",
    "on",
    "the",
    "to",
    "with",
}


class InternalSelfCoderHold(RuntimeError):
    """Aureon could not safely form or record a bounded coding proposal."""


def _canonical_json(value: Any, *, newline: bool = False) -> bytes:
    payload = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return payload + (b"\n" if newline else b"")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _all_cli_authority_and_effect_flags_false(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            must_be_false = (
                key in _CLI_RECURSIVE_FALSE_FIELDS
                or key.endswith("_authorized")
                or key.endswith("_implemented")
                or key.endswith("_eligible")
            )
            if must_be_false and item is not False:
                return False
            if not _all_cli_authority_and_effect_flags_false(item):
                return False
        return True
    if isinstance(value, (list, tuple)):
        return all(_all_cli_authority_and_effect_flags_false(item) for item in value)
    return True


def _repo_relative(value: str) -> str:
    raw = str(value or "").strip().replace("\\", "/")
    path = PurePosixPath(raw)
    if not raw or path.is_absolute() or ".." in path.parts or raw.startswith("/"):
        raise InternalSelfCoderHold("target_path_must_be_repo_relative")
    return path.as_posix()


def _bounded_state_path(root: Path, value: Path) -> Path:
    """Resolve a JSON evidence path strictly beneath the repository state dir."""

    repo_root = Path(root).resolve()
    state_root = (repo_root / "state").resolve()
    candidate = value if value.is_absolute() else repo_root / value
    resolved = candidate.resolve()
    try:
        state_root.relative_to(repo_root)
        resolved.relative_to(state_root)
    except ValueError as exc:
        raise InternalSelfCoderHold("self_coder_state_path_must_remain_under_repo_state") from exc
    if resolved.suffix.casefold() != ".json":
        raise InternalSelfCoderHold("self_coder_state_path_must_be_json")
    return resolved


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    allowed = bool(
        args
        and (
            args[0] in {"ls-files", "status"}
            or args == ("rev-parse", "HEAD")
        )
    )
    if not allowed:
        raise InternalSelfCoderHold("git_command_outside_read_only_inventory")
    try:
        return subprocess.run(
            ["git", "-c", "core.quotepath=false", *args],
            cwd=root,
            capture_output=True,
            check=False,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise InternalSelfCoderHold("git_repository_evidence_unavailable") from exc


def _head_commit(root: Path) -> str:
    result = _git(root, "rev-parse", "HEAD")
    value = result.stdout.strip().lower()
    if result.returncode != 0 or re.fullmatch(r"[0-9a-f]{40}", value) is None:
        raise InternalSelfCoderHold("git_head_commit_unavailable")
    return value


def _default_proposal_forge() -> LocalProposalForge:
    boundary = LocalOSProtectionBoundary(
        boundary_id=SELF_CODER_BOUNDARY_ID,
        master_key_provider=lambda: packet_master_key_from_env() or None,
        max_ingress_bytes=1024 * 1024,
        max_active_handles=4,
        max_active_ingress_bytes=4 * 1024 * 1024,
        max_replay_tokens=256,
        max_quarantine_evidence=64,
    )
    return LocalProposalForge(
        forge_id=SELF_CODER_FORGE_ID,
        os_boundary=boundary,
    )


def _require_forge_preflight(forge: LocalProposalForge) -> dict[str, Any]:
    if type(forge) is not LocalProposalForge:
        raise InternalSelfCoderHold("trusted_local_proposal_forge_required")
    preflight = forge.preflight()
    expected = {
        "schema",
        "forge_id",
        "ready",
        "reason_code",
        "os_key_preflight_schema",
        "key_material_returned",
        "proposal_admission_authorized",
        "action_eligible",
        "economic_eligible",
        "local_development_only",
        "production_ready",
    }
    if (
        not isinstance(preflight, dict)
        or set(preflight) != expected
        or preflight.get("schema")
        != "aureon.plumber.proposal-forge-preflight.v0"
        or preflight.get("ready") is not True
        or preflight.get("reason_code") != "ready"
        or preflight.get("os_key_preflight_schema")
        != "aureon.plumber.os-key-preflight.v0"
        or preflight.get("key_material_returned") is not False
        or preflight.get("proposal_admission_authorized") is not False
        or preflight.get("action_eligible") is not False
        or preflight.get("economic_eligible") is not False
        or preflight.get("local_development_only") is not True
        or preflight.get("production_ready") is not False
    ):
        raise InternalSelfCoderHold("hnc_proposal_master_key_unavailable")
    return preflight


def _require_confidential_thought_path(thought_path: Any) -> dict[str, Any]:
    if type(thought_path) is not TruthGatedTenNineOneThoughtPath:
        raise InternalSelfCoderHold("self_coder_commitment_only_thought_path_required")
    preflight = thought_path.self_coder_confidential_preflight()
    expected = {
        "schema_version",
        "ready",
        "truth_gate_enforced",
        "trusted_local_evidence_resolver",
        "trusted_receipt_backed_truth_gate",
        "commitment_only_propagation",
        "raw_answer_bus_persistence_authorized",
        "raw_answer_trace_persistence_authorized",
        "action_eligible",
        "economic_eligible",
    }
    if (
        not isinstance(preflight, dict)
        or set(preflight) != expected
        or preflight.get("schema_version")
        != SELF_CODER_CONFIDENTIAL_PREFLIGHT_SCHEMA
        or preflight.get("ready") is not True
        or preflight.get("truth_gate_enforced") is not True
        or preflight.get("trusted_local_evidence_resolver") is not True
        or preflight.get("trusted_receipt_backed_truth_gate") is not True
        or preflight.get("commitment_only_propagation") is not True
        or preflight.get("raw_answer_bus_persistence_authorized") is not False
        or preflight.get("raw_answer_trace_persistence_authorized") is not False
        or preflight.get("action_eligible") is not False
        or preflight.get("economic_eligible") is not False
    ):
        raise InternalSelfCoderHold("self_coder_commitment_only_thought_path_required")
    return preflight


def _require_local_transport(resolver: Any) -> dict[str, Any]:
    preflight_method = getattr(resolver, "self_coder_transport_preflight", None)
    preflight = preflight_method() if callable(preflight_method) else None
    expected = {
        "schema_version",
        "ready",
        "provider_mode",
        "endpoint_authority_digest",
        "endpoint_loopback",
        "external_source_egress_authorized",
        "action_eligible",
        "economic_eligible",
    }
    if (
        not isinstance(preflight, dict)
        or set(preflight) != expected
        or preflight.get("schema_version") != SELF_CODER_TRANSPORT_PREFLIGHT_SCHEMA
        or preflight.get("ready") is not True
        or preflight.get("provider_mode") != LOCAL_SELF_CODER_PROVIDER_MODE
        or re.fullmatch(r"[0-9a-f]{64}", str(preflight.get("endpoint_authority_digest") or ""))
        is None
        or preflight.get("endpoint_loopback") is not True
        or preflight.get("external_source_egress_authorized") is not False
        or preflight.get("action_eligible") is not False
        or preflight.get("economic_eligible") is not False
    ):
        raise InternalSelfCoderHold("self_coder_external_model_egress_forbidden")
    return preflight


def _metadata_only_target_selection(selection: dict[str, Any]) -> dict[str, Any]:
    public = {key: value for key, value in selection.items() if key != "reason"}
    reason = str(selection.get("reason") or "")
    public.update(
        {
            "reason_sha256": hashlib.sha256(reason.encode("utf-8")).hexdigest(),
            "raw_reason_included": False,
        }
    )
    return public


def _require_empty_proposal_state(path: Path) -> None:
    """Reject corrupt, unknown, or previously populated proposal state."""

    if not path.exists():
        return
    try:
        raw = path.read_bytes()
        if not raw or len(raw) > MAX_PROPOSAL_STATE_BYTES:
            raise ValueError("proposal state size invalid")
        payload = json.loads(raw.decode("utf-8", "strict"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise InternalSelfCoderHold("existing_proposal_state_unreadable") from exc
    expected_fields = {
        "enabled",
        "auto_approve",
        "last_error",
        "pending_count",
        "pending_proposals",
        "recent_reviews",
    }
    if (
        not isinstance(payload, dict)
        or set(payload) != expected_fields
        or payload.get("enabled") is not True
        or type(payload.get("auto_approve")) is not bool
        or payload.get("last_error") != ""
        or payload.get("pending_count") != 0
        or payload.get("pending_proposals") != []
        or payload.get("recent_reviews") != []
    ):
        raise InternalSelfCoderHold(
            "existing_proposal_state_requires_manual_protected_archive"
        )


def _clean_tracked_target(root: Path, target_path: str) -> Path:
    target = _repo_relative(target_path)
    tracked = _git(root, "ls-files", "--error-unmatch", "--", target)
    if tracked.returncode != 0:
        raise InternalSelfCoderHold("target_must_be_tracked")
    status = _git(root, "status", "--porcelain=v1", "--", target)
    if status.returncode != 0 or status.stdout.strip():
        raise InternalSelfCoderHold("target_must_be_clean")
    resolved = (root / target).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise InternalSelfCoderHold("target_escaped_repository") from exc
    if resolved.suffix.casefold() != ".py" or not resolved.is_file():
        raise InternalSelfCoderHold("tracked_python_target_required")
    lowered_parts = {part.casefold() for part in PurePosixPath(target).parts}
    if lowered_parts.intersection(EXCLUDED_PARTS) or any(
        token in target.casefold() for token in SENSITIVE_TOKENS
    ):
        raise InternalSelfCoderHold("target_outside_bounded_self_coding_scope")
    if resolved.stat().st_size <= 0 or resolved.stat().st_size > MAX_CANDIDATE_BYTES:
        raise InternalSelfCoderHold("target_size_limit_failed")
    return resolved


def _goal_tokens(goal: str) -> set[str]:
    return {
        token for token in re.findall(r"[a-z0-9_]{3,}", str(goal or "").casefold()) if token not in STOP_WORDS
    }


def _candidate_score(root: Path, relative: str, tokens: set[str]) -> tuple[int, int, str]:
    path_text = relative.casefold()
    source = (root / relative).read_text(encoding="utf-8", errors="ignore")[:64_000].casefold()
    path_hits = sum(token in path_text for token in tokens)
    source_hits = sum(min(source.count(token), 4) for token in tokens)
    return (path_hits * 20 + source_hits, path_hits, relative)


def discover_clean_python_candidates(root: Path, goal: str) -> tuple[str, ...]:
    """Return a deterministic, goal-ranked set of clean tracked Python files."""

    repo_root = Path(root).resolve()
    tracked = _git(repo_root, "ls-files", "--", "*.py")
    if tracked.returncode != 0:
        raise InternalSelfCoderHold("tracked_source_inventory_unavailable")
    tokens = _goal_tokens(goal)
    if not tokens:
        raise InternalSelfCoderHold("goal_has_no_selection_tokens")
    ranked: list[tuple[int, int, str]] = []
    for raw in tracked.stdout.splitlines():
        relative = _repo_relative(raw)
        try:
            _clean_tracked_target(repo_root, relative)
        except InternalSelfCoderHold:
            continue
        score = _candidate_score(repo_root, relative, tokens)
        if score[0] > 0:
            ranked.append(score)
    ranked.sort(key=lambda row: (-row[0], -row[1], row[2].casefold()))
    candidates = tuple(row[2] for row in ranked[:MAX_CANDIDATES])
    if not candidates:
        raise InternalSelfCoderHold("no_clean_goal_relevant_python_candidate")
    return candidates


def _parse_selection(raw: str) -> dict[str, Any]:
    text = str(raw or "").strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.I | re.S)
    if fenced:
        text = fenced.group(1).strip()
    payloads: list[Any] = []
    try:
        payloads.append(json.loads(text))
    except (TypeError, ValueError):
        decoder = json.JSONDecoder()
        for offset, character in enumerate(text):
            if character != "{":
                continue
            try:
                payload, _end = decoder.raw_decode(text[offset:])
            except ValueError:
                continue
            if isinstance(payload, dict) and set(payload) == {"target_path", "reason"}:
                payloads.append(payload)
    valid = [
        payload
        for payload in payloads
        if isinstance(payload, dict) and set(payload) == {"target_path", "reason"}
    ]
    if len(valid) != 1:
        raise InternalSelfCoderHold("architecture_selection_json_invalid")
    payload = valid[0]
    if not isinstance(payload, dict) or set(payload) != {"target_path", "reason"}:
        raise InternalSelfCoderHold("architecture_selection_shape_invalid")
    target = _repo_relative(payload.get("target_path", ""))
    reason = str(payload.get("reason") or "").strip()
    if not reason or len(reason) > 1000:
        raise InternalSelfCoderHold("architecture_selection_reason_invalid")
    return {"target_path": target, "reason": reason}


def select_target(*, root: Path, goal: str, workforce: Any) -> dict[str, Any]:
    candidates = discover_clean_python_candidates(root, goal)
    candidate_digest = _digest(list(candidates))
    prompt = (
        'Return one JSON object only, shaped exactly as {"target_path":"...","reason":"..."}. '
        "Select one target from the supplied "
        "candidate list for the stated coding goal. Do not invent a path and do not select authority, "
        "credential, economic, deployment, or test code.\n"
        f"Goal: {str(goal).strip()}\n"
        f"Candidate digest: {candidate_digest}\n"
        f"Candidates: {json.dumps(list(candidates), ensure_ascii=True)}"
    )
    receipts = []
    selection: dict[str, Any] | None = None
    for attempt in range(1, 3):
        attempt_prompt = prompt
        if attempt == 2:
            attempt_prompt = (
                prompt
                + "\nYour first response failed the strict JSON parser. Return only the one JSON object now."
            )
        raw, receipt = workforce.decide(
            subject_type="agent",
            subject_id="Code Architect",
            process_id=workforce.process_id_for_role("Code Architect"),
            prompt=attempt_prompt,
            stage="autonomous_target_selection",
            work_kind="target_selection",
        )
        receipts.append(receipt.receipt_id)
        try:
            selection = _parse_selection(raw)
        except InternalSelfCoderHold:
            continue
        break
    if selection is None:
        raise InternalSelfCoderHold("architecture_selection_json_invalid")
    if selection["target_path"] not in candidates:
        raise InternalSelfCoderHold("architecture_selected_unoffered_target")
    _clean_tracked_target(Path(root).resolve(), selection["target_path"])
    return {
        "schema_version": "aureon-internal-target-selection-v1",
        **selection,
        "candidate_count": len(candidates),
        "candidate_digest": candidate_digest,
        "selection_work_receipt_id": receipts[-1],
        "selection_work_receipt_ids": receipts,
        "action_eligible": False,
        "economic_eligible": False,
    }


def derive_test_commands(root: Path, target_path: str) -> tuple[tuple[str, ...], ...]:
    """Derive suggested offline checks; this module never executes them."""

    target = _repo_relative(target_path)
    source = _clean_tracked_target(Path(root).resolve(), target)
    exact_test = Path(root) / "tests" / f"test_{source.stem}.py"
    commands: list[tuple[str, ...]] = [
        (sys.executable, "-m", "py_compile", target),
        (sys.executable, "-m", "ruff", "check", target, "--select", "E9,F"),
    ]
    if exact_test.is_file():
        commands.append(
            (
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "--disable-socket",
                exact_test.relative_to(root).as_posix(),
            )
        )
    return tuple(commands)


def _write_evidence(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = _canonical_json(payload, newline=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.chmod(temporary, 0o600)
        except OSError:
            pass
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _read_evidence(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
        payload = json.loads(raw.decode("utf-8", "strict"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise InternalSelfCoderHold("self_coder_evidence_unreadable") from exc
    if not isinstance(payload, dict) or raw != _canonical_json(payload, newline=True):
        raise InternalSelfCoderHold("self_coder_evidence_not_canonical")
    observed = payload.get("evidence_digest")
    core = {key: value for key, value in payload.items() if key != "evidence_digest"}
    if observed != _digest(core):
        raise InternalSelfCoderHold("self_coder_evidence_digest_mismatch")
    return payload


def read_self_coding_evidence(
    *,
    root: Path,
    evidence_path: Path = DEFAULT_EVIDENCE_PATH,
) -> dict[str, Any]:
    """Read and validate the canonical receipt from the latest coding cycle."""

    repo_root = Path(root).resolve()
    return _read_evidence(_bounded_state_path(repo_root, evidence_path))


def run_autonomous_self_coding(
    *,
    root: Path,
    goal: str,
    target_path: str = "",
    test_commands: Sequence[Sequence[str]] = (),
    ledger_path: Path = DEFAULT_LEDGER_PATH,
    proposal_path: Path = DEFAULT_PROPOSAL_PATH,
    evidence_path: Path = DEFAULT_EVIDENCE_PATH,
    resolver: Any = None,
    thought_path: Any = None,
    truth_authorities: TruthAuthorityBundle | None = None,
    proposal_forge: LocalProposalForge | None = None,
) -> dict[str, Any]:
    """Run one bounded Aureon-selected and Aureon-authored coding cycle."""

    repo_root = Path(root).resolve()
    goal_text = str(goal or "").strip()
    if not goal_text:
        raise InternalSelfCoderHold("goal_required")
    if target_path:
        target = _repo_relative(target_path)
        _clean_tracked_target(repo_root, target)
        selection = {
            "schema_version": "aureon-internal-target-selection-v1",
            "target_path": target,
            "reason": "Exact target constrained by the operator scope.",
            "candidate_count": 1,
            "candidate_digest": _digest([target]),
            "selection_work_receipt_id": "",
            "selection_work_receipt_ids": [],
            "action_eligible": False,
            "economic_eligible": False,
        }
    ledger_file = _bounded_state_path(repo_root, ledger_path)
    proposal_file = _bounded_state_path(repo_root, proposal_path)
    evidence_file = _bounded_state_path(repo_root, evidence_path)
    if evidence_file.exists():
        _read_evidence(evidence_file)
        raise InternalSelfCoderHold("existing_self_coder_evidence_requires_manual_archive")
    _require_empty_proposal_state(proposal_file)
    selected_forge = proposal_forge if proposal_forge is not None else _default_proposal_forge()
    _require_forge_preflight(selected_forge)
    selected_thought_path = thought_path
    if selected_thought_path is None:
        try:
            selected_thought_path = build_local_confidential_self_coder_thought_path(
                truth_authorities,
                root=repo_root,
            )
        except ValueError as exc:
            reason = str(exc)
            if reason == "authenticated_self_coder_truth_authority_bundle_required":
                raise InternalSelfCoderHold(reason) from exc
            raise InternalSelfCoderHold(
                "confidential_self_coder_thought_path_unavailable"
            ) from exc
    _require_confidential_thought_path(selected_thought_path)
    brain_resolver = resolver or OllamaSwitchboardBrainResolver()
    transport_preflight = _require_local_transport(brain_resolver)
    ledger = DurableInternalWorkLedger(ledger_file)
    workforce = ledger.bind_agent_company_workforce(
        brain_resolver,
        thought_path=selected_thought_path,
    )
    company_brain_fabric = company_brain_fabric_report(workforce)
    if (
        not company_brain_fabric.get("ready")
        or company_brain_fabric.get("tools_enabled") is not False
    ):
        raise InternalSelfCoderHold("agent_company_brain_fabric_not_ready")
    initial_workforce_report = workforce.report()
    if not initial_workforce_report.get("brain_fabric_ready"):
        raise InternalSelfCoderHold("coding_workforce_brain_fabric_not_ready")
    workforce.assert_sensitive_local_only(
        endpoint_authority_digest=str(transport_preflight["endpoint_authority_digest"])
    )
    if not target_path:
        selection = select_target(root=repo_root, goal=goal_text, workforce=workforce)
        target = str(selection["target_path"])
    commands = tuple(tuple(str(part) for part in command) for command in test_commands)
    if not commands:
        commands = derive_test_commands(repo_root, target)
    request = build_patch_request(
        root=repo_root,
        goal=goal_text,
        target_path=target,
        test_commands=commands,
    )
    base_commit = _head_commit(repo_root)
    controller = SafeCodeControl(state_path=proposal_file)
    cycle = run_internal_patch_cycle(
        root=repo_root,
        request=request,
        workforce=workforce,
        controller=controller,
        proposal_forge=selected_forge,
        base_commit=base_commit,
        adviser_id=OPENAI_ADVISER_ID,
        reviewer_id=OPENAI_REVIEWER_ID,
        adviser_evidence_sha256=OPENAI_ADVISER_EVIDENCE_SHA256,
    )
    proposal_protection = cycle.get("proposal_protection")
    transient_hnc_seal_verified = bool(
        isinstance(proposal_protection, dict)
        and proposal_protection.get("admitted_hnc") is True
        and proposal_protection.get("transient_hnc_seal_verified") is True
        and proposal_protection.get("proposal_recoverable") is False
    )
    core = {
        "schema_version": SCHEMA_VERSION,
        "status": cycle["status"],
        "applied": cycle["applied"],
        "pending_senior_review": cycle["pending_senior_review"],
        "proposal_created": False,
        "proposal_recoverable": False,
        "proposal_reviewable": False,
        "transient_hnc_seal_verified": transient_hnc_seal_verified,
        "durable_proposal_vault_available": False,
        "proposal_quarantined": bool(
            isinstance(proposal_protection, dict)
            and proposal_protection.get("quarantined_hnc") is True
        ),
        "proposal_only": True,
        "release_hold": True,
        "release_authorized": False,
        "repository_mutation_authorized": False,
        "generated_code_execution_authorized": False,
        "repository_mutation_implemented": False,
        "generated_code_execution_implemented": False,
        "subprocess_test_execution_implemented": False,
        "effect_attempted": False,
        "test_commands_executed": False,
        "production_magic_star_release_available": False,
        "production_ready": False,
        "base_commit": base_commit,
        "goal_sha256": hashlib.sha256(goal_text.encode("utf-8")).hexdigest(),
        "aureon_evidence_raw_goal_retained": False,
        "local_model_nonretention_verified": False,
        "client_external_model_egress_attempted": False,
        "local_model_server_downstream_egress_verified": False,
        "target_selection": _metadata_only_target_selection(selection),
        "suggested_test_commands_sha256": _digest(
            {"test_commands": [list(command) for command in commands]}
        ),
        "suggested_test_command_count": len(commands),
        "aureon_evidence_raw_suggested_test_commands_retained": False,
        "patch_cycle": cycle,
        "agent_company_brain_fabric": company_brain_fabric,
        "work_ledger": ledger.status(),
        "codex_role": "senior_review_and_veto_only",
        "codex_implementation": False,
        "action_eligible": False,
        "economic_eligible": False,
    }
    evidence = {**core, "evidence_digest": _digest(core)}
    _write_evidence(evidence_file, evidence)
    return evidence


def record_senior_proposal_review(
    *,
    root: Path,
    review_output_digest: str,
    ledger_path: Path = DEFAULT_LEDGER_PATH,
    evidence_path: Path = DEFAULT_EVIDENCE_PATH,
    resolver: Any = None,
    thought_path: Any = None,
) -> dict[str, Any]:
    """Hold review until a durable authenticated proposal vault exists.

    The current self-coder persists only commitment metadata.  A process-epoch
    opaque handle is not a reviewable proposal, so caller-supplied JSON or a
    review digest can never open this route.
    """

    del root, ledger_path, evidence_path, resolver, thought_path
    if not re.fullmatch(r"[0-9a-f]{64}", str(review_output_digest or "")):
        raise InternalSelfCoderHold("senior_review_output_digest_invalid")
    raise InternalSelfCoderHold("durable_proposal_vault_unavailable")

def record_senior_release_review(
    *,
    root: Path,
    review_output_digest: str,
    ledger_path: Path = DEFAULT_LEDGER_PATH,
    evidence_path: Path = DEFAULT_EVIDENCE_PATH,
    resolver: Any = None,
    full_stack_gate: Any = None,
    thought_path: Any = None,
) -> dict[str, Any]:
    """Disabled compatibility entrypoint; this checkout cannot release code."""

    del root, review_output_digest, ledger_path, evidence_path, resolver, full_stack_gate, thought_path
    raise InternalSelfCoderHold("release_review_entrypoint_disabled_proposal_only")


def _parse_test_command(value: str) -> tuple[str, ...]:
    try:
        payload = json.loads(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("test command must be a JSON string array") from exc
    if (
        not isinstance(payload, list)
        or not payload
        or not all(isinstance(part, str) and part for part in payload)
    ):
        raise argparse.ArgumentTypeError("test command must be a non-empty JSON string array")
    return tuple(payload)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run one held Aureon transient HNC seal-and-burn experiment."
    )
    parser.add_argument("--goal", required=True)
    parser.add_argument("--target", default="", help="Optional clean tracked Python target constraint.")
    parser.add_argument(
        "--test-command-json",
        action="append",
        default=[],
        type=_parse_test_command,
        help="Suggested checks to record only; this module never executes them.",
    )
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    try:
        result = run_autonomous_self_coding(
            root=args.root,
            goal=args.goal,
            target_path=args.target,
            test_commands=args.test_command_json,
        )
    except (InternalPatchHold, InternalSelfCoderHold, WorkLedgerError, WorkforceHold) as exc:
        print(json.dumps({"ok": False, "status": "hold", "reason": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    patch_cycle = result.get("patch_cycle")
    proposal_protection = (
        patch_cycle.get("proposal_protection")
        if isinstance(patch_cycle, dict)
        else {}
    )
    successful_transient_hold = (
        result.get("status") == "internal_patch_transient_hnc_seal_held"
        and all(result.get(field) is False for field in _CLI_REQUIRED_FALSE_FIELDS)
        and _all_cli_authority_and_effect_flags_false(result)
        and result.get("transient_hnc_seal_verified") is True
        and result.get("proposal_only") is True
        and result.get("release_hold") is True
        and isinstance(proposal_protection, dict)
        and proposal_protection.get("transient_hnc_handle_burned") is True
    )
    return 0 if successful_transient_hold else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "DEFAULT_EVIDENCE_PATH",
    "DEFAULT_LEDGER_PATH",
    "DEFAULT_PROPOSAL_PATH",
    "InternalSelfCoderHold",
    "SCHEMA_VERSION",
    "derive_test_commands",
    "discover_clean_python_candidates",
    "read_self_coding_evidence",
    "run_autonomous_self_coding",
    "record_senior_proposal_review",
    "record_senior_release_review",
    "select_target",
]
