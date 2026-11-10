"""Versioned follow-up; writes new receipts and does not amend historical verdicts."""
import argparse
import hashlib
import json
import os
import pathlib
import platform
import time

import numpy as np
import scipy
from scipy.sparse.linalg import eigsh
import repaired_solver as s


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def random_check(dx, seed):
    nx, ny, nz, hx, hy, hz = s.grid_for(dx)
    active = np.ones((nx, ny, nz), dtype=bool)
    matrix, diag, idx, n = s.make_matrix(hx, hy, hz, active, np.zeros_like(active))
    asym = matrix - matrix.T
    assert asym.nnz == 0 or np.max(np.abs(asym.data)) < 1e-12
    lam, vec = eigsh(matrix, k=27, sigma=-.01, which='LM',
                     v0=np.random.default_rng(seed).standard_normal(n),
                     tol=1e-11, maxiter=3000, ncv=60)
    order = np.argsort(lam)
    lam, vec = lam[order], vec[:, order]
    absres = np.linalg.norm(matrix @ vec - vec * lam[None, :], axis=0)
    frequencies = s.C_AIR / (2*np.pi) * np.sqrt(np.maximum(lam, 0))
    selected = frequencies > .1
    f = frequencies[selected]
    eig = lam[selected]
    residual = absres[selected] / np.abs(eig)
    exact_f = np.asarray(s.discrete_analytic(nx, ny, nz, hx, hy, hz, 26))
    exact_eig = (2*np.pi*exact_f/s.C_AIR)**2
    count_ok = len(f) == len(exact_f) == 26
    max_rel = float(np.max(np.abs(eig - exact_eig)/exact_eig)) if count_ok else None
    checks = dict(mode_count=count_ok, finite=bool(np.isfinite(lam).all() and np.isfinite(absres).all()),
                  relative_residual=bool(residual.max() <= 1e-8),
                  exact_eigenvalues=bool(count_ok and max_rel <= 1e-6),
                  orthogonality=bool(np.linalg.norm(vec.T @ vec-np.eye(27), ord=2) <= 1e-8))
    return dict(status='PASS' if all(checks.values()) else 'FAIL', checks=checks, seed=seed, dx=dx,
                grid_shape=[nx, ny, nz], n_cells=n, eigenvalues=eig.tolist(), frequencies_hz=f.tolist(),
                discrete_exact_frequencies_hz=exact_f.tolist(), relative_residuals=residual.tolist(),
                max_eigenvalue_relative_error=max_rel, zero_mode_absolute_residual=float(absres[0]),
                method='ARPACK shift-invert on assembled sparse operator, random initial vector',
                operator_sha256=hashlib.sha256(matrix.data.tobytes()+matrix.indices.tobytes()+matrix.indptr.tobytes()).hexdigest())


def gram_check():
    # Numerical integration independent of the code's closed-form coffer integrals.
    modes = np.array([[0,0,0], [1,0,0], [0,2,0], [1,1,0], [1,1,1], [2,1,3]])
    u, weight = np.polynomial.legendre.leggauss(80)
    gram = np.ones((len(modes), len(modes)))
    for axis, length in enumerate([s.LX, s.LY, s.LZ]):
        coords = (u+1)*length/2
        basis = np.cos(np.pi*modes[:, axis, None]*coords[None, :]/length)
        gram *= (basis * (weight*length/2)[None, :]) @ basis.T
    norm = s.basis_normalization(modes[:,0], modes[:,1], modes[:,2], s.LX*s.LY*s.LZ)
    gram *= norm[:,None]*norm[None,:]
    return float(np.max(np.abs(gram-np.eye(len(modes)))))


def selftest():
    error = gram_check()
    assert error < 1e-12, error
    for band in [60,120]:
        modes = s.analytic_modes(s.LX,s.LY,s.LZ,band)
        assert all(0 <= mode[0] <= band for mode in modes)
        assert len(set(mode[1:] for mode in modes)) == len(modes)
    trial = random_check(.8, 123)
    assert trial['status'] == 'PASS', trial
    return dict(status='PASS', numerical_gram_error=error, coarse_random_solver=trial)


def controls():
    out = s.run_controls()
    null = np.asarray(out['null_schumann_min_rel_all'])
    statistic = out['chamber_stats']['schumann_min_rel']
    better = int(np.count_nonzero(null <= statistic))
    out['corrected_schumann_comparison'] = dict(
        statistic='minimum relative distance from any 0.1<f<=60 Hz mode to the fixed Schumann set, once per room',
        chamber_value=statistic, null_at_least_as_close=better, null_rooms=len(null),
        empirical_fraction=better/len(null), plus_one_rank_p=(better+1)/(len(null)+1),
        interpretation='Calibration against the specified synthetic room generator; not a test of design intent. Replaces the invalid comparison of chamber modes with room-level minima.')
    out['status'] = 'COMPLETE'
    return out


def galerkin(cut):
    error = gram_check()
    assert error < 1e-12
    f0, modes0, _ = s.galerkin_coffer(F_cut=120, coffer=(0,0,0,0,0,0))
    f0 = f0[f0 > .1]
    exact = np.asarray([m[0] for m in modes0 if m[0] > .1])
    assert len(f0) == len(exact)
    empty_error = float(np.max(np.abs(f0-exact)/exact))
    f, modes, lam = s.galerkin_coffer(F_cut=cut)
    return dict(status='COMPLETE', cutoff_hz=cut, basis_size=len(modes),
                frequencies_hz=f[f>.1][:26].tolist(), minimum_eigenvalue=float(lam.min()),
                numerical_gram_error=error, empty_coffer_relative_error=empty_error,
                finite=bool(np.isfinite(f).all()))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('task', choices=['selftest','random','controls','galerkin'])
    p.add_argument('--seed', type=int, default=1)
    p.add_argument('--cutoff', type=int, default=200)
    p.add_argument('--output', required=True)
    a = p.parse_args()
    started = time.monotonic()
    if a.task == 'random':
        result = random_check(.2, a.seed)
    elif a.task == 'galerkin':
        result = galerkin(a.cutoff)
    else:
        result = {'selftest':selftest, 'controls':controls}[a.task]()
    result.update(schema='acoustics-repair-result/v1', task=a.task,
                  wall_seconds=time.monotonic()-started, host=platform.node(),
                  job=os.environ.get('SLURM_JOB_ID'), numpy=np.__version__, scipy=scipy.__version__,
                  solver_sha256=sha(s.__file__), runner_sha256=sha(__file__),
                  amendment_sha256=sha(pathlib.Path(__file__).with_name('AMENDMENT.json')),
                  historical_verdict_unchanged='INCONCLUSIVE')
    with pathlib.Path(a.output).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    print(json.dumps({k:v for k,v in result.items() if k not in ['null_schumann_min_rel_all','null_min_rel_16_all','null_min_rel_32_all','detune','coarse_random_solver']}, indent=2))
    if result['status'] == 'FAIL':
        raise SystemExit(1)
