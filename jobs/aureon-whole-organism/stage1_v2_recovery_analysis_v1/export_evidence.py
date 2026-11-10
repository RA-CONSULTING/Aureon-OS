import hashlib,json,pathlib,sys,tarfile
out=pathlib.Path(sys.argv[1]);run=pathlib.Path(sys.argv[2]);repair=run.parent.parent
result=json.loads((out/'analysis.json').read_text());assert result['evidence_integrity']=='PASS'
archive=out.parent/('recovery-evidence-'+out.name+'.tar.gz');assert not archive.exists()
with tarfile.open(str(archive),'w:gz',compresslevel=4) as tar:
    for p in sorted(run.rglob('*')):
        if p.is_file():tar.add(str(p),arcname='run/'+str(p.relative_to(run)),recursive=False)
    for p in sorted(out.iterdir()):
        if p.is_file():tar.add(str(p),arcname='analysis/'+p.name,recursive=False)
    for p in sorted(repair.glob('recovery-6503592.*')):
        if p.is_file():tar.add(str(p),arcname='batch/'+p.name,recursive=False)
h=hashlib.sha256()
with archive.open('rb') as f:
    for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
receipt=dict(archive=str(archive),sha256=h.hexdigest(),bytes=archive.stat().st_size,original_first_run_archive_unchanged=True)
(out.parent/('export-'+out.name+'.json')).write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
