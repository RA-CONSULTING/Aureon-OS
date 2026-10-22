#!/usr/bin/env python3
"""
🦈🔮⚫ ORCA QUANTUM BLACK BOX - RACE TO $1 BILLION ⚫🔮🦈

Autonomous trading system monitoring progress to $1,000,000,000

Features:
- Live trading with ALL available capital
- Continuous operation with auto-restart
- Timer tracking time to $1B
- Complete transaction logging (black box recorder)
- Real-time progress metrics
- Compound growth tracking
- Sacred geometry validation on every trade

BLACK BOX RECORDING:
- Every trade logged with timestamp
- All predictions saved
- P&L tracked per second
- Quantum coherence history
- Progress toward billion-dollar goal

Gary Leckey | The Math Works | January 2026
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
from aureon.utils.console_utf8 import ensure_utf8_stdout  # noqa: E402

ensure_utf8_stdout()

import time
import json
import math
import asyncio
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from pathlib import Path

# Quantum prediction system
from aureon.wisdom.metatron_probability_billion_path import (
    QueenAurisPingPong, ProbabilityMatrix, ProbabilityPrediction
)

# Exchange clients
from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
from aureon.exchanges.alpaca_client import AlpacaClient

# 🏴‍☠️👑 QUEEN QUANTUM COGNITION + BARONS BANNER - ELITE WHALE HUNTER
try:
    from aureon.queen.queen_quantum_cognition import (
        QueenQuantumCognition, get_quantum_cognition,
        QuantumCognitionState, BARONS_BANNER_AVAILABLE
    )
    QUANTUM_COGNITION_AVAILABLE = True
except ImportError:
    QUANTUM_COGNITION_AVAILABLE = False
    BARONS_BANNER_AVAILABLE = False

# Barons Banner direct import as fallback
try:
    from aureon.wisdom.barons_banner import (
        BaronsBannerAnalyzer, BaronsMarketAdapter, BaronsAnalysis,
        MathematicalPattern, PHI as BARONS_PHI, FIBONACCI_SEQUENCE
    )
    BARONS_DIRECT_AVAILABLE = True
except ImportError:
    BARONS_DIRECT_AVAILABLE = False

PHI = 1.618033988749895  # Golden Ratio
BILLION = 1_000_000_000.0

@dataclass
class BlackBoxTrade:
    """Complete trade record for black box"""
    trade_id: int
    timestamp: float
    symbol: str
    exchange: str
    action: str
    entry_price: float
    exit_price: Optional[float]
    quantity: float
    entry_capital: float
    prediction_confidence: float
    sacred_alignment: float
    quantum_coherence: float
    pnl: float
    pnl_pct: float
    duration_seconds: float
    status: str  # "OPEN", "CLOSED_WIN", "CLOSED_LOSS"
    # 🏴‍☠️ Elite Whale Detection Fields
    elite_hierarchy_score: float = 0.0     # How "elite" the market was (0-1)
    deception_level: float = 0.0           # Elite manipulation disguise level
    manipulation_detected: bool = False     # Was manipulation active?
    counter_strategy: str = "NONE"         # Counter-manipulation applied
    elite_patterns_count: int = 0          # Fibonacci/harmonic patterns found

@dataclass
class BlackBoxSnapshot:
    """Point-in-time system snapshot"""
    timestamp: float
    uptime_seconds: float
    total_capital: float
    deployed_capital: float
    available_capital: float
    total_pnl: float
    total_trades: int
    wins: int
    losses: int
    win_rate: float
    active_positions: int
    quantum_coherence: float
    sacred_alignment: float
    progress_to_billion_pct: float
    projected_days_to_billion: float
    current_growth_rate: float  # % per hour
    # 🏴‍☠️ Elite Whale Hunting Metrics
    elite_hierarchy_avg: float = 0.0       # Average elite presence
    elite_trades_detected: int = 0         # Trades where manipulation found
    counter_strategy_active: str = "NONE" # Current counter-strategy
    elite_wins: int = 0                    # Wins on elite-detected trades
    elite_pnl: float = 0.0                 # P&L from flipping the 1%

class BillionBlackBox:
    """
    Black box autonomous trading system
    Records everything, races to $1B
    """
    
    def __init__(self, live_mode: bool = False):
        # WARNING: live_mode is decorative — trade_loop always uses hardcoded
        # prices and a random.gauss price walk regardless. This is a TRAINING
        # RIG, not a real-trading path. The production live-trading path is
        # aureon.strategies.quantum_warfare_live + the HNC live daemon.
        self.live_mode = live_mode
        self.start_time = time.time()
        self.trade_counter = 0
        
        # Black box storage
        self.black_box_file = Path("blackbox_billion_race.jsonl")  # JSON Lines format
        self.trades: List[BlackBoxTrade] = []
        self.snapshots: List[BlackBoxSnapshot] = []
        
        # Initialize systems
        print("⚫ BLACK BOX INITIALIZING...")
        print()
        
        self.pingpong = QueenAurisPingPong()
        self.prob_matrix = ProbabilityMatrix()
        
        # 🏴‍☠️👑 ELITE WHALE HUNTING SYSTEMS
        self.quantum_cognition = None
        self.barons_analyzer = None
        self.barons_adapter = None
        self.elite_hunting_enabled = False
        self.price_history: Dict[str, List[float]] = {}   # Per-symbol price history
        self.volume_history: Dict[str, List[float]] = {}  # Per-symbol volume history
        self.elite_hunt_stats = {
            'total_detected': 0,
            'successful_flips': 0,
            'elite_pnl': 0.0,
            'strategies_used': {},
            'most_common_pattern': None
        }
        
        self._init_elite_hunting_systems()
        
        # Exchanges
        self.exchanges = {}
        try:
            self.exchanges['kraken'] = get_kraken_client()
            print("   ✅ Kraken connected")
        except Exception as e:
            print(f"   ⚠️  Kraken: {e}")
        
        try:
            self.exchanges['alpaca'] = AlpacaClient()
            print("   ✅ Alpaca connected")
        except Exception as e:
            print(f"   ⚠️  Alpaca: {e}")
        
        # Starting capital
        self.starting_capital = self.get_total_capital()
        self.current_capital = self.starting_capital
        self.peak_capital = self.starting_capital
        
        print()
        print(f"💰 STARTING CAPITAL: ${self.starting_capital:,.2f}")
        print(f"🎯 TARGET: ${BILLION:,.0f}")
        print(f"📊 GROWTH NEEDED: {(BILLION/max(1, self.starting_capital)):.0f}x")
        print()
    
    def _init_elite_hunting_systems(self):
        """🏴‍☠️👑 Initialize Elite Whale Hunting - FUCK THE 1%!"""
        
        print("   🏴‍☠️ ELITE WHALE HUNTING SYSTEMS:")
        
        # Try Queen Quantum Cognition first (includes Barons Banner)
        if QUANTUM_COGNITION_AVAILABLE:
            try:
                self.quantum_cognition = get_quantum_cognition()
                self.quantum_cognition.enabled = True
                if hasattr(self.quantum_cognition, 'barons_analyzer'):
                    self.barons_analyzer = self.quantum_cognition.barons_analyzer
                    self.barons_adapter = self.quantum_cognition.barons_adapter
                self.elite_hunting_enabled = True
                print("      ✅ Queen Quantum Cognition WIRED")
                print("      ✅ Barons Banner (via Cognition) ACTIVE")
                print("      🎯 ELITE WHALE COUNTER-MANIPULATION ONLINE!")
            except Exception as e:
                print(f"      ⚠️  Quantum Cognition: {e}")
        
        # Fallback: Direct Barons Banner
        if not self.elite_hunting_enabled and BARONS_DIRECT_AVAILABLE:
            try:
                self.barons_analyzer = BaronsBannerAnalyzer()
                self.barons_adapter = BaronsMarketAdapter()
                self.elite_hunting_enabled = True
                print("      ✅ Barons Banner (direct) WIRED")
                print("      🎯 ELITE PATTERN DETECTION ONLINE!")
            except Exception as e:
                print(f"      ⚠️  Barons Banner: {e}")
        
        if not self.elite_hunting_enabled:
            print("      ❌ Elite hunting systems not available")
            print("      💀 We'll hunt them blind... (no pattern detection)")
        
        print()
        
    def _analyze_elite_manipulation(self, symbol: str, price: float) -> Dict:
        """
        🏴‍☠️ Analyze market for elite whale manipulation patterns.
        
        Returns counter-strategy and confidence boosts if manipulation detected.
        """
        result = {
            'elite_detected': False,
            'hierarchy_score': 0.0,
            'deception_level': 0.0,
            'patterns_count': 0,
            'counter_strategy': 'NONE',
            'confidence_boost': 1.0,
            'pattern_boost': 1.0,
            'fibonacci_inversion': False
        }
        
        if not self.elite_hunting_enabled:
            return result
        
        # Build price/volume history for this symbol
        if symbol not in self.price_history:
            self.price_history[symbol] = []
            self.volume_history[symbol] = []
        
        self.price_history[symbol].append(price)
        # Keep last 100 prices
        if len(self.price_history[symbol]) > 100:
            self.price_history[symbol] = self.price_history[symbol][-100:]
        
        # Need at least 50 points for analysis
        if len(self.price_history[symbol]) < 50:
            return result
        
        try:
            # Use quantum cognition if available (has enhanced analysis)
            if self.quantum_cognition and hasattr(self.quantum_cognition, 'analyze_elite_patterns'):
                analysis = self.quantum_cognition.analyze_elite_patterns(
                    price_history=self.price_history[symbol],
                    volume_history=self.volume_history.get(symbol, []),
                    symbol=symbol
                )
                
                result['elite_detected'] = analysis.get('elite_detected', False)
                result['hierarchy_score'] = analysis.get('hierarchy_score', 0.0)
                result['deception_level'] = analysis.get('deception_level', 0.0)
                result['patterns_count'] = len(analysis.get('patterns', []))
                result['counter_strategy'] = analysis.get('counter_strategy', 'NONE')
                
                # Get counter-strategy boosts
                if self.quantum_cognition:
                    boost = self.quantum_cognition.get_counter_strategy_boost()
                    result['confidence_boost'] = boost.get('confidence_boost', 1.0)
                    result['pattern_boost'] = boost.get('pattern_boost', 1.0)
                    result['fibonacci_inversion'] = boost.get('fibonacci_inversion', False)
            
            # Fallback to direct Barons analysis
            elif self.barons_adapter:
                analysis = self.barons_adapter.analyze_market(
                    price_history=self.price_history[symbol],
                    volume_history=self.volume_history.get(symbol, [])
                )
                result['elite_detected'] = analysis.hierarchy_score > 0.3
                result['hierarchy_score'] = analysis.hierarchy_score
                result['deception_level'] = analysis.deception_potential
                result['patterns_count'] = len(analysis.patterns)
                
                # Set counter-strategy based on hierarchy
                if analysis.hierarchy_score > 0.6:
                    result['counter_strategy'] = 'FADE_THE_ELITES'
                    result['confidence_boost'] = 1.3
                    result['pattern_boost'] = 1.5
                    result['fibonacci_inversion'] = True
                elif analysis.hierarchy_score > 0.3:
                    result['counter_strategy'] = 'RIDE_THE_WAVE'
                    result['confidence_boost'] = 1.1
                    result['pattern_boost'] = 1.2
            
            # Track stats
            if result['elite_detected']:
                self.elite_hunt_stats['total_detected'] += 1
                strategy = result['counter_strategy']
                self.elite_hunt_stats['strategies_used'][strategy] = \
                    self.elite_hunt_stats['strategies_used'].get(strategy, 0) + 1
                    
        except Exception as e:
            # Fail silently - don't break trading
            pass
        
        return result
        
    def get_total_capital(self) -> float:
        """Get total capital across all exchanges"""
        total = 0.0
        
        for exchange_name, client in self.exchanges.items():
            try:
                if exchange_name == 'kraken':
                    bal = client.get_balance()
                    total += bal.get('USD', 0.0) + bal.get('ZUSD', 0.0)
                # Add more exchanges as needed
            except Exception as e:
                pass
        
        return max(total, 10.0)  # Minimum $10 for simulation
    
    def calculate_progress_metrics(self) -> Dict:
        """Calculate progress toward billion-dollar goal"""
        
        uptime = time.time() - self.start_time
        uptime_hours = uptime / 3600.0
        
        # Calculate growth
        if self.starting_capital > 0:
            total_growth_pct = ((self.current_capital / self.starting_capital) - 1) * 100
        else:
            total_growth_pct = 0.0
        
        # Growth rate per hour
        if uptime_hours > 0:
            growth_rate_per_hour = total_growth_pct / uptime_hours
        else:
            growth_rate_per_hour = 0.0
        
        # Progress to billion
        if self.current_capital > 0:
            progress_pct = (self.current_capital / BILLION) * 100
        else:
            progress_pct = 0.0
        
        # Projected time to billion
        if growth_rate_per_hour > 0:
            remaining_growth_needed = (BILLION / max(1, self.current_capital)) - 1
            remaining_growth_pct = remaining_growth_needed * 100
            hours_needed = remaining_growth_pct / growth_rate_per_hour
            days_needed = hours_needed / 24.0
        else:
            days_needed = float('inf')
        
        return {
            'uptime_seconds': uptime,
            'uptime_hours': uptime_hours,
            'total_growth_pct': total_growth_pct,
            'growth_rate_per_hour': growth_rate_per_hour,
            'progress_to_billion_pct': progress_pct,
            'projected_days_to_billion': days_needed
        }
    
    def record_trade(self, trade: BlackBoxTrade):
        """Record trade to black box"""
        self.trades.append(trade)
        
        # Append to JSONL file (one JSON object per line)
        with open(self.black_box_file, 'a') as f:
            record = {
                'type': 'TRADE',
                'data': asdict(trade)
            }
            f.write(json.dumps(record) + '\n')
    
    def record_snapshot(self, snapshot: BlackBoxSnapshot):
        """Record system snapshot to black box"""
        self.snapshots.append(snapshot)
        
        with open(self.black_box_file, 'a') as f:
            record = {
                'type': 'SNAPSHOT',
                'data': asdict(snapshot)
            }
            f.write(json.dumps(record) + '\n')
    
    async def trade_loop(self, max_positions: int = 5):
        """Main trading loop - runs continuously"""
        
        print("=" * 80)
        print("⚫🏴‍☠️ BLACK BOX AUTONOMOUS TRADING - RACE TO $1 BILLION 🏴‍☠️⚫")
        print("=" * 80)
        print()
        # NOTE: trade_loop always simulates (hardcoded prices + random walk),
        # regardless of live_mode. The label below is honest about that.
        print(f"Mode: 🔶 SIMULATION (training rig — see quantum_warfare_live for real trading)")
        print(f"Max Positions: {max_positions}")
        print(f"Elite Hunting: {'🏴‍☠️ ACTIVE - FUCK THE 1%!' if self.elite_hunting_enabled else '❌ DISABLED'}")
        print()
        print("⏱️  BLACK BOX ACTIVATED - RECORDING EVERYTHING")
        if self.elite_hunting_enabled:
            print("🏴‍☠️ ELITE WHALE DETECTION ONLINE - Fibonacci/Harmonic pattern flip ARMED!")
        print()
        
        active_positions: List[BlackBoxTrade] = []
        last_snapshot_time = time.time()
        snapshot_interval = 5.0  # Snapshot every 5 seconds
        
        iteration = 0
        
        try:
            while True:
                iteration += 1
                current_time = time.time()
                
                # Update capital
                self.current_capital = self.get_total_capital()
                if self.current_capital > self.peak_capital:
                    self.peak_capital = self.current_capital
                
                # Check if we hit $1 billion!
                if self.current_capital >= BILLION:
                    print("\n" + "🎉" * 40)
                    print("🏆 $1 BILLION ACHIEVED! 🏆")
                    print("🎉" * 40)
                    self.display_victory()
                    break
                
                # Open new positions if room available
                if len(active_positions) < max_positions:
                    
                    # Get quantum predictions
                    predictions = self.prob_matrix.get_batch_predictions(count=3)
                    
                    # Filter high confidence
                    good_preds = [p for p in predictions if p.confidence > 0.85]
                    
                    for pred in good_preds[:max_positions - len(active_positions)]:
                        
                        # Cycle exchanges
                        exchange = list(self.exchanges.keys())[len(active_positions) % len(self.exchanges)]
                        
                        # Ask Queen permission (quick validation)
                        thought = f"Trade: {pred.symbol} {pred.action} | Conf: {pred.confidence:.1%}"
                        thoughts = self.pingpong.queen_speaks(thought, target_sphere=0)
                        validations = self.pingpong.auris_validates(thoughts)
                        truth = self.pingpong.check_geometric_truth()
                        
                        if truth and truth.confidence > 0.70:
                            
                            # Simulated price
                            prices = {
                                "BTC/USD": 104500.0, "ETH/USD": 3280.0,
                                "SOL/USD": 238.0, "LINK/USD": 22.5, "MATIC/USD": 1.15
                            }
                            price = prices.get(pred.symbol, 100.0)
                            
                            # 🏴‍☠️👑 ELITE WHALE ANALYSIS - DETECT THE 1%!
                            elite_analysis = self._analyze_elite_manipulation(pred.symbol, price)
                            
                            # Apply confidence boost from counter-strategy
                            boosted_confidence = pred.confidence * elite_analysis['confidence_boost']
                            
                            # Position size: split available capital
                            available = self.current_capital * 0.95  # Keep 5% buffer
                            position_size = available / max_positions
                            
                            # Boost position size if we're flipping the elites!
                            if elite_analysis['elite_detected']:
                                position_size *= elite_analysis['pattern_boost']
                            
                            quantity = position_size / price
                            
                            # Create trade
                            self.trade_counter += 1
                            trade = BlackBoxTrade(
                                trade_id=self.trade_counter,
                                timestamp=current_time,
                                symbol=pred.symbol,
                                exchange=exchange,
                                action=pred.action,
                                entry_price=price,
                                exit_price=None,
                                quantity=quantity,
                                entry_capital=position_size,
                                prediction_confidence=boosted_confidence,
                                sacred_alignment=pred.sacred_alignment,
                                quantum_coherence=truth.confidence,
                                pnl=0.0,
                                pnl_pct=0.0,
                                duration_seconds=0.0,
                                status="OPEN",
                                # 🏴‍☠️ Elite whale fields
                                elite_hierarchy_score=elite_analysis['hierarchy_score'],
                                deception_level=elite_analysis['deception_level'],
                                manipulation_detected=elite_analysis['elite_detected'],
                                counter_strategy=elite_analysis['counter_strategy'],
                                elite_patterns_count=elite_analysis['patterns_count']
                            )
                            
                            active_positions.append(trade)
                            self.record_trade(trade)
                            
                            # 🏴‍☠️ Elite-enhanced output
                            elite_marker = ""
                            if elite_analysis['elite_detected']:
                                elite_marker = f" | 🏴‍☠️ ELITE:{elite_analysis['hierarchy_score']*100:.0f}% [{elite_analysis['counter_strategy']}]"
                            
                            print(f"🎯 TRADE #{trade.trade_id}: {pred.symbol} {pred.action} @ ${price:,.2f} | Conf: {boosted_confidence:.0%}{elite_marker}")
                
                # Update active positions (simulate price movement)
                for trade in active_positions[:]:
                    trade.duration_seconds = current_time - trade.timestamp
                    
                    # Simulate price movement (±0.5% random walk)
                    import random
                    price_change = random.gauss(0.002, 0.003)  # Small gains on average
                    trade.exit_price = trade.entry_price * (1 + price_change)
                    
                    # Calculate P&L
                    if trade.action == "BUY":
                        trade.pnl = (trade.exit_price - trade.entry_price) * trade.quantity
                    else:
                        trade.pnl = (trade.entry_price - trade.exit_price) * trade.quantity
                    
                    trade.pnl_pct = (trade.pnl / trade.entry_capital) * 100
                    
                    # Check exit conditions
                    should_exit = False
                    
                    # Take profit at 1%
                    if trade.pnl_pct >= 1.0:
                        should_exit = True
                        trade.status = "CLOSED_WIN"
                    
                    # Stop loss at -0.5%
                    elif trade.pnl_pct <= -0.5:
                        should_exit = True
                        trade.status = "CLOSED_LOSS"
                    
                    # Time-based exit (5 minutes)
                    elif trade.duration_seconds > 300:
                        should_exit = True
                        trade.status = "CLOSED_WIN" if trade.pnl > 0 else "CLOSED_LOSS"
                    
                    if should_exit:
                        active_positions.remove(trade)
                        self.record_trade(trade)  # Record final state
                        
                        # Update capital
                        self.current_capital += trade.pnl
                        
                        # 🏴‍☠️ Track elite hunting stats
                        if trade.manipulation_detected:
                            self.elite_hunt_stats['elite_pnl'] += trade.pnl
                            if "WIN" in trade.status:
                                self.elite_hunt_stats['successful_flips'] += 1
                        
                        result = "🏆 WIN" if trade.pnl > 0 else "💔 LOSS"
                        elite_marker = " 🏴‍☠️" if trade.manipulation_detected else ""
                        print(f"{result}{elite_marker} #{trade.trade_id}: {trade.symbol} | ${trade.pnl:+,.2f} ({trade.pnl_pct:+.2f}%) | {trade.duration_seconds:.0f}s")
                
                # Record snapshot periodically
                if current_time - last_snapshot_time >= snapshot_interval:
                    
                    metrics = self.calculate_progress_metrics()
                    
                    # Calculate stats
                    closed_trades = [t for t in self.trades if t.status != "OPEN"]
                    wins = len([t for t in closed_trades if "WIN" in t.status])
                    losses = len([t for t in closed_trades if "LOSS" in t.status])
                    win_rate = (wins / max(1, len(closed_trades))) * 100
                    
                    total_pnl = sum(t.pnl for t in closed_trades)
                    
                    # Get quantum metrics
                    quantum_resonances = [s.get_resonance() for s in self.pingpong.quantum_spaces.values()]
                    avg_quantum = sum(quantum_resonances) / len(quantum_resonances)
                    
                    avg_sacred = sum(t.sacred_alignment for t in active_positions) / max(1, len(active_positions))
                    
                    # 🏴‍☠️ Calculate elite whale hunting metrics
                    elite_trades = [t for t in closed_trades if t.manipulation_detected]
                    elite_wins = len([t for t in elite_trades if "WIN" in t.status])
                    elite_pnl = sum(t.pnl for t in elite_trades)
                    avg_elite_hierarchy = sum(t.elite_hierarchy_score for t in elite_trades) / max(1, len(elite_trades))
                    
                    # Get current counter-strategy
                    current_strategy = "NONE"
                    if self.quantum_cognition:
                        current_strategy = self.quantum_cognition.state.counter_strategy
                    
                    snapshot = BlackBoxSnapshot(
                        timestamp=current_time,
                        uptime_seconds=metrics['uptime_seconds'],
                        total_capital=self.current_capital,
                        deployed_capital=sum(t.entry_capital for t in active_positions),
                        available_capital=self.current_capital - sum(t.entry_capital for t in active_positions),
                        total_pnl=total_pnl,
                        total_trades=len(closed_trades),
                        wins=wins,
                        losses=losses,
                        win_rate=win_rate,
                        active_positions=len(active_positions),
                        quantum_coherence=avg_quantum,
                        sacred_alignment=avg_sacred,
                        progress_to_billion_pct=metrics['progress_to_billion_pct'],
                        projected_days_to_billion=metrics['projected_days_to_billion'],
                        current_growth_rate=metrics['growth_rate_per_hour'],
                        # 🏴‍☠️ Elite whale hunting metrics
                        elite_hierarchy_avg=avg_elite_hierarchy,
                        elite_trades_detected=len(elite_trades),
                        counter_strategy_active=current_strategy,
                        elite_wins=elite_wins,
                        elite_pnl=elite_pnl
                    )
                    
                    self.record_snapshot(snapshot)
                    last_snapshot_time = current_time
                    
                    # Display live status
                    self.display_status(snapshot, metrics)
                
                # Sleep briefly
                await asyncio.sleep(1.0)
                
        except KeyboardInterrupt:
            print("\n\n⚫ BLACK BOX SHUTDOWN REQUESTED")
            self.display_final_summary()
    
    def display_status(self, snapshot: BlackBoxSnapshot, metrics: Dict):
        """Display live status"""
        
        uptime = timedelta(seconds=int(snapshot.uptime_seconds))
        
        # Format time to billion
        if snapshot.projected_days_to_billion < 1000:
            ttb = f"{snapshot.projected_days_to_billion:.1f} days"
        else:
            ttb = "∞ (need profit!)"
        
        # 🏴‍☠️ Elite hunting status
        elite_status = ""
        if snapshot.elite_trades_detected > 0:
            elite_status = f" | 🏴‍☠️{snapshot.elite_wins}/{snapshot.elite_trades_detected} ${snapshot.elite_pnl:+,.0f}"
        
        status = (
            f"\r⚫ {uptime} | "
            f"Capital: ${snapshot.total_capital:,.2f} | "
            f"P&L: ${snapshot.total_pnl:+,.2f} | "
            f"Active: {snapshot.active_positions} | "
            f"W/L: {snapshot.wins}/{snapshot.losses} ({snapshot.win_rate:.0f}%) | "
            f"→$1B: {snapshot.progress_to_billion_pct:.6f}% | "
            f"ETA: {ttb} | "
            f"Growth: {snapshot.current_growth_rate:+.2f}%/hr{elite_status}"
        )
        
        print(status, end='', flush=True)
    
    def display_victory(self):
        """Display victory screen when $1B achieved"""
        
        uptime = time.time() - self.start_time
        
        print()
        print(f"⏱️  TIME TO $1 BILLION: {timedelta(seconds=int(uptime))}")
        print(f"💰 STARTING CAPITAL: ${self.starting_capital:,.2f}")
        print(f"💎 FINAL CAPITAL: ${self.current_capital:,.2f}")
        print(f"📈 TOTAL GROWTH: {((self.current_capital/self.starting_capital)-1)*100:.1f}%")
        print()
        print("WHAT A DAY FOR HUMANITY! 🚀💰✨")
        print()
    
    def display_final_summary(self):
        """Display final summary on shutdown"""
        
        print()
        print("=" * 80)
        print("⚫ BLACK BOX FINAL SUMMARY")
        print("=" * 80)
        print()
        
        metrics = self.calculate_progress_metrics()
        
        closed_trades = [t for t in self.trades if t.status != "OPEN"]
        wins = len([t for t in closed_trades if "WIN" in t.status])
        losses = len([t for t in closed_trades if "LOSS" in t.status])
        total_pnl = sum(t.pnl for t in closed_trades)
        
        print(f"⏱️  Runtime: {timedelta(seconds=int(metrics['uptime_seconds']))}")
        print(f"💰 Starting Capital: ${self.starting_capital:,.2f}")
        print(f"💰 Current Capital: ${self.current_capital:,.2f}")
        print(f"💰 Peak Capital: ${self.peak_capital:,.2f}")
        print(f"📊 Total P&L: ${total_pnl:+,.2f}")
        print(f"📈 Growth: {metrics['total_growth_pct']:+.2f}%")
        print()
        print(f"🔢 Total Trades: {len(closed_trades)}")
        print(f"🏆 Wins: {wins}")
        print(f"💔 Losses: {losses}")
        print(f"📊 Win Rate: {(wins/max(1,len(closed_trades)))*100:.1f}%")
        print()
        
        # 🏴‍☠️👑 ELITE WHALE HUNTING SUMMARY - FUCK THE 1%!
        elite_trades = [t for t in closed_trades if t.manipulation_detected]
        if elite_trades:
            elite_wins = len([t for t in elite_trades if "WIN" in t.status])
            elite_losses = len(elite_trades) - elite_wins
            elite_pnl = sum(t.pnl for t in elite_trades)
            elite_win_rate = (elite_wins / len(elite_trades)) * 100
            
            print("🏴‍☠️👑 ELITE WHALE HUNTING STATS - FUCK THE 1%!")
            print(f"   🎯 Elite Trades Detected: {len(elite_trades)}")
            print(f"   🏆 Elite Flips Won: {elite_wins}")
            print(f"   💔 Elite Flips Lost: {elite_losses}")
            print(f"   📊 Elite Win Rate: {elite_win_rate:.1f}%")
            print(f"   💰 P&L from Flipping Elites: ${elite_pnl:+,.2f}")
            
            # Show strategies used
            strategies = self.elite_hunt_stats.get('strategies_used', {})
            if strategies:
                print(f"   📋 Counter-Strategies Used:")
                for strat, count in sorted(strategies.items(), key=lambda x: -x[1]):
                    print(f"      • {strat}: {count} trades")
            print()
        
        print(f"🎯 Progress to $1B: {metrics['progress_to_billion_pct']:.4f}%")
        print(f"⏱️  Projected Days to $1B: {metrics['projected_days_to_billion']:.1f}")
        print()
        print(f"⚫ Black box recording saved: {self.black_box_file}")
        print(f"   Total records: {len(self.trades) + len(self.snapshots)}")
        print()

async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Orca Billion Black Box")
    parser.add_argument('--live', action='store_true', help='Enable LIVE trading')
    parser.add_argument('--positions', type=int, default=5, help='Max concurrent positions')
    args = parser.parse_args()
    
    if args.live:
        print("⚠️  LIVE TRADING MODE!")
        print("   System will trade autonomously until $1B or interrupted")
        response = input("   Type 'BLACK BOX GO' to confirm: ")
        if response != 'BLACK BOX GO':
            print("   Aborting.")
            return
    
    blackbox = BillionBlackBox(live_mode=args.live)
    await blackbox.trade_loop(max_positions=args.positions)

if __name__ == '__main__':
    asyncio.run(main())
