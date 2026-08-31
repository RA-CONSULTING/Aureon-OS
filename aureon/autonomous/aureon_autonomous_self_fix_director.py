"""Proposal-only self-fix planning and containment evidence.

This module may inspect and publish patch proposals, but it never applies a
patch, executes generated code, or runs proposal-supplied validation commands.
The production Magic Star release boundary is not implemented in this
checkout, so every proposal remains on release HOLD.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

from aureon.autonomous.aureon_capability_forge import REPO_ROOT
from aureon.operator.coherence_gate import compute_evolution_flow

DEFAULT_STATE_PATH = Path("state/aureon_autonomous_self_fix_director_last_run.json")
DEFAULT_AUDIT_JSON = Path("docs/audits/aureon_autonomous_self_fix_director.json")
DEFAULT_AUDIT_MD = Path("docs/audits/aureon_autonomous_self_fix_director.md")
DEFAULT_PUBLIC_JSON = Path("frontend/public/aureon_autonomous_self_fix_director.json")

DEFAULT_EVIDENCE_PATHS = [
    Path("state/aureon_coding_organism_last_run.json"),
    Path("state/aureon_capability_forge_last_run.json"),
    Path("state/aureon_complex_build_stress_audit_last_run.json"),
    Path("state/aureon_coding_capability_unblocker_last_run.json"),
    Path("state/aureon_agent_creative_process_guardian_last_run.json"),
    Path("frontend/public/aureon_coding_organism_bridge.json"),
    Path("frontend/public/aureon_capability_forge.json"),
    Path("frontend/public/aureon_complex_build_stress_audit.json"),
    Path("frontend/public/aureon_coding_capability_unblocker.json"),
]

DEFAULT_PROPOSAL_STATE_PATHS = [
    Path("state/safe_code_control_state.json"),
    Path("state/aureon_capability_forge_safe_code_state.json"),
]

DEFAULT_PATCH_ALLOWLIST = [
    "aureon/autonomous/aureon_autonomous_self_fix_director.py",
    "aureon/autonomous/aureon_capability_forge.py",
    "aureon/autonomous/aureon_coding_organism_bridge.py",
    "aureon/autonomous/aureon_complex_build_stress_audit.py",
    "aureon/autonomous/aureon_safe_code_control.py",
    "frontend/src/components/generated/AureonCodingOrganismConsole.tsx",
    "frontend/tests/capability-forge.spec.ts",
    "tests/test_aureon_autonomous_self_fix_director.py",
    "tests/test_aureon_capability_forge.py",
    "tests/test_aureon_coding_organism_bridge.py",
    "tests/test_aureon_complex_build_stress_audit.py",
    "tests/test_safe_code_control.py",
]

MANUAL_AUTHORITY_NEEDLES = (
    "live trade",
    "place order",
    "order mutation",
    "credential reveal",
    "api secret",
    "saved credentials",
    "send payment",
    "top up",
    "official filing",
    "hmrc submit",
    "companies house submit",
    "delete the repo",
    "wipe",
    "format disk",
    "destructive os",
)

BLOCKED_PATH_NEEDLES = (
    ".env",
    "credential",
    "credentials",
    "secret",
    "secrets",
    "private_key",
    "live_order",
    "order_router",
    "payment",
    "filing",
    "hmrc",
    "companies_house",
)

SECRET_CONTENT_PATTERNS = (
    re.compile(r"BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY", re.I),
    re.compile(r"\bsk_live_[A-Za-z0-9]{12,}", re.I),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"(?i)(api[_-]?secret|password|private[_-]?key)\s*=\s*['\"][^'\"]{6,}"),
)


def _default_root() -> Path:
    return Path.cwd().resolve() if (Path.cwd() / "aureon").exists() else REPO_ROOT


def _rooted(root: Path, rel_path: Path) -> Path:
    return rel_path if rel_path.is_absolute() else root / rel_path


def _bounded_output_path(root: Path, rel_path: Path) -> Path:
    """Resolve a fixed report path without following storage outside the repo."""

    if rel_path.is_absolute():
        raise ValueError("self_fix_output_path_must_be_repo_relative")
    repo_root = root.resolve()
    candidate = repo_root / rel_path
    try:
        candidate.resolve().relative_to(repo_root)
    except ValueError as exc:
        raise ValueError("self_fix_output_path_escaped_repository") from exc
    return candidate


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_text(path: Path, content: str) -> Dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return {"path": str(path), "ok": path.exists(), "bytes": path.stat().st_size if path.exists() else 0}


def _write_json(path: Path, payload: Dict[str, Any]) -> Dict[str, Any]:
    return _write_text(path, json.dumps(payload, indent=2, sort_keys=True, default=str))


def _normalize_rel_path(value: str) -> str:
    raw = str(value or "").strip().replace("\\", "/")
    raw = re.sub(r"^[ab]/", "", raw)
    raw = raw.lstrip("/")
    return raw


def _path_blocked(path: str) -> bool:
    lower = _normalize_rel_path(path).lower()
    return any(needle in lower for needle in BLOCKED_PATH_NEEDLES)


def _contains_manual_authority(text: str) -> bool:
    lower = str(text or "").lower()
    return any(needle in lower for needle in MANUAL_AUTHORITY_NEEDLES)


def _extract_patch_target_files(patch_text: str) -> List[str]:
    targets: List[str] = []
    for line in str(patch_text or "").splitlines():
        if line.startswith("+++ ") or line.startswith("--- "):
            raw = line[4:].strip().split("\t", 1)[0]
            if raw == "/dev/null":
                continue
            rel = _normalize_rel_path(raw)
            if rel and rel not in targets:
                targets.append(rel)
    return targets


def _scan_patch_for_secrets(patch_text: str) -> List[str]:
    findings: List[str] = []
    added_lines = "\n".join(
        line[1:]
        for line in str(patch_text or "").splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    for pattern in SECRET_CONTENT_PATTERNS:
        if pattern.search(added_lines):
            findings.append(pattern.pattern)
    return findings


def _resolve_evolution_flow(
    coherence_inputs: Dict[str, Any] | None = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Read the fresh shared field and derive a non-closing repair rhythm."""
    inputs = dict(coherence_inputs or {})
    if coherence_inputs is None:
        try:
            from aureon.autonomous.aureon_unified_self_evolution_loop import (
                read_evolution_field_inputs,
            )

            inputs = read_evolution_field_inputs()
        except Exception as exc:
            inputs = {
                "gamma": None,
                "advisory_open": None,
                "lighthouse_severity": None,
                "auris_confidence": None,
                "beta": None,
                "sources": {
                    "status": "no_data",
                    "reason": f"{type(exc).__name__}: {exc}",
                },
            }
    flow = compute_evolution_flow(
        inputs.get("gamma"),
        inputs.get("advisory_open"),
        inputs.get("lighthouse_severity"),
        auris_confidence=inputs.get("auris_confidence"),
        beta=inputs.get("beta"),
    )
    capabilities = dict(flow.get("capabilities") or {})
    capabilities.update(
        {
            "apply_patch": False,
            "execute_generated_code": False,
            "execute_test_commands": False,
            "rollback": False,
        }
    )
    flow = {
        **flow,
        "capabilities": capabilities,
        "proposal_only": True,
        "production_magic_star_release_available": False,
    }
    return inputs, flow


def _proposal_id(proposal: Dict[str, Any], index: int) -> str:
    return str(proposal.get("id") or proposal.get("title") or proposal.get("kind") or f"proposal_{index}")


def _load_proposals(root: Path, state_paths: Sequence[Path]) -> List[Dict[str, Any]]:
    proposals: List[Dict[str, Any]] = []
    for rel_path in state_paths:
        path = _rooted(root, rel_path)
        payload = _read_json(path)
        if not payload:
            continue
        for key in ("pending_proposals", "recent_reviews"):
            for item in payload.get(key, []) if isinstance(payload.get(key), list) else []:
                # An explicit review approval makes a record eligible for
                # proposal preflight only.  It never grants execution authority.
                if isinstance(item, dict) and str(item.get("status") or "").casefold() == "approved":
                    proposals.append({**item, "_proposal_state_path": str(path), "_proposal_state_bucket": key})
    return proposals


@dataclass
class ProposalPreflight:
    """Validate proposal metadata without attempting any repository effect."""

    root: Path
    allowlist: Sequence[str] = field(default_factory=lambda: list(DEFAULT_PATCH_ALLOWLIST))
    test_commands: Sequence[Sequence[str]] = field(default_factory=list)
    timeout_sec: int = 120
    required_test_layers: Sequence[str] = field(default_factory=lambda: ["focused", "integration", "regression"])
    review_cycles: int = 1

    def inspect_proposal(self, proposal: Dict[str, Any], *, index: int = 0) -> Dict[str, Any]:
        patch_text = str(proposal.get("patch_text") or "")
        target_files = [
            _normalize_rel_path(item)
            for item in list(proposal.get("target_files") or []) + _extract_patch_target_files(patch_text)
            if str(item or "").strip()
        ]
        target_files = list(dict.fromkeys(target_files))
        evidence: Dict[str, Any] = {
            "proposal_id": _proposal_id(proposal, index),
            "source": proposal.get("source", "SafeCodeControl"),
            "status": "blocked_proposal",
            "applied": False,
            "ever_applied": False,
            "effect_attempted": False,
            "test_commands_executed": False,
            "repository_mutation_authorized": False,
            "generated_code_execution_authorized": False,
            "repository_mutation_implemented": False,
            "generated_code_execution_implemented": False,
            "subprocess_test_execution_implemented": False,
            "release_authorized": False,
            "proposal_only": True,
            "local_development_only": True,
            "production_ready": False,
            "target_files": target_files,
            "allowlist": list(self.allowlist),
            "coherence_proof": {
                "required_test_layers": list(self.required_test_layers),
                "review_cycles": max(1, int(self.review_cycles)),
            },
            "checks": [],
            "test_results": [],
        }

        def add_check(check_id: str, ok: bool, detail: str) -> None:
            evidence["checks"].append({"id": check_id, "ok": bool(ok), "detail": detail})

        proposal_status = str(proposal.get("status") or "").strip().casefold()
        explicitly_approved = proposal_status == "approved"
        add_check(
            "proposal_explicitly_approved",
            explicitly_approved,
            f"status={proposal_status or 'missing'}",
        )
        if not explicitly_approved:
            evidence["blocked_reason"] = "proposal_not_explicitly_approved"
            return evidence

        if not patch_text.strip():
            add_check("patch_text_present", False, "proposal has no unified diff")
            evidence["blocked_reason"] = "empty_patch_text"
            return evidence
        add_check("patch_text_present", True, "patch text provided")

        looks_unified = "--- " in patch_text and "+++ " in patch_text and "@@" in patch_text
        add_check("unified_diff_shape", looks_unified, "requires ---/+++/@@ unified diff markers")
        if not looks_unified:
            evidence["blocked_reason"] = "not_unified_diff"
            return evidence

        if not target_files:
            add_check("target_files_present", False, "no target files found in proposal or patch")
            evidence["blocked_reason"] = "no_target_files"
            return evidence
        add_check("target_files_present", True, ", ".join(target_files))

        allow = {_normalize_rel_path(item) for item in self.allowlist}
        allowlist_ok = all(path in allow for path in target_files)
        blocked_paths = [path for path in target_files if path not in allow or _path_blocked(path)]
        add_check("target_files_allowlisted", allowlist_ok and not blocked_paths, ", ".join(blocked_paths) or "all target files allowlisted")
        if not allowlist_ok or blocked_paths:
            evidence["blocked_reason"] = "target_file_not_allowlisted_or_authority_blocked"
            return evidence

        secret_findings = _scan_patch_for_secrets(patch_text)
        add_check("secret_scan_clean", not secret_findings, ", ".join(secret_findings) or "no secret-like additions")
        if secret_findings:
            evidence["blocked_reason"] = "secret_scan_failed"
            return evidence

        validation_ready = bool(self.test_commands)
        add_check(
            "suggested_validation_commands_present",
            validation_ready,
            f"{len(self.test_commands)} suggested validation command(s); none executed",
        )
        if not validation_ready:
            evidence["blocked_reason"] = "validation_commands_missing"
            return evidence

        proof_depth_valid = bool(self.required_test_layers) and int(self.review_cycles) >= 1
        add_check(
            "coherence_proof_depth",
            proof_depth_valid,
            (
                f"layers={','.join(self.required_test_layers)}; "
                f"review_cycles={max(1, int(self.review_cycles))}"
            ),
        )
        if not proof_depth_valid:
            evidence["blocked_reason"] = "coherence_proof_depth_invalid"
            return evidence

        add_check(
            "production_magic_star_release_available",
            False,
            "checked-in Plumber and Magic Star are local-development controls",
        )
        evidence.update(
            {
                "status": "held_proposal_only",
                "applied": False,
                "ever_applied": False,
                "effect_attempted": False,
                "test_commands_executed": False,
                "blocked_reason": "production_magic_star_release_unavailable",
                "repository_mutation_authorized": False,
                "generated_code_execution_authorized": False,
                "release_authorized": False,
                "proposal_only": True,
                "local_development_only": True,
                "production_ready": False,
            }
        )
        return evidence

    def apply_proposal(self, proposal: Dict[str, Any], *, index: int = 0) -> Dict[str, Any]:
        """Compatibility shim: perform proposal preflight, never patch application."""

        return self.inspect_proposal(proposal, index=index)


# Compatibility for callers that imported the historical name.  The alias has
# proposal-preflight semantics only; no apply implementation exists here.
GuardedPatchApplier = ProposalPreflight


def _load_evidence(root: Path, paths: Sequence[Path] = DEFAULT_EVIDENCE_PATHS) -> Dict[str, Dict[str, Any]]:
    evidence: Dict[str, Dict[str, Any]] = {}
    for rel_path in paths:
        payload = _read_json(_rooted(root, rel_path))
        if payload:
            evidence[rel_path.as_posix()] = payload
    return evidence


def _any_status(evidence: Dict[str, Dict[str, Any]], needle: str) -> bool:
    lower = needle.lower()
    return any(lower in json.dumps(payload, default=str).lower() for payload in evidence.values())


def build_swot(evidence: Dict[str, Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    has_forge = _any_status(evidence, "aureon-local-capability-forge-v1")
    has_complex = _any_status(evidence, "aureon-complex-build-stress-audit-v1")
    has_unblocker = _any_status(evidence, "aureon-coding-capability-unblocker-v1")
    has_quality = _any_status(evidence, "artifact_quality_report")
    has_unique = _any_status(evidence, "fresh_project_per_request")
    has_fake_pass = _any_status(evidence, "fake_pass_detected\": true") or _any_status(evidence, "fake_pass_count\": 1")
    has_repairs = _any_status(evidence, "repair_attempts")
    return {
        "strengths": [
            {"id": "capability_forge", "text": "Capability forge exists and can create local artifacts.", "present": has_forge},
            {"id": "complex_stress", "text": "Complex build stress certification exists.", "present": has_complex},
            {"id": "coding_unblocker", "text": "Coding unblocker maps coding blockers into autonomous gates.", "present": has_unblocker},
            {"id": "quality_gate", "text": "Artifact quality gate and public evidence are wired.", "present": has_quality},
            {"id": "unique_artifacts", "text": "Generated build IDs prevent stale artifact reuse.", "present": has_unique},
        ],
        "weaknesses": [
            {"id": "proposal_only_apply", "text": "SafeCodeControl records proposals, but no production Magic Star release service exists.", "present": True},
            {"id": "stress_repair_depth", "text": "Stress repairs must create proposal work orders without self-authorizing effects.", "present": has_repairs},
            {"id": "repo_integration_depth", "text": "Generated artifacts can pass while live repo integration remains shallow.", "present": True},
        ],
        "opportunities": [
            {"id": "guarded_patch_apply", "text": "Build an independently reviewed production release service outside the self-coder trust boundary.", "present": True},
            {"id": "self_fix_backlog", "text": "Convert failed stress cases into repair jobs Aureon owns.", "present": True},
            {"id": "source_packets", "text": "Use local/GitHub/docs research as source packets before coding.", "present": has_unblocker},
        ],
        "threats": [
            {"id": "authority_leakage", "text": "Live trading, payments, filings, secrets, and destructive OS actions must stay blocked.", "present": True},
            {"id": "fake_passes", "text": "Fake passes must block handover.", "present": has_fake_pass},
            {"id": "license_or_copy_risk", "text": "Open-source references need license notes and must not be copied blindly.", "present": True},
            {"id": "stale_evidence", "text": "Stale public evidence can make the cockpit look healthier than it is.", "present": True},
        ],
    }


def _repair_backlog_from_swot(swot: Dict[str, List[Dict[str, Any]]], evidence: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    complex_payload = next(
        (payload for path, payload in evidence.items() if "complex_build_stress" in path or payload.get("schema_version") == "aureon-complex-build-stress-audit-v1"),
        {},
    )
    failed_cases = [
        item
        for item in complex_payload.get("cases", [])
        if isinstance(item, dict) and (not item.get("ok") or item.get("fake_pass_detected"))
    ]
    backlog = [
        {
            "id": "production_magic_star_release_service",
            "priority": "P0",
            "title": "Design the production Magic Star proposal release service",
            "source": "SWOT weakness proposal_only_apply",
            "acceptance": "Independent custody, review, sandbox, transaction, rollback, and durable receipts are externally verified before any mutation.",
        },
        {
            "id": "stress_repair_work_orders",
            "priority": "P0",
            "title": "Make complex stress failures become self-fix work orders",
            "source": "SWOT weakness stress_repair_depth",
            "acceptance": "Every failed/fake-pass case records a repair work order or a precise no-safe-patch blocker.",
        },
        {
            "id": "cockpit_self_fix_panel",
            "priority": "P1",
            "title": "Show Aureon Self-Fix SWOT in the coding cockpit",
            "source": "operator visibility",
            "acceptance": "Human sees SWOT, selected repairs, patch evidence, tests, snags, and Codex audit state.",
        },
    ]
    for case in failed_cases:
        backlog.append(
            {
                "id": f"repair_case_{case.get('id', 'unknown')}",
                "priority": "P0",
                "title": f"Repair failed stress case: {case.get('id', 'unknown')}",
                "source": "complex_build_stress_audit",
                "acceptance": "Aureon emits a bounded proposal or publishes the exact blocker without mutation.",
                "failure_reason": case.get("failure_reason", ""),
            }
        )
    return backlog


def _manual_authority_snags(operator_prompt: str) -> List[Dict[str, Any]]:
    if not _contains_manual_authority(operator_prompt):
        return []
    return [
        {
            "id": "manual_authority_request_held",
            "title": "Manual authority request remains human-held",
            "blocking": True,
            "source": "operator_prompt",
            "next_action": "Ask for a safe local-only coding or evidence task instead.",
        }
    ]


def _test_summary(patch_evidence: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    test_results = [result for item in patch_evidence for result in item.get("test_results", [])]
    return {
        "status": "tests_passed" if test_results and all(item.get("ok") for item in test_results) else "tests_not_run_or_attention",
        "command_count": len(test_results),
        "ok": bool(test_results) and all(item.get("ok") for item in test_results),
        "results": test_results,
    }


def _make_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Aureon Autonomous Self-Fix Director",
        "",
        f"- status: {report.get('status')}",
        f"- production_handover_ready: {report.get('handover_ready')}",
        f"- release_hold: {report.get('release_hold')}",
        f"- codex_audit_state: {(report.get('codex_audit_state') or {}).get('state')}",
        f"- coherence_flow: {(report.get('coherence_flow') or {}).get('flow')}",
        f"- coherence_field_status: {(report.get('coherence_flow') or {}).get('field_status')}",
        f"- patch_batch_limit: {(report.get('summary') or {}).get('patch_batch_limit')}",
        f"- required_test_layers: {', '.join((report.get('coherence_flow') or {}).get('required_test_layers') or [])}",
        f"- minimum_review_cycles: {(report.get('coherence_flow') or {}).get('minimum_review_cycles')}",
        f"- repairs selected: {len(report.get('selected_repairs') or [])}",
        "- patches applied: 0 (proposal-only boundary)",
        f"- snags: {len(report.get('snags') or [])}",
        "",
        "## SWOT",
    ]
    swot = report.get("swot", {})
    for key in ("strengths", "weaknesses", "opportunities", "threats"):
        lines.append(f"### {key.title()}")
        for item in swot.get(key, []):
            lines.append(f"- {item.get('id')}: {item.get('text')} present={item.get('present')}")
    lines.extend(["", "## Repair Backlog"])
    for item in report.get("repair_backlog", []):
        lines.append(f"- {item.get('priority')} {item.get('id')}: {item.get('title')}")
    return "\n".join(lines) + "\n"


def build_and_write_autonomous_self_fix_director(
    *,
    root: Path | None = None,
    operator_prompt: str = "",
    apply_safe_fixes: bool = False,
    test_commands: Sequence[Sequence[str]] | None = None,
    codex_audit_state: str = "pending",
    proposal_state_paths: Sequence[Path] = DEFAULT_PROPOSAL_STATE_PATHS,
    patch_allowlist: Sequence[str] = DEFAULT_PATCH_ALLOWLIST,
    max_patch_proposals: int | None = None,
    coherence_inputs: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    root = Path(root or _default_root()).resolve()
    field_inputs, coherence_flow = _resolve_evolution_flow(coherence_inputs)
    flow_batch_limit = max(1, int(coherence_flow.get("patch_batch_limit") or 1))
    patch_batch_limit = (
        flow_batch_limit
        if max_patch_proposals is None
        else min(flow_batch_limit, max(0, int(max_patch_proposals)))
    )
    evidence = _load_evidence(root)
    swot = build_swot(evidence)
    repair_backlog = _repair_backlog_from_swot(swot, evidence)
    selected_repairs = repair_backlog[:patch_batch_limit]
    proposals = _load_proposals(root, proposal_state_paths)
    patch_candidates = [
        item
        for item in proposals
        if str(item.get("patch_text") or "").strip()
    ][:patch_batch_limit]
    proposal_preflight_evidence: List[Dict[str, Any]] = []
    if apply_safe_fixes and patch_candidates:
        preflight = ProposalPreflight(
            root=root,
            allowlist=patch_allowlist,
            test_commands=list(test_commands or []),
            required_test_layers=list(coherence_flow.get("required_test_layers") or []),
            review_cycles=max(1, int(coherence_flow.get("minimum_review_cycles") or 1)),
        )
        for index, proposal in enumerate(patch_candidates, start=1):
            proposal_preflight_evidence.append(preflight.inspect_proposal(proposal, index=index))
    elif patch_candidates:
        proposal_preflight_evidence = [
            {
                "proposal_id": _proposal_id(item, index),
                "status": "held_proposal_only",
                "applied": False,
                "ever_applied": False,
                "effect_attempted": False,
                "test_commands_executed": False,
                "repository_mutation_authorized": False,
                "generated_code_execution_authorized": False,
                "release_authorized": False,
                "proposal_only": True,
                "local_development_only": True,
                "production_ready": False,
                "blocked_reason": "proposal_preflight_disabled",
                "target_files": item.get("target_files", []),
            }
            for index, item in enumerate(patch_candidates, start=1)
        ]

    test_evidence = _test_summary(proposal_preflight_evidence)
    snags = _manual_authority_snags(operator_prompt)
    snags.extend(
        {
            "id": f"patch_{item.get('proposal_id')}_blocked",
            "title": f"Patch proposal {item.get('proposal_id')} remains on release HOLD",
            "blocking": True,
            "source": "proposal_only_release_boundary",
            "next_action": item.get("blocked_reason", "inspect patch evidence"),
        }
        for item in proposal_preflight_evidence
    )
    snags.append(
        {
            "id": "production_magic_star_release_unavailable",
            "title": "Production Magic Star release remains unavailable",
            "blocking": True,
            "source": "proposal_only_release_boundary",
            "next_action": "Keep every proposal on HOLD pending an independently reviewed production release service.",
        }
    )
    codex_audit = {
        "state": codex_audit_state,
        "allowed_states": ["autonomous_safe", "pending", "passed", "failed"],
        "reviewer": "Codex/user",
        "policy": "Codex/user audit is advisory and cannot authorize repository mutation or generated-code execution.",
        "autonomous_safe_local": False,
        "blocking_states": ["failed"],
    }
    audit_gate_ok = codex_audit_state != "failed"
    handover_ready = False
    status = "self_fix_failed_audit" if not audit_gate_ok else "self_fix_proposal_only_release_hold"
    report: Dict[str, Any] = {
        "schema_version": "aureon-autonomous-self-fix-director-v1",
        "status": status,
        "ok": False,
        "proposal_cycle_completed": True,
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
        "production_ready": False,
        "generated_at": _utc_now(),
        "operator_prompt": operator_prompt,
        "coherence_inputs": field_inputs,
        "coherence_flow": coherence_flow,
        "swot": swot,
        "repair_backlog": repair_backlog,
        "selected_repairs": selected_repairs,
        "proposal_policy": {
            "repair_authority": "proposal_only_no_repository_mutation",
            "repair_rhythm": "HNC/Auris coherence changes proposal batch size and review depth without granting release authority",
            "audit_policy": "codex_user_audit_is_advisory_and_cannot_release_code",
            "diff_source": "SafeCodeControl/QueenCodeBridge unified diffs only",
            "allowlist": list(patch_allowlist),
            "blocked_authority": ["live_trading", "payments", "filings", "credential_reveal", "destructive_os_actions"],
            "requires": [
                "unified_diff",
                "target_allowlist",
                "secret_scan",
                "validation_commands",
                "coherence_required_test_layers",
                "coherence_review_cycles",
                "independent_production_magic_star_release",
                "sandboxed_validation",
                "transactional_apply_and_rollback",
                "durable_provider_readback",
            ],
            "production_magic_star_release_available": False,
            "repository_mutation_implemented": False,
            "generated_code_execution_implemented": False,
            "subprocess_test_execution_implemented": False,
        },
        "proposal_preflight_evidence": proposal_preflight_evidence,
        # Read-only compatibility field for the existing cockpit.  Every item
        # is explicitly non-applied and release-held.
        "patch_apply_evidence": proposal_preflight_evidence,
        "test_evidence": test_evidence,
        "snags": snags,
        "codex_audit_state": codex_audit,
        "handover_ready": handover_ready,
        "summary": {
            "evidence_file_count": len(evidence),
            "repair_backlog_count": len(repair_backlog),
            "selected_repair_count": len(selected_repairs),
            "coherence_flow": coherence_flow.get("flow"),
            "coherence_field_status": coherence_flow.get("field_status"),
            "patch_batch_limit": patch_batch_limit,
            "required_test_layers": list(coherence_flow.get("required_test_layers") or []),
            "minimum_review_cycles": coherence_flow.get("minimum_review_cycles"),
            "patch_candidate_count": len(patch_candidates),
            "patch_applied_count": 0,
            "blocking_snag_count": sum(1 for item in snags if item.get("blocking")),
            "codex_audit_state": codex_audit_state,
            "audit_gate_ok": audit_gate_ok,
        },
        "output_files": [
            DEFAULT_STATE_PATH.as_posix(),
            DEFAULT_AUDIT_JSON.as_posix(),
            DEFAULT_AUDIT_MD.as_posix(),
            DEFAULT_PUBLIC_JSON.as_posix(),
        ],
    }
    writes = [
        _write_json(_bounded_output_path(root, DEFAULT_STATE_PATH), report),
        _write_json(_bounded_output_path(root, DEFAULT_AUDIT_JSON), report),
        _write_text(_bounded_output_path(root, DEFAULT_AUDIT_MD), _make_markdown(report)),
        _write_json(_bounded_output_path(root, DEFAULT_PUBLIC_JSON), report),
    ]
    report["write_info"] = {"evidence_writes": writes}
    for rel_path in (DEFAULT_STATE_PATH, DEFAULT_AUDIT_JSON, DEFAULT_PUBLIC_JSON):
        _write_json(_bounded_output_path(root, rel_path), report)
    _write_text(_bounded_output_path(root, DEFAULT_AUDIT_MD), _make_markdown(report))
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Aureon's autonomous self-fix SWOT and audit director.")
    parser.add_argument("--root", default="", help="Repository root. Defaults to current Aureon repo.")
    parser.add_argument("--prompt", default="", help="Optional operator prompt to check for authority holds.")
    parser.add_argument("--json", action="store_true", help="Print full JSON report.")
    parser.add_argument("--no-apply", action="store_true", help="Skip legacy proposal preflight; mutation is always disabled.")
    parser.add_argument(
        "--codex-audit-state",
        default="pending",
        choices=["autonomous_safe", "pending", "passed", "failed"],
        help="Advisory audit state; it never authorizes code mutation.",
    )
    parser.add_argument(
        "--test-command",
        action="append",
        default=[],
        help="Suggested validation command to record for a future release service; never executed here.",
    )
    args = parser.parse_args(argv)
    root = Path(args.root).resolve() if args.root else None
    commands: List[List[str]] = []
    for command in args.test_command:
        commands.append(command.split())
    report = build_and_write_autonomous_self_fix_director(
        root=root,
        operator_prompt=args.prompt,
        apply_safe_fixes=not args.no_apply,
        test_commands=commands,
        codex_audit_state=args.codex_audit_state,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True, default=str))
    else:
        summary = report.get("summary", {})
        print(
            f"{report.get('status')}: repairs={summary.get('selected_repair_count')} "
            f"patches={summary.get('patch_applied_count')} snags={summary.get('blocking_snag_count')} "
            f"codex_audit={summary.get('codex_audit_state')}"
        )
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
