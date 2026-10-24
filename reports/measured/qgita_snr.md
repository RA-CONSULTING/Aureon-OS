# QGITA signal-to-noise benchmark

Detector `aureon.wisdom.aureon_qgita_framework.FTCPDetector`. Baseline: max absolute adjacent difference on the same lattice samples.
Calibration seed `20261024`, evaluation seed `777`.
80 planted trials and 80 noise trials in each split.
Thresholds are frozen on the calibration split at a false-alarm target of 0.1. Live trading is off.

| detector | AUC | detection rate | false-alarm rate |
| --- | ---: | ---: | ---: |
| FTCP | 0.6691 | 0.2875 | 0.0875 |
| baseline | 0.6211 | 0.1750 | 0.1375 |

Public series `data/de440_timeseries.csv`: **HOLD**. de440_timeseries.csv is the ephemeris series already in the repo. Its conjunction and opposition columns are not signal-in-noise ground truth, so detection rate, false-alarm rate, and AUC are not claimed.
