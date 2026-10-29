---
title: HNC field
emoji: "🔷"
colorFrom: blue
colorTo: gray
sdk: gradio
sdk_version: 5.49.1
app_file: app.py
pinned: false
license: mit
---

# HNC field

Licence: **MIT**, the same licence as the Aureon OS [`LICENSE`](https://github.com/RA-CONSULTING/Aureon-OS/blob/a00f744d2e686e916e45b81dd4222408c368e305/LICENSE).

This Space runs `HarmonicRealityField.step`, `read_canonical_field`, and `blend_field` from the Aureon OS repo. It does not reimplement those formulas.

The bundled file `replay/brain.json` is a copy of the committed brain run. That brain run is a deterministic run at commit `a00f744d2e686e916e45b81dd4222408c368e305`.

The class default `HarmonicRealityField()` is the multiverse-on path. The other row is the multiverse-off path (`enable_multiverse=False`). Both are cited from [reports/measured/brain.json](https://github.com/RA-CONSULTING/Aureon-OS/blob/a00f744d2e686e916e45b81dd4222408c368e305/reports/measured/brain.json).

| Path | Coherence | Last Lambda | State | Label |
| --- | --- | --- | --- | --- |
| Class default HarmonicRealityField() (multiverse on) | 0.857719007627168 | 0.002306037019850606 | LOCKED | cited |
| enable_multiverse=False (multiverse off) | 0.9331334813083556 | 1.409626852655939 | UNIFIED | cited |

The multiverse-off state value stored in the file is `unified`. The class-default state value stored in `multiverse_extension` is `locked`. A missing input is unavailable.

Trade readiness: **HOLD**. Auris joined to Lambda: **HOLD**. QGITA detection rate: **HOLD**. Schumann f0: **null**, **HOLD**. No committed run in this Space measured Schumann f0.

There is no canonical-field envelope in the replay. `read_canonical_field` stays unavailable until a fresh envelope is pasted.

This Space makes no track-record, return, or performance claim. Refused imports: aureon.exchanges, aureon.trading, unified_margin_trader, aureon.bots, aureon.bots_intelligence, aureon.bridges, aureon.scanners. No keys are present.
