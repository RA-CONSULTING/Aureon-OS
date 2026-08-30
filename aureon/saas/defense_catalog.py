"""
Defense & Validation catalog — the bio family surfaced for the console.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The bio package now carries 29 Tier-A-benchmarked modules — the derived-signal **sensor
lanes**, the **statistical-validity dossier** (size, power, calibration, multiple-comparison
error control), and the **cognitive immune layer** (integrity guard · swarm defense · MCP
membrane · authenticity discriminator · immune memory · immune regulation). The SaaS catalog
counts them anonymously; nothing presented them together, by group, with honest status.

This is that surface. It is **registry-as-data + report-derived status**: the grouping is
static here; the live ``{passed, metrics, evidence, truth_status}`` is read from the committed
Tier-A benchmark report (``tests/benchmarks/report.json``) and overlaid with the module's most
recent ThoughtBus **bus-trace** when it has actually run. Nothing heavy is cold-booted — the
bio modules are **never imported or executed on a request**; a module that has neither been
benchmarked nor run reports ``no_data``, never a fabricated status.

Gary Leckey · Aureon Institute
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger("aureon.saas.defense_catalog")

_REPO_ROOT = Path(__file__).resolve().parents[2]
_REPORT_PATH = _REPO_ROOT / "tests" / "benchmarks" / "report.json"

# ── the three groups (what layer of the body a bio module belongs to) ─────────
_GROUP_META: Dict[str, Dict[str, str]] = {
    "cognitive_immune_layer": {
        "label": "Cognitive immune layer",
        "purpose": "the organism's border defenses — detect tampering with its pinned "
                   "invariants, mount a leaderless quorum response, and hold the boundary "
                   "when attached to a flagship model (sensor → effector → membrane)",
    },
    "statistical_validity": {
        "label": "Statistical-validity dossier",
        "purpose": "the falsifiability audits — the same φ detector's size, detection power, "
                   "null calibration, and multiple-comparison error control (FWER + FDR), "
                   "each reported exactly as the pre-registered test returns it",
    },
    "adaptive_direction": {
        "label": "Adaptive-direction integrity",
        "purpose": "proof that the adaptive logic is directed by the one canonical HNC field and that "
                   "the flagship-model connection is a stable, isolated bridge in BOTH directions — a "
                   "source-level direction audit (every consumer on the shared field), an inbound "
                   "read-only connector (any model served a gated, screened, interior-proven surface), "
                   "and an outbound reply membrane (whatever a model says back is screened as "
                   "data-not-instructions before Aureon acts on it)",
    },
    "sensor_lane": {
        "label": "Sensor lanes",
        "purpose": "the derived-signal lanes — every modality (image · audio · video · sky · "
                   "market · UPE · sacred lattice · harmonic core · observatory) scanned through "
                   "the one unchanged φ engine",
    },
    "market_validation": {
        "label": "HNC market validation",
        "purpose": "the proof the trading mind is calibrated — the volatility sentinel's "
                   "predictive veto pinned on a labeled regime library, and the whole "
                   "HNC/Auris/sentinel stack replayed over REAL open exchange history "
                   "(provenance-stamped, integrity-proven, no API keys) with profit margins "
                   "attributed per gate: every layer earns its place in measured numbers, "
                   "never assertion",
    },
    "universal_prompt_router": {
        "label": "Universal prompt router",
        "purpose": "the one door for every prompt — chat, API, coding, research all enter "
                   "through the same Operator/Cognition gateway (the route audit is re-proven "
                   "from source each run), each request classified against the goal-capability "
                   "map, complex multi-role prompts councilled by a deterministic swarm cluster, "
                   "and every answer wearing the enforced envelope: sources named or 'general "
                   "knowledge, no repo hit' stated, conscience verdict, trace id, and an honest "
                   "ok / honest_unavailable / fault status — offline the pipeline says so, "
                   "it never hallucinates; the heart charter rides every envelope: the "
                   "organism's measured life score, its honest affect channel, and the "
                   "consequence ledger of the power it exercised or withheld",
    },
    "harmonic_swarm": {
        "label": "Harmonic swarm (hive mind)",
        "purpose": "the HNC-grounded multi-agent company — every agent a harmonic "
                   "mode with its own probability simplex (soft mass, never hard "
                   "votes), clusters owning tasks (never a single agent), Γ as a "
                   "measured rolling correlation, steering that shapes and never "
                   "arrests, the island of stability enforced on β, realized-only "
                   "causal-echo memory, and a Queen gate the canonical field may "
                   "only tighten",
    },
    "kings_court_accounting": {
        "label": "King's Court accounting",
        "purpose": "the commercial HNC accounting body — multi-client double-entry books in "
                   "integer pennies where every posting is a measured coordination step, "
                   "file-drop ingestion that parks the unexplained in suspense (never guessed), "
                   "the Throne agent seat that names codes only from the chart, and statutory "
                   "shapes (P&L, balance sheet, MTD VAT 9-box, FRS 105) that self-prove from "
                   "the same books — drafts for review, nothing transmits to HMRC or "
                   "Companies House",
    },
    "measured_benchmarks": {
        "label": "Measured benchmarks",
        "purpose": "the honesty layer over the benchmarks themselves — Aureon scored on "
                   "OPEN sources (GSM8K, HumanEval) through the one door with the engine "
                   "named, the competition cited by source URL and never claimed, and the "
                   "march to a full 100% benchmark of the OS made falsifiable: every Tier-A "
                   "pin reconciled against the real filesystem, the uncovered domains named "
                   "as the roadmap, and progress held by a one-way ratchet",
    },
}
_GROUP_ORDER: List[str] = [
    "cognitive_immune_layer", "statistical_validity", "adaptive_direction", "sensor_lane",
    "market_validation", "kings_court_accounting", "harmonic_swarm", "universal_prompt_router",
    "measured_benchmarks",
]

# module-basename (no .py) → group; anything else under aureon/bio/ is a sensor lane
_GROUPS: Dict[str, str] = {
    "integrity_guard": "cognitive_immune_layer",
    "swarm_defense": "cognitive_immune_layer",
    "mcp_membrane": "cognitive_immune_layer",
    "authenticity_discriminator": "cognitive_immune_layer",
    "immune_memory": "cognitive_immune_layer",
    "immune_regulation": "cognitive_immune_layer",
    "proxy_suite": "statistical_validity",
    "null_calibration": "statistical_validity",
    "power_analysis": "statistical_validity",
    "calibration_curve": "statistical_validity",
    "multiplicity": "statistical_validity",
    "false_discovery": "statistical_validity",
    "hnc_direction_audit": "adaptive_direction",
    "mcp_transport": "adaptive_direction",
    "direction_runtime": "adaptive_direction",
    "brain_reply_membrane": "adaptive_direction",
    # non-bio modules admitted by explicit mapping only (see build filter)
    "volatility_sentinel_benchmark": "market_validation",
    "historical_replay_validation": "market_validation",
    "client_ledger": "kings_court_accounting",
    "company": "harmonic_swarm",
    "capability_grid": "harmonic_swarm",
    "fleadh": "harmonic_swarm",
    "containment": "harmonic_swarm",
    "prompt_router": "universal_prompt_router",
    "cognition": "universal_prompt_router",
    "bake": "universal_prompt_router",
    "acquisition": "universal_prompt_router",
    "coherence_gate": "universal_prompt_router",
    "heart": "universal_prompt_router",
    "hnc_field": "adaptive_direction",              # b64: the one-field seam itself
    "open_benchmark": "measured_benchmarks",
    "benchmark_coverage": "measured_benchmarks",
}

# module-basename → bus-trace name (the emit_* mirror), for the live overlay only
_TRACE_NAMES: Dict[str, str] = {
    "integrity_guard": "integrity_guard",
    "swarm_defense": "swarm_defense",
    "mcp_membrane": "mcp_membrane",
    "authenticity_discriminator": "authenticity_discriminator",
    "immune_memory": "immune_memory",
    "immune_regulation": "immune_regulation",
    "proxy_suite": "signal_adapter_suite",
    "null_calibration": "null_calibration",
    "power_analysis": "power_analysis",
    "calibration_curve": "calibration_curve",
    "multiplicity": "multiplicity",
    "false_discovery": "false_discovery",
    "hnc_direction_audit": "hnc_direction_audit",
    "mcp_transport": "mcp_transport",
    "direction_runtime": "direction_runtime",
    "brain_reply_membrane": "brain_reply_membrane",
    "celestial_observatory": "observatory",
}


def _load_report() -> Dict[str, Any]:
    """Read the committed Tier-A benchmark report; guarded → ``{}`` if absent/corrupt."""
    try:
        return json.loads(_REPORT_PATH.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 — a missing report is no_data, never a crash
        logger.debug("defense catalog: report unreadable (%s)", exc)
        return {}


def _basename(module: str) -> str:
    return Path(str(module)).stem


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(text).lower()).strip("_") or "entry"


def _latest_trace(name: str) -> Dict[str, Any] | None:
    """Most recent bus-trace row for ``name`` (the live overlay); never raises."""
    try:
        from aureon.core.bus_trace import read_trace_latest

        return read_trace_latest(name)
    except Exception as exc:  # noqa: BLE001 — trace bridge is best-effort
        logger.debug("defense catalog: trace read failed for %s (%s)", name, exc)
        return None


def build_defense_catalog() -> Dict[str, Any]:
    """The bio family — sensor lanes, statistical-validity dossier, cognitive immune layer —
    grouped, with real ``passed``/``metrics``/``evidence`` from the committed Tier-A report and
    a live bus-trace overlay where a module has run. Pure-read, never imports/executes a bio
    module, never raises."""
    from aureon.saas.cognitive import provenance_block

    report = _load_report()
    tier_a = report.get("tier_a", []) if isinstance(report, dict) else []
    generated_at = report.get("ts") if isinstance(report, dict) else None

    rows: List[Dict[str, Any]] = []
    for entry in tier_a:
        module = str(entry.get("module", ""))
        base = _basename(module)
        # bio modules are always in (default group: sensor lane); a non-bio
        # module joins ONLY by explicit mapping — connections are registered
        # by name, never inferred
        if not (module.startswith("aureon/bio/") or base in _GROUPS):
            continue
        group = _GROUPS.get(base, "sensor_lane")
        invariants = entry.get("invariants", {}) if isinstance(entry.get("invariants"), dict) else {}
        inv_pass = sum(1 for v in invariants.values() if v)

        # live overlay: if the module has actually run, lift its boundary + mark live
        boundary = None
        truth_status = "real_derived" if entry else "no_data"
        trace_name = _TRACE_NAMES.get(base)
        if trace_name:
            latest = _latest_trace(trace_name)
            if isinstance(latest, dict):
                boundary = latest.get("boundary")
                truth_status = "live"

        rows.append({
            "key": _slug(entry.get("name", base)),
            "name": entry.get("name", base),
            "module": module,
            "group": group,
            "passed": bool(entry.get("passed", False)),
            "metrics": entry.get("metrics", {}) if isinstance(entry.get("metrics"), dict) else {},
            "invariants_passed": inv_pass,
            "invariants_total": len(invariants),
            "evidence": str(entry.get("evidence", ""))[:400],
            "boundary": boundary,
            "truth_status": truth_status,
        })

    groups: Dict[str, Any] = {}
    for gkey in _GROUP_ORDER:
        members = [r for r in rows if r["group"] == gkey]
        meta = _GROUP_META[gkey]
        groups[gkey] = {
            "label": meta["label"],
            "purpose": meta["purpose"],
            "module_count": len(members),
            "passing": sum(1 for r in members if r["passed"]),
            "modules": members,
        }

    n_modules = len(rows)
    n_passing = sum(1 for r in rows if r["passed"])
    overall = ("live" if any(r["truth_status"] == "live" for r in rows)
               else "real_derived" if n_modules else "no_data")

    return {
        "generated_at": generated_at,
        "group_order": _GROUP_ORDER,
        "groups": groups,
        "counts": {"total": n_modules, "passing": n_passing, "groups": len(_GROUP_ORDER)},
        "note": "the bio family — sensor lanes, statistical-validity dossier, and cognitive "
                "immune layer — surfaced from the committed Tier-A benchmark report and live "
                "bus-traces; read-only, the modules are never run on a request",
        "provenance": provenance_block(),
        "truth_status": overall,
    }
