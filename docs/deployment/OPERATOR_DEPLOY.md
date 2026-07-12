# 🎛️ Aureon Operator / Cognition — Deploy Runbook

How to run the Aureon Operator + Cognition service in production: the switchboard,
the agentic cognition (repo-wide grounding + tools + veto), and the mobile
proof-of-concept page — with real flagship models, and reachable from a phone.

See also: [`docs/architecture/AUREON_OPERATOR_SWITCHBOARD.md`](../architecture/AUREON_OPERATOR_SWITCHBOARD.md)
· [`docs/runbooks/PRODUCTION_GRADE.md`](../runbooks/PRODUCTION_GRADE.md) (the production-grade program: two-tier gate, serving surface, CI/Docker, ledger).

---

## What runs

One process — `python -m aureon.operator.operator_server` — serves:

| Route | Purpose |
|---|---|
| `GET /` | mobile-responsive chat page (switchboard + 🧠 cognition toggle) |
| `GET /healthz` | liveness + active model line-up |
| `GET /api/operator/stream` · `POST /api/operator/respond` | switchboard (fan-out → consensus → veto) |
| `GET /api/cognition/stream` · `POST /api/cognition/reason` | agentic cognition (grounding + tools + veto) |

On startup it builds the cognition with `join_mesh=True`, so the service
registers on the **mycelium mesh** and the **Queen hive** as it boots.

---

## Environment

```bash
# Model lines — set the ones you have; absent keys are skipped, and with none set
# the service runs offline on stub/local adapters (never hangs on the network).
OPENAI_API_KEY=sk-...        # ChatGPT lines  (https://api.openai.com/v1)
XAI_API_KEY=xai-...          # Grok lines     (https://api.x.ai/v1)
GEMINI_API_KEY=...           # Gemini lines   (generativelanguage v1beta)
ANTHROPIC_API_KEY=...        # optional Claude line
AUREON_LLM_BASE_URL=...      # optional self-hosted OpenAI-compatible model (Ollama/vLLM)

# Service
AUREON_OPERATOR_PORT=8790    # default; keep distinct from the 8080 Power Station
AUREON_OPERATOR_HOST=0.0.0.0

# Safety / mode guards (any truthy value disables outbound model + web calls)
AUREON_LLM_OFFLINE=1         # hard offline
AUREON_AUDIT_MODE=1          # audit — network off unless AUREON_LLM_ALLOW_HTTP_IN_AUDIT
# AUREON_SOVEREIGN_MODE stays UNSET — it would relax tool denylists; leave off.
```

Adapters are verified by `tests/test_operator_production.py::test_flagship_adapter_key_paths`
(right base URL + `Bearer` auth for OpenAI/Grok, key-in-URL for Gemini, OpenAI `/v1`
path — not the Ollama native path). Any flagship model, or several, plug in as a
registry row (`aureon/operator/config.py` `DEFAULT_REGISTRY`); keyless rows are
skipped at assembly.

---

## Run it

```bash
# local / dev
AUREON_OPERATOR_PORT=8790 python -m aureon.operator.operator_server

# under supervisord — already wired as [program:aureon_operator] (priority 50)
supervisorctl start aureon_operator          # supervisord.conf (Codespaces paths)
supervisorctl start aureon-operator          # production/supervisord.conf (/aureon/app)
```

Both supervisord files ship the program block; it autostarts and autorestarts on
priority 50 (after the trading loops), logging to `logs/aureon_operator.log`.

---

## DigitalOcean (current stack)

The repo's live stack is DigitalOcean (see
[`DIGITALOCEAN_DEPLOYMENT.md`](DIGITALOCEAN_DEPLOYMENT.md),
[`DIGITAL_OCEAN_MASTER_GUIDE.md`](DIGITAL_OCEAN_MASTER_GUIDE.md)). To expose the
operator:

- **App Platform:** add an HTTP route / component for port **8790**, or place it
  behind the existing ingress and route `/api/operator`, `/api/cognition`, and `/`
  to it. Health check: `GET /healthz`.
- **Droplet:** it starts with the rest via `production/supervisord.conf`. Front it
  with the existing nginx/Caddy over HTTPS; proxy `:8790`.
- Region London (`lon`), Ubuntu 24.04 — unchanged from the current guides.

## IONOS (alternative target)

IONOS is **net-new** to this repo. Mirror the DigitalOcean conventions: a small
cloud VM, `supervisord` with the same priority order, ports 8080 (Power Station)
and **8790** (operator), state JSONs at the repo root (do not move — see
[`../STATE_FILES.md`](../STATE_FILES.md)). The service is a thin front door; the
data centre is the black box behind it.

---

## Reaching it from a phone

The container's `localhost` is not the phone's `localhost`. Use one of:

1. **Deployed HTTPS URL** — the DigitalOcean/IONOS domain routing to `:8790`
   (e.g. `https://operator.yourdomain.com`). Open it on the phone; the SSE stream
   and cognition toggle work over HTTPS.
2. **Tunnel** (dev) — `cloudflared tunnel --url http://localhost:8790` (or
   ngrok / tailscale), then open the tunnel URL on the phone.

SSE needs an un-buffered proxy: the service already sends
`Cache-Control: no-cache` and `X-Accel-Buffering: no`; ensure nginx has
`proxy_buffering off;` on the `/api/*/stream` locations.

---

## Guardrails (always on)

- Hard authority boundary — **live trade / payment / gate-bypass / credential /
  filing** — refused deterministically, before any model or tool runs, at every
  autonomy level.
- Consequential tools (file write/patch, shell) pass path/secret/syntax and
  boundary guards before executing; `AUREON_SOVEREIGN_MODE` stays off.
- `AUREON_LLM_OFFLINE` / `AUREON_AUDIT_MODE` disable all outbound model + web calls.

---

## Verify a deployment

```bash
curl -s http://HOST:8790/healthz                                   # {"ok":true, providers:[...]}
curl -s -X POST http://HOST:8790/api/cognition/reason \
     -H 'Content-Type: application/json' \
     -d '{"prompt":"How does Aureon ground its answers?"}'          # grounded + cited
curl -N "http://HOST:8790/api/cognition/stream?prompt=hello"        # live SSE tokens
```

---

***🎛️ One thin front door. Any flagship model behind it. Grounded, gated, and reachable from your pocket.***
