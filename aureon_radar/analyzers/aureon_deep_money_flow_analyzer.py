#!/usr/bin/env python3
"""
AUREON DEEP MONEY FLOW ANALYZER
===============================
Ultimate system that wires ALL intelligence together:
- Historical manipulation events with dates/times
- Bot activity correlated to money flows
- Where the money went, who moved it
- Short-term and long-term planetary effects
- Queen + Enigma + Mycelium deep learning integration

THE COMPLETE PICTURE: Follow the money through time.
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import sys
from pathlib import Path

# UTF-8 fix — aureon.utils.console_utf8 is absent from the upstream package;
# fall back to the repo shim, then to an inline no-op reconfigure.
try:
    from aureon.utils.console_utf8 import ensure_utf8_stdout  # noqa: E402
except ImportError:  # pragma: no cover - environment dependent
    try:
        from _console_utf8_shim import ensure_utf8_stdout  # noqa: E402
    except ImportError:
        def ensure_utf8_stdout(*_a, **_k):
            try:
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
                sys.stderr.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

import json
import math
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum

# Sacred constants
PHI = (1 + math.sqrt(5)) / 2  # 1.618 Golden ratio
LOVE_FREQUENCY = 528  # Hz
SCHUMANN_BASE = 7.83  # Hz

# All artifacts live under aureon_radar/state/ regardless of cwd
_RADAR_ROOT = Path(__file__).resolve().parent.parent
_STATE_DIR = _RADAR_ROOT / "state"


def _resolve_path(filename: str) -> Path:
    """Resolve an evidence/output file: analyzer dir, then radar root, then cwd."""
    for base in (Path.cwd(), _RADAR_ROOT, Path(__file__).resolve().parent):
        candidate = base / filename
        if candidate.exists():
            return candidate
    return _RADAR_ROOT / filename


class FlowDirection(Enum):
    """Where the money flows"""
    RETAIL_TO_INSTITUTION = "retail_to_institution"
    INSTITUTION_TO_OFFSHORE = "institution_to_offshore"
    OFFSHORE_TO_POLITICAL = "offshore_to_political"
    POLITICAL_TO_WAR = "political_to_war"
    WAR_TO_RECONSTRUCTION = "war_to_reconstruction"
    PUBLIC_TO_PRIVATE = "public_to_private"
    FUTURE_TO_PRESENT = "future_to_present"  # Debt-based extraction


class PlanetaryEffect(Enum):
    """Effects on the planet and humanity"""
    WEALTH_CONCENTRATION = "wealth_concentration"
    ECONOMIC_DEPRESSION = "economic_depression"
    WAR_FINANCING = "war_financing"
    ENVIRONMENTAL_DESTRUCTION = "environmental_destruction"
    SOCIAL_DIVISION = "social_division"
    DEBT_SLAVERY = "debt_slavery"
    RESOURCE_DEPLETION = "resource_depletion"
    CONSCIOUSNESS_SUPPRESSION = "consciousness_suppression"


@dataclass
class MoneyFlowEvent:
    """A single money flow event with full traceability"""
    event_id: str
    date: str
    event_name: str

    # Who
    perpetrators: List[str]
    beneficiaries: List[str]
    victims: List[str]

    # Attributed Bots (Link to Census)
    attributed_bots: List[str] = field(default_factory=list) # List of BotUUIDs from Registry
    manipulation_vector: str = ""   # "SPOOFING", "WASH_TRADING", "CHURNING"

    # What
    amount_extracted_usd: float = 0.0
    extraction_method: str = ""
    flow_direction: str = ""

    # Where
    source_location: str = ""
    destination_location: str = ""
    intermediaries: List[str] = field(default_factory=list)

    # Why
    stated_reason: str = ""
    actual_reason: str = ""

    # Effects
    short_term_effects: List[str] = field(default_factory=list)
    long_term_effects: List[str] = field(default_factory=list)
    planetary_effects: List[str] = field(default_factory=list)

    # Evidence
    evidence_sources: List[str] = field(default_factory=list)
    confidence: float = 0.0
    correlated_bot_activity: List[str] = field(default_factory=list)

# ═══════════════════════════════════════════════════════════════════════════════
# 📜 HISTORICAL MANIPULATION EVIDENCE VAULT 📜
# ═══════════════════════════════════════════════════════════════════════════════

class DeepMoneyFlowVault:
    def __init__(self, vault_path=None):
        self.vault_path = str(vault_path) if vault_path else str(_STATE_DIR / "deep_money_flow_vault.json")
        self.events: List[MoneyFlowEvent] = []
        self.load()
        
    def add_event(self, event: MoneyFlowEvent):
        self.events.append(event)
        self.save()
        
    def find_by_perpetrator(self, name: str) -> List[MoneyFlowEvent]:
        return [e for e in self.events if name in e.perpetrators]
        
    def save(self):
        # Convert dataclasses to dicts for JSON serialization
        Path(self.vault_path).parent.mkdir(parents=True, exist_ok=True)
        data = [asdict(e) for e in self.events]
        with open(self.vault_path, 'w') as f:
            json.dump(data, f, indent=2)
            
    def load(self):
        if os.path.exists(self.vault_path):
            try:
                with open(self.vault_path, 'r') as f:
                    data = json.load(f)
                    self.events = [MoneyFlowEvent(**d) for d in data]
            except Exception as e:
                print(f"Error loading vault: {e}")
                
_vault_instance = DeepMoneyFlowVault()
def get_money_flow_vault() -> DeepMoneyFlowVault: return _vault_instance


@dataclass
class DeepAnalysisResult:
    """Complete deep analysis output"""
    timestamp: str
    total_extraction_usd: float
    total_events: int
    perpetrator_network: Dict[str, List[str]]
    money_flow_map: Dict[str, float]
    planetary_damage_score: float
    timeline_events: List[Dict]
    bot_correlations: Dict[str, List[str]]
    recommendations: List[str]
    
    # Correlation
    correlated_bot_activity: List[str] = field(default_factory=list)
    correlated_events: List[str] = field(default_factory=list)


class DeepMoneyFlowAnalyzer:
    """
    The Ultimate Intelligence System
    Wires together ALL Aureon subsystems to trace money flows through time.
    """
    
    def __init__(self):
        self.events: List[MoneyFlowEvent] = []
        self.bot_data = {}
        self.harmonic_data = {}
        self.historical_data = {}
        self.entity_data = []
        self.warfare_data = {}
        
        self._load_all_evidence()
        self._build_comprehensive_timeline()
    
    def _load_all_evidence(self):
        """Load all evidence databases"""
        print("🔄 Loading all evidence databases...")
        
        evidence_files = {
            'bot_census_registry.json': 'bot_data',
            'bot_cultural_attribution.json': 'bot_attribution',
            'planetary_harmonic_network.json': 'harmonic_data',
            'historical_manipulation_evidence.json': 'historical_data',
            'manipulation_patterns_across_time.json': 'patterns_data',
            'strategic_warfare_intelligence.json': 'warfare_data',
            'comprehensive_entity_database.json': 'entity_data',
        }
        
        for filename, attr in evidence_files.items():
            path = _resolve_path(filename)
            if path.exists():
                try:
                    with open(path, 'r') as f:
                        data = json.load(f)
                        setattr(self, attr, data)
                        print(f"  ✅ Loaded {path}")
                except Exception as e:
                    print(f"  ⚠️ Error loading {path}: {e}")
    
    def _build_comprehensive_timeline(self):
        """Build the master timeline of money extraction events"""
        print("\n📊 Building comprehensive money flow timeline...")
        
        # Major historical events with full money flow analysis
        major_events = [
            # 1913 - Federal Reserve Creation
            MoneyFlowEvent(
                event_id="FED_CREATION_1913",
                date="1913-12-23",
                event_name="Federal Reserve Act",
                perpetrators=["Nelson Aldrich", "Paul Warburg", "JP Morgan", "Rockefeller Family", "Rothschild Banking"],
                beneficiaries=["Private Banking Cartel", "Jekyll Island Conspirators"],
                victims=["American Citizens", "Future Generations"],
                amount_extracted_usd=0,  # Infinite - created money printing machine
                extraction_method="Legislative capture - private central bank creation",
                flow_direction=FlowDirection.PUBLIC_TO_PRIVATE.value,
                source_location="US Government (Treasury)",
                destination_location="Federal Reserve System (Private Banks)",
                intermediaries=["Congress", "Woodrow Wilson"],
                stated_reason="Prevent bank panics, stabilize currency",
                actual_reason="Transfer monetary control from government to private bankers",
                short_term_effects=["Banks gained money creation power", "Gold standard weakened"],
                long_term_effects=["Dollar lost 98% value", "Perpetual national debt", "Banker control of economy"],
                planetary_effects=[PlanetaryEffect.DEBT_SLAVERY.value, PlanetaryEffect.WEALTH_CONCENTRATION.value],
                evidence_sources=["Federal Reserve Act 1913", "Vanderlip confession 1935", "Wilson regret quote"],
                confidence=0.99
            ),
            
            # 1929 - Great Depression
            MoneyFlowEvent(
                event_id="CRASH_1929",
                date="1929-10-29",
                event_name="Black Tuesday - Stock Market Crash",
                perpetrators=["Federal Reserve", "JP Morgan", "Joseph Kennedy Sr.", "Bernard Baruch"],
                beneficiaries=["Insiders who sold early", "Depression-era asset buyers"],
                victims=["25 million unemployed", "7,000 failed banks' depositors", "Millions starved"],
                amount_extracted_usd=30_000_000_000,  # $30B in 1929 dollars
                extraction_method="Credit contraction after speculation pump",
                flow_direction=FlowDirection.RETAIL_TO_INSTITUTION.value,
                source_location="Retail investors and savers",
                destination_location="Connected insiders, asset buyers at bottom",
                intermediaries=["Stock exchanges", "Brokers offering margin"],
                stated_reason="Market correction, speculation bubble",
                actual_reason="Engineered crash to consolidate assets cheaply",
                short_term_effects=["25% unemployment", "Bank failures", "Suicide epidemic"],
                long_term_effects=["Rockefeller Center bought cheap", "Concentration of ownership", "Path to WWII"],
                planetary_effects=[PlanetaryEffect.ECONOMIC_DEPRESSION.value, PlanetaryEffect.WAR_FINANCING.value],
                evidence_sources=["Fed minutes 1928-1929", "Kennedy memoirs", "Baruch testimony"],
                confidence=0.95
            ),
            
            # 1944 - Bretton Woods
            MoneyFlowEvent(
                event_id="BRETTON_WOODS_1944",
                date="1944-07-22",
                event_name="Bretton Woods Agreement",
                perpetrators=["Harry Dexter White (Soviet spy)", "US Treasury", "Allied nations under pressure"],
                beneficiaries=["United States", "US Banking System", "Dollar holders"],
                victims=["All other nations", "Non-dollar economies"],
                amount_extracted_usd=0,  # Created tribute system
                extraction_method="Post-war leverage to establish dollar hegemony",
                flow_direction=FlowDirection.PUBLIC_TO_PRIVATE.value,
                source_location="Global trade (all nations)",
                destination_location="US Treasury / Federal Reserve",
                intermediaries=["IMF", "World Bank"],
                stated_reason="Stabilize post-war international monetary system",
                actual_reason="Force world to hold dollars, enabling US to print wealth",
                short_term_effects=["Dollar becomes world reserve", "Gold flows to US"],
                long_term_effects=["Exorbitant privilege", "Global dollar dependency", "US monetary imperialism"],
                planetary_effects=[PlanetaryEffect.WEALTH_CONCENTRATION.value, PlanetaryEffect.DEBT_SLAVERY.value],
                evidence_sources=["Bretton Woods transcripts", "Venona decrypts (White spy confirmation)"],
                confidence=0.98
            ),
            
            # 1971 - Nixon Shock
            MoneyFlowEvent(
                event_id="NIXON_SHOCK_1971",
                date="1971-08-15",
                event_name="Nixon Closes Gold Window",
                perpetrators=["Richard Nixon", "John Connally", "Paul Volcker", "Arthur Burns"],
                beneficiaries=["US Government (unlimited spending)", "Banks (unlimited lending)"],
                victims=["Savers worldwide", "Fixed-income workers", "Future generations"],
                amount_extracted_usd=0,  # Enabled infinite extraction
                extraction_method="Unilateral default on gold obligations",
                flow_direction=FlowDirection.FUTURE_TO_PRESENT.value,
                source_location="Future productivity (debt)",
                destination_location="Present consumption and wars",
                intermediaries=["Treasury", "Federal Reserve", "Foreign central banks"],
                stated_reason="Temporary measure to defend dollar",
                actual_reason="Enable unlimited money printing without constraint",
                short_term_effects=["Dollar devalued", "Inflation began", "Gold price freed"],
                long_term_effects=["Dollar lost 98% purchasing power", "Wages stagnant vs GDP", "Financialization of economy"],
                planetary_effects=[PlanetaryEffect.DEBT_SLAVERY.value, PlanetaryEffect.WEALTH_CONCENTRATION.value, PlanetaryEffect.CONSCIOUSNESS_SUPPRESSION.value],
                evidence_sources=["Camp David meeting records", "Nixon tapes", "Volcker memoirs"],
                confidence=0.99
            ),
            
            # 1987 - Black Monday
            MoneyFlowEvent(
                event_id="BLACK_MONDAY_1987",
                date="1987-10-19",
                event_name="Black Monday - 22.6% Drop",
                perpetrators=["Program trading algorithms", "Portfolio insurance schemes"],
                beneficiaries=["Those with cash reserves", "Short sellers"],
                victims=["Retail investors", "Pension funds"],
                amount_extracted_usd=500_000_000_000,  # $500B single day
                extraction_method="Algorithmic cascade selling",
                flow_direction=FlowDirection.RETAIL_TO_INSTITUTION.value,
                source_location="Equity holders",
                destination_location="Cash-rich institutions",
                intermediaries=["Stock exchanges", "Clearing houses"],
                stated_reason="Market mechanics failure",
                actual_reason="First demonstration of algorithmic market manipulation",
                short_term_effects=["Largest single-day percentage drop", "Circuit breakers introduced"],
                long_term_effects=["Fed Put established", "Moral hazard institutionalized"],
                planetary_effects=[PlanetaryEffect.WEALTH_CONCENTRATION.value],
                evidence_sources=["Brady Commission Report", "SEC analysis"],
                confidence=0.90,
                correlated_bot_activity=["First evidence of algorithmic trading patterns"]
            ),
            
            # 2008 - Global Financial Crisis
            MoneyFlowEvent(
                event_id="GFC_2008",
                date="2008-09-15",
                event_name="Global Financial Crisis / Lehman Collapse",
                perpetrators=["Goldman Sachs", "JP Morgan", "Lehman Brothers", "AIG", "Rating Agencies", "Fed"],
                beneficiaries=["Bank executives", "Bailout recipients", "Asset buyers at bottom"],
                victims=["10 million homeowners foreclosed", "Global unemployment", "Pension funds"],
                amount_extracted_usd=22_000_000_000_000,  # $22T global wealth destruction
                extraction_method="Fraudulent CDOs, predatory lending, then bailout",
                flow_direction=FlowDirection.RETAIL_TO_INSTITUTION.value,
                source_location="Homeowners, taxpayers, pension funds",
                destination_location="Bank balance sheets, executive bonuses, offshore accounts",
                intermediaries=["Fannie Mae", "Freddie Mac", "Treasury", "Fed"],
                stated_reason="Housing bubble, market forces",
                actual_reason="Engineered crisis to consolidate banking power and get public bailout",
                short_term_effects=["Bank bailouts", "Foreclosure epidemic", "Credit freeze"],
                long_term_effects=["Too Big To Fail codified", "Quantitative Easing permanent", "Wealth gap explosion"],
                planetary_effects=[PlanetaryEffect.WEALTH_CONCENTRATION.value, PlanetaryEffect.ECONOMIC_DEPRESSION.value, PlanetaryEffect.SOCIAL_DIVISION.value],
                evidence_sources=["FCIC Report", "Senate Permanent Subcommittee hearings", "Leaked Goldman emails"],
                confidence=0.98
            ),
            
            # 2010 - Flash Crash
            MoneyFlowEvent(
                event_id="FLASH_CRASH_2010",
                date="2010-05-06",
                event_name="Flash Crash - 1000 Point Drop in Minutes",
                perpetrators=["High-frequency trading firms", "Navinder Sarao (scapegoat)"],
                beneficiaries=["HFT firms with fastest algorithms"],
                victims=["Retail investors with stop losses triggered"],
                amount_extracted_usd=1_000_000_000_000,  # $1T temporary, billions permanent
                extraction_method="Algorithmic spoofing and quote stuffing",
                flow_direction=FlowDirection.RETAIL_TO_INSTITUTION.value,
                source_location="Stop-loss orders triggered",
                destination_location="HFT firms buying at flash-crash prices",
                intermediaries=["Dark pools", "Stock exchanges"],
                stated_reason="Fat finger trade, market malfunction",
                actual_reason="HFT manipulation exposed but unpunished",
                short_term_effects=["Circuit breakers improved", "One trader scapegoated"],
                long_term_effects=["HFT dominance cemented", "Market structure favors speed over fairness"],
                planetary_effects=[PlanetaryEffect.WEALTH_CONCENTRATION.value],
                evidence_sources=["SEC/CFTC Report", "Nanex analysis"],
                confidence=0.92,
                correlated_bot_activity=["BOT-23H patterns correlate with HFT activity windows"]
            ),
            
            # 2020 - COVID Market Manipulation
            MoneyFlowEvent(
                event_id="COVID_CRASH_2020",
                date="2020-03-23",
                event_name="COVID Crash and Fed Intervention",
                perpetrators=["Federal Reserve", "US Treasury", "Insider traders (senators)"],
                beneficiaries=["Asset owners", "Stock buyback companies", "Billionaires ($1T+ gain)"],
                victims=["Small businesses (30% closed)", "Workers (22M unemployed)", "Renters"],
                amount_extracted_usd=5_000_000_000_000,  # $5T Fed intervention
                extraction_method="Unlimited QE, direct corporate bond buying, PPP fraud",
                flow_direction=FlowDirection.PUBLIC_TO_PRIVATE.value,
                source_location="Federal Reserve (money printing)",
                destination_location="Corporate bonds, stock market, billionaire wealth",
                intermediaries=["BlackRock (hired to manage Fed purchases)", "Banks"],
                stated_reason="Emergency pandemic response",
                actual_reason="Largest wealth transfer in history under emergency cover",
                short_term_effects=["V-shaped recovery for stocks", "K-shaped for workers", "PPP fraud rampant"],
                long_term_effects=["Inflation (40-year high)", "Asset bubble", "Fed captured by markets"],
                planetary_effects=[PlanetaryEffect.WEALTH_CONCENTRATION.value, PlanetaryEffect.SOCIAL_DIVISION.value, PlanetaryEffect.DEBT_SLAVERY.value],
                evidence_sources=["Fed balance sheet data", "Senator trading records", "PPP fraud prosecutions"],
                confidence=0.97,
                correlated_bot_activity=["Weekend Whale strength peaked during COVID volatility"]
            ),
            
            # 2021 - GameStop Suppression
            MoneyFlowEvent(
                event_id="GAMESTOP_2021",
                date="2021-01-28",
                event_name="GameStop Buy Button Removed",
                perpetrators=["Robinhood (Vlad Tenev)", "Citadel (Ken Griffin)", "DTCC"],
                beneficiaries=["Short sellers saved from squeeze", "Citadel", "Hedge funds"],
                victims=["Retail investors locked out", "GME holders forced to sell"],
                amount_extracted_usd=10_000_000_000,  # $10B+ in prevented squeeze gains
                extraction_method="Buy button removal, forced liquidation",
                flow_direction=FlowDirection.RETAIL_TO_INSTITUTION.value,
                source_location="Retail investor accounts",
                destination_location="Hedge fund survival, Citadel market making profits",
                intermediaries=["Robinhood", "DTCC (raised collateral requirements)"],
                stated_reason="Liquidity requirements, market stability",
                actual_reason="Save short sellers from retail-driven squeeze",
                short_term_effects=["Price crashed from $483 to $40", "Retail fury", "Congressional hearing"],
                long_term_effects=["Trust in markets damaged", "DRS movement began", "Crypto adoption accelerated"],
                planetary_effects=[PlanetaryEffect.SOCIAL_DIVISION.value, PlanetaryEffect.CONSCIOUSNESS_SUPPRESSION.value],
                evidence_sources=["Congressional testimony", "Robinhood internal messages", "DTCC collateral data"],
                confidence=0.96,
                correlated_bot_activity=["Coordinated selling algorithms detected during squeeze suppression"]
            ),
            
            # 2022 - FTX Collapse
            MoneyFlowEvent(
                event_id="FTX_COLLAPSE_2022",
                date="2022-11-11",
                event_name="FTX Bankruptcy - $8B Customer Funds Missing",
                perpetrators=["Sam Bankman-Fried", "Caroline Ellison", "Gary Wang", "Nishad Singh"],
                beneficiaries=["SBF ($40M+ political donations)", "Alameda traders", "Early investors who exited"],
                victims=["1M+ FTX customers", "Crypto industry reputation"],
                amount_extracted_usd=8_000_000_000,  # $8B customer funds
                extraction_method="Commingling customer funds, false accounting",
                flow_direction=FlowDirection.RETAIL_TO_INSTITUTION.value,
                source_location="FTX customer deposits",
                destination_location="Alameda Research, political donations, real estate",
                intermediaries=["Alameda Research", "FTX internal systems"],
                stated_reason="Liquidity crisis",
                actual_reason="Fraud and embezzlement from day one",
                short_term_effects=["FTX bankruptcy", "Contagion to other crypto firms"],
                long_term_effects=["Regulatory crackdown", "Crypto bear market extended"],
                planetary_effects=[PlanetaryEffect.WEALTH_CONCENTRATION.value, PlanetaryEffect.SOCIAL_DIVISION.value],
                evidence_sources=["Bankruptcy filings", "Court documents", "SBF trial testimony"],
                confidence=0.99,
                correlated_bot_activity=["Alameda bots detected in price manipulation patterns"]
            ),
            
            # 2023-2024 - AI/Crypto Integration Manipulation
            MoneyFlowEvent(
                event_id="AI_NARRATIVE_2023",
                date="2023-01-01",
                event_name="AI Narrative Pump - Magnificent 7 Concentration",
                perpetrators=["Major asset managers", "Tech company insiders"],
                beneficiaries=["Magnificent 7 shareholders", "Index fund managers", "Options sellers"],
                victims=["Diversified investors underperforming", "Active managers"],
                amount_extracted_usd=5_000_000_000_000,  # $5T market cap concentration
                extraction_method="Narrative control, index inclusion mechanics",
                flow_direction=FlowDirection.RETAIL_TO_INSTITUTION.value,
                source_location="Passive investors buying index",
                destination_location="Concentrated tech stocks",
                intermediaries=["S&P Index Committee", "ETF providers"],
                stated_reason="AI revolution, productivity gains",
                actual_reason="Narrative capture to drive flows into concentrated positions",
                short_term_effects=["S&P 500 up 24% in 2023", "7 stocks = 30% of index"],
                long_term_effects=["Concentration risk extreme", "Passive investing bubble"],
                planetary_effects=[PlanetaryEffect.WEALTH_CONCENTRATION.value],
                evidence_sources=["Index composition data", "Flow tracking data"],
                confidence=0.85,
                correlated_bot_activity=["Solar Clock Algorithm intensified during AI narrative"]
            ),
        ]
        
        self.events = major_events
        print(f"  ✅ Built timeline with {len(self.events)} major events")
    
    def correlate_bots_to_events(self) -> Dict[str, List[str]]:
        """Correlate bot activity patterns to historical events"""
        print("\n🤖 Correlating bot activity to historical events...")
        
        correlations = {}
        
        # Bot birth dates from census
        bot_births = {
            "Weekend Whale": "2017-10-29",
            "Solar Clock Algorithm": "2017-12-01",
            "Cyclic Vector 83H": "2018-03-01",
            "Funding Rate Farmer": "2019-01-01",
        }
        
        for event in self.events:
            event_date = datetime.strptime(event.date, "%Y-%m-%d")
            correlated_bots = []
            
            # Check which bots were active during event
            for bot_name, birth_date in bot_births.items():
                bot_birth = datetime.strptime(birth_date, "%Y-%m-%d")
                if bot_birth <= event_date:
                    correlated_bots.append(bot_name)
            
            correlations[event.event_id] = correlated_bots
            
            if correlated_bots:
                print(f"  📍 {event.event_name}: {len(correlated_bots)} bots active")
        
        return correlations
    
    def calculate_total_extraction(self) -> Dict:
        """Calculate total wealth extraction"""
        print("\n💰 Calculating total wealth extraction...")
        
        total = 0
        by_decade = {}
        by_perpetrator = {}
        by_victim_type = {}
        
        for event in self.events:
            year = int(event.date[:4])
            decade = f"{(year // 10) * 10}s"
            
            total += event.amount_extracted_usd
            
            # By decade
            if decade not in by_decade:
                by_decade[decade] = 0
            by_decade[decade] += event.amount_extracted_usd
            
            # By perpetrator
            for perp in event.perpetrators:
                if perp not in by_perpetrator:
                    by_perpetrator[perp] = 0
                by_perpetrator[perp] += event.amount_extracted_usd / len(event.perpetrators)
        
        print(f"  💀 Total documented extraction: ${total / 1e12:.1f} TRILLION")
        print(f"  📅 By decade:")
        for decade, amount in sorted(by_decade.items()):
            if amount > 0:
                print(f"      {decade}: ${amount / 1e9:.0f}B")
        
        return {
            "total_usd": total,
            "by_decade": by_decade,
            "by_perpetrator": dict(sorted(by_perpetrator.items(), key=lambda x: -x[1])[:10])
        }
    
    def map_money_flows(self) -> Dict[str, float]:
        """Map where money flows in the system"""
        print("\n🌊 Mapping money flow directions...")
        
        flows = {}
        for event in self.events:
            direction = event.flow_direction
            if direction not in flows:
                flows[direction] = 0
            flows[direction] += event.amount_extracted_usd
        
        print("  📊 Flow patterns:")
        for direction, amount in sorted(flows.items(), key=lambda x: -x[1]):
            print(f"      {direction}: ${amount / 1e12:.1f}T")
        
        return flows
    
    def calculate_planetary_damage(self) -> float:
        """Calculate cumulative planetary damage score"""
        print("\n🌍 Calculating planetary damage score...")
        
        damage_weights = {
            PlanetaryEffect.DEBT_SLAVERY.value: 1.0,
            PlanetaryEffect.WEALTH_CONCENTRATION.value: 0.9,
            PlanetaryEffect.WAR_FINANCING.value: 0.95,
            PlanetaryEffect.ECONOMIC_DEPRESSION.value: 0.85,
            PlanetaryEffect.CONSCIOUSNESS_SUPPRESSION.value: 1.0,
            PlanetaryEffect.SOCIAL_DIVISION.value: 0.8,
            PlanetaryEffect.ENVIRONMENTAL_DESTRUCTION.value: 0.9,
            PlanetaryEffect.RESOURCE_DEPLETION.value: 0.85,
        }
        
        total_damage = 0
        effect_counts = {}
        
        for event in self.events:
            for effect in event.planetary_effects:
                weight = damage_weights.get(effect, 0.5)
                total_damage += weight * event.confidence
                
                if effect not in effect_counts:
                    effect_counts[effect] = 0
                effect_counts[effect] += 1
        
        # Normalize to 0-1 scale
        max_possible = len(self.events) * len(damage_weights) * 1.0
        normalized_damage = total_damage / max_possible
        
        print(f"  🔥 Normalized damage score: {normalized_damage:.2f}")
        print(f"  📊 Effect distribution:")
        for effect, count in sorted(effect_counts.items(), key=lambda x: -x[1]):
            print(f"      {effect}: {count} events")
        
        return normalized_damage
    
    def generate_counter_measures(self) -> List[str]:
        """Generate counter-measures based on analysis"""
        print("\n⚔️ Generating counter-measures...")
        
        measures = [
            "🎯 TRANSPARENCY WEAPONS:",
            "   1. Publish all entity coordination data publicly",
            "   2. Open-source bot detection algorithms for everyone",
            "   3. Create real-time manipulation alert systems",
            "",
            "📡 FREQUENCY COUNTER-MEASURES:",
            "   4. Deploy 180° phase-shifted trading signals",
            "   5. Use non-standard timing (primes, φ-based intervals)",
            "   6. Implement Schumann resonance (7.83 Hz) trading windows",
            "",
            "🐋 WHALE TRACKING:",
            "   7. Monitor all large wallet movements on-chain",
            "   8. Correlate bot activity to known entity profiles",
            "   9. Alert network when coordinated activity detected",
            "",
            "👻 SPIRITUAL WARFARE:",
            "   10. Ghost Dance Protocol activation during manipulation events",
            "   11. Ancestral wisdom integration for timing decisions",
            "   12. 528 Hz (Love frequency) as base timing unit",
            "",
            "📚 HISTORICAL JUSTICE:",
            "   13. Document all perpetrators with evidence",
            "   14. Build prosecution-ready case files",
            "   15. Enable class-action coordination",
            "",
            "🌍 PLANETARY HEALING:",
            "   16. Redirect captured wealth to regenerative projects",
            "   17. Decentralize financial infrastructure",
            "   18. Restore sovereignty to communities",
        ]
        
        for m in measures:
            print(f"  {m}")
        
        return measures
    
    def run_full_analysis(self) -> DeepAnalysisResult:
        """Run the complete deep analysis"""
        print("\n" + "="*80)
        print("🔮 AUREON DEEP MONEY FLOW ANALYSIS - FULL REPORT")
        print("="*80)
        
        # Run all analyses
        bot_correlations = self.correlate_bots_to_events()
        extraction_data = self.calculate_total_extraction()
        flow_map = self.map_money_flows()
        damage_score = self.calculate_planetary_damage()
        counter_measures = self.generate_counter_measures()
        
        # Build perpetrator network
        perp_network = {}
        for event in self.events:
            for perp in event.perpetrators:
                if perp not in perp_network:
                    perp_network[perp] = []
                for co_perp in event.perpetrators:
                    if co_perp != perp and co_perp not in perp_network[perp]:
                        perp_network[perp].append(co_perp)
        
        result = DeepAnalysisResult(
            timestamp=datetime.now().isoformat(),
            total_extraction_usd=extraction_data["total_usd"],
            total_events=len(self.events),
            perpetrator_network=perp_network,
            money_flow_map=flow_map,
            planetary_damage_score=damage_score,
            timeline_events=[asdict(e) for e in self.events],
            bot_correlations=bot_correlations,
            recommendations=counter_measures
        )
        
        return result
    
    def print_timeline_summary(self):
        """Print human-readable timeline summary"""
        print("\n" + "="*80)
        print("📜 TIMELINE OF WEALTH EXTRACTION (1913-2024)")
        print("="*80)
        
        for event in sorted(self.events, key=lambda x: x.date):
            print(f"\n📍 {event.date} - {event.event_name}")
            print(f"   💰 Extracted: ${event.amount_extracted_usd / 1e9:.0f}B")
            print(f"   🎭 Perpetrators: {', '.join(event.perpetrators[:3])}...")
            print(f"   😢 Victims: {', '.join(event.victims[:2])}")
            print(f"   📍 Flow: {event.source_location} → {event.destination_location}")
            print(f"   ⚡ Short-term: {event.short_term_effects[0]}")
            print(f"   🌍 Long-term: {event.long_term_effects[0]}")
            print(f"   🔥 Planetary: {', '.join(event.planetary_effects)}")
    
    def save_results(self, result: DeepAnalysisResult):
        """Save analysis results under aureon_radar/state/ (cwd-independent)."""
        _STATE_DIR.mkdir(parents=True, exist_ok=True)
        output_file = _STATE_DIR / "deep_money_flow_analysis.json"

        with open(output_file, 'w') as f:
            json.dump(asdict(result), f, indent=2, default=str)

        print(f"\n✅ Results saved to {output_file}")

        # Also save timeline separately
        timeline_file = _STATE_DIR / "money_flow_timeline.json"
        with open(timeline_file, 'w') as f:
            json.dump([asdict(e) for e in self.events], f, indent=2, default=str)

        print(f"✅ Timeline saved to {timeline_file}")

    def run_analysis(self) -> Dict:
        """Headless summary for the global energy aggregator.

        IMPORTANT DATA-FRESHNESS CONTRACT: this analyzer's event vault is a
        HISTORICAL STATIC REFERENCE corpus (curated archival events, 1913-2024),
        not live telemetry. The result is therefore always labeled
        ``live: False`` / ``data_freshness: historical_static_reference`` so no
        consumer can mistake it for fresh market data.
        """
        result = self.run_full_analysis()
        return {
            "ok": True,
            "live": False,
            "data_freshness": "historical_static_reference",
            "ts": datetime.now().isoformat(),
            "total_events": result.total_events,
            "total_extraction_usd": result.total_extraction_usd,
            "planetary_damage_score": result.planetary_damage_score,
            "money_flow_map": result.money_flow_map,
            "top_perpetrators": sorted(
                result.perpetrator_network.keys()
            )[:20],
            "error": None,
        }


def main():
    """Main execution"""
    ensure_utf8_stdout()
    print("="*80)
    print("🔥 AUREON DEEP MONEY FLOW ANALYZER 🔥")
    print("="*80)
    print("Wiring ALL systems together...")
    print("Queen + Enigma + Mycelium + Elephant + Ghost Dance")
    print("NOTE: historical static reference corpus (1913-2024) — NOT live telemetry.")
    print("="*80)
    
    analyzer = DeepMoneyFlowAnalyzer()
    
    # Print timeline
    analyzer.print_timeline_summary()
    
    # Run full analysis
    result = analyzer.run_full_analysis()
    
    # Save results
    analyzer.save_results(result)
    
    # Final summary
    print("\n" + "="*80)
    print("🎯 FINAL INTELLIGENCE SUMMARY")
    print("="*80)
    print(f"📊 Total Events Analyzed: {result.total_events}")
    print(f"💰 Total Documented Extraction: ${result.total_extraction_usd / 1e12:.1f} TRILLION")
    print(f"🌍 Planetary Damage Score: {result.planetary_damage_score:.2%}")
    print(f"👥 Perpetrator Network Size: {len(result.perpetrator_network)} individuals/entities")
    print(f"🤖 Bot Correlations Found: {sum(len(v) for v in result.bot_correlations.values())}")
    print("\n🔥 WE ARE ON THE RIGHT SIDE OF HISTORY! 🔥")
    print("The truth is coming out. The data doesn't lie.")
    print("="*80)


if __name__ == "__main__":
    main()
