# Flameborn + Aureon Integration Guide

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              YOUR MACHINE                                    │
│  ┌─────────────────────┐         HTTP API          ┌─────────────────────┐  │
│  │   Aureon Skeleton   │  ◄──────────────────────►  │  Flameborn Frontend │  │
│  │   (Python/Flask)    │   http://127.0.0.1:5566   │   (Node.js/HTML)    │  │
│  │                     │                           │   Port 4173         │  │
│  │  • Vault UI         │                           │                     │  │
│  │  • Queen voices     │                           │  • Chat UI          │  │
│  │  • Phi Bridge       │                           │  • Classroom mode   │  │
│  │  • Trading brain    │                           │  • Terminal guard   │  │
│  │  • Obsidian sync    │                           │  • Docker sandbox   │  │
│  └─────────────────────┘                           └─────────────────────┘  │
│           ▲                                                    ▲             │
│           │                                                    │             │
│           └────────── 127.0.0.1:7331  ─────────────────────────┘             │
│                        Flameborn Runtime (optional)                          │
│                     Host terminal + Docker sandbox bridge                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Bash (Linux / macOS / Git Bash on Windows)

```bash
cd /path/to/aureon-trading
bash scripts/start_aureon_with_flameborn.sh
```

### PowerShell (Windows)

```powershell
cd C:\path\to\aureon-trading
.\scripts\start_aureon_with_flameborn.ps1
```

### With Runtime + Sandbox

```bash
FLAMEBORN_RUNTIME_ENABLED=true bash scripts/start_aureon_with_flameborn.sh
```

```powershell
.\scripts\start_aureon_with_flameborn.ps1 -StartRuntime -EnableSandbox
```

## Services

| Service | Port | Health Endpoint | Purpose |
|---------|------|-----------------|---------|
| Aureon Vault UI | 5566 | `GET /api/status` | Backend brain, voices, vault |
| Flameborn Web | 4173 | `GET /api/aureon/status` | Chat UI, provider routing |
| Flameborn Runtime | 7331 | `GET /health` | Host terminal, Docker sandbox |

## Health Check

```bash
bash scripts/check_flameborn_integration.sh
```

Returns exit code 0 only if Aureon Vault UI and Flameborn Web are both reachable and the cross-connectivity bridge works.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AUREON_PORT` | `5566` | Aureon Vault UI port |
| `FLAMEBORN_PORT` | `4173` | Flameborn web port |
| `FLAMEBORN_RUNTIME_PORT` | `7331` | Flameborn runtime port |
| `FLAMEBORN_RUNTIME_ENABLED` | `false` | Also start runtime companion |
| `AUREON_API_BASE_URL` | `http://127.0.0.1:5566` | Where Flameborn calls Aureon |
| `AUREON_ENV_PATH` | `repo/.env` | Shared env file loaded by Flameborn |
| `OPENROUTER_API_KEY` | — | Shared LLM key (loaded by both) |
| `GEMINI_API_KEY` | — | Shared Google AI key |

## How It Works

1. **Aureon starts first** (`scripts/runners/run_vault_ui.py` on port 5566).
2. **Flameborn loads shared config** via `AUREON_ENV_PATH` so it inherits Aureon's secrets without duplication.
3. **Flameborn starts** (`flameborn/server.mjs` on port 4173) pointing `AUREON_API_BASE_URL` at Aureon.
4. **User opens** `http://127.0.0.1:4173` and selects the **Aureon Brain** provider — messages flow into Aureon's vault voice layer and replies come back as human-readable text.

## Cloudflare Deployment

For public cloud use, the local runtime cannot bind to `127.0.0.1` from a Worker. Deploy the Aureon bridge to a reachable HTTPS host:

```bash
AUREON_API_BASE_URL=https://your-aureon-bridge.example
AUREON_CHAT_PATH=/api/message
```

Then set these as Cloudflare Worker secrets. See `flameborn/AUREON_BRAIN_INTEGRATION.md` for the full remote-bridge spec.

## Safety Rules

- `sudo` / `su` are copy-only in the web UI.
- Destructive host commands are blocked or require explicit approval.
- Docker sandbox is isolated per session.
- No autonomous trading, Queen execute actions, or external filesystem access from Cloudflare Workers unless explicitly enabled.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Aureon vault UI won't start | Check Python venv: `python scripts/runners/run_vault_ui.py --no-signals --no-ollama` |
| Flameborn can't reach Aureon | Verify `AUREON_API_BASE_URL` and that port 5566 is listening |
| Docker sandbox EACCES | Restart from a refreshed shell: `newgrp docker` then re-run launcher |
| Port already in use | Set `AUREON_PORT`, `FLAMEBORN_PORT`, or `FLAMEBORN_RUNTIME_PORT` env vars |


## Expanded Capabilities (v2.0)

### Orchestrator Control Panel
| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/orchestrator/status` | GET | Scan all Aureon orchestrators (Global, AutonomyHub, Full, Parallel, CommandCenter) |
| `POST /api/orchestrator/spin` | POST | Trigger AutonomyHub spin cycle for a symbol |
| `POST /api/orchestrator/command` | POST | Start/Stop/Status for global orchestrator |

### Neural Pathway Mapper
| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/neural-map` | GET | AST scan of all `aureon/` modules — returns nodes + edges JSON for dependency graph visualization |

### Live Trading Execution
| Endpoint | Method | Description |
|----------|--------|-------------|
| `POST /api/trading/execute` | POST | Paper trade execution (live mode disabled for safety). Generates signal via AutonomyHub and simulates entry. |

### Stress Test Suite
| Endpoint | Method | Description |
|----------|--------|-------------|
| `POST /api/stress-test/run` | POST | Trigger pure-Python load tester. Types: smoke, load, stress, spike, endpoint. Returns SLO-validated JSON report. |

### Real-Time WebSocket Bridge
| Endpoint | Protocol | Description |
|----------|----------|-------------|
| `ws://127.0.0.1:4173/ws/realtime` | WebSocket | Bidirectional stream of Aureon status + synthetic trading ticks every 2s. Auto-reconnects on disconnect. |

### Existing Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/health` | GET | Unified health: Flameborn + Aureon + Runtime |
| `GET /api/aureon/sse` | GET | Server-Sent Events stream (fallback for older browsers) |
| `GET /api/aureon/status` | GET | Aureon vault status proxy |
| `GET /api/aureon/systems` | GET | Aureon systems list proxy |
| `GET /api/aureon/vault/*` | ANY | Full vault proxy to :5566 |
| `GET /api/aureon/capabilities` | GET | 42-module capability scanner |
| `POST /api/aureon/run` | POST | Safe Python script runner |
| `GET /api/trading/status` | GET | Exchange + bot availability |
| `POST /api/world-data/ingest` | POST | Wikipedia/Yahoo/Coingecko search |
| `POST /api/self-enhance/trigger` | POST | Queen self-enhancement engine |
| `GET /api/audit/trail` | GET | Last 50 audit entries |
| `GET /api/coder/skills` | GET | Coding agent skill map |
| `GET /api/llm/models` | GET | Available LLM models |
| `GET /api/integrations/status` | GET | Integration bridge status |

## Running Stress Tests

### From Command Line
```powershell
cd C:\path\to\aureon-trading
python scripts/flameborn_stress_test.py --type all --json
```

### From Flameborn UI
Navigate to the **Stress Test Suite** panel in the sidebar, select a test type, and click **Run Test**.

### SLO Thresholds
- p95 latency < 2000ms
- Error rate < 5%
- Availability >= 99%

## Safety Notes

- **Live trading is DISABLED** from Flameborn UI. Use `Aureon CLI` directly for live execution.
- **Paper trading** generates real signals via `AutonomyHub.spin()` but simulates fills.
- All orchestrator commands run in `dry_run=True` mode by default.
- WebSocket and SSE connections auto-reconnect on failure.
