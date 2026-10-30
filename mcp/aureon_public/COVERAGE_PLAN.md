# Public MCP coverage plan

Counts are the pinned `docs/mcp/inventory.json`. A public entry point is a public function or method. Reachable means `public_entry_refusal` returns None, so `body_call` will run it. A listed module or class is not an entry point. The sha256 below is `INVENTORY_SHA256`. A different inventory file is not loaded.

Inventory sha256: `4bc19ea9b5444a7b8a9abbd3fabf635d083bd25bea6c1b2d6eab2605b4f5716b`

Reproduce:

```bash
env -u PYTHONPATH PYTHONPATH=mcp python3.12 -m aureon_public.coverage_plan --check
bash measured/aureon_public_stage1_run.sh
bash measured/aureon_public_stage2_sweep.sh
bash measured/aureon_public_call_sweep.sh
env -u PYTHONPATH /tmp/aureon-public-venv/bin/python -m pytest tests/test_aureon_public_mcp.py tests/test_aureon_body.py tests/bio/test_mcp_*.py tests/test_aureon_public_alignment.py tests/test_aureon_public_stage1.py --tb=line
```

`--write` rewrites this file from the same function. `measured/aureon_public_stage1_run.sh` installs `mcp/aureon_public/requirements.txt` and `mcp/aureon_public/test-requirements.txt`, then rewrites both `measured/aureon_public_alignment.json` and `measured/aureon_public_stage1.json`. `test-requirements.txt` is the test install: pytest, pytest-timeout, flask, pandas, and scipy. It is not the public server runtime. `measured/aureon_public_stage2_sweep.sh` and `measured/aureon_public_call_sweep.sh` place fake `NEXUS-LIVE-FEED-` and `Aureon-Trading--Project-Sero` checkouts beside the repo, block sockets, and rewrite their measured records. Each record names the pin and the `aureon_source` kind.

Listed symbols: 20083. Public entry points: 4388. Reachable now: 85. The previous plan recorded 89 reachable. Methods open because a constructor is allowlisted: 19. The refused-imports fence is unchanged.
Only the stage-1 tools are tested. Reachable now is what `body_call` still runs after the call sweep. Plan stages 3 and 4 stay closed. Stage 2 reach that remains is untested, unaudited reach, not coverage. The call sweep calls every entry point that was still reachable, with no arguments, and refuses one that opens a connection or loads queen, miner, swarm_motion, inhouse_ai, ollama_config, or an HTTP client. `get_unified_directive` is refused that way. It does not build the queen and miner bridges.

## Stage order

The stage is the inventory safety text, not a new scan.

1. Deterministic read-only. No key, order, live-fetch, process, or write sentence, and the package is not operator-only.
2. A process or write sentence, and still no key, order, or live-fetch sentence.
3. Operator-scoped, with no pure public row and no key, order, or live-fetch sentence.
4. Last. Any key, order, or live-fetch sentence, plus the refused-imports fence. The fence is `_BLOCKED` and `unified_margin_trader`. This run does not add to it and does not import it.

Packages still excluded by `more_layers`: atn, command_centers, conversion, identity, inhouse_ai, miner, monitors, swarm_motion. `generated` left that list because its score model is deterministic and does not fetch. The other exclusions stay.

Within a stage, packages are alphabetical. The first package is `alignment`.
Stage 1 is the deterministic read-only packages. This run opens generated and swarm, after alignment. Organism is stage 4 because its join loads the in-house adapter chain.
Stage 2 has no new tools. Clean stage-2 entry points stay callable through `body_call`. A stage-2 module whose import loads an adapter or an HTTP client, or opens a connection, is refused.

## Counts

| Stage | Package | Listed | Public entry points | Reachable now |
| ---: | --- | ---: | ---: | ---: |
| 1 | alignment | 36 | 24 | 11 |
| 1 | generated | 8 | 4 | 4 |
| 1 | swarm | 79 | 41 | 24 |
| 2 | atn | 57 | 28 | 0 |
| 2 | cognition | 44 | 14 | 1 |
| 2 | conversion | 170 | 0 | 0 |
| 2 | decoders | 161 | 80 | 5 |
| 2 | evaluation | 20 | 10 | 7 |
| 2 | gates | 24 | 12 | 3 |
| 2 | observer | 104 | 63 | 29 |
| 2 | s51 | 55 | 24 | 1 |
| 3 | accounting | 50 | 0 | 0 |
| 3 | miner | 15 | 0 | 0 |
| 4 | analytics | 464 | 167 | 0 |
| 4 | appliance | 15 | 7 | 0 |
| 4 | approval | 82 | 42 | 0 |
| 4 | autonomous | 1745 | 0 | 0 |
| 4 | bio | 474 | 206 | 0 |
| 4 | bots | 611 | 0 | 0 |
| 4 | bots_intelligence | 234 | 0 | 0 |
| 4 | bridges | 281 | 0 | 0 |
| 4 | briefing | 62 | 34 | 0 |
| 4 | code_architect | 98 | 0 | 0 |
| 4 | command_centers | 260 | 0 | 0 |
| 4 | connectors | 47 | 0 | 0 |
| 4 | core | 986 | 452 | 0 |
| 4 | data_feeds | 251 | 118 | 0 |
| 4 | exchanges | 643 | 0 | 0 |
| 4 | governance | 204 | 105 | 0 |
| 4 | grants | 77 | 44 | 0 |
| 4 | harmonic | 605 | 278 | 0 |
| 4 | identity | 16 | 0 | 0 |
| 4 | inhouse_ai | 145 | 0 | 0 |
| 4 | integrations | 167 | 65 | 0 |
| 4 | intelligence | 597 | 274 | 0 |
| 4 | launch | 97 | 0 | 0 |
| 4 | monitors | 345 | 158 | 0 |
| 4 | observability | 27 | 9 | 0 |
| 4 | operator | 1080 | 0 | 0 |
| 4 | organism | 3 | 1 | 0 |
| 4 | plumber | 497 | 271 | 0 |
| 4 | portals | 74 | 51 | 0 |
| 4 | portfolio | 322 | 0 | 0 |
| 4 | queen | 1348 | 566 | 0 |
| 4 | saas | 83 | 0 | 0 |
| 4 | scanners | 335 | 0 | 0 |
| 4 | search | 21 | 5 | 0 |
| 4 | simulation | 440 | 200 | 0 |
| 4 | strategies | 474 | 0 | 0 |
| 4 | swarm_motion | 49 | 10 | 0 |
| 4 | trading | 2023 | 0 | 0 |
| 4 | unified_margin_trader | 1643 | 0 | 0 |
| 4 | utils | 1162 | 455 | 0 |
| 4 | vault | 418 | 195 | 0 |
| 4 | wisdom | 755 | 375 | 0 |

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
Stage 2 was not started. No stage-2 tool was written.

The pin stays `8aa6a2d971cc529484e2a5e261e28afafab4e4f4`. The alignment modules at this checkout match that pin, so the tools do not need a newer commit. `GUARD_BLOB` and `INVENTORY_SHA256` are unchanged.

