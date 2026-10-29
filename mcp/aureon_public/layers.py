"""Read-only and one-step tools for organism layers that do not order or write state/.

Dispositions follow the scoping table. A package with no safe callable stays
catalog-only. Blocked trading imports are not called.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from aureon_public import paths
from aureon_public.guard_loader import apply_space_guard
from aureon_public.quiet import quiet
from aureon_public.text import AURIS_FOUR, HOLD_LINE
from aureon_public.tools import _dumps, _finite

apply_space_guard()

# kind: public tool name, catalog (named, not called), or operator (not on this server).
PACKAGES: tuple[dict[str, str], ...] = (
    {"package": "accounting", "kind": "operator", "reason": "Inferred private. Not opened. No live orders."},
    {"package": "alignment", "kind": "catalog", "reason": "Not opened. No safe zero-write callable was wrapped."},
    {"package": "analytics", "kind": "catalog", "reason": "Lighthouse seat module was not given a separate tool. QGITA lighthouse math is wrapped on wisdom."},
    {"package": "appliance", "kind": "catalog", "reason": "Not opened. No safe callable wrapped."},
    {"package": "approval", "kind": "catalog", "reason": "Not opened. No safe callable wrapped."},
    {"package": "atn", "kind": "catalog", "reason": "Not opened. No safe callable wrapped."},
    {"package": "autonomous", "kind": "operator", "reason": "Self-coding and launchers. Operator server only. No live orders."},
    {"package": "bio", "kind": "membrane_screen", "reason": "screen_ingress is read-only containment. The Flask transport is not re-exported."},
    {"package": "bots", "kind": "operator", "reason": "Blocked by guard.py. Operator refusal only. No live orders."},
    {"package": "bots_intelligence", "kind": "operator", "reason": "Blocked by guard.py. Operator refusal only. No live orders."},
    {"package": "bridges", "kind": "operator", "reason": "Blocked by guard.py. Operator refusal only. No live orders."},
    {"package": "briefing", "kind": "catalog", "reason": "Not opened. No safe callable wrapped."},
    {"package": "code_architect", "kind": "operator", "reason": "Self-coding. Operator server only. No repo writes from this server."},
    {"package": "cognition", "kind": "catalog", "reason": "Not opened. No safe callable wrapped."},
    {"package": "command_centers", "kind": "catalog", "reason": "Not opened. No safe callable wrapped."},
    {"package": "connectors", "kind": "operator", "reason": "Inferred private. Not opened. No live orders."},
    {"package": "conversion", "kind": "catalog", "reason": "Not opened. No safe callable wrapped."},
    {"package": "core", "kind": "public", "reason": "Canonical field, LambdaEngine, circulation catalog, and the repository-layer hold."},
    {"package": "data_feeds", "kind": "catalog", "reason": "Feeds are key-adjacent. Not called."},
    {"package": "decoders", "kind": "catalog", "reason": "Not opened. No safe callable wrapped."},
    {"package": "evaluation", "kind": "evidence_predict_next", "reason": "predict_next only. evaluate_organism is not called."},
    {"package": "exchanges", "kind": "operator", "reason": "Blocked by guard.py. Operator refusal only. No live orders."},
    {"package": "gates", "kind": "catalog", "reason": "Signature pass was not done. Not called."},
    {"package": "generated", "kind": "catalog", "reason": "Generated trees are not exposed."},
    {"package": "governance", "kind": "catalog", "reason": "Seat resolvers were not started."},
    {"package": "grants", "kind": "catalog", "reason": "Out of the public tool surface."},
    {"package": "harmonic", "kind": "public", "reason": "HarmonicRealityField plus substrate, echo, observer, potential, and projection. HFT order types are not called."},
    {"package": "identity", "kind": "catalog", "reason": "Not opened. No safe callable wrapped."},
    {"package": "inhouse_ai", "kind": "catalog", "reason": "The operator tool registry is not re-exported."},
    {"package": "integrations", "kind": "catalog", "reason": "External systems. Not called."},
    {"package": "intelligence", "kind": "catalog", "reason": "GlobalMarketOrganism is not a stateless API. Not called."},
    {"package": "launch", "kind": "operator", "reason": "Process start. Operator server only. This server does not launch it."},
    {"package": "miner", "kind": "catalog", "reason": "Not opened. No safe callable wrapped."},
    {"package": "monitors", "kind": "catalog", "reason": "Not opened. No safe callable wrapped."},
    {"package": "observability", "kind": "catalog", "reason": "Not opened. No safe callable wrapped."},
    {"package": "observer", "kind": "catalog", "reason": "HarmonicObserver attaches to the live daemon. Not called."},
    {"package": "operator", "kind": "operator", "reason": "Flask app and the existing /mcp routes. Not mounted here."},
    {"package": "organism", "kind": "repository_layers_hold", "reason": "compose_repository_layers on an empty root. No network transport."},
    {"package": "plumber", "kind": "catalog", "reason": "Crypto extras. Not called."},
    {"package": "portfolio", "kind": "operator", "reason": "Inferred private. Not opened. No live orders."},
    {"package": "portals", "kind": "catalog", "reason": "Not opened. No safe callable wrapped."},
    {"package": "queen", "kind": "catalog", "reason": "QueenLayer init is not called. Auris node and evaluator calls live on utils."},
    {"package": "s51", "kind": "catalog", "reason": "Not opened. No safe callable wrapped."},
    {"package": "saas", "kind": "operator", "reason": "Billing. Operator server only. No charges."},
    {"package": "scanners", "kind": "operator", "reason": "Blocked by guard.py. Operator refusal only. No live orders."},
    {"package": "search", "kind": "catalog", "reason": "Not repo_search. Not called."},
    {"package": "simulation", "kind": "catalog", "reason": "Long-running. Not called."},
    {"package": "strategies", "kind": "operator", "reason": "Trading-adjacent. Operator refusal only. No live orders."},
    {"package": "swarm", "kind": "catalog", "reason": "Council seat is named in organism_catalog. The council is not started."},
    {"package": "swarm_motion", "kind": "catalog", "reason": "Not opened. No safe callable wrapped."},
    {"package": "trading", "kind": "operator", "reason": "Blocked by guard.py. Operator refusal only. No live orders."},
    {"package": "utils", "kind": "public", "reason": "Nine nodes and the coherence evaluator. QueenHiveMind.__init__ is not called."},
    {"package": "vault", "kind": "catalog", "reason": "State files. Not opened and not written."},
    {"package": "wisdom", "kind": "public", "reason": "QGITAMarketAnalyzer, FTCPDetector, and LighthouseModel metric calls. Signals are dropped."},
)

HOLDS = {
    "trade_readiness": "HOLD",
    "auris_to_lambda": "HOLD",
    "qgita_detection_rate": "HOLD",
    "qgita_false_alarm_rate": "HOLD",
    "schumann_f0": "null. HOLD",
    "human_eval": "not run. HOLD",
}


def _package_rows() -> list[dict[str, str]]:
    root = paths.repo_root() / "aureon"
    rows = []
    for row in PACKAGES:
        present = (root / row["package"]).is_dir() or row["package"] == "unified_margin_trader"
        rows.append({**row, "present": "yes" if present else "no", "holds": HOLD_LINE})
    return rows


@quiet
def package_dispositions(package: str | None = None) -> str:
    """Disposition of each aureon package. Label: inferred from the scoping table, except where a tool below calls a real function.

    Blocked packages are operator-only. This tool does not import them.

    Args:
        package: Optional package name. Omitted returns the full table. Label: inferred.
    """

    rows = _package_rows()
    if package:
        chosen = [row for row in rows if row["package"] == package]
        if not chosen:
            return _dumps(
                {
                    "holds": HOLDS,
                    "label": "inferred",
                    "provenance": "inferred",
                    "reason": "Unknown package.",
                    "status": "unavailable",
                }
            )
        rows = chosen
    return _dumps(
        {
            "holds": HOLDS,
            "label": "inferred. Package dispositions. Not a measurement.",
            "packages": rows,
            "provenance": "inferred",
            "status": "inferred",
            "which_auris": AURIS_FOUR,
        }
    )


@quiet
def hnc_substrate_eval(t: float = 0.0) -> str:
    """One HarmonicSubstrate.evaluate call. Provenance: inferred. This is not HarmonicRealityField.step.

    The substrate equation is the class docstring. No formula was added. Trade readiness: HOLD.

    Args:
        t: Time passed to evaluate. Label: cited, HarmonicSubstrate.evaluate.
    """

    number = _finite(t)
    if number is None:
        return _dumps({"provenance": "cited", "reason": "t is missing", "status": "unavailable"})
    from aureon.harmonic.aureon_harmonic_reality import HarmonicSubstrate

    substrate = HarmonicSubstrate()
    return _dumps(
        {
            "label": "inferred. One HarmonicSubstrate.evaluate call.",
            "provenance": "inferred",
            "status": "inferred",
            "t": number,
            "value": float(substrate.evaluate(number)),
        }
    )


@quiet
def hnc_echo_eval(current_lambda: float = 0.0) -> str:
    """One CausalEcho.evaluate call on a new echo. Provenance: inferred.

    The buffer starts at zeros in CausalEcho.__init__. This is that function, not a new formula. Trade readiness: HOLD.

    Args:
        current_lambda: Value passed to evaluate. Label: cited, CausalEcho.evaluate.
    """

    number = _finite(current_lambda)
    if number is None:
        return _dumps({"provenance": "cited", "reason": "current_lambda is missing", "status": "unavailable"})
    from aureon.harmonic.aureon_harmonic_reality import CausalEcho

    echo = CausalEcho()
    return _dumps(
        {
            "label": "inferred. One CausalEcho.evaluate call on a new instance.",
            "provenance": "inferred",
            "status": "inferred",
            "value": float(echo.evaluate(number)),
        }
    )


@quiet
def hnc_observer_eval(current_lambda: float = 0.0) -> str:
    """One ObserverNode.evaluate call on a new observer. Provenance: inferred.

    Args:
        current_lambda: Value passed to evaluate. Label: cited, ObserverNode.evaluate.
    """

    number = _finite(current_lambda)
    if number is None:
        return _dumps({"provenance": "cited", "reason": "current_lambda is missing", "status": "unavailable"})
    from aureon.harmonic.aureon_harmonic_reality import ObserverNode

    observer = ObserverNode()
    return _dumps(
        {
            "label": "inferred. One ObserverNode.evaluate call on a new instance.",
            "provenance": "inferred",
            "status": "inferred",
            "value": float(observer.evaluate(number)),
        }
    )


@quiet
def hnc_potential_eval(lambda_val: float = 0.0) -> str:
    """One UnifiedPotential.evaluate call. Provenance: inferred.

    The potential string is the class docstring. No formula was added. Trade readiness: HOLD.

    Args:
        lambda_val: Value passed to evaluate. Label: cited, UnifiedPotential.evaluate.
    """

    number = _finite(lambda_val)
    if number is None:
        return _dumps({"provenance": "cited", "reason": "lambda_val is missing", "status": "unavailable"})
    from aureon.harmonic.aureon_harmonic_reality import UnifiedPotential

    potential = UnifiedPotential()
    return _dumps(
        {
            "label": "inferred. One UnifiedPotential.evaluate call.",
            "provenance": "inferred",
            "status": "inferred",
            "value": float(potential.evaluate(number)),
        }
    )


@quiet
def hnc_translate_project(psi_5d: float = 1.0, phi: float = 0.0, delta_phi: float = 0.0, f_value: float = 1.0) -> str:
    """One TranslationMap.project_to_3d call with observed_residual left unset. Provenance: inferred.

    Noise is the method's own result when no residual is supplied. Label: cited, TranslationMap.project_to_3d.

    Args:
        psi_5d: High-dimensional state. Label: cited.
        phi: Extra angle. Label: cited.
        delta_phi: Phase difference. Label: cited.
        f_value: Brane frequency passed as F. Label: cited.
    """

    numbers = {
        "psi_5d": _finite(psi_5d),
        "phi": _finite(phi),
        "delta_phi": _finite(delta_phi),
        "f_value": _finite(f_value),
    }
    if any(value is None for value in numbers.values()):
        return _dumps({"provenance": "cited", "reason": "A projection input is missing", "status": "unavailable"})
    from aureon.harmonic.aureon_harmonic_reality import TranslationMap

    mapped = TranslationMap()
    projected, noise = mapped.project_to_3d(
        psi_5d=float(numbers["psi_5d"]),
        phi=float(numbers["phi"]),
        delta_phi=float(numbers["delta_phi"]),
        F=float(numbers["f_value"]),
    )
    return _dumps(
        {
            "label": "inferred. project_to_3d with no observed residual.",
            "noise": float(noise),
            "projected": float(projected),
            "provenance": "inferred",
            "status": "inferred",
        }
    )


@quiet
def qgita_ftcp_detect(values: list[float] | None = None) -> str:
    """FTCPDetector.detect_ftcps on a caller series or a short default. Provenance: inferred.

    Detection rate: HOLD. False-alarm rate: HOLD. This is not QGITAMarketAnalyzer.signals.

    Args:
        values: Optional series of at least three numbers. Omitted uses 0,1,1,2,3,5,8. Label: inferred for the call. The detector is cited.
    """

    series = [0.0, 1.0, 1.0, 2.0, 3.0, 5.0, 8.0] if values is None else []
    if values is not None:
        for item in values:
            number = _finite(item)
            if number is None:
                return _dumps(
                    {
                        "detection_rate": "HOLD",
                        "false_alarm_rate": "HOLD",
                        "provenance": "cited",
                        "reason": "A value is missing",
                        "status": "unavailable",
                    }
                )
            series.append(number)
    if len(series) < 3:
        return _dumps(
            {
                "detection_rate": "HOLD",
                "false_alarm_rate": "HOLD",
                "provenance": "cited",
                "reason": "At least three values are required",
                "status": "unavailable",
            }
        )
    import numpy as np

    from aureon.wisdom.aureon_qgita_framework import FTCPDetector

    detector = FTCPDetector()
    times = np.arange(len(series), dtype=float)
    found = detector.detect_ftcps(times, np.asarray(series, dtype=float))
    return _dumps(
        {
            "detection_rate": "HOLD",
            "false_alarm_rate": "HOLD",
            "ftcp_count": len(found),
            "label": "inferred. FTCPDetector.detect_ftcps. Not a detection rate.",
            "provenance": "inferred",
            "status": "inferred",
        }
    )


@quiet
def qgita_lighthouse_coherence(values: list[float] | None = None) -> str:
    """LighthouseModel.compute_linear_coherence on one series. Provenance: inferred.

    Detection rate: HOLD. False-alarm rate: HOLD. validate_ftcp is not called. Signals are not returned.

    Args:
        values: Optional series. Omitted uses 1,1,1,1,1. Label: inferred for the call. The method is cited.
    """

    series = [1.0, 1.0, 1.0, 1.0, 1.0] if values is None else []
    if values is not None:
        for item in values:
            number = _finite(item)
            if number is None:
                return _dumps(
                    {
                        "detection_rate": "HOLD",
                        "false_alarm_rate": "HOLD",
                        "provenance": "cited",
                        "reason": "A value is missing",
                        "status": "unavailable",
                    }
                )
            series.append(number)
    import numpy as np

    from aureon.wisdom.aureon_qgita_framework import LighthouseModel

    model = LighthouseModel()
    signal = np.asarray(series, dtype=float)
    return _dumps(
        {
            "c_linear": float(model.compute_linear_coherence(signal)),
            "detection_rate": "HOLD",
            "false_alarm_rate": "HOLD",
            "label": "inferred. LighthouseModel.compute_linear_coherence.",
            "provenance": "inferred",
            "status": "inferred",
        }
    )


@quiet
def membrane_screen(text: str = "") -> str:
    """screen_ingress on caller text. Provenance: cited. This does not dispatch a tool and does not trade.

    Args:
        text: Inbound text screened as data. Label: cited, aureon/bio/mcp_membrane.py screen_ingress.
    """

    from dataclasses import asdict

    missing = _load_phenolic_fingerprint()
    if missing:
        return _dumps(
            {
                "label": "cited-unverified. phenolic_fingerprint was not loaded, so screen_ingress did not run.",
                "provenance": "cited-unverified",
                "reason": missing,
                "status": "unavailable",
            }
        )
    try:
        from aureon.bio.mcp_membrane import screen_ingress
    except Exception as exc:
        return _dumps(
            {
                "label": "cited-unverified. screen_ingress did not import in this process.",
                "provenance": "cited-unverified",
                "reason": f"{type(exc).__name__}: {exc}"[:240],
                "status": "unavailable",
            }
        )

    verdict = screen_ingress(str(text), source="aureon-public")
    body = asdict(verdict)
    body["label"] = (
        "cited. screen_ingress. phenolic_fingerprint loaded from checkout "
        "after the blob check for pin a00f744d. Not an order."
    )
    body["provenance"] = "cited"
    body["status"] = "cited"
    return _dumps(body)


@quiet
def repository_layers_hold() -> str:
    """compose_repository_layers on an empty directory. Provenance: cited.

    No field or market transport is passed, and the empty root has no sibling checkouts, so this does not open a network socket from those call sites. may_act stays false.

    Args:
        none: This tool takes no inputs. Label: cited, aureon/organism/repository_layers.py compose_repository_layers.
    """

    import tempfile

    from aureon.organism.repository_layers import compose_repository_layers

    empty = Path(tempfile.mkdtemp(prefix="aureon-public-layers-"))
    try:
        report = compose_repository_layers(repos_root=empty)
    finally:
        empty.rmdir()
    report["label"] = "cited. Empty-root hold join. Not a network observation."
    report["provenance"] = "cited"
    return _dumps(report)


@quiet
def evidence_predict_next(values: list[float] | None = None) -> str:
    """evaluate.organism_proof.predict_next. Provenance: inferred.

    This does not call evaluate_organism. HumanEval: not run. HOLD.

    Args:
        values: Optional numbers. Omitted uses 1,2,3. Label: inferred for the call. The function is cited.
    """

    series: list[float] = []
    raw = [1.0, 2.0, 3.0] if values is None else values
    for item in raw:
        number = _finite(item)
        if number is None:
            return _dumps(
                {
                    "human_eval": "not run. HOLD",
                    "provenance": "cited",
                    "reason": "A value is missing",
                    "status": "unavailable",
                }
            )
        series.append(number)
    from aureon.evaluation.organism_proof import predict_next

    predicted = predict_next(series)
    return _dumps(
        {
            "human_eval": "not run. HOLD",
            "label": "inferred. predict_next. evaluate_organism was not called.",
            "predicted": predicted,
            "provenance": "inferred",
            "status": "inferred",
        }
    )


@quiet
def source_names(package: str) -> str:
    """Top-level class and function names parsed from a package's Python files. Provenance: cited.

    This reads source text with ast. It does not import the package and does not call those functions. Blocked packages are refused.

    Args:
        package: aureon package name, or unified_margin_trader. Label: cited, the file names on disk.
    """

    blocked = {
        "exchanges",
        "trading",
        "bots",
        "bots_intelligence",
        "bridges",
        "scanners",
    }
    if package in blocked or package == "unified_margin_trader":
        return _dumps(
            {
                "label": "cited. guard.py refuses these imports. Names are not loaded.",
                "package": package,
                "provenance": "cited",
                "status": "unavailable",
            }
        )
    root = paths.repo_root() / "aureon" / package
    if not root.is_dir():
        return _dumps(
            {
                "provenance": "cited",
                "reason": "Package directory is missing",
                "status": "unavailable",
            }
        )
    names: list[dict[str, str]] = []
    for path in sorted(root.glob("*.py")):
        if path.name == "__init__.py":
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.append({"file": path.name, "kind": type(node).__name__, "name": node.name})
                if len(names) >= 40:
                    break
        if len(names) >= 40:
            break
    return _dumps(
        {
            "label": "cited. ast names only. Functions were not called.",
            "names": names,
            "package": package,
            "provenance": "cited",
            "status": "cited",
        }
    )


def _load_phenolic_fingerprint(root: Path | None = None) -> str | None:
    """Register the checkout's phenolic_fingerprint without putting the repo root on sys.path.

    The file is executed only when its git blob is the blob at pin a00f744d.
    A different checkout copy is refused and is not loaded.
    """

    import importlib.util
    import sys

    from aureon_public.pin_blob import (
        PHENOLIC_MISMATCH,
        PINNED_PHENOLIC_BLOB,
        pinned_blob_refusal,
    )

    base = paths.repo_root() if root is None else root
    path = base / "phenolic_fingerprint.py"
    refusal = pinned_blob_refusal(path, PINNED_PHENOLIC_BLOB, PHENOLIC_MISMATCH)
    if refusal:
        return refusal
    if "phenolic_fingerprint" in sys.modules:
        return None
    spec = importlib.util.spec_from_file_location("phenolic_fingerprint", path)
    if spec is None or spec.loader is None:
        return "phenolic_fingerprint.py could not be loaded"
    module = importlib.util.module_from_spec(spec)
    sys.modules["phenolic_fingerprint"] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        sys.modules.pop("phenolic_fingerprint", None)
        return f"{type(exc).__name__}: {exc}"[:240]
    return None


def public_layer_tools() -> list[Any]:
    from aureon_public.more_layers import TOOLS

    return [
        package_dispositions,
        hnc_substrate_eval,
        hnc_echo_eval,
        hnc_observer_eval,
        hnc_potential_eval,
        hnc_translate_project,
        qgita_ftcp_detect,
        qgita_lighthouse_coherence,
        membrane_screen,
        repository_layers_hold,
        evidence_predict_next,
        source_names,
        *TOOLS,
    ]


def packages_resource() -> str:
    """Every package disposition, including operator exclusions. Provenance: inferred.

    Auris meanings stay separate. The conjecture is not called. The nine nodes and the coherence evaluator are the utils tools. The persona is not scored. Label: inferred.
    """

    return package_dispositions()
