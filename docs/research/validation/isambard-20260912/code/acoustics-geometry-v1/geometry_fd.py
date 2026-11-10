"""Converged FD geometry follow-up; original grid and geometry conventions preserved."""
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


def matrix_for(geometry, dx):
    nx,ny,nz,hx,hy,hz=s.grid_for(dx)
    if geometry=='coffer':
        active=np.ones((nx,ny,nz),bool)
        active=s.add_coffer(active,hx,hy,hz)
        release=np.zeros_like(active)
    else:
        extra=int(np.ceil(1.5/hx)); total=nx+extra
        active=np.zeros((total,ny,nz),bool); active[:nx]=True
        release=np.zeros_like(active)
        active=s.add_coffer(active,hx,hy,hz)
        j1=int(np.ceil((s.LY-1.05)/hy)); j2=int(np.floor(s.LY/hy))-1
        k2=int(np.floor(1.10/hz))-1
        active[nx:,j1:j2+1,:k2+1]=True
        active[total-1,j1:j2+1,:k2+1]=False
        release[total-1,j1:j2+1,:k2+1]=True
    matrix,_,_,n=s.make_matrix(hx,hy,hz,active,release)
    return matrix,active,[hx,hy,hz],n


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--geometry',choices=['coffer','opening'],required=True)
    p.add_argument('--dx',type=float,required=True)
    p.add_argument('--output',required=True)
    a=p.parse_args(); started=time.monotonic()
    matrix,active,h,n=matrix_for(a.geometry,a.dx)
    diff=matrix-matrix.T
    assert diff.nnz==0 or np.max(np.abs(diff.data))<1e-12
    k=27 if a.geometry=='coffer' else 26
    lam,vec=eigsh(matrix,k=k,sigma=-.01,which='LM',
                  v0=np.random.default_rng(1).standard_normal(n),ncv=60,maxiter=3000,tol=1e-11)
    order=np.argsort(lam); lam=lam[order]; vec=vec[:,order]
    residual=np.linalg.norm(matrix@vec-vec*lam[None,:],axis=0)
    f=s.C_AIR/(2*np.pi)*np.sqrt(np.maximum(lam,0))
    keep=f>.1; f=f[keep]; relative=residual[keep]/np.abs(lam[keep])
    checks=dict(count=len(f)==26,finite=bool(np.isfinite(f).all() and np.isfinite(relative).all()),
                nonnegative=bool(lam.min()>-1e-8),relative_residual=bool(relative.max()<=1e-8),
                orthogonal=bool(np.linalg.norm(vec.T@vec-np.eye(k),ord=2)<=1e-8))
    root=pathlib.Path(__file__).parent
    sha=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
    r=dict(schema='acoustics-geometry-repair/v1',status='PASS' if all(checks.values()) else 'FAIL',
           checks=checks,geometry=a.geometry,dx=a.dx,n_cells=n,grid_shape=list(active.shape),h=h,
           seed=1,frequencies_hz=f.tolist(),relative_residuals=relative.tolist(),
           max_relative_residual=float(relative.max()),host=platform.node(),job=os.environ.get('SLURM_JOB_ID'),
           wall_seconds=time.monotonic()-started,numpy=np.__version__,scipy=scipy.__version__,
           runner_sha256=sha(__file__),solver_sha256=sha(s.__file__),amendment_sha256=sha(root/'GEOMETRY_AMENDMENT.json'),
           operator_sha256=hashlib.sha256(matrix.data.tobytes()+matrix.indices.tobytes()+matrix.indptr.tobytes()).hexdigest(),
           historical_verdict_unchanged='INCONCLUSIVE')
    with pathlib.Path(a.output).open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(r,stream,indent=2,allow_nan=False)
    print(json.dumps(r,indent=2))
    if r['status']!='PASS':raise SystemExit(1)
