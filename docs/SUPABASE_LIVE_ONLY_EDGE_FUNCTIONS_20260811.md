# Supabase live-only Edge Function quarantine - 2026-08-11

## Outcome

Local source control now contains an inert quarantine candidate for eleven
production-only Edge Function slugs and a hash-bound evidence archive of the
provider source. This is a local result only.

**Production status: unchanged.** No Edge Function was invoked, deployed,
deleted, or reconfigured. No database row, secret value, DDL, billing action,
or other provider mutation occurred in this phase. Production therefore
remains exposed until a separately authorized deployment is completed and
read back from the provider.

## Evidence boundary

- Project: `siihxcwetdjdsrfdexmb`
- Provider state at capture: all eleven functions were active with
  `verify_jwt=false`.
- Archive: `docs/evidence/supabase/edge-functions/20260811`
- Normalization: LF line endings and one final newline only.
- Verification: every archive SHA-256 matched a fresh read-only provider
  retrieval after the declared normalization.
- Repository caller search before adding this audit material: zero references
  to the eleven slugs.
- The prior operator snapshot showed zero Edge/API events in the last 24 hours.
  That is not proof that no external or dormant caller exists.

The archived source is explicitly **DO NOT DEPLOY**. Only the inert handlers
under `supabase/functions/<slug>/index.ts` belong to the deployment
candidate.

## Disposition

| Function | Provider version | Disposition | Blocking finding |
| --- | ---: | --- | --- |
| `client-portal-api` | 4 | Quarantine | Public service-role project, invoice, and message IDOR plus arbitrary message insert |
| `chronicle-data-manager` | 4 | Quarantine | Public service-role mutations, broken client construction, and undefined handlers |
| `nexus-api-gateway` | 4 | Quarantine pending redesign | Raw key compared to `key_hash`, query-string key accepted, no scopes, and non-atomic limiter |
| `spiritual-data-manager` | 7 | Quarantine | Public service-role PII and biometric CRUD using caller-supplied user IDs |
| `realtime-data-stream` | 4 | Retire candidate | Each public subscriber triggers database writes every two seconds and fabricated values |
| `data-ingestion-pipeline` | 4 | Retire candidate | Public inserts and cleanup delete plus fabricated fallback measurements |
| `backend-health-monitor` | 4 | Retire/rebuild | Public privileged reads/writes and an undefined Supabase client at runtime |
| `distributed-health-monitor` | 4 | Retire candidate | Public registry mutation and mock health/correlation writes |
| `realtime-session-manager` | 4 | Retire/consolidate | Public create/list/delete and a local record presented as a provider session |
| `realtime-sessions-api` | 4 | Retire/consolidate | Duplicate public create/list/delete surface with the same false session boundary |
| `nexus-database-api` | 3 | Quarantine | Generic public service-role read/write facade with caller-supplied user IDs |

## Quarantine contract

Each deploy-tree handler:

- returns deterministic HTTP 410 JSON;
- reads no environment variable or request body;
- performs no database, network, WebSocket, or provider action;
- emits no CORS allow-origin header;
- sends `Cache-Control: no-store` and
  `X-Content-Type-Options: nosniff`.

The eleven `supabase/config.toml` entries explicitly set
`verify_jwt=true`. That platform check rejects missing or invalid user JWTs
before handler execution. It is not sufficient authorization for a retained
service-role handler; this phase removes all privileged handler logic instead.

## Compatibility and rebuild gates

Keep each production slug quarantined for a 30-day observation and
owner-identification window before considering deletion. The clock begins
only after a quarantine deployment has a provider receipt. Unknown external
callers remain a compatibility risk.

If a route is rebuilt:

- Browser routes use a user JWT, derive user and tenant identity from verified
  claims, use the caller auth context so RLS applies, validate an exact origin
  allowlist, and never trust a body-supplied owner ID.
- Initial browser budgets are 16 KiB JSON, 30 reads/minute/user, and
  10 writes/minute/user. Biometric input may use 64 KiB only after a concrete
  schema proves it necessary. Session creation starts at 5/minute/user.
- Machine ingestion and health routes expose no browser CORS. They require a
  dedicated timestamp, nonce, and body-hash signature before any service-role
  client is constructed. Initial health budget is 16 KiB and 12/minute/server;
  ingestion is contract-specific, capped at 256 KiB and 1-60/minute/caller.
- `nexus-api-gateway` requires a separate v2 design: header key only, key ID
  plus keyed hash and constant-time verification, scopes and tenant filters,
  atomic database rate limiting, GET-only reads, page size at most 100, and
  redacted logs. The initial ceiling is 60/minute/key.
- `realtime-data-stream` is not repaired in place. Use one authenticated,
  scheduled, receipt-bearing data producer and read-only Supabase Realtime.
  A subscriber must never generate or write measurements.
- Oversized bodies are rejected while streaming; `Content-Length` alone is
  not trusted.

Current Supabase references used for the design:

- https://supabase.com/docs/guides/functions/auth-headers
- https://supabase.com/docs/guides/functions/auth-legacy-jwt
- https://supabase.com/docs/guides/functions/websockets
- https://supabase.com/docs/guides/functions/cors
