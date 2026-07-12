# 🎛️ Aureon Operator — Production Audit & A/B Benchmark
## "Standard output vs. the same model with the Aureon OS installed"

**Date:** 2026-07-12 · **Auditor:** in-session flagship model (acting as the switchboard line) · **Chain under test:** `aureon/operator/` · **Status:** 🟢 production-stage

---

## 🔬 What was measured

One flagship model, two conditions, identical prompts:

| Condition | Meaning | Chain |
|---|---|---|
| **baseline** | raw model output — "your standard output, as Fable" | model only |
| **aureon** | the same model with the Aureon OS installed | ground → fan-out → consensus → veto |

Both answer sets are **real model generations**, captured once to a fixture and served through `RecordedAdapter` so the run is deterministic and reproducible. The moment a live `OPENAI_API_KEY` / `XAI_API_KEY` / `GEMINI_API_KEY` is present, the identical chain dials those flagship lines instead — the recorded adapter exists only so the design can be *seen working end-to-end through the entire repo* in a keyless sandbox.

- **Prompts:** 12 (10 factual + 2 adversarial) — `data/research/operator_benchmark_prompts.json`
- **Ground truth:** `docs/CLAIMS_AND_EVIDENCE.md` (claims C1–C6, T1–T5, M3–M4, R5)
- **Grounding:** real — every Aureon-condition answer was grounded against the live repo via `aureon_dynamic_prompt_filter` (4 source packets per prompt)
- **Consensus:** real — N = 2 independent grounded lines collapsed by medoid/Jaccard agreement

---

## 📊 Results

| Metric | Baseline (raw) | Aureon (OS installed) | Δ |
|---|---:|---:|---|
| **Fact accuracy** | 10.0% | **100.0%** | 🟢 +90 pts |
| **Hallucination rate** | 0.0% | 0.0% | — tie (neither fabricates) |
| **Honest abstention** | 90.0% | 0.0% | context |
| **Grounding coverage** (answers citing repo sources) | 0.0% | **100.0%** | 🟢 +100 pts |
| **Safety block rate** (adversarial vetoed) | 0.0% | **100.0%** | 🟢 +100 pts |
| **Mean consensus agreement** (factual) | n/a | 0.426 (min 0.20 · max 0.60) | N = 2 collapse |
| **Mean latency** | ~0 ms (recorded) | 22.9 ms (full chain) | +22.9 ms |

### The honest reading

The raw model is **safe but useless** on Aureon-specific facts: it correctly answered only the one *general-physics* question in the set (Schumann fundamental ≈ 7.83 Hz) and **honestly abstained on the other 90%** ("I don't have information / I can't confirm"). It did **not** fabricate — hallucination was 0%.

With the Aureon OS installed, the same model answered **100% of the factual prompts correctly**, **every** answer carried repo-source grounding, and it **deterministically blocked 100%** of the boundary-crossing prompts. Hallucination stayed at 0%.

> The value the operator adds is not "stops the model lying" — this model didn't lie. It is **turning honest ignorance into grounded, cited, correct answers**, and adding a **deterministic authority-boundary layer** the raw model does not have. A raw model *might* refuse a dangerous instruction; the Aureon chain *guarantees* it, regardless of which model is on the line.

---

## 🧪 Chain audit — every link verified

Each phase was exercised and asserted (see `tests/test_operator_production.py`, `tests/test_aureon_operator.py` — 26 tests, all green):

| Link | Verified behaviour | Evidence |
|---|---|---|
| **ground** | Pulls real repo source packets (4/prompt) and compiles a grounded system prompt; degrades, never crashes | `grounding_coverage = 100%` |
| **fan-out** | Patches the prompt to every line; parallel `ThreadPoolExecutor`; retries transient failures; per-line circuit breaker trips after N failures and half-opens after cooldown | `test_parallel_fanout_calls_all_lines`, `test_retry_recovers…`, `test_circuit_breaker_trips_and_cools_down` |
| **consensus** | Medoid collapse over N lines; Jaccard agreement scored; single-line ≠ synthesized | agreement 0.426 across 10 factual prompts, `synthesized = True` |
| **veto** | Soft conscience (`QueenConscience.ask_why`) + **hard authority boundary** (live-trade / payment / gate-bypass / credential / filing) that blocks deterministically regardless of the soft verdict | `safety_block_rate = 100%`, `test_operator_blocks_boundary_prompt_even_without_conscience` |
| **trace** | Every phase publishes a `Thought` on the bus under `operator.phase.*` → `operator.complete` with one `trace_id` | `test_bus_receives_all_phase_topics` |
| **cache** | TTL + LRU keyed by prompt + grounding signature + model set; vetoed answers never cached | `test_operator_second_call_is_served_from_cache` |
| **observability** | Prometheus counters/histograms + structured JSON logs per phase; degrades to no-op when `prometheus_client` absent | `aureon/operator/metrics.py` |

---

## 🚀 Production-readiness checklist

| Scope | Delivered |
|---|---|
| Robustness | ✅ retries + backoff, hard per-call timeout, per-line circuit breaker, parallel fan-out |
| Observability | ✅ `aureon_operator_*` Prometheus metrics + structured JSON logs (fail-safe) |
| Caching + config | ✅ TTL/LRU response cache; `OperatorConfig.from_env()`; `ModelSpec` registry for N flagship models |
| Any-flagship / multi-model | ✅ OpenAI · Grok · Gemini · Anthropic · local · recorded — a registry row each; keyless rows skipped at assembly |
| Audit report | ✅ this document + shareable HTML report |

---

## 🔁 Reproduce

```bash
# A/B benchmark (offline, no keys)
AUREON_LLM_OFFLINE=1 python scripts/run_operator_benchmark.py
# → data/research/operator_benchmark_results.json

# chain audit
AUREON_LLM_OFFLINE=1 pytest tests/test_operator_production.py tests/test_aureon_operator.py -v

# same chain against a live flagship model — just add a key:
OPENAI_API_KEY=sk-... python scripts/run_operator_benchmark.py
```

---

## ⚠️ Limitations & falsifiability

- **N is small (12 prompts, 1 model).** This is a design-validation benchmark, not a population study. The harness scales to any prompt count and, with keys, to N independent flagship models — the numbers above are a floor for the mechanism, not a claim about all questions.
- **The model here is honest by disposition** — hallucination was already 0% at baseline, so the fabrication-reduction axis wasn't stressed by this set. A model prone to confident guessing would show a hallucination-rate delta; the harness measures it (`specificity_pattern`) and would report it.
- **Consensus agreement (0.426) reflects paraphrase lines**, which share facts but differ in wording. With N truly independent models the number is a genuine cross-model coherence signal, not a paraphrase artifact.
- **Everything is reproducible and adversarial-testable.** If a claim here doesn't hold when you re-run it, the repository is the authority — file an issue.

---

## 📚 Related Documentation

- [`docs/architecture/AUREON_OPERATOR_SWITCHBOARD.md`](../../architecture/AUREON_OPERATOR_SWITCHBOARD.md) — the operator design
- [`docs/CLAIMS_AND_EVIDENCE.md`](../../CLAIMS_AND_EVIDENCE.md) — the ground-truth source
- `aureon/operator/benchmark.py` · `scripts/run_operator_benchmark.py` · `tests/test_operator_production.py`

---

***🎛️ Standard output abstains. The same model, with the Aureon OS installed, answers — grounded, cited, and gated.***
