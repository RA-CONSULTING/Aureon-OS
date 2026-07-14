# Live Multi-Daemon Benchmark

**Status:** pass · 5/5 critical · 3/4 informational

Boots the three supervisord daemons as separate processes and verifies the organism senses itself across the process boundary — including the metacognition self-loop.

| Check | Tier | Result | Detail |
|-------|------|--------|--------|
| daemon_boot | critical | ✅ | launched ['hnc', 'operator', 'organism'] on port 60739 |
| consensus_breathing | critical | ✅ | consensus age=0.9s after 6s (organism daemon breathed) |
| metacognition_selfloop | critical | ✅ | metacognition_monitor sub-field present=True (the daemon read its own signals and looped back); sources=['consciousness_module', 'metacognition_monitor'] |
| operator_pulse | critical | ✅ | /api/pulse served=True |
| api_metacognition | info | ✅ | /api/metacognition self_coherence=0.8967 truth=real_derived |
| cross_process_field | info | ⚠️ | /api/pulse organism.unification.field_flowing=False (informational — HNC Layer-1 sources degrade offline) |
| hnc_field_flowing | info | ✅ | trace grew 10941→12155 bytes; last sls=0.5900893783919237 |
| flight_check | info | ✅ | standing-wave health=0.1094 |
| saas_compliance | critical | ✅ | 15/15 checks; 0 required failures |
