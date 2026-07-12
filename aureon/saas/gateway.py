"""
Aureon SaaS — HTTP gateway routes.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

`register_saas_routes(app)` mounts the platform surface onto the operator's Flask
app — so one service (8790) serves operator + cognition + the SaaS catalog behind
the same security envelope (bearer/rate-limit already applied to /api/* by the
operator's before_request gate).

Routes:
  GET  /api/catalog            categorized catalog (12 categories × domains × systems)
  GET  /api/domains            per-domain reachability report
  GET  /api/domains/<domain>   one domain: entry point + its systems
  GET  /api/status             live platform health (honest, often degraded)
  GET  /api/manifests/<name>   a frontend manifest, rendered live (JSON)
  POST /api/manifests/refresh  rebuild catalog + rewrite frontend manifests

Optional tenancy bridge: when ``AUREON_SUPABASE_JWT_SECRET`` is set, these routes
additionally require a valid Supabase JWT (HS256) — stdlib verify, no new dep.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import time
from typing import Any, Dict

logger = logging.getLogger("aureon.saas.gateway")


# ── Supabase JWT (optional, stdlib HS256) ─────────────────────────────────────

def _b64url_decode(seg: str) -> bytes:
    pad = "=" * (-len(seg) % 4)
    return base64.urlsafe_b64decode(seg + pad)


def verify_supabase_jwt(token: str, secret: str) -> Dict[str, Any] | None:
    """Verify an HS256 Supabase JWT with the project secret. Returns claims or None."""
    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        expected = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _b64url_decode(sig_b64)):
            return None
        claims = json.loads(_b64url_decode(payload_b64))
        if isinstance(claims.get("exp"), (int, float)) and claims["exp"] < time.time():
            return None
        return claims
    except Exception:  # noqa: BLE001 — any malformed token is simply invalid
        return None


def register_saas_routes(app: Any) -> Any:
    """Mount the SaaS catalog/status routes onto an existing Flask app."""
    from flask import g, jsonify, request

    from aureon.saas.catalog import build_catalog, render_manifests, write_frontend_manifests
    from aureon.saas.domains import PRODUCT_DOMAINS, domain_report, probe_domain
    from aureon.saas.status import get_platform_status

    jwt_secret = str(os.environ.get("AUREON_SUPABASE_JWT_SECRET", "") or "")

    def _tenant_ok() -> bool:
        """When a Supabase JWT secret is configured, require a valid tenant token."""
        if not jwt_secret:
            return True  # tenancy bridge disabled
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return False
        claims = verify_supabase_jwt(auth[len("Bearer "):].strip(), jwt_secret)
        if claims is None:
            return False
        g.tenant = claims.get("sub")  # user id for downstream scoping
        return True

    def _guarded(fn):
        def wrapper(*a, **k):
            if not _tenant_ok():
                return jsonify({"error": {"code": 401, "message": "valid Supabase token required"}}), 401
            return fn(*a, **k)
        wrapper.__name__ = fn.__name__
        return wrapper

    @app.get("/api/catalog")
    @_guarded
    def saas_catalog():
        return jsonify(build_catalog(use_cache=True))

    @app.get("/api/domains")
    @_guarded
    def saas_domains():
        return jsonify({"product_domains": PRODUCT_DOMAINS, "domains": domain_report()})

    @app.get("/api/domains/<domain>")
    @_guarded
    def saas_domain(domain: str):
        catalog = build_catalog(use_cache=True)
        systems = [
            s for cat in catalog.get("categories", {}).values() for s in cat["systems"]
            if s.get("fs_domain") == domain or s.get("product_domain") == domain
        ]
        return jsonify({"domain": domain, "entry": probe_domain(domain), "system_count": len(systems), "systems": systems[:200]})

    @app.get("/api/status")
    @_guarded
    def saas_status():
        return jsonify(get_platform_status())

    @app.get("/api/manifests/<name>")
    @_guarded
    def saas_manifest(name: str):
        # Live manifests over HTTP so the production frontend can fetch them
        # through the /api proxy instead of relying on baked static files.
        manifests = render_manifests(catalog=build_catalog(use_cache=True), status=get_platform_status())
        if name not in manifests:
            return jsonify({"error": {"code": 404, "message": f"unknown manifest: {name}",
                                      "available": sorted(manifests)}}), 404
        return jsonify(manifests[name])

    @app.post("/api/manifests/refresh")
    @_guarded
    def saas_refresh():
        catalog = build_catalog()  # force rebuild
        written = write_frontend_manifests(catalog=catalog, status=get_platform_status())
        return jsonify({"refreshed": True, "manifests": [p.split("/")[-1] for p in written],
                        "total_systems": catalog.get("total_systems", 0)})

    logger.info("SaaS gateway routes registered (tenancy bridge: %s)",
                "on" if jwt_secret else "off")
    return app


__all__ = ["register_saas_routes", "verify_supabase_jwt"]
