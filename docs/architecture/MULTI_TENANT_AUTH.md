# Multi-Tenant Auth & Per-Tenant Keys

> Increment 1 toward a live, production-ready state where a real end user can log in and use Aureon OS
> with **their own** keys — safely isolated from every other user, and from the single-operator default.

## The three identities

Every request to `/api/*` (and `/mcp/*`) is resolved to exactly one identity by
[`aureon/operator/identity.py`](../../aureon/operator/identity.py) `resolve_identity()`, which the
operator gate ([`operator_server.py`](../../aureon/operator/operator_server.py) `_gate`) evaluates once
per request and stashes on `g.tenant` / `g.is_admin`:

| Identity | How | `g.tenant` | Plane |
|:---|:---|:---:|:---|
| **open** | neither secret configured | `None` | single-operator (dev / offline) — **unchanged** |
| **admin** | static `AUREON_OPERATOR_API_KEY` bearer | `None` | the instance control plane (global keystore, `os.environ`) |
| **tenant** | a valid Supabase HS256 JWT | JWT `sub` | that user's **isolated** plane |

**Zero-regression invariant.** When `AUREON_SUPABASE_JWT_SECRET` is unset, the tenant branch is never
reached — the gate behaves byte-for-byte like the old static-key `check_bearer`: open when no key is set,
bearer-required when it is. Turning tenancy on is purely additive.

### What the token verifier accepts

`verify_supabase_jwt` **forces HS256** and never reads `alg` from the token header, so the classic
algorithm-confusion attacks (`alg: none`, or an RS256 header verified with a public key as the HMAC
secret) cannot apply — probed directly, both are refused. On top of the signature it requires:

| Check | Why |
|:---|:---|
| `exp` **required**, not just honored-if-present | A signed token with no expiry never expires and cannot be revoked. Supabase always sets it; the gate refuses to *depend* on that. |
| `nbf` honored when present | A not-yet-valid token is not accepted early (60 s clock-skew leeway). |
| `role` not `anon` / `service_role` | Supabase signs its **project API keys** with the same secret, and the anon key is a *public, client-side* value. |
| `sub` must be a non-empty `str` | A non-string `sub` (int, dict, null) never becomes a tenant id. |

Pinned by `test_jwt_verifier_rejects_dangerous_tokens` in
[`tests/test_operator_tenant_security.py`](../../tests/test_operator_tenant_security.py).

## Per-tenant key isolation

Provider / connection keys live in [`aureon/operator/keystore.py`](../../aureon/operator/keystore.py),
Fernet-encrypted. Every function takes an optional `tenant`:

- `tenant=None` → the global store `~/.aureon/provider_keys.json.enc` (admin / single-operator) — unchanged.
- a tenant → an **isolated file** `~/.aureon/tenants/<tenant>/provider_keys.json.enc`. The `<tenant>`
  segment is sanitized (`_safe_tenant`: strict whitelist, else SHA-256 hash) so a crafted `sub` can never
  escape the tenants directory.

One tenant can never read, test, or apply another's keys; a tenant view never merges the instance
`os.environ` keys (so admin secrets are never shown to a user).

### The one invariant that prevents a leak

`apply_to_env()` injects keys into the **shared process `os.environ`**. That is fine for the single
global operator, but it is the *only* way one user's key could bleed into another user's reasoning. So:

> **A tenant write NEVER calls `apply_to_env()` / `_rebuild_switchboard()` and NEVER mutates
> `os.environ` or the shared `_operator.providers`.** ([`operator_server.py`](../../aureon/operator/operator_server.py)
> forks every `providers_*` / `connections_*` route on `g.tenant` exactly here.)

This is enforced and regression-tested in
[`tests/test_operator_tenant_keys.py`](../../tests/test_operator_tenant_keys.py)
(`test_tenant_write_never_mutates_os_environ`).

## Frontend

[`frontend/src/services/apiClient.ts`](../../frontend/src/services/apiClient.ts) now attaches the
end-user session bearer to every `/api/*` call via an injectable `authTokenProvider`, wired once in
[`main.tsx`](../../frontend/src/main.tsx) to `supabase.auth.getSession()`. No session ⇒ no header ⇒
unchanged. The capability pages (Operator Chat, Providers, Connections) route through `apiClient`, so the
tenant token flows to the backend.

## What ships now vs. what's next (honest)

**Ships:** end-user identity end-to-end; each user's keys **stored, managed, and live-tested** in full
isolation; the single-operator default unchanged; and **per-user live reasoning** — a signed-in user's
own model drives their own `/api/cognition/reason` and `/api/operator/respond`.

## The two planes: default-deny, enforced once in the gate

**A tenant may reach only what is explicitly allowlisted.** The mechanism is a table —
`_TENANT_OWN_PLANE | _TENANT_SHOWCASE` in
[`operator_server.py`](../../aureon/operator/operator_server.py) — checked once in `_gate` against
`request.url_rule.rule` (the *pattern*, so a crafted id cannot be read as another route). Anything
absent returns `403` to a tenant. Admin and open planes skip the check entirely, which is what keeps
the single-operator default byte-for-byte unchanged.

| Tenant may reach | What it covers |
|:---|:---|
| **Own plane** | `/api/providers*`, `/api/connections*` (their keys), `/api/cognition/reason`, `/api/operator/respond` + both streams (their reasoning), `/api/billing/balance\|usage\|status` (their billing), `/api/notifications/telegram` — *the view is stricter than the table here: a tenant may send only with their own `botToken`* |
| **Public showcase** | the read-only organism views already public via `/watch` and the Twitch stream: `/api/organism`, `/api/soul`, `/api/consciousness`, `/api/company`, `/api/org`, `/api/affect`, `/api/pursuit`, `/api/inner-work`, `/api/metacognition`, `/api/automation`, `/api/cognition*` (HNC), `/api/catalog`, `/api/domains*`, `/api/coverage`, `/api/defense` |

Everything else is operator-only **by omission** — including `/api/terminal-state`, `/api/flight-test`,
`/api/reboot-advice`, `/api/env-credentials`, `/api/switchboard*`, `/api/approvals*`, `/api/action*`,
`/api/pulse`, `/api/manifests/*`, `/api/billing/charge-fee`, `/mcp/*`, `/api/status`, `/api/trades`,
`/api/bots`.

### Why enumeration was abandoned

Per-route guarding failed **three audits running, always the same way**: the write sibling got a guard
and the read sibling kept serving.

| Round | Found |
|:---|:---|
| 1 | unguarded `POST` routes (switchboard, action, approvals, manifests, telegram) |
| 2 | fixed those — and `POST /api/billing/charge-fee`, `/mcp/*`, `/api/env-credentials`, plus a tenant toolbelt that was a denylist |
| 3 | the matching **GETs**: `/api/terminal-state` (instance equity, exchange account id, open positions, PnL), `/api/flight-test` + `/api/reboot-advice` (the `.env` path and *which* exchange keys were written — the very disclosure round 2 had just closed on `/api/env-credentials`), `/api/approvals`, `/api/switchboard`, `/api/pulse`, `/api/action/status` |

The cause is structural, not carelessness: the ~64 rules are mounted by **five different registrars**
(`operator_server`, `saas/gateway`, `legacy_runtime_api`, `connections_api`,
`autonomous/aureon_face_app`), so no file lists them and no reviewer sees them all. The gate *does* see
them all — so the decision belongs there. With default-deny the failure mode inverts: a new route is
closed to tenants by construction, and the worst outcome is "a tenant feature 403s until it is added to
the table", which is loud and safe.

Existing per-view `_admin_denied()` / `@_admin_only` calls are kept as defense-in-depth.

### What the tests pin

[`tests/test_operator_tenant_security.py`](../../tests/test_operator_tenant_security.py):
every found route `403`s a tenant **and** still answers the operator (invariant 1 — round 2 shipped a
guard that locked the operator out of their own approvals desk, and that assertion is what catches it);
every allowlisted route stays reachable, so default-deny does not dark the console;
`test_every_route_is_classified` walks the real `url_map` and admits no third state between
allowlisted and refused, so the gate cannot silently stop enforcing; and
`test_no_route_escapes_the_gate_prefixes` pins the set of routes outside `/api/` and `/mcp/` — those
are served **unauthenticated**, verified, so adding one has to be a conscious decision.

### Accepted, with the reason

The grounding step (`_ground`, [`cognition.py`](../../aureon/operator/cognition.py)) runs
`repo_search(prompt)` and splices snippets into the system prompt sent to the tenant's *own*
`base_url`. That is left as-is: `repo_index._EXCLUDE` drops `state/` and `_INGEST` is only
`.md/.py/.txt/.pdf`, so what travels is **already-public MIT source from a public GitHub repo**, not
instance secrets. Worth knowing; not worth breaking Aureon-specific grounding over.

### What the counter-audit found (round 2)

The round-1 patches were then attacked in turn, and several fell. Recording them because the
*shape* of each mistake is the reusable lesson:

- **A denylist is not a lockdown.** `build_operator_tools(allow_writes=False, allow_shell=False)`
  removed 3 of 17 tools. The 14 that remained were themselves the exploit: `web_fetch` (arbitrary
  outbound HTTP *from the operator's host* — SSRF onto co-located instance services and cloud
  metadata, plus an unattributed egress relay), `touch_module` (import any module), `publish_thought`
  (writes the process-global thought bus, going straight around `_IsolatedBus`), `read_state` /
  `read_positions` / `read_prices` (the instance's live trading state), and `repo_search` /
  `read_repo_file` / `list_repo` (repository contents). The belt is now an **allowlist**
  ([`TENANT_ALLOWED_TOOLS`](../../aureon/operator/tools.py)) applied as a *final filter*, so a
  built-in added upstream can never silently widen the tenant surface.
- **The enumeration missed the one route that moves money.** `charge-fee`'s own docstring called it
  "operator-authenticated"; the env gate and the audit trail existed, the authentication did not.
- **A guard on the LLM half is not a guard on the whole surface.** `/api/connections` and
  `/api/connections/readiness` still built their exchange / data-source rows from the *global*
  keystore plus `os.environ` — exactly where the real money keys are.
- **Guards can lock out the operator too.** Stacking `@_guarded` (which requires a valid *Supabase
  JWT*) over `@_admin_only` meant the admin static bearer — not a JWT — got `401` before the admin
  check ran, so **no** identity could decide an approval. Fixed by having `_tenant_ok` accept an
  identity the operator gate already authenticated.
- **Two namespaces sharing one directory space collide.** `_safe_tenant` used a whitelisted `sub`
  verbatim and hashed the rest — but a SHA-256 digest itself satisfies the whitelist, so a tenant
  could be handed another tenant's store. The forms are now prefixed `v_` / `h_`, provably disjoint.
- **Detaching a bus after construction is too late.** `QueenConscience.__init__` subscribes before
  `_thought_bus = None` runs, leaving the tenant-plane conscience fed by the instance's substrate
  pulses. It is now explicitly unsubscribed.
- **`join_mesh=False` only governed inbound membership.** The outbound `broadcast_to_mesh` calls
  fired regardless, carrying the conscience verdict (which quotes the user's prompt). Outbound is now
  its own flag, `mesh_broadcast`, default `True` so the instance engine is unchanged.

### Per-user live reasoning

When a request carries a tenant, `operator_server` builds a **request-scoped engine from that tenant's
keystore** via [`providers.build_provider_set_from_entries()`](../../aureon/operator/providers.py) (which
reads explicit keys and never touches `os.environ`), and caches it per tenant in a **bounded LRU** (max 8).
Three properties keep it safe and leak-free:

- **Allowlisted toolbelt — a hard boundary.** A tenant supplies their own `base_url`, so the model
  answering their turn is a server **they** control, and whatever `tool_calls` it returns get dispatched
  on the operator host. The conscience veto runs *after* the tool loop, so it cannot undo a side effect.
  Therefore a tenant engine is built with `allowlist=TENANT_ALLOWED_TOOLS` — pure-compute tools only
  (`code_validate`: `ast.parse`, no I/O, no network, no shared state). No shell, no repo write, and
  equally no network egress, no module import, no bus write, and no instance-state read. The filter is
  applied *last*, so nothing registered upstream can widen it. And the plumbing must **fail closed**:
  `ToolRegistry` defines `__len__`, so a registry pruned to zero is *falsy* and the old
  `self.tools = tools or build_operator_tools(...)` would have silently restored the **full** belt —
  now an explicit `is not None` check in both `cognition.py` and `agent_runner.py`.
- **One model response cannot exhaust the host.** Tool calls arrive in the *model's* response, so the
  256 KB request cap never applied to them. `agent_runner` bounds the calls per response and each
  argument's size, refusing over-cap ones as ordinary blocked tool results.
- **Isolated bus** — per-tenant engines get an `_IsolatedBus`: `subscribe` is a no-op (so cached engines
  can't accumulate organism callbacks) *and* `publish`/`recall` are no-ops, so a tenant's prompt and
  answer never land in the shared instance thought bus. `join_mesh=False` keeps them off the mesh
  inbound, and `mesh_broadcast=False` keeps their turns from radiating outward onto it.
- **Tenant-plane conscience** — the ethical gate always runs, but the Queen publishes each verdict
  (quoting the action, i.e. the user's prompt). So the tenant plane uses its own conscience instance with
  `_thought_bus` detached: identical judgement, nothing written into shared instance memory.
- **Honest keyless reply** — a signed-in user with no model of their own gets a clear "add a key" response
  on **every** entrypoint — `reason`, `respond`, and both SSE streams — **never** the instance's models
  (that would spend the operator's keys on a stranger). The same rule governs `*/test` probes: a tenant
  with no stored key gets an honest verdict rather than an empty key, which the adapters would otherwise
  resolve from the process env.
- **Revocation takes effect at once** — every tenant credential write/delete drops that tenant's cached
  engines, so a rotated or revoked key stops being spent on the next request.

The admin/open plane (`g.tenant is None`) still uses the shared instance engine, byte-for-byte as before.

**Deferred (follow-ups):** per-tenant crypto keys; SSE stream tenancy (`EventSource` cannot carry an
Authorization header, so `/api/*/stream` stays on the admin/global plane — the console chat uses POST,
which is covered); migrating the sign-up Binance-key capture off Supabase onto the tenant keystore.

## Configure

| Variable | Effect |
|:---|:---|
| `AUREON_SUPABASE_JWT_SECRET` | **On/off switch** for tenancy. Unset ⇒ single-operator, unchanged. |
| `AUREON_OPERATOR_API_KEY` | The admin/operator static bearer (control plane). |
| `VITE_REQUIRE_AUTH=1` | Frontend: require a Supabase login to reach the console (build-time). |
| `VITE_SUPABASE_*` / `SUPABASE_*` | Supabase project URL + keys (see `docs/SAAS_INTEGRATION_READINESS.md`). |

## Reproduce the isolation proof

```bash
AUREON_LLM_OFFLINE=1 AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS=1 \
  pytest tests/test_operator_tenant_keys.py -q
```

Asserts: tenant B can't see tenant A's key · a tenant write leaves `os.environ` untouched · admin uses the
global store · a tenant can live-test their own key · the identity matrix · open-mode backward-compat.
