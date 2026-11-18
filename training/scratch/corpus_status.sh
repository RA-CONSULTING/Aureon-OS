#!/bin/bash
# Corpus staging status, one line per source, plus the tail of the harvest log.
S=/projects/u6vs/pretrain
echo '--- harvest3.log:'
tail -12 "$S/harvest3.log" 2>/dev/null
echo '--- shard counts:'
for d in fineweb fineweb-edu code codeparrot-clean; do
    n=$(ls "$S/data/$d/sample/100BT/"*.parquet 2>/dev/null | wc -l)
    bytes=$(du -sb "$S/data/$d" 2>/dev/null | cut -f1)
    echo "$d shards=$n bytes=${bytes:-0}"
done
