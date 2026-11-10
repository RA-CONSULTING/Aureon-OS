"""Independent full-timeline recomputation and family-level analysis of the new study."""
import argparse,collections,concurrent.futures,datetime,hashlib,json,math,pathlib,sys,time
import numpy as np


def sha(p):
    h=hashlib.sha256()
    with pathlib.Path(p).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def canonical_bytes(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def read(path):
    value=json.loads(pathlib.Path(path).read_text());payload=value['payload']
    assert hashlib.sha256(canonical_bytes(payload)).hexdigest()==value['payload_sha256']
    return payload


def independent_bank(x,mask,train,scales,lattice,observed):
    # Explicit 12-by-test-time matrix, distinct from the runner's updating maximum/winner loop.
    times=np.arange(train,len(x));matrix=np.full((len(lattice)-2,len(times)),-np.inf)
    for row in range(len(lattice)-2):
        p,c,s=map(int,lattice[row:row+3]);starts=times-s
        allowed=starts>=0
        if observed:allowed&=~(mask[starts+p]|mask[starts+c]|mask[times])
        t=times[allowed];left=t-s+p;middle=t-s+c;hm=float(c-p);hp=float(s-c)
        value=2./(hm+hp)*((x[t]-x[middle])/hp-(x[middle]-x[left])/hm)
        matrix[row,allowed]=np.abs(value)/scales[row]
    maximum=matrix.max(axis=0);winner=matrix.argmax(axis=0)+1
    counts=np.sum(np.isfinite(matrix),axis=0);maximum[counts==0]=np.nan;winner[counts==0]=-1
    return maximum,winner,counts


def endpoint(scores,train,start,end):
    finite=np.isfinite(scores);coverage=int(finite.sum())
    if not coverage:return dict(selected_index_zero_based=None,selected_index_one_based=None,selected_score=None,
        strict_localisation=False,ucr_localisation=False,abstained=True,scoreable_test_points=0,test_points=len(scores),scoreable_fraction=0.)
    largest=float(np.max(scores[finite]));ties=np.flatnonzero(scores==largest);chosen=train+int(ties[0]);margin=max(end-start+1,100)
    distance=chosen-start if chosen<start else chosen-end if chosen>end else 0
    lower=max(train,start-margin);upper=min(train+len(scores)-1,end+margin)
    return dict(selected_index_zero_based=chosen,selected_index_one_based=chosen+1,selected_score=largest,
        maximum_tie_count=len(ties),maximum_tie=bool(len(ties)>1),strict_localisation=bool(start<=chosen<=end),
        ucr_localisation=bool(lower<=chosen<=upper),signed_distance_from_anomaly=distance,absolute_distance_from_anomaly=abs(distance),
        ucr_tolerance_start_zero_based=lower,ucr_tolerance_end_zero_based=upper,abstained=False,
        scoreable_test_points=coverage,test_points=len(scores),scoreable_fraction=coverage/len(scores))


def verify_one(task):
    args,record=task;pack=pathlib.Path(args['pack']);cache=pathlib.Path(args['cache']);root=pathlib.Path(args['campaign']);sys.path.insert(0,str(pack))
    import audit_qgita_ucr_robustness as legacy
    dataset=record['dataset_id'];directory=root/('dataset-'+dataset);cfg=json.loads((pack/'config.json').read_text())
    cm=json.loads((cache/'cache-manifest.json').read_text());cr=next(r for r in cm['series'] if r['dataset_id']==dataset)
    assert sha(cache/cr['array_file'])==cr['array_sha256'] and cr['member_sha256']==record['uncompressed_sha256']
    x=np.load(cache/cr['array_file'],allow_pickle=False);train=record['train_end_zero_based_exclusive'];start=record['anomaly_start_zero_based'];end=record['anomaly_end_zero_based']
    identity=dict(dataset_id=dataset,config_sha256=sha(pack/'config.json'),input_manifest_sha256=sha(pack/'inputs.sha256'),cache_manifest_sha256=sha(cache/'cache-manifest.json'),array_sha256=cr['array_sha256'],numpy=np.__version__)
    clean=read(directory/'clean.json');assert clean['identity']==identity and clean['family_key']==record['family_key']
    scales=legacy.training_scales(x,train);assert scales.tolist()==clean['training_scales']
    zero=np.zeros(len(x),dtype=bool);cb=independent_bank(x,zero,train,scales,legacy.LATTICE,True)
    assert endpoint(cb[0],train,start,end)==clean['clean']
    for field in ['selected_index_zero_based','ucr_localisation','strict_localisation']:assert clean['clean'][field]==record['methods']['qgita_fibonacci_scale_normalized'][field]
    historical=json.loads((pack/'historical.json').read_text());old=next(r for r in historical['series'] if r['dataset_id']==dataset)
    hashes={'clean.json':sha(directory/'clean.json')};summary={};cases=0
    for phase,n in [('historical',5),('new_masks',32)]:
        names=cfg['historical_scenarios'] if phase=='historical' else cfg['new_scenarios'];summary[phase]={name:collections.Counter() for name in names}
        for replicate in range(n):
            file=directory/(phase+'-r'+str(replicate).zfill(3)+'.json');block=read(file);hashes[file.name]=sha(file)
            assert block['identity']==identity and block['phase']==phase and block['replicate']==replicate
            assert [row['scenario'] for row in block['scenarios']]==names
            for row in block['scenarios']:
                name=row['scenario'];root_seed=20260728 if phase=='historical' else 20260912
                seed=int.from_bytes(hashlib.sha256(f'{root_seed}|{dataset}|{name}|{replicate}'.encode()).digest()[:8],'big');assert row['seed']==seed
                rng=np.random.default_rng(seed);mask=np.zeros(len(x),dtype=bool)
                if name.startswith('mcar_'):
                    fraction=int(name.split('_')[1])/100;count=round(fraction*(len(x)-train));mask[train+rng.choice(len(x)-train,size=count,replace=False)]=True
                else:
                    length=math.ceil((.01 if name=='burst_05' else .02)*(len(x)-train))
                    for s in rng.integers(train,len(x),size=5):mask[int(s):min(len(x),int(s)+length)]=True
                assert row['mask_sha256']==hashlib.sha256(mask.tobytes()).hexdigest()
                assert row['missing_count']==int(mask.sum()) and row['missing_fraction']==float(mask.sum()/(len(x)-train))
                # Independent causal carry-forward index construction.
                observed_indices=np.flatnonzero(~mask);which=np.searchsorted(observed_indices,np.arange(len(x)),side='right')-1;filled=x[observed_indices[which]]
                control=independent_bank(filled,mask,train,scales,legacy.LATTICE,False)
                actual=independent_bank(x,mask,train,scales,legacy.LATTICE,True)
                for field,bank in [('locf',control),('observed_triplet',actual)]:
                    expected=endpoint(bank[0],train,start,end);assert expected==row[field],(dataset,phase,replicate,name,field)
                    peak=expected['selected_index_zero_based'];label=field if field=='locf' else 'observed'
                    triplet=row[label+'_winning_triplet']
                    if peak is None:assert triplet is None
                    else:
                        k=int(bank[1][peak-train]);p,c,s=map(int,legacy.LATTICE[k-1:k+2]);indices=[peak-s+p,peak-s+c,peak]
                        assert triplet==dict(component=k,indices=indices,missing=[bool(mask[i]) for i in indices],contains_imputed_value=bool(mask[indices].any()))
                        if field=='observed_triplet':assert not triplet['contains_imputed_value']
                if phase=='historical':
                    prior=old['missing'][name][replicate]
                    for field in ['selected_index_zero_based','strict_localisation','ucr_localisation']:assert prior[field]==row['locf'][field]
                    assert row['historical_locf_selected_score_absolute_difference']==abs(row['locf']['selected_score']-prior['selected_score'])
                else:assert row['historical_locf_selected_score_absolute_difference'] is None
                peak=clean['clean']['selected_index_zero_based'];k=int(cb[1][peak-train]);p,c,s=map(int,legacy.LATTICE[k-1:k+2]);indices=[peak-s+p,peak-s+c,peak]
                assert row['clean_winning_triplet_under_mask']==dict(component=k,indices=indices,missing=[bool(mask[i]) for i in indices],contains_imputed_value=bool(mask[indices].any()))
                assert row['clean_winning_index_still_scoreable']==bool(np.isfinite(actual[0][peak-train]))
                stats=summary[phase][name];l=row['locf']['ucr_localisation'];o=row['observed_triplet']['ucr_localisation'];cl=clean['clean']['ucr_localisation']
                stats.update(n=1,locf=int(l),observed=int(o),strict_locf=int(row['locf']['strict_localisation']),strict_observed=int(row['observed_triplet']['strict_localisation']),
                    gain=int(o and not l),loss=int(l and not o),clean_success_lost_by_locf=int(cl and not l),clean_success_recovered=int(cl and not l and o),
                    abstentions=int(row['observed_triplet']['abstained']),locf_imputed_winner=int(row['locf_winning_triplet']['contains_imputed_value']),
                    failed_locf_imputed_winner=int(not l and row['locf_winning_triplet']['contains_imputed_value']),locf_failures=int(not l),
                    coverage_sum=row['observed_triplet']['scoreable_fraction'],missing_fraction_sum=row['missing_fraction'])
                cases+=1
    expected={'clean.json'}|{phase+'-r'+str(rep).zfill(3)+'.json' for phase,n in [('historical',5),('new_masks',32)] for rep in range(n)}
    assert set(hashes)==expected
    return dict(dataset_id=dataset,family_key=record['family_key'],clean=int(clean['clean']['ucr_localisation']),verified_mask_sets=cases,
                per_scenario={p:{s:dict(c) for s,c in d.items()} for p,d in summary.items()},source_hashes=hashes)


def statistics(audits,cfg):
    families=sorted({r['family_key'] for r in audits});assert len(families)==46
    rng=np.random.default_rng(np.random.SeedSequence(cfg['bootstrap_seed_sequence']));indices=rng.integers(0,46,size=(cfg['bootstrap_draws'],46))
    result={}
    for phase in ['historical','new_masks']:
        names=cfg['historical_scenarios'] if phase=='historical' else cfg['new_scenarios'];result[phase]={}
        for name in names:
            family_rows=[];totals=collections.Counter()
            for family in families:
                records=[r for r in audits if r['family_key']==family];rates=[]
                for r in records:
                    c=r['per_scenario'][phase][name];totals.update(c);rates.append([r['clean'],c['locf']/c['n'],c['observed']/c['n']])
                mean=np.mean(rates,axis=0);family_rows.append(dict(family=family,series=len(records),clean=float(mean[0]),locf=float(mean[1]),observed=float(mean[2])))
            matrix=np.array([[r[k] for k in ['clean','locf','observed']] for r in family_rows]);contrasts={}
            for label,j in [('observed_minus_locf',1),('observed_minus_clean',0)]:
                difference=matrix[:,2]-matrix[:,j];estimate=float(difference.mean());samples=difference[indices].mean(axis=1)
                contrasts[label]=dict(estimate=estimate,percentile_95_interval=np.quantile(samples,[.025,.975]).tolist(),
                    centered_bootstrap_two_sided_p=float((1+np.count_nonzero(np.abs(samples-estimate)>=abs(estimate)))/(len(samples)+1)))
            result[phase][name]=dict(family_macro=dict(zip(['clean','locf','observed'],matrix.mean(axis=0).tolist())),
                series_macro_observed=float(np.mean([r['per_scenario'][phase][name]['observed']/r['per_scenario'][phase][name]['n'] for r in audits])),
                contrasts=contrasts,noninferior_to_clean=bool(contrasts['observed_minus_clean']['percentile_95_interval'][0]>-.05),
                totals=dict(totals),mean_scoreable_fraction=totals['coverage_sum']/totals['n'],family_detail=family_rows)
    names=cfg['new_scenarios'];order=sorted(range(6),key=lambda i:result['new_masks'][names[i]]['contrasts']['observed_minus_locf']['centered_bootstrap_two_sided_p']);previous=0.
    for rank,i in enumerate(order):
        c=result['new_masks'][names[i]]['contrasts']['observed_minus_locf'];previous=max(previous,min(1.,(6-rank)*c['centered_bootstrap_two_sided_p']));c['holm_adjusted_p']=previous
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--pack',required=True);p.add_argument('--cache',required=True);p.add_argument('--campaign',required=True)
    p.add_argument('--summary',required=True);p.add_argument('--workers',type=int,default=16);p.add_argument('--output',required=True)
    a=p.parse_args();assert np.__version__=='2.3.5';pack=pathlib.Path(a.pack);out=pathlib.Path(a.output);assert not out.exists()
    for line in (pack/'inputs.sha256').read_text().splitlines():
        h,n=line.split('  ',1);assert sha(pack/n)==h
    cfg=json.loads((pack/'config.json').read_text());summary=read(a.summary)
    assert summary['status']=='COMPLETE' and not summary['pilot'] and summary['series']==250 and summary['new_replicates']==32
    assert summary['input_manifest_sha256']==sha(pack/'inputs.sha256')
    assert sha(pathlib.Path(a.cache)/'cache-manifest.json')==cfg['cache_manifest_sha256']
    series=json.loads((pack/'canonical.json').read_text())['series'];start=time.monotonic()
    with concurrent.futures.ProcessPoolExecutor(max_workers=a.workers) as pool:
        audits=[]
        for result in pool.map(verify_one,[(vars(a),r) for r in series],chunksize=1):
            audits.append(result)
            if len(audits)%25==0:print(json.dumps(dict(verified_series=len(audits))),flush=True)
    assert len(audits)==250 and sum(r['verified_mask_sets'] for r in audits)==51750
    result=dict(schema='qgita-missingness-full-audit/v1',status='PASS',verified_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                elapsed_seconds=time.monotonic()-start,source_sha256=sha(__file__),input_manifest_sha256=sha(pack/'inputs.sha256'),
                source_series=250,source_families=46,verified_mask_sets=51750,verified_candidate_control_outcomes=103500,
                independent_full_timeline_recomputation=True,all_historical_locf_decisions_match=True,
                analysis=statistics(audits,cfg),per_series_audits=audits,
                interpretation='Method-development evidence on the known UCR panel. New masks are not independent new source families. Original negative results remain unchanged.')
    out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(status='PASS',verified_mask_sets=51750,analysis={p:{s:{k:v for k,v in r.items() if k in ['family_macro','contrasts','noninferior_to_clean','mean_scoreable_fraction']} for s,r in d.items()} for p,d in result['analysis'].items()}),indent=2),flush=True)

if __name__=='__main__':main()
