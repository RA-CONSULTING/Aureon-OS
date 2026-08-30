from __future__ import annotations

import argparse
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence


SCHEMA_VERSION = "aureon-agent-creative-process-guardian-v1"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATE_PATH = Path("state/aureon_agent_creative_process_guardian_last_run.json")
DEFAULT_AUDIT_JSON = Path("docs/audits/aureon_agent_creative_process_guardian.json")
DEFAULT_AUDIT_MD = Path("docs/audits/aureon_agent_creative_process_guardian.md")
DEFAULT_PUBLIC_JSON = Path("frontend/public/aureon_agent_creative_process_guardian.json")

HNC_PROOF_PATHS = (
    Path("state/aureon_hnc_cognitive_proof.json"),
    Path("docs/audits/aureon_hnc_cognitive_proof.json"),
)
HARMONIC_AFFECT_PATHS = (
    Path("docs/audits/aureon_harmonic_affect_state.json"),
    Path("frontend/public/aureon_harmonic_affect_state.json"),
)
COGNITIVE_EVIDENCE_PATHS = (
    Path("docs/audits/aureon_cognitive_trade_evidence.json"),
    Path("frontend/public/aureon_cognitive_trade_evidence.json"),
)
EXPRESSION_PROFILE_PATHS = (
    Path("state/aureon_expression_profile.json"),
    Path("frontend/public/aureon_expression_profile.json"),
)
VOICE_STATE_PATHS = (
    Path("state/aureon_voice_last_run.json"),
    Path("state/voice_intent_cognition_state.json"),
)
AGENT_COMPANY_PATHS = (
    Path("frontend/public/aureon_agent_company_bill_list.json"),
    Path("docs/audits/aureon_agent_company_bill_list.json"),
)
CODING_SKILL_BASE_PATHS = (
    Path("frontend/public/aureon_coding_agent_skill_base.json"),
    Path("docs/audits/aureon_coding_agent_skill_base.json"),
)

AUTHORITY_BOUNDARIES = (
    "no live trading bypass",
    "no payment or official filing mutation",
    "no credential reveal",
    "no destructive OS action without approved safe route",
    "housekeeping reports before mutation",
)

CREATIVE_PROCESS_LOOP = [
    {
        "step": "sense",
        "owner": "Metacognitive Sensor",
        "rule": "Read the current goal, runtime state, HNC proof, harmonic affect, Auris node status, voice/expression profile, repo state, and existing role memory before creating.",
    },
    {
        "step": "orient",
        "owner": "Client Brief Broker",
        "rule": "Declare who owns the work, what is being made, where it may act, when it is allowed to act, and which authority gates apply.",
    },
    {
        "step": "compose",
        "owner": "Assigned Creative Crew",
        "rule": "Create only through the role-approved Aureon route, using whole-organism context without exceeding authority.",
    },
    {
        "step": "harmonic_check",
        "owner": "HNC/Auris Drift Inspector",
        "rule": "Reject or hold output when HNC proof, master formula, Auris nodes, coherence, runtime freshness, or safety boundaries are missing or stale.",
    },
    {
        "step": "prove",
        "owner": "Test Pilot / Quality Gate Inspector",
        "rule": "Attach render, playback, build, test, source, or evidence proof before claiming the work is finished.",
    },
    {
        "step": "act",
        "owner": "Release Manager",
        "rule": "Publish who/what/where/when/how/act, snags, handoffs, and next actions; keep handover hidden while blockers remain.",
    },
]


def _default_root() -> Path:
    return Path.cwd().resolve() if (Path.cwd() / "aureon").exists() else REPO_ROOT


def _rooted(root: Path, rel_path: Path) -> Path:
    return rel_path if rel_path.is_absolute() else root / rel_path


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path, default: Any = None) -> Any:
    try:
        if not path.exists():
            return {} if default is None else default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {} if default is None else default


def _write_text(path: Path, content: str) -> Dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return {"path": str(path), "ok": path.exists(), "bytes": path.stat().st_size if path.exists() else 0}


def _write_json(path: Path, payload: Dict[str, Any]) -> Dict[str, Any]:
    return _write_text(path, json.dumps(payload, indent=2, sort_keys=True, default=str))


def _age_sec(path: Path) -> float:
    try:
        return max(0.0, time.time() - path.stat().st_mtime)
    except Exception:
        return math.inf


def _read_first_json(root: Path, paths: Iterable[Path]) -> tuple[Dict[str, Any], str, float]:
    for rel in paths:
        path = _rooted(root, rel)
        payload = _read_json(path, {})
        if isinstance(payload, dict) and payload:
            return payload, str(path), _age_sec(path)
    return {}, "", math.inf


def _source_contract(root: Path, name: str, paths: Iterable[Path], max_age_sec: float) -> Dict[str, Any]:
    payload, path, age_sec = _read_first_json(root, paths)
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    status = str(payload.get("status") or summary.get("status") or ("present" if payload else "missing"))
    stale = bool(path and age_sec > max_age_sec)
    return {
        "name": name,
        "present": bool(payload),
        "path": path,
        "age_sec": round(age_sec, 3) if path else None,
        "max_age_sec": max_age_sec,
        "stale": stale,
        "schema_version": payload.get("schema_version", ""),
        "status": status,
        "summary": summary,
    }


def _refresh_mind_reports(root: Path) -> List[Dict[str, Any]]:
    writes: List[Dict[str, Any]] = []
    try:
        from aureon.autonomous.aureon_cognitive_trade_evidence import (
            build_cognitive_trade_state,
            write_cognitive_trade_state,
        )

        state = build_cognitive_trade_state(root)
        output, public = write_cognitive_trade_state(
            state,
            _rooted(root, Path("docs/audits/aureon_cognitive_trade_evidence.json")),
            _rooted(root, Path("frontend/public/aureon_cognitive_trade_evidence.json")),
        )
        writes.append({"system": "cognitive_trade_evidence", "ok": True, "paths": [str(output), str(public)]})
    except Exception as exc:
        writes.append({"system": "cognitive_trade_evidence", "ok": False, "error": str(exc)})
    try:
        from aureon.autonomous.aureon_harmonic_affect_state import (
            build_harmonic_affect_state,
            write_harmonic_affect_state,
        )

        state = build_harmonic_affect_state(root)
        output, public = write_harmonic_affect_state(
            state,
            _rooted(root, Path("docs/audits/aureon_harmonic_affect_state.json")),
            _rooted(root, Path("frontend/public/aureon_harmonic_affect_state.json")),
        )
        writes.append({"system": "harmonic_affect_state", "ok": True, "paths": [str(output), str(public)]})
    except Exception as exc:
        writes.append({"system": "harmonic_affect_state", "ok": False, "error": str(exc)})
    return writes


def _load_agent_company(root: Path, goal: str) -> Dict[str, Any]:
    payload, _, _ = _read_first_json(root, AGENT_COMPANY_PATHS)
    if isinstance(payload.get("roles"), list) and payload.get("roles"):
        return payload
    try:
        from aureon.autonomous.aureon_agent_company_builder import build_agent_company_bill_list

        return build_agent_company_bill_list(root=root, goal=goal)
    except Exception as exc:
        return {
            "schema_version": "aureon-agent-company-unavailable",
            "status": "agent_company_unavailable",
            "summary": {"role_count": 0},
            "roles": [],
            "error": str(exc),
        }


def _load_coding_skill_base(root: Path) -> Dict[str, Any]:
    payload, _, _ = _read_first_json(root, CODING_SKILL_BASE_PATHS)
    return payload if isinstance(payload, dict) else {}


def _safe_text(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text if text else fallback


def _role_process(role: Dict[str, Any], mind_contract: Dict[str, Any], goal: str) -> Dict[str, Any]:
    existing_surfaces = role.get("existing_surfaces") if isinstance(role.get("existing_surfaces"), list) else []
    work_orders = role.get("work_orders") if isinstance(role.get("work_orders"), list) else []
    day_to_day = role.get("day_to_day") if isinstance(role.get("day_to_day"), list) else []
    checks = role.get("standing_checks") if isinstance(role.get("standing_checks"), list) else []
    role_loop = role.get("who_what_where_when_how_act") if isinstance(role.get("who_what_where_when_how_act"), dict) else {}
    access = role.get("whole_organism_access") if isinstance(role.get("whole_organism_access"), dict) else {}
    blocked: List[str] = []
    if not role_loop:
        blocked.append("missing_role_who_what_where_when_how_act")
    if not day_to_day:
        blocked.append("missing_day_to_day_loop")
    if not checks:
        blocked.append("missing_standing_checks")
    if not (existing_surfaces or work_orders):
        blocked.append("missing_surface_or_work_order")
    if access.get("access_model") != "whole_organism_with_role_authority":
        blocked.append("missing_whole_organism_access_policy")

    who = _safe_text(role_loop.get("who"), _safe_text(role.get("title"), "Unknown role"))
    what = _safe_text(role_loop.get("what"), _safe_text(role.get("mission"), "Role mission not declared"))
    where = role_loop.get("where") or existing_surfaces or work_orders
    when = _safe_text(role_loop.get("when"), "Before acting, read mind/sensory state and current client scope.")
    how = role_loop.get("how") or day_to_day[:6]
    act = _safe_text(role_loop.get("act"), "Publish evidence, checks, handoffs, and next action.")
    return {
        "role_id": role.get("role_id"),
        "title": role.get("title"),
        "department": role.get("department"),
        "status": "creative_process_ready" if not blocked else "creative_process_attention",
        "who": who,
        "what": what,
        "where": where,
        "when": when,
        "how": how,
        "act": act,
        "creative_process_checklist": [
            {"id": "sense_mind", "ok": mind_contract.get("metacognitive_ready"), "evidence": "metacognitive and sensory reports read"},
            {"id": "hnc_auris_guard", "ok": mind_contract.get("hnc_auris_ready"), "evidence": "HNC proof, master formula, and Auris nodes"},
            {"id": "role_loop_declared", "ok": bool(role_loop), "evidence": "who/what/where/when/how/act declared"},
            {"id": "whole_access_bounded", "ok": access.get("access_model") == "whole_organism_with_role_authority", "evidence": "whole organism access with role authority"},
            {"id": "proof_route", "ok": bool(checks), "evidence": "standing checks exist"},
            {"id": "surface_or_work_order", "ok": bool(existing_surfaces or work_orders), "evidence": "real surface or work order is mapped"},
        ],
        "mind_bindings": {
            "metacognitive_systems": mind_contract.get("metacognitive_sources", []),
            "sensory_systems": mind_contract.get("sensory_sources", []),
            "hnc_auris_systems": mind_contract.get("hnc_auris_sources", []),
            "sentient_style_systems": mind_contract.get("sentient_style_sources", []),
            "sentience_boundary": "computational state and self-model evidence only; no claim of human consciousness",
        },
        "authority_boundaries": list(AUTHORITY_BOUNDARIES),
        "goal_context": goal,
        "blockers": blocked,
    }


def _scan_agent_surfaces(root: Path, limit: int = 350) -> List[Dict[str, Any]]:
    scan_roots = [root / "aureon", root / "frontend" / "src", root / "tests"]
    patterns = ("agent", "bot", "queen", "organism", "bridge", "auris", "hnc", "sentient", "skill", "forge", "worker")
    skip_parts = {".git", ".venv", "node_modules", "__pycache__", "dist", "imports", "test-results"}
    rows: List[Dict[str, Any]] = []
    for base in scan_roots:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if len(rows) >= limit:
                return rows
            if not path.is_file() or path.suffix.lower() not in {".py", ".ts", ".tsx", ".json", ".md"}:
                continue
            rel = path.relative_to(root)
            rel_parts = set(rel.parts)
            if rel_parts & skip_parts:
                continue
            rel_text = str(rel).replace("\\", "/").lower()
            if not any(pattern in rel_text for pattern in patterns):
                continue
            if "trading" in rel_text or "exchange" in rel_text:
                domain = "trading_data"
            elif "frontend" in rel_text or rel_text.endswith(".tsx"):
                domain = "product_ui"
            elif "test" in rel_text:
                domain = "quality"
            elif "vault" in rel_text or "voice" in rel_text:
                domain = "memory_voice"
            elif "harmonic" in rel_text or "auris" in rel_text or "hnc" in rel_text:
                domain = "hnc_auris"
            else:
                domain = "autonomous"
            rows.append(
                {
                    "path": str(rel).replace("\\", "/"),
                    "domain": domain,
                    "creative_contract": "must publish who/what/where/when/how/act before claiming completion",
                    "status": "covered_by_guardian_contract",
                }
            )
    return rows


def _build_mind_contract(root: Path, max_age_sec: float) -> Dict[str, Any]:
    hnc, _, _ = _read_first_json(root, HNC_PROOF_PATHS)
    harmonic, _, _ = _read_first_json(root, HARMONIC_AFFECT_PATHS)
    cognitive, _, _ = _read_first_json(root, COGNITIVE_EVIDENCE_PATHS)
    expression, _, _ = _read_first_json(root, EXPRESSION_PROFILE_PATHS)
    voice, _, _ = _read_first_json(root, VOICE_STATE_PATHS)

    master = hnc.get("master_formula") if isinstance(hnc.get("master_formula"), dict) else {}
    auris = hnc.get("auris_nodes") if isinstance(hnc.get("auris_nodes"), dict) else {}
    hnc_passed = bool(hnc.get("passed")) or str(hnc.get("status", "")).lower() == "passing"
    master_passed = bool(master.get("passed", hnc_passed))
    auris_passed = bool(auris.get("passed", hnc_passed))

    sources = [
        _source_contract(root, "hnc_cognitive_proof", HNC_PROOF_PATHS, max_age_sec),
        _source_contract(root, "harmonic_affect_state", HARMONIC_AFFECT_PATHS, max_age_sec),
        _source_contract(root, "cognitive_trade_evidence", COGNITIVE_EVIDENCE_PATHS, max_age_sec),
        _source_contract(root, "whole_knowledge_expression_profile", EXPRESSION_PROFILE_PATHS, max_age_sec * 4),
        _source_contract(root, "voice_intent_cognition_state", VOICE_STATE_PATHS, max_age_sec * 4),
    ]
    present = {source["name"]: source for source in sources if source["present"]}
    blockers: List[str] = []
    if not hnc:
        blockers.append("hnc_cognitive_proof_missing")
    if hnc and not hnc_passed:
        blockers.append("hnc_cognitive_proof_not_passing")
    if hnc and not master_passed:
        blockers.append("hnc_master_formula_not_passing")
    if hnc and not auris_passed:
        blockers.append("auris_nodes_not_passing")
    if not harmonic:
        blockers.append("harmonic_affect_state_missing")

    stale_sources = [source["name"] for source in sources if source["present"] and source["stale"]]
    warnings = [f"{name}_stale" for name in stale_sources]
    harmonic_summary = harmonic.get("summary") if isinstance(harmonic.get("summary"), dict) else {}
    cognitive_summary = cognitive.get("summary") if isinstance(cognitive.get("summary"), dict) else {}

    return {
        "metacognitive_ready": bool(cognitive or expression or voice),
        "sensory_ready": bool(harmonic or expression or voice),
        "hnc_auris_ready": not blockers,
        "sentient_style_ready": bool(expression or voice or harmonic),
        "metacognitive_sources": ["cognitive_trade_evidence", "whole_knowledge_expression_profile", "voice_intent_cognition_state"],
        "sensory_sources": ["harmonic_affect_state", "whole_knowledge_expression_profile", "voice_intent_cognition_state"],
        "hnc_auris_sources": ["hnc_cognitive_proof", "harmonic_affect_state", "auris_nodes", "master_formula"],
        "sentient_style_sources": ["whole_knowledge_voice_core", "phi_bridge", "auris_metacognition", "harmonic_affect_state"],
        "source_contracts": sources,
        "present_source_names": sorted(present),
        "summary": {
            "hnc_passed": hnc_passed,
            "master_formula_passed": master_passed,
            "auris_nodes_passed": auris_passed,
            "hnc_coherence_score": harmonic_summary.get("hnc_coherence_score") or master.get("score") or auris.get("coherence"),
            "affect_phase": harmonic_summary.get("affect_phase"),
            "cognitive_action_mode": cognitive_summary.get("action_mode"),
            "runtime_stale": bool(harmonic_summary.get("runtime_stale") or cognitive_summary.get("runtime_stale")),
        },
        "blockers": blockers,
        "warnings": warnings,
        "sentience_boundary": "Aureon uses computational self-monitoring, metacognition, voice, HNC/Auris, and sensory-state reports as operating evidence; this report does not assert human subjective consciousness.",
    }


def build_agent_creative_process_guardian(
    *,
    root: Optional[Path] = None,
    goal: str = "",
    refresh_inputs: bool = True,
    max_age_sec: float = 6 * 60 * 60,
) -> Dict[str, Any]:
    root = Path(root or _default_root()).resolve()
    refresh_writes = _refresh_mind_reports(root) if refresh_inputs else []
    generated_at = _utc_now()
    agent_company = _load_agent_company(root, goal)
    coding_skill_base = _load_coding_skill_base(root)
    roles = agent_company.get("roles") if isinstance(agent_company.get("roles"), list) else []
    mind_contract = _build_mind_contract(root, max_age_sec=max_age_sec)
    role_processes = [_role_process(role, mind_contract, goal) for role in roles if isinstance(role, dict)]
    repo_agent_surfaces = _scan_agent_surfaces(root)
    blocked_roles = [role for role in role_processes if role.get("blockers")]
    role_count = len(role_processes)
    process_ready = role_count > 0 and not blocked_roles and mind_contract.get("hnc_auris_ready")
    source_blockers = list(mind_contract.get("blockers", []))
    snags: List[Dict[str, Any]] = []
    for blocker in source_blockers:
        snags.append(
            {
                "id": f"mind_{blocker}",
                "title": blocker.replace("_", " "),
                "severity": "blocking",
                "owner": "HNC/Auris Drift Inspector",
                "status": "open",
                "next_action": "Refresh or repair the missing/passing HNC/Auris evidence before creative handover.",
            }
        )
    for role in blocked_roles[:25]:
        snags.append(
            {
                "id": f"role_{role.get('role_id')}_creative_process",
                "title": f"{role.get('title')} creative process incomplete",
                "severity": "blocking",
                "owner": "Quality Gate Inspector",
                "status": "open",
                "evidence": role.get("blockers"),
                "next_action": "Add day-to-day loop, surfaces/work orders, standing checks, and who/what/where/when/how/act.",
            }
        )
    if not snags:
        snags.append(
            {
                "id": "creative_process_ready_for_agent_use",
                "title": "Creative process guardian ready",
                "severity": "notice",
                "owner": "Release Manager",
                "status": "ready",
                "next_action": "Use this contract as a proof gate for all agent creative work.",
            }
        )

    output_files = [
        str(_rooted(root, DEFAULT_STATE_PATH)),
        str(_rooted(root, DEFAULT_AUDIT_JSON)),
        str(_rooted(root, DEFAULT_AUDIT_MD)),
        str(_rooted(root, DEFAULT_PUBLIC_JSON)),
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "status": "agent_creative_process_guardian_ready" if process_ready else "agent_creative_process_guardian_attention",
        "ok": bool(process_ready),
        "goal": goal,
        "summary": {
            "role_count": role_count,
            "creative_process_ready_role_count": role_count - len(blocked_roles),
            "blocked_role_count": len(blocked_roles),
            "repo_agent_surface_count": len(repo_agent_surfaces),
            "mind_source_count": len(mind_contract.get("source_contracts", [])),
            "present_mind_source_count": len(mind_contract.get("present_source_names", [])),
            "metacognitive_ready": bool(mind_contract.get("metacognitive_ready")),
            "sensory_ready": bool(mind_contract.get("sensory_ready")),
            "hnc_auris_ready": bool(mind_contract.get("hnc_auris_ready")),
            "sentient_style_ready": bool(mind_contract.get("sentient_style_ready")),
            "who_what_where_when_how_act_ready": role_count > 0 and not blocked_roles,
            "all_agents_guarded": bool(process_ready),
            "blocking_snag_count": len([snag for snag in snags if snag.get("severity") == "blocking"]),
        },
        "organism_mind_contract": mind_contract,
        "creative_process_loop": CREATIVE_PROCESS_LOOP,
        "agent_creative_process_map": role_processes,
        "repo_agent_surfaces": repo_agent_surfaces,
        "coding_logic_map": coding_skill_base.get("coding_logic_map", {}),
        "agent_company_summary": agent_company.get("summary", {}),
        "authority_boundaries": list(AUTHORITY_BOUNDARIES),
        "proof_checklist": [
            {
                "id": "metacognitive_sources_present",
                "label": "Metacognitive sources present",
                "ok": bool(mind_contract.get("metacognitive_ready")),
                "blocking": True,
            },
            {
                "id": "sensory_sources_present",
                "label": "Sensory/sentient-style sources present",
                "ok": bool(mind_contract.get("sensory_ready")),
                "blocking": True,
            },
            {
                "id": "hnc_auris_sources_passing",
                "label": "HNC, master formula, and Auris nodes pass",
                "ok": bool(mind_contract.get("hnc_auris_ready")),
                "blocking": True,
            },
            {
                "id": "role_processes_declared",
                "label": "Every role has who/what/where/when/how/act",
                "ok": role_count > 0 and not blocked_roles,
                "blocking": True,
            },
            {
                "id": "repo_agent_surfaces_scanned",
                "label": "Repo agent surfaces scanned",
                "ok": bool(repo_agent_surfaces),
                "blocking": False,
            },
        ],
        "snagging_list": snags,
        "who_what_where_when_how_act": {
            "who": "Aureon Agent Creative Process Guardian",
            "what": "Bind every Aureon agent role and repo agent surface to metacognitive, sensory, HNC/Auris, and sentient-style evidence before creative action.",
            "where": output_files,
            "when": "Before any agent claims creative work is ready for client handover.",
            "how": [
                "refresh cognitive trade and harmonic affect reports",
                "read HNC cognitive proof, master formula, and Auris nodes",
                "read whole-knowledge voice/expression and sensory-state evidence",
                "load Aureon agent company roles and coding skill logic map",
                "scan repo agent-like surfaces",
                "materialize who/what/where/when/how/act for every role",
                "publish proof checklist, blockers, and public dashboard evidence",
            ],
            "act": "Hold or clear agent creative handover based on the proof checklist and snagging list.",
        },
        "refresh_writes": refresh_writes,
        "output_files": output_files,
    }


def _make_markdown(report: Dict[str, Any]) -> str:
    summary = report.get("summary", {})
    lines = [
        "# Aureon Agent Creative Process Guardian",
        "",
        f"- Status: `{report.get('status')}`",
        f"- Roles guarded: {summary.get('creative_process_ready_role_count', 0)}/{summary.get('role_count', 0)}",
        f"- Repo agent surfaces scanned: {summary.get('repo_agent_surface_count', 0)}",
        f"- HNC/Auris ready: {summary.get('hnc_auris_ready')}",
        f"- Metacognitive ready: {summary.get('metacognitive_ready')}",
        f"- Sensory ready: {summary.get('sensory_ready')}",
        f"- Sentient-style ready: {summary.get('sentient_style_ready')}",
        "",
        "## Creative Process Loop",
        "",
    ]
    for step in report.get("creative_process_loop", []):
        lines.append(f"- **{step.get('step')}** ({step.get('owner')}): {step.get('rule')}")
    lines.extend(["", "## Snags", ""])
    for snag in report.get("snagging_list", [])[:30]:
        lines.append(f"- `{snag.get('severity')}` {snag.get('title')} - {snag.get('status')}")
    return "\n".join(lines) + "\n"


def build_and_write_agent_creative_process_guardian(
    *,
    root: Optional[Path] = None,
    goal: str = "",
    refresh_inputs: bool = True,
    max_age_sec: float = 6 * 60 * 60,
) -> Dict[str, Any]:
    root = Path(root or _default_root()).resolve()
    report = build_agent_creative_process_guardian(
        root=root,
        goal=goal,
        refresh_inputs=refresh_inputs,
        max_age_sec=max_age_sec,
    )
    writes = [
        _write_json(_rooted(root, DEFAULT_STATE_PATH), report),
        _write_json(_rooted(root, DEFAULT_AUDIT_JSON), report),
        _write_text(_rooted(root, DEFAULT_AUDIT_MD), _make_markdown(report)),
        _write_json(_rooted(root, DEFAULT_PUBLIC_JSON), report),
    ]
    report["write_info"] = {"writer": "AureonAgentCreativeProcessGuardian", "evidence_writes": writes}
    for write in writes:
        if write.get("path", "").endswith(".json"):
            _write_json(Path(write["path"]), report)
    return report


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Aureon's agent creative process guardian.")
    parser.add_argument("--goal", "--prompt", default="", help="Current creative/client goal.")
    parser.add_argument("--repo-root", default="", help="Repo root; defaults to current Aureon repo.")
    parser.add_argument("--no-refresh", action="store_true", help="Do not refresh cognitive/harmonic input reports first.")
    parser.add_argument("--json", action="store_true", help="Print the full report JSON.")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    root = Path(args.repo_root).resolve() if args.repo_root else _default_root()
    report = build_and_write_agent_creative_process_guardian(
        root=root,
        goal=args.goal,
        refresh_inputs=not args.no_refresh,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True, default=str))
    else:
        print(
            json.dumps(
                {
                    "status": report.get("status"),
                    "ok": report.get("ok"),
                    "summary": report.get("summary"),
                    "public_json": str(_rooted(root, DEFAULT_PUBLIC_JSON)),
                },
                indent=2,
                sort_keys=True,
            )
        )
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
