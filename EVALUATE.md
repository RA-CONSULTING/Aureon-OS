# Evaluating Aureon OS: the one supported path

This page is for an outside evaluator who wants to download Aureon OS, run it,
and inspect it. There is one supported evaluation route: a full `git clone`
and `./install.sh`. The master launcher, the `scripts/launchers/` files, the Docker image and
provider deployments are not this evaluation route. They are listed at the end so nobody
mistakes one for this path.

Go-live stays **HOLD**. This is research-stage software. Running the steps
below is an evaluation, not a go-live clearance and not a validation of the
release.

## What you need

- Linux or macOS with `bash`. (Windows: `install.cmd --smoke`, see
  [`docs/windows/GUARDED_SMOKE.md`](docs/windows/GUARDED_SMOKE.md). No Windows
  run has been measured yet.)
- Python 3.11 or newer with `venv` (on Debian or Ubuntu, `python3-venv`).
- Node.js 20 or newer with `npm`.
- Network access for the first install: pip and npm fetch packages.
- Free disk for the checkout, `.venv`, the dashboard dependencies and logs.
- No exchange keys and no `.env`. `./install.sh` does not read `.env`.

## Step 1: clone

```bash
git clone https://github.com/RA-CONSULTING/Aureon-OS.git
cd Aureon-OS
```

Use a full clone. Do not use `--depth 1` or GitHub's Download ZIP: the public
MCP server checks Aureon files against a pinned git commit that must be in the
local history.

## Step 2: run the guarded smoke

```bash
./install.sh --smoke
```

This creates `.venv`, installs the pinned `requirements-plug.lock`, installs the
dashboard with `npm ci --ignore-scripts --prefix frontend`, starts the local
stack on `127.0.0.1` only, requests each endpoint, prints a `SMOKE` line per
check, and stops the stack. The run is in guarded mode:
`AUREON_AUTONOMY_MODE=guarded`, `AUREON_LIVE_TRADING=0`,
`AUREON_DISABLE_REAL_ORDERS=1`, `AUREON_DISABLE_EXCHANGE_MUTATIONS=1`,
`AUREON_LLM_OFFLINE=1`. The language-model line is the offline adapter. No
order is placed.

The smoke binds these loopback ports while it runs:

| Service | Default |
|---|---|
| operator API | `127.0.0.1:8790` |
| public MCP server | `127.0.0.1:8077/mcp` |
| dashboard | `127.0.0.1:5173` |
| stack health and the HNC / Auris / QGITA report | `127.0.0.1:8787` |

If any of those ports is taken, move the stack with `AUREON_PLUG_OPERATOR_PORT`,
`AUREON_PLUG_MCP_PORT`, `AUREON_PLUG_FRONTEND_PORT` and `AUREON_PLUG_STACK_PORT`,
for example:

```bash
AUREON_PLUG_OPERATOR_PORT=28790 AUREON_PLUG_MCP_PORT=28077 \
AUREON_PLUG_FRONTEND_PORT=25173 AUREON_PLUG_STACK_PORT=28787 \
./install.sh --smoke
```

A passing run ends with `SMOKE PASSED`. A failing run ends with `SMOKE FAILED`
and names each failed check. Child logs are in `deploy/plug/runtime/`.

## Step 3 (optional): leave the stack up and inspect it

```bash
./install.sh          # same guarded stack, left running
./install.sh --stop   # stop it
```

With the stack up, the URLs above can be opened in a browser or with `curl`.
The cognition report at `/api/cognition` on the stack port shows measured HNC,
Auris and QGITA output with evidence tags. Missing feeds read as unavailable or
`no_data`; the stack does not invent values.

## Known state

Every claim on this page is about what the steps do. Whether a given commit
passes the smoke is recorded per commit, not here. On a clean clone of `main`
at `05089138` (12 Nov 2026), the install, operator, readiness, dashboard and
MCP initialize checks passed, and the smoke ended `SMOKE FAILED` because the
three public MCP tools refused with `checkout … differs from pin`. A candidate tag is not ready to send until its own clean-clone smoke ends
`SMOKE PASSED` and the wider readiness review is complete. A smoke pass alone
does not establish that every feature works or that the checkout is bug-free.

## Not evaluation routes

- **Master launcher** (`python -m aureon.launch.master`,
  `scripts/launch/aureon-master.sh`, `.ps1`, `.bat`). It writes `.env` from
  `.env.example` when `.env` is absent and boots live trading once a complete
  exchange key group is present. Do not use it for evaluation.
- **Canonical launchers** (`scripts/launchers/AUREON_PRODUCTION_LIVE.cmd`,
  `scripts/launchers/AUREON_WAKE_UP_FULL_AUTONOMOUS.ps1`,
  `scripts/launchers/AUREON_DATA_OCEAN.cmd`,
  `scripts/launchers/AUREON_DATA_OCEAN.ps1`). On HOLD. Not an approved start.
- **Docker image** (`Dockerfile`, `docker-compose.yml`). A guarded preflight
  that returns a HOLD receipt. It has no listener and starts no Aureon runtime,
  so it is not a way to run the system. See
  [`docs/deployment/PUBLIC_CONTAINER.md`](docs/deployment/PUBLIC_CONTAINER.md).

See also [`INSTALL.md`](INSTALL.md) for a measured walkthrough,
[`AUTONOMY.md`](AUTONOMY.md) for the live route and the absence of a kill
switch, and [`docs/TRUST.md`](docs/TRUST.md) for how changes are reviewed.
