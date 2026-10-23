"""The Nexus field reader stays source-bound and does not act."""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "sources" / "NEXUS-LIVE-FEED-" / "organism" / "public_field.py"
SPEC = importlib.util.spec_from_file_location("nexus_public_field", MODULE_PATH)
assert SPEC and SPEC.loader
FIELD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FIELD)


def test_object_row_is_hashed_and_cannot_act():
    body = json.dumps([{"time_tag": "2026-10-15T06:00:00", "Kp": 1.33, "a_running": 5, "station_count": 8}]).encode()
    observed = FIELD.observe_planetary_k_index(lambda url: body if url == FIELD.SOURCE else (_ for _ in ()).throw(ValueError(url)))
    assert observed["schema"] == "nexus.public-field.v1"
    assert observed["kp"] == 1.33
    assert observed["may_act"] is False
    assert observed["generated_values"] is False
    assert observed["source"] == FIELD.SOURCE


def test_noaa_header_table_uses_the_last_row():
    body = json.dumps(
        [
            ["time_tag", "Kp", "a_running", "station_count"],
            ["2026-10-14 21:00:00", "2.00", "7", "8"],
            ["2026-10-15 06:00:00", "1.33", "5", "8"],
        ]
    ).encode()
    observed = FIELD.observe_planetary_k_index(lambda _url: body)
    assert observed["time_tag"] == "2026-10-15 06:00:00"
    assert observed["kp"] == 1.33
    assert observed["station_count"] == 8.0
    assert observed["may_act"] is False
