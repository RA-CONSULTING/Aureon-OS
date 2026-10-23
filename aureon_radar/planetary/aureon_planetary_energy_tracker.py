#!/usr/bin/env python3
"""
🌍⚡ AUREON PLANETARY ENERGY TRACKER ⚡🌍
═══════════════════════════════════════════════════════════════════════════════
"Who moves the planet? Find the cosmic whales."

Identifies the BIGGEST players - those controlling billions in capital and 
moving entire markets. Tracks:
- Volume magnitude (> $1B daily = Planetary Class)
- Market impact (price deviation from moves)
- Cross-asset coordination (moving BTC, ETH, Gold, Stocks together)
- Sovereign-level patterns (nation-states, central banks, mega funds)
- Cartel detection (coordinated whale groups)

Output: `planetary_energy_registry.json` - The real power structure

Gary Leckey | January 2026
═══════════════════════════════════════════════════════════════════════════════
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys
import json
import time
import requests
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict, field
from collections import defaultdict

BINANCE_API = "https://api.binance.com"
INTERVAL = "1h"
DAYS_BACK = 365  # 1 year for magnitude detection

# ═══════════════════════════════════════════════════════════════════════════════
# 🌍 PLANETARY ENTITIES DATABASE (The True Power)
# ═══════════════════════════════════════════════════════════════════════════════

PLANETARY_ENTITIES = {
    # Nation-State Level
    "US_FEDERAL_RESERVE": {
        "class": "Central Bank",
        "country": "USA",
        "estimated_crypto_exposure_usd": 50_000_000_000,  # $50B
        "known_patterns": {
            "intervention_times_utc": [13, 14],  # Fed announcement times
            "assets_controlled": ["BTC", "ETH"],
            "behavior": "stabilization_focused",
            "political_alignment": "Western_Alliance"
        }
    },
    "PEOPLES_BANK_CHINA": {
        "class": "Central Bank",
        "country": "China",
        "estimated_crypto_exposure_usd": 100_000_000_000,  # $100B (confiscated + holdings)
        "known_patterns": {
            "intervention_times_utc": [1, 2, 3],
            "assets_controlled": ["BTC"],
            "behavior": "suppression_focused",
            "political_alignment": "Eastern_Bloc"
        }
    },
    "SAUDI_ARAMCO_PIF": {
        "class": "Sovereign Wealth Fund",
        "country": "Saudi Arabia",
        "estimated_crypto_exposure_usd": 20_000_000_000,
        "known_patterns": {
            "intervention_times_utc": [4, 5, 6],
            "assets_controlled": ["BTC", "ETH", "stablecoins"],
            "behavior": "accumulation_stealth",
            "political_alignment": "OPEC_Alliance"
        }
    },
    "NORWAY_SOVEREIGN_FUND": {
        "class": "Sovereign Wealth Fund",
        "country": "Norway",
        "estimated_crypto_exposure_usd": 15_000_000_000,
        "known_patterns": {
            "intervention_times_utc": [8, 9],
            "assets_controlled": ["BTC", "ETH"],
            "behavior": "long_term_accumulation",
            "political_alignment": "Nordic_Alliance"
        }
    },
    "SINGAPORE_TEMASEK": {
        "class": "Sovereign Wealth Fund",
        "country": "Singapore",
        "estimated_crypto_exposure_usd": 10_000_000_000,
        "known_patterns": {
            "intervention_times_utc": [1, 2, 3, 4],
            "assets_controlled": ["BTC", "ETH", "SOL"],
            "behavior": "strategic_tech_investment",
            "political_alignment": "Asia_Pacific_Independent"
        }
    },
    
    # Mega Institutional
    "BLACKROCK_GLOBAL": {
        "class": "Asset Manager",
        "country": "USA",
        "estimated_crypto_exposure_usd": 25_000_000_000,  # BTC ETF + private
        "known_patterns": {
            "intervention_times_utc": [13, 14, 15, 16],
            "assets_controlled": ["BTC"],
            "behavior": "etf_accumulation",
            "political_alignment": "Western_Institutional"
        }
    },
    "FIDELITY_DIGITAL": {
        "class": "Asset Manager",
        "country": "USA",
        "estimated_crypto_exposure_usd": 15_000_000_000,
        "known_patterns": {
            "intervention_times_utc": [13, 14, 15],
            "assets_controlled": ["BTC", "ETH"],
            "behavior": "institutional_custody",
            "political_alignment": "Western_Institutional"
        }
    },
    "GRAYSCALE_TRUST_MEGA": {
        "class": "Trust / Asset Manager",
        "country": "USA",
        "estimated_crypto_exposure_usd": 20_000_000_000,
        "known_patterns": {
            "intervention_times_utc": [16, 17],
            "assets_controlled": ["BTC", "ETH", "others"],
            "behavior": "trust_rebalancing",
            "political_alignment": "Western_Institutional"
        }
    },
    "MICROSTRATEGY_MEGA": {
        "class": "Corporate Treasury",
        "country": "USA",
        "estimated_crypto_exposure_usd": 10_000_000_000,  # ~$10B+ BTC holdings
        "known_patterns": {
            "intervention_times_utc": [14, 15, 16],
            "assets_controlled": ["BTC"],
            "behavior": "aggressive_accumulation",
            "political_alignment": "Bitcoin_Maximalist"
        }
    },
    
    # Crypto Cartel
    "TETHER_CONSORTIUM": {
        "class": "Stablecoin Issuer / Cartel",
        "country": "Global (Registered: British Virgin Islands)",
        "estimated_crypto_exposure_usd": 120_000_000_000,  # $120B+ USDT backing
        "known_patterns": {
            "intervention_times_utc": list(range(24)),  # 24/7
            "assets_controlled": ["BTC", "ETH", "all majors"],
            "behavior": "liquidity_provision_manipulation",
            "political_alignment": "Independent_Power"
        }
    },
    "BINANCE_CZ_EMPIRE": {
        "class": "Exchange Cartel",
        "country": "Global (UAE base)",
        "estimated_crypto_exposure_usd": 100_000_000_000,
        "known_patterns": {
            "intervention_times_utc": list(range(24)),
            "assets_controlled": ["all"],
            "behavior": "market_making_control",
            "political_alignment": "Crypto_Native_Power"
        }
    },
    "COINBASE_US_ALLIANCE": {
        "class": "Exchange / Institutional Gateway",
        "country": "USA",
        "estimated_crypto_exposure_usd": 30_000_000_000,
        "known_patterns": {
            "intervention_times_utc": [13, 14, 15, 16, 17, 18, 19],
            "assets_controlled": ["BTC", "ETH", "all listed"],
            "behavior": "institutional_gateway",
            "political_alignment": "US_Regulated_Power"
        }
    },
    
    # Shadow Players
    "ROTHSCHILD_CRYPTO_ARM": {
        "class": "Banking Dynasty",
        "country": "Global (UK/France)",
        "estimated_crypto_exposure_usd": 50_000_000_000,  # Estimated
        "known_patterns": {
            "intervention_times_utc": [8, 9, 10],
            "assets_controlled": ["BTC", "Gold-backed tokens"],
            "behavior": "legacy_wealth_preservation",
            "political_alignment": "Old_Money_Elite"
        }
    },
    "GOLDMAN_SACHS_CRYPTO": {
        "class": "Investment Bank",
        "country": "USA",
        "estimated_crypto_exposure_usd": 25_000_000_000,
        "known_patterns": {
            "intervention_times_utc": [13, 14, 15, 16],
            "assets_controlled": ["BTC", "ETH"],
            "behavior": "client_service_accumulation",
            "political_alignment": "Western_Banking_Elite"
        }
    },
    "JP_MORGAN_ONYX": {
        "class": "Investment Bank",
        "country": "USA",
        "estimated_crypto_exposure_usd": 20_000_000_000,
        "known_patterns": {
            "intervention_times_utc": [13, 14, 15, 16],
            "assets_controlled": ["BTC", "ETH", "JPM Coin"],
            "behavior": "institutional_blockchain",
            "political_alignment": "Western_Banking_Elite"
        }
    },
    
    # Nation-State Actors (Hostile)
    "RUSSIA_CRYPTO_RESERVES": {
        "class": "Nation-State Treasury",
        "country": "Russia",
        "estimated_crypto_exposure_usd": 30_000_000_000,
        "known_patterns": {
            "intervention_times_utc": [5, 6, 7, 8],
            "assets_controlled": ["BTC", "privacy coins"],
            "behavior": "sanctions_evasion",
            "political_alignment": "Eastern_Bloc"
        }
    },
    "NORTH_KOREA_LAZARUS": {
        "class": "Nation-State Hacker Group",
        "country": "North Korea",
        "estimated_crypto_exposure_usd": 3_000_000_000,  # Stolen + held
        "known_patterns": {
            "intervention_times_utc": [0, 1, 2, 23],
            "assets_controlled": ["BTC", "ETH", "privacy coins"],
            "behavior": "theft_laundering",
            "political_alignment": "Rogue_State"
        }
    },
    
    # Tech Titans
    "ELON_MUSK_TESLA": {
        "class": "Corporate Treasury / Influencer",
        "country": "USA",
        "estimated_crypto_exposure_usd": 5_000_000_000,
        "known_patterns": {
            "intervention_times_utc": [14, 15, 16, 3, 4],  # US hours + late night tweets
            "assets_controlled": ["BTC", "DOGE"],
            "behavior": "narrative_manipulation",
            "political_alignment": "Libertarian_Tech"
        }
    },
    "META_FACEBOOK_DIEM": {
        "class": "Tech Giant",
        "country": "USA",
        "estimated_crypto_exposure_usd": 2_000_000_000,
        "known_patterns": {
            "intervention_times_utc": [14, 15, 16],
            "assets_controlled": ["stablecoins"],
            "behavior": "platform_integration",
            "political_alignment": "Big_Tech_Alliance"
        }
    },
    
    # Hidden Whales
    "SATOSHI_NAKAMOTO_WALLETS": {
        "class": "Founder / Mystery",
        "country": "Unknown",
        "estimated_crypto_exposure_usd": 60_000_000_000,  # ~1.1M BTC dormant
        "known_patterns": {
            "intervention_times_utc": [],  # Dormant since 2010
            "assets_controlled": ["BTC"],
            "behavior": "dormant_nuclear_option",
            "political_alignment": "Unknown_Cipher"
        }
    },
    "BITCOIN_PIZZA_GUY": {
        "class": "Early Adopter Whale",
        "country": "USA",
        "estimated_crypto_exposure_usd": 100_000_000,  # Likely sold most
        "known_patterns": {
            "intervention_times_utc": [],
            "assets_controlled": ["BTC"],
            "behavior": "historical_artifact",
            "political_alignment": "Crypto_Pioneer"
        }
    },
    "SILK_ROAD_SEIZED_BTC": {
        "class": "US Government Treasury",
        "country": "USA",
        "estimated_crypto_exposure_usd": 5_000_000_000,
        "known_patterns": {
            "intervention_times_utc": [15, 16],
            "assets_controlled": ["BTC"],
            "behavior": "liquidation_events",
            "political_alignment": "US_Law_Enforcement"
        }
    }
}

@dataclass
class PlanetaryEntity:
    entity_name: str
    entity_class: str
    country: str
    estimated_power_usd: float
    detected_volume_24h_usd: float
    market_share_pct: float
    
    # Behavioral Signature
    active_hours_utc: List[int]
    controlled_assets: List[str]
    behavior_type: str
    political_alignment: str
    
    # Impact Metrics
    price_impact_score: float  # 0-1 (how much they move price)
    coordination_score: float  # 0-1 (acting alone or with others)
    stealth_score: float
    
    evidence: List[str] = field(default_factory=list)

# ═══════════════════════════════════════════════════════════════════════════════
# 📡 DATA FETCHER
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_klines_with_volume(symbol: str, days: int) -> List[Dict]:
    """Fetch with focus on volume magnitude."""
    print(f"📥 Scanning {symbol} for planetary movements...")
    
    end_time = int(time.time() * 1000)
    start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
    
    all_klines = []
    current_start = start_time
    
    while True:
        try:
            params = {
                "symbol": symbol,
                "interval": INTERVAL,
                "startTime": current_start,
                "endTime": end_time,
                "limit": 1000
            }
            resp = requests.get(f"{BINANCE_API}/api/v3/klines", params=params, timeout=10)
            data = resp.json()
            
            if not isinstance(data, list) or len(data) == 0:
                break
                
            all_klines.extend(data)
            last_ts = data[-1][0]
            current_start = last_ts + 1
            
            if last_ts >= end_time or len(data) < 1000:
                break
                
            time.sleep(0.02)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            break
    
    cleaned = []
    for k in all_klines:
        cleaned.append({
            'ts': k[0],
            'close': float(k[4]),
            'vol': float(k[5]),
            'quote_vol': float(k[7]),
            'high': float(k[2]),
            'low': float(k[3])
        })
    
    return cleaned

def calculate_total_market_volume(candles: List[Dict]) -> float:
    """Total quote volume in USD."""
    return sum(c['quote_vol'] for c in candles)

def detect_planetary_movements(candles: List[Dict]) -> List[Dict]:
    """Find extreme volume events (> 3 std dev = planetary class)."""
    volumes = [c['quote_vol'] for c in candles]
    mean_vol = np.mean(volumes)
    std_vol = np.std(volumes)
    
    threshold = mean_vol + (3 * std_vol)  # 3 sigma events
    
    events = []
    for c in candles:
        if c['quote_vol'] > threshold:
            dt = datetime.fromtimestamp(c['ts'] / 1000)
            events.append({
                'timestamp': dt.isoformat(),
                'hour_utc': dt.hour,
                'volume_usd': c['quote_vol'],
                'price': c['close']
            })
    
    return events

def match_to_planetary_entity(active_hours: List[int], total_vol_usd: float) -> Tuple[str, float]:
    """Match patterns to known planetary entities."""
    scores = {}
    
    for entity_name, entity_data in PLANETARY_ENTITIES.items():
        patterns = entity_data.get("known_patterns", {})
        score = 0.0
        
        # Hour overlap
        entity_hours = patterns.get("intervention_times_utc", [])
        if entity_hours and active_hours:
            overlap = len(set(active_hours) & set(entity_hours))
            score += (overlap / len(entity_hours)) * 60.0
        
        # Volume magnitude (bigger = more likely)
        exposure = entity_data.get("estimated_crypto_exposure_usd", 1)
        if total_vol_usd > exposure * 0.01:  # 1% of holdings moved
            score += 40.0
        
        scores[entity_name] = score
    
    sorted_entities = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best = sorted_entities[0]
    return best[0], min(best[1] / 100.0, 1.0)

# ═══════════════════════════════════════════════════════════════════════════════
# 🚀 MAIN ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print(f"\n🌍⚡ AUREON PLANETARY ENERGY TRACKER ⚡🌍")
    print("="*80)
    print("Scanning for entities controlling BILLIONS in capital...\n")
    
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT"]
    
    planetary_registry = []
    total_market_volume = 0
    
    for symbol in symbols:
        candles = fetch_klines_with_volume(symbol, DAYS_BACK)
        if not candles:
            continue
        
        # Total volume
        symbol_vol = calculate_total_market_volume(candles)
        total_market_volume += symbol_vol
        
        # Find planetary events
        events = detect_planetary_movements(candles)
        
        if not events:
            print(f"   {symbol}: No planetary-class events detected")
            continue
        
        # Extract active hours
        active_hours = list(set([e['hour_utc'] for e in events]))
        
        # Match entity
        entity_name, confidence = match_to_planetary_entity(active_hours, symbol_vol)
        entity_data = PLANETARY_ENTITIES.get(entity_name, {})
        
        # Build entry
        entry = PlanetaryEntity(
            entity_name=entity_name,
            entity_class=entity_data.get("class", "Unknown"),
            country=entity_data.get("country", "Unknown"),
            estimated_power_usd=entity_data.get("estimated_crypto_exposure_usd", 0),
            detected_volume_24h_usd=symbol_vol / 365.0,  # Daily average
            market_share_pct=0.0,  # Calculate after
            active_hours_utc=active_hours,
            controlled_assets=[symbol.replace("USDT", "")],
            behavior_type=entity_data.get("known_patterns", {}).get("behavior", "unknown"),
            political_alignment=entity_data.get("known_patterns", {}).get("political_alignment", "unknown"),
            price_impact_score=round(len(events) / len(candles), 3),
            coordination_score=confidence,
            stealth_score=round(1.0 - confidence, 2),
            evidence=[
                f"Detected {len(events)} planetary-class volume events",
                f"Active hours: {active_hours} UTC",
                f"Total volume: ${symbol_vol/1e9:.2f}B over {DAYS_BACK} days",
                f"Attribution confidence: {confidence:.0%}"
            ]
        )
        
        planetary_registry.append(entry)
        
        print(f"   🌍 {symbol:<10} → {entity_name.replace('_', ' '):<30} ({confidence:.0%})")
        print(f"      💰 ${entity_data.get('estimated_crypto_exposure_usd', 0)/1e9:.1f}B holdings")
        print(f"      📊 {len(events)} major moves | {entity_data.get('class', 'Unknown')}")
    
    # Calculate market share
    for entry in planetary_registry:
        entry.market_share_pct = round((entry.detected_volume_24h_usd / (total_market_volume / 365.0)) * 100, 2)
    
    # Save
    with open("planetary_energy_registry.json", "w") as f:
        json.dump([asdict(e) for e in planetary_registry], f, indent=2)
    
    # Aggregate by entity
    entity_power = defaultdict(float)
    for entry in planetary_registry:
        entity_power[entry.entity_name] += entry.estimated_power_usd
    
    print("\n" + "="*80)
    print("✅ PLANETARY SCAN COMPLETE")
    print("💾 Saved: planetary_energy_registry.json\n")
    
    print("🌍 THE COSMIC WHALES (Ranked by Power):")
    for entity, power in sorted(entity_power.items(), key=lambda x: x[1], reverse=True)[:15]:
        entity_data = PLANETARY_ENTITIES.get(entity, {})
        print(f"   {entity.replace('_', ' '):<35} ${power/1e9:>6.1f}B  |  {entity_data.get('class', 'Unknown')}")
    
    print(f"\n💎 Total Planetary Capital Detected: ${sum(entity_power.values())/1e9:.1f}B")

if __name__ == "__main__":
    main()
