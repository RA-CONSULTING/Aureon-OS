# aureon-public

MCP lets outside models call Aureon's tools. No outside model or API becomes Aureon's reasoning. The cognition runs in Aureon's own code.

This process is a read-only FastMCP server named `aureon-public`. It exposes the milestone-1 tools, resources, and prompts. It does not place orders, read keys, start circulation, self-code, self-repair, or write the repository or `state/`.

`aureon` is pinned to commit `8aa6a2d971cc529484e2a5e261e28afafab4e4f4`, the same pin as the Hugging Face Spaces. A local checkout run uses its own commit, not the pin. The MCP SDK pin is `mcp==1.30.0` in `requirements.txt` and `pyproject.toml`. That is the version this server was installed and tested with. `mcp==1.30.0` provides `FastMCP` (`mcp.server.fastmcp`). MCP 2 renamed that class.

Any public hosting, including the future aureon-public Space, must set `AUREON_PUBLIC_REQUIRE_PIN=1`. That refuses to start unless `aureon_source` is kind `pinned` at `8aa6a2d971cc529484e2a5e261e28afafab4e4f4`. Local runs leave the variable unset and keep the visible `aureon_source` label. Each Hugging Face Space entry point calls `enforce_public_pin()` itself before `demo.launch`.

The operator process is separate: `python -m aureon_operator`. It stays off unless `AUREON_OPERATOR_MCP=1`, speaks stdio only, and refuses live orders. It does not import `aureon.trading` or the other blocked packages.

`repo_root()` and `aureon_source()` raise `FileNotFoundError` when the process is not inside a checkout that contains `huggingface/hnc-field/guard.py` and `aureon/core/hnc_field.py`. This server needs that checkout. It does not invent a 'no checkout' status.

A layer counts as full depth only where its real entry points are called.
Each figure is reachable public functions and methods out of the public functions and methods in the pinned `docs/mcp/inventory.json`.

| Package | Reachable | Public entry points |
| --- | ---: | ---: |
| accounting | 0 | 0 |
| alignment | 12 | 24 |
| analytics | 0 | 167 |
| appliance | 0 | 7 |
| approval | 0 | 42 |
| atn | 0 | 28 |
| autonomous | 0 | 0 |
| bio | 0 | 206 |
| bots | 0 | 0 |
| bots_intelligence | 0 | 0 |
| bridges | 0 | 0 |
| briefing | 0 | 34 |
| code_architect | 0 | 0 |
| cognition | 1 | 14 |
| command_centers | 0 | 0 |
| connectors | 0 | 0 |
| conversion | 0 | 0 |
| core | 0 | 452 |
| data_feeds | 0 | 118 |
| decoders | 5 | 80 |
| evaluation | 7 | 10 |
| exchanges | 0 | 0 |
| gates | 6 | 12 |
| generated | 4 | 4 |
| governance | 0 | 105 |
| grants | 0 | 44 |
| harmonic | 0 | 278 |
| identity | 0 | 0 |
| inhouse_ai | 0 | 0 |
| integrations | 0 | 65 |
| intelligence | 0 | 274 |
| launch | 0 | 0 |
| miner | 0 | 0 |
| monitors | 0 | 158 |
| observability | 0 | 9 |
| observer | 29 | 63 |
| operator | 0 | 0 |
| organism | 0 | 1 |
| plumber | 0 | 271 |
| portals | 0 | 51 |
| portfolio | 0 | 0 |
| queen | 0 | 566 |
| s51 | 1 | 24 |
| saas | 0 | 0 |
| scanners | 0 | 0 |
| search | 0 | 5 |
| simulation | 0 | 200 |
| strategies | 0 | 0 |
| swarm | 24 | 41 |
| swarm_motion | 0 | 10 |
| trading | 0 | 0 |
| unified_margin_trader | 0 | 0 |
| utils | 0 | 455 |
| vault | 0 | 195 |
| wisdom | 0 | 375 |

The extra package tools are helpers. A helper call is not that layer's cognition.

The order for opening the rest of the inventory is `COVERAGE_PLAN.md`. Alignment is the first package in that order.

`body_call` runs one inventoried function or method. `body_surface` reads a module or class and does not construct it. `body_depth` reports the same ratio as this table. `body_registry` names the servers. The operator tool is `body_call_operator`. Live orders stay refused. A checkout file is imported only when its git blob matches pin `8aa6a2d9`. The plan and the call rules are in `docs/mcp/REGISTRY.md`.

Licence: MIT, the same licence as the repository `LICENSE`.

## Two brain paths

`hnc_reality_step` takes `enable_multiverse` and reports that value in the output.

The class default `HarmonicRealityField()` sets `enable_multiverse=True` (multiverse on). This tool's default is that class default.

Do not mix the two committed paths in `huggingface/hnc-field/replay/brain.json`:

| Path | `enable_multiverse` | Coherence in the file |
| --- | --- | --- |
| Class default, multiverse on (`multiverse_extension`) | `true` | `0.857719007627168` |
| Multiverse off (`hnc`) | `false` | `0.9331334813083556` |

Those figures are cited from that file. They are not a track record. Trade readiness is HOLD.

## Which Auris

Four meanings stay separate.

- The conjecture is the five symbolic-life markers in `LambdaEngine`. It is not called.
- The nine nodes are `QueenHiveMind.read_auris_nodes` and `AURIS_NODES`. That is `auris_nodes` and `aureon://auris/nodes`.
- The persona on `QueenHiveMind` is not scored.
- The coherence evaluator is `QueenHiveMind.get_auris_coherence`. That is `auris_coherence`.

Only the nine nodes and `get_auris_coherence` are real functions exposed here. If any of the nine nodes has no reading, `auris_coherence` returns status `no_data`, coherence null, and the missing node names. The Auris-to-Lambda link is HOLD.

`lambda_engine_step` returns status `unavailable` when readings are missing or fewer than two. It does not fill the result with 0.

## Install

From a checkout of this branch:

```bash
python3 -m venv .venv-aureon-public
source .venv-aureon-public/bin/activate
pip install -e mcp
```

`pip install -e mcp` installs this package and the pinned `aureon` commit. The install is editable so the server can still see `huggingface/` replay files in the checkout.

## Run

stdio, which is what desktop clients use:

```bash
python -m aureon_public
```

Optional streamable HTTP on `127.0.0.1:8077` at path `/mcp`:

```bash
python -m aureon_public --transport streamable-http --host 127.0.0.1 --port 8077
```

The HTTP URL is `http://127.0.0.1:8077/mcp`.

## Claude Desktop

Put this in the Claude Desktop MCP config. Use the venv interpreter and the checkout path.

```json
{
  "mcpServers": {
    "aureon-public": {
      "command": "/absolute/path/to/.venv-aureon-public/bin/python",
      "args": ["-m", "aureon_public"]
    }
  }
}
```

## Cursor

The same stdio block goes in Cursor's MCP settings (`mcp.json`):

```json
{
  "mcpServers": {
    "aureon-public": {
      "command": "/absolute/path/to/.venv-aureon-public/bin/python",
      "args": ["-m", "aureon_public"]
    }
  }
}
```

## Any other MCP client

Any client that speaks MCP stdio can use the same command. A client that speaks streamable HTTP can use `http://127.0.0.1:8077/mcp` after the HTTP command above. No API key is read. No outside model becomes the reasoning: the client only receives the tool results computed in this process.

## What is not on this server

Orders, exchange keys, `aureon.exchanges`, `aureon.trading`, `unified_margin_trader`, `aureon.bots`, `aureon.bots_intelligence`, `aureon.bridges`, `aureon.scanners`, circulation start, self-code, and self-repair are not tools. The operator Flask routes in `aureon/bio/mcp_transport.py` are a different process and are not widened here.
