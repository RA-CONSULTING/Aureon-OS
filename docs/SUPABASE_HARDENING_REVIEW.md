# Aureon Supabase Hardening Review

Current tracked snapshot: 2026-07-13.

This review makes the hosted Supabase function boundary explicit for SaaS
integration. The machine-readable manifest is
[`supabase_hardening_manifest.json`](supabase_hardening_manifest.json), mirrored
to
[`../frontend/public/aureon_supabase_hardening_manifest.json`](../frontend/public/aureon_supabase_hardening_manifest.json).

Generate and validate from repo root:

```text
python scripts/validation/generate_supabase_hardening_manifest.py
python scripts/validation/validate_repo_navigation_contract.py
```

## Production Position

The repo is suitable for local-first SaaS integration and public navigation.
As of the 2026-07-13 snapshot, the previously identified high-risk public
Supabase routes are JWT gated in `supabase/config.toml`, so the generated
hardening manifest reports zero public high-risk production blockers.

Hosted production still requires route-level hardening before live use:
JWT-gated mutation and ingestion routes need role checks, payload validation,
rate limits, replay protection where relevant, and redacted logging.

## Current Boundary

- Supabase functions are defined in `supabase/config.toml`.
- JWT-gated functions still need role checks, payload validation, rate limits,
  and redacted logging before production use.
- Public functions must be anonymous-safe. Mutation, credential, terminal-state,
  brain-state, balance, position, and trade-related routes are not treated as
  production-safe merely because they are listed in config.
- The high-risk route set `confirm-trade`, `poll-trade-confirmations`,
  `force-validated-trade`, `test-exchange-connection`, `ingest-trades`,
  `ingest-terminal-state`, and `ingest-brain-state` now requires a valid JWT at
  the Supabase edge before handler execution.

## Required Production Gates

1. Keep high-risk mutation and sensitive-state routes JWT gated.
2. Prove remaining public routes are anonymous-safe.
3. Add role checks for JWT-gated mutation routes.
4. Add payload schema validation for all hosted functions.
5. Define CORS allowlist, rate limits, replay protection, and redacted logging.

## Public Contract

The hardening manifest contains endpoint names, path metadata, auth posture,
risk classes, and required controls only. It does not contain source code,
credentials, customer data, private runtime state, or environment values.
