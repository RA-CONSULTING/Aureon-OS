from __future__ import annotations

import argparse
from html import escape
import json
import math
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from aureon.autonomous.runtime_status_source import read_runtime_status


REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_VERSION = "aureon-gold-capital-intelligence-company-v1"

DEFAULT_STATE_PATH = Path("state/aureon_gold_capital_intelligence_company_last_run.json")
DEFAULT_AUDIT_JSON = Path("docs/audits/aureon_gold_capital_intelligence_company.json")
DEFAULT_AUDIT_MD = Path("docs/audits/aureon_gold_capital_intelligence_company.md")
DEFAULT_PUBLIC_JSON = Path("frontend/public/aureon_gold_capital_intelligence_company.json")
GOLD_ARTIFACT_DIR = Path("frontend/public/aureon_gold_intelligence")
GOLD_FORECAST_SVG = GOLD_ARTIFACT_DIR / "gold_priority_forecast.svg"
GOLD_FORECAST_HTML = GOLD_ARTIFACT_DIR / "gold_priority_forecast.html"

SOURCE_PATHS = {
    "capital_asset_registry": Path("state/aureon_capital_tradable_asset_registry.json"),
    "runtime_status": Path("state/unified_runtime_status.json"),
    "data_ocean_status": Path("state/aureon_data_ocean_status.json"),
    "global_financial_coverage": Path("frontend/public/aureon_global_financial_coverage_map.json"),
    "exchange_data_matrix": Path("frontend/public/aureon_exchange_data_capability_matrix.json"),
    "exchange_monitoring": Path("frontend/public/aureon_exchange_monitoring_checklist.json"),
    "trading_intelligence": Path("frontend/public/aureon_trading_intelligence_checklist.json"),
    "world_financial_ecosystem": Path("frontend/public/aureon_world_financial_ecosystem_intelligence.json"),
    "scanner_fusion_matrix": Path("frontend/public/aureon_scanner_fusion_matrix.json"),
    "shadow_trade_report": Path("frontend/public/aureon_unified_shadow_trade_report.json"),
    "harmonic_affect": Path("docs/audits/aureon_harmonic_affect_state.json"),
    "agent_company": Path("state/aureon_agent_company_last_run.json"),
    "hnc_cognitive_proof": Path("state/aureon_hnc_cognitive_proof.json"),
    "hnc_operating_cycle": Path("state/aureon_hnc_operating_cycle.json"),
    "hnc_quantum_packet": Path("state/aureon_hnc_quantum_packet_last_run.json"),
    "lambda_history": Path("state/lambda_history.json"),
}

GOLD_AGENT_SUPPORT_PATHS = {
    "coding_organism_bridge": Path("frontend/public/aureon_coding_organism_bridge.json"),
    "capability_forge": Path("frontend/public/aureon_capability_forge.json"),
    "autonomous_job_executor": Path("frontend/public/aureon_autonomous_job_executor.json"),
    "autonomous_self_run_loop": Path("frontend/public/aureon_autonomous_self_run_loop.json"),
    "dynamic_prompt_filter": Path("frontend/public/aureon_dynamic_prompt_filter.json"),
    "agent_company": Path("state/aureon_agent_company_last_run.json"),
}

PROBABILITY_DATA_PATHS = {
    "probability_predictions": Path("data/probability_predictions.jsonl"),
    "probability_matrix_data": Path("data/probability_matrix_data.jsonl"),
}

ACTION_SOURCE_FRESHNESS_SECONDS = {
    "capital_asset_registry": 900,
    "runtime_status": 180,
    "exchange_data_matrix": 900,
    "exchange_monitoring": 900,
    "trading_intelligence": 900,
    "world_financial_ecosystem": 900,
    "scanner_fusion_matrix": 900,
    "shadow_trade_report": 900,
    "harmonic_affect": 900,
}

GOLD_INTERVAL_VALIDATION_WINDOWS = [
    {"id": "tick", "label": "Tick", "seconds": 30},
    {"id": "1m", "label": "1 minute", "seconds": 60},
    {"id": "5m", "label": "5 minutes", "seconds": 300},
    {"id": "15m", "label": "15 minutes", "seconds": 900},
    {"id": "1h", "label": "1 hour", "seconds": 3600},
    {"id": "session", "label": "Session", "seconds": 23_400},
]

GOLD_EVOLVING_PROJECTION_HORIZONS = [
    {"id": "1s", "label": "1 second", "seconds": 1, "max_input_age_seconds": 2, "band": "seconds"},
    {"id": "5s", "label": "5 seconds", "seconds": 5, "max_input_age_seconds": 10, "band": "seconds"},
    {"id": "15s", "label": "15 seconds", "seconds": 15, "max_input_age_seconds": 30, "band": "seconds"},
    {"id": "30s", "label": "30 seconds", "seconds": 30, "max_input_age_seconds": 60, "band": "seconds"},
    {"id": "tick", "label": "Tick", "seconds": 30, "max_input_age_seconds": 60, "band": "seconds"},
    {"id": "1m", "label": "1 minute", "seconds": 60, "max_input_age_seconds": 120, "band": "minutes"},
    {"id": "5m", "label": "5 minutes", "seconds": 300, "max_input_age_seconds": 300, "band": "minutes"},
    {"id": "15m", "label": "15 minutes", "seconds": 900, "max_input_age_seconds": 900, "band": "minutes"},
    {"id": "1h", "label": "1 hour", "seconds": 3_600, "max_input_age_seconds": 1_800, "band": "hours"},
    {"id": "4h", "label": "4 hours", "seconds": 14_400, "max_input_age_seconds": 3_600, "band": "hours"},
    {"id": "session", "label": "Session", "seconds": 23_400, "max_input_age_seconds": 7_200, "band": "session"},
    {"id": "1d", "label": "1 day", "seconds": 86_400, "max_input_age_seconds": 21_600, "band": "days"},
    {"id": "1w", "label": "1 week", "seconds": 604_800, "max_input_age_seconds": 86_400, "band": "weeks_months"},
    {"id": "1mo", "label": "1 month", "seconds": 2_592_000, "max_input_age_seconds": 86_400, "band": "weeks_months"},
    {"id": "3mo", "label": "3 months", "seconds": 7_776_000, "max_input_age_seconds": 86_400, "band": "weeks_months"},
]

GOLD_TICKER_SOURCE_MESH_SPECS = [
    {
        "id": "capital_gold_xau",
        "label": "Capital GOLD/XAU",
        "symbols": ["GOLD", "XAUUSD", "GOLDUSD"],
        "venue": "Capital.com",
        "source_id": "capital_asset_registry",
        "driver_id": "capital_gold_cfd",
        "role": "target_action_lane",
        "max_age_seconds": 900,
    },
    {
        "id": "gold_futures_curve",
        "label": "GC futures context",
        "symbols": ["GC=F", "GCM2026", "GC"],
        "venue": "Futures/reference",
        "source_id": "global_financial_coverage",
        "driver_id": "gold_futures_curve",
        "role": "confirmation_context",
        "max_age_seconds": 3600,
    },
    {
        "id": "gold_etf_miners",
        "label": "Gold ETFs and miners",
        "symbols": ["GLD", "IAU", "GDX", "GDXJ"],
        "venue": "Alpaca/market data",
        "source_id": "global_financial_coverage",
        "driver_id": "gold_etfs_miners",
        "role": "confirmation_context",
        "max_age_seconds": 900,
    },
    {
        "id": "usd_rates_fx",
        "label": "USD, DXY, and rates",
        "symbols": ["DXY", "USD", "US10Y", "REAL_YIELD"],
        "venue": "Macro/FX",
        "source_id": "world_financial_ecosystem",
        "driver_id": "usd_dxy_fx",
        "role": "confirmation_context",
        "max_age_seconds": 1800,
    },
    {
        "id": "oil_energy",
        "label": "Oil and energy",
        "symbols": ["USOIL", "WTI", "BRENT", "XLE"],
        "venue": "Capital.com/macro",
        "source_id": "world_financial_ecosystem",
        "driver_id": "oil_energy_inflation",
        "role": "confirmation_context",
        "max_age_seconds": 1800,
    },
    {
        "id": "equity_volatility",
        "label": "Equities and volatility",
        "symbols": ["SPY", "QQQ", "VIX", "US500"],
        "venue": "Alpaca/Capital.com",
        "source_id": "global_financial_coverage",
        "driver_id": "equity_risk_vix",
        "role": "confirmation_context",
        "max_age_seconds": 900,
    },
    {
        "id": "crypto_liquidity",
        "label": "Crypto liquidity",
        "symbols": ["BTCUSDT", "ETHUSDT", "BTCUSD"],
        "venue": "Binance/Kraken",
        "source_id": "exchange_data_matrix",
        "driver_id": "crypto_liquidity_safe_haven",
        "role": "confirmation_context",
        "max_age_seconds": 300,
    },
    {
        "id": "macro_news_sentiment",
        "label": "Macro, geopolitics, news, and sentiment",
        "symbols": ["MACRO", "NEWS", "SENTIMENT"],
        "venue": "Research/data ocean",
        "source_id": "data_ocean_status",
        "driver_id": "geopolitical_news_sentiment",
        "role": "confirmation_context",
        "max_age_seconds": 3600,
    },
]

COGNITIVE_ROUTE_SURFACES = [
    {
        "id": "auris_nodes",
        "family": "auris_nodes",
        "path": "aureon/utils/aureon_queen_hive_mind.py",
        "role": "Nine-node sensory market texture and coherence evaluator.",
        "required_markers": ["AURIS_NODES", "read_auris_nodes", "get_auris_coherence"],
    },
    {
        "id": "auris_trader",
        "family": "auris_nodes",
        "path": "aureon/trading/aureon_auris_trader.py",
        "role": "Trading-facing Auris bridge for non-mutating coherence context.",
        "required_markers": ["Auris", "trader"],
    },
    {
        "id": "hnc_master_protocol",
        "family": "hnc",
        "path": "aureon/strategies/hnc_master_protocol.py",
        "role": "Harmonic Nexus Core master protocol and trading bridge.",
        "required_markers": ["HarmonicNexusCore", "HNCTradingBridge"],
    },
    {
        "id": "hnc_probability_matrix",
        "family": "probability",
        "path": "aureon/strategies/hnc_probability_matrix.py",
        "role": "HNC probability matrix validation and timestamped probability layer.",
        "required_markers": ["ProbabilityMatrix", "HNCProbabilityIntegration"],
    },
    {
        "id": "probability_intelligence_matrix",
        "family": "probability",
        "path": "aureon/strategies/probability_intelligence_matrix.py",
        "role": "Market probability intelligence matrix for confidence and direction tests.",
        "required_markers": ["probability", "matrix"],
    },
    {
        "id": "probability_validator",
        "family": "probability",
        "path": "aureon/strategies/probability_validator.py",
        "role": "Validation layer for probability claims before promotion.",
        "required_markers": ["probability", "validate"],
    },
    {
        "id": "lambda_engine",
        "family": "lambda",
        "path": "aureon/core/aureon_lambda_engine.py",
        "role": "Lambda engine producing organism timing/coherence history.",
        "required_markers": ["LambdaEngine", "lambda_t"],
    },
    {
        "id": "quantum_signals",
        "family": "quantum",
        "path": "aureon/strategies/quantum_signals.py",
        "role": "Quantum signal layer used as shadow/context evidence.",
        "required_markers": ["quantum", "signal"],
    },
    {
        "id": "quantum_rapid",
        "family": "quantum",
        "path": "aureon/trading/aureon_quantum_rapid.py",
        "role": "Trading-facing quantum rapid evaluation path.",
        "required_markers": ["quantum"],
    },
    {
        "id": "live_quantum_bridge",
        "family": "quantum",
        "path": "aureon/data_feeds/aureon_live_quantum_bridge.py",
        "role": "Live quantum bridge for read-only market evidence.",
        "required_markers": ["quantum", "bridge"],
    },
    {
        "id": "harmonic_nexus_bridge",
        "family": "hnc",
        "path": "aureon/harmonic/harmonic_nexus_bridge.py",
        "role": "Harmonic Nexus bridge that binds HNC and harmonic evidence.",
        "required_markers": ["Harmonic", "Nexus"],
    },
]

HFT_SPEED_PREDICTION_SURFACES = [
    {
        "id": "probability_validator",
        "path": "aureon/strategies/probability_validator.py",
        "role": "Validate prediction claims against outcome windows before confidence is trusted.",
        "required_markers": ["probability", "validate"],
    },
    {
        "id": "probability_matrix_backtest",
        "path": "aureon/strategies/probability_matrix_backtest.py",
        "role": "Replay historical probability predictions and detect fake passes.",
        "required_markers": ["probability", "backtest"],
    },
    {
        "id": "quantum_prediction_stream",
        "path": "aureon/strategies/quantum_prediction_stream_30_30_30.py",
        "role": "Fast quantum prediction stream for short-horizon shadow hypotheses.",
        "required_markers": ["quantum", "prediction"],
    },
    {
        "id": "unified_signal_engine",
        "path": "aureon/trading/unified_signal_engine.py",
        "role": "Fast signal fusion before shadow promotion.",
        "required_markers": ["signal"],
    },
    {
        "id": "live_stream_cache",
        "path": "aureon/data_feeds/live_stream_cache.py",
        "role": "Low-latency market cache used to keep prediction inputs fresh.",
        "required_markers": ["cache"],
    },
]

HISTORICAL_STRESS_SURFACES = [
    {
        "id": "global_history_db",
        "path": "aureon/core/aureon_global_history_db.py",
        "role": "Repo-wide market history store used to replay cross-asset bars and waveform memory.",
        "required_markers": ["history", "market"],
    },
    {
        "id": "historical_backtest",
        "path": "aureon/analytics/aureon_historical_backtest.py",
        "role": "Historical backtest surface for validating signal behavior on old bars.",
        "required_markers": ["backtest", "historical"],
    },
    {
        "id": "probability_matrix_backtest",
        "path": "aureon/strategies/probability_matrix_backtest.py",
        "role": "Probability replay and fake-pass detection for prediction rows.",
        "required_markers": ["probability", "backtest"],
    },
    {
        "id": "historical_unity_replay",
        "path": "tools/historical_unity_replay.py",
        "role": "Whole-system historical replay bridge for checking how repo signals agree.",
        "required_markers": ["historical", "replay"],
    },
    {
        "id": "cached_backtest_runner",
        "path": "scripts/runners/run_backtest_cached.py",
        "role": "Cached replay runner for repeatable local stress runs.",
        "required_markers": ["backtest", "cache"],
    },
    {
        "id": "market_history_ingest",
        "path": "scripts/python/ingest_market_history.py",
        "role": "Historical market data ingestion route for real bar evidence.",
        "required_markers": ["history", "ingest"],
    },
]

GOLD_AGENT_SUPPORT_SURFACES = [
    {
        "id": "coding_organism_bridge",
        "family": "coding",
        "path": "aureon/autonomous/aureon_coding_organism_bridge.py",
        "role": "Turns operator and agent coding prompts into scoped jobs, proof, tests, and public evidence.",
        "required_markers": ["coding", "organism"],
    },
    {
        "id": "autonomous_job_executor",
        "family": "coding",
        "path": "aureon/autonomous/aureon_autonomous_job_executor.py",
        "role": "Durable local job queue for agent-created coding, UI, media, and tool work.",
        "required_markers": ["job", "queue"],
    },
    {
        "id": "capability_forge",
        "family": "coding",
        "path": "aureon/autonomous/aureon_capability_forge.py",
        "role": "Local build and quality-gate forge for new agent-requested artifacts.",
        "required_markers": ["capability", "forge"],
    },
    {
        "id": "self_run_loop",
        "family": "monitoring",
        "path": "aureon/autonomous/aureon_autonomous_self_run_loop.py",
        "role": "Heartbeat loop that keeps queued work and health/self-fix cycles moving.",
        "required_markers": ["self", "run", "loop"],
    },
    {
        "id": "dynamic_prompt_filter",
        "family": "chat",
        "path": "aureon/autonomous/aureon_dynamic_prompt_filter.py",
        "role": "Shared prompt filter and response compiler for agent chat and Ollama shards.",
        "required_markers": ["prompt", "filter"],
    },
    {
        "id": "mind_thought_action_hub",
        "family": "chat",
        "path": "aureon/autonomous/aureon_mind_thought_action_hub.py",
        "role": "Local hub endpoint for operator/agent prompts and cockpit conversation.",
        "required_markers": ["thought", "action"],
    },
    {
        "id": "llm_adapter",
        "family": "chat",
        "path": "aureon/inhouse_ai/llm_adapter.py",
        "role": "In-house LLM adapter used by Aureon/Phi/Ollama conversation paths.",
        "required_markers": ["LLM", "adapter"],
    },
    {
        "id": "tool_registry",
        "family": "tools",
        "path": "aureon/inhouse_ai/tool_registry.py",
        "role": "Tool registry surface for agent-visible local capabilities.",
        "required_markers": ["tool", "registry"],
    },
    {
        "id": "phi_bridge",
        "family": "chat",
        "path": "aureon/harmonic/phi_bridge.py",
        "role": "Phi bridge for local organism chat and harmonic routing.",
        "required_markers": ["Phi", "bridge"],
    },
    {
        "id": "thought_bus",
        "family": "monitoring",
        "path": "aureon/core/aureon_thought_bus.py",
        "role": "ThoughtBus for agent handoffs, observations, blockers, and work packets.",
        "required_markers": ["ThoughtBus"],
    },
    {
        "id": "capital_market_monitor",
        "family": "gold_monitoring",
        "path": "aureon/exchanges/capital_market_monitor.py",
        "role": "Capital.com market monitor for GOLD and connected CFD evidence.",
        "required_markers": ["Capital", "monitor"],
    },
    {
        "id": "realtime_wave_monitor",
        "family": "gold_monitoring",
        "path": "aureon/monitors/realtime_wave_monitor.py",
        "role": "Realtime wave monitor for fast market texture and historical waveform context.",
        "required_markers": ["wave", "monitor"],
    },
]

CAPITAL_REFERENCE_PACKETS = [
    {
        "title": "Capital.com API market search",
        "source_url": "https://open-api.capital.com/",
        "guidance": "Use GET /markets with searchTerm to resolve market epics and GET /markets/{epic} for single-market details.",
        "mode": "reference_only",
    },
    {
        "title": "Capital.com WebSocket market data",
        "source_url": "https://open-api.capital.com/",
        "guidance": "Use marketData.subscribe for real-time quotes and OHLCMarketData.subscribe for bars; maximum epics per subscription is constrained.",
        "mode": "reference_only",
    },
    {
        "title": "Capital.com trading authority boundary",
        "source_url": "https://open-api.capital.com/",
        "guidance": "Creating positions uses trading endpoints and requires session tokens; Aureon keeps those routes runtime-gated and does not reveal credentials.",
        "mode": "authority_boundary",
    },
]

GOLD_COMPANY_ROLES = [
    {
        "role": "Gold Strategy Steward",
        "department": "executive",
        "authority": "observe_plan_only",
        "mission": "Keep the whole organism pointed at Capital GOLD evidence, not generic market noise.",
    },
    {
        "role": "Capital Venue Specialist",
        "department": "trading_data",
        "authority": "capital_runtime_gated",
        "mission": "Resolve Capital.com GOLD epics, snapshot health, spread, minimum deal size, and route blockers.",
    },
    {
        "role": "Gold Market Data Ocean Operator",
        "department": "trading_data",
        "authority": "read_only_market_data",
        "mission": "Blend Capital snapshots, exchange coverage, waveform memory, history, and live-cache readiness.",
    },
    {
        "role": "Macro And Dollar Analyst",
        "department": "intelligence",
        "authority": "read_only_research",
        "mission": "Mark macro, USD, rates, sentiment, and calendar gaps that affect gold.",
    },
    {
        "role": "HNC/Auris Harmonic Analyst",
        "department": "cognition",
        "authority": "coherence_gate",
        "mission": "Translate harmonic affect, coherence, safety blockers, and organism state into an energy score.",
    },
    {
        "role": "Risk Governor",
        "department": "trading_data",
        "authority": "live_trading_runtime_gated",
        "mission": "Prevent leverage, stale-data, margin, or open-position risk from becoming blind action.",
    },
    {
        "role": "Shadow Trade Validator",
        "department": "trading_data",
        "authority": "non_mutating_validation",
        "mission": "Allow only paper/shadow hypotheses until runtime freshness and execution gates pass.",
    },
    {
        "role": "Counter Intelligence Validator",
        "department": "intelligence",
        "authority": "stale_contradiction_check",
        "mission": "Reject stale, contradictory, or unsupported gold price/energy claims.",
    },
    {
        "role": "Operator Evidence Clerk",
        "department": "product_ui",
        "authority": "publish_evidence_only",
        "mission": "Make the gold thesis, blockers, proof, and next action visible in the console.",
    },
]

GOLD_INTELLIGENCE_SURFACES = [
    {
        "id": "capital_asset_registry",
        "path": "aureon/exchanges/capital_asset_registry.py",
        "department": "trading_data",
        "tool_type": "capital_market_discovery",
        "use_for_gold": "Resolve Capital.com GOLD, futures, ETFs, miners, minimum deal size, spread, and market state.",
        "activation_guidance": "Refresh the registry before any gold thesis; never emit credentials or place orders.",
        "terms": ["gold", "capital", "epic", "market"],
    },
    {
        "id": "capital_market_monitor",
        "path": "aureon/exchanges/capital_market_monitor.py",
        "department": "trading_data",
        "tool_type": "capital_runtime_monitor",
        "use_for_gold": "Watch Capital.com market snapshots and open-position context for GOLD without mutation.",
        "activation_guidance": "Use as read-only evidence unless the existing runtime execution gate is explicitly active.",
        "terms": ["capital", "market", "position"],
    },
    {
        "id": "capital_cfd_trader",
        "path": "aureon/exchanges/capital_cfd_trader.py",
        "department": "trading_data",
        "tool_type": "execution_boundary",
        "use_for_gold": "Know the CFD execution route and risk surface, but keep order mutation gated.",
        "activation_guidance": "Expose readiness and blockers only; live order authority remains outside this report.",
        "terms": ["capital", "cfd", "order", "position"],
    },
    {
        "id": "global_financial_feed",
        "path": "aureon/data_feeds/global_financial_feed.py",
        "department": "market_data",
        "tool_type": "cross_asset_feed",
        "use_for_gold": "Blend commodities, FX, indices, crypto, VIX, DXY, and macro context around gold.",
        "activation_guidance": "Use as a read-only data ocean and mark stale domains before scoring.",
        "terms": ["gold", "dxy", "vix", "commod"],
    },
    {
        "id": "market_harp",
        "path": "aureon/data_feeds/market_harp.py",
        "department": "market_data",
        "tool_type": "waveform_signal",
        "use_for_gold": "Turn market movement into waveform pressure and resonance evidence.",
        "activation_guidance": "Feed only timestamped waveform evidence into the gold thesis.",
        "terms": ["market", "wave", "signal"],
    },
    {
        "id": "world_data_ingester",
        "path": "aureon/integrations/world_data/world_data_ingester.py",
        "department": "research",
        "tool_type": "open_world_macro_ingest",
        "use_for_gold": "Fetch public macro, FRED/Yahoo/World Bank style context for rates, inflation, and USD pressure.",
        "activation_guidance": "Use public/read-only endpoints; record source, timestamp, and provider limitations.",
        "terms": ["fred", "yahoo", "gold", "macro"],
    },
    {
        "id": "macro_intelligence",
        "path": "aureon/intelligence/macro_intelligence.py",
        "department": "intelligence",
        "tool_type": "macro_context_engine",
        "use_for_gold": "Score macro pressure from risk appetite, volatility, dollar strength, and broad market state.",
        "activation_guidance": "Adapt crypto-oriented macro scores into gold-specific notes instead of raw reuse.",
        "terms": ["macro", "score", "vol"],
    },
    {
        "id": "aureon_seer_macro",
        "path": "aureon/intelligence/aureon_seer.py",
        "department": "intelligence",
        "tool_type": "seer_sentiment_macro",
        "use_for_gold": "Read Yahoo GC=F, DXY, indices, yields, oil, and sentiment-style context.",
        "activation_guidance": "Treat narrative output as advisory context; require numeric/timestamp proof.",
        "terms": ["GC=F", "DXY", "gold", "sentiment"],
    },
    {
        "id": "universal_forecast",
        "path": "aureon/intelligence/aureon_universal_forecast.py",
        "department": "forecasting",
        "tool_type": "multi_signal_forecast",
        "use_for_gold": "Route GOLD through universal forecast, Fibonacci, golden-ratio, and cross-market patterns.",
        "activation_guidance": "Use as a shadow forecast only until backtest and freshness proof pass.",
        "terms": ["GOLD", "forecast", "fibonacci", "golden"],
    },
    {
        "id": "sensory_framework",
        "path": "aureon/intelligence/aureon_sensory_framework.py",
        "department": "cognition",
        "tool_type": "sentiment_sensory_layer",
        "use_for_gold": "Translate volatility, sentiment, news velocity, and market pressure into sensory signals.",
        "activation_guidance": "Only use sensory language when backed by numeric market context.",
        "terms": ["sentiment", "news", "volatility"],
    },
    {
        "id": "advanced_intelligence",
        "path": "aureon/intelligence/aureon_advanced_intelligence.py",
        "department": "forecasting",
        "tool_type": "harmonic_pattern_engine",
        "use_for_gold": "Evaluate harmonic ratios, golden-ratio alignment, sentiment, and technical pattern pressure.",
        "activation_guidance": "Use as one weighted signal, never as sole authority.",
        "terms": ["golden", "sentiment", "harmonic"],
    },
    {
        "id": "cross_asset_correlator",
        "path": "aureon/analytics/cross_asset_correlator.py",
        "department": "analytics",
        "tool_type": "correlation_engine",
        "use_for_gold": "Compare gold against USD, yields, oil, equity risk, crypto, and related miners.",
        "activation_guidance": "Require enough bars before accepting a correlation claim.",
        "terms": ["correl", "asset", "gold"],
    },
    {
        "id": "unified_signal_engine",
        "path": "aureon/trading/unified_signal_engine.py",
        "department": "trading_data",
        "tool_type": "signal_fusion",
        "use_for_gold": "Fuse trend, momentum, volatility, and risk signals into a non-mutating gold posture.",
        "activation_guidance": "Keep output as observe/shadow until runtime fresh and execution gates pass.",
        "terms": ["signal", "trend", "momentum"],
    },
    {
        "id": "harmonic_affect_state",
        "path": "docs/audits/aureon_harmonic_affect_state.json",
        "department": "cognition",
        "tool_type": "hnc_auris_gate",
        "use_for_gold": "Gate confidence using HNC/Auris coherence, blockers, blind spots, and goal alignment.",
        "activation_guidance": "Safety blockers reduce confidence; they do not create trade authority.",
        "terms": ["coherence", "blocker", "auris"],
    },
]

GOLD_LOCAL_RESEARCH_PACKETS = [
    {
        "id": "phi_squared_gold_safe_haven_research",
        "path": "docs/research/THE_PHI_SQUARED_CHAIN_Sumer_to_Rome_to_Now.md",
        "topic": "gold_safe_haven_stress_claims",
        "guidance": "Use as local hypothesis/research context about gold safe-haven behavior under crisis; require fresh market proof before trading conclusions.",
        "terms": ["Gold Failure", "GC=F", "safe-haven"],
        "confidence": 0.58,
    },
    {
        "id": "white_paper_gold_crisis_claims",
        "path": "docs/research/AUREON_WHITE_PAPER_RESEARCH_HUB.md",
        "topic": "gold_crisis_backdrop",
        "guidance": "Use as a research packet for prior gold decline claims and crisis framing; keep it source-linked and not authoritative alone.",
        "terms": ["Gold Futures", "safe-haven", "GC=F"],
        "confidence": 0.55,
    },
    {
        "id": "hnc_gold_verification_audit",
        "path": "docs/research/audits/HNC_VERIFICATION_AUDIT_v3_2026-04-29.md",
        "topic": "verified_gold_peak_to_trough_claim",
        "guidance": "Use as audit evidence for historical GC=F measurement methods and verification discipline.",
        "terms": ["Gold declined", "GC=F", "measured"],
        "confidence": 0.72,
    },
    {
        "id": "hnc_gold_method_audit",
        "path": "docs/research/audits/HNC_VERIFICATION_AUDIT_v2_2026-04-07.md",
        "topic": "gold_data_method",
        "guidance": "Use as implementation guidance for Yahoo/yfinance GC=F measurement and audit trails.",
        "terms": ["GC=F", "yfinance", "Gold"],
        "confidence": 0.7,
    },
]

GOLD_DRIVER_FAMILIES = [
    {
        "id": "capital_gold_cfd",
        "label": "Capital GOLD CFD venue",
        "driver_role": "Primary trade venue and price snapshot.",
        "coverage_domains": ["cfd_fx_indices_equities"],
        "exchange_rows": ["capital"],
        "surface_ids": ["capital_asset_registry", "capital_market_monitor", "capital_cfd_trader"],
        "asset_buckets": ["capital_gold_core"],
        "next_action": "Refresh GOLD quote/OHLC, market hours, spread, minimum size, and open-position context.",
    },
    {
        "id": "gold_futures_curve",
        "label": "Gold futures curve",
        "driver_role": "Futures basis and forward pressure around GC-style instruments.",
        "coverage_domains": ["historical_waveform_memory", "macro_events_context"],
        "exchange_rows": ["capital"],
        "surface_ids": ["aureon_seer_macro", "world_data_ingester", "cross_asset_correlator"],
        "asset_buckets": ["gold_futures"],
        "next_action": "Compare Capital GOLD against GC futures and historical bars before accepting direction.",
    },
    {
        "id": "gold_etfs_miners",
        "label": "Gold ETFs and miners",
        "driver_role": "Equity-market confirmation through GLD/GDX/GDXJ/miner-style assets.",
        "coverage_domains": ["equity_and_etf_live_market", "cfd_fx_indices_equities"],
        "exchange_rows": ["alpaca", "capital"],
        "surface_ids": ["global_financial_feed", "cross_asset_correlator", "aureon_seer_macro"],
        "asset_buckets": ["gold_etf", "gold_miners"],
        "next_action": "Refresh GLD/GDX/miner snapshots and compare breadth against GOLD.",
    },
    {
        "id": "usd_dxy_fx",
        "label": "USD/DXY and FX pressure",
        "driver_role": "Dollar strength usually changes gold pressure and CFD FX context.",
        "coverage_domains": ["cfd_fx_indices_equities", "macro_events_context"],
        "exchange_rows": ["capital"],
        "surface_ids": ["world_data_ingester", "macro_intelligence", "aureon_seer_macro", "global_financial_feed"],
        "asset_buckets": [],
        "next_action": "Attach fresh DXY/USD and key FX context with timestamps.",
    },
    {
        "id": "rates_inflation_macro",
        "label": "Rates, inflation, and macro calendar",
        "driver_role": "Real yields, inflation expectations, and calendar events shape gold repricing.",
        "coverage_domains": ["macro_events_context"],
        "exchange_rows": [],
        "surface_ids": ["world_data_ingester", "macro_intelligence", "aureon_seer_macro"],
        "asset_buckets": [],
        "next_action": "Pull FRED/rates/inflation/calendar packets through read-only macro routes.",
    },
    {
        "id": "oil_energy_inflation",
        "label": "Oil and energy stress",
        "driver_role": "Energy shocks and inflation stress can move gold and risk assets together.",
        "coverage_domains": ["macro_events_context", "historical_waveform_memory"],
        "exchange_rows": ["capital"],
        "surface_ids": ["world_data_ingester", "aureon_seer_macro", "global_financial_feed"],
        "asset_buckets": [],
        "next_action": "Add oil/energy bars and stress context to the gold packet.",
    },
    {
        "id": "equity_risk_vix",
        "label": "Stocks, indices, ETFs, and VIX",
        "driver_role": "Risk-on/risk-off equity pressure changes gold demand and liquidity flows.",
        "coverage_domains": ["equity_and_etf_live_market", "cfd_fx_indices_equities", "historical_waveform_memory"],
        "exchange_rows": ["alpaca", "capital"],
        "surface_ids": ["global_financial_feed", "cross_asset_correlator", "aureon_seer_macro"],
        "asset_buckets": ["gold_etf"],
        "next_action": "Compare equity risk, VIX, GLD/miners, and Capital indices in one cross-asset view.",
    },
    {
        "id": "crypto_liquidity_safe_haven",
        "label": "Crypto liquidity and safe-haven rotation",
        "driver_role": "BTC/crypto liquidity can confirm or contradict old gold safe-haven narratives.",
        "coverage_domains": ["crypto_live_market", "sentiment_onchain_forecast_context", "historical_waveform_memory"],
        "exchange_rows": ["binance", "kraken"],
        "surface_ids": ["global_financial_feed", "cross_asset_correlator", "universal_forecast", "market_harp"],
        "asset_buckets": [],
        "next_action": "Use crypto breadth/BTC/liquidity as a contradiction or rotation signal, not a direct gold order signal.",
    },
    {
        "id": "geopolitical_news_sentiment",
        "label": "Geopolitics, news, and sentiment",
        "driver_role": "War, sanctions, supply stress, and narrative velocity can reprice gold quickly.",
        "coverage_domains": ["macro_events_context", "sentiment_onchain_forecast_context"],
        "exchange_rows": [],
        "surface_ids": ["world_data_ingester", "aureon_seer_macro", "sensory_framework"],
        "asset_buckets": [],
        "next_action": "Refresh owned/licensed geopolitics/news/sentiment feeds and timestamp every claim.",
    },
    {
        "id": "historical_waveform_memory",
        "label": "Historical waveform memory",
        "driver_role": "Multi-horizon pattern memory checks whether a move is normal, stretched, or reversing.",
        "coverage_domains": ["historical_waveform_memory"],
        "exchange_rows": ["binance", "kraken", "alpaca", "capital"],
        "surface_ids": ["market_harp", "advanced_intelligence", "universal_forecast"],
        "asset_buckets": ["capital_gold_core", "gold_futures", "gold_etf"],
        "next_action": "Backfill/refresh 1h-to-1y bars for GOLD, GC, GLD, miners, DXY, yields, oil, BTC, and VIX.",
    },
    {
        "id": "hnc_auris_counter_intelligence",
        "label": "HNC/Auris and counter-intelligence",
        "driver_role": "Coherence, blind spots, stale detection, and contradiction checks control confidence.",
        "coverage_domains": [],
        "exchange_rows": [],
        "surface_ids": ["harmonic_affect_state", "sensory_framework", "unified_signal_engine"],
        "asset_buckets": [],
        "next_action": "Keep stale-data and contradiction gates lowering confidence until proof is fresh.",
    },
]

GOLD_SWARM_AGENTS = [
    {
        "id": "gold_data_commander",
        "role": "Gold Data Commander",
        "department": "executive",
        "mode": "compile",
        "driver_ids": ["capital_gold_cfd", "historical_waveform_memory", "hnc_auris_counter_intelligence"],
        "mission": "Keep all gold evidence moving into one source-linked thesis instead of separate noisy dashboards.",
    },
    {
        "id": "capital_gold_collector",
        "role": "Capital GOLD Collector",
        "department": "trading_data",
        "mode": "gather",
        "driver_ids": ["capital_gold_cfd", "gold_futures_curve"],
        "mission": "Collect Capital GOLD, futures-style instruments, spread, market hours, and venue readiness.",
    },
    {
        "id": "etf_miner_cross_reader",
        "role": "ETF And Miner Cross-Reader",
        "department": "market_data",
        "mode": "gather_and_compare",
        "driver_ids": ["gold_etfs_miners", "equity_risk_vix"],
        "mission": "Use ETF, miner, stock, index, and VIX context as confirmation or contradiction for gold.",
    },
    {
        "id": "crypto_rotation_reader",
        "role": "Crypto Liquidity Rotation Reader",
        "department": "market_data",
        "mode": "sensemake",
        "driver_ids": ["crypto_liquidity_safe_haven"],
        "mission": "Compare BTC/crypto liquidity and safe-haven rotation against the gold thesis.",
    },
    {
        "id": "macro_rates_reader",
        "role": "Macro Rates Reader",
        "department": "intelligence",
        "mode": "gather_and_compare",
        "driver_ids": ["usd_dxy_fx", "rates_inflation_macro", "oil_energy_inflation"],
        "mission": "Gather USD, DXY, real-yield, inflation, oil, and broad macro pressure.",
    },
    {
        "id": "geopolitical_sentiment_reader",
        "role": "Geopolitical Sentiment Reader",
        "department": "research",
        "mode": "gather",
        "driver_ids": ["geopolitical_news_sentiment"],
        "mission": "Attach source-linked geopolitics, calendar, news velocity, and sentiment context.",
    },
    {
        "id": "waveform_forecaster",
        "role": "Waveform Forecast Reader",
        "department": "forecasting",
        "mode": "sensemake",
        "driver_ids": ["historical_waveform_memory", "gold_futures_curve", "equity_risk_vix"],
        "mission": "Use historical bars, waveform memory, and forecast engines to mark stretched or reversing states.",
    },
    {
        "id": "hnc_auris_counter_intel",
        "role": "HNC/Auris Counter-Intelligence Gate",
        "department": "cognition",
        "mode": "gate",
        "driver_ids": ["hnc_auris_counter_intelligence"],
        "mission": "Lower confidence when evidence is stale, contradictory, unsafe, or over-narrated.",
    },
    {
        "id": "risk_shadow_validator",
        "role": "Risk And Shadow Validator",
        "department": "trading_data",
        "mode": "validate",
        "driver_ids": ["capital_gold_cfd", "usd_dxy_fx", "historical_waveform_memory"],
        "mission": "Keep output in shadow/observe until runtime, price freshness, and risk gates pass.",
    },
]

GOLD_COMMAND_SYSTEMS = [
    {
        "id": "war_room",
        "path": "aureon/command_centers/war_room.py",
        "role": "operator strategy room",
        "use_for_gold": "Frame the GOLD theatre, evidence, blockers, and action posture in one operator command packet.",
        "authority": "read_only_strategy_context",
    },
    {
        "id": "war_strategy",
        "path": "aureon/command_centers/war_strategy.py",
        "role": "strategy pattern mapper",
        "use_for_gold": "Translate driver pressure into a stepwise strategy rather than a raw signal.",
        "authority": "read_only_strategy_context",
    },
    {
        "id": "aureon_strategic_war_planner",
        "path": "aureon/command_centers/aureon_strategic_war_planner.py",
        "role": "multi-step planner",
        "use_for_gold": "Build the action ladder from data gathering to shadow validation to gated execution.",
        "authority": "read_only_strategy_context",
    },
    {
        "id": "aureon_war_band",
        "path": "aureon/command_centers/aureon_war_band.py",
        "role": "multi-agent coordination",
        "use_for_gold": "Coordinate specialist agents across macro, venue, waveform, sentiment, and risk.",
        "authority": "read_only_strategy_context",
    },
    {
        "id": "orca_unified_kill_chain",
        "path": "aureon/bots/orca_unified_kill_chain.py",
        "role": "execution discipline pattern",
        "use_for_gold": "Use the staged validation pattern as a non-mutating checklist for GOLD; never mount order mutation here.",
        "authority": "non_mutating_strategy_pattern",
    },
]

GOLD_MARGIN_TRADER_UNITY_SURFACES = [
    {
        "id": "unified_margin_brain",
        "path": "aureon/trading/unified_margin_brain.py",
        "role": "Unifies margin context, risk posture, collateral pressure, and allowed route state.",
        "required_markers": ["margin", "brain"],
    },
    {
        "id": "dynamic_margin_sizer",
        "path": "aureon/trading/dynamic_margin_sizer.py",
        "role": "Computes non-mutating size proposals only after price, spread, collateral, and floor proof are present.",
        "required_markers": ["margin", "size"],
    },
    {
        "id": "margin_wave_rider",
        "path": "aureon/trading/margin_wave_rider.py",
        "role": "Reads waveform/timing context for margin opportunities without opening exposure.",
        "required_markers": ["margin", "wave"],
    },
    {
        "id": "margin_harmonic_scanner",
        "path": "aureon/scanners/aureon_margin_harmonic_scanner.py",
        "role": "Scans harmonic margin setups and feeds confidence into HNC/Auris gates.",
        "required_markers": ["margin", "harmonic"],
    },
    {
        "id": "capital_cfd_trader",
        "path": "aureon/exchanges/capital_cfd_trader.py",
        "role": "Capital CFD execution boundary for GOLD; used here as readiness and blocker evidence only.",
        "required_markers": ["capital", "cfd", "order"],
    },
    {
        "id": "capital_margin_runner",
        "path": "scripts/runners/run_capital_margin_only.ps1",
        "role": "Capital margin route runner; remains human/runtime gated for mutation.",
        "required_markers": ["capital", "margin"],
    },
    {
        "id": "margin_goal_recorder",
        "path": "aureon/monitors/margin_goal_recorder.py",
        "role": "Records entry-selection scans and outcome proof for margin goal learning.",
        "required_markers": ["margin", "goal"],
    },
    {
        "id": "margin_eta_predictor",
        "path": "aureon/monitors/margin_eta_predictor.py",
        "role": "Estimates time-to-profit and pressure windows for active or shadow margin routes.",
        "required_markers": ["margin", "ETA"],
    },
    {
        "id": "real_profit_monitor",
        "path": "aureon/portfolio/real_profit_monitor.py",
        "role": "Checks real net profit after fees so the 3p floor is not phantom profit.",
        "required_markers": ["profit", "fees"],
    },
    {
        "id": "position_reconciler",
        "path": "aureon/portfolio/reconcile_positions.py",
        "role": "Reconciles open positions before any margin route claims new exposure capacity.",
        "required_markers": ["position", "reconcile"],
    },
]


def _default_root() -> Path:
    return Path.cwd().resolve() if (Path.cwd() / "aureon").exists() else REPO_ROOT


def _rooted(root: Path, rel: Path) -> Path:
    return rel if rel.is_absolute() else root / rel


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}
    return {}


def _read_jsonl_tail(path: Path, *, limit: int = 250) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    try:
        if not path.exists():
            return rows
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        for line in lines[-limit:]:
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except Exception:
                continue
            if isinstance(payload, dict):
                rows.append(payload)
    except Exception:
        return rows
    return rows


def _write_json(path: Path, payload: Dict[str, Any]) -> Dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")
    return {"path": str(path), "bytes": path.stat().st_size}


def _write_text(path: Path, content: str) -> Dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return {"path": str(path), "bytes": path.stat().st_size}


def _parse_time(value: Any) -> Optional[datetime]:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        raw = float(value)
        if raw > 10_000_000_000:
            raw = raw / 1000.0
        return datetime.fromtimestamp(raw, tz=timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def _age_seconds(value: Any, now: datetime) -> Optional[float]:
    parsed = _parse_time(value)
    if not parsed:
        return None
    return max(0.0, (now - parsed).total_seconds())


def _num(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
        if math.isfinite(number):
            return number
    except Exception:
        pass
    return default


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _summary(payload: Dict[str, Any]) -> Dict[str, Any]:
    value = payload.get("summary")
    return value if isinstance(value, dict) else {}


def _list_rows(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = payload.get("rows")
    if isinstance(rows, list):
        return [row for row in rows if isinstance(row, dict)]
    return []


def _find_row(payload: Dict[str, Any], *needles: str) -> Dict[str, Any]:
    terms = [needle.lower() for needle in needles if needle]
    for row in _list_rows(payload):
        blob = json.dumps(row, default=str).lower()
        if all(term in blob for term in terms):
            return row
    return {}


def _read_text_sample(path: Path, limit: int = 800_000) -> str:
    try:
        if path.exists() and path.is_file():
            return path.read_text(encoding="utf-8", errors="ignore")[:limit]
    except Exception:
        return ""
    return ""


def _matched_terms(text: str, terms: Iterable[str]) -> List[str]:
    lower = text.lower()
    return [term for term in terms if term.lower() in lower]


def _build_cognitive_surface_map(root: Path) -> List[Dict[str, Any]]:
    surfaces: List[Dict[str, Any]] = []
    for spec in COGNITIVE_ROUTE_SURFACES:
        path = _rooted(root, Path(spec["path"]))
        sample = _read_text_sample(path, limit=120_000) if path.exists() else ""
        markers = _matched_terms(sample, spec.get("required_markers", []))
        surfaces.append(
            {
                "id": spec["id"],
                "family": spec["family"],
                "path": str(path),
                "present": path.exists(),
                "status": "present_markers_verified" if path.exists() and markers else "present_needs_marker_review" if path.exists() else "missing",
                "role": spec["role"],
                "markers_found": markers,
                "required_markers": spec.get("required_markers", []),
                "route_use": "required_cognitive_route_for_gold_shadow_logic",
            }
        )
    return surfaces


def _build_hft_speed_surface_map(root: Path) -> List[Dict[str, Any]]:
    surfaces: List[Dict[str, Any]] = []
    for spec in HFT_SPEED_PREDICTION_SURFACES:
        path = _rooted(root, Path(spec["path"]))
        sample = _read_text_sample(path, limit=100_000) if path.exists() else ""
        markers = _matched_terms(sample, spec.get("required_markers", []))
        surfaces.append(
            {
                "id": spec["id"],
                "path": str(path),
                "present": path.exists(),
                "status": "present_markers_verified" if path.exists() and markers else "present_needs_marker_review" if path.exists() else "missing",
                "role": spec["role"],
                "markers_found": markers,
                "required_markers": spec.get("required_markers", []),
                "route_use": "required_hft_speed_and_prediction_validation_route",
            }
        )
    return surfaces


def _latest_epoch_age_seconds(value: Any, now: datetime) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number <= 0:
        return None
    return max(0.0, now.timestamp() - number)


def _build_probability_data_evidence(root: Path, now: datetime) -> Dict[str, Any]:
    data_sets: List[Dict[str, Any]] = []
    gold_rows: List[Dict[str, Any]] = []
    gold_terms = ("gold", "xau", "gc=f", "goldusd", "xauusd")
    for data_id, rel in PROBABILITY_DATA_PATHS.items():
        path = _rooted(root, rel)
        rows = _read_jsonl_tail(path)
        parsed_rows: List[Dict[str, Any]] = []
        latest_time: Optional[datetime] = None
        for row in rows:
            symbol = str(row.get("symbol") or row.get("prediction_id") or "")
            timestamp = row.get("timestamp") or row.get("window_start")
            parsed_time = _parse_time(timestamp)
            if parsed_time and (latest_time is None or parsed_time > latest_time):
                latest_time = parsed_time
            is_gold = any(term in symbol.lower() for term in gold_terms)
            parsed = {
                "symbol": symbol,
                "timestamp": timestamp,
                "probability": row.get("predicted_probability") or row.get("probability_score"),
                "confidence": row.get("predicted_confidence") or row.get("confidence"),
                "direction": row.get("predicted_direction") or row.get("predicted_action"),
                "interval": row.get("interval") or row.get("horizon") or row.get("window") or row.get("validation_interval"),
                "actual_direction": row.get("actual_direction"),
                "forecast_level": row.get("forecast_level") or row.get("target_price") or row.get("price"),
                "source_tickers": row.get("source_tickers") or row.get("symbols"),
                "shadow_p_l_effect": row.get("shadow_p_l_effect"),
                "validated": bool(row.get("validated")),
                "direction_correct": bool(row.get("direction_correct")),
                "outcome_score": row.get("outcome_score"),
                "source": data_id,
                "gold_related": is_gold,
            }
            parsed_rows.append(parsed)
            if is_gold:
                gold_rows.append(parsed)
        age = _age_seconds(latest_time.isoformat() if latest_time else None, now)
        data_sets.append(
            {
                "id": data_id,
                "path": str(path),
                "present": path.exists(),
                "tail_row_count": len(parsed_rows),
                "gold_row_count": sum(1 for row in parsed_rows if row.get("gold_related")),
                "latest_timestamp": latest_time.isoformat() if latest_time else None,
                "latest_age_seconds": round(age, 3) if age is not None else None,
                "fresh": bool(age is not None and age <= 3600),
            }
        )
    return {
        "status": "gold_probability_data_ready" if gold_rows else "gold_probability_data_missing",
        "datasets": data_sets,
        "gold_probability_rows": gold_rows[-12:],
        "gold_row_count": len(gold_rows),
        "fresh_gold_row_count": sum(
            1
            for row in gold_rows
            if _age_seconds(row.get("timestamp"), now) is not None and _num(_age_seconds(row.get("timestamp"), now)) <= 3600
        ),
    }


def _build_hnc_auris_quantum_probability_route(
    *,
    root: Path,
    sources: Dict[str, Dict[str, Any]],
    harmonic_summary: Dict[str, Any],
    generated_at: str,
    now: datetime,
) -> Dict[str, Any]:
    hnc_proof = sources.get("hnc_cognitive_proof") or {}
    quantum_packet = sources.get("hnc_quantum_packet") or {}
    operating_cycle = sources.get("hnc_operating_cycle") or {}
    lambda_history = sources.get("lambda_history") or {}
    auris_nodes = hnc_proof.get("auris_nodes") if isinstance(hnc_proof.get("auris_nodes"), dict) else {}
    master_formula = hnc_proof.get("master_formula") if isinstance(hnc_proof.get("master_formula"), dict) else {}
    real_data = hnc_proof.get("real_data") if isinstance(hnc_proof.get("real_data"), dict) else {}
    lambda_values = lambda_history.get("history") if isinstance(lambda_history.get("history"), list) else []
    psi_values = lambda_history.get("psi_history") if isinstance(lambda_history.get("psi_history"), list) else []
    lambda_age = _latest_epoch_age_seconds(lambda_history.get("saved_at"), now)
    probability_evidence = _build_probability_data_evidence(root, now)
    surfaces = _build_cognitive_surface_map(root)
    surface_counts: Dict[str, int] = {}
    present_counts: Dict[str, int] = {}
    for surface in surfaces:
        family = str(surface.get("family") or "unknown")
        surface_counts[family] = surface_counts.get(family, 0) + 1
        if surface.get("present"):
            present_counts[family] = present_counts.get(family, 0) + 1

    blockers: List[Dict[str, Any]] = []
    if not hnc_proof:
        blockers.append({"id": "hnc_cognitive_proof_missing", "reason": "HNC cognitive proof is required before GOLD logic can promote."})
    elif not bool(hnc_proof.get("passed")):
        blockers.append({"id": "hnc_cognitive_proof_not_passing", "reason": "HNC cognitive proof exists but is not passing."})
    if not auris_nodes:
        blockers.append({"id": "auris_nodes_missing", "reason": "Auris node proof is missing from HNC cognitive proof."})
    elif not bool(auris_nodes.get("passed")):
        blockers.append({"id": "auris_nodes_not_passing", "reason": "Auris node coherence did not pass."})
    if _num(auris_nodes.get("node_count")) < 9:
        blockers.append({"id": "auris_node_count_low", "reason": f"{auris_nodes.get('node_count') or 0} Auris nodes visible; 9 required."})
    if not lambda_values:
        blockers.append({"id": "lambda_history_missing", "reason": "Lambda history is missing."})
    elif lambda_age is None or lambda_age > 86_400:
        blockers.append({"id": "lambda_history_stale", "reason": f"Lambda history age is {round(lambda_age or -1, 1)} seconds."})
    if not quantum_packet:
        blockers.append({"id": "hnc_quantum_packet_missing", "reason": "HNC quantum packet metadata is missing."})
    if probability_evidence["gold_row_count"] <= 0:
        blockers.append({"id": "gold_probability_rows_missing", "reason": "Probability systems have no GOLD/XAU rows in the local evidence tail."})
    missing_surface_families = [
        family
        for family, count in surface_counts.items()
        if present_counts.get(family, 0) < count
    ]
    for family in missing_surface_families:
        blockers.append({"id": f"{family}_route_surface_missing", "reason": f"{family} route surfaces are not fully present."})

    hnc_age = _age_seconds(hnc_proof.get("generated_at"), now)
    quantum_age = _age_seconds(quantum_packet.get("generated_at"), now)
    route_passed = not blockers
    return {
        "status": "hnc_auris_quantum_probability_route_passing" if route_passed else "hnc_auris_quantum_probability_route_blocking",
        "generated_at": generated_at,
        "route_policy": "Every GOLD shadow decision must pass through Auris nodes, lambda history, HNC proof, quantum packet context, and probability evidence before promotion.",
        "route_passed": route_passed,
        "mutation_allowed": False,
        "hnc": {
            "present": bool(hnc_proof),
            "passed": bool(hnc_proof.get("passed")),
            "status": hnc_proof.get("status"),
            "generated_at": hnc_proof.get("generated_at"),
            "age_seconds": round(hnc_age, 3) if hnc_age is not None else None,
            "master_formula_score": master_formula.get("score"),
            "master_formula_passed": bool(master_formula.get("passed")),
            "real_data_passed": bool(real_data.get("passed")),
            "real_data_source_count": real_data.get("source_count"),
        },
        "auris_nodes": {
            "present": bool(auris_nodes),
            "passed": bool(auris_nodes.get("passed")),
            "node_count": int(_num(auris_nodes.get("node_count"))),
            "coherence": round(_num(auris_nodes.get("coherence")), 6),
            "status": auris_nodes.get("status") or harmonic_summary.get("affect_phase"),
            "node_names": sorted((auris_nodes.get("nodes") or {}).keys()) if isinstance(auris_nodes.get("nodes"), dict) else [],
        },
        "lambda_system": {
            "present": bool(lambda_values),
            "sample_count": len(lambda_values),
            "latest_lambda": round(_num(lambda_values[-1]), 6) if lambda_values else None,
            "latest_psi": round(_num(psi_values[-1]), 6) if psi_values else None,
            "step_count": lambda_history.get("step_count"),
            "saved_at": lambda_history.get("saved_at"),
            "age_seconds": round(lambda_age, 3) if lambda_age is not None else None,
            "fresh": bool(lambda_age is not None and lambda_age <= 86_400),
        },
        "quantum_systems": {
            "packet_present": bool(quantum_packet),
            "packet_generated_at": quantum_packet.get("generated_at"),
            "packet_age_seconds": round(quantum_age, 3) if quantum_age is not None else None,
            "packet_policy": quantum_packet.get("secret_policy") or "metadata_only",
            "operating_cycle_present": bool(operating_cycle),
            "surface_count": surface_counts.get("quantum", 0),
            "present_surface_count": present_counts.get("quantum", 0),
        },
        "probability_systems": {
            **probability_evidence,
            "surface_count": surface_counts.get("probability", 0),
            "present_surface_count": present_counts.get("probability", 0),
        },
        "route_surfaces": surfaces,
        "blockers": blockers[:16],
    }


def _build_hft_speed_prediction_gate(
    *,
    root: Path,
    source_evidence: List[Dict[str, Any]],
    cognitive_route: Dict[str, Any],
    verified_data_gate: Dict[str, Any],
    historical_signal_lab: Dict[str, Any],
    generated_at: str,
) -> Dict[str, Any]:
    latency_budget_ms = 250
    source_freshness_budget_ms = 1_000
    hft_sources = {
        "capital_asset_registry",
        "runtime_status",
        "scanner_fusion_matrix",
        "shadow_trade_report",
        "trading_intelligence",
        "hnc_cognitive_proof",
    }
    latency_checks: List[Dict[str, Any]] = []
    for item in source_evidence:
        source_id = str(item.get("id") or "")
        if source_id not in hft_sources:
            continue
        age_seconds = item.get("age_seconds")
        age_ms = _num(age_seconds) * 1000.0 if age_seconds is not None else None
        latency_checks.append(
            {
                "id": source_id,
                "present": bool(item.get("present")),
                "generated_at": item.get("generated_at"),
                "age_ms": round(age_ms, 3) if age_ms is not None else None,
                "max_age_ms": source_freshness_budget_ms,
                "fresh_for_hft": bool(age_ms is not None and age_ms <= source_freshness_budget_ms),
                "status": item.get("status"),
            }
        )

    probability = cognitive_route.get("probability_systems") if isinstance(cognitive_route.get("probability_systems"), dict) else {}
    gold_rows = probability.get("gold_probability_rows") if isinstance(probability.get("gold_probability_rows"), list) else []
    fresh_rows = [
        row
        for row in gold_rows
        if _age_seconds(row.get("timestamp"), _parse_time(generated_at) or datetime.now(timezone.utc)) is not None
        and _num(_age_seconds(row.get("timestamp"), _parse_time(generated_at) or datetime.now(timezone.utc))) <= 60
    ]
    validated_rows = [row for row in gold_rows if row.get("validated")]
    validated_correct_rows = [row for row in validated_rows if row.get("direction_correct") or _num(row.get("outcome_score")) > 0]
    surfaces = _build_hft_speed_surface_map(root)
    present_surface_count = sum(1 for surface in surfaces if surface.get("present"))
    blockers: List[Dict[str, Any]] = []
    if present_surface_count < len(surfaces):
        blockers.append({"id": "hft_speed_surfaces_missing", "reason": f"{present_surface_count}/{len(surfaces)} speed/prediction surfaces are present."})
    if not latency_checks:
        blockers.append({"id": "hft_latency_sources_missing", "reason": "No low-latency source freshness checks are available."})
    for check in latency_checks:
        if not check.get("fresh_for_hft"):
            blockers.append({"id": f"{check.get('id')}_not_hft_fresh", "reason": f"{check.get('id')} age {check.get('age_ms')}ms exceeds {source_freshness_budget_ms}ms or timestamp is missing."})
    if not gold_rows:
        blockers.append({"id": "gold_prediction_rows_missing", "reason": "No GOLD/XAU prediction rows are available for the HFT gate."})
    if not fresh_rows:
        blockers.append({"id": "fresh_gold_prediction_missing", "reason": "No GOLD/XAU prediction row is fresh enough for high-frequency use."})
    if not validated_rows:
        blockers.append({"id": "validated_gold_prediction_missing", "reason": "No GOLD/XAU prediction has outcome validation."})
    if not validated_correct_rows:
        blockers.append({"id": "validated_correct_gold_prediction_missing", "reason": "No GOLD/XAU prediction has a positive validated outcome."})
    if not cognitive_route.get("route_passed"):
        blockers.append({"id": "cognitive_route_not_passing", "reason": "HNC/Auris/lambda/quantum/probability route must pass before HFT promotion."})
    if not verified_data_gate.get("action_allowed_by_data"):
        blockers.append({"id": "verified_real_data_gate_blocking", "reason": "Fresh verified real-data gate is not passing."})
    if historical_signal_lab.get("orderbook_signal_state") != "ready_shadow_replay":
        blockers.append({"id": "direct_orderbook_not_hft_ready", "reason": "Direct GOLD order-book pressure is not ready for timing."})

    speed_score = _clamp(
        (present_surface_count / max(1, len(surfaces))) * 0.2
        + (sum(1 for check in latency_checks if check.get("fresh_for_hft")) / max(1, len(latency_checks))) * 0.25
        + (min(len(fresh_rows), 3) / 3.0) * 0.15
        + (min(len(validated_correct_rows), 3) / 3.0) * 0.25
        + (0.15 if cognitive_route.get("route_passed") else 0.0)
    )
    return {
        "status": "hft_speed_prediction_gate_passing" if not blockers else "hft_speed_prediction_gate_blocking",
        "generated_at": generated_at,
        "gate_passed": not blockers,
        "mode": "gold_hft_shadow_speed_validated_predictions_only",
        "latency_budget_ms": latency_budget_ms,
        "source_freshness_budget_ms": source_freshness_budget_ms,
        "speed_score": round(speed_score, 4),
        "validated_prediction_policy": "Speed is only accepted when a GOLD/XAU prediction is fresh, outcome-validated, and backed by real-data/HNC/Auris/probability gates.",
        "latency_checks": latency_checks,
        "prediction_validation": {
            "gold_prediction_count": len(gold_rows),
            "fresh_gold_prediction_count": len(fresh_rows),
            "validated_gold_prediction_count": len(validated_rows),
            "validated_correct_gold_prediction_count": len(validated_correct_rows),
            "rows": gold_rows[:8],
        },
        "surface_count": len(surfaces),
        "present_surface_count": present_surface_count,
        "route_surfaces": surfaces,
        "promotion_use": "blocks_gold_shadow_promotion_until_fast_and_validated",
        "live_order_allowed": False,
        "order_mutation_allowed": False,
        "blockers": blockers[:18],
    }


def _build_historical_stress_surface_map(root: Path) -> List[Dict[str, Any]]:
    surfaces: List[Dict[str, Any]] = []
    for spec in HISTORICAL_STRESS_SURFACES:
        path = _rooted(root, Path(spec["path"]))
        sample = _read_text_sample(path, limit=120_000) if path.exists() else ""
        markers = _matched_terms(sample, spec.get("required_markers", []))
        surfaces.append(
            {
                "id": spec["id"],
                "path": str(path),
                "present": path.exists(),
                "status": "present_markers_verified" if path.exists() and markers else "present_needs_marker_review" if path.exists() else "missing",
                "role": spec["role"],
                "markers_found": markers,
                "required_markers": spec.get("required_markers", []),
                "route_use": "required_gold_historical_stress_replay_route",
            }
        )
    return surfaces


def _normalize_direction(value: Any) -> str:
    text = str(value or "").strip().upper()
    if text in {"BUY", "LONG", "BULL", "BULLISH", "UP", "CALL"}:
        return "UP"
    if text in {"SELL", "SHORT", "BEAR", "BEARISH", "DOWN", "PUT"}:
        return "DOWN"
    if text in {"HOLD", "NEUTRAL", "FLAT", "OBSERVE", "WAIT"}:
        return "FLAT"
    return text


def _collect_gold_probability_history(root: Path, now: datetime) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    for data_id, rel in PROBABILITY_DATA_PATHS.items():
        path = _rooted(root, rel)
        for raw in _read_jsonl_tail(path, limit=5_000):
            symbol = str(raw.get("symbol") or raw.get("prediction_id") or raw.get("instrument") or raw.get("market") or "")
            if not _gold_related_blob(symbol, raw.get("asset"), raw.get("route_symbol")):
                continue
            predicted_direction = _normalize_direction(
                raw.get("predicted_direction")
                or raw.get("predicted_action")
                or raw.get("direction")
                or raw.get("side")
                or raw.get("signal")
            )
            actual_direction = _normalize_direction(
                raw.get("actual_direction")
                or raw.get("outcome_direction")
                or raw.get("realized_direction")
                or raw.get("result_direction")
            )
            outcome_score_present = raw.get("outcome_score") is not None
            direction_correct = raw.get("direction_correct")
            if direction_correct is None and predicted_direction and actual_direction:
                direction_correct = predicted_direction == actual_direction
            if direction_correct is None and outcome_score_present:
                direction_correct = _num(raw.get("outcome_score")) > 0
            validated = bool(
                raw.get("validated")
                or raw.get("outcome_validated")
                or direction_correct is not None
                or actual_direction
                or outcome_score_present
            )
            timestamp = raw.get("timestamp") or raw.get("generated_at") or raw.get("window_start") or raw.get("created_at")
            parsed_time = _parse_time(timestamp)
            rows.append(
                {
                    "symbol": symbol,
                    "timestamp": timestamp,
                    "parsed_timestamp": parsed_time.isoformat() if parsed_time else None,
                    "prediction_horizon": raw.get("horizon") or raw.get("prediction_horizon") or raw.get("window"),
                    "predicted_direction": predicted_direction,
                    "actual_direction": actual_direction,
                    "probability": raw.get("predicted_probability") or raw.get("probability_score") or raw.get("probability"),
                    "confidence": raw.get("predicted_confidence") or raw.get("confidence"),
                    "validated": validated,
                    "direction_correct": bool(direction_correct),
                    "outcome_score": raw.get("outcome_score"),
                    "source": data_id,
                    "source_path": str(path),
                }
            )
    rows.sort(key=lambda item: item.get("parsed_timestamp") or "")
    validated_rows = [row for row in rows if row.get("validated")]
    correct_rows = [row for row in validated_rows if row.get("direction_correct")]
    timestamps = [_parse_time(row.get("timestamp")) for row in rows]
    timestamps = [value for value in timestamps if value is not None]
    oldest = min(timestamps) if timestamps else None
    latest = max(timestamps) if timestamps else None
    lookback_days = None
    if oldest and latest:
        lookback_days = max(0.0, (latest - oldest).total_seconds() / 86_400.0)
    avg_probability = None
    probability_values = [_num(row.get("probability"), math.nan) for row in rows]
    probability_values = [value for value in probability_values if math.isfinite(value)]
    if probability_values:
        avg_probability = sum(probability_values) / len(probability_values)
    avg_confidence = None
    confidence_values = [_num(row.get("confidence"), math.nan) for row in rows]
    confidence_values = [value for value in confidence_values if math.isfinite(value)]
    if confidence_values:
        avg_confidence = sum(confidence_values) / len(confidence_values)
    hit_rate = (len(correct_rows) / len(validated_rows)) if validated_rows else None
    latest_age = _age_seconds(latest.isoformat() if latest else None, now)
    return {
        "status": "gold_historical_probability_history_ready" if rows else "gold_historical_probability_history_missing",
        "row_count": len(rows),
        "validated_count": len(validated_rows),
        "validated_correct_count": len(correct_rows),
        "hit_rate": round(hit_rate, 4) if hit_rate is not None else None,
        "avg_probability": round(avg_probability, 4) if avg_probability is not None else None,
        "avg_confidence": round(avg_confidence, 4) if avg_confidence is not None else None,
        "oldest_timestamp": oldest.isoformat() if oldest else None,
        "latest_timestamp": latest.isoformat() if latest else None,
        "latest_age_seconds": round(latest_age, 3) if latest_age is not None else None,
        "lookback_days": round(lookback_days, 4) if lookback_days is not None else None,
        "recent_rows": rows[-12:],
        "validation_policy": "Only GOLD/XAU rows with timestamped outcome validation can count toward historical stress proof.",
    }


def _stress_scenario(
    scenario_id: str,
    label: str,
    passed: bool,
    proof: str,
    blocker_id: str,
    blocker_reason: str,
) -> Dict[str, Any]:
    return {
        "id": scenario_id,
        "label": label,
        "state": "passed" if passed else "blocked",
        "proof": proof,
        "blocker": None if passed else {"id": blocker_id, "reason": blocker_reason},
    }


def _build_gold_historical_stress_test(
    *,
    root: Path,
    cognitive_route: Dict[str, Any],
    hft_speed_gate: Dict[str, Any],
    historical_signal_lab: Dict[str, Any],
    generated_at: str,
    now: datetime,
) -> Dict[str, Any]:
    surfaces = _build_historical_stress_surface_map(root)
    present_surface_count = sum(1 for surface in surfaces if surface.get("present"))
    prediction_validation = _collect_gold_probability_history(root, now)
    row_count = int(_num(prediction_validation.get("row_count")))
    validated_count = int(_num(prediction_validation.get("validated_count")))
    correct_count = int(_num(prediction_validation.get("validated_correct_count")))
    hit_rate = prediction_validation.get("hit_rate")
    hit_rate_number = _num(hit_rate, -1.0) if hit_rate is not None else -1.0
    replay_lanes = historical_signal_lab.get("replay_lanes") if isinstance(historical_signal_lab.get("replay_lanes"), list) else []
    ready_lanes = [lane for lane in replay_lanes if str(lane.get("state") or "") != "blocked_missing_evidence"]
    chart_ready = any(lane.get("id") == "gold_ohlc_replay" and str(lane.get("state") or "") != "blocked_missing_evidence" for lane in replay_lanes)
    orderbook_ready = str(historical_signal_lab.get("orderbook_signal_state") or "") != "blocked_missing_evidence"
    stress_scenarios = [
        _stress_scenario(
            "historical_replay_surfaces",
            "Historical replay and backtest surfaces are present",
            present_surface_count >= len(surfaces),
            f"{present_surface_count}/{len(surfaces)} historical replay surfaces present.",
            "historical_stress_surfaces_missing",
            f"{present_surface_count}/{len(surfaces)} replay/backtest surfaces are present.",
        ),
        _stress_scenario(
            "gold_prediction_sample",
            "GOLD/XAU historical prediction sample exists",
            row_count >= 3,
            f"{row_count} GOLD/XAU prediction rows found.",
            "gold_historical_prediction_sample_too_small",
            "At least 3 timestamped GOLD/XAU historical prediction rows are required.",
        ),
        _stress_scenario(
            "validated_hit_rate",
            "Outcome validation clears minimum hit-rate proof",
            validated_count >= 3 and hit_rate_number >= 0.55,
            f"validated={validated_count} correct={correct_count} hit_rate={hit_rate}",
            "gold_historical_hit_rate_not_proven",
            "At least 3 validated rows and hit_rate >= 0.55 are required before the replay can pass.",
        ),
        _stress_scenario(
            "chart_and_orderbook_replay",
            "Chart/order-book replay evidence exists",
            chart_ready and orderbook_ready,
            f"chart_ready={chart_ready} orderbook_state={historical_signal_lab.get('orderbook_signal_state')}",
            "gold_chart_or_orderbook_replay_missing",
            "GOLD chart/OHLC replay and direct/proxy order-book pressure must be visible.",
        ),
        _stress_scenario(
            "cross_market_replay_lanes",
            "Cross-market lanes are replayable",
            len(ready_lanes) >= 4,
            f"{len(ready_lanes)}/{len(replay_lanes)} historical signal lanes replayable.",
            "cross_market_replay_lane_count_low",
            "At least 4 historical signal lanes must be replayable.",
        ),
        _stress_scenario(
            "hnc_auris_probability_route",
            "HNC/Auris/quantum/probability route is present for historical interpretation",
            bool(cognitive_route.get("route_passed")),
            f"route_passed={cognitive_route.get('route_passed')} blockers={len(cognitive_route.get('blockers') or [])}",
            "hnc_auris_probability_route_not_passing",
            "Historical stress evidence must still pass through HNC/Auris/lambda/quantum/probability context.",
        ),
    ]
    blockers = [scenario["blocker"] for scenario in stress_scenarios if scenario.get("blocker")]
    stress_passed = not blockers
    return {
        "status": "gold_historical_stress_passed" if stress_passed else "gold_historical_stress_blocking",
        "generated_at": generated_at,
        "mode": "gold_historical_replay_shadow_validation",
        "stress_passed": stress_passed,
        "data_source_policy": "No fake rows, synthetic fills, visual-only data, or unvalidated predictions count. Missing proof blocks handover.",
        "prediction_validation": prediction_validation,
        "scenarios": stress_scenarios,
        "surface_count": len(surfaces),
        "present_surface_count": present_surface_count,
        "route_surfaces": surfaces,
        "hft_read_through": {
            "gate_status": hft_speed_gate.get("status"),
            "gate_passed": bool(hft_speed_gate.get("gate_passed")),
            "speed_score": hft_speed_gate.get("speed_score"),
            "note": "Historical stress can pass as replay proof while live/high-frequency promotion remains blocked until fresh HFT gates pass.",
        },
        "live_order_allowed": False,
        "order_mutation_allowed": False,
        "blockers": blockers[:16],
    }


def _build_gold_agent_support_surface_map(root: Path) -> List[Dict[str, Any]]:
    surfaces: List[Dict[str, Any]] = []
    for spec in GOLD_AGENT_SUPPORT_SURFACES:
        path = _rooted(root, Path(spec["path"]))
        sample = _read_text_sample(path, limit=120_000) if path.exists() else ""
        markers = _matched_terms(sample, spec.get("required_markers", []))
        surfaces.append(
            {
                "id": spec["id"],
                "family": spec["family"],
                "path": str(path),
                "present": path.exists(),
                "status": "present_markers_verified" if path.exists() and markers else "present_needs_marker_review" if path.exists() else "missing",
                "role": spec["role"],
                "markers_found": markers,
                "required_markers": spec.get("required_markers", []),
                "route_use": "agent_chat_coding_tool_support_for_gold_mission",
            }
        )
    return surfaces


def _support_artifact_snapshot(root: Path, artifact_id: str, rel: Path, now: datetime) -> Dict[str, Any]:
    path = _rooted(root, rel)
    payload = _read_json(path)
    generated_at = payload.get("generated_at") or _summary(payload).get("generated_at")
    age = _age_seconds(generated_at, now)
    jobs = payload.get("jobs") if isinstance(payload.get("jobs"), list) else []
    queue_depth = payload.get("queue_depth")
    if queue_depth is None:
        queue_depth = len(jobs)
    active_job = payload.get("active_job") if isinstance(payload.get("active_job"), dict) else {}
    quality = payload.get("artifact_quality_report") if isinstance(payload.get("artifact_quality_report"), dict) else {}
    return {
        "id": artifact_id,
        "path": str(path),
        "present": bool(payload),
        "status": payload.get("status") or _summary(payload).get("status") or ("present" if payload else "missing"),
        "generated_at": generated_at,
        "age_seconds": round(age, 3) if age is not None else None,
        "fresh": bool(age is not None and age <= 900),
        "queue_depth": int(_num(queue_depth)),
        "active_job_present": bool(active_job),
        "handover_ready": bool(payload.get("handover_ready") or quality.get("handover_ready")),
        "summary_keys": sorted(_summary(payload).keys())[:10],
    }


def _build_gold_agent_coding_support(
    *,
    root: Path,
    generated_at: str,
    now: datetime,
    verified_data_gate: Dict[str, Any],
    hft_speed_gate: Dict[str, Any],
    historical_stress_test: Dict[str, Any],
    gold_action_command: Dict[str, Any],
) -> Dict[str, Any]:
    surfaces = _build_gold_agent_support_surface_map(root)
    artifacts = [
        _support_artifact_snapshot(root, artifact_id, rel, now)
        for artifact_id, rel in GOLD_AGENT_SUPPORT_PATHS.items()
    ]
    present_surface_count = sum(1 for surface in surfaces if surface.get("present"))
    present_artifact_count = sum(1 for artifact in artifacts if artifact.get("present"))
    fresh_artifact_count = sum(1 for artifact in artifacts if artifact.get("fresh"))
    by_id = {str(artifact.get("id")): artifact for artifact in artifacts}
    surface_by_id = {str(surface.get("id")): surface for surface in surfaces}

    chat_lanes = [
        {
            "id": "phi_operator_chat",
            "label": "Phi/Aureon operator chat",
            "surface_ids": ["phi_bridge", "llm_adapter", "dynamic_prompt_filter"],
            "artifact_ids": ["dynamic_prompt_filter"],
            "status": "ready" if surface_by_id.get("phi_bridge", {}).get("present") and by_id.get("dynamic_prompt_filter", {}).get("present") else "attention",
            "use_for_gold": "Agents can ask for clear operator summaries of GOLD evidence, blockers, and next actions.",
        },
        {
            "id": "thoughtbus_agent_handoff",
            "label": "ThoughtBus handoff lane",
            "surface_ids": ["thought_bus", "mind_thought_action_hub"],
            "artifact_ids": ["agent_company"],
            "status": "ready" if surface_by_id.get("thought_bus", {}).get("present") and by_id.get("agent_company", {}).get("present") else "attention",
            "use_for_gold": "Agents publish GOLD observations, missing evidence, repair work, and cross-role handoffs.",
        },
    ]
    tool_lanes = [
        {
            "id": "coding_organism_jobs",
            "label": "Coding organism job lane",
            "surface_ids": ["coding_organism_bridge", "autonomous_job_executor"],
            "artifact_ids": ["coding_organism_bridge", "autonomous_job_executor"],
            "status": "ready" if by_id.get("coding_organism_bridge", {}).get("present") and by_id.get("autonomous_job_executor", {}).get("present") else "attention",
            "use_for_gold": "Create local code, UI, adapters, tests, and repair tasks needed by GOLD agents.",
        },
        {
            "id": "capability_forge_builds",
            "label": "Capability forge build lane",
            "surface_ids": ["capability_forge", "tool_registry"],
            "artifact_ids": ["capability_forge"],
            "status": "ready" if by_id.get("capability_forge", {}).get("present") and surface_by_id.get("tool_registry", {}).get("present") else "attention",
            "use_for_gold": "Build new local tools or dashboards when agents discover a missing capability.",
        },
        {
            "id": "self_run_monitoring",
            "label": "Self-run monitor lane",
            "surface_ids": ["self_run_loop", "capital_market_monitor", "realtime_wave_monitor"],
            "artifact_ids": ["autonomous_self_run_loop"],
            "status": "ready" if by_id.get("autonomous_self_run_loop", {}).get("present") else "attention",
            "use_for_gold": "Keep the GOLD evidence refresh, replay, and self-repair queue visible.",
        },
    ]
    monitor_targets = [
        {
            "id": "verified_real_data_gate",
            "label": "Verified real data gate",
            "status": verified_data_gate.get("status"),
            "ready": bool(verified_data_gate.get("action_allowed_by_data")),
            "agent_action": "Refresh or repair missing timestamped market/runtime evidence.",
        },
        {
            "id": "hft_speed_prediction_gate",
            "label": "HFT speed and validated predictions",
            "status": hft_speed_gate.get("status"),
            "ready": bool(hft_speed_gate.get("gate_passed")),
            "agent_action": "Produce fresh, outcome-validated GOLD/XAU prediction rows before speed claims.",
        },
        {
            "id": "gold_historical_stress_test",
            "label": "Historical stress replay",
            "status": historical_stress_test.get("status"),
            "ready": bool(historical_stress_test.get("stress_passed")),
            "agent_action": "Run/rebuild historical replay and validation rows for GOLD/XAU.",
        },
        {
            "id": "gold_action_command",
            "label": "Gold action command",
            "status": gold_action_command.get("status"),
            "ready": str((gold_action_command.get("act") or {}).get("state") or "").startswith("shadow_validate_"),
            "agent_action": "Keep action as hold/shadow until proof chain is fully ready.",
        },
    ]
    blockers: List[Dict[str, Any]] = []
    if present_surface_count < len(surfaces):
        blockers.append({"id": "agent_support_surfaces_missing", "reason": f"{present_surface_count}/{len(surfaces)} support code surfaces are present."})
    if present_artifact_count < len(artifacts):
        blockers.append({"id": "agent_support_artifacts_missing", "reason": f"{present_artifact_count}/{len(artifacts)} support evidence artifacts are present."})
    if not any(lane.get("status") == "ready" for lane in chat_lanes):
        blockers.append({"id": "gold_agent_chat_lane_not_ready", "reason": "No agent chat/handoff lane is fully ready."})
    if not any(lane.get("status") == "ready" for lane in tool_lanes):
        blockers.append({"id": "gold_agent_tool_lane_not_ready", "reason": "No coding/tool lane is ready for agent-created support work."})

    return {
        "status": "gold_agent_coding_support_ready" if not blockers else "gold_agent_coding_support_attention",
        "generated_at": generated_at,
        "mission": "Let GOLD-focused agents use Aureon's coding, chat, tool, and monitoring systems to gather evidence, build missing local tooling, and publish proof without bypassing trading gates.",
        "support_ready": not blockers,
        "chat_lane_count": len(chat_lanes),
        "tool_lane_count": len(tool_lanes),
        "monitor_target_count": len(monitor_targets),
        "surface_count": len(surfaces),
        "present_surface_count": present_surface_count,
        "artifact_count": len(artifacts),
        "present_artifact_count": present_artifact_count,
        "fresh_artifact_count": fresh_artifact_count,
        "chat_lanes": chat_lanes,
        "tool_lanes": tool_lanes,
        "monitor_targets": monitor_targets,
        "support_artifacts": artifacts,
        "route_surfaces": surfaces,
        "agent_work_contract": [
            "Agents may create coding/tool/UI/research jobs for missing GOLD evidence.",
            "All agent-created work must publish source paths, tests, quality proof, and blockers.",
            "Chat answers must use the dynamic prompt filter and clear operator voice.",
            "Live trading, credential reveal, payments, filings, and destructive OS actions remain blocked.",
        ],
        "blockers": blockers[:12],
    }


def _build_gold_intelligence_map(root: Path) -> List[Dict[str, Any]]:
    surfaces: List[Dict[str, Any]] = []
    for spec in GOLD_INTELLIGENCE_SURFACES:
        path = _rooted(root, Path(str(spec["path"])))
        text = _read_text_sample(path)
        matches = _matched_terms(text, spec.get("terms", []))
        surfaces.append(
            {
                "id": spec["id"],
                "path": str(path),
                "relative_path": spec["path"],
                "department": spec["department"],
                "tool_type": spec["tool_type"],
                "present": path.exists(),
                "status": "ready_for_gold_context" if path.exists() and matches else "present_needs_gold_mapping" if path.exists() else "missing",
                "matched_terms": matches,
                "use_for_gold": spec["use_for_gold"],
                "activation_guidance": spec["activation_guidance"],
            }
        )
    return surfaces


def _build_local_research_packets(root: Path) -> List[Dict[str, Any]]:
    packets: List[Dict[str, Any]] = []
    for spec in GOLD_LOCAL_RESEARCH_PACKETS:
        path = _rooted(root, Path(str(spec["path"])))
        text = _read_text_sample(path)
        matches = _matched_terms(text, spec.get("terms", []))
        packets.append(
            {
                "id": spec["id"],
                "path": str(path),
                "relative_path": spec["path"],
                "topic": spec["topic"],
                "present": path.exists(),
                "matched_terms": matches,
                "confidence": spec["confidence"] if path.exists() and matches else 0.0,
                "guidance": spec["guidance"],
                "authority": "research_context_only",
            }
        )
    return packets


def _classify_gold_asset(asset: Dict[str, Any]) -> str:
    blob = " ".join(
        str(asset.get(key) or "")
        for key in ("symbol", "epic", "instrument_name", "instrument_type", "asset_class")
    ).lower()
    symbol = str(asset.get("symbol") or asset.get("epic") or "").upper()
    if symbol == "GOLD" or "xau" in blob:
        return "capital_gold_core"
    if symbol.startswith("GC") or "gold -" in blob or "future" in blob:
        return "gold_futures"
    if symbol in {"GLD", "GDX", "GDXJ", "IAU"} or "shares" in blob or "etf" in blob:
        return "gold_etf"
    if any(term in blob for term in ("newmont", "barrick", "goldcorp", "miner", "mining")):
        return "gold_miners"
    return "gold_related"


def _build_gold_market_universe(candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    buckets: Dict[str, List[Dict[str, Any]]] = {
        "capital_gold_core": [],
        "gold_futures": [],
        "gold_etf": [],
        "gold_miners": [],
        "gold_related": [],
    }
    for asset in candidates:
        bucket = _classify_gold_asset(asset)
        buckets.setdefault(bucket, []).append(asset)
    return {
        "bucket_counts": {bucket: len(items) for bucket, items in buckets.items()},
        "trade_ready_count": sum(1 for item in candidates if item.get("trade_ready")),
        "sample": {
            bucket: [
                {
                    "symbol": item.get("symbol"),
                    "epic": item.get("epic"),
                    "instrument_name": item.get("instrument_name"),
                    "market_status": item.get("market_status"),
                    "mid_price": item.get("mid_price"),
                    "last_snapshot_at": item.get("last_snapshot_at"),
                }
                for item in items[:5]
            ]
            for bucket, items in buckets.items()
        },
    }


def _score_gold_intelligence_coverage(surfaces: List[Dict[str, Any]], research_packets: List[Dict[str, Any]]) -> float:
    if not surfaces:
        return 0.0
    present = sum(1 for item in surfaces if item.get("present"))
    mapped = sum(1 for item in surfaces if item.get("matched_terms"))
    research_present = sum(1 for item in research_packets if item.get("present") and item.get("matched_terms"))
    return _clamp((present / len(surfaces)) * 0.45 + (mapped / len(surfaces)) * 0.35 + (research_present / max(1, len(research_packets))) * 0.2)


def _rows_by_key(payload: Dict[str, Any], key: str) -> Dict[str, Dict[str, Any]]:
    rows: Dict[str, Dict[str, Any]] = {}
    for row in _list_rows(payload):
        value = str(row.get(key) or "").lower()
        if value:
            rows[value] = row
    return rows


def _asset_bucket_counts(candidates: List[Dict[str, Any]]) -> Dict[str, int]:
    counts = {
        "capital_gold_core": 0,
        "gold_futures": 0,
        "gold_etf": 0,
        "gold_miners": 0,
        "gold_related": 0,
    }
    for asset in candidates:
        bucket = _classify_gold_asset(asset)
        counts[bucket] = counts.get(bucket, 0) + 1
    return counts


def _build_cross_market_driver_matrix(
    *,
    coverage: Dict[str, Any],
    exchange_matrix: Dict[str, Any],
    trading_intel: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    surfaces: List[Dict[str, Any]],
    research_packets: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    coverage_rows = _rows_by_key(coverage, "domain")
    exchange_rows = _rows_by_key(exchange_matrix, "exchange")
    trading_summary = _summary(trading_intel)
    surface_by_id = {str(item.get("id")): item for item in surfaces}
    asset_counts = _asset_bucket_counts(candidates)
    drivers: List[Dict[str, Any]] = []
    for spec in GOLD_DRIVER_FAMILIES:
        coverage_hits = [coverage_rows[domain] for domain in spec.get("coverage_domains", []) if domain in coverage_rows]
        exchange_hits = [exchange_rows[exchange] for exchange in spec.get("exchange_rows", []) if exchange in exchange_rows]
        surface_hits = [surface_by_id[surface_id] for surface_id in spec.get("surface_ids", []) if surface_id in surface_by_id]
        asset_hit_count = sum(asset_counts.get(bucket, 0) for bucket in spec.get("asset_buckets", []))
        fresh_count = sum(1 for row in coverage_hits if row.get("fresh")) + sum(
            1 for row in exchange_hits if ((row.get("current_state") or {}).get("fresh_feed"))
        )
        usable_count = sum(1 for row in coverage_hits if row.get("usable")) + sum(
            1 for row in exchange_hits if ((row.get("current_state") or {}).get("usable_for_mapping"))
        )
        mapped_surface_count = sum(1 for item in surface_hits if item.get("present") and item.get("matched_terms"))
        evidence_count = len(coverage_hits) + len(exchange_hits) + mapped_surface_count + min(asset_hit_count, 1)
        required_count = max(1, len(spec.get("coverage_domains", [])) + len(spec.get("exchange_rows", [])) + len(spec.get("surface_ids", [])))
        score = _clamp(
            (evidence_count / required_count) * 0.38
            + (fresh_count / max(1, len(coverage_hits) + len(exchange_hits))) * 0.22
            + (usable_count / max(1, len(coverage_hits) + len(exchange_hits))) * 0.18
            + (mapped_surface_count / max(1, len(spec.get("surface_ids", [])))) * 0.17
            + (0.05 if asset_hit_count else 0.0)
        )
        blockers: List[str] = []
        for row in coverage_hits:
            if not row.get("fresh"):
                blockers.append(f"{row.get('domain')}:not_fresh")
            if not row.get("usable"):
                blockers.append(f"{row.get('domain')}:not_usable")
            for missing in row.get("missing") or []:
                blockers.append(f"{row.get('domain')}:{missing}")
        for row in exchange_hits:
            blockers.extend(str(item) for item in (row.get("gaps") or [])[:4])
        if spec["id"] in {"capital_gold_cfd", "gold_futures_curve", "gold_etfs_miners"} and not asset_hit_count:
            blockers.append("no_related_gold_asset_bucket")
        if spec["id"] == "geopolitical_news_sentiment" and not coverage_rows.get("macro_events_context", {}).get("fresh"):
            blockers.append("geopolitical_calendar_not_fresh")
        if trading_summary.get("runtime_stale"):
            blockers.append("runtime_stale_blocks_live_decision_use")
        driver_state = "ready_shadow_driver" if score >= 0.7 else "partial_driver" if score >= 0.4 else "blocked_driver"
        drivers.append(
            {
                "id": spec["id"],
                "label": spec["label"],
                "driver_role": spec["driver_role"],
                "driver_state": driver_state,
                "score": round(score, 4),
                "fresh": fresh_count > 0 and not any("not_fresh" in item for item in blockers),
                "usable_for_gold_thesis": score >= 0.4,
                "coverage_domains": spec.get("coverage_domains", []),
                "exchange_rows": spec.get("exchange_rows", []),
                "surface_ids": spec.get("surface_ids", []),
                "asset_buckets": spec.get("asset_buckets", []),
                "asset_hit_count": asset_hit_count,
                "evidence_count": evidence_count,
                "fresh_source_count": fresh_count,
                "usable_source_count": usable_count,
                "mapped_surface_count": mapped_surface_count,
                "blockers": sorted(set(blockers))[:10],
                "next_action": spec["next_action"],
            }
        )
    return drivers


def _channel_status(row: Dict[str, Any], channel_name: str) -> str:
    channels = row.get("data_channels") if isinstance(row.get("data_channels"), list) else []
    for channel in channels:
        if not isinstance(channel, dict):
            continue
        if str(channel.get("name") or "").lower() == channel_name.lower():
            return str(channel.get("status") or "unknown")
    return "missing"


def _build_gold_exchange_optimization(
    *,
    asset: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    exchange_matrix: Dict[str, Any],
    exchange_monitoring: Dict[str, Any],
    driver_matrix: List[Dict[str, Any]],
    runtime_stale: bool,
    snapshot_fresh: bool,
    generated_at: str,
) -> Dict[str, Any]:
    exchange_rows = _rows_by_key(exchange_matrix, "exchange")
    monitoring_rows = _rows_by_key(exchange_monitoring, "exchange")
    asset_counts = _asset_bucket_counts(candidates)
    driver_by_id = {str(driver.get("id")): driver for driver in driver_matrix}
    venue_specs = [
        {
            "id": "capital",
            "label": "Capital.com",
            "role": "primary_gold_target_venue",
            "target_authority": "GOLD/XAU direct target only; live orders remain runtime-gated.",
            "watch_symbols": ["GOLD", "XAUUSD", "USOIL", "UKOIL", "DXY proxy", "major indices"],
            "required_channels": ["live_ticks", "price_history", "market_hours"],
            "freshness_budget_seconds": 2,
            "driver_ids": ["capital_gold_cfd", "gold_futures_curve", "oil_energy_inflation", "equity_risk_vix"],
        },
        {
            "id": "alpaca",
            "label": "Alpaca",
            "role": "gold_etf_miner_equity_confirmation",
            "target_authority": "Read-only GLD/IAU/GDX/GDXJ/miner/risk-index confirmation.",
            "watch_symbols": ["GLD", "IAU", "GDX", "GDXJ", "NEM", "BARRICK/GOLD", "SPY", "QQQ"],
            "required_channels": ["live_ticks", "market_hours"],
            "freshness_budget_seconds": 15,
            "driver_ids": ["gold_etfs_miners", "equity_risk_vix"],
        },
        {
            "id": "binance",
            "label": "Binance",
            "role": "crypto_liquidity_fast_proxy",
            "target_authority": "Read-only crypto liquidity/risk proxy; not a GOLD target.",
            "watch_symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "USDT liquidity", "crypto breadth"],
            "required_channels": ["live_ticks"],
            "freshness_budget_seconds": 5,
            "driver_ids": ["crypto_liquidity_safe_haven"],
        },
        {
            "id": "kraken",
            "label": "Kraken",
            "role": "crypto_liquidity_collateral_proxy",
            "target_authority": "Read-only crypto/liquidity/collateral proxy; not a GOLD target.",
            "watch_symbols": ["BTC/USD", "ETH/USD", "SOL/USD", "USD liquidity"],
            "required_channels": ["live_ticks"],
            "freshness_budget_seconds": 5,
            "driver_ids": ["crypto_liquidity_safe_haven"],
        },
    ]
    venues: List[Dict[str, Any]] = []
    blockers: List[Dict[str, Any]] = []
    ready_count = 0
    for spec in venue_specs:
        row = exchange_rows.get(spec["id"], {})
        monitoring_row = monitoring_rows.get(spec["id"], {})
        current_state = row.get("current_state") if isinstance(row.get("current_state"), dict) else {}
        present = bool(row)
        fresh_feed = bool(current_state.get("fresh_feed"))
        usable_for_mapping = bool(current_state.get("usable_for_mapping"))
        usable_for_decision = bool(current_state.get("usable_for_decision"))
        channel_checks = [
            {
                "name": channel,
                "status": _channel_status(row, channel),
                "ready": _channel_status(row, channel).lower() in {"fresh", "available", "active", "configured"},
            }
            for channel in spec["required_channels"]
        ]
        driver_checks = [
            {
                "id": driver_id,
                "state": (driver_by_id.get(driver_id) or {}).get("driver_state") or "missing_driver",
                "score": (driver_by_id.get(driver_id) or {}).get("score"),
            }
            for driver_id in spec["driver_ids"]
        ]
        venue_blockers: List[str] = []
        if not present:
            venue_blockers.append("exchange_row_missing")
        if present and not fresh_feed:
            venue_blockers.append("fresh_feed_missing")
        if present and not usable_for_mapping:
            venue_blockers.append("mapping_not_usable")
        if spec["id"] == "capital" and not asset:
            venue_blockers.append("capital_gold_asset_missing")
        if spec["id"] == "capital" and not snapshot_fresh:
            venue_blockers.append("capital_gold_snapshot_not_fresh")
        if spec["id"] == "capital" and _channel_status(row, "price_history").lower() not in {"available", "fresh", "active", "configured"}:
            venue_blockers.append("capital_gold_price_history_missing")
        for channel in channel_checks:
            if not channel["ready"]:
                venue_blockers.append(f"{channel['name']}_channel_{channel['status']}")
        for gap in row.get("gaps") or []:
            venue_blockers.append(str(gap))
        for gap in monitoring_row.get("gaps") or []:
            venue_blockers.append(str(gap))
        if runtime_stale:
            venue_blockers.append("runtime_stale_blocks_live_decision_use")
        channels_ready = all(bool(channel.get("ready")) for channel in channel_checks)
        venue_ready = present and fresh_feed and usable_for_mapping and channels_ready and not any(
            blocker in venue_blockers
            for blocker in {"exchange_row_missing", "capital_gold_asset_missing", "capital_gold_snapshot_not_fresh", "capital_gold_price_history_missing"}
        )
        if venue_ready:
            ready_count += 1
        venues.append(
            {
                "id": spec["id"],
                "label": spec["label"],
                "role": spec["role"],
                "target_authority": spec["target_authority"],
                "present": present,
                "ready_for_gold_monitoring": venue_ready,
                "fresh_feed": fresh_feed,
                "usable_for_mapping": usable_for_mapping,
                "usable_for_decision": usable_for_decision,
                "channels_ready": channels_ready,
                "freshness_budget_seconds": spec["freshness_budget_seconds"],
                "watch_symbols": spec["watch_symbols"],
                "channel_checks": channel_checks,
                "driver_checks": driver_checks,
                "blockers": sorted(set(venue_blockers))[:12],
            }
        )
        if spec["id"] == "capital" and venue_blockers:
            blockers.append({"id": "capital_gold_exchange_not_fully_optimized", "reason": ", ".join(sorted(set(venue_blockers))[:5])})
    watchlist = [
        {"bucket": "direct_gold_target", "symbols": ["GOLD", "XAUUSD"], "venue": "Capital.com", "authority": "target_shadow_only"},
        {"bucket": "gold_etfs_miners", "symbols": ["GLD", "IAU", "GDX", "GDXJ", "NEM", "BARRICK/GOLD"], "venue": "Alpaca/Capital", "authority": "confirmation_only"},
        {"bucket": "energy_inflation", "symbols": ["USOIL", "UKOIL", "WTI", "BRENT", "NATGAS"], "venue": "Capital/data ocean", "authority": "confirmation_only"},
        {"bucket": "usd_rates_macro", "symbols": ["DXY", "US10Y", "US02Y", "TIPS", "CPI", "FOMC"], "venue": "macro/data ocean", "authority": "context_only"},
        {"bucket": "risk_equity", "symbols": ["VIX", "SPX", "SPY", "QQQ", "NASDAQ"], "venue": "Alpaca/Capital/data ocean", "authority": "confirmation_only"},
        {"bucket": "crypto_liquidity", "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BTC/USD", "ETH/USD"], "venue": "Binance/Kraken", "authority": "liquidity_proxy_only"},
    ]
    monitoring_contract = [
        {
            "id": "capital_gold_micro_monitor",
            "cadence_seconds": 2,
            "inputs": ["Capital GOLD bid/ask", "spread", "market status", "price history channel"],
            "blocks_if_missing": True,
        },
        {
            "id": "connected_assets_fast_monitor",
            "cadence_seconds": 5,
            "inputs": ["oil/energy", "crypto liquidity", "risk index proxies", "scanner fusion"],
            "blocks_if_missing": False,
        },
        {
            "id": "macro_context_monitor",
            "cadence_seconds": 900,
            "inputs": ["DXY", "yields", "inflation/calendar/news", "geopolitical context"],
            "blocks_if_missing": False,
        },
        {
            "id": "historical_replay_monitor",
            "cadence_seconds": 300,
            "inputs": ["GOLD bars", "prediction rows", "outcome validation", "lead/lag history"],
            "blocks_if_missing": True,
        },
    ]
    ready_watchlist_buckets = sum(1 for item in watchlist if item["symbols"])
    optimization_score = _clamp(
        (ready_count / max(1, len(venues))) * 0.45
        + (ready_watchlist_buckets / len(watchlist)) * 0.2
        + (min(asset_counts.get("capital_gold_core", 0), 1) * 0.15)
        + (0.1 if asset_counts.get("gold_etf", 0) or asset_counts.get("gold_miners", 0) else 0.0)
        + (0.1 if not runtime_stale else 0.0)
    )
    if ready_count < 3:
        blockers.append({"id": "gold_exchange_monitoring_coverage_low", "reason": f"{ready_count}/{len(venues)} venues are ready for GOLD monitoring."})
    if runtime_stale:
        blockers.append({"id": "runtime_stale_exchange_monitoring_hold", "reason": "Exchange optimization can monitor, but live decision use is held while runtime is stale."})
    return {
        "status": "gold_exchange_optimization_ready" if not blockers else "gold_exchange_optimization_attention",
        "generated_at": generated_at,
        "mode": "dynamic_gold_exchange_monitoring",
        "optimization_score": round(optimization_score, 4),
        "venue_count": len(venues),
        "ready_venue_count": ready_count,
        "watchlist_bucket_count": len(watchlist),
        "primary_target_venue": "Capital.com",
        "live_order_allowed": False,
        "order_mutation_allowed": False,
        "venues": venues,
        "related_asset_watchlist": watchlist,
        "monitoring_contract": monitoring_contract,
        "asset_bucket_counts": asset_counts,
        "blockers": blockers[:12],
        "safety_contract": [
            "Capital GOLD is the only target lane.",
            "Alpaca, Binance, Kraken, macro, energy, and risk assets are confirmation/proxy lanes unless separately authorized.",
            "Monitoring can be dynamic; execution remains gated by runtime, risk, credentials, and verified data.",
            "No fake metrics, no stale values, no credential reveal, and no external mutation unlock action.",
        ],
    }


def _build_gold_margin_trader_surface_map(root: Path) -> List[Dict[str, Any]]:
    surfaces: List[Dict[str, Any]] = []
    for spec in GOLD_MARGIN_TRADER_UNITY_SURFACES:
        path = _rooted(root, Path(spec["path"]))
        sample = _read_text_sample(path, limit=100_000) if path.exists() else ""
        markers = _matched_terms(sample, spec.get("required_markers", []))
        surfaces.append(
            {
                "id": spec["id"],
                "path": str(path),
                "present": path.exists(),
                "status": "present_markers_verified" if path.exists() and markers else "present_needs_marker_review" if path.exists() else "missing",
                "role": spec["role"],
                "markers_found": markers,
                "required_markers": spec.get("required_markers", []),
                "route_use": "margin_trader_unity_focus_for_capital_gold",
            }
        )
    return surfaces


def _build_gold_margin_trader_unity(
    *,
    root: Path,
    decision: Dict[str, Any],
    three_p_gate: Dict[str, Any],
    verified_data_gate: Dict[str, Any],
    gold_exchange_optimization: Dict[str, Any],
    cognitive_route: Dict[str, Any],
    hft_speed_gate: Dict[str, Any],
    historical_stress_test: Dict[str, Any],
    generated_at: str,
) -> Dict[str, Any]:
    surfaces = _build_gold_margin_trader_surface_map(root)
    present_surface_count = sum(1 for surface in surfaces if surface.get("present"))
    mission_directives = [
        {
            "id": "unify_target",
            "directive": "Every margin trader component treats Capital GOLD/XAU as the only target lane for this mission.",
            "state": "active",
        },
        {
            "id": "use_connected_markets_as_context",
            "directive": "Crypto, ETF/miner, oil/energy, USD/rates, equity risk, and geopolitics are confirmation/context lanes, not independent margin targets.",
            "state": "active",
        },
        {
            "id": "respect_3p_floor",
            "directive": "Margin sizing cannot promote unless expected net profit clears at least 3p after spread, slippage, financing, and fees.",
            "state": "ready" if str(three_p_gate.get("state")) == "shadow_trade_candidate" else "held",
        },
        {
            "id": "route_through_hnc_auris",
            "directive": "Margin timing must pass HNC/Auris/lambda/quantum/probability context before confidence rises.",
            "state": "ready" if cognitive_route.get("route_passed") else "held",
        },
        {
            "id": "shadow_before_live",
            "directive": "The margin trader may size, replay, and shadow-validate; it must not place or mutate live orders from this report.",
            "state": "active",
        },
    ]
    margin_roles = [
        {
            "role": "Unified Margin Brain",
            "surface_id": "unified_margin_brain",
            "job": "Fuse Capital GOLD target, collateral/risk, exchange optimization, and HNC/Auris proof into one margin posture.",
        },
        {
            "role": "Dynamic Margin Sizer",
            "surface_id": "dynamic_margin_sizer",
            "job": "Calculate only the smallest shadow size that can clear 3p net when all proof is fresh.",
        },
        {
            "role": "Margin Wave Rider",
            "surface_id": "margin_wave_rider",
            "job": "Watch waveform timing and avoid entries when GOLD is stretched, stale, or contradictory.",
        },
        {
            "role": "Profit And Position Monitor",
            "surface_id": "real_profit_monitor",
            "job": "Reject phantom profit and reconcile positions before any new margin route is considered.",
        },
    ]
    blockers: List[Dict[str, Any]] = []
    if present_surface_count < len(surfaces):
        blockers.append({"id": "margin_trader_unity_surfaces_missing", "reason": f"{present_surface_count}/{len(surfaces)} margin unity surfaces are present."})
    if not verified_data_gate.get("action_allowed_by_data"):
        blockers.append({"id": "verified_real_data_gate_blocking", "reason": "Margin trader unity can monitor, but cannot promote while real-data gate is blocking."})
    if str(three_p_gate.get("state")) != "shadow_trade_candidate":
        blockers.append({"id": "three_p_floor_not_proven", "reason": "Margin trader cannot size a candidate until the 3p net floor is mathematically proven."})
    if not gold_exchange_optimization.get("ready_venue_count"):
        blockers.append({"id": "gold_exchange_optimization_not_ready", "reason": "No exchange venue is ready for GOLD monitoring."})
    if not cognitive_route.get("route_passed"):
        blockers.append({"id": "hnc_auris_route_not_passing", "reason": "HNC/Auris/lambda/quantum/probability route is not passing."})
    if not historical_stress_test.get("stress_passed"):
        blockers.append({"id": "historical_stress_not_proven", "reason": "Historical GOLD/XAU replay has not proven the margin thesis."})
    if not hft_speed_gate.get("gate_passed"):
        blockers.append({"id": "hft_speed_gate_not_passing", "reason": "Fast GOLD prediction path is not fresh and outcome-validated."})

    unity_state = "gold_margin_unity_shadow_ready" if not blockers else "gold_margin_unity_held"
    return {
        "status": "gold_margin_trader_unity_ready" if unity_state.endswith("ready") else "gold_margin_trader_unity_attention",
        "generated_at": generated_at,
        "unity_state": unity_state,
        "target_symbol": "GOLD",
        "target_venue": "Capital.com",
        "mission": "Tell every margin trader and margin support system to work in unity around Capital GOLD, with connected assets as context and hard gates preserved.",
        "surface_count": len(surfaces),
        "present_surface_count": present_surface_count,
        "margin_roles": margin_roles,
        "mission_directives": mission_directives,
        "proof_inputs": {
            "three_p_floor_state": three_p_gate.get("state"),
            "three_p_side": three_p_gate.get("side"),
            "suggested_shadow_size": three_p_gate.get("suggested_shadow_size"),
            "verified_real_data_status": verified_data_gate.get("status"),
            "exchange_optimization_status": gold_exchange_optimization.get("status"),
            "ready_exchange_venues": gold_exchange_optimization.get("ready_venue_count"),
            "hnc_auris_route_status": cognitive_route.get("status"),
            "hft_speed_status": hft_speed_gate.get("status"),
            "historical_stress_status": historical_stress_test.get("status"),
            "shadow_observation_allowed": bool(decision.get("shadow_observation_allowed")),
        },
        "margin_command": {
            "act": "shadow_monitor_gold_margin_unity" if blockers else "shadow_validate_gold_margin_candidate",
            "live_order_allowed": False,
            "margin_order_allowed": False,
            "leverage_change_allowed": False,
            "order_mutation_allowed": False,
            "instruction": "Unify all margin logic toward GOLD, gather/replay/size in shadow only, and wait for verified gates before any live runtime can consider execution.",
        },
        "route_surfaces": surfaces,
        "blockers": blockers[:14],
    }


def _build_intelligence_gaps(
    *,
    asset: Dict[str, Any],
    snapshot_fresh: bool,
    runtime_stale: bool,
    surfaces: List[Dict[str, Any]],
    research_packets: List[Dict[str, Any]],
    coverage_summary: Dict[str, Any],
    driver_matrix: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    gaps: List[Dict[str, Any]] = []
    if not asset:
        gaps.append(
            {
                "id": "gold_market_missing",
                "severity": "critical",
                "owner": "Capital Venue Specialist",
                "gap": "Capital GOLD was not found in the local tradable asset registry.",
                "next_action": "Refresh the Capital asset registry and prove GOLD/XAU epics.",
            }
        )
    if not snapshot_fresh:
        gaps.append(
            {
                "id": "gold_snapshot_not_fresh",
                "severity": "high",
                "owner": "Gold Market Data Ocean Operator",
                "gap": "Capital GOLD price snapshot is stale or missing.",
                "next_action": "Refresh Capital GOLD details, quote, and OHLC evidence before accepting a direction.",
            }
        )
    if runtime_stale:
        gaps.append(
            {
                "id": "runtime_not_fresh",
                "severity": "high",
                "owner": "COO Runtime Steward",
                "gap": "Runtime freshness is not sufficient for live decision use.",
                "next_action": "Restore fresh runtime ticks; keep this report in shadow/observe mode.",
            }
        )
    macro_surfaces = [item for item in surfaces if item.get("department") in {"research", "intelligence"}]
    if any(not item.get("present") for item in macro_surfaces) or _num(coverage_summary.get("usable_domain_count")) < 3:
        gaps.append(
            {
                "id": "macro_usd_rates_context_incomplete",
                "severity": "medium",
                "owner": "Macro And Dollar Analyst",
                "gap": "USD, rates, macro calendar, or public macro domains are incomplete in local evidence.",
                "next_action": "Pull read-only USD/DXY, Treasury yield, inflation, oil, VIX, calendar, and news packets.",
            }
        )
    if not any(item.get("matched_terms") for item in research_packets):
        gaps.append(
            {
                "id": "local_gold_research_not_selected",
                "severity": "medium",
                "owner": "Counter Intelligence Validator",
                "gap": "No local gold research packets were selected.",
                "next_action": "Index repo research and attach only source-linked gold packets.",
            }
        )
    driver_matrix = driver_matrix or []
    weak_drivers = [driver for driver in driver_matrix if driver.get("driver_state") != "ready_shadow_driver"]
    if weak_drivers:
        gaps.append(
            {
                "id": "cross_market_driver_matrix_partial",
                "severity": "medium",
                "owner": "Gold Strategy Steward",
                "gap": f"{len(weak_drivers)} cross-market gold driver(s) need fresher or more usable evidence.",
                "next_action": "Advance the weakest gold drivers first: "
                + ", ".join(str(driver.get("id")) for driver in weak_drivers[:5]),
            }
        )
    return gaps


def _build_gold_swarm_intelligence(
    *,
    driver_matrix: List[Dict[str, Any]],
    surfaces: List[Dict[str, Any]],
    research_packets: List[Dict[str, Any]],
    signals: List[Dict[str, Any]],
    blockers: List[Dict[str, Any]],
    intelligence_gaps: List[Dict[str, Any]],
    runtime_stale: bool,
    snapshot_fresh: bool,
) -> Dict[str, Any]:
    drivers_by_id = {str(driver.get("id")): driver for driver in driver_matrix}
    surface_count = len([surface for surface in surfaces if surface.get("present")])
    research_count = len([packet for packet in research_packets if packet.get("present") and packet.get("matched_terms")])
    agents: List[Dict[str, Any]] = []
    for spec in GOLD_SWARM_AGENTS:
        assigned = [drivers_by_id[driver_id] for driver_id in spec.get("driver_ids", []) if driver_id in drivers_by_id]
        score = _clamp(sum(_num(driver.get("score")) for driver in assigned) / max(1, len(assigned)))
        driver_blockers = sorted({str(blocker) for driver in assigned for blocker in driver.get("blockers", [])})[:8]
        weak = [driver for driver in assigned if driver.get("driver_state") != "ready_shadow_driver"]
        if runtime_stale or driver_blockers or weak:
            state = "attention"
        elif assigned:
            state = "active"
        else:
            state = "waiting"
        agents.append(
            {
                "id": spec["id"],
                "role": spec["role"],
                "department": spec["department"],
                "mode": spec["mode"],
                "mission": spec["mission"],
                "assigned_driver_ids": [driver.get("id") for driver in assigned],
                "assigned_driver_count": len(assigned),
                "score": round(score, 4),
                "state": state,
                "data_gathering_task": (
                    "Gather source-linked evidence for "
                    + ", ".join(str(driver.get("label")) for driver in assigned[:3])
                    if assigned
                    else "Wait for a mapped gold driver."
                ),
                "sensemaking_task": (
                    "Return compact evidence, contradiction notes, freshness state, and confidence effect to the gold compiler."
                ),
                "blockers": driver_blockers,
            }
        )

    active_count = sum(1 for agent in agents if agent["state"] == "active")
    attention_count = sum(1 for agent in agents if agent["state"] == "attention")
    gather_count = sum(1 for agent in agents if "gather" in agent["mode"])
    sense_count = sum(1 for agent in agents if agent["mode"] in {"sensemake", "gather_and_compare", "compile", "gate", "validate"})
    compile_blockers = [blocker.get("id") for blocker in blockers] + [gap.get("id") for gap in intelligence_gaps if gap.get("severity") in {"critical", "high"}]
    compile_state = "held_for_fresh_evidence" if compile_blockers else "ready_for_shadow_compile"
    return {
        "status": "gold_swarm_attention" if attention_count else "gold_swarm_active",
        "agent_count": len(agents),
        "active_agent_count": active_count,
        "attention_agent_count": attention_count,
        "gather_agent_count": gather_count,
        "sensemaking_agent_count": sense_count,
        "agents": agents,
        "data_gathering_contract": {
            "policy": "use_existing_repo_tools_and_state_first",
            "source_count": surface_count + research_count + len(signals),
            "surfaces_present": surface_count,
            "research_packets_present": research_count,
            "no_reinvention": True,
            "authority": "read_only_data_gathering_until_existing_runtime_gates_pass",
        },
        "sensemaking_contract": {
            "compiler": "Aureon Gold Capital Intelligence Company",
            "inputs": ["driver_matrix", "repo_surfaces", "local_research_packets", "runtime_state", "HNC/Auris", "counter_intelligence"],
            "output": "single shadow gold thesis with proof, blockers, stale penalties, and next actions",
            "no_single_agent_final_authority": True,
        },
        "compile_gate": {
            "state": compile_state,
            "runtime_stale": runtime_stale,
            "capital_snapshot_fresh": snapshot_fresh,
            "blocking_items": compile_blockers[:12],
            "handover": "shadow_observation_only" if compile_blockers else "shadow_thesis_ready",
        },
    }


def _walk_dicts(value: Any, *, limit: int = 4000) -> Iterable[Dict[str, Any]]:
    seen = 0
    stack: List[Any] = [value]
    while stack and seen < limit:
        item = stack.pop()
        if isinstance(item, dict):
            seen += 1
            yield item
            stack.extend(item.values())
        elif isinstance(item, list):
            stack.extend(item)


def _gold_related_blob(*parts: Any) -> bool:
    blob = " ".join(str(part or "") for part in parts).lower()
    return any(term in blob for term in ("gold", "xau", "gld", "gdx", "gcm", "gc=f", "goldusd", "xauusd"))


def _gold_shadow_context_relation(*parts: Any) -> str:
    blob = " ".join(str(part or "") for part in parts).lower()
    if _gold_related_blob(blob):
        return "gold_target_candidate"
    if any(term in blob for term in ("oil", "crude", "brent", "wti", "usoil", "ukoil", "xbr", "xng", "natgas", "gas", "energy")):
        return "energy_confirmation_context"
    if any(term in blob for term in ("dxy", "usd", "yield", "rate", "inflation", "fred", "cpi", "treasury")):
        return "usd_rates_confirmation_context"
    if any(term in blob for term in ("vix", "spx", "spy", "nasdaq", "index", "equity", "risk")):
        return "risk_confirmation_context"
    if any(term in blob for term in ("btc", "bitcoin", "crypto", "eth", "liquidity")):
        return "crypto_liquidity_context"
    if any(term in blob for term in ("news", "sentiment", "geopolit", "war", "sanction", "macro")):
        return "geopolitical_macro_context"
    return "excluded_generic_shadow"


def _state_from_ready(ready: bool, attention: bool = False, blocked: bool = False) -> str:
    if blocked:
        return "blocked_missing_evidence"
    if ready and not attention:
        return "ready_shadow_replay"
    if ready:
        return "attention_needs_fresh_proof"
    return "attention_mapped_not_proven"


def _capital_price_history_state(exchange_matrix: Dict[str, Any]) -> Dict[str, Any]:
    exchange_rows = _rows_by_key(exchange_matrix, "exchange")
    capital_row = exchange_rows.get("capital") or _find_row(exchange_matrix, "capital.com")
    channels = capital_row.get("data_channels") if isinstance(capital_row.get("data_channels"), list) else []
    by_name = {str(channel.get("name") or "").lower(): channel for channel in channels if isinstance(channel, dict)}
    price_history = by_name.get("price_history", {})
    live_ticks = by_name.get("live_ticks", {})
    market_hours = by_name.get("market_hours", {})
    current_state = capital_row.get("current_state") if isinstance(capital_row.get("current_state"), dict) else {}
    return {
        "exchange": capital_row.get("exchange") or "capital",
        "label": capital_row.get("label") or "Capital.com",
        "price_history_available": str(price_history.get("status") or "").lower() in {"available", "fresh", "configured", "active"},
        "live_ticks_status": live_ticks.get("status"),
        "market_hours_status": market_hours.get("status"),
        "fresh_feed": bool(current_state.get("fresh_feed")),
        "waveform_history_active": bool(current_state.get("waveform_history_active")),
        "usable_for_mapping": bool(current_state.get("usable_for_mapping")),
        "usable_for_decision": bool(current_state.get("usable_for_decision")),
        "stream_preferred": bool((capital_row.get("optimization_policy") or {}).get("stream_preferred")),
        "gaps": [str(item) for item in (capital_row.get("gaps") or [])],
    }


def _extract_lead_lag_candidates(world_ecosystem: Dict[str, Any]) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []
    for item in _walk_dicts(world_ecosystem):
        has_relationship = item.get("leader") is not None and item.get("follower") is not None
        has_metric = item.get("correlation") is not None or item.get("lag_seconds") is not None
        if not (has_relationship and has_metric):
            continue
        leader = str(item.get("leader") or "")
        follower = str(item.get("follower") or "")
        symbol = str(item.get("symbol") or item.get("raw_symbol") or follower)
        gold_related = _gold_related_blob(symbol, leader, follower, item.get("category"))
        candidates.append(
            {
                "symbol": symbol,
                "leader": leader,
                "follower": follower,
                "side": item.get("side"),
                "reason": item.get("reason") or "cross_asset_presignal",
                "category": item.get("category") or "cross_asset",
                "correlation": round(_num(item.get("correlation")), 4),
                "lag_seconds": _num(item.get("lag_seconds")),
                "confidence": round(_num(item.get("confidence")), 4),
                "change_pct": round(_num(item.get("change_pct")), 6),
                "remaining_pct": round(_num(item.get("remaining_pct")), 6),
                "gold_related": gold_related,
                "relationship_to_gold": "direct_gold_pair" if gold_related else "proxy_driver_for_gold_context",
            }
        )
    candidates.sort(key=lambda item: (not item["gold_related"], -abs(_num(item.get("correlation"))), -_num(item.get("confidence"))))
    unique: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for item in candidates:
        key = f"{item.get('leader')}->{item.get('follower')}:{item.get('symbol')}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
        if len(unique) >= 12:
            break
    return unique


def _extract_orderbook_evidence(shadow_report: Dict[str, Any]) -> Dict[str, Any]:
    samples: List[Dict[str, Any]] = []
    for item in _walk_dicts(shadow_report):
        pressure = item.get("orderbook_pressure") if isinstance(item.get("orderbook_pressure"), dict) else {}
        fast_money = item.get("fast_money_profile") if isinstance(item.get("fast_money_profile"), dict) else {}
        alignment = item.get("orderbook_alignment") or fast_money.get("orderbook_alignment") or pressure.get("pressure_side")
        score = item.get("orderbook_score")
        if score is None:
            score = fast_money.get("orderbook_score")
        if score is None:
            score = pressure.get("score")
        if alignment is None and score is None:
            continue
        symbol = str(item.get("symbol") or pressure.get("symbol") or item.get("route_symbol") or "")
        if not symbol:
            continue
        samples.append(
            {
                "symbol": symbol,
                "venue": item.get("venue"),
                "side": item.get("side"),
                "confidence": round(_num(item.get("confidence")), 4),
                "orderbook_score": round(_num(score), 4),
                "orderbook_alignment": str(alignment or "unknown"),
                "orderbook_available": bool(pressure.get("available")) if pressure else str(alignment or "").lower() not in {"unavailable", "not_sampled"},
                "pressure_side": pressure.get("pressure_side"),
                "reason": pressure.get("reason") or item.get("selection_basis") or "orderbook evidence packet",
                "gold_related": _gold_related_blob(symbol, item.get("route_signature")),
            }
        )
    samples.sort(key=lambda item: (not item["gold_related"], -_num(item.get("orderbook_score")), str(item.get("symbol"))))
    unique: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for item in samples:
        key = f"{item.get('symbol')}:{item.get('side')}:{item.get('orderbook_alignment')}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
        if len(unique) >= 12:
            break
    available_count = sum(1 for item in unique if item.get("orderbook_available"))
    gold_count = sum(1 for item in unique if item.get("gold_related"))
    return {
        "status": "gold_orderbook_pressure_ready" if gold_count else "proxy_orderbook_pressure_only" if unique else "orderbook_pressure_missing",
        "sample_count": len(unique),
        "available_count": available_count,
        "gold_sample_count": gold_count,
        "samples": unique,
        "source_status": shadow_report.get("status") or "missing",
    }


def _extract_scanner_fusion_evidence(scanner_fusion: Dict[str, Any]) -> Dict[str, Any]:
    raw_candidates = scanner_fusion.get("candidates") if isinstance(scanner_fusion.get("candidates"), list) else []
    candidates: List[Dict[str, Any]] = []
    for item in raw_candidates:
        if not isinstance(item, dict):
            continue
        symbol = str(item.get("symbol") or item.get("route_symbol") or "")
        candidates.append(
            {
                "symbol": symbol,
                "side": item.get("side"),
                "selection_rank": item.get("selection_rank"),
                "scanner_fusion_score": round(_num(item.get("scanner_fusion_score")), 4),
                "profit_velocity_score": round(_num(item.get("profit_velocity_score")), 4),
                "fast_money_score": round(_num(item.get("fast_money_score")), 4),
                "cross_reference_count": int(_num(item.get("cross_reference_count"))),
                "orderbook_alignment": item.get("orderbook_alignment"),
                "active_scanners": [str(scanner) for scanner in (item.get("active_scanners") or [])[:8]],
                "blockers": [str(blocker) for blocker in (item.get("blockers") or [])[:6]],
                "usable_for_decision": bool(item.get("usable_for_decision")),
                "gold_related": _gold_related_blob(symbol, item.get("active_scanners")),
            }
        )
    candidates.sort(key=lambda item: (not item["gold_related"], -_num(item.get("scanner_fusion_score")), _num(item.get("selection_rank"), 999)))
    systems = scanner_fusion.get("systems") if isinstance(scanner_fusion.get("systems"), list) else []
    waveform_system = next(
        (
            system
            for system in systems
            if isinstance(system, dict)
            and ("waveform" in str(system.get("facet") or system.get("name") or "").lower())
        ),
        {},
    )
    return {
        "status": scanner_fusion.get("status") or ("scanner_fusion_present" if scanner_fusion else "scanner_fusion_missing"),
        "fresh": bool(scanner_fusion.get("fresh")),
        "fed_to_decision_logic": bool(scanner_fusion.get("fed_to_decision_logic")),
        "candidate_count": len(candidates),
        "gold_candidate_count": sum(1 for item in candidates if item.get("gold_related")),
        "usable_candidate_count": sum(1 for item in candidates if item.get("usable_for_decision")),
        "top_candidates": candidates[:12],
        "waveform_system": {
            "name": waveform_system.get("name"),
            "fresh": bool(waveform_system.get("fresh")),
            "usable_for_decision": bool(waveform_system.get("usable_for_decision")),
            "reason": waveform_system.get("reason"),
            "repo_path": waveform_system.get("repo_path"),
        }
        if waveform_system
        else {},
    }


def _build_historical_signal_lab(
    *,
    asset: Dict[str, Any],
    snapshot_fresh: bool,
    runtime_stale: bool,
    coverage: Dict[str, Any],
    exchange_matrix: Dict[str, Any],
    trading_intel: Dict[str, Any],
    world_ecosystem: Dict[str, Any],
    scanner_fusion: Dict[str, Any],
    shadow_report: Dict[str, Any],
    data_ocean: Dict[str, Any],
    driver_matrix: List[Dict[str, Any]],
) -> Dict[str, Any]:
    coverage_rows = _rows_by_key(coverage, "domain")
    waveform_row = coverage_rows.get("historical_waveform_memory", {})
    capital_history = _capital_price_history_state(exchange_matrix)
    lead_lag_candidates = _extract_lead_lag_candidates(world_ecosystem)
    orderbook = _extract_orderbook_evidence(shadow_report)
    scanner = _extract_scanner_fusion_evidence(scanner_fusion)
    data_ocean_summary = _summary(data_ocean)
    trading_summary = _summary(trading_intel)
    ready_driver_count = sum(1 for item in driver_matrix if item.get("driver_state") == "ready_shadow_driver")

    has_asset = bool(asset)
    price_history_ready = bool(capital_history.get("price_history_available") and has_asset)
    waveform_ready = bool(waveform_row.get("fresh") and waveform_row.get("usable")) or bool((scanner.get("waveform_system") or {}).get("fresh"))
    cross_asset_ready = bool(lead_lag_candidates)
    direct_gold_lead_lag = any(item.get("gold_related") for item in lead_lag_candidates)
    orderbook_ready = orderbook["sample_count"] > 0
    direct_gold_orderbook = orderbook["gold_sample_count"] > 0
    scanner_ready = bool(scanner.get("fresh") and scanner.get("usable_candidate_count"))
    gold_scanner_ready = bool(scanner.get("gold_candidate_count"))

    replay_lanes = [
        {
            "id": "gold_ohlc_replay",
            "label": "Capital GOLD Chart/OHLC Replay",
            "state": _state_from_ready(price_history_ready, attention=runtime_stale or not snapshot_fresh, blocked=not price_history_ready),
            "source": "Capital price_history channel plus Capital GOLD asset registry",
            "source_paths": [str(SOURCE_PATHS["exchange_data_matrix"]), str(SOURCE_PATHS["capital_asset_registry"])],
            "evidence": {
                "price_history_available": capital_history.get("price_history_available"),
                "live_ticks_status": capital_history.get("live_ticks_status"),
                "market_hours_status": capital_history.get("market_hours_status"),
                "snapshot_fresh": snapshot_fresh,
            },
            "why_it_matters": "Aureon needs real GOLD bars before chart claims about support, breakout, reversal, or energy are trusted.",
            "next_action": "Refresh Capital GOLD history and chart bars, then replay 1m/5m/1h/1d moves against cross-market drivers.",
        },
        {
            "id": "cross_asset_lead_lag",
            "label": "Cross-Asset Lead/Lag Map",
            "state": _state_from_ready(cross_asset_ready, attention=not direct_gold_lead_lag, blocked=not cross_asset_ready),
            "source": "World financial ecosystem intelligence mesh",
            "source_paths": [str(SOURCE_PATHS["world_financial_ecosystem"])],
            "evidence": {
                "candidate_count": len(lead_lag_candidates),
                "direct_gold_candidate_count": sum(1 for item in lead_lag_candidates if item.get("gold_related")),
                "fed_to_decision_logic": bool(world_ecosystem.get("fed_to_decision_logic")),
            },
            "why_it_matters": "This shows what tends to move first and what may follow when liquidity, crypto, stocks, FX, or commodities shift.",
            "next_action": "Add direct GOLD/DXY/rates/oil/ETF lead-lag rows; keep crypto rows as liquidity proxy evidence.",
        },
        {
            "id": "orderbook_pressure_replay",
            "label": "Order-Book Pressure Replay",
            "state": _state_from_ready(orderbook_ready, attention=not direct_gold_orderbook, blocked=not orderbook_ready),
            "source": "Unified shadow trade report and order-book probes",
            "source_paths": [str(SOURCE_PATHS["shadow_trade_report"])],
            "evidence": {
                "sample_count": orderbook["sample_count"],
                "available_count": orderbook["available_count"],
                "gold_sample_count": orderbook["gold_sample_count"],
                "source_status": orderbook["source_status"],
            },
            "why_it_matters": "Order-book imbalance can explain fast moves, but GOLD must have direct pressure proof before it affects confidence.",
            "next_action": "Probe Capital/available venue GOLD order-book or quote-depth equivalents, then compare pressure before/after moves.",
        },
        {
            "id": "scanner_fusion_replay",
            "label": "Scanner Fusion Replay",
            "state": _state_from_ready(scanner_ready, attention=not gold_scanner_ready, blocked=not scanner_ready),
            "source": "Scanner fusion matrix with momentum, order-book, waveform, model, and shadow evidence",
            "source_paths": [str(SOURCE_PATHS["scanner_fusion_matrix"])],
            "evidence": {
                "candidate_count": scanner["candidate_count"],
                "usable_candidate_count": scanner["usable_candidate_count"],
                "gold_candidate_count": scanner["gold_candidate_count"],
                "fresh": scanner["fresh"],
            },
            "why_it_matters": "Aureon's existing scanners should find whether GOLD is moving with or against the active market regime.",
            "next_action": "Put GOLD, GLD, GDX, DXY, oil, BTC, VIX, and yields into the scanner fusion candidate set.",
        },
        {
            "id": "historical_waveform_replay",
            "label": "Historical Waveform Replay",
            "state": _state_from_ready(waveform_ready, attention=runtime_stale, blocked=not waveform_ready),
            "source": "Historical waveform memory and MultiHorizonWaveformMemory",
            "source_paths": [str(SOURCE_PATHS["global_financial_coverage"]), str(SOURCE_PATHS["scanner_fusion_matrix"])],
            "evidence": {
                "domain_fresh": bool(waveform_row.get("fresh")),
                "domain_usable": bool(waveform_row.get("usable")),
                "history_count": waveform_row.get("history_count"),
                "waveform_system": scanner.get("waveform_system"),
            },
            "why_it_matters": "This is the repo's memory of how markets behave across 1h-to-1y horizons.",
            "next_action": "Backtest GOLD against its related drivers on the same horizons used by waveform memory.",
        },
        {
            "id": "driver_attribution",
            "label": "Gold Driver Attribution",
            "state": _state_from_ready(ready_driver_count >= 6, attention=ready_driver_count < len(driver_matrix), blocked=not driver_matrix),
            "source": "Cross-market driver matrix",
            "source_paths": ["cross_market_driver_matrix"],
            "evidence": {
                "ready_driver_count": ready_driver_count,
                "driver_count": len(driver_matrix),
                "weak_driver_ids": [str(item.get("id")) for item in driver_matrix if item.get("driver_state") != "ready_shadow_driver"][:8],
            },
            "why_it_matters": "Gold moves for different reasons in different regimes; attribution keeps the thesis from becoming one-note.",
            "next_action": "Strengthen the weak drivers before letting any one explanation dominate the gold map.",
        },
    ]
    ready_count = sum(1 for lane in replay_lanes if lane.get("state") != "blocked_missing_evidence")

    gaps: List[Dict[str, Any]] = []
    if runtime_stale:
        gaps.append(
            {
                "id": "historical_lab_runtime_stale",
                "severity": "high",
                "gap": "Runtime is stale, so replay output is evidence-only and cannot drive live decisions.",
                "next_action": "Restore fresh runtime ticks before any live-use claim.",
            }
        )
    if not snapshot_fresh:
        gaps.append(
            {
                "id": "gold_chart_snapshot_not_fresh",
                "severity": "high",
                "gap": "Capital GOLD snapshot is stale or missing, so the chart replay needs a fresh anchor price.",
                "next_action": "Refresh Capital GOLD quote and OHLC before accepting chart signals.",
            }
        )
    if not direct_gold_lead_lag:
        gaps.append(
            {
                "id": "direct_gold_lead_lag_missing",
                "severity": "medium",
                "gap": "Lead-lag evidence exists only as proxy rows or is missing direct GOLD relationships.",
                "next_action": "Add GOLD versus DXY, yields, oil, GLD/miners, BTC, VIX, and indices lead-lag rows.",
            }
        )
    if not direct_gold_orderbook:
        gaps.append(
            {
                "id": "direct_gold_orderbook_pressure_missing",
                "severity": "medium",
                "gap": "Order-book pressure samples are not yet direct GOLD samples.",
                "next_action": "Collect GOLD quote depth/order pressure or the closest Capital-supported equivalent.",
            }
        )
    for gap in (data_ocean_summary.get("top_gaps") or [])[:4]:
        if isinstance(gap, dict):
            source_id = str(gap.get("source_id") or "")
            if source_id in {"fred_macro", "fmp_calendar", "world_news", "yfinance_history"}:
                gaps.append(
                    {
                        "id": f"data_ocean_{source_id}",
                        "severity": "medium",
                        "gap": str(gap.get("reason") or "data ocean source gap"),
                        "next_action": str(gap.get("next_action") or "Refresh missing data-ocean source."),
                    }
                )

    hypothesis_tests = [
        {
            "id": "gold_vs_dxy_rates_inverse_test",
            "question": "Does GOLD move opposite USD/DXY and real-yield pressure in the current regime?",
            "inputs": ["Capital GOLD OHLC", "DXY/USD", "Treasury yield or rates proxy", "macro calendar"],
            "current_state": "attention" if any(gap["id"].startswith("data_ocean_fred") for gap in gaps) else "mapped",
            "pass_condition": "Directional relationship is measured on matching timestamps with enough bars.",
        },
        {
            "id": "gold_vs_crypto_liquidity_rotation_test",
            "question": "Is crypto liquidity confirming risk-on rotation or contradicting a safe-haven gold move?",
            "inputs": ["BTC/ETH breadth", "crypto live market", "historical waveform memory", "gold bars"],
            "current_state": "proxy_candidates_present" if lead_lag_candidates else "waiting_for_proxy_rows",
            "pass_condition": "Crypto proxy rows are compared against direct GOLD bars and marked confirm/contradict.",
        },
        {
            "id": "gold_etf_miner_confirmation_test",
            "question": "Are GLD/miners/equity-risk instruments confirming the Capital GOLD move?",
            "inputs": ["GLD/GDX/miners", "VIX/indices", "Capital GOLD", "scanner fusion"],
            "current_state": "attention" if not gold_scanner_ready else "mapped",
            "pass_condition": "ETF/miner breadth agrees or a contradiction is explicitly reported.",
        },
        {
            "id": "gold_orderbook_pressure_test",
            "question": "Does quote/order pressure explain the move before price follows?",
            "inputs": ["Capital GOLD quote/depth", "shadow orderbook probes", "scanner fusion"],
            "current_state": orderbook["status"],
            "pass_condition": "Direct GOLD pressure sample exists before confidence is increased.",
        },
        {
            "id": "gold_waveform_regime_replay_test",
            "question": "Is the move normal, stretched, or reversing against multi-horizon waveform memory?",
            "inputs": ["1h-to-1y waveform memory", "Capital GOLD chart", "related drivers"],
            "current_state": "waveform_ready" if waveform_ready else "waveform_gap",
            "pass_condition": "Waveform replay returns stretch/reversal state with source bars.",
        },
    ]

    source_packets = [
        {
            "id": "capital_price_history",
            "source_path": str(SOURCE_PATHS["exchange_data_matrix"]),
            "packet_type": "chart_ohlc_capability",
            "status": "available" if capital_history.get("price_history_available") else "missing",
            "guidance": "Use Capital price_history for GOLD chart replay before chart-language claims.",
        },
        {
            "id": "world_financial_lead_lag",
            "source_path": str(SOURCE_PATHS["world_financial_ecosystem"]),
            "packet_type": "cross_asset_lead_lag",
            "status": "present" if lead_lag_candidates else "missing",
            "guidance": "Use lead-lag rows to map what moves first and whether it is direct GOLD or proxy context.",
        },
        {
            "id": "shadow_orderbook_pressure",
            "source_path": str(SOURCE_PATHS["shadow_trade_report"]),
            "packet_type": "orderbook_pressure",
            "status": orderbook["status"],
            "guidance": "Use order-book pressure only when available and source-linked; proxy rows do not prove GOLD pressure.",
        },
        {
            "id": "scanner_waveform_fusion",
            "source_path": str(SOURCE_PATHS["scanner_fusion_matrix"]),
            "packet_type": "scanner_fusion",
            "status": scanner["status"],
            "guidance": "Use scanner fusion to cross-reference momentum, waveform, model, shadow, and order-book evidence.",
        },
    ]

    return {
        "status": "gold_historical_signal_lab_ready" if ready_count >= 4 and len(gaps) <= 2 else "gold_historical_signal_lab_attention",
        "lane_count": len(replay_lanes),
        "ready_lane_count": ready_count,
        "source_packets": source_packets,
        "replay_lanes": replay_lanes,
        "lead_lag_candidates": lead_lag_candidates,
        "orderbook_evidence": orderbook,
        "scanner_fusion_evidence": scanner,
        "capital_price_history": capital_history,
        "hypothesis_tests": hypothesis_tests,
        "gaps": gaps,
        "chart_replay_state": replay_lanes[0]["state"],
        "lead_lag_state": replay_lanes[1]["state"],
        "orderbook_signal_state": replay_lanes[2]["state"],
        "waveform_replay_state": replay_lanes[4]["state"],
        "data_ocean_runtime_stale": bool(data_ocean_summary.get("runtime_stale")),
        "trading_decision_posture": trading_summary.get("decision_posture"),
    }


def _load_sources(root: Path) -> Dict[str, Dict[str, Any]]:
    sources = {name: _read_json(_rooted(root, rel)) for name, rel in SOURCE_PATHS.items()}
    sources["runtime_status"] = read_runtime_status(root, rel_path=SOURCE_PATHS["runtime_status"])
    return sources


def _source_evidence(root: Path, sources: Dict[str, Dict[str, Any]], now: datetime) -> List[Dict[str, Any]]:
    evidence: List[Dict[str, Any]] = []
    for name, rel in SOURCE_PATHS.items():
        payload = sources.get(name) or {}
        path = _rooted(root, rel)
        generated_at = payload.get("generated_at") or _summary(payload).get("generated_at")
        age = _age_seconds(generated_at, now)
        evidence.append(
            {
                "id": name,
                "path": str(path),
                "present": bool(payload),
                "status": payload.get("status") or _summary(payload).get("status") or ("present" if payload else "missing"),
                "generated_at": generated_at,
                "age_seconds": round(age, 3) if age is not None else None,
                "summary_keys": sorted(_summary(payload).keys())[:12],
            }
        )
    return evidence


def _build_verified_real_data_gate(
    *,
    source_evidence: List[Dict[str, Any]],
    signals: List[Dict[str, Any]],
    asset: Dict[str, Any],
    snapshot_age_sec: Optional[float],
    snapshot_fresh: bool,
    runtime_stale: bool,
    historical_signal_lab: Dict[str, Any],
) -> Dict[str, Any]:
    evidence_by_id = {str(item.get("id")): item for item in source_evidence}
    source_checks: List[Dict[str, Any]] = []
    blockers: List[Dict[str, Any]] = []
    for source_id, max_age in ACTION_SOURCE_FRESHNESS_SECONDS.items():
        evidence = evidence_by_id.get(source_id, {})
        present = bool(evidence.get("present"))
        age = evidence.get("age_seconds")
        age_known = age is not None
        fresh = present and age_known and _num(age) <= max_age
        if source_id == "runtime_status" and runtime_stale:
            fresh = False
        source_checks.append(
            {
                "id": source_id,
                "present": present,
                "generated_at": evidence.get("generated_at"),
                "age_seconds": age,
                "max_age_seconds": max_age,
                "fresh": fresh,
                "data_class": "real_market_or_runtime_evidence",
                "source_status": evidence.get("status"),
            }
        )
        if not present:
            blockers.append({"id": f"{source_id}_missing", "reason": f"{source_id} evidence file is missing."})
        elif not age_known:
            blockers.append({"id": f"{source_id}_timestamp_missing", "reason": f"{source_id} does not publish generated_at timestamp proof."})
        elif not fresh:
            blockers.append({"id": f"{source_id}_not_fresh", "reason": f"{source_id} age {round(_num(age), 1)}s exceeds {max_age}s or runtime stale."})

    if not asset:
        blockers.append({"id": "capital_gold_asset_missing", "reason": "No real Capital GOLD asset is available."})
    if not snapshot_fresh:
        blockers.append({"id": "capital_gold_bid_ask_not_fresh", "reason": f"GOLD bid/ask age is {round(snapshot_age_sec or -1, 1)}s."})
    if runtime_stale:
        blockers.append({"id": "runtime_truth_not_fresh", "reason": "Runtime says data is stale; action metrics cannot unlock."})

    signal_checks: List[Dict[str, Any]] = []
    reference_sources = {"repo gold intelligence surfaces", "global coverage, exchange matrix, trading checklist, repo surfaces"}
    for signal in signals:
        source = str(signal.get("source") or "")
        is_reference = source in reference_sources or source.startswith("repo ") or "surfaces" in source
        data_class = "context_only_reference" if is_reference else "real_market_or_runtime_evidence"
        verified = bool(signal.get("fresh")) and not is_reference
        signal_checks.append(
            {
                "id": signal.get("id"),
                "label": signal.get("label"),
                "source": source,
                "fresh": bool(signal.get("fresh")),
                "data_class": data_class,
                "verified_for_action": verified,
                "action_use": "allowed_if_gate_passes" if verified else "blocked_for_action_context_only",
            }
        )

    shadow_artifact_checks = [
        {
            "id": "gold_priority_forecast_bands",
            "data_class": "shadow_derived_artifact",
            "verified_for_action": False,
            "action_use": "display_only_not_action_authority",
            "reason": "Forecast bands are derived from evidence and never unlock action without fresh source proof.",
        },
        {
            "id": "gold_chart_svg_html",
            "data_class": "visualization_artifact",
            "verified_for_action": False,
            "action_use": "display_only_not_action_authority",
            "reason": "Browser charts explain evidence; they do not create market truth.",
        },
    ]

    direct_gold_orderbook_ready = historical_signal_lab.get("orderbook_signal_state") == "ready_shadow_replay"
    direct_chart_ready = historical_signal_lab.get("chart_replay_state") == "ready_shadow_replay"
    if not direct_gold_orderbook_ready:
        blockers.append({"id": "direct_gold_orderbook_not_verified", "reason": "Direct GOLD order-book/pressure proof is not fresh and verified."})
    if not direct_chart_ready:
        blockers.append({"id": "direct_gold_chart_replay_not_verified", "reason": "Direct GOLD chart/OHLC replay is not fresh and verified."})

    fresh_required_count = sum(1 for item in source_checks if item["fresh"])
    actionable_signal_count = sum(1 for item in signal_checks if item["verified_for_action"])
    unique_blockers: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for blocker in blockers:
        blocker_id = str(blocker.get("id"))
        if blocker_id in seen:
            continue
        seen.add(blocker_id)
        unique_blockers.append(blocker)
    passed = not unique_blockers
    return {
        "status": "verified_real_data_gate_passed" if passed else "verified_real_data_gate_blocking",
        "policy": "No fake, scaffolded, stale, synthetic, reference-only, or visual-only metric can unlock action.",
        "action_allowed_by_data": passed,
        "fresh_required_source_count": fresh_required_count,
        "required_source_count": len(source_checks),
        "actionable_signal_count": actionable_signal_count,
        "signal_count": len(signal_checks),
        "source_checks": source_checks,
        "signal_checks": signal_checks,
        "shadow_artifact_checks": shadow_artifact_checks,
        "blockers": unique_blockers[:20],
        "manual_truth": [
            "Real Capital GOLD bid/ask must be fresh.",
            "Runtime truth must be fresh.",
            "Every action signal must carry source path, timestamp, freshness, and verification class.",
            "Shadow forecast and UI charts are display-only until source proof passes.",
        ],
    }


def _build_gold_ticker_source_mesh(
    *,
    asset: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    source_evidence: List[Dict[str, Any]],
    driver_matrix: List[Dict[str, Any]],
    snapshot_fresh: bool,
    now: datetime,
) -> Dict[str, Any]:
    evidence_by_id = {str(item.get("id")): item for item in source_evidence}
    driver_by_id = {str(item.get("id")): item for item in driver_matrix}
    candidate_blob = json.dumps(candidates, default=str).upper()
    lanes: List[Dict[str, Any]] = []
    blockers: List[Dict[str, Any]] = []
    for spec in GOLD_TICKER_SOURCE_MESH_SPECS:
        evidence = evidence_by_id.get(str(spec["source_id"]), {})
        driver = driver_by_id.get(str(spec["driver_id"]), {})
        age = evidence.get("age_seconds")
        age_known = age is not None
        source_fresh = bool(evidence.get("present") and age_known and _num(age) <= _num(spec["max_age_seconds"]))
        driver_fresh = bool(driver.get("fresh")) if driver else False
        ticker_present = any(str(symbol).upper() in candidate_blob for symbol in spec["symbols"])
        if spec["id"] == "capital_gold_xau":
            ticker_present = bool(asset)
            source_fresh = bool(source_fresh and snapshot_fresh)
        lane_fresh = bool(source_fresh and (driver_fresh or spec["role"] == "target_action_lane" or ticker_present))
        action_influence_allowed = bool(lane_fresh and evidence.get("present") and (driver_fresh or spec["role"] == "target_action_lane"))
        lane = {
            "id": spec["id"],
            "label": spec["label"],
            "symbols": spec["symbols"],
            "venue": spec["venue"],
            "role": spec["role"],
            "source_id": spec["source_id"],
            "driver_id": spec["driver_id"],
            "source_path": evidence.get("path"),
            "generated_at": evidence.get("generated_at"),
            "age_seconds": age,
            "max_age_seconds": spec["max_age_seconds"],
            "source_fresh": source_fresh,
            "driver_fresh": driver_fresh,
            "ticker_present": ticker_present,
            "fresh": lane_fresh,
            "action_influence_allowed": action_influence_allowed,
            "influence_policy": "target_may_influence_action_if_all_gates_pass" if spec["role"] == "target_action_lane" else "context_may_confirm_or_contradict_only_when_fresh",
            "next_action": driver.get("next_action") or "Refresh timestamped ticker/source packet for this lane.",
        }
        lanes.append(lane)
        if not evidence.get("present"):
            blockers.append({"id": f"{spec['id']}_source_missing", "reason": f"{spec['label']} source evidence is missing."})
        elif not age_known:
            blockers.append({"id": f"{spec['id']}_timestamp_missing", "reason": f"{spec['label']} has no timestamp proof."})
        elif not lane_fresh:
            blockers.append({"id": f"{spec['id']}_not_fresh", "reason": f"{spec['label']} age/source/driver proof is not fresh enough for GOLD influence."})

    fresh_count = sum(1 for lane in lanes if lane["fresh"])
    influence_count = sum(1 for lane in lanes if lane["action_influence_allowed"])
    return {
        "status": "gold_ticker_source_mesh_ready" if not blockers else "gold_ticker_source_mesh_attention",
        "generated_at": now.isoformat(),
        "policy": "Capital GOLD is the target; all other tickers are fresh confirmation or contradiction context only.",
        "lane_count": len(lanes),
        "fresh_lane_count": fresh_count,
        "action_influence_lane_count": influence_count,
        "lanes": lanes,
        "blockers": blockers[:16],
    }


def _build_gold_signal_freshness_matrix(
    *,
    source_evidence: List[Dict[str, Any]],
    signals: List[Dict[str, Any]],
    ticker_source_mesh: Dict[str, Any],
    verified_data_gate: Dict[str, Any],
    historical_signal_lab: Dict[str, Any],
    generated_at: str,
) -> Dict[str, Any]:
    source_checks = verified_data_gate.get("source_checks") if isinstance(verified_data_gate.get("source_checks"), list) else []
    source_fresh_by_id = {str(item.get("id")): bool(item.get("fresh")) for item in source_checks if isinstance(item, dict)}
    source_age_by_id = {str(item.get("id")): item.get("age_seconds") for item in source_checks if isinstance(item, dict)}
    evidence_by_path = {str(item.get("path")): item for item in source_evidence}
    rows: List[Dict[str, Any]] = []
    blockers: List[Dict[str, Any]] = []
    mesh_lanes = ticker_source_mesh.get("lanes") if isinstance(ticker_source_mesh.get("lanes"), list) else []
    for lane in mesh_lanes:
        if not isinstance(lane, dict):
            continue
        rows.append(
            {
                "id": f"ticker_{lane.get('id')}",
                "kind": "ticker_source_lane",
                "label": lane.get("label"),
                "symbols": lane.get("symbols"),
                "venue": lane.get("venue"),
                "source_path": lane.get("source_path"),
                "generated_at": lane.get("generated_at"),
                "age_seconds": lane.get("age_seconds"),
                "fresh": bool(lane.get("fresh")),
                "source_linked": bool(lane.get("source_path")),
                "bid_ask_or_ohlc_proof": bool(lane.get("ticker_present") or lane.get("source_fresh")),
                "action_influence_allowed": bool(lane.get("action_influence_allowed")),
                "action_use": lane.get("influence_policy"),
            }
        )
    for signal in signals:
        source = str(signal.get("source") or "")
        evidence = evidence_by_path.get(source, {})
        source_id = str(evidence.get("id") or signal.get("id") or "")
        is_reference = source.startswith("repo ") or "surfaces" in source or source in {"global coverage, exchange matrix, trading checklist, repo surfaces"}
        source_fresh = source_fresh_by_id.get(source_id, bool(signal.get("fresh") and not is_reference))
        action_influence_allowed = bool(signal.get("fresh") and source_fresh and not is_reference)
        rows.append(
            {
                "id": f"signal_{signal.get('id')}",
                "kind": "signal",
                "label": signal.get("label"),
                "symbols": ["GOLD"] if "gold" in str(signal.get("label") or signal.get("id") or "").lower() else [],
                "venue": "mixed",
                "source_path": source,
                "generated_at": evidence.get("generated_at"),
                "age_seconds": source_age_by_id.get(source_id, evidence.get("age_seconds")),
                "fresh": bool(signal.get("fresh")),
                "source_linked": bool(source),
                "bid_ask_or_ohlc_proof": bool(signal.get("id") == "capital_gold_snapshot" or historical_signal_lab.get("chart_replay_state") == "ready_shadow_replay"),
                "action_influence_allowed": action_influence_allowed,
                "action_use": "allowed_if_projection_interval_validates" if action_influence_allowed else "context_or_blocked_until_fresh",
            }
        )

    for row in rows:
        if not row.get("source_linked"):
            blockers.append({"id": f"{row.get('id')}_source_missing", "reason": f"{row.get('label')} has no source path."})
        if not row.get("fresh") and row.get("kind") == "ticker_source_lane":
            blockers.append({"id": f"{row.get('id')}_not_fresh", "reason": f"{row.get('label')} cannot influence GOLD until refreshed."})
        if row.get("action_influence_allowed") and not row.get("bid_ask_or_ohlc_proof"):
            blockers.append({"id": f"{row.get('id')}_price_proof_missing", "reason": f"{row.get('label')} lacks bid/ask/last/OHLC proof."})

    influence_rows = [row for row in rows if row.get("action_influence_allowed")]
    fresh_rows = [row for row in rows if row.get("fresh")]
    return {
        "status": "gold_signal_freshness_matrix_passed" if not blockers and influence_rows else "gold_signal_freshness_matrix_blocking",
        "generated_at": generated_at,
        "policy": "Signals can influence action only when fresh, source-linked, price/bar-backed, and not reference-only.",
        "row_count": len(rows),
        "fresh_row_count": len(fresh_rows),
        "action_influence_row_count": len(influence_rows),
        "rows": rows,
        "blockers": blockers[:24],
        "action_influence_allowed": bool(not blockers and influence_rows and verified_data_gate.get("action_allowed_by_data")),
    }


def _row_interval_id(row: Dict[str, Any]) -> str:
    value = str(row.get("interval") or row.get("horizon") or row.get("window") or row.get("validation_interval") or "").strip().lower()
    aliases = {
        "tick": "tick",
        "t": "tick",
        "second": "1s",
        "1sec": "1s",
        "1s": "1s",
        "5sec": "5s",
        "5s": "5s",
        "15sec": "15s",
        "15s": "15s",
        "30sec": "30s",
        "30s": "30s",
        "1min": "1m",
        "1m": "1m",
        "5min": "5m",
        "5m": "5m",
        "15min": "15m",
        "15m": "15m",
        "1hour": "1h",
        "1hr": "1h",
        "1h": "1h",
        "4hour": "4h",
        "4hr": "4h",
        "4h": "4h",
        "day": "session",
        "daily": "session",
        "session": "session",
        "1day": "1d",
        "1d": "1d",
        "week": "1w",
        "1week": "1w",
        "1w": "1w",
        "month": "1mo",
        "1month": "1mo",
        "1mo": "1mo",
        "1mth": "1mo",
        "3month": "3mo",
        "3months": "3mo",
        "3mo": "3mo",
        "3mth": "3mo",
    }
    return aliases.get(value, value)


def _build_gold_projection_interval_validation(
    *,
    cognitive_route: Dict[str, Any],
    gold_priority_workbench: Dict[str, Any],
    ticker_source_mesh: Dict[str, Any],
    signal_freshness_matrix: Dict[str, Any],
    generated_at: str,
    now: datetime,
) -> Dict[str, Any]:
    probability = cognitive_route.get("probability_systems") if isinstance(cognitive_route.get("probability_systems"), dict) else {}
    gold_rows = probability.get("gold_probability_rows") if isinstance(probability.get("gold_probability_rows"), list) else []
    forecast_points = gold_priority_workbench.get("forecast_points") if isinstance(gold_priority_workbench.get("forecast_points"), list) else []
    forecast_by_horizon = {str(point.get("horizon")).lower(): point for point in forecast_points if isinstance(point, dict)}
    mesh_symbols: List[str] = []
    for lane in ticker_source_mesh.get("lanes", []):
        if isinstance(lane, dict):
            mesh_symbols.extend(str(symbol) for symbol in lane.get("symbols", []) if symbol)
    rows_by_interval: Dict[str, Dict[str, Any]] = {}
    for row in gold_rows:
        if not isinstance(row, dict):
            continue
        interval_id = _row_interval_id(row)
        if interval_id and interval_id not in rows_by_interval:
            rows_by_interval[interval_id] = row

    intervals: List[Dict[str, Any]] = []
    blockers: List[Dict[str, Any]] = []
    total_shadow_pl = 0.0
    for spec in GOLD_INTERVAL_VALIDATION_WINDOWS:
        interval_id = spec["id"]
        row = rows_by_interval.get(interval_id, {})
        timestamp = row.get("timestamp")
        parsed = _parse_time(timestamp)
        deadline = (parsed.timestamp() + _num(spec["seconds"])) if parsed else None
        validated = bool(row.get("validated"))
        hit = bool(row.get("direction_correct") or _num(row.get("outcome_score")) > 0)
        outcome_score = _num(row.get("outcome_score"))
        confidence = _num(row.get("confidence") or row.get("predicted_confidence"))
        shadow_pl = _num(row.get("shadow_p_l_effect"), outcome_score * 0.01)
        total_shadow_pl += shadow_pl if validated else 0.0
        forecast_point = forecast_by_horizon.get(interval_id, {})
        interval = {
            "id": interval_id,
            "label": spec["label"],
            "window_seconds": spec["seconds"],
            "forecast_direction": row.get("direction") or row.get("predicted_direction") or row.get("predicted_action"),
            "forecast_level": row.get("forecast_level") or row.get("target_price") or row.get("price") or forecast_point.get("shadow_mid"),
            "source_tickers": row.get("source_tickers") or row.get("symbols") or ([row.get("symbol")] if row.get("symbol") else mesh_symbols[:8]),
            "source_packet": row.get("source") or "probability_systems",
            "prediction_timestamp": timestamp,
            "validation_deadline": datetime.fromtimestamp(deadline, tz=timezone.utc).isoformat() if deadline else None,
            "observed_outcome": row.get("actual_direction") or row.get("observed_outcome") or row.get("outcome"),
            "hit_miss": "hit" if validated and hit else "miss" if validated else "unvalidated",
            "validated": validated,
            "confidence_delta": round((confidence * 0.1) if hit else (-confidence * 0.1 if validated else 0.0), 5),
            "shadow_p_l_effect": round(shadow_pl, 5) if validated else 0.0,
            "action_influence_allowed": bool(validated and hit and signal_freshness_matrix.get("action_influence_allowed")),
        }
        intervals.append(interval)
        if not row:
            blockers.append({"id": f"{interval_id}_projection_missing", "reason": f"No GOLD projection row exists for {spec['label']} validation."})
        elif not validated:
            blockers.append({"id": f"{interval_id}_projection_unvalidated", "reason": f"{spec['label']} GOLD projection has no outcome validation."})

    validated_count = sum(1 for item in intervals if item["validated"])
    hit_count = sum(1 for item in intervals if item["hit_miss"] == "hit")
    hit_rate = hit_count / validated_count if validated_count else 0.0
    if validated_count < len(GOLD_INTERVAL_VALIDATION_WINDOWS):
        blockers.append({"id": "interval_validation_incomplete", "reason": f"{validated_count}/{len(GOLD_INTERVAL_VALIDATION_WINDOWS)} GOLD intervals are outcome-validated."})
    if hit_rate < 0.55:
        blockers.append({"id": "interval_hit_rate_below_floor", "reason": f"Interval hit rate {round(hit_rate, 4)} is below 0.55."})
    if not signal_freshness_matrix.get("action_influence_allowed"):
        blockers.append({"id": "fresh_signal_matrix_blocking", "reason": "Projection intervals cannot influence action while fresh signal matrix is blocking."})

    validation_passed = not blockers
    return {
        "status": "gold_projection_interval_validation_passed" if validation_passed else "gold_projection_interval_validation_blocking",
        "generated_at": generated_at,
        "policy": "Every GOLD projection must validate on tick, 1m, 5m, 15m, 1h, and session windows before action influence.",
        "required_interval_count": len(GOLD_INTERVAL_VALIDATION_WINDOWS),
        "validated_interval_count": validated_count,
        "hit_count": hit_count,
        "hit_rate": round(hit_rate, 4) if validated_count else None,
        "total_shadow_p_l_effect": round(total_shadow_pl, 5),
        "action_influence_allowed": validation_passed,
        "intervals": intervals,
        "blockers": blockers[:16],
    }


def _build_gold_evolving_projection_path(
    *,
    cognitive_route: Dict[str, Any],
    gold_priority_workbench: Dict[str, Any],
    ticker_source_mesh: Dict[str, Any],
    signal_freshness_matrix: Dict[str, Any],
    projection_interval_validation: Dict[str, Any],
    generated_at: str,
    now: datetime,
) -> Dict[str, Any]:
    probability = cognitive_route.get("probability_systems") if isinstance(cognitive_route.get("probability_systems"), dict) else {}
    gold_rows = probability.get("gold_probability_rows") if isinstance(probability.get("gold_probability_rows"), list) else []
    forecast_points = gold_priority_workbench.get("forecast_points") if isinstance(gold_priority_workbench.get("forecast_points"), list) else []
    forecast_by_horizon = {str(point.get("horizon")).lower(): point for point in forecast_points if isinstance(point, dict)}
    rows_by_interval: Dict[str, Dict[str, Any]] = {}
    for row in gold_rows:
        if not isinstance(row, dict):
            continue
        interval_id = _row_interval_id(row)
        if interval_id and interval_id not in rows_by_interval:
            rows_by_interval[interval_id] = row

    horizons: List[Dict[str, Any]] = []
    blockers: List[Dict[str, Any]] = []
    band_counts: Dict[str, Dict[str, int]] = {}
    for spec in GOLD_EVOLVING_PROJECTION_HORIZONS:
        horizon_id = spec["id"]
        band = str(spec["band"])
        band_counts.setdefault(band, {"total": 0, "fresh": 0, "validated": 0, "hit": 0})
        band_counts[band]["total"] += 1
        row = rows_by_interval.get(horizon_id, {})
        timestamp = row.get("timestamp")
        age = _age_seconds(timestamp, now)
        input_fresh = bool(age is not None and age <= _num(spec["max_input_age_seconds"]))
        parsed = _parse_time(timestamp)
        deadline = (parsed.timestamp() + _num(spec["seconds"])) if parsed else None
        deadline_reached = bool(deadline is not None and now.timestamp() >= deadline)
        validated = bool(row.get("validated"))
        hit = bool(row.get("direction_correct") or _num(row.get("outcome_score")) > 0)
        confidence = _num(row.get("confidence") or row.get("predicted_confidence"))
        forecast_point = forecast_by_horizon.get(horizon_id) or forecast_by_horizon.get("now" if horizon_id in {"1s", "5s", "15s", "30s", "tick"} else horizon_id, {})
        if not row:
            validation_state = "missing_projection"
            next_action = f"create_{horizon_id}_gold_projection_from_fresh_tick"
            blockers.append({"id": f"{horizon_id}_projection_missing", "reason": f"{spec['label']} has no live GOLD projection row."})
        elif not input_fresh:
            validation_state = "stale_input"
            next_action = f"refresh_{horizon_id}_gold_input"
            blockers.append({"id": f"{horizon_id}_projection_stale", "reason": f"{spec['label']} input age {round(age or -1, 3)}s exceeds {spec['max_input_age_seconds']}s."})
        elif validated and hit:
            validation_state = "validated_hit"
            next_action = f"roll_forward_{horizon_id}_projection"
            band_counts[band]["validated"] += 1
            band_counts[band]["hit"] += 1
        elif validated:
            validation_state = "validated_miss"
            next_action = f"lower_confidence_and_retrain_{horizon_id}"
            band_counts[band]["validated"] += 1
            blockers.append({"id": f"{horizon_id}_projection_miss", "reason": f"{spec['label']} was validated but missed."})
        elif deadline_reached:
            validation_state = "deadline_reached_needs_outcome"
            next_action = f"validate_{horizon_id}_outcome_now"
            blockers.append({"id": f"{horizon_id}_deadline_unvalidated", "reason": f"{spec['label']} validation deadline has passed without outcome proof."})
        else:
            validation_state = "awaiting_live_outcome"
            next_action = f"wait_until_{horizon_id}_deadline_then_validate"
        if input_fresh:
            band_counts[band]["fresh"] += 1
        horizons.append(
            {
                "id": horizon_id,
                "label": spec["label"],
                "band": band,
                "window_seconds": spec["seconds"],
                "max_input_age_seconds": spec["max_input_age_seconds"],
                "prediction_timestamp": timestamp,
                "input_age_seconds": round(age, 3) if age is not None else None,
                "input_fresh": input_fresh,
                "forecast_direction": row.get("direction") or row.get("predicted_direction") or row.get("predicted_action"),
                "forecast_level": row.get("forecast_level") or row.get("target_price") or row.get("price") or forecast_point.get("shadow_mid"),
                "source_tickers": row.get("source_tickers") or row.get("symbols") or [],
                "probability": row.get("probability"),
                "confidence": round(confidence, 4),
                "validation_deadline": datetime.fromtimestamp(deadline, tz=timezone.utc).isoformat() if deadline else None,
                "deadline_reached": deadline_reached,
                "validated": validated,
                "hit_miss": "hit" if validated and hit else "miss" if validated else "unvalidated",
                "validation_state": validation_state,
                "confidence_delta": round((confidence * 0.1) if hit else (-confidence * 0.1 if validated else 0.0), 5),
                "shadow_p_l_effect": round(_num(row.get("shadow_p_l_effect")), 5) if validated else 0.0,
                "next_action": next_action,
            }
        )

    fresh_horizon_count = sum(1 for item in horizons if item.get("input_fresh"))
    validated_horizon_count = sum(1 for item in horizons if item.get("validated"))
    hit_count = sum(1 for item in horizons if item.get("hit_miss") == "hit")
    hit_rate = hit_count / validated_horizon_count if validated_horizon_count else 0.0
    short_ready = all(
        any(item["id"] == horizon_id and item.get("input_fresh") for item in horizons)
        for horizon_id in ("1s", "5s", "15s", "30s")
    )
    core_validated = bool(projection_interval_validation.get("action_influence_allowed"))
    live_evolving_ready = bool(
        short_ready
        and core_validated
        and signal_freshness_matrix.get("action_influence_allowed")
        and hit_rate >= 0.55
        and validated_horizon_count >= len(GOLD_INTERVAL_VALIDATION_WINDOWS)
    )
    if not short_ready:
        blockers.append({"id": "second_level_path_not_fresh", "reason": "1s/5s/15s/30s GOLD projections are not all fresh."})
    if not core_validated:
        blockers.append({"id": "core_interval_validation_blocking", "reason": "Core tick/1m/5m/15m/1h/session validation has not passed."})

    return {
        "status": "gold_evolving_projection_path_live_validating" if live_evolving_ready and not blockers else "gold_evolving_projection_path_attention",
        "generated_at": generated_at,
        "mode": "rolling_second_to_month_projection_validation",
        "policy": "Every GOLD projection horizon from seconds to months must use fresh input, publish a validation deadline, record hit/miss outcomes, and roll forward continuously.",
        "live_evolving_ready": bool(live_evolving_ready and not blockers),
        "horizon_count": len(horizons),
        "fresh_horizon_count": fresh_horizon_count,
        "validated_horizon_count": validated_horizon_count,
        "hit_count": hit_count,
        "hit_rate": round(hit_rate, 4) if validated_horizon_count else None,
        "band_counts": band_counts,
        "horizons": horizons,
        "next_roll_forward_action": next((item["next_action"] for item in horizons if item.get("validation_state") != "validated_hit"), "roll_forward_all_horizons"),
        "action_influence_allowed": bool(live_evolving_ready and not blockers),
        "blockers": blockers[:24],
        "manual_boundaries": [
            "This path evolves forecasts and validation evidence only.",
            "Seconds-to-months validation does not bypass the GOLD process flow guard.",
            "Live orders remain outside this report even when all horizons validate.",
        ],
    }


def _build_gold_dynamic_market_edge_stream(
    *,
    asset: Dict[str, Any],
    ticker_source_mesh: Dict[str, Any],
    signal_freshness_matrix: Dict[str, Any],
    projection_interval_validation: Dict[str, Any],
    evolving_projection_path: Dict[str, Any],
    probability_projection_forecast: Dict[str, Any],
    hnc_action_coherence_gate: Dict[str, Any],
    portfolio_uplift_guard: Dict[str, Any],
    historical_signal_lab: Dict[str, Any],
    cross_market_driver_matrix: List[Dict[str, Any]],
    generated_at: str,
) -> Dict[str, Any]:
    lanes = ticker_source_mesh.get("lanes") if isinstance(ticker_source_mesh.get("lanes"), list) else []
    drivers_by_id = {str(driver.get("id")): driver for driver in cross_market_driver_matrix if isinstance(driver, dict)}
    forecast = probability_projection_forecast.get("forecast_distribution") if isinstance(probability_projection_forecast.get("forecast_distribution"), dict) else {}
    validated_forecast = probability_projection_forecast.get("validated_forecast") if isinstance(probability_projection_forecast.get("validated_forecast"), dict) else {}
    truth = probability_projection_forecast.get("truth_discipline") if isinstance(probability_projection_forecast.get("truth_discipline"), dict) else {}
    side = _side_from_projection(forecast.get("calibrated_direction") or validated_forecast.get("direction"))
    if side not in {"BUY", "SELL"}:
        side = "HOLD"

    waveform_state = str(historical_signal_lab.get("waveform_replay_state") or "waveform_waiting")
    chart_state = str(historical_signal_lab.get("chart_replay_state") or "chart_waiting")
    orderbook_state = str(historical_signal_lab.get("orderbook_signal_state") or "orderbook_waiting")
    waveform_ready = waveform_state in {"ready_shadow_replay", "waveform_ready", "ready"}
    chart_ready = chart_state in {"ready_shadow_replay", "ready"}
    pressure_ready = orderbook_state in {"ready_shadow_replay", "ready", "attention_mapped_not_proven"}
    auris_coherence = _num(hnc_action_coherence_gate.get("auris_coherence"))
    target_lane_fresh = False
    stream_rows: List[Dict[str, Any]] = []
    for lane in lanes:
        if not isinstance(lane, dict):
            continue
        driver = drivers_by_id.get(str(lane.get("driver_id")), {})
        age = lane.get("age_seconds")
        max_age = _num(lane.get("max_age_seconds"), 1.0) or 1.0
        age_ratio = _clamp(1.0 - (_num(age) / max_age)) if age is not None else 0.0
        driver_ready = str(driver.get("driver_state") or "") == "ready_shadow_driver"
        lane_fresh = bool(lane.get("fresh"))
        if lane.get("id") == "capital_gold_xau":
            target_lane_fresh = lane_fresh
        role_weight = 1.25 if lane.get("role") == "target_action_lane" else 0.75
        lane_edge_score = _clamp(
            (0.45 if lane_fresh else 0.0)
            + (0.2 if driver_ready else 0.0)
            + age_ratio * 0.2
            + (0.1 if lane.get("ticker_present") else 0.0)
            + (0.05 if lane.get("action_influence_allowed") else 0.0)
        )
        stream_state = "streaming_edge_watch" if lane_fresh else "refresh_required"
        stream_rows.append(
            {
                "id": lane.get("id"),
                "label": lane.get("label"),
                "symbols": lane.get("symbols") or [],
                "venue": lane.get("venue"),
                "role": lane.get("role"),
                "source_path": lane.get("source_path"),
                "age_seconds": age,
                "max_age_seconds": lane.get("max_age_seconds"),
                "stream_state": stream_state,
                "fresh": lane_fresh,
                "driver_state": driver.get("driver_state"),
                "edge_score": round(_clamp(lane_edge_score * role_weight), 4),
                "edge_use": "target_trigger" if lane.get("role") == "target_action_lane" else "confirmation_or_contradiction",
                "next_action": lane.get("next_action") or "Refresh timestamped market packet.",
            }
        )

    fresh_stream_count = sum(1 for row in stream_rows if row.get("fresh"))
    target_row = next((row for row in stream_rows if row.get("role") == "target_action_lane"), {})
    context_fresh_count = sum(1 for row in stream_rows if row.get("role") != "target_action_lane" and row.get("fresh"))
    edge_score = _clamp(
        (_num(ticker_source_mesh.get("fresh_lane_count")) / max(1.0, _num(ticker_source_mesh.get("lane_count"), 1.0))) * 0.2
        + (_num(signal_freshness_matrix.get("action_influence_row_count")) / max(1.0, _num(signal_freshness_matrix.get("row_count"), 1.0))) * 0.15
        + (_num(evolving_projection_path.get("fresh_horizon_count")) / max(1.0, _num(evolving_projection_path.get("horizon_count"), 1.0))) * 0.12
        + (_num(evolving_projection_path.get("validated_horizon_count")) / max(1.0, _num(evolving_projection_path.get("horizon_count"), 1.0))) * 0.12
        + _num(forecast.get("calibrated_confidence")) * 0.16
        + auris_coherence * 0.1
        + (0.08 if waveform_ready else 0.0)
        + (0.04 if chart_ready else 0.0)
        + (0.03 if pressure_ready else 0.0)
    )
    blockers: List[Dict[str, Any]] = []
    if not target_lane_fresh:
        blockers.append({"id": "capital_gold_stream_not_fresh", "reason": "Capital GOLD target stream/profile is not fresh enough for edge timing."})
    if context_fresh_count < 2:
        blockers.append({"id": "context_stream_confluence_low", "reason": f"Only {context_fresh_count} related market context stream(s) are fresh."})
    if not waveform_ready:
        blockers.append({"id": "waveform_replay_not_ready", "reason": f"Waveform replay state is {waveform_state}."})
    if not signal_freshness_matrix.get("action_influence_allowed"):
        blockers.append({"id": "fresh_signal_matrix_blocking", "reason": "Dynamic edge stream cannot trigger while fresh signal matrix is blocking."})
    if not projection_interval_validation.get("action_influence_allowed"):
        blockers.append({"id": "interval_validation_blocking", "reason": "Dynamic edge stream cannot trigger until projection intervals validate."})
    if not evolving_projection_path.get("live_evolving_ready"):
        blockers.append({"id": "evolving_projection_path_blocking", "reason": "Second-to-month projection path is not live-validating."})
    if not truth.get("truth_claim_allowed"):
        blockers.append({"id": "probability_truth_blocking", "reason": "Probability forecast is not allowed to make a live truth claim."})
    if not hnc_action_coherence_gate.get("action_coherence_allowed"):
        blockers.append({"id": "hnc_auris_holding_confidence", "reason": "HNC/Auris is lowering or holding confidence."})
    if not portfolio_uplift_guard.get("order_intent_consideration_allowed"):
        blockers.append({"id": "portfolio_uplift_guard_blocking", "reason": "3p floor, spread, slippage, fee, or risk proof is not passing."})

    shadow_edge_ready = bool(side in {"BUY", "SELL"} and edge_score >= 0.72 and not blockers)
    edge_state = "gold_dynamic_market_edge_shadow_ready" if shadow_edge_ready else "gold_dynamic_market_edge_watch_refreshing"
    next_action = "shadow_validate_gold_margin_edge_without_live_order" if shadow_edge_ready else "refresh_capital_gold_stream_and_context_edges"
    if blockers:
        first_blocker = str(blockers[0].get("id") or "")
        next_action = f"repair_{first_blocker}"
    return {
        "status": "gold_dynamic_market_edge_stream_ready" if shadow_edge_ready else "gold_dynamic_market_edge_stream_attention",
        "generated_at": generated_at,
        "mode": "dynamic_streaming_gold_edge_watch_shadow_only",
        "policy": "Continuously watch Capital GOLD and related tickers for waveform edge movement; publish shadow intent only after fresh data, interval validation, HNC/Auris, and portfolio gates pass.",
        "edge_state": edge_state,
        "stream_lane_count": len(stream_rows),
        "fresh_stream_count": fresh_stream_count,
        "context_fresh_count": context_fresh_count,
        "target_stream_fresh": target_lane_fresh,
        "edge_score": round(edge_score, 4),
        "waveform_state": waveform_state,
        "chart_state": chart_state,
        "orderbook_pressure_state": orderbook_state,
        "stream_rows": stream_rows,
        "edge_trigger_map": {
            "target": target_row,
            "side": side,
            "calibrated_confidence": forecast.get("calibrated_confidence"),
            "evolving_path_ready": bool(evolving_projection_path.get("live_evolving_ready")),
            "fresh_horizons": evolving_projection_path.get("fresh_horizon_count"),
            "validated_horizons": evolving_projection_path.get("validated_horizon_count"),
            "auris_coherence": hnc_action_coherence_gate.get("auris_coherence"),
            "portfolio_uplift_ready": bool(portfolio_uplift_guard.get("order_intent_consideration_allowed")),
        },
        "action_candidate": {
            "candidate": asset.get("symbol") or "GOLD",
            "venue": "Capital.com",
            "side": side,
            "state": "shadow_edge_candidate_ready" if shadow_edge_ready else "held_for_fresh_edge_proof",
            "edge_score": round(edge_score, 4),
            "trigger_reason": "Fresh waveform edge with validated projection path" if shadow_edge_ready else "Waiting for fresh waveform/projection/portfolio proof.",
            "shadow_intent_allowed": shadow_edge_ready,
            "live_order_allowed": False,
            "margin_order_allowed": False,
            "order_mutation_allowed": False,
        },
        "next_action": next_action,
        "blockers": blockers[:20],
        "manual_boundaries": [
            "Dynamic streaming can decide what to shadow-validate, not place live trades.",
            "Capital margin order mutation remains outside this report.",
            "A waveform edge is ignored unless fresh source proof and interval validation agree.",
        ],
    }


def _build_gold_hnc_history_future_bridge(
    *,
    cognitive_route: Dict[str, Any],
    historical_signal_lab: Dict[str, Any],
    historical_stress_test: Dict[str, Any],
    evolving_projection_path: Dict[str, Any],
    dynamic_market_edge_stream: Dict[str, Any],
    probability_projection_forecast: Dict[str, Any],
    hnc_action_coherence_gate: Dict[str, Any],
    generated_at: str,
) -> Dict[str, Any]:
    replay_lanes = historical_signal_lab.get("replay_lanes") if isinstance(historical_signal_lab.get("replay_lanes"), list) else []
    hypothesis_tests = historical_signal_lab.get("hypothesis_tests") if isinstance(historical_signal_lab.get("hypothesis_tests"), list) else []
    prediction_validation = historical_stress_test.get("prediction_validation") if isinstance(historical_stress_test.get("prediction_validation"), dict) else {}
    horizons = evolving_projection_path.get("horizons") if isinstance(evolving_projection_path.get("horizons"), list) else []
    edge_candidate = dynamic_market_edge_stream.get("action_candidate") if isinstance(dynamic_market_edge_stream.get("action_candidate"), dict) else {}
    forecast_distribution = probability_projection_forecast.get("forecast_distribution") if isinstance(probability_projection_forecast.get("forecast_distribution"), dict) else {}
    ready_lanes = [lane for lane in replay_lanes if str(lane.get("state") or "") != "blocked_missing_evidence"]
    passed_tests = [
        test
        for test in hypothesis_tests
        if str(test.get("current_state") or "").lower()
        in {"mapped", "waveform_ready", "proxy_candidates_present", "ready", "passed"}
    ]
    validated_count = int(_num(prediction_validation.get("validated_count")))
    hit_rate = prediction_validation.get("hit_rate")
    hit_rate_number = _num(hit_rate, 0.0) if hit_rate is not None else 0.0
    auris = cognitive_route.get("auris_nodes") if isinstance(cognitive_route.get("auris_nodes"), dict) else {}
    auris_coherence = _num(auris.get("coherence"))
    historical_memory_score = _clamp(
        (len(ready_lanes) / max(1.0, len(replay_lanes))) * 0.24
        + (len(passed_tests) / max(1.0, len(hypothesis_tests))) * 0.16
        + (min(validated_count, 6) / 6.0) * 0.18
        + hit_rate_number * 0.18
        + auris_coherence * 0.12
        + _num(dynamic_market_edge_stream.get("edge_score")) * 0.12
    )
    future_windows = [
        {
            "id": horizon.get("id"),
            "label": horizon.get("label"),
            "band": horizon.get("band"),
            "history_use": "future_window_from_validated_history",
            "validation_state": horizon.get("validation_state"),
            "forecast_direction": horizon.get("forecast_direction"),
            "validation_deadline": horizon.get("validation_deadline"),
            "ready": bool(horizon.get("input_fresh") and horizon.get("validated")),
            "next_action": horizon.get("next_action"),
        }
        for horizon in horizons
    ]
    historical_analogs = [
        {
            "id": lane.get("id"),
            "label": lane.get("label"),
            "state": lane.get("state"),
            "source": lane.get("source"),
            "future_use": "map_history_to_gold_move_timing" if str(lane.get("state") or "") != "blocked_missing_evidence" else "blocked_until_replayable",
            "why_it_matters": lane.get("why_it_matters"),
            "next_action": lane.get("next_action"),
        }
        for lane in replay_lanes
    ]
    blockers: List[Dict[str, Any]] = []
    if not historical_stress_test.get("stress_passed"):
        blockers.append({"id": "historical_stress_not_passing", "reason": "Historical replay has not passed the stress gate."})
    if not cognitive_route.get("route_passed"):
        blockers.append({"id": "hnc_route_not_passing", "reason": "HNC/Auris/lambda/quantum/probability route is not passing."})
    if not hnc_action_coherence_gate.get("action_coherence_allowed"):
        blockers.append({"id": "hnc_action_coherence_holding", "reason": "HNC/Auris is holding confidence because fresh proof or interval validation is blocking."})
    if not evolving_projection_path.get("live_evolving_ready"):
        blockers.append({"id": "future_projection_path_not_live", "reason": "Seconds-to-months projection path is not live-validating."})
    if not edge_candidate.get("shadow_intent_allowed"):
        blockers.append({"id": "dynamic_edge_not_shadow_ready", "reason": "Dynamic GOLD edge stream has not produced a shadow-ready edge."})
    if str(historical_signal_lab.get("status") or "").endswith("attention"):
        blockers.append({"id": "historical_signal_lab_attention", "reason": "Historical signal lab still has replay or data gaps."})

    bridge_ready = not blockers
    return {
        "status": "gold_hnc_history_future_bridge_ready" if bridge_ready else "gold_hnc_history_future_bridge_attention",
        "generated_at": generated_at,
        "mode": "history_to_future_hnc_shadow_bridge",
        "policy": "History may shape GOLD future hypotheses through HNC/Auris only when replay rows, source lanes, projection windows, and dynamic edge proof are fresh and validated.",
        "bridge_ready": bridge_ready,
        "historical_memory_score": round(historical_memory_score, 4),
        "validated_history_count": validated_count,
        "historical_hit_rate": round(hit_rate_number, 4) if hit_rate is not None else None,
        "ready_replay_lane_count": len(ready_lanes),
        "replay_lane_count": len(replay_lanes),
        "passed_hypothesis_count": len(passed_tests),
        "hypothesis_count": len(hypothesis_tests),
        "auris_coherence": auris.get("coherence"),
        "hnc_confidence_effect": hnc_action_coherence_gate.get("confidence_effect"),
        "dynamic_edge_score": dynamic_market_edge_stream.get("edge_score"),
        "future_side": edge_candidate.get("side") or forecast_distribution.get("calibrated_direction") or "HOLD",
        "future_claim_state": "history_backed_shadow_future" if bridge_ready else "history_informs_but_does_not_unlock_action",
        "historical_analogs": historical_analogs,
        "future_windows": future_windows,
        "hnc_compile_packet": {
            "who": "HNC/Auris historical future bridge",
            "what": "Translate validated GOLD history into future windows without fake certainty.",
            "where": ["historical_signal_lab", "gold_historical_stress_test", "gold_evolving_projection_path", "gold_dynamic_market_edge_stream", "gold_hnc_action_coherence_gate"],
            "when": generated_at,
            "how": "Compare replay lanes, validated prediction rows, waveform state, Auris coherence, and dynamic edge score; blockers lower confidence.",
            "act": "shadow_future_ready" if bridge_ready else "hold_history_as_context",
        },
        "action_influence_allowed": bridge_ready,
        "live_order_allowed": False,
        "margin_order_allowed": False,
        "order_mutation_allowed": False,
        "blockers": blockers[:16],
        "manual_boundaries": [
            "History informs future hypotheses; it is not certainty or financial advice.",
            "This bridge cannot place trades or change margin.",
            "Fresh real data and existing runtime/risk gates remain authoritative.",
        ],
    }


def _build_gold_creative_dream_hypothesis_engine(
    *,
    cross_market_driver_matrix: List[Dict[str, Any]],
    historical_signal_lab: Dict[str, Any],
    dynamic_market_edge_stream: Dict[str, Any],
    hnc_history_future_bridge: Dict[str, Any],
    probability_projection_forecast: Dict[str, Any],
    local_research_packets: List[Dict[str, Any]],
    swarm_intelligence: Dict[str, Any],
    generated_at: str,
) -> Dict[str, Any]:
    ready_driver_ids = {
        str(driver.get("id"))
        for driver in cross_market_driver_matrix
        if driver.get("driver_state") == "ready_shadow_driver"
    }
    source_paths = [
        str(packet.get("path"))
        for packet in local_research_packets
        if packet.get("path") and packet.get("matched_terms")
    ][:8]
    active_agents = [
        agent
        for agent in (swarm_intelligence.get("agents") or [])
        if agent.get("state") == "active"
    ]
    replay_lanes = historical_signal_lab.get("replay_lanes") if isinstance(historical_signal_lab.get("replay_lanes"), list) else []
    ready_replay_count = sum(1 for lane in replay_lanes if str(lane.get("state") or "") != "blocked_missing_evidence")
    edge_score = _num(dynamic_market_edge_stream.get("edge_score"))
    memory_score = _num(hnc_history_future_bridge.get("historical_memory_score"))
    forecast_distribution = probability_projection_forecast.get("forecast_distribution") if isinstance(probability_projection_forecast.get("forecast_distribution"), dict) else {}
    forecast_confidence = _num(forecast_distribution.get("calibrated_confidence"))
    templates = [
        {
            "id": "gold_liquidity_snap",
            "title": "GOLD liquidity snap dream",
            "imagination_lane": "microstructure",
            "premise": "A sudden GOLD bid/ask pressure shift may appear before the broader driver mesh agrees.",
            "driver_ids": ["capital_gold_xau", "orderbook_pressure", "scanner_fusion"],
        },
        {
            "id": "usd_real_yield_release",
            "title": "USD real-yield release dream",
            "imagination_lane": "macro",
            "premise": "Gold may wake up when DXY or rates pressure relaxes before miners confirm.",
            "driver_ids": ["usd_dxy", "rates_yields", "macro_calendar"],
        },
        {
            "id": "oil_energy_inflation_heat",
            "title": "Oil-energy inflation heat dream",
            "imagination_lane": "energy",
            "premise": "Oil and energy stress can pull inflation expectations toward a GOLD demand impulse.",
            "driver_ids": ["oil_energy", "macro_calendar", "world_financial_ecosystem"],
        },
        {
            "id": "miner_confirmation_lag",
            "title": "Miner confirmation lag dream",
            "imagination_lane": "equity_proxy",
            "premise": "GLD, GDX, and miners may lag the metal; the lag itself can become confirmation.",
            "driver_ids": ["gold_etfs", "miners", "equity_indices"],
        },
        {
            "id": "waveform_stretch_reversal",
            "title": "Waveform stretch reversal dream",
            "imagination_lane": "waveform",
            "premise": "A stretched GOLD waveform can reverse when history analogs and current edge pressure disagree.",
            "driver_ids": ["historical_waveform_replay", "market_harp", "capital_gold_xau"],
        },
        {
            "id": "order_pressure_front_run",
            "title": "Order pressure front-run dream",
            "imagination_lane": "timing",
            "premise": "Short-lived pressure in direct GOLD or proxy order books may lead the chart by seconds.",
            "driver_ids": ["orderbook_pressure", "capital_gold_xau", "live_stream_cache"],
        },
        {
            "id": "geopolitical_spark",
            "title": "Geopolitical spark dream",
            "imagination_lane": "news_context",
            "premise": "Risk-off headlines can move GOLD before the macro packet is fully refreshed.",
            "driver_ids": ["geopolitical_news", "vix_risk", "macro_calendar"],
        },
        {
            "id": "crypto_safe_haven_conflict",
            "title": "Crypto safe-haven conflict dream",
            "imagination_lane": "liquidity_proxy",
            "premise": "BTC/ETH liquidity may confirm or contradict the same risk story GOLD is telling.",
            "driver_ids": ["crypto_liquidity", "usd_dxy", "vix_risk"],
        },
        {
            "id": "session_breakout_memory",
            "title": "Session breakout memory dream",
            "imagination_lane": "session_memory",
            "premise": "Prior session breakout/reversion patterns may shape what the next London/New York impulse attempts.",
            "driver_ids": ["session_replay", "historical_waveform_replay", "capital_gold_xau"],
        },
        {
            "id": "hnc_coherence_alignment",
            "title": "HNC coherence alignment dream",
            "imagination_lane": "hnc_auris",
            "premise": "Auris coherence may highlight when many weak signals are becoming one clearer GOLD story.",
            "driver_ids": ["hnc_auris", "lambda_history", "probability_rows"],
        },
        {
            "id": "probability_contradiction_hunt",
            "title": "Probability contradiction hunt dream",
            "imagination_lane": "counter_intelligence",
            "premise": "The best trade may be no trade when probability rows conflict with fresh source lanes.",
            "driver_ids": ["probability_rows", "contradiction_matrix", "counter_intelligence"],
        },
        {
            "id": "three_p_micro_edge",
            "title": "Three-pence micro-edge dream",
            "imagination_lane": "profit_floor",
            "premise": "Tiny validated GOLD moves matter only when spread, slippage, financing, and size still clear the 3p floor.",
            "driver_ids": ["three_p_floor", "spread_slippage", "portfolio_uplift"],
        },
    ]
    dreams: List[Dict[str, Any]] = []
    for index, template in enumerate(templates):
        driver_ids = list(template["driver_ids"])
        ready_count = sum(1 for driver_id in driver_ids if driver_id in ready_driver_ids)
        evidence_score = _clamp(
            (ready_count / max(1.0, len(driver_ids))) * 0.34
            + (ready_replay_count / max(1.0, len(replay_lanes))) * 0.16
            + edge_score * 0.16
            + memory_score * 0.18
            + forecast_confidence * 0.08
            + (0.08 if source_paths else 0.0)
        )
        creativity_score = _clamp(
            0.52
            + (index % 5) * 0.055
            + (0.08 if template["imagination_lane"] in {"counter_intelligence", "hnc_auris", "waveform"} else 0.0)
            + min(len(active_agents), 12) * 0.005
        )
        hnc_fit_score = _clamp(memory_score * 0.45 + edge_score * 0.25 + forecast_confidence * 0.2 + (0.1 if ready_count else 0.0))
        proof_gap_count = sum(1 for driver_id in driver_ids if driver_id not in ready_driver_ids)
        if evidence_score >= 0.58 and proof_gap_count <= 1:
            state = "ready_for_shadow_validation"
            next_action = "attach_fresh_tick_and_interval_deadline"
        elif evidence_score >= 0.34:
            state = "dream_needs_driver_confirmation"
            next_action = "refresh_missing_driver_lanes"
        else:
            state = "idea_only_needs_source_proof"
            next_action = "collect_source_packets_and_replay_history"
        dreams.append(
            {
                **template,
                "driver_ids": driver_ids,
                "ready_driver_count": ready_count,
                "validation_route": [
                    "fresh_source_mesh",
                    "historical_replay",
                    "dynamic_edge_stream",
                    "interval_validation",
                    "hnc_auris_coherence",
                    "three_p_floor_guard",
                ],
                "evidence_score": round(evidence_score, 4),
                "creativity_score": round(creativity_score, 4),
                "hnc_fit_score": round(hnc_fit_score, 4),
                "proof_gap_count": proof_gap_count,
                "state": state,
                "action_use": "idea_only_until_fresh_interval_validated",
                "live_order_allowed": False,
                "margin_order_allowed": False,
                "order_mutation_allowed": False,
                "next_validation_action": next_action,
                "source_paths": source_paths,
            }
        )

    ready_dreams = [dream for dream in dreams if dream.get("state") == "ready_for_shadow_validation"]
    validation_queue = [
        {
            "dream_id": dream.get("id"),
            "priority": "high" if dream.get("state") == "ready_for_shadow_validation" else "medium" if _num(dream.get("evidence_score")) >= 0.34 else "low",
            "next_validation_action": dream.get("next_validation_action"),
            "required_proof": dream.get("validation_route"),
            "action_authority": "non_mutating_shadow_validation_only",
        }
        for dream in sorted(dreams, key=lambda item: (_num(item.get("evidence_score")), _num(item.get("creativity_score"))), reverse=True)
    ]
    average_creativity = sum(_num(dream.get("creativity_score")) for dream in dreams) / max(1, len(dreams))
    average_evidence = sum(_num(dream.get("evidence_score")) for dream in dreams) / max(1, len(dreams))
    blockers: List[Dict[str, Any]] = []
    if len(dreams) < 10:
        blockers.append({"id": "dream_count_low", "reason": "At least 10 distinct GOLD dreams are required for creative breadth."})
    if not source_paths:
        blockers.append({"id": "research_packets_missing", "reason": "Local Gary/Aureon research packets are not selected for dream grounding."})
    if len(active_agents) < 4:
        blockers.append({"id": "agent_creativity_crew_small", "reason": "Not enough active agents are available to pressure-test creative hypotheses."})
    if not ready_dreams:
        blockers.append({"id": "no_dream_ready_for_shadow_validation", "reason": "No dream has enough proof to enter shadow validation."})
    status = "gold_creative_dream_hypothesis_engine_ready" if not blockers else "gold_creative_dream_hypothesis_engine_attention"
    return {
        "status": status,
        "generated_at": generated_at,
        "mode": "creative_gold_hypothesis_factory",
        "policy": "Dream widely, then force every idea through fresh source proof, interval validation, HNC/Auris coherence, and the 3p floor before it can matter.",
        "dream_count": len(dreams),
        "ready_dream_count": len(ready_dreams),
        "research_packet_count": len(source_paths),
        "active_agent_count": len(active_agents),
        "average_creativity_score": round(average_creativity, 4),
        "average_evidence_score": round(average_evidence, 4),
        "dreams": dreams,
        "validation_queue": validation_queue[:12],
        "creative_contract": {
            "who": "Aureon creative GOLD intelligence crew",
            "what": "Generate many plausible GOLD edge dreams, then convert them into proof-seeking validation jobs.",
            "where": ["cross_market_driver_matrix", "historical_signal_lab", "gold_dynamic_market_edge_stream", "gold_hnc_history_future_bridge", "gold_probability_projection_forecast"],
            "when": generated_at,
            "how": "Blend source packets, driver readiness, replay memory, waveform edge score, probability confidence, and active agent coverage.",
            "act": "queue_shadow_validation_not_live_action",
        },
        "action_influence_allowed": False,
        "live_order_allowed": False,
        "margin_order_allowed": False,
        "order_mutation_allowed": False,
        "blockers": blockers[:12],
        "manual_boundaries": [
            "Creative dreams are hypotheses, not truth claims.",
            "Dreams cannot unlock live orders, margin mutation, or portfolio-growth claims.",
            "Only fresh interval validation and existing runtime/risk gates can promote a downstream shadow intent.",
        ],
    }


def _build_gold_hnc_action_coherence_gate(
    *,
    cognitive_route: Dict[str, Any],
    signal_freshness_matrix: Dict[str, Any],
    projection_interval_validation: Dict[str, Any],
    generated_at: str,
) -> Dict[str, Any]:
    auris = cognitive_route.get("auris_nodes") if isinstance(cognitive_route.get("auris_nodes"), dict) else {}
    blockers: List[Dict[str, Any]] = []
    if not cognitive_route.get("route_passed"):
        blockers.append({"id": "hnc_auris_route_blocking", "reason": "HNC/Auris route is not passing."})
    if not signal_freshness_matrix.get("action_influence_allowed"):
        blockers.append({"id": "fresh_signal_matrix_blocking", "reason": "HNC cannot promote stale or reference-only GOLD signals."})
    if not projection_interval_validation.get("action_influence_allowed"):
        blockers.append({"id": "projection_intervals_blocking", "reason": "HNC cannot promote unvalidated GOLD projection intervals."})
    action_coherence_allowed = not blockers
    return {
        "status": "gold_hnc_action_coherence_gate_passed" if action_coherence_allowed else "gold_hnc_action_coherence_gate_blocking",
        "generated_at": generated_at,
        "weapon_policy": "HNC/Auris raises confidence only after fresh ticker proof and interval validation; otherwise it lowers confidence.",
        "action_coherence_allowed": action_coherence_allowed,
        "hnc_route_status": cognitive_route.get("status"),
        "auris_node_count": auris.get("node_count"),
        "auris_coherence": auris.get("coherence"),
        "confidence_effect": "raise_allowed" if action_coherence_allowed else "lower_or_hold",
        "blockers": blockers[:12],
    }


def _build_gold_portfolio_uplift_guard(
    *,
    asset: Dict[str, Any],
    three_p_gate: Dict[str, Any],
    projection_interval_validation: Dict[str, Any],
    runtime_stale: bool,
    snapshot_fresh: bool,
    generated_at: str,
) -> Dict[str, Any]:
    estimated_net = _num(three_p_gate.get("estimated_net_at_suggested_size"))
    floor_amount = _num(three_p_gate.get("profit_floor_account_currency"), 0.03)
    shadow_pl = _num(projection_interval_validation.get("total_shadow_p_l_effect"))
    blockers: List[Dict[str, Any]] = []
    if not asset:
        blockers.append({"id": "capital_gold_asset_missing", "reason": "Portfolio guard has no Capital GOLD asset."})
    if runtime_stale:
        blockers.append({"id": "runtime_stale", "reason": "Portfolio uplift proof cannot promote while runtime is stale."})
    if not snapshot_fresh:
        blockers.append({"id": "capital_gold_snapshot_not_fresh", "reason": "Portfolio uplift proof requires fresh GOLD bid/ask."})
    if three_p_gate.get("state") != "shadow_trade_candidate":
        blockers.append({"id": "three_p_floor_not_proven", "reason": "3p net floor has not produced a shadow trade candidate."})
    if estimated_net < floor_amount:
        blockers.append({"id": "estimated_net_below_3p_floor", "reason": f"Estimated net {round(estimated_net, 5)} is below {floor_amount}."})
    if not projection_interval_validation.get("action_influence_allowed"):
        blockers.append({"id": "projection_intervals_not_validated", "reason": "Portfolio uplift cannot use unvalidated projection intervals."})
    if shadow_pl <= 0:
        blockers.append({"id": "shadow_pl_not_positive", "reason": "Validated projection intervals do not show positive shadow P/L effect."})
    order_intent_consideration_allowed = not blockers
    return {
        "status": "gold_portfolio_uplift_guard_passed" if order_intent_consideration_allowed else "gold_portfolio_uplift_guard_blocking",
        "generated_at": generated_at,
        "policy": "Portfolio increase claims require validated shadow P/L, 3p floor proof, fresh price, and current risk/runtime truth.",
        "portfolio_growth_claim_allowed": order_intent_consideration_allowed,
        "order_intent_consideration_allowed": order_intent_consideration_allowed,
        "estimated_net_at_suggested_size": three_p_gate.get("estimated_net_at_suggested_size"),
        "profit_floor_account_currency": floor_amount,
        "validated_shadow_p_l_effect": round(shadow_pl, 5),
        "suggested_shadow_size": three_p_gate.get("suggested_shadow_size"),
        "live_order_allowed": False,
        "order_mutation_allowed": False,
        "blockers": blockers[:12],
    }


def _asset_candidates(registry: Dict[str, Any]) -> List[Dict[str, Any]]:
    assets = registry.get("assets") if isinstance(registry.get("assets"), list) else []
    candidates: List[Dict[str, Any]] = []
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        blob = " ".join(
            str(asset.get(key) or "")
            for key in ("symbol", "epic", "instrument_name", "instrument_type", "asset_class")
        ).lower()
        if "gold" in blob or "xau" in blob:
            candidates.append(asset)
    return sorted(
        candidates,
        key=lambda item: (
            0 if str(item.get("epic", "")).upper() == "GOLD" else 1,
            0 if item.get("trade_ready") else 1,
            str(item.get("expiry") or "9999"),
        ),
    )


def _primary_gold_asset(registry: Dict[str, Any]) -> Dict[str, Any]:
    candidates = _asset_candidates(registry)
    return candidates[0] if candidates else {}


def _apply_runtime_gold_asset_overlay(asset: Dict[str, Any], runtime: Dict[str, Any], now: datetime) -> Dict[str, Any]:
    proof = runtime.get("gold_runtime_trade_proof") if isinstance(runtime.get("gold_runtime_trade_proof"), dict) else {}
    fresh_source = proof.get("fresh_gold_data_source") if isinstance(proof.get("fresh_gold_data_source"), dict) else {}
    if not proof.get("gold_runtime_candidate_ready") or not fresh_source.get("ready"):
        return asset
    age = _num(fresh_source.get("age_sec"), -1.0)
    budget = _num(fresh_source.get("fresh_seconds_budget"), 180.0)
    reference_price = _num(fresh_source.get("reference_price"), 0.0)
    if age < 0 or age > budget or reference_price <= 0:
        return asset

    overlaid = dict(asset) if isinstance(asset, dict) else {}
    spread = _num(overlaid.get("spread"), 0.5)
    bid = reference_price - spread / 2.0 if spread > 0 else reference_price
    ask = reference_price + spread / 2.0 if spread > 0 else reference_price
    timestamp = now - timedelta(seconds=age)
    overlaid.update(
        {
            "symbol": fresh_source.get("capital_symbol") or overlaid.get("symbol") or "GOLD",
            "epic": fresh_source.get("capital_symbol") or overlaid.get("epic") or "GOLD",
            "instrument_name": overlaid.get("instrument_name") or "Gold",
            "market_status": overlaid.get("market_status") or "TRADEABLE",
            "bid": round(bid, 6),
            "ask": round(ask, 6),
            "mid_price": round(reference_price, 6),
            "spread": round(max(0.0, ask - bid), 6),
            "spread_pct": round((max(0.0, ask - bid) / reference_price) * 100.0, 8),
            "last_snapshot_at": timestamp.isoformat(),
            "trade_ready": bool(overlaid.get("trade_ready", True)),
            "live_quote_overlay_applied": True,
            "live_quote_source_path": "state/unified_runtime_status.json#gold_runtime_trade_proof.fresh_gold_data_source",
            "runtime_candidate_symbol": proof.get("candidate_symbol"),
            "runtime_candidate_side": proof.get("candidate_side"),
            "runtime_candidate_ready": bool(proof.get("gold_runtime_candidate_ready")),
            "runtime_gold_intent_publish_reason": proof.get("gold_intent_publish_reason"),
        }
    )
    return overlaid


def _build_signal(
    signal_id: str,
    label: str,
    score: float,
    *,
    direction: str,
    source: str,
    reason: str,
    fresh: bool,
) -> Dict[str, Any]:
    return {
        "id": signal_id,
        "label": label,
        "score": round(_clamp(score), 4),
        "direction": direction,
        "source": source,
        "reason": reason,
        "fresh": bool(fresh),
    }


def _price_hypothesis(asset: Dict[str, Any], snapshot_age_sec: Optional[float]) -> Dict[str, Any]:
    mid = _num(asset.get("mid_price"))
    bid = _num(asset.get("bid"))
    ask = _num(asset.get("ask"))
    spread = _num(asset.get("spread"), max(0.0, ask - bid))
    stale_factor = 1.0
    if snapshot_age_sec is None:
        stale_factor = 2.0
    elif snapshot_age_sec > 900:
        stale_factor = min(8.0, 1.0 + snapshot_age_sec / 21_600.0)
    band = max(spread * 3.0, mid * 0.0015) * stale_factor if mid else 0.0
    return {
        "symbol": asset.get("symbol") or asset.get("epic") or "GOLD",
        "epic": asset.get("epic") or "GOLD",
        "mid_price": round(mid, 5) if mid else None,
        "bid": round(bid, 5) if bid else None,
        "ask": round(ask, 5) if ask else None,
        "spread": round(spread, 5) if spread else None,
        "currency": asset.get("currency") or "USD",
        "hypothesis_low": round(mid - band, 5) if mid and band else None,
        "hypothesis_high": round(mid + band, 5) if mid and band else None,
        "band_reason": "range expands when Capital snapshot/runtime evidence is stale",
        "not_investment_advice": True,
    }


def _build_gold_priority_workbench(
    *,
    asset: Dict[str, Any],
    decision: Dict[str, Any],
    price_hypothesis: Dict[str, Any],
    historical_signal_lab: Dict[str, Any],
    cross_market_driver_matrix: List[Dict[str, Any]],
    blockers: List[Dict[str, Any]],
    intelligence_gaps: List[Dict[str, Any]],
    generated_at: str,
) -> Dict[str, Any]:
    mid = _num(price_hypothesis.get("mid_price"))
    spread = _num(price_hypothesis.get("spread"), mid * 0.0003 if mid else 0.0)
    energy = _num(decision.get("gold_energy_score"))
    confidence = _num(decision.get("confidence"))
    freshness_factor = 0.35 if blockers else 0.85
    bias = (energy - 0.5) * 2.0
    base_band = max(spread * 5.0, mid * 0.0015 if mid else 1.0)
    horizons = [
        ("now", 0.0),
        ("5m", 0.18),
        ("15m", 0.35),
        ("1h", 0.6),
        ("4h", 1.0),
        ("1d", 1.55),
        ("3d", 2.15),
        ("1w", 2.8),
    ]
    forecast_points: List[Dict[str, Any]] = []
    for label, multiplier in horizons:
        drift = mid * 0.0012 * bias * multiplier * freshness_factor if mid else 0.0
        uncertainty = base_band * (1.0 + multiplier * 0.45) * (1.65 if blockers else 1.0)
        forecast_points.append(
            {
                "horizon": label,
                "shadow_mid": round(mid + drift, 5) if mid else None,
                "shadow_low": round(mid + drift - uncertainty, 5) if mid else None,
                "shadow_high": round(mid + drift + uncertainty, 5) if mid else None,
                "confidence": round(_clamp(confidence * (1.0 - multiplier * 0.08)), 4),
                "mode": "shadow_forecast_band",
            }
        )

    weak_driver_ids = [str(item.get("id")) for item in cross_market_driver_matrix if item.get("driver_state") != "ready_shadow_driver"]
    lab_gaps = [str(gap.get("id")) for gap in historical_signal_lab.get("gaps", []) if isinstance(gap, dict)]
    data_queue = [
        {
            "id": "refresh_capital_gold_quote_and_ohlc",
            "priority": "P0",
            "agent": "Capital GOLD Collector",
            "data_needed": "Fresh GOLD quote, market hours, 1m/5m/1h/1d OHLC bars, spread, and timestamp.",
            "proof_required": "Capital snapshot and chart bars are under the freshness threshold.",
            "blocks": ["chart_replay_state", "live_use_confidence"],
        },
        {
            "id": "build_gold_cross_asset_pack",
            "priority": "P0",
            "agent": "Macro Rates Reader",
            "data_needed": "DXY/USD, real-yield/rates proxy, oil, VIX, GLD/GDX/miners, BTC/crypto liquidity, and equity index context.",
            "proof_required": "Matched timestamps and lead-lag rows for every driver.",
            "blocks": ["driver_attribution", "lead_lag_state"],
        },
        {
            "id": "probe_gold_orderbook_pressure",
            "priority": "P1",
            "agent": "Risk And Shadow Validator",
            "data_needed": "GOLD quote-depth/order pressure or closest Capital-supported equivalent.",
            "proof_required": "Direct GOLD pressure sample before confidence increases.",
            "blocks": ["orderbook_signal_state"],
        },
        {
            "id": "run_gold_waveform_backtest",
            "priority": "P1",
            "agent": "Waveform Forecast Reader",
            "data_needed": "Multi-horizon GOLD bars plus related drivers on the same timeline.",
            "proof_required": "Replay labels move as normal, stretched, reversing, or contradictory.",
            "blocks": ["waveform_replay_state"],
        },
        {
            "id": "draw_gold_forecast_dashboard",
            "priority": "P1",
            "agent": "Operator Evidence Clerk",
            "data_needed": "Latest forecast points, bands, drivers, blockers, and chart preview links.",
            "proof_required": "Browser-openable SVG and HTML preview exist.",
            "blocks": ["human_operator_visibility"],
        },
    ]
    return {
        "status": "gold_priority_workbench_attention" if blockers or lab_gaps else "gold_priority_workbench_ready",
        "priority_focus": "Capital GOLD",
        "generated_at": generated_at,
        "artifact_manifest": {
            "svg_url": "/" + GOLD_FORECAST_SVG.relative_to(Path("frontend/public")).as_posix(),
            "html_url": "/" + GOLD_FORECAST_HTML.relative_to(Path("frontend/public")).as_posix(),
            "svg_path": GOLD_FORECAST_SVG.as_posix(),
            "html_path": GOLD_FORECAST_HTML.as_posix(),
        },
        "forecast_points": forecast_points,
        "data_priority_queue": data_queue,
        "agent_assignments": [
            {"agent": item["agent"], "active_task": item["id"], "priority": item["priority"]}
            for item in data_queue
        ],
        "quality_gates": [
            "Draw charts only from timestamped local evidence or label them as scaffold.",
            "Forecast bands are shadow hypotheses, not financial advice.",
            "Increase confidence only after fresh Capital GOLD OHLC, direct driver rows, and direct pressure proof.",
            "Keep live Capital execution blocked behind existing runtime/risk/credential gates.",
        ],
        "driver_ids": [str(item.get("id")) for item in cross_market_driver_matrix],
        "weak_driver_ids": weak_driver_ids,
        "lab_gap_ids": lab_gaps,
        "blocker_ids": [str(item.get("id")) for item in blockers],
        "intelligence_gap_ids": [str(item.get("id")) for item in intelligence_gaps],
        "chart_contract": {
            "chart_type": "shadow_forecast_band_with_driver_queue",
            "target_symbol": asset.get("symbol") or "GOLD",
            "venue": "Capital.com",
            "handover": "visible_for_operator_review",
            "authority": "read_only_non_mutating",
        },
    }


def _round_deal_size(size: float, step: float) -> float:
    if step <= 0:
        return round(size, 6)
    return round(math.ceil(size / step) * step, 6)


def _build_three_p_profit_floor_gate(
    *,
    asset: Dict[str, Any],
    decision: Dict[str, Any],
    price_hypothesis: Dict[str, Any],
    historical_signal_lab: Dict[str, Any],
    blockers: List[Dict[str, Any]],
    runtime_stale: bool,
    snapshot_fresh: bool,
) -> Dict[str, Any]:
    floor_amount = 0.03
    floor_label = "3p net floor"
    bid = _num(asset.get("bid"))
    ask = _num(asset.get("ask"))
    mid = _num(price_hypothesis.get("mid_price") or asset.get("mid_price"))
    spread = _num(price_hypothesis.get("spread") or asset.get("spread"), max(0.0, ask - bid))
    min_deal_size = max(0.0, _num(asset.get("minimum_deal_size"), 0.01))
    size_step = min_deal_size if min_deal_size else 0.01
    slippage_buffer = max(spread * 0.5, mid * 0.0001 if mid else 0.0)
    unknown_fee_buffer = 0.0
    known_cost_per_unit = spread + slippage_buffer + unknown_fee_buffer
    min_move_for_floor_at_min_size = known_cost_per_unit + (floor_amount / max(min_deal_size, 0.000001))
    direction_guess = str(decision.get("direction_guess") or "").upper()
    if "BULLISH" in direction_guess:
        side = "BUY"
    elif "BEARISH" in direction_guess:
        side = "SELL"
    else:
        side = "HOLD"

    if side == "BUY":
        entry_level = ask
        target_level = ask + min_move_for_floor_at_min_size if ask else None
        stop_level = ask - (min_move_for_floor_at_min_size * 1.5) if ask else None
        expected_move = _num(price_hypothesis.get("hypothesis_high")) - ask if ask else 0.0
        entry_instruction = "buy only at or below current ask after fresh proof"
    elif side == "SELL":
        entry_level = bid
        target_level = bid - min_move_for_floor_at_min_size if bid else None
        stop_level = bid + (min_move_for_floor_at_min_size * 1.5) if bid else None
        expected_move = bid - _num(price_hypothesis.get("hypothesis_low")) if bid else 0.0
        entry_instruction = "sell only at or above current bid after fresh proof"
    else:
        entry_level = mid
        target_level = None
        stop_level = None
        expected_move = 0.0
        entry_instruction = "hold until a directional edge is fresh and proven"

    net_move_after_cost = max(0.0, expected_move - known_cost_per_unit)
    size_required_for_floor = _round_deal_size(floor_amount / net_move_after_cost, size_step) if net_move_after_cost > 0 else None
    suggested_size = max(min_deal_size, size_required_for_floor or min_deal_size)
    estimated_net_at_suggested_size = max(0.0, net_move_after_cost * suggested_size)
    lab_attention = str(historical_signal_lab.get("status") or "").endswith("attention")
    direct_orderbook_missing = historical_signal_lab.get("orderbook_signal_state") != "ready_shadow_replay"
    gate_blockers: List[Dict[str, Any]] = []
    if side == "HOLD":
        gate_blockers.append({"id": "no_directional_edge", "reason": f"Direction is {direction_guess or 'unknown'}."})
    if runtime_stale:
        gate_blockers.append({"id": "runtime_stale_blocks_3p_floor", "reason": "Runtime freshness is required before a 3p floor can be trusted."})
    if not snapshot_fresh:
        gate_blockers.append({"id": "capital_gold_snapshot_not_fresh", "reason": "Fresh GOLD bid/ask is required before sizing."})
    if lab_attention:
        gate_blockers.append({"id": "historical_signal_lab_attention", "reason": "Replay lab is still attention-gated."})
    if direct_orderbook_missing:
        gate_blockers.append({"id": "direct_orderbook_pressure_missing", "reason": "Direct GOLD pressure proof is not ready."})
    if estimated_net_at_suggested_size < floor_amount:
        gate_blockers.append(
            {
                "id": "expected_net_below_3p_floor",
                "reason": f"Estimated net {round(estimated_net_at_suggested_size, 5)} is below {floor_amount}.",
            }
        )
    gate_blockers.extend({"id": str(item.get("id")), "reason": str(item.get("reason") or "")} for item in blockers[:6])
    unique_blockers: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for item in gate_blockers:
        if item["id"] in seen:
            continue
        seen.add(item["id"])
        unique_blockers.append(item)

    state = "shadow_trade_candidate" if side != "HOLD" and not unique_blockers else "hold_until_3p_floor_proven"
    return {
        "status": "three_p_profit_floor_active",
        "state": state,
        "profit_floor_account_currency": floor_amount,
        "profit_floor_label": floor_label,
        "currency": asset.get("currency") or price_hypothesis.get("currency") or "account_currency",
        "side": side,
        "entry_instruction": entry_instruction,
        "entry_level": round(entry_level, 5) if entry_level else None,
        "target_level": round(target_level, 5) if target_level else None,
        "stop_level": round(stop_level, 5) if stop_level else None,
        "minimum_price_move_for_floor_at_min_size": round(min_move_for_floor_at_min_size, 5),
        "known_cost_per_unit": round(known_cost_per_unit, 5),
        "spread": round(spread, 5),
        "slippage_buffer": round(slippage_buffer, 5),
        "minimum_deal_size": min_deal_size,
        "suggested_shadow_size": round(suggested_size, 6),
        "size_required_for_floor": round(size_required_for_floor, 6) if size_required_for_floor is not None else None,
        "estimated_net_at_suggested_size": round(estimated_net_at_suggested_size, 5),
        "margin_required_for_min_deal": asset.get("margin_required_for_min_deal"),
        "min_notional_estimate": asset.get("min_notional_estimate"),
        "live_order_allowed": False,
        "order_mutation_allowed": False,
        "blockers": unique_blockers[:12],
        "rules": [
            "Never enter unless expected net profit is at least 0.03 after spread and slippage.",
            "Use fresh bid/ask and chart proof before choosing BUY or SELL.",
            "Use the smallest proven size first; scale only after repeatable shadow proof.",
            "Live orders remain blocked unless existing runtime, risk, credential, and execution gates pass.",
        ],
        "buy_contract": {
            "when": "Only when fresh forecast and driver proof make the upside target exceed ask plus cost and 3p floor.",
            "entry_price_source": "current ask",
            "target_formula": "ask + spread + slippage_buffer + floor_amount / size",
        },
        "sell_contract": {
            "when": "Only when fresh forecast and driver proof make the downside target exceed bid minus cost and 3p floor.",
            "entry_price_source": "current bid",
            "target_formula": "bid - spread - slippage_buffer - floor_amount / size",
        },
    }


def _side_from_projection(value: Any) -> str:
    text = str(value or "").upper()
    if any(token in text for token in ("BUY", "BULL", "UP", "LONG")):
        return "BUY"
    if any(token in text for token in ("SELL", "BEAR", "DOWN", "SHORT")):
        return "SELL"
    return "HOLD"


def _build_gold_probability_projection_forecast(
    *,
    decision: Dict[str, Any],
    cognitive_route: Dict[str, Any],
    signal_freshness_matrix: Dict[str, Any],
    ticker_source_mesh: Dict[str, Any],
    projection_interval_validation: Dict[str, Any],
    hnc_action_coherence_gate: Dict[str, Any],
    portfolio_uplift_guard: Dict[str, Any],
    verified_data_gate: Dict[str, Any],
    hft_speed_gate: Dict[str, Any],
    historical_stress_test: Dict[str, Any],
    margin_trader_unity: Dict[str, Any],
    cross_market_driver_matrix: List[Dict[str, Any]],
    swarm_intelligence: Dict[str, Any],
    generated_at: str,
) -> Dict[str, Any]:
    probability = cognitive_route.get("probability_systems") if isinstance(cognitive_route.get("probability_systems"), dict) else {}
    probability_rows = probability.get("gold_probability_rows") if isinstance(probability.get("gold_probability_rows"), list) else []
    intervals = projection_interval_validation.get("intervals") if isinstance(projection_interval_validation.get("intervals"), list) else []
    lanes = ticker_source_mesh.get("lanes") if isinstance(ticker_source_mesh.get("lanes"), list) else []
    active_agents = [agent for agent in (swarm_intelligence.get("agents") or []) if agent.get("state") == "active"]
    ready_drivers = [driver for driver in cross_market_driver_matrix if driver.get("driver_state") == "ready_shadow_driver"]
    weak_drivers = [driver for driver in cross_market_driver_matrix if driver.get("driver_state") != "ready_shadow_driver"]

    side_weights = {"BUY": 0.0, "SELL": 0.0, "HOLD": 0.0}
    probability_claims: List[Dict[str, Any]] = []
    for row in probability_rows:
        side = _side_from_projection(row.get("direction") or row.get("predicted_action") or row.get("predicted_direction"))
        probability_score = _num(row.get("probability"), 0.5)
        confidence = _num(row.get("confidence"), 0.5)
        validated = bool(row.get("validated"))
        hit = bool(row.get("direction_correct") or _num(row.get("outcome_score")) > 0)
        validation_weight = 1.15 if validated and hit else 0.6 if validated else 0.35
        weight = max(0.05, probability_score * confidence * validation_weight)
        side_weights[side] = side_weights.get(side, 0.0) + weight
        probability_claims.append(
            {
                "id": row.get("prediction_id") or f"{row.get('symbol')}_{row.get('interval')}",
                "symbol": row.get("symbol"),
                "interval": _row_interval_id(row) or row.get("interval"),
                "side": side,
                "probability": round(probability_score, 4),
                "confidence": round(confidence, 4),
                "validated": validated,
                "hit_miss": "hit" if validated and hit else "miss" if validated else "unvalidated",
                "truth_status": "validated_outcome_hit" if validated and hit else "validated_outcome_miss" if validated else "hypothesis_only",
                "source_tickers": row.get("source_tickers") or [],
                "shadow_p_l_effect": row.get("shadow_p_l_effect"),
            }
        )
    if not probability_claims:
        side_weights["HOLD"] = 1.0

    total_weight = sum(side_weights.values()) or 1.0
    distribution = {
        side.lower(): round(_clamp(weight / total_weight), 4)
        for side, weight in side_weights.items()
    }
    dominant_side = max(side_weights, key=lambda side: side_weights[side])
    validated_count = sum(1 for item in probability_claims if item["validated"])
    hit_count = sum(1 for item in probability_claims if item["hit_miss"] == "hit")
    miss_count = sum(1 for item in probability_claims if item["hit_miss"] == "miss")
    hit_rate = hit_count / validated_count if validated_count else 0.0

    source_quality = _num(ticker_source_mesh.get("fresh_lane_count")) / max(1.0, _num(ticker_source_mesh.get("lane_count"), 1.0))
    signal_quality = _num(signal_freshness_matrix.get("action_influence_row_count")) / max(1.0, _num(signal_freshness_matrix.get("row_count"), 1.0))
    interval_quality = _num(projection_interval_validation.get("hit_rate")) * (
        _num(projection_interval_validation.get("validated_interval_count")) / max(1.0, _num(projection_interval_validation.get("required_interval_count"), 1.0))
    )
    hnc_quality = _num((cognitive_route.get("auris_nodes") or {}).get("coherence")) if cognitive_route.get("route_passed") else 0.0
    hft_quality = _num(hft_speed_gate.get("speed_score")) if hft_speed_gate.get("gate_passed") else _num(hft_speed_gate.get("speed_score")) * 0.35
    historical_quality = _num((historical_stress_test.get("prediction_validation") or {}).get("hit_rate")) if historical_stress_test.get("stress_passed") else 0.0
    portfolio_quality = 1.0 if portfolio_uplift_guard.get("order_intent_consideration_allowed") else 0.0
    margin_quality = 1.0 if margin_trader_unity.get("unity_state") == "gold_margin_unity_shadow_ready" else 0.0
    organism_quality = _clamp(
        source_quality * 0.16
        + signal_quality * 0.12
        + interval_quality * 0.18
        + hnc_quality * 0.14
        + hft_quality * 0.12
        + historical_quality * 0.14
        + portfolio_quality * 0.07
        + margin_quality * 0.07
    )
    dominant_probability = distribution.get(dominant_side.lower(), 0.0)
    calibrated_confidence = _clamp(dominant_probability * (0.25 + organism_quality * 0.75))

    blockers: List[Dict[str, Any]] = []
    if not verified_data_gate.get("action_allowed_by_data"):
        blockers.append({"id": "verified_real_data_gate_blocking", "reason": "Forecast cannot be treated as truth while verified real data is blocking."})
    if not signal_freshness_matrix.get("action_influence_allowed"):
        blockers.append({"id": "fresh_signal_matrix_blocking", "reason": "Probability forecast cannot influence action while source rows are stale or blocked."})
    if not projection_interval_validation.get("action_influence_allowed"):
        blockers.append({"id": "projection_interval_validation_blocking", "reason": "Forecast intervals are not fully validated for action influence."})
    if not hnc_action_coherence_gate.get("action_coherence_allowed"):
        blockers.append({"id": "hnc_auris_coherence_blocking", "reason": "HNC/Auris is lowering or holding confidence."})
    if not hft_speed_gate.get("gate_passed"):
        blockers.append({"id": "hft_speed_prediction_gate_blocking", "reason": "Fast forecast path is not fresh and outcome-validated enough."})
    if not historical_stress_test.get("stress_passed"):
        blockers.append({"id": "historical_stress_test_blocking", "reason": "Historical stress test has not passed."})
    if not portfolio_uplift_guard.get("order_intent_consideration_allowed"):
        blockers.append({"id": "portfolio_uplift_guard_blocking", "reason": "Portfolio uplift guard blocks any portfolio-growth claim."})
    if margin_trader_unity.get("unity_state") != "gold_margin_unity_shadow_ready":
        blockers.append({"id": "margin_unity_not_shadow_ready", "reason": "Margin systems are not unified enough to promote the forecast."})
    if miss_count:
        blockers.append({"id": "validated_interval_contradictions_present", "reason": f"{miss_count} validated probability claim(s) contradicted the forecast."})

    contradiction_matrix: List[Dict[str, Any]] = []
    for claim in probability_claims:
        if claim["hit_miss"] == "miss":
            contradiction_matrix.append(
                {
                    "id": f"{claim.get('interval')}_validated_miss",
                    "source": claim.get("id"),
                    "reason": f"{claim.get('interval')} {claim.get('side')} probability claim missed.",
                    "confidence_effect": "lower",
                }
            )
    for driver in weak_drivers[:8]:
        contradiction_matrix.append(
            {
                "id": str(driver.get("id")),
                "source": "cross_market_driver_matrix",
                "reason": f"{driver.get('label') or driver.get('id')} is {driver.get('driver_state')}.",
                "confidence_effect": "hold",
            }
        )
    for lane in lanes[:8]:
        if not lane.get("fresh"):
            contradiction_matrix.append(
                {
                    "id": str(lane.get("id")),
                    "source": "gold_ticker_source_mesh",
                    "reason": f"{lane.get('label') or lane.get('id')} is not fresh.",
                    "confidence_effect": "lower",
                }
            )

    truth_claim_allowed = not blockers
    validated_forecast_state = (
        "validated_forecast_action_influence_allowed"
        if truth_claim_allowed
        else "validated_history_but_not_truth_claim"
        if validated_count >= len(GOLD_INTERVAL_VALIDATION_WINDOWS) and hit_rate >= 0.55
        else "hypothesis_until_validated"
    )
    if dominant_side not in {"BUY", "SELL"} or calibrated_confidence < 0.4:
        forecast_direction = "HOLD"
    else:
        forecast_direction = dominant_side

    return {
        "status": "gold_probability_projection_forecast_passed" if truth_claim_allowed else "gold_probability_projection_forecast_blocking",
        "generated_at": generated_at,
        "mode": "probabilistic_validated_forecast_not_truth_until_proven",
        "truth_discipline": {
            "truth_claim_allowed": truth_claim_allowed,
            "truth_status": "validated_action_truth" if truth_claim_allowed else "hypothesis_until_validated",
            "operator_language": "Say probability, proof, blocker, and next validation action. Do not say truth or certainty until all gates pass.",
            "no_fake_certainty": True,
        },
        "forecast_distribution": {
            "buy_probability": distribution.get("buy", 0.0),
            "sell_probability": distribution.get("sell", 0.0),
            "hold_probability": distribution.get("hold", 0.0),
            "dominant_side": dominant_side,
            "calibrated_direction": forecast_direction,
            "calibrated_confidence": round(calibrated_confidence, 4),
            "organism_quality_score": round(organism_quality, 4),
        },
        "validated_forecast": {
            "state": validated_forecast_state,
            "direction": forecast_direction,
            "validated_claim_count": validated_count,
            "hit_count": hit_count,
            "miss_count": miss_count,
            "hit_rate": round(hit_rate, 4) if validated_count else None,
            "action_influence_allowed": truth_claim_allowed,
            "current_decision_direction": decision.get("direction_guess"),
            "current_decision_confidence": decision.get("confidence"),
        },
        "organism_inputs": {
            "probability_rows": len(probability_claims),
            "fresh_ticker_lanes": ticker_source_mesh.get("fresh_lane_count"),
            "ticker_lanes": ticker_source_mesh.get("lane_count"),
            "fresh_signal_rows": signal_freshness_matrix.get("fresh_row_count"),
            "signal_rows": signal_freshness_matrix.get("row_count"),
            "validated_intervals": projection_interval_validation.get("validated_interval_count"),
            "required_intervals": projection_interval_validation.get("required_interval_count"),
            "active_swarm_agents": len(active_agents),
            "ready_driver_count": len(ready_drivers),
            "driver_count": len(cross_market_driver_matrix),
            "auris_nodes": (cognitive_route.get("auris_nodes") or {}).get("node_count"),
            "auris_coherence": (cognitive_route.get("auris_nodes") or {}).get("coherence"),
        },
        "forecast_claims": probability_claims[:12],
        "interval_claims": [
            {
                "id": interval.get("id"),
                "forecast_direction": interval.get("forecast_direction"),
                "hit_miss": interval.get("hit_miss"),
                "validated": interval.get("validated"),
                "truth_status": "validated_interval" if interval.get("validated") else "hypothesis_only",
                "action_influence_allowed": interval.get("action_influence_allowed"),
            }
            for interval in intervals
        ],
        "contradiction_matrix": contradiction_matrix[:16],
        "blockers": blockers[:16],
        "manual_boundaries": [
            "Forecast probabilities are evidence, not financial advice.",
            "A validated history row is not a live truth claim unless source freshness and action gates also pass.",
            "Live margin action remains behind runtime, risk, exchange, credential, and order gates.",
        ],
    }


def _build_gold_action_command(
    *,
    root: Path,
    decision: Dict[str, Any],
    three_p_gate: Dict[str, Any],
    verified_data_gate: Dict[str, Any],
    historical_signal_lab: Dict[str, Any],
    gold_priority_workbench: Dict[str, Any],
    swarm_intelligence: Dict[str, Any],
    cognitive_route: Dict[str, Any],
    hft_speed_gate: Dict[str, Any],
    historical_stress_test: Dict[str, Any],
    margin_trader_unity: Dict[str, Any],
    signal_freshness_matrix: Dict[str, Any],
    projection_interval_validation: Dict[str, Any],
    probability_projection_forecast: Dict[str, Any],
    dynamic_market_edge_stream: Dict[str, Any],
    hnc_history_future_bridge: Dict[str, Any],
    creative_dream_hypothesis_engine: Dict[str, Any],
    hnc_action_coherence_gate: Dict[str, Any],
    portfolio_uplift_guard: Dict[str, Any],
    cross_market_driver_matrix: List[Dict[str, Any]],
    blockers: List[Dict[str, Any]],
    intelligence_gaps: List[Dict[str, Any]],
    generated_at: str,
) -> Dict[str, Any]:
    ready_drivers = [driver for driver in cross_market_driver_matrix if driver.get("driver_state") == "ready_shadow_driver"]
    weak_drivers = [driver for driver in cross_market_driver_matrix if driver.get("driver_state") != "ready_shadow_driver"]
    active_agents = [agent for agent in (swarm_intelligence.get("agents") or []) if agent.get("state") == "active"]
    attention_agents = [agent for agent in (swarm_intelligence.get("agents") or []) if agent.get("state") != "active"]
    floor_state = str(three_p_gate.get("state") or "hold_until_3p_floor_proven")
    floor_side = str(three_p_gate.get("side") or "HOLD")
    command_systems: List[Dict[str, Any]] = []
    for system in GOLD_COMMAND_SYSTEMS:
        path = _rooted(root, Path(system["path"]))
        command_systems.append(
            {
                **system,
                "path": str(path),
                "present": path.exists(),
                "status": "mobilized_read_only" if path.exists() else "missing",
            }
        )

    proof_chain = [
        {
            "id": "verified_real_data",
            "question": "Are every action metric and signal backed by fresh real verified data?",
            "state": "ready" if verified_data_gate.get("action_allowed_by_data") else "blocked",
            "proof": (
                f"{verified_data_gate.get('fresh_required_source_count')}/"
                f"{verified_data_gate.get('required_source_count')} required sources fresh; "
                f"{verified_data_gate.get('actionable_signal_count')}/"
                f"{verified_data_gate.get('signal_count')} signals action-verified."
            ),
        },
        {
            "id": "fresh_capital_gold_quote",
            "question": "Is the current GOLD bid/ask fresh enough to size?",
            "state": "blocked" if any(blocker.get("id") == "capital_gold_snapshot_stale" for blocker in blockers) else "ready",
            "proof": "Capital GOLD snapshot age and spread are visible.",
        },
        {
            "id": "chart_and_waveform_story",
            "question": "Does chart/OHLC replay agree with waveform memory?",
            "state": historical_signal_lab.get("chart_replay_state") or "waiting",
            "proof": "GOLD OHLC and multi-horizon replay lanes must agree or show contradiction.",
        },
        {
            "id": "driver_confluence",
            "question": "Are enough GOLD drivers telling the same story?",
            "state": "ready" if len(ready_drivers) >= 8 else "attention",
            "proof": f"{len(ready_drivers)}/{len(cross_market_driver_matrix)} drivers are ready shadow drivers.",
        },
        {
            "id": "orderbook_pressure",
            "question": "Does direct GOLD pressure confirm timing?",
            "state": historical_signal_lab.get("orderbook_signal_state") or "waiting",
            "proof": "Direct GOLD pressure is required before confidence can rise.",
        },
        {
            "id": "hnc_auris_quantum_probability_route",
            "question": "Did GOLD logic pass through Auris nodes, lambda, HNC, quantum, and probability systems?",
            "state": "ready" if cognitive_route.get("route_passed") else "blocked",
            "proof": (
                f"auris_nodes={(cognitive_route.get('auris_nodes') or {}).get('node_count')} "
                f"lambda_fresh={(cognitive_route.get('lambda_system') or {}).get('fresh')} "
                f"probability_gold_rows={(cognitive_route.get('probability_systems') or {}).get('gold_row_count')}"
            ),
        },
        {
            "id": "hft_speed_validated_predictions",
            "question": "Is the GOLD prediction path fast and outcome-validated enough for high-frequency shadow use?",
            "state": "ready" if hft_speed_gate.get("gate_passed") else "blocked",
            "proof": (
                f"fresh_predictions={(hft_speed_gate.get('prediction_validation') or {}).get('fresh_gold_prediction_count')} "
                f"validated_correct={(hft_speed_gate.get('prediction_validation') or {}).get('validated_correct_gold_prediction_count')} "
                f"speed_score={hft_speed_gate.get('speed_score')}"
            ),
        },
        {
            "id": "fresh_interval_validated_gold_projection",
            "question": "Are GOLD signals fresh and are projections validated across tick, 1m, 5m, 15m, 1h, and session windows?",
            "state": "ready" if projection_interval_validation.get("action_influence_allowed") else "blocked",
            "proof": (
                f"fresh_rows={signal_freshness_matrix.get('fresh_row_count')}/{signal_freshness_matrix.get('row_count')} "
                f"validated_intervals={projection_interval_validation.get('validated_interval_count')}/"
                f"{projection_interval_validation.get('required_interval_count')} "
                f"hit_rate={projection_interval_validation.get('hit_rate')}"
            ),
        },
        {
            "id": "dynamic_gold_market_edge_stream",
            "question": "Is Aureon dynamically streaming GOLD and related tickers for a fresh waveform edge?",
            "state": "ready" if (dynamic_market_edge_stream.get("action_candidate") or {}).get("shadow_intent_allowed") else "blocked",
            "proof": (
                f"edge_score={dynamic_market_edge_stream.get('edge_score')} "
                f"fresh_streams={dynamic_market_edge_stream.get('fresh_stream_count')}/"
                f"{dynamic_market_edge_stream.get('stream_lane_count')} "
                f"waveform={dynamic_market_edge_stream.get('waveform_state')} "
                f"next={dynamic_market_edge_stream.get('next_action')}"
            ),
        },
        {
            "id": "gold_hnc_history_future_bridge",
            "question": "Does validated GOLD history show the next future path through HNC/Auris?",
            "state": "ready" if hnc_history_future_bridge.get("action_influence_allowed") else "blocked",
            "proof": (
                f"memory_score={hnc_history_future_bridge.get('historical_memory_score')} "
                f"validated_history={hnc_history_future_bridge.get('validated_history_count')} "
                f"hit_rate={hnc_history_future_bridge.get('historical_hit_rate')} "
                f"future={hnc_history_future_bridge.get('future_claim_state')}"
            ),
        },
        {
            "id": "gold_creative_dream_hypothesis_engine",
            "question": "Is Aureon generating many creative GOLD edge hypotheses and forcing them into validation?",
            "state": "ready" if _num(creative_dream_hypothesis_engine.get("dream_count")) >= 10 else "blocked",
            "proof": (
                f"dreams={creative_dream_hypothesis_engine.get('dream_count')} "
                f"ready={creative_dream_hypothesis_engine.get('ready_dream_count')} "
                f"creativity={creative_dream_hypothesis_engine.get('average_creativity_score')} "
                "authority=idea_only_until_validated"
            ),
        },
        {
            "id": "gold_probability_projection_forecast",
            "question": "Is the GOLD forecast a calibrated probability with validated claims and no fake certainty?",
            "state": "ready" if (probability_projection_forecast.get("truth_discipline") or {}).get("truth_claim_allowed") else "blocked",
            "proof": (
                f"direction={(probability_projection_forecast.get('forecast_distribution') or {}).get('calibrated_direction')} "
                f"confidence={(probability_projection_forecast.get('forecast_distribution') or {}).get('calibrated_confidence')} "
                f"truth={(probability_projection_forecast.get('truth_discipline') or {}).get('truth_status')}"
            ),
        },
        {
            "id": "gold_hnc_action_coherence_gate",
            "question": "Is HNC/Auris acting as a coherence weapon only after fresh ticker and interval proof?",
            "state": "ready" if hnc_action_coherence_gate.get("action_coherence_allowed") else "blocked",
            "proof": (
                f"effect={hnc_action_coherence_gate.get('confidence_effect')} "
                f"auris={hnc_action_coherence_gate.get('auris_node_count')} "
                f"blockers={len(hnc_action_coherence_gate.get('blockers') or [])}"
            ),
        },
        {
            "id": "gold_portfolio_uplift_guard",
            "question": "Can the validated setup plausibly increase portfolio value after 3p floor, spread, slippage, fees, and risk?",
            "state": "ready" if portfolio_uplift_guard.get("order_intent_consideration_allowed") else "blocked",
            "proof": (
                f"shadow_pl={portfolio_uplift_guard.get('validated_shadow_p_l_effect')} "
                f"estimated_net={portfolio_uplift_guard.get('estimated_net_at_suggested_size')} "
                f"blockers={len(portfolio_uplift_guard.get('blockers') or [])}"
            ),
        },
        {
            "id": "gold_historical_stress_test",
            "question": "Did GOLD/XAU historical replay validate the prediction logic before handover?",
            "state": "ready" if historical_stress_test.get("stress_passed") else "blocked",
            "proof": (
                f"rows={(historical_stress_test.get('prediction_validation') or {}).get('row_count')} "
                f"validated={(historical_stress_test.get('prediction_validation') or {}).get('validated_count')} "
                f"hit_rate={(historical_stress_test.get('prediction_validation') or {}).get('hit_rate')}"
            ),
        },
        {
            "id": "gold_margin_trader_unity",
            "question": "Are the margin trader, sizing, risk, profit, and position monitors unified around Capital GOLD?",
            "state": "ready" if margin_trader_unity.get("unity_state") == "gold_margin_unity_shadow_ready" else "blocked",
            "proof": (
                f"state={margin_trader_unity.get('unity_state')} "
                f"surfaces={margin_trader_unity.get('present_surface_count')}/{margin_trader_unity.get('surface_count')} "
                f"blockers={len(margin_trader_unity.get('blockers') or [])}"
            ),
        },
        {
            "id": "three_p_floor",
            "question": "Can the setup clear at least 3p net after spread and slippage?",
            "state": floor_state,
            "proof": f"Required move at min size: {three_p_gate.get('minimum_price_move_for_floor_at_min_size')}.",
        },
        {
            "id": "runtime_risk_gate",
            "question": "Are live runtime and risk gates clear?",
            "state": "blocked" if blockers else "ready",
            "proof": "Existing runtime, risk, credential, and exchange gates remain authoritative.",
        },
    ]
    blocked_chain = [item for item in proof_chain if str(item.get("state")).lower().startswith("blocked") or "attention" in str(item.get("state")).lower() or "hold" in str(item.get("state")).lower()]
    if floor_side in {"BUY", "SELL"} and not blocked_chain:
        act_state = f"shadow_validate_{floor_side.lower()}_candidate"
        act_instruction = f"Shadow-validate {floor_side} only; live execution remains separately gated."
    else:
        act_state = "hold_gather_replay"
        act_instruction = "Hold; gather fresh GOLD proof, replay the story, and do not enter until the 3p floor is proven."

    return {
        "status": "gold_action_command_attention" if blocked_chain else "gold_action_command_shadow_ready",
        "generated_at": generated_at,
        "who": {
            "commander": "Gold Strategy Steward",
            "field_agents": [agent.get("role") for agent in (swarm_intelligence.get("agents") or [])],
            "active_agent_count": len(active_agents),
            "attention_agent_count": len(attention_agents),
        },
        "what": {
            "mission": "Answer one question: what is the best allowed action on Capital GOLD right now?",
            "profit_floor": three_p_gate.get("profit_floor_label"),
            "target": "Capital.com GOLD",
            "not_financial_advice": True,
        },
        "when": {
            "current_window": act_state,
            "open_conditions": [
                "Capital GOLD quote and OHLC are fresh.",
                "Cross-market drivers align without unresolved contradiction.",
                "Direct GOLD pressure or equivalent timing proof is present.",
                "The setup clears at least 3p net after spread and slippage.",
                "Runtime, risk, credential, and exchange gates are clear.",
            ],
            "close_conditions": [
                "Freshness expires.",
                "Driver story breaks or contradicts.",
                "3p net floor is no longer mathematically available.",
                "Runtime/risk/manual authority gate blocks action.",
            ],
        },
        "how": {
            "data_story": [
                "Capital GOLD bid/ask and OHLC define the battlefield.",
                "DXY/rates/oil/VIX/equities/crypto/geopolitics explain why the move may be happening.",
                "Waveform and scanner fusion test whether the move is normal, stretched, or reversing.",
                "Order-book pressure times the entry only after direct proof exists.",
                "HNC/Auris and counter-intelligence lower confidence when evidence is stale or contradictory.",
            ],
            "ready_driver_ids": [str(driver.get("id")) for driver in ready_drivers],
            "weak_driver_ids": [str(driver.get("id")) for driver in weak_drivers],
            "priority_tasks": [str(item.get("id")) for item in (gold_priority_workbench.get("data_priority_queue") or [])],
        },
        "act": {
            "state": act_state,
            "instruction": act_instruction,
            "side": floor_side,
            "entry_level": three_p_gate.get("entry_level"),
            "target_level": three_p_gate.get("target_level"),
            "stop_level": three_p_gate.get("stop_level"),
            "suggested_shadow_size": three_p_gate.get("suggested_shadow_size"),
            "live_order_allowed": False,
            "order_mutation_allowed": False,
        },
        "proof_chain": proof_chain,
        "blocking_items": [
            {"id": str(item.get("id")), "state": str(item.get("state")), "proof": str(item.get("proof"))}
            for item in blocked_chain
        ],
        "command_systems": command_systems,
        "standing_orders": [
            "Gather and replay first; act only after proof, never from excitement.",
            "The 3p net floor is the minimum; if it is not proven, HOLD.",
            "Use repo intelligence as source-linked evidence, not vibes.",
            "Live trading, credentials, payments, filings, and destructive actions remain outside this autonomous lane.",
        ],
    }


def _extract_shadow_focus_items(payload: Dict[str, Any], *, source: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for item in _walk_dicts(payload):
        symbol = str(
            item.get("symbol")
            or item.get("route_symbol")
            or item.get("raw_symbol")
            or item.get("epic")
            or ""
        ).strip()
        pressure = item.get("orderbook_pressure") if isinstance(item.get("orderbook_pressure"), dict) else {}
        fast_money = item.get("fast_money_profile") if isinstance(item.get("fast_money_profile"), dict) else {}
        side = str(item.get("side") or item.get("direction") or pressure.get("pressure_side") or "").upper()
        has_trade_shape = bool(
            symbol
            and (
                side
                or item.get("confidence") is not None
                or item.get("scanner_fusion_score") is not None
                or item.get("orderbook_score") is not None
                or pressure
                or fast_money
            )
        )
        if not has_trade_shape:
            continue
        relation = _gold_shadow_context_relation(
            symbol,
            item.get("venue"),
            item.get("route_signature"),
            item.get("selection_basis"),
            item.get("reason"),
            item.get("category"),
            item.get("active_scanners"),
            pressure,
        )
        orderbook_score = item.get("orderbook_score")
        if orderbook_score is None:
            orderbook_score = fast_money.get("orderbook_score")
        if orderbook_score is None:
            orderbook_score = pressure.get("score")
        confidence = _num(item.get("confidence"), _num(item.get("scanner_fusion_score"), _num(orderbook_score)))
        key = f"{source}:{symbol.upper()}:{side}:{relation}"
        if key in seen:
            continue
        seen.add(key)
        items.append(
            {
                "source": source,
                "symbol": symbol,
                "venue": item.get("venue"),
                "side": side or "CONTEXT",
                "confidence": round(_clamp(confidence), 4),
                "scanner_fusion_score": round(_num(item.get("scanner_fusion_score")), 4),
                "orderbook_score": round(_num(orderbook_score), 4),
                "orderbook_alignment": item.get("orderbook_alignment") or fast_money.get("orderbook_alignment"),
                "relation_to_gold": relation,
                "promotion_use": "target_candidate" if relation == "gold_target_candidate" else "context_only" if relation != "excluded_generic_shadow" else "excluded",
                "mutation_allowed": False,
            }
        )
    items.sort(
        key=lambda item: (
            item["relation_to_gold"] != "gold_target_candidate",
            item["relation_to_gold"] == "excluded_generic_shadow",
            -_num(item.get("confidence")),
            str(item.get("symbol")),
        )
    )
    return items[:40]


def _build_gold_shadow_trading_focus(
    *,
    shadow_report: Dict[str, Any],
    scanner_fusion: Dict[str, Any],
    decision: Dict[str, Any],
    three_p_gate: Dict[str, Any],
    verified_data_gate: Dict[str, Any],
    gold_action_command: Dict[str, Any],
    cognitive_route: Dict[str, Any],
    hft_speed_gate: Dict[str, Any],
    historical_stress_test: Dict[str, Any],
    cross_market_driver_matrix: List[Dict[str, Any]],
    generated_at: str,
) -> Dict[str, Any]:
    shadow_items = _extract_shadow_focus_items(shadow_report, source="unified_shadow_trade_report")
    scanner_items = _extract_shadow_focus_items(scanner_fusion, source="scanner_fusion_matrix")
    all_items = shadow_items + scanner_items
    target_candidates = [item for item in all_items if item.get("relation_to_gold") == "gold_target_candidate"]
    context_items = [
        item
        for item in all_items
        if item.get("relation_to_gold") not in {"gold_target_candidate", "excluded_generic_shadow"}
    ]
    excluded_items = [item for item in all_items if item.get("relation_to_gold") == "excluded_generic_shadow"]
    drivers_by_id = {str(driver.get("id")): driver for driver in cross_market_driver_matrix}
    lane_specs = [
        ("capital_gold_cfd", "Capital GOLD target lane", "target"),
        ("oil_energy_inflation", "Oil and energy stress lane", "energy_associated_context"),
        ("usd_dxy_fx", "USD, DXY, and FX pressure lane", "confirmation_context"),
        ("rates_inflation_macro", "Rates, yields, and inflation lane", "confirmation_context"),
        ("gold_etfs_miners", "Gold ETFs and miners lane", "confirmation_context"),
        ("equity_risk_vix", "Equity risk and VIX lane", "confirmation_context"),
        ("crypto_liquidity_safe_haven", "Crypto liquidity rotation lane", "confirmation_context"),
        ("geopolitical_news_sentiment", "Geopolitics, news, and sentiment lane", "confirmation_context"),
        ("historical_waveform_memory", "Historical waveform memory lane", "timing_context"),
        ("hnc_auris_counter_intelligence", "HNC/Auris contradiction gate", "coherence_context"),
    ]
    energy_context_lanes: List[Dict[str, Any]] = []
    for driver_id, label, lane_role in lane_specs:
        driver = drivers_by_id.get(driver_id, {})
        energy_context_lanes.append(
            {
                "id": driver_id,
                "label": label,
                "lane_role": lane_role,
                "driver_state": driver.get("driver_state") or "missing_driver",
                "score": driver.get("score"),
                "fresh": bool(driver.get("fresh")),
                "next_action": driver.get("next_action") or "Refresh source-linked context before using this lane.",
                "target_authority": "gold_target_only" if lane_role == "target" else "context_confirmation_only",
            }
        )

    promotion_blockers: List[Dict[str, Any]] = []
    if not target_candidates:
        promotion_blockers.append({"id": "gold_shadow_candidate_missing", "reason": "No GOLD/XAU/Capital GOLD shadow candidate is present."})
    if not decision.get("shadow_observation_allowed"):
        promotion_blockers.append({"id": "shadow_observation_not_allowed", "reason": "Trading intelligence does not currently trust the shadow lane."})
    if not verified_data_gate.get("action_allowed_by_data"):
        promotion_blockers.append({"id": "verified_real_data_gate_blocking", "reason": "Fresh real-data proof has not passed for GOLD promotion."})
    if str(three_p_gate.get("state")) != "shadow_trade_candidate":
        promotion_blockers.append({"id": "three_p_floor_not_proven", "reason": "The 3p net floor is not mathematically proven for a shadow candidate."})
    if not cognitive_route.get("route_passed"):
        promotion_blockers.append({"id": "hnc_auris_quantum_probability_route_blocking", "reason": "Auris nodes, lambda, HNC, quantum, and probability route is not fully passing."})
    if not hft_speed_gate.get("gate_passed"):
        promotion_blockers.append({"id": "hft_speed_prediction_gate_blocking", "reason": "Fast GOLD prediction path is not fresh, outcome-validated, and latency-proven."})
    if not historical_stress_test.get("stress_passed"):
        promotion_blockers.append({"id": "gold_historical_stress_test_blocking", "reason": "Historical GOLD/XAU replay has not proven the prediction logic yet."})
    act_state = str((gold_action_command.get("act") or {}).get("state") or "")
    if not act_state.startswith("shadow_validate_"):
        promotion_blockers.append({"id": "gold_action_command_hold", "reason": f"Gold action command is {act_state or 'held'}."})

    status = "gold_energy_shadow_focus_ready"
    if not target_candidates:
        status = "gold_energy_shadow_focus_waiting_for_gold_candidate"
    elif promotion_blockers:
        status = "gold_energy_shadow_focus_blocked_for_fresh_data"
    floor_side = str(three_p_gate.get("side") or "HOLD")
    promotion_state = "shadow_candidate_ready" if status == "gold_energy_shadow_focus_ready" else "held_until_verified_real_data"
    return {
        "status": status,
        "generated_at": generated_at,
        "mode": "gold_and_gold_energy_only_shadow_validation",
        "target_symbol": "GOLD",
        "target_venue": "Capital.com",
        "target_epic": "GOLD",
        "target_only": True,
        "cognitive_route_status": cognitive_route.get("status"),
        "hft_speed_prediction_gate_status": hft_speed_gate.get("status"),
        "historical_stress_status": historical_stress_test.get("status"),
        "allowed_shadow_universe": [
            "Capital GOLD / XAU direct target",
            "Gold futures and GLD/IAU/GDX/GDXJ confirmation",
            "Oil, Brent, WTI, gas, and energy stress confirmation",
            "USD, DXY, rates, yields, inflation, and macro calendar",
            "VIX, indices, stocks, ETF breadth, and risk appetite",
            "BTC/crypto liquidity and safe-haven rotation",
            "Geopolitics, news, sanctions, and sentiment",
            "Direct GOLD order-book, OHLC, scanner, and waveform proof",
        ],
        "focus_rules": [
            "Only GOLD/XAU/Capital GOLD can become a shadow trade target while this focus mode is active.",
            "Oil and energy symbols are context/confirmation lanes for GOLD, not independent trade targets in this mode.",
            "USD/rates, ETFs/miners, VIX, crypto, and geopolitics can confirm or contradict the GOLD thesis.",
            "Generic non-gold shadows are excluded from the active candidate lane and kept out of promotion.",
            "Verified real-data freshness and the 3p net floor must pass before any GOLD shadow candidate is promoted.",
            "Auris nodes, lambda history, HNC proof, quantum context, and probability rows must be accounted for before promotion.",
            "High-frequency promotion requires fresh latency checks and outcome-validated GOLD/XAU predictions.",
            "Historical stress replay must prove the GOLD/XAU prediction logic before any handover-ready claim.",
            "Live orders remain blocked by existing runtime, credential, risk, and execution gates.",
        ],
        "energy_context_lanes": energy_context_lanes,
        "shadow_candidates": target_candidates[:8],
        "context_only_shadow_items": context_items[:8],
        "excluded_shadow_items": excluded_items[:8],
        "gold_related_shadow_count": len(target_candidates),
        "context_shadow_count": len(context_items),
        "excluded_shadow_count": len(excluded_items),
        "promotion_gate": {
            "state": promotion_state,
            "side": floor_side,
            "entry_level": three_p_gate.get("entry_level"),
            "target_level": three_p_gate.get("target_level"),
            "suggested_shadow_size": three_p_gate.get("suggested_shadow_size"),
            "verified_real_data_status": verified_data_gate.get("status"),
            "three_p_floor_state": three_p_gate.get("state"),
            "historical_stress_status": historical_stress_test.get("status"),
            "live_order_allowed": False,
            "order_mutation_allowed": False,
            "blockers": promotion_blockers[:12],
        },
        "who_what_where_when_how_act": {
            "who": "Gold Shadow Trade Validator with Macro Rates Reader, Capital GOLD Collector, and HNC/Auris Gate",
            "what": "Keep the shadow trading lane focused on GOLD as the only target, using energy and connected markets as evidence.",
            "where": [str(SOURCE_PATHS["shadow_trade_report"]), str(SOURCE_PATHS["scanner_fusion_matrix"]), str(SOURCE_PATHS["trading_intelligence"])],
            "when": generated_at,
            "how": "Filter every shadow candidate through relation_to_gold, exclude generic symbols, retain energy/context lanes, then apply real-data and 3p gates.",
            "act": "shadow_validate_gold_only" if status == "gold_energy_shadow_focus_ready" else "hold_refresh_gold_energy_evidence",
        },
    }


def _build_gold_live_stream_command_deck(
    *,
    asset: Dict[str, Any],
    runtime: Dict[str, Any],
    exchange_matrix: Dict[str, Any],
    exchange_monitoring: Dict[str, Any],
    trading_intel: Dict[str, Any],
    gold_action_command: Dict[str, Any],
    gold_shadow_trading_focus: Dict[str, Any],
    gold_ticker_source_mesh: Dict[str, Any],
    gold_signal_freshness_matrix: Dict[str, Any],
    gold_projection_interval_validation: Dict[str, Any],
    gold_dynamic_market_edge_stream: Dict[str, Any],
    gold_hnc_action_coherence_gate: Dict[str, Any],
    gold_portfolio_uplift_guard: Dict[str, Any],
    gold_margin_trader_unity: Dict[str, Any],
    historical_signal_lab: Dict[str, Any],
    three_p_gate: Dict[str, Any],
    snapshot_age: Optional[float],
    snapshot_fresh: bool,
    runtime_stale: bool,
    generated_at: str,
) -> Dict[str, Any]:
    exchange_rows = _rows_by_key(exchange_matrix, "exchange")
    monitoring_rows = _rows_by_key(exchange_monitoring, "exchange")
    capital_exchange = exchange_rows.get("capital") or _find_row(exchange_matrix, "capital.com")
    capital_monitoring = monitoring_rows.get("capital") or _find_row(exchange_monitoring, "capital.com")
    capital_state = capital_exchange.get("current_state") if isinstance(capital_exchange.get("current_state"), dict) else {}
    trading_summary = _summary(trading_intel)
    live_stream_cache = trading_summary.get("live_stream_cache") if isinstance(trading_summary.get("live_stream_cache"), dict) else {}
    metacognitive_context = trading_summary.get("metacognitive_data_context") if isinstance(trading_summary.get("metacognitive_data_context"), dict) else {}
    action = gold_action_command.get("act") if isinstance(gold_action_command.get("act"), dict) else {}
    proof_blockers = gold_action_command.get("blocking_items") if isinstance(gold_action_command.get("blocking_items"), list) else []
    projection_intervals = gold_projection_interval_validation.get("intervals") if isinstance(gold_projection_interval_validation.get("intervals"), list) else []
    ticker_lanes = gold_ticker_source_mesh.get("lanes") if isinstance(gold_ticker_source_mesh.get("lanes"), list) else []
    signal_rows = gold_signal_freshness_matrix.get("rows") if isinstance(gold_signal_freshness_matrix.get("rows"), list) else []
    edge_candidate = gold_dynamic_market_edge_stream.get("action_candidate") if isinstance(gold_dynamic_market_edge_stream.get("action_candidate"), dict) else {}

    next_target = "refresh_capital_gold_stream"
    if _num(gold_ticker_source_mesh.get("fresh_lane_count")) <= 0:
        next_target = "refresh_gold_ticker_source_mesh"
    elif not gold_projection_interval_validation.get("action_influence_allowed"):
        next_target = "validate_gold_projection_intervals"
    elif not edge_candidate.get("shadow_intent_allowed"):
        next_target = str(gold_dynamic_market_edge_stream.get("next_action") or "watch_dynamic_gold_market_edge")
    elif not gold_hnc_action_coherence_gate.get("action_coherence_allowed"):
        next_target = "feed_fresh_proof_back_to_hnc"
    elif not gold_portfolio_uplift_guard.get("order_intent_consideration_allowed"):
        next_target = "prove_portfolio_uplift_and_3p_floor"
    elif str(action.get("state") or "").startswith("shadow_validate_"):
        next_target = "shadow_validate_capital_gold_candidate"

    now_state = str(action.get("state") or "hold_gather_replay")
    act_result = "held_for_fresh_proof" if proof_blockers else "shadow_ready_runtime_gated"
    stream_channels = [
        {
            "id": "capital_gold_profile",
            "label": "Capital GOLD profile",
            "status": "fresh" if snapshot_fresh else "stale",
            "fresh": snapshot_fresh,
            "age_seconds": round(snapshot_age, 3) if snapshot_age is not None else None,
            "source": str(SOURCE_PATHS["capital_asset_registry"]),
            "next_action": "Refresh Capital GOLD bid/ask/OHLC/profile if stale.",
        },
        {
            "id": "capital_live_ticks",
            "label": "Capital live ticks",
            "status": _channel_status(capital_exchange, "live_ticks"),
            "fresh": _channel_status(capital_exchange, "live_ticks").lower() in {"fresh", "active", "available"},
            "age_seconds": capital_monitoring.get("age_sec"),
            "source": str(SOURCE_PATHS["exchange_monitoring"]),
            "next_action": "Keep Capital stream and quote cache fresh for GOLD.",
        },
        {
            "id": "capital_price_history",
            "label": "Capital price history",
            "status": _channel_status(capital_exchange, "price_history"),
            "fresh": _channel_status(capital_exchange, "price_history").lower() in {"fresh", "active", "available", "configured"},
            "age_seconds": None,
            "source": str(SOURCE_PATHS["exchange_data_matrix"]),
            "next_action": "Replay Capital GOLD 1m/5m/15m/1h/session bars.",
        },
        {
            "id": "multi_exchange_live_stream_cache",
            "label": "Live stream cache",
            "status": "fresh" if live_stream_cache.get("fresh") else "held",
            "fresh": bool(live_stream_cache.get("fresh")),
            "age_seconds": live_stream_cache.get("max_age_sec"),
            "source": str(SOURCE_PATHS["trading_intelligence"]),
            "next_action": "Use stream cache as context only until GOLD ticker source mesh is fresh.",
        },
        {
            "id": "gold_projection_intervals",
            "label": "Projection interval validation",
            "status": gold_projection_interval_validation.get("status"),
            "fresh": bool(gold_projection_interval_validation.get("action_influence_allowed")),
            "age_seconds": None,
            "source": "gold_projection_interval_validation",
            "next_action": "Fill and validate tick, 1m, 5m, 15m, 1h, and session rows.",
        },
        {
            "id": "dynamic_gold_edge_stream",
            "label": "Dynamic GOLD edge stream",
            "status": gold_dynamic_market_edge_stream.get("edge_state"),
            "fresh": bool(edge_candidate.get("shadow_intent_allowed")),
            "age_seconds": None,
            "source": "gold_dynamic_market_edge_stream",
            "next_action": gold_dynamic_market_edge_stream.get("next_action") or "Keep streaming GOLD and related context lanes.",
        },
        {
            "id": "hnc_auris_feedback",
            "label": "HNC/Auris feedback",
            "status": gold_hnc_action_coherence_gate.get("status"),
            "fresh": bool(gold_hnc_action_coherence_gate.get("action_coherence_allowed")),
            "age_seconds": None,
            "source": "gold_hnc_action_coherence_gate",
            "next_action": "Feed fresh signal and interval proof back into HNC/Auris before confidence can rise.",
        },
    ]
    chart_streams = [
        {
            "id": "capital_price_band",
            "label": "Capital GOLD bid/mid/ask",
            "chart_type": "price_band",
            "points": [
                {"label": "bid", "value": asset.get("bid")},
                {"label": "mid", "value": asset.get("mid_price")},
                {"label": "ask", "value": asset.get("ask")},
            ],
            "fresh": snapshot_fresh,
            "source": str(SOURCE_PATHS["capital_asset_registry"]),
        },
        {
            "id": "freshness_pressure",
            "label": "Freshness pressure",
            "chart_type": "bar_ratio",
            "points": [
                {"label": "ticker lanes", "value": gold_ticker_source_mesh.get("fresh_lane_count"), "max": gold_ticker_source_mesh.get("lane_count")},
                {"label": "signal rows", "value": gold_signal_freshness_matrix.get("fresh_row_count"), "max": gold_signal_freshness_matrix.get("row_count")},
                {"label": "validated intervals", "value": gold_projection_interval_validation.get("validated_interval_count"), "max": gold_projection_interval_validation.get("required_interval_count")},
            ],
            "fresh": bool(gold_signal_freshness_matrix.get("action_influence_allowed")),
            "source": "gold_signal_freshness_matrix",
        },
        {
            "id": "projection_interval_results",
            "label": "Projection interval results",
            "chart_type": "interval_status",
            "points": [
                {
                    "label": interval.get("id"),
                    "value": 1 if interval.get("hit_miss") == "hit" else -1 if interval.get("hit_miss") == "miss" else 0,
                    "hit_miss": interval.get("hit_miss"),
                    "shadow_p_l_effect": interval.get("shadow_p_l_effect"),
                }
                for interval in projection_intervals
            ],
            "fresh": bool(gold_projection_interval_validation.get("action_influence_allowed")),
            "source": "gold_projection_interval_validation",
        },
        {
            "id": "hnc_feedback_state",
            "label": "HNC/Auris feedback state",
            "chart_type": "coherence_bar",
            "points": [
                {"label": "auris coherence", "value": gold_hnc_action_coherence_gate.get("auris_coherence"), "max": 1},
                {"label": "portfolio shadow P/L", "value": gold_portfolio_uplift_guard.get("validated_shadow_p_l_effect"), "max": 0.03},
            ],
            "fresh": bool(gold_hnc_action_coherence_gate.get("action_coherence_allowed")),
            "source": "gold_hnc_action_coherence_gate",
        },
        {
            "id": "dynamic_edge_score",
            "label": "Dynamic GOLD edge score",
            "chart_type": "edge_score",
            "points": [
                {"label": "edge score", "value": gold_dynamic_market_edge_stream.get("edge_score"), "max": 1},
                {"label": "fresh streams", "value": gold_dynamic_market_edge_stream.get("fresh_stream_count"), "max": gold_dynamic_market_edge_stream.get("stream_lane_count")},
                {"label": "context streams", "value": gold_dynamic_market_edge_stream.get("context_fresh_count"), "max": max(1, _num(gold_dynamic_market_edge_stream.get("stream_lane_count")) - 1)},
            ],
            "fresh": bool(edge_candidate.get("shadow_intent_allowed")),
            "source": "gold_dynamic_market_edge_stream",
        },
    ]
    feedback_packet = {
        "who": "GOLD live stream command deck feeding HNC/Auris",
        "what": "Send fresh source, interval validation, action blockers, margin/leverage profile, and portfolio uplift proof back into coherence scoring.",
        "where": [
            "gold_ticker_source_mesh",
            "gold_signal_freshness_matrix",
            "gold_projection_interval_validation",
            "gold_dynamic_market_edge_stream",
            "gold_portfolio_uplift_guard",
            "gold_margin_trader_unity",
        ],
        "when": generated_at,
        "how": "HNC/Auris can only raise confidence after fresh lanes and interval validation pass; otherwise it receives blockers and lowers or holds confidence.",
        "act": "feed_hnc_blockers" if proof_blockers else "feed_hnc_shadow_ready_state",
    }
    blockers: List[Dict[str, Any]] = []
    if runtime_stale:
        blockers.append({"id": "runtime_stale", "reason": "Runtime is stale, so live stream analytics are observe-only."})
    if not snapshot_fresh:
        blockers.append({"id": "capital_gold_profile_stale", "reason": "Capital GOLD profile/snapshot is not fresh enough."})
    if not gold_signal_freshness_matrix.get("action_influence_allowed"):
        blockers.append({"id": "fresh_signal_matrix_blocking", "reason": "Fresh signal matrix blocks action influence."})
    if not gold_projection_interval_validation.get("action_influence_allowed"):
        blockers.append({"id": "projection_interval_validation_blocking", "reason": "Projection intervals are not fully validated."})
    if not gold_portfolio_uplift_guard.get("order_intent_consideration_allowed"):
        blockers.append({"id": "portfolio_uplift_guard_blocking", "reason": "Portfolio uplift guard blocks order-intent consideration."})

    return {
        "status": "gold_live_stream_command_deck_ready" if not blockers else "gold_live_stream_command_deck_attention",
        "generated_at": generated_at,
        "mode": "read_only_live_gold_stream_analytics",
        "refresh_hint_ms": 2_500,
        "target": {
            "symbol": asset.get("symbol") or "GOLD",
            "epic": asset.get("epic") or "GOLD",
            "venue": "Capital.com",
            "targeting_state": next_target,
        },
        "what_am_i_doing_now": {
            "state": now_state,
            "instruction": action.get("instruction") or "Hold; gather fresh GOLD proof.",
            "current_result": act_result,
        },
        "what_am_i_doing_next": {
            "targeting": next_target,
            "next_refresh_action": next((channel["next_action"] for channel in stream_channels if not channel.get("fresh")), "Keep validating GOLD shadow route."),
        },
        "what_will_i_act_on": {
            "candidate": "Capital GOLD",
            "side": edge_candidate.get("side") or action.get("side") or three_p_gate.get("side") or "HOLD",
            "entry_level": action.get("entry_level"),
            "target_level": action.get("target_level"),
            "allowed_action": "shadow_validate_only" if str(now_state).startswith("shadow_validate_") else "hold_refresh_validate",
            "live_order_allowed": False,
            "order_mutation_allowed": False,
        },
        "act_result": {
            "state": act_result,
            "blocking_count": len(proof_blockers) + len(blockers),
            "latest_blockers": (proof_blockers[:6] + blockers[:6])[:8],
        },
        "capital_data_profile": {
            "market_status": asset.get("market_status"),
            "trade_ready": bool(asset.get("trade_ready")),
            "bid": asset.get("bid"),
            "ask": asset.get("ask"),
            "mid_price": asset.get("mid_price"),
            "spread": asset.get("spread"),
            "spread_pct": asset.get("spread_pct"),
            "last_snapshot_at": asset.get("last_snapshot_at"),
            "snapshot_age_seconds": round(snapshot_age, 3) if snapshot_age is not None else None,
            "snapshot_fresh": snapshot_fresh,
            "minimum_deal_size": asset.get("minimum_deal_size"),
            "can_buy_profile_visible": bool(asset.get("can_buy")),
            "can_sell_profile_visible": bool(asset.get("can_sell")),
        },
        "leverage_margin_status": {
            "leverage_estimate": asset.get("leverage_estimate"),
            "margin_factor_pct": asset.get("margin_factor_pct"),
            "margin_required_for_min_deal": asset.get("margin_required_for_min_deal"),
            "min_notional_estimate": asset.get("min_notional_estimate"),
            "margin_unity_state": gold_margin_trader_unity.get("unity_state"),
            "margin_order_allowed": False,
            "leverage_change_allowed": False,
        },
        "live_stream_profile": {
            "runtime_stale": runtime_stale,
            "runtime_stale_reason": runtime.get("stale_reason") or trading_summary.get("stale_reason"),
            "live_stream_cache": live_stream_cache,
            "metacognitive_data_context": metacognitive_context,
            "capital_exchange_state": capital_state,
            "capital_monitoring": capital_monitoring,
        },
        "stream_channels": stream_channels,
        "chart_streams": chart_streams,
        "hnc_feedback_loop": feedback_packet,
        "dynamic_market_edge_stream": {
            "status": gold_dynamic_market_edge_stream.get("status"),
            "edge_state": gold_dynamic_market_edge_stream.get("edge_state"),
            "edge_score": gold_dynamic_market_edge_stream.get("edge_score"),
            "action_candidate": edge_candidate,
            "next_action": gold_dynamic_market_edge_stream.get("next_action"),
            "blocker_count": len(gold_dynamic_market_edge_stream.get("blockers") or []),
        },
        "shadow_focus_state": {
            "status": gold_shadow_trading_focus.get("status"),
            "candidate_count": gold_shadow_trading_focus.get("gold_related_shadow_count"),
            "promotion_state": (gold_shadow_trading_focus.get("promotion_gate") or {}).get("state"),
        },
        "historical_chart_state": {
            "chart_replay_state": historical_signal_lab.get("chart_replay_state"),
            "orderbook_signal_state": historical_signal_lab.get("orderbook_signal_state"),
            "waveform_replay_state": historical_signal_lab.get("waveform_replay_state"),
        },
        "signal_sample": signal_rows[:8],
        "blockers": blockers[:12],
        "manual_boundaries": [
            "Charts and analytics are read-only operator evidence.",
            "Capital order, leverage, and margin mutation remain runtime-gated outside this report.",
            "HNC/Auris receives blockers and proof, not permission to bypass freshness gates.",
        ],
    }


def _build_gold_margin_signal_action_loop(
    *,
    decision: Dict[str, Any],
    three_p_gate: Dict[str, Any],
    verified_data_gate: Dict[str, Any],
    gold_signal_freshness_matrix: Dict[str, Any],
    gold_projection_interval_validation: Dict[str, Any],
    gold_hnc_action_coherence_gate: Dict[str, Any],
    gold_portfolio_uplift_guard: Dict[str, Any],
    gold_margin_trader_unity: Dict[str, Any],
    gold_action_command: Dict[str, Any],
    gold_live_stream_command_deck: Dict[str, Any],
    gold_dynamic_market_edge_stream: Dict[str, Any],
    cognitive_route: Dict[str, Any],
    hft_speed_gate: Dict[str, Any],
    historical_stress_test: Dict[str, Any],
    runtime_stale: bool,
    snapshot_fresh: bool,
    generated_at: str,
) -> Dict[str, Any]:
    action = gold_action_command.get("act") if isinstance(gold_action_command.get("act"), dict) else {}
    live_deck_act = gold_live_stream_command_deck.get("what_will_i_act_on") if isinstance(gold_live_stream_command_deck.get("what_will_i_act_on"), dict) else {}
    hnc_feedback = gold_live_stream_command_deck.get("hnc_feedback_loop") if isinstance(gold_live_stream_command_deck.get("hnc_feedback_loop"), dict) else {}
    margin_command = gold_margin_trader_unity.get("margin_command") if isinstance(gold_margin_trader_unity.get("margin_command"), dict) else {}
    projection_intervals = gold_projection_interval_validation.get("intervals") if isinstance(gold_projection_interval_validation.get("intervals"), list) else []
    edge_candidate = gold_dynamic_market_edge_stream.get("action_candidate") if isinstance(gold_dynamic_market_edge_stream.get("action_candidate"), dict) else {}

    pipeline = [
        {
            "id": "fresh_signal_matrix",
            "label": "Fresh Signal Matrix",
            "system": "gold_signal_freshness_matrix",
            "ready": bool(gold_signal_freshness_matrix.get("action_influence_allowed")),
            "state": gold_signal_freshness_matrix.get("status"),
            "proof": (
                f"{gold_signal_freshness_matrix.get('fresh_row_count')}/"
                f"{gold_signal_freshness_matrix.get('row_count')} rows fresh; "
                f"{gold_signal_freshness_matrix.get('action_influence_row_count')} action rows."
            ),
        },
        {
            "id": "interval_projection_validation",
            "label": "Interval Projection Validation",
            "system": "gold_projection_interval_validation",
            "ready": bool(gold_projection_interval_validation.get("action_influence_allowed")),
            "state": gold_projection_interval_validation.get("status"),
            "proof": (
                f"{gold_projection_interval_validation.get('validated_interval_count')}/"
                f"{gold_projection_interval_validation.get('required_interval_count')} intervals validated; "
                f"hit_rate={gold_projection_interval_validation.get('hit_rate')}."
            ),
        },
        {
            "id": "dynamic_gold_edge_stream",
            "label": "Dynamic GOLD Edge Stream",
            "system": "gold_dynamic_market_edge_stream",
            "ready": bool(edge_candidate.get("shadow_intent_allowed")),
            "state": gold_dynamic_market_edge_stream.get("edge_state"),
            "proof": (
                f"edge_score={gold_dynamic_market_edge_stream.get('edge_score')} "
                f"fresh_streams={gold_dynamic_market_edge_stream.get('fresh_stream_count')}/"
                f"{gold_dynamic_market_edge_stream.get('stream_lane_count')} "
                f"candidate={edge_candidate.get('side') or 'HOLD'}."
            ),
        },
        {
            "id": "hnc_auris_nodes",
            "label": "HNC/Auris Nodes",
            "system": "hnc_auris_quantum_probability_route",
            "ready": bool(gold_hnc_action_coherence_gate.get("action_coherence_allowed") and cognitive_route.get("route_passed")),
            "state": gold_hnc_action_coherence_gate.get("status"),
            "proof": (
                f"auris_nodes={(cognitive_route.get('auris_nodes') or {}).get('node_count')} "
                f"coherence={(cognitive_route.get('auris_nodes') or {}).get('coherence')} "
                f"effect={gold_hnc_action_coherence_gate.get('confidence_effect')}."
            ),
        },
        {
            "id": "margin_unity",
            "label": "Margin Trader Unity",
            "system": "gold_margin_trader_unity",
            "ready": gold_margin_trader_unity.get("unity_state") == "gold_margin_unity_shadow_ready",
            "state": gold_margin_trader_unity.get("unity_state"),
            "proof": (
                f"{gold_margin_trader_unity.get('present_surface_count')}/"
                f"{gold_margin_trader_unity.get('surface_count')} margin surfaces present."
            ),
        },
        {
            "id": "portfolio_uplift_guard",
            "label": "Portfolio Uplift Guard",
            "system": "gold_portfolio_uplift_guard",
            "ready": bool(gold_portfolio_uplift_guard.get("order_intent_consideration_allowed")),
            "state": gold_portfolio_uplift_guard.get("status"),
            "proof": (
                f"shadow_pl={gold_portfolio_uplift_guard.get('validated_shadow_p_l_effect')} "
                f"net={gold_portfolio_uplift_guard.get('estimated_net_at_suggested_size')} "
                f"floor={three_p_gate.get('profit_floor_account_currency')}."
            ),
        },
        {
            "id": "gold_action_command",
            "label": "Action Command Stage",
            "system": "gold_action_command",
            "ready": str(action.get("state") or "").startswith("shadow_validate_"),
            "state": action.get("state"),
            "proof": action.get("instruction") or "Action command is holding until proof passes.",
        },
        {
            "id": "live_stream_feedback",
            "label": "Live Stream Feedback",
            "system": "gold_live_stream_command_deck",
            "ready": hnc_feedback.get("act") == "feed_hnc_shadow_ready_state",
            "state": hnc_feedback.get("act"),
            "proof": "Live deck feeds either blockers or shadow-ready state back into HNC/Auris.",
        },
    ]

    blockers: List[Dict[str, Any]] = []
    if runtime_stale:
        blockers.append({"id": "runtime_stale", "reason": "Runtime is stale, so margin action remains shadow/refresh only."})
    if not snapshot_fresh:
        blockers.append({"id": "capital_gold_snapshot_stale", "reason": "Capital GOLD snapshot is not fresh enough for margin sizing."})
    if not verified_data_gate.get("action_allowed_by_data"):
        blockers.append({"id": "verified_real_data_gate_blocking", "reason": "Verified real data gate blocks action influence."})
    if not hft_speed_gate.get("gate_passed"):
        blockers.append({"id": "hft_speed_prediction_gate_blocking", "reason": "Fast prediction path is not fresh/outcome-validated enough."})
    if not historical_stress_test.get("stress_passed"):
        blockers.append({"id": "gold_historical_stress_test_blocking", "reason": "Historical stress replay has not passed."})
    for stage in pipeline:
        if not stage.get("ready"):
            blockers.append(
                {
                    "id": f"{stage.get('id')}_not_ready",
                    "reason": f"{stage.get('label')} is {stage.get('state') or 'not ready'}; proof: {stage.get('proof')}",
                }
            )
    upstream_blockers = (
        (gold_signal_freshness_matrix.get("blockers") or [])
        + (gold_projection_interval_validation.get("blockers") or [])
        + (gold_dynamic_market_edge_stream.get("blockers") or [])
        + (gold_hnc_action_coherence_gate.get("blockers") or [])
        + (gold_portfolio_uplift_guard.get("blockers") or [])
        + (gold_margin_trader_unity.get("blockers") or [])
    )
    for blocker in upstream_blockers[:12]:
        blockers.append(
            {
                "id": str(blocker.get("id") or "upstream_blocker"),
                "reason": str(blocker.get("reason") or blocker.get("next_action") or "Upstream GOLD margin/action proof is blocking."),
            }
        )

    ready_stage_count = sum(1 for stage in pipeline if stage.get("ready"))
    all_stages_ready = ready_stage_count == len(pipeline)
    shadow_margin_intent_allowed = bool(all_stages_ready and not blockers)
    acting_state = "shadow_margin_intent_ready" if shadow_margin_intent_allowed else "refresh_validate_and_feed_hnc"
    if blockers and any(str(blocker.get("id", "")).startswith("hnc_auris") or "hnc" in str(blocker.get("id", "")).lower() for blocker in blockers):
        acting_state = "feed_hnc_auris_blockers"
    elif blockers and any("fresh" in str(blocker.get("id", "")).lower() or "stale" in str(blocker.get("id", "")).lower() for blocker in blockers):
        acting_state = "refresh_freshness_before_margin_action"

    side = str(edge_candidate.get("side") or action.get("side") or three_p_gate.get("side") or decision.get("direction_guess") or "HOLD").upper()
    if side not in {"BUY", "SELL"}:
        side = "HOLD"
    target_symbol = str(gold_margin_trader_unity.get("target_symbol") or live_deck_act.get("candidate") or "GOLD")
    target_venue = str(gold_margin_trader_unity.get("target_venue") or "Capital.com")
    margin_intent = {
        "intent_state": "shadow_margin_intent_ready" if shadow_margin_intent_allowed else "held_for_proof",
        "target_symbol": target_symbol,
        "target_venue": target_venue,
        "side": side,
        "entry_level": action.get("entry_level") or three_p_gate.get("entry_level"),
        "target_level": action.get("target_level") or three_p_gate.get("target_level"),
        "stop_level": action.get("stop_level") or three_p_gate.get("stop_level"),
        "suggested_shadow_size": action.get("suggested_shadow_size") or three_p_gate.get("suggested_shadow_size"),
        "expected_floor": three_p_gate.get("profit_floor_account_currency"),
        "estimated_net_at_suggested_size": three_p_gate.get("estimated_net_at_suggested_size"),
        "validated_shadow_p_l_effect": gold_portfolio_uplift_guard.get("validated_shadow_p_l_effect"),
        "dynamic_edge_score": gold_dynamic_market_edge_stream.get("edge_score"),
        "dynamic_edge_state": gold_dynamic_market_edge_stream.get("edge_state"),
        "intervals_used": [str(item.get("id")) for item in projection_intervals if item.get("validated")],
        "live_order_allowed": False,
        "margin_order_allowed": False,
        "order_mutation_allowed": False,
    }
    if not shadow_margin_intent_allowed:
        margin_intent["hold_reason"] = (blockers[0].get("reason") if blockers else "Waiting for all proof stages.")

    action_authority = {
        "shadow_margin_intent_allowed": shadow_margin_intent_allowed,
        "live_order_allowed": False,
        "margin_order_allowed": False,
        "leverage_change_allowed": False,
        "order_mutation_allowed": False,
        "credential_access_allowed": False,
        "authority_note": "This layer can create shadow margin intent evidence only. Existing runtime/risk/exchange gates remain the only live mutation path.",
    }

    hnc_auris_node_feedback = {
        "node_count": (cognitive_route.get("auris_nodes") or {}).get("node_count"),
        "coherence": (cognitive_route.get("auris_nodes") or {}).get("coherence"),
        "route_passed": cognitive_route.get("route_passed"),
        "feedback_action": "feed_shadow_intent_to_hnc" if shadow_margin_intent_allowed else "feed_blockers_to_hnc",
        "feedback_packet": {
            "fresh_signal_ready": pipeline[0]["ready"],
            "intervals_ready": pipeline[1]["ready"],
            "dynamic_edge_ready": pipeline[2]["ready"],
            "portfolio_uplift_ready": pipeline[5]["ready"],
            "margin_intent_state": margin_intent["intent_state"],
            "blocking_ids": [str(item.get("id")) for item in blockers[:8]],
        },
    }

    next_action = "shadow_validate_margin_intent_without_live_order" if shadow_margin_intent_allowed else "refresh_gold_source_mesh_and_validate_intervals"
    if acting_state == "feed_hnc_auris_blockers":
        next_action = "feed_blockers_to_hnc_auris_then_recompute_confidence"
    elif acting_state == "refresh_freshness_before_margin_action":
        next_action = "refresh_capital_gold_and_context_lanes_before_repricing_margin_intent"

    return {
        "status": "gold_margin_signal_action_loop_shadow_ready" if shadow_margin_intent_allowed else "gold_margin_signal_action_loop_blocking",
        "generated_at": generated_at,
        "mode": "read_only_shadow_margin_action_loop",
        "acting_state": acting_state,
        "active_now": {
            "state": acting_state,
            "task": "Convert GOLD intelligence into a gated shadow margin intent or feed blockers back into HNC/Auris.",
            "proof_required": "Fresh source mesh, interval validation, HNC/Auris coherence, margin unity, portfolio uplift, and action command must all pass.",
        },
        "next_action": next_action,
        "signal_to_action_pipeline": pipeline,
        "ready_stage_count": ready_stage_count,
        "stage_count": len(pipeline),
        "margin_intent": margin_intent,
        "action_authority": action_authority,
        "intelligence_feedback": {
            "decision_direction": decision.get("direction_guess"),
            "decision_confidence": decision.get("confidence"),
            "hft_speed_status": hft_speed_gate.get("status"),
            "historical_stress_status": historical_stress_test.get("status"),
            "verified_real_data_status": verified_data_gate.get("status"),
            "margin_unity_status": gold_margin_trader_unity.get("status"),
            "live_deck_status": gold_live_stream_command_deck.get("status"),
            "compiler_rule": "Ollama/agents/HNC/Auris can reason over shards, but final margin intent authority comes from this proof pipeline.",
        },
        "hnc_auris_node_feedback": hnc_auris_node_feedback,
        "blockers": blockers[:20],
        "manual_boundaries": [
            "No live margin order is submitted by this loop.",
            "No leverage, position, or credential mutation is allowed by this report.",
            "Only shadow intent and next-refresh work are published until runtime/risk/exchange gates independently clear.",
        ],
    }


def _build_gold_process_logic_flow_guard(
    *,
    verified_data_gate: Dict[str, Any],
    ticker_source_mesh: Dict[str, Any],
    signal_freshness_matrix: Dict[str, Any],
    projection_interval_validation: Dict[str, Any],
    evolving_projection_path: Dict[str, Any],
    dynamic_market_edge_stream: Dict[str, Any],
    hnc_history_future_bridge: Dict[str, Any],
    creative_dream_hypothesis_engine: Dict[str, Any],
    probability_projection_forecast: Dict[str, Any],
    hnc_action_coherence_gate: Dict[str, Any],
    portfolio_uplift_guard: Dict[str, Any],
    margin_trader_unity: Dict[str, Any],
    gold_action_command: Dict[str, Any],
    gold_live_stream_command_deck: Dict[str, Any],
    gold_margin_signal_action_loop: Dict[str, Any],
    generated_at: str,
) -> Dict[str, Any]:
    action = gold_action_command.get("act") if isinstance(gold_action_command.get("act"), dict) else {}
    probability_truth = probability_projection_forecast.get("truth_discipline") if isinstance(probability_projection_forecast.get("truth_discipline"), dict) else {}
    probability_validated = probability_projection_forecast.get("validated_forecast") if isinstance(probability_projection_forecast.get("validated_forecast"), dict) else {}
    margin_authority = gold_margin_signal_action_loop.get("action_authority") if isinstance(gold_margin_signal_action_loop.get("action_authority"), dict) else {}
    live_act = gold_live_stream_command_deck.get("what_will_i_act_on") if isinstance(gold_live_stream_command_deck.get("what_will_i_act_on"), dict) else {}
    live_margin = gold_live_stream_command_deck.get("leverage_margin_status") if isinstance(gold_live_stream_command_deck.get("leverage_margin_status"), dict) else {}
    edge_candidate = dynamic_market_edge_stream.get("action_candidate") if isinstance(dynamic_market_edge_stream.get("action_candidate"), dict) else {}
    dreams_ready = (
        bool(hnc_history_future_bridge.get("action_influence_allowed"))
        and _num(creative_dream_hypothesis_engine.get("dream_count")) >= 10
        and not bool(
            creative_dream_hypothesis_engine.get("live_order_allowed")
            or creative_dream_hypothesis_engine.get("margin_order_allowed")
            or creative_dream_hypothesis_engine.get("order_mutation_allowed")
        )
    )

    gate_sequence = [
        {
            "id": "verified_real_data_gate",
            "order": 1,
            "label": "Verified real data gate",
            "ready": bool(verified_data_gate.get("action_allowed_by_data")),
            "state": verified_data_gate.get("status"),
            "proof": (
                f"{verified_data_gate.get('fresh_required_source_count')}/"
                f"{verified_data_gate.get('required_source_count')} required sources fresh."
            ),
        },
        {
            "id": "ticker_signal_freshness",
            "order": 2,
            "label": "Ticker and signal freshness",
            "ready": bool(ticker_source_mesh.get("fresh_lane_count")) and bool(signal_freshness_matrix.get("action_influence_allowed")),
            "state": signal_freshness_matrix.get("status"),
            "proof": (
                f"lanes={ticker_source_mesh.get('fresh_lane_count')}/{ticker_source_mesh.get('lane_count')} "
                f"signal_rows={signal_freshness_matrix.get('fresh_row_count')}/{signal_freshness_matrix.get('row_count')}."
            ),
        },
        {
            "id": "interval_validation",
            "order": 3,
            "label": "Projection interval validation",
            "ready": bool(projection_interval_validation.get("action_influence_allowed")),
            "state": projection_interval_validation.get("status"),
            "proof": (
                f"{projection_interval_validation.get('validated_interval_count')}/"
                f"{projection_interval_validation.get('required_interval_count')} intervals; "
                f"hit_rate={projection_interval_validation.get('hit_rate')}."
            ),
        },
        {
            "id": "evolving_projection_path",
            "order": 4,
            "label": "Evolving projection path",
            "ready": bool(evolving_projection_path.get("live_evolving_ready")),
            "state": evolving_projection_path.get("status"),
            "proof": (
                f"horizons={evolving_projection_path.get('fresh_horizon_count')}/"
                f"{evolving_projection_path.get('horizon_count')} fresh; "
                f"validated={evolving_projection_path.get('validated_horizon_count')}."
            ),
        },
        {
            "id": "dynamic_market_edge_stream",
            "order": 5,
            "label": "Dynamic market edge stream",
            "ready": bool(edge_candidate.get("shadow_intent_allowed")),
            "state": dynamic_market_edge_stream.get("edge_state"),
            "proof": (
                f"edge_score={dynamic_market_edge_stream.get('edge_score')} "
                f"fresh_streams={dynamic_market_edge_stream.get('fresh_stream_count')}/"
                f"{dynamic_market_edge_stream.get('stream_lane_count')} "
                f"side={edge_candidate.get('side') or 'HOLD'}."
            ),
        },
        {
            "id": "hnc_history_future_bridge",
            "order": 6,
            "label": "HNC history future bridge",
            "ready": bool(hnc_history_future_bridge.get("action_influence_allowed")),
            "state": hnc_history_future_bridge.get("status"),
            "proof": (
                f"memory_score={hnc_history_future_bridge.get('historical_memory_score')} "
                f"history={hnc_history_future_bridge.get('validated_history_count')} "
                f"future={hnc_history_future_bridge.get('future_claim_state')}."
            ),
        },
        {
            "id": "creative_dream_hypothesis_engine",
            "order": 7,
            "label": "Creative dream hypothesis engine",
            "ready": dreams_ready,
            "state": creative_dream_hypothesis_engine.get("status"),
            "proof": (
                f"dreams={creative_dream_hypothesis_engine.get('dream_count')} "
                f"ready={creative_dream_hypothesis_engine.get('ready_dream_count')} "
                f"creativity={creative_dream_hypothesis_engine.get('average_creativity_score')} "
                "authority=idea_only."
            ),
        },
        {
            "id": "probability_projection_forecast",
            "order": 8,
            "label": "Probability projection forecast",
            "ready": bool(probability_truth.get("truth_claim_allowed") and probability_validated.get("action_influence_allowed")),
            "state": probability_projection_forecast.get("status"),
            "proof": (
                f"truth={probability_truth.get('truth_status')} "
                f"direction={(probability_projection_forecast.get('forecast_distribution') or {}).get('calibrated_direction')} "
                f"confidence={(probability_projection_forecast.get('forecast_distribution') or {}).get('calibrated_confidence')}."
            ),
        },
        {
            "id": "hnc_auris_coherence",
            "order": 9,
            "label": "HNC/Auris coherence",
            "ready": bool(hnc_action_coherence_gate.get("action_coherence_allowed")),
            "state": hnc_action_coherence_gate.get("status"),
            "proof": (
                f"effect={hnc_action_coherence_gate.get('confidence_effect')} "
                f"coherence={hnc_action_coherence_gate.get('auris_coherence')}."
            ),
        },
        {
            "id": "portfolio_uplift_guard",
            "order": 10,
            "label": "Portfolio uplift guard",
            "ready": bool(portfolio_uplift_guard.get("order_intent_consideration_allowed")),
            "state": portfolio_uplift_guard.get("status"),
            "proof": (
                f"shadow_pl={portfolio_uplift_guard.get('validated_shadow_p_l_effect')} "
                f"net={portfolio_uplift_guard.get('estimated_net_at_suggested_size')}."
            ),
        },
        {
            "id": "margin_trader_unity",
            "order": 11,
            "label": "Margin trader unity",
            "ready": margin_trader_unity.get("unity_state") == "gold_margin_unity_shadow_ready",
            "state": margin_trader_unity.get("unity_state"),
            "proof": (
                f"surfaces={margin_trader_unity.get('present_surface_count')}/"
                f"{margin_trader_unity.get('surface_count')}."
            ),
        },
        {
            "id": "gold_action_command",
            "order": 12,
            "label": "Gold action command",
            "ready": str(action.get("state") or "").startswith("shadow_validate_"),
            "state": action.get("state"),
            "proof": action.get("instruction") or "Action command is holding.",
        },
        {
            "id": "margin_signal_action_loop",
            "order": 13,
            "label": "Margin signal action loop",
            "ready": bool(margin_authority.get("shadow_margin_intent_allowed")),
            "state": gold_margin_signal_action_loop.get("acting_state"),
            "proof": (
                f"stages={gold_margin_signal_action_loop.get('ready_stage_count')}/"
                f"{gold_margin_signal_action_loop.get('stage_count')} "
                f"shadow_intent={margin_authority.get('shadow_margin_intent_allowed')}."
            ),
        },
    ]

    violations: List[Dict[str, Any]] = []
    first_blocked_index: Optional[int] = None
    for index, stage in enumerate(gate_sequence):
        if first_blocked_index is None and not stage["ready"]:
            first_blocked_index = index
        if stage["ready"] and first_blocked_index is not None and first_blocked_index < index:
            violations.append(
                {
                    "id": f"{stage['id']}_ready_before_upstream",
                    "stage": stage["id"],
                    "blocked_upstream": gate_sequence[first_blocked_index]["id"],
                    "reason": f"{stage['label']} claims ready while {gate_sequence[first_blocked_index]['label']} is blocked.",
                }
            )

    all_gates_ready = all(bool(stage["ready"]) for stage in gate_sequence)
    action_authority_checks = [
        {
            "id": "dynamic_edge_live_order",
            "allowed": bool(edge_candidate.get("live_order_allowed")),
            "allowed_when_all_gates_ready": False,
            "reason": "Dynamic edge stream can publish shadow intent only, never live orders.",
        },
        {
            "id": "dynamic_edge_margin_order",
            "allowed": bool(edge_candidate.get("margin_order_allowed")),
            "allowed_when_all_gates_ready": False,
            "reason": "Dynamic edge stream cannot place Capital margin orders.",
        },
        {
            "id": "action_command_live_order",
            "allowed": bool(action.get("live_order_allowed")),
            "allowed_when_all_gates_ready": False,
            "reason": "Gold action command must not place live orders from this report.",
        },
        {
            "id": "creative_dream_live_order",
            "allowed": bool(creative_dream_hypothesis_engine.get("live_order_allowed")),
            "allowed_when_all_gates_ready": False,
            "reason": "Creative dreams can queue validation only, never live orders.",
        },
        {
            "id": "creative_dream_margin_order",
            "allowed": bool(creative_dream_hypothesis_engine.get("margin_order_allowed")),
            "allowed_when_all_gates_ready": False,
            "reason": "Creative dreams cannot mutate Capital margin orders.",
        },
        {
            "id": "action_command_order_mutation",
            "allowed": bool(action.get("order_mutation_allowed")),
            "allowed_when_all_gates_ready": False,
            "reason": "Gold action command must not mutate orders from this report.",
        },
        {
            "id": "live_deck_live_order",
            "allowed": bool(live_act.get("live_order_allowed")),
            "allowed_when_all_gates_ready": False,
            "reason": "Live stream deck is read-only evidence.",
        },
        {
            "id": "live_deck_margin_order",
            "allowed": bool(live_margin.get("margin_order_allowed")),
            "allowed_when_all_gates_ready": False,
            "reason": "Live stream deck cannot arm margin orders.",
        },
        {
            "id": "margin_loop_live_order",
            "allowed": bool(margin_authority.get("live_order_allowed")),
            "allowed_when_all_gates_ready": False,
            "reason": "Margin signal loop can only publish shadow intent evidence.",
        },
        {
            "id": "margin_loop_leverage_change",
            "allowed": bool(margin_authority.get("leverage_change_allowed")),
            "allowed_when_all_gates_ready": False,
            "reason": "Leverage changes remain outside this autonomous report.",
        },
    ]
    for check in action_authority_checks:
        if check["allowed"]:
            violations.append(
                {
                    "id": f"{check['id']}_authority_leak",
                    "stage": check["id"],
                    "blocked_upstream": None if all_gates_ready else gate_sequence[first_blocked_index or 0]["id"],
                    "reason": check["reason"],
                }
            )

    if margin_authority.get("shadow_margin_intent_allowed") and not all_gates_ready:
        violations.append(
            {
                "id": "shadow_margin_intent_before_all_gates",
                "stage": "margin_signal_action_loop",
                "blocked_upstream": gate_sequence[first_blocked_index or 0]["id"],
                "reason": "Shadow margin intent cannot be allowed until every upstream proof gate is ready.",
            }
        )

    flow_correct = not violations
    first_blocked_stage = gate_sequence[first_blocked_index] if first_blocked_index is not None else None
    if all_gates_ready and flow_correct:
        flow_state = "flow_correct_shadow_intent_ready"
    elif flow_correct:
        flow_state = "flow_correct_action_held"
    else:
        flow_state = "flow_violation_attention"

    return {
        "status": "gold_process_logic_flow_guard_passing" if flow_correct else "gold_process_logic_flow_guard_blocking",
        "generated_at": generated_at,
        "flow_state": flow_state,
        "flow_correct": flow_correct,
        "all_gates_ready": all_gates_ready,
        "ready_gate_count": sum(1 for stage in gate_sequence if stage["ready"]),
        "gate_count": len(gate_sequence),
        "first_blocked_gate": first_blocked_stage,
        "policy": "GOLD process order is data -> freshness -> interval validation -> evolving path -> dynamic market edge stream -> HNC history future bridge -> creative dream hypotheses -> probability forecast -> HNC/Auris -> portfolio -> margin unity -> action command -> shadow margin loop.",
        "gate_sequence": gate_sequence,
        "action_authority_checks": action_authority_checks,
        "fake_pass_count": len(violations),
        "violations": violations[:16],
        "next_validation_action": (
            "shadow_validate_margin_intent_without_live_order"
            if all_gates_ready and flow_correct
            else f"repair_or_refresh_{first_blocked_stage['id']}" if first_blocked_stage else "inspect_flow_violation"
        ),
        "manual_boundaries": [
            "A blocked upstream gate must force every downstream action gate to hold.",
            "Passing historical/probability evidence is not enough unless freshness and action-influence gates also pass.",
            "This guard can certify flow integrity, not live trading authority.",
        ],
    }


def _gold_source_route_spec(source_id: str) -> Dict[str, Any]:
    specs: Dict[str, Dict[str, Any]] = {
        "capital_asset_registry": {
            "data_family": "target_market_profile",
            "meaning": "Capital GOLD tradable instrument, bid/ask/spread, margin factor, deal size, and venue profile.",
            "destinations": [
                "verified_real_data_gate",
                "gold_ticker_source_mesh",
                "gold_dynamic_market_edge_stream",
                "three_p_profit_floor_gate",
                "gold_live_stream_command_deck",
                "gold_margin_signal_action_loop",
            ],
            "gold_use": "target_price_and_margin_context",
        },
        "runtime_status": {
            "data_family": "runtime_truth",
            "meaning": "Runtime freshness, trading/data readiness, stale reason, and action posture.",
            "destinations": [
                "verified_real_data_gate",
                "gold_process_logic_flow_guard",
                "gold_action_command",
                "gold_margin_signal_action_loop",
            ],
            "gold_use": "authority_and_freshness_gate",
        },
        "data_ocean_status": {
            "data_family": "macro_research_gap_state",
            "meaning": "Macro/news/on-chain/source gaps that explain what extra context is missing.",
            "destinations": ["gold_ticker_source_mesh", "cross_market_driver_matrix", "gold_creative_dream_hypothesis_engine", "next_actions", "tool_activation_plan"],
            "gold_use": "context_gap_queue",
        },
        "global_financial_coverage": {
            "data_family": "cross_market_coverage",
            "meaning": "Coverage for ETFs, miners, indices, crypto, energy, historical waveform, and macro lanes.",
            "destinations": ["gold_market_universe", "cross_market_driver_matrix", "gold_ticker_source_mesh"],
            "gold_use": "related_market_context",
        },
        "exchange_data_matrix": {
            "data_family": "venue_capability",
            "meaning": "Exchange readiness, stream channels, order-book/price-history capabilities, and gaps.",
            "destinations": ["gold_exchange_optimization", "gold_live_stream_command_deck", "gold_dynamic_market_edge_stream", "hft_speed_prediction_gate"],
            "gold_use": "venue_and_stream_readiness",
        },
        "exchange_monitoring": {
            "data_family": "venue_monitoring",
            "meaning": "Fresh exchange feeds, active streams, tickers, and monitoring blockers.",
            "destinations": ["gold_exchange_optimization", "gold_live_stream_command_deck", "gold_dynamic_market_edge_stream", "verified_real_data_gate"],
            "gold_use": "fresh_feed_watch",
        },
        "trading_intelligence": {
            "data_family": "decision_trust_state",
            "meaning": "Trading trust posture, live stream cache, HFT staleness, and decision-fed capabilities.",
            "destinations": ["hft_speed_prediction_gate", "gold_action_command", "gold_live_stream_command_deck"],
            "gold_use": "decision_trust_and_speed_context",
        },
        "world_financial_ecosystem": {
            "data_family": "macro_cross_asset_story",
            "meaning": "DXY/rates/oil/VIX/equity/crypto/geopolitical context and lead-lag signals.",
            "destinations": ["cross_market_driver_matrix", "gold_dynamic_market_edge_stream", "gold_creative_dream_hypothesis_engine", "gold_probability_projection_forecast", "gold_shadow_trading_focus"],
            "gold_use": "why_gold_may_move",
        },
        "scanner_fusion_matrix": {
            "data_family": "multi_scanner_signal",
            "meaning": "Scanner, waveform, order-book, and fast-money candidates for GOLD and related lanes.",
            "destinations": ["historical_signal_lab", "gold_hnc_history_future_bridge", "gold_creative_dream_hypothesis_engine", "gold_shadow_trading_focus", "gold_dynamic_market_edge_stream", "gold_probability_projection_forecast"],
            "gold_use": "candidate_and_timing_evidence",
        },
        "shadow_trade_report": {
            "data_family": "shadow_trade_evidence",
            "meaning": "Non-mutating shadow candidates, energy context, and excluded non-GOLD symbols.",
            "destinations": ["gold_shadow_trading_focus", "historical_signal_lab", "gold_hnc_history_future_bridge", "gold_action_command"],
            "gold_use": "shadow_validation_context",
        },
        "harmonic_affect": {
            "data_family": "hnc_auris_affect",
            "meaning": "HNC coherence, goal/reward alignment, affect phase, and safety/blind-spot pressure.",
            "destinations": ["hnc_auris_quantum_probability_route", "gold_hnc_action_coherence_gate", "gold_process_logic_flow_guard"],
            "gold_use": "coherence_and_safety_pressure",
        },
        "agent_company": {
            "data_family": "agent_workforce",
            "meaning": "Available agent roles, tool readiness, and workforce capacity for GOLD tasks.",
            "destinations": ["gold_agent_coding_support", "swarm_intelligence", "gold_creative_dream_hypothesis_engine", "next_actions"],
            "gold_use": "agent_assignment_and_tooling",
        },
        "hnc_cognitive_proof": {
            "data_family": "hnc_cognitive_proof",
            "meaning": "HNC real-data proof, master formula, and Auris node status.",
            "destinations": ["hnc_auris_quantum_probability_route", "gold_hnc_action_coherence_gate"],
            "gold_use": "coherence_gate_truth_source",
        },
        "hnc_operating_cycle": {
            "data_family": "hnc_operating_cycle",
            "meaning": "HNC operating loop proof and cycle status.",
            "destinations": ["hnc_auris_quantum_probability_route", "gold_process_logic_flow_guard"],
            "gold_use": "organism_cycle_state",
        },
        "hnc_quantum_packet": {
            "data_family": "quantum_context",
            "meaning": "Metadata-only HNC quantum packet context for non-mutating probability/coherence interpretation.",
            "destinations": ["hnc_auris_quantum_probability_route", "gold_probability_projection_forecast"],
            "gold_use": "quantum_context_evidence",
        },
        "lambda_history": {
            "data_family": "lambda_timing_history",
            "meaning": "Lambda and psi history used as organism timing/coherence context.",
            "destinations": ["hnc_auris_quantum_probability_route", "gold_hnc_action_coherence_gate"],
            "gold_use": "timing_and_coherence_memory",
        },
    }
    return specs.get(
        source_id,
        {
            "data_family": "unclassified",
            "meaning": "Source is present but has no explicit GOLD route specification yet.",
            "destinations": [],
            "gold_use": "needs_route_spec",
        },
    )


def _build_gold_data_sensemaking_router(
    *,
    source_evidence: List[Dict[str, Any]],
    local_research_packets: List[Dict[str, Any]],
    signals: List[Dict[str, Any]],
    cross_market_driver_matrix: List[Dict[str, Any]],
    gold_ticker_source_mesh: Dict[str, Any],
    gold_signal_freshness_matrix: Dict[str, Any],
    gold_projection_interval_validation: Dict[str, Any],
    gold_evolving_projection_path: Dict[str, Any],
    gold_dynamic_market_edge_stream: Dict[str, Any],
    gold_hnc_history_future_bridge: Dict[str, Any],
    gold_creative_dream_hypothesis_engine: Dict[str, Any],
    gold_probability_projection_forecast: Dict[str, Any],
    hnc_action_coherence_gate: Dict[str, Any],
    gold_process_logic_flow_guard: Dict[str, Any],
    generated_at: str,
) -> Dict[str, Any]:
    source_routes: List[Dict[str, Any]] = []
    blockers: List[Dict[str, Any]] = []
    destination_counts: Dict[str, int] = {}
    for source in source_evidence:
        source_id = str(source.get("id") or "")
        spec = _gold_source_route_spec(source_id)
        destinations = list(spec.get("destinations") or [])
        present = bool(source.get("present"))
        fresh = bool(source.get("fresh"))
        route_ready = bool(present and destinations)
        for destination in destinations:
            destination_counts[destination] = destination_counts.get(destination, 0) + 1
        route = {
            "id": source_id,
            "path": source.get("path"),
            "present": present,
            "fresh": fresh,
            "age_seconds": source.get("age_seconds"),
            "status": source.get("status"),
            "data_family": spec.get("data_family"),
            "meaning": spec.get("meaning"),
            "gold_use": spec.get("gold_use"),
            "destinations": destinations,
            "route_ready": route_ready,
            "classification_state": "read_classified_routed" if route_ready else "unrouted_or_missing",
            "operator_summary": f"{source_id} -> {', '.join(destinations) if destinations else 'needs route'}",
        }
        source_routes.append(route)
        if not present:
            blockers.append({"id": f"{source_id}_missing", "reason": f"{source_id} was not readable."})
        elif not destinations:
            blockers.append({"id": f"{source_id}_unrouted", "reason": f"{source_id} has no GOLD destination route."})
        elif not fresh:
            blockers.append({"id": f"{source_id}_not_fresh", "reason": f"{source_id} is routed but not fresh enough for action influence."})

    meaning_packets = [
        {
            "id": "ticker_source_mesh",
            "meaning": "Which GOLD and related tickers are fresh enough to matter.",
            "destination": "gold_signal_freshness_matrix",
            "state": gold_ticker_source_mesh.get("status"),
            "ready": bool(gold_ticker_source_mesh.get("fresh_lane_count")),
        },
        {
            "id": "signal_freshness_matrix",
            "meaning": "Which signal rows can influence action.",
            "destination": "gold_projection_interval_validation",
            "state": gold_signal_freshness_matrix.get("status"),
            "ready": bool(gold_signal_freshness_matrix.get("action_influence_allowed")),
        },
        {
            "id": "projection_interval_validation",
            "meaning": "Whether forecasts have tick/1m/5m/15m/1h/session outcome proof.",
            "destination": "gold_evolving_projection_path",
            "state": gold_projection_interval_validation.get("status"),
            "ready": bool(gold_projection_interval_validation.get("action_influence_allowed")),
        },
        {
            "id": "evolving_projection_path",
            "meaning": "Rolling seconds-to-months projection ladder with live deadlines, hit/miss validation, and roll-forward action.",
            "destination": "gold_dynamic_market_edge_stream",
            "state": gold_evolving_projection_path.get("status"),
            "ready": bool(gold_evolving_projection_path.get("live_evolving_ready")),
        },
        {
            "id": "dynamic_market_edge_stream",
            "meaning": "Live GOLD and related-market stream watcher that maps waveform edge, trigger side, blockers, and shadow-only action candidate.",
            "destination": "gold_hnc_history_future_bridge",
            "state": gold_dynamic_market_edge_stream.get("status"),
            "ready": bool((gold_dynamic_market_edge_stream.get("action_candidate") or {}).get("shadow_intent_allowed")),
        },
        {
            "id": "hnc_history_future_bridge",
            "meaning": "Validated history translated into future GOLD windows through HNC/Auris, with blockers lowering confidence.",
            "destination": "gold_creative_dream_hypothesis_engine",
            "state": gold_hnc_history_future_bridge.get("status"),
            "ready": bool(gold_hnc_history_future_bridge.get("action_influence_allowed")),
        },
        {
            "id": "creative_dream_hypothesis_engine",
            "meaning": "Many GOLD edge dreams are generated, grounded in source packets, and queued for non-mutating validation.",
            "destination": "gold_probability_projection_forecast",
            "state": gold_creative_dream_hypothesis_engine.get("status"),
            "ready": _num(gold_creative_dream_hypothesis_engine.get("dream_count")) >= 10,
        },
        {
            "id": "probability_projection_forecast",
            "meaning": "Calibrated BUY/SELL/HOLD probability and truth discipline.",
            "destination": "gold_hnc_action_coherence_gate",
            "state": gold_probability_projection_forecast.get("status"),
            "ready": bool((gold_probability_projection_forecast.get("truth_discipline") or {}).get("truth_claim_allowed")),
        },
        {
            "id": "hnc_action_coherence_gate",
            "meaning": "Whether HNC/Auris may raise confidence or must lower/hold.",
            "destination": "gold_process_logic_flow_guard",
            "state": hnc_action_coherence_gate.get("status"),
            "ready": bool(hnc_action_coherence_gate.get("action_coherence_allowed")),
        },
        {
            "id": "process_logic_flow_guard",
            "meaning": "Whether the whole chain is ordered correctly without fake passes.",
            "destination": "operator_and_action_loop",
            "state": gold_process_logic_flow_guard.get("status"),
            "ready": bool(gold_process_logic_flow_guard.get("flow_correct")),
        },
    ]
    contradiction_count = len(gold_probability_projection_forecast.get("contradiction_matrix") or [])
    if contradiction_count:
        blockers.append(
            {
                "id": "forecast_contradictions_visible",
                "reason": f"{contradiction_count} probability/driver/source contradiction(s) must be routed as confidence-lowering evidence.",
            }
        )
    if not gold_process_logic_flow_guard.get("flow_correct"):
        blockers.append({"id": "process_flow_violation", "reason": "Data is routed, but downstream gate order has a flow violation."})

    routed_count = sum(1 for route in source_routes if route.get("route_ready"))
    present_count = sum(1 for route in source_routes if route.get("present"))
    fresh_count = sum(1 for route in source_routes if route.get("fresh"))
    research_routes = [
        {
            "id": packet.get("id"),
            "path": packet.get("path"),
            "matched_terms": packet.get("matched_terms") or [],
            "destination": "local_research_packets",
            "use": "operator/source context only unless paired with fresh market evidence",
            "route_ready": bool(packet.get("matched_terms")),
        }
        for packet in local_research_packets
    ]
    signal_routes = [
        {
            "id": signal.get("id"),
            "label": signal.get("label"),
            "direction": signal.get("direction"),
            "fresh": bool(signal.get("fresh")),
            "destination": "gold_signal_freshness_matrix",
            "action_use": "candidate_signal" if signal.get("fresh") else "context_or_blocker",
        }
        for signal in signals
    ]
    driver_routes = [
        {
            "id": driver.get("id"),
            "label": driver.get("label"),
            "state": driver.get("driver_state"),
            "destination": "gold_probability_projection_forecast" if driver.get("driver_state") == "ready_shadow_driver" else "contradiction_matrix",
            "action_use": "confidence_context" if driver.get("driver_state") == "ready_shadow_driver" else "confidence_hold_or_lower",
        }
        for driver in cross_market_driver_matrix
    ]
    sensemaking_score = _clamp(
        (present_count / max(1.0, len(source_routes))) * 0.25
        + (routed_count / max(1.0, len(source_routes))) * 0.3
        + (fresh_count / max(1.0, len(source_routes))) * 0.15
        + (sum(1 for packet in meaning_packets if packet.get("ready")) / max(1.0, len(meaning_packets))) * 0.2
        + (0.1 if gold_process_logic_flow_guard.get("flow_correct") else 0.0)
    )
    status = "gold_data_sensemaking_router_ready" if not blockers else "gold_data_sensemaking_router_attention"
    return {
        "status": status,
        "generated_at": generated_at,
        "sensemaking_state": "read_classified_routed_with_blockers" if blockers else "read_classified_routed_ready",
        "policy": "Every GOLD data source must be read, classified by meaning, routed to a destination gate, and blocked from action if stale, contradictory, or unmapped.",
        "sensemaking_score": round(sensemaking_score, 4),
        "source_count": len(source_routes),
        "present_source_count": present_count,
        "fresh_source_count": fresh_count,
        "routed_source_count": routed_count,
        "destination_count": len(destination_counts),
        "destination_counts": destination_counts,
        "source_routes": source_routes,
        "meaning_packets": meaning_packets,
        "research_routes": research_routes[:12],
        "signal_routes": signal_routes[:12],
        "driver_routes": driver_routes[:16],
        "blockers": blockers[:20],
        "manual_boundaries": [
            "Sensemaking routes data into gates; it does not create trading authority.",
            "Reference/research context cannot unlock action without fresh market proof.",
            "Contradictions are routed into confidence-lowering evidence, not ignored.",
        ],
    }


def _scale_points(points: List[Dict[str, Any]], width: int, height: int, pad: int) -> Dict[str, Any]:
    values: List[float] = []
    for point in points:
        for key in ("shadow_low", "shadow_mid", "shadow_high"):
            value = point.get(key)
            if value is not None:
                values.append(_num(value))
    if not values:
        return {"low": 0.0, "high": 1.0, "coords": []}
    low = min(values)
    high = max(values)
    if high <= low:
        high = low + 1.0
    span = high - low
    coords: List[Dict[str, Any]] = []
    plot_w = width - pad * 2
    plot_h = height - pad * 2
    for index, point in enumerate(points):
        x = pad + (plot_w * index / max(1, len(points) - 1))
        mapped: Dict[str, Any] = {"x": x, "horizon": point.get("horizon")}
        for key in ("shadow_low", "shadow_mid", "shadow_high"):
            value = point.get(key)
            y = pad + plot_h - ((_num(value) - low) / span) * plot_h if value is not None else pad + plot_h
            mapped[key] = y
        coords.append(mapped)
    return {"low": low, "high": high, "coords": coords}


def _make_gold_forecast_svg(report: Dict[str, Any]) -> str:
    workbench = report.get("gold_priority_workbench", {})
    points = workbench.get("forecast_points") if isinstance(workbench.get("forecast_points"), list) else []
    summary = report.get("summary", {})
    decision = report.get("decision", {})
    lanes = (report.get("historical_signal_lab") or {}).get("replay_lanes") or []
    width, height, pad = 1040, 620, 72
    scaled = _scale_points(points, width, 360, pad)
    coords = scaled["coords"]
    mid_path = " ".join(f"{'M' if i == 0 else 'L'} {item['x']:.1f} {item['shadow_mid']:.1f}" for i, item in enumerate(coords))
    upper_path = " ".join(f"{'M' if i == 0 else 'L'} {item['x']:.1f} {item['shadow_high']:.1f}" for i, item in enumerate(coords))
    lower_path = " ".join(f"{'L'} {item['x']:.1f} {item['shadow_low']:.1f}" for item in reversed(coords))
    band_path = f"{upper_path} {lower_path} Z" if coords else ""
    lane_rows = []
    for index, lane in enumerate(lanes[:6]):
        y = 430 + index * 26
        state = str(lane.get("state") or "waiting")
        color = "#22c55e" if state.startswith("ready") else "#f59e0b" if "attention" in state else "#ef4444"
        label = escape(str(lane.get("label") or lane.get("id") or "lane"))
        lane_rows.append(f'<circle cx="78" cy="{y}" r="5" fill="{color}" /><text x="92" y="{y + 4}" class="small">{label}: {escape(state)}</text>')
    point_labels = []
    for item, point in zip(coords, points):
        point_labels.append(
            f'<circle cx="{item["x"]:.1f}" cy="{item["shadow_mid"]:.1f}" r="5" fill="#fde047" />'
            f'<text x="{item["x"] - 14:.1f}" y="386" class="axis">{escape(str(point.get("horizon") or ""))}</text>'
        )
    status = escape(str(workbench.get("status") or "gold_priority_workbench_waiting"))
    target = escape(str(summary.get("target_symbol") or "GOLD"))
    direction = escape(str(decision.get("direction_guess") or summary.get("direction_guess") or "OBSERVE"))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Aureon Capital GOLD priority forecast workbench">
  <style>
    .bg {{ fill: #071014; }}
    .panel {{ fill: #0d1b1f; stroke: #27424a; stroke-width: 1; }}
    .title {{ fill: #f8fafc; font: 700 26px Arial, sans-serif; }}
    .subtitle {{ fill: #94a3b8; font: 14px Arial, sans-serif; }}
    .axis {{ fill: #9ca3af; font: 12px Arial, sans-serif; }}
    .small {{ fill: #cbd5e1; font: 13px Arial, sans-serif; }}
    .metric {{ fill: #fef08a; font: 700 18px Arial, sans-serif; }}
  </style>
  <rect class="bg" width="{width}" height="{height}" />
  <rect class="panel" x="28" y="24" width="984" height="572" rx="8" />
  <text x="56" y="66" class="title">Aureon Capital GOLD Priority Workbench</text>
  <text x="56" y="92" class="subtitle">Shadow forecast band from local evidence. Charts do not place trades or bypass runtime gates.</text>
  <text x="760" y="64" class="metric">{target} {direction}</text>
  <text x="760" y="88" class="subtitle">{status}</text>
  <line x1="{pad}" y1="360" x2="{width - pad}" y2="360" stroke="#334155" />
  <line x1="{pad}" y1="{pad}" x2="{pad}" y2="360" stroke="#334155" />
  <text x="80" y="124" class="axis">high {scaled["high"]:.2f}</text>
  <text x="80" y="350" class="axis">low {scaled["low"]:.2f}</text>
  <path d="{band_path}" fill="#facc15" opacity="0.16" />
  <path d="{upper_path}" fill="none" stroke="#eab308" stroke-width="2" stroke-dasharray="5 5" />
  <path d="{mid_path}" fill="none" stroke="#fde047" stroke-width="4" />
  {''.join(point_labels)}
  <text x="56" y="408" class="subtitle">Replay lanes and proof state</text>
  {''.join(lane_rows)}
</svg>'''


def _make_gold_forecast_html(report: Dict[str, Any]) -> str:
    workbench = report.get("gold_priority_workbench", {})
    manifest = workbench.get("artifact_manifest") if isinstance(workbench.get("artifact_manifest"), dict) else {}
    queue = workbench.get("data_priority_queue") if isinstance(workbench.get("data_priority_queue"), list) else []
    rows = []
    for item in queue:
        rows.append(
            "<tr>"
            f"<td>{escape(str(item.get('priority') or ''))}</td>"
            f"<td>{escape(str(item.get('id') or '').replace('_', ' '))}</td>"
            f"<td>{escape(str(item.get('agent') or ''))}</td>"
            f"<td>{escape(str(item.get('data_needed') or ''))}</td>"
            f"<td>{escape(str(item.get('proof_required') or ''))}</td>"
            "</tr>"
        )
    svg_url = escape(str(manifest.get("svg_url") or "gold_priority_forecast.svg"))
    status = escape(str(workbench.get("status") or "waiting"))
    generated_at = escape(str(report.get("generated_at") or ""))
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Aureon Capital GOLD Priority Workbench</title>
  <style>
    body {{ margin: 0; background: #071014; color: #e5e7eb; font-family: Arial, sans-serif; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 24px; }}
    img {{ width: 100%; border: 1px solid #27424a; border-radius: 8px; background: #0d1b1f; }}
    table {{ width: 100%; margin-top: 18px; border-collapse: collapse; font-size: 13px; }}
    th, td {{ border: 1px solid #27424a; padding: 10px; vertical-align: top; }}
    th {{ background: #10252b; text-align: left; }}
    .meta {{ color: #94a3b8; }}
  </style>
</head>
<body>
  <main>
    <h1>Aureon Capital GOLD Priority Workbench</h1>
    <p class="meta">Status: {status} | generated: {generated_at} | read-only shadow evidence, not financial advice.</p>
    <img src="{svg_url}" alt="Capital GOLD priority forecast chart" />
    <h2>Data Priority Queue</h2>
    <table>
      <thead><tr><th>Priority</th><th>Task</th><th>Agent</th><th>Data needed</th><th>Proof required</th></tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
  </main>
</body>
</html>'''


def _write_gold_forecast_artifacts(root: Path, report: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        _write_text(_rooted(root, GOLD_FORECAST_SVG), _make_gold_forecast_svg(report)),
        _write_text(_rooted(root, GOLD_FORECAST_HTML), _make_gold_forecast_html(report)),
    ]


def _make_markdown(report: Dict[str, Any]) -> str:
    summary = report.get("summary", {})
    hypothesis = report.get("price_energy_hypothesis", {})
    lines = [
        "# Aureon Gold Capital Intelligence Company",
        "",
        f"- status: {report.get('status')}",
        f"- generated_at: {report.get('generated_at')}",
        f"- target: {summary.get('target_symbol')} on Capital.com",
        f"- action_posture: {summary.get('action_posture')}",
        f"- gold_energy_score: {summary.get('gold_energy_score')}",
        f"- confidence: {summary.get('confidence')}",
        f"- direction_guess: {summary.get('direction_guess')}",
        f"- live_trade_allowed: {summary.get('live_trade_allowed')}",
        f"- shadow_observation_allowed: {summary.get('shadow_observation_allowed')}",
        "",
        "## Price/Energy Hypothesis",
        "",
        f"- mid_price: {hypothesis.get('mid_price')} {hypothesis.get('currency')}",
        f"- range: {hypothesis.get('hypothesis_low')} to {hypothesis.get('hypothesis_high')}",
        f"- reason: {hypothesis.get('band_reason')}",
        "",
        "## Blockers",
    ]
    for blocker in report.get("blockers", []):
        lines.append(f"- {blocker.get('id')}: {blocker.get('reason')}")
    if not report.get("blockers"):
        lines.append("- none")
    lines.extend(["", "## Company Roles"])
    for role in report.get("company_roles", []):
        lines.append(f"- {role.get('role')}: {role.get('mission')}")
    lines.extend(["", "## Signals"])
    for signal in report.get("signals", []):
        lines.append(f"- {signal.get('label')}: {signal.get('direction')} score={signal.get('score')} ({signal.get('reason')})")
    lines.extend(["", "## Gold Intelligence Surfaces"])
    for surface in report.get("gold_intelligence_map", []):
        lines.append(
            f"- {surface.get('id')}: {surface.get('status')} "
            f"department={surface.get('department')} tool={surface.get('tool_type')}"
        )
    lines.extend(["", "## Intelligence Gaps"])
    gaps = report.get("intelligence_gaps", [])
    if gaps:
        for gap in gaps:
            lines.append(f"- {gap.get('severity')} {gap.get('id')}: {gap.get('next_action')}")
    else:
        lines.append("- none")
    swarm = report.get("swarm_intelligence", {})
    lines.extend(["", "## Gold Swarm Intelligence"])
    lines.append(
        f"- status: {swarm.get('status')} agents={swarm.get('active_agent_count')}/"
        f"{swarm.get('agent_count')} active attention={swarm.get('attention_agent_count')}"
    )
    lines.append(f"- compile_gate: {(swarm.get('compile_gate') or {}).get('state')}")
    for agent in (swarm.get("agents") or [])[:12]:
        lines.append(
            f"- {agent.get('id')}: {agent.get('state')} score={agent.get('score')} "
            f"drivers={','.join(str(item) for item in agent.get('assigned_driver_ids', []))}"
        )
    lines.extend(["", "## Cross-Market Gold Driver Matrix"])
    for driver in report.get("cross_market_driver_matrix", []):
        lines.append(
            f"- {driver.get('id')}: {driver.get('driver_state')} score={driver.get('score')} "
            f"fresh={driver.get('fresh')} next={driver.get('next_action')}"
        )
    exchange_optimization = report.get("gold_exchange_optimization", {})
    lines.extend(["", "## Gold Exchange Optimization"])
    lines.append(f"- status: {exchange_optimization.get('status')}")
    lines.append(f"- optimization_score: {exchange_optimization.get('optimization_score')}")
    lines.append(
        f"- ready_venues: {exchange_optimization.get('ready_venue_count')}/"
        f"{exchange_optimization.get('venue_count')} watchlists={exchange_optimization.get('watchlist_bucket_count')}"
    )
    for venue in (exchange_optimization.get("venues") or []):
        lines.append(
            f"- venue {venue.get('label')}: ready={venue.get('ready_for_gold_monitoring')} "
            f"role={venue.get('role')} blockers={','.join(str(item) for item in venue.get('blockers', [])[:4])}"
        )
    for item in (exchange_optimization.get("related_asset_watchlist") or []):
        lines.append(f"- watchlist {item.get('bucket')}: {','.join(str(symbol) for symbol in item.get('symbols', [])[:8])}")
    for blocker in (exchange_optimization.get("blockers") or [])[:8]:
        lines.append(f"- blocker {blocker.get('id')}: {blocker.get('reason')}")
    margin_unity = report.get("gold_margin_trader_unity", {})
    lines.extend(["", "## Gold Margin Trader Unity"])
    lines.append(f"- status: {margin_unity.get('status')}")
    lines.append(f"- unity_state: {margin_unity.get('unity_state')}")
    lines.append(
        f"- surfaces: {margin_unity.get('present_surface_count')}/"
        f"{margin_unity.get('surface_count')} target={margin_unity.get('target_venue')} {margin_unity.get('target_symbol')}"
    )
    lines.append(
        f"- live_order_allowed: {(margin_unity.get('margin_command') or {}).get('live_order_allowed')} "
        f"margin_order_allowed: {(margin_unity.get('margin_command') or {}).get('margin_order_allowed')}"
    )
    for role in (margin_unity.get("margin_roles") or [])[:8]:
        lines.append(f"- role {role.get('role')}: {role.get('job')}")
    for directive in (margin_unity.get("mission_directives") or [])[:8]:
        lines.append(f"- directive {directive.get('id')}: {directive.get('state')} - {directive.get('directive')}")
    for blocker in (margin_unity.get("blockers") or [])[:8]:
        lines.append(f"- blocker {blocker.get('id')}: {blocker.get('reason')}")
    lab = report.get("historical_signal_lab", {})
    lines.extend(["", "## Historical Signal Lab"])
    lines.append(
        f"- status: {lab.get('status')} lanes={lab.get('ready_lane_count')}/"
        f"{lab.get('lane_count')} ready lead_lag={len(lab.get('lead_lag_candidates') or [])} "
        f"orderbook={lab.get('orderbook_signal_state')}"
    )
    for lane in (lab.get("replay_lanes") or []):
        lines.append(f"- {lane.get('id')}: {lane.get('state')} next={lane.get('next_action')}")
    workbench = report.get("gold_priority_workbench", {})
    manifest = workbench.get("artifact_manifest") or {}
    lines.extend(["", "## Gold Priority Workbench"])
    lines.append(f"- status: {workbench.get('status')}")
    lines.append(f"- forecast_html: {manifest.get('html_url')}")
    lines.append(f"- forecast_svg: {manifest.get('svg_url')}")
    for item in (workbench.get("data_priority_queue") or [])[:8]:
        lines.append(f"- {item.get('priority')} {item.get('id')}: {item.get('data_needed')}")
    floor_gate = report.get("three_p_profit_floor_gate", {})
    lines.extend(["", "## 3p Profit Floor Gate"])
    lines.append(f"- state: {floor_gate.get('state')}")
    lines.append(f"- side: {floor_gate.get('side')}")
    lines.append(f"- entry: {floor_gate.get('entry_level')} target: {floor_gate.get('target_level')} stop: {floor_gate.get('stop_level')}")
    lines.append(f"- suggested_shadow_size: {floor_gate.get('suggested_shadow_size')}")
    for blocker in (floor_gate.get("blockers") or [])[:8]:
        lines.append(f"- blocker {blocker.get('id')}: {blocker.get('reason')}")
    real_gate = report.get("verified_real_data_gate", {})
    lines.extend(["", "## Verified Real Data Gate"])
    lines.append(f"- status: {real_gate.get('status')}")
    lines.append(f"- action_allowed_by_data: {real_gate.get('action_allowed_by_data')}")
    lines.append(
        f"- fresh_sources: {real_gate.get('fresh_required_source_count')}/"
        f"{real_gate.get('required_source_count')}"
    )
    for blocker in (real_gate.get("blockers") or [])[:8]:
        lines.append(f"- blocker {blocker.get('id')}: {blocker.get('reason')}")
    freshness = report.get("gold_signal_freshness_matrix", {})
    ticker_mesh = report.get("gold_ticker_source_mesh", {})
    projection_validation = report.get("gold_projection_interval_validation", {})
    hnc_action_gate = report.get("gold_hnc_action_coherence_gate", {})
    portfolio_guard = report.get("gold_portfolio_uplift_guard", {})
    lines.extend(["", "## GOLD Fresh Signal Validation"])
    lines.append(f"- signal_freshness_status: {freshness.get('status')}")
    lines.append(
        f"- fresh_signal_rows: {freshness.get('fresh_row_count')}/"
        f"{freshness.get('row_count')} action_influence={freshness.get('action_influence_allowed')}"
    )
    lines.append(
        f"- ticker_mesh: {ticker_mesh.get('fresh_lane_count')}/"
        f"{ticker_mesh.get('lane_count')} fresh lanes"
    )
    lines.append(
        f"- interval_validation: {projection_validation.get('validated_interval_count')}/"
        f"{projection_validation.get('required_interval_count')} hit_rate={projection_validation.get('hit_rate')}"
    )
    lines.append(f"- hnc_action_coherence: {hnc_action_gate.get('status')} effect={hnc_action_gate.get('confidence_effect')}")
    lines.append(f"- portfolio_uplift_guard: {portfolio_guard.get('status')} shadow_pl={portfolio_guard.get('validated_shadow_p_l_effect')}")
    for lane in (ticker_mesh.get("lanes") or [])[:8]:
        lines.append(
            f"- source {lane.get('id')}: fresh={lane.get('fresh')} "
            f"role={lane.get('role')} symbols={','.join(str(symbol) for symbol in lane.get('symbols', [])[:5])}"
        )
    for interval in (projection_validation.get("intervals") or [])[:8]:
        lines.append(
            f"- interval {interval.get('id')}: {interval.get('hit_miss')} "
            f"validated={interval.get('validated')} action={interval.get('action_influence_allowed')}"
        )
    for blocker in (
        (freshness.get("blockers") or [])
        + (projection_validation.get("blockers") or [])
        + (portfolio_guard.get("blockers") or [])
    )[:10]:
        lines.append(f"- blocker {blocker.get('id')}: {blocker.get('reason')}")
    evolving_path = report.get("gold_evolving_projection_path", {})
    lines.extend(["", "## GOLD Evolving Projection Path"])
    lines.append(f"- status: {evolving_path.get('status')}")
    lines.append(f"- live_evolving_ready: {evolving_path.get('live_evolving_ready')}")
    lines.append(
        f"- horizons: fresh={evolving_path.get('fresh_horizon_count')}/"
        f"{evolving_path.get('horizon_count')} validated={evolving_path.get('validated_horizon_count')} "
        f"hit_rate={evolving_path.get('hit_rate')}"
    )
    lines.append(f"- next_roll_forward_action: {evolving_path.get('next_roll_forward_action')}")
    for horizon in (evolving_path.get("horizons") or [])[:12]:
        lines.append(
            f"- horizon {horizon.get('id')}: {horizon.get('validation_state')} "
            f"fresh={horizon.get('input_fresh')} validated={horizon.get('validated')} next={horizon.get('next_action')}"
        )
    for blocker in (evolving_path.get("blockers") or [])[:8]:
        lines.append(f"- blocker {blocker.get('id')}: {blocker.get('reason')}")
    dynamic_edge = report.get("gold_dynamic_market_edge_stream", {})
    edge_candidate = dynamic_edge.get("action_candidate") or {}
    lines.extend(["", "## GOLD Dynamic Market Edge Stream"])
    lines.append(f"- status: {dynamic_edge.get('status')}")
    lines.append(f"- edge_state: {dynamic_edge.get('edge_state')} edge_score={dynamic_edge.get('edge_score')}")
    lines.append(
        f"- streams: fresh={dynamic_edge.get('fresh_stream_count')}/"
        f"{dynamic_edge.get('stream_lane_count')} context={dynamic_edge.get('context_fresh_count')} "
        f"target_fresh={dynamic_edge.get('target_stream_fresh')}"
    )
    lines.append(
        f"- action_candidate: {edge_candidate.get('candidate')} {edge_candidate.get('side')} "
        f"state={edge_candidate.get('state')} shadow={edge_candidate.get('shadow_intent_allowed')}"
    )
    lines.append(f"- next_action: {dynamic_edge.get('next_action')}")
    for row in (dynamic_edge.get("stream_rows") or [])[:10]:
        lines.append(
            f"- stream {row.get('id')}: {row.get('stream_state')} score={row.get('edge_score')} "
            f"fresh={row.get('fresh')} use={row.get('edge_use')}"
        )
    for blocker in (dynamic_edge.get("blockers") or [])[:8]:
        lines.append(f"- blocker {blocker.get('id')}: {blocker.get('reason')}")
    history_future = report.get("gold_hnc_history_future_bridge", {})
    lines.extend(["", "## GOLD HNC History Future Bridge"])
    lines.append(f"- status: {history_future.get('status')}")
    lines.append(f"- bridge_ready: {history_future.get('bridge_ready')} future={history_future.get('future_claim_state')}")
    lines.append(
        f"- memory_score: {history_future.get('historical_memory_score')} "
        f"validated={history_future.get('validated_history_count')} hit_rate={history_future.get('historical_hit_rate')}"
    )
    lines.append(
        f"- replay_lanes: {history_future.get('ready_replay_lane_count')}/"
        f"{history_future.get('replay_lane_count')} future_windows={len(history_future.get('future_windows') or [])}"
    )
    for analog in (history_future.get("historical_analogs") or [])[:8]:
        lines.append(
            f"- analog {analog.get('id')}: {analog.get('state')} "
            f"use={analog.get('future_use')} next={analog.get('next_action')}"
        )
    for blocker in (history_future.get("blockers") or [])[:8]:
        lines.append(f"- blocker {blocker.get('id')}: {blocker.get('reason')}")
    creative_dreams = report.get("gold_creative_dream_hypothesis_engine", {})
    lines.extend(["", "## GOLD Creative Dream Hypothesis Engine"])
    lines.append(f"- status: {creative_dreams.get('status')}")
    lines.append(
        f"- dreams: {creative_dreams.get('ready_dream_count')}/"
        f"{creative_dreams.get('dream_count')} ready creativity={creative_dreams.get('average_creativity_score')} "
        f"evidence={creative_dreams.get('average_evidence_score')}"
    )
    lines.append(f"- action_influence_allowed: {creative_dreams.get('action_influence_allowed')}")
    for dream in (creative_dreams.get("dreams") or [])[:8]:
        lines.append(
            f"- dream {dream.get('id')}: {dream.get('state')} "
            f"creative={dream.get('creativity_score')} evidence={dream.get('evidence_score')} next={dream.get('next_validation_action')}"
        )
    for blocker in (creative_dreams.get("blockers") or [])[:8]:
        lines.append(f"- blocker {blocker.get('id')}: {blocker.get('reason')}")
    probability_forecast = report.get("gold_probability_projection_forecast", {})
    truth_discipline = probability_forecast.get("truth_discipline") or {}
    forecast_distribution = probability_forecast.get("forecast_distribution") or {}
    validated_forecast = probability_forecast.get("validated_forecast") or {}
    lines.extend(["", "## GOLD Probability Projection Forecast"])
    lines.append(f"- status: {probability_forecast.get('status')}")
    lines.append(f"- truth_status: {truth_discipline.get('truth_status')} truth_claim_allowed={truth_discipline.get('truth_claim_allowed')}")
    lines.append(
        f"- calibrated_direction: {forecast_distribution.get('calibrated_direction')} "
        f"confidence={forecast_distribution.get('calibrated_confidence')} quality={forecast_distribution.get('organism_quality_score')}"
    )
    lines.append(
        f"- distribution: buy={forecast_distribution.get('buy_probability')} "
        f"sell={forecast_distribution.get('sell_probability')} hold={forecast_distribution.get('hold_probability')}"
    )
    lines.append(
        f"- validated_claims: {validated_forecast.get('validated_claim_count')} "
        f"hits={validated_forecast.get('hit_count')} misses={validated_forecast.get('miss_count')} "
        f"hit_rate={validated_forecast.get('hit_rate')}"
    )
    for claim in (probability_forecast.get("forecast_claims") or [])[:8]:
        lines.append(
            f"- claim {claim.get('interval')}: side={claim.get('side')} prob={claim.get('probability')} "
            f"confidence={claim.get('confidence')} truth={claim.get('truth_status')}"
        )
    for contradiction in (probability_forecast.get("contradiction_matrix") or [])[:8]:
        lines.append(f"- contradiction {contradiction.get('id')}: {contradiction.get('reason')}")
    for blocker in (probability_forecast.get("blockers") or [])[:8]:
        lines.append(f"- blocker {blocker.get('id')}: {blocker.get('reason')}")
    live_deck = report.get("gold_live_stream_command_deck", {})
    capital_profile = live_deck.get("capital_data_profile") or {}
    leverage_margin = live_deck.get("leverage_margin_status") or {}
    lines.extend(["", "## GOLD Live Stream Command Deck"])
    lines.append(f"- status: {live_deck.get('status')}")
    lines.append(f"- target: {(live_deck.get('target') or {}).get('venue')} {(live_deck.get('target') or {}).get('symbol')} targeting={(live_deck.get('target') or {}).get('targeting_state')}")
    lines.append(f"- now: {(live_deck.get('what_am_i_doing_now') or {}).get('state')} result={(live_deck.get('act_result') or {}).get('state')}")
    lines.append(f"- next: {(live_deck.get('what_am_i_doing_next') or {}).get('targeting')}")
    lines.append(
        f"- capital_profile: bid={capital_profile.get('bid')} ask={capital_profile.get('ask')} "
        f"snapshot_fresh={capital_profile.get('snapshot_fresh')} age={capital_profile.get('snapshot_age_seconds')}"
    )
    lines.append(
        f"- margin_profile: leverage={leverage_margin.get('leverage_estimate')} "
        f"margin_factor={leverage_margin.get('margin_factor_pct')} "
        f"min_margin={leverage_margin.get('margin_required_for_min_deal')}"
    )
    lines.append(f"- hnc_feedback_act: {(live_deck.get('hnc_feedback_loop') or {}).get('act')}")
    for channel in (live_deck.get("stream_channels") or [])[:8]:
        lines.append(f"- stream {channel.get('id')}: status={channel.get('status')} fresh={channel.get('fresh')} next={channel.get('next_action')}")
    for chart in (live_deck.get("chart_streams") or [])[:6]:
        lines.append(f"- chart {chart.get('id')}: type={chart.get('chart_type')} fresh={chart.get('fresh')}")
    for blocker in (live_deck.get("blockers") or [])[:8]:
        lines.append(f"- blocker {blocker.get('id')}: {blocker.get('reason')}")
    action_loop = report.get("gold_margin_signal_action_loop", {})
    margin_intent = action_loop.get("margin_intent") or {}
    authority = action_loop.get("action_authority") or {}
    lines.extend(["", "## GOLD Margin Signal Action Loop"])
    lines.append(f"- status: {action_loop.get('status')}")
    lines.append(f"- acting_state: {action_loop.get('acting_state')}")
    lines.append(
        f"- stages_ready: {action_loop.get('ready_stage_count')}/"
        f"{action_loop.get('stage_count')} shadow_intent_allowed={authority.get('shadow_margin_intent_allowed')}"
    )
    lines.append(
        f"- margin_intent: {margin_intent.get('target_venue')} {margin_intent.get('target_symbol')} "
        f"side={margin_intent.get('side')} state={margin_intent.get('intent_state')}"
    )
    lines.append(
        f"- authority: live_order_allowed={authority.get('live_order_allowed')} "
        f"margin_order_allowed={authority.get('margin_order_allowed')} "
        f"leverage_change_allowed={authority.get('leverage_change_allowed')}"
    )
    lines.append(f"- hnc_feedback: {(action_loop.get('hnc_auris_node_feedback') or {}).get('feedback_action')}")
    for stage in (action_loop.get("signal_to_action_pipeline") or [])[:8]:
        lines.append(f"- stage {stage.get('id')}: ready={stage.get('ready')} state={stage.get('state')} proof={stage.get('proof')}")
    for blocker in (action_loop.get("blockers") or [])[:8]:
        lines.append(f"- blocker {blocker.get('id')}: {blocker.get('reason')}")
    flow_guard = report.get("gold_process_logic_flow_guard", {})
    lines.extend(["", "## GOLD Process Logic Flow Guard"])
    lines.append(f"- status: {flow_guard.get('status')}")
    lines.append(f"- flow_state: {flow_guard.get('flow_state')}")
    lines.append(
        f"- flow_correct: {flow_guard.get('flow_correct')} ready_gates={flow_guard.get('ready_gate_count')}/"
        f"{flow_guard.get('gate_count')} fake_passes={flow_guard.get('fake_pass_count')}"
    )
    lines.append(f"- first_blocked_gate: {(flow_guard.get('first_blocked_gate') or {}).get('id')}")
    lines.append(f"- next_validation_action: {flow_guard.get('next_validation_action')}")
    for stage in (flow_guard.get("gate_sequence") or [])[:10]:
        lines.append(f"- gate {stage.get('order')} {stage.get('id')}: ready={stage.get('ready')} state={stage.get('state')}")
    for violation in (flow_guard.get("violations") or [])[:8]:
        lines.append(f"- violation {violation.get('id')}: {violation.get('reason')}")
    sensemaking = report.get("gold_data_sensemaking_router", {})
    lines.extend(["", "## GOLD Data Sensemaking Router"])
    lines.append(f"- status: {sensemaking.get('status')}")
    lines.append(f"- sensemaking_state: {sensemaking.get('sensemaking_state')}")
    lines.append(
        f"- sources: present={sensemaking.get('present_source_count')}/"
        f"{sensemaking.get('source_count')} fresh={sensemaking.get('fresh_source_count')} "
        f"routed={sensemaking.get('routed_source_count')} destinations={sensemaking.get('destination_count')}"
    )
    lines.append(f"- score: {sensemaking.get('sensemaking_score')}")
    for route in (sensemaking.get("source_routes") or [])[:10]:
        lines.append(
            f"- route {route.get('id')}: family={route.get('data_family')} "
            f"fresh={route.get('fresh')} destinations={','.join(str(item) for item in route.get('destinations', [])[:5])}"
        )
    for packet in (sensemaking.get("meaning_packets") or [])[:8]:
        lines.append(f"- meaning {packet.get('id')}: ready={packet.get('ready')} -> {packet.get('destination')} ({packet.get('meaning')})")
    for blocker in (sensemaking.get("blockers") or [])[:8]:
        lines.append(f"- blocker {blocker.get('id')}: {blocker.get('reason')}")
    action_command = report.get("gold_action_command", {})
    lines.extend(["", "## Gold Action Command"])
    lines.append(f"- status: {action_command.get('status')}")
    lines.append(f"- state: {(action_command.get('act') or {}).get('state')}")
    lines.append(f"- instruction: {(action_command.get('act') or {}).get('instruction')}")
    for item in (action_command.get("proof_chain") or [])[:8]:
        lines.append(f"- proof {item.get('id')}: {item.get('state')} ({item.get('proof')})")
    agent_support = report.get("gold_agent_coding_support", {})
    lines.extend(["", "## Gold Agent Coding Support"])
    lines.append(f"- status: {agent_support.get('status')}")
    lines.append(f"- support_ready: {agent_support.get('support_ready')}")
    lines.append(f"- chat_lanes: {agent_support.get('chat_lane_count')} tool_lanes: {agent_support.get('tool_lane_count')}")
    lines.append(
        f"- surfaces: {agent_support.get('present_surface_count')}/"
        f"{agent_support.get('surface_count')} artifacts={agent_support.get('present_artifact_count')}/"
        f"{agent_support.get('artifact_count')}"
    )
    for lane in (agent_support.get("chat_lanes") or [])[:4]:
        lines.append(f"- chat {lane.get('id')}: {lane.get('status')} ({lane.get('use_for_gold')})")
    for lane in (agent_support.get("tool_lanes") or [])[:4]:
        lines.append(f"- tool {lane.get('id')}: {lane.get('status')} ({lane.get('use_for_gold')})")
    for target in (agent_support.get("monitor_targets") or [])[:6]:
        lines.append(f"- monitor {target.get('id')}: {target.get('status')} ready={target.get('ready')}")
    for blocker in (agent_support.get("blockers") or [])[:8]:
        lines.append(f"- blocker {blocker.get('id')}: {blocker.get('reason')}")
    shadow_focus = report.get("gold_shadow_trading_focus", {})
    lines.extend(["", "## Gold Shadow Trading Focus"])
    lines.append(f"- status: {shadow_focus.get('status')}")
    lines.append(f"- mode: {shadow_focus.get('mode')}")
    lines.append(f"- target_symbol: {shadow_focus.get('target_symbol')}")
    lines.append(f"- gold_related_shadow_count: {shadow_focus.get('gold_related_shadow_count')}")
    lines.append(f"- context_shadow_count: {shadow_focus.get('context_shadow_count')}")
    lines.append(f"- excluded_shadow_count: {shadow_focus.get('excluded_shadow_count')}")
    lines.append(f"- promotion_state: {(shadow_focus.get('promotion_gate') or {}).get('state')}")
    for blocker in ((shadow_focus.get("promotion_gate") or {}).get("blockers") or [])[:8]:
        lines.append(f"- blocker {blocker.get('id')}: {blocker.get('reason')}")
    cognitive_route = report.get("hnc_auris_quantum_probability_route", {})
    lines.extend(["", "## HNC/Auris Quantum Probability Route"])
    lines.append(f"- status: {cognitive_route.get('status')}")
    lines.append(f"- route_passed: {cognitive_route.get('route_passed')}")
    lines.append(f"- auris_nodes: {(cognitive_route.get('auris_nodes') or {}).get('node_count')} coherence={(cognitive_route.get('auris_nodes') or {}).get('coherence')}")
    lines.append(f"- lambda_fresh: {(cognitive_route.get('lambda_system') or {}).get('fresh')} latest_lambda={(cognitive_route.get('lambda_system') or {}).get('latest_lambda')}")
    lines.append(f"- quantum_surfaces: {(cognitive_route.get('quantum_systems') or {}).get('present_surface_count')}/{(cognitive_route.get('quantum_systems') or {}).get('surface_count')}")
    lines.append(f"- probability_gold_rows: {(cognitive_route.get('probability_systems') or {}).get('gold_row_count')}")
    for blocker in (cognitive_route.get("blockers") or [])[:8]:
        lines.append(f"- blocker {blocker.get('id')}: {blocker.get('reason')}")
    hft_gate = report.get("hft_speed_prediction_gate", {})
    hft_validation = hft_gate.get("prediction_validation") or {}
    lines.extend(["", "## HFT Speed And Validated Predictions Gate"])
    lines.append(f"- status: {hft_gate.get('status')}")
    lines.append(f"- gate_passed: {hft_gate.get('gate_passed')}")
    lines.append(f"- speed_score: {hft_gate.get('speed_score')}")
    lines.append(f"- latency_budget_ms: {hft_gate.get('latency_budget_ms')}")
    lines.append(f"- fresh_gold_predictions: {hft_validation.get('fresh_gold_prediction_count')}")
    lines.append(f"- validated_gold_predictions: {hft_validation.get('validated_gold_prediction_count')}")
    lines.append(f"- validated_correct_gold_predictions: {hft_validation.get('validated_correct_gold_prediction_count')}")
    for blocker in (hft_gate.get("blockers") or [])[:8]:
        lines.append(f"- blocker {blocker.get('id')}: {blocker.get('reason')}")
    historical_stress = report.get("gold_historical_stress_test", {})
    historical_validation = historical_stress.get("prediction_validation") or {}
    lines.extend(["", "## Gold Historical Stress Test"])
    lines.append(f"- status: {historical_stress.get('status')}")
    lines.append(f"- stress_passed: {historical_stress.get('stress_passed')}")
    lines.append(f"- prediction_rows: {historical_validation.get('row_count')}")
    lines.append(f"- validated_rows: {historical_validation.get('validated_count')}")
    lines.append(f"- hit_rate: {historical_validation.get('hit_rate')}")
    lines.append(
        f"- replay_surfaces: {historical_stress.get('present_surface_count')}/"
        f"{historical_stress.get('surface_count')}"
    )
    for scenario in (historical_stress.get("scenarios") or [])[:8]:
        lines.append(f"- scenario {scenario.get('id')}: {scenario.get('state')} ({scenario.get('proof')})")
    for blocker in (historical_stress.get("blockers") or [])[:8]:
        lines.append(f"- blocker {blocker.get('id')}: {blocker.get('reason')}")
    lines.extend(["", "## Local Research Packets"])
    for packet in report.get("local_research_packets", []):
        lines.append(f"- {packet.get('id')}: present={packet.get('present')} confidence={packet.get('confidence')}")
    return "\n".join(lines) + "\n"


def build_gold_capital_intelligence_company(
    *,
    root: Optional[Path] = None,
    target_symbol: str = "GOLD",
) -> Dict[str, Any]:
    root = Path(root or _default_root()).resolve()
    now = datetime.now(timezone.utc)
    generated_at = now.isoformat()
    sources = _load_sources(root)
    registry = sources["capital_asset_registry"]
    runtime = sources["runtime_status"]
    data_ocean = sources["data_ocean_status"]
    trading_intel = sources["trading_intelligence"]
    coverage = sources["global_financial_coverage"]
    exchange_matrix = sources["exchange_data_matrix"]
    exchange_monitoring = sources["exchange_monitoring"]
    world_ecosystem = sources["world_financial_ecosystem"]
    scanner_fusion = sources["scanner_fusion_matrix"]
    shadow_report = sources["shadow_trade_report"]
    harmonic = sources["harmonic_affect"]
    gold_intelligence_map = _build_gold_intelligence_map(root)
    local_research_packets = _build_local_research_packets(root)

    asset = _apply_runtime_gold_asset_overlay(_primary_gold_asset(registry), runtime, now)
    if asset.get("live_quote_overlay_applied"):
        registry = dict(registry)
        registry["generated_at"] = asset.get("last_snapshot_at") or generated_at
        registry["status"] = "capital_asset_registry_with_runtime_gold_quote_overlay"
        sources["capital_asset_registry"] = registry
    candidates = _asset_candidates(registry)
    market_universe = _build_gold_market_universe(candidates)
    cross_market_driver_matrix = _build_cross_market_driver_matrix(
        coverage=coverage,
        exchange_matrix=exchange_matrix,
        trading_intel=trading_intel,
        candidates=candidates,
        surfaces=gold_intelligence_map,
        research_packets=local_research_packets,
    )
    snapshot_age = _age_seconds(asset.get("last_snapshot_at"), now) if asset else None
    snapshot_fresh = snapshot_age is not None and snapshot_age <= 900
    runtime_stale = bool(runtime.get("stale") or _summary(trading_intel).get("runtime_stale") or _summary(exchange_matrix).get("runtime_stale"))
    stale_reason = str(runtime.get("stale_reason") or _summary(trading_intel).get("stale_reason") or _summary(exchange_matrix).get("stale_reason") or "")
    trading_summary = _summary(trading_intel)
    coverage_summary = _summary(coverage)
    matrix_summary = _summary(exchange_matrix)
    monitoring_summary = _summary(exchange_monitoring)
    harmonic_summary = _summary(harmonic)
    gold_exchange_optimization = _build_gold_exchange_optimization(
        asset=asset,
        candidates=candidates,
        exchange_matrix=exchange_matrix,
        exchange_monitoring=exchange_monitoring,
        driver_matrix=cross_market_driver_matrix,
        runtime_stale=runtime_stale,
        snapshot_fresh=snapshot_fresh,
        generated_at=generated_at,
    )
    cognitive_route = _build_hnc_auris_quantum_probability_route(
        root=root,
        sources=sources,
        harmonic_summary=harmonic_summary,
        generated_at=generated_at,
        now=now,
    )
    gold_intelligence_coverage_score = _score_gold_intelligence_coverage(gold_intelligence_map, local_research_packets)
    cross_market_driver_score = _clamp(
        sum(_num(driver.get("score")) for driver in cross_market_driver_matrix) / max(1, len(cross_market_driver_matrix))
    )
    historical_signal_lab = _build_historical_signal_lab(
        asset=asset,
        snapshot_fresh=snapshot_fresh,
        runtime_stale=runtime_stale,
        coverage=coverage,
        exchange_matrix=exchange_matrix,
        trading_intel=trading_intel,
        world_ecosystem=world_ecosystem,
        scanner_fusion=scanner_fusion,
        shadow_report=shadow_report,
        data_ocean=data_ocean,
        driver_matrix=cross_market_driver_matrix,
    )
    historical_signal_score = _clamp(
        _num(historical_signal_lab.get("ready_lane_count")) / max(1.0, _num(historical_signal_lab.get("lane_count"), 1.0))
    )

    spread_pct = _num(asset.get("spread_pct"))
    spread_score = _clamp(1.0 - (spread_pct / 0.25)) if spread_pct else 0.5
    capital_snapshot_score = 0.0
    if asset:
        capital_snapshot_score = 0.35
        if asset.get("trade_ready"):
            capital_snapshot_score += 0.2
        if str(asset.get("market_status", "")).upper() == "TRADEABLE":
            capital_snapshot_score += 0.15
        capital_snapshot_score += spread_score * 0.1
        if snapshot_fresh:
            capital_snapshot_score += 0.2
        elif snapshot_age is not None:
            capital_snapshot_score -= 0.2
    capital_snapshot_score = _clamp(capital_snapshot_score)

    data_ocean_score = _clamp(
        (_num(coverage_summary.get("coverage_percent")) / 100.0) * 0.45
        + (_num(coverage_summary.get("active_live_source_count")) / 4.0) * 0.2
        + (_num(coverage_summary.get("fresh_exchange_count")) / 4.0) * 0.2
        + (_num(coverage_summary.get("usable_domain_count")) / max(1.0, _num(coverage_summary.get("domain_count"), 6.0))) * 0.15
    )

    decision_score = _clamp(
        _num(trading_summary.get("decision_self_trust_score")) * 0.5
        + (0.25 if trading_summary.get("trust_to_decide") else 0.0)
        + (0.2 if trading_summary.get("trust_to_shadow") else 0.0)
        + (0.05 if trading_summary.get("trust_to_act") else 0.0)
    )
    hnc_base_score = _clamp(
        _num(harmonic_summary.get("hnc_coherence_score")) * 0.45
        + _num(harmonic_summary.get("goal_alignment")) * 0.25
        + _num(harmonic_summary.get("reward_alignment")) * 0.2
        + _num(harmonic_summary.get("anchor_readiness")) * 0.1
    )
    cognitive_route_score = _clamp(
        (0.2 if (cognitive_route.get("hnc") or {}).get("passed") else 0.0)
        + (0.2 if (cognitive_route.get("auris_nodes") or {}).get("passed") else 0.0)
        + (0.15 if (cognitive_route.get("lambda_system") or {}).get("fresh") else 0.0)
        + (
            0.15
            * _num((cognitive_route.get("quantum_systems") or {}).get("present_surface_count"))
            / max(1.0, _num((cognitive_route.get("quantum_systems") or {}).get("surface_count"), 1.0))
        )
        + (
            0.15
            * _num((cognitive_route.get("probability_systems") or {}).get("present_surface_count"))
            / max(1.0, _num((cognitive_route.get("probability_systems") or {}).get("surface_count"), 1.0))
        )
        + (0.15 if _num((cognitive_route.get("probability_systems") or {}).get("gold_row_count")) > 0 else 0.0)
    )
    hnc_score = _clamp(hnc_base_score * 0.55 + cognitive_route_score * 0.45)
    exchange_score = _clamp(
        (_num(matrix_summary.get("connected_exchange_count")) / max(1.0, _num(matrix_summary.get("exchange_count"), 4.0))) * 0.35
        + (_num(matrix_summary.get("fresh_feed_count")) / max(1.0, _num(matrix_summary.get("exchange_count"), 4.0))) * 0.25
        + (_num(monitoring_summary.get("fresh_exchange_count")) / max(1.0, _num(monitoring_summary.get("exchange_count"), 4.0))) * 0.2
        + (0.2 if matrix_summary.get("data_ready") else 0.0)
    )
    freshness_penalty = 0.28 if runtime_stale else 0.0
    if not snapshot_fresh:
        freshness_penalty += 0.15
    blocker_count = int(_num(harmonic_summary.get("safety_blocker_count")) + _num(harmonic_summary.get("blind_spot_count")))
    blocker_penalty = min(0.18, blocker_count * 0.003)

    gold_energy_score = _clamp(
        capital_snapshot_score * 0.28
        + data_ocean_score * 0.14
        + gold_intelligence_coverage_score * 0.08
        + cross_market_driver_score * 0.1
        + decision_score * 0.16
        + hnc_score * 0.14
        + exchange_score * 0.12
        - freshness_penalty
        - blocker_penalty
    )
    confidence = _clamp(gold_energy_score * (0.35 if runtime_stale or not snapshot_fresh else 0.75))
    if runtime_stale or not snapshot_fresh:
        direction_guess = "OBSERVE_STALE"
    elif gold_energy_score >= 0.68:
        direction_guess = "BULLISH_WATCH"
    elif gold_energy_score <= 0.36:
        direction_guess = "BEARISH_WATCH"
    else:
        direction_guess = "NEUTRAL_WATCH"

    live_trade_allowed = False
    shadow_observation_allowed = bool(asset and trading_summary.get("trust_to_shadow"))
    blockers: List[Dict[str, Any]] = []
    if not asset:
        blockers.append({"id": "capital_gold_asset_missing", "reason": "No GOLD/XAU asset was found in the Capital tradable asset registry."})
    if runtime_stale:
        blockers.append({"id": "runtime_stale", "reason": stale_reason or "runtime stale blocks live Capital GOLD action"})
    if not snapshot_fresh:
        blockers.append({"id": "capital_gold_snapshot_stale", "reason": f"Capital GOLD snapshot age is {round(snapshot_age or -1, 1)} seconds."})
    if not trading_summary.get("trust_to_act"):
        blockers.append({"id": "decision_not_trusted_for_live_action", "reason": trading_summary.get("decision_posture") or "decision layer is shadow-only"})
    if harmonic_summary.get("safety_blocker_count"):
        blockers.append({"id": "hnc_auris_safety_blockers", "reason": f"{harmonic_summary.get('safety_blocker_count')} safety blocker(s) visible."})
    if not cognitive_route.get("route_passed"):
        blockers.append({"id": "hnc_auris_quantum_probability_route_blocking", "reason": "Auris nodes, lambda, HNC, quantum, and probability systems are not fully passing for GOLD logic."})
    intelligence_gaps = _build_intelligence_gaps(
        asset=asset,
        snapshot_fresh=snapshot_fresh,
        runtime_stale=runtime_stale,
        surfaces=gold_intelligence_map,
        research_packets=local_research_packets,
        coverage_summary=coverage_summary,
        driver_matrix=cross_market_driver_matrix,
    )
    for gap in historical_signal_lab.get("gaps", []):
        if isinstance(gap, dict):
            intelligence_gaps.append(
                {
                    "id": gap.get("id"),
                    "severity": gap.get("severity", "medium"),
                    "owner": "Gold Historical Signal Lab",
                    "gap": gap.get("gap"),
                    "next_action": gap.get("next_action"),
                }
            )

    signals = [
        _build_signal(
            "capital_gold_snapshot",
            "Capital GOLD snapshot",
            capital_snapshot_score,
            direction="TRADEABLE_STALE" if asset and not snapshot_fresh else "TRADEABLE_FRESH" if asset else "MISSING",
            source=str(SOURCE_PATHS["capital_asset_registry"]),
            reason=f"spread_pct={round(spread_pct, 6)} snapshot_age_sec={round(snapshot_age, 1) if snapshot_age is not None else 'unknown'}",
            fresh=snapshot_fresh,
        ),
        _build_signal(
            "data_ocean",
            "Global financial data ocean",
            data_ocean_score,
            direction="MAPPED_FOR_THOUGHT",
            source=str(SOURCE_PATHS["global_financial_coverage"]),
            reason=f"coverage={coverage_summary.get('coverage_percent')} active_live_sources={coverage_summary.get('active_live_source_count')}",
            fresh=bool(coverage_summary.get("fresh_source_count")),
        ),
        _build_signal(
            "gold_intelligence_surface_coverage",
            "Gold intelligence surface coverage",
            gold_intelligence_coverage_score,
            direction="ORGANS_MAPPED" if gold_intelligence_coverage_score >= 0.7 else "ORGANS_PARTIAL",
            source="repo gold intelligence surfaces",
            reason=(
                f"mapped={sum(1 for item in gold_intelligence_map if item.get('matched_terms'))}/"
                f"{len(gold_intelligence_map)} research={sum(1 for item in local_research_packets if item.get('matched_terms'))}/"
                f"{len(local_research_packets)}"
            ),
            fresh=True,
        ),
        _build_signal(
            "cross_market_gold_driver_matrix",
            "Cross-market gold driver matrix",
            cross_market_driver_score,
            direction="CONNECTED_DRIVERS" if cross_market_driver_score >= 0.7 else "PARTIAL_DRIVERS",
            source="global coverage, exchange matrix, trading checklist, repo surfaces",
            reason=(
                f"drivers={sum(1 for item in cross_market_driver_matrix if item.get('driver_state') == 'ready_shadow_driver')}/"
                f"{len(cross_market_driver_matrix)} ready"
            ),
            fresh=all(bool(item.get("fresh")) for item in cross_market_driver_matrix if item.get("usable_for_gold_thesis")),
        ),
        _build_signal(
            "gold_historical_signal_lab",
            "Gold historical signal lab",
            historical_signal_score,
            direction="REPLAY_READY" if historical_signal_lab.get("status") == "gold_historical_signal_lab_ready" else "REPLAY_ATTENTION",
            source="Capital price history, waveform memory, lead-lag, scanner fusion, order-book pressure",
            reason=(
                f"lanes={historical_signal_lab.get('ready_lane_count')}/"
                f"{historical_signal_lab.get('lane_count')} ready; "
                f"orderbook={historical_signal_lab.get('orderbook_signal_state')}"
            ),
            fresh=historical_signal_lab.get("status") == "gold_historical_signal_lab_ready",
        ),
        _build_signal(
            "trading_intelligence",
            "Trading intelligence trust",
            decision_score,
            direction="SHADOW_READY" if trading_summary.get("trust_to_shadow") else "NOT_READY",
            source=str(SOURCE_PATHS["trading_intelligence"]),
            reason=str(trading_summary.get("decision_posture") or "unknown posture"),
            fresh=not bool(trading_summary.get("runtime_stale")),
        ),
        _build_signal(
            "hnc_auris",
            "HNC/Auris harmonic coherence",
            hnc_score,
            direction=str(harmonic_summary.get("affect_phase") or "unknown"),
            source=str(SOURCE_PATHS["harmonic_affect"]),
            reason=f"coherence={harmonic_summary.get('hnc_coherence_score')} blockers={harmonic_summary.get('safety_blocker_count')}",
            fresh=not bool(harmonic_summary.get("runtime_stale")),
        ),
        _build_signal(
            "hnc_auris_quantum_probability_route",
            "HNC/Auris quantum probability route",
            cognitive_route_score,
            direction="ROUTE_PASSING" if cognitive_route.get("route_passed") else "ROUTE_BLOCKING",
            source="Auris nodes, lambda history, HNC proof, quantum packet, probability matrix",
            reason=(
                f"auris={(cognitive_route.get('auris_nodes') or {}).get('node_count')} "
                f"lambda_fresh={(cognitive_route.get('lambda_system') or {}).get('fresh')} "
                f"prob_gold_rows={(cognitive_route.get('probability_systems') or {}).get('gold_row_count')}"
            ),
            fresh=bool(cognitive_route.get("route_passed")),
        ),
        _build_signal(
            "exchange_matrix",
            "Exchange capability matrix",
            exchange_score,
            direction=str(matrix_summary.get("preflight_overall") or "unknown"),
            source=str(SOURCE_PATHS["exchange_data_matrix"]),
            reason=f"connected={matrix_summary.get('connected_exchange_count')} fresh_feeds={matrix_summary.get('fresh_feed_count')}",
            fresh=not bool(matrix_summary.get("runtime_stale")),
        ),
    ]
    source_evidence = _source_evidence(root, sources, now)
    verified_real_data_gate = _build_verified_real_data_gate(
        source_evidence=source_evidence,
        signals=signals,
        asset=asset,
        snapshot_age_sec=snapshot_age,
        snapshot_fresh=snapshot_fresh,
        runtime_stale=runtime_stale,
        historical_signal_lab=historical_signal_lab,
    )
    if not verified_real_data_gate["action_allowed_by_data"]:
        blockers.append(
            {
                "id": "verified_real_data_gate_blocking",
                "reason": "One or more GOLD action metrics are stale, missing timestamp proof, reference-only, or not directly verified.",
            }
        )
    hft_speed_prediction_gate = _build_hft_speed_prediction_gate(
        root=root,
        source_evidence=source_evidence,
        cognitive_route=cognitive_route,
        verified_data_gate=verified_real_data_gate,
        historical_signal_lab=historical_signal_lab,
        generated_at=generated_at,
    )
    if not hft_speed_prediction_gate["gate_passed"]:
        blockers.append(
            {
                "id": "hft_speed_prediction_gate_blocking",
                "reason": "GOLD high-frequency path is not both fast and prediction-validated.",
            }
        )
    gold_historical_stress_test = _build_gold_historical_stress_test(
        root=root,
        cognitive_route=cognitive_route,
        hft_speed_gate=hft_speed_prediction_gate,
        historical_signal_lab=historical_signal_lab,
        generated_at=generated_at,
        now=now,
    )
    if not gold_historical_stress_test["stress_passed"]:
        blockers.append(
            {
                "id": "gold_historical_stress_test_blocking",
                "reason": "GOLD historical replay has not yet proven validated prediction behavior.",
            }
        )
    swarm_intelligence = _build_gold_swarm_intelligence(
        driver_matrix=cross_market_driver_matrix,
        surfaces=gold_intelligence_map,
        research_packets=local_research_packets,
        signals=signals,
        blockers=blockers,
        intelligence_gaps=intelligence_gaps,
        runtime_stale=runtime_stale,
        snapshot_fresh=snapshot_fresh,
    )

    price_hypothesis = _price_hypothesis(asset, snapshot_age) if asset else {}
    action_posture = "shadow_observe_refresh_before_live"
    if not asset:
        action_posture = "blocked_missing_gold_asset"
    elif not blockers and confidence >= 0.55:
        action_posture = "shadow_decision_ready_live_still_runtime_gated"
    decision_packet = {
        "direction_guess": direction_guess,
        "gold_energy_score": round(gold_energy_score, 4),
        "confidence": round(confidence, 4),
        "live_trade_allowed": live_trade_allowed,
        "shadow_observation_allowed": shadow_observation_allowed,
        "reason": "Gold action remains observation/shadow until runtime and Capital snapshot freshness pass.",
        "not_financial_advice": True,
    }
    gold_priority_workbench = _build_gold_priority_workbench(
        asset=asset,
        decision=decision_packet,
        price_hypothesis=price_hypothesis,
        historical_signal_lab=historical_signal_lab,
        cross_market_driver_matrix=cross_market_driver_matrix,
        blockers=blockers,
        intelligence_gaps=intelligence_gaps,
        generated_at=generated_at,
    )
    three_p_profit_floor_gate = _build_three_p_profit_floor_gate(
        asset=asset,
        decision=decision_packet,
        price_hypothesis=price_hypothesis,
        historical_signal_lab=historical_signal_lab,
        blockers=blockers,
        runtime_stale=runtime_stale,
        snapshot_fresh=snapshot_fresh,
    )
    gold_ticker_source_mesh = _build_gold_ticker_source_mesh(
        asset=asset,
        candidates=candidates,
        source_evidence=source_evidence,
        driver_matrix=cross_market_driver_matrix,
        snapshot_fresh=snapshot_fresh,
        now=now,
    )
    gold_signal_freshness_matrix = _build_gold_signal_freshness_matrix(
        source_evidence=source_evidence,
        signals=signals,
        ticker_source_mesh=gold_ticker_source_mesh,
        verified_data_gate=verified_real_data_gate,
        historical_signal_lab=historical_signal_lab,
        generated_at=generated_at,
    )
    gold_projection_interval_validation = _build_gold_projection_interval_validation(
        cognitive_route=cognitive_route,
        gold_priority_workbench=gold_priority_workbench,
        ticker_source_mesh=gold_ticker_source_mesh,
        signal_freshness_matrix=gold_signal_freshness_matrix,
        generated_at=generated_at,
        now=now,
    )
    gold_evolving_projection_path = _build_gold_evolving_projection_path(
        cognitive_route=cognitive_route,
        gold_priority_workbench=gold_priority_workbench,
        ticker_source_mesh=gold_ticker_source_mesh,
        signal_freshness_matrix=gold_signal_freshness_matrix,
        projection_interval_validation=gold_projection_interval_validation,
        generated_at=generated_at,
        now=now,
    )
    gold_hnc_action_coherence_gate = _build_gold_hnc_action_coherence_gate(
        cognitive_route=cognitive_route,
        signal_freshness_matrix=gold_signal_freshness_matrix,
        projection_interval_validation=gold_projection_interval_validation,
        generated_at=generated_at,
    )
    gold_portfolio_uplift_guard = _build_gold_portfolio_uplift_guard(
        asset=asset,
        three_p_gate=three_p_profit_floor_gate,
        projection_interval_validation=gold_projection_interval_validation,
        runtime_stale=runtime_stale,
        snapshot_fresh=snapshot_fresh,
        generated_at=generated_at,
    )
    if not gold_projection_interval_validation["action_influence_allowed"]:
        blockers.append(
            {
                "id": "fresh_interval_validated_gold_projection_blocking",
                "reason": "GOLD projection intervals are not fully fresh, source-linked, and outcome-validated.",
            }
        )
    if not gold_hnc_action_coherence_gate["action_coherence_allowed"]:
        blockers.append(
            {
                "id": "gold_hnc_action_coherence_gate_blocking",
                "reason": "HNC/Auris cannot promote until fresh ticker proof and interval validation pass.",
            }
        )
    if not gold_portfolio_uplift_guard["order_intent_consideration_allowed"]:
        blockers.append(
            {
                "id": "gold_portfolio_uplift_guard_blocking",
                "reason": "Portfolio uplift proof is not strong enough for order-intent consideration.",
            }
        )
    gold_margin_trader_unity = _build_gold_margin_trader_unity(
        root=root,
        decision=decision_packet,
        three_p_gate=three_p_profit_floor_gate,
        verified_data_gate=verified_real_data_gate,
        gold_exchange_optimization=gold_exchange_optimization,
        cognitive_route=cognitive_route,
        hft_speed_gate=hft_speed_prediction_gate,
        historical_stress_test=gold_historical_stress_test,
        generated_at=generated_at,
    )
    gold_probability_projection_forecast = _build_gold_probability_projection_forecast(
        decision=decision_packet,
        cognitive_route=cognitive_route,
        signal_freshness_matrix=gold_signal_freshness_matrix,
        ticker_source_mesh=gold_ticker_source_mesh,
        projection_interval_validation=gold_projection_interval_validation,
        hnc_action_coherence_gate=gold_hnc_action_coherence_gate,
        portfolio_uplift_guard=gold_portfolio_uplift_guard,
        verified_data_gate=verified_real_data_gate,
        hft_speed_gate=hft_speed_prediction_gate,
        historical_stress_test=gold_historical_stress_test,
        margin_trader_unity=gold_margin_trader_unity,
        cross_market_driver_matrix=cross_market_driver_matrix,
        swarm_intelligence=swarm_intelligence,
        generated_at=generated_at,
    )
    gold_dynamic_market_edge_stream = _build_gold_dynamic_market_edge_stream(
        asset=asset,
        ticker_source_mesh=gold_ticker_source_mesh,
        signal_freshness_matrix=gold_signal_freshness_matrix,
        projection_interval_validation=gold_projection_interval_validation,
        evolving_projection_path=gold_evolving_projection_path,
        probability_projection_forecast=gold_probability_projection_forecast,
        hnc_action_coherence_gate=gold_hnc_action_coherence_gate,
        portfolio_uplift_guard=gold_portfolio_uplift_guard,
        historical_signal_lab=historical_signal_lab,
        cross_market_driver_matrix=cross_market_driver_matrix,
        generated_at=generated_at,
    )
    gold_hnc_history_future_bridge = _build_gold_hnc_history_future_bridge(
        cognitive_route=cognitive_route,
        historical_signal_lab=historical_signal_lab,
        historical_stress_test=gold_historical_stress_test,
        evolving_projection_path=gold_evolving_projection_path,
        dynamic_market_edge_stream=gold_dynamic_market_edge_stream,
        probability_projection_forecast=gold_probability_projection_forecast,
        hnc_action_coherence_gate=gold_hnc_action_coherence_gate,
        generated_at=generated_at,
    )
    gold_creative_dream_hypothesis_engine = _build_gold_creative_dream_hypothesis_engine(
        cross_market_driver_matrix=cross_market_driver_matrix,
        historical_signal_lab=historical_signal_lab,
        dynamic_market_edge_stream=gold_dynamic_market_edge_stream,
        hnc_history_future_bridge=gold_hnc_history_future_bridge,
        probability_projection_forecast=gold_probability_projection_forecast,
        local_research_packets=local_research_packets,
        swarm_intelligence=swarm_intelligence,
        generated_at=generated_at,
    )
    gold_action_command = _build_gold_action_command(
        root=root,
        decision=decision_packet,
        three_p_gate=three_p_profit_floor_gate,
        verified_data_gate=verified_real_data_gate,
        historical_signal_lab=historical_signal_lab,
        gold_priority_workbench=gold_priority_workbench,
        swarm_intelligence=swarm_intelligence,
        cognitive_route=cognitive_route,
        hft_speed_gate=hft_speed_prediction_gate,
        historical_stress_test=gold_historical_stress_test,
        margin_trader_unity=gold_margin_trader_unity,
        signal_freshness_matrix=gold_signal_freshness_matrix,
        projection_interval_validation=gold_projection_interval_validation,
        probability_projection_forecast=gold_probability_projection_forecast,
        dynamic_market_edge_stream=gold_dynamic_market_edge_stream,
        hnc_history_future_bridge=gold_hnc_history_future_bridge,
        creative_dream_hypothesis_engine=gold_creative_dream_hypothesis_engine,
        hnc_action_coherence_gate=gold_hnc_action_coherence_gate,
        portfolio_uplift_guard=gold_portfolio_uplift_guard,
        cross_market_driver_matrix=cross_market_driver_matrix,
        blockers=blockers,
        intelligence_gaps=intelligence_gaps,
        generated_at=generated_at,
    )
    gold_agent_coding_support = _build_gold_agent_coding_support(
        root=root,
        generated_at=generated_at,
        now=now,
        verified_data_gate=verified_real_data_gate,
        hft_speed_gate=hft_speed_prediction_gate,
        historical_stress_test=gold_historical_stress_test,
        gold_action_command=gold_action_command,
    )
    gold_shadow_trading_focus = _build_gold_shadow_trading_focus(
        shadow_report=shadow_report,
        scanner_fusion=scanner_fusion,
        decision=decision_packet,
        three_p_gate=three_p_profit_floor_gate,
        verified_data_gate=verified_real_data_gate,
        gold_action_command=gold_action_command,
        cognitive_route=cognitive_route,
        hft_speed_gate=hft_speed_prediction_gate,
        historical_stress_test=gold_historical_stress_test,
        cross_market_driver_matrix=cross_market_driver_matrix,
        generated_at=generated_at,
    )
    gold_live_stream_command_deck = _build_gold_live_stream_command_deck(
        asset=asset,
        runtime=runtime,
        exchange_matrix=exchange_matrix,
        exchange_monitoring=exchange_monitoring,
        trading_intel=trading_intel,
        gold_action_command=gold_action_command,
        gold_shadow_trading_focus=gold_shadow_trading_focus,
        gold_ticker_source_mesh=gold_ticker_source_mesh,
        gold_signal_freshness_matrix=gold_signal_freshness_matrix,
        gold_projection_interval_validation=gold_projection_interval_validation,
        gold_dynamic_market_edge_stream=gold_dynamic_market_edge_stream,
        gold_hnc_action_coherence_gate=gold_hnc_action_coherence_gate,
        gold_portfolio_uplift_guard=gold_portfolio_uplift_guard,
        gold_margin_trader_unity=gold_margin_trader_unity,
        historical_signal_lab=historical_signal_lab,
        three_p_gate=three_p_profit_floor_gate,
        snapshot_age=snapshot_age,
        snapshot_fresh=snapshot_fresh,
        runtime_stale=runtime_stale,
        generated_at=generated_at,
    )
    gold_margin_signal_action_loop = _build_gold_margin_signal_action_loop(
        decision=decision_packet,
        three_p_gate=three_p_profit_floor_gate,
        verified_data_gate=verified_real_data_gate,
        gold_signal_freshness_matrix=gold_signal_freshness_matrix,
        gold_projection_interval_validation=gold_projection_interval_validation,
        gold_hnc_action_coherence_gate=gold_hnc_action_coherence_gate,
        gold_portfolio_uplift_guard=gold_portfolio_uplift_guard,
        gold_margin_trader_unity=gold_margin_trader_unity,
        gold_action_command=gold_action_command,
        gold_live_stream_command_deck=gold_live_stream_command_deck,
        gold_dynamic_market_edge_stream=gold_dynamic_market_edge_stream,
        cognitive_route=cognitive_route,
        hft_speed_gate=hft_speed_prediction_gate,
        historical_stress_test=gold_historical_stress_test,
        runtime_stale=runtime_stale,
        snapshot_fresh=snapshot_fresh,
        generated_at=generated_at,
    )
    gold_process_logic_flow_guard = _build_gold_process_logic_flow_guard(
        verified_data_gate=verified_real_data_gate,
        ticker_source_mesh=gold_ticker_source_mesh,
        signal_freshness_matrix=gold_signal_freshness_matrix,
        projection_interval_validation=gold_projection_interval_validation,
        evolving_projection_path=gold_evolving_projection_path,
        dynamic_market_edge_stream=gold_dynamic_market_edge_stream,
        hnc_history_future_bridge=gold_hnc_history_future_bridge,
        creative_dream_hypothesis_engine=gold_creative_dream_hypothesis_engine,
        probability_projection_forecast=gold_probability_projection_forecast,
        hnc_action_coherence_gate=gold_hnc_action_coherence_gate,
        portfolio_uplift_guard=gold_portfolio_uplift_guard,
        margin_trader_unity=gold_margin_trader_unity,
        gold_action_command=gold_action_command,
        gold_live_stream_command_deck=gold_live_stream_command_deck,
        gold_margin_signal_action_loop=gold_margin_signal_action_loop,
        generated_at=generated_at,
    )
    gold_data_sensemaking_router = _build_gold_data_sensemaking_router(
        source_evidence=source_evidence,
        local_research_packets=local_research_packets,
        signals=signals,
        cross_market_driver_matrix=cross_market_driver_matrix,
        gold_ticker_source_mesh=gold_ticker_source_mesh,
        gold_signal_freshness_matrix=gold_signal_freshness_matrix,
        gold_projection_interval_validation=gold_projection_interval_validation,
        gold_evolving_projection_path=gold_evolving_projection_path,
        gold_dynamic_market_edge_stream=gold_dynamic_market_edge_stream,
        gold_hnc_history_future_bridge=gold_hnc_history_future_bridge,
        gold_creative_dream_hypothesis_engine=gold_creative_dream_hypothesis_engine,
        gold_probability_projection_forecast=gold_probability_projection_forecast,
        hnc_action_coherence_gate=gold_hnc_action_coherence_gate,
        gold_process_logic_flow_guard=gold_process_logic_flow_guard,
        generated_at=generated_at,
    )

    report: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": "gold_capital_intelligence_ready" if asset else "gold_capital_intelligence_blocked_missing_gold_asset",
        "ok": bool(asset),
        "generated_at": generated_at,
        "provider_policy": "local_evidence_first_reference_only_external_docs",
        "target": {
            "venue": "Capital.com",
            "symbol": asset.get("symbol") or target_symbol,
            "epic": asset.get("epic") or target_symbol,
            "instrument_name": asset.get("instrument_name") or "Gold",
            "asset_class": asset.get("asset_class") or "commodity_cfd",
            "market_status": asset.get("market_status"),
            "trade_ready": bool(asset.get("trade_ready")),
        },
        "capital_gold_candidates": [
            {
                "symbol": item.get("symbol"),
                "epic": item.get("epic"),
                "instrument_name": item.get("instrument_name"),
                "market_status": item.get("market_status"),
                "mid_price": item.get("mid_price"),
                "last_snapshot_at": item.get("last_snapshot_at"),
            }
            for item in candidates[:10]
        ],
        "company_roles": GOLD_COMPANY_ROLES,
        "who_what_where_when_how_act": {
            "who": "Aureon Gold Capital Intelligence Company",
            "what": "Gather all local Aureon evidence needed to estimate Capital GOLD price/energy.",
            "where": [str(path) for path in SOURCE_PATHS.values()],
            "when": generated_at,
            "how": "Blend Capital GOLD snapshot, chart/OHLC replay, cross-asset lead-lag, order-book pressure, exchange readiness, global data ocean, trading trust, HNC/Auris coherence, and stale-data blockers.",
            "act": action_posture,
        },
        "source_packets": CAPITAL_REFERENCE_PACKETS,
        "local_research_packets": local_research_packets,
        "source_evidence": source_evidence,
        "gold_intelligence_map": gold_intelligence_map,
        "gold_market_universe": market_universe,
        "cross_market_driver_matrix": cross_market_driver_matrix,
        "gold_exchange_optimization": gold_exchange_optimization,
        "gold_margin_trader_unity": gold_margin_trader_unity,
        "gold_signal_freshness_matrix": gold_signal_freshness_matrix,
        "gold_projection_interval_validation": gold_projection_interval_validation,
        "gold_evolving_projection_path": gold_evolving_projection_path,
        "gold_dynamic_market_edge_stream": gold_dynamic_market_edge_stream,
        "gold_hnc_history_future_bridge": gold_hnc_history_future_bridge,
        "gold_creative_dream_hypothesis_engine": gold_creative_dream_hypothesis_engine,
        "gold_probability_projection_forecast": gold_probability_projection_forecast,
        "gold_ticker_source_mesh": gold_ticker_source_mesh,
        "gold_portfolio_uplift_guard": gold_portfolio_uplift_guard,
        "gold_hnc_action_coherence_gate": gold_hnc_action_coherence_gate,
        "historical_signal_lab": historical_signal_lab,
        "gold_priority_workbench": gold_priority_workbench,
        "three_p_profit_floor_gate": three_p_profit_floor_gate,
        "verified_real_data_gate": verified_real_data_gate,
        "gold_action_command": gold_action_command,
        "gold_agent_coding_support": gold_agent_coding_support,
        "gold_shadow_trading_focus": gold_shadow_trading_focus,
        "gold_live_stream_command_deck": gold_live_stream_command_deck,
        "gold_margin_signal_action_loop": gold_margin_signal_action_loop,
        "gold_process_logic_flow_guard": gold_process_logic_flow_guard,
        "gold_data_sensemaking_router": gold_data_sensemaking_router,
        "hnc_auris_quantum_probability_route": cognitive_route,
        "hft_speed_prediction_gate": hft_speed_prediction_gate,
        "gold_historical_stress_test": gold_historical_stress_test,
        "swarm_intelligence": swarm_intelligence,
        "signals": signals,
        "price_energy_hypothesis": price_hypothesis,
        "decision": decision_packet,
        "blockers": blockers,
        "intelligence_gaps": intelligence_gaps,
        "tool_activation_plan": [
            {
                "id": "refresh_gold_market_universe",
                "phase": "market_data",
                "tools": ["capital_asset_registry", "capital_market_monitor", "global_financial_feed"],
                "expected_output": "Fresh Capital GOLD quote, related gold instruments, spread, market status, and timestamp proof.",
                "authority": "read_only_or_existing_runtime_gated",
            },
            {
                "id": "build_gold_macro_packet",
                "phase": "macro_context",
                "tools": ["world_data_ingester", "macro_intelligence", "aureon_seer_macro"],
                "expected_output": "USD/DXY, yields, inflation, oil, VIX, calendar, and news context with source timestamps.",
                "authority": "read_only_research",
            },
            {
                "id": "run_gold_forecast_fusion",
                "phase": "forecast",
                "tools": ["universal_forecast", "advanced_intelligence", "cross_asset_correlator", "unified_signal_engine"],
                "expected_output": "Shadow-only direction thesis with confidence, contradiction checks, and no order mutation.",
                "authority": "non_mutating_validation",
            },
            {
                "id": "validate_gold_projection_intervals",
                "phase": "fresh_signal_validation",
                "tools": ["probability_validator", "probability_matrix_backtest", "capital_market_monitor", "live_stream_cache", "HNC/Auris"],
                "expected_output": "Tick, 1m, 5m, 15m, 1h, and session GOLD projections with source tickers, outcome validation, hit/miss, and shadow P/L proof.",
                "authority": "non_mutating_validation",
            },
            {
                "id": "run_dynamic_gold_edge_stream",
                "phase": "dynamic_edge_watch",
                "tools": ["capital_market_monitor", "live_stream_cache", "scanner_fusion_matrix", "margin_wave_rider", "HNC/Auris"],
                "expected_output": "Fresh GOLD target stream plus related context lanes, waveform edge score, trigger side, blockers, and shadow-only margin candidate.",
                "authority": "non_mutating_validation",
            },
            {
                "id": "compile_hnc_history_future_bridge",
                "phase": "history_to_future",
                "tools": ["historical_signal_lab", "gold_historical_stress_test", "HNC/Auris", "lambda_engine", "probability_validator"],
                "expected_output": "Validated history analogs mapped into future GOLD windows with HNC confidence effect and blockers.",
                "authority": "non_mutating_validation",
            },
            {
                "id": "generate_gold_creative_dream_hypotheses",
                "phase": "creative_hypothesis",
                "tools": ["gold_creative_dream_hypothesis_engine", "MeaningResolver", "HNC/Auris", "agent_company", "local_research_packets"],
                "expected_output": "Many source-grounded GOLD edge dreams converted into validation queue items without action authority.",
                "authority": "idea_generation_non_mutating_validation",
            },
            {
                "id": "run_gold_historical_signal_replay",
                "phase": "historical_signal_lab",
                "tools": ["capital_price_history", "scanner_fusion_matrix", "world_financial_ecosystem", "unified_shadow_trade_report"],
                "expected_output": "Chart replay, lead-lag candidates, order-book pressure proof, waveform regime state, and attribution gaps.",
                "authority": "non_mutating_validation",
            },
            {
                "id": "optimize_gold_exchange_monitoring",
                "phase": "exchange_monitoring",
                "tools": ["capital_market_monitor", "exchange_data_matrix", "exchange_monitoring_checklist", "data_ocean", "scanner_fusion_matrix"],
                "expected_output": "Dynamic Capital GOLD target monitoring plus Alpaca ETF/miner, Binance/Kraken crypto-liquidity, energy, USD/rates, and risk proxy watchlists.",
                "authority": "read_only_or_existing_runtime_gated",
            },
            {
                "id": "unify_margin_trader_for_gold",
                "phase": "margin_unity",
                "tools": ["unified_margin_brain", "dynamic_margin_sizer", "margin_wave_rider", "real_profit_monitor", "position_reconciler"],
                "expected_output": "All margin, sizing, risk, profit, and position systems point at Capital GOLD as the target mission while live mutation remains gated.",
                "authority": "shadow_margin_validation_only",
            },
            {
                "id": "compile_gold_hnc_auris_gate",
                "phase": "cognitive_gate",
                "tools": ["harmonic_affect_state", "sensory_framework", "market_harp"],
                "expected_output": "Coherence, sensory pressure, stale-data penalty, and safety blocker report.",
                "authority": "coherence_gate",
            },
            {
                "id": "agent_code_tool_support_for_gold",
                "phase": "agent_support",
                "tools": ["coding_organism_bridge", "autonomous_job_executor", "capability_forge", "dynamic_prompt_filter", "ThoughtBus"],
                "expected_output": "Agent-created GOLD support jobs, local tools, UI panels, tests, and clear chat summaries with proof.",
                "authority": "code_work_enabled_no_live_trading_mutation",
            },
        ],
        "next_actions": [
            {
                "id": "refresh_capital_gold_snapshot",
                "owner": "Capital Venue Specialist",
                "action": "Refresh Capital.com GOLD market details and marketData/OHLC subscription evidence.",
                "authority": "read_only_or_existing_runtime_gated",
            },
            {
                "id": "wire_gold_macro_context",
                "owner": "Macro And Dollar Analyst",
                "action": "Add fresh USD/rates/calendar/sentiment packets to the gold thesis.",
                "authority": "read_only_research",
            },
            {
                "id": "activate_gold_forecast_organs",
                "owner": "Gold Strategy Steward",
                "action": "Run universal forecast, seer macro, sensory framework, and cross-asset correlation as separate shadow signals.",
                "authority": "non_mutating_validation",
            },
            {
                "id": "validate_fresh_gold_projection_intervals",
                "owner": "HNC/Auris Counter-Intelligence Gate",
                "action": "Validate every GOLD projection across tick, 1m, 5m, 15m, 1h, and session windows before allowing action influence.",
                "authority": "non_mutating_validation",
            },
            {
                "id": "stream_dynamic_gold_market_edges",
                "owner": "Gold Waveform Edge Watcher",
                "action": "Stream Capital GOLD, GC/GLD/miners, USD/rates, oil/energy, VIX/equities, crypto liquidity, macro/news, waveform, and order-pressure lanes into one shadow edge map.",
                "authority": "non_mutating_validation",
            },
            {
                "id": "compile_history_future_through_hnc",
                "owner": "HNC/Auris Historical Future Bridge",
                "action": "Use validated GOLD history, replay lanes, waveform memory, and Auris coherence to shape the next future windows while blocking fake certainty.",
                "authority": "non_mutating_validation",
            },
            {
                "id": "dream_many_gold_edges",
                "owner": "Creative GOLD Hypothesis Crew",
                "action": "Generate many GOLD edge dreams from repo research, drivers, history, dynamic edge, and probability evidence, then queue the best for fresh validation.",
                "authority": "idea_generation_non_mutating_validation",
            },
            {
                "id": "shadow_validate_gold_hypothesis",
                "owner": "Shadow Trade Validator",
                "action": "Run non-mutating shadow validation against the next fresh Capital GOLD tick.",
                "authority": "non_mutating_validation",
            },
            {
                "id": "optimize_gold_exchange_watchlists",
                "owner": "Capital Venue Specialist",
                "action": "Keep Capital GOLD as the primary venue and dynamically monitor GLD/IAU/GDX/miners, oil/energy, USD/rates, VIX/indices, and Binance/Kraken crypto liquidity as confirmation lanes.",
                "authority": "read_only_or_existing_runtime_gated",
            },
            {
                "id": "command_margin_trader_gold_unity",
                "owner": "Risk Governor",
                "action": "Tell unified margin brain, dynamic margin sizer, margin wave rider, profit monitor, and position reconciler to work as one GOLD-focused shadow validation lane.",
                "authority": "shadow_margin_validation_only",
            },
            {
                "id": "focus_shadow_lane_on_gold_energy",
                "owner": "Shadow Trade Validator",
                "action": "Keep GOLD as the only target candidate and use oil/energy, USD/rates, VIX, crypto, miners, and geopolitics as confirmation context.",
                "authority": "non_mutating_validation",
            },
            {
                "id": "replay_gold_historical_signals",
                "owner": "Gold Historical Signal Lab",
                "action": "Run GOLD OHLC, lead-lag, order-book, scanner, waveform, and driver-attribution replay lanes.",
                "authority": "non_mutating_validation",
            },
            {
                "id": "publish_trading_tab_panel",
                "owner": "Operator Evidence Clerk",
                "action": "Keep this packet visible in the Trading tab with blockers and price hypothesis.",
                "authority": "ui_evidence_only",
            },
            {
                "id": "route_gold_agent_tool_requests",
                "owner": "Gold Strategy Steward",
                "action": "Use the coding organism, capability forge, dynamic prompt filter, and ThoughtBus when agents need tools, chat, repair jobs, or monitoring support for GOLD evidence.",
                "authority": "code_work_enabled_no_live_trading_mutation",
            },
        ],
        "manual_boundaries": [
            "No live Capital.com GOLD order is placed by this report.",
            "No credential value is read or emitted.",
            "CFD execution remains runtime-gated and risk-governed.",
            "No fake, stale, synthetic, visual-only, or reference-only metric may unlock action.",
            "This is evidence and hypothesis support, not financial advice.",
        ],
        "summary": {
            "target_symbol": asset.get("symbol") or target_symbol,
            "target_epic": asset.get("epic") or target_symbol,
            "candidate_count": len(candidates),
            "capital_snapshot_fresh": snapshot_fresh,
            "capital_snapshot_age_sec": round(snapshot_age, 3) if snapshot_age is not None else None,
            "runtime_stale": runtime_stale,
            "stale_reason": stale_reason,
            "gold_energy_score": round(gold_energy_score, 4),
            "confidence": round(confidence, 4),
            "direction_guess": direction_guess,
            "action_posture": action_posture,
            "live_trade_allowed": live_trade_allowed,
            "shadow_observation_allowed": shadow_observation_allowed,
            "blocker_count": len(blockers),
            "intelligence_gap_count": len(intelligence_gaps),
            "source_count": len([item for item in source_evidence if item["present"]]),
            "gold_intelligence_surface_count": len(gold_intelligence_map),
            "gold_intelligence_surface_ready_count": sum(1 for item in gold_intelligence_map if item.get("matched_terms")),
            "gold_intelligence_coverage_score": round(gold_intelligence_coverage_score, 4),
            "cross_market_driver_score": round(cross_market_driver_score, 4),
            "cross_market_driver_count": len(cross_market_driver_matrix),
            "cross_market_driver_ready_count": sum(1 for item in cross_market_driver_matrix if item.get("driver_state") == "ready_shadow_driver"),
            "gold_exchange_optimization_status": gold_exchange_optimization["status"],
            "gold_exchange_optimization_score": gold_exchange_optimization["optimization_score"],
            "gold_exchange_ready_venue_count": gold_exchange_optimization["ready_venue_count"],
            "gold_exchange_venue_count": gold_exchange_optimization["venue_count"],
            "gold_exchange_watchlist_bucket_count": gold_exchange_optimization["watchlist_bucket_count"],
            "gold_exchange_optimization_blocker_count": len(gold_exchange_optimization["blockers"]),
            "gold_margin_trader_unity_status": gold_margin_trader_unity["status"],
            "gold_margin_unity_state": gold_margin_trader_unity["unity_state"],
            "gold_margin_unity_surface_count": gold_margin_trader_unity["surface_count"],
            "gold_margin_unity_present_surface_count": gold_margin_trader_unity["present_surface_count"],
            "gold_margin_unity_blocker_count": len(gold_margin_trader_unity["blockers"]),
            "gold_margin_live_order_allowed": gold_margin_trader_unity["margin_command"]["live_order_allowed"],
            "gold_margin_order_allowed": gold_margin_trader_unity["margin_command"]["margin_order_allowed"],
            "gold_signal_freshness_status": gold_signal_freshness_matrix["status"],
            "gold_signal_fresh_row_count": gold_signal_freshness_matrix["fresh_row_count"],
            "gold_signal_row_count": gold_signal_freshness_matrix["row_count"],
            "gold_signal_action_influence_row_count": gold_signal_freshness_matrix["action_influence_row_count"],
            "gold_signal_action_influence_allowed": gold_signal_freshness_matrix["action_influence_allowed"],
            "gold_ticker_source_mesh_status": gold_ticker_source_mesh["status"],
            "gold_ticker_source_fresh_lane_count": gold_ticker_source_mesh["fresh_lane_count"],
            "gold_ticker_source_lane_count": gold_ticker_source_mesh["lane_count"],
            "gold_projection_interval_status": gold_projection_interval_validation["status"],
            "gold_projection_validated_interval_count": gold_projection_interval_validation["validated_interval_count"],
            "gold_projection_required_interval_count": gold_projection_interval_validation["required_interval_count"],
            "gold_projection_interval_hit_rate": gold_projection_interval_validation["hit_rate"],
            "gold_projection_interval_shadow_pl": gold_projection_interval_validation["total_shadow_p_l_effect"],
            "gold_evolving_projection_path_status": gold_evolving_projection_path["status"],
            "gold_evolving_projection_horizon_count": gold_evolving_projection_path["horizon_count"],
            "gold_evolving_projection_fresh_horizon_count": gold_evolving_projection_path["fresh_horizon_count"],
            "gold_evolving_projection_validated_horizon_count": gold_evolving_projection_path["validated_horizon_count"],
            "gold_evolving_projection_hit_rate": gold_evolving_projection_path["hit_rate"],
            "gold_evolving_projection_live_ready": gold_evolving_projection_path["live_evolving_ready"],
            "gold_evolving_projection_blocker_count": len(gold_evolving_projection_path["blockers"]),
            "gold_evolving_projection_next_action": gold_evolving_projection_path["next_roll_forward_action"],
            "gold_dynamic_market_edge_stream_status": gold_dynamic_market_edge_stream["status"],
            "gold_dynamic_market_edge_state": gold_dynamic_market_edge_stream["edge_state"],
            "gold_dynamic_market_edge_score": gold_dynamic_market_edge_stream["edge_score"],
            "gold_dynamic_market_edge_stream_lane_count": gold_dynamic_market_edge_stream["stream_lane_count"],
            "gold_dynamic_market_edge_fresh_stream_count": gold_dynamic_market_edge_stream["fresh_stream_count"],
            "gold_dynamic_market_edge_context_fresh_count": gold_dynamic_market_edge_stream["context_fresh_count"],
            "gold_dynamic_market_edge_target_fresh": gold_dynamic_market_edge_stream["target_stream_fresh"],
            "gold_dynamic_market_edge_shadow_intent_allowed": (gold_dynamic_market_edge_stream["action_candidate"] or {}).get("shadow_intent_allowed"),
            "gold_dynamic_market_edge_blocker_count": len(gold_dynamic_market_edge_stream["blockers"]),
            "gold_dynamic_market_edge_next_action": gold_dynamic_market_edge_stream["next_action"],
            "gold_hnc_history_future_bridge_status": gold_hnc_history_future_bridge["status"],
            "gold_hnc_history_future_bridge_ready": gold_hnc_history_future_bridge["bridge_ready"],
            "gold_hnc_history_future_memory_score": gold_hnc_history_future_bridge["historical_memory_score"],
            "gold_hnc_history_future_validated_count": gold_hnc_history_future_bridge["validated_history_count"],
            "gold_hnc_history_future_hit_rate": gold_hnc_history_future_bridge["historical_hit_rate"],
            "gold_hnc_history_future_replay_ready_count": gold_hnc_history_future_bridge["ready_replay_lane_count"],
            "gold_hnc_history_future_window_count": len(gold_hnc_history_future_bridge["future_windows"]),
            "gold_hnc_history_future_claim_state": gold_hnc_history_future_bridge["future_claim_state"],
            "gold_hnc_history_future_blocker_count": len(gold_hnc_history_future_bridge["blockers"]),
            "gold_creative_dream_engine_status": gold_creative_dream_hypothesis_engine["status"],
            "gold_creative_dream_count": gold_creative_dream_hypothesis_engine["dream_count"],
            "gold_creative_dream_ready_count": gold_creative_dream_hypothesis_engine["ready_dream_count"],
            "gold_creative_average_score": gold_creative_dream_hypothesis_engine["average_creativity_score"],
            "gold_creative_average_evidence_score": gold_creative_dream_hypothesis_engine["average_evidence_score"],
            "gold_creative_research_packet_count": gold_creative_dream_hypothesis_engine["research_packet_count"],
            "gold_creative_action_influence_allowed": gold_creative_dream_hypothesis_engine["action_influence_allowed"],
            "gold_creative_blocker_count": len(gold_creative_dream_hypothesis_engine["blockers"]),
            "gold_probability_projection_forecast_status": gold_probability_projection_forecast["status"],
            "gold_probability_forecast_truth_claim_allowed": gold_probability_projection_forecast["truth_discipline"]["truth_claim_allowed"],
            "gold_probability_forecast_truth_status": gold_probability_projection_forecast["truth_discipline"]["truth_status"],
            "gold_probability_forecast_direction": gold_probability_projection_forecast["forecast_distribution"]["calibrated_direction"],
            "gold_probability_forecast_calibrated_confidence": gold_probability_projection_forecast["forecast_distribution"]["calibrated_confidence"],
            "gold_probability_forecast_validated_claim_count": gold_probability_projection_forecast["validated_forecast"]["validated_claim_count"],
            "gold_probability_forecast_hit_rate": gold_probability_projection_forecast["validated_forecast"]["hit_rate"],
            "gold_probability_forecast_contradiction_count": len(gold_probability_projection_forecast["contradiction_matrix"]),
            "gold_probability_forecast_blocker_count": len(gold_probability_projection_forecast["blockers"]),
            "gold_probability_forecast_action_influence_allowed": gold_probability_projection_forecast["validated_forecast"]["action_influence_allowed"],
            "gold_hnc_action_coherence_status": gold_hnc_action_coherence_gate["status"],
            "gold_hnc_action_coherence_allowed": gold_hnc_action_coherence_gate["action_coherence_allowed"],
            "gold_portfolio_uplift_status": gold_portfolio_uplift_guard["status"],
            "gold_portfolio_uplift_order_intent_allowed": gold_portfolio_uplift_guard["order_intent_consideration_allowed"],
            "gold_portfolio_uplift_shadow_pl": gold_portfolio_uplift_guard["validated_shadow_p_l_effect"],
            "historical_signal_lane_count": historical_signal_lab["lane_count"],
            "historical_signal_ready_count": historical_signal_lab["ready_lane_count"],
            "historical_signal_status": historical_signal_lab["status"],
            "lead_lag_candidate_count": len(historical_signal_lab["lead_lag_candidates"]),
            "orderbook_signal_state": historical_signal_lab["orderbook_signal_state"],
            "chart_replay_state": historical_signal_lab["chart_replay_state"],
            "gold_priority_workbench_status": gold_priority_workbench["status"],
            "gold_priority_data_queue_count": len(gold_priority_workbench["data_priority_queue"]),
            "gold_priority_artifact_count": 2,
            "three_p_floor_state": three_p_profit_floor_gate["state"],
            "three_p_floor_side": three_p_profit_floor_gate["side"],
            "three_p_floor_suggested_shadow_size": three_p_profit_floor_gate["suggested_shadow_size"],
            "three_p_floor_minimum_move": three_p_profit_floor_gate["minimum_price_move_for_floor_at_min_size"],
            "verified_real_data_gate_status": verified_real_data_gate["status"],
            "verified_real_data_action_allowed": verified_real_data_gate["action_allowed_by_data"],
            "verified_real_data_fresh_source_count": verified_real_data_gate["fresh_required_source_count"],
            "verified_real_data_required_source_count": verified_real_data_gate["required_source_count"],
            "verified_real_data_blocker_count": len(verified_real_data_gate["blockers"]),
            "gold_action_command_status": gold_action_command["status"],
            "gold_action_state": gold_action_command["act"]["state"],
            "gold_action_blocking_count": len(gold_action_command["blocking_items"]),
            "gold_command_system_count": len(gold_action_command["command_systems"]),
            "gold_agent_coding_support_status": gold_agent_coding_support["status"],
            "gold_agent_support_ready": gold_agent_coding_support["support_ready"],
            "gold_agent_chat_lane_count": gold_agent_coding_support["chat_lane_count"],
            "gold_agent_tool_lane_count": gold_agent_coding_support["tool_lane_count"],
            "gold_agent_monitor_target_count": gold_agent_coding_support["monitor_target_count"],
            "gold_agent_support_surface_count": gold_agent_coding_support["surface_count"],
            "gold_agent_support_present_surface_count": gold_agent_coding_support["present_surface_count"],
            "gold_agent_support_artifact_count": gold_agent_coding_support["artifact_count"],
            "gold_agent_support_present_artifact_count": gold_agent_coding_support["present_artifact_count"],
            "gold_agent_support_fresh_artifact_count": gold_agent_coding_support["fresh_artifact_count"],
            "gold_agent_support_blocker_count": len(gold_agent_coding_support["blockers"]),
            "gold_shadow_focus_status": gold_shadow_trading_focus["status"],
            "gold_shadow_focus_candidate_count": gold_shadow_trading_focus["gold_related_shadow_count"],
            "gold_shadow_focus_context_count": gold_shadow_trading_focus["context_shadow_count"],
            "gold_shadow_focus_energy_lane_count": len(gold_shadow_trading_focus["energy_context_lanes"]),
            "gold_shadow_focus_excluded_shadow_count": gold_shadow_trading_focus["excluded_shadow_count"],
            "gold_shadow_focus_promotion_state": gold_shadow_trading_focus["promotion_gate"]["state"],
            "gold_live_stream_command_deck_status": gold_live_stream_command_deck["status"],
            "gold_live_stream_channel_count": len(gold_live_stream_command_deck["stream_channels"]),
            "gold_live_chart_stream_count": len(gold_live_stream_command_deck["chart_streams"]),
            "gold_live_deck_targeting_state": gold_live_stream_command_deck["target"]["targeting_state"],
            "gold_live_deck_now_state": gold_live_stream_command_deck["what_am_i_doing_now"]["state"],
            "gold_live_deck_act_result_state": gold_live_stream_command_deck["act_result"]["state"],
            "capital_gold_leverage_estimate": (gold_live_stream_command_deck["leverage_margin_status"] or {}).get("leverage_estimate"),
            "capital_gold_margin_factor_pct": (gold_live_stream_command_deck["leverage_margin_status"] or {}).get("margin_factor_pct"),
            "capital_gold_margin_required_for_min_deal": (gold_live_stream_command_deck["leverage_margin_status"] or {}).get("margin_required_for_min_deal"),
            "gold_margin_signal_action_loop_status": gold_margin_signal_action_loop["status"],
            "gold_margin_signal_acting_state": gold_margin_signal_action_loop["acting_state"],
            "gold_margin_signal_pipeline_stage_count": gold_margin_signal_action_loop["stage_count"],
            "gold_margin_signal_ready_stage_count": gold_margin_signal_action_loop["ready_stage_count"],
            "gold_margin_signal_shadow_intent_allowed": gold_margin_signal_action_loop["action_authority"]["shadow_margin_intent_allowed"],
            "gold_margin_signal_live_order_allowed": gold_margin_signal_action_loop["action_authority"]["live_order_allowed"],
            "gold_margin_signal_margin_order_allowed": gold_margin_signal_action_loop["action_authority"]["margin_order_allowed"],
            "gold_margin_signal_blocker_count": len(gold_margin_signal_action_loop["blockers"]),
            "gold_process_logic_flow_guard_status": gold_process_logic_flow_guard["status"],
            "gold_process_flow_state": gold_process_logic_flow_guard["flow_state"],
            "gold_process_flow_correct": gold_process_logic_flow_guard["flow_correct"],
            "gold_process_flow_all_gates_ready": gold_process_logic_flow_guard["all_gates_ready"],
            "gold_process_flow_ready_gate_count": gold_process_logic_flow_guard["ready_gate_count"],
            "gold_process_flow_gate_count": gold_process_logic_flow_guard["gate_count"],
            "gold_process_flow_fake_pass_count": gold_process_logic_flow_guard["fake_pass_count"],
            "gold_process_flow_first_blocked_gate": (gold_process_logic_flow_guard["first_blocked_gate"] or {}).get("id"),
            "gold_data_sensemaking_router_status": gold_data_sensemaking_router["status"],
            "gold_data_sensemaking_state": gold_data_sensemaking_router["sensemaking_state"],
            "gold_data_sensemaking_score": gold_data_sensemaking_router["sensemaking_score"],
            "gold_data_source_count": gold_data_sensemaking_router["source_count"],
            "gold_data_present_source_count": gold_data_sensemaking_router["present_source_count"],
            "gold_data_fresh_source_count": gold_data_sensemaking_router["fresh_source_count"],
            "gold_data_routed_source_count": gold_data_sensemaking_router["routed_source_count"],
            "gold_data_destination_count": gold_data_sensemaking_router["destination_count"],
            "gold_data_sensemaking_blocker_count": len(gold_data_sensemaking_router["blockers"]),
            "hnc_auris_quantum_probability_route_status": cognitive_route["status"],
            "hnc_auris_quantum_probability_route_passed": cognitive_route["route_passed"],
            "auris_node_count": (cognitive_route["auris_nodes"] or {}).get("node_count"),
            "auris_coherence": (cognitive_route["auris_nodes"] or {}).get("coherence"),
            "lambda_history_fresh": (cognitive_route["lambda_system"] or {}).get("fresh"),
            "latest_lambda": (cognitive_route["lambda_system"] or {}).get("latest_lambda"),
            "quantum_route_surface_count": (cognitive_route["quantum_systems"] or {}).get("surface_count"),
            "quantum_route_present_surface_count": (cognitive_route["quantum_systems"] or {}).get("present_surface_count"),
            "probability_route_surface_count": (cognitive_route["probability_systems"] or {}).get("surface_count"),
            "probability_route_present_surface_count": (cognitive_route["probability_systems"] or {}).get("present_surface_count"),
            "gold_probability_row_count": (cognitive_route["probability_systems"] or {}).get("gold_row_count"),
            "cognitive_route_blocker_count": len(cognitive_route["blockers"]),
            "hft_speed_prediction_gate_status": hft_speed_prediction_gate["status"],
            "hft_speed_prediction_gate_passed": hft_speed_prediction_gate["gate_passed"],
            "hft_speed_score": hft_speed_prediction_gate["speed_score"],
            "hft_latency_budget_ms": hft_speed_prediction_gate["latency_budget_ms"],
            "hft_source_freshness_budget_ms": hft_speed_prediction_gate["source_freshness_budget_ms"],
            "hft_fresh_gold_prediction_count": hft_speed_prediction_gate["prediction_validation"]["fresh_gold_prediction_count"],
            "hft_validated_gold_prediction_count": hft_speed_prediction_gate["prediction_validation"]["validated_gold_prediction_count"],
            "hft_validated_correct_gold_prediction_count": hft_speed_prediction_gate["prediction_validation"]["validated_correct_gold_prediction_count"],
            "hft_prediction_blocker_count": len(hft_speed_prediction_gate["blockers"]),
            "gold_historical_stress_status": gold_historical_stress_test["status"],
            "gold_historical_stress_passed": gold_historical_stress_test["stress_passed"],
            "gold_historical_stress_prediction_count": gold_historical_stress_test["prediction_validation"]["row_count"],
            "gold_historical_stress_validated_count": gold_historical_stress_test["prediction_validation"]["validated_count"],
            "gold_historical_stress_hit_rate": gold_historical_stress_test["prediction_validation"]["hit_rate"],
            "gold_historical_stress_surface_count": gold_historical_stress_test["surface_count"],
            "gold_historical_stress_present_surface_count": gold_historical_stress_test["present_surface_count"],
            "gold_historical_stress_blocker_count": len(gold_historical_stress_test["blockers"]),
            "gold_swarm_agent_count": swarm_intelligence["agent_count"],
            "gold_swarm_active_agent_count": swarm_intelligence["active_agent_count"],
            "gold_swarm_attention_agent_count": swarm_intelligence["attention_agent_count"],
            "gold_swarm_compile_state": swarm_intelligence["compile_gate"]["state"],
            "local_research_packet_count": len([item for item in local_research_packets if item.get("matched_terms")]),
            "market_universe_bucket_counts": market_universe["bucket_counts"],
            "role_count": len(GOLD_COMPANY_ROLES),
        },
        "output_files": [
            DEFAULT_STATE_PATH.as_posix(),
            DEFAULT_AUDIT_JSON.as_posix(),
            DEFAULT_AUDIT_MD.as_posix(),
            DEFAULT_PUBLIC_JSON.as_posix(),
            GOLD_FORECAST_SVG.as_posix(),
            GOLD_FORECAST_HTML.as_posix(),
        ],
    }
    return report


def build_and_write_gold_capital_intelligence_company(
    *,
    root: Optional[Path] = None,
    target_symbol: str = "GOLD",
) -> Dict[str, Any]:
    root = Path(root or _default_root()).resolve()
    report = build_gold_capital_intelligence_company(root=root, target_symbol=target_symbol)
    artifact_writes = _write_gold_forecast_artifacts(root, report)
    writes = [
        _write_json(_rooted(root, DEFAULT_STATE_PATH), report),
        _write_json(_rooted(root, DEFAULT_AUDIT_JSON), report),
        _write_text(_rooted(root, DEFAULT_AUDIT_MD), _make_markdown(report)),
        _write_json(_rooted(root, DEFAULT_PUBLIC_JSON), report),
    ]
    report["write_info"] = {"evidence_writes": writes, "artifact_writes": artifact_writes}
    for rel in (DEFAULT_STATE_PATH, DEFAULT_AUDIT_JSON, DEFAULT_PUBLIC_JSON):
        _write_json(_rooted(root, rel), report)
    _write_text(_rooted(root, DEFAULT_AUDIT_MD), _make_markdown(report))
    return report


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Build Aureon's Capital GOLD intelligence company packet.")
    parser.add_argument("--repo-root", default="", help="Repository root; defaults to cwd/repo.")
    parser.add_argument("--symbol", default="GOLD", help="Capital.com symbol/epic focus.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Markdown.")
    args = parser.parse_args(argv)
    root = Path(args.repo_root).resolve() if args.repo_root else None
    report = build_and_write_gold_capital_intelligence_company(root=root, target_symbol=args.symbol)
    print(json.dumps(report, indent=2, sort_keys=True, default=str) if args.json else _make_markdown(report))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
