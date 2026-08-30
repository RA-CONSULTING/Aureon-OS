"""Strict-JSON regression tests for browser-facing SaaS responses."""

from __future__ import annotations

import json

import pytest

from aureon.core.jsonsafe import json_safe


def _reject_nonfinite(value: str) -> None:
    raise AssertionError(f"non-finite JSON constant emitted: {value}")


def test_json_safe_recurses_without_mutating_finite_values() -> None:
    source = {
        "finite": 1.25,
        "nested": [float("nan"), (float("inf"), float("-inf"))],
    }

    assert json_safe(source) == {
        "finite": 1.25,
        "nested": [None, [None, None]],
    }


def test_cognition_route_emits_browser_parseable_json(monkeypatch) -> None:
    flask = pytest.importorskip("flask", reason="SaaS gateway requires Flask")
    from aureon.saas import cognitive
    from aureon.saas.gateway import register_saas_routes

    monkeypatch.delenv("AUREON_SUPABASE_JWT_SECRET", raising=False)
    monkeypatch.setattr(
        cognitive,
        "field_surface",
        lambda: {"coherence": float("nan"), "energy": float("inf")},
    )
    app = flask.Flask(__name__)
    register_saas_routes(app)

    response = app.test_client().get("/api/cognition/field")

    assert response.status_code == 200
    payload = json.loads(response.get_data(as_text=True), parse_constant=_reject_nonfinite)
    assert payload == {"surface": "field", "data": {"coherence": None, "energy": None}}
