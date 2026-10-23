from capital_client import CapitalClient
import requests

c = CapitalClient()
c.authenticate()
print('auth ok')

if hasattr(c, 'session'):
    h = c.session.headers
    tok = h.get('X-SECURITY-TOKEN', 'N/A')
    cst = h.get('CST', 'N/A')
    print('token:', tok[:20] if tok else 'N/A')
    print('cst:', cst[:20] if cst else 'N/A')
    
    # Fetch deal history
    resp = requests.get('https://api-capital.backend-capital.com/api/v1/history/activity?pageSize=50', headers=h, timeout=10)
    print('status:', resp.status_code)
    if resp.status_code == 200:
        data = resp.json()
        acts = data.get('activities', [])
        print(f'activities: {len(acts)}')
        for a in acts[:20]:
            desc = a.get('description', '?')
            date = a.get('date', '?')
            print(f'  {date} | {desc}')
    else:
        print('error:', resp.text[:200])
