from aureon_dual_capital import DualCapitalConnector

dc = DualCapitalConnector()
print('=== DUAL CAPITAL STATUS ===')
status = dc.get_status()
print('Demo ready:', status['demo']['ready'])
print('Demo balance:', status['demo']['balance'])
print('Demo positions:', status['demo']['positions'])
print('Live ready:', status['live']['ready'])
print('Live balance:', status['live']['balance'])
print('Live positions:', status['live']['positions'])

# Show demo positions detail
print('\n=== DEMO POSITIONS ===')
demo_pos = dc.get_demo_positions()
for p in demo_pos:
    position = p.get('position', {})
    market = p.get('market', {})
    epic = market.get('epic', '?')
    direction = position.get('direction', '?')
    size = position.get('size', 0)
    upl = position.get('upl', 0)
    print(f'  {direction} {size} {epic} UPL={upl}')

# Show live positions detail
print('\n=== LIVE POSITIONS ===')
live_pos = dc.get_live_positions()
for p in live_pos:
    position = p.get('position', {})
    market = p.get('market', {})
    epic = market.get('epic', '?')
    direction = position.get('direction', '?')
    size = position.get('size', 0)
    upl = position.get('upl', 0)
    print(f'  {direction} {size} {epic} UPL={upl}')
