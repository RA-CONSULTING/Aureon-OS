#!/bin/bash
# Stage pretraining data on Isambard, one source at a time.
#
# Must run inside a LIVE ssh session. This login node kills user processes
# when the session closes: nohup + setsid lose the process, and
# `systemd-run --user` reports "Running as unit" but the work never runs.
# Compute nodes have no outbound network, so a Slurm job cannot fetch either.
# Reconnect and rerun this script after a drop; curl -C - resumes.
#
# Rerunning is safe and is the normal repair path: fetch_corpus.py skips any
# shard already present at the expected byte size, so a partial source refills
# and a complete one costs only a stat per file.
set -u

BASE=/projects/u6vs/hnc-organism
OUT=/projects/u6vs/pretrain
export HF_HOME=$BASE/hf_cache PYTHONNOUSERSITE=1

PY="apptainer exec --bind /projects/u6vs:/projects/u6vs $BASE/containers/pytorch-25.05-py3.sif $BASE/venvs/aureon-sft/bin/python -u"
FETCH="$BASE/training/scratch/fetch_corpus.py"

# fineweb-edu and fineweb together are ~143B tokens; code adds the share the
# model needs to write Aureon's own reasoning layer. starcoderdata and
# the-stack-dedup both answer 401 anonymously, so the code legs here are the
# ungated ones: codeparrot-clean (gzip JSONL) and smollm's python-edu.
SRCS="fineweb-edu fineweb code code-python-edu"
[ -n "${HF_TOKEN:-}" ] && SRCS="$SRCS code-stack-dedup"

for src in $SRCS; do
    for attempt in 1 2 3; do
        echo "=== $src attempt $attempt $(date -Is) ==="
        $PY "$FETCH" --source "$src" --out "$OUT/data" && break
        echo "=== $src attempt $attempt failed, retrying ==="
        sleep 30
    done
done

echo "=== harvest complete $(date -Is) ==="
du -sh "$OUT/data"
df -h /projects/u6vs | tail -1
