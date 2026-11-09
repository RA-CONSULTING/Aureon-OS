# Stage 6 source-boundary census

Receipt 4 of the go-live list. Decision: `HOLD`. This is not a go-live clear.

Provenance digest: `cea8089cd4be4c39f80123f5f0f9ee806fefb76e528194c42602bbca7ae20289`
Path: `measured/go_live_stage6_provenance.json`

## Lineage

Pin `bb04503119681adcf832f3c3e9b0cbf09fc7a938` aureon tree `a5114a7e5ecb4e9a51df57d58355e72882cf0a3c`.
Tip `b2b0310362597dc520114de86d8700c0c50758d5` aureon tree `a5114a7e5ecb4e9a51df57d58355e72882cf0a3c`.
Those aureon trees match: `true`.
Release-tree content sha256: `19bfb60dc368532b0b2178921a4247f55b2f1be9f8ee52dbcc66196bf6aff3ec`.
Files: 1442. Bytes: 46172063.
Pin-move paths: 31.
Pin-move touches aureon: `false`.
Pin-move touches inventory.json: `false`.

The pin-move commit updates published pin strings and the tests that name them. It does not change the aureon bytes this digest measures.

## Closure

Scan symbols: 20185. Inventory symbols: 20121.
Unlisted in the inventory: 64.
Inventory rows missing from source: 0.
Field drift on shared keys: 0.
Source boundary closed: `false`.
Symbols added since the inventory blob at the pin: 0.
Removed since that blob: 0.

A public entry point is a public function or method. A module or class is listed and is not an entry point. `reachable_count` in the census file is null. This stage does not invent one.

### Public entry points added since the pin inventory

| Module | Symbol | Plan stage | Refusal |
| --- | --- | ---: | --- |

### Other symbols added since the pin inventory

| Module | Symbol | Kind | Server | Full-body stage |
| --- | --- | --- | --- | ---: |

## Open gaps

- `sweep_not_repeated`. The call sweep was not repeated at pin bb04503119681adcf832f3c3e9b0cbf09fc7a938. measured/aureon_public_call_sweep.json still names pin ad9be6c3179bba140fb7e88d5733616046110da9 and aureon tree 2b89d73db122486e2537047baa9b342f3a0249be. Reachable and tested figures in COVERAGE_PLAN.md are that record plus public_entry_refusal. This stage does not publish a new reachable count.
- `brain_proof_blob`. `aureon/evaluation/brain_proof.py` blob at the measured aureon tree is `7c9d20e1e580130e363674894a9c77eef8776e44` and at pin `bb04503119681adcf832f3c3e9b0cbf09fc7a938` is `b24087c3e395a8402fd9a92f03632316ff703525`. Public function source text added: none. Removed: none. Changed: ['evaluate_brain', 'render_brain_markdown']. `render_brain_markdown` is one of those public functions. This stage did not call it and did not call `evaluate_brain`.
- `plan_stages_3_and_4_closed`. OPEN_PLAN_THROUGH stays 2. The read gate opens two entry points: miner MinerAIInsight.to_dict and queen compute_zpe_ground. Exchange body_call stays refused. Full-body ENABLED_THROUGH is 6. That full-body number is not the read gate. 0 public entry points added since the pin inventory are refused. evidence is plan stage 4 because render_results matches the scanner key pattern. Harmonic stays plan stage 4. Exchanges stay plan stage 4. Exchange rows stay operator. The matched token in `render_results` is `dotenv`, from the letters inside `python-dotenv`.
- `changed_blobs_not_recalled`. These existing files differ in git blob between the measured aureon tree and the pin. The census compares symbol names and scanner fields. It does not re-call them: `aureon/core/aureon_env.py`, `aureon/evaluation/auris_node_eval.py`, `aureon/evaluation/brain_proof.py`, `aureon/evaluation/measured_proof.py`, `aureon/evaluation/qgita_snr_benchmark.py`, `aureon/harmonic/aureon_harmonic_reality.py`, `aureon/saas/domains.py`, `aureon/utils/aureon_queen_hive_mind.py`.
- `receipt_5_absent`. Receipt 1 is measured at reports/measured/native_process_containment.json. This stage does not rewrite that record. Receipts 2 and 4 are this remeasurement. Receipt 3 is the DigiCert head anchor in docs/runbooks/GO_LIVE_HARDENING.md. This stage does not append a later head, does not set external_head_anchor_attested, and does not report the system alive. Receipt 5, an authenticated deployment receipt and provider-side read-back, is absent. Decision remains HOLD. go_live_clear is false.
- `pin_inventory_predates_closure`. Inventory sha256 at pin bb04503119681adcf832f3c3e9b0cbf09fc7a938 is be5e14d73ae1130a16d04d355478a1474bf1f1b2c405c9d2196444eca8a391dc. The closure inventory sha256 is 66e9e1ba8da5e11b032c0c27656b7847e88734cf3b030f838af2fd7aa1867bfd. Tip b2b0310362597dc520114de86d8700c0c50758d5 did not change the inventory blob. No inventory rows were added since the pin inventory. The pin aureon tree matches the tip aureon tree.
- `pin_tree_symbols_outside_inventory`. 64 symbols are in the pin aureon tree and are not in docs/mcp/inventory.json. They were not added. The symbol count is a scan of this checkout, which is later than tip b2b0310362597dc520114de86d8700c0c50758d5. The tip field stays that commit and is not a claim that these counts were measured there. `evaluation/market_series.py` `http_get` is a live public fetch. Listing that row would move the evaluation package from plan stage 2 to plan stage 4 and would change the reachable count. Reachable stays the prior sweep's 69. Plan stages 3 and 4 stay closed. The unlisted paths are `aureon/containment/__init__.py`, `aureon/containment/__main__.py`, `aureon/containment/_child_probe.py`, `aureon/containment/_child_wrapper.py`, `aureon/containment/cold_boot.py`, `aureon/containment/native.py`, `aureon/evaluation/market_series.py`, `aureon/evaluation/qgita_series_rates.py`, `aureon/evidence/hnc_anchor.py`.

## Reproduce

```bash
env -u PYTHONPATH PYTHONPATH=mcp python3.12 scripts/validation/go_live_stage6.py --check
```

The check reads git objects for the pin and the tip, scans the checkout files that exist at the pin, and compares these files. Paths added after the pin stay out of the inventory. It does not import a trading package and it does not start a listener.
