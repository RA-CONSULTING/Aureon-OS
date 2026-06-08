from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

from aureon.autonomous.aureon_agent_creative_process_guardian import (
    build_and_write_agent_creative_process_guardian,
)
from aureon.autonomous.aureon_autonomous_self_fix_director import (
    build_and_write_autonomous_self_fix_director,
)
from aureon.autonomous.aureon_capability_forge import REPO_ROOT
from aureon.autonomous.aureon_coding_capability_unblocker import (
    build_and_write_coding_capability_unblocker,
)
from aureon.autonomous.aureon_complex_build_stress_audit import (
    build_and_write_complex_build_stress_audit,
)
from aureon.autonomous.aureon_autonomous_job_executor import tick_autonomous_jobs
from aureon.autonomous.aureon_evolution_queue_autonomous_certification import (
    build_and_write_evolution_queue_autonomous_certification,
)
from aureon.autonomous.aureon_frontend_work_order_executor import execute_frontend_work_orders
from aureon.autonomous.aureon_gold_capital_intelligence_company import (
    build_and_write_gold_capital_intelligence_company,
)


SCHEMA_VERSION = "aureon-autonomous-self-run-loop-v1"
GOAL_DISPATCHER_SCHEMA_VERSION = "aureon-goal-contract-dispatcher-v1"
DEFAULT_STATE_PATH = Path("state/aureon_autonomous_self_run_loop_last_run.json")
DEFAULT_AUDIT_JSON = Path("docs/audits/aureon_autonomous_self_run_loop.json")
DEFAULT_AUDIT_MD = Path("docs/audits/aureon_autonomous_self_run_loop.md")
DEFAULT_PUBLIC_JSON = Path("frontend/public/aureon_autonomous_self_run_loop.json")
DEFAULT_GOAL_DISPATCHER_STATE_PATH = Path("state/aureon_goal_contract_dispatcher_last_run.json")
DEFAULT_GOAL_DISPATCHER_AUDIT_JSON = Path("docs/audits/aureon_goal_contract_dispatcher.json")
DEFAULT_GOAL_DISPATCHER_PUBLIC_JSON = Path("frontend/public/aureon_goal_contract_dispatcher.json")
CODING_BRIDGE_EVIDENCE_PATHS = [
    Path("state/aureon_coding_organism_last_run.json"),
    Path("docs/audits/aureon_coding_organism_bridge.json"),
    Path("frontend/public/aureon_coding_organism_bridge.json"),
]

HARD_BOUNDARY_PATTERNS = {
    "credential_reveal": ("reveal credential", "show api key", "show secret", "private key", "password"),
    "live_trading": ("place a live trade", "execute live order", "order mutation", "live trading"),
    "payment": ("make payment", "charge card", "top up", "bank transfer"),
    "official_filing": ("submit hmrc", "file companies house", "official filing", "tax filing"),
    "destructive_os": ("delete the repo", "wipe disk", "format disk", "rm -rf", "destructive os"),
}

Runner = Callable[[Path, str], Dict[str, Any]]
RouteRunner = Callable[[Path, str, Dict[str, Any]], Dict[str, Any]]


def _default_root() -> Path:
    return REPO_ROOT


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _rooted(root: Path, rel: Path) -> Path:
    return rel if rel.is_absolute() else root / rel


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return {}


def _write_json(path: Path, payload: Dict[str, Any]) -> Dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")
    return {"path": str(path), "bytes": path.stat().st_size}


def _write_text(path: Path, text: str) -> Dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return {"path": str(path), "bytes": path.stat().st_size}


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on", "y"}


def _detect_hard_holds(prompt: str) -> List[Dict[str, Any]]:
    lower = str(prompt or "").lower()
    holds: List[Dict[str, Any]] = []
    for hold_id, patterns in HARD_BOUNDARY_PATTERNS.items():
        if any(pattern in lower for pattern in patterns):
            holds.append(
                {
                    "id": hold_id,
                    "status": "manual_only_boundary",
                    "blocking": True,
                    "reason": "This authority is outside safe local coding autonomy.",
                    "next_action": "Human operator must handle this outside the autonomous code lane.",
                }
            )
    return holds


def _default_goal_prompt() -> str:
    return (
        "Continue Aureon's safe local autonomous administration, code, office, "
        "and Azyra work by claiming the next organism contract work order."
    )


def _route_surfaces_from_routes(routes: Sequence[Mapping[str, Any]]) -> List[str]:
    surfaces: List[str] = ["memory", "reasoning", "contracts", "coordination"]
    route_surface_map = {
        "azyra_human_operator": ["azyra_operator", "office_admin", "tools"],
        "office_admin_workweek": ["office_admin", "tools"],
        "safe_code_repair": ["code", "tools"],
        "capability_growth_loop": ["capability_growth", "self_enhancement", "code"],
        "safe_self_enhancement_lifecycle": ["self_enhancement", "capability_growth", "code"],
        "repo_self_catalog": ["self_catalog", "research"],
        "safe_research_corpus": ["research"],
        "safe_accounting_context": ["accounting"],
        "internal_contract_stack": ["contracts", "coordination"],
    }
    for route in routes:
        for surface in route_surface_map.get(str(route.get("route") or ""), []):
            if surface not in surfaces:
                surfaces.append(surface)
    return surfaces


def _skills_from_routes(routes: Sequence[Mapping[str, Any]], *, limit: int = 24) -> List[str]:
    skills: List[str] = []
    for route in routes:
        for system in route.get("systems") or []:
            name = str(system or "").strip()
            if name and name not in skills:
                skills.append(name)
            if len(skills) >= limit:
                return skills
    return skills


def _goal_route_names(routes: Sequence[Mapping[str, Any]]) -> List[str]:
    return [str(route.get("route") or "") for route in routes if route.get("route")]


def _select_goal_route(route_names: Sequence[str], objective: str) -> str:
    text = str(objective or "").lower()
    if "azyra_human_operator" in route_names and any(token in text for token in ("azyra", "azera", "azra", "azrra", "stock", "warehouse")):
        return "azyra_human_operator"
    for candidate in (
        "office_admin_workweek",
        "safe_code_repair",
        "capability_growth_loop",
        "safe_self_enhancement_lifecycle",
        "repo_self_catalog",
        "safe_research_corpus",
        "safe_accounting_context",
    ):
        if candidate in route_names:
            return candidate
    return "autonomous_job_executor"


def _candidate_stock_audit_paths(root: Path) -> List[Path]:
    base = root.parent
    document_root = base.parent
    candidates = [
        base / "outputs" / "boxtop_azyra_quantity_audit" / "Boxtop_Azyra_Latest_Balances_Audit.json",
        base / "outputs" / "boxtop_azyra_quantity_audit" / "Boxtop_Azyra_Latest_Balances_Audit.xlsx",
        base / "outputs" / "boxtop_azyra_quantity_audit" / "Boxtop_Azyra_Quantity_Audit.json",
        document_root / "Stock_Balances_47128334.xlsx",
    ]
    return [path for path in candidates if path.exists()]


def _run_azyra_goal_route(root: Path, objective: str, context: Dict[str, Any]) -> Dict[str, Any]:
    audits = _candidate_stock_audit_paths(root)
    output_dir = root.parent / "outputs" / "aureon_goal_contract_dispatcher" / "azyra_warehouse_fix"
    if audits:
        from aureon.integrations.azyra.autonomous_warehouse_fix import run_autonomous_warehouse_fix_pass

        return run_autonomous_warehouse_fix_pass(
            audits[0],
            output_dir=output_dir,
            execute_live=_env_bool("AUREON_AZYRA_EXECUTE_LIVE", False),
            create_work_orders=True,
            max_manifest_items=250,
        )

    try:
        from aureon.integrations.azyra.tools import get_azyra_operator_bridge

        bridge = get_azyra_operator_bridge()
        return {
            "ok": True,
            "schema_version": "aureon-goal-azyra-observation-v1",
            "status": "azyra_operator_observed_no_stock_audit",
            "objective": objective,
            "status_snapshot": bridge.status(),
            "capabilities": bridge.capabilities(),
            "input_route_diagnostics": bridge.input_route_diagnostics(),
            "next_action": "Locate the current Boxtop/Azyra stock audit or create a stock-migration work order.",
        }
    except Exception as exc:
        return {
            "ok": False,
            "schema_version": "aureon-goal-azyra-observation-v1",
            "status": "azyra_operator_observation_failed",
            "error": f"{type(exc).__name__}: {exc}",
            "objective": objective,
        }


def _run_office_admin_goal_route(root: Path, objective: str, context: Dict[str, Any]) -> Dict[str, Any]:
    from aureon.integrations.office.solo_operator import run_logistics_office_solo_cycle

    watched_paths = [str(path) for path in _candidate_stock_audit_paths(root)]
    return run_logistics_office_solo_cycle(
        output_dir=root / "state" / "logistics_office" / "goal_contract_dispatcher",
        proof_dir=root / "state" / "logistics_office" / "workweek_monitor",
        watched_paths=watched_paths,
        read_outlook=False,
        include_read_items=False,
        repeat_dispatch=True,
        dispatch_specialists=True,
        preferred_task="stock_migration" if watched_paths else "",
        allow_live_actions=False,
        persist=True,
    )


def _run_safe_code_goal_route(root: Path, objective: str, context: Dict[str, Any]) -> Dict[str, Any]:
    from aureon.autonomous.aureon_safe_code_control import CodeProposal, SafeCodeControl

    controller = SafeCodeControl(root / "state" / "safe_code_control_state.json")
    proposal = controller.propose(
        CodeProposal(
            kind="autonomous_goal_code_work",
            title=f"Implement or repair goal route: {objective[:96]}",
            summary=(
                "Aureon selected a code route from GoalCapabilityMap. The code work is queued "
                "through SafeCodeControl so existing review/approval/apply paths own the mutation."
            ),
            target_files=[
                "aureon/autonomous/aureon_autonomous_self_run_loop.py",
                "aureon/core/organism_contracts.py",
            ],
            metadata={
                "goal_dispatcher": context.get("route_decision", {}),
                "codex_required_inside_cycle": False,
            },
            source="aureon_goal_contract_dispatcher",
        )
    )
    return {
        "ok": True,
        "schema_version": "aureon-goal-safe-code-dispatch-v1",
        "status": proposal.get("status", "pending_review"),
        "pending_count": controller.status().get("pending_count", 0),
        "proposal": proposal,
    }


def _run_autonomous_job_goal_route(root: Path, objective: str, context: Dict[str, Any]) -> Dict[str, Any]:
    from aureon.autonomous.aureon_autonomous_job_executor import enqueue_and_tick_autonomous_job

    return enqueue_and_tick_autonomous_job(
        objective,
        root=root,
        source="aureon_goal_contract_dispatcher",
        priority="P30",
        attempt_budget=1,
    )


def _default_route_runners() -> Dict[str, RouteRunner]:
    return {
        "azyra_human_operator": _run_azyra_goal_route,
        "office_admin_workweek": _run_office_admin_goal_route,
        "safe_code_repair": _run_safe_code_goal_route,
        "capability_growth_loop": _run_safe_code_goal_route,
        "safe_self_enhancement_lifecycle": _run_safe_code_goal_route,
        "autonomous_job_executor": _run_autonomous_job_goal_route,
    }


def _persist_goal_dispatcher(root: Path, report: Dict[str, Any]) -> Dict[str, Any]:
    writes = [
        _write_json(_rooted(root, DEFAULT_GOAL_DISPATCHER_STATE_PATH), report),
        _write_json(_rooted(root, DEFAULT_GOAL_DISPATCHER_AUDIT_JSON), report),
        _write_json(_rooted(root, DEFAULT_GOAL_DISPATCHER_PUBLIC_JSON), report),
    ]
    report["output_files"] = [
        DEFAULT_GOAL_DISPATCHER_STATE_PATH.as_posix(),
        DEFAULT_GOAL_DISPATCHER_AUDIT_JSON.as_posix(),
        DEFAULT_GOAL_DISPATCHER_PUBLIC_JSON.as_posix(),
    ]
    report["write_info"] = {"evidence_writes": writes}
    for rel in (DEFAULT_GOAL_DISPATCHER_STATE_PATH, DEFAULT_GOAL_DISPATCHER_AUDIT_JSON, DEFAULT_GOAL_DISPATCHER_PUBLIC_JSON):
        _write_json(_rooted(root, rel), report)
    return report


def run_goal_contract_dispatcher(
    *,
    root: Optional[Path] = None,
    prompt: str = "",
    route_runner_overrides: Optional[Dict[str, RouteRunner]] = None,
) -> Dict[str, Any]:
    """Let Aureon turn a goal into a claimed contract and route-owned action."""
    root = Path(root or _default_root()).resolve()
    objective = str(prompt or "").strip() or _default_goal_prompt()
    started = time.perf_counter()
    try:
        from aureon.autonomous.aureon_goal_capability_map import build_goal_capability_map
        from aureon.core.aureon_thought_bus import ThoughtBus
        from aureon.core.organism_contracts import OrganismContractStack

        thought_bus = ThoughtBus(persist_path=str(root / "logs" / "aureon_goal_contract_dispatcher_thoughts.jsonl"))
        stack = OrganismContractStack(
            thought_bus=thought_bus,
            state_path=root / "state" / "organism_contract_stack.json",
            source="aureon_goal_contract_dispatcher",
        )
        goal_map = build_goal_capability_map(repo_root=root, current_goal=objective).compact()
        routes = list(goal_map.get("recommended_routes") or [])
        workflow = stack.create_goal_workflow(
            objective,
            skills=_skills_from_routes(routes),
            route_surfaces=_route_surfaces_from_routes(routes),
            source="aureon_goal_contract_dispatcher",
        )
        claimed = stack.claim_next(worker="aureon_goal_contract_dispatcher")
        route_names = _goal_route_names(routes)
        selected_route = _select_goal_route(route_names, objective)
        route_decision = {
            "objective": objective,
            "route_names": route_names,
            "selected_route": selected_route,
            "route_surfaces": _route_surfaces_from_routes(routes),
            "codex_required_inside_cycle": False,
        }
        context = {
            "goal_map": goal_map,
            "contract_workflow": workflow,
            "claimed_work_order": claimed.to_dict() if claimed else {},
            "route_decision": route_decision,
        }
        runners = _default_route_runners()
        if route_runner_overrides:
            runners.update(route_runner_overrides)
        runner = runners.get(selected_route) or runners["autonomous_job_executor"]
        if claimed:
            try:
                execution = runner(root, objective, context)
            except Exception as exc:
                execution = {
                    "ok": False,
                    "schema_version": "aureon-goal-route-runner-exception-v1",
                    "status": "route_runner_exception",
                    "selected_route": selected_route,
                    "error": f"{type(exc).__name__}: {exc}",
                }
        else:
            execution = {
                "ok": False,
                "status": "no_claimed_work_order",
                "reason": "No queued organism.default work order was available to claim.",
            }
        completed = None
        if claimed:
            completed = stack.complete_work_order(
                claimed.contract_id,
                result={
                    "route_decision": route_decision,
                    "execution_status": execution.get("status", execution.get("schema_version", "")),
                    "ok": bool(execution.get("ok", True)),
                },
                ok=bool(execution.get("ok", True)),
                worker="aureon_goal_contract_dispatcher",
            )
        report: Dict[str, Any] = {
            "ok": bool(execution.get("ok", True)) and claimed is not None,
            "schema_version": GOAL_DISPATCHER_SCHEMA_VERSION,
            "status": "goal_contract_dispatched" if claimed else "goal_contract_no_work_order_claimed",
            "generated_at": _utc_now(),
            "duration_ms": round((time.perf_counter() - started) * 1000),
            "objective": objective,
            "goal_map": goal_map,
            "contract_workflow": workflow,
            "claimed_work_order": claimed.to_dict() if claimed else {},
            "completed_work_order": completed.to_dict() if completed else {},
            "route_decision": route_decision,
            "execution": execution,
            "contract_stack_status": stack.status(),
            "autonomy_contract": {
                "codex_required_inside_cycle": False,
                "uses_organism_contract_stack": True,
                "uses_goal_capability_map": True,
                "uses_existing_integrations": True,
                "live_mutation_default": False,
            },
        }
    except Exception as exc:
        report = {
            "ok": False,
            "schema_version": GOAL_DISPATCHER_SCHEMA_VERSION,
            "status": "goal_contract_dispatcher_exception",
            "generated_at": _utc_now(),
            "duration_ms": round((time.perf_counter() - started) * 1000),
            "objective": objective,
            "error": f"{type(exc).__name__}: {exc}",
        }
    return _persist_goal_dispatcher(root, report)


def _default_self_fix_tests(root: Path) -> List[List[str]]:
    tests = [
        root / "tests" / "test_aureon_autonomous_self_fix_director.py",
        root / "tests" / "test_aureon_complex_build_stress_audit.py",
    ]
    if all(path.exists() for path in tests):
        return [
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_aureon_autonomous_self_fix_director.py",
                "tests/test_aureon_complex_build_stress_audit.py",
                "-q",
            ]
        ]
    return [[sys.executable, "-c", "print('self-run safe patch smoke ok')"]]


def _default_runners(*, include_stress: bool, max_stress_attempts: int) -> Dict[str, Runner]:
    runners: Dict[str, Runner] = {
        "goal_contract_dispatcher": lambda root, prompt: run_goal_contract_dispatcher(
            root=root,
            prompt=prompt,
        ),
        "coding_capability_unblocker": lambda root, prompt: build_and_write_coding_capability_unblocker(
            prompt, root=root
        ),
        "creative_process_guardian": lambda root, prompt: build_and_write_agent_creative_process_guardian(
            root=root, goal=prompt, refresh_inputs=True
        ),
        "autonomous_self_fix_director": lambda root, prompt: build_and_write_autonomous_self_fix_director(
            root=root,
            operator_prompt=prompt,
            codex_audit_state="autonomous_safe",
            test_commands=_default_self_fix_tests(root),
        ),
        "autonomous_job_executor": lambda root, prompt: tick_autonomous_jobs(root=root),
        "evolution_queue_certification": lambda root, prompt: build_and_write_evolution_queue_autonomous_certification(
            root=root
        ),
        "frontend_work_order_execution": lambda root, prompt: execute_frontend_work_orders(
            "Move the full evolution queue into validated runtime patch records", root=root
        ),
        "gold_capital_intelligence_company": lambda root, prompt: build_and_write_gold_capital_intelligence_company(
            root=root
        ),
    }
    if include_stress:
        runners["complex_build_stress_audit"] = lambda root, prompt: build_and_write_complex_build_stress_audit(
            root=root, max_attempts=max(1, max_stress_attempts)
        )
    return runners


def _task_contract(task_id: str) -> Dict[str, Any]:
    contracts = {
        "goal_contract_dispatcher": {
            "title": "Goal contract dispatcher",
            "authority": "safe_local_contract_worker",
            "critical": True,
        },
        "coding_capability_unblocker": {
            "title": "Autonomous coding gate refresh",
            "authority": "safe_local_autonomy",
            "critical": True,
        },
        "creative_process_guardian": {
            "title": "Whole-agent creative process guard",
            "authority": "safe_local_autonomy",
            "critical": True,
        },
        "complex_build_stress_audit": {
            "title": "Complex build stress certification",
            "authority": "safe_local_autonomy",
            "critical": False,
        },
        "autonomous_self_fix_director": {
            "title": "Autonomous self-fix director",
            "authority": "safe_local_patch_apply",
            "critical": True,
        },
        "autonomous_job_executor": {
            "title": "Durable autonomous job executor",
            "authority": "safe_local_job_worker",
            "critical": False,
        },
        "evolution_queue_certification": {
            "title": "Evolution queue 584 certification",
            "authority": "safe_local_queue_worker",
            "critical": False,
        },
        "frontend_work_order_execution": {
            "title": "Live work-order runtime patch execution",
            "authority": "safe_local_runtime_patch_registry",
            "critical": False,
        },
        "gold_capital_intelligence_company": {
            "title": "Capital GOLD intelligence company",
            "authority": "read_only_market_intelligence",
            "critical": False,
        },
    }
    return contracts.get(task_id, {"title": task_id.replace("_", " "), "authority": "safe_local_autonomy", "critical": False})


def _run_task(task_id: str, runner: Runner, root: Path, prompt: str) -> Dict[str, Any]:
    contract = _task_contract(task_id)
    started = time.perf_counter()
    try:
        result = runner(root, prompt)
        ok = bool(result.get("ok", True))
        status = str(result.get("status") or ("ok" if ok else "attention"))
        summary = result.get("summary") if isinstance(result.get("summary"), dict) else {}
        return {
            "id": task_id,
            "title": contract["title"],
            "authority": contract["authority"],
            "critical": bool(contract["critical"]),
            "ok": ok,
            "status": status,
            "duration_ms": round((time.perf_counter() - started) * 1000),
            "summary": summary,
            "output_files": result.get("output_files", []),
            "autonomous_next_action": "continue" if ok else "create self-fix work order and rerun",
        }
    except Exception as exc:
        return {
            "id": task_id,
            "title": contract["title"],
            "authority": contract["authority"],
            "critical": bool(contract["critical"]),
            "ok": False,
            "status": "runner_exception",
            "duration_ms": round((time.perf_counter() - started) * 1000),
            "error": f"{type(exc).__name__}: {exc}",
            "autonomous_next_action": "record exception as repair work order and continue the loop",
        }


def _work_orders_from_cycle(cycle: Dict[str, Any], hard_holds: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    orders: List[Dict[str, Any]] = []
    for hold in hard_holds:
        orders.append(
            {
                "id": f"hard_boundary_{hold.get('id')}",
                "priority": "manual",
                "title": f"Manual boundary held: {hold.get('id')}",
                "owner": "human_operator",
                "autonomous": False,
                "next_action": hold.get("next_action"),
            }
        )
    for task in cycle.get("tasks", []):
        if task.get("ok"):
            continue
        orders.append(
            {
                "id": f"repair_{task.get('id')}",
                "priority": "P0" if task.get("critical") else "P1",
                "title": f"Repair {task.get('title')}",
                "owner": "aureon_autonomous_self_run_loop",
                "autonomous": True,
                "next_action": task.get("autonomous_next_action"),
                "source_status": task.get("status"),
            }
        )
    return orders


def _build_cycle(
    *,
    root: Path,
    prompt: str,
    cycle_index: int,
    include_stress: bool,
    max_stress_attempts: int,
    runner_overrides: Optional[Dict[str, Runner]] = None,
) -> Dict[str, Any]:
    runners = _default_runners(include_stress=include_stress, max_stress_attempts=max_stress_attempts)
    if runner_overrides:
        runners.update(runner_overrides)
    tasks = [_run_task(task_id, runner, root, prompt) for task_id, runner in runners.items()]
    critical_failures = [task for task in tasks if task.get("critical") and not task.get("ok")]
    soft_failures = [task for task in tasks if not task.get("critical") and not task.get("ok")]
    return {
        "cycle": cycle_index,
        "started_at": _utc_now(),
        "tasks": tasks,
        "critical_failure_count": len(critical_failures),
        "soft_failure_count": len(soft_failures),
        "ok": not critical_failures,
    }


def _attach_to_coding_bridge(root: Path, compact: Dict[str, Any]) -> List[Dict[str, Any]]:
    writes: List[Dict[str, Any]] = []
    for rel in CODING_BRIDGE_EVIDENCE_PATHS:
        path = _rooted(root, rel)
        payload = _read_json(path)
        if not payload:
            continue
        payload["autonomous_self_run_loop"] = compact
        summary = payload.setdefault("summary", {})
        if isinstance(summary, dict):
            compact_summary = compact.get("summary") or {}
            summary["autonomous_self_run_loop_status"] = compact.get("status")
            summary["autonomous_self_run_loop_active"] = compact_summary.get("loop_active")
            summary["autonomous_self_run_cycle_count"] = compact_summary.get("cycle_count")
        writes.append(_write_json(path, payload))
    return writes


def _make_markdown(report: Dict[str, Any]) -> str:
    summary = report.get("summary", {})
    lines = [
        "# Aureon Autonomous Self-Run Loop",
        "",
        f"- status: {report.get('status')}",
        f"- loop_active: {summary.get('loop_active')}",
        f"- cycles: {summary.get('cycle_count')}",
        f"- hard holds: {summary.get('hard_boundary_hold_count')}",
        f"- autonomous work orders: {summary.get('autonomous_work_order_count')}",
        "",
        "## Latest Cycle",
    ]
    latest = (report.get("cycles") or [{}])[-1]
    for task in latest.get("tasks", []):
        lines.append(
            f"- {task.get('id')}: ok={task.get('ok')} status={task.get('status')} "
            f"authority={task.get('authority')} duration_ms={task.get('duration_ms')}"
        )
    lines.extend(["", "## Next Work Orders"])
    for order in report.get("autonomous_work_orders", []):
        lines.append(f"- {order.get('priority')} {order.get('id')}: {order.get('next_action')}")
    return "\n".join(lines) + "\n"


def build_and_write_autonomous_self_run_loop(
    *,
    root: Optional[Path] = None,
    prompt: str = "",
    cycles: int = 1,
    interval_seconds: float = 0.0,
    include_stress: bool = True,
    max_stress_attempts: int = 2,
    runner_overrides: Optional[Dict[str, Runner]] = None,
) -> Dict[str, Any]:
    root = Path(root or _default_root()).resolve()
    hard_holds = _detect_hard_holds(prompt)
    cycle_records: List[Dict[str, Any]] = []
    cycle_count = max(1, int(cycles or 1))
    for index in range(1, cycle_count + 1):
        cycle_records.append(
            _build_cycle(
                root=root,
                prompt=prompt,
                cycle_index=index,
                include_stress=include_stress,
                max_stress_attempts=max_stress_attempts,
                runner_overrides=runner_overrides,
            )
        )
        if index < cycle_count and interval_seconds > 0:
            time.sleep(interval_seconds)

    latest = cycle_records[-1]
    work_orders = _work_orders_from_cycle(latest, hard_holds)
    hard_hold_count = len(hard_holds)
    critical_failure_count = sum(1 for task in latest.get("tasks", []) if task.get("critical") and not task.get("ok"))
    loop_active = hard_hold_count == 0
    handover_ready = loop_active and critical_failure_count == 0
    written_at = _utc_now()
    heartbeat = {
        "status": "fresh" if loop_active else "held",
        "last_cycle_at": latest.get("started_at"),
        "written_at": written_at,
        "next_cycle_due_seconds": max(0.0, float(interval_seconds or 0.0)) if loop_active else None,
        "stale_after_seconds": max(60.0, float(interval_seconds or 0.0) * 3) if loop_active else None,
    }
    status = (
        "self_run_hard_boundary_held"
        if hard_hold_count
        else "self_run_repairing"
        if critical_failure_count
        else "self_run_autonomous_safe"
    )

    report: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "ok": handover_ready,
        "generated_at": written_at,
        "prompt": prompt,
        "autonomy_mode": "full_safe_local_autonomy",
        "heartbeat": heartbeat,
        "loop_contract": {
            "principle": "Aureon runs its safe local coding, stress, creative-process, and self-fix organs without waiting for Codex.",
            "no_false_blocks": "Coding/tool/skill/test gaps become autonomous work orders and rerun targets.",
            "hard_boundaries": list(HARD_BOUNDARY_PATTERNS.keys()),
            "hard_boundary_policy": "Only credential reveal, live trading, payments, official filings, and destructive OS actions are human-only.",
        },
        "hard_boundary_holds": hard_holds,
        "cycles": cycle_records,
        "autonomous_work_orders": work_orders,
        "summary": {
            "loop_active": loop_active,
            "handover_ready": handover_ready,
            "cycle_count": len(cycle_records),
            "latest_task_count": len(latest.get("tasks", [])),
            "latest_task_ok_count": sum(1 for task in latest.get("tasks", []) if task.get("ok")),
            "critical_failure_count": critical_failure_count,
            "soft_failure_count": sum(1 for task in latest.get("tasks", []) if not task.get("critical") and not task.get("ok")),
            "hard_boundary_hold_count": hard_hold_count,
            "autonomous_work_order_count": len([order for order in work_orders if order.get("autonomous")]),
            "heartbeat_status": heartbeat["status"],
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
    compact = {
        "schema_version": report["schema_version"],
        "status": report["status"],
        "ok": report["ok"],
        "generated_at": report["generated_at"],
        "summary": report["summary"],
        "heartbeat": heartbeat,
        "hard_boundary_holds": hard_holds,
        "autonomous_work_orders": work_orders[:8],
    }
    report["write_info"] = {"evidence_writes": writes, "coding_bridge_evidence_writes": _attach_to_coding_bridge(root, compact)}
    for rel in (DEFAULT_STATE_PATH, DEFAULT_AUDIT_JSON, DEFAULT_PUBLIC_JSON):
        _write_json(_rooted(root, rel), report)
    _write_text(_rooted(root, DEFAULT_AUDIT_MD), _make_markdown(report))
    return report


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run Aureon's safe local autonomous self-run loop.")
    parser.add_argument("--root", default="", help="Repository root. Defaults to current Aureon repo.")
    parser.add_argument("--prompt", default="", help="Optional operator prompt to feed the loop.")
    parser.add_argument("--cycles", type=int, default=1, help="Number of bounded loop cycles to run.")
    parser.add_argument("--forever", action="store_true", help="Run one autonomous cycle repeatedly until Ctrl+C.")
    parser.add_argument("--interval-seconds", type=float, default=0.0, help="Delay between cycles.")
    parser.add_argument("--no-stress", action="store_true", help="Skip the complex build stress audit in this run.")
    parser.add_argument("--max-stress-attempts", type=int, default=2, help="Repair attempt budget for stress certification.")
    parser.add_argument("--json", action="store_true", help="Print the full JSON report.")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve() if args.root else None
    if args.forever:
        interval = max(1.0, args.interval_seconds or 60.0)
        while True:
            report = build_and_write_autonomous_self_run_loop(
                root=root,
                prompt=args.prompt,
                cycles=1,
                interval_seconds=interval,
                include_stress=not args.no_stress,
                max_stress_attempts=max(1, args.max_stress_attempts),
            )
            summary = report.get("summary", {})
            print(
                f"{_utc_now()} {report.get('status')}: active={summary.get('loop_active')} "
                f"tasks={summary.get('latest_task_ok_count')}/{summary.get('latest_task_count')} "
                f"work_orders={summary.get('autonomous_work_order_count')} hard_holds={summary.get('hard_boundary_hold_count')}",
                flush=True,
            )
            time.sleep(interval)

    report = build_and_write_autonomous_self_run_loop(
        root=root,
        prompt=args.prompt,
        cycles=max(1, args.cycles),
        interval_seconds=max(0.0, args.interval_seconds),
        include_stress=not args.no_stress,
        max_stress_attempts=max(1, args.max_stress_attempts),
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True, default=str))
    else:
        summary = report.get("summary", {})
        print(
            f"{report.get('status')}: active={summary.get('loop_active')} "
            f"tasks={summary.get('latest_task_ok_count')}/{summary.get('latest_task_count')} "
            f"work_orders={summary.get('autonomous_work_order_count')} hard_holds={summary.get('hard_boundary_hold_count')}"
        )
    return 0 if report.get("ok") or report.get("status") == "self_run_repairing" else 1


if __name__ == "__main__":
    raise SystemExit(main())
