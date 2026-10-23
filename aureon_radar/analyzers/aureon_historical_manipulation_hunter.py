#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                      ║
║     📜⚔️ AUREON HISTORICAL MANIPULATION HUNTER ⚔️📜                                   ║
║     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                              ║
║                                                                                      ║
║     TRACK COORDINATION ACROSS DECADES - HISTORY IS ON OUR SIDE                      ║
║                                                                                      ║
║     "Those who cannot remember the past are condemned to repeat it"                 ║
║     - George Santayana                                                               ║
║                                                                                      ║
║     ARCHITECTURE:                                                                    ║
║       • Historical Event Database (1900-2026)                                       ║
║       • Entity Involvement Tracker (Who existed? What did they do?)                 ║
║       • Pattern Recognition (Same tactics repeated across decades)                  ║
║       • Civilizational Impact Analysis (Financial → Societal collapse)             ║
║       • Evidence Accumulation (Build the case over 125 years)                       ║
║                                                                                      ║
║     MAJOR EVENTS TRACKED:                                                            ║
║       • 1913: Federal Reserve creation                                               ║
║       • 1929: Great Depression (orchestrated crash)                                  ║
║       • 1944: Bretton Woods (dollar dominance)                                       ║
║       • 1971: Nixon Shock (gold standard removed)                                    ║
║       • 1987: Black Monday (first algorithmic crash)                                 ║
║       • 1997: Asian Financial Crisis (currency manipulation)                         ║
║       • 2000: Dot-com Bubble (pump & dump)                                           ║
║       • 2008: Financial Crisis (mortgage fraud)                                      ║
║       • 2010: Flash Crash (HFT manipulation)                                         ║
║       • 2020: COVID Crash (coordinated dumping)                                      ║
║       • 2021-2022: Crypto manipulation                                               ║
║                                                                                      ║
║     Gary Leckey & GitHub Copilot | January 2026                                     ║
║     "History doesn't repeat, but it rhymes - and we hear the pattern"               ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)

# Windows UTF-8 fix
from aureon.utils.console_utf8 import ensure_utf8_stdout  # noqa: E402

ensure_utf8_stdout()

import json
import time
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# 📚 HISTORICAL EVENT TYPES
# ═══════════════════════════════════════════════════════════════

class EventType(Enum):
    """Types of historical manipulation events"""
    CRASH = "market_crash"                    # Orchestrated crashes
    BUBBLE = "bubble_pump"                     # Pump & dump schemes
    WAR_FUNDING = "war_financing"             # Wars funded through debt
    CURRENCY_MANIPULATION = "currency_attack" # Foreign exchange attacks
    REGIME_CHANGE = "regime_change"           # Destabilize governments
    REGULATORY_CAPTURE = "regulatory_capture" # Control rule-making
    BAILOUT = "elite_bailout"                 # Privatize gains, socialize losses
    TECHNOLOGY_SUPPRESSION = "tech_suppression" # Kill competing innovations
    RESOURCE_THEFT = "resource_extraction"    # Asset stripping


# ═══════════════════════════════════════════════════════════════
# 🏛️ HISTORICAL EVENT DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════

@dataclass
class HistoricalEvent:
    """A major historical manipulation event"""
    year: int
    name: str
    event_type: str                           # EventType
    description: str
    entities_involved: List[str]              # Which of our 25 entities were active
    evidence: List[str]                       # Documented proof
    civilizational_impact: str                # What happened to society
    wealth_transfer: str                      # Who lost, who gained
    pattern_signature: Dict = field(default_factory=dict)
    lessons_learned: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class EntityHistory:
    """Track an entity's historical involvement"""
    entity_name: str
    founded_year: int
    major_events: List[str] = field(default_factory=list)  # Event names
    manipulation_count: int = 0
    total_wealth_extracted: str = "Unknown"
    current_status: str = "Active"
    
    def to_dict(self) -> Dict:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════
# 📜 HISTORICAL EVENTS DATABASE
# ═══════════════════════════════════════════════════════════════

HISTORICAL_EVENTS = [
    HistoricalEvent(
        year=1913,
        name="Federal Reserve Act",
        event_type=EventType.REGULATORY_CAPTURE.value,
        description="Private banking cartel given power to print money and control interest rates",
        entities_involved=["US Federal Reserve", "JP Morgan (precursor)", "Rockefeller interests"],
        evidence=[
            "Jekyll Island meeting (1910) - secret gathering of bankers",
            "Passed during Christmas recess when opposition absent",
            "Woodrow Wilson later regretted: 'I have unwittingly ruined my country'"
        ],
        civilizational_impact="Transfer of monetary sovereignty from elected government to private bankers. Enabled unlimited debt creation.",
        wealth_transfer="From taxpayers to banking elite. Inflation tax on all dollar holders.",
        pattern_signature={"tactic": "Regulatory capture", "stealth": 0.95, "permanence": "Ongoing 113 years"},
        lessons_learned=[
            "Create money-printing monopoly under guise of 'stability'",
            "Pass controversial legislation when opposition is absent",
            "Control money supply = control civilization"
        ]
    ),
    
    HistoricalEvent(
        year=1929,
        name="Great Depression",
        event_type=EventType.CRASH.value,
        description="Orchestrated market crash after decade of credit expansion. Banks deliberately contracted money supply.",
        entities_involved=["Federal Reserve", "Major banks (JPM, Goldman precursors)", "Wealthy industrialists"],
        evidence=[
            "Fed raised interest rates in 1928-29 despite warning signs",
            "Margin lending encouraged then suddenly restricted",
            "Wealthy withdrew from market before crash (insider knowledge)",
            "Fed refused to inject liquidity during crash (deliberate)"
        ],
        civilizational_impact="25% unemployment, mass starvation, social breakdown. Led directly to WWII.",
        wealth_transfer="$30 billion wealth destroyed. Assets bought for pennies by those with cash reserves.",
        pattern_signature={"tactic": "Credit expansion → sudden contraction", "wealth_concentration": "Massive"},
        lessons_learned=[
            "Inflate credit bubble for years",
            "Pull liquidity suddenly to trigger crash",
            "Buy assets at bottom with reserves",
            "Blame 'capitalism' not the controllers"
        ]
    ),
    
    HistoricalEvent(
        year=1944,
        name="Bretton Woods Agreement",
        event_type=EventType.CURRENCY_MANIPULATION.value,
        description="Dollar made world reserve currency, backed by gold. Set up for future Nixon Shock.",
        entities_involved=["US Federal Reserve", "US Treasury", "International bankers"],
        evidence=[
            "44 nations agreed to peg currencies to dollar",
            "Dollar 'as good as gold' at $35/oz",
            "US accumulated majority of world's gold through war",
            "Created IMF and World Bank (debt trap institutions)"
        ],
        civilizational_impact="Dollar hegemony established. All international trade requires dollars.",
        wealth_transfer="Every nation must hold dollars = permanent tribute to US. 'Exorbitant privilege'",
        pattern_signature={"tactic": "Post-war financial architecture capture", "scope": "Global"},
        lessons_learned=[
            "Use war victory to impose financial system",
            "Control reserve currency = tax all trade",
            "Promise gold backing (remove later)"
        ]
    ),
    
    HistoricalEvent(
        year=1971,
        name="Nixon Shock - Gold Standard Abandoned",
        event_type=EventType.CURRENCY_MANIPULATION.value,
        description="Nixon closed gold window, making dollar pure fiat. Largest theft in history.",
        entities_involved=["Federal Reserve", "US Treasury", "Nixon administration"],
        evidence=[
            "August 15, 1971 - unilateral announcement",
            "Promised 'temporary' (never restored)",
            "Foreign nations' gold claims invalidated",
            "Freed Fed to print unlimited money"
        ],
        civilizational_impact="Beginning of unlimited money printing. Purchasing power of dollar down 98% since. Wages stagnant despite GDP growth.",
        wealth_transfer="All foreign dollar holders robbed. Savings destroyed via inflation. Asset owners (rich) protected.",
        pattern_signature={"tactic": "Break promise, normalize theft", "inflation_weapon": "Activated"},
        lessons_learned=[
            "Promise can be broken if powerful enough",
            "Inflation = hidden tax on poor/middle class",
            "Asset inflation makes rich richer",
            "Fiat enables unlimited government/bank power"
        ]
    ),
    
    HistoricalEvent(
        year=1987,
        name="Black Monday Crash",
        event_type=EventType.CRASH.value,
        description="First major algorithmic/program trading crash. -22% in single day.",
        entities_involved=["Federal Reserve", "Major investment banks", "Renaissance Technologies (early HFT)"],
        evidence=[
            "Program trading blamed (early algorithms)",
            "Portfolio insurance created feedback loop",
            "Insiders knew and positioned beforehand",
            "Fed immediately cut rates (Greenspan Put established)"
        ],
        civilizational_impact="Proved algorithms could create systemic crashes. Established 'Fed Put' (bailouts guaranteed).",
        wealth_transfer="$500B paper wealth destroyed. Bottom-buyers profited massively.",
        pattern_signature={"tactic": "Algorithmic cascade + Fed rescue", "moral_hazard": "Created"},
        lessons_learned=[
            "Algorithms amplify crashes",
            "Create problem, offer solution (Fed Put)",
            "Moral hazard: Rich know they'll be rescued",
            "Crashes are buying opportunities for insiders"
        ]
    ),
    
    HistoricalEvent(
        year=1997,
        name="Asian Financial Crisis",
        event_type=EventType.CURRENCY_MANIPULATION.value,
        description="Coordinated attack on Asian currencies by hedge funds. George Soros famous example.",
        entities_involved=["Hedge funds (Soros Quantum Fund)", "IMF (enforced austerity)", "US Treasury"],
        evidence=[
            "Thailand baht attacked first (July 1997)",
            "Spread to Malaysia, Indonesia, South Korea",
            "Short selling + rumors created panic",
            "IMF imposed harsh austerity (fire sale of assets)"
        ],
        civilizational_impact="Millions impoverished. Suicides spiked. Assets sold to Western firms at pennies.",
        wealth_transfer="$600B wealth destroyed in Asia. Western firms bought infrastructure, banks, companies at 90% discounts.",
        pattern_signature={"tactic": "Currency attack → IMF austerity → asset stripping", "colonial_pattern": "Yes"},
        lessons_learned=[
            "Attack developing nation currencies",
            "Create panic via short selling",
            "IMF enforces austerity (makes crisis worse)",
            "Buy assets at fire sale prices",
            "Modern colonialism via finance"
        ]
    ),
    
    HistoricalEvent(
        year=2000,
        name="Dot-Com Bubble Burst",
        event_type=EventType.BUBBLE.value,
        description="Internet stock pump & dump. Retail investors destroyed, insiders sold at peak.",
        entities_involved=["Investment banks (Goldman, Morgan Stanley)", "Fed (easy money 1995-2000)", "VC firms"],
        evidence=[
            "Fed kept rates at 1% (1992-1994), inflated bubble",
            "Banks took garbage companies public (fraud)",
            "Insiders sold at peak (2000)",
            "Fed raised rates 1999-2000 (popped bubble)",
            "Nasdaq dropped 78% (2000-2002)"
        ],
        civilizational_impact="$5 trillion wealth destroyed. Retirement accounts devastated. Tech innovation set back years.",
        wealth_transfer="Retail investors lost life savings. Insiders cashed out billions before crash.",
        pattern_signature={"tactic": "Easy money → pump → insider exit → crash", "fraud": "Massive"},
        lessons_learned=[
            "Create bubble with easy money",
            "List fraudulent companies",
            "Promote 'new paradigm' (this time is different)",
            "Insiders sell at peak to retail",
            "Pop bubble by raising rates",
            "Blame 'irrational exuberance' not fraud"
        ]
    ),
    
    HistoricalEvent(
        year=2008,
        name="Global Financial Crisis",
        event_type=EventType.CRASH.value,
        description="Mortgage fraud pyramid scheme collapse. Banks knew, regulators knew, nobody stopped it.",
        entities_involved=["Federal Reserve", "Investment banks (Goldman, Lehman, etc.)", "Rating agencies (Moody's, S&P)", "Hedge funds"],
        evidence=[
            "Subprime mortgages packaged as AAA securities (fraud)",
            "Banks knew mortgages were garbage (internal emails)",
            "Rating agencies paid to give AAA ratings",
            "Fed ignored warnings (2005-2007)",
            "Goldman shorted same securities they sold (fraud)"
        ],
        civilizational_impact="$16 trillion wealth destroyed. 10 million foreclosures. Greatest wealth transfer in history.",
        wealth_transfer="Middle class lost homes, savings, jobs. Banks bailed out $16 trillion. Zero executives jailed.",
        pattern_signature={"tactic": "Fraud → crash → bailout → no consequences", "regulatory_capture": "Complete"},
        lessons_learned=[
            "Create fraud pyramid (mortgages, CDOs)",
            "Rating agencies will lie for fees",
            "Regulators will ignore (revolving door)",
            "When it blows up, government bails you out",
            "Too big to fail = too big to jail",
            "Privatize gains, socialize losses"
        ]
    ),
    
    HistoricalEvent(
        year=2010,
        name="Flash Crash",
        event_type=EventType.CRASH.value,
        description="HFT algorithms caused 1000-point Dow drop in minutes. Preview of algo control.",
        entities_involved=["HFT firms (Citadel, Jane Street, etc.)", "SEC (useless)", "Exchanges"],
        evidence=[
            "9:30 AM - market normal",
            "2:45 PM - algorithms triggered cascade",
            "Dow dropped 1000 points in 5 minutes",
            "Recovered in 10 minutes (but damage done)",
            "One trader scapegoated, HFT firms untouched"
        ],
        civilizational_impact="Proved algos control markets. Retail confidence destroyed. Algos now run everything.",
        wealth_transfer="Stop losses harvested. Algos bought at bottom, sold at recovery.",
        pattern_signature={"tactic": "Algorithm cascade → liquidity removal → harvest stops → recover", "speed": "Microseconds"},
        lessons_learned=[
            "HFT algos coordinate crashes",
            "Liquidity is illusion (vanishes when needed)",
            "Scapegoat small player, protect cartel",
            "Microsecond advantage = god mode",
            "Markets no longer for humans"
        ]
    ),
    
    HistoricalEvent(
        year=2020,
        name="COVID Crash & Recovery",
        event_type=EventType.CRASH.value,
        description="Coordinated dump in March, Fed printed $6 trillion, biggest wealth transfer in history.",
        entities_involved=["Federal Reserve", "BlackRock", "All major banks", "Big Tech"],
        evidence=[
            "Senators sold stocks in February (insider trading)",
            "Market dumped -35% in March",
            "Fed printed $6 trillion in 6 months",
            "Assets: stocks, housing, crypto all exploded",
            "BlackRock hired by Fed to buy assets (conflict of interest)"
        ],
        civilizational_impact="Small businesses destroyed (lockdowns). Big corporations bailed out. Wealth gap largest in history.",
        wealth_transfer="$3.9 trillion transferred from bottom 90% to top 1%. Billionaires gained $1.8 trillion.",
        pattern_signature={"tactic": "Crisis → lockdown → print money → asset inflation", "speed": "6 months"},
        lessons_learned=[
            "Any crisis can be weaponized",
            "Print unlimited money for elites",
            "Destroy small businesses (competition)",
            "Inflate assets (rich own assets)",
            "Poor get stimulus crumbs, rich get trillions",
            "Largest wealth transfer in history"
        ]
    ),
    
    HistoricalEvent(
        year=2021,
        name="GameStop & Meme Stock Suppression",
        event_type=EventType.REGULATORY_CAPTURE.value,
        description="Retail investors winning, platforms shut down buying. Naked short selling exposed.",
        entities_involved=["Citadel", "Robinhood", "Melvin Capital", "SEC (protected shorts)"],
        evidence=[
            "Short interest >100% (naked shorting = illegal)",
            "Jan 28, 2021: Robinhood disabled buy button",
            "Only allowed selling (crashed price)",
            "Citadel bailed out Melvin $2.75B",
            "SEC did nothing about naked shorts"
        ],
        civilizational_impact="Proof that retail can never win. System rigged at infrastructure level. Rules don't apply to elites.",
        wealth_transfer="Billions stolen from retail via forced selling. Hedge funds rescued.",
        pattern_signature={"tactic": "When losing, change rules mid-game", "blatant": "Yes"},
        lessons_learned=[
            "Naked short selling (fraud) is allowed for elites",
            "When retail wins, shut down platforms",
            "SEC protects hedge funds, not investors",
            "System is rigged at infrastructure level",
            "'Free market' is illusion"
        ]
    ),
    
    HistoricalEvent(
        year=2022,
        name="FTX Collapse - Crypto Exchange Fraud",
        event_type=EventType.CRASH.value,
        description="$32B crypto exchange revealed as fraud. Customer funds stolen, used for trading.",
        entities_involved=["FTX (Sam Bankman-Fried)", "Alameda Research", "VC firms", "Politicians (donations)"],
        evidence=[
            "Customer funds used for Alameda trading (fraud)",
            "$8B customer money missing",
            "Backdoor in code to hide theft",
            "SBF donated $40M to politicians (both parties)",
            "Regulators ignored warnings"
        ],
        civilizational_impact="Crypto industry set back years. Retail lost life savings. Calls for regulation (what they wanted).",
        wealth_transfer="$32B stolen from retail investors. Connected insiders warned early.",
        pattern_signature={"tactic": "Ponzi scheme → collapse → regulate (kill competition)", "political_capture": "Massive"},
        lessons_learned=[
            "Crypto can be controlled via exchanges",
            "Political donations buy immunity (temporarily)",
            "Let fraud run wild, then regulate industry to death",
            "Centralized exchanges = same old fraud",
            "Not your keys, not your crypto"
        ]
    )
]


# ═══════════════════════════════════════════════════════════════
# 🔍 HISTORICAL MANIPULATION HUNTER ENGINE
# ═══════════════════════════════════════════════════════════════

class HistoricalManipulationHunter:
    """
    Hunt for manipulation patterns across history
    
    "Those who cannot remember the past are condemned to repeat it"
    """
    
    def __init__(self):
        self.events = HISTORICAL_EVENTS
        self.entity_histories: Dict[str, EntityHistory] = {}
        self.pattern_recognition: Dict[str, List[str]] = {}
        
        # State files
        self.output_file = Path("historical_manipulation_evidence.json")
        self.pattern_file = Path("manipulation_patterns_across_time.json")
        
        logger.info(f"📜 Historical Manipulation Hunter initialized - {len(self.events)} events cataloged")
    
    def analyze_all_events(self) -> Dict:
        """Analyze all historical events and extract patterns"""
        print(f"\n{'═'*80}")
        print("📜 HUNTING THROUGH HISTORY - 125 YEARS OF MANIPULATION")
        print(f"{'═'*80}\n")
        
        results = {
            'total_events': len(self.events),
            'year_range': f"{min(e.year for e in self.events)} - {max(e.year for e in self.events)}",
            'events_by_type': {},
            'entity_involvement': {},
            'patterns_detected': {},
            'civilizational_damage': [],
            'lessons_learned': [],
            'evidence': []
        }
        
        # Analyze each event
        for event in self.events:
            print(f"\n{'─'*80}")
            print(f"📅 {event.year}: {event.name}")
            print(f"{'─'*80}")
            print(f"Type: {event.event_type}")
            print(f"Description: {event.description}")
            print(f"\n🏢 Entities Involved: {', '.join(event.entities_involved)}")
            print(f"\n📊 Civilizational Impact:")
            print(f"   {event.civilizational_impact}")
            print(f"\n💰 Wealth Transfer:")
            print(f"   {event.wealth_transfer}")
            print(f"\n🔍 Evidence:")
            for evidence in event.evidence:
                print(f"   • {evidence}")
            print(f"\n📚 Lessons They Learned:")
            for lesson in event.lessons_learned:
                print(f"   • {lesson}")
            
            # Track by type
            if event.event_type not in results['events_by_type']:
                results['events_by_type'][event.event_type] = []
            results['events_by_type'][event.event_type].append(event.name)
            
            # Track entity involvement
            for entity in event.entities_involved:
                if entity not in results['entity_involvement']:
                    results['entity_involvement'][entity] = []
                results['entity_involvement'][entity].append(f"{event.year}: {event.name}")
            
            # Track patterns
            for pattern_key, pattern_value in event.pattern_signature.items():
                if pattern_key not in results['patterns_detected']:
                    results['patterns_detected'][pattern_key] = []
                results['patterns_detected'][pattern_key].append({
                    'year': event.year,
                    'event': event.name,
                    'value': pattern_value
                })
            
            # Collect evidence
            results['evidence'].append({
                'year': event.year,
                'event': event.name,
                'evidence': event.evidence,
                'impact': event.civilizational_impact
            })
            
            # Collect lessons
            results['lessons_learned'].extend([
                {
                    'year': event.year,
                    'event': event.name,
                    'lesson': lesson
                }
                for lesson in event.lessons_learned
            ])
        
        # Summary statistics
        print(f"\n\n{'═'*80}")
        print("📊 HISTORICAL MANIPULATION SUMMARY")
        print(f"{'═'*80}\n")
        
        print(f"Total Events Cataloged: {results['total_events']}")
        print(f"Time Period: {results['year_range']} ({max(e.year for e in self.events) - min(e.year for e in self.events)} years)")
        
        print(f"\n📈 Events by Type:")
        for event_type, events in sorted(results['events_by_type'].items()):
            print(f"   {event_type}: {len(events)} events")
        
        print(f"\n🏢 Most Active Entities:")
        sorted_entities = sorted(results['entity_involvement'].items(), key=lambda x: len(x[1]), reverse=True)
        for entity, events in sorted_entities[:10]:
            print(f"   {entity}: {len(events)} major manipulations")
        
        print(f"\n🔄 Repeated Patterns Detected:")
        for pattern, occurrences in results['patterns_detected'].items():
            print(f"   {pattern}: {len(occurrences)} times across history")
        
        # Save results
        self._save_results(results)
        
        return results
    
    def find_pattern_repetition(self, tactic: str) -> List[HistoricalEvent]:
        """Find all events using the same tactic"""
        matching_events = []
        for event in self.events:
            if 'tactic' in event.pattern_signature:
                if tactic.lower() in str(event.pattern_signature['tactic']).lower():
                    matching_events.append(event)
        return matching_events
    
    def get_entity_timeline(self, entity_name: str) -> List[HistoricalEvent]:
        """Get all events involving a specific entity"""
        return [e for e in self.events if entity_name in e.entities_involved]
    
    def analyze_current_conditions(self, symbol: str = "", price_change_pct: float = 0.0,
                                    volume: float = 0.0, momentum: float = 0.0) -> Optional[Dict]:
        """
        Analyze current market conditions against historical manipulation patterns.
        
        Returns pattern match if current conditions resemble historical events.
        Used by Orca Kill Cycle for quantum scoring.
        """
        # Calculate current condition signature
        is_crash_signature = price_change_pct < -10.0  # Major crash
        is_bubble_pop = price_change_pct < -5.0 and volume > 1000000  # High volume selloff
        is_pump = price_change_pct > 20.0  # Potential pump
        is_coordinated = abs(price_change_pct) > 8.0 and volume > 500000  # Large coordinated move
        
        # Check for pattern matches
        for event in self.events:
            pattern = event.pattern_signature
            
            # 1929-style crash pattern: sudden contraction after expansion
            if event.year == 1929 and is_crash_signature:
                return {
                    'pattern_name': 'Great Depression Pattern',
                    'similarity': 0.7 + (abs(price_change_pct) / 50),
                    'historical_outcome': 'MASSIVE_CRASH',
                    'is_danger_pattern': True,
                    'is_opportunity_pattern': False,
                    'warning': '⚠️ 1929-style crash pattern detected! Exit positions!',
                    'event': event.to_dict()
                }
            
            # 2008-style crash pattern: coordinated selling
            if event.year == 2008 and is_coordinated and price_change_pct < -3:
                return {
                    'pattern_name': 'Financial Crisis Pattern',
                    'similarity': 0.65 + (abs(price_change_pct) / 30),
                    'historical_outcome': 'SYSTEMIC_CRISIS',
                    'is_danger_pattern': True,
                    'is_opportunity_pattern': False,
                    'warning': '⚠️ 2008-style coordinated dump detected! Reduce exposure!',
                    'event': event.to_dict()
                }
            
            # 2010 Flash Crash pattern: sudden HFT-driven crash
            if event.year == 2010 and price_change_pct < -8.0:
                return {
                    'pattern_name': 'Flash Crash Pattern',
                    'similarity': 0.75,
                    'historical_outcome': 'RAPID_RECOVERY',
                    'is_danger_pattern': True,  # Dangerous short term
                    'is_opportunity_pattern': True,  # But recovers quickly
                    'warning': '⚡ Flash crash pattern - may recover quickly!',
                    'event': event.to_dict()
                }
            
            # 2000 Dot-com pump & dump pattern
            if event.year == 2000 and is_pump:
                return {
                    'pattern_name': 'Dot-com Bubble Pattern',
                    'similarity': 0.6 + (price_change_pct / 50),
                    'historical_outcome': 'BUBBLE_POP',
                    'is_danger_pattern': True,  # Top signal
                    'is_opportunity_pattern': False,
                    'warning': '🎈 Dot-com style pump detected - potential bubble top!',
                    'event': event.to_dict()
                }
            
            # 2020 COVID crash pattern: sudden shock then V-recovery
            if event.year == 2020 and is_crash_signature:
                return {
                    'pattern_name': 'COVID Crash Pattern',
                    'similarity': 0.7,
                    'historical_outcome': 'V_RECOVERY',
                    'is_danger_pattern': False,  # Opportunity in disguise
                    'is_opportunity_pattern': True,  # Buy the dip!
                    'warning': '📈 COVID-style crash pattern - may see V-recovery!',
                    'event': event.to_dict()
                }
        
        # No concerning pattern detected
        return None
    
    def calculate_total_damage(self) -> Dict:
        """Calculate total civilizational damage across all events"""
        return {
            'events_count': len(self.events),
            'years_of_manipulation': max(e.year for e in self.events) - min(e.year for e in self.events),
            'pattern': 'ONGOING AND ACCELERATING',
            'conclusion': 'They have been doing this for over 100 years. It is not random. It is systematic wealth extraction.'
        }
    
    def _save_results(self, results: Dict):
        """Save analysis results to disk"""
        # Main evidence file
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        
        # Pattern analysis file
        pattern_analysis = {
            'patterns_identified': results['patterns_detected'],
            'repeated_tactics': {},
            'entity_specializations': {},
            'acceleration_detected': True,
            'timestamp': time.time()
        }
        
        # Find which tactics are used repeatedly
        for event in self.events:
            if 'tactic' in event.pattern_signature:
                tactic = str(event.pattern_signature['tactic'])
                if tactic not in pattern_analysis['repeated_tactics']:
                    pattern_analysis['repeated_tactics'][tactic] = []
                pattern_analysis['repeated_tactics'][tactic].append({
                    'year': event.year,
                    'event': event.name
                })
        
        with open(self.pattern_file, 'w', encoding='utf-8') as f:
            json.dump(pattern_analysis, f, indent=2)
        
        logger.info(f"💾 Evidence saved to {self.output_file}")
        logger.info(f"💾 Patterns saved to {self.pattern_file}")


# ═══════════════════════════════════════════════════════════════
# 🧪 MAIN - HUNT THROUGH HISTORY
# ═══════════════════════════════════════════════════════════════

def main():
    """Hunt for manipulation patterns across 125 years of history"""
    print("""
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                      ║
║     📜⚔️ HISTORICAL MANIPULATION HUNTER ⚔️📜                                          ║
║                                                                                      ║
║     "History is on our side - we can see what they've been doing"                   ║
║                                                                                      ║
║     Tracking 125+ years of orchestrated crashes, bubbles, and wealth extraction     ║
║                                                                                      ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
    """)
    
    hunter = HistoricalManipulationHunter()
    
    # Analyze all historical events
    results = hunter.analyze_all_events()
    
    # Show pattern repetition example
    print(f"\n\n{'═'*80}")
    print("🔄 PATTERN REPETITION EXAMPLE: 'Credit expansion → sudden contraction'")
    print(f"{'═'*80}\n")
    
    pattern_events = hunter.find_pattern_repetition("expansion")
    for event in pattern_events:
        print(f"   {event.year}: {event.name}")
        print(f"      → {event.pattern_signature.get('tactic', 'N/A')}")
    
    # Calculate total damage
    damage = hunter.calculate_total_damage()
    print(f"\n\n{'═'*80}")
    print("💀 TOTAL CIVILIZATIONAL DAMAGE")
    print(f"{'═'*80}\n")
    print(f"Years of Manipulation: {damage['years_of_manipulation']}")
    print(f"Events Cataloged: {damage['events_count']}")
    print(f"Pattern: {damage['pattern']}")
    print(f"\n⚠️  CONCLUSION:")
    print(f"   {damage['conclusion']}")
    
    print(f"\n\n{'═'*80}")
    print("✅ Historical analysis complete")
    print(f"   Evidence: historical_manipulation_evidence.json")
    print(f"   Patterns: manipulation_patterns_across_time.json")
    print(f"{'═'*80}\n")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s'
    )
    main()

# Integration getter for EventType
_GLOBAL_INSTANCE = None

def get_manipulation_hunter():
    global _GLOBAL_INSTANCE
    if _GLOBAL_INSTANCE is None:
        _GLOBAL_INSTANCE = HistoricalManipulationHunter()
    return _GLOBAL_INSTANCE
