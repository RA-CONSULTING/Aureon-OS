# Logic-train audit — every decision site, one canonical field

**Connected: False** — 34/83 relevant sites wired (41.0%)

* scanned: 1089 modules
* authority (define the field): 7
* producers (compute a local field): 27
* consumers (decide on a field): 49
* inert (name it, decide nothing): 1006

## Still unwired

| module | role | reason |
|---|---|---|
| `aureon/alignment/unified_directive.py` | consumer | measured unwired at pin time (role=consumer, reads a field, no canonical wire) |
| `aureon/autonomous/aureon_dynamic_prompt_filter.py` | consumer | measured unwired at pin time (role=consumer, reads a field, no canonical wire) |
| `aureon/autonomous/aureon_face_app.py` | producer | measured unwired at pin time (role=producer, reads a field, no canonical wire) |
| `aureon/autonomous/aureon_gold_capital_intelligence_company.py` | producer | measured unwired at pin time (role=producer, reads a field, no canonical wire) |
| `aureon/bridges/aureon_ui_bridge.py` | consumer | measured unwired at pin time (role=consumer, reads a field, no canonical wire) |
| `aureon/core/cognitive_dashboard.py` | consumer | measured unwired at pin time (role=consumer, reads a field, no canonical wire) |
| `aureon/core/goal_execution_engine.py` | producer | measured unwired at pin time (role=producer, reads a field, no canonical wire) |
| `aureon/core/integrated_cognitive_system.py` | producer | cognitive integrator computes its own Λ instead of reading the shared one |
| `aureon/exchanges/capital_cfd_trader.py` | producer | LIVE ORDER PATH — venue adapter with a private coherence figure; highest priority |
| `aureon/harmonic/auris_voice_filter.py` | producer | measured unwired at pin time (role=producer, reads a field, no canonical wire) |
| `aureon/harmonic/dj_resonance.py` | consumer | measured unwired at pin time (role=consumer, reads a field, no canonical wire) |
| `aureon/observer/benchmark.py` | consumer | measured unwired at pin time (role=consumer, reads a field, no canonical wire) |
| `aureon/observer/fitter.py` | producer | measured unwired at pin time (role=producer, reads a field, no canonical wire) |
| `aureon/observer/harmonic_observer.py` | producer | observer core computes a real local field; should publish it as a sub-field |
| `aureon/observer/historical_backtest.py` | producer | backtest harness — fixture surface, expected to stay off the live field |
| `aureon/observer/run.py` | consumer | measured unwired at pin time (role=consumer, reads a field, no canonical wire) |
| `aureon/observer/wave_predictor.py` | consumer | measured unwired at pin time (role=consumer, reads a field, no canonical wire) |
| `aureon/operator/local_action_bridge.py` | consumer | measured unwired at pin time (role=consumer, reads a field, no canonical wire) |
| `aureon/portfolio/aureon_profit_now.py` | consumer | LIVE ORDER PATH — measured unwired at pin time (role=consumer, reads a field, no canonical wire) |
| `aureon/queen/being_model.py` | producer | measured unwired at pin time (role=producer, reads a field, no canonical wire) |
| `aureon/queen/meaning_resolver.py` | consumer | measured unwired at pin time (role=consumer, reads a field, no canonical wire) |
| `aureon/queen/queen_cognitive_action_planner.py` | consumer | measured unwired at pin time (role=consumer, reads a field, no canonical wire) |
| `aureon/queen/queen_coherence_mandala.py` | consumer | measured unwired at pin time (role=consumer, reads a field, no canonical wire) |
| `aureon/queen/queen_prose_composer.py` | producer | measured unwired at pin time (role=producer, reads a field, no canonical wire) |
| `aureon/queen/queen_sentience_integration.py` | consumer | measured unwired at pin time (role=consumer, reads a field, no canonical wire) |
| `aureon/queen/self_enhancement_engine.py` | consumer | measured unwired at pin time (role=consumer, reads a field, no canonical wire) |
| `aureon/queen/temporal_ground.py` | producer | temporal grounding computes a private Λ echo |
| `aureon/status.py` | producer | status surface reports a field it computes rather than the canonical one |
| `aureon/swarm_motion/as_above_so_below.py` | consumer | measured unwired at pin time (role=consumer, reads a field, no canonical wire) |
| `aureon/swarm_motion/love_stream.py` | consumer | measured unwired at pin time (role=consumer, reads a field, no canonical wire) |
| `aureon/swarm_motion/swarm_hive.py` | consumer | measured unwired at pin time (role=consumer, reads a field, no canonical wire) |
| `aureon/trading/aureon_live.py` | consumer | LIVE ORDER PATH — measured unwired at pin time (role=consumer, reads a field, no canonical wire) |
| `aureon/trading/aureon_mesh_live.py` | consumer | LIVE ORDER PATH — measured unwired at pin time (role=consumer, reads a field, no canonical wire) |
| `aureon/trading/aureon_multi_pair_live.py` | consumer | LIVE ORDER PATH — measured unwired at pin time (role=consumer, reads a field, no canonical wire) |
| `aureon/trading/aureon_the_play.py` | consumer | LIVE ORDER PATH — measured unwired at pin time (role=consumer, reads a field, no canonical wire) |
| `aureon/trading/aureon_the_play_old.py` | consumer | LIVE ORDER PATH — measured unwired at pin time (role=consumer, reads a field, no canonical wire) |
| `aureon/trading/aureon_unified_ecosystem.py` | consumer | LIVE ORDER PATH — measured unwired at pin time (role=consumer, reads a field, no canonical wire) |
| `aureon/trading/micro_profit_labyrinth.py` | consumer | LIVE ORDER PATH — measured unwired at pin time (role=consumer, reads a field, no canonical wire) |
| `aureon/trading/parallel_strategy_unity.py` | consumer | LIVE ORDER PATH — measured unwired at pin time (role=consumer, reads a field, no canonical wire) |
| `aureon/utils/aureon_miner.py` | consumer | measured unwired at pin time (role=consumer, reads a field, no canonical wire) |
| `aureon/vault/auris_metacognition.py` | consumer | measured unwired at pin time (role=consumer, reads a field, no canonical wire) |
| `aureon/vault/casimir_quantifier.py` | consumer | measured unwired at pin time (role=consumer, reads a field, no canonical wire) |
| `aureon/vault/hnc_deployer.py` | consumer | measured unwired at pin time (role=consumer, reads a field, no canonical wire) |
| `aureon/vault/voice/aureon_personas.py` | consumer | measured unwired at pin time (role=consumer, reads a field, no canonical wire) |
| `aureon/vault/voice/choice_gate.py` | consumer | measured unwired at pin time (role=consumer, reads a field, no canonical wire) |
| `aureon/vault/voice/document_artifact_skill.py` | consumer | measured unwired at pin time (role=consumer, reads a field, no canonical wire) |
| `aureon/vault/voice/goal_dispatch_bridge.py` | consumer | measured unwired at pin time (role=consumer, reads a field, no canonical wire) |
| `aureon/vault/voice/vault_voice.py` | consumer | measured unwired at pin time (role=consumer, reads a field, no canonical wire) |
| `aureon/vault/voice/whole_knowledge_voice.py` | consumer | measured unwired at pin time (role=consumer, reads a field, no canonical wire) |

---

Every site in the repository that acts on a harmonic field value is discovered by reading the tree, classified by role, and checked for its wire to the one canonical field. Producers must publish their local field so the whole body can see it; consumers must read the canonical layer rather than a private number. What is still unwired is named in the report and pinned in source, so a new unwired decision site fails the audit and the remaining gap cannot be misplaced. It is a source-level wiring proof, not a measurement of how strongly the field sways one decision, and it is NOT a claim about any person.
