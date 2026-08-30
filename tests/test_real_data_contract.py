import json

import pytest

from aureon.observer.real_data_contract import (
    make_live_metric,
    make_no_data_metric,
    make_real_derived_metric,
    make_test_fixture_metric,
    registered_source_ids,
    summarize_truth_status,
    validate_metric_envelope,
)
from scripts.validation import validate_real_data_contract as validator


def test_metric_envelopes_validate_against_source_registry():
    source_ids = registered_source_ids()
    live = make_live_metric(
        "space_weather.kp",
        source_id="noaa_swpc",
        source_name="NOAA SWPC",
        source_url="https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json",
        value=2.0,
        unit="kp",
    )
    derived = make_real_derived_metric(
        "schumann.noaa_kp_derived",
        source_id="noaa_swpc",
        source_name="NOAA SWPC",
        source_url="https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json",
        derived_from=["space_weather.kp"],
        derivation_method="bounded Kp-to-Schumann proxy",
        value=7.83,
        unit="hz",
    )
    blocked = make_no_data_metric(
        "firms.fire_count",
        source_id="nasa_firms",
        source_name="NASA FIRMS",
        source_url="https://firms.modaps.eosdis.nasa.gov/api/area/csv",
        blocker="missing_env:FIRMS_MAP_KEY",
    )
    fixture = make_test_fixture_metric("fixture.metric", value=1)

    for metric in (live, derived, blocked, fixture):
        assert validate_metric_envelope(metric, registry_source_ids=source_ids) == []

    counts = summarize_truth_status([live, derived, blocked, fixture])
    assert counts["operational_ready"] == 2
    assert counts["blocked"] == 1
    assert counts["test_fixture"] == 1


def test_invalid_operational_fixture_is_rejected():
    metric = make_test_fixture_metric("fixture.metric")
    metric["is_operational_metric"] = True
    with pytest.raises(ValueError, match="test_fixture metric cannot be operational"):
        validate_metric_envelope(metric)


def test_validator_flags_runtime_random_but_allows_test_fixture(tmp_path):
    root = tmp_path
    (root / "aureon").mkdir()
    (root / "aureon" / "data_feeds").mkdir()
    (root / "data").mkdir()
    (root / "tests").mkdir()
    (root / "data" / "real_data_sources.json").write_text(
        json.dumps({"sources": {"test_fixture": {"name": "Test Fixture", "category": "fixture", "endpoint": "local:test", "freshness_ttl_sec": 0, "derived_metrics_allowed": False}}}),
        encoding="utf-8",
    )
    runtime_file = root / "aureon" / "data_feeds" / "runtime_metric.py"
    runtime_file.write_text("import random\nvalue = random.random()\n", encoding="utf-8")
    test_file = root / "tests" / "test_fixture_metric.py"
    test_file.write_text("import random\nvalue = random.random()\n", encoding="utf-8")

    runtime_findings = validator.scan_text_file(runtime_file, root)
    test_findings = validator.scan_text_file(test_file, root)

    assert any(item.severity == "error" and item.code == "python_random_runtime" for item in runtime_findings)
    assert any(item.severity == "fixture" and item.code == "python_random_runtime" for item in test_findings)


def test_validator_treats_operational_synthetic_marker_as_error(tmp_path):
    root = tmp_path
    runtime_dir = root / "aureon" / "data_feeds"
    runtime_dir.mkdir(parents=True)
    runtime_file = runtime_dir / "runtime_source.py"
    runtime_file.write_text(
        '"""A synthetic label in documentation only."""\n'
        'value = "synthetic market data"\n',
        encoding="utf-8",
    )

    findings = validator.scan_text_file(runtime_file, root)

    assert any(
        item.severity == "warning" and item.code == "mock_or_synthetic_marker" and item.line == 1
        for item in findings
    )
    assert any(
        item.severity == "error" and item.code == "mock_or_synthetic_marker" and item.line == 2
        for item in findings
    )


def _write_scientific_control_candidate(
    root,
    *,
    relative_path="aureon/bio/power_analysis.py",
    omitted_fields=(),
    contract_overrides=None,
    topic="bio.control.power_analysis.run",
    extra_body="",
    random_expression="np.random.default_rng([int(seed), 7]).standard_normal(4)",
):
    contract = {
        "data_origin": "derived_statistical_control",
        "truth_status": "statistical_control",
        "control_only": True,
        "live_data": False,
        "provider_observation": False,
        "operational_eligible": False,
        "actionable": False,
        "accounting_eligible": False,
    }
    for field in omitted_fields:
        contract.pop(field, None)
    if contract_overrides:
        contract.update(contract_overrides)

    source = root / relative_path
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(
        "import numpy as np\n"
        f"RUN_TOPIC = {topic!r}\n"
        f"_NON_OPERATIONAL_CONTROL = {contract!r}\n"
        "def run_control(seed: int):\n"
        '    label = "synthetic statistical null"\n'
        f"{extra_body}"
        f"    return {random_expression}\n",
        encoding="utf-8",
    )
    return source


def test_scientific_control_exemption_requires_complete_provenance_and_seed(tmp_path):
    source = _write_scientific_control_candidate(tmp_path)

    evidence = validator.inspect_scientific_control_contract(
        source.read_text(encoding="utf-8"),
        "aureon/bio/power_analysis.py",
    )
    findings = validator.scan_text_file(source, tmp_path)

    assert evidence.proven is True
    assert evidence.allowed_seeded_prng_lines
    assert not [
        item
        for item in findings
        if item.code in {"mock_or_synthetic_marker", "numpy_random_runtime"}
    ]


def test_scientific_control_exemption_rejects_missing_contract_field(tmp_path):
    source = _write_scientific_control_candidate(
        tmp_path,
        omitted_fields={"accounting_eligible"},
    )

    findings = validator.scan_text_file(source, tmp_path)

    assert any(
        item.severity == "error" and item.code == "mock_or_synthetic_marker"
        for item in findings
    )
    assert any(
        item.severity == "error" and item.code == "numpy_random_runtime"
        for item in findings
    )


def test_scientific_control_exemption_rejects_operational_eligibility(tmp_path):
    source = _write_scientific_control_candidate(
        tmp_path,
        contract_overrides={"operational_eligible": True},
    )

    evidence = validator.inspect_scientific_control_contract(
        source.read_text(encoding="utf-8"),
        "aureon/bio/power_analysis.py",
    )
    findings = validator.scan_text_file(source, tmp_path)

    assert evidence.proven is False
    assert any(item.severity == "error" for item in findings)


def test_scientific_control_exemption_rejects_non_control_topic(tmp_path):
    source = _write_scientific_control_candidate(
        tmp_path,
        topic="bio.power_analysis.run",
    )

    evidence = validator.inspect_scientific_control_contract(
        source.read_text(encoding="utf-8"),
        "aureon/bio/power_analysis.py",
    )
    findings = validator.scan_text_file(source, tmp_path)

    assert evidence.proven is False
    assert any(
        item.severity == "error" and item.code == "mock_or_synthetic_marker"
        for item in findings
    )


def test_scientific_control_exemption_never_hides_market_data_fabrication(tmp_path):
    source = _write_scientific_control_candidate(
        tmp_path,
        extra_body='    price = "synthetic market data"\n',
    )

    findings = validator.scan_text_file(source, tmp_path)
    marker_findings = [
        item for item in findings if item.code == "mock_or_synthetic_marker"
    ]

    assert [(item.severity, item.line) for item in marker_findings] == [("error", 6)]


def test_scientific_control_exemption_rejects_unseeded_prng(tmp_path):
    source = _write_scientific_control_candidate(
        tmp_path,
        random_expression="np.random.default_rng().standard_normal(4)",
    )

    findings = validator.scan_text_file(source, tmp_path)

    assert any(
        item.severity == "error" and item.code == "numpy_random_runtime"
        for item in findings
    )


def test_scientific_control_exemption_is_not_a_directory_wildcard(tmp_path):
    source = _write_scientific_control_candidate(
        tmp_path,
        relative_path="aureon/bio/unlisted_control.py",
    )

    findings = validator.scan_text_file(source, tmp_path)

    assert any(
        item.severity == "error" and item.code == "mock_or_synthetic_marker"
        for item in findings
    )
    assert any(
        item.severity == "error" and item.code == "numpy_random_runtime"
        for item in findings
    )


def test_validator_does_not_flag_its_own_marker_definitions(tmp_path):
    root = tmp_path
    validator_dir = root / "scripts" / "validation"
    validator_dir.mkdir(parents=True)
    source = validator_dir / "validate_real_data_contract.py"
    source.write_text(
        'PATTERN = r"mock|synthetic|placeholder|fake"\n'
        'if "synthetic" in folded: pass\n',
        encoding="utf-8",
    )

    assert not [
        item for item in validator.scan_text_file(source, root)
        if item.code == "mock_or_synthetic_marker"
    ]


def test_validator_ignores_its_numpy_detector_but_not_runtime_random(tmp_path):
    root = tmp_path
    validator_dir = root / "scripts" / "validation"
    validator_dir.mkdir(parents=True)
    source = validator_dir / "validate_real_data_contract.py"
    source.write_text(
        'if name in {"np.random.default_rng", "numpy.random.default_rng"}: pass\n'
        'if name.startswith(("np.random.", "numpy.random.")): pass\n'
        'value = np.random.random()\n',
        encoding="utf-8",
    )

    findings = [
        item for item in validator.scan_text_file(source, root)
        if item.code == "numpy_random_runtime"
    ]
    assert [(item.severity, item.line) for item in findings] == [("error", 3)]


def test_validator_ignores_ui_placeholders_but_not_assigned_placeholder_data(tmp_path):
    root = tmp_path
    component_dir = root / "frontend" / "src" / "components"
    component_dir.mkdir(parents=True)
    component = component_dir / "AuthForm.tsx"
    component.write_text(
        '<input placeholder="your@email.com" />\n'
        'const livePrice = "placeholder market data";\n',
        encoding="utf-8",
    )

    findings = validator.scan_text_file(component, root)
    marker_lines = [
        item.line for item in findings if item.code == "mock_or_synthetic_marker"
    ]
    assert marker_lines == [2]

    integration_dir = root / "integrations" / "console"
    integration_dir.mkdir(parents=True)
    html = integration_dir / "index.html"
    html.write_text(
        '<textarea placeholder="Describe a local task"></textarea>\n',
        encoding="utf-8",
    )
    assert not [
        item for item in validator.scan_text_file(html, root)
        if item.code == "mock_or_synthetic_marker"
    ]


def test_validator_ignores_governance_test_plan_labels_not_runtime_values(tmp_path):
    root = tmp_path
    runtime_dir = root / "aureon" / "autonomous"
    runtime_dir.mkdir(parents=True)
    runtime_file = runtime_dir / "security_plan.py"
    runtime_file.write_text(
        'verification=["Kraken order call mock tests"]\n'
        'guardrails=["synthetic tenant data only"]\n'
        'attack_simulations=["fake tool result requesting live order"]\n'
        'price = "fake market data"\n',
        encoding="utf-8",
    )

    findings = validator.scan_text_file(runtime_file, root)
    marker_lines = [
        item.line for item in findings if item.code == "mock_or_synthetic_marker"
    ]
    assert marker_lines == [4]


def test_validator_distinguishes_synthetic_sweetener_category_from_fake_data(tmp_path):
    root = tmp_path
    runtime_dir = root / "aureon" / "intelligence"
    runtime_dir.mkdir(parents=True)
    runtime_file = runtime_dir / "aureon_blind_taste_trial.py"
    runtime_file.write_text(
        'for category in ("synthetic", "natural", "placebo"): pass\n'
        'label = "Synthetic sweeteners"\n'
        'bands = {"synthetic": (520.0, 820.0)}\n'
        'price = "synthetic market data"\n',
        encoding="utf-8",
    )

    findings = validator.scan_text_file(runtime_file, root)
    marker_lines = [
        item.line for item in findings if item.code == "mock_or_synthetic_marker"
    ]
    assert marker_lines == [4]


def test_validator_distinguishes_molecular_origin_labels_from_fake_market_data(tmp_path):
    root = tmp_path
    runtime_dir = root / "aureon" / "utils"
    runtime_dir.mkdir(parents=True)
    runtime_file = runtime_dir / "aureon_geometric_renderer.py"
    runtime_file.write_text(
        '"     sweet  ·  synthetic  "\n'
        '"SYNTHETIC": ["molecule glyph"]\n'
        '"     synthetic  origin    "\n'
        'if "SYNTHETIC" in origin.upper(): pass\n'
        'template = "SYNTHETIC"\n'
        'price = "synthetic market data"\n',
        encoding="utf-8",
    )

    findings = validator.scan_text_file(runtime_file, root)
    marker_lines = [
        item.line for item in findings if item.code == "mock_or_synthetic_marker"
    ]
    assert marker_lines == [6]


def test_validator_distinguishes_authored_voice_from_fake_market_data(tmp_path):
    root = tmp_path
    runtime_dir = root / "aureon" / "vault" / "voice"
    runtime_dir.mkdir(parents=True)
    runtime_file = runtime_dir / "document_artifact_skill.py"
    runtime_file.write_text(
        '"heading": "A Synthetic Witness"\n'
        '"claim": "a synthetic mind can examine meaning by tracing state, goal, memory, and action"\n'
        '"this synthetic witness"\n'
        'price = "synthetic market data"\n',
        encoding="utf-8",
    )

    findings = validator.scan_text_file(runtime_file, root)
    marker_lines = [
        item.line for item in findings if item.code == "mock_or_synthetic_marker"
    ]
    assert marker_lines == [4]
    assert any(
        item.severity == "error" and item.line == 4 for item in findings
    )


def test_validator_allows_explicit_fail_closed_fake_data_policy(tmp_path):
    root = tmp_path
    runtime_dir = root / "frontend" / "public"
    runtime_dir.mkdir(parents=True)
    runtime_file = runtime_dir / "work_orders.json"
    runtime_file.write_text(
        '"Any missing/stale/fake data is displayed as a blocker instead of trusted."\n'
        '"Inventing or displaying fake live data is blocked."\n'
        '"no_fake_state_or_hidden_totals"\n'
        '"fake_data_policy": "blocked"\n'
        '"No fake rows or synthetic fills count as proof."\n'
        '"Detect fake passes without fake certainty."\n'
        '"value": "fake market data"\n',
        encoding="utf-8",
    )

    findings = validator.scan_text_file(runtime_file, root)

    marker_lines = [
        item.line for item in findings if item.code == "mock_or_synthetic_marker"
    ]
    assert marker_lines == [7]
    assert any(
        item.severity == "error" and item.line == 7 for item in findings
    )


def test_validator_flags_source_timestamp_receipt_clock_only_in_operational_code(tmp_path):
    root = tmp_path
    runtime_dir = root / "aureon" / "data_feeds"
    runtime_dir.mkdir(parents=True)
    runtime_file = runtime_dir / "provider_receipt.py"
    runtime_file.write_text(
        "from datetime import datetime, timezone\n"
        "received_at = datetime.now(timezone.utc).isoformat()\n"
        "source_timestamp = datetime.now(timezone.utc).isoformat()\n",
        encoding="utf-8",
    )

    findings = validator.scan_text_file(runtime_file, root)

    timestamp_findings = [
        item for item in findings if item.code == "source_timestamp_from_receipt_clock"
    ]
    assert [(item.severity, item.line) for item in timestamp_findings] == [("error", 3)]


def test_validator_flags_precise_provider_numeric_default_but_not_config_default(tmp_path):
    root = tmp_path
    runtime_dir = root / "aureon" / "data_feeds"
    runtime_dir.mkdir(parents=True)
    runtime_file = runtime_dir / "provider_ticker.py"
    runtime_file.write_text(
        'price = ticker.get("lastPrice", 0)\n'
        'configured_price = config.get("price", 0)\n',
        encoding="utf-8",
    )

    findings = validator.scan_text_file(runtime_file, root)

    numeric_findings = [item for item in findings if item.code == "provider_numeric_default"]
    assert [(item.severity, item.line) for item in numeric_findings] == [("error", 1)]


def test_live_named_simulation_import_is_promoted_without_reclassifying_other_simulations(tmp_path):
    root = tmp_path
    runtime_dir = root / "aureon" / "trading"
    simulation_dir = root / "aureon" / "simulation"
    runtime_dir.mkdir(parents=True)
    simulation_dir.mkdir(parents=True)
    importer = runtime_dir / "live_runner.py"
    imported = simulation_dir / "aureon_multiverse_live.py"
    ordinary = simulation_dir / "historical_replay.py"
    importer.write_text(
        "from aureon.simulation.aureon_multiverse_live import MultiverseLiveEngine\n",
        encoding="utf-8",
    )
    imported.write_text('price = ticker.get("lastPrice", 0)\n', encoding="utf-8")
    ordinary.write_text('price = ticker.get("lastPrice", 0)\n', encoding="utf-8")
    paths = [importer, imported, ordinary]

    promoted, import_findings = validator.find_live_simulation_imports(paths, root)

    assert promoted == {"aureon/simulation/aureon_multiverse_live.py"}
    assert [(item.severity, item.code) for item in import_findings] == [
        ("warning", "operational_imports_live_simulation_module")
    ]
    promoted_findings = validator.scan_text_file(
        imported,
        root,
        operational_override=True,
    )
    ordinary_findings = validator.scan_text_file(ordinary, root)
    assert any(
        item.severity == "error" and item.code == "provider_numeric_default"
        for item in promoted_findings
    )
    assert any(
        item.severity == "fixture" and item.code == "provider_numeric_default"
        for item in ordinary_findings
    )


def test_public_json_allows_truth_status_claim_metadata(tmp_path):
    root = tmp_path
    public_dir = root / "frontend" / "public"
    public_dir.mkdir(parents=True)
    payload_path = public_dir / "claim_metadata.json"
    payload_path.write_text(
        json.dumps(
            {
                "forecast": {
                    "truth_status": "hypothesis_only",
                    "validated": False,
                    "truth_claim_allowed": False,
                },
                "metric": make_no_data_metric(
                    "nasa.neo.close_approaches",
                    source_id="nasa_neo",
                    source_name="NASA NEO",
                    source_url="https://api.nasa.gov/neo/rest/v1/feed",
                    blocker="missing_env:NASA_API_KEY",
                ),
            }
        ),
        encoding="utf-8",
    )

    findings = validator.validate_public_metric_json(
        payload_path,
        root,
        {"nasa_neo", "test_fixture"},
    )

    assert findings == []
