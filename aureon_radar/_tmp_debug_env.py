import sys, os
sys.stdout.reconfigure(encoding='utf-8')

try:
    from dotenv import load_dotenv
    print('python-dotenv: OK')
except ImportError:
    print('python-dotenv: NOT INSTALLED')
    exit()

load_dotenv(r'C:\Users\user\.kimi_openclaw\workspace\aureon_radar\.env')

vars_to_check = ['CAPITAL_API_KEY', 'CAPITAL_IDENTIFIER', 'CAPITAL_PASSWORD', 'CAPITAL_DEMO']
for v in vars_to_check:
    val = os.getenv(v, 'NOT_SET')
    if val == 'NOT_SET':
        print(f'{v}=NOT_SET')
    else:
        print(f'{v}={val[:4]}... (len={len(val)})')

sys.path.insert(0, r'C:\Users\user\.kimi_openclaw\workspace\aureon_radar')
from capital_client import CapitalClient

client = CapitalClient(
    api_key=os.getenv('CAPITAL_API_KEY'),
    identifier=os.getenv('CAPITAL_IDENTIFIER'),
    password=os.getenv('CAPITAL_PASSWORD'),
    demo=os.getenv('CAPITAL_DEMO', '1') == '1'
)
print(f'Client enabled: {client.enabled}')
print(f'Client init_error: {getattr(client, "init_error", "N/A")}')
