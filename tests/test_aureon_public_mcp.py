"""Milestone-1 checks for aureon-public, including the three HNC reviewer cases."""

from __future__ import annotations

import asyncio
import inspect
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "mcp"))

from aureon_public import surfaces, tools  # noqa: E402
from aureon_public.guard_loader import (  # noqa: E402
    PINNED_COMMIT,
    aureon_source,
    describe_aureon_source,
)
from aureon_public.server import SERVER_INSTRUCTIONS, build_server  # noqa: E402
from aureon_public.text import SERVER_PLAIN  # noqa: E402

pytestmark = pytest.mark.timeout(180)


def _load(text: str) -> dict:
    return json.loads(text)


def _brain() -> dict:
    return json.loads((ROOT / "huggingface" / "hnc-field" / "replay" / "brain.json").read_text())


def test_server_text_says_outside_models_do_not_become_the_reasoning() -> None:
    readme = (ROOT / "mcp" / "aureon_public" / "README.md").read_text(encoding="utf-8")
    assert "A local checkout run uses its own commit, not the pin." in readme
    for sentence in (
        "MCP lets outside models call Aureon's tools.",
        "No outside model or API becomes Aureon's reasoning.",
        "The cognition runs in Aureon's own code.",
    ):
        assert sentence in readme
        assert sentence in SERVER_PLAIN
        assert sentence in SERVER_INSTRUCTIONS
    server = build_server()
    assert server.instructions is not None
    assert "No outside model or API becomes Aureon's reasoning." in server.instructions


def test_hnc_description_and_schema_keep_the_class_default_on() -> None:
    brain = _brain()
    doc = tools.hnc_reality_step.__doc__ or ""
    assert "Class default" in doc or "class default" in doc
    assert "True" in doc
    assert "multiverse on" in doc
    assert json.dumps(brain["hnc"]["multiverse_extension"]["coherence"]) in doc
    assert json.dumps(brain["hnc"]["coherence"]) in doc
    default = inspect.signature(tools.hnc_reality_step).parameters["enable_multiverse"].default
    assert default is True
    from aureon.harmonic.aureon_harmonic_reality import HarmonicRealityField

    class_default = inspect.signature(HarmonicRealityField.__init__).parameters["enable_multiverse"].default
    assert class_default is True


def test_hnc_reality_step_reports_enable_multiverse_and_matches_each_brain_path() -> None:
    brain = _brain()
    on = _load(tools.hnc_reality_step())
    assert on["enable_multiverse"] is True
    assert on["class_default_enable_multiverse"] is True
    assert on["committed_replay_match"] is True
    assert on["coherence"] == brain["hnc"]["multiverse_extension"]["coherence"]
    assert on["state_value"] == brain["hnc"]["multiverse_extension"]["state"]

    off = _load(tools.hnc_reality_step(enable_multiverse=False))
    assert off["enable_multiverse"] is False
    assert off["committed_replay_match"] is True
    assert off["coherence"] == brain["hnc"]["coherence"]
    assert off["state_value"] == brain["hnc"]["state"]
    assert on["coherence"] != off["coherence"]


def test_hnc_reality_step_caps_steps() -> None:
    capped = _load(tools.hnc_reality_step(steps=101))
    assert capped["status"] == "unavailable"
    assert capped["enable_multiverse"] is True
    assert "series" not in capped
    missing = _load(tools.hnc_reality_step(steps=0))
    assert missing["status"] == "unavailable"


def test_lambda_engine_step_is_unavailable_without_enough_readings() -> None:
    for call in (
        tools.lambda_engine_step(),
        tools.lambda_engine_step(readings=None),
        tools.lambda_engine_step(readings=[]),
        tools.lambda_engine_step(readings=[{"name": "only", "value": 0.2, "confidence": 1.0, "state": "x"}]),
        tools.lambda_engine_step(
            readings=[
                {"name": "a", "value": 0.2, "confidence": 1.0, "state": "x"},
                {"name": "b", "value": 0.4, "confidence": 1.0, "state": "y"},
            ]
        ),
    ):
        body = _load(call)
        assert body["status"] == "unavailable"
        assert body["lambda_t"] is None
        assert body["auris_to_lambda"] == "HOLD"
        assert not any(isinstance(value, (int, float)) and not isinstance(value, bool) for value in body.values())


def test_lambda_engine_step_runs_only_when_readings_and_volatility_are_supplied() -> None:
    body = _load(
        tools.lambda_engine_step(
            volatility=0.2,
            readings=[
                {"name": "a", "value": 0.2, "confidence": 1.0, "state": "x"},
                {"name": "b", "value": 0.4, "confidence": 1.0, "state": "y"},
            ],
        )
    )
    assert body["status"] == "inferred"
    assert body["auris_to_lambda"] == "HOLD"
    assert isinstance(body["lambda_t"], float)


def test_auris_coherence_is_no_data_and_lists_missing_nodes() -> None:
    doc = tools.auris_coherence.__doc__ or ""
    assert "coherence evaluator" in doc
    assert "not called" in doc
    assert "not scored" in doc
    assert "Auris-to-Lambda link: HOLD" in doc
    assert "Only the nine nodes and get_auris_coherence" in doc

    empty = _load(tools.auris_coherence())
    assert empty["status"] == "no_data"
    assert empty["coherence"] is None
    assert empty["auris"] == "coherence evaluator"
    assert empty["auris_to_lambda"] == "HOLD"
    assert len(empty["missing_nodes"]) == 9

    supplied = _load(tools.auris_coherence(volatility=0.2, momentum=0.1, volume=0.3, spread=0.05))
    assert supplied["status"] == "no_data"
    assert supplied["coherence"] is None
    assert "Owl" in supplied["missing_nodes"]
    assert "Clownfish" in supplied["missing_nodes"]
    assert supplied["missing_nodes"] == ["Clownfish", "Owl"]


def test_auris_names_say_which_auris() -> None:
    nodes_doc = tools.auris_nodes.__doc__ or ""
    assert "nine nodes" in nodes_doc
    assert "not called" in nodes_doc
    assert "not scored" in nodes_doc
    resource_doc = surfaces.auris_nodes_resource.__doc__ or ""
    replay_doc = surfaces.replay_auris_resource.__doc__ or ""
    prompt_doc = surfaces.explain_auris_four_meanings.__doc__ or ""
    for doc in (resource_doc, replay_doc, prompt_doc):
        assert "not called" in doc
        assert "not scored" in doc
        assert "get_auris_coherence" in doc or "coherence evaluator" in doc


def test_qgita_analyze_drops_signals_and_organism_fault_is_synthetic() -> None:
    qgita = _load(tools.qgita_analyze())
    assert "signals" not in qgita
    assert qgita["detection_rate"] == "HOLD"
    committed = json.loads(
        (ROOT / "huggingface" / "qgita-snr" / "replay" / "qgita_snr.json").read_text()
    )
    derived = committed["derived_series"]
    assert qgita["ftcp_count"] == derived["ftcp_count"]
    assert qgita["lhe_count"] == derived["lhe_count"]

    organism = _load(tools.organism_replay_read())
    fault = organism["seeded_synthetic_fault"]
    assert fault["label"] == "Seeded synthetic input, not telemetry."
    assert fault["origin"] == "synthetic"
    assert "HOLD" in fault["hold"]
    assert "verdict" in organism["cited"]


def test_canonical_and_blend_default_do_not_require_state() -> None:
    canonical = _load(tools.hnc_canonical_read())
    blend = _load(tools.hnc_blend_read())
    assert canonical["status"] == "unavailable"
    assert canonical["available"] is False
    assert blend["status"] == "unavailable"
    assert blend["available"] is False


def test_catalog_and_import_blocker() -> None:
    catalog = _load(tools.organism_catalog())
    assert catalog["seats"]
    assert catalog["nodes"]
    assert catalog["systems"]
    import importlib

    with pytest.raises(ImportError):
        importlib.import_module("aureon.trading")


def test_aureon_source_pinned_commit_comes_from_direct_url(tmp_path: Path) -> None:
    site = tmp_path / "site"
    package = site / "aureon"
    package.mkdir(parents=True)
    origin = package / "__init__.py"
    origin.write_text("", encoding="utf-8")
    dist = site / "aureon-2.1.0.dist-info"
    dist.mkdir()
    (dist / "direct_url.json").write_text(
        json.dumps({"vcs_info": {"commit_id": PINNED_COMMIT}}),
        encoding="utf-8",
    )
    source = describe_aureon_source(origin, tmp_path / "checkout")
    assert source == {"kind": "pinned", "commit": PINNED_COMMIT}

    other = site / "aureon-9.9.9.dist-info"
    other.mkdir()
    (dist / "direct_url.json").write_text(
        json.dumps({"vcs_info": {"commit_id": "b" * 40}}),
        encoding="utf-8",
    )
    # The first dist-info in sorted order is aureon-2.1.0, now rewritten.
    mismatched = describe_aureon_source(origin, tmp_path / "checkout")
    assert mismatched["kind"] == "checkout"
    assert mismatched["commit"] == "unknown"


def test_aureon_source_checkout_uses_git_head_or_unknown(tmp_path: Path) -> None:
    checkout = tmp_path / "tree"
    package = checkout / "aureon"
    package.mkdir(parents=True)
    origin = package / "__init__.py"
    origin.write_text("", encoding="utf-8")
    missing = describe_aureon_source(origin, checkout)
    assert missing == {"kind": "checkout", "commit": "unknown"}

    live = describe_aureon_source(ROOT / "aureon" / "__init__.py", ROOT)
    assert live["kind"] == "checkout"
    assert live["commit"] != "unknown"
    assert len(live["commit"]) == 40


def test_tool_output_and_server_info_name_the_aureon_that_ran() -> None:
    source = aureon_source()
    assert source["kind"] in {"pinned", "checkout"}
    if source["kind"] == "pinned":
        assert source["commit"] == PINNED_COMMIT
    else:
        assert source["commit"] == "unknown" or len(source["commit"]) == 40
    body = _load(tools.lambda_engine_step())
    assert body["aureon_source"] == source
    canonical = _load(tools.hnc_canonical_read())
    assert canonical["aureon_source"] == source
    server = build_server()
    assert json.dumps(source, sort_keys=True) in (server.instructions or "")


def test_registered_names() -> None:
    server = build_server()
    tools_listed = asyncio.run(server.list_tools())
    names = sorted(item.name for item in tools_listed)
    assert names == [
        "auris_coherence",
        "auris_nodes",
        "hnc_blend_read",
        "hnc_canonical_read",
        "hnc_reality_step",
        "lambda_engine_step",
        "organism_catalog",
        "organism_replay_read",
        "qgita_analyze",
    ]
    hnc = next(item for item in tools_listed if item.name == "hnc_reality_step")
    assert hnc.description is not None
    assert "multiverse on" in hnc.description
    assert hnc.inputSchema["properties"]["enable_multiverse"]["default"] is True
    resources = asyncio.run(server.list_resources())
    uris = sorted(str(item.uri) for item in resources)
    assert "aureon://auris/nodes" in uris
    assert "aureon://replay/auris" in uris
    assert len(uris) == 12
    prompts = asyncio.run(server.list_prompts())
    prompt_names = sorted(item.name for item in prompts)
    assert "explain_auris_four_meanings" in prompt_names
    assert len(prompt_names) == 4
