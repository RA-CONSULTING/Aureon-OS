from pathlib import Path
import hashlib, json, subprocess, tarfile

script='''import datetime,hashlib,json,pathlib,subprocess,tarfile
base=pathlib.Path('/projects/u6vs/hnc-organism/expansion-20260912');src=base/'tandem-repair-v1';root=base/'tandem-repair-results-v1'
accounting=subprocess.check_output(['sacct','-j','6506231,6506293','-P','-n','-o','JobIDRaw,State,ExitCode,ElapsedRaw,AllocNodes'],universal_newlines=True)
assert any(l.startswith('6506293|COMPLETED|0:0|') for l in accounting.splitlines()),accounting
subprocess.check_call(['sha256sum','-c','inputs.sha256'],cwd=str(src))
files=[];receipts=[];gpu={};elapsed={};size=0
manifest=hashlib.sha256((src/'inputs.sha256').read_bytes()).hexdigest()
assert manifest=='ecea7bc161a3c0daafa198758d13b7889ba144f8fd7a17472c1b7d670674016e'
for stage in range(7):
 for shard in [0,15,16,31]:
  p=root/('pilot-s%02d-c%02d.json'%(stage,shard));a=p.with_suffix('.npz');r=json.loads(p.read_text())
  assert (r['stage_id'],r['shard'],r['trials'],r['pilot'],r['slurm_job_id'])==(stage,shard,512,True,'6506293')
  assert r['input_manifest_sha256']==manifest and r['array_sha256']==hashlib.sha256(a.read_bytes()).hexdigest()
  if stage>=3:assert r['max_selected_weight_after']==0
  gpu.setdefault(shard,set()).add(r['gpu_uuid']);elapsed[shard]=elapsed.get(shard,0)+r['elapsed_seconds']
  receipts.append(r);files.extend([p,a]);size+=a.stat().st_size
assert all(len(v)==1 for v in gpu.values()) and len(set(next(iter(v)) for v in gpu.values()))==4
summary=dict(observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),accounting=accounting,manifest_sha256=manifest,receipts=receipts,rank_elapsed_seconds=elapsed,projected_full_seconds=max(elapsed.values())*(10368/512),projection_with_margin_seconds=max(elapsed.values())*(10368/512)*1.5+600,pilot_array_bytes=size,projected_full_array_bytes=size*(32/4)*(10368/512),filesystem=subprocess.check_output(['df','-B1',str(root)],universal_newlines=True))
assert summary['projection_with_margin_seconds']<=10800
archive=base/'tandem-repair-pilot-6506293.tar.gz'
with tarfile.open(str(archive),'w:gz') as tar:
 for p in files:tar.add(str(p),arcname=p.name)
 for p in [src/'tests-6506231.json',src/'whiten-29331187f0a045df.build.json']:tar.add(str(p),arcname=p.name)
summary['archive_sha256']=hashlib.sha256(archive.read_bytes()).hexdigest();summary['archive_bytes']=archive.stat().st_size
print('RESULT='+json.dumps(summary))
'''
compile(script,'remote_pilot_collect','exec')
Path('outputs/tandem-repair-pilot-6506293.remote.py').write_bytes(script.encode())
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=30','u6vs.aip2.isambard','python3 -'],input=script.encode(),capture_output=True,timeout=100)
if r.returncode:raise RuntimeError(r.stderr.decode()[-3000:]+r.stdout.decode()[-3000:])
result=json.loads(next(l for l in r.stdout.decode().splitlines() if l.startswith('RESULT=')).split('=',1)[1])
out=Path('outputs/tandem-repair-pilot-6506293');out.mkdir(exist_ok=True)
archive=out/'pilot.tar.gz'
subprocess.run(['scp','-o','BatchMode=yes','-o','ConnectTimeout=30','u6vs.aip2.isambard:/projects/u6vs/hnc-organism/expansion-20260912/tandem-repair-pilot-6506293.tar.gz',str(archive)],check=True,timeout=120)
assert hashlib.sha256(archive.read_bytes()).hexdigest()==result['archive_sha256']
with tarfile.open(archive) as tar:
 for m in tar.getmembers():
  assert m.isfile() and '/' not in m.name and '..' not in m.name
  (out/m.name).write_bytes(tar.extractfile(m).read())
(out/'remote-audit.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
print(json.dumps({k:v for k,v in result.items() if k!='receipts'},indent=2))
