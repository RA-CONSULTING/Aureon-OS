"""The five repository layers join on real observations and stay unable to act."""

from __future__ import annotations

import json
from pathlib import Path

from aureon.organism.repository_layers import compose_repository_layers

FIELD = {
    "time_tag": "2026-10-15T06:00:00",
    "Kp": 1.33,
    "a_running": 5,
    "station_count": 8,
}
MARKET = {"symbol": "BTCUSDT", "price": "81290.01000000"}


def _field(_url: str) -> bytes:
    return json.dumps([{"time_tag": "2026-10-14T21:00:00", "Kp": 2.0, "a_running": 7, "station_count": 8}, FIELD]).encode()


def _market(_url: str) -> bytes:
    return json.dumps(MARKET).encode()


_FIELD_MODULE = '''
import hashlib, json
SOURCE = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"
def observe_planetary_k_index(transport=None):
    raw = transport(SOURCE)
    row = json.loads(raw)[-1]
    return {"schema": "nexus.public-field.v1", "source": SOURCE, "time_tag": row["time_tag"],
            "kp": row["Kp"], "a_running": row["a_running"], "station_count": row["station_count"],
            "payload_sha256": hashlib.sha256(raw).hexdigest(), "generated_values": False, "may_act": False}
'''

_MARKET_MODULE = '''
import hashlib, json
SOURCE = "https://data-api.binance.vision/api/v3/ticker/price?symbol=BTCUSDT"
def observe_public_price(transport=None):
    raw = transport(SOURCE)
    payload = json.loads(raw)
    return {"schema": "sero.public-market.v1", "source": SOURCE, "symbol": payload["symbol"],
            "price": payload["price"], "order_count": 0, "payload_sha256": hashlib.sha256(raw).hexdigest(),
            "generated_values": False, "may_act": False}
'''


def test_sample_evidence_stays_out_and_public_readings_keep_their_source(tmp_path: Path):
    repos = tmp_path
    nexus = repos / "NEXUS-LIVE-FEED-" / "organism"
    sero = repos / "Aureon-Trading--Project-Sero" / "organism"
    skaila = repos / "skaila-journey-platform" / "spec" / "build-pack"
    founder = repos / "aureon-founder-mirror"
    nexus.mkdir(parents=True)
    sero.mkdir(parents=True)
    skaila.mkdir(parents=True)
    founder.mkdir()
    (nexus / "public_field.py").write_text(_FIELD_MODULE, encoding="utf-8")
    (sero / "public_market.py").write_text(_MARKET_MODULE, encoding="utf-8")
    (skaila / "aureon-gate-policy.yaml").write_text("gates: hold\n", encoding="utf-8")
    (founder / "README.md").write_text(
        "Draft-only: never sends, spends or signs. All reused parts on HOLD until reviewed.\n",
        encoding="utf-8",
    )

    joined = compose_repository_layers(
        repos_root=repos,
        evidence={"authority": "synthetic", "gate": "HOLD", "readiness": 62, "adoption": 43},
        field_transport=_field,
        market_transport=_market,
    )

    assert joined["schema"] == "aureon.repository-layers.v1"
    assert joined["status"] == "hold"
    assert joined["may_act"] is False
    assert joined["action_eligible"] is False
    assert joined["economic_mutation"] is False
    assert joined["generated_values"] is False
    by_id = {layer["id"]: layer for layer in joined["layers"]}
    assert by_id["skaila"]["truth_status"] == "no_data"
    assert by_id["skaila"]["reason"] == "sample_or_synthetic_evidence_excluded"
    assert by_id["skaila"]["observation"] is None
    assert by_id["nexus"]["truth_status"] == "real_observed"
    assert by_id["nexus"]["observation"]["kp"] == 1.33
    assert by_id["nexus"]["observation"]["source"].startswith("https://services.swpc.noaa.gov/")
    assert by_id["sero"]["observation"]["price"] == "81290.01000000"
    assert by_id["sero"]["observation"]["order_count"] == 0
    assert by_id["founder-mirror"]["observation"]["sends"] is False
    assert by_id["aureon-os"]["gate"] == "HOLD"
    assert by_id["aureon-os"]["may_act"] is False


def test_an_observation_that_claims_authority_is_rejected(tmp_path: Path):
    module_path = tmp_path / "NEXUS-LIVE-FEED-" / "organism"
    module_path.mkdir(parents=True)
    (module_path / "public_field.py").write_text(
        "SOURCE = 'https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json'\n"
        "def observe_planetary_k_index(transport=None):\n"
        "    return {'schema': 'nexus.public-field.v1', 'source': SOURCE, 'generated_values': False,\n"
        "            'may_act': True, 'payload_sha256': 'a' * 64}\n",
        encoding="utf-8",
    )
    (tmp_path / "Aureon-Trading--Project-Sero" / "organism").mkdir(parents=True)
    (tmp_path / "aureon-founder-mirror").mkdir()

    joined = compose_repository_layers(repos_root=tmp_path, field_transport=lambda _url: b"{}")
    nexus = next(layer for layer in joined["layers"] if layer["id"] == "nexus")
    assert nexus["may_act"] is False
    assert nexus["truth_status"] == "no_data"
    assert joined["may_act"] is False
