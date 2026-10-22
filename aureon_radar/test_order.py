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

# Test placing a small order
payload = {
    "epic": "NATURALGAS",
    "direction": "BUY",
    "size": 0.01,
    "orderType": "MARKET",
    "guaranteedStop": False,
    "forceOpen": True,
    "currencyCode": "GBP"
}

order = requests.post(
    "https://api-capital.backend-capital.com/api/v1/positions",
    json=payload,
    headers={"X-CAP-API-KEY": os.environ['CAPITAL_API_KEY'], "CST": cst, "X-SECURITY-TOKEN": xsec, "Content-Type": "application/json"}
)
print("Order status:", order.status_code)
print(order.text[:500])
