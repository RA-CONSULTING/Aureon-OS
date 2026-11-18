#!/bin/bash
# Report Zenodo pull progress: size, throughput, completions, failures.
#
# Kept as a file rather than an inline ssh one-liner because shell arithmetic
# with $( ) and $(( )) cannot survive the cmd.exe -> ssh -> bash quoting chain
# intact; escaping the $ breaks it in bash instead.
set -u

D=/projects/u6vs/zenodo/files
LOG=/projects/u6vs/zenodo/pull.log
INTERVAL=${1:-120}

a=$(du -sm "$D" 2>/dev/null | cut -f1)
a=${a:-0}
t1=$(date +%s)
sleep "$INTERVAL"
b=$(du -sm "$D" 2>/dev/null | cut -f1)
b=${b:-0}
t2=$(date +%s)

el=$((t2 - t1))
[ "$el" -le 0 ] && el=1
grown=$((b - a))

done=$(grep -c . "$D/pulled.jsonl" 2>/dev/null) || done=0
fails=$(grep -c 'curl ' "$LOG" 2>/dev/null) || fails=0

printf 'date      : %s\n' "$(date -Is)"
printf 'size      : %s MB -> %s MB  (+%s MB in %ss)\n' "$a" "$b" "$grown" "$el"
printf 'rate      : %s MB/s\n' "$((grown / el))"
printf 'completed : %s files\n' "$done"
printf 'failures  : %s\n' "$fails"
printf 'in flight : %s\n' "$(tail -1 "$LOG")"
printf 'disk      : %s\n' "$(df -h /projects/u6vs | tail -1)"
