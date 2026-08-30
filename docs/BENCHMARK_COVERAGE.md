# Benchmark coverage — the march to 100%

> Derived from the committed Tier-A report + the filesystem. Nothing invented;
> the uncovered list is the roadmap, the ratchet makes progress one-way.

- Tier-A benchmarks: **76** (all passed: True)
- Unique modules pinned: **72** of 1127 on disk
- Domain coverage: **23/40** (0.575)

## Per-domain

| Domain | Modules | Pinned | Covered |
|---|---|---|---|
| accounting | 11 | 1 | yes |
| alignment | 4 | 0 | **no** |
| analytics | 46 | 4 | yes |
| atn | 4 | 0 | **no** |
| autonomous | 114 | 0 | **no** |
| bio | 41 | 30 | yes |
| bots | 33 | 0 | **no** |
| bots_intelligence | 22 | 0 | **no** |
| bridges | 18 | 0 | **no** |
| code_architect | 10 | 0 | **no** |
| cognition | 7 | 3 | yes |
| command_centers | 17 | 0 | **no** |
| conversion | 11 | 0 | **no** |
| core | 77 | 1 | yes |
| data_feeds | 22 | 1 | yes |
| decoders | 12 | 0 | **no** |
| exchanges | 41 | 1 | yes |
| generated | 3 | 0 | **no** |
| harmonic | 35 | 2 | yes |
| inhouse_ai | 9 | 1 | yes |
| integrations | 20 | 0 | **no** |
| intelligence | 36 | 1 | yes |
| miner | 2 | 0 | **no** |
| monitors | 26 | 1 | yes |
| observer | 15 | 1 | yes |
| operator | 33 | 6 | yes |
| portfolio | 32 | 1 | yes |
| queen | 80 | 1 | yes |
| s51 | 6 | 0 | **no** |
| saas | 16 | 1 | yes |
| scanners | 19 | 1 | yes |
| search | 5 | 0 | **no** |
| simulation | 35 | 0 | **no** |
| strategies | 36 | 1 | yes |
| swarm | 10 | 4 | yes |
| swarm_motion | 5 | 0 | **no** |
| trading | 94 | 1 | yes |
| utils | 42 | 1 | yes |
| vault | 41 | 6 | yes |
| wisdom | 37 | 1 | yes |

## Pins outside `aureon/`

- `scripts/validation/benchmark_nasa_sky.py`

## Uncovered domains (the roadmap)

- `alignment` — 4 modules, zero pins
- `atn` — 4 modules, zero pins
- `autonomous` — 114 modules, zero pins
- `bots` — 33 modules, zero pins
- `bots_intelligence` — 22 modules, zero pins
- `bridges` — 18 modules, zero pins
- `code_architect` — 10 modules, zero pins
- `command_centers` — 17 modules, zero pins
- `conversion` — 11 modules, zero pins
- `decoders` — 12 modules, zero pins
- `generated` — 3 modules, zero pins
- `integrations` — 20 modules, zero pins
- `miner` — 2 modules, zero pins
- `s51` — 6 modules, zero pins
- `search` — 5 modules, zero pins
- `simulation` — 35 modules, zero pins
- `swarm_motion` — 5 modules, zero pins
