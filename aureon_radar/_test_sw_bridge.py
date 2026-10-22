import sys
import json
sys.path.insert(0, r'C:\.kimi_openclaw\Aureon-OS\aureon\data_feeds')
from aureon_space_weather_bridge import SpaceWeatherBridge

b = SpaceWeatherBridge()
r = b.get_live_data(force_refresh=True)
d = r.to_dict()
print(json.dumps(d, indent=2))
print()
print(f"CMEs: {d['cmes_24h']}")
print(f"NASA-CME in sources: {'NASA-CME' in d['active_sources']}")
