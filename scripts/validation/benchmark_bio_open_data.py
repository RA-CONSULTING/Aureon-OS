#!/usr/bin/env python3
"""Test + benchmark the bio pipeline on the data we legitimately have.

Two honest lanes, printed with ✅/❌:

1. **Bio anchor (synthetic / cited reference).** No open UPE dataset exists as a
   clean download (biophoton data lives in paper supplements — see
   ``docs/reports/UPE_DATA_AVAILABILITY.md``), so the UPE path is exercised on the
   cited reference profile + deterministic synthetic data: broadband/featureless
   UPE must score NON-separable (the honest anchor), planted emission lines must
   score separable, and the convergence map must run under governance.

2. **Real open molecular data.** The repo already holds genuine open-source spectra
   (NIST WebBook IR peaks in ``data/spectra/nist_ir_peaks.csv``). We run the
   falsifiable phenolic engine on them via ``connector.run_analysis`` and assert a
   valid, deterministic result — the "open source data + test" demonstration.

Run: ``python scripts/validation/benchmark_bio_open_data.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DATA = REPO_ROOT / "data" / "spectra"
FIXTURES = REPO_ROOT / "tests" / "fixtures"


def main(argv: list[str] | None = None) -> int:
    """Run the bio anchor + real-open-data checks; return 0 iff all pass."""
    import numpy as np

    from aureon.bio.convergence_map import analyze_convergence
    from aureon.bio.upe_signal_adapter import score_upe, synthetic_upe

    checks: list[tuple[bool, str]] = []

    # ---- Lane 1: bio anchor (synthetic / cited reference) ------------------
    broadband = score_upe(synthetic_upe("broadband"), consent=True,
                          provenance="open-data validation (synthetic UPE)", nulls=300)
    structured = score_upe(synthetic_upe("structured"), consent=True,
                          provenance="open-data validation (synthetic UPE)", nulls=300)
    checks.append((broadband.valid and not broadband.structure_present,
                   "broadband UPE reference -> structure ABSENT (honest anchor)"))
    checks.append((structured.structure_present,
                   "structured UPE (planted lines) -> structure PRESENT"))

    img = np.zeros((120, 120, 3), np.uint8)
    img[:60, :60] = (230, 30, 30)
    img[:60, 60:] = (30, 200, 30)
    img[60:, :60] = (30, 30, 220)
    img[60:, 60:] = (230, 220, 20)
    cmap = analyze_convergence(img, consent=True, provenance="open-data validation (synthetic image)",
                               grid=4, nulls=200)
    checks.append((cmap.valid and cmap.controls_pass
                   and all(c.converged == (c.channels_fired == 2) for c in cmap.cells),
                   f"convergence map valid; {cmap.n_converged}/{len(cmap.cells)} both-channel cells"))

    # ---- Lane 2: real open molecular data (NIST IR) ------------------------
    sources = [str(p) for p in (
        FIXTURES / "weed_phenolic_spectral_map_codex.csv",
        DATA / "nist_ir_peaks.csv",
        DATA / "curated_open_access_peaks.csv",
    ) if p.exists()]
    nist_present = (DATA / "nist_ir_peaks.csv").exists()
    if sources:
        import connector

        r1 = connector.run_analysis(sources, nulls=300, seed=0)
        r2 = connector.run_analysis(sources, nulls=300, seed=0)
        d1, d2 = r1.to_dict(), r2.to_dict()
        checks.append((d1["valid"] and len(d1["compounds"]) > 0,
                       f"real open data ({len(sources)} src, NIST={nist_present}) -> "
                       f"valid, {len(d1['compounds'])} compounds"))
        checks.append((d1["compounds"] == d2["compounds"],
                       "phenolic run on open data is deterministic (seed=0)"))
    else:
        checks.append((False, "no open-data sources found on disk"))

    print("Bio pipeline — open-source data test + benchmark")
    ok = True
    for passed, label in checks:
        ok = ok and passed
        print(f"  {'✅' if passed else '❌'} {label}")
    print(f"  broadband A_p={broadband.test_A_p} | structured A_p={structured.test_A_p} "
          f"B_p={structured.test_B_p}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
