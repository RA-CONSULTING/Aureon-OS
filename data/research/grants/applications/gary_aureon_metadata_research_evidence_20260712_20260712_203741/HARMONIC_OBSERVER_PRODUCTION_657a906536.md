# Harmonic Observer — Production Runbook

This runbook is the operator's reference for deploying the
HarmonicObserver + Vote 7 + narrow-band + Kelly-buffer wiring into
live trading. Read it before flipping any switch.

---

## 1. The honest picture

The observer integration was built across Stages A → AA. Every stage
was smoke-tested individually; **none of them have ever influenced a
real exchange order**. The decision to flip from `dry_run` to `live`
is the first time real money will flow through:

- `queen_gated_buy` Vote 7 (BEARISH consensus → veto bad entry)
- `execute_sell_with_logging` Vote 7 (BULLISH consensus → veto premature TP)
- multi-brain narrow-band threshold (+1 vote required when coherence < 0.4)
- Kelly buffer auto-widening (up to 1.5× safety margin in chaotic fields)
- Brain 6 (per-symbol observer) and Brain 7 (bus consensus) +1 votes

The discovery that **Vote 7 was dead code from commit `f5132d9`
through `98ecf94`** (a missing `get_hub` import alias swallowed an
ImportError silently) is exactly the kind of latent bug we're guarding
against by shipping with `dry_run` default. Stage AB exists so the
next "Vote 7 was dead" situation can be caught from the audit log
without a single trade going wrong.

---

## 2. The three modes

Controlled by the env var `AUREON_OBSERVER_MODE`. Default = `dry_run`.

### `dry_run` (default — safest)

- Observer + bus consensus + wave predictor all RUN.
- Their outputs are recorded in `state/observer_audit.jsonl`.
- **Decisions are bit-identical to pre-observer trading**:
  - Vote 7 buy/sell vetos → recorded only, NOT applied
  - Narrow-band threshold tightening → recorded only, NOT applied
  - Brain 6/7 +1 votes → recorded only, NOT applied
  - Kelly buffer multiplier → stays at 1.0
- This is the ONLY mode safe for first deploy. Run it for a verification
  window (≥ 1 week, more if low-volume) and review the audit log
  before going further.

### `shadow`

- Same decision behaviour as `dry_run` (no veto, no scaling).
- Audit log entries tagged `mode: shadow` so post-trade analysis can
  separate "shadow recommendations vs actual trades" cleanly.
- Use this once `dry_run` has validated: the observer is producing
  sensible recommendations and the operator wants to start formally
  comparing them against trade outcomes.

### `live`

- Full Stages L/T/V/Y behaviour.
- Vote 7 vetos buys / TP sells when consensus is strongly opposed.
- Narrow-band raises the multi-brain threshold by +1 in chaotic fields.
- Kelly buffer widens up to 1.5× as coherence drops.
- Brain 6/7 +1 votes contribute to multi-brain confirmations.
- Only flip to this after `dry_run` and `shadow` have been clean.

---

## 3. How to deploy

### First deploy (with the wiring inactive)

```bash
# In the production env file (.env / systemd unit / supervisord conf):
export AUREON_OBSERVER_MODE=dry_run

# Restart the daemon
supervisorctl restart aureon
```

Confirm in logs:
```
HarmonicObserver mode resolved: dry_run
```

The system now runs identically to pre-observer behaviour. The audit
log fills up. Watch for:
- File grows (`tail -f state/observer_audit.jsonl`)
- Rows include `would_have_blocked` (true/false) and
  `actually_blocked: false` (because mode != live)
- No regressions in trade volume, P&L, or error rates

### Promote to shadow

After the dry_run verification window:

```bash
export AUREON_OBSERVER_MODE=shadow
supervisorctl restart aureon
```

Behaviour is identical to `dry_run` but audit rows now show
`mode: shadow`. Run analysis: how often `would_have_blocked: true` for
buys that DID happen and DID profit (false positive — observer would
have missed wins) vs DIDN'T profit (true positive — observer would
have saved a loss).

### Promote to live

After shadow has shown net-positive divergence:

```bash
export AUREON_OBSERVER_MODE=live
supervisorctl restart aureon
```

The observer now influences decisions. Watch the first hour closely.

---

## 4. Rollback

A single env var change + restart:

```bash
export AUREON_OBSERVER_MODE=dry_run
supervisorctl restart aureon
```

Or kill the observer entirely (no audit, no veto, no scaling, full
pre-observer behaviour everywhere):

```bash
# In the daemon launcher
HNCLiveDaemon(attach_observer=False)
```

Or disable specific components via the older Stage C env var:

```bash
# Disables only the Kelly gate scaling, observer still runs
export AUREON_KELLY_OBSERVE_COHERENCE=0
```

Everything is additive and can be turned off without re-deploying code.

---

## 5. Monitoring

### Audit log inspection

```bash
# Tail latest decisions
tail -f state/observer_audit.jsonl

# Count divergences (would have blocked, didn't)
jq -c 'select(.would_have_blocked == true and .actually_blocked == false)' \
   state/observer_audit.jsonl | wc -l

# Per-event-type counts
jq -r '.event' state/observer_audit.jsonl | sort | uniq -c

# Buy decisions where consensus was BEARISH
jq -c 'select(.event == "buy_vote7" and .payload.consensus_direction == "BEARISH")' \
   state/observer_audit.jsonl | head
```

### Live status

```bash
python -m aureon.status                     # current snapshot
python -m aureon.observer.run --duration 60  # spot-run
```

### Daemon health

```bash
python -m aureon.observer.benchmark --duration 60 --tag prod-health
```

---

## 6. Known fragility points

1. **The 9 hub-side predictors return None when their data feeds
   aren't pulling.** In a sandbox `bus.run_predictions` returns 2
   (observer + wave_predictor). In production with the news service /
   macro feed / whale tracker running, all 11 contribute. Watch the
   `predictor_breakdown` field in the audit log to confirm density.

2. **Vote 7 BEARISH veto threshold (`conf ≥ 0.6, str ≤ −0.3`) was
   chosen by judgement, not data fit.** Tighten it via code change
   if `would_have_blocked: true` correlates with profitable trades in
   the dry_run audit.

3. **Kelly `MAX_BUFFER_INFLATION = 0.5`** is a heuristic. The 50%-
   wider safety margin in coherence=0 fields is conservative; loosen
   if dry_run shows it's blocking too many marginal-but-profitable
   trades.

4. **WavePredictor weight = 1.0 in `get_consensus`'s `weight_map`**.
   Lower this in `aureon_autonomy_hub.py` line 395 if the wave
   predictor's untracked status is producing too much consensus pull
   relative to validated predictors (nexus_predictor at 3.0,
   probability_ultimate at 2.5).

5. **HNC parameters are still defaults** (α=0.35, g=2.5, β=1.0, τ=10).
   Run `python -m aureon.observer.fitter` after collecting ≥ 1 day
   of trace data to write `state/hnc_fitted_params.json`. Daemon
   picks up the fitted values on next start.

---

## 7. Wiring index (where each gate lives)

| Stage | Gate | File | Mode flag |
|---|---|---|---|
| L | Observer narrow-band threshold | `aureon/bots/orca_complete_kill_cycle.py` `queen_gated_buy` | `narrow_band_threshold_active()` |
| T | Buy-side Vote 7 (consensus veto + +1 vote) | `aureon/bots/orca_complete_kill_cycle.py` `queen_gated_buy` | `gate_buy_veto_active()` / `vote_addition_active()` |
| V | Sell-side Vote 7 (premature TP veto) | `aureon/bots/orca_complete_kill_cycle.py` `execute_sell_with_logging` | `gate_sell_veto_active()` |
| Y | Kelly buffer auto-scaling | `aureon/utils/adaptive_prime_profit_gate.py` `_resolve_auto_observer_coherence` | `kelly_buffer_scaling_active()` |

All four switches share `AUREON_OBSERVER_MODE`. Per-component opt-out
env vars exist for fine-grained rollback (see §4).

---

## 8. Promotion criteria

A dry_run window is "clean" if all of these hold:

- ✅ No new exceptions in daemon logs related to `aureon.observer.*`
- ✅ Audit log writing without errors (`tail -f` shows steady growth)
- ✅ At least 100 rows accumulated for each `event` type
  (`narrow_band_evaluation`, `buy_vote7`, `sell_vote7`,
  `kelly_buffer_evaluation`)
- ✅ `would_have_blocked / actually_blocked` divergence count is
  non-zero (proves the gates are firing in their RECORDED capacity)
- ✅ Sample-by-sample inspection of 10 random "would have blocked"
  trades shows the recommendation is sensible (BEARISH consensus
  during bad news, BULLISH during good)
- ✅ Pre-observer P&L over the window matches what you'd expect from
  the strategy without the observer

A shadow window adds one more:

- ✅ The would-have-blocked-but-didn't trades show a net loss in
  hindsight (observer veto would have been right)

After both windows pass, `live` is justified.

---

## 9. Stage map for further hardening

If the system runs cleanly for a month in `live`:

- Run the fitter weekly to update HNC parameters from accumulated
  trace data
- Tighten Vote 7 thresholds based on audit-log statistics
- Add the news-tone correlations from the parallel research thread
  (n=30+ once the dataset has grown)
- Add a daily P&L attribution: how much of today's P&L was the
  observer's contribution (vetoed losses, taken-up wins) vs the
  baseline strategy

---

## 10. Emergency contact

If the observer integration causes anomalous trade behaviour and you
can't tell why:

1. `export AUREON_OBSERVER_MODE=dry_run` then restart — instant
   rollback to baseline behaviour.
2. Capture the last 10k lines of `state/observer_audit.jsonl` for
   post-mortem.
3. Capture `state/lambda_history.json` for kernel-state context.
4. Capture the daemon logs around the anomaly window.

The integration is fully additive — every observer-driven decision
can be turned off without losing the recordings.
