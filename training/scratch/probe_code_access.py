"""Check, anonymously, whether candidate code corpora can actually be fetched.

A gated repo lists its files happily and refuses the download with 401, which
is why the `code` source staged zero bytes twice. Status codes here are the
only evidence that matters, so resolve one real file per candidate and HEAD it.
"""

from __future__ import annotations

import urllib.error
import urllib.request

from huggingface_hub import HfApi

api = HfApi()

WANT = {
    "bigcode/the-stack-dedup": lambda p: "/python/" in p,
    "HuggingFaceTB/smollm-corpus": lambda p: p.startswith("python-edu/"),
    "codeparrot/codeparrot-clean": lambda p: p.endswith(".gz"),
}

for repo, pick in WANT.items():
    try:
        info = api.repo_info(repo, repo_type="dataset", files_metadata=True)
    except Exception as exc:
        print(f"{repo}: listing failed ({type(exc).__name__}: {exc})", flush=True)
        continue
    names = sorted(s.rfilename for s in info.siblings if pick(s.rfilename))
    if not names:
        print(f"{repo}: no matching files", flush=True)
        continue
    name = names[0]
    size = next(int(s.size or 0) for s in info.siblings if s.rfilename == name)
    url = f"https://huggingface.co/datasets/{repo}/resolve/main/{name}"
    req = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            code = r.status
    except urllib.error.HTTPError as exc:
        code = exc.code
    except Exception as exc:
        code = f"{type(exc).__name__}: {exc}"
    total = sum(int(s.size or 0) for s in info.siblings if pick(s.rfilename))
    n = len([s for s in info.siblings if pick(s.rfilename)])
    print(f"{repo}: {n} matching files, {total / 1e9:.1f} GB, "
          f"HEAD {code} on {name} ({size / 1e9:.2f} GB)", flush=True)
