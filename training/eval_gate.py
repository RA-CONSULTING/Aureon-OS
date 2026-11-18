"""Acceptance gate: does the LoRA adapter actually beat the base model?

Scores base and tuned generations on the held-out split with objective,
deterministic metrics only — no LLM judge, so the gate cannot be talked into
a pass. Three signals:

  parse_rate     share of generated Python that compiles (implement rows only)
  symbol_recall  share of the reference's top-level names that appear in the
                 generation (implement: defs/classes/assignments;
                 explain: the `def x` / `class X` lines of the summary)
  line_f1        overlap of substantive lines, as a coarse shape check

Usage — run once per model, then compare:
  python eval_gate.py run --model M --data sft/eval.jsonl --out base.json
  python eval_gate.py run --model M --adapter out/adapter --data sft/eval.jsonl --out tuned.json
  python eval_gate.py compare --base base.json --tuned tuned.json --min-gain 0.05

  python eval_gate.py self-test        # validates the scorer, needs no model
"""

from __future__ import annotations

import argparse
import ast
import json
import pathlib
import re
import sys

from prompt_contract import SYSTEM

FENCE = re.compile(r"^\s*```[a-zA-Z0-9_+-]*\s*$", re.MULTILINE)
SYMBOL = re.compile(r"(?:def|class)\s+([A-Za-z_][A-Za-z0-9_]*)")


def strip_fences(text: str) -> str:
    return FENCE.sub("", text).strip()


def top_level_names(src: str) -> set[str]:
    try:
        tree = ast.parse(src)
    except (SyntaxError, ValueError):
        return set()
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
    return names


def reference_symbols(row: dict, ref: str) -> set[str]:
    if row.get("shape") == "explain":
        return set(SYMBOL.findall(ref))
    return top_level_names(ref)


def substantive_lines(text: str) -> set[str]:
    return {ln.strip() for ln in text.splitlines() if len(ln.strip()) >= 12}


def line_f1(gen: str, ref: str) -> float:
    g, r = substantive_lines(gen), substantive_lines(ref)
    if not g or not r:
        return 0.0
    hit = len(g & r)
    if not hit:
        return 0.0
    precision, recall = hit / len(g), hit / len(r)
    return 2 * precision * recall / (precision + recall)


def score_row(row: dict, gen: str) -> dict:
    ref = row["response"]
    body = strip_fences(gen)
    out: dict = {"shape": row.get("shape", "implement"), "path": row.get("path", "")}

    if out["shape"] == "implement" and str(row.get("path", "")).endswith(".py"):
        # ast.parse("") is a valid empty module, so require real statements —
        # otherwise a model that emits nothing would score a perfect parse rate.
        out["parses"] = False
        if body.strip():
            try:
                out["parses"] = bool(ast.parse(body).body)
            except (SyntaxError, ValueError):
                out["parses"] = False

    expected = reference_symbols(row, ref)
    if expected:
        out["symbol_recall"] = sum(1 for n in expected if re.search(rf"\b{re.escape(n)}\b", body)) / len(expected)
    else:
        out["symbol_recall"] = None

    out["line_f1"] = line_f1(body, ref)
    return out


def aggregate(rows: list[dict]) -> dict:
    parse = [r["parses"] for r in rows if "parses" in r]
    syms = [r["symbol_recall"] for r in rows if r.get("symbol_recall") is not None]
    f1s = [r["line_f1"] for r in rows]

    def mean(xs: list[float]) -> float:
        return sum(xs) / len(xs) if xs else 0.0

    agg = {
        "rows": len(rows),
        "parse_rate": mean([1.0 if p else 0.0 for p in parse]),
        "parse_scored": len(parse),
        "symbol_recall": mean(syms),
        "symbol_scored": len(syms),
        "line_f1": mean(f1s),
    }
    for shape in ("implement", "explain"):
        sub = [r for r in rows if r["shape"] == shape]
        agg[f"{shape}_rows"] = len(sub)
        agg[f"{shape}_symbol_recall"] = mean(
            [r["symbol_recall"] for r in sub if r.get("symbol_recall") is not None]
        )
        agg[f"{shape}_line_f1"] = mean([r["line_f1"] for r in sub])
    return agg


def load_rows(path: pathlib.Path, limit: int) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))
    if limit:
        rows = rows[:limit]
    return rows


def generate_all(args: argparse.Namespace, rows: list[dict]) -> list[str]:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    # SYSTEM comes from prompt_contract: the gate must score the model under
    # exactly the prompt it was trained with, or a good adapter fails here.
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "left"

    dtype = torch.bfloat16 if (torch.cuda.is_available() and torch.cuda.is_bf16_supported()) else torch.float32
    model = AutoModelForCausalLM.from_pretrained(
        args.model, dtype=dtype, attn_implementation="sdpa", device_map="auto" if torch.cuda.is_available() else None
    )
    if args.adapter:
        from peft import PeftModel

        model = PeftModel.from_pretrained(model, args.adapter)
    model.eval()

    if args.raw:
        from aureon_chat_server import format_prompt

    prompts = []
    for row in rows:
        messages = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": row["instruction"]},
        ]
        if args.raw:
            text = format_prompt(messages)
        else:
            try:
                text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            except Exception:
                text = f"### Instruction\n{row['instruction']}\n\n### Response\n"
        prompts.append(text)

    generations: list[str] = []
    with torch.no_grad():
        for start in range(0, len(prompts), args.batch_size):
            chunk = prompts[start:start + args.batch_size]
            enc = tokenizer(chunk, return_tensors="pt", padding=True, truncation=True, max_length=args.max_prompt_tokens)
            # The own-model tokenizer is a raw tokenizers wrapper and emits
            # token_type_ids, which causal generate() rejects outright.
            enc.pop("token_type_ids", None)
            enc = {k: v.to(model.device) for k, v in enc.items()}
            ids = model.generate(
                **enc,
                max_new_tokens=args.max_new_tokens,
                do_sample=False,
                num_beams=1,
                pad_token_id=tokenizer.pad_token_id,
            )
            for i in range(len(chunk)):
                new = ids[i][enc["input_ids"].shape[1]:]
                generations.append(tokenizer.decode(new, skip_special_tokens=True))
            print(f"[eval] {min(start + args.batch_size, len(prompts))}/{len(prompts)}", flush=True)
    return generations


def cmd_run(args: argparse.Namespace) -> int:
    rows = load_rows(pathlib.Path(args.data), args.limit)

    if args.answers:
        # Re-score saved generations instead of re-running the model.
        saved = json.loads(pathlib.Path(args.answers).read_text(encoding="utf-8"))
        generations = saved["generations"]
    else:
        generations = generate_all(args, rows)

    scored = [score_row(row, gen) for row, gen in zip(rows, generations)]
    report = {
        "model": args.model,
        "adapter": args.adapter or None,
        "data": str(args.data),
        "rows": len(scored),
        "max_new_tokens": args.max_new_tokens,
        "aggregate": aggregate(scored),
        "scores": scored,
        "generations": generations,
    }
    pathlib.Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["aggregate"], indent=2))
    print(f"[eval] report -> {args.out}", flush=True)
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    base = json.loads(pathlib.Path(args.base).read_text(encoding="utf-8"))
    tuned = json.loads(pathlib.Path(args.tuned).read_text(encoding="utf-8"))
    b, t = base["aggregate"], tuned["aggregate"]

    gain_sym = t["symbol_recall"] - b["symbol_recall"]
    gain_f1 = t["line_f1"] - b["line_f1"]
    gate_parse = t["parse_rate"] >= b["parse_rate"] - args.parse_tolerance

    print(f"{'metric':<22}{'base':>10}{'tuned':>10}{'delta':>10}")
    for key in ("parse_rate", "symbol_recall", "line_f1", "implement_symbol_recall", "explain_symbol_recall"):
        if key in b and key in t:
            print(f"{key:<22}{b[key]:>10.4f}{t[key]:>10.4f}{t[key] - b[key]:>+10.4f}")

    checks = {
        f"symbol_recall gain >= {args.min_gain}": gain_sym >= args.min_gain,
        "parse_rate not regressed": gate_parse,
        f"line_f1 gain >= {args.min_f1_gain}": gain_f1 >= args.min_f1_gain,
    }
    for label, ok in checks.items():
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")

    verdict = all(checks.values())
    print(f"\nGATE: {'PASS — adapter is shippable' if verdict else 'FAIL — do not ship'}")
    return 0 if verdict else 1


def cmd_self_test() -> int:
    row_py = {
        "instruction": "Write the module.",
        "response": "import os\n\n\ndef load_config(path):\n    \"\"\"Read the config.\"\"\"\n    return os.path.join(path, 'x')\n\n\nclass Registry:\n    pass\n",
        "path": "a/b.py",
        "shape": "implement",
    }
    row_ex = {
        "instruction": "Describe it.",
        "response": "`a/b.py`\n\nReads config.\n\nPublic surface:\n- def load_config(...)\n- class Registry",
        "path": "a/b.py",
        "shape": "explain",
    }
    perfect = [score_row(row_py, row_py["response"]), score_row(row_ex, row_ex["response"])]
    empty = [score_row(row_py, ""), score_row(row_ex, "")]

    for name, rows, expect_recall, expect_parse in (
        ("reference-vs-itself", perfect, 1.0, 1.0),
        ("empty-generation", empty, 0.0, 0.0),
    ):
        agg = aggregate(rows)
        ok = abs(agg["symbol_recall"] - expect_recall) < 1e-9 and abs(agg["parse_rate"] - expect_parse) < 1e-9
        print(f"[self-test] {name:<20} recall={agg['symbol_recall']:.3f} parse={agg['parse_rate']:.3f} -> {'OK' if ok else 'BAD'}")
        if not ok:
            return 1

    fenced = score_row(row_py, "```python\n" + row_py["response"] + "\n```")
    print(f"[self-test] fence-stripping     recall={fenced['symbol_recall']:.3f} parses={fenced['parses']} "
          f"-> {'OK' if fenced['parses'] and fenced['symbol_recall'] == 1.0 else 'BAD'}")
    return 0 if fenced["parses"] and fenced["symbol_recall"] == 1.0 else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="score one model (optionally with an adapter)")
    run.add_argument("--model", required=True)
    run.add_argument("--adapter", default=None)
    run.add_argument("--data", required=True)
    run.add_argument("--out", required=True)
    run.add_argument("--limit", type=int, default=0)
    run.add_argument("--batch-size", type=int, default=4)
    run.add_argument("--max-new-tokens", type=int, default=1024)
    run.add_argument("--max-prompt-tokens", type=int, default=2048)
    run.add_argument("--raw", action="store_true",
                     help="prompt exactly as aureon_chat_server.format_prompt "
                          "does (system:/user:/assistant: plain text) instead "
                          "of apply_chat_template. Required when scoring the "
                          "from-scratch model: its tokenizer has no chat "
                          "template, so the chat prompt is the contract.")
    run.add_argument("--answers", default=None, help="re-score a saved report's generations")
    run.set_defaults(func=cmd_run)

    cmp_ = sub.add_parser("compare", help="apply the acceptance threshold")
    cmp_.add_argument("--base", required=True)
    cmp_.add_argument("--tuned", required=True)
    cmp_.add_argument("--min-gain", type=float, default=0.05)
    cmp_.add_argument("--min-f1-gain", type=float, default=0.0)
    cmp_.add_argument("--parse-tolerance", type=float, default=0.02)
    cmp_.set_defaults(func=cmd_compare)

    st = sub.add_parser("self-test", help="validate the scorer without a model")
    st.set_defaults(func=lambda _a: cmd_self_test())

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
