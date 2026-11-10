#!/bin/bash
#SBATCH --job-name=tandem-repair-full
#SBATCH --account=brics.u6vs
#SBATCH --partition=workq
#SBATCH --nodes=8
#SBATCH --ntasks-per-node=4
#SBATCH --gpus-per-node=4
#SBATCH --cpus-per-task=8
#SBATCH --time=00:45:00
#SBATCH --no-requeue
#SBATCH --output=/projects/u6vs/hnc-organism/expansion-20260912/tandem-full-v1/full-%j.out
#SBATCH --error=/projects/u6vs/hnc-organism/expansion-20260912/tandem-full-v1/full-%j.err
set -euo pipefail
umask 007
cd /projects/u6vs/hnc-organism/expansion-20260912/tandem-full-v1
sha256sum -c inputs.sha256
cd /projects/u6vs/hnc-organism/expansion-20260912/tandem-repair-v1
test "$(sha256sum inputs.sha256 | cut -d' ' -f1)" = ecea7bc161a3c0daafa198758d13b7889ba144f8fd7a17472c1b7d670674016e
sha256sum -c inputs.sha256
test "$(sha256sum whiten-29331187f0a045df.so | cut -d' ' -f1)" = 9207b8f2e2410b707e67b397152b636dffac625ad4a7fc7077a7b44a1b30af3d
scontrol show job "$SLURM_JOB_ID" > /projects/u6vs/hnc-organism/expansion-20260912/tandem-full-v1/allocation-$SLURM_JOB_ID.txt
srun --gpus-per-task=1 --gpu-bind=single:1 --output=/projects/u6vs/hnc-organism/expansion-20260912/tandem-full-v1/full-%j-rank-%t.out --error=/projects/u6vs/hnc-organism/expansion-20260912/tandem-full-v1/full-%j-rank-%t.err bash /projects/u6vs/hnc-organism/expansion-20260912/tandem-full-v1/worker.sh
date -u +%Y-%m-%dT%H:%M:%SZ > /projects/u6vs/hnc-organism/expansion-20260912/tandem-full-v1/completed-$SLURM_JOB_ID.txt
