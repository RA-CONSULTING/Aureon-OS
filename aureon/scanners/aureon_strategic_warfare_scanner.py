#!/usr/bin/env python3
"""
🎖️⚡ AUREON STRATEGIC WARFARE SCANNER ⚡🎖️
========================================
Intelligence gathering system combining:
- Sun Tzu's Art of War principles
- IRA guerrilla tactics  
- Apache warfare patience
- Modern SIGINT analysis

"Know your enemy and know yourself; in a hundred battles, you will never be defeated."
- Sun Tzu

"Move quietly, strike precisely, disappear before they realize what happened."
- IRA Doctrine

MISSION: Identify hidden power structures, coordination networks, and strategic vulnerabilities
in global financial markets using warfare intelligence methodologies.
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

import json
import numpy as np
import requests
import time
import math
import logging
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Optional, Tuple, Set
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
from collections import defaultdict

# 🚌 Communication Buses
try:
    from aureon.core.aureon_thought_bus import ThoughtBus, Thought
    THOUGHT_BUS_AVAILABLE = True
except ImportError:
    THOUGHT_BUS_AVAILABLE = False
    ThoughtBus = None

try:
    from aureon.core.aureon_chirp_bus import ChirpBus
    CHIRP_BUS_AVAILABLE = True
except ImportError:
    CHIRP_BUS_AVAILABLE = False
    ChirpBus = None

# Sacred Constants
PHI = (1 + math.sqrt(5)) / 2

@dataclass
class IntelligenceReport:
    """SIGINT/HUMINT intelligence report on market entity."""
    entity_name: str
    entity_type: str
    threat_level: str  # CRITICAL, HIGH, MEDIUM, LOW
    
    # Sun Tzu Analysis
    strength_assessment: float  # 0-1 (market power)
    position_analysis: str  # "offensive", "defensive", "neutral"
    terrain_control: List[str]  # Symbols/markets controlled
    
    # IRA Guerrilla Analysis
    movement_pattern: str  # "hit-and-run", "accumulation", "manipulation"
    stealth_score: float  # 0-1 (how hidden their ops are)
    ambush_locations: List[Tuple[str, float]]  # (symbol, time_hours)
    
    # Apache Patience Analysis
    patience_score: float  # 0-1 (wait time between actions)
    terrain_knowledge: float  # 0-1 (how well they know the market)
    survival_tactics: List[str]
    
    # Network Intelligence
    coordination_partners: List[str]
    coordination_strength: Dict[str, float]
    operation_frequency: float  # Hz
    
    # Vulnerability Assessment
    weaknesses_identified: List[str]
    counter_strategy: str
    disruption_probability: float  # 0-1
    
    timestamp: float = field(default_factory=time.time)

@dataclass
class CovertOperation:
    """Detected covert trading operation."""
    operation_id: str
    entities_involved: List[str]
    symbol: str
    operation_type: str  # "accumulation", "distribution", "squeeze", "raid"
    start_time: float
    duration_hours: float
    volume_moved: float
    stealth_rating: float  # 0-1
    detection_confidence: float  # 0-1
    countermeasure: str

class StrategicWarfareScanner:
    """
    Military-grade intelligence scanner for market warfare.
    
    Combines Sun Tzu, IRA, and Apache tactics to identify:
    1. Hidden coordination networks
    2. Covert accumulation/distribution ops
    3. Strategic ambush points
    4. Vulnerability windows
    """
    
    def __init__(self):
        self.entities = self.load_entity_database()
        self.intelligence_reports: List[IntelligenceReport] = []
        self.covert_operations: List[CovertOperation] = []
        self.network_map: Dict[str, Set[str]] = defaultdict(set)
        
        # Bus Integration
        self.thought_bus = ThoughtBus() if THOUGHT_BUS_AVAILABLE else None
        self.chirp_bus = None
        if CHIRP_BUS_AVAILABLE:
            try:
                self.chirp_bus = ChirpBus()
            except Exception:
                pass

        # Load wisdom databases
        self.sun_tzu_principles = self.load_sun_tzu_wisdom()
        self.ira_tactics = self.load_ira_tactics()
        
        print("🎖️ Strategic Warfare Scanner initialized")
        print("📚 Sun Tzu: Art of War principles loaded")
        print("🇮🇪 IRA: Guerrilla tactics database ready")
        print("🪶 Apache: Patience protocols active")
    
    def load_entity_database(self) -> Dict:
        """Load comprehensive entity database."""
        try:
            with open('comprehensive_entity_database.json', 'r') as f:
                entities_list = json.load(f)
            return {e['entity_name']: e for e in entities_list}
        except:
            return {}
    
    def load_sun_tzu_wisdom(self) -> Dict:
        """Load Sun Tzu's Art of War principles."""
        return {
            "know_enemy": "Gather maximum intelligence before engagement",
            "terrain": "Control the high ground - dominant market positions",
            "timing": "Strike when enemy is weak, retreat when strong",
            "deception": "All warfare is deception - markets lie constantly",
            "supreme_excellence": "Win without fighting - profit without risk",
            "concentration": "Concentrate force at decisive point",
            "speed": "Speed is essence of war - fast execution wins",
            "morale": "Will to fight matters more than weapons",
            "alliance": "Know who your allies are in the market",
            "spies": "Intelligence network is most valuable asset"
        }
    
    def load_ira_tactics(self) -> Dict:
        """Load IRA guerrilla warfare tactics."""
        return {
            "hit_and_run": "Quick strike, immediate withdrawal - scalp trades",
            "ambush": "Wait patiently, strike when target vulnerable",
            "covert_movement": "Operate in shadows, avoid detection",
            "safe_houses": "Multiple exchanges = multiple escape routes",
            "intelligence": "Courier network - information flows before action",
            "patience": "Wait weeks/months for perfect opportunity",
            "asymmetric": "Small force defeats large through superior tactics",
            "local_support": "Know the terrain intimately - your market",
            "propaganda": "Narrative warfare - sentiment manipulation",
            "cell_structure": "Decentralized ops - one cell compromised ≠ network down"
        }
    
    def analyze_entity_strength(self, entity_name: str, symbols: List[str]) -> IntelligenceReport:
        """
        Full military intelligence analysis of entity.
        
        Combines:
        - Sun Tzu strength/weakness assessment
        - IRA stealth/movement analysis
        - Apache patience scoring
        - Network coordination mapping
        """
        entity = self.entities.get(entity_name, {})
        
        print(f"\n🎯 Analyzing: {entity_name}")
        print(f"   Type: {entity.get('type', 'unknown')}")
        
        # Fetch market data across multiple symbols
        all_data = []
        for symbol in symbols:
            klines = self.fetch_klines(symbol, '1h', 500)
            if klines:
                all_data.append((symbol, klines))
                time.sleep(0.1)
        
        # Sun Tzu Analysis: Strength Assessment
        strength = self.assess_strength(all_data)
        position = self.analyze_position(all_data)
        terrain = self.identify_controlled_terrain(all_data)
        
        # IRA Analysis: Guerrilla Patterns
        movement = self.detect_movement_pattern(all_data)
        stealth = self.calculate_stealth_score(all_data)
        ambush_points = self.find_ambush_locations(all_data)
        
        # Apache Analysis: Patience & Terrain Knowledge
        patience = self.measure_patience(all_data)
        terrain_knowledge = self.assess_terrain_knowledge(all_data)
        survival = self.identify_survival_tactics(all_data)
        
        # Network Intelligence
        partners = self.detect_coordination_partners(entity_name)
        coord_strength = self.measure_coordination_strength(entity_name, partners)
        op_freq = self.calculate_operation_frequency(all_data)
        
        # Vulnerability Assessment
        weaknesses = self.identify_weaknesses(strength, stealth, patience)
        counter_strategy = self.generate_counter_strategy(movement, weaknesses)
        disruption_prob = self.calculate_disruption_probability(weaknesses)
        
        # Threat Classification
        threat_level = self.classify_threat_level(strength, coord_strength, stealth)
        
        report = IntelligenceReport(
            entity_name=entity_name,
            entity_type=entity.get('type', 'unknown'),
            threat_level=threat_level,
            strength_assessment=strength,
            position_analysis=position,
            terrain_control=terrain,
            movement_pattern=movement,
            stealth_score=stealth,
            ambush_locations=ambush_points,
            patience_score=patience,
            terrain_knowledge=terrain_knowledge,
            survival_tactics=survival,
            coordination_partners=partners,
            coordination_strength=coord_strength,
            operation_frequency=op_freq,
            weaknesses_identified=weaknesses,
            counter_strategy=counter_strategy,
            disruption_probability=disruption_prob
        )
        
        self.intelligence_reports.append(report)
        self._publish_report(report)
        return report
    
    def _publish_report(self, report: IntelligenceReport) -> None:
        """Publish intelligence report to ThoughtBus and ChirpBus."""
        try:
            # 1. ThoughtBus — Thought carries topic/payload/meta; the old
            # thought_type=/priority=/content= kwargs raised TypeError into the
            # except below, which also killed the ChirpBus publish after it, so
            # warfare intel had never actually reached either bus.
            if self.thought_bus:
                self.thought_bus.publish(Thought(
                    source="STRATEGIC_WARFARE",
                    topic="intelligence.warfare.report",
                    payload=asdict(report),
                    meta={"priority": 2, "thought_type": "INTELLIGENCE_REPORT"},
                ))

            # 2. ChirpBus
            if self.chirp_bus:
                self.chirp_bus.publish("warfare.intel", {
                    "entity": report.entity_name,
                    "threat": report.threat_level,
                    "strength": report.strength_assessment,
                    "type": report.entity_type
                })
        except Exception as e:
            print(f"⚠️ Failed to publish warfare report: {e}")

    def fetch_klines(self, symbol: str, interval: str, limit: int) -> List[Dict]:
        """Fetch klines from Binance."""
        url = "https://api.binance.com/api/v3/klines"
        params = {
            'symbol': symbol.replace('/', ''),
            'interval': interval,
            'limit': limit
        }
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            klines = response.json()
            return [
                {
                    'timestamp': k[0],
                    'open': float(k[1]),
                    'high': float(k[2]),
                    'low': float(k[3]),
                    'close': float(k[4]),
                    'volume': float(k[5]),
                }
                for k in klines
            ]
        except:
            return []
    
    def assess_strength(self, market_data: List) -> float:
        """Sun Tzu: Assess enemy strength (market dominance)."""
        if not market_data:
            return 0.0
        
        # Measure: Volume consistency, price impact, market share
        total_volume = sum([
            np.mean([k['volume'] for k in klines])
            for symbol, klines in market_data
        ])
        
        # Normalize 0-1 (log scale, arbitrary reference)
        strength = min(1.0, np.log10(total_volume + 1) / 8.0)
        return strength
    
    def analyze_position(self, market_data: List) -> str:
        """Sun Tzu: Is enemy offensive, defensive, or neutral?"""
        if not market_data:
            return "neutral"
        
        # Offensive = increasing volume, volatility
        # Defensive = decreasing volume, tight ranges
        
        total_volatility = 0
        for symbol, klines in market_data:
            if len(klines) < 20:
                continue
            recent = klines[-20:]
            volatility = np.std([k['close'] for k in recent]) / np.mean([k['close'] for k in recent])
            total_volatility += volatility
        
        avg_volatility = total_volatility / len(market_data) if market_data else 0
        
        if avg_volatility > 0.03:
            return "offensive"
        elif avg_volatility < 0.01:
            return "defensive"
        else:
            return "neutral"
    
    def identify_controlled_terrain(self, market_data: List) -> List[str]:
        """Sun Tzu: What markets does enemy control?"""
        controlled = []
        for symbol, klines in market_data:
            if len(klines) < 50:
                continue
            
            # Control = high volume presence consistently
            volumes = [k['volume'] for k in klines[-50:]]
            avg_vol = np.mean(volumes)
            
            # If consistently high volume (above median), they control this terrain
            if avg_vol > np.median(volumes) * 1.5:
                controlled.append(symbol)
        
        return controlled[:5]  # Top 5
    
    def detect_movement_pattern(self, market_data: List) -> str:
        """IRA: Hit-and-run, accumulation, or manipulation?"""
        if not market_data:
            return "unknown"
        
        # Analyze volume spike patterns
        spike_counts = []
        for symbol, klines in market_data:
            if len(klines) < 100:
                continue
            
            volumes = np.array([k['volume'] for k in klines[-100:]])
            median_vol = np.median(volumes)
            
            # Spike = > 2x median
            spikes = np.sum(volumes > median_vol * 2)
            spike_counts.append(spikes)
        
        if not spike_counts:
            return "unknown"
        
        avg_spikes = np.mean(spike_counts)
        
        if avg_spikes > 15:
            return "hit-and-run"  # Frequent spikes
        elif avg_spikes < 5:
            return "accumulation"  # Quiet accumulation
        else:
            return "manipulation"  # Periodic large moves
    
    def calculate_stealth_score(self, market_data: List) -> float:
        """IRA: How well hidden are their operations? (0=visible, 1=covert)"""
        if not market_data:
            logger.warning("[insufficient-data] calculate_stealth_score returning "
                           "neutral 0.5 (empty market_data)")
            return 0.5
        
        # Stealth = low volatility + consistent volume = blend in
        stealth_scores = []
        for symbol, klines in market_data:
            if len(klines) < 50:
                continue
            
            volumes = np.array([k['volume'] for k in klines[-50:]])
            vol_std = np.std(volumes)
            vol_mean = np.mean(volumes)
            
            # Coefficient of variation (lower = more stealthy)
            cv = vol_std / vol_mean if vol_mean > 0 else 1.0
            stealth = 1.0 - min(1.0, cv / 2.0)  # Normalize
            stealth_scores.append(stealth)
        
        return np.mean(stealth_scores) if stealth_scores else 0.5
    
    def find_ambush_locations(self, market_data: List) -> List[Tuple[str, float]]:
        """IRA: When/where do they strike? (symbol, hour_of_day)"""
        ambush_points = []
        
        for symbol, klines in market_data:
            if len(klines) < 100:
                continue
            
            # Find peak activity hours
            hourly_volume = defaultdict(list)
            for k in klines[-100:]:
                hour = (k['timestamp'] // 3600000) % 24
                hourly_volume[hour].append(k['volume'])
            
            # Calculate average volume per hour
            hourly_averages = {hour: np.mean(vols) for hour, vols in hourly_volume.items()}
            
            if not hourly_averages:
                continue
            
            # Identify top ambush hours
            median_hourly_vol = np.median(list(hourly_averages.values()))
            for hour, avg_vol in hourly_averages.items():
                if avg_vol > median_hourly_vol * 1.5:
                    ambush_points.append((symbol, float(hour)))
        
        return ambush_points[:10]  # Top 10
    
    def measure_patience(self, market_data: List) -> float:
        """Apache: How patient are they? (time between actions)"""
        if not market_data:
            logger.warning("[insufficient-data] measure_patience returning "
                           "neutral 0.5 (empty market_data)")
            return 0.5
        
        # Patience = low frequency of large moves
        patience_scores = []
        for symbol, klines in market_data:
            if len(klines) < 100:
                continue
            
            # Find gaps between significant moves
            prices = np.array([k['close'] for k in klines[-100:]])
            pct_changes = np.abs(np.diff(prices) / prices[:-1])
            
            # Significant move = >2% change
            sig_moves = np.where(pct_changes > 0.02)[0]
            
            if len(sig_moves) > 1:
                gaps = np.diff(sig_moves)
                avg_gap = np.mean(gaps)
                # Higher gap = more patience
                patience = min(1.0, avg_gap / 20.0)
            else:
                patience = 1.0  # Very patient
            
            patience_scores.append(patience)
        
        return np.mean(patience_scores) if patience_scores else 0.5
    
    def assess_terrain_knowledge(self, market_data: List) -> float:
        """Apache: How well do they know the market terrain?"""
        # Terrain knowledge = success in chosen symbols
        # (We approximate by volume presence)
        return min(1.0, len([1 for s, k in market_data if len(k) > 100]) / 5.0)
    
    def identify_survival_tactics(self, market_data: List) -> List[str]:
        """Apache: What survival tactics do they use?"""
        tactics = []
        
        # Tactic 1: Diversification (multiple symbols)
        if len(market_data) >= 3:
            tactics.append("diversification_across_terrain")
        
        # Tactic 2: Low profile (stealth)
        stealth = self.calculate_stealth_score(market_data)
        if stealth > 0.7:
            tactics.append("covert_operations")
        
        # Tactic 3: Patience (wait for optimal conditions)
        patience = self.measure_patience(market_data)
        if patience > 0.7:
            tactics.append("tactical_patience")
        
        return tactics
    
    def detect_coordination_partners(self, entity_name: str) -> List[str]:
        """SIGINT: Who are they coordinating with?"""
        # Load coordination network from previous scan
        try:
            with open('planetary_harmonic_network.json', 'r') as f:
                network_data = json.load(f)
            
            partners = set()
            for link in network_data.get('coordination_network', []):
                if link['entity_a'] == entity_name:
                    partners.add(link['entity_b'])
                elif link['entity_b'] == entity_name:
                    partners.add(link['entity_a'])
            
            return list(partners)[:10]  # Top 10
        except:
            return []
    
    def measure_coordination_strength(self, entity_name: str, partners: List[str]) -> Dict[str, float]:
        """SIGINT: How strong is coordination with each partner?"""
        strengths = {}
        
        try:
            with open('planetary_harmonic_network.json', 'r') as f:
                network_data = json.load(f)
            
            for link in network_data.get('coordination_network', []):
                if (link['entity_a'] == entity_name and link['entity_b'] in partners) or \
                   (link['entity_b'] == entity_name and link['entity_a'] in partners):
                    partner = link['entity_b'] if link['entity_a'] == entity_name else link['entity_a']
                    strengths[partner] = link['coordination_strength']
        except:
            pass
        
        return strengths
    
    def calculate_operation_frequency(self, market_data: List) -> float:
        """SIGINT: How often do they operate? (Hz)"""
        if not market_data:
            return 0.0
        
        # Average number of significant moves per hour
        total_ops = 0
        total_hours = 0
        
        for symbol, klines in market_data:
            if len(klines) < 50:
                continue
            
            volumes = np.array([k['volume'] for k in klines[-50:]])
            median_vol = np.median(volumes)
            
            # Operation = volume spike
            ops = np.sum(volumes > median_vol * 1.5)
            hours = len(klines)
            
            total_ops += ops
            total_hours += hours
        
        if total_hours > 0:
            return total_ops / total_hours
        return 0.0
    
    def identify_weaknesses(self, strength: float, stealth: float, patience: float) -> List[str]:
        """Sun Tzu: Every enemy has weaknesses."""
        weaknesses = []
        
        if strength < 0.3:
            weaknesses.append("low_market_power")
        if stealth < 0.3:
            weaknesses.append("highly_visible_operations")
        if patience < 0.3:
            weaknesses.append("impatient_overtrading")
        if strength > 0.9:
            weaknesses.append("overextended_positions")
        if stealth > 0.9:
            weaknesses.append("too_passive_miss_opportunities")
        
        return weaknesses
    
    def generate_counter_strategy(self, movement: str, weaknesses: List[str]) -> str:
        """Sun Tzu + IRA: How to counter this enemy?"""
        
        if "hit-and-run" in movement:
            return "Avoid their ambush hours. Trade opposite schedule. Use limit orders to avoid their impact."
        elif "accumulation" in movement:
            return "Front-run their accumulation. Small positions ahead of their buys."
        elif "manipulation" in movement:
            return "Fade their manipulation. When they pump, short. When they dump, buy."
        
        if "low_market_power" in weaknesses:
            return "Ignore them. Focus on bigger threats."
        if "highly_visible_operations" in weaknesses:
            return "Trade against them. Their visibility = predictability."
        if "overextended_positions" in weaknesses:
            return "Wait for liquidation cascade. Strike when they're forced to exit."
        
        return "Monitor and adapt. No clear counter-strategy yet."
    
    def calculate_disruption_probability(self, weaknesses: List[str]) -> float:
        """Probability we can disrupt their operations (0-1)."""
        if not weaknesses:
            return 0.1  # Strong enemy, hard to disrupt
        
        # More weaknesses = higher disruption probability
        return min(0.9, len(weaknesses) * 0.15)
    
    def classify_threat_level(self, strength: float, coord_strength: Dict, stealth: float) -> str:
        """Overall threat classification."""
        
        # Highly coordinated + strong = CRITICAL
        avg_coord = np.mean(list(coord_strength.values())) if coord_strength else 0
        
        if strength > 0.8 and avg_coord > 0.9:
            return "CRITICAL"
        elif strength > 0.6 and avg_coord > 0.7:
            return "HIGH"
        elif strength > 0.4 or stealth > 0.8:
            return "MEDIUM"
        else:
            return "LOW"
    
    def run_full_intelligence_sweep(self, max_entities: int = 25):
        """Execute full strategic intelligence sweep on all entities."""
        
        print("\n" + "="*80)
        print("🎖️⚡ STRATEGIC WARFARE INTELLIGENCE SWEEP ⚡🎖️")
        print("="*80)
        print("\n📚 Sun Tzu: 'If you know the enemy and know yourself...")
        print("          ...you need not fear the result of a hundred battles.'\n")
        print("🇮🇪 IRA: 'Move quietly, strike precisely, disappear.'\n")
        print("🪶 Apache: 'Patience is the warrior's greatest weapon.'\n")
        print("="*80 + "\n")
        
        symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'BNBUSDT']
        
        for idx, (entity_name, entity_data) in enumerate(list(self.entities.items())[:max_entities], 1):
            print(f"\n[{idx}/{min(max_entities, len(self.entities))}] 🎯 INTELLIGENCE GATHERING: {entity_name}")
            
            report = self.analyze_entity_strength(entity_name, symbols)
            
            # Display intelligence summary
            print(f"\n   📊 INTELLIGENCE SUMMARY:")
            print(f"   ├─ Threat Level: {report.threat_level}")
            print(f"   ├─ Strength: {report.strength_assessment:.2f} | Position: {report.position_analysis}")
            print(f"   ├─ Stealth: {report.stealth_score:.2f} | Movement: {report.movement_pattern}")
            print(f"   ├─ Patience: {report.patience_score:.2f} | Terrain Knowledge: {report.terrain_knowledge:.2f}")
            print(f"   ├─ Coordination Partners: {len(report.coordination_partners)}")
            print(f"   ├─ Weaknesses: {', '.join(report.weaknesses_identified) if report.weaknesses_identified else 'None detected'}")
            print(f"   └─ Counter-Strategy: {report.counter_strategy[:80]}...")
            
            time.sleep(0.2)  # Rate limit
        
        # Save intelligence reports
        self.save_intelligence_reports()
        
        # Final summary
        print("\n" + "="*80)
        print("📊 INTELLIGENCE SWEEP COMPLETE")
        print("="*80)
        print(f"🎯 Entities Analyzed: {len(self.intelligence_reports)}")
        
        critical = sum(1 for r in self.intelligence_reports if r.threat_level == 'CRITICAL')
        high = sum(1 for r in self.intelligence_reports if r.threat_level == 'HIGH')
        
        if critical > 0:
            print(f"🚨 CRITICAL THREATS: {critical}")
        if high > 0:
            print(f"⚠️ HIGH THREATS: {high}")
        
        print(f"\n💾 Full intelligence report: strategic_warfare_intelligence.json")
        print("\n🎖️ 'The general who wins a battle makes many calculations beforehand.' - Sun Tzu\n")
    
    def save_intelligence_reports(self):
        """Save all intelligence reports to file."""
        output = {
            'metadata': {
                'scan_timestamp': time.time(),
                'scan_date': datetime.now(timezone.utc).isoformat(),
                'total_entities_analyzed': len(self.intelligence_reports),
                'methodology': 'Sun Tzu + IRA + Apache warfare intelligence',
            },
            'intelligence_reports': [asdict(r) for r in self.intelligence_reports],
            'threat_matrix': self.generate_threat_matrix(),
            'tactical_recommendations': self.generate_tactical_recommendations(),
        }
        
        with open('strategic_warfare_intelligence.json', 'w') as f:
            json.dump(output, f, indent=2)
    
    def generate_threat_matrix(self) -> Dict:
        """Generate threat assessment matrix."""
        matrix = {
            'CRITICAL': [],
            'HIGH': [],
            'MEDIUM': [],
            'LOW': []
        }
        
        for report in self.intelligence_reports:
            matrix[report.threat_level].append({
                'entity': report.entity_name,
                'strength': report.strength_assessment,
                'coordination_partners': len(report.coordination_partners),
                'stealth': report.stealth_score
            })
        
        return matrix
    
    def generate_tactical_recommendations(self) -> List[str]:
        """Sun Tzu: Tactical recommendations based on intelligence."""
        recommendations = []
        
        # Analyze overall threat landscape
        critical_entities = [r for r in self.intelligence_reports if r.threat_level == 'CRITICAL']
        
        if len(critical_entities) > 5:
            recommendations.append("⚠️ HIGH COORDINATION DETECTED: Avoid trading against synchronized whale movements. Wait for coordination breakdown.")
        
        hit_run_entities = [r for r in self.intelligence_reports if r.movement_pattern == 'hit-and-run']
        if len(hit_run_entities) > 10:
            recommendations.append("🎯 MULTIPLE HIT-AND-RUN OPERATORS: Use limit orders, avoid market orders during their ambush hours.")
        
        accumulation_entities = [r for r in self.intelligence_reports if r.movement_pattern == 'accumulation']
        if accumulation_entities:
            recommendations.append(f"📊 ACCUMULATION DETECTED: {len(accumulation_entities)} entities quietly accumulating. Consider front-running their positions.")
        
        high_stealth = [r for r in self.intelligence_reports if r.stealth_score > 0.8]
        if high_stealth:
            recommendations.append(f"👻 COVERT OPERATIONS: {len(high_stealth)} entities operating with high stealth. Monitor for sudden volume spikes.")
        
        recommendations.append("🎖️ Sun Tzu: 'In the midst of chaos, there is also opportunity.' Trade when whales are fighting each other.")
        recommendations.append("🇮🇪 IRA: 'Hit and run. Small, precise strikes. Never overstay your welcome.'")
        recommendations.append("🪶 Apache: 'Patience. Know the terrain. Wait for the perfect moment.'")
        
        return recommendations

if __name__ == "__main__":
    scanner = StrategicWarfareScanner()
    scanner.run_full_intelligence_sweep(max_entities=25)

# Integration getter for IntelligenceReport
_GLOBAL_INSTANCE = None

def get_warfare_scanner():
    global _GLOBAL_INSTANCE
    if _GLOBAL_INSTANCE is None:
        _GLOBAL_INSTANCE = StrategicWarfareScanner()
    return _GLOBAL_INSTANCE
