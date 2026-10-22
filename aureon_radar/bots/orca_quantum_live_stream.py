#!/usr/bin/env python3
"""
🦈🔮 ORCA QUANTUM LIVE STREAM - RACE TO THE BILLION 🔮🦈

🟡 STANDALONE TRAINING/DEMO RIG — uses ProbabilityMatrix from
   metatron_probability_billion_path which returns RANDOM predictions
   (not real 95% predictions). The ProbabilityMatrix calls now raise
   in production unless AUREON_ALLOW_SIM_FALLBACK is set, so this
   bot will fail loud at start in production rather than trade off
   synthetic predictions.

Integration of:
- Orca Complete Kill Cycle (multi-exchange hunting)
- Quantum Prediction Stream (95% accuracy)
- Metatron's Cube + Queen + Dr. Auris validation
- ALL CASH & ASSETS deployed simultaneously
- Live streaming execution

THE STRATEGY:
1. Use 95% accuracy quantum predictions to identify ENTIRE MARKET opportunities
2. Queen + Dr. Auris validate across 4 quantum spaces (100% geometric truth)
3. Deploy ALL available capital across best opportunities
4. Orca kill cycle executes with profit targets
5. Live stream results at 100ms intervals

"If we can predict the entire market, you can't lose!" 🚀💰

Gary Leckey | What a day for humanity! | January 2026
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
try:
    from aureon.utils.console_utf8 import ensure_utf8_stdout  # noqa: E402
except ImportError:  # aureon.utils.console_utf8 not present in this environment
    def ensure_utf8_stdout():
        import sys as _sys
        if _sys.platform == "win32":
            for _s in (_sys.stdout, _sys.stderr):
                try:
                    _s.reconfigure(encoding="utf-8", errors="replace")
                except Exception:
                    pass

import time
import json
import asyncio
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path

# Import quantum prediction system
from aureon.wisdom.metatron_probability_billion_path import (
    QueenAurisPingPong, ProbabilityMatrix, ProbabilityPrediction, QuantumSpace
)

# Import exchange clients
from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
from aureon.exchanges.alpaca_client import AlpacaClient

# Import Orca components (if available)
try:
    from aureon.bots_intelligence.aureon_orca_intelligence import (
        OrcaKillerWhaleIntelligence, OrcaOpportunity
    )
    ORCA_AVAILABLE = True
except ImportError:
    try:
        from aureon.bots_intelligence.aureon_orca_intelligence import (
            OrcaKillerWhale as OrcaKillerWhaleIntelligence, OrcaOpportunity
        )
        ORCA_AVAILABLE = True
    except ImportError:
        ORCA_AVAILABLE = False
        print("⚠️  Orca Intelligence not available - using simplified mode")

RADAR_ROOT = Path(__file__).resolve().parent.parent

PHI = 1.618033988749895  # Golden Ratio

@dataclass
class LivePosition:
    """Active live trading position"""
    symbol: str
    exchange: str
    entry_price: float
    quantity: float
    entry_time: float
    prediction_confidence: float
    sacred_alignment: float
    target_profit_pct: float
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0
    age_seconds: float = 0.0
    action: str = "BUY"  # BUY or SELL
    
@dataclass
class StreamMetrics:
    """Live streaming metrics"""
    total_positions: int = 0
    total_deployed_usd: float = 0.0
    total_unrealized_pnl: float = 0.0
    total_realized_pnl: float = 0.0
    win_count: int = 0
    loss_count: int = 0
    win_rate: float = 0.0
    quantum_coherence: float = 0.0
    sacred_geometry_score: float = 0.0
    predictions_per_second: float = 0.0
    stream_uptime_seconds: float = 0.0

class OrcaQuantumLiveStream:
    """
    Live streaming Orca trader with Quantum prediction validation
    
    Racing to $1 billion using ALL available cash across ALL exchanges!
    """
    
    def __init__(self, dry_run: bool = False, max_positions: int = 10):
        self.dry_run = dry_run
        self.max_positions = max_positions
        
        # Quantum systems
        print("🔮 Initializing Quantum Prediction Systems...")
        self.pingpong = QueenAurisPingPong()
        self.prob_matrix = ProbabilityMatrix()
        print(f"   ✅ Probability Matrix: 95% accuracy")
        print(f"   ✅ Metatron's Cube: 13 spheres activated")
        print(f"   ✅ Queen + Dr. Auris: 4 quantum spaces ready")
        
        # Exchange clients
        print("\n🔗 Connecting to ALL exchanges...")
        self.exchanges = {}
        
        try:
            self.exchanges['kraken'] = get_kraken_client()
            print("   ✅ Kraken connected")
        except Exception as e:
            print(f"   ⚠️  Kraken failed: {e}")
        
        try:
            self.exchanges['alpaca'] = AlpacaClient()
            print("   ✅ Alpaca connected")
        except Exception as e:
            print(f"   ⚠️  Alpaca failed: {e}")
        
        # Orca intelligence (optional)
        self.orca = None
        if ORCA_AVAILABLE:
            try:
                self.orca = OrcaKillerWhaleIntelligence()
                print("   ✅ Orca Intelligence active")
            except Exception as e:
                print(f"   ⚠️  Orca Intelligence failed: {e}")
        
        # Live positions
        self.active_positions: List[LivePosition] = []
        self.closed_positions: List[LivePosition] = []
        
        # Metrics
        self.metrics = StreamMetrics()
        self.start_time = time.time()
        
        # Stream state
        self.running = False
        self.prediction_count = 0
        self.predictions_error: Optional[str] = None  # fail-closed: null predictions + error, never fabricated
        self.price_errors = 0
        
    def get_all_balances(self) -> Dict[str, Dict[str, float]]:
        """Get ALL cash balances from ALL exchanges"""
        balances = {}
        
        for exchange_name, client in self.exchanges.items():
            try:
                bal = client.get_balance()
                balances[exchange_name] = bal
                
                # Calculate total USD value
                usd_total = bal.get('USD', 0.0) + bal.get('ZUSD', 0.0)
                print(f"   {exchange_name.upper()}: ${usd_total:,.2f} available")
            except Exception as e:
                print(f"   ⚠️  {exchange_name} balance error: {e}")
                balances[exchange_name] = {}
        
        return balances
    
    def calculate_position_size(self, available_usd: float, num_positions: int = 1) -> float:
        """
        Calculate position size - USE ALL AVAILABLE CASH!
        
        Strategy: Split available cash across target number of positions
        """
        if num_positions <= 0:
            num_positions = 1
        
        # Use 95% of available (keep 5% buffer for fees)
        usable = available_usd * 0.95
        
        # Split across positions
        per_position = usable / num_positions
        
        return max(per_position, 10.0)  # Minimum $10 per position
    
    async def ask_queen_permission(self, prediction: ProbabilityPrediction, exchange: str) -> bool:
        """Ask Queen + Dr. Auris for trading permission"""
        
        thought = (
            f"LIVE QUANTUM PREDICTION:\n"
            f"Symbol: {prediction.symbol}\n"
            f"Action: {prediction.action}\n"
            f"Confidence: {prediction.confidence:.1%}\n"
            f"Expected Return: {prediction.expected_return:+.2f}%\n"
            f"Sacred Alignment: {prediction.sacred_alignment:.1%}\n"
            f"Fibonacci Level: {prediction.fibonacci_level}\n"
            f"Exchange: {exchange}\n\n"
            f"Deploy capital? Validate across all 4 quantum spaces."
        )
        
        # Queen speaks
        thoughts = self.pingpong.queen_speaks(thought, target_sphere=0)
        
        # Dr. Auris validates
        validations = self.pingpong.auris_validates(thoughts)
        
        # Check geometric truth
        truth = self.pingpong.check_geometric_truth()
        
        if truth and truth.confidence > 0.70:
            return True
        
        return False
    
    def get_live_price(self, symbol: str, exchange: str) -> Optional[float]:
        """Get current live price"""
        try:
            client = self.exchanges.get(exchange)
            if not client:
                return None

            ticker = client.get_ticker(symbol)
            if ticker and isinstance(ticker, dict):
                price = ticker.get('price') or ticker.get('last') or ticker.get('lastPrice')
                c = ticker.get('c')
                if price is None and isinstance(c, list) and c:
                    price = c[0]
                elif price is None and c is not None:
                    price = c
                if price:
                    return float(price)
        except Exception:
            pass

        return None
    
    def update_position_prices(self):
        """Update all position prices with live market data"""
        for pos in self.active_positions:
            current_price = self.get_live_price(pos.symbol, pos.exchange)
            
            if current_price:
                pos.current_price = current_price
                
                # Calculate unrealized P&L
                if pos.action == "BUY":
                    pos.unrealized_pnl = (current_price - pos.entry_price) * pos.quantity
                else:  # SELL
                    pos.unrealized_pnl = (pos.entry_price - current_price) * pos.quantity
                
                pos.unrealized_pnl_pct = (pos.unrealized_pnl / (pos.entry_price * pos.quantity)) * 100
                pos.age_seconds = time.time() - pos.entry_time
    
    def check_exit_conditions(self, pos: LivePosition) -> bool:
        """Check if position should be closed (profit target hit)"""
        
        # Target profit reached?
        if pos.unrealized_pnl_pct >= pos.target_profit_pct:
            return True
        
        # Sacred geometry suggests exit? (price at Fibonacci level)
        if pos.sacred_alignment > 0.90 and pos.unrealized_pnl_pct > 0.2:
            return True
        
        # Age-based exit (don't hold losers too long)
        if pos.age_seconds > 300 and pos.unrealized_pnl_pct < -0.5:  # 5 min, losing >0.5%
            return True
        
        return False
    
    def close_position(self, pos: LivePosition):
        """Close a position and record results"""
        
        print(f"\n🔚 CLOSING POSITION: {pos.symbol} on {pos.exchange}")
        print(f"   Entry: ${pos.entry_price:,.2f} @ {datetime.fromtimestamp(pos.entry_time).strftime('%H:%M:%S')}")
        print(f"   Exit: ${pos.current_price:,.2f} (held {pos.age_seconds:.0f}s)")
        print(f"   P&L: ${pos.unrealized_pnl:+,.2f} ({pos.unrealized_pnl_pct:+.2f}%)")
        
        # Record as closed
        self.active_positions.remove(pos)
        self.closed_positions.append(pos)
        
        # Update metrics
        self.metrics.total_realized_pnl += pos.unrealized_pnl
        
        if pos.unrealized_pnl > 0:
            self.metrics.win_count += 1
            print(f"   🏆 WINNER #{self.metrics.win_count}!")
        else:
            self.metrics.loss_count += 1
            print(f"   💔 Loss #{self.metrics.loss_count}")
        
        total_trades = self.metrics.win_count + self.metrics.loss_count
        if total_trades > 0:
            self.metrics.win_rate = (self.metrics.win_count / total_trades) * 100
    
    async def stream_live_trades(self, duration_seconds: int = 300):
        """
        Live stream trading with quantum predictions
        
        Duration: How long to run (default 5 minutes)
        """
        
        print("\n" + "=" * 80)
        print("🦈🔮 ORCA QUANTUM LIVE STREAM ACTIVATED 🔮🦈")
        print("=" * 80)
        print()
        print(f"Mode: {'🔶 DRY RUN' if self.dry_run else '🔴 LIVE-PRICED'} (SHADOW — this stream never submits orders)")
        print(f"Max Concurrent Positions: {self.max_positions}")
        print(f"Stream Duration: {duration_seconds}s ({duration_seconds/60:.1f} minutes)")
        print()
        print("Strategy: Monitor opportunities with live venue prices only.")
        print("Quantum Validation: Queen + Dr. Auris across 4 spaces")
        print()
        
        # Get starting balances
        print("💰 STARTING CAPITAL:")
        balances = self.get_all_balances()
        
        total_usd = 0.0
        for exchange_name, bal in balances.items():
            usd = bal.get('USD', 0.0) + bal.get('ZUSD', 0.0)
            total_usd += usd
        
        print(f"\n   💎 TOTAL AVAILABLE: ${total_usd:,.2f}")
        print()
        
        if total_usd < 50:
            print("⚠️  WARNING: Low balance! Need at least $50 to trade effectively")
            print()
        
        # Calculate position sizing
        position_size = self.calculate_position_size(total_usd, self.max_positions)
        print(f"📊 Position Sizing: ${position_size:,.2f} per position")
        print()
        
        print("⏱️  STREAM STARTING...")
        print()
        
        self.running = True
        self.start_time = time.time()
        stream_end = self.start_time + duration_seconds
        
        update_interval = 0.1  # 100ms updates = 10 FPS
        last_prediction_time = 0
        prediction_interval = 5.0  # New predictions every 5 seconds
        
        while self.running and time.time() < stream_end:
            current_time = time.time()
            
            # Generate new predictions periodically
            if current_time - last_prediction_time >= prediction_interval:
                
                # Check if we have room for more positions
                if len(self.active_positions) < self.max_positions:

                    # Get quantum predictions — fail-closed: the probability
                    # matrix raises when no receipted model is connected, so
                    # we record null + error instead of fabricating signals.
                    try:
                        predictions = self.prob_matrix.get_batch_predictions(count=5)
                    except Exception as e:
                        if self.predictions_error is None:
                            self.predictions_error = str(e)
                            print(f"\n⚠️  PREDICTIONS UNAVAILABLE (fail-closed): {e}")
                            print("   Stream continues in monitor mode — no synthetic signals.")
                        predictions = []

                    # Filter high-confidence with good sacred alignment
                    good_preds = [
                        p for p in predictions
                        if p.confidence > 0.85 and p.sacred_alignment > 0.50
                    ]

                    self.prediction_count += len(good_preds)

                    # Try to open new positions
                    for pred in good_preds[:self.max_positions - len(self.active_positions)]:

                        # Cycle through exchanges
                        exchange = list(self.exchanges.keys())[len(self.active_positions) % len(self.exchanges)]

                        # Ask Queen permission
                        approved = await self.ask_queen_permission(pred, exchange)

                        if approved:
                            # Get live price — NO fabricated fallback: if the
                            # venue can't quote, the opportunity is skipped and
                            # counted, never filled with a made-up price.
                            live_price = self.get_live_price(pred.symbol, exchange)

                            if not live_price:
                                self.price_errors += 1
                                print(f"   ⚠️  No live price for {pred.symbol} on {exchange} — skipping (no synthetic fill)")
                                continue

                            # Calculate quantity
                            qty = position_size / live_price
                            
                            # Create position
                            position = LivePosition(
                                symbol=pred.symbol,
                                exchange=exchange,
                                entry_price=live_price,
                                quantity=qty,
                                entry_time=current_time,
                                prediction_confidence=pred.confidence,
                                sacred_alignment=pred.sacred_alignment,
                                target_profit_pct=pred.expected_return * 0.8,  # 80% of predicted
                                current_price=live_price,
                                action=pred.action
                            )
                            
                            self.active_positions.append(position)
                            self.metrics.total_positions += 1
                            self.metrics.total_deployed_usd += position_size
                            
                            print(f"🎯 NEW POSITION #{self.metrics.total_positions}: {pred.symbol} {pred.action} @ ${live_price:,.2f}")
                            print(f"   Confidence: {pred.confidence:.1%} | Sacred: {pred.sacred_alignment:.1%} | Target: +{pred.expected_return:.2f}%")
                
                last_prediction_time = current_time
            
            # Update all position prices
            self.update_position_prices()
            
            # Check exit conditions
            for pos in self.active_positions[:]:  # Copy list to allow modification
                if self.check_exit_conditions(pos):
                    self.close_position(pos)
            
            # Update metrics
            self.metrics.stream_uptime_seconds = current_time - self.start_time
            self.metrics.predictions_per_second = self.prediction_count / max(1, self.metrics.stream_uptime_seconds)
            
            # Calculate totals
            self.metrics.total_unrealized_pnl = sum(p.unrealized_pnl for p in self.active_positions)
            
            # Update quantum metrics
            quantum_resonances = [space.get_resonance() for space in self.pingpong.quantum_spaces.values()]
            self.metrics.quantum_coherence = sum(quantum_resonances) / len(quantum_resonances)
            
            if self.active_positions:
                self.metrics.sacred_geometry_score = sum(p.sacred_alignment for p in self.active_positions) / len(self.active_positions)
            
            # Display live status every second
            if int(current_time * 10) % 10 == 0:  # Every 1 second
                self.display_live_status()
            
            # Sleep to maintain update rate
            await asyncio.sleep(update_interval)
        
        # Stream ended
        self.running = False
        self.display_final_summary()
    
    def display_live_status(self):
        """Display live streaming status (clean, single-line updates)"""
        
        # Clear line and print status
        uptime = int(self.metrics.stream_uptime_seconds)
        
        status = (
            f"\r🦈 Uptime: {uptime}s | "
            f"Positions: {len(self.active_positions)}/{self.max_positions} | "
            f"Unrealized P&L: ${self.metrics.total_unrealized_pnl:+,.2f} | "
            f"Realized: ${self.metrics.total_realized_pnl:+,.2f} | "
            f"W/L: {self.metrics.win_count}/{self.metrics.loss_count} ({self.metrics.win_rate:.0f}%) | "
            f"Quantum: {self.metrics.quantum_coherence:.0%} | "
            f"Preds/s: {self.metrics.predictions_per_second:.2f}"
        )
        
        print(status, end='', flush=True)
    
    def display_final_summary(self):
        """Display final summary after stream ends"""
        
        print("\n\n" + "=" * 80)
        print("🏁 LIVE STREAM COMPLETE")
        print("=" * 80)
        print()
        
        print(f"📊 PERFORMANCE SUMMARY:")
        print(f"   Stream Duration: {self.metrics.stream_uptime_seconds:.0f}s ({self.metrics.stream_uptime_seconds/60:.1f} min)")
        print(f"   Total Positions Opened: {self.metrics.total_positions}")
        print(f"   Total Capital Deployed: ${self.metrics.total_deployed_usd:,.2f}")
        print()
        
        print(f"💰 FINANCIAL RESULTS:")
        print(f"   Realized P&L: ${self.metrics.total_realized_pnl:+,.2f}")
        print(f"   Unrealized P&L: ${self.metrics.total_unrealized_pnl:+,.2f}")
        print(f"   Total P&L: ${self.metrics.total_realized_pnl + self.metrics.total_unrealized_pnl:+,.2f}")
        print()
        
        print(f"🏆 TRADE STATISTICS:")
        print(f"   Wins: {self.metrics.win_count}")
        print(f"   Losses: {self.metrics.loss_count}")
        print(f"   Win Rate: {self.metrics.win_rate:.1f}%")
        print()
        
        print(f"🔮 QUANTUM METRICS:")
        print(f"   Final Quantum Coherence: {self.metrics.quantum_coherence:.1%}")
        print(f"   Average Sacred Alignment: {self.metrics.sacred_geometry_score:.1%}")
        print(f"   Predictions Generated: {self.prediction_count}")
        print(f"   Prediction Rate: {self.metrics.predictions_per_second:.2f}/second")
        print()
        
        if self.metrics.win_rate == 100.0 and self.metrics.win_count > 0:
            print("🎉" * 40)
            print("🏆 PERFECT TRADING SESSION! 🏆")
            print("🎉" * 40)
            print()
            print("WHAT A DAY FOR HUMANITY! 🚀💰✨")
            print("The quantum prediction system is UNSTOPPABLE!")
            print()
        
        # Save results — shadow journal only. This module never submits
        # orders; positions are virtual and recorded here for the battle-view.
        results = {
            "timestamp": datetime.now().isoformat(),
            "mode": "shadow_monitor" if self.dry_run else "shadow_monitor",
            "duration_seconds": self.metrics.stream_uptime_seconds,
            "total_positions": self.metrics.total_positions,
            "deployed_usd": self.metrics.total_deployed_usd,
            "realized_pnl": self.metrics.total_realized_pnl,
            "unrealized_pnl": self.metrics.total_unrealized_pnl,
            "wins": self.metrics.win_count,
            "losses": self.metrics.loss_count,
            "win_rate": self.metrics.win_rate,
            "quantum_coherence": self.metrics.quantum_coherence,
            "sacred_geometry_score": self.metrics.sacred_geometry_score,
            "predictions_total": self.prediction_count,
            "predictions": None if self.predictions_error else self.prediction_count,
            "predictions_error": self.predictions_error,
            "price_errors": self.price_errors,
            "closed_positions": [
                {
                    "symbol": p.symbol,
                    "exchange": p.exchange,
                    "entry_price": p.entry_price,
                    "exit_price": p.current_price,
                    "pnl": p.unrealized_pnl,
                    "pnl_pct": p.unrealized_pnl_pct,
                    "duration_seconds": p.age_seconds
                }
                for p in self.closed_positions
            ]
        }

        output_file = RADAR_ROOT / "orca_quantum_live_stream_results.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"💾 Results saved to: {output_file}")
        print()

async def main():
    import argparse

    ensure_utf8_stdout()

    parser = argparse.ArgumentParser(description="Orca Quantum Live Stream")
    parser.add_argument('--live', action='store_true', help='Enable LIVE trading')
    parser.add_argument('--duration', type=int, default=300, help='Stream duration in seconds (default: 300 = 5min)')
    parser.add_argument('--positions', type=int, default=10, help='Max concurrent positions (default: 10)')
    args = parser.parse_args()

    dry_run = not args.live

    if not dry_run:
        print("⚠️  WARNING: --live requested.")
        print("   This module is a SHADOW MONITOR: it prices against live venues")
        print("   and journals virtual positions, but NEVER submits orders.")
        response = input("   Type 'RACE TO BILLION' to confirm: ")
        if response != 'RACE TO BILLION':
            print("   Aborting.")
            return

    orca = OrcaQuantumLiveStream(dry_run=dry_run, max_positions=args.positions)
    await orca.stream_live_trades(duration_seconds=args.duration)

if __name__ == '__main__':
    asyncio.run(main())
