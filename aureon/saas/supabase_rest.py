"""
Aureon SaaS — minimal Supabase REST client (billing).
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Sync, `requests`-based access to PostgREST tables and edge functions using the
service-role key — the same header pattern the UI bridge already uses
(`aureon/bridges/aureon_ui_bridge.py`), no supabase-py SDK.

Design rules:
  • Offline-safe: every method catches transport errors and returns a benign
    value (False / None / (0, {...})) — nothing here may raise into a request path.
  • Injectable session: tests pass a stub with .post/.get; production uses a
    shared requests.Session.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

logger = logging.getLogger("aureon.saas.supabase_rest")


@dataclass(frozen=True)
class SupabaseConfig:
    """Connection settings for the Supabase project (service-role access)."""

    url: str
    service_key: str
    timeout_s: float = 5.0

    @classmethod
    def from_env(cls) -> SupabaseConfig:
        return cls(
            url=str(os.environ.get("SUPABASE_URL", "") or "").rstrip("/"),
            service_key=str(os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "") or ""),
            timeout_s=float(os.environ.get("AUREON_BILLING_HTTP_TIMEOUT_S", "5") or 5),
        )

    @property
    def ok(self) -> bool:
        return bool(self.url and self.service_key)

    def missing(self) -> List[str]:
        out = []
        if not self.url:
            out.append("SUPABASE_URL")
        if not self.service_key:
            out.append("SUPABASE_SERVICE_ROLE_KEY")
        return out


class SupabaseRest:
    """Thin PostgREST + edge-function caller. Never raises into callers."""

    def __init__(self, config: SupabaseConfig, session: Any | None = None) -> None:
        self.config = config
        if session is not None:
            self._session = session
        else:
            import requests

            self._session = requests.Session()

    def _headers(self) -> Dict[str, str]:
        return {
            "apikey": self.config.service_key,
            "Authorization": f"Bearer {self.config.service_key}",
            "Content-Type": "application/json",
        }

    def insert(self, table: str, rows: List[Dict[str, Any]]) -> bool:
        """Insert rows into a table via PostgREST. True on 2xx."""
        if not self.config.ok or not rows:
            return False
        try:
            resp = self._session.post(
                f"{self.config.url}/rest/v1/{table}",
                json=rows,
                headers={**self._headers(), "Prefer": "return=minimal"},
                timeout=self.config.timeout_s,
            )
            if 200 <= resp.status_code < 300:
                return True
            logger.warning("supabase insert %s -> %s", table, resp.status_code)
            return False
        except Exception as exc:  # noqa: BLE001 — transport errors must not propagate
            logger.warning("supabase insert %s failed: %s", table, exc)
            return False

    def select(
        self,
        table: str,
        filters: Dict[str, str] | None = None,
        order: str = "",
        limit: int = 100,
    ) -> List[Dict[str, Any]] | None:
        """Select rows via PostgREST. Filters use PostgREST syntax (col -> 'eq.value').
        Returns None on any failure (distinct from an empty result)."""
        if not self.config.ok:
            return None
        params: Dict[str, str] = {"select": "*", "limit": str(max(1, limit))}
        params.update(filters or {})
        if order:
            params["order"] = order
        try:
            resp = self._session.get(
                f"{self.config.url}/rest/v1/{table}",
                params=params,
                headers=self._headers(),
                timeout=self.config.timeout_s,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data if isinstance(data, list) else None
            logger.warning("supabase select %s -> %s", table, resp.status_code)
            return None
        except Exception as exc:  # noqa: BLE001
            logger.warning("supabase select %s failed: %s", table, exc)
            return None

    def call_function(self, name: str, payload: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        """Invoke an edge function. Returns (status_code, json) — (0, {error}) on transport failure."""
        if not self.config.ok:
            return 0, {"error": "supabase not configured", "missing": self.config.missing()}
        try:
            resp = self._session.post(
                f"{self.config.url}/functions/v1/{name}",
                json=payload,
                headers=self._headers(),
                timeout=self.config.timeout_s,
            )
            try:
                body = resp.json()
            except Exception:  # noqa: BLE001 — non-JSON body
                body = {"raw": getattr(resp, "text", "")[:500]}
            if not isinstance(body, dict):
                body = {"result": body}
            return int(resp.status_code), body
        except Exception as exc:  # noqa: BLE001
            logger.warning("supabase function %s failed: %s", name, exc)
            return 0, {"error": str(exc)}


__all__ = ["SupabaseConfig", "SupabaseRest"]
