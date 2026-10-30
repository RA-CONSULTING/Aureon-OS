"""Real stage-2 call arguments. Values are copied from the repo, not invented.

A fixture name is resolved only inside a sweep worker. The public server
never sets ``AUREON_PUBLIC_SWEEP``, so a client cannot ask for a fixture.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from aureon_public.paths import repo_root

# Copied from tests/test_phenolic_bridge.py.
PHENOLIC_ANALYSIS: dict[str, Any] = {
    "valid": True,
    "alpha": 0.05,
    "source_path": "x.csv",
    "formats": ["native"],
    "controls": {"positive": {"passed": True}, "negative": {"passed": True}},
    "compounds": {
        "caffeic acid": {
            "test_A_p": 0.003,
            "test_B_p": 0.7,
            "separable": False,
            "n_peaks": 59,
            "sources": ["doi:cga"],
        },
        "luteolin": {
            "test_A_p": 0.005,
            "test_B_p": 0.6,
            "separable": True,
            "n_peaks": 21,
            "sources": ["doi:lut", "COMPUTED GFN2-xTB (theoretical, non-experimental)"],
        },
        "apigenin": {
            "test_A_p": 0.8,
            "test_B_p": 0.9,
            "separable": False,
            "n_peaks": 5,
            "sources": ["doi:api"],
        },
    },
}

# reports/measured/organism.json holds baseline 6 and predicted 7 for the tick
# field, and organism_proof.TICKS is 8. The history before the held-out tick is
# 0 through 6.
TICK_HISTORY = [0, 1, 2, 3, 4, 5, 6]

DE440_SOURCE = "data/de440_timeseries.csv"
DE440_LIMIT = 80
REPORTS = {
    "auris": "reports/measured/auris_nodes.json",
    "brain": "reports/measured/brain.json",
    "organism": "reports/measured/organism.json",
    "qgita": "reports/measured/qgita_snr.json",
    "self_coder": "reports/measured/self_coder.json",
}

# Reachable entry points the sweep calls, and the public server does not
# register, because the worker cannot be given the real object as JSON.
NOT_A_TOOL: dict[tuple[str, str], str] = {
    ("decoders/book_of_ur.py", "test_phi_resonance_me"): (
        "The argument is a SumerianMe. That class is not on the constructor "
        "allowlist, so the public server does not build one. The sweep uses "
        "the catalog entry ENSHIP from aureon/decoders/book_of_ur.py."
    ),
    ("observer/momentum.py", "set_momentum_tracker"): (
        "The argument is a MomentumTracker. The class is not on the constructor "
        "allowlist. The sweep constructs an empty tracker inside the worker."
    ),
    ("observer/predictor.py", "make_predictor"): (
        "The argument is a HarmonicObserver. The class is not on the constructor "
        "allowlist. The sweep uses the construction in "
        "tests/observer/test_predictor_contract.py: trace_interval_s 1.0 and "
        "publish_to_bus false."
    ),
    ("observer/wave_predictor.py", "set_wave_predictor"): (
        "The argument is a WavePredictor. The class is not on the constructor "
        "allowlist. The sweep constructs an empty predictor inside the worker."
    ),
    ("observer/wave_predictor.py", "make_predictor"): (
        "The argument is a WavePredictor. The class is not on the constructor "
        "allowlist. The sweep constructs an empty predictor inside the worker."
    ),
}


def de440_lambda_prefix(limit: int = DE440_LIMIT) -> list[float]:
    """The first Lambda values of the committed DE440 file."""

    path = repo_root() / DE440_SOURCE
    values: list[float] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            values.append(float(row["Lambda"]))
            if len(values) >= limit:
                break
    return values


def load_report(relative: str) -> dict[str, Any]:
    """One committed measured report. The file is read, not rewritten."""

    path = repo_root() / relative
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise TypeError(relative)
    return loaded


def attempts_for(module: str, symbol: str) -> list[dict[str, Any]]:
    """Argument calls for one stage-2 entry point. Empty when no-arg is the call."""

    key = (module, symbol)
    table: dict[tuple[str, str], list[dict[str, Any]]] = {
        ("cognition/phenolic_bridge.py", "summarize_patterns"): [
            {
                "arguments": {"analysis": PHENOLIC_ANALYSIS},
                "label": "phenolic_test_fixture",
                "note": "Fixture dict from the phenolic bridge test. Not a laboratory result.",
                "source": "tests/test_phenolic_bridge.py",
            }
        ],
        ("decoders/book_of_ur.py", "test_phi_resonance_me"): [
            {
                "fixture": "sumerian_enship",
                "label": "enship",
                "note": "First foundation me in the module catalog.",
                "source": "aureon/decoders/book_of_ur.py",
            }
        ],
        ("evaluation/auris_node_eval.py", "render_auris_markdown"): [_report_attempt("auris")],
        ("evaluation/brain_proof.py", "render_brain_markdown"): [_report_attempt("brain")],
        ("evaluation/measured_proof.py", "self_coder_report"): [
            {
                "fixture": "repo_root_path",
                "label": "checkout_root",
                "note": "The checkout path. This calls the harness.",
                "source": "aureon/evaluation/measured_proof.py",
            }
        ],
        ("evaluation/measured_proof.py", "render_self_coder_markdown"): [_report_attempt("self_coder")],
        ("evaluation/organism_proof.py", "predict_next"): [
            {
                "arguments": {"values": TICK_HISTORY},
                "label": "tick_history",
                "note": "Ticks 0 through 6. The committed organism report's tick baseline is 6 and the held-out tick is 7.",
                "source": "reports/measured/organism.json",
            }
        ],
        ("evaluation/organism_proof.py", "render_organism_markdown"): [_report_attempt("organism")],
        ("evaluation/qgita_snr_benchmark.py", "render_qgita_markdown"): [_report_attempt("qgita")],
        ("gates/benchmark.py", "build_report"): [
            {
                "arguments": {"checks": []},
                "label": "empty_checks",
                "note": "The function's own comment says an empty check list must not pass. The panel is not convened.",
                "source": "aureon/gates/benchmark.py",
            }
        ],
        ("gates/panel.py", "ungrounded_nodes"): [
            {
                "arguments": {"grounded_slices": []},
                "label": "empty_grounded_set",
                "note": "The empty set in tests/gates/test_switchboard.py. Nothing was measured.",
                "source": "tests/gates/test_switchboard.py",
            }
        ],
        ("gates/switchboard.py", "is_human_held"): [
            {
                "arguments": {"action": "draft"},
                "label": "draft",
                "note": "An ordinary action in the switchboard test.",
                "source": "tests/gates/test_switchboard.py",
            },
            {
                "arguments": {"action": "submit"},
                "label": "submit",
                "note": "A human-held verb in the switchboard test.",
                "source": "tests/gates/test_switchboard.py",
            },
        ],
        ("observer/fitter.py", "fit_tanh"): [_de440_attempt()],
        ("observer/fitter.py", "fit_full"): [_de440_attempt()],
        ("observer/live_data_policy.py", "fallback_marker"): [
            {
                "arguments": {"source": "b70_probe", "when": 123.0},
                "label": "b70_probe",
                "note": "The marker call in tests/benchmarks/benchmark_aureon_scope.py. when is 123.0 in that test.",
                "source": "tests/benchmarks/benchmark_aureon_scope.py",
            }
        ],
        ("observer/momentum.py", "set_momentum_tracker"): [
            {
                "fixture": "empty_momentum_tracker",
                "label": "empty_tracker",
                "note": "MomentumTracker() takes no readings.",
                "source": "aureon/observer/momentum.py",
            }
        ],
        ("observer/predictor.py", "make_predictor"): [
            {
                "fixture": "empty_harmonic_observer",
                "label": "unpublished_observer",
                "note": "The test constructs the observer with publish_to_bus false.",
                "source": "tests/observer/test_predictor_contract.py",
            }
        ],
        ("observer/real_data_contract.py", "make_test_fixture_metric"): [
            {
                "arguments": {"name": "fixture.metric", "value": 1},
                "label": "fixture_metric",
                "note": "The name and value in tests/test_real_data_contract.py. The envelope is a test fixture.",
                "source": "tests/test_real_data_contract.py",
            }
        ],
        ("observer/real_data_contract.py", "summarize_truth_status"): [
            {
                "arguments": {"metrics": [{"truth_status": "test_fixture"}]},
                "label": "one_test_fixture_status",
                "note": "truth_status test_fixture is the status make_test_fixture_metric writes. This is one status, not a census of sources.",
                "source": "aureon/observer/real_data_contract.py",
            }
        ],
        ("observer/wave_predictor.py", "set_wave_predictor"): [
            {
                "fixture": "empty_wave_for_set",
                "label": "empty_predictor",
                "note": "WavePredictor() takes no trace.",
                "source": "aureon/observer/wave_predictor.py",
            }
        ],
        ("observer/wave_predictor.py", "make_predictor"): [
            {
                "fixture": "empty_wave_for_make",
                "label": "empty_predictor",
                "note": "WavePredictor() takes no trace.",
                "source": "aureon/observer/wave_predictor.py",
            }
        ],
        ("s51/aureon_51_compound.py", "summarize_compounding"): [
            {
                "arguments": {"receipts": []},
                "label": "no_receipts",
                "note": "The module calls summarize_compounding with an empty list when run as a script. The result is no_data. No trade is added.",
                "source": "aureon/s51/aureon_51_compound.py",
            }
        ],
    }
    return table.get(key, [])


def _report_attempt(name: str) -> dict[str, Any]:
    relative = REPORTS[name]
    return {
        "fixture": f"report:{relative}",
        "label": relative,
        "note": "The committed measured report. This call formats that file. It does not rerun the proof.",
        "source": relative,
    }


def _de440_attempt() -> dict[str, Any]:
    return {
        "fixture": "de440_lambda_prefix",
        "label": "de440_lambda_prefix",
        "note": f"The first {DE440_LIMIT} Lambda values of {DE440_SOURCE}. A curve fit of that prefix, not a live trace.",
        "source": DE440_SOURCE,
    }


def resolve_fixture(name: str) -> dict[str, Any]:
    """Build one real argument inside the sweep worker."""

    if name == "repo_root_path":
        return {"root": repo_root()}
    if name == "sumerian_enship":
        from aureon.decoders.book_of_ur import _ME_CATALOG

        me = next(item for item in _ME_CATALOG if item.id == "ENSHIP")
        return {"me": me}
    if name == "empty_harmonic_observer":
        from aureon.observer.harmonic_observer import HarmonicObserver

        return {"observer": HarmonicObserver(trace_interval_s=1.0, publish_to_bus=False)}
    if name == "empty_momentum_tracker":
        from aureon.observer.momentum import MomentumTracker

        return {"t": MomentumTracker()}
    if name == "empty_wave_for_set":
        from aureon.observer.wave_predictor import WavePredictor

        return {"p": WavePredictor()}
    if name == "empty_wave_for_make":
        from aureon.observer.wave_predictor import WavePredictor

        return {"predictor": WavePredictor()}
    if name == "de440_lambda_prefix":
        return {"lambda_values": de440_lambda_prefix()}
    if name.startswith("report:"):
        return {"report": load_report(name.split(":", 1)[1])}
    raise KeyError(name)
