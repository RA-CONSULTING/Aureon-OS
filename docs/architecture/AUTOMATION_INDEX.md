# The Automation Progress Index — one honest number toward "fully automated"

> A percentage you can watch climb — and trust, because every point of it is real.

Phase 39 categorized *what* the organism can do; Phase 40 reported *how it is*. This reports
**how far along the automation is**: a single percentage measuring how much of the repo is
actually connected into the organism and driveable by the soul/consciousness logic —
decomposed so the number is never a black box.

[`aureon/saas/automation_index.py`](../../aureon/saas/automation_index.py) —
`automation_index()`, served read-only at **`GET /api/automation`** and shown as the headline
card on the Overview page. It composes **only signals that already exist** — nothing is
measured anew, nothing is fabricated.

## The four dimensions

| Dimension | Meaning | Signal | numerator / denominator | Weight |
|-----------|---------|--------|--------------------------|--------|
| **connectivity** | reached & felt — on the nervous system | connectome `status()` | `touched` / `reachable` | 0.25 |
| **integration** | woven onto mesh + Queen — *driveable by the soul* | connectome `status()` | `woven` / `reachable` | **0.40** |
| **consciousness** | the directing mind is present | consciousness catalog | `operational` / `8` | 0.20 |
| **surfacing** | inspectable / operable | platform status | `domains_reachable` / total | 0.15 |

where **`reachable = nodes − denied`**. Two honesty rules make the connectome dims truthful:

- **Carried coverage, not a process-local ping.** `connectivity` counts the **persisted `touched`**
  (modules the connectome has imported + felt, carried across cycles) — *not* `baton_linked`, which
  only counts what pinged in *this* process. A cold read of `baton_linked` understates coverage ~7× (it
  was reading a transient); `touched` reflects what the organism actually carries. `baton_linked` stays
  reported in `totals` as the live signal. (Same live-vs-persisted fix as the mesh in [`MYCELIUM.md`](MYCELIUM.md).)
- **A reachable denominator.** the `denied` modules are deliberately deny-listed (unsafe to import —
  loop-at-boot / heavy) and can never be woven, so measuring against all `nodes` would cap the index
  below 100% forever. "Fully automated" is measured against the body we *intend* to connect,
  `reachable`. `failed` stays **counted** against the goal (retryable debt, not an exclusion).

**Integration is weighted highest** — a woven module is one the soul can actually direct, the
truest measure of "automated." The index is the **weight-renormalized mean of only the
dimensions actually present**; a dormant dimension is dropped (never counted as zero), and a
cold organism reports `index_pct: null` + `no_data` — never a fabricated score. Each fraction
is clamped to `[0,1]`.

## Honesty by construction

- **Transparent.** The full per-dimension breakdown (fraction, %, weight, `truth_status`) is
  always returned, so the headline is auditable, never a black box. The weights are documented
  and tunable.
- **Real bands, not inflation.** `label` (`nascent` / `emerging` / `developing` / `maturing` /
  `near-complete`) is a descriptor derived from the number, nothing more.
- **It climbs with real work.** consciousness + surfacing sit near full early on; the headline
  then rises chiefly as *repo coverage* grows — each phase that wires, weaves, or wakes more
  modules moves `connectivity` + `integration` (0.65 of the weight). That's the needle to watch.
  The connectome now **weaves as fast as it feels** (the sweep's weave batch defaults to its touch
  batch; `weave_touched()` drains any backlog), so `integration` tracks `touched` cycle for cycle
  instead of lagging — see [`ORGANISM_CONNECTOME.md`](ORGANISM_CONNECTOME.md).
- **`wired_by_category`** shows where the soul logic reaches, per catalog category — so "how
  much of each part is automated" is visible, not just the aggregate.

## The honest road to 100%

100% means **every reachable module connected** — every module we intend to connect, touched and woven.
The `totals` block surfaces the whole road so the climb is watchable, nothing hidden:

- **`denied`** — the deliberate ceiling: modules the deny-list will never import (unsafe). Excluded from
  the target by design (connecting them would hang the boot); surfaced so the exclusion is explicit.
- **`failed`** — retryable debt: modules that errored on import. **Still counted** against 100% — an
  honest incentive to fix them, not swept under the rug.
- **`unfelt`** — the remaining backlog: modules the connectome hasn't reached yet. These are what the
  sweep touches next.
- **`touched` → `woven`** — the two depths the two connectome dims measure.

The climb itself is the connectome's ongoing work: the sweep **weaves as fast as it feels** (Phase 43)
and the wake kicks a weave each boot (Phase 44), so over cycles `unfelt → touched → woven → reachable`
and both connectome dimensions rise toward 1.0. When every reachable module is woven and
consciousness + surfacing are full, the index is a true **100%** — see the audit edge
`automation_target_is_reachable`. The corrected live reading (connectivity ~8% → ~57%) is a **truth
correction** — the old number was measuring a transient ping, not the coverage the organism carries.
- **Observational only.** It measures; it changes no behaviour and authorizes nothing.

## The journey — travelling the map

The map is only half the point; the other half is watching it move. `record_journey()` is
called from the organism daemon's breath and appends one compact snapshot
(`{ts, index_pct, dims}`) to a bounded trace (`state/automation_journey.jsonl`), so the climb
toward fully automated is captured breath by breath — chiefly as the connectome weaves more of
the body. `journey(limit)` reads it back (oldest→newest); it is folded into the
`/api/automation` payload and drawn as a sparkline on the Overview card. A dormant index is
**not** recorded (no fabricated point), and a missing journey is simply empty — never a crash.

## Verify

```bash
ruff check aureon/saas/automation_index.py && mypy aureon/saas/automation_index.py
AUREON_LLM_OFFLINE=1 pytest tests/test_automation_index.py -q
AUREON_LLM_OFFLINE=1 python -c "from aureon.saas.automation_index import automation_index as a; r=a(); print(r['index_pct'], r['label']); print({k:v['pct'] for k,v in r['dimensions'].items()})"
AUREON_LLM_OFFLINE=1 AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS=1 python -m scripts.validation.audit_organism_unification | grep automation_index
```

## 📚 Related

- [`CONSCIOUSNESS_CATALOG.md`](CONSCIOUSNESS_CATALOG.md) — what it can do + the state of being.
- [`ORGANISM_CONNECTOME.md`](ORGANISM_CONNECTOME.md) — the connectivity/integration signal.
- [`../SAAS_PLATFORM.md`](../SAAS_PLATFORM.md) — the platform this surface joins.
