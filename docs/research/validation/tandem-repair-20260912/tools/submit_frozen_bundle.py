"""Upload an immutable flat analysis bundle and submit once with a durable intent."""
from pathlib import Path
import argparse, hashlib, io, json, subprocess, tarfile


def submit(directory, remote, batch, receipt_path, extra=None):
    directory = Path(directory); receipt_path = Path(receipt_path)
    files = sorted(p for p in directory.iterdir() if p.is_file() and p.name != 'inputs.sha256')
    for p in directory.glob('*.py'): compile(p.read_text(), p.name, 'exec')
    manifest = ''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in files)
    target = directory/'inputs.sha256'
    if target.exists(): assert target.read_bytes() == manifest.encode()
    else: target.write_bytes(manifest.encode())
    archive = receipt_path.with_suffix('.tar.gz')
    if not archive.exists():
        with tarfile.open(archive,'w:gz') as tar:
            for p in files+[target]:
                data=p.read_bytes();info=tarfile.TarInfo(p.name);info.size=len(data);info.mode=0o660;tar.addfile(info,io.BytesIO(data))
    digest=hashlib.sha256(archive.read_bytes()).hexdigest();uploaded=remote+'.tar.gz'
    subprocess.run(['scp','-o','BatchMode=yes','-o','ConnectTimeout=30',str(archive),'u6vs.aip2.isambard:'+uploaded],check=True,timeout=90)
    data=dict(remote=remote,archive=uploaded,digest=digest,batch=batch,extra=extra or [])
    script='''import datetime,fcntl,hashlib,json,pathlib,subprocess,tarfile
data=DATA;root=pathlib.Path(data['remote']);root.mkdir(parents=True,exist_ok=True)
archive=pathlib.Path(data['archive']);assert hashlib.sha256(archive.read_bytes()).hexdigest()==data['digest']
with tarfile.open(str(archive)) as tar:
    for m in tar.getmembers():
        assert m.isfile() and '/' not in m.name and '..' not in m.name
        content=tar.extractfile(m).read();p=root/m.name
        if p.exists():assert p.read_bytes()==content,'Existing input differs'
        else:p.write_bytes(content)
subprocess.check_call(['sha256sum','-c','inputs.sha256'],cwd=str(root))
subprocess.check_call(['bash','-n',str(root/data['batch'])])
lock=(root/'submit.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX)
receipt=root/'submission.json'
if receipt.exists():result=json.loads(receipt.read_text())
else:
    intent=root/'submission-intent.txt';assert not intent.exists(),'Uncertain submission; inspect scheduler'
    intent.write_text(datetime.datetime.now(datetime.timezone.utc).isoformat())
    cmd=['sbatch','--parsable']+data['extra']+[str(root/data['batch'])]
    raw=subprocess.check_output(cmd,cwd=str(root),universal_newlines=True).strip();job=raw.split(';')[0];assert job.isdigit(),raw
    result=dict(job_id=job,remote=str(root),archive_sha256=data['digest'],manifest_sha256=hashlib.sha256((root/'inputs.sha256').read_bytes()).hexdigest(),command=cmd,submitted_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    receipt.write_text(json.dumps(result,indent=2)+'\\n')
print('SUBMITTED='+json.dumps(result))
'''.replace('DATA',repr(data))
    compile(script,'submit','exec')
    receipt_path.with_suffix('.remote.py').write_text(script)
    r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=30','u6vs.aip2.isambard','python3 -'],input=script.encode(),capture_output=True,timeout=80)
    if r.returncode:raise RuntimeError(r.stderr.decode()[-2500:]+r.stdout.decode()[-2500:])
    result=json.loads(next(l for l in r.stdout.decode().splitlines() if l.startswith('SUBMITTED=')).split('=',1)[1])
    receipt_path.write_text(json.dumps(result,indent=2)+'\n');return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',required=True);p.add_argument('--remote',required=True)
    p.add_argument('--batch',required=True);p.add_argument('--receipt',required=True)
    a=p.parse_args();print(json.dumps(submit(a.directory,a.remote,a.batch,a.receipt),indent=2))
