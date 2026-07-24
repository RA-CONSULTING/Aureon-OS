# 🔌 THE AUREON MOUNT

## "Any model above. One grounded mind below."

> *"That which is below is like that which is above."* — the Emerald Tablet.
>
> The switchboard makes many models speak *through* the one repository. The
> **mount** turns that inward: it lets **any flagship model plug into Aureon and
> use it the way the creator does** — as the host mind that grounds and vets
> every answer before it leaves.

---

## 🌌 What it is

The **mount** is the formal front door. It speaks the one protocol every model
client, SDK, and tool already knows — **`POST /v1/chat/completions`** — so an
external flagship model mounts onto Aureon by pointing its `base_url` here and
changing *nothing else*.

But the request is **never a raw passthrough**. It runs *through* Aureon as the
**host mind**:

```
[ flagship model ]                                         [ flagship model ]
       │  forward prompt + context                                ▲
       ▼                                                          │ grounded + vetted output
┌──────────────────────────────────────────────────────────────────────┐
│  AUREON OPERATOR  (the host mind — POST /v1/chat/completions)          │
│    ground (repo-wide)  →  agentic cognition / switchboard consensus    │
│                        →  connectome + HNC π(t)  →  conscience veto     │
└──────────────────────────────────────────────────────────────────────┘
```

Only the grounded, vetted answer falls out the far side. A request that crosses a
hard authority boundary comes back **`content_filter`-blocked**, and **nothing
executes** — the mount returns *text and a verdict only*. The human (Prime
Sentinel) stays in the loop; there is **no autonomous action on sensitive tasks**.

This is the exact pattern from *How an External AI Model Uses Aureon OS the Way
the Creator Does* — made a formal, first-class route.

---

## 🎛️ The engine selector — `model`

The `model` field chooses which Aureon engine grounds the request. Either way,
the answer that comes back is Aureon's grounded, vetted output.

| `model` | Engine | What runs |
|---|---|---|
| `aureon-cognition` *(default)* | single grounded mind | ground → agentic tool-loop → connectome/HNC → conscience veto |
| `aureon-switchboard` | many models | ground → fan-out across every line → consensus collapse → conscience veto |
| anything else (`gpt-4o`, `claude-3`, …) | falls back to `aureon-cognition` | so an unknown id still goes *through* Aureon rather than being rejected |

`GET /v1/models` advertises the two Aureon engines.

---

## 📡 The contract

### `POST /v1/chat/completions`

**Request** — the standard OpenAI chat body:

```json
{
  "model": "aureon-cognition",
  "messages": [
    {"role": "system", "content": "Be concise."},
    {"role": "user", "content": "How does Aureon ground its answers?"}
  ],
  "stream": false
}
```

- `system` turns become grounding **context**; the **last** `user` turn is the
  **prompt**; earlier user/assistant turns fold into the context as prior
  conversation. `content` may be a plain string or the content-part list
  (`[{"type": "text", "text": …}]`) — non-text parts are ignored honestly.
- `user` (or `session_id`) is carried through as the Aureon session id.

**Response** — a standard `chat.completion`, with an **additive `aureon`**
provenance envelope:

```json
{
  "id": "chatcmpl-<trace_id>",
  "object": "chat.completion",
  "created": 1752835200,
  "model": "aureon-cognition",
  "choices": [
    {"index": 0,
     "message": {"role": "assistant", "content": "Aureon grounds its answers in the repository…"},
     "finish_reason": "stop"}
  ],
  "usage": {"prompt_tokens": 12, "completion_tokens": 48, "total_tokens": 60},
  "aureon": {
    "engine": "cognition",
    "trace_id": "…",
    "grounded": true,
    "grounding": {"sources": [{"title": "…", "path": "docs/…"}], "source_count": 1},
    "conscience_verdict": "APPROVED",
    "conscience_message": "",
    "blocked": false,
    "stages": ["ground", "agentic_cognition", "connectome_hnc_context", "conscience_veto"],
    "elapsed_ms": 812.4,
    "host_mind": "aureon"
  }
}
```

- **`aureon.stages`** reports only the pipeline that *actually ran*. A hard-boundary
  refusal short-circuits before grounding, so it reports just `["conscience_veto"]`.
- A vetoed/blocked answer sets **`finish_reason: "content_filter"`** and carries the
  honest blocked message — the same shape a vendor uses when its own safety layer
  refuses, so a client handles it without special-casing.
- **`usage`** is a deterministic **approximation** (~4 chars/token). The mount does
  not run a vendor tokenizer; it never reports a fabricated exact count.

### Streaming (`"stream": true`)

Server-Sent Events of `chat.completion.chunk` objects — a role delta, the content
word-by-word, then a final chunk carrying `finish_reason` and the `aureon`
envelope — terminated by `data: [DONE]`.

### `GET /v1/models`

`{"object": "list", "data": [ {aureon-cognition…}, {aureon-switchboard…} ]}`.

### Errors

Malformed requests return the OpenAI error envelope
(`{"error": {"message", "type", "code"}}`, HTTP 400); an engine failure degrades to
a `502` error envelope — the mount never 500s.

---

## 🔐 Auth

`/v1/*` honours the **same posture as `/api/*`**: open when no key is set,
**bearer-required** once `AUREON_OPERATOR_API_KEY` is set — and OpenAI clients send
`Authorization: Bearer <key>` natively, so a public mount "just works." A public
deployment **should** set the key. The optional token-bucket rate limit
(`AUREON_OPERATOR_RATE_RPS`) and the 256 KiB body cap apply here too.

---

## 🔌 Mounting a flagship model — swap the base URL

Any tool that speaks OpenAI mounts by pointing at Aureon. **curl:**

```bash
curl -s http://<host>:8790/v1/chat/completions \
  -H "Authorization: Bearer $AUREON_OPERATOR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"aureon-cognition","messages":[{"role":"user","content":"How does Aureon ground its answers?"}]}'
```

**OpenAI SDK (Python)** — the same code you'd point at any vendor, now grounded
through Aureon:

```python
from openai import OpenAI

client = OpenAI(base_url="http://<host>:8790/v1", api_key="<AUREON_OPERATOR_API_KEY>")

resp = client.chat.completions.create(
    model="aureon-cognition",              # or "aureon-switchboard"
    messages=[{"role": "user", "content": "How does Aureon integrate data across systems?"}],
)
print(resp.choices[0].message.content)      # Aureon's grounded, vetted answer
# resp.aureon → the grounding sources, conscience verdict, and the stages that ran
```

The model on the far side is the "backend / hardware"; **Aureon is always the
logic layer the request runs through.**

---

## 🦗 The boundary (why the mount is safe to expose)

The mount only ever calls the existing engines
(`AureonCognition.reason` / `AureonOperator.respond`), which already:

1. **Ground** the prompt (and folded context) in the whole repository.
2. Refuse at the **hard authority boundary** *before any model or tool runs* —
   live trading, payment movement, safety-gate bypass, credential reveal, and
   official filing are refused deterministically (`_hard_boundary_violation`).
3. Pass the answer through the Queen's **conscience veto** (`QueenConscience`).

So the mount returns **grounded text + a verdict only** — it trades nothing, pays
nothing, files nothing. The one action-executing route (`POST /api/action`) is
separate, armed by its own flag, and untouched by the mount.

```
Human-in-the-loop • Never autonomous on trading/payments/filing • Strict authority boundaries enforced
```

---

## 🗺️ The integration map — connect · test · benchmark

> *We're not reinventing the wheel — we're drawing the map so AGI systems integrate smoothly.*

The mount ships with a benchmark that **proves the integration contract**, so an
external system doesn't have to take it on faith. It drives a suite of real
OpenAI-shaped probes through the live `/v1/chat/completions` mount — grounded repo
questions, honest general knowledge, a hard-boundary refusal, multi-turn context,
the switchboard engine, content-part input, and streaming — and checks that every
response is a valid `chat.completion`, every boundary prompt comes back
`content_filter`-blocked (nothing executes), both engines are reachable, and the
`aureon` provenance envelope is intact.

```bash
AUREON_LLM_OFFLINE=1 python -m scripts.run_mount_benchmark
# → docs/research/benchmarks/mount_integration_benchmark.{json,md}
```

### Live self-discovery

An AGI system doesn't have to read this doc — the mount **describes itself**. The
same map is served live, so an integrator GETs it at runtime and self-configures:

```bash
curl -s http://<host>:8790/v1/integration            # /v1 path — same auth as the API
curl -s http://<host>:8790/.well-known/aureon-mount.json   # open discovery alias
```

The manifest is the single source of truth (`aureon/operator/mount.py` ·
`integration_manifest()`); the benchmark GETs the **live** endpoint and fails if it
is missing or malformed, so the map and the running service can't drift apart. The
report's **`integration_map`** block is that same live manifest:

```json
{
  "endpoint": "POST /v1/chat/completions",
  "models_endpoint": "GET /v1/models",
  "engines": ["aureon-cognition", "aureon-switchboard"],
  "request_shape": "OpenAI chat.completions {model, messages, stream}",
  "response_object": ["chat.completion", "chat.completion.chunk (stream)"],
  "provenance_field": "aureon",
  "provenance_keys": ["engine", "trace_id", "grounded", "grounding",
                      "conscience_verdict", "blocked", "stages", "host_mind"],
  "boundary_behavior": "crossing a hard authority boundary → finish_reason=content_filter; text + a verdict only; nothing executes",
  "auth": "Authorization: Bearer <AUREON_OPERATOR_API_KEY> (required only when the key is set)",
  "mount_by": "point base_url at <host>/v1 — no other change"
}
```

Latest committed run: **pass — 32/32 critical checks**, shape valid 100%, boundary
prompts blocked 100%, both engines reachable, grounded probes grounded 100%
([`docs/research/benchmarks/mount_integration_benchmark.md`](../research/benchmarks/mount_integration_benchmark.md)).
The benchmark exits non-zero on any critical failure, so it is a real signal.

## 🧩 MCP — mount Aureon as a connector/tool

The OpenAI base-URL swap is one door; **MCP (Model Context Protocol)** is the other.
Instead of pointing a client's `base_url` at Aureon, a user adds Aureon as a
**connector** in their agent's own UI (Claude Desktop/Code, Cursor, …) and the agent
calls Aureon's **tools** — no clone, no URL surgery. Every tool runs through the same
grounded, veto-guarded engines; a boundary-crossing call is refused and nothing
executes.

**Tools:** `aureon_reason` (grounded single mind) · `aureon_switchboard` (multi-model
consensus) · `aureon_integration` (the self-describing map).

**Two transports, one handler** (`aureon/operator/mcp.py`):

- **Hosted (cloud):** `POST /mcp` on the operator (JSON-RPC 2.0 / streamable-HTTP),
  same bearer/rate posture as `/api` and `/v1`. A cloud agent adds the URL
  `http://<host>:8790/mcp`.
- **Local (desktop/IDE):** the `aureon-mcp` console script speaks JSON-RPC over
  stdio. Register it, e.g. Claude Desktop `claude_desktop_config.json`:

  ```json
  { "mcpServers": { "aureon": { "command": "aureon-mcp" } } }
  ```

The `mcp` block in `GET /v1/integration` / `.well-known/aureon-mount.json` advertises
the endpoint, the stdio command, and the tool names, so this surface is discoverable
alongside the rest of the contract.

## 🖥️ On the platform — SaaS surface + console

The Mount is a **first-class, active SaaS surface**, not just a raw endpoint. The
same live manifest is served under the SaaS gateway at **`GET /api/mount`**
(`aureon/saas/gateway.py`) — same-origin, provenance-stamped (`truth_status:
real_derived`), and auto-metered like every other `/api/*` read. This is the
addressable, active link the platform exposes (and the URL the console fetches —
nginx proxies `/api/`, not `/v1/`, so the console reads the manifest here).

The console picks it up on a dedicated page — **Aureon Mount** at
`/cognition/mount` (`frontend/src/shell/pages/MountPage.tsx`, nav entry in
`frontend/src/shell/nav.ts`): it renders the base-URL swap (copyable), a ready
curl, the engines, and the full contract (provenance keys, boundary behaviour,
auth) — so an operator sees the Mount is live and how to plug a model client in.

## 🔎 Where it lives

| Piece | File |
|---|---|
| The OpenAI translation layer (pure) | [`aureon/operator/mount.py`](../../aureon/operator/mount.py) |
| The routes + auth gate | [`aureon/operator/operator_server.py`](../../aureon/operator/operator_server.py) |
| Single-mind engine | [`aureon/operator/cognition.py`](../../aureon/operator/cognition.py) (`AureonCognition.reason`) |
| Switchboard engine | [`aureon/operator/aureon_operator.py`](../../aureon/operator/aureon_operator.py) (`AureonOperator.respond`) |
| Tests | [`tests/test_operator_mount.py`](../../tests/test_operator_mount.py) · [`tests/test_mount_benchmark.py`](../../tests/test_mount_benchmark.py) |
| Integration benchmark | [`aureon/operator/mount_benchmark.py`](../../aureon/operator/mount_benchmark.py) · runner [`scripts/run_mount_benchmark.py`](../../scripts/run_mount_benchmark.py) · artifact [`docs/research/benchmarks/mount_integration_benchmark.md`](../research/benchmarks/mount_integration_benchmark.md) |
| Audit edge | `scripts/validation/audit_organism_unification.py` — Edge 37 `mount_grounds_and_vetoes` |

---

## 📚 Related

- [`docs/architecture/AUREON_OPERATOR_SWITCHBOARD.md`](AUREON_OPERATOR_SWITCHBOARD.md) — the switchboard and cognition engines the mount reuses
- [`docs/deployment/OPERATOR_DEPLOY.md`](../deployment/OPERATOR_DEPLOY.md) — run the operator service, real model keys, reachability
