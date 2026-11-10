#!/bin/bash
#SBATCH --job-name=stage1-error-export
#SBATCH --account=brics.u6vs
#SBATCH --partition=workq
#SBATCH --nodes=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output=/projects/u6vs/hnc-organism/expansion-20260912/stage1-diagnostics-v1/diagnostics-%j.out
#SBATCH --error=/projects/u6vs/hnc-organism/expansion-20260912/stage1-diagnostics-v1/diagnostics-%j.err
set -euo pipefail
cd /projects/u6vs/hnc-organism/expansion-20260912/stage1-diagnostics-v1
sha256sum -c inputs.sha256
apptainer exec --cleanenv --bind /projects/u6vs/hnc-organism:/projects/u6vs/hnc-organism /projects/u6vs/hnc-organism/containers/pytorch-25.05-py3.sif python diagnose_stage1.py
