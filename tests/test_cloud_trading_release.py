from __future__ import annotations

import base64
from datetime import UTC, datetime

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from aureon.operator import cloud_trading_release as release


class Response:
    def __init__(self, value, status=200):
        self.value = value
        self.status_code = status

    def json(self):
        return self.value


def _ready(now: float):
    expires = datetime.fromtimestamp(now + 3600, tz=UTC).isoformat()
    return {
        "operator_can_apply_live": True,
        "desired_live_state": True,
        "authorization": {
            "active": True, "ledger_event_sha256": "1" * 64, "expires_at_iso": expires,
        },
        "capabilities": {
            "durable_budget_ledger": True, "order_adapter_ready": True,
            "all_four_provider_readback_pinned": True, "live_result_binding_ready": True,
            "instrument_preflight_enforced": True,
            "controller_integrated": True,
        },
        "last_probe": {
            "current": True, "receipt_sha256": "2" * 64,
            "source_revision": "a" * 40,
            "runtime_measurement_sha256": release.probe_runtime_measurement_sha256("a" * 40),
            "provider_readback": {"readback_sha256": "3" * 64},
        },
    }


def test_activation_request_binds_current_evidence_and_publishes_once():
    sent = []

    def requester(method, url, **kwargs):
        sent.append((method, url, kwargs))
        return Response({"messageIds": ["123456789"]})

    result = release.publish_release_request(
        "activate", _ready(1_800_000_000),
        environ={"AUREON_REVISION": "a" * 40}, now=1_800_000_000,
        requester=requester, token_provider=lambda: "x" * 40,
    )
    assert result["controller_pending"] is True and result["release_authority"] is False
    encoded = sent[0][2]["json"]["messages"][0]["data"]
    value = __import__("json").loads(base64.b64decode(encoded))
    assert value["action"] == "activate"
    assert value["authorization_event_sha256"] == "1" * 64
    assert value["probe_receipt_sha256"] == "2" * 64
    assert value["provider_readback_sha256"] == "3" * 64


def test_activation_rejects_readiness_without_instrument_preflight_gate():
    control = _ready(1_800_000_000)
    control["capabilities"].pop("instrument_preflight_enforced")
    with pytest.raises(release.CloudTradingReleaseError, match="prerequisites_not_ready"):
        release.publish_release_request(
            "activate", control,
            environ={"AUREON_REVISION": "a" * 40}, now=1_800_000_000,
            requester=lambda *_args, **_kwargs: Response({"messageIds": ["unexpected"]}),
            token_provider=lambda: "x" * 40,
        )


def test_activation_rejects_replayed_probe_from_another_revision_without_publish():
    control = _ready(1_800_000_000)
    control["last_probe"]["source_revision"] = "b" * 40
    control["last_probe"]["runtime_measurement_sha256"] = (
        release.probe_runtime_measurement_sha256("b" * 40)
    )
    calls = []
    with pytest.raises(release.CloudTradingReleaseError, match="probe_revision_mismatch"):
        release.publish_release_request(
            "activate", control,
            environ={"AUREON_REVISION": "a" * 40}, now=1_800_000_000,
            requester=lambda *args, **kwargs: calls.append((args, kwargs)),
            token_provider=lambda: "x" * 40,
        )
    assert calls == []


def test_hold_request_is_always_fail_closed_and_carries_no_lease_evidence():
    captured = []

    def requester(_method, _url, **kwargs):
        captured.append(kwargs["json"])
        return Response({"messageIds": ["7"]})

    release.publish_release_request(
        "hold", {}, environ={"AUREON_OPERATOR_REVISION": "b" * 40}, now=1_800_000_000,
        requester=requester, token_provider=lambda: "x" * 40,
    )
    value = __import__("json").loads(base64.b64decode(captured[0]["messages"][0]["data"]))
    assert value["requested_controls"] == release.HELD_CONTROLS
    assert value["authorization_event_sha256"] is None


def test_controller_state_requires_the_pinned_ed25519_signature():
    private = Ed25519PrivateKey.generate()
    public_pem = private.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")
    unsigned = {
        "schema": release.RELEASE_SCHEMA, "state": "held", "generation": 1,
        "request_id": "1" * 64, "requested_controls_sha256": "2" * 64,
        "authorization_event_sha256": "0" * 64, "authorization_expires_at_ms": 0,
        "probe_receipt_sha256": "0" * 64, "provider_readback_sha256": "0" * 64,
        "source_revision": "a" * 40, "signed_at_ms": 1_800_000_000_000,
        "controller_key_version": release.CONTROLLER_KEY,
    }
    fields = {**unsigned, "signature": base64.b64encode(private.sign(release._canonical(unsigned))).decode()}

    def encoded(value):
        if type(value) is bool:
            return {"booleanValue": value}
        if type(value) is int:
            return {"integerValue": str(value)}
        return {"stringValue": value}

    document = {"name": "release", "updateTime": "2026-09-12T00:00:00Z",
                "fields": {key: encoded(value) for key, value in fields.items()}}

    def requester(_method, url, **_kwargs):
        if url.endswith("/publicKey"):
            return Response({"name": release.CONTROLLER_KEY, "algorithm": "EC_SIGN_ED25519", "pem": public_pem})
        return Response(document)

    state, error = release.read_controller_release(
        environ={"AUREON_CONTROLLER_KEY_VERSION": release.CONTROLLER_KEY},
        requester=requester, token_provider=lambda: "x" * 40,
    )
    assert error is None and state["state"] == "held" and state["generation"] == 1
