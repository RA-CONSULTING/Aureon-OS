# Offline gallery

Three checkout commands, run from committed fixtures. No live market fetch, no order, and no write to `reports/measured`.

Release boundary: **HOLD**. This gallery is not a production-ready release. The public require-pin stays `bb04503119681adcf832f3c3e9b0cbf09fc7a938`. The containment pin stays `34864ff0547d2cff03e707414743a3b0cc8770b5`. The orange release-boundary badge in `README.md` stays. `go_live_clear` stays false. Receipts 2, 3, 4, and 5 stay HOLD.

Python 3.11 or newer, from the repository root. The commands set `AUREON_LLM_OFFLINE=1`, `AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS=1`, `AUREON_DISABLE_REAL_ORDERS=1`, and `AUREON_LIVE_TRADING=0` inside the process. `aureon.evaluation.market_series.http_get` is replaced with a function that raises, so a live GET fails closed.

```bash
PYTHONPATH=. python3 examples/offline/load_market_series.py
PYTHONPATH=. python3 examples/offline/run_brain_proof.py
PYTHONPATH=. python3 examples/offline/cold_boot.py
```

## What each command does

| Command | What it calls | Fixture |
| --- | --- | --- |
| `load_market_series.py` | `fetch_public_pack` with a fixture transport, then `load_market_series`, then `python -m aureon.evaluation.market_series --check` on that sandbox | `fixtures/kraken_ohlc.json`, `fixtures/kraken_spread.json` |
| `run_brain_proof.py` | `evaluate_brain` on the same sandbox, then `render_brain_markdown` | the pack above, plus cited copies of `aureon/trading/aureon_auris_trader.py`, `aureon/core/hnc_field.py`, and `frontend/src/core/aurisNodes.ts`. Those copies are read as source text and are not executed. `data/de440_timeseries.csv` is not copied in, so the derived column stays HOLD |
| `cold_boot.py` | `judge_default` on `fixtures/cold_boot_child.json` | child probe labelled `evidence_tag: fixture` |

The Kraken bodies are synthetic public-shaped responses (closes 100 through 112, plus one open bar the loader drops). Brain proof may tag that pack `measured` because the bars verified. That tag is not a live Kraken fetch. A pass or fail on paper next-bar labels is a brain-proof figure. It does not clear the release boundary.

The cold-boot fixture judge can print `pass` with `allowed at default: none`. That means the fixture shape has no route. It is not a measurement of this machine, and it is not the stage-7 receipt.

## Commands this gallery does not run

These stay available in the checkout. This gallery does not invoke them.

Market series fetch (public HTTP, still no order):

```bash
AUREON_DISABLE_REAL_ORDERS=1 PYTHONPATH=. python3 -m aureon.evaluation.market_series --out reports/measured
```

Check the pack already committed under `reports/measured` (no fetch, but that pack is a recorded public series, not this fixture):

```bash
PYTHONPATH=. python3 -m aureon.evaluation.market_series --check --out reports/measured
```

Brain proof on the checkout root (reads `reports/measured/market_series.json` and `data/de440_timeseries.csv` when they are present):

```bash
AUREON_LLM_OFFLINE=1 AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS=1 AUREON_DISABLE_REAL_ORDERS=1 PYTHONPATH=. python3 -c "from aureon.evaluation.brain_proof import evaluate_brain, render_brain_markdown; print(render_brain_markdown(evaluate_brain()))"
```

Containment cold boot. The measurer opens one control TCP handshake to `1.1.1.1:443` outside the contained namespace, reads zero bytes, and does not place an order. `--no-write` skips the receipt files. This gallery does not start that process.

```bash
python3 -m aureon.containment.cold_boot --no-write
```
