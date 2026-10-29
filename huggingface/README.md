# Hugging Face bundle

Licence: **MIT**, the same licence as the repository [`LICENSE`](../LICENSE).

| Path | What it is |
| --- | --- |
| `hnc-field/` | Gradio Space for the Harmonic Nexus Core field |
| `auris-coherence/` | Gradio Space for the nine nodes and the coherence evaluator |
| `qgita-snr/` | Gradio Space for the QGITA adapter |
| `organism-replay/` | Gradio Space for the circulation replay |
| `fixed-seed-reproducible-runs/` | Dataset of the committed runs |
| `ORG_CARD.md` | Draft organisation card |
| `PUBLISH.md` | Upload commands. They read `HF_TOKEN` from the environment |

The brain runs are deterministic at commit `a00f744d`. Trade readiness, the Auris-to-Lambda link, and the QGITA detection rates are HOLD. Schumann f0 is null. HumanEval is not run.

Install the modules from this repo:

```bash
pip install "aureon @ git+https://github.com/RA-CONSULTING/Aureon-OS.git@a00f744d2e686e916e45b81dd4222408c368e305"
```

The git+ install brings the whole repo, trading modules included, and only the Spaces switch them off.

```python
from aureon.core.hnc_field import blend_field, read_canonical_field
from aureon.harmonic.aureon_harmonic_reality import HarmonicRealityField
from aureon.utils.aureon_queen_hive_mind import QueenHiveMind
from aureon.wisdom.aureon_qgita_framework import QGITAMarketAnalyzer
field = HarmonicRealityField(enable_multiverse=False)
print([field.step() for _ in range(100)][-1], field.coherence)
print(read_canonical_field().available, blend_field().available)
queen = QueenHiveMind.__new__(QueenHiveMind)
print(queen.get_auris_coherence(None))
print(QGITAMarketAnalyzer().analyze()["status"])
```

A false `available` flag means the canonical field had nothing fresh to read. The Spaces show that as unavailable. This bundle makes no track-record, return, or performance claim.
