import argparse
import collections
import hashlib
import json
import pathlib
import numpy as np


def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as stream:
        for chunk in iter(lambda:stream.read(4*1024*1024),b''):h.update(chunk)
    return h.hexdigest()


p=argparse.ArgumentParser();p.add_argument('--base',required=True);p.add_argument('--stop',type=int,required=True)
p.add_argument('--job',required=True);p.add_argument('--output',required=True);a=p.parse_args()
base=pathlib.Path(a.base);source=base/'hnc-fine-v1';root=base/'fine-campaign-v1'
config=json.loads((source/'config.json').read_text());errors=[];rows=[];ownership={};hosts=collections.Counter()
expected={'config_sha256':sha(source/'config.json'),'harness_sha256':sha(source/'hnc_fine.py'),'runner_sha256':sha(source/'run_fine.py')}
def check(ok,label):
    if not ok:errors.append(label)
check(sha(root/'config.json')==expected['config_sha256'],'root configuration')
for rank,task in enumerate(config['tasks']):
    try:
        chain=[]
        for file in (root/f'rank-{rank:03d}').glob('attempt-*/receipt.json'):
            r=json.loads(file.read_text())
            for key,value in dict(expected,rank=rank,task=task,horizon=config['horizon'],reference_beta=1.0).items():
                check(r.get(key)==value,f'{rank}/{file.parent.name}/{key}')
            for name,key in [('grid.npz','grid_sha256'),('checkpoint.pt','checkpoint_sha256')]:
                check(sha(file.parent/name)==r[key],f'{rank}/{file.parent.name}/{name} hash')
            chain.append((r,file))
        chain.sort(key=lambda x:x[0]['stop']);stop=0;previous=None;escaped_before=None
        for r,file in chain:
            check(r['start']==stop and r['stop']>stop and r['stop']<=r['target_stop'],f'{rank}/step interval')
            check(r['previous_receipt_sha256']==previous,f'{rank}/receipt chain')
            check(r['status'] in ['COMPLETE','COMPLETE_SEGMENT','INTERRUPTED'],f'{rank}/status')
            with np.load(file.parent/'grid.npz',allow_pickle=False) as z:grid={k:z[k] for k in z.files}
            for key,axis in [('alpha',config['alphas']),('beta',config['betas'])]:
                check(np.array_equal(grid[key],axis),f'{rank}/{key} axis')
            shape=(len(config['alphas']),len(config['betas']))
            for key in ['escaped','max_abs','first_escape_step','lyapunov_per_step','lyapunov_blocks']:
                check(grid[key].shape==shape and np.isfinite(grid[key]).all(),f'{rank}/{key} validity')
            check(np.array_equal(grid['escaped'],grid['first_escape_step']>0),f'{rank}/escape flags')
            if escaped_before is not None:check(not np.any(escaped_before&(~grid['escaped'])),f'{rank}/escape reversal')
            escaped_before=grid['escaped'];stop=r['stop'];previous=sha(file)
        check(bool(chain),f'{rank}/missing receipts')
        if not chain:continue
        check(stop==a.stop,f'{rank}/expected stop {a.stop}, found {stop}')
        check(r['job']==a.job,f'{rank}/expected job')
        uuid=r.get('gpu_uuid')
        check(isinstance(uuid,str) and len(uuid)>=32,f'{rank}/physical GPU UUID')
        check(uuid not in ownership,f'{rank}/duplicate physical GPU UUID');ownership[uuid]=rank
        hosts[r['host']]+=1
        stable=(~grid['escaped'])&(grid['lyapunov_blocks']>0)&(grid['lyapunov_per_step']<=1e-4)
        i=np.flatnonzero(grid['beta']==1.)
        rows.append(dict(rank=rank,parameters=task,stop=stop,receipt_count=len(chain),
                         elapsed_seconds=sum(x[0]['elapsed_seconds'] for x in chain),
                         peak_allocated_bytes=max(x[0]['peak_allocated_bytes'] for x in chain),
                         escaped=int(grid['escaped'].sum()),stable=int(stable.sum()),
                         beta1_stable=int(stable[:,i].sum()),beta1_tested=len(config['alphas']),
                         bounded_without_valid_lyapunov=int(((~grid['escaped'])&(grid['lyapunov_blocks']==0)).sum()),
                         gpu_uuid=uuid,host=r['host']))
    except (OSError,ValueError,KeyError,IndexError,TypeError) as exc:errors.append(f'{rank}: {type(exc).__name__}: {exc}')
check(len(ownership)==128 and len(hosts)==32 and all(n==4 for n in hosts.values()),'128 distinct GPUs on 32 hosts')
result=dict(schema='hnc-fine-audit/v1',status='PASS' if not errors else 'FAIL',errors=errors,
            expected_stop=a.stop,job=a.job,cells=len(rows),config_sha256=expected['config_sha256'],
            source_hashes=expected,auditor_sha256=sha(pathlib.Path(__file__)),
            summary={key:sum(r[key] for r in rows) for key in ['escaped','stable','beta1_stable','beta1_tested','receipt_count','bounded_without_valid_lyapunov']},
            peak_allocated_bytes_max=max((r['peak_allocated_bytes'] for r in rows),default=None),
            cumulative_compute_seconds_max=max((r['elapsed_seconds'] for r in rows),default=None),rows=rows,
            scope='Artifact/identity/chain/grid and physical-device audit; no independent checkpoint semantic recomputation or scientific proof.')
with pathlib.Path(a.output).open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))
if errors:raise SystemExit(1)
