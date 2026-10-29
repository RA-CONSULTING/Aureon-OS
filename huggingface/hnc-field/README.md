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

The bundled file `replay/brain.json` is a copy of the committed brain run. That brain run is a fixed-seed reproducible run at commit `a00f744d2e686e916e45b81dd4222408c368e305`.

Cited figures, linked to [reports/measured/brain.json](https://github.com/RA-CONSULTING/Aureon-OS/blob/a00f744d2e686e916e45b81dd4222408c368e305/reports/measured/brain.json):

| Figure | Value | Label |
| --- | --- | --- |
| Formula coherence | 0.9331334813083556 | cited |
| Last Lambda | 1.409626852655939 | cited |
| State | unified | cited |

A local rerun is labelled inferred. If it matches the file, the match is reported. A missing input is unavailable.

Trade readiness: **HOLD**. Auris joined to Lambda: **HOLD**. QGITA detection rate: **HOLD**. Schumann f0: **null**, **HOLD**. No committed run in this Space measured Schumann f0.

There is no canonical-field envelope in the replay. `read_canonical_field` stays unavailable until a fresh envelope is pasted.

This Space makes no track-record, return, or performance claim. Trading modules are hard-disabled. No exchange is contacted.
