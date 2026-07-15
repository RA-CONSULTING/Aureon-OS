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
| `retry_failed(limit=None)` | **A failure is not forever.** Re-attempt latched `failed` modules (the import context is healed first — see below); recovered → `touched`, still-broken → keeps an `attempts` counter and **settles** after `AUREON_CONNECTOME_MAX_RETRY` (default 3) so it never churns. Bounded, guarded. Returns `{retried, recovered, still_failed}`. |
| `sweep_once()` / `start_sweep()` | Progressively touch the untouched, batch by batch, and weave them. A daemon thread with a pulse each cycle. `weave_batch` per cycle: `>0` caps at N, `-1` weaves **all** touched (keep-pace), `0` weaves none. It **defaults to the touch batch** so `woven` tracks `touched` — no growing backlog. Also self-heals a bounded `retry_batch` of failures each cycle (`AUREON_CONNECTOME_RETRY_BATCH`, default 5; `0` = off). |
| `pulse()` | One breath: publishes `organism.connectome.pulse` with honest coverage. |
| `status()` | The honest picture (see below). |

**Deny by behaviour, not by name.** The real protection is a **timeout-guarded touch**:
the import runs in a worker thread with a join timeout (`AUREON_CONNECTOME_TOUCH_TIMEOUT`,
default 10s; `0` = synchronous). If an import exceeds the timeout it is recorded `failed`
("treated as a hanger") and the sweep moves on — **no misbehaving module can ever block the
sweep** (worst case: one leaked daemon thread + a settled `failed`). Because behaviour now
decides, the deny-list is only a **fast-path** for *known* loopers: the anchored daemons/
servers/launchers (`*_daemon`, `*_server`, `*_launcher`, `hnc_live_daemon`, `operator_server`,
`integrated_cognitive_system`, the master launcher) plus a small explicit set of modules that
do a blocking/network import at module top level (`aureon_unified_live`, `aureon_multiverse_live`).
The old broad name suffixes (`_live`/`_runner`/`_app`) were **dropped** — probing showed ~26 of
those import fine and were denied purely for their name, needlessly shrinking `reachable`; now
they join the connectable body (denied 34 → 13, reachable ~1225 → ~1246).

**A denial is not forever either.** A module recorded `denied` under an *older, broader* gate stays
frozen — the sweep skips any recorded module, so it never re-touches even once it is allowed again.
`reconcile_denied()` (run at the top of each `sweep_once` and on each wake) clears the record for
every `denied` module the *current* gate no longer matches, returning it to `unfelt` so the sweep
re-touches it (behaviour, via the timeout guard, then decides — weave / fail / re-deny). So narrowing
the deny-list actually frees the stuck modules instead of leaving them latched (live: freed 9,
denied 19 → 10). Mirrors "failures aren't forever" — the body keeps re-evaluating what it once
refused.

**Persistence**: `state/organism_connectome.json` (gitignored) so the body-map
survives restarts.

### Failures aren't forever — heal the context, then retry

Once a module was recorded `failed` it used to be skipped on every future sweep — a
transient error (a dep momentarily absent, the `sys.path` shim not active, a missing file)
latched it against 100% forever. Two composing fixes make `failed` **retryable, self-healing
debt**:

- **Heal the import context.** `touch()` now activates the repo's own `sys.path` shim
  (`aureon/_path_setup.py`, one-time, guarded — it only populates `sys.path`) before importing,
  so intra-repo bare-name imports (`import binance_client`) resolve exactly as they do when an
  app entry point runs. Roughly **half of the failures were spurious `ModuleNotFoundError`s** for
  modules that live in the repo — measured live, **32 of 60 recover** the moment the shim is active.
- **Re-attempt, but settle.** `retry_failed()` (on demand, once per wake via `AUREON_AWAKEN_RETRY`,
  and a small batch per sweep cycle) re-touches latched failures. A genuinely-broken module keeps an
  `attempts` counter and stops being retried after the cap, so there is no perpetual churn; the
  remaining ~28 are environmental (missing pip deps, absent files, platform) and recover on their own
  the moment the environment provides them. `status()` reports `retryable` (failed, not yet settled)
  alongside `failed` so the healing debt is legible.

The net effect: `failed` falls and `touched`/`woven` climb toward 100% as the environment heals —
real recovery (the module actually imported), never a fabricated success.

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
