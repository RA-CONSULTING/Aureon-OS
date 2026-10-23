# Launcher inventory

One canonical entry brings the checkout up. It does not arm live trading. That switch stays with Gary.

```
python -m aureon.launch.master
```

Linux: `scripts/launch/aureon-master.sh`
Windows: `scripts/launch/aureon-master.ps1` and `scripts/launch/aureon-master.bat`

These older names are thin wrappers around the same entry. They do not arm live trading. The canonical entry writes `.env` from `.env.example` when `.env` is absent:

- `python -m aureon.autonomous.aureon_master_launcher`
- `aureon_radar/launch_all.bat`
- `aureon_radar/launch_all_fixed.bat`
- `aureon_radar/start_radar.bat`
- `aureon_radar/start_radar.sh`

The terminal-hold scripts stay holds. `deploy/start_master_launcher.sh`, `scripts/linux/aureon-up.sh`, `scripts/shell/start/*.sh`, the Windows bootstrap `.ps1`/`.cmd` files, and the root `docker-compose.yml` files still enter the isolated bootstrap and do not start this stack. The compose file this launcher uses is `deploy/selfhost/docker-compose.yml`.

## Flags

| Flag | What it does |
|---|---|
| *(none)* | Write `.env` from `.env.example` when `.env` is absent, install Python requirements, Node packages, and Docker images, then start every component, in dependency order, and print the health table. |
| `--status` | Health-check only. Nothing is spawned. |
| `--stop` | Stop processes this launcher recorded. Postgres, Redis, or nginx it did not start are left alone. |
| `--only a,b` | Start the named components and the dependencies they declare. |

A missing credential, binary, script, or daemon is a row with status `blocked` and the reason. The process exits 0. An unknown `--only` name exits 2 before anything starts.

## What the launcher will not do

- It never sets `AUREON_LIVE_TRADING=1` and never creates `aureon_fusion/state/capital_release.flag`.
- Every child it spawns receives `AUREON_LIVE_TRADING=0`, an empty `AUREON_FUSION_ARM_LIVE`, and `AUREON_DISABLE_REAL_ORDERS=1`. Gary's value in the parent shell is left as he set it.
- `organ/aureon_radar_suite` stays blocked. That suite is the capital live launcher.
- `organ/orca_unified_kill_chain` stays blocked. That loop places orders and does not read the live-trading switch.
- `organ/unity_supervisor` is started with `--dry-run`, so it cannot open a second ungated fleet behind this launcher's credential gate.
- `loop/self_repair` starts only when `AUREON_SELF_REPAIR_ENABLE` is on and `state/self_repair_config.json` says `{"enabled": true}`. The kill switch blocks it in guarded mode and in full mode. The launcher does not enable repair and does not run a repair cycle.
- `loop/self_coder` stands by in the current `AUREON_AUTONOMY_MODE` (public default `guarded`). The launcher does not invent a goal and does not apply a patch.
- There is no separate v5b module in the tree. `seat/trading_world_v5b` is `aureon_fusion.http_service` bound to `127.0.0.1:8765`. The local fusion token is the one already committed in `deploy/selfhost/docker-compose.yml`.

When Docker is down, compose services fall back to a host process where one exists (error sink, api_b, frontend, nginx, redis). `compose/api_a` points at the trading-world seat instead of binding 8765 twice. `compose/hnc_core` points at `organ/hnc_core`. Postgres is used if `pg_isready -d aureon` answers; the launcher does not run `sudo`.

## Component catalog

Built from `deploy/selfhost/docker-compose.yml`, `aureon_fusion.organ_registry.ORGAN_ORDER`, and `aureon_fusion.flight_recorder.FACULTY_FILES`, plus the dependency installers, the seat, the two loops, the dashboard rollup, and the Windows stdio repair. Sixty-four components.

`deps/env` copies `.env.example` to `.env` when `.env` is absent and applies the safe overlay: live trading stays `0`, Alpaca paper and Capital demo stay on, QuickBooks mutation stays off, and empty keys stay empty. An existing `.env` is left untouched. `SERO_WORKSPACE` is set on each child to the checkout being launched and is not written into `.env`. `deps/python` creates `.venv` (via `python -m venv`, or `uv venv` when that module is missing) and installs `requirements-linux.txt` on Linux or `requirements.txt` on Windows. It never installs into the system interpreter. A PyAudio or desktop-extra failure is retried without those packages. `deps/node` runs `npm install` in `frontend/` when `node` and `npm` are on PATH. It does not run `apt-get`. `deps/docker` runs `docker compose pull` and `docker compose build` for `deploy/selfhost/docker-compose.yml` when the daemon answers. Compose up stays `--no-build`. A missing daemon is a blocked row; host fallbacks still run.

| order | name | kind | depends on |
|---:|---|---|---|
| 1 | deps/env | env_deps | — |
| 2 | deps/python | python_deps | deps/env |
| 3 | deps/node | node_deps | — |
| 4 | deps/docker | docker_deps | — |
| 5 | stdio/windows | stdio | — |
| 6 | compose/postgres | compose | deps/docker |
| 7 | compose/redis | compose | deps/docker |
| 8 | compose/error_sink | compose | deps/docker |
| 9 | compose/api_a | compose | compose/redis, compose/error_sink, deps/docker |
| 10 | compose/api_b | compose | compose/redis, compose/error_sink, deps/docker |
| 11 | compose/frontend | compose | deps/docker |
| 12 | compose/hnc_core | compose | deps/docker |
| 13 | compose/nginx | compose | compose/api_a, compose/api_b, compose/frontend, deps/docker |
| 14 | seat/trading_world_v5b | seat | deps/python |
| 15 | organ/unified_market_trader | organ | exchange key pair, or the row is blocked, deps/python |
| 16 | organ/operator_gateway | organ | deps/python |
| 17 | organ/frontend_vite | organ | compose/frontend, deps/node |
| 18 | organ/unified_market_status | organ | deps/python |
| 19 | organ/market_stream_feeder | organ | deps/python |
| 20 | organ/real_time_data_feeder | organ | script at the workspace root, deps/python |
| 21 | organ/schumann_real_daemon | organ | script at the workspace root, deps/python |
| 22 | organ/planetary_monitor_daemon | organ | script at the workspace root, deps/python |
| 23 | organ/solar_system_collector | organ | script at the workspace root, deps/python |
| 24 | organ/sero_space_weather | organ | script at the workspace root, deps/python |
| 25 | organ/sero_autonomous_expansion | organ | script at the workspace root, deps/python |
| 26 | organ/aureon_radar_bridge | organ | signal/dry-run bridge, deps/python |
| 27 | organ/aureon_radar_suite | organ | not started; live suite, deps/python |
| 28 | organ/mind_thought_action_hub | organ | deps/python |
| 29 | organ/self_questioning_ai | organ | Ollama on 127.0.0.1:11434, deps/python |
| 30 | organ/hnc_core | organ | deps/python |
| 31 | organ/soul_protection_daemon | organ | script at the workspace root, deps/python |
| 32 | organ/mind_neural_canvas | organ | deps/python |
| 33 | organ/queen_mind | organ | the queen, deps/python |
| 34 | organ/heartbeat_daemon | organ | deps/python |
| 35 | organ/grand_wheel | organ | deps/python |
| 36 | organ/knowledge_pulse_feeder | organ | deps/python |
| 37 | organ/trading_progress_monitor | organ | deps/python |
| 38 | organ/_portfolio_writer_loop | organ | deps/python |
| 39 | organ/_temporal_refresh_loop | organ | temporal refresh, deps/python |
| 40 | organ/_world_digest_loop | organ | deps/python |
| 41 | organ/_harmonic_seed_loop | organ | upstream producer, deps/python |
| 42 | organ/global_energy_aggregator | organ | deps/python |
| 43 | organ/orca_unified_kill_chain | organ | not started; order loop, deps/python |
| 44 | organ/orca_command_center | organ | dashboard, deps/python |
| 45 | organ/unity_supervisor | organ | dry-run supervisor, deps/python |
| 46 | organ/flight_recorder | organ | faculty recorder, deps/python |
| 47 | organ/bus_bridge | organ | deps/python |
| 48 | organ/assessment_snapshot_producer | organ | module must exist, deps/python |
| 49 | organ/harmonic_affect_producer | organ | deps/python |
| 50 | organ/hnc_live_daemon | organ | HNC loop, deps/python |
| 51 | faculty/hnc_core | faculty | organ/hnc_core |
| 52 | faculty/real_time_data | faculty | organ/real_time_data_feeder |
| 53 | faculty/schumann | faculty | organ/schumann_real_daemon |
| 54 | faculty/knowledge_pulse | faculty | organ/knowledge_pulse_feeder |
| 55 | faculty/trading_progress | faculty | organ/trading_progress_monitor |
| 56 | faculty/real_portfolio | faculty | organ/_portfolio_writer_loop |
| 57 | faculty/temporal_outlook | faculty | organ/_temporal_refresh_loop |
| 58 | faculty/prophecy_summary | faculty | organ/flight_recorder |
| 59 | faculty/news_geo_digest | faculty | organ/flight_recorder |
| 60 | faculty/heartbeat_last_results | faculty | organ/heartbeat_daemon |
| 61 | faculty/organ_registry | faculty | organ/flight_recorder |
| 62 | loop/self_repair | repair | enable flag and config; respects `AUREON_AUTONOMY_MODE` |
| 63 | loop/self_coder | coder | respects `AUREON_AUTONOMY_MODE`; kill switch blocks it |
| 64 | dashboards | dashboards | frontend, vite, neural canvas, orca command center, mind hub, market status |

## Fresh-clone health table

Command, inside a clean `python:3.12-slim-bookworm` image with Debian `nodejs` and `npm`, as user `porter` (uid 2000), `HOME=/home/porter`, `AUREON_LIVE_TRADING=0`, no exchange keys, no inherited `SERO_WORKSPACE`, and no Docker socket. The tree was a `git clone --no-hardlinks` of this checkout. The launcher wrote `.env` (owner uid 2000) from `.env.example`. Exit 0.

```
python -m aureon.launch.master
```

Docker is not installed in that image, so image pull did not run. Postgres, Redis, and nginx are not installed there either. Ollama was absent. The faculty state files are not tracked. The container exited with the parent process; it did not leave host listeners behind. The exact table:

```
AUREON MASTER LAUNCHER
autonomy_mode=guarded
live_trading_armed_by_launcher=false
platform=linux
parent_AUREON_LIVE_TRADING=0

order  name                                status    health   reason
-----  ----------------------------------  -------   ------   ------
1      deps/env                            started   ok       wrote .env from .env.example; live trading left off; empty keys left empty
2      deps/python                         started   ok       installed requirements-linux.txt into .venv; desktop-only packages in requirements.txt are omitted on this platform; venv present
3      deps/node                           started   ok       npm install finished; vite.js present
4      deps/docker                         blocked   down     docker not installed
5      stdio/windows                       started   ok       posix streams usable; CONOUT$ repair is the Windows path
6      compose/postgres                    blocked   down     docker not installed; pg_isready not installed
7      compose/redis                       blocked   down     docker not installed; redis-server not installed
8      compose/error_sink                  started   ok       docker not installed; host error_sink pid 110; http://127.0.0.1:8088/healthz answered
9      compose/api_a                       blocked   down     docker not installed; host seat is seat/trading_world_v5b on 127.0.0.1:8765
10     compose/api_b                       started   ok       docker not installed; host api_b pid 111; http://127.0.0.1:8766/healthz answered
11     compose/frontend                    blocked   down     docker not installed; organ/frontend_vite owns port 5173
12     compose/hnc_core                    blocked   down     docker not installed; local Master-Equation seat is organ/hnc_core
13     compose/nginx                       blocked   down     docker not installed; nginx not installed
14     seat/trading_world_v5b              started   ok       v5b seat is the fusion API on 127.0.0.1:8765; pid 112; http://127.0.0.1:8765/healthz answered
15     organ/unified_market_trader         blocked   down     missing credential: KRAKEN_API_KEY+KRAKEN_API_SECRET or BINANCE_API_KEY+BINANCE_API_SECRET or ALPACA_API_KEY+ALPACA_SECRET_KEY or CAPITAL_API_KEY+CAPITAL_IDENTIFIER+CAPITAL_PASSWORD
16     organ/operator_gateway              started   ok       pid 113
17     organ/frontend_vite                 started   ok       pid 114; http://127.0.0.1:5173/ answered
18     organ/unified_market_status         started   ok       pid 115; http://127.0.0.1:8791/ answered
19     organ/market_stream_feeder          started   ok       pid 116
20     organ/real_time_data_feeder         blocked   down     script not present: real_time_data_feeder.py
21     organ/schumann_real_daemon          blocked   down     script not present: schumann_real_daemon.py
22     organ/planetary_monitor_daemon      blocked   down     script not present: planetary_monitor_daemon.py
23     organ/solar_system_collector        blocked   down     script not present: solar_system_collector.py
24     organ/sero_space_weather            blocked   down     script not present: sero_space_weather.py
25     organ/sero_autonomous_expansion     blocked   down     script not present: sero_autonomous_expansion.py
26     organ/aureon_radar_bridge           started   ok       pid 117
27     organ/aureon_radar_suite            blocked   down     launcher does not arm live trading and does not create capital_release.flag
28     organ/mind_thought_action_hub       started   ok       pid 118; http://127.0.0.1:13002/ answered
29     organ/self_questioning_ai           blocked   down     ollama not answering http://127.0.0.1:11434/api/tags
30     organ/hnc_core                      started   ok       pid 119
31     organ/soul_protection_daemon        blocked   down     script not present: soul_protection_daemon.py
32     organ/mind_neural_canvas            started   ok       pid 121; http://127.0.0.1:13012/ answered
33     organ/queen_mind                    started   ok       pid 126
34     organ/heartbeat_daemon              started   ok       pid 127
35     organ/grand_wheel                   started   ok       pid 128
36     organ/knowledge_pulse_feeder        started   ok       pid 129
37     organ/trading_progress_monitor      started   ok       pid 131
38     organ/_portfolio_writer_loop        started   ok       pid 132
39     organ/_temporal_refresh_loop        started   ok       pid 133
40     organ/_world_digest_loop            started   ok       pid 134
41     organ/_harmonic_seed_loop           started   ok       pid 135
42     organ/global_energy_aggregator      started   ok       pid 136
43     organ/orca_unified_kill_chain       blocked   down     order loop does not read the live-trading switch; launcher will not start it
44     organ/orca_command_center           started   down     pid 137; process alive; http://127.0.0.1:8888/ did not answer yet
45     organ/unity_supervisor              started   ok       pid 138; dry-run so the supervisor cannot bypass credential or live-trading gates
46     organ/flight_recorder               started   ok       pid 139
47     organ/bus_bridge                    started   ok       pid 140
48     organ/assessment_snapshot_producer  blocked   down     module not present: aureon.autonomous.aureon_assessment_snapshot_producer
49     organ/harmonic_affect_producer      started   ok       pid 141
50     organ/hnc_live_daemon               started   ok       pid 142
51     faculty/hnc_core                    blocked   down     faculty state file absent: hnc_core_state.json
52     faculty/real_time_data              blocked   down     faculty state file absent: real_time_data.json
53     faculty/schumann                    blocked   down     faculty state file absent: schumann_state.json
54     faculty/knowledge_pulse             blocked   down     faculty state file absent: knowledge_pulse.json
55     faculty/trading_progress            blocked   down     faculty state file absent: trading_progress_state.json
56     faculty/real_portfolio              blocked   down     faculty state file absent: real_portfolio_state.json
57     faculty/temporal_outlook            blocked   down     faculty state file absent: temporal_outlook.json
58     faculty/prophecy_summary            blocked   down     faculty state file absent: prophecy_summary.json
59     faculty/news_geo_digest             blocked   down     faculty state file absent: news_geo_digest.json
60     faculty/heartbeat_last_results      blocked   down     faculty state file absent: heartbeat_last_results.json
61     faculty/organ_registry              blocked   down     faculty state file absent: organ_registry.json
62     loop/self_repair                    blocked   skipped  self-repair not enabled: AUREON_SELF_REPAIR_ENABLE is unset; launcher does not enable it
63     loop/self_coder                     started   ok       standing by; autonomy=guarded; launcher does not invent a goal or run a patch
64     dashboards                          started   ok       up: organ/frontend_vite, organ/unified_market_status, organ/mind_thought_action_hub, organ/mind_neural_canvas, organ/orca_command_center

started=33 blocked=31 total=64
```
