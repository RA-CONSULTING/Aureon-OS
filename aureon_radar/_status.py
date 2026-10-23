import sys, os
sys.path.insert(0, os.getcwd())
from aureon_phi_radar import AureonPhiRadar
radar = AureonPhiRadar()
status = radar.honey_ladder.get_status()
hp = status['honey_pot']
print('=== HONEY LADDER STATUS ===')
print('State:', radar.state.value)
print('Honey Pot:', 'ACTIVE' if hp['active'] else 'EMPTY')
if hp['active']:
    print('  Symbol:', hp['symbol'])
    print('  Direction:', hp['direction'])
    print('  Size:', hp['size'])
    print('  Held:', str(int(hp['held_seconds'])) + 's')
    print('  Target:', hp['target_price'])
    print('  Source:', hp['source'])
    print('  Rung:', hp['rung'])
ss = status['shadow_stats']
print('')
print('Shadows:', ss['total'], 'total,', ss['hits'], 'hits,', ss['open'], 'open')
print('Live trades today:', radar.live_trades_today)
print('Profit today:', '£', round(radar.profit_today, 2))
print('')
print('Source Records:')
for src, rec in status['source_records'].items():
    print('  ' + src + ': rung=' + str(rec['ladder_rung']) + ', phi_wr=' + str(round(rec['phi_win_rate'], 2)) + ', hits=' + str(rec['hits']))
print('')
print('Sector Heat:')
for sector, heat in status['sector_heat'].items():
    print('  ' + sector + ': hit_rate=' + str(round(heat['hit_rate'], 2)) + ', sweet_spot=' + str(heat['sweet_spot']))
