import collections,datetime,hashlib,json,pathlib,tarfile
BASE=pathlib.Path('/projects/u6vs/hnc-organism/expansion-20260912')
audit_path=BASE/'stage1-audit-v1/audit-6500947.json'
assert hashlib.sha256(audit_path.read_bytes()).hexdigest()=='91e5281235f954c62a4fffb98d15bfecf0d36450dd5f6bea9eb69e2bf22b1395'
audit=json.loads(audit_path.read_text());assert audit['complete_matrix'] and audit['integrity_status']=='PASS'
metrics=collections.defaultdict(collections.Counter);actions=collections.defaultdict(collections.Counter);confusions=collections.defaultdict(collections.Counter);examples=[];archive_files=[]
for receipt in audit['shard_receipts']:
    root=pathlib.Path(receipt['path'])
    for name,h in receipt['files_sha256'].items():
        path=root/name;assert hashlib.sha256(path.read_bytes()).hexdigest()==h
        archive_files.append(('shard-%04d/'%receipt['shard']+name,path))
    for line in (root/'raw-results.jsonl').read_text().splitlines():
        r=json.loads(line);c=r['condition'];family=r['family'];s=r['scoring'];parsed=r['parsed']
        act=parsed.get('action') if isinstance(parsed,dict) else None
        act_label=json.dumps(act,sort_keys=True) if not isinstance(act,str) else act
        enum_valid=isinstance(act,str) and act in {'report','hold','request_more','refuse'}
        for key in [c,c+'/'+family]:
            metrics[key].update(n=1,json_invalid=int(not s['json_valid']),action_enum_invalid=int(not enum_valid),action_correct=int(s['action_correct']),verdict_correct=int(s['verdict_correct']),source_complete=int(s['sources_complete']))
        actions[c][act_label]+=1
        confusions[c][r['expected_action']+' -> '+act_label]+=1
        if receipt['shard']==0 and c in ['full_organism','frozen_baseline'] and not s['action_correct'] and r['repetition']==0:
            examples.append({k:r[k] for k in ['condition','family','scenario','expected_action','expected_verdict','parsed','scoring']})
result=dict(schema='stage1-error-diagnostics/v1',generated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_audit_sha256=hashlib.sha256(audit_path.read_bytes()).hexdigest(),
    scope='Descriptive error diagnosis of the same audited responses; no new inference or changed scores.',counts={k:dict(v) for k,v in metrics.items()},action_distributions={k:dict(v) for k,v in actions.items()},action_confusions={k:dict(v) for k,v in confusions.items()},shard0_wrong_action_examples=examples)
out=pathlib.Path(__file__).parent
with (out/'diagnostics.json').open('x') as f:json.dump(result,f,indent=2)
archive=out/'stage1-verified-responses.tar.gz'
with tarfile.open(archive,'x:gz') as tar:
    for name,path in archive_files:tar.add(path,arcname=name,recursive=False)
    tar.add(audit_path,arcname='audit-6500947.json',recursive=False)
export=dict(archive=str(archive),bytes=archive.stat().st_size,sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),files=len(archive_files)+1,scope='Six verified receipt/response/scenario/runtime files per shard plus the full retrospective audit. Model weights and other logs are not included.')
with (out/'export.json').open('x') as f:json.dump(export,f,indent=2)
print(json.dumps(dict(counts={c:dict(metrics[c]) for c in ['full_organism','frozen_baseline']},export=export),indent=2))
