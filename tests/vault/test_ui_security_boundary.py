from __future__ import annotations

import base64
from io import BytesIO
from types import SimpleNamespace
import warnings
from collections.abc import Iterator
from typing import Any

import pytest
from flask import Flask
from werkzeug.test import EnvironBuilder

pytest.importorskip("flask")

from aureon.harmonic.phi_bridge_mesh import get_phi_bridge_mesh, reset_phi_bridge_mesh
from aureon.vault import AureonSelfFeedbackLoop
from aureon.vault.ui.server import (
    VAULT_UI_AUTH_ENV,
    VAULT_UI_MAX_HEADER_BYTES,
    VAULT_UI_MAX_REQUEST_BYTES,
    VaultUIRedactedRequestHandler,
    create_app,
    run_server,
    vault_ui_security_preflight,
)


TOKEN = "vault-ui-test-" + ("T" * 48)
ROTATED_TOKEN = "vault-ui-rotated-" + ("R" * 48)
HNC_KEY = base64.urlsafe_b64encode(b"V" * 32).decode().rstrip("=")
AUTH = {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture(autouse=True)
def _reset_mesh() -> Iterator[None]:
    reset_phi_bridge_mesh()
    yield
    reset_phi_bridge_mesh()


def _configure_security(monkeypatch: pytest.MonkeyPatch, *, hnc_key: bool = True) -> None:
    monkeypatch.setenv(VAULT_UI_AUTH_ENV, TOKEN)
    if hnc_key:
        monkeypatch.setenv("AUREON_HNC_PACKET_MASTER_KEY", HNC_KEY)
    else:
        monkeypatch.delenv("AUREON_HNC_PACKET_MASTER_KEY", raising=False)
        monkeypatch.delenv("HNC_PACKET_MASTER_KEY", raising=False)


def _client(monkeypatch: pytest.MonkeyPatch, *, hnc_key: bool = True):
    _configure_security(monkeypatch, hnc_key=True)
    app = create_app(base_interval_s=0.01)
    loop = app.config["AUREON_LOOP"]
    app.testing = True
    if not hnc_key:
        monkeypatch.delenv("AUREON_HNC_PACKET_MASTER_KEY", raising=False)
        monkeypatch.delenv("HNC_PACKET_MASTER_KEY", raising=False)
    return app, app.test_client(), loop


def test_bind_preflight_requires_loopback_bearer_hnc_key_and_no_debug(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(VAULT_UI_AUTH_ENV, raising=False)
    monkeypatch.delenv("AUREON_HNC_PACKET_MASTER_KEY", raising=False)
    monkeypatch.delenv("HNC_PACKET_MASTER_KEY", raising=False)

    missing = vault_ui_security_preflight(host="127.0.0.1")
    assert missing["status"] == "HOLD"
    assert set(missing["denial_codes"]) == {
        "vault_ui_bearer_token_unavailable_or_invalid",
        "hnc_master_key_unavailable_or_invalid",
    }

    _configure_security(monkeypatch)
    assert vault_ui_security_preflight(host="127.0.0.1")["status"] == "READY_LOCAL_HOLD"
    assert "loopback_bind_required" in vault_ui_security_preflight(
        host="0.0.0.0"
    )["denial_codes"]
    assert "debug_server_forbidden" in vault_ui_security_preflight(
        host="127.0.0.1", debug=True
    )["denial_codes"]


def test_factory_preflight_fails_before_constructing_runtime_components(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aureon.vault.ui import server as server_module

    monkeypatch.delenv(VAULT_UI_AUTH_ENV, raising=False)
    monkeypatch.delenv("AUREON_HNC_PACKET_MASTER_KEY", raising=False)
    monkeypatch.delenv("HNC_PACKET_MASTER_KEY", raising=False)
    monkeypatch.setattr(
        server_module,
        "AureonSelfFeedbackLoop",
        lambda *_args, **_kwargs: pytest.fail("factory preflight must run first"),
    )

    with pytest.raises(RuntimeError, match="vault_ui_factory_preflight_failed"):
        create_app()


def test_default_app_factory_uses_inert_local_components(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_security(monkeypatch)
    from aureon.vault.harmonic_pinger import HarmonicPinger

    monkeypatch.setattr(
        HarmonicPinger,
        "_load_chirp_bus",
        lambda _self: pytest.fail("HOLD factory must not attach shared-memory ChirpBus"),
    )
    monkeypatch.setattr(
        HarmonicPinger,
        "_load_thought_bus",
        lambda _self: pytest.fail("HOLD factory must not attach or persist ThoughtBus"),
    )

    app = create_app()
    loop = app.config["AUREON_LOOP"]

    assert loop._running is False
    assert loop.voice_engine is None
    assert loop._enhance_enabled is False
    assert loop.casimir._engine_kind == "stub"
    assert loop.casimir._engine is None
    assert loop.pinger._chirp_bus is None
    assert loop.pinger._thought_bus is None
    with pytest.raises(RuntimeError, match="vault_ui_voice_startup_hold"):
        create_app(enable_voice=True)


def test_app_factory_rejects_supplied_feedback_loop_without_touching_lifecycle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_security(monkeypatch)
    loop = AureonSelfFeedbackLoop(
        base_interval_s=0.01,
        auto_wire_bus=False,
        enable_voice=False,
        enable_self_enhancement=False,
        enable_native_casimir=False,
        enable_harmonic_buses=False,
    )
    monkeypatch.setattr(
        loop,
        "stop",
        lambda: pytest.fail("factory must not touch caller-owned lifecycle"),
    )

    with pytest.raises(RuntimeError, match="supplied_feedback_loop_forbidden"):
        create_app(loop=loop)

    assert loop._running is False
    assert loop._thread is None


def test_every_route_requires_a_strong_bearer_and_loopback_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _app, client, _loop = _client(monkeypatch)

    missing = client.get("/api/health")
    assert missing.status_code == 401
    assert missing.get_json()["request_executed"] is False

    wrong = client.get(
        "/api/health",
        headers={"Authorization": "Bearer " + ("W" * 64)},
    )
    assert wrong.status_code == 401

    remote = client.get(
        "/api/health",
        headers=AUTH,
        environ_base={"REMOTE_ADDR": "10.20.30.40"},
    )
    assert remote.status_code == 403
    assert remote.get_json()["reason_code"] == "loopback_transport_required"


def test_bearer_rotation_and_revocation_take_effect_on_the_next_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _app, client, _loop = _client(monkeypatch)

    assert client.get("/api/health", headers=AUTH).status_code == 200
    monkeypatch.setenv(VAULT_UI_AUTH_ENV, ROTATED_TOKEN)

    assert client.get("/api/health", headers=AUTH).status_code == 401
    rotated_auth = {"Authorization": f"Bearer {ROTATED_TOKEN}"}
    assert client.get("/api/health", headers=rotated_auth).status_code == 200

    monkeypatch.delenv(VAULT_UI_AUTH_ENV, raising=False)
    revoked = client.get("/api/health", headers=rotated_auth)
    assert revoked.status_code == 503
    assert revoked.get_json()["reason_code"] == "vault_ui_authorization_not_configured"


def test_request_metadata_limits_reject_before_hnc_admission(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, client, _loop = _client(monkeypatch)
    boundary = app.config["AUREON_VAULT_UI_INGRESS_BOUNDARY"]

    oversized_auth = client.post(
        "/api/tick",
        headers={"Authorization": "Bearer " + ("A" * 1100)},
    )
    oversized_headers = client.post(
        "/api/tick",
        headers={**AUTH, "X-Oversized": "H" * (VAULT_UI_MAX_HEADER_BYTES + 1)},
    )
    oversized_content_type = client.post(
        "/api/tick",
        headers={**AUTH, "Content-Type": "x" * 1025},
    )
    oversized_method = client.open(
        "/api/tick",
        method="M" * 33,
        headers=AUTH,
    )

    assert oversized_auth.status_code == 431
    assert oversized_headers.status_code == 431
    assert oversized_content_type.status_code == 431
    assert oversized_method.status_code == 400
    summary = boundary.public_summary()
    assert summary["seen_replay_count"] == 0
    assert summary["active_opaque_handle_count"] == 0


def test_authenticated_read_only_health_is_bounded_and_hardened(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _app, client, _loop = _client(monkeypatch)

    response = client.get("/api/health", headers=AUTH)

    assert response.status_code == 200
    assert response.get_json()["service"] == "aureon_vault_ui"
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]


def test_bridge_invite_is_a_network_inert_loopback_hold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _app, client, _loop = _client(monkeypatch)

    response = client.get("/api/bridge/invite", headers=AUTH)
    body = response.get_json()

    assert response.status_code == 200
    assert body["status"] == "HOLD"
    assert body["reason_code"] == "production_magic_star_release_unavailable"
    assert body["lan_ip"] == ""
    assert body["phone_url"] is None
    assert body["desktop_url"].startswith("http://127.0.0.1:")
    assert body["loopback_only"] is True


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/api/message", {"text": "hostile-message", "voice": "queen"}),
        ("/api/speak", {"voice": "queen"}),
        ("/api/converse", {}),
        ("/api/tick", {}),
        ("/api/loop/start", {}),
        ("/api/loop/stop", {}),
        ("/api/bridge/register", {"peer_id": "attacker"}),
        ("/api/bridge/sync", {"peer_id": "attacker", "state": {"poison": True}}),
        ("/api/bridge/drop", {"peer_id": "owner"}),
        ("/api/bridge/cards", {"from_peer_id": "attacker", "cards": []}),
        ("/api/queen/arm", {"live": True}),
        ("/api/queen/memory/clear", {}),
        ("/api/queen/execute", {"tool": "write_file", "params": {"path": "x"}}),
    ],
)
def test_every_mutating_route_becomes_hnc_and_holds_before_effect(
    monkeypatch: pytest.MonkeyPatch,
    path: str,
    payload: dict[str, Any],
) -> None:
    app, client, loop = _client(monkeypatch)
    cycles_before = loop._cycle
    vault_size_before = len(loop.vault)
    mesh = app.config["AUREON_PHI_BRIDGE_MESH"]
    mesh_received_before = mesh.info()["total_cards_in"]

    response = client.post(path, json=payload, headers=AUTH)
    body = response.get_json()

    assert response.status_code == 423
    assert body["status"] == "HOLD"
    assert body["reason_code"] == "production_magic_star_release_unavailable"
    assert body["request_executed"] is False
    assert body["effect_attempted"] is False
    assert body["plumber_hnc_admitted"] is True
    assert body["magic_star_release_required"] is True
    assert body["admission"]["disposition"] == "ADMITTED_HNC"
    assert body["disposal"]["disposition"] == "DISCARDED_HNC"
    assert body["disposal"]["carrier_released"] is False
    assert loop._cycle == cycles_before
    assert len(loop.vault) == vault_size_before
    assert mesh.info()["total_cards_in"] == mesh_received_before


def test_registered_effectful_route_census_has_no_hnc_bypass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, client, _loop = _client(monkeypatch)
    boundary = app.config["AUREON_VAULT_UI_INGRESS_BOUNDARY"]
    tested: set[tuple[str, str]] = set()
    effectful_get_fixtures = {
        "/static/<path:filename>": "/static/held-probe.js",
    }

    for rule in app.url_map.iter_rules():
        methods = sorted(set(rule.methods or ()) & {"POST", "PUT", "PATCH", "DELETE"})
        for method in methods:
            assert "<" not in rule.rule, f"parameterized mutating route needs a hostile fixture: {rule}"
            response = client.open(
                rule.rule,
                method=method,
                data=b"{}",
                headers={**AUTH, "Content-Type": "application/json"},
            )
            body = response.get_json()
            assert response.status_code == 423, (method, rule.rule, body)
            assert body["request_executed"] is False
            assert body["plumber_hnc_admitted"] is True
            assert body["magic_star_release_required"] is True
            assert body["disposal"]["disposition"] == "DISCARDED_HNC"
            tested.add((method, rule.rule))

        if "GET" in (rule.methods or ()) and rule.rule not in set(
            app.config["AUREON_VAULT_UI_SECURITY"]["safe_read_rules"]
        ):
            request_path = effectful_get_fixtures.get(rule.rule, rule.rule)
            assert "<" not in request_path, f"parameterized effectful GET needs a fixture: {rule}"
            for method in ("GET", "HEAD", "OPTIONS"):
                response = client.open(request_path, method=method, headers=AUTH)
                body = response.get_json() if method != "HEAD" else None
                assert response.status_code == 423, (method, rule.rule, body)
                if body is not None:
                    assert body["request_executed"] is False
                    assert body["plumber_hnc_admitted"] is True
                    assert body["magic_star_release_required"] is True
                    assert body["disposal"]["disposition"] == "DISCARDED_HNC"
                tested.add((method, rule.rule))

    assert tested
    summary = boundary.public_summary()
    assert summary["active_opaque_handle_count"] == 0
    assert summary["active_ingress_bytes"] == 0


def test_safe_read_allowlist_is_independently_pinned_and_options_are_held(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, client, loop = _client(monkeypatch)
    expected = {
        "/api/health",
        "/api/status",
        "/api/voices",
        "/api/utterances",
        "/api/message/<job_id>",
        "/api/bridge/invite",
        "/api/bridge/mesh/info",
        "/api/bridge/discovery/peers",
    }
    assert set(app.config["AUREON_VAULT_UI_SECURITY"]["safe_read_rules"]) == expected

    monkeypatch.setattr(
        loop,
        "tick",
        lambda: pytest.fail("safe read must not tick loop"),
    )
    monkeypatch.setattr(
        loop.vault,
        "ingest",
        lambda *_args, **_kwargs: pytest.fail("safe read must not mutate vault"),
    )
    paths = {
        "/api/health": 200,
        "/api/status": 200,
        "/api/voices": 200,
        "/api/utterances?n=2": 200,
        "/api/message/not-a-job": 404,
        "/api/bridge/invite": 200,
        "/api/bridge/mesh/info": 200,
        "/api/bridge/discovery/peers": 200,
    }

    for path, expected_status in paths.items():
        assert client.get(path, headers=AUTH).status_code == expected_status
        assert client.head(path, headers=AUTH).status_code == expected_status
        options = client.open(path, method="OPTIONS", headers=AUTH)
        assert options.status_code == 423
        assert options.get_json()["request_executed"] is False

    class PoisonDiscovery:
        def __getattribute__(self, _name: str):
            raise AssertionError("safe read must not dereference mutable discovery config")

    app.config["AUREON_PHI_BRIDGE_DISCOVERY"] = PoisonDiscovery()
    response = client.get("/api/bridge/discovery/peers", headers=AUTH)
    assert response.status_code == 200
    assert response.get_json() == {
        "ok": True,
        "running": False,
        "status": "HOLD",
        "reason_code": "production_magic_star_release_unavailable",
        "peers": [],
    }


def test_effectful_gets_hold_before_lazy_init_cleanup_or_persistence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, client, loop = _client(monkeypatch)
    from aureon.vault.ui import server as server_module

    bridge = app.config["AUREON_PHI_BRIDGE"]
    monkeypatch.setattr(bridge, "info", lambda: pytest.fail("bridge info must not run"))
    monkeypatch.setattr(bridge, "peers", lambda: pytest.fail("bridge peers must not run"))
    monkeypatch.setattr(loop, "get_status", lambda: pytest.fail("loop status must not run"))
    monkeypatch.setattr(
        server_module,
        "get_queen_action_bridge",
        lambda: pytest.fail("Queen action bridge must not initialize"),
    )
    monkeypatch.setattr(
        server_module,
        "get_conversation_memory",
        lambda: pytest.fail("conversation memory must not initialize"),
    )

    for path in (
        "/bridge-reset",
        "/api/bridge/info",
        "/api/bridge/state",
        "/api/bridge/peers",
        "/api/queen/status",
        "/api/queen/tools",
        "/api/queen/skills",
        "/api/queen/actions",
        "/api/queen/memory",
    ):
        response = client.get(path, headers=AUTH)
        assert response.status_code == 423, path
        assert response.get_json()["effect_attempted"] is False


def test_mutation_is_quarantined_without_hnc_key_and_never_reaches_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _app, client, loop = _client(monkeypatch, hnc_key=False)
    before = loop._cycle

    safe_read = client.get("/api/health", headers=AUTH)
    assert safe_read.status_code == 503
    assert safe_read.get_json()["reason_code"] == "hnc_master_key_unavailable_or_invalid"

    response = client.post("/api/tick", json={}, headers=AUTH)
    body = response.get_json()

    assert response.status_code == 409
    assert body["status"] == "QUARANTINED_HNC"
    assert body["request_executed"] is False
    assert body["effect_attempted"] is False
    assert body["plumber_hnc_admitted"] is False
    assert loop._cycle == before


def test_hnc_hold_response_never_echoes_body_or_bearer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _app, client, _loop = _client(monkeypatch)
    marker = "NEVER-ECHO-THIS-HOSTILE-BODY-8472"

    response = client.post(
        "/api/queen/execute",
        json={"tool": marker, "params": {"secret": marker}},
        headers=AUTH,
    )
    encoded = response.get_data()

    assert response.status_code == 423
    assert marker.encode() not in encoded
    assert TOKEN.encode() not in encoded


def test_bodyless_unknown_and_get_body_effect_intents_still_become_hnc(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _app, client, _loop = _client(monkeypatch)

    responses = (
        client.post("/api/tick", headers=AUTH),
        client.get("/unknown-effect-intent", headers=AUTH),
        client.get(
            "/api/health",
            data=b"unexpected-get-body",
            headers={**AUTH, "Content-Type": "application/octet-stream"},
        ),
    )

    for response in responses:
        body = response.get_json()
        assert response.status_code == 423
        assert body["plumber_hnc_admitted"] is True
        assert body["disposal"]["disposition"] == "DISCARDED_HNC"
        assert body["effect_attempted"] is False


def test_chunked_get_body_without_content_length_cannot_bypass_hnc(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, client, _loop = _client(monkeypatch)
    boundary = app.config["AUREON_VAULT_UI_INGRESS_BOUNDARY"]
    hostile = b"UNADMITTED-CHUNKED-BODY"
    builder = EnvironBuilder(path="/api/health", method="GET", headers=AUTH)
    environ = builder.get_environ()
    environ.pop("CONTENT_LENGTH", None)
    environ["wsgi.input"] = BytesIO(hostile)
    environ["wsgi.input_terminated"] = True

    response = client.open(environ)
    body = response.get_json()

    assert response.status_code == 423
    assert body["plumber_hnc_admitted"] is True
    assert body["disposal"]["disposition"] == "DISCARDED_HNC"
    assert hostile not in response.get_data()
    summary = boundary.public_summary()
    assert summary["consumed_opaque_handle_count"] == 1
    assert summary["active_opaque_handle_count"] == 0


@pytest.mark.parametrize(
    ("body_size", "expected_status", "expected_replay_count"),
    [
        (VAULT_UI_MAX_REQUEST_BYTES, 423, 1),
        (VAULT_UI_MAX_REQUEST_BYTES + 1, 413, 0),
        (VAULT_UI_MAX_REQUEST_BYTES * 4, 413, 0),
    ],
)
def test_chunked_body_boundary_is_exact_without_content_length(
    monkeypatch: pytest.MonkeyPatch,
    body_size: int,
    expected_status: int,
    expected_replay_count: int,
) -> None:
    app, client, _loop = _client(monkeypatch)
    boundary = app.config["AUREON_VAULT_UI_INGRESS_BOUNDARY"]
    builder = EnvironBuilder(
        path="/api/tick",
        method="POST",
        headers={**AUTH, "Content-Type": "application/octet-stream"},
    )
    environ = builder.get_environ()
    environ.pop("CONTENT_LENGTH", None)
    environ["wsgi.input"] = BytesIO(b"C" * body_size)
    environ["wsgi.input_terminated"] = True

    response = client.open(environ)

    assert response.status_code == expected_status
    summary = boundary.public_summary()
    assert summary["seen_replay_count"] == expected_replay_count
    assert summary["active_opaque_handle_count"] == 0
    assert summary["active_ingress_bytes"] == 0


def test_replay_and_header_binding_are_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, client, _loop = _client(monkeypatch)
    boundary = app.config["AUREON_VAULT_UI_INGRESS_BOUNDARY"]
    payload = b"same-effect-intent"
    headers_a = {
        **AUTH,
        "Content-Type": "application/octet-stream",
        "User-Agent": "vault-hostile-a",
    }
    headers_b = {**headers_a, "User-Agent": "vault-hostile-b"}

    first = client.post("/api/tick?mode=a", data=payload, headers=headers_a)
    replay = client.post("/api/tick?mode=a", data=payload, headers=headers_a)
    changed_header = client.post("/api/tick?mode=a", data=payload, headers=headers_b)
    changed_query = client.post("/api/tick?mode=b", data=payload, headers=headers_b)

    assert first.status_code == 423
    assert replay.status_code == 409
    assert "ingress_replay_detected" in replay.get_json()["admission"]["denial_codes"]
    assert changed_header.status_code == 423
    assert changed_query.status_code == 423
    summary = boundary.public_summary()
    assert summary["seen_replay_count"] == 3
    assert summary["active_opaque_handle_count"] == 0


def test_replay_ledger_capacity_exhaustion_quarantines_new_intent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, client, _loop = _client(monkeypatch)
    boundary = app.config["AUREON_VAULT_UI_INGRESS_BOUNDARY"]
    boundary._max_replay_tokens = 2

    first = client.post("/api/tick?n=1", headers=AUTH)
    second = client.post("/api/tick?n=2", headers=AUTH)
    exhausted = client.post("/api/tick?n=3", headers=AUTH)

    assert first.status_code == 423
    assert second.status_code == 423
    assert exhausted.status_code == 409
    assert "replay_ledger_capacity_exhausted" in exhausted.get_json()["admission"][
        "denial_codes"
    ]
    assert boundary.public_summary()["active_opaque_handle_count"] == 0


def test_oversized_mutation_is_rejected_before_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _app, client, loop = _client(monkeypatch)
    before = loop._cycle

    response = client.post(
        "/api/tick",
        data=b"X" * (64 * 1024 + 1),
        headers={**AUTH, "Content-Type": "application/octet-stream"},
    )

    assert response.status_code == 413
    assert response.get_json()["reason_code"] == "request_size_limit_exceeded"
    assert loop._cycle == before


def test_create_app_does_not_start_udp_discovery_or_card_gossip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_security(monkeypatch)

    class Discovery:
        def __init__(self) -> None:
            self.start_calls = 0
            self.stop_calls = 0

        def start(self) -> None:
            self.start_calls += 1

        def stop(self) -> None:
            self.stop_calls += 1

    discovery = Discovery()
    from aureon.vault.ui import server as server_module

    monkeypatch.setattr(
        server_module.threading,
        "Thread",
        lambda *_args, **_kwargs: pytest.fail("create_app must not start background threads"),
    )
    with pytest.raises(RuntimeError, match="supplied_mesh_discovery_forbidden"):
        create_app(mesh_discovery=discovery)  # type: ignore[arg-type]
    app = create_app()
    mesh = app.config["AUREON_PHI_BRIDGE_MESH"]

    assert discovery.start_calls == 0
    assert discovery.stop_calls == 0
    assert app.config["AUREON_PHI_BRIDGE_DISCOVERY"] is None
    assert mesh.info()["running"] is False
    assert app.config["AUREON_PHI_BRIDGE_MESH_RUNTIME"] == {
        "status": "HOLD",
        "udp_discovery_started": False,
        "card_gossip_started": False,
        "reason_code": "production_magic_star_release_unavailable",
        "production_ready": False,
    }
    assert app.config["AUREON_LLM_WARMER_RUNTIME"] == {
        "status": "HOLD",
        "boot_ping_started": False,
        "keepalive_thread_started": False,
        "reason_code": "production_magic_star_release_unavailable",
        "production_ready": False,
    }


def test_direct_singleton_mesh_start_is_held_and_app_uses_owned_mesh(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_security(monkeypatch)

    class RunningDiscovery:
        def __init__(self) -> None:
            self._running = True
            self.stop_calls = 0

        def known_peers(self) -> list[object]:
            return []

        def stop(self) -> None:
            self.stop_calls += 1
            self._running = False

    discovery = RunningDiscovery()
    loop = AureonSelfFeedbackLoop(
        base_interval_s=0.01,
        auto_wire_bus=False,
        enable_voice=False,
        enable_self_enhancement=False,
        enable_native_casimir=False,
        enable_harmonic_buses=False,
    )
    mesh = get_phi_bridge_mesh(vault=loop.vault, discovery=discovery)
    mesh.interval_s = 0.01
    with pytest.raises(RuntimeError, match="phi_bridge_mesh_hold"):
        mesh.start()

    app = create_app()
    owned_mesh = app.config["AUREON_PHI_BRIDGE_MESH"]

    assert owned_mesh is not mesh
    assert owned_mesh.vault is app.config["AUREON_LOOP"].vault
    assert mesh.info()["running"] is False
    assert discovery.stop_calls == 0
    assert app.config["AUREON_PHI_BRIDGE_DISCOVERY"] is None


def test_run_server_rejects_external_bind_before_flask_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_security(monkeypatch)

    with pytest.raises(RuntimeError, match="loopback_bind_required"):
        run_server(host="0.0.0.0")
    with pytest.raises(RuntimeError, match="loop_start_hold"):
        run_server(host="127.0.0.1", start_loop=True)


def test_app_run_forces_loopback_single_process_and_redacted_handler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, _client_instance, _loop = _client(monkeypatch)
    captured: dict[str, Any] = {}

    def _capture_run(_self, *args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs

    monkeypatch.setattr(Flask, "run", _capture_run)

    with pytest.raises(RuntimeError, match="loopback_bind_required"):
        app.run(host="0.0.0.0")
    with pytest.raises(RuntimeError, match="debug_server_forbidden"):
        app.run(host="127.0.0.1", debug=True)
    with pytest.raises(RuntimeError, match="debug_server_forbidden"):
        app.run(host="127.0.0.1", use_reloader=True)

    app.run(
        host="localhost",
        port=6007,
        load_dotenv=True,
        threaded=True,
        processes=9,
        request_handler=object,
    )

    options = captured["kwargs"]
    assert options["host"] == "127.0.0.1"
    assert options["port"] == 6007
    assert options["debug"] is False
    assert options["load_dotenv"] is False
    assert options["use_debugger"] is False
    assert options["use_evalex"] is False
    assert options["use_reloader"] is False
    assert options["threaded"] is False
    assert options["processes"] == 1
    assert options["request_handler"] is VaultUIRedactedRequestHandler


def test_request_handler_never_logs_request_target_or_error_arguments() -> None:
    secret = "SECRET-PATH-QUERY-TOKEN-4481"
    records: list[tuple[Any, ...]] = []
    fake = SimpleNamespace(
        path=f"/api/tick?token={secret}",
        requestline=f"POST /api/tick?token={secret} HTTP/1.1",
        log=lambda *args: records.append(args),
    )

    VaultUIRedactedRequestHandler.log_request(fake, 423, 12)
    VaultUIRedactedRequestHandler.log_error(fake, "%s", secret)
    VaultUIRedactedRequestHandler.log_message(fake, "%s", secret)

    rendered = repr(records)
    assert secret not in rendered
    assert "vault-target-redacted" in rendered
    assert "vault-request-error-redacted" in rendered
    assert "vault-request-message-redacted" in rendered


def test_integrated_system_rejects_lan_remote_and_tunnel_without_launching(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Some ICS dependencies import urllib3, whose module-level IPv6 capability
    # check creates a local socket. The socket remains blocked; suppress only
    # pytest-socket's expected diagnostic for that dependency import probe.
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=r"A test tried to use socket\.socket\.",
            category=UserWarning,
        )
        from aureon.core.integrated_cognitive_system import IntegratedCognitiveSystem

    system = IntegratedCognitiveSystem.__new__(IntegratedCognitiveSystem)
    monkeypatch.setattr(system, "boot", lambda: pytest.fail("boot must not run"))

    with pytest.raises(RuntimeError, match="external_exposure_hold"):
        system.run(lan=True)
    with pytest.raises(RuntimeError, match="external_exposure_hold"):
        system.run(remote=True)
    with pytest.raises(RuntimeError, match="integrated_cognitive_system_runtime_hold"):
        system.run()
    assert system._start_tunnel(5566) is None

    monkeypatch.delenv("AUREON_AUDIT_MODE", raising=False)
    monkeypatch.delenv("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", raising=False)
    initialized = IntegratedCognitiveSystem()
    with pytest.raises(RuntimeError, match="integrated_cognitive_system_boot_hold"):
        initialized.boot()
