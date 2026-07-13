# Swarm Search Mapping Stress Audit

Status: `swarm_search_fabric_active`
Mode: `real_repo_evidence_no_synthetic_capture`

This maps Aureon's search, browser mapping, and data-capture systems into one fabric.
It is real-repo evidence only and does not add trading gates or broker authority.

## Summary
- `source_system_count`: `11`
- `wired_source_system_count`: `11`
- `browser_mapping_count`: `4`
- `browser_mapping_present_count`: `4`
- `data_capture_artifact_count`: `15`
- `data_capture_artifact_present_count`: `15`
- `fabric_event_count`: `120`
- `keyword_search_active`: `True`
- `latest_keyword_query`: `keyword_search`
- `keyword_scanned_file_count`: `325`
- `keyword_match_file_count`: `1`
- `keyword_match_count`: `6`
- `online_research_cinema_active`: `True`
- `online_research_topic`: `Harmonic Nexus Score`
- `online_research_source_count`: `5`
- `online_research_frame_count`: `6`
- `online_research_motion_ready`: `True`
- `online_research_paper_created`: `True`
- `research_coding_artifacts_created`: `True`
- `research_generated_file_count`: `6`
- `research_metacognition_active`: `True`
- `metacognitive_concept_count`: `8`
- `metacognitive_understood_concept_count`: `8`
- `metacognitive_route_count`: `8`
- `metacognitive_ready_route_count`: `7`
- `metacognitive_unknown_count`: `2`
- `metacognitive_test_action_count`: `3`
- `metacognitive_understanding_published`: `True`
- `phase_seen_count`: `14`
- `phase_expected_count`: `27`
- `thoughtbus_receiving`: `True`
- `mycelium_receiving`: `True`
- `live_search_capture_active`: `True`
- `no_synthetic_capture`: `True`
- `no_new_trading_gate`: `True`
- `no_external_mutation`: `True`

## Source Systems
- Agent Core web search/browser/capture: `wired` -> `aureon/autonomous/aureon_agent_core.py`
- Local keyword reader: `wired` -> `aureon/search/local_keyword_search.py`
- Online research cinema: `wired` -> `aureon/search/online_research_cinema.py`
- Research metacognition: `wired` -> `aureon/search/research_metacognition.py`
- Queen online researcher: `wired` -> `aureon/queen/queen_online_researcher.py`
- Queen research engine: `wired` -> `aureon/utils/aureon_queen_research_engine.py`
- Queen research neuron: `wired` -> `aureon/utils/aureon_queen_research_neuron.py`
- Self research loop: `wired` -> `aureon/queen/self_research_loop.py`
- Research corpus index: `wired` -> `aureon/queen/research_corpus_index.py`
- Frontend Queen Hive browser: `wired` -> `frontend/src/core/queenHiveBrowser.ts`
- Swarm search fabric: `wired` -> `aureon/search/swarm_search_fabric.py`

## Next Actions
- `query_received`: run producer aureon_agent_core through the real search/capture path
- `source_selected`: run producer aureon_agent_core through the real search/capture path
- `result_captured`: run producer aureon_agent_core through the real search/capture path
- `page_fetch_requested`: run producer aureon_agent_core through the real search/capture path
- `page_fetched`: run producer aureon_agent_core through the real search/capture path
- `browser_opened`: run producer aureon_agent_core through the real search/capture path
- `screen_captured`: run producer aureon_agent_core through the real search/capture path
- `keyword_scan_requested`: run producer aureon_agent_core through the real search/capture path
- `keyword_file_read`: run producer aureon_agent_core through the real search/capture path
- `keyword_match_captured`: run producer aureon_agent_core through the real search/capture path
- `keyword_scan_completed`: run producer aureon_agent_core through the real search/capture path
- `knowledge_search_requested`: run producer aureon_agent_core through the real search/capture path
- `knowledge_search_completed`: run producer aureon_agent_core through the real search/capture path
