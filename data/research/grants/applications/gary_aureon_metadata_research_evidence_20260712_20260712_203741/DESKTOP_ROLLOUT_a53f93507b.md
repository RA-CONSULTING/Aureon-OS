# Desktop Rollout

Branch target: `desktop-runtime-experiment`

## Goal

Run FlameBorn as a desktop-first local AI environment while preserving rollback to the stable web savepoint.

## Install

```bash
cd /home/l/CodexPROsSparrow
npm run desktop:install
```

## Start

```bash
npm run desktop:start
```

Or:

```bash
bash scripts/start_desktop_experiment.sh
```

## Smoke check

```bash
npm run desktop:smoke
```

## Packaging

Install desktop dependencies first:

```bash
cd /home/l/CodexPROsSparrow
npm run desktop:install
```

Create an unpacked Linux desktop build:

```bash
cd /home/l/CodexPROsSparrow/desktop
npm run pack:dir
```

Current artifact path after a successful build:

```text
/home/l/CodexPROsSparrow/desktop/dist/linux-unpacked/flameborn-desktop-experiment
```

## Recommended preflight

1. Docker group is refreshed in the current shell if sandbox mode is required.
2. `npm run check` passes.
3. `curl -s http://127.0.0.1:7331/health` works when runtime is up.
4. `curl -s http://127.0.0.1:4173/api/aureon/status` works when web UI is up.

## In-app desktop controls

Desktop shell adds a `Desktop Control` panel for:
- web service status
- local runtime status
- Aureon status
- Docker sandbox readiness summary
- restart actions for web/runtime/Aureon
- opening logs

Chat-side desktop commands:
- `/desktop help`
- `/desktop status`
- `/desktop restart web`
- `/desktop restart runtime`
- `/desktop restart aureon`
- `/desktop open logs`

## Current limitations

- no packaged installer yet
- no signed desktop binaries yet
- no native auto-update flow yet
- host PTY and sandbox PTY are functional paths, but UI still needs more polish for long coding sessions

## Rollback

```bash
cd /home/l/CodexPROsSparrow
git checkout web-stable-savepoint
```
