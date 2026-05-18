from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from aureon.autonomous.aureon_capability_forge import REPO_ROOT


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


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
                if isinstance(item, dict):
                    proposals.append({**item, "_proposal_state_path": str(path), "_proposal_state_bucket": key})
    return proposals


@dataclass
class GuardedPatchApplier:
    root: Path
    allowlist: Sequence[str] = field(default_factory=lambda: list(DEFAULT_PATCH_ALLOWLIST))
    test_commands: Sequence[Sequence[str]] = field(default_factory=list)
    timeout_sec: int = 120

    def apply_proposal(self, proposal: Dict[str, Any], *, index: int = 0) -> Dict[str, Any]:
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
            "status": "blocked",
            "applied": False,
            "target_files": target_files,
            "allowlist": list(self.allowlist),
            "checks": [],
            "test_results": [],
        }

        def add_check(check_id: str, ok: bool, detail: str) -> None:
            evidence["checks"].append({"id": check_id, "ok": bool(ok), "detail": detail})

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

        check = self._run_git_apply(patch_text, check_only=True)
        evidence["git_apply_check"] = check
        add_check("git_apply_check", bool(check.get("ok")), check.get("stderr") or check.get("stdout") or "git apply --check passed")
        if not check.get("ok"):
            evidence["blocked_reason"] = "git_apply_check_failed"
            return evidence

        apply = self._run_git_apply(patch_text, check_only=False)
        evidence["git_apply"] = apply
        add_check("git_apply", bool(apply.get("ok")), apply.get("stderr") or apply.get("stdout") or "patch applied")
        if not apply.get("ok"):
            evidence["blocked_reason"] = "git_apply_failed"
            return evidence

        tests = self._run_tests()
        evidence["test_results"] = tests
        tests_ok = bool(tests) and all(item.get("ok") for item in tests)
        add_check("tests_ran_and_passed", tests_ok, f"{len(tests)} command(s)")
        if not tests_ok:
            evidence["status"] = "applied_tests_failed"
            evidence["applied"] = True
            evidence["blocked_reason"] = "tests_failed_or_missing"
            return evidence

        evidence["status"] = "applied"
        evidence["applied"] = True
        evidence["blocked_reason"] = ""
        return evidence

    def _run_git_apply(self, patch_text: str, *, check_only: bool) -> Dict[str, Any]:
        command = ["git", "apply", "--whitespace=nowarn"]
        if check_only:
            command.append("--check")
        try:
            proc = subprocess.run(
                command,
                cwd=self.root,
                input=patch_text,
                text=True,
                capture_output=True,
                timeout=self.timeout_sec,
            )
            return {
                "ok": proc.returncode == 0,
                "command": " ".join(command),
                "returncode": proc.returncode,
                "stdout": proc.stdout[-2000:],
                "stderr": proc.stderr[-2000:],
            }
        except Exception as exc:
            return {"ok": False, "command": " ".join(command), "error": f"{type(exc).__name__}: {exc}"}

    def _run_tests(self) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for command in self.test_commands:
            try:
                proc = subprocess.run(
                    list(command),
                    cwd=self.root,
                    text=True,
                    capture_output=True,
                    timeout=self.timeout_sec,
                )
                results.append(
                    {
                        "ok": proc.returncode == 0,
                        "command": list(command),
                        "returncode": proc.returncode,
                        "stdout": proc.stdout[-2000:],
                        "stderr": proc.stderr[-2000:],
                    }
                )
            except Exception as exc:
                results.append({"ok": False, "command": list(command), "error": f"{type(exc).__name__}: {exc}"})
        return results


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
            {"id": "proposal_only_apply", "text": "SafeCodeControl records proposals but needs a guarded patch applier.", "present": True},
            {"id": "stress_repair_depth", "text": "Stress repairs must create work orders and apply safe fixes, not only rerun proof.", "present": has_repairs},
            {"id": "repo_integration_depth", "text": "Generated artifacts can pass while live repo integration remains shallow.", "present": True},
        ],
        "opportunities": [
            {"id": "guarded_patch_apply", "text": "Use allowlisted diffs with git apply checks and tests.", "present": True},
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
            "id": "guarded_patch_applier",
            "priority": "P0",
            "title": "Add guarded repo patch applier",
            "source": "SWOT weakness proposal_only_apply",
            "acceptance": "Allowlisted unified diffs pass git apply --check, secret scan, apply, and tests before handover.",
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
                "acceptance": "Aureon applies a safe local fix or publishes the exact blocker.",
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
        f"- handover_ready: {report.get('handover_ready')}",
        f"- codex_audit_state: {(report.get('codex_audit_state') or {}).get('state')}",
        f"- repairs selected: {len(report.get('selected_repairs') or [])}",
        f"- patches applied: {sum(1 for item in report.get('patch_apply_evidence', []) if item.get('applied'))}",
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
    root: Optional[Path] = None,
    operator_prompt: str = "",
    apply_safe_fixes: bool = True,
    test_commands: Optional[Sequence[Sequence[str]]] = None,
    codex_audit_state: str = "autonomous_safe",
    proposal_state_paths: Sequence[Path] = DEFAULT_PROPOSAL_STATE_PATHS,
    patch_allowlist: Sequence[str] = DEFAULT_PATCH_ALLOWLIST,
    max_patch_proposals: int = 3,
) -> Dict[str, Any]:
    root = Path(root or _default_root()).resolve()
    evidence = _load_evidence(root)
    swot = build_swot(evidence)
    repair_backlog = _repair_backlog_from_swot(swot, evidence)
    selected_repairs = repair_backlog[:3]
    proposals = _load_proposals(root, proposal_state_paths)
    patch_candidates = [
        item
        for item in proposals
        if str(item.get("patch_text") or "").strip()
    ][:max_patch_proposals]
    patch_apply_evidence: List[Dict[str, Any]] = []
    if apply_safe_fixes and patch_candidates:
        applier = GuardedPatchApplier(
            root=root,
            allowlist=patch_allowlist,
            test_commands=list(test_commands or []),
        )
        for index, proposal in enumerate(patch_candidates, start=1):
            patch_apply_evidence.append(applier.apply_proposal(proposal, index=index))
    elif patch_candidates:
        patch_apply_evidence = [
            {
                "proposal_id": _proposal_id(item, index),
                "status": "skipped",
                "applied": False,
                "blocked_reason": "apply_safe_fixes_disabled",
                "target_files": item.get("target_files", []),
            }
            for index, item in enumerate(patch_candidates, start=1)
        ]

    test_evidence = _test_summary(patch_apply_evidence)
    snags = _manual_authority_snags(operator_prompt)
    snags.extend(
        {
            "id": f"patch_{item.get('proposal_id')}_blocked",
            "title": f"Patch proposal {item.get('proposal_id')} did not safely apply",
            "blocking": True,
            "source": "guarded_patch_applier",
            "next_action": item.get("blocked_reason", "inspect patch evidence"),
        }
        for item in patch_apply_evidence
        if not item.get("applied") or item.get("status") == "applied_tests_failed"
    )
    codex_audit = {
        "state": codex_audit_state,
        "allowed_states": ["autonomous_safe", "pending", "passed", "failed"],
        "reviewer": "Codex/user",
        "policy": "Safe local fixes run autonomously; Codex/user audit is recorded after the fact and only a failed audit blocks handover.",
        "autonomous_safe_local": True,
        "blocking_states": ["failed"],
    }
    no_blocking_snags = not any(item.get("blocking") for item in snags)
    patch_requirement_ok = not patch_candidates or any(item.get("applied") and item.get("status") == "applied" for item in patch_apply_evidence)
    audit_gate_ok = codex_audit_state != "failed"
    handover_ready = no_blocking_snags and patch_requirement_ok and audit_gate_ok
    status = (
        "self_fix_autonomous_safe_ready"
        if handover_ready
        else "self_fix_failed_audit"
        if not audit_gate_ok
        else "self_fix_ready_for_repair"
        if no_blocking_snags and patch_requirement_ok
        else "self_fix_blocked"
    )
    report: Dict[str, Any] = {
        "schema_version": "aureon-autonomous-self-fix-director-v1",
        "status": status,
        "ok": handover_ready,
        "generated_at": _utc_now(),
        "operator_prompt": operator_prompt,
        "swot": swot,
        "repair_backlog": repair_backlog,
        "selected_repairs": selected_repairs,
        "safe_apply_policy": {
            "repair_authority": "auto_apply_safe_local_fixes",
            "audit_policy": "codex_user_audit_is_post_hoc_for_safe_local_repairs",
            "diff_source": "SafeCodeControl/QueenCodeBridge unified diffs only",
            "allowlist": list(patch_allowlist),
            "blocked_authority": ["live_trading", "payments", "filings", "credential_reveal", "destructive_os_actions"],
            "requires": ["unified_diff", "target_allowlist", "secret_scan", "git_apply_check", "git_apply", "tests"],
        },
        "patch_apply_evidence": patch_apply_evidence,
        "test_evidence": test_evidence,
        "snags": snags,
        "codex_audit_state": codex_audit,
        "handover_ready": handover_ready,
        "summary": {
            "evidence_file_count": len(evidence),
            "repair_backlog_count": len(repair_backlog),
            "selected_repair_count": len(selected_repairs),
            "patch_candidate_count": len(patch_candidates),
            "patch_applied_count": sum(1 for item in patch_apply_evidence if item.get("applied") and item.get("status") == "applied"),
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
        _write_json(_rooted(root, DEFAULT_STATE_PATH), report),
        _write_json(_rooted(root, DEFAULT_AUDIT_JSON), report),
        _write_text(_rooted(root, DEFAULT_AUDIT_MD), _make_markdown(report)),
        _write_json(_rooted(root, DEFAULT_PUBLIC_JSON), report),
    ]
    report["write_info"] = {"evidence_writes": writes}
    for rel_path in (DEFAULT_STATE_PATH, DEFAULT_AUDIT_JSON, DEFAULT_PUBLIC_JSON):
        _write_json(_rooted(root, rel_path), report)
    _write_text(_rooted(root, DEFAULT_AUDIT_MD), _make_markdown(report))
    return report


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run Aureon's autonomous self-fix SWOT and audit director.")
    parser.add_argument("--root", default="", help="Repository root. Defaults to current Aureon repo.")
    parser.add_argument("--prompt", default="", help="Optional operator prompt to check for authority holds.")
    parser.add_argument("--json", action="store_true", help="Print full JSON report.")
    parser.add_argument("--no-apply", action="store_true", help="Do not apply safe patch proposals.")
    parser.add_argument(
        "--codex-audit-state",
        default="autonomous_safe",
        choices=["autonomous_safe", "pending", "passed", "failed"],
        help="Audit verdict to record. Safe local mode runs without waiting for Codex unless failed is supplied.",
    )
    parser.add_argument(
        "--test-command",
        action="append",
        default=[],
        help="Test command to run after a patch. Repeatable. Defaults to no patch handover tests.",
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
