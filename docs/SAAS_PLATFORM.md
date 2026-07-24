# Aureon SaaS Platform — connected · working · categorized

> The platform layer that turns the 715-module organism into a coherent
> product surface. It **surfaces** the repo — it does not rewrite it. Every
> system is categorized, every domain has a canonical entry point, and health
> is reported **honestly** (degraded where deps are missing, not everything-green).

This is **Phase 6A** of the production program. It builds on the
[Production-Grade Program](runbooks/PRODUCTION_GRADE.md) (the two-tier gate and
serving surface) and the [Aureon Operator Switchboard](architecture/AUREON_OPERATOR_SWITCHBOARD.md)
(the grounded cognition front door), reusing both rather than duplicating them.

---

## The shape of the problem

Three things already existed and only needed connecting:

| Layer | Already present | Role |
|-------|-----------------|------|
| **Tenant / auth / billing** | Supabase backend (`supabase/`) — auth, RBAC, per-user encrypted exchange keys, prepaid "gas-tank" credits, ~101 edge functions, 58 migrations | The multi-tenant foundation. Reused, not rebuilt. |
| **Catalog UI** | React console (`frontend/`, Vite + TS + shadcn) grouped by the 6 product domains | Already a systems console — but **starved of data** (the manifest JSONs it fetches didn't exist). |
| **Categorizer** | `SystemRegistry` (`aureon/command_centers/aureon_system_hub.py`) → 12 capability categories × per-module metadata | The classification engine. |
| **Health surfaces** | `SystemCoordinator.get_coordination_state()`, `get_operational_core().get_health()` | Live status inputs. |

**The gap:** there was no unified Python HTTP gateway producing a categorized
catalog + live status to feed the frontend, and nothing bridging the
single-tenant Python engine to the Supabase tenant layer. `aureon/saas/` is
exactly that bridge.

---

## Three taxonomies, reconciled

The repo describes itself three ways. The catalog maps all three onto each other:

```
6 product domains          24 filesystem domains          12 capability categories
(what the console groups)  (folders under aureon/)        (SystemRegistry semantics)
─────────────────────────  ─────────────────────────      ──────────────────────────
trading            ◄──────  trading, exchanges,      ┐     Exchange Clients
accounting                  scanners, strategies …   │     Market Scanners
research                                              ├──►  Execution Engines
cognition          ◄──────  operator, cognition,     │     Neural Networks
security                    queen, bots_intelligence │     Stargate & Quantum
self-improvement            …                        ┘     Codebreaking & Harmonics · …
```

- **Product domain ← filesystem domain**: `domains._FS_TO_PRODUCT` (unmapped → `self-improvement`).
- **Capability category ← module**: `SystemRegistry` classification, or the
  stdlib keyword classifier (`catalog._CATEGORY_RULES`) when the registry can't load.

---

## Package layout — `aureon/saas/`

| Module | Responsibility | Key entry points |
|--------|----------------|------------------|
| `catalog.py` | **Categorized.** Build the normalized catalog; emit frontend manifests. | `build_catalog()`, `write_frontend_manifests()` |
| `domains.py` | **Connected.** Canonical entry point per domain + cheap reachability probe. | `domain_report()`, `probe_domain()`, `product_domain_for()` |
| `status.py` | **Working.** Honest health rollup, no heavy boot. | `get_platform_status()` |
| `gateway.py` | HTTP surface + optional Supabase tenancy bridge. | `register_saas_routes(app)`, `verify_supabase_jwt()` |

### `catalog.py` — categorized

`build_catalog(workspace=REPO_ROOT)` prefers the repo's `SystemRegistry` (richer
metadata: LOC, dashboard/thought-bus/Queen flags). If the registry can't import
— e.g. `psutil` absent in a lean environment — it falls back to a **self-contained
stdlib scanner** (`_scan_builtin`) that walks `aureon/` and classifies by keyword
rules. **The catalog never collapses to zero categories**; production always
categorizes. Result is cached to `state/aureon_saas_catalog.json` (gitignored).

`write_frontend_manifests()` emits the two JSONs the React console already fetches,
shaped to the frontend's TypeScript interfaces:

- **`aureon_saas_system_inventory.json`** — every system as a *surface* with
  `id · path · name · kind · domain · purpose · owner_subsystem · wiring_status ·
  safety_class · auth_requirement · called_apis`, grouped by product domain.
- **`aureon_organism_runtime_status.json`** — one pulse per product domain
  (status + system_count + categories), live when a status snapshot is passed in.

**Manifest ownership (post-unification):** the checked-in static copies in
`frontend/public/` are owned by the repo's manifest pipeline
(`scripts/validation/generate_*`), which emits a richer schema
(`schema_version`, `entrypoint_status`, `imports/exports`, `runtime_route`, …).
The gateway serves its own live-rendered manifests at `GET /api/manifests/<name>`
and does **not** overwrite the static files unless
`AUREON_WRITE_STATIC_MANIFESTS=1` is set (boot write and
`POST /api/manifests/refresh` both honour this). The console fetches live first
and falls back to the static copies.

### `domains.py` — connected

Each of the 24 filesystem domains gets a canonical entry point in `_ADAPTERS`
(`get_operational_core`, `get_queen`, `run_operator`, `AureonCognition`,
`get_feed_hub`, …). `probe_domain()` checks reachability with
`importlib.util.find_spec` — **an import-spec check, no construction** — so the
report is cheap and side-effect-free. Domains without a clean singleton fall back
to "is the package importable".

### `status.py` — working (honestly)

`get_platform_status()` composes per-domain reachability + the operational core's
own health snapshot + (if present) coordinator state, and rolls reachability up
into per-product-domain status (`ready` / `degraded` / `down`). It carries an
explicit **`note`**: reachability is import-level — a domain can be reachable yet
run degraded (e.g. optional `numpy` missing). Nothing is masked green.

---

## HTTP API

Mounted onto the operator's Flask app by `register_saas_routes(app)`, so **one
service on port 8790** serves operator + cognition + the SaaS catalog behind the
same security envelope (bearer auth / rate-limit / metrics / health from
[PRODUCTION_GRADE.md](runbooks/PRODUCTION_GRADE.md)).

| Method | Route | Returns |
|--------|-------|---------|
| `GET`  | `/api/catalog` | Categorized catalog (12 categories × domains × systems). |
| `GET`  | `/api/domains` | Product domains + per-domain reachability report. |
| `GET`  | `/api/domains/<domain>` | One domain: entry point + its systems (capped). |
| `GET`  | `/api/status` | Live platform health (honest, often degraded). |
| `GET`  | `/api/organism` | Connectome coverage + recent breaths + mesh membership + unification telemetry. |
| `GET`  | `/api/cognition` | The whole cognitive substrate + data provenance + truth roll-up. See [`architecture/COGNITIVE_SAAS.md`](architecture/COGNITIVE_SAAS.md). |
| `GET`  | `/api/cognition/<part>` | One cognitive surface: `field` · `bus` · `mycelium` · `connectome` · `brain`, each provenance-stamped. |
| `GET`  | `/api/consciousness` | The consciousness organs, categorized (self-perception · selfhood · purpose · governance · workforce · body), each with its route, safety posture & live truth_status. See [`architecture/CONSCIOUSNESS_CATALOG.md`](architecture/CONSCIOUSNESS_CATALOG.md). |
| `GET`  | `/api/automation` | Progress toward "the whole repo, fully automated" — one honest % decomposed by dimension (connectivity · integration · consciousness · surfacing) + by category, composed from real coverage only. See [`architecture/AUTOMATION_INDEX.md`](architecture/AUTOMATION_INDEX.md). |
| `GET`  | `/api/manifests/<name>` | A frontend manifest, rendered live (404 lists available names). |
| `POST` | `/api/manifests/refresh` | Rebuild the catalog; static files rewritten only with `AUREON_WRITE_STATIC_MANIFESTS=1`. |

---

## Tenancy bridge (optional, off by default)

The Supabase backend already owns auth/RBAC/billing. The gateway bridges to it
**without a new dependency**: when `AUREON_SUPABASE_JWT_SECRET` is set, the
`/api/*` routes additionally require a valid Supabase JWT, verified with a
stdlib HS256 check (`verify_supabase_jwt` — signature + `exp`). The verified
`sub` (user id) is stashed on `flask.g.tenant` for downstream scoping.

When the secret is **unset the bridge is disabled** (dev/offline unchanged),
layered *on top of* the operator's own bearer/rate-limit envelope — the two are
independent gates.

```
                         ┌─────────────────────────────────────────┐
  React console  ──JWT──►│ operator service :8790                   │
  (Supabase session)     │  ├ security envelope (bearer/rate-limit) │
                         │  ├ [optional] Supabase JWT bridge        │
                         │  ├ operator + cognition routes           │
                         │  └ SaaS routes → catalog/domains/status  │──► the 715-module
                         └─────────────────────────────────────────┘     Python organism
                                                                          (surfaced, not rewritten)
```

---

## Verify

```bash
pip install -e '.[operator,dev]'
ruff check aureon/saas/ && mypy aureon/saas/
AUREON_LLM_OFFLINE=1 pytest tests/test_saas_catalog.py tests/test_saas_gateway.py -q

# catalog + manifests
AUREON_LLM_OFFLINE=1 python -c "from aureon.saas.catalog import build_catalog, write_frontend_manifests; c=build_catalog(); print('categories', c['category_count'], 'systems', c['total_systems']); print('manifests', [p.split('/')[-1] for p in write_frontend_manifests()])"

# gateway routes (offline)
AUREON_LLM_OFFLINE=1 python -c "from aureon.operator.operator_server import create_app; c=create_app().test_client(); print('catalog', c.get('/api/catalog').status_code, 'status', c.get('/api/status').status_code, 'domains', len(c.get('/api/domains').get_json()['domains']))"
```

CI gates on `aureon/saas` in the strict tier (`operator-ci.yml`): ruff-clean +
mypy-clean + `tests/test_saas_*.py` green.

---

## Production deploy (Phase 6B)

One command brings up the whole platform — console + gateway on a single origin:

```bash
# Supabase project values for the console build + server-side JWT verify:
export VITE_SUPABASE_URL=https://<project>.supabase.co
export VITE_SUPABASE_PUBLISHABLE_KEY=<anon key>
export AUREON_SUPABASE_JWT_SECRET=<project JWT secret>

docker compose -f deploy/docker-compose.saas.yml up --build
# → console on :8088 (auth-gated), gateway proxied at /api
```

How the pieces fit:

- **`deploy/frontend.Dockerfile`** — multi-stage: node builds the Vite bundle
  (production defaults baked in: `VITE_REQUIRE_AUTH=1`,
  `VITE_AUREON_MANIFEST_BASE=/api/manifests`), nginx serves it.
- **`deploy/frontend.nginx.conf`** — SPA fallback + `/api` and `/command-stream`
  (WebSocket) proxied to `aureon-operator:8790`. **One origin for the browser**:
  no CORS, no hardcoded backend hosts, health probes pass through.
- **`AuthGate`** (`frontend/src/components/AuthGate.tsx`) — wraps the console.
  A no-op unless `VITE_REQUIRE_AUTH=1`, so dev/local stays open; the production
  build renders the existing `AuthForm` until a Supabase session exists.
- **Live manifests** — the console fetches manifests from
  `VITE_AUREON_MANIFEST_BASE` (`/api/manifests/...`, rendered live by the
  gateway) and falls back to the static `frontend/public` copies automatically.
- **End-to-end tenancy** — the browser's Supabase session token can be verified
  server-side by the gateway (`AUREON_SUPABASE_JWT_SECRET`), closing the loop:
  the same session that opens the console authorizes its API calls.

Dev is unchanged: `npm run dev` in `frontend/` with no env vars = open console,
static manifests, localhost bridges.

---

## Billing (Phase 6C)

**The authority boundary first: the platform never initiates payments.** Metering
is record-only; the single money-moving route ships disabled and is audited.

Three layers, all reusing the wallet that already existed
(`gas_tank_accounts` + `gas_tank_transactions`, the £-denominated performance-fee
tank with its working `gas-tank-topup` edge function):

### 1. Support the project (money in — the user's choice, on their clock)

Aureon runs free. The console tracks cumulative runtime locally and, after ~4
hours of use, shows a **small dismissible corner card** — never a modal, never a
gate — inviting the user to support the project via the SumUp payment links
(`VITE_SUPPORT_PAYMENT_URLS`; defaults are the project's live links). The flow
is **self-confirmed**: the user says what they gave, the existing
`gas-tank-topup` edge function credits their tank, and a `payment_transactions`
row (`provider: sumup`, `status: self_confirmed`) is recorded so payouts can be
reconciled manually against SumUp. Trust-based by design; the admin
`verify-payment` flow remains for disputes.

### 2. Usage metering (record-only — `aureon/saas/metering.py`)

When `AUREON_BILLING_METERING=1`, every `/api/*` request becomes one
`api_request` event (tenant-attributed via the Supabase JWT when present) in a
bounded buffer, flushed by a daemon thread to the `saas_usage_events` table via
PostgREST. Per-provider LLM token usage — parsed by the operator all along but
previously dropped — is swept into `llm_tokens` events and the
`aureon_llm_tokens_total` Prometheus counter. Honesty rules: drop-oldest is
counted, flush failures are counted and dropped, and `GET /api/billing/status`
names the true sink (`disabled` / `prometheus-only` / `supabase`). **Nothing in
this layer debits a balance.** Per-tenant token attribution is staged (fan-out
runs in worker threads; claiming it now would be dishonest).

### 3. Billing API + the fee path's first caller (`aureon/saas/billing.py`)

| Method | Route | Returns |
|--------|-------|---------|
| `GET`  | `/api/billing/status` | Always 200: config, metering stats, token totals, flags. |
| `GET`  | `/api/billing/balance` | The tenant's gas-tank account (503/401/404/502 — precise, never a bare 500). |
| `GET`  | `/api/billing/usage` | The tenant's usage events + buffer stats. |
| `POST` | `/api/billing/charge-fee` | ⚠ **MOVES MONEY — ships OFF.** 403 unless `AUREON_BILLING_CHARGE_ENABLED=1`. |

`charge-fee` is the first-ever caller for the previously dead
`gas-tank-deduct-fee` edge function (the performance-fee math — 20%/10% on
profit above the high-water mark — stays there, single source of truth). It
exists for the server-side trade loop: the profit-realization step POSTs
`{user_id, profit, trade_execution_id}` behind the operator bearer, and every
attempt is audited as a `fee_charge` usage event. No live trader is wired to it
yet — that hookup is a deliberate, separate decision.

### Billing environment

| Var | Default | Effect |
|---|---|---|
| `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` | unset | PostgREST + edge-function access |
| `AUREON_BILLING_METERING` | off | usage-event recording/flushing |
| `AUREON_BILLING_FLUSH_S` / `_BUFFER_MAX` / `_HTTP_TIMEOUT_S` | 10 / 5000 / 5 | tuning |
| `AUREON_BILLING_CHARGE_ENABLED` | **off — moves money** | enables charge-fee |
| `VITE_SUPPORT_PAYMENT_URLS` | the project's SumUp links | support links |
| `VITE_SUPPORT_PROMPT_HOURS` / `VITE_SUPPORT_SNOOZE_HOURS` | 4 / 12 | prompt cadence |

### Hardening notes (recorded, not yet fixed)

- `gas_tank_accounts.fees_paid_today` is never reset by any job.
- `payment_transactions.currency` defaults to `'EUR'` in the schema while every writer sends `'GBP'`.
- Several older tables use permissive `USING(true)` RLS write policies (service-role reliance); `saas_usage_events` deliberately does not.
- `REFUND` / `ADJUSTMENT` transaction types are declared but never produced.
- `aureon_user_sessions.gas_tank_balance` is vestigial — overloaded as "harvested capital", unrelated to the wallet.
- When the operator bearer (`AUREON_OPERATOR_API_KEY`) and the Supabase JWT bridge are both enabled they compete for the same `Authorization` header.

---

## Unified UI Shell (Phase 7)

One professional interface for the entire repo — every capability behind one
sidebar, one router, one design language (the Aureon prism identity, kept by
the creator's choice).

**Architecture: the shell wraps the monolith, it does not rewrite it.**

- **`frontend/src/shell/nav.ts`** — the single source of truth: sections →
  routes → icons → lazy page loaders. The sidebar, router, breadcrumbs, and
  command palette all derive from this table; adding a surface is one entry.
- **`ShellLayout.tsx`** — collapsible grouped sidebar (built on the previously
  unused shadcn `ui/sidebar.tsx` + existing `--sidebar-*` tokens), top bar with
  breadcrumb, live platform-status dot (polls `GET /api/status`), and a
  **⌘K command palette** that jumps to any surface.
- **Routes** (all `React.lazy` — every surface is its own chunk):
  *Trading* war-room · live bridge · Orca · analytics · backtesting —
  *Research & Planetary* Harmonic Nexus · Earth resonance · solar · NOAA space
  weather — *Cognition & LLM* **Operator Chat** (new: talks to
  `/api/cognition/reason`, renders grounding sources, tool calls, and the
  conscience verdict honestly) · agent company — *Coding System* organism ·
  skills · work orders · director bridge — *Operations* gold & capital ·
  systems integration · operational console — *Platform* overview (new) ·
  repo map · billing & support (new) · **legacy console**.
- **The legacy nine-tab console is preserved intact** at `/platform/console`
  (exported as `LegacyConsole` from `App.tsx`); its five entangled tabs
  (live-ops, trading audits, security, inventory, evidence) still work, and old
  `#tab` deep links redirect into the right shell route.
- **Resilience**: every route renders inside a per-route error boundary (a
  crashing dashboard never takes down the shell) with a retry, and live-data
  surfaces carry an honest notice when no backend is connected.
- **Performance**: `vite` manualChunks + route-level lazy loading split the
  former 1,566 kB single bundle into a 227 kB entry + per-surface chunks; the
  oversize-chunk warning is gone.

Verified: production build clean, eslint clean, and an 11-point headless
browser smoke suite (every route renders in the shell, hash redirects work,
palette opens) passes against the built bundle.

---

## Staged ledger

Phases 6A–6C and 7 are done. The remaining SaaS work is tracked, not hidden:

| # | Phase | Item | Done? |
|---|-------|------|-------|
| 6A | Platform layer | Categorized catalog + domain adapters + honest status + gateway routes + Supabase JWT bridge. | ☑ |
| 6B | Production frontend | Frontend Dockerfile + nginx one-origin proxy; auth-gated console (`VITE_REQUIRE_AUTH`); live manifest fetches via `/api/manifests` with static fallback; full-stack compose. | ☑ |
| 6C | Billing | Support-the-project flow (SumUp, self-confirm → gas tank) + record-only usage metering + billing read API + env-gated charge-fee proxy. Staged: per-unit debits, per-tenant token attribution, automated payment capture (SumUp API/Stripe), trade-loop fee hookup, usage panel UI. | ☑ |
| 7 | Unified UI shell | Router + grouped sidebar + command palette over every surface; new Overview/Operator-Chat/Billing pages; legacy console preserved; per-route error boundaries; code-split bundle. Staged: extracting the legacy console's five entangled tabs into shell routes. | ☑ |
| 9 | Organism connectome | The metacognitive layer touches every module (sense/touch/weave/pulse); cognition gains sense/list/touch tools; dormant organs (ConsciousnessModule, HNC live daemon) woken via supervisord; honest wiring instruments; `/api/organism` + Overview card. See [`architecture/ORGANISM_CONNECTOME.md`](architecture/ORGANISM_CONNECTOME.md). Staged: arbitrary-invoke behind the boundary, per-tenant weave policy. | ☑ |
| 10 | Investor-ready repo | Professional README (hero + badges + staged registers), [`COMPANY.md`](../COMPANY.md) with real credentials (Companies House NI696693, Silver Innovate NI cert), root health files + templates, de-cluttered root (binaries/junk/launchers/standalone scripts relocated with history preserved). Secret hygiene: removed a tracked `.env1.txt`. | ☑ |
| 22 | Cognitive Systems SaaS | The cognitive + meta-cognitive substrate (field · bus · mycelium · connectome · brain) as verified read APIs at `/api/cognition*`, each response provenance-stamped (`live`/`real_derived`/`cached_real`/`no_data`, never fabricated); auto-metered + auth-gated; console page at `/cognition/systems`. No cold-boot of heavy organs from a GET. See [`architecture/COGNITIVE_SAAS.md`](architecture/COGNITIVE_SAAS.md). | ☑ |
| 39 | Consciousness catalog | The Phase 25-38 consciousness organs categorized into one honest surface — self-perception · selfhood · purpose · governance · workforce · body — each with its purpose, route, **safety posture** (`read_only_assess` / `records_only_gated` / `reversible_ascent_gated`) and live truth_status. Registry-as-data at `/api/consciousness`; **Consciousness** page at `/cognition/consciousness`. Dormant organ → `no_data`, never fabricated. See [`architecture/CONSCIOUSNESS_CATALOG.md`](architecture/CONSCIOUSNESS_CATALOG.md). | ☑ |
| 41 | Automation progress index | One honest % toward "the whole repo, fully automated", decomposed by dimension (connectivity · integration · consciousness · surfacing, weight-renormalized) + by category, composed from real coverage signals only (clamped; dormant → `index_pct: null` + `no_data`, never inflated). `/api/automation`; headline card on Overview; observational only. See [`architecture/AUTOMATION_INDEX.md`](architecture/AUTOMATION_INDEX.md). | ☑ |
| 57–60 | The Mount | An OpenAI-compatible `POST /v1/chat/completions` front door so any flagship / AGI model mounts by pointing its `base_url` at Aureon — the request runs *through* Aureon as the host mind (grounded + vetted), returning an additive `aureon` provenance envelope; boundary-crossing prompts → `content_filter`, nothing executes. A live self-describing manifest (`GET /v1/integration`) is proven by an integration benchmark (`scripts/run_mount_benchmark.py`, 33/33 critical). Registered as an **active SaaS surface** at `GET /api/mount` (provenance-stamped) with a console page at `/cognition/mount`. See [`architecture/AUREON_MOUNT.md`](architecture/AUREON_MOUNT.md). | ☑ |
| 54 | Feature switchboard | Turn every system feature on/off at human discretion — instance-owned, encrypted flag store (`~/.aureon/feature_flags.json.enc`), applied at daemon boot via `bootstrap_credentials()`. Safe toggles + a hard-boundary tier behind a typed-confirm arming ceremony. Flipping only sets the flag's own env var — no downstream gate (conscience veto / approval queue / runtime dry-run) is ever removed. `/api/switchboard`; **Switchboard** page at `/platform/switchboard`. See [`architecture/FEATURE_SWITCHBOARD.md`](architecture/FEATURE_SWITCHBOARD.md). | ☑ |
| 57 | The Mount | An OpenAI-compatible `POST /v1/chat/completions` front door so any flagship model plugs into Aureon by pointing its `base_url` here — the request runs *through* Aureon as the host mind (a thin translator reusing `AureonCognition.reason` / `AureonOperator.respond`, selected by the `model` field), returning grounded, vetted output with an additive `aureon` provenance envelope (grounding · veto · the stages that ran). A boundary-crossing prompt → `finish_reason: content_filter`; text + a verdict only, nothing executes; `/v1/*` honors the same bearer as `/api/*`. See [`architecture/AUREON_MOUNT.md`](architecture/AUREON_MOUNT.md). | ☑ |

---

## Guardrails

The operator security envelope is reused; the Supabase JWT bridge is **off by
default**; hard authority boundaries (live-trade / payment / credential / filing)
and the `AUREON_LLM_OFFLINE` / `AUREON_AUDIT_MODE` guards stay in force. The 715
modules are surfaced and health-checked, **not** rewritten. Status is honest.
`state/` caches and `frontend/public/` manifests are generated and gitignored.
The Supabase project and its secrets are untouched (read-only bridge).

---

## 📚 Related
- [`runbooks/PRODUCTION_GRADE.md`](runbooks/PRODUCTION_GRADE.md) · [`architecture/AUREON_OPERATOR_SWITCHBOARD.md`](architecture/AUREON_OPERATOR_SWITCHBOARD.md) · [`deployment/OPERATOR_DEPLOY.md`](deployment/OPERATOR_DEPLOY.md)
- [`MODULES_AT_A_GLANCE.md`](MODULES_AT_A_GLANCE.md) — the 24 filesystem domains
- `aureon/saas/` · `.github/workflows/operator-ci.yml`

---

***🌐 The organism, made legible: every system categorized, every domain connected, every status honest.***
