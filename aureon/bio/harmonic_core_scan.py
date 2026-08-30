#!/usr/bin/env python3
"""Harmonic-core scan — direct the HNC's OWN harmonic substrate at the engine.

Where the sacred-lattice scan mapped the sky through Earth's lattice, this scans the
repo's **core harmonic system** — the Master Formula Λ(t) modes, the Celtic Ogham
tree-tones, and the Ghost Dance ancestral Solfeggio ladder
(:mod:`aureon.bio.harmonic_core_reference`) — through the **identical** governed
pipeline every other sensor uses (``score_sky``: controls → Test A / Test B →
separability at ``ALPHA`` → Operator/conscience veto → ``SCIENTIFIC_BOUNDARY``).
Nothing about the engine is modified; each verdict is reported exactly as returned.

Reuses the sky adapter's ``radio_hz`` path — no new engine machinery.
"""

from __future__ import annotations

import phenolic_fingerprint as engine
from aureon.bio import harmonic_core_reference as core
from aureon.bio.human_harmonic_proxy import ProxyResult
from aureon.bio.sky_signal_adapter import score_sky

__all__ = ["score_harmonic_core", "main"]

_CITATIONS = {
    "lambda": core.LAMBDA_CITATION,
    "ogham": core.OGHAM_CITATION,
    "ghostdance": core.GHOST_DANCE_CITATION,
}


def score_harmonic_core(
    name: str,
    *,
    consent: bool = True,
    provenance: str | None = None,
    nulls: int = engine.DEFAULT_NULLS,
    seed: int = 0,
) -> ProxyResult:
    """Scan a named harmonic-core catalog ('lambda' | 'ogham' | 'ghostdance')."""
    freqs = core.catalog_hz(name)
    citation = _CITATIONS.get(name, "")
    prov = provenance or f"harmonic core: {name} ({citation})"
    return score_sky(freqs, consent=consent, provenance=prov, kind="radio_hz",
                     nulls=nulls, seed=seed)


def main(argv: list[str] | None = None) -> int:
    """CLI: scan the HNC's own harmonic systems through the engine and report neutrally."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Direct the repo's own HNC harmonic substrate (Λ(t) modes, Celtic "
        "Ogham, Ghost Dance) at the phenolic engine (φ logic unchanged)."
    )
    parser.add_argument("--system",
                        choices=["lambda", "ogham", "ghostdance", "all"], default="all")
    parser.add_argument("--nulls", type=int, default=engine.DEFAULT_NULLS)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)

    print("Harmonic-core scan — the repo's OWN harmonic substrate, one unchanged φ engine")
    print(f"  boundary: {core.HARMONIC_CORE_BOUNDARY}")

    def _report(label, result):
        d = result.to_dict()
        print(f"  {label:11s}: n_tones={d['n_tones']} valid={d['valid']} "
              f"structure_present={d['structure_present']} "
              f"A_p={d['test_A_p']} B_p={d['test_B_p']}")

    want = ("lambda", "ogham", "ghostdance") if args.system == "all" else (args.system,)
    for sys_name in want:
        _report(sys_name, score_harmonic_core(sys_name, nulls=args.nulls, seed=args.seed))
    return 0


if __name__ == "__main__":  # pragma: no cover - manual entry point
    raise SystemExit(main())
