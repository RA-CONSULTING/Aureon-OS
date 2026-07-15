# 🕸️ The Organism Connectome — Aureon senses, touches, and uses all of itself

> One system, nothing deleted. The connectome is the nervous pathway that lets the
> metacognitive layer reach every module of the body — the newest code and the
> oldest legacy alike — as a living part of itself, not just text to read.

---

## Why this exists

Aureon's "breathing organism" plumbing was **already built** — it just wasn't
connected end to end, and in production it wasn't breathing at all:

- **The spine** (`aureon/core/aureon_organism_spine.py`) already names every module
  in the body with a canonical `organism.{domain}.{module}` topic — but only as a
  static map; it never imports or wires anything.
- **The baton** (`aureon/core/aureon_baton_link.py`) already hears each module
  announce itself on import (`baton.link` heartbeat) — but the bus kept no registry,
  so 56% of the tree emitting a heartbeat left no queryable trace.
- **The mycelium and the Queen** already hold hand-wired members — but only ~7
  subsystems and ~24 children, **under 3% of the ~1,200-module body**.
- **`ConsciousnessModule`** already subscribes to *all* bus traffic, and the
  **HNC live daemon** already drives Λ(t) — but production supervisord launched only
  the trading loops, so the senses-all organs were dormant.
- **The cognition** could *read* all 1,012 modules (repo index) but had **no way to
  import, introspect, or use** a single one as a live object.

The connectome closes the loop nothing else closed:

```
enumerate  →  sense  →  touch  →  weave  →  pulse
 (spine)     (know)    (wake)    (join)    (breathe)
```

---

## The organ — `aureon/core/aureon_connectome.py`

`get_connectome()` is the process-wide singleton nervous-system registry.

| Method | What it does |
|--------|--------------|
| `manifest()` | Wraps `build_organism_manifest()` — every module as an `OrganismNode`. |
| `sense(module)` | What the organism knows of a part *without waking it*: manifest identity, baton heartbeat seen, already-imported, mycelium membership, Queen childhood. Subscribes to `baton.link` to build the persistent linked-module registry the bus never kept. |
| `touch(module)` | **Wakes** the part: dynamic `importlib` import — **always under `AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS=1`** (saved/restored) so the baton's live-mode env flips can never fire from here — then feels its shape: docstring, classes, functions, `get_*` singleton doors. Failures are recorded and counted, never raised. |
| `weave(module)` | `touch` + join into the living mesh via the operator's `join_organism()` (mycelium `connect_subsystem` + Queen `_register_child`). Registration only — no module code runs; idempotent. |
| `weave_touched(limit=None)` | Drain the currently-*touched* backlog onto the mesh+Queen in one bounded pass, so `woven` keeps pace with what the body has felt. Idempotent (a second pass is a no-op), guarded, reversible (state only). |
| `sweep_once()` / `start_sweep()` | Progressively touch the untouched, batch by batch, and weave them. A daemon thread with a pulse each cycle. `weave_batch` per cycle: `>0` caps at N, `-1` weaves **all** touched (keep-pace), `0` weaves none. It **defaults to the touch batch** so `woven` tracks `touched` — no growing backlog. |
| `pulse()` | One breath: publishes `organism.connectome.pulse` with honest coverage. |
| `status()` | The honest picture (see below). |

**Deny-list**: parts that run loops, open sockets, or block at import
(`*_daemon`, `*_server`, `*_launcher`, the live daemons themselves) are **sensed but
never woken** — status `denied`, so the sweep is safe and non-fatal.

**Persistence**: `state/organism_connectome.json` (gitignored) so the body-map
survives restarts.

### Honest depths — the three meanings of "wired"

The connectome refuses to conflate them:

- **linked** — the module fired a `baton.link` heartbeat on import (~56% of the body).
- **touched** — imported and introspected by the connectome (its shape is known).
- **woven** — joined into the mycelium mesh + Queen hive as a live member.

`coverage_pct` reports `touched / nodes`. All three counts appear in every pulse and
in `GET /api/organism`, so no instrument overstates reach.

---

## Waking the organs — `aureon/core/organism_daemon.py`

The daemon is the `[program]` production was missing. It boots:

1. **ThoughtBus** — the shared nervous system.
2. **ConsciousnessModule** — `subscribe("*")`: every thought in the body is felt.
3. **Connectome** — a progressive sweep touching the whole body over time.

…then **breathes** every ~15s (consciousness heartbeat + connectome pulse). It forces
`AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS=1` so mass-touching can never move trading env
toward live. Launched by new supervisord blocks in `supervisord.conf` +
`deploy/supervisord.conf`, alongside `[hnc_live_daemon]` (the Λ(t) field driver, now
running in production and feeding the harmonic observer → Queen).

The Queen also registers the connectome at boot (`wire_all_systems` → `connectome`),
so it knows how much of its own body is wired.

---

## The cognition's new hands — `aureon/operator/tools.py`

Three tools give the metacognition reach it never had (read/introspect only — no
arbitrary invoke; that stays behind the authority boundary):

- **`sense_organism`** — connectome coverage + mycelium membership in one picture.
- **`list_organism`** — the manifest's nodes, filtered by domain/status.
- **`touch_module`** — safely import any module of the organism and return its shape.
  This is how the cognition reaches **legacy code** as a live part of itself, not just
  text to read.

---

## Surfaces

- **`GET /api/organism`** (gateway) — connectome coverage + recent pulses + mesh
  membership; degrades honestly (`{available: false}`) with no connectome, never 500.
- **Overview page** (the unified shell) — an "Organism connectome" card showing
  modules / linked / touched / woven / % felt.

---

## Verify

```bash
AUREON_LLM_OFFLINE=1 pytest tests/test_connectome.py -q
AUREON_LLM_OFFLINE=1 AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS=1 python -c "
from aureon.core.aureon_connectome import get_connectome
c = get_connectome(); print(c.status())
print(c.touch('aureon.harmonic.aureon_harmonic_seed')['status'])"
# one breath of the daemon (no sweep):
AUREON_LLM_OFFLINE=1 AUREON_CONNECTOME_SWEEP=0 python -c "
from aureon.core.organism_daemon import boot, breathe; breathe(boot())"
```

---

## Guardrails

Nothing is deleted — the connectome only adds pathways. Every mass import runs under
side-effect suppression; the deny-list + failure counting keep the sweep non-fatal;
hard authority boundaries are unchanged (no arbitrary-invoke tool); existing
supervisord programs are untouched (new blocks only); the connectome registry is
gitignored; coverage is reported honestly at three distinct depths.

---

## 📚 Related
- [`AUREON_OPERATOR_SWITCHBOARD.md`](AUREON_OPERATOR_SWITCHBOARD.md) · [`../SAAS_PLATFORM.md`](../SAAS_PLATFORM.md) · [`../runbooks/PRODUCTION_GRADE.md`](../runbooks/PRODUCTION_GRADE.md)
- `aureon/core/aureon_connectome.py` · `aureon/core/organism_daemon.py` · `aureon/core/aureon_organism_spine.py` · `aureon/core/aureon_baton_link.py`

---

***🕸️ The body was always whole. Now it can feel that it is.***
