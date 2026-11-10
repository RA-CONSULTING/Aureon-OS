"""Frozen stage comparisons from eligible scalar records; no model imports."""
import itertools
import numpy as np

METHODS={'D0':'discriminant','sphere_diagnostic':'sphere_score','conditional_glrt':'conditional_glrt'}
ETA=np.array([0,.002,.005,.01,.02,.05,.1,.2]);SNR=np.array([-10.,0.,10.,20.])

def ratio(hit,mask):
    n=int(mask.sum());k=int(np.count_nonzero(hit&mask))
    return dict(n=n,hits=k,rate=k/n if n else None)

def masks(d):
    eligible=~(np.isin(d['cell'],[0,15,16,31])&(d['trial_id']%10_000_000<512))
    positive=(d['truth_model']==2)&(d['eta']>0)
    return dict(eligible=eligible,positive=eligible&positive,calibration=eligible&~positive&(d['null_split']==0),evaluation=eligible&~positive&(d['null_split']==1),target=eligible&positive&(d['eta']>=.05)&(d['snr_db']>=0),weak=eligible&positive&(d['eta']==.05)&(d['snr_db']==0))

def stage_analysis(d,stage):
    m=masks(d);result=dict(stage=stage,total_records=len(d['trial_id']),eligible=int(m['eligible'].sum()),excluded_pilot_overlap=int((~m['eligible']).sum()),denominators={k:int(v.sum()) for k,v in m.items()},methods={})
    assert result['eligible']==329728 and result['excluded_pilot_overlap']==2048
    result['correct_template_beats_shifted']=ratio(d['corr_true']>d['corr_shift'],m['positive'])
    for method,key in METHODS.items():
        score=d[key];threshold=np.full(len(score),np.nan);threshold_rows=[]
        for noise,op,snr in itertools.product(range(3),range(3),SNR):
            group=(d['noise_model']==noise)&(d['operator']==op)&(d['snr_db']==snr)
            cal=m['calibration']&group;assert cal.sum()>=100
            value=float(np.quantile(score[cal],.99));threshold[group]=value
            threshold_rows.append(dict(noise=noise,operator=op,snr_db=float(snr),calibration_n=int(cal.sum()),threshold=value))
        assert np.isfinite(threshold).all();hit=score>threshold
        metric={k:ratio(hit,m[k]) for k in ['evaluation','target','weak','positive']}
        metric['thresholds']=threshold_rows;metric['strata']=[];metric['cells']=[]
        metric['detector_gate_pass']=bool(metric['evaluation']['rate']<=.015 and metric['target']['rate']>=.8 and result['correct_template_beats_shifted']['rate']>.5)
        for noise,op,snr in itertools.product(range(3),range(3),SNR):
            group=(d['noise_model']==noise)&(d['operator']==op)&(d['snr_db']==snr)
            row=dict(noise=noise,operator=op,snr_db=float(snr),fpr=ratio(hit,m['evaluation']&group),target_power=ratio(hit,m['target']&group))
            row['null_truth_fpr']={str(truth):ratio(hit,m['evaluation']&group&(d['truth_model']==truth)) for truth in range(3)}
            row['eta_power']={str(float(eta)):ratio(hit,m['positive']&group&(d['eta']==eta)) for eta in ETA[1:]}
            metric['strata'].append(row)
        for cell in range(32):
            metric['cells'].append(dict(cell=cell,**{k:ratio(hit,m[k]&(d['cell']==cell)) for k in ['evaluation','target','weak','positive']}))
        result['methods'][method]=metric
    result['diagnostics']=dict(noise_rms_mean=float(d['noise_rms'][m['eligible']].mean()),noise_rms_std=float(d['noise_rms'][m['eligible']].std()),selected_weight_before_mean=float(d['selected_weight_before'][m['eligible']].mean()),selected_weight_after_max=float(d['selected_weight_after'].max()),effective_branches_mean=float(d['effective_branches'][m['eligible']].mean()),sphere_h1_error_positive_median=float(np.median(d['sphere_h1_error'][m['positive']])),sphere_null_error_eval_median=float(np.median(d['sphere_null_error'][m['evaluation']])))
    result['gaussian_bounds_valid']=stage['noise']=='stationary_gaussian'
    if result['gaussian_bounds_valid']:
        bounds=[]
        for noise,op,snr,eta in itertools.product(range(3),range(3),SNR,ETA[1:]):
            group=m['positive']&(d['noise_model']==noise)&(d['operator']==op)&(d['snr_db']==snr)&(d['eta']==eta);assert group.any()
            row=dict(noise=noise,operator=op,snr_db=float(snr),eta=float(eta),n=int(group.sum()))
            for key in ['uniform_null_oracle_power_bound','delay_only_oracle_power','distance_from_delay','distance_from_nearest_phase','template_correlation']:
                v=d[key][group];row[key]=dict(mean=float(v.mean()),min=float(v.min()),max=float(v.max()),p10=float(np.quantile(v,.1)),median=float(np.median(v)),p90=float(np.quantile(v,.9)))
            bounds.append(row)
        result['bound_strata']=bounds
        result['bound_summary']={name:{key:float(d[key][m[name]].mean()) for key in ['uniform_null_oracle_power_bound','delay_only_oracle_power']} for name in ['target','weak','positive']}
    return result

def comparisons(stages,repetitions=20000,seed=49120926):
    rng=np.random.default_rng(seed);weights=rng.multinomial(32,np.full(32,1/32),size=repetitions)
    signs=rng.choice([-1,1],size=(repetitions,32));rows=[]
    for si in range(1,7):
        a=stages[si-1]['methods']['conditional_glrt']['cells'];b=stages[si]['methods']['conditional_glrt']['cells']
        row=dict(from_stage=si-1,to_stage=si,method='conditional_glrt')
        for metric in ['target','evaluation']:
            ka=np.array([c[metric]['hits'] for c in a]);na=np.array([c[metric]['n'] for c in a]);kb=np.array([c[metric]['hits'] for c in b]);nb=np.array([c[metric]['n'] for c in b]);assert np.all(na>0)&np.all(nb>0)
            delta=(weights@kb)/(weights@nb)-(weights@ka)/(weights@na)
            row[metric]=dict(pooled_difference=float(kb.sum()/nb.sum()-ka.sum()/na.sum()),paired_cell_bootstrap_ci95=np.quantile(delta,[.025,.975]).tolist())
            if metric=='target':
                diff=kb/nb-ka/na;observed=abs(diff.mean());simulated=np.abs(signs@diff/32)
                row['target']['cell_mean_difference']=float(diff.mean());row['power_sign_flip_p']=(1+int(np.count_nonzero(simulated>=observed-1e-15)))/(repetitions+1)
        rows.append(row)
    order=np.argsort([r['power_sign_flip_p'] for r in rows]);last=0
    for rank,index in enumerate(order):
        last=max(last,min(1.,rows[index]['power_sign_flip_p']*(6-rank)));rows[index]['power_sign_flip_p_holm']=last
    return dict(repetitions=repetitions,seed=seed,unit='configuration cell; paired stages; conditional on fixed 32-cell panel',bootstrap='Resample whole configuration cells; recompute pooled rates using paired counts. Thresholds remain the declared fitted calibration thresholds. Intervals do not include threshold refitting or independently sampled physical systems.',rows=rows)

def analyse(all_data,cfg):
    stages=[stage_analysis(d,s) for d,s in zip(all_data,cfg['stages'])]
    weights=np.random.default_rng(cfg['inference_seed']).multinomial(32,np.full(32,1/32),size=cfg['bootstrap_repetitions'])
    for stage in stages:
        for method in stage['methods'].values():
            for metric in ['evaluation','target','weak','positive']:
                k=np.array([c[metric]['hits'] for c in method['cells']]);n=np.array([c[metric]['n'] for c in method['cells']])
                rate=(weights@k)/(weights@n)
                method[metric]['configuration_cell_bootstrap_ci95']=np.quantile(rate,[.025,.975]).tolist()
    return dict(schema='tandem-repair-analysis/v1',claim_class='computational_simulation',stages=stages,comparisons=comparisons(stages,cfg['bootstrap_repetitions'],cfg['inference_seed']),bound_boundary='Conditional Gaussian simple-versus-simple bounds require false-positive control uniformly at every conditional null mean, including the nearest phase alternative. They do not bound a detector controlling only average-mixture FPR. Exact baseline, scale, noise family and templates are privileged simulated inputs.',historical_boundary='Old exact-RMS noise is not Gaussian. Its old detector gate failures do not prove mathematical nonidentifiability. Stage 0 retains that distribution as a control; no Gaussian bound is applied there.')
