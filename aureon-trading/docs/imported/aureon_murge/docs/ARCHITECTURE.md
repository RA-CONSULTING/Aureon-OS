# Architecture

## Legal execution model

Cloudflare-hosted web UI cannot safely or directly control a user's privileged local shell.

The supported model is:

Cloudflare or local web app
-> browser
-> localhost companion runtime
-> PTY / shell or Docker sandbox

## Components

### Web app
- `index.html`
- `script.js`
- `style.css`
- `server.mjs`

Responsibilities:
- AI chat
- provider routing
- Classroom features
- terminal/sandbox UI
- calling the companion runtime

### Companion runtime
- `runtime/server.mjs`

Responsibilities:
- host command execution
- PTY session management
- Docker session management
- WebSocket streaming
- command safety checks
- local-only trust boundary

### Docker sandbox
- `runtime/Dockerfile`

Responsibilities:
- reproducible execution environment
- isolation
- session workspaces
- bounded CPU/RAM

## Runtime endpoints

REST:
- `GET /health`
- `GET /api/runtime/info`
- `GET /api/terminal/status`
- `POST /api/terminal/run`
- `GET /api/sandbox/status`
- `POST /api/sandbox/run`

WebSocket:
- `/ws/terminal`
- `/ws/sandbox-terminal`

## Design choices

- `sudo` is never silently executed from the web UI
- Docker sandbox is the preferred publication path
- host execution remains explicit and auditable
- remote access is deny-by-default
