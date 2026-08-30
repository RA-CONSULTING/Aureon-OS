from __future__ import annotations

import json
import logging
import sys
from types import SimpleNamespace

from aureon.operator.operator_server import create_app


def _app():
    return create_app(operator=SimpleNamespace(providers={}), cognition=object())


def test_operator_propagates_validated_request_id_on_open_probe() -> None:
    response = _app().test_client().get(
        "/healthz", headers={"X-Request-ID": "operator-probe-1234"}
    )
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "operator-probe-1234"


def test_operator_500_is_generic_correlated_and_locally_sanitized(caplog) -> None:
    app = _app()

    @app.get("/_observability_test_boom")
    def boom():
        raise RuntimeError("Bearer operator-provider-secret")

    with caplog.at_level(logging.ERROR):
        response = app.test_client().get(
            "/_observability_test_boom",
            headers={"X-Request-ID": "operator-error-1234"},
        )

    assert response.status_code == 500
    assert response.headers["X-Request-ID"] == "operator-error-1234"
    assert response.headers["Cache-Control"] == "no-store"
    assert response.get_json() == {
        "error": {
            "code": 500,
            "message": "internal server error",
            "request_id": "operator-error-1234",
        }
    }
    encoded_logs = "\n".join(record.message for record in caplog.records)
    assert "operator-provider-secret" not in encoded_logs
    events = [json.loads(record.message) for record in caplog.records if record.message.startswith("{")]
    assert [event["event"] for event in events] == ["flask_unhandled_exception"]
    assert {event["exception_type"] for event in events} == {"RuntimeError"}


def test_operator_readiness_uses_fixed_codes_and_sanitized_events(monkeypatch, caplog) -> None:
    def fail_repo_index():
        raise RuntimeError("password=repo-index-secret")

    def fail_real_data_policy():
        raise ValueError("Bearer real-data-secret")

    monkeypatch.setitem(
        sys.modules,
        "aureon.operator.repo_index",
        SimpleNamespace(get_operator_repo_index=fail_repo_index),
    )
    monkeypatch.setitem(
        sys.modules,
        "aureon.operator.connections_api",
        SimpleNamespace(_real_data_policy_summary=fail_real_data_policy),
    )

    with caplog.at_level(logging.WARNING, logger="aureon.operator.server"):
        response = _app().test_client().get(
            "/readyz", headers={"X-Request-ID": "operator-ready-1234"}
        )

    assert response.status_code == 503
    assert response.headers["X-Request-ID"] == "operator-ready-1234"
    checks = response.get_json()["checks"]
    assert checks["repo_index_error"] == "repo_index_unavailable"
    assert checks["real_data_policy"] == {
        "probe_report_status": "unavailable",
        "error": "real_data_policy_unavailable",
    }
    encoded = response.get_data(as_text=True) + "\n" + "\n".join(
        record.message for record in caplog.records
    )
    assert "repo-index-secret" not in encoded
    assert "real-data-secret" not in encoded
