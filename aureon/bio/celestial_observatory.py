#!/usr/bin/env python3
"""The φ Celestial Observatory — every sky-facing sensor, one unchanged engine.

This is the capstone that pulls the thread together: it operates the whole family of
sky/cosmic φ sensors through the **same** unchanged phenolic engine and reports one
consolidated picture. Each lane is an existing governed scorer (nothing reinvented,
no engine logic changed); the observatory just runs them all and tabulates what the
pre-registered test returns for each, neutrally.

Lanes (each reuses its own module):
  * Hydrogen Balmer / solar Fraunhofer / airglow line lists  → ``sky_signal_adapter``
  * Diffuse night-sky background (featureless anchor)         → ``sky_signal_adapter``
  * NASA host-star Wien colour (pooled)                       → ``sky_map`` sources
  * Schumann ionospheric modes / planetary Cosmic-Octave      → ``cosmic_scan``
  * Kp/ap/F10.7 space weather                                 → ``cosmic_scan``
  * DE440 coherence spectrum                                  → ``coherence_scan``
  * Sacred lattice: stargate / Maeshowe / Metatron            → ``sacred_lattice_scan``
  * Harmonic core: Master Formula Λ(t) / Ogham / Ghost Dance  → ``harmonic_core_scan``
  * Counter-frequency: φ/Fibonacci harmonic canon              → ``counter_frequency_scan``
  * All-sky RA/Dec map + sacred-lattice Earth-grid map        → ``sky_map``

Every lane routes through ``score_signal`` (consent/provenance → controls →
Operator/conscience veto → Test A / Test B → separability at ``ALPHA``) and carries
the shared ``SCIENTIFIC_BOUNDARY``. Verdicts are reported exactly as returned.

Pure stdlib + numpy + the bio lanes; matplotlib for the rendered picture.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Final

import phenolic_fingerprint as engine
from aureon.bio.human_harmonic_proxy import (
    HumanSignal,
    ProxyResult,
    score_signal,
)

__all__ = [
    "OBSERVATORY_BOUNDARY",
    "OBS_RUN_TOPIC",
    "OBS_TRACE_NAME",
    "LaneReading",
    "ObservatoryReport",
    "observe",
    "render_observatory",
    "write_observatory_report",
    "emit_observatory",
    "main",
]

#: ThoughtBus topic + bus-trace name — mirrors the human-proxy / phenolic-bridge idiom
#: so the metacognition monitor / Queen can sense the observatory's consolidated run.
OBS_RUN_TOPIC: Final[str] = "bio.observatory.run"
OBS_TRACE_NAME: Final[str] = "celestial_observatory"
_SOURCE: Final[str] = "celestial_observatory"

OBSERVATORY_BOUNDARY: Final[str] = (
    "The φ Celestial Observatory reports statistical structure in derived signals "
    "only, across every sky/cosmic lane, through one unchanged φ engine - NOT a claim "
    "about the nature, composition, or behaviour of any celestial object, and no "
    "efficacy claim. Each verdict is exactly what the pre-registered test returned."
)


@dataclass(frozen=True)
class LaneReading:
    """One sensor lane's verdict, as the engine returned it."""

    lane: str
    domain: str
    n_tones: int
    valid: bool
    structure_present: bool
    test_A_p: float | None
    test_B_p: float | None
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ObservatoryReport:
    """The consolidated φ Celestial Observatory picture."""

    readings: list[LaneReading]
    n_lanes: int
    n_valid: int
    n_separable: int
    sky_map_converged: int | None
    sky_map_scored: int | None
    lattice_converged: int | None = None
    lattice_scored: int | None = None
    boundary: str = OBSERVATORY_BOUNDARY
    out_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["readings"] = [r.to_dict() for r in self.readings]
        return d


def _reading(lane: str, domain: str, result: ProxyResult, note: str = "") -> LaneReading:
    d = result.to_dict()
    return LaneReading(
        lane=lane, domain=domain, n_tones=int(d["n_tones"]), valid=bool(d["valid"]),
        structure_present=bool(d["structure_present"]), test_A_p=d["test_A_p"],
        test_B_p=d["test_B_p"], note=note,
    )


def observe(
    *,
    consent: bool = True,
    nulls: int = 300,
    seed: int = 0,
    include_map: bool = True,
) -> ObservatoryReport:
    """Operate every sky/cosmic lane through the unchanged engine and tabulate.

    Lanes whose real data is absent are skipped (recorded as an invalid, note-tagged
    reading) so the observatory runs offline anywhere. Every scored lane is governed
    by ``score_signal``; verdicts are reported exactly as the test returns them.
    """
    from aureon.bio.coherence_scan import score_coherence
    from aureon.bio.cosmic_scan import score_cosmic_catalog, score_space_weather
    from aureon.bio.counter_frequency_scan import score_counter_frequency
    from aureon.bio.harmonic_core_scan import score_harmonic_core
    from aureon.bio.sacred_lattice_scan import lattice_sky_sources, score_lattice
    from aureon.bio.sky_map import (
        analyze_sky_map,
        planet_track_sources_from_de440,
        stellar_sources_from_nasa,
    )
    from aureon.bio.sky_signal_adapter import score_catalog, score_diffuse

    readings: list[LaneReading] = []

    # optical / astronomical line lists
    readings.append(_reading("Hydrogen Balmer", "starlight (emission)",
                             score_catalog("balmer", nulls=nulls, seed=seed)))
    readings.append(_reading("Solar Fraunhofer", "sunlight (absorption)",
                             score_catalog("fraunhofer", nulls=nulls, seed=seed)))
    readings.append(_reading("Airglow", "nightglow (self-emission)",
                             score_catalog("airglow", nulls=nulls, seed=seed)))
    readings.append(_reading("Diffuse night sky", "diffuse background (anchor)",
                             score_diffuse(nulls=nulls, seed=seed)))

    # NASA host-star Wien colour (pooled tones from the sky-map stellar sources)
    stellar = stellar_sources_from_nasa()
    if stellar:
        tones = tuple(sorted(t for s in stellar for t in s.tones_hz))
        sig = HumanSignal(label="observatory:nasa_stellar", frequencies_hz=tones,
                          provenance="NASA host-star Wien colour (pooled)", consent=consent,
                          modality="sky", notes="pooled host-star Wien tones")
        readings.append(_reading("NASA stellar Wien", "host-star colour",
                                score_signal(sig, nulls=nulls, seed=seed),
                                note=f"{len(stellar)} hosts"))
    else:
        readings.append(LaneReading("NASA stellar Wien", "host-star colour", 0, False,
                                   False, None, None, note="cache absent — skipped"))

    # cosmic systems
    readings.append(_reading("Schumann modes", "ionosphere (ELF)",
                             score_cosmic_catalog("schumann", nulls=nulls, seed=seed)))
    readings.append(_reading("Planetary tones", "orbital (Cosmic Octave)",
                             score_cosmic_catalog("planetary", nulls=nulls, seed=seed)))
    readings.append(_reading("Space weather", "solar (Kp/ap/F10.7)",
                             score_space_weather(nulls=nulls, seed=seed)))

    # DE440 coherence spectrum
    if Path("data/de440_gate3_coherence.csv").exists():
        readings.append(_reading("DE440 coherence", "planetary coherence",
                                score_coherence(nulls=nulls, seed=seed)))
    else:
        readings.append(LaneReading("DE440 coherence", "planetary coherence", 0, False,
                                   False, None, None, note="data absent — skipped"))

    # sacred lattice — the repo's OWN sky-mapping systems (Earth harmonic grid)
    readings.append(_reading("Stargate lattice", "Earth grid (ancient sites)",
                             score_lattice("stargate", consent=consent, nulls=nulls, seed=seed)))
    readings.append(_reading("Maeshowe solstice", "chamber (solstice)",
                             score_lattice("maeshowe", consent=consent, nulls=nulls, seed=seed)))
    readings.append(_reading("Metatron geometry", "φ-geometry (13-sphere)",
                             score_lattice("metatron", consent=consent, nulls=nulls, seed=seed)))

    # harmonic core — the repo's OWN HNC harmonic substrate
    readings.append(_reading("Master Formula Λ(t)", "HNC substrate (6 modes)",
                             score_harmonic_core("lambda", consent=consent, nulls=nulls, seed=seed)))
    readings.append(_reading("Celtic Ogham", "tree-tones (φ-scaled)",
                             score_harmonic_core("ogham", consent=consent, nulls=nulls, seed=seed)))
    readings.append(_reading("Ghost Dance", "ancestral (Solfeggio)",
                             score_harmonic_core("ghostdance", consent=consent, nulls=nulls, seed=seed)))

    # counter-frequency — the repo's OWN φ/Fibonacci harmonic canon
    readings.append(_reading("Counter-frequency", "φ/Fibonacci canon",
                             score_counter_frequency("counter", consent=consent, nulls=nulls, seed=seed)))

    # all-sky RA/Dec map summary + the sacred-lattice Earth-grid map
    sky_map_converged: int | None = None
    sky_map_scored: int | None = None
    lattice_converged: int | None = None
    lattice_scored: int | None = None
    if include_map:
        sources = stellar + planet_track_sources_from_de440()
        if sources:
            m = analyze_sky_map(sources, consent=consent, provenance="observatory sky map",
                               nulls=min(nulls, 200), seed=seed)
            sky_map_converged = m.n_converged
            sky_map_scored = sum(1 for c in m.cells if c.n_tones >= 2)
        lat_sources = lattice_sky_sources()
        if lat_sources:
            lm = analyze_sky_map(lat_sources, consent=consent,
                                provenance="observatory sacred-lattice map",
                                nulls=min(nulls, 200), seed=seed)
            lattice_converged = lm.n_converged
            lattice_scored = sum(1 for c in lm.cells if c.n_tones >= 2)

    scored = [r for r in readings if r.valid]
    return ObservatoryReport(
        readings=readings,
        n_lanes=len(readings),
        n_valid=len(scored),
        n_separable=sum(1 for r in readings if r.structure_present),
        sky_map_converged=sky_map_converged,
        sky_map_scored=sky_map_scored,
        lattice_converged=lattice_converged,
        lattice_scored=lattice_scored,
    )


def render_observatory(report: ObservatoryReport, out_path: str | Path) -> ObservatoryReport:
    """Render the consolidated picture: per-lane Test A / Test B p-values + separability."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    scored = [r for r in report.readings if r.valid and r.test_A_p is not None]
    labels = [f"{r.lane}" for r in scored]
    a_p = [max(r.test_A_p, 1e-4) for r in scored]
    b_p = [max(r.test_B_p or 1.0, 1e-4) for r in scored]
    y = np.arange(len(scored))

    fig, ax = plt.subplots(figsize=(10, max(4, 0.5 * len(scored) + 1.5)))
    ax.scatter(a_p, y - 0.15, s=60, color="#e0578a", label="Test A (clustering) p")
    ax.scatter(b_p, y + 0.15, s=60, color="#f0c040", label="Test B (φ alignment) p")
    ax.axvline(engine.ALPHA, color="white", linestyle="--", alpha=0.6,
               label=f"ALPHA = {engine.ALPHA}")
    ax.set_xscale("log")
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel("p-value (log scale) — left of ALPHA = significant")
    ax.set_title("φ Celestial Observatory — every sky lane, one φ engine")
    ax.legend(loc="lower right", fontsize=7)
    ax.grid(True, axis="x", alpha=0.15)
    cap = (f"{report.n_valid}/{report.n_lanes} lanes valid · {report.n_separable} separable · "
           f"sky-map {report.sky_map_converged} converged\n{OBSERVATORY_BOUNDARY}")
    fig.text(0.5, 0.005, cap, ha="center", va="bottom", fontsize=6, wrap=True)
    fig.subplots_adjust(left=0.28, bottom=0.2)
    out = str(out_path)
    fig.savefig(out, dpi=120)
    plt.close(fig)
    from dataclasses import replace
    return replace(report, out_path=out)


def _fmt_p(p: float | None) -> str:
    """p-value cell exactly as ``main()`` prints it (``-`` when the lane is unscored)."""
    return f"{p:.4f}" if p is not None else "-"


def write_observatory_report(
    report: ObservatoryReport,
    out_md: str | Path,
    out_json: str | Path | None = None,
) -> ObservatoryReport:
    """Write the consolidated picture as a durable evidence artifact (markdown [+ JSON]).

    Sibling to :func:`render_observatory`, but text instead of a figure: it *serializes*
    the report — every number copied verbatim from ``report.to_dict()``, nothing
    recomputed, nothing editorialized. The body carries no wall-clock timestamp, so two
    runs at the same ``seed``/``nulls`` produce byte-identical files (mirroring the
    determinism the tests already assert on ``to_dict()``). The honest
    :data:`OBSERVATORY_BOUNDARY` is printed verbatim. Returns the report with
    ``out_path`` set to the markdown path.
    """
    import json

    d = report.to_dict()
    lines: list[str] = []
    lines.append("# φ Celestial Observatory — cross-lane evidence report")
    lines.append("")
    lines.append(
        "Generated by `python -m aureon.bio.celestial_observatory --report <OUT.md>` — every "
        "sky/cosmic lane operated through the one unchanged φ engine. Each verdict below is "
        "exactly what the pre-registered test returned; nothing here is recomputed or hedged."
    )
    lines.append("")
    lines.append(f"> {OBSERVATORY_BOUNDARY}")
    lines.append("")
    lines.append(
        f"**{report.n_valid}/{report.n_lanes} lanes valid** · {report.n_separable} separable · "
        f"sky-map {report.sky_map_converged} converged of {report.sky_map_scored} scored · "
        f"lattice-map {report.lattice_converged} converged of {report.lattice_scored} scored."
    )
    lines.append("")
    lines.append("| lane | domain | tones | valid | separable | Test A p | Test B p | note |")
    lines.append("|---|---|---:|:---:|:---:|---:|---:|---|")
    for r in report.readings:
        lines.append(
            f"| {r.lane} | {r.domain} | {r.n_tones} | {r.valid} | {r.structure_present} | "
            f"{_fmt_p(r.test_A_p)} | {_fmt_p(r.test_B_p)} | {r.note or ''} |"
        )
    lines.append("")
    md = "\n".join(lines) + "\n"

    out_md_path = Path(out_md)
    out_md_path.write_text(md, encoding="utf-8")

    if out_json is not None:
        Path(out_json).write_text(
            json.dumps(d, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    from dataclasses import replace

    return replace(report, out_path=str(out_md_path))


def emit_observatory(
    report: ObservatoryReport, *, bus: Any | None = None, trace: bool = True
) -> dict[str, Any]:
    """Publish the observatory's consolidated picture to cognition; return its dict.

    Closes the loop: mirrors :func:`aureon.bio.human_harmonic_proxy.emit_proxy_result`
    — a ``bio.observatory.run`` Thought on the ThoughtBus + a compact
    ``celestial_observatory`` bus_trace — so the metacognition monitor / Queen can
    sense the whole-sky picture. Bus/trace failures are swallowed; emission never
    crashes a run.
    """
    payload = report.to_dict()
    summary = {
        "n_lanes": report.n_lanes,
        "n_valid": report.n_valid,
        "n_separable": report.n_separable,
        "sky_map_converged": report.sky_map_converged,
        "lattice_converged": report.lattice_converged,
        "lanes": [
            {"lane": r.lane, "valid": r.valid, "structure_present": r.structure_present}
            for r in report.readings
        ],
        "boundary": OBSERVATORY_BOUNDARY,
    }
    try:
        from aureon.core.aureon_thought_bus import Thought, get_thought_bus

        target = bus if bus is not None else get_thought_bus()
        target.publish(
            Thought(source=_SOURCE, topic=OBS_RUN_TOPIC, trace_id=uuid.uuid4().hex,
                    payload=summary)
        )
    except Exception:  # noqa: BLE001 - emission is best-effort, never fatal
        pass

    if trace:
        try:
            from aureon.core.bus_trace import append_trace

            append_trace(OBS_TRACE_NAME, {
                "n_lanes": report.n_lanes,
                "n_valid": report.n_valid,
                "n_separable": report.n_separable,
                "sky_map_converged": report.sky_map_converged,
                "boundary": OBSERVATORY_BOUNDARY,
                "_ts": time.time(),
            })
        except Exception:  # noqa: BLE001 - trace mirror is best-effort
            pass

    return payload


def main(argv: list[str] | None = None) -> int:
    """CLI: operate the φ Celestial Observatory and print the consolidated picture."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Operate every sky/cosmic φ sensor through the one unchanged engine."
    )
    parser.add_argument("--render", metavar="OUT.png", help="render the consolidated picture")
    parser.add_argument("--report", metavar="OUT.md",
                        help="write the consolidated picture as a markdown evidence artifact")
    parser.add_argument("--report-json", metavar="OUT.json",
                        help="also write the full machine-readable JSON record (with --report)")
    parser.add_argument("--nulls", type=int, default=300)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--no-map", action="store_true", help="skip the all-sky map summary")
    parser.add_argument("--emit", action="store_true",
                        help="publish the consolidated picture to cognition (ThoughtBus)")
    args = parser.parse_args(argv)

    report = observe(nulls=args.nulls, seed=args.seed, include_map=not args.no_map)
    print("φ Celestial Observatory — every sky lane, one unchanged φ engine")
    print(f"  boundary: {OBSERVATORY_BOUNDARY}")
    print(f"  {'lane':22s} {'domain':28s} {'tones':>5s} {'valid':>5s} {'sep':>4s} "
          f"{'A_p':>8s} {'B_p':>8s}")
    for r in report.readings:
        ap = f"{r.test_A_p:.4f}" if r.test_A_p is not None else "   -"
        bp = f"{r.test_B_p:.4f}" if r.test_B_p is not None else "   -"
        print(f"  {r.lane:22s} {r.domain:28s} {r.n_tones:5d} {str(r.valid):>5s} "
              f"{str(r.structure_present):>4s} {ap:>8s} {bp:>8s}"
              + (f"   ({r.note})" if r.note else ""))
    print(f"  ── {report.n_valid}/{report.n_lanes} lanes valid · "
          f"{report.n_separable} separable · sky-map {report.sky_map_converged} converged "
          f"of {report.sky_map_scored} scored · lattice-map {report.lattice_converged} "
          f"converged of {report.lattice_scored} scored")

    if args.render:
        result = render_observatory(report, args.render)
        print(f"  rendered: {result.out_path}")
    if args.report:
        result = write_observatory_report(report, args.report, args.report_json)
        print(f"  report written: {result.out_path}"
              + (f" (+ {args.report_json})" if args.report_json else ""))
    if args.emit:
        emit_observatory(report)
        print(f"  emitted:  {OBS_RUN_TOPIC} (cognition)")
    return 0


if __name__ == "__main__":  # pragma: no cover - manual entry point
    raise SystemExit(main())
