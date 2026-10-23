import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

state_file = r'C:\Users\user\.kimi_openclaw\workspace\aureon_radar\probability_matrix_state.json'
try:
    with open(state_file, 'r') as f:
        data = json.load(f)
    print('Sources tracked:', len(data.get('source_accuracy', {})))
    for src, stats in data.get('source_accuracy', {}).items():
        total = stats.get('hits', 0) + stats.get('misses', 0)
        acc = stats.get('hits', 0) / total if total > 0 else 0
        print(f'  {src:20s}: {acc:.0%} ({stats.get("hits",0)}/{total})')
except FileNotFoundError:
    print('No state file yet')
except Exception as e:
    print(f'Error: {e}')
