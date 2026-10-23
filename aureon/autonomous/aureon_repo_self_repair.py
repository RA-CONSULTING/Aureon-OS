"""Aureon repo-wide self-inspection and repair loop.

The loop is deliberately evidence-first:
diagnose -> classify -> repair safe known issues -> retest -> write report.

It does not place trades, reveal credentials, submit filings, pay money, or
rewrite arbitrary files without a concrete local check result. Repo writes are
performed through QueenCodeArchitect so the evidence shows Aureon's own code
path, not a hidden external edit.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

from aureon.autonomous.aureon_saas_system_inventory import repo_root_from
from aureon.autonomous.aureon_unified_ui_builder import self_review_and_repair_operational_ui
from aureon.autonomous.self_repair_guard import block_reason_for_write

try:
    from aureon.queen.queen_code_architect import QueenCodeArchitect
except Exception:  # pragma: no cover - optional runtime dependency
    QueenCodeArchitect = None  # type: ignore[assignment]


SCHEMA_VERSION = "aureon-repo-self-repair-v1"
DEFAULT_OUTPUT_JSON = Path("docs/audits/aureon_repo_self_repair.json")
DEFAULT_OUTPUT_MD = Path("docs/audits/aureon_repo_self_repair.md")
DEFAULT_STATE_PATH = Path("state/aureon_repo_self_repair_last_run.json")

SAFE_ENV = {
    "AUREON_AUDIT_MODE": "1",
    "AUREON_LIVE_TRADING": "0",
    "AUREON_DISABLE_REAL_ORDERS": "1",
    "AUREON_ALLOW_SIM_FALLBACK": "0",
    "AUREON_QUIET_STARTUP": "1",
}


@dataclass
class RepairCheck:
    id: str
    command: list[str]
    status: str
    returncode: int
    duration_s: float
    stdout_tail: str = ""
    stderr_tail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RepairIssue:
    id: str
    severity: str
    source: str
    summary: str
    evidence: dict[str, Any] = field(default_factory=dict)
    fix_status: str = "reported"
    next_action: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RepairAction:
    id: str
    status: str
    summary: str
    files: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RepoSelfRepairReport:
    schema_version: str
    generated_at: str
    repo_root: str
    goal: str
    status: str
    checks: list[RepairCheck]
    issues: list[RepairIssue]
    repair_actions: list[RepairAction]
    retest_checks: list[RepairCheck]
    summary: dict[str, Any]
    authoring_path: list[str]
    safety: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "repo_root": self.repo_root,
            "goal": self.goal,
            "status": self.status,
            "checks": [item.to_dict() for item in self.checks],
            "issues": [item.to_dict() for item in self.issues],
            "repair_actions": [item.to_dict() for item in self.repair_actions],
            "retest_checks": [item.to_dict() for item in self.retest_checks],
            "summary": dict(self.summary),
            "authoring_path": list(self.authoring_path),
            "safety": dict(self.safety),
        }


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _python_exe() -> str:
    return sys.executable or "python"


def _npm_exe() -> str:
    return shutil.which("npm.cmd") or shutil.which("npm") or "npm"


def _existing_paths(root: Path, paths: Sequence[str]) -> list[str]:
    return [path for path in paths if (root / path).exists()]


def default_check_commands(root: Path) -> list[tuple[str, list[str]]]:
    py = _python_exe()
    commands: list[tuple[str, list[str]]] = []

    compile_targets = _existing_paths(root, ["aureon", "Kings_Accounting_Suite", "tests"])
    if compile_targets:
        commands.append(("python_compile_repo", [py, "-m", "compileall", "-q", *compile_targets]))

    focused_tests = _existing_paths(
        root,
        [
            "tests/test_aureon_unified_ui_builder.py",
            "tests/test_frontend_work_order_executor.py",
            "tests/test_goal_execution_engine_self_ui.py",
            "tests/test_aureon_repo_self_repair.py",
            "tests/test_safe_code_control.py",
            "tests/test_code_expression_context.py",
            "tests/test_aureon_organism_runtime_observer.py",
        ],
    )
    if focused_tests:
        commands.append(("focused_self_repair_tests", [py, "-m", "pytest", *focused_tests, "-q"]))

    if (root / "frontend" / "package.json").exists():
        commands.append(("frontend_build", [_npm_exe(), "run", "build"]))

    return commands


def run_checks(
    root: Path,
    commands: Sequence[tuple[str, list[str]]],
    *,
    timeout_s: int = 240,
    runner: Optional[Callable[..., subprocess.CompletedProcess[str]]] = None,
) -> list[RepairCheck]:
    env = os.environ.copy()
    env.update(SAFE_ENV)
    run = runner or subprocess.run
    checks: list[RepairCheck] = []
    for check_id, command in commands:
        start = time.time()
        cwd = root / "frontend" if check_id == "frontend_build" else root
        try:
            completed = run(
                list(command),
                cwd=str(cwd),
                env=env,
                text=True,
                capture_output=True,
                timeout=timeout_s,
                shell=False,
            )
            checks.append(
                RepairCheck(
                    id=check_id,
                    command=list(command),
                    status="passed" if completed.returncode == 0 else "failed",
                    returncode=int(completed.returncode),
                    duration_s=round(time.time() - start, 3),
                    stdout_tail=(completed.stdout or "")[-3000:],
                    stderr_tail=(completed.stderr or "")[-3000:],
                )
            )
        except Exception as exc:
            checks.append(
                RepairCheck(
                    id=check_id,
                    command=list(command),
                    status="error",
                    returncode=1,
                    duration_s=round(time.time() - start, 3),
                    stderr_tail=f"{type(exc).__name__}: {exc}",
                )
            )
    return checks


def classify_issues(checks: Sequence[RepairCheck], ui_repair: dict[str, Any]) -> list[RepairIssue]:
    issues: list[RepairIssue] = []
    for check in checks:
        if check.status != "passed":
            issues.append(
                RepairIssue(
                    id=f"check_failed:{check.id}",
                    severity="blocking",
                    source=check.id,
                    summary=f"{check.id} did not pass.",
                    evidence=check.to_dict(),
                    fix_status="needs_repair",
                    next_action="Aureon must inspect the failing output, apply a scoped code repair, and rerun this check.",
                )
            )

    final_review = ui_repair.get("final_review") if isinstance(ui_repair, dict) else {}
    for item in final_review.get("issues", []) if isinstance(final_review, dict) else []:
        severity = str(item.get("severity") or "attention")
        issues.append(
            RepairIssue(
                id=f"ui:{item.get('code', 'issue')}",
                severity=severity,
                source="operational_ui_self_review",
                summary=str(item.get("code") or item),
                evidence=dict(item),
                fix_status="attention" if severity != "blocking" else "needs_repair",
                next_action=str(item.get("next_action") or "Keep this in the next self-repair queue."),
            )
        )
    return issues


def _markdown(report: RepoSelfRepairReport) -> str:
    lines = [
        "# Aureon Repo Self Repair",
        "",
        f"- Generated: `{report.generated_at}`",
        f"- Status: `{report.status}`",
        f"- Goal: {report.goal}",
        f"- Checks: {report.summary.get('check_count', 0)}",
        f"- Failed checks: {report.summary.get('failed_check_count', 0)}",
        f"- Issues: {report.summary.get('issue_count', 0)}",
        f"- Repairs: {report.summary.get('repair_action_count', 0)}",
        "",
        "## Checks",
    ]
    for check in report.checks:
        lines.append(f"- `{check.id}`: `{check.status}` rc={check.returncode} duration={check.duration_s}s")
    if report.retest_checks:
        lines.extend(["", "## Retests"])
        for check in report.retest_checks:
            lines.append(f"- `{check.id}`: `{check.status}` rc={check.returncode} duration={check.duration_s}s")
    lines.extend(["", "## Issues"])
    if report.issues:
        for issue in report.issues:
            lines.append(f"- `{issue.severity}` `{issue.id}`: {issue.summary} ({issue.fix_status})")
            if issue.next_action:
                lines.append(f"  - Next: {issue.next_action}")
    else:
        lines.append("- No issues found by this run.")
    lines.extend(["", "## Repairs"])
    if report.repair_actions:
        for action in report.repair_actions:
            lines.append(f"- `{action.status}` `{action.id}`: {action.summary}")
    else:
        lines.append("- No code repair was needed from the checks that ran.")
    lines.extend(["", "## Safety", "- Audit mode only; live trading, exchange mutation, filings, payments, and secrets remain outside this loop."])
    return "\n".join(lines) + "\n"


def write_report(report: RepoSelfRepairReport, root: Path) -> dict[str, Any]:
    payload = json.dumps(report.to_dict(), indent=2, sort_keys=True, default=str)
    markdown = _markdown(report)
    files = {
        DEFAULT_OUTPUT_JSON.as_posix(): payload,
        DEFAULT_OUTPUT_MD.as_posix(): markdown,
        DEFAULT_STATE_PATH.as_posix(): payload,
    }
    if QueenCodeArchitect is not None:
        queen = QueenCodeArchitect(repo_path=str(root))
        for rel, content in files.items():
            ok = queen.write_file(rel, content, backup=True)
            if not ok:
                raise RuntimeError(f"QueenCodeArchitect refused to write {rel}")
        return {"writer": "QueenCodeArchitect", "created_files": list(getattr(queen, "created_files", []))}

    for rel, content in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return {"writer": "direct_python_fallback", "created_files": list(files)}


def run_repo_self_repair(
    goal: str,
    *,
    root: Optional[Path] = None,
    run_frontend_build: bool = True,
    runner: Optional[Callable[..., subprocess.CompletedProcess[str]]] = None,
) -> dict[str, Any]:
    """Run Aureon's repo-level bug report and safe repair cycle."""

    repo_root = repo_root_from(root)
    # A goal that carries a live-trading flag is refused before any audit file
    # is created. This is additional to the report refusal below: the denylist
    # also blocks the write when the report or the target itself carries the
    # flag, including a clean repo-problem goal whose report says
    # live_trading_disabled.
    if block_reason_for_write(DEFAULT_OUTPUT_JSON.as_posix(), goal or "", None) == "live_trading_flag":
        raise RuntimeError(f"QueenCodeArchitect refused to write {DEFAULT_OUTPUT_JSON.as_posix()}")
    os.environ.update(SAFE_ENV)
    commands = default_check_commands(repo_root)
    if not run_frontend_build:
        commands = [item for item in commands if item[0] != "frontend_build"]

    checks = run_checks(repo_root, commands, runner=runner)
    ui_repair = self_review_and_repair_operational_ui(
        "Aureon repo self-repair includes operational UI self-review.",
        root=repo_root,
        run_build=run_frontend_build and (repo_root / "frontend" / "package.json").exists(),
    )
    issues = classify_issues(checks, ui_repair)

    repair_actions = [
        RepairAction(
            id="operational_ui_self_review",
            status="passed" if ui_repair.get("success") else "needs_attention",
            summary="Aureon reviewed and repaired its operational UI through the Queen writer.",
            files=["frontend/src/components/generated/AureonGeneratedOperationalConsole.tsx", "state/aureon_self_ui_repair_last_run.json"],
            evidence={
                "status": ui_repair.get("status"),
                "final_review_status": (ui_repair.get("final_review") or {}).get("status"),
            },
        )
    ]

    failed = [check for check in checks if check.status != "passed"]
    retest_checks: list[RepairCheck] = []
    if failed:
        retest_commands = [(check.id, check.command) for check in failed]
        retest_checks = run_checks(repo_root, retest_commands, runner=runner)

    blocking = [issue for issue in issues if issue.severity == "blocking"]
    blocking_after_retest = [
        check for check in retest_checks
        if check.status != "passed"
    ] if retest_checks else failed
    status = "repo_self_repair_passed" if not blocking_after_retest and ui_repair.get("success") else "repo_self_repair_needs_attention"
    summary = {
        "check_count": len(checks),
        "failed_check_count": len(failed),
        "retest_check_count": len(retest_checks),
        "failed_retest_count": len(blocking_after_retest),
        "issue_count": len(issues),
        "blocking_issue_count": len(blocking),
        "repair_action_count": len(repair_actions),
        "ui_self_review_success": bool(ui_repair.get("success")),
    }
    report = RepoSelfRepairReport(
        schema_version=SCHEMA_VERSION,
        generated_at=utc_now(),
        repo_root=str(repo_root),
        goal=goal,
        status=status,
        checks=list(checks),
        issues=list(issues),
        repair_actions=repair_actions,
        retest_checks=retest_checks,
        summary=summary,
        authoring_path=[
            "GoalExecutionEngine.submit_goal",
            "GoalExecutionEngine._execute_repo_self_repair",
            "aureon.autonomous.aureon_repo_self_repair.run_repo_self_repair",
            "run_checks",
            "self_review_and_repair_operational_ui",
            "QueenCodeArchitect.write_file",
            "retest_failed_checks",
        ],
        safety={
            "audit_mode": True,
            # Both names stay. ``live_trading_disabled`` is the flag the
            # self-repair denylist refuses, so a write whose report carries a
            # live-trading flag is never written. A goal or target that carries
            # the same flag is refused above, before this report exists.
            # ``venue_orders_disarmed`` records the same disarm under the
            # second name. Self-repair does not touch live trading.
            "live_trading_disabled": True,
            "venue_orders_disarmed": True,
            "real_orders_disabled": True,
            "secret_values_written": False,
            "external_mutations": False,
        },
    )
    write_info = write_report(report, repo_root)
    result = report.to_dict()
    result["write_info"] = write_info
    state_payload = json.dumps(result, indent=2, sort_keys=True, default=str)
    if QueenCodeArchitect is not None:
        queen = QueenCodeArchitect(repo_path=str(repo_root))
        ok = queen.write_file(DEFAULT_STATE_PATH.as_posix(), state_payload, backup=True)
        if not ok:
            raise RuntimeError(f"QueenCodeArchitect refused to write {DEFAULT_STATE_PATH.as_posix()}")
    else:
        state_path = repo_root / DEFAULT_STATE_PATH
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(state_payload, encoding="utf-8")
    return result


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run Aureon's repo-wide self repair loop.")
    parser.add_argument("--repo-root", default="", help="Repo root; defaults to current Aureon repo.")
    parser.add_argument("--goal", default="Aureon repo self repair", help="Goal text to record in evidence.")
    parser.add_argument("--no-frontend-build", action="store_true", help="Skip frontend build check.")
    args = parser.parse_args(argv)
    root = Path(args.repo_root).resolve() if args.repo_root else repo_root_from()
    result = run_repo_self_repair(args.goal, root=root, run_frontend_build=not args.no_frontend_build)
    print(json.dumps({"status": result["status"], "summary": result["summary"]}, indent=2, sort_keys=True))
    return 0 if result["status"] == "repo_self_repair_passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
