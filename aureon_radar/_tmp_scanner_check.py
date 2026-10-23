import sys
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
_trader = Path(__file__).resolve().parents[1] / "aureon" / "exchanges" / "capital_cfd_trader.py"
with open(_trader, "r", encoding="utf-8") as f:
    content = f.read()

print('=== SCANNER/INTELLIGENCE IMPORTS ===')
for line in content.split('\n'):
    if 'import' in line and any(k in line.lower() for k in ['scanner', 'momentum', 'orderbook', 'whale', 'intel', 'mind', 'mycelium', 'fusion', 'nexus', 'seer', 'lyra']):
        print(line.strip()[:100])

print()
print('=== KEY METHOD CALLS ===')
for line in content.split('\n'):
    stripped = line.strip()
    if any(k in stripped.lower() for k in ['_refresh_unified', '_refresh_mind', '_refresh_mycelium', '_find_best', '_quad_gate', '_ranked', 'momentum', 'orderbook', 'whale']):
        if not stripped.startswith('#'):
            print(stripped[:100])
