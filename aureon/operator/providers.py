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

import json
import logging
import os
import uuid
from typing import Dict, Generator, List, Optional

from aureon.inhouse_ai.llm_adapter import (
    AureonLocalAdapter,
    AureonStubAdapter,
    LLMAdapter,
    LLMResponse,
    StreamChunk,
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
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
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
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
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
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self.model = model or os.environ.get("GEMINI_MODEL", self.DEFAULT_MODEL)
        self.base_url = (base_url or os.environ.get("GEMINI_BASE_URL", self.DEFAULT_BASE_URL)).rstrip("/")
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
        tools: Optional[List[Dict]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs,
    ) -> LLMResponse:
        if not self._session:
            return LLMResponse(text="[ERROR] requests library not available", stop_reason="error")
        if _llm_http_disabled():
            return LLMResponse(text="[ERROR] LLM HTTP disabled by audit/offline mode", stop_reason="error")

        payload = self._to_gemini_contents(messages, system)
        payload["generationConfig"] = {
            "maxOutputTokens": int(max_tokens),
            "temperature": float(temperature),
        }
        url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
        try:
            timeout = float(os.environ.get("AUREON_LLM_REQUEST_TIMEOUT_S", "30") or "30")
            resp = self._session.post(url, json=payload, timeout=max(1.0, timeout))
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:  # noqa: BLE001 — normalise any transport failure
            logger.error("Gemini request failed: %s", e)
            return LLMResponse(text=f"[ERROR] {e}", stop_reason="error")

        text_parts: List[str] = []
        for cand in data.get("candidates", []) or []:
            for part in (cand.get("content", {}) or {}).get("parts", []) or []:
                if part.get("text"):
                    text_parts.append(str(part["text"]))
        usage_meta = data.get("usageMetadata", {}) or {}
        return LLMResponse(
            text="\n".join(text_parts),
            stop_reason="end_turn",
            usage={
                "input_tokens": int(usage_meta.get("promptTokenCount", 0) or 0),
                "output_tokens": int(usage_meta.get("candidatesTokenCount", 0) or 0),
            },
            model=self.model,
            raw=data,
        )

    def stream(
        self,
        messages: List[Dict],
        system: str = "",
        tools: Optional[List[Dict]] = None,
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
        return bool(self.api_key) and self._session is not None and not _llm_http_disabled()


# ─────────────────────────────────────────────────────────────────────────────
# Provider set assembly — the switchboard's line-up
# ─────────────────────────────────────────────────────────────────────────────

_OFFLINE_STUB_ANSWER = (
    "[Aureon offline provider] No cloud AI key configured, so this line answers "
    "from the grounded repo context only. Set OPENAI_API_KEY / XAI_API_KEY / "
    "GEMINI_API_KEY to fan out across live models."
)


def _build_from_spec(spec) -> Optional[LLMAdapter]:
    """Resolve one ModelSpec into a live adapter, or None if it can't run."""
    kind = spec.kind
    try:
        if kind == "openai":
            return AureonOpenAIAdapter(model=spec.model or None)
        if kind == "grok":
            return AureonGrokAdapter(model=spec.model or None)
        if kind == "gemini":
            return AureonGeminiAdapter(model=spec.model or None)
        if kind == "anthropic":
            from aureon.inhouse_ai.llm_adapter import AureonAnthropicAdapter

            adapter = AureonAnthropicAdapter(model=spec.model or None)
            return adapter if adapter.health_check() else None
        if kind == "local":
            adapter = AureonLocalAdapter(model=spec.model or None)
            return adapter if adapter.health_check() else None
        if kind == "stub":
            return AureonStubAdapter(spec.options.get("message", _OFFLINE_STUB_ANSWER), model=spec.model or "stub")
    except Exception as exc:  # noqa: BLE001 — a bad line must never sink the board
        logger.warning("provider %s (%s) failed to initialise: %s", spec.name, kind, exc)
    return None


def build_registry(
    specs=None,
    *,
    allow_local: bool = True,
    force_offline: Optional[bool] = None,
) -> Dict[str, LLMAdapter]:
    """
    Assemble the switchboard from a list of ``ModelSpec`` (config-driven).

    Only rows that are enabled, key-present, and successfully initialised are
    included — so the registry can list every flagship model you *might* use and
    the runtime dials only the ones actually configured. With none live (or under
    the repo's offline/audit guards) it degrades to a local model or a single
    offline stub, so the operator always has at least one working line.
    """
    from aureon.operator.config import default_registry

    if specs is None:
        specs = default_registry()
    offline = _llm_http_disabled() if force_offline is None else bool(force_offline)

    providers: Dict[str, LLMAdapter] = {}
    if not offline:
        for spec in specs:
            if not spec.enabled or not spec.key_present():
                continue
            if spec.kind == "local" and not allow_local:
                continue
            adapter = _build_from_spec(spec)
            if adapter is not None:
                providers[spec.name] = adapter

    if providers:
        return providers

    return {"offline": AureonStubAdapter(_OFFLINE_STUB_ANSWER, model="aureon-operator-offline")}


def build_provider_set(
    *,
    allow_local: bool = True,
    force_offline: Optional[bool] = None,
) -> Dict[str, LLMAdapter]:
    """Convenience wrapper: assemble from the default registry (back-compat)."""
    return build_registry(allow_local=allow_local, force_offline=force_offline)


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
    "describe_provider_set",
]
