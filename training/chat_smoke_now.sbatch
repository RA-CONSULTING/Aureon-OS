#!/bin/bash
# Definitive self-contained proof that Aureon-OS's own model serves and chats.
# Starts the chat server against the hf-17k export, then drives it over HTTP:
# /v1/models and one real /v1/chat/completions round trip, byte-identical to
# what AureonLocalAdapter sends.
#SBATCH --job-name=aureon-chat-smoke
#SBATCH --account=brics.u6vs
#SBATCH --partition=workq
#SBATCH --nodes=1
#SBATCH --gpus-per-node=1
#SBATCH --cpus-per-task=64
#SBATCH --mem=115000M
#SBATCH --time=00:40:00
#SBATCH --no-requeue
#SBATCH --output=logs/%x-%j.out

set -euo pipefail

BASE=/projects/u6vs/hnc-organism
SIF=$BASE/containers/pytorch-25.05-py3.sif
VENV=$BASE/venvs/aureon-sft
MODEL=${MODEL:-$BASE/runs/aureon-7b-v65k/hf-17k}
PORT=${PORT:-8000}

test -f "$MODEL/config.json"

echo "[smoke] node=$(hostname) model=$MODEL"

exec apptainer exec --nv --cleanenv \
    --bind /projects/u6vs:/projects/u6vs \
    --env PYTHONNOUSERSITE=1 \
    --env PYTHONPATH=$BASE/training \
    --env HF_HUB_OFFLINE=1 \
    "$SIF" \
    "$VENV/bin/python" -u "$BASE/training/aureon_chat_server.py" \
        --model "$MODEL" --port "$PORT" &
SERVER_PID=$!

# Wait until /v1/models answers (model load takes minutes on first cold start).
for i in $(seq 1 60); do
    if curl -s -m 2 "http://127.0.0.1:${PORT}/v1/models" | grep -q aureon; then
        break
    fi
    sleep 5
done

echo "[smoke] /v1/models:"
curl -s "http://127.0.0.1:${PORT}/v1/models"
echo

echo "[smoke] chat round trip:"
curl -s -X POST "http://127.0.0.1:${PORT}/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -d '{
      "model": "aureon-7b-v65k",
      "messages": [
        {"role": "system", "content": "You are Aureon, a coding agent working inside the Aureon-OS repository. You write Python that matches the repository'"'"'s existing module layout, type hints, and docstring conventions."},
        {"role": "user", "content": "Write the complete Python module `aureon_systems/aureon_lattice_simulation.py` in the Aureon-OS repository."}
      ],
      "max_tokens": 120,
      "temperature": 0.0
    }'
echo
echo "[smoke] done"
kill "$SERVER_PID" 2>/dev/null || true
