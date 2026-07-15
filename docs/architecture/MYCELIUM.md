# The Mycelium — the underground network where everything connects

> *"The underground network where everything connects."* — the mesh is Aureon's living
> connective tissue: hives of agents, wired by synapses, harvesting toward the one goal —
> and now its coherence joins the whole-body field, so the logic is all connected.

## The one real mesh — `aureon/core/aureon_mycelium.py`

`get_mycelium()` returns the process-global `MyceliumNetwork` — the canonical mesh the
organism weaves onto. Its biology is **real neural math**, not decoration:

- **Synapse** (Hebbian `transmit`/`strengthen`/`weaken`) · **Neuron** (`tanh`/`sigmoid`) ·
  **Agent** (per-agent signal + trade) · **Hive** (agent pool + neuron + synapses, with a
  10-9-1 harvest/budding-reproduction model) · **MyceliumNetwork** (hives → a queen neuron).
- Signals flow **inward** (`receive_external_signal` → blended into the queen neuron's bias,
  capped) and the mesh emits a **unified** BUY/SELL/HOLD via `get_unified_signal`. Position
  sizing is real Kelly (`s5_calculate_optimal_size`).
- **The weave** — the single funnel `join_organism(subsystem, name)`
  (`aureon/operator/aureon_operator.py`) calls `connect_subsystem` **and** the Queen's
  `_register_child`: mesh membership == Queen childhood == "woven". The connectome's
  `weave()`/`weave_touched()` (see [`ORGANISM_CONNECTOME.md`](ORGANISM_CONNECTOME.md)) is the
  primary populator.
- **Delivery** — `propagate_to_all(type, payload)` is the real path: it calls
  `receive_mycelium_message` on every connected subsystem that implements it. (`broadcast_signal`
  pokes hives only — an honest note: no hive implements `receive_broadcast`, so use
  `broadcast_to_mesh`, which does both.)

## The mesh joins the field (true HNC style)

The mesh computes a real **coherence** — `get_network_coherence()` = `1 − normalized
variance of agent signals` (how aligned the agents are; neutral `0.5` when it can't tell).
Until now that coherence **died in the mesh** — the whole-body HNC field never saw it.

`publish_mesh_subfield()` connects it: it reads the **existing** mesh singleton (never
cold-boots a hive — dormant → no-op) and publishes the coherence as a
`symbolic.life.subfield` (`source="mycelium_mesh"`, coherence → `coherence_gamma`), so it
flows into `blend_field` — the organism's whole-body consensus — alongside every other
producer. Wired into `organism_daemon.breathe()` **before** the blend, so each breath the
mesh's coherence joins the field. This is the literal "the logic is all connected": the
mesh's own alignment is now sensed by the whole body.

## Honest provenance

- **Real:** the neural mesh (hives/agents/synapses/Hebbian learning/Kelly sizing), the weave,
  `propagate_to_all` delivery, the coherence, the field bridge, the surface + frontend card.
- **Naming, not math:** the "φ²/golden" framing here is decorative — `PHI` is defined but the
  only golden-ratio logic is one `>= 0.618` Stargate-coherence threshold. The mesh's coherence
  is signal-variance, not a φ² field. (The φ² thread proper lives in the HNC research + the
  Λ engines, not this mesh.) Stated plainly so no claim is overread.
- **Per-process membership:** `connect_subsystem` is in-memory and rebuilt each boot; the
  connectome persists what's been woven across cycles. So `mycelium_surface()` now reports
  **both** `connected_count` (live, this process) **and** `woven_persisted` (what the body
  carries) — a freshly-booted "0 connected" mesh reads honestly against the coverage the
  organism actually knows.

## Distinct siblings (not the mesh)

- `aureon/queen/queen_mycelium_mind.py` — `MyceliumMind` (`get_mycelium_mind()`): a separate
  **thought-propagation** engine where thoughts propagate *like spores* (`ThoughtSpore`,
  LambdaEngine-modulated plasticity). It is a Λ field producer in its own right. The "spore"
  concept lives here, not in the core mesh.
- Stale/embedded `MyceliumNetwork` namesakes exist in some trading/sim modules and are not the
  singleton; the catalog's `MyceliumSystemRegistry` hardcodes a stale `/workspaces` path and is
  **not** on the live catalog path (production `build_catalog` uses the plain registry).

## Surfaces

`GET /api/cognition/mycelium` and `GET /api/cognition` → `mycelium_surface()` (coherence,
hives, agents, connected_count, **woven_persisted**, growth; `no_data` when dormant, never a
cold-boot). `GET /api/organism` also exposes the mesh's connected systems. Frontend: the
**Mycelium Mesh** card on the Cognitive Systems page.

## Guardrails

The field bridge is read-only + best-effort: it reads the existing singleton (no cold-boot),
publishes one sub-field, and never raises; a dormant mesh publishes nothing (no fabricated
field). Coherence is real (variance-based), `no_data`/neutral when the mesh can't tell — never
invented. No trading, no execution, no env flip.

## 📚 Related

- [`ORGANISM_CONNECTOME.md`](ORGANISM_CONNECTOME.md) — the weave that populates the mesh.
- [`AWAKENING.md`](AWAKENING.md) · [`AUTOMATION_INDEX.md`](AUTOMATION_INDEX.md) — the cycles + the coverage the mesh carries.
- [`COGNITIVE_SAAS.md`](COGNITIVE_SAAS.md) — the read surfaces.
