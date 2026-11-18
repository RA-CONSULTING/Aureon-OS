"""Build a deterministic fine-tuning corpus from an Aureon checkout.

Emits:
  <out>/files.jsonl   one JSON record per accepted file
  <out>/holdout.txt   paths reserved for evaluation
  <out>/manifest.json stats, filters, content hashes

Usage:
  python build_corpus.py --root C:\\Users\\samle\\Aureon-OS --out .\\corpus
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
from collections import Counter

CODE_EXT = {".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cu", ".c", ".h", ".cpp",
            ".go", ".rs", ".java", ".sql", ".sh", ".ps1", ".bat"}
DOC_EXT = {".md", ".rst", ".txt"}
CFG_EXT = {".toml", ".yaml", ".yml", ".ini", ".cfg"}
KEEP_EXT = CODE_EXT | DOC_EXT | CFG_EXT

# Generated bundles, vendored snapshots, and research-data dumps dominate by
# volume while teaching the model nothing about how Aureon is written.
EXCLUDE_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv", "dist", "build",
    ".next", ".mypy_cache", ".pytest_cache", ".ruff_cache", "site-packages",
    "imports", "archive", "artifacts", "sources", "data", "public",
    "Antarctic research", "memory", "wisdom_data",
}
EXCLUDE_NAMES = {"package-lock.json", "yarn.lock", "poetry.lock", "pnpm-lock.yaml"}
MAX_BYTES = 2_000_000
MIN_CHARS = 200
HOLDOUT_MODULUS = 50          # 1 file in 50 is held out, stable by path hash


def is_minified(text: str) -> bool:
    lines = text.splitlines() or [""]
    return len(lines) < 5 and len(text) > 4000 or any(len(l) > 3000 for l in lines)


def norm_hash(text: str) -> str:
    canon = "\n".join(line.rstrip() for line in text.splitlines()).strip()
    return hashlib.sha1(canon.encode("utf-8", "ignore")).hexdigest()


def iter_files(root: pathlib.Path):
    for dirpath, dirnames, filenames in os_walk(root):
        for name in sorted(filenames):
            yield pathlib.Path(dirpath) / name


def os_walk(root: pathlib.Path):
    import os
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDE_DIRS)
        yield dirpath, dirnames, filenames


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    root = pathlib.Path(args.root).resolve()
    out = pathlib.Path(args.out).resolve()
    if not (root / ".git").exists() and not (root / "README.md").exists():
        print(f"refusing: {root} does not look like a checkout", file=sys.stderr)
        return 2
    out.mkdir(parents=True, exist_ok=True)

    seen_hashes: dict[str, str] = {}
    rejected: Counter[str] = Counter()
    per_ext: Counter[str] = Counter()
    per_top: Counter[int] = Counter()
    records: list[dict] = []
    holdout: list[str] = []

    for path in iter_files(root):
        rel = path.relative_to(root).as_posix()
        ext = path.suffix.lower()
        if ext not in KEEP_EXT:
            rejected["extension"] += 1
            continue
        if path.name in EXCLUDE_NAMES:
            rejected["lockfile"] += 1
            continue
        try:
            size = path.stat().st_size
        except OSError:
            rejected["stat_error"] += 1
            continue
        if size > MAX_BYTES:
            rejected["too_large"] += 1
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            rejected["read_error"] += 1
            continue
        if "\x00" in text[:2048]:
            rejected["binary"] += 1
            continue
        if len(text) < MIN_CHARS:
            rejected["too_small"] += 1
            continue
        if is_minified(text):
            rejected["minified"] += 1
            continue

        digest = norm_hash(text)
        if digest in seen_hashes:
            rejected["duplicate"] += 1
            continue
        seen_hashes[digest] = rel

        top = rel.split("/")[0] if "/" in rel else "(root)"
        bucket = int(hashlib.sha1(rel.encode()).hexdigest()[:8], 16) % HOLDOUT_MODULUS
        split = "holdout" if bucket == 0 else "train"
        if split == "holdout":
            holdout.append(rel)

        records.append({
            "path": rel,
            "ext": ext,
            "lang": ext.lstrip("."),
            "top": top,
            "chars": len(text),
            "sha1": digest,
            "split": split,
            "text": text,
        })
        per_ext[ext] += 1
        per_top[top] += len(text)

    chars_total = sum(r["chars"] for r in records)
    chars_train = sum(r["chars"] for r in records if r["split"] == "train")
    chars_hold = chars_total - chars_train

    with (out / "files.jsonl").open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    (out / "holdout.txt").write_text("\n".join(sorted(holdout)) + "\n", encoding="utf-8")

    manifest = {
        "root": str(root),
        "accepted_files": len(records),
        "chars_total": chars_total,
        "chars_train": chars_train,
        "chars_holdout": chars_hold,
        "est_tokens_total": round(chars_total / 3.6),
        "est_tokens_train": round(chars_train / 3.6),
        "est_tokens_holdout": round(chars_hold / 3.6),
        "rejected": dict(rejected.most_common()),
        "per_ext": dict(per_ext.most_common()),
        "per_top_chars": dict(per_top.most_common()),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(json.dumps({k: v for k, v in manifest.items() if not k.startswith("per_")}, indent=2))
    print("\ntop dirs by chars:", json.dumps(dict(list(per_top.most_common(8))), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
