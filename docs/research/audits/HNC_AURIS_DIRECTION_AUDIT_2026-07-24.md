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

## Target — after the un-siloing (GREEN)

Workstream 2 wires every consumer onto `read_canonical_field` / `blend_field` (miner brain self-sources
when no context is injected; the Kelly gate reads `coherence_gamma`; the Seer oracle reconciles onto the
canonical field; the base Queen couples its first-pass routing; the conscience veto fails *safe* rather
than open). The safety rail: only the *reads* are unified in every mode — the numeric influence on live
position-sizing / routing stays behind the existing `aureon/observer/production_mode.py` gates, so
DRY_RUN / SHADOW output is bit-reproducible.

When that lands, b41 is registered into the Tier-A suite and this section records the GREEN result
(`directed_fraction` 1.000, `all_directed` true) alongside the baseline above — the before/after evidence
for the claim.

> Scope: b41 is a source-level wiring audit (necessary condition — the wire is present); b40 is the live
> trace (the signal flows on one trace_id). Neither is a claim about any person.
