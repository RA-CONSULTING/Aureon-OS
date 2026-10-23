"""Apply verified commissioning changes while retaining every replaced original."""
import hashlib, json, pathlib, shutil
HERE=pathlib.Path(__file__).resolve().parent
ROOT=pathlib.Path('/srv/aureon/runtime/workspace').resolve()
BACKUP=pathlib.Path('/srv/aureon/import/pre-cloud-overlay')
manifest=json.loads((HERE/'overlay-manifest.json').read_text())
for row in manifest['files']:
    source=(HERE/'files'/row['path']).resolve()
    dest=(ROOT/row['path']).resolve()
    if not source.is_relative_to(HERE/'files') or not dest.is_relative_to(ROOT):
        raise ValueError('Unsafe overlay path')
    if hashlib.sha256(source.read_bytes()).hexdigest()!=row['sha256']:
        raise ValueError('Overlay integrity check failed')
changed=[]
for row in manifest['files']:
    source=HERE/'files'/row['path']
    dest=ROOT/row['path']
    original=None
    if dest.exists():
        original=hashlib.sha256(dest.read_bytes()).hexdigest()
        backup=BACKUP/row['path']
        if not backup.exists():
            backup.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(dest,backup)
    dest.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,dest)
    changed.append({'path':row['path'],'original_sha256':original,'deployed_sha256':row['sha256']})
(HERE/'overlay-receipt.json').write_text(json.dumps({'verified':True,'files':changed},indent=2))
print('Verified and applied '+str(len(changed))+' deployment files; replaced originals retained')
