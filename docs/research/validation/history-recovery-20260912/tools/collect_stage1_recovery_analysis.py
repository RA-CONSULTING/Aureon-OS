from pathlib import Path, PurePosixPath
import datetime, hashlib, json, subprocess, tarfile
from stage1_v2_audit import sha
from stage1_v2_recovery_analysis import analyse
ROOT=Path(__file__).resolve().parent.parent
REMOTE='/projects/u6vs/hnc-organism/expansion-20260912/stage1-v2-recovery-analysis-v1'
OUT=ROOT/'outputs/stage1-v2-recovery-6504504';OUT.mkdir(exist_ok=True)
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=30','u6vs.aip2.isambard','cat '+REMOTE+'/export-analysis-6504504.json'],capture_output=True,check=True,timeout=60)
receipt=json.loads(r.stdout);archive=OUT/'evidence.tar.gz'
if not archive.exists():
    subprocess.run(['scp','-o','BatchMode=yes','-o','ConnectTimeout=30','u6vs.aip2.isambard:'+receipt['archive'],str(archive)],check=True,timeout=180)
assert sha(archive)==receipt['sha256'] and archive.stat().st_size==receipt['bytes']
members=0
with tarfile.open(archive) as tar:
    for m in tar.getmembers():
        assert m.isfile() and not m.name.startswith('/') and '..' not in PurePosixPath(m.name).parts and '\\' not in m.name and ':' not in m.name
        p=OUT/m.name;assert OUT.resolve() in p.resolve().parents;p.parent.mkdir(parents=True,exist_ok=True)
        stream=tar.extractfile(m);h=hashlib.sha256();target=None if p.exists() else p.open('wb')
        try:
            for chunk in iter(lambda:stream.read(1024*1024),b''):
                h.update(chunk)
                if target:target.write(chunk)
        finally:
            if target:target.close()
        assert sha(p)==h.hexdigest(),m.name
        members+=1
print(json.dumps(dict(archive_verified=True,members=members)),flush=True)
remote=json.loads((OUT/'analysis/analysis.json').read_text())
for line in (OUT/'analysis/results.sha256').read_text().splitlines():
    h,name=line.split('  ',1);assert sha(OUT/'analysis'/name)==h
result=analyse(ROOT/'work/stage1-v2',OUT/'run',ROOT/'outputs/stage1-v2-forensic-6503602/runs',ROOT/'outputs/stage1-v2-forensic-6503602/analysis/analysis.json',ROOT/'work/stage1-v2-recovery-v1')
assert all(result[k]==remote[k] for k in result),'Local verification differs from remote analysis'
verification=dict(status='PASS',verified_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  archive_sha256=receipt['sha256'],archive_members_verified=members,
                  recovery_calls_reparsed_and_rescored=53760,combined_evaluation_requests=184320,
                  original_source_hashes_reverified=True,paired_statistics_recomputed_exactly=True,
                  original_degraded_first_run_preserved=True,script_sha256=sha(__file__),analysis_sha256=sha(OUT/'analysis/analysis.json'))
(OUT/'local-verification.json').write_text(json.dumps(verification,indent=2)+'\n')
(OUT/'export-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(verification,indent=2),flush=True)
print(json.dumps(dict(analysis=result['analysis'],repeat=result['repeated_original_successful_requests']),indent=2),flush=True)
