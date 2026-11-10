import collections
import datetime
import hashlib
import json
import pathlib
import numpy as np

BASE = pathlib.Path('/projects/u6vs/hnc-organism/expansion-20260912')
ROOT = BASE/'fine-campaign-v1'
AUDIT = BASE/'fine-audit-v1/audit-6498144.json'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

audit = json.loads(AUDIT.read_text())
assert audit['status'] == 'PASS' and audit['expected_stop'] == 16777216
assert sha(AUDIT) == 'e5f7504bebc298c51a41f7d9907c825d74af65863b2af410f0cf4b77b943cda6'
assert sha(ROOT/'config.json') == audit['config_sha256']
config = json.loads((ROOT/'config.json').read_text())
rows = []
for rank, task in enumerate(config['tasks']):
    receipts = sorted([(json.loads(p.read_text()), p) for p in (ROOT/('rank-%03d'%rank)).glob('attempt-*/receipt.json')], key=lambda r:r[0]['stop'])
    previous = None
    for receipt, path in receipts:
        assert receipt['rank'] == rank and receipt['task'] == task
        assert receipt['previous_receipt_sha256'] == previous
        previous = sha(path)
        grid_path = path.parent/'grid.npz'
        assert sha(grid_path) == receipt['grid_sha256']
        with np.load(grid_path, allow_pickle=False) as z:
            g = {k:z[k] for k in z.files}
        stable = (~g['escaped']) & (g['lyapunov_blocks']>0) & (g['lyapunov_per_step']<=1e-4)
        beta = g['beta']; fine = (beta>=.9995)&(beta<=1.0015)
        b = beta[fine]; f = stable.mean(axis=0)[fine]
        crosses = []
        brackets = []
        for i in range(len(b)-1):
            if f[i] >= .5 > f[i+1]:
                crosses.append(float(b[i]+(.5-f[i])*(b[i+1]-b[i])/(f[i+1]-f[i])))
                brackets.append([float(b[i]),float(b[i+1])])
        controls = {str(v):int(stable[:,np.flatnonzero(beta==v)[0]].sum()) for v in [1.,1.1]}
        rows.append(dict(rank=rank,parameters=task,stop=receipt['stop'],grid_sha256=receipt['grid_sha256'],receipt_sha256=sha(path),
            escaped=int(g['escaped'].sum()),stable=int(stable.sum()),
            bounded_without_valid_lyapunov=int(((~g['escaped'])&(g['lyapunov_blocks']==0)).sum()),
            bounded_positive_lyapunov=int(((~g['escaped'])&(g['lyapunov_blocks']>0)&(g['lyapunov_per_step']>1e-4)).sum()),
            stable_controls=controls,control_tested=len(config['alphas']),
            first_downward_crossing=crosses[0] if crosses else None,all_downward_crossings=crosses,crossing_brackets=brackets,
            starts_below_half=bool(f[0]<.5),upward_steps=int((np.diff(f)>0).sum()),stable_fraction_by_beta=f.tolist()))
summary=[]; previous_escaped=None
for step in sorted(set(r['stop'] for r in rows)):
    rs=[r for r in rows if r['stop']==step];assert len(rs)==128
    boundaries=[r['first_downward_crossing'] for r in rs if r['first_downward_crossing'] is not None]
    escaped=sum(r['escaped'] for r in rs)
    summary.append(dict(stop=step,cells=len(rs),escaped=escaped,additional_escapes=None if previous_escaped is None else escaped-previous_escaped,
        stable=sum(r['stable'] for r in rs),beta1_stable=sum(r['stable_controls']['1.0'] for r in rs),beta1_tested=15488,
        beta1p1_stable=sum(r['stable_controls']['1.1'] for r in rs),
        bounded_without_valid_lyapunov=sum(r['bounded_without_valid_lyapunov'] for r in rs),
        bounded_positive_lyapunov=sum(r['bounded_positive_lyapunov'] for r in rs),
        cells_with_crossing=len(boundaries),first_crossing_min_median_max=[float(v) for v in np.quantile(boundaries,[0,.5,1])] if boundaries else None,
        starts_below_half=sum(r['starts_below_half'] for r in rs),nonmonotonic_cells=sum(r['upward_steps']>0 for r in rs),
        multiple_crossing_cells=sum(len(r['all_downward_crossings'])>1 for r in rs)))
    assert previous_escaped is None or escaped>=previous_escaped
    previous_escaped=escaped
for k in ['escaped','stable','beta1_stable','beta1_tested','bounded_without_valid_lyapunov']:
    assert summary[-1][k] == audit['summary'][k], k
result=dict(schema='hnc-fine-analysis/v1',status='PASS',generated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    auditor_sha256=sha(pathlib.Path(__file__)),source_audit_sha256=sha(AUDIT),config_sha256=audit['config_sha256'],
    summary=summary,fine_betas=b.tolist(),rows=rows,
    interpretation='Finite-time simulation classifications. Crossings interpolate adjacent fine-grid points only; all crossings and nonmonotonicity are retained. Cells with no crossing are not assigned an invented threshold. No infinite-time or physical claim follows.',
    verification='Rehashed all result grids and receipts, checked chains and matched final audit totals. Checkpoint tensors were hashed by audit 6498144; this analysis does not independently recompute their semantics.')
output=pathlib.Path(__file__).parent/'analysis.json'
with output.open('x') as stream:json.dump(result,stream,separators=(',',':'))
print(json.dumps({k:v for k,v in result.items() if k not in ['rows','fine_betas']},indent=2))
