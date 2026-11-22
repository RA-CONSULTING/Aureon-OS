#!/bin/bash
# Download the pinned public release anonymously, then validate entirely offline.
#SBATCH --job-name=aureon-hub-validate
#SBATCH --account=brics.u6vs
#SBATCH --partition=workq
#SBATCH --nodes=1
#SBATCH --gpus-per-node=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=120000M
#SBATCH --time=01:00:00
#SBATCH --no-requeue
#SBATCH --output=/projects/u6vs/aureon-hf-release/logs/%x-%j.out
#SBATCH --error=/projects/u6vs/aureon-hf-release/logs/%x-%j.err

set -euo pipefail

BASE=/projects/u6vs/hnc-organism
RELEASE=/projects/u6vs/aureon-hf-release
CONSOLIDATED=$RELEASE/source
SIF=$BASE/containers/pytorch-25.05-py3.sif
VENV=$BASE/venvs/aureon-sft
HF_VENV=$RELEASE/private/hf-venv
VALIDATOR=$CONSOLIDATED/huggingface/validate_aureon_model.py
DOWNLOADER=$CONSOLIDATED/huggingface/download_aureon_hub.py
PUBLIC_RECEIPT=$RELEASE/model-public-receipt.json
DOWNLOAD_PARENT=$RELEASE/fresh-hub-downloads
DOWNLOAD=$DOWNLOAD_PARENT/job-$SLURM_JOB_ID
HUB_REPOSITORY=GaryLeckey/aureon-7b
HUB_REVISION=0757a7bdc36b190e9641a4cf421f89b9c66fab05

# Fresh artifacts must not overlap either the streamed source or hnc-organism.
case "$DOWNLOAD/" in
    "$CONSOLIDATED/"*|"$BASE/"*)
        echo "download directory must be outside source and hnc-organism" >&2
        exit 1
        ;;
esac
if [[ -e "$DOWNLOAD" || -L "$DOWNLOAD" ]]; then
    echo "refusing to reuse download path $DOWNLOAD" >&2
    exit 1
fi

test -f "$VALIDATOR"
test -f "$DOWNLOADER"
test -f "$PUBLIC_RECEIPT"
test -f "$CONSOLIDATED/training/aureon_chat_server.py"
test -f "$SIF"
test -f "$RELEASE/source-revision"
read -r SOURCE_REVISION < "$RELEASE/source-revision"
[[ "$SOURCE_REVISION" =~ ^[0-9a-f]{40}$ ]]
mkdir -p "$DOWNLOAD_PARENT" "$RELEASE/logs"

DOWNLOAD_PYTHON=$VENV/bin/python
if ! apptainer exec --cleanenv \
    --bind /projects/u6vs:/projects/u6vs \
    --env PYTHONNOUSERSITE=1 \
    "$SIF" "$DOWNLOAD_PYTHON" -c 'import huggingface_hub' >/dev/null 2>&1
then
    DOWNLOAD_PYTHON=$HF_VENV/bin/python
fi

apptainer exec --cleanenv \
    --bind /projects/u6vs:/projects/u6vs \
    --env PYTHONNOUSERSITE=1 \
    --env HF_HUB_OFFLINE=0 \
    --env HF_HUB_DISABLE_TELEMETRY=1 \
    --env HF_HUB_ETAG_TIMEOUT=30 \
    --env HF_HUB_DOWNLOAD_TIMEOUT=60 \
    "$SIF" "$DOWNLOAD_PYTHON" -u "$DOWNLOADER" \
        --download-dir "$DOWNLOAD" \
        --public-receipt "$PUBLIC_RECEIPT"

exec apptainer exec --nv --cleanenv \
    --bind /projects/u6vs:/projects/u6vs \
    --env SLURM_JOB_ID="$SLURM_JOB_ID" \
    --env PYTHONNOUSERSITE=1 \
    --env PYTHONPATH="$CONSOLIDATED:$CONSOLIDATED/training" \
    --env HF_HUB_OFFLINE=1 \
    --env TRANSFORMERS_OFFLINE=1 \
    --env HF_DATASETS_OFFLINE=1 \
    --env TOKENIZERS_PARALLELISM=false \
    "$SIF" "$VENV/bin/python" -u "$VALIDATOR" \
        --model "$DOWNLOAD" \
        --fresh-hub-download \
        --hub-repository "$HUB_REPOSITORY" \
        --hub-revision "$HUB_REVISION" \
        --source-tree "$CONSOLIDATED" \
        --source-revision "$SOURCE_REVISION" \
        --receipt "$RELEASE/fresh-hub-validation-receipt-$SLURM_JOB_ID.json"
