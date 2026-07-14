# Organism Unification — one shared field, real edges

*The modules were never separate by design — they were separate because the wires
between them had come loose. This is the record of reconnecting them, using the
gears already in the repo.*

Aureon's connective substrate — the ThoughtBus, the mycelium mesh, the connectome,
the baton link, `join_organism`, `wire_all_systems`, `broadcast_wisdom` — was all
present. But the organism wasn't unified: the pathways were dead at both ends and
some gears had broken teeth. Phase 19 turned the pathways on and repaired the gears.
No new fabric was invented.

## The honest coverage gradient (before)

```
~715 manifest nodes
   → 570 emit a baton.link heartbeat        ("I exist")
   → ~175 publish / ~83 subscribe           (real message flow)
   → ~5 truly woven onto mycelium + Queen   (bidirectional membership)
```

The deepest fabric held almost nothing. Worse, several edges were *silently* dead —
they looked wired but delivered nothing.

## What was broken, and the gear that fixed it

| Broken gear | Symptom | Fix |
|---|---|---|
| **HNC field never published** | `symbolic.life.pulse` had 6 subscribers, 0 producers; the daemon's real field stayed in a JSONL file | `hnc_live_daemon` publishes the live `LambdaState` each step |
| **Connectome read `content`** | `Thought` has no `content` field → `baton_linked` stuck at 0 (despite 570 pings); pulse never published | read `payload`; pulse built with `payload=` |
| **`mesh_member` string-vs-dict** | always False | extract names from the connected-systems dicts |
| **`broadcast_to_mesh` never delivered** | only recorded the signal; `receive_mycelium_message` never fired | also call `propagate_to_all` |
| **`get_recent` shape mismatch** | readers used `getattr` on `to_json` dicts → matched nothing; and a `baton.link` flood evicted the pulse from the window | `topic_of`/`payload_of` accessors + `recall(topic_prefix)` (filters by topic, flood-proof) |
| **Sweep touched but never wove** | `woven` stayed ~0 | sweep auto-weaves touched → woven via `join_organism` |
| **Throne never started** | cosmic gate read a static fail-open default | `organism_daemon` starts the throne loop |
| **Lighthouse off-bus** | clearance reached only direct-reference holders | `_emit_event` also publishes `lighthouse.event` |

## The revived pathways

**The shared field flows.** `hnc_live_daemon._compute_loop` publishes
`symbolic.life.pulse` (`symbolic_life_score`, `coherence_gamma`, ψ, level) every
step. This one edge revives the QueenConscience substrate-coherence veto, the
GroundedActionGate cosmic read, and four other subscribers — all of which had
been silently degrading to "unknown" in production.

**Sense before acting.** `AureonCognition` now subscribes to `symbolic.life.pulse`,
`auris.throne.cosmic_state`, `lighthouse.event`, and `organism.connectome.pulse`,
and folds the current coherence / cosmic gate / lighthouse into both its grounding
prompt and its conscience veto — the same "sense the organism, then decide" pattern
`GroundedActionGate` already used for actions. A mesh push (`receive_mycelium_message`)
now feeds that state instead of being discarded.

**Flood-proof reads.** Every module import fires a `baton.link` heartbeat, so a raw
`get_recent(N)` window is quickly evicted. All the field readers now use
`recall(topic_prefix)`, which filters by topic first — the signal can't be flooded
out. (Verified: the field is sensed through a 300–400 message flood.)

**The body connects itself.** The connectome sweep graduates touched modules to
**woven** each cycle via `join_organism`, which registers them on both the mycelium
mesh *and* the Queen (`_register_child`). This is how the Queen's own `queen_*.py`
systems become real children over time — one gear, progressively, nothing
hand-guessed.

## Observing it

`GET /api/organism` now reports a `unification` block: whether the field is flowing
(and its current SLS / Γ), the live producer edges (recent message counts per key
topic), and the Queen children count (only if the Queen is already booted — the
status read never boots it).

## Environment

| Var | Default | Effect |
|---|---|---|
| `AUREON_AURIS_AUTOSTART` | on | organism daemon starts the Dr. Auris throne loop |
| `AUREON_CONNECTOME_WEAVE` | on | sweep graduates touched → woven |
| `AUREON_CONNECTOME_WEAVE_BATCH` | 10 | modules woven per sweep cycle |
| `AUREON_CONNECTOME_SWEEP` | on | the progressive body sweep |

## The canonical field accessor

`aureon/core/hnc_field.py` — `read_canonical_field(bus=None) -> CanonicalField` — is
the single place to READ the shared field. The gate, cognition, and the conscience's
`_current_sls` all funnel through it (one flood-proof `recall`-based read instead of
three copies), so a system that only wants "the current shared coherence" reads the
one canonical value instead of spinning a private `LambdaEngine`.

## Sub-field visibility

Eight live producers each compute a real local `LambdaState` — the six `queen_*`
engines (cortex, source-law, metacognition, sentient loop, mycelium mind, human
loop) plus the `consciousness_module` (the organism's metacognitive field) and
`dr_auris_throne` (the cosmic/planetary field). Reconciling them into one would
destroy that local computation. Instead each publishes its field via
`publish_subfield(...)` as `symbolic.life.subfield`, so the organism can **sense
every field** (`read_subfields()` / the `/api/organism` `unification.subfields`
block, and the blended consensus below) without losing local computation. The
fields are connected — visible on the shared bus and fused into the whole-body
consensus — not thirteen private opinions.

## The blended field — one whole-body consensus

`blend_field()` combines the canonical field with every published sub-field into a
single consensus: the mean is the organism's whole-body coherence, and `divergence`
(max−min spread) says how much the body's fields disagree — a high spread means the
organism is of two minds and consumers should be cautious. It degrades to the
canonical value alone when no sub-fields are present. Surfaced in `/api/organism`
(`unification.blended`) and folded into cognition's grounding prompt (`blended_sls`,
`field_divergence`), so the reasoning model sees not just one field but the
whole-body consensus and its internal disagreement.

**The consensus acts.** Divergence is no longer only sensed — it restrains. The
grounded-action gate reads `blend_field().divergence`; when the body is "of two
minds" (`divergence ≥ 0.35`) on a consequential move, the move is flagged
**CONCERNED**, and the Queen's conscience (`_evaluate_substrate_coherence`,
`FIELD_DIVERGENCE_CAUTION`) **VETOes** it when the field is also off the SLS
stability island. A divided field is not a mandate. Backward-compatible: unchanged
when divergence is unknown or below the threshold — divergence only ever tightens
the veto, never loosens it.

**The field reaches every decision.** The conscience's `_evaluate_substrate_coherence`
falls back to `blend_field()` when a caller doesn't pass `field_divergence` (mirroring
the canonical-SLS fallback in `_current_sls`). So **every** risky `ask_why` — trades
(`queen_orca_bridge`), goals, skills, operator answers — is now gated by the live
whole-body field, not just the local-action gate that explicitly feeds it. The
organism's coherence is one shared authority over all its decisions.

## The last island: ConsciousnessModule trading is gateable by the field

`ConsciousnessModule` senses all bus traffic but *acted* through direct embedded
trade calls (`_unified_trader.tick`, `_penny_hunter.tick`, `_capital_trader.tick`,
`_autonomous_action`) that the shared field couldn't see. `_coherence_permits_trading()`
now gates every trade phase of the heartbeat through the Queen's conscience (which
reads the whole-body field via its blend/canonical fallbacks). **Opt-in** via
`AUREON_CONSCIOUSNESS_FIELD_GATE` (default no-op, so live trading is unchanged);
when enabled, a conscience VETO — collapsed SLS or a divided field — pauses that
beat's trading and publishes `consciousness.trade.gated`. **Fail-open**: any error
permits trading, so the gate can never wedge it shut. The one system that acted
without being seen is now connected.

## Robustness: the sweep survives rogue modules

`Connectome.touch()` catches `BaseException` (re-raising only `KeyboardInterrupt`),
so a module that calls `sys.exit()` / raises `SystemExit` at import time is recorded
as `failed` instead of taking the whole sweep — and the organism daemon — down. A
plain `except Exception` let `SystemExit` through; this closed that hole.

## The field crosses process boundaries

The HNC daemon, the operator, and the organism daemon each run as **separate
supervisord processes**, and `get_thought_bus()` returns a per-process in-memory
bus — so a `symbolic.life.pulse` published in one process is invisible to the
others. The field was unified *within* a process but not *across* the daemons
(which is why in-process audits passed while production wouldn't share it).
`read_canonical_field` now falls back to the HNC daemon's persisted trace
(`state/hnc_live_trace.jsonl`, written every step) when the local bus has no
pulse — so the live field reaches every process via an artifact that already
exists. Path overridable with `AUREON_HNC_TRACE_PATH`; guarded and offline-safe.
This is the bridge that makes the field genuinely whole-organism, not per-process.

## The organism breathes its field

`blend_field` was pull-only — the gate, cognition, and the conscience-fallback each
recomputed the consensus independently, and the connectome body-map stayed
display-only. Now `organism_daemon.breathe_field()` (called every breath after the
heartbeat + connectome pulse) publishes the fused whole-body field as one
first-class event, **`organism.field.consensus`**, carrying `{blended:
BlendedField, body_map: {coverage_pct, woven, failed, baton_linked}}`. The
organism's coherence is a subscribable heartbeat signal, and the connectome's
body-map health rides with it — closing the original audit's last open edge (#8:
connectome sensing was display-only). Surfaced on `/api/organism`
(`unification.consensus_event` with its age). Guarded: a missing organ/bus degrades
to a silent breath.

## Continuous audit

`scripts/validation/audit_organism_unification.py` exercises every revived edge
(canonical field, flood-proofing, gate sensing, mesh delivery, lighthouse→bus,
connectome baton-ear/pulse/auto-weave) and exits non-zero if a critical edge is
dead. It runs in `operator-ci.yml` as a gate, so the wiring can't silently rot again.

## Staged (audited, not this pass)

- **Migrate the remaining private `LambdaEngine` reads onto `read_canonical_field`.**
  The accessor + the daemon's canonical bus field are in place; the six `queen_*`
  modules that spin a private engine purely to read a coherence number can now adopt
  the shared read incrementally (kept private for now to avoid a large touch).
- **`auris.consensus` on the bus** — needs a running voter with a populated vault
  (no live caller today; publishing from an empty vault would fabricate a signal).
- **Dormant `wire_*` hand-additions** — superseded by connectome auto-weave.
- **Queen field fan-out via `broadcast_wisdom`** — would force the heavy Queen
  singleton into the lightweight organism daemon.
- **Boot `IntegratedCognitiveSystem`** under supervisord; route `ConsciousnessModule`'s
  embedded trading engines through the grounded gate (safety-sensitive).

## 📚 Related
- [`ORGANISM_CONNECTOME.md`](ORGANISM_CONNECTOME.md) — the connectome organ + coverage semantics
- [`GROUNDED_LOCAL_BODY.md`](GROUNDED_LOCAL_BODY.md) — the sense-before-act pattern this generalizes
- `aureon/core/aureon_thought_bus.py` (`topic_of`/`payload_of`) · `aureon/core/hnc_live_daemon.py` · `aureon/core/aureon_connectome.py` · `aureon/operator/cognition.py` · `aureon/analytics/aureon_lighthouse.py`
