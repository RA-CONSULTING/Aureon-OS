#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.getcwd())

from aureon_phi_radar import AureonPhiRadar, SystemState

radar = AureonPhiRadar()
print('=== RADAR STATUS ===')
print(f"State: {radar.state.value}")
print(f"Live trades today: {radar.live_trades_today}")
print(f"Profit today: £{radar.profit_today:.2f}")
print()

stats = radar.validator.get_stats()
print('=== SHADOW STATS ===')
print(f"Total shadow trades: {stats['total_trades']}")
print(f"Win rate: {stats['win_rate']:.1%}")
print(f"Open shadows: {stats['open_trades']}")
print(f"Validated signals: {stats['validated_signals']}")
print()

print('=== AUTO-ARM CHECK ===')
print(f"Min trades needed: {radar.validator.min_trades_to_arm}")
print(f"Auto-arm threshold: {radar.validator.auto_arm_threshold:.0%}")
print(f"Can auto-arm: {radar.validator.should_auto_arm()}")
print()

# Check positions
positions = radar.capital_live.get_positions()
print(f"=== LIVE POSITIONS ({len(positions)}) ===")
for p in positions:
    pos = p.get('position', {})
    mkt = p.get('market', {})
    epic = mkt.get('epic', '?')
    direction = pos.get('direction', '?')
    size = pos.get('size', 0)
    level = pos.get('level', 0)
    upl = pos.get('upl', 0)
    print(f"  {direction} {size} {epic} @ {level} (UPL: £{upl})")

print()
print('=== BALANCE ===')
bal = radar.capital_live.get_account_balance()
print(f"£{bal:.2f}")
