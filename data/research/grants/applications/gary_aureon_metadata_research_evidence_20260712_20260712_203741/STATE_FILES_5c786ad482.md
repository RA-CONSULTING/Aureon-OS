# Runtime State Files (Repo-Root JSONs)

Several JSON files live in the repository root because they are runtime-state
artifacts opened via **relative paths** by 20+ modules across `aureon/`,
`scripts/`, and `tests/`. They must remain in the repo root so that scripts
executed from the project root resolve them correctly.

> ⚠️ **Do not move these files** without updating every `open("<name>.json")`
> reference across the codebase. Moving them would silently break learning
> persistence, seed data, and integration tests.

| File | Role | Primary owners |
|------|------|----------------|
| [`adaptive_learning_history.json`](../adaptive_learning_history.json) | Adaptive-learning event log (seeded + appended at runtime) | `aureon/utils/learned_analytics_reset.py`, `scripts/python/learning_analytics_cli.py`, `aureon/utils/full_market_trainer.py` |
| [`bot_army_catalog.json`](../bot_army_catalog.json) | Catalog of tracked bot fleets used by scanners and simulations | `aureon/bots/sniper_training_simulation.py`, `aureon/scanners/ira_sniper_mode.py`, `aureon/simulation/nuclear_crypto_reality.py` |
| [`brain_predictions_history.json`](../brain_predictions_history.json) | Historical prediction log for the miner brain / hive mind | `aureon/utils/aureon_miner_brain.py`, `aureon/utils/aureon_queen_hive_mind.py`, `aureon/analytics/historical_pattern_hunter.py` |
| [`miner_brain_knowledge.json`](../miner_brain_knowledge.json) | Persistent knowledge base for the miner brain | `aureon/utils/aureon_miner_brain.py`, `aureon/wisdom/irish_patriot_scouts.py`, `aureon/command_centers/aureon_command_center_ui.py` |

## Related Runtime State (written by scripts, not always committed)

These files are **generated at runtime** in the current working directory by
specific modules. They may or may not be committed at any given point:

| File | Generator |
|------|-----------|
| `ghost_dance_state.json` | `aureon/wisdom/aureon_ghost_dance_protocol.py` |
| `comprehensive_entity_database.json` | `aureon/scanners/aureon_strategic_warfare_scanner.py` |
| `planetary_harmonic_network.json` | `aureon/harmonic/aureon_planetary_harmonic_sweep.py` |
| `strategic_warfare_intelligence.json` | `aureon/scanners/aureon_strategic_warfare_scanner.py` |
| `harmonic_counter_frequency_map.json` | `aureon/harmonic/aureon_harmonic_counter_frequency.py` |
| `bot_census_registry.json`, `bot_cultural_attribution.json`, `historical_manipulation_evidence.json`, `manipulation_patterns_across_time.json`, `planetary_intelligence_report.json` | `aureon/bridges/aureon_planetary_intelligence_hub.py` |
| `deep_money_flow_analysis.json`, `money_flow_timeline.json` | `aureon/analytics/aureon_historical_manipulation_hunter.py` |

## Future Refactor

A future cleanup could centralize these under `data/state/` with a
`STATE_DIR` environment variable / module constant that every consumer
reads, eliminating the CWD coupling. That refactor is deferred to avoid
touching 20+ call sites in this reorganization pass.
