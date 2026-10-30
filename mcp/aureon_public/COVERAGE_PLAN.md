# Public MCP coverage plan

Counts are the pinned `docs/mcp/inventory.json`. A public entry point is a public function or method. Reachable means `public_entry_refusal` returns None, so `body_call` will run it. A listed module or class is not an entry point. The sha256 below is `INVENTORY_SHA256`. A different inventory file is not loaded.

Inventory sha256: `4bc19ea9b5444a7b8a9abbd3fabf635d083bd25bea6c1b2d6eab2605b4f5716b`

Reproduce:

```bash
env -u PYTHONPATH PYTHONPATH=mcp python3.12 -m aureon_public.coverage_plan --check
bash measured/aureon_public_stage1_run.sh
bash measured/aureon_public_stage2_sweep.sh
bash measured/aureon_public_call_sweep.sh
bash measured/aureon_public_protocol_run.sh
env -u PYTHONPATH /tmp/aureon-public-venv/bin/python -m pytest tests/test_aureon_public_mcp.py tests/test_aureon_body.py tests/bio/test_mcp_interior_attribution.py tests/bio/test_mcp_membrane.py tests/bio/test_mcp_transport.py tests/test_aureon_public_alignment.py tests/test_aureon_public_stage1.py tests/test_aureon_public_stage2.py tests/test_aureon_public_protocol.py --tb=line
```

That pytest command is the gate. It runs in `/tmp/aureon-public-venv`, the venv `measured/aureon_public_stage1_run.sh` creates (`VENV` overrides the path). The file list is `tests/test_aureon_public_mcp.py`, `tests/test_aureon_body.py`, `tests/bio/test_mcp_interior_attribution.py`, `tests/bio/test_mcp_membrane.py`, `tests/bio/test_mcp_transport.py`, `tests/test_aureon_public_alignment.py`, `tests/test_aureon_public_stage1.py`, `tests/test_aureon_public_stage2.py`, and `tests/test_aureon_public_protocol.py`. `tests/test_async_socket_isolation.py` is not in the gate list. It imports `pytest_socket`, and `mcp/aureon_public/test-requirements.txt` does not install that plugin.

`--write` rewrites this file from the same function. `measured/aureon_public_stage1_run.sh` installs `mcp/aureon_public/requirements.txt` and `mcp/aureon_public/test-requirements.txt`, then rewrites both `measured/aureon_public_alignment.json` and `measured/aureon_public_stage1.json`. It writes those two files under a temp directory first and copies them into `measured/` only after both stamps have finished. `measurement_stamp` raises `RuntimeError` when `git status --porcelain` is not empty, so the second stamp must not see the first file. `test-requirements.txt` is the test install: pytest, pytest-timeout, flask, pandas, and scipy. It is not the public server runtime. `measured/aureon_public_stage2_sweep.sh` and `measured/aureon_public_call_sweep.sh` copy the checkout with `cp -a` under an ordinary temp parent, place fake `NEXUS-LIVE-FEED-` and `Aureon-Trading--Project-Sero` checkouts beside that copy, block sockets, and rewrite their measured records. Each sweep record names the pin, the `aureon/` tree hash beside that pin, the `aureon_source` kind, and that temp parent. `measured/aureon_public_protocol_run.sh` starts this server over stdio and over Streamable HTTP bound to `127.0.0.1`, with `AUREON_PUBLIC_REQUIRE_PIN=1`. An MCP SDK 1.30.0 client calls `tools/list`, `resources/list`, `prompts/list`, and one `tools/call` (`alignment_consonance_read` with ratio 1.0). The raw pages are `measured/aureon_public_protocol.json`. These measured records name `code_commit`, the parent of the commit that contains the record file. A record cannot name the commit that adds the file.

Listed symbols: 20083. Public entry points: 4388. Reachable now: 78. Tested: 68. Refused: 4310. The plan on main recorded 879 reachable. An earlier draft head of the stage-1 PR recorded 89 reachable, before the call sweep. Methods open because a constructor is allowlisted: 19. The refused-imports fence is unchanged.
Reachable means `public_entry_refusal` returns None. Tested means a public tool calls that entry point and `tests/test_aureon_public_stage1.py` or `tests/test_aureon_public_stage2.py` exercises the tool. Refused means a public entry point the server will not run. Plan stages 3 and 4 stay closed. The call sweep calls every entry point that was still reachable, with no arguments, and calls each stage-2 entry point again with the real arguments in `stage2_arguments.py`. It refuses one that opens a connection, starts a process, writes outside the sandbox, or loads queen, miner, swarm_motion, inhouse_ai, ollama_config, or an HTTP client. `get_unified_directive` is refused that way. It does not build the queen and miner bridges.

## Stage order

The stage is the inventory safety text, not a new scan.

1. Deterministic read-only. No key, order, live-fetch, process, or write sentence, and the package is not operator-only.
2. A process or write sentence, and still no key, order, or live-fetch sentence.
3. Operator-scoped, with no pure public row and no key, order, or live-fetch sentence.
4. Last. Any key, order, or live-fetch sentence, plus the refused-imports fence. The fence is `_BLOCKED` and `unified_margin_trader`. This run does not add to it and does not import it.

Packages still excluded by `more_layers`: atn, command_centers, conversion, identity, inhouse_ai, miner, monitors, swarm_motion. `generated` left that list because its score model is deterministic and does not fetch. The other exclusions stay.

Within a stage, packages are alphabetical. The first package is `alignment`.
Stage 1 is the deterministic read-only packages. This run opens generated and swarm, after alignment. Organism is stage 4 because its join loads the in-house adapter chain.
Stage 2 is open. A stage-2 module whose import loads an adapter or an HTTP client, starts a process, or writes outside the sandbox is refused. A stage-2 entry point is refused when the no-argument call or a real-argument call does any of those, or does not finish. `atn` stays excluded. `conversion` has no public function or method and stays excluded.

## Counts

| Stage | Package | Listed | Public entry points | Reachable now | Tested | Refused |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | alignment | 36 | 24 | 11 | 11 | 13 |
| 1 | generated | 8 | 4 | 4 | 4 | 0 |
| 1 | swarm | 79 | 41 | 24 | 14 | 17 |
| 2 | atn | 57 | 28 | 0 | 0 | 28 |
| 2 | cognition | 44 | 14 | 1 | 1 | 13 |
| 2 | conversion | 170 | 0 | 0 | 0 | 0 |
| 2 | decoders | 161 | 80 | 4 | 4 | 76 |
| 2 | evaluation | 20 | 10 | 6 | 6 | 4 |
| 2 | gates | 24 | 12 | 3 | 3 | 9 |
| 2 | observer | 104 | 63 | 24 | 24 | 39 |
| 2 | s51 | 55 | 24 | 1 | 1 | 23 |
| 3 | accounting | 50 | 0 | 0 | 0 | 0 |
| 3 | miner | 15 | 0 | 0 | 0 | 0 |
| 4 | analytics | 464 | 167 | 0 | 0 | 167 |
| 4 | appliance | 15 | 7 | 0 | 0 | 7 |
| 4 | approval | 82 | 42 | 0 | 0 | 42 |
| 4 | autonomous | 1745 | 0 | 0 | 0 | 0 |
| 4 | bio | 474 | 206 | 0 | 0 | 206 |
| 4 | bots | 611 | 0 | 0 | 0 | 0 |
| 4 | bots_intelligence | 234 | 0 | 0 | 0 | 0 |
| 4 | bridges | 281 | 0 | 0 | 0 | 0 |
| 4 | briefing | 62 | 34 | 0 | 0 | 34 |
| 4 | code_architect | 98 | 0 | 0 | 0 | 0 |
| 4 | command_centers | 260 | 0 | 0 | 0 | 0 |
| 4 | connectors | 47 | 0 | 0 | 0 | 0 |
| 4 | core | 986 | 452 | 0 | 0 | 452 |
| 4 | data_feeds | 251 | 118 | 0 | 0 | 118 |
| 4 | exchanges | 643 | 0 | 0 | 0 | 0 |
| 4 | governance | 204 | 105 | 0 | 0 | 105 |
| 4 | grants | 77 | 44 | 0 | 0 | 44 |
| 4 | harmonic | 605 | 278 | 0 | 0 | 278 |
| 4 | identity | 16 | 0 | 0 | 0 | 0 |
| 4 | inhouse_ai | 145 | 0 | 0 | 0 | 0 |
| 4 | integrations | 167 | 65 | 0 | 0 | 65 |
| 4 | intelligence | 597 | 274 | 0 | 0 | 274 |
| 4 | launch | 97 | 0 | 0 | 0 | 0 |
| 4 | monitors | 345 | 158 | 0 | 0 | 158 |
| 4 | observability | 27 | 9 | 0 | 0 | 9 |
| 4 | operator | 1080 | 0 | 0 | 0 | 0 |
| 4 | organism | 3 | 1 | 0 | 0 | 1 |
| 4 | plumber | 497 | 271 | 0 | 0 | 271 |
| 4 | portals | 74 | 51 | 0 | 0 | 51 |
| 4 | portfolio | 322 | 0 | 0 | 0 | 0 |
| 4 | queen | 1348 | 566 | 0 | 0 | 566 |
| 4 | saas | 83 | 0 | 0 | 0 | 0 |
| 4 | scanners | 335 | 0 | 0 | 0 | 0 |
| 4 | search | 21 | 5 | 0 | 0 | 5 |
| 4 | simulation | 440 | 200 | 0 | 0 | 200 |
| 4 | strategies | 474 | 0 | 0 | 0 | 0 |
| 4 | swarm_motion | 49 | 10 | 0 | 0 | 10 |
| 4 | trading | 2023 | 0 | 0 | 0 | 0 |
| 4 | unified_margin_trader | 1643 | 0 | 0 | 0 | 0 |
| 4 | utils | 1162 | 455 | 0 | 0 | 455 |
| 4 | vault | 418 | 195 | 0 | 0 | 195 |
| 4 | wisdom | 755 | 375 | 0 | 0 | 375 |

## Fence

These packages are stage 4 because they are on the refused-imports fence or an inventory row says order. `body_call` returns `live_orders: refused` and does not import them.

- `bots`
- `bots_intelligence`
- `bridges`
- `exchanges`
- `scanners`
- `trading`
- `unified_margin_trader`

## Stage 4

`alignment/unified_directive.py` `get_unified_directive` is not a stage-1 tool. Queen is stage 4. Miner is stage 3. `body_call` refuses it now. The no-argument call is in the call sweep.

Calling `get_unified_directive` constructs `UnifiedHarmonicDirective` with auto-wire on. That constructs `QueenAIBridge` and `MinerAIBridge`. Each bridge loads `AureonBrainAdapter` as the reasoning backend when the Ollama switchboard is missing or unhealthy, and each bridge wires itself to a `ThoughtBus`. The call imports `aureon.queen`, `aureon.miner`, and `aureon.swarm_motion`, and it attempted a connection to `127.0.0.1:11434`. The sweep blocked that socket.

## This run

`alignment` stays the first stage-1 package. `get_pillar_alignment` stays, with `auto_load_pillars` false. `get_unified_directive` is not a stage-1 tool. This run opens `generated` and `swarm`. `organism` is not opened.
Generated was on the more_layers exclusion list. It is open because `aureon/generated/research_cinema/harmonic_nexus_score_model.py` imports only dataclasses and its module docstring calls it a deterministic helper, not trading authority. The four entry points are `build_default_inputs`, `HarmonicNexusScoreInputs.normalized`, `harmonic_nexus_score`, and `score_breakdown`. `tests/generated/test_harmonic_nexus_score_model.py` shows all-ones inputs score 100.0. That 100 is the weighted sum in that file. It does not score any Aureon or HNC claim and cannot be quoted as evidence.
`body_call` refuses `organism/repository_layers.py` `compose_repository_layers`. With the checkout beside `NEXUS-LIVE-FEED-` and `Aureon-Trading--Project-Sero`, that call uses `Path(__file__).parents[3]`, independent of `AUREON_REPOS_ROOT`, and execs those sibling modules outside the pin. One call also loads `core.organism_composition`, and through that `aureon.inhouse_ai.llm_adapter`, `agent_runner`, `orchestrator`, `aureon.ollama_config`, and `aureon.autonomous.aureon_internal_coding_workforce`. `inhouse_ai` stays excluded. Organism reachable is 0.
`body_call` refuses `swarm/capability_grid.py` `build_lane`. `build_lane("fintech")` imports `aureon.accounting`, and that package init reaches `aureon.autonomous.aureon_internal_coding_workforce`, which imports `aureon.inhouse_ai` and `aureon.ollama_config`. Swarm's other entry points stay. Swarm reachable is 24.
The other swarm tools use fixtures from the swarm tests or fixed example arguments. Classes that need nested agent instances stay off the constructor allowlist: Cluster, Company, Zone, FleadhCompany, VisitorAgent, and WorkerAgent. Name-blocked `run_` entry points stay refused. Properties such as SwarmAgent.purity are not given tools because the worker calls methods. `validate_seat_receipt` stays reachable through `body_call` and is not a second tool: the public result cap would drop receipt fields before another call.
Stage 2 tools call through `dispatch`. The inputs are the tests and committed files named on each tool. `atn` stays excluded because its modules load an HTTP client. `conversion` has no public function or method and stays excluded. The constructor allowlist, the `__post_init__` refusal, the `AUREON_PUBLIC_SWEEP` start refusal, and the pin check are unchanged.
Import refusals:
- `atn/aureon_atn_backtest.py`: module import loads an adapter or http client
- `atn/aureon_atn_forensics.py`: module import loads an adapter or http client
- `atn/aureon_atn_monitor.py`: module import loads an adapter or http client
- `decoders/emerald_spec.py`: module import loads an adapter or http client
- `decoders/grail_convergence.py`: module import loads an adapter or http client
Import errors that are not refusals:
- `s51/aureon_51.py`: ImportError: Refused imports: aureon.exchanges, aureon.trading, unified_margin_trader, aureon.bots, aureon.bots_intelligence, aureon.bridges, aureon.scanners. No keys are present. Refused: aureon.exchanges
- `s51/aureon_51_live.py`: ModuleNotFoundError: No module named 'websockets'
Call refusals from the sweep:
- `alignment/unified_directive.py` `get_unified_directive`: call loads a banned chain or opens a connection
- `evaluation/measured_proof.py` `self_coder_report`: call loads a banned chain or opens a connection. The same call started a process. The sweep blocked it.
- `gates/panel.py` `auris_panel`: call loads a banned chain or opens a connection
- `gates/panel.py` `build_vault`: call loads a banned chain or opens a connection
- `gates/switchboard.py` `read_organism`: call loads a banned chain or opens a connection
These five were reachable and had no tool. `body_call` and `dispatch` refuse them. The constructor allowlist is unchanged.
- `decoders/book_of_ur.py` `test_phi_resonance_me`: untested stage-2 entry point is not called. The argument is a SumerianMe. That class is not on the constructor allowlist, so the public server does not build one. The sweep uses the catalog entry ENSHIP from aureon/decoders/book_of_ur.py.
- `observer/momentum.py` `set_momentum_tracker`: untested stage-2 entry point is not called. The argument is a MomentumTracker. The class is not on the constructor allowlist. The sweep constructs an empty tracker inside the worker.
- `observer/predictor.py` `make_predictor`: untested stage-2 entry point is not called. The argument is a HarmonicObserver. The class is not on the constructor allowlist. The sweep uses the construction in tests/observer/test_predictor_contract.py: trace_interval_s 1.0 and publish_to_bus false.
- `observer/wave_predictor.py` `make_predictor`: untested stage-2 entry point is not called. The argument is a WavePredictor. The class is not on the constructor allowlist. The sweep constructs an empty predictor inside the worker.
- `observer/wave_predictor.py` `set_wave_predictor`: untested stage-2 entry point is not called. The argument is a WavePredictor. The class is not on the constructor allowlist. The sweep constructs an empty predictor inside the worker.
## Count reconciliation

Main `c1ae468d` recorded reachable 85. Stage 1 was 39 (alignment 11, generated 4, swarm 24). Stage 2 was 46 (atn 0, cognition 1, conversion 0, decoders 5, evaluation 7, gates 3, observer 29, s51 1). 39 + 46 = 85. Tested on that main was the 29 stage-1 tool entry points below. Stage 2 tested was 0. Registering a tool does not add a reachable row. The tool calls an entry point that was already reachable.
Stage 1 reachable now: 39. Stage 2 reachable now: 39. 39 + 39 = 78.
Stage 1 tested now: 29. Stage 2 tested now: 39. 29 + 39 = 68.
Every stage-1 entry point that was tested on main is still tested. None dropped out:
No stage-1 tested entry point dropped out.
- `alignment/harmonic_resonance.py` `HarmonicAnalysis.to_dict`
- `alignment/harmonic_resonance.py` `analyse_frequency_harmony`
- `alignment/harmonic_resonance.py` `compute_phase_coherence`
- `alignment/harmonic_resonance.py` `compute_signal_consensus`
- `alignment/harmonic_resonance.py` `consonance_score`
- `alignment/harmonic_resonance.py` `derive_phase`
- `alignment/harmonic_resonance.py` `full_harmonic_analysis`
- `alignment/harmonic_resonance.py` `geometric_mean`
- `alignment/pillar_alignment.py` `AlignmentCycleResult.to_dict`
- `alignment/pillar_alignment.py` `get_pillar_alignment`
- `alignment/unified_directive.py` `MasterDirective.to_dict`
- `generated/research_cinema/harmonic_nexus_score_model.py` `HarmonicNexusScoreInputs.normalized`
- `generated/research_cinema/harmonic_nexus_score_model.py` `build_default_inputs`
- `generated/research_cinema/harmonic_nexus_score_model.py` `harmonic_nexus_score`
- `generated/research_cinema/harmonic_nexus_score_model.py` `score_breakdown`
- `swarm/agent.py` `SwarmAgent.propose`
- `swarm/agent.py` `SwarmAgent.substrate`
- `swarm/agent.py` `SwarmAgent.to_dict`
- `swarm/coherence.py` `ClusterCoherence.gamma`
- `swarm/coherence.py` `ClusterCoherence.to_dict`
- `swarm/druidic_council.py` `CouncilReceipt.to_dict`
- `swarm/druidic_council.py` `SeatReceipt.to_dict`
- `swarm/druidic_council.py` `build_seat_receipt`
- `swarm/druidic_council.py` `voice_for_gamma`
- `swarm/fleadh.py` `steer_flow`
- `swarm/memory_bus.py` `CausalEchoBus.echo`
- `swarm/memory_bus.py` `CausalEchoBus.to_dict`
- `swarm/queen_gate.py` `Actualization.to_dict`
- `swarm/steering.py` `SteeringField.steer`
Stage 1 still has reachable entry points that were not tested on main and are not tested now. This run did not remove them from tested, because they were not tested:
- `swarm/agent.py` `SwarmAgent.purity`
- `swarm/agent.py` `SwarmAgent.update`
- `swarm/auris_node_receipts.py` `issue_auris_node_receipt`
- `swarm/auris_node_receipts.py` `validate_auris_node_receipt`
- `swarm/auris_node_receipts.py` `validate_hnc_evidence`
- `swarm/auris_node_receipts.py` `validate_provider_moment`
- `swarm/coherence.py` `ClusterCoherence.warm`
- `swarm/druidic_council.py` `validate_council_receipt`
- `swarm/druidic_council.py` `validate_seat_receipt`
- `swarm/memory_bus.py` `CausalEchoBus.possibilities`
Stage 2 reachable fell by 7, from 46 to 39. The call sweep refused `self_coder_report`. Five reachable entry points had no tool. `log_blocked_fallback` would write a fallback log for an event that did not happen, so `body_call` refuses it.
- `evaluation/measured_proof.py` `self_coder_report`: call loads a banned chain or opens a connection.
- `decoders/book_of_ur.py` `test_phi_resonance_me`: untested stage-2 entry point is not called.
- `observer/momentum.py` `set_momentum_tracker`: untested stage-2 entry point is not called.
- `observer/predictor.py` `make_predictor`: untested stage-2 entry point is not called.
- `observer/wave_predictor.py` `make_predictor`: untested stage-2 entry point is not called.
- `observer/wave_predictor.py` `set_wave_predictor`: untested stage-2 entry point is not called.
- `observer/live_data_policy.py` `log_blocked_fallback`: fallback log is not emitted for an event that did not happen.
Those seven are the only entry points that left the reachable set since main `c1ae468d`. 85 - 7 = 78. Stage 2's remaining 39 reachable entry points are the 39 tested tools. 39 + 39 = 78 reachable. 29 + 39 = 68 tested.

The pin stays `8aa6a2d971cc529484e2a5e261e28afafab4e4f4`. The alignment modules at this checkout match that pin, so the tools do not need a newer commit. `GUARD_BLOB` and `INVENTORY_SHA256` are unchanged.

## MCP SDK

This server imports `FastMCP` from `mcp.server.fastmcp` and passes `host`, `port`, and `streamable_http_path` to that constructor. The requirement is `mcp==1.30.0,<2` in `mcp/aureon_public/requirements.txt` and `mcp/pyproject.toml`. That specifier matches 1.30.0 and excludes every 2.x release. Migration to SDK v2 is a later decision.

The claim that official Python SDK v2 renamed `FastMCP` to `MCPServer` was checked against the published package and the v2 source. The claim is true.

- PyPI project `mcp`: `info.version` is 2.3.0. The newest 1.x release is 1.30.0. https://pypi.org/pypi/mcp/json
- Release v2.0.0, published 28 July 2026, says `FastMCP` is now `MCPServer`, v1.x is maintenance-only on branch `v1.x`, and a project that is not migrating should keep a `<2` upper bound, for example `mcp>=1.28,<2`. https://github.com/modelcontextprotocol/python-sdk/releases/tag/v2.0.0
- Migration guide, section `FastMCP` renamed to `MCPServer`: `from mcp.server.fastmcp import FastMCP` becomes `from mcp.server.mcpserver import MCPServer`. https://py.sdk.modelcontextprotocol.io/v2/migration/
- Tag v2.0.0 and tag v2.3.0 `src/mcp/server/__init__.py` export `MCPServer` from `.mcpserver`. https://github.com/modelcontextprotocol/python-sdk/blob/v2.3.0/src/mcp/server/__init__.py
- Tag v2.3.0 `src/mcp/server/mcpserver/server.py` defines `class MCPServer`. `MCPServer.__init__` takes no `host`, `port`, or `streamable_http_path`. Those arguments are on `run(transport="streamable-http")`. The default name when none is passed is `mcp-server`. `instructions` is no longer the second positional parameter. https://github.com/modelcontextprotocol/python-sdk/blob/v2.3.0/src/mcp/server/mcpserver/server.py
- `src/mcp/server/fastmcp/__init__.py` on tag v2.3.0 is not published. The raw URL returns HTTP 404. https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/v2.3.0/src/mcp/server/fastmcp/__init__.py
- v1 documentation stays at https://py.sdk.modelcontextprotocol.io/v1/

The same v2.0.0 notes also replace `ClientSession` plus the transport clients with `Client`, and the v2.3.0 constructor no longer accepts `host`, `port`, or `streamable_http_path`. This server still passes those three to `FastMCP`, and the measured client still uses `ClientSession`. Staying on 1.30.0 keeps that call shape.

The protocol proof is the stdio session and the Streamable HTTP session bound to `127.0.0.1`. A Hugging Face Space scaffold and remote HTTP auth stay for a later PR. Stage 2 is this run.

