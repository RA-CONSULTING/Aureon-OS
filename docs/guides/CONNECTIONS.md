# 🔌 Connections — every external source, from trading to NASA

Aureon reaches a lot of the outside world: trading exchanges, market data, NASA /
space-weather feeds, on-chain & whale-flow "surveillance", news, and
notifications — on top of the AI/LLM models. The **Connections** page
(*Operations → Connections*) is the single place to see them all, enter keys,
test connectivity, and answer the big question: **what do we need to run the
whole system at full operational capacity?**

## The dashboard

- **Readiness banner** — "Full operational capacity: N %", how many keyed
  sources are connected, and a one-click list of what's still missing (each links
  to where you get the key).
- **Category sections** — AI/LLM · Trading exchanges · Market data & macro ·
  Space & science · Ephemeris · On-chain & whale · News & social · Notifications.
  Every source shows a **status dot** (green = connected, sky = keyless/public,
  amber = key set, grey = needs key), a **Test** button, and inline **key entry**
  where a key applies.

## What needs a key vs. what's free

**Keyless / public (no key — just a reachability test):** NOAA SWPC (space
weather — the Λ(t) driver), USGS earthquakes, NASA EONET, JPL Horizons / Skyfield
ephemeris, Binance public klines, Reddit, CoinGecko (works keyless).

**Key-optional (a key raises limits / unlocks enrichment):**

| Source | Env var | Unlocks |
|---|---|---|
| NASA (DONKI/NEO) | `NASA_API_KEY` | Solar flares, storms, CMEs, near-Earth objects (falls back to rate-limited `DEMO_KEY`) |
| NASA FIRMS | `FIRMS_MAP_KEY` | Global active-wildfire detections |
| CoinAPI | `COINAPI_KEY` | Cross-exchange market history + anomaly detection |
| FRED | `FRED_API_KEY` | Macro series (rates, CPI, GDP) |
| FMP | `FMP_API_KEY` | Economic / earnings / IPO calendar |
| Etherscan / Alchemy / Covalent | `ETHERSCAN_API_KEY` / `ALCHEMY_API_KEY` (+`ALCHEMY_NETWORK`) / `COVALENT_API_KEY` | On-chain + whale transfer tracking |
| Glassnode / Unusual Whales | `GLASSNODE_API_KEY` / `UNUSUAL_WHALES_API_KEY` | On-chain metrics / options-whale flow (paid) |
| World News | `WORLD_NEWS_API_KEY` | News + geopolitical sentiment |
| Telegram | `TELEGRAM_BOT_TOKEN` (+`TELEGRAM_CHAT_ID`) | Outbound trade/alert messages |

**Trading exchanges** (`BINANCE_*`, `KRAKEN_*`, `ALPACA_*`, `CAPITAL_*`) unlock
live execution + balances.

## How keys flow

```
Connections UI  →  POST /api/connections/<id>
   • data source  → encrypted operator keystore + os.environ (the operator uses it immediately)
   • exchange     → delegated to the existing .env writer + restart-intent (the SEPARATE trading
                    process reads .env at boot, so exchange keys land there, not the operator store)
```

- **Data-source keys** are stored in the same encrypted keystore as the LLM keys
  (`~/.aureon/provider_keys.json.enc`, Fernet, git-ignored), masked on read (last
  4), never logged.
- **Exchange keys** are **not** put in the operator keystore — the trader is a
  separate process that reads `.env`, so exchange edits go through your existing
  `/api/env-credentials` writer (which backs up `.env`, encrypts values as HNC
  packets when a master key is set, and records a restart intent). The dashboard
  shows their live `*_ready` status.
- **Connectivity Test** does a real, short outbound probe (keyless → a public
  endpoint; keyed → an authenticated call) and reports latency or the exact error.
  It never persists.

## How keys reach the daemons

Storing a key in the UI (or `.env`) is only half the job — the long-running HNC
processes have to *receive* it. They all call one shared bootstrap at start-up,
`bootstrap_credentials()` in `aureon/core/aureon_env.py`, which:

1. loads `.env` across every candidate path, **decodes HNC env-packets**, and
   applies the credential aliases (`load_aureon_environment`), then
2. layers the encrypted keystore on top (`keystore.apply_to_env()`) — so a key
   set in the Providers/Connections UI reaches the engine exactly like a `.env` one.

It returns a **presence-only** self-check (booleans, never values) that each
daemon logs at boot, e.g. `credentials: NASA=on NOAA=on USGS=on … AUREON=on`.
The entrypoints that call it: the operator server (`operator_server`), the HNC
live daemon (`hnc-live-daemon`), and the organism daemon (`aureon-organism`).
Before this, only the operator loaded keys — the HNC daemons ran without them, so
`NASA_API_KEY` (DONKI enrichment) and the NOAA/USGS keys were invisible to their
fetchers. Now every process sees every key.

### Live science sources that consume the keys

Two keyed feeds flow straight into the HNC Λ(t) pipeline as live sources
(registered in `hnc_live_daemon._wire_default_sources`; both **degrade to a
neutral, zero-confidence reading when unkeyed**, so a keyless deploy still boots):

| Source | Env var | Endpoint (auth header) | Cadence |
|---|---|---|---|
| NOAA NCEI Climate Data Online | `NOAA_API_KEY` | `ncei.noaa.gov/cdo-web/api/v2/datasets` (`token`) | 60 min |
| USGS Water Data | `USGS_API_KEY` | `api.waterdata.usgs.gov/ogcapi/v0/collections` (`X-Api-Key`) | 30 min |

(The keyless NOAA SWPC space-weather feed and the keyless USGS earthquake feed are
unchanged — these are the *keyed* NCEI/Water-Data services, distinct endpoints.)

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/connections` | categorized sources + masked key status |
| GET | `/api/connections/readiness` | full-capacity report (present/missing, counts, what each unlocks) |
| POST | `/api/connections/<id>` | set a key (data source → keystore; exchange → delegated) |
| POST | `/api/connections/<id>/test` | connectivity probe (never persists) |

## Security

- Keys encrypted at rest, masked on every read, never logged; keystore
  git-ignored. Write/test endpoints are under `/api/*` — set
  `AUREON_OPERATOR_API_KEY` to require a bearer on a shared/public deployment.
- A previously **leaked hardcoded World News API key** was removed from the code
  (env-only now).

## To run at full capacity

1. Open *Operations → Connections*.
2. Fill the keyed sources you want (the readiness banner lists what's missing).
3. **Test** each — green means Aureon is talking to it.
4. Keyless feeds (NOAA/USGS/NASA-EONET/ephemeris) need nothing but network — Test
   confirms reachability.

Everything here also works as plain environment variables — see `.env.example`.
The dashboard just makes it encrypted, testable, and visible in one place.
