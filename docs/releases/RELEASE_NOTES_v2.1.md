# Aureon OS v2.1 — Production Platform & Investor-Ready

*A product of R&A Consulting and Brokerage Services Ltd, trading as Aureon Zorza Technologies.*

## 🎯 Headline

v2.0 wired the full trading arsenal into the autonomous loop. **v2.1 turns the
repository into a production-grade platform and a professional front door** — a grounded
AI operating layer (the operator + agentic cognition), a metacognitive connectome that
touches every module of the body, a categorized SaaS platform, one unified console over
the whole repo, a two-tier CI gate, and an investor-ready presentation layer — with the
project formally rebranded to **Aureon OS — Harmonic Nexus Core**.

---

## 🔷 New: the grounded AI core

- **Aureon Operator** — a switchboard that routes a prompt through many models, grounds
  it in the repo, reaches consensus, and applies a conscience veto before answering.
- **Agentic cognition** — the operator as an agent: repo-wide grounding, tool use
  (search / read / code / trading-state / organism), with **hard authority boundaries
  enforced before any action** (it never trades, pays, or files autonomously).
- Robustness + observability: retries, circuit-breaker, parallel fan-out, a cache,
  Prometheus metrics, structured logs, and an A/B benchmark.

## 🕸️ New: the organism connectome

- A metacognitive layer that **senses, touches, and weaves every module** (~1,200) of
  the body — legacy code included — into one living system.
- Cognition gains `sense_organism` / `list_organism` / `touch_module` tools; the dormant
  organs (ConsciousnessModule, the HNC Λ(t) live daemon) now breathe in production via
  supervisord; honest three-depth coverage reporting (`linked` ≠ `touched` ≠ `woven`).
- See [`docs/architecture/ORGANISM_CONNECTOME.md`](../architecture/ORGANISM_CONNECTOME.md).

## 🧩 New: the SaaS platform

- A categorized catalog of the whole repo (12 capability categories × 24 filesystem
  domains × 6 product domains), honest per-domain health status, and frontend manifests.
- HTTP gateway (`/api/catalog`, `/api/domains`, `/api/status`, `/api/organism`,
  `/api/billing/*`) behind one security envelope, with an optional Supabase JWT tenancy
  bridge.
- Billing: a support-the-project flow (SumUp, self-confirm → gas tank), record-only usage
  metering, and an env-gated performance-fee proxy. See [`docs/SAAS_PLATFORM.md`](../SAAS_PLATFORM.md).

## 🖥️ New: the unified console

- One professional React interface over the whole repo — collapsible sidebar, ⌘K command
  palette, breadcrumb, live status, and **every dashboard as a lazy-loaded route**.
- The original nine-tab console is preserved; per-route error boundaries; the bundle is
  code-split (1,566 kB → 227 kB entry).

## 🏭 Production hardening

- WSGI serving (waitress), `/healthz` `/readyz` `/metrics`, optional bearer auth +
  token-bucket rate limiting, Docker images + compose, a **two-tier lint/type gate**
  (strict on the product surface, informational ratchet repo-wide), and CI.

## 🔎 Whole-system verification

- Every tracked `.py` compiles on Python 3.11 (4 f-string modules fixed).
- **114 real undefined-name bugs fixed** (silent failures across exchange clients, the
  Queen, and the Orca kill-cycle); 47 remain, all triaged dead/false-positive.
- Configs validated (YAML/TOML/supervisord/nginx/SQL/JSON); the full report is at
  [`docs/research/audits/SYSTEM_VERIFICATION_2026-07-13.md`](../research/audits/SYSTEM_VERIFICATION_2026-07-13.md).

## 💼 Investor-ready & rebrand

- New README (branded hero, honest badges, an architecture diagram, quickstart) and
  [`COMPANY.md`](../../COMPANY.md) with verifiable credentials: Companies House **NI696693**,
  the Minister-awarded **Silver-level Innovate NI** certificate (21 Jul 2025), and the
  Street Soccer NI / Homeless World Cup community sponsorship.
- Root de-cluttered (binaries/launchers/standalone scripts relocated with history
  preserved), root health files + templates added.
- **Rebranded to Aureon OS — Harmonic Nexus Core.**

## 🔐 Security

- Removed a tracked `.env1.txt` that contained live-looking API secrets and gitignored
  it. **Those keys are in git history and must be rotated.**

---

## ✅ Quality at this release

- Strict tier: `ruff` clean · `mypy` clean · **92 tests passing** (offline, no keys).
- Whole package compiles; front-door links resolve; frontend builds.

## ⚠️ Operator notes

- Enable GitHub Actions on the org to turn the live CI badges green (workflows are fixed).
- Rotate the API keys that were previously committed.
- The `saas_usage_events` migration deploys on the next `supabase db push`.

*Nothing in these notes is an offer of securities or a promise of investment returns.
Research claims are pre-registered and falsifiable — see
[`docs/CLAIMS_AND_EVIDENCE.md`](../CLAIMS_AND_EVIDENCE.md).*
