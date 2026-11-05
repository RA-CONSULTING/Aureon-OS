# Windows guarded smoke

This is the path for a Windows machine that has never seen this checkout. Live trading stays off. The release boundary stays **HOLD**. Supported go-live stays **HOLD**.

Other notes in `docs/windows/` are earlier write-ups. Use this file for the guarded stack.

## What you need

- Windows 10 or Windows 11
- Python 3.11 or newer from [python.org](https://www.python.org/downloads/windows/), including the `py` launcher
- Node.js 20 or newer, which includes `npm`
- Git
- A clone of this repository

`install.cmd` does not install those programs and does not call winget. Open a new terminal after installing Python or Node so `PATH` picks them up.

## Smoke

In Command Prompt or PowerShell, from the checkout:

```bat
install.cmd --smoke
```

The same command with an execution policy bypass, if you call the PowerShell file yourself:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 --smoke
```

Wait until the log prints `SMOKE PASSED`. The script then stops the stack.

`SMOKE PASSED` means the local guarded stack answered. QGITA detection rate stays **HOLD**. No order is placed. Exchange keys stay unset for this process. A `.env` file in the checkout stays unread and is left as it is.

The supervisor sets `AUREON_AUTONOMY_MODE=guarded`, `AUREON_LIVE_TRADING=0`, and `AUREON_LLM_OFFLINE=1`, and drops credential-shaped variables from the child environment.

## Leave the stack up

```bat
install.cmd
```

Stop it:

```bat
install.cmd --stop
```

| Surface | URL |
|---|---|
| Dashboard | http://127.0.0.1:5173/ |
| Operator health | http://127.0.0.1:8790/healthz |
| Operator ready | http://127.0.0.1:8790/readyz |
| Public MCP | http://127.0.0.1:8077/mcp |
| Cognition | http://127.0.0.1:8787/api/cognition |
| Stack health | http://127.0.0.1:8787/healthz |

## What the command installs

1. `.venv`, when `.venv\Scripts\python.exe` is absent, using `py -3` when that launcher is Python 3.11 or newer, otherwise `python`.
2. Python packages from `requirements-plug.lock`.
3. Dashboard packages with `npm ci --ignore-scripts --prefix frontend` when `frontend\node_modules\vite\bin\vite.js` is absent.

On Windows the dashboard process is `node frontend\node_modules\vite\bin\vite.js`. The supervisor starts each child in its own process group and stops the tree with `taskkill /T`, then `taskkill /F /T`.

## What stays HOLD

Supported go-live stays **HOLD** after a local smoke. Receipts 2–5 in [`docs/runbooks/GO_LIVE_HARDENING.md`](../runbooks/GO_LIVE_HARDENING.md) stay open.

`production\Install-AUREON.ps1` is a separate installer. It can write `.env` from `.env.example` and it calls `scripts\launch\aureon-master.ps1`. A complete exchange key group in `.env` can make that boot live. The guarded smoke command is `install.cmd`.

The contract for this path is also in [`PORTABILITY.md`](../../PORTABILITY.md).

## If it stops early

| Message | What to do |
|---|---|
| `Python 3.11 or newer is required` | Install Python 3.11 or newer and open a new terminal. |
| `Node.js 20 or newer` | Install Node.js 20 or newer and open a new terminal. |
| `Could not create .venv` | The `py` launcher or `python` on `PATH` is older than 3.11. |
| `dashboard binary missing` | `npm ci` did not leave `frontend\node_modules\vite\bin\vite.js`. |
| `stack already recorded` | Run `install.cmd --stop`, then run the smoke again. |
| `SMOKE FAILED` | The lines above that sentence name the check that failed. The stack is stopped. Live trading stayed off. |
