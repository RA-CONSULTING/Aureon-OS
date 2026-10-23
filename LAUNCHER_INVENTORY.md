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

The table from a fresh clone is written here after the smoke run. A clone has no Docker socket, no exchange keys, no Ollama, and no faculty state files.
