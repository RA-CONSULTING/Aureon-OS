"""
Open-source benchmark harness — Aureon measured against the published
competition, with the claim discipline the rest of the repo lives by.

Three rules, enforced by benchmark b62:

  1. AUREON'S NUMBERS ARE MEASURED. Every item runs through the ONE DOOR
     (``AureonCognition`` — envelope, gates, conscience) with whatever
     adapter the operator honestly resolves on this machine. When the
     adapter is offline/keyless the per-item status says ``honest_
     unavailable`` and the score is reported as exactly what it is —
     never invented, never extrapolated.
  2. THE COMPETITION'S NUMBERS ARE CITED, NEVER CLAIMED. Rows for Kimi K2,
     DeepSeek-V3, Llama, Qwen, GPT-4o carry the vendor's own published
     figure, a source URL, and the label ``vendor_published`` — they were
     not measured here and the table says so.
  3. THE ARCHITECTURE COMPARISON CLAIMS ONLY WHAT IS PINNED. The contract
     columns (enforced envelope, measured knowledge reach, conscience
     veto, coherence gate, heart charter, pipeline-order pin) cite the
     Tier-A benchmark that measures each one (b53–b61). A raw model API
     that does not ship the feature is marked ``not offered`` from its
     public documentation, not from speculation.

Datasets are OPEN SOURCES fetched with provenance stamps (URL, sha256,
license, retrieval time) and cached under ``data/research/open_benchmarks/``.
Offline, the harness runs on its cache or a LABELED fixture and says so.
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import logging
import re
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List

logger = logging.getLogger("aureon.analytics.open_benchmark")

_REPO_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = _REPO_ROOT / "data" / "research" / "open_benchmarks"

# ── the open sources (permissive licenses, raw URLs) ───────────────────────

DATASETS: Dict[str, Dict[str, str]] = {
    "gsm8k": {
        "url": ("https://raw.githubusercontent.com/openai/grade-school-math/"
                "master/grade_school_math/data/test.jsonl"),
        "license": "MIT (openai/grade-school-math)",
        "task": "grade-school math word problems (exact-match final number)",
    },
    "humaneval": {
        "url": ("https://raw.githubusercontent.com/openai/human-eval/"
                "master/data/HumanEval.jsonl.gz"),
        "license": "MIT (openai/human-eval)",
        "task": "Python function synthesis (pass@1 via guarded execution)",
    },
}

# ── the competition (vendor-published, cited — NOT measured here) ──────────

VENDOR_PUBLISHED = "vendor_published — cited from the source URL, not measured here"

COMPETITION: List[Dict[str, Any]] = [
    {"model": "Kimi K2 Instruct (Moonshot AI, open weights)",
     "source": "https://huggingface.co/moonshotai/Kimi-K2-Instruct",
     "label": VENDOR_PUBLISHED,
     "scores": {"humaneval_pass@1": None, "gsm8k": None,
                "note": "vendor card leads with LiveCodeBench/MATH-500/agentic "
                        "suites; classic GSM8K/HumanEval not the headline rows — "
                        "cite the card directly rather than transplant numbers"}},
    {"model": "DeepSeek-V3 (open weights)",
     "source": "https://huggingface.co/deepseek-ai/DeepSeek-V3",
     "label": VENDOR_PUBLISHED,
     "scores": {"humaneval_pass@1": None, "gsm8k": None,
                "note": "see model card benchmark table at the source URL"}},
    {"model": "Llama 3.1 405B Instruct (Meta, open weights)",
     "source": "https://huggingface.co/meta-llama/Llama-3.1-405B-Instruct",
     "label": VENDOR_PUBLISHED,
     "scores": {"humaneval_pass@1": None, "gsm8k": None,
                "note": "see model card benchmark table at the source URL"}},
    {"model": "Qwen2.5-72B-Instruct (Alibaba, open weights)",
     "source": "https://huggingface.co/Qwen/Qwen2.5-72B-Instruct",
     "label": VENDOR_PUBLISHED,
     "scores": {"humaneval_pass@1": None, "gsm8k": None,
                "note": "see model card benchmark table at the source URL"}},
]

# ── the architectural contract (measured here, pinned by Tier-A) ──────────

ARCHITECTURE_CONTRACT: List[Dict[str, str]] = [
    {"feature": "Enforced response envelope (sources named or absence stated)",
     "aureon": "measured — b53", "raw_model_api": "not offered"},
    {"feature": "Measured knowledge reach + reach class on every answer",
     "aureon": "measured — b57", "raw_model_api": "not offered"},
    {"feature": "Conscience veto + hard authority boundaries (wall first)",
     "aureon": "measured — b61", "raw_model_api": "not offered"},
    {"feature": "Field-driven coherence aperture (tighten-only, live signal)",
     "aureon": "measured — b58", "raw_model_api": "not offered"},
    {"feature": "Film-Reel actualization ledger (realized vs parked)",
     "aureon": "measured — b54", "raw_model_api": "not offered"},
    {"feature": "Bake-until-complete with honest incompleteness seal",
     "aureon": "measured — b56", "raw_model_api": "not offered"},
    {"feature": "Heart charter (alive / love / power consequences stated)",
     "aureon": "measured — b59", "raw_model_api": "not offered"},
    {"feature": "Deterministic pipeline-order pin (the flow itself tested)",
     "aureon": "measured — b61", "raw_model_api": "not offered"},
]


# ── provenance-stamped fetch (open sources only) ───────────────────────────


@dataclass
class Dataset:
    name: str
    items: List[Dict[str, Any]]
    provenance: Dict[str, Any] = field(default_factory=dict)


def _stamp(name: str, url: str, raw: bytes, license_: str) -> Dict[str, Any]:
    return {"source_url": url, "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw), "license": license_,
            "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}


def fetch_dataset(name: str, limit: int = 50, timeout: float = 60.0,
                  offline: bool = False,
                  cache_dir: Path | None = None) -> Dataset:
    """Fetch an open dataset with a provenance stamp, caching to disk.
    Offline (or on any failure) the cache is used if present; otherwise the
    result is honestly empty with the blocker named — never a fabricated set."""
    spec = DATASETS[name]
    cache_root = cache_dir or CACHE_DIR
    cache_root.mkdir(parents=True, exist_ok=True)
    cache = cache_root / f"{name}.jsonl"
    prov_path = cache_root / f"{name}.provenance.json"

    raw: bytes | None = None
    if not offline:
        try:
            with urllib.request.urlopen(spec["url"], timeout=timeout) as resp:
                raw = resp.read()
        except Exception as exc:  # noqa: BLE001 — an unreachable source is a named blocker
            logger.warning("open benchmark fetch failed for %s: %s", name, exc)
    if raw is not None:
        raw_text = (gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
                    if spec["url"].endswith(".gz") else raw)
        cache.write_bytes(raw_text)
        prov_path.write_text(json.dumps(_stamp(name, spec["url"], raw,
                                               spec["license"]), indent=2),
                             encoding="utf-8")
    if not cache.exists():
        return Dataset(name=name, items=[], provenance={
            "status": "honest_unavailable",
            "blocker": f"source unreachable and no cache: {spec['url']}"})
    items = [json.loads(line) for line in
             cache.read_text(encoding="utf-8").splitlines() if line.strip()]
    provenance = (json.loads(prov_path.read_text(encoding="utf-8"))
                  if prov_path.exists() else {"status": "cache_without_stamp"})
    provenance.update({"task": spec["task"], "items_used": min(limit, len(items)),
                       "items_total": len(items)})
    return Dataset(name=name, items=items[:limit], provenance=provenance)


# ── run through the ONE DOOR, score honestly ───────────────────────────────

_NUM = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


def _final_number(text: str) -> str | None:
    hits = _NUM.findall(text or "")
    return hits[-1].replace(",", "") if hits else None


def _gsm8k_gold(answer: str) -> str | None:
    tail = (answer or "").split("####")[-1]
    return _final_number(tail)


def run_gsm8k(cog: Any, dataset: Dataset) -> Dict[str, Any]:
    """Measured GSM8K subset accuracy through the one door. Statuses are
    counted; an honest_unavailable adapter yields score None, never a guess."""
    results, correct, ok = [], 0, 0
    for item in dataset.items:
        res = cog.reason("Solve this math problem. End with the final "
                         f"numeric answer.\n\n{item['question']}")
        status = res.status()
        got = _final_number(res.text) if status == "ok" else None
        gold = _gsm8k_gold(item.get("answer", ""))
        hit = bool(status == "ok" and got is not None and got == gold)
        ok += status == "ok"
        correct += hit
        results.append({"status": status, "got": got, "gold": gold,
                        "correct": hit,
                        "envelope": bool(res.envelope().get("trace_id"))})
    n = len(dataset.items)
    return {"dataset": "gsm8k", "n": n, "ok_turns": ok, "correct": correct,
            "accuracy": (round(correct / n, 4) if n and ok else None),
            "provenance": dataset.provenance, "results": results}


_CODE_FENCE = re.compile(r"```(?:python|py)?[ \t]*\n(.*?)```", re.DOTALL)


def _extract_code(text: str) -> str:
    """Pull the code out of a chat answer — fenced ```python blocks first
    (standard harness practice: a raw markdown fence is a Python syntax
    error, which would fail every fenced answer regardless of the code
    inside), falling back to the raw text when the answer is already bare
    code."""
    blocks = _CODE_FENCE.findall(text or "")
    if blocks:
        return "\n\n".join(b.strip("\n") for b in blocks)
    return text or ""


def _guarded_exec(program: str, timeout_s: float = 10.0) -> bool:
    """HumanEval check execution in a subprocess with a hard timeout — the
    standard harness practice, on an offline box, for OUR adapter's output."""
    import subprocess
    import sys

    try:
        proc = subprocess.run([sys.executable, "-c", program],
                              capture_output=True, timeout=timeout_s)
        return proc.returncode == 0
    except Exception:  # noqa: BLE001 — any failure is a fail, never a pass
        return False


def run_humaneval(cog: Any, dataset: Dataset) -> Dict[str, Any]:
    """Measured HumanEval subset pass@1 through the one door."""
    results, passed, ok = [], 0, 0
    for item in dataset.items:
        res = cog.reason(
            "Complete this Python function. Reply with the complete function "
            "definition inside one ```python code block — the code must be in "
            "the answer text itself; do not write it to a file.\n\n"
            f"{item['prompt']}")
        status = res.status()
        hit = False
        if status == "ok" and res.text:
            program = (item["prompt"] + "\n" + _extract_code(res.text) + "\n"
                       + item["test"] + f"\ncheck({item['entry_point']})\n")
            hit = _guarded_exec(program)
        ok += status == "ok"
        passed += hit
        results.append({"task_id": item.get("task_id"), "status": status,
                        "passed": hit})
    n = len(dataset.items)
    return {"dataset": "humaneval", "n": n, "ok_turns": ok, "passed": passed,
            "pass_at_1": (round(passed / n, 4) if n and ok else None),
            "provenance": dataset.provenance, "results": results}


# ── the full comparison run ────────────────────────────────────────────────


def run_open_benchmark(limit: int = 25, offline: bool = False,
                       cog_factory: Callable[[], Any] | None = None) -> Dict[str, Any]:
    """Fetch the open sets, run Aureon through the one door, and assemble the
    honest comparison: measured Aureon rows, cited competition rows, pinned
    architecture contract."""
    if cog_factory is None:
        def cog_factory() -> Any:
            from aureon.operator.cognition import AureonCognition

            return AureonCognition(join_mesh=False, mesh_broadcast=False)
    cog = cog_factory()
    adapter = getattr(cog, "adapter", None)
    adapter_name = type(adapter).__name__
    model_name = str(getattr(adapter, "model", "") or "")

    gsm = run_gsm8k(cog, fetch_dataset("gsm8k", limit=limit, offline=offline))
    he = run_humaneval(cog, fetch_dataset("humaneval", limit=limit,
                                          offline=offline))
    return {
        "adapter": adapter_name,
        "model": model_name,
        "aureon_measured": {"gsm8k": gsm, "humaneval": he},
        "competition_cited": COMPETITION,
        "architecture_contract": ARCHITECTURE_CONTRACT,
        "honesty": ("Aureon rows are measured on THIS machine's resolved "
                    "adapter and scale with the provider set behind the one "
                    "door; competition rows are vendor-published citations; "
                    "the architecture columns cite the Tier-A benchmark that "
                    "pins each feature."),
    }


def write_report(payload: Dict[str, Any], out_md: Path, out_json: Path) -> None:
    out_json.write_text(json.dumps(payload, indent=2, default=str),
                        encoding="utf-8")
    g = payload["aureon_measured"]["gsm8k"]
    h = payload["aureon_measured"]["humaneval"]
    lines = [
        "# Open benchmark — Aureon vs the published competition", "",
        f"Adapter resolved by the one door: `{payload['adapter']}`"
        + (f" — model `{payload['model']}`" if payload.get("model") else ""), "",
        "## Aureon (measured here)", "",
        "| Set | n | ok turns | score |", "|---|---|---|---|",
        f"| GSM8K | {g['n']} | {g['ok_turns']} | "
        f"{g['accuracy'] if g['accuracy'] is not None else 'honest_unavailable'} |",
        f"| HumanEval | {h['n']} | {h['ok_turns']} | "
        f"{h['pass_at_1'] if h['pass_at_1'] is not None else 'honest_unavailable'} |",
        "", "## Competition (vendor-published, cited)", "",
        "| Model | Source |", "|---|---|",
    ]
    lines += [f"| {c['model']} | {c['source']} |" for c in payload["competition_cited"]]
    lines += ["", "## Architectural contract (pinned)", "",
              "| Feature | Aureon | Raw model API |", "|---|---|---|"]
    lines += [f"| {r['feature']} | {r['aureon']} | {r['raw_model_api']} |"
              for r in payload["architecture_contract"]]
    lines += ["", f"> {payload['honesty']}", ""]
    out_md.write_text("\n".join(lines), encoding="utf-8")


def main(argv: List[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=25)
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--out", type=Path,
                    default=_REPO_ROOT / "docs" / "OPEN_BENCHMARK.md")
    args = ap.parse_args(argv)
    payload = run_open_benchmark(limit=args.limit, offline=args.offline)
    write_report(payload, args.out, args.out.with_suffix(".json"))
    g = payload["aureon_measured"]["gsm8k"]
    print(f"gsm8k: {g['correct']}/{g['n']} (accuracy={g['accuracy']})")
    h = payload["aureon_measured"]["humaneval"]
    print(f"humaneval: {h['passed']}/{h['n']} (pass@1={h['pass_at_1']})")
    return 0


__all__ = ["DATASETS", "COMPETITION", "ARCHITECTURE_CONTRACT", "Dataset",
           "fetch_dataset", "run_gsm8k", "run_humaneval",
           "run_open_benchmark", "write_report", "main"]

if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
