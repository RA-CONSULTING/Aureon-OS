"""Trading intelligence freshness checklist.

This module turns the live trading runtime snapshot into a checklist showing
which intelligence and counter-intelligence systems are present, active,
fresh-live, and wired into the HNC/Auris decision path.
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence

from aureon.autonomous.runtime_status_source import read_runtime_status


SCHEMA_VERSION = "aureon-trading-intelligence-checklist-v1"
REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_STATUS_PATH = Path("state/unified_runtime_status.json")
DEFAULT_OUTPUT_JSON = REPO_ROOT / "docs/audits/aureon_trading_intelligence_checklist.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs/audits/aureon_trading_intelligence_checklist.md"
DEFAULT_PUBLIC_JSON = REPO_ROOT / "frontend/public/aureon_trading_intelligence_checklist.json"
DATA_OCEAN_STATUS_PATH = Path("state/aureon_data_ocean_status.json")
GLOBAL_COVERAGE_PATH = Path("docs/audits/aureon_global_financial_coverage_map.json")
EXCHANGE_CHECKLIST_PATH = Path("docs/audits/aureon_exchange_monitoring_checklist.json")

LIVE_MARKET = "live_market_intelligence"
HNC_AURIS = "hnc_auris_cognition"
COUNTER_INTELLIGENCE = "counter_intelligence_validation"
PROFIT_TIMING = "profit_timing"
RESEARCH_CONTEXT = "research_context_mesh"
META_COGNITIVE = "metacognitive_data_context"

HNC_AURIS_NAMES = {
    "HNCMasterProtocol",
    "HNCProbabilityMatrix",
    "Seer",
    "Lyra",
    "KingCapitalLogic",
    "AurisNodes",
    "HNCOperatingCycle",
}
COUNTER_NAMES = {
    "PhantomSignalFilter",
    "ShadowTradeValidator",
    "SelfValidatingPredictor",
    "TruthPredictionEngine",
    "RuntimeWatchdog",
    "APIGovernor",
    "ExchangeRouteClearance",
    "CapitalPortfolioMemory",
    "CapitalLeverageEnvelope",
    "CapitalStressBuffer",
    "CapitalDynamicLaneControl",
    "CapitalUnifiedWaveformCheck",
    "CapitalConfidenceRatchet",
}
PROFIT_NAMES = {
    "MicroMomentumGoal",
    "FastMoneySelector",
    "FastMoneySelectorRuntime",
    "OrderBookPressure",
    "OrderBookPressureRuntime",
    "PennyProfitEngine",
    "DynamicTakeProfit",
    "TemporalTradeCognition",
    "TorchBearerSystem",
    "RisingStarLogic",
    "ProfitVelocityRanker",
}
RESEARCH_NAMES = {
    "NewsSignal",
    "QueenOnlineResearcher",
    "ResearchCorpusIndex",
    "QueenRepositoryScanner",
    "MinerBrain",
}
META_COGNITIVE_NAMES = {
    "DataOceanCognitiveContext",
    "PlanetaryCoverageMap",
    "ExchangeWaveformMemory",
}
LIVE_NAMES = {
    "LiveExchangeFeeds",
    "LiveStreamCache",
    "LiveStreamCacheRuntime",
    "UnifiedSignalEngine",
    "ModelSignalFeed",
    "OrcaIntelligence",
    "OrderBookPressure",
    "OrderBookPressureRuntime",
}
TRUST_TO_DECIDE_THRESHOLD = 0.62
TRUST_TO_SHADOW_THRESHOLD = 0.42


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
        if math.isfinite(number):
            return number
    except Exception:
        pass
    return default


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(_as_float(value, default))
    except Exception:
        return default


def _clamp01(value: Any, default: float = 0.0) -> float:
    return max(0.0, min(1.0, _as_float(value, default)))


def _ratio(value: Any, total: Any) -> float:
    denominator = max(1, _as_int(total, 0))
    return _clamp01(_as_float(value, 0.0) / float(denominator))


def _runtime_stale(runtime: dict[str, Any]) -> bool:
    watchdog = runtime.get("runtime_watchdog") if isinstance(runtime.get("runtime_watchdog"), dict) else {}
    return bool(runtime.get("stale") or watchdog.get("tick_stale"))


def _stale_reason(runtime: dict[str, Any]) -> str:
    watchdog = runtime.get("runtime_watchdog") if isinstance(runtime.get("runtime_watchdog"), dict) else {}
    return str(runtime.get("stale_reason") or watchdog.get("tick_stale_reason") or "runtime_stale")


def _runtime_fresh(runtime: dict[str, Any]) -> bool:
    return bool(runtime.get("data_ready") and not _runtime_stale(runtime))


def _mesh(runtime: dict[str, Any]) -> dict[str, Any]:
    plan = runtime.get("exchange_action_plan") if isinstance(runtime.get("exchange_action_plan"), dict) else {}
    order_flow = runtime.get("order_flow_feed") if isinstance(runtime.get("order_flow_feed"), dict) else {}
    for candidate in (
        runtime.get("intelligence_mesh"),
        plan.get("intelligence_mesh"),
        order_flow.get("intelligence_mesh"),
    ):
        if isinstance(candidate, dict):
            return candidate
    return {}


def _category_for(name: str, facet: str, wire: str) -> str:
    if name in META_COGNITIVE_NAMES or facet in {"metacognitive_data_context", "planetary_financial_ocean", "exchange_waveform_memory"}:
        return META_COGNITIVE
    if name in HNC_AURIS_NAMES or wire == "hnc_proof" or facet in {"hnc_harmonic", "harmonic_affect", "oracle_forecast", "capital_logic"}:
        return HNC_AURIS
    if name in COUNTER_NAMES or facet in {"noise_filter", "self_validation", "prediction_truth"}:
        return COUNTER_INTELLIGENCE
    if name in PROFIT_NAMES or facet in {"fast_profit_eta", "fast_money_selection", "orderbook_pressure", "exit_logic", "temporal_trade_logic", "fast_strike_strategy", "whole_market_search"}:
        return PROFIT_TIMING
    if name in RESEARCH_NAMES or wire in {"research_context", "sentiment_context"}:
        return RESEARCH_CONTEXT
    if name in LIVE_NAMES or wire in {"direct_live_signal", "model_stack", "thought_bus"} or facet in {"live_market_data", "live_stream_data", "signal_fusion", "whale_intelligence"}:
        return LIVE_MARKET
    return COUNTER_INTELLIGENCE if wire == "mesh_context" else LIVE_MARKET


def _stage_for(name: str, category: str, wire: str) -> str:
    if category == META_COGNITIVE:
        return "metacognitive_context"
    if name == "AurisNodes":
        return "auris_state"
    if category == HNC_AURIS:
        return "hnc_proof"
    if name == "ShadowTradeValidator" or category == COUNTER_INTELLIGENCE:
        return "shadow_validation" if name in {"ShadowTradeValidator", "PhantomSignalFilter", "SelfValidatingPredictor", "TruthPredictionEngine"} else "exchange_action_plan"
    if category == PROFIT_TIMING:
        return "profit_velocity"
    if wire == "direct_live_signal" or category == LIVE_MARKET:
        return "market_feed"
    return "exchange_action_plan"


def _evidence_timestamp(runtime: dict[str, Any], stage: str, fallback: str) -> str:
    plan = runtime.get("exchange_action_plan") if isinstance(runtime.get("exchange_action_plan"), dict) else {}
    shadow = runtime.get("shadow_trading") if isinstance(runtime.get("shadow_trading"), dict) else {}
    hnc = runtime.get("hnc_cognitive_proof") if isinstance(runtime.get("hnc_cognitive_proof"), dict) else {}
    watchdog = runtime.get("runtime_watchdog") if isinstance(runtime.get("runtime_watchdog"), dict) else {}
    if stage == "metacognitive_context":
        return str(runtime.get("dashboard_generated_at") or watchdog.get("heartbeat_at") or fallback)
    if stage in {"hnc_proof", "auris_state"}:
        return str(hnc.get("generated_at") or fallback)
    if stage == "shadow_validation":
        return str(shadow.get("generated_at") or plan.get("generated_at") or fallback)
    if stage in {"exchange_action_plan", "profit_velocity"}:
        return str(plan.get("generated_at") or fallback)
    return str(watchdog.get("heartbeat_at") or runtime.get("dashboard_generated_at") or fallback)


def _summary_from_report(report: Any) -> dict[str, Any]:
    if not isinstance(report, dict):
        return {}
    summary = report.get("summary")
    return summary if isinstance(summary, dict) else {}


def _metacognitive_data_context(root: Path, runtime: dict[str, Any]) -> dict[str, Any]:
    data_ocean = _read_json(root / DATA_OCEAN_STATUS_PATH, {})
    global_map = _read_json(root / GLOBAL_COVERAGE_PATH, {})
    exchange_checklist = _read_json(root / EXCHANGE_CHECKLIST_PATH, {})
    data_summary = _summary_from_report(data_ocean)
    global_summary = _summary_from_report(global_map)
    exchange_summary = _summary_from_report(exchange_checklist)
    present = bool(data_ocean or global_map or exchange_checklist)

    mapping_complete = bool(
        data_ocean.get("mapping_complete")
        or global_map.get("mapping_complete")
        or data_summary.get("coverage_percent") == 100.0
        or global_summary.get("mapping_complete")
    )
    coverage_percent = max(
        _as_float(data_summary.get("coverage_percent")),
        _as_float(global_summary.get("coverage_percent")),
    )
    configured_reachable_count = max(
        _as_int(data_summary.get("configured_reachable_count")),
        _as_int(global_summary.get("configured_reachable_source_count")),
    )
    usable_source_count = max(
        _as_int(data_summary.get("usable_source_count")),
        _as_int(global_summary.get("usable_source_count")),
    )
    decision_usable_source_count = max(
        _as_int(data_summary.get("decision_usable_source_count")),
        _as_int(global_summary.get("decision_usable_source_count")),
        _as_int(global_summary.get("decision_fed_exchange_count")),
    )
    active_live_source_count = _as_int(global_summary.get("active_live_source_count"))
    fresh_exchange_count = _as_int(exchange_summary.get("fresh_exchange_count") or global_summary.get("fresh_exchange_count"))
    waveform_history_exchange_count = _as_int(exchange_summary.get("waveform_history_exchange_count"))
    if waveform_history_exchange_count <= 0:
        waveform_history_exchange_count = fresh_exchange_count if bool(global_summary.get("history_db_present")) else 0
    live_ticker_count = _as_int(global_summary.get("live_ticker_count"))
    history_rows = _as_int(global_summary.get("total_history_rows"))
    fresh_domain_count = _as_int(global_summary.get("fresh_domain_count"))
    usable_domain_count = _as_int(global_summary.get("usable_domain_count"))

    coverage_ready = bool(coverage_percent >= 99.0)
    sources_ready = bool(configured_reachable_count == 0 or usable_source_count >= configured_reachable_count)
    live_ready = bool(active_live_source_count > 0 and live_ticker_count > 0)
    history_ready = bool(history_rows > 0)
    exchange_waveform_ready = bool(fresh_exchange_count > 0 and waveform_history_exchange_count > 0)
    usable_for_metacognition = bool(
        present and mapping_complete and coverage_ready and sources_ready and live_ready and history_ready and exchange_waveform_ready
    )
    runtime_fresh = _runtime_fresh(runtime)
    usable_for_live_decision = bool(usable_for_metacognition and runtime_fresh)
    blockers: list[str] = []
    if not present:
        blockers.append("metacognitive_data_reports_missing")
    if present and not mapping_complete:
        blockers.append("configured_registry_not_fully_mapped")
    if present and not coverage_ready:
        blockers.append("coverage_below_configured_threshold")
    if present and not sources_ready:
        blockers.append("configured_sources_not_all_usable_for_mapping")
    if present and not live_ready:
        blockers.append("live_ticker_context_missing")
    if present and not history_ready:
        blockers.append("historical_waveform_memory_missing")
    if present and not exchange_waveform_ready:
        blockers.append("exchange_waveform_memory_not_proven")
    if usable_for_metacognition and not runtime_fresh:
        blockers.append(_stale_reason(runtime) if _runtime_stale(runtime) else "runtime_data_not_ready")

    factors = [
        1.0 if mapping_complete else 0.0,
        _clamp01(coverage_percent / 100.0),
        _ratio(usable_source_count, configured_reachable_count),
        _ratio(active_live_source_count, 4),
        _clamp01(live_ticker_count / 3000.0),
        _clamp01(history_rows / 60000.0),
        _ratio(fresh_exchange_count, 4),
    ]
    cleanliness = round(sum(factors) / len(factors), 6) if factors else 0.0
    if usable_for_live_decision:
        phrase = "Planetary data ocean is mapped, fresh, and cleared for live decision context."
    elif usable_for_metacognition:
        phrase = "Planetary data ocean is mapped and usable for thought, but live action waits on runtime freshness."
    elif present:
        phrase = "Planetary data ocean is partially visible; Aureon can learn from it but must keep filling gaps."
    else:
        phrase = "Planetary data ocean evidence is missing from this cycle."

    return {
        "present": present,
        "usable_for_metacognition": usable_for_metacognition,
        "usable_for_live_decision": usable_for_live_decision,
        "decision_blocker": ", ".join(dict.fromkeys(blockers)),
        "mapping_complete": mapping_complete,
        "coverage_percent": round(coverage_percent, 6),
        "configured_reachable_source_count": configured_reachable_count,
        "usable_source_count": usable_source_count,
        "decision_usable_source_count": decision_usable_source_count,
        "active_live_source_count": active_live_source_count,
        "fresh_exchange_count": fresh_exchange_count,
        "waveform_history_exchange_count": waveform_history_exchange_count,
        "live_ticker_count": live_ticker_count,
        "history_rows": history_rows,
        "fresh_domain_count": fresh_domain_count,
        "usable_domain_count": usable_domain_count,
        "cognitive_cleanliness_score": cleanliness,
        "planetary_context_ready": bool(mapping_complete and coverage_ready and sources_ready and live_ready),
        "exchange_waveform_ready": exchange_waveform_ready,
        "state_phrase": phrase,
        "evidence_sources": [
            str(DATA_OCEAN_STATUS_PATH).replace("\\", "/"),
            str(GLOBAL_COVERAGE_PATH).replace("\\", "/"),
            str(EXCHANGE_CHECKLIST_PATH).replace("\\", "/"),
        ],
    }


def _row(
    *,
    name: str,
    facet: str,
    wire: str,
    path: str,
    present: bool,
    active: bool,
    fed: bool,
    runtime: dict[str, Any],
    evidence_source: str,
    stage: str,
    extra_blockers: Optional[list[str]] = None,
) -> dict[str, Any]:
    runtime_fresh = _runtime_fresh(runtime)
    blockers = list(extra_blockers or [])
    if not present:
        blockers.append("repo_path_missing")
    if present and not active:
        blockers.append("not_active_this_cycle")
    if not fed:
        blockers.append("not_wired_to_decision_logic")
    if not runtime_fresh:
        blockers.append(_stale_reason(runtime) if _runtime_stale(runtime) else "runtime_data_not_ready")
    fresh = bool(present and active and runtime_fresh)
    usable = bool(fresh and fed and not blockers)
    category = _category_for(name, facet, wire)
    return {
        "system": name,
        "category": category,
        "facet": facet,
        "wire_path": wire,
        "path": path,
        "evidence_source": evidence_source,
        "last_timestamp": _evidence_timestamp(runtime, stage, utc_now()),
        "present": bool(present),
        "active_this_cycle": bool(active),
        "fresh": fresh,
        "usable_for_decision": usable,
        "fed_to_decision_logic": bool(fed),
        "blocker": ", ".join(dict.fromkeys(blockers)),
        "downstream_stage": stage,
    }


def _capability_rows(runtime: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    mesh = _mesh(runtime)
    capabilities = mesh.get("capabilities") if isinstance(mesh.get("capabilities"), list) else []
    for capability in capabilities:
        if not isinstance(capability, dict):
            continue
        name = str(capability.get("name") or "UnknownSystem")
        facet = str(capability.get("facet") or "uncategorized")
        wire = str(capability.get("wire") or "mesh_context")
        category = _category_for(name, facet, wire)
        stage = _stage_for(name, category, wire)
        active = bool(capability.get("active_this_cycle"))
        fed = bool(active and category in {LIVE_MARKET, HNC_AURIS, COUNTER_INTELLIGENCE, PROFIT_TIMING, RESEARCH_CONTEXT})
        rows.append(
            _row(
                name=name,
                facet=facet,
                wire=wire,
                path=str(capability.get("path") or ""),
                present=bool(capability.get("present")),
                active=active,
                fed=fed,
                runtime=runtime,
                evidence_source=f"state/unified_runtime_status.json#exchange_action_plan.intelligence_mesh.capabilities.{name}",
                stage=stage,
            )
        )
    return rows


def _candidate_has_model_signal(candidate: Any) -> bool:
    return isinstance(candidate, dict) and isinstance(candidate.get("model_signal"), dict) and bool(candidate.get("model_signal"))


def _synthetic_rows(runtime: dict[str, Any], root: Path = REPO_ROOT) -> list[dict[str, Any]]:
    code_root = root if (root / "aureon").exists() else REPO_ROOT
    plan = runtime.get("exchange_action_plan") if isinstance(runtime.get("exchange_action_plan"), dict) else {}
    shadow = runtime.get("shadow_trading") if isinstance(runtime.get("shadow_trading"), dict) else {}
    hnc = runtime.get("hnc_cognitive_proof") if isinstance(runtime.get("hnc_cognitive_proof"), dict) else {}
    watchdog = runtime.get("runtime_watchdog") if isinstance(runtime.get("runtime_watchdog"), dict) else {}
    governor = runtime.get("api_governor") if isinstance(runtime.get("api_governor"), dict) else {}
    capital_risk = runtime.get("capital_risk_envelope") if isinstance(runtime.get("capital_risk_envelope"), dict) else {}
    capital_evidence = runtime.get("capital_trade_evidence") if isinstance(runtime.get("capital_trade_evidence"), dict) else {}
    capital_ratchet = runtime.get("capital_confidence_ratchet") if isinstance(runtime.get("capital_confidence_ratchet"), dict) else {}
    capital_waveform = runtime.get("capital_unified_waveform_check") if isinstance(runtime.get("capital_unified_waveform_check"), dict) else {}
    kraken_registry = runtime.get("kraken_asset_registry") if isinstance(runtime.get("kraken_asset_registry"), dict) else {}
    if not capital_risk and isinstance(runtime.get("capital"), dict):
        capital_risk = runtime["capital"].get("capital_risk_envelope") if isinstance(runtime["capital"].get("capital_risk_envelope"), dict) else {}
    if not capital_evidence and isinstance(runtime.get("capital"), dict):
        capital_evidence = runtime["capital"].get("capital_trade_evidence") if isinstance(runtime["capital"].get("capital_trade_evidence"), dict) else {}
    if not capital_ratchet and isinstance(runtime.get("capital"), dict):
        capital_ratchet = runtime["capital"].get("capital_confidence_ratchet") if isinstance(runtime["capital"].get("capital_confidence_ratchet"), dict) else {}
    if not capital_waveform and isinstance(runtime.get("capital"), dict):
        capital_waveform = runtime["capital"].get("capital_unified_waveform_check") if isinstance(runtime["capital"].get("capital_unified_waveform_check"), dict) else {}
    if not kraken_registry and isinstance(runtime.get("combined"), dict):
        kraken_registry = runtime["combined"].get("kraken_asset_registry") if isinstance(runtime["combined"].get("kraken_asset_registry"), dict) else {}
    stream_cache = runtime.get("live_stream_cache") if isinstance(runtime.get("live_stream_cache"), dict) else {}
    shared_order_flow = runtime.get("shared_order_flow") if isinstance(runtime.get("shared_order_flow"), dict) else {}
    fast_money = shared_order_flow.get("fast_money_intelligence") if isinstance(shared_order_flow.get("fast_money_intelligence"), dict) else {}
    scanner_fusion = shared_order_flow.get("scanner_fusion_matrix") if isinstance(shared_order_flow.get("scanner_fusion_matrix"), dict) else {}
    venues = plan.get("venues") if isinstance(plan.get("venues"), dict) else {}
    candidates: list[Any] = []
    for venue in venues.values():
        if isinstance(venue, dict):
            top = venue.get("top_candidates")
            if isinstance(top, list):
                candidates.extend(top)
    ready_venues = _as_int(plan.get("ready_venue_count"))
    venue_count = _as_int(plan.get("venue_count"), len(venues))
    runtime_clearances = plan.get("runtime_clearances") if isinstance(plan.get("runtime_clearances"), list) else []
    model_active = bool(plan.get("model_coverage") or any(_candidate_has_model_signal(item) for item in candidates))
    profit_active = bool(
        "profit_velocity" in str(plan.get("selection_process", {}).get("mode") if isinstance(plan.get("selection_process"), dict) else "")
        or any(isinstance(item, dict) and item.get("profit_velocity_score") is not None for item in candidates)
    )
    auris = hnc.get("auris_nodes") if isinstance(hnc.get("auris_nodes"), dict) else {}
    operating_cycle = runtime.get("hnc_operating_cycle") if isinstance(runtime.get("hnc_operating_cycle"), dict) else {}
    if not operating_cycle and isinstance(hnc.get("operating_cycle"), dict):
        operating_cycle = hnc.get("operating_cycle") or {}
    if not operating_cycle and isinstance(hnc.get("hnc_operating_cycle"), dict):
        operating_cycle = hnc.get("hnc_operating_cycle") or {}
    cycle_order = operating_cycle.get("cycle_order") if isinstance(operating_cycle.get("cycle_order"), list) else []
    expected_cycle = ["who", "what", "where", "when", "how", "act"]
    missing_cycle_steps = [step for step in expected_cycle if step not in cycle_order]
    operating_cycle_active = bool(
        operating_cycle.get("passed")
        or operating_cycle.get("fed_to_decision_logic")
        or _as_int(operating_cycle.get("passed_count")) > 0
    )
    shadow_active = bool(shadow.get("enabled", True) and (shadow.get("shadow_opened_count") is not None or shadow.get("active_shadow_count") is not None))
    stream_active = bool(stream_cache.get("fresh") and _as_int(stream_cache.get("symbol_count")) > 0)
    stream_report_present = bool(stream_cache)
    stream_fed = bool(stream_cache.get("usable_for_decision") or stream_active)
    fast_money_report_present = bool(fast_money)
    fast_money_active = bool(
        fast_money.get("active_this_cycle")
        or _as_int(fast_money.get("candidate_count")) > 0
        or _as_int(fast_money.get("evaluated_candidate_count")) > 0
        or _as_int(fast_money.get("active_order_flow_count")) > 0
    )
    fast_money_fed = bool(fast_money.get("fed_to_decision_logic") or fast_money_active)
    orderbook_attempt_count = _as_int(fast_money.get("orderbook_attempt_count"))
    orderbook_probe_count = _as_int(fast_money.get("orderbook_probe_count"))
    orderbook_active = bool(orderbook_probe_count > 0 or orderbook_attempt_count > 0)
    orderbook_fed = bool(orderbook_probe_count > 0 or orderbook_attempt_count > 0)
    if not orderbook_active and isinstance(scanner_fusion.get("systems"), list):
        for system in scanner_fusion["systems"]:
            if isinstance(system, dict) and system.get("name") == "OrderBookPressure" and system.get("active_this_cycle"):
                orderbook_active = True
                orderbook_fed = bool(system.get("fed_to_decision_logic", True))
                break
    fast_money_path = "aureon/exchanges/unified_market_trader.py"
    orderbook_path = "aureon/analytics/aureon_whale_orderbook_analyzer.py"
    meta_context = _metacognitive_data_context(root, runtime)
    rows = [
        _row(
            name="LiveStreamCacheRuntime",
            facet="live_stream_data",
            wire="direct_live_signal",
            path="ws_cache/ws_prices.json",
            present=stream_report_present,
            active=stream_active,
            fed=stream_fed,
            runtime=runtime,
            evidence_source="state/unified_runtime_status.json#live_stream_cache",
            stage="market_feed",
            extra_blockers=[] if stream_active else [str(stream_cache.get("reason") or "stream_cache_not_fresh")],
        ),
        _row(
            name="FastMoneySelectorRuntime",
            facet="fast_money_selection",
            wire="profit_context",
            path=fast_money_path,
            present=bool((code_root / fast_money_path).exists()),
            active=fast_money_active,
            fed=fast_money_fed,
            runtime=runtime,
            evidence_source="state/unified_runtime_status.json#shared_order_flow.fast_money_intelligence",
            stage="profit_velocity",
            extra_blockers=[] if fast_money_report_present else ["fast_money_report_missing"],
        ),
        _row(
            name="OrderBookPressureRuntime",
            facet="orderbook_pressure",
            wire="direct_live_signal",
            path=orderbook_path,
            present=bool((code_root / orderbook_path).exists()),
            active=orderbook_active,
            fed=orderbook_fed,
            runtime=runtime,
            evidence_source="state/unified_runtime_status.json#shared_order_flow.fast_money_intelligence.orderbook_probe_count",
            stage="profit_velocity",
            extra_blockers=[] if orderbook_active else [str(fast_money.get("orderbook_reason") or "orderbook_pressure_not_sampled_this_cycle")],
        ),
        _row(
            name="ModelSignalFeed",
            facet="signal_fusion",
            wire="direct_live_signal",
            path="state/unified_runtime_status.json",
            present=bool(plan),
            active=model_active,
            fed=model_active,
            runtime=runtime,
            evidence_source="state/unified_runtime_status.json#exchange_action_plan.model_coverage/top_candidates",
            stage="market_feed",
        ),
        _row(
            name="AurisNodes",
            facet="sensory_market_texture",
            wire="hnc_proof",
            path="aureon/utils/aureon_queen_hive_mind.py",
            present=bool(auris),
            active=bool(auris.get("evaluated") or auris.get("node_count")),
            fed=bool(auris),
            runtime=runtime,
            evidence_source="state/unified_runtime_status.json#hnc_cognitive_proof.auris_nodes",
            stage="auris_state",
        ),
        _row(
            name="HNCOperatingCycle",
            facet="who_what_where_when_how_act",
            wire="hnc_proof",
            path="state/aureon_hnc_operating_cycle.json",
            present=bool(operating_cycle),
            active=operating_cycle_active,
            fed=bool(operating_cycle.get("fed_to_decision_logic")),
            runtime=runtime,
            evidence_source="state/unified_runtime_status.json#hnc_operating_cycle",
            stage="hnc_proof",
            extra_blockers=[f"missing_cycle_step:{step}" for step in missing_cycle_steps],
        ),
        _row(
            name="RuntimeWatchdog",
            facet="freshness_truth",
            wire="runtime_watchdog",
            path="state/unified_runtime_status.json",
            present=bool(watchdog),
            active=bool(watchdog.get("heartbeat_alive") or watchdog.get("tick_stale") is not None),
            fed=True,
            runtime=runtime,
            evidence_source="state/unified_runtime_status.json#runtime_watchdog",
            stage="exchange_action_plan",
        ),
        _row(
            name="APIGovernor",
            facet="api_rate_counter_intelligence",
            wire="exchange_action_plan",
            path="state/unified_runtime_status.json",
            present=bool(governor),
            active=bool(governor),
            fed=bool(governor),
            runtime=runtime,
            evidence_source="state/unified_runtime_status.json#api_governor",
            stage="exchange_action_plan",
        ),
        _row(
            name="KrakenTradableAssetRegistry",
            facet="kraken_spot_margin_asset_book",
            wire="direct_live_signal",
            path="aureon/exchanges/kraken_asset_registry.py",
            present=bool(kraken_registry and not kraken_registry.get("missing")),
            active=bool(_as_int(kraken_registry.get("spot_trade_ready_count")) > 0),
            fed=bool(kraken_registry),
            runtime=runtime,
            evidence_source="state/unified_runtime_status.json#kraken_asset_registry",
            stage="market_feed",
            extra_blockers=[] if _as_int(kraken_registry.get("spot_trade_ready_count")) > 0 else [str(kraken_registry.get("next_action") or "kraken_asset_registry_not_ready")],
        ),
        _row(
            name="KrakenMarginCostEnvelope",
            facet="kraken_margin_survival",
            wire="exchange_action_plan",
            path="aureon/exchanges/kraken_asset_registry.py",
            present=bool(kraken_registry and not kraken_registry.get("missing")),
            active=bool(_as_int(kraken_registry.get("margin_trade_ready_count")) > 0),
            fed=bool(kraken_registry),
            runtime=runtime,
            evidence_source="state/unified_runtime_status.json#kraken_asset_registry.survival_policy",
            stage="exchange_action_plan",
            extra_blockers=[] if _as_int(kraken_registry.get("margin_trade_ready_count")) > 0 else ["kraken_margin_pairs_not_ready_or_not_sampled"],
        ),
        _row(
            name="KrakenPendingOrderSurvival",
            facet="kraken_pending_order_survival",
            wire="exchange_action_plan",
            path="aureon/exchanges/kraken_asset_registry.py",
            present=bool(kraken_registry and not kraken_registry.get("missing")),
            active=bool(isinstance(kraken_registry.get("survival_policy"), dict)),
            fed=bool(kraken_registry),
            runtime=runtime,
            evidence_source="state/unified_runtime_status.json#kraken_asset_registry.survival_policy",
            stage="exchange_action_plan",
            extra_blockers=[] if isinstance(kraken_registry.get("survival_policy"), dict) else ["kraken_pending_order_survival_policy_missing"],
        ),
        _row(
            name="CapitalPortfolioMemory",
            facet="capital_portfolio_memory",
            wire="exchange_action_plan",
            path="aureon/exchanges/capital_cfd_trader.py",
            present=bool(capital_risk),
            active=bool(capital_risk.get("equity_gbp") is not None),
            fed=bool(capital_risk),
            runtime=runtime,
            evidence_source="state/unified_runtime_status.json#capital_risk_envelope",
            stage="exchange_action_plan",
        ),
        _row(
            name="CapitalLeverageEnvelope",
            facet="capital_leverage_survival",
            wire="exchange_action_plan",
            path="aureon/exchanges/capital_cfd_trader.py",
            present=bool(capital_risk),
            active=bool(capital_risk.get("margin_utilization_after_pct") is not None),
            fed=bool(capital_risk),
            runtime=runtime,
            evidence_source="state/unified_runtime_status.json#capital_risk_envelope",
            stage="exchange_action_plan",
            extra_blockers=list(capital_risk.get("blockers", [])) if isinstance(capital_risk.get("blockers"), list) else [],
        ),
        _row(
            name="CapitalStressBuffer",
            facet="capital_stress_buffer",
            wire="exchange_action_plan",
            path="aureon/exchanges/capital_cfd_trader.py",
            present=bool(capital_risk),
            active=bool(_as_float(capital_risk.get("stress_buffer_before_gbp"), 0.0) >= 0.0),
            fed=bool(capital_risk),
            runtime=runtime,
            evidence_source="state/unified_runtime_status.json#capital_risk_envelope.stress_buffer_before_gbp",
            stage="exchange_action_plan",
            extra_blockers=[] if _as_float(capital_risk.get("stress_buffer_before_gbp"), 0.0) >= 0.0 else ["capital_stress_buffer_negative"],
        ),
        _row(
            name="CapitalDynamicLaneControl",
            facet="dynamic_live_slot_control",
            wire="exchange_action_plan",
            path="aureon/exchanges/capital_cfd_trader.py",
            present=bool(capital_risk),
            active=bool(capital_risk.get("dynamic_lane_expansion_enabled")),
            fed=bool(capital_risk),
            runtime=runtime,
            evidence_source="state/unified_runtime_status.json#capital_risk_envelope.dynamic_lane_expansion_enabled",
            stage="exchange_action_plan",
        ),
        _row(
            name="CapitalUnifiedWaveformCheck",
            facet="unified_waveform_contradiction_check",
            wire="hnc_proof",
            path="aureon/exchanges/capital_cfd_trader.py",
            present=bool(capital_waveform),
            active=bool(capital_waveform.get("ok")),
            fed=bool(capital_waveform),
            runtime=runtime,
            evidence_source="state/unified_runtime_status.json#capital_unified_waveform_check",
            stage="hnc_proof",
            extra_blockers=list(capital_waveform.get("blockers", [])) if isinstance(capital_waveform.get("blockers"), list) else [],
        ),
        _row(
            name="CapitalConfidenceRatchet",
            facet="confidence_ratchet",
            wire="hnc_proof",
            path="aureon/exchanges/capital_cfd_trader.py",
            present=bool(capital_ratchet),
            active=bool(capital_ratchet.get("enabled", True) and capital_ratchet.get("ok", True)),
            fed=bool(capital_ratchet),
            runtime=runtime,
            evidence_source="state/unified_runtime_status.json#capital_confidence_ratchet",
            stage="hnc_proof",
            extra_blockers=[] if bool(capital_ratchet.get("ok", True)) else [str(capital_ratchet.get("reason") or "confidence_ratchet_blocked")],
        ),
        _row(
            name="CapitalWhoWhatWhereWhenHowEvidence",
            facet="who_what_where_when_how_act",
            wire="hnc_proof",
            path="aureon/exchanges/capital_cfd_trader.py",
            present=bool(capital_evidence),
            active=bool(capital_evidence.get("act", {}).get("evidence_complete", bool(capital_evidence)) if isinstance(capital_evidence.get("act"), dict) else bool(capital_evidence)),
            fed=bool(capital_evidence),
            runtime=runtime,
            evidence_source="state/unified_runtime_status.json#capital_trade_evidence",
            stage="hnc_proof",
        ),
        _row(
            name="ExchangeRouteClearance",
            facet="route_validation",
            wire="exchange_action_plan",
            path="state/unified_runtime_status.json",
            present=bool(plan),
            active=bool(venue_count),
            fed=bool(plan),
            runtime=runtime,
            evidence_source="state/unified_runtime_status.json#exchange_action_plan.venues",
            stage="exchange_action_plan",
            extra_blockers=[str(item) for item in runtime_clearances if str(item)] + ([] if ready_venues > 0 else ["no_ready_venues"]),
        ),
        _row(
            name="ProfitVelocityRanker",
            facet="fast_profit_eta",
            wire="profit_context",
            path="aureon/exchanges/unified_market_trader.py",
            present=bool(plan),
            active=profit_active,
            fed=profit_active,
            runtime=runtime,
            evidence_source="state/unified_runtime_status.json#exchange_action_plan.selection_process/top_candidates",
            stage="profit_velocity",
        ),
        _row(
            name="ShadowTradeSelfMeasurement",
            facet="self_validation",
            wire="direct_live_signal",
            path="state/unified_shadow_trade_report.json",
            present=bool(shadow),
            active=shadow_active,
            fed=shadow_active,
            runtime=runtime,
            evidence_source="state/unified_runtime_status.json#shadow_trading",
            stage="shadow_validation",
        ),
    ]
    if not (capital_risk or capital_evidence or capital_ratchet or capital_waveform):
        rows = [row for row in rows if not str(row.get("system") or "").startswith("Capital")]
    if not kraken_registry:
        rows = [row for row in rows if not str(row.get("system") or "").startswith("Kraken")]
    if meta_context.get("present"):
        meta_blockers = [meta_context["decision_blocker"]] if meta_context.get("decision_blocker") else []
        rows.extend(
            [
                _row(
                    name="DataOceanCognitiveContext",
                    facet="metacognitive_data_context",
                    wire="hnc_proof",
                    path=str(DATA_OCEAN_STATUS_PATH).replace("\\", "/"),
                    present=bool((root / DATA_OCEAN_STATUS_PATH).exists()),
                    active=bool(meta_context.get("usable_for_metacognition")),
                    fed=True,
                    runtime=runtime,
                    evidence_source="state/aureon_data_ocean_status.json#summary",
                    stage="metacognitive_context",
                    extra_blockers=meta_blockers,
                ),
                _row(
                    name="PlanetaryCoverageMap",
                    facet="planetary_financial_ocean",
                    wire="hnc_proof",
                    path=str(GLOBAL_COVERAGE_PATH).replace("\\", "/"),
                    present=bool((root / GLOBAL_COVERAGE_PATH).exists()),
                    active=bool(meta_context.get("planetary_context_ready")),
                    fed=True,
                    runtime=runtime,
                    evidence_source="docs/audits/aureon_global_financial_coverage_map.json#summary",
                    stage="metacognitive_context",
                    extra_blockers=meta_blockers,
                ),
                _row(
                    name="ExchangeWaveformMemory",
                    facet="exchange_waveform_memory",
                    wire="hnc_proof",
                    path=str(EXCHANGE_CHECKLIST_PATH).replace("\\", "/"),
                    present=bool((root / EXCHANGE_CHECKLIST_PATH).exists()),
                    active=bool(meta_context.get("exchange_waveform_ready")),
                    fed=True,
                    runtime=runtime,
                    evidence_source="docs/audits/aureon_exchange_monitoring_checklist.json#summary",
                    stage="metacognitive_context",
                    extra_blockers=meta_blockers,
                ),
            ]
        )
    return rows


def _dedupe_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_name: dict[str, dict[str, Any]] = {}
    for row in rows:
        name = str(row.get("system") or "")
        if not name:
            continue
        existing = by_name.get(name)
        if existing is None or (row.get("active_this_cycle") and not existing.get("active_this_cycle")):
            by_name[name] = row
    return list(by_name.values())


def _summary(rows: list[dict[str, Any]], runtime: dict[str, Any], root: Path = REPO_ROOT) -> dict[str, Any]:
    runtime_fresh = _runtime_fresh(runtime)
    stream_cache = runtime.get("live_stream_cache") if isinstance(runtime.get("live_stream_cache"), dict) else {}
    shared_order_flow = runtime.get("shared_order_flow") if isinstance(runtime.get("shared_order_flow"), dict) else {}
    fast_money = shared_order_flow.get("fast_money_intelligence") if isinstance(shared_order_flow.get("fast_money_intelligence"), dict) else {}
    hnc = runtime.get("hnc_cognitive_proof") if isinstance(runtime.get("hnc_cognitive_proof"), dict) else {}
    operating_cycle = runtime.get("hnc_operating_cycle") if isinstance(runtime.get("hnc_operating_cycle"), dict) else {}
    if not operating_cycle and isinstance(hnc.get("operating_cycle"), dict):
        operating_cycle = hnc.get("operating_cycle") or {}
    if not operating_cycle and isinstance(hnc.get("hnc_operating_cycle"), dict):
        operating_cycle = hnc.get("hnc_operating_cycle") or {}
    categories = {
        category: [row for row in rows if row.get("category") == category]
        for category in (LIVE_MARKET, HNC_AURIS, COUNTER_INTELLIGENCE, PROFIT_TIMING, RESEARCH_CONTEXT, META_COGNITIVE)
    }
    meta_context = _metacognitive_data_context(root, runtime)
    fresh_usable = [row for row in rows if row.get("usable_for_decision")]
    stale_or_blocked = [row for row in rows if not row.get("usable_for_decision")]
    decision_fed = [row for row in rows if row.get("fed_to_decision_logic")]
    blockers = [row for row in stale_or_blocked if row.get("blocker")]
    status = "fresh_decision_ready" if runtime_fresh and not blockers else "connected_guarded" if runtime.get("data_ready") else "runtime_data_not_ready"
    return {
        "status": status,
        "runtime_fresh": runtime_fresh,
        "runtime_stale": _runtime_stale(runtime),
        "stale_reason": _stale_reason(runtime) if _runtime_stale(runtime) else "",
        "trading_ready": bool(runtime.get("trading_ready")),
        "data_ready": bool(runtime.get("data_ready")),
        "live_stream_cache": {
            "fresh": bool(stream_cache.get("fresh")),
            "usable_for_decision": bool(stream_cache.get("usable_for_decision")),
            "symbol_count": _as_int(stream_cache.get("symbol_count")),
            "raw_ticker_count": _as_int(stream_cache.get("raw_ticker_count")),
            "max_age_sec": _as_float(stream_cache.get("max_age_sec")),
            "top_symbol": str(stream_cache.get("top_symbol") or ""),
            "reason": str(stream_cache.get("reason") or ""),
        },
        "fast_money_intelligence": {
            "candidate_count": _as_int(fast_money.get("candidate_count")),
            "high_volatility_count": _as_int(fast_money.get("high_volatility_count")),
            "orderbook_probe_count": _as_int(fast_money.get("orderbook_probe_count")),
            "orderbook_aligned_count": _as_int(fast_money.get("orderbook_aligned_count")),
            "top_symbol": str(fast_money.get("top_symbol") or ""),
            "top_side": str(fast_money.get("top_side") or ""),
            "top_fast_money_score": _as_float(fast_money.get("top_fast_money_score")),
            "top_momentum_tier": str(fast_money.get("top_momentum_tier") or ""),
        },
        "hnc_operating_cycle": {
            "present": bool(operating_cycle),
            "status": str(operating_cycle.get("status") or ""),
            "passed": bool(operating_cycle.get("passed")),
            "fed_to_decision_logic": bool(operating_cycle.get("fed_to_decision_logic")),
            "question_count": len(operating_cycle.get("questions", []) if isinstance(operating_cycle.get("questions"), list) else []),
            "cycle_order": operating_cycle.get("cycle_order", []) if isinstance(operating_cycle.get("cycle_order"), list) else [],
            "action_state": (
                operating_cycle.get("decision_output", {}).get("action_state")
                if isinstance(operating_cycle.get("decision_output"), dict)
                else ""
            ),
        },
        "system_count": len(rows),
        "present_count": sum(1 for row in rows if row.get("present")),
        "active_count": sum(1 for row in rows if row.get("active_this_cycle")),
        "fresh_usable_count": len(fresh_usable),
        "stale_or_blocked_count": len(stale_or_blocked),
        "decision_fed_count": len(decision_fed),
        "direct_live_systems_passing": sum(1 for row in categories[LIVE_MARKET] if row.get("usable_for_decision")),
        "hnc_auris_passing": sum(1 for row in categories[HNC_AURIS] if row.get("usable_for_decision")),
        "counter_intelligence_passing": sum(1 for row in categories[COUNTER_INTELLIGENCE] if row.get("usable_for_decision")),
        "profit_timing_passing": sum(1 for row in categories[PROFIT_TIMING] if row.get("usable_for_decision")),
        "research_context_passing": sum(1 for row in categories[RESEARCH_CONTEXT] if row.get("usable_for_decision")),
        "metacognitive_context_passing": sum(1 for row in categories[META_COGNITIVE] if row.get("usable_for_decision")),
        "metacognitive_data_context": meta_context,
        "category_counts": {
            category: {
                "total": len(items),
                "usable": sum(1 for row in items if row.get("usable_for_decision")),
                "fed": sum(1 for row in items if row.get("fed_to_decision_logic")),
            }
            for category, items in categories.items()
        },
        "top_blockers": [
            {
                "system": row.get("system"),
                "category": row.get("category"),
                "blocker": row.get("blocker"),
                "evidence_source": row.get("evidence_source"),
            }
            for row in blockers[:8]
        ],
    }


def _category_usable_ratio(summary: dict[str, Any], category: str) -> float:
    counts = summary.get("category_counts", {}).get(category, {}) if isinstance(summary.get("category_counts"), dict) else {}
    return _ratio(counts.get("usable", 0), counts.get("total", 0)) if isinstance(counts, dict) else 0.0


def _category_fed_ratio(summary: dict[str, Any], category: str) -> float:
    counts = summary.get("category_counts", {}).get(category, {}) if isinstance(summary.get("category_counts"), dict) else {}
    return _ratio(counts.get("fed", 0), counts.get("total", 0)) if isinstance(counts, dict) else 0.0


def _top_candidate_scores(runtime: dict[str, Any]) -> dict[str, Any]:
    plan = runtime.get("exchange_action_plan") if isinstance(runtime.get("exchange_action_plan"), dict) else {}
    venues = plan.get("venues") if isinstance(plan.get("venues"), dict) else {}
    best: dict[str, Any] = {}
    best_score = -1.0
    for venue_key, venue in venues.items():
        if not isinstance(venue, dict):
            continue
        for candidate in venue.get("top_candidates", []) if isinstance(venue.get("top_candidates"), list) else []:
            if not isinstance(candidate, dict):
                continue
            confidence = _clamp01(candidate.get("confidence", 0.0))
            velocity = _clamp01(candidate.get("profit_velocity_score", 0.0))
            fast_money = _clamp01(candidate.get("fast_money_score", 0.0))
            score = (confidence * 0.45) + (velocity * 0.35) + (fast_money * 0.20)
            if score > best_score:
                best_score = score
                best = {
                    "venue": venue_key,
                    "symbol": candidate.get("symbol") or candidate.get("route_symbol") or "",
                    "side": candidate.get("side") or "",
                    "confidence": round(confidence, 6),
                    "profit_velocity_score": round(velocity, 6),
                    "fast_money_score": round(fast_money, 6),
                    "combined_score": round(score, 6),
                }
    if not best:
        return {
            "venue": "",
            "symbol": "",
            "side": "",
            "confidence": 0.0,
            "profit_velocity_score": 0.0,
            "fast_money_score": 0.0,
            "combined_score": 0.0,
        }
    return best


def _hnc_score(runtime: dict[str, Any]) -> float:
    hnc = runtime.get("hnc_cognitive_proof") if isinstance(runtime.get("hnc_cognitive_proof"), dict) else {}
    master = hnc.get("master_formula") if isinstance(hnc.get("master_formula"), dict) else {}
    if master.get("score") is not None:
        return _clamp01(master.get("score"))
    return _ratio(hnc.get("passed_count", 0), hnc.get("step_count", 0))


def _shadow_score(runtime: dict[str, Any]) -> float:
    shadow = runtime.get("shadow_trading") if isinstance(runtime.get("shadow_trading"), dict) else {}
    measurement = shadow.get("self_measurement") if isinstance(shadow.get("self_measurement"), dict) else {}
    if measurement.get("agent_average_score") is not None:
        return _clamp01(measurement.get("agent_average_score"))
    if _as_int(shadow.get("validated_shadow_count", 0)) > 0:
        return 0.75
    if _as_int(shadow.get("active_shadow_count", 0)) > 0 or _as_int(shadow.get("shadow_opened_count", 0)) > 0:
        return 0.5
    return 0.0


def _runtime_clearance_items(runtime: dict[str, Any]) -> list[str]:
    plan = runtime.get("exchange_action_plan") if isinstance(runtime.get("exchange_action_plan"), dict) else {}
    values: list[str] = []
    for key in ("runtime_clearances", "global_clearances", "global_blockers"):
        raw = plan.get(key)
        if isinstance(raw, list):
            values.extend(str(item) for item in raw if str(item))
    return list(dict.fromkeys(values))


def _decision_trust(rows: list[dict[str, Any]], runtime: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
    plan = runtime.get("exchange_action_plan") if isinstance(runtime.get("exchange_action_plan"), dict) else {}
    system_count = max(1, len(rows))
    usable_ratio = _ratio(summary.get("fresh_usable_count", 0), system_count)
    active_ratio = _ratio(summary.get("active_count", 0), system_count)
    fed_ratio = _ratio(summary.get("decision_fed_count", 0), system_count)
    live_ratio = _category_fed_ratio(summary, LIVE_MARKET)
    hnc_ratio = _category_fed_ratio(summary, HNC_AURIS)
    counter_ratio = _category_fed_ratio(summary, COUNTER_INTELLIGENCE)
    profit_ratio = _category_fed_ratio(summary, PROFIT_TIMING)
    meta_ratio = _category_fed_ratio(summary, META_COGNITIVE)
    route_ratio = _ratio(plan.get("ready_venue_count", 0), plan.get("venue_count", 0))
    candidate = _top_candidate_scores(runtime)
    hnc_score = _hnc_score(runtime)
    shadow_score = _shadow_score(runtime)
    evidence_score = _clamp01(
        (active_ratio * 0.16)
        + (fed_ratio * 0.16)
        + (live_ratio * 0.12)
        + (hnc_ratio * 0.12)
        + (counter_ratio * 0.12)
        + (profit_ratio * 0.08)
        + (route_ratio * 0.08)
        + (_clamp01(candidate.get("combined_score", 0.0)) * 0.08)
        + (hnc_score * 0.05)
        + (shadow_score * 0.03)
    )
    meta_counts = summary.get("category_counts", {}).get(META_COGNITIVE, {}) if isinstance(summary.get("category_counts"), dict) else {}
    if isinstance(meta_counts, dict) and _as_int(meta_counts.get("total")) > 0:
        evidence_score = _clamp01((evidence_score * 0.9) + (meta_ratio * 0.1))
    runtime_fresh = bool(summary.get("runtime_fresh"))
    runtime_clearances = _runtime_clearance_items(runtime)
    live_action_score = evidence_score if runtime_fresh else round(evidence_score * 0.35, 6)
    trust_to_decide = bool(evidence_score >= TRUST_TO_DECIDE_THRESHOLD and fed_ratio >= TRUST_TO_DECIDE_THRESHOLD)
    trust_to_shadow = bool(evidence_score >= TRUST_TO_SHADOW_THRESHOLD or fed_ratio >= TRUST_TO_DECIDE_THRESHOLD)
    trust_to_act = bool(trust_to_decide and runtime_fresh and not runtime_clearances)
    if not bool(summary.get("data_ready")):
        posture = "wait_for_live_data"
        self_instruction = "Wait for live market data to return, then re-rank candidates before publishing intent."
        not_fear_reason = "The decision system is not hesitating; live data is not ready."
    elif trust_to_act:
        posture = "trust_to_publish_runtime_gated_trade_intent"
        self_instruction = "Trust the verified evidence, select the ranked route, and publish through the runtime-gated order-intent path."
        not_fear_reason = "Fresh market evidence, HNC/Auris proof, route readiness, and validation are aligned."
    elif not runtime_fresh:
        posture = "trust_decision_shadow_until_runtime_fresh" if trust_to_shadow else "recover_freshness_before_live_action"
        self_instruction = "Keep shadow-validating the ranked trade logic, restore a fresh tick, then re-check live action eligibility."
        not_fear_reason = f"Live action is held by runtime freshness truth ({summary.get('stale_reason') or 'runtime_stale'}), not by fear."
    elif runtime_clearances:
        posture = "trust_decision_wait_for_runtime_clearance" if trust_to_decide else "hold_until_runtime_clearance_and_signal_alignment"
        self_instruction = "Keep the decision path measured, then publish only after runtime clearances pass."
        not_fear_reason = "The decision path can keep ranking; execution is waiting on runtime clearance."
    elif trust_to_shadow:
        posture = "trust_to_shadow_until_confidence_rises"
        self_instruction = "Use shadow trades and HNC/Auris feedback to raise evidence alignment before live intent."
        not_fear_reason = "The system is learning from measured shadows rather than freezing."
    else:
        posture = "hold_until_signal_alignment"
        self_instruction = "Do not invent conviction; keep scanning until live, HNC/Auris, counter-intelligence, and profit timing agree."
        not_fear_reason = "Low alignment is a truth signal, not fear."
    return {
        "schema_version": 1,
        "evidence_self_trust_score": round(evidence_score, 6),
        "live_action_trust_score": round(live_action_score, 6),
        "trust_to_decide": trust_to_decide,
        "trust_to_shadow": trust_to_shadow,
        "trust_to_act": trust_to_act,
        "posture": posture,
        "synthetic_affect_state": "calibrated_courage" if trust_to_decide or trust_to_shadow else "quiet_observation",
        "not_fear_reason": not_fear_reason,
        "self_instruction": self_instruction,
        "thresholds": {
            "trust_to_decide": TRUST_TO_DECIDE_THRESHOLD,
            "trust_to_shadow": TRUST_TO_SHADOW_THRESHOLD,
        },
        "inputs": {
            "usable_ratio": round(usable_ratio, 6),
            "active_ratio": round(active_ratio, 6),
            "fed_ratio": round(fed_ratio, 6),
            "live_ratio": round(live_ratio, 6),
            "hnc_ratio": round(hnc_ratio, 6),
            "counter_intelligence_ratio": round(counter_ratio, 6),
            "profit_timing_ratio": round(profit_ratio, 6),
            "metacognitive_context_ratio": round(meta_ratio, 6),
            "route_ratio": round(route_ratio, 6),
            "hnc_score": round(hnc_score, 6),
            "shadow_score": round(shadow_score, 6),
            "top_candidate": candidate,
            "runtime_clearances": runtime_clearances,
        },
    }


def build_trading_intelligence_checklist(root: Optional[Path] = None) -> dict[str, Any]:
    root = (root or REPO_ROOT).resolve()
    runtime_rel = RUNTIME_STATUS_PATH
    runtime = read_runtime_status(root, rel_path=runtime_rel)
    if not isinstance(runtime, dict):
        runtime = {}
    rows = _dedupe_rows(_capability_rows(runtime) + _synthetic_rows(runtime, root))
    summary = _summary(rows, runtime, root)
    decision_trust = _decision_trust(rows, runtime, summary)
    summary.update(
        {
            "evidence_self_trust_score": decision_trust["evidence_self_trust_score"],
            "decision_self_trust_score": decision_trust["live_action_trust_score"],
            "decision_posture": decision_trust["posture"],
            "trust_to_decide": decision_trust["trust_to_decide"],
            "trust_to_shadow": decision_trust["trust_to_shadow"],
            "trust_to_act": decision_trust["trust_to_act"],
        }
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "status": summary["status"],
        "repo_root": str(root),
        "runtime_source": str(runtime_rel).replace("\\", "/"),
        "summary": summary,
        "contract": {
            "freshness_source": "state/unified_runtime_status.json runtime stale/tick truth checks",
            "fed_to_decision_logic": "system evidence is wired into exchange_action_plan, HNC/Auris proof, shadow validation, or profit velocity ranking",
            "usable_for_decision": "present, active, fed, and runtime fresh-live",
            "self_trust": "Aureon trusts aligned evidence to decide; live action still requires fresh runtime truth and clear execution state",
            "metacognitive_data_context": "data-ocean, global coverage, and exchange-monitoring reports feed HNC/Auris as wider context while runtime freshness remains authoritative",
            "no_execution_change": "checklist is proof/visibility only and does not loosen live exchange mutation rules",
        },
        "decision_trust": decision_trust,
        "rows": rows,
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    rows = report.get("rows") if isinstance(report.get("rows"), list) else []
    meta = summary.get("metacognitive_data_context") if isinstance(summary.get("metacognitive_data_context"), dict) else {}
    lines = [
        "# Aureon Trading Intelligence Checklist",
        "",
        f"- Generated: {report.get('generated_at', '')}",
        f"- Status: {report.get('status', '')}",
        f"- Runtime fresh: {summary.get('runtime_fresh')}",
        f"- Fresh usable: {summary.get('fresh_usable_count', 0)}/{summary.get('system_count', 0)}",
        f"- Decision fed: {summary.get('decision_fed_count', 0)}",
        f"- Evidence self-trust: {summary.get('evidence_self_trust_score', 0)}",
        f"- Live action trust: {summary.get('decision_self_trust_score', 0)}",
        f"- Decision posture: {summary.get('decision_posture', '')}",
        "- Metacognitive data context: mapped={mapped} coverage={coverage}% live_sources={live_sources} tickers={tickers} history_rows={history_rows} usable_for_thought={thought} usable_for_live_decision={live}".format(
            mapped=meta.get("mapping_complete", False),
            coverage=meta.get("coverage_percent", 0),
            live_sources=meta.get("active_live_source_count", 0),
            tickers=meta.get("live_ticker_count", 0),
            history_rows=meta.get("history_rows", 0),
            thought=meta.get("usable_for_metacognition", False),
            live=meta.get("usable_for_live_decision", False),
        ),
        "- Live stream cache: fresh={fresh} symbols={symbols} top={top}".format(
            fresh=(summary.get("live_stream_cache", {}) or {}).get("fresh", False)
            if isinstance(summary.get("live_stream_cache"), dict)
            else False,
            symbols=(summary.get("live_stream_cache", {}) or {}).get("symbol_count", 0)
            if isinstance(summary.get("live_stream_cache"), dict)
            else 0,
            top=(summary.get("live_stream_cache", {}) or {}).get("top_symbol", "")
            if isinstance(summary.get("live_stream_cache"), dict)
            else "",
        ),
        "- Fast money: candidates={candidates} high_vol={high_vol} orderbook={books} aligned={aligned} top={top} score={score}".format(
            candidates=(summary.get("fast_money_intelligence", {}) or {}).get("candidate_count", 0)
            if isinstance(summary.get("fast_money_intelligence"), dict)
            else 0,
            high_vol=(summary.get("fast_money_intelligence", {}) or {}).get("high_volatility_count", 0)
            if isinstance(summary.get("fast_money_intelligence"), dict)
            else 0,
            books=(summary.get("fast_money_intelligence", {}) or {}).get("orderbook_probe_count", 0)
            if isinstance(summary.get("fast_money_intelligence"), dict)
            else 0,
            aligned=(summary.get("fast_money_intelligence", {}) or {}).get("orderbook_aligned_count", 0)
            if isinstance(summary.get("fast_money_intelligence"), dict)
            else 0,
            top=(summary.get("fast_money_intelligence", {}) or {}).get("top_symbol", "")
            if isinstance(summary.get("fast_money_intelligence"), dict)
            else "",
            score=(summary.get("fast_money_intelligence", {}) or {}).get("top_fast_money_score", 0)
            if isinstance(summary.get("fast_money_intelligence"), dict)
            else 0,
        ),
        "- HNC operating cycle: status={status} passed={passed} fed={fed} questions={questions} action={action}".format(
            status=(summary.get("hnc_operating_cycle", {}) or {}).get("status", "")
            if isinstance(summary.get("hnc_operating_cycle"), dict)
            else "",
            passed=(summary.get("hnc_operating_cycle", {}) or {}).get("passed", False)
            if isinstance(summary.get("hnc_operating_cycle"), dict)
            else False,
            fed=(summary.get("hnc_operating_cycle", {}) or {}).get("fed_to_decision_logic", False)
            if isinstance(summary.get("hnc_operating_cycle"), dict)
            else False,
            questions=(summary.get("hnc_operating_cycle", {}) or {}).get("question_count", 0)
            if isinstance(summary.get("hnc_operating_cycle"), dict)
            else 0,
            action=(summary.get("hnc_operating_cycle", {}) or {}).get("action_state", "")
            if isinstance(summary.get("hnc_operating_cycle"), dict)
            else "",
        ),
        f"- Stale reason: {summary.get('stale_reason') or 'none'}",
        "",
        "| System | Category | Stage | Fresh | Usable | Fed | Blocker |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| {system} | {category} | {stage} | {fresh} | {usable} | {fed} | {blocker} |".format(
                system=str(row.get("system", "")),
                category=str(row.get("category", "")),
                stage=str(row.get("downstream_stage", "")),
                fresh=str(row.get("fresh", False)),
                usable=str(row.get("usable_for_decision", False)),
                fed=str(row.get("fed_to_decision_logic", False)),
                blocker=str(row.get("blocker", "")).replace("|", "/"),
            )
        )
    lines.append("")
    lines.append("This checklist is evidence-only. It does not place orders, change exchange credentials, or bypass runtime truth checks.")
    return "\n".join(lines) + "\n"


def write_trading_intelligence_checklist(
    report: dict[str, Any],
    output_json: Path = DEFAULT_OUTPUT_JSON,
    output_md: Path = DEFAULT_OUTPUT_MD,
    public_json: Path = DEFAULT_PUBLIC_JSON,
) -> tuple[Path, Path, Path]:
    _write_json(output_json, report)
    _write_json(public_json, report)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(render_markdown(report), encoding="utf-8")
    return output_json, output_md, public_json


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Aureon's trading intelligence freshness checklist.")
    parser.add_argument("--repo-root", default="", help="Repo root; defaults to current Aureon repo.")
    parser.add_argument("--json", default=str(DEFAULT_OUTPUT_JSON), help="Audit JSON path.")
    parser.add_argument("--md", default=str(DEFAULT_OUTPUT_MD), help="Audit Markdown path.")
    parser.add_argument("--public-json", default=str(DEFAULT_PUBLIC_JSON), help="Frontend public JSON path.")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    root = Path(args.repo_root).resolve() if args.repo_root else REPO_ROOT
    report = build_trading_intelligence_checklist(root)
    output_json, output_md, public_json = write_trading_intelligence_checklist(
        report,
        Path(args.json),
        Path(args.md),
        Path(args.public_json),
    )
    print(
        json.dumps(
            {
                "json": str(output_json),
                "md": str(output_md),
                "public_json": str(public_json),
                "summary": report["summary"],
            },
            indent=2,
            sort_keys=True,
            default=str,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
