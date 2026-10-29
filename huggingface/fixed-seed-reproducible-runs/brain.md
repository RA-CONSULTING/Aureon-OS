# HNC, Auris coherence, and QGITA

These figures are the HNC field paths, Auris coherence, and the QGITA adapter. No outside model was called. Live trading stayed off. No order was placed.

The class default `HarmonicRealityField()` is the multiverse-on path. The second row is the multiverse-off path (`enable_multiverse=False`).

| Path | Coherence | Last Lambda | State | Label |
| --- | --- | --- | --- | --- |
| Class default HarmonicRealityField() (multiverse on) | 0.857719007627168 | 0.002306037019850606 | LOCKED | cited from brain.json `multiverse_extension` |
| enable_multiverse=False (multiverse off) | 0.9331334813083556 | 1.409626852655939 | UNIFIED | cited from brain.json |

The file stores those states as `locked` and `unified`. Steps `100`.

Multiverse extension: **measured**. project_to_3d sets noise to 0 when no observed residual is supplied. TranslationMap.noise_level is stored and is not read by that method. Three constructions of the default HarmonicRealityField returned the same series.
Auris coherence `None` with status `no_data`. Nodes without a reading: Clownfish, Owl.
Trade readiness: **HOLD**. no market series and no trade-outcome labels
QGITA on the derived series `data/de440_timeseries.csv` (cited-unverified): status `complete`, FTCP count `0`, lighthouse events `0`. Detection rate **HOLD**. Clock: sample index. analyze_price_stream uses range(len(prices)) when no timestamps are passed
QGITA on the formula series: FTCP count `0`, lighthouse events `0`. Detection rate **HOLD**. Clock: step index times HarmonicRealityField.dt
Auris is not joined to Λ(t): **HOLD**. no function in the repo passes Λ(t) into get_auris_coherence
