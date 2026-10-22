import requests
import os
from dotenv import load_dotenv

load_dotenv('.env')

api_key = os.getenv('CAPITAL_API_KEY')
identifier = os.getenv('CAPITAL_IDENTIFIER')
password = os.getenv('CAPITAL_PASSWORD')

url = 'https://api-capital.backend-capital.com/api/v1/session'

# Capital.com uses X-CAP-API-KEY header for auth
resp = requests.post(url, 
    json={'identifier': identifier, 'password': password},
    headers={'X-CAP-API-KEY': api_key, 'Content-Type': 'application/json'}
)
print(f'Status: {resp.status_code}')
print(f'Response: {resp.text[:500]}')
print(f'CST: {resp.headers.get("CST", "NONE")}')
print(f'X-SECURITY-TOKEN: {"EXISTS" if resp.headers.get("X-SECURITY-TOKEN") else "NONE"}')
