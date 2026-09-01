"""Compact, fail-closed adapter from the self-run loop to Aureon's self-coder.

The adapter does not author code and does not grant review or release authority.
It invokes at most one already-guarded internal coding experiment.  Current
transient-seal evidence always returns HOLD, and any existing evidence blocks a
second brain cycle until it is manually archived.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from aureon.autonomous.aureon_internal_coding_workforce import WorkforceHold
from aureon.autonomous.aureon_internal_patch_loop import InternalPatchHold
from aureon.autonomous.aureon_internal_self_coder import (
    DEFAULT_EVIDENCE_PATH,
    InternalSelfCoderHold,
    read_self_coding_evidence,
    run_autonomous_self_coding,
)
from aureon.autonomous.aureon_internal_work_ledger import WorkLedgerError

SelfCoder = Callable[..., Mapping[str, Any]]
_HEX_64 = re.compile(r"[0-9a-f]{64}")
COMPACT_SELF_CODER_SUMMARY_FIELDS = frozenset(
    {
        "reason_code",
        "applied",
        "pending_senior_review",
        "release_ready",
        "codex_implementation",
        "action_eligible",
        "economic_eligible",
    }
)
_FALSE_EFFECT_FIELDS = frozenset(
    {
        "action_eligible",
        "applied",
        "codex_implementation",
        "economic_eligible",
        "effect_attempted",
        "execution_authorized",
        "filesystem_mutation_attempted",
        "final_applier_invoked",
        "generated_code_execution_authorized",
        "generated_code_execution_implemented",
        "production_magic_star_release_available",
        "production_ready",
        "release_authorized",
        "repository_mutation_authorized",
        "repository_mutation_implemented",
        "subprocess_test_execution_implemented",
        "test_commands_executed",
    }
)


def _evidence_digest(value: Mapping[str, Any]) -> str:
    try:
        encoded = json.dumps(
            dict(value),
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError):
        return ""
    return hashlib.sha256(encoded).hexdigest()


def _effect_flags_are_false(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key in _FALSE_EFFECT_FIELDS and item is not False:
                return False
            if not _effect_flags_are_false(item):
                return False
        return True
    if isinstance(value, (list, tuple)):
        return all(_effect_flags_are_false(item) for item in value)
    return True


def _held_result(reason_code: str, *, status: str = "internal_self_coder_held") -> dict[str, Any]:
    summary: dict[str, Any] = {
        "reason_code": reason_code,
        "applied": False,
        "pending_senior_review": False,
        "release_ready": False,
        "codex_implementation": False,
        "action_eligible": False,
        "economic_eligible": False,
    }
    assert set(summary) == COMPACT_SELF_CODER_SUMMARY_FIELDS
    return {
        "status": status,
        "ok": False,
        "summary": summary,
        "output_files": [],
    }


def _compact_result(result: Mapping[str, Any]) -> dict[str, Any]:
    """Return a generic HOLD for self-consistent but unattested local JSON.

    No caller-supplied or locally recomputed JSON receipt can create review
    authority or prove that a transient HNC seal existed. It never returns
    ``ok=True`` or infers a proposal-specific denial reason from the receipt.
    """

    if not isinstance(result, Mapping):
        return _held_result("internal_self_coder_receipt_invalid")
    digest = result.get("evidence_digest")
    digest_core = {key: value for key, value in result.items() if key != "evidence_digest"}
    if (
        not isinstance(digest, str)
        or _HEX_64.fullmatch(digest) is None
        or digest != _evidence_digest(digest_core)
        or not _effect_flags_are_false(result)
    ):
        return _held_result("internal_self_coder_receipt_invalid")
    return _held_result(
        "internal_self_coder_receipt_unattested",
        status="internal_self_coder_evidence_hold",
    )


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
    """Run one Aureon-owned seal experiment; evidence blocks another cycle."""

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
        compact = _compact_result(prior)
        if compact["status"] == "internal_self_coder_evidence_hold":
            compact["status"] = "internal_self_coder_existing_evidence_hold"
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
        read_self_coding_evidence(root=repo_root)
    except InternalSelfCoderHold:
        return True
    return True


__all__ = [
    "COMPACT_SELF_CODER_SUMMARY_FIELDS",
    "run_self_coding_task",
    "self_coding_patch_lane_blocked",
]
