# Web Stable Savepoint

Date: 2026-05-14
Project root: `/home/l/CodexPROsSparrow`
Primary branch before savepoint: `main`
Savepoint branch: `web-stable-savepoint`
Follow-up experiment branch: `desktop-runtime-experiment`

## Current architecture

The application currently has a hybrid structure with a stable web-first UI and local execution companions:

1. Web app server
   - file: `server.mjs`
   - serves the main UI on `http://127.0.0.1:4173`
   - handles chat/provider routing
   - exposes web API routes for provider chat, Aureon status, and classroom-related features
2. Cloudflare worker deployment path
   - file: `workers/index.mjs`
   - config: `wrangler.jsonc`
   - static bundle target: `dist-workers/`
3. Local companion runtime
   - file: `runtime/server.mjs`
   - local runtime target: `http://127.0.0.1:7331`
   - host terminal REST bridge
   - PTY/WebSocket support
   - Docker sandbox orchestration
4. Local Aureon bridge launcher
   - file: `scripts/start_aureon_brain_local.sh`
   - Aureon Phi Bridge target: `http://127.0.0.1:5566`

## Working features

Core chat features:
- multi-provider routing in the web UI
- Gemini support
- OpenRouter support
- OpenAI support
- Hugging Face support
- Grok support
- Aureon bridge support
- PL/EN language toggle
- provider/model selection
- role-based prompting

Execution/runtime features:
- local command runner through companion runtime
- command risk classification
- `sudo` and `su` kept copy-only in the web UI
- Docker sandbox image build path
- Docker sandbox REST execution path
- local PTY host terminal WebSocket path
- sandbox PTY WebSocket path

Deployment and integration features:
- Cloudflare worker deployment configuration preserved
- Wrangler config preserved
- local runtime preserved as separate layer
- Aureon integration preserved
- existing API key flow preserved

Deferred/hidden features currently preserved in code but disabled in active UI:
- Classroom/observer lab
- Open Research Feed
- Metacognition Monitor
- Aureon systems sync panel

## Known issues

- Docker sandbox depends on the runtime process being started from a shell that has refreshed Docker group membership.
- If runtime is launched from a stale shell, sandbox status may report `EACCES /var/run/docker.sock` even after the image is built successfully.
- The frontend is currently plain HTML/CSS/JS rather than React/Next.js.
- Desktop migration has not replaced the web deployment path; it is experimental and must stay reversible.

## Deployment instructions

### Web app local

```bash
cd /home/l/CodexPROsSparrow
node server.mjs
```

Open:
`http://127.0.0.1:4173`

### Companion runtime local

```bash
cd /home/l/CodexPROsSparrow
bash scripts/start_flameborn_runtime.sh
```

### Docker sandbox health

```bash
newgrp docker
cd /home/l/CodexPROsSparrow
npm run sandbox:build
curl -s http://127.0.0.1:7331/api/sandbox/status
```

Expected healthy fields:
- `dockerAvailable: true`
- `dockerCliAvailable: true`
- `imageAvailable: true`

### Cloudflare worker path

```bash
cd /home/l/CodexPROsSparrow
npm run cf:build
npm run cf:dev
```

Deploy later with:

```bash
npm run cf:deploy
```

## Rollback instructions

Return to stable web savepoint:

```bash
cd /home/l/CodexPROsSparrow
git checkout web-stable-savepoint
```

Return to original main line:

```bash
git checkout main
```

Discard desktop experiment and return to savepoint:

```bash
git checkout web-stable-savepoint
git branch -D desktop-runtime-experiment
```

## Included snapshots

- `docs/architecture_snapshot.md`
- `docs/dependency_snapshot.md`
- `docs/environment_variables.md`
- `docs/migration_notes.md`
