"""Read-only audit of both HNC horizon runs, with physical UUID checks for new runs."""
import argparse
import collections
import hashlib
import json
import pathlib

import numpy as np


def sha(path):
    h = hashlib.sha256()
    with pathlib.Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def boundaries(beta, fraction):
    mask = (beta >= .95) & (beta <= 1.05)
    x, y = beta[mask], fraction[mask]
    if len(x) < 2 or np.any(np.diff(x) <= 0):
        raise ValueError('invalid fine grid')
    values = [float(x[i] + (.5-y[i]) * (x[i+1]-x[i]) / (y[i+1]-y[i]))
              for i in range(len(x)-1) if y[i] >= .5 > y[i+1]]
    return dict(boundary=values[0] if values else None,
                all_downward_crossings=values,
                boundary_status='within_fine_grid' if values else
                    ('below_threshold_throughout' if y.max() < .5 else 'no_downward_crossing'),
                starts_below_threshold=bool(y[0] < .5),
                curve_has_upward_step=bool(np.any(np.diff(y) > 0)))


def run(args):
    base = pathlib.Path(args.base)
    config_path = base / 'horizon-extension-v1/config.json'
    config = json.loads(config_path.read_text())
    chash = sha(config_path)
    old_source, new_source = base / 'longrun-v1', base / 'horizon-extension-v1'
    # These are the frozen inputs of the already launched campaign.
    expected_config = 'f43b0d9c725c421f59e130cb5ef33bae23969e8f13d563d5f68168cfa55bbe65'
    expected_kernel = 'bb0e231ec1a39abc5b1096413fab6cbd3c68ce2934b7e4ba82fbfb2566b6fe9d'
    expected_runners = {False: 'c7ee208101625399ad82ba0ef50b90a68b22e5096abc11b8fc3950d7c7b0f82a',
                        True: '081192626d365b72a1ee29a929bbc1c0dd5c2a2354800105bd7fe4efb22b5373'}
    errors, rows, prior = [], [], {}
    def check(condition, label):
        if not condition:
            errors.append(label)
    check(chash == expected_config, 'frozen config hash')
    for new, source in [(False, old_source), (True, new_source)]:
        for name, expected in [('config.json', expected_config), ('hnc_resumable.py', expected_kernel),
                               ('run_segment.py', expected_runners[new])]:
            check(sha(source / name) == expected, f'source hash {source.name}/{name}')
    axes = [np.asarray(config[k]) for k in ['alphas', 'betas']]
    shape = tuple(len(x) for x in axes)
    check(len(set(json.dumps(t, sort_keys=True) for t in config['tasks'])) == len(config['tasks']), 'unique tasks')
    steps = [65536, 262144, 1048576] + ([4194304] if args.final else [])
    for si, step in enumerate(steps):
        new = step > 262144
        root = base / ('million-6497438' if new else 'horizon-6497215')
        check(sha(root / 'config.json') == chash, f'run config {root.name}')
        ownership, hosts = {}, collections.Counter()
        for rank, task in enumerate(config['tasks']):
            tag = f'{rank}/{step}'
            directory = root / f'rank-{rank:03d}' / f'step-{step:09d}'
            try:
                receipt_path = directory / 'receipt.json'
                receipt = json.loads(receipt_path.read_text())
                expected = dict(status='COMPLETE', rank=rank, task=task, stop=step,
                                start=steps[si-1] if si else 0, horizon=config['horizon'],
                                config_sha256=chash, harness_sha256=expected_kernel,
                                runner_sha256=expected_runners[new],
                                job='6497438' if new else '6497215')
                for key, value in expected.items():
                    check(receipt.get(key) == value, f'receipt {tag}/{key}')
                for name, field in [('grid.npz', 'grid_sha256'), ('checkpoint.pt', 'checkpoint_sha256')]:
                    check(sha(directory / name) == receipt.get(field), f'file hash {tag}/{name}')
                check(receipt.get('previous_receipt_sha256') == (prior[rank]['hash'] if rank in prior else None),
                      f'previous receipt chain {tag}')
                check(receipt.get('visible_gpu_count') == 1, f'visible device count {tag}')
                if new:
                    uuid = receipt.get('gpu_uuid')
                    check(isinstance(uuid, str) and len(uuid) >= 32, f'missing physical UUID {tag}')
                    check(uuid not in ownership, f'duplicate physical UUID {tag}')
                    ownership[uuid] = rank
                    hosts[receipt['host']] += 1
                with np.load(directory / 'grid.npz', allow_pickle=False) as z:
                    grid = {k: z[k] for k in z.files}
                for key, axis in zip(['alpha', 'beta'], axes):
                    check(np.array_equal(grid[key], axis), f'axis {tag}/{key}')
                for key in ['escaped', 'max_abs', 'first_escape_step', 'lyapunov_per_step', 'lyapunov_blocks']:
                    check(grid[key].shape == shape, f'shape {tag}/{key}')
                    check(np.isfinite(grid[key]).all(), f'finite {tag}/{key}')
                escaped, first = grid['escaped'], grid['first_escape_step']
                check(escaped.dtype == np.bool_, f'escape mask type {tag}')
                check(np.array_equal(escaped, first > 0), f'escape flags {tag}')
                check(np.all(first[~escaped] == -1) and np.all(first[escaped] <= step), f'escape times {tag}')
                check(np.all(grid['lyapunov_blocks'] >= 0), f'Lyapunov block counts {tag}')
                stable = (~escaped) & (grid['lyapunov_per_step'] <= 1e-4) & (grid['lyapunov_blocks'] > 0)
                fraction = stable.mean(axis=0)
                one = np.flatnonzero(grid['beta'] == 1.)
                check(len(one) == 1, f'exact beta=1 column {tag}')
                row = dict(rank=rank, step=step, parameters=task, escaped=int(escaped.sum()),
                           stable=int(stable.sum()), stable_at_beta_1=int(stable[:, one].sum()),
                           tested_at_beta_1=len(axes[0]), **boundaries(grid['beta'], fraction),
                           stable_fraction_by_beta=fraction.tolist(), beta=grid['beta'].tolist(),
                           bounded_without_valid_lyapunov=int(((~escaped) & (grid['lyapunov_blocks'] == 0)).sum()),
                           elapsed_seconds=receipt['elapsed_seconds'], peak_allocated_bytes=receipt['peak_allocated_bytes'],
                           host=receipt['host'], physical_gpu_uuid=receipt.get('gpu_uuid'))
                if rank in prior:
                    previous = prior[rank]
                    check(not np.any(previous['escaped'] & (~escaped)), f'escape reversal {tag}')
                    check(np.array_equal(previous['first'][previous['escaped']], first[previous['escaped']]),
                          f'changed first escape {tag}')
                    row['late_escapes'] = int(((~previous['escaped']) & escaped).sum())
                    row['stable_to_unstable'] = int((previous['stable'] & (~stable)).sum())
                prior[rank] = dict(hash=sha(receipt_path), escaped=escaped, first=first, stable=stable)
                rows.append(row)
            except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
                errors.append(f'{tag}: {type(exc).__name__}: {exc}')
        if new:
            check(len(ownership) == len(config['tasks']), f'physical GPU coverage {step}')
            check(len(hosts) == 9 and all(n == 4 for n in hosts.values()), f'nine hosts/four workers {step}')
    summaries = []
    for step in steps:
        subset = [r for r in rows if r['step'] == step]
        bs = [r['boundary'] for r in subset if r['boundary'] is not None]
        summaries.append(dict(step=step, expected_cells=len(config['tasks']), cells=len(subset),
                              boundary_median=float(np.median(bs)) if bs else None,
                              boundary_range=[min(bs), max(bs)] if bs else None,
                              bounded_boundary_cells=len(bs),
                              **{k: sum(r.get(k, 0) for r in subset) for k in
                                 ['escaped', 'stable', 'late_escapes', 'stable_at_beta_1', 'tested_at_beta_1',
                                  'stable_to_unstable', 'bounded_without_valid_lyapunov']}))
    return dict(schema='hnc-extension-audit/v1', status='PASS' if not errors else 'FAIL', errors=errors,
                audited_steps=steps, config_sha256=chash, auditor_sha256=sha(__file__), rows=rows, summary=summaries,
                verification='Receipt identities, source/result/checkpoint byte hashes, previous receipt chains, grid consistency and new-run physical UUID uniqueness. Checkpoint tensor semantics are not independently recomputed.',
                historical_uuid_attribution='Not collected in job 6497215; not retroactively claimed.',
                interpretation='Finite-horizon numerical outcomes. First downward 50% crossings within the fine grid only; all crossings retained. Medians are descriptive, not pooled confidence limits or asymptotic stability proof.')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--base', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--final', action='store_true')
    args = p.parse_args()
    report = run(args)
    with pathlib.Path(args.output).open('x', encoding='utf-8', newline='\n') as f:
        json.dump(report, f, indent=2, allow_nan=False)
    print(json.dumps({k: v for k, v in report.items() if k != 'rows'}, indent=2))
    raise SystemExit(0 if report['status'] == 'PASS' else 1)
