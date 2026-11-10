from pathlib import Path
import hashlib, json, subprocess
ROOT=Path(__file__).resolve().parent.parent
H='/projects/u6vs/hnc-organism/expansion-20260912/hnc-histories-v1'
A='/projects/u6vs/hnc-organism/expansion-20260912/hnc-history-audit-v4'
C='/projects/u6vs/hnc-organism/expansion-20260912/history-campaign-v1'
source_hash=hashlib.sha256((ROOT/'work/hnc-history-audit-v4/audit_hnc_histories.py').read_bytes()).hexdigest()
data=dict(h=H,a=A,c=C,audit_source_sha256=source_hash)
script='''import csv,datetime,fcntl,hashlib,json,math,pathlib,shutil,subprocess
data=DATA;h=pathlib.Path(data['h']);a=pathlib.Path(data['a']);c=pathlib.Path(data['c'])
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
raw=subprocess.check_output(['sacct','-j','6504281,6504297,6504609','--format=JobID,State,ExitCode,ElapsedRaw,AllocNodes','-P'],universal_newlines=True)
jobs={r['JobID']:r for r in csv.DictReader(raw.splitlines(),delimiter='|')}
for job in ['6504281','6504297','6504609']:assert jobs[job]['State']=='COMPLETED' and jobs[job]['ExitCode']=='0:0'
auditpath=a/'audit-6504609.json';audit=json.loads(auditpath.read_text());decision=audit['resource_decision']
assert audit['status']=='PASS' and audit['job']=='6504297' and audit['stop']==65536
assert audit['audit_source_sha256']==data['audit_source_sha256'] and audit['ranks_verified']==audit['distinct_gpus']==128
assert audit['input_manifest_sha256']==sha(h/'inputs.sha256')=='54dc5fc6e61448a3d9b71681f5c60ccae1e23a70f0d99b9f5a25e5afb4993dc9'
subprocess.check_call(['sha256sum','-c','inputs.sha256'],cwd=str(h))
for r in audit['ranks']:assert sha(c/r['receipt'])==r['receipt_sha256']
assert decision['status']=='READY_TO_STAGE' and decision['nodes']==32 and decision['gpus']==128
wall=decision['walltime_seconds'];assert wall==math.ceil((1.25*decision['projected_remaining_seconds']+900)/1800)*1800 and 0<wall<=28800
assert shutil.disk_usage(c).free>decision['projected_checkpoint_storage_bytes']+100*1024**3
lock=(h/'production-submit.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX)
receipt=h/'production-submission.json'
if receipt.exists():result=json.loads(receipt.read_text())
else:
    intent=h/'production-submit-intent.txt';assert not intent.exists(),'Uncertain production submission; inspect scheduler'
    frozen=dict(decision=decision,pilot_audit_sha256=sha(auditpath),pilot_audit_job='6504609',pilot_job='6504297',input_manifest_sha256=sha(h/'inputs.sha256'),decision_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    (h/'production-resource-decision.json').write_text(json.dumps(frozen,indent=2)+'\\n')
    intent.write_text(datetime.datetime.now(datetime.timezone.utc).isoformat())
    walltext='%02d:%02d:%02d'%(wall//3600,(wall%3600)//60,wall%60)
    cmd=['sbatch','--parsable','--time='+walltext,str(h/'production.sbatch')]
    raw=subprocess.check_output(cmd,cwd=str(h),universal_newlines=True).strip();job=raw.split(';')[0];assert job.isdigit(),raw
    result=dict(job_id=job,submitted_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),command=cmd,resource_decision=frozen,nodes=32,gpus=128,trajectory_count=25214464,horizon=33554432,ceiling_node_hours=decision['ceiling_node_hours'])
    receipt.write_text(json.dumps(result,indent=2)+'\\n')
print('RESULT='+json.dumps(dict(production=result,pilot_audit=audit,accounting=jobs,audit_sha256=sha(auditpath))))
'''.replace('DATA',repr(data))
compile(script,'production','exec');(ROOT/'work/hnc_history_production_remote.py').write_text(script)
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=30','u6vs.aip2.isambard','python3 -'],input=script.encode(),capture_output=True,timeout=90)
if r.returncode:raise RuntimeError(r.stderr.decode()[-2500:]+r.stdout.decode()[-2500:])
result=json.loads(next(line for line in r.stdout.decode().splitlines() if line.startswith('RESULT=')).split('=',1)[1])
(ROOT/'outputs/hnc-histories-production-submission-v1.json').write_text(json.dumps(result['production'],indent=2)+'\n')
(ROOT/'outputs/hnc-histories-pilot-audit-6504609.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result['production'],indent=2))
print(json.dumps(dict(rounding_max_ulp=max(x['maximum_ulp_difference'] for x in result['pilot_audit']['cpu_gpu_rounding_diagnostics']),cpu_different_values=sum(x['cpu_rolling_unequal_values'] for x in result['pilot_audit']['cpu_gpu_rounding_diagnostics']))))
