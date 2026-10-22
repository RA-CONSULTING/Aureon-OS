import sys, os
sys.path.insert(0, os.getcwd())
from aureon_phi_radar import AureonPhiRadar

radar = AureonPhiRadar()
print('=== RADAR STATUS ===')
print(f'State: {radar.state.value}')

status = radar.honey_ladder.get_status()
hp = status['honey_pot']
print(f'Honey Pot: {"ACTIVE" if hp["active"] else "EMPTY"}')
if hp['active']:
    print(f'  Symbol: {hp["symbol"]}')
    print(f'  Held: {hp["held_seconds"]:.0f}s')

ss = status['shadow_stats']
print(f'\nShadows: {ss["total"]} total, {ss["hits"]} hits, {ss["open"]} open')
print(f'Live trades today: {radar.live_trades_today}')

print(f'\nSource Records:')
for src, rec in status['source_records'].items():
    print(f'  {src}: rung={rec["ladder_rung"]}, phi_wr={rec["phi_win_rate"]}, hits={rec["hits"]}')

print(f'\nSector Heat:')
for sector, heat in status['sector_heat'].items():
    print(f'  {sector}: hit_rate={heat["hit_rate"]}, sweet_spot={heat["sweet_spot"]}')
