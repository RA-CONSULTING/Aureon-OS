"""Independent NumPy numerical and per-example ledger verification."""
from pathlib import Path
import hashlib,json,math
import numpy as np


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def metrics(s,y,threshold):
    y=np.asarray(y,dtype=bool);p=np.sort(s[y]);n=np.sort(s[~y]);n1=len(p);n0=len(n)
    assert n1 and n0 and np.isfinite(s).all()
    auc=(np.searchsorted(n,p,side='left').sum()+np.searchsorted(n,p,side='right').sum())/(2*n1*n0)
    v,inv,cnt=np.unique(s,return_inverse=True,return_counts=True)
    pos=np.bincount(inv,weights=y,minlength=len(v))[::-1]
    precision=np.cumsum(pos)/np.cumsum(cnt[::-1]);ap=(precision*pos).sum()/n1
    tp=int((s[y]>threshold).sum());fp=int((s[~y]>threshold).sum())
    return dict(auroc=float(auc),average_precision=float(ap),positives=n1,negatives=n0,
                true_positives=tp,false_positives=fp,tpr=tp/n1,fpr=fp/n0,threshold=float(threshold))


def sample_scores(z,lane,ops,order):
    I=z[lane+'_audit_images'];T=z[lane+'_audit_template'];b,h,w=I.shape;n=h*w
    F=np.fft.fft2(I,norm='ortho');power=np.abs(F)**2
    bins=ops['bins'];count=np.bincount(bins)
    P0=np.stack([np.bincount(bins,weights=p.ravel(),minlength=len(count))/np.maximum(count,1) for p in power])
    floor=power.reshape(b,-1)[:,1:].mean(1)*1e-6
    P=np.maximum(P0,floor[:,None])[:,bins].reshape(I.shape);P[:,0,0]=1
    transfer=ops['transfers'];response=np.fft.ifft2(F[:,None]*transfer[None],norm='ortho').real
    mag=np.abs(response);roi=ops['roi'].astype(bool)
    result={}
    def maximum(m,mask=False):
        if mask:m=np.where(roi,m,-np.inf)
        k=np.argmax(m.reshape(b,-1),axis=1)
        return np.max(m.reshape(b,-1),axis=1),k//w,k%w
    for j,name in enumerate(order[:7]):result[name]=maximum(mag[:,j])
    phi=mag[:,0]
    white=np.abs(np.fft.ifft2(F[:,None]*transfer[[0,6]][None]/np.sqrt(P[:,None]),norm='ortho').real)
    white/=np.sqrt(np.sum(transfer[[0,6]]**2,axis=(1,2))/n)[None,:,None,None]
    def bankmap(bank):
        norm=np.sqrt(np.sum(np.abs(bank)[None]**2/P[:,None],axis=(2,3)))
        maps=np.fft.ifft2(F[:,None]*bank[None]/P[:,None],norm='ortho').real*np.sqrt(n)/norm[:,:,None,None]
        return np.abs(maps).max(1)
    gauss=bankmap(ops['gauss']);ring=bankmap(ops['ring'])
    for name,m in [('phi2_roi',phi),('whitened_phi2_roi',white[:,0]),('whitened_log_roi',white[:,1]),('matched_gaussian_roi',gauss),('matched_ring_roi',ring)]:result[name]=maximum(m,True)
    iy=np.rint(z[lane+'_cy'][:b]).astype(int).clip(0,h-1);ix=np.rint(z[lane+'_cx'][:b]).astype(int).clip(0,w-1)
    for name,m in [('truth_location_phi2',phi),('truth_location_whitened_phi2',white[:,0]),('truth_location_matched_ring',ring)]:result[name]=(m[np.arange(b),iy,ix],iy,ix)
    TF=np.fft.fft2(T,norm='ortho')
    exact=np.abs(np.sum(F*TF.conj()/P,axis=(1,2)).real)/np.sqrt(np.sum(np.abs(TF)**2/P,axis=(1,2)))
    result['truth_shape_location_matched']=(exact,iy,ix)
    errors=[]
    for name,(s,y,x) in result.items():
        j=order.index(name);old=z[lane+'_scores'][:b,j]
        np.testing.assert_allclose(s,old,rtol=5e-10,atol=5e-10)
        assert np.array_equal(y,z[lane+'_found_y'][:b,j]) and np.array_equal(x,z[lane+'_found_x'][:b,j])
        errors.append(float(np.max(np.abs(s-old))))
    return dict(examples=b,methods=len(result),max_absolute_score_difference=max(errors))


def verify_operators(ops,h):
    # Independently reconstruct physical template shapes and support.
    coords=np.arange(h,dtype=float);coords[coords>=h/2]-=h
    dist=np.hypot(coords[:,None],coords[None,:]);ring=[];gauss=[]
    for sig in [2.,3.75,5.5]:
        core=np.exp(-.5*(dist/sig)**2);gauss.append(core-core.mean())
        for ratio in [2.,3.,4.]:
            for width in [.7,1.25,1.8]:
                t=core+.45*np.exp(-.5*((dist-sig*ratio)/width)**2);ring.append(t-t.mean())
    np.testing.assert_allclose(ops['ring'],np.fft.fft2(np.stack(ring),norm='ortho').conj(),rtol=2e-10,atol=2e-12)
    np.testing.assert_allclose(ops['gauss'],np.fft.fft2(np.stack(gauss),norm='ortho').conj(),rtol=2e-10,atol=2e-12)
    # Floating-point ffreq can lie either side of an exact integer boundary.
    radial=np.hypot(coords[:,None],coords[None,:]).flatten()
    assert np.all(ops['bins']<=radial+1e-12) and np.all(ops['bins']+1>=radial-1e-12)
    margin=max(8,h//5);roi=np.zeros((h,h),bool);roi[margin:h-margin+1,margin:h-margin+1]=True
    assert np.array_equal(roi,ops['roi'])


def verify_record(path,operators,manifest):
    path=Path(path);r=json.loads(path.read_text());zpath=path.with_suffix('.npz')
    assert r['arrays_sha256']==sha(zpath) and r['input_manifest_sha256']==manifest
    z=np.load(zpath,allow_pickle=False);order=r['method_order'];n=r['samples'];nc=r['calibration_samples']
    assert len(order)==20 and len(z['test_scores'])==n and len(z['cal_scores'])==nc
    assert np.isfinite(z['test_scores']).all() and np.isfinite(z['cal_scores']).all()
    assert not z['cal_labels'].any()
    assert np.array_equal(z['test_nuisance'],np.arange(n)%5) and np.array_equal(z['cal_nuisance'],np.arange(nc)%5)
    grid=r['grid'];h=grid['rows'];w=grid['cols'];cy=z['test_cy'];cx=z['test_cx']
    assert np.all((cy>=max(8,h//5))&(cy<h-max(8,h//5)))
    assert np.all((cx>=max(8,w//5))&(cx<w-max(8,w//5)))
    assert np.all((z['test_sigma']>=2)&(z['test_sigma']<=5.5))
    assert np.all((z['test_amplitude']>=.45)&(z['test_amplitude']<=2))
    for lane in ['cal','test']:
        err=np.hypot(z[lane+'_found_y']-z[lane+'_cy'][:,None],z[lane+'_found_x']-z[lane+'_cx'][:,None])
        np.testing.assert_allclose(err,z[lane+'_error'],rtol=2e-15,atol=2e-14)
    th=np.quantile(z['cal_scores'],.95,axis=0);maxdelta=0
    for j,name in enumerate(order):
        saved=r['methods'][name];actual=metrics(z['test_scores'][:,j],z['test_labels'],saved['threshold'])
        assert abs(th[j]-saved['threshold'])<1e-11
        for key,v in actual.items():
            delta=abs(saved[key]-v);maxdelta=max(maxdelta,delta);assert delta<2e-14,(path.name,name,key,delta)
        truth=z['test_labels'];err=z['test_error'][truth,j]
        assert saved['median_localisation_error_pixels']==float(np.median(err))
        assert saved['p90_localisation_error_pixels']==float(np.quantile(err,.9))
        assert saved['localised_within_3px_fraction']==float(np.mean(err<=3))
        assert saved['detected_and_localised_within_3px_fraction']==float(np.mean((err<=3)&(z['test_scores'][truth,j]>saved['threshold'])))
        for k in range(5):
            mask=z['test_nuisance']==k;m=metrics(z['test_scores'][mask,j],truth[mask],saved['threshold'])
            for key,v in m.items():assert abs(saved['strata'][str(k)][key]-v)<2e-14
    sample=[sample_scores(z,lane,operators,order) for lane in ['cal','test']]
    return dict(file=path.name,arrays_sha256=r['arrays_sha256'],result_sha256=sha(path),test_examples=n,calibration_examples=nc,max_metric_difference=maxdelta,sample_scores=sample)


CONTRASTS=[('phi2_roi','phi2'),('whitened_phi2_roi','phi2_roi'),('whitened_log_roi','whitened_phi2_roi'),('matched_ring_roi','whitened_phi2_roi')]


def analyse(records,reps=20000):
    records=sorted(records,key=lambda r:r['shard']);assert [r['shard'] for r in records]==list(range(128))
    names=records[0]['method_order'];result={};tests=[]
    for gi,group in [(0,[r for r in records if r['grid_index']==0]),(1,[r for r in records if r['grid_index']==1]),(2,records)]:
        count=len(group);rng=np.random.default_rng(np.random.SeedSequence([29120926,gi]))
        ix=rng.integers(0,count,size=(reps,count))
        signs=rng.choice(np.array([-1.,1.]),size=(reps,count))
        summary={}
        for name in names:
            summary[name]={}
            for key in ['auroc','average_precision','tpr','fpr','median_localisation_error_pixels','localised_within_3px_fraction','detected_and_localised_within_3px_fraction']:
                v=np.array([r['methods'][name][key] for r in group]);draw=v[ix].mean(1)
                summary[name][key]=dict(mean=float(v.mean()),ci95=np.quantile(draw,[.025,.975]).tolist())
            summary[name]['strata_auroc']={str(k):float(np.mean([r['methods'][name]['strata'][str(k)]['auroc'] for r in group])) for k in range(5)}
        comparisons=[]
        for a,b in CONTRASTS:
            delta=np.array([r['methods'][a]['auroc']-r['methods'][b]['auroc'] for r in group])
            estimate=float(delta.mean());ci=np.quantile(delta[ix].mean(1),[.025,.975]).tolist()
            pv=(1+int(np.sum(np.abs((delta*signs).mean(1))>=abs(estimate))))/(reps+1)
            c=dict(method=a,control=b,auroc_difference=estimate,ci95=ci,two_sided_sign_flip_p=pv)
            comparisons.append(c)
            if gi<2:tests.append(c)
        result[str(gi)]=dict(shards=count,test_examples=sum(r['samples'] for r in group),methods=summary,comparisons=comparisons)
    ordered=sorted(tests,key=lambda x:x['two_sided_sign_flip_p']);prev=0
    for i,t in enumerate(ordered):
        prev=max(prev,min(1,(len(ordered)-i)*t['two_sided_sign_flip_p']));t['holm_eight_adjusted_p']=prev
    return dict(schema='lidar-analysis/v1',groups=result,bootstrap_repetitions=reps,inference_seed=29120926,
                limits='Synthetic generator only. Truth diagnostics are privileged and not upper bounds. Group 2 pixel localization summaries mix scales and must not be interpreted or reported as physical errors.')
