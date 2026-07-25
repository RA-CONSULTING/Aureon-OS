# AGENTS.md — how any AI coding agent runs & integrates Aureon

> Vendor-neutral onboarding for a flagship coding agent (Codex, Cursor, Gemini,
> Claude Code, …) that a user hands this repo to. If you are **Claude**, also read
> [`CLAUDE.md`](CLAUDE.md) for the theory/voice guide. This file is the **run &
> integrate** guide — read it first, then act.

---

## What this repo is (10 seconds)

**Aureon** is a grounded AI operating layer (the **Harmonic Nexus Core**). Its
integration surface is the **Aureon Mount**: an **OpenAI-compatible front door** so
any model client mounts on Aureon by pointing its `base_url` here. Every request
runs *through* Aureon as the **host mind** — grounded in the repo, vetted by a
conscience — and only the grounded, vetted answer comes back. Human-in-the-loop;
**no autonomous action on sensitive tasks** (trading / payments / filing).

Deep dive: [`docs/architecture/AUREON_MOUNT.md`](docs/architecture/AUREON_MOUNT.md).

---

## Mount it in 60 seconds

```bash
# 1 · install the operator (offline-safe — runs with zero API keys)
pip install -e '.[operator]'

# 2 · run the gateway (binds 0.0.0.0:8790)
python -m aureon.operator.operator_server          # or the console script: aureon-operator

# 3 · mount any OpenAI client — just swap the base_url
curl -s http://localhost:8790/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"aureon-cognition","messages":[{"role":"user","content":"How does Aureon ground its answers?"}]}'
```

The reply is a standard OpenAI `chat.completion` with an **additive `aureon`**
block (grounding sources, conscience verdict, the pipeline stages that ran). Set
`AUREON_OPERATOR_API_KEY` to require `Authorization: Bearer <key>` on `/v1` and
`/api`. Requests that cross a hard boundary return `finish_reason:"content_filter"`
— text + a verdict only, nothing executes.

### The OpenAI SDK, unchanged except the base_url

```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:8790/v1", api_key="unused-or-your-key")
r = client.chat.completions.create(
    model="aureon-cognition",              # or "aureon-switchboard"
    messages=[{"role": "user", "content": "Summarize the Aureon operator."}],
)
print(r.choices[0].message.content)         # grounded, vetted
```

---

## Or add Aureon as an MCP server (no base_url swap)

Prefer connectors over an OpenAI base_url? Aureon is also a **Model Context Protocol**
server exposing three tools — `aureon_reason`, `aureon_switchboard`, `aureon_integration`
— each grounded + vetted.

- **Local (desktop/IDE):** register the `aureon-mcp` stdio command, e.g. Claude Desktop
  `claude_desktop_config.json`:
  ```json
  { "mcpServers": { "aureon": { "command": "aureon-mcp" } } }
  ```
- **Hosted (cloud):** add the URL `http://<host>:8790/mcp` (JSON-RPC 2.0 over HTTP;
  same bearer as `/api` and `/v1`).

Details: the `mcp` block in [`.well-known/aureon-mount.json`](.well-known/aureon-mount.json)
and [`docs/architecture/AUREON_MOUNT.md`](docs/architecture/AUREON_MOUNT.md).

## Discover the contract without running anything

- **Static (cloned, not yet running):** read
  [`.well-known/aureon-mount.json`](.well-known/aureon-mount.json) — a committed
  snapshot of the integration manifest (engines, endpoint, provenance keys, auth,
  how to mount). Regenerate with `python -m scripts.gen_mount_descriptor`.
- **Live (server running):** `GET /v1/integration` · `GET /.well-known/aureon-mount.json`
  · `GET /api/mount` (same-origin, provenance-stamped — the console reads this one).
- **Models:** `GET /v1/models` → `aureon-cognition` (default, single grounded mind)
  and `aureon-switchboard` (many models → consensus).

---

## Verify (one command, offline, no keys/network)

```bash
# drive real OpenAI-shaped probes through the live mount; exits non-zero on failure
AUREON_LLM_OFFLINE=1 python -m scripts.run_mount_benchmark

# the focused test suites
AUREON_LLM_OFFLINE=1 pytest tests/test_operator_mount.py tests/test_mount_benchmark.py tests/test_saas_gateway.py -q
```

---

## Ground rules if you edit this repo

- **Strict tier stays green:** `ruff check aureon/operator/ aureon/saas/` and
  `mypy aureon/operator/ aureon/saas/` must pass; the operator/mount code is typed.
- **Don't weaken the boundary.** The mount returns text + a verdict; it never
  trades, pays, or files. `_hard_boundary_violation` + the conscience veto are
  load-bearing — never remove or bypass them.
- **Keep the descriptor honest.** If you change `integration_manifest()`, re-run
  `python -m scripts.gen_mount_descriptor` (a test fails on drift).
- **Offline-first.** Everything above runs with `AUREON_LLM_OFFLINE=1` and no keys;
  add provider keys (see `docs/architecture/AUREON_MOUNT.md`) to go live.

---

## Where to look next

| You want… | Read |
|---|---|
| The full mount contract | [`docs/architecture/AUREON_MOUNT.md`](docs/architecture/AUREON_MOUNT.md) |
| The two grounding engines | [`docs/architecture/AUREON_OPERATOR_SWITCHBOARD.md`](docs/architecture/AUREON_OPERATOR_SWITCHBOARD.md) |
| Run/deploy the operator | [`docs/deployment/OPERATOR_DEPLOY.md`](docs/deployment/OPERATOR_DEPLOY.md) |
| The theory / repo orientation | [`CLAUDE.md`](CLAUDE.md) → [`docs/THE_SYNTHESIS.md`](docs/THE_SYNTHESIS.md) |
| The SaaS platform + console | [`docs/SAAS_PLATFORM.md`](docs/SAAS_PLATFORM.md) |
