import sys, json
sys.stdout.reconfigure(encoding='utf-8')

with open(r'C:\Users\user\.kimi_openclaw\workspace\aureon_radar\honey_ladder_state.json', 'r') as f:
    data = json.load(f)

print('Honey pot active:', data.get('honey_pot', {}).get('active', False))
print('Shadows total:', len(data.get('shadow_runs', [])))
print('Source records:')
for src, rec in data.get('source_records', {}).items():
    total = rec.get('total_trades', 0)
    hits = rec.get('hits', 0)
    wr = hits/total*100 if total > 0 else 0
    rung = rec.get('ladder_rung', 1)
    print(f'  {src:20s}: {hits}/{total} ({wr:.0f}%) rung={rung}')
