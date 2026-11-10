from pathlib import Path
import json, sys
import numpy as np
import torch
import diagnostic as d


def main():
    checks=[];dev=torch.device('cuda');dtype=torch.float64
    torch.set_num_threads(1)
    for grid in d.CFG['geometries']:
        for force_null in [True,False]:
            a=d.original.make_generator(dev,20260912);b=d.original.make_generator(dev,20260912)
            for start,size in [(0,64),(64,4),(68,3)]:
                args=(size,grid['rows'],grid['cols'],start,dev,dtype)
                orig=d.original.generate_terrain_batch(*args,a,force_null)
                amended=d.generate(*args,b,force_null)
                assert all(torch.equal(x,y) for x,y in zip(orig,amended[:5]))
            assert torch.equal(a.get_state(),b.get_state())
            checks.append(dict(name='original_generator_bitwise_and_rng',grid=grid['rows'],null=force_null,passed=True))
    for scores,labels,expected_auc,expected_ap in [([1,1,1,1],[0,1,0,1],.5,.5),([0,0,1,1],[0,0,1,1],1.,1.),([1,1,0,0],[0,0,1,1],0.,.5)]:
        r=d.metrics(scores,labels,.5)
        assert r['auroc']==expected_auc and r['average_precision']==expected_ap
        for order in [[3,2,1,0],[1,3,0,2]]:assert d.metrics(np.array(scores)[order],np.array(labels)[order],.5)==r
    checks.append(dict(name='ties_and_known_metrics_order_invariant',passed=True))
    for grid in d.CFG['geometries']:
        detector=d.Detector(grid,770000,dev)
        sample=d.generate(5,grid['rows'],grid['cols'],0,dev,dtype,d.original.make_generator(dev,721),False)
        images,labels,cy,cx,nu,meta=sample
        (score,ys,xs),debug=detector.score(images,cy,cx,meta,return_debug=True)
        ft=torch.fft.fft2(images,norm='ortho');power_t=ft.abs().square().flatten(1)
        scat=[]
        for repeat in range(8):
            z=torch.zeros((len(images),detector.nb),device=dev,dtype=dtype)
            z.scatter_add_(1,detector.bins.expand(len(images),-1),power_t);scat.append(z)
        difference=max(float((v-scat[0]).abs().max()) for v in scat[1:])
        checks.append(dict(name='old_atomic_summation_repeatability_diagnostic',grid=grid['rows'],max_absolute_difference=difference,passed=True))
        assert torch.equal(detector.psd(ft),detector.psd(ft))
        I=images.cpu().numpy();F=np.fft.fft2(I,norm='ortho')
        power=np.abs(F)**2;bins=detector.bins.cpu().numpy();nb=detector.nb
        ps=np.stack([np.bincount(bins,weights=p.ravel(),minlength=nb)/np.maximum(np.bincount(bins,minlength=nb),1) for p in power])
        floor=power.reshape(5,-1)[:,1:].mean(1)*d.CFG['spectrum_floor_relative']
        ps=np.maximum(ps,floor[:,None]);P=ps[:,bins].reshape(F.shape);P[:,0,0]=1
        np.testing.assert_allclose(P,debug['psd'].cpu().numpy(),rtol=2e-12,atol=1e-12)
        bank=detector.ring.cpu().numpy()
        norm=np.sqrt(np.sum(np.abs(bank)[None]**2/P[:,None],axis=(2,3)))
        maps=np.abs(np.fft.ifft2(F[:,None]*bank[None]/P[:,None],norm='ortho').real*np.sqrt(detector.n)/norm[:,:,None,None]).max(1)
        np.testing.assert_allclose(maps,debug['ring_map'].cpu().numpy(),rtol=2e-10,atol=2e-10)
        T=np.fft.fft2(meta['template'].cpu().numpy(),norm='ortho')
        exact=np.abs(np.sum(F*T.conj()/P,axis=(1,2)).real)/np.sqrt(np.sum(np.abs(T)**2/P,axis=(1,2)))
        np.testing.assert_allclose(exact,score[:,-1].cpu().numpy(),rtol=2e-10,atol=2e-10)
        # Sign reversal leaves all absolute scoring and positions invariant.
        neg=detector.score(-images,cy,cx,meta)
        torch.testing.assert_close(score,neg[0],rtol=1e-12,atol=1e-12)
        assert torch.equal(ys,neg[1]) and torch.equal(xs,neg[2])
        # Truth metadata cannot affect any deployable candidate.
        altered={**meta,'template':torch.roll(meta['template'],3,1)}
        other=detector.score(images,cy+2,cx-2,altered)
        cutoff=detector.names.index('truth_location_phi2')
        assert torch.equal(score[:,:cutoff],other[0][:,:cutoff])
        checks.append(dict(name='independent_numpy_psd_maps_oracle_sign_truth_isolation',grid=grid['rows'],passed=True))
    d.write_json(sys.argv[1],dict(passed=True,checks=checks,environment=d.original.environment(dev,dtype)))
    print(json.dumps(dict(passed=True,grouped_checks=len(checks))))


if __name__=='__main__':main()
