"""
Aureon Operator — request identity resolution.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

One place that answers "who is this request?" for the whole HTTP surface, reconciling the two auth
schemes the operator supports:

  * **admin / operator** — a single static instance key (``AUREON_OPERATOR_API_KEY``), checked in
    constant time. This is the control plane; it manages the instance's own defaults and global state.
  * **tenant / end user** — a Supabase HS256 JWT (verified with ``AUREON_SUPABASE_JWT_SECRET``). The
    JWT ``sub`` becomes the tenant id, and every per-user store (keystore, billing) is namespaced by it.
  * **open** — neither secret configured: auth is disabled (dev / offline / single-operator default),
    exactly as before this module existed.

``resolve_identity`` is pure (no Flask, no env reads inside): the caller passes the ``Authorization``
header and the two secrets it computed once at app start, and gets back an :class:`Identity`. The
**zero-regression invariant** is structural — when ``jwt_secret`` is empty the tenant branch is never
reached, so the resolver behaves exactly like the old ``check_bearer`` static-key gate.

The Supabase JWT verifier (``verify_supabase_jwt``) lives here too so both the operator gate and the
SaaS gateway share one stdlib HS256 implementation (no new dependency).

Gary Leckey · Aureon Institute
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any, Dict

# ── Supabase JWT (optional, stdlib HS256) ─────────────────────────────────────

def _b64url_decode(seg: str) -> bytes:
    pad = "=" * (-len(seg) % 4)
    return base64.urlsafe_b64decode(seg + pad)


#: Small leeway for clock drift between the token issuer and this host.
_CLOCK_SKEW_S = 60.0

#: Supabase signs its *project API keys* with the same project JWT secret as user tokens. The anon key
#: is a public, client-side value — it must never be mistakable for an end user. They carry no ``sub``
#: today (so the resolver already refuses them), but reject the roles explicitly rather than rely on
#: that staying true.
_API_KEY_ROLES = frozenset({"anon", "service_role"})


def verify_supabase_jwt(token: str, secret: str) -> Dict[str, Any] | None:
    """Verify an HS256 Supabase JWT with the project secret. Returns claims or None.

    HS256 is **forced**, never read from the token header, so the classic algorithm-confusion attacks
    (``alg: none``, or an RS256 header verified with a public key as an HMAC secret) cannot apply —
    an attacker who cannot produce a valid HS256 signature cannot get past the compare below.

    Claim checks, all deliberate:
      * ``exp`` is **required**. A token without an expiry never expires and cannot be revoked; a
        signed-but-eternal bearer is a worse failure than a rejected login. (Supabase always sets it —
        this refuses to depend on that.)
      * ``nbf``, when present, is honored, so a not-yet-valid token is not accepted early.
      * project API-key roles are refused outright (see :data:`_API_KEY_ROLES`).
    """
    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        expected = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _b64url_decode(sig_b64)):
            return None
        claims = json.loads(_b64url_decode(payload_b64))
        if not isinstance(claims, dict):
            return None
        now = time.time()
        exp = claims.get("exp")
        if not isinstance(exp, (int, float)) or exp < now:
            return None
        nbf = claims.get("nbf")
        if isinstance(nbf, (int, float)) and nbf > now + _CLOCK_SKEW_S:
            return None
        if claims.get("role") in _API_KEY_ROLES:
            return None
        return claims
    except Exception:  # noqa: BLE001 — any malformed token is simply invalid
        return None


# ── Request identity ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Identity:
    """Who a request is. ``tenant`` is set only for an end-user JWT (its ``sub``)."""

    kind: str            # "admin" | "tenant" | "open"
    tenant: str | None    # JWT sub for tenants, else None
    ok: bool             # False ⇒ the gate should 401

    def to_dict(self) -> Dict[str, Any]:
        return {"kind": self.kind, "tenant": self.tenant, "ok": self.ok}


def _bearer_token(auth_header: str | None) -> str | None:
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    tok = auth_header[len("Bearer "):].strip()
    return tok or None


def resolve_identity(auth_header: str | None, *, operator_key: str, jwt_secret: str) -> Identity:
    """Resolve a request to an :class:`Identity`. Pure — pass the secrets, get the answer.

    Order (must not regress the old static-key gate):
      1. both secrets empty            → open (auth disabled; unchanged single-operator behavior).
      2. static key matches            → admin (the instance control plane).
      3. else a valid Supabase JWT     → tenant(``sub``) — only reachable when ``jwt_secret`` is set.
      4. else                          → not ok (the gate returns 401).
    """
    # A key that is only whitespace is not a key — treat it as unset, or a stray space in the env
    # would flip an open instance into permanently-locked-out (nothing could ever match it).
    operator_key = (operator_key or "").strip()
    jwt_secret = jwt_secret or ""

    # 1 — nothing configured: auth disabled, exactly as before.
    if not operator_key and not jwt_secret:
        return Identity(kind="open", tenant=None, ok=True)

    token = _bearer_token(auth_header)
    if not token:
        return Identity(kind="open", tenant=None, ok=False)

    # 2 — the static instance key: the admin / operator plane. compare_digest raises TypeError on
    # non-ASCII str input, so compare bytes — a unicode Authorization header must be a clean 401,
    # never an unhandled 500.
    if operator_key and hmac.compare_digest(token.encode("utf-8"), operator_key.encode("utf-8")):
        return Identity(kind="admin", tenant=None, ok=True)

    # 3 — a Supabase JWT: the end-user / tenant plane. Unreachable when jwt_secret is empty.
    if jwt_secret:
        claims = verify_supabase_jwt(token, jwt_secret)
        sub = claims.get("sub") if isinstance(claims, dict) else None
        if isinstance(sub, str) and sub:
            return Identity(kind="tenant", tenant=sub, ok=True)

    # 4 — a token was presented but matched nothing valid.
    return Identity(kind="open", tenant=None, ok=False)


__all__ = ["Identity", "resolve_identity", "verify_supabase_jwt", "_b64url_decode"]
