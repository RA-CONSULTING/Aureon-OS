import sys
sys.stdout.reconfigure(encoding='utf-8')
with open(r'C:\Users\user\.kimi_openclaw\workspace\aureon_radar\aureon_phi_radar.py', 'r', encoding='utf-8') as f:
    content = f.read()

checks = [
    ('Probability matrix import', 'radar_probability_matrix'),
    ('evaluate_signal call', 'evaluate_signal'),
    ('should_trade gate', 'should_trade'),
    ('Approval logging', 'PROB] APPROVED'),
    ('Block logging', 'PROB] BLOCKED'),
    ('Flight test', 'flight_test'),
    ('Capability gate', 'capability_gate'),
    ('TTL filter', 'TTL'),
    ('MAX_NOTIONAL', 'MAX_NOTIONAL'),
]

for name, keyword in checks:
    status = 'FOUND' if keyword in content else 'NOT FOUND'
    print(f'{name:25s}: {status}')
