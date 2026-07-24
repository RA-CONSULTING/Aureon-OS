#!/usr/bin/env python3
"""Counter-frequency scan — the repo's φ/Fibonacci canon through the engine.

Scans the counter-frequency engine's SACRED_FREQUENCIES canon
(:mod:`aureon.bio.counter_frequency_reference`) through the **identical** governed
pipeline every other sensor uses (``score_sky``: controls → Test A / Test B →
separability at ``ALPHA`` → Operator/conscience veto → ``SCIENTIFIC_BOUNDARY``).
Nothing about the engine is modified; each verdict is reported exactly as returned.

Reuses the sky adapter's ``radio_hz`` path — no new engine machinery.
"""

from __future__ import annotations

import phenolic_fingerprint as engine
from aureon.bio import counter_frequency_reference as cf
from aureon.bio.human_harmonic_proxy import ProxyResult
from aureon.bio.sky_signal_adapter import score_sky

__all__ = ["score_counter_frequency", "main"]


def score_counter_frequency(
    name: str = "counter",
    *,
    consent: bool = True,
    provenance: str | None = None,
    nulls: int = engine.DEFAULT_NULLS,
    seed: int = 0,
) -> ProxyResult:
    """Scan a named counter-frequency catalog ('counter' | 'fibonacci' | 'phi')."""
    freqs = cf.catalog_hz(name)
    prov = provenance or f"counter frequency: {name} ({cf.COUNTER_FREQUENCY_CITATION})"
    return score_sky(freqs, consent=consent, provenance=prov, kind="radio_hz",
                     nulls=nulls, seed=seed)


def main(argv: list[str] | None = None) -> int:
    """CLI: scan the φ/Fibonacci canon through the engine and report neutrally."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Direct the repo's own φ/Fibonacci harmonic canon at the phenolic "
        "engine (φ logic unchanged)."
    )
    parser.add_argument("--system", choices=["counter", "fibonacci", "phi", "all"],
                        default="all")
    parser.add_argument("--nulls", type=int, default=engine.DEFAULT_NULLS)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)

    print("Counter-frequency scan — the repo's φ/Fibonacci canon, one unchanged φ engine")
    print(f"  boundary: {cf.COUNTER_FREQUENCY_BOUNDARY}")

    def _report(label, result):
        d = result.to_dict()
        print(f"  {label:10s}: n_tones={d['n_tones']} valid={d['valid']} "
              f"structure_present={d['structure_present']} "
              f"A_p={d['test_A_p']} B_p={d['test_B_p']}")

    want = ("counter", "fibonacci", "phi") if args.system == "all" else (args.system,)
    for sys_name in want:
        _report(sys_name, score_counter_frequency(sys_name, nulls=args.nulls, seed=args.seed))
    return 0


if __name__ == "__main__":  # pragma: no cover - manual entry point
    raise SystemExit(main())
