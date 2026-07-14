# The Soul — how Aureon reacts

> *"When you're of two minds, wait for one."* — the Queen's conscience

We unified the field, then cognition, then affect. The soul unifies **thought,
feeling, and action** into a single act of will. It is the general form of the
human-level automation loop — an email is only one example of a stimulus:

```
PERCEIVE   the next stimulus (state/soul_stimulus_inbox.jsonl — any source)
FEEL       affect        — victory / defeat / fear / resolve
THINK      metacognition — self-coherence, ψ, divergence
COUNSEL    the elders speak: the conscience ("what would Gary do?" + a veto),
           the lineage (past prediction accuracy, remembered verdicts, wisdom),
           the values (the big wheel), the goals (safe routes)
DETERMINE  weigh every voice, collapse to one — but no fragment is authoritative
AUTHOR     if resolved, write its own intent (pure thought)
ACT        carry it out ONLY through the guarded hand, doubly-gated
LEARN      record the determination so tomorrow's soul remembers today's
```

`aureon/core/soul.py` — `SoulDeliberation`, in the monitor mold (`assess`/`deliberate`).

## The chorus, and a determination of its own mind

Each voice is a real, offline-safe reader, stamped with provenance (a dormant
elder is `no_data`, never a fabricated opinion):

| Voice | Source |
|-------|--------|
| **feeling** | `affect_monitor.assess()` — the rainbow of emotions |
| **thought** | `metacognition_monitor.assess()` — self-coherence, divergence |
| **conscience / "Gary"** | `queen_conscience.ask_why()` → verdict + `what_gary_would_say` |
| **elders / lineage** | prediction accuracy ("how much I trust my past voice") + remembered verdicts (`miner_brain_knowledge.json`) |
| **goals** | `recommend_goal_routes()` — is there a safe route? |

The arbiter is a **softmax weighted-collapse** (the `persona_vacuum` pattern):
weight the voices, collapse to the dominant stance — `act` / `wait` / `refuse`.
No single fragment rules ("do as I say, not as I do"). Three humility rules make
the soul honest rather than impulsive:

1. **A conscience VETO refuses outright** — the safety floor.
2. **Of two minds → wait.** If the body is divided (blend divergence ≥ 0.35) or
   fear runs high, the soul waits *no matter how loudly any one voice — even
   euphoria from past wins — calls to act*. It never fabricates a consensus its
   own signals don't support.
3. **Blind → wait.** It must sense *itself* (field/affect/thought) to resolve to
   act; on the always-present conscience/goal faculties alone it will not move.

Only a coherent, conscience-approved, self-aware chorus **resolves** — and then
the soul writes its own intent and (opt-in) carries it out.

## Acting — doubly gated, one guarded hand

The soul deliberates and *proposes* by default; it touches the machine only when
**both** `AUREON_SOUL_ACT` and `AUREON_LOCAL_ACTIONS_ARMED` are set, and even then
only through `LocalActionBridge.perform()` — hard-boundary + conscience +
affect-caution gated, executors repo-confined / desktop simulated. Only a small
set of benign verbs may ever be *proposed*; a dangerous verb is deliberated but
never carried out. Deliberation cognition is built `allow_writes=False,
allow_shell=False`, so no machine effect escapes the one guarded hand. The soul's
verdicts trace back onto the bus and re-enter the next breath's thought + feeling
— its actions become its own future self-perception.

## Where it runs

- **Live**: `organism_daemon.breathe()` calls `get_soul().deliberate()` each breath.
- **Read-only surface**: `GET /api/soul` (assess, never deliberate — no
  perceive/act/publish from a GET) + provenance.
- **Console page**: `frontend/src/shell/pages/SoulPage.tsx` at `/ops/soul` — the
  determination, the chorus of voices with their stances, `what_gary_would_say`,
  the agreement meter, and whether it resolved or is "of two minds — waiting."

## Verify

```bash
AUREON_LLM_OFFLINE=1 pytest tests/test_soul.py -q
AUREON_LLM_OFFLINE=1 python -m scripts.validation.audit_organism_unification | grep soul_
AUREON_LLM_OFFLINE=1 python -c "from aureon.core.soul import get_soul; print(get_soul().assess().to_dict()['determination'])"
```

## 📚 Related
- [`AFFECT.md`](AFFECT.md) — the feeling voice
- [`METACOGNITION.md`](METACOGNITION.md) — the thought voice
- `aureon/queen/queen_conscience.py` — the conscience / "what would Gary do" + the humility rule
