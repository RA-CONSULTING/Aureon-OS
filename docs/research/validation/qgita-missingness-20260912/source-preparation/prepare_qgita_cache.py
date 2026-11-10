"""Verify the original UCR archive in memory and cache private numerical inputs."""
import argparse,datetime,fcntl,hashlib,io,json,os,pathlib,urllib.request,zipfile
import numpy as np


def sha(p):
    h=hashlib.sha256()
    with pathlib.Path(p).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


p=argparse.ArgumentParser();p.add_argument('--canonical',required=True);p.add_argument('--output',required=True)
a=p.parse_args();source=pathlib.Path(a.canonical);root=pathlib.Path(a.output);root.mkdir(parents=True,exist_ok=True)
assert sha(source)=='924411087c598c3f86632b6272ca3caf3673cff1f5ac277db5888e0f93b27ddb'
ledger=json.loads(source.read_text());meta=ledger['acquisition'];assert len(ledger['series'])==250
lock=(root/'.cache-writer.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
if (root/'cache-manifest.json').exists():
    result=json.loads((root/'cache-manifest.json').read_text());assert result['canonical_sha256']==sha(source)
    for row in result['series']:assert sha(root/row['array_file'])==row['array_sha256']
    print(json.dumps(dict(status='ALREADY_VERIFIED',series=len(result['series']))));raise SystemExit(0)
archive=io.BytesIO();h=hashlib.sha256();count=0
request=urllib.request.Request(meta['archive_url'],headers={'User-Agent':'QGITA-source-verification/2026-09-12'})
with urllib.request.urlopen(request,timeout=120) as response:
    assert response.status==200
    headers={k:response.headers.get(k) for k in ['Content-Length','ETag','Last-Modified']}
    while True:
        chunk=response.read(1024*1024)
        if not chunk:break
        archive.write(chunk);h.update(chunk);count+=len(chunk)
        if count%(16*1024*1024)==0:print(json.dumps(dict(downloaded_bytes=count)),flush=True)
assert count==meta['content_length'] and h.hexdigest().upper()==meta['archive_sha256']
archive.seek(0);rows=[]
with zipfile.ZipFile(archive) as z:
    for record in ledger['series']:
        payload=z.read(record['member_path']);assert hashlib.sha256(payload).hexdigest().upper()==record['uncompressed_sha256']
        text=payload.decode('ascii');values=np.fromstring(text,sep=' ',dtype=np.float64)
        assert len(text.split())==len(values)==record['row_count'] and np.all(np.isfinite(values))
        target=root/(record['dataset_id']+'.npy')
        if target.exists():assert np.array_equal(np.load(target,allow_pickle=False),values)
        else:
            temp=target.with_suffix('.npy.tmp')
            with temp.open('wb') as f:np.save(f,values,allow_pickle=False);f.flush();os.fsync(f.fileno())
            os.replace(temp,target)
        rows.append(dict(dataset_id=record['dataset_id'],family_key=record['family_key'],row_count=len(values),
                         array_file=target.name,array_sha256=sha(target),member_path=record['member_path'],member_sha256=record['uncompressed_sha256']))
        if len(rows)%25==0:print(json.dumps(dict(verified_series=len(rows))),flush=True)
result=dict(schema='qgita-private-ucr-cache/v1',status='PASS',verified_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            source_url=meta['archive_url'],source_archive_sha256=h.hexdigest(),source_archive_bytes=count,source_headers=headers,
            canonical_sha256=sha(source),preparation_source_sha256=sha(__file__),numpy=np.__version__,job=os.environ.get('SLURM_JOB_ID'),
            source_zip_retained_on_disk=False,private_numeric_arrays_retained=True,redistributed=False,series=rows)
target=root/'cache-manifest.json';temp=root/'cache-manifest.tmp';temp.write_text(json.dumps(result,indent=2)+'\n');os.replace(temp,target)
print(json.dumps(dict(status='PASS',series=len(rows),values=sum(r['row_count'] for r in rows),manifest_sha256=sha(target))),flush=True)
