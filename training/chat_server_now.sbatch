#!/bin/bash
# Serve the fine-tuned Aureon model over the chat contract from a compute node.
# Prints the node hostname FIRST so an ssh tunnel can be aimed at it immediately:
#   ssh -L 11435:<NODE-IP>:8000 u6vs.aip2.isambard
#
#SBATCH --job-name=aureon-chat-server
#SBATCH --account=brics.u6vs
#SBATCH --partition=workq
#SBATCH --nodes=1
#SBATCH --gpus-per-node=1
#SBATCH --cpus-per-task=64
#SBATCH --mem=115000M
#SBATCH --time=06:00:00
#SBATCH --no-requeue
#SBATCH --output=logs/%x-%j.out

set -euo pipefail

BASE=/projects/u6vs/hnc-organism
SIF=$BASE/containers/pytorch-25.05-py3.sif
VENV=$BASE/venvs/aureon-sft
MODEL=${MODEL:-$BASE/runs/aureon-7b-sft-now/hf}
PORT=${PORT:-8000}
HOST=${HOST:-$(hostname -i | awk '{print $1}')}

test -f "$SIF"
test -f "$MODEL/config.json"

echo "[chat] node=$(hostname) host=$HOST port=$PORT model=$MODEL"
echo "[chat] tunnel: ssh -L 11435:${HOST}:${PORT} u6vs.aip2.isambard"

exec apptainer exec --nv --cleanenv \
    --bind /projects/u6vs:/projects/u6vs \
    --env PYTHONNOUSERSITE=1 \
    --env PYTHONPATH=$BASE/training \
    --env HF_HUB_OFFLINE=1 \
    "$SIF" \
    "$VENV/bin/python" -u "$BASE/training/aureon_chat_server.py" \
        --model "$MODEL" --host "$HOST" --port "$PORT"
