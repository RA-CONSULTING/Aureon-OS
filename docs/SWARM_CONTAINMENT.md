# The Containment Study — Same Species of Agent, Different Governance

> The agents *are* the replicators. The HNC is the physics that keeps them
> from becoming the uncontrolled version. That is a claim about the controls
> — so it is proven the way every claim in this repo is proven: by
> measurement, not assertion.

## The experiment

`aureon/swarm/containment.py` runs **the same hash-seeded agents** (a core
group at β = 0.9 and a beyond-cliff group at β = 1.2, identical context,
identical action set) under four named governance policies:

| Policy | Soft mass | Queen gate (Γ + island) | Steering |
|---|---|---|---|
| `governed` | ✓ | ✓ | ✓ |
| `no_gate` | ✓ | ✗ (everything actualizes) | ✓ |
| `hard_votes` | ✗ (winner-take-all one-hot) | ✓ | ✓ |
| `ungoverned` | ✗ | ✗ | ✗ |

## What was measured (canonical run, 16 steps × 2 groups)

| Measure | governed | no_gate | hard_votes | ungoverned |
|---|---|---|---|---|
| Actualization rate | **6.25%** | 100% | 0% | 100% |
| β=1.2 (cliff) actualizations | **0** | 16 | 0 | 16 |
| Warm-up (unmeasured Γ) actualizations | **0** | 10 | 0 | 10 |
| Mean simplex entropy (the sea) | **0.71** | 0.61 | **0.00** | 0.00 |
| Heading churn | 0.20 | 3.85 (**19×**) | 0.00 | 1.14 |

Three findings, all pinned as Tier-A invariants (**b55**):

1. **Ungoverned expansion is real.** Remove the Queen and *everything*
   materializes — the unstable β = 1.2 group included, steps with an
   unmeasured Γ included — and the realized path thrashes with 19× the
   heading churn. That is the SG-1 Replicator.
2. **Hard votes kill the collective.** Replace soft probability mass with
   winner-take-all voting and the sea collapses to *exactly* zero entropy —
   and the monoculture then **never clears the coherence gate** (0%
   actualization). Either nothing coherent materializes, or (ungoverned)
   the monoculture expands blindly. Soft mass is not a stylistic choice;
   it is what keeps coherent materialization possible at all.
3. **Governance is selective, not arrested.** The governed swarm still
   actualizes (6.25%, measured > 0) — flows are shaped, never stopped —
   with zero cliff leaks, zero warm-up leaks, and single-agent task
   ownership refused by construction.

**Honesty boundary:** a LABELED governance-ablation study of the swarm's own
dynamics — deterministic and reproducible, an experiment on our controls,
never a claim about external agents or systems.

## Reproduce

```bash
python -m pytest tests/test_swarm_containment.py -q      # 7 pinned rules
python tests/benchmarks/benchmark_aureon_scope.py        # Tier-A incl. b55
python -c "from aureon.swarm.containment import run_containment_study as r; \
import json; print(json.dumps(r()['variants'], indent=1))"
```

---

*Gary Leckey · Aureon Institute — without the controls: pure Replicator
expansion. With them: a replicator that only materialises the correctly
formed result. Now it's not a metaphor; it's a measured ablation.*
