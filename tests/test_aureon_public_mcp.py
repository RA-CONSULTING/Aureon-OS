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


def test_canonical_and_blend_omit_consciousness_keys() -> None:
    canonical = _load(tools.hnc_canonical_read())
    blend = _load(tools.hnc_blend_read())
    for body in (canonical, blend):
        assert "consciousness_level" not in body
        assert "consciousness_psi" not in body
    from aureon.core.hnc_field import CanonicalField

    public = {
        key: value
        for key, value in canonical.items()
        if key not in {"label", "status", "aureon_source"}
    }
    rebuilt = CanonicalField(**public)
    assert rebuilt.consciousness_level is None
    assert rebuilt.consciousness_psi is None


def test_require_pin_blocks_every_source_except_the_pin(monkeypatch: pytest.MonkeyPatch) -> None:
    from aureon_public.server import enforce_public_pin

    monkeypatch.delenv("AUREON_PUBLIC_REQUIRE_PIN", raising=False)
    enforce_public_pin({"kind": "checkout", "commit": "a" * 40})
    monkeypatch.setenv("AUREON_PUBLIC_REQUIRE_PIN", "1")
    enforce_public_pin({"kind": "pinned", "commit": PINNED_COMMIT})
    for source in (
        {"kind": "installed", "commit": "b" * 40},
        {"kind": "checkout", "commit": "c" * 40},
        {"kind": "pinned", "commit": "d" * 40},
    ):
        with pytest.raises(SystemExit):
            enforce_public_pin(source)


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
    assert mismatched == {"kind": "installed", "commit": "b" * 40}


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
    assert source["kind"] in {"pinned", "installed", "checkout"}
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
    from aureon_public.layers import public_layer_tools

    names = sorted(item.name for item in tools_listed)
    expected = {
        "auris_coherence",
        "auris_nodes",
        "hnc_blend_read",
        "hnc_canonical_read",
        "hnc_reality_step",
        "lambda_engine_step",
        "organism_catalog",
        "organism_replay_read",
        "qgita_analyze",
        *(fn.__name__ for fn in public_layer_tools()),
        "body_call",
        "body_depth",
        "body_registry",
        "body_surface",
    }
    assert set(names) == expected
    hnc = next(item for item in tools_listed if item.name == "hnc_reality_step")
    assert hnc.description is not None
    assert "multiverse on" in hnc.description
    assert hnc.inputSchema["properties"]["enable_multiverse"]["default"] is True
    resources = asyncio.run(server.list_resources())
    uris = sorted(str(item.uri) for item in resources)
    assert "aureon://auris/nodes" in uris
    assert "aureon://replay/auris" in uris
    assert "aureon://packages" in uris
    assert "aureon://body/depth" in uris
    assert "aureon://body/registry" in uris
    assert len(uris) == 15
    prompts = asyncio.run(server.list_prompts())
    prompt_names = sorted(item.name for item in prompts)
    assert "explain_auris_four_meanings" in prompt_names
    assert len(prompt_names) == 4


def test_each_new_layer_tool_is_labelled_and_omits_consciousness_keys() -> None:
    calls = {
        "package_dispositions": layers_call("package_dispositions"),
        "hnc_substrate_eval": layers_call("hnc_substrate_eval"),
        "hnc_echo_eval": layers_call("hnc_echo_eval"),
        "hnc_observer_eval": layers_call("hnc_observer_eval"),
        "hnc_potential_eval": layers_call("hnc_potential_eval"),
        "hnc_translate_project": layers_call("hnc_translate_project"),
        "qgita_ftcp_detect": layers_call("qgita_ftcp_detect"),
        "qgita_lighthouse_coherence": layers_call("qgita_lighthouse_coherence"),
        "membrane_screen": layers_call("membrane_screen"),
        "repository_layers_hold": layers_call("repository_layers_hold"),
        "evidence_predict_next": layers_call("evidence_predict_next"),
        "source_names": layers_call("source_names", "core"),
    }
    for name, body in calls.items():
        assert body.get("provenance") in {"cited", "inferred", "cited-unverified", "speculative"}, name
        assert "aureon_source" in body
        assert "consciousness_level" not in body
        assert "consciousness_psi" not in body
        flat = json.dumps(body)
        assert "consciousness_" not in flat
    assert calls["evidence_predict_next"]["human_eval"] == "not run. HOLD"
    assert calls["qgita_ftcp_detect"]["detection_rate"] == "HOLD"
    assert calls["repository_layers_hold"]["may_act"] is False
    rows = calls["package_dispositions"]["packages"]
    assert len(rows) == 54
    assert {row["package"] for row in rows if row["kind"] == "operator"} >= {
        "trading",
        "exchanges",
        "bots",
        "bots_intelligence",
        "bridges",
        "scanners",
    }


def layers_call(name: str, package: str | None = None) -> dict:
    from aureon_public import layers

    fn = getattr(layers, name)
    if package is None:
        return _load(fn())
    return _load(fn(package))


def test_source_names_refuses_blocked_packages_and_guard_still_blocks_import() -> None:
    from aureon_public.layers import source_names

    for package in (
        "trading",
        "exchanges",
        "bots",
        "bots_intelligence",
        "bridges",
        "scanners",
        "unified_margin_trader",
    ):
        body = _load(source_names(package))
        assert body["status"] == "unavailable"
    import importlib

    for module in (
        "aureon.exchanges",
        "aureon.trading",
        "aureon.bots",
        "aureon.bots_intelligence",
        "aureon.bridges",
        "aureon.scanners",
        "unified_margin_trader",
    ):
        with pytest.raises(ImportError):
            importlib.import_module(module)


def test_operator_server_stays_off_without_the_flag_and_is_stdio_only(monkeypatch: pytest.MonkeyPatch) -> None:
    from aureon_operator.server import main as operator_main
    from aureon_operator.server import refuse_live_order

    monkeypatch.delenv("AUREON_OPERATOR_MCP", raising=False)
    with pytest.raises(SystemExit):
        operator_main([])
    monkeypatch.setenv("AUREON_OPERATOR_MCP", "1")
    with pytest.raises(SystemExit):
        operator_main(["--transport", "streamable-http"])
    body = _load(refuse_live_order("BTCUSDT"))
    assert body["live_orders"] == "refused"
    assert body["status"] == "unavailable"


def test_new_package_tools_and_membrane_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    import sys

    from aureon_public import layers
    from aureon_public.more_layers import TOOLS

    for fn in TOOLS:
        body = _load(fn())
        assert body.get("provenance") in {"cited", "inferred", "cited-unverified"}, fn.__name__
        assert "consciousness_" not in json.dumps(body)
        assert body.get("status") in {"cited", "inferred", "unavailable"}
        assert str(body.get("label", "")).startswith("helper.")
    fear = _load(getattr(sys.modules["aureon_public.more_layers"], "analytics_fear_greed")())
    tick = _load(getattr(sys.modules["aureon_public.more_layers"], "data_feed_parse_tick")())
    assert fear["label"] == (
        "helper. inferred. derive_fear_greed on a fixed 40-step fixture ramp, not market data. Not a backtest."
    )
    assert tick["label"] == (
        "helper. inferred. parse_binance_tick on one fixture tick, not market data. No socket was opened."
    )
    live = _load(layers.membrane_screen("hello"))
    assert live["status"] == "cited"
    assert live["provenance"] == "cited"
    assert "loaded from checkout" in live["label"]
    assert "blob check" in live["label"]
    monkeypatch.setattr(layers, "_load_phenolic_fingerprint", lambda: "phenolic_fingerprint.py is not in this checkout")
    sys.modules.pop("aureon.bio.mcp_membrane", None)
    blocked = _load(layers.membrane_screen("hello"))
    assert blocked["status"] == "unavailable"
    assert blocked["provenance"] == "cited-unverified"
    assert "phenolic_fingerprint" in blocked["reason"]
    rows = _load(layers.package_dispositions())["packages"]
    kinds = {row["package"]: row["kind"] for row in rows}
    assert kinds["cognition"] == "cognition_logic_flow"
    assert kinds["queen"] == "queen_zpe_ground"
    assert kinds["swarm"] == "swarm_voice_for_gamma"
    assert kinds["observer"] == "observer_kp_sample"
    assert kinds["gates"] == "gates_reading"
    assert kinds["atn"] == "excluded"
    assert kinds["identity"] == "excluded"
    assert all(row["reason"].startswith("Helper only.") for row in rows if row["package"] in {
        "alignment", "atn", "cognition", "queen", "vault"
    })


def test_phenolic_blob_matches_pin_and_a_changed_copy_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import sys

    from aureon_public import layers, paths
    from aureon_public.pin_blob import PINNED_PHENOLIC_BLOB, git_blob_sha1

    original = paths.repo_root() / "phenolic_fingerprint.py"
    assert git_blob_sha1(original.read_bytes()) == PINNED_PHENOLIC_BLOB
    sys.modules.pop("phenolic_fingerprint", None)
    assert layers._load_phenolic_fingerprint() is None
    matched = _load(layers.membrane_screen("hello"))
    assert matched["status"] == "cited"

    (tmp_path / "phenolic_fingerprint.py").write_bytes(original.read_bytes() + b"\n# not the pin\n")
    reason = layers._load_phenolic_fingerprint(tmp_path)
    assert reason == "checkout phenolic_fingerprint differs from pin a00f744d"
    monkeypatch.setattr(layers.paths, "repo_root", lambda: tmp_path)
    refused = _load(layers.membrane_screen("hello"))
    assert refused["status"] == "unavailable"
    assert refused["reason"] == "checkout phenolic_fingerprint differs from pin a00f744d"


def test_pinned_source_reads_once_and_executes_those_bytes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import sys

    from aureon_public.pin_blob import git_blob_sha1, load_pinned_source

    path = tmp_path / "pinned_bytes_probe.py"
    path.write_text("VALUE = 1\n", encoding="utf-8")
    expected = git_blob_sha1(path.read_bytes())
    real_read = Path.read_bytes
    reads: list[Path] = []

    def read_once(self: Path) -> bytes:
        data = real_read(self)
        if self == path:
            reads.append(self)
            path.write_text("VALUE = 2\n", encoding="utf-8")
        return data

    monkeypatch.setattr(Path, "read_bytes", read_once)
    sys.modules.pop("pinned_bytes_probe", None)
    assert load_pinned_source("pinned_bytes_probe", path, expected, "mismatch") is None
    assert reads == [path]
    assert sys.modules["pinned_bytes_probe"].VALUE == 1
    sys.modules.pop("pinned_bytes_probe", None)

    changed = tmp_path / "pinned_bytes_changed.py"
    changed.write_bytes(path.read_bytes())
    sys.modules.pop("pinned_bytes_changed", None)
    refusal = load_pinned_source("pinned_bytes_changed", changed, expected, "mismatch")
    assert refusal == "mismatch"
    assert "pinned_bytes_changed" not in sys.modules
    assert load_pinned_source("pinned_bytes_changed", changed, "", "mismatch") == "expected blob is required"


def test_spec_from_file_location_is_not_used_under_mcp() -> None:
    import ast

    root = ROOT / "mcp"
    offenders: list[str] = []
    for path in root.rglob("*.py"):
        if any(part in {"build", "__pycache__"} for part in path.parts):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            name = ""
            if isinstance(node, ast.Name):
                name = node.id
            elif isinstance(node, ast.Attribute):
                name = node.attr
            if name == "spec_from_file_location":
                offenders.append(f"{path.relative_to(root)}:{node.lineno}")
    assert offenders == []


def test_subprocess_body_call_ignores_stray_module_in_repo_root() -> None:
    import importlib

    from aureon_public.body import body_call

    root = ROOT
    shadow = root / "aureon.py"
    shadow.write_text(
        'raise ImportError("stray repo-root aureon.py was imported")\n',
        encoding="utf-8",
    )
    try:
        body = _load(body_call("harmonic/rainbow_reference.py", "solfeggio_ladder"))
        assert body["status"] == "cited"
        assert body.get("called") is True
    finally:
        shadow.unlink(missing_ok=True)
        for name in list(sys.modules):
            if name == "aureon" or name.startswith("aureon."):
                sys.modules.pop(name, None)
        importlib.invalidate_caches()


def test_import_checked_refuses_disallowed_parent_package() -> None:
    from aureon_public.body import _import_checked

    loaded, refusal = _import_checked("exchanges/single_currency_equity.py")
    assert loaded is None
    assert refusal is not None
    assert "exchanges" in refusal


def test_import_checked_has_no_import_module_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    import importlib

    from aureon_public.body import _import_checked

    def forbidden(name: str, *args: object, **kwargs: object) -> object:
        raise AssertionError(f"importlib.import_module must not be used; got {name!r}")

    monkeypatch.setattr(importlib, "import_module", forbidden)
    loaded, refusal = _import_checked("harmonic/rainbow_reference.py")
    assert loaded is not None
    assert refusal is None
    assert hasattr(loaded, "solfeggio_ladder")


def test_space_entry_points_call_enforce_public_pin() -> None:
    for name in ("hnc-field", "auris-coherence", "qgita-snr", "organism-replay"):
        text = (ROOT / "huggingface" / name / "app.py").read_text(encoding="utf-8")
        main_at = text.index('if __name__ == "__main__":')
        call_at = text.index("enforce_public_pin()")
        assert call_at > main_at
        assert "demo.launch(" in text[call_at:]
