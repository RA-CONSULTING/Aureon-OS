"""Pre-flight health check: is the training input actually fit to train on?

Read-only. Run before every training submission — a corpus problem discovered
after six GPU-hours is six GPU-hours wasted.

  <venv>/bin/python training/health_check.py --base /projects/u6vs/hnc-organism

Exit code 0 = all critical checks pass, 1 = at least one FAIL.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import py_compile
import shutil
import sys
import tempfile

MAX_SEQ = 4096
CHARS_PER_TOKEN = 3.6  # conservative estimate used when building the corpus

results: list[tuple[str, str, str]] = []


def check(name: str, ok: bool, detail: str, critical: bool = True) -> bool:
    status = "PASS" if ok else ("FAIL" if critical else "WARN")
    results.append((status, name, detail))
    return ok or not critical


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="/projects/u6vs/hnc-organism")
    args = ap.parse_args()

    base = pathlib.Path(args.base)
    corpus = base / "training" / "corpus"
    sft = base / "training" / "sft"
    model = base / "models" / "Qwen2.5-Coder-7B-Instruct"

    # ---- corpus -----------------------------------------------------------
    files_jsonl = corpus / "files.jsonl"
    ok_files = check("corpus files.jsonl present", files_jsonl.is_file(), str(files_jsonl))
    manifest_path = corpus / "manifest.json"
    ok_manifest = check("corpus manifest.json present", manifest_path.is_file(), str(manifest_path))

    n_files = 0
    py_train_chars = 0
    train_paths: set[str] = set()
    holdout_paths: set[str] = set()
    empty_text = 0
    bad_json = 0
    split_bad = 0

    if ok_files:
        with files_jsonl.open(encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    bad_json += 1
                    continue
                n_files += 1
                if not str(rec.get("text", "")).strip():
                    empty_text += 1
                split = rec.get("split")
                if split == "holdout":
                    holdout_paths.add(rec["path"])
                elif split == "train":
                    train_paths.add(rec["path"])
                    if rec.get("ext") == ".py":
                        py_train_chars += len(rec["text"])
                else:
                    split_bad += 1

        check("corpus rows parse as JSON", bad_json == 0, f"{bad_json} malformed")
        check("no empty corpus records", empty_text == 0, f"{empty_text} empty")
        check("every record has a valid split", split_bad == 0, f"{split_bad} invalid")
        check("corpus non-trivial", n_files > 1000, f"{n_files} records")

    if ok_manifest and ok_files:
        man = json.loads(manifest_path.read_text(encoding="utf-8"))
        check(
            "manifest row count matches files.jsonl",
            man.get("accepted_files") == n_files,
            f"manifest={man.get('accepted_files')} actual={n_files}",
        )
        check(
            "holdout exists and is small but non-empty",
            0 < len(holdout_paths) < len(train_paths),
            f"holdout={len(holdout_paths)} train={len(train_paths)}",
        )

    # ---- SFT pairs --------------------------------------------------------
    train_jsonl = sft / "train.jsonl"
    eval_jsonl = sft / "eval.jsonl"
    ok_train = check("SFT train.jsonl present", train_jsonl.is_file(), str(train_jsonl))
    ok_eval = check("SFT eval.jsonl present", eval_jsonl.is_file(), str(eval_jsonl))

    def load_pairs(path: pathlib.Path) -> list[dict]:
        rows: list[dict] = []
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    rows.append(json.loads(line))
        return rows

    train_rows: list[dict] = []
    eval_rows: list[dict] = []
    sft_py_chars = 0
    if ok_train:
        train_rows = load_pairs(train_jsonl)
        # Responses only, and excluding the "explain" shape whose summary
        # repeats module docstrings: source text must partition the corpus, so
        # a figure above 100% would mean duplication rather than coverage.
        sft_py_chars = sum(
            len(r["response"])
            for r in train_rows
            if str(r.get("path", "")).endswith(".py") and r.get("shape") != "explain"
        )
        missing = sum(1 for r in train_rows if not r.get("instruction") or not r.get("response"))
        check("train pairs all have instruction+response", missing == 0, f"{missing} incomplete")
        check("train set non-trivial", len(train_rows) > 100, f"{len(train_rows)} rows")
    if ok_eval:
        eval_rows = load_pairs(eval_jsonl)
        missing_e = sum(1 for r in eval_rows if not r.get("instruction") or not r.get("response"))
        check("eval pairs all have instruction+response", missing_e == 0, f"{missing_e} incomplete")
        check("eval set non-empty", len(eval_rows) > 0, f"{len(eval_rows)} rows")

    # ---- leakage: the gate is only meaningful if it is truly held out -----
    if train_rows and eval_rows:
        train_pair_paths = {r.get("path", "") for r in train_rows}
        eval_pair_paths = {r.get("path", "") for r in eval_rows}
        overlap = train_pair_paths & eval_pair_paths
        check(
            "no path appears in both train and eval pairs",
            not overlap,
            f"{len(overlap)} overlapping paths" + (f" e.g. {sorted(overlap)[:2]}" if overlap else ""),
        )
        if holdout_paths:
            outside = eval_pair_paths - holdout_paths
            check(
                "every eval pair comes from a holdout file",
                not outside,
                f"{len(outside)} eval paths not in holdout",
            )

    # ---- length profile: rows longer than max_seq_length get truncated ----
    if train_rows:
        est = [len(r["instruction"]) + len(r["response"]) for r in train_rows]
        toks = [c / CHARS_PER_TOKEN for c in est]
        too_long = sum(1 for t in toks if t > MAX_SEQ)
        check(
            f"under 5% of rows exceed max_seq_length={MAX_SEQ}",
            too_long / len(toks) < 0.05,
            f"{too_long}/{len(toks)} rows ({100 * too_long / len(toks):.1f}%), "
            f"median={sorted(toks)[len(toks) // 2]:.0f} tok, max={max(toks):.0f} tok",
            critical=False,
        )
        check(
            "no pair is absurdly small",
            min(est) > 20,
            f"smallest pair = {min(est)} chars",
        )

        # Coverage: how much source actually reaches the trainer. Measured
        # against Python chars, because that is what the pair generator targets
        # and what a coding adapter needs; the all-file ratio is reported for
        # context but is dominated by oversized non-Python and data tables.
        if ok_manifest:
            man_cov = json.loads(manifest_path.read_text(encoding="utf-8"))
            corpus_train_chars = man_cov.get("chars_train") or 0
            sft_chars = sum(est)
            if py_train_chars:
                py_cov = sft_py_chars / py_train_chars
                check(
                    "SFT pairs cover most Python source in the corpus",
                    py_cov >= 0.5,
                    f"{sft_py_chars/1e6:.1f}M of {py_train_chars/1e6:.1f}M Python chars "
                    f"({100*py_cov:.0f}%)",
                    critical=False,
                )
            if corpus_train_chars:
                results.append((
                    "INFO",
                    "all-file char coverage",
                    f"{sft_chars/1e6:.1f}M of {corpus_train_chars/1e6:.1f}M chars "
                    f"({100*sft_chars/corpus_train_chars:.0f}%), "
                    f"~{sft_chars/CHARS_PER_TOKEN/1e6:.2f}M est tokens",
                ))

    # ---- model artifacts --------------------------------------------------
    ok_cfg = check("model config.json present", (model / "config.json").is_file(), str(model))
    check("model tokenizer.json present", (model / "tokenizer.json").is_file(), str(model))
    shards = sorted(model.glob("*.safetensors")) if model.is_dir() else []
    check("model has safetensors shards", len(shards) > 0, f"{len(shards)} shards")

    if ok_cfg and shards:
        cfg = json.loads((model / "config.json").read_text(encoding="utf-8"))
        check(
            "model is a causal LM",
            "ForCausalLM" in " ".join(cfg.get("architectures") or []),
            str(cfg.get("architectures")),
        )
        on_disk = sum(s.stat().st_size for s in shards)
        idx = model / "model.safetensors.index.json"
        if idx.is_file():
            declared = json.loads(idx.read_text(encoding="utf-8"))["metadata"]["total_size"]
            check(
                "shard sizes match index total_size",
                abs(on_disk - declared) < 1e6,
                f"on_disk={on_disk/1e9:.2f} GB declared={declared/1e9:.2f} GB",
            )
            check(
                "weights look bf16-sized for the param count",
                abs(declared / 2 / 1e9 - 7.6) < 1.0,
                f"~{declared/2/1e9:.2f}B params at 2 bytes",
            )
        vocab_cfg = cfg.get("vocab_size")
        tok_path = model / "tokenizer.json"
        if tok_path.is_file() and vocab_cfg:
            tok_vocab = len(json.loads(tok_path.read_text(encoding="utf-8"))["model"]["vocab"])
            check(
                "tokenizer vocab fits model embeddings",
                tok_vocab <= int(vocab_cfg),
                f"tokenizer={tok_vocab} config={vocab_cfg}",
            )

    # ---- python stack -----------------------------------------------------
    from importlib import metadata

    want = {
        "torch": "2.",
        "transformers": "4.",
        "peft": "0.",
        "trl": "0.1",
        "datasets": "3.",
        "accelerate": "1.",
    }
    for pkg, prefix in want.items():
        try:
            ver = metadata.version(pkg)
            check(f"{pkg} importable", ver.startswith(prefix), f"{pkg}=={ver} (want {prefix}x)")
        except metadata.PackageNotFoundError:
            check(f"{pkg} importable", False, "not installed")

    # ---- scripts ----------------------------------------------------------
    for script in ("train_lora.py", "make_sft.py", "build_corpus.py", "eval_gate.py"):
        target = base / "training" / script
        if not target.is_file():
            check(f"{script} present", False, "missing")
            continue
        try:
            with tempfile.TemporaryDirectory() as td:
                py_compile.compile(
                    str(target), doraise=True, cfile=str(pathlib.Path(td) / (script + "c"))
                )
            check(f"{script} compiles", True, "ok")
        except py_compile.PyCompileError as exc:
            check(f"{script} compiles", False, str(exc)[:120])

    # ---- disk -------------------------------------------------------------
    free = shutil.disk_usage(str(base)).free / 1e12
    check("at least 50 GB free on project storage", free > 0.05, f"{free:.1f} TB free")

    # ---- report -----------------------------------------------------------
    width = max(len(n) for _, n, _ in results)
    print()
    for status, name, detail in results:
        print(f"[{status}] {name:<{width}}  {detail}")
    fails = sum(1 for s, _, _ in results if s == "FAIL")
    warns = sum(1 for s, _, _ in results if s == "WARN")
    print(f"\n{len(results)} checks — {fails} FAIL, {warns} WARN")
    print("VERDICT: FIT TO TRAIN" if fails == 0 else "VERDICT: NOT FIT — fix FAILs first")
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
