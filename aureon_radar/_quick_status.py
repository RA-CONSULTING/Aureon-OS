import sys, os
sys.path.insert(0, os.getcwd())
from aureon_phi_radar import AureonPhiRadar
radar = AureonPhiRadar()
status = radar.honey_ladder.get_status()
hp = status['honey_pot']
print('Honey Pot:', 'ACTIVE' if hp['active'] else 'EMPTY')
if hp['active']:
    print('  Symbol:', hp['symbol'])
    print('  Direction:', hp['direction'])
    print('  Size:', hp['size'])
    print('  Held:', f"{hp['held_seconds']:.0f}s")
    print('  Target:', hp['target_price'])
    print('  Stop:', hp['stop_loss'])
    print('  Source:', hp['source'])
    print('  Rung:', hp['rung'])
ss = status['shadow_stats']
print('\nShadows:', ss['total'], 'total,', ss['hits'], 'hits,', ss['open'], 'open')
print('Live trades today:', radar.live_trades_today)
print('Cycle:', radar.cycle_count)
