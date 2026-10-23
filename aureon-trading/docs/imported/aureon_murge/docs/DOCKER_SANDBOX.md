# Docker Sandbox

## Build

```bash
cd /home/l/CodexPROsSparrow
npm run sandbox:build
```

## Verify

```bash
curl -s http://127.0.0.1:7331/api/sandbox/status
```

Expected healthy fields:
- `dockerAvailable: true`
- `dockerCliAvailable: true`
- `imageAvailable: true`

## Execution model

- one container per session
- workspace mounted into `/workspace`
- shell runs as `coder`
- container base: Ubuntu 24.04

## Current state

- REST command execution is implemented
- PTY streaming is implemented for sandbox terminal over WebSocket
