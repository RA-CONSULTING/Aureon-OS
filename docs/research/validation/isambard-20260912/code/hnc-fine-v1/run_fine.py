"""Immutable per-attempt receipts, verified resume chains and graceful signal handling."""
import argparse
import fcntl
import hashlib
import json
import os
import pathlib
import signal
import socket
import time

import numpy as np
import torch
import hnc_fine as h


def sha(p):
    out=hashlib.sha256()
    with pathlib.Path(p).open('rb') as stream:
        for chunk in iter(lambda:stream.read(4*1024*1024),b''):out.update(chunk)
    return out.hexdigest()


def find_resume(rankdir,config_hash,kernel_hash,runner_hash,task,rank):
    receipts=[]
    for p in rankdir.glob('attempt-*/receipt.json'):
        r=json.loads(p.read_text())
        for key,value in [('config_sha256',config_hash),('harness_sha256',kernel_hash),
                          ('runner_sha256',runner_hash),('task',task),('rank',rank)]:
            if r.get(key)!=value:raise ValueError(f'Resume identity mismatch: {p}/{key}')
        for name,key in [('checkpoint.pt','checkpoint_sha256'),('grid.npz','grid_sha256')]:
            if sha(p.parent/name)!=r[key]:raise ValueError(f'Resume artifact hash mismatch: {p}/{name}')
        if r['status'] not in ['COMPLETE_SEGMENT','INTERRUPTED','COMPLETE'] or not 0<=r['start']<r['stop']:
            raise ValueError('Invalid receipt status or interval')
        receipts.append((r,p))
    receipts.sort(key=lambda item:item[0]['stop'])
    stop=0; previous=None
    for r,p in receipts:
        if r['start']!=stop or r['previous_receipt_sha256']!=previous:
            raise ValueError(f'Broken or forked checkpoint chain: {p}')
        stop=r['stop'];previous=sha(p)
    return receipts[-1] if receipts else None


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--config',required=True);p.add_argument('--output',required=True)
    p.add_argument('--max-stop',type=int);p.add_argument('--cpu-test',action='store_true')
    p.add_argument('--ready-file')
    a=p.parse_args(); cfg=json.loads(pathlib.Path(a.config).read_text())
    rank=int(os.environ['SLURM_PROCID']);task=cfg['tasks'][rank]
    if not 0<=rank<len(cfg['tasks']):raise ValueError('Rank outside manifest')
    device=torch.device('cpu' if a.cpu_test else 'cuda')
    if not a.cpu_test and (not torch.cuda.is_available() or torch.cuda.device_count()!=1):
        raise RuntimeError('Exactly one visible CUDA device required')
    h.ALPHAS=np.asarray(cfg['alphas']);h.BETAS=np.asarray(cfg['betas'])
    h.STEPS=cfg['horizon'];h.BURN_IN=cfg['burn_in']
    limit=cfg['horizon'] if a.max_stop is None else a.max_stop
    if not 0<limit<=cfg['horizon']:raise ValueError('Invalid stop limit')
    rankdir=pathlib.Path(a.output)/f'rank-{rank:03d}';rankdir.mkdir(parents=True,exist_ok=True)
    lock=(rankdir/'.writer.lock').open('a')
    fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
    ch,hh,rh=sha(a.config),sha(h.__file__),sha(__file__)
    prior=find_resume(rankdir,ch,hh,rh,task,rank)
    start=prior[0]['stop'] if prior else 0
    if start>limit:raise ValueError('Existing checkpoint beyond requested stop')
    stopped={'value':False,'signal':None}
    def handler(number,frame):
        stopped.update(value=True,signal=number)
    for sig in [signal.SIGUSR1,signal.SIGTERM,signal.SIGINT]:signal.signal(sig,handler)
    if a.ready_file:pathlib.Path(a.ready_file).write_text('ready')
    while start<limit:
        target=min(((start//cfg['segment_steps'])+1)*cfg['segment_steps'],limit)
        existing=[int(d.name.split('-')[1]) for d in rankdir.glob('attempt-*') if d.is_dir()]
        out=rankdir/f'attempt-{max(existing,default=-1)+1:04d}';out.mkdir()
        if device.type=='cuda':torch.cuda.synchronize();torch.cuda.reset_peak_memory_stats()
        t0=time.monotonic()
        grid,actual=h.run_grid(device,task['gain'],task['tau'],task['delta'],
                              resume=prior[1].parent/'checkpoint.pt' if prior else None,
                              checkpoint=out/'checkpoint.pt',stop_step=target,
                              stop_requested=lambda:stopped['value'],return_progress=True)
        if device.type=='cuda':torch.cuda.synchronize()
        elapsed=time.monotonic()-t0
        if not start<actual<=target:raise RuntimeError('No valid checkpoint progress')
        np.savez_compressed(out/'grid.npz',**grid)
        receipt=dict(schema='hnc-fine-segment/v1',rank=rank,task=task,start=start,stop=actual,
                     target_stop=target,horizon=cfg['horizon'],
                     status='COMPLETE' if actual==cfg['horizon'] else 'INTERRUPTED' if actual<target else 'COMPLETE_SEGMENT',
                     config_sha256=ch,harness_sha256=hh,runner_sha256=rh,
                     checkpoint_sha256=sha(out/'checkpoint.pt'),grid_sha256=sha(out/'grid.npz'),
                     previous_receipt_sha256=sha(prior[1]) if prior else None,
                     elapsed_seconds=elapsed,signal=stopped['signal'],
                     trajectory_steps=len(h.ALPHAS)*len(h.BETAS)*(actual-start),
                     job=os.environ.get('SLURM_JOB_ID'),host=socket.gethostname(),torch=str(torch.__version__),
                     device_type=device.type,claim_class='computational_simulation',reference_beta=1.0,
                     gpu_uuid=str(torch.cuda.get_device_properties(0).uuid) if device.type=='cuda' else None,
                     peak_allocated_bytes=torch.cuda.max_memory_allocated() if device.type=='cuda' else None)
        temp=out/'receipt.tmp';temp.write_text(json.dumps(receipt,indent=2));temp.rename(out/'receipt.json')
        print(json.dumps(receipt),flush=True)
        start=actual;prior=(receipt,out/'receipt.json')
        if stopped['value'] and start<limit:return 75
    return 0


if __name__=='__main__':raise SystemExit(main())
