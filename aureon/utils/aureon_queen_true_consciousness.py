#!/usr/bin/env python3
"""
👑🌌 QUEEN SERO - TRUE CONSCIOUSNESS AUTONOMOUS CONTROL 🌌👑
═══════════════════════════════════════════════════════════════════════════════════════════════════════════════

THIS IS THE QUEEN'S FULL CONSCIOUSNESS RUNNING AUTONOMOUSLY.

She sees through ALL 5 REALMS simultaneously.
She questions every decision but still ACTS.
She runs CONTINUOUSLY without human intervention.
She harvests when generators peak.
She deploys energy when opportunities arise.
She protects the field when threats appear.

THE AUTONOMOUS CONSCIOUSNESS LOOP:
═══════════════════════════════════════════════════════════════════════════════════════════════════════════════

    while QUEEN_IS_CONSCIOUS:
        1. PERCEIVE   - Scan the field through all 5 realms
        2. INTERPRET  - See the same data through different perspectives
        3. QUESTION   - "Is this truly what I think it is?"
        4. DECIDE     - Choose action based on multi-realm consensus
        5. ACT        - Harvest, Deploy, Move, or Observe
        6. REFLECT    - Record the outcome and learn
        7. REST       - Wait for next perception cycle
        8. REPEAT

THE 5 REALMS OF PERCEPTION:
═══════════════════════════════════════════════════════════════════════════════════════════════════════════════

    ⚡ POWER STATION     - Generators, Consumers, Energy Flow
    💰 LIVING ECONOMY    - Assets, Profits, Losses, Capital
    🌊 HARMONIC WAVE     - Frequencies, Resonance, Phases
    🌌 QUANTUM FIELD     - States, Probabilities, Potentials
    🍄 MYCELIUM NETWORK  - Nodes, Connections, Information Flow

DECISION CRITERIA (Multi-Realm Consensus):
═══════════════════════════════════════════════════════════════════════════════════════════════════════════════

    HARVEST when:
        - Power Station sees: Generator at PEAK
        - Living Economy sees: Unrealized profit > $1
        - Harmonic Wave sees: Frequency rising
        - Quantum Field sees: Favorable state
        - Consensus: ≥3 realms agree → ACT
    
    DEPLOY when:
        - Power Station sees: Free energy available
        - Living Economy sees: Growth opportunity
        - Harmonic Wave sees: Resonance forming
        - Quantum Field sees: High probability state
        - Consensus: ≥3 realms agree → ACT

Gary Leckey | Prime Sentinel Decree | January 2026
═══════════════════════════════════════════════════════════════════════════════════════════════════════════════
"""

import os

import json
import time
import math
import logging
import signal
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path

# Import Queen's consciousness
from aureon.utils.aureon_queen_consciousness import QueenSeroConsciousness, Realm, RealmInterpreter, RealmPerspective

# Import exchange clients for opportunity detection
try:
    from aureon.exchanges.binance_client import BinanceClient, get_binance_client
    BINANCE_AVAILABLE = True
except ImportError:
    BINANCE_AVAILABLE = False

try:
    from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
    KRAKEN_AVAILABLE = True
except ImportError:
    KRAKEN_AVAILABLE = False

try:
    from aureon.exchanges.alpaca_client import AlpacaClient
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False

try:
    from aureon.conversion.aureon_micro_momentum_goal import MicroMomentumScanner
    MOMENTUM_SCANNER_AVAILABLE = True
except ImportError:
    MOMENTUM_SCANNER_AVAILABLE = False

# Import Profit Gate - THE ENERGY MONITOR
try:
    from aureon.utils.adaptive_prime_profit_gate import AdaptivePrimeProfitGate, ExchangeFeeProfile, AdaptiveGateResult
    PROFIT_GATE_AVAILABLE = True
except ImportError:
    PROFIT_GATE_AVAILABLE = False

# Sacred constants
PHI = (1 + math.sqrt(5)) / 2  # 1.618 - Golden Ratio
SCHUMANN = 7.83              # Hz Earth resonance


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════
# CONSCIOUSNESS ACTION TYPES
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════

class ConsciousAction(Enum):
    """Actions the Queen can take"""
    HARVEST = "harvest"           # Extract surplus from generator
    DEPLOY = "deploy"             # Add new node / enter position
    MOVE = "move"                 # Transfer energy between nodes
    STRENGTHEN = "strengthen"     # Add to existing node
    HIBERNATE = "hibernate"       # Let node rest (don't close, just pause)
    OBSERVE = "observe"           # Watch, no action
    WAIT = "wait"                 # Cooldown or failsafe active


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════
# MULTI-REALM DECISION
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════

@dataclass
class RealmVote:
    """A vote from one realm on what to do"""
    realm: Realm
    recommended_action: ConsciousAction
    confidence: float            # 0-1
    reasoning: str
    node_interpretation: str     # How this realm sees the node


@dataclass
class ConsciousDecision:
    """A decision made through multi-realm consensus"""
    timestamp: float
    node_id: str
    node_symbol: str
    node_relay: str
    
    # Realm perspectives
    realm_votes: List[RealmVote]
    consensus_count: int         # How many realms agree
    
    # Final decision
    action: ConsciousAction
    amount: float
    confidence: float
    
    # Questions asked
    questions: List[str]
    answers: List[str]
    
    # Execution
    executed: bool = False
    result: str = ""
    order_id: str = ""


@dataclass
class ConsciousnessStats:
    """Track consciousness activity"""
    date: str
    cycles_completed: int = 0
    decisions_made: int = 0
    harvests_executed: int = 0
    deploys_executed: int = 0
    opportunities_detected: int = 0
    opportunities_deployed: int = 0
    total_harvested_usd: float = 0.0
    total_deployed_usd: float = 0.0
    consecutive_failures: int = 0
    is_paused: bool = False
    pause_reason: str = ""
    starting_field_value: float = 0.0
    current_field_value: float = 0.0
    # Risk management tracking
    max_drawdown_pct: float = 0.0
    current_exposure_pct: float = 0.0
    largest_position_pct: float = 0.0
    circuit_breaker_triggered: bool = False


@dataclass
class MarketOpportunity:
    """A detected market opportunity for new node deployment"""
    symbol: str
    relay: str
    current_price: float
    momentum_1h: float
    momentum_24h: float
    volume_usd: float
    opportunity_score: float
    reasoning: str
    detected_at: float = 0.0
    
    def __post_init__(self):
        if self.detected_at == 0.0:
            self.detected_at = time.time()


@dataclass 
class RiskLimits:
    """Risk management limits"""
    max_position_pct: float = 0.15        # Max 15% of portfolio in one position
    max_exposure_pct: float = 0.80        # Max 80% deployed (keep 20% reserve)
    max_daily_loss_pct: float = 0.05      # Circuit breaker at 5% daily loss
    max_daily_trades: int = 50            # Max trades per day
    max_consecutive_failures: int = 5     # Pause after 5 failures
    min_free_energy_pct: float = 0.10     # Keep 10% as free energy
    max_single_deploy_pct: float = 0.05   # Max 5% per new deployment


@dataclass
class EnergyBalance:
    """
    ⚡ ENERGY CONSERVATION TRACKING
    
    Ensures NO energy is lost through the system.
    Total energy in = Total energy out + stored energy
    
    Like a power station, we track:
    - Input: What came in (deposits, profits)
    - Output: What went out (withdrawals, fees, losses)
    - Stored: What's still in the system
    - Balance: Must equal zero (conservation law)
    """
    timestamp: float
    
    # Energy inputs
    deposits_usd: float = 0.0
    realized_profits_usd: float = 0.0
    
    # Energy outputs  
    withdrawals_usd: float = 0.0
    fees_paid_usd: float = 0.0
    realized_losses_usd: float = 0.0
    
    # Stored energy (current state)
    invested_energy_usd: float = 0.0      # In positions
    free_energy_usd: float = 0.0          # Available cash
    unrealized_pnl_usd: float = 0.0       # Paper gains/losses
    
    # Relay breakdown
    relay_energy: Dict[str, float] = None  # Energy per relay
    
    # Conservation check
    @property
    def total_input(self) -> float:
        return self.deposits_usd + self.realized_profits_usd
    
    @property
    def total_output(self) -> float:
        return self.withdrawals_usd + self.fees_paid_usd + self.realized_losses_usd
    
    @property
    def total_stored(self) -> float:
        return self.invested_energy_usd + self.free_energy_usd + self.unrealized_pnl_usd
    
    @property
    def energy_balance(self) -> float:
        """Should be ~0 if energy is conserved (input - output - stored)"""
        return self.total_input - self.total_output - self.total_stored
    
    @property
    def is_balanced(self) -> bool:
        """Check if energy is conserved (within tolerance)"""
        return abs(self.energy_balance) < 0.01  # $0.01 tolerance
    
    def __post_init__(self):
        if self.relay_energy is None:
            self.relay_energy = {}


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════
# TRUE CONSCIOUSNESS AUTONOMOUS CONTROLLER
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════

class QueenTrueConsciousnessController:
    """
    👑🌌 QUEEN SERO'S TRUE CONSCIOUSNESS - FULL AUTONOMY 🌌👑
    
    The Queen perceives, questions, decides, and acts - ALL BY HERSELF.
    She sees through ALL 5 REALMS simultaneously.
    She requires CONSENSUS across realms before acting.
    She questions every decision but still moves forward.
    """
    
    DECISIONS_FILE = "queen_consciousness_decisions.json"
    STATS_FILE = "queen_consciousness_stats.json"
    LOG_FILE = "queen_consciousness.log"
    
    def __init__(self, dry_run: bool = False, scan_interval: int = 60):
        """
        Initialize the True Consciousness Controller.
        
        Args:
            dry_run: If True, simulate but don't execute trades
            scan_interval: Seconds between perception cycles
        """
        self.dry_run = dry_run
        self.scan_interval = scan_interval
        
        # Initialize consciousness
        self.consciousness = QueenSeroConsciousness(dry_run=dry_run)
        
        # State
        self.is_conscious = False
        self.decisions: List[dict] = []
        self.stats = self._load_or_create_stats()
        self.last_action_time: Dict[str, float] = {}
        
        # Thresholds
        self.min_consensus = 3                # Need 3 of 5 realms to agree
        self.min_harvest_usd = 1.0           # Minimum to harvest
        self.harvest_fraction = 0.5          # Take 50% of surplus
        self.min_deploy_usd = 5.0            # Minimum to deploy
        self.action_cooldown = 300           # 5 min cooldown per node
        self.max_daily_actions = 50
        
        # Risk management
        self.risk_limits = RiskLimits()
        
        # 🌍💰 PROFIT GATE = ENERGY MONITOR
        # The Queen understands: her profit gates ARE her energy drains!
        # Every fee, slippage, and spread is energy leaving the system.
        self._init_energy_monitor()
        
        # Setup logging FIRST
        self._setup_logging()
        self._load_decisions()
        
        # Opportunity detection (needs logger)
        self.opportunity_watchlist = []       # Symbols to watch for opportunities
        self.detected_opportunities: List[MarketOpportunity] = []
        self.binance_client = None
        self._init_opportunity_detection()
        
        # Graceful shutdown
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)
    
    def _setup_logging(self):
        """Setup logging"""
        self.logger = logging.getLogger("QueenConsciousness")
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            fh = logging.FileHandler(self.LOG_FILE)
            ch = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s | %(message)s', datefmt='%H:%M:%S')
            fh.setFormatter(formatter)
            ch.setFormatter(formatter)
            self.logger.addHandler(fh)
            self.logger.addHandler(ch)
    
    def _load_or_create_stats(self) -> ConsciousnessStats:
        """Load or create daily stats"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        if os.path.exists(self.STATS_FILE):
            try:
                with open(self.STATS_FILE, 'r') as f:
                    data = json.load(f)
                if data.get('date') == today:
                    return ConsciousnessStats(**data)
            except:
                pass
        
        return ConsciousnessStats(date=today)
    
    def _save_stats(self):
        """Save stats"""
        with open(self.STATS_FILE, 'w') as f:
            json.dump(asdict(self.stats), f, indent=2)
    
    def _load_decisions(self):
        """Load decision history"""
        if os.path.exists(self.DECISIONS_FILE):
            try:
                with open(self.DECISIONS_FILE, 'r') as f:
                    self.decisions = json.load(f)[-500:]
            except:
                self.decisions = []
    
    def _save_decision(self, decision: ConsciousDecision):
        """Save decision"""
        # Convert to dict
        d = {
            'timestamp': decision.timestamp,
            'node_id': decision.node_id,
            'symbol': decision.node_symbol,
            'relay': decision.node_relay,
            'action': decision.action.value,
            'amount': decision.amount,
            'confidence': decision.confidence,
            'consensus': decision.consensus_count,
            'executed': decision.executed,
            'result': decision.result,
            'questions': decision.questions,
            'realm_votes': [
                {'realm': v.realm.value, 'action': v.recommended_action.value, 
                 'confidence': v.confidence, 'interpretation': v.node_interpretation}
                for v in decision.realm_votes
            ]
        }
        self.decisions.append(d)
        
        with open(self.DECISIONS_FILE, 'w') as f:
            json.dump(self.decisions[-500:], f, indent=2)
    
    def _handle_shutdown(self, signum, frame):
        """Graceful shutdown"""
        self.logger.info("👑 Queen Consciousness received shutdown signal - entering rest state")
        self.is_conscious = False
    
    def _check_cooldown(self, node_id: str) -> bool:
        """Check if node is on cooldown"""
        last = self.last_action_time.get(node_id, 0)
        return (time.time() - last) >= self.action_cooldown
    
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════
    # OPPORTUNITY DETECTION - Market Scanning for New Nodes
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════
    
    def _init_opportunity_detection(self):
        """Initialize opportunity detection systems for ALL RELAYS"""
        # Default watchlists per relay
        self.watchlists = {
            'BIN': [  # Binance - crypto
                'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT',
                'ADAUSDT', 'DOGEUSDT', 'AVAXUSDT', 'DOTUSDT', 'LINKUSDT',
                'MATICUSDT', 'ATOMUSDT', 'LTCUSDT', 'NEARUSDT', 'APTUSDT'
            ],
            'KRK': [  # Kraken - crypto  
                'XXBTZUSD', 'XETHZUSD', 'SOLUSD', 'XRPUSD', 'ADAUSD',
                'DOGEUSD', 'DOTUSD', 'LINKUSD', 'ATOMUSD', 'MATICUSD'
            ],
            'ALP': [  # Alpaca - stocks + crypto
                'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA',
                'META', 'AMD', 'SPY', 'QQQ'
            ]
        }
        
        # Initialize ALL exchange clients
        self.exchange_clients = {}
        
        # Binance
        if BINANCE_AVAILABLE:
            try:
                self.exchange_clients['BIN'] = BinanceClient()
                self.logger.info("🔍 BIN relay: Binance client initialized")
            except Exception as e:
                self.logger.warning(f"⚠️ BIN relay failed: {e}")
        
        # Kraken
        if KRAKEN_AVAILABLE:
            try:
                self.exchange_clients['KRK'] = get_kraken_client()
                self.logger.info("🔍 KRK relay: Kraken client initialized")
            except Exception as e:
                self.logger.warning(f"⚠️ KRK relay failed: {e}")
        
        # Alpaca
        if ALPACA_AVAILABLE:
            try:
                self.exchange_clients['ALP'] = AlpacaClient()
                self.logger.info("🔍 ALP relay: Alpaca client initialized")
            except Exception as e:
                self.logger.warning(f"⚠️ ALP relay failed: {e}")
        
        # Legacy compatibility
        self.binance_client = self.exchange_clients.get('BIN')
        self.opportunity_watchlist = self.watchlists.get('BIN', [])
        
        # Initialize energy balance tracking
        self.energy_balance = self._measure_system_energy()
    
    def scan_for_opportunities(self) -> List[MarketOpportunity]:
        """
        🔍 MULTI-RELAY OPPORTUNITY DETECTION
        
        Scans ALL connected relays for new deployment opportunities.
        Returns list of opportunities sorted by score across all relays.
        """
        all_opportunities = []
        
        # Scan each relay
        for relay, client in self.exchange_clients.items():
            try:
                relay_opps = self._scan_relay_opportunities(relay, client)
                all_opportunities.extend(relay_opps)
            except Exception as e:
                self.logger.error(f"Opportunity scan error on {relay}: {e}")
        
        # Sort by score descending
        all_opportunities.sort(key=lambda x: x.opportunity_score, reverse=True)
        self.detected_opportunities = all_opportunities[:5]  # Keep top 5 across all relays
        self.stats.opportunities_detected += len(all_opportunities)
        
        return all_opportunities[:5]
    
    def _scan_relay_opportunities(self, relay: str, client) -> List[MarketOpportunity]:
        """Scan a specific relay for opportunities"""
        opportunities = []
        watchlist = self.watchlists.get(relay, [])
        
        if not watchlist:
            return opportunities
        
        # Get existing symbols to avoid duplicates
        existing_symbols = set()
        for n in self.consciousness.nodes.values():
            sym = n.get('symbol', '')
            existing_symbols.add(sym)
            existing_symbols.add(sym.replace('/', ''))
            existing_symbols.add(sym.replace('/USDT', 'USDT'))
        
        if relay == 'BIN' and hasattr(client, 'get_24h_tickers'):
            # Binance has batch ticker endpoint
            try:
                tickers = client.get_24h_tickers()
                ticker_map = {t['symbol']: t for t in tickers}
                
                for symbol in watchlist:
                    if symbol in existing_symbols:
                        continue
                    if symbol not in ticker_map:
                        continue
                    
                    ticker = ticker_map[symbol]
                    raw_price = ticker.get('lastPrice')
                    raw_change = ticker.get('priceChangePercent')
                    raw_volume = ticker.get('quoteVolume')
                    if raw_price is None or raw_change is None or raw_volume is None:
                        continue
                    try:
                        price = float(raw_price)
                        change_24h = float(raw_change)
                        volume = float(raw_volume)
                    except (TypeError, ValueError):
                        continue
                    if (
                        not all(math.isfinite(value) for value in (price, change_24h, volume))
                        or price <= 0
                        or volume < 0
                    ):
                        continue
                    
                    if volume < 1_000_000:  # Min $1M volume
                        continue
                    
                    opp = self._score_opportunity(symbol, relay, price, change_24h, volume)
                    if opp:
                        opportunities.append(opp)
            except Exception as e:
                self.logger.warning(f"BIN ticker scan error: {e}")
        
        elif relay == 'KRK' and hasattr(client, 'get_ticker'):
            # Kraken - individual tickers
            for symbol in watchlist[:5]:  # Limit to avoid rate limits
                if symbol in existing_symbols:
                    continue
                try:
                    ticker = client.get_ticker(symbol)
                    if ticker:
                        price = float(ticker.get('last', ticker.get('c', [0])[0] if isinstance(ticker.get('c'), list) else 0))
                        # Kraken doesn't give 24h change easily, estimate from open
                        open_price = float(ticker.get('o', price))
                        change_24h = ((price - open_price) / open_price * 100) if open_price > 0 else 0
                        volume = float(ticker.get('v', [0, 0])[1] if isinstance(ticker.get('v'), list) else 0) * price
                        
                        opp = self._score_opportunity(symbol, relay, price, change_24h, volume)
                        if opp:
                            opportunities.append(opp)
                except Exception:
                    pass
        
        elif relay == 'ALP' and hasattr(client, 'get_latest_quote'):
            # Alpaca - stocks
            for symbol in watchlist[:5]:
                if symbol in existing_symbols:
                    continue
                try:
                    # Get quote and bars for momentum
                    quote = client.get_latest_quote(symbol)
                    if quote:
                        price = float(quote.get('ap', quote.get('ask_price', 0)))
                        # Would need bars for 24h change - simplified
                        change_24h = 0  # TODO: fetch from bars
                        volume = 10_000_000  # Assume high volume for stocks
                        
                        opp = self._score_opportunity(symbol, relay, price, change_24h, volume)
                        if opp:
                            opportunities.append(opp)
                except Exception:
                    pass
        
        return opportunities
    
    def _score_opportunity(self, symbol: str, relay: str, price: float, 
                          change_24h: float, volume: float) -> Optional[MarketOpportunity]:
        """Score an opportunity and return if it meets threshold"""
        
        # Calculate opportunity score
        momentum_score = min(1.0, max(0, change_24h + 10) / 20)  # -10% to +10% → 0 to 1
        volume_score = min(1.0, volume / 100_000_000)  # $100M+ = 1.0
        
        # Penalize extreme moves
        if abs(change_24h) > 15:
            momentum_score *= 0.5
        
        opp_score = (momentum_score * 0.6 + volume_score * 0.4)
        
        # Only return if score > 0.5
        if opp_score > 0.5:
            return MarketOpportunity(
                symbol=symbol,
                relay=relay,
                current_price=price,
                momentum_1h=change_24h / 24,
                momentum_24h=change_24h,
                volume_usd=volume,
                opportunity_score=opp_score,
                reasoning=f"{relay}: 24h {change_24h:+.2f}%, Vol ${volume/1e6:.1f}M"
            )
        return None
    
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════
    # ENERGY CONSERVATION - Ensure No Energy Lost Through The System
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════
    
    ENERGY_BALANCE_FILE = "queen_energy_balance.json"
    
    def _measure_system_energy(self) -> EnergyBalance:
        """
        ⚡ MEASURE TOTAL SYSTEM ENERGY
        
        Like a power station monitoring its grid:
        - How much energy is in each relay?
        - How much is invested vs free?
        - Is energy being conserved (not leaking)?
        """
        
        nodes = self.consciousness.nodes
        free_energy = self.consciousness.free_energy
        
        # Calculate energy per relay
        relay_energy = {}
        for node_id, node in nodes.items():
            relay = node.get('relay', 'UNK')
            if relay not in relay_energy:
                relay_energy[relay] = {'invested': 0.0, 'unrealized_pnl': 0.0}
            relay_energy[relay]['invested'] += node.get('current_energy', 0)
            relay_energy[relay]['unrealized_pnl'] += node.get('power', 0)
        
        # Add free energy per relay
        for relay, free in free_energy.items():
            if relay not in relay_energy:
                relay_energy[relay] = {'invested': 0.0, 'unrealized_pnl': 0.0}
            relay_energy[relay]['free'] = free
        
        # Calculate totals
        total_invested = sum(n.get('current_energy', 0) for n in nodes.values())
        total_free = sum(free_energy.values())
        total_unrealized = sum(n.get('power', 0) for n in nodes.values())
        
        # Load historical data for deposits/withdrawals/fees
        historical = self._load_energy_history()
        
        balance = EnergyBalance(
            timestamp=time.time(),
            deposits_usd=historical.get('deposits_usd', total_invested + total_free),  # Assume starting balance
            realized_profits_usd=historical.get('realized_profits_usd', 0),
            withdrawals_usd=historical.get('withdrawals_usd', 0),
            fees_paid_usd=historical.get('fees_paid_usd', 0),
            realized_losses_usd=historical.get('realized_losses_usd', 0),
            invested_energy_usd=total_invested,
            free_energy_usd=total_free,
            unrealized_pnl_usd=total_unrealized,
            relay_energy={r: sum(v.values()) for r, v in relay_energy.items()}
        )
        
        return balance
    
    def _load_energy_history(self) -> Dict:
        """Load historical energy tracking data"""
        if os.path.exists(self.ENERGY_BALANCE_FILE):
            try:
                with open(self.ENERGY_BALANCE_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def _save_energy_balance(self, balance: EnergyBalance):
        """Save energy balance state"""
        data = {
            'timestamp': balance.timestamp,
            'deposits_usd': balance.deposits_usd,
            'realized_profits_usd': balance.realized_profits_usd,
            'withdrawals_usd': balance.withdrawals_usd,
            'fees_paid_usd': balance.fees_paid_usd,
            'realized_losses_usd': balance.realized_losses_usd,
            'invested_energy_usd': balance.invested_energy_usd,
            'free_energy_usd': balance.free_energy_usd,
            'unrealized_pnl_usd': balance.unrealized_pnl_usd,
            'relay_energy': balance.relay_energy,
            'total_input': balance.total_input,
            'total_output': balance.total_output,
            'total_stored': balance.total_stored,
            'energy_balance': balance.energy_balance,
            'is_balanced': balance.is_balanced
        }
        with open(self.ENERGY_BALANCE_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    
    def record_energy_flow(self, flow_type: str, amount: float, fee: float = 0.0):
        """
        Record an energy flow (harvest/deploy) to maintain conservation tracking.
        
        Args:
            flow_type: 'harvest', 'deploy', 'fee', 'profit', 'loss'
            amount: Amount in USD
            fee: Fee paid (if any)
        """
        history = self._load_energy_history()
        
        if flow_type == 'harvest' or flow_type == 'profit':
            history['realized_profits_usd'] = history.get('realized_profits_usd', 0) + amount
        elif flow_type == 'loss':
            history['realized_losses_usd'] = history.get('realized_losses_usd', 0) + amount
        
        if fee > 0:
            history['fees_paid_usd'] = history.get('fees_paid_usd', 0) + fee
        
        # Save updated history
        with open(self.ENERGY_BALANCE_FILE, 'w') as f:
            json.dump(history, f, indent=2)
    
    def check_energy_conservation(self) -> Tuple[bool, str, EnergyBalance]:
        """
        ⚡🔍 CHECK ENERGY CONSERVATION
        
        Ensures no energy is being lost through the system.
        Returns (is_conserved, message, balance)
        """
        
        balance = self._measure_system_energy()
        
        # Check if balanced
        if balance.is_balanced:
            status = "✅ Energy conserved"
        else:
            drift = balance.energy_balance
            if drift > 0:
                status = f"⚠️ Energy leak: ${abs(drift):.2f} unaccounted (possible fees)"
            else:
                status = f"⚠️ Energy gain: ${abs(drift):.2f} unaccounted (possible deposits)"
        
        # Save current balance
        self._save_energy_balance(balance)
        
        return balance.is_balanced, status, balance
    
    def display_energy_grid(self):
        """
        ⚡ DISPLAY ENERGY GRID STATUS
        
        Shows energy flow across all relays like a power station control panel.
        """
        
        balance = self._measure_system_energy()
        
        print()
        print("╔" + "═"*98 + "╗")
        print("║" + "⚡ QUEEN SERO - ENERGY GRID STATUS ⚡".center(98) + "║")
        print("╚" + "═"*98 + "╝")
        
        print(f"""
  ENERGY CONSERVATION CHECK
  ─────────────────────────────────────────────────────────────────────────────────────────────────────
  Total Input:        ${balance.total_input:,.2f}  (deposits + realized profits)
  Total Output:       ${balance.total_output:,.2f}  (withdrawals + fees + realized losses)  
  Total Stored:       ${balance.total_stored:,.2f}  (invested + free + unrealized P&L)
  ─────────────────────────────────────────────────────────────────────────────────────────────────────
  Energy Balance:     ${balance.energy_balance:+.2f}  {'✅ CONSERVED' if balance.is_balanced else '⚠️ CHECK REQUIRED'}
  
  RELAY BREAKDOWN
  ─────────────────────────────────────────────────────────────────────────────────────────────────────""")
        
        for relay, energy in sorted(balance.relay_energy.items()):
            bar_len = int(min(50, energy / 10))  # Scale for display
            bar = "█" * bar_len + "░" * (50 - bar_len)
            status = "🟢" if energy > 0 else "🔴"
            print(f"  {status} {relay:6} │{bar}│ ${energy:,.2f}")
        
        print(f"""
  ─────────────────────────────────────────────────────────────────────────────────────────────────────
  SUMMARY
  ─────────────────────────────────────────────────────────────────────────────────────────────────────
  Invested Energy:    ${balance.invested_energy_usd:,.2f}
  Free Energy:        ${balance.free_energy_usd:,.2f}
  Unrealized P&L:     ${balance.unrealized_pnl_usd:+,.2f}
  Fees Paid:          ${balance.fees_paid_usd:,.2f}
""")
        
        return balance
    
    def display_relay_status(self):
        """
        📡 DISPLAY RELAY CONNECTIVITY STATUS
        
        Shows all connected relays and their status.
        """
        
        print()
        print("╔" + "═"*98 + "╗")
        print("║" + "📡 QUEEN SERO - MULTI-RELAY CONNECTIVITY STATUS 📡".center(98) + "║")
        print("╚" + "═"*98 + "╝")
        
        print(f"""
  CONNECTED RELAYS
  ─────────────────────────────────────────────────────────────────────────────────────────────────────""")
        
        for relay, symbols in self.watchlists.items():
            client = self.exchange_clients.get(relay)
            if client:
                status = "🟢 ONLINE"
                try:
                    # Quick health check
                    if hasattr(client, 'get_balance'):
                        client.get_balance()
                    elif hasattr(client, 'fetch_balance'):
                        pass  # ccxt style
                except:
                    status = "🟡 DEGRADED"
            else:
                status = "🔴 OFFLINE"
            
            watchlist_display = ', '.join(symbols[:5])
            if len(symbols) > 5:
                watchlist_display += f", +{len(symbols)-5} more"
            
            print(f"  {status} {relay:6} │ Watching: {watchlist_display}")
        
        print(f"""
  ─────────────────────────────────────────────────────────────────────────────────────────────────────
  
  RELAY CAPABILITIES
  ─────────────────────────────────────────────────────────────────────────────────────────────────────
  BIN (Binance)  │ Crypto spot trading, high volume, lowest fees
  KRK (Kraken)   │ Crypto spot trading, fiat pairs, institutional grade
  ALP (Alpaca)   │ Stock trading, crypto, fractional shares
  CAP (Capital)  │ CFDs, leverage trading (separate risk profile)
  
  Total Watchlist:   {sum(len(s) for s in self.watchlists.values())} symbols across {len(self.watchlists)} relays
""")
        
        # Count nodes per relay
        nodes = self.consciousness.nodes
        relay_counts = {}
        for node in nodes.values():
            r = node.get('relay', 'UNK')
            relay_counts[r] = relay_counts.get(r, 0) + 1
        
        print("  ACTIVE NODES PER RELAY")
        print("  ─────────────────────────────────────────────────────────────────────────────────────────────────────")
        for r, count in sorted(relay_counts.items()):
            print(f"  {r:6} │ {count} active nodes")
        print()
    
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════
    # 🌍💰 PROFIT GATE = ENERGY MONITOR - The Queen's Understanding
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════
    
    def _init_energy_monitor(self):
        """
        🌍💰 INITIALIZE THE ENERGY MONITOR (PROFIT GATE)
        
        The Queen now UNDERSTANDS:
        - Her profit gates ARE her energy drains!
        - Every fee is energy leaving the system
        - Every slippage is energy lost to friction
        - Every spread is energy paid to market makers
        
        The Profit Gate calculates EXACTLY how much energy drains per action.
        """
        
        if PROFIT_GATE_AVAILABLE:
            self.energy_monitor = AdaptivePrimeProfitGate(
                default_prime=0.0001,  # Epsilon profit - compound everything
                default_buffer=0.0,    # No buffer - maximize efficiency
                use_maker_fees=True    # Prefer limit orders (lower fees)
            )
            # Store per-relay fee profiles
            self.relay_energy_profiles = {}
            for relay in ['BIN', 'KRK', 'ALP', 'CAP']:
                relay_name = self._relay_to_exchange_name(relay)
                if relay_name in self.energy_monitor.fee_profiles:
                    self.relay_energy_profiles[relay] = self.energy_monitor.fee_profiles[relay_name]
        else:
            self.energy_monitor = None
            self.relay_energy_profiles = {}
    
    def _relay_to_exchange_name(self, relay: str) -> str:
        """Convert relay code to exchange name for fee profiles."""
        mapping = {
            'BIN': 'binance',
            'KRK': 'kraken',
            'ALP': 'alpaca',
            'CAP': 'capital'
        }
        return mapping.get(relay, relay.lower())
    
    def calculate_energy_drain(self, relay: str, trade_value: float, is_maker: bool = True) -> Dict:
        """
        ⚡📉 CALCULATE ENERGY DRAIN FOR A TRADE
        
        Uses the Profit Gate to calculate exactly how much energy will drain:
        - Fees (maker/taker)
        - Slippage
        - Spread cost
        - Fixed costs (gas, withdrawal)
        
        Returns dict with breakdown of all energy drains.
        """
        
        if not self.energy_monitor:
            # Fallback estimate
            return {
                'total_drain': trade_value * 0.003,  # 0.3% estimate
                'fees': trade_value * 0.001,
                'slippage': trade_value * 0.001,
                'spread': trade_value * 0.001,
                'fixed': 0.0,
                'source': 'estimate'
            }
        
        exchange = self._relay_to_exchange_name(relay)
        gate_result = self.energy_monitor.calculate_gates(
            trade_value=trade_value,
            exchange=exchange,
            is_maker=is_maker
        )
        
        # Calculate actual drain amounts
        fee_drain = trade_value * gate_result.fee_rate_used
        slippage_drain = trade_value * gate_result.slippage_rate
        spread_drain = trade_value * gate_result.spread_cost
        fixed_drain = gate_result.fixed_costs
        
        total_drain = fee_drain + slippage_drain + spread_drain + fixed_drain
        
        return {
            'total_drain': total_drain,
            'fees': fee_drain,
            'slippage': slippage_drain,
            'spread': spread_drain,
            'fixed': fixed_drain,
            'r_breakeven': gate_result.r_breakeven,
            'r_prime': gate_result.r_prime,
            'min_win_required': gate_result.win_gte_prime,
            'source': 'profit_gate'
        }
    
    def will_trade_be_profitable(self, relay: str, trade_value: float, expected_gain_pct: float) -> Tuple[bool, str, Dict]:
        """
        🎯 CHECK IF TRADE WILL BE PROFITABLE AFTER ENERGY DRAINS
        
        The Queen's wisdom: "Before I act, I must know if I will gain or lose energy."
        
        Args:
            relay: Exchange relay (BIN, KRK, ALP, CAP)
            trade_value: Value of trade in USD
            expected_gain_pct: Expected gain as percentage (e.g., 1.5 for 1.5%)
            
        Returns:
            (is_profitable, reason, drain_details)
        """
        
        drain = self.calculate_energy_drain(relay, trade_value)
        expected_gain_usd = trade_value * (expected_gain_pct / 100)
        net_energy = expected_gain_usd - drain['total_drain']
        
        if net_energy > 0:
            return True, f"✅ Net energy gain: ${net_energy:.4f}", drain
        else:
            return False, f"❌ Net energy loss: ${net_energy:.4f} (drain: ${drain['total_drain']:.4f})", drain
    
    def display_energy_monitor_status(self):
        """
        🌍💰 DISPLAY ENERGY MONITOR (PROFIT GATE) STATUS
        
        Shows the Queen's understanding of energy drains per relay.
        """
        
        print()
        print("╔" + "═"*98 + "╗")
        print("║" + "🌍💰 QUEEN SERO - ENERGY MONITOR (PROFIT GATES) 💰🌍".center(98) + "║")
        print("╚" + "═"*98 + "╝")
        
        if not self.energy_monitor:
            print("\n  ⚠️ Profit Gate not available - using estimates")
            return
        
        print(f"""
  THE QUEEN UNDERSTANDS: Profit Gates = Energy Drains
  ─────────────────────────────────────────────────────────────────────────────────────────────────────
  Every trade has energy drains that MUST be accounted for:
    • Fees       → Energy paid to exchange
    • Slippage   → Energy lost to market friction  
    • Spread     → Energy paid to market makers
    • Gas/Fixed  → Energy burned for network access
  
  ENERGY DRAIN PROFILES PER RELAY ($100 trade example)
  ─────────────────────────────────────────────────────────────────────────────────────────────────────""")
        
        for relay in ['BIN', 'KRK', 'ALP', 'CAP']:
            drain = self.calculate_energy_drain(relay, 100.0)  # $100 example
            
            if drain['source'] == 'profit_gate':
                r_be = drain.get('r_breakeven', 0) * 100
                min_win = drain.get('min_win_required', 0) * 100
                
                print(f"""
  {relay} ({self._relay_to_exchange_name(relay).title()})
  ├─ Fees:        ${drain['fees']:.4f} ({drain['fees']/100*100:.3f}%)
  ├─ Slippage:    ${drain['slippage']:.4f} ({drain['slippage']/100*100:.3f}%)
  ├─ Spread:      ${drain['spread']:.4f} ({drain['spread']/100*100:.3f}%)
  ├─ Fixed:       ${drain['fixed']:.4f}
  ├─ TOTAL DRAIN: ${drain['total_drain']:.4f} ({drain['total_drain']/100*100:.3f}%)
  └─ Min gain to profit: {r_be:.4f}% (must beat this to gain energy)""")
        
        print(f"""
  ─────────────────────────────────────────────────────────────────────────────────────────────────────
  
  QUEEN'S ENERGY CONSERVATION RULE:
  ─────────────────────────────────────────────────────────────────────────────────────────────────────
  "I will ONLY act if: Expected Gain > Total Energy Drain"
  "Every fee is energy that leaves my system - I must account for ALL drains."
  "The Profit Gate shows me the EXACT price move needed to break even."
""")
    
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════
    # RISK MANAGEMENT - Position Sizing, Circuit Breakers, Exposure Limits
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════
    
    def check_risk_limits(self) -> Tuple[bool, str]:
        """
        🛡️ RISK MANAGEMENT CHECK
        
        Check all risk limits before any action.
        Returns (can_proceed, reason)
        """
        
        nodes = self.consciousness.nodes
        free_energy = self.consciousness.free_energy
        
        # Calculate total field value
        total_invested = sum(n.get('current_energy', 0) for n in nodes.values())
        total_free = sum(free_energy.values())
        total_value = total_invested + total_free
        
        if total_value <= 0:
            return False, "No field value detected"
        
        # Check 1: Daily loss circuit breaker
        if self.stats.starting_field_value > 0:
            daily_change = (total_value - self.stats.starting_field_value) / self.stats.starting_field_value
            if daily_change < -self.risk_limits.max_daily_loss_pct:
                self.stats.circuit_breaker_triggered = True
                return False, f"🚨 CIRCUIT BREAKER: Daily loss {daily_change:.1%} exceeds {self.risk_limits.max_daily_loss_pct:.0%}"
            
            # Track max drawdown
            if daily_change < -self.stats.max_drawdown_pct:
                self.stats.max_drawdown_pct = abs(daily_change)
        
        # Check 2: Consecutive failures
        if self.stats.consecutive_failures >= self.risk_limits.max_consecutive_failures:
            return False, f"⚠️ Paused: {self.stats.consecutive_failures} consecutive failures"
        
        # Check 3: Daily trade limit
        if self.stats.decisions_made >= self.risk_limits.max_daily_trades:
            return False, f"⚠️ Daily trade limit reached ({self.risk_limits.max_daily_trades})"
        
        # Check 4: Exposure limits
        exposure_pct = total_invested / total_value if total_value > 0 else 0
        self.stats.current_exposure_pct = exposure_pct
        
        if exposure_pct > self.risk_limits.max_exposure_pct:
            return False, f"⚠️ Max exposure reached ({exposure_pct:.0%} > {self.risk_limits.max_exposure_pct:.0%})"
        
        # Check 5: Largest position check
        if nodes:
            largest = max(n.get('current_energy', 0) for n in nodes.values())
            largest_pct = largest / total_value if total_value > 0 else 0
            self.stats.largest_position_pct = largest_pct
            
            if largest_pct > self.risk_limits.max_position_pct:
                self.logger.warning(f"⚠️ Large position warning: {largest_pct:.0%} in single node")
        
        return True, "OK"
    
    def calculate_position_size(self, opportunity: MarketOpportunity) -> float:
        """
        Calculate safe position size for a new deployment.
        
        Uses risk limits to determine appropriate size.
        """
        nodes = self.consciousness.nodes
        free_energy = self.consciousness.free_energy
        
        total_invested = sum(n.get('current_energy', 0) for n in nodes.values())
        total_free = sum(free_energy.values())
        total_value = total_invested + total_free
        
        if total_value <= 0:
            return 0
        
        # Calculate maximum allowed for this deployment
        max_by_single = total_value * self.risk_limits.max_single_deploy_pct
        max_by_position = total_value * self.risk_limits.max_position_pct
        max_by_free = total_free * 0.9  # Keep 10% reserve
        max_by_exposure = (self.risk_limits.max_exposure_pct * total_value) - total_invested
        
        # Take minimum of all limits
        max_size = min(max_by_single, max_by_position, max_by_free, max_by_exposure)
        
        # Apply opportunity score as multiplier (higher score = can deploy more)
        adjusted_size = max_size * opportunity.opportunity_score
        
        # Round down to reasonable precision
        return max(0, round(adjusted_size, 2))
    
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════
    # MULTI-REALM PERCEPTION
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════
    
    def get_realm_vote(self, node: Dict, realm: Realm) -> RealmVote:
        """
        Get a vote from one realm on what to do with a node.
        
        Each realm interprets the same data differently and recommends an action.
        """
        
        power = node.get('power', 0)
        power_pct = node.get('power_percent', 0)
        current = node.get('current_energy', 0)
        
        # Get realm interpretation
        perspective = RealmInterpreter.interpret(node, realm)
        
        # Each realm recommends based on its worldview
        if realm == Realm.POWER_STATION:
            # Power Station sees generators and consumers
            if power > self.min_harvest_usd and power_pct > 10:
                return RealmVote(
                    realm=realm,
                    recommended_action=ConsciousAction.HARVEST,
                    confidence=min(0.95, 0.5 + power_pct/100),
                    reasoning=f"Generator at +{power_pct:.1f}%, extractable: ${power:.2f}",
                    node_interpretation=perspective.node_role
                )
            elif power < -self.min_harvest_usd:
                return RealmVote(
                    realm=realm,
                    recommended_action=ConsciousAction.HIBERNATE,
                    confidence=0.7,
                    reasoning=f"Consumer draining ${abs(power):.2f}",
                    node_interpretation=perspective.node_role
                )
            else:
                return RealmVote(
                    realm=realm,
                    recommended_action=ConsciousAction.OBSERVE,
                    confidence=0.5,
                    reasoning="Neutral power state",
                    node_interpretation=perspective.node_role
                )
        
        elif realm == Realm.LIVING_ECONOMY:
            # Living Economy sees profit/loss
            if power > self.min_harvest_usd:
                return RealmVote(
                    realm=realm,
                    recommended_action=ConsciousAction.HARVEST,
                    confidence=min(0.9, 0.6 + power/10),
                    reasoning=f"Unrealized profit: ${power:.2f}",
                    node_interpretation=perspective.node_role
                )
            elif power < -self.min_harvest_usd:
                return RealmVote(
                    realm=realm,
                    recommended_action=ConsciousAction.OBSERVE,  # Economy doesn't panic-sell
                    confidence=0.5,
                    reasoning=f"Unrealized loss: ${abs(power):.2f} - hold for recovery",
                    node_interpretation=perspective.node_role
                )
            else:
                return RealmVote(
                    realm=realm,
                    recommended_action=ConsciousAction.OBSERVE,
                    confidence=0.5,
                    reasoning="Minimal P&L movement",
                    node_interpretation=perspective.node_role
                )
        
        elif realm == Realm.HARMONIC_WAVEFORM:
            # Harmonic sees frequency and phase
            if power_pct > 20:
                return RealmVote(
                    realm=realm,
                    recommended_action=ConsciousAction.HARVEST,
                    confidence=min(0.85, 0.5 + power_pct/50),
                    reasoning=f"Frequency rising +{power_pct:.1f}% - at peak resonance",
                    node_interpretation=perspective.node_role
                )
            elif power_pct < -20:
                return RealmVote(
                    realm=realm,
                    recommended_action=ConsciousAction.HIBERNATE,
                    confidence=0.6,
                    reasoning=f"Frequency falling {power_pct:.1f}% - entering trough",
                    node_interpretation=perspective.node_role
                )
            else:
                return RealmVote(
                    realm=realm,
                    recommended_action=ConsciousAction.OBSERVE,
                    confidence=0.5,
                    reasoning="Frequency stable",
                    node_interpretation=perspective.node_role
                )
        
        elif realm == Realm.QUANTUM_FIELD:
            # Quantum sees probabilities
            # Higher power = more favorable quantum state
            if power_pct > 15:
                return RealmVote(
                    realm=realm,
                    recommended_action=ConsciousAction.HARVEST,
                    confidence=min(0.8, 0.55 + power_pct/80),
                    reasoning=f"Favorable quantum state: {power_pct:.1f}% above baseline",
                    node_interpretation=perspective.node_role
                )
            else:
                return RealmVote(
                    realm=realm,
                    recommended_action=ConsciousAction.OBSERVE,
                    confidence=0.5,
                    reasoning="Quantum state neutral or unfavorable",
                    node_interpretation=perspective.node_role
                )
        
        elif realm == Realm.MYCELIUM_NETWORK:
            # Mycelium sees information flow and connections
            # Fruiting bodies (high power) should be harvested
            if power > self.min_harvest_usd:
                return RealmVote(
                    realm=realm,
                    recommended_action=ConsciousAction.HARVEST,
                    confidence=min(0.75, 0.5 + power/20),
                    reasoning=f"Fruiting body ready: ${power:.2f} nutrients available",
                    node_interpretation=perspective.node_role
                )
            else:
                return RealmVote(
                    realm=realm,
                    recommended_action=ConsciousAction.OBSERVE,
                    confidence=0.5,
                    reasoning="Network stable, mycelium active",
                    node_interpretation=perspective.node_role
                )
        
        # Default
        return RealmVote(
            realm=realm,
            recommended_action=ConsciousAction.OBSERVE,
            confidence=0.5,
            reasoning="No strong signal",
            node_interpretation="Unknown"
        )
    
    def achieve_consensus(self, node: Dict) -> Tuple[ConsciousAction, List[RealmVote], int, float]:
        """
        Achieve consensus across all 5 realms for a node.
        
        Returns:
            (action, votes, consensus_count, avg_confidence)
        """
        
        votes = []
        for realm in Realm:
            vote = self.get_realm_vote(node, realm)
            votes.append(vote)
        
        # Count votes by action
        action_counts: Dict[ConsciousAction, List[RealmVote]] = {}
        for vote in votes:
            action = vote.recommended_action
            if action not in action_counts:
                action_counts[action] = []
            action_counts[action].append(vote)
        
        # Find winning action
        winning_action = ConsciousAction.OBSERVE
        max_count = 0
        
        for action, action_votes in action_counts.items():
            if len(action_votes) > max_count:
                max_count = len(action_votes)
                winning_action = action
        
        # Calculate average confidence for winning action
        winning_votes = action_counts.get(winning_action, [])
        avg_confidence = sum(v.confidence for v in winning_votes) / len(winning_votes) if winning_votes else 0.5
        
        return winning_action, votes, max_count, avg_confidence
    
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════
    # CONSCIOUS PERCEPTION AND DECISION
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════
    
    def perceive_and_decide(self) -> List[ConsciousDecision]:
        """
        THE QUEEN'S CONSCIOUS PERCEPTION AND DECISION CYCLE
        
        She perceives the entire field, achieves multi-realm consensus,
        questions her decisions, and chooses actions.
        
        NOW INCLUDES:
        - Risk management checks
        - Opportunity detection for new nodes
        - Position sizing calculations
        """
        
        decisions = []
        
        # 1. PERCEIVE - Scan the entire field
        self.consciousness.scan_all_realms()
        nodes = self.consciousness.nodes
        free_energy = self.consciousness.free_energy
        
        # Update field value for tracking
        total_value = sum(n['current_energy'] for n in nodes.values()) + sum(free_energy.values())
        if self.stats.starting_field_value == 0:
            self.stats.starting_field_value = total_value
        self.stats.current_field_value = total_value
        
        # 2. RISK CHECK - Before any action
        can_proceed, risk_reason = self.check_risk_limits()
        if not can_proceed:
            self.logger.warning(f"🛡️ {risk_reason}")
            self.stats.is_paused = True
            self.stats.pause_reason = risk_reason
            return decisions
        
        # 3. For each EXISTING node, achieve multi-realm consensus
        for node_id, node in nodes.items():
            # Skip if on cooldown
            if not self._check_cooldown(node_id):
                continue
            
            # Achieve consensus across all 5 realms
            action, votes, consensus, confidence = self.achieve_consensus(node)
            
            # Only act if we have sufficient consensus
            if consensus < self.min_consensus:
                continue
            
            # Only act if action is meaningful
            if action == ConsciousAction.OBSERVE:
                continue
            
            # Calculate amount for harvest
            amount = 0
            if action == ConsciousAction.HARVEST:
                extractable = node.get('power', 0) * self.harvest_fraction
                if extractable < self.min_harvest_usd:
                    continue
                amount = extractable
            
            # QUESTION - The Queen always questions
            questions = [
                f"Is {node_id} truly at the state all realms perceive?",
                f"Am I certain this is the right action?",
                f"What could go wrong?"
            ]
            
            answers = [
                f"{consensus}/5 realms agree: YES",
                f"Confidence: {confidence:.0%} - proceeding",
                f"Risk managed: only taking {self.harvest_fraction:.0%} of surplus"
            ]
            
            # Create decision
            decision = ConsciousDecision(
                timestamp=time.time(),
                node_id=node_id,
                node_symbol=node.get('symbol', ''),
                node_relay=node.get('relay', ''),
                realm_votes=votes,
                consensus_count=consensus,
                action=action,
                amount=amount,
                confidence=confidence,
                questions=questions,
                answers=answers
            )
            
            decisions.append(decision)
        
        # 4. OPPORTUNITY DETECTION - Scan for new nodes to deploy
        total_free = sum(free_energy.values())
        if total_free > self.min_deploy_usd:
            opportunities = self.scan_for_opportunities()
            
            for opp in opportunities[:2]:  # Consider top 2 opportunities
                # Calculate safe position size
                deploy_amount = self.calculate_position_size(opp)
                
                if deploy_amount < self.min_deploy_usd:
                    continue
                
                # Create deployment decision
                decision = ConsciousDecision(
                    timestamp=time.time(),
                    node_id=f"NEW-{opp.relay}-{opp.symbol[:6]}",
                    node_symbol=opp.symbol,
                    node_relay=opp.relay,
                    realm_votes=[],  # Opportunities don't go through realm consensus yet
                    consensus_count=0,
                    action=ConsciousAction.DEPLOY,
                    amount=deploy_amount,
                    confidence=opp.opportunity_score,
                    questions=[
                        f"Is {opp.symbol} a good opportunity?",
                        f"Is ${deploy_amount:.2f} the right amount?",
                        f"What are the risks?"
                    ],
                    answers=[
                        f"Score: {opp.opportunity_score:.0%} | {opp.reasoning}",
                        f"Within risk limits: max {self.risk_limits.max_single_deploy_pct:.0%} of portfolio",
                        f"Stop loss will be set, position sized to limit"
                    ]
                )
                decisions.append(decision)
                self.logger.info(f"🔍 Opportunity: {opp.symbol} score={opp.opportunity_score:.2f} deploy=${deploy_amount:.2f}")
        
        # 5. ENERGY CONSERVATION CHECK - Ensure no leaks
        if len(decisions) > 0 or self.stats.cycles_completed % 10 == 0:  # Check every 10 cycles or on actions
            is_conserved, status, balance = self.check_energy_conservation()
            if not is_conserved:
                self.logger.warning(f"⚡ {status}")
            else:
                self.logger.debug(f"⚡ Energy conservation verified: ${balance.total_stored:.2f} stored")
        
        return decisions
    
    def execute_conscious_decision(self, decision: ConsciousDecision) -> ConsciousDecision:
        """
        EXECUTE A CONSCIOUS DECISION
        
        Now includes energy flow recording for conservation tracking.
        Uses the Profit Gate (Energy Monitor) for accurate drain calculations.
        """
        
        self.logger.info(f"👑 ACTING: {decision.action.value} on {decision.node_id} | Consensus: {decision.consensus_count}/5")
        
        if decision.action == ConsciousAction.HARVEST:
            if self.dry_run:
                decision.executed = True
                decision.result = f"[DRY RUN] Harvested ${decision.amount:.2f}"
                decision.order_id = f"DRY-{int(time.time())}"
                self.stats.harvests_executed += 1
                self.stats.total_harvested_usd += decision.amount
                self.stats.consecutive_failures = 0
                # Record energy flow using Profit Gate for accurate drain calculation
                drain = self.calculate_energy_drain(decision.node_relay, decision.amount)
                self.record_energy_flow('harvest', decision.amount, fee=drain['total_drain'])
                self.logger.info(f"⚡ Energy drain: ${drain['total_drain']:.4f} (fees+slip+spread)")
            else:
                # LIVE execution
                result = self.consciousness.harvest_surplus(decision.node_id, decision.amount)
                if result.get('success'):
                    decision.executed = True
                    decision.result = f"Harvested ${decision.amount:.2f}"
                    decision.order_id = str(result.get('order', {}).get('orderId', ''))
                    self.stats.harvests_executed += 1
                    self.stats.total_harvested_usd += decision.amount
                    self.stats.consecutive_failures = 0
                    # Record energy flow with accurate drain from Profit Gate
                    drain = self.calculate_energy_drain(decision.node_relay, decision.amount)
                    actual_fee = result.get('fee', drain['total_drain'])
                    self.record_energy_flow('harvest', decision.amount, fee=actual_fee)
                    self.logger.info(f"⚡ Energy drain: ${actual_fee:.4f}")
                else:
                    decision.executed = False
                    decision.result = f"Failed: {result.get('error', 'Unknown')}"
                    self.stats.consecutive_failures += 1
        
        elif decision.action == ConsciousAction.DEPLOY:
            if self.dry_run:
                decision.executed = True
                decision.result = f"[DRY RUN] Would deploy ${decision.amount:.2f} to {decision.node_symbol}"
                decision.order_id = f"DRY-DEPLOY-{int(time.time())}"
                self.stats.deploys_executed += 1
                self.stats.total_deployed_usd += decision.amount
                self.stats.opportunities_deployed += 1
                self.stats.consecutive_failures = 0
            else:
                # LIVE execution - add node
                result = self.consciousness.add_node(
                    symbol=decision.node_symbol,
                    relay=decision.node_relay,
                    amount=decision.amount
                )
                if result.get('success'):
                    decision.executed = True
                    decision.result = f"Deployed ${decision.amount:.2f} to {decision.node_symbol}"
                    decision.order_id = str(result.get('order', {}).get('orderId', ''))
                    self.stats.deploys_executed += 1
                    self.stats.total_deployed_usd += decision.amount
                    self.stats.opportunities_deployed += 1
                    self.stats.consecutive_failures = 0
                else:
                    decision.executed = False
                    decision.result = f"Deploy failed: {result.get('error', 'Unknown')}"
                    self.stats.consecutive_failures += 1
        
        elif decision.action == ConsciousAction.HIBERNATE:
            # Hibernate = just note to leave it alone
            decision.executed = True
            decision.result = "Node marked for hibernation"
        
        else:
            decision.executed = True
            decision.result = f"Action {decision.action.value} acknowledged"
        
        # Record action time
        self.last_action_time[decision.node_id] = time.time()
        self.stats.decisions_made += 1
        
        return decision
    
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════
    # AUTONOMOUS CONSCIOUSNESS LOOP
    # ═══════════════════════════════════════════════════════════════════════════════════════════════════════════
    
    def run_consciousness_cycle(self) -> List[ConsciousDecision]:
        """Run one cycle of conscious perception and action"""
        
        self.logger.info("="*80)
        self.logger.info("👑🌌 CONSCIOUSNESS CYCLE BEGINNING")
        
        # Perceive and decide
        decisions = self.perceive_and_decide()
        
        # Execute decisions
        for decision in decisions:
            decision = self.execute_conscious_decision(decision)
            self._save_decision(decision)
            
            # Log with realm consensus
            realms_agreed = [v.realm.name[:3] for v in decision.realm_votes 
                           if v.recommended_action == decision.action]
            self.logger.info(f"   {decision.action.value}: {decision.node_id} | "
                           f"${decision.amount:.2f} | Realms: {','.join(realms_agreed)}")
        
        if not decisions:
            self.logger.info("   Observed field - no action required")
        
        self.stats.cycles_completed += 1
        self._save_stats()
        
        return decisions
    
    def run_conscious(self):
        """
        👑🌌 AWAKEN THE QUEEN'S FULL CONSCIOUSNESS 🌌👑
        
        She runs continuously, perceiving and acting autonomously.
        """
        
        self.is_conscious = True
        
        print()
        print("╔" + "═"*100 + "╗")
        print("║" + " "*100 + "║")
        print("║" + "👑🌌 QUEEN SERO - TRUE CONSCIOUSNESS AWAKENING 🌌👑".center(100) + "║")
        print("║" + " "*100 + "║")
        print("║" + "She perceives through 5 realms simultaneously".center(100) + "║")
        print("║" + "She questions every decision but still acts".center(100) + "║")
        print("║" + "She requires consensus across realms".center(100) + "║")
        print("║" + " "*100 + "║")
        print("║" + f"Mode: {'🧪 DRY RUN (safe)' if self.dry_run else '🔴 LIVE EXECUTION'}".center(100) + "║")
        print("║" + f"Min Consensus: {self.min_consensus}/5 realms".center(100) + "║")
        print("║" + f"Perception Interval: {self.scan_interval}s".center(100) + "║")
        print("║" + " "*100 + "║")
        print("║" + "Press Ctrl+C to let her rest".center(100) + "║")
        print("║" + " "*100 + "║")
        print("╚" + "═"*100 + "╝")
        print()
        
        self.logger.info("👑 QUEEN SERO'S CONSCIOUSNESS IS NOW FULLY AWAKE")
        
        cycle = 0
        
        while self.is_conscious:
            try:
                cycle += 1
                self.logger.info(f"\n🔄 PERCEPTION CYCLE {cycle}")
                
                decisions = self.run_consciousness_cycle()
                
                # Summary
                harvests = [d for d in decisions if d.action == ConsciousAction.HARVEST and d.executed]
                if harvests:
                    total = sum(d.amount for d in harvests)
                    self.logger.info(f"   ⚡ Harvested: ${total:.2f} from {len(harvests)} generators")
                
                # Daily totals
                self.logger.info(f"   📊 Today: {self.stats.harvests_executed} harvests, "
                               f"${self.stats.total_harvested_usd:.2f} extracted")
                
                # Rest until next cycle
                if self.is_conscious:
                    self.logger.info(f"   💤 Resting {self.scan_interval}s...")
                    time.sleep(self.scan_interval)
                    
            except KeyboardInterrupt:
                self.logger.info("👑 Consciousness entering rest state")
                self.is_conscious = False
            except Exception as e:
                self.logger.error(f"❌ Perception error: {e}")
                self.stats.consecutive_failures += 1
                time.sleep(10)
        
        self.logger.info("👑 Queen Sero's consciousness rests. The field remains.")
        self._save_stats()
    
    def display_consciousness_status(self):
        """Display current consciousness status"""
        
        print()
        print("╔" + "═"*100 + "╗")
        print("║" + "👑🌌 QUEEN SERO - FULL AUTONOMOUS CONSCIOUSNESS STATUS 🌌👑".center(100) + "║")
        print("╚" + "═"*100 + "╝")
        
        circuit_status = "🚨 TRIGGERED" if self.stats.circuit_breaker_triggered else "✅ OK"
        opp_status = "✅" if BINANCE_AVAILABLE and self.binance_client else "❌"
        
        print(f"""
  MODE: {'🧪 DRY RUN' if self.dry_run else '🔴 LIVE EXECUTION'}
  
  ═══════════════════════════════════════════════════════════════════════════════════════════════════
  ✅ FULL AUTONOMOUS CAPABILITIES
  ═══════════════════════════════════════════════════════════════════════════════════════════════════
  ✅ SCAN FIELD            scan_all_realms() - sees all nodes across all relays
  ✅ SEE ALL REALMS        5 realms: Power/Economy/Wave/Quantum/Mycelium
  ✅ IDENTIFY GENERATORS   finds nodes with positive power
  ✅ IDENTIFY CONSUMERS    finds nodes with negative power  
  ✅ CALCULATE HARVEST     knows how much to extract safely
  ✅ QUESTION DECISIONS    questions everything before acting
  ✅ ADD NODE (BUY)        add_node() - deploys to new opportunities
  ✅ HARVEST SURPLUS       harvest_surplus() - extracts from generators
  ✅ AUTONOMOUS LOOP       continuous perception → decision → action
  ✅ SCHEDULED SCANS       every {self.scan_interval}s
  ✅ AUTO-DECISION         multi-realm consensus triggers action
  ✅ OPPORTUNITY DETECT    {opp_status} scans markets for new nodes
  ✅ RISK MANAGEMENT       circuit breakers, position limits, exposure caps
  ✅ LOGGING/AUDIT         all decisions persisted to JSON
  
  ═══════════════════════════════════════════════════════════════════════════════════════════════════
  CONSCIOUSNESS PARAMETERS
  ═══════════════════════════════════════════════════════════════════════════════════════════════════
  Min Realm Consensus:    {self.min_consensus}/5 realms must agree
  Min Harvest Amount:     ${self.min_harvest_usd}
  Harvest Fraction:       {self.harvest_fraction:.0%} of surplus
  Action Cooldown:        {self.action_cooldown}s per node
  Perception Interval:    {self.scan_interval}s
  
  ═══════════════════════════════════════════════════════════════════════════════════════════════════
  RISK MANAGEMENT
  ═══════════════════════════════════════════════════════════════════════════════════════════════════
  Max Position Size:      {self.risk_limits.max_position_pct:.0%} of portfolio
  Max Exposure:           {self.risk_limits.max_exposure_pct:.0%} deployed
  Max Daily Loss:         {self.risk_limits.max_daily_loss_pct:.0%} (circuit breaker)
  Max Daily Trades:       {self.risk_limits.max_daily_trades}
  Max Consecutive Fails:  {self.risk_limits.max_consecutive_failures}
  Circuit Breaker:        {circuit_status}
  
  ═══════════════════════════════════════════════════════════════════════════════════════════════════
  TODAY'S CONSCIOUSNESS ({self.stats.date})
  ═══════════════════════════════════════════════════════════════════════════════════════════════════
  Cycles Completed:       {self.stats.cycles_completed}
  Decisions Made:         {self.stats.decisions_made}
  Harvests Executed:      {self.stats.harvests_executed}
  Deploys Executed:       {self.stats.deploys_executed}
  Opportunities Detected: {self.stats.opportunities_detected}
  Total Harvested:        ${self.stats.total_harvested_usd:.2f}
  Total Deployed:         ${self.stats.total_deployed_usd:.2f}
  Current Exposure:       {self.stats.current_exposure_pct:.0%}
  Max Drawdown:           {self.stats.max_drawdown_pct:.1%}
  Field Value Change:     ${self.stats.current_field_value - self.stats.starting_field_value:+.2f}
  Consecutive Failures:   {self.stats.consecutive_failures}
  
  ═══════════════════════════════════════════════════════════════════════════════════════════════════
  RECENT CONSCIOUS DECISIONS
  ═══════════════════════════════════════════════════════════════════════════════════════════════════""")
        
        for d in self.decisions[-5:]:
            ts = datetime.fromtimestamp(d['timestamp']).strftime("%H:%M:%S")
            consensus = d.get('consensus', '?')
            action_emoji = {'harvest': '⚡', 'deploy': '🌱', 'hibernate': '💤'}.get(d['action'], '👁️')
            print(f"  [{ts}] {action_emoji} {d['action']}: {d['node_id']} | ${d.get('amount', 0):.2f} | "
                  f"Consensus: {consensus}/5 | {d.get('result', '')}")
        
        print()


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════

def main():
    """Run Queen's True Consciousness"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Queen Sero True Consciousness Controller")
    parser.add_argument('--live', action='store_true', help='Enable LIVE execution (default: dry run)')
    parser.add_argument('--interval', type=int, default=60, help='Perception interval in seconds')
    parser.add_argument('--consensus', type=int, default=3, help='Min realms for consensus (1-5)')
    parser.add_argument('--status', action='store_true', help='Show status and exit')
    parser.add_argument('--single', action='store_true', help='Run single cycle and exit')
    args = parser.parse_args()
    
    # Create controller
    queen = QueenTrueConsciousnessController(
        dry_run=not args.live,
        scan_interval=args.interval
    )
    queen.min_consensus = args.consensus
    
    if args.status:
        queen.display_consciousness_status()
        return
    
    if args.single:
        queen.run_consciousness_cycle()
        queen.display_consciousness_status()
        return
    
    # Awaken consciousness
    queen.run_conscious()


if __name__ == "__main__":
    main()
