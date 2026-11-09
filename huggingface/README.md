# Hugging Face bundle

Licence: **MIT**, the same licence as the repository [`LICENSE`](../LICENSE).

Status: local scaffold. The Spaces are not live. Go-live: **HOLD**. This page does not clear the orange release-boundary badge.

The Gradio apps bind to `127.0.0.1` and keep Gradio share off. A `0.0.0.0` listener needs `AUREON_HF_GARY_YES=1` and `AUREON_HF_LISTENER=1` together. A public Space or a public dataset also needs Gary's own yes. Those flags are not set here. Live trading stays off. The apps do not read a `.env` file and do not keep token values in the process.

The distribution measurement is [`measured/hf_space_distribution.json`](../measured/hf_space_distribution.json). It is a HOLD-skip when `HF_TOKEN` is missing, when Gary's yes is missing, or when the selected hardware would need a PRO plan. It does not report a Space as live.

| Path | What it is |
| --- | --- |
| `hnc-field/` | Gradio Space for the Harmonic Nexus Core field |
| `auris-coherence/` | Gradio Space for the nine nodes and the coherence evaluator |
| `qgita-snr/` | Gradio Space for the QGITA adapter |
| `organism-replay/` | Gradio Space for the circulation replay |
| `fixed-seed-reproducible-runs/` | Dataset of the committed runs |
| `ORG_CARD.md` | Draft organisation card |
| `PUBLISH.md` | Private upload commands. They read `HF_TOKEN` from the environment and were not run |
| `space_bind.py` | Guarded bind. Copied into each Space directory |
| `distribution.py` | Writes the HOLD-skip receipt. The default command does not sign in |

The brain runs are deterministic at commit `a00f744d`. Trade readiness, the Auris-to-Lambda link, and the QGITA detection rates are HOLD. Schumann f0 is null. HumanEval is not run.

Install the modules from this repo:

```bash
pip install "aureon @ git+https://github.com/RA-CONSULTING/Aureon-OS.git@bb04503119681adcf832f3c3e9b0cbf09fc7a938"
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
