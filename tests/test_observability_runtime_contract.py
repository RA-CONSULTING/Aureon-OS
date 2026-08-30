from __future__ import annotations

import asyncio
import json
import logging
import re

from aureon.observability import (
    ASGIObservabilityMiddleware,
    correlation_scope,
    current_correlation_id,
    emit_local_event,
    install_flask_request_correlation,
    normalize_correlation_id,
    redact_observability_value,
    safe_observability_event,
)
from aureon.operator.metrics import OperatorMetrics


def test_correlation_ids_preserve_only_conservative_values() -> None:
    supplied = "edge-request_1234:abcd"
    assert normalize_correlation_id(supplied) == supplied

    generated = normalize_correlation_id("bad id\r\nx-injected: yes")
    assert re.fullmatch(r"[0-9a-f]{32}", generated)

    assert current_correlation_id() == ""
    with correlation_scope(supplied):
        assert current_correlation_id() == supplied
    assert current_correlation_id() == ""


def test_recursive_redaction_covers_keys_embedded_tokens_and_bounds() -> None:
    private_key = "-----BEGIN PRIVATE KEY-----\nvery-secret\n-----END PRIVATE KEY-----"
    value = {
        "authorization": "Bearer TOP-SECRET",
        "nested": {
            "apiKey": "openai-secret",
            "url": "https://alice:password@example.test/path",
            "message": "access_token=hunter2 and Bearer abc.def.ghi",
            "private": private_key,
        },
        "long": "x" * 3_000,
        "many": list(range(100)),
    }
    safe = redact_observability_value(value)
    encoded = json.dumps(safe)

    for forbidden in (
        "TOP-SECRET",
        "openai-secret",
        "password",
        "hunter2",
        "abc.def.ghi",
        "very-secret",
    ):
        assert forbidden not in encoded
    assert safe["authorization"] == "[REDACTED]"
    assert "[REDACTED]@example.test" in safe["nested"]["url"]
    assert safe["long"].endswith("[TRUNCATED]")
    assert safe["many"][-1] == "[TRUNCATED]"


def test_recursive_redaction_does_not_call_hostile_key_stringification() -> None:
    class HostileKey:
        def __str__(self) -> str:
            raise AssertionError("observability must not call arbitrary __str__")

    safe = redact_observability_value({HostileKey(): "ordinary"})
    assert safe == {"<HostileKey>": "ordinary"}

    generated = normalize_correlation_id(HostileKey())
    assert re.fullmatch(r"[0-9a-f]{32}", generated)


def test_exception_records_expose_type_not_message_or_traceback() -> None:
    secret = "sk-proj-super-secret-value"
    exc = RuntimeError(f"provider rejected {secret}")
    record = safe_observability_event(
        "provider_failure",
        correlation_id="request-12345678",
        fields={"password": "also-secret", "safe": "offline"},
        exception=exc,
    )
    encoded = json.dumps(record)

    assert record["exception_type"] == "RuntimeError"
    assert record["password"] == "[REDACTED]"
    assert record["safe"] == "offline"
    assert "provider rejected" not in encoded
    assert secret not in encoded
    assert "traceback" not in encoded.lower()


def test_operator_metrics_uses_sanitized_local_json(caplog) -> None:
    metrics = OperatorMetrics(enabled=False, structured_logs=True, trace_id="trace-12345678")
    with caplog.at_level(logging.INFO, logger="aureon.operator.metrics"):
        metrics._log(
            "provider_call",
            authorization="Bearer operator-secret",
            payload={"clientSecret": "nested-secret", "result": "held"},
            correlation_id="cannot-override",
        )
    record = json.loads(caplog.records[-1].message)

    assert record["event"] == "provider_call"
    assert record["correlation_id"] == "trace-12345678"
    assert record["authorization"] == "[REDACTED]"
    assert record["payload"]["clientSecret"] == "[REDACTED]"
    assert "operator-secret" not in caplog.records[-1].message
    assert "nested-secret" not in caplog.records[-1].message


def test_emit_local_event_never_raises_when_handler_is_broken() -> None:
    class BrokenLogger:
        def log(self, *_args, **_kwargs):
            raise OSError("local sink unavailable with password=secret")

    record = emit_local_event(
        BrokenLogger(),  # type: ignore[arg-type]
        logging.ERROR,
        "sink_failure",
        fields={"token": "do-not-log"},
    )
    assert record["token"] == "[REDACTED]"


def _raise_from_callsite_one() -> None:
    raise RuntimeError("same type, first secret")


def _raise_from_callsite_two() -> None:
    raise RuntimeError("same type, second secret")


def test_exception_fingerprint_groups_by_safe_code_metadata_not_message() -> None:
    records = []
    for raiser in (_raise_from_callsite_one, _raise_from_callsite_two):
        try:
            raiser()
        except RuntimeError as exc:
            records.append(safe_observability_event("failed", exception=exc))

    assert records[0]["exception_type"] == records[1]["exception_type"] == "RuntimeError"
    assert records[0]["exception_fingerprint"] != records[1]["exception_fingerprint"]
    assert "secret" not in json.dumps(records)


def test_flask_hook_validates_propagates_and_resets_request_id() -> None:
    from flask import Flask, jsonify

    app = Flask("observability-contract")
    install_flask_request_correlation(app)

    @app.get("/probe")
    def probe():
        return jsonify({"request_id": current_correlation_id()})

    client = app.test_client()
    valid = client.get("/probe", headers={"X-Request-ID": "flask-request-1234"})
    assert valid.status_code == 200
    assert valid.headers["X-Request-ID"] == "flask-request-1234"
    assert valid.get_json() == {"request_id": "flask-request-1234"}

    invalid = client.get("/probe", headers={"X-Request-ID": "not valid"})
    generated = invalid.headers["X-Request-ID"]
    assert re.fullmatch(r"[0-9a-f]{32}", generated)
    assert invalid.get_json() == {"request_id": generated}
    assert current_correlation_id() == ""


def test_flask_hook_replaces_raw_framework_exception_logging(caplog) -> None:
    from flask import Flask

    app = Flask("observability-error-contract")
    logger = logging.getLogger("test.observability.flask")
    install_flask_request_correlation(app, logger=logger)

    @app.get("/boom")
    def boom():
        raise RuntimeError("Bearer flask-provider-secret")

    with caplog.at_level(logging.ERROR):
        response = app.test_client().get(
            "/boom", headers={"X-Request-ID": "flask-error-1234"}
        )

    assert response.status_code == 500
    assert response.headers["X-Request-ID"] == "flask-error-1234"
    encoded = "\n".join(record.message for record in caplog.records)
    assert "flask-provider-secret" not in encoded
    event = json.loads(caplog.records[-1].message)
    assert event["event"] == "flask_unhandled_exception"
    assert event["exception_type"] == "RuntimeError"


def test_asgi_middleware_propagates_request_id_without_external_io() -> None:
    observed: dict[str, str] = {}

    async def app(scope, receive, send):
        observed["id"] = current_correlation_id()
        await send(
            {
                "type": "http.response.start",
                "status": 204,
                "headers": [(b"x-request-id", b"old")],
            }
        )
        await send({"type": "http.response.body", "body": b""})

    sent: list[dict] = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/readyz",
        "headers": [(b"x-request-id", b"edge-request-1234")],
    }
    asyncio.run(ASGIObservabilityMiddleware(app)(scope, receive, send))

    assert observed["id"] == "edge-request-1234"
    headers = sent[0]["headers"]
    assert [item for item in headers if item[0].lower() == b"x-request-id"] == [
        (b"x-request-id", b"edge-request-1234")
    ]
    assert current_correlation_id() == ""


def test_asgi_middleware_returns_generic_no_store_500_and_sanitizes_log(caplog) -> None:
    async def app(scope, receive, send):
        raise RuntimeError("Bearer provider-secret must never escape")

    sent: list[dict] = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/operator/respond",
        "headers": [(b"x-request-id", b"bad id\r\ninjected")],
    }
    logger = logging.getLogger("test.observability.asgi")
    with caplog.at_level(logging.ERROR, logger=logger.name):
        asyncio.run(ASGIObservabilityMiddleware(app, logger=logger)(scope, receive, send))

    start, body_message = sent
    assert start["status"] == 500
    headers = dict(start["headers"])
    assert headers[b"cache-control"] == b"no-store"
    request_id = headers[b"x-request-id"].decode("ascii")
    assert re.fullmatch(r"[0-9a-f]{32}", request_id)
    payload = json.loads(body_message["body"])
    assert payload == {
        "error": {"code": 500, "message": "internal server error", "request_id": request_id}
    }
    assert "provider-secret" not in caplog.records[-1].message
    assert "must never escape" not in caplog.records[-1].message
    assert json.loads(caplog.records[-1].message)["exception_type"] == "RuntimeError"


def test_asgi_partial_response_exception_is_closed_without_raw_reraise(caplog) -> None:
    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"partial", "more_body": True})
        raise ValueError("password=partial-response-secret")

    sent: list[dict] = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    scope = {"type": "http", "method": "GET", "path": "/stream", "headers": []}
    logger = logging.getLogger("test.observability.asgi.partial")
    with caplog.at_level(logging.ERROR, logger=logger.name):
        asyncio.run(ASGIObservabilityMiddleware(app, logger=logger)(scope, receive, send))

    assert sent[-1] == {"type": "http.response.body", "body": b"", "more_body": False}
    assert "partial-response-secret" not in caplog.records[-1].message
    assert json.loads(caplog.records[-1].message)["exception_type"] == "ValueError"
