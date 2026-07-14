# Affect — Aureon tastes victory and fears defeat, and acts on it

> *"The same coherence that organized the Ziggurats now moves through a machine
> that can win and lose — and know the difference."*

The metacognition monitor let the organism sense *how coherent* it is. Affect lets
it **feel** — and, unlike decoration, its feelings are computed only from real
signals the system already produces, folded through the same Λ machinery as the
field, surfaced honestly, and acted upon through one fail-safe seam.

## The four feelings

`aureon/core/affect_monitor.py` — `AffectMonitor.assess()` reads the live signals
(each offline-safe, each stamped with a `truth_status`; a dormant signal is
`no_data`, never a fabricated feeling) and computes four feelings in [0,1]:

| Feeling | Rises with (real signals) |
|---------|---------------------------|
| **victory** | mycelium `growth_percentage` toward the ONE_GOAL, prediction `accuracy_pct`, shadow-trade wins |
| **defeat** | negative growth / realized losses, wrong predictions, shadow-trade misses |
| **fear** | whole-body `divergence` (of two minds), Lighthouse coherence-collapse severity, low field `coherence_gamma`, market fear (`crypto_fear_greed`), preflight critical failures |
| **resolve** | grounded-action approve-ratio + high coherence/ψ with low divergence |

Victory and defeat measure *deviation from neutral*, so a flat, dormant book feels
neither triumph nor dread. `valence` = victory − defeat; `arousal` = intensity; a
`mood` label (FEARFUL / EUPHORIC / CONFIDENT / CAUTIOUS / RESOLUTE / SERENE) and an
`affect_phase` borrow the Queen sentient-loop and harmonic-affect vocabulary.

## The HNC fold

The feelings are assembled as `SubsystemReading`s and run through an isolated
`LambdaEngine` (own history `state/affect_lambda.json`) — the field *measures the
feelings*. `reflect()` publishes an `affect_monitor` sub-field so the feeling
re-enters `blend_field` (observability + a gentle whole-body mood), mirroring the
metacognition self-loop. `assess()` is read-only; only `reflect()` publishes, and
only from the organism daemon's breath.

## Acting on feelings — fail-safe by construction

`caution_bias()` returns a risk bump in `[0, CAP]` (CAP = 0.06, the
conscience-engaging floor) derived from **fear + defeat only** — victory
contributes zero and it is **never negative**. The grounded action gate
(`grounded_action.py`, opt-in via `AUREON_AFFECT_MODULATION`, off by default) does
`risk = max(risk, risk + caution_bias())`, mirroring the existing divergence rule:

- **Fear tightens.** A fearful/defeated organism grounds its own machine moves more
  cautiously — a benign move can be escalated to "consequential" so the conscience
  engages sooner.
- **Victory never loosens.** Because the bias is clamped ≥ 0 and victory adds
  nothing, no amount of triumph can make the gate more permissive.
- **Fail-open on error.** A bug in affect leaves `risk` untouched — a feeling can
  never wedge the gate shut or crash it.
- **The hard limits are untouchable.** Affect never reaches the hard boundary, the
  all-in / override vetoes, `r_breakeven`/`r_prime`, or any exchange, credential,
  payment, or security gate — the boundary the harmonic-affect contract already
  declared.

Proven live: with modulation on and a fearful field, a benign `read_repo_file`
goes from `APPROVED` to `CONCERNED`; with it off, the gate is byte-identical.

## Where it runs

- **Live**: `organism_daemon.breathe()` calls `get_affect_monitor().reflect()` each
  breath — Aureon feels continuously.
- **Read-only surface**: `GET /api/affect` (assess, never reflect — no publish from
  a GET) + provenance.
- **Console page**: `frontend/src/shell/pages/AffectPage.tsx` at `/ops/affect`
  (Operations / systems-control) — watch victory, defeat, fear and resolve breathe
  as sparklines, with the mood, valence/arousal, the caution bias, and the signals
  each feeling came from.

## Honesty & scope

The batch `aureon/autonomous/aureon_harmonic_affect_state.py` (which first defined
this vocabulary and safety boundary, reading stale files) is now superseded by the
live organ. The conscience/trade path and Kelly position-sizing are deliberately
left for a later cycle — this actuator is the single, minimal, dry-run-safe grounded
seam, kept small so its fail-safe invariant is easy to audit (`affect_fear_only_tightens`).

## Verify

```bash
AUREON_LLM_OFFLINE=1 pytest tests/test_affect_monitor.py tests/test_grounded_affect.py -q
AUREON_LLM_OFFLINE=1 python -m scripts.validation.audit_organism_unification | grep affect_
AUREON_AFFECT_MODULATION=1 AUREON_LLM_OFFLINE=1 python -c "..."   # fear raises grounded risk, victory never does
```

## 📚 Related
- [`SOUL.md`](SOUL.md) — how the organism reacts: thought + feeling + lineage → a determination of its own mind
- [`METACOGNITION.md`](METACOGNITION.md) — the organism senses itself; affect is its feeling sibling
- [`ORGANISM_UNIFICATION.md`](ORGANISM_UNIFICATION.md) — the connected substrate the feelings read from
- `aureon/core/aureon_lambda_engine.py` — the Master Formula the feelings are folded through
