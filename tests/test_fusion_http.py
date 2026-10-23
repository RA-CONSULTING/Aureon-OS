"""Auth, rate limit, health, cache, and the local error sink. No network."""

from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request

import pytest

from aureon_fusion.http_service import reset_limits, serve

TOKEN = "fusion-test-token-16"


@pytest.fixture()
def server(monkeypatch, tmp_path):
    monkeypatch.setenv("AUREON_FUSION_API_TOKEN", TOKEN)
    monkeypatch.setenv("AUREON_FUSION_RATE_LIMIT", "30")
    monkeypatch.setenv("AUREON_FUSION_RATE_WINDOW_S", "60")
    monkeypatch.setenv("AUREON_FUSION_CACHE_TTL_S", "30")
    monkeypatch.setenv("AUREON_LOG_PATH", str(tmp_path / "app.log"))
    monkeypatch.setenv("AUREON_ERROR_LOG_PATH", str(tmp_path / "errors.log"))
    monkeypatch.delenv("AUREON_ERROR_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("AUREON_FUSION_ARM_LIVE", raising=False)
    monkeypatch.setenv("AUREON_LIVE_TRADING", "0")
    reset_limits()
    httpd = serve(port=0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    yield base, tmp_path
    httpd.shutdown()
    reset_limits()


def _get(url: str, token: str | None = None) -> tuple[int, dict | str]:
    headers = {}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            raw = response.read().decode("utf-8")
            content_type = response.headers.get("Content-Type", "")
            if "json" in content_type:
                return response.status, json.loads(raw)
            return response.status, raw
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            body = raw
        return exc.code, body


def test_health_is_open_and_disarmed(server):
    base, _tmp = server
    status, body = _get(base + "/healthz")
    assert status == 200
    assert body["status"] == "ok"
    assert body["live_trading"] is False
    assert body["paper_default"] is True
    assert TOKEN not in json.dumps(body)


def test_status_requires_the_env_token(server):
    base, _tmp = server
    status, body = _get(base + "/api/status")
    assert status == 401
    assert body["live_trading"] is False
    status, body = _get(base + "/api/status", token="wrong-token-value")
    assert status == 401
    status, body = _get(base + "/api/status", token=TOKEN)
    assert status == 200
    assert body["live_trading"] is False
    assert body["may_act"] is False
    assert body["paper_default"] is True
    assert body["cache"] == "miss"
    status, again = _get(base + "/api/status", token=TOKEN)
    assert status == 200
    assert again["cache"] == "hit"


def test_dashboard_requires_auth_and_says_trading_is_off(server):
    base, _tmp = server
    status, _body = _get(base + "/")
    assert status == 401
    status, page = _get(base + "/", token=TOKEN)
    assert status == 200
    assert "LIVE TRADING OFF" in page
    assert TOKEN not in page


def test_rate_limit_returns_429(server, monkeypatch):
    base, _tmp = server
    monkeypatch.setenv("AUREON_FUSION_RATE_LIMIT", "2")
    reset_limits()
    codes = []
    for _ in range(3):
        status, _body = _get(base + "/api/status", token=TOKEN)
        codes.append(status)
    assert codes == [200, 200, 429]


def test_error_sink_records_locally_and_does_not_call_a_webhook(server):
    base, tmp = server
    status, body = _get(base + "/error-test", token=TOKEN)
    assert status == 500
    assert body["error"] == "internal"
    lines = (tmp / "errors.log").read_text(encoding="utf-8").strip().splitlines()
    assert lines
    saved = json.loads(lines[-1])
    assert saved["error_type"] == "RuntimeError"
    assert saved["event"] == "exception"
    assert TOKEN not in lines[-1]
    assert "webhook_status" not in saved


def test_request_log_is_json_and_omits_the_token(server):
    base, tmp = server
    _get(base + "/healthz")
    log_path = tmp / "app.log"
    text = ""
    for _ in range(40):
        text = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
        if '"path": "/healthz"' in text:
            break
        time.sleep(0.05)
    assert TOKEN not in text
    records = [json.loads(line) for line in text.strip().splitlines()]
    record = next(item for item in records if item.get("path") == "/healthz")
    assert record["event"] == "request"
    assert record["live_trading"] is False
    assert "authorization" not in record


def test_server_refuses_to_start_when_the_token_is_missing(monkeypatch):
    monkeypatch.delenv("AUREON_FUSION_API_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="AUREON_FUSION_API_TOKEN"):
        serve(port=0)


def test_server_refuses_to_start_when_live_trading_is_armed(monkeypatch):
    monkeypatch.setenv("AUREON_FUSION_API_TOKEN", TOKEN)
    monkeypatch.setenv("AUREON_LIVE_TRADING", "1")
    with pytest.raises(RuntimeError, match="live trading"):
        serve(port=0)
