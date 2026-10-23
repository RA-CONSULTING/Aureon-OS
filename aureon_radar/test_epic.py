import os
import requests
import json

# Auth
resp = requests.post(
    "https://api-capital.backend-capital.com/api/v1/session",
    json={"identifier": os.environ['CAPITAL_IDENTIFIER'], "password": os.environ['CAPITAL_PASSWORD']},
    headers={"X-CAP-API-KEY": os.environ['CAPITAL_API_KEY'], "Content-Type": "application/json"}
)
cst = resp.headers.get("CST")
xsec = resp.headers.get("X-SECURITY-TOKEN")

# Search for NATURALGAS
search = requests.get(
    "https://api-capital.backend-capital.com/api/v1/markets",
    params={"searchTerm": "NATURALGAS", "pageSize": 10},
    headers={"X-CAP-API-KEY": os.environ['CAPITAL_API_KEY'], "CST": cst, "X-SECURITY-TOKEN": xsec}
)
print("Search status:", search.status_code)
data = search.json()
if "markets" in data:
    for m in data["markets"]:
        print(f"  {m.get('epic')} | {m.get('instrumentName')} | {m.get('symbol')}")

# Also try just getting the market directly
market = requests.get(
    "https://api-capital.backend-capital.com/api/v1/markets/NATURALGAS",
    headers={"X-CAP-API-KEY": os.environ['CAPITAL_API_KEY'], "CST": cst, "X-SECURITY-TOKEN": xsec}
)
print("\nDirect market status:", market.status_code)
print(market.text[:500])
