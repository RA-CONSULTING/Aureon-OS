from pathlib import Path
import ast,json

out=Path('work/tandem-audit-v1');assert not (out/'inputs.sha256').exists()
pilot=Path('work/audit_tandem_pilot_local.py').read_text();tree=ast.parse(pilot)
function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='white')
(out/'independent_channels.py').write_bytes(('"""Separate scalar Kalman implementation; verified against dense covariance."""\nimport math\nimport numpy as np\n\n'+ast.get_source_segment(pilot,function)+'\n').encode())
(out/'full-submission.json').write_bytes(Path('outputs/tandem-repair-full-submission-v1.json').read_bytes())
(out/'config.json').write_bytes(Path('work/tandem-repair-v1/config.json').read_bytes())
(out/'PROTOCOL.md').write_bytes(Path('work/tandem-repair-v1/PROTOCOL.md').read_bytes())
base='/projects/u6vs/hnc-organism';remote=base+'/expansion-20260912/tandem-audit-v1'
batch=f'''#!/bin/bash
#SBATCH --job-name=tandem-repair-audit
#SBATCH --account=brics.u6vs
#SBATCH --partition=workq
#SBATCH --nodes=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=12G
#SBATCH --time=00:30:00
#SBATCH --no-requeue
#SBATCH --output={remote}/audit-%j.out
#SBATCH --error={remote}/audit-%j.err
set -euo pipefail
umask 007
cd {remote}
sha256sum -c inputs.sha256
sacct -j 6506231,6506293,6506509 -P -n -o JobIDRaw,State,ExitCode,ElapsedRaw,AllocNodes > accounting-$SLURM_JOB_ID.psv
export APPTAINERENV_OMP_NUM_THREADS=1 APPTAINERENV_OPENBLAS_NUM_THREADS=1 APPTAINERENV_PYTHONDONTWRITEBYTECODE=1
BASE={base}
IMAGE=$BASE/containers/pytorch-25.05-py3.sif
apptainer exec --cleanenv --bind "$BASE:$BASE" "$IMAGE" python test_analysis.py > tests-$SLURM_JOB_ID.json
apptainer exec --cleanenv --bind "$BASE:$BASE" "$IMAGE" python run_audit.py accounting-$SLURM_JOB_ID.psv
'''
(out/'audit.sbatch').write_bytes(batch.encode())
for p in out.glob('*.py'):compile(p.read_text(),str(p),'exec')
print(json.dumps(dict(files=len(list(out.iterdir())),prepared=True)))
