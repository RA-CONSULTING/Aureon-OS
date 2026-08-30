#!/usr/bin/env python3
"""Cosmic scan — direct the repo's Schumann / planetary / space-weather systems at the engine.

Enriches the sky picture by scanning three more real sky/space frequency systems
(:mod:`aureon.bio.cosmic_reference`) through the **identical** governed pipeline the
other sensors use (``score_signal`` / ``score_sky``: controls → Test A / Test B →
separability at ``ALPHA`` → Operator/conscience veto → ``SCIENTIFIC_BOUNDARY``).
Nothing about the engine is modified; each verdict is reported exactly as the test
returns it.

Reuses the sky adapter's ``radio_hz`` path for the Schumann and planetary line lists,
and the timeseries sensor for the Kp / ap / F10.7 space-weather series. No new engine
machinery.
"""

from __future__ import annotations

from pathlib import Path

import phenolic_fingerprint as engine
from aureon.bio import cosmic_reference as cosmic
from aureon.bio.human_harmonic_proxy import (
    HumanSignal,
    ProxyResult,
    score_signal,
)
from aureon.bio.sky_signal_adapter import score_sky

__all__ = [
    "score_cosmic_catalog",
    "score_space_weather",
    "main",
]


def score_cosmic_catalog(
    name: str,
    *,
    consent: bool = True,
    provenance: str | None = None,
    nulls: int = engine.DEFAULT_NULLS,
    seed: int = 0,
) -> ProxyResult:
    """Scan a named cosmic catalog ('schumann' or 'planetary') through the engine."""
    freqs = cosmic.catalog_hz(name)
    citation = cosmic.SCHUMANN_CITATION if name == "schumann" else cosmic.PLANETARY_CITATION
    prov = provenance or f"cosmic catalog: {name} ({citation})"
    return score_sky(freqs, consent=consent, provenance=prov, kind="radio_hz", nulls=nulls, seed=seed)


def score_space_weather(
    *,
    path: str | Path = "data/sim_kp.csv",
    consent: bool = True,
    provenance: str | None = None,
    nulls: int = engine.DEFAULT_NULLS,
    seed: int = 0,
) -> ProxyResult:
    """Scan the pooled Kp / ap / F10.7 space-weather tones through the engine."""
    tones = cosmic.space_weather_tones(path)
    signal = HumanSignal(
        label="cosmic:space_weather",
        frequencies_hz=tones,
        provenance=provenance or f"space weather ({cosmic.SPACE_WEATHER_CITATION})",
        consent=consent,
        modality="sky",
        notes="pooled Kp/ap/F10.7 dominant tones; derived-signal structure only",
    )
    return score_signal(signal, nulls=nulls, seed=seed)


def main(argv: list[str] | None = None) -> int:
    """CLI: scan the cosmic systems through the engine and report neutrally."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Direct the repo's Schumann / planetary / space-weather systems at "
        "the phenolic engine (φ logic unchanged)."
    )
    parser.add_argument("--system", choices=["schumann", "planetary", "space_weather", "all"],
                        default="all")
    parser.add_argument("--nulls", type=int, default=engine.DEFAULT_NULLS)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)

    print("Cosmic scan — more repo systems, directed at the sky (φ logic unchanged)")
    print(f"  boundary: {cosmic.COSMIC_BOUNDARY}")

    def _report(label, result):
        d = result.to_dict()
        print(f"  {label:14s}: n_tones={d['n_tones']} valid={d['valid']} "
              f"structure_present={d['structure_present']} "
              f"A_p={d['test_A_p']} B_p={d['test_B_p']}")

    want = ("schumann", "planetary", "space_weather") if args.system == "all" else (args.system,)
    for sys_name in want:
        if sys_name == "space_weather":
            _report("space_weather", score_space_weather(nulls=args.nulls, seed=args.seed))
        else:
            _report(sys_name, score_cosmic_catalog(sys_name, nulls=args.nulls, seed=args.seed))
    return 0


if __name__ == "__main__":  # pragma: no cover - manual entry point
    raise SystemExit(main())
