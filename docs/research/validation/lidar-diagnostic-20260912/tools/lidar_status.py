import json,subprocess,sys
from pathlib import Path
script='''import datetime,json,pathlib,subprocess
b=pathlib.Path('/projects/u6vs/hnc-organism/expansion-20260912');p=b/'lidar-diagnostic-v1';out=b/'lidar-diagnostic-results-v1'
jobs=['6505264']
if (p/'full-submission.json').exists():jobs.append(json.loads((p/'full-submission.json').read_text())['job_id'])
r=dict(observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),accounting=subprocess.check_output(['sacct','-j',','.join(jobs),'--format=JobID,State,ExitCode,ElapsedRaw,AllocNodes','-P'],universal_newlines=True),files=len(list(out.glob('*.json'))),logs={})
for name in ['pilot-6505264.out','pilot-6505264.err']:
    q=p/name
    if q.exists():r['logs'][name]=q.read_text(errors='replace').splitlines()[-25:]
for q in out.glob('historical-*.json'):
    x=json.loads(q.read_text());r[q.name]=dict(seconds=x['elapsed_seconds'],original_differences={a:{k:v for k,v in vals.items() if not v['equal']} for a,vals in x['original_comparison'].items() if any(not v['equal'] for v in vals.values())},auroc={a:v['auroc'] for a,v in x['methods'].items()})
print(json.dumps(r))
'''
version=sys.argv[1] if len(sys.argv)>1 else '1'
if version=='2':script=script.replace('lidar-diagnostic-v1','lidar-diagnostic-v2').replace('lidar-diagnostic-results-v1','lidar-diagnostic-results-v2').replace('6505264','6505275')
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=30','u6vs.aip2.isambard','python3 -'],input=script.encode(),capture_output=True,timeout=65,check=True)
x=json.loads(r.stdout);Path('outputs/lidar-diagnostic-status-v'+version+'.json').write_text(json.dumps(x,indent=2)+'\n');print(json.dumps(x,indent=2))
