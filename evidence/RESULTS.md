# Evidence results

This file is written by `python -m aureon.evidence`. Floats here use Python `format(x, ".6g")`. Full values are in `evidence/output/`.

The run calls `HarmonicRealityField.step`, `QueenHiveMind.get_auris_coherence`, `QueenHiveMind.read_auris_nodes`, and `QGITAMarketAnalyzer.analyze`. It does not call an external model. It does not place an order. It does not say the system is alive.

## Reproduce

```
make evidence
```

That target runs `PYTHONHASHSEED=0 PYTHONPATH=. python3 -m aureon.evidence --check`. The check rebuilds every committed output and requires the bytes to match. `evidence/environment.json` is included, except the field `commit_sha`, which is `git rev-parse HEAD` at run time and is allowed to differ. There is no numeric tolerance. The match is for the Python, NumPy, and platform recorded below.

Dependencies used by the imported implementations: NumPy, and `python-dotenv` because `QueenHiveMind` imports it. This command does not install packages and does not call a network API.

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
- QGITA positive calls use the analyzer's own gates, `ftcp_count > 0` and `lhe_count > 0`. Those thresholds were not tuned.
- Energy baseline: maximum squared sample, location unknown. Oracle baseline: squared sample at the known injection index. Their call threshold is fit on separate null draws so about 5% of those draws lie strictly above it.
- AUROC is Mann-Whitney with ties counted as one half. Higher scores rank as the injected class. Scores are not flipped when the ranking runs the other way.

## HNC

| path | coherence | boundedness | echo_strength | state | min | max | finite | seed diff | repeat diff | shuffled coherence | gaussian coherence | zero coherence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| formula | 0.994589 | 0.663268 | 1 | unified | 0.199239 | 8.06523 | true | 0 | 0 | 0.136174 | 0.106848 | 0 |
| multiverse | 0.754003 | 0.216786 | 0.999979 | coherent | -0.0429927 | 0.0407312 | true | 0 | 0 | null | null | null |

Formula versus multiverse, maximum absolute difference: 8.06509.
Six-digit formatting rounds the formula-path echo_strength to 1. The JSON value is 0.9999999999981624.

## Auris

| quantity | value |
| --- | --- |
| cases | 63 |
| dependency mismatches | 0 / 567 |
| cases with a numeric coherence | 0 |
| cases whose coherence status matches the null input | 63 / 63 |
| null coherence status | no_data |
| nodes with no reading on any case | Clownfish, Owl |
| median distance from the zero input | 0.444427 |
| median distance from the key shuffle | 0.255844 |

| node | role | readings | missing | value on zeros | value on ones |
| --- | --- | --- | --- | --- | --- |
| CargoShip | infrastructure | 60 | 3 | 0 | 1 |
| Clownfish | symbiosis | 0 | 63 | null | null |
| Deer | sensing | 60 | 3 | 0 | 1 |
| Dolphin | emotion | 60 | 3 | 0.5 | 0.5 |
| Falcon | momentum | 59 | 4 | 0 | 1 |
| Hummingbird | stability | 58 | 5 | 0.6 | 0.00594059 |
| Owl | memory | 0 | 63 | null | null |
| Panda | love | 58 | 5 | 1 | 0.5 |
| Tiger | volatility | 58 | 5 | 0.8 | 0 |

## QGITA

Precision is null when a detector made no positive calls. Recall and false-alarm rate use the injected label.

| placement | snr_db | amplitude | ftcp recall | ftcp FPR | ftcp precision | lhe recall | lhe FPR | g_eff AUROC | energy AUROC | oracle AUROC | shuffled FTCP rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tight_lattice | -12 | 0.251189 | 0.28125 | 0.21875 | 0.5625 | 0 | 0 | 0.525879 | 0.5 | 0.550781 | 0.21875 |
| tight_lattice | -6 | 0.501187 | 0.28125 | 0.25 | 0.529412 | 0 | 0 | 0.514648 | 0.505371 | 0.563477 | 0.25 |
| tight_lattice | 0 | 1 | 0.375 | 0.40625 | 0.48 | 0 | 0 | 0.514648 | 0.515625 | 0.612305 | 0.09375 |
| tight_lattice | 6 | 1.99526 | 0.625 | 0.15625 | 0.8 | 0 | 0 | 0.758789 | 0.570801 | 0.904297 | 0.25 |
| tight_lattice | 12 | 3.98107 | 0.96875 | 0.15625 | 0.861111 | 0.0625 | 0 | 0.979004 | 0.864258 | 0.995117 | 0.09375 |
| tight_lattice | 18 | 7.94328 | 1 | 0.1875 | 0.842105 | 0.3125 | 0 | 1 | 1 | 1 | 0.28125 |
| tight_lattice | 24 | 15.8489 | 1 | 0.15625 | 0.864865 | 0.84375 | 0 | 1 | 1 | 1 | 0.15625 |
| tight_lattice | 30 | 31.6228 | 1 | 0.15625 | 0.864865 | 0.90625 | 0 | 1 | 1 | 1 | 0.125 |
| tight_lattice | 36 | 63.0957 | 1 | 0.0625 | 0.941176 | 1 | 0 | 1 | 1 | 1 | 0 |
| mid_lattice | -12 | 0.251189 | 0.25 | 0.25 | 0.5 | 0 | 0 | 0.5 | 0.5 | 0.469727 | 0.125 |
| mid_lattice | -6 | 0.501187 | 0.15625 | 0.15625 | 0.5 | 0 | 0 | 0.5 | 0.5 | 0.570312 | 0.0625 |
| mid_lattice | 0 | 1 | 0.3125 | 0.3125 | 0.5 | 0 | 0 | 0.5 | 0.51709 | 0.603516 | 0.1875 |
| mid_lattice | 6 | 1.99526 | 0.3125 | 0.3125 | 0.5 | 0 | 0 | 0.5 | 0.543457 | 0.837891 | 0.15625 |
| mid_lattice | 12 | 3.98107 | 0.28125 | 0.28125 | 0.5 | 0 | 0 | 0.5 | 0.915527 | 0.999023 | 0.28125 |
| mid_lattice | 18 | 7.94328 | 0.1875 | 0.25 | 0.428571 | 0 | 0 | 0.470703 | 1 | 1 | 0.21875 |
| mid_lattice | 24 | 15.8489 | 0.03125 | 0.0625 | 0.333333 | 0 | 0 | 0.484863 | 1 | 1 | 0.09375 |
| mid_lattice | 30 | 31.6228 | 0 | 0.21875 | 0 | 0 | 0 | 0.390625 | 1 | 1 | 0.0625 |
| mid_lattice | 36 | 63.0957 | 0 | 0.28125 | 0 | 0 | 0 | 0.359375 | 1 | 1 | 0 |
| off_lattice | -12 | 0.251189 | 0.15625 | 0.15625 | 0.5 | 0 | 0 | 0.5 | 0.502441 | 0.506836 | 0.28125 |
| off_lattice | -6 | 0.501187 | 0.125 | 0.125 | 0.5 | 0 | 0 | 0.5 | 0.5 | 0.567383 | 0.25 |
| off_lattice | 0 | 1 | 0.25 | 0.25 | 0.5 | 0 | 0 | 0.5 | 0.51123 | 0.547852 | 0.21875 |
| off_lattice | 6 | 1.99526 | 0.25 | 0.21875 | 0.533333 | 0 | 0 | 0.513184 | 0.576172 | 0.806641 | 0.21875 |
| off_lattice | 12 | 3.98107 | 0.125 | 0.125 | 0.5 | 0 | 0 | 0.5 | 0.841797 | 0.99707 | 0.09375 |
| off_lattice | 18 | 7.94328 | 0.15625 | 0.15625 | 0.5 | 0 | 0 | 0.5 | 1 | 1 | 0.28125 |
| off_lattice | 24 | 15.8489 | 0.0625 | 0.1875 | 0.25 | 0 | 0 | 0.44043 | 1 | 1 | 0.1875 |
| off_lattice | 30 | 31.6228 | 0.03125 | 0.1875 | 0.142857 | 0 | 0 | 0.424316 | 1 | 1 | 0.09375 |
| off_lattice | 36 | 63.0957 | 0 | 0.21875 | 0 | 0 | 0 | 0.390625 | 1 | 1 | 0.03125 |

Energy threshold 13.1292, calibration false-alarm rate 0.046875. Oracle threshold 2.50274, calibration false-alarm rate 0.046875.

## Claims

Measured: a figure this run computed. Inferred: a comparison or a reading of the implementation that the figure supports. Speculative: recorded so it is explicit, and not asserted as a result.

| id | tag | asserted | statement |
| --- | --- | --- | --- |
| hnc.formula.window | measured | true | HarmonicRealityField.step with enable_multiverse false, 1000 steps, seed 0: state unified, coherence 0.994589, boundedness 0.663268, echo_strength 1, lambda min 0.199239, max 8.06523, finite true. |
| hnc.formula.seeds | inferred | true | The formula-path series is unchanged across the recorded seeds and a repeat of seed 0. |
| hnc.formula.coherence_baselines | inferred | true | Formula-path coherence is higher than the shuffled-series baseline and the unit-Gaussian baseline under HarmonicRealityField._calculate_coherence. Measured coherence 0.994589, shuffled 0.136174, gaussian 0.106848, zeros 0. |
| hnc.formula.echo_strength | inferred | true | CausalEcho.get_echo_strength returns min(1, abs(current*delayed) / (abs(current)*abs(delayed) + 1e-10)). This run measured 0.999999999998. The expression is near 1 whenever both samples are nonzero, so the figure is not a correlation. |
| hnc.formula.nyquist | inferred | true | 5 substrate modes are at or above the Nyquist rate 500 Hz for sample_rate 1000. Those modes are not represented as distinct frequencies by this discrete step. The mode frequencies are 528, 639, 741, 852, 963. |
| hnc.multiverse.seeds | inferred | true | The class-default multiverse path is unchanged across the recorded seeds and a repeat. |
| hnc.multiverse.versus_formula | measured | true | Maximum absolute difference between the seed-0 formula series and the seed-0 multiverse series is 8.06509. Multiverse coherence 0.754003, state coherent. |
| auris.dependency | measured | true | Input-guard checks 0 mismatches out of 567 node readings. |
| auris.coherence_versus_null | inferred | true | get_auris_coherence returned no number, and the same status as the null input, on every synthetic case (63 of 63). These inputs are not separated from the null baseline by the coherence figure. |
| auris.nodes_without_readings | inferred | true | Nodes with no numeric reading on any case: Clownfish, Owl. get_auris_coherence returns no_data when any node value is missing, so a node that never reads is enough to withhold the coherence figure on these inputs. |
| auris.baselines | inferred | true | Moving the seeded random inputs onto different keys changed node outputs (median distance 0.255844). The readings are key-sensitive on these cases. Median distance from the all-zero input on the same random cases is 0.444427. |
| qgita.gates_versus_null | inferred | true | FTCP recall exceeded the FTCP false-alarm rate in 9 of 27 cells (tight_lattice -12 dB, tight_lattice -6 dB, tight_lattice 6 dB, tight_lattice 12 dB, tight_lattice 18 dB, tight_lattice 24 dB, tight_lattice 30 dB, tight_lattice 36 dB, off_lattice 6 dB). FTCP recall was below that false-alarm rate in 8 of 27 cells (tight_lattice 0 dB, mid_lattice 18 dB, mid_lattice 24 dB, mid_lattice 30 dB, mid_lattice 36 dB, off_lattice 24 dB, off_lattice 30 dB, off_lattice 36 dB). LHE recall exceeded the LHE false-alarm rate in 5 of 27 cells (tight_lattice 12 dB, tight_lattice 18 dB, tight_lattice 24 dB, tight_lattice 30 dB, tight_lattice 36 dB). A gate that ignores the injected impulse has recall near its false-alarm rate. The inequality is the raw counts. It is not a significance test, so a one-trial gap is listed and is not a detection result by itself. FTCPDetector raises its curvature threshold as (1 + std) when adaptive_threshold is on, and discrete curvature divides by the product of the adjacent knot gaps. Those are the detector's existing definitions. This run did not retune them. |
| qgita.geff_versus_energy | inferred | true | max_g_eff AUROC exceeded the location-unknown energy detector AUROC in 4 of 27 cells (tight_lattice -12 dB, tight_lattice -6 dB, tight_lattice 6 dB, tight_lattice 12 dB). Higher scores were ranked as the injected class and were not flipped. |
| qgita.placement | measured | true | Maximum FTCP recall on the tight knot was 1. Maximum FTCP recall on the mid knot was 0.3125. Maximum FTCP recall off the lattice was 0.25. Minimum energy-detector AUROC off the lattice was 0.5. |
| not_claimed.alive_or_hold | speculative | false | Nothing measured here says that HNC, Auris, or QGITA is alive, conscious, or validated, and nothing here lifts deployment HOLD. Reading a coherence label or an AUROC as that decision would be speculative. |

Deployment HOLD is unchanged by this run.
