# Ollama + Obsidian Integration

This document is the walkthrough for the two external tools that are
wired into the Aureon cognitive loops: **Ollama** (self-hosted LLM
runner) and **Obsidian** (local-first knowledge graph).

It covers architecture, how to set them up, how the vault talks to
them, and how the audit trail tells you whether they are healthy.

> Code lives under [`aureon/integrations/`](../../aureon/integrations/).
> Tests live under [`tests/integrations/`](../../tests/integrations/).

---

## TL;DR

```python
from aureon.vault import AureonVault, AureonSelfFeedbackLoop
from aureon.integrations import wire_integrations

vault = AureonVault()
loop  = AureonSelfFeedbackLoop(vault=vault, enable_voice=True)

result = wire_integrations(vault=vault, loop=loop)

# At this point:
#  - Every loop.tick()  → Obsidian loops/self_feedback_loop.md gets a line
#  - Every vault voice  → runs on Ollama's native /api/chat (if reachable)
#                       → its utterance goes into a dated daily journal
#                         and a per-voice markdown note
#  - vault.pathway_graph is populated with aureon.* module imports
#  - IntegrationAuditTrail has written a snapshot to integrations_audit.jsonl

print("\n".join(result.audit.summary_lines()))
```

---

## Architecture

```
┌──────────────────────── AureonSelfFeedbackLoop ───────────────────────┐
│                                                                       │
│ INGEST → SHUFFLE → QUANTIFY → VOTE → DEPLOY → HEAL → RALLY → PING →   │
│   SPEAK (voice_engine.converse())                                     │
│        │                                                              │
│        │     ┌──────────────────────────────────────────────┐         │
│        │     │  VaultVoice  (queen/miner/scout/council/...)  │         │
│        │     │     adapter = OllamaLLMAdapter  ◄────────┐    │         │
│        │     └────────────────┬─────────────────────────┼────┘         │
│        │                      │                         │              │
│        │                      ▼                         │              │
│        │               OllamaBridge ───► /api/chat       │              │
│        │                 /api/generate /api/embed        │              │
│        │                 /api/tags     /api/ps           │              │
│        │                 /api/pull     /api/show         │              │
│        │                 /api/version                    │              │
│        │                                                 │              │
│        ▼                                                 │              │
│   Utterance ──► ObsidianSink.on_utterance ──► ObsidianBridge            │
│                                                    │                   │
│                                                    ▼                   │
│                                      Local REST (https://*:27124)     │
│                                        OR Filesystem vault            │
│                                                                       │
│  loop.tick() result ──► ObsidianSink.on_tick  ──► loops/…md           │
│  IntegrationAuditTrail.run() ──► on_audit     ──► integrations/…md    │
│                                                                       │
│  NeuralPathwayMapper ──► vault.pathway_graph                          │
└───────────────────────────────────────────────────────────────────────┘
```

Five modules under `aureon/integrations/`:

| Module | What it does |
|---|---|
| `ollama/ollama_bridge.py` | Native Ollama REST client (`/api/chat`, `/api/generate`, `/api/embed`, `/api/tags`, `/api/show`, `/api/pull`, `/api/ps`, `/api/version`). |
| `ollama/ollama_adapter.py` | `OllamaLLMAdapter` — implements `aureon.inhouse_ai.LLMAdapter` on top of the bridge, so any VaultVoice can be pointed at it. |
| `obsidian/obsidian_bridge.py` | Two-mode client: talks to the `obsidian-local-rest-api` plugin on `https://localhost:27124` **or** falls back to direct filesystem writes in an Obsidian vault folder. |
| `obsidian/obsidian_sink.py` | Write-only observer that renders utterances, ticks, and audit snapshots as markdown notes (daily journal, per-voice notes, loop log, audit trail). |
| `neural_pathway_mapper.py` | Walks `aureon/*.py`, parses imports with `ast`, builds a module-level dependency graph, writes it into `vault.pathway_graph`. |
| `audit_trail.py` | Machine-readable checklist + JSONL audit log of every integration health check. |
| `wiring.py` | `wire_integrations(vault, loop)` — the single call that plugs all of the above into the cognitive loops. |

---

## Ollama setup

### 1. Install and run Ollama

```bash
# macOS / Linux
curl -fsSL https://ollama.com/install.sh | sh
ollama serve                  # starts the server on http://localhost:11434
ollama pull llama3.1:8b       # or any other model
ollama pull nomic-embed-text  # for /api/embed support
```

### 2. Tell Aureon about it (all env vars are optional)

```bash
export AUREON_OLLAMA_BASE_URL=http://localhost:11434
export AUREON_OLLAMA_MODEL=llama3.1:8b
export AUREON_OLLAMA_EMBED_MODEL=nomic-embed-text
export AUREON_OLLAMA_KEEP_ALIVE=5m
```

### 3. Verify

```python
from aureon.integrations import OllamaBridge

bridge = OllamaBridge()
print("reachable:", bridge.health_check())
print("version:",   bridge.version())
print("models:",    [m.name for m in bridge.list_models()])
print("running:",   [m.name for m in bridge.ps()])
print("embed dim:", len(bridge.embed("hello")[0]))
```

The bridge **degrades gracefully**. If Ollama is not running, every call
returns a well-formed fallback and the vault voices fall back to the
in-house `AureonBrainAdapter` — the cognitive loops keep ticking.

### Native API vs OpenAI compat

Note: `aureon.inhouse_ai.AureonLocalAdapter` already spoke to Ollama via
its `/v1/chat/completions` OpenAI-compat surface. This integration adds
the **native** API surface, which gives access to Ollama-only knobs:

| Knob | Where |
|---|---|
| `keep_alive` | controls when Ollama unloads the model |
| `options` | temperature, `num_ctx`, `top_k`, `top_p`, `repeat_penalty`, `seed`, … |
| `format` | `"json"` or a JSON schema for structured output |
| `think` | thinking mode |
| `/api/embed` | batched embeddings (returns N vectors from N inputs) |
| `/api/pull` | download a model, with streamed progress |
| `/api/ps` | VRAM usage + expiry for currently loaded models |

---

## Obsidian setup

Two transport modes — **pick one**.

### Mode A: Local REST (recommended)

1. In Obsidian, install the community plugin
   **obsidian-local-rest-api** and enable it.
2. In its settings, grab the API key.
3. Point Aureon at it:

   ```bash
   export AUREON_OBSIDIAN_API_KEY=your-key-here
   export AUREON_OBSIDIAN_BASE_URL=https://localhost:27124
   # The plugin uses a self-signed cert by default; leave verification off
   # unless you've installed the cert into your system trust store.
   export AUREON_OBSIDIAN_VERIFY_TLS=0
   ```

### Mode B: Filesystem vault (zero setup)

```bash
export AUREON_OBSIDIAN_VAULT_PATH=~/AureonObsidianVault
```

The bridge will create the directory, write `.md` files directly, and
the files behave exactly like an Obsidian vault once you open the folder
in the Obsidian app.

The bridge **auto-selects** Mode A if the plugin is reachable, otherwise
Mode B. You do not need to choose explicitly.

### What gets written

```
<your obsidian vault>/
├── daily/
│   └── 2026-04-11.md                          ← one note per day
├── voices/
│   ├── queen/20260411T203105_abcd1234.md      ← one note per utterance
│   ├── miner/…
│   ├── scout/…
│   ├── council/…
│   ├── architect/…
│   └── lover/…
├── loops/
│   └── self_feedback_loop.md                  ← rolling log of tick telemetry
└── integrations/
    └── audit_trail.md                          ← rolling audit snapshots
```

Every note carries frontmatter with the vault fingerprint before/after
the utterance, the speaker, listener, urgency, and reasoning — so you
can search your Obsidian vault by `aureon_voice: queen` or by
fingerprint hash.

---

## How the wiring works

`wire_integrations(vault, loop)` does four things:

1. **Builds `OllamaBridge` + `OllamaLLMAdapter`.** If `bridge.health_check()`
   passes, every `VaultVoice` on `loop.voice_engine` is rewired so its
   `adapter` attribute points at the Ollama adapter. From that moment on,
   every `voice.speak(vault)` call hits Ollama's native `/api/chat`.
2. **Builds `ObsidianBridge` + `ObsidianSink`.** Wraps `loop.tick` so that
   every tick result flows into `sink.on_tick` → `loops/self_feedback_loop.md`,
   and wraps `voice_engine.converse` so every produced `Utterance` flows
   into `sink.on_utterance` → `daily/…md` + `voices/<speaker>/…md`.
3. **Runs the `NeuralPathwayMapper`** once and writes the module graph
   into `vault.pathway_graph`, then ingests a `pathway.graph.built` card
   so the voice engine can reason over the graph on its next turn.
4. **Runs the `IntegrationAuditTrail`** once and emits the audit snapshot
   through the Obsidian sink's `on_audit` hook.

The call is **idempotent**. Running `wire_integrations` a second time
re-checks health, refreshes the audit, and guards the loop/voice wrappers
so they are not double-applied.

---

## The integration checklist

`aureon.integrations.INTEGRATION_CHECKLIST` is a literal Python list of
`CheckSpec` rows. Every row runs a tiny probe (import, HTTP ping,
filesystem check) and produces a `CheckResult` with a `passed` flag and
a detail dict. The current checklist covers:

| name | category | what it proves |
|---|---|---|
| `ollama.bridge.import`      | `ollama`      | `OllamaBridge` class is importable |
| `ollama.adapter.import`     | `ollama`      | `OllamaLLMAdapter` class is importable |
| `ollama.bridge.health`      | `ollama`      | `/api/version` responds (graceful on unreachable) |
| `ollama.adapter.interface`  | `ollama`      | `OllamaLLMAdapter` implements `aureon.inhouse_ai.LLMAdapter` |
| `obsidian.bridge.import`    | `obsidian`    | `ObsidianBridge` class is importable |
| `obsidian.sink.import`      | `obsidian`    | `ObsidianSink` class is importable |
| `obsidian.bridge.health`    | `obsidian`    | bridge picks a mode (local_rest OR filesystem) |
| `obsidian.sink.health`      | `obsidian`    | sink reports reachable + mode |
| `wiring.vault_voice_loop`   | `wiring`      | vault + self-feedback loop + voice engine all import together |
| `pathway.neural_mapper`     | `pathway`     | `NeuralPathwayMapper` builds a non-empty graph |
| `inhouse_ai.llm_adapter`    | `inhouse_ai`  | `aureon.inhouse_ai.llm_adapter` still importable |
| `inhouse_ai.orchestrator`   | `inhouse_ai`  | `OpenMultiAgent` class still exists |

Add a row when you wire a new integration. The row lives in
`aureon/integrations/audit_trail.py::INTEGRATION_CHECKLIST`.

---

## Audit trail on disk

Every `IntegrationAuditTrail.run()` appends one JSONL event to
`integrations_audit.jsonl` at the repo root. One line per audit. Each
event carries:

```json
{
  "audit_id": "audit_20260411T203105",
  "when": 1776025865.12,
  "iso_time": "2026-04-11T20:31:05Z",
  "total": 12,
  "passed": 12,
  "failed": 0,
  "health_ratio": 1.0,
  "results": [
    {"name": "ollama.bridge.import", "passed": true, "detail": "...", ...},
    …
  ]
}
```

When you run the audit under `wire_integrations()`, the same snapshot is
**also** written to `integrations/audit_trail.md` inside your Obsidian
vault, so you can read it in Obsidian alongside the utterance journal.

---

## Neural-pathway self-mapping

> "The internal system builds its own neural pathways based on its
> current architecture."

`NeuralPathwayMapper` walks every `.py` file under `aureon/`, parses it
with `ast`, and extracts every `aureon.*` import target. The result is a
directed graph:

- **node** — `aureon.vault.voice.self_dialogue` (dotted module path)
- **edge** — "this module imports that other aureon module"
- **cluster** — top-level domain (`vault`, `queen`, `harmonic`, …)

Stats you can pull off the graph:

```python
from aureon.integrations import build_pathway_graph

graph = build_pathway_graph()
stats = graph.stats()
print(stats["node_count"])     # e.g. 715
print(stats["edge_count"])     # e.g. 2841
print(stats["most_referenced"]) # top 10 modules by fan-in
print(stats["most_importing"])  # top 10 modules by fan-out
print(stats["cluster_sizes"])   # {'vault': 18, 'queen': 53, ...}
```

`mapper.write_to_vault(vault)` mirrors the graph into
`vault.pathway_graph` — which was declared on `AureonVault` since day
one but was previously empty. Any voice that wants to reason about "what
parts of me are connected to what?" can now read from that dict.

The mapper caches by source-file mtime hash, so calling it on every
self-feedback tick is cheap.

---

## Running the tests

```bash
python tests/integrations/test_ollama_bridge.py
python tests/integrations/test_obsidian_bridge.py
python tests/integrations/test_wiring_and_audit.py
```

Current suite:

- `test_ollama_bridge.py`: 33 checks (construction, health, chat, generate,
  embed, list_models, ps, snapshot, adapter interface, error paths,
  content-block normalisation)
- `test_obsidian_bridge.py`: 34 checks (mode selection, CRUD,
  patch_section, search, list, path sanitisation, sink.on_utterance,
  sink.on_tick, sink.on_audit)
- `test_wiring_and_audit.py`: 29 checks (NeuralPathwayMapper,
  IntegrationAuditTrail, end-to-end wire_integrations round-trip,
  run_full_audit)

**Total: 96 integration checks, all passing.**

The tests never require a running Ollama server or Obsidian app — the
Ollama tests stub the HTTP session, and the Obsidian tests run against a
filesystem vault in a temporary directory.

---

## Where the voice layer speaks next

Once Ollama is wired, the voice adapters on the `SelfDialogueEngine` are
pointed at Ollama's native `/api/chat`. You can force a voice to speak
and see the output flow through in one call:

```python
utterance = loop.voice_engine.speak_as("queen")
print(utterance.statement.text)   # came from Ollama
# Same text is now in:
#   <obsidian vault>/daily/2026-04-11.md
#   <obsidian vault>/voices/queen/20260411T203105_<id>.md
```

And one `loop.tick()` away:

```python
tick = loop.tick()
# Appended as one line to <obsidian vault>/loops/self_feedback_loop.md
```
