# Public environment postures

This page names the variables for three public postures. The committable template is [`.env.example`](../.env.example). The release boundary stays **HOLD**.

## Charlie rule

`.env.example` uses placeholder names only. A secret line is blank, or it is an obvious placeholder name such as `your_binance_api_key_here` or `REDACTED_USE_CLOUD_SECRET` in a vendored template. A real key value never goes in that file.

The root template keeps exchange, broker, model, and ingest secrets blank. The variable name is the placeholder. A real value belongs in the gitignored `.env` on the operator's machine, or in the operator's secret store.

A non-blank Kraken, Binance, Alpaca, or Capital.com key group is what [`scripts/launch/aureon-master.sh`](../scripts/launch/aureon-master.sh) treats as live when autonomy is full. Blank is what keeps a fresh copy of the template on paper/public-data.

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

## 3. Live orders — explicitly disabled

This template ships live orders off. `AUREON_LIVE_TRADING` stays unassigned in `.env.example`. Copying `.env.example` to `.env` leaves these locks in place:

| Variable | Template value | Role |
|---|---|---|
| `AUREON_DISABLE_REAL_ORDERS` | `1` | Blocks live exchange mutations for readers of the file. |
| `AUREON_DISABLE_EXCHANGE_MUTATIONS` | `1` | Same block, second name. |
| `AUREON_ORDER_INTENT_PUBLISH` | `0` | Order-intent publish stays off. |
| `AUREON_UNIFIED_ORDER_EXECUTOR` | `0` | Unified order executor stays off. |
| `AUREON_DRY_RUN` | `1` | Dry run stays on. |
| `DRY_RUN` | `1` | Dry run stays on. |
| `ALPACA_PAPER` | `true` | Alpaca stays on the paper venue URL. |
| `CAPITAL_DEMO` | `1` | Capital.com stays on the demo venue URL. |
| `CAPITAL_DEMO_MODE` | `true` | Demo alias stays on. The client reads `CAPITAL_DEMO`. |

Exchange key names stay blank: `KRAKEN_API_KEY`, `KRAKEN_API_SECRET`, `BINANCE_API_KEY`, `BINANCE_API_SECRET`, `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`, `CAPITAL_API_KEY`, `CAPITAL_IDENTIFIER`, `CAPITAL_PASSWORD`. Order-size and Kelly lines stay blank too.

`./install.sh` is the public first command. The master launcher is a separate entry. Its code default for autonomy is full when the shell and `state/autonomy_mode.json` leave the mode unset. With no complete key group it reports `trading_mode=paper/public-data (no exchange keys)`. With a complete key group it reports `trading_mode=live (exchange keys present)`. A first look stays on the five-minute quickstart in the root README. Explicit `AUREON_AUTONOMY_MODE=guarded` in the shell keeps that launcher on the paper profile. See [`AUTONOMY.md`](../AUTONOMY.md) and [`PORTABILITY.md`](../PORTABILITY.md).

## What a fresh `.env` contains

When `.env` is absent, the master launcher copies `.env.example` once. The copy keeps blank secrets, paper and demo on, and QuickBooks mutation `false` in the sandbox environment. The launcher forces those two QuickBooks lines if the template ever drifts. It leaves an existing `.env` untouched. It does not write `SERO_WORKSPACE`. It does not write a live-trading assignment into the file.

Do not commit `.env`.
