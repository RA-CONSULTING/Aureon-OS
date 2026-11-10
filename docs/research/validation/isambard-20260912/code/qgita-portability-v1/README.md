# QGITA supplemental portability audit v1

This supplemental audit was added after inspecting the Isambard rerun differences. It is an explicitly post-hoc diagnostic; it does not amend the frozen v2 protocol or change its failed byte-identity result.

`structural_audit.py` is derived from the frozen `verify_qgita_ucr_postconfirmatory_robustness.py`. Its structural, arithmetic, seed, family bootstrap and spectral-preservation checks remain intact. The changed entry path applies those checks to the rerun ledger, verifies stdout against the rerun, and reports historical byte identity separately. `portability_audit.py` compares all JSON leaves. All decision/identity/summary fields must be exactly equal; only the specified selected-score and spectral-error diagnostics may differ, and every difference is reported. No claim of numerical score equivalence is made.

Run:

    python test_portability.py
    python portability_audit.py /path/to/package --output supplemental-audit.json

The exercised package is `qgita-ucr-full-6145729/package`. Its sole pinned Python requirement is numpy==2.3.5. Inputs and numerical constants retain the frozen hashes and spectral tolerance. A successful supplemental audit does not convert missing-data noninferiority failures to success, establish a Fibonacci-specific mechanism, or count as independent scientific replication.
