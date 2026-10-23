# Local portability

A clone of this repository is the organism. Setup and the master launcher do not read Gary's home, a Sero box path, or a hosted runner.

```bash
scripts/launch/aureon-master.sh
```

Windows: `scripts/launch/aureon-master.ps1` and `scripts/launch/aureon-master.bat`.

What that entry does on a machine that has never seen this tree:

1. If `.env` is absent, it copies `.env.example` and applies a safe overlay. Live trading stays `0`. `ALPACA_PAPER` and `CAPITAL_DEMO_MODE` are `true`. QuickBooks mutation stays `false` and the environment stays `sandbox`. Empty keys stay empty. An existing `.env` is not rewritten and is not committed.
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

The daemon pulled the image and refused to start it: `unable to find user ContainerUser: no matching entries in passwd file` (exit 125). A Windows container cannot run here. Path logic for Windows is still covered by the repo-relative `Path(__file__)` / `SERO_WORKSPACE` resolution, which does not name a profile. The shell wrappers remain `scripts/launch/aureon-master.ps1` and `aureon-master.bat`.

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

Hosted CI and GitHub Actions are not part of this path. A billing lock on the forge does not gate a local start.
