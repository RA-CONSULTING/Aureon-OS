"""Immutable per-replicate ledgers; masks never consume anomaly boundaries."""
import argparse,concurrent.futures,datetime,fcntl,hashlib,json,math,os,pathlib,resource,time
import numpy as np
import audit_qgita_ucr_robustness as legacy
import benchmark_ucr_confirmatory as canonical
import qgita_missing as candidate


def sha(p):
    h=hashlib.sha256()
    with pathlib.Path(p).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def encode(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def save(path,payload):
    path=pathlib.Path(path);assert not path.exists()
    wrapper=dict(payload=payload,payload_sha256=hashlib.sha256(encode(payload)).hexdigest())
    temp=path.with_suffix(path.suffix+'.tmp')
    with temp.open('wb') as f:f.write(encode(wrapper)+b'\n');f.flush();os.fsync(f.fileno())
    os.replace(temp,path)


def load(path):
    wrapper=json.loads(pathlib.Path(path).read_text());payload=wrapper['payload']
    assert hashlib.sha256(encode(payload)).hexdigest()==wrapper['payload_sha256'],'Corrupt checkpoint ledger'
    return payload


def seed(dataset,scenario,replicate,phase):
    root=20260728 if phase=='historical' else 20260912
    return int.from_bytes(hashlib.sha256(f'{root}|{dataset}|{scenario}|{replicate}'.encode()).digest()[:8],'big')


def mask_for(length,train,dataset,scenario,replicate,phase):
    rng=np.random.default_rng(seed(dataset,scenario,replicate,phase))
    if scenario.startswith('mcar_'):return legacy.mcar_mask(length,train,int(scenario.split('_')[1])/100,rng)
    if scenario=='burst_05':return legacy.burst_mask(length,train,rng)
    if scenario!='burst_10':raise ValueError('Unknown scenario')
    mask=np.zeros(length,dtype=bool);size=math.ceil(.02*(length-train))
    for start in rng.integers(train,length,size=5):mask[int(start):min(length,int(start)+size)]=True
    return mask


def run_series(task):
    args,record=task;pack=pathlib.Path(args['pack']);cache=pathlib.Path(args['cache']);root=pathlib.Path(args['output'])
    dataset=record['dataset_id'];directory=root/('dataset-'+dataset);directory.mkdir(parents=True,exist_ok=True)
    lock=(directory/'.writer.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    started=time.monotonic();cfg=json.loads((pack/'config.json').read_text())
    cm=json.loads((cache/'cache-manifest.json').read_text());cached=next(r for r in cm['series'] if r['dataset_id']==dataset)
    assert sha(cache/cached['array_file'])==cached['array_sha256']
    assert cached['member_sha256']==record['uncompressed_sha256']
    values=np.load(cache/cached['array_file'],allow_pickle=False)
    assert len(values)==record['row_count'] and np.all(np.isfinite(values))
    train=record['train_end_zero_based_exclusive'];start=record['anomaly_start_zero_based'];end=record['anomaly_end_zero_based']
    scales=legacy.training_scales(values,train);cleanbank=candidate.score_bank(values,np.zeros(len(values),dtype=bool),train,scales)
    clean=candidate.select(cleanbank,train,start,end);expected=record['methods'][canonical.PRIMARY_METHOD]
    for field in ['selected_index_zero_based','strict_localisation','ucr_localisation']:assert clean[field]==expected[field],(dataset,field)
    identity=dict(dataset_id=dataset,config_sha256=sha(pack/'config.json'),input_manifest_sha256=sha(pack/'inputs.sha256'),
                  cache_manifest_sha256=sha(cache/'cache-manifest.json'),array_sha256=cached['array_sha256'],numpy=np.__version__)
    clean_payload=dict(identity=identity,family_key=record['family_key'],clean=clean,training_scales=scales.tolist(),
                       canonical_selected_score_absolute_difference=abs(clean['selected_score']-expected['selected_score']))
    cp=directory/'clean.json'
    if cp.exists():assert load(cp)==clean_payload,'Clean checkpoint identity changed'
    else:save(cp,clean_payload)
    historical=json.loads((pack/'historical.json').read_text());old=next(r for r in historical['series'] if r['dataset_id']==dataset)
    created=0;reused=0;new_sets=0;sets_by_phase={}
    for phase,n in [('historical',5),('new_masks',args['new_replicates'])]:
        scenarios=cfg['historical_scenarios'] if phase=='historical' else cfg['new_scenarios']
        sets_by_phase[phase]=n*len(scenarios)
        for replicate in range(n):
            target=directory/(phase+'-r'+str(replicate).zfill(3)+'.json')
            if target.exists():
                stored=load(target)
                assert stored['identity']==identity and stored['phase']==phase and stored['replicate']==replicate
                assert [r['scenario'] for r in stored['scenarios']]==scenarios
                reused+=1;continue
            t0=time.monotonic();rows=[]
            for scenario in scenarios:
                mask=mask_for(len(values),train,dataset,scenario,replicate,phase)
                assert not np.any(mask[:train]);filled=legacy.locf(values,mask)
                controlbank=candidate.score_bank(filled,mask,train,scales,require_observed=False)
                control=candidate.select(controlbank,train,start,end)
                observedbank=candidate.score_bank(values,mask,train,scales)
                observed=candidate.select(observedbank,train,start,end)
                old_difference=None
                if phase=='historical':
                    oldrow=old['missing'][scenario][replicate]
                    assert oldrow['seed']==seed(dataset,scenario,replicate,phase)
                    assert oldrow['realized_missing_count']==int(mask.sum())
                    for field in ['selected_index_zero_based','strict_localisation','ucr_localisation']:assert control[field]==oldrow[field],(dataset,scenario,replicate,field)
                    old_difference=abs(control['selected_score']-oldrow['selected_score'])
                triplet=candidate.selected_triplet(observedbank,observed,mask,train)
                assert triplet is None or not triplet['contains_imputed_value']
                rows.append(dict(scenario=scenario,seed=seed(dataset,scenario,replicate,phase),mask_sha256=hashlib.sha256(mask.tobytes()).hexdigest(),
                    missing_count=int(mask.sum()),missing_fraction=float(mask.sum()/(len(values)-train)),
                    locf=control,observed_triplet=observed,
                    locf_winning_triplet=candidate.selected_triplet(controlbank,control,mask,train),
                    observed_winning_triplet=triplet,clean_winning_triplet_under_mask=candidate.selected_triplet(cleanbank,clean,mask,train),
                    clean_winning_index_still_scoreable=bool(np.isfinite(observedbank['scores'][clean['selected_index_zero_based']-train])),
                    historical_locf_selected_score_absolute_difference=old_difference))
            payload=dict(identity=identity,phase=phase,replicate=replicate,scenarios=rows,
                         elapsed_seconds=time.monotonic()-t0,job=os.environ.get('SLURM_JOB_ID'))
            save(target,payload);created+=1;new_sets+=len(scenarios)
    return dict(dataset_id=dataset,blocks_created=created,blocks_reused=reused,new_mask_sets_computed=new_sets,
                total_sets_by_phase=sets_by_phase,elapsed_seconds=time.monotonic()-started,peak_rss_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                clean_sha256=sha(cp))


def main():
    p=argparse.ArgumentParser();p.add_argument('--pack',required=True);p.add_argument('--cache',required=True)
    p.add_argument('--output',required=True);p.add_argument('--summary',required=True);p.add_argument('--workers',type=int,required=True)
    p.add_argument('--pilot',action='store_true');p.add_argument('--new-replicates',type=int,default=32)
    a=p.parse_args();assert np.__version__=='2.3.5';pack=pathlib.Path(a.pack);cfg=json.loads((pack/'config.json').read_text())
    assert 0<a.new_replicates<=cfg['new_replicates'] and 0<a.workers<=64
    for line in (pack/'inputs.sha256').read_text().splitlines():
        h,name=line.split('  ',1);assert sha(pack/name)==h
    cm=pathlib.Path(a.cache)/'cache-manifest.json';assert sha(cm)==cfg['cache_manifest_sha256']
    canonical_result=json.loads((pack/'canonical.json').read_text());series=canonical_result['series']
    if a.pilot:
        ids=set(legacy.representative_ids(series).values());series=[r for r in series if r['dataset_id'] in ids]
        assert len(series)==46 and a.new_replicates==2
    else:assert len(series)==250 and a.new_replicates==32
    assert not pathlib.Path(a.summary).exists();root=pathlib.Path(a.output);root.mkdir(parents=True,exist_ok=True)
    started=time.monotonic();results=[]
    with concurrent.futures.ProcessPoolExecutor(max_workers=a.workers) as pool:
        for result in pool.map(run_series,[(vars(a),r) for r in series],chunksize=1):
            results.append(result);print(json.dumps(result),flush=True)
    summary=dict(schema='qgita-missingness-wave/v1',status='COMPLETE',job=os.environ.get('SLURM_JOB_ID'),pilot=a.pilot,
                 config_sha256=sha(pack/'config.json'),input_manifest_sha256=sha(pack/'inputs.sha256'),
                 series=len(results),workers=a.workers,new_replicates=a.new_replicates,elapsed_seconds=time.monotonic()-started,
                 completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),per_series=results)
    save(a.summary,summary)
    print(json.dumps({k:v for k,v in summary.items() if k!='per_series'}),flush=True)

if __name__=='__main__':main()
