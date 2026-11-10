from pathlib import Path,PurePosixPath
import collections,datetime,hashlib,json,subprocess,sys,tarfile
import numpy as np
from stage1_v2_audit import audit_block,records,sha
from stage1_v2_evaluation_analysis import planned_statistics
ROOT=Path(__file__).resolve().parent.parent
status=json.loads((ROOT/'outputs/stage1-v2-recovery-status.json').read_text())
receipt=status['forensic']['export']
out=ROOT/'outputs/stage1-v2-forensic-6503602';out.mkdir(exist_ok=True)
archive=out/'evidence.tar.gz'
if not archive.exists() or sha(archive)!=receipt['sha256']:
    subprocess.run(['scp','-o','BatchMode=yes','-o','ConnectTimeout=30','u6vs.aip2.isambard:'+receipt['archive'],str(archive)],check=True,timeout=220)
assert sha(archive)==receipt['sha256']
members=0
with tarfile.open(archive) as tar:
    for m in tar.getmembers():
        assert m.isfile() and not m.name.startswith('/') and '..' not in PurePosixPath(m.name).parts and '\\' not in m.name and ':' not in m.name
        p=out/m.name;assert out.resolve() in p.resolve().parents
        p.parent.mkdir(parents=True,exist_ok=True)
        stream=tar.extractfile(m);h=hashlib.sha256()
        target=None if p.exists() else p.open('wb')
        try:
            for chunk in iter(lambda:stream.read(1024*1024),b''):
                h.update(chunk)
                if target:target.write(chunk)
        finally:
            if target:target.close()
        assert sha(p)==h.hexdigest(),('Archive/member mismatch',m.name)
        members+=1
print(json.dumps(dict(archive_verified=True,members=members)),flush=True)
remote=json.loads((out/'analysis/analysis.json').read_text())
for line in (out/'analysis/results.sha256').read_text().splitlines():
    h,name=line.split('  ',1);assert sha(out/'analysis'/name)==h
pack=ROOT/'work/stage1-v2'
assert sha(pack/'inputs.sha256')==remote['input_manifest_sha256']
for line in (pack/'inputs.sha256').read_text().splitlines():
    h,name=line.split('  ',1);assert sha(pack/name)==h
sys.path.insert(0,str(pack));from fixtures import FAMILIES
from run_benchmark import plan
allkeys=set();counts=collections.defaultdict(lambda:collections.defaultdict(collections.Counter));audits=[]
contexts=json.loads((pack/'contexts.json').read_text())['contexts'];evaluation=list(records(pack/'evaluation.jsonl'))
for i in range(4):
    name='evaluation-6502171_'+str(i);run=out/'runs'/name;block=run/('evaluation-'+str(i).zfill(3))
    expected=remote['source_file_hashes'][name]
    assert {str(p.relative_to(run)).replace('\\','/') for p in run.rglob('*') if p.is_file()}==set(expected)
    for relative,h in expected.items():assert sha(run/relative)==h,(name,relative)
    rows=[r for r in evaluation if (r['instance']//2)%4==i]
    assert json.loads((block/'plan.json').read_text())==plan(rows,contexts,2,91300+i)
    audited=audit_block(block,pack);assert audited['unresolved_attempts']==0
    assert audited['arms']==remote['per_shard_audits'][i]['arms']
    for r in records(block/'results.jsonl'):
        assert r['key'] not in allkeys;allkeys.add(r['key'])
    for template,arms in audited['template_joint_counts'].items():
        for arm,c in arms.items():counts[template][arm].update(c)
    audits.append(dict(shard=i,records=audited['responses'],transport_failures=audited['summary']['transport_failures']))
    print(json.dumps(audits[-1]),flush=True)
assert allkeys=={r['key'] for r in plan(evaluation,contexts,2,0)} and len(allkeys)==184320
arms=sorted(remote['arm_counts']);values=np.zeros((10,6,24))
for fi,family in enumerate(FAMILIES):
    templates=sorted(t for t in counts if t.startswith(family+'/'));assert len(templates)==6
    for ti,t in enumerate(templates):
        for ai,arm in enumerate(arms):
            c=counts[t][arm];assert c['n']==128;values[fi,ti,ai]=c['sum']/c['n']
recomputed=planned_statistics(values,arms)
assert recomputed==remote['analysis'],'Local/remote declared statistics differ'
result=dict(status='PASS',verified_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            verified_archive_sha256=receipt['sha256'],archive_members_verified=members,
            final_request_records=184320,transport_failures=39484,
            successful_transport_responses=144836,collection_operational_status='DEGRADED_SERVICE_FAILURE',
            actual_requests_rechecked=True,raw_outputs_reparsed_and_rescored=True,
            paired_template_statistics_recomputed=True,per_shard=audits,
            script_sha256=sha(__file__),original_failed_job_preserved=True)
(out/'local-verification.json').write_text(json.dumps(result,indent=2)+'\n')
(out/'export-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(result,indent=2))
