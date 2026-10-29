---
title: Organism replay
emoji: "🔷"
colorFrom: blue
colorTo: gray
sdk: gradio
sdk_version: 5.49.1
app_file: app.py
pinned: false
license: mit
---

# Organism replay

Licence: **MIT**, the same licence as the Aureon OS [`LICENSE`](https://github.com/RA-CONSULTING/Aureon-OS/blob/a00f744d2e686e916e45b81dd4222408c368e305/LICENSE).

The dashboard loads `replay/organism.json`, a byte copy of the committed circulation record. Link: [organism.json](https://github.com/RA-CONSULTING/Aureon-OS/blob/a00f744d2e686e916e45b81dd4222408c368e305/reports/measured/organism.json). It is labelled replay. This Space does not start a seat and does not add telemetry.

`CognitiveDashboard` is constructed on an empty bus. The replay has no `ics.*` rows, so those panels are unavailable rather than filled with zeros.

The fault block in the file is seeded synthetic input, seed `20261024`, injected by the harness. It is not telemetry. A claim that those faults were recorded from a seat is **HOLD**.

Cited from the same file: connectivity verdict `pass`, score `1.0`, roster `14`, connected `14`, HTTP seat bound `false`.

Trade readiness: **HOLD**. Auris joined to Lambda: **HOLD**. QGITA detection rate: **HOLD**. Schumann f0: **null**, **HOLD**.

This Space makes no track-record, return, or performance claim. Trading modules are hard-disabled. No exchange is contacted.
