"""The own-model chat server attaches the HNC gears without crashing.

``training/aureon_chat_server.py`` calls ``_with_gears()`` on every
``POST /v1/chat/completions``. ``_with_gears()`` builds its import roots with
``Path``, so a missing ``pathlib`` import raised ``NameError`` there, and the
handler's catch-all turned every completion into HTTP 500.

No model is loaded here: ``_with_gears()`` needs only the reply text.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SERVER = Path(__file__).resolve().parents[1] / "training" / "aureon_chat_server.py"


@pytest.fixture
def chat_server(tmp_path, monkeypatch):
    monkeypatch.setenv("AUREON_HNC_TRACE_PATH", str(tmp_path / "hnc_trace.jsonl"))
    spec = importlib.util.spec_from_file_location("_aureon_chat_server_under_test", _SERVER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_with_gears_attaches_a_receipt_and_keeps_the_reply(chat_server) -> None:
    body = chat_server.completion_body('{"claim_class": "C5"}', 3, 1, "aureon-7b-v65k")

    out = chat_server._with_gears(body, '{"claim_class": "C5"}')

    assert out["choices"][0]["message"]["content"] == '{"claim_class": "C5"}'
    gears = out["hnc_gears"]
    assert [gear["name"] for gear in gears["gears"]] == ["parse", "field", "auris", "qgita"]
    assert gears["parsed"] is True


def test_with_gears_on_unparseable_text_still_returns_a_receipt(chat_server) -> None:
    body = chat_server.completion_body("salad", 3, 1, "aureon-7b-v65k")

    out = chat_server._with_gears(body, "salad")

    assert out["choices"][0]["message"]["content"] == "salad"
    assert out["hnc_gears"]["parsed"] is False
