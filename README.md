<div align="center">

<img src="docs/images/aureon_zorza_logo.jpg" alt="Aureon Zorza Technologies" width="720" />

# Aureon OS

### — Harmonic Nexus Core —

**The operating system for evidence-heavy, high-control work: a grounded AI operating layer.**
Trading research · autonomous operator · planetary/HNC research · a coding organism — one auditable system.

![Release boundary: HOLD](https://img.shields.io/badge/release%20boundary-HOLD-orange.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)

*A product of [R&A Consulting and Brokerage Services Ltd](COMPANY.md) — trading as **Aureon Zorza Technologies** · Belfast, Northern Ireland · Silver-level Innovate NI innovator.*

</div>

## Quick start in five minutes

Python 3.11 or newer, Node.js 20 or newer, and a blank key file. On Debian or Ubuntu, install `python3-venv` first. `./install.sh` creates `.venv`, installs the pinned `requirements-plug.lock`, installs the dashboard with `npm ci` when `frontend/node_modules` is absent, and starts the local stack:

- operator API on `http://127.0.0.1:8790/`
- public MCP server on `http://127.0.0.1:8077/mcp`
- dashboard on `http://127.0.0.1:5173/`
- stack health and the in-process HNC / Auris / QGITA report on `http://127.0.0.1:8787/`

The command leaves exchange keys unset and does not read `.env`. `AUREON_AUTONOMY_MODE=guarded` keeps live trading off. `AUREON_LLM_OFFLINE=1` keeps the operator off external model HTTP, so the provider line is the offline adapter. HNC, Auris, and QGITA run from this repository. The release boundary stays **HOLD**. Trade readiness on the committed public series is the measured brain-proof verdict.

```bash
git clone https://github.com/RA-CONSULTING/Aureon-OS.git
cd Aureon-OS
./install.sh
```

Stop it with `./install.sh --stop`.

`./install.sh --smoke` boots that same stack, requests the endpoints, and stops. Installer logs from pip, and from `npm ci` on a fresh tree, scroll first. The stack then prints:

```text
{"autonomy_mode": "guarded", "banner": "aureon-plug", "exchange_keys": "unset", "external_llm": false, "live_trading": false, "ok": true, "pids": {"frontend": 3356, "mcp": 3355, "operator": 3354}, "service": "aureon-plug", "services": {"cognition": {"ok": true, "runner": "aureon.evaluation.brain_proof.evaluate_brain", "url": "http://127.0.0.1:8787/api/cognition"}, "frontend": {"ok": true, "status": 200, "url": "http://127.0.0.1:5173/"}, "mcp": {"ok": true, "status": 405, "url": "http://127.0.0.1:8077/mcp"}, "operator": {"ok": true, "providers": ["offline"], "ready": true, "status": 200, "url": "http://127.0.0.1:8790/healthz"}}}
operator   http://127.0.0.1:8790/healthz
ready      http://127.0.0.1:8790/readyz
mcp        http://127.0.0.1:8077/mcp
frontend   http://127.0.0.1:5173/
cognition  http://127.0.0.1:8787/api/cognition
health     http://127.0.0.1:8787/healthz
SMOKE healthz 200 {"autonomy_mode": "guarded", "exchange_keys": "unset", "external_llm": false, "live_trading": false, "ok": true, "service": "aureon-plug", "services": {"cognition": {"ok": true, "runner": "aureon.evaluation.brain_proof.evaluate_brain", "url": "http://127.0.0.1:8787/api/cognition"}, "frontend": {"ok": true, "status": 200, "url": "http://127.0.0.1:5173/"}, "mcp": {"ok": true, "status": 405, "url": "http://127.0.0.1:8077/mcp"}, "operator": {"ok": true, "providers": ["offline"], "ready": true, "status": 200, "url": "http://127.0.0.1:8790/healthz"}}}
SMOKE operator 200 {"ok":true,"providers":[{"adapter":"AureonStubAdapter","model":"","name":"offline"}],"service":"aureon-operator"}
SMOKE readyz 200 {"checks":{"cognition":true,"providers":true,"real_data_policy":{"probe_report_path":"","probe_report_status":"missing","probe_summary":{"blocked":0,"cached_real":0,"live":0,"no_data":0,"operational_ready":0,"real_derived":0,"test_fixture":0},"simulation_fallback_allowed":false,"source_registry_count":19,"truth_statuses":["cached_real","live","no_data","real_derived","test_fixture"]},"repo_index":true},"ready":true}
SMOKE frontend 200 aureon_os=True
SMOKE mcp_initialize {"name": "aureon-public", "version": "1.30.0"}
SMOKE mcp_tools auris_coherence hnc_reality_step qgita_analyze
SMOKE hnc {"coherence": 0.9331334813083556, "enable_multiverse": false, "status": "inferred"}
SMOKE qgita {"detection_rate": "HOLD", "false_alarm_rate": "HOLD", "ftcp_count": 0, "status": "complete"}
SMOKE auris_mcp Error executing tool auris_coherence: checkout aureon/utils/aureon_queen_hive_mind.py differs from pin 8aa6a2d971cc
SMOKE cognition {"auris": {"coherence": null, "hold_nodes": ["Clownfish", "Owl"], "status": "no_data", "trade_readiness": {"reason": "no market series and no trade-outcome labels", "verdict": "HOLD"}}, "cognition": "internal", "external_llm": false, "hnc": {"coherence": 0.9331334813083556, "enable_multiverse": false, "lambda_last": 1.409626852655939, "multiverse_extension_verdict": "measured", "state": "unified", "steps": 100}, "live_trading": false, "orders_placed": false, "qgita": {"derived_ftcp_count": 0, "derived_rates_verdict": "HOLD", "derived_status": "complete", "derived_verdict": "measured_counts_rates_hold", "on_hnc_ftcp_count": 0, "on_hnc_rates_verdict": "HOLD", "on_hnc_status": "complete"}, "schema": "aureon.brain-proof.v1", "together": {"auris_joined_to_lambda": {"reason": "no function in the repo passes \u039b(t) into get_auris_coherence", "verdict": "HOLD"}, "qgita_on_the_formula_series": "measured_counts_rates_hold"}}
SMOKE PASSED
```

Process ids in that banner are from the run that produced it. A later run prints its own pids. The public MCP `auris_coherence` tool returns the pin refusal above when `aureon/utils/aureon_queen_hive_mind.py` differs from the published pin. The in-process report on `/api/cognition` runs `evaluate_brain`. With `reports/measured/market_series.json` loaded, that report's Auris coherence is the pack reading and trade readiness is the measured paper-label verdict. QGITA detection rate stays **HOLD**. Auris joined to Λ(t) stays **HOLD**: the formula-path Λ(t) is passed into `get_auris_coherence`, and that call does not change the coherence figure. The release boundary stays **HOLD**. The smoke banner above is an earlier run, from before that pack.

`python3 scripts/stage_plug_image.py` then `docker compose -f deploy/plug/docker-compose.yml up --build` is the container form of the same command. It uses host networking so the processes can bind `127.0.0.1`.

The offline pytest commands are in the Five-minute quickstart section below.

Older notes in `docs/` (for example `docs/AUREON_MIND_STATUS.md`), `aureon-trading/docs/`, and `imports/` (including the `imports/Kimi_Agent_Aureon_20260408` snapshot) are earlier research writing and may repeat figures that have since been withdrawn. This README and `mcp/aureon_public` are the current, checked parts.

> **Leave exchange keys unset.** `./install.sh` sets `AUREON_AUTONOMY_MODE=guarded` and skips `.env`. `scripts/launch/aureon-master.sh` and `production/install.sh` use the public autonomy default: a complete exchange key group in `.env` makes that boot live.

---

## Five-minute quickstart

A fresh clone, Python 3.11 or newer, and no API keys. This path does not start Docker, does not read exchange keys, and does not place an order. It installs the operator extra, runs the offline operator server tests, the connectome test, and the quickstart banner test, then prints the HNC measurement from `aureon.evaluation.brain_proof.evaluate_brain`. That function runs `HarmonicRealityField.step` for 100 steps with the multiverse extension off. The class default HarmonicRealityField() has the multiverse on, which gives coherence 0.857719 and LOCKED. It is deterministic: it takes no seed, so the same figures come back on every run.

Linux and macOS:

```bash
git clone https://github.com/RA-CONSULTING/Aureon-OS.git && cd Aureon-OS
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
python -m pip install -e '.[operator]' 'pytest>=8' 'pytest-timeout>=2.3' 'numpy>=1.26' 'cryptography>=46'
AUREON_LLM_OFFLINE=1 AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS=1 pytest tests/test_operator_server.py tests/test_connectome.py tests/test_quickstart_brain_proof.py --timeout=60
AUREON_LLM_OFFLINE=1 AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS=1 python -c "from aureon.evaluation.brain_proof import evaluate_brain, render_brain_markdown; print(render_brain_markdown(evaluate_brain()))"
```

Windows:

```bat
git clone https://github.com/RA-CONSULTING/Aureon-OS.git && cd Aureon-OS
py -3 -m venv .venv
.venv\Scripts\activate
python -m pip install -U pip
python -m pip install -e ".[operator]" "pytest>=8" "pytest-timeout>=2.3" "numpy>=1.26" "cryptography>=46"
set AUREON_LLM_OFFLINE=1
set AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS=1
pytest tests/test_operator_server.py tests/test_connectome.py tests/test_quickstart_brain_proof.py --timeout=60
python -c "from aureon.evaluation.brain_proof import evaluate_brain, render_brain_markdown; print(render_brain_markdown(evaluate_brain()))"
```

The measurement below is from a run of that command with no keys. The HNC figures are the committed formula path (`reports/measured/brain.json`). Auris uses the public series in `reports/measured/market_series.json` when that pack is loaded. Trade readiness is a measured **fail** on 166 paper next-bar labels: `get_auris_coherence` did not mark any labelled bar ready to trade, and this checkout has no filled order outcome. Clownfish and Owl have a reading on every labelled bar. The release boundary stays **HOLD**.

```text
# HNC, Auris coherence, and QGITA

These figures are the HNC master-formula path, Auris coherence, and the QGITA analyzer. They are not a claim that the system is conscious or alive.

No outside model was called. Live trading stayed off. No order was placed.
HNC formula path, multiverse off: state `coherent`, coherence `0.7739191103121901`, last Λ(t) `1.1030284973375342`, steps `100`.
Multiverse extension: **measured**. project_to_3d sets noise to 0 when no observed residual is supplied. TranslationMap.noise_level is stored and is not read by that method. Three constructions of the default HarmonicRealityField returned the same series.
Auris coherence `0.5023340603593964` with status `⛔ COHERENCE BREAK - Do not trade`. Zero-input nodes without a reading: none. Window nodes without a reading: none. The window is one call on the whole pack and includes the latest spread print, even when that print is after the OHLC bars. Labelled bars are a separate clock: a spread print counts only at or before the decision close.
Trade readiness: **fail**. paper trade-outcome labels: 166 next-bar close-to-close returns from public:kraken XBTUSD; the prices are measured and the outcomes are paper; filled outcomes: 0; Clownfish readings 166 of 166; Owl readings 166 of 166; nodes without a reading on a labelled bar: Deer; ready-to-trade paper entries: 0; entries with a higher next close: 0; entries without a higher next close: 0; a spread print is used only when its time is at or before the decision close; window call status: ⛔ COHERENCE BREAK - Do not trade; measured fail: get_auris_coherence did not mark any labelled bar ready to trade; release boundary stays HOLD
QGITA on the derived series `data/de440_timeseries.csv` (cited-unverified): status `complete`, FTCP count `0`, lighthouse events `0`. Detection rate **HOLD**. Clock: sample index. analyze_price_stream uses range(len(prices)) when no timestamps are passed
QGITA on the formula series: FTCP count `0`, lighthouse events `0`. Detection rate **HOLD**. Clock: step index times HarmonicRealityField.dt
QGITA on the public series `XBTUSD` (measured, key group `public:kraken`): status `complete`, FTCP count `0`, lighthouse events `0`. Detection rate **HOLD**. Clock: venue bar open time in unix seconds; price is the bar close
Auris joined to Λ(t): **HOLD**. HarmonicRealityField.step Λ(t) was passed into get_auris_coherence under the keys lambda, lambda_t, lambda_current. Each only-lambda call returned coherence null and status 'no_data', the same as get_auris_coherence(None). Beside the loaded market texture, coherence stayed 0.5023340603593964 with status '⛔ COHERENCE BREAK - Do not trade' for all 100 formula-series samples under those keys (300 calls). Cited from _auris_role_value, the keys read are momentum, spread, volatility, volume. Neither _auris_role_value nor get_auris_coherence names lambda. On this formula series the coherence figure was unchanged by those keys. No join contract was found. reconcile_gamma does not name lambda and its docstring returns the caller figure. AurisEngine.calculate_coherence does not name lambda. Its source comment claims a Master Equation Λ(t) bias, and the executed branch multiplies coherence by 1.1 when snapshot.momentum > 0.0 and snapshot.volume > 0.5. MarketSnapshot fields are symbol, price, volume, volatility, momentum, spread, timestamp. That comment was not copied into get_auris_coherence. The TypeScript MarketSnapshot fields are price, volume, volatility, momentum, spread, timestamp. That snapshot does not name lambda. HOLD remains because the coherence formula does not consume lambda. This item does not clear the release boundary. No formula was added. No order was placed. Go-live stays HOLD.
```

The longer operator preflight, containers, and the full offline suite are further down.

## Public MCP (stages 1 and 2 of 4)

[`mcp/aureon_public/README.md`](mcp/aureon_public/README.md) is the public MCP surface. It is read-only. Stages 1 and 2 of 4 are open. Stages 3 and 4 stay closed.

---

## What Aureon OS is

Aureon OS is a **local-first operating layer** — powered by the Harmonic Nexus Core — that
lets a human operator run, inspect, and
ground evidence-heavy automation across several domains from one place. It is built to be
*auditable first*: code, ledgers, audits, generated interfaces, and research artifacts are
kept together so a reviewer can always see what exists, what is experimental, and what is
ready for controlled use.

It is organized in three independently reviewable layers:

1. **The implementation platform** — source and offline tests; runtime release is on HOLD.
2. **The research framework (HNC)** — pre-registered, falsifiable hypotheses with evidence.
3. **The vision** — the thread that ties the ancient, the mathematical, and the market together.

> This is the formal front door. The original long-form README is preserved unchanged at
> [`docs/archive/README_legacy_20260712.md`](docs/archive/README_legacy_20260712.md) — nothing was removed, only formalized.

The shared rules for everyone working in this repo are [`docs/AUREON_RULES.md`](docs/AUREON_RULES.md).

### How it fits together

```mermaid
flowchart TB
    user["👤 Operator / Investor / End user"]
    console["Unified console<br/>(React · sidebar · every dashboard as a route)"]
    gateway["Operator gateway · :8790<br/>WSGI · auth · rate-limit · /healthz /readyz /metrics"]

    subgraph brain["Grounded AI core"]
        operator["Aureon Operator<br/>switchboard: ground → consensus → veto"]
        cognition["Agentic cognition<br/>tools · repo-wide grounding · hard boundaries"]
    end

    subgraph organism["The organism (~1,100 modules)"]
        connectome["Connectome<br/>sense · touch · weave"]
        bus["Thought bus · mycelium · Queen"]
        hnc["HNC live daemon → Λ(t) field → harmonic observer"]
    end

    saas["SaaS platform<br/>catalog · status · billing/metering"]
    supabase[("Supabase<br/>auth · tenancy · gas-tank billing")]

    user --> console --> gateway
    gateway --> operator --> cognition
    gateway --> saas
    cognition --> connectome --> bus
    hnc --> bus
    saas --> supabase
    console -. "Supabase session (JWT)" .-> supabase
```

<sub>Every consequential action passes a hard authority boundary + conscience veto before it runs; the platform never trades, pays, or files autonomously.</sub>

---

## 1 · Implementation platform (source-visible; supported runtime is HOLD)

| Capability | What it is | Entry point |
|---|---|---|
| **Aureon Operator** | A grounded AI switchboard — routes a prompt through many models, grounds it in the repo, reaches consensus, and applies a conscience veto before answering. | [`aureon/operator/`](aureon/operator/) · [switchboard doc](docs/architecture/AUREON_OPERATOR_SWITCHBOARD.md) |
| **Agentic cognition** | The operator as an agent: repo-wide grounding, tool use (search / read / code / state), hard authority boundaries enforced before any action. | [`aureon/operator/cognition.py`](aureon/operator/cognition.py) |
| **The organism connectome** | The metacognitive layer that senses, touches, and weaves every module of the body — legacy code included — into one living system. | [`aureon/core/aureon_connectome.py`](aureon/core/aureon_connectome.py) · [doc](docs/architecture/ORGANISM_CONNECTOME.md) |
| **SaaS platform** | A categorized catalog of ~1,100 modules, honest health status, a tenancy bridge, and a billing/metering layer, served behind one gateway. | [`aureon/saas/`](aureon/saas/) · [SAAS_PLATFORM.md](docs/SAAS_PLATFORM.md) |
| **Unified console** | One professional React interface — sidebar, command palette, every dashboard as a route — over the whole repo. | [`frontend/`](frontend/) |
| **Release-boundary implementation** | WSGI, auth, metrics, containers, and CI remain source-visible; supported launchers currently stop at terminal HOLD. | [PRODUCTION_GRADE.md](docs/runbooks/PRODUCTION_GRADE.md) |
| **Multi-user platform** | End-user sign-in with **per-user encrypted keys**, each user reasoning on their own models, and a default-deny boundary between a signed-in user's account and the instance's control plane. | [`aureon/operator/identity.py`](aureon/operator/identity.py) · [MULTI_TENANT_AUTH.md](docs/architecture/MULTI_TENANT_AUTH.md) |

<div align="center">
<img src="public/hnc_dashboard.png" alt="Aureon HNC dashboard" width="48%" />
<img src="public/harmonic_wave_analysis.png" alt="Harmonic wave analysis" width="48%" />
</div>

### Operator preflight, containers, and the strict suite

```bash
# 1 · evaluate the isolated operator protection preflight
pip install -e '.[operator]'
python -I -S -B scripts/bootstrap/protected_bootstrap_v05.py --target-id operator

# 2 · build and evaluate the container protection preflights
docker compose -f deploy/docker-compose.saas.yml up --build

# 3 · run the strict-tier test suite (offline, no keys/network)
AUREON_LLM_OFFLINE=1 pytest tests/test_operator_*.py tests/test_saas_*.py tests/test_connectome.py -q
```

### Current local verification boundary

Everything needed to inspect source and run offline tests is in this repo. Do not
inject exchange, model, hosting, or deployment credentials while validating the
current release: the isolated operator bootstrap, containers, and supervisor
entrypoints stay on **HOLD**.

The local installer is the path that brings a clone up. Linux and macOS:
`bash production/install.sh`. Windows: `production\Install-AUREON.ps1` (or
`production\install-windows.bat`). `bash scripts/linux/aureon-up.sh` calls that
installer when the virtualenv is missing, then starts the same preflight.
The shell is `http://127.0.0.1:5173/`. Dashboard and Command Center are tabs of
the local console at `http://127.0.0.1:5173/console/local`. Every other
dashboard and status page — the 8080 console, Orca on 8888, market status on
8791, the gateway on 8790, the fusion seat on 8765, the circulation bus on
8799, the neural canvas, the thought-action hub, the error sink, and API B —
is a tab at `http://127.0.0.1:5173/console/seats`, with the other status
pages (queen unified, pro dashboard, master hub, Earth shield, queen web,
system hub, bot hunter, the dashboard API, queen power, trader telemetry,
Kraken telemetry, and the legacy command center) on that same tab row. Those
tabs read the live buses through the gateway. A source that is down, or a
page that draws invented readings, shows the reason and no invented number.
`AUREON_SIMULATED_BOOT` stays unset, so those generators do not load. The launcher leaves port 8080 alone. Live mode turns on when a complete exchange key group is in
`.env`. With no complete group the boot stays paper/public-data and the health
report says `trading_mode=paper/public-data (no exchange keys)`. With keys it
says `trading_mode=live (exchange keys present)`. The launcher does not place
an order by itself. The thought bus health check is
`http://127.0.0.1:8799/healthz`. The fusion seat keeps
`http://127.0.0.1:8765/healthz`.
A HOLD receipt proves only that the fail-closed preflight ran; it is not proof
that the whole system is protected or production-ready.

### Canonical organism launcher

> **Stay on the five-minute quickstart. Do not add your own exchange keys.** This launcher defaults to full autonomy. If exchange keys are in `.env`, the boot can go live and trade.

The terminal-HOLD bootstraps stay holds. The organism launcher is a separate entry. Its default is full autonomy, and it does not place an order by itself:

```bash
scripts/launch/aureon-master.sh
```

Windows uses `scripts/launch/aureon-master.ps1` and `scripts/launch/aureon-master.bat`. On a fresh clone it writes `.env` from `.env.example` when `.env` is absent, installs Python requirements into `.venv`, Node packages for `frontend/`, and the self-host Docker images, then starts the organism and prints a health table. Paths follow the checkout. Trading is live when the operator's own exchange keys are in `.env`. With no keys the report says `trading_mode=paper/public-data (no exchange keys)`. A missing binary, script, or daemon is a blocked row. The mode is in [`AUTONOMY.md`](AUTONOMY.md). The module name and the table are in [`LAUNCHER_INVENTORY.md`](LAUNCHER_INVENTORY.md). What still names a machine is in [`PORTABILITY.md`](PORTABILITY.md).

### How anyone can run it

A fresh clone on your own machine is enough. The launcher does not need Gary's home directory, a hosted runner, or a key that shipped with the repo.

Linux and macOS, from the checkout:

```bash
scripts/launch/aureon-master.sh
```

Windows, from the checkout:

```bat
scripts\launch\aureon-master.ps1
```

`scripts\launch\aureon-master.bat` is the same entry. That one command writes `.env` from `.env.example` when `.env` is absent, installs Python requirements into `.venv`, Node packages for `frontend/`, and the self-host images when Docker answers, then starts the organism. An existing `.env` is left as it is. Paths follow the checkout.

Do not add exchange keys to `.env`. A complete key group (Kraken, Binance, Alpaca, or Capital.com) makes the next boot live, and the health report says `trading_mode=live (exchange keys present)`. With no complete group the same boot stays in paper/public-data mode and the report says `trading_mode=paper/public-data (no exchange keys)`. Do not commit `.env`. The launcher does not place an order by itself. New users should stay on the five-minute quickstart.

The boot is unrestricted by default. `AUREON_AUTONOMY_MODE` unset is `full`. Self-coding may edit any path except credential material, approves its own edits, and commits a patch after that patch's tests pass. Nothing is pushed. There is no kill switch and no kill file: `AUREON_SELF_REPAIR_KILL` and `state/SELF_REPAIR_KILL` do not stop a write or an order. Changes and order attempts are appended to `state/autonomy_audit.jsonl`. The unity exchange brain, the unified market trader, the Capital.com CFD trader, and the micro-profit labyrinth each record an attempt. Secret values are redacted. The same records are published on the circulation thought bus. The metacognition and self-repair loops consume them. After repeated failed self-changes, metacognition raises a concern and lowers its confidence, and self-repair deprioritises a target that keeps failing. A self-patch whose tests fail stays applied. It is not reversed. Credentials are still never written into the repo or into a log.

The health table is the last thing the launcher prints. Each row is `order`, `name`, `status`, `health`, and `reason`. A missing binary, script, or daemon is `blocked` with the reason. The totals are `started`, `blocked`, and `total`.

```bash
scripts/launch/aureon-master.sh --status
scripts/launch/aureon-master.sh --stop
```

`--status` prints that table and starts nothing. `--stop` stops the processes this launcher recorded. Postgres, Redis, or nginx it did not start are left alone. On Windows, pass the same flags to `aureon-master.ps1` or `aureon-master.bat`. Those two flags are ordinary process control.

The existing installer is the one step that also brings up the toolchain and the UI. Linux and macOS:

```bash
bash production/install.sh
```

Windows: `production\Install-AUREON.ps1`, or `production\install-windows.bat`. Running it again is safe. It installs Python, venv, Node, npm, git, and curl when apt, dnf, Homebrew, or winget can, writes `.env` from `.env.example` only when `.env` is absent, installs and builds the frontend, then calls the master launcher above. Docker images are used when the daemon answers. With no daemon the launcher uses its native fallbacks. When the UI answers, the installer prints `Aureon UI: http://127.0.0.1:5173/`.

Installing from git (`pip install git+...`) brings the whole repo, trading modules included. A Hugging Face Space is planned, and nothing is hosted yet, so no Space is switching those modules off.

`PyAudio` in `requirements.txt` needs the system audio headers (`portaudio`) before pip can build it. The Linux installer uses `requirements-linux.txt`, which leaves that package out and includes pytest, so `tests/test_preflight_snags.py` can run in the installer environment. Build the test virtualenv with `python -m venv --copies .venv`. A symlinked interpreter fails 32 evidence tests: `sys.executable` must be a real file inside the venv, which `--copies` provides and a symlink into another prefix does not. The installer creates `.venv` with `--copies`. Pytest prints a header note when the interpreter it is running is itself a symlink.

### Archive of unreferenced root files

`archive/workspace-root/` holds notes, one-off scripts, and captured ledgers that the running fleet does not import. Live organ paths stay where [`aureon_fusion/paths.py`](aureon_fusion/paths.py) and [`aureon_fusion/organ_registry.py`](aureon_fusion/organ_registry.py) name them. Fleet output stays untracked.

Direct-module and go-live runbooks are superseded until native process
containment, target-source measurement, external HNC head anchoring, and
provider-side read-back are proven.

### Multi-user implementation status

The source contains a proposed single-operator and multi-user separation model,
but no supported runtime starts it while the release is on HOLD:

| | The operator | A signed-in end user |
|---|---|---|
| **Keys** | the instance's own, in `os.environ` + the global keystore | **their own**, Fernet-encrypted in an isolated per-account store, masked to last-4 on read, never written into the process environment |
| **Reasoning** | the instance engine, full toolbelt | **their own models**, on a request-scoped engine with a pure-compute toolbelt — no shell, no repo write, no network egress, no instance-state read |
| **Memory** | the shared thought bus and mesh | isolated: their prompts and answers never enter shared instance memory |
| **Control plane** | theirs — switchboard, host actions, approvals, manifests, MCP, instance credentials | **refused**. A tenant reaches an explicit allowlist; every other `/api` route is operator-only by omission |

The intended request boundary is centralized and default-deny rather than
implemented independently per route. This is an implementation claim backed by
tests, not evidence of a deployed tenant service.

The design history and adversarial findings remain in
[`docs/architecture/MULTI_TENANT_AUTH.md`](docs/architecture/MULTI_TENANT_AUTH.md).
Do not add tenant, operator, model, or hosting secrets merely to inspect this
source. Network exposure remains outside the current release boundary.

---

## 2 · The research framework — HNC (pre-registered & falsifiable)

Aureon is built on the **Harmonic Nexus Core (HNC)** — a research framework proposing that a
φ² (golden-ratio-squared) mathematical coherence links ancient knowledge systems, geopolitical
stress in open data, and market dynamics. These are **research hypotheses**, stated as
falsifiable claims with reproduction commands — never as financial promises.

| Claim | Value | Evidence & how to reproduce |
|---|---|---|
| Oil volatility → open-data node activation | r = 0.85, p < 0.001, 24–48h lag | [`CLAIMS_AND_EVIDENCE.md §C1`](docs/CLAIMS_AND_EVIDENCE.md) |
| φ² hydrogen-line reproduction | 1,420.405754 MHz vs NIST 1,420.405752 MHz (ppb) | [`CLAIMS_AND_EVIDENCE.md §C6`](docs/CLAIMS_AND_EVIDENCE.md) |
| Pre-registered predictions (P1–P5) | falsifiable, tracked | [`CLAIMS_AND_EVIDENCE.md`](docs/CLAIMS_AND_EVIDENCE.md) · [falsification protocol](docs/HNC_FALSIFICATION_PROTOCOL.md) |

Every claim links to the file that establishes it and a command you can run. If a claim is not
backed by a source, it is a bug — the repository is the authority. See the full spine in
[`docs/CLAIMS_AND_EVIDENCE.md`](docs/CLAIMS_AND_EVIDENCE.md).

<div align="center">
<img src="docs/images/forensics_feb2026_convergence.jpg" alt="From theory to forensics — Feb 5–6 geomagnetic convergence event, predictions vs verified public data" width="70%" />
<br/><sub>A worked example: the Feb 5–6 geomagnetic-convergence event, predictions checked against verified public data (NASA/NOAA, Reuters). Research/education only — not financial advice.</sub>
</div>

---

## 3 · The vision

> *The same coherence that organized the Ziggurats of Ur, the Great Pyramid, and the Roman road
> network expresses itself now — measurably — in the rhythms of open data and markets. Aureon is
> the instrument built to listen for it, and to act only with a conscience in the loop.*

The full thread — the ancient substrate, the mathematics, the extraction machine, and the
distributed response — is told in the creator's own voice in
[`docs/THE_SYNTHESIS.md`](docs/THE_SYNTHESIS.md).

---

## Company & credentials

**[R&A Consulting and Brokerage Services Ltd](COMPANY.md)** — registered in Northern Ireland,
**company no. NI696693** — trading as **Aureon Zorza Technologies**.

- 🏅 **Silver-level innovator** on the Innovate NI Innovation Framework (Department for the Economy / Tourism NI), awarded 21 July 2025 by the Minister for the Economy. → [certificate](docs/images/innovate_ni_silver_2025.png)
- 🤝 **Community**: a supporter of Street Soccer NI / Homeless World Cup (Norway 2025). → [`COMPANY.md`](COMPANY.md)
- 🌐 Website: [aureonzorzatechnologies.pl](https://aureonzorzatechnologies.pl)
- 📄 License: [MIT](LICENSE) · © 2025 R&A Consulting and Brokerage Services Ltd
- 📚 Cite this source: [`CITATION.cff`](CITATION.cff) — Aureon OS / Harmonic Nexus Core. Rights holder R&A Consulting and Brokerage Services Ltd, company no. **NI696693**. The package version in that file is not a go-live clearance. The release boundary stays **HOLD**.
- 💬 Discussions: [`docs/COMMUNITY.md`](docs/COMMUNITY.md) — welcome for [GitHub Discussions](https://github.com/RA-CONSULTING/Aureon-OS/discussions). A thread is about the source. Go-live stays **HOLD**.
- Full company details: [`COMPANY.md`](COMPANY.md)

### Early interest

Open-source repository traffic to date (verifiable in the repo's GitHub **Insights → Traffic**):

<div align="center">
<img src="docs/images/github_traffic_infographic.jpg" alt="GitHub clone traffic: 4,559 unique cloners, 51,287 clone operations, Dec 2025–Mar 2026" width="46%" />
<img src="docs/images/github_clone_traffic_insights.jpg" alt="GitHub Insights traffic — clones over 14 days" width="46%" />
</div>

<sub>These are **repository clone-traffic** figures (developer/researcher interest in the code), not user, customer, or revenue numbers. Source: GitHub Insights.</sub>

---

## Where to go next

| You are… | Start here |
|---|---|
| **Working on Aureon OS** | [`docs/AUREON_RULES.md`](docs/AUREON_RULES.md) — the shared rulebook |
| **An investor or funder** | [`docs/investor/README.md`](docs/investor/README.md) — diligence path, capability categories, and claim discipline |
| **A developer** | [`docs/INDEX.md`](docs/INDEX.md) · [`CAPABILITIES.md`](CAPABILITIES.md) · [`docs/SAAS_PLATFORM.md`](docs/SAAS_PLATFORM.md) |
| **A researcher** | [`docs/THE_SYNTHESIS.md`](docs/THE_SYNTHESIS.md) · [`docs/CLAIMS_AND_EVIDENCE.md`](docs/CLAIMS_AND_EVIDENCE.md) · [`docs/research/READING_PATHS.md`](docs/research/READING_PATHS.md) |
| **Deployment status** | [`docs/runbooks/GO_LIVE_HARDENING.md`](docs/runbooks/GO_LIVE_HARDENING.md) · [`docs/deployment/`](docs/deployment/) — terminal HOLD; no supported listener or deploy route |
| **Running it for several users** | [`docs/architecture/MULTI_TENANT_AUTH.md`](docs/architecture/MULTI_TENANT_AUTH.md) — the account/instance boundary and how it is enforced |
| **Checking what the numbers mean** | [`docs/architecture/DATA_PROVENANCE_AUDIT.md`](docs/architecture/DATA_PROVENANCE_AUDIT.md) — which readings are live, which are withheld as `no_data`, and which generated feeds are opt-in |
| **Browsing the whole repo** | [`docs/REPO_SITEMAP.md`](docs/REPO_SITEMAP.md) · the console's `#repo-map` tab |
| **Contributing** | [`CONTRIBUTING.md`](CONTRIBUTING.md) · [`SECURITY.md`](SECURITY.md) · [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) |
| **Talking with the community** | [`docs/COMMUNITY.md`](docs/COMMUNITY.md) — Discussions welcome. Go-live stays **HOLD** |
| **Citing the source** | [`CITATION.cff`](CITATION.cff) — Aureon OS / HNC / R&A Consulting, company no. NI696693 |

---

## Continuous integration

Quality evidence is suite- and revision-specific. Run the current offline tests
and static checks rather than relying on historical pass counts or badges. A
passing implementation suite does not override the terminal release HOLD.

The hosted GitHub Actions status badges below turn green once Actions is enabled on the
organization (they reflect hosted runs, not the local gate):

[![Operator CI](https://github.com/RA-CONSULTING/Aureon-OS/actions/workflows/operator-ci.yml/badge.svg)](https://github.com/RA-CONSULTING/Aureon-OS/actions/workflows/operator-ci.yml)
[![Aureon CI](https://github.com/RA-CONSULTING/Aureon-OS/actions/workflows/main_ci.yml/badge.svg)](https://github.com/RA-CONSULTING/Aureon-OS/actions/workflows/main_ci.yml)
[![Nightly benchmark](https://github.com/RA-CONSULTING/Aureon-OS/actions/workflows/nightly-benchmark.yml/badge.svg)](https://github.com/RA-CONSULTING/Aureon-OS/actions/workflows/nightly-benchmark.yml)

```bash
# reproduce the gate locally
pip install -e '.[operator,dev]'
ruff check aureon/operator/ aureon/saas/ && mypy aureon/operator/ aureon/saas/
AUREON_LLM_OFFLINE=1 pytest tests/test_operator_*.py tests/test_saas_*.py tests/test_connectome.py -q

# evaluate the capability-demo protection preflight; it currently returns HOLD
# without importing or booting the capability surface. That is not a measured
# capability result.
AUREON_LLM_OFFLINE=1 AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS=1 \
  python -I -S -B scripts/bootstrap/protected_bootstrap_v05.py --target-id capability-demo -- --report docs/reports/CAPABILITY_DEMO.md
```

## Operating boundaries

Aureon is designed for **controlled local operation with a human in the loop**. Live trading,
warehouse mutation, filing support, payment activity, and other sensitive workflows require
explicit operator review, valid credentials, and route-specific evidence — the platform never
initiates them autonomously. Public documentation describes capability and repository state; it
is **not financial, legal, tax, or regulatory advice**, and nothing here is an offer of
securities or a promise of returns. Private credentials, customer data, and sensitive local
evidence are not published in this repository.

---

<div align="center">
<sub>Aureon OS · Harmonic Nexus Core — a product of R&A Consulting and Brokerage Services Ltd, trading as Aureon Zorza Technologies.</sub>
</div>
