from pathlib import Path
import json,subprocess
script='''import datetime,json,pathlib,subprocess
root=pathlib.Path('/projects/u6vs/hnc-organism/expansion-20260912/tandem-repair-results-v1')
rows=[]
for p in sorted(root.glob('full-s*-c*.json')):
 r=json.loads(p.read_text());rows.append(dict(stage=r['stage_id'],cell=r['shard'],trials=r['trials'],gpu_uuid=r['gpu_uuid'],elapsed_seconds=r['elapsed_seconds']))
print(json.dumps(dict(observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),accounting=subprocess.check_output(['sacct','-j','6506231,6506293,6506509,6506656','-P','-n','-o','JobIDRaw,State,ExitCode,ElapsedRaw,AllocNodes'],universal_newlines=True),queue=subprocess.check_output(['squeue','-j','6506509,6506656','-h','-o','%i|%T|%M|%D|%R'],universal_newlines=True),records=rows,completed_receipt_count=len(rows))))
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=30','u6vs.aip2.isambard','python3 -'],input=script.encode(),capture_output=True,check=True,timeout=65)
result=json.loads(r.stdout);Path('outputs/tandem-repair-status-v1.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
print(json.dumps({k:v for k,v in result.items() if k!='records'},indent=2))
