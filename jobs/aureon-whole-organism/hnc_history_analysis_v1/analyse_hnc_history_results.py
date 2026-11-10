"""Apply the frozen finite-time screen and descriptive last-quarter trend to audited grids."""
import argparse, collections, datetime, hashlib, json, pathlib, sys
import numpy as np


def sha(p):
    h=hashlib.sha256()
    with pathlib.Path(p).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def trends(x,y):
    x=np.asarray(x,dtype=float);y=np.asarray(y,dtype=float)
    assert len(x)==8 and y.shape[0]==8 and np.all(np.diff(x)>0)
    centred=x-x.mean();slope=np.sum(centred[:,None,None,None]*(y-y.mean(axis=0)),axis=0)/np.sum(centred**2)
    residual=y-(y.mean(axis=0)+centred[:,None,None,None]*slope)
    rms=np.sqrt(np.mean(residual**2,axis=0));change=np.abs(slope)*(x[-1]-x[0])
    flag=(np.abs(slope)>1e-8)&(change>np.maximum(1.,10*rms))&np.all(np.isfinite(y),axis=0)
    return slope,rms,flag


def main():
    p=argparse.ArgumentParser();p.add_argument('--pack',required=True);p.add_argument('--campaign',required=True)
    p.add_argument('--audit',required=True);p.add_argument('--original',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();pack=pathlib.Path(a.pack);root=pathlib.Path(a.campaign);out=pathlib.Path(a.output);assert not out.exists()
    audit=json.loads(pathlib.Path(a.audit).read_text());cfg=json.loads((pack/'config.json').read_text())
    assert audit['status']=='PASS' and audit['stop']==cfg['horizon']==33554432
    assert audit['input_manifest_sha256']==sha(pack/'inputs.sha256')
    # Cross-check the vector implementation against the frozen one-series definition on synthetic inputs.
    sys.path.insert(0,str(pack));from trend import temporal_trend
    times=np.arange(25,33,dtype=float)*cfg['segment_steps']
    rng=np.random.default_rng(20260912);sample=rng.normal(size=(8,1,1,12))
    sample[:,:,:,0]=2+1e-5*times[:,None,None]
    sample[:,:,:,1]=2-1e-5*times[:,None,None]
    sample[:,:,:,2]=1.
    slopes,rms,flags=trends(times,sample)
    for j in range(12):
        expected=temporal_trend(times,sample[:,0,0,j])
        assert bool(flags[0,0,j])==expected['flag']
        assert np.isclose(slopes[0,0,j],expected['slope_per_step'],rtol=1e-13,atol=1e-20)
    summaries=[];totals=[collections.Counter() for _ in cfg['initial_histories']]
    beta_counts=np.zeros((4,len(cfg['betas'])),dtype=np.int64)
    original_comparisons=[];shape=(4,len(cfg['alphas']),len(cfg['betas']))
    for rank in range(128):
        rankdir=root/('rank-'+str(rank).zfill(3));receipts={}
        for rp in rankdir.glob('attempt-*/receipt.json'):
            r=json.loads(rp.read_text());assert r['stop'] not in receipts;receipts[r['stop']]=(r,rp)
        final,fp=receipts[cfg['horizon']];assert sha(fp)==audit['ranks'][rank]['receipt_sha256']
        series=[]
        for step in times.astype(int):
            r,rp=receipts[int(step)];gp=rp.parent/'grid.npz';assert sha(gp)==r['grid_sha256']
            with np.load(gp) as z:series.append(z['mean_history'].copy())
        slopes,rms,flags=trends(times,np.stack(series))
        assert sha(fp.parent/'grid.npz')==final['grid_sha256']
        with np.load(fp.parent/'grid.npz') as z:
            escaped=z['escaped'];valid=z['lyapunov_blocks']>0
            stable=(~escaped)&valid&(z['lyapunov_per_step']<=cfg['finite_time_lyapunov_threshold'])
            flags&=~escaped
            beta_counts+=stable.sum(axis=1)
            for hi,name in enumerate(cfg['initial_histories']):
                count=collections.Counter(trajectories=int(escaped[hi].size),escaped=int(escaped[hi].sum()),
                    finite_time_screen=int(stable[hi].sum()),unescaped_without_valid_blocks=int(((~escaped[hi])&(~valid[hi])).sum()),
                    unescaped_above_lyapunov_threshold=int(((~escaped[hi])&valid[hi]&(~stable[hi])).sum()),
                    descriptive_trend=int(flags[hi].sum()),screen_with_descriptive_trend=int((stable[hi]&flags[hi]).sum()))
                references={}
                for beta in [1.,1.1]:
                    bi=cfg['betas'].index(beta)
                    references[str(beta)]=dict(cases=len(cfg['alphas']),escaped=int(escaped[hi,:,bi].sum()),finite_time_screen=int(stable[hi,:,bi].sum()),
                        descriptive_trend=int(flags[hi,:,bi].sum()),screen_with_descriptive_trend=int((stable[hi,:,bi]&flags[hi,:,bi]).sum()),
                        slope_min=float(slopes[hi,:,bi].min()),slope_max=float(slopes[hi,:,bi].max()))
                totals[hi].update(count)
                summaries.append(dict(rank=rank,task=cfg['tasks'][rank],history=name,counts=dict(count),references=references))
        # Direct zero-history control at the old full horizon; preserve and report any mismatch.
        r,rp=receipts[cfg['preceding_horizon']];assert sha(rp.parent/'grid.npz')==r['grid_sha256']
        olddir=pathlib.Path(a.original)/('rank-'+str(rank).zfill(3));candidates=[]
        for op in olddir.glob('attempt-*/receipt.json'):
            old=json.loads(op.read_text())
            if old['stop']==cfg['preceding_horizon']:candidates.append((old,op))
        assert len(candidates)==1
        old,op=candidates[0];assert sha(op.parent/'grid.npz')==old['grid_sha256']
        assert old['job']=='6498143' and old['task']==cfg['tasks'][rank]
        fields={}
        with np.load(rp.parent/'grid.npz') as nz,np.load(op.parent/'grid.npz') as oz:
            for field in ['max_abs','escaped','first_escape_step','lyapunov_per_step','lyapunov_blocks']:
                fields[field]=dict(bitwise_equal=bool(np.array_equal(nz[field][0],oz[field])),different_values=int(np.count_nonzero(nz[field][0]!=oz[field])))
        original_comparisons.append(dict(rank=rank,fields=fields,old_receipt_sha256=sha(op),new_receipt_sha256=sha(rp)))
    parity=all(v['bitwise_equal'] for r in original_comparisons for v in r['fields'].values())
    result=dict(schema='hnc-history-results/v1',status='PASS' if parity else 'CONTROL_REVIEW_REQUIRED',
        analysed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),audit_sha256=sha(a.audit),analysis_source_sha256=sha(__file__),
        reference_beta=1.,horizon=cfg['horizon'],trajectories=25214464,
        history_totals={name:dict(totals[i]) for i,name in enumerate(cfg['initial_histories'])},
        beta_values=cfg['betas'],finite_time_screen_counts_by_history_and_beta=beta_counts.tolist(),cases_per_beta_and_history=15488,
        per_rank_history=summaries,original_zero_history_at_previous_horizon=original_comparisons,
        previous_horizon_zero_control_bitwise=parity,trend_rule='Frozen PROTOCOL.md last eight regular endpoints; slope/change/residual thresholds',
        analysis_self_check='PASS',interpretation='Finite-time model observations across four histories. The finite-time screen can coexist with secular drift. No infinite-time, physical or historical validation.')
    out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['status','trajectories','horizon','history_totals','previous_horizon_zero_control_bitwise']},indent=2))

if __name__=='__main__':main()
