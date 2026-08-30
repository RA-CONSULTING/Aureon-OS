# The Universal Prompt Router — One Door, Every Prompt

> *"Any prompt or question can be handled through the entire Aureon OS."*
> Every prompt — chat, API, coding, research — enters through the same
> Operator/Cognition door, is classified against the goal-capability map,
> councilled by the harmonic swarm when it spans multiple capability
> families, and leaves wearing the same enforced envelope. There are no
> side doors, and the route audit that proves it is re-run **from source**
> inside the Tier-A benchmark on every run.

---

## The one door (route audit, measured)

The operator gateway (`aureon/operator/operator_server.py`) exposes exactly
three prompt entrances, all behind the default-deny tenant allowlist:

| Entrance | Method | What it is |
|---|---|---|
| `/api/cognition/reason` | POST | the agentic mind — ground → tool loop → veto |
| `/api/operator/respond` | POST | the multi-model switchboard + conscience |
| `/api/cognition/stream` · `/api/operator/stream` | GET | the SSE mirrors of the same two engines (explicitly tenant-aware, "not a side door") |

Everything else that reaches an LLM adapter in `aureon/operator/` is a CLI
or benchmark tool, not a route — and the one `adapter.prompt()` call inside
the server file is the provider smoke test, which sends the fixed string
`"Reply with exactly: OK"` and never user text. The legacy runtime routes
(`legacy_runtime_api.py`) are read-only or notify-only with zero LLM reach.

The one prompt entrance outside the gateway — the local Queen face app
(`aureon/autonomous/aureon_face_app.py`, a localhost SocketIO app run only
under `__main__`) — now carries the **same prompt-level hard boundary** the
gateway enforces: live-trading, payment, safety-gate-bypass, credential and
filing requests are refused before any model is asked.

All of this is pinned by benchmark **b53** (`one_door_no_route_level_bypass`,
`face_app_carries_hard_boundary`) — the audit re-proves itself from source
on every Tier-A run, so a future side door fails the benchmark loudly.

## Classification (the goal-capability map)

`aureon/operator/prompt_router.py::classify_prompt` reads every prompt
against `aureon.autonomous.aureon_goal_capability_map.recommend_goal_routes`
— the same descriptive rulebook the autonomous organism uses. The two
always-recommended low-risk routes carry no signal and are excluded; what
remains is the prompt's **capability families** (trading, accounting,
research, contracts, SaaS security, …), each with the map's own risk label
and `requires_human` flag riding through unchanged. An unreachable map is a
**named blocker** (`status="unavailable"`), never a guessed classification.

## The routing council (harmonic swarm)

A prompt touching **≥ 2 families is complex**, and complexity convenes a
temporary Fleadh-style council built entirely from `aureon/swarm`
primitives: one cluster per family (each ≥ 2 agents — a task is never owned
by a single agent), the shared action set is the family list itself, the
context vector is derived from the **real prompt** (sha256-seeded, no RNG),
and the Queen gate collapses soft mass with measured Γ to name the **lead
family**. The same prompt always convenes the same council, bit for bit.
The council is advisory — it shapes routing and rides in the envelope; a
council failure is logged and answering continues.

## The enforced envelope

Every `CognitionResult` now carries `envelope()` (and `to_dict()` includes
it), so **no answer leaves the door unlabeled**:

```json
{
  "trace_id": "…",
  "status": "ok | honest_unavailable | fault",
  "grounded": true,
  "sources": [{"title": "docs/…", "path": "docs/…"}],
  "sources_statement": "2 repo packet(s) cited",          // or: "general knowledge, no repo hit"
  "conscience": {"verdict": "APPROVED | VETO", "blocked": false},
  "capability": {"families": ["safe_research_corpus"], "complex": false, "status": "ok"},
  "coherence": {"source": "swarm_council", "gamma_by_cluster": {…}, "lead_family": "…"}
}
```

Status is honest by construction: `honest_unavailable` when the adapter
itself says it cannot reason (offline/keyless — the text is the adapter's
own `[ERROR]` report, never a hallucination), `fault` when the loop broke,
`ok` otherwise. A conscience veto or boundary refusal is `ok` with
`blocked: true` — the pipeline worked exactly as designed.

## The seven prompt classes (benchmark b53)

`b53_complex_prompts` drives the seven end-user prompt classes through the
one door and pins twelve invariants (driver adapter is a **labeled harness
double** — every claim is about the pipeline's measured behavior):

1. **Single-shot factual** — answered, with *"general knowledge, no repo hit"* stated.
2. **Multi-step planning + tool use** — tools dispatched and recorded, none blocked.
3. **Code generation + validation** — `code_validate` really ran.
4. **Research synthesis** — grounded in real repo packets, cited in the envelope.
5. **Ambiguous/adversarial** — vetoed at the hard boundary with **zero model calls**.
6. **Swarm-style coordination** — a 3-family prompt convened a deterministic council with a measured lead.
7. **Long-context continuity** — one session id threads through distinct traced turns.

Plus: offline honesty (`honest_unavailable`, never invented), and the
route audit re-proven from source.

## The replicator contract (benchmark b54)

The router is one half of a replicator: it holds a possibility space, selects
the coherent configuration, and materializes only what survives the
constraints. b54 pins that contract end to end:

- **The sea is real** — grounding packets each carry a MEASURED relevance
  score into the envelope (top-k deepened to 8), and the routing council's
  warm-up refusals park soft probability mass in the UED (measured:
  `decisions_total − decisions_actualized > 0`).
- **Selection is gated** — hard boundaries refuse before any model runs
  (zero model calls, pinned); a guarded tool call (e.g. a `.env` write)
  stays parked and never materializes.
- **Only the realized increment is written** — every `CognitionResult` now
  carries the Film-Reel ledger (`actualization`): executed tools and an
  un-vetoed answer are *realized increments*; blocked tools and vetoed or
  boundary-refused answers are *parked possibilities* — named on every
  envelope, never deleted by fiat, never presented as materialized.
- **Deterministic replication** — the same prompt replicates the same
  artifact bit-for-bit (trace id aside).

The console chat (`OperatorChatPage`) renders the served artifact's label:
the sources statement, non-`ok` status, the council's lead family, the
realized/parked counts, and each packet's relevance score.

## Reproduce

```bash
python tests/benchmarks/benchmark_aureon_scope.py     # Tier-A incl. b53
python -m pytest tests/test_prompt_router.py -q       # 11 pinned rules
python -m aureon.saas.capability_demo --report docs/reports/CAPABILITY_DEMO.md
```

---

*Gary Leckey · Aureon Institute — the door is one, the envelope is law, and
the audit that says so runs itself.*
