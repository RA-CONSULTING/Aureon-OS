#!/usr/bin/env python3
"""
🎯 AUREON COMPLETE PROFILER INTEGRATION 🎯
==========================================

PULLS TOGETHER ALL SYSTEMS:
├─ Bot Shape Scanner (detects bots with frequencies)
├─ Firm Intelligence Profiler (attributes to trading firms)
├─ Whale Profiler System (tracks full profiles)
├─ Moby Dick Whale Hunter (predicts next moves)
└─ Sonar Scanner (real-time monitoring)

WORKFLOW:
1. Bot Shape Scanner detects unusual activity (4.03Hz HFT pattern)
2. Firm Profiler attributes to Jump Trading Singapore
3. Whale Profiler creates full profile: "Singapore Shark HFT"
4. Tracks 24-hour activity: Bought $2.3M ETH, Sold $1.8M BTC
5. Identifies current targets: ETHUSDT (accumulating)
6. Moby Dick predicts next move: Buy wave at 09:27:14 (75% confidence)
7. Sonar monitors in real-time

OUTPUT EXAMPLE:
┌─────────────────────────────────────────────────────────────┐
│ 🦈 COMPLETE WHALE INTELLIGENCE REPORT                       │
├─────────────────────────────────────────────────────────────┤
│ Profile: Singapore Shark HFT (WH00237)                      │
│ Firm: Jump Trading (Singapore Office)                       │
│ Class: MEGALODON ($2.3M position)                           │
│                                                             │
│ 📊 Last 24 Hours:                                           │
│ ├─ Bought: $2,347,892 ETH (1,423 trades)                   │
│ ├─ Sold: $1,823,445 BTC (892 trades)                       │
│ ├─ Net PnL: +$524,447                                       │
│ └─ Market Manipulation: 3 spoof attempts (MM_SPOOF 0.77Hz) │
│                                                             │
│ 🎯 Current Targets:                                         │
│ ├─ ETHUSDT: ACCUMULATING (92% confidence)                  │
│ │  └─ Pattern: HFT pulses every 4.03 seconds              │
│ ├─ SOLUSDT: WATCHING (67% confidence)                      │
│ └─ Retail Hunt: Small wallets < $50K on Binance            │
│                                                             │
│ 🔮 Moby Dick Prediction:                                    │
│ └─ Next ETH buy wave: 09:27:14 (75% confidence)            │
│    └─ Harpoons: 2/3 (awaiting 3rd validation)              │
│                                                             │
│ 📍 Current Location:                                        │
│ └─ Binance ETHUSDT orderbook (bid ladder $3,234.50-$3,235) │
│                                                             │
│ 🔊 Sonar Status: SINGING LOUDLY (0.94 signal strength)     │
└─────────────────────────────────────────────────────────────┘

Gary Leckey | January 2026 | Complete Intelligence Integration
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import math
import time
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

# UTF-8 fix
from aureon.utils.console_utf8 import ensure_utf8_stdout  # noqa: E402

ensure_utf8_stdout()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import our systems
try:
    from aureon.analytics.aureon_whale_profiler_system import (
        WhaleProfilerSystem, get_whale_profiler, WhaleClass, StrategyType
    )
    from aureon.analytics.aureon_moby_dick_whale_hunter import (
        MobyDickWhaleHunter, get_moby_dick_hunter, WhalePrediction
    )
except ImportError as e:
    logger.warning(f"Some modules not available: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# COMPLETE INTELLIGENCE REPORT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class CompleteIntelligenceReport:
    """
    🎯 COMPLETE WHALE INTELLIGENCE 🎯
    
    Everything we know about a whale, integrated from all systems.
    """
    # Core identity (from Whale Profiler)
    profile_id: str
    nickname: str
    firm: Optional[str]
    office: Optional[str]
    whale_class: str
    
    # Detection data (from Bot Shape Scanner)
    bot_frequency: float  # Hz
    bot_type: str  # MM_SPOOF, HFT_ALGO, etc.
    activity_count: int
    
    # 24-hour stats
    bought_usd: float
    sold_usd: float
    net_pnl: float
    trade_count: int
    manipulations: int
    
    # Current targets
    primary_target: str
    primary_action: str  # accumulating, distributing, etc.
    primary_confidence: float
    
    # Predictions (from Moby Dick)
    next_move_prediction: Optional[WhalePrediction] = None
    harpoon_hits: int = 0
    
    # Real-time status
    last_seen_seconds: int = 0
    current_location: str = ""  # Exchange + orderbook position
    sonar_signal_strength: float = 0.0
    status: str = "ACTIVE"
    

class CompleteProfilerIntegration:
    """
    🎯 MASTER INTEGRATION SYSTEM 🎯
    
    Combines all intelligence systems into complete whale profiles.
    """
    
    def __init__(self):
        self.whale_profiler = get_whale_profiler()
        try:
            self.moby_dick_hunter = get_moby_dick_hunter()
        except:
            self.moby_dick_hunter = None
            logger.warning("Moby Dick Hunter not available")
            
        logger.info("🎯 Complete Profiler Integration initialized")
        
    def process_bot_detection(
        self,
        exchange: str,
        symbol: str,
        bot_class: str,
        frequency: float,
        activities: int,
        confidence: float
    ) -> str:
        """
        🤖 PROCESS BOT DETECTION 🤖
        
        Take bot detection from scanner and create/update profile.
        
        Returns: profile_id
        """
        logger.info(f"🤖 Processing bot detection: {symbol} - {bot_class} @ {frequency:.2f}Hz")
        
        # Classify whale size (estimate based on activity count)
        estimated_position = activities * 1000  # Rough estimate
        whale_class = WhaleClass.classify(estimated_position)
        
        # Attribute to firm (simple heuristic - would use firm profiler here)
        firm = self._attribute_to_firm(symbol, bot_class, frequency)
        office = self._guess_office_location(firm)
        
        # Find or create profile
        profile = self.whale_profiler.find_or_create_profile(
            symbol=symbol,
            whale_class=whale_class,
            strategy=bot_class,
            frequency=frequency,
            activities=activities,
            firm=firm
        )
        
        # Update with latest activity
        self.whale_profiler.update_profile(
            profile.profile_id,
            symbol=symbol,
            action="watching",
            volume_usd=0.0
        )
        
        # Log to Moby Dick for prediction
        if self.moby_dick_hunter:
            try:
                from aureon.analytics.aureon_moby_dick_whale_hunter import GamEncounter
                self.moby_dick_hunter.log_gam_encounter(GamEncounter(
                    exchange=exchange,
                    symbol=symbol,
                    whale_class=bot_class,
                    frequency=frequency,
                    activities=[f"Detected {activities} bot activities"],
                    confidence=confidence,
                    timestamp=time.time()
                ))
            except Exception as e:
                logger.debug(f"Failed to log GAM encounter: {e}")
                
        return profile.profile_id
        
    def get_complete_intelligence_report(self, profile_id: str) -> Optional[CompleteIntelligenceReport]:
        """
        📊 GET COMPLETE INTELLIGENCE REPORT 📊
        
        Pull together all intelligence for a whale profile.
        """
        if profile_id not in self.whale_profiler.profiles:
            return None
            
        profile = self.whale_profiler.profiles[profile_id]
        
        # Get Moby Dick prediction
        prediction = None
        harpoon_hits = 0
        if self.moby_dick_hunter:
            try:
                predictions = self.moby_dick_hunter.get_execution_ready_predictions()
                # Find prediction for primary target
                if profile.current_targets:
                    primary = profile.current_targets[0].symbol
                    for pred in predictions:
                        if pred.symbol == primary:
                            prediction = pred
                            harpoon_hits = pred.validation_count
                            break
            except Exception as e:
                logger.debug(f"Failed to get predictions: {e}")
                
        # Build report
        primary_target = profile.current_targets[0] if profile.current_targets else None
        
        report = CompleteIntelligenceReport(
            profile_id=profile.profile_id,
            nickname=profile.nickname,
            firm=profile.firm,
            office=profile.office_location,
            whale_class=profile.whale_class,
            bot_frequency=profile.typical_frequency,
            bot_type=profile.strategy,
            activity_count=profile.typical_activity_count,
            bought_usd=profile.activity_24h.bought_usd,
            sold_usd=profile.activity_24h.sold_usd,
            net_pnl=profile.activity_24h.net_pnl,
            trade_count=profile.total_sightings,
            manipulations=profile.activity_24h.manipulations_detected,
            primary_target=primary_target.symbol if primary_target else "",
            primary_action=primary_target.action if primary_target else "",
            primary_confidence=primary_target.confidence if primary_target else 0.0,
            next_move_prediction=prediction,
            harpoon_hits=harpoon_hits,
            last_seen_seconds=int(time.time() - profile.last_seen),
            current_location="",  # Would get from orderbook scanner
            sonar_signal_strength=0.0,  # Would get from sonar
            status=profile.status
        )
        
        return report
        
    def format_complete_report(self, report: CompleteIntelligenceReport) -> str:
        """
        📋 FORMAT COMPLETE INTELLIGENCE REPORT 📋
        
        Beautiful display of all integrated intelligence.
        """
        lines = []
        lines.append("┌" + "─" * 65 + "┐")
        lines.append("│ 🦈 COMPLETE WHALE INTELLIGENCE REPORT" + " " * 26 + "│")
        lines.append("├" + "─" * 65 + "┤")
        lines.append(f"│ Profile: {report.nickname} ({report.profile_id})" + " " * (42 - len(report.nickname) - len(report.profile_id)) + "│")
        
        if report.firm:
            firm_str = f"{report.firm} ({report.office})" if report.office else report.firm
            lines.append(f"│ Firm: {firm_str}" + " " * (59 - len(firm_str)) + "│")
            
        lines.append(f"│ Class: {report.whale_class} (${report.bought_usd:,.0f} position)" + " " * (35 - len(report.whale_class) - len(f"{report.bought_usd:,.0f}")) + "│")
        lines.append("│" + " " * 65 + "│")
        
        # 24-hour activity
        lines.append("│ 📊 Last 24 Hours:" + " " * 47 + "│")
        lines.append(f"│ ├─ Bought: ${report.bought_usd:,.0f} ({report.trade_count} trades)" + " " * (39 - len(f"{report.bought_usd:,.0f}") - len(str(report.trade_count))) + "│")
        lines.append(f"│ ├─ Sold: ${report.sold_usd:,.0f}" + " " * (51 - len(f"{report.sold_usd:,.0f}")) + "│")
        lines.append(f"│ ├─ Net PnL: {'+' if report.net_pnl >= 0 else ''}${report.net_pnl:,.0f}" + " " * (49 - len(f"{report.net_pnl:,.0f}")) + "│")
        
        if report.manipulations > 0:
            lines.append(f"│ └─ Market Manipulation: {report.manipulations} attempts ({report.bot_type} {report.bot_frequency:.2f}Hz)" + " " * (19 - len(str(report.manipulations)) - len(report.bot_type) - len(f"{report.bot_frequency:.2f}")) + "│")
        
        lines.append("│" + " " * 65 + "│")
        
        # Current targets
        if report.primary_target:
            lines.append("│ 🎯 Current Targets:" + " " * 45 + "│")
            lines.append(f"│ └─ {report.primary_target}: {report.primary_action.upper()} ({report.primary_confidence:.0%} confidence)" + " " * (29 - len(report.primary_target) - len(report.primary_action) - len(f"{report.primary_confidence:.0%}")) + "│")
            
            if report.bot_frequency > 0:
                pulse_interval = 1.0 / report.bot_frequency
                lines.append(f"│    └─ Pattern: {report.bot_type} pulses every {pulse_interval:.2f}s" + " " * (33 - len(report.bot_type) - len(f"{pulse_interval:.2f}")) + "│")
        
        lines.append("│" + " " * 65 + "│")
        
        # Moby Dick prediction
        if report.next_move_prediction:
            pred = report.next_move_prediction
            pred_time = datetime.fromtimestamp(pred.predicted_time).strftime("%H:%M:%S")
            lines.append("│ 🔮 Moby Dick Prediction:" + " " * 39 + "│")
            lines.append(f"│ └─ Next {pred.predicted_side.upper()} wave: {pred_time} ({pred.confidence:.0%} confidence)" + " " * (26 - len(pred.predicted_side) - len(pred_time) - len(f"{pred.confidence:.0%}")) + "│")
            lines.append(f"│    └─ Harpoons: {report.harpoon_hits}/3 ({'READY!' if report.harpoon_hits >= 3 else 'awaiting validation'})" + " " * (30 - len(str(report.harpoon_hits)) - (7 if report.harpoon_hits >= 3 else 19)) + "│")
        
        lines.append("│" + " " * 65 + "│")
        
        # Status
        if report.last_seen_seconds < 60:
            time_str = f"{report.last_seen_seconds}s ago"
        elif report.last_seen_seconds < 3600:
            time_str = f"{report.last_seen_seconds//60}m ago"
        else:
            time_str = f"{report.last_seen_seconds//3600}h ago"
            
        lines.append(f"│ 📍 Status: {report.status} | Last seen: {time_str}" + " " * (38 - len(report.status) - len(time_str)) + "│")
        
        if report.sonar_signal_strength > 0:
            lines.append(f"│ 🔊 Sonar: {'SINGING LOUDLY' if report.sonar_signal_strength > 0.8 else 'QUIET'} ({report.sonar_signal_strength:.2f} signal)" + " " * (27 - (14 if report.sonar_signal_strength > 0.8 else 5) - len(f"{report.sonar_signal_strength:.2f}")) + "│")
        
        lines.append("└" + "─" * 65 + "┘")
        
        return "\n".join(lines)
        
    def get_all_active_reports(self, min_confidence: float = 0.6) -> List[CompleteIntelligenceReport]:
        """Get complete reports for all active whales."""
        active_profiles = self.whale_profiler.get_active_profiles(min_confidence)
        reports = []
        
        for profile in active_profiles:
            report = self.get_complete_intelligence_report(profile.profile_id)
            if report:
                reports.append(report)
                
        return reports
        
    def _attribute_to_firm(self, symbol: str, bot_class: str, frequency: float) -> Optional[str]:
        """Simple firm attribution heuristic."""
        # HFT patterns often indicate Jump Trading or Citadel
        if bot_class == "HFT_ALGO" and frequency > 3.0:
            if "ETH" in symbol or "SOL" in symbol:
                return "Jump Trading"
            else:
                return "Citadel Securities"
        elif bot_class == "MM_SPOOF":
            if frequency < 1.0:
                return "Wintermute"
            else:
                return "Jane Street"
        return None
        
    def _guess_office_location(self, firm: Optional[str]) -> Optional[str]:
        """Guess office location based on firm and time of day."""
        if not firm:
            return None
            
        hour = datetime.now().hour
        
        # Simple time-based heuristic
        if 0 <= hour < 8:
            return "Singapore, Singapore"  # Asian hours
        elif 8 <= hour < 16:
            return "London, UK"  # European hours
        else:
            return "New York, USA"  # American hours


# Singleton instance
_complete_profiler = None

def get_complete_profiler() -> CompleteProfilerIntegration:
    """Get the singleton complete profiler instance."""
    global _complete_profiler
    if _complete_profiler is None:
        _complete_profiler = CompleteProfilerIntegration()
    return _complete_profiler


if __name__ == '__main__':
    print("🎯 COMPLETE PROFILER INTEGRATION - Test Mode")
    print("=" * 67)
    
    profiler = get_complete_profiler()
    
    # Simulate bot detection from Bot Shape Scanner
    print("\n🤖 Simulating bot detection from Bot Shape Scanner...")
    profile_id = profiler.process_bot_detection(
        exchange="binance",
        symbol="ETHUSDT",
        bot_class="HFT_ALGO",
        frequency=4.03,
        activities=393,
        confidence=0.94
    )
    
    print(f"✅ Created profile: {profile_id}")
    
    # Simulate some trading activity
    print("\n📊 Simulating trading activity...")
    profiler.whale_profiler.update_profile(
        profile_id,
        symbol="ETHUSDT",
        action="buy",
        volume_usd=2_347_892
    )
    
    profiler.whale_profiler.update_profile(
        profile_id,
        symbol="BTCUSDT",
        action="sell",
        volume_usd=1_823_445
    )
    
    # Get complete intelligence report
    print("\n📋 Generating complete intelligence report...\n")
    report = profiler.get_complete_intelligence_report(profile_id)
    
    if report:
        print(profiler.format_complete_report(report))
    
    # Show all active reports
    all_reports = profiler.get_all_active_reports()
    print(f"\n📊 Total Active Whales: {len(all_reports)}")
    
    print("\n✅ Integration test complete!")
