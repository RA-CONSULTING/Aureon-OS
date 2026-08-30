"""
Aureon SaaS — billing gateway (metering hooks + read API + gated fee proxy).
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

`register_billing(app)` mounts onto the operator Flask app:

  • an `after_request` metering hook — one `api_request` usage event per /api/*
    request, tenant-attributed when a Supabase JWT is present (best-effort; the
    hook never rejects and never breaks a response);
  • GET  /api/billing/status      — always 200; the honest config/metering state
  • GET  /api/billing/balance     — the tenant's gas_tank_accounts row (PostgREST)
  • GET  /api/billing/usage       — the tenant's usage events
  • POST /api/billing/charge-fee  — ⚠ MOVES MONEY. Proxy to the existing
    gas-tank-deduct-fee edge function (the fee math stays there). Disabled unless
    AUREON_BILLING_CHARGE_ENABLED=1; every call is audited as a fee_charge event.

The platform never initiates payments on its own: metering is record-only, and
charge-fee is an explicit, operator-authenticated, env-gated, audited endpoint
for the server-side trade loop.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, Tuple

from aureon.saas.metering import UsageEvent, get_buffer
from aureon.saas.supabase_rest import SupabaseConfig, SupabaseRest

logger = logging.getLogger("aureon.saas.billing")

_ACCOUNTS_TABLE = "gas_tank_accounts"
_USAGE_TABLE = "saas_usage_events"
_DEDUCT_FN = "gas-tank-deduct-fee"


def _charge_enabled() -> bool:
    return str(os.environ.get("AUREON_BILLING_CHARGE_ENABLED", "") or "") == "1"


def register_billing(app: Any) -> Any:
    """Mount metering hooks + /api/billing routes onto an existing Flask app."""
    from flask import g, jsonify, request

    from aureon.saas.gateway import verify_supabase_jwt

    jwt_secret = str(os.environ.get("AUREON_SUPABASE_JWT_SECRET", "") or "")
    charge_enabled = _charge_enabled()  # captured at register time, like the JWT secret
    config = SupabaseConfig.from_env()
    rest = SupabaseRest(config) if config.ok else None

    # ── tenant resolution (best-effort; never rejects) ───────────────────────

    def _resolve_tenant() -> str | None:
        tenant = getattr(g, "tenant", None)
        if tenant:
            return str(tenant)
        if not jwt_secret:
            return None
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return None
        claims = verify_supabase_jwt(auth[len("Bearer "):].strip(), jwt_secret)
        if claims is None:
            return None
        sub = claims.get("sub")
        return str(sub) if sub else None

    def _require_tenant() -> Tuple[str | None, Any]:
        """(tenant, error_response). Honest failures: 503 when unconfigured, 401 when unauthenticated."""
        if not jwt_secret:
            return None, (jsonify({"error": {
                "code": 503,
                "message": "tenancy bridge disabled (AUREON_SUPABASE_JWT_SECRET unset)",
            }}), 503)
        tenant = _resolve_tenant()
        if tenant is None:
            return None, (jsonify({"error": {"code": 401, "message": "valid Supabase token required"}}), 401)
        return tenant, None

    def _require_supabase() -> Any:
        if rest is None:
            return jsonify({"error": {
                "code": 503,
                "message": "billing backend not configured",
                "missing": config.missing(),
            }}), 503
        return None

    def _admin_denied() -> Any:
        """Refuse a signed-in end user (tenant) on an operator-only route.

        ``g.is_admin`` is set by the operator request gate (admin bearer, or the open single-operator
        default ⇒ True) and is absent when these routes are mounted on a bare app, so the default is
        permissive and standalone mounts are unaffected.
        """
        if not getattr(g, "is_admin", True):
            return jsonify({"error": {"code": 403,
                                      "message": "this control-plane route is operator-only",
                                      "plane": "admin"}}), 403
        return None

    # ── metering hooks ────────────────────────────────────────────────────────

    @app.before_request
    def _billing_t0() -> None:
        if request.path.startswith("/api/"):
            g._bill_t0 = time.monotonic()

    @app.after_request
    def _billing_meter(response: Any) -> Any:
        try:
            if not request.path.startswith("/api/"):
                return response
            t0 = getattr(g, "_bill_t0", None)
            latency_ms = round((time.monotonic() - t0) * 1000.0, 2) if t0 else 0.0
            rule = getattr(request.url_rule, "rule", None) or request.path
            get_buffer().record(UsageEvent(
                kind="api_request",
                tenant_id=_resolve_tenant(),
                quantity=1.0,
                unit="request",
                route=str(rule),
                method=request.method,
                status=int(response.status_code),
                metadata={"latency_ms": latency_ms},
            ))
        except Exception as exc:  # noqa: BLE001 — metering must never break a response
            logger.debug("metering hook error: %s", exc)
        return response

    # ── read API ─────────────────────────────────────────────────────────────

    @app.get("/api/billing/status")
    def billing_status() -> Any:
        from aureon.operator.metrics import token_usage_totals

        return jsonify({
            "configured": config.ok,
            "missing_env": config.missing(),
            "tenancy_bridge": "on" if jwt_secret else "off",
            "metering": get_buffer().stats(),
            "tokens": token_usage_totals(),
            "charge_endpoint": {"enabled": charge_enabled},
            "model": "record-only metering; the wallet's performance fee is charged "
                     "only via the gated charge-fee proxy",
        })

    @app.get("/api/billing/balance")
    def billing_balance() -> Any:
        tenant, err = _require_tenant()
        if err is not None:
            return err
        missing = _require_supabase()
        if missing is not None:
            return missing
        assert rest is not None
        rows = rest.select(_ACCOUNTS_TABLE, {"user_id": f"eq.{tenant}"}, limit=1)
        if rows is None:
            return jsonify({"error": {"code": 502, "message": "billing backend unreachable"}}), 502
        if not rows:
            return jsonify({"error": {"code": 404, "message": "no gas tank account for this user"}}), 404
        acct = rows[0]
        return jsonify({
            "tenant": tenant,
            "currency": "GBP",
            "account": {k: acct.get(k) for k in (
                "balance", "initial_balance", "high_water_mark", "total_fees_paid",
                "fees_paid_today", "membership_type", "fee_rate", "status", "updated_at",
            )},
        })

    @app.get("/api/billing/usage")
    def billing_usage() -> Any:
        tenant, err = _require_tenant()
        if err is not None:
            return err
        missing = _require_supabase()
        if missing is not None:
            return missing
        assert rest is not None
        try:
            limit = min(500, max(1, int(request.args.get("limit", "100"))))
        except ValueError:
            limit = 100
        filters: Dict[str, str] = {"tenant_id": f"eq.{tenant}"}
        since = request.args.get("since", "")
        if since:
            filters["created_at"] = f"gte.{since}"
        rows = rest.select(_USAGE_TABLE, filters, order="created_at.desc", limit=limit)
        if rows is None:
            return jsonify({"error": {"code": 502, "message": "billing backend unreachable"}}), 502
        return jsonify({
            "tenant": tenant,
            "count": len(rows),
            "events": rows,
            "buffer": get_buffer().stats(),
            "note": "llm_tokens events are untenanted (per-provider) and do not appear here",
        })

    # ── charge-fee proxy (MOVES MONEY — off by default) ──────────────────────

    @app.post("/api/billing/charge-fee")
    def billing_charge_fee() -> Any:
        # OPERATOR-ONLY, and checked FIRST. This route moves money: the charged principal is
        # body["user_id"], and the deduct call is signed with the instance's Supabase service-role
        # key. Without this guard any signed-in end user could debit any other user's gas tank (and
        # fabricate audited fee events against them) using the instance's privileged credential — a
        # counter-audit reproduced exactly that. The env gate and the audit trail were already here;
        # the authentication the module docstring promises was not. Admin-first so a tenant also
        # learns nothing about whether charging is enabled on this instance.
        denied = _admin_denied()
        if denied is not None:
            return denied
        if not charge_enabled:
            return jsonify({"error": {
                "code": 403,
                "message": "charge endpoint disabled (AUREON_BILLING_CHARGE_ENABLED unset)",
            }}), 403
        missing = _require_supabase()
        if missing is not None:
            return missing
        assert rest is not None
        body = request.get_json(silent=True) or {}
        user_id = str(body.get("user_id", "") or "")
        try:
            profit = float(body.get("profit", 0) or 0)
        except (TypeError, ValueError):
            profit = 0.0
        if not user_id or profit <= 0:
            return jsonify({"error": {
                "code": 400,
                "message": "user_id and a positive profit are required",
            }}), 400
        trade_id = body.get("trade_execution_id")
        status, result = rest.call_function(_DEDUCT_FN, {
            "userId": user_id,
            "profit": profit,
            "tradeExecutionId": trade_id,
        })
        # Audit every platform-initiated fee, whatever the outcome.
        get_buffer().record(UsageEvent(
            kind="fee_charge",
            tenant_id=user_id,
            quantity=float(result.get("feeAmount", 0) or 0),
            unit="gbp",
            metadata={"profit": profit, "trade_execution_id": trade_id,
                      "edge_status": status, "caller": "gateway"},
        ))
        if status == 0:
            return jsonify({"error": {"code": 502, "message": "billing backend unreachable",
                                      "detail": result}}), 502
        return jsonify({"forwarded": _DEDUCT_FN, "status": status, "result": result}), status

    logger.info("billing routes registered (metering: %s, charge: %s)",
                get_buffer().stats()["sink"], "on" if charge_enabled else "off")
    return app


__all__ = ["register_billing"]
