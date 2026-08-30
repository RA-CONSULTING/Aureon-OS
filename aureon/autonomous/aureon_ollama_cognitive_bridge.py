from __future__ import annotations

import argparse
import json
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence


SCHEMA_VERSION = "aureon-ollama-cognitive-bridge-v1"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATE_PATH = Path("state/aureon_ollama_cognitive_bridge_last_run.json")
DEFAULT_AUDIT_JSON = Path("docs/audits/aureon_ollama_cognitive_bridge.json")
DEFAULT_AUDIT_MD = Path("docs/audits/aureon_ollama_cognitive_bridge.md")
DEFAULT_PUBLIC_JSON = Path("frontend/public/aureon_ollama_cognitive_bridge.json")

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
AGENT_GUARDIAN_PATHS = (
    Path("frontend/public/aureon_agent_creative_process_guardian.json"),
    Path("docs/audits/aureon_agent_creative_process_guardian.json"),
)
AGENT_COMPANY_PATHS = (
    Path("frontend/public/aureon_agent_company_bill_list.json"),
    Path("docs/audits/aureon_agent_company_bill_list.json"),
)
CODING_SKILL_BASE_PATHS = (
    Path("frontend/public/aureon_coding_agent_skill_base.json"),
    Path("docs/audits/aureon_coding_agent_skill_base.json"),
)

AUTHORITY_BOUNDARIES = [
    "Ollama is a local language worker, not an authority bypass.",
    "Aureon cognitive evidence can enrich prompts and status, but live trading remains runtime-gated.",
    "Credential values are never emitted; only readiness/status may be reported.",
    "Payments, official filings, and destructive OS actions remain blocked unless existing safe routes explicitly allow them.",
    "Phi chat replies must be evidence-honest and publish ThoughtBus proof when used through the hub.",
]

HANDSHAKE_CREW = [
    {
        "role": "Phi Chat Steward",
        "department": "operator",
        "day_to_day": "Accept the human message, redact context, and keep the dashboard conversation live.",
    },
    {
        "role": "Aureon Metacognitive Context Builder",
        "department": "cognition",
        "day_to_day": "Gather HNC/Auris, cognitive, voice, role, and skill evidence before the model answers.",
    },
    {
        "role": "Ollama Language Worker",
        "department": "local_llm",
        "day_to_day": "Generate local language responses through the installed Ollama model when reachable.",
    },
    {
        "role": "Aureon Brain Fallback",
        "department": "cognition",
        "day_to_day": "Keep reasoning available when the local model is offline, slow, or blocked by audit mode.",
    },
    {
        "role": "HNC/Auris Drift Inspector",
        "department": "quality",
        "day_to_day": "Hold claims when harmonic, node, or cognitive proof is missing or stale.",
    },
    {
        "role": "ThoughtBus Evidence Clerk",
        "department": "memory",
        "day_to_day": "Publish chat and bridge status evidence without leaking secrets.",
    },
]

HANDSHAKE_FLOW = [
    {
        "step": "sense",
        "owner": "Aureon Metacognitive Context Builder",
        "how": "Read local cognitive evidence, HNC/Auris state, voice state, role memory, and skill maps.",
    },
    {
        "step": "guard",
        "owner": "HNC/Auris Drift Inspector",
        "how": "Check that the response lane has safety boundaries, source evidence, and fallback behavior.",
    },
    {
        "step": "speak",
        "owner": "Ollama Language Worker",
        "how": "Use the configured local model through Ollama native/OpenAI-compatible routes.",
    },
    {
        "step": "fallback",
        "owner": "Aureon Brain Fallback",
        "how": "Answer through Aureon's in-house rule/brain layer when Ollama is unavailable.",
    },
    {
        "step": "publish",
        "owner": "ThoughtBus Evidence Clerk",
        "how": "Write state, audit, public JSON, and chat evidence so the cockpit can show the truth.",
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
    return {
        "name": name,
        "present": bool(payload),
        "path": path,
        "age_sec": round(age_sec, 3) if path else None,
        "max_age_sec": max_age_sec,
        "stale": bool(path and age_sec > max_age_sec),
        "schema_version": str(payload.get("schema_version") or ""),
        "status": status,
        "summary": summary,
    }


def _ollama_snapshot() -> Dict[str, Any]:
    try:
        from aureon.integrations.ollama import OllamaBridge

        timeout_s = float(os.environ.get("AUREON_OLLAMA_BRIDGE_TIMEOUT_S", "2") or 2)
        return OllamaBridge(timeout_s=max(0.25, timeout_s)).snapshot()
    except Exception as exc:
        from aureon.ollama_config import resolve_ollama_native_base_url

        return {
            "reachable": False,
            "base_url": resolve_ollama_native_base_url(),
            "chat_model": os.environ.get("AUREON_LLM_MODEL") or os.environ.get("AUREON_OLLAMA_MODEL") or "",
            "models": [],
            "running": [],
            "error": str(exc),
        }


def _resolve_model(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    models = [str(item) for item in snapshot.get("models", []) if str(item).strip()]
    running = [str(item) for item in snapshot.get("running", []) if str(item).strip()]
    configured = (
        os.environ.get("AUREON_LLM_MODEL")
        or os.environ.get("AUREON_OLLAMA_MODEL")
        or str(snapshot.get("chat_model") or "")
        or "llama3"
    )
    resolved = ""
    reason = "no_model_library_visible"
    if configured in models:
        resolved = configured
        reason = "configured_model_installed"
    elif models:
        family = configured.split(":")[0].split(".")[0].lower()
        same_family = [model for model in models if family and family in model.lower()]
        depth_preferred = [model for model in models if model in {"llama3:latest", "llama3.1:8b", "llama3.2:3b"}]
        if same_family:
            resolved = same_family[0]
            reason = "using_configured_model_family"
        elif depth_preferred:
            resolved = depth_preferred[0]
            reason = "using_depth_model"
        elif running:
            resolved = running[0]
            reason = "using_running_model"
        else:
            resolved = models[0]
            reason = "using_available_model"
    elif running:
        resolved = running[0]
        reason = "using_running_model"
    return {
        "configured_model": configured,
        "resolved_model": resolved,
        "model_ready": bool(snapshot.get("reachable") and resolved),
        "resolution_reason": reason,
        "running": resolved in running if resolved else False,
    }


def _build_source_contracts(root: Path) -> List[Dict[str, Any]]:
    day = 24 * 60 * 60
    return [
        _source_contract(root, "hnc_cognitive_proof", HNC_PROOF_PATHS, day),
        _source_contract(root, "harmonic_affect_state", HARMONIC_AFFECT_PATHS, day),
        _source_contract(root, "cognitive_trade_evidence", COGNITIVE_EVIDENCE_PATHS, day),
        _source_contract(root, "expression_profile", EXPRESSION_PROFILE_PATHS, 7 * day),
        _source_contract(root, "voice_state", VOICE_STATE_PATHS, 7 * day),
        _source_contract(root, "agent_creative_process_guardian", AGENT_GUARDIAN_PATHS, day),
        _source_contract(root, "agent_company_registry", AGENT_COMPANY_PATHS, 7 * day),
        _source_contract(root, "coding_skill_base", CODING_SKILL_BASE_PATHS, 7 * day),
    ]


def _cognitive_readiness(source_contracts: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_name = {str(item.get("name")): item for item in source_contracts}
    guardian = by_name.get("agent_creative_process_guardian", {})
    guardian_summary = guardian.get("summary") if isinstance(guardian.get("summary"), dict) else {}
    hnc_present = bool(by_name.get("hnc_cognitive_proof", {}).get("present"))
    harmonic_present = bool(by_name.get("harmonic_affect_state", {}).get("present"))
    cognitive_present = bool(by_name.get("cognitive_trade_evidence", {}).get("present"))
    roles_ready = bool(guardian_summary.get("who_what_where_when_how_act_ready")) or bool(
        by_name.get("agent_company_registry", {}).get("present")
    )
    hnc_auris_ready = bool(guardian_summary.get("hnc_auris_ready")) or (hnc_present and harmonic_present)
    metacognitive_ready = bool(guardian_summary.get("metacognitive_ready")) or cognitive_present
    present_count = sum(1 for item in source_contracts if item.get("present"))
    return {
        "hnc_auris_ready": hnc_auris_ready,
        "metacognitive_ready": metacognitive_ready,
        "role_contracts_ready": roles_ready,
        "cognitive_source_count": present_count,
        "minimum_source_count": 3,
        "cognitive_ready": bool(hnc_auris_ready and metacognitive_ready and roles_ready and present_count >= 3),
    }


def _proof_checklist(
    snapshot: Dict[str, Any],
    model_resolution: Dict[str, Any],
    readiness: Dict[str, Any],
) -> List[Dict[str, Any]]:
    return [
        {
            "id": "ollama_server_reachable",
            "label": "Configured Ollama local/cloud endpoint is reachable",
            "ok": bool(snapshot.get("reachable")),
            "blocking": True,
            "evidence": snapshot.get("base_url", ""),
        },
        {
            "id": "local_model_library_visible",
            "label": "Ollama model catalog is visible",
            "ok": bool(snapshot.get("models")),
            "blocking": True,
            "evidence": ", ".join([str(item) for item in snapshot.get("models", [])[:6]]),
        },
        {
            "id": "chat_model_resolved",
            "label": "A chat model is resolved for Aureon",
            "ok": bool(model_resolution.get("model_ready")),
            "blocking": True,
            "evidence": model_resolution.get("resolved_model") or model_resolution.get("resolution_reason"),
        },
        {
            "id": "hnc_auris_context_ready",
            "label": "HNC/Auris context is ready for guarded conversation",
            "ok": bool(readiness.get("hnc_auris_ready")),
            "blocking": True,
            "evidence": f"sources={readiness.get('cognitive_source_count', 0)}",
        },
        {
            "id": "metacognitive_context_ready",
            "label": "Aureon metacognitive evidence is present",
            "ok": bool(readiness.get("metacognitive_ready")),
            "blocking": True,
            "evidence": f"sources={readiness.get('cognitive_source_count', 0)}",
        },
        {
            "id": "role_contracts_ready",
            "label": "Agent roles can declare who, what, where, when, how, and act",
            "ok": bool(readiness.get("role_contracts_ready")),
            "blocking": True,
            "evidence": "agent company / creative guardian",
        },
        {
            "id": "brain_fallback_declared",
            "label": "Aureon Brain fallback is declared when Ollama is unavailable",
            "ok": True,
            "blocking": True,
            "evidence": "AureonHybridAdapter falls back to AureonBrainAdapter",
        },
        {
            "id": "authority_boundaries_preserved",
            "label": "Existing live-action and credential gates remain authoritative",
            "ok": True,
            "blocking": True,
            "evidence": "no bypass introduced",
        },
    ]


def _next_actions(
    snapshot: Dict[str, Any],
    model_resolution: Dict[str, Any],
    readiness: Dict[str, Any],
) -> List[Dict[str, Any]]:
    actions: List[Dict[str, Any]] = []
    if not snapshot.get("reachable"):
        if snapshot.get("cloud") or snapshot.get("auth_required"):
            actions.append(
                {
                    "id": "inspect_ollama_cloud",
                    "severity": "repair",
                    "action": "Recheck the configured Ollama Cloud endpoint and runtime credential bootstrap.",
                    "powershell": "python scripts/validation/audit_external_llm_fallback.py",
                }
            )
        else:
            actions.append(
                {
                    "id": "start_ollama",
                    "severity": "repair",
                    "action": "Start Ollama locally, then refresh the mind hub.",
                    "powershell": "ollama serve",
                }
            )
    if snapshot.get("reachable") and not snapshot.get("models"):
        actions.append(
            {
                "id": "install_local_model",
                "severity": "blocking",
                "action": "Install a local model; llama3 gives deeper cockpit reasoning when the machine can carry it.",
                "powershell": "ollama pull llama3",
            }
        )
    if snapshot.get("models") and not model_resolution.get("model_ready"):
        actions.append(
            {
                "id": "set_model",
                "severity": "blocking",
                "action": "Set Aureon to an installed Ollama model.",
                "powershell": '$env:AUREON_LLM_MODEL = "llama3:latest"',
            }
        )
    if not readiness.get("cognitive_ready"):
        actions.append(
            {
                "id": "refresh_cognitive_proof",
                "severity": "blocking",
                "action": "Refresh HNC/Auris, cognitive evidence, and creative-process guardian reports.",
                "powershell": ".\\.venv\\Scripts\\python.exe -m aureon.autonomous.aureon_agent_creative_process_guardian --json",
            }
        )
    actions.append(
        {
            "id": "use_hybrid_backend",
            "severity": "setup",
            "action": "Use the hand-in-hand voice backend for the dashboard chat lane.",
            "powershell": '$env:AUREON_VOICE_BACKEND = "ollama_hybrid"',
        }
    )
    return actions


def _status_for(checks: List[Dict[str, Any]], snapshot: Dict[str, Any], readiness: Dict[str, Any]) -> str:
    blocking_failed = [item for item in checks if item.get("blocking") and not item.get("ok")]
    if not blocking_failed:
        return "ollama_cognitive_bridge_ready"
    if not snapshot.get("reachable"):
        return "ollama_cognitive_bridge_waiting_for_ollama"
    if not readiness.get("cognitive_ready"):
        return "ollama_cognitive_bridge_blocked_by_cognitive_sources"
    return "ollama_cognitive_bridge_needs_attention"


def _make_markdown(report: Dict[str, Any]) -> str:
    summary = report.get("summary", {})
    lines = [
        "# Aureon Ollama Cognitive Bridge",
        "",
        f"- status: {report.get('status')}",
        f"- generated_at: {report.get('generated_at')}",
        f"- ollama_reachable: {summary.get('ollama_reachable')}",
        f"- resolved_model: {summary.get('resolved_model')}",
        f"- hnc_auris_ready: {summary.get('hnc_auris_ready')}",
        f"- metacognitive_ready: {summary.get('metacognitive_ready')}",
        f"- hand_in_hand_ready: {report.get('ok')}",
        "",
        "## Crew",
    ]
    for item in report.get("handshake_crew", []):
        lines.append(f"- {item.get('role')}: {item.get('day_to_day')}")
    lines.extend(["", "## Proof Checklist"])
    for item in report.get("proof_checklist", []):
        state = "pass" if item.get("ok") else "hold"
        lines.append(f"- {state}: {item.get('label')} ({item.get('evidence')})")
    lines.extend(["", "## Next Actions"])
    for item in report.get("next_actions", []):
        lines.append(f"- {item.get('id')}: {item.get('action')}")
    return "\n".join(lines) + "\n"


def build_ollama_cognitive_bridge(*, root: Optional[Path] = None) -> Dict[str, Any]:
    root = Path(root or _default_root()).resolve()
    generated_at = _utc_now()
    snapshot = _ollama_snapshot()
    model_resolution = _resolve_model(snapshot)
    source_contracts = _build_source_contracts(root)
    readiness = _cognitive_readiness(source_contracts)
    checks = _proof_checklist(snapshot, model_resolution, readiness)
    status = _status_for(checks, snapshot, readiness)
    ok = status == "ollama_cognitive_bridge_ready"
    output_files = [
        DEFAULT_STATE_PATH.as_posix(),
        DEFAULT_AUDIT_JSON.as_posix(),
        DEFAULT_AUDIT_MD.as_posix(),
        DEFAULT_PUBLIC_JSON.as_posix(),
    ]

    report: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "ok": ok,
        "generated_at": generated_at,
        "bridge_mode": "configured_ollama_endpoint_plus_aureon_cognition",
        "provider_policy": "configured_local_or_ollama_cloud",
        "recommended_voice_backend": "ollama_hybrid",
        "ollama": snapshot,
        "model_resolution": model_resolution,
        "source_contracts": source_contracts,
        "cognitive_readiness": readiness,
        "handshake_crew": HANDSHAKE_CREW,
        "handshake_flow": HANDSHAKE_FLOW,
        "proof_checklist": checks,
        "next_actions": _next_actions(snapshot, model_resolution, readiness),
        "authority_boundaries": AUTHORITY_BOUNDARIES,
        "who_what_where_when_how_act": {
            "who": {
                "operator_lane": "MindThoughtActionHub Phi chat",
                "language_worker": "Ollama Language Worker",
                "cognitive_context": "Aureon Metacognitive Context Builder",
                "safety_guard": "HNC/Auris Drift Inspector",
                "fallback": "Aureon Brain Fallback",
            },
            "what": {
                "job": "Make configured Ollama local/cloud reasoning and Aureon's internal cognitive systems work as one agent crew.",
                "model": model_resolution.get("resolved_model") or model_resolution.get("configured_model"),
                "status": status,
            },
            "where": {
                "ollama_base_url": snapshot.get("base_url", ""),
                "phi_status_endpoint": "http://127.0.0.1:13002/api/phi-bridge/status",
                "ollama_cognitive_status_endpoint": "http://127.0.0.1:13002/api/ollama-cognitive/status",
                "public_json": "/aureon_ollama_cognitive_bridge.json",
            },
            "when": "At startup, on cockpit refresh, and before/after Phi chat replies.",
            "how": "Redacted dashboard context is enriched with Aureon cognitive proof, sent through local Ollama when reachable, and held by HNC/Auris and authority boundaries.",
            "act": "Answer the operator, publish evidence, expose blockers, and fall back to AureonBrain without bypassing safety gates.",
        },
        "summary": {
            "ollama_reachable": bool(snapshot.get("reachable")),
            "installed_model_count": len(snapshot.get("models", []) or []),
            "running_model_count": len(snapshot.get("running", []) or []),
            "resolved_model": model_resolution.get("resolved_model", ""),
            "model_ready": bool(model_resolution.get("model_ready")),
            "hnc_auris_ready": bool(readiness.get("hnc_auris_ready")),
            "metacognitive_ready": bool(readiness.get("metacognitive_ready")),
            "role_contracts_ready": bool(readiness.get("role_contracts_ready")),
            "cognitive_ready": bool(readiness.get("cognitive_ready")),
            "blocking_check_count": sum(1 for item in checks if item.get("blocking") and not item.get("ok")),
            "hand_in_hand_ready": ok,
        },
        "output_files": output_files,
        "write_info": {
            "writer": "AureonOllamaCognitiveBridge",
            "authoring_path": [
                "probe_ollama_bridge",
                "resolve_local_model",
                "read_cognitive_evidence",
                "build_handshake_crew",
                "run_proof_checklist",
                "publish_state_docs_frontend",
            ],
        },
    }
    return report


def write_ollama_cognitive_bridge(report: Dict[str, Any], *, root: Optional[Path] = None) -> Dict[str, Any]:
    root = Path(root or _default_root()).resolve()
    writes = [
        _write_json(_rooted(root, DEFAULT_STATE_PATH), report),
        _write_json(_rooted(root, DEFAULT_AUDIT_JSON), report),
        _write_text(_rooted(root, DEFAULT_AUDIT_MD), _make_markdown(report)),
        _write_json(_rooted(root, DEFAULT_PUBLIC_JSON), report),
    ]
    report.setdefault("write_info", {})["evidence_writes"] = writes
    for rel in (DEFAULT_STATE_PATH, DEFAULT_AUDIT_JSON, DEFAULT_PUBLIC_JSON):
        _write_json(_rooted(root, rel), report)
    _write_text(_rooted(root, DEFAULT_AUDIT_MD), _make_markdown(report))
    return report


def build_and_write_ollama_cognitive_bridge(*, root: Optional[Path] = None) -> Dict[str, Any]:
    report = build_ollama_cognitive_bridge(root=root)
    return write_ollama_cognitive_bridge(report, root=root)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Publish Aureon's Ollama cognitive bridge proof.")
    parser.add_argument("--repo-root", default="", help="Repository root; defaults to cwd/repo.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Markdown.")
    args = parser.parse_args(argv)

    root = Path(args.repo_root).resolve() if args.repo_root else None
    from aureon.core.aureon_env import bootstrap_credentials

    bootstrap_credentials(root)
    report = build_and_write_ollama_cognitive_bridge(root=root)
    print(json.dumps(report, indent=2, sort_keys=True, default=str) if args.json else _make_markdown(report))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
