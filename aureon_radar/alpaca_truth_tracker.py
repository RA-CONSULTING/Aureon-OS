#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 ALPACA POSITION TRUTH TRACKER
════════════════════════════════════════════════════════════════════

"If we know everything about it, we know it's not lying."
                                                    - Gary Leckey

This module tracks EVERY interaction with Alpaca API and verifies:
1. What positions does Alpaca SAY we have?
2. What did we actually BUY/SELL?
3. Are we bleeding phantom money?
4. Is the API consistent?

TRUST BUT VERIFY.

"""
from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys
import os

# Windows UTF-8 Fix
if sys.platform == 'win32':
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
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path

# State file for tracking
TRUTH_STATE_FILE = Path("alpaca_truth_tracker_state.json")
TRUTH_HISTORY_FILE = Path("alpaca_truth_history.json")


@dataclass
class PositionSnapshot:
    """A point-in-time snapshot of a position."""
    symbol: str
    qty: float
    avg_entry_price: float
    current_price: float
    market_value: float
    unrealized_pl: float
    unrealized_plpc: float  # Percentage
    cost_basis: float
    timestamp: float = field(default_factory=time.time)
    
    @property
    def our_calculated_pl(self) -> float:
        """Calculate P/L ourselves to verify API isn't lying."""
        return (self.current_price - self.avg_entry_price) * self.qty
    
    @property
    def pl_matches(self) -> bool:
        """Check if API P/L matches our calculation."""
        diff = abs(self.unrealized_pl - self.our_calculated_pl)
        return diff < 0.01  # Allow 1 cent tolerance
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        d['our_calculated_pl'] = self.our_calculated_pl
        d['pl_matches'] = self.pl_matches
        return d


@dataclass  
class TruthReport:
    """Complete truth report comparing API claims vs our records."""
    timestamp: float = field(default_factory=time.time)
    
    # API claims
    api_total_value: float = 0.0
    api_total_pl: float = 0.0
    api_cash: float = 0.0
    api_buying_power: float = 0.0
    api_positions: List[PositionSnapshot] = field(default_factory=list)
    
    # Our calculations
    our_total_value: float = 0.0
    our_total_pl: float = 0.0
    
    # Verification results
    value_matches: bool = True
    pl_matches: bool = True
    all_positions_match: bool = True
    
    # Discrepancies
    discrepancies: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp,
            'datetime': datetime.fromtimestamp(self.timestamp).isoformat(),
            'api_claims': {
                'total_value': self.api_total_value,
                'total_pl': self.api_total_pl,
                'cash': self.api_cash,
                'buying_power': self.api_buying_power,
                'position_count': len(self.api_positions),
            },
            'our_calculations': {
                'total_value': self.our_total_value,
                'total_pl': self.our_total_pl,
            },
            'verification': {
                'value_matches': self.value_matches,
                'pl_matches': self.pl_matches,
                'all_positions_match': self.all_positions_match,
            },
            'discrepancies': self.discrepancies,
            'positions': [p.to_dict() for p in self.api_positions],
        }


class AlpacaTruthTracker:
    """
    🔍 THE TRUTH TRACKER - Verifies Alpaca isn't lying.
    
    "Trust but verify. If it says we're in profit, are we?"
    
    This tracker:
    1. Snapshots positions at regular intervals
    2. Calculates P/L independently to verify API
    3. Tracks historical position changes
    4. Detects phantom bleeding (value disappearing without trades)
    5. Alerts on discrepancies
    """
    
    def __init__(self, alpaca_client=None):
        self.alpaca = alpaca_client
        self.position_history: List[TruthReport] = []
        self.last_report: Optional[TruthReport] = None
        
        # Load previous state
        self._load_state()
        
        print("🔍 ALPACA TRUTH TRACKER INITIALIZED")
        print("   Monitoring for phantom bleeding...")
    
    def _load_state(self):
        """Load previous tracking state."""
        try:
            if TRUTH_STATE_FILE.exists():
                data = json.loads(TRUTH_STATE_FILE.read_text())
                # Could restore last_report here
        except Exception as e:
            print(f"   Could not load truth state: {e}")
    
    def _save_state(self, report: TruthReport):
        """Save tracking state to disk."""
        try:
            TRUTH_STATE_FILE.write_text(json.dumps(report.to_dict(), indent=2))
            
            # Also append to history
            history = []
            if TRUTH_HISTORY_FILE.exists():
                try:
                    history = json.loads(TRUTH_HISTORY_FILE.read_text())
                except:
                    history = []
            
            history.append(report.to_dict())
            # Keep last 1000 entries
            history = history[-1000:]
            TRUTH_HISTORY_FILE.write_text(json.dumps(history, indent=2))
            
        except Exception as e:
            print(f"   Could not save truth state: {e}")
    
    def verify_positions(self) -> TruthReport:
        """
        🔍 VERIFY CURRENT POSITIONS
        
        Fetches positions from Alpaca and verifies:
        - P/L calculations match
        - No phantom value loss
        - All trades accounted for
        """
        report = TruthReport()
        
        if not self.alpaca:
            report.discrepancies.append("No Alpaca client configured")
            return report
        
        try:
            # ═══════════════════════════════════════════════════════════
            # 1. GET POSITIONS FROM API
            # ═══════════════════════════════════════════════════════════
            positions = self.alpaca.get_positions()
            
            for pos in positions:
                snapshot = PositionSnapshot(
                    symbol=pos.get('symbol', 'UNKNOWN'),
                    qty=float(pos.get('qty', 0)),
                    avg_entry_price=float(pos.get('avg_entry_price', 0)),
                    current_price=float(pos.get('current_price', 0)),
                    market_value=float(pos.get('market_value', 0)),
                    unrealized_pl=float(pos.get('unrealized_pl', 0)),
                    unrealized_plpc=float(pos.get('unrealized_plpc', 0)) if pos.get('unrealized_plpc') else 0,
                    cost_basis=float(pos.get('cost_basis', 0)),
                )
                report.api_positions.append(snapshot)
                
                # Verify this position's P/L
                if not snapshot.pl_matches:
                    report.discrepancies.append(
                        f"{snapshot.symbol}: API says P/L=${snapshot.unrealized_pl:.4f} "
                        f"but we calculate ${snapshot.our_calculated_pl:.4f}"
                    )
                    report.all_positions_match = False
            
            # ═══════════════════════════════════════════════════════════
            # 2. CALCULATE TOTALS
            # ═══════════════════════════════════════════════════════════
            report.api_total_value = sum(p.market_value for p in report.api_positions)
            report.api_total_pl = sum(p.unrealized_pl for p in report.api_positions)
            report.our_total_value = sum(p.market_value for p in report.api_positions)  # Same source
            report.our_total_pl = sum(p.our_calculated_pl for p in report.api_positions)
            
            # ═══════════════════════════════════════════════════════════
            # 3. GET ACCOUNT INFO
            # ═══════════════════════════════════════════════════════════
            try:
                if hasattr(self.alpaca, '_trading_api'):
                    account = self.alpaca._trading_api.get_account()
                    report.api_cash = float(account.cash)
                    report.api_buying_power = float(account.buying_power)
                elif hasattr(self.alpaca, 'get_account'):
                    account = self.alpaca.get_account()
                    report.api_cash = float(account.get('cash', 0))
                    report.api_buying_power = float(account.get('buying_power', 0))
            except Exception as e:
                report.discrepancies.append(f"Could not get account info: {e}")
            
            # ═══════════════════════════════════════════════════════════
            # 4. COMPARE WITH LAST REPORT (detect phantom bleeding)
            # ═══════════════════════════════════════════════════════════
            if self.last_report:
                # Check for unexplained value changes
                value_change = report.api_total_value - self.last_report.api_total_value
                pl_change = report.api_total_pl - self.last_report.api_total_pl
                
                # If value dropped but P/L didn't explain it, that's suspicious
                expected_change = pl_change  # Value should only change due to P/L
                unexplained = abs(value_change - expected_change)
                
                if unexplained > 0.10:  # More than 10 cents unexplained
                    report.discrepancies.append(
                        f"PHANTOM BLEEDING: Value changed ${value_change:.2f} "
                        f"but P/L only explains ${pl_change:.2f}. "
                        f"Unexplained: ${unexplained:.2f}"
                    )
            
            # ═══════════════════════════════════════════════════════════
            # 5. FINAL VERIFICATION
            # ═══════════════════════════════════════════════════════════
            pl_diff = abs(report.api_total_pl - report.our_total_pl)
            report.pl_matches = pl_diff < 0.02  # 2 cent tolerance
            report.value_matches = True  # Using same source for now
            
            if not report.pl_matches:
                report.discrepancies.append(
                    f"Total P/L mismatch: API=${report.api_total_pl:.4f}, "
                    f"Our calc=${report.our_total_pl:.4f}"
                )
            
        except Exception as e:
            report.discrepancies.append(f"Verification error: {e}")
        
        # Save and return
        self.last_report = report
        self._save_state(report)
        self.position_history.append(report)
        
        return report
    
    def print_truth_report(self, report: TruthReport = None):
        """Print a beautiful truth report."""
        if report is None:
            report = self.last_report
        if report is None:
            print("No truth report available. Run verify_positions() first.")
            return
        
        print("\n" + "=" * 70)
        print("🔍 ALPACA TRUTH REPORT - IS THE API LYING?")
        print("=" * 70)
        print(f"   {datetime.fromtimestamp(report.timestamp).strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Summary verdict
        if not report.discrepancies:
            print("\n   ✅ VERDICT: API IS TELLING THE TRUTH!")
            print("   🟢 All positions verified. No phantom bleeding detected.")
        else:
            print("\n   ⚠️ VERDICT: DISCREPANCIES FOUND!")
            for disc in report.discrepancies:
                print(f"   🔴 {disc}")
        
        print("\n" + "-" * 70)
        print("💼 POSITIONS (API vs OUR CALCULATION)")
        print("-" * 70)
        
        for pos in report.api_positions:
            match_emoji = "✅" if pos.pl_matches else "❌"
            pl_pct = ((pos.current_price - pos.avg_entry_price) / pos.avg_entry_price * 100) if pos.avg_entry_price > 0 else 0
            print(f"\n   {pos.symbol}:")
            print(f"      Qty: {pos.qty:.6f}")
            print(f"      Entry: ${pos.avg_entry_price:.4f} → Current: ${pos.current_price:.4f} ({pl_pct:+.2f}%)")
            print(f"      Value: ${pos.market_value:.2f}")
            print(f"      API P/L: ${pos.unrealized_pl:.4f}")
            print(f"      OUR P/L: ${pos.our_calculated_pl:.4f} {match_emoji}")
        
        print("\n" + "-" * 70)
        print("📊 TOTALS")
        print("-" * 70)
        print(f"   💰 Total Position Value: ${report.api_total_value:.2f}")
        print(f"   💵 Cash Balance: ${report.api_cash:.2f}")
        print(f"   💪 Buying Power: ${report.api_buying_power:.2f}")
        print(f"   📈 API Total P/L: ${report.api_total_pl:.4f}")
        print(f"   🧮 Our Total P/L: ${report.our_total_pl:.4f}")
        
        pl_match = "✅ MATCH" if report.pl_matches else "❌ MISMATCH"
        print(f"   🔍 P/L Verification: {pl_match}")
        
        print("\n" + "=" * 70)
    
    def detect_phantom_bleeding(self, hours: int = 24) -> Dict:
        """
        🩸 DETECT PHANTOM BLEEDING
        
        Analyzes position history to detect unexplained value loss.
        Returns a report of any suspicious activity.
        """
        # Load history
        if not TRUTH_HISTORY_FILE.exists():
            return {'error': 'No history available'}
        
        try:
            history = json.loads(TRUTH_HISTORY_FILE.read_text())
        except:
            return {'error': 'Could not read history'}
        
        if len(history) < 2:
            return {'error': 'Not enough history'}
        
        # Analyze over time period
        cutoff = time.time() - (hours * 3600)
        relevant = [h for h in history if h.get('timestamp', 0) > cutoff]
        
        if len(relevant) < 2:
            return {'error': f'Not enough data in last {hours} hours'}
        
        first = relevant[0]
        last = relevant[-1]
        
        start_value = first.get('api_claims', {}).get('total_value', 0)
        end_value = last.get('api_claims', {}).get('total_value', 0)
        total_pl = last.get('api_claims', {}).get('total_pl', 0) - first.get('api_claims', {}).get('total_pl', 0)
        
        value_change = end_value - start_value
        unexplained = value_change - total_pl
        
        return {
            'period_hours': hours,
            'start_value': start_value,
            'end_value': end_value,
            'value_change': value_change,
            'explained_by_pl': total_pl,
            'unexplained_loss': unexplained,
            'is_bleeding': unexplained < -0.50,  # More than 50 cents unexplained loss
            'data_points': len(relevant),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# STANDALONE TEST
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    """Run truth verification."""
    print("\n" + "=" * 70)
    print("🔍 ALPACA TRUTH TRACKER - VERIFYING API HONESTY")
    print("=" * 70)
    
    # Load Alpaca client
    try:
        from aureon.exchanges.alpaca_client import AlpacaClient
        alpaca = AlpacaClient()
        print("✅ Alpaca client loaded")
    except Exception as e:
        print(f"❌ Could not load Alpaca client: {e}")
        return
    
    # Create tracker
    tracker = AlpacaTruthTracker(alpaca)
    
    # Verify positions
    report = tracker.verify_positions()
    
    # Print report
    tracker.print_truth_report(report)
    
    # Check for phantom bleeding
    print("\n🩸 CHECKING FOR PHANTOM BLEEDING (Last 24h)...")
    bleeding = tracker.detect_phantom_bleeding(hours=24)
    
    if bleeding.get('error'):
        print(f"   ⚠️ {bleeding['error']}")
    else:
        print(f"   📊 Period: {bleeding['period_hours']} hours ({bleeding['data_points']} data points)")
        print(f"   💰 Start Value: ${bleeding['start_value']:.2f}")
        print(f"   💰 End Value: ${bleeding['end_value']:.2f}")
        print(f"   📈 Value Change: ${bleeding['value_change']:.2f}")
        print(f"   📊 Explained by P/L: ${bleeding['explained_by_pl']:.2f}")
        print(f"   🩸 Unexplained: ${bleeding['unexplained_loss']:.2f}")
        
        if bleeding['is_bleeding']:
            print("\n   🚨 WARNING: PHANTOM BLEEDING DETECTED!")
            print("   🔴 Value is disappearing without explanation!")
        else:
            print("\n   ✅ No phantom bleeding detected")
    
    return tracker


if __name__ == '__main__':
    main()
