"""Independent history oracle, original control, batch parity and real interruption checks."""
import json
import math
import os
import pathlib
import shutil
import signal
import subprocess
import sys
import tempfile
import time

import numpy as np
import torch
import hnc_histories as new
import hnc_original as old
import run_histories as runner
from trend import temporal_trend

NAMES = ("zero", "positive_one", "negative_one", "alternating_one")
FIELDS = ("max_abs", "escaped", "first_escape_step", "lyapunov_per_step", "lyapunov_blocks")


def configure(module, steps=2048):
    module.ALPHAS = np.array([0., .35, .85, 1.5])
    module.BETAS = np.array([.85, 1., 1.000005, 1.1])
    module.STEPS = steps
    module.BURN_IN = 128


def equal(a, b):
    assert a.keys() == b.keys()
    for field in a:
        assert np.array_equal(a[field], b[field]), field


def oracle(name, alpha, beta, gain, tau, delta, steps):
    # A chronological list and direct recent-window sum, independent of the ring/rolling code.
    length = max(tau, delta) + 1
    history = {"zero": [0.] * length, "positive_one": [1.] * length,
               "negative_one": [-1.] * length,
               "alternating_one": [1. if t % 2 == 0 else -1. for t in range(-length, 0)]}[name]
    weights = 1. / (1. + np.log(new.FREQUENCIES / 7.83))
    weights /= weights.sum()
    phases = 2. * np.pi * np.arange(len(weights)) / len(weights)
    largest = 0.
    for t in range(steps):
        forcing = sum(float(w) * math.sin(2. * math.pi * float(f) * (t / new.FS) + float(p))
                      for w, f, p in zip(weights, new.FREQUENCIES, phases))
        value = forcing + alpha * math.tanh(gain * sum(history[-delta:]) / delta) + beta * history[-tau]
        history.append(value)
        largest = max(largest, abs(value))
    return dict(last_value=history[-1], mean_history=np.mean(history[-length:]),
                rolling_mean=np.mean(history[-delta:]), max_abs=largest)


checks = []
with tempfile.TemporaryDirectory() as temp:
    root = pathlib.Path(temp)
    for kind in ['cpu', 'cuda']:
        assert kind == 'cpu' or torch.cuda.is_available()
        device = torch.device(kind)
        for module in [old, new]:
            configure(module)
        new.HISTORY_NAMES = NAMES
        for tau, delta in [(10, 1), (10, 50), (50, 10)]:
            baseline = old.run_grid(device, 1.5, tau, delta)
            ensemble = new.run_grid(device, 1.5, tau, delta)
            for field in FIELDS:
                assert np.array_equal(baseline[field], ensemble[field][0]), (kind, tau, delta, field)
            checkpoint = root / 'checkpoint.pt'
            _, stop = new.run_grid(device, 1.5, tau, delta, checkpoint=checkpoint,
                                  stop_requested=lambda: True, return_progress=True)
            assert stop == 1024
            equal(ensemble, new.run_grid(device, 1.5, tau, delta, resume=checkpoint))
            new.HISTORY_NAMES = tuple(reversed(NAMES))
            try:
                new.run_grid(device, 1.5, tau, delta, resume=checkpoint)
            except ValueError:
                pass
            else:
                raise AssertionError('Changed history ordering accepted')
            new.HISTORY_NAMES = NAMES
            checks.append(dict(device=kind, tau=tau, delta=delta, original_zero_bitwise=True,
                               interrupted_resume_bitwise=True, history_identity_rejected=True))
        for index, name in enumerate(NAMES):
            new.HISTORY_NAMES = (name,)
            single = new.run_grid(device, 1.5, 50, 10)
            for field in FIELDS + ('last_value', 'mean_history', 'rolling_mean'):
                assert np.array_equal(single[field][0], ensemble[field][index]), (kind, name, field)
        checks.append(dict(device=kind, batched_vs_separate_histories_bitwise=True))
        new.HISTORY_NAMES = NAMES
        configure(new, 96)
        new.ALPHAS = np.array([0., .35])
        new.BETAS = np.array([.85, 1.])
        for tau, delta in [(1, 1), (10, 50), (50, 10), (100, 100)]:
            actual = new.run_grid(device, .5, tau, delta)
            maximum_error = 0.
            for hi, name in enumerate(NAMES):
                for ai, alpha in enumerate(new.ALPHAS):
                    for bi, beta in enumerate(new.BETAS):
                        expected = oracle(name, alpha, beta, .5, tau, delta, 96)
                        for field, value in expected.items():
                            observed = actual[field][hi, ai, bi]
                            assert np.isclose(value, observed, rtol=1e-11, atol=1e-11), (kind, name, field, value, observed)
                            maximum_error = max(maximum_error, abs(value - observed))
            checks.append(dict(device=kind, scalar_direct_history_oracle=True, tau=tau, delta=delta,
                               maximum_absolute_error=maximum_error, tolerance=1e-11))

    configure(new, 8192)
    new.HISTORY_NAMES = NAMES
    config = dict(alphas=new.ALPHAS.tolist(), betas=new.BETAS.tolist(), horizon=8192, burn_in=128,
                  segment_steps=8192, tasks=[dict(gain=1.5, tau=10, delta=1)], initial_histories=list(NAMES))
    config_path = root / 'config.json'
    config_path.write_text(json.dumps(config))
    baseline = new.run_grid(torch.device('cpu'), 1.5, 10, 1)
    env = dict(os.environ, SLURM_PROCID='0')
    for sig in [signal.SIGUSR1, signal.SIGTERM, signal.SIGKILL]:
        out = root / f'signal-{sig}'
        ready = root / f'ready-{sig}'
        cmd = [sys.executable, runner.__file__, '--config', str(config_path), '--output', str(out), '--cpu-test']
        with (root / f'child-{sig}.log').open('w') as log:
            process = subprocess.Popen(cmd + ['--ready-file', str(ready)], env=env, stdout=log, stderr=subprocess.STDOUT)
            deadline = time.monotonic() + 45
            while not ready.exists():
                assert process.poll() is None, 'child exited before signal'
                assert time.monotonic() < deadline, 'child not ready'
                time.sleep(.01)
            process.send_signal(sig)
            code = process.wait(timeout=90)
            assert code == (-signal.SIGKILL if sig == signal.SIGKILL else 75), (sig, code)
            if sig != signal.SIGKILL:
                receipts = list(out.glob('rank-*/attempt-*/receipt.json'))
                assert len(receipts) == 1 and 0 < json.loads(receipts[0].read_text())['stop'] < 8192
            subprocess.run(cmd, env=env, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=90)
        rankdir = out / 'rank-000'
        args = [rankdir, runner.sha(config_path), runner.sha(new.__file__), runner.sha(runner.__file__), config['tasks'][0], 0]
        last = runner.find_resume(*args)
        assert last[0]['stop'] == 8192
        with np.load(last[1].parent / 'grid.npz') as z:
            equal(baseline, {k: z[k] for k in z.files})
        for change in ['config', 'checkpoint', 'fork']:
            if change == 'config':
                altered = list(args); altered[1] = 'bad-config'
            elif change == 'checkpoint':
                cp = last[1].parent / 'checkpoint.pt'; saved = cp.read_bytes(); cp.write_bytes(saved + b'corruption')
                altered = args
            else:
                shutil.copytree(last[1].parent, rankdir / 'attempt-9999')
                altered = args
            try:
                runner.find_resume(*altered)
            except ValueError:
                pass
            else:
                raise AssertionError('Accepted invalid resume: ' + change)
            if change == 'checkpoint': cp.write_bytes(saved)
        checks.append(dict(actual_signal=int(sig), exit_code=code, resumed_output_bitwise=True,
                           configuration_mismatch_rejected=True, corruption_rejected=True, fork_rejected=True))
    t = np.arange(8, dtype=float) * 1048576
    assert not temporal_trend(t, np.ones(8))['flag']
    assert temporal_trend(t, 2. + 1e-5 * t)['flag']
    assert temporal_trend(t, 2. - 1e-5 * t)['flag']
    assert not temporal_trend(t, np.array([1., -1.] * 4))['flag']
    assert not temporal_trend(t[:3], t[:3])['eligible']
    checks.append(dict(descriptive_trend_constant_linear_signs_oscillation_short_series=True))

result = dict(status='PASS', checks=checks, torch=str(torch.__version__),
              kernel_sha256=runner.sha(new.__file__), runner_sha256=runner.sha(runner.__file__),
              original_sha256=runner.sha(old.__file__), test_sha256=runner.sha(__file__),
              job=os.environ.get('SLURM_JOB_ID'))
pathlib.Path(sys.argv[1]).write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2), flush=True)
