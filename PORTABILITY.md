# Local portability

A clone of this repository is the organism. Setup and the master launcher do not read Gary's home, a Sero box path, or a hosted runner.

```bash
scripts/launch/aureon-master.sh
```

Windows organism launcher: `scripts/launch/aureon-master.ps1` and `scripts/launch/aureon-master.bat`.

Windows guarded smoke (live trading off, `.env` unread, release boundary **HOLD**): `install.cmd --smoke`. That path is separate from the organism launcher. The procedure is in [Windows guarded smoke](#windows-guarded-smoke) and [`docs/windows/GUARDED_SMOKE.md`](docs/windows/GUARDED_SMOKE.md).

What the organism launcher does on a machine that has never seen this tree:

1. If `.env` is absent, it copies `.env.example` and applies a safe overlay. The template's secret lines are blank placeholder names (Charlie rule: never a real key value). The copy does not assign the live-trading switch. It ships `AUREON_DISABLE_REAL_ORDERS=1`, `AUREON_DRY_RUN=1`, `DRY_RUN=1`, `ALPACA_PAPER=true`, and `CAPITAL_DEMO` / `CAPITAL_DEMO_MODE` on demo. Those disable and dry-run lines are the file's values. They are not a lock. When autonomy is full and a complete exchange key group is present, the launcher's last write overrides those disable and dry-run flags. That is a full+keyed master boot. Exchange keys in `.env` make that boot live. A blank root `.env` is not the only source: a complete key group in the inherited shell, or in `aureon_radar/.env`, arms the same boot. QuickBooks mutation stays `false` and the environment stays `sandbox`. Empty keys in the copy stay empty. An existing `.env` is not rewritten and is not committed. The three postures are in [`docs/PUBLIC_ENV.md`](docs/PUBLIC_ENV.md).
2. `SERO_WORKSPACE` for every child is the checkout being launched. It is not written into `.env`, so moving the checkout does not leave a stale absolute path behind.
3. Python requirements go into `.venv` (`requirements-linux.txt` on Linux, `requirements.txt` on Windows). Node packages go into `frontend/`. Docker images are pulled only when `docker info` answers. The launcher does not install the Python, Node, or Docker *binaries*. `production/install.sh` (Windows: `production/Install-AUREON.ps1`) does that toolchain step when apt, dnf, Homebrew, or winget can, builds the frontend, then calls this launcher.
4. Organs that need an exchange key pair and do not have one are a `blocked` row beginning `missing credential:`. The names of the missing variables are printed. The values are not.

`--status` does not write `.env` and does not install. `--stop` stops only processes this launcher recorded.

## What a clean run still refuses

These are honest skips, not a dependency on one operator's machine:

- Exchange, broker, QuickBooks, and model keys. The public default has none.
- Docker, when the daemon is absent or the socket is not readable by the user. Compose rows then use a host process where one exists, or stay blocked.
- Seven organ scripts named by `aureon_fusion` that are not in this tree (`real_time_data_feeder.py`, `schumann_real_daemon.py`, `planetary_monitor_daemon.py`, `solar_system_collector.py`, `sero_space_weather.py`, `sero_autonomous_expansion.py`, `soul_protection_daemon.py`).
- Faculty state files that are runtime output and are not tracked.
- `organ/aureon_radar_suite` and `organ/orca_unified_kill_chain`. The launcher does not arm live trading.
- `loop/self_repair` until `AUREON_SELF_REPAIR_ENABLE` is set and `state/self_repair_config.json` says enabled.
- Ollama, when nothing answers `127.0.0.1:11434`.
- Desktop and audio packages (PyAudio, pycaw, opencv-python, pytesseract, screeninfo, keyboard, mouse, pyautogui, sounddevice) on Linux. The launcher retries without them.
- `python -m venv` on a Debian/Ubuntu interpreter built without ensurepip. The launcher keeps that partial `.venv` and finishes the install with `uv` when `uv` is on `PATH` or at the current user's `~/.local/bin/uv`. That home path is the current user, not a fixed username.

## Proof

Linux. A `git clone --no-hardlinks` of this checkout was mounted at `/work` in `python:3.12-slim-bookworm` plus Debian `git`, `nodejs`, and `npm`. The process ran as `porter` (uid 2000), `HOME=/home/porter`, `AUREON_LIVE_TRADING=0`, `PYTHONPATH=/work`, with no exchange keys and no Docker socket. `whoami` printed `porter`. The launcher wrote `.env` owned by uid 2000: live trading `0`, Alpaca paper and Capital demo on, exchange keys empty, no `SERO_WORKSPACE` line, no home directory in the file. Exit 0. The table is in [`LAUNCHER_INVENTORY.md`](LAUNCHER_INVENTORY.md): `started=33 blocked=31 total=64`. `deps/docker` is `docker not installed`. The trader row is `missing credential:`.

Windows. This host's Docker engine is Linux. One attempt:

```
docker run --rm --platform windows/amd64 mcr.microsoft.com/windows/nanoserver:ltsc2022
```

The daemon pulled the image and refused to start it: `unable to find user ContainerUser: no matching entries in passwd file` (exit 125). A Windows container cannot run here. Path logic for Windows is still covered by the repo-relative `Path(__file__)` / `SERO_WORKSPACE` resolution, which does not name a profile. The shell wrappers for the organism launcher remain `scripts/launch/aureon-master.ps1` and `aureon-master.bat`. The guarded stack for a Windows stranger is `install.cmd`, in the section below. This host did not execute that smoke. Supported go-live stays **HOLD**.

## What still names a machine

These are not consulted as the launcher's host path. They stay because rewriting them would invent history or break a reviewed pin.

| Where | What remains |
|---|---|
| `deploy/selfhost/docker-compose.yml` | `SERO_WORKSPACE: /workspace` is the container mount of the checkout (`../../:/workspace`), not a host home. |
| `deploy/selfhost/image/` | Gitignored image snapshot. A fresh clone does not contain it. Tracked sources it was copied from resolve through the checkout. |
| `frontend/public/aureon_adaptive_skills/**/skill.json` | Recorded forge metadata. Thousands of `asset_path` values name `C:\Users\user\aureon-trading` and an integrated snapshot. The launcher does not open those paths. A loader that honors `asset_path` should ignore a path that sits outside the checkout. |
| `docs/`, `aureon-trading/docs/`, `flameborn/`, `archive/`, `data/research/` | Historical prose, grant inventories, and evidence. `data/research/grants/scripts/gather_gary_aureon_metadata_research_20260712.py` still lists `.kimi_openclaw` as a glob to *exclude* from a metadata gather. |
| `aureon/operator/design_candidate_test_evidence.py` | Reviewed Windows Node pin `C:/Program Files/nodejs/node.exe`, sha256-bound. Linux has no fallback to `PATH`. Tests require that string. |
| `aureon/operator/website_source_rationalisation.py` | Reviewed Windows PowerShell pin `C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe`, sha256-bound. Absent on Linux, the check fails closed. |
| `aureon/search/online_research_cinema.py` | Optional `C:/Windows/Fonts/arial.ttf`, used only when that file exists; otherwise the default font. |
| `aureon/portals/ifs.py` | Docstring example of the default Chrome install path for a local debugging port. The code uses `AUREON_CDP_URL` on `127.0.0.1`. |
| `aureon/autonomous/vm_control/simulated.py` | Canned `dir` text mentions a Windows `C:\` listing. `pwd` and `cd` answer `.` |
| `aureon/autonomous/aureon_agent_core.py` | Windows disk usage is `C:\`, the system drive, not a profile. |
| `aureon/trading/bounded_binance_roundtrip.py`, `aureon/autonomous/aureon_coding_capability_unblocker.py` | The name "Gary Leckey" is an identity check in those modules, not a filesystem path. |

Hosted CI and GitHub Actions are not part of the organism-launcher path. A billing lock on the forge does not gate a local start.

## Windows guarded smoke

A Windows machine that has never seen this tree can boot the same local stack as `./install.sh` without the organism launcher. From the checkout, in Command Prompt or PowerShell:

```bat
install.cmd --smoke
```

`powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 --smoke` is the same command. `install.cmd` sets `ExecutionPolicy Bypass` for that process only. The step-by-step page is [`docs/windows/GUARDED_SMOKE.md`](docs/windows/GUARDED_SMOKE.md).

What that command does:

1. Requires Python 3.11 or newer (`py -3`, otherwise `python`) and Node.js 20 or newer, already on `PATH`. Python and Node stay the operator's to install. winget stays outside this command.
2. Creates `.venv` when `.venv\Scripts\python.exe` is absent, then installs `requirements-plug.lock`. The organism launcher stays out of this command.
3. Runs `npm ci --ignore-scripts --prefix frontend` when `frontend\node_modules\vite\bin\vite.js` is absent.
4. Starts `scripts\plug_and_play.py`. That supervisor sets `AUREON_AUTONOMY_MODE=guarded`, `AUREON_LIVE_TRADING=0`, and `AUREON_LLM_OFFLINE=1`, strips credential-shaped variables, and leaves `.env` unread. An existing `.env` stays on disk, unmodified. Exchange keys stay unset for this process.
5. `--smoke` requests the local endpoints and then stops. `--stop` stops a stack this supervisor recorded. With no flags the stack stays up until `--stop`.

On Windows the supervisor starts each child in its own process group and stops the tree with `taskkill /T`, then `taskkill /F /T`. The dashboard command is `node frontend\node_modules\vite\bin\vite.js`. POSIX still uses `start_new_session`, `os.killpg`, and `frontend/node_modules/.bin/vite`. `install.sh` is unchanged.

`production\Install-AUREON.ps1` is a different installer. It can write `.env` and it calls the organism launcher. A complete exchange key group in `.env` can make that boot live. The guarded smoke command is `install.cmd`.

Supported go-live stays **HOLD**. A log line `SMOKE PASSED` means the guarded local stack answered. Receipts 2–5 in [`docs/runbooks/GO_LIVE_HARDENING.md`](docs/runbooks/GO_LIVE_HARDENING.md) stay open. This checkout was prepared on Linux. It did not start a Windows container, and it did not execute `install.cmd --smoke`. The tests check the script contract. `.github/workflows/windows-contract.yml` parses `install.ps1` on `windows-latest` and runs those tests. That parse is not a smoke of the stack.

