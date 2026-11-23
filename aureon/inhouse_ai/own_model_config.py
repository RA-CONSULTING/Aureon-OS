"""Stable configuration for Aureon's own local OpenAI-compatible inference.

This is not an Ollama model or a fallback provider. The model name is pinned
and only a literal loopback HTTP origin with an explicit ``/v1`` path is valid.
"""

from __future__ import annotations

import ipaddress
import os
from urllib.parse import urlsplit

AUREON_OWN_PROVIDER = "aureon_own_model"
AUREON_OWN_DEFAULT_BASE_URL = "http://127.0.0.1:11435/v1"
AUREON_OWN_DEFAULT_MODEL = "aureon-7b-v65k"


def aureon_own_route() -> tuple[str, str]:
    base = (
        os.environ.get("AUREON_OWN_LLM_BASE_URL", "") or AUREON_OWN_DEFAULT_BASE_URL
    ).strip().rstrip("/")
    model = (
        os.environ.get("AUREON_OWN_LLM_MODEL", "") or AUREON_OWN_DEFAULT_MODEL
    ).strip()
    return base, model


def is_aureon_own_route(base_url: str, model: str) -> bool:
    """Accept the pinned model on an explicit, unauthenticated loopback route."""

    expected_base, expected_model = aureon_own_route()
    candidate = str(base_url or "").strip().rstrip("/")
    if (
        candidate != expected_base
        or str(model).strip() != expected_model
        or expected_model != AUREON_OWN_DEFAULT_MODEL
    ):
        return False
    try:
        parsed = urlsplit(candidate)
        address = ipaddress.ip_address(str(parsed.hostname or ""))
        port = parsed.port
    except (TypeError, ValueError):
        return False
    return bool(
        parsed.scheme == "http"
        and address.is_loopback
        and port == 11435
        and parsed.path.rstrip("/") == "/v1"
        and parsed.username is None
        and parsed.password is None
        and not parsed.query
        and not parsed.fragment
    )


__all__ = [
    "AUREON_OWN_DEFAULT_BASE_URL",
    "AUREON_OWN_DEFAULT_MODEL",
    "AUREON_OWN_PROVIDER",
    "aureon_own_route",
    "is_aureon_own_route",
]
