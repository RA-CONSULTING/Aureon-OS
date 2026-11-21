# Local consolidated stack runbook

This is the single operational entry for the selected non-model Aureon stack on
this Windows checkout. It keeps real orders and exchange mutations off. It does
not change the supported go-live status, which stays **HOLD**.

## Canonical checkout and branch

- Checkout: `C:\Users\samle\Aureon-OS`
- Consolidation branch: `consolidation/20261121`
- Python: `.venv\Scripts\python.exe`
- Launcher: `scripts\launch\aureon-local-organism.ps1`
- Watchdog: `scripts\launch\aureon-stack-service.ps1`
- Task Scheduler task: `AureonOS-LocalStack`

Other checkouts on this machine are archived copies, not additional runtime
entries. Do not start a second stack from them. See
[Archived checkouts](#archived-checkouts) below before deleting anything.

## Start, status, stop

Run PowerShell from the checkout root:

```powershell
# Start the selected components, rotate bounded logs, refresh the
# generated registry when requested, and start the health monitor.
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\launch\aureon-local-organism.ps1

# Start only the core runtime: no Vite dashboard and no mind hub.
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\launch\aureon-local-organism.ps1 -CoreOnly

# Read-only status: service, launcher process table, and one monitor report.
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\launch\aureon-local-organism.ps1 -Status

# Stop the watchdog, the monitor, and every process the launcher recorded.
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\launch\aureon-local-organism.ps1 -Stop

# One monitor pass without starting anything.
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\launch\aureon-local-organism.ps1 -Monitor

# Start only the monitor watcher (singleton).
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\launch\aureon-local-organism.ps1 -Watch

# Regenerate the system registry before starting.
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\launch\aureon-local-organism.ps1 -RefreshRegistry

# Report loaded env files and model reachability without printing values.
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\launch\aureon-local-organism.ps1 -EnvStatus
```

The launcher fixes this environment for every child:

```text
AUREON_LIVE_TRADING=0
AUREON_DISABLE_REAL_ORDERS=1
AUREON_DISABLE_EXCHANGE_MUTATIONS=1
AUREON_ORDER_INTENT_PUBLISH=0
AUREON_UNIFIED_ORDER_EXECUTOR=0
AUREON_DRY_RUN=1
AUREON_PLUG_AND_PLAY=0
AUREON_AUTONOMY_MODE=full
```

`AUREON_AUTONOMY_MODE=full` is the public default. It is not live-trading
authority. No complete exchange credential group is present, so the market
runtime stays paper/public-data and reports `stale=true`.

## Selected components and ports

| Component | Port or signal | Expected state |
|---|---|---|
| `organ/hnc_core` | `state/hnc_live_trace.jsonl` | fresh |
| `organ/hnc_live_daemon` | `state/hnc_live_trace.jsonl` | fresh |
| `organ/organism_circulation` | `http://127.0.0.1:8799/healthz` | 18 connectors, loops heard |
| `organ/operator_gateway` | `http://127.0.0.1:8790/readyz` | 200; `/healthz` is liveness |
| `organ/frontend_vite` | `http://127.0.0.1:5173/` | 200 after first cold build |
| `organ/unified_market_status` | `http://127.0.0.1:8791/api/terminal-state` | degraded without keys |
| `organ/mind_thought_action_hub` | `http://127.0.0.1:13002/api/thoughts` | degraded while warming up |
| `organ/bus_bridge` | `aureon_fusion/state/bus_bridge.log` | fresh |

`organ/frontend_vite` and `organ/mind_thought_action_hub` are optional dashboard
components. The core-only profile skips them and the monitor marks them
`skipped`, not down. The mind hub serves thoughts and health while
`status=initializing`; treat that as degraded, not down.

## Watchdog service

`AureonOS-LocalStack` runs at logon and calls the launcher every 300 seconds.
The launcher starts only missing components; it never duplicates a live
recorded PID.

- Service PID: `state\launcher\service.pid`
- Stop flag: `state\launcher\service.stop`
- Service log: `state\launcher\logs\stack_service.log` (rotated by the service)
- Launcher PID table: `state\launcher\pids.json`

The stack service is the process that survives a terminal session. Processes
started directly from a terminal or agent session can be killed when that
session ends, so use the Task Scheduler task or the launcher for anything that
must stay up.

When `state\launcher\core-only` exists, the watchdog passes `-CoreOnly` to the
launcher. Create the marker with:

```powershell
New-Item -ItemType File -Force -Path .\state\launcher\core-only
```

Remove it to let the watchdog start the full eight-component stack again.

`-Stop` writes the stop flag and stops the service. Delete
`state\launcher\service.stop`, or start with the launcher, before expecting the
logon task to run again.

## Logs and rotation

Active files:

| File | Cap |
|---|---:|
| `thoughts.jsonl` | 8 MiB |
| `aureon_fusion/state/unified_bus.jsonl` | 8 MiB |
| `state/hnc_live_trace.jsonl` | 16 MiB |
| `state/launcher/logs/*.log` | 8 MiB |
| `aureon_fusion/state/*.log` | 8 MiB |
| `state/monitor/monitor.jsonl` | 2 MiB, two backups |
| `state/monitor/monitor.out.log` | quiet watch mode; not used for the report |
| `state/monitor/monitor.err.log` | stderr only |

The launcher sets `AUREON_THOUGHT_BUS_MAX_BYTES=8388608`,
`AUREON_THOUGHT_BUS_BACKUPS=2`, and
`AUREON_UNIFIED_BUS_MAX_BYTES=8388608`. The rotation helper also keeps only the
two newest timestamped unified-bus archives, because the in-process rotation
does not delete old archives.

Manual rotation and registry helpers:

```powershell
.\.venv\Scripts\python.exe scripts\ops\rotate_logs.py --dry-run
.\.venv\Scripts\python.exe scripts\ops\rotate_logs.py
.\.venv\Scripts\python.exe scripts\ops\ensure_system_registry.py
.\.venv\Scripts\python.exe scripts\ops\ensure_system_registry.py --force
```

`rotate_logs.py` shifts archives and never truncates. On Windows it skips a
file another process holds open. The stack service rotates its own log at cycle
start.

## Health monitor

The monitor is read-only. It checks recorded PID ownership, HTTP endpoints,
log/trace freshness, ThoughtBus and unified-bus traffic, the generated system
registry, HNC truth/freshness, and free disk.

```powershell
.\.venv\Scripts\python.exe scripts\monitor\aureon_health_monitor.py
.\.venv\Scripts\python.exe scripts\monitor\aureon_health_monitor.py --json
.\.venv\Scripts\python.exe scripts\monitor\aureon_health_monitor.py --watch --interval 60 --quiet
```

Outputs:

- `state\monitor\health.json` - latest full report
- `state\monitor\monitor.jsonl` - bounded history
- `state\monitor\monitor.pid` - watch singleton

Exit code is `0` for `ok` or `degraded`, and `1` when connectivity or a checked
subsystem (bus, HNC, registry, or disk) is `down`.

The monitor distinguishes these cases:

- A frontend that listens on 5173 but misses the HTTP timeout is `degraded`,
  not `down`.
- An operator that serves `/healthz` before `/readyz` is mounted is `degraded`,
  not `down`.
- A quiet operator log is `idle` while HTTP is responsive; the gateway does not
  write a line for every health probe.
- Market `stale=true` and mind `initializing=true` are expected degraded states.
- In the core-only profile, the frontend and mind hub are `skipped` and are not
  counted as down.

## System registry

The operator coordinator reads `aureon_system_registry.json` from the checkout
root. It is generated inventory, not source. `ensure_system_registry.py`
regenerates it when missing or older than seven days.

At consolidation the registry contained 2,118 systems across 12 categories and
the coordinator logged `SystemCoordinator initialized with 2118 systems`.

## Measured consolidation state, 21 November 2026

These are observations from this host, not guarantees:

- All eight selected parent processes were alive.
- Ports 5173, 8790, 8791, 8799, and 13002 were bound.
- Bus traffic was about 1,010 messages per 300 seconds from 18 sources.
- The bus bridge log was fresh.
- The operator returned HTTP 200 on `/readyz` and `/healthz`.
- The frontend returned HTTP 200 on `/` after a 12.4 second warm request.
- The mind hub served `/api/thoughts` with `status=initializing`.
- Market status was `stale=true`, `trading_ready=false`.
- HNC reported `data_status=live`, `truth_status=real_derived`,
  `freshness_status=fresh`.
- Free disk was about 0.7 GiB. The pagefile had grown to about 10.3 GiB, so disk
  remains the main host constraint.

The monitor reported `overall=degraded` because of the expected market and mind
warnings plus low disk. Connectivity stayed `ok` with all eight processes up.

### Disk emergency and core-only recovery

At about 11:47 the system-managed pagefile reached 10.78 GiB and the volume
reported 0 bytes free. The full stack was stopped to avoid corrupt writes. Only
generated runtime logs were deleted; no source, other checkout, `node_modules`,
package cache, or application data was removed. The deleted logs regenerate.

The core-only profile is the current recovery state:

- Active: HNC core, HNC live daemon, organism circulation, operator gateway,
  unified market status, and bus bridge.
- Skipped: Vite frontend and mind thought/action hub.
- Monitor: `overall=down` because disk is below the 512 MiB critical threshold;
  `connectivity=ok` and all six active processes are up.

The marker is `state\launcher\core-only`. To restore the full stack, free at
least 1.5 GiB first, remove the marker, and restart the task. Options include
closing memory-heavy applications, moving data off the volume, or setting a
smaller fixed pagefile with administrator rights and a reboot. Hibernation is
enabled and `hiberfil.sys` is about 1.6 GiB; disabling it would free that file
but changes a system power setting and needs the owner's approval.

## Host pressure and frontend warm-up

This host has 4 CPUs and about 3.8 GiB of physical memory. The Ollama desktop
app was holding about 4.2 GiB of private memory with no model loaded; stopping
that app freed the commit charge that was blocking the stack. The Ollama API
service was left running.

Vite's first page load can take tens of seconds while it transforms the React
graph. The monitor's bound-port fallback covers that window. Do not kill Vite
merely because the first request is slow; check whether 5173 is listening and
whether `/@vite/client` eventually answers.

## Safety boundaries

- No order is placed by this stack.
- No exchange keys are present in the root `.env`.
- `live_trading_armed_by_launcher=false`.
- The operator provider is `aureon-own` with the
  `AureonUnavailableAdapter`; the pinned `aureon-7b-v65k` model is not available
  at `127.0.0.1:11435`.
- The supported production go-live status stays **HOLD**.
- The guarded fresh-machine path is `install.cmd --smoke`, not this runtime.

## Archived checkouts

Do not delete these without explicit owner approval. They are not part of the
single runtime entry.

| Path | What it is | Disposition |
|---|---|---|
| `C:\Users\samle\Aureon-OS-integration` | Git worktree sharing the canonical `.git`; branch `audit/full-system-20261119` at `7ed6896e` | clean; unique QGITA and bus fixes already ported |
| `C:\Users\samle\Aureon-OS-merge` | Separate repository; branch `audit/merge-train-20261119` at `592a18ca` | unfinished shell-guard WIP preserved as `wip/shell-guard-20261121` = `125a6357` |
| `C:\Users\samle\Aureon-pr-407` | Plain export without `.git` | redundant |
| `C:\Users\samle\aureon-deploy` | Deployment evidence and an operator key | do not read or print the key; rotate only if the owner asks |
| `C:\Users\samle\AureonObsidianVault` | small vault directory | leave in place |

The canonical repository also has a local remote named `merge-local` pointing
at the merge checkout so the preserved WIP ref is reachable from the canonical
checkout.

## Troubleshooting

**Port 5173 listens but `/` times out.** Wait for the first Vite transform. Run
`curl.exe -m 150 http://127.0.0.1:5173/`. If it still fails, check
`state\launcher\logs\organ_frontend_vite.log`, then restart Vite through the
watchdog by stopping its recorded PID and letting the next service cycle start
it.

**Monitor says `overall=down` but processes are up.** Read
`state\monitor\health.json` and the `detail` column. A down HTTP status with a
live port is reported as degraded; an actual missing PID is down.

**Operator `/readyz` returns 404.** The old process may still be loading. The
monitor falls back to `/healthz` and reports degraded until `/readyz` is
mounted.

**Disk warning.** Free space below 1.5 GiB is degraded; below 512 MiB is down.
The pagefile and other applications can consume space faster than the stack
logs. Delete only generated artifacts you own; do not remove another checkout,
`node_modules`, package caches, or application data without approval.

**Stop did not stay stopped.** `-Stop` leaves
`state\launcher\service.stop`. Remove it before the logon task can start a new
service, or start with the launcher, which removes the flag.
