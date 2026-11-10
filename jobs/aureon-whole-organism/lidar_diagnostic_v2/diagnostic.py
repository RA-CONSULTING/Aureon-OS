"""Label-blind spectral controls plus explicitly privileged simulation diagnostics.

Original terrain generator is unchanged. An inspected-source return amendment
exposes a transformed target template without consuming any random draws.
"""
from pathlib import Path
import hashlib, inspect, json, math
import numpy as np
import torch
import harmonic_lidar_benchmark as original

ROOT=Path(__file__).resolve().parent
CFG=json.loads((ROOT/'diagnostic-config.json').read_text())
SOURCE_SHA='62800896433e36512e84b4dff9928f2512c7c6cdc491e6481c0cdedbac2e9c05'


def instrumented_generator():
    assert hashlib.sha256(Path(original.__file__).read_bytes()).hexdigest()==SOURCE_SHA
    source=inspect.getsource(original.generate_terrain_batch)
    old='    return terrain, labels, center_y, center_x, nuisance'
    assert source.count(old)==1
    new='''    diagnostic_template = target.clone()
    if bool(torch.any(missing)):
        diagnostic_template = torch.where(missing_mask, torch.zeros_like(diagnostic_template), diagnostic_template)
    if bool(torch.any(blurred)):
        diagnostic_blur = torch.fft.ifft2(torch.fft.fft2(diagnostic_template) * blur_transfer).real
        diagnostic_template = torch.where(blurred[:, None, None], diagnostic_blur, diagnostic_template)
    diagnostic_template -= diagnostic_template.mean(dim=(1, 2), keepdim=True)
    metadata = dict(template=diagnostic_template, beta=beta.flatten(), amplitude=amplitude.flatten(),
                    sigma=core_sigma.flatten(), ring_multiple=ring_multiple.flatten(), width=ring_width.flatten())
    return terrain, labels, center_y, center_x, nuisance, metadata'''
    scope=dict(vars(original));exec(compile(source.replace(old,new),'instrumented_original','exec'),scope)
    return scope['generate_terrain_batch']


generate=instrumented_generator()


def metrics(scores,labels,threshold):
    scores=np.asarray(scores,dtype=np.float64);labels=np.asarray(labels,dtype=bool)
    assert scores.ndim==labels.ndim==1 and len(scores)==len(labels) and np.isfinite(scores).all()
    n1=int(labels.sum());n0=int((~labels).sum())
    if not n1 or not n0: raise ValueError('Both classes required')
    # Average ranks and grouped average precision: ties cannot depend on order.
    order=np.argsort(scores,kind='stable');s=scores[order];y=labels[order]
    starts=np.r_[0,np.flatnonzero(s[1:]!=s[:-1])+1];ends=np.r_[starts[1:],len(s)]
    counts=ends-starts;pos=np.add.reduceat(y.astype(int),starts)
    ranks=(starts+1+ends)/2
    auc=float((np.dot(pos,ranks)-n1*(n1+1)/2)/(n1*n0))
    dp=pos[::-1];dn=counts[::-1];cp=np.cumsum(dp);cn=np.cumsum(dn)
    ap=float(np.sum(dp*(cp/cn))/n1)
    pred=scores>threshold
    tp=int((pred&labels).sum());fp=int((pred&~labels).sum())
    return dict(auroc=auc,average_precision=ap,positives=n1,negatives=n0,
                true_positives=tp,false_positives=fp,tpr=tp/n1,fpr=fp/n0,threshold=float(threshold))


class Detector:
    def __init__(self,grid,jitter_seed,device):
        self.grid=grid;self.device=device;self.dtype=torch.float64
        h,w=grid['rows'],grid['cols'];self.h=h;self.w=w;self.n=h*w
        self.original_names,self.transfers,self.centres=original.build_transfers(**grid,device=device,dtype=self.dtype,jitter_seed=jitter_seed)
        fy=torch.fft.fftfreq(h,device=device,dtype=self.dtype)
        fx=torch.fft.fftfreq(w,device=device,dtype=self.dtype)
        # Integer annuli on the square pixel frequency plane; no truth labels.
        radial=torch.sqrt((h*fy[:,None])**2+(w*fx[None,:])**2)
        self.bins=torch.floor(radial).long().flatten()
        self.nb=int(self.bins.max())+1
        self.counts=torch.bincount(self.bins,minlength=self.nb).to(self.dtype)
        self.membership=torch.nn.functional.one_hot(self.bins,num_classes=self.nb).to(self.dtype)
        self.roi=torch.zeros((h,w),device=device,dtype=torch.bool)
        my=max(8,h//5);mx=max(8,w//5)
        self.roi[my:h-my+1,mx:w-mx+1]=True
        yp=torch.fft.fftfreq(h,device=device,dtype=self.dtype)*h
        xp=torch.fft.fftfreq(w,device=device,dtype=self.dtype)*w
        dist=torch.sqrt(yp[:,None]**2+xp[None,:]**2)
        ring=[];gauss=[]
        for sigma in CFG['template_sigmas']:
            core=torch.exp(-.5*(dist/sigma)**2);gauss.append(core-core.mean())
            for multiple in CFG['template_ring_multiples']:
                for width in CFG['template_widths']:
                    template=core+.45*torch.exp(-.5*((dist-sigma*multiple)/width)**2)
                    ring.append(template-template.mean())
        self.ring=torch.fft.fft2(torch.stack(ring),norm='ortho').conj()
        self.gauss=torch.fft.fft2(torch.stack(gauss),norm='ortho').conj()
        self.names=self.original_names+['phi2_roi','whitened_phi2_roi','whitened_log_roi',
            'matched_gaussian_roi','matched_ring_roi','truth_location_phi2','truth_location_whitened_phi2',
            'truth_location_matched_ring','truth_shape_location_matched']

    def psd(self,F):
        power=F.abs().square().flatten(1)
        # Fixed dense reduction avoids order-dependent CUDA atomic scatter sums.
        ps=power@self.membership
        ps/=self.counts.clamp_min(1)
        floor=power[:,1:].mean(1,keepdim=True)*CFG['spectrum_floor_relative']
        ps=ps.clamp_min(floor)
        P=ps[:,self.bins].reshape(F.shape)
        P[:,0,0]=1
        return P

    def maxima(self,maps,roi=False):
        if roi: maps=maps.masked_fill(~self.roi,-torch.inf)
        score,loc=maps.flatten(1).max(1)
        return score,loc//self.w,loc%self.w

    def bank_map(self,F,P,bank):
        H=bank[None]/P[:,None]
        norm=(bank.abs().square()[None]/P[:,None]).sum((2,3)).sqrt()
        response=torch.fft.ifft2(F[:,None]*H,norm='ortho').real*math.sqrt(self.n)
        response=response/norm[:,:,None,None].clamp_min(1e-15)
        return response.abs().amax(1)

    def score(self,images,cy,cx,meta,return_debug=False):
        old,y,x=original.score_batch(images,self.transfers)
        F=torch.fft.fft2(images,norm='ortho');P=self.psd(F)
        phi_map=torch.fft.ifft2(F*self.transfers[0],norm='ortho').real.abs()
        pick=[0,self.original_names.index('laplacian_of_gaussian')]
        H=self.transfers[pick][None]/P[:,None].sqrt()
        white_maps=torch.fft.ifft2(F[:,None]*H,norm='ortho').real.abs()
        white_norm=(self.transfers[pick].square().sum((1,2))/self.n).sqrt()
        white_maps=white_maps/white_norm[None,:,None,None]
        gauss=self.bank_map(F,P,self.gauss);ring=self.bank_map(F,P,self.ring)
        scores=[old[:,j] for j in range(old.shape[1])]
        ys=[y[:,j] for j in range(y.shape[1])];xs=[x[:,j] for j in range(x.shape[1])]
        for m in [phi_map,white_maps[:,0],white_maps[:,1],gauss,ring]:
            sc,yy,xx=self.maxima(m,True);scores.append(sc);ys.append(yy);xs.append(xx)
        iy=cy.round().long().clamp(0,self.h-1);ix=cx.round().long().clamp(0,self.w-1)
        bi=torch.arange(len(images),device=self.device)
        for m in [phi_map,white_maps[:,0],ring]:
            scores.append(m[bi,iy,ix]);ys.append(iy);xs.append(ix)
        T=torch.fft.fft2(meta['template'],norm='ortho')
        exact=(F*T.conj()/P).sum((1,2)).real.abs()/(T.abs().square()/P).sum((1,2)).sqrt().clamp_min(1e-15)
        scores.append(exact);ys.append(iy);xs.append(ix)
        result=(torch.stack(scores,1),torch.stack(ys,1),torch.stack(xs,1))
        if return_debug:return result,dict(psd=P,ring_map=ring,phi_map=phi_map,white_maps=white_maps)
        return result


def evidence_hash(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path,payload):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as f:json.dump(payload,f,indent=2,allow_nan=False);f.write('\n')
