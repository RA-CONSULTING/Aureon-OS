"""Explicit synthetic observation-model repairs and conditional diagnostics."""
from pathlib import Path
import ctypes,functools,hashlib,inspect,json,math,statistics,subprocess,fcntl,os
import numpy as np
import torch
import tandem_10_9_1_falsification as original

ROOT=Path(__file__).resolve().parent
CFG=json.loads((ROOT/'config.json').read_text())
assert len(CFG['stages'])==7 and len({s['name'] for s in CFG['stages']})==7
OLD_SHA='5ff9000846bdeaf65a2c93f14463200442fe9cdadced1e4db3c6b6f7709567d2'
NORMAL=statistics.NormalDist();FALSE_POSITIVE=.015;Z_ALPHA=NORMAL.inv_cdf(1-FALSE_POSITIVE)


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def population_noise(batch,steps,model_ids,generator,sampling_scale=1.):
    device=model_ids.device;dtype=torch.float64
    white=torch.randn((batch,steps),generator=generator,device=device,dtype=dtype)
    ar09=original.ar_noise(torch.randn((batch,steps),generator=generator,device=device,dtype=dtype),.9**(1/sampling_scale))
    slow=original.ar_noise(torch.randn((batch,steps),generator=generator,device=device,dtype=dtype),.97**(1/sampling_scale))
    fast=original.ar_noise(torch.randn((batch,steps),generator=generator,device=device,dtype=dtype),.45**(1/sampling_scale))
    mix=(.65*slow+.35*fast)/math.sqrt(.65**2+.35**2)
    return torch.where((model_ids==2)[:,None],mix,torch.where((model_ids==1)[:,None],ar09,white))


def generator_for(stage):
    assert sha(ROOT/'tandem_10_9_1_falsification.py')==OLD_SHA
    scope=dict(__name__='frozen_tandem_clone',__file__=str(ROOT/'tandem_10_9_1_falsification.py'))
    exec(compile((ROOT/'tandem_10_9_1_falsification.py').read_text(),'frozen_tandem','exec'),scope)
    scale=int(stage['fs']/1000);assert stage['fs']==1000*scale
    scope.update(BETA=stage['beta'],FS=stage['fs'],EXCLUDE_SELECTED=stage['exclude_selected'],SAMPLING_SCALE=scale)
    if stage['noise']=='stationary_gaussian':scope['make_unit_noise']=functools.partial(population_noise,sampling_scale=scale)
    src=inspect.getsource(original.run_batch)
    marker='    echo_weights = torch.softmax(standardized, dim=1)'
    assert src.count(marker)==1
    src=src.replace(marker,marker+'''
    selected_weight_before = echo_weights.gather(1, selected_index[:, None]).flatten().clone()
    if EXCLUDE_SELECTED:
        echo_weights = echo_weights.clone()
        echo_weights.scatter_(1, selected_index[:, None], 0.0)
        echo_weights /= echo_weights.sum(dim=1, keepdim=True)
    selected_weight_after = echo_weights.gather(1, selected_index[:, None]).flatten().clone()
''')
    for before,after in [('lag_span = max(1, tau // 4)','lag_span = max(1, (tau // SAMPLING_SCALE) // 4)'),
                         ('lag = tau + (branch % lag_span)','lag = tau + (branch % lag_span) * SAMPLING_SCALE'),
                         ('max(train_start, tau + lag_span)','max(train_start, tau + lag_span * SAMPLING_SCALE)'),
                         ('3 * tau + 17)','3 * tau + 17 * SAMPLING_SCALE)')]:
        assert src.count(before)==1;src=src.replace(before,after)
    assert src.count('    return {')==1
    src=src.replace('    return {','    result = {')
    src+='''
    metadata = dict(residual=residual.detach().cpu().numpy(),
                    echo=echo_scaled.detach().cpu().numpy(),phase=phase_mix_scaled.detach().cpu().numpy(),
                    sigma=noise_sigma.detach().cpu().numpy(),
                    noise_rms=unit_noise.square().mean(1).sqrt().detach().cpu().numpy(),
                    noise_mean=unit_noise.mean(1).detach().cpu().numpy(),
                    selected_weight_before=selected_weight_before.detach().cpu().numpy(),
                    selected_weight_after=selected_weight_after.detach().cpu().numpy(),
                    effective_branches=(1/echo_weights.square().sum(1)).detach().cpu().numpy())
    return result, metadata
'''
    exec(compile(src,'amended_tandem_generator','exec'),scope)
    return scope['run_batch']


@functools.lru_cache(None)
def coefficients(length,sampling_scale=1.):
    slow=.97**(1/sampling_scale);fast=.45**(1/sampling_scale)
    a=np.diag([slow,fast]);q=np.diag([1-slow**2,1-fast**2]);p=np.eye(2)
    h=np.array([.65,.35])/math.sqrt(.65**2+.35**2)
    ks=[];ss=[]
    for _ in range(length):
        v=float(h@p@h);k=p@h/v
        ks.append(k);ss.append(1/math.sqrt(v))
        p=a@(p-np.outer(k,h@p))@a+q
        p=(p+p.T)/2
    k=np.array(ks);return np.ascontiguousarray(k[:,0]),np.ascontiguousarray(k[:,1]),np.array(ss)


@functools.lru_cache(None)
def native_library():
    source=ROOT/'whiten.cpp';library=ROOT/('whiten-'+sha(source)[:16]+'.so')
    receipt=library.with_suffix('.build.json')
    with (ROOT/'native-build.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if not library.exists():
            assert not receipt.exists()
            tmp=library.with_suffix('.'+str(os.getpid())+'.tmp.so')
            command=['g++','-O2','-shared','-fPIC','-ffp-contract=off','-o',str(tmp),str(source)]
            subprocess.run(command,check=True);tmp.replace(library)
            write_json(receipt,dict(source_sha256=sha(source),library_sha256=sha(library),command=command,compiler=subprocess.check_output(['g++','--version'],text=True).splitlines()[0]))
        saved=json.loads(receipt.read_text());assert saved['source_sha256']==sha(source) and saved['library_sha256']==sha(library)
    lib=ctypes.CDLL(str(library));p=ctypes.POINTER(ctypes.c_double)
    lib.whiten.argtypes=[p,p,ctypes.POINTER(ctypes.c_int64),ctypes.c_int64,ctypes.c_int64,ctypes.c_int64,ctypes.c_double,ctypes.c_double,ctypes.c_double,p,p,p]
    lib.whiten.restype=None
    return lib,library


def whiten(values,noise_ids,sampling_scale=1.):
    values=np.ascontiguousarray(values,dtype=np.float64);ids=np.ascontiguousarray(noise_ids,dtype=np.int64)
    assert values.ndim==3 and values.shape[0]==len(ids) and np.all((ids>=0)&(ids<=2))
    b,c,n=values.shape;out=np.empty_like(values);k0,k1,s=coefficients(n,sampling_scale);lib,_=native_library()
    p=ctypes.POINTER(ctypes.c_double)
    lib.whiten(values.ctypes.data_as(p),out.ctypes.data_as(p),ids.ctypes.data_as(ctypes.POINTER(ctypes.c_int64)),b,c,n,.9**(1/sampling_scale),.97**(1/sampling_scale),.45**(1/sampling_scale),k0.ctypes.data_as(p),k1.ctypes.data_as(p),s.ctypes.data_as(p))
    assert np.isfinite(out).all();return out


def normal_power(distance):
    return np.fromiter((NORMAL.cdf(float(v)-Z_ALPHA) for v in np.asarray(distance).ravel()),dtype=float).reshape(np.shape(distance))


def diagnostics(base,meta,stage):
    r=meta['residual']/meta['sigma'][:,None];e=meta['echo']/meta['sigma'][:,None];p=meta['phase']/meta['sigma'][:,None]
    rr=np.mean(r*r,1);ee=np.mean(e*e,1);pp=np.mean(p*p,1);re=np.mean(r*e,1);rp=np.mean(r*p,1)
    eta=np.asarray(original.ETA_LEVELS)
    error_e=np.abs(rr[:,None]-2*re[:,None]*eta[None,:]+ee[:,None]*eta[None,:]**2-1)
    error_p=np.abs(rr[:,None]-2*rp[:,None]*eta[None,:]+pp[:,None]*eta[None,:]**2-1)
    minimum_e=error_e[:,1:].min(1);minimum_null=error_p.min(1)
    sphere_score=np.log10((minimum_null+1e-14)/(minimum_e+1e-14))
    cut=r.shape[1]//2
    x=np.stack([r[:,cut:],e[:,cut:],p[:,cut:]],axis=1)
    w=whiten(x,base['noise_model'],stage['fs']/1000);R,E,P=w[:,0],w[:,1],w[:,2]
    er=np.sum(E*R,1);pr=np.sum(P*R,1);en=np.sum(E*E,1);pn=np.sum(P*P,1);ep=np.sum(E*P,1)
    eta_e=np.clip(er/np.maximum(en,1e-24),0,.2);eta_p=np.clip(pr/np.maximum(pn,1e-24),0,.2)
    le=2*eta_e*er-eta_e**2*en;lp=2*eta_p*pr-eta_p**2*pn
    glrt=le-lp
    strength=base['eta'];closest_phase=np.clip(strength*ep/np.maximum(pn,1e-24),0,.2)
    d_delay=strength*np.sqrt(en)
    d_phase=np.sqrt(np.maximum(0,strength**2*en-2*strength*closest_phase*ep+closest_phase**2*pn))
    analytic_valid=stage['noise']=='stationary_gaussian'
    additions=dict(sphere_score=sphere_score,sphere_h1_error=minimum_e,sphere_null_error=minimum_null,
                   conditional_glrt=glrt,glrt_eta_hat=eta_e,glrt_phase_eta_hat=eta_p,
                   white_template_norm=en,phase_template_norm=pn,template_inner_product=ep,
                   distance_from_delay=d_delay,distance_from_nearest_phase=d_phase,
                   uniform_null_oracle_power_bound=normal_power(d_phase) if analytic_valid else np.full(len(en),-1.),
                   delay_only_oracle_power=normal_power(d_delay) if analytic_valid else np.full(len(en),-1.),
                   template_correlation=ep/np.sqrt(np.maximum(en*pn,1e-24)),
                   **{k:v for k,v in meta.items() if k not in ['residual','echo','phase','sigma']},noise_sigma=meta['sigma'])
    assert all(np.isfinite(v).all() for v in additions.values())
    return additions


def batch_seed(shard,offset):
    # Same phases/draws across same-length arms, independent fixed blocks.
    text=f"{CFG['base_seed']}|{shard}|{offset}".encode()
    return int.from_bytes(hashlib.sha256(text).digest()[:8],'big')%(2**63-1)


def write_json(path,value):
    with Path(path).open('x',encoding='utf-8') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n')
