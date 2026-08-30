from __future__ import annotations

import importlib
from types import SimpleNamespace


def _app(monkeypatch, tmp_path, *, operator_key: str):
    monkeypatch.setenv("AUREON_OPERATOR_API_KEY", operator_key)
    monkeypatch.setenv("AUREON_OPERATOR_ENV", "test")
    monkeypatch.setenv("AUREON_LLM_OFFLINE", "1")
    monkeypatch.setenv("AUREON_BUS_TRACE_DIR", str(tmp_path))
    monkeypatch.delenv("AUREON_SUPABASE_JWT_SECRET", raising=False)

    import aureon.core.approval_queue as approval_module
    import aureon.operator.operator_server as server_module

    importlib.reload(approval_module)
    importlib.reload(server_module)
    operator = SimpleNamespace(providers={}, bus=None)
    cognition = SimpleNamespace()
    app = server_module.create_app(operator=operator, cognition=cognition)
    return app.test_client(), approval_module.get_approval_queue()


def test_approval_decision_requires_configured_admin_bearer(monkeypatch, tmp_path):
    client, queue = _app(monkeypatch, tmp_path, operator_key="owner-admin-secret")
    item_id = queue.propose("trade", "bounded proof", {"symbol": "BTCUSDT"})

    assert client.post(
        f"/api/approvals/{item_id}", json={"decision": "approve"}
    ).status_code == 401
    response = client.post(
        f"/api/approvals/{item_id}",
        json={"decision": "approve"},
        headers={"Authorization": "Bearer owner-admin-secret"},
    )

    assert response.status_code == 200
    decided = queue.get(item_id)
    assert decided["status"] == "approved"
    assert decided["approver"] == "gary-operator-admin"
    assert decided["approval_auth"] == {
        "authenticated": True,
        "identity_kind": "admin",
        "authn_method": "operator_static_bearer",
    }


def test_request_body_cannot_spoof_approver(monkeypatch, tmp_path):
    client, queue = _app(monkeypatch, tmp_path, operator_key="owner-admin-secret")
    item_id = queue.propose("trade", "bounded proof", {"symbol": "BTCUSDT"})
    response = client.post(
        f"/api/approvals/{item_id}",
        json={"decision": "approve", "approver": "forged-owner"},
        headers={"Authorization": "Bearer owner-admin-secret"},
    )
    assert response.status_code == 400
    assert queue.get(item_id)["status"] == "pending"


def test_open_development_identity_cannot_decide(monkeypatch, tmp_path):
    client, queue = _app(monkeypatch, tmp_path, operator_key="")
    item_id = queue.propose("trade", "bounded proof", {"symbol": "BTCUSDT"})
    response = client.post(
        f"/api/approvals/{item_id}", json={"decision": "approve"}
    )
    assert response.status_code == 403
    assert queue.get(item_id)["status"] == "pending"
