import sys
sys.stdout.reconfigure(encoding='utf-8')
import os

# Load env
from dotenv import load_dotenv
load_dotenv(r'C:\Users\user\.kimi_openclaw\workspace\aureon_radar\.env')

# Now check the actual Capital.com API
import requests
import json

API_KEY = os.getenv('CAPITAL_API_KEY')
IDENTIFIER = os.getenv('CAPITAL_IDENTIFIER')
PASSWORD = os.getenv('CAPITAL_PASSWORD')
DEMO = os.getenv('CAPITAL_DEMO', '1') == '1'

BASE_URL = "https://demo-api-capital.backend-capital.com" if DEMO else "https://api-capital.backend-capital.com"

print(f"Base URL: {BASE_URL}")
print(f"Identifier: {IDENTIFIER[:10]}...")
print(f"API Key: {API_KEY[:4]}...")

# Step 1: Create session
session_url = f"{BASE_URL}/api/v1/session"
headers = {
    "X-CAP-API-KEY": API_KEY,
    "Content-Type": "application/json"
}
payload = {
    "identifier": IDENTIFIER,
    "password": PASSWORD
}

try:
    resp = requests.post(session_url, headers=headers, json=payload, timeout=15)
    print(f"Session status: {resp.status_code}")
    
    cst = resp.headers.get('CST')
    xst = resp.headers.get('X-SECURITY-TOKEN')
    
    print(f"CST received: {bool(cst)}")
    print(f"X-SECURITY-TOKEN received: {bool(xst)}")
    
    if cst and xst:
        # Step 2: Get accounts
        acc_headers = {
            "CST": cst,
            "X-SECURITY-TOKEN": xst
        }
        acc_resp = requests.get(f"{BASE_URL}/api/v1/accounts", headers=acc_headers, timeout=15)
        print(f"Accounts status: {acc_resp.status_code}")
        
        if acc_resp.status_code == 200:
            data = acc_resp.json()
            print(f"Accounts: {json.dumps(data, indent=2)[:800]}")
        else:
            print(f"Accounts error: {acc_resp.text[:300]}")
    else:
        print(f"Session body: {resp.text[:400]}")
        
except Exception as e:
    print(f"Error: {e}")
