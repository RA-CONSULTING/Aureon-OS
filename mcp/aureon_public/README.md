---
title: aureon-public
emoji: "🔷"
colorFrom: blue
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# aureon-public

This is a partial release covering stages 1 and 2 of 4. Stages 3 and 4 stay closed. That includes miner, queen, exchanges, orders, and keys. `COVERAGE_PLAN.md` records the counts: listed symbols 20083, public entry points 4388, reachable now 69, tested 69, refused 4319. Stage 1 reachable now is 30 and stage 1 tested now is 30. Stage 2 reachable now is 39 and stage 2 tested now is 39. 30 + 39 = 69 reachable. 30 + 39 = 69 tested.

Miner is stage 3: 15 listed, 0 public entry points, reachable 0, tested 0, refused 0. Queen is stage 4: 1348 listed, 566 public entry points, reachable 0, tested 0, refused 566. Exchanges are stage 4: 643 listed, 0 public entry points, reachable 0, tested 0, refused 0. Accounting is stage 3 with reachable 0. Trading is stage 4 with reachable 0.

The measured tests are the call sweep. It calls every entry point that was still reachable, with no arguments, and calls each stage-2 entry point again with the real arguments in `stage2_arguments.py`. Connections, process starts, and writes outside the sandbox are logged: the committed record says sockets blocked, processes blocked, and writes outside the sandbox blocked. A call that opens a connection, starts a process, writes outside the sandbox, or loads queen, miner, swarm_motion, inhouse_ai, ollama_config, or an HTTP client is refused. Other arguments have not been swept.

The Space entry is `python -m aureon_public.space`. It sets `AUREON_PUBLIC_REQUIRE_PIN=1` and `AUREON_OBSERVER_MODE=dry_run`, and it refuses to start when `AUREON_PUBLIC_SWEEP` is set. The image installs `requirements.txt` (`mcp==1.30.0,<2` and aureon pin `8aa6a2d971cc529484e2a5e261e28afafab4e4f4`) and then the mcp package with `--no-deps`, the same runtime install as `measured/aureon_public_stage1_run.sh`. The image does not install test requirements and does not contain `AUREON_PUBLIC_API_KEY`.

`AUREON_PUBLIC_OPEN=1` is set in the image, so the read-only stage-1 and stage-2 surface is served on port 7860 without a key. Set `AUREON_PUBLIC_API_KEY` in the Space secret settings to require `Authorization: Bearer`. A missing or wrong bearer then receives HTTP 401. With neither the key nor `AUREON_PUBLIC_OPEN=1`, the process binds to `127.0.0.1` only and refuses `0.0.0.0`. The image keeps `AUREON_PUBLIC_HOST=0.0.0.0` whenever it is in open mode or keyed mode. The MCP SDK turns DNS-rebinding protection on for a `127.0.0.1` bind and then answers HTTP 421 to `Host: *.hf.space`. A `0.0.0.0` bind accepts that Host header, which is what Hugging Face's proxy sends. The public HTTP server uses MCP SDK 1.30 stateless JSON responses (`stateless_http` and `json_response`). `GET /mcp` returns HTTP 405. That long-lived event stream is not used, and it does not take an in-flight call slot. `AUREON_PUBLIC_MAX_INFLIGHT` (default 4, the same size as the public worker pool) caps concurrent in-flight POST `/mcp` requests. Each tool call starts a worker process. A POST over that cap returns HTTP 503 with `error` `busy`. `AUREON_PUBLIC_RATE_LIMIT` (default 120) and `AUREON_PUBLIC_RATE_WINDOW_S` (default 60) limit requests per client. `AUREON_PUBLIC_TRUSTED_PROXY_HOPS` defaults to 1. When `X-Forwarded-For` is present and has at least that many values, the client is the value that many hops from the right. With the default, that is the last value, including a header whose only value is the client address. A fake first hop in front of that value does not get its own bucket. Zero trusted proxy hops ignores the header and uses the socket peer. The real Hugging Face header shape has to be confirmed on the private Space before this default is treated as settled. `AUREON_PUBLIC_FORWARDED_DIAG=1` records hop count and whether each hop is an IPv4 address, an IPv6 address, or something else. It does not store the addresses. Open mode buckets by that address only. A bearer is the client id only when it matches `AUREON_PUBLIC_API_KEY`. The tracked-id table is capped by `AUREON_PUBLIC_RATE_MAX_CLIENTS` (default 4096) and drops expired windows. `AUREON_PUBLIC_MAX_BODY_BYTES` (default 1048576) counts bytes as they arrive, including a chunked body with no content-length. Every body message is counted until `more_body` is false or the client disconnects. Empty chunks do not stop that count, and the unread remainder is not passed through. `AUREON_PUBLIC_REQUEST_TIMEOUT_S` (default 30) limits a POST and also bounds that body read. A rate limit returns HTTP 429. A body over the cap returns HTTP 413. An idle or unfinished body returns HTTP 408 with `error` `body_timeout`. A POST that passes the timeout returns HTTP 504.

This scaffold is not deployed and it does not create a Hugging Face repository. The measured session was taken without Docker. `.github/workflows/aureon-public-space.yml` builds this image on a pull request and runs `python -m aureon_public.space --check`. `AUREON_REF` defaults to `0390194b80cddb66c8cfd052efe3aa4f9d1545d6`, the merge commit of #225. That tree contains the aureon pin. Do not point `AUREON_REF` at cf43882e as a standing default. The first Hugging Face build log must show the `AUREON_REF` build arg. Uvicorn is started with `proxy_headers` off and an empty `forwarded_allow_ips`, so `X-Forwarded-For` is read only by this server's own middleware.

MCP lets outside models call Aureon's tools. No outside model or API becomes Aureon's reasoning. The cognition runs in Aureon's own code.

This process is a read-only FastMCP server named `aureon-public`. It exposes the milestone-1 tools, resources, and prompts. It does not place orders, read keys, start circulation, self-code, self-repair, or write the repository or `state/`.

`aureon` is pinned to commit `8aa6a2d971cc529484e2a5e261e28afafab4e4f4`, the same pin as the Hugging Face Spaces. A local checkout run uses its own commit, not the pin. The MCP SDK requirement is `mcp==1.30.0,<2` in `requirements.txt` and `pyproject.toml`. That installs 1.30.0 and excludes every 2.x release. This server imports `FastMCP` from `mcp.server.fastmcp`. The check that MCP 2 renamed that class to `MCPServer` is in `COVERAGE_PLAN.md`, with the sources. Migration to SDK v2 is a later decision.

Any public hosting, including this aureon-public Space scaffold, must set `AUREON_PUBLIC_REQUIRE_PIN=1`. That refuses to start unless `aureon_source` is kind `pinned` at `8aa6a2d971cc529484e2a5e261e28afafab4e4f4`. Local runs of `python -m aureon_public` leave the variable unset and keep the visible `aureon_source` label. `python -m aureon_public.space` calls `enforce_public_pin()` before it binds.

The operator process is separate: `python -m aureon_operator`. It stays off unless `AUREON_OPERATOR_MCP=1`, speaks stdio only, and refuses live orders. It does not import `aureon.trading` or the other blocked packages.

`repo_root()` and `aureon_source()` raise `FileNotFoundError` when the process is not inside a checkout that contains `huggingface/hnc-field/guard.py` and `aureon/core/hnc_field.py`. This server needs that checkout. It does not invent a 'no checkout' status.

A layer counts as full depth only where its real entry points are called.
Each figure is reachable public functions and methods out of the public functions and methods in the pinned `docs/mcp/inventory.json`.

| Package | Reachable | Public entry points |
| --- | ---: | ---: |
| accounting | 0 | 0 |
| alignment | 11 | 24 |
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
| decoders | 4 | 80 |
| evaluation | 6 | 10 |
| exchanges | 0 | 0 |
| gates | 3 | 12 |
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
| observer | 24 | 63 |
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
| swarm | 15 | 41 |
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

Check the closed-stage report with:

```bash
python -m aureon_public.space --check
```

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
