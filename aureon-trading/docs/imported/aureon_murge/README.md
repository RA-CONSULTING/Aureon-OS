# flAmeBornLLC / LLM Academy

Legal, open-source AI coding environment for local development and future Cloudflare deployment.

## Core model

The project is split into two layers:

1. Web app
   - chat UI
   - provider routing
   - Classroom / observer features
   - branding and user workflows
2. Local companion runtime
   - host terminal execution
   - PTY sessions
   - Docker sandbox orchestration
   - localhost REST + WebSocket bridge

This keeps the security boundary explicit:
- the browser does not get direct privileged host access
- `sudo` stays manual and visible in the real terminal
- containerized execution is the publication-track path

## Current architecture

- Web app: `http://127.0.0.1:4173`
- Local runtime: `http://127.0.0.1:7331`
- Aureon Phi Bridge: `http://127.0.0.1:5566`
- Docker sandbox image: `flameborn-runtime:24.04`

Docs:
- `docs/ARCHITECTURE.md`
- `docs/SECURITY.md`
- `docs/LOCAL_RUNTIME_SETUP.md`
- `docs/DOCKER_SANDBOX.md`

## Quick start

### 1. App server

```bash
cd /home/l/CodexPROsSparrow
node server.mjs
```

Open:
`http://127.0.0.1:4173`

### 2. Local runtime companion

```bash
cd /home/l/CodexPROsSparrow
npm run runtime:start
```

Health check:

```bash
curl -s http://127.0.0.1:7331/health
curl -s http://127.0.0.1:7331/api/runtime/info
```

### 2b. Desktop shell experiment

```bash
cd /home/l/CodexPROsSparrow/desktop
npm install
npm start
```

Or from repo root:

```bash
cd /home/l/CodexPROsSparrow
npm run desktop:start
```

### 3. Docker sandbox build

```bash
cd /home/l/CodexPROsSparrow
npm run sandbox:build
curl -s http://127.0.0.1:7331/api/sandbox/status
```

If runtime reports:
- `dockerAvailable: true`
- `dockerCliAvailable: true`
- `imageAvailable: true`

then `Docker Sandbox` mode is ready.

## UI behavior

Agent modes currently available:
- `Standard chat`
- `Codex Agent`
- `Aureon Agent`
- `CLI Terminal`
- `Docker Sandbox`

Runtime-backed features now use the companion app on `localhost:7331`:
- `/api/terminal/status`
- `/api/terminal/run`
- `/api/sandbox/status`
- `/api/sandbox/run`
- `/ws/terminal`
- `/ws/sandbox-terminal`

## Security rules

- `sudo` and `su` are copy-only in the web UI
- destructive host commands are blocked or require explicit approval
- Docker sandbox is isolated per session
- remote browser access is disabled by default
- no hidden persistence, no privilege bypass, no silent escalation

## Controlled remote mode

Default mode is local-only.

For a trusted deployed web app later, configure the local runtime with explicit origins:

```bash
export FLAMEBORN_RUNTIME_TRUSTED_ORIGINS="https://your-cloudflare-app.example"
export FLAMEBORN_RUNTIME_ALLOW_REMOTE=false
npm run runtime:start
```

The runtime still binds to localhost by default. The deployed app talks to the user's local runtime through the browser.

## Existing provider layer

Current provider support in the web app:
- Gemini
- OpenRouter
- Hugging Face
- Grok
- OpenAI
- Aureon bridge

Gemini keys can also be loaded from:
`~/.config/gemini/env`

## Existing research / observer layer

- Classroom Mode
- Open Research Feed
- Metacognition Monitor
- Aureon systems sync

## Checks

```bash
cd /home/l/CodexPROsSparrow
npm run check
```

## Status of this implementation

Already implemented:
- companion runtime on `7331`
- host terminal REST bridge
- Docker sandbox REST bridge
- sandbox PTY streaming over WebSocket
- runtime-oriented frontend wiring
- security documentation

Not fully migrated yet:
- frontend is still plain HTML/CSS/JS, not Next.js/React/Tailwind
- no full TypeScript migration yet
- local host PTY exists in runtime, but the current UI still uses the simpler command panel for host execution and xterm for sandbox execution

That is intentional. Stability and security were prioritized over framework churn.
