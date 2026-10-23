# Launcher inventory

One canonical entry brings the checkout up. It does not arm live trading. That switch stays with Gary.

```
python -m aureon.launch.master
```

Linux: `scripts/launch/aureon-master.sh`
Windows: `scripts/launch/aureon-master.ps1` and `scripts/launch/aureon-master.bat`

These older names are thin wrappers around the same entry. They do not arm live trading and they do not copy `.env`:

- `python -m aureon.autonomous.aureon_master_launcher`
- `aureon_radar/launch_all.bat`
- `aureon_radar/launch_all_fixed.bat`
- `aureon_radar/start_radar.bat`
- `aureon_radar/start_radar.sh`

The terminal-hold scripts stay holds. `deploy/start_master_launcher.sh`, `scripts/linux/aureon-up.sh`, `scripts/shell/start/*.sh`, the Windows bootstrap `.ps1`/`.cmd` files, and the root `docker-compose.yml` files still enter the isolated bootstrap and do not start this stack. The compose file this launcher uses is `deploy/selfhost/docker-compose.yml`.

## Flags

| Flag | What it does |
|---|---|
| *(none)* | Start every component, in dependency order, then print the health table. |
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

Built from `deploy/selfhost/docker-compose.yml`, `aureon_fusion.organ_registry.ORGAN_ORDER`, and `aureon_fusion.flight_recorder.FACULTY_FILES`, plus the seat, the two loops, the dashboard rollup, and the Windows stdio repair. Sixty components.

| order | name | kind | depends on |
|---:|---|---|---|
| 1 | stdio/windows | stdio | — |
| 2 | compose/postgres | compose | — |
| 3 | compose/redis | compose | — |
| 4 | compose/error_sink | compose | — |
| 5 | compose/api_a | compose | compose/redis, compose/error_sink |
| 6 | compose/api_b | compose | compose/redis, compose/error_sink |
| 7 | compose/frontend | compose | — |
| 8 | compose/hnc_core | compose | — |
| 9 | compose/nginx | compose | compose/api_a, compose/api_b, compose/frontend |
| 10 | seat/trading_world_v5b | seat | — |
| 11 | organ/unified_market_trader | organ | exchange key pair, or the row is blocked |
| 12 | organ/operator_gateway | organ | — |
| 13 | organ/frontend_vite | organ | compose/frontend |
| 14 | organ/unified_market_status | organ | — |
| 15 | organ/market_stream_feeder | organ | — |
| 16 | organ/real_time_data_feeder | organ | script at the workspace root |
| 17 | organ/schumann_real_daemon | organ | script at the workspace root |
| 18 | organ/planetary_monitor_daemon | organ | script at the workspace root |
| 19 | organ/solar_system_collector | organ | script at the workspace root |
| 20 | organ/sero_space_weather | organ | script at the workspace root |
| 21 | organ/sero_autonomous_expansion | organ | script at the workspace root |
| 22 | organ/aureon_radar_bridge | organ | signal/dry-run bridge |
| 23 | organ/aureon_radar_suite | organ | not started; live suite |
| 24 | organ/mind_thought_action_hub | organ | — |
| 25 | organ/self_questioning_ai | organ | Ollama on 127.0.0.1:11434 |
| 26 | organ/hnc_core | organ | — |
| 27 | organ/soul_protection_daemon | organ | script at the workspace root |
| 28 | organ/mind_neural_canvas | organ | — |
| 29 | organ/queen_mind | organ | the queen |
| 30 | organ/heartbeat_daemon | organ | — |
| 31 | organ/grand_wheel | organ | — |
| 32 | organ/knowledge_pulse_feeder | organ | — |
| 33 | organ/trading_progress_monitor | organ | — |
| 34 | organ/_portfolio_writer_loop | organ | — |
| 35 | organ/_temporal_refresh_loop | organ | temporal refresh |
| 36 | organ/_world_digest_loop | organ | — |
| 37 | organ/_harmonic_seed_loop | organ | upstream producer |
| 38 | organ/global_energy_aggregator | organ | — |
| 39 | organ/orca_unified_kill_chain | organ | not started; order loop |
| 40 | organ/orca_command_center | organ | dashboard |
| 41 | organ/unity_supervisor | organ | dry-run supervisor |
| 42 | organ/flight_recorder | organ | faculty recorder |
| 43 | organ/bus_bridge | organ | — |
| 44 | organ/assessment_snapshot_producer | organ | module must exist |
| 45 | organ/harmonic_affect_producer | organ | — |
| 46 | organ/hnc_live_daemon | organ | HNC loop |
| 47 | faculty/hnc_core | faculty | organ/hnc_core |
| 48 | faculty/real_time_data | faculty | organ/real_time_data_feeder |
| 49 | faculty/schumann | faculty | organ/schumann_real_daemon |
| 50 | faculty/knowledge_pulse | faculty | organ/knowledge_pulse_feeder |
| 51 | faculty/trading_progress | faculty | organ/trading_progress_monitor |
| 52 | faculty/real_portfolio | faculty | organ/_portfolio_writer_loop |
| 53 | faculty/temporal_outlook | faculty | organ/_temporal_refresh_loop |
| 54 | faculty/prophecy_summary | faculty | organ/flight_recorder |
| 55 | faculty/news_geo_digest | faculty | organ/flight_recorder |
| 56 | faculty/heartbeat_last_results | faculty | organ/heartbeat_daemon |
| 57 | faculty/organ_registry | faculty | organ/flight_recorder |
| 58 | loop/self_repair | repair | enable flag and config; respects `AUREON_AUTONOMY_MODE` |
| 59 | loop/self_coder | coder | respects `AUREON_AUTONOMY_MODE`; kill switch blocks it |
| 60 | dashboards | dashboards | frontend, vite, neural canvas, orca command center, mind hub, market status |

## Fresh-clone health table

Command, from a clean `git clone` of this commit, with `AUREON_LIVE_TRADING=0` and no exchange keys:

```
python -m aureon.launch.master
```

Exit 0. Docker's socket was not reachable, Ollama was absent, `node_modules` is not in the clone, and the faculty state files are not tracked. Postgres and Redis were already answering on the host, so those rows are `started` and `--stop` does not touch them. The exact table:

```
AUREON MASTER LAUNCHER
autonomy_mode=guarded
live_trading_armed_by_launcher=false
platform=linux
parent_AUREON_LIVE_TRADING=0

order  name                                status    health   reason
-----  ----------------------------------  -------   ------   ------
1      stdio/windows                       started   ok       posix streams usable; CONOUT$ repair is the Windows path
2      compose/postgres                    started   ok       pg_isready accepted database aureon; launcher did not start postgres and will not stop it
3      compose/redis                       started   ok       redis answered PONG; launcher did not start redis and will not stop it
4      compose/error_sink                  started   ok       docker daemon not reachable: permission denied while trying to connect to the docker API at unix:///var/run/docker.sock; host error_sink pid 1140837; http://127.0.0.1:8088/healthz answered
5      compose/api_a                       blocked   down     docker daemon not reachable: permission denied while trying to connect to the docker API at unix:///var/run/docker.sock; host seat is seat/trading_world_v5b on 127.0.0.1:8765
6      compose/api_b                       started   ok       docker daemon not reachable: permission denied while trying to connect to the docker API at unix:///var/run/docker.sock; host api_b pid 1140838; http://127.0.0.1:8766/healthz answered
7      compose/frontend                    started   ok       docker daemon not reachable: permission denied while trying to connect to the docker API at unix:///var/run/docker.sock; host frontend pid 1140839; http://127.0.0.1:5173/ answered
8      compose/hnc_core                    blocked   down     docker daemon not reachable: permission denied while trying to connect to the docker API at unix:///var/run/docker.sock; local Master-Equation seat is organ/hnc_core
9      compose/nginx                       started   ok       127.0.0.1:8080/healthz already answered; launcher did not bind it and will not stop it
10     seat/trading_world_v5b              started   ok       v5b seat is the fusion API on 127.0.0.1:8765; pid 1140841; http://127.0.0.1:8765/healthz answered
11     organ/unified_market_trader         blocked   down     missing credential: KRAKEN_API_KEY+KRAKEN_API_SECRET or BINANCE_API_KEY+BINANCE_API_SECRET or ALPACA_API_KEY+ALPACA_SECRET_KEY or CAPITAL_API_KEY+CAPITAL_IDENTIFIER+CAPITAL_PASSWORD
12     organ/operator_gateway              started   ok       pid 1140842
13     organ/frontend_vite                 blocked   down     script not present: vite.js
14     organ/unified_market_status         started   ok       pid 1140843; http://127.0.0.1:8791/ answered
15     organ/market_stream_feeder          started   ok       pid 1140844
16     organ/real_time_data_feeder         blocked   down     script not present: real_time_data_feeder.py
17     organ/schumann_real_daemon          blocked   down     script not present: schumann_real_daemon.py
18     organ/planetary_monitor_daemon      blocked   down     script not present: planetary_monitor_daemon.py
19     organ/solar_system_collector        blocked   down     script not present: solar_system_collector.py
20     organ/sero_space_weather            blocked   down     script not present: sero_space_weather.py
21     organ/sero_autonomous_expansion     blocked   down     script not present: sero_autonomous_expansion.py
22     organ/aureon_radar_bridge           started   ok       pid 1140845
23     organ/aureon_radar_suite            blocked   down     launcher does not arm live trading and does not create capital_release.flag
24     organ/mind_thought_action_hub       started   ok       pid 1140846; http://127.0.0.1:13002/ answered
25     organ/self_questioning_ai           blocked   down     ollama not answering http://127.0.0.1:11434/api/tags
26     organ/hnc_core                      started   ok       pid 1140847
27     organ/soul_protection_daemon        blocked   down     script not present: soul_protection_daemon.py
28     organ/mind_neural_canvas            started   ok       pid 1140848; http://127.0.0.1:13012/ answered
29     organ/queen_mind                    started   ok       pid 1140849
30     organ/heartbeat_daemon              started   ok       pid 1140852
31     organ/grand_wheel                   started   ok       pid 1140853
32     organ/knowledge_pulse_feeder        started   ok       pid 1140854
33     organ/trading_progress_monitor      started   ok       pid 1140855
34     organ/_portfolio_writer_loop        started   ok       pid 1140856
35     organ/_temporal_refresh_loop        started   ok       pid 1140857
36     organ/_world_digest_loop            started   ok       pid 1140858
37     organ/_harmonic_seed_loop           started   ok       pid 1140859
38     organ/global_energy_aggregator      started   ok       pid 1140860
39     organ/orca_unified_kill_chain       blocked   down     order loop does not read the live-trading switch; launcher will not start it
40     organ/orca_command_center           started   down     pid 1140861; process alive; http://127.0.0.1:8888/ did not answer yet
41     organ/unity_supervisor              started   ok       pid 1140862; dry-run so the supervisor cannot bypass credential or live-trading gates
42     organ/flight_recorder               started   ok       pid 1140863
43     organ/bus_bridge                    started   ok       pid 1140864
44     organ/assessment_snapshot_producer  blocked   down     module not present: aureon.autonomous.aureon_assessment_snapshot_producer
45     organ/harmonic_affect_producer      started   ok       pid 1140865
46     organ/hnc_live_daemon               started   ok       pid 1140866
47     faculty/hnc_core                    blocked   down     faculty state file absent: hnc_core_state.json
48     faculty/real_time_data              blocked   down     faculty state file absent: real_time_data.json
49     faculty/schumann                    blocked   down     faculty state file absent: schumann_state.json
50     faculty/knowledge_pulse             blocked   down     faculty state file absent: knowledge_pulse.json
51     faculty/trading_progress            blocked   down     faculty state file absent: trading_progress_state.json
52     faculty/real_portfolio              blocked   down     faculty state file absent: real_portfolio_state.json
53     faculty/temporal_outlook            blocked   down     faculty state file absent: temporal_outlook.json
54     faculty/prophecy_summary            blocked   down     faculty state file absent: prophecy_summary.json
55     faculty/news_geo_digest             blocked   down     faculty state file absent: news_geo_digest.json
56     faculty/heartbeat_last_results      blocked   down     faculty state file absent: heartbeat_last_results.json
57     faculty/organ_registry              blocked   down     faculty state file absent: organ_registry.json
58     loop/self_repair                    blocked   skipped  self-repair not enabled: AUREON_SELF_REPAIR_ENABLE is unset; launcher does not enable it
59     loop/self_coder                     started   ok       standing by; autonomy=guarded; launcher does not invent a goal or run a patch
60     dashboards                          started   ok       up: compose/frontend, organ/unified_market_status, organ/mind_thought_action_hub, organ/mind_neural_canvas, organ/orca_command_center

started=33 blocked=27 total=60
```
