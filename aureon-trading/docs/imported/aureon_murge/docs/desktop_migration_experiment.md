# Desktop Migration Experiment

Branch: `desktop-runtime-experiment`
Date: 2026-05-14

## Objective

Begin a desktop-first migration without replacing or destroying the stable web application.

## Experiment scope

Implemented in this branch:
- separate `desktop/` module
- Electron shell scaffold
- secure preload bridge
- runtime manager that can auto-start:
  - `server.mjs`
  - `runtime/server.mjs`
- documented env controls

## Preserved from web savepoint

- `web-stable-savepoint` remains the rollback branch
- Cloudflare worker path remains intact
- existing provider integrations remain intact
- current local runtime remains the execution layer

## Deliberately not done yet

- no forced rewrite to React/Next.js
- no desktop-only auth rewrite yet
- no key rotation
- no destruction of worker deploy path
- no hidden remote access

## Next desktop tasks

1. add desktop status bar for web/runtime/Aureon/Docker health
2. wire xterm tabs directly inside desktop shell
3. decide whether chat should target local runtime for Codex-like orchestration
4. split desktop settings from web settings
5. document desktop OAuth redirect changes if OAuth is added later
