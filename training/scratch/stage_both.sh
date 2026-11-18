#!/bin/bash
# Own or watch each transfer, whichever login node this lands on.
#
# The SSH name u6vs.aip2.isambard load-balances across login nodes (login40-44
# observed) and they all share /projects. A node-local pgrep is therefore
# useless as a guard: on 2026-10-26 the pull was running on login42 while every
# check of mine landed on login40/43/44 and reported nothing running. Acting on
# that check starts a second writer on a file another node already has open,
# which is how an archive grew ~1.7 GB past its true length and corrupted.
#
# State therefore lives on the shared filesystem: an atomic mkdir is the mutex,
# and the owner rewrites a heartbeat every 15s. A node starts a job only if it
# wins the mkdir, or if the owner's heartbeat is stale, meaning that session was
# torn down. A node that does not win keeps its own session open and polls, so
# takeover happens immediately without reconnecting through the balancer.
set -u

BASE=/projects/u6vs/hnc-organism
PY="apptainer exec --bind /projects/u6vs:/projects/u6vs $BASE/containers/pytorch-25.05-py3.sif $BASE/venvs/aureon-sft/bin/python -u"
export HF_HOME=$BASE/hf_cache
export PYTHONNOUSERSITE=1

SCRATCH=$BASE/training/scratch
GUARD_LOG=$SCRATCH/guard.log

log() { echo "guard[$(hostname)]: $* $(date -Is)" >> "$GUARD_LOG"; }

# 0 = free to start (no lock, or a dead owner); 1 = someone is alive.
free_or_stale() {
    local lock=$1 hb=$2 now ts
    [ -d "$lock" ] || return 0
    now=$(date +%s)
    if ! ts=$(stat -c %Y "$hb" 2>/dev/null); then
        rm -rf "$lock" 2>/dev/null
        return 0
    fi
    if [ $((now - ts)) -gt 75 ]; then
        rm -rf "$lock" 2>/dev/null
        return 0
    fi
    return 1
}

# Watch one job forever: run it while this node owns the lock, poll otherwise.
# $1 name, $2 lock, $3 heartbeat, $4 url pattern of its curl orphans,
# $5 log file the job appends to, then the command to run.
guard_job() {
    local name=$1 lock=$2 hb=$3 curlpat=$4 joblog=$5
    shift 5
    local cpid owner last=""
    while :; do
        if ! free_or_stale "$lock" "$hb"; then
            owner=$(head -1 "$hb" 2>/dev/null)
            if [ "$owner" != "$last" ]; then
                log "$name held elsewhere: $owner"
                last=$owner
            fi
            sleep 20
            continue
        fi
        if ! mkdir "$lock" 2>/dev/null; then
            sleep 5
            continue
        fi
        # This node owns the lock, so any curl here with that URL is an orphan
        # of a dead python parent and would keep appending to the same file.
        pkill -9 -f "$curlpat" 2>/dev/null
        log "starting $name"
        "$@" >> "$joblog" 2>&1 &
        cpid=$!
        while kill -0 "$cpid" 2>/dev/null; do
            echo "owner=$(hostname) child=$cpid $(date -Is)" > "$hb"
            sleep 15
        done
        wait "$cpid"
        log "$name exited rc=$?"
        rmdir "$lock" 2>/dev/null
        sleep 30
    done
}

guard_job zenodo "$SCRATCH/.lock-zenodo" "$SCRATCH/.hb-zenodo" \
    '[z]enodo\.org/api/records' /projects/u6vs/zenodo/pull.log \
    $PY "$SCRATCH/fetch_zenodo.py" --pull \
        --meta /projects/u6vs/zenodo/meta.jsonl \
        --out /projects/u6vs/zenodo/files \
        --budget-gb 0 --max-file-gb 0 &
ZPID=$!

guard_job corpus "$SCRATCH/.lock-corpus" "$SCRATCH/.hb-corpus" \
    '[d]ata\.huggingface\.co' /projects/u6vs/pretrain/harvest3.log \
    bash "$SCRATCH/harvest.sh" &
CPID=$!

log "guard session up, zenodo=$ZPID corpus=$CPID"
wait
