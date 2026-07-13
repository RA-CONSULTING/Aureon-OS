"""Live organism pulse and guarded action contract for Aureon.

This module does not place trades by itself. It refreshes safe self-audit
artifacts, checks whether each organism domain has fresh data, records blind
spots, and publishes one frontend-readable status manifest that says which
existing runtime gates may act right now and which boundaries remain manual.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence

_MD_PIPE = "\\|"  # markdown-escaped pipe (kept out of f-string expressions for 3.11)


SCHEMA_VERSION = "aureon-organism-runtime-status-v1"
DEFAULT_OUTPUT_MD = Path("docs/audits/aureon_organism_runtime_status.md")
DEFAULT_OUTPUT_JSON = Path("docs/audits/aureon_organism_runtime_status.json")
DEFAULT_PUBLIC_JSON = Path("frontend/public/aureon_organism_runtime_status.json")
DEFAULT_VAULT_NOTE = Path(".obsidian/Aureon Self Understanding/aureon_organism_runtime_status.md")
DEFAULT_LOCAL_TERMINAL_URL = os.getenv("AUREON_RUNTIME_FEED_URL", "http://127.0.0.1:8790/api/terminal-state")
WAKE_UP_MANIFEST_PATHS = (
    Path("state/aureon_wake_up_manifest.json"),
    Path("frontend/public/aureon_wake_up_manifest.json"),
)

SAFE_OBSERVER_ENV = {
    "AUREON_AUDIT_MODE": "1",
    "AUREON_LIVE_TRADING": "0",
    "AUREON_DISABLE_REAL_ORDERS": "1",
    "AUREON_ALLOW_SIM_FALLBACK": "1",
    "AUREON_QUIET_STARTUP": "1",
}

CORE_REFRESH_MODULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("saas_inventory", ("aureon.autonomous.aureon_saas_system_inventory",)),
    ("frontend_unification", ("aureon.autonomous.aureon_frontend_unification_plan",)),
    ("frontend_evolution_queue", ("aureon.autonomous.aureon_frontend_evolution_queue",)),
    ("capability_switchboard", ("aureon.autonomous.aureon_autonomous_capability_switchboard",)),
    ("operational_ui_builder", ("aureon.autonomous.aureon_unified_ui_builder",)),
    ("system_readiness", ("aureon.autonomous.aureon_system_readiness_audit",)),
    ("cognitive_trade_evidence", ("aureon.autonomous.aureon_cognitive_trade_evidence",)),
    ("harmonic_affect_state", ("aureon.autonomous.aureon_harmonic_affect_state",)),
    ("trading_intelligence_checklist", ("aureon.autonomous.aureon_trading_intelligence_checklist",)),
)

HEAVY_REFRESH_MODULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("repo_organization", ("aureon.autonomous.repo_wide_organization_audit",)),
    ("repo_self_catalog", ("aureon.autonomous.aureon_repo_self_catalog",)),
    ("mind_wiring", ("aureon.autonomous.mind_wiring_audit", "--static", "--imports")),
)


@dataclass
class DomainPulse:
    id: str
    label: str
    domain: str
    status: str
    freshness: str
    source_path: str
    generated_at: str = ""
    age_seconds: Optional[int] = None
    summary: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    blind_spots: list[str] = field(default_factory=list)
    display_state: str = "not_mounted"
    next_action: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BlindSpot:
    id: str
    severity: str
    domain: str
    issue: str
    evidence: dict[str, Any] = field(default_factory=dict)
    next_action: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RefreshResult:
    id: str
    status: str
    command: list[str]
    duration_seconds: float
    stdout_tail: str = ""
    stderr_tail: str = ""
    returncode: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OrganismRuntimeStatus:
    schema_version: str
    generated_at: str
    repo_root: str
    status: str
    mode: str
    safety: dict[str, Any]
    summary: dict[str, Any]
    domains: list[DomainPulse]
    blind_spots: list[BlindSpot]
    data_freshness: dict[str, Any]
    refresh_results: list[RefreshResult]
    real_time_feeds: dict[str, Any]
    status_lines: list[str]
    next_actions: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "repo_root": self.repo_root,
            "status": self.status,
            "mode": self.mode,
            "safety": dict(self.safety),
            "summary": dict(self.summary),
            "domains": [item.to_dict() for item in self.domains],
            "blind_spots": [item.to_dict() for item in self.blind_spots],
            "data_freshness": dict(self.data_freshness),
            "refresh_results": [item.to_dict() for item in self.refresh_results],
            "real_time_feeds": dict(self.real_time_feeds),
            "status_lines": list(self.status_lines),
            "next_actions": list(self.next_actions),
        }


DOMAIN_MANIFESTS: tuple[dict[str, Any], ...] = (
    {
        "id": "saas_inventory",
        "label": "SaaS And Frontend Inventory",
        "domain": "operator",
        "path": "docs/audits/aureon_saas_system_inventory.json",
        "public_path": "frontend/public/aureon_saas_system_inventory.json",
        "fresh_seconds": 15 * 60,
        "required_summary_keys": ("surface_count", "frontend_surface_count", "supabase_function_count"),
        "attention_keys": ("security_blocker_count", "orphaned_frontend_count", "missing_supabase_function_call_count"),
        "next_action": "Run python -m aureon.autonomous.aureon_saas_system_inventory.",
    },
    {
        "id": "frontend_unification",
        "label": "Unified Frontend Plan",
        "domain": "operator",
        "path": "docs/audits/aureon_frontend_unification_plan.json",
        "public_path": "frontend/public/aureon_frontend_unification_plan.json",
        "fresh_seconds": 15 * 60,
        "required_summary_keys": ("screen_count", "source_surface_count"),
        "attention_keys": ("security_blocker_count", "missing_screen_capability_count"),
        "next_action": "Run python -m aureon.autonomous.aureon_frontend_unification_plan.",
    },
    {
        "id": "frontend_evolution_queue",
        "label": "Frontend Evolution Queue",
        "domain": "self_improvement",
        "path": "docs/audits/aureon_frontend_evolution_queue.json",
        "public_path": "frontend/public/aureon_frontend_evolution_queue.json",
        "fresh_seconds": 15 * 60,
        "required_summary_keys": ("queue_count",),
        "attention_keys": ("blocked_count", "archive_candidate_count"),
        "next_action": "Run python -m aureon.autonomous.aureon_frontend_evolution_queue.",
    },
    {
        "id": "capability_switchboard",
        "label": "Autonomous Capability Switchboard",
        "domain": "self_improvement",
        "path": "docs/audits/aureon_autonomous_capability_switchboard.json",
        "public_path": "frontend/public/aureon_autonomous_capability_switchboard.json",
        "fresh_seconds": 15 * 60,
        "required_summary_keys": ("capability_count", "presentation_intent_count"),
        "attention_keys": ("blocker_count", "blocked_capability_count"),
        "next_action": "Run python -m aureon.autonomous.aureon_autonomous_capability_switchboard.",
    },
    {
        "id": "operational_ui_builder",
        "label": "Aureon Operational UI Builder",
        "domain": "self_improvement",
        "path": "docs/audits/aureon_operational_ui_builder.json",
        "public_path": "frontend/public/aureon_operational_ui_spec.json",
        "fresh_seconds": 15 * 60,
        "required_summary_keys": ("capability_count", "frontend_work_order_count", "template_count"),
        "summary_path": ("capability_coverage",),
        "attention_keys": ("blocked_work_order_count", "blind_spot_count"),
        "next_action": "Run python -m aureon.autonomous.aureon_unified_ui_builder.",
    },
    {
        "id": "system_readiness",
        "label": "Whole Organism Readiness",
        "domain": "cognition",
        "path": "docs/audits/aureon_system_readiness_audit.json",
        "fresh_seconds": 15 * 60,
        "required_summary_keys": ("proof_count",),
        "attention_keys": ("blocked_count", "attention_count"),
        "next_action": "Run python -m aureon.autonomous.aureon_system_readiness_audit.",
    },
    {
        "id": "cognitive_trade_evidence",
        "label": "Cognitive Trade Evidence",
        "domain": "trading",
        "path": "docs/audits/aureon_cognitive_trade_evidence.json",
        "public_path": "frontend/public/aureon_cognitive_trade_evidence.json",
        "fresh_seconds": 15 * 60,
        "required_summary_keys": ("evidence_count", "signal_quality", "action_mode"),
        "attention_keys": ("runtime_stale",),
        "next_action": "Run python -m aureon.autonomous.aureon_cognitive_trade_evidence.",
    },
    {
        "id": "harmonic_affect_state",
        "label": "HNC Auris Harmonic Affect State",
        "domain": "cognition",
        "path": "docs/audits/aureon_harmonic_affect_state.json",
        "public_path": "frontend/public/aureon_harmonic_affect_state.json",
        "fresh_seconds": 15 * 60,
        "required_summary_keys": ("hnc_coherence_score", "affect_phase", "resonance_frequency_hz"),
        "attention_keys": ("runtime_stale", "safety_blocker_count"),
        "next_action": "Run python -m aureon.autonomous.aureon_harmonic_affect_state.",
    },
    {
        "id": "trading_intelligence_checklist",
        "label": "Trading Intelligence Checklist",
        "domain": "trading",
        "path": "docs/audits/aureon_trading_intelligence_checklist.json",
        "public_path": "frontend/public/aureon_trading_intelligence_checklist.json",
        "fresh_seconds": 15 * 60,
        "required_summary_keys": ("system_count", "fresh_usable_count", "decision_fed_count"),
        "attention_keys": ("runtime_stale", "stale_or_blocked_count"),
        "next_action": "Run python -m aureon.autonomous.aureon_trading_intelligence_checklist.",
    },
    {
        "id": "exchange_data_capability_matrix",
        "label": "Exchange Data Capability Matrix",
        "domain": "trading",
        "path": "docs/audits/aureon_exchange_data_capability_matrix.json",
        "public_path": "frontend/public/aureon_exchange_data_capability_matrix.json",
        "fresh_seconds": 15 * 60,
        "required_summary_keys": ("exchange_count", "official_rate_limit_profile_count", "data_boost_eligible_count"),
        "attention_keys": ("runtime_stale",),
        "next_action": "Run python -m aureon.autonomous.aureon_exchange_data_capability_matrix.",
    },
    {
        "id": "mind_wiring",
        "label": "Whole-Mind Wiring",
        "domain": "cognition",
        "path": "docs/audits/mind_wiring_audit.json",
        "fresh_seconds": 24 * 60 * 60,
        "required_summary_keys": (),
        "attention_nested_counts": ("counts", ("broken", "partial", "unknown")),
        "next_action": "Run python -m aureon.autonomous.mind_wiring_audit --static --imports --local-services.",
    },
    {
        "id": "repo_self_catalog",
        "label": "File Self-Catalog",
        "domain": "self_knowledge",
        "path": "docs/audits/aureon_repo_self_catalog.json",
        "fresh_seconds": 24 * 60 * 60,
        "required_summary_keys": ("cataloged_file_count",),
        "attention_keys": ("secret_metadata_only_count",),
        "next_action": "Run python -m aureon.autonomous.aureon_repo_self_catalog.",
    },
    {
        "id": "accounting_registry",
        "label": "Accounting System Registry",
        "domain": "accounting",
        "path": "docs/audits/accounting_system_registry.json",
        "fresh_seconds": 24 * 60 * 60,
        "required_summary_keys": (),
        "next_action": "Run the accounting registry/accounts generation workflow in safe manual-filing mode.",
    },
    {
        "id": "capability_growth_loop",
        "label": "Capability Growth Loop",
        "domain": "self_improvement",
        "path": "docs/audits/aureon_capability_growth_loop.json",
        "fresh_seconds": 24 * 60 * 60,
        "required_summary_keys": (),
        "attention_keys": ("blocked_count",),
        "next_action": "Run python -m aureon.autonomous.aureon_capability_growth_loop.",
    },
    {
        "id": "self_enhancement_lifecycle",
        "label": "Self-Enhancement Lifecycle",
        "domain": "self_improvement",
        "path": "docs/audits/aureon_self_enhancement_lifecycle.json",
        "fresh_seconds": 24 * 60 * 60,
        "required_summary_keys": (),
        "attention_keys": ("blocked_count",),
        "next_action": "Run python -m aureon.autonomous.aureon_self_enhancement_lifecycle.",
    },
    {
        "id": "hnc_saas_security",
        "label": "HNC SaaS Security Blueprint",
        "domain": "saas_security",
        "path": "docs/audits/hnc_saas_security_blueprint.json",
        "fresh_seconds": 24 * 60 * 60,
        "required_summary_keys": (),
        "attention_keys": ("critical_gap_count", "blocker_count"),
        "next_action": "Run python -m aureon.autonomous.hnc_saas_security_architect.",
    },
    {
        "id": "hnc_attack_lab",
        "label": "Authorized Attack Lab",
        "domain": "saas_security",
        "path": "docs/audits/hnc_authorized_attack_lab.json",
        "fresh_seconds": 24 * 60 * 60,
        "required_summary_keys": (),
        "attention_keys": ("blocked_count", "finding_count"),
        "next_action": "Run the authorized attack lab against owned/local targets only.",
    },
)

STATE_FILES: tuple[dict[str, Any], ...] = (
    {
        "id": "adaptive_learning_history",
        "label": "Adaptive Learning History",
        "domain": "cognition",
        "path": "adaptive_learning_history.json",
        "fresh_seconds": 6 * 60 * 60,
        "next_action": "Start the safe runtime/cognition loop so learning history is repopulated.",
    },
    {
        "id": "brain_predictions_history",
        "label": "Brain Prediction History",
        "domain": "cognition",
        "path": "brain_predictions_history.json",
        "fresh_seconds": 6 * 60 * 60,
        "next_action": "Start the safe runtime/cognition loop so prediction history is repopulated.",
    },
    {
        "id": "miner_brain_knowledge",
        "label": "Miner Brain Knowledge",
        "domain": "research",
        "path": "miner_brain_knowledge.json",
        "fresh_seconds": 24 * 60 * 60,
        "next_action": "Run the research/vault ingestion loop to refresh miner knowledge.",
    },
    {
        "id": "consciousness_state",
        "label": "Consciousness State",
        "domain": "cognition",
        "path": "public/consciousness_state.json",
        "fresh_seconds": 60 * 60,
        "next_action": "Start the cognition runtime so consciousness state is updated.",
    },
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def repo_root_from(start: Optional[Path] = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "aureon").is_dir() and (candidate / "scripts").is_dir():
            return candidate
    return Path(__file__).resolve().parents[2]


def _rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        return path.as_posix().replace("\\", "/")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


def _parse_time(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        text = str(value).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return None


def _file_time(path: Path) -> Optional[datetime]:
    if not path.exists():
        return None
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    except Exception:
        return None


def _age_seconds(ts: Optional[datetime]) -> Optional[int]:
    if ts is None:
        return None
    return max(0, int((datetime.now(timezone.utc) - ts).total_seconds()))


def _tail(text: str, limit: int = 1600) -> str:
    return text[-limit:] if len(text) > limit else text


def _nonzero_summary_keys(summary: dict[str, Any], keys: Sequence[str]) -> list[str]:
    found: list[str] = []
    for key in keys:
        value = summary.get(key)
        try:
            if float(value or 0) > 0:
                found.append(key)
        except Exception:
            if value:
                found.append(key)
    return found


def read_wake_up_manifest(root: Path) -> dict[str, Any]:
    for relative_path in WAKE_UP_MANIFEST_PATHS:
        path = root / relative_path
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                payload["_source_path"] = _rel(path, root)
                return payload
        except Exception:
            continue
    return {}


def _project_manifest_runtime_env(wake_manifest: dict[str, Any]) -> dict[str, str]:
    safety = wake_manifest.get("safety") if isinstance(wake_manifest.get("safety"), dict) else {}
    live_flags = wake_manifest.get("live_safety_flags") if isinstance(wake_manifest.get("live_safety_flags"), dict) else {}

    def _value(*keys: str) -> str:
        for source in (live_flags, safety):
            for key in keys:
                value = source.get(key)
                if value is not None and str(value) != "":
                    return str(value)
        return ""

    return {
        "AUREON_AUDIT_MODE": _value("aureon_audit_mode", "audit_mode"),
        "AUREON_LIVE_TRADING": _value("live_trading"),
        "AUREON_DISABLE_REAL_ORDERS": _value("disable_real_orders"),
        "AUREON_DISABLE_EXCHANGE_MUTATIONS": _value("disable_exchange_mutations"),
        "AUREON_ALLOW_SIM_FALLBACK": _value("allow_sim_fallback"),
        "AUREON_DRY_RUN": _value("aureon_dry_run"),
        "DRY_RUN": _value("dry_run"),
        "LIVE": _value("live"),
    }


def safe_observer_environment(wake_manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    runtime_env = {key: os.environ.get(key, "") for key in SAFE_OBSERVER_ENV}
    runtime_env["AUREON_DISABLE_EXCHANGE_MUTATIONS"] = os.environ.get("AUREON_DISABLE_EXCHANGE_MUTATIONS", "")
    runtime_env["AUREON_DRY_RUN"] = os.environ.get("AUREON_DRY_RUN", "")
    runtime_env["DRY_RUN"] = os.environ.get("DRY_RUN", "")
    runtime_env["LIVE"] = os.environ.get("LIVE", "")
    manifest_env = _project_manifest_runtime_env(wake_manifest or {})
    for key, value in manifest_env.items():
        if value and not runtime_env.get(key):
            runtime_env[key] = value
    refresh_env = dict(SAFE_OBSERVER_ENV)
    try:
        from aureon.core.aureon_runtime_safety import apply_safe_runtime_environment

        apply_safe_runtime_environment(refresh_env)
    except Exception:
        pass
    return {
        "runtime": runtime_env,
        "refresh_sandbox": refresh_env,
        "wake_up_manifest": {
            "source_path": (wake_manifest or {}).get("_source_path"),
            "mode": (wake_manifest or {}).get("mode"),
            "runtime_feed_url": (wake_manifest or {}).get("runtime_feed_url"),
            "runtime_flight_test_url": (wake_manifest or {}).get("runtime_flight_test_url"),
            "runtime_reboot_advice_url": (wake_manifest or {}).get("runtime_reboot_advice_url"),
        },
    }


def refresh_artifacts(
    root: Path,
    *,
    refresh_core: bool = False,
    refresh_heavy: bool = False,
    timeout_seconds: int = 180,
) -> list[RefreshResult]:
    if not refresh_core and not refresh_heavy:
        return []

    env = os.environ.copy()
    env.update(SAFE_OBSERVER_ENV)
    commands = list(CORE_REFRESH_MODULES if refresh_core else ())
    if refresh_heavy:
        commands.extend(HEAVY_REFRESH_MODULES)

    results: list[RefreshResult] = []
    for refresh_id, module_parts in commands:
        cmd = [sys.executable, "-m", module_parts[0], *module_parts[1:]]
        started = time.perf_counter()
        try:
            completed = subprocess.run(
                cmd,
                cwd=str(root),
                env=env,
                text=True,
                capture_output=True,
                timeout=timeout_seconds,
                check=False,
            )
            duration = time.perf_counter() - started
            results.append(
                RefreshResult(
                    id=refresh_id,
                    status="ok" if completed.returncode == 0 else "failed",
                    command=cmd,
                    duration_seconds=round(duration, 3),
                    stdout_tail=_tail(completed.stdout),
                    stderr_tail=_tail(completed.stderr),
                    returncode=int(completed.returncode),
                )
            )
        except subprocess.TimeoutExpired as exc:
            duration = time.perf_counter() - started
            results.append(
                RefreshResult(
                    id=refresh_id,
                    status="timeout",
                    command=cmd,
                    duration_seconds=round(duration, 3),
                    stdout_tail=_tail(exc.stdout or ""),
                    stderr_tail=_tail(exc.stderr or ""),
                    returncode=124,
                )
            )
        except Exception as exc:
            duration = time.perf_counter() - started
            results.append(
                RefreshResult(
                    id=refresh_id,
                    status="failed",
                    command=cmd,
                    duration_seconds=round(duration, 3),
                    stderr_tail=f"{type(exc).__name__}: {exc}",
                    returncode=1,
                )
            )
    return results


def build_domain_pulse(root: Path, spec: dict[str, Any]) -> DomainPulse:
    path = root / str(spec["path"])
    data = _load_json(path)
    summary_path = tuple(spec.get("summary_path") or ())
    summary_source: Any = data
    for part in summary_path:
        summary_source = summary_source.get(part) if isinstance(summary_source, dict) else {}
    if summary_path:
        summary = summary_source if isinstance(summary_source, dict) else {}
    else:
        summary = data.get("summary") if isinstance(data.get("summary"), dict) else {}
    metrics = dict(summary)
    generated_time = _parse_time(data.get("generated_at")) or _file_time(path)
    age = _age_seconds(generated_time)
    fresh_seconds = int(spec.get("fresh_seconds") or 3600)
    public_path = root / str(spec.get("public_path") or "")
    display_state = "mounted" if spec.get("public_path") and public_path.exists() else "internal"
    blind_spots: list[str] = []

    if not path.exists():
        status = "missing"
        freshness = "missing"
        blind_spots.append("manifest_missing")
    elif data.get("error"):
        status = "broken"
        freshness = "unknown"
        blind_spots.append("manifest_parse_error")
    elif age is not None and age > fresh_seconds:
        status = "stale"
        freshness = "stale"
        blind_spots.append("manifest_stale")
    else:
        status = "fresh"
        freshness = "fresh"

    required = tuple(spec.get("required_summary_keys") or ())
    for key in required:
        if key not in summary:
            blind_spots.append(f"missing_summary_{key}")
        else:
            try:
                if float(summary.get(key) or 0) <= 0:
                    blind_spots.append(f"not_populated_{key}")
            except Exception:
                if not summary.get(key):
                    blind_spots.append(f"not_populated_{key}")

    attention = _nonzero_summary_keys(summary, tuple(spec.get("attention_keys") or ()))
    for key in attention:
        blind_spots.append(f"attention_{key}")

    nested = spec.get("attention_nested_counts")
    if nested:
        container_name, nested_keys = nested
        container = data.get(container_name) if isinstance(data.get(container_name), dict) else {}
        for key in nested_keys:
            try:
                if float(container.get(key) or 0) > 0:
                    blind_spots.append(f"attention_{container_name}_{key}")
            except Exception:
                if container.get(key):
                    blind_spots.append(f"attention_{container_name}_{key}")
        metrics[container_name] = container

    if blind_spots and status == "fresh":
        status = "attention"

    return DomainPulse(
        id=str(spec["id"]),
        label=str(spec["label"]),
        domain=str(spec["domain"]),
        status=status,
        freshness=freshness,
        source_path=_rel(path, root),
        generated_at=generated_time.isoformat() if generated_time else "",
        age_seconds=age,
        summary=summary,
        metrics=metrics,
        blind_spots=blind_spots,
        display_state=display_state,
        next_action=str(spec.get("next_action") or "Regenerate the related audit artifact."),
    )


def build_state_file_pulse(root: Path, spec: dict[str, Any]) -> DomainPulse:
    path = root / str(spec["path"])
    timestamp = _file_time(path)
    age = _age_seconds(timestamp)
    fresh_seconds = int(spec.get("fresh_seconds") or 3600)
    blind_spots: list[str] = []
    summary: dict[str, Any] = {}

    if not path.exists():
        status = "missing"
        freshness = "missing"
        blind_spots.append("state_file_missing")
    else:
        try:
            size = path.stat().st_size
        except Exception:
            size = 0
        summary["bytes"] = size
        if size <= 2:
            blind_spots.append("state_file_empty")
        if age is not None and age > fresh_seconds:
            status = "stale"
            freshness = "stale"
            blind_spots.append("state_file_stale")
        else:
            status = "fresh"
            freshness = "fresh"

    if blind_spots and status == "fresh":
        status = "attention"

    return DomainPulse(
        id=str(spec["id"]),
        label=str(spec["label"]),
        domain=str(spec["domain"]),
        status=status,
        freshness=freshness,
        source_path=_rel(path, root),
        generated_at=timestamp.isoformat() if timestamp else "",
        age_seconds=age,
        summary=summary,
        metrics=summary,
        blind_spots=blind_spots,
        display_state="internal",
        next_action=str(spec["next_action"]),
    )


def probe_local_runtime_feed(url: str, timeout_seconds: float = 1.5) -> dict[str, Any]:
    try:
        request = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read(350_000)
        data = json.loads(raw.decode("utf-8", errors="replace"))
        status_lines = data.get("status_lines") if isinstance(data.get("status_lines"), list) else []
        return {
            "status": "online",
            "url": url,
            "ok": bool(data.get("ok")),
            "service": data.get("service") or data.get("source"),
            "generated_at": data.get("generated_at"),
            "status_line_count": len(status_lines),
            "portfolio_value": data.get("portfolio_value"),
            "open_positions": data.get("combined", {}).get("open_positions") if isinstance(data.get("combined"), dict) else None,
            "trading_mode": data.get("trading_mode") or data.get("queen_state"),
            "trading_ready": bool(data.get("trading_ready", False)),
            "data_ready": bool(data.get("data_ready", False)),
            "stale": bool(data.get("stale", False)),
            "booting": bool(data.get("booting", False)),
            "last_tick_completed_at": data.get("last_tick_completed_at"),
            "last_tick_age_sec": data.get("last_tick_age_sec"),
            "runtime_writer": data.get("runtime_writer") if isinstance(data.get("runtime_writer"), dict) else {},
            "runtime_watchdog": data.get("runtime_watchdog") if isinstance(data.get("runtime_watchdog"), dict) else {},
            "api_governor": data.get("api_governor") if isinstance(data.get("api_governor"), dict) else {},
            "errors": data.get("errors") if isinstance(data.get("errors"), dict) else {},
            "notes": ["Local runtime feed responded to read-only GET."],
        }
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return {
            "status": "offline",
            "url": url,
            "error": f"{type(exc).__name__}: {exc}",
            "notes": ["Start Aureon ignition/runtime status service to populate real-time trading/cognition data."],
        }


def flight_test_url_from_terminal_url(url: str) -> str:
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.path.endswith("/api/terminal-state"):
            path = parsed.path[: -len("/api/terminal-state")] + "/api/flight-test"
        else:
            path = "/api/flight-test"
        return urllib.parse.urlunparse(parsed._replace(path=path, query="", fragment=""))
    except Exception:
        return "http://127.0.0.1:8791/api/flight-test"


def probe_runtime_flight_test(terminal_url: str, timeout_seconds: float = 1.5) -> dict[str, Any]:
    url = flight_test_url_from_terminal_url(terminal_url)
    try:
        request = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read(150_000)
        data = json.loads(raw.decode("utf-8", errors="replace"))
        if not isinstance(data, dict):
            data = {}
        return {
            "status": "online",
            "url": url,
            "ok": bool(data.get("ok")),
            "checks": data.get("checks") if isinstance(data.get("checks"), dict) else {},
            "reboot_advice": data.get("reboot_advice") if isinstance(data.get("reboot_advice"), dict) else {},
            "generated_at": data.get("generated_at"),
        }
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return {
            "status": "offline",
            "url": url,
            "error": f"{type(exc).__name__}: {exc}",
            "checks": {},
            "reboot_advice": {},
        }


def _env_flag(environment: dict[str, Any], key: str, default: bool = False) -> bool:
    runtime_env = environment.get("runtime", environment) if isinstance(environment, dict) else {}
    raw = runtime_env.get(key) if isinstance(runtime_env, dict) else None
    if raw is None or raw == "":
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on", "live"}


def build_action_capability(runtime_feed: dict[str, Any], environment: dict[str, Any]) -> dict[str, Any]:
    runtime_online = runtime_feed.get("status") == "online"
    live_env = _env_flag(environment, "AUREON_LIVE_TRADING", False)
    real_orders_disabled = _env_flag(environment, "AUREON_DISABLE_REAL_ORDERS", True)
    exchange_mutations_disabled = _env_flag(environment, "AUREON_DISABLE_EXCHANGE_MUTATIONS", False)
    trading_ready = bool(runtime_feed.get("trading_ready"))
    stale = bool(runtime_feed.get("stale"))
    booting = bool(runtime_feed.get("booting"))
    api_governor = runtime_feed.get("api_governor") if isinstance(runtime_feed.get("api_governor"), dict) else {}
    runtime_writer = runtime_feed.get("runtime_writer") if isinstance(runtime_feed.get("runtime_writer"), dict) else {}
    runtime_watchdog = runtime_feed.get("runtime_watchdog") if isinstance(runtime_feed.get("runtime_watchdog"), dict) else {}
    flight_test = runtime_feed.get("flight_test") if isinstance(runtime_feed.get("flight_test"), dict) else {}
    flight_checks = flight_test.get("checks") if isinstance(flight_test.get("checks"), dict) else {}
    reboot_advice = flight_test.get("reboot_advice") if isinstance(flight_test.get("reboot_advice"), dict) else {}
    combined = runtime_feed.get("combined") if isinstance(runtime_feed.get("combined"), dict) else {}
    try:
        open_positions = int(runtime_feed.get("open_positions") or combined.get("open_positions") or 0)
    except Exception:
        open_positions = 0
    watchdog_open_positions = bool(runtime_watchdog.get("open_positions") or flight_checks.get("open_positions"))

    blockers: list[str] = []
    if not runtime_online:
        blockers.append("runtime_feed_offline")
    if booting:
        blockers.append("runtime_booting")
    if stale:
        blockers.append("runtime_stale")
        stale_reason = str(runtime_feed.get("stale_reason") or runtime_watchdog.get("tick_stale_reason") or "").strip()
        if stale_reason:
            blockers.append(stale_reason)
        if open_positions > 0 or watchdog_open_positions:
            blockers.append("open_positions")
        if flight_checks.get("downtime_window") is False:
            blockers.append("downtime_window_false")
    if not trading_ready:
        blockers.append("trading_runtime_not_ready")
    if not live_env:
        blockers.append("live_trading_env_not_enabled")
    if real_orders_disabled:
        blockers.append("real_orders_disabled")
    if exchange_mutations_disabled:
        blockers.append("exchange_mutations_disabled")

    live_orders_allowed = not blockers
    mode = "guarded_live_action" if live_orders_allowed else "guarded_observe_plan"
    if not runtime_online:
        mode = "safe_observation"

    timestamp = utc_now()
    return {
        "generated_at": timestamp,
        "mode": mode,
        "clock": {
            "timestamp_utc": timestamp,
            "source": "aureon_organism_runtime_observer",
        },
        "loop": ["who", "what", "where", "when", "why", "how", "act", "verify", "record", "repeat"],
        "trading": {
            "can_act": live_orders_allowed,
            "authority": "existing exchange adapters, risk gates, API governor, and order-intent controls only",
            "blocked_by": blockers,
            "verify_by": [
                "runtime feed fresh",
                "runtime writer lock owned",
                "API governor within budgets",
                "open positions and pending orders observed before restart",
                "trade/order records persisted after action",
            ],
            "open_positions": runtime_feed.get("open_positions"),
            "runtime_writer": runtime_writer,
            "runtime_watchdog": runtime_watchdog,
            "flight_test": flight_test,
            "reboot_advice": reboot_advice,
            "api_governor": api_governor,
        },
        "research": {
            "can_act": True,
            "authority": "read-only local/web/API knowledge gathering with source-linked outputs",
            "verify_by": ["source link", "timestamp", "manifest refresh", "visible blocker if source missing"],
        },
        "cognition": {
            "can_act": True,
            "authority": "ThoughtBus, mind hub, prediction history, adaptive learning, and self-questioning loops",
            "verify_by": ["timestamped thought", "manifest evidence", "goal route", "result check"],
        },
        "self_improvement": {
            "can_act": True,
            "authority": "patch, test, flight-test, and defer restarts to downtime windows",
            "verify_by": ["tests or smoke checks", "reboot advice", "downtime window", "change record"],
        },
        "payments": {
            "can_act": False,
            "authority": "manual only",
            "blocked_by": ["payments_manual_boundary"],
        },
        "official_filings": {
            "can_act": False,
            "authority": "manual filing support only",
            "blocked_by": ["official_filing_manual_boundary"],
        },
        "external_security_testing": {
            "can_act": False,
            "authority": "owned/local/staging targets only after explicit authorization",
            "blocked_by": ["authorization_required"],
        },
    }


def build_blind_spots(domains: Sequence[DomainPulse], runtime_feed: dict[str, Any], refresh_results: Sequence[RefreshResult]) -> list[BlindSpot]:
    blind_spots: list[BlindSpot] = []
    for domain in domains:
        for item in domain.blind_spots:
            severity = "high" if "missing" in item or "parse" in item else "medium" if "stale" in item else "attention"
            blind_spots.append(
                BlindSpot(
                    id=f"{domain.id}.{item}",
                    severity=severity,
                    domain=domain.domain,
                    issue=f"{domain.label}: {item.replace('_', ' ')}.",
                    evidence={
                        "source_path": domain.source_path,
                        "age_seconds": domain.age_seconds,
                        "status": domain.status,
                    },
                    next_action=domain.next_action,
                )
            )

    if runtime_feed.get("status") != "online":
        blind_spots.append(
            BlindSpot(
                id="runtime_feed.offline",
                severity="medium",
                domain="runtime",
                issue="Local real-time runtime feed is offline or not populated.",
                evidence={"url": runtime_feed.get("url"), "error": runtime_feed.get("error")},
                next_action="Start the safe Aureon runtime/ignition status service, then rerun the observer.",
            )
        )

    for result in refresh_results:
        if result.status != "ok":
            blind_spots.append(
                BlindSpot(
                    id=f"refresh.{result.id}.{result.status}",
                    severity="high",
                    domain="self_improvement",
                    issue=f"Refresh step {result.id} ended with {result.status}.",
                    evidence={"command": result.command, "returncode": result.returncode, "stderr_tail": result.stderr_tail},
                    next_action="Inspect the refresh output, fix the failing generator, and rerun the observer.",
                )
            )

    return blind_spots


def compute_freshness(domains: Sequence[DomainPulse]) -> dict[str, Any]:
    counts: dict[str, int] = {"fresh": 0, "stale": 0, "missing": 0, "unknown": 0, "attention": 0}
    max_age = 0
    for domain in domains:
        counts[domain.freshness if domain.freshness in counts else "unknown"] += 1
        if domain.status == "attention":
            counts["attention"] += 1
        if domain.age_seconds is not None:
            max_age = max(max_age, int(domain.age_seconds))
    total = max(1, len(domains))
    fresh_ratio = round(counts["fresh"] / total, 3)
    return {
        "counts": counts,
        "domain_count": len(domains),
        "fresh_ratio": fresh_ratio,
        "max_age_seconds": max_age,
    }


def build_status_lines(
    status: str,
    domains: Sequence[DomainPulse],
    blind_spots: Sequence[BlindSpot],
    runtime_feed: dict[str, Any],
    action_capability: dict[str, Any],
) -> list[str]:
    counts: dict[str, int] = {}
    for domain in domains:
        counts[domain.status] = counts.get(domain.status, 0) + 1
    lines = [
        f"Organism pulse: {status}",
        f"Domains fresh={counts.get('fresh', 0)} attention={counts.get('attention', 0)} stale={counts.get('stale', 0)} missing={counts.get('missing', 0)}",
        f"Blind spots visible: {len(blind_spots)}",
        f"Runtime feed: {runtime_feed.get('status', 'unknown')}",
        f"Action mode: {action_capability.get('mode', 'unknown')}",
    ]
    trading = action_capability.get("trading", {}) if isinstance(action_capability.get("trading"), dict) else {}
    if trading.get("can_act"):
        lines.append("Trading action: allowed through existing runtime risk gates and API governor.")
    else:
        blockers = trading.get("blocked_by") if isinstance(trading.get("blocked_by"), list) else []
        lines.append("Trading action: blocked by " + (", ".join(str(item) for item in blockers[:6]) or "unknown_guard"))
    lines.append("Manual boundaries: official filings, payments, credential reveal, and unowned security mutations remain blocked.")
    for item in list(blind_spots)[:8]:
        lines.append(f"{item.severity.upper()} {item.id}: {item.issue}")
    return lines


def build_organism_runtime_status(
    root: Optional[Path] = None,
    *,
    refresh_core: bool = False,
    refresh_heavy: bool = False,
    local_terminal_url: str = DEFAULT_LOCAL_TERMINAL_URL,
) -> OrganismRuntimeStatus:
    root = repo_root_from(root)
    wake_manifest = read_wake_up_manifest(root)
    manifest_feed_url = str(wake_manifest.get("runtime_feed_url") or "").strip()
    if manifest_feed_url and local_terminal_url == DEFAULT_LOCAL_TERMINAL_URL:
        local_terminal_url = manifest_feed_url
    safety = safe_observer_environment(wake_manifest)
    refresh_results = refresh_artifacts(root, refresh_core=refresh_core, refresh_heavy=refresh_heavy)

    domains = [build_domain_pulse(root, spec) for spec in DOMAIN_MANIFESTS]
    domains.extend(build_state_file_pulse(root, spec) for spec in STATE_FILES)

    runtime_feed = probe_local_runtime_feed(local_terminal_url)
    runtime_feed["flight_test"] = probe_runtime_flight_test(local_terminal_url) if runtime_feed.get("status") == "online" else {}
    public_status_path = root / DEFAULT_PUBLIC_JSON
    frontend_public = {
        "organism_runtime_status": public_status_path.exists(),
        "saas_inventory": (root / "frontend/public/aureon_saas_system_inventory.json").exists(),
        "frontend_unification": (root / "frontend/public/aureon_frontend_unification_plan.json").exists(),
        "frontend_evolution_queue": (root / "frontend/public/aureon_frontend_evolution_queue.json").exists(),
        "capability_switchboard": (root / "frontend/public/aureon_autonomous_capability_switchboard.json").exists(),
        "operational_ui_spec": (root / "frontend/public/aureon_operational_ui_spec.json").exists(),
    }
    runtime_feed["frontend_public_manifests"] = frontend_public
    action_capability = build_action_capability(runtime_feed, safety)

    blind_spots = build_blind_spots(domains, runtime_feed, refresh_results)
    freshness = compute_freshness(domains)
    high_count = sum(1 for item in blind_spots if item.severity == "high")
    stale_count = freshness["counts"]["stale"]
    missing_count = freshness["counts"]["missing"]
    failed_refresh = sum(1 for item in refresh_results if item.status != "ok")

    action_mode = str(action_capability.get("mode") or "safe_observation")
    if action_mode == "guarded_live_action":
        status_prefix = "organism_guarded_action"
    elif action_mode == "guarded_observe_plan":
        status_prefix = "organism_guarded_observe_plan"
    else:
        status_prefix = "organism_observing"

    if high_count or missing_count or failed_refresh:
        status = f"{status_prefix}_with_blind_spots"
    elif stale_count or blind_spots:
        status = f"{status_prefix}_with_attention"
    else:
        status = f"{status_prefix}_fresh"

    next_actions: list[str] = []
    seen_actions: set[str] = set()
    for item in blind_spots:
        if item.next_action and item.next_action not in seen_actions:
            next_actions.append(item.next_action)
            seen_actions.add(item.next_action)
    if not next_actions:
        next_actions.append("Keep the observer running with --watch to maintain a real-time organism pulse.")

    summary = {
        "domain_count": len(domains),
        "blind_spot_count": len(blind_spots),
        "high_blind_spot_count": high_count,
        "fresh_domain_count": freshness["counts"]["fresh"],
        "stale_domain_count": stale_count,
        "missing_domain_count": missing_count,
        "attention_domain_count": freshness["counts"]["attention"],
        "refresh_count": len(refresh_results),
        "failed_refresh_count": failed_refresh,
        "runtime_feed_status": runtime_feed.get("status"),
        "action_mode": action_mode,
        "trading_action_allowed": bool(action_capability.get("trading", {}).get("can_act")) if isinstance(action_capability.get("trading"), dict) else False,
        "frontend_public_manifest_count": sum(1 for value in frontend_public.values() if value),
    }
    trading_action = action_capability.get("trading", {}) if isinstance(action_capability.get("trading"), dict) else {}
    live_orders_allowed = bool(trading_action.get("can_act"))

    return OrganismRuntimeStatus(
        schema_version=SCHEMA_VERSION,
        generated_at=utc_now(),
        repo_root=str(root),
        status=status,
        mode=action_mode,
        safety={
            "observer_only": not live_orders_allowed,
            "live_orders_allowed": live_orders_allowed,
            "exchange_mutations_allowed": live_orders_allowed,
            "external_mutation_scope": (
                "exchange order intents only through existing runtime gates"
                if live_orders_allowed
                else "none"
            ),
            "official_filing_allowed": False,
            "payments_allowed": False,
            "external_mutations_allowed": live_orders_allowed,
            "environment": safety,
            "action_capability": action_capability,
        },
        summary=summary,
        domains=domains,
        blind_spots=blind_spots,
        data_freshness=freshness,
        refresh_results=list(refresh_results),
        real_time_feeds={"local_terminal": runtime_feed, "action_capability": action_capability},
        status_lines=build_status_lines(status, domains, blind_spots, runtime_feed, action_capability),
        next_actions=next_actions,
    )


def render_markdown(status: OrganismRuntimeStatus) -> str:
    data = status.to_dict()
    lines = [
        "# Aureon Organism Runtime Status",
        "",
        f"- Generated: `{status.generated_at}`",
        f"- Status: `{status.status}`",
        f"- Mode: `{status.mode}`",
        f"- Repo: `{status.repo_root}`",
        "",
        "## Summary",
        "",
    ]
    for key, value in status.summary.items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(
        [
            "",
            "## Safety",
            "",
            f"- Action mode: `{status.mode}`.",
            f"- Live orders allowed: `{bool(status.safety.get('live_orders_allowed'))}`.",
            f"- Exchange mutation scope: `{status.safety.get('external_mutation_scope', 'none')}`.",
            "- Official filings, payments, credential reveal, and unowned security mutations are blocked.",
            "",
            "## Domain Pulse",
            "",
            "| Status | Freshness | Domain | Source | Blind spots | Next action |",
            "| --- | --- | --- | --- | ---: | --- |",
        ]
    )
    for domain in status.domains:
        next_action = domain.next_action.replace("|", "\\|")
        lines.append(
            f"| `{domain.status}` | `{domain.freshness}` | `{domain.label}` | `{domain.source_path}` | "
            f"{len(domain.blind_spots)} | {next_action} |"
        )
    lines.extend(["", "## Blind Spots", ""])
    if status.blind_spots:
        lines.append("| Severity | Domain | Issue | Next action |")
        lines.append("| --- | --- | --- | --- |")
        for item in status.blind_spots[:200]:
            lines.append(
                f"| `{item.severity}` | `{item.domain}` | {item.issue.replace('|', _MD_PIPE)} | "
                f"{item.next_action.replace('|', _MD_PIPE)} |"
            )
    else:
        lines.append("- No blind spots detected in this observer pass.")
    lines.extend(["", "## Status Lines", ""])
    for line in status.status_lines:
        lines.append(f"- {line}")
    lines.extend(["", "## JSON Snapshot", "", "```json", json.dumps(data["summary"], indent=2, sort_keys=True), "```", ""])
    return "\n".join(lines)


def write_status(
    status: OrganismRuntimeStatus,
    markdown_path: Path = DEFAULT_OUTPUT_MD,
    json_path: Path = DEFAULT_OUTPUT_JSON,
    public_json_path: Path = DEFAULT_PUBLIC_JSON,
    vault_path: Path = DEFAULT_VAULT_NOTE,
) -> tuple[Path, Path, Path, Path]:
    root = Path(status.repo_root)
    md_path = markdown_path if markdown_path.is_absolute() else root / markdown_path
    js_path = json_path if json_path.is_absolute() else root / json_path
    public_path = public_json_path if public_json_path.is_absolute() else root / public_json_path
    note_path = vault_path if vault_path.is_absolute() else root / vault_path
    for path in (md_path, js_path, public_path, note_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    rendered = render_markdown(status)
    data = json.dumps(status.to_dict(), indent=2, sort_keys=True, default=str)
    md_path.write_text(rendered, encoding="utf-8")
    js_path.write_text(data, encoding="utf-8")
    public_path.write_text(data, encoding="utf-8")
    note_path.write_text(rendered, encoding="utf-8")
    return md_path, js_path, public_path, note_path


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish Aureon's safe live organism runtime pulse.")
    parser.add_argument("--repo-root", default="", help="Repo root; defaults to current Aureon repo.")
    parser.add_argument("--refresh-core", action="store_true", help="Refresh fast core manifests before building the pulse.")
    parser.add_argument("--refresh-heavy", action="store_true", help="Also refresh heavier self-catalog/mind-wiring audits.")
    parser.add_argument("--watch", action="store_true", help="Keep writing the pulse on an interval.")
    parser.add_argument("--interval", type=int, default=30, help="Watch interval in seconds.")
    parser.add_argument("--local-terminal-url", default=DEFAULT_LOCAL_TERMINAL_URL, help="Read-only local runtime status endpoint.")
    parser.add_argument("--markdown", default=str(DEFAULT_OUTPUT_MD), help="Markdown report path.")
    parser.add_argument("--json", default=str(DEFAULT_OUTPUT_JSON), help="JSON manifest path.")
    parser.add_argument("--public-json", default=str(DEFAULT_PUBLIC_JSON), help="Frontend-readable public JSON path.")
    parser.add_argument("--vault-note", default=str(DEFAULT_VAULT_NOTE), help="Vault note path.")
    parser.add_argument("--no-write", action="store_true", help="Print summary without writing artifacts.")
    return parser.parse_args(argv)


def run_once(args: argparse.Namespace) -> OrganismRuntimeStatus:
    root = Path(args.repo_root).resolve() if args.repo_root else repo_root_from()
    status = build_organism_runtime_status(
        root,
        refresh_core=bool(args.refresh_core),
        refresh_heavy=bool(args.refresh_heavy),
        local_terminal_url=str(args.local_terminal_url),
    )
    if not args.no_write:
        write_status(status, Path(args.markdown), Path(args.json), Path(args.public_json), Path(args.vault_note))
    return status


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    while True:
        status = run_once(args)
        print(
            json.dumps(
                {
                    "status": status.status,
                    "json": str((repo_root_from(Path(args.repo_root)) if args.repo_root else repo_root_from()) / Path(args.json)),
                    "public_json": str((repo_root_from(Path(args.repo_root)) if args.repo_root else repo_root_from()) / Path(args.public_json)),
                    "summary": status.summary,
                },
                indent=2,
                sort_keys=True,
            ),
            flush=True,
        )
        if not args.watch:
            return 0
        time.sleep(max(5, int(args.interval)))


if __name__ == "__main__":
    raise SystemExit(main())
