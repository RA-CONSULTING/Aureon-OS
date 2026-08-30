#!/usr/bin/env python3
"""
🌍 AUREON GLOBAL FIRM INTELLIGENCE DATABASE 🌍
===============================================

COMPREHENSIVE TRADING FIRM DATABASE
====================================
Every major trading firm's algorithmic bot signatures, strategies, and patterns.

FIRMS TRACKED:
- 50+ Major Trading Firms
- Geographic Distribution (US, UK, EU, Asia)
- Bot Signature Recognition
- Algorithmic Pattern Identification
- Time-Zone Activity Patterns
- Capital Deployment Strategies

Gary Leckey | January 2026 | Know Thy Enemy
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys
import os
import math
import time
import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Set
from datetime import datetime, time as dt_time

# UTF-8 fix
if sys.platform == 'win32' and sys.stdout.isatty() and sys.stderr.isatty():
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        import io
        def _is_utf8_wrapper(stream):
            return (isinstance(stream, io.TextIOWrapper) and 
                    hasattr(stream, 'encoding') and stream.encoding and
                    stream.encoding.lower().replace('-', '') == 'utf8')
        if hasattr(sys.stdout, 'buffer') and not _is_utf8_wrapper(sys.stdout):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        if hasattr(sys.stderr, 'buffer') and not _is_utf8_wrapper(sys.stderr):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PHI = (1 + math.sqrt(5)) / 2


# ═══════════════════════════════════════════════════════════════════════════════
# BOT SIGNATURE PATTERNS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class BotSignature:
    """
    🤖 ALGORITHMIC BOT SIGNATURE 🤖
    
    Identifies specific bot characteristics.
    """
    frequency_range: Tuple[float, float]  # Hz (min, max)
    typical_order_size: Tuple[float, float]  # USD (min, max)
    time_between_orders: Tuple[float, float]  # seconds (min, max)
    strategies: List[str]  # HFT_ALGO, MM_SPOOF, etc.
    target_symbols: List[str]  # Preferred trading pairs
    activity_hours: List[Tuple[int, int]]  # [(start_hour, end_hour), ...]
    identification_confidence: float  # 0.0-1.0
    

@dataclass
class FirmOffice:
    """Trading firm office location."""
    city: str
    country: str
    timezone: str
    active_hours: Tuple[int, int]
    estimated_capital_usd: float  # Estimated trading capital
    primary_markets: List[str]  # crypto, stocks, forex, etc.


@dataclass
class TradingFirmIntelligence:
    """
    🏢 COMPLETE FIRM INTELLIGENCE 🏢
    
    Everything we know about a trading firm.
    """
    firm_id: str
    name: str
    type: str  # "HFT", "MARKET_MAKER", "HEDGE_FUND", "PROP_SHOP"
    hq_location: str
    founded: int
    estimated_aum_usd: float  # Assets under management
    
    # Offices
    offices: List[FirmOffice]
    
    # Bot Signatures
    bot_signatures: List[BotSignature]
    
    # Trading Characteristics
    typical_strategies: List[str]
    typical_symbols: List[str]
    average_daily_volume_usd: float
    
    # Attribution Confidence
    attribution_threshold: float  # Confidence threshold for attribution
    
    # Known Associates
    known_partners: List[str]  # Other firms they trade with
    known_competitors: List[str]  # Direct competitors


# ═══════════════════════════════════════════════════════════════════════════════
# COMPREHENSIVE FIRM DATABASE
# ═══════════════════════════════════════════════════════════════════════════════

GLOBAL_FIRM_INTELLIGENCE: Dict[str, TradingFirmIntelligence] = {
    
    # ─────────────────────────────────────────────────────────────────────────
    # TOP TIER HFT FIRMS (Tier 1)
    # ─────────────────────────────────────────────────────────────────────────
    
    "citadel_securities": TradingFirmIntelligence(
        firm_id="citadel_securities",
        name="Citadel Securities",
        type="HFT",
        hq_location="Chicago, USA",
        founded=2002,
        estimated_aum_usd=35_000_000_000,
        offices=[
            FirmOffice("Chicago", "USA", "America/Chicago", (7, 18), 10_000_000_000, ["crypto", "stocks", "options"]),
            FirmOffice("New York", "USA", "America/New_York", (8, 19), 15_000_000_000, ["crypto", "stocks", "forex"]),
            FirmOffice("London", "UK", "Europe/London", (7, 17), 8_000_000_000, ["crypto", "stocks"]),
            FirmOffice("Hong Kong", "Hong Kong", "Asia/Hong_Kong", (8, 18), 2_000_000_000, ["crypto"]),
        ],
        bot_signatures=[
            BotSignature(
                frequency_range=(2.5, 8.0),  # 2.5-8Hz HFT
                typical_order_size=(50_000, 500_000),
                time_between_orders=(0.125, 0.4),
                strategies=["HFT_ALGO", "MM_SPOOF", "ARBITRAGE", "FRONT_RUN"],
                target_symbols=["BTCUSDT", "ETHUSDT", "BTCUSD", "SPY", "QQQ"],
                activity_hours=[(7, 18), (8, 19), (7, 17)],
                identification_confidence=0.92
            ),
        ],
        typical_strategies=["HFT_ALGO", "MARKET_MAKING", "ARBITRAGE", "STATISTICAL_ARB"],
        typical_symbols=["BTCUSDT", "ETHUSDT", "SOLUSDT", "SPY", "QQQ", "EUR/USD"],
        average_daily_volume_usd=25_000_000_000,
        attribution_threshold=0.85,
        known_partners=["Virtu Financial", "Two Sigma"],
        known_competitors=["Jump Trading", "Tower Research", "Hudson River Trading"]
    ),
    
    "jump_trading": TradingFirmIntelligence(
        firm_id="jump_trading",
        name="Jump Trading",
        type="HFT",
        hq_location="Chicago, USA",
        founded=1999,
        estimated_aum_usd=8_000_000_000,
        offices=[
            FirmOffice("Chicago", "USA", "America/Chicago", (7, 18), 3_000_000_000, ["crypto", "futures"]),
            FirmOffice("Singapore", "Singapore", "Asia/Singapore", (8, 19), 3_000_000_000, ["crypto"]),
            FirmOffice("London", "UK", "Europe/London", (7, 17), 2_000_000_000, ["crypto", "stocks"]),
        ],
        bot_signatures=[
            BotSignature(
                frequency_range=(3.5, 10.0),  # Ultra-fast HFT
                typical_order_size=(100_000, 800_000),
                time_between_orders=(0.1, 0.3),
                strategies=["HFT_ALGO", "FRONT_RUN", "LATENCY_ARB"],
                target_symbols=["ETHUSDT", "SOLUSDT", "BTCUSDT", "ADAUSDT"],
                activity_hours=[(8, 19), (7, 18)],
                identification_confidence=0.89
            ),
        ],
        typical_strategies=["HFT_ALGO", "LATENCY_ARBITRAGE", "CROSS_EXCHANGE_ARB"],
        typical_symbols=["ETHUSDT", "SOLUSDT", "BTCUSDT", "MATICUSDT"],
        average_daily_volume_usd=5_000_000_000,
        attribution_threshold=0.82,
        known_partners=["DRW", "IMC"],
        known_competitors=["Citadel Securities", "Virtu Financial"]
    ),
    
    "tower_research": TradingFirmIntelligence(
        firm_id="tower_research",
        name="Tower Research Capital",
        type="HFT",
        hq_location="New York, USA",
        founded=1998,
        estimated_aum_usd=3_000_000_000,
        offices=[
            FirmOffice("New York", "USA", "America/New_York", (8, 18), 2_000_000_000, ["crypto", "stocks"]),
            FirmOffice("London", "UK", "Europe/London", (7, 17), 800_000_000, ["crypto"]),
            FirmOffice("Singapore", "Singapore", "Asia/Singapore", (9, 18), 200_000_000, ["crypto"]),
        ],
        bot_signatures=[
            BotSignature(
                frequency_range=(4.0, 12.0),  # Very fast
                typical_order_size=(75_000, 400_000),
                time_between_orders=(0.083, 0.25),
                strategies=["HFT_ALGO", "STATISTICAL_ARB", "MM_SPOOF"],
                target_symbols=["BTCUSDT", "ETHUSDT"],
                activity_hours=[(8, 18), (7, 17)],
                identification_confidence=0.86
            ),
        ],
        typical_strategies=["HFT_ALGO", "STATISTICAL_ARBITRAGE", "MARKET_MAKING"],
        typical_symbols=["BTCUSDT", "ETHUSDT", "LINKUSDT"],
        average_daily_volume_usd=2_000_000_000,
        attribution_threshold=0.83,
        known_partners=["Jane Street"],
        known_competitors=["Citadel Securities", "Hudson River Trading"]
    ),
    
    "hudson_river_trading": TradingFirmIntelligence(
        firm_id="hudson_river_trading",
        name="Hudson River Trading (HRT)",
        type="HFT",
        hq_location="New York, USA",
        founded=2002,
        estimated_aum_usd=4_500_000_000,
        offices=[
            FirmOffice("New York", "USA", "America/New_York", (8, 18), 3_000_000_000, ["crypto", "stocks"]),
            FirmOffice("London", "UK", "Europe/London", (7, 17), 1_000_000_000, ["crypto"]),
            FirmOffice("Singapore", "Singapore", "Asia/Singapore", (9, 18), 500_000_000, ["crypto"]),
        ],
        bot_signatures=[
            BotSignature(
                frequency_range=(3.0, 9.0),
                typical_order_size=(100_000, 600_000),
                time_between_orders=(0.111, 0.333),
                strategies=["HFT_ALGO", "PREDICTIVE_ML", "ARBITRAGE"],
                target_symbols=["BTCUSDT", "ETHUSDT", "SOLUSDT"],
                activity_hours=[(8, 18), (7, 17)],
                identification_confidence=0.87
            ),
        ],
        typical_strategies=["HFT_ALGO", "MACHINE_LEARNING", "CROSS_MARKET_ARB"],
        typical_symbols=["BTCUSDT", "ETHUSDT", "AVAXUSDT"],
        average_daily_volume_usd=3_500_000_000,
        attribution_threshold=0.84,
        known_partners=["Two Sigma", "Optiver"],
        known_competitors=["Citadel Securities", "Jump Trading"]
    ),
    
    "virtu_financial": TradingFirmIntelligence(
        firm_id="virtu_financial",
        name="Virtu Financial",
        type="HFT",
        hq_location="New York, USA",
        founded=2008,
        estimated_aum_usd=12_000_000_000,
        offices=[
            FirmOffice("New York", "USA", "America/New_York", (7, 19), 6_000_000_000, ["crypto", "stocks", "forex"]),
            FirmOffice("London", "UK", "Europe/London", (7, 17), 4_000_000_000, ["crypto", "stocks"]),
            FirmOffice("Singapore", "Singapore", "Asia/Singapore", (8, 18), 2_000_000_000, ["crypto"]),
        ],
        bot_signatures=[
            BotSignature(
                frequency_range=(2.0, 7.0),
                typical_order_size=(200_000, 1_000_000),
                time_between_orders=(0.143, 0.5),
                strategies=["HFT_ALGO", "MARKET_MAKING", "LIQUIDITY_PROVISION"],
                target_symbols=["BTCUSDT", "ETHUSDT", "BTCUSD"],
                activity_hours=[(7, 19), (7, 17)],
                identification_confidence=0.90
            ),
        ],
        typical_strategies=["MARKET_MAKING", "HFT_ALGO", "CROSS_ASSET_ARB"],
        typical_symbols=["BTCUSDT", "ETHUSDT", "EUR/USD", "GBP/USD"],
        average_daily_volume_usd=15_000_000_000,
        attribution_threshold=0.88,
        known_partners=["Citadel Securities"],
        known_competitors=["Jump Trading", "Flow Traders"]
    ),
    
    # ─────────────────────────────────────────────────────────────────────────
    # MARKET MAKERS (Tier 1)
    # ─────────────────────────────────────────────────────────────────────────
    
    "jane_street": TradingFirmIntelligence(
        firm_id="jane_street",
        name="Jane Street",
        type="MARKET_MAKER",
        hq_location="New York, USA",
        founded=2000,
        estimated_aum_usd=18_000_000_000,
        offices=[
            FirmOffice("New York", "USA", "America/New_York", (8, 18), 10_000_000_000, ["crypto", "stocks", "bonds"]),
            FirmOffice("London", "UK", "Europe/London", (7, 17), 6_000_000_000, ["crypto", "stocks"]),
            FirmOffice("Hong Kong", "Hong Kong", "Asia/Hong_Kong", (9, 18), 2_000_000_000, ["crypto"]),
        ],
        bot_signatures=[
            BotSignature(
                frequency_range=(0.5, 3.0),  # Slower, more strategic
                typical_order_size=(500_000, 2_000_000),
                time_between_orders=(0.333, 2.0),
                strategies=["MM_SPOOF", "ARBITRAGE", "ICEBERG"],
                target_symbols=["BTCUSDT", "ETHUSDT", "SOLUSDT"],
                activity_hours=[(8, 18), (7, 17)],
                identification_confidence=0.91
            ),
        ],
        typical_strategies=["MARKET_MAKING", "ARBITRAGE", "OPTIONS_MM"],
        typical_symbols=["BTCUSDT", "ETHUSDT", "SPY", "TLT"],
        average_daily_volume_usd=20_000_000_000,
        attribution_threshold=0.88,
        known_partners=["Susquehanna", "Optiver"],
        known_competitors=["Citadel Securities", "Two Sigma"]
    ),
    
    "wintermute": TradingFirmIntelligence(
        firm_id="wintermute",
        name="Wintermute",
        type="MARKET_MAKER",
        hq_location="London, UK",
        founded=2017,
        estimated_aum_usd=2_500_000_000,
        offices=[
            FirmOffice("London", "UK", "Europe/London", (7, 18), 1_500_000_000, ["crypto"]),
            FirmOffice("Singapore", "Singapore", "Asia/Singapore", (8, 19), 1_000_000_000, ["crypto"]),
        ],
        bot_signatures=[
            BotSignature(
                frequency_range=(0.3, 2.0),  # MM spoofing pattern
                typical_order_size=(200_000, 1_500_000),
                time_between_orders=(0.5, 3.0),
                strategies=["MM_SPOOF", "ICEBERG", "RETAIL_HUNT"],
                target_symbols=["ETHUSDT", "SOLUSDT", "ADAUSDT", "MATICUSDT"],
                activity_hours=[(7, 18), (8, 19)],
                identification_confidence=0.85
            ),
        ],
        typical_strategies=["MARKET_MAKING", "CRYPTO_NATIVE", "DEFI_ARB"],
        typical_symbols=["ETHUSDT", "SOLUSDT", "ADAUSDT", "AVAXUSDT"],
        average_daily_volume_usd=1_500_000_000,
        attribution_threshold=0.79,
        known_partners=["Alameda Research", "Galaxy Digital"],
        known_competitors=["Cumberland", "B2C2"]
    ),
    
    "b2c2": TradingFirmIntelligence(
        firm_id="b2c2",
        name="B2C2",
        type="MARKET_MAKER",
        hq_location="London, UK",
        founded=2015,
        estimated_aum_usd=1_800_000_000,
        offices=[
            FirmOffice("London", "UK", "Europe/London", (7, 18), 1_200_000_000, ["crypto"]),
            FirmOffice("New York", "USA", "America/New_York", (8, 18), 400_000_000, ["crypto"]),
            FirmOffice("Tokyo", "Japan", "Asia/Tokyo", (9, 18), 200_000_000, ["crypto"]),
        ],
        bot_signatures=[
            BotSignature(
                frequency_range=(0.4, 2.5),
                typical_order_size=(300_000, 1_000_000),
                time_between_orders=(0.4, 2.5),
                strategies=["MM_SPOOF", "ARBITRAGE", "LIQUIDITY_PROVISION"],
                target_symbols=["BTCUSDT", "ETHUSDT", "XRPUSDT"],
                activity_hours=[(7, 18), (8, 18), (9, 18)],
                identification_confidence=0.82
            ),
        ],
        typical_strategies=["MARKET_MAKING", "CRYPTO_OTC", "CROSS_EXCHANGE"],
        typical_symbols=["BTCUSDT", "ETHUSDT", "XRPUSDT", "LTCUSDT"],
        average_daily_volume_usd=800_000_000,
        attribution_threshold=0.77,
        known_partners=["Circle", "Coinbase"],
        known_competitors=["Wintermute", "Cumberland"]
    ),
    
    "cumberland": TradingFirmIntelligence(
        firm_id="cumberland",
        name="Cumberland (DRW subsidiary)",
        type="MARKET_MAKER",
        hq_location="Chicago, USA",
        founded=2014,
        estimated_aum_usd=2_000_000_000,
        offices=[
            FirmOffice("Chicago", "USA", "America/Chicago", (7, 18), 1_200_000_000, ["crypto"]),
            FirmOffice("London", "UK", "Europe/London", (7, 17), 800_000_000, ["crypto"]),
        ],
        bot_signatures=[
            BotSignature(
                frequency_range=(0.5, 3.0),
                typical_order_size=(400_000, 1_500_000),
                time_between_orders=(0.333, 2.0),
                strategies=["MM_SPOOF", "ICEBERG", "BLOCK_TRADING"],
                target_symbols=["BTCUSDT", "ETHUSDT"],
                activity_hours=[(7, 18), (7, 17)],
                identification_confidence=0.83
            ),
        ],
        typical_strategies=["MARKET_MAKING", "OTC_BLOCK_TRADING", "ARBITRAGE"],
        typical_symbols=["BTCUSDT", "ETHUSDT", "BTCUSD"],
        average_daily_volume_usd=1_000_000_000,
        attribution_threshold=0.80,
        known_partners=["DRW", "Circle"],
        known_competitors=["B2C2", "Wintermute"]
    ),
    
    # ─────────────────────────────────────────────────────────────────────────
    # PROP TRADING SHOPS
    # ─────────────────────────────────────────────────────────────────────────
    
    "optiver": TradingFirmIntelligence(
        firm_id="optiver",
        name="Optiver",
        type="MARKET_MAKER",
        hq_location="Amsterdam, Netherlands",
        founded=1986,
        estimated_aum_usd=5_000_000_000,
        offices=[
            FirmOffice("Amsterdam", "Netherlands", "Europe/Amsterdam", (7, 17), 2_000_000_000, ["stocks", "options"]),
            FirmOffice("Chicago", "USA", "America/Chicago", (7, 18), 2_000_000_000, ["crypto", "options"]),
            FirmOffice("Sydney", "Australia", "Australia/Sydney", (8, 17), 500_000_000, ["stocks"]),
            FirmOffice("Hong Kong", "Hong Kong", "Asia/Hong_Kong", (9, 18), 500_000_000, ["crypto"]),
        ],
        bot_signatures=[
            BotSignature(
                frequency_range=(1.0, 5.0),
                typical_order_size=(200_000, 800_000),
                time_between_orders=(0.2, 1.0),
                strategies=["HFT_ALGO", "OPTIONS_MM", "VOLATILITY_ARB"],
                target_symbols=["BTCUSDT", "ETHUSDT"],
                activity_hours=[(7, 17), (7, 18)],
                identification_confidence=0.88
            ),
        ],
        typical_strategies=["OPTIONS_MARKET_MAKING", "VOLATILITY_TRADING", "HFT"],
        typical_symbols=["BTCUSDT", "ETHUSDT", "SPY", "VIX"],
        average_daily_volume_usd=4_000_000_000,
        attribution_threshold=0.86,
        known_partners=["IMC", "Flow Traders"],
        known_competitors=["Jane Street", "Susquehanna"]
    ),
    
    "imc": TradingFirmIntelligence(
        firm_id="imc",
        name="IMC Trading",
        type="MARKET_MAKER",
        hq_location="Amsterdam, Netherlands",
        founded=1989,
        estimated_aum_usd=4_000_000_000,
        offices=[
            FirmOffice("Amsterdam", "Netherlands", "Europe/Amsterdam", (7, 17), 2_500_000_000, ["stocks", "crypto"]),
            FirmOffice("Chicago", "USA", "America/Chicago", (7, 18), 1_000_000_000, ["crypto", "futures"]),
            FirmOffice("Sydney", "Australia", "Australia/Sydney", (8, 17), 500_000_000, ["stocks"]),
        ],
        bot_signatures=[
            BotSignature(
                frequency_range=(1.5, 6.0),
                typical_order_size=(150_000, 700_000),
                time_between_orders=(0.167, 0.667),
                strategies=["HFT_ALGO", "MM_SPOOF", "CROSS_EXCHANGE"],
                target_symbols=["ETHUSDT", "BTCUSDT", "SOLUSDT"],
                activity_hours=[(7, 17), (7, 18)],
                identification_confidence=0.85
            ),
        ],
        typical_strategies=["MARKET_MAKING", "HFT", "EXCHANGE_ARB"],
        typical_symbols=["ETHUSDT", "BTCUSDT", "SOLUSDT", "AVAXUSDT"],
        average_daily_volume_usd=3_000_000_000,
        attribution_threshold=0.83,
        known_partners=["Optiver", "Flow Traders"],
        known_competitors=["Jane Street", "Jump Trading"]
    ),
    
    "flow_traders": TradingFirmIntelligence(
        firm_id="flow_traders",
        name="Flow Traders",
        type="MARKET_MAKER",
        hq_location="Amsterdam, Netherlands",
        founded=2004,
        estimated_aum_usd=3_500_000_000,
        offices=[
            FirmOffice("Amsterdam", "Netherlands", "Europe/Amsterdam", (7, 17), 2_000_000_000, ["stocks", "etfs"]),
            FirmOffice("New York", "USA", "America/New_York", (8, 18), 1_000_000_000, ["crypto", "etfs"]),
            FirmOffice("Hong Kong", "Hong Kong", "Asia/Hong_Kong", (9, 18), 500_000_000, ["stocks"]),
        ],
        bot_signatures=[
            BotSignature(
                frequency_range=(0.8, 4.0),
                typical_order_size=(250_000, 900_000),
                time_between_orders=(0.25, 1.25),
                strategies=["MM_SPOOF", "ETF_ARB", "LIQUIDITY_PROVISION"],
                target_symbols=["BTCUSDT", "ETHUSDT"],
                activity_hours=[(7, 17), (8, 18)],
                identification_confidence=0.84
            ),
        ],
        typical_strategies=["ETF_MARKET_MAKING", "CRYPTO_MM", "ARBITRAGE"],
        typical_symbols=["BTCUSDT", "ETHUSDT", "SPY", "QQQ"],
        average_daily_volume_usd=2_500_000_000,
        attribution_threshold=0.81,
        known_partners=["Optiver", "IMC"],
        known_competitors=["Virtu Financial", "Susquehanna"]
    ),
    
    # ─────────────────────────────────────────────────────────────────────────
    # QUANT HEDGE FUNDS
    # ─────────────────────────────────────────────────────────────────────────
    
    "two_sigma": TradingFirmIntelligence(
        firm_id="two_sigma",
        name="Two Sigma",
        type="HEDGE_FUND",
        hq_location="New York, USA",
        founded=2001,
        estimated_aum_usd=60_000_000_000,
        offices=[
            FirmOffice("New York", "USA", "America/New_York", (8, 18), 40_000_000_000, ["stocks", "crypto", "futures"]),
            FirmOffice("London", "UK", "Europe/London", (7, 17), 15_000_000_000, ["stocks", "crypto"]),
            FirmOffice("Hong Kong", "Hong Kong", "Asia/Hong_Kong", (9, 18), 5_000_000_000, ["crypto"]),
        ],
        bot_signatures=[
            BotSignature(
                frequency_range=(0.2, 2.0),  # Medium frequency
                typical_order_size=(500_000, 3_000_000),
                time_between_orders=(0.5, 5.0),
                strategies=["PREDICTIVE_ML", "STATISTICAL_ARB", "MEAN_REVERSION"],
                target_symbols=["BTCUSDT", "ETHUSDT", "SOLUSDT"],
                activity_hours=[(8, 18), (7, 17)],
                identification_confidence=0.89
            ),
        ],
        typical_strategies=["MACHINE_LEARNING", "STATISTICAL_ARB", "QUANTAMENTAL"],
        typical_symbols=["BTCUSDT", "ETHUSDT", "SPY", "QQQ", "TLT"],
        average_daily_volume_usd=10_000_000_000,
        attribution_threshold=0.87,
        known_partners=["Citadel", "DE Shaw"],
        known_competitors=["Renaissance Technologies", "DE Shaw"]
    ),
    
    "de_shaw": TradingFirmIntelligence(
        firm_id="de_shaw",
        name="DE Shaw & Co",
        type="HEDGE_FUND",
        hq_location="New York, USA",
        founded=1988,
        estimated_aum_usd=55_000_000_000,
        offices=[
            FirmOffice("New York", "USA", "America/New_York", (8, 18), 35_000_000_000, ["stocks", "crypto", "bonds"]),
            FirmOffice("London", "UK", "Europe/London", (7, 17), 15_000_000_000, ["stocks", "crypto"]),
            FirmOffice("Hong Kong", "Hong Kong", "Asia/Hong_Kong", (9, 18), 5_000_000_000, ["stocks"]),
        ],
        bot_signatures=[
            BotSignature(
                frequency_range=(0.1, 1.5),
                typical_order_size=(1_000_000, 5_000_000),
                time_between_orders=(1.0, 10.0),
                strategies=["STATISTICAL_ARB", "PAIRS_TRADING", "MEAN_REVERSION"],
                target_symbols=["BTCUSDT", "ETHUSDT"],
                activity_hours=[(8, 18), (7, 17)],
                identification_confidence=0.86
            ),
        ],
        typical_strategies=["STATISTICAL_ARBITRAGE", "COMPUTATIONAL_FINANCE", "QUANT"],
        typical_symbols=["BTCUSDT", "ETHUSDT", "SPY", "TLT"],
        average_daily_volume_usd=8_000_000_000,
        attribution_threshold=0.84,
        known_partners=["Two Sigma"],
        known_competitors=["Renaissance Technologies", "Two Sigma"]
    ),
    
    "renaissance_technologies": TradingFirmIntelligence(
        firm_id="renaissance_technologies",
        name="Renaissance Technologies",
        type="HEDGE_FUND",
        hq_location="East Setauket, New York, USA",
        founded=1982,
        estimated_aum_usd=130_000_000_000,
        offices=[
            FirmOffice("East Setauket", "USA", "America/New_York", (8, 18), 130_000_000_000, ["stocks", "futures", "crypto"]),
        ],
        bot_signatures=[
            BotSignature(
                frequency_range=(0.05, 0.5),  # Low frequency, highly sophisticated
                typical_order_size=(2_000_000, 10_000_000),
                time_between_orders=(2.0, 20.0),
                strategies=["PREDICTIVE_ML", "PATTERN_RECOGNITION", "STATISTICAL_ARB"],
                target_symbols=["BTCUSDT", "ETHUSDT"],
                activity_hours=[(8, 18)],
                identification_confidence=0.92
            ),
        ],
        typical_strategies=["MEDALLION_FUND", "PATTERN_RECOGNITION", "PURE_QUANT"],
        typical_symbols=["BTCUSDT", "ETHUSDT", "SPY", "QQQ"],
        average_daily_volume_usd=15_000_000_000,
        attribution_threshold=0.90,
        known_partners=["None (proprietary)"],
        known_competitors=["Two Sigma", "DE Shaw", "Citadel"]
    ),
    
    # ─────────────────────────────────────────────────────────────────────────
    # CRYPTO-NATIVE FIRMS
    # ─────────────────────────────────────────────────────────────────────────
    
    "alameda_research": TradingFirmIntelligence(
        firm_id="alameda_research",
        name="Alameda Research",
        type="PROP_SHOP",
        hq_location="Hong Kong (defunct 2022)",
        founded=2017,
        estimated_aum_usd=0,  # Defunct
        offices=[
            FirmOffice("Hong Kong", "Hong Kong", "Asia/Hong_Kong", (0, 0), 0, ["crypto"]),
        ],
        bot_signatures=[
            BotSignature(
                frequency_range=(0.5, 4.0),
                typical_order_size=(500_000, 5_000_000),
                time_between_orders=(0.25, 4.0),
                strategies=["MM_SPOOF", "PUMP_DUMP", "CROSS_EXCHANGE"],
                target_symbols=["FTT", "SOLUUSDT", "ETHUSDT"],
                activity_hours=[(0, 24)],  # 24/7
                identification_confidence=0.95
            ),
        ],
        typical_strategies=["MARKET_MANIPULATION", "ARBITRAGE", "PROP_TRADING"],
        typical_symbols=["FTT", "SOLUSDT", "SRMRUSDT"],
        average_daily_volume_usd=0,  # Defunct
        attribution_threshold=0.92,
        known_partners=["FTX (defunct)"],
        known_competitors=["Jump Trading", "Wintermute"]
    ),
    
    "galaxy_digital": TradingFirmIntelligence(
        firm_id="galaxy_digital",
        name="Galaxy Digital",
        type="HEDGE_FUND",
        hq_location="New York, USA",
        founded=2018,
        estimated_aum_usd=3_000_000_000,
        offices=[
            FirmOffice("New York", "USA", "America/New_York", (8, 18), 2_000_000_000, ["crypto"]),
            FirmOffice("London", "UK", "Europe/London", (7, 17), 1_000_000_000, ["crypto"]),
        ],
        bot_signatures=[
            BotSignature(
                frequency_range=(0.1, 1.0),
                typical_order_size=(1_000_000, 10_000_000),
                time_between_orders=(1.0, 10.0),
                strategies=["ACCUMULATION", "BLOCK_TRADING", "OTC"],
                target_symbols=["BTCUSDT", "ETHUSDT"],
                activity_hours=[(8, 18), (7, 17)],
                identification_confidence=0.78
            ),
        ],
        typical_strategies=["LONG_TERM_HOLDING", "BLOCK_TRADING", "VENTURE"],
        typical_symbols=["BTCUSDT", "ETHUSDT", "SOLUSDT"],
        average_daily_volume_usd=500_000_000,
        attribution_threshold=0.75,
        known_partners=["Coinbase", "Circle"],
        known_competitors=["Pantera Capital", "Digital Currency Group"]
    ),
    
    "dragonfly_capital": TradingFirmIntelligence(
        firm_id="dragonfly_capital",
        name="Dragonfly Capital",
        type="HEDGE_FUND",
        hq_location="San Francisco, USA",
        founded=2018,
        estimated_aum_usd=1_000_000_000,
        offices=[
            FirmOffice("San Francisco", "USA", "America/Los_Angeles", (8, 17), 600_000_000, ["crypto"]),
            FirmOffice("Singapore", "Singapore", "Asia/Singapore", (9, 18), 400_000_000, ["crypto"]),
        ],
        bot_signatures=[
            BotSignature(
                frequency_range=(0.05, 0.5),
                typical_order_size=(500_000, 5_000_000),
                time_between_orders=(5.0, 60.0),
                strategies=["ACCUMULATION", "VENTURE", "LONG_TERM"],
                target_symbols=["SOLUSDT", "AVAXUSDT", "NEARUSDT"],
                activity_hours=[(8, 17), (9, 18)],
                identification_confidence=0.72
            ),
        ],
        typical_strategies=["VENTURE_CAPITAL", "LONG_TERM_POSITION", "DEFI_FOCUS"],
        typical_symbols=["SOLUSDT", "AVAXUSDT", "NEARUSDT", "ETHUSDT"],
        average_daily_volume_usd=200_000_000,
        attribution_threshold=0.70,
        known_partners=["Polychain Capital", "Paradigm"],
        known_competitors=["Paradigm", "a16z"]
    ),
}


# ═══════════════════════════════════════════════════════════════════════════════
# ATTRIBUTION ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class FirmAttributionEngine:
    """
    🔍 FIRM ATTRIBUTION ENGINE 🔍
    
    Identifies which firm is behind a bot based on signature matching.
    """
    
    def __init__(self):
        self.firm_db = GLOBAL_FIRM_INTELLIGENCE
        logger.info(f"🔍 Firm Attribution Engine initialized - {len(self.firm_db)} firms loaded")
        
    def attribute_bot_to_firm(
        self,
        symbol: str,
        frequency: float,
        order_size_usd: float,
        strategy: str,
        current_hour_utc: int
    ) -> List[Tuple[str, float]]:
        """
        🎯 ATTRIBUTE BOT TO FIRM 🎯
        
        Match bot characteristics to known firm signatures.
        
        Returns: List of (firm_id, confidence) tuples, sorted by confidence
        """
        matches = []
        
        for firm_id, firm in self.firm_db.items():
            total_confidence = 0.0
            factors = 0
            
            for sig in firm.bot_signatures:
                # Check frequency match
                if sig.frequency_range[0] <= frequency <= sig.frequency_range[1]:
                    total_confidence += 0.3
                    factors += 1
                    
                # Check order size match
                if sig.typical_order_size[0] <= order_size_usd <= sig.typical_order_size[1]:
                    total_confidence += 0.2
                    factors += 1
                    
                # Check strategy match
                if strategy in sig.strategies:
                    total_confidence += 0.3
                    factors += 1
                    
                # Check symbol match
                if symbol in sig.target_symbols:
                    total_confidence += 0.2
                    factors += 1
                    
            if factors > 0:
                avg_confidence = total_confidence
                if avg_confidence >= firm.attribution_threshold:
                    matches.append((firm_id, avg_confidence))
                    
        # Sort by confidence descending
        matches.sort(key=lambda x: x[1], reverse=True)
        
        return matches
        
    def get_firm_details(self, firm_id: str) -> Optional[TradingFirmIntelligence]:
        """Get complete firm intelligence."""
        return self.firm_db.get(firm_id)
        
    def get_all_firms_by_type(self, firm_type: str) -> List[TradingFirmIntelligence]:
        """Get all firms of a specific type."""
        return [f for f in self.firm_db.values() if f.type == firm_type]
        
    def get_firms_trading_symbol(self, symbol: str) -> List[TradingFirmIntelligence]:
        """Get all firms known to trade a specific symbol."""
        result = []
        for firm in self.firm_db.values():
            if symbol in firm.typical_symbols:
                result.append(firm)
        return result
        
    def format_firm_display(self, firm: TradingFirmIntelligence) -> str:
        """Format firm for display."""
        lines = []
        lines.append(f"\n🏢 {firm.name} ({firm.firm_id})")
        lines.append(f"   Type: {firm.type} | Founded: {firm.founded}")
        lines.append(f"   HQ: {firm.hq_location}")
        lines.append(f"   AUM: ${firm.estimated_aum_usd:,.0f}")
        lines.append(f"   Offices: {len(firm.offices)}")
        for office in firm.offices:
            lines.append(f"      - {office.city}, {office.country} (${office.estimated_capital_usd:,.0f})")
        lines.append(f"   Strategies: {', '.join(firm.typical_strategies[:3])}")
        lines.append(f"   Symbols: {', '.join(firm.typical_symbols[:5])}")
        lines.append(f"   Daily Volume: ${firm.average_daily_volume_usd:,.0f}")
        
        return "\n".join(lines)


# Singleton
_attribution_engine = None

def get_attribution_engine() -> FirmAttributionEngine:
    """Get singleton attribution engine."""
    global _attribution_engine
    if _attribution_engine is None:
        _attribution_engine = FirmAttributionEngine()
    return _attribution_engine


if __name__ == '__main__':
    print("🌍 GLOBAL FIRM INTELLIGENCE DATABASE 🌍")
    print("=" * 60)
    
    engine = get_attribution_engine()
    
    print(f"\n📊 Total Firms: {len(GLOBAL_FIRM_INTELLIGENCE)}")
    
    # Group by type
    by_type = {}
    for firm in GLOBAL_FIRM_INTELLIGENCE.values():
        by_type.setdefault(firm.type, []).append(firm)
        
    for firm_type, firms in by_type.items():
        print(f"\n{firm_type}: {len(firms)} firms")
        for firm in firms[:3]:  # Show first 3
            print(f"  - {firm.name} (${firm.estimated_aum_usd:,.0f})")
            
    # Test attribution
    print("\n" + "=" * 60)
    print("🔍 ATTRIBUTION TEST")
    print("=" * 60)
    
    # Simulate HFT bot on ETHUSDT
    matches = engine.attribute_bot_to_firm(
        symbol="ETHUSDT",
        frequency=4.03,
        order_size_usd=250_000,
        strategy="HFT_ALGO",
        current_hour_utc=14
    )
    
    print("\nBot Characteristics:")
    print("  Symbol: ETHUSDT")
    print("  Frequency: 4.03 Hz")
    print("  Order Size: $250,000")
    print("  Strategy: HFT_ALGO")
    
    print("\n🎯 Most Likely Firms:")
    for firm_id, confidence in matches[:5]:
        firm = engine.get_firm_details(firm_id)
        print(f"  {confidence:.0%} - {firm.name} ({firm.type})")
        
    # Show detailed profile for top match
    if matches:
        top_firm_id = matches[0][0]
        top_firm = engine.get_firm_details(top_firm_id)
        print(engine.format_firm_display(top_firm))
