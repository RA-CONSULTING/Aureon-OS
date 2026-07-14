# The Grounded Local Body

*How Aureon touches its own machine — and why every move first passes through the
Master Formula, the Auris field, and the Queen's conscience.*

Aureon has hands. It can read and write files, run shell commands, and — where the
OS and drivers allow — move a mouse, type keys, read the screen. The question this
subsystem answers is not *can it act* but *is it coherent enough to act, and does
the conscience consent?* A body without grounding is just an actuator; a body
grounded in the field is the organism operating itself.

> *the local system always grounds its logic moves into its cognitive systems —
> the HNC Auris nodes and the Master Formula — and uses the local Ollama LLM to
> help its logic.* — the operator directive this subsystem realizes

## The one chokepoint

Every local-machine move flows through **`GroundedActionGate.ground(action,
params, context)`** (`aureon/operator/grounded_action.py`) before it may run:

```
proposed move
   │
   ├─▶ 1. hard boundary        deterministic refusal (live-trade / move-funds /
   │                            reveal-secret / disable-safety) — never negotiable
   │
   ├─▶ 2. HNC read             the Master Formula's current substrate coherence
   │                            (symbolic_life_score + Γ) from the live Λ(t) state,
   │                            and Dr Auris's cosmic gate (get_cosmic_score /
   │                            is_gate_open). Best-effort; degrades to "unknown".
   │
   ├─▶ 3. local reasoning       an optional, Ollama-FIRST one-line rationale
   │                            ("is this wise?"). The LLM only ADVISES. Offline
   │                            or absent → skipped, never blocks.
   │
   ├─▶ 4. conscience 4th-pass   QueenConscience.ask_why(action, {risk, SLS, …}).
   │                            A risky move while coherence is off the β-stability
   │                            island (symbolic_life_score < 0.20) is VETOED;
   │                            drifting (< 0.40) is CONCERNED; on the island it
   │                            proceeds.
   │
   └─▶ verdict  APPROVED | CONCERNED | VETOED | BLOCKED
        + HNC scalars, published on the bus as operator.action.request /
          operator.action.verdict under one trace_id — the organism senses it.
```

The deterministic HNC + conscience gate **decides**; the local LLM only advises.
Nothing in this module touches the machine — it produces a verdict.

### Why local verbs now engage the veto

`QueenConscience._is_risky_action` historically recognized only trade/override
verbs, so a `click` or `delete_file` never engaged the substrate-coherence veto.
Phase 18 extends it with local-machine verbs (`delete`, `overwrite`, `shell`,
`click`, `type`, `wifi`, `lock`, `shutdown`, …) — so the organism's own hands are
held to the same β-stability standard as a trade. Read-only observations
(`read`, `list`, `screenshot`, `get_*`) are deliberately *not* risky: a benign
look never trips the veto.

## The body — `LocalActionBridge`

`aureon/operator/local_action_bridge.py` is the single grounded path to the
machine. `perform(action, params, context)`:

1. grounds the move through the gate;
2. **vetoed** → abandons it (`local.action.abandoned`), returns blocked;
3. **approved but not armed** → returns a dry-run result (nothing executes — the
   default posture); the gate still ran, so a full grounded verdict + trace exist;
4. **approved and armed** → dispatches to a pluggable executor and publishes
   `local.action.result`.

Executor contract (duck-typed): `executor(action, params) -> {ok, result,
artefacts, error}`. The default router sends file/shell moves to the guarded
operator toolbelt (`GuardedToolRegistry` — repo-confined, sensitive-path-blocked,
AST-checked) and desktop moves to the `vm_control` dispatcher (simulated backend
by default). Anything without a live executor degrades honestly to *executor
unavailable* — it never fabricates success.

## Grounding the move back into the Master Formula

The loop closes: `hnc_live_daemon` registers a **`local_action`** source that
reads recent `operator.action.verdict` traces off the bus and maps the approve
ratio + volume into a `SubsystemReading` fed to `LambdaEngine.step`. So Λ(t) — the
Master Formula itself — incorporates what the body is doing to its own machine.
The organism's hands are not outside its coherence; they are an input to it.

## Reasoning with the local LLM (Ollama-first)

`AureonCognition(prefer_local=True)` (or `AUREON_COGNITION_PREFER_LOCAL=1`) makes
the local Ollama line the reasoning brain even when cloud keys are present. The
gate uses this seam for its optional rationale. To let Ollama actually *drive
tools* (not just emit text), use the OpenAI-compatible path — set
`AUREON_LLM_PREFER_NATIVE=0` so `/v1/chat/completions` parses `tool_calls` (the
native `/api/chat` path returns none) — with a function-calling-capable model.
Everything is offline-safe: with no Ollama, the gate still grounds
deterministically on Λ(t) + conscience.

## The safety model

| Control | Default | Effect |
|---|---|---|
| `AUREON_LOCAL_ACTIONS_ARMED` | **off** | Bridge is DRY-RUN — nothing touches the machine until armed. |
| Conscience 4th-pass veto | always on | Risky moves refused when substrate coherence collapses. |
| Hard boundary | always on | Live-trade / move-funds / reveal-secret / disable-safety refused deterministically. |
| `GuardedToolRegistry` | always on | Repo-confinement, sensitive-path block, destructive-shell regex, AST check. |
| `vm_control` risk model | always on | Arm / dry-run-default / emergency-stop per action risk class. |
| `AUREON_GROUND_LOCAL_ACTIONS` | off (opt-in) | Routes the ungated "sovereign" `AureonAgentCore` path through the gate too. |

The gate is **additive** — it only adds checks in front of executors; it never
loosens an existing guard. The recommended path for any new local capability is
`LocalActionBridge`, not the raw hands.

## HTTP surface

Under `/api/*` (bearer-gated when `AUREON_OPERATOR_API_KEY` is set):

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/action` | Ground + (if armed) perform a local move; returns the verdict + HNC scalars. Dry-run by default. |
| GET | `/api/action/status` | Armed state + recent approve/veto stats. |

## Dormant-here matrix (honest)

On a Linux host without `pyautogui`/`paramiko`/`pywinrm`/`cv2`, the desktop/HAL and
live VM backends are **code-complete but dormant** — verified here via the
**simulated VM backend + dry-run + guarded repo/shell + offline Ollama**. The gate,
bridge, conscience veto, Λ(t) feedback, and HTTP surface all run and are tested
offline. They light up the moment the drivers/OS are present.

## 📚 Related
- [`AUREON_OPERATOR_SWITCHBOARD.md`](AUREON_OPERATOR_SWITCHBOARD.md) — the cognition/switchboard this grounds
- [`ORGANISM_CONNECTOME.md`](ORGANISM_CONNECTOME.md) — how the body joins the organism
- [`../runbooks/PRODUCTION_GRADE.md`](../runbooks/PRODUCTION_GRADE.md) — the strict tier this holds to
- `aureon/operator/grounded_action.py` · `aureon/operator/local_action_bridge.py` · `aureon/queen/queen_conscience.py` · `aureon/core/hnc_live_daemon.py`
