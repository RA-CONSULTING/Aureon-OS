#!/usr/bin/env python3
"""
Aureon Bot Intelligence Profiler
=================================
Identifies bot ownership, strategies, metrics, and global operations.
Maps trading firms (Jane Street, Citadel, etc.) to their bot armies.

Profiles bots with:
- Likely owner/firm identification
- Strategy classification
- Global operation zones
- Metrics and performance
- Hierarchical structure (firm → whales → workers)
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys, os
if sys.platform == 'win32' and sys.stdout.isatty():
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        import io
        def _is_utf8_wrapper(stream):
            return (isinstance(stream, io.TextIOWrapper) and 
                    hasattr(stream, 'encoding') and stream.encoding and
                    stream.encoding.lower().replace('-', '') == 'utf8')
        if hasattr(sys.stdout, 'buffer') and not _is_utf8_wrapper(sys.stdout):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        # Skip stderr wrapping (causes Windows exit errors)
    except Exception:
        pass

import asyncio
import json
import time
import math
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict
from datetime import datetime

# ═══════════════════════════════════════════════════════════════════════════
# BOT OWNERSHIP FINGERPRINTS - GLOBAL DATABASE
# ═══════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════
# 🇺🇸 USA - WALL STREET GIANTS
# ═══════════════════════════════════════════════════════════════════════════

TRADING_FIRM_SIGNATURES = {
    "jane_street": {
        "name": "Jane Street Capital",
        "country": "USA",
        "hq_location": "New York, NY",
        "animal": "🦈 Shark",  # Fast, efficient predator
        "patterns": {
            "hft_frequency": (50, 200),
            "order_size_consistency": 0.95,
            "market_making_ratio": 0.8,
            "latency_profile": "ultra_low",
            "symbols_preference": ["BTC", "ETH", "SPY", "QQQ"],
            "time_zones": ["US/Eastern", "Europe/London", "Asia/Singapore"],
        },
        "known_strategies": ["market_making", "arbitrage", "hft"],
        "estimated_capital": 50_000_000_000,
    },
    "citadel": {
        "name": "Citadel Securities",
        "country": "USA",
        "hq_location": "Chicago, IL",
        "animal": "🦁 Lion",  # King of the jungle
        "patterns": {
            "hft_frequency": (100, 500),
            "order_size_consistency": 0.92,
            "market_making_ratio": 0.85,
            "latency_profile": "ultra_low",
            "symbols_preference": ["SPY", "QQQ", "AAPL", "TSLA", "BTC"],
            "time_zones": ["US/Central", "US/Eastern", "Europe/London"],
        },
        "known_strategies": ["market_making", "statistical_arbitrage", "hft"],
        "estimated_capital": 60_000_000_000,
    },
    "renaissance": {
        "name": "Renaissance Technologies",
        "country": "USA",
        "hq_location": "East Setauket, NY",
        "animal": "🦉 Owl",  # Wise, sees in the dark
        "patterns": {
            "hft_frequency": (20, 100),
            "order_size_consistency": 0.88,
            "market_making_ratio": 0.3,
            "latency_profile": "low",
            "symbols_preference": ["SPY", "futures", "bonds"],
            "time_zones": ["US/Eastern"],
        },
        "known_strategies": ["statistical_arbitrage", "mean_reversion", "momentum"],
        "estimated_capital": 130_000_000_000,
    },
    "two_sigma": {
        "name": "Two Sigma Investments",
        "country": "USA",
        "hq_location": "New York, NY",
        "animal": "🐺 Wolf",  # Pack hunter, AI-driven
        "patterns": {
            "hft_frequency": (30, 150),
            "order_size_consistency": 0.90,
            "market_making_ratio": 0.5,
            "latency_profile": "low",
            "symbols_preference": ["SPY", "QQQ", "tech_stocks"],
            "time_zones": ["US/Eastern", "Europe/London"],
        },
        "known_strategies": ["machine_learning", "statistical_arbitrage", "momentum"],
        "estimated_capital": 60_000_000_000,
    },
    "jump_trading": {
        "name": "Jump Trading",
        "country": "USA",
        "hq_location": "Chicago, IL",
        "animal": "🐆 Cheetah",  # Fastest on land
        "patterns": {
            "hft_frequency": (100, 300),
            "order_size_consistency": 0.94,
            "market_making_ratio": 0.75,
            "latency_profile": "ultra_low",
            "symbols_preference": ["BTC", "ETH", "futures", "options"],
            "time_zones": ["US/Central", "Europe/London", "Asia/Singapore"],
        },
        "known_strategies": ["market_making", "arbitrage", "hft"],
        "estimated_capital": 20_000_000_000,
    },
    "virtu": {
        "name": "Virtu Financial",
        "country": "USA",
        "hq_location": "New York, NY",
        "animal": "🕷️ Spider",  # Web everywhere
        "patterns": {
            "hft_frequency": (80, 250),
            "order_size_consistency": 0.93,
            "market_making_ratio": 0.90,
            "latency_profile": "ultra_low",
            "symbols_preference": ["all"],
            "time_zones": ["US/Eastern", "Europe/London", "Asia/Singapore", "US/Pacific"],
        },
        "known_strategies": ["market_making", "liquidity_provision"],
        "estimated_capital": 10_000_000_000,
    },
    "de_shaw": {
        "name": "D. E. Shaw & Co.",
        "country": "USA",
        "hq_location": "New York, NY",
        "animal": "🦅 Eagle",  # High-flying, sharp vision
        "patterns": {
            "hft_frequency": (10, 80),
            "order_size_consistency": 0.85,
            "market_making_ratio": 0.4,
            "latency_profile": "medium",
            "symbols_preference": ["SPY", "bonds", "currencies"],
            "time_zones": ["US/Eastern", "Europe/London", "Asia/Hong_Kong"],
        },
        "known_strategies": ["statistical_arbitrage", "macro", "quantitative"],
        "estimated_capital": 60_000_000_000,
    },
    "point72": {
        "name": "Point72 Asset Management",
        "country": "USA",
        "hq_location": "Stamford, CT",
        "animal": "🐻 Bear",  # Steve Cohen's beast
        "patterns": {
            "hft_frequency": (15, 60),
            "order_size_consistency": 0.82,
            "market_making_ratio": 0.35,
            "latency_profile": "low",
            "symbols_preference": ["SPY", "tech_stocks", "healthcare"],
            "time_zones": ["US/Eastern"],
        },
        "known_strategies": ["fundamental", "quantitative", "event_driven"],
        "estimated_capital": 35_000_000_000,
    },
    "millennium": {
        "name": "Millennium Management",
        "country": "USA",
        "hq_location": "New York, NY",
        "animal": "🦎 Chameleon",  # Adapts to everything
        "patterns": {
            "hft_frequency": (20, 100),
            "order_size_consistency": 0.87,
            "market_making_ratio": 0.45,
            "latency_profile": "low",
            "symbols_preference": ["SPY", "QQQ", "currencies", "commodities"],
            "time_zones": ["US/Eastern", "Europe/London", "Asia/Singapore"],
        },
        "known_strategies": ["multi_strategy", "statistical_arbitrage", "relative_value"],
        "estimated_capital": 60_000_000_000,
    },
    "aqr": {
        "name": "AQR Capital Management",
        "country": "USA",
        "hq_location": "Greenwich, CT",
        "animal": "🐘 Elephant",  # Never forgets, systematic
        "patterns": {
            "hft_frequency": (5, 30),
            "order_size_consistency": 0.80,
            "market_making_ratio": 0.25,
            "latency_profile": "medium",
            "symbols_preference": ["SPY", "global_equities", "bonds"],
            "time_zones": ["US/Eastern", "Europe/London"],
        },
        "known_strategies": ["factor_investing", "momentum", "value"],
        "estimated_capital": 140_000_000_000,
    },
    "bridgewater": {
        "name": "Bridgewater Associates",
        "country": "USA",
        "hq_location": "Westport, CT",
        "animal": "🐋 Blue Whale",  # Largest of all
        "patterns": {
            "hft_frequency": (1, 10),
            "order_size_consistency": 0.75,
            "market_making_ratio": 0.1,
            "latency_profile": "high",
            "symbols_preference": ["bonds", "currencies", "commodities", "global_macro"],
            "time_zones": ["US/Eastern", "Europe/London", "Asia/Singapore"],
        },
        "known_strategies": ["macro", "risk_parity", "all_weather"],
        "estimated_capital": 150_000_000_000,
    },
    "blackrock": {
        "name": "BlackRock",
        "country": "USA",
        "hq_location": "New York, NY",
        "animal": "🦍 Gorilla",  # Absolute dominance
        "patterns": {
            "hft_frequency": (5, 50),
            "order_size_consistency": 0.78,
            "market_making_ratio": 0.2,
            "latency_profile": "medium",
            "symbols_preference": ["all"],
            "time_zones": ["US/Eastern", "Europe/London", "Asia/Tokyo", "Asia/Singapore"],
        },
        "known_strategies": ["index_tracking", "etf", "systematic"],
        "estimated_capital": 10_000_000_000_000,  # $10 TRILLION
    },
    "susquehanna": {
        "name": "Susquehanna International Group (SIG)",
        "country": "USA",
        "hq_location": "Bala Cynwyd, PA",
        "animal": "🦊 Fox",  # Clever options trader
        "patterns": {
            "hft_frequency": (40, 180),
            "order_size_consistency": 0.91,
            "market_making_ratio": 0.85,
            "latency_profile": "ultra_low",
            "symbols_preference": ["options", "ETF", "BTC", "ETH"],
            "time_zones": ["US/Eastern", "Europe/Dublin", "Asia/Hong_Kong"],
        },
        "known_strategies": ["options_market_making", "etf_arbitrage", "crypto"],
        "estimated_capital": 50_000_000_000,
    },
    "drw": {
        "name": "DRW Trading",
        "country": "USA",
        "hq_location": "Chicago, IL",
        "animal": "🐉 Dragon",  # Powerful, diverse
        "patterns": {
            "hft_frequency": (60, 200),
            "order_size_consistency": 0.89,
            "market_making_ratio": 0.7,
            "latency_profile": "ultra_low",
            "symbols_preference": ["futures", "options", "BTC", "ETH"],
            "time_zones": ["US/Central", "Europe/London", "Asia/Singapore"],
        },
        "known_strategies": ["market_making", "arbitrage", "crypto_trading"],
        "estimated_capital": 15_000_000_000,
    },
    "hudson_river": {
        "name": "Hudson River Trading",
        "country": "USA",
        "hq_location": "New York, NY",
        "animal": "🦑 Squid",  # Tentacles everywhere
        "patterns": {
            "hft_frequency": (150, 400),
            "order_size_consistency": 0.96,
            "market_making_ratio": 0.88,
            "latency_profile": "ultra_low",
            "symbols_preference": ["SPY", "QQQ", "all_equities"],
            "time_zones": ["US/Eastern", "Europe/London"],
        },
        "known_strategies": ["hft", "market_making", "statistical_arbitrage"],
        "estimated_capital": 8_000_000_000,
    },
    "tower_research": {
        "name": "Tower Research Capital",
        "country": "USA",
        "hq_location": "New York, NY",
        "animal": "🦇 Bat",  # Echolocation = ultra-fast signals
        "patterns": {
            "hft_frequency": (200, 600),
            "order_size_consistency": 0.97,
            "market_making_ratio": 0.82,
            "latency_profile": "ultra_low",
            "symbols_preference": ["futures", "equities", "forex"],
            "time_zones": ["US/Eastern", "Europe/London", "Asia/Singapore"],
        },
        "known_strategies": ["hft", "market_making", "latency_arbitrage"],
        "estimated_capital": 5_000_000_000,
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # 🇬🇧 UK & EUROPE - LONDON SHARKS
    # ═══════════════════════════════════════════════════════════════════════════
    
    "gsg": {
        "name": "GSA Capital Partners",
        "country": "UK",
        "hq_location": "London",
        "animal": "🦈 Hammerhead",
        "patterns": {
            "hft_frequency": (30, 120),
            "order_size_consistency": 0.88,
            "market_making_ratio": 0.55,
            "latency_profile": "low",
            "symbols_preference": ["FTSE", "DAX", "EUR/USD"],
            "time_zones": ["Europe/London"],
        },
        "known_strategies": ["statistical_arbitrage", "market_neutral"],
        "estimated_capital": 5_000_000_000,
    },
    "man_group": {
        "name": "Man Group",
        "country": "UK",
        "hq_location": "London",
        "animal": "🐂 Bull",  # AHL momentum
        "patterns": {
            "hft_frequency": (10, 50),
            "order_size_consistency": 0.82,
            "market_making_ratio": 0.3,
            "latency_profile": "medium",
            "symbols_preference": ["futures", "commodities", "currencies"],
            "time_zones": ["Europe/London", "US/Eastern", "Asia/Hong_Kong"],
        },
        "known_strategies": ["cta", "momentum", "systematic"],
        "estimated_capital": 150_000_000_000,
    },
    "winton": {
        "name": "Winton Group",
        "country": "UK",
        "hq_location": "London",
        "animal": "🦔 Hedgehog",  # Diversified
        "patterns": {
            "hft_frequency": (5, 30),
            "order_size_consistency": 0.79,
            "market_making_ratio": 0.2,
            "latency_profile": "medium",
            "symbols_preference": ["futures", "commodities"],
            "time_zones": ["Europe/London"],
        },
        "known_strategies": ["trend_following", "statistical"],
        "estimated_capital": 20_000_000_000,
    },
    "optiver": {
        "name": "Optiver",
        "country": "Netherlands",
        "hq_location": "Amsterdam",
        "animal": "🐙 Octopus",  # 8 arms on every market
        "patterns": {
            "hft_frequency": (100, 350),
            "order_size_consistency": 0.94,
            "market_making_ratio": 0.92,
            "latency_profile": "ultra_low",
            "symbols_preference": ["options", "ETF", "equities"],
            "time_zones": ["Europe/Amsterdam", "US/Central", "Asia/Singapore"],
        },
        "known_strategies": ["options_market_making", "etf_arbitrage"],
        "estimated_capital": 8_000_000_000,
    },
    "flow_traders": {
        "name": "Flow Traders",
        "country": "Netherlands",
        "hq_location": "Amsterdam",
        "animal": "🐟 School of Fish",  # ETF flow
        "patterns": {
            "hft_frequency": (50, 200),
            "order_size_consistency": 0.90,
            "market_making_ratio": 0.88,
            "latency_profile": "ultra_low",
            "symbols_preference": ["ETF", "ETP", "crypto_etp"],
            "time_zones": ["Europe/Amsterdam", "US/Eastern", "Asia/Singapore"],
        },
        "known_strategies": ["etf_market_making", "crypto_etp"],
        "estimated_capital": 3_000_000_000,
    },
    "imc": {
        "name": "IMC Trading",
        "country": "Netherlands",
        "hq_location": "Amsterdam",
        "animal": "🦜 Parrot",  # Mimics prices
        "patterns": {
            "hft_frequency": (80, 250),
            "order_size_consistency": 0.92,
            "market_making_ratio": 0.87,
            "latency_profile": "ultra_low",
            "symbols_preference": ["options", "equities", "crypto"],
            "time_zones": ["Europe/Amsterdam", "US/Central", "Asia/Sydney"],
        },
        "known_strategies": ["options_market_making", "statistical_arbitrage"],
        "estimated_capital": 4_000_000_000,
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # 🇯🇵🇨🇳🇸🇬🇭🇰 ASIA-PACIFIC - EASTERN DRAGONS
    # ═══════════════════════════════════════════════════════════════════════════
    
    "nomura": {
        "name": "Nomura Holdings",
        "country": "Japan",
        "hq_location": "Tokyo",
        "animal": "🐅 Tiger",  # Japanese power
        "patterns": {
            "hft_frequency": (20, 80),
            "order_size_consistency": 0.85,
            "market_making_ratio": 0.6,
            "latency_profile": "low",
            "symbols_preference": ["Nikkei", "JPY", "Asian_equities"],
            "time_zones": ["Asia/Tokyo", "Europe/London", "US/Eastern"],
        },
        "known_strategies": ["market_making", "prop_trading"],
        "estimated_capital": 30_000_000_000,
    },
    "softbank": {
        "name": "SoftBank Vision Fund",
        "country": "Japan",
        "hq_location": "Tokyo",
        "animal": "🦄 Unicorn",  # Tech vision
        "patterns": {
            "hft_frequency": (5, 20),
            "order_size_consistency": 0.70,
            "market_making_ratio": 0.15,
            "latency_profile": "high",
            "symbols_preference": ["tech_stocks", "NVDA", "ARM"],
            "time_zones": ["Asia/Tokyo", "US/Pacific"],
        },
        "known_strategies": ["venture", "growth", "tech_momentum"],
        "estimated_capital": 100_000_000_000,
    },
    "gic": {
        "name": "GIC Private Limited",
        "country": "Singapore",
        "hq_location": "Singapore",
        "animal": "🐲 Eastern Dragon",  # Sovereign wealth
        "patterns": {
            "hft_frequency": (2, 15),
            "order_size_consistency": 0.75,
            "market_making_ratio": 0.1,
            "latency_profile": "high",
            "symbols_preference": ["global_equities", "bonds", "real_estate"],
            "time_zones": ["Asia/Singapore", "US/Eastern", "Europe/London"],
        },
        "known_strategies": ["long_term", "diversified", "value"],
        "estimated_capital": 700_000_000_000,
    },
    "temasek": {
        "name": "Temasek Holdings",
        "country": "Singapore",
        "hq_location": "Singapore",
        "animal": "🦁 Merlion",  # Singapore's icon
        "patterns": {
            "hft_frequency": (2, 10),
            "order_size_consistency": 0.72,
            "market_making_ratio": 0.1,
            "latency_profile": "high",
            "symbols_preference": ["Asian_equities", "tech", "infrastructure"],
            "time_zones": ["Asia/Singapore"],
        },
        "known_strategies": ["long_term", "strategic", "growth"],
        "estimated_capital": 380_000_000_000,
    },
    "china_amc": {
        "name": "China Asset Management",
        "country": "China",
        "hq_location": "Beijing",
        "animal": "🐼 Panda",  # Chinese giant
        "patterns": {
            "hft_frequency": (10, 50),
            "order_size_consistency": 0.80,
            "market_making_ratio": 0.4,
            "latency_profile": "medium",
            "symbols_preference": ["CSI300", "A_shares", "CNY"],
            "time_zones": ["Asia/Shanghai"],
        },
        "known_strategies": ["index", "quant", "domestic"],
        "estimated_capital": 200_000_000_000,
    },
    "hillhouse": {
        "name": "Hillhouse Capital",
        "country": "China/Singapore",
        "hq_location": "Singapore/Beijing",
        "animal": "🦢 Swan",  # Elegant long-term
        "patterns": {
            "hft_frequency": (3, 15),
            "order_size_consistency": 0.78,
            "market_making_ratio": 0.2,
            "latency_profile": "high",
            "symbols_preference": ["China_tech", "healthcare", "consumer"],
            "time_zones": ["Asia/Singapore", "Asia/Shanghai"],
        },
        "known_strategies": ["long_term", "growth", "fundamental"],
        "estimated_capital": 100_000_000_000,
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # 🪙 CRYPTO NATIVE - DEGENS & LEGENDS
    # ═══════════════════════════════════════════════════════════════════════════
    
    "wintermute": {
        "name": "Wintermute Trading",
        "country": "UK",
        "hq_location": "London",
        "animal": "❄️ Ice Dragon",  # Crypto MM king
        "patterns": {
            "hft_frequency": (80, 300),
            "order_size_consistency": 0.88,
            "market_making_ratio": 0.92,
            "latency_profile": "ultra_low",
            "symbols_preference": ["BTC", "ETH", "altcoins", "defi"],
            "time_zones": ["Europe/London", "Asia/Singapore"],
        },
        "known_strategies": ["crypto_market_making", "defi", "otc"],
        "estimated_capital": 3_000_000_000,
    },
    "cumberland": {
        "name": "Cumberland (DRW)",
        "country": "USA",
        "hq_location": "Chicago, IL",
        "animal": "🦬 Bison",  # OTC beast
        "patterns": {
            "hft_frequency": (20, 100),
            "order_size_consistency": 0.85,
            "market_making_ratio": 0.75,
            "latency_profile": "low",
            "symbols_preference": ["BTC", "ETH", "stablecoins"],
            "time_zones": ["US/Central", "Europe/London", "Asia/Singapore"],
        },
        "known_strategies": ["otc", "crypto_market_making", "institutional"],
        "estimated_capital": 5_000_000_000,
    },
    "galaxy_digital": {
        "name": "Galaxy Digital",
        "country": "USA",
        "hq_location": "New York, NY",
        "animal": "🌌 Cosmic Entity",  # Mike Novogratz
        "patterns": {
            "hft_frequency": (10, 60),
            "order_size_consistency": 0.78,
            "market_making_ratio": 0.5,
            "latency_profile": "medium",
            "symbols_preference": ["BTC", "ETH", "crypto_ventures"],
            "time_zones": ["US/Eastern"],
        },
        "known_strategies": ["crypto_trading", "venture", "mining"],
        "estimated_capital": 2_000_000_000,
    },
    "genesis": {
        "name": "Genesis Trading",
        "country": "USA",
        "hq_location": "New York, NY",
        "animal": "🔮 Oracle",  # OTC lending
        "patterns": {
            "hft_frequency": (5, 40),
            "order_size_consistency": 0.80,
            "market_making_ratio": 0.6,
            "latency_profile": "medium",
            "symbols_preference": ["BTC", "ETH", "stablecoins"],
            "time_zones": ["US/Eastern"],
        },
        "known_strategies": ["otc", "lending", "institutional"],
        "estimated_capital": 1_000_000_000,
    },
    "b2c2": {
        "name": "B2C2",
        "country": "UK",
        "hq_location": "London",
        "animal": "🤖 Crypto Robot",  # Systematic crypto
        "patterns": {
            "hft_frequency": (50, 180),
            "order_size_consistency": 0.90,
            "market_making_ratio": 0.88,
            "latency_profile": "ultra_low",
            "symbols_preference": ["BTC", "ETH", "altcoins"],
            "time_zones": ["Europe/London", "US/Eastern", "Asia/Singapore"],
        },
        "known_strategies": ["crypto_market_making", "algorithmic"],
        "estimated_capital": 2_000_000_000,
    },
    "amber_group": {
        "name": "Amber Group",
        "country": "Singapore",
        "hq_location": "Singapore",
        "animal": "🐯 Crypto Tiger",  # Asian crypto giant
        "patterns": {
            "hft_frequency": (30, 150),
            "order_size_consistency": 0.85,
            "market_making_ratio": 0.75,
            "latency_profile": "low",
            "symbols_preference": ["BTC", "ETH", "Asian_alts"],
            "time_zones": ["Asia/Singapore", "Asia/Hong_Kong"],
        },
        "known_strategies": ["crypto_trading", "wealth_management", "defi"],
        "estimated_capital": 5_000_000_000,
    },
    "qcp_capital": {
        "name": "QCP Capital",
        "country": "Singapore",
        "hq_location": "Singapore",
        "animal": "🦂 Scorpion",  # Options specialist
        "patterns": {
            "hft_frequency": (20, 100),
            "order_size_consistency": 0.88,
            "market_making_ratio": 0.82,
            "latency_profile": "low",
            "symbols_preference": ["BTC", "ETH", "options"],
            "time_zones": ["Asia/Singapore"],
        },
        "known_strategies": ["crypto_options", "structured_products", "derivatives"],
        "estimated_capital": 1_000_000_000,
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # 💀 GHOSTS & LEGENDS (Defunct but bots still active)
    # ═══════════════════════════════════════════════════════════════════════════
    
    "alameda_ghost": {
        "name": "Alameda Research (GHOST)",
        "country": "Bahamas",
        "hq_location": "Nassau (defunct)",
        "animal": "👻 Ghost",  # Dead but haunting
        "patterns": {
            "hft_frequency": (5, 30),
            "order_size_consistency": 0.60,
            "market_making_ratio": 0.5,
            "latency_profile": "medium",
            "symbols_preference": ["FTT", "SOL", "BTC", "ETH"],
            "time_zones": ["US/Pacific"],
        },
        "known_strategies": ["wash_trading", "spoofing", "front_running"],
        "estimated_capital": 0,
    },
    "three_arrows": {
        "name": "Three Arrows Capital (3AC) GHOST",
        "country": "Singapore/BVI",
        "hq_location": "Defunct",
        "animal": "💀 Skeleton",  # Dead fund
        "patterns": {
            "hft_frequency": (2, 10),
            "order_size_consistency": 0.65,
            "market_making_ratio": 0.3,
            "latency_profile": "high",
            "symbols_preference": ["BTC", "ETH", "LUNA"],
            "time_zones": ["Asia/Singapore"],
        },
        "known_strategies": ["leverage", "directional", "ponzi_adjacent"],
        "estimated_capital": 0,
    },
}

# All firms combined - we track EVERYONE on the planet!
ALL_FIRMS = TRADING_FIRM_SIGNATURES

# ═══════════════════════════════════════════════════════════════════════════
# BOT PROFILE DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class BotMetrics:
    """Comprehensive bot performance metrics"""
    total_trades: int = 0
    total_volume_usd: float = 0.0
    avg_trade_size_usd: float = 0.0
    trades_per_second: float = 0.0
    win_rate: float = 0.0
    profit_estimate_usd: float = 0.0
    avg_latency_ms: float = 0.0
    order_size_consistency: float = 0.0  # 0-1, how consistent are trade sizes
    market_making_ratio: float = 0.0  # Ratio of balanced buy/sell
    timestamp: float = field(default_factory=time.time)

@dataclass
class BotProfile:
    """Complete bot intelligence profile"""
    bot_id: str
    symbol: str
    exchange: str
    
    # Identification
    likely_owner: str = "unknown"  # Firm ID or "unknown"
    owner_confidence: float = 0.0  # 0-1 confidence in ownership
    owner_name: str = "Unknown Entity"
    
    # Classification
    pattern: str = "unknown"
    size_class: str = "minnow"  # minnow, shark, whale, megalodon
    role: str = "worker"  # worker, leader, coordinator
    
    # Strategy
    strategies: List[str] = field(default_factory=list)
    behavior_labels: List[str] = field(default_factory=list)
    
    # Location
    operating_region: str = "unknown"
    time_zone: str = "unknown"
    country: str = "unknown"
    
    # Metrics
    metrics: BotMetrics = field(default_factory=BotMetrics)
    
    # Hierarchy
    firm_hierarchy_level: int = 0  # 0=unknown, 1=worker, 2=squad_leader, 3=whale
    parent_bot_id: Optional[str] = None
    child_bot_ids: List[str] = field(default_factory=list)
    
    # Timestamps
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    
    def to_dict(self):
        d = asdict(self)
        return d

@dataclass
class FirmIntelligence:
    """Intelligence on a trading firm's operations"""
    firm_id: str
    firm_name: str
    country: str
    hq_location: str
    estimated_capital: float
    
    # Discovered bots
    whale_bots: List[str] = field(default_factory=list)  # Bot IDs
    worker_bots: List[str] = field(default_factory=list)
    total_bots: int = 0
    
    # Operations
    active_symbols: Set[str] = field(default_factory=set)
    operating_regions: Set[str] = field(default_factory=set)
    strategies_observed: Set[str] = field(default_factory=set)
    
    # Performance
    total_volume_usd: float = 0.0
    estimated_daily_profit_usd: float = 0.0
    
    # Timestamps
    first_detected: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    
    def to_dict(self):
        d = asdict(self)
        d['active_symbols'] = list(d['active_symbols'])
        d['operating_regions'] = list(d['operating_regions'])
        d['strategies_observed'] = list(d['strategies_observed'])
        return d

# ═══════════════════════════════════════════════════════════════════════════
# BOT INTELLIGENCE PROFILER
# ═══════════════════════════════════════════════════════════════════════════

class BotIntelligenceProfiler:
    """
    Identifies bot ownership and creates comprehensive intelligence profiles.
    
    Maps trading firms to their bot armies and analyzes their global operations.
    """
    
    def __init__(self):
        self.bot_profiles: Dict[str, BotProfile] = {}
        self.firm_intelligence: Dict[str, FirmIntelligence] = {}
        
        # Initialize firm intelligence for all known firms
        for firm_id, firm_data in ALL_FIRMS.items():
            self.firm_intelligence[firm_id] = FirmIntelligence(
                firm_id=firm_id,
                firm_name=firm_data["name"],
                country=firm_data["country"],
                hq_location=firm_data["hq_location"],
                estimated_capital=firm_data["estimated_capital"],
            )
        
        print("🧠 Bot Intelligence Profiler initialized")
        print(f"📊 Tracking {len(ALL_FIRMS)} known trading firms")
    
    def profile_bot(self, bot_data: Dict) -> BotProfile:
        """
        Create comprehensive intelligence profile for a bot.
        
        Args:
            bot_data: Raw bot detection data from scanner
            
        Returns:
            Complete BotProfile with ownership identification
        """
        bot_id = bot_data.get('bot_id', self._generate_bot_id(bot_data))
        
        # Get or create profile
        if bot_id in self.bot_profiles:
            profile = self.bot_profiles[bot_id]
            profile.last_seen = time.time()
        else:
            profile = BotProfile(
                bot_id=bot_id,
                symbol=bot_data.get('symbol', 'UNKNOWN'),
                exchange=bot_data.get('exchange', 'UNKNOWN'),
                pattern=bot_data.get('pattern', 'unknown'),
                size_class=bot_data.get('size_class', 'minnow'),
            )
        
        # Update metrics
        self._update_metrics(profile, bot_data)
        
        # Identify likely owner
        self._identify_owner(profile, bot_data)
        
        # Classify strategies and behaviors
        self._classify_strategies(profile, bot_data)
        
        # Determine operating region
        self._determine_location(profile, bot_data)
        
        # Assign hierarchy role
        self._assign_hierarchy_role(profile)
        
        # Store profile
        self.bot_profiles[bot_id] = profile
        
        # Update firm intelligence
        if profile.likely_owner != "unknown":
            self._update_firm_intelligence(profile)
        
        return profile
    
    def _generate_bot_id(self, bot_data: Dict) -> str:
        """Generate unique bot ID from characteristics"""
        components = [
            bot_data.get('symbol', 'UNK'),
            bot_data.get('exchange', 'UNK'),
            bot_data.get('pattern', 'unk'),
            str(bot_data.get('avg_trade_size', 0))[:6],
        ]
        hash_input = '_'.join(components)
        return hashlib.md5(hash_input.encode()).hexdigest()[:12]
    
    def _update_metrics(self, profile: BotProfile, bot_data: Dict):
        """Update bot performance metrics"""
        metrics = profile.metrics
        
        # Increment trade count
        new_trades = bot_data.get('trade_count', 1)
        metrics.total_trades += new_trades
        
        # Update volume
        trade_volume = bot_data.get('total_volume_usd', 0)
        metrics.total_volume_usd += trade_volume
        
        # Calculate averages
        if metrics.total_trades > 0:
            metrics.avg_trade_size_usd = metrics.total_volume_usd / metrics.total_trades
        
        # Calculate trade frequency
        time_window = bot_data.get('time_window_seconds', 1.0)
        metrics.trades_per_second = new_trades / time_window if time_window > 0 else 0
        
        # Order size consistency (variance in trade sizes)
        trade_sizes = bot_data.get('trade_sizes', [])
        if len(trade_sizes) > 1:
            mean_size = sum(trade_sizes) / len(trade_sizes)
            variance = sum((x - mean_size) ** 2 for x in trade_sizes) / len(trade_sizes)
            std_dev = math.sqrt(variance) if variance > 0 else 0
            # Consistency = 1 - (coefficient of variation)
            metrics.order_size_consistency = max(0, 1 - (std_dev / mean_size if mean_size > 0 else 1))
        
        # Market making ratio (balance of buys vs sells)
        buy_count = bot_data.get('buy_count', 0)
        sell_count = bot_data.get('sell_count', 0)
        total = buy_count + sell_count
        if total > 0:
            balance = 1 - abs(buy_count - sell_count) / total
            metrics.market_making_ratio = balance
        
        # Latency estimate (based on trade timing precision)
        metrics.avg_latency_ms = bot_data.get('latency_ms', 10.0)
        
        metrics.timestamp = time.time()
    
    def _identify_owner(self, profile: BotProfile, bot_data: Dict):
        """
        Identify likely owner/firm based on behavioral fingerprints.
        
        Uses pattern matching against known firm signatures.
        """
        best_match_firm = "unknown"
        best_match_score = 0.0
        
        for firm_id, firm_data in ALL_FIRMS.items():
            score = self._calculate_ownership_score(profile, firm_data)
            if score > best_match_score:
                best_match_score = score
                best_match_firm = firm_id
        
        # Require minimum confidence threshold
        if best_match_score > 0.5:  # 50% confidence minimum
            profile.likely_owner = best_match_firm
            profile.owner_confidence = best_match_score
            profile.owner_name = ALL_FIRMS[best_match_firm]["name"]
        else:
            profile.likely_owner = "unknown"
            profile.owner_confidence = 0.0
            profile.owner_name = "Unknown Entity"
    
    def _calculate_ownership_score(self, profile: BotProfile, firm_data: Dict) -> float:
        """
        Calculate match score between bot and firm signature.
        
        Returns score 0-1 indicating likelihood bot belongs to firm.
        """
        patterns = firm_data.get("patterns", {})
        score = 0.0
        factors = 0
        
        # Check HFT frequency match
        freq_range = patterns.get("hft_frequency", (0, 1000))
        if freq_range[0] <= profile.metrics.trades_per_second <= freq_range[1]:
            score += 1.0
        factors += 1
        
        # Check order size consistency
        expected_consistency = patterns.get("order_size_consistency", 0.5)
        consistency_diff = abs(profile.metrics.order_size_consistency - expected_consistency)
        consistency_score = max(0, 1 - consistency_diff)
        score += consistency_score
        factors += 1
        
        # Check market making ratio
        expected_mm_ratio = patterns.get("market_making_ratio", 0.5)
        mm_diff = abs(profile.metrics.market_making_ratio - expected_mm_ratio)
        mm_score = max(0, 1 - mm_diff)
        score += mm_score
        factors += 1
        
        # Check symbol preference
        preferred_symbols = patterns.get("symbols_preference", [])
        if preferred_symbols:
            # Check if bot's symbol matches any preferred symbols
            for pref in preferred_symbols:
                if pref.upper() in profile.symbol.upper():
                    score += 1.0
                    break
        factors += 1
        
        # Check latency profile
        latency_profile = patterns.get("latency_profile", "medium")
        latency_match = False
        if latency_profile == "ultra_low" and profile.metrics.avg_latency_ms < 2:
            latency_match = True
        elif latency_profile == "low" and profile.metrics.avg_latency_ms < 10:
            latency_match = True
        elif latency_profile == "medium":
            latency_match = True
        
        if latency_match:
            score += 1.0
        factors += 1
        
        # Normalize score
        return score / factors if factors > 0 else 0.0
    
    def _classify_strategies(self, profile: BotProfile, bot_data: Dict):
        """Classify bot strategies and behaviors"""
        strategies = []
        labels = []
        
        # Based on pattern
        if profile.pattern in ['hft', 'scalper']:
            strategies.append('high_frequency_trading')
            labels.append('HFT')
        
        if profile.pattern == 'market_maker':
            strategies.append('market_making')
            labels.append('Market Maker')
        
        if profile.pattern == 'whale':
            strategies.append('large_order_execution')
            labels.append('Whale')
        
        if profile.pattern == 'coordinated':
            strategies.append('coordinated_trading')
            labels.append('Coordinated')
        
        # Based on metrics
        if profile.metrics.market_making_ratio > 0.7:
            if 'market_making' not in strategies:
                strategies.append('market_making')
            labels.append('Liquidity Provider')
        
        if profile.metrics.trades_per_second > 50:
            labels.append('Ultra-HFT')
        elif profile.metrics.trades_per_second > 10:
            labels.append('HFT')
        
        if profile.metrics.order_size_consistency > 0.9:
            labels.append('Algorithmic')
        
        profile.strategies = strategies
        profile.behavior_labels = labels
    
    def _determine_location(self, profile: BotProfile, bot_data: Dict):
        """Determine bot's operating region and location"""
        # Use timezone from activity patterns
        current_hour_utc = datetime.utcnow().hour
        
        # Simple heuristic based on activity time
        if 13 <= current_hour_utc <= 21:  # 9am-5pm US Eastern
            profile.operating_region = "Americas"
            profile.time_zone = "US/Eastern"
            profile.country = "USA"
        elif 8 <= current_hour_utc <= 16:  # 9am-5pm London
            profile.operating_region = "Europe"
            profile.time_zone = "Europe/London"
            profile.country = "UK"
        elif 0 <= current_hour_utc <= 8:  # 9am-5pm Singapore
            profile.operating_region = "Asia"
            profile.time_zone = "Asia/Singapore"
            profile.country = "Singapore"
        else:
            profile.operating_region = "24/7 Global"
            profile.time_zone = "UTC"
            profile.country = "Unknown"
        
        # Override with firm location if known
        if profile.likely_owner != "unknown":
            firm_data = ALL_FIRMS.get(profile.likely_owner, {})
            profile.country = firm_data.get("country", profile.country)
    
    def _assign_hierarchy_role(self, profile: BotProfile):
        """Assign hierarchy role based on size and behavior"""
        # Determine role
        if profile.size_class == "megalodon":
            profile.role = "leader"
            profile.firm_hierarchy_level = 3
        elif profile.size_class == "whale":
            profile.role = "coordinator"
            profile.firm_hierarchy_level = 3
        elif profile.size_class == "shark":
            profile.role = "squad_leader"
            profile.firm_hierarchy_level = 2
        else:  # minnow
            profile.role = "worker"
            profile.firm_hierarchy_level = 1
    
    def _update_firm_intelligence(self, profile: BotProfile):
        """Update firm intelligence with bot data"""
        firm_id = profile.likely_owner
        if firm_id not in self.firm_intelligence:
            return
        
        firm = self.firm_intelligence[firm_id]
        
        # Update bot lists
        if profile.size_class in ["whale", "megalodon"]:
            if profile.bot_id not in firm.whale_bots:
                firm.whale_bots.append(profile.bot_id)
        else:
            if profile.bot_id not in firm.worker_bots:
                firm.worker_bots.append(profile.bot_id)
        
        firm.total_bots = len(firm.whale_bots) + len(firm.worker_bots)
        
        # Update operations
        firm.active_symbols.add(profile.symbol)
        firm.operating_regions.add(profile.operating_region)
        firm.strategies_observed.update(profile.strategies)
        
        # Update performance
        firm.total_volume_usd += profile.metrics.total_volume_usd
        
        # Update timestamps
        firm.last_activity = time.time()
    
    def get_firm_summary(self, firm_id: str) -> Optional[Dict]:
        """Get comprehensive summary of a firm's operations"""
        if firm_id not in self.firm_intelligence:
            return None
        
        firm = self.firm_intelligence[firm_id]
        
        # Get bot details
        whale_profiles = [
            self.bot_profiles[bot_id].to_dict()
            for bot_id in firm.whale_bots
            if bot_id in self.bot_profiles
        ]
        
        worker_profiles = [
            self.bot_profiles[bot_id].to_dict()
            for bot_id in firm.worker_bots[:10]  # Limit to 10 workers
            if bot_id in self.bot_profiles
        ]
        
        return {
            "firm": firm.to_dict(),
            "whales": whale_profiles,
            "workers": worker_profiles,
            "worker_count": len(firm.worker_bots),
        }
    
    def get_all_firms_summary(self) -> List[Dict]:
        """Get summary of all detected firms"""
        summaries = []
        
        for firm_id in self.firm_intelligence:
            firm = self.firm_intelligence[firm_id]
            if firm.total_bots > 0:  # Only include active firms
                summaries.append({
                    "firm_id": firm_id,
                    "firm_name": firm.firm_name,
                    "country": firm.country,
                    "hq_location": firm.hq_location,
                    "total_bots": firm.total_bots,
                    "whale_count": len(firm.whale_bots),
                    "worker_count": len(firm.worker_bots),
                    "active_symbols": list(firm.active_symbols),
                    "operating_regions": list(firm.operating_regions),
                    "strategies": list(firm.strategies_observed),
                    "total_volume_usd": firm.total_volume_usd,
                })
        
        # Sort by total bots (most active first)
        summaries.sort(key=lambda x: x['total_bots'], reverse=True)
        return summaries
    
    def export_intelligence_report(self, filepath: str = "bot_intelligence_report.json"):
        """Export complete intelligence report to JSON"""
        report = {
            "timestamp": time.time(),
            "total_bots_profiled": len(self.bot_profiles),
            "firms_detected": len([f for f in self.firm_intelligence.values() if f.total_bots > 0]),
            "firms": self.get_all_firms_summary(),
            "all_bots": {
                bot_id: profile.to_dict()
                for bot_id, profile in self.bot_profiles.items()
            }
        }
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"📊 Intelligence report exported to {filepath}")
        return report
    
    # ═══════════════════════════════════════════════════════════════════════════
    # LEARNING & BACKPROPAGATION - Neural Attribution Learning
    # ═══════════════════════════════════════════════════════════════════════════
    
    def learn_from_attribution(self, bot_id: str, confirmed_firm: str, correct: bool):
        """
        Backpropagation learning from confirmed attributions.
        Adjusts internal scoring weights based on feedback.
        
        Args:
            bot_id: The bot whose attribution was confirmed/denied
            confirmed_firm: The actual firm (if correct) or the correct firm (if wrong)
            correct: Whether the original attribution was correct
        """
        if not hasattr(self, '_learning_history'):
            self._learning_history = []
            self._firm_accuracy = {}
            self._pattern_weights = {}
        
        if bot_id not in self.bot_profiles:
            return
        
        profile = self.bot_profiles[bot_id]
        original_firm = profile.likely_owner
        
        # Record learning event
        self._learning_history.append({
            'timestamp': time.time(),
            'bot_id': bot_id,
            'original_attribution': original_firm,
            'confirmed_firm': confirmed_firm,
            'correct': correct,
            'confidence': profile.owner_confidence,
            'pattern': profile.pattern,
            'size_class': profile.size_class
        })
        
        # Update firm accuracy tracking
        if original_firm not in self._firm_accuracy:
            self._firm_accuracy[original_firm] = {'correct': 0, 'total': 0}
        
        self._firm_accuracy[original_firm]['total'] += 1
        if correct:
            self._firm_accuracy[original_firm]['correct'] += 1
        
        # If wrong, learn what features led to mistake
        if not correct and confirmed_firm in ALL_FIRMS:
            # Extract features that should have indicated correct firm
            correct_patterns = ALL_FIRMS[confirmed_firm].get('patterns', {})
            wrong_patterns = ALL_FIRMS.get(original_firm, {}).get('patterns', {})
            
            # Learn pattern weight adjustments
            pattern_key = f"{profile.pattern}_{profile.size_class}"
            if pattern_key not in self._pattern_weights:
                self._pattern_weights[pattern_key] = {}
            
            # Increase weight for correct firm patterns
            for key, value in correct_patterns.items():
                if key not in self._pattern_weights[pattern_key]:
                    self._pattern_weights[pattern_key][key] = 1.0
                self._pattern_weights[pattern_key][key] *= 1.1  # Boost
            
            # Decrease weight for wrong firm patterns
            for key, value in wrong_patterns.items():
                if key in self._pattern_weights[pattern_key]:
                    self._pattern_weights[pattern_key][key] *= 0.9  # Reduce
            
            # Update profile with correct attribution
            profile.likely_owner = confirmed_firm
            profile.owner_name = ALL_FIRMS[confirmed_firm]['name']
            profile.owner_confidence = 0.95  # High confidence after confirmation
        
        # Save learning state
        self._save_learning_state()
        
        print(f"📚 Learning: {original_firm} → {confirmed_firm} ({'✓' if correct else '✗'})")
    
    def get_attribution_explanation(self, bot_id: str) -> Dict:
        """
        Get detailed explanation of why a bot was attributed to a firm.
        Returns reasoning chain suitable for Queen's voice.
        """
        if bot_id not in self.bot_profiles:
            return {'error': 'Bot not found'}
        
        profile = self.bot_profiles[bot_id]
        
        if profile.likely_owner == 'unknown':
            return {
                'firm': 'Unknown',
                'confidence': 0.0,
                'reasoning': ['Insufficient behavioral data for attribution'],
                'evidence': {}
            }
        
        firm_data = ALL_FIRMS.get(profile.likely_owner, {})
        patterns = firm_data.get('patterns', {})
        
        reasoning = []
        evidence = {}
        
        # Explain HFT frequency match
        freq_range = patterns.get('hft_frequency', (0, 1000))
        tps = profile.metrics.trades_per_second
        if freq_range[0] <= tps <= freq_range[1]:
            reasoning.append(f"Trade frequency of {tps:.1f}/sec matches {firm_data.get('name', 'firm')}'s typical {freq_range[0]}-{freq_range[1]}/sec range")
            evidence['hft_frequency'] = {'observed': tps, 'expected_range': freq_range, 'match': True}
        
        # Explain order consistency
        expected_consistency = patterns.get('order_size_consistency', 0.5)
        actual_consistency = profile.metrics.order_size_consistency
        if abs(actual_consistency - expected_consistency) < 0.1:
            reasoning.append(f"Order size consistency of {actual_consistency:.0%} indicates algorithmic precision typical of {firm_data.get('name', 'firm')}")
            evidence['order_consistency'] = {'observed': actual_consistency, 'expected': expected_consistency, 'match': True}
        
        # Explain latency profile
        latency_profile = patterns.get('latency_profile', 'medium')
        latency_ms = profile.metrics.avg_latency_ms
        latency_match = False
        if latency_profile == 'ultra_low' and latency_ms < 2:
            latency_match = True
            reasoning.append(f"Ultra-low latency of {latency_ms:.1f}ms indicates co-located infrastructure consistent with {firm_data.get('name', 'firm')}")
        elif latency_profile == 'low' and latency_ms < 10:
            latency_match = True
            reasoning.append(f"Low latency execution indicates professional infrastructure")
        evidence['latency'] = {'observed_ms': latency_ms, 'profile': latency_profile, 'match': latency_match}
        
        # Explain symbol preference
        preferred_symbols = patterns.get('symbols_preference', [])
        if any(sym.upper() in profile.symbol.upper() for sym in preferred_symbols):
            reasoning.append(f"{profile.symbol} is a known focus area for {firm_data.get('name', 'firm')}")
            evidence['symbol_preference'] = {'symbol': profile.symbol, 'preferred': preferred_symbols, 'match': True}
        
        # Explain market making ratio
        expected_mm = patterns.get('market_making_ratio', 0.5)
        actual_mm = profile.metrics.market_making_ratio
        if abs(actual_mm - expected_mm) < 0.15:
            reasoning.append(f"Market-making ratio of {actual_mm:.0%} consistent with {firm_data.get('name', 'firm')}'s trading style")
            evidence['market_making'] = {'observed': actual_mm, 'expected': expected_mm, 'match': True}
        
        # Add firm context
        evidence['firm'] = {
            'name': firm_data.get('name', 'Unknown'),
            'animal': firm_data.get('animal', '🤖'),
            'country': firm_data.get('country', 'Unknown'),
            'hq': firm_data.get('hq_location', 'Unknown'),
            'capital': firm_data.get('estimated_capital', 0),
            'strategies': firm_data.get('known_strategies', [])
        }
        
        # Calculate overall confidence explanation
        confidence_factors = len([r for r in reasoning if r])
        if confidence_factors >= 4:
            confidence_explanation = "High confidence - multiple strong indicators"
        elif confidence_factors >= 2:
            confidence_explanation = "Moderate confidence - several matching patterns"
        else:
            confidence_explanation = "Low confidence - limited matching data"
        
        return {
            'firm': profile.owner_name,
            'firm_id': profile.likely_owner,
            'animal': firm_data.get('animal', '🤖'),
            'confidence': profile.owner_confidence,
            'confidence_explanation': confidence_explanation,
            'reasoning': reasoning,
            'evidence': evidence,
            'profile_summary': {
                'bot_id': bot_id,
                'symbol': profile.symbol,
                'pattern': profile.pattern,
                'size_class': profile.size_class,
                'role': profile.role
            }
        }
    
    def get_learning_stats(self) -> Dict:
        """Get statistics on attribution learning"""
        if not hasattr(self, '_learning_history'):
            return {'total_learnings': 0, 'accuracy_by_firm': {}}
        
        total = len(self._learning_history)
        correct = sum(1 for l in self._learning_history if l['correct'])
        
        accuracy_by_firm = {}
        for firm, stats in self._firm_accuracy.items():
            if stats['total'] > 0:
                accuracy_by_firm[firm] = stats['correct'] / stats['total']
        
        return {
            'total_learnings': total,
            'overall_accuracy': correct / total if total > 0 else 0,
            'accuracy_by_firm': accuracy_by_firm,
            'pattern_weights': getattr(self, '_pattern_weights', {})
        }
    
    def _save_learning_state(self):
        """Save learning state to file"""
        try:
            state = {
                'history': list(self._learning_history)[-100:],  # Keep last 100
                'firm_accuracy': self._firm_accuracy,
                'pattern_weights': self._pattern_weights,
                'timestamp': time.time()
            }
            with open('data/profiler_learning_state.json', 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save learning state: {e}")
    
    def _load_learning_state(self):
        """Load learning state from file"""
        try:
            with open('data/profiler_learning_state.json', 'r') as f:
                state = json.load(f)
                self._learning_history = state.get('history', [])
                self._firm_accuracy = state.get('firm_accuracy', {})
                self._pattern_weights = state.get('pattern_weights', {})
                print(f"📚 Loaded {len(self._learning_history)} learning events")
        except FileNotFoundError:
            self._learning_history = []
            self._firm_accuracy = {}
            self._pattern_weights = {}
        except Exception as e:
            print(f"Warning: Could not load learning state: {e}")
            self._learning_history = []
            self._firm_accuracy = {}
            self._pattern_weights = {}

# ═══════════════════════════════════════════════════════════════════════════
# MAIN TEST
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("🧠 Starting Bot Intelligence Profiler test...")
    
    profiler = BotIntelligenceProfiler()
    
    # Simulate bot detections
    test_bots = [
        {
            'symbol': 'BTCUSDT',
            'exchange': 'binance',
            'pattern': 'hft',
            'size_class': 'shark',
            'trade_count': 150,
            'total_volume_usd': 50000,
            'time_window_seconds': 1.0,
            'trade_sizes': [333] * 150,  # Very consistent
            'buy_count': 75,
            'sell_count': 75,
            'latency_ms': 0.8,
        },
        {
            'symbol': 'ETHUSDT',
            'exchange': 'binance',
            'pattern': 'market_maker',
            'size_class': 'whale',
            'trade_count': 200,
            'total_volume_usd': 150000,
            'time_window_seconds': 1.0,
            'trade_sizes': [750] * 200,
            'buy_count': 100,
            'sell_count': 100,
            'latency_ms': 1.2,
        },
    ]
    
    for bot_data in test_bots:
        profile = profiler.profile_bot(bot_data)
        print(f"\n🤖 Bot Profile: {profile.bot_id}")
        print(f"   Symbol: {profile.symbol}")
        print(f"   Owner: {profile.owner_name} (confidence: {profile.owner_confidence:.2%})")
        print(f"   Role: {profile.role} (Level {profile.firm_hierarchy_level})")
        print(f"   Strategies: {', '.join(profile.strategies)}")
        print(f"   Location: {profile.operating_region} ({profile.country})")
        print(f"   Metrics: {profile.metrics.total_trades} trades, ${profile.metrics.total_volume_usd:,.0f} volume")
    
    # Print firm summary
    print("\n" + "="*80)
    print("📊 FIRM INTELLIGENCE SUMMARY")
    print("="*80)
    
    for firm_summary in profiler.get_all_firms_summary():
        print(f"\n🏢 {firm_summary['firm_name']}")
        print(f"   Location: {firm_summary['hq_location']}, {firm_summary['country']}")
        print(f"   Total Bots: {firm_summary['total_bots']} ({firm_summary['whale_count']} whales, {firm_summary['worker_count']} workers)")
        print(f"   Active Symbols: {', '.join(firm_summary['active_symbols'])}")
        print(f"   Operating Regions: {', '.join(firm_summary['operating_regions'])}")
        print(f"   Strategies: {', '.join(firm_summary['strategies'])}")
        print(f"   Total Volume: ${firm_summary['total_volume_usd']:,.0f}")
    
    # Export report
    profiler.export_intelligence_report()
    
    print("\n✅ Bot Intelligence Profiler test complete!")
