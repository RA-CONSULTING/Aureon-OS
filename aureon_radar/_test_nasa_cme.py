import os
import requests
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load Aureon-OS .env
load_dotenv(r'C:\.kimi_openclaw\Aureon-OS\.env')

key = os.environ.get('NASA_API_KEY', '')
print(f'NASA_API_KEY present: {bool(key)}')
print(f'Key prefix: {key[:15]}...' if key else 'NOT SET')

# Test CME endpoint
start = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
end = datetime.now().strftime('%Y-%m-%d')
url = f'https://api.nasa.gov/DONKI/CME?startDate={start}&endDate={end}&api_key={key}'
print(f'Testing NASA CME API...')
resp = requests.get(url, timeout=10)
print(f'Status: {resp.status_code}')
if resp.status_code == 200:
    data = resp.json()
    print(f'CMEs found: {len(data)}')
    if data:
        print(f'Latest: {data[0].get("activityID", "unknown")}')
        print(f'Time: {data[0].get("startTime", "unknown")}')
        print(f'Note: {data[0].get("note", "")[:100]}')
