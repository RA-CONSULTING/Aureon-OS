# HNC, Auris coherence, and QGITA

These figures are the HNC master-formula path, Auris coherence, and the QGITA analyzer. They are not a claim that the system is conscious or alive.

No outside model was called. Live trading stayed off. No order was placed.
HNC formula path, multiverse off: state `coherent`, coherence `0.7739191103121901`, last Λ(t) `1.1030284973375342`, steps `100`.
Multiverse extension: **measured**. project_to_3d sets noise to 0 when no observed residual is supplied. TranslationMap.noise_level is stored and is not read by that method. Three constructions of the default HarmonicRealityField returned the same series.
Auris coherence `0.5023340603593964` with status `⛔ COHERENCE BREAK - Do not trade`. Zero-input nodes without a reading: none. Series nodes without a reading: none.
Trade readiness: **HOLD**. market series loaded from public:kraken XBTUSD 2026-10-29T19:00:00Z to 2026-11-05T19:00:00Z; nodes without a reading on this series: none; no trade-outcome labels; release boundary stays HOLD
QGITA on the derived series `data/de440_timeseries.csv` (cited-unverified): status `complete`, FTCP count `0`, lighthouse events `0`. Detection rate **HOLD**. Clock: sample index. analyze_price_stream uses range(len(prices)) when no timestamps are passed
QGITA on the formula series: FTCP count `0`, lighthouse events `0`. Detection rate **HOLD**. Clock: step index times HarmonicRealityField.dt
QGITA on the public series `XBTUSD` (measured, key group `public:kraken`): status `complete`, FTCP count `0`, lighthouse events `0`. Detection rate **HOLD**. Clock: venue bar open time in unix seconds; price is the bar close
Auris is not joined to Λ(t): **HOLD**. no function in the repo passes Λ(t) into get_auris_coherence
