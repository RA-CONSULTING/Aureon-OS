import datetime,hashlib,json,sys
from pathlib import Path
root=Path(sys.argv[1]);status=int(sys.argv[2])
stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
(root/'exit.json').write_text(json.dumps(dict(batch_exit_code=status,finalized_utc=stamp),indent=2)+'\n')
if status==0:(root/'completed_utc.txt').write_text(stamp+'\n')
rows=[]
for p in sorted(root.rglob('*')):
    if not p.is_file() or p.name=='results.sha256':continue
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    rows.append(h.hexdigest()+'  '+str(p.relative_to(root)))
(root/'results.sha256').write_text('\n'.join(rows)+'\n')
