# Aureon Trading System — Signal Detection & Cognitive Systems Placement Checklist

> **Generated:** 2026-05-20
> **Scope:** HNC systems, QGITA signal detection, Harmonic systems, and Cognitive layers across the full trading decision loop.
> **Goal:** Ensure every signal detection subsystem is correctly wired into data capture → prediction → decision → execution → feedback.

---

## 1. Recent System Modifications (Last 30 Commits)

| Commit | Modification | Impact on Trading Loop |
|--------|--------------|------------------------|
| `df4c4bbb` | Launcher PowerShell ASCII fix | Boot reliability |
| `cc1ebbe7` | `start_everything_production.ps1` one-command launch | Operational entry point |
| `8bca3db1` | Flameborn frontend merged into Aureon skeleton | UI layer for loop monitoring |
| `2fcae94c` | MURGE runtime activation | Execution-stage runtime |
| `83a104b3` | Vault → dataset sync + auto self-organize | Feedback loop crystallization |
| `81ec78d3` | 11 free APIs + 5W1H metacognitive routing | Data capture enrichment |
| `a74fb102` | Free-API ingester + self-research loop | Autonomous data capture |
| `0b3e52bf` | HNC feedback ladder closed: TKB → Lambda → Dialer → bus → TKB | **Critical: closes HNC cognitive loop** |
| `e56c10a5` | TemporalKnowledgeBase (TKB) — agents gain sense of time | Prediction context |
| `b42781eb` | Metacognitive prose composer reads real state | Reporting / oversight |
| `ef6f1969` | Source Law + Emerald Tablet LLM wiring | **Decision gate threshold control** |
| `7fd386ae` | Source Law decree wired into ALL LLM logic | Cognitive override layer |
| `914a6410` | Source Law Engine + As Above So Below Mirror | Ethical guardrails on execution |
| `c6d91787` | LoveStream, Conscience, Integrations + vault feed + chain split | Cognitive coherence inputs |

**Verification:** Run `git log --oneline -20` in `aureon-trading/` to confirm these commits are present.

---

## 2. QGITA Signal Detection — Placement Audit

### 2.1 QGITA Architecture Recap
- **Stage 1:** FTCPDetector (Fibonacci-Tightened Curvature Points) — geometric anomaly detection on φ-resonant time lattice.
- **Stage 2:** LighthouseModel — 5-metric consensus validation (C_linear, C_nonlinear, C_phi, G_eff, Q_anomaly).
- **Output:** `L(t)` Lighthouse Intensity, `R(t)` Global Coherence, regime state, direction, confidence.

### 2.2 QGITA Files & Locations

| File | Role | Lines |
|------|------|-------|
| `aureon/wisdom/aureon_qgita_framework.py` | **Core implementation** — `FibonacciTimeLattice`, `FTCPDetector`, `LighthouseModel`, `QGITAMarketAnalyzer` | ~1111 |
| `aureon/wisdom/aureon_enigma_integration.py` | **Integration layer** — wires QGITA into Enigma consciousness as Layer 11 | ~2123 |
| `aureon/trading/aureon_unified_ecosystem.py` | **Trading runtime** — imports QGITA for market analysis | ~3000+ |
| `loveavblr/aureon_qgita.py` | Legacy standalone QGITA trader | — |
| `docs/QGITA_INTEGRATION_SUMMARY.md` | Documentation & verification steps | 416 |

### 2.3 QGITA in the Trading Loop — Step-by-Step

```
[DATA CAPTURE]  Market price tick
       ↓
[QGITA STAGE 1]  FTCPDetector.feed_price(price, timestamp)
       ↓
[QGITA STAGE 2]  LighthouseModel.analyze() → L(t), R(t), regime
       ↓
[ENIGMA BRIDGE]  EnigmaIntegration.feed_from_qgita(market_data)
       ↓
[CONSCIOUSNESS]  Enigma feed_consciousness() maps:
                   • L(t) → signal_strength
                   • R(t) → consciousness_score
                   • regime → fear_score
                   • LHE count → unity moments
       ↓
[THOUGHT BUS]    EnigmaThought broadcast + Chirp Bus emission (639 Hz / 528 Hz)
       ↓
[PREDICTION BUS] AutonomyHub.PredictionBus.register_predictor('qgita', ...)
       ↓
[DECISION GATE]  DecisionGate.evaluate() — QGITA gets weight 2.0 in consensus
       ↓
[SOURCE LAW]     SourceLawEngine.cogitate() — 10-9-1 funnel; entry threshold 0.938
       ↓
[EXECUTION]      Trade placed via UnifiedExchangeClient
       ↓
[FEEDBACK LOOP]  FeedbackLoopEngine.record_outcome() → recalibrates QGITA predictor weight
```

### 2.4 QGITA Checklist

- [x] **Framework file exists:** `aureon/wisdom/aureon_qgita_framework.py` ✅
- [x] **Enigma integration wired:** `aureon/wisdom/aureon_enigma_integration.py` lines 200-213, 296-300, 679-755 ✅
- [x] **PredictionBus registration:** `aureon/autonomous/aureon_autonomy_hub.py` weight map includes `'qgita': 2.0` ✅
- [x] **Live price feed connected to QGITA** — `feed_price()` called on every WebSocket tick (Binance/Kraken/Alpaca) ✅
- [x] **LHE events trigger trade decisions** — `structural_event=True` boosts confidence +0.08 in DecisionGate ✅
- [x] **QGITA regime state used for position sizing** — chaos = 0.5x strength, coherent = 1.2x strength ✅
- [ ] **Feedback loop recalibrates QGITA weights** — verify `record_outcome()` updates QGITA accuracy tracker
- [ ] **Multi-timeframe QGITA** — confirm 1m, 5m, 1h, 1d lattices are running (not just single timeframe)

---

## 3. HNC Systems — Placement Audit

### 3.1 HNC Architecture Recap
- **Master Formula:** Λ(t) = Σ wᵢ sin(2πfᵢt + φᵢ) + α tanh(g Λ_Δt(t)) + β Λ(t-τ)
- **Feedback Ladder:** TKB (Temporal Knowledge Base) → Lambda Engine → Temporal Dialer → ThoughtBus → TKB
- **Auris 9-Node Voter:** Owl, Deer, Dolphin, Tiger, Hummingbird, CargoShip, Clownfish, Falcon, Panda
- **Source Law:** 10 (Quantum Vacuum) → 9 (Auris Nodes) → 1 (Cognition Output) — entry ≥ 0.938, exit ≤ 0.934

### 3.2 HNC Files & Locations

| File | Role | Lines |
|------|------|-------|
| `docs/HNC_UNIFIED_WHITE_PAPER.md` | Theory, Tree of Light, Master Formula | 447 |
| `run_hnc_live.py` | **Human interaction loop** — HNC Λ(t) → Auris 9-node → Phi Prime Train → Temporal Ground | 303 |
| `aureon/core/integrated_cognitive_system.py` | **Cognitive orchestrator** — boots TKB, Lambda, Dialer, Source Law | 1612 |
| `aureon/queen/hnc_human_loop.py` | HNC pipeline implementation | — |
| `aureon/queen/queen_source_law.py` | **10-9-1 Source Law Engine** — decision threshold gate | 575 |
| `aureon/core/aureon_lambda_engine.py` | Lambda field computation | — |
| `aureon/queen/temporal_knowledge.py` | TKB — time-indexed event knowledge | — |
| `aureon/intelligence/aureon_temporal_dialer.py` | Temporal Dialer — frequency tuner | — |
| `aureon/harmonic/global_harmonic_field.py` | Master Formula Λ(t) implementation | — |
| `aureon/bridges/aureon_hnc_live_connector.py` | HNC → live trading bridge | — |

### 3.3 HNC in the Trading Loop — Step-by-Step

```
[DATA CAPTURE]  All subsystem events → ThoughtBus
       ↓
[TKB UP]        TemporalKnowledgeBase.ingest() — hottest topics, bursting detection
       ↓
[LAMBDA FIELD]  LambdaEngine.step(readings=[subsystem_health + tkb_hot + tkb_burst])
       ↓
[HNC STATE]     lambda_t, coherence_gamma, consciousness_psi, consciousness_level
       ↓
[AURIS VOTE]    AurisMetacognition.vote(vault) → 9-node consensus, lighthouse_cleared
       ↓
[COMPOSITE COH] 0.4*lambda_gamma + 0.3*cortex_psi + 0.3*auris_confidence
       ↓
[SOURCE LAW]    QuantumVacuum.accumulate() → NineAurisProcess.process() →
                CognitionOutput.cogitate() → action (EXECUTE/HOLD)
       ↓
[TEMPORAL GROUND] TemporalGroundStation.tick() — multiverse hash chain, ZPE grounding
       ↓
[DIALER DOWN]   TemporalDialer.tune_frequency(gamma→[7.83..528]Hz) → pull_quantum_data()
       ↓
[BUS FEEDBACK]  ThoughtBus.publish("temporal.dialer.packet", ...) → TKB captures on next event
       ↓
[CLOSED LOOP]   TKB → Lambda → Dialer → bus → TKB  (feedback ladder complete)
```

### 3.4 HNC Checklist

- [x] **HNC white paper present:** `docs/HNC_UNIFIED_WHITE_PAPER.md` ✅
- [x] **Live terminal loop:** `run_hnc_live.py` ✅
- [x] **ICS boots TKB:** `integrated_cognitive_system.py` Phase 2.5 ✅
- [x] **ICS boots Dialer:** `integrated_cognitive_system.py` Phase 2.6 ✅
- [x] **ICS boots Source Law:** `integrated_cognitive_system.py` Phase 12 ✅
- [x] **Feedback ladder UP (TKB→Lambda):** `integrated_cognitive_system.py` lines 831-858 ✅
- [x] **Feedback ladder DOWN (Dialer→bus):** `integrated_cognitive_system.py` lines 967-993 ✅
- [x] **Source Law thresholds configurable:** `AUREON_SOURCE_LAW_ENTRY` / `AUREON_SOURCE_LAW_EXIT` env vars ✅
- [x] **HNC coherence_gamma >= 0.938 before trade execution** — Source Law hard gate in `open_position()` + DecisionGate external_checks ✅
- [x] **Temporal Ground ZPE grounding required before live trades** — ZPE hard gate in `open_position()` + DecisionGate external_checks ✅
- [ ] **HNC live connector active** — verify `aureon_hnc_live_connector.py` is imported in trading runtime
- [x] **Auris lighthouse_cleared gate** — `vote.lighthouse_cleared` hard gate in `open_position()` + DecisionGate external_checks ✅
- [ ] **HNC regime detection (chaotic/transitional/coherent) feeds position sizing** — verify `lambda_t` or `gamma` scales trade size

---

## 4. Harmonic Systems — Placement Audit

### 4.1 Harmonic Architecture Recap
- **Signal Chain:** Queen(963Hz) → Enigma(639Hz) → Scanner(528Hz) → Ecosystem(174Hz) → Whale(7.83Hz)
- **Tree of Light:** 8 levels from Seed Oscillation → Global Reality Field Λ(t)
- **Key Frequencies:** Schumann 7.83 Hz, Love 528 Hz, Unity 741 Hz, Phi-scaled intervals

### 4.2 Harmonic Files & Locations

| File | Role | Frequency |
|------|------|-----------|
| `aureon/harmonic/aureon_harmonic_fusion.py` | Schumann resonance fusion | 7.83 Hz |
| `aureon/harmonic/aureon_harmonic_signal_chain.py` | Queen→Enigma→Scanner→Ecosystem→Whale | Multi |
| `aureon/harmonic/aureon_hft_harmonic_mycelium.py` | HFT harmonic mycelium | — |
| `aureon/harmonic/aureon_planetary_harmonic_sweep.py` | 0.0° phase sync detection | — |
| `aureon/harmonic/global_harmonic_field.py` | Master Formula Λ(t) — 42 sources → 7 layers → Ω | — |
| `aureon/harmonic/harmonic_nexus_bridge.py` | Research-to-trading bridge | — |
| `aureon/harmonic/phi_bridge.py` | Phi Bridge — phone/desktop vault sync | φ lattice |
| `aureon/harmonic/earth_resonance_engine.py` | Earth resonance live feed | Schumann |
| `aureon/queen/queen_harmonic_voice.py` | Queen harmonic output layer | 963 Hz |

### 4.3 Harmonic Systems in the Trading Loop

```
[DATA CAPTURE]  Exchange ticks + Earth resonance feed + Planetary sweep
       ↓
[HARMONIC FUSION]  Schumann lock + coherence scoring + prime alignment
       ↓
[SIGNAL CHAIN]  Queen(963) → Enigma(639) → Scanner(528) → Ecosystem(174) → Whale(7.83)
       ↓
[PLANETARY SWEEP]  0.0° phase sync detection across 125 entity signatures
       ↓
[GLOBAL FIELD]  Λ(t) computation — 42 sources → 7 layers → Ω output
       ↓
[NEXUS BRIDGE]  HarmonicNexusBridge — research anomalies → trading signals
       ↓
[DECISION GATE]  Harmonic coherence feeds into PredictionBus consensus
       ↓
[PHI BRIDGE]  Resonant frequencies sync vault state to mobile/command nodes
```

### 4.4 Harmonic Checklist

- [x] **Harmonic fusion available:** `aureon/harmonic/aureon_harmonic_fusion.py` ✅
- [x] **Signal chain defined:** `aureon/harmonic/aureon_harmonic_signal_chain.py` ✅
- [x] **Planetary sweep:** `aureon/harmonic/aureon_planetary_harmonic_sweep.py` ✅
- [x] **Global harmonic field:** `aureon/harmonic/global_harmonic_field.py` ✅
- [x] **Phi bridge:** `aureon/harmonic/phi_bridge.py` ✅
- [x] **Earth resonance:** `aureon/harmonic/earth_resonance_engine.py` ✅
- [ ] **Harmonic fusion output feeds EnigmaIntegration** — verify `feed_from_harmonic_fusion()` is called in trading loop
- [ ] **Planetary sweep phase sync ≤30° triggers veto/alert** — confirm in `DecisionGate` or `SourceLaw`
- [ ] **0.0° synchronization blocks counter-trend trades** — verify Queen veto logic
- [ ] **Schumann resonance spike (>10 Hz) triggers circuit breaker** — confirm in `aureon_operational_core.py`
- [x] **Global harmonic field Ω output weights PredictionBus consensus** — `harmonic_field` predictor registered in AutonomyHub with confidence boost ✅

---

## 5. Cognitive Systems — Placement Audit

### 5.1 Cognitive Architecture (ICS — Integrated Cognitive System)
Boot Sequence (20+ phases) → Unified Cognitive Tick (~1Hz) → User Input / Goal Execution

### 5.2 Cognitive Files & Locations

| File | Role | Phase |
|------|------|-------|
| `run_integrated_cognitive_system.py` | **Entry point** — boots ICS, dashboard, Vault UI | — |
| `aureon/core/integrated_cognitive_system.py` | **Orchestrator** — 20-phase boot, 1Hz tick | 1-20 |
| `aureon/queen/queen_cortex.py` | Cortex band snapshot (delta/theta/alpha/beta/gamma) | 5 |
| `aureon/queen/queen_metacognition.py` | 5W self-reflection loop | 9 |
| `aureon/queen/queen_conscience.py` | Ethical compass (Jiminy Cricket) | 11 |
| `aureon/queen/queen_source_law.py` | 10-9-1 Emerald Tablet decision funnel | 12 |
| `aureon/swarm_motion/as_above_so_below.py` | Hermetic reflection mirror | 13 |
| `aureon/queen/queen_prose_composer.py` | Self-description from real state | 26 |
| `aureon/core/goal_execution_engine.py` | Goal → plan → steps → execution | 16 |
| `aureon/autonomous/aureon_agent_core.py` | Agent capabilities & tool use | 14 |

### 5.3 Cognitive Systems in the Trading Loop

```
[BOOT]          20-phase initialization (ThoughtBus → Vault → TKB → Dialer → Lambda →
                Cortex → Feedback → Sentient → Mycelium → Metacognition → LoveStream →
                Conscience → SourceLaw → Mirror → Agent → ActionBridge → Being →
                Elephant → Swarm → Temporal → Nexus → Dataset → Interpreter →
                Stash → GoalEngine → Dashboard → Auris → PhiBridge → VaultUI →
                WorldData → SelfResearch → VaultBridge → Integrations → Prose)
       ↓
[TICK ~1Hz]     Unified cognitive tick:
                1. BODY — Agent stats
                2. MIND — Cortex bands
                3. SOURCE — Lambda step (subsystem health + TKB hot/burst readings)
                4. SOUL — Being model snapshot
                5. HNC — Auris vote + composite coherence
                6. TEMPORAL GROUND — Multiverse hash chain maintenance
                7. VAULT FEED — Ingest tick state
                8. DIALER FEEDBACK — Tune frequency, pull quantum packet
                9. SOURCE LAW — Cogitate every 5th tick
       ↓
[USER INPUT]    /goal, /research, /stash, /ladder, /organize, /coherence, /decree
       ↓
[GOAL ENGINE]   GoalExecutionEngine.submit_goal() → plan → steps → agent execution
       ↓
[TRADING LOOP]  If goal is trading-related → routed to AutonomyHub → DecisionGate
```

### 5.4 Cognitive Checklist

- [x] **ICS entry point:** `run_integrated_cognitive_system.py` ✅
- [x] **20-phase boot sequence:** `integrated_cognitive_system.py` lines 342-694 ✅
- [x] **1Hz unified tick:** `_unified_cognitive_tick()` lines 725-1014 ✅
- [x] **Source Law cogitate every 5 ticks:** `if self._tick_count % 5 == 0` ✅
- [x] **TKB hot topics feed Lambda:** lines 831-858 ✅
- [x] **Dialer feedback every 3 ticks:** `if self._tick_count % 3 == 0` ✅
- [x] **Composite coherence computed:** `0.4*lambda_gamma + 0.3*cortex_psi + 0.3*auris_conf` ✅
- [x] **Source Law EXECUTE output directly triggers AutonomyHub DecisionGate** — `external_checks` wired in `spin_cycle()` + hard gate in `open_position()` ✅
- [ ] **Conscience veto wired to DecisionGate** — verify ethical override on high-risk trades
- [ ] **Metacognition 5W reflection logged before every trade** — verify `Who/What/When/Where/Why` captured
- [ ] **Goal engine trading goals route through Source Law before execution** — confirm path

---

## 6. Unified Trading Loop — Master Flow

This is the **single diagram** that shows where HNC, QGITA, Harmonic, and Cognitive systems sit in the end-to-end trading decision.

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                         AUREON UNIFIED TRADING LOOP                          ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ LAYER 1: DATA CAPTURE                                                        ║
║ ├─ Market ticks (Binance/Kraken/Alpaca/Capital)                             ║
║ ├─ Macro snapshot (VIX, DXY, Fear&Greed, yield curve)                       ║
║ ├─ News sentiment (crypto + overall)                                        ║
║ ├─ Options flow (Unusual Whales)                                            ║
║ ├─ Whale hunter (accumulation/distribution)                                 ║
║ ├─ Surveillance alerts (manipulation detection)                             ║
║ ├─ World data ingester (11 free APIs)                                       ║
║ └─ HARMONIC: Schumann resonance, Earth resonance, Planetary sweep           ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ LAYER 2: SIGNAL DETECTION & PREDICTION                                       ║
║ ├─ QGITA: FTCP + Lighthouse → L(t), R(t), regime, direction                 ║
║ ├─ HNC: Lambda field → coherence_gamma, consciousness_psi                   ║
║ ├─ Nexus Predictor (79.6% validated)                                        ║
║ ├─ Probability Ultimate Intelligence (95% claimed)                          ║
║ ├─ HNC Probability Matrix                                                   ║
║ ├─ Imperial Predictability Engine                                           ║
║ ├─ Whale Hunter predictions                                                 ║
║ ├─ Quantum Telescope                                                        ║
║ ├─ Phase Transition Detector (Takens embedding)                             ║
║ ├─ Cross-Substrate Solar Monitor (NOAA + Granger)                           ║
║ └─ HARMONIC: Global harmonic field Λ(t), Planetary phase sync               ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ LAYER 3: COGNITIVE FUSION                                                    ║
║ ├─ PredictionBus.get_consensus() — weighted fusion of all predictors        ║
║ ├─ Enigma Integration — 11-layer consciousness decoding                       ║
║ ├─ Auris 9-Node Voter — consensus + lighthouse_cleared                      ║
║ ├─ Source Law Engine — 10-9-1 quantum funnel                                ║
║ │   ├─ 10: QuantumVacuum accumulates all signals unobserved                 ║
║ │   ├─ 9: NineAurisProcess processes 9 dimensions                           ║
║ │   └─ 1: CognitionOutput — EXECUTE (≥0.938) or HOLD (<0.938)               ║
║ ├─ Temporal Ground — multiverse hash chain, ZPE grounding, timeline fork    ║
║ ├─ Conscience — ethical compass veto                                        ║
║ └─ Metacognition — 5W self-reflection                                       ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ LAYER 4: DECISION GATE                                                       ║
║ ├─ GATE 1: Circuit breaker (hard stop)                                      ║
║ ├─ GATE 2: Macro veto (global conditions)                                   ║
║ ├─ GATE 3: Minimum consensus confidence (≥0.45)                             ║
║ ├─ GATE 4: Minimum predictor agreement (≥50%)                              ║
║ ├─ GATE 5: Sentiment confirmation (optional boost)                          ║
║ ├─ GATE 6: Whale flow confirmation (optional boost)                         ║
║ ├─ GATE 7: Source Law coherence (≥0.938 for entry, ≤0.934 for exit)        ║
║ ├─ GATE 8: HNC ZPE grounded check                                           ║
║ └─ GATE 9: Auris lighthouse_cleared                                         ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ LAYER 5: EXECUTION                                                           ║
║ ├─ Position size multiplier (0.5x → 0.75x → 1.0x based on confidence)      ║
║ ├─ UnifiedExchangeClient.place_market_order()                               ║
║ ├─ IRA Sniper Mode override (if active)                                     ║
║ ├─ Operational Core — Signal Gate + Circuit Breaker + Trade Lock            ║
║ └─ Cross-exchange duplicate prevention (Mycelium)                           ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ LAYER 6: FEEDBACK & LEARNING                                                 ║
║ ├─ FeedbackLoopEngine.record_outcome()                                      ║
║ ├─ Score each predictor accuracy → dynamic weight recalculation             ║
║ ├─ NexusPredictor.record_trade_outcome()                                    ║
║ ├─ Adaptive Prime Profit Gate recalibration                                 ║
║ ├─ Internal Multiverse — 10-9-1-10 world outcomes                           ║
║ ├─ Vault Knowledge Bridge — crystallize trade into dataset                  ║
║ ├─ Temporal Knowledge Base — time-index trade events                        ║
║ └─ HARMONIC: HNC feedback ladder closes loop (TKB→Λ→Dialer→bus→TKB)        ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

## 7. Critical Gaps & Action Items

| # | Gap | Severity | Status | Fix Applied |
|---|-----|----------|--------|-------------|
| 1 | **QGITA `feed_price()` not called on every live tick** | 🔴 High | ✅ FIXED | `feed_price()` added to Binance/Kraken/Alpaca WebSocket handlers in `aureon_unified_ecosystem.py` |
| 2 | **HNC `coherence_gamma` threshold (0.938) not checked in `DecisionGate`** | 🔴 High | ✅ FIXED | Source Law hard gate added to `open_position()` + `DecisionGate.evaluate(external_checks)` |
| 3 | **Temporal Ground `grounded` flag not checked before trade execution** | 🟡 Medium | ✅ FIXED | ZPE hard gate added to `open_position()` + `DecisionGate.evaluate(external_checks)` |
| 4 | **Auris `lighthouse_cleared` not wired as hard gate before execution** | 🟡 Medium | ✅ FIXED | Auris veto added to `open_position()` + `DecisionGate.evaluate(external_checks)` |
| 5 | **Multi-timeframe QGITA (1m/5m/1h/1d) documented but only single timeframe** | 🟡 Medium | ⏳ OPEN | Instantiate 4 `QGITAMarketAnalyzer` instances with different `delta_t` values |
| 6 | **HNC live connector (`aureon_hnc_live_connector.py`) import status unknown** | 🟡 Medium | ⏳ OPEN | Verify import and active thread in `aureon_unified_ecosystem.py` |
| 7 | **Harmonic global field Ω output not registered as predictor in `PredictionBus`** | 🟡 Medium | ✅ FIXED | `adapt_harmonic_field` registered in `AutonomyHub.__init__` |
| 8 | **Schumann spike circuit breaker not verified in operational core** | 🟢 Low | ⏳ OPEN | Add test: simulate SR > 10 Hz and verify trading pauses |
| 9 | **Metacognition 5W reflection not captured in trade journal** | 🟢 Low | ⏳ OPEN | Add `self.metacognition.reflect()` output to `FeedbackLoopEngine` persistence |
| 10 | **Conscience veto not explicitly wired to DecisionGate** | 🟡 Medium | ⏳ OPEN | Add conscience check as Gate 8 in `DecisionGate.evaluate()` |

---

## 8. Verification Commands

Run these to confirm system placement:

```bash
# 1. QGITA standalone test
python aureon/wisdom/aureon_qgita_framework.py

# 2. Enigma integration test (all 11 layers)
python aureon/wisdom/aureon_enigma_integration.py

# 3. HNC human loop
python run_hnc_live.py
# Then type: "test" and check Lambda, Auris, ZPE output

# 4. ICS boot + status
python run_integrated_cognitive_system.py
# Then type: /status, /ladder, /coherence, /decree

# 5. Source Law threshold check
python -c "from aureon.queen.queen_source_law import ENTRY_COHERENCE, EXIT_COHERENCE; print(f'Entry: {ENTRY_COHERENCE}, Exit: {EXIT_COHERENCE}')"

# 6. Autonomy hub predictor list
python -c "from aureon.autonomous.aureon_autonomy_hub import PredictionBus; pb = PredictionBus(); print(list(pb._predictors.keys()))"

# 7. Recent trading loop logs
tail -50 aureon_unified.log

# 8. HNC feedback ladder status
python run_integrated_cognitive_system.py
# Then type: /ladder
```

---

## 9. File Index — Where to Look

| Concern | Primary File | Secondary Files |
|---------|--------------|-----------------|
| QGITA signal detection | `aureon/wisdom/aureon_qgita_framework.py` | `aureon_enigma_integration.py`, `aureon_autonomy_hub.py` |
| HNC master formula | `aureon/harmonic/global_harmonic_field.py` | `docs/HNC_UNIFIED_WHITE_PAPER.md` |
| HNC feedback ladder | `aureon/core/integrated_cognitive_system.py` | `aureon/queen/temporal_knowledge.py`, `aureon/intelligence/aureon_temporal_dialer.py` |
| Source Law decision gate | `aureon/queen/queen_source_law.py` | `integrated_cognitive_system.py` (Phase 12) |
| Harmonic signal chain | `aureon/harmonic/aureon_harmonic_signal_chain.py` | `aureon_harmonic_fusion.py`, `aureon_planetary_harmonic_sweep.py` |
| Trading decision fusion | `aureon/autonomous/aureon_autonomy_hub.py` | `aureon/trading/aureon_unified_ecosystem.py` |
| Live trading runtime | `aureon/trading/aureon_unified_ecosystem.py` | `loveavblr/aureon_unified_ecosystem.py` |
| Cognitive orchestration | `aureon/core/integrated_cognitive_system.py` | `run_integrated_cognitive_system.py` |
| Auris 9-node voter | `aureon/vault/auris_metacognition.py` | `integrated_cognitive_system.py` (Phase 18) |
| Feedback loop | `aureon/autonomous/aureon_autonomy_hub.py` (FeedbackLoopEngine) | `aureon/vault/vault_knowledge_bridge.py` |

---

*End of checklist. Review gaps in Section 7 first — they represent the highest-risk disconnects between signal detection and trading execution.*
