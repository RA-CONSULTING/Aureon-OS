from pathlib import Path
import argparse,datetime,json,os,time
import numpy as np
import torch
import tandem_repair as t


def run(stage_id,shard,out,pilot=False):
    stage=t.CFG['stages'][stage_id];out=Path(out);out.mkdir(parents=True,exist_ok=True)
    stem=('pilot' if pilot else 'full')+f'-s{stage_id:02d}-c{shard:02d}';receipt=out/(stem+'.json');array=out/(stem+'.npz')
    if receipt.exists():
        r=json.loads(receipt.read_text());assert r['array_sha256']==t.sha(array) and r['input_manifest_sha256']==t.sha(t.ROOT/'inputs.sha256');return r
    assert not array.exists(),'Unfinished output; preserve and inspect before rerun'
    trials=t.CFG['pilot_batch'] if pilot else t.CFG['trials'];size=t.CFG['batch_size']
    gain,tau,delta=t.original.shard_parameters(shard);scale=int(stage['fs']/1000);tau*=scale;delta*=scale
    dev=torch.device('cuda');generate=t.generator_for(stage);pieces={};samples={};start=time.monotonic()
    for offset in range(0,trials,size):
        batch=min(size,trials-offset);gen=torch.Generator(device=dev).manual_seed(t.batch_seed(shard,offset))
        base,meta=generate(shard=shard,trial_offset=offset,batch=batch,steps=stage['steps'],branches=16,gain=gain,tau=tau,delta=delta,device=dev,generator=gen)
        extra=t.diagnostics(base,meta,stage)
        for key,value in {**base,**extra}.items():pieces.setdefault(key,[]).append(value)
        if offset==0:
            for key in ['residual','echo','phase','sigma']:samples['sample_'+key]=meta[key][:2]
        print(json.dumps(dict(stage=stage_id,shard=shard,done=offset+batch,total=trials)),flush=True)
    arrays={k:np.concatenate(v) for k,v in pieces.items()};assert all(len(v)==trials and np.isfinite(v).all() for v in arrays.values())
    np.savez_compressed(array,**arrays,**samples)
    r=dict(schema='tandem-repair-result/v1',stage_id=stage_id,stage=stage,shard=shard,pilot=pilot,trials=trials,batch_size=size,
           gain=gain,tau_steps=tau,delta_steps=delta,array_sha256=t.sha(array),input_manifest_sha256=t.sha(t.ROOT/'inputs.sha256'),
           elapsed_seconds=time.monotonic()-start,completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
           gpu_uuid=str(torch.cuda.get_device_properties(0).uuid),device=torch.cuda.get_device_name(0),slurm_job_id=os.environ.get('SLURM_JOB_ID'),
           memory_peak_bytes=torch.cuda.max_memory_allocated(),noise_rms_mean=float(arrays['noise_rms'].mean()),noise_rms_std=float(arrays['noise_rms'].std()),
           max_selected_weight_after=float(arrays['selected_weight_after'].max()),gaussian_bound_valid=stage['noise']=='stationary_gaussian')
    t.write_json(receipt,r);print('COMPLETE='+json.dumps(r),flush=True);return r


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--pilot',action='store_true');p.add_argument('--rank',type=int,default=0);p.add_argument('--ranks',type=int,default=1);a=p.parse_args()
    torch.set_num_threads(1)
    if a.pilot:
        shard=t.CFG['pilot_shards'][a.rank]
        for si in range(len(t.CFG['stages'])):run(si,shard,a.output,True)
    else:
        for shard in t.CFG['full_shards']:
            if shard%a.ranks==a.rank:
                for si in range(len(t.CFG['stages'])):run(si,shard,a.output,False)
