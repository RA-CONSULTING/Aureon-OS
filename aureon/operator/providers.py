"""
Aureon Operator — provider adapters (the switchboard's lines).
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Each external AI (ChatGPT, Grok, Gemini, Claude) is one *line* on the
switchboard. They all speak the in-house ``LLMAdapter`` interface
(:mod:`aureon.inhouse_ai.llm_adapter`), so the operator never learns a vendor
SDK — it only ever calls ``prompt()`` / ``stream()``.

Design rules (offline-first):
  • A provider is only wired when its API key is present.
  • With no keys — or under the repo's audit/offline guards
    (``AUREON_LLM_OFFLINE`` / ``AUREON_AUDIT_MODE`` / ``AUREON_DISABLE_LLM_HTTP``)
    — the switchboard degrades to a local model (if reachable) or a stub, so
    the operator always answers without touching the network.

OpenAI and xAI/Grok both expose an OpenAI-compatible ``/v1/chat/completions``,
so those adapters reuse ``AureonLocalAdapter`` almost verbatim (base-URL + key).
Gemini speaks its own ``generativelanguage`` REST shape and gets a thin adapter
that normalises into the shared ``LLMResponse``.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Generator, List

from aureon.inhouse_ai.llm_adapter import (
    AureonLocalAdapter,
    AureonStubAdapter,
    AureonUnavailableAdapter,
    LLMAdapter,
    LLMResponse,
    StreamChunk,
    _aureon_own_adapter,
    _aureon_own_route,
    _is_aureon_own_route,
    _llm_http_disabled,
)

logger = logging.getLogger("aureon.operator.providers")


# ─────────────────────────────────────────────────────────────────────────────
# OpenAI-compatible providers (ChatGPT, Grok) — thin base-URL + key wrappers
# ─────────────────────────────────────────────────────────────────────────────


class AureonOpenAIAdapter(AureonLocalAdapter):
    """ChatGPT via the OpenAI ``/v1`` API. OpenAI-compatible → reuse the local adapter."""

    DEFAULT_BASE_URL = "https://api.openai.com/v1"
    DEFAULT_MODEL = "gpt-4o-mini"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
    ):
        super().__init__(
            base_url=base_url or os.environ.get("OPENAI_BASE_URL", self.DEFAULT_BASE_URL),
            model=model or os.environ.get("OPENAI_MODEL", self.DEFAULT_MODEL),
            api_key=api_key or os.environ.get("OPENAI_API_KEY", ""),
        )
        # Cloud vendors are never the Ollama native endpoint; keep the OpenAI path.
        self._prefer_native = False


class AureonGrokAdapter(AureonLocalAdapter):
    """Grok via the xAI ``/v1`` API. OpenAI-compatible → reuse the local adapter."""

    DEFAULT_BASE_URL = "https://api.x.ai/v1"
    DEFAULT_MODEL = "grok-2-latest"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
    ):
        super().__init__(
            base_url=base_url or os.environ.get("XAI_BASE_URL", self.DEFAULT_BASE_URL),
            model=model or os.environ.get("XAI_MODEL", self.DEFAULT_MODEL),
            api_key=api_key or os.environ.get("XAI_API_KEY", ""),
        )
        self._prefer_native = False


# ─────────────────────────────────────────────────────────────────────────────
# Gemini — Google generativelanguage REST, normalised into LLMResponse
# ─────────────────────────────────────────────────────────────────────────────


class AureonGeminiAdapter(LLMAdapter):
    """
    Gemini via Google's ``generativelanguage`` REST API.

    Kept deliberately thin: one POST to ``:generateContent`` and a
    normalisation of the ``candidates[0].content.parts[*].text`` shape into the
    shared ``LLMResponse``. Tool-calling is not wired (not needed by the
    operator's fan-out); the operator only reads ``.text``.
    """

    DEFAULT_MODEL = "gemini-1.5-flash"
    DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
    ):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self.model = model or os.environ.get("GEMINI_MODEL", self.DEFAULT_MODEL)
        self.base_url = (base_url or os.environ.get("GEMINI_BASE_URL", self.DEFAULT_BASE_URL)).rstrip("/")
        self._session: Any | None = None
        try:
            import requests

            self._session = requests.Session()
        except ImportError:
            self._session = None
            logger.warning("requests not installed — Gemini adapter degraded")

    @staticmethod
    def _to_gemini_contents(messages: List[Dict], system: str) -> Dict:
        """Flatten the shared message list into Gemini ``contents`` + system instruction."""
        contents = []
        for msg in messages:
            role = "model" if msg.get("role") == "assistant" else "user"
            content = msg.get("content", "")
            if isinstance(content, list):
                parts_text = []
                for c in content:
                    if isinstance(c, dict) and c.get("type") == "text":
                        parts_text.append(str(c.get("text", "")))
                    elif isinstance(c, str):
                        parts_text.append(c)
                content = "\n".join(parts_text)
            contents.append({"role": role, "parts": [{"text": str(content)}]})
        payload: Dict = {"contents": contents}
        if system:
            payload["systemInstruction"] = {"parts": [{"text": str(system)}]}
        return payload

    def prompt(
        self,
        messages: List[Dict],
        system: str = "",
        tools: List[Dict] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs,
    ) -> LLMResponse:
        return LLMResponse(
            text="[ERROR] Aureon's own model is required; the external Gemini route is disabled.",
            stop_reason="error",
            model=self.model,
            raw={"error": "aureon_own_model_required"},
        )

    def stream(
        self,
        messages: List[Dict],
        system: str = "",
        tools: List[Dict] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs,
    ) -> Generator[StreamChunk, None, None]:
        # Simulate streaming from the one-shot response (keeps the adapter thin).
        response = self.prompt(messages, system, tools, max_tokens, temperature, **kwargs)
        for word in response.text.split(" "):
            yield StreamChunk(text=word + " ")
        yield StreamChunk(done=True, stop_reason=response.stop_reason)

    def health_check(self) -> bool:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Provider set assembly — the switchboard's line-up
# ─────────────────────────────────────────────────────────────────────────────

_OFFLINE_STUB_ANSWER = (
    "[Aureon offline provider] No cloud AI key configured, so this line answers "
    "from the grounded repo context only. Set OPENAI_API_KEY / XAI_API_KEY / "
    "GEMINI_API_KEY to fan out across live models."
)


def _build_from_spec(spec) -> LLMAdapter | None:
    """Resolve only an own-model spec; external catalog rows stay disabled."""
    kind = spec.kind
    if kind not in ("local", "aureon", "own", "aureon_own"):
        return AureonUnavailableAdapter(
            "Aureon's own model is required; this external provider is disabled.",
            model="aureon_own_model_required",
        )
    try:
        own_base, own_model = _aureon_own_route()
        if spec.model and str(spec.model) != own_model:
            return None
        if not _is_aureon_own_route(own_base, own_model):
            return None
        adapter = _aureon_own_adapter()
        return adapter if adapter.health_check() else None
    except Exception as exc:  # noqa: BLE001 — a bad line must never sink the board
        logger.warning("provider %s (%s) failed to initialise: %s", spec.name, kind, exc)
    return None


def build_registry(
    specs=None,
    *,
    allow_local: bool = True,
    force_offline: bool | None = None,
) -> Dict[str, LLMAdapter]:
    """Return only Aureon's own model, or an explicitly unavailable line."""
    del specs, allow_local
    if force_offline is True or (force_offline is None and _llm_http_disabled()):
        return {
            "aureon-own": AureonUnavailableAdapter(
                "Aureon's own model is unavailable while LLM HTTP is disabled.",
                model="aureon-own-offline",
            )
        }
    try:
        own = _aureon_own_adapter()
        if own.health_check():
            return {"aureon-own": own}
    except Exception as exc:  # noqa: BLE001 — failure must not enable another provider
        logger.debug("Aureon own-model provider unavailable: %s", exc)
    return {
        "aureon-own": AureonUnavailableAdapter(
            "Aureon's own model is unavailable; external provider fallback is disabled.",
            model="aureon-own-unavailable",
        )
    }


def build_provider_set(
    *,
    allow_local: bool = True,
    force_offline: bool | None = None,
) -> Dict[str, LLMAdapter]:
    """Convenience wrapper: assemble from the default registry (back-compat)."""
    return build_registry(allow_local=allow_local, force_offline=force_offline)


def build_adapter(kind: str, *, api_key: str, base_url: Any = None, model: str = "") -> LLMAdapter:
    """Construct only the configured Aureon own-model route; reject all others."""
    del api_key
    own_base, own_model = _aureon_own_route()
    candidate_base = str(base_url or own_base)
    candidate_model = str(model or own_model)
    if kind in ("local", "aureon", "own", "aureon_own") and _is_aureon_own_route(
        candidate_base, candidate_model
    ):
        return _aureon_own_adapter()
    return AureonUnavailableAdapter(
        "Aureon's own model is required; this external or substitute provider is disabled.",
        model="aureon_own_model_required",
    )


def build_provider_set_from_entries(entries: Dict[str, Dict[str, Any]]) -> Dict[str, LLMAdapter]:
    """Assemble a switchboard from explicit keystore ``entries`` — **no ``os.environ`` reads/writes**.

    ``entries`` is a keystore dict (``{provider_id: {api_key, base_url, model, enabled}}``), e.g.
    ``keystore.load(tenant)``. Only enabled LLM providers with a key are built. Keyed by the provider's
    registry name, matching ``build_registry``. This is the seam for per-tenant live reasoning: a future
    ``AureonOperator(providers=build_provider_set_from_entries(keystore.load(tenant)))`` runs a tenant's
    own models without ever mutating the shared process env.
    """
    from aureon.operator.provider_catalog import get_provider

    out: Dict[str, LLMAdapter] = {}
    for provider_id, entry in entries.items():
        if not bool(entry.get("enabled", True)):
            continue
        api_key = str(entry.get("api_key", "") or "")
        info = get_provider(provider_id)
        if info is None or not api_key:
            continue
        try:
            out[info.registry_name] = build_adapter(
                info.kind, api_key=api_key,
                base_url=str(entry.get("base_url", "") or "") or info.default_base_url,
                model=str(entry.get("model", "") or "") or info.default_model,
            )
        except Exception:  # noqa: BLE001 — a bad entry is skipped, never sinks the set
            logger.warning("could not build adapter for provider %s", provider_id)
    return out


def describe_provider_set(providers: Dict[str, LLMAdapter]) -> List[Dict[str, str]]:
    """Compact, log-safe description of the active switchboard (no secrets)."""
    described = []
    for name, adapter in providers.items():
        described.append(
            {
                "name": name,
                "adapter": type(adapter).__name__,
                "model": str(getattr(adapter, "model", "") or ""),
            }
        )
    return described


__all__ = [
    "AureonOpenAIAdapter",
    "AureonGrokAdapter",
    "AureonGeminiAdapter",
    "build_registry",
    "build_provider_set",
    "build_adapter",
    "build_provider_set_from_entries",
    "describe_provider_set",
]
