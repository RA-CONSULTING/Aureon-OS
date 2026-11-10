from pathlib import Path
import json,math,sys
import numpy as np
import torch
import tandem_repair as t


def main():
    torch.set_num_threads(1);checks=[];dev=torch.device('cuda')
    legacy=t.generator_for(t.CFG['stages'][0])
    for shard in [0,31]:
        gen=torch.Generator(device=dev).manual_seed(10901000+shard)
        reference=np.load(t.ROOT/f'historical-{shard:03d}.npz',allow_pickle=False)
        gain,tau,delta=t.original.shard_parameters(shard)
        chunks=[]
        for offset in range(0,256,64):
            b,m=legacy(shard=shard,trial_offset=offset,batch=64,steps=2048,branches=16,gain=gain,tau=tau,delta=delta,device=dev,generator=gen)
            for key,v in b.items():assert np.array_equal(v,reference[key][offset:offset+64]),(shard,key)
            chunks.append(m)
        checks.append(dict(name='archived_historical_stream_exact',shard=shard,trials=256,fields=len(b),passed=True))
    # Exact covariance identity, including finite-series initialization.
    for n,scale in [(8,1),(33,1),(128,1),(33,2),(128,2)]:
        lag=np.abs(np.arange(n)[:,None]-np.arange(n)[None,:])
        for model in range(3):
            C=np.eye(n) if model==0 else (.9**(lag/scale) if model==1 else (.65**2*.97**(lag/scale)+.35**2*.45**(lag/scale))/(.65**2+.35**2))
            W=t.whiten(np.eye(n)[None],np.array([model]),scale)[0].T
            np.testing.assert_allclose(W@C@W.T,np.eye(n),rtol=2e-12,atol=2e-12)
            x=np.random.default_rng(703+n+model).normal(size=(3,n))
            wx=t.whiten(x[None],np.array([model]),scale)[0]
            np.testing.assert_allclose(wx@wx.T,x@np.linalg.solve(C,x.T),rtol=2e-12,atol=2e-12)
    checks.append(dict(name='native_whitening_dense_covariance_precision_identity',sizes=[8,33,128],noise_models=3,passed=True))
    ids=torch.arange(4096,device=dev)%3
    gen=torch.Generator(device=dev).manual_seed(88511)
    noise=t.population_noise(4096,128,ids,gen).cpu().numpy()
    assert np.std(np.sqrt(np.mean(noise*noise,1)))>.03
    for model in range(3):
        sample=noise[ids.cpu().numpy()==model]
        assert abs(np.mean(sample))<.08 and abs(np.mean(sample*sample)-1)<.08
    checks.append(dict(name='population_variance_noise_is_not_fixed_record_rms',rms_std=float(np.std(np.sqrt(np.mean(noise*noise,1)))),passed=True))
    # The scalar likelihood optimum is checked against a dense strength grid.
    for norm,dot in [(3.,.2),(10.,-1.),(5.,4.)]:
        eta=np.clip(dot/norm,0,.2);value=2*eta*dot-eta**2*norm
        grid=np.linspace(0,.2,10001);brute=np.max(2*grid*dot-grid**2*norm)
        assert 0<=value-brute<1e-8
    assert abs(float(t.normal_power(np.array([0.]))[0])-.015)<1e-14
    critical=t.Z_ALPHA+t.NORMAL.inv_cdf(.8)
    assert abs(float(t.normal_power(np.array([critical]))[0])-.8)<1e-14
    checks.append(dict(name='conditional_gaussian_bound_and_glrt',critical_distance_for_80_percent=critical,passed=True))
    # Frequencies above 500 Hz alias at the legacy rate. A 2k sample retains
    # the stated input harmonics; this is not a proof of recurrence convergence.
    times=np.arange(1024)/1000;aliases=[]
    for f in t.original.FREQUENCIES:
        signed=(f+500)%1000-500
        np.testing.assert_allclose(np.sin(2*np.pi*f*times+.31),np.sin(2*np.pi*signed*times+.31),atol=2e-12,rtol=0)
        if f>500:aliases.append(dict(stated_hz=float(f),signed_alias_hz=float(signed)))
    assert max(t.original.FREQUENCIES)<2000/2
    checks.append(dict(name='sampling_alias_identity',aliases=aliases,passed=True))
    for stage in t.CFG['stages'][1:]:
        gen=torch.Generator(device=dev).manual_seed(93012)
        sample_stage={**stage,'steps':2048}
        # Short generated smoke on each configured fs/beta/selection choice;
        # full-duration resource pilot is separate.
        gain,tau,delta=t.original.shard_parameters(31);scale=int(stage['fs']/1000)
        b,m=t.generator_for(stage)(shard=31,trial_offset=0,batch=16,steps=2048,branches=16,gain=gain,tau=tau*scale,delta=delta*scale,device=dev,generator=gen)
        assert np.all(m['selected_weight_before']>0)
        if stage['exclude_selected']:assert np.all(m['selected_weight_after']==0)
        else:assert np.array_equal(m['selected_weight_after'],m['selected_weight_before'])
        z=t.diagnostics(b,m,stage);assert all(np.isfinite(v).all() for v in z.values())
        checks.append(dict(name='finite_amended_generator_and_selection',stage=stage['name'],passed=True))
    lib,library=t.native_library()
    t.write_json(sys.argv[1],dict(passed=True,checks=checks,native_library_sha256=t.sha(library),native_build=json.loads(library.with_suffix('.build.json').read_text()),runtime=dict(torch=torch.__version__,device=torch.cuda.get_device_name(0))))
    print(json.dumps(dict(passed=True,grouped_checks=len(checks))))


if __name__=='__main__':main()
