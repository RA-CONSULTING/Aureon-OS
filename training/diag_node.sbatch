#!/bin/bash
# Find out why eval_baseline.sbatch exited 1 with an empty log.
#
# A batch script under `set -euo pipefail` that exits without writing a byte is
# not failing in a normal way: every guard would print something. This runs the
# same guards on a compute node, with xtrace merged into stdout, so the first
# failing step names itself.
#
#   sbatch training/diag_node.sbatch
#
#SBATCH --job-name=aureon-diag
#SBATCH --account=brics.u6vs
#SBATCH --partition=workq
#SBATCH --nodes=1
#SBATCH --gpus-per-node=4
#SBATCH --cpus-per-task=8
#SBATCH --mem=16000M
#SBATCH --time=00:10:00
#SBATCH --no-requeue
#SBATCH --output=/projects/u6vs/hnc-organism/logs/diag-%j.out
#SBATCH --error=/projects/u6vs/hnc-organism/logs/diag-%j.err

exec 2>&1
set -x

BASE=/projects/u6vs/hnc-organism
SIF="$BASE/containers/pytorch-25.05-py3.sif"
VENV="$BASE/venvs/aureon-sft"

echo "start $(date -Is) on $(hostname) cwd=$(pwd)"

ls -ld "$BASE" "$VENV/bin/python" "$SIF" || echo "ls failed rc=$?"
test -f "$SIF"; echo "sif rc=$?"
test -x "$VENV/bin/python"; echo "venv rc=$?"
test -f "$BASE/models/Qwen2.5-Coder-7B-Instruct/config.json"; echo "model rc=$?"
test -f "$BASE/training/sft/eval.jsonl"; echo "data rc=$?"

nvidia-smi -L || echo "nvidia-smi rc=$?"
apptainer --version || echo "apptainer missing"

apptainer exec --nv --cleanenv \
  --bind /projects/u6vs:/projects/u6vs \
  "$SIF" "$VENV/bin/python" -c \
  "import torch, transformers; print('torch', torch.__version__, 'tf', transformers.__version__, 'cuda', torch.cuda.is_available(), torch.cuda.device_count())"
echo "container rc=$?"

echo "diag done $(date -Is)"
