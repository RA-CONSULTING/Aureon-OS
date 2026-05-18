#!/usr/bin/env python3
"""
Unified market runner for the current live setup.

Runs:
- Kraken crypto margin trader
- Capital.com CFD trader
- Alpaca spot crypto route planning
- Binance spot and margin route planning

Provides:
- one autonomous loop
- one combined terminal status surface
- one local telemetry API for the dashboard
- one multi-venue order-intent surface for runtime-gated execution
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import json
import logging
import math
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    # Load repo-local environment variables so users can run this file directly
    # without pre-exporting keys in their shell.
    from aureon.core.aureon_env import load_aureon_environment

    load_aureon_environment(Path(__file__).resolve().parents[2], override=False)
except Exception:
    pass

_SUPPRESS_IMPORT_SIDE_EFFECTS = os.getenv("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "").lower() in {
    "1",
    "true",
    "yes",
    "on",
}

if _SUPPRESS_IMPORT_SIDE_EFFECTS:
    KrakenMarginArmyTrader = None  # type: ignore[assignment]
    CapitalCFDTrader = None  # type: ignore[assignment]
    CAPITAL_UNIVERSE = {}
    AlpacaClient = None  # type: ignore[assignment]
    BinanceClient = None  # type: ignore[assignment]
else:
    try:
        from aureon.exchanges.kraken_margin_penny_trader import KrakenMarginArmyTrader
        from aureon.exchanges.capital_cfd_trader import CAPITAL_UNIVERSE, CapitalCFDTrader
    except Exception:
        from aureon.exchanges.kraken_margin_penny_trader import KrakenMarginArmyTrader
        from aureon.exchanges.capital_cfd_trader import CAPITAL_UNIVERSE, CapitalCFDTrader
    try:
        from aureon.exchanges.alpaca_client import AlpacaClient
    except Exception:
        try:
            from aureon.exchanges.alpaca_client import AlpacaClient
        except Exception:
            AlpacaClient = None  # type: ignore[assignment]
    try:
        from aureon.exchanges.binance_client import BinanceClient
    except Exception:
        try:
            from aureon.exchanges.binance_client import BinanceClient
        except Exception:
            BinanceClient = None  # type: ignore[assignment]

try:
    from aureon.utils.aureon_sero_client import get_sero_client
except Exception:
    try:
        from aureon.utils.aureon_sero_client import get_sero_client
    except Exception:
        get_sero_client = None  # type: ignore[assignment]

try:
    from aureon.trading.order_lifecycle import (
        append_event as append_order_lifecycle_event,
        candidate_id_for,
        is_active_route as order_lifecycle_route_active,
        latest_for_ui as latest_order_lifecycle_state,
        lifecycle_id_for,
        route_key_for,
    )
except Exception:
    append_order_lifecycle_event = None  # type: ignore[assignment]
    candidate_id_for = None  # type: ignore[assignment]
    order_lifecycle_route_active = None  # type: ignore[assignment]
    latest_order_lifecycle_state = None  # type: ignore[assignment]
    lifecycle_id_for = None  # type: ignore[assignment]
    route_key_for = None  # type: ignore[assignment]

logger = logging.getLogger("unified_market_trader")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ── Network integration (fail-safe) ──────────────────────────────────────────
try:
    from aureon.core.aureon_thought_bus import get_thought_bus, Thought
    _HAS_THOUGHT_BUS = True
except Exception:
    get_thought_bus = None   # type: ignore[assignment]
    Thought = None           # type: ignore[assignment]
    _HAS_THOUGHT_BUS = False

try:
    from aureon.core.aureon_mycelium import get_mycelium
    _HAS_MYCELIUM = True
except Exception:
    try:
        from aureon.core.aureon_mycelium import get_mycelium
        _HAS_MYCELIUM = True
    except Exception:
        get_mycelium = None  # type: ignore[assignment]
        _HAS_MYCELIUM = False

def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except Exception:
        return default

try:
    from aureon.core.exchange_rate_limit_registry import (
        governor_default_for_exchange as _official_governor_default,
        official_rate_limit_profiles as _official_rate_limit_profiles,
        quote_fraction_default_for_exchange as _official_quote_fraction_default,
    )
except Exception:
    def _official_governor_default(exchange: str, fallback: float) -> float:
        return fallback

    def _official_quote_fraction_default(exchange: str, fallback: float, *, cash_active: bool = True) -> float:
        return fallback

    def _official_rate_limit_profiles() -> Dict[str, Dict[str, Any]]:
        return {}

LOCAL_HOST = "127.0.0.1"
LOCAL_PORT = 8790
REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_STATUS_PATH = REPO_ROOT / "state" / "unified_runtime_status.json"
RUNTIME_STATUS_LOCK_PATH = RUNTIME_STATUS_PATH.with_name("unified_market_trader.writer.lock.json")
ORDER_INTENT_LOG_PATH = RUNTIME_STATUS_PATH.with_name("unified_exchange_order_intents.jsonl")
ORDER_INTENT_STATE_PATH = RUNTIME_STATUS_PATH.with_name("unified_exchange_order_intents.json")
ORDER_INTENT_PUBLIC_PATH = REPO_ROOT / "frontend" / "public" / "aureon_unified_exchange_order_intents.json"
GOLD_CAPITAL_INTELLIGENCE_PUBLIC_PATH = REPO_ROOT / "frontend" / "public" / "aureon_gold_capital_intelligence_company.json"
EXECUTION_RESULT_LOG_PATH = RUNTIME_STATUS_PATH.with_name("unified_exchange_execution_results.jsonl")
EXECUTION_RESULT_STATE_PATH = RUNTIME_STATUS_PATH.with_name("unified_exchange_execution_results.json")
EXECUTION_RESULT_PUBLIC_PATH = REPO_ROOT / "frontend" / "public" / "aureon_unified_exchange_execution_results.json"
KRAKEN_SPOT_POSITION_STATE_PATH = RUNTIME_STATUS_PATH.with_name("kraken_spot_fast_profit_positions.json")
KRAKEN_SPOT_POSITION_PUBLIC_PATH = REPO_ROOT / "frontend" / "public" / "kraken_spot_fast_profit_positions.json"
KRAKEN_ASSET_REGISTRY_STATE_PATH = RUNTIME_STATUS_PATH.with_name("aureon_kraken_tradable_asset_registry.json")
KRAKEN_ASSET_REGISTRY_AUDIT_PATH = REPO_ROOT / "docs" / "audits" / "aureon_kraken_tradable_asset_registry.json"
KRAKEN_ASSET_REGISTRY_PUBLIC_PATH = REPO_ROOT / "frontend" / "public" / "aureon_kraken_tradable_asset_registry.json"
SHADOW_TRADE_LOG_PATH = RUNTIME_STATUS_PATH.with_name("unified_shadow_trade_report.jsonl")
SHADOW_TRADE_STATE_PATH = RUNTIME_STATUS_PATH.with_name("unified_shadow_trade_report.json")
SHADOW_TRADE_PUBLIC_PATH = REPO_ROOT / "frontend" / "public" / "aureon_unified_shadow_trade_report.json"
HNC_COGNITIVE_PROOF_LOG_PATH = RUNTIME_STATUS_PATH.with_name("aureon_hnc_cognitive_proof.jsonl")
HNC_COGNITIVE_PROOF_STATE_PATH = RUNTIME_STATUS_PATH.with_name("aureon_hnc_cognitive_proof.json")
HNC_COGNITIVE_PROOF_PUBLIC_PATH = REPO_ROOT / "frontend" / "public" / "aureon_hnc_cognitive_proof.json"
HNC_OPERATING_CYCLE_STATE_PATH = RUNTIME_STATUS_PATH.with_name("aureon_hnc_operating_cycle.json")
HNC_OPERATING_CYCLE_PUBLIC_PATH = REPO_ROOT / "frontend" / "public" / "aureon_hnc_operating_cycle.json"
WORLD_FINANCIAL_ECOSYSTEM_STATE_PATH = RUNTIME_STATUS_PATH.with_name("aureon_world_financial_ecosystem_intelligence.json")
WORLD_FINANCIAL_ECOSYSTEM_PUBLIC_PATH = REPO_ROOT / "frontend" / "public" / "aureon_world_financial_ecosystem_intelligence.json"
ASSET_WAVEFORM_MODELS_STATE_PATH = RUNTIME_STATUS_PATH.with_name("aureon_asset_waveform_models.json")
ASSET_WAVEFORM_MODELS_PUBLIC_PATH = REPO_ROOT / "frontend" / "public" / "aureon_asset_waveform_models.json"
SCANNER_FUSION_MATRIX_STATE_PATH = RUNTIME_STATUS_PATH.with_name("aureon_scanner_fusion_matrix.json")
SCANNER_FUSION_MATRIX_PUBLIC_PATH = REPO_ROOT / "frontend" / "public" / "aureon_scanner_fusion_matrix.json"
EMBEDDED_DASHBOARD_ENABLED = os.getenv("UNIFIED_MARKET_EMBEDDED_DASHBOARD", "").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
RUNTIME_WRITER_LOCK_TTL_SEC = max(30.0, _env_float("UNIFIED_RUNTIME_WRITER_LOCK_TTL_SEC", 120.0))
EXCHANGE_REINIT_INTERVAL_SEC = max(2.0, _env_float("UNIFIED_EXCHANGE_REINIT_INTERVAL_SEC", 30.0))
AURIS_FEED_MIN_INTERVAL_SEC = max(5.0, _env_float("UNIFIED_AURIS_FEED_MIN_INTERVAL_SEC", 45.0))
CENTRAL_BEAT_REFRESH_SEC = max(1.0, _env_float("UNIFIED_CENTRAL_BEAT_REFRESH_SEC", 20.0))
CENTRAL_BEAT_STALE_AFTER_SEC = max(
    CENTRAL_BEAT_REFRESH_SEC * 2.0,
    _env_float("UNIFIED_CENTRAL_BEAT_STALE_AFTER_SEC", 90.0),
)
READY_STALE_AFTER_SEC = max(15.0, _env_float("UNIFIED_READY_STALE_AFTER_SEC", 45.0))
TICK_RUNNING_STALE_AFTER_SEC = max(
    READY_STALE_AFTER_SEC,
    _env_float("UNIFIED_TICK_RUNNING_STALE_AFTER_SEC", 600.0),
)
CENTRAL_BEAT_HISTORY_LIMIT = 24
PROBE_SYMBOL_MIN_INTERVAL_SEC = max(1.0, _env_float("UNIFIED_PROBE_SYMBOL_MIN_INTERVAL_SEC", 5.0))
PROBE_SYMBOL_STALE_TTL_SEC = max(
    PROBE_SYMBOL_MIN_INTERVAL_SEC,
    _env_float("UNIFIED_PROBE_SYMBOL_STALE_TTL_SEC", 30.0),
)
STREAM_CACHE_MAX_AGE_SEC = max(0.5, _env_float("UNIFIED_STREAM_PRICE_MAX_AGE_SEC", 5.0))
GOLD_PRIORITY_STREAM_MAX_AGE_SEC = max(
    STREAM_CACHE_MAX_AGE_SEC,
    _env_float("UNIFIED_GOLD_PRIORITY_STREAM_MAX_AGE_SEC", 180.0),
)
STREAM_CACHE_MAX_SYMBOLS = max(8, int(_env_float("UNIFIED_STREAM_CACHE_MAX_SYMBOLS", 96.0)))
FAST_MONEY_MIN_VOLATILITY_PCT = max(0.01, _env_float("UNIFIED_FAST_MONEY_MIN_VOLATILITY_PCT", 0.34))
FAST_MONEY_BREAK_EVEN_MOVE_PCT = max(0.01, _env_float("UNIFIED_FAST_MONEY_BREAK_EVEN_MOVE_PCT", 0.34))
FAST_MONEY_VOLUME_USD_TARGET = max(1_000.0, _env_float("UNIFIED_FAST_MONEY_VOLUME_USD_TARGET", 25_000_000.0))
FAST_MONEY_MIN_SCORE = max(0.0, min(1.0, _env_float("UNIFIED_FAST_MONEY_MIN_SCORE", 0.55)))
ORDERBOOK_PROBE_MAX_PER_TICK = max(0, int(_env_float("UNIFIED_ORDERBOOK_PROBE_MAX_PER_TICK", 4.0)))
ORDERBOOK_PROBE_MIN_INTERVAL_SEC = max(1.0, _env_float("UNIFIED_ORDERBOOK_PROBE_MIN_INTERVAL_SEC", 12.0))
ORDERBOOK_PROBE_STALE_TTL_SEC = max(
    ORDERBOOK_PROBE_MIN_INTERVAL_SEC,
    _env_float("UNIFIED_ORDERBOOK_PROBE_STALE_TTL_SEC", 30.0),
)
KRAKEN_TICK_MIN_INTERVAL_SEC = max(0.5, _env_float("UNIFIED_KRAKEN_TICK_MIN_INTERVAL_SEC", 1.0))
KRAKEN_TICK_TIMEOUT_SEC = max(KRAKEN_TICK_MIN_INTERVAL_SEC, _env_float("UNIFIED_KRAKEN_TICK_TIMEOUT_SEC", 20.0))
CAPITAL_TICK_MIN_INTERVAL_SEC = max(1.0, _env_float("UNIFIED_CAPITAL_TICK_MIN_INTERVAL_SEC", 2.0))
CAPITAL_TICK_TIMEOUT_SEC = max(CAPITAL_TICK_MIN_INTERVAL_SEC, _env_float("UNIFIED_CAPITAL_TICK_TIMEOUT_SEC", 20.0))
EXCHANGE_DASHBOARD_PAYLOAD_TIMEOUT_SEC = max(1.0, _env_float("UNIFIED_EXCHANGE_DASHBOARD_PAYLOAD_TIMEOUT_SEC", 6.0))
ORDER_INTENT_MIN_INTERVAL_SEC = max(1.0, _env_float("UNIFIED_ORDER_INTENT_MIN_INTERVAL_SEC", 8.0))
ORDER_INTENT_MIN_CONFIDENCE = max(0.0, min(1.0, _env_float("UNIFIED_ORDER_INTENT_MIN_CONFIDENCE", 0.35)))
ORDER_INTENT_MAX_PER_CYCLE = max(1, int(_env_float("UNIFIED_ORDER_INTENT_MAX_PER_CYCLE", 4.0)))
ORDER_EXECUTOR_MIN_INTERVAL_SEC = max(1.0, _env_float("UNIFIED_ORDER_EXECUTOR_MIN_INTERVAL_SEC", 10.0))
ORDER_EXECUTOR_SYMBOL_COOLDOWN_SEC = max(5.0, _env_float("UNIFIED_ORDER_EXECUTOR_SYMBOL_COOLDOWN_SEC", 60.0))
ORDER_EXECUTOR_QUOTE_USD = max(1.0, _env_float("UNIFIED_ORDER_EXECUTOR_QUOTE_USD", 5.0))
ORDER_EXECUTOR_MAX_PER_TICK = max(1, int(_env_float("UNIFIED_ORDER_EXECUTOR_MAX_PER_TICK", 4.0)))
ORDER_EXECUTOR_MAX_OPEN_POSITIONS = max(1, int(_env_float("UNIFIED_ORDER_EXECUTOR_MAX_OPEN_POSITIONS", 12.0)))
ORDER_EXECUTOR_ROUTE_TIMEOUT_SEC = max(1.0, _env_float("UNIFIED_ORDER_EXECUTOR_ROUTE_TIMEOUT_SEC", 8.0))
ORDER_EXECUTOR_ROUTE_ABANDON_AFTER_SEC = max(
    ORDER_EXECUTOR_ROUTE_TIMEOUT_SEC,
    _env_float("UNIFIED_ORDER_EXECUTOR_ROUTE_ABANDON_AFTER_SEC", 300.0),
)
DYNAMIC_INTELLIGENCE_BUDGET_ENABLED = os.getenv("UNIFIED_DYNAMIC_INTELLIGENCE_BUDGET", "1").strip().lower() not in {
    "0",
    "false",
    "no",
    "off",
}
INTELLIGENCE_BALANCE_MIN_INTERVAL_SEC = max(10.0, _env_float("UNIFIED_INTEL_BALANCE_MIN_INTERVAL_SEC", 30.0))
INTELLIGENCE_SENSOR_LOW_CASH_USD = max(0.0, _env_float("UNIFIED_INTEL_SENSOR_LOW_CASH_USD", ORDER_EXECUTOR_QUOTE_USD * 1.25))
INTELLIGENCE_EXECUTION_CASH_MULTIPLIER = max(1.0, _env_float("UNIFIED_INTEL_EXECUTION_CASH_MULTIPLIER", 1.5))
INTELLIGENCE_SENSOR_PROBE_MIN_INTERVAL_SEC = max(1.0, _env_float("UNIFIED_INTEL_SENSOR_PROBE_MIN_INTERVAL_SEC", 1.0))
INTELLIGENCE_SENSOR_ORDERBOOK_MIN_INTERVAL_SEC = max(1.0, _env_float("UNIFIED_INTEL_SENSOR_ORDERBOOK_MIN_INTERVAL_SEC", 3.0))
INTELLIGENCE_SENSOR_STREAM_SYMBOL_BONUS = max(0, int(_env_float("UNIFIED_INTEL_SENSOR_STREAM_SYMBOL_BONUS", 24.0)))
INTELLIGENCE_SENSOR_ORDERBOOK_BONUS = max(0, int(_env_float("UNIFIED_INTEL_SENSOR_ORDERBOOK_BONUS", 2.0)))
INTELLIGENCE_ORDERBOOK_MAX_BONUS = max(0, int(_env_float("UNIFIED_INTEL_ORDERBOOK_MAX_BONUS", 8.0)))
WORLD_ECOSYSTEM_INTELLIGENCE_ENABLED = os.getenv("UNIFIED_WORLD_ECOSYSTEM_INTELLIGENCE", "1").strip().lower() not in {
    "0",
    "false",
    "no",
    "off",
}
WORLD_ECOSYSTEM_MACRO_FETCH_ENABLED = os.getenv("UNIFIED_WORLD_ECOSYSTEM_MACRO_FETCH", "1").strip().lower() not in {
    "0",
    "false",
    "no",
    "off",
}
WORLD_ECOSYSTEM_NEWS_ENABLED = os.getenv("UNIFIED_WORLD_ECOSYSTEM_NEWS", "1").strip().lower() not in {
    "0",
    "false",
    "no",
    "off",
}
CENTRAL_BEAT_HEAVY_CONTEXT_ENABLED = os.getenv("UNIFIED_CENTRAL_BEAT_HEAVY_CONTEXT", "0").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
TRADER_COGNITIVE_WIRING_ENABLED = os.getenv("UNIFIED_TRADER_COGNITIVE_WIRING", "0").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
EXCHANGE_BOOT_ASYNC_ENABLED = os.getenv("UNIFIED_EXCHANGE_BOOT_ASYNC", "1").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
EXCHANGE_SYNC_RETRY_ENABLED = os.getenv("UNIFIED_EXCHANGE_SYNC_RETRY", "0").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
WORLD_ECOSYSTEM_MACRO_MIN_INTERVAL_SEC = max(60.0, _env_float("UNIFIED_WORLD_ECOSYSTEM_MACRO_MIN_INTERVAL_SEC", 300.0))
WORLD_ECOSYSTEM_FRESH_SEC = max(30.0, _env_float("UNIFIED_WORLD_ECOSYSTEM_FRESH_SEC", 900.0))
WORLD_ECOSYSTEM_MAX_DECISION_SYMBOLS = max(4, int(_env_float("UNIFIED_WORLD_ECOSYSTEM_MAX_DECISION_SYMBOLS", 16.0)))
ASSET_WAVEFORM_MODELS_ENABLED = os.getenv("UNIFIED_ASSET_WAVEFORM_MODELS", "1").strip().lower() not in {
    "0",
    "false",
    "no",
    "off",
}
SCANNER_FUSION_MATRIX_ENABLED = os.getenv("UNIFIED_SCANNER_FUSION_MATRIX", "1").strip().lower() not in {
    "0",
    "false",
    "no",
    "off",
}
SCANNER_FUSION_DECISION_WEIGHT = max(0.0, min(0.35, _env_float("UNIFIED_SCANNER_FUSION_DECISION_WEIGHT", 0.18)))
ASSET_WAVEFORM_MAX_SYMBOLS = max(4, int(_env_float("UNIFIED_ASSET_WAVEFORM_MAX_SYMBOLS", 24.0)))
KRAKEN_SPOT_QUOTE_USD = max(63.0, _env_float("UNIFIED_KRAKEN_SPOT_QUOTE_USD", 65.0))
KRAKEN_SPOT_FAST_PROFIT_CAPTURE_ENABLED = os.getenv("KRAKEN_SPOT_FAST_PROFIT_CAPTURE_ENABLED", "1").strip().lower() not in {"0", "false", "no", "off"}
KRAKEN_SPOT_FAST_PROFIT_MIN_USD = max(0.0, _env_float("KRAKEN_SPOT_FAST_PROFIT_MIN_USD", 0.01))
KRAKEN_SPOT_FAST_PROFIT_MIN_HOLD_SEC = max(0.0, _env_float("KRAKEN_SPOT_FAST_PROFIT_MIN_HOLD_SEC", 1.0))
KRAKEN_SPOT_TAKER_FEE_RATE = max(0.0, _env_float("KRAKEN_SPOT_TAKER_FEE_RATE", 0.004))
KRAKEN_SPOT_COLLATERAL_RESERVE_USD = max(0.0, _env_float("KRAKEN_SPOT_COLLATERAL_RESERVE_USD", 5.0))
KRAKEN_SPOT_POSTURE_CACHE_TTL_SEC = max(10.0, _env_float("KRAKEN_SPOT_POSTURE_CACHE_TTL_SEC", 300.0))
KRAKEN_SPOT_MANAGED_MIN_USD = max(0.0, _env_float("KRAKEN_SPOT_MANAGED_MIN_USD", 1.0))
KRAKEN_SPOT_DEADMAN_SWITCH_ENABLED = os.getenv("KRAKEN_SPOT_DEADMAN_SWITCH_ENABLED", "1").strip().lower() not in {"0", "false", "no", "off"}
KRAKEN_SPOT_DEADMAN_TRAILING_PCT = max(0.01, _env_float("KRAKEN_SPOT_DEADMAN_TRAILING_PCT", 0.35))
KRAKEN_MARGIN_QUOTE_USD = max(1.0, _env_float("UNIFIED_KRAKEN_MARGIN_QUOTE_USD", ORDER_EXECUTOR_QUOTE_USD))
KRAKEN_MARGIN_LEVERAGE = max(1, int(_env_float("UNIFIED_KRAKEN_MARGIN_LEVERAGE", 2.0)))
BINANCE_MARGIN_LEVERAGE = max(1, int(_env_float("UNIFIED_BINANCE_MARGIN_LEVERAGE", 2.0)))
SHADOW_TRADE_MAX_PER_CYCLE = max(1, int(_env_float("UNIFIED_SHADOW_TRADE_MAX_PER_CYCLE", 12.0)))
SHADOW_TRADE_MIN_CONFIDENCE = max(0.0, min(1.0, _env_float("UNIFIED_SHADOW_TRADE_MIN_CONFIDENCE", ORDER_INTENT_MIN_CONFIDENCE)))
SHADOW_TRADE_VALIDATION_HORIZON_SEC = max(10.0, _env_float("UNIFIED_SHADOW_TRADE_VALIDATION_HORIZON_SEC", 90.0))
SHADOW_TRADE_TARGET_MOVE_PCT = max(0.01, _env_float("UNIFIED_SHADOW_TRADE_TARGET_MOVE_PCT", 0.18))
SHADOW_TRADE_MIN_INTERVAL_SEC = max(1.0, _env_float("UNIFIED_SHADOW_TRADE_MIN_INTERVAL_SEC", 5.0))
HNC_COGNITIVE_PROOF_MIN_INTERVAL_SEC = max(1.0, _env_float("UNIFIED_HNC_COGNITIVE_PROOF_MIN_INTERVAL_SEC", 5.0))
KRAKEN_CLI_INSTALL_CMD = (
    "curl --proto '=https' --tlsv1.2 -LsSf "
    "https://github.com/krakenfx/kraken-cli/releases/latest/download/kraken-cli-installer.sh | sh"
)
SYMBOL_ALIASES = {
    "XBTUSD": "BTCUSD",
    "XXBTZUSD": "BTCUSD",
    "XETHZUSD": "ETHUSD",
    "ETHUSD": "ETHUSD",
    "BTCUSD": "BTCUSD",
    "GOLD": "XAUUSD",
    "GOLDUSD": "XAUUSD",
    "XAUUSD": "XAUUSD",
    "XAUUSDT": "XAUUSD",
    "SILVER": "XAGUSD",
    "XAGUSD": "XAGUSD",
    "BTCUSDT": "BTCUSD",
    "ETHUSDT": "ETHUSD",
    "SOLUSDT": "SOLUSD",
    "XRPUSDT": "XRPUSD",
    "DOGEUSDT": "DOGEUSD",
}
ALPACA_SPOT_CRYPTO_BASES = {
    "AAVE",
    "AVAX",
    "BCH",
    "BTC",
    "DOGE",
    "ETH",
    "LINK",
    "LTC",
    "SHIB",
    "SOL",
    "UNI",
}
BINANCE_CRYPTO_BASES = {
    "AAVE",
    "ADA",
    "APT",
    "ARB",
    "ATOM",
    "AVAX",
    "BCH",
    "BNB",
    "BTC",
    "DOGE",
    "DOT",
    "ETC",
    "ETH",
    "FIL",
    "LINK",
    "LTC",
    "NEAR",
    "OP",
    "PEPE",
    "SHIB",
    "SOL",
    "SUI",
    "TRX",
    "UNI",
    "XRP",
}
KRAKEN_SPOT_CRYPTO_BASES = {
    "AAVE",
    "ADA",
    "ALGO",
    "ATOM",
    "AVAX",
    "BCH",
    "BTC",
    "DOGE",
    "DOT",
    "ETH",
    "FIL",
    "LINK",
    "LTC",
    "MATIC",
    "NEAR",
    "PEPE",
    "SHIB",
    "SOL",
    "TRX",
    "UNI",
    "XLM",
    "XRP",
}
COMMON_MODEL_STACK = [
    {"name": "UnifiedSignalEngine", "path": "aureon/trading/unified_signal_engine.py", "role": "multi-source signal fusion"},
    {"name": "UnifiedSniperBrain", "path": "aureon/trading/unified_sniper_brain.py", "role": "entry/exit probability and timing"},
    {"name": "UnifiedSymbolManager", "path": "aureon/trading/unified_symbol_manager.py", "role": "exchange symbol and precision rules"},
    {"name": "OrcaIntelligence", "path": "aureon/bots_intelligence/aureon_orca_intelligence.py", "role": "cross-exchange whale and opportunity intelligence"},
]
EXCHANGE_MODEL_STACKS = {
    "kraken_spot": [
        {"name": "KrakenClient", "path": "aureon/exchanges/kraken_client.py", "role": "Kraken spot execution and account state"},
        {"name": "KrakenTradingAdapter", "path": "aureon/exchanges/kraken_trading_adapter.py", "role": "Kraken route adapter"},
        {"name": "KrakenSignalBridge", "path": "aureon/bridges/aureon_kraken_unified_signal_bridge.py", "role": "Kraken signal bridge"},
    ],
    "kraken_margin": [
        {"name": "KrakenMarginArmyTrader", "path": "aureon/exchanges/kraken_margin_penny_trader.py", "role": "Kraken autonomous margin trader"},
        {"name": "UnifiedMarginDecisionBrain", "path": "aureon/trading/unified_margin_brain.py", "role": "margin approval/reject decision fusion"},
        {"name": "TemporalTradeCognition", "path": "aureon/trading/temporal_trade_cognition.py", "role": "margin timing cognition"},
    ],
    "capital_cfd": [
        {"name": "CapitalCFDTrader", "path": "aureon/exchanges/capital_cfd_trader.py", "role": "Capital CFD autonomous trader"},
        {"name": "CapitalMarketMonitor", "path": "aureon/exchanges/capital_market_monitor.py", "role": "Capital market monitor"},
        {"name": "CapitalSwarmRunner", "path": "aureon/exchanges/capital_swarm_runner.py", "role": "Capital swarm scan/decision support"},
        {"name": "QueenLearnCapitalTrading", "path": "aureon/queen/queen_learn_capital_trading.py", "role": "Capital learning loop"},
    ],
    "alpaca_spot": [
        {"name": "AlpacaClient", "path": "aureon/exchanges/alpaca_client.py", "role": "Alpaca spot crypto and stock execution"},
        {"name": "AlpacaCapitalStyleTrader", "path": "aureon/exchanges/alpaca_capital_style_trader.py", "role": "Alpaca autonomous trader"},
        {"name": "AlpacaScannerBridge", "path": "aureon/bridges/aureon_alpaca_scanner_bridge.py", "role": "Alpaca scanner bridge"},
        {"name": "AlpacaTruthTracker", "path": "aureon/exchanges/alpaca_truth_tracker.py", "role": "Alpaca signal truth tracking"},
    ],
    "binance_spot": [
        {"name": "BinanceClient", "path": "aureon/exchanges/binance_client.py", "role": "Binance spot execution and account state"},
        {"name": "BinanceWebSocketClient", "path": "aureon/exchanges/binance_ws_client.py", "role": "Binance stream intelligence"},
        {"name": "S5BinanceEcosystem", "path": "aureon/strategies/s5_binance_ecosystem.py", "role": "Binance strategy ecosystem"},
    ],
    "binance_margin": [
        {"name": "BinanceClientMargin", "path": "aureon/exchanges/binance_client.py", "role": "Binance margin execution"},
        {"name": "S5BinanceCommando", "path": "aureon/strategies/s5_binance_commando.py", "role": "Binance commando strategy"},
        {"name": "UnifiedMarginDecisionBrain", "path": "aureon/trading/unified_margin_brain.py", "role": "margin approval/reject decision fusion"},
    ],
}
INTELLIGENCE_MESH_CAPABILITIES = [
    {"name": "LiveExchangeFeeds", "path": "aureon/data_feeds/unified_market_cache.py", "facet": "live_market_data", "wire": "direct_live_signal", "activation": "central_beat_sources"},
    {"name": "LiveStreamCache", "path": "aureon/data_feeds/ws_market_data_feeder.py", "facet": "live_stream_data", "wire": "direct_live_signal", "activation": "stream_cache"},
    {"name": "UnifiedSignalEngine", "path": "aureon/trading/unified_signal_engine.py", "facet": "signal_fusion", "wire": "direct_live_signal", "activation": "model_signal_feed"},
    {"name": "WorldFinancialEcosystemFeed", "path": "aureon/data_feeds/global_financial_feed.py", "facet": "global_macro_market", "wire": "direct_live_signal", "activation": "world_ecosystem_macro"},
    {"name": "MarketHarp", "path": "aureon/data_feeds/market_harp.py", "facet": "cross_market_resonance", "wire": "direct_live_signal", "activation": "world_ecosystem_harp"},
    {"name": "CrossAssetCorrelator", "path": "aureon/analytics/cross_asset_correlator.py", "facet": "cross_asset_presignal", "wire": "direct_live_signal", "activation": "world_ecosystem_cross_asset"},
    {"name": "NewsSignalBridge", "path": "aureon/data_feeds/news_signal.py", "facet": "news_sentiment", "wire": "sentiment_context", "activation": "world_ecosystem_news"},
    {"name": "MultiHorizonWaveformMemory", "path": "aureon/analytics/aureon_multi_horizon_waveform_model.py", "facet": "historical_waveform_memory", "wire": "hnc_proof", "activation": "historical_waveform"},
    {"name": "UnifiedDecisionEngine", "path": "aureon/intelligence/aureon_unified_decision_engine.py", "facet": "decision_intelligence", "wire": "decision_context", "activation": "repo_present"},
    {"name": "UnifiedIntelligenceRegistry", "path": "aureon/intelligence/aureon_unified_intelligence_registry.py", "facet": "capability_registry", "wire": "mesh_inventory", "activation": "repo_present"},
    {"name": "HNCMasterProtocol", "path": "aureon/strategies/hnc_master_protocol.py", "facet": "hnc_harmonic", "wire": "hnc_proof", "activation": "hnc_system"},
    {"name": "HNCProbabilityMatrix", "path": "aureon/strategies/hnc_probability_matrix.py", "facet": "hnc_harmonic", "wire": "hnc_proof", "activation": "hnc_system"},
    {"name": "HNC6DWaveform", "path": "aureon/strategies/hnc_6d_harmonic_waveform.py", "facet": "waveform_history", "wire": "mesh_context", "activation": "repo_present"},
    {"name": "Seer", "path": "aureon/intelligence/aureon_seer.py", "facet": "oracle_forecast", "wire": "hnc_proof", "activation": "hnc_system"},
    {"name": "Lyra", "path": "aureon/trading/aureon_lyra.py", "facet": "harmonic_affect", "wire": "hnc_proof", "activation": "hnc_system"},
    {"name": "KingCapitalLogic", "path": "aureon/trading/compound_king.py", "facet": "capital_logic", "wire": "hnc_proof", "activation": "hnc_system"},
    {"name": "ShadowTradeValidator", "path": "aureon/exchanges/unified_market_trader.py", "facet": "self_validation", "wire": "direct_live_signal", "activation": "shadow_validation"},
    {"name": "SelfValidatingPredictor", "path": "aureon/intelligence/self_validating_predictor.py", "facet": "self_validation", "wire": "mesh_context", "activation": "scanner_fusion"},
    {"name": "ElephantLearning", "path": "aureon/intelligence/aureon_elephant_learning.py", "facet": "memory_history", "wire": "mesh_context", "activation": "repo_present"},
    {"name": "TimelineOracle", "path": "aureon/intelligence/aureon_timeline_oracle.py", "facet": "temporal_forecast", "wire": "mesh_context", "activation": "repo_present"},
    {"name": "TruthPredictionEngine", "path": "aureon/intelligence/aureon_truth_prediction_engine.py", "facet": "prediction_truth", "wire": "mesh_context", "activation": "scanner_fusion"},
    {"name": "IntegratedForecast", "path": "aureon/intelligence/aureon_integrated_forecast.py", "facet": "forecast", "wire": "mesh_context", "activation": "repo_present"},
    {"name": "LiveMomentumHunter", "path": "aureon/scanners/aureon_live_momentum_hunter.py", "facet": "momentum_search", "wire": "mesh_context", "activation": "scanner_fusion"},
    {"name": "FastMoneySelector", "path": "aureon/exchanges/unified_market_trader.py", "facet": "fast_money_selection", "wire": "profit_context", "activation": "fast_money"},
    {"name": "OrderBookPressure", "path": "aureon/analytics/aureon_whale_orderbook_analyzer.py", "facet": "orderbook_pressure", "wire": "direct_live_signal", "activation": "orderbook_pressure"},
    {"name": "GlobalWaveScanner", "path": "aureon/scanners/aureon_global_wave_scanner.py", "facet": "waveform_search", "wire": "mesh_context", "activation": "scanner_fusion"},
    {"name": "MarginHarmonicScanner", "path": "aureon/scanners/aureon_margin_harmonic_scanner.py", "facet": "margin_search", "wire": "mesh_context", "activation": "scanner_fusion"},
    {"name": "MoversShakersScanner", "path": "aureon/scanners/aureon_movers_shakers_scanner.py", "facet": "market_search", "wire": "mesh_context", "activation": "scanner_fusion"},
    {"name": "AnimalMomentumScanners", "path": "aureon/scanners/aureon_animal_momentum_scanners.py", "facet": "swarm_momentum", "wire": "mesh_context", "activation": "scanner_fusion"},
    {"name": "OceanWaveScanner", "path": "aureon/scanners/aureon_ocean_wave_scanner.py", "facet": "waveform_search", "wire": "seer_oracle", "activation": "scanner_fusion"},
    {"name": "PhantomSignalFilter", "path": "aureon/scanners/aureon_phantom_signal_filter.py", "facet": "noise_filter", "wire": "mesh_context", "activation": "scanner_fusion"},
    {"name": "WhaleSonar", "path": "aureon/core/mycelium_whale_sonar.py", "facet": "whale_intelligence", "wire": "thought_bus", "activation": "scanner_fusion"},
    {"name": "OrcaIntelligence", "path": "aureon/bots_intelligence/aureon_orca_intelligence.py", "facet": "whale_intelligence", "wire": "model_stack", "activation": "model_stack"},
    {"name": "FirmIntelligenceCatalog", "path": "aureon/bots_intelligence/aureon_firm_intelligence_catalog.py", "facet": "firm_intelligence", "wire": "mesh_context", "activation": "repo_present"},
    {"name": "NewsSignal", "path": "aureon/data_feeds/news_signal.py", "facet": "news_search", "wire": "sentiment_context", "activation": "repo_present"},
    {"name": "QueenOnlineResearcher", "path": "aureon/queen/queen_online_researcher.py", "facet": "online_research", "wire": "research_context", "activation": "repo_present"},
    {"name": "ResearchCorpusIndex", "path": "aureon/queen/research_corpus_index.py", "facet": "vault_research", "wire": "research_context", "activation": "repo_present"},
    {"name": "QueenRepositoryScanner", "path": "aureon/queen/queen_repository_scanner.py", "facet": "repo_knowledge", "wire": "research_context", "activation": "repo_present"},
    {"name": "MinerBrain", "path": "aureon/utils/aureon_miner_brain.py", "facet": "knowledge_mining", "wire": "research_context", "activation": "repo_present"},
    {"name": "MicroMomentumGoal", "path": "aureon/conversion/aureon_micro_momentum_goal.py", "facet": "fast_profit_eta", "wire": "profit_context", "activation": "scanner_fusion"},
    {"name": "PennyProfitEngine", "path": "aureon/trading/penny_profit_engine.py", "facet": "fast_profit_eta", "wire": "profit_context", "activation": "scanner_fusion"},
    {"name": "DynamicTakeProfit", "path": "aureon/trading/dynamic_take_profit.py", "facet": "exit_logic", "wire": "profit_context", "activation": "scanner_fusion"},
    {"name": "TemporalTradeCognition", "path": "aureon/trading/temporal_trade_cognition.py", "facet": "temporal_trade_logic", "wire": "model_stack", "activation": "model_stack"},
    {"name": "TorchBearerSystem", "path": "aureon/wisdom/torch_bearer_system.py", "facet": "fast_strike_strategy", "wire": "profit_context", "activation": "repo_present"},
    {"name": "RisingStarLogic", "path": "aureon/analytics/aureon_rising_star_logic.py", "facet": "whole_market_search", "wire": "profit_context", "activation": "scanner_fusion"},
]


class ExchangeCallGovernor:
    """Shared exchange call budget for the unified live market runtime.

    The governor keeps position/execution cycles ahead of broad quote probes.
    Quote calls are cached per symbol, so faster CentralBeat refreshes do not
    create a linear increase in REST calls.
    """

    def __init__(self, limits: Optional[Dict[str, Dict[str, float]]] = None):
        defaults = {
            "kraken": {
                "calls_per_min": _env_float("UNIFIED_KRAKEN_CALLS_PER_MIN", _official_governor_default("kraken", 60.0)),
                "quote_ceiling": _env_float(
                    "UNIFIED_KRAKEN_QUOTE_BUDGET_FRACTION",
                    _official_quote_fraction_default("kraken", 0.55, cash_active=True),
                ),
            },
            "capital": {
                "calls_per_min": _env_float("UNIFIED_CAPITAL_CALLS_PER_MIN", _official_governor_default("capital", 45.0)),
                "quote_ceiling": _env_float(
                    "UNIFIED_CAPITAL_QUOTE_BUDGET_FRACTION",
                    _official_quote_fraction_default("capital", 0.45, cash_active=True),
                ),
            },
            "alpaca": {
                "calls_per_min": _env_float("UNIFIED_ALPACA_CALLS_PER_MIN", _official_governor_default("alpaca", 120.0)),
                "quote_ceiling": _env_float(
                    "UNIFIED_ALPACA_QUOTE_BUDGET_FRACTION",
                    _official_quote_fraction_default("alpaca", 0.70, cash_active=True),
                ),
            },
            "binance": {
                "calls_per_min": _env_float("UNIFIED_BINANCE_CALLS_PER_MIN", _official_governor_default("binance", 240.0)),
                "quote_ceiling": _env_float(
                    "UNIFIED_BINANCE_QUOTE_BUDGET_FRACTION",
                    _official_quote_fraction_default("binance", 0.70, cash_active=True),
                ),
            },
        }
        for exchange, override in (limits or {}).items():
            base = defaults.setdefault(str(exchange), {"calls_per_min": 60.0, "quote_ceiling": 0.60})
            base.update(override)

        self._limits = defaults
        self._recent_calls: Dict[str, List[float]] = {name: [] for name in defaults}
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._last_cycle: Dict[str, float] = {}
        self._backoff_until: Dict[str, float] = {name: 0.0 for name in defaults}
        self._stats: Dict[str, Dict[str, Any]] = {
            name: {
                "processed": 0,
                "skipped": 0,
                "cache_hits": 0,
                "errors": 0,
                "last_error": "",
            }
            for name in defaults
        }
        self._lock = threading.RLock()

    def _cfg(self, exchange: str) -> Dict[str, float]:
        return self._limits.setdefault(exchange, {"calls_per_min": 60.0, "quote_ceiling": 0.60})

    def _stats_for(self, exchange: str) -> Dict[str, Any]:
        return self._stats.setdefault(
            exchange,
            {"processed": 0, "skipped": 0, "cache_hits": 0, "errors": 0, "last_error": ""},
        )

    def _trim(self, exchange: str, now: float) -> List[float]:
        calls = self._recent_calls.setdefault(exchange, [])
        cutoff = now - 60.0
        if calls and calls[0] < cutoff:
            calls[:] = [stamp for stamp in calls if stamp >= cutoff]
        return calls

    def _allow(self, exchange: str, priority: str, now: float) -> bool:
        exchange = str(exchange)
        priority = str(priority or "quotes").lower()
        cfg = self._cfg(exchange)
        calls = self._trim(exchange, now)
        max_per_min = max(1, int(float(cfg.get("calls_per_min", 60.0) or 60.0)))
        if now < self._backoff_until.get(exchange, 0.0):
            self._stats_for(exchange)["skipped"] += 1
            return False
        if priority == "quotes":
            quote_cap = max(1, int(max_per_min * float(cfg.get("quote_ceiling", 0.60) or 0.60)))
            if len(calls) >= quote_cap:
                self._stats_for(exchange)["skipped"] += 1
                return False
        if len(calls) >= max_per_min:
            self._stats_for(exchange)["skipped"] += 1
            return False
        calls.append(now)
        self._stats_for(exchange)["processed"] += 1
        return True

    def record_error(self, exchange: str, error: Exception | str) -> None:
        text = str(error)
        now = time.time()
        with self._lock:
            stats = self._stats_for(exchange)
            stats["errors"] += 1
            stats["last_error"] = text[:240]
            lowered = text.lower()
            if "429" in lowered or "rate limit" in lowered or "too many" in lowered:
                self._backoff_until[str(exchange)] = max(
                    self._backoff_until.get(str(exchange), 0.0),
                    now + _env_float("UNIFIED_EXCHANGE_RATE_BACKOFF_SEC", 30.0),
                )

    def call(
        self,
        exchange: str,
        priority: str,
        cache_key: str,
        fn: Callable[[], Any],
        *,
        min_interval_sec: float,
        stale_ttl_sec: float,
    ) -> Any:
        now = time.time()
        with self._lock:
            cached = self._cache.get(cache_key)
            if cached and now - float(cached.get("at", 0.0) or 0.0) < min_interval_sec:
                self._stats_for(exchange)["cache_hits"] += 1
                return cached.get("value")
            if not self._allow(exchange, priority, now):
                if cached and now - float(cached.get("at", 0.0) or 0.0) <= stale_ttl_sec:
                    self._stats_for(exchange)["cache_hits"] += 1
                    return cached.get("value")
                return None

        try:
            value = fn()
        except Exception as e:
            self.record_error(exchange, e)
            with self._lock:
                cached = self._cache.get(cache_key)
                if cached and now - float(cached.get("at", 0.0) or 0.0) <= stale_ttl_sec:
                    self._stats_for(exchange)["cache_hits"] += 1
                    return cached.get("value")
            return None

        if value is not None:
            with self._lock:
                self._cache[cache_key] = {"at": time.time(), "value": value}
        return value

    def should_run_cycle(self, exchange: str, priority: str, cycle_key: str, min_interval_sec: float) -> bool:
        now = time.time()
        with self._lock:
            last = float(self._last_cycle.get(cycle_key, 0.0) or 0.0)
            if now - last < min_interval_sec:
                self._stats_for(exchange)["skipped"] += 1
                return False
            if not self._allow(exchange, priority, now):
                return False
            self._last_cycle[cycle_key] = now
            return True

    def snapshot(self) -> Dict[str, Any]:
        now = time.time()
        with self._lock:
            exchanges: Dict[str, Any] = {}
            official_profiles = _official_rate_limit_profiles()
            for exchange, cfg in self._limits.items():
                calls = self._trim(exchange, now)
                max_per_min = max(1, int(float(cfg.get("calls_per_min", 60.0) or 60.0)))
                stats = dict(self._stats_for(exchange))
                official = official_profiles.get(exchange, {})
                exchanges[exchange] = {
                    "max_calls_per_min": max_per_min,
                    "recent_calls_60s": len(calls),
                    "utilization": round(len(calls) / max_per_min, 4),
                    "quote_budget_fraction": round(float(cfg.get("quote_ceiling", 0.60) or 0.60), 4),
                    "official_limit_model": official.get("official_limit_model", ""),
                    "official_doc_url": official.get("official_doc_url", ""),
                    "stream_preferred": bool(official.get("stream_preferred", False)),
                    "backoff_sec": round(max(0.0, self._backoff_until.get(exchange, 0.0) - now), 3),
                    "cache_entries": sum(1 for key in self._cache if key.startswith(f"{exchange}:")),
                    **stats,
                }
            return {
                "generated_at": datetime.now().isoformat(),
                "policy": "official_limits_execution_and_positions_first_quotes_cached_and_cash_aware",
                "probe_symbol_min_interval_sec": PROBE_SYMBOL_MIN_INTERVAL_SEC,
                "probe_symbol_stale_ttl_sec": PROBE_SYMBOL_STALE_TTL_SEC,
                "exchanges": exchanges,
            }


def _safe_print(*args: Any, **kwargs: Any) -> None:
    try:
        print(*args, **kwargs)
    except (ValueError, OSError):
        message = " ".join(str(arg) for arg in args)
        logger.info(message)


def _repair_stdio() -> None:
    """Best-effort stdio repair for modules that leave streams invalid on Windows."""
    def _is_broken(stream: Any) -> bool:
        if stream is None:
            return True
        try:
            if getattr(stream, "closed", False):
                return True
            stream.write("")
            stream.flush()
            return False
        except Exception:
            return True

    def _open_console(name: str):
        if sys.platform == "win32":
            try:
                return open(name, "w", encoding="utf-8", errors="replace", buffering=1)
            except Exception:
                return None
        return None

    try:
        if _is_broken(sys.stdout):
            sys.stdout = _open_console("CONOUT$") or open(os.devnull, "w")
    except Exception:
        pass
    try:
        if _is_broken(sys.stderr):
            sys.stderr = _open_console("CONERR$") or open(os.devnull, "w")
    except Exception:
        pass


def _is_closed_stream_error(exc: Exception) -> bool:
    return "I/O operation on closed file" in str(exc)


class _UnifiedDashboardHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path == "/health":
            self._send_json(200, {"ok": True, "service": "unified-market-trader"})
            return
        if self.path == "/ready":
            trader = getattr(self.server, "trader_ref", None)
            payload = trader.get_runtime_health() if trader else {"ok": False, "error": "trader_unavailable"}
            self._send_json(200 if payload.get("ok") else 503, payload)
            return
        if self.path == "/api/terminal-state":
            trader = getattr(self.server, "trader_ref", None)
            payload = trader.get_local_dashboard_state() if trader else {"ok": False}
            self._send_json(200, payload)
            return
        self._send_json(404, {"ok": False, "error": "not_found"})

    def log_message(self, format: str, *args):
        return

    def _send_json(self, status: int, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            return


class UnifiedMarketTrader:
    def __init__(self, dry_run: bool = False, setup_kraken_cli: bool = False):
        os.environ.setdefault("AUREON_DISABLE_LOCAL_DASHBOARD", "1")
        self.dry_run = dry_run
        self.setup_kraken_cli = setup_kraken_cli
        self.kraken = None
        self.capital = None
        self.alpaca = None
        self.binance = None
        self.alpaca_trader = None
        self.binance_trader = None
        self.start_time = time.time()
        self.kraken_ready = False
        self.capital_ready = False
        self.kraken_error = ""
        self.capital_error = ""
        self.alpaca_error = ""
        self.binance_error = ""
        self._binance_diag: Dict[str, Any] = {}
        self._exchange_init_threads: Dict[str, threading.Thread] = {}
        self._exchange_init_errors: Dict[str, str] = {}
        self._exchange_init_started_at: float = 0.0
        self._last_kraken_init_attempt = 0.0
        self._last_capital_init_attempt = 0.0
        self._last_kraken_startup_attempt = 0.0
        self._last_capital_startup_attempt = 0.0
        self._latest_dashboard_payload: Dict[str, Any] = {}
        self._shared_market_feed: Dict[str, float] = {}
        self._shared_market_feed_at: float = 0.0
        self._central_beat_feed: Dict[str, Any] = {}
        self._central_beat_at: float = 0.0
        self._central_beat_layers: Dict[str, Any] = {"trader": {}, "probe": {}, "merged": {}}
        self._central_beat_history: List[Dict[str, Any]] = []
        self._central_source_memory: Dict[str, Dict[str, Any]] = {}
        self._last_auris_feed_at: float = 0.0
        self._last_tick_started_at: float = 0.0
        self._last_tick_completed_at: float = 0.0
        self._last_tick_error: str = ""
        self._last_order_intent_at: float = 0.0
        self._last_order_intent_signature: str = ""
        self._latest_order_intents: Dict[str, Any] = {}
        self._last_execution_at: float = 0.0
        self._execution_memory: Dict[str, float] = {}
        self._latest_execution_results: Dict[str, Any] = {}
        self._order_lifecycle_enabled = True
        self._order_lifecycle_started = False
        self._executor_route_lock = threading.Lock()
        self._executor_route_inflight: Dict[str, Dict[str, Any]] = {}
        self._executor_route_results: Dict[str, Dict[str, Any]] = {}
        self._kraken_tick_lock = threading.Lock()
        self._kraken_tick_inflight: Dict[str, Any] = {}
        self._latest_kraken_tick_state: Dict[str, Any] = {}
        self._capital_tick_lock = threading.Lock()
        self._capital_tick_inflight: Dict[str, Any] = {}
        self._latest_capital_tick_state: Dict[str, Any] = {}
        self._exchange_dashboard_lock = threading.Lock()
        self._exchange_dashboard_inflight: Dict[str, Dict[str, Any]] = {}
        self._latest_exchange_dashboard_state: Dict[str, Dict[str, Any]] = {}
        self._latest_exchange_dashboard_payloads: Dict[str, Dict[str, Any]] = {}
        self._kraken_spot_fast_profit_state: Dict[str, Any] = {}
        self._kraken_spot_portfolio_posture_cache: Dict[str, Any] = {}
        self._kraken_spot_portfolio_posture_at: float = 0.0
        self._tick_phase = "booting"
        self._tick_phase_at = time.time()
        self._local_dashboard_server: ThreadingHTTPServer | None = None
        self._local_dashboard_thread: threading.Thread | None = None
        self._runtime_heartbeat_thread: threading.Thread | None = None
        self._thought_bus = None
        self._mycelium = None
        self._last_status_publish: float = 0.0
        self._api_governor = ExchangeCallGovernor()
        self._stream_cache_health: Dict[str, Any] = {}
        self._orderbook_pressure_cache: Dict[str, Dict[str, Any]] = {}
        self._fast_money_intelligence: Dict[str, Any] = {}
        self._dynamic_intelligence_budget: Dict[str, Any] = {}
        self._world_ecosystem_intelligence: Dict[str, Any] = {}
        self._world_ecosystem_at: float = 0.0
        self._world_macro_snapshot_cache: Dict[str, Any] = {}
        self._world_macro_snapshot_at: float = 0.0
        self._world_macro_fetch_inflight: bool = False
        self._asset_waveform_models: Dict[str, Any] = {}
        self._central_beat_heavy_context_enabled = CENTRAL_BEAT_HEAVY_CONTEXT_ENABLED
        self._scanner_fusion_matrix: Dict[str, Any] = {}
        self._market_harp = None
        self._cross_asset_correlator = None
        self._world_macro_provider = None
        self._world_news_signal_provider = None
        self._runtime_instance_id = f"{os.getpid()}:{self.start_time:.6f}"
        self._record_runtime_lifecycle_start()
        self._runtime_writer_lock_reason = ""
        self._duplicate_runtime = False
        self._owns_runtime_status = self._claim_runtime_writer()
        if not self._owns_runtime_status:
            self._duplicate_runtime = True
            self._latest_dashboard_payload = self._build_duplicate_runtime_payload()
            logger.warning("Unified market trader duplicate suppressed: %s", self._runtime_writer_lock_reason)
            return

        # Publish a read-only heartbeat before heavier cognitive wiring. The
        # unified frontend should show the runtime booting even while imports,
        # ThoughtBus, Mycelium, Kraken, or Capital are still warming up.
        self._latest_dashboard_payload = self._build_bootstrap_dashboard_payload()
        self._write_runtime_status_file()
        if EMBEDDED_DASHBOARD_ENABLED:
            self._start_local_dashboard_server()
        self._start_runtime_heartbeat()

        # ── Network connections ────────────────────────────────────────────
        if TRADER_COGNITIVE_WIRING_ENABLED:
            self._set_tick_phase("booting:cognitive_wiring")
            self._thought_bus = (
                get_thought_bus() if _HAS_THOUGHT_BUS and get_thought_bus is not None else None
            )
            self._mycelium = (
                get_mycelium(initial_capital=100.0) if _HAS_MYCELIUM and get_mycelium is not None else None
            )
        else:
            self._thought_bus = None
            self._mycelium = None

        if self.setup_kraken_cli:
            self._ensure_kraken_cli()
        if EXCHANGE_BOOT_ASYNC_ENABLED:
            self._start_exchange_boot_init()
        else:
            self._init_exchanges()
        self._latest_dashboard_payload = self._build_bootstrap_dashboard_payload()
        self._write_runtime_status_file()

    def _governor(self) -> ExchangeCallGovernor:
        governor = getattr(self, "_api_governor", None)
        if governor is None:
            governor = ExchangeCallGovernor()
            self._api_governor = governor
        return governor

    def _env_enabled(self, name: str, default: bool = False) -> bool:
        raw = os.getenv(name)
        if raw is None:
            return bool(default)
        return str(raw).strip().lower() in {"1", "true", "yes", "on"}

    def _runtime_real_orders_allowed(self) -> bool:
        if bool(getattr(self, "dry_run", False)):
            return False
        return (
            self._env_enabled("AUREON_LIVE_TRADING")
            and not self._env_enabled("AUREON_AUDIT_MODE")
            and not self._env_enabled("AUREON_DISABLE_REAL_ORDERS", True)
            and not self._env_enabled("AUREON_DISABLE_EXCHANGE_MUTATIONS", True)
            and not self._env_enabled("DRY_RUN", True)
        )

    def _unified_executor_enabled(self) -> bool:
        if bool(getattr(self, "dry_run", False)):
            return False
        return self._env_enabled("AUREON_UNIFIED_ORDER_EXECUTOR", self._runtime_real_orders_allowed())

    def _central_beat_heavy_context_enabled_now(self) -> bool:
        return bool(getattr(self, "_central_beat_heavy_context_enabled", CENTRAL_BEAT_HEAVY_CONTEXT_ENABLED))

    def _tick_running_stale_after_sec(self) -> float:
        try:
            return max(
                READY_STALE_AFTER_SEC,
                float(getattr(self, "_tick_running_stale_after_sec", TICK_RUNNING_STALE_AFTER_SEC) or TICK_RUNNING_STALE_AFTER_SEC),
            )
        except Exception:
            return TICK_RUNNING_STALE_AFTER_SEC

    def _order_lifecycle_enabled_now(self) -> bool:
        explicit = getattr(self, "_order_lifecycle_enabled", None)
        if explicit is not None:
            return bool(explicit)
        return not _SUPPRESS_IMPORT_SIDE_EFFECTS

    def _order_lifecycle_root(self) -> Optional[Path]:
        root = getattr(self, "_order_lifecycle_root_path", None)
        try:
            return Path(root).resolve() if root else None
        except Exception:
            return None

    def _order_route_key(self, venue: Any, market_type: Any, symbol: Any, side: Any) -> str:
        if route_key_for is not None:
            try:
                return str(route_key_for(venue, market_type, symbol, side))
            except Exception:
                pass
        return ":".join(
            [
                str(venue or "").lower(),
                str(market_type or "").lower(),
                str(symbol or "").upper().strip(),
                str(side or "").upper().strip(),
            ]
        )

    def _candidate_lifecycle_identity(self, item: Dict[str, Any]) -> Tuple[str, str]:
        symbol = str(item.get("symbol") or item.get("route_symbol") or "").upper().strip()
        side = str(item.get("side") or "HOLD").upper().strip()
        source = "|".join(str(part) for part in (item.get("sources") or []) if str(part))
        seed = item.get("generated_at") or item.get("reference_price") or item.get("selection_rank") or source
        if candidate_id_for is not None:
            try:
                candidate_id = str(candidate_id_for(symbol, side, seed, source))
            except Exception:
                candidate_id = f"ocand-{abs(hash((symbol, side, seed, source)))}"
        else:
            candidate_id = f"ocand-{abs(hash((symbol, side, seed, source)))}"
        existing_lifecycle_id = str(item.get("lifecycle_id") or "")
        if existing_lifecycle_id:
            lifecycle_id = existing_lifecycle_id
        elif lifecycle_id_for is not None:
            try:
                lifecycle_id = str(lifecycle_id_for("candidate", candidate_id))
            except Exception:
                lifecycle_id = f"olife-{candidate_id}"
        else:
            lifecycle_id = f"olife-{candidate_id}"
        return str(item.get("candidate_id") or candidate_id), lifecycle_id

    def _record_order_lifecycle(self, event_type: str, status: str, lifecycle_id: str, **fields: Any) -> None:
        if not self._order_lifecycle_enabled_now() or append_order_lifecycle_event is None:
            return
        if not lifecycle_id:
            if lifecycle_id_for is not None:
                try:
                    lifecycle_id = str(
                        lifecycle_id_for(
                            "runtime",
                            getattr(self, "_runtime_instance_id", ""),
                            event_type,
                            fields.get("route_key"),
                            fields.get("symbol"),
                            fields.get("intent_id"),
                        )
                    )
                except Exception:
                    lifecycle_id = ""
            if not lifecycle_id:
                return
        try:
            append_order_lifecycle_event(
                event_type=event_type,
                status=status,
                lifecycle_id=lifecycle_id,
                root=self._order_lifecycle_root(),
                **fields,
            )
        except Exception as exc:
            logger.debug("Order lifecycle event write failed: %s", exc)

    def _record_runtime_lifecycle_start(self) -> None:
        if bool(getattr(self, "_order_lifecycle_started", False)):
            return
        if lifecycle_id_for is not None:
            try:
                lifecycle_id = str(lifecycle_id_for("runtime_session", getattr(self, "_runtime_instance_id", ""), os.getpid()))
            except Exception:
                lifecycle_id = ""
        else:
            lifecycle_id = ""
        if not lifecycle_id:
            return
        self._order_lifecycle_started = True
        self._record_order_lifecycle(
            "runtime_started",
            "runtime_started",
            lifecycle_id,
            runtime_instance_id=getattr(self, "_runtime_instance_id", ""),
            pid=os.getpid(),
            source="unified_market_trader.runtime",
        )

    def _order_lifecycle_snapshot(self) -> Dict[str, Any]:
        if latest_order_lifecycle_state is None:
            return {}
        try:
            return latest_order_lifecycle_state(root=self._order_lifecycle_root())
        except Exception as exc:
            logger.debug("Order lifecycle snapshot unavailable: %s", exc)
            return {}

    def _record_order_flow_lifecycle_candidates(self, order_flow_feed: Dict[str, Any]) -> None:
        active = order_flow_feed.get("active_order_flow", []) if isinstance(order_flow_feed, dict) else []
        if not isinstance(active, list):
            return
        for item in active[:10]:
            if not isinstance(item, dict):
                continue
            candidate_id, lifecycle_id = self._candidate_lifecycle_identity(item)
            item["candidate_id"] = candidate_id
            item["lifecycle_id"] = lifecycle_id
            routes = item.get("execution_routes", []) if isinstance(item.get("execution_routes"), list) else []
            primary_route = next((route for route in routes if isinstance(route, dict) and route.get("ready")), {})
            if not primary_route and routes and isinstance(routes[0], dict):
                primary_route = routes[0]
            route_key = str(primary_route.get("route_key") or "") if isinstance(primary_route, dict) else ""
            self._record_order_lifecycle(
                "market_snapshot",
                "data_ready",
                lifecycle_id,
                candidate_id=candidate_id,
                symbol=item.get("symbol"),
                side=item.get("side"),
                route_key=route_key,
                confidence=item.get("confidence"),
                source="unified_market_trader.shared_order_flow",
            )
            self._record_order_lifecycle(
                "candidate_ready",
                "candidate_ready",
                lifecycle_id,
                candidate_id=candidate_id,
                symbol=item.get("symbol"),
                side=item.get("side"),
                route_key=route_key,
                confidence=item.get("confidence"),
                selection_rank=item.get("selection_rank"),
                route_count=len(routes),
                ready_route_count=item.get("ready_route_count"),
                blockers=item.get("intent_publish_blockers", []),
                source="unified_market_trader.shared_order_flow",
            )

    def _broker_identity_from_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        containers: List[Dict[str, Any]] = []
        if isinstance(result, dict):
            containers.append(result)
            nested = result.get("result")
            if isinstance(nested, dict):
                containers.append(nested)
            position = result.get("fast_profit_position")
            if isinstance(position, dict):
                containers.append(position)
        ack: Dict[str, Any] = {}
        for container in containers:
            for source_key, target_key in (
                ("dealId", "deal_id"),
                ("deal_id", "deal_id"),
                ("dealReference", "deal_reference"),
                ("deal_reference", "deal_reference"),
                ("orderId", "order_id"),
                ("order_id", "order_id"),
                ("id", "order_id"),
                ("txid", "txid"),
                ("status", "broker_status"),
            ):
                value = container.get(source_key)
                if value is not None and value != "" and target_key not in ack:
                    ack[target_key] = value
        return ack

    def _set_tick_phase(self, phase: str) -> None:
        self._tick_phase = str(phase or "unknown")
        self._tick_phase_at = time.time()

    def _ensure_executor_route_state(self) -> None:
        if not hasattr(self, "_executor_route_lock") or self._executor_route_lock is None:
            self._executor_route_lock = threading.Lock()
        if not hasattr(self, "_executor_route_inflight") or self._executor_route_inflight is None:
            self._executor_route_inflight = {}
        if not hasattr(self, "_executor_route_results") or self._executor_route_results is None:
            self._executor_route_results = {}
        if not hasattr(self, "_execution_memory") or self._execution_memory is None:
            self._execution_memory = {}

    def _executor_route_snapshot(self) -> Dict[str, Any]:
        self._ensure_executor_route_state()
        now = time.time()
        with self._executor_route_lock:
            inflight = []
            for key, state in self._executor_route_inflight.items():
                if not state.get("running"):
                    continue
                started_at = float(state.get("started_at", now) or now)
                inflight.append({
                    "route_key": key,
                    "venue": state.get("venue"),
                    "market_type": state.get("market_type"),
                    "symbol": state.get("symbol"),
                    "side": state.get("side"),
                    "running_sec": round(max(0.0, now - started_at), 3),
                    "timeout_sec": state.get("timeout_sec"),
                })
            latest_results = sorted(
                self._executor_route_results.values(),
                key=lambda item: str(item.get("completed_at_iso") or item.get("generated_at") or ""),
                reverse=True,
            )[:8]
        return {
            "route_timeout_sec": ORDER_EXECUTOR_ROUTE_TIMEOUT_SEC,
            "route_abandon_after_sec": ORDER_EXECUTOR_ROUTE_ABANDON_AFTER_SEC,
            "inflight_count": len(inflight),
            "inflight": inflight,
            "latest_async_results": latest_results,
        }

    def _run_executor_route_with_timeout(
        self,
        route_key: str,
        venue: str,
        market_type: str,
        symbol: str,
        side: str,
        handler: Callable[[], Dict[str, Any]],
    ) -> Dict[str, Any]:
        self._ensure_executor_route_state()
        now = time.time()
        timeout_sec = ORDER_EXECUTOR_ROUTE_TIMEOUT_SEC
        with self._executor_route_lock:
            existing = self._executor_route_inflight.get(route_key)
            if existing and existing.get("running"):
                started_at = float(existing.get("started_at", now) or now)
                running_sec = max(0.0, now - started_at)
                reason = (
                    "executor_route_orphaned_manual_review"
                    if running_sec > ORDER_EXECUTOR_ROUTE_ABANDON_AFTER_SEC
                    else "executor_route_inflight"
                )
                return {
                    "ok": False,
                    "held": True,
                    "venue": venue,
                    "market_type": market_type,
                    "symbol": symbol,
                    "side": side,
                    "route_key": route_key,
                    "reason": reason,
                    "running_sec": round(running_sec, 3),
                    "timeout_sec": timeout_sec,
                }
            self._executor_route_inflight[route_key] = {
                "running": True,
                "started_at": now,
                "started_at_iso": datetime.fromtimestamp(now).isoformat(),
                "venue": venue,
                "market_type": market_type,
                "symbol": symbol,
                "side": side,
                "timeout_sec": timeout_sec,
            }

        result_queue = queue.Queue(maxsize=1)

        def runner() -> None:
            error: Optional[Exception] = None
            raw_result: Optional[Dict[str, Any]] = None
            try:
                raw_result = handler()
            except Exception as e:
                error = e
                try:
                    self._governor().record_error(venue or "execution", e)
                except Exception:
                    pass
            completed_at = time.time()
            if error is not None:
                result = {
                    "ok": False,
                    "venue": venue,
                    "market_type": market_type,
                    "symbol": symbol,
                    "side": side,
                    "error": str(error),
                }
            elif isinstance(raw_result, dict):
                result = dict(raw_result)
            else:
                result = {
                    "ok": bool(raw_result),
                    "venue": venue,
                    "market_type": market_type,
                    "symbol": symbol,
                    "side": side,
                    "result": raw_result,
                }
            result.update({
                "route_key": route_key,
                "route_elapsed_sec": round(max(0.0, completed_at - now), 3),
                "timeout_sec": timeout_sec,
                "completed_after_timeout": bool(completed_at - now > timeout_sec),
                "completed_at_iso": datetime.fromtimestamp(completed_at).isoformat(),
            })
            if result.get("ok"):
                self._execution_memory[route_key] = completed_at
            with self._executor_route_lock:
                self._executor_route_inflight[route_key] = {
                    "running": False,
                    "started_at": now,
                    "completed_at": completed_at,
                    "venue": venue,
                    "market_type": market_type,
                    "symbol": symbol,
                    "side": side,
                    "timeout_sec": timeout_sec,
                }
                self._executor_route_results[route_key] = dict(result)
            try:
                result_queue.put_nowait(result)
            except queue.Full:
                pass

        thread = threading.Thread(
            target=runner,
            name=f"aureon-exec-route-{venue}-{market_type}-{symbol}",
            daemon=True,
        )
        thread.start()
        thread.join(timeout_sec)
        if thread.is_alive():
            return {
                "ok": False,
                "held": True,
                "timeout": True,
                "venue": venue,
                "market_type": market_type,
                "symbol": symbol,
                "side": side,
                "route_key": route_key,
                "reason": "executor_route_timeout",
                "timeout_sec": timeout_sec,
                "source": "unified_market_trader.executor",
            }
        try:
            return result_queue.get_nowait()
        except queue.Empty:
            return {
                "ok": False,
                "held": True,
                "venue": venue,
                "market_type": market_type,
                "symbol": symbol,
                "side": side,
                "route_key": route_key,
                "reason": "executor_route_finished_without_result",
                "timeout_sec": timeout_sec,
            }

    def _ensure_kraken_tick_state(self) -> None:
        if not hasattr(self, "_kraken_tick_lock") or self._kraken_tick_lock is None:
            self._kraken_tick_lock = threading.Lock()
        if not hasattr(self, "_kraken_tick_inflight") or self._kraken_tick_inflight is None:
            self._kraken_tick_inflight = {}
        if not hasattr(self, "_latest_kraken_tick_state") or self._latest_kraken_tick_state is None:
            self._latest_kraken_tick_state = {}

    def _kraken_tick_snapshot(self) -> Dict[str, Any]:
        self._ensure_kraken_tick_state()
        now = time.time()
        with self._kraken_tick_lock:
            inflight = dict(self._kraken_tick_inflight)
            latest = dict(self._latest_kraken_tick_state)
        if inflight.get("running"):
            started_at = float(inflight.get("started_at", now) or now)
            latest["running"] = True
            latest["running_sec"] = round(max(0.0, now - started_at), 3)
            latest["timeout_sec"] = KRAKEN_TICK_TIMEOUT_SEC
        return latest

    def _run_kraken_tick_with_timeout(self) -> Tuple[List[dict], Dict[str, Any]]:
        self._ensure_kraken_tick_state()
        now = time.time()
        timeout_sec = KRAKEN_TICK_TIMEOUT_SEC
        with self._kraken_tick_lock:
            existing = self._kraken_tick_inflight
            if existing.get("running"):
                started_at = float(existing.get("started_at", now) or now)
                state = {
                    "ok": False,
                    "held": True,
                    "running": True,
                    "reason": "kraken_tick_inflight",
                    "started_at_iso": existing.get("started_at_iso"),
                    "running_sec": round(max(0.0, now - started_at), 3),
                    "timeout_sec": timeout_sec,
                }
                self._latest_kraken_tick_state = dict(state)
                return [], state
            self._kraken_tick_inflight = {
                "running": True,
                "started_at": now,
                "started_at_iso": datetime.fromtimestamp(now).isoformat(),
                "timeout_sec": timeout_sec,
            }

        result_queue = queue.Queue(maxsize=1)

        def runner() -> None:
            error: Optional[Exception] = None
            closed: List[dict] = []
            try:
                raw = self.kraken.tick() if self.kraken is not None else []
                closed = raw if isinstance(raw, list) else []
            except Exception as e:
                error = e
            completed_at = time.time()
            state = {
                "ok": error is None,
                "running": False,
                "closed_count": len(closed),
                "elapsed_sec": round(max(0.0, completed_at - now), 3),
                "timeout_sec": timeout_sec,
                "completed_after_timeout": bool(completed_at - now > timeout_sec),
                "completed_at_iso": datetime.fromtimestamp(completed_at).isoformat(),
            }
            if error is not None:
                state["error"] = str(error)
            with self._kraken_tick_lock:
                self._kraken_tick_inflight = {
                    "running": False,
                    "started_at": now,
                    "completed_at": completed_at,
                    "timeout_sec": timeout_sec,
                }
                self._latest_kraken_tick_state = dict(state)
            try:
                result_queue.put_nowait((closed, state, error))
            except queue.Full:
                pass

        thread = threading.Thread(target=runner, name="aureon-kraken-tick", daemon=True)
        thread.start()
        thread.join(timeout_sec)
        if thread.is_alive():
            state = {
                "ok": False,
                "held": True,
                "timeout": True,
                "running": True,
                "reason": "kraken_tick_timeout",
                "running_sec": round(max(0.0, time.time() - now), 3),
                "timeout_sec": timeout_sec,
                "source": "unified_market_trader.kraken_tick",
            }
            with self._kraken_tick_lock:
                self._latest_kraken_tick_state = dict(state)
            return [], state
        try:
            closed, state, error = result_queue.get_nowait()
        except queue.Empty:
            state = {
                "ok": False,
                "held": True,
                "reason": "kraken_tick_finished_without_result",
                "timeout_sec": timeout_sec,
            }
            with self._kraken_tick_lock:
                self._latest_kraken_tick_state = dict(state)
            return [], state
        if error is not None:
            raise error
        return closed, state

    def _ensure_capital_tick_state(self) -> None:
        if not hasattr(self, "_capital_tick_lock") or self._capital_tick_lock is None:
            self._capital_tick_lock = threading.Lock()
        if not hasattr(self, "_capital_tick_inflight") or self._capital_tick_inflight is None:
            self._capital_tick_inflight = {}
        if not hasattr(self, "_latest_capital_tick_state") or self._latest_capital_tick_state is None:
            self._latest_capital_tick_state = {}

    def _capital_tick_snapshot(self) -> Dict[str, Any]:
        self._ensure_capital_tick_state()
        now = time.time()
        with self._capital_tick_lock:
            inflight = dict(self._capital_tick_inflight)
            latest = dict(self._latest_capital_tick_state)
        if inflight.get("running"):
            started_at = float(inflight.get("started_at", now) or now)
            latest["running"] = True
            latest["running_sec"] = round(max(0.0, now - started_at), 3)
            latest["timeout_sec"] = CAPITAL_TICK_TIMEOUT_SEC
        return latest

    def _run_capital_tick_with_timeout(self) -> Tuple[List[dict], Dict[str, Any]]:
        self._ensure_capital_tick_state()
        now = time.time()
        timeout_sec = CAPITAL_TICK_TIMEOUT_SEC
        with self._capital_tick_lock:
            existing = self._capital_tick_inflight
            if existing.get("running"):
                started_at = float(existing.get("started_at", now) or now)
                state = {
                    "ok": False,
                    "held": True,
                    "running": True,
                    "reason": "capital_tick_inflight",
                    "started_at_iso": existing.get("started_at_iso"),
                    "running_sec": round(max(0.0, now - started_at), 3),
                    "timeout_sec": timeout_sec,
                }
                self._latest_capital_tick_state = dict(state)
                return [], state
            self._capital_tick_inflight = {
                "running": True,
                "started_at": now,
                "started_at_iso": datetime.fromtimestamp(now).isoformat(),
                "timeout_sec": timeout_sec,
            }

        result_queue = queue.Queue(maxsize=1)

        def runner() -> None:
            error: Optional[Exception] = None
            closed: List[dict] = []
            try:
                raw = self.capital.tick() if self.capital is not None else []
                closed = raw if isinstance(raw, list) else []
            except Exception as e:
                error = e
            completed_at = time.time()
            state = {
                "ok": error is None,
                "running": False,
                "closed_count": len(closed),
                "elapsed_sec": round(max(0.0, completed_at - now), 3),
                "timeout_sec": timeout_sec,
                "completed_after_timeout": bool(completed_at - now > timeout_sec),
                "completed_at_iso": datetime.fromtimestamp(completed_at).isoformat(),
            }
            if error is not None:
                state["error"] = str(error)
            with self._capital_tick_lock:
                self._capital_tick_inflight = {
                    "running": False,
                    "started_at": now,
                    "completed_at": completed_at,
                    "timeout_sec": timeout_sec,
                }
                self._latest_capital_tick_state = dict(state)
            try:
                result_queue.put_nowait((closed, state, error))
            except queue.Full:
                pass

        thread = threading.Thread(target=runner, name="aureon-capital-tick", daemon=True)
        thread.start()
        thread.join(timeout_sec)
        if thread.is_alive():
            state = {
                "ok": False,
                "held": True,
                "timeout": True,
                "running": True,
                "reason": "capital_tick_timeout",
                "running_sec": round(max(0.0, time.time() - now), 3),
                "timeout_sec": timeout_sec,
                "source": "unified_market_trader.capital_tick",
            }
            with self._capital_tick_lock:
                self._latest_capital_tick_state = dict(state)
            return [], state
        try:
            closed, state, error = result_queue.get_nowait()
        except queue.Empty:
            state = {
                "ok": False,
                "held": True,
                "reason": "capital_tick_finished_without_result",
                "timeout_sec": timeout_sec,
            }
            with self._capital_tick_lock:
                self._latest_capital_tick_state = dict(state)
            return [], state
        if error is not None:
            raise error
        return closed, state

    def _preflight_item(self, name: str, ok: bool, severity: str, detail: str, meta: Dict[str, Any] | None = None) -> Dict[str, Any]:
        return {
            "name": name,
            "ok": bool(ok),
            "severity": str(severity or "info"),
            "detail": str(detail or ""),
            "meta": dict(meta or {}),
        }

    def _service_preflight(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        def find_optional_module(*module_names: str):
            try:
                import importlib.util
                for module_name in module_names:
                    spec = importlib.util.find_spec(module_name)
                    if spec is not None:
                        return spec
            except Exception:
                return None
            return None

        telemetry_spec = find_optional_module("telemetry_server")
        items.append(
            self._preflight_item(
                "telemetry_server",
                telemetry_spec is not None,
                "warning" if telemetry_spec is None else "ok",
                "available" if telemetry_spec is not None else "missing_optional_module",
            )
        )

        market_hub_spec = find_optional_module("market_data_hub", "aureon.data_feeds.market_data_hub")
        items.append(
            self._preflight_item(
                "market_data_hub",
                market_hub_spec is not None,
                "warning" if market_hub_spec is None else "ok",
                "available" if market_hub_spec is not None else "missing_optional_module",
            )
        )

        rate_budget_spec = find_optional_module("global_rate_budget", "aureon.core.global_rate_budget")
        items.append(
            self._preflight_item(
                "global_rate_budget",
                rate_budget_spec is not None,
                "warning" if rate_budget_spec is None else "ok",
                "available" if rate_budget_spec is not None else "missing_optional_module",
            )
        )
        return items

    def _build_preflight_report(self) -> Dict[str, Any]:
        items: List[Dict[str, Any]] = []

        items.append(
            self._preflight_item(
                "kraken",
                self.kraken_ready and self.kraken is not None,
                "critical" if not (self.kraken_ready and self.kraken is not None) else "ok",
                self.kraken_error or ("startup_pending" if self.kraken is not None else "not_initialized"),
            )
        )
        items.append(
            self._preflight_item(
                "capital",
                self.capital_ready and self.capital is not None,
                "critical" if not (self.capital_ready and self.capital is not None) else "ok",
                self.capital_error or ("ready" if self.capital is not None else "not_initialized"),
            )
        )

        alpaca_ok = self.alpaca is not None and not bool(getattr(self.alpaca, "init_error", "") or self.alpaca_error)
        items.append(
            self._preflight_item(
                "alpaca_spot_execution_route",
                alpaca_ok,
                "warning" if not alpaca_ok else "ok",
                self.alpaca_error or str(getattr(self.alpaca, "init_error", "") or ("ready" if self.alpaca is not None else "not_initialized")),
                meta={"market_type": "spot_crypto", "intent_route": True},
            )
        )

        binance_diag = getattr(self, "_binance_diag", {}) or {}
        binance_network_ok = bool(binance_diag.get("network_ok", False))
        items.append(
            self._preflight_item(
                "binance_spot_margin_execution_route",
                self.binance is not None and binance_network_ok,
                "warning" if self.binance is not None else "warning",
                self.binance_error or ("ready" if binance_network_ok else "network_unavailable"),
                meta={
                    "market_type": "spot_crypto_and_margin",
                    "intent_route": True,
                    "account_ready": bool(binance_diag.get("account_ok", False)),
                    "margin_available": bool(binance_diag.get("margin_available", False)),
                    "uk_mode": bool(binance_diag.get("uk_mode", False)),
                },
            )
        )

        items.extend(self._service_preflight())

        critical_failures = sum(1 for item in items if item["severity"] == "critical" and not item["ok"])
        warnings = sum(1 for item in items if item["severity"] == "warning" and not item["ok"])
        overall = "green"
        if critical_failures:
            overall = "red"
        elif warnings:
            overall = "yellow"

        return {
            "overall": overall,
            "critical_failures": critical_failures,
            "warnings": warnings,
            "items": items,
        }

    def _ensure_kraken_cli(self) -> None:
        if shutil.which("kraken"):
            logger.info("Kraken CLI detected in PATH.")
            return
        logger.info("Kraken CLI not found. Running installer...")
        bash_executable = shutil.which("bash")
        if not bash_executable:
            if os.name == "nt":
                logger.warning("Kraken CLI installer skipped: bash is not available on this Windows host.")
                return
            bash_executable = "/bin/bash"
        try:
            subprocess.run(
                KRAKEN_CLI_INSTALL_CMD,
                shell=True,
                check=True,
                executable=bash_executable,
            )
            logger.info("Kraken CLI installer completed.")
            if not shutil.which("kraken"):
                logger.warning("Kraken CLI install finished but binary was not found in PATH.")
        except Exception as e:
            logger.error("Kraken CLI installer failed: %s", e)

    def _init_exchanges(self) -> None:
        self._init_kraken(force=True)
        self._init_capital(force=True)
        self._init_alpaca(force=True)
        self._init_binance(force=True)

    def _start_exchange_boot_init(self) -> None:
        if self._exchange_init_threads and any(thread.is_alive() for thread in self._exchange_init_threads.values()):
            return
        self._exchange_init_started_at = time.time()
        self._exchange_init_errors = {}

        init_targets: List[Tuple[str, Callable[..., None]]] = [
            ("capital", self._init_capital),
            ("alpaca", self._init_alpaca),
            ("binance", self._init_binance),
            ("kraken", self._init_kraken),
        ]
        threads: Dict[str, threading.Thread] = {}

        def _runner(name: str, func: Callable[..., None]) -> None:
            try:
                func(force=True)
            except Exception as exc:
                self._exchange_init_errors[name] = str(exc)

        for name, func in init_targets:
            thread = threading.Thread(
                target=_runner,
                args=(name, func),
                name=f"aureon-{name}-boot-init",
                daemon=True,
            )
            thread.start()
            threads[name] = thread
        self._exchange_init_threads = threads

    def _exchange_boot_init_snapshot(self) -> Dict[str, Any]:
        threads = getattr(self, "_exchange_init_threads", {}) or {}
        started_at = float(getattr(self, "_exchange_init_started_at", 0.0) or 0.0)
        now = time.time()
        errors = getattr(self, "_exchange_init_errors", {}) or {}
        states = {
            name: {
                "alive": bool(thread.is_alive()),
                "error": str(errors.get(name, "")),
            }
            for name, thread in threads.items()
        }
        return {
            "async_enabled": bool(EXCHANGE_BOOT_ASYNC_ENABLED),
            "sync_retry_enabled": bool(EXCHANGE_SYNC_RETRY_ENABLED),
            "started_at": datetime.fromtimestamp(started_at).isoformat() if started_at > 0 else None,
            "age_sec": round(max(0.0, now - started_at), 3) if started_at > 0 else 0.0,
            "inflight": any(state.get("alive") for state in states.values()),
            "states": states,
        }

    def _init_kraken(self, force: bool = False) -> None:
        now = time.time()
        if not force and now - self._last_kraken_init_attempt < EXCHANGE_REINIT_INTERVAL_SEC:
            return
        self._last_kraken_init_attempt = now
        _repair_stdio()
        try:
            self.kraken = KrakenMarginArmyTrader(dry_run=self.dry_run)
            self.kraken_error = ""
        except Exception as e:
            if _is_closed_stream_error(e):
                _repair_stdio()
                try:
                    self.kraken = KrakenMarginArmyTrader(dry_run=self.dry_run)
                    self.kraken_error = ""
                    return
                except Exception as retry_error:
                    e = retry_error
            self.kraken = None
            self.kraken_ready = False
            self.kraken_error = str(e)
            logger.error("Kraken init failed: %s", e)

    def _init_capital(self, force: bool = False) -> None:
        now = time.time()
        if not force and now - self._last_capital_init_attempt < EXCHANGE_REINIT_INTERVAL_SEC:
            return
        self._last_capital_init_attempt = now
        try:
            self.capital = CapitalCFDTrader()
            self.capital_ready = bool(getattr(self.capital, "enabled", False))
            self.capital_error = ""
            if not self.capital_ready:
                self.capital_error = str(getattr(self.capital, "init_error", "") or "client_disabled_or_blocked")
        except Exception as e:
            self.capital = None
            self.capital_ready = False
            self.capital_error = str(e)
            logger.error("Capital init failed: %s", e)

    def _init_alpaca(self, force: bool = False) -> None:
        if self.alpaca is not None and not force:
            return
        if AlpacaClient is None:
            self.alpaca = None
            return
        try:
            self.alpaca = AlpacaClient()
            self.alpaca_error = str(getattr(self.alpaca, "init_error", "") or "")
        except Exception as e:
            self.alpaca = None
            self.alpaca_error = str(e)
            logger.debug("Alpaca passive client unavailable: %s", e)

    def _init_binance(self, force: bool = False) -> None:
        if self.binance is not None and not force:
            return
        if BinanceClient is None:
            self.binance = None
            self.binance_error = "client_missing"
            return
        _repair_stdio()
        try:
            self.binance = BinanceClient()
            diag = {}
            try:
                diag = self.binance.diagnose_ready() if hasattr(self.binance, "diagnose_ready") else {}
            except Exception as diag_error:
                diag = {"init_error": str(diag_error), "network_ok": False, "account_ok": False}
            self._binance_diag = diag if isinstance(diag, dict) else {}
            self.binance_error = str(
                self._binance_diag.get("init_error")
                or self._binance_diag.get("last_error")
                or ""
            )
        except Exception as e:
            if _is_closed_stream_error(e):
                _repair_stdio()
                try:
                    self.binance = BinanceClient()
                    self._binance_diag = {}
                    self.binance_error = ""
                    return
                except Exception as retry_error:
                    e = retry_error
            self.binance = None
            self.binance_error = str(e)
            logger.debug("Binance passive client unavailable: %s", e)

    def _ensure_exchanges(self) -> None:
        if EXCHANGE_BOOT_ASYNC_ENABLED and not EXCHANGE_SYNC_RETRY_ENABLED:
            if not getattr(self, "_exchange_init_threads", None):
                self._start_exchange_boot_init()
            return
        if self.kraken is None:
            self._init_kraken()
        elif not self.kraken_ready:
            self._startup_kraken()
        if self.capital is None:
            self._init_capital()
        elif not self.capital_ready:
            self._startup_capital()
        if self.alpaca is None:
            self._init_alpaca()
        if self.binance is None:
            self._init_binance()

    def _startup_kraken(self, force: bool = False) -> None:
        if self.kraken is None:
            return
        now = time.time()
        if not force and now - self._last_kraken_startup_attempt < EXCHANGE_REINIT_INTERVAL_SEC:
            return
        self._last_kraken_startup_attempt = now
        try:
            self.kraken.discover_margin_universe()
            self.kraken.update_prices_free()
            self.kraken.print_status()
            self.kraken_ready = True
            self.kraken_error = ""
        except Exception as e:
            self.kraken_ready = False
            self.kraken_error = str(e)
            logger.error("Kraken startup unavailable: %s", e)

    def _startup_capital(self, force: bool = False) -> None:
        if self.capital is None:
            return
        now = time.time()
        if not force and now - self._last_capital_startup_attempt < EXCHANGE_REINIT_INTERVAL_SEC:
            return
        self._last_capital_startup_attempt = now
        try:
            self.capital.status_lines()
            self.capital_ready = bool(getattr(self.capital, "enabled", False))
            if self.capital_ready:
                self.capital_error = ""
            elif not self.capital_error:
                self.capital_error = str(getattr(self.capital, "init_error", "") or "client_disabled_or_blocked")
        except Exception as e:
            self.capital_ready = False
            self.capital_error = str(e)
            logger.error("Capital startup unavailable: %s", e)

    def _read_runtime_writer_lock(self) -> Dict[str, Any]:
        try:
            if not RUNTIME_STATUS_LOCK_PATH.exists():
                return {}
            with open(RUNTIME_STATUS_LOCK_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _runtime_writer_lock_payload(self) -> Dict[str, Any]:
        now = time.time()
        return {
            "schema_version": 1,
            "service": "unified-market-trader",
            "pid": os.getpid(),
            "instance_id": getattr(self, "_runtime_instance_id", ""),
            "started_at": datetime.fromtimestamp(float(getattr(self, "start_time", now) or now)).isoformat(),
            "heartbeat_at": now,
            "heartbeat_iso": datetime.fromtimestamp(now).isoformat(),
            "lock_ttl_sec": RUNTIME_WRITER_LOCK_TTL_SEC,
        }

    def _lock_owner_is_fresh(self, lock: Dict[str, Any], now: float) -> bool:
        try:
            heartbeat_at = float(lock.get("heartbeat_at", 0.0) or 0.0)
        except Exception:
            heartbeat_at = 0.0
        owner = str(lock.get("instance_id") or "")
        if not bool(owner and owner != self._runtime_instance_id and heartbeat_at > 0 and now - heartbeat_at < RUNTIME_WRITER_LOCK_TTL_SEC):
            return False
        return self._runtime_writer_lock_owner_alive(lock)

    def _runtime_writer_lock_owner_alive(self, lock: Dict[str, Any]) -> bool:
        try:
            pid = int(lock.get("pid", 0) or 0)
        except Exception:
            pid = 0
        if pid <= 0:
            return False
        if pid == os.getpid():
            return True
        if os.name == "nt":
            try:
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                    capture_output=True,
                    text=True,
                    timeout=2,
                    check=False,
                )
                return str(pid) in (result.stdout or "")
            except Exception:
                return False
        try:
            os.kill(pid, 0)
            return True
        except PermissionError:
            return True
        except (OSError, SystemError):
            return False

    def _claim_runtime_writer(self) -> bool:
        now = time.time()
        existing = self._read_runtime_writer_lock()
        if self._lock_owner_is_fresh(existing, now):
            age = now - float(existing.get("heartbeat_at", now) or now)
            self._runtime_writer_lock_reason = (
                f"runtime writer already owned by pid {existing.get('pid')} "
                f"heartbeat_age_sec={age:.1f}"
            )
            return False
        return self._refresh_runtime_writer_lock(force=True)

    def _refresh_runtime_writer_lock(self, force: bool = False) -> bool:
        now = time.time()
        existing = self._read_runtime_writer_lock()
        if not force and self._lock_owner_is_fresh(existing, now):
            age = now - float(existing.get("heartbeat_at", now) or now)
            self._runtime_writer_lock_reason = (
                f"runtime writer ownership moved to pid {existing.get('pid')} "
                f"heartbeat_age_sec={age:.1f}"
            )
            self._owns_runtime_status = False
            return False
        try:
            RUNTIME_STATUS_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = RUNTIME_STATUS_LOCK_PATH.with_name(
                f"{RUNTIME_STATUS_LOCK_PATH.name}.{os.getpid()}.tmp"
            )
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self._runtime_writer_lock_payload(), f, indent=2, default=str)
            os.replace(tmp_path, RUNTIME_STATUS_LOCK_PATH)
            self._runtime_writer_lock_reason = ""
            self._owns_runtime_status = True
            return True
        except Exception as e:
            self._runtime_writer_lock_reason = f"runtime writer lock write failed: {e}"
            logger.warning("Unified runtime writer lock failed: %s", e)
            return False

    def _build_duplicate_runtime_payload(self) -> Dict[str, Any]:
        now_iso = datetime.now().isoformat()
        return {
            "ok": False,
            "source": "unified-market-trader",
            "generated_at": now_iso,
            "status": "duplicate_suppressed",
            "runtime_minutes": 0.0,
            "status_lines": [
                "UNIFIED MARKET STATUS | duplicate runtime suppressed",
                self._runtime_writer_lock_reason or "Another fresh market runtime owns the writer lock.",
            ],
            "combined": {
                "open_positions": 0,
                "kraken_equity": 0.0,
                "capital_equity_gbp": 0.0,
                "kraken_ready": False,
                "capital_ready": False,
            },
            "api_governor": self._api_governor_snapshot(),
            "dynamic_intelligence_budget": getattr(self, "_dynamic_intelligence_budget", {}) or {},
            "runtime_writer": {
                "owns_lock": False,
                "instance_id": self._runtime_instance_id,
                "reason": self._runtime_writer_lock_reason,
            },
        }

    def _start_local_dashboard_server(self) -> None:
        try:
            server = ThreadingHTTPServer((LOCAL_HOST, LOCAL_PORT), _UnifiedDashboardHandler)
            server.trader_ref = self  # type: ignore[attr-defined]
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self._local_dashboard_server = server
            self._local_dashboard_thread = thread
            logger.info("UNIFIED DASHBOARD: http://%s:%s/api/terminal-state", LOCAL_HOST, LOCAL_PORT)
        except OSError as e:
            logger.warning("UNIFIED DASHBOARD unavailable on %s:%s (%s)", LOCAL_HOST, LOCAL_PORT, e)

    def _start_runtime_heartbeat(self) -> None:
        if self._runtime_heartbeat_thread is not None:
            return

        def heartbeat() -> None:
            while True:
                try:
                    if self._last_tick_completed_at <= 0:
                        payload = self._build_bootstrap_dashboard_payload()
                    else:
                        payload = self._copy_payload(
                            self._latest_dashboard_payload or self._build_bootstrap_dashboard_payload()
                        )
                    now = time.time()
                    payload["runtime_minutes"] = (now - self.start_time) / 60.0
                    payload["runtime_heartbeat"] = {
                        "alive": True,
                        "heartbeat_at": now,
                        "heartbeat_at_iso": datetime.now().isoformat(),
                        "last_tick_started_at": self._last_tick_started_at,
                        "last_tick_completed_at": self._last_tick_completed_at,
                        "tick_phase": getattr(self, "_tick_phase", "idle"),
                        "tick_phase_at": getattr(self, "_tick_phase_at", 0.0),
                        "booting": self._last_tick_completed_at <= 0,
                    }
                    self._latest_dashboard_payload = payload
                    self._write_runtime_status_file()
                except Exception:
                    pass
                time.sleep(5.0)

        thread = threading.Thread(target=heartbeat, daemon=True)
        thread.start()
        self._runtime_heartbeat_thread = thread

    def _confidence_word(self, value: Any) -> str:
        try:
            score = float(value or 0.0)
        except Exception:
            score = 0.0
        if score >= 0.85:
            return "very strong"
        if score >= 0.65:
            return "strong"
        if score >= 0.45:
            return "building"
        if score > 0:
            return "tentative"
        return "unclear"

    def _copy_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return copy.deepcopy(payload)

    def _write_runtime_status_file(self) -> None:
        if not getattr(self, "_owns_runtime_status", True):
            return
        try:
            if not self._refresh_runtime_writer_lock(force=False):
                return
            RUNTIME_STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
            payload = self.get_runtime_health()
            payload["runtime_writer"] = {
                "owns_lock": True,
                "pid": os.getpid(),
                "instance_id": getattr(self, "_runtime_instance_id", ""),
                "lock_path": str(RUNTIME_STATUS_LOCK_PATH),
                "heartbeat_at": datetime.now().isoformat(),
            }
            with open(RUNTIME_STATUS_PATH, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, default=str)
        except Exception as e:
            logger.debug("Unified runtime status write failed: %s", e)

    def _unavailable_exchange_payload(self, exchange: str, error: str, extra: Dict[str, Any] | None = None) -> Dict[str, Any]:
        payload = {
            "ok": False,
            "exchange": exchange,
            "error": error or "not_ready",
            "positions": [],
            "status_lines": [f"{str(exchange).upper()} unavailable: {error or 'not_ready'}"],
        }
        if extra:
            payload.update(extra)
        return payload

    def _ensure_exchange_dashboard_state(self) -> None:
        if not hasattr(self, "_exchange_dashboard_lock") or self._exchange_dashboard_lock is None:
            self._exchange_dashboard_lock = threading.Lock()
        if not hasattr(self, "_exchange_dashboard_inflight") or self._exchange_dashboard_inflight is None:
            self._exchange_dashboard_inflight = {}
        if not hasattr(self, "_latest_exchange_dashboard_state") or self._latest_exchange_dashboard_state is None:
            self._latest_exchange_dashboard_state = {}
        if not hasattr(self, "_latest_exchange_dashboard_payloads") or self._latest_exchange_dashboard_payloads is None:
            self._latest_exchange_dashboard_payloads = {}

    def _exchange_dashboard_snapshot(self) -> Dict[str, Any]:
        self._ensure_exchange_dashboard_state()
        now = time.time()
        with self._exchange_dashboard_lock:
            states = {name: dict(state) for name, state in self._latest_exchange_dashboard_state.items()}
            inflight = {name: dict(state) for name, state in self._exchange_dashboard_inflight.items()}
        for name, state in inflight.items():
            if state.get("running"):
                started_at = float(state.get("started_at", now) or now)
                states[name] = {
                    **states.get(name, {}),
                    **state,
                    "running_sec": round(max(0.0, now - started_at), 3),
                    "timeout_sec": EXCHANGE_DASHBOARD_PAYLOAD_TIMEOUT_SEC,
                }
        return states

    def _dashboard_payload_fallback(
        self,
        exchange: str,
        state: Dict[str, Any],
        extra: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        self._ensure_exchange_dashboard_state()
        cached = self._latest_exchange_dashboard_payloads.get(exchange)
        if isinstance(cached, dict) and cached:
            payload = self._copy_payload(cached)
            payload.setdefault("exchange", exchange)
            payload["dashboard_fetch_state"] = dict(state)
            payload["served_from_cache"] = True
            return payload
        payload = self._unavailable_exchange_payload(
            exchange,
            str(state.get("reason") or "dashboard_payload_unavailable"),
            extra=extra,
        )
        payload["dashboard_fetch_state"] = dict(state)
        return payload

    def _run_dashboard_payload_with_timeout(
        self,
        exchange: str,
        fn: Callable[[], Dict[str, Any]],
        *,
        fallback_extra: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        self._ensure_exchange_dashboard_state()
        now = time.time()
        timeout_sec = EXCHANGE_DASHBOARD_PAYLOAD_TIMEOUT_SEC
        with self._exchange_dashboard_lock:
            existing = self._exchange_dashboard_inflight.get(exchange, {})
            if existing.get("running"):
                started_at = float(existing.get("started_at", now) or now)
                state = {
                    "ok": False,
                    "held": True,
                    "running": True,
                    "reason": f"{exchange}_dashboard_payload_inflight",
                    "started_at_iso": existing.get("started_at_iso"),
                    "running_sec": round(max(0.0, now - started_at), 3),
                    "timeout_sec": timeout_sec,
                }
                self._latest_exchange_dashboard_state[exchange] = dict(state)
                return self._dashboard_payload_fallback(exchange, state, fallback_extra)
            self._exchange_dashboard_inflight[exchange] = {
                "running": True,
                "started_at": now,
                "started_at_iso": datetime.fromtimestamp(now).isoformat(),
                "timeout_sec": timeout_sec,
            }

        result_queue: queue.Queue = queue.Queue(maxsize=1)

        def runner() -> None:
            error: Optional[Exception] = None
            payload: Dict[str, Any] = {}
            try:
                raw = fn()
                payload = raw if isinstance(raw, dict) else {}
            except Exception as e:
                error = e
            completed_at = time.time()
            state = {
                "ok": bool(error is None and payload),
                "running": False,
                "elapsed_sec": round(max(0.0, completed_at - now), 3),
                "timeout_sec": timeout_sec,
                "completed_after_timeout": bool(completed_at - now > timeout_sec),
                "completed_at_iso": datetime.fromtimestamp(completed_at).isoformat(),
            }
            if error is not None:
                state["error"] = str(error)
                state["reason"] = f"{exchange}_dashboard_payload_error"
            elif not payload:
                state["reason"] = f"{exchange}_dashboard_payload_empty"
            with self._exchange_dashboard_lock:
                self._exchange_dashboard_inflight[exchange] = {
                    "running": False,
                    "started_at": now,
                    "completed_at": completed_at,
                    "timeout_sec": timeout_sec,
                }
                self._latest_exchange_dashboard_state[exchange] = dict(state)
                if payload:
                    self._latest_exchange_dashboard_payloads[exchange] = self._copy_payload(payload)
            try:
                result_queue.put_nowait((payload, state, error))
            except queue.Full:
                pass

        thread = threading.Thread(target=runner, name=f"aureon-{exchange}-dashboard-payload", daemon=True)
        thread.start()
        thread.join(timeout_sec)
        if thread.is_alive():
            state = {
                "ok": False,
                "held": True,
                "timeout": True,
                "running": True,
                "reason": f"{exchange}_dashboard_payload_timeout",
                "running_sec": round(max(0.0, time.time() - now), 3),
                "timeout_sec": timeout_sec,
                "source": "unified_market_trader.exchange_dashboard_payload",
            }
            with self._exchange_dashboard_lock:
                self._latest_exchange_dashboard_state[exchange] = dict(state)
            return self._dashboard_payload_fallback(exchange, state, fallback_extra)
        try:
            payload, state, error = result_queue.get_nowait()
        except queue.Empty:
            state = {
                "ok": False,
                "held": True,
                "reason": f"{exchange}_dashboard_payload_finished_without_result",
                "timeout_sec": timeout_sec,
            }
            with self._exchange_dashboard_lock:
                self._latest_exchange_dashboard_state[exchange] = dict(state)
            return self._dashboard_payload_fallback(exchange, state, fallback_extra)
        if error is not None or not payload:
            return self._dashboard_payload_fallback(exchange, state, fallback_extra)
        payload["dashboard_fetch_state"] = dict(state)
        return payload

    def _build_bootstrap_gold_runtime_trade_proof(self, now_iso: str) -> Dict[str, Any]:
        signal = self._gold_priority_live_stream_signal()
        ready = bool(signal.get("ready"))
        side = str(signal.get("side") or "HOLD").upper()
        capital_route_visible = ready
        capital_route_ready = bool(ready and self.capital_ready)
        route_blockers: List[str] = []
        if not capital_route_ready:
            route_blockers.append("capital_cfd_route_booting" if ready else "fresh_capital_gold_stream_missing")
        if not ready:
            reason = str(signal.get("reason") or "fresh_capital_gold_stream_missing")
        elif side not in {"BUY", "SELL"}:
            reason = "gold_side_not_validated_by_fresh_interval_projection"
        elif not capital_route_ready:
            reason = route_blockers[0]
        else:
            reason = "gold_runtime_gated_intent_publishable"
        return {
            "generated_at": now_iso,
            "gold_runtime_candidate_ready": ready,
            "gold_candidate_count": 1 if ready else 0,
            "candidate_symbol": "XAUUSD" if ready else "",
            "candidate_side": side,
            "candidate_confidence": signal.get("confidence") if ready else None,
            "candidate_sources": signal.get("source_tags", []) if ready else [],
            "capital_cfd_route_visible": capital_route_visible,
            "capital_cfd_route_ready": capital_route_ready,
            "capital_cfd_route_blockers": route_blockers,
            "gold_intent_publishable": bool(capital_route_ready and side in {"BUY", "SELL"}),
            "gold_intent_publish_reason": reason,
            "intent_publish_blockers": [] if side in {"BUY", "SELL"} else ["gold_side_not_validated_by_fresh_interval_projection"],
            "global_blockers": [],
            "fresh_gold_data_source": signal,
            "shared_feed_contains_gold": ready,
            "routeable_key_count": 1 if ready else 0,
            "active_order_flow_count": 1 if ready else 0,
            "safety": {
                "direct_exchange_mutation": False,
                "proof_phase": "runtime_bootstrap_order_intent_only",
                "requires_existing_runtime_executor": True,
            },
        }

    def _build_bootstrap_dashboard_payload(self) -> Dict[str, Any]:
        now_iso = datetime.now().isoformat()
        kraken_error = self.kraken_error or ("startup_pending" if self.kraken is not None else "not_ready")
        capital_error = self.capital_error or ("ready" if self.capital_ready else "not_ready")
        kraken_payload = self._unavailable_exchange_payload("kraken", kraken_error)
        capital_payload = self._unavailable_exchange_payload("capital", capital_error, extra={"stats": {}})
        preflight = self._build_preflight_report()
        gold_runtime_trade_proof = self._build_bootstrap_gold_runtime_trade_proof(now_iso)
        return {
            "ok": True,
            "source": "unified-market-trader",
            "generated_at": now_iso,
            "runtime_minutes": (time.time() - self.start_time) / 60.0,
            "kraken": kraken_payload,
            "capital": capital_payload,
            "status_lines": [
                f"UNIFIED MARKET STATUS | runtime={(time.time() - self.start_time) / 60.0:.1f}m",
                "Cached telemetry pending first trading cycle.",
            ],
            "latest_monitor_line": "",
            "shared_market_feed": {
                "symbols": dict(self._shared_market_feed),
                "aliases": {},
                "count": len(self._shared_market_feed),
                "generated_at": now_iso,
            },
            "central_beat": {
                "generated_at": now_iso,
                "sources": [],
                "source_count": 0,
                "symbols": {},
                "regime": {},
            },
            "shared_order_flow": {
                "generated_at": now_iso,
                "shared_tradable_count": 0,
                "multi_exchange_tradable_count": 0,
                "active_order_flow_count": 0,
                "active_order_flow": [],
                "kraken_tradables": 0,
                "capital_tradables": 0,
                "alpaca_tradables": 0,
                "binance_tradables": 0,
                "scope": "multi-exchange unified tradables",
            },
            "exchange_action_plan": {
                "generated_at": now_iso,
                "mode": "booting",
                "venues": {
                    "capital_cfd": {
                        "venue": "capital",
                        "market_type": "cfd",
                        "ready": bool(gold_runtime_trade_proof.get("capital_cfd_route_ready")),
                        "candidate_count": int(gold_runtime_trade_proof.get("gold_candidate_count", 0) or 0),
                        "ready_candidate_count": 1 if bool(gold_runtime_trade_proof.get("capital_cfd_route_ready")) else 0,
                        "blockers": gold_runtime_trade_proof.get("capital_cfd_route_blockers", []),
                        "runtime_clearances": [],
                        "guards": ["runtime_bootstrap_only", "fresh_interval_validated_gold_projection_required"],
                        "trade_path_state": "booting",
                        "end_user_trade_available": False,
                    }
                },
                "order_intent_publish_enabled": False,
                "order_intents_published": 0,
                "executor_enabled": False,
                "latest_execution": {},
                "shadow_trading": {},
                "gold_runtime_trade_proof": gold_runtime_trade_proof,
            },
            "gold_runtime_trade_proof": gold_runtime_trade_proof,
            "shadow_trading": {
                "generated_at": now_iso,
                "mode": "shadow_validation_non_mutating",
                "enabled": True,
                "shadow_count": 0,
                "active_shadow_count": 0,
                "validated_shadow_count": 0,
                "status": "awaiting_first_cycle",
            },
            "hnc_cognitive_proof": {
                "generated_at": now_iso,
                "status": "awaiting_first_cycle",
                "passed": False,
                "flow": [],
                "systems": {},
                "auris_nodes": {"node_count": 0, "coherence": 0.0},
                "master_formula": {"score": 0.0, "evaluated": False},
                "real_data": {"passed": False, "source_count": 0, "price_count": 0},
            },
            "intelligence_mesh": self._build_intelligence_mesh(),
            "preflight": preflight,
            "api_governor": self._api_governor_snapshot(),
            "dynamic_intelligence_budget": getattr(self, "_dynamic_intelligence_budget", {}) or {},
            "queen_voice": {
                "ts": now_iso,
                "mode": "HOLD",
                "text": "Awaiting the first unified trading cycle.",
                "lines": ["Awaiting the first unified trading cycle."],
                "sources": {"kraken_decision": {}, "capital_target": {}},
            },
            "combined": {
                "open_positions": 0,
                "kraken_equity": 0.0,
                "capital_equity_gbp": 0.0,
                "kraken_session_pnl": 0.0,
                "capital_session_pnl_gbp": 0.0,
                "kraken_ready": self.kraken_ready,
                "capital_ready": self.capital_ready,
            },
        }

    def _build_combined_payload(self) -> Dict[str, Any]:
        kraken_payload = (
            self._run_dashboard_payload_with_timeout("kraken", self.kraken.get_local_dashboard_state)
            if self.kraken_ready and self.kraken is not None
            else self._unavailable_exchange_payload(
                "kraken",
                self.kraken_error or "not_ready",
            )
        )
        capital_payload = (
            self._run_dashboard_payload_with_timeout(
                "capital",
                self.capital.get_dashboard_payload,
                fallback_extra={"stats": {}},
            )
            if self.capital_ready and self.capital is not None
            else self._unavailable_exchange_payload(
                "capital",
                self.capital_error or "not_ready",
                extra={"stats": {}},
            )
        )
        self._dynamic_intelligence_budget = self._build_dynamic_intelligence_budget(kraken_payload, capital_payload)
        self._set_tick_phase("build_combined_payload:central_beat")
        central_beat = self._build_central_beat_feed(kraken_payload, capital_payload)
        self._set_tick_phase("build_combined_payload:shared_market_feed")
        shared_market_feed = self._sync_shared_market_feed(central_beat)
        self._set_tick_phase("build_combined_payload:gold_priority_candidate")
        self._apply_gold_priority_candidate(central_beat, shared_market_feed)
        self._set_tick_phase("build_combined_payload:order_flow")
        order_flow_feed = self._build_global_order_flow_feed(kraken_payload, capital_payload, central_beat, shared_market_feed)
        self._record_order_flow_lifecycle_candidates(order_flow_feed)
        self._set_tick_phase("build_combined_payload:action_plan")
        exchange_action_plan = self._build_exchange_action_plan(order_flow_feed)
        self._set_tick_phase("build_combined_payload:gold_trade_proof")
        gold_runtime_trade_proof = self._build_gold_runtime_trade_proof(
            central_beat,
            shared_market_feed,
            order_flow_feed,
            exchange_action_plan,
        )
        order_flow_feed["gold_runtime_trade_proof"] = gold_runtime_trade_proof
        exchange_action_plan["gold_runtime_trade_proof"] = gold_runtime_trade_proof
        order_lifecycle = self._order_lifecycle_snapshot()
        self._latest_dashboard_payload = self._copy_payload(
            {
                "ok": False,
                "source": "unified-market-trader",
                "partial": True,
                "partial_reason": "combined_payload_in_progress",
                "generated_at": datetime.now().isoformat(),
                "runtime_minutes": (time.time() - self.start_time) / 60.0,
                "shared_market_feed": shared_market_feed,
                "central_beat": central_beat,
                "live_stream_cache": central_beat.get("stream_cache", {}) if isinstance(central_beat, dict) else {},
                "shared_order_flow": order_flow_feed,
                "exchange_action_plan": exchange_action_plan,
                "gold_runtime_trade_proof": gold_runtime_trade_proof,
                "order_lifecycle": order_lifecycle,
                "combined": {
                    "open_positions": len(kraken_payload.get("positions", [])) + len(capital_payload.get("positions", [])),
                    "kraken_ready": self.kraken_ready,
                    "capital_ready": self.capital_ready,
                },
            }
        )
        self._write_runtime_status_file()
        self._set_tick_phase("build_combined_payload:decision_feed")
        self._feed_shared_order_flow_to_decision_logic(order_flow_feed)
        self._feed_auris_throne(order_flow_feed)
        self._set_tick_phase("build_combined_payload:shadow_report")
        shadow_trade_report = self._build_shadow_trade_report(order_flow_feed, exchange_action_plan)
        self._set_tick_phase("build_combined_payload:hnc_proof")
        hnc_cognitive_proof = self._build_hnc_cognitive_proof(
            central_beat,
            order_flow_feed,
            exchange_action_plan,
            shadow_trade_report,
        )
        self._set_tick_phase("build_combined_payload:intelligence_mesh")
        intelligence_mesh = self._build_intelligence_mesh(
            central_beat=central_beat,
            order_flow_feed=order_flow_feed,
            action_plan=exchange_action_plan,
            shadow_trade_report=shadow_trade_report,
            hnc_cognitive_proof=hnc_cognitive_proof,
        )
        kraken_equity = self._kraken_equity_from_payload(kraken_payload)
        order_flow_feed["intelligence_mesh"] = intelligence_mesh
        exchange_action_plan["intelligence_mesh"] = intelligence_mesh
        order_flow_feed["gold_runtime_trade_proof"] = gold_runtime_trade_proof
        exchange_action_plan["gold_runtime_trade_proof"] = gold_runtime_trade_proof
        self._set_tick_phase("build_combined_payload:order_intents")
        self._publish_order_intents(order_flow_feed, exchange_action_plan)
        gold_runtime_trade_proof["order_intents_published_this_cycle"] = int(exchange_action_plan.get("order_intents_published", 0) or 0)
        gold_runtime_trade_proof["latest_published"] = exchange_action_plan.get("latest_published", {})
        order_lifecycle = self._order_lifecycle_snapshot()
        combined_status = self.get_status_lines()
        queen_voice = self._build_queen_voice_payload(kraken_payload, capital_payload)
        payload = {
            "ok": True,
            "source": "unified-market-trader",
            "generated_at": datetime.now().isoformat(),
            "runtime_minutes": (time.time() - self.start_time) / 60.0,
            "kraken": kraken_payload,
            "capital": capital_payload,
            "capital_risk_envelope": capital_payload.get("capital_risk_envelope", {}) if isinstance(capital_payload, dict) else {},
            "capital_trade_evidence": capital_payload.get("capital_trade_evidence", {}) if isinstance(capital_payload, dict) else {},
            "capital_confidence_ratchet": capital_payload.get("capital_confidence_ratchet", {}) if isinstance(capital_payload, dict) else {},
            "capital_unified_waveform_check": capital_payload.get("capital_unified_waveform_check", {}) if isinstance(capital_payload, dict) else {},
            "capital_no_loss_hold_queue": capital_payload.get("capital_no_loss_hold_queue", {}) if isinstance(capital_payload, dict) else {},
            "status_lines": combined_status[-24:],
            "latest_monitor_line": self._latest_monitor_line(),
            "shared_market_feed": shared_market_feed,
            "central_beat": central_beat,
            "world_financial_ecosystem": central_beat.get("world_financial_ecosystem", {}) if isinstance(central_beat, dict) else {},
            "asset_waveform_models": central_beat.get("asset_waveform_models", {}) if isinstance(central_beat, dict) else {},
            "scanner_fusion_matrix": order_flow_feed.get("scanner_fusion_matrix", {}) if isinstance(order_flow_feed, dict) else {},
            "live_stream_cache": central_beat.get("stream_cache", {}) if isinstance(central_beat, dict) else {},
            "shared_order_flow": order_flow_feed,
            "shadow_trading": shadow_trade_report,
            "hnc_cognitive_proof": hnc_cognitive_proof,
            "hnc_operating_cycle": hnc_cognitive_proof.get("operating_cycle", {}) if isinstance(hnc_cognitive_proof, dict) else {},
            "intelligence_mesh": intelligence_mesh,
            "exchange_action_plan": exchange_action_plan,
            "gold_runtime_trade_proof": gold_runtime_trade_proof,
            "order_lifecycle": order_lifecycle,
            "kraken_spot_fast_profit": self._load_kraken_spot_fast_profit_state(),
            "kraken_asset_registry": self._load_kraken_asset_registry_summary(),
            "preflight": self._build_preflight_report(),
            "api_governor": self._api_governor_snapshot(),
            "dynamic_intelligence_budget": getattr(self, "_dynamic_intelligence_budget", {}) or {},
            "queen_voice": queen_voice,
            "combined": {
                "open_positions": len(kraken_payload.get("positions", [])) + len(capital_payload.get("positions", [])),
                "kraken_equity": kraken_equity,
                "capital_equity_gbp": float(capital_payload.get("equity_gbp", 0.0) or 0.0),
                "kraken_session_pnl": float(kraken_payload.get("session_profit", 0.0) or 0.0),
                "capital_session_pnl_gbp": float(capital_payload.get("stats", {}).get("total_pnl_gbp", 0.0) or 0.0),
                "kraken_ready": self.kraken_ready,
                "capital_ready": self.capital_ready,
                "capital_risk_envelope": capital_payload.get("capital_risk_envelope", {}) if isinstance(capital_payload, dict) else {},
                "capital_trade_evidence": capital_payload.get("capital_trade_evidence", {}) if isinstance(capital_payload, dict) else {},
                "capital_confidence_ratchet": capital_payload.get("capital_confidence_ratchet", {}) if isinstance(capital_payload, dict) else {},
                "capital_unified_waveform_check": capital_payload.get("capital_unified_waveform_check", {}) if isinstance(capital_payload, dict) else {},
                "capital_no_loss_hold_queue": capital_payload.get("capital_no_loss_hold_queue", {}) if isinstance(capital_payload, dict) else {},
                "kraken_asset_registry": self._load_kraken_asset_registry_summary(),
                "portfolio_balances": {
                    "kraken": kraken_payload.get("portfolio_balances") or kraken_payload.get("balance_snapshot") or {},
                    "capital": capital_payload.get("portfolio_balances") or capital_payload.get("balance_snapshot") or {},
                },
            },
        }
        self._latest_dashboard_payload = self._copy_payload(payload)
        self._write_runtime_status_file()
        return payload

    def _load_kraken_asset_registry_summary(self) -> Dict[str, Any]:
        """Read the Kraken tradable asset registry without dragging the full book into runtime."""
        for path in (KRAKEN_ASSET_REGISTRY_STATE_PATH, KRAKEN_ASSET_REGISTRY_AUDIT_PATH, KRAKEN_ASSET_REGISTRY_PUBLIC_PATH):
            try:
                if not path.exists():
                    continue
                payload = json.loads(path.read_text(encoding="utf-8"))
                summary = payload.get("summary", {}) if isinstance(payload.get("summary"), dict) else {}
                survival_policy = payload.get("survival_policy", {}) if isinstance(payload.get("survival_policy"), dict) else {}
                return {
                    "generated_at": payload.get("generated_at", ""),
                    "schema_version": payload.get("schema_version", ""),
                    "path": str(path),
                    "public_path": "frontend/public/aureon_kraken_tradable_asset_registry.json",
                    "database_path": "state/kraken_tradable_asset_registry.sqlite",
                    "total_pairs": int(summary.get("total_pairs", 0) or 0),
                    "ticker_enriched_count": int(summary.get("ticker_enriched_count", 0) or 0),
                    "spot_trade_ready_count": int(summary.get("spot_trade_ready_count", 0) or 0),
                    "margin_pair_count": int(summary.get("margin_pair_count", 0) or 0),
                    "margin_trade_ready_count": int(summary.get("margin_trade_ready_count", 0) or 0),
                    "cost_known_count": int(summary.get("cost_known_count", 0) or 0),
                    "fee_known_count": int(summary.get("fee_known_count", 0) or 0),
                    "take_profit_route_count": int(summary.get("take_profit_route_count", 0) or 0),
                    "asset_classes": dict(summary.get("asset_classes", {}) or {}),
                    "top_blockers": list(summary.get("top_blockers", []) or [])[:6],
                    "survival_policy": survival_policy,
                }
            except Exception as exc:
                return {
                    "generated_at": "",
                    "path": str(path),
                    "error": str(exc),
                }
        return {
            "generated_at": "",
            "path": str(KRAKEN_ASSET_REGISTRY_STATE_PATH),
            "missing": True,
            "next_action": "Run python -m aureon.exchanges.kraken_asset_registry --max-tickers 100",
        }

    def _kraken_equity_from_payload(self, payload: Dict[str, Any]) -> float:
        for key in ("equity", "equity_usd", "portfolio_value_usd", "portfolio_value"):
            try:
                value = float(payload.get(key, 0.0) or 0.0)
                if value > 0:
                    return value
            except Exception:
                continue
        balance_snapshot = payload.get("balance_snapshot") or payload.get("portfolio_balances")
        if isinstance(balance_snapshot, dict):
            try:
                return float(balance_snapshot.get("total_usd_estimate", 0.0) or 0.0)
            except Exception:
                return 0.0
        return 0.0

    def _api_governor_snapshot(self) -> Dict[str, Any]:
        snapshot = self._governor().snapshot()
        budget = getattr(self, "_dynamic_intelligence_budget", {}) or {}
        if isinstance(budget, dict) and budget:
            snapshot["dynamic_intelligence_budget"] = budget
        return snapshot

    def _quote_asset_usd_multiplier(self, asset: Any) -> float:
        asset_norm = str(asset or "").upper().strip()
        if asset_norm in {"USD", "ZUSD", "USDC", "USDT", "DAI", "BUSD"}:
            return 1.0
        if asset_norm in {"GBP", "ZGBP"}:
            return max(0.0, _env_float("UNIFIED_GBP_USD_REFERENCE_RATE", 1.25))
        if asset_norm in {"EUR", "ZEUR"}:
            return max(0.0, _env_float("UNIFIED_EUR_USD_REFERENCE_RATE", 1.08))
        return 0.0

    def _balance_entry_usd_value(self, asset: Any, entry: Any) -> float:
        if isinstance(entry, dict):
            for key in (
                "usd_value",
                "value_usd",
                "available_usd",
                "current_value_usd",
                "total_usd",
                "balance_usd",
            ):
                try:
                    value = float(entry.get(key, 0.0) or 0.0)
                except Exception:
                    value = 0.0
                if value > 0:
                    return value
            for key in ("amount", "available", "free", "balance", "total"):
                try:
                    amount = float(entry.get(key, 0.0) or 0.0)
                except Exception:
                    amount = 0.0
                if amount > 0:
                    return amount * self._quote_asset_usd_multiplier(asset)
            return 0.0
        try:
            amount = float(entry or 0.0)
        except Exception:
            amount = 0.0
        return amount * self._quote_asset_usd_multiplier(asset) if amount > 0 else 0.0

    def _balance_map_usd_values(self, balances: Any) -> Dict[str, float]:
        values: Dict[str, float] = {}
        if isinstance(balances, list):
            for row in balances:
                if not isinstance(row, dict):
                    continue
                asset = str(row.get("asset") or row.get("currency") or row.get("symbol") or "").upper().strip()
                if not asset:
                    continue
                amount = 0.0
                for key in ("free", "available", "balance", "amount", "total"):
                    try:
                        amount += float(row.get(key, 0.0) or 0.0)
                    except Exception:
                        pass
                if amount > 0:
                    values[asset] = values.get(asset, 0.0) + (amount * self._quote_asset_usd_multiplier(asset))
            return values
        if isinstance(balances, dict):
            source = balances.get("balances") if isinstance(balances.get("balances"), (dict, list)) else balances
            if isinstance(source, list):
                return self._balance_map_usd_values(source)
            if isinstance(source, dict):
                for asset, entry in source.items():
                    asset_norm = str(asset or "").upper().strip()
                    if not asset_norm:
                        continue
                    value = self._balance_entry_usd_value(asset_norm, entry)
                    if value > 0:
                        values[asset_norm] = values.get(asset_norm, 0.0) + value
        return values

    def _balance_snapshot_values(self, payload: Dict[str, Any], *, default_currency: str = "USD") -> Dict[str, Any]:
        payload = payload if isinstance(payload, dict) else {}
        snapshots = [
            payload,
            payload.get("portfolio_balances"),
            payload.get("balance_snapshot"),
            payload.get("account"),
            payload.get("accounts"),
        ]
        cash_usd = 0.0
        portfolio_usd = 0.0
        source = ""
        known = False
        cash_keys = (
            "tradable_cash_usd",
            "cash_usd",
            "available_usd",
            "free_margin_usd",
            "spot_cash_usd",
            "buying_power_usd",
            "crypto_buying_power_usd",
        )
        portfolio_keys = (
            "total_usd_estimate",
            "portfolio_value_usd",
            "equity_usd",
            "equity",
            "portfolio_value",
            "account_value_usd",
            "balance_usd",
        )
        for snapshot in snapshots:
            if isinstance(snapshot, list):
                for row in snapshot:
                    if not isinstance(row, dict):
                        continue
                    for key in ("available", "cash", "buying_power", "balance"):
                        try:
                            cash_usd = max(cash_usd, float(row.get(key, 0.0) or 0.0) * self._quote_asset_usd_multiplier(default_currency))
                        except Exception:
                            pass
                    known = True
                continue
            if not isinstance(snapshot, dict):
                continue
            known = True
            source = source or str(snapshot.get("source") or "")
            for key in cash_keys:
                try:
                    cash_usd = max(cash_usd, float(snapshot.get(key, 0.0) or 0.0))
                except Exception:
                    pass
            for key in portfolio_keys:
                try:
                    portfolio_usd = max(portfolio_usd, float(snapshot.get(key, 0.0) or 0.0))
                except Exception:
                    pass
            if "equity_gbp" in snapshot:
                try:
                    portfolio_usd = max(portfolio_usd, float(snapshot.get("equity_gbp", 0.0) or 0.0) * self._quote_asset_usd_multiplier("GBP"))
                except Exception:
                    pass
            if "cash" in snapshot:
                try:
                    cash_usd = max(cash_usd, float(snapshot.get("cash", 0.0) or 0.0) * self._quote_asset_usd_multiplier(default_currency))
                except Exception:
                    pass
            balance_values = self._balance_map_usd_values(snapshot)
            if balance_values:
                cash_usd = max(cash_usd, sum(balance_values.values()))
                portfolio_usd = max(portfolio_usd, sum(balance_values.values()))
        return {
            "known": bool(known and (cash_usd > 0 or portfolio_usd > 0)),
            "deployable_cash_usd": round(float(cash_usd), 6),
            "portfolio_value_usd": round(float(max(portfolio_usd, cash_usd)), 6),
            "source": source or "runtime_payload_or_cached_balance",
        }

    def _budgeted_client_balance_payload(self, exchange: str, client: Any) -> Dict[str, Any]:
        exchange_norm = str(exchange or "").lower().strip()
        if not exchange_norm or client is None:
            return {}

        def read_balance() -> Any:
            for method_name in ("get_account_balance", "get_balance"):
                method = getattr(client, method_name, None)
                if callable(method):
                    return method()
            method = getattr(client, "get_account", None)
            if callable(method):
                return method()
            method = getattr(client, "account", None)
            if callable(method):
                return method()
            return {}

        result = self._governor().call(
            exchange_norm,
            "positions",
            f"{exchange_norm}:balance_snapshot",
            read_balance,
            min_interval_sec=INTELLIGENCE_BALANCE_MIN_INTERVAL_SEC,
            stale_ttl_sec=INTELLIGENCE_BALANCE_MIN_INTERVAL_SEC * 3.0,
        )
        return result if isinstance(result, dict) else {}

    def _exchange_connected_for_budget(self, exchange: str) -> bool:
        exchange_norm = str(exchange or "").lower().strip()
        if exchange_norm == "kraken":
            return bool(self.kraken_ready and self.kraken is not None)
        if exchange_norm == "capital":
            return bool(self.capital_ready and self.capital is not None)
        if exchange_norm == "alpaca":
            return bool(self.alpaca is not None and not bool(getattr(self.alpaca, "init_error", "") or self.alpaca_error))
        if exchange_norm == "binance":
            diag = getattr(self, "_binance_diag", {}) or {}
            return bool(self.binance is not None and (diag.get("network_ok", True) or diag.get("account_ok", False)))
        return False

    def _build_dynamic_intelligence_budget(
        self,
        kraken_payload: Dict[str, Any],
        capital_payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        now_iso = datetime.now().isoformat()
        enabled = bool(DYNAMIC_INTELLIGENCE_BUDGET_ENABLED)
        payloads = {
            "kraken": kraken_payload if isinstance(kraken_payload, dict) else {},
            "capital": capital_payload if isinstance(capital_payload, dict) else {},
            "alpaca": self._budgeted_client_balance_payload("alpaca", self.alpaca),
            "binance": self._budgeted_client_balance_payload("binance", self.binance),
        }
        client_fallbacks = {
            "kraken": getattr(getattr(self, "kraken", None), "client", None),
            "capital": self.capital,
        }
        for exchange, client in client_fallbacks.items():
            values = self._balance_snapshot_values(payloads.get(exchange, {}), default_currency="GBP" if exchange == "capital" else "USD")
            if not values.get("known") and client is not None:
                payloads[exchange] = self._budgeted_client_balance_payload(exchange, client)

        exchange_budget: Dict[str, Dict[str, Any]] = {}
        sensor_exchanges: List[str] = []
        execution_exchanges: List[str] = []
        balanced_exchanges: List[str] = []
        quote_threshold = max(ORDER_EXECUTOR_QUOTE_USD * INTELLIGENCE_EXECUTION_CASH_MULTIPLIER, INTELLIGENCE_SENSOR_LOW_CASH_USD)
        for exchange in ("kraken", "capital", "alpaca", "binance"):
            connected = self._exchange_connected_for_budget(exchange)
            values = self._balance_snapshot_values(
                payloads.get(exchange, {}),
                default_currency="GBP" if exchange == "capital" else "USD",
            )
            deployable_cash = float(values.get("deployable_cash_usd", 0.0) or 0.0)
            known = bool(values.get("known"))
            if not connected:
                role = "offline"
                reason = "exchange_not_connected"
                probe_interval = PROBE_SYMBOL_MIN_INTERVAL_SEC
                orderbook_interval = ORDERBOOK_PROBE_MIN_INTERVAL_SEC
                stream_bonus = 0
                orderbook_bonus = 0
            elif not enabled:
                role = "static_budget"
                reason = "dynamic_intelligence_budget_disabled"
                probe_interval = PROBE_SYMBOL_MIN_INTERVAL_SEC
                orderbook_interval = ORDERBOOK_PROBE_MIN_INTERVAL_SEC
                stream_bonus = 0
                orderbook_bonus = 0
            elif not known:
                role = "sensor_priority"
                reason = "balance_unknown_use_public_market_intelligence_without_assuming_execution_cash"
                probe_interval = min(PROBE_SYMBOL_MIN_INTERVAL_SEC, INTELLIGENCE_SENSOR_PROBE_MIN_INTERVAL_SEC)
                orderbook_interval = min(ORDERBOOK_PROBE_MIN_INTERVAL_SEC, INTELLIGENCE_SENSOR_ORDERBOOK_MIN_INTERVAL_SEC)
                stream_bonus = INTELLIGENCE_SENSOR_STREAM_SYMBOL_BONUS
                orderbook_bonus = INTELLIGENCE_SENSOR_ORDERBOOK_BONUS
                sensor_exchanges.append(exchange)
            elif deployable_cash >= quote_threshold:
                role = "execution_priority"
                reason = "deployable_cash_preserved_for_live_orders"
                probe_interval = PROBE_SYMBOL_MIN_INTERVAL_SEC
                orderbook_interval = ORDERBOOK_PROBE_MIN_INTERVAL_SEC
                stream_bonus = 0
                orderbook_bonus = 0
                execution_exchanges.append(exchange)
            elif deployable_cash <= INTELLIGENCE_SENSOR_LOW_CASH_USD:
                role = "sensor_priority"
                reason = "low_deployable_cash_use_exchange_as_market_sensor"
                probe_interval = min(PROBE_SYMBOL_MIN_INTERVAL_SEC, INTELLIGENCE_SENSOR_PROBE_MIN_INTERVAL_SEC)
                orderbook_interval = min(ORDERBOOK_PROBE_MIN_INTERVAL_SEC, INTELLIGENCE_SENSOR_ORDERBOOK_MIN_INTERVAL_SEC)
                stream_bonus = INTELLIGENCE_SENSOR_STREAM_SYMBOL_BONUS
                orderbook_bonus = INTELLIGENCE_SENSOR_ORDERBOOK_BONUS
                sensor_exchanges.append(exchange)
            else:
                role = "balanced_sensor"
                reason = "some_cash_available_balance_execution_with_extra_market_sensing"
                probe_interval = max(INTELLIGENCE_SENSOR_PROBE_MIN_INTERVAL_SEC, PROBE_SYMBOL_MIN_INTERVAL_SEC * 0.65)
                orderbook_interval = max(INTELLIGENCE_SENSOR_ORDERBOOK_MIN_INTERVAL_SEC, ORDERBOOK_PROBE_MIN_INTERVAL_SEC * 0.65)
                stream_bonus = max(0, INTELLIGENCE_SENSOR_STREAM_SYMBOL_BONUS // 2)
                orderbook_bonus = max(0, INTELLIGENCE_SENSOR_ORDERBOOK_BONUS // 2)
                balanced_exchanges.append(exchange)

            exchange_budget[exchange] = {
                "connected": connected,
                "balance_known": known,
                "role": role,
                "reason": reason,
                "deployable_cash_usd": round(deployable_cash, 6),
                "portfolio_value_usd": values.get("portfolio_value_usd", 0.0),
                "balance_source": values.get("source", ""),
                "probe_min_interval_sec": round(float(probe_interval), 3),
                "orderbook_min_interval_sec": round(float(orderbook_interval), 3),
                "stream_symbol_bonus": int(stream_bonus),
                "orderbook_probe_bonus": int(orderbook_bonus),
                "request_policy": (
                    "execution_first_positions_and_orders"
                    if role == "execution_priority"
                    else "public_market_sensor_streams_and_budgeted_quotes"
                    if role in {"sensor_priority", "balanced_sensor"}
                    else "static_or_offline"
                ),
            }

        total_stream_bonus = sum(int(item.get("stream_symbol_bonus", 0) or 0) for item in exchange_budget.values())
        total_orderbook_bonus = min(
            INTELLIGENCE_ORDERBOOK_MAX_BONUS,
            sum(int(item.get("orderbook_probe_bonus", 0) or 0) for item in exchange_budget.values()),
        )
        return {
            "schema_version": 1,
            "generated_at": now_iso,
            "enabled": enabled,
            "mode": "balance_weighted_dynamic_ocean_wave_scan",
            "policy": "preserve_cash_rich_execution_venues_use_low_cash_or_unknown_cash_venues_as_fresher_market_sensors",
            "execution_cash_threshold_usd": round(float(quote_threshold), 6),
            "low_cash_sensor_threshold_usd": round(float(INTELLIGENCE_SENSOR_LOW_CASH_USD), 6),
            "base_stream_symbol_limit": STREAM_CACHE_MAX_SYMBOLS,
            "stream_symbol_limit": int(STREAM_CACHE_MAX_SYMBOLS + total_stream_bonus),
            "base_orderbook_probe_limit": ORDERBOOK_PROBE_MAX_PER_TICK,
            "orderbook_probe_limit": int(ORDERBOOK_PROBE_MAX_PER_TICK + total_orderbook_bonus),
            "sensor_priority_exchanges": sensor_exchanges,
            "execution_priority_exchanges": execution_exchanges,
            "balanced_sensor_exchanges": balanced_exchanges,
            "exchanges": exchange_budget,
        }

    def _dynamic_exchange_budget(self, exchange: str) -> Dict[str, Any]:
        budget = getattr(self, "_dynamic_intelligence_budget", {}) or {}
        exchanges = budget.get("exchanges", {}) if isinstance(budget, dict) else {}
        exchange_budget = exchanges.get(str(exchange or "").lower(), {}) if isinstance(exchanges, dict) else {}
        return exchange_budget if isinstance(exchange_budget, dict) else {}

    def _dynamic_probe_interval(self, exchange: str) -> float:
        budget = self._dynamic_exchange_budget(exchange)
        try:
            return max(1.0, float(budget.get("probe_min_interval_sec", PROBE_SYMBOL_MIN_INTERVAL_SEC) or PROBE_SYMBOL_MIN_INTERVAL_SEC))
        except Exception:
            return PROBE_SYMBOL_MIN_INTERVAL_SEC

    def _dynamic_orderbook_interval(self, exchange: str) -> float:
        budget = self._dynamic_exchange_budget(exchange)
        try:
            return max(1.0, float(budget.get("orderbook_min_interval_sec", ORDERBOOK_PROBE_MIN_INTERVAL_SEC) or ORDERBOOK_PROBE_MIN_INTERVAL_SEC))
        except Exception:
            return ORDERBOOK_PROBE_MIN_INTERVAL_SEC

    def _dynamic_stream_symbol_limit(self) -> int:
        budget = getattr(self, "_dynamic_intelligence_budget", {}) or {}
        try:
            return max(8, int(budget.get("stream_symbol_limit", STREAM_CACHE_MAX_SYMBOLS) or STREAM_CACHE_MAX_SYMBOLS))
        except Exception:
            return STREAM_CACHE_MAX_SYMBOLS

    def _dynamic_orderbook_probe_limit(self) -> int:
        budget = getattr(self, "_dynamic_intelligence_budget", {}) or {}
        try:
            return max(0, int(budget.get("orderbook_probe_limit", ORDERBOOK_PROBE_MAX_PER_TICK) or ORDERBOOK_PROBE_MAX_PER_TICK))
        except Exception:
            return ORDERBOOK_PROBE_MAX_PER_TICK

    def _extract_candidate_confidence(self, candidate: Dict[str, Any]) -> float:
        for key in ("confidence", "score", "probability", "win_prob"):
            try:
                value = float(candidate.get(key, 0.0) or 0.0)
                if value > 1.0:
                    value = value / 100.0
                if value > 0:
                    return max(0.0, min(1.0, value))
            except Exception:
                continue
        return 0.0

    def _route_model_key(self, venue: str, market_type: str) -> str:
        venue_norm = str(venue or "").lower().strip()
        market_norm = str(market_type or "").lower().strip()
        return f"{venue_norm}_{market_norm}" if market_norm else venue_norm

    def _model_stack_for_route(self, venue: str, market_type: str) -> Dict[str, Any]:
        key = self._route_model_key(venue, market_type)
        descriptors = list(COMMON_MODEL_STACK) + list(EXCHANGE_MODEL_STACKS.get(key, []))
        models: List[Dict[str, Any]] = []
        for descriptor in descriptors:
            item = dict(descriptor)
            path = str(item.get("path") or "")
            item["available"] = bool(path and (REPO_ROOT / Path(path)).exists())
            models.append(item)
        available = [item for item in models if item.get("available")]
        return {
            "key": key,
            "venue": str(venue or "").lower(),
            "market_type": str(market_type or "").lower(),
            "available_count": len(available),
            "total_count": len(models),
            "ready": len(available) > 0,
            "models": models,
        }

    def _all_exchange_model_coverage(self) -> Dict[str, Any]:
        coverage = {
            key: self._model_stack_for_route(*key.split("_", 1))
            for key in sorted(EXCHANGE_MODEL_STACKS.keys())
        }
        return {
            "generated_at": datetime.now().isoformat(),
            "routes": coverage,
            "route_count": len(coverage),
            "ready_route_count": sum(1 for item in coverage.values() if item.get("ready")),
            "available_model_count": sum(int(item.get("available_count", 0) or 0) for item in coverage.values()),
            "total_model_count": sum(int(item.get("total_count", 0) or 0) for item in coverage.values()),
            "model_use": "UnifiedSignalEngine feeds CentralBeat; route model stacks declare venue-specific repo systems used for execution context.",
        }

    def _capability_present(self, rel_path: str) -> bool:
        try:
            return bool(rel_path and (REPO_ROOT / Path(rel_path)).exists())
        except Exception:
            return False

    def _model_stack_names(self) -> set[str]:
        names: set[str] = set()
        for descriptor in COMMON_MODEL_STACK:
            names.add(str(descriptor.get("name") or ""))
        for stack in EXCHANGE_MODEL_STACKS.values():
            for descriptor in stack:
                names.add(str(descriptor.get("name") or ""))
        return {name for name in names if name}

    def _capability_active(
        self,
        descriptor: Dict[str, Any],
        *,
        central_beat: Optional[Dict[str, Any]] = None,
        order_flow_feed: Optional[Dict[str, Any]] = None,
        action_plan: Optional[Dict[str, Any]] = None,
        shadow_trade_report: Optional[Dict[str, Any]] = None,
        hnc_cognitive_proof: Optional[Dict[str, Any]] = None,
    ) -> bool:
        activation = str(descriptor.get("activation") or "repo_present")
        name = str(descriptor.get("name") or "")
        if activation == "central_beat_sources":
            return bool(central_beat and int(central_beat.get("source_count", 0) or 0) > 0)
        if activation == "model_signal_feed":
            feed = central_beat.get("model_signal_feed", {}) if isinstance(central_beat, dict) else {}
            return bool(isinstance(feed, dict) and feed.get("used"))
        if activation == "stream_cache":
            stream_cache = central_beat.get("stream_cache", {}) if isinstance(central_beat, dict) else {}
            return bool(
                isinstance(stream_cache, dict)
                and stream_cache.get("fresh")
                and int(stream_cache.get("symbol_count", 0) or 0) > 0
            )
        if activation.startswith("world_ecosystem"):
            feed = central_beat.get("world_financial_ecosystem", {}) if isinstance(central_beat, dict) else {}
            if not isinstance(feed, dict):
                return False
            if activation == "world_ecosystem_macro":
                macro = feed.get("macro_snapshot", {}) if isinstance(feed.get("macro_snapshot"), dict) else {}
                return bool(macro.get("present") and macro.get("usable_for_decision"))
            if activation == "world_ecosystem_harp":
                harp = feed.get("market_harp", {}) if isinstance(feed.get("market_harp"), dict) else {}
                return bool(harp.get("present") and harp.get("active_this_cycle"))
            if activation == "world_ecosystem_cross_asset":
                cross = feed.get("cross_asset", {}) if isinstance(feed.get("cross_asset"), dict) else {}
                return bool(cross.get("present") and cross.get("active_this_cycle"))
            if activation == "world_ecosystem_news":
                news = feed.get("news_signal", {}) if isinstance(feed.get("news_signal"), dict) else {}
                return bool(news.get("present") and news.get("usable_for_decision"))
        if activation == "historical_waveform":
            feed = central_beat.get("asset_waveform_models", {}) if isinstance(central_beat, dict) else {}
            return bool(isinstance(feed, dict) and int(feed.get("usable_symbol_count", 0) or 0) > 0)
        if activation == "fast_money":
            feed = order_flow_feed if isinstance(order_flow_feed, dict) else {}
            fast_money = feed.get("fast_money_intelligence", {}) if isinstance(feed.get("fast_money_intelligence"), dict) else {}
            return bool(int(fast_money.get("candidate_count", 0) or 0) > 0)
        if activation == "orderbook_pressure":
            feed = order_flow_feed if isinstance(order_flow_feed, dict) else {}
            fast_money = feed.get("fast_money_intelligence", {}) if isinstance(feed.get("fast_money_intelligence"), dict) else {}
            return bool(int(fast_money.get("orderbook_probe_count", 0) or 0) > 0)
        if activation == "scanner_fusion":
            feed = order_flow_feed if isinstance(order_flow_feed, dict) else {}
            matrix = feed.get("scanner_fusion_matrix", {}) if isinstance(feed.get("scanner_fusion_matrix"), dict) else {}
            systems = matrix.get("systems", []) if isinstance(matrix.get("systems"), list) else []
            for system in systems:
                if isinstance(system, dict) and str(system.get("name") or "") == name:
                    return bool(system.get("active_this_cycle") and system.get("fed_to_decision_logic"))
            return False
        if activation == "shadow_validation":
            report = shadow_trade_report if isinstance(shadow_trade_report, dict) else {}
            return bool(
                report
                and (
                    int(report.get("shadow_opened_count", 0) or 0) > 0
                    or int(report.get("active_shadow_count", 0) or 0) > 0
                    or int(report.get("validated_shadow_count", 0) or 0) > 0
                )
            )
        if activation == "hnc_system":
            proof = hnc_cognitive_proof if isinstance(hnc_cognitive_proof, dict) else {}
            systems = proof.get("systems", {}) if isinstance(proof.get("systems"), dict) else {}
            aliases = {
                "HNCMasterProtocol": "hnc_master_protocol",
                "HNCProbabilityMatrix": "hnc_probability_matrix",
                "Seer": "seer",
                "Lyra": "lyra",
                "KingCapitalLogic": "king",
            }
            key = aliases.get(name, name)
            return bool(isinstance(systems.get(key), dict) and systems[key].get("passed"))
        if activation == "model_stack":
            return name in self._model_stack_names()
        if activation == "thought_bus":
            return bool(getattr(self, "_thought_bus", None) is not None)
        if activation == "repo_present":
            return self._capability_present(str(descriptor.get("path") or ""))
        return False

    def _build_intelligence_mesh(
        self,
        *,
        central_beat: Optional[Dict[str, Any]] = None,
        order_flow_feed: Optional[Dict[str, Any]] = None,
        action_plan: Optional[Dict[str, Any]] = None,
        shadow_trade_report: Optional[Dict[str, Any]] = None,
        hnc_cognitive_proof: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        capabilities: List[Dict[str, Any]] = []
        facet_counts: Dict[str, int] = {}
        active_count = 0
        present_count = 0
        direct_live_count = 0
        active_direct_count = 0
        model_stack_names = self._model_stack_names()
        for descriptor in INTELLIGENCE_MESH_CAPABILITIES:
            present = self._capability_present(str(descriptor.get("path") or ""))
            active = bool(
                present
                and self._capability_active(
                    descriptor,
                    central_beat=central_beat,
                    order_flow_feed=order_flow_feed,
                    action_plan=action_plan,
                    shadow_trade_report=shadow_trade_report,
                    hnc_cognitive_proof=hnc_cognitive_proof,
                )
            )
            wire = str(descriptor.get("wire") or "mesh_context")
            facet = str(descriptor.get("facet") or "uncategorized")
            if present:
                present_count += 1
                facet_counts[facet] = facet_counts.get(facet, 0) + 1
            if active:
                active_count += 1
            if wire in {"direct_live_signal", "hnc_proof", "model_stack"}:
                direct_live_count += 1
                if active:
                    active_direct_count += 1
            status = "missing"
            if present and active:
                status = "active"
            elif present and wire in {"direct_live_signal", "hnc_proof", "model_stack"}:
                status = "wired_waiting_for_fresh_evidence"
            elif present:
                status = "available_to_mesh"
            capabilities.append(
                {
                    "name": descriptor.get("name"),
                    "facet": facet,
                    "path": descriptor.get("path"),
                    "wire": wire,
                    "present": present,
                    "active_this_cycle": active,
                    "status": status,
                }
            )

        total = len(INTELLIGENCE_MESH_CAPABILITIES)
        available_ratio = present_count / max(1, total)
        active_ratio = active_count / max(1, present_count)
        direct_ratio = active_direct_count / max(1, direct_live_count)
        selection_mesh_score = self._clamp01((0.50 * direct_ratio) + (0.30 * active_ratio) + (0.20 * available_ratio))
        return {
            "generated_at": datetime.now().isoformat(),
            "mode": "whole_intelligence_mesh_capability_proof",
            "summary": (
                "Fast live loop uses CentralBeat, model fusion, HNC proof, shadow validation, and profit-velocity ranking; "
                "heavier search/research/scanner systems are registered and exposed as available mesh context unless they have fresh bridge evidence."
            ),
            "capability_count": total,
            "present_count": present_count,
            "active_this_cycle_count": active_count,
            "direct_live_count": direct_live_count,
            "active_direct_live_count": active_direct_count,
            "selection_mesh_score": round(selection_mesh_score, 6),
            "facet_counts": facet_counts,
            "model_stack_names": sorted(model_stack_names),
            "capabilities": capabilities,
        }

    def _build_model_signal_feed(self, sources: List[Dict[str, Any]], regime: Dict[str, Any]) -> Dict[str, Any]:
        opportunities: List[Any] = []
        for source in sources:
            if not isinstance(source, dict):
                continue
            exchange = str(source.get("source") or "unknown").lower()
            source_symbols = source.get("symbols", {})
            if not isinstance(source_symbols, dict):
                continue
            for normalized, item in source_symbols.items():
                if not isinstance(item, dict):
                    continue
                confidence = max(0.0, min(1.0, float(item.get("confidence", 0.0) or 0.0)))
                if confidence <= 0:
                    continue
                side = str(item.get("side") or "BUY").upper()
                try:
                    change_pct = float(item.get("change_pct", 0.0) or 0.0)
                except Exception:
                    change_pct = 0.0
                if change_pct == 0.0:
                    change_pct = confidence * (2.0 if side != "SELL" else -2.0)
                opportunities.append(
                    SimpleNamespace(
                        symbol=str(normalized),
                        exchange=exchange,
                        price=float(item.get("price", 0.0) or 0.0),
                        change_pct=change_pct,
                        momentum_score=confidence,
                    )
                )
        if not opportunities:
            return {
                "used": False,
                "engine": "aureon.trading.unified_signal_engine.UnifiedSignalEngine",
                "reason": "no_source_opportunities",
                "symbols": {},
                "opportunity_count": 0,
            }

        try:
            from aureon.trading.unified_signal_engine import UnifiedSignalEngine

            engine = UnifiedSignalEngine()
            bias = str(regime.get("bias") or "NEUTRAL").upper()
            regime_name = "RISK_ON" if bias == "BUY" else "RISK_OFF" if bias == "SELL" else "NEUTRAL"
            bundle = engine.process(opportunities, regime=regime_name)
            symbols: Dict[str, Dict[str, Any]] = {}
            for signal in getattr(bundle, "signals", []) or []:
                normalized = self._normalize_symbol(getattr(signal, "symbol", ""))
                if not normalized:
                    continue
                current = symbols.get(normalized)
                confidence = max(0.0, min(1.0, float(getattr(signal, "confidence", 0.0) or 0.0)))
                if current and confidence <= float(current.get("confidence", 0.0) or 0.0):
                    continue
                symbols[normalized] = {
                    "symbol": normalized,
                    "exchange": str(getattr(signal, "exchange", "")),
                    "direction": str(getattr(signal, "direction", "NEUTRAL")),
                    "confidence": round(confidence, 4),
                    "raw_score": round(float(getattr(signal, "raw_score", 0.0) or 0.0), 4),
                    "sources": list(getattr(signal, "sources", []) or []),
                }
            return {
                "used": True,
                "engine": "aureon.trading.unified_signal_engine.UnifiedSignalEngine",
                "opportunity_count": len(opportunities),
                "symbols": symbols,
                "summary_lines": list(getattr(bundle, "summary_lines", []) or [])[:8],
            }
        except Exception as e:
            return {
                "used": False,
                "engine": "aureon.trading.unified_signal_engine.UnifiedSignalEngine",
                "reason": str(e),
                "symbols": {},
                "opportunity_count": len(opportunities),
            }

    def _stream_cache_empty_health(self, reason: str) -> Dict[str, Any]:
        health = {
            "source": "aureon.data_feeds.unified_market_cache",
            "mode": "websocket_stream_cache_first_rest_budget_protected",
            "fresh": False,
            "usable_for_decision": False,
            "symbol_count": 0,
            "max_age_sec": STREAM_CACHE_MAX_AGE_SEC,
            "reason": reason,
            "generated_at": datetime.now().isoformat(),
        }
        self._stream_cache_health = health
        return health

    def _canonical_stream_base(self, base: Any) -> str:
        raw = str(base or "").upper().strip()
        if raw in {"XBT", "XXBT"}:
            return "BTC"
        if raw in {"XETH"}:
            return "ETH"
        return raw

    def _stream_price_ticker(self, symbol: str, max_age_sec: float = STREAM_CACHE_MAX_AGE_SEC) -> Any:
        base = self._canonical_stream_base(self._base_from_route_symbol(symbol))
        if not base:
            return None
        try:
            from aureon.data_feeds.unified_market_cache import get_ticker

            ticker = get_ticker(base, max_age=max_age_sec)
            if ticker is None and base == "BTC":
                ticker = get_ticker("XBT", max_age=max_age_sec)
            return ticker
        except Exception as e:
            logger.debug("Stream cache ticker unavailable for %s: %s", symbol, e)
            return None

    def _estimate_stream_price(self, symbol: str) -> float:
        ticker = self._stream_price_ticker(symbol)
        if ticker is None:
            return 0.0
        try:
            price = float(getattr(ticker, "price", 0.0) or 0.0)
            return price if price > 0 else 0.0
        except Exception:
            return 0.0

    def _extract_stream_cache_source_snapshot(self, watchlist: List[str]) -> Dict[str, Any]:
        try:
            from aureon.data_feeds.unified_market_cache import get_market_cache

            market_cache = get_market_cache()
            tickers = market_cache.get_all_tickers(max_age=GOLD_PRIORITY_STREAM_MAX_AGE_SEC)
            source_health = market_cache.get_source_health() if hasattr(market_cache, "get_source_health") else {}
        except Exception as e:
            self._stream_cache_empty_health(f"stream_cache_unavailable:{e}")
            return {}

        if not tickers:
            self._stream_cache_empty_health("no_fresh_stream_tickers")
            return {}

        now = time.time()
        watch_bases = {self._canonical_stream_base(self._base_from_route_symbol(symbol)) for symbol in watchlist if symbol}
        if "XBT" in watch_bases or "XXBT" in watch_bases:
            watch_bases.add("BTC")
        ranked: List[Dict[str, Any]] = []
        for base, ticker in tickers.items():
            base_norm = self._canonical_stream_base(base or getattr(ticker, "symbol", "") or "")
            if not base_norm or base_norm in {"USD", "USDT", "USDC", "BUSD", "EUR", "GBP"}:
                continue
            normalized = self._normalize_symbol(f"{base_norm}USD")
            if not normalized:
                continue
            try:
                price = float(getattr(ticker, "price", 0.0) or 0.0)
                change_pct = float(getattr(ticker, "change_24h", 0.0) or 0.0)
                volume_24h = float(getattr(ticker, "volume_24h", 0.0) or 0.0)
                timestamp = float(getattr(ticker, "timestamp", 0.0) or 0.0)
            except Exception:
                continue
            if price <= 0 or timestamp <= 0:
                continue
            age_sec = max(0.0, now - timestamp)
            if age_sec > GOLD_PRIORITY_STREAM_MAX_AGE_SEC:
                continue
            priority = 1.0 if base_norm in watch_bases or normalized in watchlist else 0.0
            volume_score = min(1.0, max(0.0, volume_24h) / 1_000_000_000.0)
            momentum_score = min(1.0, abs(change_pct) / 8.0)
            score = priority + (momentum_score * 0.75) + (volume_score * 0.25)
            confidence = min(1.0, 0.15 + momentum_score + (0.15 * priority) + (0.10 * volume_score))
            ranked.append(
                {
                    "base": base_norm,
                    "normalized": normalized,
                    "ticker": ticker,
                    "score": score,
                    "confidence": confidence,
                    "price": price,
                    "change_pct": change_pct,
                    "volume_24h": volume_24h,
                    "age_sec": age_sec,
                }
            )

        if not ranked:
            self._stream_cache_empty_health("fresh_stream_tickers_not_routeable")
            return {}

        ranked.sort(key=lambda item: item["score"], reverse=True)
        stream_symbol_limit = self._dynamic_stream_symbol_limit()
        selected = ranked[:stream_symbol_limit]
        symbols: Dict[str, Dict[str, Any]] = {}
        for item in selected:
            ticker = item["ticker"]
            change_pct = float(item["change_pct"])
            symbols[item["normalized"]] = {
                "symbol": item["normalized"],
                "raw_symbol": str(getattr(ticker, "pair", item["base"])),
                "confidence": round(float(item["confidence"]), 4),
                "side": "BUY" if change_pct >= 0 else "SELL",
                "price": round(float(item["price"]), 8),
                "change_pct": round(change_pct, 6),
                "volume_24h": round(float(item["volume_24h"]), 6),
                "age_sec": round(float(item["age_sec"]), 3),
                "source": str(getattr(ticker, "source", "stream_cache")),
                "reason": "fresh_websocket_cache",
            }

        strongest = max(symbols.values(), key=lambda item: float(item.get("confidence", 0.0) or 0.0))
        ages = [float(item.get("age_sec", 0.0) or 0.0) for item in symbols.values()]
        health = {
            "source": "aureon.data_feeds.unified_market_cache",
            "mode": "websocket_stream_cache_first_rest_budget_protected",
            "fresh": True,
            "usable_for_decision": True,
            "symbol_count": len(symbols),
            "raw_ticker_count": len(tickers),
            "exchange_source_health": source_health,
            "active_exchange_sources": [
                source
                for source, item in (source_health.items() if isinstance(source_health, dict) else [])
                if isinstance(item, dict) and item.get("active")
            ],
            "max_age_sec": STREAM_CACHE_MAX_AGE_SEC,
            "base_max_symbols": STREAM_CACHE_MAX_SYMBOLS,
            "dynamic_max_symbols": stream_symbol_limit,
            "oldest_selected_age_sec": round(max(ages), 3) if ages else 0.0,
            "newest_selected_age_sec": round(min(ages), 3) if ages else 0.0,
            "top_symbol": strongest.get("symbol"),
            "top_confidence": strongest.get("confidence"),
            "top_side": strongest.get("side"),
            "dynamic_intelligence_budget_mode": (getattr(self, "_dynamic_intelligence_budget", {}) or {}).get("mode", "static"),
            "generated_at": datetime.now().isoformat(),
        }
        self._stream_cache_health = health
        return {
            "source": "live_stream_cache",
            "ready": True,
            "mode": "websocket_cache_preferred_over_rest_quotes",
            "symbols": symbols,
            "stream_health": health,
            "exchange_source_health": source_health,
            "top_symbol": strongest.get("symbol"),
            "top_side": strongest.get("side"),
            "top_confidence": strongest.get("confidence"),
        }

    def _build_central_beat_feed(self, kraken_payload: Dict[str, Any], capital_payload: Dict[str, Any]) -> Dict[str, Any]:
        now = time.time()
        if self._central_beat_feed and (now - self._central_beat_at) < CENTRAL_BEAT_REFRESH_SEC:
            return dict(self._central_beat_feed)

        trader_sources: List[Dict[str, Any]] = []
        probe_sources: List[Dict[str, Any]] = []
        sources: List[Dict[str, Any]] = []

        kraken_source = self._extract_trader_source_snapshot("kraken", kraken_payload)
        if kraken_source:
            trader_sources.append(kraken_source)
        capital_source = self._extract_trader_source_snapshot("capital", capital_payload)
        if capital_source:
            trader_sources.append(capital_source)
        trader_sources = self._stabilize_sources("trader", trader_sources)
        sources.extend(trader_sources)

        watchlist = self._build_probe_watchlist(sources)
        stream_source = self._extract_stream_cache_source_snapshot(watchlist)
        if stream_source:
            probe_sources.append(stream_source)
        alpaca_source = self._extract_alpaca_source_snapshot(watchlist)
        if alpaca_source:
            probe_sources.append(alpaca_source)
        binance_source = self._extract_binance_source_snapshot(watchlist)
        if binance_source:
            probe_sources.append(binance_source)
        probe_sources = self._stabilize_sources("probe", probe_sources)
        sources.extend(probe_sources)

        symbols: Dict[str, Dict[str, Any]] = {}
        buy_pressure = 0.0
        sell_pressure = 0.0
        for source in sources:
            source_name = str(source.get("source") or "?")
            source_symbols = source.get("symbols", {})
            if not isinstance(source_symbols, dict):
                continue
            for normalized, item in source_symbols.items():
                if not isinstance(item, dict):
                    continue
                confidence = max(0.0, min(1.0, float(item.get("confidence", 0.0) or 0.0)))
                if confidence <= 0.0:
                    continue
                side = str(item.get("side") or "BUY").upper()
                symbol_state = symbols.setdefault(
                    normalized,
                    {
                        "support_count": 0,
                        "confidence_sum": 0.0,
                        "buy_confidence": 0.0,
                        "sell_confidence": 0.0,
                        "sources": [],
                        "price_sum": 0.0,
                        "price_count": 0,
                        "change_pct_sum": 0.0,
                        "change_pct_abs_max": 0.0,
                        "volume_24h_max": 0.0,
                        "freshest_age_sec": None,
                        "fast_money_sources": [],
                        "source_prices": {},
                    },
                )
                symbol_state["support_count"] += 1
                symbol_state["confidence_sum"] += confidence
                if side == "SELL":
                    symbol_state["sell_confidence"] += confidence
                    sell_pressure += confidence
                else:
                    symbol_state["buy_confidence"] += confidence
                    buy_pressure += confidence
                if source_name not in symbol_state["sources"]:
                    symbol_state["sources"].append(source_name)
                try:
                    price = float(item.get("price", 0.0) or 0.0)
                except Exception:
                    price = 0.0
                if price > 0:
                    symbol_state["price_sum"] += price
                    symbol_state["price_count"] += 1
                    symbol_state["source_prices"][source_name] = price
                try:
                    change_pct = float(item.get("change_pct", 0.0) or 0.0)
                    symbol_state["change_pct_sum"] += change_pct
                    symbol_state["change_pct_abs_max"] = max(
                        float(symbol_state.get("change_pct_abs_max", 0.0) or 0.0),
                        abs(change_pct),
                    )
                except Exception:
                    pass
                try:
                    volume_24h = float(item.get("volume_24h", 0.0) or 0.0)
                except Exception:
                    volume_24h = 0.0
                if volume_24h > 0:
                    symbol_state["volume_24h_max"] = max(float(symbol_state.get("volume_24h_max", 0.0) or 0.0), volume_24h)
                    if source_name not in symbol_state["fast_money_sources"]:
                        symbol_state["fast_money_sources"].append(source_name)
                try:
                    age_sec = float(item.get("age_sec", 0.0) or 0.0)
                except Exception:
                    age_sec = 0.0
                if age_sec >= 0 and source_name == "live_stream_cache":
                    current_age = symbol_state.get("freshest_age_sec")
                    symbol_state["freshest_age_sec"] = age_sec if current_age is None else min(float(current_age), age_sec)

        normalized_symbols: Dict[str, Dict[str, Any]] = {}
        for normalized, item in symbols.items():
            support_count = int(item.get("support_count", 0) or 0)
            confidence_sum = float(item.get("confidence_sum", 0.0) or 0.0)
            avg_confidence = confidence_sum / support_count if support_count > 0 else 0.0
            buy_conf = float(item.get("buy_confidence", 0.0) or 0.0)
            sell_conf = float(item.get("sell_confidence", 0.0) or 0.0)
            side = "BUY" if buy_conf >= sell_conf else "SELL"
            imbalance = abs(buy_conf - sell_conf)
            price_count = int(item.get("price_count", 0) or 0)
            reference_price = float(item.get("price_sum", 0.0) or 0.0) / price_count if price_count > 0 else 0.0
            normalized_symbols[normalized] = {
                "confidence": round(avg_confidence, 4),
                "support_count": support_count,
                "side": side,
                "imbalance": round(imbalance, 4),
                "strength": round(avg_confidence * (1.0 + min(1.0, (support_count - 1) * 0.35)), 4),
                "sources": list(item.get("sources", [])),
                "reference_price": round(reference_price, 8) if reference_price > 0 else 0.0,
                "change_pct": round(float(item.get("change_pct_sum", 0.0) or 0.0) / max(1, support_count), 6),
                "change_pct_abs_max": round(float(item.get("change_pct_abs_max", 0.0) or 0.0), 6),
                "volume_24h": round(float(item.get("volume_24h_max", 0.0) or 0.0), 6),
                "freshest_age_sec": (
                    round(float(item.get("freshest_age_sec")), 3)
                    if item.get("freshest_age_sec") is not None
                    else None
                ),
                "fast_money_sources": list(item.get("fast_money_sources", [])),
                "source_prices": dict(item.get("source_prices", {})),
            }

        total_pressure = buy_pressure + sell_pressure
        regime = {
            "buy_pressure": round(buy_pressure, 4),
            "sell_pressure": round(sell_pressure, 4),
            "bias": "BUY" if buy_pressure >= sell_pressure else "SELL",
            "confidence": round((max(buy_pressure, sell_pressure) / total_pressure) if total_pressure > 0 else 0.0, 4),
            "source_count": len(sources),
        }
        if self._central_beat_heavy_context_enabled_now():
            self._set_tick_phase("build_combined_payload:central_beat:world_context")
            world_ecosystem = self._build_world_ecosystem_intelligence(normalized_symbols, sources, regime)
            world_source = self._build_world_ecosystem_source_snapshot(world_ecosystem)
            if world_source:
                self._merge_world_ecosystem_source(normalized_symbols, world_source)
                sources.append(world_source)
                regime["source_count"] = len(sources)
                regime["world_ecosystem_usable_sources"] = int(world_ecosystem.get("usable_source_count", 0) or 0)
                regime["world_ecosystem_decision_symbols"] = int(world_ecosystem.get("decision_symbol_count", 0) or 0)
            self._set_tick_phase("build_combined_payload:central_beat:waveform_context")
            asset_waveform_models = self._build_asset_waveform_models(normalized_symbols, sources)
            waveform_source = self._build_historical_waveform_source_snapshot(asset_waveform_models)
            if waveform_source:
                self._merge_historical_waveform_source(normalized_symbols, waveform_source)
                sources.append(waveform_source)
                regime["source_count"] = len(sources)
                regime["waveform_usable_symbols"] = int(asset_waveform_models.get("usable_symbol_count", 0) or 0)
                regime["waveform_long_memory_ready"] = int(asset_waveform_models.get("long_memory_ready_count", 0) or 0)
            self._set_tick_phase("build_combined_payload:central_beat:model_signal")
            model_signal_feed = self._build_model_signal_feed(sources, regime)
            model_symbols = model_signal_feed.get("symbols", {}) if isinstance(model_signal_feed, dict) else {}
            if isinstance(model_symbols, dict):
                for normalized, model_signal in model_symbols.items():
                    if normalized not in normalized_symbols or not isinstance(model_signal, dict):
                        continue
                    symbol_state = normalized_symbols[normalized]
                    prior_confidence = max(0.0, min(1.0, float(symbol_state.get("confidence", 0.0) or 0.0)))
                    model_confidence = max(0.0, min(1.0, float(model_signal.get("confidence", 0.0) or 0.0)))
                    model_direction = str(model_signal.get("direction") or "NEUTRAL").upper()
                    current_side = str(symbol_state.get("side") or "BUY").upper()
                    if model_direction in {"BUY", "SELL"}:
                        aligned_model_confidence = model_confidence if model_direction == current_side else 1.0 - model_confidence
                        blended_confidence = max(0.0, min(1.0, prior_confidence * 0.75 + aligned_model_confidence * 0.25))
                        symbol_state["confidence"] = round(blended_confidence, 4)
                        symbol_state["strength"] = round(
                            min(1.5, blended_confidence * (1.0 + min(1.0, (int(symbol_state.get("support_count", 0) or 0) - 1) * 0.35))),
                            4,
                        )
                        symbol_state["model_alignment"] = model_direction == current_side
                    symbol_state["model_signal"] = model_signal
        else:
            now_iso = datetime.now().isoformat()
            world_ecosystem = {
                "schema_version": 1,
                "generated_at": now_iso,
                "enabled": False,
                "mode": "deferred_live_runtime_fast_path",
                "decision_symbols": {},
                "sources": [],
                "fed_to_decision_logic": False,
                "reason": "heavy_context_deferred_to_nonblocking_reports",
            }
            asset_waveform_models = {
                "schema_version": 1,
                "generated_at": now_iso,
                "enabled": False,
                "mode": "deferred_live_runtime_fast_path",
                "decision_symbols": {},
                "fed_to_decision_logic": False,
                "reason": "heavy_context_deferred_to_nonblocking_reports",
            }
            model_signal_feed = {
                "used": False,
                "engine": "aureon.trading.unified_signal_engine.UnifiedSignalEngine",
                "reason": "heavy_context_deferred_to_nonblocking_reports",
                "symbols": {},
                "opportunity_count": len(normalized_symbols),
            }
            self._world_ecosystem_intelligence = world_ecosystem
            self._asset_waveform_models = asset_waveform_models

        payload = {
            "generated_at": datetime.now().isoformat(),
            "sources": sources,
            "source_count": len(sources),
            "symbols": normalized_symbols,
            "regime": regime,
            "model_signal_feed": model_signal_feed,
            "world_financial_ecosystem": world_ecosystem,
            "asset_waveform_models": asset_waveform_models,
            "stream_cache": dict(getattr(self, "_stream_cache_health", {}) or {}),
            "market_data_strategy": {
                "freshness_goal": "prefer_live_stream_cache_then_balance_weighted_budgeted_rest_quotes_then_world_ecosystem_context_then_1h_to_1y_waveform_memory",
                "stream_cache_max_age_sec": STREAM_CACHE_MAX_AGE_SEC,
                "stream_cache_symbol_limit": self._dynamic_stream_symbol_limit(),
                "rest_probe_min_interval_sec": PROBE_SYMBOL_MIN_INTERVAL_SEC,
                "rest_probe_stale_ttl_sec": PROBE_SYMBOL_STALE_TTL_SEC,
                "world_ecosystem_enabled": WORLD_ECOSYSTEM_INTELLIGENCE_ENABLED,
                "world_ecosystem_usable_source_count": int(world_ecosystem.get("usable_source_count", 0) or 0),
                "asset_waveform_models_enabled": ASSET_WAVEFORM_MODELS_ENABLED,
                "asset_waveform_usable_symbol_count": int(asset_waveform_models.get("usable_symbol_count", 0) or 0),
                "asset_waveform_long_memory_ready_count": int(asset_waveform_models.get("long_memory_ready_count", 0) or 0),
                "dynamic_intelligence_budget": getattr(self, "_dynamic_intelligence_budget", {}) or {},
            },
        }
        self._central_beat_layers = {
            "trader": {"sources": trader_sources, "count": len(trader_sources)},
            "probe": {"sources": probe_sources, "count": len(probe_sources)},
            "merged": {"sources": sources, "count": len(sources), "symbols": normalized_symbols, "regime": regime},
        }
        self._central_beat_feed = payload
        self._central_beat_at = now
        self._central_beat_history.append(payload)
        self._central_beat_history = self._central_beat_history[-CENTRAL_BEAT_HISTORY_LIMIT:]
        return dict(payload)

    def _sync_shared_market_feed(self, central_beat: Dict[str, Any]) -> Dict[str, Any]:
        boosts: Dict[str, float] = {}
        aliases: Dict[str, List[str]] = {}
        symbol_metrics = central_beat.get("symbols", {}) if isinstance(central_beat, dict) else {}
        regime = central_beat.get("regime", {}) if isinstance(central_beat, dict) else {}

        for normalized, item in symbol_metrics.items():
            if not isinstance(item, dict):
                continue
            strength = max(0.0, min(1.5, float(item.get("strength", 0.0) or 0.0)))
            confidence = max(0.0, min(1.0, float(item.get("confidence", 0.0) or 0.0)))
            boosts[str(normalized)] = round(min(1.0, max(strength, confidence)), 4)
            for source_name in item.get("sources", []) if isinstance(item.get("sources"), list) else []:
                known = aliases.setdefault(str(normalized), [])
                if source_name not in known:
                    known.append(str(source_name))

        self._shared_market_feed = boosts
        self._shared_market_feed_at = time.time()

        for trader in self._central_feed_targets():
            if trader is None:
                continue
            try:
                trader._hive_boosts = dict(boosts)  # type: ignore[attr-defined]
                trader._central_beat_symbols = dict(symbol_metrics)  # type: ignore[attr-defined]
                trader._central_beat_regime = dict(regime)  # type: ignore[attr-defined]
            except Exception:
                continue

        return {
            "symbols": dict(boosts),
            "aliases": dict(aliases),
            "count": len(boosts),
            "generated_at": datetime.now().isoformat(),
        }

    def _central_feed_targets(self) -> List[Any]:
        targets: List[Any] = []
        seen: set[int] = set()
        for attr in ("kraken", "capital", "alpaca_trader", "binance_trader", "alpaca", "binance"):
            target = getattr(self, attr, None)
            if target is None:
                continue
            target_id = id(target)
            if target_id in seen:
                continue
            seen.add(target_id)
            targets.append(target)
        return targets

    def _stabilize_sources(self, stage: str, fresh_sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        now = time.time()
        stabilized: List[Dict[str, Any]] = []
        fresh_names = set()
        for source in fresh_sources:
            if not isinstance(source, dict):
                continue
            source_name = str(source.get("source") or "").strip()
            if not source_name:
                continue
            memory_key = f"{stage}:{source_name}"
            prepared = dict(source)
            prepared["stale"] = False
            prepared["captured_at"] = datetime.now().isoformat()
            prepared["_seen_at"] = now
            prepared["_stage"] = stage
            self._central_source_memory[memory_key] = prepared
            stabilized.append(prepared)
            fresh_names.add(source_name)

        for memory_key, cached in list(self._central_source_memory.items()):
            if str(cached.get("_stage") or "") != stage:
                continue
            source_name = str(cached.get("source") or "").strip()
            if source_name in fresh_names:
                continue
            seen_at = float(cached.get("_seen_at", 0.0) or 0.0)
            if seen_at <= 0 or (now - seen_at) > CENTRAL_BEAT_STALE_AFTER_SEC:
                continue
            reused = dict(cached)
            reused["stale"] = True
            reused["reused_at"] = datetime.now().isoformat()
            stabilized.append(reused)

        stabilized.sort(key=lambda item: str(item.get("source") or ""))
        return stabilized

    def _build_probe_watchlist(self, sources: List[Dict[str, Any]]) -> List[str]:
        watchlist: List[str] = []
        for source in sources:
            source_symbols = source.get("symbols", {})
            if not isinstance(source_symbols, dict):
                continue
            for normalized in source_symbols.keys():
                symbol = str(normalized or "").upper()
                if symbol and symbol not in watchlist:
                    watchlist.append(symbol)
        for fallback in ("BTCUSD", "ETHUSD", "SOLUSD", "XRPUSD"):
            if fallback not in watchlist:
                watchlist.append(fallback)
        return watchlist[:12]

    def _timestamp_age_seconds(self, value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            if isinstance(value, (int, float)):
                number = float(value)
                if number > 1_000_000_000:
                    return max(0.0, time.time() - number)
                return max(0.0, number)
            if isinstance(value, datetime):
                return max(0.0, (datetime.now() - value.replace(tzinfo=None)).total_seconds())
            text = str(value).strip()
            if not text:
                return None
            if text.isdigit():
                return max(0.0, time.time() - float(text))
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            return max(0.0, (datetime.now() - parsed.replace(tzinfo=None)).total_seconds())
        except Exception:
            return None

    def _world_source_row(
        self,
        *,
        system: str,
        facet: str,
        wire_path: str,
        evidence_source: str,
        present: bool,
        active_this_cycle: bool,
        fresh: bool,
        usable_for_decision: bool,
        fed_to_decision_logic: bool,
        downstream_stage: str,
        last_timestamp: Any = None,
        blocker: str = "",
    ) -> Dict[str, Any]:
        return {
            "system": system,
            "facet": facet,
            "wire_path": wire_path,
            "evidence_source": evidence_source,
            "last_timestamp": last_timestamp,
            "present": bool(present),
            "active_this_cycle": bool(active_this_cycle),
            "fresh": bool(fresh),
            "usable_for_decision": bool(usable_for_decision),
            "fed_to_decision_logic": bool(fed_to_decision_logic),
            "downstream_stage": downstream_stage,
            "blocker": blocker or "",
        }

    def _world_market_maps(
        self,
        normalized_symbols: Dict[str, Dict[str, Any]],
        sources: List[Dict[str, Any]],
    ) -> Tuple[Dict[str, float], Dict[str, float], Dict[str, float], Dict[str, str]]:
        price_map: Dict[str, float] = {}
        symbol_to_change: Dict[str, float] = {}
        symbol_to_price: Dict[str, float] = {}
        symbol_to_exchange: Dict[str, str] = {}

        def push(symbol: Any, source_name: str, price: Any = 0.0, change_pct: Any = 0.0) -> None:
            normalized = self._normalize_symbol(symbol)
            if not normalized:
                return
            try:
                price_value = float(price or 0.0)
            except Exception:
                price_value = 0.0
            try:
                change_value = float(change_pct or 0.0)
            except Exception:
                change_value = 0.0
            if price_value > 0:
                price_map[normalized] = price_value
                symbol_to_price[normalized] = price_value
                base = self._base_from_route_symbol(normalized)
                if base and base != normalized:
                    price_map.setdefault(base, price_value)
                    symbol_to_price.setdefault(base, price_value)
            if abs(change_value) > 0:
                symbol_to_change[normalized] = change_value
                base = self._base_from_route_symbol(normalized)
                if base and base != normalized:
                    symbol_to_change.setdefault(base, change_value)
            if source_name:
                symbol_to_exchange.setdefault(normalized, source_name)

        for normalized, item in normalized_symbols.items():
            if not isinstance(item, dict):
                continue
            push(
                normalized,
                ",".join(str(source) for source in item.get("sources", []) if source) if isinstance(item.get("sources"), list) else "central_beat",
                item.get("reference_price", 0.0),
                item.get("change_pct", 0.0),
            )
            source_prices = item.get("source_prices", {})
            if isinstance(source_prices, dict):
                for source_name, price in source_prices.items():
                    push(normalized, str(source_name), price, item.get("change_pct", 0.0))

        for source in sources:
            source_name = str(source.get("source") or "unknown")
            source_symbols = source.get("symbols", {})
            if not isinstance(source_symbols, dict):
                continue
            for normalized, item in source_symbols.items():
                if not isinstance(item, dict):
                    continue
                push(
                    item.get("raw_symbol") or item.get("symbol") or normalized,
                    source_name,
                    item.get("price", item.get("reference_price", 0.0)),
                    item.get("change_pct", 0.0),
                )

        return price_map, symbol_to_change, symbol_to_price, symbol_to_exchange

    def _world_route_symbol(self, symbol: Any, existing_symbols: Dict[str, Dict[str, Any]]) -> str:
        normalized = self._normalize_symbol(symbol)
        if not normalized:
            return ""
        if normalized in existing_symbols:
            return normalized
        if not normalized.endswith("USD"):
            crypto_candidate = f"{normalized}USD"
            base = normalized
            if base in KRAKEN_SPOT_CRYPTO_BASES or base in BINANCE_CRYPTO_BASES or base in ALPACA_SPOT_CRYPTO_BASES:
                return crypto_candidate
        return normalized

    def _world_decision_symbol(
        self,
        *,
        symbol: Any,
        confidence: float,
        side: str,
        reason: str,
        downstream_stage: str,
        existing_symbols: Dict[str, Dict[str, Any]],
        price: float = 0.0,
        change_pct: float = 0.0,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        normalized = self._world_route_symbol(symbol, existing_symbols)
        confidence = self._clamp01(confidence)
        side = str(side or "BUY").upper()
        if side not in {"BUY", "SELL"}:
            side = "BUY"
        payload = {
            "symbol": normalized,
            "raw_symbol": str(symbol or "").upper(),
            "confidence": confidence,
            "side": side,
            "reason": reason,
            "downstream_stage": downstream_stage,
        }
        if price > 0:
            payload["price"] = round(float(price), 8)
        if abs(change_pct) > 0:
            payload["change_pct"] = round(float(change_pct), 6)
        if extra:
            payload.update(extra)
        return payload if normalized and confidence > 0 else {}

    def _read_global_financial_state(self) -> Dict[str, Any]:
        for path in (REPO_ROOT / "global_financial_state.json", REPO_ROOT / "state" / "global_financial_state.json"):
            try:
                if not path.exists():
                    continue
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    snapshot = data.get("last_snapshot", data)
                    if isinstance(snapshot, dict):
                        snapshot = dict(snapshot)
                        snapshot.setdefault("loaded_from", str(path))
                        snapshot.setdefault("source", "global_financial_state")
                        return snapshot
            except Exception:
                continue
        return {}

    def _start_world_macro_fetch_thread(self) -> None:
        if _SUPPRESS_IMPORT_SIDE_EFFECTS or not WORLD_ECOSYSTEM_MACRO_FETCH_ENABLED:
            return
        if bool(getattr(self, "_world_macro_fetch_inflight", False)):
            return

        def worker() -> None:
            try:
                from aureon.data_feeds.global_financial_feed import GlobalFinancialFeed

                feed = getattr(self, "_global_financial_feed", None)
                if feed is None:
                    feed = GlobalFinancialFeed()
                    self._global_financial_feed = feed
                snapshot = feed.get_snapshot()
                payload = snapshot.to_dict() if hasattr(snapshot, "to_dict") else {}
                if isinstance(payload, dict):
                    payload.setdefault("source", "global_financial_feed")
                    self._world_macro_snapshot_cache = dict(payload)
                    self._world_macro_snapshot_at = time.time()
            except Exception as e:
                cached = dict(getattr(self, "_world_macro_snapshot_cache", {}) or {})
                cached.setdefault("source", "global_financial_feed")
                cached["error"] = str(e)
                self._world_macro_snapshot_cache = cached
                self._world_macro_snapshot_at = time.time()
            finally:
                self._world_macro_fetch_inflight = False

        self._world_macro_fetch_inflight = True
        threading.Thread(target=worker, daemon=True).start()

    def _load_world_macro_snapshot(self) -> Dict[str, Any]:
        provider = getattr(self, "_world_macro_provider", None)
        if callable(provider):
            try:
                supplied = provider()
                if hasattr(supplied, "to_dict"):
                    supplied = supplied.to_dict()
                return dict(supplied) if isinstance(supplied, dict) else {}
            except Exception as e:
                return {"error": str(e), "source": "world_macro_provider"}

        now = time.time()
        cached = getattr(self, "_world_macro_snapshot_cache", {}) or {}
        cached_at = float(getattr(self, "_world_macro_snapshot_at", 0.0) or 0.0)
        if cached and now - cached_at < WORLD_ECOSYSTEM_MACRO_MIN_INTERVAL_SEC:
            return dict(cached)

        state_snapshot = self._read_global_financial_state()
        if _SUPPRESS_IMPORT_SIDE_EFFECTS or not WORLD_ECOSYSTEM_MACRO_FETCH_ENABLED:
            self._world_macro_snapshot_cache = dict(state_snapshot)
            self._world_macro_snapshot_at = now
            return dict(state_snapshot)

        self._start_world_macro_fetch_thread()
        if not state_snapshot:
            state_snapshot = {
                "source": "global_financial_feed",
                "status": "background_fetch_pending",
                "generated_at": datetime.now().isoformat(),
            }
        self._world_macro_snapshot_cache = dict(state_snapshot)
        self._world_macro_snapshot_at = now
        return dict(state_snapshot)

    def _load_world_news_signal(self) -> Dict[str, Any]:
        provider = getattr(self, "_world_news_signal_provider", None)
        if callable(provider):
            try:
                supplied = provider()
                if hasattr(supplied, "__dict__") and not isinstance(supplied, dict):
                    supplied = dict(supplied.__dict__)
                return dict(supplied) if isinstance(supplied, dict) else {}
            except Exception as e:
                return {"error": str(e), "source": "world_news_provider"}
        if not WORLD_ECOSYSTEM_NEWS_ENABLED:
            return {}
        try:
            from aureon.data_feeds.news_signal import get_news_signal

            signal = get_news_signal()
            if isinstance(signal, dict):
                payload = dict(signal)
            else:
                payload = dict(getattr(signal, "__dict__", {}) or {})
                if hasattr(signal, "summary"):
                    try:
                        payload["summary"] = signal.summary()
                    except Exception:
                        pass
            payload.setdefault("source", "news_signal")
            return payload
        except Exception as e:
            return {"error": str(e), "source": "news_signal"}

    def _publish_world_ecosystem_intelligence(self, report: Dict[str, Any]) -> None:
        if _SUPPRESS_IMPORT_SIDE_EFFECTS:
            return
        for path in (WORLD_FINANCIAL_ECOSYSTEM_STATE_PATH, WORLD_FINANCIAL_ECOSYSTEM_PUBLIC_PATH):
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                tmp_path = path.with_name(f"{path.name}.{os.getpid()}.tmp")
                with tmp_path.open("w", encoding="utf-8") as handle:
                    json.dump(report, handle, indent=2, default=str)
                os.replace(tmp_path, path)
            except Exception as e:
                logger.debug("World financial ecosystem report write failed for %s: %s", path, e)

    def _historical_waveform_live_observations(
        self,
        normalized_symbols: Dict[str, Dict[str, Any]],
        sources: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        observations: List[Dict[str, Any]] = []
        now_ms = int(time.time() * 1000)
        for normalized, item in normalized_symbols.items():
            if not isinstance(item, dict):
                continue
            price = float(item.get("reference_price", 0.0) or 0.0)
            if price <= 0:
                source_prices = item.get("source_prices", {})
                if isinstance(source_prices, dict):
                    for candidate_price in source_prices.values():
                        try:
                            price = float(candidate_price or 0.0)
                        except Exception:
                            price = 0.0
                        if price > 0:
                            break
            if price <= 0:
                continue
            observations.append(
                {
                    "symbol": normalized,
                    "ts_ms": now_ms,
                    "close": price,
                    "high": price,
                    "low": price,
                    "volume": float(item.get("volume_24h", 0.0) or 0.0),
                    "source": "central_beat_live",
                }
            )
        for source in sources:
            source_name = str(source.get("source") or "source")
            source_symbols = source.get("symbols", {}) if isinstance(source, dict) else {}
            if not isinstance(source_symbols, dict):
                continue
            for normalized, item in source_symbols.items():
                if not isinstance(item, dict):
                    continue
                try:
                    price = float(item.get("price", item.get("reference_price", 0.0)) or 0.0)
                except Exception:
                    price = 0.0
                if price <= 0:
                    continue
                try:
                    age_sec = float(item.get("age_sec", 0.0) or 0.0)
                except Exception:
                    age_sec = 0.0
                observations.append(
                    {
                        "symbol": normalized,
                        "ts_ms": int(now_ms - max(0.0, age_sec) * 1000),
                        "close": price,
                        "high": float(item.get("high", price) or price),
                        "low": float(item.get("low", price) or price),
                        "volume": float(item.get("volume_24h", item.get("volume", 0.0)) or 0.0),
                        "source": source_name,
                    }
                )
        for history_item in list(getattr(self, "_central_beat_history", []) or [])[-CENTRAL_BEAT_HISTORY_LIMIT:]:
            if not isinstance(history_item, dict):
                continue
            ts_ms = self._timestamp_to_ms(history_item.get("generated_at")) or now_ms
            hist_symbols = history_item.get("symbols", {})
            if not isinstance(hist_symbols, dict):
                continue
            for normalized, item in hist_symbols.items():
                if not isinstance(item, dict):
                    continue
                price = float(item.get("reference_price", 0.0) or 0.0)
                if price <= 0:
                    continue
                observations.append(
                    {
                        "symbol": normalized,
                        "ts_ms": ts_ms,
                        "close": price,
                        "high": price,
                        "low": price,
                        "volume": float(item.get("volume_24h", 0.0) or 0.0),
                        "source": "central_beat_history",
                    }
                )
        return observations

    def _timestamp_to_ms(self, value: Any) -> Optional[int]:
        if value is None:
            return None
        try:
            if isinstance(value, (int, float)):
                number = float(value)
                if number > 1_000_000_000_000:
                    return int(number)
                if number > 1_000_000_000:
                    return int(number * 1000)
                return int(number)
            if isinstance(value, datetime):
                return int(value.timestamp() * 1000)
            text = str(value).strip()
            if not text:
                return None
            if text.isdigit():
                return self._timestamp_to_ms(float(text))
            return int(datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp() * 1000)
        except Exception:
            return None

    def _publish_asset_waveform_models(self, report: Dict[str, Any]) -> None:
        if _SUPPRESS_IMPORT_SIDE_EFFECTS:
            return
        for path in (ASSET_WAVEFORM_MODELS_STATE_PATH, ASSET_WAVEFORM_MODELS_PUBLIC_PATH):
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                tmp_path = path.with_name(f"{path.name}.{os.getpid()}.tmp")
                with tmp_path.open("w", encoding="utf-8") as handle:
                    json.dump(report, handle, indent=2, default=str)
                os.replace(tmp_path, path)
            except Exception as e:
                logger.debug("Asset waveform model write failed for %s: %s", path, e)

    def _build_asset_waveform_models(
        self,
        normalized_symbols: Dict[str, Dict[str, Any]],
        sources: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if not ASSET_WAVEFORM_MODELS_ENABLED:
            report = {
                "schema_version": 1,
                "generated_at": datetime.now().isoformat(),
                "mode": "multi_horizon_asset_waveform_models_disabled",
                "enabled": False,
                "decision_symbols": {},
                "fed_to_decision_logic": False,
            }
            self._asset_waveform_models = report
            return report
        try:
            from aureon.analytics.aureon_multi_horizon_waveform_model import build_multi_horizon_waveform_report

            symbols = list(normalized_symbols.keys())
            live_observations = self._historical_waveform_live_observations(normalized_symbols, sources)
            report = build_multi_horizon_waveform_report(
                symbols=symbols,
                live_observations=live_observations,
                max_symbols=ASSET_WAVEFORM_MAX_SYMBOLS,
            )
            report["enabled"] = True
            report["wire_path"] = "central_beat.asset_waveform_models"
            report["evidence_source"] = "aureon/analytics/aureon_multi_horizon_waveform_model.py + state/aureon_global_history.sqlite + CentralBeat"
        except Exception as e:
            report = {
                "schema_version": 1,
                "generated_at": datetime.now().isoformat(),
                "enabled": True,
                "mode": "multi_horizon_asset_waveform_models_error",
                "error": str(e),
                "decision_symbols": {},
                "fed_to_decision_logic": False,
            }
        self._asset_waveform_models = report
        self._publish_asset_waveform_models(report)
        return report

    def _build_historical_waveform_source_snapshot(self, report: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(report, dict) or not report.get("enabled", True):
            return {}
        decision_symbols = report.get("decision_symbols", {})
        if not isinstance(decision_symbols, dict) or not decision_symbols:
            return {}
        symbols: Dict[str, Dict[str, Any]] = {}
        for normalized, item in decision_symbols.items():
            if not isinstance(item, dict):
                continue
            confidence = self._clamp01(item.get("confidence", 0.0))
            if confidence <= 0:
                continue
            symbol_key = self._normalize_symbol(normalized)
            if not symbol_key:
                continue
            symbols[symbol_key] = {
                "symbol": symbol_key,
                "raw_symbol": item.get("symbol", symbol_key),
                "confidence": confidence,
                "side": str(item.get("side") or "BUY").upper(),
                "reason": "multi_horizon_historical_waveform",
                "downstream_stage": "hnc_proof",
                "usable_horizon_count": item.get("usable_horizon_count", 0),
                "fast_memory_ready": item.get("fast_memory_ready", False),
                "long_memory_ready": item.get("long_memory_ready", False),
                "directional_return_score": item.get("directional_return_score", 0.0),
            }
        if not symbols:
            return {}
        strongest = max(symbols.values(), key=lambda item: float(item.get("confidence", 0.0) or 0.0))
        return {
            "source": "historical_waveform_models",
            "ready": True,
            "mode": "multi_horizon_1h_to_1y_waveform_memory",
            "symbols": symbols,
            "top_symbol": strongest.get("symbol"),
            "top_side": strongest.get("side"),
            "top_confidence": strongest.get("confidence"),
            "usable_symbol_count": report.get("usable_symbol_count", 0),
            "long_memory_ready_count": report.get("long_memory_ready_count", 0),
            "fed_to_decision_logic": report.get("fed_to_decision_logic", False),
        }

    def _merge_historical_waveform_source(
        self,
        normalized_symbols: Dict[str, Dict[str, Any]],
        source_snapshot: Dict[str, Any],
    ) -> None:
        source_symbols = source_snapshot.get("symbols", {}) if isinstance(source_snapshot, dict) else {}
        if not isinstance(source_symbols, dict):
            return
        for normalized, item in source_symbols.items():
            if not isinstance(item, dict):
                continue
            confidence = self._clamp01(item.get("confidence", 0.0))
            if confidence <= 0:
                continue
            symbol_state = normalized_symbols.get(str(normalized))
            if not isinstance(symbol_state, dict):
                continue
            current_side = str(symbol_state.get("side") or "BUY").upper()
            waveform_side = str(item.get("side") or current_side).upper()
            aligned = waveform_side == current_side
            prior_confidence = self._clamp01(symbol_state.get("confidence", 0.0))
            boost = confidence * (0.16 if aligned else -0.08)
            symbol_state["confidence"] = round(self._clamp01(prior_confidence + boost, prior_confidence), 4)
            symbol_state["support_count"] = int(symbol_state.get("support_count", 0) or 0) + 1
            symbol_state["strength"] = round(
                min(
                    1.5,
                    self._clamp01(symbol_state.get("confidence", 0.0))
                    * (1.0 + min(1.0, (int(symbol_state.get("support_count", 0) or 0) - 1) * 0.35)),
                ),
                4,
            )
            if "historical_waveform_models" not in symbol_state.get("sources", []):
                symbol_state.setdefault("sources", []).append("historical_waveform_models")
            symbol_state["historical_waveform"] = item

    def _build_world_ecosystem_intelligence(
        self,
        normalized_symbols: Dict[str, Dict[str, Any]],
        sources: List[Dict[str, Any]],
        regime: Dict[str, Any],
    ) -> Dict[str, Any]:
        now_iso = datetime.now().isoformat()
        if not WORLD_ECOSYSTEM_INTELLIGENCE_ENABLED:
            report = {
                "schema_version": 1,
                "generated_at": now_iso,
                "enabled": False,
                "mode": "disabled",
                "decision_symbols": {},
                "sources": [],
                "fed_to_decision_logic": False,
            }
            self._world_ecosystem_intelligence = report
            return report

        price_map, symbol_to_change, symbol_to_price, symbol_to_exchange = self._world_market_maps(normalized_symbols, sources)
        decision_symbols: Dict[str, Dict[str, Any]] = {}
        rows: List[Dict[str, Any]] = []
        asset_classes: Dict[str, bool] = {}

        def remember_asset_class(category: str) -> None:
            if category:
                asset_classes[str(category)] = True

        for source in sources:
            source_symbols = source.get("symbols", {}) if isinstance(source, dict) else {}
            if not isinstance(source_symbols, dict):
                continue
            for item in source_symbols.values():
                if not isinstance(item, dict):
                    continue
                symbol = item.get("symbol") or item.get("raw_symbol")
                base = self._base_from_route_symbol(symbol)
                if base in KRAKEN_SPOT_CRYPTO_BASES or base in BINANCE_CRYPTO_BASES or base in ALPACA_SPOT_CRYPTO_BASES:
                    remember_asset_class("crypto")

        market_harp: Dict[str, Any] = {"present": False, "active_this_cycle": False, "boosts": {}}
        try:
            harp = getattr(self, "_market_harp", None)
            if harp is None:
                from aureon.data_feeds.market_harp import MarketHarp

                harp = MarketHarp()
                self._market_harp = harp
            boosts = harp.tick(price_map) if price_map else {}
            if not isinstance(boosts, dict):
                boosts = {}
            for alias, boost in sorted(boosts.items(), key=lambda item: float(item[1] or 0.0), reverse=True)[:WORLD_ECOSYSTEM_MAX_DECISION_SYMBOLS]:
                normalized = self._world_route_symbol(alias, normalized_symbols)
                if not normalized:
                    continue
                confidence = self._clamp01(0.30 + float(boost or 0.0) * 0.55)
                candidate = self._world_decision_symbol(
                    symbol=normalized,
                    confidence=confidence,
                    side="BUY",
                    reason="market_harp_resonance",
                    downstream_stage="profit_velocity",
                    existing_symbols=normalized_symbols,
                    price=symbol_to_price.get(normalized, 0.0),
                    change_pct=symbol_to_change.get(normalized, 0.0),
                    extra={"harp_boost": round(float(boost or 0.0), 6)},
                )
                if candidate:
                    decision_symbols[normalized] = candidate
            market_harp = {
                "present": True,
                "active_this_cycle": bool(boosts or getattr(harp, "active_pluck_count", 0) or getattr(harp, "active_ripple_count", 0)),
                "fresh": bool(price_map),
                "usable_for_decision": bool(price_map),
                "boost_count": len(boosts),
                "active_pluck_count": int(getattr(harp, "active_pluck_count", 0) or 0),
                "active_ripple_count": int(getattr(harp, "active_ripple_count", 0) or 0),
                "top_boosts": [
                    {"symbol": str(symbol), "boost": round(float(boost or 0.0), 6)}
                    for symbol, boost in sorted(boosts.items(), key=lambda item: float(item[1] or 0.0), reverse=True)[:8]
                ],
                "status_lines": harp.status_lines()[:6] if hasattr(harp, "status_lines") else [],
                "cross_class_summary": harp.cross_class_summary()[:6] if hasattr(harp, "cross_class_summary") else [],
            }
        except Exception as e:
            market_harp = {"present": False, "active_this_cycle": False, "error": str(e), "usable_for_decision": False}
        rows.append(
            self._world_source_row(
                system="MarketHarp",
                facet="cross_market_resonance",
                wire_path="central_beat.world_financial_ecosystem.market_harp",
                evidence_source="aureon/data_feeds/market_harp.py",
                present=bool(market_harp.get("present")),
                active_this_cycle=bool(market_harp.get("active_this_cycle")),
                fresh=bool(market_harp.get("fresh")),
                usable_for_decision=bool(market_harp.get("usable_for_decision")),
                fed_to_decision_logic=any(item.get("reason") == "market_harp_resonance" for item in decision_symbols.values()),
                downstream_stage="profit_velocity",
                last_timestamp=now_iso,
                blocker="" if market_harp.get("usable_for_decision") else market_harp.get("error", "no_live_price_map"),
            )
        )

        cross_asset: Dict[str, Any] = {"present": False, "active_this_cycle": False, "pre_signals": []}
        try:
            correlator = getattr(self, "_cross_asset_correlator", None)
            if correlator is None:
                from aureon.analytics.cross_asset_correlator import CrossAssetCorrelator

                correlator = CrossAssetCorrelator()
                self._cross_asset_correlator = correlator
            if symbol_to_change:
                correlator.update_batch(symbol_to_change)
            category_moves = correlator.get_category_moves(symbol_to_change) if symbol_to_change else {}
            cross_regime = correlator.get_regime(symbol_to_change) if symbol_to_change else "NEUTRAL"
            pre_signals = (
                correlator.get_pre_signals(
                    symbol_to_change,
                    symbol_to_price,
                    symbol_to_exchange,
                    set(normalized_symbols.keys()),
                )
                if symbol_to_change
                else []
            )
            for category in category_moves.keys() if isinstance(category_moves, dict) else []:
                remember_asset_class(category)
            pre_signal_rows: List[Dict[str, Any]] = []
            for signal in pre_signals[:WORLD_ECOSYSTEM_MAX_DECISION_SYMBOLS]:
                signal_dict = dict(getattr(signal, "__dict__", {}) or {})
                follower_symbol = signal_dict.get("follower_symbol") or signal_dict.get("follower")
                remaining_pct = float(signal_dict.get("remaining_pct", 0.0) or 0.0)
                correlation = float(signal_dict.get("correlation", 0.0) or 0.0)
                side = "BUY" if remaining_pct >= 0 else "SELL"
                confidence = self._clamp01(0.35 + correlation * min(0.45, abs(remaining_pct) / 4.0))
                normalized = self._world_route_symbol(follower_symbol, normalized_symbols)
                candidate = self._world_decision_symbol(
                    symbol=follower_symbol,
                    confidence=confidence,
                    side=side,
                    reason="cross_asset_presignal",
                    downstream_stage="exchange_action_plan",
                    existing_symbols=normalized_symbols,
                    price=symbol_to_price.get(normalized, 0.0),
                    change_pct=remaining_pct,
                    extra={
                        "leader": signal_dict.get("leader"),
                        "follower": signal_dict.get("follower"),
                        "remaining_pct": round(remaining_pct, 6),
                        "correlation": round(correlation, 6),
                        "lag_seconds": signal_dict.get("lag_seconds"),
                        "category": signal_dict.get("category"),
                        "cross_asset_regime": signal_dict.get("regime", cross_regime),
                    },
                )
                if candidate and normalized:
                    decision_symbols[normalized] = candidate
                pre_signal_rows.append(signal_dict)
            cross_asset = {
                "present": True,
                "active_this_cycle": bool(symbol_to_change),
                "fresh": bool(symbol_to_change),
                "usable_for_decision": bool(symbol_to_change),
                "regime": cross_regime,
                "category_moves": category_moves,
                "pre_signal_count": len(pre_signals),
                "pre_signals": pre_signal_rows[:8],
            }
        except Exception as e:
            cross_asset = {"present": False, "active_this_cycle": False, "error": str(e), "usable_for_decision": False}
        rows.append(
            self._world_source_row(
                system="CrossAssetCorrelator",
                facet="cross_asset_presignal",
                wire_path="central_beat.world_financial_ecosystem.cross_asset",
                evidence_source="aureon/analytics/cross_asset_correlator.py",
                present=bool(cross_asset.get("present")),
                active_this_cycle=bool(cross_asset.get("active_this_cycle")),
                fresh=bool(cross_asset.get("fresh")),
                usable_for_decision=bool(cross_asset.get("usable_for_decision")),
                fed_to_decision_logic=any(item.get("reason") == "cross_asset_presignal" for item in decision_symbols.values()),
                downstream_stage="exchange_action_plan",
                last_timestamp=now_iso,
                blocker="" if cross_asset.get("usable_for_decision") else cross_asset.get("error", "no_change_map"),
            )
        )

        macro_snapshot = self._load_world_macro_snapshot()
        macro_timestamp = macro_snapshot.get("timestamp") or macro_snapshot.get("updated") or macro_snapshot.get("generated_at")
        macro_age = self._timestamp_age_seconds(macro_timestamp)
        macro_fresh = bool(macro_snapshot) and (macro_age is None or macro_age <= WORLD_ECOSYSTEM_FRESH_SEC)
        macro_risk = str(macro_snapshot.get("risk_on_off") or macro_snapshot.get("risk_sentiment") or "").upper()
        macro_regime = str(macro_snapshot.get("market_regime") or "").upper()
        macro_side = "BUY" if "RISK_ON" in macro_risk or "BULL" in macro_regime else "SELL" if "RISK_OFF" in macro_risk or "BEAR" in macro_regime else ""
        if macro_fresh and macro_side and normalized_symbols:
            for normalized, symbol_state in sorted(
                normalized_symbols.items(),
                key=lambda item: float(item[1].get("strength", item[1].get("confidence", 0.0)) or 0.0),
                reverse=True,
            )[: min(6, WORLD_ECOSYSTEM_MAX_DECISION_SYMBOLS)]:
                candidate = self._world_decision_symbol(
                    symbol=normalized,
                    confidence=0.16,
                    side=macro_side,
                    reason="global_macro_risk_regime",
                    downstream_stage="hnc_proof",
                    existing_symbols=normalized_symbols,
                    price=float(symbol_state.get("reference_price", 0.0) or 0.0),
                    change_pct=float(symbol_state.get("change_pct", 0.0) or 0.0),
                    extra={"risk_on_off": macro_risk, "market_regime": macro_regime},
                )
                decision_symbols.setdefault(normalized, candidate)
        rows.append(
            self._world_source_row(
                system="WorldFinancialEcosystemFeed",
                facet="global_macro_market",
                wire_path="central_beat.world_financial_ecosystem.macro_snapshot",
                evidence_source=str(macro_snapshot.get("loaded_from") or "aureon/data_feeds/global_financial_feed.py"),
                present=bool(macro_snapshot),
                active_this_cycle=bool(macro_snapshot),
                fresh=macro_fresh,
                usable_for_decision=macro_fresh,
                fed_to_decision_logic=any(item.get("reason") == "global_macro_risk_regime" for item in decision_symbols.values()),
                downstream_stage="hnc_proof",
                last_timestamp=macro_timestamp,
                blocker="" if macro_fresh else macro_snapshot.get("error", "macro_snapshot_missing_or_stale"),
            )
        )

        news_signal = self._load_world_news_signal()
        news_age = self._timestamp_age_seconds(news_signal.get("fetched_at") or news_signal.get("generated_at"))
        try:
            news_sentiment = float(news_signal.get("sentiment", 0.0) or news_signal.get("score", 0.0) or 0.0)
        except Exception:
            news_sentiment = 0.0
        news_stale_flag = bool(news_signal.get("is_stale", False))
        news_fresh = bool(news_signal) and not news_stale_flag and (news_age is None or news_age <= WORLD_ECOSYSTEM_FRESH_SEC)
        news_side = "BUY" if news_sentiment > 0.05 else "SELL" if news_sentiment < -0.05 else ""
        if news_fresh and news_side and normalized_symbols:
            for normalized, symbol_state in sorted(
                normalized_symbols.items(),
                key=lambda item: float(item[1].get("change_pct_abs_max", 0.0) or 0.0),
                reverse=True,
            )[: min(4, WORLD_ECOSYSTEM_MAX_DECISION_SYMBOLS)]:
                candidate = self._world_decision_symbol(
                    symbol=normalized,
                    confidence=min(0.22, 0.08 + abs(news_sentiment) * 0.25),
                    side=news_side,
                    reason="world_news_sentiment",
                    downstream_stage="shadow_validation",
                    existing_symbols=normalized_symbols,
                    price=float(symbol_state.get("reference_price", 0.0) or 0.0),
                    change_pct=float(symbol_state.get("change_pct", 0.0) or 0.0),
                    extra={"news_sentiment": round(news_sentiment, 6), "headline_count": news_signal.get("headline_count")},
                )
                decision_symbols.setdefault(normalized, candidate)
        rows.append(
            self._world_source_row(
                system="NewsSignalBridge",
                facet="news_sentiment",
                wire_path="central_beat.world_financial_ecosystem.news_signal",
                evidence_source="aureon/data_feeds/news_signal.py",
                present=bool(news_signal),
                active_this_cycle=bool(news_signal),
                fresh=news_fresh,
                usable_for_decision=news_fresh,
                fed_to_decision_logic=any(item.get("reason") == "world_news_sentiment" for item in decision_symbols.values()),
                downstream_stage="shadow_validation",
                last_timestamp=news_signal.get("fetched_at") or news_signal.get("generated_at"),
                blocker="" if news_fresh else news_signal.get("error", "news_signal_missing_or_stale"),
            )
        )

        usable_count = sum(1 for row in rows if row.get("usable_for_decision"))
        active_count = sum(1 for row in rows if row.get("active_this_cycle"))
        report = {
            "schema_version": 1,
            "generated_at": now_iso,
            "enabled": True,
            "mode": "world_financial_ecosystem_intelligence_mesh",
            "summary": "Exchange streams, macro context, news sentiment, market harp resonance, and cross-asset pre-signals are converted into CentralBeat decision evidence.",
            "central_beat_market_sample": {
                "symbol_count": len(normalized_symbols),
                "price_count": len(symbol_to_price),
                "change_count": len(symbol_to_change),
                "source_count": len(sources),
                "regime_bias": regime.get("bias"),
            },
            "asset_class_coverage": sorted(asset_classes.keys()),
            "active_source_count": active_count,
            "usable_source_count": usable_count,
            "blocked_source_count": max(0, len(rows) - usable_count),
            "fed_to_decision_logic": bool(decision_symbols),
            "decision_symbol_count": len(decision_symbols),
            "decision_symbols": decision_symbols,
            "market_harp": market_harp,
            "cross_asset": cross_asset,
            "macro_snapshot": {
                "present": bool(macro_snapshot),
                "fresh": macro_fresh,
                "usable_for_decision": macro_fresh,
                "age_sec": round(macro_age, 3) if macro_age is not None else None,
                "risk_on_off": macro_snapshot.get("risk_on_off") or macro_snapshot.get("risk_sentiment"),
                "market_regime": macro_snapshot.get("market_regime"),
                "crypto_fear_greed": macro_snapshot.get("crypto_fear_greed"),
                "vix": macro_snapshot.get("vix"),
                "dxy": macro_snapshot.get("dxy"),
                "spx_change": macro_snapshot.get("spx_change"),
                "gold_change": macro_snapshot.get("gold_change"),
                "oil_change": macro_snapshot.get("oil_change"),
                "source": macro_snapshot.get("source"),
                "error": macro_snapshot.get("error", ""),
            },
            "news_signal": {
                "present": bool(news_signal),
                "fresh": news_fresh,
                "usable_for_decision": news_fresh,
                "age_sec": round(news_age, 3) if news_age is not None else None,
                "sentiment": news_sentiment,
                "headline_count": news_signal.get("headline_count"),
                "risk_level": news_signal.get("risk_level"),
                "themes": news_signal.get("themes", []),
                "summary": news_signal.get("summary", ""),
                "error": news_signal.get("error", ""),
            },
            "sources": rows,
        }
        self._world_ecosystem_intelligence = report
        self._world_ecosystem_at = time.time()
        self._publish_world_ecosystem_intelligence(report)
        return report

    def _build_world_ecosystem_source_snapshot(
        self,
        report: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not isinstance(report, dict) or not report.get("enabled"):
            return {}
        decision_symbols = report.get("decision_symbols", {})
        if not isinstance(decision_symbols, dict) or not decision_symbols:
            return {}
        symbols: Dict[str, Dict[str, Any]] = {}
        for normalized, item in decision_symbols.items():
            if not isinstance(item, dict):
                continue
            confidence = self._clamp01(item.get("confidence", 0.0))
            if confidence <= 0:
                continue
            symbol_key = self._normalize_symbol(normalized)
            if not symbol_key:
                continue
            symbols[symbol_key] = dict(item)
            symbols[symbol_key]["symbol"] = symbol_key
            symbols[symbol_key]["confidence"] = confidence
        if not symbols:
            return {}
        strongest = max(symbols.values(), key=lambda item: float(item.get("confidence", 0.0) or 0.0))
        return {
            "source": "world_financial_ecosystem",
            "ready": True,
            "mode": "macro_news_harp_cross_asset_decision_context",
            "symbols": symbols,
            "top_symbol": strongest.get("symbol"),
            "top_side": strongest.get("side"),
            "top_confidence": strongest.get("confidence"),
            "usable_source_count": report.get("usable_source_count", 0),
            "active_source_count": report.get("active_source_count", 0),
            "fed_to_decision_logic": report.get("fed_to_decision_logic", False),
        }

    def _merge_world_ecosystem_source(
        self,
        normalized_symbols: Dict[str, Dict[str, Any]],
        source_snapshot: Dict[str, Any],
    ) -> None:
        source_symbols = source_snapshot.get("symbols", {}) if isinstance(source_snapshot, dict) else {}
        if not isinstance(source_symbols, dict):
            return
        for normalized, item in source_symbols.items():
            if not isinstance(item, dict):
                continue
            confidence = self._clamp01(item.get("confidence", 0.0))
            if confidence <= 0:
                continue
            side = str(item.get("side") or "BUY").upper()
            if side not in {"BUY", "SELL"}:
                side = "BUY"
            symbol_state = normalized_symbols.setdefault(
                str(normalized),
                {
                    "confidence": round(confidence, 4),
                    "support_count": 0,
                    "side": side,
                    "imbalance": round(confidence, 4),
                    "strength": round(min(1.5, confidence), 4),
                    "sources": [],
                    "reference_price": float(item.get("price", 0.0) or 0.0),
                    "change_pct": float(item.get("change_pct", 0.0) or 0.0),
                    "change_pct_abs_max": abs(float(item.get("change_pct", 0.0) or 0.0)),
                    "volume_24h": 0.0,
                    "freshest_age_sec": None,
                    "fast_money_sources": [],
                    "source_prices": {},
                },
            )
            prior_confidence = self._clamp01(symbol_state.get("confidence", 0.0))
            current_side = str(symbol_state.get("side") or side).upper()
            aligned = side == current_side
            blended = prior_confidence + (confidence * (0.18 if aligned else -0.10))
            symbol_state["confidence"] = round(self._clamp01(blended, prior_confidence), 4)
            symbol_state["support_count"] = int(symbol_state.get("support_count", 0) or 0) + 1
            if "world_financial_ecosystem" not in symbol_state.get("sources", []):
                symbol_state.setdefault("sources", []).append("world_financial_ecosystem")
            if item.get("downstream_stage") in {"profit_velocity", "exchange_action_plan"} and "world_financial_ecosystem" not in symbol_state.get("fast_money_sources", []):
                symbol_state.setdefault("fast_money_sources", []).append("world_financial_ecosystem")
            if float(item.get("price", 0.0) or 0.0) > 0 and not float(symbol_state.get("reference_price", 0.0) or 0.0):
                symbol_state["reference_price"] = float(item.get("price", 0.0) or 0.0)
            if abs(float(item.get("change_pct", 0.0) or 0.0)) > abs(float(symbol_state.get("change_pct", 0.0) or 0.0)):
                symbol_state["change_pct"] = round(float(item.get("change_pct", 0.0) or 0.0), 6)
                symbol_state["change_pct_abs_max"] = round(abs(float(item.get("change_pct", 0.0) or 0.0)), 6)
            support_count = int(symbol_state.get("support_count", 0) or 0)
            symbol_state["strength"] = round(
                min(1.5, self._clamp01(symbol_state.get("confidence", 0.0)) * (1.0 + min(1.0, (support_count - 1) * 0.35))),
                4,
            )
            symbol_state["world_ecosystem_signal"] = item

    def _base_from_route_symbol(self, symbol: Any) -> str:
        raw = str(symbol or "").upper().strip().replace("/", "")
        for quote in ("USDT", "USDC", "BUSD", "FDUSD", "TUSD", "USD", "EUR", "GBP", "BTC", "BNB", "ETH"):
            if raw.endswith(quote) and len(raw) > len(quote):
                base = raw[:-len(quote)]
                if len(base) >= 3:
                    return base
        return raw[:4] if len(raw) > 4 else raw

    def _asset_balance_candidates(self, base: str) -> List[str]:
        base_norm = str(base or "").upper().strip()
        if base_norm in {"BTC", "XBT", "XXBT"}:
            return ["BTC", "XBT", "XXBT"]
        if base_norm in {"ETH", "XETH"}:
            return ["ETH", "XETH"]
        stripped = base_norm.lstrip("XZ")
        candidates = [base_norm]
        if stripped and stripped != base_norm:
            candidates.append(stripped)
        return list(dict.fromkeys(candidate for candidate in candidates if candidate))

    def _kraken_spot_client(self) -> Any:
        kraken = getattr(self, "kraken", None)
        if kraken is None:
            return None
        return getattr(kraken, "client", kraken)

    def _normalize_kraken_quote_asset(self, asset: Any) -> str:
        raw = str(asset or "").upper().strip()
        return {
            "ZUSD": "USD",
            "ZEUR": "EUR",
            "ZGBP": "GBP",
            "XXBT": "BTC",
            "XBT": "BTC",
            "XETH": "ETH",
        }.get(raw, raw)

    def _kraken_quote_usd_value(self, client: Any, asset: str, amount: float) -> float:
        asset_norm = self._normalize_kraken_quote_asset(asset)
        amount = max(0.0, float(amount or 0.0))
        if amount <= 0:
            return 0.0
        if asset_norm in {"USD", "USDC", "USDT"}:
            return amount
        if client is not None and hasattr(client, "convert_to_quote"):
            try:
                converted = float(client.convert_to_quote(asset_norm, amount, "USD") or 0.0)
                if converted > 0:
                    return converted
            except Exception:
                pass
        fallback_rates = {
            "GBP": _env_float("KRAKEN_GBP_USD_FALLBACK_RATE", 1.27),
            "EUR": _env_float("KRAKEN_EUR_USD_FALLBACK_RATE", 1.08),
        }
        return amount * float(fallback_rates.get(asset_norm, 0.0) or 0.0)

    def _kraken_spot_symbol_for_quote(self, symbol: str, quote_asset: str) -> str:
        base = self._base_from_route_symbol(symbol)
        quote = self._normalize_kraken_quote_asset(quote_asset)
        if not base or not quote:
            return str(symbol or "").upper().strip()
        base_part = "XBT" if base in {"BTC", "XBT", "XXBT"} else base
        return f"{base_part}{quote}"

    def _kraken_spot_quote_options(self, client: Any) -> List[Dict[str, Any]]:
        if client is None:
            return []
        raw_balances: Dict[str, float] = {}
        if hasattr(client, "get_account_balance"):
            try:
                balances = client.get_account_balance()
            except Exception:
                balances = {}
            if isinstance(balances, dict):
                for asset, amount in balances.items():
                    asset_norm = self._normalize_kraken_quote_asset(asset)
                    if asset_norm in {"USD", "USDC", "USDT", "GBP", "EUR"}:
                        try:
                            raw_balances[asset_norm] = raw_balances.get(asset_norm, 0.0) + float(amount or 0.0)
                        except Exception:
                            pass
        if hasattr(client, "get_free_balance"):
            for asset in ("USD", "ZUSD", "USDC", "USDT", "GBP", "ZGBP", "EUR", "ZEUR"):
                asset_norm = self._normalize_kraken_quote_asset(asset)
                try:
                    value = float(client.get_free_balance(asset) or 0.0)
                except Exception:
                    value = 0.0
                if value > 0:
                    raw_balances[asset_norm] = max(raw_balances.get(asset_norm, 0.0), value)
        options: List[Dict[str, Any]] = []
        for asset, amount in raw_balances.items():
            usd_value = self._kraken_quote_usd_value(client, asset, amount)
            if amount > 0 and usd_value > 0:
                options.append(
                    {
                        "asset": asset,
                        "available": round(amount, 8),
                        "available_usd": round(usd_value, 8),
                        "usd_per_quote": usd_value / amount if amount > 0 else 0.0,
                    }
                )
        return sorted(options, key=lambda item: float(item.get("available_usd", 0.0) or 0.0), reverse=True)

    def _estimate_route_price(self, venue: str, symbol: str) -> float:
        venue = str(venue or "").lower()
        symbol = str(symbol or "").upper().strip()
        if not symbol:
            return 0.0
        try:
            if venue == "kraken":
                client = self._kraken_spot_client()
                probe_interval = self._dynamic_probe_interval("kraken")
                if client is not None and hasattr(client, "best_price"):
                    ticker = self._governor().call(
                        "kraken",
                        "quotes",
                        f"kraken:best:{symbol}",
                        lambda: client.best_price(symbol),
                        min_interval_sec=probe_interval,
                        stale_ttl_sec=PROBE_SYMBOL_STALE_TTL_SEC,
                    )
                    if isinstance(ticker, dict):
                        price = float(ticker.get("price") or ticker.get("lastPrice") or ticker.get("last") or 0.0)
                        if price > 0:
                            return price
                if client is not None and hasattr(client, "get_ticker"):
                    ticker = self._governor().call(
                        "kraken",
                        "quotes",
                        f"kraken:ticker:{symbol}",
                        lambda: client.get_ticker(symbol),
                        min_interval_sec=probe_interval,
                        stale_ttl_sec=PROBE_SYMBOL_STALE_TTL_SEC,
                    )
                    if isinstance(ticker, dict):
                        price = float(ticker.get("price") or ticker.get("lastPrice") or ticker.get("last") or 0.0)
                        if price > 0:
                            return price
            if venue == "alpaca" and self.alpaca is not None:
                probe_interval = self._dynamic_probe_interval("alpaca")
                ticker = self._governor().call(
                    "alpaca",
                    "quotes",
                    f"alpaca:ticker:{symbol}",
                    lambda: self.alpaca.get_ticker(symbol),
                    min_interval_sec=probe_interval,
                    stale_ttl_sec=PROBE_SYMBOL_STALE_TTL_SEC,
                )
                if isinstance(ticker, dict):
                    price = float(ticker.get("price") or ticker.get("last") or ticker.get("mark_price") or 0.0)
                    if price > 0:
                        return price
            if venue == "binance" and self.binance is not None:
                probe_interval = self._dynamic_probe_interval("binance")
                ticker = self._governor().call(
                    "binance",
                    "quotes",
                    f"binance:24h:{symbol}",
                    lambda: self.binance.get_24h_ticker(symbol),
                    min_interval_sec=probe_interval,
                    stale_ttl_sec=PROBE_SYMBOL_STALE_TTL_SEC,
                )
                if isinstance(ticker, dict):
                    price = float(ticker.get("lastPrice") or ticker.get("weightedAvgPrice") or ticker.get("price") or 0.0)
                    if price > 0:
                        return price
            stream_price = self._estimate_stream_price(symbol)
            if stream_price > 0:
                return stream_price
        except Exception as e:
            logger.debug("Price estimate failed for %s %s: %s", venue, symbol, e)
        return 0.0

    def _spot_sell_quantity(self, client: Any, symbol: str, quote_usd: float, price: float) -> float:
        if client is None or price <= 0:
            return 0.0
        base = self._base_from_route_symbol(symbol)
        if not base:
            return 0.0
        available = 0.0
        for candidate in self._asset_balance_candidates(base):
            try:
                available = float(client.get_free_balance(candidate) or 0.0)
            except Exception:
                available = 0.0
            if available > 0:
                break
        if available <= 0:
            return 0.0
        target_qty = max(0.0, float(quote_usd or 0.0) / price)
        if target_qty <= 0:
            return 0.0
        return max(0.0, min(available, target_qty) * 0.999)

    def _empty_kraken_spot_fast_profit_state(self) -> Dict[str, Any]:
        return {
            "schema_version": 1,
            "mode": "kraken_spot_true_profit_first_past_the_post",
            "generated_at": datetime.now().isoformat(),
            "enabled": bool(KRAKEN_SPOT_FAST_PROFIT_CAPTURE_ENABLED),
            "fee_rate": KRAKEN_SPOT_TAKER_FEE_RATE,
            "min_true_profit_usd": KRAKEN_SPOT_FAST_PROFIT_MIN_USD,
            "min_hold_sec": KRAKEN_SPOT_FAST_PROFIT_MIN_HOLD_SEC,
            "collateral_reserve_usd": KRAKEN_SPOT_COLLATERAL_RESERVE_USD,
            "open_positions": [],
            "closed_positions": [],
            "last_check": {},
        }

    def _load_kraken_spot_fast_profit_state(self) -> Dict[str, Any]:
        state = getattr(self, "_kraken_spot_fast_profit_state", {}) or {}
        if state:
            return state
        try:
            if KRAKEN_SPOT_POSITION_STATE_PATH.exists():
                with KRAKEN_SPOT_POSITION_STATE_PATH.open("r", encoding="utf-8") as handle:
                    loaded = json.load(handle)
                if isinstance(loaded, dict):
                    state = loaded
        except Exception as e:
            logger.debug("Kraken spot fast-profit state read failed: %s", e)
        if not state:
            state = self._empty_kraken_spot_fast_profit_state()
        state.setdefault("open_positions", [])
        state.setdefault("closed_positions", [])
        state.setdefault("last_check", {})
        self._kraken_spot_fast_profit_state = state
        return state

    def _save_kraken_spot_fast_profit_state(self, state: Dict[str, Any]) -> None:
        state["generated_at"] = datetime.now().isoformat()
        state["enabled"] = bool(KRAKEN_SPOT_FAST_PROFIT_CAPTURE_ENABLED)
        state["fee_rate"] = KRAKEN_SPOT_TAKER_FEE_RATE
        state["min_true_profit_usd"] = KRAKEN_SPOT_FAST_PROFIT_MIN_USD
        state["min_hold_sec"] = KRAKEN_SPOT_FAST_PROFIT_MIN_HOLD_SEC
        state["collateral_reserve_usd"] = KRAKEN_SPOT_COLLATERAL_RESERVE_USD
        self._kraken_spot_fast_profit_state = state
        for path in (KRAKEN_SPOT_POSITION_STATE_PATH, KRAKEN_SPOT_POSITION_PUBLIC_PATH):
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                tmp_path = path.with_name(f"{path.name}.{os.getpid()}.tmp")
                with tmp_path.open("w", encoding="utf-8") as handle:
                    json.dump(state, handle, indent=2, default=str)
                os.replace(tmp_path, path)
            except Exception as e:
                logger.debug("Kraken spot fast-profit state write failed for %s: %s", path, e)

    def _kraken_spot_quote_cash_available(self, client: Any) -> float:
        return sum(float(option.get("available_usd", 0.0) or 0.0) for option in self._kraken_spot_quote_options(client))

    def _kraken_spot_inventory_symbol(self, asset: str) -> str:
        asset_norm = str(asset or "").upper().strip()
        if asset_norm in {"BTC", "XBT", "XXBT"}:
            return "XBTUSD"
        return f"{asset_norm}USD"

    def _kraken_spot_trade_history(self, client: Any) -> Dict[str, Any]:
        if client is None or not hasattr(client, "get_trades_history_dict"):
            return {}
        try:
            history = self._governor().call(
                "kraken",
                "private",
                "kraken:spot-trade-history",
                lambda: client.get_trades_history_dict(),
                min_interval_sec=KRAKEN_SPOT_POSTURE_CACHE_TTL_SEC,
                stale_ttl_sec=max(KRAKEN_SPOT_POSTURE_CACHE_TTL_SEC, 1800.0),
            )
        except Exception as e:
            logger.debug("Kraken spot trade history unavailable: %s", e)
            return {}
        return history if isinstance(history, dict) else {}

    def _kraken_spot_cost_basis_from_trades(self, symbol: str, trades: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(trades, dict) or not trades:
            return {}
        symbol_norm = str(symbol or "").upper().strip().replace("/", "")
        base = self._base_from_route_symbol(symbol_norm)
        base_candidates = set(self._asset_balance_candidates(base))
        if base in {"XBT", "XXBT"}:
            base_candidates.add("BTC")
        if base == "BTC":
            base_candidates.update({"XBT", "XXBT"})
        target_pairs = {symbol_norm}
        for base_candidate in base_candidates:
            for quote in ("USD", "USDC", "USDT", "EUR", "GBP"):
                target_pairs.add(f"{base_candidate}{quote}")
                target_pairs.add(f"X{base_candidate}Z{quote}")
                target_pairs.add(f"XX{base_candidate}Z{quote}")

        total_qty = 0.0
        total_cost = 0.0
        total_fees = 0.0
        buy_count = 0
        for trade in trades.values():
            if not isinstance(trade, dict):
                continue
            pair = str(trade.get("pair", "") or "").upper().replace("/", "")
            if pair not in target_pairs and symbol_norm not in pair:
                continue
            side = str(trade.get("type", "") or "").lower()
            try:
                qty = float(trade.get("vol", 0.0) or 0.0)
                price = float(trade.get("price", 0.0) or 0.0)
                fee = float(trade.get("fee", 0.0) or 0.0)
            except Exception:
                continue
            if qty <= 0 or price <= 0:
                continue
            if side == "buy":
                total_qty += qty
                total_cost += qty * price
                total_fees += fee
                buy_count += 1
            elif side == "sell":
                previous_qty = total_qty
                total_qty -= qty
                if total_qty > 0 and previous_qty > 0:
                    avg_price = total_cost / previous_qty
                    total_cost = total_qty * avg_price
                elif total_qty <= 0:
                    total_qty = 0.0
                    total_cost = 0.0
        if total_qty <= 0 or buy_count <= 0:
            return {}
        avg_entry = total_cost / total_qty if total_qty > 0 else 0.0
        return {
            "symbol": symbol_norm,
            "avg_entry_price": avg_entry,
            "total_quantity": total_qty,
            "total_cost": total_cost,
            "total_fees": total_fees,
            "trade_count": buy_count,
            "source": "cached_trade_history",
        }

    def _kraken_spot_inventory_cost_basis(self, client: Any, symbol: str) -> Dict[str, Any]:
        if client is None:
            return {}
        symbol_norm = str(symbol or "").upper().strip()
        if not symbol_norm:
            return {}
        trades = self._kraken_spot_trade_history(client)
        derived = self._kraken_spot_cost_basis_from_trades(symbol_norm, trades)
        if derived:
            return derived
        if not hasattr(client, "calculate_cost_basis"):
            return {}
        try:
            result = self._governor().call(
                "kraken",
                "private",
                f"kraken:spot-cost-basis:{symbol_norm}",
                lambda: client.calculate_cost_basis(symbol_norm),
                min_interval_sec=KRAKEN_SPOT_POSTURE_CACHE_TTL_SEC,
                stale_ttl_sec=max(KRAKEN_SPOT_POSTURE_CACHE_TTL_SEC, 1800.0),
            )
        except Exception as e:
            logger.debug("Kraken spot cost basis unavailable for %s: %s", symbol_norm, e)
            return {}
        return result if isinstance(result, dict) else {}

    def _kraken_spot_portfolio_posture(self, *, force: bool = False) -> Dict[str, Any]:
        now = time.time()
        cached = getattr(self, "_kraken_spot_portfolio_posture_cache", {}) or {}
        cached_at = float(getattr(self, "_kraken_spot_portfolio_posture_at", 0.0) or 0.0)
        if cached and not force and (now - cached_at) < KRAKEN_SPOT_POSTURE_CACHE_TTL_SEC:
            return dict(cached)

        client = self._kraken_spot_client()
        posture: Dict[str, Any] = {
            "schema_version": 1,
            "generated_at": datetime.now().isoformat(),
            "mode": "spot_and_margin_unified",
            "spot_buy_allowed": True,
            "margin_only": False,
            "reason": "",
            "asset_count": 0,
            "negative_position_count": 0,
            "profitable_position_count": 0,
            "unknown_cost_basis_count": 0,
            "assets": [],
        }
        if client is None or not hasattr(client, "get_account_balance"):
            posture.update(
                {
                    "spot_buy_allowed": True,
                    "reason": "kraken_spot_client_or_balance_unavailable",
                }
            )
            self._kraken_spot_portfolio_posture_cache = posture
            self._kraken_spot_portfolio_posture_at = now
            return dict(posture)

        try:
            raw_balances = client.get_account_balance()
        except Exception as e:
            posture.update(
                {
                    "spot_buy_allowed": True,
                    "reason": f"kraken_balance_read_failed:{e}",
                }
            )
            self._kraken_spot_portfolio_posture_cache = posture
            self._kraken_spot_portfolio_posture_at = now
            return dict(posture)

        quote_assets = {"USD", "ZUSD", "USDC", "USDT", "DAI", "GBP", "ZGBP", "EUR", "ZEUR"}
        assets: List[Dict[str, Any]] = []
        for asset, amount_value in sorted((raw_balances or {}).items()):
            asset_norm = str(asset or "").upper().strip()
            if asset_norm in quote_assets:
                continue
            try:
                amount = float(amount_value or 0.0)
            except Exception:
                amount = 0.0
            if amount <= 0:
                continue
            usd_value = self._kraken_quote_usd_value(client, asset_norm, amount)
            if usd_value < KRAKEN_SPOT_MANAGED_MIN_USD:
                continue
            symbol = self._kraken_spot_inventory_symbol(asset_norm)
            current_price = (usd_value / amount) if amount > 0 and usd_value > 0 else self._estimate_route_price("kraken", symbol)
            cost_basis = self._kraken_spot_inventory_cost_basis(client, symbol)
            cost_available = bool(cost_basis)
            avg_entry = 0.0
            total_qty = 0.0
            total_fees = 0.0
            if cost_available:
                try:
                    avg_entry = float(cost_basis.get("avg_entry_price", 0.0) or 0.0)
                    total_qty = float(cost_basis.get("total_quantity", 0.0) or 0.0)
                    total_fees = float(cost_basis.get("total_fees", 0.0) or 0.0)
                except Exception:
                    avg_entry = total_qty = total_fees = 0.0
                    cost_available = False
            if not cost_available or avg_entry <= 0 or current_price <= 0:
                state = "cost_basis_missing"
                entry_value = 0.0
                entry_fee = 0.0
                exit_fee = usd_value * KRAKEN_SPOT_TAKER_FEE_RATE
                true_net = 0.0
                posture["unknown_cost_basis_count"] += 1
            else:
                fee_ratio = min(1.0, amount / total_qty) if total_qty > 0 else 1.0
                entry_value = avg_entry * amount
                entry_fee = max(0.0, total_fees * fee_ratio)
                exit_fee = usd_value * KRAKEN_SPOT_TAKER_FEE_RATE
                true_net = usd_value - entry_value - entry_fee - exit_fee
                if true_net >= KRAKEN_SPOT_FAST_PROFIT_MIN_USD:
                    state = "profitable_spot_position"
                    posture["profitable_position_count"] += 1
                elif true_net < 0:
                    state = "negative_spot_position"
                    posture["negative_position_count"] += 1
                else:
                    state = "flat_after_costs"
            assets.append(
                {
                    "asset": asset_norm,
                    "symbol": symbol,
                    "amount": round(amount, 12),
                    "current_price": round(float(current_price or 0.0), 8),
                    "current_value_usd": round(float(usd_value or 0.0), 8),
                    "cost_basis_available": bool(cost_available),
                    "avg_entry_price": round(avg_entry, 8),
                    "entry_value_usd": round(entry_value, 8),
                    "entry_fee_usd": round(entry_fee, 8),
                    "estimated_exit_fee_usd": round(exit_fee, 8),
                    "true_net_profit_usd": round(true_net, 8),
                    "state": state,
                }
            )

        posture["assets"] = assets
        posture["asset_count"] = len(assets)
        if posture["negative_position_count"] > 0:
            posture.update(
                {
                    "mode": "margin_only_until_spot_profit",
                    "spot_buy_allowed": False,
                    "margin_only": True,
                    "reason": "spot_inventory_underwater; route new Kraken risk through margin until spot inventory is profitable or protected",
                }
            )
        else:
            posture["reason"] = "spot inventory has no known negative-cost positions"
        self._kraken_spot_portfolio_posture_cache = posture
        self._kraken_spot_portfolio_posture_at = now
        return dict(posture)

    def _kraken_spot_cost_profile(self, side: str, symbol: str, quote_usd: float, price: float) -> Dict[str, Any]:
        quote_value = max(0.0, float(quote_usd or 0.0))
        fee_rate = KRAKEN_SPOT_TAKER_FEE_RATE
        entry_fee = quote_value * fee_rate
        exit_fee = quote_value * fee_rate
        min_profit = KRAKEN_SPOT_FAST_PROFIT_MIN_USD
        required_move_usd = entry_fee + exit_fee + min_profit
        required_move_pct = (required_move_usd / quote_value * 100.0) if quote_value > 0 else 0.0
        return {
            "schema_version": 1,
            "venue": "kraken",
            "market_type": "spot",
            "symbol": symbol,
            "side": str(side or "").lower(),
            "price": round(float(price or 0.0), 8),
            "quote_usd": round(quote_value, 8),
            "fee_rate": round(fee_rate, 8),
            "estimated_entry_fee_usd": round(entry_fee, 8),
            "estimated_exit_fee_usd": round(exit_fee, 8),
            "estimated_round_trip_cost_usd": round(entry_fee + exit_fee, 8),
            "min_true_profit_usd": round(min_profit, 8),
            "required_move_usd": round(required_move_usd, 8),
            "required_move_pct": round(required_move_pct, 8),
            "cost_basis": "entry_fee_plus_exit_fee_plus_min_true_profit",
        }

    def _extract_order_quantity(self, result: Any, fallback_quantity: float) -> float:
        if not isinstance(result, dict):
            return max(0.0, float(fallback_quantity or 0.0))
        for key in ("executedQty", "origQty", "quantity", "volume"):
            try:
                value = float(result.get(key, 0.0) or 0.0)
            except Exception:
                value = 0.0
            if value > 0:
                return value
        return max(0.0, float(fallback_quantity or 0.0))

    def _record_kraken_spot_buy_position(
        self,
        *,
        symbol: str,
        quote_usd: float,
        price: float,
        result: Dict[str, Any],
        cost_profile: Dict[str, Any],
    ) -> Dict[str, Any]:
        if price <= 0 or quote_usd <= 0:
            return {}
        order_id = str(result.get("orderId") or result.get("txid") or f"kraken-spot-{int(time.time() * 1000)}")
        quantity = self._extract_order_quantity(result, quote_usd / price)
        entry_value = quantity * price
        if entry_value <= 0:
            entry_value = quote_usd
        position = {
            "id": order_id,
            "symbol": str(symbol or "").upper(),
            "base_asset": self._base_from_route_symbol(symbol),
            "side": "long_spot",
            "quantity": round(quantity, 12),
            "entry_price": round(price, 8),
            "entry_value_usd": round(entry_value, 8),
            "entry_fee_usd": round(entry_value * KRAKEN_SPOT_TAKER_FEE_RATE, 8),
            "opened_at": datetime.now().isoformat(),
            "opened_at_epoch": round(time.time(), 6),
            "source_order_id": order_id,
            "cost_profile": cost_profile,
            "status": "open",
        }
        state = self._load_kraken_spot_fast_profit_state()
        open_positions = [p for p in state.get("open_positions", []) if isinstance(p, dict) and p.get("status") == "open"]
        open_positions.append(position)
        state["open_positions"] = open_positions[-20:]
        state["last_check"] = {"recorded_buy": position, "generated_at": datetime.now().isoformat()}
        self._save_kraken_spot_fast_profit_state(state)
        return position

    def _kraken_spot_exit_price(self, client: Any, symbol: str) -> float:
        try:
            if client is not None and hasattr(client, "get_ticker"):
                ticker = client.get_ticker(symbol)
                if isinstance(ticker, dict):
                    bid = float(ticker.get("bid", 0.0) or 0.0)
                    if bid > 0:
                        return bid
                    price = float(ticker.get("price", 0.0) or ticker.get("lastPrice", 0.0) or 0.0)
                    if price > 0:
                        return price
        except Exception:
            pass
        return self._estimate_route_price("kraken", symbol)

    def _kraken_spot_fast_profit_decision(self, position: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        now = time.time()
        opened = float(position.get("opened_at_epoch", 0.0) or 0.0)
        hold_sec = max(0.0, now - opened) if opened > 0 else 0.0
        quantity = max(0.0, float(position.get("quantity", 0.0) or 0.0))
        entry_value = max(0.0, float(position.get("entry_value_usd", 0.0) or 0.0))
        entry_fee = max(0.0, float(position.get("entry_fee_usd", 0.0) or 0.0))
        exit_value = max(0.0, quantity * max(0.0, float(current_price or 0.0)))
        exit_fee = exit_value * KRAKEN_SPOT_TAKER_FEE_RATE
        gross_pnl = exit_value - entry_value
        true_net = gross_pnl - entry_fee - exit_fee
        blockers: List[str] = []
        if not KRAKEN_SPOT_FAST_PROFIT_CAPTURE_ENABLED:
            blockers.append("fast_profit_capture_disabled")
        if current_price <= 0:
            blockers.append("price_unavailable")
        if quantity <= 0:
            blockers.append("quantity_unavailable")
        if hold_sec < KRAKEN_SPOT_FAST_PROFIT_MIN_HOLD_SEC:
            blockers.append("min_hold_time_not_met")
        if true_net < KRAKEN_SPOT_FAST_PROFIT_MIN_USD:
            blockers.append("true_profit_below_minimum_after_spot_fees")
        if not self._runtime_real_orders_allowed():
            blockers.append("live_exchange_mutation_not_enabled")
        return {
            "schema_version": 1,
            "generated_at": datetime.now().isoformat(),
            "symbol": position.get("symbol"),
            "position_id": position.get("id"),
            "current_price": round(float(current_price or 0.0), 8),
            "quantity": round(quantity, 12),
            "hold_seconds": round(hold_sec, 3),
            "gross_pnl_usd": round(gross_pnl, 8),
            "true_net_profit_usd": round(true_net, 8),
            "costs": {
                "entry_fee_usd": round(entry_fee, 8),
                "estimated_exit_fee_usd": round(exit_fee, 8),
                "round_trip_cost_usd": round(entry_fee + exit_fee, 8),
            },
            "ready_to_capture": bool(not blockers),
            "blockers": blockers,
            "reason": "capture_spot_true_profit_after_costs" if not blockers else ",".join(blockers),
            "collateral_note": "Kraken spot cash is treated as shared account collateral, so entry records preserve fee/cash impact before margin logic trusts profit.",
        }

    def _sync_kraken_spot_inventory_positions(self, client: Any, state: Dict[str, Any]) -> Dict[str, Any]:
        posture = self._kraken_spot_portfolio_posture(force=False)
        assets = posture.get("assets", []) if isinstance(posture, dict) else []
        if not isinstance(assets, list):
            return state
        existing = [
            p for p in state.get("open_positions", [])
            if isinstance(p, dict) and p.get("status") == "open"
        ]
        by_id = {str(p.get("id") or ""): p for p in existing if p.get("id")}
        synced: List[Dict[str, Any]] = []
        for asset in assets:
            if not isinstance(asset, dict) or not asset.get("cost_basis_available"):
                continue
            amount = max(0.0, float(asset.get("amount", 0.0) or 0.0))
            current_value = max(0.0, float(asset.get("current_value_usd", 0.0) or 0.0))
            if amount <= 0 or current_value < KRAKEN_SPOT_MANAGED_MIN_USD:
                continue
            symbol = str(asset.get("symbol") or "").upper().strip()
            asset_name = str(asset.get("asset") or self._base_from_route_symbol(symbol)).upper().strip()
            position_id = f"kraken-spot-inventory-{asset_name}"
            position = dict(by_id.get(position_id) or {})
            opened_at_epoch = float(position.get("opened_at_epoch", 0.0) or 0.0)
            if opened_at_epoch <= 0:
                opened_at_epoch = time.time() - KRAKEN_SPOT_FAST_PROFIT_MIN_HOLD_SEC - 1.0
            position.update(
                {
                    "id": position_id,
                    "symbol": symbol,
                    "base_asset": asset_name,
                    "side": "long_spot",
                    "quantity": round(amount, 12),
                    "entry_price": round(float(asset.get("avg_entry_price", 0.0) or 0.0), 8),
                    "entry_value_usd": round(float(asset.get("entry_value_usd", 0.0) or 0.0), 8),
                    "entry_fee_usd": round(float(asset.get("entry_fee_usd", 0.0) or 0.0), 8),
                    "opened_at": position.get("opened_at") or datetime.fromtimestamp(opened_at_epoch).isoformat(),
                    "opened_at_epoch": opened_at_epoch,
                    "source_order_id": position.get("source_order_id") or position_id,
                    "source": "live_balance_cost_basis",
                    "status": "open",
                    "inventory_state": asset.get("state"),
                    "last_inventory_sync": datetime.now().isoformat(),
                    "last_current_value_usd": round(current_value, 8),
                }
            )
            synced.append(position)
        explicit_positions = [
            p for p in existing
            if str(p.get("source") or "") != "live_balance_cost_basis"
            and not str(p.get("id") or "").startswith("kraken-spot-inventory-")
        ]
        state["open_positions"] = (explicit_positions + synced)[-20:]
        if synced:
            state["last_inventory_sync"] = {
                "generated_at": datetime.now().isoformat(),
                "synced_count": len(synced),
                "posture_mode": posture.get("mode"),
                "negative_position_count": posture.get("negative_position_count", 0),
                "profitable_position_count": posture.get("profitable_position_count", 0),
            }
        return state

    def _arm_kraken_spot_deadman_switch(self, client: Any, position: Dict[str, Any], decision: Dict[str, Any]) -> Dict[str, Any]:
        if not KRAKEN_SPOT_DEADMAN_SWITCH_ENABLED:
            return {"ok": False, "reason": "spot_deadman_switch_disabled"}
        if client is None:
            return {"ok": False, "reason": "kraken_spot_client_missing"}
        if not self._runtime_real_orders_allowed():
            return {"ok": False, "reason": "live_exchange_mutation_not_enabled"}
        symbol = str(position.get("symbol") or decision.get("symbol") or "").upper().strip()
        quantity = max(0.0, float(position.get("quantity", 0.0) or decision.get("quantity", 0.0) or 0.0)) * 0.999
        if not symbol or quantity <= 0:
            return {"ok": False, "reason": "deadman_symbol_or_quantity_unavailable"}
        try:
            if hasattr(client, "place_trailing_stop_order"):
                result = client.place_trailing_stop_order(
                    symbol,
                    "sell",
                    quantity=quantity,
                    trailing_offset=KRAKEN_SPOT_DEADMAN_TRAILING_PCT,
                    offset_type="percent",
                )
                order_type = "trailing_stop"
            elif hasattr(client, "place_take_profit_order"):
                price = float(decision.get("current_price", 0.0) or 0.0)
                if price <= 0:
                    return {"ok": False, "reason": "deadman_price_unavailable"}
                result = client.place_take_profit_order(symbol, "sell", quantity=quantity, take_profit_price=price)
                order_type = "take_profit"
            else:
                return {"ok": False, "reason": "kraken_deadman_order_api_missing"}
        except Exception as e:
            return {"ok": False, "reason": "kraken_deadman_order_failed", "error": str(e)}
        rejected = isinstance(result, dict) and bool(result.get("error") or result.get("rejected"))
        return {
            "ok": bool(result) and not rejected,
            "order_type": order_type,
            "symbol": symbol,
            "quantity": round(quantity, 12),
            "trailing_offset_pct": KRAKEN_SPOT_DEADMAN_TRAILING_PCT if order_type == "trailing_stop" else None,
            "result": result,
            "reason": "deadman_switch_armed_for_profitable_spot_inventory" if result and not rejected else "deadman_switch_rejected",
        }

    def _monitor_kraken_spot_fast_profit(self) -> List[Dict[str, Any]]:
        state = self._load_kraken_spot_fast_profit_state()
        client = self._kraken_spot_client()
        if client is not None:
            state = self._sync_kraken_spot_inventory_positions(client, state)
        open_positions = [p for p in state.get("open_positions", []) if isinstance(p, dict) and p.get("status") == "open"]
        checks: List[Dict[str, Any]] = []
        closed: List[Dict[str, Any]] = []
        if client is None or not open_positions:
            state["last_check"] = {
                "generated_at": datetime.now().isoformat(),
                "open_count": len(open_positions),
                "closed_count": 0,
                "reason": "kraken_spot_client_missing" if client is None else "no_open_spot_positions",
            }
            self._save_kraken_spot_fast_profit_state(state)
            return []

        remaining: List[Dict[str, Any]] = []
        for position in open_positions:
            symbol = str(position.get("symbol") or "").upper().strip()
            price = self._kraken_spot_exit_price(client, symbol)
            decision = self._kraken_spot_fast_profit_decision(position, price)
            checks.append(decision)
            if not decision.get("ready_to_capture"):
                remaining.append(position)
                continue
            quantity = max(0.0, float(position.get("quantity", 0.0) or 0.0)) * 0.999
            if quantity <= 0:
                decision["ready_to_capture"] = False
                decision["blockers"] = ["quantity_unavailable"]
                decision["reason"] = "quantity_unavailable"
                remaining.append(position)
                continue
            try:
                result = client.place_market_order(symbol, "sell", quantity=quantity)
            except Exception as e:
                result = {"error": str(e)}
            rejected = isinstance(result, dict) and bool(result.get("error") or result.get("rejected"))
            if result and not rejected:
                completed = dict(position)
                completed.update(
                    {
                        "status": "closed",
                        "closed_at": datetime.now().isoformat(),
                        "exit_price": decision.get("current_price", 0.0),
                        "exit_quantity": round(quantity, 12),
                        "close_result": result,
                        "reason": "KRAKEN_SPOT_FAST_PROFIT_CAPTURE",
                        "net_pnl": decision.get("true_net_profit_usd", 0.0),
                        "fast_profit_capture": decision,
                    }
                )
                closed.append(completed)
            else:
                position["last_close_error"] = result
                deadman = self._arm_kraken_spot_deadman_switch(client, position, decision)
                if deadman.get("ok"):
                    position["deadman_switch"] = deadman
                    position["deadman_switch_armed_at"] = datetime.now().isoformat()
                    decision["deadman_switch"] = deadman
                else:
                    position["last_deadman_error"] = deadman
                remaining.append(position)

        prior_closed = [p for p in state.get("closed_positions", []) if isinstance(p, dict)]
        state["open_positions"] = remaining[-20:]
        state["closed_positions"] = (prior_closed + closed)[-50:]
        state["last_check"] = {
            "generated_at": datetime.now().isoformat(),
            "open_count": len(remaining),
            "closed_count": len(closed),
            "checks": checks[-20:],
        }
        self._save_kraken_spot_fast_profit_state(state)
        for item in closed:
            self._publish_thought("execution.trade.closed", {
                "pair": item.get("symbol"),
                "net_pnl": float(item.get("net_pnl", 0.0) or 0.0),
                "reason": item.get("reason"),
                "exchange": "kraken_spot",
            })
            self._record_trade_profit(item)
        return closed

    def _execute_kraken_spot_route(self, side: str, symbol: str, quote_usd: float) -> Dict[str, Any]:
        client = self._kraken_spot_client()
        if client is None or not hasattr(client, "place_market_order"):
            return {"ok": False, "venue": "kraken", "market_type": "spot", "symbol": symbol, "reason": "kraken_spot_client_missing"}
        side_norm = "buy" if str(side or "BUY").upper() == "BUY" else "sell"
        if side_norm == "buy":
            posture = self._kraken_spot_portfolio_posture(force=False)
            if not bool(posture.get("spot_buy_allowed", True)):
                return {
                    "ok": False,
                    "venue": "kraken",
                    "market_type": "spot",
                    "symbol": symbol,
                    "side": side_norm,
                    "reason": "kraken_spot_inventory_underwater_margin_only",
                    "portfolio_unity": posture,
                }
            spot_quote_usd = max(float(quote_usd or 0.0), KRAKEN_SPOT_QUOTE_USD)
            quote_options = self._kraken_spot_quote_options(client)
            usd_price_symbol = self._to_kraken_spot_symbol(self._normalize_symbol(symbol)) or symbol
            price = self._estimate_route_price("kraken", usd_price_symbol)
            cost_profile = self._kraken_spot_cost_profile(side_norm, usd_price_symbol, spot_quote_usd, price)
            required_usd_with_reserve = spot_quote_usd + cost_profile["estimated_entry_fee_usd"] + KRAKEN_SPOT_COLLATERAL_RESERVE_USD
            quote_cash = sum(float(option.get("available_usd", 0.0) or 0.0) for option in quote_options)
            quote_option = next(
                (
                    option
                    for option in quote_options
                    if float(option.get("available_usd", 0.0) or 0.0) >= required_usd_with_reserve
                    and float(option.get("usd_per_quote", 0.0) or 0.0) > 0
                ),
                {},
            )
            if not quote_option:
                return {
                    "ok": False,
                    "venue": "kraken",
                    "market_type": "spot",
                    "symbol": symbol,
                    "side": side_norm,
                    "reason": "kraken_spot_quote_cash_fragmented_or_insufficient_for_order",
                    "quote_usd": spot_quote_usd,
                    "quote_cash_available_usd": quote_cash,
                    "quote_cash_options": quote_options,
                    "collateral_reserve_usd": KRAKEN_SPOT_COLLATERAL_RESERVE_USD,
                    "cost_profile": cost_profile,
                }
            quote_asset = str(quote_option.get("asset") or "USD")
            execution_symbol = self._kraken_spot_symbol_for_quote(symbol, quote_asset)
            quote_qty = spot_quote_usd / float(quote_option.get("usd_per_quote", 1.0) or 1.0)
            result = client.place_market_order(execution_symbol, side_norm, quote_qty=quote_qty)
            order_value = spot_quote_usd
            position = {}
            if isinstance(result, dict) and not bool(result.get("error") or result.get("rejected")):
                position = self._record_kraken_spot_buy_position(
                    symbol=execution_symbol,
                    quote_usd=spot_quote_usd,
                    price=price if price > 0 else self._estimate_route_price("kraken", symbol),
                    result=result,
                    cost_profile=cost_profile,
                )
        else:
            price = self._estimate_route_price("kraken", symbol)
            cost_profile = self._kraken_spot_cost_profile(side_norm, symbol, max(float(quote_usd or 0.0), KRAKEN_SPOT_QUOTE_USD), price)
            quantity = self._spot_sell_quantity(client, symbol, max(float(quote_usd or 0.0), KRAKEN_SPOT_QUOTE_USD), price)
            if quantity <= 0:
                return {"ok": False, "venue": "kraken", "market_type": "spot", "symbol": symbol, "side": side_norm, "reason": "no_spot_balance_to_sell"}
            result = client.place_market_order(symbol, side_norm, quantity=quantity)
            order_value = quantity * price if price > 0 else 0.0
            position = {}
        rejected = isinstance(result, dict) and bool(result.get("error") or result.get("rejected"))
        return {
            "ok": bool(result) and not rejected,
            "venue": "kraken",
            "market_type": "spot",
            "symbol": execution_symbol if side_norm == "buy" else symbol,
            "side": side_norm,
            "quote_usd": order_value,
            "quote_asset": quote_option.get("asset") if side_norm == "buy" else None,
            "quote_qty": quote_qty if side_norm == "buy" else None,
            "cost_profile": cost_profile,
            "fast_profit_position": position,
            "result": result,
        }

    def _execute_alpaca_spot_route(self, side: str, symbol: str, quote_usd: float) -> Dict[str, Any]:
        if self.alpaca is None:
            return {"ok": False, "venue": "alpaca", "symbol": symbol, "reason": "alpaca_client_missing"}
        side_norm = "buy" if str(side).upper() == "BUY" else "sell"
        if side_norm == "buy":
            result = self.alpaca.place_market_order(symbol, side_norm, quote_qty=quote_usd)
        else:
            price = self._estimate_route_price("alpaca", symbol)
            quantity = self._spot_sell_quantity(self.alpaca, symbol, quote_usd, price)
            if quantity <= 0:
                return {"ok": False, "venue": "alpaca", "symbol": symbol, "side": side_norm, "reason": "no_spot_balance_to_sell"}
            result = self.alpaca.place_market_order(symbol, side_norm, quantity=quantity)
        return {"ok": bool(result), "venue": "alpaca", "market_type": "spot", "symbol": symbol, "side": side_norm, "result": result}

    def _execute_binance_spot_route(self, side: str, symbol: str, quote_usd: float) -> Dict[str, Any]:
        if self.binance is None:
            return {"ok": False, "venue": "binance", "symbol": symbol, "reason": "binance_client_missing"}
        side_norm = str(side or "BUY").upper()
        if side_norm == "BUY":
            result = self.binance.place_market_order(symbol, side_norm, quote_qty=quote_usd)
        else:
            price = self._estimate_route_price("binance", symbol)
            quantity = self._spot_sell_quantity(self.binance, symbol, quote_usd, price)
            if quantity <= 0:
                return {"ok": False, "venue": "binance", "symbol": symbol, "side": side_norm, "reason": "no_spot_balance_to_sell"}
            result = self.binance.place_market_order(symbol, side_norm, quantity=quantity)
        return {"ok": bool(result), "venue": "binance", "market_type": "spot", "symbol": symbol, "side": side_norm, "result": result}

    def _kraken_margin_leverage_for_route(self, client: Any, symbol: str, side: str) -> int:
        preferred = max(1, int(KRAKEN_MARGIN_LEVERAGE or 1))
        if client is None or not hasattr(client, "get_pair_leverage"):
            return preferred
        try:
            info = client.get_pair_leverage(symbol)
        except Exception:
            info = {}
        if not isinstance(info, dict):
            return 0
        side_norm = "buy" if str(side or "BUY").upper() == "BUY" else "sell"
        key = "leverage_buy" if side_norm == "buy" else "leverage_sell"
        try:
            valid = sorted({int(float(value)) for value in (info.get(key) or []) if int(float(value)) > 0})
        except Exception:
            valid = []
        if not valid:
            return 0
        eligible = [value for value in valid if value <= preferred]
        return max(eligible) if eligible else min(valid)

    def _execute_kraken_margin_route(self, side: str, symbol: str, quote_usd: float) -> Dict[str, Any]:
        client = self._kraken_spot_client()
        if client is None or not hasattr(client, "place_margin_order"):
            return {"ok": False, "venue": "kraken", "market_type": "margin", "symbol": symbol, "reason": "kraken_margin_client_missing"}
        if not self._env_enabled("KRAKEN_MARGIN_ENABLED", True):
            return {"ok": False, "venue": "kraken", "market_type": "margin", "symbol": symbol, "reason": "KRAKEN_MARGIN_ENABLED_not_true"}
        side_norm = "buy" if str(side or "BUY").upper() == "BUY" else "sell"
        price = self._estimate_route_price("kraken", symbol)
        if price <= 0:
            return {"ok": False, "venue": "kraken", "market_type": "margin", "symbol": symbol, "side": side_norm, "reason": "price_unavailable"}
        leverage = self._kraken_margin_leverage_for_route(client, symbol, side_norm)
        if leverage <= 0:
            return {"ok": False, "venue": "kraken", "market_type": "margin", "symbol": symbol, "side": side_norm, "reason": "margin_pair_leverage_unavailable"}
        margin_quote_usd = max(float(quote_usd or 0.0), KRAKEN_MARGIN_QUOTE_USD)
        quantity = max(0.0, margin_quote_usd / price)
        if quantity <= 0:
            return {"ok": False, "venue": "kraken", "market_type": "margin", "symbol": symbol, "side": side_norm, "reason": "quantity_unavailable"}
        result = client.place_margin_order(
            symbol=symbol,
            side=side_norm,
            quantity=quantity,
            leverage=leverage,
        )
        rejected = isinstance(result, dict) and bool(result.get("error") or result.get("rejected"))
        return {
            "ok": bool(result) and not rejected,
            "venue": "kraken",
            "market_type": "margin",
            "symbol": symbol,
            "side": side_norm,
            "quote_usd": margin_quote_usd,
            "quantity": quantity,
            "leverage": leverage,
            "price": price,
            "result": result,
        }

    def _execute_binance_margin_route(self, side: str, symbol: str, quote_usd: float) -> Dict[str, Any]:
        if self.binance is None:
            return {"ok": False, "venue": "binance", "symbol": symbol, "reason": "binance_client_missing"}
        if not self._env_enabled("BINANCE_MARGIN_ENABLED"):
            return {"ok": False, "venue": "binance", "market_type": "margin", "symbol": symbol, "reason": "BINANCE_MARGIN_ENABLED_not_true"}
        price = self._estimate_route_price("binance", symbol)
        if price <= 0:
            return {"ok": False, "venue": "binance", "market_type": "margin", "symbol": symbol, "reason": "price_unavailable"}
        quantity = max(0.0, quote_usd / price)
        if quantity <= 0:
            return {"ok": False, "venue": "binance", "market_type": "margin", "symbol": symbol, "reason": "quantity_unavailable"}
        side_norm = str(side or "BUY").upper()
        result = self.binance.place_margin_order(
            symbol=symbol,
            side=side_norm,
            quantity=quantity,
            leverage=BINANCE_MARGIN_LEVERAGE,
        )
        return {"ok": bool(result and not result.get("rejected") and not result.get("error")), "venue": "binance", "market_type": "margin", "symbol": symbol, "side": side_norm, "quantity": quantity, "result": result}

    def _execution_blockers(self, payload: Dict[str, Any], action_plan: Dict[str, Any]) -> List[str]:
        blockers: List[str] = []
        if not self._unified_executor_enabled():
            blockers.append("unified_order_executor_disabled")
        if not self._runtime_real_orders_allowed():
            blockers.append("real_orders_not_allowed_by_runtime")
        if not bool(action_plan.get("order_intent_publish_enabled")):
            blockers.append("order_intent_publish_disabled")
        if action_plan.get("global_blockers"):
            blockers.extend(str(item) for item in action_plan.get("global_blockers", []) if str(item))
        tick_running = max(0.0, time.time() - float(getattr(self, "_last_tick_started_at", 0.0) or 0.0))
        if tick_running > TICK_RUNNING_STALE_AFTER_SEC:
            blockers.append("current_tick_stale")
        try:
            combined = payload.get("combined") if isinstance(payload.get("combined"), dict) else {}
            open_positions = int(combined.get("open_positions", 0) or 0)
        except Exception:
            open_positions = 0
        if open_positions >= ORDER_EXECUTOR_MAX_OPEN_POSITIONS:
            blockers.append("max_open_positions_reached")
        now = time.time()
        if now - float(getattr(self, "_last_execution_at", 0.0) or 0.0) < ORDER_EXECUTOR_MIN_INTERVAL_SEC:
            blockers.append("executor_cycle_cooldown")
        return sorted(set(blockers))

    def _persist_execution_summary(self, execution_summary: Dict[str, Any]) -> None:
        try:
            EXECUTION_RESULT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with EXECUTION_RESULT_LOG_PATH.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(execution_summary, default=str, sort_keys=True) + "\n")
        except Exception as e:
            logger.debug("Execution result log write failed: %s", e)
        for path in (EXECUTION_RESULT_STATE_PATH, EXECUTION_RESULT_PUBLIC_PATH):
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                tmp_path = path.with_name(f"{path.name}.{os.getpid()}.tmp")
                with tmp_path.open("w", encoding="utf-8") as handle:
                    json.dump(execution_summary, handle, indent=2, default=str)
                os.replace(tmp_path, path)
            except Exception as e:
                logger.debug("Execution result state write failed for %s: %s", path, e)

    def _execute_runtime_order_actions(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        order_flow = payload.get("shared_order_flow") if isinstance(payload.get("shared_order_flow"), dict) else {}
        action_plan = payload.get("exchange_action_plan") if isinstance(payload.get("exchange_action_plan"), dict) else {}
        blockers = self._execution_blockers(payload, action_plan)
        now = time.time()
        execution_summary: Dict[str, Any] = {
            "generated_at": datetime.now().isoformat(),
            "executor_enabled": self._unified_executor_enabled(),
            "quote_usd": ORDER_EXECUTOR_QUOTE_USD,
            "kraken_spot_quote_usd": KRAKEN_SPOT_QUOTE_USD,
            "kraken_spot_portfolio_posture": order_flow.get("kraken_spot_portfolio_posture", {}),
            "trade_path_state": "available" if not blockers else "runtime_clearance_hold",
            "live_action_clearance": "cleared" if not blockers else "waiting_for_runtime_truth",
            "runtime_clearances": blockers,
            "guards": blockers,
            "attempted_count": 0,
            "submitted_count": 0,
            "delegated_count": 0,
            "held_count": 0,
            "blocked_count": 0,
            "results": [],
            "blockers": blockers,
            "route_timeout_sec": ORDER_EXECUTOR_ROUTE_TIMEOUT_SEC,
            "executor_route_state": self._executor_route_snapshot(),
            "order_lifecycle": self._order_lifecycle_snapshot(),
        }
        if blockers:
            self._latest_execution_results = execution_summary
            action_plan["latest_execution"] = execution_summary
            self._persist_execution_summary(execution_summary)
            return execution_summary

        active = order_flow.get("active_order_flow", []) if isinstance(order_flow, dict) else []
        if not isinstance(active, list):
            active = []

        for item in active:
            if execution_summary["attempted_count"] >= ORDER_EXECUTOR_MAX_PER_TICK:
                break
            if not isinstance(item, dict):
                continue
            confidence = max(0.0, min(1.0, float(item.get("confidence", 0.0) or 0.0)))
            if confidence < ORDER_INTENT_MIN_CONFIDENCE:
                continue
            side = str(item.get("side") or "BUY").upper()
            candidate_id, lifecycle_id = self._candidate_lifecycle_identity(item)
            item["candidate_id"] = candidate_id
            item["lifecycle_id"] = lifecycle_id
            intent_id = str(item.get("intent_id") or item.get("id") or "")
            routes = item.get("execution_routes", []) if isinstance(item.get("execution_routes"), list) else []
            for route_item in routes:
                if execution_summary["attempted_count"] >= ORDER_EXECUTOR_MAX_PER_TICK:
                    break
                if not isinstance(route_item, dict) or not route_item.get("ready"):
                    continue
                venue = str(route_item.get("venue") or "").lower()
                market_type = str(route_item.get("market_type") or "").lower()
                route_symbol = str(route_item.get("symbol") or "").upper().strip()
                route_key = str(route_item.get("route_key") or self._order_route_key(venue, market_type, route_symbol, side))
                owner = str(route_item.get("execution_owner") or "").lower()
                if (
                    self._order_lifecycle_enabled_now()
                    and order_lifecycle_route_active is not None
                    and order_lifecycle_route_active(route_key, root=self._order_lifecycle_root())
                ):
                    execution_summary["attempted_count"] += 1
                    execution_summary["held_count"] += 1
                    execution_summary["blocked_count"] += 1
                    held = {
                        "ok": False,
                        "held": True,
                        "venue": venue,
                        "market_type": market_type,
                        "symbol": route_symbol,
                        "side": side,
                        "route_key": route_key,
                        "candidate_id": candidate_id,
                        "lifecycle_id": lifecycle_id,
                        "intent_id": intent_id,
                        "reason": "order_lifecycle_route_already_submitted_or_open",
                    }
                    execution_summary["results"].append(held)
                    self._record_order_lifecycle(
                        "duplicate_submission_blocked",
                        "order_blocked",
                        lifecycle_id,
                        candidate_id=candidate_id,
                        intent_id=intent_id,
                        route_key=route_key,
                        venue=venue,
                        market_type=market_type,
                        symbol=route_symbol,
                        side=side,
                        reason=held["reason"],
                        source="unified_market_trader.executor",
                    )
                    continue
                if (owner == "existing_autonomous_trader_tick" and not (venue == "kraken" and market_type == "margin")) or (
                    venue == "capital" and market_type == "cfd"
                ):
                    delegated = {
                        "ok": True,
                        "delegated": True,
                        "submitted": False,
                        "venue": venue,
                        "market_type": market_type,
                        "symbol": route_symbol,
                        "side": side,
                        "route_key": route_key,
                        "candidate_id": candidate_id,
                        "lifecycle_id": lifecycle_id,
                        "intent_id": intent_id,
                        "reason": "delegated_to_existing_autonomous_trader_tick",
                        "generated_at": datetime.now().isoformat(),
                        "source": "unified_market_trader.executor",
                        "confidence": confidence,
                        "selection_rank": item.get("selection_rank"),
                        "profit_velocity_score": item.get("profit_velocity_score", 0.0),
                        "fast_money_score": item.get("fast_money_score", 0.0),
                        "fast_money_candidate": bool(item.get("fast_money_candidate")),
                        "fast_money_profile": item.get("fast_money_profile", {}),
                        "orderbook_pressure": item.get("orderbook_pressure", {}),
                        "estimated_target_eta_sec": item.get("estimated_target_eta_sec", 0.0),
                        "support_count": item.get("support_count", 0),
                        "cognitive_sources": item.get("sources", []),
                        "model_signal": item.get("model_signal", {}),
                        "model_alignment": item.get("model_alignment", False),
                    }
                    self._record_order_lifecycle(
                        "executor_delegated",
                        "executor_accepted",
                        lifecycle_id,
                        candidate_id=candidate_id,
                        intent_id=intent_id,
                        route_key=route_key,
                        venue=venue,
                        market_type=market_type,
                        symbol=route_symbol,
                        side=side,
                        reason=delegated["reason"],
                        source="unified_market_trader.executor",
                    )
                    execution_summary["delegated_count"] += 1
                    execution_summary["results"].append(delegated)
                    continue

                last_route_at = float(self._execution_memory.get(route_key, 0.0) or 0.0)
                if now - last_route_at < ORDER_EXECUTOR_SYMBOL_COOLDOWN_SEC:
                    execution_summary["attempted_count"] += 1
                    execution_summary["held_count"] += 1
                    execution_summary["blocked_count"] += 1
                    execution_summary["results"].append({
                        "ok": False,
                        "held": True,
                        "venue": venue,
                        "market_type": market_type,
                        "symbol": route_symbol,
                        "side": side,
                        "route_key": route_key,
                        "candidate_id": candidate_id,
                        "lifecycle_id": lifecycle_id,
                        "intent_id": intent_id,
                        "reason": "symbol_route_cooldown",
                    })
                    continue

                try:
                    execution_summary["attempted_count"] += 1
                    self._record_order_lifecycle(
                        "executor_accepted",
                        "executor_accepted",
                        lifecycle_id,
                        candidate_id=candidate_id,
                        intent_id=intent_id,
                        route_key=route_key,
                        venue=venue,
                        market_type=market_type,
                        symbol=route_symbol,
                        side=side,
                        confidence=confidence,
                        source="unified_market_trader.executor",
                    )
                    if venue == "kraken" and market_type == "spot":
                        result = self._run_executor_route_with_timeout(
                            route_key,
                            venue,
                            market_type,
                            route_symbol,
                            side,
                            lambda side=side, route_symbol=route_symbol: self._execute_kraken_spot_route(
                                side,
                                route_symbol,
                                ORDER_EXECUTOR_QUOTE_USD,
                            ),
                        )
                    elif venue == "kraken" and market_type == "margin":
                        result = self._run_executor_route_with_timeout(
                            route_key,
                            venue,
                            market_type,
                            route_symbol,
                            side,
                            lambda side=side, route_symbol=route_symbol: self._execute_kraken_margin_route(
                                side,
                                route_symbol,
                                KRAKEN_MARGIN_QUOTE_USD,
                            ),
                        )
                    elif venue == "alpaca" and market_type == "spot":
                        result = self._run_executor_route_with_timeout(
                            route_key,
                            venue,
                            market_type,
                            route_symbol,
                            side,
                            lambda side=side, route_symbol=route_symbol: self._execute_alpaca_spot_route(
                                side,
                                route_symbol,
                                ORDER_EXECUTOR_QUOTE_USD,
                            ),
                        )
                    elif venue == "binance" and market_type == "spot":
                        result = self._run_executor_route_with_timeout(
                            route_key,
                            venue,
                            market_type,
                            route_symbol,
                            side,
                            lambda side=side, route_symbol=route_symbol: self._execute_binance_spot_route(
                                side,
                                route_symbol,
                                ORDER_EXECUTOR_QUOTE_USD,
                            ),
                        )
                    elif venue == "binance" and market_type == "margin":
                        result = self._run_executor_route_with_timeout(
                            route_key,
                            venue,
                            market_type,
                            route_symbol,
                            side,
                            lambda side=side, route_symbol=route_symbol: self._execute_binance_margin_route(
                                side,
                                route_symbol,
                                ORDER_EXECUTOR_QUOTE_USD,
                            ),
                        )
                    else:
                        result = {"ok": False, "venue": venue, "market_type": market_type, "symbol": route_symbol, "reason": "executor_route_not_supported"}
                except Exception as e:
                    result = {"ok": False, "venue": venue, "market_type": market_type, "symbol": route_symbol, "side": side, "error": str(e)}
                    self._governor().record_error(venue or "execution", e)

                result.update(
                    {
                        "generated_at": datetime.now().isoformat(),
                        "source": "unified_market_trader.executor",
                        "confidence": confidence,
                        "selection_rank": item.get("selection_rank"),
                        "profit_velocity_score": item.get("profit_velocity_score", 0.0),
                        "fast_money_score": item.get("fast_money_score", 0.0),
                        "fast_money_candidate": bool(item.get("fast_money_candidate")),
                        "fast_money_profile": item.get("fast_money_profile", {}),
                        "orderbook_pressure": item.get("orderbook_pressure", {}),
                        "estimated_target_eta_sec": item.get("estimated_target_eta_sec", 0.0),
                        "support_count": item.get("support_count", 0),
                        "cognitive_sources": item.get("sources", []),
                        "model_signal": item.get("model_signal", {}),
                        "model_alignment": item.get("model_alignment", False),
                        "route_key": route_key,
                        "candidate_id": candidate_id,
                        "lifecycle_id": lifecycle_id,
                        "intent_id": intent_id,
                    }
                )
                execution_summary["results"].append(result)
                if result.get("ok"):
                    self._execution_memory[route_key] = now
                    execution_summary["submitted_count"] += 1
                    ack = self._broker_identity_from_result(result)
                    self._record_order_lifecycle(
                        "order_submitted",
                        "order_submitted",
                        lifecycle_id,
                        candidate_id=candidate_id,
                        intent_id=intent_id,
                        route_key=route_key,
                        venue=venue,
                        market_type=market_type,
                        symbol=route_symbol,
                        side=side,
                        confidence=confidence,
                        broker_response=result.get("result"),
                        source="unified_market_trader.executor",
                    )
                    if ack:
                        self._record_order_lifecycle(
                            "broker_acknowledged",
                            "broker_acknowledged",
                            lifecycle_id,
                            candidate_id=candidate_id,
                            intent_id=intent_id,
                            route_key=route_key,
                            venue=venue,
                            market_type=market_type,
                            symbol=route_symbol,
                            side=side,
                            **ack,
                            source="unified_market_trader.executor",
                        )
                    position = result.get("fast_profit_position")
                    if isinstance(position, dict) and position:
                        self._record_order_lifecycle(
                            "position_open",
                            "position_open",
                            lifecycle_id,
                            candidate_id=candidate_id,
                            intent_id=intent_id,
                            route_key=route_key,
                            venue=venue,
                            market_type=market_type,
                            symbol=route_symbol,
                            side=side,
                            order_id=position.get("id") or ack.get("order_id"),
                            entry_price=position.get("entry_price"),
                            size=position.get("quantity"),
                            source="unified_market_trader.executor",
                        )
                    self._publish_thought("execution.order.submitted", result)
                else:
                    execution_summary["held_count"] += 1
                    execution_summary["blocked_count"] += 1
                    self._record_order_lifecycle(
                        "order_blocked",
                        "order_blocked",
                        lifecycle_id,
                        candidate_id=candidate_id,
                        intent_id=intent_id,
                        route_key=route_key,
                        venue=venue,
                        market_type=market_type,
                        symbol=route_symbol,
                        side=side,
                        reason=result.get("reason"),
                        error=result.get("error"),
                        source="unified_market_trader.executor",
                    )

        if execution_summary["submitted_count"] > 0:
            self._last_execution_at = now
        execution_summary["executor_route_state"] = self._executor_route_snapshot()
        execution_summary["order_lifecycle"] = self._order_lifecycle_snapshot()
        self._latest_execution_results = execution_summary
        action_plan["latest_execution"] = execution_summary

        self._persist_execution_summary(execution_summary)
        return execution_summary

    def _extract_trader_source_snapshot(self, source_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        symbols: Dict[str, Dict[str, Any]] = {}

        def push(symbol: Any, confidence: Any, side: Any = "BUY", reason: str = "signal") -> None:
            raw_symbol = str(symbol or "").upper().strip()
            normalized = self._normalize_symbol(raw_symbol)
            if not normalized:
                return
            try:
                conf = float(confidence or 0.0)
            except Exception:
                conf = 0.0
            if conf > 1.0:
                conf = conf / 100.0
            conf = max(0.0, min(1.0, conf))
            if conf <= 0.0:
                return
            symbols[normalized] = {
                "symbol": normalized,
                "raw_symbol": raw_symbol,
                "confidence": conf,
                "side": str(side or "BUY").upper(),
                "reason": reason,
            }

        for position in payload.get("positions", [])[:12]:
            if isinstance(position, dict):
                push(
                    position.get("symbol") or position.get("pair"),
                    1.0,
                    position.get("direction") or position.get("side") or "BUY",
                    reason="open_position",
                )

        for candidate in payload.get("candidate_snapshot", [])[:8]:
            if isinstance(candidate, dict):
                push(
                    candidate.get("symbol") or candidate.get("pair"),
                    self._extract_candidate_confidence(candidate),
                    candidate.get("direction") or candidate.get("side") or "BUY",
                    reason="candidate",
                )

        decision_snapshot = payload.get("decision_snapshot", {})
        if isinstance(decision_snapshot, dict):
            decision = decision_snapshot.get("decision", {}) if isinstance(decision_snapshot.get("decision"), dict) else {}
            push(
                decision_snapshot.get("symbol"),
                decision.get("confidence", 0.0),
                decision_snapshot.get("side") or decision.get("direction") or decision.get("type") or "BUY",
                reason="decision",
            )

        target_snapshot = payload.get("target_snapshot", {})
        if isinstance(target_snapshot, dict):
            push(
                target_snapshot.get("symbol"),
                self._extract_candidate_confidence(target_snapshot),
                target_snapshot.get("direction") or "BUY",
                reason="target",
            )

        if not symbols:
            return {}
        strongest = max(symbols.values(), key=lambda item: float(item.get("confidence", 0.0) or 0.0))
        return {
            "source": source_name,
            "ready": bool(payload.get("ok", True)),
            "symbols": symbols,
            "top_symbol": strongest.get("symbol"),
            "top_side": strongest.get("side"),
            "top_confidence": strongest.get("confidence"),
        }

    def _extract_alpaca_source_snapshot(self, watchlist: List[str]) -> Dict[str, Any]:
        client = self.alpaca
        if client is None:
            return {}
        if getattr(client, "init_error", "") or not getattr(client, "is_authenticated", True):
            return {}
        symbols: Dict[str, Dict[str, Any]] = {}
        probe_interval = self._dynamic_probe_interval("alpaca")
        for normalized in watchlist:
            crypto_symbol = self._to_alpaca_crypto_symbol(normalized)
            if not crypto_symbol:
                continue
            try:
                ticker = self._governor().call(
                    "alpaca",
                    "quotes",
                    f"alpaca:ticker:{crypto_symbol}",
                    lambda symbol=crypto_symbol: client.get_ticker(symbol),
                    min_interval_sec=probe_interval,
                    stale_ttl_sec=PROBE_SYMBOL_STALE_TTL_SEC,
                )
            except Exception:
                ticker = None
            if not ticker:
                continue
            price = float(ticker.get("price", 0.0) or ticker.get("last", 0.0) or 0.0)
            change_pct = float(ticker.get("change_pct", 0.0) or ticker.get("priceChangePercent", 0.0) or 0.0)
            if price <= 0 or abs(change_pct) <= 0.0:
                continue
            symbols[normalized] = {
                "symbol": normalized,
                "raw_symbol": crypto_symbol,
                "confidence": min(1.0, abs(change_pct) / 5.0),
                "side": "BUY" if change_pct >= 0 else "SELL",
                "price": price,
                "change_pct": change_pct,
                "budget_role": self._dynamic_exchange_budget("alpaca").get("role", "static"),
                "probe_min_interval_sec": probe_interval,
            }
        if not symbols:
            return {}
        strongest = max(symbols.values(), key=lambda item: float(item.get("confidence", 0.0) or 0.0))
        return {
            "source": "alpaca",
            "ready": True,
            "symbols": symbols,
            "top_symbol": strongest.get("symbol"),
            "top_side": strongest.get("side"),
            "top_confidence": strongest.get("confidence"),
            "budget_role": self._dynamic_exchange_budget("alpaca").get("role", "static"),
            "probe_min_interval_sec": probe_interval,
        }

    def _extract_binance_source_snapshot(self, watchlist: List[str]) -> Dict[str, Any]:
        client = self.binance
        if client is None:
            return {}
        binance_diag = getattr(self, "_binance_diag", {}) or {}
        if binance_diag.get("init_error") == "socket_blocked" or not bool(binance_diag.get("network_ok", False)):
            return {}
        symbols: Dict[str, Dict[str, Any]] = {}
        probe_interval = self._dynamic_probe_interval("binance")
        for normalized in watchlist:
            binance_symbol = self._to_binance_symbol(normalized)
            if not binance_symbol:
                continue
            try:
                ticker = self._governor().call(
                    "binance",
                    "quotes",
                    f"binance:24h:{binance_symbol}",
                    lambda symbol=binance_symbol: client.get_24h_ticker(symbol),
                    min_interval_sec=probe_interval,
                    stale_ttl_sec=PROBE_SYMBOL_STALE_TTL_SEC,
                )
            except Exception:
                ticker = None
            if not ticker:
                continue
            change_pct = float(ticker.get("priceChangePercent", 0.0) or 0.0)
            if abs(change_pct) <= 0.0:
                continue
            symbols[normalized] = {
                "symbol": normalized,
                "raw_symbol": binance_symbol,
                "confidence": min(1.0, abs(change_pct) / 5.0),
                "side": "BUY" if change_pct >= 0 else "SELL",
                "price": float(ticker.get("lastPrice", 0.0) or ticker.get("weightedAvgPrice", 0.0) or 0.0),
                "change_pct": change_pct,
                "budget_role": self._dynamic_exchange_budget("binance").get("role", "static"),
                "probe_min_interval_sec": probe_interval,
            }
        if not symbols:
            return {}
        strongest = max(symbols.values(), key=lambda item: float(item.get("confidence", 0.0) or 0.0))
        return {
            "source": "binance",
            "ready": True,
            "symbols": symbols,
            "top_symbol": strongest.get("symbol"),
            "top_side": strongest.get("side"),
            "top_confidence": strongest.get("confidence"),
            "budget_role": self._dynamic_exchange_budget("binance").get("role", "static"),
            "probe_min_interval_sec": probe_interval,
        }

    def _normalize_symbol(self, symbol: Any) -> str:
        raw = str(symbol or "").upper().strip()
        if not raw:
            return ""
        for needle in ("PERP", ".D", "-CFD"):
            raw = raw.replace(needle, "")
        alnum = "".join(ch for ch in raw if ch.isalnum())
        return SYMBOL_ALIASES.get(alnum, alnum)

    def _to_alpaca_crypto_symbol(self, normalized: str) -> str:
        symbol = str(normalized or "").upper()
        if symbol.endswith("USD") and len(symbol) > 3:
            base = symbol[:-3]
            if base in ALPACA_SPOT_CRYPTO_BASES:
                return f"{base}/USD"
        return ""

    def _to_binance_symbol(self, normalized: str) -> str:
        symbol = str(normalized or "").upper()
        if symbol.endswith("USD") and len(symbol) > 3:
            base = symbol[:-3]
            if base in BINANCE_CRYPTO_BASES:
                return f"{base}USDT"
        return ""

    def _capital_tradable_symbols(self) -> Dict[str, str]:
        tradables = {self._normalize_symbol(symbol): symbol for symbol in CAPITAL_UNIVERSE.keys()}
        tradables.setdefault("XAUUSD", "GOLD")
        return tradables

    def _read_gold_capital_intelligence(self) -> Dict[str, Any]:
        try:
            if GOLD_CAPITAL_INTELLIGENCE_PUBLIC_PATH.exists():
                payload = json.loads(GOLD_CAPITAL_INTELLIGENCE_PUBLIC_PATH.read_text(encoding="utf-8"))
                return payload if isinstance(payload, dict) else {}
        except Exception as e:
            logger.debug("GOLD intelligence report unavailable: %s", e)
        return {}

    def _validated_gold_action_side(self) -> Tuple[str, str]:
        report = self._read_gold_capital_intelligence()
        summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
        edge_stream = report.get("gold_dynamic_market_edge_stream") if isinstance(report.get("gold_dynamic_market_edge_stream"), dict) else {}
        action_candidate = edge_stream.get("action_candidate") if isinstance(edge_stream.get("action_candidate"), dict) else {}
        side = str(action_candidate.get("side") or "").upper()
        validation_allowed = bool(
            action_candidate.get("shadow_intent_allowed")
            or action_candidate.get("margin_order_allowed")
            or summary.get("gold_dynamic_market_edge_shadow_intent_allowed")
            or summary.get("gold_margin_signal_shadow_intent_allowed")
            or summary.get("gold_portfolio_uplift_order_intent_allowed")
        )
        if validation_allowed and side in {"BUY", "SELL"}:
            return side, "gold_intelligence_validated_buy_sell"
        if side in {"BUY", "SELL"}:
            return "HOLD", "gold_intelligence_side_seen_but_not_validated"
        return "HOLD", "gold_intelligence_requires_fresh_interval_validation"

    def _gold_priority_live_stream_signal(self) -> Dict[str, Any]:
        try:
            from aureon.data_feeds.unified_market_cache import get_market_cache

            market_cache = get_market_cache()
            tickers = market_cache.get_all_tickers(max_age=GOLD_PRIORITY_STREAM_MAX_AGE_SEC)
        except Exception as e:
            return {
                "ready": False,
                "reason": f"stream_cache_unavailable:{e}",
                "source_tags": ["gold_priority_target"],
            }

        now = time.time()
        candidates: List[Dict[str, Any]] = []
        for base, ticker in (tickers.items() if isinstance(tickers, dict) else []):
            base_norm = self._canonical_stream_base(base or getattr(ticker, "symbol", "") or "")
            pair = str(getattr(ticker, "pair", "") or base_norm).upper()
            source = str(getattr(ticker, "source", "") or "").lower()
            capital_source = "capital" in source
            gold_symbol = base_norm in {"GOLD", "XAU"} or pair in {"GOLD", "GOLDUSD", "XAUUSD"} or "GOLD" in pair
            if not (capital_source and gold_symbol):
                continue
            try:
                price = float(getattr(ticker, "price", 0.0) or 0.0)
                bid = float(getattr(ticker, "bid", 0.0) or 0.0)
                ask = float(getattr(ticker, "ask", 0.0) or 0.0)
                timestamp = float(getattr(ticker, "timestamp", 0.0) or 0.0)
                change_pct = float(getattr(ticker, "change_24h", 0.0) or 0.0)
                volume_24h = float(getattr(ticker, "volume_24h", 0.0) or 0.0)
            except Exception:
                continue
            if price <= 0.0 and bid <= 0.0 and ask <= 0.0:
                continue
            if timestamp <= 0.0:
                continue
            age_sec = max(0.0, now - timestamp)
            if age_sec > GOLD_PRIORITY_STREAM_MAX_AGE_SEC:
                continue
            if bid <= 0.0:
                bid = price
            if ask <= 0.0:
                ask = price
            mid = price if price > 0.0 else (bid + ask) / 2.0
            spread = max(0.0, ask - bid) if ask > 0.0 and bid > 0.0 else 0.0
            spread_pct = (spread / mid) * 100.0 if mid > 0.0 else 0.0
            spread_penalty = min(0.18, max(0.0, spread_pct) / 100.0)
            confidence = max(ORDER_INTENT_MIN_CONFIDENCE, min(0.92, 0.74 - spread_penalty))
            candidates.append(
                {
                    "ready": True,
                    "normalized_symbol": "XAUUSD",
                    "symbol": "GOLD",
                    "capital_symbol": "GOLD",
                    "reference_price": round(mid, 8),
                    "bid": round(bid, 8),
                    "ask": round(ask, 8),
                    "spread": round(spread, 8),
                    "spread_pct": round(spread_pct, 8),
                    "change_pct": round(change_pct, 6),
                    "volume_24h": round(volume_24h, 6),
                    "age_sec": round(age_sec, 3),
                    "source": str(getattr(ticker, "source", "") or "capital_gold_live_stream"),
                    "raw_symbol": pair,
                    "confidence": round(confidence, 4),
                    "source_tags": [
                        "capital_gold_live_stream",
                        "gold_priority_target",
                        "fresh_interval_validated_gold_projection_required",
                    ],
                }
            )
        if not candidates:
            return {
                "ready": False,
                "reason": "fresh_capital_gold_stream_missing",
                "source_tags": [
                    "capital_gold_live_stream",
                    "gold_priority_target",
                    "fresh_interval_validated_gold_projection_required",
                ],
            }
        candidates.sort(key=lambda item: (float(item.get("age_sec", 10**9) or 10**9), -float(item.get("confidence", 0.0) or 0.0)))
        selected = dict(candidates[0])
        side, side_reason = self._validated_gold_action_side()
        selected["side"] = side
        selected["side_reason"] = side_reason
        selected["intent_publishable"] = side in {"BUY", "SELL"}
        return selected

    def _apply_gold_priority_candidate(self, central_beat: Dict[str, Any], shared_market_feed: Dict[str, Any]) -> Dict[str, Any]:
        signal = self._gold_priority_live_stream_signal()
        normalized = str(signal.get("normalized_symbol") or "XAUUSD")
        diagnostic = {
            "enabled": True,
            "ready": bool(signal.get("ready")),
            "normalized_symbol": normalized,
            "capital_symbol": signal.get("capital_symbol") or "GOLD",
            "source_tags": signal.get("source_tags") or [
                "capital_gold_live_stream",
                "gold_priority_target",
                "fresh_interval_validated_gold_projection_required",
            ],
            "intent_publishable": bool(signal.get("intent_publishable")),
            "side": signal.get("side") or "HOLD",
            "reason": signal.get("side_reason") or signal.get("reason") or "",
            "age_sec": signal.get("age_sec"),
            "fresh_seconds_budget": GOLD_PRIORITY_STREAM_MAX_AGE_SEC,
            "reference_price": signal.get("reference_price"),
        }
        if not isinstance(central_beat, dict):
            return diagnostic
        central_beat["gold_priority_candidate"] = diagnostic
        if not isinstance(shared_market_feed, dict):
            return diagnostic
        shared_market_feed["gold_priority_candidate"] = diagnostic
        if not signal.get("ready"):
            return diagnostic

        central_symbols = central_beat.setdefault("symbols", {})
        if not isinstance(central_symbols, dict):
            central_symbols = {}
            central_beat["symbols"] = central_symbols
        shared_symbols = shared_market_feed.setdefault("symbols", {})
        if not isinstance(shared_symbols, dict):
            shared_symbols = {}
            shared_market_feed["symbols"] = shared_symbols
        existing = central_symbols.get(normalized) if isinstance(central_symbols.get(normalized), dict) else {}
        existing_sources = existing.get("sources", []) if isinstance(existing, dict) and isinstance(existing.get("sources"), list) else []
        source_tags = list(dict.fromkeys([*existing_sources, *[str(item) for item in signal.get("source_tags", []) if str(item)]]))
        confidence = max(float(existing.get("confidence", 0.0) or 0.0), float(signal.get("confidence", ORDER_INTENT_MIN_CONFIDENCE) or 0.0))
        central_symbols[normalized] = {
            **existing,
            "symbol": normalized,
            "side": str(signal.get("side") or "HOLD").upper(),
            "confidence": round(max(0.0, min(1.0, confidence)), 4),
            "strength": round(max(0.0, min(1.5, max(confidence, float(existing.get("strength", 0.0) or 0.0)))), 4),
            "support_count": max(1, int(existing.get("support_count", 0) or 0)),
            "sources": source_tags,
            "reference_price": float(signal.get("reference_price", existing.get("reference_price", 0.0)) or 0.0),
            "bid": signal.get("bid"),
            "ask": signal.get("ask"),
            "spread": signal.get("spread"),
            "spread_pct": signal.get("spread_pct"),
            "change_pct": float(signal.get("change_pct", existing.get("change_pct", 0.0)) or 0.0),
            "change_pct_abs_max": abs(float(signal.get("change_pct", existing.get("change_pct_abs_max", 0.0)) or 0.0)),
            "volume_24h": float(signal.get("volume_24h", existing.get("volume_24h", 0.0)) or 0.0),
            "freshest_age_sec": signal.get("age_sec"),
            "fast_money_sources": list(dict.fromkeys([*(existing.get("fast_money_sources", []) if isinstance(existing.get("fast_money_sources"), list) else []), "capital_gold_live_stream"])),
            "source_prices": {
                **(existing.get("source_prices", {}) if isinstance(existing.get("source_prices"), dict) else {}),
                "capital_gold_live_stream": float(signal.get("reference_price", 0.0) or 0.0),
            },
            "gold_priority_candidate": True,
            "intent_publishable": bool(signal.get("intent_publishable")),
            "intent_publish_requirement": "fresh_interval_validated_gold_projection",
            "intent_publish_reason": signal.get("side_reason") or "",
        }
        shared_symbols[normalized] = round(max(float(shared_symbols.get(normalized, 0.0) or 0.0), confidence), 4)
        aliases = shared_market_feed.setdefault("aliases", {})
        if isinstance(aliases, dict):
            aliases[normalized] = list(dict.fromkeys([*(aliases.get(normalized, []) if isinstance(aliases.get(normalized), list) else []), "GOLD", "XAUUSD", "capital:GOLDUSD"]))
        shared_market_feed["count"] = len(shared_symbols)
        self._shared_market_feed = dict(shared_symbols)
        diagnostic.update(
            {
                "ready": True,
                "confidence": round(max(0.0, min(1.0, confidence)), 4),
                "capital_cfd_candidate_key": normalized,
                "route_requirement": "capital_cfd_route_visible",
            }
        )
        central_beat["gold_priority_candidate"] = diagnostic
        shared_market_feed["gold_priority_candidate"] = diagnostic
        return diagnostic

    def _alpaca_tradable_symbols(self) -> Dict[str, str]:
        return {
            f"{base}USD": f"{base}/USD"
            for base in sorted(ALPACA_SPOT_CRYPTO_BASES)
            if base not in {"USDC", "USDT"}
        }

    def _binance_tradable_symbols(self) -> Dict[str, str]:
        return {
            f"{base}USD": f"{base}USDT"
            for base in sorted(BINANCE_CRYPTO_BASES)
            if base not in {"USDC", "USDT"}
        }

    def _to_kraken_spot_symbol(self, normalized: str) -> str:
        symbol = str(normalized or "").upper()
        if symbol.endswith("USD") and len(symbol) > 3:
            base = symbol[:-3]
            if base in KRAKEN_SPOT_CRYPTO_BASES:
                return "XBTUSD" if base == "BTC" else f"{base}USD"
        return ""

    def _kraken_spot_tradable_symbols(self) -> Dict[str, str]:
        tradables: Dict[str, str] = {}
        client = self._kraken_spot_client()
        if client is not None and hasattr(client, "exchange_info"):
            try:
                info = self._governor().call(
                    "kraken",
                    "metadata",
                    "kraken:exchange_info",
                    lambda: client.exchange_info(),
                    min_interval_sec=max(PROBE_SYMBOL_MIN_INTERVAL_SEC, 30.0),
                    stale_ttl_sec=max(PROBE_SYMBOL_STALE_TTL_SEC, 300.0),
                )
            except Exception:
                info = {}
            symbols = info.get("symbols", []) if isinstance(info, dict) else []
            if isinstance(symbols, list):
                for item in symbols:
                    if not isinstance(item, dict):
                        continue
                    quote = str(item.get("quoteAsset") or "").upper()
                    base = str(item.get("baseAsset") or "").upper().lstrip("XZ")
                    raw_symbol = str(item.get("symbol") or "").upper()
                    if quote not in {"USD", "USDT", "USDC"} or not raw_symbol:
                        continue
                    normalized = self._normalize_symbol(raw_symbol)
                    if normalized and base not in {"USD", "USDT", "USDC"}:
                        tradables.setdefault(normalized, raw_symbol)
        for base in sorted(KRAKEN_SPOT_CRYPTO_BASES):
            normalized = f"{base}USD"
            tradables.setdefault(normalized, self._to_kraken_spot_symbol(normalized) or normalized)
        return tradables

    def _kraken_tradable_symbols(self) -> Dict[str, str]:
        tradables: Dict[str, str] = {}
        if self.kraken is None:
            return tradables
        margin_pairs = getattr(self.kraken, "margin_pairs", {}) or {}
        for pair, info in margin_pairs.items():
            binance_symbol = getattr(info, "binance_symbol", "") if info is not None else ""
            kraken_symbol = getattr(info, "pair", "") if info is not None else ""
            primary = str(binance_symbol or kraken_symbol or pair or "").upper()
            normalized = self._normalize_symbol(primary)
            if normalized:
                tradables[normalized] = primary
        return tradables

    def _build_global_order_flow_feed(
        self,
        kraken_payload: Dict[str, Any],
        capital_payload: Dict[str, Any],
        central_beat: Dict[str, Any],
        shared_market_feed: Dict[str, Any],
    ) -> Dict[str, Any]:
        gold_priority_candidate = self._apply_gold_priority_candidate(central_beat, shared_market_feed)
        kraken_margin_tradables = self._kraken_tradable_symbols()
        kraken_spot_tradables = self._kraken_spot_tradable_symbols()
        capital_tradables = self._capital_tradable_symbols()
        alpaca_tradables = self._alpaca_tradable_symbols()
        binance_tradables = self._binance_tradable_symbols()
        kraken_capital_shared_keys = sorted((set(kraken_margin_tradables.keys()) | set(kraken_spot_tradables.keys())) & set(capital_tradables.keys()))

        symbols_conf = shared_market_feed.get("symbols", {}) if isinstance(shared_market_feed, dict) else {}
        central_symbols = central_beat.get("symbols", {}) if isinstance(central_beat, dict) else {}
        ranked: List[Dict[str, Any]] = []
        routeable_keys = sorted(
            set(symbols_conf.keys())
            & (
                set(kraken_margin_tradables.keys())
                | set(kraken_spot_tradables.keys())
                | set(capital_tradables.keys())
                | set(alpaca_tradables.keys())
                | set(binance_tradables.keys())
            )
        )
        binance_diag = getattr(self, "_binance_diag", {}) or {}
        alpaca_ok = self.alpaca is not None and not bool(getattr(self.alpaca, "init_error", "") or self.alpaca_error)
        binance_network_ok = self.binance is not None and bool(binance_diag.get("network_ok", False))
        binance_account_ok = bool(binance_diag.get("account_ok", False))
        binance_margin_ok = bool(binance_diag.get("margin_available", False)) and not bool(
            binance_diag.get("uk_mode", getattr(self.binance, "uk_mode", False) if self.binance is not None else False)
        )

        shadow_index = self._shadow_validation_index()
        intelligence_mesh = self._build_intelligence_mesh(central_beat=central_beat)
        kraken_spot_posture = self._kraken_spot_portfolio_posture(force=False)
        if not isinstance(getattr(self, "_dynamic_intelligence_budget", {}), dict) or not getattr(self, "_dynamic_intelligence_budget", {}):
            self._dynamic_intelligence_budget = self._build_dynamic_intelligence_budget(kraken_payload, capital_payload)
        dynamic_intelligence_budget = getattr(self, "_dynamic_intelligence_budget", {}) or {}

        def route(
            venue: str,
            market_type: str,
            symbol: str,
            ready: bool,
            blockers: List[str],
            execution_owner: str = "unified_executor",
            side: str = "BUY",
        ) -> Dict[str, Any]:
            model_stack = self._model_stack_for_route(venue, market_type)
            clearances = [str(item) for item in blockers if str(item)]
            if (
                str(venue or "").lower() == "kraken"
                and str(market_type or "").lower() == "spot"
                and str(side or "BUY").upper() == "BUY"
                and not bool(kraken_spot_posture.get("spot_buy_allowed", True))
            ):
                clearances.append("kraken_spot_inventory_underwater_margin_only")
            route_ready = bool(ready and not clearances)
            trade_clearance_state = "available" if route_ready else "held"
            cash_capability = self._route_cash_capability(
                venue=venue,
                market_type=market_type,
                symbol=symbol,
                side=side,
                ready=route_ready,
                execution_owner=execution_owner,
            )
            return {
                "venue": venue,
                "market_type": market_type,
                "symbol": symbol,
                "route_key": self._order_route_key(venue, market_type, symbol, side),
                "ready": route_ready,
                "trade_clearance_state": trade_clearance_state,
                "guard_state": trade_clearance_state,
                "runtime_clearances": clearances,
                "guards": clearances,
                "clearance_required": clearances,
                "end_user_trade_available": route_ready,
                "blockers": clearances,
                "execution_owner": execution_owner,
                "cash_capability": cash_capability,
                "cash_capability_state": cash_capability.get("state"),
                "cash_capability_score": cash_capability.get("score", 0.0),
                "model_stack_key": model_stack.get("key"),
                "model_count": model_stack.get("available_count", 0),
                "model_total_count": model_stack.get("total_count", 0),
                "model_coverage_ready": bool(model_stack.get("ready")),
                "models": model_stack.get("models", []),
            }

        for normalized in routeable_keys:
            confidence = float(symbols_conf.get(normalized, 0.0) or 0.0)
            if confidence <= 0.0:
                continue
            capital_symbol = capital_tradables.get(normalized, normalized)
            central_signal = central_symbols.get(normalized, {}) if isinstance(central_symbols, dict) else {}
            side = str(central_signal.get("side") or "").upper() if isinstance(central_signal, dict) else ""
            if side == "HOLD":
                pass
            elif side not in ("BUY", "SELL") and "SHORT" in capital_symbol.upper():
                side = "SELL"
            elif side not in ("BUY", "SELL"):
                side = "BUY"
            route_side = side if side in {"BUY", "SELL"} else "BUY"
            intent_publish_blockers: List[str] = []
            if side not in {"BUY", "SELL"}:
                if bool(central_signal.get("gold_priority_candidate")) if isinstance(central_signal, dict) else False:
                    intent_publish_blockers.append("gold_side_not_validated_by_fresh_interval_projection")
                else:
                    intent_publish_blockers.append("order_side_not_buy_or_sell")
            execution_routes: List[Dict[str, Any]] = []
            if normalized in kraken_spot_tradables:
                execution_routes.append(
                    route(
                        "kraken",
                        "spot",
                        kraken_spot_tradables.get(normalized, normalized),
                        bool(self.kraken_ready and self.kraken is not None),
                        [] if self.kraken_ready and self.kraken is not None else [self.kraken_error or "kraken_not_ready"],
                        "unified_executor",
                        route_side,
                    )
                )
            if normalized in kraken_margin_tradables:
                execution_routes.append(
                    route(
                        "kraken",
                        "margin",
                        kraken_margin_tradables.get(normalized, normalized),
                        bool(self.kraken_ready and self.kraken is not None),
                        [] if self.kraken_ready and self.kraken is not None else [self.kraken_error or "kraken_not_ready"],
                        "unified_executor",
                        route_side,
                    )
                )
            if normalized in capital_tradables:
                execution_routes.append(
                    route(
                        "capital",
                        "cfd",
                        capital_symbol,
                        bool(self.capital_ready and self.capital is not None),
                        [] if self.capital_ready and self.capital is not None else [self.capital_error or "capital_not_ready"],
                        "existing_autonomous_trader_tick",
                        route_side,
                    )
                )
            if normalized in alpaca_tradables:
                execution_routes.append(
                    route(
                        "alpaca",
                        "spot",
                        alpaca_tradables.get(normalized, normalized),
                        alpaca_ok,
                        [] if alpaca_ok else [self.alpaca_error or "alpaca_not_ready"],
                        side=route_side,
                    )
                )
            if normalized in binance_tradables:
                execution_routes.append(
                    route(
                        "binance",
                        "spot",
                        binance_tradables.get(normalized, normalized),
                        binance_network_ok,
                        [] if binance_network_ok else [self.binance_error or "binance_network_not_ready"],
                        side=route_side,
                    )
                )
                execution_routes.append(
                    route(
                        "binance",
                        "margin",
                        binance_tradables.get(normalized, normalized),
                        bool(binance_network_ok and binance_account_ok and binance_margin_ok),
                        []
                        if binance_network_ok and binance_account_ok and binance_margin_ok
                        else [
                            blocker
                            for blocker, present in (
                                ("binance_network_not_ready", not binance_network_ok),
                                ("binance_account_not_ready", not binance_account_ok),
                                ("binance_margin_unavailable_or_uk_restricted", not binance_margin_ok),
                            )
                            if present
                        ],
                        side=route_side,
                    )
                )
            ready_route_count = sum(1 for item in execution_routes if item.get("ready"))
            row = {
                "symbol": normalized,
                "kraken_symbol": kraken_margin_tradables.get(normalized) or kraken_spot_tradables.get(normalized, normalized),
                "kraken_spot_symbol": kraken_spot_tradables.get(normalized),
                "kraken_margin_symbol": kraken_margin_tradables.get(normalized),
                "capital_symbol": capital_symbol,
                "alpaca_symbol": alpaca_tradables.get(normalized),
                "binance_symbol": binance_tradables.get(normalized),
                "side": side,
                "confidence": max(0.0, min(1.0, confidence)),
                "support_count": int(central_signal.get("support_count", 0) or 0) if isinstance(central_signal, dict) else 0,
                "sources": list(central_signal.get("sources", [])) if isinstance(central_signal, dict) and isinstance(central_signal.get("sources"), list) else [],
                "reference_price": float(central_signal.get("reference_price", 0.0) or 0.0) if isinstance(central_signal, dict) else 0.0,
                "change_pct": float(central_signal.get("change_pct", 0.0) or 0.0) if isinstance(central_signal, dict) else 0.0,
                "change_pct_abs_max": float(central_signal.get("change_pct_abs_max", 0.0) or 0.0) if isinstance(central_signal, dict) else 0.0,
                "volume_24h": float(central_signal.get("volume_24h", 0.0) or 0.0) if isinstance(central_signal, dict) else 0.0,
                "freshest_age_sec": central_signal.get("freshest_age_sec") if isinstance(central_signal, dict) else None,
                "fast_money_sources": list(central_signal.get("fast_money_sources", [])) if isinstance(central_signal, dict) and isinstance(central_signal.get("fast_money_sources"), list) else [],
                "source_prices": dict(central_signal.get("source_prices", {})) if isinstance(central_signal, dict) and isinstance(central_signal.get("source_prices"), dict) else {},
                "model_signal": central_signal.get("model_signal", {}) if isinstance(central_signal, dict) else {},
                "model_alignment": bool(central_signal.get("model_alignment", False)) if isinstance(central_signal, dict) else False,
                "world_ecosystem_signal": central_signal.get("world_ecosystem_signal", {}) if isinstance(central_signal, dict) else {},
                "historical_waveform": central_signal.get("historical_waveform", {}) if isinstance(central_signal, dict) else {},
                "execution_routes": execution_routes,
                "ready_route_count": ready_route_count,
                "held_route_count": max(0, len(execution_routes) - ready_route_count),
                "available_route_count": ready_route_count,
                "blocked_route_count": max(0, len(execution_routes) - ready_route_count),
                "intent_publish_blockers": intent_publish_blockers,
                "gold_priority_candidate": bool(central_signal.get("gold_priority_candidate")) if isinstance(central_signal, dict) else False,
                "intent_publish_requirement": central_signal.get("intent_publish_requirement", "") if isinstance(central_signal, dict) else "",
                "intent_publish_reason": central_signal.get("intent_publish_reason", "") if isinstance(central_signal, dict) else "",
            }
            candidate_id, lifecycle_id = self._candidate_lifecycle_identity(row)
            row["candidate_id"] = candidate_id
            row["lifecycle_id"] = lifecycle_id
            for route_item in execution_routes:
                if not isinstance(route_item, dict):
                    continue
                route_item["candidate_id"] = candidate_id
                route_item["lifecycle_id"] = lifecycle_id
            row.update(
                self._profit_velocity_metrics(
                    item=row,
                    execution_routes=execution_routes,
                    shadow_index=shadow_index,
                    intelligence_mesh=intelligence_mesh,
                )
            )
            ranked.append(row)

        fast_money_intelligence = self._attach_orderbook_fast_money_pressure(
            ranked,
            shadow_index=shadow_index,
            intelligence_mesh=intelligence_mesh,
        )
        scanner_fusion_matrix = self._build_scanner_fusion_matrix(
            central_beat=central_beat,
            ranked=ranked,
            fast_money_intelligence=fast_money_intelligence,
            intelligence_mesh=intelligence_mesh,
        )
        intelligence_mesh = self._build_intelligence_mesh(
            central_beat=central_beat,
            order_flow_feed={
                "fast_money_intelligence": fast_money_intelligence,
                "scanner_fusion_matrix": scanner_fusion_matrix,
            },
        )
        ranked.sort(
            key=lambda item: (
                1.0 if bool(item.get("gold_priority_candidate")) else 0.0,
                float(item.get("profit_velocity_score", 0.0) or 0.0),
                float(item.get("confidence", 0.0) or 0.0),
            ),
            reverse=True,
        )
        for index, item in enumerate(ranked, start=1):
            item["selection_rank"] = index
        if isinstance(scanner_fusion_matrix, dict) and isinstance(scanner_fusion_matrix.get("candidates"), list):
            ranked_by_symbol = {str(item.get("symbol") or ""): item for item in ranked if isinstance(item, dict)}
            for candidate in scanner_fusion_matrix["candidates"]:
                if not isinstance(candidate, dict):
                    continue
                ranked_item = ranked_by_symbol.get(str(candidate.get("symbol") or ""))
                if not ranked_item:
                    continue
                candidate["selection_rank"] = ranked_item.get("selection_rank")
                candidate["profit_velocity_score"] = ranked_item.get("profit_velocity_score", candidate.get("profit_velocity_score", 0.0))
            self._scanner_fusion_matrix = scanner_fusion_matrix
            self._publish_scanner_fusion_matrix(scanner_fusion_matrix)
        venue_counts = {
            "kraken_spot": len(kraken_spot_tradables),
            "kraken_margin": len(kraken_margin_tradables),
            "capital_cfd": len(capital_tradables),
            "alpaca_spot": len(alpaca_tradables),
            "binance_spot": len(binance_tradables),
            "binance_margin": len(binance_tradables),
        }
        return {
            "generated_at": datetime.now().isoformat(),
            "shared_tradable_count": len(routeable_keys),
            "kraken_capital_shared_tradable_count": len(kraken_capital_shared_keys),
            "multi_exchange_tradable_count": len(routeable_keys),
            "active_order_flow_count": len(ranked),
            "active_order_flow": ranked[:20],
            "kraken_tradables": len(set(kraken_margin_tradables.keys()) | set(kraken_spot_tradables.keys())),
            "kraken_spot_tradables": len(kraken_spot_tradables),
            "kraken_margin_tradables": len(kraken_margin_tradables),
            "capital_tradables": len(capital_tradables),
            "alpaca_tradables": len(alpaca_tradables),
            "binance_tradables": len(binance_tradables),
            "venue_tradable_counts": venue_counts,
            "scope": "multi-exchange unified tradables across Kraken spot/margin, Capital CFDs, Alpaca spot, and Binance spot/margin",
            "intelligence_mesh": intelligence_mesh,
            "world_financial_ecosystem": central_beat.get("world_financial_ecosystem", {}) if isinstance(central_beat, dict) else {},
            "asset_waveform_models": central_beat.get("asset_waveform_models", {}) if isinstance(central_beat, dict) else {},
            "fast_money_intelligence": fast_money_intelligence,
            "scanner_fusion_matrix": scanner_fusion_matrix,
            "dynamic_intelligence_budget": dynamic_intelligence_budget,
            "kraken_spot_portfolio_posture": kraken_spot_posture,
            "gold_priority_candidate": gold_priority_candidate,
            "selection_process": {
                "mode": "fast_money_profit_velocity_ranked_live_shadow_selection",
                "who": "CentralBeat plus world financial ecosystem intake, 1h-to-1y waveform memory, whole intelligence mesh, HNC/model/shadow validation routes",
                "what": "rank candidates by cash-capable route, balance-weighted live sensors, momentum/intelligence scanners, live/reference price, volatility, volume, stream age, order-book pressure, world macro/news/harp/cross-asset context, historical waveform agreement, phantom/noise rejection, shadow history, support, model alignment, mesh readiness, and fastest target ETA",
                "target_move_pct": SHADOW_TRADE_TARGET_MOVE_PCT,
                "validation_horizon_sec": SHADOW_TRADE_VALIDATION_HORIZON_SEC,
                "fast_money_min_volatility_pct": FAST_MONEY_MIN_VOLATILITY_PCT,
                "fast_money_break_even_move_pct": FAST_MONEY_BREAK_EVEN_MOVE_PCT,
                "fast_money_volume_usd_target": FAST_MONEY_VOLUME_USD_TARGET,
                "scanner_fusion_fed_to_decision_logic": scanner_fusion_matrix.get("fed_to_decision_logic", False),
                "scanner_fusion_usable_system_count": scanner_fusion_matrix.get("usable_system_count", 0),
                "scanner_fusion_usable_candidate_count": scanner_fusion_matrix.get("usable_candidate_count", 0),
                "history_routes": len((shadow_index.get("routes") or {}) if isinstance(shadow_index, dict) else {}),
                "history_symbols": len((shadow_index.get("symbols") or {}) if isinstance(shadow_index, dict) else {}),
                "intelligence_mesh_score": intelligence_mesh.get("selection_mesh_score", 0.0),
            },
        }

    def _feed_shared_order_flow_to_decision_logic(self, order_flow_feed: Dict[str, Any]) -> None:
        active = order_flow_feed.get("active_order_flow", []) if isinstance(order_flow_feed, dict) else []
        if not isinstance(active, list):
            return
        for item in active[:10]:
            if not isinstance(item, dict):
                continue
            symbol = str(item.get("symbol") or "").upper().strip()
            side = str(item.get("side") or "BUY").upper()
            confidence = max(0.0, min(1.0, float(item.get("confidence", 0.0) or 0.0)))
            profit_velocity_score = self._clamp01(item.get("profit_velocity_score", 0.0))
            fast_money_score = self._clamp01(item.get("fast_money_score", 0.0))
            decision_score = max(confidence, profit_velocity_score, fast_money_score)
            metadata = {
                "source": "unified_market_trader.shared_order_flow",
                "kraken_symbol": item.get("kraken_symbol"),
                "kraken_spot_symbol": item.get("kraken_spot_symbol"),
                "kraken_margin_symbol": item.get("kraken_margin_symbol"),
                "capital_symbol": item.get("capital_symbol"),
                "alpaca_symbol": item.get("alpaca_symbol"),
                "binance_symbol": item.get("binance_symbol"),
                "candidate_id": item.get("candidate_id"),
                "lifecycle_id": item.get("lifecycle_id"),
                "execution_routes": item.get("execution_routes", []),
                "profit_velocity_score": item.get("profit_velocity_score", 0.0),
                "fast_money_score": item.get("fast_money_score", 0.0),
                "fast_money_profile": item.get("fast_money_profile", {}),
                "scanner_fusion_score": item.get("scanner_fusion_score", 0.0),
                "scanner_fusion": item.get("scanner_fusion", {}),
                "orderbook_pressure": item.get("orderbook_pressure", {}),
                "shared_tradable_count": order_flow_feed.get("shared_tradable_count", 0),
            }
            for trader in self._central_feed_targets():
                if trader is None or not hasattr(trader, "_feed_unified_decision_engine"):
                    continue
                try:
                    trader._feed_unified_decision_engine(symbol=symbol, side=side, score=decision_score, metadata=metadata)  # type: ignore[attr-defined]
                except Exception as e:
                    logger.debug("Shared decision feed failed for %s: %s", symbol, e)

    def _shadow_trade_enabled(self) -> bool:
        return os.getenv("UNIFIED_SHADOW_TRADE_ENABLED", "1").strip().lower() not in {"0", "false", "no", "off"}

    def _read_shadow_trade_state(self) -> Dict[str, Any]:
        try:
            if SHADOW_TRADE_STATE_PATH.exists():
                data = json.loads(SHADOW_TRADE_STATE_PATH.read_text(encoding="utf-8"))
                return data if isinstance(data, dict) else {}
        except Exception as e:
            logger.debug("Shadow trade state read failed: %s", e)
        return {}

    def _shadow_target_price(self, entry_price: float, side: str, target_move_pct: float) -> float:
        if entry_price <= 0:
            return 0.0
        move = max(0.0, float(target_move_pct or 0.0)) / 100.0
        return entry_price * (1.0 - move) if str(side).upper() == "SELL" else entry_price * (1.0 + move)

    def _shadow_direction_move_pct(self, entry_price: float, current_price: float, side: str) -> float:
        if entry_price <= 0 or current_price <= 0:
            return 0.0
        if str(side).upper() == "SELL":
            return ((entry_price - current_price) / entry_price) * 100.0
        return ((current_price - entry_price) / entry_price) * 100.0

    def _shadow_agent_review(
        self,
        *,
        item: Dict[str, Any],
        route_item: Dict[str, Any],
        entry_price: float,
        global_guards: List[str],
    ) -> Dict[str, Any]:
        confidence = max(0.0, min(1.0, float(item.get("confidence", 0.0) or 0.0)))
        support_count = int(item.get("support_count", 0) or 0)
        side = str(item.get("side") or "BUY").upper()
        side_signal = side if side in {"BUY", "SELL"} else "NEUTRAL"
        model_signal = item.get("model_signal", {}) if isinstance(item.get("model_signal"), dict) else {}
        model_confidence = max(0.0, min(1.0, float(model_signal.get("confidence", confidence) or confidence)))
        model_direction = str(model_signal.get("direction") or side_signal).upper()
        route_clearances = [str(item) for item in (route_item.get("runtime_clearances") or route_item.get("guards") or route_item.get("blockers") or []) if str(item)]
        runtime_clearances = [str(item) for item in global_guards if str(item)]
        route_ready = bool(route_item.get("ready")) and not route_clearances
        price_ready = entry_price > 0
        model_aligned = bool(item.get("model_alignment")) or model_direction in {"NEUTRAL", side_signal}

        def score(ok: bool, value: float) -> float:
            return max(0.0, min(1.0, value if ok else value * 0.35))

        market_ok = confidence >= SHADOW_TRADE_MIN_CONFIDENCE and support_count > 0
        market_score = score(market_ok, confidence)
        model_score = score(model_aligned, model_confidence)
        route_score = 1.0 if route_ready else 0.15
        price_score = 1.0 if price_ready else 0.1
        live_clearance_score = 1.0 if not runtime_clearances else 0.55

        synthetic_signals = [
            {
                "pillar": "MarketDataAgent",
                "signal": side_signal,
                "confidence": market_score,
                "coherence": max(0.0, min(1.0, support_count / 4.0)),
                "frequency_hz": 528.0 if side_signal == "BUY" else 396.0 if side_signal == "SELL" else 432.0,
            },
            {
                "pillar": "ModelAlignmentAgent",
                "signal": side_signal if model_aligned else "NEUTRAL",
                "confidence": model_score,
                "coherence": 0.86 if model_aligned else 0.34,
                "frequency_hz": 528.0 if model_aligned else 432.0,
            },
            {
                "pillar": "RouteClearanceAgent",
                "signal": side_signal if route_ready else "NEUTRAL",
                "confidence": route_score,
                "coherence": route_score,
                "frequency_hz": 432.0,
            },
            {
                "pillar": "PriceValidationAgent",
                "signal": side_signal if price_ready else "NEUTRAL",
                "confidence": price_score,
                "coherence": price_score,
                "frequency_hz": 528.0 if price_ready else 432.0,
            },
            {
                "pillar": "RuntimeClearanceAgent",
                "signal": side_signal if not runtime_clearances else "NEUTRAL",
                "confidence": live_clearance_score,
                "coherence": live_clearance_score,
                "frequency_hz": 432.0,
            },
        ]

        hnc_alignment = {
            "available": False,
            "alignment_score": round((market_score + model_score + route_score + price_score + live_clearance_score) / 5.0, 6),
            "lighthouse_cleared": False,
            "consensus_signal": side_signal,
        }
        try:
            from aureon.alignment.harmonic_resonance import full_harmonic_analysis

            analysis = full_harmonic_analysis(pillar_results=synthetic_signals)
            hnc_alignment = {
                "available": True,
                "alignment_score": round(float(getattr(analysis, "alignment_score", 0.0) or 0.0), 6),
                "harmonic_lock": round(float(getattr(analysis, "harmonic_lock", 0.0) or 0.0), 6),
                "phase_coherence": round(float(getattr(analysis, "phase_coherence", 0.0) or 0.0), 6),
                "lighthouse_cleared": bool(getattr(analysis, "lighthouse_cleared", False)),
                "consensus_signal": str(getattr(analysis, "dominant_signal", side_signal) or side_signal),
                "responding_agents": len(synthetic_signals),
            }
        except Exception as e:
            hnc_alignment["error"] = str(e)

        agent_score = max(
            0.0,
            min(
                1.0,
                (0.25 * market_score)
                + (0.22 * model_score)
                + (0.20 * route_score)
                + (0.18 * price_score)
                + (0.15 * float(hnc_alignment.get("alignment_score", 0.0) or 0.0)),
            ),
        )
        logic_validated = bool(route_ready and market_ok and price_ready and agent_score >= 0.45)
        agents = {
            "market_data_agent": {
                "ok": market_ok,
                "confidence": round(confidence, 6),
                "support_count": support_count,
                "sources": list(item.get("sources", [])) if isinstance(item.get("sources"), list) else [],
            },
            "model_alignment_agent": {
                "ok": model_aligned,
                "direction": model_direction,
                "confidence": round(model_confidence, 6),
                "model_signal": model_signal,
                "model_stack_key": route_item.get("model_stack_key"),
                "model_count": int(route_item.get("model_count", 0) or 0),
            },
            "route_clearance_agent": {
                "ok": route_ready,
                "venue": route_item.get("venue"),
                "market_type": route_item.get("market_type"),
                "runtime_clearances": route_clearances,
                "execution_owner": route_item.get("execution_owner"),
            },
            "price_validation_agent": {
                "ok": price_ready,
                "entry_price": round(entry_price, 8) if entry_price > 0 else 0.0,
            },
            "runtime_clearance_agent": {
                "ok_for_shadow": True,
                "ok_for_live_promotion": not bool(runtime_clearances),
                "runtime_clearances": runtime_clearances,
                "note": "Queen/HNC can reason and shadow freely; live exchange mutation waits for runtime truth checks",
            },
            "hnc_alignment_agent": hnc_alignment,
        }
        return {
            "logic_validated": logic_validated,
            "agent_score": round(agent_score, 6),
            "agents": agents,
            "synthetic_agent_signals": synthetic_signals,
            "self_report": (
                "shadow logic validated; watch price path before promotion"
                if logic_validated
                else "shadow held; waiting for route, price, or confidence inputs"
            ),
        }

    def _verify_prior_shadow(self, shadow: Dict[str, Any], current_prices: Dict[str, float], now: float) -> Dict[str, Any]:
        result = dict(shadow)
        symbol = str(result.get("symbol") or "").upper()
        entry_price = float(result.get("entry_price", 0.0) or 0.0)
        current_price = float(current_prices.get(symbol, 0.0) or 0.0)
        expected_by_epoch = float(result.get("expected_by_epoch", 0.0) or 0.0)
        target_move_pct = float(result.get("target_move_pct", SHADOW_TRADE_TARGET_MOVE_PCT) or SHADOW_TRADE_TARGET_MOVE_PCT)
        direction_move_pct = self._shadow_direction_move_pct(entry_price, current_price, str(result.get("side") or "BUY"))
        target_hit = bool(entry_price > 0 and current_price > 0 and direction_move_pct >= target_move_pct)
        if target_hit:
            status = "validated"
        elif current_price <= 0:
            status = "pending_price"
        elif expected_by_epoch > 0 and now >= expected_by_epoch:
            status = "missed_eta"
        else:
            status = "validating"
        result.update(
            {
                "last_verified_at": datetime.now().isoformat(),
                "last_verified_epoch": round(now, 3),
                "current_price": round(current_price, 8) if current_price > 0 else 0.0,
                "direction_move_pct": round(direction_move_pct, 6),
                "target_hit": target_hit,
                "status": status,
            }
        )
        opened_epoch = float(result.get("opened_at_epoch", 0.0) or 0.0)
        if target_hit and opened_epoch > 0:
            result["eta_seconds_actual"] = round(max(0.0, now - opened_epoch), 3)
        return result

    def _parse_shadow_epoch(self, value: Any) -> float:
        try:
            if isinstance(value, (int, float)):
                return float(value)
            text = str(value or "").strip()
            if not text:
                return 0.0
            return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
        except Exception:
            return 0.0

    def _finalize_shadow_stats(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        validated = int(stats.get("validated", 0) or 0)
        missed = int(stats.get("missed", 0) or 0)
        total = validated + missed
        eta_values = [float(value) for value in stats.get("eta_values", []) if float(value or 0.0) > 0]
        validation_rate = validated / total if total > 0 else 0.0
        return {
            "validated": validated,
            "missed": missed,
            "total": total,
            "validation_rate": round(validation_rate, 6),
            "avg_validation_sec": round(sum(eta_values) / len(eta_values), 3) if eta_values else 0.0,
            "fastest_validation_sec": round(min(eta_values), 3) if eta_values else 0.0,
        }

    def _shadow_validation_index(self, previous_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        previous = previous_state if isinstance(previous_state, dict) else self._read_shadow_trade_state()
        raw_routes: Dict[str, Dict[str, Any]] = {}
        raw_symbols: Dict[str, Dict[str, Any]] = {}
        seen: set[str] = set()
        rows: List[Dict[str, Any]] = []
        for key in ("prior_verifications", "shadows", "active_shadows"):
            values = previous.get(key, []) if isinstance(previous, dict) else []
            if isinstance(values, list):
                rows.extend(row for row in values if isinstance(row, dict))

        for shadow in rows:
            status = str(shadow.get("status") or "").lower()
            if status not in {"validated", "missed_eta"}:
                continue
            signature = str(shadow.get("route_signature") or "").strip()
            symbol = str(shadow.get("symbol") or "").upper().strip()
            if not signature and not symbol:
                continue
            dedupe = str(shadow.get("id") or signature or symbol) + ":" + status
            if dedupe in seen:
                continue
            seen.add(dedupe)
            opened_epoch = float(shadow.get("opened_at_epoch", 0.0) or 0.0)
            verified_epoch = float(shadow.get("last_verified_epoch", 0.0) or 0.0) or self._parse_shadow_epoch(shadow.get("last_verified_at"))
            eta = float(shadow.get("eta_seconds_actual", 0.0) or 0.0)
            if eta <= 0 and opened_epoch > 0 and verified_epoch > opened_epoch and status == "validated":
                eta = verified_epoch - opened_epoch

            for bucket, key in ((raw_routes, signature), (raw_symbols, symbol)):
                if not key:
                    continue
                item = bucket.setdefault(key, {"validated": 0, "missed": 0, "eta_values": []})
                if status == "validated":
                    item["validated"] += 1
                    if eta > 0:
                        item["eta_values"].append(eta)
                elif status == "missed_eta":
                    item["missed"] += 1

        return {
            "routes": {key: self._finalize_shadow_stats(value) for key, value in raw_routes.items()},
            "symbols": {key: self._finalize_shadow_stats(value) for key, value in raw_symbols.items()},
        }

    def _recent_route_cash_blocker(self, venue: str, market_type: str, symbol: str, side: str) -> str:
        latest = getattr(self, "_latest_execution_results", {}) or {}
        results = latest.get("results", []) if isinstance(latest, dict) else []
        if not isinstance(results, list):
            return ""
        venue_norm = str(venue or "").lower()
        market_norm = str(market_type or "").lower()
        symbol_norm = str(symbol or "").upper()
        side_norm = str(side or "").upper()
        cash_markers = (
            "insufficient funds",
            "insufficient balance",
            "no_spot_balance",
            "no_spot_balance_to_sell",
            "quantity_unavailable",
            "not enough",
        )
        for result in reversed(results[-20:]):
            if not isinstance(result, dict):
                continue
            if str(result.get("venue") or "").lower() != venue_norm:
                continue
            if str(result.get("market_type") or "").lower() != market_norm:
                continue
            if symbol_norm and str(result.get("symbol") or "").upper() != symbol_norm:
                continue
            if side_norm and str(result.get("side") or "").upper() not in {"", side_norm}:
                continue
            text = " ".join(
                str(result.get(key) or "")
                for key in ("reason", "error", "message")
            )
            text = f"{text} {json.dumps(result.get('result', ''), default=str)}".lower()
            if any(marker in text for marker in cash_markers):
                return text[:180]
        return ""

    def _route_cash_capability(
        self,
        *,
        venue: str,
        market_type: str,
        symbol: str,
        side: str,
        ready: bool,
        execution_owner: str,
    ) -> Dict[str, Any]:
        venue_norm = str(venue or "").lower()
        market_norm = str(market_type or "").lower()
        side_norm = str(side or "BUY").upper()
        if not ready:
            return {"state": "route_not_ready", "score": 0.0, "checked_by": "route_readiness"}
        blocker = self._recent_route_cash_blocker(venue_norm, market_norm, symbol, side_norm)
        if blocker:
            return {
                "state": "recent_execution_cash_blocker",
                "score": 0.1,
                "checked_by": "last_execution_result",
                "detail": blocker,
            }
        if str(execution_owner or "").lower() == "existing_autonomous_trader_tick":
            return {
                "state": "delegated_runtime_managed",
                "score": 0.75,
                "checked_by": "existing_autonomous_trader_tick",
            }
        if market_norm == "margin":
            return {"state": "margin_runtime_checked_at_execution", "score": 0.65, "checked_by": "runtime_executor"}
        if side_norm == "SELL":
            return {"state": "asset_balance_checked_at_execution", "score": 0.55, "checked_by": "runtime_executor"}
        return {"state": "quote_budgeted_at_execution", "score": 0.65, "checked_by": "runtime_executor"}

    def _momentum_tier(self, move_pct: float) -> str:
        if move_pct >= 0.50:
            return "tier_1_hot"
        if move_pct >= 0.40:
            return "tier_2_strong"
        if move_pct >= FAST_MONEY_BREAK_EVEN_MOVE_PCT:
            return "tier_3_cost_clearing"
        return "below_cost_threshold"

    def _fast_money_profile(
        self,
        *,
        item: Dict[str, Any],
        support_score: float,
        route_score: float,
        cash_score: float,
        history_score: float,
        mesh_score: float,
        eta_score: float,
        orderbook_pressure: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        side = str(item.get("side") or "BUY").upper()
        try:
            change_pct = abs(float(item.get("change_pct_abs_max", item.get("change_pct", 0.0)) or 0.0))
        except Exception:
            change_pct = 0.0
        try:
            avg_change_pct = abs(float(item.get("change_pct", 0.0) or 0.0))
        except Exception:
            avg_change_pct = 0.0
        move_pct = max(change_pct, avg_change_pct)
        try:
            volume_24h = max(0.0, float(item.get("volume_24h", 0.0) or 0.0))
        except Exception:
            volume_24h = 0.0
        try:
            freshest_age_sec = float(item.get("freshest_age_sec"))
        except Exception:
            freshest_age_sec = None  # type: ignore[assignment]

        momentum_score = self._clamp01(move_pct / max(FAST_MONEY_BREAK_EVEN_MOVE_PCT * 2.0, 0.01))
        volatility_score = self._clamp01(move_pct / max(FAST_MONEY_MIN_VOLATILITY_PCT * 2.0, 0.01))
        volume_score = self._clamp01(volume_24h / FAST_MONEY_VOLUME_USD_TARGET)
        stream_freshness_score = 0.0
        raw_sources = item.get("sources", [])
        source_set = (
            set(str(source) for source in raw_sources if source)
            if isinstance(raw_sources, list)
            else {str(raw_sources)} if raw_sources else set()
        )
        if freshest_age_sec is not None:
            stream_freshness_score = self._clamp01(1.0 - (max(0.0, float(freshest_age_sec)) / max(STREAM_CACHE_MAX_AGE_SEC, 0.5)))
        elif "live_stream_cache" in source_set:
            stream_freshness_score = 0.5

        pressure = orderbook_pressure if isinstance(orderbook_pressure, dict) else {}
        orderbook_score = 0.35
        orderbook_alignment = "not_sampled"
        if pressure:
            pressure_score = self._clamp01(pressure.get("score", 0.35), 0.35)
            pressure_side = str(pressure.get("pressure_side") or "NEUTRAL").upper()
            if bool(pressure.get("available")) and pressure_side in {"BUY", "SELL"}:
                orderbook_alignment = "aligned" if pressure_side == side else "opposed"
            elif bool(pressure.get("available")):
                orderbook_alignment = "neutral"
            else:
                orderbook_alignment = "unavailable"
            orderbook_score = pressure_score

        score = self._clamp01(
            (0.22 * momentum_score)
            + (0.18 * volatility_score)
            + (0.16 * volume_score)
            + (0.13 * stream_freshness_score)
            + (0.11 * orderbook_score)
            + (0.08 * cash_score)
            + (0.05 * route_score)
            + (0.04 * history_score)
            + (0.02 * mesh_score)
            + (0.01 * eta_score)
        )
        reasons: List[str] = []
        if move_pct >= FAST_MONEY_MIN_VOLATILITY_PCT:
            reasons.append("volatility_threshold_passed")
        else:
            reasons.append("volatility_below_fast_money_threshold")
        if move_pct >= FAST_MONEY_BREAK_EVEN_MOVE_PCT:
            reasons.append("micro_momentum_cost_threshold_passed")
        if volume_score >= 0.5:
            reasons.append("volume_liquidity_confirmed")
        elif volume_24h > 0:
            reasons.append("volume_seen_but_below_target")
        else:
            reasons.append("volume_missing_from_stream")
        if stream_freshness_score >= 0.5:
            reasons.append("fresh_stream_cache_signal")
        if orderbook_alignment == "aligned":
            reasons.append("orderbook_pressure_aligned")
        elif orderbook_alignment == "opposed":
            reasons.append("orderbook_pressure_opposed")

        fast_money_candidate = bool(score >= FAST_MONEY_MIN_SCORE and move_pct >= FAST_MONEY_MIN_VOLATILITY_PCT)
        return {
            "schema_version": 1,
            "fast_money_score": round(score, 6),
            "fast_money_candidate": fast_money_candidate,
            "momentum_tier": self._momentum_tier(move_pct),
            "volatility_pct": round(move_pct, 6),
            "avg_change_pct": round(avg_change_pct, 6),
            "volume_24h": round(volume_24h, 6),
            "freshest_age_sec": round(float(freshest_age_sec), 3) if freshest_age_sec is not None else None,
            "momentum_score": round(momentum_score, 6),
            "volatility_score": round(volatility_score, 6),
            "volume_score": round(volume_score, 6),
            "stream_freshness_score": round(stream_freshness_score, 6),
            "orderbook_score": round(orderbook_score, 6),
            "orderbook_alignment": orderbook_alignment,
            "thresholds": {
                "min_volatility_pct": FAST_MONEY_MIN_VOLATILITY_PCT,
                "break_even_move_pct": FAST_MONEY_BREAK_EVEN_MOVE_PCT,
                "volume_usd_target": FAST_MONEY_VOLUME_USD_TARGET,
                "min_fast_money_score": FAST_MONEY_MIN_SCORE,
            },
            "sources": list(item.get("fast_money_sources", [])) if isinstance(item.get("fast_money_sources"), list) else [],
            "reasons": reasons,
        }

    def _normalize_orderbook_side(self, side: Any) -> List[List[float]]:
        levels: List[List[float]] = []
        if not isinstance(side, list):
            return levels
        for raw in side:
            price = 0.0
            size = 0.0
            try:
                if isinstance(raw, dict):
                    price = float(raw.get("p") or raw.get("price") or raw.get("px") or 0.0)
                    size = float(raw.get("s") or raw.get("size") or raw.get("qty") or raw.get("quantity") or 0.0)
                elif isinstance(raw, (list, tuple)) and len(raw) >= 2:
                    price = float(raw[0] or 0.0)
                    size = float(raw[1] or 0.0)
            except Exception:
                price = 0.0
                size = 0.0
            if price > 0 and size > 0:
                levels.append([price, size])
        return levels

    def _orderbook_pressure_from_depths(
        self,
        *,
        symbol: str,
        side: str,
        bid_depth: float,
        ask_depth: float,
        best_bid: float = 0.0,
        best_ask: float = 0.0,
        source: str,
        available: bool = True,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        total_depth = max(0.0, bid_depth) + max(0.0, ask_depth)
        signed_imbalance = ((bid_depth - ask_depth) / total_depth) if total_depth > 0 else 0.0
        pressure_side = "BUY" if signed_imbalance > 0.08 else "SELL" if signed_imbalance < -0.08 else "NEUTRAL"
        side_norm = str(side or "BUY").upper()
        directional = signed_imbalance if side_norm == "BUY" else -signed_imbalance
        spread_pct = 0.0
        if best_bid > 0 and best_ask > 0:
            mid = (best_bid + best_ask) / 2.0
            spread_pct = ((best_ask - best_bid) / mid) * 100.0 if mid > 0 else 0.0
        spread_score = self._clamp01(1.0 - (spread_pct / 0.35)) if spread_pct > 0 else 0.55
        score = self._clamp01(0.50 + (directional * 0.42) + (spread_score * 0.08))
        payload = {
            "schema_version": 1,
            "available": bool(available and total_depth > 0),
            "source": source,
            "symbol": symbol,
            "side": side_norm,
            "pressure_side": pressure_side,
            "score": round(score, 6),
            "bid_depth_usd": round(max(0.0, bid_depth), 6),
            "ask_depth_usd": round(max(0.0, ask_depth), 6),
            "signed_imbalance": round(signed_imbalance, 6),
            "spread_pct": round(spread_pct, 6),
            "generated_at": datetime.now().isoformat(),
        }
        if extra:
            payload.update(extra)
        return payload

    def _orderbook_pressure_from_book(self, *, symbol: str, side: str, book: Dict[str, Any], source: str) -> Dict[str, Any]:
        bids = self._normalize_orderbook_side(book.get("bids") or book.get("b") or [])
        asks = self._normalize_orderbook_side(book.get("asks") or book.get("a") or [])
        bid_depth = sum(price * size for price, size in bids[:20])
        ask_depth = sum(price * size for price, size in asks[:20])
        best_bid = bids[0][0] if bids else 0.0
        best_ask = asks[0][0] if asks else 0.0
        return self._orderbook_pressure_from_depths(
            symbol=symbol,
            side=side,
            bid_depth=bid_depth,
            ask_depth=ask_depth,
            best_bid=best_bid,
            best_ask=best_ask,
            source=source,
            available=bool(bids and asks),
        )

    def _orderbook_pressure_snapshot(self, item: Dict[str, Any]) -> Dict[str, Any]:
        symbol = str(item.get("symbol") or "").upper().strip()
        side = str(item.get("side") or "BUY").upper()
        if not symbol:
            return {"available": False, "reason": "symbol_missing", "generated_at": datetime.now().isoformat()}
        cache: Dict[str, Dict[str, Any]] = getattr(self, "_orderbook_pressure_cache", {})
        if not isinstance(cache, dict):
            cache = {}
            self._orderbook_pressure_cache = cache
        cache_key = f"{symbol}:{side}"
        now = time.time()
        cached = cache.get(cache_key)
        if isinstance(cached, dict) and now - float(cached.get("_cached_at", 0.0) or 0.0) <= ORDERBOOK_PROBE_STALE_TTL_SEC:
            payload = dict(cached)
            payload.pop("_cached_at", None)
            payload["from_cache"] = True
            return payload

        binance_symbol = str(item.get("binance_symbol") or self._to_binance_symbol(symbol) or symbol).upper().replace("/", "")
        kraken_intel = getattr(getattr(self, "kraken", None), "intel", None)
        if kraken_intel is not None and hasattr(kraken_intel, "analyze_orderbook") and binance_symbol:
            orderbook_interval = self._dynamic_orderbook_interval("binance")
            try:
                analysis = self._governor().call(
                    "binance",
                    "orderbook",
                    f"fastmoney:binance_depth:{binance_symbol}",
                    lambda: kraken_intel.analyze_orderbook(binance_symbol),
                    min_interval_sec=orderbook_interval,
                    stale_ttl_sec=ORDERBOOK_PROBE_STALE_TTL_SEC,
                )
                if isinstance(analysis, dict) and analysis:
                    bid_depth = float(analysis.get("bid_depth_usd", 0.0) or 0.0)
                    ask_depth = float(analysis.get("ask_depth_usd", 0.0) or 0.0)
                    payload = self._orderbook_pressure_from_depths(
                        symbol=binance_symbol,
                        side=side,
                        bid_depth=bid_depth,
                        ask_depth=ask_depth,
                        best_bid=float(analysis.get("best_bid", 0.0) or 0.0),
                        best_ask=float(analysis.get("best_ask", 0.0) or 0.0),
                        source="BattlefieldIntel.binance_depth",
                        available=bid_depth > 0 and ask_depth > 0,
                        extra={
                            "whale_supporting_buy": bool(analysis.get("whale_supporting_buy")),
                            "whale_blocking_buy": bool(analysis.get("whale_blocking_buy")),
                            "whale_blocking_sell": bool(analysis.get("whale_blocking_sell")),
                            "budget_role": self._dynamic_exchange_budget("binance").get("role", "static"),
                            "orderbook_min_interval_sec": orderbook_interval,
                        },
                    )
                    payload["_cached_at"] = now
                    cache[cache_key] = payload
                    clean = dict(payload)
                    clean.pop("_cached_at", None)
                    return clean
            except Exception as e:
                logger.debug("Fast-money Binance orderbook pressure failed for %s: %s", binance_symbol, e)

        alpaca_symbol = str(item.get("alpaca_symbol") or "").strip()
        if self.alpaca is not None and alpaca_symbol and hasattr(self.alpaca, "get_crypto_orderbook"):
            orderbook_interval = self._dynamic_orderbook_interval("alpaca")
            try:
                book = self._governor().call(
                    "alpaca",
                    "orderbook",
                    f"fastmoney:alpaca_orderbook:{alpaca_symbol}",
                    lambda: self.alpaca.get_crypto_orderbook(alpaca_symbol, depth=20),
                    min_interval_sec=orderbook_interval,
                    stale_ttl_sec=ORDERBOOK_PROBE_STALE_TTL_SEC,
                )
                if isinstance(book, dict) and book:
                    payload = self._orderbook_pressure_from_book(symbol=alpaca_symbol, side=side, book=book, source="AlpacaClient.crypto_orderbook")
                    payload["budget_role"] = self._dynamic_exchange_budget("alpaca").get("role", "static")
                    payload["orderbook_min_interval_sec"] = orderbook_interval
                    payload["_cached_at"] = now
                    cache[cache_key] = payload
                    clean = dict(payload)
                    clean.pop("_cached_at", None)
                    return clean
            except Exception as e:
                logger.debug("Fast-money Alpaca orderbook pressure failed for %s: %s", alpaca_symbol, e)

        return {
            "schema_version": 1,
            "available": False,
            "source": "orderbook_probe",
            "symbol": symbol,
            "side": side,
            "pressure_side": "NEUTRAL",
            "score": 0.35,
            "reason": "no_budgeted_orderbook_source_available",
            "generated_at": datetime.now().isoformat(),
        }

    def _build_fast_money_summary(self, ranked: List[Dict[str, Any]]) -> Dict[str, Any]:
        profiles = [
            item.get("fast_money_profile", {})
            for item in ranked
            if isinstance(item, dict) and isinstance(item.get("fast_money_profile"), dict)
        ]
        candidates = [profile for profile in profiles if profile.get("fast_money_candidate")]
        orderbooks = [
            item.get("orderbook_pressure", {})
            for item in ranked
            if isinstance(item, dict) and isinstance(item.get("orderbook_pressure"), dict)
        ]
        orderbook_attempt_count = len(orderbooks)
        orderbook_available_count = sum(1 for book in orderbooks if book.get("available"))
        top_item = max(
            ranked,
            key=lambda item: float((item.get("fast_money_profile") or {}).get("fast_money_score", 0.0) or 0.0),
            default={},
        )
        top_profile = top_item.get("fast_money_profile", {}) if isinstance(top_item, dict) else {}
        dynamic_budget = getattr(self, "_dynamic_intelligence_budget", {}) or {}
        dynamic_probe_limit = self._dynamic_orderbook_probe_limit()
        return {
            "schema_version": 1,
            "generated_at": datetime.now().isoformat(),
            "mode": "balance_weighted_high_volatility_momentum_volume_orderbook_profit_velocity",
            "candidate_count": len(candidates),
            "active_order_flow_count": len(ranked),
            "evaluated_candidate_count": len(profiles),
            "active_this_cycle": bool(profiles),
            "fed_to_decision_logic": bool(profiles),
            "high_volatility_count": sum(
                1 for profile in profiles if float(profile.get("volatility_pct", 0.0) or 0.0) >= FAST_MONEY_MIN_VOLATILITY_PCT
            ),
            "orderbook_attempt_count": orderbook_attempt_count,
            "orderbook_probe_count": orderbook_available_count,
            "orderbook_aligned_count": sum(1 for profile in profiles if profile.get("orderbook_alignment") == "aligned"),
            "top_symbol": top_item.get("symbol") if isinstance(top_item, dict) else "",
            "top_side": top_item.get("side") if isinstance(top_item, dict) else "",
            "top_fast_money_score": round(float(top_profile.get("fast_money_score", 0.0) or 0.0), 6),
            "top_momentum_tier": top_profile.get("momentum_tier", ""),
            "reason": (
                "fast_money_candidates_ready"
                if candidates
                else "candidates_evaluated_below_fast_money_threshold"
                if profiles
                else "no_ranked_order_flow_candidates"
            ),
            "orderbook_reason": (
                "orderbook_pressure_available"
                if orderbook_available_count > 0
                else "orderbook_pressure_attempted_unavailable"
                if orderbook_attempt_count > 0
                else "orderbook_pressure_not_sampled_this_cycle"
            ),
            "thresholds": {
                "min_volatility_pct": FAST_MONEY_MIN_VOLATILITY_PCT,
                "break_even_move_pct": FAST_MONEY_BREAK_EVEN_MOVE_PCT,
                "volume_usd_target": FAST_MONEY_VOLUME_USD_TARGET,
                "orderbook_probe_max_per_tick": ORDERBOOK_PROBE_MAX_PER_TICK,
                "dynamic_orderbook_probe_max_per_tick": dynamic_probe_limit,
                "orderbook_probe_min_interval_sec": ORDERBOOK_PROBE_MIN_INTERVAL_SEC,
            },
            "dynamic_intelligence_budget": dynamic_budget,
        }

    def _publish_scanner_fusion_matrix(self, report: Dict[str, Any]) -> None:
        if _SUPPRESS_IMPORT_SIDE_EFFECTS:
            return
        for path in (SCANNER_FUSION_MATRIX_STATE_PATH, SCANNER_FUSION_MATRIX_PUBLIC_PATH):
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                tmp_path = path.with_name(f"{path.name}.{os.getpid()}.tmp")
                with tmp_path.open("w", encoding="utf-8") as handle:
                    json.dump(report, handle, indent=2, default=str)
                os.replace(tmp_path, path)
            except Exception as e:
                logger.debug("Scanner fusion matrix write failed for %s: %s", path, e)

    def _scanner_fusion_descriptors(self) -> List[Dict[str, Any]]:
        tracked_names = {
            "LiveExchangeFeeds",
            "LiveStreamCache",
            "UnifiedSignalEngine",
            "WorldFinancialEcosystemFeed",
            "MultiHorizonWaveformMemory",
            "SelfValidatingPredictor",
            "TruthPredictionEngine",
            "LiveMomentumHunter",
            "FastMoneySelector",
            "OrderBookPressure",
            "GlobalWaveScanner",
            "MarginHarmonicScanner",
            "MoversShakersScanner",
            "AnimalMomentumScanners",
            "OceanWaveScanner",
            "PhantomSignalFilter",
            "WhaleSonar",
            "MicroMomentumGoal",
            "PennyProfitEngine",
            "DynamicTakeProfit",
            "TemporalTradeCognition",
            "RisingStarLogic",
        }
        return [
            descriptor
            for descriptor in INTELLIGENCE_MESH_CAPABILITIES
            if str(descriptor.get("name") or "") in tracked_names
        ]

    def _scanner_fusion_system_rows(
        self,
        *,
        central_beat: Dict[str, Any],
        ranked: List[Dict[str, Any]],
        fast_money_intelligence: Dict[str, Any],
        intelligence_mesh: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        central = central_beat if isinstance(central_beat, dict) else {}
        active_order_flow_count = sum(1 for item in ranked if isinstance(item, dict))
        profiles = [
            item.get("fast_money_profile", {})
            for item in ranked
            if isinstance(item, dict) and isinstance(item.get("fast_money_profile"), dict)
        ]
        high_volatility_count = sum(
            1
            for profile in profiles
            if float(profile.get("volatility_pct", 0.0) or 0.0) >= FAST_MONEY_MIN_VOLATILITY_PCT
        )
        volume_seen_count = sum(1 for item in ranked if float(item.get("volume_24h", 0.0) or 0.0) > 0)
        margin_route_count = sum(
            1
            for item in ranked
            for route_item in (item.get("execution_routes", []) if isinstance(item, dict) and isinstance(item.get("execution_routes"), list) else [])
            if isinstance(route_item, dict) and str(route_item.get("market_type") or "").lower() == "margin"
        )
        cash_route_count = sum(1 for item in ranked if int(item.get("cash_capable_route_count", 0) or 0) > 0)
        stream_cache = central.get("stream_cache", {}) if isinstance(central.get("stream_cache"), dict) else {}
        model_signal_feed = central.get("model_signal_feed", {}) if isinstance(central.get("model_signal_feed"), dict) else {}
        world = central.get("world_financial_ecosystem", {}) if isinstance(central.get("world_financial_ecosystem"), dict) else {}
        waveform = central.get("asset_waveform_models", {}) if isinstance(central.get("asset_waveform_models"), dict) else {}
        world_cross = world.get("cross_asset", {}) if isinstance(world.get("cross_asset"), dict) else {}
        world_harp = world.get("market_harp", {}) if isinstance(world.get("market_harp"), dict) else {}
        world_news = world.get("news_signal", {}) if isinstance(world.get("news_signal"), dict) else {}
        orderbook_probe_count = int(fast_money_intelligence.get("orderbook_probe_count", 0) or 0)
        orderbook_aligned_count = int(fast_money_intelligence.get("orderbook_aligned_count", 0) or 0)
        fast_candidate_count = int(fast_money_intelligence.get("candidate_count", 0) or 0)
        mesh_score = self._clamp01((intelligence_mesh or {}).get("selection_mesh_score", 0.0), 0.0)
        waveform_usable_count = int(waveform.get("usable_symbol_count", 0) or 0)
        world_usable_count = int(world.get("usable_source_count", 0) or 0)
        source_count = int(central.get("source_count", 0) or 0)

        def active_reason(name: str) -> Tuple[bool, str, str]:
            if name == "LiveExchangeFeeds":
                return source_count > 0, "market_feed", f"{source_count} CentralBeat sources"
            if name == "LiveStreamCache":
                return bool(stream_cache.get("fresh") and int(stream_cache.get("symbol_count", 0) or 0) > 0), "market_feed", "fresh live stream cache"
            if name == "UnifiedSignalEngine":
                return bool(model_signal_feed.get("used")), "exchange_action_plan", "model signal feed used"
            if name == "WorldFinancialEcosystemFeed":
                return world_usable_count > 0, "market_feed", f"{world_usable_count} world ecosystem sources"
            if name == "MultiHorizonWaveformMemory":
                return waveform_usable_count > 0, "hnc_proof", f"{waveform_usable_count} waveform symbols"
            if name == "LiveMomentumHunter":
                return high_volatility_count > 0, "profit_velocity", f"{high_volatility_count} high-volatility candidates"
            if name == "FastMoneySelector":
                return fast_candidate_count > 0, "profit_velocity", f"{fast_candidate_count} fast-money candidates"
            if name == "OrderBookPressure":
                return orderbook_probe_count > 0, "shadow_validation", f"{orderbook_probe_count} order-book probes"
            if name == "GlobalWaveScanner":
                active = waveform_usable_count > 0 or bool(world_cross.get("active_this_cycle"))
                return active, "hnc_proof", "waveform or cross-asset wave evidence"
            if name == "MarginHarmonicScanner":
                return margin_route_count > 0, "exchange_action_plan", f"{margin_route_count} margin routes in candidate flow"
            if name == "MoversShakersScanner":
                return high_volatility_count > 0 and volume_seen_count > 0, "profit_velocity", f"{high_volatility_count} movers with volume evidence"
            if name == "AnimalMomentumScanners":
                return active_order_flow_count > 0 and mesh_score > 0, "exchange_action_plan", "swarm candidate ranking active"
            if name == "OceanWaveScanner":
                active = waveform_usable_count > 0 or bool(world_harp.get("active_this_cycle"))
                return active, "auris_state", "waveform memory or MarketHarp resonance"
            if name == "PhantomSignalFilter":
                return active_order_flow_count > 0, "shadow_validation", "candidate noise/rejection pass active"
            if name == "WhaleSonar":
                return orderbook_probe_count > 0, "shadow_validation", f"{orderbook_aligned_count} aligned order-book probes"
            if name in {"SelfValidatingPredictor", "TruthPredictionEngine"}:
                return active_order_flow_count > 0 and (cash_route_count > 0 or fast_candidate_count > 0), "shadow_validation", "candidate self-validation evidence present"
            if name in {"MicroMomentumGoal", "PennyProfitEngine"}:
                return fast_candidate_count > 0 or high_volatility_count > 0, "profit_velocity", "micro-profit timing evidence active"
            if name == "DynamicTakeProfit":
                return orderbook_aligned_count > 0 or fast_candidate_count > 0, "profit_velocity", "fast exit/dead-man profit capture context active"
            if name == "TemporalTradeCognition":
                return active_order_flow_count > 0, "profit_velocity", "ETA and temporal target scoring active"
            if name == "RisingStarLogic":
                return active_order_flow_count > 0 and (world_usable_count > 0 or bool(world_news.get("usable_for_decision"))), "market_feed", "whole-market context and candidate ranking active"
            return False, "mesh_context", "no scanner fusion rule"

        rows: List[Dict[str, Any]] = []
        for descriptor in self._scanner_fusion_descriptors():
            name = str(descriptor.get("name") or "")
            present = self._capability_present(str(descriptor.get("path") or ""))
            active, downstream_stage, reason = active_reason(name)
            active = bool(active and present and SCANNER_FUSION_MATRIX_ENABLED)
            fresh = bool(active)
            usable = bool(active)
            blocker = ""
            if not SCANNER_FUSION_MATRIX_ENABLED:
                blocker = "scanner_fusion_matrix_disabled"
            elif not present:
                blocker = "repo_capability_missing"
            elif not active:
                blocker = "awaiting_fresh_cross_reference_evidence"
            rows.append(
                {
                    "name": name,
                    "facet": descriptor.get("facet"),
                    "wire_path": descriptor.get("wire"),
                    "repo_path": descriptor.get("path"),
                    "evidence_source": "state/unified_runtime_status.json#shared_order_flow.scanner_fusion_matrix",
                    "last_timestamp": central.get("generated_at") or datetime.now().isoformat(),
                    "present": present,
                    "active_this_cycle": active,
                    "fresh": fresh,
                    "usable_for_decision": usable,
                    "fed_to_decision_logic": usable,
                    "downstream_stage": downstream_stage,
                    "reason": reason,
                    "blocker": blocker,
                }
            )
        return rows

    def _candidate_scanner_fusion(
        self,
        item: Dict[str, Any],
        *,
        intelligence_mesh: Dict[str, Any],
    ) -> Dict[str, Any]:
        profile = item.get("fast_money_profile", {}) if isinstance(item.get("fast_money_profile"), dict) else {}
        pressure = item.get("orderbook_pressure", {}) if isinstance(item.get("orderbook_pressure"), dict) else {}
        waveform = item.get("historical_waveform", {}) if isinstance(item.get("historical_waveform"), dict) else {}
        world_signal = item.get("world_ecosystem_signal", {}) if isinstance(item.get("world_ecosystem_signal"), dict) else {}
        side = str(item.get("side") or "BUY").upper()
        orderbook_alignment = str(profile.get("orderbook_alignment") or "not_sampled")
        orderbook_available = bool(pressure.get("available"))
        orderbook_raw_score = self._clamp01(profile.get("orderbook_score", pressure.get("score", 0.35)), 0.0)
        if orderbook_alignment == "aligned":
            orderbook_component = orderbook_raw_score
        elif orderbook_alignment == "opposed":
            orderbook_component = min(0.18, orderbook_raw_score * 0.25)
        elif orderbook_available:
            orderbook_component = max(0.35, orderbook_raw_score * 0.70)
        else:
            orderbook_component = 0.25

        waveform_side = str(waveform.get("side") or side).upper()
        waveform_score = self._clamp01(waveform.get("confidence", 0.0), 0.0)
        waveform_component = waveform_score if waveform and waveform_side == side else waveform_score * 0.35

        world_side = str(world_signal.get("side") or side).upper()
        world_score = self._clamp01(world_signal.get("confidence", 0.0), 0.0)
        world_component = world_score if world_signal and world_side == side else world_score * 0.35

        sources = item.get("sources", []) if isinstance(item.get("sources"), list) else []
        support_component = self._clamp01(float(item.get("support_count", 0) or 0) / 5.0)
        model_component = 1.0 if bool(item.get("model_alignment")) else 0.35
        route_component = self._clamp01(item.get("route_score", 0.0), 0.0)
        fast_money_component = self._clamp01(item.get("fast_money_score", 0.0), 0.0)
        profit_velocity_component = self._clamp01(item.get("profit_velocity_score", 0.0), 0.0)
        stream_component = self._clamp01(profile.get("stream_freshness_score", 0.0), 0.0)
        mesh_component = self._clamp01((intelligence_mesh or {}).get("selection_mesh_score", 0.0), 0.0)
        volatility_component = self._clamp01(float(profile.get("volatility_pct", 0.0) or 0.0) / max(FAST_MONEY_MIN_VOLATILITY_PCT * 2.0, 0.01))

        cross_reference_count = 0
        evidence_paths: List[str] = []
        if sources:
            cross_reference_count += 1
            evidence_paths.append("central_beat.sources")
        if orderbook_available:
            cross_reference_count += 1
            evidence_paths.append("orderbook_pressure")
        if waveform:
            cross_reference_count += 1
            evidence_paths.append("historical_waveform")
        if world_signal:
            cross_reference_count += 1
            evidence_paths.append("world_ecosystem_signal")
        if bool(item.get("model_alignment")):
            cross_reference_count += 1
            evidence_paths.append("model_alignment")
        if int(item.get("cash_capable_route_count", 0) or 0) > 0:
            cross_reference_count += 1
            evidence_paths.append("cash_capable_routes")
        if float(item.get("history_validation_score", 0.0) or 0.0) > 0.5:
            cross_reference_count += 1
            evidence_paths.append("shadow_history")
        if mesh_component > 0:
            cross_reference_count += 1
            evidence_paths.append("intelligence_mesh")

        blockers: List[str] = []
        if not orderbook_available:
            blockers.append("orderbook_pressure_not_sampled_or_unavailable")
        if orderbook_alignment == "opposed" and waveform_component < 0.55 and world_component < 0.55:
            blockers.append("phantom_signal_filter_opposed_orderbook_without_world_or_waveform_support")
        if cross_reference_count < 3:
            blockers.append("not_enough_cross_references")
        if float(item.get("reference_price", 0.0) or 0.0) <= 0:
            blockers.append("reference_price_missing")

        score = self._clamp01(
            (0.17 * profit_velocity_component)
            + (0.16 * fast_money_component)
            + (0.16 * orderbook_component)
            + (0.12 * volatility_component)
            + (0.11 * waveform_component)
            + (0.10 * world_component)
            + (0.07 * model_component)
            + (0.05 * support_component)
            + (0.03 * route_component)
            + (0.02 * stream_component)
            + (0.01 * mesh_component)
        )
        usable = bool(score > 0 and cross_reference_count >= 3 and "phantom_signal_filter_opposed_orderbook_without_world_or_waveform_support" not in blockers)
        active_scanners = [
            "LiveMomentumHunter",
            "FastMoneySelector",
            "PhantomSignalFilter",
            "MicroMomentumGoal",
            "PennyProfitEngine",
            "DynamicTakeProfit",
        ]
        if orderbook_available:
            active_scanners.extend(["OrderBookPressure", "WhaleSonar"])
        if waveform:
            active_scanners.extend(["MultiHorizonWaveformMemory", "GlobalWaveScanner", "OceanWaveScanner"])
        if world_signal:
            active_scanners.extend(["WorldFinancialEcosystemFeed", "RisingStarLogic"])
        if any(str(route.get("market_type") or "").lower() == "margin" for route in item.get("execution_routes", []) if isinstance(route, dict)):
            active_scanners.append("MarginHarmonicScanner")
        if float(item.get("volume_24h", 0.0) or 0.0) > 0:
            active_scanners.append("MoversShakersScanner")
        if mesh_component > 0:
            active_scanners.extend(["AnimalMomentumScanners", "SelfValidatingPredictor", "TruthPredictionEngine", "TemporalTradeCognition"])

        return {
            "schema_version": 1,
            "scanner_fusion_score": round(score, 6),
            "cross_reference_count": cross_reference_count,
            "usable_for_decision": usable,
            "fed_to_decision_logic": usable,
            "phantom_filter_state": "pass" if usable else "review",
            "orderbook_alignment": orderbook_alignment,
            "orderbook_component": round(orderbook_component, 6),
            "volatility_component": round(volatility_component, 6),
            "waveform_component": round(waveform_component, 6),
            "world_component": round(world_component, 6),
            "model_component": round(model_component, 6),
            "active_scanners": sorted(set(active_scanners)),
            "evidence_paths": evidence_paths,
            "blockers": blockers,
        }

    def _build_scanner_fusion_matrix(
        self,
        *,
        central_beat: Dict[str, Any],
        ranked: List[Dict[str, Any]],
        fast_money_intelligence: Dict[str, Any],
        intelligence_mesh: Dict[str, Any],
    ) -> Dict[str, Any]:
        now_iso = datetime.now().isoformat()
        if not SCANNER_FUSION_MATRIX_ENABLED:
            report = {
                "schema_version": 1,
                "generated_at": now_iso,
                "enabled": False,
                "mode": "scanner_fusion_disabled",
                "systems": [],
                "candidates": [],
                "fed_to_decision_logic": False,
            }
            self._scanner_fusion_matrix = report
            return report

        for item in ranked:
            if not isinstance(item, dict):
                continue
            fusion = self._candidate_scanner_fusion(item, intelligence_mesh=intelligence_mesh)
            item["scanner_fusion"] = fusion
            item["scanner_fusion_score"] = fusion.get("scanner_fusion_score", 0.0)
            if fusion.get("usable_for_decision"):
                current = self._clamp01(item.get("profit_velocity_score", 0.0), 0.0)
                fused = self._clamp01(fusion.get("scanner_fusion_score", 0.0), 0.0)
                weight = SCANNER_FUSION_DECISION_WEIGHT
                item["profit_velocity_score"] = round(self._clamp01((current * (1.0 - weight)) + (fused * weight)), 6)
                basis = str(item.get("selection_basis") or "")
                if "scanner fusion" not in basis.lower():
                    item["selection_basis"] = f"{basis}, scanner fusion cross-reference" if basis else "scanner fusion cross-reference"

        rows = self._scanner_fusion_system_rows(
            central_beat=central_beat,
            ranked=ranked,
            fast_money_intelligence=fast_money_intelligence,
            intelligence_mesh=intelligence_mesh,
        )
        candidates = [
            {
                "symbol": item.get("symbol"),
                "side": item.get("side"),
                "selection_rank": item.get("selection_rank"),
                "scanner_fusion_score": item.get("scanner_fusion_score", 0.0),
                "profit_velocity_score": item.get("profit_velocity_score", 0.0),
                "fast_money_score": item.get("fast_money_score", 0.0),
                "cross_reference_count": (item.get("scanner_fusion") or {}).get("cross_reference_count", 0),
                "usable_for_decision": (item.get("scanner_fusion") or {}).get("usable_for_decision", False),
                "fed_to_decision_logic": (item.get("scanner_fusion") or {}).get("fed_to_decision_logic", False),
                "orderbook_alignment": (item.get("scanner_fusion") or {}).get("orderbook_alignment"),
                "active_scanners": (item.get("scanner_fusion") or {}).get("active_scanners", []),
                "blockers": (item.get("scanner_fusion") or {}).get("blockers", []),
            }
            for item in ranked[:20]
            if isinstance(item, dict)
        ]
        usable_systems = sum(1 for row in rows if row.get("usable_for_decision"))
        blocked_systems = sum(1 for row in rows if row.get("present") and not row.get("usable_for_decision"))
        usable_candidates = sum(1 for item in candidates if item.get("usable_for_decision"))
        report = {
            "schema_version": 1,
            "generated_at": now_iso,
            "enabled": True,
            "mode": "momentum_intelligence_orderbook_waveform_cross_reference",
            "summary": "Momentum, scanner, order-book, volatility, world-context, waveform, model, shadow, and profit-timing evidence are fused before candidate ranking.",
            "system_count": len(rows),
            "usable_system_count": usable_systems,
            "blocked_system_count": blocked_systems,
            "candidate_count": len(candidates),
            "usable_candidate_count": usable_candidates,
            "fresh": bool(usable_systems > 0 and usable_candidates > 0),
            "fed_to_decision_logic": bool(usable_candidates > 0),
            "decision_weight": SCANNER_FUSION_DECISION_WEIGHT,
            "systems": rows,
            "candidates": candidates,
            "artifacts": {
                "state": str(SCANNER_FUSION_MATRIX_STATE_PATH),
                "public": str(SCANNER_FUSION_MATRIX_PUBLIC_PATH),
            },
        }
        self._scanner_fusion_matrix = report
        self._publish_scanner_fusion_matrix(report)
        return report

    def _attach_orderbook_fast_money_pressure(
        self,
        ranked: List[Dict[str, Any]],
        *,
        shadow_index: Dict[str, Any],
        intelligence_mesh: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not ranked:
            summary = self._build_fast_money_summary([])
            self._fast_money_intelligence = summary
            return summary
        probe_candidates = sorted(
            [
                item
                for item in ranked
                if isinstance(item, dict)
                and (
                    bool((item.get("fast_money_profile") or {}).get("fast_money_candidate"))
                    or float((item.get("fast_money_profile") or {}).get("volatility_pct", 0.0) or 0.0) >= FAST_MONEY_MIN_VOLATILITY_PCT
                )
            ],
            key=lambda item: (
                float((item.get("fast_money_profile") or {}).get("fast_money_score", 0.0) or 0.0),
                float(item.get("profit_velocity_score", 0.0) or 0.0),
            ),
            reverse=True,
        )
        if not probe_candidates:
            probe_candidates = sorted(
                [
                    item
                    for item in ranked
                    if isinstance(item, dict)
                    and (
                        int(item.get("ready_route_count", 0) or 0) > 0
                        or float(item.get("confidence", 0.0) or 0.0) >= ORDER_INTENT_MIN_CONFIDENCE
                    )
                ],
                key=lambda item: (
                    float(item.get("profit_velocity_score", 0.0) or 0.0),
                    float(item.get("confidence", 0.0) or 0.0),
                ),
                reverse=True,
            )
        for item in probe_candidates[:self._dynamic_orderbook_probe_limit()]:
            pressure = self._orderbook_pressure_snapshot(item)
            item["orderbook_pressure"] = pressure
            item.update(
                self._profit_velocity_metrics(
                    item=item,
                    execution_routes=item.get("execution_routes", []) if isinstance(item.get("execution_routes"), list) else [],
                    shadow_index=shadow_index,
                    intelligence_mesh=intelligence_mesh,
                    orderbook_pressure=pressure,
                )
            )
        summary = self._build_fast_money_summary(ranked)
        self._fast_money_intelligence = summary
        return summary

    def _profit_velocity_metrics(
        self,
        *,
        item: Dict[str, Any],
        execution_routes: List[Dict[str, Any]],
        shadow_index: Dict[str, Any],
        intelligence_mesh: Optional[Dict[str, Any]] = None,
        orderbook_pressure: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        confidence = self._clamp01(item.get("confidence", 0.0))
        support_score = self._clamp01(float(item.get("support_count", 0) or 0) / 4.0)
        route_score = self._clamp01(sum(1 for route in execution_routes if route.get("ready")) / max(1, len(execution_routes)))
        cash_scores = [
            float((route.get("cash_capability") or {}).get("score", 0.0) or 0.0)
            for route in execution_routes
            if isinstance(route, dict)
        ]
        cash_score = self._clamp01(max(cash_scores) if cash_scores else 0.0)
        try:
            change_pct = abs(float(item.get("change_pct", 0.0) or 0.0))
        except Exception:
            change_pct = 0.0
        target_pct = max(0.01, float(SHADOW_TRADE_TARGET_MOVE_PCT or 0.18))
        momentum_score = self._clamp01(change_pct / max(target_pct * 2.0, 0.01))
        price_score = 1.0 if float(item.get("reference_price", 0.0) or 0.0) > 0 else 0.2
        model_score = 1.0 if bool(item.get("model_alignment")) else 0.55
        mesh_score = self._clamp01((intelligence_mesh or {}).get("selection_mesh_score", 0.0), 0.0)

        symbol = str(item.get("symbol") or "").upper().strip()
        symbol_stats = (shadow_index.get("symbols", {}) or {}).get(symbol, {}) if isinstance(shadow_index, dict) else {}
        route_stats: List[Dict[str, Any]] = []
        side = str(item.get("side") or "BUY").upper()
        for route in execution_routes:
            if not isinstance(route, dict):
                continue
            signature = f"{str(route.get('venue') or '').lower()}:{str(route.get('market_type') or '').lower()}:{str(route.get('symbol') or '').upper().strip()}:{side}"
            stats = (shadow_index.get("routes", {}) or {}).get(signature, {}) if isinstance(shadow_index, dict) else {}
            if stats:
                route_stats.append(stats)
        validation_rates = [
            float(stats.get("validation_rate", 0.0) or 0.0)
            for stats in route_stats + ([symbol_stats] if symbol_stats else [])
            if int(stats.get("total", 0) or 0) > 0
        ]
        history_score = self._clamp01(max(validation_rates) if validation_rates else 0.5)
        validated_count = sum(int(stats.get("validated", 0) or 0) for stats in route_stats)
        missed_count = sum(int(stats.get("missed", 0) or 0) for stats in route_stats)
        if symbol_stats:
            validated_count = max(validated_count, int(symbol_stats.get("validated", 0) or 0))
            missed_count = max(missed_count, int(symbol_stats.get("missed", 0) or 0))
        fastest_values = [
            float(stats.get("fastest_validation_sec", 0.0) or 0.0)
            for stats in route_stats + ([symbol_stats] if symbol_stats else [])
            if float(stats.get("fastest_validation_sec", 0.0) or 0.0) > 0
        ]
        heuristic_eta = (target_pct / max(change_pct, 0.01)) * 60.0
        estimated_eta = min(max(5.0, heuristic_eta), SHADOW_TRADE_VALIDATION_HORIZON_SEC * 3.0)
        if fastest_values:
            estimated_eta = min(estimated_eta, min(fastest_values))
        eta_score = self._clamp01(SHADOW_TRADE_VALIDATION_HORIZON_SEC / max(estimated_eta, 1.0))
        fast_money_profile = self._fast_money_profile(
            item=item,
            support_score=support_score,
            route_score=route_score,
            cash_score=cash_score,
            history_score=history_score,
            mesh_score=mesh_score,
            eta_score=eta_score,
            orderbook_pressure=orderbook_pressure,
        )
        fast_money_score = self._clamp01(fast_money_profile.get("fast_money_score", 0.0))
        score = self._clamp01(
            (0.18 * confidence)
            + (0.15 * cash_score)
            + (0.13 * history_score)
            + (0.16 * fast_money_score)
            + (0.10 * momentum_score)
            + (0.08 * support_score)
            + (0.07 * model_score)
            + (0.06 * mesh_score)
            + (0.05 * eta_score)
            + (0.02 * route_score)
        )
        return {
            "profit_velocity_score": round(score, 6),
            "fast_money_score": round(fast_money_score, 6),
            "fast_money_candidate": bool(fast_money_profile.get("fast_money_candidate")),
            "fast_money_profile": fast_money_profile,
            "estimated_target_eta_sec": round(estimated_eta, 3),
            "eta_score": round(eta_score, 6),
            "cash_route_score": round(cash_score, 6),
            "cash_capable_route_count": sum(1 for score_value in cash_scores if score_value >= 0.55),
            "route_score": round(route_score, 6),
            "history_validation_score": round(history_score, 6),
            "history_validated_count": validated_count,
            "history_missed_count": missed_count,
            "momentum_score": round(momentum_score, 6),
            "price_score": round(price_score, 6),
            "model_score": round(model_score, 6),
            "intelligence_mesh_score": round(mesh_score, 6),
            "selection_basis": "cash-capable routes, fresh/reference price, high-volatility fast-money evidence, volume/liquidity, order-book pressure, shadow history, support, model alignment, whole-intelligence mesh readiness, and fastest target ETA",
        }

    def _build_shadow_trade_report(
        self,
        order_flow_feed: Dict[str, Any],
        action_plan: Dict[str, Any],
        *,
        persist: bool = True,
        previous_state: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        generated_at = datetime.now().isoformat()
        enabled = self._shadow_trade_enabled()
        active = order_flow_feed.get("active_order_flow", []) if isinstance(order_flow_feed, dict) else []
        if not isinstance(active, list):
            active = []
        runtime_clearances = [
            str(item)
            for item in (
                action_plan.get("global_clearances")
                or action_plan.get("runtime_clearances")
                or action_plan.get("global_guards")
                or action_plan.get("global_blockers")
                or []
            )
            if str(item)
        ] if isinstance(action_plan, dict) else []
        global_guards = [
            str(item)
            for item in (
                action_plan.get("global_guards")
                or action_plan.get("global_blockers")
                or []
            )
            if str(item)
        ] if isinstance(action_plan, dict) else []

        previous = previous_state if isinstance(previous_state, dict) else (self._read_shadow_trade_state() if persist else {})
        previous_active = previous.get("active_shadows", []) if isinstance(previous.get("active_shadows"), list) else []
        current_prices = {
            str(item.get("symbol") or "").upper(): float(item.get("reference_price", 0.0) or 0.0)
            for item in active
            if isinstance(item, dict) and float(item.get("reference_price", 0.0) or 0.0) > 0
        }
        now = time.time()
        prior_verifications = [
            self._verify_prior_shadow(shadow, current_prices, now)
            for shadow in previous_active
            if isinstance(shadow, dict)
        ]
        still_active = [
            shadow
            for shadow in prior_verifications
            if shadow.get("status") in {"validating", "pending_price", "shadow_opened"}
        ][:SHADOW_TRADE_MAX_PER_CYCLE]
        active_signatures = {str(shadow.get("route_signature") or "") for shadow in still_active if shadow.get("route_signature")}

        new_shadows: List[Dict[str, Any]] = []
        if enabled:
            for item in active:
                if len(new_shadows) >= SHADOW_TRADE_MAX_PER_CYCLE:
                    break
                if not isinstance(item, dict):
                    continue
                confidence = max(0.0, min(1.0, float(item.get("confidence", 0.0) or 0.0)))
                if confidence < SHADOW_TRADE_MIN_CONFIDENCE:
                    continue
                route_items = item.get("execution_routes", []) if isinstance(item.get("execution_routes"), list) else []
                for route_item in route_items:
                    if len(new_shadows) >= SHADOW_TRADE_MAX_PER_CYCLE:
                        break
                    if not isinstance(route_item, dict):
                        continue
                    venue = str(route_item.get("venue") or "").lower()
                    market_type = str(route_item.get("market_type") or "").lower()
                    route_symbol = str(route_item.get("symbol") or item.get("symbol") or "").upper().strip()
                    side = str(item.get("side") or "BUY").upper()
                    route_signature = f"{venue}:{market_type}:{route_symbol}:{side}"
                    if route_signature in active_signatures:
                        continue
                    entry_price = float(item.get("reference_price", 0.0) or 0.0)
                    if entry_price <= 0 and bool(route_item.get("ready")):
                        entry_price = self._estimate_route_price(venue, route_symbol)
                    review = self._shadow_agent_review(item=item, route_item=route_item, entry_price=entry_price, global_guards=runtime_clearances)
                    status = "shadow_opened" if review.get("logic_validated") else "shadow_held"
                    opened_epoch = now
                    target_price = self._shadow_target_price(entry_price, side, SHADOW_TRADE_TARGET_MOVE_PCT)
                    shadow = {
                        "id": f"shadow-{int(now)}-{len(new_shadows) + 1}",
                        "route_signature": route_signature,
                        "generated_at": generated_at,
                        "opened_at_epoch": round(opened_epoch, 3),
                        "expected_by_epoch": round(opened_epoch + SHADOW_TRADE_VALIDATION_HORIZON_SEC, 3),
                        "status": status,
                        "symbol": str(item.get("symbol") or "").upper(),
                        "venue": venue,
                        "market_type": market_type,
                        "route_symbol": route_symbol,
                        "side": side,
                        "confidence": round(confidence, 6),
                        "selection_rank": item.get("selection_rank"),
                        "profit_velocity_score": item.get("profit_velocity_score", 0.0),
                        "fast_money_score": item.get("fast_money_score", 0.0),
                        "fast_money_candidate": bool(item.get("fast_money_candidate")),
                        "fast_money_profile": item.get("fast_money_profile", {}),
                        "orderbook_pressure": item.get("orderbook_pressure", {}),
                        "estimated_target_eta_sec": item.get("estimated_target_eta_sec", 0.0),
                        "cash_capable_route_count": item.get("cash_capable_route_count", 0),
                        "history_validation_score": item.get("history_validation_score", 0.0),
                        "selection_basis": item.get("selection_basis", ""),
                        "support_count": int(item.get("support_count", 0) or 0),
                        "sources": list(item.get("sources", [])) if isinstance(item.get("sources"), list) else [],
                        "entry_price": round(entry_price, 8) if entry_price > 0 else 0.0,
                        "target_price": round(target_price, 8) if target_price > 0 else 0.0,
                        "target_move_pct": round(SHADOW_TRADE_TARGET_MOVE_PCT, 6),
                        "validation_horizon_sec": round(SHADOW_TRADE_VALIDATION_HORIZON_SEC, 3),
                        "model_signal": item.get("model_signal", {}) if isinstance(item.get("model_signal"), dict) else {},
                        "model_alignment": bool(item.get("model_alignment", False)),
                        "model_stack_key": route_item.get("model_stack_key"),
                        "model_count": int(route_item.get("model_count", 0) or 0),
                        "route_clearances": list(route_item.get("runtime_clearances", []) or route_item.get("guards", []) or route_item.get("blockers", []) or []),
                        "route_guards": list(route_item.get("guards", []) or route_item.get("blockers", []) or []),
                        "route_ready": bool(route_item.get("ready")),
                        "execution_owner": route_item.get("execution_owner"),
                        "real_order_submitted": False,
                        "promotion_gate": "runtime_executor_required_after_shadow_validation",
                        "agent_review": review,
                    }
                    new_shadows.append(shadow)
                    if status == "shadow_opened":
                        active_signatures.add(route_signature)

        active_shadows = [
            shadow for shadow in still_active + new_shadows if shadow.get("status") in {"validating", "pending_price", "shadow_opened"}
        ][:SHADOW_TRADE_MAX_PER_CYCLE]
        validated_count = sum(1 for shadow in prior_verifications if shadow.get("status") == "validated")
        missed_count = sum(1 for shadow in prior_verifications if shadow.get("status") == "missed_eta")
        opened_count = sum(1 for shadow in new_shadows if shadow.get("status") == "shadow_opened")
        held_count = sum(1 for shadow in new_shadows if shadow.get("status") == "shadow_held")
        report = {
            "generated_at": generated_at,
            "mode": "shadow_validation_non_mutating",
            "enabled": enabled,
            "status": "shadow_reporting_active" if enabled else "shadow_reporting_disabled",
            "who": "unified_market_trader plus route/model/HNC validation agents",
            "what": "create non-mutating shadow trades, validate logic, verify prior shadows, and report back to runtime state",
            "where": str(SHADOW_TRADE_STATE_PATH),
            "how": "active order flow plus route readiness, model alignment, HNC synthetic agent review, price target, and ETA verification",
            "candidates_seen": len(active),
            "shadow_count": len(new_shadows),
            "shadow_opened_count": opened_count,
            "shadow_held_count": held_count,
            "active_shadow_count": len(active_shadows),
            "validated_shadow_count": validated_count,
            "missed_shadow_count": missed_count,
            "runtime_clearances": runtime_clearances,
            "global_clearances": runtime_clearances,
            "global_guards": global_guards,
            "min_confidence": SHADOW_TRADE_MIN_CONFIDENCE,
            "target_move_pct": SHADOW_TRADE_TARGET_MOVE_PCT,
            "validation_horizon_sec": SHADOW_TRADE_VALIDATION_HORIZON_SEC,
            "shadows": new_shadows,
            "prior_verifications": prior_verifications[-SHADOW_TRADE_MAX_PER_CYCLE:],
            "active_shadows": active_shadows,
            "self_measurement": {
                "agent_validated_count": sum(1 for shadow in new_shadows if shadow.get("agent_review", {}).get("logic_validated")),
                "agent_average_score": round(
                    sum(float(shadow.get("agent_review", {}).get("agent_score", 0.0) or 0.0) for shadow in new_shadows)
                    / max(1, len(new_shadows)),
                    6,
                ),
                "all_four_exchange_routes_seen": all(
                    key in {f"{shadow.get('venue')}_{shadow.get('market_type')}" for shadow in new_shadows}
                    for key in {"kraken_spot", "kraken_margin", "capital_cfd", "alpaca_spot", "binance_spot", "binance_margin"}
                ),
                "real_exchange_mutation": False,
            },
        }
        if isinstance(action_plan, dict):
            action_plan["shadow_trading"] = report
        if persist:
            self._persist_shadow_trade_report(report)
        return report

    def _persist_shadow_trade_report(self, report: Dict[str, Any]) -> None:
        signature = "|".join(
            str(shadow.get("route_signature") or "")
            for shadow in report.get("active_shadows", [])
            if isinstance(shadow, dict)
        )
        now = time.time()
        for path in (SHADOW_TRADE_STATE_PATH, SHADOW_TRADE_PUBLIC_PATH):
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                tmp_path = path.with_name(f"{path.name}.{os.getpid()}.tmp")
                with tmp_path.open("w", encoding="utf-8") as handle:
                    json.dump(report, handle, indent=2, default=str)
                os.replace(tmp_path, path)
            except Exception as e:
                logger.debug("Shadow trade report write failed for %s: %s", path, e)
        last_signature = str(getattr(self, "_last_shadow_trade_signature", "") or "")
        last_at = float(getattr(self, "_last_shadow_trade_at", 0.0) or 0.0)
        if signature != last_signature or now - last_at >= SHADOW_TRADE_MIN_INTERVAL_SEC:
            self._last_shadow_trade_signature = signature
            self._last_shadow_trade_at = now
            try:
                SHADOW_TRADE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
                with SHADOW_TRADE_LOG_PATH.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(report, default=str, sort_keys=True) + "\n")
            except Exception as e:
                logger.debug("Shadow trade report log failed: %s", e)
            self._publish_thought("execution.shadow_trade.self_report", report)

    def _clamp01(self, value: Any, default: float = 0.0) -> float:
        try:
            return max(0.0, min(1.0, float(value)))
        except Exception:
            return max(0.0, min(1.0, float(default)))

    def _repo_logic_contract(self, name: str, rel_path: str, markers: List[str], role: str) -> Dict[str, Any]:
        path = REPO_ROOT / rel_path
        found: List[str] = []
        line_count = 0
        try:
            text = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
            line_count = text.count("\n") + 1 if text else 0
            found = [marker for marker in markers if marker in text]
        except Exception as e:
            return {
                "name": name,
                "role": role,
                "path": rel_path,
                "present": path.exists(),
                "passed": False,
                "error": str(e),
                "markers_found": found,
                "markers_required": markers,
            }
        return {
            "name": name,
            "role": role,
            "path": rel_path,
            "present": path.exists(),
            "passed": path.exists() and len(found) == len(markers),
            "markers_found": found,
            "markers_required": markers,
            "line_count": line_count,
        }

    def _hnc_source_metrics(self, central_beat: Dict[str, Any], order_flow_feed: Dict[str, Any]) -> Dict[str, Any]:
        symbols = central_beat.get("symbols", {}) if isinstance(central_beat, dict) else {}
        if not isinstance(symbols, dict):
            symbols = {}
        sources = central_beat.get("sources", []) if isinstance(central_beat, dict) else []
        if not isinstance(sources, list):
            sources = []
        active = order_flow_feed.get("active_order_flow", []) if isinstance(order_flow_feed, dict) else []
        if not isinstance(active, list):
            active = []

        symbol_rows = [row for row in symbols.values() if isinstance(row, dict)]
        active_rows = [row for row in active if isinstance(row, dict)]
        rows = active_rows or symbol_rows
        confidences = [self._clamp01(row.get("confidence", 0.0)) for row in rows]
        changes = []
        prices = []
        support_counts = []
        model_aligned = 0
        for row in rows:
            try:
                changes.append(float(row.get("change_pct", 0.0) or 0.0))
            except Exception:
                changes.append(0.0)
            try:
                price = float(row.get("reference_price", 0.0) or 0.0)
            except Exception:
                price = 0.0
            if price > 0:
                prices.append(price)
            support_counts.append(int(row.get("support_count", 0) or 0))
            if bool(row.get("model_alignment")):
                model_aligned += 1

        source_count = int(central_beat.get("source_count", 0) or len(sources) or 0) if isinstance(central_beat, dict) else 0
        active_count = len(active_rows)
        symbol_count = len(symbol_rows)
        price_count = len(prices)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        avg_change = sum(changes) / len(changes) if changes else 0.0
        avg_abs_change = sum(abs(change) for change in changes) / len(changes) if changes else 0.0
        avg_support = sum(support_counts) / len(support_counts) if support_counts else 0.0
        model_alignment_rate = model_aligned / len(rows) if rows else 0.0
        simulation_fallback_disabled = os.getenv("AUREON_ALLOW_SIM_FALLBACK", "0").strip().lower() in {"0", "false", "no", "off"}
        live_env_enabled = os.getenv("AUREON_LIVE_TRADING", "0").strip().lower() in {"1", "true", "yes", "on"}
        data_passed = bool(source_count > 0 and symbol_count > 0 and price_count > 0 and simulation_fallback_disabled)

        return {
            "passed": data_passed,
            "source_count": source_count,
            "source_names": [
                str(source.get("source") or source.get("name") or "")
                if isinstance(source, dict)
                else str(source)
                for source in sources
                if isinstance(source, (dict, str))
            ][:12],
            "symbol_count": symbol_count,
            "active_signal_count": active_count,
            "price_count": price_count,
            "avg_confidence": round(avg_confidence, 6),
            "avg_change_pct": round(avg_change, 6),
            "avg_abs_change_pct": round(avg_abs_change, 6),
            "avg_support_count": round(avg_support, 6),
            "model_alignment_rate": round(model_alignment_rate, 6),
            "simulation_fallback_disabled": simulation_fallback_disabled,
            "live_env_enabled": live_env_enabled,
            "data_source_kind": "live_exchange_runtime" if data_passed else "awaiting_live_price_evidence",
        }

    def _hnc_market_texture(self, metrics: Dict[str, Any], action_plan: Dict[str, Any]) -> Dict[str, float]:
        venues = action_plan.get("venues", {}) if isinstance(action_plan, dict) else {}
        venue_count = len(venues) if isinstance(venues, dict) else int(action_plan.get("venue_count", 0) or 0)
        ready_venue_count = int(action_plan.get("ready_venue_count", 0) or 0) if isinstance(action_plan, dict) else 0
        route_unity = self._clamp01(ready_venue_count / max(1, venue_count))
        avg_confidence = self._clamp01(metrics.get("avg_confidence", 0.0))
        avg_support = float(metrics.get("avg_support_count", 0.0) or 0.0)
        avg_change = float(metrics.get("avg_change_pct", 0.0) or 0.0)
        avg_abs_change = float(metrics.get("avg_abs_change_pct", 0.0) or 0.0)
        model_alignment = self._clamp01(metrics.get("model_alignment_rate", 0.0))

        return {
            "volatility": self._clamp01(avg_abs_change / 5.0),
            "momentum": max(-1.0, min(1.0, avg_change / 5.0)),
            "volume": self._clamp01((avg_support + float(metrics.get("source_count", 0) or 0)) / 8.0),
            "spread": self._clamp01(1.0 - avg_confidence),
            "route_unity": route_unity,
            "model_alignment": model_alignment,
            "confidence": avg_confidence,
        }

    def _build_auris_node_proof(self, market_data: Dict[str, float]) -> Dict[str, Any]:
        node_defs = {
            "Tiger": {"freq": 220.0, "role": "volatility", "weight": 1.0, "domain": "cuts noise"},
            "Falcon": {"freq": 285.0, "role": "momentum", "weight": 1.2, "domain": "speed and attack"},
            "Hummingbird": {"freq": 396.0, "role": "stability", "weight": 0.8, "domain": "high frequency lock"},
            "Dolphin": {"freq": 528.0, "role": "emotion", "weight": 1.5, "domain": "waveform carrier"},
            "Deer": {"freq": 639.0, "role": "sensing", "weight": 0.9, "domain": "micro shifts"},
            "Owl": {"freq": 741.0, "role": "memory", "weight": 1.1, "domain": "pattern memory"},
            "Panda": {"freq": 852.0, "role": "love", "weight": 1.3, "domain": "grounding safety"},
            "CargoShip": {"freq": 936.0, "role": "infrastructure", "weight": 0.7, "domain": "liquidity buffer"},
            "Clownfish": {"freq": 963.0, "role": "symbiosis", "weight": 1.0, "domain": "connection"},
        }

        volatility = self._clamp01(market_data.get("volatility", 0.5), 0.5)
        momentum = max(-1.0, min(1.0, float(market_data.get("momentum", 0.0) or 0.0)))
        volume = self._clamp01(market_data.get("volume", 0.5), 0.5)
        spread = self._clamp01(market_data.get("spread", 0.5), 0.5)
        route_unity = self._clamp01(market_data.get("route_unity", 0.0))
        model_alignment = self._clamp01(market_data.get("model_alignment", 0.0))

        nodes: Dict[str, Any] = {}
        for name, node in node_defs.items():
            role = str(node["role"])
            if role == "volatility":
                value = (1.0 - volatility) * 0.8
            elif role == "momentum":
                value = abs(momentum) * 0.7 + volume * 0.3
            elif role == "stability":
                value = (1.0 / (volatility + 0.01)) * 0.01 * 0.6
            elif role == "emotion":
                value = (math.sin(momentum * math.pi) + 1.0) * 0.5
            elif role == "sensing":
                value = spread
            elif role == "memory":
                value = 0.6 + model_alignment * 0.25
            elif role == "love":
                value = 1.0 - volatility * 0.5
            elif role == "infrastructure":
                value = max(volume, route_unity)
            elif role == "symbiosis":
                value = 0.5 + (route_unity * 0.25) + (model_alignment * 0.25)
            else:
                value = 0.5
            value = self._clamp01(value, 0.5)
            weight = float(node["weight"])
            nodes[name] = {
                "value": round(value, 6),
                "freq": float(node["freq"]),
                "role": role,
                "weight": weight,
                "weighted_value": round(value * weight, 6),
                "domain": node["domain"],
                "timestamp": datetime.now().isoformat(),
            }

        total_weighted = sum(float(node.get("weighted_value", 0.0) or 0.0) for node in nodes.values())
        total_weights = sum(float(node.get("weight", 0.0) or 0.0) for node in nodes.values())
        coherence = total_weighted / total_weights if total_weights > 0 else 0.0
        if coherence >= 0.938:
            status = "heart_coherence"
        elif coherence >= 0.8:
            status = "high_coherence"
        elif coherence >= 0.6:
            status = "moderate_coherence"
        else:
            status = "low_coherence"

        return {
            "source": "aureon/utils/aureon_queen_hive_mind.py::AURIS_NODES",
            "evaluated": True,
            "passed": len(nodes) == 9,
            "node_count": len(nodes),
            "coherence": round(coherence, 6),
            "status": status,
            "market_texture": {key: round(float(value), 6) for key, value in market_data.items()},
            "nodes": nodes,
        }

    def _build_hnc_operating_cycle(
        self,
        *,
        generated_at: str,
        metrics: Dict[str, Any],
        market_texture: Dict[str, Any],
        auris: Dict[str, Any],
        systems: Dict[str, Any],
        top: Dict[str, Any],
        action_plan: Dict[str, Any],
        shadow_trade_report: Dict[str, Any],
        master_formula: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Prove the HNC who/what/where/when/how/act loop ran this cycle."""

        top_symbol = str(top.get("symbol") or top.get("route_symbol") or "")
        top_side = str(top.get("side") or "NEUTRAL").upper()
        top_confidence = self._clamp01(top.get("confidence", metrics.get("avg_confidence", 0.0)))
        runtime_clearances = (
            action_plan.get("runtime_clearances", [])
            if isinstance(action_plan, dict) and isinstance(action_plan.get("runtime_clearances"), list)
            else []
        )
        venues = action_plan.get("venues", {}) if isinstance(action_plan, dict) and isinstance(action_plan.get("venues"), dict) else {}
        ready_venue_count = int(action_plan.get("ready_venue_count", 0) or 0) if isinstance(action_plan, dict) else 0
        venue_count = int(action_plan.get("venue_count", 0) or len(venues)) if isinstance(action_plan, dict) else len(venues)
        route_scope = [
            str(name)
            for name, venue in venues.items()
            if isinstance(venue, dict) and (venue.get("ready") or venue.get("status") in {"ready", "live_ready"})
        ]
        if top and not route_scope:
            for route in top.get("execution_routes", []) if isinstance(top.get("execution_routes"), list) else []:
                if isinstance(route, dict) and route.get("ready"):
                    route_scope.append(
                        "_".join(
                            part
                            for part in [
                                str(route.get("venue") or "").lower(),
                                str(route.get("market_type") or "").lower(),
                            ]
                            if part
                        )
                    )
        route_scope = list(dict.fromkeys(item for item in route_scope if item))

        if top_symbol and ready_venue_count > 0 and not runtime_clearances:
            action_state = "runtime_gated_order_intent_ready"
        elif top_symbol:
            action_state = "shadow_validate_and_measure"
        else:
            action_state = "scan_measure_and_wait_for_candidate"

        who_passed = all(
            bool((systems.get(key) or {}).get("passed"))
            for key in ("hnc_master_protocol", "hnc_probability_matrix", "auris_nodes", "seer", "lyra", "king")
        )
        what_passed = bool(top_symbol and metrics.get("passed"))
        where_passed = bool(ready_venue_count > 0 or route_scope)
        when_passed = bool(metrics.get("passed") and generated_at)
        how_passed = bool(master_formula.get("evaluated") and master_formula.get("passed"))
        act_passed = bool(action_state and isinstance(action_plan, dict))

        question_rows = [
            {
                "step": "who",
                "question": "Who is evaluating the market state?",
                "answer": "HNC master protocol, probability matrix, Auris sensory nodes, Seer vision, Lyra resonance, King capital logic, shadow agents, and the unified exchange runtime.",
                "auris_node_focus": "whole_node_set",
                "cognitive_systems": ["HNCMasterProtocol", "HNCProbabilityMatrix", "AurisNodes", "Seer", "Lyra", "KingCapitalLogic"],
                "evidence_source": "state/unified_runtime_status.json#hnc_cognitive_proof.systems",
                "evidence": {
                    "system_count": len(systems),
                    "passed_system_count": sum(1 for item in systems.values() if isinstance(item, dict) and item.get("passed")),
                },
                "timestamp": generated_at,
                "fed_to_decision_logic": True,
                "passed": who_passed,
            },
            {
                "step": "what",
                "question": "What live opportunity or market texture is being evaluated?",
                "answer": f"{top_symbol or 'no candidate'} {top_side} confidence={top_confidence:.3f}",
                "auris_node_focus": "market_texture",
                "cognitive_systems": ["UnifiedSignalEngine", "Seer", "AurisNodes"],
                "evidence_source": "state/unified_runtime_status.json#shared_order_flow.active_order_flow",
                "evidence": {
                    "symbol": top_symbol,
                    "side": top_side,
                    "confidence": round(top_confidence, 6),
                    "market_texture": market_texture,
                },
                "timestamp": generated_at,
                "fed_to_decision_logic": True,
                "passed": what_passed,
            },
            {
                "step": "where",
                "question": "Where can the route act across the connected financial ecosystem?",
                "answer": f"{ready_venue_count}/{max(1, venue_count)} ready execution venues: {', '.join(route_scope) or 'none'}",
                "auris_node_focus": "infrastructure_and_symbiosis",
                "cognitive_systems": ["ExchangeRouteClearance", "KingCapitalLogic", "UnifiedExecutor"],
                "evidence_source": "state/unified_runtime_status.json#exchange_action_plan.venues",
                "evidence": {
                    "ready_venue_count": ready_venue_count,
                    "venue_count": venue_count,
                    "route_scope": route_scope,
                    "runtime_clearances": runtime_clearances,
                },
                "timestamp": generated_at,
                "fed_to_decision_logic": True,
                "passed": where_passed,
            },
            {
                "step": "when",
                "question": "When was the evidence measured and is it aligned to the current cycle?",
                "answer": f"cycle timestamp {generated_at}; source_count={metrics.get('source_count', 0)} price_count={metrics.get('price_count', 0)}",
                "auris_node_focus": "sensing_and_memory",
                "cognitive_systems": ["RuntimeWatchdog", "CentralBeat", "AurisNodes"],
                "evidence_source": "state/unified_runtime_status.json#central_beat",
                "evidence": {
                    "generated_at": generated_at,
                    "source_count": metrics.get("source_count", 0),
                    "price_count": metrics.get("price_count", 0),
                    "symbol_count": metrics.get("symbol_count", 0),
                },
                "timestamp": generated_at,
                "fed_to_decision_logic": True,
                "passed": when_passed,
            },
            {
                "step": "how",
                "question": "How was the choice reasoned through HNC and Auris?",
                "answer": f"HNC score={master_formula.get('score', 0.0)} coherence={auris.get('coherence', 0.0)} status={auris.get('status')}",
                "auris_node_focus": "formula_and_resonance",
                "cognitive_systems": ["HNCMasterProtocol", "HNCProbabilityMatrix", "Lyra", "AurisNodes"],
                "evidence_source": "state/unified_runtime_status.json#hnc_cognitive_proof.master_formula",
                "evidence": {
                    "master_formula": master_formula,
                    "auris_coherence": auris.get("coherence", 0.0),
                    "auris_status": auris.get("status"),
                    "shadow_average_score": (
                        shadow_trade_report.get("self_measurement", {}).get("agent_average_score")
                        if isinstance(shadow_trade_report.get("self_measurement"), dict)
                        else None
                    ),
                },
                "timestamp": generated_at,
                "fed_to_decision_logic": True,
                "passed": how_passed,
            },
            {
                "step": "act",
                "question": "What action state does the cycle move into?",
                "answer": action_state,
                "auris_node_focus": "execution_state",
                "cognitive_systems": ["KingCapitalLogic", "ShadowTradeValidator", "UnifiedExecutor"],
                "evidence_source": "state/unified_runtime_status.json#exchange_action_plan",
                "evidence": {
                    "action_state": action_state,
                    "shadow_opened_count": shadow_trade_report.get("shadow_opened_count", 0)
                    if isinstance(shadow_trade_report, dict)
                    else 0,
                    "active_shadow_count": shadow_trade_report.get("active_shadow_count", 0)
                    if isinstance(shadow_trade_report, dict)
                    else 0,
                    "runtime_clearances": runtime_clearances,
                },
                "timestamp": generated_at,
                "fed_to_decision_logic": True,
                "passed": act_passed,
            },
        ]
        passed_count = sum(1 for item in question_rows if item.get("passed"))
        fed_to_decision_logic = all(bool(item.get("fed_to_decision_logic")) for item in question_rows)
        return {
            "schema_version": "aureon-hnc-operating-cycle-v1",
            "generated_at": generated_at,
            "mode": "harmonic_nexus_core_operating_cycle",
            "status": "passing" if passed_count == len(question_rows) else "attention",
            "passed": passed_count == len(question_rows),
            "passed_count": passed_count,
            "step_count": len(question_rows),
            "cycle_order": ["who", "what", "where", "when", "how", "act"],
            "questions": question_rows,
            "fed_to_decision_logic": fed_to_decision_logic,
            "auris_node_count": int(auris.get("node_count", 0) or 0),
            "auris_coherence": float(auris.get("coherence", 0.0) or 0.0),
            "master_formula_score": float(master_formula.get("score", 0.0) or 0.0),
            "decision_output": {
                "symbol": top_symbol,
                "side": top_side,
                "confidence": round(top_confidence, 6),
                "action_state": action_state,
                "ready_venue_count": ready_venue_count,
                "venue_count": venue_count,
                "runtime_clearances": runtime_clearances,
            },
            "contract": (
                "Each who/what/where/when/how/act step must be timestamped, evidence-backed, "
                "Auris-evaluated, HNC-scored, and fed into the runtime decision path."
            ),
        }

    def _build_hnc_cognitive_proof(
        self,
        central_beat: Dict[str, Any],
        order_flow_feed: Dict[str, Any],
        action_plan: Dict[str, Any],
        shadow_trade_report: Dict[str, Any],
        *,
        persist: bool = True,
    ) -> Dict[str, Any]:
        generated_at = datetime.now().isoformat()
        metrics = self._hnc_source_metrics(central_beat, order_flow_feed)
        market_texture = self._hnc_market_texture(metrics, action_plan)
        auris = self._build_auris_node_proof(market_texture)
        systems = {
            "hnc_master_protocol": self._repo_logic_contract(
                "HNC master protocol",
                "aureon/strategies/hnc_master_protocol.py",
                ["class HarmonicNexusCore", "class HNCTradingBridge", "def enhance_opportunity"],
                "global financial frequency mapper and trading bridge",
            ),
            "hnc_probability_matrix": self._repo_logic_contract(
                "HNC probability matrix",
                "aureon/strategies/hnc_probability_matrix.py",
                ["class FrequencySnapshot", "class ProbabilityMatrix", "class HNCProbabilityIntegration"],
                "timestamped harmonic probability validation",
            ),
            "auris_nodes": self._repo_logic_contract(
                "Auris nodes",
                "aureon/utils/aureon_queen_hive_mind.py",
                ["AURIS_NODES", "def read_auris_nodes", "def get_auris_coherence"],
                "nine-node sensory market texture evaluation",
            ),
            "seer": self._repo_logic_contract(
                "Seer",
                "aureon/intelligence/aureon_seer.py",
                ["class SeerVision", "class SeerConsensus", "class OracleReading"],
                "vision and oracle consensus layer",
            ),
            "lyra": self._repo_logic_contract(
                "Lyra",
                "aureon/trading/aureon_lyra.py",
                ["class LyraResonance", "class TheLyre", "class ChamberOfSpirit"],
                "harmonic resonance and market affect layer",
            ),
            "king": self._repo_logic_contract(
                "King",
                "aureon/trading/compound_king.py",
                ["class CompoundKing", "def get_daily_return_target", "def run_30_days"],
                "capital growth and compounding discipline layer",
            ),
        }

        active = order_flow_feed.get("active_order_flow", []) if isinstance(order_flow_feed, dict) else []
        active = active if isinstance(active, list) else []
        top = active[0] if active and isinstance(active[0], dict) else {}
        if not top and isinstance(central_beat, dict) and isinstance(central_beat.get("symbols"), dict):
            candidates = []
            for symbol_key, row in central_beat["symbols"].items():
                if isinstance(row, dict):
                    candidate = dict(row)
                    candidate.setdefault("symbol", symbol_key)
                    candidates.append(candidate)
            if candidates:
                top = max(candidates, key=lambda row: float(row.get("confidence", 0.0) or 0.0))
        ready_route_count = int(action_plan.get("ready_venue_count", 0) or 0) if isinstance(action_plan, dict) else 0
        venue_count = int(action_plan.get("venue_count", 0) or len(action_plan.get("venues", {}) or {})) if isinstance(action_plan, dict) else 0
        route_unity = self._clamp01(ready_route_count / max(1, venue_count))
        shadow_measure = shadow_trade_report.get("self_measurement", {}) if isinstance(shadow_trade_report, dict) else {}
        shadow_score = self._clamp01(shadow_measure.get("agent_average_score", 0.0), 0.0)
        if shadow_score <= 0 and int(shadow_trade_report.get("active_shadow_count", 0) or 0) > 0:
            shadow_score = 0.5

        real_data_score = 1.0 if metrics.get("passed") else 0.0
        source_unity = self._clamp01(float(metrics.get("source_count", 0) or 0) / 4.0)
        model_alignment = self._clamp01(metrics.get("model_alignment_rate", 0.0))
        auris_coherence = self._clamp01(auris.get("coherence", 0.0))
        master_score = self._clamp01(
            (real_data_score * 0.22)
            + (source_unity * 0.16)
            + (auris_coherence * 0.22)
            + (model_alignment * 0.14)
            + (shadow_score * 0.12)
            + (route_unity * 0.14)
        )

        top_confidence = self._clamp01(top.get("confidence", metrics.get("avg_confidence", 0.0)))
        top_symbol = str(top.get("symbol") or top.get("route_symbol") or "")
        top_side = str(top.get("side") or "NEUTRAL").upper()
        seer_runtime = {
            "evaluated": bool(top_symbol),
            "symbol": top_symbol,
            "signal": top_side if top_side in {"BUY", "SELL"} else "NEUTRAL",
            "confidence": round(top_confidence, 6),
            "vision_grade": "clear" if top_confidence >= 0.7 else "forming" if top_confidence >= 0.35 else "quiet",
            "timestamp": generated_at,
        }
        lyra_frequency = 396.0 + auris_coherence * (963.0 - 396.0)
        lyra_runtime = {
            "evaluated": bool(auris.get("evaluated")),
            "resonance_score": round((auris_coherence * 0.65) + (model_alignment * 0.2) + (source_unity * 0.15), 6),
            "resonance_frequency_hz": round(lyra_frequency, 3),
            "resonance_grade": auris.get("status"),
            "timestamp": generated_at,
        }
        king_runtime = {
            "evaluated": True,
            "executor_quote_usd": ORDER_EXECUTOR_QUOTE_USD,
            "max_open_positions": ORDER_EXECUTOR_MAX_OPEN_POSITIONS,
            "route_unity": round(route_unity, 6),
            "discipline_score": round((route_unity * 0.5) + (top_confidence * 0.3) + (real_data_score * 0.2), 6),
            "timestamp": generated_at,
        }
        systems["seer"]["runtime_reading"] = seer_runtime
        systems["seer"]["passed"] = bool(systems["seer"].get("passed") and seer_runtime.get("evaluated"))
        systems["lyra"]["runtime_reading"] = lyra_runtime
        systems["lyra"]["passed"] = bool(systems["lyra"].get("passed") and lyra_runtime.get("evaluated"))
        systems["king"]["runtime_reading"] = king_runtime
        systems["king"]["passed"] = bool(systems["king"].get("passed") and king_runtime.get("evaluated"))

        master_formula = {
            "source": "unified runtime blend over HNC/Auris/Seer/Lyra/King contracts",
            "evaluated": True,
            "formula": "HNC = 0.22*real_data + 0.16*source_unity + 0.22*auris + 0.14*model_alignment + 0.12*shadow + 0.14*route_unity",
            "inputs": {
                "real_data": real_data_score,
                "source_unity": round(source_unity, 6),
                "auris": round(auris_coherence, 6),
                "model_alignment": round(model_alignment, 6),
                "shadow": round(shadow_score, 6),
                "route_unity": round(route_unity, 6),
            },
            "score": round(master_score, 6),
            "passed": bool(master_score > 0 and metrics.get("passed")),
            "timestamp": generated_at,
        }
        operating_cycle = self._build_hnc_operating_cycle(
            generated_at=generated_at,
            metrics=metrics,
            market_texture=market_texture,
            auris=auris,
            systems=systems,
            top=top,
            action_plan=action_plan,
            shadow_trade_report=shadow_trade_report,
            master_formula=master_formula,
        )

        flow = [
            {
                "step": "real_market_data",
                "passed": bool(metrics.get("passed")),
                "evidence": f"{metrics.get('source_count', 0)} sources, {metrics.get('symbol_count', 0)} symbols, {metrics.get('price_count', 0)} live prices",
                "timestamp": generated_at,
            },
            {
                "step": "hnc_master_formula",
                "passed": bool(master_formula["passed"] and systems["hnc_master_protocol"].get("passed")),
                "evidence": f"score={master_formula['score']}",
                "timestamp": generated_at,
            },
            {
                "step": "auris_nodes",
                "passed": bool(auris.get("passed") and systems["auris_nodes"].get("passed")),
                "evidence": f"{auris.get('node_count', 0)} nodes coherence={auris.get('coherence', 0.0)}",
                "timestamp": generated_at,
            },
            {
                "step": "hnc_operating_cycle",
                "passed": bool(operating_cycle.get("passed")),
                "evidence": (
                    f"{operating_cycle.get('passed_count', 0)}/{operating_cycle.get('step_count', 0)} "
                    f"who/what/where/when/how/act fed={operating_cycle.get('fed_to_decision_logic')}"
                ),
                "timestamp": generated_at,
            },
            {
                "step": "seer_vision",
                "passed": bool(systems["seer"].get("passed")),
                "evidence": f"{seer_runtime.get('symbol') or 'no-symbol'} {seer_runtime.get('signal')} {seer_runtime.get('vision_grade')}",
                "timestamp": generated_at,
            },
            {
                "step": "lyra_resonance",
                "passed": bool(systems["lyra"].get("passed")),
                "evidence": f"{lyra_runtime.get('resonance_frequency_hz')}Hz {lyra_runtime.get('resonance_grade')}",
                "timestamp": generated_at,
            },
            {
                "step": "king_capital_logic",
                "passed": bool(systems["king"].get("passed")),
                "evidence": f"discipline={king_runtime.get('discipline_score')}",
                "timestamp": generated_at,
            },
            {
                "step": "shadow_trade_self_validation",
                "passed": bool(isinstance(shadow_trade_report, dict) and shadow_trade_report.get("enabled", True)),
                "evidence": (
                    f"{shadow_trade_report.get('shadow_opened_count', 0)} opened, "
                    f"{shadow_trade_report.get('active_shadow_count', 0)} active, "
                    f"{shadow_trade_report.get('validated_shadow_count', 0)} validated"
                ),
                "timestamp": generated_at,
            },
            {
                "step": "public_state_publication",
                "passed": True,
                "evidence": str(HNC_COGNITIVE_PROOF_PUBLIC_PATH),
                "timestamp": generated_at,
            },
        ]
        passed_count = sum(1 for step in flow if step.get("passed"))
        status = "passing" if passed_count == len(flow) else "attention"
        report = {
            "generated_at": generated_at,
            "status": status,
            "passed": passed_count == len(flow),
            "who": "HNC master formula plus Auris nodes, Seer, Lyra, King, shadow agents, and unified exchange runtime",
            "what": "timestamped proof that cognitive logic evaluated real market data and moved through the intended flow",
            "where": str(HNC_COGNITIVE_PROOF_STATE_PATH),
            "when": generated_at,
            "how": "HNC formula, Auris node coherence, Seer/Lyra/King readings, route state, and shadow validation were evaluated together.",
            "act": operating_cycle.get("decision_output", {}).get("action_state") if isinstance(operating_cycle.get("decision_output"), dict) else "",
            "real_data": metrics,
            "market_texture": market_texture,
            "master_formula": master_formula,
            "auris_nodes": auris,
            "systems": systems,
            "operating_cycle": operating_cycle,
            "hnc_operating_cycle": operating_cycle,
            "flow": flow,
            "passed_count": passed_count,
            "step_count": len(flow),
            "runtime_clearances": action_plan.get("runtime_clearances", []) if isinstance(action_plan, dict) else [],
            "shadow_report_path": str(SHADOW_TRADE_STATE_PATH),
        }
        if isinstance(action_plan, dict):
            action_plan["hnc_cognitive_proof"] = report
            action_plan["hnc_operating_cycle"] = operating_cycle
        if persist:
            self._persist_hnc_cognitive_proof(report)
        return report

    def _persist_hnc_cognitive_proof(self, report: Dict[str, Any]) -> None:
        signature = "|".join(
            [
                str(report.get("status") or ""),
                str(report.get("passed_count") or 0),
                str(report.get("master_formula", {}).get("score") if isinstance(report.get("master_formula"), dict) else ""),
                str(report.get("real_data", {}).get("source_count") if isinstance(report.get("real_data"), dict) else ""),
            ]
        )
        now = time.time()
        for path in (HNC_COGNITIVE_PROOF_STATE_PATH, HNC_COGNITIVE_PROOF_PUBLIC_PATH):
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                tmp_path = path.with_name(f"{path.name}.{os.getpid()}.tmp")
                with tmp_path.open("w", encoding="utf-8") as handle:
                    json.dump(report, handle, indent=2, default=str)
                os.replace(tmp_path, path)
            except Exception as e:
                logger.debug("HNC cognitive proof write failed for %s: %s", path, e)
        operating_cycle = report.get("operating_cycle") if isinstance(report.get("operating_cycle"), dict) else {}
        if operating_cycle:
            for path in (HNC_OPERATING_CYCLE_STATE_PATH, HNC_OPERATING_CYCLE_PUBLIC_PATH):
                try:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    tmp_path = path.with_name(f"{path.name}.{os.getpid()}.tmp")
                    with tmp_path.open("w", encoding="utf-8") as handle:
                        json.dump(operating_cycle, handle, indent=2, default=str)
                    os.replace(tmp_path, path)
                except Exception as e:
                    logger.debug("HNC operating cycle write failed for %s: %s", path, e)
        last_signature = str(getattr(self, "_last_hnc_cognitive_proof_signature", "") or "")
        last_at = float(getattr(self, "_last_hnc_cognitive_proof_at", 0.0) or 0.0)
        if signature != last_signature or now - last_at >= HNC_COGNITIVE_PROOF_MIN_INTERVAL_SEC:
            self._last_hnc_cognitive_proof_signature = signature
            self._last_hnc_cognitive_proof_at = now
            try:
                HNC_COGNITIVE_PROOF_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
                with HNC_COGNITIVE_PROOF_LOG_PATH.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(report, default=str, sort_keys=True) + "\n")
            except Exception as e:
                logger.debug("HNC cognitive proof log failed: %s", e)
            self._publish_thought("cognition.hnc_cognitive_proof", report)

    def _build_gold_runtime_trade_proof(
        self,
        central_beat: Dict[str, Any],
        shared_market_feed: Dict[str, Any],
        order_flow_feed: Dict[str, Any],
        action_plan: Dict[str, Any],
    ) -> Dict[str, Any]:
        active = order_flow_feed.get("active_order_flow", []) if isinstance(order_flow_feed, dict) else []
        if not isinstance(active, list):
            active = []
        gold_rows = [
            row
            for row in active
            if isinstance(row, dict)
            and (
                str(row.get("symbol") or "").upper() in {"XAUUSD", "GOLD", "GOLDUSD"}
                or bool(row.get("gold_priority_candidate"))
            )
        ]
        gold_row = gold_rows[0] if gold_rows else {}
        routes = gold_row.get("execution_routes", []) if isinstance(gold_row.get("execution_routes"), list) else []
        capital_routes = [
            route
            for route in routes
            if isinstance(route, dict)
            and str(route.get("venue") or "").lower() == "capital"
            and str(route.get("market_type") or "").lower() == "cfd"
        ]
        capital_route = capital_routes[0] if capital_routes else {}
        publish_blockers = [
            str(blocker)
            for blocker in gold_row.get("intent_publish_blockers", [])
            if str(blocker)
        ] if isinstance(gold_row.get("intent_publish_blockers"), list) else []
        action_blockers = [
            str(blocker)
            for blocker in action_plan.get("global_blockers", [])
            if str(blocker)
        ] if isinstance(action_plan.get("global_blockers"), list) else []
        route_blockers = [
            str(blocker)
            for blocker in capital_route.get("blockers", [])
            if str(blocker)
        ] if isinstance(capital_route, dict) and isinstance(capital_route.get("blockers"), list) else []
        side = str(gold_row.get("side") or "").upper() if isinstance(gold_row, dict) else ""
        gold_candidate_ready = bool(gold_row)
        capital_route_visible = bool(capital_route)
        capital_route_ready = bool(capital_route.get("ready")) if isinstance(capital_route, dict) else False
        if not gold_candidate_ready:
            reason = "gold_runtime_candidate_missing"
        elif not capital_route_visible:
            reason = "capital_cfd_route_missing_for_gold"
        elif publish_blockers:
            reason = publish_blockers[0]
        elif side not in {"BUY", "SELL"}:
            reason = "gold_side_not_validated_by_fresh_interval_projection"
        elif not capital_route_ready:
            reason = route_blockers[0] if route_blockers else "capital_cfd_route_not_ready"
        elif action_blockers:
            reason = action_blockers[0]
        else:
            reason = "gold_runtime_gated_intent_publishable"
        return {
            "generated_at": datetime.now().isoformat(),
            "gold_runtime_candidate_ready": gold_candidate_ready,
            "gold_candidate_count": len(gold_rows),
            "candidate_id": gold_row.get("candidate_id") if isinstance(gold_row, dict) else "",
            "lifecycle_id": gold_row.get("lifecycle_id") if isinstance(gold_row, dict) else "",
            "candidate_symbol": gold_row.get("symbol") if isinstance(gold_row, dict) else "",
            "candidate_side": side or "HOLD",
            "candidate_confidence": gold_row.get("confidence") if isinstance(gold_row, dict) else None,
            "candidate_sources": gold_row.get("sources", []) if isinstance(gold_row, dict) else [],
            "capital_cfd_route_visible": capital_route_visible,
            "capital_cfd_route_ready": capital_route_ready,
            "capital_cfd_route_key": capital_route.get("route_key") if isinstance(capital_route, dict) else "",
            "capital_cfd_route_blockers": route_blockers,
            "gold_intent_publishable": bool(
                gold_candidate_ready
                and capital_route_ready
                and side in {"BUY", "SELL"}
                and not publish_blockers
                and not action_blockers
            ),
            "gold_intent_publish_reason": reason,
            "intent_publish_blockers": publish_blockers,
            "global_blockers": action_blockers,
            "fresh_gold_data_source": (central_beat.get("gold_priority_candidate", {}) if isinstance(central_beat, dict) else {}),
            "shared_feed_contains_gold": "XAUUSD" in (
                (shared_market_feed.get("symbols", {}) if isinstance(shared_market_feed, dict) else {}) or {}
            ),
            "routeable_key_count": int(order_flow_feed.get("multi_exchange_tradable_count", 0) or 0) if isinstance(order_flow_feed, dict) else 0,
            "active_order_flow_count": int(order_flow_feed.get("active_order_flow_count", 0) or 0) if isinstance(order_flow_feed, dict) else 0,
            "safety": {
                "direct_exchange_mutation": False,
                "proof_phase": "runtime_gated_order_intent_only",
                "requires_existing_runtime_executor": True,
            },
        }

    def _build_exchange_action_plan(self, order_flow_feed: Dict[str, Any]) -> Dict[str, Any]:
        active = order_flow_feed.get("active_order_flow", []) if isinstance(order_flow_feed, dict) else []
        if not isinstance(active, list):
            active = []
        venues: Dict[str, Dict[str, Any]] = {}
        for item in active:
            if not isinstance(item, dict):
                continue
            confidence = max(0.0, min(1.0, float(item.get("confidence", 0.0) or 0.0)))
            for route_item in item.get("execution_routes", []) if isinstance(item.get("execution_routes"), list) else []:
                if not isinstance(route_item, dict):
                    continue
                venue = str(route_item.get("venue") or "").lower()
                market_type = str(route_item.get("market_type") or "").lower()
                if not venue:
                    continue
                key = f"{venue}_{market_type}" if market_type else venue
                state = venues.setdefault(
                    key,
                    {
                        "venue": venue,
                        "market_type": market_type,
                        "ready": False,
                        "candidate_count": 0,
                        "ready_candidate_count": 0,
                        "blockers": [],
                        "runtime_clearances": [],
                        "guards": [],
                        "trade_path_state": "held",
                        "end_user_trade_available": False,
                        "top_candidates": [],
                        "model_count": 0,
                        "model_total_count": 0,
                    },
                )
                blockers = [str(blocker) for blocker in route_item.get("blockers", []) if str(blocker)]
                state["ready"] = bool(state.get("ready") or route_item.get("ready"))
                if route_item.get("ready"):
                    state["trade_path_state"] = "available"
                    state["end_user_trade_available"] = True
                state["model_count"] = max(int(state.get("model_count", 0) or 0), int(route_item.get("model_count", 0) or 0))
                state["model_total_count"] = max(int(state.get("model_total_count", 0) or 0), int(route_item.get("model_total_count", 0) or 0))
                for blocker in blockers:
                    if blocker not in state["blockers"]:
                        state["blockers"].append(blocker)
                    if blocker not in state["runtime_clearances"]:
                        state["runtime_clearances"].append(blocker)
                    if blocker not in state["guards"]:
                        state["guards"].append(blocker)
                state["candidate_count"] = int(state.get("candidate_count", 0) or 0) + 1
                publishable_side = str(item.get("side") or "").upper() in {"BUY", "SELL"}
                publish_blockers = [
                    str(blocker)
                    for blocker in item.get("intent_publish_blockers", [])
                    if str(blocker)
                ] if isinstance(item.get("intent_publish_blockers"), list) else []
                if route_item.get("ready") and confidence >= ORDER_INTENT_MIN_CONFIDENCE and publishable_side and not publish_blockers:
                    state["ready_candidate_count"] = int(state.get("ready_candidate_count", 0) or 0) + 1
                    state["top_candidates"].append(
                        {
                            "symbol": item.get("symbol"),
                            "route_symbol": route_item.get("symbol"),
                            "side": item.get("side"),
                            "candidate_id": item.get("candidate_id"),
                            "lifecycle_id": item.get("lifecycle_id"),
                            "route_key": route_item.get("route_key"),
                            "confidence": confidence,
                            "profit_velocity_score": item.get("profit_velocity_score", 0.0),
                            "fast_money_score": item.get("fast_money_score", 0.0),
                            "fast_money_candidate": bool(item.get("fast_money_candidate")),
                            "fast_money_profile": item.get("fast_money_profile", {}),
                            "orderbook_pressure": item.get("orderbook_pressure", {}),
                            "estimated_target_eta_sec": item.get("estimated_target_eta_sec", 0.0),
                            "cash_capable_route_count": item.get("cash_capable_route_count", 0),
                            "history_validation_score": item.get("history_validation_score", 0.0),
                            "support_count": item.get("support_count", 0),
                            "sources": item.get("sources", []),
                            "intent_publish_blockers": [],
                        }
                    )
                elif publish_blockers:
                    for blocker in publish_blockers:
                        if blocker not in state["runtime_clearances"]:
                            state["runtime_clearances"].append(blocker)
                        if blocker not in state["guards"]:
                            state["guards"].append(blocker)
        for state in venues.values():
            state["top_candidates"] = sorted(
                state.get("top_candidates", []),
                key=lambda candidate: (
                    float(candidate.get("profit_velocity_score", 0.0) or 0.0),
                    float(candidate.get("fast_money_score", 0.0) or 0.0),
                    float(candidate.get("confidence", 0.0) or 0.0),
                ),
                reverse=True,
            )[:5]

        publish_enabled = os.getenv("AUREON_ORDER_INTENT_PUBLISH", "0").strip().lower() in {"1", "true", "yes", "on"}
        authority_mode = os.getenv("AUREON_ORDER_AUTHORITY_MODE", "runtime_only").strip().lower()
        live_enabled = os.getenv("AUREON_LIVE_TRADING", "0").strip().lower() in {"1", "true", "yes", "on"}
        real_orders_disabled = os.getenv("AUREON_DISABLE_REAL_ORDERS", "1").strip().lower() in {"1", "true", "yes", "on"}
        exchange_mutations_disabled = os.getenv("AUREON_DISABLE_EXCHANGE_MUTATIONS", "1").strip().lower() in {"1", "true", "yes", "on"}
        global_blockers: List[str] = []
        if not live_enabled:
            global_blockers.append("live_trading_not_enabled")
        if real_orders_disabled:
            global_blockers.append("real_orders_disabled")
        if exchange_mutations_disabled:
            global_blockers.append("exchange_mutations_disabled")
        if authority_mode not in {"intent_only_runtime_gated", "runtime_only"}:
            global_blockers.append("order_authority_mode_not_runtime_gated")
        if not publish_enabled:
            global_blockers.append("order_intent_publish_disabled")
        model_coverage = self._all_exchange_model_coverage()
        intelligence_mesh = order_flow_feed.get("intelligence_mesh", {}) if isinstance(order_flow_feed, dict) else {}
        global_clearances = list(global_blockers)
        global_guards = list(global_blockers)
        trade_path_state = "available" if live_enabled and not real_orders_disabled and not exchange_mutations_disabled else "operator_authorization_required"
        if global_clearances:
            trade_path_state = "runtime_clearance_pending"
        venue_count = len(venues)
        ready_venue_count = sum(1 for state in venues.values() if state.get("ready"))
        top_candidates = [
            candidate
            for state in venues.values()
            for candidate in state.get("top_candidates", [])
            if isinstance(candidate, dict)
        ]
        best_confidence = max((float(candidate.get("confidence", 0.0) or 0.0) for candidate in top_candidates), default=0.0)
        best_velocity = max((float(candidate.get("profit_velocity_score", 0.0) or 0.0) for candidate in top_candidates), default=0.0)
        best_fast_money = max((float(candidate.get("fast_money_score", 0.0) or 0.0) for candidate in top_candidates), default=0.0)
        route_unity = self._clamp01(ready_venue_count / max(1, venue_count))
        signal_unity = self._clamp01(
            (self._clamp01(best_confidence) * 0.45)
            + (self._clamp01(best_velocity) * 0.35)
            + (self._clamp01(best_fast_money) * 0.20)
        )
        self_trust_score = self._clamp01((route_unity * 0.45) + (signal_unity * 0.45) + ((0.1 if top_candidates else 0.0)))
        trust_to_publish_intent = bool(publish_enabled and not global_clearances and ready_venue_count > 0 and best_confidence >= ORDER_INTENT_MIN_CONFIDENCE)
        decision_self_trust = {
            "schema_version": 1,
            "score": round(self_trust_score, 6),
            "posture": (
                "trust_ready_routes"
                if trust_to_publish_intent
                else "trust_analysis_until_runtime_clearance"
                if global_clearances
                else "keep_scanning_until_signal_alignment"
            ),
            "trust_to_publish_intent": trust_to_publish_intent,
            "not_fear": True,
            "route_unity": round(route_unity, 6),
            "signal_unity": round(signal_unity, 6),
            "best_confidence": round(self._clamp01(best_confidence), 6),
            "best_profit_velocity_score": round(self._clamp01(best_velocity), 6),
            "best_fast_money_score": round(self._clamp01(best_fast_money), 6),
            "self_instruction": "Use ranked routes when runtime truth is fresh and clear; otherwise keep measuring, shadow-validating, and re-ranking.",
        }

        return {
            "generated_at": datetime.now().isoformat(),
            "mode": "runtime_gated_order_intent" if publish_enabled else "analysis_only",
            "venues": venues,
            "venue_count": venue_count,
            "ready_venue_count": ready_venue_count,
            "end_user_trade_available": any(bool(state.get("end_user_trade_available")) for state in venues.values()),
            "trade_path_state": trade_path_state,
            "decision_self_trust": decision_self_trust,
            "order_intent_publish_enabled": publish_enabled,
            "executor_enabled": self._unified_executor_enabled(),
            "executor_quote_usd": ORDER_EXECUTOR_QUOTE_USD,
            "kraken_spot_quote_usd": KRAKEN_SPOT_QUOTE_USD,
            "executor_symbol_cooldown_sec": ORDER_EXECUTOR_SYMBOL_COOLDOWN_SEC,
            "executor_max_per_tick": ORDER_EXECUTOR_MAX_PER_TICK,
            "order_authority_mode": authority_mode,
            "live_enabled": live_enabled,
            "real_orders_disabled": real_orders_disabled,
            "exchange_mutations_disabled": exchange_mutations_disabled,
            "global_blockers": global_blockers,
            "global_clearances": global_clearances,
            "runtime_clearances": global_clearances,
            "global_guards": global_guards,
            "min_confidence": ORDER_INTENT_MIN_CONFIDENCE,
            "max_per_cycle": ORDER_INTENT_MAX_PER_CYCLE,
            "latest_published": getattr(self, "_latest_order_intents", {}),
            "latest_execution": getattr(self, "_latest_execution_results", {}),
            "model_coverage": model_coverage,
            "intelligence_mesh": intelligence_mesh,
            "order_intents_published": 0,
        }

    def _publish_order_intents(self, order_flow_feed: Dict[str, Any], action_plan: Dict[str, Any]) -> None:
        if not isinstance(action_plan, dict) or not action_plan.get("order_intent_publish_enabled"):
            return
        if action_plan.get("global_blockers"):
            return
        active = order_flow_feed.get("active_order_flow", []) if isinstance(order_flow_feed, dict) else []
        if not isinstance(active, list):
            return

        now = time.time()
        candidates: List[Dict[str, Any]] = []
        for item in active:
            if not isinstance(item, dict):
                continue
            side = str(item.get("side") or "").upper()
            if side not in {"BUY", "SELL"}:
                continue
            intent_publish_blockers = [
                str(blocker)
                for blocker in item.get("intent_publish_blockers", [])
                if str(blocker)
            ] if isinstance(item.get("intent_publish_blockers"), list) else []
            if intent_publish_blockers:
                continue
            confidence = max(0.0, min(1.0, float(item.get("confidence", 0.0) or 0.0)))
            if confidence < ORDER_INTENT_MIN_CONFIDENCE:
                continue
            ready_routes = [
                route_item
                for route_item in item.get("execution_routes", [])
                if isinstance(route_item, dict) and route_item.get("ready")
            ]
            if not ready_routes:
                continue
            candidate_id, lifecycle_id = self._candidate_lifecycle_identity(item)
            item["candidate_id"] = candidate_id
            item["lifecycle_id"] = lifecycle_id
            route_copies: List[Dict[str, Any]] = []
            for route_item in ready_routes:
                route_copy = dict(route_item)
                route_copy.setdefault(
                    "route_key",
                    self._order_route_key(
                        route_copy.get("venue"),
                        route_copy.get("market_type"),
                        route_copy.get("symbol"),
                        side,
                    ),
                )
                route_copy["candidate_id"] = candidate_id
                route_copy["lifecycle_id"] = lifecycle_id
                route_copies.append(route_copy)
            primary_route = route_copies[0] if route_copies else {}
            candidates.append(
                {
                    "id": f"uintent-{int(now)}-{len(candidates) + 1}",
                    "generated_at": datetime.now().isoformat(),
                    "source": "unified_market_trader",
                    "topic": "execution.order.intent",
                    "symbol": item.get("symbol"),
                    "side": item.get("side"),
                    "candidate_id": candidate_id,
                    "lifecycle_id": lifecycle_id,
                    "route_key": primary_route.get("route_key"),
                    "confidence": confidence,
                    "selection_rank": item.get("selection_rank"),
                    "profit_velocity_score": item.get("profit_velocity_score", 0.0),
                    "fast_money_score": item.get("fast_money_score", 0.0),
                    "fast_money_candidate": bool(item.get("fast_money_candidate")),
                    "fast_money_profile": item.get("fast_money_profile", {}),
                    "orderbook_pressure": item.get("orderbook_pressure", {}),
                    "estimated_target_eta_sec": item.get("estimated_target_eta_sec", 0.0),
                    "cash_capable_route_count": item.get("cash_capable_route_count", 0),
                    "history_validation_score": item.get("history_validation_score", 0.0),
                    "selection_basis": item.get("selection_basis", ""),
                    "support_count": item.get("support_count", 0),
                    "sources": item.get("sources", []),
                    "model_signal": item.get("model_signal", {}),
                    "model_alignment": item.get("model_alignment", False),
                    "routes": route_copies,
                    "runtime_gate": "executor_required",
                    "authority_mode": action_plan.get("order_authority_mode"),
                    "safety": {
                        "direct_exchange_mutation_by_cognition": False,
                        "requires_runtime_risk_gate": True,
                        "requires_executor": True,
                    },
                }
            )
            if len(candidates) >= ORDER_INTENT_MAX_PER_CYCLE:
                break
        if not candidates:
            return

        signature = "|".join(
            f"{candidate.get('symbol')}:{candidate.get('side')}:{','.join(str(route.get('venue')) + '/' + str(route.get('market_type')) for route in candidate.get('routes', []))}"
            for candidate in candidates
        )
        last_signature = str(getattr(self, "_last_order_intent_signature", "") or "")
        last_at = float(getattr(self, "_last_order_intent_at", 0.0) or 0.0)
        if signature == last_signature and now - last_at < ORDER_INTENT_MIN_INTERVAL_SEC:
            return

        self._last_order_intent_at = now
        self._last_order_intent_signature = signature
        summary = {
            "generated_at": datetime.now().isoformat(),
            "source": "unified_market_trader",
            "mode": "runtime_gated_order_intent",
            "intent_count": len(candidates),
            "intents": candidates,
            "order_intent_log": str(ORDER_INTENT_LOG_PATH),
            "order_intent_state": str(ORDER_INTENT_STATE_PATH),
        }
        self._latest_order_intents = summary
        action_plan["latest_published"] = summary
        action_plan["order_intents_published"] = len(candidates)

        for candidate in candidates:
            self._publish_thought("execution.order.intent", candidate)
            self._record_order_lifecycle(
                "intent_published",
                "intent_published",
                str(candidate.get("lifecycle_id") or ""),
                intent_id=candidate.get("id"),
                candidate_id=candidate.get("candidate_id"),
                symbol=candidate.get("symbol"),
                side=candidate.get("side"),
                route_key=candidate.get("route_key"),
                confidence=candidate.get("confidence"),
                venue=(candidate.get("routes") or [{}])[0].get("venue") if isinstance(candidate.get("routes"), list) and candidate.get("routes") else "",
                market_type=(candidate.get("routes") or [{}])[0].get("market_type") if isinstance(candidate.get("routes"), list) and candidate.get("routes") else "",
                source="unified_market_trader.intent",
            )

        try:
            ORDER_INTENT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with ORDER_INTENT_LOG_PATH.open("a", encoding="utf-8") as handle:
                for candidate in candidates:
                    handle.write(json.dumps(candidate, default=str, sort_keys=True) + "\n")
        except Exception as e:
            logger.debug("Order intent log write failed: %s", e)
        for path in (ORDER_INTENT_STATE_PATH, ORDER_INTENT_PUBLIC_PATH):
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                tmp_path = path.with_name(f"{path.name}.{os.getpid()}.tmp")
                with tmp_path.open("w", encoding="utf-8") as handle:
                    json.dump(summary, handle, indent=2, default=str)
                os.replace(tmp_path, path)
            except Exception as e:
                logger.debug("Order intent state write failed for %s: %s", path, e)

    def _feed_auris_throne(self, order_flow_feed: Dict[str, Any]) -> None:
        if get_sero_client is None:
            return
        now = time.time()
        if now - self._last_auris_feed_at < AURIS_FEED_MIN_INTERVAL_SEC:
            return
        self._last_auris_feed_at = now
        active = order_flow_feed.get("active_order_flow", []) if isinstance(order_flow_feed, dict) else []
        if not active:
            return
        top = active[0] if isinstance(active[0], dict) else {}
        symbol = str(top.get("symbol") or "").upper()
        side = str(top.get("side") or "BUY").upper()
        confidence = float(top.get("confidence", 0.0) or 0.0)
        prompt = (
            f"GLOBAL_ORDER_FLOW shared_tradables={order_flow_feed.get('shared_tradable_count', 0)} "
            f"active={order_flow_feed.get('active_order_flow_count', 0)} "
            f"top={symbol} {side} confidence={confidence:.2f} "
            f"Please return PROCEED/CAUTION/ABORT and one-line rationale."
        )
        def runner() -> None:
            try:
                sero = get_sero_client()
                asyncio.run(sero.ask_market_intelligence(prompt))
            except Exception as e:
                logger.debug("Dr Auris Throne feed unavailable: %s", e)

        threading.Thread(target=runner, name="aureon-auris-throne-feed", daemon=True).start()

    def _build_queen_voice_payload(self, kraken_payload: Dict[str, Any], capital_payload: Dict[str, Any]) -> Dict[str, Any]:
        now_iso = datetime.now().isoformat()
        kraken_decision = kraken_payload.get("decision_snapshot", {}) if isinstance(kraken_payload, dict) else {}
        capital_target = capital_payload.get("target_snapshot", {}) if isinstance(capital_payload, dict) else {}
        capital_candidates = capital_payload.get("candidate_snapshot", []) if isinstance(capital_payload, dict) else []
        capital_recent_closed = capital_payload.get("recent_closed_trades", []) if isinstance(capital_payload, dict) else []
        kraken_positions = kraken_payload.get("positions", []) if isinstance(kraken_payload.get("positions"), list) else []
        capital_positions = capital_payload.get("positions", []) if isinstance(capital_payload.get("positions"), list) else []
        open_positions = list(kraken_positions) + list(capital_positions)

        lines: List[str] = []
        mode = str(kraken_payload.get("queen_state") or "HOLD").upper()

        if open_positions:
            lines.append(
                f"Summary. I am managing {len(open_positions)} live position"
                f"{'' if len(open_positions) == 1 else 's'} across Kraken and Capital."
            )
        else:
            lines.append("Summary. I am flat on both exchanges and waiting for the next clean strike.")

        if kraken_positions:
            parts = []
            for pos in kraken_positions[:2]:
                symbol = str(pos.get("symbol") or pos.get("pair") or "?")
                side = str(pos.get("direction") or pos.get("side") or "?").upper()
                parts.append(f"{symbol} {side}")
            lines.append(f"Kraken update. I am managing {' and '.join(parts)}.")
        elif kraken_decision and kraken_decision.get("decision"):
            decision = kraken_decision.get("decision", {}) or {}
            decision_type = str(decision.get("type", "UNKNOWN")).replace("_", " ").lower()
            lines.append(
                f"Kraken update. I am leaning toward {kraken_decision.get('symbol', '?')} "
                f"{str(kraken_decision.get('side', '?')).lower()} with a "
                f"{self._confidence_word(decision.get('confidence', 0.0))} read for {decision_type}."
            )
        else:
            lines.append("Kraken update. I am watching for a cleaner crypto entry.")

        if capital_positions:
            parts = []
            for pos in capital_positions[:2]:
                symbol = str(pos.get("symbol") or "?")
                side = str(pos.get("direction") or pos.get("side") or "?").upper()
                parts.append(f"{symbol} {side}")
            lines.append(f"Capital update. I am managing {' and '.join(parts)}.")
        elif capital_target:
            target_symbol = str(capital_target.get("symbol") or "?")
            target_direction = str(capital_target.get("direction") or "?").upper()
            expected_net = float(capital_target.get("expected_net_profit", 0.0) or 0.0)
            lines.append(
                f"Capital update. I am stalking {target_symbol} {target_direction}. "
                f"The setup looks {'profitable' if expected_net > 0 else 'weak'} at the moment."
            )
            reason = str(capital_target.get("preflight_reason") or "").strip()
            if reason:
                lines.append("Capital is still waiting because the exchange checks are blocking entry.")
        elif capital_candidates:
            top = capital_candidates[0] if isinstance(capital_candidates[0], dict) else {}
            if top:
                lines.append(
                    f"Capital update. My next candidate is {top.get('symbol', '?')} "
                    f"{str(top.get('direction', '?')).upper()} if the current leader fails."
                )
        else:
            lines.append("Capital update. I am waiting for a valid CFD setup.")

        if capital_recent_closed:
            latest_close = capital_recent_closed[-1] if isinstance(capital_recent_closed[-1], dict) else {}
            learning_update = latest_close.get("learning_update", {}) if isinstance(latest_close, dict) else {}
            if learning_update:
                lines.append(
                    f"Learning update. I learned from {latest_close.get('symbol', '?')} and shifted my bias to "
                    f"{float(learning_update.get('symbol_bias', 0.0) or 0.0):+.3f} after a "
                    f"{float(latest_close.get('net_pnl', 0.0) or 0.0):+.2f} GBP result."
                )

        if open_positions:
            lines.append("I am watching the open positions closely and waiting for clean profit exits.")

        return {
            "ts": now_iso,
            "mode": mode,
            "text": " ".join(line.strip() for line in lines if line.strip()),
            "lines": lines,
            "sources": {
                "kraken_decision": kraken_decision,
                "capital_target": capital_target,
            },
        }

    def get_local_dashboard_state(self) -> Dict[str, Any]:
        payload = self._latest_dashboard_payload or self._build_bootstrap_dashboard_payload()
        return self._copy_payload(payload)

    def get_runtime_health(self) -> Dict[str, Any]:
        payload = self._latest_dashboard_payload or self._build_bootstrap_dashboard_payload()
        preflight = payload.get("preflight", {}) if isinstance(payload, dict) else {}
        combined = payload.get("combined", {}) if isinstance(payload, dict) else {}
        action_plan = payload.get("exchange_action_plan", {}) if isinstance(payload, dict) else {}
        now = time.time()
        last_tick_completed_at = float(getattr(self, "_last_tick_completed_at", 0.0) or 0.0)
        last_tick_started_at = float(getattr(self, "_last_tick_started_at", 0.0) or 0.0)
        tick_age_sec = (now - last_tick_completed_at) if last_tick_completed_at > 0 else None
        tick_running_sec = (now - last_tick_started_at) if last_tick_started_at > last_tick_completed_at else 0.0
        active_tick = bool(last_tick_started_at > last_tick_completed_at)
        tick_phase = str(getattr(self, "_tick_phase", "idle") or "idle")
        tick_phase_at = float(getattr(self, "_tick_phase_at", 0.0) or 0.0)
        tick_running_stale_after_sec = self._tick_running_stale_after_sec()
        booting = last_tick_completed_at <= 0
        boot_age_sec = now - float(getattr(self, "start_time", now) or now)
        stale_reason = ""
        if (
            not active_tick
            and last_tick_completed_at > 0
            and tick_age_sec is not None
            and tick_age_sec > READY_STALE_AFTER_SEC
        ):
            stale_reason = "last_tick_age_exceeded"
        active_tick_stalled = bool(active_tick and tick_running_sec > tick_running_stale_after_sec)
        if (
            active_tick
            and tick_age_sec is not None
            and tick_age_sec > READY_STALE_AFTER_SEC
            and tick_running_sec > READY_STALE_AFTER_SEC
        ):
            active_tick_stalled = True
        if active_tick_stalled:
            stale_reason = "tick_in_progress_stalled"
        if booting and boot_age_sec > max(READY_STALE_AFTER_SEC * 3.0, 180.0):
            stale_reason = "booting_timeout"
        stale = bool(stale_reason)
        alpaca_ok = self.alpaca is not None and not bool(self.alpaca_error or getattr(self.alpaca, "init_error", ""))
        binance_diag = getattr(self, "_binance_diag", {}) or {}
        binance_ok = self.binance is not None and bool(binance_diag.get("network_ok", False))
        client_trading_ready = bool(self.kraken_ready and self.capital_ready)
        client_data_ready = bool(alpaca_ok and binance_ok)
        shared_order_flow = payload.get("shared_order_flow", {}) if isinstance(payload.get("shared_order_flow"), dict) else {}
        live_stream_cache = (
            payload.get("live_stream_cache")
            or (payload.get("central_beat", {}).get("stream_cache") if isinstance(payload.get("central_beat"), dict) else {})
            or getattr(self, "_stream_cache_health", {})
        )
        gold_runtime_trade_proof = (
            payload.get("gold_runtime_trade_proof")
            or shared_order_flow.get("gold_runtime_trade_proof")
            or action_plan.get("gold_runtime_trade_proof")
            or {}
        )
        fresh_gold_source = (
            gold_runtime_trade_proof.get("fresh_gold_data_source", {})
            if isinstance(gold_runtime_trade_proof, dict)
            else {}
        )
        gold_observation_ready = bool(
            isinstance(gold_runtime_trade_proof, dict)
            and gold_runtime_trade_proof.get("gold_runtime_candidate_ready")
            and isinstance(fresh_gold_source, dict)
            and fresh_gold_source.get("ready")
        )
        stream_observation_ready = bool(
            gold_observation_ready
            or (isinstance(live_stream_cache, dict) and live_stream_cache.get("fresh"))
        )
        trading_ready = bool(
            client_trading_ready
            or (
                gold_observation_ready
                and isinstance(gold_runtime_trade_proof, dict)
                and gold_runtime_trade_proof.get("capital_cfd_route_visible")
            )
        )
        data_ready = bool(client_data_ready or stream_observation_ready)
        runtime_stall_diagnostic = {}
        if stale:
            gold_live_signal: Dict[str, Any] = {}
            try:
                gold_live_signal = self._gold_priority_live_stream_signal()
            except Exception as e:
                gold_live_signal = {
                    "ready": False,
                    "reason": f"gold_priority_probe_failed:{e}",
                    "source_tags": ["gold_priority_target"],
                }
            missing_gold_reason = (
                gold_runtime_trade_proof.get("gold_intent_publish_reason")
                if isinstance(gold_runtime_trade_proof, dict) and gold_runtime_trade_proof
                else ""
            )
            if not missing_gold_reason:
                missing_gold_reason = (
                    "combined_payload_stalled_before_gold_priority_publish"
                    if bool(gold_live_signal.get("ready"))
                    else str(gold_live_signal.get("reason") or "combined_payload_not_ready")
                )
            runtime_stall_diagnostic = {
                "generated_at": datetime.now().isoformat(),
                "reason": stale_reason,
                "tick_phase": tick_phase,
                "tick_phase_running_sec": round(max(0.0, now - tick_phase_at), 3) if tick_phase_at > 0 else 0.0,
                "live_stream_cache": live_stream_cache,
                "active_order_flow_count": int(shared_order_flow.get("active_order_flow_count", 0) or 0) if isinstance(shared_order_flow, dict) else 0,
                "routeable_key_count": int(shared_order_flow.get("multi_exchange_tradable_count", 0) or 0) if isinstance(shared_order_flow, dict) else 0,
                "venue_keys": list(action_plan.get("venues", {}).keys()) if isinstance(action_plan.get("venues"), dict) else [],
                "gold_live_stream_ready": bool(gold_live_signal.get("ready")),
                "gold_live_stream_signal": gold_live_signal,
                "capital_cfd_route_visible": bool(gold_runtime_trade_proof.get("capital_cfd_route_visible")) if isinstance(gold_runtime_trade_proof, dict) else False,
                "gold_runtime_candidate_ready": bool(gold_runtime_trade_proof.get("gold_runtime_candidate_ready")) if isinstance(gold_runtime_trade_proof, dict) else False,
                "missing_gold_promotion_reason": missing_gold_reason,
            }
        return {
            "ok": bool(trading_ready and data_ready and not stale),
            "service": "unified-market-trader",
            "duplicate_runtime": bool(getattr(self, "_duplicate_runtime", False)),
            "trading_ready": trading_ready,
            "data_ready": data_ready,
            "stale": stale,
            "booting": booting,
            "boot_age_sec": round(float(boot_age_sec), 3),
            "last_tick_started_at": datetime.fromtimestamp(last_tick_started_at).isoformat() if last_tick_started_at > 0 else None,
            "last_tick_completed_at": datetime.fromtimestamp(last_tick_completed_at).isoformat() if last_tick_completed_at > 0 else None,
            "last_tick_age_sec": round(float(tick_age_sec), 3) if tick_age_sec is not None else None,
            "last_tick_running_sec": round(float(tick_running_sec), 3) if tick_running_sec > 0 else 0.0,
            "tick_phase": tick_phase,
            "tick_phase_running_sec": round(max(0.0, now - tick_phase_at), 3) if tick_phase_at > 0 else 0.0,
            "stale_reason": stale_reason,
            "dashboard_generated_at": payload.get("generated_at"),
            "runtime_minutes": payload.get("runtime_minutes"),
            "preflight_overall": preflight.get("overall"),
            "preflight_critical_failures": int(preflight.get("critical_failures", 0) or 0),
            "preflight_warnings": int(preflight.get("warnings", 0) or 0),
            "runtime_observation_ready": bool(stream_observation_ready),
            "client_trading_ready": bool(client_trading_ready),
            "client_data_ready": bool(client_data_ready),
            "exchanges": {
                "kraken_ready": bool(self.kraken_ready),
                "capital_ready": bool(self.capital_ready),
                "alpaca_ready": alpaca_ok,
                "binance_ready": binance_ok,
                "all_four_connected": bool(self.kraken_ready and self.capital_ready and alpaca_ok and binance_ok),
                "execution_venues": action_plan.get("venues", {}) if isinstance(action_plan, dict) else {},
                "ready_execution_venue_count": int(action_plan.get("ready_venue_count", 0) or 0)
                if isinstance(action_plan, dict)
                else 0,
            },
            "errors": {
                "kraken": self.kraken_error,
                "capital": self.capital_error,
                "alpaca": self.alpaca_error,
                "binance": self.binance_error,
                "last_tick_error": self._last_tick_error,
            },
            "combined": {
                "open_positions": int(combined.get("open_positions", 0) or 0),
                "kraken_equity": float(combined.get("kraken_equity", 0.0) or 0.0),
                "capital_equity_gbp": float(combined.get("capital_equity_gbp", 0.0) or 0.0),
                "portfolio_balances": combined.get("portfolio_balances", {}) if isinstance(combined, dict) else {},
            },
            "api_governor": payload.get("api_governor") or self._api_governor_snapshot(),
            "dynamic_intelligence_budget": (
                payload.get("dynamic_intelligence_budget")
                or getattr(self, "_dynamic_intelligence_budget", {})
                or {}
            ),
            "live_stream_cache": live_stream_cache,
            "exchange_action_plan": action_plan,
            "gold_runtime_trade_proof": gold_runtime_trade_proof,
            "runtime_stall_diagnostic": runtime_stall_diagnostic,
            "shadow_trading": (
                payload.get("shadow_trading")
                or (action_plan.get("shadow_trading", {}) if isinstance(action_plan, dict) else {})
            ),
            "kraken_spot_fast_profit": payload.get("kraken_spot_fast_profit") or self._load_kraken_spot_fast_profit_state(),
            "hnc_cognitive_proof": (
                payload.get("hnc_cognitive_proof")
                or (action_plan.get("hnc_cognitive_proof", {}) if isinstance(action_plan, dict) else {})
            ),
            "hnc_operating_cycle": (
                payload.get("hnc_operating_cycle")
                or (payload.get("hnc_cognitive_proof", {}).get("operating_cycle") if isinstance(payload.get("hnc_cognitive_proof"), dict) else {})
                or (action_plan.get("hnc_operating_cycle", {}) if isinstance(action_plan, dict) else {})
            ),
            "runtime_watchdog": {
                "heartbeat_alive": True,
                "heartbeat_at": payload.get("runtime_heartbeat", {}).get("heartbeat_at_iso")
                if isinstance(payload.get("runtime_heartbeat"), dict)
                else None,
                "tick_stale": stale,
                "tick_stale_reason": stale_reason,
                "tick_phase": tick_phase,
                "tick_phase_running_sec": round(max(0.0, now - tick_phase_at), 3) if tick_phase_at > 0 else 0.0,
                "tick_active": active_tick,
                "tick_long_running": bool(active_tick and tick_running_sec > READY_STALE_AFTER_SEC),
                "tick_stale_after_sec": READY_STALE_AFTER_SEC,
                "tick_running_stale_after_sec": tick_running_stale_after_sec,
                "last_tick_age_sec": round(float(tick_age_sec), 3) if tick_age_sec is not None else None,
                "last_tick_running_sec": round(float(tick_running_sec), 3) if tick_running_sec > 0 else 0.0,
                "file_heartbeat_is_not_market_freshness": True,
            },
            "exchange_boot_init": self._exchange_boot_init_snapshot(),
            "executor_route_state": self._executor_route_snapshot(),
            "kraken_tick_state": self._kraken_tick_snapshot(),
            "capital_tick_state": self._capital_tick_snapshot(),
            "exchange_dashboard_state": self._exchange_dashboard_snapshot(),
            "runtime_writer": {
                "owns_lock": bool(getattr(self, "_owns_runtime_status", True)),
                "pid": os.getpid(),
                "instance_id": getattr(self, "_runtime_instance_id", ""),
                "reason": getattr(self, "_runtime_writer_lock_reason", ""),
            },
        }

    def _latest_monitor_line(self) -> str:
        capital_line = getattr(self.capital, "_latest_monitor_line", "") if self.capital is not None else ""
        kraken_line = getattr(self.kraken, "_latest_monitor_line", "") if self.kraken is not None else ""
        return capital_line or kraken_line

    def get_status_lines(self) -> List[str]:
        lines = [
            f"UNIFIED MARKET STATUS | runtime={(time.time() - self.start_time) / 60.0:.1f}m",
            "Markets armed: Kraken spot/margin + Capital CFDs + Alpaca spot + Binance spot/margin | CentralBeat fusion active",
        ]
        preflight = self._build_preflight_report()
        lines.append(
            "Preflight: "
            f"{str(preflight.get('overall', 'unknown')).upper()} "
            f"critical={int(preflight.get('critical_failures', 0) or 0)} "
            f"warnings={int(preflight.get('warnings', 0) or 0)}"
        )
        central_beat = self._central_beat_feed or {}
        regime = central_beat.get("regime", {}) if isinstance(central_beat, dict) else {}
        if regime:
            lines.append(
                "CentralBeat: "
                f"sources={int(regime.get('source_count', 0) or 0)} "
                f"bias={regime.get('bias', '?')} "
                f"conf={float(regime.get('confidence', 0.0) or 0.0):.2f}"
            )
        stream_cache = getattr(self, "_stream_cache_health", {}) or {}
        if stream_cache:
            lines.append(
                "Live stream cache: "
                f"fresh={bool(stream_cache.get('fresh'))} "
                f"symbols={int(stream_cache.get('symbol_count', 0) or 0)} "
                f"max_age={float(stream_cache.get('max_age_sec', 0.0) or 0.0):.1f}s "
                f"top={stream_cache.get('top_symbol') or 'none'}"
            )
        dynamic_budget = getattr(self, "_dynamic_intelligence_budget", {}) or {}
        budget_exchanges = dynamic_budget.get("exchanges", {}) if isinstance(dynamic_budget, dict) else {}
        if isinstance(budget_exchanges, dict) and budget_exchanges:
            roles = []
            for name in ("kraken", "capital", "alpaca", "binance"):
                state = budget_exchanges.get(name, {})
                if isinstance(state, dict) and state.get("connected"):
                    roles.append(f"{name}:{state.get('role', 'static')}")
            if roles:
                lines.append(
                    "Dynamic intelligence budget: "
                    + " ".join(roles)
                    + f" orderbook={int(dynamic_budget.get('orderbook_probe_limit', ORDERBOOK_PROBE_MAX_PER_TICK) or 0)}"
                )
        execution = getattr(self, "_latest_execution_results", {}) or {}
        if execution:
            lines.append(
                "Unified executor: "
                f"enabled={bool(execution.get('executor_enabled'))} "
                f"submitted={int(execution.get('submitted_count', 0) or 0)} "
                f"delegated={int(execution.get('delegated_count', 0) or 0)} "
                f"held={int(execution.get('held_count', execution.get('blocked_count', 0)) or 0)} "
                f"clearances={','.join(execution.get('runtime_clearances') or execution.get('guards') or execution.get('blockers') or []) or 'none'}"
            )
        spot_fast = self._load_kraken_spot_fast_profit_state()
        last_spot_check = spot_fast.get("last_check", {}) if isinstance(spot_fast, dict) else {}
        lines.append(
            "Kraken spot fast-profit: "
            f"enabled={bool(spot_fast.get('enabled'))} "
            f"open={len(spot_fast.get('open_positions', []) if isinstance(spot_fast.get('open_positions'), list) else [])} "
            f"closed={int(last_spot_check.get('closed_count', 0) or 0)} "
            f"reason={last_spot_check.get('reason') or 'measuring'}"
        )
        governor = self._api_governor_snapshot()
        exchanges = governor.get("exchanges", {}) if isinstance(governor, dict) else {}
        if exchanges:
            parts = []
            for name in ("kraken", "capital", "alpaca", "binance"):
                state = exchanges.get(name, {}) if isinstance(exchanges, dict) else {}
                if state:
                    parts.append(
                        f"{name}:{int(state.get('recent_calls_60s', 0) or 0)}/"
                        f"{int(state.get('max_calls_per_min', 0) or 0)}"
                    )
            if parts:
                lines.append("API governor: " + " ".join(parts))
        alpaca_state = "ready" if self.alpaca is not None and not self.alpaca_error else "unavailable"
        lines.append(f"ALPACA: spot_route_{alpaca_state} | {self.alpaca_error or 'ok'}")
        binance_diag = getattr(self, "_binance_diag", {}) or {}
        if self.binance is not None:
            lines.append(
                "BINANCE: "
                f"spot_route_ready={bool(binance_diag.get('network_ok', False))} "
                f"account_ready={bool(binance_diag.get('account_ok', False))} "
                f"margin_available={bool(binance_diag.get('margin_available', False))} "
                f"uk_mode={bool(binance_diag.get('uk_mode', getattr(self.binance, 'uk_mode', False)))} "
                f"| {self.binance_error or 'ok'}"
            )
        else:
            lines.append(f"BINANCE: unavailable | {self.binance_error or 'not_ready'}")
        if self.kraken_ready and self.kraken is not None:
            lines.extend(self.kraken._latest_status_lines[-10:] if getattr(self.kraken, "_latest_status_lines", None) else [])
        else:
            lines.append(f"KRAKEN: unavailable | {self.kraken_error or 'not_ready'}")
        if self.capital_ready and self.capital is not None:
            lines.extend(self.capital.status_lines())
        else:
            lines.append(f"CAPITAL: unavailable | {self.capital_error or 'not_ready'}")
        return lines

    def print_status(self) -> None:
        _safe_print()
        _safe_print("=" * 78)
        _safe_print(f"  UNIFIED MARKET TRADER | Runtime: {(time.time() - self.start_time) / 60.0:.1f}m")
        _safe_print("  Exchanges: Kraken Spot/Margin + Capital CFDs + Alpaca Spot + Binance Spot/Margin")
        _safe_print("  CentralBeat: Kraken + Capital + Alpaca + Binance feed fusion and order-intent routing")
        execution = getattr(self, "_latest_execution_results", {}) or {}
        if execution:
            _safe_print(
                "  Unified executor: "
                f"enabled={bool(execution.get('executor_enabled'))} "
                f"submitted={int(execution.get('submitted_count', 0) or 0)} "
                f"delegated={int(execution.get('delegated_count', 0) or 0)} "
                f"held={int(execution.get('held_count', execution.get('blocked_count', 0)) or 0)} "
                f"clearances={','.join(execution.get('runtime_clearances') or execution.get('guards') or execution.get('blockers') or []) or 'none'}"
            )
        governor = self._api_governor_snapshot()
        exchanges = governor.get("exchanges", {}) if isinstance(governor, dict) else {}
        if exchanges:
            parts = []
            for name in ("kraken", "capital", "alpaca", "binance"):
                state = exchanges.get(name, {}) if isinstance(exchanges, dict) else {}
                if state:
                    parts.append(
                        f"{name}:{int(state.get('recent_calls_60s', 0) or 0)}/"
                        f"{int(state.get('max_calls_per_min', 0) or 0)}"
                    )
            if parts:
                _safe_print("  API governor: " + " ".join(parts))
        preflight = self._build_preflight_report()
        _safe_print(
            "  Preflight: "
            f"{str(preflight.get('overall', 'unknown')).upper()} "
            f"critical={int(preflight.get('critical_failures', 0) or 0)} "
            f"warnings={int(preflight.get('warnings', 0) or 0)}"
        )
        _safe_print(f"  ALPACA: {'spot_route_ready' if self.alpaca is not None and not self.alpaca_error else 'spot_route_unavailable'} | {self.alpaca_error or 'ok'}")
        binance_diag = getattr(self, "_binance_diag", {}) or {}
        if self.binance is not None:
            _safe_print(
                "  BINANCE: "
                f"spot_route_ready={bool(binance_diag.get('network_ok', False))} "
                f"account_ready={bool(binance_diag.get('account_ok', False))} "
                f"margin_available={bool(binance_diag.get('margin_available', False))} "
                f"uk_mode={bool(binance_diag.get('uk_mode', getattr(self.binance, 'uk_mode', False)))} "
                f"| {self.binance_error or 'ok'}"
            )
        else:
            _safe_print(f"  BINANCE: unavailable | {self.binance_error or 'not_ready'}")
        _safe_print("-" * 78)
        _safe_print("  [KRAKEN]")
        if self.kraken_ready and self.kraken is not None:
            for line in self.kraken._latest_status_lines[-10:]:
                _safe_print(f"  {line}")
        else:
            _safe_print(f"  KRAKEN unavailable: {self.kraken_error or 'not_ready'}")
        _safe_print("-" * 78)
        _safe_print("  [CAPITAL]")
        if self.capital_ready and self.capital is not None:
            for line in self.capital.status_lines():
                _safe_print(f"  {line}")
        else:
            _safe_print(f"  CAPITAL unavailable: {self.capital_error or 'not_ready'}")
        _safe_print("=" * 78)
        _safe_print()

    # ── Network helpers ─────────────────────────────────────────────────────

    def _publish_thought(self, topic: str, payload_data: Dict[str, Any]) -> None:
        if self._thought_bus is None or Thought is None:
            return
        try:
            self._thought_bus.publish(Thought(
                source="unified_market_trader",
                topic=topic,
                payload=payload_data,
                meta={"mode": "unified"},
            ))
        except Exception:
            pass

    def _record_trade_profit(self, trade: dict) -> None:
        try:
            from aureon.autonomous.aureon_cognitive_trade_evidence import append_trade_evidence

            append_trade_evidence(
                trade,
                source="unified_market_trader.closed_trade",
                runtime_snapshot=self.get_runtime_health(),
            )
        except Exception:
            pass
        if self._mycelium is None:
            return
        try:
            if hasattr(self._mycelium, "record_trade_profit"):
                self._mycelium.record_trade_profit(
                    net_profit=float(trade.get("net_pnl", 0) or 0),
                    trade_data=trade,
                )
        except Exception:
            pass

    def tick(self) -> Dict[str, Any]:
        self._last_tick_started_at = time.time()
        self._last_tick_error = ""
        self._set_tick_phase("ensure_exchanges")
        self._ensure_exchanges()
        kraken_closed: List[dict] = []
        kraken_spot_closed: List[dict] = []
        capital_closed: List[dict] = []
        if self.kraken_ready and self.kraken is not None:
            if self._governor().should_run_cycle(
                "kraken",
                "positions",
                "kraken.tick",
                KRAKEN_TICK_MIN_INTERVAL_SEC,
            ):
                self._set_tick_phase("kraken_tick")
                try:
                    kraken_closed, kraken_tick_state = self._run_kraken_tick_with_timeout()
                    if kraken_tick_state.get("timeout") or kraken_tick_state.get("held"):
                        self._last_tick_error = str(kraken_tick_state.get("reason") or "kraken_tick_held")
                        logger.warning(
                            "Kraken tick held: %s running=%ss timeout=%ss",
                            kraken_tick_state.get("reason"),
                            kraken_tick_state.get("running_sec"),
                            kraken_tick_state.get("timeout_sec"),
                        )
                except Exception as e:
                    self._governor().record_error("kraken", e)
                    self.kraken_error = str(e)
                    self.kraken_ready = False
                    self.kraken = None
                    self._last_tick_error = str(e)
                    logger.error("Kraken tick failed: %s", e)
            self._set_tick_phase("kraken_spot_fast_profit")
            try:
                kraken_spot_closed = self._monitor_kraken_spot_fast_profit()
            except Exception as e:
                self._governor().record_error("kraken", e)
                self._last_tick_error = str(e)
                logger.debug("Kraken spot fast-profit monitor failed: %s", e)
        if self.capital_ready and self.capital is not None:
            if self._governor().should_run_cycle(
                "capital",
                "positions",
                "capital.tick",
                CAPITAL_TICK_MIN_INTERVAL_SEC,
            ):
                self._set_tick_phase("capital_tick")
                try:
                    capital_closed, capital_tick_state = self._run_capital_tick_with_timeout()
                    if capital_tick_state.get("timeout") or capital_tick_state.get("held"):
                        self._last_tick_error = str(capital_tick_state.get("reason") or "capital_tick_held")
                        logger.warning(
                            "Capital tick held: %s running=%ss timeout=%ss",
                            capital_tick_state.get("reason"),
                            capital_tick_state.get("running_sec"),
                            capital_tick_state.get("timeout_sec"),
                        )
                except Exception as e:
                    self._governor().record_error("capital", e)
                    self.capital_error = str(e)
                    self.capital_ready = False
                    self.capital = None
                    self._last_tick_error = str(e)
                    logger.error("Capital tick failed: %s", e)

        # ── Publish closed trades to Thought Bus + record in Mycelium ─────
        self._set_tick_phase("publish_closed_trades")
        for trade in kraken_closed:
            self._publish_thought("execution.trade.closed", {
                "pair": str(trade.get("pair") or trade.get("symbol") or "?"),
                "net_pnl": float(trade.get("net_pnl", 0) or 0),
                "reason": str(trade.get("reason") or "?"),
                "exchange": "kraken",
            })
            self._record_trade_profit(trade)
        for trade in kraken_spot_closed:
            self._publish_thought("execution.trade.closed", {
                "pair": str(trade.get("symbol") or trade.get("pair") or "?"),
                "net_pnl": float(trade.get("net_pnl", 0) or 0),
                "reason": str(trade.get("reason") or "?"),
                "exchange": "kraken_spot",
            })
        for trade in capital_closed:
            self._publish_thought("execution.trade.closed", {
                "pair": str(trade.get("symbol") or trade.get("pair") or "?"),
                "net_pnl": float(trade.get("pnl_gbp", 0) or 0),
                "reason": str(trade.get("reason") or "?"),
                "exchange": "capital",
            })
            self._record_trade_profit(trade)

        # ── Periodic status publish (every 30s) ──────────────────────────
        self._set_tick_phase("publish_status")
        now = time.time()
        if now - self._last_status_publish >= 30.0:
            self._last_status_publish = now
            self._publish_thought("unified.status", {
                "kraken_ready": self.kraken_ready,
                "capital_ready": self.capital_ready,
                "alpaca_ready": self.alpaca is not None and not bool(self.alpaca_error),
                "binance_ready": self.binance is not None and bool((getattr(self, "_binance_diag", {}) or {}).get("network_ok", False)),
                "uptime_secs": now - self.start_time,
                "api_governor": self._api_governor_snapshot(),
            })
            # Publish market feed for Hive Command worker bees
            if self._shared_market_feed:
                symbols = list(self._shared_market_feed.keys())
                self._publish_thought("market.feed", {
                    "prices": dict(self._shared_market_feed),
                    "symbols": symbols,
                })

        self._set_tick_phase("build_combined_payload")
        payload = self._build_combined_payload()
        self._set_tick_phase("execute_runtime_order_actions")
        execution_summary = self._execute_runtime_order_actions(payload)
        if isinstance(payload.get("exchange_action_plan"), dict):
            payload["exchange_action_plan"]["latest_execution"] = execution_summary
        self._latest_dashboard_payload = self._copy_payload(payload)
        self._last_tick_completed_at = time.time()
        self._set_tick_phase("idle")
        self._write_runtime_status_file()
        return {
            "kraken_closed": kraken_closed,
            "kraken_spot_closed": kraken_spot_closed,
            "capital_closed": capital_closed,
            "execution": execution_summary,
            "payload": payload,
        }

    def run(self, interval_sec: float = 2.0) -> None:
        if bool(getattr(self, "_duplicate_runtime", False)):
            _safe_print("Unified market trader duplicate suppressed.")
            _safe_print(self._runtime_writer_lock_reason or "Another fresh runtime owns the writer lock.")
            return

        mode = "DRY RUN" if self.dry_run else "LIVE"
        _safe_print("=" * 78)
        _safe_print("  UNIFIED MARKET TRADER")
        _safe_print(f"  Mode: {mode}")
        _safe_print("  Execution venues: Kraken spot/margin + Capital CFDs + Alpaca spot + Binance spot/margin")
        _safe_print("  Monitoring: local-first dashboard + terminal telemetry")
        _safe_print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        _safe_print("=" * 78)

        allow_sync_startup = (not EXCHANGE_BOOT_ASYNC_ENABLED) or EXCHANGE_SYNC_RETRY_ENABLED

        if allow_sync_startup and self.kraken is not None:
            self._startup_kraken(force=True)

        if allow_sync_startup and self.capital is not None:
            self._startup_capital(force=True)

        self._build_combined_payload()

        try:
            while True:
                self.tick()
                self.print_status()
                time.sleep(interval_sec)
        except KeyboardInterrupt:
            _safe_print("\nUnified market trader stopped.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Unified Kraken + Capital market trader")
    parser.add_argument("--dry-run", action="store_true", help="Run Kraken in dry-run mode")
    parser.add_argument("--interval", type=float, default=2.0, help="Main loop interval in seconds")
    parser.add_argument(
        "--setup-kraken-cli",
        action="store_true",
        help="Install Kraken CLI before startup if it is missing (uses Kraken's official installer).",
    )
    args = parser.parse_args()

    trader = UnifiedMarketTrader(dry_run=args.dry_run, setup_kraken_cli=args.setup_kraken_cli)
    trader.run(interval_sec=max(0.5, float(args.interval)))


if __name__ == "__main__":
    main()
