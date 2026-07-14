#!/usr/bin/env python3
"""
AUREON IGNITION -- One Switch. Everything Fires.

This is the master launcher. One command boots the entire Aureon operating
system: ThoughtBus, ChirpBus, Queen Hive Mind, Cortex brainwave layers,
Source Law consciousness funnel, Mycelium Mind, Metacognition mirror,
Sentient Loop, 60 queen modules, 50+ domain systems, Intelligence Engine,
Feed Hub, Whale Sonar, HFT Engine, Micro Profit Labyrinth, API Server,
and the autonomous trading loop.

    python scripts/aureon_ignition.py              # DRY-RUN mode
    python scripts/aureon_ignition.py --live        # LIVE TRADING
    python scripts/aureon_ignition.py --live --no-trade  # Boot only, no loop

The Queen boots first. All systems activate beneath her.
Then the trading loop runs until Ctrl+C.

Gary Leckey & Tina Brown | April 2026 | The Ignition Switch
"""

import os
import sys
import signal
import time
import logging
import argparse
import json
import importlib.util
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager

# ============================================================================
# PATH SETUP -- ensure all aureon modules are importable
# ============================================================================

_REPO_ROOT = Path(__file__).resolve().parents[1]
_AUREON_DIR = _REPO_ROOT / "aureon"

# Add repo root and all aureon subdirectories to sys.path
sys.path.insert(0, str(_REPO_ROOT))
for sub in sorted(_AUREON_DIR.iterdir()):
    if sub.is_dir() and not sub.name.startswith(("_", ".")):
        p = str(sub)
        if p not in sys.path:
            sys.path.insert(0, p)

# Ensure scripts/ is in path for legacy runners
_SCRIPTS = _REPO_ROOT / "scripts"
if _SCRIPTS.exists():
    for sub in sorted(_SCRIPTS.iterdir()):
        if sub.is_dir() and not sub.name.startswith(("_", ".")):
            p = str(sub)
            if p not in sys.path:
                sys.path.insert(0, p)

os.chdir(str(_REPO_ROOT))  # Runtime JSONs live at repo root

from aureon.core.aureon_runtime_safety import (
    apply_safe_runtime_environment,
    apply_live_runtime_environment,
    env_truthy,
    live_block_reason,
    real_orders_allowed,
    runtime_mode_snapshot,
)
from aureon.core.aureon_env import (
    EXCHANGE_REQUIRED_ENV,
    KRAKEN_REQUIRED_ENV,
    enabled_credential_groups,
    env_presence,
    env_status_summary,
    load_aureon_environment,
    missing_env,
)


# ============================================================================
# LOGGING
# ============================================================================

def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    logging.basicConfig(level=level, format=fmt, datefmt="%H:%M:%S")
    # Quiet down noisy libraries
    for name in ("urllib3", "asyncio", "websockets", "httpx"):
        logging.getLogger(name).setLevel(logging.WARNING)


# ============================================================================
# BANNER
# ============================================================================

def print_banner():
    print("""
================================================================================

     A U R E O N   I G N I T I O N

     One switch. Everything fires.
     The Queen boots first. All systems activate beneath her.

     "We don't need data centers. We have the quantum space."
                                    -- Gary Leckey, April 2026

================================================================================
""")


# ============================================================================
# RUNTIME PROFILE + PREFLIGHT AUDIT
# ============================================================================

IGNITION_AUDIT_JSON = _REPO_ROOT / "docs" / "audits" / "ignition_live_boot_audit.json"
IGNITION_AUDIT_MD = _REPO_ROOT / "docs" / "audits" / "ignition_live_boot_audit.md"

PREFLIGHT_IMPORTS = (
    ("runtime_safety", "aureon.core.aureon_runtime_safety", True),
    ("queen_layer", "queen_layer", True),
    ("goal_capability_map", "aureon.autonomous.aureon_goal_capability_map", True),
    ("self_questioning_ai", "aureon.autonomous.aureon_self_questioning_ai", True),
    ("capability_growth_loop", "aureon.autonomous.aureon_capability_growth_loop", True),
    ("accounting_context_bridge", "aureon.queen.accounting_context_bridge", True),
    ("dynamic_margin_sizer", "aureon.trading.dynamic_margin_sizer", False),
    ("temporal_trade_cognition", "aureon.trading.temporal_trade_cognition", False),
    ("unified_margin_brain", "aureon.trading.unified_margin_brain", False),
    ("micro_profit_labyrinth", "aureon.trading.micro_profit_labyrinth", True),
)


def configure_ignition_runtime(live: bool) -> dict:
    """Apply the process-wide runtime profile before importing live systems."""
    if live:
        apply_live_runtime_environment(os.environ)
    else:
        apply_safe_runtime_environment(os.environ)
    return runtime_mode_snapshot(os.environ)


def _preflight_check(name: str, ok: bool, detail: str = "", required: bool = False) -> dict:
    return {
        "name": name,
        "ok": bool(ok),
        "required": bool(required),
        "detail": str(detail or ""),
    }


def _import_check(label: str, module_name: str, required: bool) -> dict:
    try:
        spec = importlib.util.find_spec(module_name)
        if spec is None:
            return _preflight_check(
                f"import:{label}",
                False,
                f"{module_name}: module spec not found",
                required,
            )
        origin = spec.origin or module_name
        return _preflight_check(f"import:{label}", True, origin, required)
    except Exception as exc:
        return _preflight_check(
            f"import:{label}",
            False,
            f"{module_name}: {type(exc).__name__}: {exc}"[:240],
            required,
        )


def _package_check(module_name: str, required: bool = True) -> dict:
    try:
        spec = importlib.util.find_spec(module_name)
        return _preflight_check(
            f"package:{module_name}",
            spec is not None,
            spec.origin if spec is not None else "module spec not found",
            required,
        )
    except Exception as exc:
        return _preflight_check(
            f"package:{module_name}",
            False,
            f"{type(exc).__name__}: {exc}"[:240],
            required,
        )


def _accounting_status_snapshot() -> dict:
    try:
        from aureon.queen.accounting_context_bridge import get_accounting_context_bridge

        bridge = get_accounting_context_bridge()
        return bridge.status()
    except Exception as exc:
        return {"available": False, "error": f"{type(exc).__name__}: {exc}"[:240]}


def _accounting_preflight_checks() -> tuple[list[dict], dict]:
    checks = []
    suite_dir = _REPO_ROOT / "Kings_Accounting_Suite"
    checks.append(
        _preflight_check(
            "accounting_suite_path",
            suite_dir.exists(),
            str(suite_dir),
            True,
        )
    )
    for package in ("reportlab", "pypdf", "openpyxl"):
        checks.append(_package_check(package, required=False))

    status = _accounting_status_snapshot()
    combined = status.get("combined_bank_data") or {}
    registry = status.get("accounting_system_registry") or {}
    readiness = status.get("accounting_readiness") or {}
    statutory = status.get("statutory_filing_pack") or {}
    raw_summary = ((status.get("raw_data_manifest") or {}).get("summary") or {})
    swarm_scan = status.get("swarm_raw_data_wave_scan") or {}
    swarm_benchmark = swarm_scan.get("benchmark") or {}
    swarm_consensus = ((swarm_scan.get("waves") or {}).get("phi_swarm_consensus") or {})
    end_user_confirmation = status.get("end_user_confirmation") or {}
    confirmation_payload = end_user_confirmation.get("confirmation") or end_user_confirmation
    workflow = status.get("autonomous_workflow") or {}
    cognitive = workflow.get("cognitive_review") or status.get("cognitive_review") or {}
    vault_memory = workflow.get("vault_memory") or status.get("vault_memory") or {}
    handoff_pack = status.get("human_filing_handoff_pack") or workflow.get("human_filing_handoff_pack") or {}
    handoff_readiness = handoff_pack.get("readiness") or {}
    evidence_authoring = (
        status.get("accounting_evidence_authoring")
        or handoff_pack.get("accounting_evidence_authoring")
        or workflow.get("accounting_evidence_authoring")
        or {}
    )
    evidence_summary = evidence_authoring.get("summary") or {}
    llm_authoring = evidence_authoring.get("llm_document_authoring") or evidence_summary.get("llm_document_authoring") or {}
    end_user = status.get("end_user_accounting_automation") or {}
    end_user_coverage = end_user.get("requirement_coverage") or []
    end_user_generated = sum(1 for item in end_user_coverage if str(item.get("status", "")).startswith("generated"))
    uk_brain = (
        status.get("uk_accounting_requirements_brain")
        or handoff_pack.get("uk_accounting_requirements_brain")
        or workflow.get("uk_accounting_requirements_brain")
        or {}
    )
    uk_summary = uk_brain.get("summary") or {}
    uk_figures = uk_brain.get("figures") or {}
    checks.append(
        _preflight_check(
            "accounting_context_status",
            bool(status.get("available", True)) and not status.get("error"),
            (
                f"company={status.get('company_number', 'unknown')} "
                f"build={status.get('accounts_build_status', 'unknown')} "
                f"overdue={status.get('overdue_count', 0)} "
                f"manual_filing={status.get('manual_filing_required', True)} "
                f"bank_sources={combined.get('transaction_source_count', combined.get('csv_source_count', 0))} "
                f"csv_sources={combined.get('csv_source_count', 0)} "
                f"pdf_sources={combined.get('pdf_source_count', 0)} "
                f"unique_bank_rows={combined.get('unique_rows_in_period', 0)} "
                f"duplicates_removed={combined.get('duplicate_rows_removed', 0)} "
                f"accounting_tools={registry.get('module_count', 0)} "
                f"ready={readiness.get('ready', 'unknown')} "
                f"statutory_outputs={len(statutory.get('outputs') or {})} "
                f"raw_files={raw_summary.get('file_count', 0)} "
                f"swarm_files={swarm_benchmark.get('files_scanned', 0)} "
                f"swarm_consensus={swarm_consensus.get('status', 'unknown')} "
                f"end_user_confirmed={len(confirmation_payload.get('what_aureon_confirmed') or [])} "
                f"autonomous_workflow={workflow.get('status', 'unknown')} "
                f"handoff={handoff_pack.get('status', 'unknown')} "
                f"evidence_requests={evidence_summary.get('draft_count', 0)} "
                f"evidence_docs={evidence_summary.get('generated_document_count', 0)} "
                f"llm_docs={llm_authoring.get('completed_count', 0)} "
                f"llm_status={llm_authoring.get('status', 'unknown')} "
                f"end_user={end_user.get('status', 'unknown')} "
                f"end_user_coverage={end_user_generated}/{len(end_user_coverage)} "
                f"uk_requirements={uk_summary.get('requirement_count', 0)} "
                f"uk_questions={uk_summary.get('question_count', 0)} "
                f"vault_memory={vault_memory.get('status', 'unknown')} "
                f"self_questioning={cognitive.get('status', 'unknown')}"
            )
            if not status.get("error")
            else status.get("error", ""),
            False,
        )
    )
    checks.append(
        _preflight_check(
            "accounting_system_registry",
            bool(registry) and not registry.get("error"),
            (
                f"modules={registry.get('module_count', 0)} "
                f"artifacts={registry.get('artifact_count', 0)} "
                f"domains={len(registry.get('domain_counts') or {})}"
            )
            if not registry.get("error")
            else registry.get("error", ""),
            False,
        )
    )
    checks.append(
        _preflight_check(
            "accounting_readiness",
            bool(readiness.get("ready")),
            (
                f"ready_for={readiness.get('ready_for', 'unknown')} "
                f"required_failures={len(readiness.get('required_failures') or [])} "
                f"bank_sources={readiness.get('bank_sources', 0)} "
                f"statutory_outputs={readiness.get('statutory_outputs', 0)}"
            ),
            False,
        )
    )
    checks.append(
        _preflight_check(
            "accounting_statutory_pack",
            bool(statutory and statutory.get("outputs")),
            (
                f"generated_at={statutory.get('generated_at', 'unknown')} "
                f"outputs={len(statutory.get('outputs') or {})} "
                "manual_filing_required=True"
            ),
            False,
        )
    )
    checks.append(
        _preflight_check(
            "accounting_raw_data_intake",
            bool(raw_summary.get("file_count", 0)),
            (
                f"files={raw_summary.get('file_count', 0)} "
                f"transaction_sources={raw_summary.get('transaction_source_count', 0)} "
                f"evidence_only={raw_summary.get('evidence_only_count', 0)}"
            ),
            False,
        )
    )
    checks.append(
        _preflight_check(
            "accounting_swarm_raw_data_wave_scan",
            swarm_scan.get("status") == "completed" and bool(swarm_benchmark.get("files_scanned", 0)),
            (
                f"files={swarm_benchmark.get('files_scanned', 0)} "
                f"duration={swarm_benchmark.get('total_duration_seconds', 0)} "
                f"files_per_second={swarm_benchmark.get('files_per_second', 0)} "
                f"consensus={swarm_consensus.get('status', 'unknown')} "
                f"score={swarm_consensus.get('score', 'n/a')}"
            ),
            False,
        )
    )
    checks.append(
        _preflight_check(
            "accounting_end_user_confirmation_feed",
            bool(confirmation_payload.get("what_aureon_confirmed") or confirmation_payload.get("status")),
            (
                f"status={end_user_confirmation.get('status', confirmation_payload.get('status', 'unknown'))} "
                f"confirmed={len(confirmation_payload.get('what_aureon_confirmed') or [])} "
                f"attention={len(confirmation_payload.get('attention_items') or [])}"
            ),
            False,
        )
    )
    checks.append(
        _preflight_check(
            "accounting_uk_requirements_brain",
            bool(uk_brain and uk_summary.get("requirement_count", 0) and uk_summary.get("question_count", 0)),
            (
                f"status={uk_brain.get('status', 'unknown')} "
                f"requirements={uk_summary.get('requirement_count', 0)} "
                f"questions={uk_summary.get('question_count', 0)} "
                f"unresolved={uk_summary.get('unresolved_question_count', 0)} "
                f"vat_over_threshold={uk_figures.get('turnover_over_vat_threshold', 'unknown')}"
            ),
            False,
        )
    )
    checks.append(
        _preflight_check(
            "accounting_evidence_authoring",
            bool(evidence_authoring and evidence_authoring.get("outputs")),
            (
                f"status={evidence_authoring.get('status', 'unknown')} "
                f"requests={evidence_summary.get('draft_count', 0)} "
                f"documents={evidence_summary.get('generated_document_count', 0)} "
                f"petty_cash={evidence_summary.get('petty_cash_withdrawal_count', 0)} "
                f"llm_status={llm_authoring.get('status', 'unknown')} "
                f"llm_docs={llm_authoring.get('completed_count', 0)} "
                "internal_support_documents_only"
            ),
            False,
        )
    )
    checks.append(
        _preflight_check(
            "accounting_end_user_automation",
            bool(end_user and end_user_coverage),
            (
                f"status={end_user.get('status', 'unknown')} "
                f"coverage={end_user_generated}/{len(end_user_coverage)} "
                f"start_here={(end_user.get('outputs') or {}).get('end_user_start_here', 'not found')} "
                "manual_filing_required=True"
            ),
            False,
        )
    )
    source_files = status.get("source_files") or {}
    for key in (
        "full_run_manifest",
        "full_run_summary",
        "compliance_audit_json",
        "period_manifest",
        "statutory_manifest",
        "raw_data_manifest",
        "accounting_evidence_authoring_manifest",
        "accounting_evidence_requests_csv",
        "uk_accounting_requirements_brain_json",
        "accountant_self_questions_markdown",
        "end_user_accounting_automation_manifest",
        "end_user_accounting_automation_start_here",
        "end_user_confirmation_markdown",
        "end_user_confirmation_json",
        "internal_logic_chain_checklist_markdown",
        "internal_logic_chain_checklist_json",
        "swarm_raw_data_wave_scan_markdown",
        "swarm_raw_data_wave_scan_json",
    ):
        checks.append(
            _preflight_check(
                f"accounting_artifact:{key}",
                bool(source_files.get(key)),
                source_files.get(key, "not found"),
                False,
            )
        )
    return checks, status


@contextmanager
def _suppress_import_side_effects():
    previous = os.environ.get("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS")
    os.environ["AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS"] = "1"
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", None)
        else:
            os.environ["AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS"] = previous


def build_ignition_audit(live: bool, no_trade: bool = False, env_report: dict | None = None) -> dict:
    """Build a live-boot audit without starting trading."""
    checks = []
    env = runtime_mode_snapshot(os.environ)
    env_report = env_report or load_aureon_environment(_REPO_ROOT).to_dict()
    kraken_presence = env_presence(KRAKEN_REQUIRED_ENV)
    credential_groups = enabled_credential_groups()
    if live and not credential_groups and not no_trade:
        credential_groups = {"kraken": KRAKEN_REQUIRED_ENV}
    credential_presence = {
        name: env_presence(keys)
        for name, keys in credential_groups.items()
    }

    if live:
        reason = live_block_reason("Ignition")
        checks.append(_preflight_check("live_order_runtime", reason is None, reason or "real_orders_allowed=True", True))
        checks.append(_preflight_check("audit_mode_off", os.getenv("AUREON_AUDIT_MODE") == "0", "AUREON_AUDIT_MODE=0", True))
        checks.append(_preflight_check("dry_run_off", os.getenv("DRY_RUN") == "0" and os.getenv("AUREON_DRY_RUN") == "0", "DRY_RUN=0/AUREON_DRY_RUN=0", True))
        checks.append(_preflight_check("exchange_dry_run_off", os.getenv("KRAKEN_DRY_RUN") == "false" and os.getenv("BINANCE_DRY_RUN") == "false" and os.getenv("ALPACA_DRY_RUN") == "false", "Kraken/Binance/Alpaca dry-run flags false", True))
        checks.append(_preflight_check("confirm_live_set", os.getenv("CONFIRM_LIVE", "").lower() == "yes", "CONFIRM_LIVE=yes", True))
        checks.append(_preflight_check("llm_live_capabilities_on", env_truthy("AUREON_LLM_LIVE_CAPABILITIES"), "LLM may reason with live state", True))
        checks.append(_preflight_check("cognitive_live_mode_on", env_truthy("AUREON_COGNITIVE_LIVE_MODE"), "cognitive systems may reason with live state", True))
        checks.append(_preflight_check("llm_no_direct_order_authority", os.getenv("AUREON_LLM_ORDER_AUTHORITY") == "0", "LLM cannot directly place orders", True))
        checks.append(_preflight_check("cognitive_no_direct_order_authority", os.getenv("AUREON_COGNITIVE_ORDER_AUTHORITY") == "0", "cognitive layer cannot bypass execution gates", True))
        if env_truthy("AUREON_ORDER_INTENT_PUBLISH"):
            checks.append(_preflight_check(
                "cognitive_order_intent_authority",
                os.getenv("AUREON_ORDER_AUTHORITY_MODE") == "intent_only_runtime_gated",
                "cognition may publish live order intents; exchange mutation remains runtime-gated",
                True,
            ))
        for exchange, required_keys in credential_groups.items():
            missing_keys = missing_env(required_keys)
            env_detail = (
                f"{env_status_summary(required_keys)}; "
                f"loaded_env={', '.join(env_report.get('loaded_paths') or []) or 'none'}"
            )
            checks.append(
                _preflight_check(
                    f"{exchange}_credentials_present",
                    not missing_keys,
                    env_detail,
                    not no_trade,
                )
            )
    else:
        checks.append(_preflight_check("dry_runtime", not real_orders_allowed(), "dry-run/audit profile active", True))

    goal_map = {}
    accounting_status = {}
    with _suppress_import_side_effects():
        for label, module_name, required in PREFLIGHT_IMPORTS:
            checks.append(_import_check(label, module_name, required))

        accounting_checks, accounting_status = _accounting_preflight_checks()
        checks.extend(accounting_checks)

        try:
            from aureon.autonomous.aureon_goal_capability_map import build_goal_capability_map

            goal_map = build_goal_capability_map(
                repo_root=_REPO_ROOT,
                current_goal="single ignition live boot",
            ).compact()
            checks.append(
                _preflight_check(
                    "goal_capability_map",
                    goal_map.get("directive_version") == "goal-capability-v1",
                    f"{goal_map.get('tool_registry', {}).get('count', 0)} tool/skill routes; "
                    f"{goal_map.get('organism', {}).get('node_count', 0)} organism nodes",
                    True,
                )
            )
        except Exception as exc:
            checks.append(_preflight_check("goal_capability_map", False, str(exc)[:240], True))

        try:
            from aureon.autonomous.aureon_capability_growth_loop import build_capability_growth_loop

            env_before_growth_probe = os.environ.copy()
            try:
                growth = build_capability_growth_loop(
                    _REPO_ROOT,
                    iterations=1,
                    run_checks=False,
                    author_skills=False,
                    queue_contracts=False,
                    max_gaps=8,
                )
            finally:
                os.environ.clear()
                os.environ.update(env_before_growth_probe)
            checks.append(
                _preflight_check(
                    "capability_growth_loop",
                    not growth.status.startswith("growth_loop_needs_repair"),
                    f"{growth.status}; gaps={growth.summary.get('latest_gap_count', 0)} "
                    f"mean_score={growth.summary.get('latest_mean_score', 0)}",
                    False,
                )
            )
        except Exception as exc:
            checks.append(_preflight_check("capability_growth_loop", False, str(exc)[:240], False))

    required_failures = [check for check in checks if check["required"] and not check["ok"]]
    return {
        "generated_at": datetime.now().isoformat(),
        "repo_root": str(_REPO_ROOT),
        "command": "python scripts/aureon_ignition.py --live" if live else "python scripts/aureon_ignition.py",
        "mode": "LIVE" if live else "DRY_RUN",
        "no_trade": bool(no_trade),
        "runtime_env": env,
        "env_files": env_report,
        "kraken_env": kraken_presence,
        "credential_groups": credential_presence,
        "known_exchange_credentials": {
            name: list(keys)
            for name, keys in EXCHANGE_REQUIRED_ENV.items()
        },
        "accounting": accounting_status,
        "real_orders_allowed": real_orders_allowed(),
        "goal_capability_map": goal_map,
        "checks": checks,
        "required_failures": required_failures,
        "ready": not required_failures,
    }


def write_ignition_audit(report: dict) -> None:
    IGNITION_AUDIT_JSON.parent.mkdir(parents=True, exist_ok=True)
    IGNITION_AUDIT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Aureon Ignition Live Boot Audit",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- Command: `{report['command']}`",
        f"- Mode: `{report['mode']}`",
        f"- Ready: `{report['ready']}`",
        f"- Real orders allowed by runtime: `{report['real_orders_allowed']}`",
        f"- Loaded env files: `{', '.join((report.get('env_files') or {}).get('loaded_paths') or []) or 'none'}`",
        f"- Accounting status: `{(report.get('accounting') or {}).get('accounts_build_status', 'unknown')}`; "
        f"manual filing required: `{(report.get('accounting') or {}).get('manual_filing_required', True)}`; "
        f"bank sources: `{((report.get('accounting') or {}).get('combined_bank_data') or {}).get('transaction_source_count', ((report.get('accounting') or {}).get('combined_bank_data') or {}).get('csv_source_count', 0))}`; "
        f"unique bank rows: `{((report.get('accounting') or {}).get('combined_bank_data') or {}).get('unique_rows_in_period', 0)}`; "
        f"accounting tools: `{((report.get('accounting') or {}).get('accounting_system_registry') or {}).get('module_count', 0)}`; "
        f"ready: `{((report.get('accounting') or {}).get('accounting_readiness') or {}).get('ready', 'unknown')}`; "
        f"statutory outputs: `{len(((report.get('accounting') or {}).get('statutory_filing_pack') or {}).get('outputs') or {})}`; "
        f"raw files: `{(((report.get('accounting') or {}).get('raw_data_manifest') or {}).get('summary') or {}).get('file_count', 0)}`; "
        f"swarm files: `{(((report.get('accounting') or {}).get('swarm_raw_data_wave_scan') or {}).get('benchmark') or {}).get('files_scanned', 0)}`; "
        f"swarm consensus: `{(((((report.get('accounting') or {}).get('swarm_raw_data_wave_scan') or {}).get('waves') or {}).get('phi_swarm_consensus') or {}).get('status', 'unknown'))}`",
        "",
        "## Checks",
        "",
        "| Check | Required | Status | Detail |",
        "| --- | --- | --- | --- |",
    ]
    for check in report["checks"]:
        detail = str(check.get("detail", "")).replace("|", "\\|")
        status = "PASS" if check.get("ok") else "FAIL"
        lines.append(f"| `{check['name']}` | `{check['required']}` | `{status}` | {detail} |")
    lines.append("")
    if report["required_failures"]:
        lines.append("## Required Failures")
        lines.append("")
        for check in report["required_failures"]:
            lines.append(f"- `{check['name']}`: {check['detail']}")
        lines.append("")
    IGNITION_AUDIT_MD.write_text("\n".join(lines), encoding="utf-8")


def require_ignition_ready(report: dict) -> None:
    if report.get("ready"):
        return
    details = "; ".join(f"{item['name']}: {item['detail']}" for item in report.get("required_failures", []))
    raise SystemExit(f"[IGNITION] Preflight failed: {details}")


def print_accounting_status(status: dict | None = None) -> None:
    status = status or _accounting_status_snapshot()
    print("[IGNITION] Accounting context:")
    if status.get("error"):
        print(f"   unavailable: {status['error']}")
        return
    print(f"   Company: {status.get('company_number', 'unknown')} {status.get('company_name', '')}")
    print(f"   Status:  {status.get('company_status') or 'unknown'}")
    print(f"   Period:  {status.get('period_start')} to {status.get('period_end')}")
    print(f"   Build:   {status.get('accounts_build_status')} at {status.get('generated_at') or 'unknown'}")
    print(f"   Overdue: {status.get('overdue_count', 0)}")
    print(f"   Manual filing required: {status.get('manual_filing_required', True)}")
    combined = status.get("combined_bank_data") or {}
    if combined:
        accounts = ", ".join(combined.get("source_accounts") or []) or "unknown"
        transaction_sources = combined.get("transaction_source_count", combined.get("csv_source_count", 0))
        print(
            "   Bank/account data: "
            f"{transaction_sources} transaction sources "
            f"({combined.get('csv_source_count', 0)} CSV, {combined.get('pdf_source_count', 0)} parsed PDF), "
            f"{combined.get('unique_rows_in_period', 0)} unique period rows, "
            f"{combined.get('duplicate_rows_removed', 0)} duplicate overlaps removed"
        )
        print(f"   Source accounts: {accounts}")
        source_summary = combined.get("source_provider_summary") or {}
        if source_summary:
            print(
                "   Source providers: "
                + ", ".join(f"{name}={info.get('rows', 0)}" for name, info in sorted(source_summary.items()))
            )
        flow_summary = combined.get("flow_provider_summary") or {}
        if flow_summary:
            print(
                "   Flow providers: "
                + ", ".join(f"{name}={info.get('rows', 0)}" for name, info in sorted(flow_summary.items()))
            )
    registry = status.get("accounting_system_registry") or {}
    if registry and not registry.get("error"):
        print(
            "   Accounting tools: "
            f"{registry.get('module_count', 0)} modules/tools, "
            f"{registry.get('artifact_count', 0)} artifacts"
        )
    readiness = status.get("accounting_readiness") or {}
    if readiness:
        print(
            "   Accounting readiness: "
            f"{readiness.get('ready')} "
            f"({len(readiness.get('required_failures') or [])} required failures)"
        )
    statutory = status.get("statutory_filing_pack") or {}
    if statutory:
        print(
            "   Companies House/HMRC support: "
            f"{len(statutory.get('outputs') or {})} outputs; "
            "official filing remains manual"
        )
    raw_summary = ((status.get("raw_data_manifest") or {}).get("summary") or {})
    if raw_summary:
        print(
            "   Raw data intake: "
            f"{raw_summary.get('file_count', 0)} files, "
            f"{raw_summary.get('transaction_source_count', 0)} transaction sources, "
            f"{raw_summary.get('evidence_only_count', 0)} evidence-only"
        )
    swarm_scan = status.get("swarm_raw_data_wave_scan") or {}
    if swarm_scan:
        benchmark = swarm_scan.get("benchmark") or {}
        consensus = ((swarm_scan.get("waves") or {}).get("phi_swarm_consensus") or {})
        print(
            "   Swarm raw-data wave scan: "
            f"{swarm_scan.get('status', 'unknown')} "
            f"files={benchmark.get('files_scanned', 0)} "
            f"benchmark={benchmark.get('total_duration_seconds', 0)}s "
            f"files_per_second={benchmark.get('files_per_second', 0)} "
            f"consensus={consensus.get('status', 'unknown')} "
            f"score={consensus.get('score', 'n/a')}"
        )
    workflow = status.get("autonomous_workflow") or {}
    if workflow:
        cognitive = workflow.get("cognitive_review") or status.get("cognitive_review") or {}
        vault_memory = workflow.get("vault_memory") or status.get("vault_memory") or {}
        handoff_pack = status.get("human_filing_handoff_pack") or workflow.get("human_filing_handoff_pack") or {}
        handoff_readiness = handoff_pack.get("readiness") or {}
        evidence_authoring = (
            status.get("accounting_evidence_authoring")
            or handoff_pack.get("accounting_evidence_authoring")
            or workflow.get("accounting_evidence_authoring")
            or {}
        )
        evidence_summary = evidence_authoring.get("summary") or {}
        llm_authoring = evidence_authoring.get("llm_document_authoring") or evidence_summary.get("llm_document_authoring") or {}
        uk_brain = (
            status.get("uk_accounting_requirements_brain")
            or handoff_pack.get("uk_accounting_requirements_brain")
            or workflow.get("uk_accounting_requirements_brain")
            or {}
        )
        uk_summary = uk_brain.get("summary") or {}
        uk_figures = uk_brain.get("figures") or {}
        print(
            "   Autonomous accounts workflow: "
            f"{workflow.get('status', 'unknown')} "
            f"({len(workflow.get('agent_tasks') or [])} agent tasks)"
        )
        print(
            "   Accounting evidence authoring: "
            f"{evidence_authoring.get('status', 'unknown')} "
            f"requests={evidence_summary.get('draft_count', 0)} "
            f"docs={evidence_summary.get('generated_document_count', 0)} "
            f"petty_cash={evidence_summary.get('petty_cash_withdrawal_count', 0)} "
            f"llm_status={llm_authoring.get('status', 'unknown')} "
            f"llm_docs={llm_authoring.get('completed_count', 0)} "
            "internal_support_documents_only"
        )
        print(
            "   UK accounting requirements brain: "
            f"{uk_brain.get('status', 'unknown')} "
            f"requirements={uk_summary.get('requirement_count', 0)} "
            f"questions={uk_summary.get('question_count', 0)} "
            f"unresolved={uk_summary.get('unresolved_question_count', 0)} "
            f"vat_over_threshold={uk_figures.get('turnover_over_vat_threshold', 'unknown')}"
        )
        print(
            "   Human filing handoff: "
            f"{handoff_pack.get('status', 'unknown')} "
            f"ready={handoff_readiness.get('ready_for_manual_upload', handoff_readiness.get('ready_for_manual_review', 'unknown'))} "
            f"folder={handoff_pack.get('output_dir', 'not generated')}"
        )
        print(
            "   Accounting mind: "
            f"vault_memory={vault_memory.get('status', 'unknown')} "
            f"self_questioning={cognitive.get('status', 'unknown')} "
            f"source={cognitive.get('answer_source', 'n/a')}"
        )
    end_user = status.get("end_user_accounting_automation") or {}
    if end_user:
        coverage = end_user.get("requirement_coverage") or []
        generated = sum(
            1
            for item in coverage
            if str(item.get("status", "")).startswith("generated")
            or str(item.get("status", "")).startswith("final_ready")
        )
        manual = sum(1 for item in coverage if item.get("manual_required"))
        outputs = end_user.get("outputs") or {}
        print(
            "   End-user accounting automation: "
            f"{end_user.get('status', 'unknown')} "
            f"coverage={generated}/{len(coverage)} "
            f"manual_items={manual} "
            f"start_here={outputs.get('end_user_start_here', 'not generated')}"
        )
    end_user_confirmation = status.get("end_user_confirmation") or {}
    if end_user_confirmation:
        payload = end_user_confirmation.get("confirmation") or end_user_confirmation
        print(
            "   End-user confirmation feed: "
            f"{end_user_confirmation.get('status', payload.get('status', 'unknown'))} "
            f"confirmed={len(payload.get('what_aureon_confirmed') or [])} "
            f"attention={len(payload.get('attention_items') or [])}"
        )
    missing = status.get("missing_outputs") or []
    print(f"   Missing outputs: {', '.join(missing) if missing else 'none'}")


def run_accounts_build_for_ignition() -> dict:
    from aureon.queen.accounting_context_bridge import get_accounting_context_bridge

    bridge = get_accounting_context_bridge()
    if hasattr(bridge, "run_end_user_accounting_automation"):
        return bridge.run_end_user_accounting_automation(no_fetch=True)
    return bridge.run_full_accounts(no_fetch=True)


def run_autonomous_accounts_for_ignition() -> dict:
    from aureon.queen.accounting_context_bridge import get_accounting_context_bridge

    bridge = get_accounting_context_bridge()
    return bridge.run_autonomous_full_accounts(no_fetch=True)


# ============================================================================
# PHASE 0: BOOT THE QUEEN LAYER (all 6 phases inside)
# ============================================================================

def ignite_queen(live_trading: bool = False):
    """Boot the entire Queen Layer -- 6 phases, ~100+ systems."""
    from queen_layer import boot_queen_layer, get_queen_layer

    print("[IGNITION] Phase 0: Booting Queen Layer (6 internal phases)...\n")
    health = boot_queen_layer(live_trading=live_trading)

    layer = get_queen_layer()
    print(f"\n[IGNITION] Queen Layer: {health['online']}/{health['total']} systems ONLINE")

    return layer, health


# ============================================================================
# PHASE 1: WIRE EXECUTION SYSTEMS (from master launcher)
# ============================================================================

def wire_execution(layer):
    """Wire HFT, Enigma, and additional execution systems."""
    print("\n[IGNITION] Wiring execution systems...")

    queen = layer.queen
    labyrinth = layer.labyrinth
    wired = 0

    if not queen or not labyrinth:
        print("   Queen or Labyrinth not available -- execution wiring skipped")
        return wired

    # Enigma integration
    try:
        from aureon_enigma_integration import get_enigma_integration
        enigma = get_enigma_integration()
        if hasattr(queen, "wire_enigma"):
            queen.wire_enigma(enigma)
            wired += 1
    except Exception:
        pass

    # HFT Engine
    try:
        from aureon_hft_harmonic_mycelium import get_hft_engine
        hft = get_hft_engine()
        if hasattr(queen, "wire_hft_engine"):
            queen.wire_hft_engine(hft)
            wired += 1
    except Exception:
        pass

    # HFT Order Router
    try:
        from aureon_hft_websocket_order_router import get_order_router
        router = get_order_router()
        if hasattr(router, "wire_exchange_clients"):
            clients = {}
            for name in ("kraken", "binance", "alpaca"):
                client = getattr(labyrinth, name, None)
                if client:
                    clients[name] = client
            if clients:
                router.wire_exchange_clients(clients)
        if hasattr(queen, "wire_hft_order_router"):
            queen.wire_hft_order_router(router)
            wired += 1
    except Exception:
        pass

    # Harmonic signal chain + alphabet
    try:
        from aureon_harmonic_signal_chain import HarmonicSignalChain
        chain = HarmonicSignalChain()
        if hasattr(queen, "harmonic_signal_chain"):
            queen.harmonic_signal_chain = chain
            wired += 1
    except Exception:
        pass

    try:
        from aureon_harmonic_alphabet import HarmonicAlphabet
        alpha = HarmonicAlphabet()
        if hasattr(queen, "harmonic_alphabet"):
            queen.harmonic_alphabet = alpha
            wired += 1
    except Exception:
        pass

    print(f"   Execution wiring: {wired} additional systems connected")
    return wired


# ============================================================================
# PHASE 2: FLIGHT CHECK
# ============================================================================

def flight_check(layer):
    """Validate end-to-end connections before autonomous trading."""
    print("\n[IGNITION] Running system flight check...")

    queen = layer.queen
    health = layer.get_health()

    checks = {
        "queen_online": queen is not None,
        "queen_control": getattr(queen, "has_full_control", False) if queen else False,
        "trading_enabled": getattr(queen, "trading_enabled", False) if queen else False,
        "labyrinth": layer.labyrinth is not None,
        "thought_bus": layer.thought_bus is not None,
    }

    # Check critical subsystems
    for name in ("queen_cortex", "queen_source_law", "queen_mycelium_mind",
                 "queen_metacognition", "queen_sentient_loop",
                 "real_intelligence_engine", "dr_auris_throne"):
        info = layer.registry.get(name, {})
        checks[name] = info.get("status") == "ONLINE"

    passed = sum(1 for v in checks.values() if v)
    total = len(checks)

    print(f"   Flight check: {passed}/{total} systems GO")
    for name, ok in checks.items():
        status = "GO" if ok else "NO-GO"
        if not ok:
            print(f"   {status}: {name}")

    return checks


# ============================================================================
# PHASE 3: AUTONOMOUS TRADING LOOP
# ============================================================================

def run_trading_loop(layer):
    """The main autonomous trading loop under Prime Sentinel authority."""
    queen = layer.queen
    labyrinth = layer.labyrinth

    # Gather intelligence imports
    hub = None
    try:
        from aureon_real_data_feed_hub import get_feed_hub
        hub = get_feed_hub()
    except Exception:
        pass

    wiring_status_fn = None
    try:
        from aureon_system_wiring import get_wiring_status
        wiring_status_fn = get_wiring_status
    except Exception:
        pass

    print("\n" + "=" * 80)
    print("  AUTONOMOUS TRADING ACTIVE -- Prime Sentinel Authority")
    print("  Press Ctrl+C to stop")
    print("=" * 80 + "\n")

    cycle = 0
    while True:
        cycle += 1
        ts = datetime.now().strftime("%H:%M:%S")

        try:
            # Gather and distribute intelligence
            intel_summary = {}
            if hub and hasattr(hub, "gather_and_distribute"):
                try:
                    prices = {}
                    if labyrinth and hasattr(labyrinth, "get_all_prices"):
                        prices = labyrinth.get_all_prices() or {}
                    intel_summary = hub.gather_and_distribute(prices) or {}
                except Exception:
                    pass

            stats = intel_summary.get("stats", {})
            bots = stats.get("bots_detected", 0)
            whales = stats.get("whales_predicted", 0)
            validated = stats.get("validated_signals", 0)

            # Wiring status
            events = 0
            if wiring_status_fn:
                try:
                    ws = wiring_status_fn()
                    events = ws.get("total_events", 0)
                except Exception:
                    pass

            # Cortex state
            cortex_info = ""
            cortex_entry = layer.registry.get("queen_cortex", {})
            cortex = cortex_entry.get("instance")
            if cortex and hasattr(cortex, "get_dominant_band"):
                band = cortex.get_dominant_band()
                cortex_info = f" | Band: {band}"

            # Metacognition state
            meta_info = ""
            meta_entry = layer.registry.get("queen_metacognition", {})
            meta = meta_entry.get("instance")
            if meta and hasattr(meta, "get_state"):
                ms = meta.get_state()
                seeds = ms.get("dormant_seeds", 0)
                meta_info = f" | Seeds: {seeds}"

            # Status line
            print(f"\r[{ts}] Cycle {cycle:5d} | "
                  f"Bots: {bots:3d} | Whales: {whales:3d} | "
                  f"Signals: {validated:2d} | Events: {events:,}"
                  f"{cortex_info}{meta_info}",
                  end="", flush=True)

            # Execute validated signals every 5 cycles
            if cycle % 5 == 0 and validated > 0 and queen and labyrinth:
                validated_signals = intel_summary.get("validated_intelligence", [])
                if isinstance(validated_signals, list):
                    for sig in validated_signals[:3]:
                        symbol = sig.get("symbol", "?")
                        action = sig.get("action", "HOLD")
                        conf = sig.get("confidence", 0)
                        if conf > 0.7 and action != "HOLD":
                            print(f"\n   Signal: {symbol} {action} ({conf:.0%})")

            # Flight check every 60 cycles
            if cycle % 60 == 0:
                h = layer.get_health()
                print(f"\n   Health: {h['online']}/{h['total']} ONLINE", end="")

            # Metacognition self-backtest every 300 cycles (~5 min)
            if cycle % 300 == 0 and meta and hasattr(meta, "self_backtest"):
                try:
                    bt = meta.self_backtest()
                    score = bt.get("overall_metacognitive_score", 0)
                    print(f"\n   Metacognitive self-test: {score:.4f}", end="")
                except Exception:
                    pass

        except Exception as e:
            logging.getLogger(__name__).debug(f"Trading loop error: {e}")

        time.sleep(1)


# ============================================================================
# SIGNAL HANDLING
# ============================================================================

_SHUTDOWN = False


def _signal_handler(sig, frame):
    global _SHUTDOWN
    if _SHUTDOWN:
        print("\n\nForce quit.")
        sys.exit(1)
    _SHUTDOWN = True
    print("\n\n[IGNITION] Shutdown signal received. Stopping gracefully...")
    sys.exit(0)


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Aureon Ignition -- One switch, everything fires.",
    )
    parser.add_argument("--live", action="store_true",
                        help="Enable LIVE trading (default: dry-run)")
    parser.add_argument("--no-trade", action="store_true",
                        help="Boot all systems but skip the trading loop")
    parser.add_argument("--audit-only", action="store_true",
                        help="Apply the selected runtime profile, write the ignition audit, and exit before boot")
    parser.add_argument("--accounts-status", action="store_true",
                        help="Print accounting context status during startup/audit")
    parser.add_argument("--accounts-build", action="store_true",
                        help="Explicitly run the on-demand final-ready accounts workflow before boot")
    parser.add_argument("--accounts-autonomous", action="store_true",
                        help="Explicitly run the safe raw-data + vault + self-questioning accounts workflow before boot")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable debug logging")
    args = parser.parse_args()

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    setup_logging(verbose=args.verbose)
    print_banner()

    live = args.live or os.getenv("AUREON_LIVE_TRADING", "0") in ("1", "true", "yes")
    env_report = load_aureon_environment(_REPO_ROOT, override=False).to_dict()
    runtime_env = configure_ignition_runtime(live)
    audit = build_ignition_audit(live=live, no_trade=args.no_trade, env_report=env_report)
    write_ignition_audit(audit)
    require_ignition_ready(audit)

    mode = "LIVE" if live else "DRY-RUN"
    print(f"[IGNITION] Mode: {mode}")
    print(f"[IGNITION] Working directory: {os.getcwd()}")
    print(f"[IGNITION] Runtime audit: {IGNITION_AUDIT_JSON}")
    print(f"[IGNITION] Env files loaded: {', '.join(env_report.get('loaded_paths') or []) or 'none'}")
    if live:
        print("[IGNITION] Live profile applied from --live")
        print("[IGNITION] LLM/cognitive live reasoning: ON")
        if os.getenv("AUREON_ORDER_AUTHORITY_MODE") == "intent_only_runtime_gated":
            print("[IGNITION] LLM/cognitive order-intent authority: ON")
            print("[IGNITION] LLM/cognitive direct exchange mutation authority: OFF (runtime-gated)")
        else:
            print("[IGNITION] LLM/cognitive direct order authority: OFF")
        groups = enabled_credential_groups() or {"kraken": KRAKEN_REQUIRED_ENV}
        group_summary = "; ".join(
            f"{exchange}: {env_status_summary(keys)}"
            for exchange, keys in groups.items()
        )
        print(f"[IGNITION] Enabled exchange env: {group_summary}")
    else:
        print("[IGNITION] Dry-run/audit safety profile applied")
    print(f"[IGNITION] LIVE={runtime_env.get('LIVE')} DRY_RUN={runtime_env.get('DRY_RUN')} "
          f"AUREON_LIVE_TRADING={runtime_env.get('AUREON_LIVE_TRADING')} "
          f"AUREON_DISABLE_REAL_ORDERS={runtime_env.get('AUREON_DISABLE_REAL_ORDERS')}")
    if args.accounts_status:
        print_accounting_status(audit.get("accounting") or {})
    if args.accounts_build:
        print("[IGNITION] --accounts-build requested. Running final-ready accounts workflow in no-fetch/manual-filing mode...")
        build_result = run_accounts_build_for_ignition()
        print(
            "[IGNITION] Accounting final-ready build "
            f"{build_result.get('status')} (exit={build_result.get('exit_code', 'n/a')}); "
            "no Companies House/HMRC filing or payment was submitted."
        )
        audit = build_ignition_audit(live=live, no_trade=args.no_trade, env_report=env_report)
        write_ignition_audit(audit)
        if args.accounts_status:
            print_accounting_status(audit.get("accounting") or {})
    if args.accounts_autonomous:
        print("[IGNITION] --accounts-autonomous requested. Running raw-data/vault/self-questioning accounts workflow...")
        workflow_result = run_autonomous_accounts_for_ignition()
        print(
            "[IGNITION] Autonomous accounting workflow "
            f"{workflow_result.get('status')} (exit={workflow_result.get('exit_code', 'n/a')}); "
            "no Companies House/HMRC filing or payment was submitted."
        )
        audit = build_ignition_audit(live=live, no_trade=args.no_trade, env_report=env_report)
        write_ignition_audit(audit)
        if args.accounts_status:
            print_accounting_status(audit.get("accounting") or {})
    print()

    if args.audit_only:
        print("[IGNITION] --audit-only complete. No systems were booted and no trading loop was started.")
        return

    # ── BOOT ──────────────────────────────────────────────────────────
    boot_start = time.time()

    layer, health = ignite_queen(live_trading=live)
    wire_execution(layer)
    checks = flight_check(layer)

    boot_elapsed = time.time() - boot_start

    print(f"\n{'=' * 80}")
    print(f"  IGNITION COMPLETE")
    print(f"  Systems: {health['online']}/{health['total']} ONLINE")
    print(f"  Flight check: {sum(1 for v in checks.values() if v)}/{len(checks)} GO")
    print(f"  Boot time: {boot_elapsed:.1f}s")
    print(f"  Mode: {mode}")
    print(f"{'=' * 80}")

    if args.no_trade:
        print("\n[IGNITION] --no-trade flag set. Systems running. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(60)
                h = layer.get_health()
                ts = datetime.now().strftime("%H:%M:%S")
                print(f"[{ts}] Health: {h['online']}/{h['total']} ONLINE")
        except KeyboardInterrupt:
            print("\n[IGNITION] Shutdown.")
        return

    # ── TRADE ─────────────────────────────────────────────────────────
    try:
        run_trading_loop(layer)
    except KeyboardInterrupt:
        print("\n\n[IGNITION] Shutdown.")
    except SystemExit:
        pass


if __name__ == "__main__":
    main()
