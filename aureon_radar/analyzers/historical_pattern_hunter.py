#!/usr/bin/env python3
"""
💎🔮 HISTORICAL PATTERN HUNTER: PREDICT THE FUTURE FROM THE PAST 🔮💎

🟡 STANDALONE BACKTEST HARNESS — NOT A LIVE MEASUREMENT, NOT A TRADE EXECUTOR.
   Every figure this module prints is a PROJECTION over patterns that were
   learned from real history (`adaptive_learning_history.json`). It carries no
   synthetic pattern statistics: when the learning history holds no pattern,
   the hunter reports that absence and projects nothing — it never invents a
   win rate, a sample size, a confidence or a price.

   Path variation (which hour a learned pattern matches, where inside the
   pattern's own learned profit band a projected trade lands) is derived from
   the live HNC field via `_field_unit()` — Λ(t) first, coherence Γ second, a
   deterministic φ-rotation counter when the field is silent. There is no
   `random` anywhere in this file; the same field state gives the same sweep.

   The class is not imported by production code; only the __main__ block calls
   run_simulation(). Nothing here writes to disk or to a database. Do NOT call
   execute_pattern_trade or run_simulation from a live path.

"THE PRESENT IS A GIFT. USE THE PAST TO UNWRAP IT."

This uses ACTUAL historical patterns from adaptive_learning_history.json
to identify HIGH-PROBABILITY setups and project ONLY those.

Strategy:
- Load whatever learned patterns the history actually holds (0 is a valid answer)
- Keep only those with an 80%+ learned win rate and a real sample_size
- Project matches over 5-15 minute windows using the live field
- Compound the projection on the patterns' own recorded profit and loss
- Report unavailable whenever the history has nothing to say

£76 → £100,000 in 24 hours using HISTORICAL INTELLIGENCE
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import time
import json
import os
from dataclasses import dataclass
from typing import List, Dict, Optional

from aureon.harmonic.phi_bridge import PHI

try:
    from aureon.strategies.probability_ultimate_intelligence import ProbabilityUltimateIntelligence
    from aureon.strategies.probability_intelligence_matrix import ProbabilityIntelligenceMatrix
except ImportError:
    ProbabilityUltimateIntelligence = None
    ProbabilityIntelligenceMatrix = None


# ═══════════════════════════════════════════════════════════════════════════════
# FIELD-DERIVED PATH VARIATION — the only source of variation in this module
# ═══════════════════════════════════════════════════════════════════════════════
_INV_PHI = 1.0 / PHI      # 0.6180339887… — an irrational step, so no short cycle
_SWEEP_CURSOR = 0

# Harness arrival assumptions, per learned scenario: how often the harness lets a
# pattern of that scenario match, per projected hour. These are BACKTEST
# PARAMETERS OF THE HARNESS, not measurements of the market. A learned pattern
# that records its own 'hourly_match_rate' in adaptive_learning_history.json
# overrides the assumption; a scenario absent from both is never projected.
_BACKTEST_HOURLY_MATCH_RATE = {
    'arbitrage': 0.15,
    'recovery': 2 / 24,
    'breakout': 0.20,
    'momentum': 0.18,
    'bounce': 0.12,
    'accumulation': 1 / 24,
}

# Width of the projected profit band around a pattern's own learned average
# profit: a projected win lands in [0.85, 1.15] × avg_profit_pct. Harness path
# width, stated openly — not a measured dispersion.
_PROFIT_BAND_FLOOR = 0.85
_PROFIT_BAND_WIDTH = 0.30

_SCENARIO_HIGHLIGHT = {
    'recovery': '🎯 FLASH CRASH RECOVERY PATTERN MATCH:',
    'bounce': '💎 SUPPORT BOUNCE PATTERN MATCH:',
    'accumulation': '🐋 WHALE ACCUMULATION PATTERN MATCH:',
}


def _field_unit() -> float:
    """A deterministic value in [0.0, 1.0) taken from the live HNC field.

    Λ(t) is read through the canonical accessor (which never raises); coherence
    Γ is the second choice. Every draw also advances a φ-rotation so successive
    draws inside one field reading stay distinct without ever touching
    ``random``. When no reading is available the φ-rotation carries the sweep
    alone — still deterministic, still not a measurement, and every caller
    below labels what it uses the draw for.
    """
    global _SWEEP_CURSOR
    _SWEEP_CURSOR += 1
    rotation = (_SWEEP_CURSOR * _INV_PHI) % 1.0
    try:
        from aureon.core.hnc_field import read_canonical_field
        f = read_canonical_field()
        if f.available:
            basis = f.lambda_t if f.lambda_t is not None else f.coherence_gamma
            if basis is not None:
                return (abs(float(basis)) + rotation) % 1.0
    except Exception:
        pass
    return rotation


@dataclass
class HistoricalPattern:
    """A learned pattern from history"""
    pattern_id: str
    scenario: str  # 'recovery', 'breakout', 'cascade', etc.
    win_rate: float
    avg_profit_pct: float
    avg_loss_pct: float
    sample_size: int
    timeframe: str  # '5m', '15m', '1h'
    conditions: Dict


@dataclass
class PatternMatch:
    """A pattern match in current market"""
    pattern: HistoricalPattern
    symbol: str
    confidence: float
    predicted_move_pct: float
    timestamp: float


@dataclass
class TradeResult:
    """Trade execution result"""
    trade_num: int
    hour: int
    pattern_id: str
    entry_capital: float
    position_size: float
    profit_pct: float
    profit_amount: float
    exit_capital: float
    win: bool
    confidence: float


class HistoricalPatternHunter:
    """
    Uses historical patterns to hunt high-probability trades
    """
    
    def __init__(self):
        self.starting_capital = 76.0
        self.current_capital = self.starting_capital
        self.target_capital = 100000.0
        
        # Load historical patterns (real learned patterns only)
        self.historical_patterns = self.load_historical_patterns()
        print(f"✅ Loaded {len(self.historical_patterns)} learned historical patterns")

        # Filter for high-quality patterns (80%+ learned win rate)
        self.elite_patterns = [p for p in self.historical_patterns if p.win_rate >= 0.80]
        print(f"✅ Found {len(self.elite_patterns)} ELITE patterns (80%+ learned win rate)")

        # Callers must be able to tell the difference between "projected nothing"
        # and "projected a flat run". This flag is that signal.
        self.patterns_available = bool(self.elite_patterns)
        if not self.patterns_available:
            print("⚠️  No learned patterns with an 80%+ win rate are available.")
            print("    This harness does NOT substitute invented statistics —")
            print("    every projection below will report unavailable instead.")

        # Load probability systems
        self.ultimate_intel = None
        self.probability_matrix = None
        if ProbabilityUltimateIntelligence:
            try:
                self.ultimate_intel = ProbabilityUltimateIntelligence()
                print("✅ Probability Intelligence LOADED")
            except:
                pass
        
        if ProbabilityIntelligenceMatrix:
            try:
                self.probability_matrix = ProbabilityIntelligenceMatrix()
                print("✅ Risk Matrix LOADED")
            except:
                pass
        
        # Tracking
        self.trades = []
        self.patterns_matched = []
        self.hourly_capital = []
    
    def load_historical_patterns(self) -> List[HistoricalPattern]:
        """Load patterns from adaptive learning history.

        The learning history is the ONLY source of patterns. When it is missing,
        unparseable, or holds no pattern with a real ``sample_size``, this
        returns an empty list — the absence is the answer, and ``__init__``
        surfaces it via ``patterns_available``.
        """
        patterns = []

        # Try to load actual file
        if os.path.exists('adaptive_learning_history.json'):
            try:
                with open('adaptive_learning_history.json', 'r') as f:
                    data = json.load(f)
                    
                # Parse patterns from learning history
                for key, value in data.items():
                    if isinstance(value, dict):
                        pattern = HistoricalPattern(
                            pattern_id=key,
                            scenario=value.get('scenario', 'general'),
                            win_rate=value.get('win_rate', 0.0),
                            avg_profit_pct=value.get('avg_profit_pct', 0.0),
                            avg_loss_pct=value.get('avg_loss_pct', 0.0),
                            sample_size=value.get('sample_size', 0),
                            timeframe=value.get('timeframe', '15m'),
                            conditions=value.get('conditions', {})
                        )
                        if pattern.sample_size > 0:  # Only use patterns with data
                            patterns.append(pattern)
            except:
                pass
        
        # No synthetic top-up. The supplemental hook is still consulted (it
        # yields nothing, by design) so no invented statistic can enter here,
        # and real patterns are never discarded to reach a quota.
        if not patterns:
            patterns = self.create_elite_patterns()
        
        return patterns
    
    def create_elite_patterns(self) -> List[HistoricalPattern]:
        """Supplemental pattern source. Returns nothing — and that is deliberate.

        This used to hand back six hard-typed "proven" patterns (87% win rate on
        143 samples, 91% on 76, and so on). Not one of those figures was ever
        measured; they were invented and then presented as history, which is
        exactly the fabrication the harness must not carry. They are gone.

        The signature is preserved because it is the documented hook for a REAL
        supplemental pattern store. Wire one in here (an actual learning export,
        an actual audited pattern table) and it flows straight into the harness.
        Until then the honest answer is an empty list, and every projection
        downstream reports "unavailable" rather than a plausible number.
        """
        return []

    def scan_for_pattern_matches(self, hour: int) -> List[PatternMatch]:
        """Project which learned patterns the harness lets match during ``hour``.

        BACKTEST PROJECTION — nothing here reads an exchange, an order book or a
        price feed. Confidence and predicted move come straight off the learned
        pattern (its own real win rate, its own real average profit); no
        hand-typed confidence figure appears in this method any more, and no
        symbol is asserted unless the learned pattern actually recorded one.

        The match gate is the field-derived ``_field_unit()`` compared against
        the pattern's recorded ``hourly_match_rate`` when the learning history
        supplied one, else the harness arrival assumption for that scenario. A
        scenario present in neither is never projected.
        """
        matches = []

        for pattern in self.elite_patterns:
            rate = pattern.conditions.get('hourly_match_rate') if pattern.conditions else None
            if rate is None:
                rate = _BACKTEST_HOURLY_MATCH_RATE.get(pattern.scenario)
            if rate is None:
                continue  # no recorded arrival rate for this scenario — project nothing

            # Field-derived gate (Λ(t) / Γ / φ-rotation), never random.
            if _field_unit() >= float(rate):
                continue

            symbol = None
            if pattern.conditions:
                symbol = pattern.conditions.get('symbol')

            matches.append(PatternMatch(
                pattern=pattern,
                # The learned pattern names its own market, or it is identified
                # by its pattern id — an invented ticker is worse than none.
                symbol=str(symbol) if symbol else pattern.pattern_id,
                confidence=pattern.win_rate,
                predicted_move_pct=pattern.avg_profit_pct,
                timestamp=time.time()
            ))

            highlight = _SCENARIO_HIGHLIGHT.get(pattern.scenario)
            if highlight:
                print(f"    {highlight} {pattern.pattern_id} "
                      f"(learned win rate {pattern.win_rate * 100:.0f}%, "
                      f"n={pattern.sample_size})")

        return matches

    def calculate_position_size(self, match: PatternMatch) -> float:
        """Calculate position size based on pattern confidence and historical data"""
        # More aggressive sizing for high-confidence patterns
        base_size = self.current_capital * 0.20  # Base 20%
        
        # Boost for high confidence
        confidence_multiplier = 1.0 + (match.confidence - 0.80) * 2  # Up to 2.2x for 95% confidence
        
        # Boost for high win rate patterns
        win_rate_multiplier = 1.0 + (match.pattern.win_rate - 0.75) * 1.5
        
        # Calculate final size
        position_size = base_size * confidence_multiplier * win_rate_multiplier
        
        # Cap at 80% of capital for safety
        position_size = min(position_size, self.current_capital * 0.80)
        
        return position_size
    
    def execute_pattern_trade(self, match: PatternMatch, trade_num: int, hour: int) -> TradeResult:
        """Project one trade over a learned pattern. BACKTEST ONLY — executes nothing.

        No order is placed, no exchange is contacted, nothing is written to disk.
        The outcome is a projection: the field-derived draw is measured against
        the pattern's REAL learned win rate, a projected win lands inside the
        pattern's REAL learned average-profit band (the harness path width,
        ±15%), and a projected loss takes the pattern's real average loss
        exactly. Every figure traces back either to the learned pattern or to
        the labelled harness parameters at the top of this module.
        """
        position_size = self.calculate_position_size(match)

        # Field-derived outcome against the pattern's learned win rate.
        win = _field_unit() < match.pattern.win_rate

        if win:
            # Learned average profit, positioned inside the harness path band.
            band = _PROFIT_BAND_FLOOR + (_PROFIT_BAND_WIDTH * _field_unit())
            profit_pct = match.pattern.avg_profit_pct * band
            profit_amount = position_size * profit_pct
        else:
            # Learned average loss, taken as recorded.
            profit_pct = -match.pattern.avg_loss_pct
            profit_amount = position_size * profit_pct

        new_capital = self.current_capital + profit_amount
        
        result = TradeResult(
            trade_num=trade_num,
            hour=hour,
            pattern_id=match.pattern.pattern_id,
            entry_capital=self.current_capital,
            position_size=position_size,
            profit_pct=profit_pct,
            profit_amount=profit_amount,
            exit_capital=new_capital,
            win=win,
            confidence=match.confidence
        )
        
        self.current_capital = max(0.01, new_capital)
        return result
    
    def run_simulation(self) -> dict:
        """Project a 24-hour sweep over the learned patterns. BACKTEST ONLY.

        Returns a report carrying ``patterns_available``. When no learned
        pattern is available the numeric fields come back as ``None`` — the
        caller can tell the difference between "no patterns to project" and
        "projected a flat run", and no plausible capital figure is invented.
        """
        self.current_capital = self.starting_capital
        self.trades = []
        self.patterns_matched = []
        self.hourly_capital = []

        if not self.elite_patterns:
            print("\n" + "═" * 80)
            print("⚠️  NO LEARNED PATTERNS — NOTHING TO PROJECT")
            print("═" * 80)
            print("adaptive_learning_history.json supplied no pattern with a real")
            print("sample_size and an 80%+ learned win rate, and this harness will")
            print("not invent one. Every figure in the report comes back as None.")
            return {
                'success': False,
                'patterns_available': False,
                'final_capital': None,
                'return_pct': None,
                'total_trades': 0,
                'wins': 0,
                'losses': 0,
                'win_rate': None,
                'pattern_counts': {},
                'hourly_capital': []
            }

        trade_num = 0

        print("\n" + "═" * 80)
        print("🎯 PROJECTING LEARNED PATTERNS OVER A 24-HOUR SWEEP (BACKTEST)")
        print("═" * 80)

        for hour in range(24):
            print(f"\n📍 HOUR {hour} | Capital: £{self.current_capital:,.2f}")
            
            # Scan for pattern matches
            matches = self.scan_for_pattern_matches(hour)
            
            if matches:
                print(f"    🔍 Projected {len(matches)} pattern matches")
            
            # Execute pattern trades
            for match in matches:
                if self.current_capital >= self.target_capital:
                    break
                
                trade_num += 1
                result = self.execute_pattern_trade(match, trade_num, hour)
                self.trades.append(result)
                self.patterns_matched.append(match.pattern.pattern_id)
                
                if result.win:
                    print(f"    ✅ Trade #{trade_num}: {result.pattern_id} +{result.profit_pct*100:.1f}% → £{result.exit_capital:,.2f}")
                else:
                    print(f"    ❌ Trade #{trade_num}: {result.pattern_id} {result.profit_pct*100:.1f}% → £{result.exit_capital:,.2f}")
            
            # Track hourly
            self.hourly_capital.append((hour, self.current_capital))
            
            # Check for target
            if self.current_capital >= self.target_capital:
                print(f"\n🎯🎯🎯 TARGET HIT at Hour {hour}! 🎯🎯🎯")
                break
            
            # Check for critical loss
            if self.current_capital < self.starting_capital * 0.10:
                print(f"\n💀 Capital critically low at Hour {hour}")
                break
        
        # Calculate stats
        wins = [t for t in self.trades if t.win]
        losses = [t for t in self.trades if not t.win]
        
        # Pattern usage stats
        pattern_counts = {}
        for pattern_id in self.patterns_matched:
            pattern_counts[pattern_id] = pattern_counts.get(pattern_id, 0) + 1
        
        return {
            'success': self.current_capital >= self.target_capital,
            'patterns_available': True,
            'final_capital': self.current_capital,
            'return_pct': ((self.current_capital - self.starting_capital) / self.starting_capital) * 100,
            'total_trades': len(self.trades),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': len(wins) / len(self.trades) if self.trades else 0,
            'pattern_counts': pattern_counts,
            'hourly_capital': self.hourly_capital
        }


def run_single_simulation():
    """Run single detailed simulation"""
    print("\n" + "═" * 80)
    print("║" + " " * 78 + "║")
    print("║" + "  💎🔮 HISTORICAL PATTERN HUNTER 🔮💎  ".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("║" + "  \"The Present is a Gift. Use the Past to Unwrap It.\"  ".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("═" * 80)
    
    sim = HistoricalPatternHunter()
    report = sim.run_simulation()

    if not report.get('patterns_available'):
        print("\n" + "═" * 80)
        print("║" + "  📊 NO PROJECTION — NO LEARNED PATTERNS AVAILABLE  ".center(78) + "║")
        print("═" * 80)
        print("\nNothing was projected and nothing was invented in its place.")
        print("Populate adaptive_learning_history.json with real learned patterns")
        print("(win_rate, avg_profit_pct, avg_loss_pct, sample_size) to run a sweep.")
        print("\n" + "═" * 80)
        return

    print("\n" + "═" * 80)
    print("║" + " " * 78 + "║")
    print("║" + "  📊 PROJECTED RESULTS (BACKTEST, NOT LIVE)  ".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("═" * 80)

    print(f"\n{'STATUS:':<30} {'✅ SUCCESS' if report['success'] else '❌ FAILED'}")
    print(f"{'Final Capital:':<30} £{report['final_capital']:,.2f}")
    print(f"{'Return:':<30} {report['return_pct']:+,.1f}%")
    print(f"{'Total Trades:':<30} {report['total_trades']}")
    print(f"{'Wins:':<30} {report['wins']}")
    print(f"{'Losses:':<30} {report['losses']}")
    print(f"{'Win Rate:':<30} {report['win_rate']*100:.1f}%")
    
    print(f"\n{'PATTERNS USED:':<30}")
    for pattern_id, count in sorted(report['pattern_counts'].items(), key=lambda x: -x[1]):
        print(f"  {pattern_id:<25} {count} times")
    
    print("\n" + "═" * 80)


def run_multiple_simulations(num_sims: int = 100):
    """Run a repeated deterministic sweep over the learned patterns.

    This is NOT a Monte Carlo: there is no randomness in this module. Each run
    advances the same field-derived φ-rotation, so the spread you see is a
    deterministic sweep of the path space, reproducible from the same field
    state — read it as sensitivity analysis, not as a probability distribution.
    """
    print("\n" + "═" * 80)
    print("║" + " " * 78 + "║")
    print("║" + "  🔮 HISTORICAL PATTERN DETERMINISTIC SWEEP 🔮  ".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("═" * 80)

    print(f"\n🔮 Running {num_sims} field-derived sweeps (no randomness)...\n")

    results = []
    successes = 0
    
    for i in range(num_sims):
        sim = HistoricalPatternHunter()
        report = sim.run_simulation()

        if not report.get('patterns_available'):
            print("\n❌ SWEEP ABORTED — no learned patterns available.")
            print("   No aggregate is reported, because there is nothing real to")
            print("   aggregate and nothing was fabricated to fill the gap.")
            print("═" * 80)
            return

        results.append(report)

        if report['success']:
            successes += 1
            print(f"🎯 SUCCESS #{successes}: £{report['final_capital']:,.2f} in {len(report['hourly_capital'])} hours")
        
        if (i + 1) % 10 == 0:
            avg_final = sum(r['final_capital'] for r in results) / len(results)
            print(f"  Progress: {i+1}/{num_sims} | Success rate: {(successes/(i+1))*100:.1f}% | Avg final: £{avg_final:,.0f}")
    
    # Stats
    success_rate = successes / num_sims
    avg_return = sum(r['return_pct'] for r in results) / len(results)
    avg_trades = sum(r['total_trades'] for r in results) / len(results)
    avg_win_rate = sum(r['win_rate'] for r in results) / len(results)
    best = max(results, key=lambda x: x['final_capital'])
    
    print("\n" + "═" * 80)
    print("║" + " " * 78 + "║")
    print("║" + f"  🔮 DETERMINISTIC SWEEP RESULTS ({num_sims} PROJECTIONS)  ".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("═" * 80)
    
    print(f"\n{'SUCCESS RATE:':<30} {success_rate*100:.1f}%")
    print(f"{'Successes:':<30} {successes}/{num_sims}")
    print(f"{'Average Return:':<30} {avg_return:+,.1f}%")
    print(f"{'Average Trades:':<30} {avg_trades:.0f}")
    print(f"{'Average Win Rate:':<30} {avg_win_rate*100:.1f}%")
    
    print(f"\n{'BEST PROJECTION:':<30}")
    print(f"{'  Final Capital:':<30} £{best['final_capital']:,.2f}")
    print(f"{'  Return:':<30} {best['return_pct']:+,.1f}%")
    
    print("\n" + "═" * 80)
    if success_rate > 0:
        print("║" + " " * 78 + "║")
        print("║" + "  🔮 THE PAST PREDICTS THE PRESENT 🔮  ".center(78) + "║")
        print("║" + " " * 78 + "║")
    print("═" * 80)


def main():
    print("\n" + "═" * 80)
    print("║" + " " * 78 + "║")
    print("║" + "  💎🔮 HISTORICAL PATTERN HUNTER 🔮💎  ".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("═" * 80)
    print("\n🔮 BACKTEST PROJECTIONS over REAL learned patterns — not live results.")
    print("\n1. Single detailed projection")
    print("2. 100 projections (deterministic sweep)")
    print("3. 1000 projections (extensive sweep)")
    
    choice = input("\nSelect (1/2/3): ").strip()
    
    if choice == '1':
        run_single_simulation()
    elif choice == '2':
        run_multiple_simulations(100)
    elif choice == '3':
        run_multiple_simulations(1000)


if __name__ == "__main__":
    main()
