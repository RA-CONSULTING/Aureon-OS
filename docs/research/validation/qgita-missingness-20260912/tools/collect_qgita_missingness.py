from pathlib import Path,PurePosixPath
import collections,datetime,hashlib,json,math,subprocess,tarfile
import numpy as np
from audit_qgita_missingness import read,sha,statistics
ROOT=Path(__file__).resolve().parent.parent;OUT=ROOT/'outputs/qgita-missingness-6505031';OUT.mkdir(exist_ok=True)
status=json.loads((ROOT/'outputs/qgita-missingness-status-v1.json').read_text());assert status['accounting']['6505031']['State']=='COMPLETED'
receipt=status['export'];archive=OUT/'evidence.tar.gz'
if not archive.exists():subprocess.run(['scp','-o','BatchMode=yes','-o','ConnectTimeout=30','u6vs.aip2.isambard:'+receipt['archive'],str(archive)],check=True,timeout=180)
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
        assert sha(p)==h.hexdigest();members+=1
print(json.dumps(dict(archive_members_verified=members)),flush=True)
remote=json.loads((OUT/'audit/analysis-6505031.json').read_text());assert remote['status']=='PASS'
pack=ROOT/'work/qgita-missingness-v1';cfg=json.loads((pack/'config.json').read_text())
assert sha(pack/'inputs.sha256')==remote['input_manifest_sha256']
for line in (pack/'inputs.sha256').read_text().splitlines():
    h,n=line.split('  ',1);assert sha(pack/n)==h
assert sha(OUT/'source/cache-manifest.json')==cfg['cache_manifest_sha256']
canonical=json.loads((pack/'canonical.json').read_text());records={r['dataset_id']:r for r in canonical['series']}
historical={r['dataset_id']:r for r in json.loads((pack/'historical.json').read_text())['series']}
audits=[];cases=0
for original in remote['per_series_audits']:
    dataset=original['dataset_id'];directory=OUT/'campaign'/('dataset-'+dataset);record=records[dataset]
    assert {p.name for p in directory.glob('*.json')}==set(original['source_hashes'])
    for name,h in original['source_hashes'].items():assert sha(directory/name)==h
    clean=read(directory/'clean.json');summary={}
    for phase,reps in [('historical',5),('new_masks',32)]:
        names=cfg['historical_scenarios'] if phase=='historical' else cfg['new_scenarios'];summary[phase]={s:collections.Counter() for s in names}
        for rep in range(reps):
            block=read(directory/(phase+'-r'+str(rep).zfill(3)+'.json'))
            assert block['phase']==phase and block['replicate']==rep and block['identity']==clean['identity']
            assert [r['scenario'] for r in block['scenarios']]==names
            for row in block['scenarios']:
                root_seed=20260728 if phase=='historical' else 20260912
                seed=int.from_bytes(hashlib.sha256(f"{root_seed}|{dataset}|{row['scenario']}|{rep}".encode()).digest()[:8],'big');assert seed==row['seed']
                for method in ['locf','observed_triplet']:
                    result=row[method];peak=result['selected_index_zero_based'];start=record['anomaly_start_zero_based'];end=record['anomaly_end_zero_based'];train=record['train_end_zero_based_exclusive']
                    if peak is None:assert result['abstained'] and not result['ucr_localisation'] and not result['strict_localisation']
                    else:
                        assert train<=peak<record['row_count'] and not result['abstained']
                        margin=max(end-start+1,100)
                        assert result['ucr_localisation']==(max(train,start-margin)<=peak<=min(record['row_count']-1,end+margin))
                        assert result['strict_localisation']==(start<=peak<=end)
                        assert math.isfinite(result['selected_score']) and result['selected_score']>=0
                if phase=='historical':
                    old=historical[dataset]['missing'][row['scenario']][rep]
                    for field in ['selected_index_zero_based','strict_localisation','ucr_localisation']:assert old[field]==row['locf'][field]
                c=summary[phase][row['scenario']];l=row['locf']['ucr_localisation'];o=row['observed_triplet']['ucr_localisation'];cl=clean['clean']['ucr_localisation']
                c.update(n=1,locf=int(l),observed=int(o),strict_locf=int(row['locf']['strict_localisation']),strict_observed=int(row['observed_triplet']['strict_localisation']),
                    gain=int(o and not l),loss=int(l and not o),clean_success_lost_by_locf=int(cl and not l),clean_success_recovered=int(cl and not l and o),
                    abstentions=int(row['observed_triplet']['abstained']),locf_imputed_winner=int(row['locf_winning_triplet']['contains_imputed_value']),
                    failed_locf_imputed_winner=int(not l and row['locf_winning_triplet']['contains_imputed_value']),locf_failures=int(not l),
                    coverage_sum=row['observed_triplet']['scoreable_fraction'],missing_fraction_sum=row['missing_fraction'])
                cases+=1
    recomputed={p:{s:dict(c) for s,c in d.items()} for p,d in summary.items()};assert recomputed==original['per_scenario']
    audits.append(dict(original,per_scenario=recomputed))
assert cases==51750 and len(audits)==250 and len({r['family_key'] for r in audits})==46
assert statistics(audits,cfg)==remote['analysis'],'Paired family statistics did not reproduce'
result=dict(status='PASS',verified_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),archive_sha256=receipt['sha256'],archive_members_verified=members,
            verified_mask_sets=cases,verified_candidate_control_outcomes=2*cases,original_locf_decisions_rechecked=3750,
            source_and_ledger_hashes_verified=True,local_endpoint_and_counter_recomputation=True,local_family_statistics_recomputed_exactly=True,
            full_score_timelines_independently_recomputed_on_isambard=True,raw_numeric_inputs_exported=False,script_sha256=sha(__file__),analysis_sha256=sha(OUT/'audit/analysis-6505031.json'))
(OUT/'local-verification.json').write_text(json.dumps(result,indent=2)+'\n');(OUT/'export-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(result,indent=2),flush=True)
