from pathlib import Path
import csv,datetime,hashlib,json

out=Path('work/tandem-full-v1');out.mkdir(exist_ok=True)
assert not (out/'inputs.sha256').exists(),'Frozen; do not modify'
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
path=Path('outputs/isambard-accounting-tandem-20260912.psv')
columns='job_id state exit_code start end elapsed_seconds allocated_nodes time_limit_minutes'.split()
rows=list(csv.DictReader(path.read_text(encoding='utf-8-sig').splitlines(),fieldnames=columns,delimiter='|'))
assert len(rows)>=500 and len({r['job_id'] for r in rows})==len(rows)
spent=sum(int(r['elapsed_seconds'])*int(r['allocated_nodes'])/3600 for r in rows)
reserved=0;active=[]
for r in rows:
    if r['state'] in ['RUNNING','PENDING','CONFIGURING','COMPLETING']:
        assert r['time_limit_minutes'].isdigit(),r
        nodes=max(1,int(r['allocated_nodes']))
        hours=max(0,int(r['time_limit_minutes'])*60-int(r['elapsed_seconds']))*nodes/3600
        reserved+=hours;active.append({**r,'remaining_physical_node_hour_ceiling':hours})
allocation=dict(observed_utc=now,scheduler_records=len(rows),scheduler_file_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),physical_node_hours_to_query=spent,active_remaining_physical_node_hour_ceiling=reserved,active_jobs=active,portal_last_observation=json.loads(Path('outputs/isambard-portal-observation-20260912.json').read_text()),new_full_ceiling_node_hours=6.,provisional_remainder_after_visible_usage_reservations_and_new_full=4992.53-spent-reserved-6.,boundary='Fresh scheduler accounting through this query, compared with the previously verified September opening balance. Full physical nodes conservatively counted even for partial-node jobs. Portal session expired; fresh portal balance awaits user sign-in. Not an exact current billed or spendable balance; no claim of coverage for invisible jobs, other clusters, or unobserved credit changes.')
assert allocation['provisional_remainder_after_visible_usage_reservations_and_new_full']>4000
Path('outputs/isambard-allocation-tandem-20260912.json').write_bytes((json.dumps(allocation,indent=2)+'\n').encode())
for src,name in [(path,path.name),(Path('outputs/isambard-allocation-tandem-20260912.json'),'allocation.json'),(Path('outputs/tandem-repair-pilot-6506293/remote-audit.json'),'pilot-remote-audit.json'),(Path('outputs/tandem-repair-pilot-6506293/local-audit.json'),'pilot-local-audit.json'),(Path('outputs/tandem-repair-pilot-6506293/tests-6506231.json'),'preflight.json')]:
    (out/name).write_bytes(src.read_bytes())
pilot=json.loads((out/'pilot-remote-audit.json').read_text());local=json.loads((out/'pilot-local-audit.json').read_text())
assert local['passed'] and local['arrays']==28 and local['archive_sha256']==pilot['archive_sha256']
assert pilot['projection_with_margin_seconds']<2700
protocol='''# Tandem full-wave launch record

This launcher uses the frozen tandem-repair-v1 experiment without changing its
source, hypotheses, output handling, trial identities or analysis plan.
The successful 6506231 preflight and all 28 receipts from pilot 6506293 have
passed source, array, identity and distinct-GPU checks. An independent local
scalar Kalman calculation reproduces saved sample scores. Pilot runtime gives
a 697.2-second full estimate and a 1645.8-second estimate including the declared
50% margin plus ten minutes. The hard limit is tightened from the protocol's
three-hour ceiling to 45 minutes: eight nodes, 32 GPUs, at most six node-hours.
No hypothesis or detection threshold was selected using pilot outcomes.

Allocation information was refreshed using current project scheduler records.
The prior portal balance retains its date and estimated labels; renewed portal
authentication awaits the user. The resource decision uses full physical-node
accounting plus active remaining ceilings and the new six-node-hour ceiling,
against the last verified September opening balance. This is a conservative
planning estimate conditional on no unobserved allocation changes, not a live
spendable-credit claim. See allocation.json for the exact evidence.

Every full result must be hash-audited and its statistics independently checked.
The pilot overlaps the first 512 production identities in cells 0,15,16,31 of
every stage. Those records remain in accounting but are excluded from inference.
The eligibility count is 2,308,096 of 2,322,432 generated full records.
Scheduler completion alone is not an experimental conclusion.
'''
(out/'LAUNCH.md').write_bytes(protocol.encode())
base='/projects/u6vs/hnc-organism';remote=base+'/expansion-20260912/tandem-full-v1';source=base+'/expansion-20260912/tandem-repair-v1';results=base+'/expansion-20260912/tandem-repair-results-v1'
worker=f'''#!/bin/bash
set -euo pipefail
BASE={base}
SRC={source}
export APPTAINERENV_SLURM_JOB_ID="${{SLURM_JOB_ID:?}}"
export APPTAINERENV_CUDA_VISIBLE_DEVICES="${{CUDA_VISIBLE_DEVICES:?}}"
export APPTAINERENV_OMP_NUM_THREADS=1 APPTAINERENV_OPENBLAS_NUM_THREADS=1 APPTAINERENV_PYTHONDONTWRITEBYTECODE=1 APPTAINERENV_CUBLAS_WORKSPACE_CONFIG=:4096:8
exec apptainer exec --nv --cleanenv --bind "$BASE:$BASE" "$BASE/containers/pytorch-25.05-py3.sif" python "$SRC/run_repair.py" --rank "${{SLURM_PROCID:?}}" --ranks 32 --output {results}
'''
(out/'worker.sh').write_bytes(worker.encode())
batch=f'''#!/bin/bash
#SBATCH --job-name=tandem-repair-full
#SBATCH --account=brics.u6vs
#SBATCH --partition=workq
#SBATCH --nodes=8
#SBATCH --ntasks-per-node=4
#SBATCH --gpus-per-node=4
#SBATCH --cpus-per-task=8
#SBATCH --time=00:45:00
#SBATCH --no-requeue
#SBATCH --output={remote}/full-%j.out
#SBATCH --error={remote}/full-%j.err
set -euo pipefail
umask 007
cd {remote}
sha256sum -c inputs.sha256
cd {source}
test "$(sha256sum inputs.sha256 | cut -d' ' -f1)" = ecea7bc161a3c0daafa198758d13b7889ba144f8fd7a17472c1b7d670674016e
sha256sum -c inputs.sha256
test "$(sha256sum whiten-29331187f0a045df.so | cut -d' ' -f1)" = 9207b8f2e2410b707e67b397152b636dffac625ad4a7fc7077a7b44a1b30af3d
scontrol show job "$SLURM_JOB_ID" > {remote}/allocation-$SLURM_JOB_ID.txt
srun --gpus-per-task=1 --gpu-bind=single:1 --output={remote}/full-%j-rank-%t.out --error={remote}/full-%j-rank-%t.err bash {remote}/worker.sh
date -u +%Y-%m-%dT%H:%M:%SZ > {remote}/completed-$SLURM_JOB_ID.txt
'''
(out/'full.sbatch').write_bytes(batch.encode())
print(json.dumps({k:v for k,v in allocation.items() if k not in ['portal_last_observation','active_jobs']},indent=2))
