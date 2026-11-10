from pathlib import Path
import datetime, hashlib, json, math, statistics
import numpy as np

root=Path('outputs/tandem-repair-pilot-6506293')
cfg=json.loads(Path('work/tandem-repair-v1/config.json').read_text())
normal=statistics.NormalDist();z=normal.inv_cdf(.985)

def white(x,model,scale):
    if model==0:return x.copy()
    if model==1:
        rho=.9**(1/scale)
        return np.concatenate([x[:,:1],(x[:,1:]-rho*x[:,:-1])/math.sqrt(1-rho*rho)],axis=1)
    # Independent scalar Kalman covariance update and vector channel innovations.
    a,b=.97**(1/scale),.45**(1/scale)
    h,j=.65/math.sqrt(.65**2+.35**2),.35/math.sqrt(.65**2+.35**2)
    p,q,r=1.,0.,1.;m=np.zeros(x.shape[0]);n=m.copy();out=np.empty_like(x)
    for i in range(x.shape[1]):
        v=h*h*p+2*h*j*q+j*j*r;k=(p*h+q*j)/v;l=(q*h+r*j)/v
        err=x[:,i]-h*m-j*n;out[:,i]=err/math.sqrt(v)
        m=a*(m+k*err);n=b*(n+l*err)
        p,q,r=a*a*(p-k*(h*p+j*q))+1-a*a,a*b*(q-k*(h*q+j*r)),b*b*(r-l*(h*q+j*r))+1-b*b
    return out

checks=[];max_errors={};fields=None
def check(key,actual,expected,rtol=2e-9,atol=2e-10):
    np.testing.assert_allclose(actual,expected,rtol=rtol,atol=atol,err_msg=key)
    max_errors[key]=max(max_errors.get(key,0.),float(np.max(np.abs(actual-expected))))

for stage in range(7):
 for shard in cfg['pilot_shards']:
    stem=f'pilot-s{stage:02d}-c{shard:02d}';receipt=json.loads((root/(stem+'.json')).read_text());path=root/(stem+'.npz')
    assert hashlib.sha256(path.read_bytes()).hexdigest()==receipt['array_sha256']
    assert receipt['stage']==cfg['stages'][stage]
    with np.load(path,allow_pickle=False) as data:d={k:data[k] for k in data.files}
    if fields is None:fields=set(d)
    assert fields==set(d)
    assert all(np.isfinite(v).all() for v in d.values())
    ids=shard*10_000_000+np.arange(512)
    for k,v in dict(trial_id=ids,eta=np.array([0,.002,.005,.01,.02,.05,.1,.2])[ids%8],snr_db=np.array([-10,0,10,20])[(ids//8)%4],noise_model=(ids//32)%3,operator=(ids//96)%3,truth_model=(ids//288)%3,null_split=(ids//864)%2).items():assert np.array_equal(d[k],v),k
    assert all(len(v)==512 for k,v in d.items() if not k.startswith('sample_'))
    if stage>=3:assert np.all(d['selected_weight_after']==0)
    if stage==0:check('legacy_record_rms',d['noise_rms'],np.ones(512),atol=2e-14,rtol=0)
    if stage==0:assert np.all(d['uniform_null_oracle_power_bound']==-1)
    else:
        bound=np.array([normal.cdf(float(x)-z) for x in d['distance_from_nearest_phase']]);check('gaussian_bound',d['uniform_null_oracle_power_bound'],bound,rtol=0,atol=1e-14)
        assert np.all(d['distance_from_nearest_phase']<=d['distance_from_delay']+1e-10)
    cut=cfg['stages'][stage]['steps']//2;scale=cfg['stages'][stage]['fs']/1000
    for row in range(2):
        sig=d['sample_sigma'][row];rr=d['sample_residual'][row]/sig;ee=d['sample_echo'][row]/sig;pp=d['sample_phase'][row]/sig
        R,E,P=white(np.array([rr[cut:],ee[cut:],pp[cut:]]),int(d['noise_model'][row]),scale)
        en=E@E;pn=P@P;er=E@R;pr=P@R;ep=E@P
        a=np.clip(er/en,0,.2);b=np.clip(pr/pn,0,.2);score=2*a*er-a*a*en-(2*b*pr-b*b*pn)
        for k,v in dict(conditional_glrt=score,white_template_norm=en,phase_template_norm=pn,template_inner_product=ep).items():check(k,np.array([d[k][row]]),np.array([v]))
        def corr(x,y):
            x=x-x.mean();y=y-y.mean();return (x@y)/math.sqrt((x@x)*(y@y))
        shift=min(cut//3,3*receipt['tau_steps']+17*int(scale))
        c=corr(rr[cut:],ee[cut:]);s=abs(corr(rr[cut:],np.roll(ee[cut:],shift)))
        check('D0',d['discriminant'][row:row+1],np.array([c-s]),rtol=1e-8,atol=1e-12)
    checks.append(dict(stage=stage,shard=shard,trials=512,saved_channels_recomputed=2,passed=True))
result=dict(passed=True,verified_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),arrays=len(checks),trials=len(checks)*512,fields=sorted(fields),saved_channel_records=56,checks=checks,max_absolute_errors=max_errors,archive_sha256=hashlib.sha256((root/'pilot.tar.gz').read_bytes()).hexdigest(),boundary='All saved trial fields and source identities checked; independent scalar Kalman and score recalculation on 56 saved channels. This does not regenerate all latent trajectories.')
(root/'local-audit.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
print(json.dumps({k:v for k,v in result.items() if k not in ['checks','fields']},indent=2))
