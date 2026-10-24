# Auris node evaluation

Seed `20261024`, 256 labelled rows. Source `aureon.utils.aureon_queen_hive_mind.QueenHiveMind.read_auris_nodes`.
A hit is the node value at or above 0.5 agreeing with a pre-registered threshold on the named input.
That is not a trade result. Live trading is off.

| node | verdict | hit rate | baseline hit rate | output min | output max |
| --- | --- | ---: | ---: | ---: | ---: |
| Tiger | measured | 0.9648 | 0.8398 | 0.0041 | 0.7936 |
| Falcon | measured | 0.8789 | 0.9766 | 0.0392 | 0.9576 |
| Hummingbird | measured | 0.6562 | 0.8398 | 0.0060 | 0.3336 |
| Dolphin | measured | 1.0000 | 1.0000 | 0.0000 | 1.0000 |
| Deer | measured | 0.9570 | 0.9570 | 0.0008 | 0.9888 |
| Owl | HOLD | HOLD | HOLD | 0.6000 | 0.6000 |
| Panda | measured | 0.5039 | 1.0000 | 0.5025 | 0.9960 |
| CargoShip | measured | 0.9297 | 0.9297 | 0.0132 | 0.9876 |
| Clownfish | HOLD | HOLD | HOLD | 0.5000 | 0.5000 |

Trade readiness: **HOLD**. no independent trade-outcome labels; coherence is not evidence of a fill
