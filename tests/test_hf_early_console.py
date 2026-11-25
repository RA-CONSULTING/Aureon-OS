"""Fast public-console behavior; no GPU, model, or network is required."""

import http.client
import json
import threading
from pathlib import Path
from unittest.mock import patch

from deploy.huggingface import early_console


def _serve():
    server = early_console.ThreadingHTTPServer(("127.0.0.1", 0), early_console.ConsoleHandler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _request(port, method="GET", path="/"):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
    connection.request(method, path)
    response = connection.getresponse()
    body = response.read()
    connection.close()
    return response, body


def test_health_is_independent_of_dependencies():
    with patch.object(early_console, "public_status", side_effect=AssertionError("must not probe")):
        server, _thread = _serve()
    try:
        response, body = _request(server.server_port, path="/healthz")
        payload = json.loads(body)
        assert response.status == 200
        assert payload == {
            "ok": True, "service": "aureon-public-console", "live_trading": False,
        }
    finally:
        server.shutdown()
        server.server_close()


def test_console_is_available_and_honest_when_model_is_not_ready():
    with patch.object(
        early_console, "public_status",
        return_value={"state": "starting", "ready": False, "blocker": "URLError"},
    ):
        server, _thread = _serve()
        try:
            response, body = _request(server.server_port)
        finally:
            server.shutdown()
            server.server_close()
    text = body.decode("utf-8")
    assert response.status == 200
    assert "Organism is starting / evidence unavailable" in text
    assert "All systems ready" not in text
    assert "HNC / Auris / QGITA" in text
    assert "No live trading" in text


def test_ready_status_requires_verified_model_and_operator():
    with patch.object(early_console, "public_status", return_value={
        "ready": True, "state": "ready", "checks": {
            "model": {"ok": True}, "operator": {"ok": True}, "public_posture": {"ok": True},
        },
    }):
        server, _thread = _serve()
        try:
            _response, body = _request(server.server_port)
        finally:
            server.shutdown()
            server.server_close()
    text = body.decode("utf-8")
    assert "All systems ready" in text
    assert text.count("data-component=") == 4
    assert "data-component='organism'" in text


def test_console_does_not_expose_generation_credentials_or_mutations():
    with patch.object(early_console, "public_status", return_value={"ready": False}):
        server, _thread = _serve()
        try:
            response, _body = _request(server.server_port, "POST", "/api/demo/generate")
            unknown, _body = _request(server.server_port, path="/api/status")
        finally:
            server.shutdown()
            server.server_close()
    assert response.status == 405
    assert unknown.status == 404


def test_readiness_requires_real_organism_gear_evidence():
    from deploy.huggingface import demo_api

    gears = [
        {"name": "field", "turned": True, "engaged": True},
        {"name": "auris", "turned": True, "engaged": True},
        {"name": "qgita", "turned": True, "engaged": True},
    ]
    app = demo_api.DemoApplication(
        env=safe_public_env(),
        readiness_probe=lambda url, timeout: {"http_status": 200, "payload": (
            {"ready": True} if url == demo_api.OPERATOR_READY_URL else model_payload()
        )},
        organism_provider=lambda: {"all_turned": True, "all_engaged": True, "gears": gears},
    )
    assert app.readiness().status == 200
    app.organism_provider = lambda: {"all_turned": True, "all_engaged": False, "gears": []}
    response = app.readiness()
    assert response.status == 503
    assert response.payload["checks"]["organism"]["ok"] is False


def safe_public_env():
    from deploy.huggingface import demo_api

    return {**demo_api.PUBLIC_ENV, "AUREON_MODEL_REVISION": "a" * 40}


def model_payload():
    return {
        "ready": True, "provider_mode": "aureon_own_model", "model": "aureon-7b-v65k",
        "model_revision": "a" * 40,
        "weight_sha256": "48487f800623474ab99371d71b369694cae64f8ebc4ef038019c7e60da3d45bb",
        "weight_size_bytes": 13_990_806_664, "params": 6_995_383_808,
        "vocab_size": 65_536, "eos_id": 1, "device": "cuda",
        "startup_generation_verified": True, "startup_generation": {"generated_tokens": 16},
    }


def test_config_has_early_health_root_and_strict_readiness_separation():
    root = Path(__file__).resolve().parents[1]
    entrypoint = (root / "deploy/huggingface/entrypoint.sh").read_text(encoding="utf-8")
    nginx = (root / "deploy/huggingface/nginx.conf").read_text(encoding="utf-8")
    assert entrypoint.index("early_console.py") < entrypoint.index("exec /usr/bin/supervisord")
    assert "proxy_pass http://early_console" in nginx
    assert "server 127.0.0.1:7860 max_fails=0" in nginx
    assert "location = /api/console/status" in nginx
    assert "location = /readyz" in nginx
    assert "proxy_pass http://demo_api" in nginx
    assert "location = /api/demo/generate" in nginx
