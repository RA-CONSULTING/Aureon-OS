"""Compact, fail-closed adapter from the self-run loop to Aureon's self-coder.

The adapter does not author code and does not grant release authority.  It
invokes exactly one already-guarded internal coding cycle, or returns the
existing pending-review receipt without invoking any brain again.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from aureon.autonomous.aureon_agent_company_brain_fabric import (
    CANONICAL_AGENT_COMPANY_ROLE_COUNT,
)
from aureon.autonomous.aureon_internal_coding_workforce import WorkforceHold
from aureon.autonomous.aureon_internal_patch_loop import InternalPatchHold
from aureon.autonomous.aureon_internal_self_coder import (
    DEFAULT_EVIDENCE_PATH,
    DEFAULT_LEDGER_PATH,
    InternalSelfCoderHold,
    read_self_coding_evidence,
    run_autonomous_self_coding,
)
from aureon.autonomous.aureon_internal_work_ledger import WorkLedgerError

SelfCoder = Callable[..., Mapping[str, Any]]
_SAFE_STATUS = re.compile(r"[a-z0-9_]{1,128}")
_HEX_64 = re.compile(r"[0-9a-f]{64}")
COMPACT_SELF_CODER_SUMMARY_FIELDS = frozenset(
    {
        "applied",
        "pending_senior_review",
        "release_ready",
        "evidence_digest",
        "agent_company_brain_fabric_ready",
        "agent_brain_count",
        "process_brain_count",
        "brain_passport_count",
        "work_receipt_count",
        "codex_implementation",
        "action_eligible",
        "economic_eligible",
    }
)


def _held_result(reason_code: str, *, status: str = "internal_self_coder_held") -> dict[str, Any]:
    return {
        "status": status,
        "ok": False,
        "summary": {
            "reason_code": reason_code,
            "applied": False,
            "pending_senior_review": False,
            "release_ready": False,
            "codex_implementation": False,
            "action_eligible": False,
            "economic_eligible": False,
        },
        "output_files": [],
    }


def _compact_result(result: Mapping[str, Any]) -> dict[str, Any]:
    status = result.get("status")
    applied = result.get("applied")
    pending = result.get("pending_senior_review")
    digest = result.get("evidence_digest")
    fabric = result.get("agent_company_brain_fabric")
    ledger = result.get("work_ledger")
    if (
        not isinstance(status, str)
        or _SAFE_STATUS.fullmatch(status) is None
        or type(applied) is not bool
        or type(pending) is not bool
        or (applied and not pending)
        or not isinstance(digest, str)
        or _HEX_64.fullmatch(digest) is None
        or not isinstance(fabric, Mapping)
        or not isinstance(ledger, Mapping)
        or result.get("codex_implementation") is not False
        or result.get("action_eligible") is not False
        or result.get("economic_eligible") is not False
    ):
        return _held_result("internal_self_coder_receipt_invalid")

    agent_count = fabric.get("agent_brain_count")
    process_count = fabric.get("process_brain_count")
    passport_count = fabric.get("brain_passport_count")
    work_receipt_count = ledger.get("receipt_count")
    if (
        fabric.get("ready") is not True
        or type(agent_count) is not int
        or type(process_count) is not int
        or type(passport_count) is not int
        or type(work_receipt_count) is not int
        or agent_count != CANONICAL_AGENT_COMPANY_ROLE_COUNT
        or process_count != CANONICAL_AGENT_COMPANY_ROLE_COUNT
        or passport_count != CANONICAL_AGENT_COMPANY_ROLE_COUNT * 2
        or work_receipt_count < 1
    ):
        return _held_result("internal_self_coder_brain_receipt_invalid")

    return {
        "status": status,
        "ok": bool(applied and pending),
        "summary": {
            "applied": applied,
            "pending_senior_review": pending,
            "release_ready": False,
            "evidence_digest": digest,
            "agent_company_brain_fabric_ready": True,
            "agent_brain_count": agent_count,
            "process_brain_count": process_count,
            "brain_passport_count": passport_count,
            "work_receipt_count": work_receipt_count,
            "codex_implementation": False,
            "action_eligible": False,
            "economic_eligible": False,
        },
        "output_files": [
            DEFAULT_EVIDENCE_PATH.as_posix(),
            DEFAULT_LEDGER_PATH.as_posix(),
        ],
    }


def run_self_coding_task(
    root: Path,
    goal: str,
    *,
    enabled: bool = False,
    target_path: str = "",
    test_commands: Sequence[Sequence[str]] = (),
    resolver: Any = None,
    coder: SelfCoder = run_autonomous_self_coding,
) -> dict[str, Any]:
    """Run one Aureon-owned patch cycle, never a second cycle awaiting review."""

    if enabled is not True:
        return _held_result(
            "internal_self_coder_not_enabled",
            status="internal_self_coder_disabled",
        )
    repo_root = Path(root).resolve()
    evidence_file = repo_root / DEFAULT_EVIDENCE_PATH
    if evidence_file.exists():
        try:
            prior = read_self_coding_evidence(root=repo_root)
        except InternalSelfCoderHold:
            return _held_result("existing_self_coder_evidence_invalid")
        if prior.get("pending_senior_review") is True:
            compact = _compact_result(prior)
            if compact["ok"]:
                compact["status"] = "internal_self_coder_pending_senior_review"
            return compact

    try:
        result = coder(
            root=repo_root,
            goal=str(goal or "").strip(),
            target_path=str(target_path or ""),
            test_commands=test_commands,
            resolver=resolver,
        )
    except InternalPatchHold:
        return _held_result("internal_patch_hold")
    except InternalSelfCoderHold:
        return _held_result("internal_self_coder_hold")
    except WorkLedgerError:
        return _held_result("internal_work_ledger_hold")
    except WorkforceHold:
        return _held_result("internal_coding_workforce_hold")
    except Exception:
        return _held_result(
            "unexpected_internal_self_coder_error",
            status="internal_self_coder_error",
        )
    if not isinstance(result, Mapping):
        return _held_result("internal_self_coder_receipt_invalid")
    return _compact_result(result)


def self_coding_patch_lane_blocked(root: Path) -> bool:
    """Fail closed when pending or invalid evidence forbids another code mutation."""

    repo_root = Path(root).resolve()
    if not (repo_root / DEFAULT_EVIDENCE_PATH).exists():
        return False
    try:
        evidence = read_self_coding_evidence(root=repo_root)
    except InternalSelfCoderHold:
        return True
    return evidence.get("pending_senior_review") is True


__all__ = [
    "COMPACT_SELF_CODER_SUMMARY_FIELDS",
    "run_self_coding_task",
    "self_coding_patch_lane_blocked",
]
