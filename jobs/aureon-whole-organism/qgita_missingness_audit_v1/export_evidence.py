import hashlib,json,pathlib,sys,tarfile
root=pathlib.Path(sys.argv[1]);campaign=pathlib.Path(sys.argv[2]);job=sys.argv[3];analysis=root/('analysis-'+job+'.json')
result=json.loads(analysis.read_text());assert result['status']=='PASS'
files=[p for p in sorted(campaign.rglob('*.json')) if p.is_file()]
archive=root/('evidence-'+job+'.tar.gz');assert not archive.exists()
with tarfile.open(str(archive),'w:gz',compresslevel=4) as tar:
    for p in files:tar.add(str(p),arcname='campaign/'+str(p.relative_to(campaign)),recursive=False)
    for name in ['analysis-'+job+'.json','accounting-'+job+'.psv','tests-'+job+'.json']:
        tar.add(str(root/name),arcname='audit/'+name,recursive=False)
    cache=campaign.parent/'qgita-ucr-cache-v1/cache-manifest.json';tar.add(str(cache),arcname='source/cache-manifest.json',recursive=False)
h=hashlib.sha256()
with archive.open('rb') as f:
    for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
receipt=dict(archive=str(archive),bytes=archive.stat().st_size,sha256=h.hexdigest(),source_arrays_exported=False)
(root/('export-'+job+'.json')).write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
