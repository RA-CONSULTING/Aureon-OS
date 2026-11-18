"""Audit the staged pretraining corpus for shard collisions and truncated files.

fineweb-edu and fineweb both lay their shards out as sample/100BT/<name>.parquet.
fetch_corpus.py writes to out/<name>, so staging both into one --out means the
second source either overwrites the first or, worse, is skipped as "already
complete" because a same-named file of matching size is sitting there. That
would make 570 GB of expected corpus look finished at 300 GB.

This reports what is actually on disk and which repo each file matches, so the
answer comes from byte sizes rather than from the manifest's claims.
"""

import json
import pathlib
import sys

ROOT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/projects/u6vs/pretrain/data")
REPOS = ["HuggingFaceFW/fineweb-edu", "HuggingFaceFW/fineweb"]
PREFER = "sample/100BT"


def human(n: int) -> str:
    return f"{n / 1e9:.2f} GB"


def main() -> int:
    local = sorted(ROOT.rglob("*.parquet"))
    total = sum(p.stat().st_size for p in local)
    print(f"root: {ROOT}")
    print(f"local parquet files: {len(local)}   total: {human(total)}")

    groups: dict[str, list[int]] = {}
    for p in local:
        groups.setdefault(str(p.relative_to(ROOT).parent), []).append(p.stat().st_size)
    for key, sizes in sorted(groups.items()):
        print(f"  {key}/: {len(sizes)} files, {human(sum(sizes))}")

    print("\nmanifests:")
    found = False
    for m in sorted((ROOT.parent).rglob("manifest-*.json")):
        found = True
        try:
            data = json.loads(m.read_text(encoding="utf-8"))
        except ValueError:
            print(f"  {m}: unreadable")
            continue
        print(f"  {m.name}: repo={data.get('repo')} bytes={human(int(data.get('bytes') or 0))} "
              f"shards={data.get('shards') if isinstance(data.get('shards'), int) else len(data.get('shards') or [])}")
    if not found:
        print("  none")

    print("\nresolving expected shard sizes from the Hub")
    try:
        from huggingface_hub import HfApi
    except Exception as exc:  # noqa: BLE001
        print(f"  huggingface_hub unavailable: {type(exc).__name__}: {exc}")
        return 0

    api = HfApi()
    expect: dict[str, dict[str, int]] = {}
    for repo in REPOS:
        try:
            info = api.repo_info(repo, repo_type="dataset", files_metadata=True)
        except Exception as exc:  # noqa: BLE001
            print(f"  {repo}: {type(exc).__name__}: {exc}")
            continue
        n = 0
        for s in info.siblings:
            if s.rfilename.endswith(".parquet") and PREFER in s.rfilename:
                expect.setdefault(s.rfilename, {})[repo.split("/")[1]] = int(s.size or 0)
                n += 1
        print(f"  {repo}: {n} shards under {PREFER}")

    if not expect:
        print("  no expectations resolved; cannot attribute local files")
        return 0

    tags: dict[str, int] = {}
    neither_examples = []
    for p in local:
        rel = str(p.relative_to(ROOT))
        size = p.stat().st_size
        candidates = expect.get(rel)
        if not candidates:
            tags["not listed by either repo"] = tags.get("not listed by either repo", 0) + 1
            if len(neither_examples) < 5:
                neither_examples.append(f"{rel}: not listed by either repo")
            continue
        hit = [name for name, want in candidates.items() if want == size]
        if len(hit) == len(candidates) and len(candidates) > 1:
            label = "identical in both repos"
        elif len(hit) == 1:
            label = f"matches {hit[0]} only"
        else:
            label = "matches neither repo (short or foreign)"
            if len(neither_examples) < 5:
                want = ", ".join(f"{k}={human(v)}" for k, v in candidates.items())
                neither_examples.append(f"{rel}: on disk {human(size)}, expected {want}")
        tags[label] = tags.get(label, 0) + 1

    print("\nattribution:")
    for label, count in sorted(tags.items(), key=lambda kv: -kv[1]):
        print(f"  {label:42s} {count}")
    for ex in neither_examples:
        print(f"    {ex}")

    # --move repairs the mixture: each shard goes to the per-source directory
    # that fetch_corpus.py now writes to, so only the missing shards get
    # re-downloaded rather than all 570 GB. Ambiguous files (matching both
    # repos, or neither) are left where they are.
    if "--move" in sys.argv:
        moved = 0
        skipped = 0
        for p in local:
            rel = str(p.relative_to(ROOT))
            size = p.stat().st_size
            candidates = expect.get(rel) or {}
            hit = [name for name, want in candidates.items() if want == size]
            if len(hit) != 1:
                skipped += 1
                continue
            dest = ROOT / hit[0] / rel
            if dest.exists():
                skipped += 1
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            p.replace(dest)
            moved += 1
        print(f"\nmoved {moved} files into per-source directories, left {skipped} in place")

    return 0


if __name__ == "__main__":
    sys.exit(main())
