"""🧬 Signal Lab — the gated bio statistical engine of the fused runtime.

Fusion wrapper over the upstream repo's bio lane
(aureon/bio/human_harmonic_proxy.py + coherence_scan.py + false_discovery.py),
driven by the phenolic_fingerprint engine at the upstream repo root.

Contract (per the activation census):
  * Upstream modules are IMPORTED ONLY, lazily, and only after
    AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS=1 and AUREON_AUDIT_MODE=1 are set and
    sys.path is pinned to the upstream repo root (which also makes
    phenolic_fingerprint importable). No upstream main()/launchers run.
  * The tool is capability_gate-wrapped: scoring requires
    ``data_integrity:analyze_data_patterns`` (the existing ANALYZE-level gate
    for statistical analysis of derived data). A gate refusal produces a
    BLOCKED verdict — never a silent pass.
  * A submission is a *family* of derived signals (from file/JSON). Each goes
    through the governed pipeline (consent/provenance gate -> mandatory engine
    controls -> Test A / Test B -> Operator hard boundary + conscience veto).
    Per-lane conjunction p-values ``max(p_A, p_B)`` then get Benjamini-
    Hochberg FDR q-values across the family.
  * Every verdict publishes a ``bio.signal_verdict`` event on the thoughtbus
    spine. Verdicts are appended to fusion state (signal_lab_verdicts.jsonl).

Scientific boundary (upstream, enforced): this measures statistical structure
in a derived signal only — NOT a measurement of a biological aura, field,
health, or trait of any person; no efficacy claim.

CLI:
  python -m aureon_fusion.signal_lab demo            offline synthetic self-test + mini FDR audit
  python -m aureon_fusion.signal_lab status          engine/gate availability + last verdicts
  python -m aureon_fusion.signal_lab submit --file signals.json [--nulls N] [--seed S]

Import-safe: no side effects at import time; upstream imports happen only
inside functions, under the suppression env vars.
"""

import json
import os
import sys
import time
from pathlib import Path

from .paths import AUREON_UPSTREAM, FUSION_STATE
from . import capability_gate
from . import events

LAB_DIR = FUSION_STATE / "signal_lab"
VERDICTS_LOG = LAB_DIR / "signal_lab_verdicts.jsonl"
STATE_FILE = LAB_DIR / "signal_lab_state.json"

# Existing ANALYZE-level gate: statistical analysis of derived data patterns.
GATE_KEY = "data_integrity:analyze_data_patterns"

SCIENTIFIC_BOUNDARY = (
    "Statistical structure in a derived signal only - NOT a measurement of a "
    "biological aura, field, health, or trait of any person; no efficacy claim."
)

_BIO = None
_BIO_ERROR = None


def _ensure_upstream_env() -> None:
    """Census doctrine: suppression env vars BEFORE any aureon import, and the
    upstream repo root pinned on sys.path (makes phenolic_fingerprint
    importable). Idempotent."""
    os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")
    os.environ.setdefault("AUREON_AUDIT_MODE", "1")
    os.environ.pop("SIMULATED_ATTACKS", None)  # upstream real-data contract
    if str(AUREON_UPSTREAM) not in sys.path:
        sys.path.insert(0, str(AUREON_UPSTREAM))


def _load_bio():
    """Lazy-import the upstream bio lane under the suppression env vars.
    Returns (proxy_module, fdr_module) or raises."""
    global _BIO, _BIO_ERROR
    if _BIO is None:
        _ensure_upstream_env()
        try:
            from aureon.bio import human_harmonic_proxy as proxy
            from aureon.bio import false_discovery as fdr

            _BIO = (proxy, fdr)
        except Exception as e:  # reported, never fatal at import time
            _BIO_ERROR = str(e)
            raise
    return _BIO


def _bh_qvalues(pvals):
    """Benjamini-Hochberg adjusted q-values for a family of p-values.

    pvals: list of (index, p) for lanes with a valid p. Returns
    {index: q}. Stdlib-only mirror of the upstream BH step-up."""
    m = len(pvals)
    if m == 0:
        return {}
    ordered = sorted(pvals, key=lambda kv: kv[1])
    q = {}
    prev = 1.0
    for rank in range(m, 0, -1):
        idx, p = ordered[rank - 1]
        prev = min(prev, p * m / rank)
        q[idx] = min(1.0, prev)
    return q


def _gate_allows() -> tuple:
    """(allowed, gate_result_dict) via the capability gate. A gate failure or
    error means NOT allowed — the lab never scores without the gate."""
    try:
        result = capability_gate.check(GATE_KEY)
        return bool(result.get("allowed")), result
    except Exception as e:
        return False, {"gate": GATE_KEY, "verdict": "ERROR", "reason": str(e)}


def _publish_verdict(payload: dict) -> None:
    events.publish_event("signal_lab", "bio.signal_verdict", payload, priority=5)


def _record(verdicts: list) -> None:
    """Append verdicts to fusion state."""
    try:
        LAB_DIR.mkdir(parents=True, exist_ok=True)
        with open(VERDICTS_LOG, "a", encoding="utf-8") as f:
            for v in verdicts:
                f.write(json.dumps(v, ensure_ascii=False) + "\n")
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": time.time(),
                "last_run": verdicts[-1] if verdicts else None,
                "total_verdicts": sum(1 for _ in open(VERDICTS_LOG, "r", encoding="utf-8")),
            }, f, indent=2, ensure_ascii=False)
    except OSError:
        pass


def submit_signals(signals: list, *, nulls: int = None, seed: int = 0,
                   q_level: float = None) -> list:
    """
    Score a family of derived signals through the governed pipeline.

    Each entry: {label, frequencies_hz, provenance, consent, modality}.
    Returns one verdict dict per entry; publishes bio.signal_verdict events.
    """
    proxy, fdr = _load_bio()
    if nulls is None:
        nulls = proxy.engine.DEFAULT_NULLS
    if q_level is None:
        q_level = float(fdr.ALPHA)

    allowed, gate_result = _gate_allows()
    if not allowed:
        verdicts = [{
            "label": s.get("label", f"signal-{i}"),
            "verdict": "BLOCKED",
            "reason": f"capability gate refused: {gate_result.get('reason')}",
            "gate": gate_result,
            "blocked": True,
            "boundary": proxy.SCIENTIFIC_BOUNDARY,
            "timestamp": time.time(),
        } for i, s in enumerate(signals)]
        for v in verdicts:
            _publish_verdict(v)
        _record(verdicts)
        return verdicts

    results = []
    for i, spec in enumerate(signals):
        signal = proxy.HumanSignal(
            label=str(spec.get("label", f"signal-{i}")),
            frequencies_hz=tuple(float(x) for x in spec.get("frequencies_hz", ())),
            provenance=str(spec.get("provenance", "")),
            consent=bool(spec.get("consent", False)),
            modality=str(spec.get("modality", "file")),
            notes=str(spec.get("notes", "submitted via aureon_fusion.signal_lab")),
        )
        try:
            result = proxy.score_signal(signal, nulls=int(nulls), seed=int(seed))
            results.append((i, result))
        except Exception as e:
            results.append((i, proxy._blocked_result(signal, f"scoring error: {e}")))

    # BH FDR across the family's valid conjunction p-values
    lane_p = []
    for i, result in results:
        if (result.valid and not result.blocked
                and result.test_A_p is not None and result.test_B_p is not None):
            lane_p.append((i, max(float(result.test_A_p), float(result.test_B_p))))
    qvalues = _bh_qvalues(lane_p)

    verdicts = []
    for i, result in results:
        q = qvalues.get(i)
        if result.blocked:
            verdict = "BLOCKED"
        elif not result.valid:
            verdict = "INVALID"
        elif result.structure_present and (q is None or q <= q_level):
            verdict = "STRUCTURE"
        else:
            verdict = "NO_STRUCTURE"
        v = {
            "label": result.label,
            "verdict": verdict,
            "valid": result.valid,
            "blocked": result.blocked,
            "reason": result.reason,
            "structure_present": result.structure_present,
            "test_A_p": result.test_A_p,
            "test_B_p": result.test_B_p,
            "q_value": q,
            "q_level": q_level,
            "n_tones": result.n_tones,
            "modality": result.modality,
            "provenance": result.provenance,
            "consent": result.consent,
            "gate": {"gate": GATE_KEY, "verdict": gate_result.get("verdict")},
            "boundary": proxy.SCIENTIFIC_BOUNDARY,
            "timestamp": time.time(),
        }
        verdicts.append(v)
        _publish_verdict(v)

    _record(verdicts)
    return verdicts


def submit_file(path, *, nulls: int = None, seed: int = 0) -> list:
    """Load a submission from JSON: {"signals": [{label, frequencies_hz, ...}]}"""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    signals = data.get("signals", []) if isinstance(data, dict) else data
    if not isinstance(signals, list) or not signals:
        raise ValueError("submission file must contain a non-empty 'signals' list")
    return submit_signals(signals, nulls=nulls, seed=seed)


def fdr_audit(*, trials: int = 3, nulls: int = 100, m_null: int = 2,
              m_signal: int = 2, seed: int = 0) -> dict:
    """Run the upstream Benjamini-Hochberg false-discovery audit (reduced
    parameters for an offline demo; the upstream defaults are far heavier)."""
    _, fdr = _load_bio()
    report = fdr.compute_false_discovery(
        trials=trials, nulls=nulls, m_null=m_null, m_signal=m_signal, seed0=seed)
    d = report.to_dict()
    events.publish_event("signal_lab", "bio.fdr_audit", {
        "trials": report.trials, "nulls": report.nulls,
        "bh_controls_fdr": report.bh_controls_fdr,
        "bh_dominates_bonferroni": report.bh_dominates_bonferroni,
        "q": report.q,
    }, priority=4)
    return d


def demo(*, nulls: int = 200, seed: int = 0) -> int:
    """Offline synthetic self-test: structured + noise + unconsented through
    the governed pipeline, plus a mini FDR audit. No real human data, no
    network. Returns 0 when every expectation holds."""
    proxy, _ = _load_bio()
    allowed, gate_result = _gate_allows()
    print("=" * 78)
    print("🧬 SIGNAL LAB — OFFLINE DEMO (synthetic self-test, no real human data)")
    print("=" * 78)
    print(f"  boundary : {proxy.SCIENTIFIC_BOUNDARY}")
    print(f"  engine   : phenolic_fingerprint @ {AUREON_UPSTREAM}")
    print(f"  band     : {proxy.TARGET_BAND_HZ} Hz  alpha={proxy.engine.ALPHA}")
    print(f"  gate     : {GATE_KEY} -> "
          f"{'ALLOW' if allowed else 'REFUSED (' + str(gate_result.get('reason')) + ')'}")

    structured = proxy.run_synthetic("structured", nulls=nulls, seed=seed)
    noise = proxy.run_synthetic("noise", nulls=nulls, seed=seed)
    from dataclasses import replace
    unconsented = proxy.score_signal(
        replace(proxy.SyntheticSignalAdapter().extract(mode="structured", seed=seed),
                consent=False),
        nulls=nulls, seed=seed)

    checks = [
        (structured.valid and noise.valid, "engine controls valid on both runs"),
        (structured.structure_present, "structured signal -> structure PRESENT"),
        (not noise.structure_present, "noise signal -> structure ABSENT"),
        (not structured.blocked, "consented structured run not blocked"),
        (unconsented.blocked and unconsented.to_dict()["structure_present"] is False,
         "unconsented run blocked + finding suppressed"),
    ]
    ok = True
    for passed, label in checks:
        ok = ok and passed
        print(f"  {'✅' if passed else '❌'} {label}")
    print(f"  structured: A_p={structured.test_A_p:.4g} B_p={structured.test_B_p:.4g} "
          f"n={structured.n_tones}")
    print(f"  noise     : A_p={noise.test_A_p:.4g} B_p={noise.test_B_p:.4g} n={noise.n_tones}")

    print("\n  FDR audit (mini: Benjamini-Hochberg vs Bonferroni vs uncorrected):")
    rep = fdr_audit()
    print(f"  {rep['trials']} families · {rep['m_lanes']} lanes · {rep['nulls']} nulls · q={rep['q']:g}")
    for m in rep["methods"]:
        mark = "✅" if m["controls_fdr"] else "❌"
        print(f"    {m['name']:<19s} power={m['power']:.3f} FDR={m['fdr']:.3f} {mark}")
    ok = ok and rep["bh_controls_fdr"] and rep["bh_dominates_bonferroni"]

    print("=" * 78)
    print("✅ SIGNAL LAB DEMO PASSED" if ok else "❌ SIGNAL LAB DEMO FAILED")
    return 0 if ok else 1


def status() -> dict:
    """Availability snapshot: upstream import, gate, state."""
    s = {"lab_dir": str(LAB_DIR), "gate": GATE_KEY, "boundary": SCIENTIFIC_BOUNDARY}
    allowed, gate_result = _gate_allows()
    s["gate_verdict"] = gate_result.get("verdict")
    s["gate_allowed"] = allowed
    try:
        _ensure_upstream_env()
        import phenolic_fingerprint as engine

        proxy, fdr = _load_bio()
        s["engine"] = {
            "available": True,
            "repo_root": str(AUREON_UPSTREAM),
            "alpha": float(engine.ALPHA),
            "default_nulls": int(engine.DEFAULT_NULLS),
            "target_band_hz": list(proxy.TARGET_BAND_HZ),
        }
        s["fdr"] = {"default_q": float(fdr.DEFAULT_Q), "alpha": float(fdr.ALPHA)}
    except Exception as e:
        s["engine"] = {"available": False, "error": _BIO_ERROR or str(e)}
    try:
        if STATE_FILE.exists():
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                s["state"] = json.load(f)
        else:
            s["state"] = None
    except OSError:
        s["state"] = None
    return s


def _print_status() -> None:
    s = status()
    print("=" * 78)
    print("🧬 SIGNAL LAB — STATUS")
    print("=" * 78)
    print(f"  engine available : {s['engine'].get('available')}")
    if s["engine"].get("available"):
        print(f"    repo root      : {s['engine'].get('repo_root')}")
        print(f"    alpha          : {s['engine'].get('alpha')}")
        print(f"    default nulls  : {s['engine'].get('default_nulls')}")
        print(f"    target band    : {s['engine'].get('target_band_hz')} Hz")
    else:
        print(f"    error          : {s['engine'].get('error')}")
    print(f"  gate {s['gate']}: {s['gate_verdict']} (allowed={s['gate_allowed']})")
    st = s.get("state")
    if st:
        print(f"  verdicts logged  : {st.get('total_verdicts')}")
        last = st.get("last_run") or {}
        print(f"  last verdict     : {last.get('label')} -> {last.get('verdict')}")
    else:
        print("  verdicts logged  : 0")
    print("=" * 78)


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print("usage: python -m aureon_fusion.signal_lab demo|status|submit")
        print("  demo                 offline synthetic self-test + mini FDR audit")
        print("  status               engine/gate availability + last verdicts")
        print("  submit --file F.json score a family of derived signals (FDR-adjusted)")
        print("                       JSON: {\"signals\": [{label, frequencies_hz,")
        print("                                 provenance, consent, modality}]}")
        print("  [--nulls N] [--seed S] tune the permutation nulls / reproducibility seed")
        return 0

    verb = argv[0]
    rest = argv[1:]
    nulls = None
    seed = 0
    if "--nulls" in rest:
        i = rest.index("--nulls")
        nulls = int(rest[i + 1])
        del rest[i:i + 2]
    if "--seed" in rest:
        i = rest.index("--seed")
        seed = int(rest[i + 1])
        del rest[i:i + 2]

    if verb == "demo":
        return demo(nulls=nulls or 200, seed=seed)
    if verb == "status":
        _print_status()
        return 0
    if verb == "submit":
        if "--file" not in rest:
            print("usage: submit --file signals.json", file=sys.stderr)
            return 2
        path = rest[rest.index("--file") + 1]
        try:
            verdicts = submit_file(path, nulls=nulls, seed=seed)
        except Exception as e:
            print(f"❌ submission failed: {e}", file=sys.stderr)
            return 1
        for v in verdicts:
            print(f"  {v['label']}: {v['verdict']}"
                  + (f" (q={v['q_value']:.4g})" if v.get("q_value") is not None else "")
                  + (f" — {v['reason']}" if v.get("reason") else ""))
        return 0 if all(v["verdict"] != "INVALID" for v in verdicts) else 1

    print(f"unknown verb: {verb} (expected demo|status|submit)", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
