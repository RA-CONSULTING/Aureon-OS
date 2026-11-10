"""Performance diagnostic of the unchanged HNC fine-grid kernel."""
import datetime,hashlib,json,os,pathlib,statistics,sys,time
import numpy as np
import torch
ROOT=pathlib.Path(__file__).resolve().parent
FROZEN=pathlib.Path('/projects/u6vs/hnc-organism/expansion-20260912/hnc-fine-v1')
assert hashlib.sha256((FROZEN/'hnc_fine.py').read_bytes()).hexdigest()=='1eac7d95222b480e3e54d02c0e92d939a2b6ac39d5b2e33c1d196f0dec96014c'
sys.path.insert(0,str(FROZEN));import hnc_fine as h
cfg=json.loads((FROZEN/'config.json').read_text())
rank=int(os.environ['SLURM_PROCID']);assert rank in range(4)
assert torch.cuda.is_available() and torch.cuda.device_count()==1
task_id=[0,31,64,127][rank];task=cfg['tasks'][task_id]
out=ROOT/'runs'/('profile-'+os.environ['SLURM_JOB_ID'])/('rank-'+str(rank));out.mkdir(parents=True,exist_ok=False)
device=torch.device('cuda');original_alpha=np.array(cfg['alphas']);original_beta=np.array(cfg['betas'])
h.ALPHAS=original_alpha;h.BETAS=original_beta
h.STEPS=1024;h.BURN_IN=256
metrics=['max_abs','escaped','first_escape_step','lyapunov_per_step','lyapunov_blocks']
# Warm up the unchanged kernel before timing; this is not a scientific horizon test.
h.run_grid(device,**task,stop_step=64)
reference=None;measurements=[]
for multiple in [1,2,4]:
    h.ALPHAS=np.tile(original_alpha,multiple);trials=[];parity=True
    for repeat in range(3):
        torch.cuda.synchronize();torch.cuda.reset_peak_memory_stats()
        began=time.perf_counter();result=h.run_grid(device,**task);torch.cuda.synchronize()
        seconds=time.perf_counter()-began
        if reference is None:reference={k:result[k].copy() for k in metrics}
        checks={k:np.ascontiguousarray(np.tile(reference[k],(multiple,1))).tobytes()==np.ascontiguousarray(result[k]).tobytes() for k in metrics}
        parity=parity and all(checks.values())
        trials.append(dict(repeat=repeat,wall_seconds=seconds,peak_device_bytes=torch.cuda.max_memory_allocated(),parity=checks))
    median=statistics.median(x['wall_seconds'] for x in trials)
    measurements.append(dict(batch_multiple=multiple,trajectories=len(h.ALPHAS)*len(h.BETAS),steps=h.STEPS,
                             median_wall_seconds=median,trajectory_steps_per_second=len(h.ALPHAS)*len(h.BETAS)*h.STEPS/median,
                             exact_duplicate_output_parity=parity,trials=trials))
    print(json.dumps(dict(rank=rank,**measurements[-1])),flush=True)
    (out/'progress.json').write_text(json.dumps(measurements,indent=2)+'\n')
# Instrument a separate short execution; its timing is never mixed into throughput.
h.ALPHAS=original_alpha;h.STEPS=128;h.BURN_IN=32
with torch.profiler.profile(activities=[torch.profiler.ProfilerActivity.CPU,torch.profiler.ProfilerActivity.CUDA]) as prof:
    h.run_grid(device,**task);torch.cuda.synchronize()
events=[]
for event in prof.key_averages():
    value=getattr(event,'self_device_time_total',None)
    if value is None:value=getattr(event,'self_cuda_time_total',None)
    assert value is not None,'Profiler did not expose device time'
    events.append(dict(name=event.key,calls=event.count,self_cpu_us=event.self_cpu_time_total,self_device_us=value))
# Quantify the existing full-horizon forcing allocation separately from recurrence work.
h.ALPHAS=original_alpha[:1];h.BETAS=original_beta[:1];h.STEPS=cfg['horizon'];h.BURN_IN=cfg['burn_in']
torch.cuda.synchronize();torch.cuda.reset_peak_memory_stats();began=time.perf_counter()
h.run_grid(device,**task,stop_step=1);torch.cuda.synchronize()
forcing=dict(horizon=cfg['horizon'],executed_recurrence_steps=1,wall_seconds=time.perf_counter()-began,
             peak_device_bytes=torch.cuda.max_memory_allocated(),
             interpretation='Setup plus full-horizon forcing construction and one trajectory step, not isolated forcing-kernel time.')
result=dict(schema='hnc-throughput-profile/v1',completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            job=os.environ['SLURM_JOB_ID'],rank=rank,task_id=task_id,task=task,
            source_kernel_sha256=hashlib.sha256((FROZEN/'hnc_fine.py').read_bytes()).hexdigest(),
            source_config_sha256=hashlib.sha256((FROZEN/'config.json').read_bytes()).hexdigest(),
            profile_source_sha256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
            torch=str(torch.__version__),gpu=str(torch.cuda.get_device_properties(0).uuid),
            measurements=measurements,profile_events=events,full_horizon_setup=forcing,
            scope='Performance diagnostic only; duplicate trajectories are not new scientific evidence. No production checkpoint or result is changed.',
            expanded_batch_eligible=all(x['exact_duplicate_output_parity'] for x in measurements))
(out/'profile.json').write_text(json.dumps(result,indent=2)+'\n')
(out/'results.sha256').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in sorted(out.iterdir()) if p.is_file() and p.name!='results.sha256'))
