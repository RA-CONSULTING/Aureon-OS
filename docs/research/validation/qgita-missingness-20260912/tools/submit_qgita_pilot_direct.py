from pathlib import Path
import json,subprocess
ROOT=Path(__file__).resolve().parent.parent
script=(ROOT/'outputs/qgita-missingness-pilot-submission-v1.remote.py').read_text()
script=script.replace("'extra': ['--dependency=afterok:6504865']","'extra': []")
script=script.replace("root/'submission.json'","root/'direct-pilot-submission.json'").replace("root/'submission-intent.txt'","root/'direct-pilot-intent.txt'")
gate='''import csv
accounting=subprocess.check_output(['sacct','-j','6504865','--format=JobID,State,ExitCode','-P'],universal_newlines=True)
jobs={r['JobID']:r for r in csv.DictReader(accounting.splitlines(),delimiter='|')}
assert jobs['6504865']['State']=='COMPLETED' and jobs['6504865']['ExitCode']=='0:0'
cache=pathlib.Path('/projects/u6vs/hnc-organism/expansion-20260912/qgita-ucr-cache-v1/cache-manifest.json')
assert hashlib.sha256(cache.read_bytes()).hexdigest()=='882ecb8a999f1f6648994f5f4d02c24666447fcaaf2b1f4a77fba9b2fabed252'
assert json.loads(cache.read_text())['status']=='PASS'
queue=subprocess.check_output(['squeue','-u','garyleckey.u6vs','-h','-o','%j|%i'],universal_newlines=True)
assert not any(line.startswith('qgita-missingness-pilot|') for line in queue.splitlines()),'A pilot is already live'
(root/'dependency-rejection.json').write_text(json.dumps(dict(action='sbatch --dependency=afterok:6504865 pilot.sbatch',exit_code=1,error='Batch job submission failed: Job dependency problem',resolution='Verified terminal preparation accounting and exact completed cache manifest before direct submission',preparation_accounting=jobs),indent=2)+'\\n')
'''
script=script.replace("lock=(root/'submit.lock')",gate+"lock=(root/'submit.lock')")
compile(script,'direct','exec');(ROOT/'work/qgita_pilot_direct_remote.py').write_text(script)
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=30','u6vs.aip2.isambard','python3 -'],input=script.encode(),capture_output=True,timeout=80)
if r.returncode:raise RuntimeError(r.stderr.decode()[-2500:]+r.stdout.decode()[-2500:])
result=json.loads(next(line for line in r.stdout.decode().splitlines() if line.startswith('SUBMITTED=')).split('=',1)[1])
(ROOT/'outputs/qgita-missingness-pilot-submission-v1.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
