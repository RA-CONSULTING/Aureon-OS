# The Feature Switchboard — every system feature, on or off, at human discretion

> *Turn all features of the system at human discretion.* — the directive this closes.

Aureon is a large organism with many capabilities, and until now every one of them was gated by a
scattered `os.environ` read — no single place to see, or to switch, what the body is allowed to do.
The **feature switchboard** is that place: one instance-owned control plane where a human turns
system features on and off, and the choice reaches the whole organism.

It is the sibling of the two credential surfaces already shipped:

| Surface | What it manages | Where |
|---|---|---|
| **Providers** (Phase 14) | LLM API keys — bring your own for every model | `/cognition/providers` |
| **Connections** (Phase 15) | ~24 external sources (trading → NASA), keys + readiness | `/ops/connections` |
| **Switchboard** (this) | every capability feature — on/off | `/platform/switchboard` |

The "load env/API keys" half of the ask is Providers + Connections; the switchboard is the feature
on/off half.

## What it is

- **`aureon/operator/feature_switchboard.py`** — the registry (`FLAGS`) + a Fernet-encrypted store at
  `~/.aureon/feature_flags.json.enc` (key file `~/.aureon/feature_flags.key`, mode 0600, git-ignored),
  mirroring the provider keystore exactly. `save_flag(id, enabled)` records a human decision;
  `apply_to_env()` injects it into `os.environ`; `flag_view` / `grouped_view` surface it honestly.
- **`/api/switchboard`** (operator, bearer-gated) — `GET` the grouped flags; `POST /<flag_id>` to flip
  one.
- **`SwitchboardPage.tsx`** at `/platform/switchboard` — the front-door UI: grouped cards, a live/restart
  badge per flag, and the arming ceremony for the hard-boundary group.

## How a decision reaches the organism

A flag decision is persisted encrypted, then applied to `os.environ`. Two paths carry it to the code
that reads it — and each flag says **honestly** which one applies:

- **`effect: "live"`** — the flag is consumed by the operator's own cognition engine
  (`AUREON_COGNITION_PREFER_LOCAL`, `AUREON_LLM_OFFLINE`). A `POST` hot-rebuilds the switchboard
  (`_rebuild_switchboard()`), so it takes effect immediately in the operator process.
- **`effect: "restart"`** — the flag is consumed by another process (the organism daemon, the trading
  swarm, the billing route…). Every daemon calls `bootstrap_credentials()` at boot
  (`aureon/core/aureon_env.py`), which now applies the stored flags — so the decision takes hold at
  that process's **next restart**. The UI labels this plainly ("re-reads on restart"), the same honesty
  as the Connections "restart required" note.

Flags with no stored decision are left untouched, so a `.env` value or a launcher flag (`aureon-up.sh
--live`) still wins where the human has made no UI choice.

## Is it applied yet? — the honest pending-restart signal

A "restart" label alone can't tell you whether a decision has actually reached the daemon that reads
it. So each decision is stamped: `save_flag` records `decided_at = time.time()` alongside `enabled`.
The organism daemon applies the flags (`bootstrap_credentials()` → `apply_to_env()`) and then
`awaken()` stamps `last_awakened_at` into `state/aureon_genesis.json` — so those two timestamps are
directly comparable, and `flag_view()` derives a real **`pending_restart`**:

- **`live`** flag, or a flag with **no stored human decision** → `False` (nothing is waiting).
- decision recorded but `decided_at` missing (a pre-Phase-55 entry), or the organism has never awoken
  (`last_awakened_at is None`) → **`null`** — honest no_data, never a fabricated "applied".
- otherwise → `decided_at > last_awakened_at`: **`True`** means you decided *after* the last boot, so
  the consuming process is still running the old value and must restart to pick it up.

The read is guarded (`read_genome()` degrades to `None`, never raises) and imports nothing from the
trading/runtime layer. The Switchboard page shows a **"pending restart"** badge when this is `true`.
Audit edge `switchboard_pending_is_honest` proves the truth table (before-boot → pending, unknown →
`null`, live → `False`).

## Seen in governance

The switchboard is registered as a surface in the **`governance`** category of the consciousness
catalog (`aureon/saas/consciousness_catalog.py`, beside the director's desk), `safety_posture`
`records_only_gated` — so the human control plane appears in `/api/consciousness` and the Consciousness
page, not only in its own route.

## The two tiers

### Safe / reversible — simple toggles
- **Organism & Connectome:** `AUREON_CONNECTOME_SWEEP`, `AUREON_CONNECTOME_WEAVE`,
  `AUREON_AURIS_AUTOSTART`, `AUREON_TRACE_PUMP`.
- **Cognition routing:** `AUREON_COGNITION_PREFER_LOCAL`, `AUREON_LLM_OFFLINE`,
  `AUREON_AFFECT_MODULATION` (fail-safe — only ever tightens the grounded-action gate).
- **Notifications:** `AUREON_APPROVAL_EMAIL` (records, never executes).

### Hard boundary — armed toggle, gates never removed
`AUREON_LIVE_TRADING`, `AUREON_LOCAL_ACTIONS_ARMED`, `AUREON_SOUL_ACT`,
`AUREON_BILLING_CHARGE_ENABLED`, `AUREON_SOVEREIGN_MODE`, `AUREON_ACCEPT_LIVE_RISK`,
`AUREON_GROUND_LOCAL_ACTIONS`.

These are **flippable by a human**, but only through an explicit **arming ceremony**: the `POST` is
rejected (`400`) unless it carries `confirm == <flag_id>`, and the UI requires the operator to type the
flag id into a red confirmation dialog. All default **OFF**.

## The load-bearing invariant

The switchboard is a **human control plane, not an actuator.** Flipping a flag — even a hard-boundary
one — does exactly one thing: it sets that flag's own environment variable. `apply_to_env()` imports
nothing from the trading / conscience / runtime layer and calls no executor.

Arming a hard-boundary flag **records the human's intent** and removes **no** downstream gate:

- **live trading** stays behind the runtime dry-run gate + the QueenConscience 4th-pass veto;
- **local actions armed** still passes the grounded-action gate (HNC Λ(t) + Auris + conscience) per move;
- **billing charge** still forwards to the existing edge function (fee math unchanged), 403 by default;
- the **approval queue** still records decisions and never executes;
- **no internal score** (coherence / ascent / trust) can arm anything — only a human, through the
  bearer-gated UI, can. This is the same hard boundary the whole system holds: an internal score never
  self-authorizes an irreversible, outward-facing act.

The audit edge `switchboard_never_removes_gates`
(`scripts/validation/audit_organism_unification.py`) proves it: hard-boundary flags default OFF, arming
one changes only its own env var, and the module imports no executor.

## Verification

```bash
AUREON_LLM_OFFLINE=1 pytest tests/test_feature_switchboard.py -q
# flip a flag and watch it reach the env via the boot path:
python -c "
from aureon.operator import feature_switchboard as fs
fs.save_flag('AUREON_CONNECTOME_SWEEP', False)
import os; print('sweep', os.environ.get('AUREON_CONNECTOME_SWEEP'))
print('groups', [g['label'] for g in fs.grouped_view()])"
```

## 📚 Related
- [`AUREON_OPERATOR_SWITCHBOARD.md`](AUREON_OPERATOR_SWITCHBOARD.md) — the LLM switchboard this sits beside
- [`AUTONOMY.md`](AUTONOMY.md) — the director's desk; the hard boundary the switchboard preserves
- [`../guides/PROVIDER_KEYS.md`](../guides/PROVIDER_KEYS.md) · [`../guides/CONNECTIONS.md`](../guides/CONNECTIONS.md) — the env/key half
- [`../SAAS_PLATFORM.md`](../SAAS_PLATFORM.md) — the platform ledger
