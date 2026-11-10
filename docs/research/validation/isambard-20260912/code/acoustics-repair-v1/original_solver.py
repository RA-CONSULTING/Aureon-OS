#!/usr/bin/env python3
"""King's Chamber Helmholtz eigenmode solver (A5 validation, kimi-validation).

Methods:
- Explicit 7-point cell-centered FD Laplacian in CSR (Neumann graph-Laplacian;
  optional Dirichlet faces) solved by a small in-house block LOBPCG
  (Rayleigh-Ritz on [X, M*R], QR orthonormalization with rank dropping).
  The exact constant null vector is prepended to the initial block.
- Independent spectral Galerkin cross-check for the coffer geometry: box-mode
  basis with closed-form integrals over the coffer sub-region, dense
  generalized eigh.
Certification: per-mode relative residuals; bare-box runs must match the exact
discrete-analytic eigenvalues; coffer FD must match Galerkin.

Tasks:
  bare:<dx> / coffer:<dx> / opening:<dx> / random-check:<dx> / galerkin / controls
Claim geometry 10.47 x 5.23 x 5.97 m, c = 343 m/s.
"""
import json, os, sys, time, platform, warnings
import numpy as np
import scipy
import scipy.sparse as sp
import scipy.linalg as sla

C_AIR = 343.0
LX, LY, LZ = 10.47, 5.23, 5.97
K_EIG = 26
TOL = 1e-8          # relative-residual target
TOL_ACCEPT = 1e-3   # gates need ~1e-3; Ritz-value error ~ residual^2
MAXIT = 40

# ---------------------------------------------------------------- FD operator
def make_matrix(hx, hy, hz, active, dchr):
    act = active; dc = dchr
    shape = act.shape
    N = int(act.sum())
    idx = -np.ones(shape, dtype=np.int64); idx[act] = np.arange(N)
    h2 = (hx*hx, hy*hy, hz*hz)
    rows = []; cols = []; dat = []
    diag = np.zeros(N)
    for a in range(3):
        lo = [slice(None)]*3; hi = [slice(None)]*3
        lo[a] = slice(0, -1); hi[a] = slice(1, None)
        lo = tuple(lo); hi = tuple(hi)
        aa_lo = act[lo]; aa_hi = act[hi]
        both = aa_lo & aa_hi
        il = idx[lo][both]; ih = idx[hi][both]
        w = np.full(il.shape, 1.0/h2[a])
        rows += [il, ih, il, ih]; cols += [ih, il, il, ih]
        dat += [-w, -w, w, w]
        ad = aa_lo & dc[hi]; da = dc[lo] & aa_hi
        diag[idx[lo][ad]] += 1.0/h2[a]
        diag[idx[hi][da]] += 1.0/h2[a]
    A = sp.coo_matrix((np.concatenate(dat), (np.concatenate(rows), np.concatenate(cols))), shape=(N, N)).tocsr()
    A = A + sp.diags(diag)
    d = np.asarray(A.diagonal())
    return A, d, idx, N

# ---------------------------------------------------------------- LOBPCG-lite
def qr_drop(V, eps=1e-11):
    """Orthonormalize columns, dropping (near-)dependent ones."""
    if V.size == 0:
        return V
    nrm = np.linalg.norm(V, axis=0)
    V = V[:, nrm > 0]
    if V.shape[1] == 0:
        return V[:, :0]
    Q, R = np.linalg.qr(V, mode='reduced')
    keep = np.abs(np.diag(R)) > eps*np.maximum(1.0, np.abs(R).max())
    Q = Q[:, keep]
    return Q

def my_lobpcg(A, diag, X, k, tol=TOL, maxiter=MAXIT, grow=False):
    """Block LOBPCG (no P block; RR on [X, W]) with per-mode residuals.
    grow=True keeps the full enlarged subspace (small problems: superlinear
    convergence, used for the random-guess bias-guard run).
    Returns (eigvals ascending, eigvecs, rel_resid, n_iter)."""
    N = X.shape[0]
    X = qr_drop(X)
    AX = A @ X
    it = 0
    for it in range(maxiter):
        G = X.T @ AX
        G = 0.5*(G + G.T)
        lam, S = sla.eigh(G)
        X = X @ S; AX = AX @ S
        R = AX - X*lam[None, :]
        relres = np.linalg.norm(R, axis=0)/np.maximum(np.abs(lam), 1e-4)
        # converged modes are locked out of W
        act = relres > tol
        if not np.any(act):
            break
        W = R[:, act] / diag[:, None]          # Jacobi preconditioner
        W = W - X @ (X.T @ W)
        W = qr_drop(W)
        if W.shape[1] == 0:
            break
        AW = A @ W
        Z = qr_drop(np.hstack([X, W]))
        AZ = A @ Z
        G2 = Z.T @ AZ; G2 = 0.5*(G2 + G2.T)
        lam2, S2 = sla.eigh(G2)
        take = Z.shape[1] if grow else min(k + 3, Z.shape[1])
        X = Z @ S2[:, :take]
        AX = AZ @ S2[:, :take]
    G = X.T @ AX; G = 0.5*(G + G.T)
    lam, S = sla.eigh(G)
    X = X @ S; AX = AX @ S
    R = AX - X*lam[None, :]
    relres = np.linalg.norm(R, axis=0)/np.maximum(np.abs(lam), 1e-4)
    return lam, X, relres, it + 1

# ---------------------------------------------------------------- geometry
def grid_for(dx):
    nx = int(np.ceil(LX/dx)); ny = int(np.ceil(LY/dx)); nz = int(np.ceil(LZ/dx))
    return nx, ny, nz, LX/nx, LY/ny, LZ/nz

def add_coffer(act, hx, hy, hz):
    x1, x2 = 0.30, 2.58; y1, y2 = 0.62, 1.60; z2 = 1.05
    i1 = int(np.ceil(x1/hx)); i2 = int(np.floor(x2/hx))
    j1 = int(np.ceil(y1/hy)); j2 = int(np.floor(y2/hy))
    k2 = int(np.floor(z2/hz))
    act[i1:i2+1, j1:j2+1, 0:k2+1] = False
    return act

# ---------------------------------------------------------------- analytic
def analytic_modes(lx, ly, lz, fmax=60.0):
    out = []
    lm = int(2*fmax*lx/C_AIR)+1; mm = int(2*fmax*ly/C_AIR)+1; nm = int(2*fmax*lz/C_AIR)+1
    for l in range(lm+1):
        for m in range(mm+1):
            for n in range(nm+1):
                f = (C_AIR/2.0)*np.sqrt((l/lx)**2 + (m/ly)**2 + (n/lz)**2)
                if f > 0.1 or (l == m == n == 0):
                    out.append((float(f), l, m, n))
    out.sort()
    return out

def discrete_analytic(nx, ny, nz, hx, hy, hz, count):
    lam = np.zeros((nx, ny, nz))
    lam += (4/hx**2*np.sin(np.arange(nx)*np.pi/(2*nx))**2)[:, None, None]
    lam += (4/hy**2*np.sin(np.arange(ny)*np.pi/(2*ny))**2)[None, :, None]
    lam += (4/hz**2*np.sin(np.arange(nz)*np.pi/(2*nz))**2)[None, None, :]
    f = C_AIR/(2*np.pi)*np.sqrt(lam.ravel())
    f = np.sort(f[(f > 0.1) & (f < 60.0)])
    return [float(x) for x in f[:count]]

def guess_block(nx, ny, nz, idx, count):
    modes = []
    for l in range(9):
        for m in range(9):
            for n in range(9):
                f = (C_AIR/2.0)*np.sqrt((l/LX)**2 + (m/LY)**2 + (n/LZ)**2)
                if f > 0.1:
                    modes.append((f, l, m, n))
    modes.sort(); modes = modes[:count]
    ii, jj, kk = np.meshgrid(np.arange(nx), np.arange(ny), np.arange(nz), indexing='ij')
    cols = [np.ones(int((idx >= 0).sum()))]
    for _, l, m, n in modes:
        v = np.cos(np.pi*l*(ii+0.5)/nx)*np.cos(np.pi*m*(jj+0.5)/ny)*np.cos(np.pi*n*(kk+0.5)/nz)
        cols.append(v[idx >= 0])
    return np.column_stack(cols)

# ---------------------------------------------------------------- Galerkin (coffer)
def _cc_tab(lmax, a, b, L):
    """Table T[i,j] = ∫_a^b cos(i pi x/L) cos(j pi x/L) dx, i,j = 0..lmax."""
    i = np.arange(lmax+1)[:, None].astype(float)
    j = np.arange(lmax+1)[None, :].astype(float)
    sb = lambda q: np.sin(q*np.pi*b/L); sa = lambda q: np.sin(q*np.pi*a/L)
    dm = np.where(i == j, 1.0, i - j)          # safe denom
    ps = np.where(i + j == 0, 1.0, i + j)      # safe denom
    term_m = np.where(i != j, (sb(i-j) - sa(i-j))*L/(2*dm*np.pi), 0.0)
    term_p = np.where(i + j > 0, (sb(ps) - sa(ps))*L/(2*ps*np.pi), 0.0)
    diag = (b-a)/2 + np.where(i > 0, (sb(2*i) - sa(2*i))*L/(4*np.maximum(i, 1)*np.pi), 0.0)
    out = term_m + term_p
    out = np.where((i == j), diag, out)
    out = np.where((i == 0) & (j == 0), b - a, out)
    return out

def _ss_tab(lmax, a, b, L):
    """Table T[i,j] = ∫_a^b sin(i pi x/L) sin(j pi x/L) dx."""
    i = np.arange(lmax+1)[:, None].astype(float)
    j = np.arange(lmax+1)[None, :].astype(float)
    sb = lambda q: np.sin(q*np.pi*b/L); sa = lambda q: np.sin(q*np.pi*a/L)
    dm = np.where(i == j, 1.0, i - j)
    ps = np.where(i + j == 0, 1.0, i + j)
    out = np.where(i != j, (sb(i-j) - sa(i-j))*L/(2*dm*np.pi) - (sb(ps) - sa(ps))*L/(2*ps*np.pi), 0.0)
    diag = (b-a)/2 - np.where(i > 0, (sb(2*i) - sa(2*i))*L/(4*np.maximum(i, 1)*np.pi), 0.0)
    out = np.where((i == j) & (i > 0), diag, out)
    return out

def galerkin_coffer(F_cut=450.0, coffer=(0.30, 2.58, 0.62, 1.60, 0.0, 1.05)):
    modes = analytic_modes(LX, LY, LZ, fmax=F_cut)   # includes (0,0,0)
    nb = len(modes)
    lam = np.array([(2*np.pi*f/C_AIR)**2 for f, *_ in modes])
    li = np.array([m[1] for m in modes]); mi = np.array([m[2] for m in modes]); ni = np.array([m[3] for m in modes])
    x1, x2, y1, y2, z1, z2 = coffer
    V = LX*LY*LZ
    Nv = np.sqrt(2.0**((li > 0) + (mi > 0) + (ni > 0))/V)
    NN = Nv[:, None]*Nv[None, :]
    ccx = _cc_tab(li.max(), x1, x2, LX); ccy = _cc_tab(mi.max(), y1, y2, LY); ccz = _cc_tab(ni.max(), z1, z2, LZ)
    ssx = _ss_tab(li.max(), x1, x2, LX); ssy = _ss_tab(mi.max(), y1, y2, LY); ssz = _ss_tab(ni.max(), z1, z2, LZ)
    ix = np.ix_(li, li); iy = np.ix_(mi, mi); iz = np.ix_(ni, ni)
    CCx = ccx[ix]; CCy = ccy[iy]; CCz = ccz[iz]
    Mc = NN*CCx*CCy*CCz
    Kc = NN*((np.pi/LX)**2*(li[:, None]*li[None, :])*ssx[ix]*CCy*CCz
             + (np.pi/LY)**2*(mi[:, None]*mi[None, :])*CCx*ssy[iy]*CCz
             + (np.pi/LZ)**2*(ni[:, None]*ni[None, :])*CCx*CCy*ssz[iz])
    A = np.diag(lam) - Kc
    M = np.eye(nb) - Mc
    A = 0.5*(A + A.T); M = 0.5*(M + M.T)
    w2, Vv = sla.eigh(A, M)
    f = C_AIR/(2*np.pi)*np.sqrt(np.maximum(w2, 0.0))
    return f, modes, w2

def run_galerkin():
    t0 = time.time()
    out = {'task': 'galerkin', 'wall_s': None}
    # sanity: zero-size coffer must recover box modes
    f0, m0, _ = galerkin_coffer(F_cut=120.0, coffer=(0, 0, 0, 0, 0, 0))
    box = np.array([f for f, *_ in analytic_modes(LX, LY, LZ, fmax=120.0)])
    g = np.sort(np.array(f0))
    n = min(len(g), len(box))
    out['sanity_empty_coffer_max_reldiff'] = float(np.max(np.abs(g[1:n]-box[1:n])/box[1:n])) if n > 1 else None
    for Fcut in (200.0, 300.0, 380.0):
        f, modes, w2 = galerkin_coffer(F_cut=Fcut)
        fs = sorted(float(x) for x in f if 0.5 < x < 120.0)
        out[f'coffer_Fcut{int(Fcut)}'] = {
            'n_basis': len(modes),
            'freqs_hz': fs[:K_EIG],
        }
    out['wall_s'] = time.time()-t0
    return out

# ---------------------------------------------------------------- FD eigen run
def run_eigen(task, dx):
    t0 = time.time()
    nx, ny, nz, hx, hy, hz = grid_for(dx)
    if task in ('bare', 'random-check'):
        act = np.ones((nx, ny, nz), bool); dc = np.zeros((nx, ny, nz), bool)
    elif task == 'coffer':
        act = np.ones((nx, ny, nz), bool); dc = np.zeros((nx, ny, nz), bool)
        act = add_coffer(act, hx, hy, hz)
    elif task == 'opening':
        ex = int(np.ceil(1.5/hx)); nX = nx + ex
        act = np.zeros((nX, ny, nz), bool); act[:nx] = True
        dc = np.zeros((nX, ny, nz), bool)
        act = add_coffer(act, hx, hy, hz)
        j1 = int(np.ceil((LY-1.05)/hy)); j2 = int(np.floor(LY/hy)) - 1
        k2 = int(np.floor(1.10/hz)) - 1
        act[nx:, j1:j2+1, 0:k2+1] = True
        act[nX-1, j1:j2+1, 0:k2+1] = False
        dc[nX-1, j1:j2+1, 0:k2+1] = True
    else:
        raise ValueError(task)
    A, diag, idx, N = make_matrix(hx, hy, hz, act, dc)
    if task == 'random-check':
        rng = np.random.default_rng(1)
        X = np.column_stack([np.ones(N), rng.standard_normal((N, K_EIG))])
    else:
        X = guess_block(act.shape[0], ny, nz, idx, K_EIG)
    maxiter = 300 if task == 'random-check' else MAXIT
    lam, V, relres, niter = my_lobpcg(A, diag, X, K_EIG + 1, tol=TOL, maxiter=maxiter, grow=False)
    freqs = C_AIR/(2*np.pi)*np.sqrt(np.maximum(lam, 0.0))
    keep = freqs > 0.5
    out = {
        'task': task, 'dx_target': dx, 'grid_shape': list(act.shape),
        'h': [hx, hy, hz], 'n_cells': N, 'k_requested': K_EIG,
        'n_iter': niter,
        'wall_s': time.time()-t0, 'host': platform.node(),
        'numpy': np.__version__, 'scipy': scipy.__version__,
        'freqs_hz': [float(f) for f in freqs[keep]][:K_EIG],
        'resid_rel': [float(r) for r, k_ in zip(relres, keep) if k_][:K_EIG],
        'max_resid_rel': float(np.max(relres[keep])) if np.any(keep) else None,
    }
    if task in ('bare', 'random-check'):
        out['discrete_analytic_hz'] = discrete_analytic(nx, ny, nz, hx, hy, hz, K_EIG)
        ca = analytic_modes(LX, LY, LZ, fmax=120.0)
        ca = [m for m in ca if m[0] > 0.1]
        out['continuum_analytic_hz'] = [f for f, *_ in ca[:K_EIG]]
        out['continuum_analytic_lmn'] = [[l, m, n] for _, l, m, n in ca[:K_EIG]]
    return out

# ---------------------------------------------------------------- controls
SCH = np.array([7.83, 14.3, 20.8, 27.3, 33.8])

def room_modes(lx, ly, lz, fmax=60.0):
    return [f for f, l, m, n in analytic_modes(lx, ly, lz, fmax=fmax) if f > 0.1]

def room_stats(lx, ly, lz):
    modes = np.array(room_modes(lx, ly, lz))
    r = {}
    for tol, key in ((0.02, '2pct'), (0.01, '1pct')):
        r['hit16_'+key] = bool(np.any(np.abs(modes-16.2) <= tol*16.2))
        r['hit32_'+key] = bool(np.any(np.abs(modes-32.4) <= tol*32.4))
    r['min_rel_16'] = float(np.min(np.abs(modes-16.2)/16.2))
    r['min_rel_32'] = float(np.min(np.abs(modes-32.4)/32.4))
    r['schumann_min_rel'] = float(np.min(np.abs(modes[:, None]-SCH[None, :])/SCH[None, :]))
    return r

def run_controls():
    t0 = time.time()
    rng = np.random.default_rng(42)
    V0 = LX*LY*LZ
    n_target = 10000
    hit2 = hit1 = 0; n = 0; drawn = 0
    d16 = []; d32 = []; dsc = []
    while n < n_target:
        b = 20000
        lx = rng.uniform(6, 15, b); ly = rng.uniform(3, 8, b); lz = rng.uniform(3, 8, b)
        s = (V0/(lx*ly*lz))**(1/3)
        lx, ly, lz = lx*s, ly*s, lz*s
        ok = (lx >= 2)&(lx <= 20)&(ly >= 2)&(ly <= 20)&(lz >= 2)&(lz <= 20)
        drawn += b
        for a, bb, c in zip(lx[ok], ly[ok], lz[ok]):
            if n >= n_target: break
            st = room_stats(a, bb, c)
            hit2 += st['hit16_2pct'] and st['hit32_2pct']
            hit1 += st['hit16_1pct'] and st['hit32_1pct']
            d16.append(st['min_rel_16']); d32.append(st['min_rel_32']); dsc.append(st['schumann_min_rel'])
            n += 1
    det = []
    for dx_ in (-.05, -.03, -.02, -.01, 0, .01, .02, .03, .05):
        for dy_ in (-.05, -.03, -.02, -.01, 0, .01, .02, .03, .05):
            for dz_ in (-.05, -.03, -.02, -.01, 0, .01, .02, .03, .05):
                a, bb, c = LX*(1+dx_), LY*(1+dy_), LZ*(1+dz_)
                st = room_stats(a, bb, c)
                st['d'] = [dx_, dy_, dz_]
                st['f100'] = (C_AIR/2)/a; st['f010'] = (C_AIR/2)/bb; st['f001'] = (C_AIR/2)/c
                det.append(st)
    ch = room_stats(LX, LY, LZ)
    ch_modes = room_modes(LX, LY, LZ)
    ch_md = np.array(ch_modes)
    ch_sch_dists = [float(np.min(np.abs(m-SCH)/SCH)) for m in ch_md]
    return {
        'task': 'controls', 'wall_s': time.time()-t0,
        'volume_m3': V0, 'null_n': n, 'null_drawn': drawn, 'seed': 42,
        'p_null_hit_both_2pct': hit2/n, 'p_null_hit_both_1pct': hit1/n,
        'null_min_rel_dist_16_median': float(np.median(d16)),
        'null_min_rel_dist_32_median': float(np.median(d32)),
        'null_schumann_min_rel_median': float(np.median(dsc)),
        'null_schumann_min_rel_q10': float(np.quantile(dsc, 0.10)),
        'null_schumann_min_rel_all': [float(x) for x in dsc],
        'null_min_rel_16_all': [float(x) for x in d16],
        'null_min_rel_32_all': [float(x) for x in d32],
        'detune_hit_both_2pct': sum(1 for d in det if d['hit16_2pct'] and d['hit32_2pct']),
        'detune_hit_both_1pct': sum(1 for d in det if d['hit16_1pct'] and d['hit32_1pct']),
        'detune_n': len(det), 'detune': det,
        'chamber_stats': ch, 'chamber_modes_analytic': ch_modes[:26],
        'chamber_modes_schumann_dists': ch_sch_dists[:26],
    }

def run_dense_check(dx):
    """Post-hoc supplementary validation S1: dense LAPACK eigensolve of the
    assembled FD operator (zero iterative-solver assumptions)."""
    t0 = time.time()
    nx, ny, nz, hx, hy, hz = grid_for(dx)
    act = np.ones((nx, ny, nz), bool); dc = np.zeros((nx, ny, nz), bool)
    A, diag, idx, N = make_matrix(hx, hy, hz, act, dc)
    w = np.linalg.eigvalsh(A.toarray())
    f = C_AIR/(2*np.pi)*np.sqrt(np.maximum(w, 0.0))
    f = np.sort(f[(f > 0.1) & (f < 60.0)])
    da = discrete_analytic(nx, ny, nz, hx, hy, hz, len(f))
    n = min(len(f), len(da))
    return {'task': 'dense-check', 'dx_target': dx, 'n_cells': N,
            'wall_s': time.time()-t0, 'host': platform.node(),
            'dense_freqs_hz': [float(x) for x in f[:K_EIG]],
            'discrete_analytic_hz': da,
            'max_rel_diff_vs_discrete_analytic': float(np.max(np.abs(np.array(f[:n])-np.array(da[:n]))/np.array(da[:n])))}

if __name__ == '__main__':
    spec = sys.argv[1]
    outdir = sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    if spec == 'controls':
        out = run_controls(); name = 'controls.json'
    elif spec == 'galerkin':
        out = run_galerkin(); name = 'galerkin.json'
    elif spec.startswith('dense-check'):
        task, dxs = spec.split(':'); dx = float(dxs)
        out = run_dense_check(dx); name = f'dense-check-{dxs}.json'
    else:
        task, dxs = spec.split(':'); dx = float(dxs)
        out = run_eigen(task, dx)
        name = f'{task}-{dxs}.json'
    p = os.path.join(outdir, name)
    with open(p, 'w') as fh:
        json.dump(out, fh, indent=1)
    print('WROTE', p)
