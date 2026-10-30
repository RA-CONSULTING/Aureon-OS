"""Stage-2 tools. Each call goes through dispatch. Inputs are files or tests in the repo.

No queen, miner, swarm_motion, in-house adapter, or network client is imported
here. A number in the result is the function's result on the named input.
"""

from __future__ import annotations

import json
from typing import Any

from aureon_public.alignment_layer import label_result
from aureon_public.body import _unavailable, dispatch
from aureon_public.quiet import quiet
from aureon_public.stage2_arguments import (
    DE440_SOURCE,
    PHENOLIC_ANALYSIS,
    REPORTS,
    TICK_HISTORY,
    de440_lambda_prefix,
    load_report,
)

_MODE = "aureon/observer/production_mode.py"
# The worker does not receive AUREON_OBSERVER_MODE. The code default in
# production_mode.py is the string live. The public result names that default
# and does not return it as a bare mode word.
MODE_WHEN_UNSET = {
    "mode_env": None,
    "code_default": "live",
    "note": "code default only; no broker session, no orders",
}


def _call(module: str, symbol: str, arguments: dict[str, Any]) -> str:
    return dispatch(module, symbol, arguments, server="public", timeout=30.0)


@quiet
def stage2_summarize_patterns() -> str:
    """Distil the phenolic bridge test's analysis dict.

    The dict is tests/test_phenolic_bridge.py. It is not a laboratory result
    from this server. The result names separable compounds and provenance counts
    in that dict.

    Args:
        none: The fixture is fixed. Label: cited.
    """

    return label_result(
        _call(
            "cognition/phenolic_bridge.py",
            "summarize_patterns",
            {"analysis": PHENOLIC_ANALYSIS},
        ),
        "tests/test_phenolic_bridge.py",
        "Fixture dict from that test. Not a laboratory result.",
    )


@quiet
def stage2_sumerian_decoder() -> str:
    """Build the Book of Ur decoder from the me catalog in that file.

    The catalog is the module's own table. This is not a live geographic reading.

    Args:
        none: The catalog is in the module. Label: cited.
    """

    return label_result(
        _call("decoders/book_of_ur.py", "get_sumerian_decoder", {}),
        "aureon/decoders/book_of_ur.py",
        "The decoder is built from the me catalog in that file.",
    )


@quiet
def stage2_sumerian_vector() -> str:
    """Return the bearing the Sumerian decoder computes from the Ur coordinates in that file.

    Args:
        none: The coordinates are in the module. Label: cited.
    """

    return label_result(
        _call("decoders/book_of_ur.py", "get_sumerian_geographic_vector", {}),
        "aureon/decoders/book_of_ur.py",
        "The vector is computed from the coordinates in that file.",
    )


@quiet
def stage2_iching_decoder() -> str:
    """Build the I Ching decoder from the hexagram table in that file.

    Args:
        none: The table is in the module. Label: cited.
    """

    return label_result(
        _call("decoders/iching_decoder.py", "get_iching_decoder", {}),
        "aureon/decoders/iching_decoder.py",
        "The decoder is built from the hexagram table in that file.",
    )


@quiet
def stage2_iching_vector() -> str:
    """Return the geographic vector the I Ching decoder computes from its own table.

    Args:
        none: The table is in the module. Label: cited.
    """

    return label_result(
        _call("decoders/iching_decoder.py", "get_iching_geographic_vector", {}),
        "aureon/decoders/iching_decoder.py",
        "The vector is computed from the table in that file.",
    )


def _render(name: str, module: str, symbol: str) -> str:
    relative = REPORTS[name]
    try:
        report = load_report(relative)
    except (OSError, TypeError, ValueError) as exc:
        return _unavailable(f"{relative} could not be read: {exc}")
    return label_result(
        _call(module, symbol, {"report": report}),
        relative,
        "The committed measured report. This formats that file. It does not rerun the proof.",
    )


@quiet
def stage2_render_auris() -> str:
    """Format the committed Auris report as markdown.

    The numbers are reports/measured/auris_nodes.json. This does not re-evaluate the nodes.

    Args:
        none: The file is fixed. Label: cited.
    """

    return _render("auris", "evaluation/auris_node_eval.py", "render_auris_markdown")


@quiet
def stage2_render_brain() -> str:
    """Format the committed brain report as markdown.

    The numbers are reports/measured/brain.json. This does not rerun the brain proof.

    Args:
        none: The file is fixed. Label: cited.
    """

    return _render("brain", "evaluation/brain_proof.py", "render_brain_markdown")


@quiet
def stage2_render_self_coder() -> str:
    """Format the committed self-coder report as markdown.

    The numbers are reports/measured/self_coder.json. This does not run the harness.

    Args:
        none: The file is fixed. Label: cited.
    """

    return _render("self_coder", "evaluation/measured_proof.py", "render_self_coder_markdown")


@quiet
def stage2_render_organism() -> str:
    """Format the committed organism report as markdown.

    The numbers are reports/measured/organism.json. This does not rerun circulation.

    Args:
        none: The file is fixed. Label: cited.
    """

    return _render("organism", "evaluation/organism_proof.py", "render_organism_markdown")


@quiet
def stage2_render_qgita() -> str:
    """Format the committed QGITA report as markdown.

    The numbers are reports/measured/qgita_snr.json. This does not rerun the benchmark.

    Args:
        none: The file is fixed. Label: cited.
    """

    return _render("qgita", "evaluation/qgita_snr_benchmark.py", "render_qgita_markdown")


@quiet
def stage2_predict_next() -> str:
    """Apply the pre-registered next-step rule to ticks 0 through 6.

    reports/measured/organism.json records tick baseline 6 and held-out tick 7.
    organism_proof.TICKS is 8. The result is that rule on this series, not a new organism run.

    Args:
        none: The series is fixed. Label: cited.
    """

    return label_result(
        _call("evaluation/organism_proof.py", "predict_next", {"values": TICK_HISTORY}),
        "reports/measured/organism.json",
        "Ticks 0 through 6. The committed report's tick baseline is 6 and the held-out tick is 7.",
    )


@quiet
def stage2_build_report() -> str:
    """Assemble a gate report from an empty check list.

    aureon/gates/benchmark.py says an empty list must not pass. The panel is not convened.
    The status is the assembler's empty-list result, not a gate measurement.

    Args:
        none: The check list is empty. Label: cited.
    """

    return label_result(
        _call("gates/benchmark.py", "build_report", {"checks": []}),
        "aureon/gates/benchmark.py",
        "Empty check list. The panel is not convened. An empty list must not pass.",
    )


@quiet
def stage2_ungrounded_nodes() -> str:
    """Name the panel nodes whose slice is absent from an empty grounded set.

    The empty set is tests/gates/test_switchboard.py. Tiger and Panda stay in the
    result because nothing in the organism measures those slices. This is not a live vote.

    Args:
        none: The grounded set is empty. Label: cited.
    """

    return label_result(
        _call("gates/panel.py", "ungrounded_nodes", {"grounded_slices": []}),
        "tests/gates/test_switchboard.py",
        "Empty grounded set from that test. Nothing was measured.",
    )


@quiet
def stage2_is_human_held(action: str = "draft") -> str:
    """Say whether an action is on the human-held list.

    The default draft is an ordinary action in tests/gates/test_switchboard.py
    and is not held. submit is held. This does not execute the action.

    Args:
        action: The action string passed to is_human_held. Label: cited, the switchboard test.
    """

    if not isinstance(action, str):
        return _unavailable("action is missing")
    text = _call("gates/switchboard.py", "is_human_held", {"action": action})
    if action == "draft":
        return label_result(
            text,
            "tests/gates/test_switchboard.py",
            "draft is an ordinary action in that test. It is not human-held.",
        )
    if action == "submit":
        return label_result(
            text,
            "tests/gates/test_switchboard.py",
            "submit is a human-held verb in that test.",
        )
    return text


def _fit(symbol: str) -> str:
    try:
        values = de440_lambda_prefix()
    except (OSError, KeyError, TypeError, ValueError) as exc:
        return _unavailable(f"{DE440_SOURCE} could not be read: {exc}")
    return label_result(
        _call("observer/fitter.py", symbol, {"lambda_values": values}),
        DE440_SOURCE,
        "The first 80 Lambda values of that file. A curve fit of that prefix, not a live trace and not a white-paper coefficient.",
    )


@quiet
def stage2_fit_tanh() -> str:
    """Fit alpha and g to the first 80 Lambda values in data/de440_timeseries.csv.

    This is a curve fit of that prefix. It is not a live trace and it is not the white-paper coefficients.

    Args:
        none: The prefix is fixed. Label: cited.
    """

    return _fit("fit_tanh")


@quiet
def stage2_fit_full() -> str:
    """Fit alpha, g, beta, and tau to the first 80 Lambda values in data/de440_timeseries.csv.

    This is a curve fit of that prefix. It is not a live trace and it is not the white-paper coefficients.

    Args:
        none: The prefix is fixed. Label: cited.
    """

    return _fit("fit_full")


@quiet
def stage2_simulation_fallback() -> str:
    """Read whether simulation fallback is allowed in this worker.

    The worker does not set AUREON_ALLOW_SIM_FALLBACK. The function's production posture is false.
    This does not fetch a feed.

    Args:
        none: The worker environment is the public worker environment. Label: cited.
    """

    return label_result(
        _call("observer/live_data_policy.py", "simulation_fallback_allowed", {}),
        "aureon/observer/live_data_policy.py",
        "The worker does not set AUREON_ALLOW_SIM_FALLBACK. False is that function's production posture.",
    )


@quiet
def stage2_log_blocked_fallback() -> str:
    """Log the benchmark's blocked-fallback line for source b70_probe.

    The source string is tests/benchmarks/benchmark_aureon_scope.py. This writes a log line. It does not fetch.

    Args:
        none: The source and reason are the benchmark's. Label: cited.
    """

    return label_result(
        _call(
            "observer/live_data_policy.py",
            "log_blocked_fallback",
            {"reason": "live_unavailable", "source": "b70_probe"},
        ),
        "tests/benchmarks/benchmark_aureon_scope.py",
        "The source string in that benchmark. A log line. No fetch.",
    )


@quiet
def stage2_fallback_marker() -> str:
    """Build the fallback audit dict from the benchmark test.

    source is b70_probe and when is 123.0, both from tests/benchmarks/benchmark_aureon_scope.py.
    The dict says the reading is a test fixture.

    Args:
        none: The arguments are the benchmark's. Label: cited.
    """

    return label_result(
        _call(
            "observer/live_data_policy.py",
            "fallback_marker",
            {"source": "b70_probe", "when": 123.0},
        ),
        "tests/benchmarks/benchmark_aureon_scope.py",
        "when is 123.0 in that test. The dict is a test-fixture marker, not a live reading.",
    )


@quiet
def stage2_momentum_tracker() -> str:
    """Return the momentum tracker installed in this worker.

    A fresh worker has none, so the result is null. That null is not a momentum reading.

    Args:
        none: No tracker is installed. Label: cited.
    """

    return label_result(
        _call("observer/momentum.py", "get_momentum_tracker", {}),
        "aureon/observer/momentum.py",
        "A fresh worker has no tracker. Null is that fact, not a momentum reading.",
    )


@quiet
def stage2_momentum_predict() -> str:
    """Ask the momentum predictor with no tracker installed.

    The default symbol is BTCUSD, the function's own default. The result is the function's
    neutral no-data signal. It does not read a price.

    Args:
        none: The symbol default is the function's. Label: cited.
    """

    return label_result(
        _call("observer/momentum.py", "momentum_predict_fn", {}),
        "aureon/observer/momentum.py",
        "No tracker is installed. The neutral signal is the function's no-data result, not a price.",
    )


def _mode(symbol: str) -> str:
    """Call one production-mode entry point and replace its raw result.

    The worker does not receive AUREON_OBSERVER_MODE. The raw return is the
    code default. The public result is MODE_WHEN_UNSET, not that raw value.
    """

    text = label_result(
        _call("observer/production_mode.py", symbol, {}),
        _MODE,
        MODE_WHEN_UNSET["note"],
    )
    try:
        body = json.loads(text)
    except json.JSONDecodeError:
        return text
    if not isinstance(body, dict) or body.get("called") is not True:
        return text
    body["result"] = dict(MODE_WHEN_UNSET)
    return json.dumps(body, ensure_ascii=False, allow_nan=False, sort_keys=True)


@quiet
def stage2_observer_mode() -> str:
    """Read the observer mode with the variable unset.

    The result names the code default. It is not a broker session and it does not place an order.

    Args:
        none: The worker does not receive AUREON_OBSERVER_MODE. Label: cited.
    """

    return _mode("get_mode")


@quiet
def stage2_reload_mode() -> str:
    """Drop the cached observer mode and read the environment again.

    This does not write a file and does not start a process. The result names the code default.

    Args:
        none: The worker does not receive AUREON_OBSERVER_MODE. Label: cited.
    """

    return _mode("reload_mode")


@quiet
def stage2_is_live() -> str:
    """Ask whether the resolved observer mode equals the code default.

    The public result does not return that comparison as a bare word. It names the code default.

    Args:
        none: The worker does not receive AUREON_OBSERVER_MODE. Label: cited.
    """

    return _mode("is_live")


@quiet
def stage2_is_shadow() -> str:
    """Ask whether the resolved observer mode is the shadow setting.

    The public result names the code default. It does not describe a broker session.

    Args:
        none: The worker does not receive AUREON_OBSERVER_MODE. Label: cited.
    """

    return _mode("is_shadow")


@quiet
def stage2_gate_buy_veto() -> str:
    """Ask whether the buy veto flag follows the code default.

    The public result names the code default. This call does not place an order.

    Args:
        none: The worker does not receive AUREON_OBSERVER_MODE. Label: cited.
    """

    return _mode("gate_buy_veto_active")


@quiet
def stage2_gate_sell_veto() -> str:
    """Ask whether the sell veto flag follows the code default.

    The public result names the code default. This call does not place an order.

    Args:
        none: The worker does not receive AUREON_OBSERVER_MODE. Label: cited.
    """

    return _mode("gate_sell_veto_active")


@quiet
def stage2_narrow_band() -> str:
    """Ask whether the narrow-band flag follows the code default.

    The public result names the code default. This call does not change an order.

    Args:
        none: The worker does not receive AUREON_OBSERVER_MODE. Label: cited.
    """

    return _mode("narrow_band_threshold_active")


@quiet
def stage2_kelly_buffer() -> str:
    """Ask whether Kelly buffer scaling follows the code default.

    The public result names the code default. This call does not size an order.

    Args:
        none: The worker does not receive AUREON_OBSERVER_MODE. Label: cited.
    """

    return _mode("kelly_buffer_scaling_active")


@quiet
def stage2_vote_addition() -> str:
    """Ask whether the extra observer votes follow the code default.

    The public result names the code default. This call does not cast a vote.

    Args:
        none: The worker does not receive AUREON_OBSERVER_MODE. Label: cited.
    """

    return _mode("vote_addition_active")


@quiet
def stage2_phase_veto() -> str:
    """Ask whether the phase veto follows the code default.

    The public result names the code default. This call does not block an order.

    Args:
        none: The worker does not receive AUREON_OBSERVER_MODE. Label: cited.
    """

    return _mode("phase_veto_active")


@quiet
def stage2_volatility_veto() -> str:
    """Ask whether the volatility veto follows the code default.

    The public result names the code default. This call does not block an order.

    Args:
        none: The worker does not receive AUREON_OBSERVER_MODE. Label: cited.
    """

    return _mode("volatility_veto_active")


@quiet
def stage2_repo_root() -> str:
    """Resolve the checkout that contains aureon/ and data/.

    The public result may keep only the path type. The path is the checkout this process loaded.

    Args:
        none: The start path is the worker's current directory. Label: cited.
    """

    return label_result(
        _call("observer/real_data_contract.py", "repo_root_from", {}),
        "aureon/observer/real_data_contract.py",
        "The function walks parents for an aureon/ and data/ directory.",
    )


@quiet
def stage2_source_registry() -> str:
    """Read data/real_data_sources.json.

    The object is that file. This does not contact the sources.

    Args:
        none: The path is the function's own default. Label: cited.
    """

    return label_result(
        _call("observer/real_data_contract.py", "load_source_registry", {}),
        "data/real_data_sources.json",
        "The committed registry. No source was contacted.",
    )


@quiet
def stage2_source_ids() -> str:
    """List the source ids in data/real_data_sources.json.

    A set does not survive the public result cap as a list. The ids are the keys
    load_source_registry returns from that file.

    Args:
        none: The path is the function's own default. Label: cited.
    """

    return label_result(
        _call("observer/real_data_contract.py", "registered_source_ids", {}),
        "data/real_data_sources.json",
        "The ids are the keys of that file. A set may be returned as its type name.",
    )


@quiet
def stage2_test_fixture_metric() -> str:
    """Build the test-fixture metric named in tests/test_real_data_contract.py.

    The name is fixture.metric and the value is 1. The envelope's truth status is
    test_fixture. It is not a live metric.

    Args:
        none: The name and value are the test's. Label: cited.
    """

    return label_result(
        _call(
            "observer/real_data_contract.py",
            "make_test_fixture_metric",
            {"name": "fixture.metric", "value": 1},
        ),
        "tests/test_real_data_contract.py",
        "The name and value in that test. truth_status is test_fixture. Not a live metric.",
    )


@quiet
def stage2_truth_counts() -> str:
    """Count truth statuses in a one-item list whose status is test_fixture.

    test_fixture is the status make_test_fixture_metric writes. The count is of
    that one status, not a census of operational sources.

    Args:
        none: The list is that one status. Label: cited.
    """

    return label_result(
        _call(
            "observer/real_data_contract.py",
            "summarize_truth_status",
            {"metrics": [{"truth_status": "test_fixture"}]},
        ),
        "aureon/observer/real_data_contract.py",
        "One test_fixture status, the status make_test_fixture_metric writes. Not a census.",
    )


@quiet
def stage2_wave_predictor() -> str:
    """Return the wave predictor installed in this worker.

    A fresh worker has none, so the result is null. That null is not a forecast.

    Args:
        none: No predictor is installed. Label: cited.
    """

    return label_result(
        _call("observer/wave_predictor.py", "get_wave_predictor", {}),
        "aureon/observer/wave_predictor.py",
        "A fresh worker has no predictor. Null is that fact, not a forecast.",
    )


@quiet
def stage2_wave_predict() -> str:
    """Ask the wave predictor with none installed.

    The default symbol is BTCUSD, the function's own default. The result is the
    function's neutral not-running signal. It does not forecast a price.

    Args:
        none: The symbol default is the function's. Label: cited.
    """

    return label_result(
        _call("observer/wave_predictor.py", "wave_predictor_predict", {}),
        "aureon/observer/wave_predictor.py",
        "No predictor is installed. The neutral signal is the function's not-running result, not a price.",
    )


@quiet
def stage2_summarize_compounding() -> str:
    """Summarize an empty closed-trade receipt list.

    aureon/s51/aureon_51_compound.py calls this with an empty list when run as a script.
    The result is no_data. No trade is added.

    Args:
        none: The receipt list is empty. Label: cited.
    """

    return label_result(
        _call("s51/aureon_51_compound.py", "summarize_compounding", {"receipts": []}),
        "aureon/s51/aureon_51_compound.py",
        "Empty receipt list. The module reports no_data. No trade is added.",
    )


# Entry points these tools call. coverage_plan counts a tested point only when it is still reachable.
TESTED: tuple[tuple[str, str], ...] = (
    ("cognition/phenolic_bridge.py", "summarize_patterns"),
    ("decoders/book_of_ur.py", "get_sumerian_decoder"),
    ("decoders/book_of_ur.py", "get_sumerian_geographic_vector"),
    ("decoders/iching_decoder.py", "get_iching_decoder"),
    ("decoders/iching_decoder.py", "get_iching_geographic_vector"),
    ("evaluation/auris_node_eval.py", "render_auris_markdown"),
    ("evaluation/brain_proof.py", "render_brain_markdown"),
    ("evaluation/measured_proof.py", "render_self_coder_markdown"),
    ("evaluation/organism_proof.py", "predict_next"),
    ("evaluation/organism_proof.py", "render_organism_markdown"),
    ("evaluation/qgita_snr_benchmark.py", "render_qgita_markdown"),
    ("gates/benchmark.py", "build_report"),
    ("gates/panel.py", "ungrounded_nodes"),
    ("gates/switchboard.py", "is_human_held"),
    ("observer/fitter.py", "fit_tanh"),
    ("observer/fitter.py", "fit_full"),
    ("observer/live_data_policy.py", "simulation_fallback_allowed"),
    ("observer/live_data_policy.py", "log_blocked_fallback"),
    ("observer/live_data_policy.py", "fallback_marker"),
    ("observer/momentum.py", "get_momentum_tracker"),
    ("observer/momentum.py", "momentum_predict_fn"),
    ("observer/production_mode.py", "get_mode"),
    ("observer/production_mode.py", "reload_mode"),
    ("observer/production_mode.py", "is_live"),
    ("observer/production_mode.py", "is_shadow"),
    ("observer/production_mode.py", "gate_buy_veto_active"),
    ("observer/production_mode.py", "gate_sell_veto_active"),
    ("observer/production_mode.py", "narrow_band_threshold_active"),
    ("observer/production_mode.py", "kelly_buffer_scaling_active"),
    ("observer/production_mode.py", "vote_addition_active"),
    ("observer/production_mode.py", "phase_veto_active"),
    ("observer/production_mode.py", "volatility_veto_active"),
    ("observer/real_data_contract.py", "repo_root_from"),
    ("observer/real_data_contract.py", "load_source_registry"),
    ("observer/real_data_contract.py", "registered_source_ids"),
    ("observer/real_data_contract.py", "make_test_fixture_metric"),
    ("observer/real_data_contract.py", "summarize_truth_status"),
    ("observer/wave_predictor.py", "get_wave_predictor"),
    ("observer/wave_predictor.py", "wave_predictor_predict"),
    ("s51/aureon_51_compound.py", "summarize_compounding"),
)

TOOLS: list[Any] = [
    stage2_summarize_patterns,
    stage2_sumerian_decoder,
    stage2_sumerian_vector,
    stage2_iching_decoder,
    stage2_iching_vector,
    stage2_render_auris,
    stage2_render_brain,
    stage2_render_self_coder,
    stage2_render_organism,
    stage2_render_qgita,
    stage2_predict_next,
    stage2_build_report,
    stage2_ungrounded_nodes,
    stage2_is_human_held,
    stage2_fit_tanh,
    stage2_fit_full,
    stage2_simulation_fallback,
    stage2_log_blocked_fallback,
    stage2_fallback_marker,
    stage2_momentum_tracker,
    stage2_momentum_predict,
    stage2_observer_mode,
    stage2_reload_mode,
    stage2_is_live,
    stage2_is_shadow,
    stage2_gate_buy_veto,
    stage2_gate_sell_veto,
    stage2_narrow_band,
    stage2_kelly_buffer,
    stage2_vote_addition,
    stage2_phase_veto,
    stage2_volatility_veto,
    stage2_repo_root,
    stage2_source_registry,
    stage2_source_ids,
    stage2_test_fixture_metric,
    stage2_truth_counts,
    stage2_wave_predictor,
    stage2_wave_predict,
    stage2_summarize_compounding,
]
