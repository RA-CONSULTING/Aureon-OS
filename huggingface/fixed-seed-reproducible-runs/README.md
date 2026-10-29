---
license: mit
pretty_name: fixed-seed reproducible runs
language:
  - en
tags:
  - aureon
---

# fixed-seed reproducible runs

Licence: **MIT**, the same licence as the Aureon OS [`LICENSE`](https://github.com/RA-CONSULTING/Aureon-OS/blob/a00f744d2e686e916e45b81dd4222408c368e305/LICENSE).

These files are byte copies of `reports/measured/` at commit `a00f744d2e686e916e45b81dd4222408c368e305`. The brain runs in `brain.json` are fixed-seed reproducible runs. Commit `a00f744d` removed the unseeded noise path, and that brain run reproduces exactly.

Every claim below links to that commit.

## Cited from the brain run

Source: [reports/measured/brain.json](https://github.com/RA-CONSULTING/Aureon-OS/blob/a00f744d2e686e916e45b81dd4222408c368e305/reports/measured/brain.json)

The class default `HarmonicRealityField()` is the multiverse-on path. The other row is the multiverse-off path (`enable_multiverse=False`).

| Path | Coherence | Last Lambda | State | Label |
| --- | --- | --- | --- | --- |
| Class default HarmonicRealityField() (multiverse on) | 0.857719007627168 | 0.002306037019850606 | LOCKED | cited |
| enable_multiverse=False (multiverse off) | 0.9331334813083556 | 1.409626852655939 | UNIFIED | cited |

The file stores those states as `locked` and `unified`. The multiverse-extension verdict in the file is measured.

## HOLD in every card

| Claim | Label | Link |
| --- | --- | --- |
| Trade readiness | HOLD | [auris_nodes.json](https://github.com/RA-CONSULTING/Aureon-OS/blob/a00f744d2e686e916e45b81dd4222408c368e305/reports/measured/auris_nodes.json) |
| Auris joined to Lambda | HOLD | [brain.json](https://github.com/RA-CONSULTING/Aureon-OS/blob/a00f744d2e686e916e45b81dd4222408c368e305/reports/measured/brain.json) |
| QGITA detection rate on the derived series | HOLD | [qgita_snr.json](https://github.com/RA-CONSULTING/Aureon-OS/blob/a00f744d2e686e916e45b81dd4222408c368e305/reports/measured/qgita_snr.json) |
| QGITA detection rate on the formula series | HOLD | [qgita_snr.json](https://github.com/RA-CONSULTING/Aureon-OS/blob/a00f744d2e686e916e45b81dd4222408c368e305/reports/measured/qgita_snr.json) |
| Schumann f0 | null, HOLD | no committed measured f0 in this bundle |

The committed QGITA file tags the derived series `data/de440_timeseries.csv` column `Lambda` as cited-unverified and says it is not public market data. Adapter FTCP count `0` and lighthouse count `0` on that series are cited from [qgita_snr.json](https://github.com/RA-CONSULTING/Aureon-OS/blob/a00f744d2e686e916e45b81dd4222408c368e305/reports/measured/qgita_snr.json). Those counts are adapter output. They are not a detection rate.

The committed Auris record supplied no market series. Coherence is unavailable there. Owl and Clownfish stay without a reading when the four market fields are present as zero; that zero probe is named in the file and is not a market reading.

## Replay, and what is seeded synthetic

`organism.json` is a replay of the committed in-process circulation record. Link: [organism.json](https://github.com/RA-CONSULTING/Aureon-OS/blob/a00f744d2e686e916e45b81dd4222408c368e305/reports/measured/organism.json). Connectivity verdict `pass` and score `1.0` are cited from that file. It is not a market tape.

The fault block in that file is seeded synthetic input, seed `20261024`. The harness injected those faults. They are not telemetry and they are not recorded seat faults. A claim that the fault rate is a recorded fault rate is **HOLD**.

The self-coder record from this commit (PR 211, merge `a00f744d`) does not feed Auris or QGITA a drawn series. `humaneval.per_row_auris_qgita.kind` is `no_data`. There is no seeded synthetic price series in `self_coder.json`.

## HumanEval

HumanEval: **not run**.

The file status is `not_attempted`. That is not a score. Do not read a pass count in the raw file as a measured score. A separate check in `dataset_solution_smoke` executed the dataset's own reference solutions. That check is not HumanEval for this system.

SWE-bench and LiveCodeBench were not run. The flagship comparison is **HOLD**. `published_reference` in the file names an external published figure and is not this run.

## Files

`auris_nodes.json`, `auris_nodes.md`, `brain.json`, `brain.md`, `index.json`, `organism.json`, `organism.md`, `qgita_snr.json`, `qgita_snr.md`, `self_coder.json`, `self_coder.md`.

Raw files are copied unchanged. This card is the claim list.
