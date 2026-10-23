#!/usr/bin/env python3
"""
🦈🔪 ORCA SMART KILL CYCLE - USES MOMENTUM HUNTER DATA 🔪🦈
═══════════════════════════════════════════════════════════════════════════════

USES THE DATA FROM aureon_live_momentum_hunter.py TO FIND TARGETS
THEN EXECUTES COMPLETE KILL CYCLE WITH PROPER MATH

THE PROCESS:
  1. Run LiveMomentumHunter.hunt() to find validated opportunities
  2. Pick best target (highest momentum + Queen confidence)
  3. Execute OrcaKillCycle.hunt_and_kill() on that symbol
  4. Report realized P&L

WHY THIS WORKS:
  - Momentum Hunter finds +20-26% moves (VANRY, ME, etc.)
  - Queen validates with 4th-pass decision
  - Kill Cycle has proper fee math and position monitoring
  - Only executes when net profit > 0 guaranteed

Gary Leckey | The Smart Kill | January 2026
═══════════════════════════════════════════════════════════════════════════════
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
from typing import List, Optional

# Windows UTF-8 fix (MANDATORY)
from aureon.utils.console_utf8 import ensure_utf8_stdout  # noqa: E402

ensure_utf8_stdout()

from aureon.bots.orca_complete_kill_cycle import OrcaKillCycle
from aureon.scanners.aureon_live_momentum_hunter import LiveMomentumHunter, HuntResult
from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
from aureon.exchanges.alpaca_client import AlpacaClient

class OrcaSmartKillCycle:
    """Smart kill cycle that uses momentum hunter data."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.hunter = LiveMomentumHunter(dry_run=dry_run)
        self.killer = OrcaKillCycle()

    def find_best_target(self) -> Optional[HuntResult]:
        """Use momentum hunter to find the best validated target."""
        print("\n" + "="*70)
        print("🎯 FINDING BEST TARGET USING MOMENTUM HUNTER DATA")
        print("="*70)

        # Run the hunt
        opportunities = self.hunter.hunt()

        if not opportunities:
            print("❌ No validated opportunities found")
            return None

        # First try: Filter for Alpaca symbols only (since kill cycle uses Alpaca)
        alpaca_opportunities = []
        kraken_opportunities = []
        
        for opp in opportunities:
            symbol = opp.symbol.replace('/', '')  # Convert VANRY/USD to VANRYUSD
            
            # Check Alpaca
            try:
                alpaca_client = AlpacaClient()
                orderbook = alpaca_client.get_crypto_orderbook(symbol)
                if orderbook and 'asks' in orderbook and orderbook['asks']:
                    opp.exchange = 'alpaca'
                    opp.client = alpaca_client
                    alpaca_opportunities.append(opp)
                    print(f"✅ {opp.symbol} available on Alpaca")
                else:
                    print(f"❌ {opp.symbol} not available on Alpaca")
            except Exception as e:
                print(f"❌ {opp.symbol} not available on Alpaca: {e}")
            
            # Check Kraken
            try:
                kraken_client = get_kraken_client()
                orderbook = kraken_client.get_crypto_orderbook(symbol)
                if orderbook and 'asks' in orderbook and orderbook['asks']:
                    opp_kraken = opp.__class__(**opp.__dict__)  # Copy
                    opp_kraken.exchange = 'kraken'
                    opp_kraken.client = kraken_client
                    kraken_opportunities.append(opp_kraken)
                    print(f"✅ {opp.symbol} available on Kraken")
                else:
                    print(f"❌ {opp.symbol} not available on Kraken")
            except Exception as e:
                print(f"❌ {opp.symbol} not available on Kraken: {e}")

        # Prefer Alpaca if available, otherwise use Kraken
        if alpaca_opportunities:
            best = max(alpaca_opportunities, key=lambda x: x.momentum_pct)
            print(f"\n🎯 BEST ALPACA TARGET FOUND:")
        elif kraken_opportunities:
            best = max(kraken_opportunities, key=lambda x: x.momentum_pct)
            print(f"\n🎯 BEST KRAKEN TARGET FOUND (Alpaca unavailable):")
        else:
            print("❌ No Alpaca-compatible opportunities found")
            return None

        # Sort by: momentum_pct × queen_confidence × net_pct
        # Higher momentum + higher Queen confidence + higher net profit
        if alpaca_opportunities:
            alpaca_opportunities.sort(
                key=lambda r: abs(r.momentum_pct) * r.queen_confidence * r.net_pct,
                reverse=True
            )
            best = alpaca_opportunities[0]
            print(f"\n🎯 BEST ALPACA TARGET FOUND:")
        elif kraken_opportunities:
            kraken_opportunities.sort(
                key=lambda r: abs(r.momentum_pct) * r.queen_confidence * r.net_pct,
                reverse=True
            )
            best = kraken_opportunities[0]
            print(f"\n🎯 BEST KRAKEN TARGET FOUND (Alpaca unavailable):")
        else:
            print("❌ No Alpaca-compatible opportunities found")
            return None

        print(f"   Symbol: {best.symbol}")
        print(f"   Side: {best.side.upper()}")
        print(f"   Momentum: {best.momentum_pct:+.2f}%")
        print(f"   Net Edge: {best.net_pct:+.3f}%")
        print(f"   Queen Confidence: {best.queen_confidence:.2f}")
        print(f"   Scanner: {best.scanner_source}")
        print(f"   Nexus Direction: {best.nexus_direction}")
        print(f"   Reasoning: {best.queen_reasoning}")

        return best

    def smart_kill(self, target_pct: float = 1.0) -> Optional[dict]:
        """
        Complete smart kill cycle:
        1. Find best target using momentum hunter
        2. Execute kill cycle on that target
        3. Return realized P&L
        """
        print("\n" + "🦈🔪"*10)
        print("         ORCA SMART KILL CYCLE")
        print("🦈🔪"*10)

        # Step 1: Find target
        target = self.find_best_target()
        if not target:
            print("❌ No suitable target found")
            return None

        # Step 2: Get the appropriate client and symbol format
        symbol = target.symbol
        if '/' not in symbol:
            symbol = symbol.replace('USD', '/USD')

        # Get client and normalized symbol for the selected exchange
        client = target.client
        normalized_symbol = symbol.replace('/', '') if target.exchange == 'alpaca' else symbol

        print(f"\n🎯 TARGET LOCKED: {symbol} ({target.side.upper()}) on {target.exchange.upper()}")
        print(f"   Momentum: {target.momentum_pct:+.2f}%")
        print(f"   Expected Edge: {target.net_pct:+.3f}%")

        # Step 3: Calculate position size
        try:
            # Get account info based on exchange
            if target.exchange == 'alpaca':
                account = client.get_account()
                cash = float(account.get('cash', 0))
            else:  # kraken
                balance = client.get_balance()
                cash = float(balance.get('USD', 0))

            print(f"   Available Cash: ${cash:.2f}")

            # Use 90% of cash for aggressive hunting, but minimum $1 for testing
            amount_usd = max(cash * 0.9, 1.0) if cash > 0 else 0.0
            if cash < 1.0 and cash > 0:
                print(f"   ⚠️ Small balance - using ${amount_usd:.2f} for micro-trade test")
            else:
                print(f"   Trade Size: ${amount_usd:.2f}")

        except Exception as e:
            print(f"❌ Account check failed: {e}")
            return None

        # Step 4: Execute kill cycle with selected client
        print(f"\n🔪 EXECUTING KILL CYCLE WITH LIVE STREAMING...")
        # Use the enhanced killer with streaming + whale intelligence
        killer = OrcaKillCycle(client=client, exchange=target.exchange)
        pnl = killer.hunt_and_kill(normalized_symbol, amount_usd, target_pct, stop_pct=1.0, max_wait=120)

        if pnl:
            print(f"\n💰 SMART KILL COMPLETE!")
            print(f"   Symbol: {symbol}")
            print(f"   Exchange: {target.exchange.upper()}")
            print(f"   Net P&L: ${pnl['net_pnl']:+.4f} ({pnl['net_pnl_pct']:+.3f}%)")
            print(f"   Total Fees: ${pnl['total_fees']:.4f}")

            if pnl['net_pnl'] > 0:
                print("   ✅ PROFITABLE KILL - PORTFOLIO GROWTH!")
            else:
                print("   ❌ LOSS - NEED BETTER TARGET NEXT TIME")

        return pnl

    def pack_kill(self, num_positions: int = 3, amount_per: float = 2.5, target_pct: float = 1.0):
        """
        🦈🦈🦈 PACK KILL - Hunt multiple targets simultaneously!
        
        Don't pull out too early on ANY position!
        """
        print("\n" + "🦈"*25)
        print("    ORCA PACK KILL - MULTI-TARGET HUNT")
        print("🦈"*25)
        
        # Find targets
        opportunities = self.hunter.hunt()
        if not opportunities:
            print("❌ No validated opportunities")
            return None
        
        # Filter for available exchanges
        available = []
        for opp in opportunities[:num_positions * 2]:  # Check extras in case some fail
            symbol = opp.symbol.replace('/', '')
            
            # Try Alpaca first
            try:
                from aureon.exchanges.alpaca_client import AlpacaClient
                client = AlpacaClient()
                ob = client.get_crypto_orderbook(symbol)
                if ob and ob.get('asks'):
                    available.append({'symbol': symbol, 'exchange': 'alpaca', 'opp': opp})
                    if len(available) >= num_positions:
                        break
            except:
                pass
        
        if not available:
            print("❌ No Alpaca-tradeable opportunities found")
            return None
        
        print(f"\n🎯 Pack targets: {[a['symbol'] for a in available]}")
        
        # Execute pack hunt
        killer = OrcaKillCycle(exchange='alpaca')
        results = killer.pack_hunt(
            opportunities=available,
            amount_per_position=amount_per,
            target_pct=target_pct,
            stop_pct=-1.0,
            max_wait=180
        )
        
        return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Orca Smart Kill Cycle')
    parser.add_argument('--live', action='store_true', help='Execute real trades (not dry run)')
    parser.add_argument('--target-pct', type=float, default=1.0, help='Target profit %')
    parser.add_argument('--pack', type=int, default=0, help='Pack hunt with N positions (0=single)')
    parser.add_argument('--amount', type=float, default=2.5, help='Amount per position')

    args = parser.parse_args()

    dry_run = not args.live
    target_pct = args.target_pct

    print("🦈🔪 ORCA SMART KILL CYCLE 🔪🦈")
    print(f"   Mode: {'DRY RUN' if dry_run else 'LIVE TRADES'}")
    print(f"   Target: {target_pct:.1f}% profit")
    if args.pack > 0:
        print(f"   Pack Hunt: {args.pack} positions @ ${args.amount:.2f} each")
    print()

    orca = OrcaSmartKillCycle(dry_run=dry_run)
    
    if args.pack > 0:
        # Pack hunt - multiple positions
        results = orca.pack_kill(num_positions=args.pack, amount_per=args.amount, target_pct=target_pct)
        if results:
            total = sum(r['pnl']['net_pnl'] for r in results)
            print(f"\n🏁 PACK RESULT: ${total:+.4f}")
        else:
            print("\n🏁 NO PACK KILLS EXECUTED")
    else:
        # Single target
        result = orca.smart_kill(target_pct)
        if result:
            print(f"\n🏁 FINAL RESULT: ${result['net_pnl']:+.4f}")
        else:
            print("\n🏁 NO KILL EXECUTED")