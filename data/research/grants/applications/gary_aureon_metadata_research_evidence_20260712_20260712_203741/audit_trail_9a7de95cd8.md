# Integration Audit Trail

#aureon #vault #hnc #audit

Snapshots of the Ollama + Obsidian bridges, emitted by `IntegrationAuditTrail.run_full_audit()`.


## 2026-04-14 10:51:36Z — Integration Audit

#aureon #vault #hnc #audit

- **audit_id**: `audit_20260414T105130`
- **when**: `1776163890.3110964`
- **iso_time**: `2026-04-14T10:51:30.311096Z`
- **total**: `12`
- **passed**: `12`
- **failed**: `0`
- **health_ratio**: `1.0`
### results
- {'name': 'ollama.bridge.import', 'category': 'ollama', 'description': 'aureon.integrations.ollama.OllamaBridge imports', 'passed': True, 'detail': '{"class": "aureon.integrations.ollama.OllamaBridge"}', 'duration_ms': 0.0, 'timestamp': 1776163890.3110964, 'iso_time': '2026-04-14T10:51:30.311096Z'}
- {'name': 'ollama.adapter.import', 'category': 'ollama', 'description': 'aureon.integrations.ollama.OllamaLLMAdapter imports', 'passed': True, 'detail': '{"class": "aureon.integrations.ollama.OllamaLLMAdapter"}', 'duration_ms': 0.0, 'timestamp': 1776163890.3110964, 'iso_time': '2026-04-14T10:51:30.311096Z'}
- {'name': 'ollama.bridge.health', 'category': 'ollama', 'description': 'OllamaBridge reaches /api/version (graceful on unreachable)', 'passed': True, 'detail': '{"reachable": true, "base_url": "http://localhost:11434", "model_count": 0, "running_count": 0, "version": "0.20.7"}', 'duration_ms': 2074.538, 'timestamp': 1776163890.3110964, 'iso_time': '2026-04-14T10:51:30.311096Z'}
- {'name': 'ollama.adapter.interface', 'category': 'ollama', 'description': 'OllamaLLMAdapter implements aureon.inhouse_ai.LLMAdapter', 'passed': True, 'detail': '{"adapter": "OllamaLLMAdapter", "interface": "LLMAdapter"}', 'duration_ms': 0.0, 'timestamp': 1776163892.3856344, 'iso_time': '2026-04-14T10:51:32.385634Z'}
- {'name': 'obsidian.bridge.import', 'category': 'obsidian', 'description': 'aureon.integrations.obsidian.ObsidianBridge imports', 'passed': True, 'detail': '{"class": "aureon.integrations.obsidian.ObsidianBridge"}', 'duration_ms': 0.0, 'timestamp': 1776163892.3856344, 'iso_time': '2026-04-14T10:51:32.385634Z'}
- {'name': 'obsidian.sink.import', 'category': 'obsidian', 'description': 'aureon.integrations.obsidian.ObsidianSink imports', 'passed': True, 'detail': '{"class": "aureon.integrations.obsidian.ObsidianSink"}', 'duration_ms': 0.0, 'timestamp': 1776163892.3856344, 'iso_time': '2026-04-14T10:51:32.385634Z'}
- {'name': 'obsidian.bridge.health', 'category': 'obsidian', 'description': 'ObsidianBridge picks a mode (local_rest OR filesystem)', 'passed': True, 'detail': '{"reachable": true, "mode": "filesystem", "vault_path": "C:\\\\Users\\\\user\\\\AureonObsidianVault", "note_count": 1}', 'duration_ms': 2.524, 'timestamp': 1776163892.3856344, 'iso_time': '2026-04-14T10:51:32.385634Z'}
- {'name': 'obsidian.sink.health', 'category': 'obsidian', 'description': 'ObsidianSink status reports reachable + mode', 'passed': True, 'detail': '{"bridge_mode": "filesystem", "reachable": true, "utterances_written": 0, "ticks_written": 0, "audits_written": 0}', 'duration_ms': 0.0, 'timestamp': 1776163892.3881586, 'iso_time': '2026-04-14T10:51:32.388159Z'}
- {'name': 'wiring.vault_voice_loop', 'category': 'wiring', 'description': 'AureonVault + SelfFeedbackLoop + VoiceEngine all import together', 'passed': True, 'detail': '{"vault_size": 0, "loop_id": "b9132dd0", "voice_engine_ready": true, "thought_stream_ready": true}', 'duration_ms': 4034.516, 'timestamp': 1776163892.3881586, 'iso_time': '2026-04-14T10:51:32.388159Z'}
- {'name': 'pathway.neural_mapper', 'category': 'pathway', 'description': 'NeuralPathwayMapper builds a non-empty graph', 'passed': True, 'detail': '{"nodes": 80, "edges": 86, "clusters": 11}', 'duration_ms': 474.894, 'timestamp': 1776163896.422675, 'iso_time': '2026-04-14T10:51:36.422675Z'}
- {'name': 'inhouse_ai.llm_adapter', 'category': 'inhouse_ai', 'description': 'aureon.inhouse_ai.llm_adapter still importable', 'passed': True, 'detail': '{"module": "aureon.inhouse_ai.llm_adapter"}', 'duration_ms': 0.0, 'timestamp': 1776163896.8975692, 'iso_time': '2026-04-14T10:51:36.897569Z'}
- {'name': 'inhouse_ai.orchestrator', 'category': 'inhouse_ai', 'description': 'aureon.inhouse_ai.orchestrator.OpenMultiAgent still exists', 'passed': True, 'detail': '{"class": "aureon.inhouse_ai.orchestrator.OpenMultiAgent"}', 'duration_ms': 0.0, 'timestamp': 1776163896.8975692, 'iso_time': '2026-04-14T10:51:36.897569Z'}


## 2026-04-14 11:33:15Z — Integration Audit

#aureon #vault #hnc #audit

- **audit_id**: `audit_20260414T113308`
- **when**: `1776166388.8291156`
- **iso_time**: `2026-04-14T11:33:08.829116Z`
- **total**: `12`
- **passed**: `12`
- **failed**: `0`
- **health_ratio**: `1.0`
### results
- {'name': 'ollama.bridge.import', 'category': 'ollama', 'description': 'aureon.integrations.ollama.OllamaBridge imports', 'passed': True, 'detail': '{"class": "aureon.integrations.ollama.OllamaBridge"}', 'duration_ms': 0.0, 'timestamp': 1776166388.8291156, 'iso_time': '2026-04-14T11:33:08.829116Z'}
- {'name': 'ollama.adapter.import', 'category': 'ollama', 'description': 'aureon.integrations.ollama.OllamaLLMAdapter imports', 'passed': True, 'detail': '{"class": "aureon.integrations.ollama.OllamaLLMAdapter"}', 'duration_ms': 0.0, 'timestamp': 1776166388.8291156, 'iso_time': '2026-04-14T11:33:08.829116Z'}
- {'name': 'ollama.bridge.health', 'category': 'ollama', 'description': 'OllamaBridge reaches /api/version (graceful on unreachable)', 'passed': True, 'detail': '{"reachable": true, "base_url": "http://localhost:11434", "model_count": 0, "running_count": 0, "version": "0.20.7"}', 'duration_ms': 2042.595, 'timestamp': 1776166388.8291156, 'iso_time': '2026-04-14T11:33:08.829116Z'}
- {'name': 'ollama.adapter.interface', 'category': 'ollama', 'description': 'OllamaLLMAdapter implements aureon.inhouse_ai.LLMAdapter', 'passed': True, 'detail': '{"adapter": "OllamaLLMAdapter", "interface": "LLMAdapter"}', 'duration_ms': 0.0, 'timestamp': 1776166390.8717103, 'iso_time': '2026-04-14T11:33:10.871710Z'}
- {'name': 'obsidian.bridge.import', 'category': 'obsidian', 'description': 'aureon.integrations.obsidian.ObsidianBridge imports', 'passed': True, 'detail': '{"class": "aureon.integrations.obsidian.ObsidianBridge"}', 'duration_ms': 0.0, 'timestamp': 1776166390.8717103, 'iso_time': '2026-04-14T11:33:10.871710Z'}
- {'name': 'obsidian.sink.import', 'category': 'obsidian', 'description': 'aureon.integrations.obsidian.ObsidianSink imports', 'passed': True, 'detail': '{"class": "aureon.integrations.obsidian.ObsidianSink"}', 'duration_ms': 0.0, 'timestamp': 1776166390.8717103, 'iso_time': '2026-04-14T11:33:10.871710Z'}
- {'name': 'obsidian.bridge.health', 'category': 'obsidian', 'description': 'ObsidianBridge picks a mode (local_rest OR filesystem)', 'passed': True, 'detail': '{"reachable": true, "mode": "filesystem", "vault_path": "C:\\\\Users\\\\user\\\\AureonObsidianVault", "note_count": 6}', 'duration_ms': 3.033, 'timestamp': 1776166390.8717103, 'iso_time': '2026-04-14T11:33:10.871710Z'}
- {'name': 'obsidian.sink.health', 'category': 'obsidian', 'description': 'ObsidianSink status reports reachable + mode', 'passed': True, 'detail': '{"bridge_mode": "filesystem", "reachable": true, "utterances_written": 0, "ticks_written": 0, "audits_written": 0}', 'duration_ms': 0.0, 'timestamp': 1776166390.8747437, 'iso_time': '2026-04-14T11:33:10.874744Z'}
- {'name': 'wiring.vault_voice_loop', 'category': 'wiring', 'description': 'AureonVault + SelfFeedbackLoop + VoiceEngine all import together', 'passed': True, 'detail': '{"vault_size": 0, "loop_id": "1aa5be6b", "voice_engine_ready": true, "thought_stream_ready": true}', 'duration_ms': 4017.224, 'timestamp': 1776166390.8747437, 'iso_time': '2026-04-14T11:33:10.874744Z'}
- {'name': 'pathway.neural_mapper', 'category': 'pathway', 'description': 'NeuralPathwayMapper builds a non-empty graph', 'passed': True, 'detail': '{"nodes": 80, "edges": 86, "clusters": 11}', 'duration_ms': 504.457, 'timestamp': 1776166394.8919673, 'iso_time': '2026-04-14T11:33:14.891967Z'}
- {'name': 'inhouse_ai.llm_adapter', 'category': 'inhouse_ai', 'description': 'aureon.inhouse_ai.llm_adapter still importable', 'passed': True, 'detail': '{"module": "aureon.inhouse_ai.llm_adapter"}', 'duration_ms': 0.0, 'timestamp': 1776166395.3964248, 'iso_time': '2026-04-14T11:33:15.396425Z'}
- {'name': 'inhouse_ai.orchestrator', 'category': 'inhouse_ai', 'description': 'aureon.inhouse_ai.orchestrator.OpenMultiAgent still exists', 'passed': True, 'detail': '{"class": "aureon.inhouse_ai.orchestrator.OpenMultiAgent"}', 'duration_ms': 0.0, 'timestamp': 1776166395.3964248, 'iso_time': '2026-04-14T11:33:15.396425Z'}


## 2026-04-14 11:50:02Z — Integration Audit

#aureon #vault #hnc #audit

- **audit_id**: `audit_20260414T114956`
- **when**: `1776167396.426549`
- **iso_time**: `2026-04-14T11:49:56.426549Z`
- **total**: `12`
- **passed**: `12`
- **failed**: `0`
- **health_ratio**: `1.0`
### results
- {'name': 'ollama.bridge.import', 'category': 'ollama', 'description': 'aureon.integrations.ollama.OllamaBridge imports', 'passed': True, 'detail': '{"class": "aureon.integrations.ollama.OllamaBridge"}', 'duration_ms': 0.0, 'timestamp': 1776167396.426549, 'iso_time': '2026-04-14T11:49:56.426549Z'}
- {'name': 'ollama.adapter.import', 'category': 'ollama', 'description': 'aureon.integrations.ollama.OllamaLLMAdapter imports', 'passed': True, 'detail': '{"class": "aureon.integrations.ollama.OllamaLLMAdapter"}', 'duration_ms': 0.0, 'timestamp': 1776167396.426549, 'iso_time': '2026-04-14T11:49:56.426549Z'}
- {'name': 'ollama.bridge.health', 'category': 'ollama', 'description': 'OllamaBridge reaches /api/version (graceful on unreachable)', 'passed': True, 'detail': '{"reachable": true, "base_url": "http://localhost:11434", "model_count": 0, "running_count": 0, "version": "0.20.7"}', 'duration_ms': 2033.356, 'timestamp': 1776167396.426549, 'iso_time': '2026-04-14T11:49:56.426549Z'}
- {'name': 'ollama.adapter.interface', 'category': 'ollama', 'description': 'OllamaLLMAdapter implements aureon.inhouse_ai.LLMAdapter', 'passed': True, 'detail': '{"adapter": "OllamaLLMAdapter", "interface": "LLMAdapter"}', 'duration_ms': 0.505, 'timestamp': 1776167398.4599054, 'iso_time': '2026-04-14T11:49:58.459905Z'}
- {'name': 'obsidian.bridge.import', 'category': 'obsidian', 'description': 'aureon.integrations.obsidian.ObsidianBridge imports', 'passed': True, 'detail': '{"class": "aureon.integrations.obsidian.ObsidianBridge"}', 'duration_ms': 0.0, 'timestamp': 1776167398.46041, 'iso_time': '2026-04-14T11:49:58.460410Z'}
- {'name': 'obsidian.sink.import', 'category': 'obsidian', 'description': 'aureon.integrations.obsidian.ObsidianSink imports', 'passed': True, 'detail': '{"class": "aureon.integrations.obsidian.ObsidianSink"}', 'duration_ms': 0.0, 'timestamp': 1776167398.46041, 'iso_time': '2026-04-14T11:49:58.460410Z'}
- {'name': 'obsidian.bridge.health', 'category': 'obsidian', 'description': 'ObsidianBridge picks a mode (local_rest OR filesystem)', 'passed': True, 'detail': '{"reachable": true, "mode": "filesystem", "vault_path": "C:\\\\Users\\\\user\\\\AureonObsidianVault", "note_count": 6}', 'duration_ms': 0.53, 'timestamp': 1776167398.46041, 'iso_time': '2026-04-14T11:49:58.460410Z'}
- {'name': 'obsidian.sink.health', 'category': 'obsidian', 'description': 'ObsidianSink status reports reachable + mode', 'passed': True, 'detail': '{"bridge_mode": "filesystem", "reachable": true, "utterances_written": 0, "ticks_written": 0, "audits_written": 0}', 'duration_ms': 0.0, 'timestamp': 1776167398.46094, 'iso_time': '2026-04-14T11:49:58.460940Z'}
- {'name': 'wiring.vault_voice_loop', 'category': 'wiring', 'description': 'AureonVault + SelfFeedbackLoop + VoiceEngine all import together', 'passed': True, 'detail': '{"vault_size": 0, "loop_id": "5091120a", "voice_engine_ready": true, "thought_stream_ready": true}', 'duration_ms': 4043.482, 'timestamp': 1776167398.46094, 'iso_time': '2026-04-14T11:49:58.460940Z'}
- {'name': 'pathway.neural_mapper', 'category': 'pathway', 'description': 'NeuralPathwayMapper builds a non-empty graph', 'passed': True, 'detail': '{"nodes": 80, "edges": 86, "clusters": 11}', 'duration_ms': 425.328, 'timestamp': 1776167402.504422, 'iso_time': '2026-04-14T11:50:02.504422Z'}
- {'name': 'inhouse_ai.llm_adapter', 'category': 'inhouse_ai', 'description': 'aureon.inhouse_ai.llm_adapter still importable', 'passed': True, 'detail': '{"module": "aureon.inhouse_ai.llm_adapter"}', 'duration_ms': 0.0, 'timestamp': 1776167402.9297497, 'iso_time': '2026-04-14T11:50:02.929750Z'}
- {'name': 'inhouse_ai.orchestrator', 'category': 'inhouse_ai', 'description': 'aureon.inhouse_ai.orchestrator.OpenMultiAgent still exists', 'passed': True, 'detail': '{"class": "aureon.inhouse_ai.orchestrator.OpenMultiAgent"}', 'duration_ms': 0.0, 'timestamp': 1776167402.9297497, 'iso_time': '2026-04-14T11:50:02.929750Z'}


## 2026-04-14 11:59:42Z — Integration Audit

#aureon #vault #hnc #audit

- **audit_id**: `audit_20260414T115935`
- **when**: `1776167975.1384137`
- **iso_time**: `2026-04-14T11:59:35.138414Z`
- **total**: `12`
- **passed**: `12`
- **failed**: `0`
- **health_ratio**: `1.0`
### results
- {'name': 'ollama.bridge.import', 'category': 'ollama', 'description': 'aureon.integrations.ollama.OllamaBridge imports', 'passed': True, 'detail': '{"class": "aureon.integrations.ollama.OllamaBridge"}', 'duration_ms': 0.0, 'timestamp': 1776167975.1384137, 'iso_time': '2026-04-14T11:59:35.138414Z'}
- {'name': 'ollama.adapter.import', 'category': 'ollama', 'description': 'aureon.integrations.ollama.OllamaLLMAdapter imports', 'passed': True, 'detail': '{"class": "aureon.integrations.ollama.OllamaLLMAdapter"}', 'duration_ms': 0.0, 'timestamp': 1776167975.1384137, 'iso_time': '2026-04-14T11:59:35.138414Z'}
- {'name': 'ollama.bridge.health', 'category': 'ollama', 'description': 'OllamaBridge reaches /api/version (graceful on unreachable)', 'passed': True, 'detail': '{"reachable": true, "base_url": "http://localhost:11434", "model_count": 0, "running_count": 0, "version": "0.20.7"}', 'duration_ms': 2024.089, 'timestamp': 1776167975.1384137, 'iso_time': '2026-04-14T11:59:35.138414Z'}
- {'name': 'ollama.adapter.interface', 'category': 'ollama', 'description': 'OllamaLLMAdapter implements aureon.inhouse_ai.LLMAdapter', 'passed': True, 'detail': '{"adapter": "OllamaLLMAdapter", "interface": "LLMAdapter"}', 'duration_ms': 0.0, 'timestamp': 1776167977.162503, 'iso_time': '2026-04-14T11:59:37.162503Z'}
- {'name': 'obsidian.bridge.import', 'category': 'obsidian', 'description': 'aureon.integrations.obsidian.ObsidianBridge imports', 'passed': True, 'detail': '{"class": "aureon.integrations.obsidian.ObsidianBridge"}', 'duration_ms': 0.0, 'timestamp': 1776167977.162503, 'iso_time': '2026-04-14T11:59:37.162503Z'}
- {'name': 'obsidian.sink.import', 'category': 'obsidian', 'description': 'aureon.integrations.obsidian.ObsidianSink imports', 'passed': True, 'detail': '{"class": "aureon.integrations.obsidian.ObsidianSink"}', 'duration_ms': 0.0, 'timestamp': 1776167977.162503, 'iso_time': '2026-04-14T11:59:37.162503Z'}
- {'name': 'obsidian.bridge.health', 'category': 'obsidian', 'description': 'ObsidianBridge picks a mode (local_rest OR filesystem)', 'passed': True, 'detail': '{"reachable": true, "mode": "filesystem", "vault_path": "C:\\\\Users\\\\user\\\\AureonObsidianVault", "note_count": 9}', 'duration_ms': 2.533, 'timestamp': 1776167977.162503, 'iso_time': '2026-04-14T11:59:37.162503Z'}
- {'name': 'obsidian.sink.health', 'category': 'obsidian', 'description': 'ObsidianSink status reports reachable + mode', 'passed': True, 'detail': '{"bridge_mode": "filesystem", "reachable": true, "utterances_written": 0, "ticks_written": 0, "audits_written": 0}', 'duration_ms': 1.001, 'timestamp': 1776167977.165036, 'iso_time': '2026-04-14T11:59:37.165036Z'}
- {'name': 'wiring.vault_voice_loop', 'category': 'wiring', 'description': 'AureonVault + SelfFeedbackLoop + VoiceEngine all import together', 'passed': True, 'detail': '{"vault_size": 0, "loop_id": "26a31805", "voice_engine_ready": true, "thought_stream_ready": true}', 'duration_ms': 4028.014, 'timestamp': 1776167977.166037, 'iso_time': '2026-04-14T11:59:37.166037Z'}
- {'name': 'pathway.neural_mapper', 'category': 'pathway', 'description': 'NeuralPathwayMapper builds a non-empty graph', 'passed': True, 'detail': '{"nodes": 80, "edges": 86, "clusters": 11}', 'duration_ms': 410.224, 'timestamp': 1776167981.194051, 'iso_time': '2026-04-14T11:59:41.194051Z'}
- {'name': 'inhouse_ai.llm_adapter', 'category': 'inhouse_ai', 'description': 'aureon.inhouse_ai.llm_adapter still importable', 'passed': True, 'detail': '{"module": "aureon.inhouse_ai.llm_adapter"}', 'duration_ms': 0.0, 'timestamp': 1776167981.6042747, 'iso_time': '2026-04-14T11:59:41.604275Z'}
- {'name': 'inhouse_ai.orchestrator', 'category': 'inhouse_ai', 'description': 'aureon.inhouse_ai.orchestrator.OpenMultiAgent still exists', 'passed': True, 'detail': '{"class": "aureon.inhouse_ai.orchestrator.OpenMultiAgent"}', 'duration_ms': 0.0, 'timestamp': 1776167981.6042747, 'iso_time': '2026-04-14T11:59:41.604275Z'}


## 2026-04-14 12:01:21Z — Integration Audit

#aureon #vault #hnc #audit

- **audit_id**: `audit_20260414T120115`
- **when**: `1776168075.2503345`
- **iso_time**: `2026-04-14T12:01:15.250335Z`
- **total**: `12`
- **passed**: `12`
- **failed**: `0`
- **health_ratio**: `1.0`
### results
- {'name': 'ollama.bridge.import', 'category': 'ollama', 'description': 'aureon.integrations.ollama.OllamaBridge imports', 'passed': True, 'detail': '{"class": "aureon.integrations.ollama.OllamaBridge"}', 'duration_ms': 0.0, 'timestamp': 1776168075.2503345, 'iso_time': '2026-04-14T12:01:15.250335Z'}
- {'name': 'ollama.adapter.import', 'category': 'ollama', 'description': 'aureon.integrations.ollama.OllamaLLMAdapter imports', 'passed': True, 'detail': '{"class": "aureon.integrations.ollama.OllamaLLMAdapter"}', 'duration_ms': 0.0, 'timestamp': 1776168075.2503345, 'iso_time': '2026-04-14T12:01:15.250335Z'}
- {'name': 'ollama.bridge.health', 'category': 'ollama', 'description': 'OllamaBridge reaches /api/version (graceful on unreachable)', 'passed': True, 'detail': '{"reachable": true, "base_url": "http://localhost:11434", "model_count": 0, "running_count": 0, "version": "0.20.7"}', 'duration_ms': 2048.067, 'timestamp': 1776168075.2503345, 'iso_time': '2026-04-14T12:01:15.250335Z'}
- {'name': 'ollama.adapter.interface', 'category': 'ollama', 'description': 'OllamaLLMAdapter implements aureon.inhouse_ai.LLMAdapter', 'passed': True, 'detail': '{"adapter": "OllamaLLMAdapter", "interface": "LLMAdapter"}', 'duration_ms': 0.0, 'timestamp': 1776168077.298401, 'iso_time': '2026-04-14T12:01:17.298401Z'}
- {'name': 'obsidian.bridge.import', 'category': 'obsidian', 'description': 'aureon.integrations.obsidian.ObsidianBridge imports', 'passed': True, 'detail': '{"class": "aureon.integrations.obsidian.ObsidianBridge"}', 'duration_ms': 0.0, 'timestamp': 1776168077.298401, 'iso_time': '2026-04-14T12:01:17.298401Z'}
- {'name': 'obsidian.sink.import', 'category': 'obsidian', 'description': 'aureon.integrations.obsidian.ObsidianSink imports', 'passed': True, 'detail': '{"class": "aureon.integrations.obsidian.ObsidianSink"}', 'duration_ms': 0.0, 'timestamp': 1776168077.298401, 'iso_time': '2026-04-14T12:01:17.298401Z'}
- {'name': 'obsidian.bridge.health', 'category': 'obsidian', 'description': 'ObsidianBridge picks a mode (local_rest OR filesystem)', 'passed': True, 'detail': '{"reachable": true, "mode": "filesystem", "vault_path": "C:\\\\Users\\\\user\\\\AureonObsidianVault", "note_count": 9}', 'duration_ms': 1.049, 'timestamp': 1776168077.298401, 'iso_time': '2026-04-14T12:01:17.298401Z'}
- {'name': 'obsidian.sink.health', 'category': 'obsidian', 'description': 'ObsidianSink status reports reachable + mode', 'passed': True, 'detail': '{"bridge_mode": "filesystem", "reachable": true, "utterances_written": 0, "ticks_written": 0, "audits_written": 0}', 'duration_ms': 0.0, 'timestamp': 1776168077.2994504, 'iso_time': '2026-04-14T12:01:17.299450Z'}
- {'name': 'wiring.vault_voice_loop', 'category': 'wiring', 'description': 'AureonVault + SelfFeedbackLoop + VoiceEngine all import together', 'passed': True, 'detail': '{"vault_size": 0, "loop_id": "92aafa36", "voice_engine_ready": true, "thought_stream_ready": true}', 'duration_ms': 4089.144, 'timestamp': 1776168077.2994504, 'iso_time': '2026-04-14T12:01:17.299450Z'}
- {'name': 'pathway.neural_mapper', 'category': 'pathway', 'description': 'NeuralPathwayMapper builds a non-empty graph', 'passed': True, 'detail': '{"nodes": 80, "edges": 86, "clusters": 11}', 'duration_ms': 406.301, 'timestamp': 1776168081.3885942, 'iso_time': '2026-04-14T12:01:21.388594Z'}
- {'name': 'inhouse_ai.llm_adapter', 'category': 'inhouse_ai', 'description': 'aureon.inhouse_ai.llm_adapter still importable', 'passed': True, 'detail': '{"module": "aureon.inhouse_ai.llm_adapter"}', 'duration_ms': 0.0, 'timestamp': 1776168081.7948956, 'iso_time': '2026-04-14T12:01:21.794896Z'}
- {'name': 'inhouse_ai.orchestrator', 'category': 'inhouse_ai', 'description': 'aureon.inhouse_ai.orchestrator.OpenMultiAgent still exists', 'passed': True, 'detail': '{"class": "aureon.inhouse_ai.orchestrator.OpenMultiAgent"}', 'duration_ms': 0.0, 'timestamp': 1776168081.7948956, 'iso_time': '2026-04-14T12:01:21.794896Z'}


## 2026-04-14 12:06:18Z — Integration Audit

#aureon #vault #hnc #audit

- **audit_id**: `audit_20260414T120612`
- **when**: `1776168372.2047384`
- **iso_time**: `2026-04-14T12:06:12.204738Z`
- **total**: `12`
- **passed**: `12`
- **failed**: `0`
- **health_ratio**: `1.0`
### results
- {'name': 'ollama.bridge.import', 'category': 'ollama', 'description': 'aureon.integrations.ollama.OllamaBridge imports', 'passed': True, 'detail': '{"class": "aureon.integrations.ollama.OllamaBridge"}', 'duration_ms': 0.0, 'timestamp': 1776168372.2047384, 'iso_time': '2026-04-14T12:06:12.204738Z'}
- {'name': 'ollama.adapter.import', 'category': 'ollama', 'description': 'aureon.integrations.ollama.OllamaLLMAdapter imports', 'passed': True, 'detail': '{"class": "aureon.integrations.ollama.OllamaLLMAdapter"}', 'duration_ms': 0.0, 'timestamp': 1776168372.2047384, 'iso_time': '2026-04-14T12:06:12.204738Z'}
- {'name': 'ollama.bridge.health', 'category': 'ollama', 'description': 'OllamaBridge reaches /api/version (graceful on unreachable)', 'passed': True, 'detail': '{"reachable": true, "base_url": "http://localhost:11434", "model_count": 0, "running_count": 0, "version": "0.20.7"}', 'duration_ms': 2050.887, 'timestamp': 1776168372.2047384, 'iso_time': '2026-04-14T12:06:12.204738Z'}
- {'name': 'ollama.adapter.interface', 'category': 'ollama', 'description': 'OllamaLLMAdapter implements aureon.inhouse_ai.LLMAdapter', 'passed': True, 'detail': '{"adapter": "OllamaLLMAdapter", "interface": "LLMAdapter"}', 'duration_ms': 0.161, 'timestamp': 1776168374.255625, 'iso_time': '2026-04-14T12:06:14.255625Z'}
- {'name': 'obsidian.bridge.import', 'category': 'obsidian', 'description': 'aureon.integrations.obsidian.ObsidianBridge imports', 'passed': True, 'detail': '{"class": "aureon.integrations.obsidian.ObsidianBridge"}', 'duration_ms': 0.0, 'timestamp': 1776168374.2557864, 'iso_time': '2026-04-14T12:06:14.255786Z'}
- {'name': 'obsidian.sink.import', 'category': 'obsidian', 'description': 'aureon.integrations.obsidian.ObsidianSink imports', 'passed': True, 'detail': '{"class": "aureon.integrations.obsidian.ObsidianSink"}', 'duration_ms': 0.0, 'timestamp': 1776168374.2557864, 'iso_time': '2026-04-14T12:06:14.255786Z'}
- {'name': 'obsidian.bridge.health', 'category': 'obsidian', 'description': 'ObsidianBridge picks a mode (local_rest OR filesystem)', 'passed': True, 'detail': '{"reachable": true, "mode": "filesystem", "vault_path": "C:\\\\Users\\\\user\\\\AureonObsidianVault", "note_count": 9}', 'duration_ms': 1.061, 'timestamp': 1776168374.2557864, 'iso_time': '2026-04-14T12:06:14.255786Z'}
- {'name': 'obsidian.sink.health', 'category': 'obsidian', 'description': 'ObsidianSink status reports reachable + mode', 'passed': True, 'detail': '{"bridge_mode": "filesystem", "reachable": true, "utterances_written": 0, "ticks_written": 0, "audits_written": 0}', 'duration_ms': 0.0, 'timestamp': 1776168374.2568471, 'iso_time': '2026-04-14T12:06:14.256847Z'}
- {'name': 'wiring.vault_voice_loop', 'category': 'wiring', 'description': 'AureonVault + SelfFeedbackLoop + VoiceEngine all import together', 'passed': True, 'detail': '{"vault_size": 0, "loop_id": "9aa375e2", "voice_engine_ready": true, "thought_stream_ready": true}', 'duration_ms': 4039.406, 'timestamp': 1776168374.2568471, 'iso_time': '2026-04-14T12:06:14.256847Z'}
- {'name': 'pathway.neural_mapper', 'category': 'pathway', 'description': 'NeuralPathwayMapper builds a non-empty graph', 'passed': True, 'detail': '{"nodes": 80, "edges": 86, "clusters": 11}', 'duration_ms': 449.975, 'timestamp': 1776168378.296253, 'iso_time': '2026-04-14T12:06:18.296253Z'}
- {'name': 'inhouse_ai.llm_adapter', 'category': 'inhouse_ai', 'description': 'aureon.inhouse_ai.llm_adapter still importable', 'passed': True, 'detail': '{"module": "aureon.inhouse_ai.llm_adapter"}', 'duration_ms': 0.0, 'timestamp': 1776168378.7462282, 'iso_time': '2026-04-14T12:06:18.746228Z'}
- {'name': 'inhouse_ai.orchestrator', 'category': 'inhouse_ai', 'description': 'aureon.inhouse_ai.orchestrator.OpenMultiAgent still exists', 'passed': True, 'detail': '{"class": "aureon.inhouse_ai.orchestrator.OpenMultiAgent"}', 'duration_ms': 0.0, 'timestamp': 1776168378.7462282, 'iso_time': '2026-04-14T12:06:18.746228Z'}


## 2026-05-13 17:58:04Z — Integration Audit

#aureon #vault #hnc #audit

- **audit_id**: `audit_20260513T175801`
- **when**: `1778695081.5264657`
- **iso_time**: `2026-05-13T17:58:01.526466Z`
- **total**: `12`
- **passed**: `12`
- **failed**: `0`
- **health_ratio**: `1.0`
### results
- {'name': 'ollama.bridge.import', 'category': 'ollama', 'description': 'aureon.integrations.ollama.OllamaBridge imports', 'passed': True, 'detail': '{"class": "aureon.integrations.ollama.OllamaBridge"}', 'duration_ms': 0.0, 'timestamp': 1778695081.5264657, 'iso_time': '2026-05-13T17:58:01.526466Z'}
- {'name': 'ollama.adapter.import', 'category': 'ollama', 'description': 'aureon.integrations.ollama.OllamaLLMAdapter imports', 'passed': True, 'detail': '{"class": "aureon.integrations.ollama.OllamaLLMAdapter"}', 'duration_ms': 0.0, 'timestamp': 1778695081.5264657, 'iso_time': '2026-05-13T17:58:01.526466Z'}
- {'name': 'ollama.bridge.health', 'category': 'ollama', 'description': 'OllamaBridge reaches /api/version (graceful on unreachable)', 'passed': True, 'detail': '{"reachable": true, "base_url": "http://localhost:11434", "model_count": 2, "running_count": 0, "version": "0.23.3"}', 'duration_ms': 2042.247, 'timestamp': 1778695081.5264657, 'iso_time': '2026-05-13T17:58:01.526466Z'}
- {'name': 'ollama.adapter.interface', 'category': 'ollama', 'description': 'OllamaLLMAdapter implements aureon.inhouse_ai.LLMAdapter', 'passed': True, 'detail': '{"adapter": "OllamaLLMAdapter", "interface": "LLMAdapter"}', 'duration_ms': 0.0, 'timestamp': 1778695083.5687122, 'iso_time': '2026-05-13T17:58:03.568712Z'}
- {'name': 'obsidian.bridge.import', 'category': 'obsidian', 'description': 'aureon.integrations.obsidian.ObsidianBridge imports', 'passed': True, 'detail': '{"class": "aureon.integrations.obsidian.ObsidianBridge"}', 'duration_ms': 0.0, 'timestamp': 1778695083.5687122, 'iso_time': '2026-05-13T17:58:03.568712Z'}
- {'name': 'obsidian.sink.import', 'category': 'obsidian', 'description': 'aureon.integrations.obsidian.ObsidianSink imports', 'passed': True, 'detail': '{"class": "aureon.integrations.obsidian.ObsidianSink"}', 'duration_ms': 0.0, 'timestamp': 1778695083.5687122, 'iso_time': '2026-05-13T17:58:03.568712Z'}
- {'name': 'obsidian.bridge.health', 'category': 'obsidian', 'description': 'ObsidianBridge picks a mode (local_rest OR filesystem)', 'passed': True, 'detail': '{"reachable": true, "mode": "filesystem", "vault_path": "C:\\\\Users\\\\user\\\\AureonObsidianVault", "note_count": 10}', 'duration_ms': 5.822, 'timestamp': 1778695083.5687122, 'iso_time': '2026-05-13T17:58:03.568712Z'}
- {'name': 'obsidian.sink.health', 'category': 'obsidian', 'description': 'ObsidianSink status reports reachable + mode', 'passed': True, 'detail': '{"bridge_mode": "filesystem", "reachable": true, "utterances_written": 0, "ticks_written": 0, "audits_written": 0}', 'duration_ms': 0.0, 'timestamp': 1778695083.5745342, 'iso_time': '2026-05-13T17:58:03.574534Z'}
- {'name': 'wiring.vault_voice_loop', 'category': 'wiring', 'description': 'AureonVault + SelfFeedbackLoop + VoiceEngine all import together', 'passed': True, 'detail': '{"vault_size": 0, "loop_id": "7a812282", "voice_engine_ready": true, "thought_stream_ready": true}', 'duration_ms': 0.0, 'timestamp': 1778695083.5745342, 'iso_time': '2026-05-13T17:58:03.574534Z'}
- {'name': 'pathway.neural_mapper', 'category': 'pathway', 'description': 'NeuralPathwayMapper builds a non-empty graph', 'passed': True, 'detail': '{"nodes": 81, "edges": 106, "clusters": 21}', 'duration_ms': 507.005, 'timestamp': 1778695083.5745342, 'iso_time': '2026-05-13T17:58:03.574534Z'}
- {'name': 'inhouse_ai.llm_adapter', 'category': 'inhouse_ai', 'description': 'aureon.inhouse_ai.llm_adapter still importable', 'passed': True, 'detail': '{"module": "aureon.inhouse_ai.llm_adapter"}', 'duration_ms': 0.0, 'timestamp': 1778695084.0815392, 'iso_time': '2026-05-13T17:58:04.081539Z'}
- {'name': 'inhouse_ai.orchestrator', 'category': 'inhouse_ai', 'description': 'aureon.inhouse_ai.orchestrator.OpenMultiAgent still exists', 'passed': True, 'detail': '{"class": "aureon.inhouse_ai.orchestrator.OpenMultiAgent"}', 'duration_ms': 0.0, 'timestamp': 1778695084.0815392, 'iso_time': '2026-05-13T17:58:04.081539Z'}


## 2026-05-13 18:01:43Z — Integration Audit

#aureon #vault #hnc #audit

- **audit_id**: `audit_20260513T180140`
- **when**: `1778695300.7422872`
- **iso_time**: `2026-05-13T18:01:40.742287Z`
- **total**: `12`
- **passed**: `12`
- **failed**: `0`
- **health_ratio**: `1.0`
### results
- {'name': 'ollama.bridge.import', 'category': 'ollama', 'description': 'aureon.integrations.ollama.OllamaBridge imports', 'passed': True, 'detail': '{"class": "aureon.integrations.ollama.OllamaBridge"}', 'duration_ms': 0.0, 'timestamp': 1778695300.7422872, 'iso_time': '2026-05-13T18:01:40.742287Z'}
- {'name': 'ollama.adapter.import', 'category': 'ollama', 'description': 'aureon.integrations.ollama.OllamaLLMAdapter imports', 'passed': True, 'detail': '{"class": "aureon.integrations.ollama.OllamaLLMAdapter"}', 'duration_ms': 0.0, 'timestamp': 1778695300.7422872, 'iso_time': '2026-05-13T18:01:40.742287Z'}
- {'name': 'ollama.bridge.health', 'category': 'ollama', 'description': 'OllamaBridge reaches /api/version (graceful on unreachable)', 'passed': True, 'detail': '{"reachable": true, "base_url": "http://localhost:11434", "model_count": 2, "running_count": 0, "version": "0.23.3"}', 'duration_ms': 2062.312, 'timestamp': 1778695300.7422872, 'iso_time': '2026-05-13T18:01:40.742287Z'}
- {'name': 'ollama.adapter.interface', 'category': 'ollama', 'description': 'OllamaLLMAdapter implements aureon.inhouse_ai.LLMAdapter', 'passed': True, 'detail': '{"adapter": "OllamaLLMAdapter", "interface": "LLMAdapter"}', 'duration_ms': 0.109, 'timestamp': 1778695302.8045993, 'iso_time': '2026-05-13T18:01:42.804599Z'}
- {'name': 'obsidian.bridge.import', 'category': 'obsidian', 'description': 'aureon.integrations.obsidian.ObsidianBridge imports', 'passed': True, 'detail': '{"class": "aureon.integrations.obsidian.ObsidianBridge"}', 'duration_ms': 0.0, 'timestamp': 1778695302.804708, 'iso_time': '2026-05-13T18:01:42.804708Z'}
- {'name': 'obsidian.sink.import', 'category': 'obsidian', 'description': 'aureon.integrations.obsidian.ObsidianSink imports', 'passed': True, 'detail': '{"class": "aureon.integrations.obsidian.ObsidianSink"}', 'duration_ms': 0.0, 'timestamp': 1778695302.804708, 'iso_time': '2026-05-13T18:01:42.804708Z'}
- {'name': 'obsidian.bridge.health', 'category': 'obsidian', 'description': 'ObsidianBridge picks a mode (local_rest OR filesystem)', 'passed': True, 'detail': '{"reachable": true, "mode": "filesystem", "vault_path": "C:\\\\Users\\\\user\\\\AureonObsidianVault", "note_count": 10}', 'duration_ms': 6.122, 'timestamp': 1778695302.804708, 'iso_time': '2026-05-13T18:01:42.804708Z'}
- {'name': 'obsidian.sink.health', 'category': 'obsidian', 'description': 'ObsidianSink status reports reachable + mode', 'passed': True, 'detail': '{"bridge_mode": "filesystem", "reachable": true, "utterances_written": 0, "ticks_written": 0, "audits_written": 0}', 'duration_ms': 2.58, 'timestamp': 1778695302.8108299, 'iso_time': '2026-05-13T18:01:42.810830Z'}
- {'name': 'wiring.vault_voice_loop', 'category': 'wiring', 'description': 'AureonVault + SelfFeedbackLoop + VoiceEngine all import together', 'passed': True, 'detail': '{"vault_size": 0, "loop_id": "3efad49d", "voice_engine_ready": true, "thought_stream_ready": true}', 'duration_ms': 78.392, 'timestamp': 1778695302.8134103, 'iso_time': '2026-05-13T18:01:42.813410Z'}
- {'name': 'pathway.neural_mapper', 'category': 'pathway', 'description': 'NeuralPathwayMapper builds a non-empty graph', 'passed': True, 'detail': '{"nodes": 81, "edges": 106, "clusters": 21}', 'duration_ms': 594.325, 'timestamp': 1778695302.8918025, 'iso_time': '2026-05-13T18:01:42.891803Z'}
- {'name': 'inhouse_ai.llm_adapter', 'category': 'inhouse_ai', 'description': 'aureon.inhouse_ai.llm_adapter still importable', 'passed': True, 'detail': '{"module": "aureon.inhouse_ai.llm_adapter"}', 'duration_ms': 0.0, 'timestamp': 1778695303.4861279, 'iso_time': '2026-05-13T18:01:43.486128Z'}
- {'name': 'inhouse_ai.orchestrator', 'category': 'inhouse_ai', 'description': 'aureon.inhouse_ai.orchestrator.OpenMultiAgent still exists', 'passed': True, 'detail': '{"class": "aureon.inhouse_ai.orchestrator.OpenMultiAgent"}', 'duration_ms': 0.0, 'timestamp': 1778695303.4861279, 'iso_time': '2026-05-13T18:01:43.486128Z'}


## 2026-05-13 18:03:43Z — Integration Audit

#aureon #vault #hnc #audit

- **audit_id**: `audit_20260513T180340`
- **when**: `1778695420.2539456`
- **iso_time**: `2026-05-13T18:03:40.253946Z`
- **total**: `12`
- **passed**: `12`
- **failed**: `0`
- **health_ratio**: `1.0`
### results
- {'name': 'ollama.bridge.import', 'category': 'ollama', 'description': 'aureon.integrations.ollama.OllamaBridge imports', 'passed': True, 'detail': '{"class": "aureon.integrations.ollama.OllamaBridge"}', 'duration_ms': 0.0, 'timestamp': 1778695420.2539456, 'iso_time': '2026-05-13T18:03:40.253946Z'}
- {'name': 'ollama.adapter.import', 'category': 'ollama', 'description': 'aureon.integrations.ollama.OllamaLLMAdapter imports', 'passed': True, 'detail': '{"class": "aureon.integrations.ollama.OllamaLLMAdapter"}', 'duration_ms': 0.0, 'timestamp': 1778695420.2539456, 'iso_time': '2026-05-13T18:03:40.253946Z'}
- {'name': 'ollama.bridge.health', 'category': 'ollama', 'description': 'OllamaBridge reaches /api/version (graceful on unreachable)', 'passed': True, 'detail': '{"reachable": true, "base_url": "http://localhost:11434", "model_count": 2, "running_count": 1, "version": "0.23.3"}', 'duration_ms': 2078.77, 'timestamp': 1778695420.2539456, 'iso_time': '2026-05-13T18:03:40.253946Z'}
- {'name': 'ollama.adapter.interface', 'category': 'ollama', 'description': 'OllamaLLMAdapter implements aureon.inhouse_ai.LLMAdapter', 'passed': True, 'detail': '{"adapter": "OllamaLLMAdapter", "interface": "LLMAdapter"}', 'duration_ms': 0.0, 'timestamp': 1778695422.332716, 'iso_time': '2026-05-13T18:03:42.332716Z'}
- {'name': 'obsidian.bridge.import', 'category': 'obsidian', 'description': 'aureon.integrations.obsidian.ObsidianBridge imports', 'passed': True, 'detail': '{"class": "aureon.integrations.obsidian.ObsidianBridge"}', 'duration_ms': 0.0, 'timestamp': 1778695422.332716, 'iso_time': '2026-05-13T18:03:42.332716Z'}
- {'name': 'obsidian.sink.import', 'category': 'obsidian', 'description': 'aureon.integrations.obsidian.ObsidianSink imports', 'passed': True, 'detail': '{"class": "aureon.integrations.obsidian.ObsidianSink"}', 'duration_ms': 0.0, 'timestamp': 1778695422.332716, 'iso_time': '2026-05-13T18:03:42.332716Z'}
- {'name': 'obsidian.bridge.health', 'category': 'obsidian', 'description': 'ObsidianBridge picks a mode (local_rest OR filesystem)', 'passed': True, 'detail': '{"reachable": true, "mode": "filesystem", "vault_path": "C:\\\\Users\\\\user\\\\AureonObsidianVault", "note_count": 10}', 'duration_ms': 8.054, 'timestamp': 1778695422.332716, 'iso_time': '2026-05-13T18:03:42.332716Z'}
- {'name': 'obsidian.sink.health', 'category': 'obsidian', 'description': 'ObsidianSink status reports reachable + mode', 'passed': True, 'detail': '{"bridge_mode": "filesystem", "reachable": true, "utterances_written": 0, "ticks_written": 0, "audits_written": 0}', 'duration_ms': 3.038, 'timestamp': 1778695422.34077, 'iso_time': '2026-05-13T18:03:42.340770Z'}
- {'name': 'wiring.vault_voice_loop', 'category': 'wiring', 'description': 'AureonVault + SelfFeedbackLoop + VoiceEngine all import together', 'passed': True, 'detail': '{"vault_size": 0, "loop_id": "75d27387", "voice_engine_ready": true, "thought_stream_ready": true}', 'duration_ms': 3.815, 'timestamp': 1778695422.3438077, 'iso_time': '2026-05-13T18:03:42.343808Z'}
- {'name': 'pathway.neural_mapper', 'category': 'pathway', 'description': 'NeuralPathwayMapper builds a non-empty graph', 'passed': True, 'detail': '{"nodes": 81, "edges": 106, "clusters": 21}', 'duration_ms': 734.627, 'timestamp': 1778695422.347623, 'iso_time': '2026-05-13T18:03:42.347623Z'}
- {'name': 'inhouse_ai.llm_adapter', 'category': 'inhouse_ai', 'description': 'aureon.inhouse_ai.llm_adapter still importable', 'passed': True, 'detail': '{"module": "aureon.inhouse_ai.llm_adapter"}', 'duration_ms': 0.0, 'timestamp': 1778695423.0822496, 'iso_time': '2026-05-13T18:03:43.082250Z'}
- {'name': 'inhouse_ai.orchestrator', 'category': 'inhouse_ai', 'description': 'aureon.inhouse_ai.orchestrator.OpenMultiAgent still exists', 'passed': True, 'detail': '{"class": "aureon.inhouse_ai.orchestrator.OpenMultiAgent"}', 'duration_ms': 0.0, 'timestamp': 1778695423.0822496, 'iso_time': '2026-05-13T18:03:43.082250Z'}


## 2026-05-13 18:19:49Z — Integration Audit

#aureon #vault #hnc #audit

- **audit_id**: `audit_20260513T181939`
- **when**: `1778696379.29312`
- **iso_time**: `2026-05-13T18:19:39.293120Z`
- **total**: `12`
- **passed**: `12`
- **failed**: `0`
- **health_ratio**: `1.0`
### results
- {'name': 'ollama.bridge.import', 'category': 'ollama', 'description': 'aureon.integrations.ollama.OllamaBridge imports', 'passed': True, 'detail': '{"class": "aureon.integrations.ollama.OllamaBridge"}', 'duration_ms': 0.0, 'timestamp': 1778696379.29312, 'iso_time': '2026-05-13T18:19:39.293120Z'}
- {'name': 'ollama.adapter.import', 'category': 'ollama', 'description': 'aureon.integrations.ollama.OllamaLLMAdapter imports', 'passed': True, 'detail': '{"class": "aureon.integrations.ollama.OllamaLLMAdapter"}', 'duration_ms': 0.0, 'timestamp': 1778696379.29312, 'iso_time': '2026-05-13T18:19:39.293120Z'}
- {'name': 'ollama.bridge.health', 'category': 'ollama', 'description': 'OllamaBridge reaches /api/version (graceful on unreachable)', 'passed': True, 'detail': '{"reachable": true, "base_url": "http://localhost:11434", "model_count": 2, "running_count": 1, "version": "0.23.3"}', 'duration_ms': 2127.678, 'timestamp': 1778696379.29312, 'iso_time': '2026-05-13T18:19:39.293120Z'}
- {'name': 'ollama.adapter.interface', 'category': 'ollama', 'description': 'OllamaLLMAdapter implements aureon.inhouse_ai.LLMAdapter', 'passed': True, 'detail': '{"adapter": "OllamaLLMAdapter", "interface": "LLMAdapter"}', 'duration_ms': 0.541, 'timestamp': 1778696381.4207976, 'iso_time': '2026-05-13T18:19:41.420798Z'}
- {'name': 'obsidian.bridge.import', 'category': 'obsidian', 'description': 'aureon.integrations.obsidian.ObsidianBridge imports', 'passed': True, 'detail': '{"class": "aureon.integrations.obsidian.ObsidianBridge"}', 'duration_ms': 0.0, 'timestamp': 1778696381.4213388, 'iso_time': '2026-05-13T18:19:41.421339Z'}
- {'name': 'obsidian.sink.import', 'category': 'obsidian', 'description': 'aureon.integrations.obsidian.ObsidianSink imports', 'passed': True, 'detail': '{"class": "aureon.integrations.obsidian.ObsidianSink"}', 'duration_ms': 0.0, 'timestamp': 1778696381.4213388, 'iso_time': '2026-05-13T18:19:41.421339Z'}
- {'name': 'obsidian.bridge.health', 'category': 'obsidian', 'description': 'ObsidianBridge picks a mode (local_rest OR filesystem)', 'passed': True, 'detail': '{"reachable": true, "mode": "filesystem", "vault_path": "C:\\\\Users\\\\user\\\\AureonObsidianVault", "note_count": 10}', 'duration_ms': 7.627, 'timestamp': 1778696381.4213388, 'iso_time': '2026-05-13T18:19:41.421339Z'}
- {'name': 'obsidian.sink.health', 'category': 'obsidian', 'description': 'ObsidianSink status reports reachable + mode', 'passed': True, 'detail': '{"bridge_mode": "filesystem", "reachable": true, "utterances_written": 0, "ticks_written": 0, "audits_written": 0}', 'duration_ms': 0.0, 'timestamp': 1778696381.428966, 'iso_time': '2026-05-13T18:19:41.428966Z'}
- {'name': 'wiring.vault_voice_loop', 'category': 'wiring', 'description': 'AureonVault + SelfFeedbackLoop + VoiceEngine all import together', 'passed': True, 'detail': '{"vault_size": 0, "loop_id": "57b2bc72", "voice_engine_ready": true, "thought_stream_ready": true}', 'duration_ms': 94.073, 'timestamp': 1778696381.428966, 'iso_time': '2026-05-13T18:19:41.428966Z'}
- {'name': 'pathway.neural_mapper', 'category': 'pathway', 'description': 'NeuralPathwayMapper builds a non-empty graph', 'passed': True, 'detail': '{"nodes": 81, "edges": 106, "clusters": 21}', 'duration_ms': 7962.274, 'timestamp': 1778696381.5230386, 'iso_time': '2026-05-13T18:19:41.523039Z'}
- {'name': 'inhouse_ai.llm_adapter', 'category': 'inhouse_ai', 'description': 'aureon.inhouse_ai.llm_adapter still importable', 'passed': True, 'detail': '{"module": "aureon.inhouse_ai.llm_adapter"}', 'duration_ms': 0.0, 'timestamp': 1778696389.485313, 'iso_time': '2026-05-13T18:19:49.485313Z'}
- {'name': 'inhouse_ai.orchestrator', 'category': 'inhouse_ai', 'description': 'aureon.inhouse_ai.orchestrator.OpenMultiAgent still exists', 'passed': True, 'detail': '{"class": "aureon.inhouse_ai.orchestrator.OpenMultiAgent"}', 'duration_ms': 0.0, 'timestamp': 1778696389.485313, 'iso_time': '2026-05-13T18:19:49.485313Z'}


## 2026-05-13 18:27:56Z — Integration Audit

#aureon #vault #hnc #audit

- **audit_id**: `audit_20260513T182753`
- **when**: `1778696873.4348676`
- **iso_time**: `2026-05-13T18:27:53.434868Z`
- **total**: `12`
- **passed**: `12`
- **failed**: `0`
- **health_ratio**: `1.0`
### results
- {'name': 'ollama.bridge.import', 'category': 'ollama', 'description': 'aureon.integrations.ollama.OllamaBridge imports', 'passed': True, 'detail': '{"class": "aureon.integrations.ollama.OllamaBridge"}', 'duration_ms': 1.0, 'timestamp': 1778696873.4358678, 'iso_time': '2026-05-13T18:27:53.435868Z'}
- {'name': 'ollama.adapter.import', 'category': 'ollama', 'description': 'aureon.integrations.ollama.OllamaLLMAdapter imports', 'passed': True, 'detail': '{"class": "aureon.integrations.ollama.OllamaLLMAdapter"}', 'duration_ms': 0.0, 'timestamp': 1778696873.4358678, 'iso_time': '2026-05-13T18:27:53.435868Z'}
- {'name': 'ollama.bridge.health', 'category': 'ollama', 'description': 'OllamaBridge reaches /api/version (graceful on unreachable)', 'passed': True, 'detail': '{"reachable": true, "base_url": "http://localhost:11434", "model_count": 2, "running_count": 0, "version": "0.23.3"}', 'duration_ms': 2040.298, 'timestamp': 1778696873.4358678, 'iso_time': '2026-05-13T18:27:53.435868Z'}
- {'name': 'ollama.adapter.interface', 'category': 'ollama', 'description': 'OllamaLLMAdapter implements aureon.inhouse_ai.LLMAdapter', 'passed': True, 'detail': '{"adapter": "OllamaLLMAdapter", "interface": "LLMAdapter"}', 'duration_ms': 0.0, 'timestamp': 1778696875.4761658, 'iso_time': '2026-05-13T18:27:55.476166Z'}
- {'name': 'obsidian.bridge.import', 'category': 'obsidian', 'description': 'aureon.integrations.obsidian.ObsidianBridge imports', 'passed': True, 'detail': '{"class": "aureon.integrations.obsidian.ObsidianBridge"}', 'duration_ms': 0.0, 'timestamp': 1778696875.4761658, 'iso_time': '2026-05-13T18:27:55.476166Z'}
- {'name': 'obsidian.sink.import', 'category': 'obsidian', 'description': 'aureon.integrations.obsidian.ObsidianSink imports', 'passed': True, 'detail': '{"class": "aureon.integrations.obsidian.ObsidianSink"}', 'duration_ms': 0.0, 'timestamp': 1778696875.4761658, 'iso_time': '2026-05-13T18:27:55.476166Z'}
- {'name': 'obsidian.bridge.health', 'category': 'obsidian', 'description': 'ObsidianBridge picks a mode (local_rest OR filesystem)', 'passed': True, 'detail': '{"reachable": true, "mode": "filesystem", "vault_path": "C:\\\\Users\\\\user\\\\AureonObsidianVault", "note_count": 10}', 'duration_ms': 0.505, 'timestamp': 1778696875.4761658, 'iso_time': '2026-05-13T18:27:55.476166Z'}
- {'name': 'obsidian.sink.health', 'category': 'obsidian', 'description': 'ObsidianSink status reports reachable + mode', 'passed': True, 'detail': '{"bridge_mode": "filesystem", "reachable": true, "utterances_written": 0, "ticks_written": 0, "audits_written": 0}', 'duration_ms': 0.0, 'timestamp': 1778696875.4766707, 'iso_time': '2026-05-13T18:27:55.476671Z'}
- {'name': 'wiring.vault_voice_loop', 'category': 'wiring', 'description': 'AureonVault + SelfFeedbackLoop + VoiceEngine all import together', 'passed': True, 'detail': '{"vault_size": 0, "loop_id": "a87ea818", "voice_engine_ready": true, "thought_stream_ready": true}', 'duration_ms': 0.0, 'timestamp': 1778696875.4766707, 'iso_time': '2026-05-13T18:27:55.476671Z'}
- {'name': 'pathway.neural_mapper', 'category': 'pathway', 'description': 'NeuralPathwayMapper builds a non-empty graph', 'passed': True, 'detail': '{"nodes": 81, "edges": 106, "clusters": 21}', 'duration_ms': 626.783, 'timestamp': 1778696875.4766707, 'iso_time': '2026-05-13T18:27:55.476671Z'}
- {'name': 'inhouse_ai.llm_adapter', 'category': 'inhouse_ai', 'description': 'aureon.inhouse_ai.llm_adapter still importable', 'passed': True, 'detail': '{"module": "aureon.inhouse_ai.llm_adapter"}', 'duration_ms': 0.0, 'timestamp': 1778696876.1034539, 'iso_time': '2026-05-13T18:27:56.103454Z'}
- {'name': 'inhouse_ai.orchestrator', 'category': 'inhouse_ai', 'description': 'aureon.inhouse_ai.orchestrator.OpenMultiAgent still exists', 'passed': True, 'detail': '{"class": "aureon.inhouse_ai.orchestrator.OpenMultiAgent"}', 'duration_ms': 0.0, 'timestamp': 1778696876.1034539, 'iso_time': '2026-05-13T18:27:56.103454Z'}


## 2026-05-13 18:29:48Z — Integration Audit

#aureon #vault #hnc #audit

- **audit_id**: `audit_20260513T182945`
- **when**: `1778696985.6048768`
- **iso_time**: `2026-05-13T18:29:45.604877Z`
- **total**: `12`
- **passed**: `12`
- **failed**: `0`
- **health_ratio**: `1.0`
### results
- {'name': 'ollama.bridge.import', 'category': 'ollama', 'description': 'aureon.integrations.ollama.OllamaBridge imports', 'passed': True, 'detail': '{"class": "aureon.integrations.ollama.OllamaBridge"}', 'duration_ms': 0.0, 'timestamp': 1778696985.6048768, 'iso_time': '2026-05-13T18:29:45.604877Z'}
- {'name': 'ollama.adapter.import', 'category': 'ollama', 'description': 'aureon.integrations.ollama.OllamaLLMAdapter imports', 'passed': True, 'detail': '{"class": "aureon.integrations.ollama.OllamaLLMAdapter"}', 'duration_ms': 0.0, 'timestamp': 1778696985.6048768, 'iso_time': '2026-05-13T18:29:45.604877Z'}
- {'name': 'ollama.bridge.health', 'category': 'ollama', 'description': 'OllamaBridge reaches /api/version (graceful on unreachable)', 'passed': True, 'detail': '{"reachable": true, "base_url": "http://localhost:11434", "model_count": 2, "running_count": 0, "version": "0.23.3"}', 'duration_ms': 2034.823, 'timestamp': 1778696985.6048768, 'iso_time': '2026-05-13T18:29:45.604877Z'}
- {'name': 'ollama.adapter.interface', 'category': 'ollama', 'description': 'OllamaLLMAdapter implements aureon.inhouse_ai.LLMAdapter', 'passed': True, 'detail': '{"adapter": "OllamaLLMAdapter", "interface": "LLMAdapter"}', 'duration_ms': 0.0, 'timestamp': 1778696987.6396997, 'iso_time': '2026-05-13T18:29:47.639700Z'}
- {'name': 'obsidian.bridge.import', 'category': 'obsidian', 'description': 'aureon.integrations.obsidian.ObsidianBridge imports', 'passed': True, 'detail': '{"class": "aureon.integrations.obsidian.ObsidianBridge"}', 'duration_ms': 0.0, 'timestamp': 1778696987.6396997, 'iso_time': '2026-05-13T18:29:47.639700Z'}
- {'name': 'obsidian.sink.import', 'category': 'obsidian', 'description': 'aureon.integrations.obsidian.ObsidianSink imports', 'passed': True, 'detail': '{"class": "aureon.integrations.obsidian.ObsidianSink"}', 'duration_ms': 0.0, 'timestamp': 1778696987.6396997, 'iso_time': '2026-05-13T18:29:47.639700Z'}
- {'name': 'obsidian.bridge.health', 'category': 'obsidian', 'description': 'ObsidianBridge picks a mode (local_rest OR filesystem)', 'passed': True, 'detail': '{"reachable": true, "mode": "filesystem", "vault_path": "C:\\\\Users\\\\user\\\\AureonObsidianVault", "note_count": 10}', 'duration_ms': 0.545, 'timestamp': 1778696987.6396997, 'iso_time': '2026-05-13T18:29:47.639700Z'}
- {'name': 'obsidian.sink.health', 'category': 'obsidian', 'description': 'ObsidianSink status reports reachable + mode', 'passed': True, 'detail': '{"bridge_mode": "filesystem", "reachable": true, "utterances_written": 0, "ticks_written": 0, "audits_written": 0}', 'duration_ms': 0.0, 'timestamp': 1778696987.6402442, 'iso_time': '2026-05-13T18:29:47.640244Z'}
- {'name': 'wiring.vault_voice_loop', 'category': 'wiring', 'description': 'AureonVault + SelfFeedbackLoop + VoiceEngine all import together', 'passed': True, 'detail': '{"vault_size": 0, "loop_id": "8c0b13c3", "voice_engine_ready": true, "thought_stream_ready": true}', 'duration_ms': 26.267, 'timestamp': 1778696987.6402442, 'iso_time': '2026-05-13T18:29:47.640244Z'}
- {'name': 'pathway.neural_mapper', 'category': 'pathway', 'description': 'NeuralPathwayMapper builds a non-empty graph', 'passed': True, 'detail': '{"nodes": 81, "edges": 106, "clusters": 21}', 'duration_ms': 666.735, 'timestamp': 1778696987.666511, 'iso_time': '2026-05-13T18:29:47.666511Z'}
- {'name': 'inhouse_ai.llm_adapter', 'category': 'inhouse_ai', 'description': 'aureon.inhouse_ai.llm_adapter still importable', 'passed': True, 'detail': '{"module": "aureon.inhouse_ai.llm_adapter"}', 'duration_ms': 0.0, 'timestamp': 1778696988.333246, 'iso_time': '2026-05-13T18:29:48.333246Z'}
- {'name': 'inhouse_ai.orchestrator', 'category': 'inhouse_ai', 'description': 'aureon.inhouse_ai.orchestrator.OpenMultiAgent still exists', 'passed': True, 'detail': '{"class": "aureon.inhouse_ai.orchestrator.OpenMultiAgent"}', 'duration_ms': 0.0, 'timestamp': 1778696988.333246, 'iso_time': '2026-05-13T18:29:48.333246Z'}


## 2026-05-13 18:31:34Z — Integration Audit

#aureon #vault #hnc #audit

- **audit_id**: `audit_20260513T183131`
- **when**: `1778697091.9904`
- **iso_time**: `2026-05-13T18:31:31.990400Z`
- **total**: `12`
- **passed**: `12`
- **failed**: `0`
- **health_ratio**: `1.0`
### results
- {'name': 'ollama.bridge.import', 'category': 'ollama', 'description': 'aureon.integrations.ollama.OllamaBridge imports', 'passed': True, 'detail': '{"class": "aureon.integrations.ollama.OllamaBridge"}', 'duration_ms': 0.0, 'timestamp': 1778697091.9904, 'iso_time': '2026-05-13T18:31:31.990400Z'}
- {'name': 'ollama.adapter.import', 'category': 'ollama', 'description': 'aureon.integrations.ollama.OllamaLLMAdapter imports', 'passed': True, 'detail': '{"class": "aureon.integrations.ollama.OllamaLLMAdapter"}', 'duration_ms': 0.0, 'timestamp': 1778697091.9904, 'iso_time': '2026-05-13T18:31:31.990400Z'}
- {'name': 'ollama.bridge.health', 'category': 'ollama', 'description': 'OllamaBridge reaches /api/version (graceful on unreachable)', 'passed': True, 'detail': '{"reachable": true, "base_url": "http://localhost:11434", "model_count": 2, "running_count": 0, "version": "0.23.3"}', 'duration_ms': 2037.046, 'timestamp': 1778697091.9904, 'iso_time': '2026-05-13T18:31:31.990400Z'}
- {'name': 'ollama.adapter.interface', 'category': 'ollama', 'description': 'OllamaLLMAdapter implements aureon.inhouse_ai.LLMAdapter', 'passed': True, 'detail': '{"adapter": "OllamaLLMAdapter", "interface": "LLMAdapter"}', 'duration_ms': 0.0, 'timestamp': 1778697094.0274458, 'iso_time': '2026-05-13T18:31:34.027446Z'}
- {'name': 'obsidian.bridge.import', 'category': 'obsidian', 'description': 'aureon.integrations.obsidian.ObsidianBridge imports', 'passed': True, 'detail': '{"class": "aureon.integrations.obsidian.ObsidianBridge"}', 'duration_ms': 0.0, 'timestamp': 1778697094.0274458, 'iso_time': '2026-05-13T18:31:34.027446Z'}
- {'name': 'obsidian.sink.import', 'category': 'obsidian', 'description': 'aureon.integrations.obsidian.ObsidianSink imports', 'passed': True, 'detail': '{"class": "aureon.integrations.obsidian.ObsidianSink"}', 'duration_ms': 0.0, 'timestamp': 1778697094.0274458, 'iso_time': '2026-05-13T18:31:34.027446Z'}
- {'name': 'obsidian.bridge.health', 'category': 'obsidian', 'description': 'ObsidianBridge picks a mode (local_rest OR filesystem)', 'passed': True, 'detail': '{"reachable": true, "mode": "filesystem", "vault_path": "C:\\\\Users\\\\user\\\\AureonObsidianVault", "note_count": 10}', 'duration_ms': 0.507, 'timestamp': 1778697094.0274458, 'iso_time': '2026-05-13T18:31:34.027446Z'}
- {'name': 'obsidian.sink.health', 'category': 'obsidian', 'description': 'ObsidianSink status reports reachable + mode', 'passed': True, 'detail': '{"bridge_mode": "filesystem", "reachable": true, "utterances_written": 0, "ticks_written": 0, "audits_written": 0}', 'duration_ms': 0.0, 'timestamp': 1778697094.0279524, 'iso_time': '2026-05-13T18:31:34.027952Z'}
- {'name': 'wiring.vault_voice_loop', 'category': 'wiring', 'description': 'AureonVault + SelfFeedbackLoop + VoiceEngine all import together', 'passed': True, 'detail': '{"vault_size": 0, "loop_id": "59addf49", "voice_engine_ready": true, "thought_stream_ready": true}', 'duration_ms': 113.021, 'timestamp': 1778697094.0279524, 'iso_time': '2026-05-13T18:31:34.027952Z'}
- {'name': 'pathway.neural_mapper', 'category': 'pathway', 'description': 'NeuralPathwayMapper builds a non-empty graph', 'passed': True, 'detail': '{"nodes": 81, "edges": 106, "clusters": 21}', 'duration_ms': 575.39, 'timestamp': 1778697094.140973, 'iso_time': '2026-05-13T18:31:34.140973Z'}
- {'name': 'inhouse_ai.llm_adapter', 'category': 'inhouse_ai', 'description': 'aureon.inhouse_ai.llm_adapter still importable', 'passed': True, 'detail': '{"module": "aureon.inhouse_ai.llm_adapter"}', 'duration_ms': 0.0, 'timestamp': 1778697094.7163627, 'iso_time': '2026-05-13T18:31:34.716363Z'}
- {'name': 'inhouse_ai.orchestrator', 'category': 'inhouse_ai', 'description': 'aureon.inhouse_ai.orchestrator.OpenMultiAgent still exists', 'passed': True, 'detail': '{"class": "aureon.inhouse_ai.orchestrator.OpenMultiAgent"}', 'duration_ms': 0.0, 'timestamp': 1778697094.7163627, 'iso_time': '2026-05-13T18:31:34.716363Z'}


## 2026-05-13 18:34:08Z — Integration Audit

#aureon #vault #hnc #audit

- **audit_id**: `audit_20260513T183405`
- **when**: `1778697245.6891212`
- **iso_time**: `2026-05-13T18:34:05.689121Z`
- **total**: `12`
- **passed**: `12`
- **failed**: `0`
- **health_ratio**: `1.0`
### results
- {'name': 'ollama.bridge.import', 'category': 'ollama', 'description': 'aureon.integrations.ollama.OllamaBridge imports', 'passed': True, 'detail': '{"class": "aureon.integrations.ollama.OllamaBridge"}', 'duration_ms': 0.0, 'timestamp': 1778697245.6891212, 'iso_time': '2026-05-13T18:34:05.689121Z'}
- {'name': 'ollama.adapter.import', 'category': 'ollama', 'description': 'aureon.integrations.ollama.OllamaLLMAdapter imports', 'passed': True, 'detail': '{"class": "aureon.integrations.ollama.OllamaLLMAdapter"}', 'duration_ms': 0.0, 'timestamp': 1778697245.6891212, 'iso_time': '2026-05-13T18:34:05.689121Z'}
- {'name': 'ollama.bridge.health', 'category': 'ollama', 'description': 'OllamaBridge reaches /api/version (graceful on unreachable)', 'passed': True, 'detail': '{"reachable": true, "base_url": "http://localhost:11434", "model_count": 2, "running_count": 0, "version": "0.23.3"}', 'duration_ms': 2040.448, 'timestamp': 1778697245.6891212, 'iso_time': '2026-05-13T18:34:05.689121Z'}
- {'name': 'ollama.adapter.interface', 'category': 'ollama', 'description': 'OllamaLLMAdapter implements aureon.inhouse_ai.LLMAdapter', 'passed': True, 'detail': '{"adapter": "OllamaLLMAdapter", "interface": "LLMAdapter"}', 'duration_ms': 0.0, 'timestamp': 1778697247.7295692, 'iso_time': '2026-05-13T18:34:07.729569Z'}
- {'name': 'obsidian.bridge.import', 'category': 'obsidian', 'description': 'aureon.integrations.obsidian.ObsidianBridge imports', 'passed': True, 'detail': '{"class": "aureon.integrations.obsidian.ObsidianBridge"}', 'duration_ms': 0.542, 'timestamp': 1778697247.7301116, 'iso_time': '2026-05-13T18:34:07.730112Z'}
- {'name': 'obsidian.sink.import', 'category': 'obsidian', 'description': 'aureon.integrations.obsidian.ObsidianSink imports', 'passed': True, 'detail': '{"class": "aureon.integrations.obsidian.ObsidianSink"}', 'duration_ms': 0.0, 'timestamp': 1778697247.7301116, 'iso_time': '2026-05-13T18:34:07.730112Z'}
- {'name': 'obsidian.bridge.health', 'category': 'obsidian', 'description': 'ObsidianBridge picks a mode (local_rest OR filesystem)', 'passed': True, 'detail': '{"reachable": true, "mode": "filesystem", "vault_path": "C:\\\\Users\\\\user\\\\AureonObsidianVault", "note_count": 10}', 'duration_ms': 4.157, 'timestamp': 1778697247.7301116, 'iso_time': '2026-05-13T18:34:07.730112Z'}
- {'name': 'obsidian.sink.health', 'category': 'obsidian', 'description': 'ObsidianSink status reports reachable + mode', 'passed': True, 'detail': '{"bridge_mode": "filesystem", "reachable": true, "utterances_written": 0, "ticks_written": 0, "audits_written": 0}', 'duration_ms': 0.0, 'timestamp': 1778697247.7342687, 'iso_time': '2026-05-13T18:34:07.734269Z'}
- {'name': 'wiring.vault_voice_loop', 'category': 'wiring', 'description': 'AureonVault + SelfFeedbackLoop + VoiceEngine all import together', 'passed': True, 'detail': '{"vault_size": 0, "loop_id": "db0a2b4a", "voice_engine_ready": true, "thought_stream_ready": true}', 'duration_ms': 7.043, 'timestamp': 1778697247.7342687, 'iso_time': '2026-05-13T18:34:07.734269Z'}
- {'name': 'pathway.neural_mapper', 'category': 'pathway', 'description': 'NeuralPathwayMapper builds a non-empty graph', 'passed': True, 'detail': '{"nodes": 81, "edges": 106, "clusters": 21}', 'duration_ms': 591.874, 'timestamp': 1778697247.7413116, 'iso_time': '2026-05-13T18:34:07.741312Z'}
- {'name': 'inhouse_ai.llm_adapter', 'category': 'inhouse_ai', 'description': 'aureon.inhouse_ai.llm_adapter still importable', 'passed': True, 'detail': '{"module": "aureon.inhouse_ai.llm_adapter"}', 'duration_ms': 0.0, 'timestamp': 1778697248.3331852, 'iso_time': '2026-05-13T18:34:08.333185Z'}
- {'name': 'inhouse_ai.orchestrator', 'category': 'inhouse_ai', 'description': 'aureon.inhouse_ai.orchestrator.OpenMultiAgent still exists', 'passed': True, 'detail': '{"class": "aureon.inhouse_ai.orchestrator.OpenMultiAgent"}', 'duration_ms': 0.0, 'timestamp': 1778697248.3342054, 'iso_time': '2026-05-13T18:34:08.334205Z'}


## 2026-05-13 18:36:20Z — Integration Audit

#aureon #vault #hnc #audit

- **audit_id**: `audit_20260513T183617`
- **when**: `1778697377.6017566`
- **iso_time**: `2026-05-13T18:36:17.601757Z`
- **total**: `12`
- **passed**: `12`
- **failed**: `0`
- **health_ratio**: `1.0`
### results
- {'name': 'ollama.bridge.import', 'category': 'ollama', 'description': 'aureon.integrations.ollama.OllamaBridge imports', 'passed': True, 'detail': '{"class": "aureon.integrations.ollama.OllamaBridge"}', 'duration_ms': 0.0, 'timestamp': 1778697377.6017566, 'iso_time': '2026-05-13T18:36:17.601757Z'}
- {'name': 'ollama.adapter.import', 'category': 'ollama', 'description': 'aureon.integrations.ollama.OllamaLLMAdapter imports', 'passed': True, 'detail': '{"class": "aureon.integrations.ollama.OllamaLLMAdapter"}', 'duration_ms': 0.0, 'timestamp': 1778697377.6017566, 'iso_time': '2026-05-13T18:36:17.601757Z'}
- {'name': 'ollama.bridge.health', 'category': 'ollama', 'description': 'OllamaBridge reaches /api/version (graceful on unreachable)', 'passed': True, 'detail': '{"reachable": true, "base_url": "http://localhost:11434", "model_count": 2, "running_count": 0, "version": "0.23.3"}', 'duration_ms': 2041.29, 'timestamp': 1778697377.6017566, 'iso_time': '2026-05-13T18:36:17.601757Z'}
- {'name': 'ollama.adapter.interface', 'category': 'ollama', 'description': 'OllamaLLMAdapter implements aureon.inhouse_ai.LLMAdapter', 'passed': True, 'detail': '{"adapter": "OllamaLLMAdapter", "interface": "LLMAdapter"}', 'duration_ms': 0.0, 'timestamp': 1778697379.6430466, 'iso_time': '2026-05-13T18:36:19.643047Z'}
- {'name': 'obsidian.bridge.import', 'category': 'obsidian', 'description': 'aureon.integrations.obsidian.ObsidianBridge imports', 'passed': True, 'detail': '{"class": "aureon.integrations.obsidian.ObsidianBridge"}', 'duration_ms': 0.0, 'timestamp': 1778697379.6430466, 'iso_time': '2026-05-13T18:36:19.643047Z'}
- {'name': 'obsidian.sink.import', 'category': 'obsidian', 'description': 'aureon.integrations.obsidian.ObsidianSink imports', 'passed': True, 'detail': '{"class": "aureon.integrations.obsidian.ObsidianSink"}', 'duration_ms': 0.0, 'timestamp': 1778697379.6430466, 'iso_time': '2026-05-13T18:36:19.643047Z'}
- {'name': 'obsidian.bridge.health', 'category': 'obsidian', 'description': 'ObsidianBridge picks a mode (local_rest OR filesystem)', 'passed': True, 'detail': '{"reachable": true, "mode": "filesystem", "vault_path": "C:\\\\Users\\\\user\\\\AureonObsidianVault", "note_count": 10}', 'duration_ms': 0.517, 'timestamp': 1778697379.6430466, 'iso_time': '2026-05-13T18:36:19.643047Z'}
- {'name': 'obsidian.sink.health', 'category': 'obsidian', 'description': 'ObsidianSink status reports reachable + mode', 'passed': True, 'detail': '{"bridge_mode": "filesystem", "reachable": true, "utterances_written": 0, "ticks_written": 0, "audits_written": 0}', 'duration_ms': 0.0, 'timestamp': 1778697379.6435637, 'iso_time': '2026-05-13T18:36:19.643564Z'}
- {'name': 'wiring.vault_voice_loop', 'category': 'wiring', 'description': 'AureonVault + SelfFeedbackLoop + VoiceEngine all import together', 'passed': True, 'detail': '{"vault_size": 0, "loop_id": "bc0c05ac", "voice_engine_ready": true, "thought_stream_ready": true}', 'duration_ms': 9.492, 'timestamp': 1778697379.6435637, 'iso_time': '2026-05-13T18:36:19.643564Z'}
- {'name': 'pathway.neural_mapper', 'category': 'pathway', 'description': 'NeuralPathwayMapper builds a non-empty graph', 'passed': True, 'detail': '{"nodes": 81, "edges": 106, "clusters": 21}', 'duration_ms': 590.492, 'timestamp': 1778697379.6530561, 'iso_time': '2026-05-13T18:36:19.653056Z'}
- {'name': 'inhouse_ai.llm_adapter', 'category': 'inhouse_ai', 'description': 'aureon.inhouse_ai.llm_adapter still importable', 'passed': True, 'detail': '{"module": "aureon.inhouse_ai.llm_adapter"}', 'duration_ms': 0.0, 'timestamp': 1778697380.2435484, 'iso_time': '2026-05-13T18:36:20.243548Z'}
- {'name': 'inhouse_ai.orchestrator', 'category': 'inhouse_ai', 'description': 'aureon.inhouse_ai.orchestrator.OpenMultiAgent still exists', 'passed': True, 'detail': '{"class": "aureon.inhouse_ai.orchestrator.OpenMultiAgent"}', 'duration_ms': 0.0, 'timestamp': 1778697380.2435484, 'iso_time': '2026-05-13T18:36:20.243548Z'}


## 2026-05-13 18:38:00Z — Integration Audit

#aureon #vault #hnc #audit

- **audit_id**: `audit_20260513T183758`
- **when**: `1778697478.3003588`
- **iso_time**: `2026-05-13T18:37:58.300359Z`
- **total**: `12`
- **passed**: `12`
- **failed**: `0`
- **health_ratio**: `1.0`
### results
- {'name': 'ollama.bridge.import', 'category': 'ollama', 'description': 'aureon.integrations.ollama.OllamaBridge imports', 'passed': True, 'detail': '{"class": "aureon.integrations.ollama.OllamaBridge"}', 'duration_ms': 0.0, 'timestamp': 1778697478.3003588, 'iso_time': '2026-05-13T18:37:58.300359Z'}
- {'name': 'ollama.adapter.import', 'category': 'ollama', 'description': 'aureon.integrations.ollama.OllamaLLMAdapter imports', 'passed': True, 'detail': '{"class": "aureon.integrations.ollama.OllamaLLMAdapter"}', 'duration_ms': 0.0, 'timestamp': 1778697478.3003588, 'iso_time': '2026-05-13T18:37:58.300359Z'}
- {'name': 'ollama.bridge.health', 'category': 'ollama', 'description': 'OllamaBridge reaches /api/version (graceful on unreachable)', 'passed': True, 'detail': '{"reachable": true, "base_url": "http://localhost:11434", "model_count": 2, "running_count": 0, "version": "0.23.3"}', 'duration_ms': 2048.083, 'timestamp': 1778697478.3003588, 'iso_time': '2026-05-13T18:37:58.300359Z'}
- {'name': 'ollama.adapter.interface', 'category': 'ollama', 'description': 'OllamaLLMAdapter implements aureon.inhouse_ai.LLMAdapter', 'passed': True, 'detail': '{"adapter": "OllamaLLMAdapter", "interface": "LLMAdapter"}', 'duration_ms': 0.0, 'timestamp': 1778697480.3484418, 'iso_time': '2026-05-13T18:38:00.348442Z'}
- {'name': 'obsidian.bridge.import', 'category': 'obsidian', 'description': 'aureon.integrations.obsidian.ObsidianBridge imports', 'passed': True, 'detail': '{"class": "aureon.integrations.obsidian.ObsidianBridge"}', 'duration_ms': 0.514, 'timestamp': 1778697480.3484418, 'iso_time': '2026-05-13T18:38:00.348442Z'}
- {'name': 'obsidian.sink.import', 'category': 'obsidian', 'description': 'aureon.integrations.obsidian.ObsidianSink imports', 'passed': True, 'detail': '{"class": "aureon.integrations.obsidian.ObsidianSink"}', 'duration_ms': 0.0, 'timestamp': 1778697480.3489554, 'iso_time': '2026-05-13T18:38:00.348955Z'}
- {'name': 'obsidian.bridge.health', 'category': 'obsidian', 'description': 'ObsidianBridge picks a mode (local_rest OR filesystem)', 'passed': True, 'detail': '{"reachable": true, "mode": "filesystem", "vault_path": "C:\\\\Users\\\\user\\\\AureonObsidianVault", "note_count": 10}', 'duration_ms': 4.992, 'timestamp': 1778697480.3489554, 'iso_time': '2026-05-13T18:38:00.348955Z'}
- {'name': 'obsidian.sink.health', 'category': 'obsidian', 'description': 'ObsidianSink status reports reachable + mode', 'passed': True, 'detail': '{"bridge_mode": "filesystem", "reachable": true, "utterances_written": 0, "ticks_written": 0, "audits_written": 0}', 'duration_ms': 2.509, 'timestamp': 1778697480.3539479, 'iso_time': '2026-05-13T18:38:00.353948Z'}
- {'name': 'wiring.vault_voice_loop', 'category': 'wiring', 'description': 'AureonVault + SelfFeedbackLoop + VoiceEngine all import together', 'passed': True, 'detail': '{"vault_size": 0, "loop_id": "464e9f54", "voice_engine_ready": true, "thought_stream_ready": true}', 'duration_ms': 5.55, 'timestamp': 1778697480.3564568, 'iso_time': '2026-05-13T18:38:00.356457Z'}
- {'name': 'pathway.neural_mapper', 'category': 'pathway', 'description': 'NeuralPathwayMapper builds a non-empty graph', 'passed': True, 'detail': '{"nodes": 81, "edges": 106, "clusters": 21}', 'duration_ms': 558.259, 'timestamp': 1778697480.362007, 'iso_time': '2026-05-13T18:38:00.362007Z'}
- {'name': 'inhouse_ai.llm_adapter', 'category': 'inhouse_ai', 'description': 'aureon.inhouse_ai.llm_adapter still importable', 'passed': True, 'detail': '{"module": "aureon.inhouse_ai.llm_adapter"}', 'duration_ms': 0.0, 'timestamp': 1778697480.9202664, 'iso_time': '2026-05-13T18:38:00.920266Z'}
- {'name': 'inhouse_ai.orchestrator', 'category': 'inhouse_ai', 'description': 'aureon.inhouse_ai.orchestrator.OpenMultiAgent still exists', 'passed': True, 'detail': '{"class": "aureon.inhouse_ai.orchestrator.OpenMultiAgent"}', 'duration_ms': 0.0, 'timestamp': 1778697480.9202664, 'iso_time': '2026-05-13T18:38:00.920266Z'}


## 2026-05-21 08:05:33Z — Integration Audit

#aureon #vault #hnc #audit

- **audit_id**: `audit_20260521T080413`
- **when**: `1779350653.9950454`
- **iso_time**: `2026-05-21T08:04:13.995045Z`
- **total**: `12`
- **passed**: `12`
- **failed**: `0`
- **health_ratio**: `1.0`
### results
- {'name': 'ollama.bridge.import', 'category': 'ollama', 'description': 'aureon.integrations.ollama.OllamaBridge imports', 'passed': True, 'detail': '{"class": "aureon.integrations.ollama.OllamaBridge"}', 'duration_ms': 0.0, 'timestamp': 1779350653.9950454, 'iso_time': '2026-05-21T08:04:13.995045Z'}
- {'name': 'ollama.adapter.import', 'category': 'ollama', 'description': 'aureon.integrations.ollama.OllamaLLMAdapter imports', 'passed': True, 'detail': '{"class": "aureon.integrations.ollama.OllamaLLMAdapter"}', 'duration_ms': 0.0, 'timestamp': 1779350653.9950454, 'iso_time': '2026-05-21T08:04:13.995045Z'}
- {'name': 'ollama.bridge.health', 'category': 'ollama', 'description': 'OllamaBridge reaches /api/version (graceful on unreachable)', 'passed': True, 'detail': '{"reachable": true, "base_url": "http://localhost:11434", "model_count": 2, "running_count": 2, "version": "0.24.0"}', 'duration_ms': 2083.636, 'timestamp': 1779350653.9950454, 'iso_time': '2026-05-21T08:04:13.995045Z'}
- {'name': 'ollama.adapter.interface', 'category': 'ollama', 'description': 'OllamaLLMAdapter implements aureon.inhouse_ai.LLMAdapter', 'passed': True, 'detail': '{"adapter": "OllamaLLMAdapter", "interface": "LLMAdapter"}', 'duration_ms': 0.0, 'timestamp': 1779350656.0786812, 'iso_time': '2026-05-21T08:04:16.078681Z'}
- {'name': 'obsidian.bridge.import', 'category': 'obsidian', 'description': 'aureon.integrations.obsidian.ObsidianBridge imports', 'passed': True, 'detail': '{"class": "aureon.integrations.obsidian.ObsidianBridge"}', 'duration_ms': 0.0, 'timestamp': 1779350656.0786812, 'iso_time': '2026-05-21T08:04:16.078681Z'}
- {'name': 'obsidian.sink.import', 'category': 'obsidian', 'description': 'aureon.integrations.obsidian.ObsidianSink imports', 'passed': True, 'detail': '{"class": "aureon.integrations.obsidian.ObsidianSink"}', 'duration_ms': 0.0, 'timestamp': 1779350656.0786812, 'iso_time': '2026-05-21T08:04:16.078681Z'}
- {'name': 'obsidian.bridge.health', 'category': 'obsidian', 'description': 'ObsidianBridge picks a mode (local_rest OR filesystem)', 'passed': True, 'detail': '{"reachable": true, "mode": "filesystem", "vault_path": "C:\\\\Users\\\\user\\\\AureonObsidianVault", "note_count": 10}', 'duration_ms': 1.755, 'timestamp': 1779350656.0786812, 'iso_time': '2026-05-21T08:04:16.078681Z'}
- {'name': 'obsidian.sink.health', 'category': 'obsidian', 'description': 'ObsidianSink status reports reachable + mode', 'passed': True, 'detail': '{"bridge_mode": "filesystem", "reachable": true, "utterances_written": 0, "ticks_written": 0, "audits_written": 0}', 'duration_ms': 0.0, 'timestamp': 1779350656.0804367, 'iso_time': '2026-05-21T08:04:16.080437Z'}
- {'name': 'wiring.vault_voice_loop', 'category': 'wiring', 'description': 'AureonVault + SelfFeedbackLoop + VoiceEngine all import together', 'passed': True, 'detail': '{"vault_size": 0, "loop_id": "5b6e2cc9", "voice_engine_ready": true, "thought_stream_ready": true}', 'duration_ms': 76333.398, 'timestamp': 1779350656.0804367, 'iso_time': '2026-05-21T08:04:16.080437Z'}
- {'name': 'pathway.neural_mapper', 'category': 'pathway', 'description': 'NeuralPathwayMapper builds a non-empty graph', 'passed': True, 'detail': '{"nodes": 80, "edges": 86, "clusters": 11}', 'duration_ms': 663.043, 'timestamp': 1779350732.4138348, 'iso_time': '2026-05-21T08:05:32.413835Z'}
- {'name': 'inhouse_ai.llm_adapter', 'category': 'inhouse_ai', 'description': 'aureon.inhouse_ai.llm_adapter still importable', 'passed': True, 'detail': '{"module": "aureon.inhouse_ai.llm_adapter"}', 'duration_ms': 0.0, 'timestamp': 1779350733.076878, 'iso_time': '2026-05-21T08:05:33.076878Z'}
- {'name': 'inhouse_ai.orchestrator', 'category': 'inhouse_ai', 'description': 'aureon.inhouse_ai.orchestrator.OpenMultiAgent still exists', 'passed': True, 'detail': '{"class": "aureon.inhouse_ai.orchestrator.OpenMultiAgent"}', 'duration_ms': 0.0, 'timestamp': 1779350733.076878, 'iso_time': '2026-05-21T08:05:33.076878Z'}
