"""Resources and prompts. Bodies are quoted from the checkout or from code constants."""

from __future__ import annotations

import json
from typing import Any

from aureon_public import paths
from aureon_public.quiet import quiet
from aureon_public.text import AURIS_FOUR, HOLD_LINE, SERVER_PLAIN


def _text(path_reader: Any) -> str:
    return path_reader().read_text(encoding="utf-8")


def _dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, allow_nan=False, sort_keys=True)


@quiet
def harmonic_reality_defaults() -> str:
    """Code defaults for HarmonicRealityField. Not a fit and not a measurement.

    The class default enable_multiverse is True (multiverse on). Label: cited, aureon/harmonic/aureon_harmonic_reality.py.
    """

    from aureon.harmonic.aureon_harmonic_reality import (
        DEFAULT_ALPHA,
        DEFAULT_BETA,
        DEFAULT_DELTA_T,
        DEFAULT_G,
        DEFAULT_TAU,
        PHI_INVERSE,
        SCHUMANN_BASE,
        HarmonicRealityField,
    )

    formula = ""
    for line in (HarmonicRealityField.__doc__ or "").splitlines():
        if "Λ(t)" in line or "Λ(t)" in line:
            formula = line.strip()
            break
    if not formula:
        for line in (HarmonicRealityField.__doc__ or "").splitlines():
            if "Λ" in line and "=" in line:
                formula = line.strip()
                break
    return _dumps(
        {
            "class_default_enable_multiverse": True,
            "delta_t": DEFAULT_DELTA_T,
            "formula": formula,
            "g": DEFAULT_G,
            "alpha": DEFAULT_ALPHA,
            "beta": DEFAULT_BETA,
            "label": "cited. Code defaults. Not a measurement.",
            "phi_inverse": PHI_INVERSE,
            "sample_rate": 1000.0,
            "schumann_base_constant": SCHUMANN_BASE,
            "schumann_f0": "null. HOLD.",
            "tau": DEFAULT_TAU,
        }
    )


@quiet
def lambda_engine_defaults() -> str:
    """LambdaEngine module constants. BETA is _resolve_beta(), not a fitted file.

    This resource does not read state/. Label: cited, aureon/core/aureon_lambda_engine.py.
    """

    from aureon.core import aureon_lambda_engine as engine

    return _dumps(
        {
            "ALPHA": engine.ALPHA,
            "BETA": engine.BETA,
            "BETA_note": "BETA is _resolve_beta(). When AUREON_HNC_BETA is unset the function returns 1.0.",
            "DELTA_T": engine.DELTA_T,
            "FREQUENCIES": list(engine.FREQUENCIES),
            "G": engine.G,
            "TAU": engine.TAU,
            "WEIGHTS": list(engine.WEIGHTS),
            "label": "cited. Not a fitted result. state/hnc_fitted_params.json was not read.",
        }
    )


@quiet
def hnc_params_code_defaults() -> str:
    """HNCParams field defaults. Not a fit. load_params is not called.

    Label: cited, aureon/core/hnc_params.py HNCParams.
    """

    from aureon.core.hnc_params import HNCParams

    params = HNCParams()
    return _dumps(
        {
            "alpha": params.alpha,
            "beta": params.beta,
            "delta_t": params.delta_t,
            "fitted_at": params.fitted_at,
            "fitted_from": params.fitted_from,
            "g": params.g,
            "label": "cited. Code defaults on HNCParams. Not a fit. load_params was not called.",
            "r_squared": params.r_squared,
            "tau": params.tau,
        }
    )


@quiet
def auris_nodes_resource() -> str:
    """Nine nodes. This resource is the AURIS_NODES table.

    It is not the conjecture (not called), not the persona (not scored), and not the coherence evaluator. Only the nine nodes and get_auris_coherence are real functions exposed here. Label: cited, aureon/utils/aureon_queen_hive_mind.py AURIS_NODES.
    """

    from aureon.utils.aureon_queen_hive_mind import AURIS_NODES

    return _dumps(
        {
            "auris": "nine nodes",
            "label": "cited. AURIS_NODES.",
            "nodes": AURIS_NODES,
            "which_auris": AURIS_FOUR,
        }
    )


@quiet
def organism_seats_resource() -> str:
    """circulation_seats(). Names only. Circulation is not started. Label: cited."""

    from aureon.core.organism_circulation import circulation_seats

    return _dumps({"label": "cited", "seats": list(circulation_seats())})


@quiet
def organism_nodes_resource() -> str:
    """list_nodes(). Names only. Label: cited."""

    from aureon.core.algorithmic_nodes import list_nodes

    return _dumps({"label": "cited", "nodes": list_nodes()})


@quiet
def organism_systems_resource() -> str:
    """list_systems(). The rule strings are the source text. Label: cited."""

    from aureon.core.deterministic_systems import list_systems

    return _dumps({"label": "cited", "systems": list_systems()})


def holds_resource() -> str:
    """HOLD lines from huggingface/README.md. Label: cited-unverified until a new run."""

    readme = _text(paths.holds_readme)
    return _dumps(
        {
            "hold": HOLD_LINE,
            "label": "cited-unverified. huggingface/README.md",
            "readme": readme,
        }
    )


def replay_brain_resource() -> str:
    """Vendored brain replay. Two paths. Class default is multiverse on. Label: cited."""

    return _text(paths.brain_json)


def replay_qgita_resource() -> str:
    """Vendored QGITA adapter record. Detection rate stays HOLD. Label: cited."""

    return _text(paths.qgita_json)


def replay_organism_resource() -> str:
    """Vendored circulation replay. The fault block in the file is seeded synthetic, not telemetry. Label: cited."""

    return _text(paths.organism_json)


def replay_auris_resource() -> str:
    """Committed coherence-evaluator replay with no market series.

    This resource is the coherence evaluator record. It is not the conjecture (not called), not a persona score (not scored), and it does not publish nine-node values. Only the nine nodes and get_auris_coherence are real functions exposed here. Label: cited, huggingface/fixed-seed-reproducible-runs/auris_nodes.json.
    """

    body = json.loads(_text(paths.auris_json))
    if isinstance(body, dict):
        body = {
            "auris": "coherence evaluator",
            "record": body,
            "which_auris": AURIS_FOUR,
        }
    return json.dumps(body, ensure_ascii=False, sort_keys=True)


@quiet
def explain_two_lambda_implementations() -> str:
    """HarmonicRealityField and LambdaEngine are different code with different defaults.

    A number from one is not a number from the other. The formulas below are the docstrings already in the repo. Label: cited.
    """

    from aureon.core import hnc_params
    from aureon.harmonic.aureon_harmonic_reality import HarmonicRealityField

    reality = " ".join(
        line.strip()
        for line in (HarmonicRealityField.__doc__ or "").splitlines()
        if "Λ" in line and "=" in line
    )
    params = " ".join(
        line.strip() for line in (hnc_params.__doc__ or "").splitlines() if "Λ" in line and "=" in line
    )
    return (
        "HarmonicRealityField and LambdaEngine are different implementations. "
        "A number from one is not a number from the other. "
        "The class default HarmonicRealityField() sets enable_multiverse=True (multiverse on). "
        f"HarmonicRealityField docstring: {reality} "
        f"hnc_params docstring: {params} "
        "Label: cited. No formula was added here."
    )


def explain_auris_four_meanings() -> str:
    """Name the four Auris meanings. Only two functions are exposed.

    This prompt is the four-way split. The conjecture is not called. The nine nodes are read_auris_nodes and AURIS_NODES. The persona is not scored. The coherence evaluator is get_auris_coherence. Auris-to-Lambda link: HOLD.
    """

    return (
        f"{AURIS_FOUR} "
        "auris_nodes calls read_auris_nodes. "
        "aureon://auris/nodes is the AURIS_NODES table. "
        "auris_coherence calls get_auris_coherence. "
        "Whenever any node has no reading, that tool returns status no_data and coherence null. "
        "Trade readiness: HOLD. Auris-to-Lambda link: HOLD."
    )


def explain_qgita_adapter() -> str:
    """QGITA events are the adapter return. Detection rate is HOLD. signals are not shown.

    Label: cited, QGITAMarketAnalyzer.analyze. The bundled series is cited-unverified and is not public market data.
    """

    return (
        "QGITA events are the return of QGITAMarketAnalyzer.analyze. "
        "They are not a detection rate. Detection rate: HOLD. False-alarm rate: HOLD. "
        "The signals object is not shown. "
        "The bundled Lambda column is cited-unverified and is not public market data."
    )


def explain_organism_replay() -> str:
    """The organism replay is a file. Catalog names are not a running circulation.

    The fault block is seeded synthetic input, not telemetry. Label: cited.
    """

    return (
        f"{SERVER_PLAIN} "
        "The organism replay is a file. "
        "Seats in the catalog are names. Circulation is not started. "
        "The fault block is seeded synthetic input, not telemetry. "
        "A claim that those faults are recorded seat faults is HOLD."
    )
