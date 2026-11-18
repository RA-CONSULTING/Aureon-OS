#!/bin/bash
# Kill every staging writer on this node and report what was killed.
#
# Run across several connections because the SSH name load-balances between
# login nodes: one invocation only ever cleans the node it lands on.
me=$(hostname)
out=""

for pat in 'fetch_[z]enodo' 'fetch_[c]orpus' '[z]enodo\.org/api/records' '[d]ata\.huggingface\.co'; do
    for p in $(pgrep -f "$pat" 2>/dev/null); do
        [ "$p" = "$$" ] && continue
        kill -9 "$p" 2>/dev/null && out="$out $p"
    done
done

if [ -z "$out" ]; then
    echo "$me clean"
else
    echo "$me killed$out"
fi
