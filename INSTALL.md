# Install from a fresh clone

This is the path that was measured on a clean checkout of `main`. It is a
local, guarded boot. The orange release-boundary badge stays **HOLD**.
Go-live stays **HOLD**.

## What you need

- Python 3.11 or newer (`python3` on `PATH`)
- Node.js 20 or newer (`node` and `npm` on `PATH`)
- On Debian or Ubuntu, `python3-venv`

You do not need a `.env` file. `./install.sh` does not read `.env`.

## Ports

The guarded smoke binds four local ports. They must be free, or the smoke
stops after install:

- operator API: `http://127.0.0.1:8790/`
- public MCP server: `http://127.0.0.1:8077/mcp`
- dashboard: `http://127.0.0.1:5173/`
- stack health: `http://127.0.0.1:8787/`

## Order-safety defaults

`./install.sh`, `install.ps1` / `install.cmd`, and `docker-compose.yml` pin
these by default:

- `AUREON_LIVE_TRADING=0`
- `AUREON_DISABLE_REAL_ORDERS=1`
- `AUREON_DISABLE_EXCHANGE_MUTATIONS=1`

`install.sh` and `install.ps1` export these values every time they run, so
setting them differently in your shell does not change them. To flip them on
this path you would have to edit the installer. The plug-and-play supervisor
also drops credential-shaped variables from the child environment and does
not read `.env`. The test
`tests/test_install_boot_dummy_keys_no_orders.py` checks that the order
guards stay closed with dummy keys present. It is a check of the guard
functions, not a full boot.

> **Warning: do not use the master launcher with exchange keys for
> evaluation.** `python -m aureon.launch.master` (and
> `scripts/launch/aureon-master.sh`, `.ps1`, `.bat`) is a different entry
> point. It writes `.env` from `.env.example` when `.env` is absent and turns
> live trading on once a complete exchange key group is present in `.env`,
> the inherited shell, or `aureon_radar/.env`. For evaluation, stay on
> `./install.sh --smoke` and leave exchange keys unset.

## Linux and macOS

```bash
git clone https://github.com/RA-CONSULTING/Aureon-OS.git
cd Aureon-OS
./install.sh --smoke
```

That command creates `.venv`, installs the pinned
`requirements-plug.lock`, installs the dashboard with
`npm ci --ignore-scripts --prefix frontend` when `frontend/node_modules`
is absent, starts the local stack, requests the endpoints, and stops.

`./install.sh --stop` clears a recorded stack if one is already present.
`./install.sh` with no flags leaves the stack up.

On this measurement, the venv and package installs completed. The smoke
then failed because `127.0.0.1:8790` was already in use on the machine
(`operator gateway failed to bind`). With those ports free, the smoke is
the documented way to see the stack come up and go down again. Missing
feeds should read as unavailable or no reading; the boot must not invent
values.

## Windows

```bat
install.cmd --smoke
```

`install.cmd` runs `install.ps1`. The same order-safety defaults apply.
`.env` stays unread. A Windows run of `install.cmd --smoke` has not been
measured here.

## Docker

`Dockerfile` and `docker-compose.yml` describe a guarded preflight image
that returns **HOLD** and does not start the local operator stack. The
compose file pins the same three order-safety variables. A Docker image
build was not measured here.

## What this is not

This is not a go-live. It does not clear the HOLD badge. It does not
claim a model is available, and it does not place an order.
