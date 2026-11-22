#!/bin/bash
# Validate only: no training, checkpoint writes, downloads, or job submission.
#SBATCH --job-name=aureon-validate
#SBATCH --account=brics.u6vs
#SBATCH --partition=workq
#SBATCH --nodes=1
#SBATCH --gpus-per-node=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=120000M
#SBATCH --time=00:40:00
#SBATCH --no-requeue
#SBATCH --output=/projects/u6vs/aureon-hf-release/logs/%x-%j.out
#SBATCH --error=/projects/u6vs/aureon-hf-release/logs/%x-%j.err

set -euo pipefail

BASE=/projects/u6vs/hnc-organism
RELEASE=/projects/u6vs/aureon-hf-release
EXPORT=$BASE/runs/aureon-7b-sft-label-fix/hf
OVERLAY=$RELEASE/model-overlay
CONSOLIDATED=$RELEASE/source
COMBINED=$RELEASE/combined-model
SIF=$BASE/containers/pytorch-25.05-py3.sif
VENV=$BASE/venvs/aureon-sft
VALIDATOR=$CONSOLIDATED/huggingface/validate_aureon_model.py

# The combined directory is deliberately outside the streamed source tree.
case "$COMBINED/" in
    "$CONSOLIDATED/"*)
        echo "combined model must be outside $CONSOLIDATED" >&2
        exit 1
        ;;
esac

test -f "$VALIDATOR"
test -f "$CONSOLIDATED/training/aureon_chat_server.py"
test -f "$EXPORT/model.safetensors"
test -f "$SIF"
test -f "$RELEASE/source-revision"
read -r SOURCE_REVISION < "$RELEASE/source-revision"
[[ "$SOURCE_REVISION" =~ ^[0-9a-f]{40}$ ]]
mkdir -p "$COMBINED" "$RELEASE/logs"

# Only small metadata files are copied. The 14 GB weight remains in place and
# is exposed through a symlink; validate_aureon_model.py independently hashes it.
for name in \
    config.json \
    generation_config.json \
    tokenizer_config.json \
    tokenizer.json \
    aureon_export.json \
    preparation_receipt.json
do
    test -f "$OVERLAY/$name"
    cp -f -- "$OVERLAY/$name" "$COMBINED/$name"
done
ln -sfn -- "$EXPORT/model.safetensors" "$COMBINED/model.safetensors"
test -L "$COMBINED/model.safetensors"
test -f "$COMBINED/model.safetensors"

exec apptainer exec --nv --cleanenv \
    --bind /projects/u6vs:/projects/u6vs \
    --env SLURM_JOB_ID="$SLURM_JOB_ID" \
    --env PYTHONNOUSERSITE=1 \
    --env PYTHONPATH="$CONSOLIDATED:$CONSOLIDATED/training" \
    --env HF_HUB_OFFLINE=1 \
    --env TRANSFORMERS_OFFLINE=1 \
    --env HF_DATASETS_OFFLINE=1 \
    --env TOKENIZERS_PARALLELISM=false \
    "$SIF" \
    "$VENV/bin/python" -u "$VALIDATOR" \
        --model "$COMBINED" \
        --source "$EXPORT" \
        --overlay "$OVERLAY" \
        --source-tree "$CONSOLIDATED" \
        --source-revision "$SOURCE_REVISION" \
        --receipt "$RELEASE/validation-receipt-$SLURM_JOB_ID.json"
