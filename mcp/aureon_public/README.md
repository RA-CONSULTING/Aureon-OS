# aureon-public

MCP lets outside models call Aureon's tools. No outside model or API becomes Aureon's reasoning. The cognition runs in Aureon's own code.

This process is a read-only FastMCP server named `aureon-public`. It exposes the milestone-1 tools, resources, and prompts. It does not place orders, read keys, start circulation, self-code, self-repair, or write the repository or `state/`.

`aureon` is pinned to commit `a00f744d2e686e916e45b81dd4222408c368e305`, the same pin as the Hugging Face Spaces. A local checkout run uses its own commit, not the pin. The MCP SDK pin is `mcp==1.30.0` in `mcp/aureon_public/requirements.txt` and `mcp/pyproject.toml`. That is the version this server was installed and tested with. `mcp==1.30.0` provides `FastMCP` (`mcp.server.fastmcp`). MCP 2 renamed that class.

Any public hosting, including the future aureon-public Space, must set `AUREON_PUBLIC_REQUIRE_PIN=1`. That refuses to start unless `aureon_source` is kind `pinned` at `a00f744d2e686e916e45b81dd4222408c368e305`. Local runs leave the variable unset and keep the visible `aureon_source` label. Each Hugging Face Space entry point calls `enforce_public_pin()` itself before `demo.launch`.

The operator process is separate: `python -m aureon_operator`. It stays off unless `AUREON_OPERATOR_MCP=1`, speaks stdio only, and refuses live orders. It does not import `aureon.trading` or the other blocked packages.

`repo_root()` and `aureon_source()` raise `FileNotFoundError` when the process is not inside a checkout that contains `huggingface/hnc-field/guard.py` and `aureon/core/hnc_field.py`. This server needs that checkout. It does not invent a 'no checkout' status.

A layer counts as full depth only where its real entry points are called.
Each figure is reachable public functions and methods out of the public functions and methods in the pinned `docs/mcp/inventory.json`.

| Package | Reachable | Public entry points |
| --- | ---: | ---: |
| accounting | 0 | 0 |
| alignment | 24 | 26 |
| analytics | 169 | 267 |
| appliance | 1 | 6 |
| approval | 40 | 47 |
| atn | 0 | 37 |
| autonomous | 0 | 9 |
| bio | 234 | 286 |
| bots | 0 | 0 |
| bots_intelligence | 0 | 0 |
| bridges | 0 | 0 |
| briefing | 41 | 44 |
| code_architect | 0 | 0 |
| cognition | 17 | 20 |
| command_centers | 0 | 2 |
| connectors | 0 | 0 |
| conversion | 0 | 5 |
| core | 518 | 669 |
| data_feeds | 86 | 159 |
| decoders | 80 | 87 |
| evaluation | 8 | 12 |
| exchanges | 0 | 0 |
| gates | 12 | 14 |
| generated | 0 | 4 |
| governance | 103 | 119 |
| grants | 48 | 54 |
| harmonic | 332 | 407 |
| identity | 0 | 0 |
| inhouse_ai | 0 | 0 |
| integrations | 72 | 105 |
| intelligence | 311 | 363 |
| launch | 0 | 3 |
| miner | 0 | 0 |
| monitors | 0 | 211 |
| observability | 9 | 10 |
| observer | 51 | 73 |
| operator | 0 | 7 |
| organism | 1 | 1 |
| plumber | 237 | 268 |
| portals | 52 | 58 |
| portfolio | 0 | 9 |
| queen | 751 | 963 |
| s51 | 24 | 36 |
| saas | 0 | 2 |
| scanners | 0 | 0 |
| search | 4 | 12 |
| simulation | 196 | 284 |
| strategies | 0 | 7 |
| swarm | 43 | 48 |
| swarm_motion | 0 | 35 |
| trading | 0 | 0 |
| unified_margin_trader | 0 | 0 |
| utils | 703 | 880 |
| vault | 229 | 267 |
| wisdom | 436 | 531 |

The extra package tools are helpers. A helper call is not that layer's cognition.

`body_call` runs one inventoried function or method. `body_surface` reads a module or class and does not construct it. `body_depth` reports the same ratio as this table. `body_registry` names the servers. The operator tool is `body_call_operator`. Live orders stay refused. A checkout file is imported only when its git blob matches pin `a00f744d`. The plan and the call rules are in `docs/mcp/REGISTRY.md`.

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
