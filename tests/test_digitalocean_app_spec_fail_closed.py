from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_SPEC = REPO_ROOT / ".do" / "app.yaml"


def _spec() -> dict[str, object]:
    loaded = yaml.safe_load(APP_SPEC.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def test_digitalocean_service_is_single_owner_and_fail_closed() -> None:
    spec = _spec()
    services = spec["services"]
    assert isinstance(services, list)
    assert len(services) == 1
    service = services[0]

    assert service["instance_count"] == 1
    assert "autoscaling" not in service
    assert service["source_dir"] == "/"
    assert (REPO_ROOT / service["dockerfile_path"]).is_file()

    envs = {item["key"]: item for item in service["envs"]}
    expected = {
        "AUREON_ENABLE_AUTONOMOUS_CONTROL": "1",
        "LIVE": "0",
        "DRY_RUN": "1",
        "AUREON_LIVE_TRADING": "0",
        "KRAKEN_DRY_RUN": "true",
        "BINANCE_DRY_RUN": "true",
        "ALPACA_DRY_RUN": "true",
        "CAPITAL_DEMO": "true",
    }
    for key, value in expected.items():
        assert envs[key]["scope"] == "RUN_TIME"
        assert envs[key]["value"] == value


def test_digitalocean_secret_values_remain_dashboard_managed() -> None:
    service = _spec()["services"][0]
    envs = {item["key"]: item for item in service["envs"]}
    secret_keys = {
        "KRAKEN_API_KEY",
        "KRAKEN_API_SECRET",
        "BINANCE_API_KEY",
        "BINANCE_API_SECRET",
        "ALPACA_API_KEY",
        "ALPACA_SECRET_KEY",
        "CAPITAL_API_KEY",
        "CAPITAL_IDENTIFIER",
        "CAPITAL_PASSWORD",
    }

    for key in secret_keys:
        assert envs[key]["type"] == "SECRET"
        assert "value" not in envs[key]


def test_digitalocean_redis_binding_and_health_contract_parse() -> None:
    service = _spec()["services"][0]
    envs = {item["key"]: item for item in service["envs"]}

    assert envs["AUREON_REDIS_URL"]["value"] == "${db.REDIS_URL}"
    assert service["health_check"]["http_path"] == "/health"
    assert service["http_port"] == 8080
    databases = _spec()["databases"]
    assert databases == [
        {
            "name": "db",
            "engine": "REDIS",
            "production": True,
            "version": "7",
        }
    ]
