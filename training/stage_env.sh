#!/bin/bash
# Stage the training environment on Isambard.
#
# The NGC container ships torch 2.8 (aarch64) + numpy 1.26.4. We inherit them
# via --system-site-packages rather than reinstalling torch (~2.5 GB) or
# upgrading numpy (which would risk the CUDA/cudf stack).
#
# Because numpy is pinned at 1.26.4, the HF stack is capped below the majors
# that require numpy>=2: transformers<5 / datasets<4 / trl<0.16 pull
# pyarrow<20, which also satisfies NGC's cudf 25.4 (pyarrow<20).
set -euo pipefail

BASE=/projects/u6vs/hnc-organism
SIF="$BASE/containers/pytorch-25.05-py3.sif"
VENV="$BASE/venvs/aureon-sft"
BIND="--bind /projects/u6vs:/projects/u6vs"
export PYTHONNOUSERSITE=1

mkdir -p "$BASE/venvs" "$BASE/logs"

if [ ! -x "$VENV/bin/python" ]; then
  echo "[stage] creating venv with system site packages"
  apptainer exec $BIND "$SIF" python -m venv --system-site-packages "$VENV"
fi

echo "[stage] installing numpy-1.26 compatible HF/TRL/PEFT stack"
apptainer exec $BIND "$SIF" "$VENV/bin/python" -m pip install \
  "transformers>=4.46,<5" \
  "peft>=0.13,<0.19" \
  "trl>=0.12,<0.16" \
  "datasets>=3.0,<4" \
  "accelerate>=1.0,<2" \
  "pyarrow>=15,<20"

echo "[stage] verifying imports"
apptainer exec $BIND "$SIF" "$VENV/bin/python" - <<'PY'
import numpy, pyarrow, torch
import transformers, peft, trl, datasets, accelerate
print("numpy       ", numpy.__version__)
print("pyarrow     ", pyarrow.__version__)
print("torch       ", torch.__version__)
print("transformers", transformers.__version__)
print("peft        ", peft.__version__)
print("trl         ", trl.__version__)
print("datasets    ", datasets.__version__)
print("accelerate  ", accelerate.__version__)
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import LoraConfig, get_peft_model
from trl import SFTTrainer, SFTConfig
print("sft_api     ", "SFTTrainer+SFTConfig ok")
PY

echo "[stage] pip check"
apptainer exec $BIND "$SIF" "$VENV/bin/python" -m pip check || echo "[stage] pip check reported issues (non-fatal)"

echo "[stage] done"
