# Architecture Snapshot

Date: 2026-05-14

## Runtime surfaces

### Web server
- `server.mjs`
- local UI: `http://127.0.0.1:4173`
- responsibilities:
  - serve UI assets
  - route AI provider calls
  - expose chat API
  - expose Aureon-related APIs
  - preserve Cloudflare-compatible asset path

### Local companion runtime
- `runtime/server.mjs`
- local runtime: `http://127.0.0.1:7331`
- responsibilities:
  - host terminal execution REST API
  - host PTY WebSocket terminal
  - Docker sandbox execution
  - sandbox PTY WebSocket terminal
  - local-only trust boundary by default

### Aureon bridge
- launcher: `scripts/start_aureon_brain_local.sh`
- default bridge: `http://127.0.0.1:5566`
- responsibilities:
  - bridge to Gary's Aureon runtime
  - provide local Aureon chat path
  - persist Aureon vault/log outputs

### Cloudflare worker deployment surface
- worker entry: `workers/index.mjs`
- config: `wrangler.jsonc`
- assets source: `dist-workers/`
- responsibilities:
  - optional workers.dev deployment path
  - cloud-side provider proxying
  - preserve deployability of the existing web app

## UI layers

### Active core UI
- provider picker
- model picker
- role selector
- standard chat
- Codex Agent mode
- Aureon Agent mode
- CLI Terminal mode
- Docker Sandbox mode

### Hidden but preserved UI
- observer/classroom controls
- metacognition panel
- research feed
- Aureon systems sync

## Security boundaries

- browser is not a root shell
- `sudo` remains copy-only in the UI
- command safety checks remain explicit
- Docker sandbox is preferred for publication-track execution
- remote access is opt-in and disabled by default
