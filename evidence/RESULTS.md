# Evidence results

This file is written by `python -m aureon.evidence`. Floats here use Python `format(x, ".6g")`. Full values are in `evidence/output/`.

The run calls `HarmonicRealityField.step`, `QueenHiveMind.get_auris_coherence`, `QueenHiveMind.read_auris_nodes`, and `QGITAMarketAnalyzer.analyze`. It does not call an external model. It does not place an order. It does not say the system is alive.

## Reproduce

```
make evidence
```

That target runs `PYTHONHASHSEED=0 PYTHONPATH=. python3 -m aureon.evidence --check`. The check rebuilds every committed output and requires the bytes to match, including `evidence/output/hnc_head_anchor.json`, `evidence/output/hnc_head_anchor.id`, and `evidence/output/hnc_head_anchor.tsr.b64`, and the sequence 2 files `evidence/output/hnc_head_next.json`, `evidence/output/hnc_head_next.id`, and `evidence/output/hnc_head_next.tsr.b64`. `evidence/environment.json` is included, except the field `commit_sha`, which is `git rev-parse HEAD` at run time and is allowed to differ. Sequence 1 is read from the git note `refs/notes/aureon-hnc-head` on HEAD. Sequence 2 is read from `refs/notes/aureon-hnc-head-next` on HEAD. Fetch them with `git fetch origin refs/notes/aureon-hnc-head:refs/notes/aureon-hnc-head` and `git fetch origin refs/notes/aureon-hnc-head-next:refs/notes/aureon-hnc-head-next` when a clone does not have those refs. There is no numeric tolerance. The match is for the Python, NumPy, and platform recorded below.

Dependencies used by the imported implementations: NumPy, and `python-dotenv` because `QueenHiveMind` imports it. This command does not install packages and does not call a network API. Each HNC head token was requested once and is checked locally.

## Recorded environment

| item | value |
| --- | --- |
| Python | 3.12.3 |
| NumPy | 1.26.4 |
| platform | Linux-6.12.94+-x86_64-with-glibc2.39 |
| HNC seeds | 0, 1, 7, 42, 20261105 |
| HNC shuffle and Gaussian seed | 20261105 |
| Auris random seed | 20261105 |
| QGITA master seed | 20261105 |
| QGITA calibration seed start | 50000000 |
| PYTHONHASHSEED | 0 |

## Harness definitions

These belong to the harness. They are not formulas of the three systems.

- HNC baselines pass a zero series, a shuffled copy of Λ(t), and unit Gaussian noise through `HarmonicRealityField._calculate_coherence`.
- Auris ground truth is the input guard transcribed from `_auris_role_value` and `_auris_input`. Numeric node values are the function's own outputs.
- Auris baselines are the null call, the all-zero input, and the same numbers moved onto different keys.
- QGITA signal: one-sample impulse of amplitude A added to unit-variance Gaussian noise. `snr_db = 20 * log10(A)`.
- QGITA calls compare `max_g_eff` and lighthouse intensity with thresholds fit on calibration nulls at a 5% tail. The analyzer's constructor defaults are unchanged. Rate intervals are Wilson 95%. AUROC intervals are Hanley-McNeil.
- Energy baseline: maximum squared sample, location unknown. Oracle baseline: squared sample at the known injection index. Their call threshold is fit on separate null draws so about 5% of those draws lie strictly above it.
- AUROC is Mann-Whitney with ties counted as one half. Higher scores rank as the injected class. Scores are not flipped when the ranking runs the other way.

## HNC

| path | coherence | boundedness | echo magnitude ratio | state | min | max | finite | seed diff | repeat diff | shuffled coherence | gaussian coherence | zero coherence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| formula | 0.992718 | 0.6088 | 1 | unified | 0.199239 | 6.21438 | true | 0 | 0 | 0.12569 | 0.106848 | 0 |
| multiverse | 0.843088 | 0.223055 | 0.999997 | coherent | -0.0484853 | 0.0417403 | true | 0 | 0 | null | null | null |

Formula versus multiverse, maximum absolute difference: 6.23589.
The echo figure is the magnitude ratio from CausalEcho.get_echo_magnitude_ratio. JSON value 0.9999999999957911. It is not a correlation. Sample rate 1927 Hz, requested 1927 Hz.

## HNC head anchor

Receipt 3 only. This is a measured binding of the fixed-seed formula series. It is not a go-live clearance and it does not say the system is alive.

| item | value |
| --- | --- |
| tag | measured |
| anchor id | 548596463d7b4dddeeba274562b212960f879baf475ee135c7d2fd3468f58e11 |
| gen time | 2026-11-05T19:40:18Z |
| provider | http://timestamp.digicert.com |
| policy | 2.16.840.1.114412.7.1 |
| serial | 4c04ef96999f7e3d25072a00af832eba |
| TSA ordering flag | no |
| sequence | 1 |
| previous head | dfcdb9ee381a7ffe511da7d621df739884ea74c3fd4c9790069f5d584478291c |
| git note | refs/notes/aureon-hnc-head |
| formula series sha256 | 0a69c024c3a7b849857314ef710f11439eb13a30cd7c45f05429becea574f5c2 |
| recorded public pin | 34864ff0547d2cff03e707414743a3b0cc8770b5 |
| recorded pin status | historical |
| published require-pin | bb04503119681adcf832f3c3e9b0cbf09fc7a938 |
| HNC identity changed | false |
| go-live | HOLD |
| go-live clear | false |
| system alive | false |
| orders placed | false |

The anchor id is the SHA-256 of the RFC 3161 token. The same token bytes are the git note on HEAD. `make evidence` requires those bytes and does not contact the timestamp authority. A working-tree edit does not move the note.

## HNC next head

Receipt 3 follow-on. Sequence 2 of the same fixed-seed formula series. It is not a go-live clearance, it does not set external_head_anchor_attested, and it does not say the system is alive.

| item | value |
| --- | --- |
| tag | measured |
| sequence | 2 |
| anchor id | e02c59279b46e912a08b1add73f44b82970f535676d0011a3bcb769dfba68784 |
| previous anchor | 548596463d7b4dddeeba274562b212960f879baf475ee135c7d2fd3468f58e11 |
| previous gen time | 2026-11-05T19:40:18Z |
| gen time | 2026-11-05T20:44:49Z |
| provider | http://timestamp.digicert.com |
| policy | 2.16.840.1.114412.7.1 |
| serial | 440da40635433708f26fb41ac8da2f71 |
| TSA ordering flag | no |
| git note | refs/notes/aureon-hnc-head-next |
| formula series sha256 | 0a69c024c3a7b849857314ef710f11439eb13a30cd7c45f05429becea574f5c2 |
| recorded public pin | 34864ff0547d2cff03e707414743a3b0cc8770b5 |
| recorded pin status | historical |
| published require-pin | bb04503119681adcf832f3c3e9b0cbf09fc7a938 |
| HNC identity changed | false |
| external head anchor attested | false |
| go-live | HOLD |
| go-live clear | false |
| system alive | false |
| orders placed | false |

The next anchor id is the SHA-256 of a second RFC 3161 token. That token is the git note refs/notes/aureon-hnc-head-next on HEAD. Sequence 1 stays on refs/notes/aureon-hnc-head. `make evidence` verifies both locally and does not contact the timestamp authority. A working-tree edit does not move either note.

## Auris

| quantity | value |
| --- | --- |
| cases | 63 |
| dependency mismatches | 0 / 567 |
| cases with a numeric coherence | 55 |
| cases whose coherence status matches the null input | 8 / 63 |
| null coherence status | no_data |
| nodes with no reading on any case | none |
| median distance from the zero input | 0.411916 |
| median distance from the key shuffle | 0.260128 |

| node | role | readings | missing | value on zeros | value on ones |
| --- | --- | --- | --- | --- | --- |
| CargoShip | infrastructure | 60 | 3 | 0 | 1 |
| Clownfish | symbiosis | 58 | 5 | 0.8 | 0.2 |
| Deer | sensing | 60 | 3 | 0 | 1 |
| Dolphin | emotion | 60 | 3 | 0.5 | 0.5 |
| Falcon | momentum | 59 | 4 | 0 | 1 |
| Hummingbird | stability | 58 | 5 | 0.6 | 0.00594059 |
| Owl | memory | 60 | 3 | 0.6 | 0.3 |
| Panda | love | 58 | 5 | 1 | 0.5 |
| Tiger | volatility | 58 | 5 | 0.8 | 0 |

## QGITA

Brackets are 95% intervals. Precision is null when a detector made no positive calls. Evaluation trials per class: 200. Calibration nulls: 400.

| placement | snr_db | amplitude | ftcp recall | ftcp FPR | lhe recall | lhe FPR | g_eff AUROC | energy AUROC | oracle AUROC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tight_lattice | -12 | 0.251189 | 0.06 [0.0346522, 0.101932] | 0.035 [0.0170555, 0.0704706] | 0.055 [0.0309853, 0.095787] | 0.055 [0.0309853, 0.095787] | 0.492312 [0.435671, 0.548954] | 0.5008 [0.44415, 0.55745] | 0.51105 [0.454417, 0.567683] |
| tight_lattice | -6 | 0.501187 | 0.12 [0.0819799, 0.172343] | 0.075 [0.0459749, 0.120044] | 0.1 [0.0656704, 0.149406] | 0.055 [0.0309853, 0.095787] | 0.545375 [0.48901, 0.60174] | 0.500613 [0.443963, 0.557262] | 0.569125 [0.513138, 0.625112] |
| tight_lattice | 0 | 1 | 0.185 [0.137302, 0.244571] | 0.09 [0.0576874, 0.137766] | 0.145 [0.102894, 0.200487] | 0.055 [0.0309853, 0.095787] | 0.57985 [0.524085, 0.635615] | 0.5073 [0.450657, 0.563943] | 0.64045 [0.58656, 0.69434] |
| tight_lattice | 6 | 1.99526 | 0.42 [0.353736, 0.489279] | 0.05 [0.0273826, 0.0895781] | 0.32 [0.259265, 0.387519] | 0.065 [0.0383764, 0.108019] | 0.740712 [0.69238, 0.789045] | 0.569275 [0.513291, 0.625259] | 0.85045 [0.81243, 0.88847] |
| tight_lattice | 12 | 3.98107 | 0.865 [0.810709, 0.905534] | 0.055 [0.0309853, 0.095787] | 0.615 [0.545999, 0.679667] | 0.06 [0.0346522, 0.101932] | 0.9623 [0.943099, 0.981501] | 0.893513 [0.861229, 0.925796] | 0.997425 [0.992437, 1] |
| tight_lattice | 18 | 7.94328 | 1 [0.981155, 1] | 0.07 [0.0421522, 0.114055] | 0.93 [0.885945, 0.957848] | 0.065 [0.0383764, 0.108019] | 0.996875 [0.991379, 1] | 1 [1, 1] | 1 [1, 1] |
| tight_lattice | 24 | 15.8489 | 1 [0.981155, 1] | 0.085 [0.0537458, 0.131896] | 1 [0.981155, 1] | 0.085 [0.0537458, 0.131896] | 1 [1, 1] | 1 [1, 1] | 1 [1, 1] |
| tight_lattice | 30 | 31.6228 | 1 [0.981155, 1] | 0.045 [0.0238525, 0.0832967] | 1 [0.981155, 1] | 0.06 [0.0346522, 0.101932] | 1 [1, 1] | 1 [1, 1] | 1 [1, 1] |
| tight_lattice | 36 | 63.0957 | 1 [0.981155, 1] | 0.06 [0.0346522, 0.101932] | 1 [0.981155, 1] | 0.065 [0.0383764, 0.108019] | 1 [1, 1] | 1 [1, 1] | 1 [1, 1] |
| mid_lattice | -12 | 0.251189 | 0.06 [0.0346522, 0.101932] | 0.06 [0.0346522, 0.101932] | 0.095 [0.0616631, 0.143602] | 0.095 [0.0616631, 0.143602] | 0.5 [0.44335, 0.55665] | 0.5 [0.44335, 0.55665] | 0.4972 [0.440551, 0.553849] |
| mid_lattice | -6 | 0.501187 | 0.045 [0.0238525, 0.0832967] | 0.045 [0.0238525, 0.0832967] | 0.05 [0.0273826, 0.0895781] | 0.05 [0.0273826, 0.0895781] | 0.5 [0.44335, 0.55665] | 0.500025 [0.443375, 0.556675] | 0.556925 [0.500724, 0.613126] |
| mid_lattice | 0 | 1 | 0.035 [0.0170555, 0.0704706] | 0.035 [0.0170555, 0.0704706] | 0.055 [0.0309853, 0.095787] | 0.055 [0.0309853, 0.095787] | 0.5 [0.44335, 0.55665] | 0.502663 [0.446014, 0.559311] | 0.643125 [0.589343, 0.696907] |
| mid_lattice | 6 | 1.99526 | 0.07 [0.0421522, 0.114055] | 0.075 [0.0459749, 0.120044] | 0.11 [0.0737724, 0.160927] | 0.11 [0.0737724, 0.160927] | 0.497075 [0.440426, 0.553724] | 0.561562 [0.505438, 0.617687] | 0.839 [0.799646, 0.878354] |
| mid_lattice | 12 | 3.98107 | 0.09 [0.0576874, 0.137766] | 0.09 [0.0576874, 0.137766] | 0.095 [0.0616631, 0.143602] | 0.095 [0.0616631, 0.143602] | 0.493 [0.436357, 0.549643] | 0.911725 [0.882296, 0.941154] | 0.9977 [0.992986, 1] |
| mid_lattice | 18 | 7.94328 | 0.075 [0.0459749, 0.120044] | 0.075 [0.0459749, 0.120044] | 0.07 [0.0421522, 0.114055] | 0.085 [0.0537458, 0.131896] | 0.4775 [0.42092, 0.53408] | 1 [1, 1] | 1 [1, 1] |
| mid_lattice | 24 | 15.8489 | 0.04 [0.0204056, 0.0769321] | 0.04 [0.0204056, 0.0769321] | 0.03 [0.0138203, 0.0638943] | 0.055 [0.0309853, 0.095787] | 0.432237 [0.376224, 0.488251] | 1 [1, 1] | 1 [1, 1] |
| mid_lattice | 30 | 31.6228 | 0.01 [0.00274666, 0.0357218] | 0.075 [0.0459749, 0.120044] | 0.01 [0.00274666, 0.0357218] | 0.07 [0.0421522, 0.114055] | 0.412637 [0.357048, 0.468227] | 1 [1, 1] | 1 [1, 1] |
| mid_lattice | 36 | 63.0957 | 0 [0, 0.0188453] | 0.095 [0.0616631, 0.143602] | 0 [0, 0.0188453] | 0.085 [0.0537458, 0.131896] | 0.3675 [0.313303, 0.421697] | 1 [1, 1] | 1 [1, 1] |
| off_lattice | -12 | 0.251189 | 0.025 [0.0107247, 0.0571783] | 0.025 [0.0107247, 0.0571783] | 0.065 [0.0383764, 0.108019] | 0.065 [0.0383764, 0.108019] | 0.5 [0.44335, 0.55665] | 0.50075 [0.4441, 0.5574] | 0.52455 [0.467983, 0.581117] |
| off_lattice | -6 | 0.501187 | 0.07 [0.0421522, 0.114055] | 0.07 [0.0421522, 0.114055] | 0.085 [0.0537458, 0.131896] | 0.085 [0.0537458, 0.131896] | 0.5 [0.44335, 0.55665] | 0.5 [0.44335, 0.55665] | 0.574725 [0.51885, 0.6306] |
| off_lattice | 0 | 1 | 0.065 [0.0383764, 0.108019] | 0.065 [0.0383764, 0.108019] | 0.035 [0.0170555, 0.0704706] | 0.035 [0.0170555, 0.0704706] | 0.5 [0.44335, 0.55665] | 0.501925 [0.445276, 0.558574] | 0.54875 [0.492429, 0.605071] |
| off_lattice | 6 | 1.99526 | 0.05 [0.0273826, 0.0895781] | 0.05 [0.0273826, 0.0895781] | 0.085 [0.0537458, 0.131896] | 0.085 [0.0537458, 0.131896] | 0.502162 [0.445513, 0.558812] | 0.56965 [0.513673, 0.625627] | 0.831625 [0.791449, 0.871801] |
| off_lattice | 12 | 3.98107 | 0.02 [0.00780443, 0.0502871] | 0.02 [0.00780443, 0.0502871] | 0.045 [0.0238525, 0.0832967] | 0.045 [0.0238525, 0.0832967] | 0.4976 [0.440951, 0.554249] | 0.878737 [0.844343, 0.913132] | 0.99355 [0.985648, 1] |
| off_lattice | 18 | 7.94328 | 0.05 [0.0273826, 0.0895781] | 0.05 [0.0273826, 0.0895781] | 0.04 [0.0204056, 0.0769321] | 0.055 [0.0309853, 0.095787] | 0.483925 [0.427311, 0.540539] | 1 [1, 1] | 1 [1, 1] |
| off_lattice | 24 | 15.8489 | 0.045 [0.0238525, 0.0832967] | 0.045 [0.0238525, 0.0832967] | 0.045 [0.0238525, 0.0832967] | 0.05 [0.0273826, 0.0895781] | 0.451163 [0.394843, 0.507482] | 1 [1, 1] | 1 [1, 1] |
| off_lattice | 30 | 31.6228 | 0.02 [0.00780443, 0.0502871] | 0.05 [0.0273826, 0.0895781] | 0.015 [0.00511424, 0.0431657] | 0.065 [0.0383764, 0.108019] | 0.407325 [0.351869, 0.462781] | 1 [1, 1] | 1 [1, 1] |
| off_lattice | 36 | 63.0957 | 0 [0, 0.0188453] | 0.08 [0.0498406, 0.125989] | 0 [0, 0.0188453] | 0.105 [0.0697075, 0.15518] | 0.3675 [0.313303, 0.421697] | 1 [1, 1] | 1 [1, 1] |

FTCP max_g_eff threshold 0.0511806, calibration false-alarm rate 0.05. Lighthouse intensity threshold 0.0856991, calibration false-alarm rate 0.05. Energy threshold 13.1292. Oracle threshold 3.65095.

## Claims

Measured: a figure this run computed. Inferred: a comparison or a reading of the implementation that the figure supports. Speculative: recorded so it is explicit, and not asserted as a result.

| id | tag | asserted | statement |
| --- | --- | --- | --- |
| hnc.formula.window | measured | true | HarmonicRealityField.step with enable_multiverse false, 1000 steps, seed 0: state unified, coherence 0.992718, boundedness 0.6088, echo magnitude ratio 1, sample rate 1927, lambda min 0.199239, max 6.21438, finite true. |
| hnc.formula.seeds | inferred | true | The formula-path series is unchanged across the recorded seeds and a repeat of seed 0. |
| hnc.formula.coherence_baselines | inferred | true | Formula-path coherence is higher than the shuffled-series baseline and the unit-Gaussian baseline under HarmonicRealityField._calculate_coherence. Measured coherence 0.992718, shuffled 0.12569, gaussian 0.106848, zeros 0. |
| hnc.formula.echo_magnitude_ratio | measured | true | The published echo figure is CausalEcho.get_echo_magnitude_ratio, also stored as get_echo_strength. It is min(1, abs(current*delayed) / (abs(current)*abs(delayed) + 1e-10)). This run measured 0.999999999996. It is not a correlation. |
| hnc.formula.nyquist | measured | true | Every substrate mode is strictly below the Nyquist rate 963.5 Hz. The rate used is 1927 Hz (requested 1927). That rate is floor(2 * highest mode) + 1 when the request would not already clear Nyquist. |
| hnc.multiverse.seeds | inferred | true | The class-default multiverse path is unchanged across the recorded seeds and a repeat. |
| hnc.multiverse.versus_formula | measured | true | Maximum absolute difference between the seed-0 formula series and the seed-0 multiverse series is 6.23589. Multiverse coherence 0.843088, state coherent. |
| hnc.head_anchor | measured | true | Receipt 3 binds the formula-path series sha256 0a69c024c3a7b849857314ef710f11439eb13a30cd7c45f05429becea574f5c2 to RFC 3161 anchor 548596463d7b4dddeeba274562b212960f879baf475ee135c7d2fd3468f58e11 at 2026-11-05T19:40:18Z. Sequence 1. The timestamp records historical public pin 34864ff0547d2cff03e707414743a3b0cc8770b5. The published require-pin is bb04503119681adcf832f3c3e9b0cbf09fc7a938. go_live_clear stays false. The run does not report the system alive, does not place an order, and leaves go-live HOLD. |
| hnc.head_anchor.identity | inferred | true | The measured formula series sha256 matches the series recorded for historical public pin 34864ff0547d2cff03e707414743a3b0cc8770b5. The published require-pin is bb04503119681adcf832f3c3e9b0cbf09fc7a938. This receipt does not publish a new HNC identity. |
| hnc.head_anchor.next | measured | true | Receipt 3 follow-on binds sequence 2 to RFC 3161 anchor e02c59279b46e912a08b1add73f44b82970f535676d0011a3bcb769dfba68784 at 2026-11-05T20:44:49Z. prev_anchor_id is 548596463d7b4dddeeba274562b212960f879baf475ee135c7d2fd3468f58e11. Sequence 1 gen_time is 2026-11-05T19:40:18Z. The verified gen_time is strictly later. external_head_anchor_attested stays false. The timestamp records historical public pin 34864ff0547d2cff03e707414743a3b0cc8770b5. The published require-pin is bb04503119681adcf832f3c3e9b0cbf09fc7a938. go_live_clear stays false. The run does not report the system alive, does not place an order, and leaves go-live HOLD. |
| auris.dependency | measured | true | Input-guard checks 0 mismatches out of 567 node readings. |
| auris.coherence_versus_null | inferred | true | Numeric coherence was returned on 55 cases. Status matched the null input on 8 of 63 cases. |
| auris.nodes_without_readings | measured | true | Nodes with no numeric reading on any case: none. Cases with a numeric coherence: 55 of 63. get_auris_coherence still returns no_data when any required input is missing. |
| auris.baselines | inferred | true | Moving the seeded random inputs onto different keys changed node outputs (median distance 0.260128). The readings are key-sensitive on these cases. Median distance from the all-zero input on the same random cases is 0.411916. |
| qgita.gates_versus_null | inferred | true | FTCP recall exceeded the FTCP false-alarm rate in 9 of 27 cells (tight_lattice -12 dB, tight_lattice -6 dB, tight_lattice 0 dB, tight_lattice 6 dB, tight_lattice 12 dB, tight_lattice 18 dB, tight_lattice 24 dB, tight_lattice 30 dB, tight_lattice 36 dB). FTCP recall was below that false-alarm rate in 5 of 27 cells (mid_lattice 6 dB, mid_lattice 30 dB, mid_lattice 36 dB, off_lattice 30 dB, off_lattice 36 dB). LHE recall exceeded the LHE false-alarm rate in 8 of 27 cells (tight_lattice -6 dB, tight_lattice 0 dB, tight_lattice 6 dB, tight_lattice 12 dB, tight_lattice 18 dB, tight_lattice 24 dB, tight_lattice 30 dB, tight_lattice 36 dB). FTCP and lighthouse calls use thresholds fit on a separate null calibration set at a 5 percent tail of max_g_eff and lighthouse intensity. A one-trial gap is not a significance test. Wilson 95 percent intervals are in the table. |
| qgita.geff_versus_energy | inferred | true | max_g_eff AUROC exceeded the location-unknown energy detector AUROC in 4 of 27 cells (tight_lattice -6 dB, tight_lattice 0 dB, tight_lattice 6 dB, tight_lattice 12 dB). Higher scores were ranked as the injected class and were not flipped. |
| qgita.placement | measured | true | Maximum FTCP recall on the tight knot was 1. Maximum FTCP recall on the mid knot was 0.09. Maximum FTCP recall off the lattice was 0.07. Minimum energy-detector AUROC off the lattice was 0.5. |
| not_claimed.alive_or_hold | speculative | false | Nothing measured here says that HNC, Auris, or QGITA is alive, conscious, or validated, and nothing here lifts deployment HOLD. Reading a coherence label or an AUROC as that decision would be speculative. |

Deployment HOLD is unchanged by this run.
