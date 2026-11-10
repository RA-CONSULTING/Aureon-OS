"""Read-only pilot/final evidence audit with a declared production resource decision."""
import argparse, csv, datetime, hashlib, json, math, pathlib, shutil, subprocess, sys
import numpy as np
import torch


def sha(path):
    h = hashlib.sha256()
    with pathlib.Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(4 * 1024 * 1024), b''): h.update(chunk)
    return h.hexdigest()


p = argparse.ArgumentParser()
p.add_argument('--pack', required=True); p.add_argument('--campaign', required=True)
p.add_argument('--job', required=True); p.add_argument('--stop', type=int, required=True)
p.add_argument('--output', required=True)
a = p.parse_args(); pack = pathlib.Path(a.pack); root = pathlib.Path(a.campaign)
out = pathlib.Path(a.output); assert not out.exists()
sys.path.insert(0, str(pack)); import run_histories as runner
cfg = json.loads((pack / 'config.json').read_text())
for line in (pack / 'inputs.sha256').read_text().splitlines():
    digest, name = line.split('  ', 1); assert sha(pack / name) == digest
assert (root / 'config.json').read_bytes() == (pack / 'config.json').read_bytes()
assert (root / 'inputs.sha256').read_bytes() == (pack / 'inputs.sha256').read_bytes()
accounting = subprocess.check_output(['sacct', '-j', a.job, '--format=JobID,State,ExitCode,ElapsedRaw,AllocNodes,AllocTRES', '-P'], text=True)
jobs = {r['JobID']: r for r in csv.DictReader(accounting.splitlines(), delimiter='|')}
job = jobs[a.job]; assert job['State'] == 'COMPLETED' and job['ExitCode'] == '0:0', job
assert int(job['AllocNodes']) == 32
assert (root / ('completed-' + a.job + '.txt')).exists()
shape = (len(cfg['initial_histories']), len(cfg['alphas']), len(cfg['betas']))
ch, hh, rh = sha(pack / 'config.json'), sha(pack / 'hnc_histories.py'), sha(pack / 'run_histories.py')
gpu_ids = set(); receipts = []; files_verified = 0; cp_bytes = 0
for rank, task in enumerate(cfg['tasks']):
    rankdir = root / ('rank-' + str(rank).zfill(3))
    last = runner.find_resume(rankdir, ch, hh, rh, task, rank)
    assert last and last[0]['stop'] == a.stop
    r, rp = last
    assert r['job'] == a.job and r['device_type'] == 'cuda'
    assert r['initial_histories'] == cfg['initial_histories']
    assert r['horizon'] == cfg['horizon'] and r['reference_beta'] == 1.0
    assert r['trajectory_steps'] == int(np.prod(shape)) * (r['stop'] - r['start'])
    assert r['gpu_uuid'] and r['gpu_uuid'] not in gpu_ids; gpu_ids.add(r['gpu_uuid'])
    cp = rp.parent / 'checkpoint.pt'; cp_bytes += cp.stat().st_size
    payload = torch.load(cp, weights_only=True, map_location='cpu')
    identity = payload['identity']
    assert identity['initial_history_names'] == cfg['initial_histories']
    assert identity['initialization_version'] == cfg['initialization_version']
    assert identity['steps'] == cfg['horizon'] and identity['harness_sha256'] == hh
    assert identity['alphas'] == cfg['alphas'] and identity['betas'] == cfg['betas']
    assert identity['burn_in'] == cfg['burn_in'] and identity['escape_threshold'] == cfg['escape_threshold']
    assert identity['device_type'] == 'cuda' and identity['torch_version'] == r['torch']
    for key in ['gain', 'tau', 'delta']: assert identity[key] == task[key]
    assert payload['step'] == a.stop and payload['pointer'] == a.stop % (max(task['tau'], task['delta']) + 1)
    tensors = payload['tensors']; base = tensors['base']; length = max(task['tau'], task['delta']) + 1
    assert tuple(base.shape) == (int(np.prod(shape)), length)
    assert base.dtype == torch.float64 and tensors['perturbed'].shape == base.shape
    with np.load(rp.parent / 'grid.npz') as z:
        assert np.array_equal(z['initial_history_names'], cfg['initial_histories'])
        assert np.array_equal(z['alpha'], cfg['alphas']) and np.array_equal(z['beta'], cfg['betas'])
        for field, source in [('max_abs', 'max_abs'), ('escaped', 'escaped'), ('first_escape_step', 'first_escape'), ('lyapunov_blocks', 'lyapunov_blocks')]:
            assert z[field].shape == shape and np.array_equal(z[field], tensors[source].numpy().reshape(shape)), field
        assert np.array_equal(z['last_value'], base[:, (payload['pointer'] - 1) % length].numpy().reshape(shape))
        # CPU/CUDA parallel reductions can differ in rounding; these read-only summaries use a tight tolerance.
        assert np.allclose(z['mean_history'], base.mean(dim=1).numpy().reshape(shape), rtol=2e-14, atol=2e-14)
        assert np.array_equal(z['rolling_mean'], (tensors['rolling_base'] / task['delta']).numpy().reshape(shape))
        expected = tensors['lyapunov_sum'] / (tensors['lyapunov_blocks'].clamp_min(1).to(torch.float64) * identity['renormalize_every'])
        assert np.allclose(z['lyapunov_per_step'], expected.numpy().reshape(shape), rtol=2e-14, atol=2e-14)
    for rp2 in rankdir.glob('attempt-*/receipt.json'): files_verified += 2
    receipts.append(dict(rank=rank, receipt=str(rp.relative_to(root)), receipt_sha256=sha(rp),
                         stop=r['stop'], elapsed_seconds=r['elapsed_seconds'], start=r['start'],
                         seconds_per_step=r['elapsed_seconds'] / (r['stop'] - r['start']),
                         gpu_uuid=r['gpu_uuid'], checkpoint_bytes=cp.stat().st_size))
    del payload, tensors, base, expected
assert len(receipts) == 128 and len(gpu_ids) == 128
free = shutil.disk_usage(root).free
projected_storage = cp_bytes * (math.ceil(cfg['horizon'] / cfg['segment_steps']) + 2)
assert free > projected_storage + 100 * 1024 ** 3, (free, projected_storage)
remaining = cfg['horizon'] - a.stop
projected_seconds = max(r['seconds_per_step'] for r in receipts) * remaining
wall_seconds = math.ceil((1.25 * projected_seconds + 900) / 1800) * 1800
decision = dict(status='READY_TO_STAGE' if wall_seconds <= 28800 else 'REASSESS_REQUIRED',
                projected_remaining_seconds=projected_seconds, walltime_seconds=wall_seconds,
                ceiling_node_hours=32 * wall_seconds / 3600, nodes=32, gpus=128,
                rate_rule='Slowest pilot elapsed/step; 25 percent margin plus 15 minutes; half-hour ceiling; maximum eight hours',
                checkpoint_wave_bytes=cp_bytes, projected_checkpoint_storage_bytes=projected_storage,
                filesystem_free_bytes=free)
result = dict(schema='hnc-history-audit/v1', status='PASS', observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
              job=a.job, stop=a.stop, ranks_verified=128, distinct_gpus=128, result_and_checkpoint_hashes_verified=files_verified,
              input_manifest_sha256=sha(pack / 'inputs.sha256'), audit_source_sha256=sha(__file__),
              accounting=jobs, allocated_node_hours=int(job['ElapsedRaw']) * 32 / 3600,
              original_results_unchanged=True, checkpoint_outputs_verified=True, ranks=receipts, resource_decision=decision)
out.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({k: result[k] for k in ['status', 'job', 'stop', 'ranks_verified', 'distinct_gpus', 'allocated_node_hours', 'resource_decision']}, indent=2))
