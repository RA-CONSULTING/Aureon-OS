"""Hostile runtime checks for the Operator whole-OS ingress boundary.

The default app has no production Magic Star release implementation.  Every
effect-bearing HTTP ingress therefore ends as commitment-only quarantine or as
an admitted HNC carrier that is atomically burned before a HOLD response.
"""

from __future__ import annotations

import base64
import importlib
import json
from types import SimpleNamespace
from typing import Any

import pytest

pytest.importorskip("flask", reason="operator HTTP surface requires the `.[operator]` extra")

_HNC_KEY = base64.urlsafe_b64encode(b"operator-control-plane-hostile-test-key").rstrip(b"=").decode()
_TEST_RAW_KEY = b"operator-control-plane-route-test-key"


def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "AUREON_HNC_PACKET_MASTER_KEY",
        "HNC_PACKET_MASTER_KEY",
        "AUREON_OPERATOR_API_KEY",
        "AUREON_OPERATOR_RATE_RPS",
        "AUREON_OPERATOR_RATE_BURST",
        "AUREON_OPERATOR_MAX_BODY",
        "AUREON_OPERATOR_TRUSTED_PROXY_CIDRS",
        "AUREON_SUPABASE_JWT_SECRET",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("AUREON_OPERATOR_ENV", "test")
    monkeypatch.setenv("AUREON_LLM_OFFLINE", "1")
    monkeypatch.setenv("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")


def _operator(**overrides: Any) -> Any:
    values: dict[str, Any] = {
        "providers": {},
        "bus": None,
        "respond": lambda *_args, **_kwargs: SimpleNamespace(to_dict=lambda: {"reached": True}),
        "stream_events": lambda *_args, **_kwargs: (),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _server():
    import aureon.operator.operator_server as srv

    return importlib.reload(srv)


def test_missing_and_invalid_hnc_keys_quarantine_without_plaintext(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_env(monkeypatch)
    srv = _server()
    reached: list[str] = []
    app = srv.create_app(operator=_operator())
    app.add_url_rule(
        "/api/hostile-mutation",
        "hostile_mutation",
        lambda: reached.append("handler") or {"reached": True},
        methods=["POST"],
    )
    client = app.test_client()

    secret = "plaintext-never-in-public-summary"
    missing = client.post("/api/hostile-mutation", json={"value": secret})
    missing_body = missing.get_json()["error"]
    assert missing.status_code == 503
    assert missing_body["disposition"] == "QUARANTINED_HNC"
    assert "master_key_unavailable" in missing_body["denial_codes"]
    assert missing_body["raw_material_retained"] is False
    assert secret not in json.dumps(missing.get_json(), sort_keys=True)
    assert reached == []

    monkeypatch.setenv("AUREON_HNC_PACKET_MASTER_KEY", "not canonical key material!")
    invalid_app = srv.create_app(operator=_operator())
    invalid_app.add_url_rule(
        "/api/hostile-invalid-key",
        "hostile_invalid_key",
        lambda: reached.append("invalid-handler") or {"reached": True},
        methods=["POST"],
    )
    invalid = invalid_app.test_client().post(
        "/api/hostile-invalid-key",
        json={"value": secret},
    )
    invalid_body = invalid.get_json()["error"]
    assert invalid.status_code == 503
    assert invalid_body["disposition"] == "QUARANTINED_HNC"
    assert "master_key_invalid" in invalid_body["denial_codes"]
    assert secret not in json.dumps(invalid.get_json(), sort_keys=True)
    assert reached == []


def test_admitted_input_is_burned_held_and_replay_is_quarantined(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("AUREON_HNC_PACKET_MASTER_KEY", _HNC_KEY)
    srv = _server()
    reached: list[str] = []
    app = srv.create_app(operator=_operator())
    app.add_url_rule(
        "/api/replay-probe",
        "replay_probe",
        lambda: reached.append("handler") or {"reached": True},
        methods=["POST"],
    )
    client = app.test_client()

    first = client.post("/api/replay-probe", json={"request": "same-secret"})
    first_body = first.get_json()["error"]
    assert first.status_code == 503
    assert first_body["disposition"] == "ADMITTED_HNC"
    assert first_body["reason_code"] == "production_magic_star_release_unavailable"
    assert first_body["carrier_released"] is False
    assert first_body["plaintext_decoded"] is False
    assert first_body["handler_invoked"] is False

    status = app.extensions["aureon_operator_ingress_status"]()
    assert status["active_opaque_handle_count"] == 0
    assert status["active_ingress_bytes"] == 0
    assert status["consumed_opaque_handle_count"] == 1

    replay = client.post("/api/replay-probe", json={"request": "same-secret"})
    replay_body = replay.get_json()["error"]
    assert replay.status_code == 503
    assert replay_body["disposition"] == "QUARANTINED_HNC"
    assert "ingress_replay_detected" in replay_body["denial_codes"]
    assert reached == []


def test_malformed_json_is_quarantined_before_any_view(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("AUREON_HNC_PACKET_MASTER_KEY", _HNC_KEY)
    srv = _server()
    reached: list[str] = []
    app = srv.create_app(operator=_operator())
    app.add_url_rule(
        "/api/malformed-probe",
        "malformed_probe",
        lambda: reached.append("handler") or {"reached": True},
        methods=["POST"],
    )

    response = app.test_client().post(
        "/api/malformed-probe",
        data=b'{"secret":"never-returned",',
        content_type="application/json",
    )
    body = response.get_json()["error"]
    assert response.status_code == 503
    assert body["disposition"] == "QUARANTINED_HNC"
    assert "ingress_content_invalid" in body["denial_codes"]
    assert "never-returned" not in json.dumps(response.get_json(), sort_keys=True)
    assert reached == []

    duplicate = app.test_client().post(
        "/api/malformed-probe",
        data=b'{"value":"first","value":"duplicate-secret"}',
        content_type="application/json",
    )
    duplicate_body = duplicate.get_json()["error"]
    assert duplicate.status_code == 503
    assert duplicate_body["disposition"] == "QUARANTINED_HNC"
    assert "ingress_content_invalid" in duplicate_body["denial_codes"]
    assert "duplicate-secret" not in json.dumps(duplicate.get_json(), sort_keys=True)
    assert reached == []


def test_action_config_and_mcp_handlers_are_not_reached(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("AUREON_HNC_PACKET_MASTER_KEY", _HNC_KEY)
    calls: list[str] = []

    import aureon.bio.mcp_transport as mcp_transport
    import aureon.operator.feature_switchboard as switchboard
    import aureon.operator.local_action_bridge as local_action_bridge

    monkeypatch.setattr(
        local_action_bridge,
        "get_local_action_bridge",
        lambda: calls.append("local_action") or (_ for _ in ()).throw(AssertionError("reached")),
    )
    monkeypatch.setattr(
        switchboard,
        "save_flag",
        lambda *_args, **_kwargs: calls.append("switchboard")
        or (_ for _ in ()).throw(AssertionError("reached")),
    )
    monkeypatch.setattr(
        mcp_transport,
        "handle_mcp_call",
        lambda *_args, **_kwargs: calls.append("mcp")
        or (_ for _ in ()).throw(AssertionError("reached")),
    )

    srv = _server()
    client = srv.create_app(operator=_operator()).test_client()
    responses = (
        client.post("/api/action", json={"action": "list_repo"}),
        client.post("/api/switchboard/AUREON_LLM_OFFLINE", json={"enabled": True}),
        client.post("/mcp/call", json={"name": "read_state", "arguments": {}}),
    )
    assert [response.status_code for response in responses] == [503, 503, 503]
    assert all(
        response.get_json()["error"]["reason_code"]
        == "production_magic_star_release_unavailable"
        for response in responses
    )
    assert calls == []


def test_bearer_and_body_bounds_run_before_hnc_or_handlers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("AUREON_HNC_PACKET_MASTER_KEY", _HNC_KEY)
    monkeypatch.setenv("AUREON_OPERATOR_API_KEY", "operator-secret")
    monkeypatch.setenv("AUREON_OPERATOR_MAX_BODY", "32")
    srv = _server()
    hnc_calls: list[int] = []
    original_admit = srv.LocalOSProtectionBoundary.admit_external

    def recording_admit(self, raw, **kwargs):  # noqa: ANN001
        hnc_calls.append(len(raw))
        return original_admit(self, raw, **kwargs)

    monkeypatch.setattr(srv.LocalOSProtectionBoundary, "admit_external", recording_admit)
    reached: list[str] = []
    app = srv.create_app(operator=_operator())
    app.add_url_rule(
        "/api/bounds-probe",
        "bounds_probe",
        lambda: reached.append("handler") or {"reached": True},
        methods=["POST"],
    )
    client = app.test_client()

    huge_bearer = client.post(
        "/api/bounds-probe",
        data=b"{}",
        content_type="application/json",
        headers={"Authorization": "Bearer " + "x" * 9000},
    )
    assert huge_bearer.status_code == 431
    assert hnc_calls == []

    missing_bearer = client.post(
        "/api/bounds-probe",
        data=b"{" + b"x" * 100 + b"}",
        content_type="application/json",
    )
    assert missing_bearer.status_code == 401
    assert hnc_calls == []

    oversized = client.post(
        "/api/bounds-probe",
        data=b"{" + b"x" * 100 + b"}",
        content_type="application/json",
        headers={"Authorization": "Bearer operator-secret"},
    )
    assert oversized.status_code == 413
    assert hnc_calls == []
    assert reached == []


def test_query_model_ingress_and_authenticated_remote_mutation_stay_held(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("AUREON_HNC_PACKET_MASTER_KEY", _HNC_KEY)
    monkeypatch.setenv("AUREON_OPERATOR_API_KEY", "operator-secret")
    calls: list[str] = []
    srv = _server()
    operator = _operator(
        stream_events=lambda *_args, **_kwargs: calls.append("stream") or (),
        respond=lambda *_args, **_kwargs: calls.append("respond")
        or SimpleNamespace(to_dict=lambda: {"reached": True}),
    )
    client = srv.create_app(operator=operator).test_client()
    auth = {"Authorization": "Bearer operator-secret"}

    stream = client.get("/api/operator/stream?prompt=sealed-query", headers=auth)
    remote = client.post(
        "/api/operator/respond",
        json={"prompt": "sealed-remote-body"},
        headers=auth,
        environ_base={"REMOTE_ADDR": "203.0.113.77"},
    )
    assert stream.status_code == 503
    assert remote.status_code == 503
    assert stream.get_json()["error"]["disposition"] == "ADMITTED_HNC"
    assert remote.get_json()["error"]["disposition"] == "ADMITTED_HNC"
    assert calls == []


def test_peer_source_is_a_fixed_commitment_not_forwarded_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("AUREON_HNC_PACKET_MASTER_KEY", _HNC_KEY)
    monkeypatch.setenv("AUREON_OPERATOR_API_KEY", "operator-secret")
    monkeypatch.setenv("AUREON_OPERATOR_TRUSTED_PROXY_CIDRS", "127.0.0.0/8")
    srv = _server()
    captured_sources: list[str] = []
    original_admit = srv.LocalOSProtectionBoundary.admit_external

    def recording_admit(self, raw, **kwargs):  # noqa: ANN001
        captured_sources.append(kwargs["source_id"])
        return original_admit(self, raw, **kwargs)

    monkeypatch.setattr(srv.LocalOSProtectionBoundary, "admit_external", recording_admit)
    client = srv.create_app(operator=_operator()).test_client()
    forwarded = ",".join(["10.0.0.1"] * 300 + ["203.0.113.88"])
    assert len(forwarded.encode()) < srv.MAX_OPERATOR_FORWARDED_FOR_BYTES

    response = client.post(
        "/api/operator/respond",
        json={"prompt": "peer-commitment-probe"},
        headers={
            "Authorization": "Bearer operator-secret",
            "X-Forwarded-For": forwarded,
        },
        environ_base={"REMOTE_ADDR": "127.0.0.1"},
    )
    assert response.status_code == 503
    assert len(captured_sources) == 1
    prefix = "operator-http-peer-sha256:"
    assert captured_sources[0].startswith(prefix)
    assert len(captured_sources[0]) == len(prefix) + 64
    assert "203.0.113.88" not in captured_sources[0]
    assert forwarded not in json.dumps(response.get_json(), sort_keys=True)


def test_explicit_test_only_seam_preserves_route_unit_tests_after_burn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_env(monkeypatch)
    calls: list[str] = []
    srv = _server()
    operator = _operator(
        respond=lambda prompt, session_id=None: calls.append(prompt)
        or SimpleNamespace(to_dict=lambda: {"text": "test-only-route-result"}),
    )
    seam = srv.TestOnlyOperatorIngressRelease(master_key=_TEST_RAW_KEY)
    app = srv.create_app(operator=operator, test_ingress_release=seam)

    response = app.test_client().post("/api/operator/respond", json={"prompt": "unit-route"})
    assert response.status_code == 200
    assert response.get_json() == {"text": "test-only-route-result"}
    assert calls == ["unit-route"]
    status = seam.boundary_public_summary()
    assert status["active_opaque_handle_count"] == 0
    assert status["consumed_opaque_handle_count"] == 1
    assert status["production_ready"] is False


def test_test_only_seam_is_rejected_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("AUREON_OPERATOR_ENV", "production")
    monkeypatch.setenv("AUREON_OPERATOR_API_KEY", "operator-secret")
    monkeypatch.setenv("AUREON_OPERATOR_RATE_RPS", "1")
    srv = _server()
    seam = srv.TestOnlyOperatorIngressRelease(master_key=_TEST_RAW_KEY)

    with pytest.raises(ValueError, match="test_ingress_release_forbidden_in_production"):
        srv.create_app(operator=_operator(), test_ingress_release=seam)
