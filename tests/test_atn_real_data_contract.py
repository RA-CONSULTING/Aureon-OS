from aureon.atn import aureon_atn_monitor as atn


def test_atn_wildfire_missing_firms_key_returns_no_data(monkeypatch):
    monkeypatch.delenv("FIRMS_MAP_KEY", raising=False)

    result = atn._fetch_wildfires()

    assert result.name == "fire"
    assert result.error == "missing_env:FIRMS_MAP_KEY"
    assert result.raw["real_data"]["truth_status"] == "no_data"
    assert result.raw["real_data"]["source_id"] == "nasa_firms"


def test_atn_neo_missing_nasa_key_returns_no_data(monkeypatch):
    monkeypatch.delenv("NASA_API_KEY", raising=False)

    result = atn._fetch_neo()

    assert result.name == "neo"
    assert result.error == "missing_env:NASA_API_KEY"
    assert result.raw["real_data"]["truth_status"] == "no_data"
    assert result.raw["real_data"]["source_id"] == "nasa_neo"


def test_atn_state_serializes_truth_status(monkeypatch):
    fire = atn._no_data_stream(
        "fire",
        source_id="nasa_firms",
        source_name="NASA FIRMS",
        source_url="https://firms.modaps.eosdis.nasa.gov/api/area/csv",
        blocker="missing_env:FIRMS_MAP_KEY",
    )
    state = atn.EarthHazardState(
        timestamp=1.0,
        risk_factor=1.0,
        veto=False,
        reason="test",
        active_alerts=[],
        streams={"fire": fire},
    )

    payload = state.to_dict()
    assert payload["streams"]["fire"]["truth_status"] == "no_data"
    assert payload["streams"]["fire"]["source_id"] == "nasa_firms"
    assert payload["streams"]["fire"]["blocker"] == "missing_env:FIRMS_MAP_KEY"


def test_atn_aggregation_blocks_missing_error_and_no_data_streams(monkeypatch):
    good = atn.StreamResult(
        name="quake", score=1.0, veto=False, alerts=[], raw={"max_mag": 0.0}, timestamp=100.0
    )
    errored = atn.StreamResult(
        name="volcano", score=0.9, veto=False, alerts=[], raw={}, error="provider_timeout", timestamp=101.0
    )
    no_data = atn._no_data_stream(
        "fire", source_id="nasa_firms", source_name="NASA FIRMS",
        source_url="https://firms.modaps.eosdis.nasa.gov/api/area/csv",
        blocker="missing_env:FIRMS_MAP_KEY",
    )
    monkeypatch.setattr(atn, "_FETCHERS", {
        "quake": lambda: good,
        "volcano": lambda: errored,
        "fire": lambda: no_data,
    })

    payload = atn.ATNMonitor().get_trading_impact()

    assert payload["veto"] is True
    assert payload["actionable"] is False
    assert payload["risk_factor"] is None
    assert payload["provenance"]["truth_status"] == "no_data"
    assert payload["provenance"]["non_actionable_streams"] == ["fire", "volcano"]
    assert payload["streams"]["volcano"]["received_at"] == 101.0
    assert payload["streams"]["volcano"]["source_timestamp"] is None
