from pathlib import Path
import json,subprocess
ROOT=Path(__file__).resolve().parent.parent
script='''import csv,datetime,fcntl,hashlib,json,math,pathlib,subprocess
b=pathlib.Path('/projects/u6vs/hnc-organism/expansion-20260912');pack=b/'qgita-missingness-v1';campaign=b/'qgita-missingness-campaign-v1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):
    wrapped=json.loads(p.read_text());payload=wrapped['payload'];encoded=json.dumps(payload,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    assert hashlib.sha256(encoded).hexdigest()==wrapped['payload_sha256'];return payload
accounting=subprocess.check_output(['sacct','-j','6504865,6504958','--format=JobID,State,ExitCode,ElapsedRaw,AllocNodes','-P'],universal_newlines=True)
jobs={r['JobID']:r for r in csv.DictReader(accounting.splitlines(),delimiter='|')}
for job in ['6504865','6504958']:assert jobs[job]['State']=='COMPLETED' and jobs[job]['ExitCode']=='0:0'
tests=json.loads((pack/'tests-6504958.json').read_text());assert tests['status']=='PASS' and tests['tests_run']==8 and tests['numpy']=='2.3.5'
assert tests['source_sha256']==sha(pack/'qgita_missing.py') and tests['test_sha256']==sha(pack/'test_missing.py')
assert sha(pack/'inputs.sha256')=='18df898020d3a966581c80471aecfb82a80eb8e28d8d21e5883c7ea935838f22'
subprocess.check_call(['sha256sum','-c','inputs.sha256'],cwd=str(pack))
pilot=load(campaign/'pilot-6504958.json');assert pilot['status']=='COMPLETE' and pilot['series']==46 and pilot['new_replicates']==2
records=json.loads((pack/'canonical.json').read_text())['series'];lengths={r['dataset_id']:r['row_count'] for r in records}
representatives={}
for record in records:
    f=record['family_key'];representatives[f]=min(representatives.get(f,record['dataset_id']),record['dataset_id'])
assert {r['dataset_id'] for r in pilot['per_series']}==set(representatives.values())
verified=0
for r in pilot['per_series']:
    d=campaign/('dataset-'+r['dataset_id']);assert sha(d/'clean.json')==r['clean_sha256']
    for phase,n in [('historical',5),('new_masks',2)]:
        for rep in range(n):
            payload=load(d/(phase+'-r'+str(rep).zfill(3)+'.json'))
            assert payload['identity']['input_manifest_sha256']==sha(pack/'inputs.sha256') and payload['identity']['dataset_id']==r['dataset_id']
            assert payload['phase']==phase and payload['replicate']==rep and len(payload['scenarios'])==(3 if phase=='historical' else 6)
            verified+=len(payload['scenarios'])
assert verified==1242
rate=sum(r['elapsed_seconds'] for r in pilot['per_series'])/sum(lengths[r['dataset_id']]*27 for r in pilot['per_series'])
remaining_work=sum(lengths.values())*207-sum(lengths[r['dataset_id']]*27 for r in pilot['per_series'])
projected=max(rate*remaining_work/32,max(r['elapsed_seconds']/lengths[r['dataset_id']]/27 for r in pilot['per_series'])*max(lengths.values())*207)
wall=math.ceil((1.5*projected+60)/300)*300;assert 0<wall<=1800
decision=dict(nodes=1,workers=32,projected_seconds=projected,walltime_seconds=wall,ceiling_node_hours=wall/3600,pilot_verified_mask_sets=verified,
              pilot_summary_sha256=sha(campaign/'pilot-6504958.json'),pilot_allocated_node_hours=int(jobs['6504958']['ElapsedRaw'])/3600,
              rule='Observed row-weighted pilot CPU effort divided across 32 workers, bounded by a worst-rate longest-series task; 50 percent margin plus one minute; five-minute rounding')
lock=(pack/'full-submit.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX)
receipt=pack/'full-submission.json'
if receipt.exists():result=json.loads(receipt.read_text())
else:
    intent=pack/'full-submit-intent.txt';assert not intent.exists(),'Uncertain submission; inspect scheduler'
    (pack/'full-resource-decision.json').write_text(json.dumps(decision,indent=2)+'\\n')
    intent.write_text(datetime.datetime.now(datetime.timezone.utc).isoformat())
    timearg='%02d:%02d:%02d'%(wall//3600,(wall%3600)//60,wall%60)
    cmd=['sbatch','--parsable','--time='+timearg,str(pack/'full.sbatch')]
    raw=subprocess.check_output(cmd,universal_newlines=True).strip();job=raw.split(';')[0];assert job.isdigit(),raw
    result=dict(job_id=job,submitted_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),command=cmd,resource_decision=decision,input_manifest_sha256=sha(pack/'inputs.sha256'),candidate_control_outcomes=103500)
    receipt.write_text(json.dumps(result,indent=2)+'\\n')
print('RESULT='+json.dumps(dict(submission=result,pilot=pilot,tests=tests,preparation_accounting=jobs)))
'''
compile(script,'full','exec');(ROOT/'work/qgita_full_remote.py').write_text(script)
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=30','u6vs.aip2.isambard','python3 -'],input=script.encode(),capture_output=True,timeout=90)
if r.returncode:raise RuntimeError(r.stderr.decode()[-2500:]+r.stdout.decode()[-2500:])
result=json.loads(next(line for line in r.stdout.decode().splitlines() if line.startswith('RESULT=')).split('=',1)[1])
(ROOT/'outputs/qgita-missingness-full-submission-v1.json').write_text(json.dumps(result['submission'],indent=2)+'\n')
(ROOT/'outputs/qgita-missingness-pilot-verification-v1.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result['submission'],indent=2))
