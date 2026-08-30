# Go-Live Hardening — the network posture of a live Aureon instance

> What is exposed, to whom, and the env vars that change it. The operator is fail-closed in
> AUREON_OPERATOR_ENV=production; permissive local behavior requires an explicit development/test mode.
>
> Companion docs: [`SECURITY_TRADING.md`](SECURITY_TRADING.md) (exchange keys),
> [`PRODUCTION_CHECKLIST.md`](PRODUCTION_CHECKLIST.md) (readiness),
> [`../architecture/MULTI_TENANT_AUTH.md`](../architecture/MULTI_TENANT_AUTH.md) (who may call what).

## The three listeners, and what each serves

A standard deploy ([`../deployment/OPERATOR_DEPLOY.md`](../deployment/OPERATOR_DEPLOY.md)) runs several
processes under one supervisord on one host. They do **not** share an auth story, so treat them
separately:

| Listener | Default port | Auth | Carries |
|:---|:---|:---|:---|
| **Operator / console** (`aureon.operator.operator_server`) | 8790 | full envelope: bearer or Supabase JWT, rate limit, body cap, per-tenant default-deny | everything — keys, reasoning, control plane |
| **Power Station** (`aureon.queen.queen_power_dashboard`) | 8080 | **none by default** (see below) | reserves, deployed capital, live open positions with prices + PnL |
| **Market status server** (`aureon.exchanges.unified_market_status_server`) | 8765 / 8800 | none by default | runtime status, env-credential posture |

The operator is the hardened one. The others were built as local/instance tooling and grew into
long-running services, which is exactly how an internal dashboard ends up on a public interface.

## 1 · The Power Station dashboard (`:8080`) — read this one first

It binds `0.0.0.0` because containerised and DigitalOcean deploys need it (the platform health check
reaches it from outside the container), and it served `/api/status` **with no credential at all**. That
endpoint returns `total_energy`, `total_reserves`, `total_deployed`, `net_energy_gained` and every open
position with symbol, exchange, entry / current / target price and live PnL.

An adversarial audit of the tenancy work reached this port *from the operator host* and read that
payload back. The tenant-side half of that path is closed (a tenant engine no longer has any network
tool — see [`../architecture/MULTI_TENANT_AUTH.md`](../architecture/MULTI_TENANT_AUTH.md)), but the port
itself is still open to anything that can route to it.

| Variable | Effect | Set it when |
|:---|:---|:---|
| `AUREON_DASHBOARD_TOKEN` | `/` and `/api/status` require `Authorization: Bearer <token>`, or `?token=<token>` for a browser navigation. `/health` stays open. | the dashboard is reachable from anywhere but your own machine |
| `AUREON_DASHBOARD_PUBLIC=1` | `/api/status` is served **money-redacted**: cycle, uptime, harmonics, symbols and progress stay; every financial figure is `null` and listed in `redacted`. | **streaming or demoing the dashboard publicly** |
| `AUREON_DASHBOARD_BIND` | interface to bind (default `0.0.0.0`). `127.0.0.1` ⇒ loopback only. | a reverse proxy fronts it, or it is local-only |

`AUREON_DASHBOARD_PUBLIC=1` is the one to reach for when the dashboard is on stream: the organism stays
watchable, the account does not. Redaction is honest — a withheld field is `null` and named, never
replaced with a plausible-looking number.

**On startup the dashboard now says what it is exposing.** Bound to a non-loopback interface with
neither a token nor public mode, it prints a warning naming exactly what `/api/status` is serving. If
you see that warning on a public host, set one of the three variables above.

Recommended for a public deploy:

```bash
AUREON_DASHBOARD_PUBLIC=1          # stream-safe: no reserves, no live position prices
AUREON_DASHBOARD_TOKEN=<random>    # and/or require a credential outright
# or, behind a proxy:
AUREON_DASHBOARD_BIND=127.0.0.1
```

Pinned by [`../../tests/test_dashboard_exposure.py`](../../tests/test_dashboard_exposure.py).

## 2 · The operator / console (`:8790`)

Production startup requires the authenticated, rate-limited envelope. Local and offline development
remain available with AUREON_OPERATOR_ENV=development (or test).

| Variable | Effect |
|:---|:---|
| `AUREON_OPERATOR_ENV` | `production` enables fail-closed startup; use `development` or `test` explicitly for local/offline work. |
| `AUREON_OPERATOR_API_KEY` | nonempty operator bearer; empty or whitespace aborts production startup. |
| `AUREON_SUPABASE_JWT_SECRET` | enables end-user tenancy. Unset ⇒ single-operator, and the per-tenant default-deny never engages. |
| `AUREON_OPERATOR_RATE_RPS` / `AUREON_OPERATOR_RATE_BURST` | token-bucket rate limit; production rate must be positive. |
| `AUREON_OPERATOR_MAX_BODY` | request body cap (default 256 KiB). |
| `AUREON_OPERATOR_TRUSTED_PROXY_CIDRS` | comma-separated exact proxy CIDRs; X-Forwarded-For is ignored when absent or the direct peer does not match. |
| `AUREON_OPERATOR_HTTP_PROCESSES` / `AUREON_OPERATOR_REPLICAS` | both must equal one in production while limiter state is process-local. |
| `VITE_REQUIRE_AUTH=1` | the console requires a Supabase login (build-time) |

Two things worth knowing about the shape of that envelope:

- **Only `/api/*` and `/mcp/*` pass through the gate.** A route mounted at any other prefix is served
  with no credential — verified. The currently-non-gated set is pinned by
  `test_no_route_escapes_the_gate_prefixes`, so adding a prefix breaks CI rather than quietly
  publishing something.
- **Tenant access is default-deny.** A signed-in end user reaches only an explicit allowlist; every
  other `/api` route is operator-only. See the architecture doc for the table.
- **The limiter is process-local.** Waitress threads share it, but multiple WSGI processes or
  replicas do not. Do not scale horizontally until a shared limiter/cache is implemented.

## 3 · The market status server (`:8765` / `:8800`)

Serves `/api/terminal-state`, `/api/flight-test`, `/api/env-credentials` and friends. Inside the
operator app those paths are now operator-only, **but this standalone server has its own listener and
its own (absent) auth**. If it is running on a public host, put it behind a proxy or firewall it — the
operator-side guards do not cover a second process on a different port.

## 4 · Secrets at rest

| Where | Protection |
|:---|:---|
| `~/.aureon/provider_keys.json.enc` | Fernet-encrypted; the key is `~/.aureon/provider_keys.key`, written `0600`. Store files are written `0600` and replaced atomically. |
| `~/.aureon/tenants/<v_\|h_>…/provider_keys.json.enc` | per-tenant, same encryption. One instance-wide Fernet key covers all tenants — per-tenant crypto keys are a documented follow-up. |
| repo-root `.env` | **plaintext** unless `AUREON_HNC_PACKET_MASTER_KEY` is set. This is where `set_exchange_credential` writes exchange keys. Keep it `0600`, keep it gitignored (it is), and never bake it into an image. |
| masked reads | keys are returned last-4 only, never in full, and are not logged. |

## Pre-flight

```bash
# 1 · the strict gate (offline, no keys, no network)
AUREON_LLM_OFFLINE=1 AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS=1 AUREON_AUDIT_MODE=1 \
  pytest tests/test_operator_*.py tests/test_saas_*.py tests/test_dashboard_exposure.py -q

# 2 · prove the whole capability surface end to end
python -m aureon.saas.capability_demo

# 3 · confirm what each listener exposes, from the outside
curl -s localhost:8080/api/status | head -c 400      # token? redacted? or wide open?
curl -s localhost:8790/api/pulse                     # should 401 once the operator key is set
```

Then check the dashboard's startup banner for the exposure warning. If it is absent, `:8080` is either
loopback-only, tokened, or redacted — which is the state you want.
