import sys
sys.path.insert(0, r'C:\.kimi_openclaw\Aureon-OS\aureon\data_feeds')
from aureon_space_weather_bridge import SpaceWeatherBridge
import os

b = SpaceWeatherBridge()
key = b._get_nasa_api_key()
print(f"NASA key found: {bool(key)}")
print(f"Key prefix: {key[:15]}..." if key else "NONE")

# Test the CME fetch directly
count = b._fetch_cmes()
print(f"CME count from _fetch_cmes: {count}")
