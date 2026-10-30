# Public MCP coverage plan

Counts are the pinned `docs/mcp/inventory.json`. A public entry point is a public function or method. Reachable means `public_entry_refusal` returns None, so `body_call` will run it. A listed module or class is not an entry point. The sha256 below is `INVENTORY_SHA256`. A different inventory file is not loaded.

Inventory sha256: `4bc19ea9b5444a7b8a9abbd3fabf635d083bd25bea6c1b2d6eab2605b4f5716b`

Reproduce:

```bash
env -u PYTHONPATH PYTHONPATH=mcp python3.12 -m aureon_public.coverage_plan --check
```

`--write` rewrites this file from the same function.

Listed symbols: 20083. Public entry points: 4388. Reachable now: 879. Reachable before the constructor allowlist in this run: 876. The allowlist opened 3 dataclass `to_dict` methods. The refused-imports fence is unchanged.

## Stage order

The stage is the inventory safety text, not a new scan.

1. Deterministic read-only. No key, order, live-fetch, process, or write sentence, and the package is not operator-only.
2. A process or write sentence, and still no key, order, or live-fetch sentence.
3. Operator-scoped, with no pure public row and no key, order, or live-fetch sentence.
4. Last. Any key, order, or live-fetch sentence, plus the refused-imports fence. The fence is `_BLOCKED` and `unified_margin_trader`. This run does not add to it and does not import it.

Packages already excluded by `more_layers` stay excluded: atn, command_centers, conversion, generated, identity, inhouse_ai, miner, monitors, swarm_motion. Exclusion is not removed here.

Within a stage, packages are alphabetical. The first package is `alignment`. This run opens that package. Later packages stay on the counts below.

## Counts

| Stage | Package | Listed | Public entry points | Reachable now |
| ---: | --- | ---: | ---: | ---: |
| 1 | alignment | 36 | 24 | 12 |
| 1 | generated | 8 | 4 | 0 |
| 1 | organism | 3 | 1 | 1 |
| 1 | swarm | 79 | 41 | 10 |
| 2 | atn | 57 | 28 | 0 |
| 2 | cognition | 44 | 14 | 1 |
| 2 | conversion | 170 | 0 | 0 |
| 2 | decoders | 161 | 80 | 10 |
| 2 | evaluation | 20 | 10 | 7 |
| 2 | gates | 24 | 12 | 6 |
| 2 | observer | 104 | 63 | 29 |
| 2 | s51 | 55 | 24 | 1 |
| 3 | accounting | 50 | 0 | 0 |
| 3 | miner | 15 | 0 | 0 |
| 4 | analytics | 464 | 167 | 37 |
| 4 | appliance | 15 | 7 | 2 |
| 4 | approval | 82 | 42 | 20 |
| 4 | autonomous | 1745 | 0 | 0 |
| 4 | bio | 474 | 206 | 96 |
| 4 | bots | 611 | 0 | 0 |
| 4 | bots_intelligence | 234 | 0 | 0 |
| 4 | bridges | 281 | 0 | 0 |
| 4 | briefing | 62 | 34 | 7 |
| 4 | code_architect | 98 | 0 | 0 |
| 4 | command_centers | 260 | 0 | 0 |
| 4 | connectors | 47 | 0 | 0 |
| 4 | core | 986 | 452 | 109 |
| 4 | data_feeds | 251 | 118 | 11 |
| 4 | exchanges | 643 | 0 | 0 |
| 4 | governance | 204 | 105 | 41 |
| 4 | grants | 77 | 44 | 9 |
| 4 | harmonic | 605 | 278 | 58 |
| 4 | identity | 16 | 0 | 0 |
| 4 | inhouse_ai | 145 | 0 | 0 |
| 4 | integrations | 167 | 65 | 7 |
| 4 | intelligence | 597 | 274 | 36 |
| 4 | launch | 97 | 0 | 0 |
| 4 | monitors | 345 | 158 | 0 |
| 4 | observability | 27 | 9 | 4 |
| 4 | operator | 1080 | 0 | 0 |
| 4 | plumber | 497 | 271 | 52 |
| 4 | portals | 74 | 51 | 11 |
| 4 | portfolio | 322 | 0 | 0 |
| 4 | queen | 1348 | 566 | 131 |
| 4 | saas | 83 | 0 | 0 |
| 4 | scanners | 335 | 0 | 0 |
| 4 | search | 21 | 5 | 2 |
| 4 | simulation | 440 | 200 | 18 |
| 4 | strategies | 474 | 0 | 0 |
| 4 | swarm_motion | 49 | 10 | 0 |
| 4 | trading | 2023 | 0 | 0 |
| 4 | unified_margin_trader | 1643 | 0 | 0 |
| 4 | utils | 1162 | 455 | 59 |
| 4 | vault | 418 | 195 | 20 |
| 4 | wisdom | 755 | 375 | 72 |

## Fence

These packages are stage 4 because they are on the refused-imports fence or an inventory row says order. `body_call` returns `live_orders: refused` and does not import them.

- `bots`
- `bots_intelligence`
- `bridges`
- `exchanges`
- `scanners`
- `trading`
- `unified_margin_trader`

## This run

`alignment` is the first stage-1 package. The new tools call its deterministic entry points through `dispatch`, which keeps `PinnedAureonFinder`, the pin blob check, and the operator fence. `PillarAlignment` and `UnifiedHarmonicDirective` are not allowlisted: their constructors wire the thought bus and other packages. `run_synthetic_cycle` stays refused because the name fence rejects `run_`.

The pin stays `8aa6a2d971cc529484e2a5e261e28afafab4e4f4`. The alignment modules at this checkout match that pin, so the tools do not need a newer commit. `GUARD_BLOB` and `INVENTORY_SHA256` are unchanged.

