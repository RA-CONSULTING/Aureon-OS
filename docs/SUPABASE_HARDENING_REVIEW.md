# Aureon Supabase Hardening Review

Current tracked snapshot: 2026-07-12.

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
Hosted production remains blocked until high-risk public Supabase routes are
gated or proven safe by route-level controls.

## Current Boundary

- Supabase functions are defined in `supabase/config.toml`.
- JWT-gated functions still need role checks, payload validation, rate limits,
  and redacted logging before production use.
- Public functions must be anonymous-safe. Mutation, ingestion, credential,
  terminal-state, brain-state, balance, position, and trade-related routes are
  not treated as production-safe merely because they are listed in config.

## Required Production Gates

1. Gate every high-risk public route with JWT or service-role validation.
2. Prove remaining public routes are anonymous-safe.
3. Add role checks for JWT-gated mutation routes.
4. Add payload schema validation for all hosted functions.
5. Define CORS allowlist, rate limits, replay protection, and redacted logging.

## Public Contract

The hardening manifest contains endpoint names, path metadata, auth posture,
risk classes, and required controls only. It does not contain source code,
credentials, customer data, private runtime state, or environment values.
