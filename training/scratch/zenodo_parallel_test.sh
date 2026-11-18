#!/bin/bash
# Does Zenodo give more aggregate bandwidth across parallel connections?
#
# The live pull runs at ~13 MB/s on one stream. The same node pulled from the
# Hub at 110-143 MB/s, so the limit is the server, not the link. If four
# concurrent streams still total ~13 MB/s, parallelism buys nothing and the
# simple sequential puller stays. If they total ~50 MB/s, it is worth rewriting.
#
# Downloads are capped at 60 s and written to /tmp, then deleted.
set -u

META=/projects/u6vs/zenodo/meta.jsonl
TMP=/tmp/zenodo_par
rm -rf "$TMP"
mkdir -p "$TMP"

# Pick four distinct open-access files of a size that can show a rate in 60 s.
python3 - "$META" <<'PY' > "$TMP/urls.txt"
import json, sys

WANT = 4
MIN, MAX = 100_000_000, 400_000_000
got = 0
seen = set()
for line in open(sys.argv[1], encoding="utf-8"):
    try:
        rec = json.loads(line)
    except ValueError:
        continue
    if str(rec.get("access")).lower() not in ("public", "open"):
        continue
    if rec.get("id") in seen:
        continue
    for f in rec.get("files") or []:
        size = int(f.get("size") or 0)
        url = f.get("url")
        if url and MIN <= size <= MAX:
            print(url)
            seen.add(rec.get("id"))
            got += 1
            break
    if got >= WANT:
        break
PY

n=$(wc -l < "$TMP/urls.txt")
echo "streams selected: $n"

i=0
while read -r u; do
    i=$((i + 1))
    curl -sfL --max-time 60 -o "$TMP/f$i" "$u" &
done < "$TMP/urls.txt"
wait

mb=$(du -sm "$TMP" | cut -f1)
echo "aggregate in 60 s: ${mb} MB across ${i} streams  => $((mb / 60)) MB/s"

rm -rf "$TMP"
