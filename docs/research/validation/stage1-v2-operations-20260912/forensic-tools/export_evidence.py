import hashlib,json,pathlib,sys,tarfile
out=pathlib.Path(sys.argv[1]);campaign=pathlib.Path(sys.argv[2])
analysis=json.load((out/'analysis.json').open());assert analysis['evidence_integrity']=='PASS'
archive=out.parent/('original-evidence-'+out.name+'.tar.gz')
with tarfile.open(str(archive),'w:gz',compresslevel=4) as tar:
    for run in sorted((campaign/'runs').glob('evaluation-*')):
        for p in sorted(run.rglob('*')):
            if p.is_file():tar.add(str(p),arcname='runs/'+run.name+'/'+str(p.relative_to(run)),recursive=False)
    for p in sorted(out.iterdir()):
        if p.is_file():tar.add(str(p),arcname='analysis/'+p.name,recursive=False)
    for p in sorted(campaign.glob('evaluation-6502171_*.out'))+sorted(campaign.glob('evaluation-6502171_*.err')):
        tar.add(str(p),arcname='batch/'+p.name,recursive=False)
    for p in sorted(campaign.glob('audit-6502172.*')):
        tar.add(str(p),arcname='original-audit/'+p.name,recursive=False)
h=hashlib.sha256()
with archive.open('rb') as f:
    for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
receipt=dict(archive=str(archive),bytes=archive.stat().st_size,sha256=h.hexdigest(),
             source_input_manifest_sha256=analysis['input_manifest_sha256'],model_weights_exported=False)
(out.parent/('export-'+out.name+'.json')).write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
