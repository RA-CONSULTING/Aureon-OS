import os

import pytest

from aureon.core.aureon_env import (
    KRAKEN_REQUIRED_ENV,
    MASTER_KEY_ENV,
    decode_hnc_env_packets,
    enabled_credential_groups,
    env_presence,
    load_aureon_environment,
    missing_env,
)
from aureon.harmonic.hnc_quantum_packet_crypto import encode_env_packet


@pytest.fixture(autouse=True)
def _restore_environ():
    """load_aureon_environment WRITES os.environ — that is its job — and
    monkeypatch.delenv on an absent var registers no undo, so the credentials this
    module loads from its tmp .env files were leaking into every later test
    (test_system_health then saw phantom partial credentials — found by the B5
    sentinel run). Snapshot and restore the whole environment around each test."""
    saved = dict(os.environ)
    yield
    os.environ.clear()
    os.environ.update(saved)


def test_load_aureon_environment_from_explicit_file(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "ENABLE_ALPACA=true",
                "KRAKEN_API_KEY=key-from-file",
                "KRAKEN_API_SECRET=secret-from-file",
                "ALPACA_API_KEY=alpaca-key",
                "ALPACA_SECRET_KEY=alpaca-secret",
                "",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("AUREON_ENV_FILE", str(env_path))
    monkeypatch.delenv("KRAKEN_API_KEY", raising=False)
    monkeypatch.delenv("KRAKEN_API_SECRET", raising=False)
    monkeypatch.delenv("ALPACA_API_SECRET", raising=False)
    monkeypatch.delenv("ALPACA_SECRET", raising=False)
    monkeypatch.delenv("APCA_API_SECRET_KEY", raising=False)

    report = load_aureon_environment(tmp_path, override=False)

    assert report.loaded is True
    assert str(env_path) in report.loaded_paths
    assert {"target": "ALPACA_API_SECRET", "source": "ALPACA_SECRET_KEY"} in report.aliases_applied
    assert missing_env(KRAKEN_REQUIRED_ENV) == []
    assert missing_env(("ALPACA_API_SECRET", "APCA_API_SECRET_KEY")) == []
    assert enabled_credential_groups()["alpaca"] == ("ALPACA_API_KEY", "ALPACA_SECRET_KEY")
    assert env_presence(KRAKEN_REQUIRED_ENV)["KRAKEN_API_SECRET"]["set"] is True


def test_missing_env_reports_names_without_values(monkeypatch):
    monkeypatch.delenv("KRAKEN_API_KEY", raising=False)
    monkeypatch.delenv("KRAKEN_API_SECRET", raising=False)

    assert missing_env(KRAKEN_REQUIRED_ENV) == ["KRAKEN_API_KEY", "KRAKEN_API_SECRET"]
    assert env_presence(KRAKEN_REQUIRED_ENV)["KRAKEN_API_KEY"]["length"] == 0


def test_load_aureon_environment_decodes_hnc_env_packets(tmp_path, monkeypatch):
    master_key = "local-hnc-master-key-for-tests-32-bytes"
    token = encode_env_packet("packet-secret-from-file", master_key, env_key="KRAKEN_API_SECRET")
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                f"{MASTER_KEY_ENV}={master_key}",
                "KRAKEN_API_KEY=key-from-file",
                f"KRAKEN_API_SECRET={token}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("AUREON_ENV_FILE", str(env_path))
    monkeypatch.delenv("KRAKEN_API_KEY", raising=False)
    monkeypatch.delenv("KRAKEN_API_SECRET", raising=False)

    report = load_aureon_environment(tmp_path, override=False)

    assert report.loaded is True
    assert {"key": "KRAKEN_API_SECRET", "format": "hncqp1"} in report.packets_decoded
    assert report.packet_errors == []
    assert missing_env(KRAKEN_REQUIRED_ENV) == []
    assert env_presence(KRAKEN_REQUIRED_ENV)["KRAKEN_API_SECRET"]["hnc_packet"] is False


def test_decode_hnc_env_packets_leaves_packet_when_master_key_missing():
    env = {"KRAKEN_API_SECRET": "hncqp1:not-real"}

    decoded, errors = decode_hnc_env_packets(env)

    assert decoded == []
    assert errors == []
    assert env["KRAKEN_API_SECRET"] == "hncqp1:not-real"
