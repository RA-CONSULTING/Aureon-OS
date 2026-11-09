# Public environment postures

This page names the variables for three public postures. The committable template is [`.env.example`](../.env.example). The release boundary stays **HOLD**.

## Charlie rule

`.env.example` uses placeholder names only. A secret line is blank, or it is an obvious placeholder name such as `your_binance_api_key_here` or `REDACTED_USE_CLOUD_SECRET` in a vendored template. A real key value never goes in that file.

The root template keeps exchange, broker, model, and ingest secrets blank. The variable name is the placeholder. A real value belongs in the gitignored `.env` on the operator's machine, or in the operator's secret store.

A non-blank Kraken, Binance, Alpaca, or Capital.com key group is what [`scripts/launch/aureon-master.sh`](../scripts/launch/aureon-master.sh) treats as live when autonomy is full. Exchange keys in `.env` make that boot live. That launcher, `scripts/linux/aureon-up.sh`, and `production/Install-AUREON.ps1` set guarded mode unless the stage 11 go-live gate reports clear and `AUREON_OPERATOR_ALLOW_LIVE` is set for the run. Setting the flag does not override the gate. On this checkout `go_live_clear` is false, so those launchers do not start live mode.

A blank root `.env` is not enough to stay on paper. The master launcher also reads a complete key group from the inherited shell and from `aureon_radar/.env`. Either source arms that same full-autonomy boot even when every secret line in the root `.env` is blank. `./install.sh` is a different entry: it skips `.env` and sets guarded autonomy in its own process.

## 1. Guarded offline

No `.env` is required. [`./install.sh`](../install.sh) does not read `.env`, leaves exchange keys unset, and does not place an order.

The plug supervisor sets these in the process:

| Variable | Process value | Role |
|---|---|---|
| `AUREON_AUTONOMY_MODE` | `guarded` | Opt-in denylist. Live trading stays off. |
| `AUREON_LLM_OFFLINE` | `1` | Operator stays off external model HTTP. The provider line is the offline adapter. |
| `AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS` | `1` | Import stays quiet for the local stack and the offline pytest path. |
| `AUREON_PLUG_AND_PLAY` | `1` | Skips `.env`, the keystore, and the feature switchboard. |
| `AUREON_DISABLE_REAL_ORDERS` | `1` | Real orders stay disabled. |
| `AUREON_DISABLE_EXCHANGE_MUTATIONS` | `1` | Exchange mutations stay disabled. |
| `AUREON_ORDER_INTENT_PUBLISH` | `0` | Order-intent publish stays off. |
| `AUREON_FUSION_ARM_LIVE` | empty | Fusion live arm stays empty. |
| `AUREON_LIVE_TRADING` | `0` | Live trading stays off. The template leaves this name unassigned so a copied `.env` has no live-trading line. |

No exchange key and no model key are required. HNC, Auris, and QGITA run from this repository.

The five-minute offline pytest path in the root README uses `AUREON_LLM_OFFLINE=1` and `AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS=1` in the shell. The copied template also sets `AUREON_LLM_OFFLINE=1` so a fresh `.env` keeps external model HTTP off until the operator changes that line in `.env`.

## 2. Read-only market fetch

Public Binance klines and Kraken OHLC/Spread. The fetcher adds no API key and sends no order. Optional data-provider names in `.env.example` are unused by this command. Leave them blank.

Live fetch, when this machine can reach the public endpoints:

```bash
AUREON_DISABLE_REAL_ORDERS=1 PYTHONPATH=. python3 -m aureon.evaluation.market_series --out reports/measured
```

Check the pack already on disk, with no network:

```bash
PYTHONPATH=. python3 -m aureon.evaluation.market_series --check --out reports/measured
```

The committed pack is `reports/measured/market_series.json`. Key material on that pack is `none`. Key group is a public venue label (`public:binance` or `public:kraken`).

## 3. Live orders — template values, not a master lock

A fresh blank-key copy ships the flags below. `AUREON_LIVE_TRADING` stays unassigned in `.env.example`, so the copy has no live-trading line. Those lines are the file. They are not a lock.

| Variable | Template value | What a full+keyed master boot does |
|---|---|---|
| `AUREON_DISABLE_REAL_ORDERS` | `1` | Overridden to `0`. |
| `AUREON_DISABLE_EXCHANGE_MUTATIONS` | `1` | Overridden to `0`. |
| `AUREON_ORDER_INTENT_PUBLISH` | `0` | Overridden to `1`. |
| `AUREON_UNIFIED_ORDER_EXECUTOR` | `0` | Overridden to `1`. |
| `AUREON_DRY_RUN` | `1` | Overridden to `0`. |
| `DRY_RUN` | `1` | Overridden to `0`. |
| `ALPACA_PAPER` | `true` | Left as written. The live profile does not rewrite this venue line. |
| `CAPITAL_DEMO` | `1` | Left as written. The live profile does not rewrite this venue line. |
| `CAPITAL_DEMO_MODE` | `true` | Left as written. The client reads `CAPITAL_DEMO`. |

The override is the last write in `stamp_boot` (`aureon/launch/master.py`). It runs when autonomy is full and a complete exchange key group is present. That is a full+keyed master boot. The child then has disable flags `0`, dry-run flags `0`, and the live-trading switch `1`. Explicit `AUREON_AUTONOMY_MODE=guarded` keeps the paper profile, including these disable and dry-run flags. With no complete key group the report says `trading_mode=paper/public-data (no exchange keys)`. With a complete group it says `trading_mode=live (exchange keys present)`.

Exchange keys in `.env` make that boot live. A complete group in the inherited shell, or in `aureon_radar/.env`, makes that boot live too, even when the root `.env` secret lines are blank. A blank root file does not clear a key the shell already exported, and it does not hide a key in `aureon_radar/.env`.

Exchange key names stay blank in this template: `KRAKEN_API_KEY`, `KRAKEN_API_SECRET`, `BINANCE_API_KEY`, `BINANCE_API_SECRET`, `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`, `CAPITAL_API_KEY`, `CAPITAL_IDENTIFIER`, `CAPITAL_PASSWORD`. Order-size and Kelly lines stay blank too.

`./install.sh` is the public first command. The master launcher is a separate entry. Its code default for autonomy is full when the shell and `state/autonomy_mode.json` leave the mode unset. A first look stays on the five-minute quickstart in the root README. See [`AUTONOMY.md`](../AUTONOMY.md) and [`PORTABILITY.md`](../PORTABILITY.md).

## What a fresh `.env` contains

When `.env` is absent, the master launcher copies `.env.example` once. The copy keeps blank secrets, paper and demo venue lines, the disable and dry-run values above, and QuickBooks mutation `false` in the sandbox environment. The launcher forces those two QuickBooks lines if the template ever drifts. It leaves an existing `.env` untouched. It does not write `SERO_WORKSPACE`. It does not write a live-trading assignment into the file.

That copy is the blank-key template. It does not by itself keep the next master boot on paper if a complete key group is already in the inherited shell or in `aureon_radar/.env`. Exchange keys in `.env` make that boot live.

Do not commit `.env`.
