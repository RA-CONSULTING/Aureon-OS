---
title: QGITA adapter
emoji: "🔷"
colorFrom: blue
colorTo: gray
sdk: gradio
sdk_version: 5.49.1
app_file: app.py
pinned: false
license: mit
---

# QGITA adapter

Licence: **MIT**, the same licence as the Aureon OS [`LICENSE`](https://github.com/RA-CONSULTING/Aureon-OS/blob/a00f744d2e686e916e45b81dd4222408c368e305/LICENSE).

Events come from the QGITA adapter `QGITAMarketAnalyzer.analyze`. The Space does not reimplement the detector and does not show the adapter's signals object.

The bundled series is a replay of `data/de440_timeseries.csv`, column `Lambda`. The committed record tags that series cited-unverified and says it is not public market data. Link: [qgita_snr.json](https://github.com/RA-CONSULTING/Aureon-OS/blob/a00f744d2e686e916e45b81dd4222408c368e305/reports/measured/qgita_snr.json).

| Figure | Value | Label |
| --- | --- | --- |
| Adapter FTCP count on the derived series | 0 | cited |
| Adapter lighthouse count on the derived series | 0 | cited |
| Detection rate | HOLD | HOLD |
| False-alarm rate | HOLD | HOLD |

A count from a fresh adapter call in this process is labelled inferred. Schumann f0: **null**, **HOLD**.

Trade readiness: **HOLD**. Auris joined to Lambda: **HOLD**.

This Space makes no track-record, return, or performance claim. Refused imports: aureon.exchanges, aureon.trading, unified_margin_trader, aureon.bots, aureon.bots_intelligence, aureon.bridges, aureon.scanners. No keys are present.
