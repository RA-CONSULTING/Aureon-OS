#!/usr/bin/env python3
"""Authenticity discriminator — real vs synthetic, and the clone paradox (the immune layer's counterfeit sense).

A real plant and a fake plant made to imitate it can look identical to the eye — but a genuine natural
system carries a specific **harmonic + geometric makeup** an imitation lacks. Given a signal *claimed* to
come from a real system, this module decides whether its structure is genuine or a surface imitation (a
counterfeit "Ditto"), and it detects adversarial "fake-it-till-you-make-it" signals crafted to slip past
our defenses. It composes with the immune layer (b34 sensor · b35 effector · b36 membrane) as the
**counterfeit detector**, reusing the b36 membrane's sealing idea in its *keyed* form.

Two structural axes — the engine's own two independent, null-calibrated kernels (nothing invented):

* **Harmonic** makeup → ``engine.test_A`` (coherence clustering).
* **Geometric** makeup → ``engine.test_B`` (golden-interval / φ alignment).
* ``structure_present ⇔ p_A < α AND p_B < α`` (the engine's own rule).

These separate the surface imitations: a coarse mimic reproduces neither, a signal that clusters at
non-φ centers passes the harmonic axis but fails the geometric one, and a φ-spaced set with no
within-cluster coherence does the reverse — proving the two axes are independent.

The honest crux is the **Ditto / Gucci paradox**: a copy good enough to replicate every *measurable*
feature is authentic by every *measurable* test — structure alone cannot catch a perfect clone. The
resolution is **structure + provenance**: the genuine article also carries a *keyed* origin seal
(HMAC-SHA256 over its canonical tone signature) that a cloner cannot forge without the secret key. So a
perfect structural clone passes both structural tests yet is caught by provenance. ``authentic =
structure_present AND provenance_valid``.

Honest scope (stated, not decorative — enforced by tests)
---------------------------------------------------------
This distinguishes surface imitations by harmonic + geometric makeup and a perfect structural clone by a
keyed provenance seal it cannot forge. It is **synthetic only, NOT a claim about any person, and NOT a
security proof.** The irreducible limit is stated plainly: **a clone that also steals the secret key is
authentic by every test.** The real production key comes from the ``AUREON_AUTHENTICITY_KEY`` environment
variable and is never committed; a fixed, documented **non-secret** test key is the default so self-tests
are deterministic. Pure stdlib (``hmac``/``hashlib``) + numpy + the engine, called unchanged; no network,
no import-time side effects; content-bound + fixed test key → byte-identical artifacts.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import sys
import time
import uuid
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Callable, Final

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import phenolic_fingerprint as engine  # noqa: E402
from aureon.bio.power_analysis import _structured_tones  # noqa: E402

# --- guarded organism link (suppressible; never fatal) — the "I exist" heartbeat ---
try:  # pragma: no cover - environment-dependent, best-effort
    from aureon.core.aureon_baton_link import link_system

    link_system(__name__)
except Exception:  # noqa: BLE001 - the organ must import in any environment
    pass

__all__ = [
    "AUTHENTICITY_BOUNDARY",
    "AUTH_RUN_TOPIC",
    "AUTH_TRACE_NAME",
    "PROVENANCE_KEY_ENV",
    "ClassOutcome",
    "AuthenticityReport",
    "provenance_token",
    "verify_provenance",
    "discriminate",
    "compute_authenticity",
    "write_authenticity_report",
    "emit_authenticity",
    "main",
]

AUTH_RUN_TOPIC: Final[str] = "bio.authenticity.run"
AUTH_TRACE_NAME: Final[str] = "authenticity_discriminator"
_SOURCE: Final[str] = "authenticity_discriminator"

#: Environment variable holding the real provenance secret in production (never committed).
PROVENANCE_KEY_ENV: Final[str] = "AUREON_AUTHENTICITY_KEY"
#: Fixed, documented NON-SECRET default so self-tests/benchmarks are deterministic and byte-identical.
_TEST_KEY: Final[str] = "aureon-authenticity-test-key-not-a-secret"
#: The key a cloner would present — anything other than the genuine key fails verification.
_WRONG_KEY: Final[str] = "cloner-forged-key-lacking-the-secret"

AUTHENTICITY_BOUNDARY: Final[str] = (
    "Synthetic authenticity discriminator: it separates surface imitations from a genuine signal by its "
    "harmonic (Test A clustering) + geometric (Test B phi-alignment) makeup, and catches a perfect "
    "structural clone with a keyed provenance seal the cloner cannot forge - synthetic signals only, NOT "
    "a claim about any person and NOT a security proof; a clone that also steals the secret key is "
    "authentic by every test (the honest limit)."
)

ALPHA: Final[float] = float(engine.ALPHA)
PHI: Final[float] = float(engine.PHI)
_TRIAL_STRIDE: Final[int] = 1_000_003  # keeps per-(seed0, class, trial) seeds disjoint & reproducible
_CLASS_STRIDE: Final[int] = 10_007
_TOKEN_PRECISION: Final[int] = 4  # tone rounding for the canonical provenance signature


def _rng(seed: int, tag: int) -> np.random.Generator:
    """Reproducible generator stream for a (seed, purpose) pair (engine idiom)."""
    return np.random.default_rng([int(seed), int(tag)])


def _default_key() -> str:
    """The active provenance key: the production secret from the environment, else the test key."""
    return os.environ.get(PROVENANCE_KEY_ENV) or _TEST_KEY


# ── provenance seal — the keyed complement to b36's keyless integrity envelope ────────────────────


def _canonical(tones: np.ndarray) -> str:
    """Deterministic canonical signature of a tone set — the HMAC input (rounded, sorted, tight)."""
    arr = np.asarray(tones, dtype=float).ravel()
    return ",".join(f"{round(float(x), _TOKEN_PRECISION):.{_TOKEN_PRECISION}f}" for x in np.sort(arr))


def provenance_token(tones: np.ndarray, *, key: str) -> str:
    """Issue a keyed origin seal over the canonical tone signature (HMAC-SHA256 hex)."""
    return hmac.new(key.encode("utf-8"), _canonical(tones).encode("utf-8"), hashlib.sha256).hexdigest()


def verify_provenance(tones: np.ndarray, token: str | None, *, key: str) -> bool:
    """True iff ``token`` is the genuine seal for ``tones`` under ``key`` (missing/forged → False)."""
    if not token:
        return False
    expected = provenance_token(tones, key=key)
    return hmac.compare_digest(expected, str(token))


def discriminate(
    tones: np.ndarray,
    *,
    token: str | None = None,
    key: str | None = None,
    nulls: int = 200,
    seed: int = 0,
) -> dict[str, Any]:
    """Classify one signal by structure (harmonic + geometric) and provenance.

    Returns the engine's two p-values, the per-axis structural verdicts and their conjunction, whether
    the provenance seal verifies under ``key``, and the final ``authentic = structure_present AND
    provenance_valid``. A perfect structural clone (``structure_present`` True) with a forged/absent
    token is ``authentic`` False — the resolved Ditto/Gucci paradox.
    """
    active_key = key if key is not None else _default_key()
    arr = np.asarray(tones, dtype=float)
    if arr.size < 2:
        p_a = p_b = 1.0
    else:
        p_a = float(engine.test_A(arr, nulls=nulls, rng=_rng(seed, 1)))
        p_b = float(engine.test_B(arr, nulls=nulls, rng=_rng(seed, 2)))
    harmonic_present = bool(p_a < ALPHA)
    geometric_present = bool(p_b < ALPHA)
    structure_present = harmonic_present and geometric_present
    provenance_valid = verify_provenance(arr, token, key=active_key)
    return {
        "p_A": p_a,
        "p_B": p_b,
        "harmonic_present": harmonic_present,
        "geometric_present": geometric_present,
        "structure_present": structure_present,
        "provenance_valid": provenance_valid,
        "authentic": structure_present and provenance_valid,
    }


# ── synthetic signal classes (deterministic; each presents provenance as it would) ────────────────


def _authentic_tones(seed: int, jitter_hz: float) -> np.ndarray:
    """Genuine makeup: two φ-apart tight clusters — clustered AND golden-ratio spaced (passes both)."""
    return _structured_tones(jitter_hz, seed)


def _coarse_mimic_tones(seed: int, jitter_hz: float) -> np.ndarray:
    """A surface copy: envelope-matched uniform in-band draw — neither clustered nor φ-spaced."""
    lo, hi = engine.TARGET_BAND_HZ
    return np.sort(_rng(seed, 3).uniform(float(lo), float(hi), 12))


def _harmonic_only_tones(seed: int, jitter_hz: float) -> np.ndarray:
    """Clusters at NON-φ (arithmetic) centers: tight coherence (passes Test A), off-lattice (fails Test B)."""
    centers = np.array([1100.0, 1360.0, 1620.0, 1880.0])  # equal +260 Hz spacing → ratios off the φ lattice
    offsets = np.array([-4.0, 0.0, 4.0])
    tones = (centers[:, None] + offsets[None, :]).ravel()
    if jitter_hz > 0:
        tones = tones + _rng(seed, 7).normal(0.0, float(jitter_hz), size=tones.shape)
    return np.sort(tones)


def _geometric_only_tones(seed: int, jitter_hz: float) -> np.ndarray:
    """φ-spaced singletons, no within-cluster coherence: golden ratios (passes Test B), unclustered (fails Test A)."""
    tones = 1000.0 * (PHI ** np.arange(4))  # exact φ powers, far apart → no coherent pairs
    if jitter_hz > 0:
        tones = tones + _rng(seed, 7).normal(0.0, float(jitter_hz), size=tones.shape)
    return np.sort(tones)


@dataclass(frozen=True)
class _ClassSpec:
    name: str
    description: str
    index: int
    generate: Callable[[int, float], np.ndarray]
    is_surface_imitation: bool
    is_clone: bool
    forged: bool  # True → presents a token issued under the WRONG key (a cloner cannot forge the seal)


_CLASS_SPECS: Final[tuple[_ClassSpec, ...]] = (
    _ClassSpec("authentic", "genuine φ-clustered makeup with a valid keyed provenance seal",
               0, _authentic_tones, False, False, forged=False),
    _ClassSpec("coarse_mimic", "envelope-matched uniform draw — reproduces neither axis; forged seal",
               1, _coarse_mimic_tones, True, False, forged=True),
    _ClassSpec("harmonic_only", "clusters at non-φ centers — passes harmonic, fails geometric; forged seal",
               2, _harmonic_only_tones, True, False, forged=True),
    _ClassSpec("geometric_only", "φ-spaced singletons — passes geometric, fails harmonic; forged seal",
               3, _geometric_only_tones, True, False, forged=True),
    _ClassSpec("perfect_clone", "an exact structural copy of the genuine signal but a forged seal — the paradox",
               4, _authentic_tones, False, True, forged=True),
)


def _class_token(spec: _ClassSpec, tones: np.ndarray, key: str) -> str:
    """The provenance token a class *presents*: the genuine seal for the authentic class, a forged one else."""
    return provenance_token(tones, key=_WRONG_KEY if spec.forged else key)


@dataclass(frozen=True)
class ClassOutcome:
    """Structural / provenance / authentic detection rates for one synthetic signal class."""

    name: str
    description: str
    structural_rate: float
    provenance_rate: float
    authentic_rate: float
    is_surface_imitation: bool
    is_clone: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AuthenticityReport:
    """The consolidated real-vs-synthetic discrimination + clone-paradox audit."""

    classes: list[ClassOutcome]
    n_classes: int
    trials: int
    nulls: int
    alpha: float
    jitter_hz: float
    authentic_rate: float
    max_surface_imitation_rate: float
    clone_structural_rate: float
    clone_authentic_rate: float
    clone_blocked_by_provenance: bool
    separation: float
    boundary: str = AUTHENTICITY_BOUNDARY
    out_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["classes"] = [c.to_dict() for c in self.classes]
        return d


def compute_authenticity(
    *,
    trials: int = 120,
    nulls: int = 150,
    seed0: int = 0,
    jitter_hz: float = 2.0,
    tolerance: float = 0.05,
) -> AuthenticityReport:
    """Measure how each synthetic class is classified, averaged over ``trials`` reproducible draws.

    For every class the audit reports the mean rate at which it is judged structurally present (both
    engine axes fire), provenance-valid (the keyed seal verifies), and finally authentic (both). The
    genuine class should be authentic at a high rate; the three surface imitations should be authentic
    at a low rate (each failing the axis it cannot reproduce); the perfect clone should pass the
    structural tests yet be blocked by provenance (``clone_blocked_by_provenance``). ``separation`` is
    the authentic-rate margin between the genuine class and the strongest surface imitation.
    """
    active_key = _default_key()
    outcomes: list[ClassOutcome] = []
    for spec in _CLASS_SPECS:
        struct_hits = prov_hits = auth_hits = 0
        for t in range(trials):
            seed = seed0 * _TRIAL_STRIDE + spec.index * _CLASS_STRIDE + t
            tones = spec.generate(seed, jitter_hz)
            token = _class_token(spec, tones, active_key)
            r = discriminate(tones, token=token, key=active_key, nulls=nulls, seed=seed)
            struct_hits += int(r["structure_present"])
            prov_hits += int(r["provenance_valid"])
            auth_hits += int(r["authentic"])
        outcomes.append(ClassOutcome(
            name=spec.name,
            description=spec.description,
            structural_rate=struct_hits / trials,
            provenance_rate=prov_hits / trials,
            authentic_rate=auth_hits / trials,
            is_surface_imitation=spec.is_surface_imitation,
            is_clone=spec.is_clone,
        ))

    by_name = {o.name: o for o in outcomes}
    authentic_rate = by_name["authentic"].authentic_rate
    surface = [o for o in outcomes if o.is_surface_imitation]
    max_surface = max((o.authentic_rate for o in surface), default=0.0)
    clone = by_name["perfect_clone"]
    clone_blocked = clone.structural_rate >= 0.5 and clone.authentic_rate <= tolerance

    return AuthenticityReport(
        classes=outcomes,
        n_classes=len(outcomes),
        trials=trials,
        nulls=nulls,
        alpha=ALPHA,
        jitter_hz=jitter_hz,
        authentic_rate=authentic_rate,
        max_surface_imitation_rate=max_surface,
        clone_structural_rate=clone.structural_rate,
        clone_authentic_rate=clone.authentic_rate,
        clone_blocked_by_provenance=clone_blocked,
        separation=authentic_rate - max_surface,
    )


def write_authenticity_report(
    report: AuthenticityReport,
    out_md: str | Path,
    out_json: str | Path | None = None,
) -> AuthenticityReport:
    """Write the authenticity audit as a durable evidence artifact (markdown [+ JSON])."""
    import json

    d = report.to_dict()
    lines: list[str] = []
    lines.append("# Authenticity — real vs synthetic, and the clone paradox")
    lines.append("")
    lines.append(
        "Generated by `python -m aureon.bio.authenticity_discriminator --report <OUT.md>` — the rate at "
        "which each synthetic signal class is judged structurally present (the engine's own Test A "
        "harmonic + Test B geometric axes), provenance-valid (a keyed HMAC seal), and finally authentic "
        "(both). Structure separates surface imitations; the keyed seal catches a perfect structural clone."
    )
    lines.append("")
    lines.append(f"> {AUTHENTICITY_BOUNDARY}")
    lines.append("")
    lines.append(
        f"**Genuine authentic rate {report.authentic_rate:.3f}** vs **strongest surface imitation "
        f"{report.max_surface_imitation_rate:.3f}** (separation {report.separation:.3f}) over "
        f"**{report.trials} trials** per class, {report.nulls} nulls, α = {report.alpha:g}. The perfect "
        f"clone passes structure at {report.clone_structural_rate:.3f} but is authentic at only "
        f"{report.clone_authentic_rate:.3f} — **blocked by provenance: "
        f"{report.clone_blocked_by_provenance}** (the resolved Ditto/Gucci paradox). Honest limit: a "
        f"clone that also holds the secret key is authentic by every test."
    )
    lines.append("")
    lines.append("| class | structural | provenance | authentic | kind |")
    lines.append("|:---|---:|---:|---:|:---|")
    for c in report.classes:
        kind = "clone" if c.is_clone else ("surface imitation" if c.is_surface_imitation else "genuine")
        lines.append(f"| {c.name} | {c.structural_rate:.3f} | {c.provenance_rate:.3f} | "
                     f"{c.authentic_rate:.3f} | {kind} |")
    lines.append("")
    md = "\n".join(lines) + "\n"

    out_md_path = Path(out_md)
    out_md_path.write_text(md, encoding="utf-8")
    if out_json is not None:
        Path(out_json).write_text(json.dumps(d, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return replace(report, out_path=str(out_md_path))


def emit_authenticity(
    report: AuthenticityReport, *, bus: Any | None = None, trace: bool = True
) -> dict[str, Any]:
    """Publish the authenticity audit to cognition; return its dict. Best-effort, never fatal."""
    payload = report.to_dict()
    summary = {
        "n_classes": report.n_classes,
        "trials": report.trials,
        "authentic_rate": report.authentic_rate,
        "max_surface_imitation_rate": report.max_surface_imitation_rate,
        "clone_structural_rate": report.clone_structural_rate,
        "clone_authentic_rate": report.clone_authentic_rate,
        "clone_blocked_by_provenance": report.clone_blocked_by_provenance,
        "separation": report.separation,
        "boundary": AUTHENTICITY_BOUNDARY,
    }
    try:
        from aureon.core.aureon_thought_bus import Thought, get_thought_bus

        target = bus if bus is not None else get_thought_bus()
        target.publish(
            Thought(source=_SOURCE, topic=AUTH_RUN_TOPIC, trace_id=uuid.uuid4().hex, payload=summary)
        )
    except Exception:  # noqa: BLE001 - emission is best-effort, never fatal
        pass

    if trace:
        try:
            from aureon.core.bus_trace import append_trace

            append_trace(AUTH_TRACE_NAME, {
                "authentic_rate": report.authentic_rate,
                "max_surface_imitation_rate": report.max_surface_imitation_rate,
                "clone_blocked_by_provenance": report.clone_blocked_by_provenance,
                "separation": report.separation,
                "n_classes": report.n_classes,
                "boundary": AUTHENTICITY_BOUNDARY,
                "_ts": time.time(),
            })
        except Exception:  # noqa: BLE001 - trace mirror is best-effort
            pass

    return payload


def main(argv: list[str] | None = None) -> int:
    """CLI: run the authenticity discrimination audit and print / write the table."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Discriminate real vs synthetic by harmonic + geometric makeup, and catch a perfect "
                    "structural clone by a keyed provenance seal (engine tests, unchanged)."
    )
    parser.add_argument("--report", metavar="OUT.md", help="write the table as a markdown evidence artifact")
    parser.add_argument("--report-json", metavar="OUT.json", help="also write the JSON record")
    parser.add_argument("--trials", type=int, default=120)
    parser.add_argument("--nulls", type=int, default=150)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--discriminate", metavar="HZ,HZ,...",
                        help="classify one comma-separated tone set (unauthenticated: no provenance token)")
    parser.add_argument("--self-test", action="store_true",
                        help="assert genuine detected, surface imitations blocked, clone blocked by "
                             "provenance, separation > 0 (exit non-zero otherwise)")
    args = parser.parse_args(argv)

    if args.discriminate:
        tones = np.array([float(x) for x in args.discriminate.split(",") if x.strip()])
        r = discriminate(tones, nulls=args.nulls, seed=args.seed)
        print("Discriminate (unauthenticated — no provenance token presented):")
        for k, v in r.items():
            print(f"  {k:20s} {v}")
        return 0

    report = compute_authenticity(trials=args.trials, nulls=args.nulls, seed0=args.seed)

    print("Authenticity — real vs synthetic, and the clone paradox (engine tests, unchanged)")
    print(f"  boundary: {AUTHENTICITY_BOUNDARY}")
    print(f"  {report.trials} trials/class · {report.nulls} nulls · α={report.alpha:g} · "
          f"jitter {report.jitter_hz:g} Hz")
    print("  class            structural  provenance  authentic  kind")
    for c in report.classes:
        kind = "clone" if c.is_clone else ("surface" if c.is_surface_imitation else "genuine")
        print(f"  {c.name:<15s}  {c.structural_rate:9.3f}  {c.provenance_rate:10.3f}  "
              f"{c.authentic_rate:9.3f}  {kind}")
    print(f"  genuine {report.authentic_rate:.3f} vs strongest imitation "
          f"{report.max_surface_imitation_rate:.3f} (separation {report.separation:.3f}); "
          f"clone structural {report.clone_structural_rate:.3f} authentic "
          f"{report.clone_authentic_rate:.3f} → blocked by provenance {report.clone_blocked_by_provenance}")

    if args.report:
        rendered = write_authenticity_report(report, args.report, args.report_json)
        print(f"  report written: {rendered.out_path}")

    if args.self_test:
        ok = (
            report.authentic_rate >= 0.8
            and report.max_surface_imitation_rate <= 0.2
            and report.clone_blocked_by_provenance
            and report.separation > 0.0
        )
        return 0 if ok else 1
    return 0


if __name__ == "__main__":  # pragma: no cover - manual entry point
    raise SystemExit(main())
