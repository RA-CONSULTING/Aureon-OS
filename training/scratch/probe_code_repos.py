"""Report what the candidate code-corpus repos actually publish.

The `code` source keeps staging zero shards: bigcode/starcoderdata lists fine
then refuses downloads (401), and the fallback codeparrot/codeparrot-clean is
JSONL, which shard_list() filters out because it keeps only *.parquet. Before
picking a replacement, look at real file lists rather than guessing.
"""

from __future__ import annotations

import collections
import sys

from huggingface_hub import HfApi

CANDIDATES = [
    "bigcode/starcoderdata",
    "codeparrot/codeparrot-clean",
    "HuggingFaceTB/smollm-corpus",
    "bigcode/the-stack-dedup",
]

api = HfApi()

for repo in CANDIDATES:
    try:
        info = api.repo_info(repo, repo_type="dataset", files_metadata=True)
    except Exception as exc:
        print(f"{repo}: unavailable ({type(exc).__name__}: {exc})", flush=True)
        continue
    sibs = info.siblings
    ext = collections.Counter()
    total = collections.Counter()
    for s in sibs:
        e = s.rfilename.rsplit(".", 1)[-1].lower() if "." in s.rfilename else "(none)"
        ext[e] += 1
        total[e] += int(s.size or 0)
    print(f"\n{repo}: {len(sibs)} files", flush=True)
    for e, n in ext.most_common(6):
        print(f"    .{e:<8} {n:>6} files  {total[e] / 1e9:8.1f} GB", flush=True)
    pq = sorted(s.rfilename for s in sibs if s.rfilename.endswith(".parquet"))
    if pq:
        print(f"    first parquet: {pq[0]}", flush=True)
    dirs = collections.Counter(p.split("/")[0] for p in pq if "/" in p)
    if dirs:
        print(f"    parquet top dirs: {dict(list(dirs.items())[:6])}", flush=True)
sys.exit(0)
