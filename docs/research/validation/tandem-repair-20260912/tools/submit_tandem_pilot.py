from pathlib import Path
import json, subprocess

script = '''import datetime,fcntl,hashlib,json,pathlib,subprocess
root=pathlib.Path('/projects/u6vs/hnc-organism/expansion-20260912/tandem-repair-v1')
subprocess.check_call(['sha256sum','-c','inputs.sha256'],cwd=str(root))
assert hashlib.sha256((root/'inputs.sha256').read_bytes()).hexdigest()=='ecea7bc161a3c0daafa198758d13b7889ba144f8fd7a17472c1b7d670674016e'
accounting=subprocess.check_output(['sacct','-j','6506231','-P','-n','-o','JobIDRaw,State,ExitCode,ElapsedRaw'],universal_newlines=True)
assert '6506231|COMPLETED|0:0|18' in accounting.splitlines()
tests=json.loads((root/'tests-6506231.json').read_text())
assert tests['passed'] and len(tests['checks'])==12 and all(c['passed'] for c in tests['checks'])
lib=list(root.glob('whiten-*.so'));assert len(lib)==1
assert hashlib.sha256(lib[0].read_bytes()).hexdigest()==tests['native_library_sha256']
subprocess.check_call(['bash','-n',str(root/'pilot.sbatch')])
lock=(root/'pilot-submit.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX)
receipt=root/'pilot-submission.json'
if receipt.exists():result=json.loads(receipt.read_text())
else:
    intent=root/'pilot-submission-intent.txt';assert not intent.exists(),'Uncertain submission; inspect scheduler'
    intent.write_text(datetime.datetime.now(datetime.timezone.utc).isoformat())
    cmd=['sbatch','--parsable',str(root/'pilot.sbatch')]
    raw=subprocess.check_output(cmd,cwd=str(root),universal_newlines=True).strip();job=raw.split(';')[0];assert job.isdigit(),raw
    result=dict(job_id=job,remote=str(root),manifest_sha256=hashlib.sha256((root/'inputs.sha256').read_bytes()).hexdigest(),command=cmd,submitted_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),preflight_job_id='6506231',preflight=tests,preflight_accounting=accounting)
    receipt.write_text(json.dumps(result,indent=2)+'\\n')
print('RESULT='+json.dumps(result))
'''
compile(script, 'remote_submit_pilot', 'exec')
Path('outputs/tandem-repair-pilot-submission-v1.remote.py').write_bytes(script.encode())
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=30','u6vs.aip2.isambard','python3 -'],input=script.encode(),capture_output=True,timeout=80)
if r.returncode:raise RuntimeError(r.stderr.decode()[-3000:]+r.stdout.decode()[-3000:])
result=json.loads(next(line for line in r.stdout.decode().splitlines() if line.startswith('RESULT=')).split('=',1)[1])
Path('outputs/tandem-repair-pilot-submission-v1.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
print(json.dumps(result,indent=2))
