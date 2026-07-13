# IEEE Scoring Rubric — v5 Papers
## All mathematics computationally verified 2026-04-08

---

## PROJECT ALFIE v5 — Score Card

| Criterion | Weight | v4 Score | v5 Score | Notes |
|-----------|--------|----------|----------|-------|
| Technical soundness | 25% | 7 | 8 | All equations verified. HNC formula now explained. Sensitivity analysis adds depth |
| Novelty/contribution | 20% | 7 | 7.5 | Same concept but now contextualized with HNC framework and 19-experiment dataset |
| Clarity/organization | 15% | 7 | 8 | HNC explanation fills the biggest gap. Frequency derivation chain is clear |
| Literature review | 10% | 6.5 | 7 | 23 references, appropriate breadth. Schumann and ITER added |
| Experimental evidence | 15% | 5 | 7.5 | Expanded from 4 to 19 experiments. Frequency sweep data. Zero-observer protocol |
| Reproducibility | 10% | 6 | 7.5 | Open-source repo cited. ESP32 firmware mentioned. Derivation chain traceable |
| Presentation quality | 5% | 6 | 7 | 3 figures, 2 tables. Proper IEEE structure |
| **Weighted Total** | **100%** | **6.5** | **7.6** | |

### Key improvements v4→v5:
1. HNC Master Formula (Eq. 0) now explained with all parameters and verification
2. Sensitivity analysis (Table II) — 5 parametric variants with demonstrator config
3. BLE experimental section expanded — all 19 experiments, frequency sweep, derivation chain
4. Thermal management discussion with ITER reference
5. Bridge paragraph connecting BLE to launcher physics
6. "Sacred frequency" language fully stripped

### Remaining weaknesses:
- Self-citation to unpublished white paper [5] (GitHub repo, not peer-reviewed)
- Single-author independent researcher (higher scrutiny)
- BLE-to-launcher physics bridge is acknowledged as indirect
- 3.9% joint probability doesn't reach 5% significance

---

## PROJECT DRUID v5 — Score Card

| Criterion | Weight | v4 Score | v5 Score | Notes |
|-----------|--------|----------|----------|-------|
| Technical soundness | 25% | 7 | 8.5 | All cascade math verified. Electron beam charging detailed. Acoustic-in-vacuum solved |
| Novelty/contribution | 20% | 7.5 | 8 | 7-layer cascade with sensitivity analysis is genuine contribution |
| Clarity/organization | 15% | 7 | 8 | HNC explained. Acoustic medium explicitly addressed. Process tree clear |
| Literature review | 10% | 7 | 7 | 20 references. Bamford 2024 and MEESST cited |
| Experimental evidence | 15% | 5 | 7.5 | Same expansion as Alfie. EPAS chamber specs add concrete engineering |
| Reproducibility | 10% | 6 | 7.5 | Open-source, ESP32, falsifiable predictions with quantitative thresholds |
| Presentation quality | 5% | 6 | 7 | 2 figures, 2 tables |
| **Weighted Total** | **100%** | **6.6** | **7.8** | |

### Key improvements v4→v5:
1. HNC framework explained in introduction
2. Electron beam charging physics — interaction time, current density, precedent missions
3. Acoustic-in-vacuum treatment — plasma medium for L6, solid-state hull for L7
4. Sensitivity analysis (Table II) — 6 degradation scenarios, graceful degradation shown
5. L5 Casimir correctly flagged as negligible (97.3→97.2%)
6. EPAS chamber specs (30cm Argon vessel, 13.56 MHz, Paschen-optimized)

### Remaining weaknesses:
- No experimental validation of ANY layer (all T_i are theoretical)
- 97.3% sounds too good — reviewers will be skeptical
- Casimir layer may still draw fire (even with honest sensitivity analysis)
- Competitor work (Bamford) has institutional backing

---

## COMPOSITE ASSESSMENT

| Metric | Alfie v4 | Alfie v5 | Druid v4 | Druid v5 |
|--------|----------|----------|----------|----------|
| Weighted score | 6.5 | 7.6 | 6.6 | 7.8 |
| Math verified | Partial | 100% | Partial | 100% |
| HNC explained | No | Yes | No | Yes |
| Sensitivity analysis | No | Yes (5 variants) | No | Yes (6 scenarios) |
| Experiments cited | 4 | 19 | 4 | 19 |
| Sacred language | Some | Zero | Some | Zero |

Both papers have improved by approximately 1.1-1.2 points. The biggest gains came from:
1. Actually explaining the HNC framework
2. Adding sensitivity analysis
3. Expanding experimental evidence
4. Addressing specific reviewer-anticipated questions (thermal, acoustic medium, charging)
