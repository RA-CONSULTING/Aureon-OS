from capital_client import CapitalClient

c = CapitalClient()
c.get_positions()  # trigger auth

search_terms = ['USDJPY', 'TSLA', 'NVDA', 'AAPL', 'GOLD', 'US100']
for term in search_terms:
    try:
        resp = c._request('GET', '/markets', params={'searchTerm': term, 'pageSize': 10})
        if resp.status_code == 200:
            data = resp.json()
            markets = data.get('markets', [])
            print(f'\n{term}:')
            for m in markets[:3]:
                epic = m.get('epic', 'N/A')
                name = m.get('instrumentName', 'N/A')
                print(f'  {epic} - {name}')
        else:
            print(f'\n{term}: HTTP {resp.status_code}')
    except Exception as e:
        print(f'\n{term}: ERROR {e}')
