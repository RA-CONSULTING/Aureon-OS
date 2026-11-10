from pathlib import Path
import json,subprocess
script='''import datetime,fcntl,hashlib,json,pathlib,subprocess
p=pathlib.Path('/projects/u6vs/hnc-organism/expansion-20260912/lidar-diagnostic-v2');out=p.parent/'lidar-diagnostic-results-v2'
assert hashlib.sha256((p/'inputs.sha256').read_bytes()).hexdigest()=='255d45a1222770eac0916adbab1233b7480a0b719f8cbca42a30b8681b4cbb13'
subprocess.check_call(['sha256sum','-c','inputs.sha256'],cwd=str(p))
accounting=subprocess.check_output(['sacct','-X','-j','6505275','--format=JobID,State,ExitCode,ElapsedRaw,AllocNodes','-P'],universal_newlines=True)
assert '6505275|COMPLETED|0:0|' in accounting
tests=json.loads((p/'tests-6505275.json').read_text());assert tests['passed'] and len(tests['checks'])==9
historical=[]
for shard in [0,32]:
    q=out/('historical-%03d.json'%shard);j=json.loads(q.read_text())
    assert hashlib.sha256(q.with_suffix('.npz').read_bytes()).hexdigest()==j['arrays_sha256']
    assert j['input_manifest_sha256']=='255d45a1222770eac0916adbab1233b7480a0b719f8cbca42a30b8681b4cbb13'
    assert all(v['equal'] for vals in j['original_comparison'].values() for v in vals.values())
    historical.append(j)
projection=max(j['elapsed_seconds'] for j in historical)*2*32
margin=projection*1.5+60
assert margin<600
decision=dict(pilot_job='6505275',accounting=accounting,tests_sha256=hashlib.sha256((p/'tests-6505275.json').read_bytes()).hexdigest(),projection_seconds=projection,with_margin_seconds=margin,ceiling_seconds=600,nodes=1,gpus=4,new_test_examples=1280000,new_calibration_examples=384000)
lock=(p/'full-submit.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX)
receipt=p/'full-submission.json'
if receipt.exists():r=json.loads(receipt.read_text())
else:
    intent=p/'full-submission-intent.txt';assert not intent.exists(),'Uncertain prior submission; inspect first'
    intent.write_text(datetime.datetime.now(datetime.timezone.utc).isoformat())
    job=subprocess.check_output(['sbatch','--parsable',str(p/'full.sbatch')],universal_newlines=True).strip().split(';')[0];assert job.isdigit()
    r=dict(job_id=job,submitted_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),resource_decision=decision)
    receipt.write_text(json.dumps(r,indent=2)+'\\n')
print('RESULT='+json.dumps(r))
'''
compile(script,'submit_full','exec');Path('outputs/lidar-diagnostic-full-submission-v2.remote.py').write_text(script)
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=30','u6vs.aip2.isambard','python3 -'],input=script.encode(),capture_output=True,timeout=70,check=True)
x=json.loads(next(l.split('=',1)[1] for l in r.stdout.decode().splitlines() if l.startswith('RESULT=')))
Path('outputs/lidar-diagnostic-full-submission-v2.json').write_text(json.dumps(x,indent=2)+'\n');print(json.dumps(x,indent=2))
