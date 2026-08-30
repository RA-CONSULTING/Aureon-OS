# 🏭 Aureon — Production-Grade Program

How the Aureon software is held to production standard, and the honest, tracked
plan for getting the rest of the tree there.

> **The core decision.** The repo is ~2,500 Python files, much of it intentional
> research/mythopoeic code. A legacy tree that size cannot be certified
> production-correct in one pass, and it would be dishonest to claim otherwise.
> So production grade is a **two-tier program**: a **strict tier** held clean and
> gated in CI, and a **foundation tier** (packaging, serving, containers, CI,
> lint/type *baseline*) that makes the whole repo production-*capable* while the
> rest is hardened on a tracked ledger.

---

## Two tiers

### Strict tier — the product surface `aureon/operator/`
The switchboard + cognition service. Held to:
- **ruff — 0 errors** (`ruff check aureon/operator/`)
- **mypy — 0 errors** (`mypy aureon/operator/`, `check_untyped_defs` + `no_implicit_optional`)
- **tests green** (`tests/test_operator_*.py`, offline)

CI **blocks** on all three (`.github/workflows/operator-ci.yml`).

### Foundation tier — whole repo
- **Packaging** — `pyproject.toml`: installable `aureon` (`pip install -e '.[operator,dev]'`),
  `operator`/`dev` extras, `aureon-operator` entrypoint, one home for tool config.
  Bare-import shims (`conftest.py`, `aureon/_path_setup.py`) kept, so nothing breaks.
- **Python unified on 3.12** (runtime.txt · Dockerfiles · CI).
- **Lint/type baseline (ratchet)** — ruff configured repo-wide; the informational
  CI job `ruff check aureon/ --statistics` records the baseline so it can only
  shrink. `mypy` is gradual (`follow_imports=skip`, `ignore_missing_imports`)
  everywhere except the strict tier.
- **Pre-commit** — ruff (fix) + format on changed files only.

---

## Production serving surface

| Concern | Where | Notes |
|---|---|---|
| WSGI server | `aureon/operator/wsgi.py` → waitress | `main()` serves under waitress; Flask dev server only if `AUREON_OPERATOR_DEV=1` |
| Liveness | `GET /healthz` | up + line-up |
| Readiness | `GET /readyz` | providers + repo index; 503 until usable |
| Metrics | `GET /metrics` | Prometheus exposition of `aureon_operator_*` |
| Config validation | `OperatorConfig.validate()` | fail-fast at boot on bad values |
| Mode | `AUREON_OPERATOR_ENV` | production is fail-closed; development/test must be explicit |
| Auth | `AUREON_OPERATOR_API_KEY` | nonempty bearer required in production; probes stay open |
| Rate limit | `AUREON_OPERATOR_RATE_RPS` / `AUREON_OPERATOR_RATE_BURST` | positive production default → 429 + Retry-After |
| Body cap / errors | `AUREON_OPERATOR_MAX_BODY` | uniform JSON `{error:{code,message}}` |
| Trusted proxy | `AUREON_OPERATOR_TRUSTED_PROXY_CIDRS` | X-Forwarded-For ignored unless the direct peer matches |
| Limiter topology | `AUREON_OPERATOR_HTTP_PROCESSES=1` / `AUREON_OPERATOR_REPLICAS=1` | startup refuses wider production topology while limiter state is process-local |

Guardrails from earlier phases still hold: hard authority boundaries
(live-trade / payment / gate-bypass / credential / filing) are refused
deterministically; `AUREON_LLM_OFFLINE` / `AUREON_AUDIT_MODE` disable all network;
`AUREON_SOVEREIGN_MODE` stays off.

The in-memory bucket is shared by waitress threads inside one process, not by
multiple WSGI processes or replicas. Production therefore fails startup unless
the declared HTTP process and replica counts are both one. Horizontal scaling
requires a shared limiter/cache before either count can be raised.

---

## Build · CI · deploy

- **Container** — `deploy/operator.Dockerfile` (multi-stage, non-root, 3.12,
  waitress, `HEALTHCHECK /healthz`); `deploy/docker-compose.operator.yml`.
- **CI** — `operator-ci.yml` (strict gate + informational ratchet, 3.12);
  `main_ci.yml` bumped to 3.12.
- **Deploy runbook** — [`../deployment/OPERATOR_DEPLOY.md`](../deployment/OPERATOR_DEPLOY.md).

```bash
pip install -e '.[operator,dev]'
ruff check aureon/operator/ && mypy aureon/operator/
AUREON_LLM_OFFLINE=1 pytest tests/test_operator_*.py -q
docker build -t aureon-operator -f deploy/operator.Dockerfile .
```

---

## The ledger — getting the rest of the tree there

Honest, tracked follow-on (not done in the foundation pass). Each item is a
discrete, reviewable unit of work:

| # | Item | Baseline (measured) | Done? |
|---|------|--------------------|-------|
| L1 | Repo-wide **safe** ruff autofix (unused imports, ordering, comprehensions) | ~4,300 auto-fixable | ☐ (separate big diff; import-smoke verified) |
| L2 | Triage `F821` undefined-name (potential real bugs) | 164 | ☐ |
| L3 | Split-statement / style ratchet (`E701`/`E702`) | ~1,150 | ☐ |
| L4 | Expand the **strict tier** domain-by-domain (next: `aureon/core`, then `aureon/queen`) | — | ☐ |
| L5 | Per-domain test coverage as each domain enters the strict tier | — | ☐ |

**Ratchet rule:** the repo-wide ruff count is informational today; once L1–L3 land,
flip the ratchet job to *fail on regression above the recorded baseline* so the
number can only go down. Promote a domain into the strict tier only when it is
ruff-clean, mypy-clean under the strict override, and covered by tests.

---

## 📚 Related
- [`../research/audits/UI_AUDIT_2026-07-14.md`](../research/audits/UI_AUDIT_2026-07-14.md) — the **frontend** two-tier gate (build · shell lint · smoke E2E block; whole-tree typecheck/eslint informational) + the UI honesty pass
- [`../research/audits/SYSTEM_VERIFICATION_2026-07-13.md`](../research/audits/SYSTEM_VERIFICATION_2026-07-13.md) — whole-repo verification sweep (compile · F821 · configs · strict tier · CI honesty)
- [`../SAAS_PLATFORM.md`](../SAAS_PLATFORM.md) — the platform layer (catalog · domains · status) built on this gate
- [`../deployment/OPERATOR_DEPLOY.md`](../deployment/OPERATOR_DEPLOY.md) · [`../architecture/AUREON_OPERATOR_SWITCHBOARD.md`](../architecture/AUREON_OPERATOR_SWITCHBOARD.md)
- `pyproject.toml` · `.github/workflows/operator-ci.yml` · `.pre-commit-config.yaml` · `deploy/operator.Dockerfile`

---

***🏭 The product surface is gated clean today; the rest of the organism is on a ratchet that only tightens.***
