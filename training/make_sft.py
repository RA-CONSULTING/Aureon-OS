"""Turn the built corpus into SFT pairs with full, non-duplicated coverage.

Three deterministic task shapes — no LLM in the loop, so nothing here can
hallucinate training data:

  implement  whole module, when it fits in one response
  implement  one public top-level symbol at a time, for modules too big
  continue   line-window chunk of whatever the symbol pass did not cover

The symbol spans and the chunks partition each file exactly at line
boundaries, so every character appears in exactly one pair. Coverage is
therefore 100% of the corpus by construction, not by estimate.

Output: <out>/train.jsonl, <out>/eval.jsonl with {instruction, response, path}
"""

from __future__ import annotations

import argparse
import ast
import json
import pathlib

import prompt_contract as pc

MAX_RESPONSE_CHARS = 12_000   # ~3.3k tokens, comfortably inside a 4096 window
MIN_SYMBOL_CHARS = 200
MAX_SYMBOL_PAIRS = 500


def module_docstring(src: str) -> str:
    try:
        tree = ast.parse(src)
    except (SyntaxError, ValueError):
        return ""
    doc = ast.get_docstring(tree) or ""
    return doc.strip()


def public_surface(tree: ast.Module) -> list[str]:
    out = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_"):
                out.append(f"def {node.name}(...)")
        elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            out.append(f"class {node.name}")
    return out


def explain_text(rel: str, src: str) -> str:
    try:
        tree = ast.parse(src)
    except (SyntaxError, ValueError):
        return ""
    doc = (ast.get_docstring(tree) or "").strip()
    surface = public_surface(tree)
    if not doc and not surface:
        return ""
    lines = [f"`{rel}`"]
    if doc:
        first = doc.splitlines()[0].strip()
        lines.append("")
        lines.append(first)
    if surface:
        lines.append("")
        lines.append("Public surface:")
        lines.extend(f"- {s}" for s in surface[:40])
    return "\n".join(lines)


def line_starts(src: str) -> list[int]:
    starts = [0]
    for i, ch in enumerate(src):
        if ch == "\n":
            starts.append(i + 1)
    return starts


def symbol_spans(src: str, tree: ast.Module) -> tuple[list[tuple[str, str]], list[tuple[int, int]]]:
    """Return (kind, name, segment) triples plus the line-aligned spans they occupy."""
    starts = line_starts(src)
    n_lines = len(starts)
    symbols: list[tuple[str, str, str]] = []
    covered: list[tuple[int, int]] = []

    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        segment = ast.get_source_segment(src, node)
        if not segment:
            continue
        if len(segment) < MIN_SYMBOL_CHARS:
            # Too small to stand alone: leave it uncovered so the chunk pass
            # folds it into the surrounding text instead of dropping it.
            continue
        if len(segment) > MAX_RESPONSE_CHARS:
            # Too large for one response: leave it uncovered so the chunk pass
            # splits it into windows that fit. Marking it covered here would
            # silently discard it — it is neither emitted nor chunked.
            continue
        start = starts[node.lineno - 1]
        end = starts[node.end_lineno] if node.end_lineno < n_lines else len(src)
        kind = "class" if isinstance(node, ast.ClassDef) else "function"
        symbols.append((kind, node.name, segment))
        covered.append((start, end))
        if len(symbols) >= MAX_SYMBOL_PAIRS:
            break

    covered.sort()
    merged: list[tuple[int, int]] = []
    for s, e in covered:
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))
    return symbols, merged


def gaps(covered: list[tuple[int, int]], length: int) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    cursor = 0
    for s, e in covered:
        if s > cursor:
            out.append((cursor, s))
        cursor = max(cursor, e)
    if cursor < length:
        out.append((cursor, length))
    return out


def split_region(src: str, start: int, end: int, cap: int) -> list[tuple[int, int]]:
    """Slice [start, end) into windows of at most `cap` chars, on line edges."""
    out: list[tuple[int, int]] = []
    pos = start
    while pos < end:
        window = min(end, pos + cap)
        if window < end:
            nl = src.rfind("\n", pos, window)
            if nl > pos:
                window = nl + 1
        out.append((pos, window))
        pos = window
    return out


def py_pairs(rel: str, src: str) -> list[dict]:
    pairs: list[dict] = []
    tree = None
    try:
        tree = ast.parse(src)
    except (SyntaxError, ValueError):
        tree = None

    if len(src) <= MAX_RESPONSE_CHARS:
        pairs.append({
            "instruction": pc.implement_module(rel),
            "response": src,
            "path": rel,
            "shape": "implement",
        })
    elif tree is not None:
        symbols, covered = symbol_spans(src, tree)
        for kind, name, segment in symbols:
            pairs.append({
                "instruction": pc.implement_symbol(kind, name, rel),
                "response": segment,
                "path": rel,
                "shape": "implement",
                "symbol": name,
            })
        starts = line_starts(src)
        for g0, g1 in gaps(covered, len(src)):
            for c0, c1 in split_region(src, g0, g1, MAX_RESPONSE_CHARS):
                text = src[c0:c1]
                if not text.strip():
                    continue
                pairs.append({
                    "instruction": pc.continue_module(rel, _line_of(starts, c0)),
                    "response": text,
                    "path": rel,
                    "shape": "continue",
                })
    else:
        # Unparseable Python: fall back to plain chunking.
        starts = line_starts(src)
        for c0, c1 in split_region(src, 0, len(src), MAX_RESPONSE_CHARS):
            text = src[c0:c1]
            if not text.strip():
                continue
            pairs.append({
                "instruction": pc.continue_module(rel, _line_of(starts, c0)),
                "response": text,
                "path": rel,
                "shape": "continue",
            })

    summary = explain_text(rel, src)
    if summary:
        pairs.append({
            "instruction": pc.explain_module(rel),
            "response": summary,
            "path": rel,
            "shape": "explain",
        })
    return pairs


def _line_of(starts: list[int], offset: int) -> int:
    lo, hi = 0, len(starts) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if starts[mid] <= offset:
            lo = mid
        else:
            hi = mid - 1
    return lo + 1


def non_py_pairs(rel: str, src: str) -> list[dict]:
    if len(src) <= MAX_RESPONSE_CHARS:
        return [{
            "instruction": pc.implement_file(rel),
            "response": src,
            "path": rel,
            "shape": "implement",
        }]
    starts = line_starts(src)
    out = []
    for c0, c1 in split_region(src, 0, len(src), MAX_RESPONSE_CHARS):
        text = src[c0:c1]
        if not text.strip():
            continue
        out.append({
            "instruction": pc.continue_file(rel, _line_of(starts, c0)),
            "response": text,
            "path": rel,
            "shape": "continue",
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    corpus = pathlib.Path(args.corpus)
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    counts = {"train": 0, "holdout": 0, "skipped": 0}
    chars = {"train": 0, "holdout": 0}
    files = {"train": (out / "train.jsonl").open("w", encoding="utf-8"),
             "holdout": (out / "eval.jsonl").open("w", encoding="utf-8")}

    try:
        with (corpus / "files.jsonl").open(encoding="utf-8") as fh:
            for line in fh:
                rec = json.loads(line)
                split = "holdout" if rec["split"] == "holdout" else "train"
                src = rec["text"]
                rel = rec["path"]
                pairs = py_pairs(rel, src) if rec["ext"] == ".py" else non_py_pairs(rel, src)
                if not pairs:
                    counts["skipped"] += 1
                    continue
                for p in pairs:
                    files[split].write(json.dumps(p, ensure_ascii=False) + "\n")
                    counts[split] += 1
                    chars[split] += len(p["instruction"]) + len(p["response"])
    finally:
        for fh in files.values():
            fh.close()

    print(json.dumps({
        "rows": counts,
        "chars": chars,
        "est_tokens": {k: round(v / 3.6) for k, v in chars.items()},
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
