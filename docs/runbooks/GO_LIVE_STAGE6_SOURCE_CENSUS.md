# Stage 6 source-boundary census

Receipt 4 of the go-live list. Decision: `HOLD`. This is not a go-live clear.

Provenance digest: `7e3eda4b28d3fbb00e03ea00ad863c625fc68c423a0a01f4218ca0a3179040d9`
Path: `measured/go_live_stage6_provenance.json`

## Lineage

Pin `34864ff0547d2cff03e707414743a3b0cc8770b5` aureon tree `3ba0cab4a5e193b01943e5e6e0be25077ff759f6`.
Tip `c68a89d2a184d99582bb24310b91e024323a212c` aureon tree `3ba0cab4a5e193b01943e5e6e0be25077ff759f6`.
Those aureon trees match: `true`.
Release-tree content sha256: `333999abd82512a1265ab559fec8c05d073d2052a6e0830fcd7e015a603a0d9b`.
Files: 1433. Bytes: 46021601.
Pin-move paths: 32.
Pin-move touches aureon: `false`.
Pin-move touches inventory.json: `false`.

The pin-move commit updates published pin strings and the tests that name them. It does not change the aureon bytes this digest measures.

## Closure

Scan symbols: 20121. Inventory symbols: 20121.
Unlisted in the inventory: 0.
Inventory rows missing from source: 0.
Field drift on shared keys: 0.
Source boundary closed: `true`.
Symbols added since the inventory blob at the pin: 38.
Removed since that blob: 0.

A public entry point is a public function or method. A module or class is listed and is not an entry point. `reachable_count` in the census file is null. This stage does not invent one.

### Public entry points added since the pin inventory

| Module | Symbol | Plan stage | Refusal |
| --- | --- | ---: | --- |
| `evidence/auris.py` | `expects_value` | 4 | plan stage 4 is not open |
| `evidence/hnc.py` | `run_hnc` | 4 | plan stage 4 is not open |
| `evidence/metrics.py` | `auroc` | 4 | plan stage 4 is not open |
| `evidence/metrics.py` | `auroc_interval` | 4 | plan stage 4 is not open |
| `evidence/metrics.py` | `fraction_above` | 4 | plan stage 4 is not open |
| `evidence/metrics.py` | `rates` | 4 | plan stage 4 is not open |
| `evidence/metrics.py` | `upper_threshold` | 4 | plan stage 4 is not open |
| `evidence/metrics.py` | `wilson_interval` | 4 | plan stage 4 is not open |
| `evidence/report.py` | `fmt` | 4 | plan stage 4 is not open |
| `evidence/report.py` | `with_ci` | 4 | plan stage 4 is not open |
| `evidence/runner.py` | `build` | 4 | plan stage 4 is not open |
| `evidence/serialize.py` | `cell` | 4 | plan stage 4 is not open |
| `evidence/serialize.py` | `csv_text` | 4 | plan stage 4 is not open |
| `evidence/serialize.py` | `dump` | 4 | plan stage 4 is not open |
| `evidence/serialize.py` | `plain` | 4 | plan stage 4 is not open |
| `harmonic/aureon_harmonic_reality.py` | `CausalEcho.get_echo_magnitude_ratio` | 4 | plan stage 4 is not open |
| `harmonic/aureon_harmonic_reality.py` | `sample_rate_below_nyquist` | 4 | plan stage 4 is not open |

### Other symbols added since the pin inventory

| Module | Symbol | Kind | Server | Full-body stage |
| --- | --- | --- | --- | ---: |
| `evidence/__init__.py` | `__init__` | module | public | 6 |
| `evidence/__init__.py` | `main` | function | operator | 6 |
| `evidence/__main__.py` | `__main__` | module | public | 6 |
| `evidence/auris.py` | `auris` | module | public | 6 |
| `evidence/auris.py` | `run_auris` | function | operator | 6 |
| `evidence/hnc.py` | `hnc` | module | public | 6 |
| `evidence/metrics.py` | `metrics` | module | public | 6 |
| `evidence/qgita.py` | `qgita` | module | public | 6 |
| `evidence/qgita.py` | `run_qgita` | function | operator | 6 |
| `evidence/report.py` | `build_claims` | function | operator | 6 |
| `evidence/report.py` | `render_results` | function | operator | 6 |
| `evidence/report.py` | `report` | module | public | 6 |
| `evidence/runner.py` | `check` | function | operator | 6 |
| `evidence/runner.py` | `main` | function | operator | 6 |
| `evidence/runner.py` | `runner` | module | public | 6 |
| `evidence/runner.py` | `write` | function | operator | 6 |
| `evidence/serialize.py` | `serialize` | module | public | 6 |
| `exchanges/single_currency_equity.py` | `assemble_sterling_snapshot` | function | operator | 5 |
| `exchanges/single_currency_equity.py` | `currency_amount_map` | function | operator | 5 |
| `exchanges/single_currency_equity.py` | `gbp_field_from_accounts` | function | operator | 5 |
| `exchanges/single_currency_equity.py` | `nonnegative_amount` | function | operator | 5 |

## Open gaps

- `sweep_not_repeated`. The call sweep was not repeated at pin 34864ff0547d2cff03e707414743a3b0cc8770b5. measured/aureon_public_call_sweep.json still names pin ad9be6c3179bba140fb7e88d5733616046110da9 and aureon tree 2b89d73db122486e2537047baa9b342f3a0249be. Reachable and tested figures in COVERAGE_PLAN.md are that record plus public_entry_refusal. This stage does not publish a new reachable count.
- `brain_proof_blob`. `aureon/evaluation/brain_proof.py` blob at the measured aureon tree is `7c9d20e1e580130e363674894a9c77eef8776e44` and at pin `34864ff0547d2cff03e707414743a3b0cc8770b5` is `89d874ebfe2fc8b8e73113b86fe6524b3ee71322`. Public function source text added: none. Removed: none. Changed: none. `render_brain_markdown` is one of those public functions. This stage did not call it and did not call `evaluate_brain`.
- `plan_stages_3_and_4_closed`. Coverage-plan stages above 2 stay closed. Full-body ENABLED_THROUGH is 6. That full-body number is not an opening of coverage-plan stages 3 and 4. 17 public entry points added since the pin inventory are refused. evidence is plan stage 4 because render_results matches the scanner key pattern. Harmonic stays plan stage 4. Exchanges stay plan stage 4. The matched token in `render_results` is `dotenv`, from the letters inside `python-dotenv`.
- `changed_blobs_not_recalled`. These existing files differ in git blob between the measured aureon tree and the pin. The census compares symbol names and scanner fields. It does not re-call them: `aureon/core/aureon_env.py`, `aureon/evaluation/brain_proof.py`, `aureon/harmonic/aureon_harmonic_reality.py`, `aureon/utils/aureon_queen_hive_mind.py`.
- `receipts_1_and_5_absent`. Receipts 1, 3, and 5 are not produced by this stage. Native zero-network containment and an authenticated deployment receipt are absent. Receipt 3 is the DigiCert head anchor in docs/runbooks/GO_LIVE_HARDENING.md. This stage does not append a later head, does not set external_head_anchor_attested, and does not report the system alive. Decision remains HOLD. go_live_clear is false.
- `pin_inventory_predates_closure`. Inventory sha256 at pin 34864ff0547d2cff03e707414743a3b0cc8770b5 is 4bc19ea9b5444a7b8a9abbd3fabf635d083bd25bea6c1b2d6eab2605b4f5716b. The closure inventory sha256 is be5e14d73ae1130a16d04d355478a1474bf1f1b2c405c9d2196444eca8a391dc. Tip c68a89d2 did not change the inventory blob. The symbols added here were already in the pin aureon tree, which matches the tip aureon tree.
- `post_pin_checkout_not_in_closure`. These checkout paths are not in the pin tree this closure measures: `aureon/evaluation/market_series.py`, `aureon/evidence/hnc_anchor.py`. They are not added to the inventory. `evaluation/market_series.py` `http_get` is a live public fetch. Listing that row would move the evaluation package from plan stage 2 to plan stage 4 and would change the reachable count. Reachable stays the prior sweep's 69. Plan stages 3 and 4 stay closed. The pin is not moved.

## Reproduce

```bash
env -u PYTHONPATH PYTHONPATH=mcp python3.12 scripts/validation/go_live_stage6.py --check
```

The check reads git objects for the pin and the tip, scans the checkout files that exist at the pin, and compares these files. Paths added after the pin stay out of the inventory. It does not import a trading package and it does not start a listener.
