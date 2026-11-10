from pathlib import Path
import datetime,hashlib,json,subprocess,sys,tarfile
import numpy as np
ROOT=Path(__file__).resolve().parent.parent;OUT=ROOT/'outputs/lidar-diagnostic-6505336';OUT.mkdir(exist_ok=True)
remote='/projects/u6vs/hnc-organism/expansion-20260912/lidar-audit-v1/'
opts=['-o','BatchMode=yes','-o','ConnectTimeout=30']
subprocess.run(['scp']+opts+['u6vs.aip2.isambard:'+remote+'receipt-6505336.json',str(OUT/'export-receipt.json')],check=True,timeout=90)
r=json.loads((OUT/'export-receipt.json').read_text());archive=OUT/'evidence.tar.gz'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
if not archive.exists():subprocess.run(['scp']+opts+['u6vs.aip2.isambard:'+r['archive'],str(archive)],check=True,timeout=180)
assert sha(archive)==r['archive_sha256'] and archive.stat().st_size==r['bytes']
with tarfile.open(archive) as tar:
    assert len(tar.getmembers())==r['members']
    for m in tar.getmembers():
        assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
        p=OUT/m.name;assert OUT.resolve() in p.resolve().parents
        data=tar.extractfile(m).read()
        if p.exists():assert p.read_bytes()==data
        else:p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
manifest=json.loads((OUT/'export-manifest.json').read_text())
for name,h in manifest.items():assert sha(OUT/name)==h
sys.path.insert(0,str(ROOT/'work/lidar-audit-v1'));import numpy_audit as a
operators={gi:dict(np.load(OUT/f'audit/operators-grid-{gi}.npz',allow_pickle=False)) for gi in [0,1]}
for gi,h in [(0,80),(1,40)]:a.verify_operators(operators[gi],h)
paths=[OUT/f'results/historical-{i:03d}.json' for i in [0,32]]+[OUT/f'results/new-{i:03d}.json' for i in range(128)]
records=[json.loads(p.read_text()) for p in paths];verifications=[]
for p,r in zip(paths,records):
    verifications.append(a.verify_record(p,operators[r['grid_index']],'255d45a1222770eac0916adbab1233b7480a0b719f8cbca42a30b8681b4cbb13'))
    if len(verifications)%16==0:print(json.dumps(dict(local_verified=len(verifications),expected=130)),flush=True)
analysis=a.analyse(records[2:]);saved=json.loads((OUT/'audit/analysis.json').read_text())
def compare(x,y):
    if isinstance(x,dict):
        assert set(x)==set(y);return max([compare(x[k],y[k]) for k in x] or [0.])
    if isinstance(x,list):
        assert len(x)==len(y);return max([compare(v,w) for v,w in zip(x,y)] or [0.])
    if isinstance(x,float):
        delta=abs(x-y);assert delta<=1e-13;return delta
    assert x==y;return 0.
analysis_difference=compare(analysis,saved)
original=json.loads((OUT/'audit/verification.json').read_text())
for left,right in zip(verifications,original['verifications']):
    for key in ['file','arrays_sha256','result_sha256','test_examples','calibration_examples']:assert left[key]==right[key]
tests=json.loads((OUT/'operations/tests-6505275.json').read_text());assert tests['passed']
accounting=subprocess.check_output(['ssh']+opts+['u6vs.aip2.isambard','sacct -X -j 6505264,6505275,6505304,6505336 --format=JobID,State,ExitCode,ElapsedRaw,AllocNodes -P'],text=True,timeout=70)
assert '6505336|COMPLETED|0:0|' in accounting
result=dict(status='PASS',verified_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),members_verified=len(manifest)+1,
            archive_sha256=sha(archive),records=130,test_examples=1290000,calibration_examples=387000,
            locally_verified_image_pairs=1040,numerically_checked_methods_per_image=16,all_recorded_method_metrics=20,
            analysis_reproduced_exactly=analysis==saved,analysis_maximum_float_difference=analysis_difference,accounting=accounting,
            comparison_to_remote_checks='Per-record hashes and metrics exact; independent NumPy map differences may vary slightly by CPU platform.')
(OUT/'local-verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
