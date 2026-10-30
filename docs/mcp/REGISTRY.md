# Aureon MCP registry

MCP lets outside models call Aureon's tools. No outside model or API becomes Aureon's reasoning. The cognition runs in Aureon's own code.

## Servers

| Server | Start | Transport | What it calls |
| --- | --- | --- | --- |
| `aureon-public` | `python -m aureon_public` | stdio, or streamable HTTP on `127.0.0.1:8077/mcp` | Public inventory rows for stages that are open |
| `aureon-operator` | `AUREON_OPERATOR_MCP=1 python -m aureon_operator` | stdio only | Operator rows. Live orders are refused before import |

Public hosting sets `AUREON_PUBLIC_REQUIRE_PIN=1`. The four Space entry points call `enforce_public_pin()` before `demo.launch`:

- `huggingface/hnc-field/app.py`
- `huggingface/auris-coherence/app.py`
- `huggingface/qgita-snr/app.py`
- `huggingface/organism-replay/app.py`

The pin is `a00f744d2e686e916e45b81dd4222408c368e305`. A file loaded from the checkout is executed only when its git blob is the blob at that pin. `phenolic_fingerprint.py` uses the same check.

## Tools that address the inventory

The inventory is `docs/mcp/FULL_BODY_PLAN.md` and `docs/mcp/inventory.json`. Every public module, class, function, and method is a row there. The servers do not register one FastMCP tool per row.

| Tool | Form | What it does |
| --- | --- | --- |
| `body_call` | tool | Runs one public function or method. Arguments are a JSON object. |
| `body_surface` | resource read, as a tool | Returns the class or module surface. Does not construct or call it. |
| `body_depth` | tool and `aureon://body/depth` | Counts calls recorded in `measured/body_stageN.json`. |
| `body_registry` | tool and `aureon://body/registry` | Names the servers, the pin, and the blocked imports. |
| `body_call_operator` | operator tool | Same caller, operator rows only. Requires the operator flag. |

A helper in `more_layers.py` is labelled `helper.` and is not that package's depth.

## What is refused

- Blocked imports, on both servers: `aureon.trading`, `aureon.exchanges`, `aureon.bots`, `aureon.bots_intelligence`, `aureon.bridges`, `aureon.scanners`, `unified_margin_trader`. The refusal is `live_orders: refused`. The import does not run.
- Key and personal readers, including `read_identity` and `packet_master_key_from_env`.
- Process, loop, and UI starters.
- Writes into the repo.
- A stage whose number is above `ENABLED_THROUGH` in `mcp/aureon_public/body.py`.

## Stages

1. HNC, harmonic core, Auris, and QGITA.
2. cognition, queen, swarm, swarm_motion, gates, governance, alignment, observer.
3. organism, bio, evaluation, memory and vault, identity readers.
4. data_feeds, atn, decoders, search, portals, monitors, analytics.
5. Trading and exchange packages on the operator server. Live orders refused.
6. The remaining packages. Launch, miner, SaaS, command centers, connectors, autonomous, code architect, in-house AI, and the operator package are listed and not called.
7. This registry and the Space pin gate.

Depth for a package is how many of its entry points a measured sweep actually ran. A row in the plan is not a call. Queen in stage 2 is `compute_zpe_ground` only. `get_swarm_hive` does not return within the call budget. The conversion goal scan is not called, because it fetches prices and prints an execute line. Identity is not read.

HOLD stays explicit: trade readiness, the Auris-to-Lambda link, QGITA detection and false-alarm rates, Schumann f0, and HumanEval not run. `consciousness_*` keys are dropped.
