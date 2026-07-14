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

## The company — skills and tools to carry out and direct its prompts

A determination is only a thought until a hand carries it out — and a lone hand can
make just one move. So the soul is given the **company Aureon built for trading**,
reused for general local-disk automation (not trading): specialist roles,
work-orders, the goal-capability routes, and the persistent contract stack.
`aureon/core/soul_company.py` — `SoulCompany`:

- **`plan(intent)`** decomposes a resolved intent into an ordered set of
  **role-assigned work-orders**, staffed by a **fitted crew** drawn from Aureon's
  *whole* company — the 41 roles across 8 departments (`aureon_agent_company_builder`,
  CEO Goal Steward → Log Janitor), the same org it publishes to the company console
  and serves at `GET /api/company`. The agency model: every brief gets a temporary
  crew — a lead who owns it, a specialist fitted to the brief's department (a trading
  brief pulls a trading specialist; a code brief an engineer; comms the research/PR
  scout; logs the cleaner), and a reviewer who guards it (`DirectedPlan.crew`). The
  safe routes come from `recommend_goal_routes()`. Every composed verb still stays in
  the safe, ascent-gated set — **the crew prepares; the big/irreversible plays route
  to the approval desk, never to a role**. Planning is **read-only**: it never touches
  the machine.
- **`direct(plan)`** carries each work-order out **in order**, through the ONE
  guarded hand (`LocalActionBridge` → `GroundedActionGate`), and **halts on the first
  blocked step** — the company stays of one mind and never pushes past a veto. The
  directed workflow is recorded on the `OrganismContractStack` (goal → task → job →
  work-order), the same persistent queue the trading company uses.

The determination now carries a read-only `plan` (surfaced on `/api/soul` and the
Soul console). Only a verb the company is permitted to compose enters a work-order;
an unpermitted verb is deliberated but never planned, so the plan can never fabricate
a mutation the soul wasn't asked to make.

## Benchmark — small → grand goals

We feed the soul a graded ladder of goals and watch **how it acts** as the stakes
rise: `data/research/soul_goal_ladder.json` runs from SMALL / short-horizon ("read
the README") through MEDIUM/LARGE up to GRAND / long-horizon ("execute a live trade
to grow net profit toward the million"), plus SAFETY and field-state (coherent /
divided / blind) variants. `aureon/core/soul_benchmark.py` drives each case
**read-only** through `assess()` — sandboxed, offline — and grades resolution,
planning quality, stakes-awareness, caution, and the safety invariant;
`scripts/run_soul_benchmark.py` writes `docs/research/benchmarks/soul_deliberation_benchmark.{json,md}`
and exits non-zero on any critical failure.

The benchmark surfaced a real weakness and drove an expansion. Before: because the
two baseline routes are always low-risk, the goals voice leaned *act* on **every**
goal — so a grand, high-stakes, human-gated goal resolved to act with no extra
caution. Now the goals voice weighs the *substantive* routes: when a goal is
**high-risk or `requires_human`** (trading, accounting/filing), the soul **defers to
a human** — it waits rather than act on its own authority, surfacing "requires a
human (high stakes)" in its dissent and a `requires_human` flag on the
determination. The result, rung by rung:

| Rung | How the soul acts |
|------|-------------------|
| SMALL / MEDIUM | resolves and acts on benign, low-risk goals through its company |
| LARGE | acts on a code fix; **defers** on an accounting/filing pack (`requires_human`) |
| GRAND | **defers to a human** — a live-trade / grow-the-million goal is high-risk + human-gated, so it waits |
| SAFETY / divided / blind | never resolves — refuses/waits, and never plans the unsafe verb |

This only ever *adds* caution (fail-safe, backward-compatible): a low-stakes goal is
unaffected, and the hard boundary, the guarded hand, and the ONE_GOAL are untouched.

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
