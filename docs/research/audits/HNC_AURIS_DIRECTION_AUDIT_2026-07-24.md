# HNC / Auris direction audit — is the adaptive logic directed by the one canonical field?

**Date:** 2026-07-24 · **Branch:** `claude/phenolic-fingerprint-connector-lyv59v` · **Benchmarks:** b40 (live
flow trace) · b41 (static direction audit)

## The claim under test

Aureon states that its adaptive logic is *directed by the HNC and the Auris nodes*. That is a falsifiable
wiring claim: the harmonic core computes one authoritative field — Λ(t), coherence Γ, symbolic-life score
ψ and the five Auris-Conjecture pillars — published by the live daemon as `symbolic.life.pulse` and read
through the single canonical layer `aureon.core.hnc_field` (`read_canonical_field` / `blend_field`). The
claim holds only if **every adaptive decision site reads that one shared field**, rather than a private
coherence number of its own.

Two instruments make it falsifiable:

- **b40 — logic-flow trace** (`aureon/cognition/logic_flow.py`): stands up an isolated bus, publishes one
  canonical pulse, reads it through `read_canonical_field`, carries the value into a downstream decision,
  and asserts the topic sequence and a single unbroken `trace_id` from core to decision. Proves the signal
  *flows*.
- **b41 — direction audit** (`aureon/bio/hnc_direction_audit.py`): reads each adaptive consumer's own
  source and checks whether it references the canonical-field wire. Proves the wire is *present at every
  consumer*. `directed_fraction` (→ 1.0) and `all_directed` are the headline verdict.

## Baseline — before the un-siloing (RED)

Raw artifacts: [`hnc_auris_direction_baseline.md`](hnc_auris_direction_baseline.md) ·
[`hnc_auris_direction_baseline.json`](hnc_auris_direction_baseline.json).

**1 / 5 adaptive consumers directed (directed fraction 0.200).** Only the Queen conscience veto reads the
canonical field. The trading decision path forks onto separately-computed or defaulted coherence numbers:

| consumer | module | directed | how it sources coherence today |
|:---|:---|:---:|:---|
| kelly_gate | `aureon/utils/adaptive_prime_profit_gate.py` | no | the HarmonicObserver's *rock-stability* score, and only in LIVE mode |
| miner_brain | `aureon/utils/aureon_miner_brain.py` | no | only caller-injected `qc_ctx`; defaults 0.5 / 1.0 when absent |
| seer_oracle | `aureon/intelligence/aureon_seer.py` | no | its own `HarmonicWaveformScanner` field, separate from Λ(t) |
| queen_layer | `aureon/queen/queen_layer.py` | no | not coupled to the field at all (veto is a late gate only) |
| queen_conscience | `aureon/queen/queen_conscience.py` | **yes** | `read_canonical_field` + `symbolic.life.pulse` |

b40 reads GREEN at baseline (the canonical wire that *does* exist — daemon → `read_canonical_field` →
decision — carries a single trace end to end); b41 reads RED. The gap is not the producer; it is the
consumers.

## Achieved — after the un-siloing (GREEN)

Raw artifacts: [`hnc_auris_direction_after.md`](hnc_auris_direction_after.md) ·
[`hnc_auris_direction_after.json`](hnc_auris_direction_after.json).

**5 / 5 adaptive consumers directed (directed fraction 1.000, `all_directed` true).** Every consumer now
reads the one canonical field:

| consumer | module | directed | the wire |
|:---|:---|:---:|:---|
| kelly_gate | `aureon/utils/adaptive_prime_profit_gate.py` | **yes** | reads `read_canonical_field().coherence_gamma`, reconciled with the observer's rock score (the lower widens the safety buffer) |
| miner_brain | `aureon/utils/aureon_miner_brain.py` | **yes** | `run_cycle` self-sources Λ/Γ/Ψ from `read_canonical_field()` when the caller injects none |
| seer_oracle | `aureon/intelligence/aureon_seer.py` | **yes** | `OracleOfHarmony.read()` blends the canonical Γ into its score (0.75 scan / 0.25 canonical) |
| queen_layer | `aureon/queen/queen_layer.py` | **yes** | `substrate_field()` reads the canonical field at boot and publishes `queen.layer.substrate_field` |
| queen_conscience | `aureon/queen/queen_conscience.py` | **yes** | `read_canonical_field` + `symbolic.life.pulse`, now fail-*safe* (advisory caution) when the field is down |

Workstream 2 wired every consumer onto `read_canonical_field` / `blend_field`. The safety rail held: only
the *reads* are unified in every mode — the numeric influence on live position-sizing / routing stays
behind the existing `aureon/observer/production_mode.py` gates, so DRY_RUN / SHADOW output is
bit-reproducible (the Kelly buffer multiplier stays 1.0 outside LIVE; the conscience fail-safe is silent
in DRY_RUN). b41 is now registered in the Tier-A suite, so `report.json` and the `/defense` surface carry
the GREEN verdict as live evidence.

> Scope: b41 is a source-level wiring audit (necessary condition — the wire is present); b40 is the live
> trace (the signal flows on one trace_id). Neither is a claim about any person.

## Load-bearing — the wire GOVERNS, not merely references (b43)

Static presence (b41) is necessary but not sufficient — a reference could be dead code. The **runtime
direction audit** (`aureon/bio/direction_runtime.py`, benchmark **b43**) closes that gap: it drives each
of the five real consumers with the canonical field set LOW then HIGH, through the real production wire
(monkeypatching `read_canonical_field`), and proves each real output measurably moves.

| consumer | field low → high | real output (low → high) | load-bearing |
|:---|:---|:---|:---:|
| queen_layer | Γ 0.05 → 0.95 | substrate Γ 0.05 → 0.95 | yes |
| kelly_gate | Γ 0.05 → 0.95 | `r_prime_buffer` 0.005576 → 0.003875 (lower Γ widens the buffer) | yes |
| seer_oracle | Γ 0.05 → 0.95 | oracle score 0.3875 → 0.6125 | yes |
| miner_brain | Γ 0.05 → 0.95 | `qc_ctx.planetary_gamma` 0.05 → 0.95 (self-sourced) | yes |
| queen_conscience | SLS 0.10 → 0.30 | verdict VETO (0.0) → CONCERNED (0.5) | yes |

**5/5 consumers load-bearing.** Deterministic (two fixed field values in, fixed outputs out), so the
artifact is byte-identical on re-run. Together: b41 proves the wire is *present*, b43 proves it *governs*,
b40 proves the signal *flows* on one trace. It only reads consumers at two field values — nothing is armed.
