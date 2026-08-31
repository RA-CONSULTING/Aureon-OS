"""
Aureon Watch — wearable PWA surface tests (the Ray-Ban path on the wrist).

Verifies the operator serves the self-contained watch app and its PWA assets,
and that the composed read-only /api/pulse never 500s. Offline, no network.
"""

from __future__ import annotations

import json

import pytest

pytest.importorskip("flask", reason="operator HTTP surface requires the `.[operator]` extra")

@pytest.fixture()
def client():
    # Resolve both the factory and its exact typed seam from the currently
    # loaded module. Other operator suites deliberately reload that module.
    import aureon.operator.operator_server as srv

    return srv.create_app(
        test_ingress_release=srv.TestOnlyOperatorIngressRelease(
            master_key=b"operator-wearable-route-test-key-material",
        )
    ).test_client()


def test_watch_index_served(client):
    r = client.get("/watch")
    assert r.status_code == 200
    assert "text/html" in r.headers["Content-Type"]
    body = r.get_data(as_text=True)
    assert 'data-screen="ask"' in body
    assert "/watch/watch.js" in body


def test_watch_app_script(client):
    r = client.get("/watch/watch.js")
    assert r.status_code == 200
    assert "javascript" in r.headers["Content-Type"]
    assert "EventSource" in r.get_data(as_text=True)  # streams from the operator


def test_watch_stylesheet(client):
    r = client.get("/watch/watch.css")
    assert r.status_code == 200
    assert "text/css" in r.headers["Content-Type"]


def test_watch_manifest_is_valid_pwa(client):
    r = client.get("/watch/manifest.webmanifest")
    assert r.status_code == 200
    manifest = json.loads(r.get_data(as_text=True))
    assert manifest["start_url"] == "/watch/"
    assert manifest["display"] == "standalone"
    assert any(i["src"].endswith("icon-512.png") for i in manifest["icons"])


def test_service_worker_scope_header(client):
    r = client.get("/watch/sw.js")
    assert r.status_code == 200
    assert r.headers.get("Service-Worker-Allowed") == "/"


def test_watch_icon_png(client):
    r = client.get("/watch/icon-192.png")
    assert r.status_code == 200
    assert r.headers["Content-Type"] == "image/png"


def test_missing_watch_asset_is_404(client):
    assert client.get("/watch/does-not-exist.js").status_code == 404


def test_cognition_stream_has_no_request_context_error(client):
    # The watch defaults to cognition mode, so its primary path is this SSE
    # stream. Regression: the generator must capture request args up front, not
    # read `request.*` lazily inside the generator ("Working outside of request
    # context" -> 500). Consuming the whole stream must not surface a 500 frame.
    r = client.get("/api/cognition/stream?prompt=ping")
    assert r.status_code == 200
    body = r.get_data(as_text=True)  # fully consumes the generator
    assert "event:" in body
    assert "Working outside of request context" not in body


def test_api_pulse_is_composed_and_never_500(client):
    r = client.get("/api/pulse")
    assert r.status_code == 200
    body = r.get_json()
    assert body["ok"] is True
    assert "providers" in body
    assert "status" in body        # composed platform status (degrades, never raises)
    assert "organism" in body      # composed organism payload (degrades, never raises)


def test_api_pulse_is_browser_valid_json(client):
    # The watch fetches /api/pulse from the browser, whose Response.json() rejects
    # bare Infinity/NaN tokens (which Python's json emits by default). Regression:
    # the body must be strict-JSON clean.
    raw = client.get("/api/pulse").get_data(as_text=True)
    assert "Infinity" not in raw and "NaN" not in raw
    # strict parser: reject the non-finite constants the browser also rejects
    def _boom(_):  # pragma: no cover - only runs if a constant slips through
        raise AssertionError("non-finite constant in /api/pulse body")
    json.loads(raw, parse_constant=_boom)
