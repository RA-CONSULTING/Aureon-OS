from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

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
DEFAULT_STATE_PATH = Path("state/aureon_autonomous_self_run_loop_last_run.json")
DEFAULT_AUDIT_JSON = Path("docs/audits/aureon_autonomous_self_run_loop.json")
DEFAULT_AUDIT_MD = Path("docs/audits/aureon_autonomous_self_run_loop.md")
DEFAULT_PUBLIC_JSON = Path("frontend/public/aureon_autonomous_self_run_loop.json")
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
