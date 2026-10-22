import sys
sys.stdout.reconfigure(encoding='utf-8')
import os
from dotenv import load_dotenv
load_dotenv(r'C:\Users\user\.kimi_openclaw\workspace\aureon_radar\.env')

sys.path.insert(0, r'C:\Users\user\.kimi_openclaw\workspace\aureon_radar')
from aureon_dual_capital import DualCapitalConnector

dc = DualCapitalConnector()
print('Before auth:', dc.authenticated)
dc.authenticate()
print('After auth:', dc.authenticated)

# Debug the live client directly
live = dc.live
print('Live enabled:', live.enabled)
print('Live CST:', live.cst is not None)
print('Live token:', live.x_security_token is not None)

# Try raw request
import requests
headers = {
    "CST": live.cst,
    "X-SECURITY-TOKEN": live.x_security_token
}
url = "https://api-capital.backend-capital.com/api/v1/accounts"
resp = requests.get(url, headers=headers, timeout=15)
print('Raw status:', resp.status_code)
data = resp.json()
print('Raw accounts:', data)

# Check what get_account_balance sees
bal = live.get_account_balance()
print('get_account_balance returned:', bal, type(bal))
