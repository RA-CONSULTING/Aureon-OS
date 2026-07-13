# Migration Notes

Date: 2026-05-14

## Goal

Preserve the current Cloudflare/web-capable application and begin a reversible desktop runtime migration.

## Rules used for this migration

- do not destroy the stable web path
- do not rotate keys unnecessarily
- keep Cloudflare deployment recoverable
- separate desktop runtime from web deployment concerns
- make rollback branch-based and documented

## Current decision

The project is pivoting to desktop-first execution because:
- local PTY behavior is easier to stabilize
- Docker sandbox behavior is clearer locally
- browser/cloud constraints are too expensive early
- web access can be reintroduced later as a controlled extension

## API/auth audit summary

### Likely web-safe / web-preserved
- Cloudflare worker deployment path
- OpenRouter proxying through current web stack
- OpenAI/Gemini/Hugging Face/Grok provider flows already used by the web app

### Likely to need desktop-specific review later
- Google OAuth redirect URIs if desktop OAuth is added
- any provider login flows relying on hosted redirect URIs
- future auth/sync model for desktop profile/session sharing

### Current migration stance
- preserve existing web keys and flows
- document names, not values
- add desktop env separation later instead of rotating keys now

## Suggested next desktop steps

1. create Electron shell
2. keep `server.mjs` as stable web layer
3. keep `runtime/server.mjs` as local execution layer
4. add secure preload + IPC bridge
5. connect renderer to local runtime on `7331`
6. only later evaluate auth/sync via Cloudflare services
