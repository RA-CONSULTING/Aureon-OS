import json
import os
import pathlib
import signal
import subprocess
import sys
import tempfile
import time

import numpy as np
import torch
import hnc_fine as new
import hnc_reference as old
import run_fine as runner


def configure(module,steps=4096):
    module.ALPHAS=np.array([0.,.35,.85,1.5]);module.BETAS=np.array([.85,1.,1.000005,1.1])
    module.STEPS=steps;module.BURN_IN=128


def equal(a,b):
    assert a.keys()==b.keys()
    for field in a:assert np.array_equal(a[field],b[field]),field


checks=[]
with tempfile.TemporaryDirectory() as temp:
    root=pathlib.Path(temp)
    for module in [new,old]:configure(module)
    for kind in ['cpu','cuda']:
        assert kind=='cpu' or torch.cuda.is_available()
        device=torch.device(kind)
        for tau,delta in [(10,1),(10,50),(50,10)]:
            baseline=old.run_grid(device,1.5,tau,delta)
            equal(baseline,new.run_grid(device,1.5,tau,delta))
            checkpoint=root/'checkpoint.pt'
            partial,stop=new.run_grid(device,1.5,tau,delta,checkpoint=checkpoint,
                                      stop_requested=lambda:True,return_progress=True)
            assert stop==1024
            equal(baseline,new.run_grid(device,1.5,tau,delta,resume=checkpoint))
            checks.append(dict(device=kind,tau=tau,delta=delta,baseline_bitwise=True,interrupted_resume_bitwise=True))
    config=dict(alphas=new.ALPHAS.tolist(),betas=new.BETAS.tolist(),horizon=8192,burn_in=128,
                segment_steps=8192,tasks=[dict(gain=1.5,tau=10,delta=1)])
    config_path=root/'config.json';config_path.write_text(json.dumps(config))
    configure(new,8192)
    baseline=new.run_grid(torch.device('cpu'),1.5,10,1)
    env=dict(os.environ,SLURM_PROCID='0')
    script=pathlib.Path(runner.__file__)
    for sig in [signal.SIGUSR1,signal.SIGTERM,signal.SIGKILL]:
        out=root/f'signal-{sig}';ready=root/f'ready-{sig}'
        cmd=[sys.executable,str(script),'--config',str(config_path),'--output',str(out),'--cpu-test']
        with (root/f'child-{sig}.log').open('w') as log:
            process=subprocess.Popen(cmd+['--ready-file',str(ready)],env=env,stdout=log,stderr=subprocess.STDOUT)
            deadline=time.monotonic()+30
            while not ready.exists():
                assert process.poll() is None,'child exited before signal'
                assert time.monotonic()<deadline,'child not ready'
                time.sleep(.01)
            process.send_signal(sig);code=process.wait(timeout=60)
            assert code==(-signal.SIGKILL if sig==signal.SIGKILL else 75),(sig,code)
            before=list(out.glob('rank-*/attempt-*/receipt.json'))
            if sig!=signal.SIGKILL:
                assert len(before)==1
                assert 0<json.loads(before[0].read_text())['stop']<8192
            subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=60)
        rankdir=out/'rank-000'
        last=runner.find_resume(rankdir,runner.sha(config_path),runner.sha(new.__file__),runner.sha(runner.__file__),config['tasks'][0],0)
        assert last[0]['stop']==8192
        with np.load(last[1].parent/'grid.npz') as z:equal(baseline,{k:z[k] for k in z.files})
        try:runner.find_resume(rankdir,'bad-config',runner.sha(new.__file__),runner.sha(runner.__file__),config['tasks'][0],0)
        except ValueError:pass
        else:raise AssertionError('configuration mismatch accepted')
        checkpoint=last[1].parent/'checkpoint.pt';saved=checkpoint.read_bytes()
        checkpoint.write_bytes(saved+b'corruption')
        try:runner.find_resume(rankdir,runner.sha(config_path),runner.sha(new.__file__),runner.sha(runner.__file__),config['tasks'][0],0)
        except ValueError:pass
        else:raise AssertionError('corrupt checkpoint accepted')
        checks.append(dict(actual_signal=int(sig),exit_code=code,resume_bitwise=True,config_mismatch_rejected=True,checkpoint_corruption_rejected=True))
result=dict(status='PASS',checks=checks,torch=str(torch.__version__),
            kernel_sha256=runner.sha(new.__file__),runner_sha256=runner.sha(runner.__file__),
            test_sha256=runner.sha(__file__),job=os.environ.get('SLURM_JOB_ID'))
pathlib.Path(sys.argv[1]).write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
