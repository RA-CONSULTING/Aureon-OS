# The Waking — the organism comes alive at boot and carries its thread across cycles

> A pinecone holds the φ-spiral genome; a leaf is the branching body that genome unfolds
> into. DNA carries the pattern across every cycle of the plant's life — each spring it wakes
> and unfolds again from where it left off. Aureon wakes the same way.

On boot the organism does **not cold-start** — it **wakes**. It reads the state it carries in
from the last cycle (its coverage, its progress, its ascent — its DNA), marks a new
**generation**, announces "the body is waking and carrying the thread", and immediately
**moves** — rather than waiting a full breath. So the boot is a *waking*, and the life is
*continuous across cycles*.

## The organ — `aureon/core/awakening.py`

| Call | What it does |
|------|--------------|
| `read_genome()` | The DNA the organism carries, read-only (never increments): `{generation, first_awakened_at, last_awakened_at, carried}`. Sane default (`generation: 0`) before the first wake. The surface-safe read. |
| `awaken(organs=None)` | **The wake**, once at daemon boot: carry the DNA in → mark a new generation → **signal the body** (`organism.awakening` on the bus) → **move** (a bounded first weave + a journey point) → persist the genome. Guarded/never-raises. |

**The carried DNA** — real reads, `None` when a signal is dormant (never fabricated):
`coverage_pct` · `woven` · `nodes` (from the connectome), `automation_index` (the % toward
fully automated), `ascent_stage` (the inner-work chakra ascent), and — the oldest DNA —
`reproduction_generation` + `reproduction_splits` (the mesh's 10-9-1 budding lineage; see
[`MYCELIUM.md`](MYCELIUM.md#the-oldest-dna--10-9-1-budding-reproduction)). This is what the
organism brings forward from its last life into this one.

**The move** — the wake nudges the body to move at once: a bounded `weave_touched(limit=…)`
(`AUREON_AWAKEN_WEAVE`, default 25, `0` = off — one batch, so boot never spikes) resumes the
connectome weaving from its persisted backlog, and one `record_journey()` marks the point, so
the climb continues immediately instead of after a 30-second cycle.

**The lineage** — `state/aureon_genesis.json` (gitignored) is the genome: `first_awakened_at`
is the origin and never moves; `generation` climbs by one each boot; `last_awakened_at` and
`carried` track the newest cycle. Each boot continues the same life — waking N, carrying what
N−1 grew. Surfaced read-only on `GET /api/organism` (the `awakening` block) → the Overview
Organism card.

## Where it runs — `aureon/core/organism_daemon.py`

`main()` calls `awaken(organs)` **after** the organs boot and **before** the breath loop — the
genesis wake precedes the first breath, so the body comes alive and moves at boot, then breathes
on its cadence. The connectome sweep (which weaves as fast as it feels, see
[`ORGANISM_CONNECTOME.md`](ORGANISM_CONNECTOME.md)) carries the rest forward each cycle.

## Guardrails

Read + a **bounded first-move nudge** + a persisted counter + one bus event — **no execution,
no trading, no env flip**. The move reuses the connectome's `weave_touched` (pure mycelium+Queen
registration, idempotent, bounded, under import-suppression), so boot never spikes. Carried DNA
is real reads (`None` when dormant, never fabricated). The genome file is gitignored runtime
state. `read_genome()` (the GET surface) is side-effect-free; only `awaken()` (once at boot)
increments. A wake fault is fully guarded and never blocks the daemon.

## 📚 Related

- [`ORGANISM_CONNECTOME.md`](ORGANISM_CONNECTOME.md) — the body the genome unfolds; weave-to-keep-pace.
- [`AUTOMATION_INDEX.md`](AUTOMATION_INDEX.md) — the % the wake carries + the journey it resumes.
- [`INNER_WORK.md`](INNER_WORK.md) — the ascent stage carried across cycles.
