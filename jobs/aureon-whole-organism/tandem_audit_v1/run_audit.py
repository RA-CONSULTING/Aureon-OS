from pathlib import Path
import argparse,datetime,hashlib,json,math,statistics,tarfile,time
import numpy as np
from analysis import analyse
from independent_channels import white

BASE=Path('/projects/u6vs/hnc-organism/expansion-20260912')
SOURCE=BASE/'tandem-repair-v1';ROOT=BASE/'tandem-repair-results-v1';HERE=Path(__file__).resolve().parent
MANIFEST='ecea7bc161a3c0daafa198758d13b7889ba144f8fd7a17472c1b7d670674016e'

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def write(path,value):
    data=(json.dumps(value,indent=2,allow_nan=False)+'\n').encode()
    if path.exists():assert path.read_bytes()==data
    else:path.write_bytes(data)

def main(accounting_path):
    started=time.monotonic();cfg=json.loads((SOURCE/'config.json').read_text());submission=json.loads((HERE/'full-submission.json').read_text());job=submission['job_id']
    accounting=Path(accounting_path).read_text();assert any(l.startswith(job+'|COMPLETED|0:0|') for l in accounting.splitlines()),accounting
    assert sha(SOURCE/'inputs.sha256')==MANIFEST
    for line in (SOURCE/'inputs.sha256').read_text().splitlines():
        digest,name=line.split('  ',1);assert sha(SOURCE/name)==digest,name
    expected={f'full-s{s:02d}-c{c:02d}.json' for s in range(7) for c in range(32)}
    assert {p.name for p in ROOT.glob('full-s*-c*.json')}==expected
    assert {p.name for p in ROOT.glob('full-s*-c*.npz')}=={x.replace('.json','.npz') for x in expected}
    receipts=[];files=[];stages=[];gpus={};max_errors={};sample_models=set();full_trials=0
    normal=statistics.NormalDist();critical=normal.inv_cdf(.985)
    def check(key,actual,wanted,rtol=2e-9,atol=2e-10):
        np.testing.assert_allclose(actual,wanted,rtol=rtol,atol=atol,err_msg=key)
        max_errors[key]=max(max_errors.get(key,0.),float(np.max(np.abs(np.asarray(actual)-wanted))))
    for si,stage in enumerate(cfg['stages']):
        parts={}
        for cell in range(32):
            rp=ROOT/f'full-s{si:02d}-c{cell:02d}.json';ap=rp.with_suffix('.npz');r=json.loads(rp.read_text());assert sha(ap)==r['array_sha256']
            assert (r['stage_id'],r['shard'],r['trials'],r['pilot'],r['slurm_job_id'])==(si,cell,10368,False,job)
            assert r['stage']==stage and r['input_manifest_sha256']==MANIFEST
            with np.load(ap,allow_pickle=False) as pack:d={k:pack[k] for k in pack.files}
            assert all(np.isfinite(v).all() for v in d.values())
            ids=cell*10_000_000+np.arange(10368)
            wanted=dict(trial_id=ids,eta=np.array([0,.002,.005,.01,.02,.05,.1,.2])[ids%8],snr_db=np.array([-10,0,10,20])[(ids//8)%4],noise_model=(ids//32)%3,operator=(ids//96)%3,truth_model=(ids//288)%3,null_split=(ids//864)%2)
            for key,value in wanted.items():assert np.array_equal(d[key],value),key
            for key,v in d.items():
                if not key.startswith('sample_'):
                    assert v.shape==(10368,),key;parts.setdefault(key,[]).append(v)
            parts.setdefault('cell',[]).append(np.full(10368,cell,dtype=np.int64))
            assert np.array_equal(d['discriminant'],d['corr_true']-d['corr_shift'])
            assert np.all((d['selected_branch']>=0)&(d['selected_branch']<16))
            assert np.all(d['selected_weight_before']>0) and np.all((d['effective_branches']>=1)&(d['effective_branches']<=16+1e-12))
            if si>=3:assert np.all(d['selected_weight_after']==0) and r['max_selected_weight_after']==0
            else:assert np.array_equal(d['selected_weight_before'],d['selected_weight_after'])
            if si==0:
                check('legacy_fixed_rms',d['noise_rms'],np.ones(10368),rtol=0,atol=2e-14)
                assert np.all(d['uniform_null_oracle_power_bound']==-1) and not r['gaussian_bound_valid']
            else:
                assert r['gaussian_bound_valid']
                for key,dist in [('uniform_null_oracle_power_bound','distance_from_nearest_phase'),('delay_only_oracle_power','distance_from_delay')]:
                    expected_power=np.fromiter((normal.cdf(float(x)-critical) for x in d[dist]),float)
                    check(key,d[key],expected_power,rtol=0,atol=2e-14)
                assert np.all(d['distance_from_nearest_phase']<=d['distance_from_delay']+1e-10)
            # Independent saved-channel recalculation, including all 3 noise models.
            cut=stage['steps']//2;scale=stage['fs']/1000
            for row in range(2):
                sigma=d['sample_sigma'][row];x=np.array([d['sample_residual'][row],d['sample_echo'][row],d['sample_phase'][row]])/sigma
                model=int(d['noise_model'][row]);sample_models.add(model);R,E,P=white(x[:,cut:],model,scale)
                en=E@E;pn=P@P;er=E@R;pr=P@R;ep=E@P;a=np.clip(er/en,0,.2);b=np.clip(pr/pn,0,.2)
                score=2*a*er-a*a*en-(2*b*pr-b*b*pn)
                for key,value in dict(conditional_glrt=score,white_template_norm=en,phase_template_norm=pn,template_inner_product=ep).items():check(key,d[key][row],value)
                def corr(a,b):
                    a=a-a.mean();b=b-b.mean();return a@b/math.sqrt((a@a)*(b@b))
                shift=min(cut//3,3*r['tau_steps']+17*int(scale));ct=corr(x[0,cut:],x[1,cut:]);cs=abs(corr(x[0,cut:],np.roll(x[1,cut:],shift)))
                check('D0_saved_channels',d['discriminant'][row],ct-cs,rtol=1e-8,atol=1e-12)
                rr,ee,pp=x;eta=np.array([0,.002,.005,.01,.02,.05,.1,.2]);rr2=np.mean(rr*rr)
                he=np.min(np.abs(rr2-2*eta[1:]*np.mean(rr*ee)+eta[1:]**2*np.mean(ee*ee)-1))
                hn=np.min(np.abs(rr2-2*eta*np.mean(rr*pp)+eta**2*np.mean(pp*pp)-1))
                check('sphere_h1_error',d['sphere_h1_error'][row],he,rtol=1e-8,atol=1e-12)
                check('sphere_null_error',d['sphere_null_error'][row],hn,rtol=1e-8,atol=1e-12)
            # Pilot and full duplicate development blocks must reproduce exactly.
            if cell in [0,15,16,31]:
                pilot=ROOT/f'pilot-s{si:02d}-c{cell:02d}.npz';pr=json.loads(pilot.with_suffix('.json').read_text());assert sha(pilot)==pr['array_sha256']
                with np.load(pilot,allow_pickle=False) as p:
                    assert set(p.files)==set(d)
                    for key in d:
                        actual=d[key] if key.startswith('sample_') else d[key][:512]
                        assert np.array_equal(actual,p[key]),('pilot_overlap',si,cell,key)
            gpus.setdefault(cell,set()).add(r['gpu_uuid']);receipts.append(r);files.extend([rp,ap]);full_trials+=len(ids)
        stages.append({k:np.concatenate(v) for k,v in parts.items()})
        print(json.dumps(dict(stage=si,verified_cells=32)),flush=True)
    assert full_trials==2322432 and sample_models=={0,1,2}
    assert len(gpus)==32 and all(len(v)==1 for v in gpus.values()) and len({next(iter(v)) for v in gpus.values()})==32
    results=analyse(stages,cfg);assert sum(s['eligible'] for s in results['stages'])==2308096
    output=HERE/('analysis-'+job+'.json');write(output,results)
    audit=dict(passed=True,verified_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),full_job_id=job,accounting=accounting,full_records=full_trials,eligible_records=2308096,receipt_count=len(receipts),distinct_gpus=32,saved_channel_records_recomputed=448,saved_channel_noise_models=sorted(sample_models),pilot_duplicate_blocks_bitwise=28,source_manifest_sha256=MANIFEST,audit_manifest_sha256=sha(HERE/'inputs.sha256'),analysis_sha256=sha(output),max_absolute_recalculation_errors=max_errors,receipts=receipts,files=[dict(name=p.name,sha256=sha(p),bytes=p.stat().st_size) for p in files],elapsed_seconds=time.monotonic()-started,boundary='Full source/result/identity/GPU accounting and all scalar metric/bound checks. Independent sample channel calculations on 448 records. This is an author-run computational audit, not independent human or physical replication.')
    audit_path=HERE/('audit-'+job+'.json');write(audit_path,audit)
    archive=HERE/('verified-tandem-'+job+'.tar.gz')
    with tarfile.open(archive,'w:gz',compresslevel=1) as tar:
        for p in files+[output,audit_path,Path(accounting_path)]:tar.add(p,arcname=p.name)
    export=dict(archive_path=str(archive),archive_sha256=sha(archive),archive_bytes=archive.stat().st_size,analysis_sha256=sha(output),audit_sha256=sha(audit_path),members=len(files)+3)
    write(HERE/('export-'+job+'.json'),export);print(json.dumps(export),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('accounting');a=p.parse_args();main(a.accounting)
