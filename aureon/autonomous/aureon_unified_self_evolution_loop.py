"""Unify Aureon's native cognition, Ollama, HNC/Auris, and self-repair loop.

This organ does not apply patches itself.  It establishes the measured rhythm
for the existing coding organism and guarded self-fix director: observe the
whole repo, reason with Aureon's own context plus the configured Ollama
endpoint, turn readiness defects into autonomous work orders, then let the
tested patch path apply or roll back each bounded change.

HNC/Auris is a living internal membrane here, never a cage.  Low or missing
coherence increases observation and validation depth; it never removes the
abilities to inspect, reason, patch, test, roll back, or retry.  Irreversible
external authority remains a separate outer boundary.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from aureon.autonomous.aureon_capability_forge import REPO_ROOT
from aureon.operator.coherence_gate import compute_evolution_flow


SCHEMA_VERSION = "aureon-unified-self-evolution-loop-v1"
DEFAULT_STATE_PATH = Path("state/aureon_unified_self_evolution_last_run.json")
DEFAULT_HISTORY_PATH = Path("state/aureon_unified_self_evolution_cycles.jsonl")
DEFAULT_AUDIT_JSON = Path("docs/audits/aureon_unified_self_evolution_loop.json")
DEFAULT_AUDIT_MD = Path("docs/audits/aureon_unified_self_evolution_loop.md")
DEFAULT_PUBLIC_JSON = Path("frontend/public/aureon_unified_self_evolution_loop.json")
DEFAULT_VAULT_NOTE = Path(".obsidian/Aureon Self Understanding/unified_self_evolution_loop.md")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _rooted(root: Path, rel: Path) -> Path:
    return rel if rel.is_absolute() else root / rel


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def _write_text(path: Path, content: str) -> Dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return {"path": str(path), "bytes": path.stat().st_size}


def _write_json(path: Path, payload: Dict[str, Any]) -> Dict[str, Any]:
    return _write_text(path, json.dumps(payload, indent=2, sort_keys=True, default=str))


def _append_jsonl(path: Path, payload: Dict[str, Any]) -> Dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True, default=str) + "\n")
    return {"path": str(path), "bytes": path.stat().st_size}


def _fresh_trace(name: str, max_age_sec: float = 900.0) -> Dict[str, Any]:
    try:
        from aureon.core.bus_trace import read_trace_latest

        row = read_trace_latest(name) or {}
        stamp = row.get("_ts", row.get("ts"))
        age = max(0.0, time.time() - float(stamp)) if stamp is not None else None
        return {
            "present": bool(row),
            "fresh": bool(row) and age is not None and age <= max_age_sec,
            "age_sec": None if age is None else round(age, 3),
            "payload": row,
        }
    except Exception as exc:
        return {"present": False, "fresh": False, "age_sec": None, "payload": {}, "error": type(exc).__name__}


def read_evolution_field_inputs() -> Dict[str, Any]:
    """Read the one canonical HNC field plus fresh Auris/Lighthouse traces."""
    field_payload: Dict[str, Any] = {}
    try:
        from aureon.core.hnc_field import read_canonical_field

        field = read_canonical_field()
        field_payload = field.to_dict() if hasattr(field, "to_dict") else dict(vars(field))
    except Exception as exc:
        field_payload = {"available": False, "error": type(exc).__name__}

    auris_trace = _fresh_trace("auris_cosmic_state")
    lighthouse_trace = _fresh_trace("lighthouse_event")
    auris = auris_trace.get("payload") if auris_trace.get("fresh") else {}
    lighthouse = lighthouse_trace.get("payload") if lighthouse_trace.get("fresh") else {}
    beta = None
    try:
        from aureon.core.hnc_params import load_params

        beta = load_params().beta
    except Exception:
        pass

    return {
        "gamma": field_payload.get("coherence_gamma") if field_payload.get("available") else None,
        "advisory_open": auris.get("gate_open"),
        "lighthouse_severity": lighthouse.get("severity"),
        "auris_confidence": auris.get("coherence_gamma"),
        "beta": beta,
        "sources": {
            "canonical_hnc_field": field_payload,
            "auris_cosmic_state": {key: value for key, value in auris_trace.items() if key != "payload"},
            "lighthouse_event": {key: value for key, value in lighthouse_trace.items() if key != "payload"},
        },
    }


def _readiness_work_orders(root: Path) -> list[Dict[str, Any]]:
    readiness = _read_json(root / "docs" / "audits" / "aureon_system_readiness_audit.json")
    growth = _read_json(root / "docs" / "audits" / "aureon_capability_growth_loop.json")
    orders: list[Dict[str, Any]] = []
    for proof in readiness.get("proofs", []) if isinstance(readiness.get("proofs"), list) else []:
        if not isinstance(proof, dict):
            continue
        status = str(proof.get("status") or "unknown")
        if status in {"working", "working_safe_simulation", "ready", "passed"}:
            continue
        orders.append(
            {
                "id": f"evolve_{proof.get('id', 'unknown')}",
                "source": "aureon_system_readiness_audit",
                "source_status": status,
                "priority": "P0" if any(word in status for word in ("blocked", "missing", "failed")) else "P1",
                "autonomous": True,
                "blocking": False,
                "action": proof.get("next_action") or f"Observe, repair, validate, and retest {proof.get('id')}.",
                "outer_authority_boundary": proof.get("safety_boundary") or "none",
            }
        )

    iterations = growth.get("iterations") if isinstance(growth.get("iterations"), list) else []
    latest = iterations[-1] if iterations and isinstance(iterations[-1], dict) else {}
    for gap in latest.get("gaps", []) if isinstance(latest.get("gaps"), list) else []:
        if not isinstance(gap, dict):
            continue
        order_id = f"evolve_{gap.get('id', 'gap')}"
        if any(item.get("id") == order_id for item in orders):
            continue
        orders.append(
            {
                "id": order_id,
                "source": "aureon_capability_growth_loop",
                "source_status": gap.get("status", "planned"),
                "priority": "P0" if gap.get("severity") == "high" else "P1",
                "autonomous": True,
                "blocking": False,
                "action": gap.get("proposed_action") or gap.get("title"),
                "recommended_skill": gap.get("proposed_skill_name"),
            }
        )
    return orders[:32]


def _reasoning_question(
    prompt: str,
    flow: Dict[str, Any],
    orders: Sequence[Dict[str, Any]],
    phi_swarm: Optional[Dict[str, Any]] = None,
) -> str:
    objective = str(prompt or "").strip() or "Continuously audit and evolve the Aureon backend as one organism."
    order_ids = [str(item.get("id")) for item in orders[:10]]
    swarm_answer = ((phi_swarm or {}).get("synthesis") or {}).get("answer")
    swarm_context = json.dumps(swarm_answer, sort_keys=True, default=str)[:5000] if swarm_answer else "not run"
    return (
        f"Objective: {objective}\n"
        f"HNC/Auris internal evolution flow: {flow.get('flow')}; field={flow.get('field_status')}; "
        f"patch_batch_limit={flow.get('patch_batch_limit')}.\n"
        f"Current organism work orders: {', '.join(order_ids) or 'none'}.\n"
        f"HNC phi swarm synthesis: {swarm_context}.\n"
        "Using the repo self-catalog, whole-mind wiring, capability-growth skills, contract stack, "
        "coding organism, self-fix director, and Ollama context together, rank the next bounded internal "
        "repair. Low coherence must deepen observation/tests/rollback, never close introspection or repair."
    )


def _compact_cycle(cycle: Any) -> Dict[str, Any]:
    actions = []
    for item in list(getattr(cycle, "next_actions", []) or [])[:12]:
        actions.append(
            {
                "title": getattr(item, "title", ""),
                "action_type": getattr(item, "action_type", ""),
                "blocked": bool(getattr(item, "blocked", False)),
                "requires_human": bool(getattr(item, "requires_human", False)),
            }
        )
    return {
        "cycle_id": getattr(cycle, "cycle_id", ""),
        "answer_source": getattr(cycle, "answer_source", ""),
        "summary": getattr(cycle, "summary", ""),
        "answers": list(getattr(cycle, "answers", []) or [])[:8],
        "next_actions": actions,
        "errors": [str(item)[:400] for item in list(getattr(cycle, "errors", []) or [])[:8]],
        "note_path": getattr(cycle, "note_path", ""),
    }


def _make_markdown(report: Dict[str, Any]) -> str:
    flow = report.get("coherence_flow") or {}
    reasoning = report.get("reasoning") or {}
    lines = [
        "# Aureon Unified Self-Evolution Loop",
        "",
        f"- status: {report.get('status')}",
        f"- generated_at: {report.get('generated_at')}",
        f"- evolution_flow: {flow.get('flow')}",
        f"- field_status: {flow.get('field_status')}",
        f"- patch_batch_limit: {flow.get('patch_batch_limit')}",
        f"- answer_source: {reasoning.get('answer_source')}",
        f"- internal_blocking: {report.get('internal_blocking')}",
        "",
        "## Coherence Contract",
    ]
    for reason in flow.get("reasons", []):
        lines.append(f"- {reason}")
    lines.extend(["", "## Autonomous Work Orders"])
    for order in report.get("autonomous_work_orders", []):
        lines.append(f"- {order.get('priority')} {order.get('id')}: {order.get('action')}")
    lines.extend(["", "## Ollama/Aureon Reasoning", f"- {reasoning.get('summary', '')}"])
    swarm = report.get("phi_swarm") or {}
    swarm_summary = swarm.get("summary") or {}
    lines.extend(
        [
            "",
            "## HNC Phi Ollama Swarm",
            f"- status: {swarm.get('status', 'not_requested')}",
            f"- workers: {swarm_summary.get('successful_worker_count', 0)}/{swarm_summary.get('recruited_worker_count', 0)}",
            f"- distinct_models: {swarm_summary.get('distinct_worker_models', 0)}",
            f"- api_calls: {swarm_summary.get('api_call_count', 0)}",
            f"- research_packets: {swarm_summary.get('research_packet_count', 0)}",
        ]
    )
    return "\n".join(lines) + "\n"


def build_and_write_unified_self_evolution_loop(
    *,
    root: Optional[Path] = None,
    prompt: str = "",
    run_ollama: bool = True,
    field_inputs: Optional[Dict[str, Any]] = None,
    cognitive_bridge_report: Optional[Dict[str, Any]] = None,
    self_questioning: Any = None,
    run_swarm: Optional[bool] = None,
    phi_swarm: Any = None,
) -> Dict[str, Any]:
    root = Path(root or REPO_ROOT).resolve()
    inputs = dict(field_inputs or read_evolution_field_inputs())
    flow = compute_evolution_flow(
        inputs.get("gamma"),
        inputs.get("advisory_open"),
        inputs.get("lighthouse_severity"),
        auris_confidence=inputs.get("auris_confidence"),
        beta=inputs.get("beta"),
    )
    orders = _readiness_work_orders(root)

    if cognitive_bridge_report is None:
        try:
            from aureon.autonomous.aureon_ollama_cognitive_bridge import build_and_write_ollama_cognitive_bridge

            cognitive_bridge_report = build_and_write_ollama_cognitive_bridge(root=root)
        except Exception as exc:
            cognitive_bridge_report = {"ok": False, "status": "cognitive_bridge_error", "error": type(exc).__name__}

    reasoning: Dict[str, Any] = {
        "answer_source": "not_requested",
        "summary": "HNC/Auris observation completed without an Ollama reasoning turn.",
        "answers": [],
        "next_actions": [],
        "errors": [],
    }
    reasoning_error = ""
    model_switchboard: Dict[str, Any] = {
        "status": "not_requested" if not run_ollama else "injected_questioning_adapter",
        "lanes": {},
    }
    swarm_requested = bool(run_ollama and (self_questioning is None if run_swarm is None else run_swarm))
    phi_swarm_report: Dict[str, Any] = {
        "status": "not_requested",
        "ok": False,
        "summary": {
            "recruited_worker_count": 0,
            "successful_worker_count": 0,
            "distinct_worker_models": 0,
            "api_call_count": 0,
            "research_packet_count": 0,
            "internal_blocking": False,
            "credential_values_exposed": False,
        },
    }
    if run_ollama:
        try:
            switchboard = None
            if swarm_requested or self_questioning is None:
                from aureon.integrations.ollama import OllamaModelSwitchboard

                switchboard = OllamaModelSwitchboard()
            if swarm_requested:
                if phi_swarm is None:
                    from aureon.integrations.ollama import HNCPhiOllamaSwarm

                    phi_swarm = HNCPhiOllamaSwarm(repo_root=root, switchboard=switchboard)
                phi_swarm_report = phi_swarm.run(
                    str(prompt or "Continuously audit and evolve the Aureon backend as one organism."),
                    flow,
                )
            if self_questioning is None:
                from aureon.autonomous.aureon_self_questioning_ai import SelfQuestioningAI

                reasoning_bridge, selection = switchboard.bridge_for("self_evolution")
                model_switchboard = switchboard.snapshot()
                model_switchboard["active_selection"] = selection.to_dict()
                model_switchboard["status"] = "live_catalog_routed"
                self_questioning = SelfQuestioningAI(
                    repo_root=root,
                    ollama=reasoning_bridge,
                    state_path=root / "state" / "self_questioning_ai_cycles.jsonl",
                    safe_mode=True,
                )
            cycle = self_questioning.run_cycle(
                questions=[_reasoning_question(prompt, flow, orders, phi_swarm_report)],
                include_audit=False,
                include_self_scan=False,
                augment_questions=False,
            )
            reasoning = _compact_cycle(cycle)
        except Exception as exc:
            reasoning_error = f"{type(exc).__name__}: {exc}"
            reasoning = {
                "answer_source": "aureon_native_fallback",
                "summary": "External reasoning failed; keep the native observation/repair loop alive and retry next cycle.",
                "answers": [],
                "next_actions": [],
                "errors": [reasoning_error],
            }

    ok = not reasoning_error
    status = (
        "unified_self_evolution_reasoned"
        if run_ollama and str(reasoning.get("answer_source") or "").startswith("ollama")
        else "unified_self_evolution_native_fallback"
        if run_ollama
        else "unified_self_evolution_observed"
    )
    report: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "ok": ok,
        "generated_at": _utc_now(),
        "prompt": prompt,
        "internal_blocking": False,
        "coherence_inputs": inputs,
        "coherence_flow": flow,
        "cognitive_bridge": {
            "status": (cognitive_bridge_report or {}).get("status"),
            "ok": bool((cognitive_bridge_report or {}).get("ok")),
            "summary": (cognitive_bridge_report or {}).get("summary", {}),
        },
        "model_switchboard": model_switchboard,
        "phi_swarm": phi_swarm_report,
        "reasoning": reasoning,
        "autonomous_work_orders": orders,
        "evolution_contract": {
            "operator": "Aureon",
            "instructors": ["Aureon native coding/reasoning systems", "Ollama configured endpoint"],
            "coherence": "HNC canonical field plus Auris/Lighthouse changes pace and proof depth, never internal access",
            "cycle": ["catalog", "observe", "reason", "propose", "test", "apply_or_rollback", "retest", "remember", "repeat"],
            "outer_authority_boundary": [
                "credential_values",
                "live_market_or_exchange_mutation",
                "payments_or_fund_transfer",
                "official_legal_or_tax_filing",
                "destructive_host_or_repo_action",
            ],
        },
        "summary": {
            "flow": flow.get("flow"),
            "field_status": flow.get("field_status"),
            "patch_batch_limit": flow.get("patch_batch_limit"),
            "required_test_layer_count": len(flow.get("required_test_layers", [])),
            "autonomous_work_order_count": len(orders),
            "ollama_reasoning_requested": run_ollama,
            "reasoning_source": reasoning.get("answer_source"),
            "reasoning_error_count": len(reasoning.get("errors", [])),
            "ollama_model_catalog_size": model_switchboard.get("catalog_size", 0),
            "ollama_active_model": (model_switchboard.get("active_selection") or {}).get("model", ""),
            "phi_swarm_requested": swarm_requested,
            "phi_swarm_successful_workers": (phi_swarm_report.get("summary") or {}).get("successful_worker_count", 0),
            "phi_swarm_distinct_models": (phi_swarm_report.get("summary") or {}).get("distinct_worker_models", 0),
            "phi_swarm_api_calls": (phi_swarm_report.get("summary") or {}).get("api_call_count", 0),
            "internal_blocking": False,
        },
        "output_files": [
            DEFAULT_STATE_PATH.as_posix(),
            DEFAULT_HISTORY_PATH.as_posix(),
            DEFAULT_AUDIT_JSON.as_posix(),
            DEFAULT_AUDIT_MD.as_posix(),
            DEFAULT_PUBLIC_JSON.as_posix(),
        ],
    }

    writes = [
        _write_json(_rooted(root, DEFAULT_STATE_PATH), report),
        _append_jsonl(_rooted(root, DEFAULT_HISTORY_PATH), report),
        _write_json(_rooted(root, DEFAULT_AUDIT_JSON), report),
        _write_text(_rooted(root, DEFAULT_AUDIT_MD), _make_markdown(report)),
        _write_json(_rooted(root, DEFAULT_PUBLIC_JSON), report),
    ]
    try:
        from aureon.obsidian_paths import resolve_obsidian_note_path

        vault_path = resolve_obsidian_note_path(DEFAULT_VAULT_NOTE, repo_root=root)
        writes.append(_write_text(vault_path, _make_markdown(report)))
        report["vault_note"] = str(vault_path)
    except Exception as exc:
        report["vault_note_error"] = type(exc).__name__
    report["write_info"] = {"evidence_writes": writes}
    for rel in (DEFAULT_STATE_PATH, DEFAULT_AUDIT_JSON, DEFAULT_PUBLIC_JSON):
        _write_json(_rooted(root, rel), report)
    _write_text(_rooted(root, DEFAULT_AUDIT_MD), _make_markdown(report))
    return report


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run Aureon's unified non-blocking HNC/Auris self-evolution reasoning turn.")
    parser.add_argument("--root", default="", help="Repository root; defaults to the Aureon checkout.")
    parser.add_argument("--prompt", default="", help="Objective for this bounded evolution turn.")
    parser.add_argument("--no-ollama", action="store_true", help="Observe and route work without an external reasoning turn.")
    parser.add_argument("--no-swarm", action="store_true", help="Use one routed reasoning model without phi swarm fan-out.")
    parser.add_argument("--json", action="store_true", help="Print the complete report.")
    args = parser.parse_args(argv)
    report = build_and_write_unified_self_evolution_loop(
        root=Path(args.root).resolve() if args.root else None,
        prompt=args.prompt,
        run_ollama=not args.no_ollama,
        run_swarm=not args.no_swarm,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True, default=str))
    else:
        summary = report.get("summary", {})
        print(
            f"{report.get('status')}: flow={summary.get('flow')} "
            f"work_orders={summary.get('autonomous_work_order_count')} "
            f"reasoning={summary.get('reasoning_source')}"
        )
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
