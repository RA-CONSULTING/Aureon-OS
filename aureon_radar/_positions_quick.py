import sys, os
sys.path.insert(0, os.getcwd())
from aureon_phi_radar import CapitalConnector

c = CapitalConnector(demo=False)
c.authenticate()
pos = c.get_positions()
print(f'Total positions: {len(pos)}')
for p in pos[:5]:
    position = p.get('position', {})
    market = p.get('market', {})
    epic = market.get('epic', '?')
    direction = position.get('direction', '?')
    size = position.get('size', 0)
    level = position.get('level', 0)
    upl = position.get('upl', 0)
    print(f"  {direction} {size} {epic} @ {level} UPL={upl}")
if len(pos) > 5:
    print(f'  ... and {len(pos)-5} more')
