#!/bin/bash
#SBATCH --job-name=agpha
#SBATCH --output=agpha_%A_%a.out
#SBATCH --error=agpha_%A_%a.err
#SBATCH --array=0-255%32
#SBATCH --nodes=1
#SBATCH --gpus=1
#SBATCH --cpus-per-gpu=16
#SBATCH --time=02:00:00

# Aureon Global Plant Harmonic Atlas — one deterministic manifest shard per task.
# Override the array range at submission when manifest.shard_count is not 256:
#   sbatch --array=0-$((SHARDS-1))%CONCURRENCY scripts/isambard/plant_atlas_array.sbatch

set -euo pipefail

: "${AGPHA_REPO:?Set AGPHA_REPO to the checked-out Aureon-OS repository}"
: "${AGPHA_MANIFEST:?Set AGPHA_MANIFEST to an agpha.run-manifest.v1 JSON file}"
: "${AGPHA_CONTAINER:?Set AGPHA_CONTAINER to an aarch64-compatible PyTorch SIF image}"
: "${AGPHA_SOURCE_ROOT:?Set AGPHA_SOURCE_ROOT to the immutable source snapshot root}"
: "${AGPHA_OUTPUT_ROOT:?Set AGPHA_OUTPUT_ROOT to a writable project output directory}"

export OMP_NUM_THREADS="${SLURM_CPUS_PER_GPU:-16}"
export AGPHA_SEQUENCE_BACKEND="${AGPHA_SEQUENCE_BACKEND:-torch}"
export AGPHA_TORCH_DEVICE="${AGPHA_TORCH_DEVICE:-cuda}"
export AGPHA_SEQUENCE_BATCH_SIZE="${AGPHA_SEQUENCE_BATCH_SIZE:-64}"
export PYTHONHASHSEED=0

# Apptainer can inherit desktop-session variables that disturb container startup.
unset DBUS_SESSION_BUS_ADDRESS XDG_RUNTIME_DIR || true

for required in "$AGPHA_REPO" "$AGPHA_MANIFEST" "$AGPHA_CONTAINER" "$AGPHA_SOURCE_ROOT"; do
    if [[ ! -e "$required" ]]; then
        echo "Required path does not exist: $required" >&2
        exit 2
    fi
done
mkdir -p "$AGPHA_OUTPUT_ROOT"

MANIFEST_DIR="$(dirname "$AGPHA_MANIFEST")"

srun --ntasks=1 apptainer exec --nv --cleanenv \
    --bind "$AGPHA_REPO:$AGPHA_REPO:ro" \
    --bind "$MANIFEST_DIR:$MANIFEST_DIR:ro" \
    --bind "$AGPHA_SOURCE_ROOT:$AGPHA_SOURCE_ROOT:ro" \
    --bind "$AGPHA_OUTPUT_ROOT:$AGPHA_OUTPUT_ROOT" \
    "$AGPHA_CONTAINER" \
    env \
        PYTHONPATH="$AGPHA_REPO" \
        PYTHONHASHSEED=0 \
        OMP_NUM_THREADS="$OMP_NUM_THREADS" \
        AGPHA_SEQUENCE_BACKEND="$AGPHA_SEQUENCE_BACKEND" \
        AGPHA_TORCH_DEVICE="$AGPHA_TORCH_DEVICE" \
        AGPHA_SEQUENCE_BATCH_SIZE="$AGPHA_SEQUENCE_BATCH_SIZE" \
        python -m aureon.bio.plant_atlas run-shard \
            --manifest "$AGPHA_MANIFEST" \
            --shard-index "$SLURM_ARRAY_TASK_ID" \
            --source-root "$AGPHA_SOURCE_ROOT" \
            --output-root "$AGPHA_OUTPUT_ROOT"
