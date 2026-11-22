"""Focused contract tests for the bounded public demo/HNC HTTP service."""

from __future__ import annotations

import http.client
import importlib.util
import json
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "aureon_hf_demo_api", ROOT / "deploy" / "huggingface" / "demo_api.py"
)
assert SPEC is not None and SPEC.loader is not None
demo_api = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = demo_api
SPEC.loader.exec_module(demo_api)

TEST_REVISION = "a" * 40


def safe_env(**changes: str) -> dict[str, str]:
    env = dict(demo_api.PUBLIC_ENV)
    env["AUREON_MODEL_REVISION"] = TEST_REVISION
    env.update(changes)
    return env


def own_response(
    text: str = "Aureon reply",
    *,
    model: str = demo_api.MODEL,
    provider_mode: str = demo_api.PROVIDER_MODE,
    stop_reason: str = "end_turn",
) -> SimpleNamespace:
    raw = {
        "provider_mode": provider_mode,
        "model": model,
        "choices": [{"message": {"role": "assistant", "content": text}}],
        "usage": {"prompt_tokens": 4, "completion_tokens": 2, "total_tokens": 6},
        "hnc_gears": {"all_turned": True, "parsed": True, "gears": []},
    }
    return SimpleNamespace(
        raw=raw,
        model=model,
        stop_reason=stop_reason,
        usage=raw["usage"],
        text=text,
    )


class FakeAdapter:
    def __init__(self, response: SimpleNamespace | None = None) -> None:
        self.response = response or own_response()
        self.calls: list[dict] = []

    def prompt(self, messages, **kwargs):
        self.calls.append({"messages": messages, **kwargs})
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def make_app(
    *,
    adapter: FakeAdapter | None = None,
    env: dict[str, str] | None = None,
    repo_root: Path = ROOT,
    readiness_probe=None,
    hnc_status_provider=None,
    field_factory=None,
    clock=None,
):
    kwargs = {
        "env": safe_env() if env is None else env,
        "repo_root": repo_root,
        "adapter_factory": lambda: adapter or FakeAdapter(),
    }
    if readiness_probe is not None:
        kwargs["readiness_probe"] = readiness_probe
    if hnc_status_provider is not None:
        kwargs["hnc_status_provider"] = hnc_status_provider
    if field_factory is not None:
        kwargs["field_factory"] = field_factory
    if clock is not None:
        kwargs["clock"] = clock
    return demo_api.DemoApplication(**kwargs)


def generate(app, payload=b'{"prompt":"ping"}', client="127.0.0.1"):
    if not isinstance(payload, bytes):
        payload = json.dumps(payload).encode("utf-8")
    return app.generate(payload, content_type="application/json; charset=utf-8", client=client)


def ready_result(payload: dict) -> dict:
    return {"http_status": 200, "payload": payload, "error": None}


def model_ready(**changes) -> dict:
    payload = {
        "ready": True,
        "provider_mode": demo_api.PROVIDER_MODE,
        "model": demo_api.MODEL,
        "weight_sha256": demo_api.WEIGHT_SHA256,
        "weight_size_bytes": 13_990_806_664,
        "model_revision": TEST_REVISION,
        "params": 6_995_383_808,
        "vocab_size": 65_536,
        "eos_id": 1,
        "device": "cuda",
        "startup_generation_verified": True,
        "startup_generation": {"generated_tokens": 16},
    }
    payload.update(changes)
    return payload


def ready_probe(*, operator=None, model=None):
    operator = {"ready": True} if operator is None else operator
    model = model_ready() if model is None else model

    def probe(url: str, timeout: float) -> dict:
        assert 0 < timeout <= 2
        return ready_result(operator if url == demo_api.OPERATOR_READY_URL else model)

    return probe


def test_health_is_live_even_when_dependencies_are_not_ready() -> None:
    def unavailable(_url, _timeout):
        raise AssertionError("health must not probe dependencies")

    response = make_app(readiness_probe=unavailable).health()

    assert response.status == 200
    assert response.payload == {
        "ok": True,
        "live_trading": False,
        "orders_placed": 0,
        "provider_mode": "aureon_own_model",
    }


def test_generation_uses_own_adapter_and_preserves_attribution() -> None:
    adapter = FakeAdapter()
    app = make_app(adapter=adapter)

    response = generate(app, {"prompt": "hello", "max_tokens": 17})

    assert response.status == 200
    assert response.payload == {
        "provider_mode": "aureon_own_model",
        "model": "aureon-7b-v65k",
        "text": "Aureon reply",
        "stop_reason": "end_turn",
        "usage": {"prompt_tokens": 4, "completion_tokens": 2, "total_tokens": 6},
        "hnc_gears": {"all_turned": True, "parsed": True, "gears": []},
        "live_trading": False,
        "orders_placed": False,
    }
    assert adapter.calls == [
        {
            "messages": [{"role": "user", "content": "hello"}],
            "tools": None,
            "max_tokens": 17,
            "temperature": 0.0,
        }
    ]


def test_generation_defaults_to_32_tokens() -> None:
    adapter = FakeAdapter()

    response = generate(make_app(adapter=adapter))

    assert response.status == 200
    assert adapter.calls[0]["max_tokens"] == 32


@pytest.mark.parametrize(
    "response",
    [
        own_response(stop_reason="error"),
        own_response(model="borrowed-model"),
        own_response(provider_mode="external"),
        SimpleNamespace(raw=None, model=demo_api.MODEL, stop_reason="end_turn"),
    ],
)
def test_generation_adapter_failure_or_identity_mismatch_is_503(response) -> None:
    result = generate(make_app(adapter=FakeAdapter(response)))

    assert result.status == 503
    assert result.payload["ok"] is False
    assert "Aureon reply" not in json.dumps(result.payload)


def test_generation_adapter_exception_does_not_cross_http_boundary() -> None:
    adapter = FakeAdapter(RuntimeError("sensitive adapter detail"))

    result = generate(make_app(adapter=adapter))

    assert result.status == 503
    assert result.payload["error"]["code"] == "own_model_unavailable"
    assert "sensitive" not in json.dumps(result.payload)


def test_generation_wait_is_bounded() -> None:
    class SlowAdapter:
        def prompt(self, *_args, **_kwargs):
            time.sleep(0.2)
            return own_response()

    app = make_app(env=safe_env(AUREON_DEMO_GENERATE_TIMEOUT_S="0.1"))
    app.gateway.adapter_factory = SlowAdapter

    started = time.monotonic()
    result = generate(app)

    assert result.status == 503
    assert result.payload["error"]["code"] == "generation_timeout"
    assert time.monotonic() - started < 0.19


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        (b"not-json", "invalid_json"),
        (b"[]", "json_object"),
        (b'{"prompt":"x","tools":[]}', "json_object"),
        (b"{}", "prompt"),
        (b'{"prompt":"  "}', "prompt"),
        (json.dumps({"prompt": "x" * 4097}).encode(), "prompt"),
        (b'{"prompt":"x","max_tokens":true}', "max_tokens"),
        (b'{"prompt":"x","max_tokens":0}', "max_tokens"),
        (b'{"prompt":"x","max_tokens":65}', "max_tokens"),
        (b'{"prompt":"x","max_tokens":1.5}', "max_tokens"),
    ],
)
def test_generation_rejects_invalid_input(payload: bytes, code: str) -> None:
    adapter = FakeAdapter()

    result = generate(make_app(adapter=adapter), payload)

    assert result.status == 400
    assert result.payload["error"]["code"] == code
    assert adapter.calls == []


def test_generation_rejects_oversized_body_before_adapter_call() -> None:
    adapter = FakeAdapter()

    result = generate(make_app(adapter=adapter), b" " * (demo_api.MAX_BODY_BYTES + 1))

    assert result.status == 413
    assert result.payload["error"]["code"] == "body_too_large"
    assert adapter.calls == []


def test_generation_requires_json_content_type() -> None:
    result = make_app().generate(b'{"prompt":"x"}', content_type="text/plain", client="local")

    assert result.status == 415


class FakeClock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def test_token_bucket_is_per_client_and_has_retry_after() -> None:
    clock = FakeClock()
    adapter = FakeAdapter()
    app = make_app(adapter=adapter, clock=clock)

    assert generate(app, client="one").status == 200
    assert generate(app, client="one").status == 200
    limited = generate(app, client="one")

    assert limited.status == 429
    assert limited.headers["Retry-After"] == "10"
    assert limited.payload["retry_after"] == 10
    assert generate(app, client="two").status == 200
    assert len(adapter.calls) == 3

    clock.now += 10
    assert generate(app, client="one").status == 200


def test_readiness_requires_operator_model_identity_hash_and_startup() -> None:
    response = make_app(readiness_probe=ready_probe()).readiness()

    assert response.status == 200
    assert response.payload["ready"] is True
    assert response.payload["checks"]["model"]["ok"] is True
    assert response.payload["checks"]["operator"]["ok"] is True


@pytest.mark.parametrize(
    "changes",
    [
        {"ready": False},
        {"provider_mode": "external"},
        {"model": "borrowed"},
        {"model_revision": "b" * 40},
        {"weight_sha256": "0" * 64},
        {"weight_size_bytes": 1},
        {"params": 1},
        {"vocab_size": 32_000},
        {"eos_id": 2},
        {"device": "cpu"},
        {"startup_generation_verified": False},
        {"startup_generation": {"generated_tokens": 0}},
        {"startup_generation": {"generated_tokens": True}},
        {"startup_generation": {"generated_tokens": "16"}},
    ],
)
def test_readiness_fails_closed_for_each_model_requirement(changes: dict) -> None:
    response = make_app(readiness_probe=ready_probe(model=model_ready(**changes))).readiness()

    assert response.status == 503
    assert response.payload["ready"] is False
    assert response.payload["checks"]["model"]["ok"] is False


def test_readiness_requires_operator_ready() -> None:
    response = make_app(readiness_probe=ready_probe(operator={"ready": False})).readiness()

    assert response.status == 503
    assert response.payload["checks"]["operator"]["ready"] is False


def test_readiness_requires_an_immutable_configured_revision() -> None:
    env = safe_env(AUREON_MODEL_REVISION="main")

    response = make_app(env=env, readiness_probe=ready_probe()).readiness()

    assert response.status == 503
    assert response.payload["checks"]["model"]["checks"]["immutable_revision"] is False


def test_readiness_rejects_inherited_credentials_without_disclosing_values() -> None:
    secret = "inherited-exchange-secret"
    env = safe_env(KRAKEN_API_SECRET=secret)

    response = make_app(env=env, readiness_probe=ready_probe()).readiness()

    assert response.status == 503
    assert response.payload["checks"]["public_posture"]["checks"]["credentials_absent"] is False
    assert secret not in json.dumps(response.payload)


@pytest.mark.parametrize("name", demo_api.PUBLIC_ENV)
def test_readiness_rejects_unsafe_public_posture_without_disclosing_values(name: str) -> None:
    secret_value = "unsafe-value-that-must-not-leak"
    env = safe_env(**{name: secret_value})

    response = make_app(env=env, readiness_probe=ready_probe()).readiness()

    assert response.status == 503
    assert response.payload["checks"]["public_posture"]["checks"][name] is False
    assert secret_value not in json.dumps(response.payload)


def test_readiness_probe_failure_is_process_safe() -> None:
    def probe(url: str, _timeout: float) -> dict:
        if url == demo_api.OPERATOR_READY_URL:
            return {"http_status": None, "payload": None, "error": "TimeoutError"}
        return ready_result(model_ready())

    response = make_app(readiness_probe=probe).readiness()

    assert response.status == 503
    assert response.payload["checks"]["operator"]["error"] == "TimeoutError"
    assert "traceback" not in json.dumps(response.payload).lower()


def test_readiness_contains_raised_probe_exception() -> None:
    def probe(url: str, _timeout: float) -> dict:
        if url == demo_api.OPERATOR_READY_URL:
            raise OSError("private upstream detail")
        return ready_result(model_ready())

    response = make_app(readiness_probe=probe).readiness()

    assert response.status == 503
    assert response.payload["checks"]["operator"]["error"] == "OSError"
    assert "private upstream detail" not in json.dumps(response.payload)


def test_demo_status_has_exact_route_and_no_secret_environment_values() -> None:
    env = safe_env(UNRELATED_SECRET="never-publish-this")

    response = make_app(env=env).demo_status()

    assert response.payload["route"] == {
        "base_url": "http://127.0.0.1:11435/v1",
        "generate": "http://127.0.0.1:11435/v1/chat/completions",
        "readyz": "http://127.0.0.1:11435/readyz",
    }
    assert response.payload["external_providers"] is False
    assert "never-publish" not in json.dumps(response.payload)


def test_hnc_status_uses_existing_modules_and_removes_paths(monkeypatch) -> None:
    from aureon.core import hnc_field
    from aureon_fusion import hnc_core

    monkeypatch.setattr(
        hnc_core,
        "status",
        lambda: {
            "organ": "hnc_core",
            "history_path": "C:/private/history.json",
            "params_path": "C:/private/params.json",
            "memory_db": "C:/private/memory.sqlite",
            "last_gamma": 0.9,
        },
    )
    monkeypatch.setattr(hnc_core, "organ_running", lambda: (False, "not running"))
    monkeypatch.setattr(
        hnc_field,
        "read_canonical_field",
        lambda: SimpleNamespace(to_dict=lambda: {"available": False, "coherence_gamma": None}),
    )

    response = make_app(hnc_status_provider=demo_api._default_hnc_status).hnc_status()

    assert response.status == 200
    assert response.payload["organ"] == {"organ": "hnc_core", "last_gamma": 0.9, "available": True}
    assert response.payload["organ_running"]["running"] is False
    assert response.payload["canonical_field"] == {"available": False, "coherence_gamma": None}
    assert "C:/private" not in json.dumps(response.payload)


def _write_replays(root: Path, brain: dict | None, organism: dict | None = None) -> None:
    brain_path = root / demo_api.BRAIN_RECORD
    organism_path = root / demo_api.ORGANISM_RECORD
    brain_path.parent.mkdir(parents=True, exist_ok=True)
    organism_path.parent.mkdir(parents=True, exist_ok=True)
    if brain is not None:
        brain_path.write_text(json.dumps(brain), encoding="utf-8")
    if organism is not None:
        organism_path.write_text(json.dumps(organism), encoding="utf-8")


def brain_record() -> dict:
    return {
        "hnc": {
            "steps": 3,
            "series": [0.1, 0.2, 0.3],
            "coherence": 0.8,
            "lambda_last": 0.3,
            "state": "coherent",
            "multiverse_extension": {
                "steps": 3,
                "series": [1.1, 1.2, 1.3],
                "coherence": 0.7,
                "lambda_last": 1.3,
                "state": "locked",
            },
        }
    }


class FakeField:
    def __init__(self, enable_multiverse: bool = True) -> None:
        self.enable_multiverse = enable_multiverse
        self.coherence = 0.7 if enable_multiverse else 0.8
        self.state = SimpleNamespace(
            name="LOCKED" if enable_multiverse else "COHERENT",
            value="locked" if enable_multiverse else "coherent",
        )
        self.values = iter([1.1, 1.2, 1.3] if enable_multiverse else [0.1, 0.2, 0.3])

    def step(self) -> float:
        return next(self.values)


def test_hnc_replay_matches_both_paths_without_loading_model(tmp_path: Path) -> None:
    _write_replays(tmp_path, brain_record())
    constructions = []

    def factory(**kwargs):
        constructions.append(kwargs)
        return FakeField(**kwargs)

    response = make_app(repo_root=tmp_path, field_factory=factory).hnc_replay()

    assert response.status == 200
    assert response.payload["status"] == "match"
    assert response.payload["match"] is True
    assert response.payload["rerun"]["multiverse_off"]["match"] is True
    assert response.payload["rerun"]["multiverse_on"]["match"] is True
    assert response.payload["record"]["label"] == "cited"
    assert response.payload["rerun"]["label"] == "inferred"
    assert constructions == [{"enable_multiverse": False}, {}]


def test_hnc_replay_mismatch_is_explicit(tmp_path: Path) -> None:
    record = brain_record()
    record["hnc"]["multiverse_extension"]["coherence"] = 0.123
    _write_replays(tmp_path, record)

    response = make_app(repo_root=tmp_path, field_factory=FakeField).hnc_replay()

    assert response.payload["status"] == "mismatch"
    assert response.payload["match"] is False
    assert response.payload["rerun"]["multiverse_off"]["match"] is True
    assert response.payload["rerun"]["multiverse_on"]["checks"]["coherence"] is False


def test_hnc_replay_missing_is_not_a_pass_and_does_not_construct_field(tmp_path: Path) -> None:
    def forbidden(**_kwargs):
        raise AssertionError("missing record must not load the field")

    response = make_app(repo_root=tmp_path, field_factory=forbidden).hnc_replay()

    assert response.payload["status"] == "missing"
    assert response.payload["available"] is False
    assert response.payload["match"] is False
    assert "rerun" not in response.payload


def test_organism_replay_returns_record_and_separates_synthetic_faults(tmp_path: Path) -> None:
    organism = {
        "connectivity": {"roster": 2, "connected": 2},
        "self_model": {"fault": {"origin": "synthetic", "seed": 20261024, "detection_rate": 1.0}},
        "live_trading": False,
    }
    _write_replays(tmp_path, None, organism)

    response = make_app(repo_root=tmp_path).organism_replay()

    assert response.payload["record"]["data"] == organism
    assert response.payload["recorded_circulation"]["data"] == organism["connectivity"]
    assert "not newly sampled telemetry" in response.payload["recorded_circulation"]["label"]
    assert response.payload["synthetic_fault_block"]["seed"] == 20261024
    assert response.payload["synthetic_fault_block"]["data"] == organism["self_model"]["fault"]
    assert "not live" in response.payload["synthetic_fault_block"]["label"]


@pytest.fixture()
def loopback_server():
    adapter = FakeAdapter()
    app = make_app(
        adapter=adapter,
        readiness_probe=ready_probe(),
        hnc_status_provider=lambda: {
            "organ": {"available": True},
            "organ_running": {"available": True, "running": False},
            "canonical_field": {"available": False},
        },
        field_factory=FakeField,
    )
    server = demo_api.create_server(port=0, application=app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server.server_address[1], adapter
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


def http_request(port: int, method: str, path: str, body: bytes | None = None, headers=None):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    try:
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        raw = response.read()
        content_type = response.getheader("Content-Type", "")
        if not raw:
            payload = None
        else:
            payload = json.loads(raw) if content_type.startswith("application/json") else raw.decode("utf-8")
        return response.status, dict(response.getheaders()), payload
    finally:
        connection.close()


def test_real_loopback_http_health_generation_and_secure_headers(loopback_server) -> None:
    port, adapter = loopback_server

    status, headers, health = http_request(port, "GET", "/healthz")
    assert status == 200
    assert health["ok"] is True
    assert headers["Cache-Control"] == "no-store"
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert "Access-Control-Allow-Origin" not in headers

    status, headers, generated = http_request(
        port,
        "POST",
        "/api/demo/generate",
        b'{"prompt":"loopback","max_tokens":9}',
        {"Content-Type": "application/json"},
    )
    assert status == 200
    assert generated["provider_mode"] == "aureon_own_model"
    assert generated["text"] == "Aureon reply"
    assert adapter.calls[0]["max_tokens"] == 9
    assert headers["Cache-Control"] == "no-store"


def test_real_loopback_http_404_405_and_hnc_view(loopback_server) -> None:
    port, _adapter = loopback_server

    assert http_request(port, "GET", "/not-a-route")[0] == 404
    status, headers, _body = http_request(port, "GET", "/api/demo/generate")
    assert status == 405
    assert headers["Allow"] == "POST"
    assert http_request(port, "POST", "/healthz", b"{}")[0] == 405
    assert http_request(port, "OPTIONS", "/healthz")[0] == 405
    assert http_request(port, "CONNECT", "/healthz")[0] == 405
    status, headers, body = http_request(port, "HEAD", "/healthz")
    assert status == 200
    assert body is None
    assert int(headers["Content-Length"]) > 0

    for path in ("/hnc", "/hnc/"):
        status, headers, html = http_request(port, "GET", path)
        assert status == 200
        assert headers["Content-Type"].startswith("text/html")
        assert headers["Cache-Control"] == "no-store"
        assert '<html lang="en">' in html
        assert "textContent" in html
        assert "/api/hnc/replay" in html
        assert "/api/hnc/organism-replay" in html
        assert "innerHTML" not in html


def test_real_loopback_oversized_content_length_is_413(loopback_server) -> None:
    port, adapter = loopback_server

    status, _headers, body = http_request(
        port,
        "POST",
        "/api/demo/generate",
        b"{}",
        {"Content-Type": "application/json", "Content-Length": str(demo_api.MAX_BODY_BYTES + 1)},
    )

    assert status == 413
    assert body["error"]["code"] == "body_too_large"
    assert adapter.calls == []


def test_server_refuses_non_loopback_bind() -> None:
    with pytest.raises(ValueError, match="loopback"):
        demo_api.create_server(host="0.0.0.0", port=0)
