"""Aureon-owned entrypoint for bounded, receipt-backed self-coding.

The operator supplies a goal. Aureon's Architecture brain selects one clean,
tracked Python target from a deterministic repository shortlist, every coding
seat and process deliberates, and the Implementation Worker authors the diff.
The candidate is validated and retained as a proposal; this module never
mutates the repository or executes generated code.

Codex is deliberately absent from target selection and authoring.  A successful
proposal remains pending an exact senior review and a production Plumber/Magic
Star release implementation, which is not available in this checkout.
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
from pathlib import Path, PurePosixPath
from typing import Any, Sequence

from aureon.autonomous.aureon_agent_company_brain_fabric import (
    CANONICAL_AGENT_COMPANY_ROLE_COUNT,
    canonical_agent_company_brain_topology,
    company_brain_fabric_report,
)
from aureon.autonomous.aureon_internal_coding_workforce import (
    OllamaSwitchboardBrainResolver,
    WorkforceHold,
)
from aureon.autonomous.aureon_internal_patch_loop import (
    PRE_APPLY_COUNCIL_ROLES,
    InternalPatchHold,
    build_patch_request,
    run_internal_patch_cycle,
)
from aureon.autonomous.aureon_internal_work_ledger import (
    DurableInternalWorkLedger,
    WorkLedgerError,
)
from aureon.autonomous.aureon_safe_code_control import SafeCodeControl

SCHEMA_VERSION = "aureon-internal-self-coder-v1"
DEFAULT_LEDGER_PATH = Path("state/aureon_internal_coding_work_ledger.json")
DEFAULT_PROPOSAL_PATH = Path("state/aureon_internal_patch_proposals.json")
DEFAULT_EVIDENCE_PATH = Path("state/aureon_internal_self_coder_last_run.json")
MAX_CANDIDATES = 12
MAX_CANDIDATE_BYTES = 256 * 1024
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
    if not args or args[0] not in {"ls-files", "status"}:
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
    brain_resolver = resolver or OllamaSwitchboardBrainResolver()
    ledger_file = _bounded_state_path(repo_root, ledger_path)
    proposal_file = _bounded_state_path(repo_root, proposal_path)
    evidence_file = _bounded_state_path(repo_root, evidence_path)
    ledger = DurableInternalWorkLedger(ledger_file)
    workforce = ledger.bind_agent_company_workforce(
        brain_resolver,
        thought_path=thought_path,
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
    if not target_path:
        selection = select_target(root=repo_root, goal=goal_text, workforce=workforce)
        target = selection["target_path"]
    commands = tuple(tuple(str(part) for part in command) for command in test_commands)
    if not commands:
        commands = derive_test_commands(repo_root, target)
    request = build_patch_request(
        root=repo_root,
        goal=goal_text,
        target_path=target,
        test_commands=commands,
    )
    controller = SafeCodeControl(state_path=proposal_file)
    cycle = run_internal_patch_cycle(
        root=repo_root,
        request=request,
        workforce=workforce,
        controller=controller,
    )
    core = {
        "schema_version": SCHEMA_VERSION,
        "status": cycle["status"],
        "applied": cycle["applied"],
        "pending_senior_review": cycle["pending_senior_review"],
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
        "goal": goal_text,
        "target_selection": selection,
        "suggested_test_commands": [list(command) for command in commands],
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
    """Record advisory senior review while preserving the production HOLD.

    This function does not review or implement code. The caller must supply the
    SHA-256 digest of its independently produced senior review. The ledger only
    accepts the receipt when the resulting lifetime share remains at least 99%
    Aureon-internal work and every brain passport is still valid. It does not
    invoke a release gate, authorize mutation, or execute any suggested tests.
    """

    if not re.fullmatch(r"[0-9a-f]{64}", str(review_output_digest or "")):
        raise InternalSelfCoderHold("senior_review_output_digest_invalid")
    repo_root = Path(root).resolve()
    evidence_file = _bounded_state_path(repo_root, evidence_path)
    evidence = _read_evidence(evidence_file)
    if evidence.get("schema_version") != SCHEMA_VERSION or not evidence.get("pending_senior_review"):
        raise InternalSelfCoderHold("pending_self_coder_evidence_required")
    reviewed_evidence_digest = str(evidence["evidence_digest"])
    ledger = DurableInternalWorkLedger(_bounded_state_path(repo_root, ledger_path))
    patch_cycle = evidence.get("patch_cycle")
    council = patch_cycle.get("pre_apply_council") if isinstance(patch_cycle, dict) else None
    apply_evidence = patch_cycle.get("apply_evidence") if isinstance(patch_cycle, dict) else None
    fabric = evidence.get("agent_company_brain_fabric")
    evidence_ledger = evidence.get("work_ledger")
    council_decisions = council.get("decisions") if isinstance(council, dict) else None
    council_receipt_ids = (
        [
            receipt_id
            for item in council_decisions
            if isinstance(item, dict)
            for receipt_id in (
                item.get("agent_work_receipt_id"),
                item.get("process_work_receipt_id"),
            )
        ]
        if isinstance(council_decisions, list)
        else []
    )
    expected = CANONICAL_AGENT_COMPANY_ROLE_COUNT
    if (
        evidence.get("applied") is not False
        or evidence.get("proposal_only") is not True
        or evidence.get("release_hold") is not True
        or evidence.get("release_authorized") is not False
        or evidence.get("repository_mutation_authorized") is not False
        or evidence.get("generated_code_execution_authorized") is not False
        or evidence.get("repository_mutation_implemented") is not False
        or evidence.get("generated_code_execution_implemented") is not False
        or evidence.get("subprocess_test_execution_implemented") is not False
        or evidence.get("effect_attempted") is not False
        or evidence.get("test_commands_executed") is not False
        or not isinstance(patch_cycle, dict)
        or patch_cycle.get("applied") is not False
        or patch_cycle.get("release_authorized") is not False
        or patch_cycle.get("effect_attempted") is not False
        or patch_cycle.get("test_commands_executed") is not False
        or patch_cycle.get("repository_mutation_implemented") is not False
        or patch_cycle.get("generated_code_execution_implemented") is not False
        or patch_cycle.get("subprocess_test_execution_implemented") is not False
        or not isinstance(apply_evidence, dict)
        or apply_evidence.get("applied") is not False
        or apply_evidence.get("effect_attempted") is not False
        or apply_evidence.get("test_commands_executed") is not False
        or apply_evidence.get("release_authorized") is not False
        or apply_evidence.get("repository_mutation_implemented") is not False
        or apply_evidence.get("generated_code_execution_implemented") is not False
        or apply_evidence.get("subprocess_test_execution_implemented") is not False
        or not isinstance(council, dict)
        or council.get("accepted") is not True
        or council.get("acceptance_scope") != "proposal_review_only"
        or council.get("execution_authorized") is not False
        or council.get("release_authorized") is not False
        or council.get("decision_count") != len(PRE_APPLY_COUNCIL_ROLES) * 2
        or council.get("hold_count") != 0
        or not isinstance(council_decisions, list)
        or len(council_decisions) != len(PRE_APPLY_COUNCIL_ROLES)
        or {item.get("role") for item in council_decisions if isinstance(item, dict)}
        != set(PRE_APPLY_COUNCIL_ROLES)
        or any(
            not isinstance(item, dict)
            or item.get("agent_verdict") != "ACCEPT"
            or item.get("process_verdict") != "ACCEPT"
            for item in council_decisions
        )
        or len(council_receipt_ids) != len(PRE_APPLY_COUNCIL_ROLES) * 2
        or len(set(council_receipt_ids)) != len(council_receipt_ids)
        or any(
            not isinstance(receipt_id, str) or not receipt_id.startswith("work:")
            for receipt_id in council_receipt_ids
        )
        or not isinstance(fabric, dict)
        or fabric.get("ready") is not True
        or fabric.get("agent_brain_count") != expected
        or fabric.get("process_brain_count") != expected
        or fabric.get("brain_passport_count") != expected * 2
        or not isinstance(evidence_ledger, dict)
        or evidence_ledger.get("ten_nine_one_complete") is not True
    ):
        raise InternalSelfCoderHold("self_coder_proposal_review_evidence_invalid")
    ledger_before = ledger.status()
    ledger_receipts = {receipt.receipt_id: receipt for receipt in ledger.receipts()}
    _role_lanes, process_bindings = canonical_agent_company_brain_topology()
    expected_process_by_role = {owner: process_id for process_id, (_lane, owner) in process_bindings.items()}
    council_actor_binding_valid = (
        all(
            ledger_receipts[item["agent_work_receipt_id"]].actor_id == f"aureon:agent:{item['role']}"
            and ledger_receipts[item["process_work_receipt_id"]].actor_id
            == f"aureon:process:{item['process_id']}"
            and item["process_id"] == expected_process_by_role.get(item["role"])
            and ledger_receipts[item["agent_work_receipt_id"]].stage == "pre_apply_council"
            and ledger_receipts[item["process_work_receipt_id"]].stage == "pre_apply_council"
            for item in council_decisions
        )
        if set(council_receipt_ids).issubset(ledger_receipts)
        else False
    )
    if (
        any(
            evidence_ledger.get(key) != ledger_before.get(key)
            for key in ("receipt_count", "last_receipt_id", "state_hash")
        )
        or not council_actor_binding_valid
    ):
        raise InternalSelfCoderHold("self_coder_proposal_review_ledger_mismatch")
    workforce = ledger.bind_agent_company_workforce(resolver, thought_path=thought_path)
    before = workforce.report()
    internal_units = before.get("internal_work_units")
    total_units = before.get("total_work_units")
    if not before.get("brain_fabric_ready"):
        raise InternalSelfCoderHold("brain_fabric_not_ready_for_proposal_review")
    if before.get("ten_nine_one_complete") is not True:
        raise InternalSelfCoderHold("ten_nine_one_work_evidence_incomplete")
    if type(internal_units) is not int or type(total_units) is not int:
        raise InternalSelfCoderHold("workforce_ratio_evidence_invalid")
    if internal_units * 100 < (total_units + 1) * 99:
        raise InternalSelfCoderHold("senior_review_would_violate_99_percent_contract")
    receipt = workforce.record_senior_oversight(
        process_id="internal_review",
        stage="contract_review",
        reviewed_input_digest=reviewed_evidence_digest,
        review_output_digest=review_output_digest,
    )
    report = workforce.report()
    if not report.get("ready"):
        raise InternalSelfCoderHold("senior_proposal_review_did_not_close_workforce_contract")
    updated_core = {
        **{key: value for key, value in evidence.items() if key != "evidence_digest"},
        "status": "internal_patch_senior_proposal_review_recorded_release_hold",
        "pending_senior_review": False,
        "applied": False,
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
        "proposal_review_recorded": True,
        "reviewed_evidence_digest": reviewed_evidence_digest,
        "senior_review_output_digest": review_output_digest,
        "senior_proposal_review_receipt_id": receipt.receipt_id,
        "work_ledger": ledger.status(),
        "workforce_proposal_review_report": {
            **report,
            "report_scope": "workforce_review_evidence_only",
            "production_release_authorized": False,
        },
    }
    updated = {**updated_core, "evidence_digest": _digest(updated_core)}
    _write_evidence(evidence_file, updated)
    return updated


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
    parser = argparse.ArgumentParser(description="Create one held Aureon internal coding proposal.")
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
    return 0 if result.get("status") == "internal_patch_proposal_held_for_senior_review" else 1


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
