# Data Provenance Audit — what is real, what is withheld, what is generated

*Audit date: 2026-07-25 · scope: `main` at `3a585a1` · method: read the producers, run them cold, read
what came out.*

The rule this audit enforces is the repo's own: **a dormant feature reports `no_data`, it never
guesses.** A fabricated number on a live topic is worse than a missing one, because a missing number
is visibly missing and a fabricated one is not.

Every finding below was reproduced by running the code in a clean offline process, not inferred from
reading it. Each fix is pinned by tests named in the last column.

---

## 1 · The freshness of the HNC field

`aureon/core/hnc_field.py` reads the canonical field across process boundaries through persisted
trace files, and **a file on disk has no idea how old it is.** Before this audit `available=True` meant
only "a row exists somewhere":

| Reader | What it served | Observed on a clean checkout |
|---|---|---|
| `_read_field_from_trace` | the **last line** of `state/hnc_live_trace.jsonl`, whatever its age | a coherence figure written by a daemon that had since stopped, served to dashboards as the current field |
| `read_subfields` | up to 200 rows from the `symbolic_subfield` trace, **with no age check** | rows carried *no timestamp at all* — staleness was not ignored, it was unknowable |

Reproduction, in a fresh process with no producer running: `blend_field()` returned
`available: true`, `symbolic_life_score: 0.6156`, two contributors.

**Fixed.** Rows are stamped at publish, refused once older than `FIELD_MAX_AGE_S` (300 s, tunable via
`AUREON_HNC_FIELD_MAX_AGE_S`), and refused outright when the age cannot be established. Freshness is
checked **per row**, so one live producer cannot revive a dead one that shares the trace. A producer
whose clock runs slightly ahead is tolerated (60 s); an absurd future stamp is not.

Pinned by `tests/test_hnc_field_freshness.py` (10 tests).

## 2 · The Queen live runner's feed

`aureon/trading/aureon_queen_live_runner.py` streamed, every 2 seconds, under the banner
"REAL INTELLIGENCE MODE":

| Topic | What it actually was |
|---|---|
| `market.price` | prices seeded `50000 + random()*10000`, random-walked each tick; `volume_24h = random()*1000000`; `change_1h = (random()-0.5)*5` |
| `market.momentum` | "top momentum" symbol chosen by `max(key=lambda s: random())`, random 1h change, random volume-surge flag |
| `whale.orderbook` | random bid/ask depth, an imbalance computed from those random numbers, two invented "walls" |
| `bot.detected` · `firm.activity` · `counter.strategy` | **trading-firm attribution from an md5 of `<symbol>_<current minute>`**, firing on ~60% of hashes, "confidence" 0.65–0.98 read off the hash's low digits |

Naming a real firm as the counterparty to activity nobody observed is the least defensible fake data
in this repo.

**Fixed.** Every generated value sits behind `simulation_fallback_allowed()` —
`AUREON_ALLOW_SIMULATED_FEED`, default **off**. With it off the runner emits only what a real source
quoted and reports the rest as `no_data` with a named blocker (`no_orderbook_feed_connected`,
`no_price_history_source`, `no_order_flow_source_for_firm_attribution`). With it on, every thought is
stamped `test_fixture`. All thoughts now carry a `truth_status` from
`aureon/observer/real_data_contract.py` in the envelope, so a consumer reads provenance without
knowing which producer wrote the row.

Two path bugs found alongside, both silent:

* the hub dashboard's spawn path pointed at `command_centers/aureon_queen_live_runner.py`, which has
  never existed — so `_ensure_live_runner()` always failed and reported "not detected";
* the runner wrote `aureon/trading/thoughts.jsonl` while the dashboard read
  `aureon/command_centers/thoughts.jsonl` — **two different files**, so nothing the runner emitted
  ever arrived. Both now resolve one path, overridable with `AUREON_THOUGHTS_FILE`.

Fixing the spawn path would have started launching a background producer on every dashboard boot, so
auto-start is opt-in via `AUREON_AUTOSTART_LIVE_RUNNER`; opening a dashboard stays a read-only act.

Pinned by `tests/test_live_runner_feed_provenance.py` (15 tests).

This file has been **removed from `QUARANTINE_EXACT_PATHS`** in
`scripts/validation/validate_real_data_contract.py`: it now passes the operational scan on its own
merits (0 errors) rather than by exemption. Do not re-add it.

## 3 · QGITA's decision path

`aureon/wisdom/aureon_qgita.py` places real Binance orders. Two inputs were not real:

* `DecisionFusion.generate_model_signal` was labelled *"Simulate ensemble model signals"* and did
  exactly that — four named models (lstm, randomForest, xgboost, transformer), each scored
  `normalized_trend + bias + (random()-0.5)*0.1` with a random confidence. That stand-in carried
  **60% of the fused decision weight**.
* `RiskManager.evaluate` computed `win_rate = 0.55*confidence + 0.45*random()` and fed it to the
  Kelly criterion, so the same signal sized differently every time it appeared.

**Fixed.** The simulated ensemble is opt-in *and* paper-only (`--simulated-models`, refused when not
`--dry-run`). With no ensemble the fusion runs on the QGITA lighthouse alone; with neither it holds
and names `blocker: no_model_ensemble_connected` instead of emitting a coin-flip. Kelly uses the
session's **measured** win rate once 20 trades have closed (fed by `record_outcome` on every close),
and a deterministic function of confidence before that.

Pinned by `tests/test_qgita_decision_provenance.py` (11 tests).

**Honest scoping note:** the QGITA *framework* (`aureon/wisdom/aureon_qgita_framework.py`) was checked
and is clean — its only `np.random` is inside `if __name__ == "__main__"`, and `QGITAMarketAnalyzer`
computes FTCP/Lighthouse results from the price buffer it is fed. The live path through
`aureon/bridges/aureon_hnc_live_connector.py` feeds it real price history.

## 4 · Dr Auris Throne's cosmic state

`CosmicState` gives every field a plausible resting value — `schumann_hz = 7.83`,
`schumann_coherence = 0.5`, `cosmic_score = 0.5`, `earth_blessing = 0.5`, `kp_index = 0.0` — so a
state assembled with **nothing connected looked exactly like a quiet, measured sky**. The Λ(t) step
then fed those defaults into the Lambda engine unconditionally and published the result as the
`dr_auris_throne` sub-field, putting a fabricated cosmic contribution into the organism's shared HNC
consensus, the grounded-action gate and the Queen's world sense.

**Fixed.** Every cycle records which sources answered (`sources_live` / `sources_unavailable`),
`data_available` is False when none did, and Λ(t) is **skipped** rather than computed from defaults —
so no sub-field is published either. Provenance travels in the `auris.throne.cosmic_state` payload.

Pinned by `tests/test_auris_throne_provenance.py` (10 tests).

## 5 · Checked and found honest

Not everything flagged by a pattern scan is a defect. These were examined and left alone, because the
code was already truthful:

| System | Finding |
|---|---|
| Thought bus (`aureon/core/aureon_thought_bus.py`) | carries what producers publish; no synthesis of its own |
| Mycelium (`aureon/core/aureon_mycelium.py`) | quarantined by the contract scanner, but its outputs derive from real inputs |
| QGITA framework | see §3 — clean |
| `random.shuffle(usdt_pairs)` in the QGITA scanner | shuffles **scan order**, not data. Left as is; the comment already says so |
| `_estimate_timing`, bid/ask spread off a real quote | derived from real inputs, and now labelled `real_derived` rather than `live` |

## 6 · What is broken on `main`

| Finding | Status |
|---|---|
| `python -m compileall aureon scripts tests` | **clean** — nothing is syntactically broken |
| 2 test modules imported `pypdf` at module scope; it is declared only in `Kings_Accounting_Suite/requirements.txt` and the runtime imports it lazily. Pytest aborts the **whole run** on a collection error, so on a root-only install `pytest tests/` executed **zero tests** — `Interrupted: 2 errors during collection`, exit 2. Measured on a pristine `main` worktree with every root-declared dependency installed. | **fixed** — they `importorskip`, so the suite collects and runs |
| 13 test modules need `python-dotenv`, 2 need `psutil` | **environment, not repo** — both are declared in `requirements.txt` and `pyproject.toml`; install them and the modules collect |
| Dead unreachable `return bots` after a `return` in `_estimate_timing` | removed |

---

## Verification run for this audit

```
pytest tests/test_hnc_field_freshness.py tests/test_live_runner_feed_provenance.py \
       tests/test_qgita_decision_provenance.py tests/test_auris_throne_provenance.py   # 46 tests
pytest tests/test_operator_*.py tests/test_saas_*.py tests/test_connectome.py \
       tests/test_capability_demo.py tests/test_dashboard_exposure.py                 # 110 green
python scripts/validation/validate_real_data_contract.py --json                        # error_count 0
python tests/benchmarks/benchmark_aureon_scope.py                                      # Tier A 45/45
python -m compileall -q aureon scripts tests                                           # clean
```

The contract validator reporting `error_count: 0` is worth reading precisely: it means no operational
file trips the scan **and** that 15 files remain exempted by `QUARANTINE_EXACT_PATHS` (down from 16 —
see §2). Those exemptions are the honest remaining work, and the next audit's starting list:

`aureon/core/aureon_lattice.py` · `aureon/core/aureon_mycelium.py` ·
`aureon/harmonic/aureon_harmonic_reality.py` · `aureon/trading/aureon_kraken_ecosystem.py` ·
`aureon/trading/aureon_omega.py` · `aureon/trading/aureon_queen_execute.py` ·
`aureon/trading/aureon_the_play.py` · `aureon/trading/aureon_the_play_old.py` ·
`aureon/trading/aureon_tsx_trader.py` · `aureon/trading/aureon_ultimate.py` ·
`aureon/trading/aureon_unified_ecosystem.py` · `aureon/trading/compound_king.py` ·
`aureon/trading/micro_profit_labyrinth.py` · `aureon/trading/unified_sniper_brain.py` ·
`frontend/public/aureon_organism_runtime_status.json`
