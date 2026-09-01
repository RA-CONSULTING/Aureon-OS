"""
LLM Adapter Layer — In-House Sovereign AI
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Replaces Anthropic / OpenAI / Copilot with fully in-house alternatives:

  AureonLocalAdapter   — self-hosted LLM via HTTP (Ollama, vLLM, llama.cpp, HF TGI)
  AureonBrainAdapter   — existing AureonBrain intelligence as reasoning engine
  AureonHybridAdapter  — local LLM + AureonBrain combined

All adapters implement the same LLMAdapter interface so agents are backend-agnostic.
"""

from __future__ import annotations

import ipaddress
import json
import logging
import os
import re
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional
from urllib.parse import urlsplit

from aureon.ollama_config import (
    ensure_ollama_runtime_config,
    is_ollama_cloud_url,
    looks_like_ollama_url,
    ollama_authorization_headers,
    resolve_ollama_api_key,
    resolve_ollama_openai_base_url,
    resolve_ollama_reasoning_effort,
)

logger = logging.getLogger("aureon.inhouse_ai.llm")


def _env_truthy(name: str) -> bool:
    return str(os.environ.get(name, "")).strip().lower() in {"1", "true", "yes", "on"}


def _llm_http_disabled() -> bool:
    """Return True when local-model HTTP calls should be skipped."""
    if _env_truthy("AUREON_DISABLE_LLM_HTTP") or _env_truthy("AUREON_LLM_OFFLINE"):
        return True
    if _env_truthy("AUREON_AUDIT_MODE") and not _env_truthy("AUREON_LLM_ALLOW_HTTP_IN_AUDIT"):
        return True
    return False


def _llm_timeout(default_s: float, audit_default_s: float) -> float:
    return audit_default_s if _env_truthy("AUREON_AUDIT_MODE") else default_s


def _read_small_json(path: Path) -> Dict[str, Any]:
    try:
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}
    return {}


def _aureon_cognitive_context_summary() -> str:
    """Return compact local cognitive proof for Aureon+Ollama system prompts."""
    root = Path(__file__).resolve().parents[2]
    bridge = _read_small_json(root / "frontend/public/aureon_ollama_cognitive_bridge.json")
    guardian = _read_small_json(root / "frontend/public/aureon_agent_creative_process_guardian.json")
    cognitive = _read_small_json(root / "frontend/public/aureon_cognitive_trade_evidence.json")
    harmonic = _read_small_json(root / "frontend/public/aureon_harmonic_affect_state.json")

    bridge_value = bridge.get("summary")
    guardian_value = guardian.get("summary")
    cognitive_value = cognitive.get("summary")
    harmonic_value = harmonic.get("summary")
    bridge_summary: Dict[str, Any] = bridge_value if isinstance(bridge_value, dict) else {}
    guardian_summary: Dict[str, Any] = (
        guardian_value if isinstance(guardian_value, dict) else {}
    )
    cognitive_summary: Dict[str, Any] = (
        cognitive_value if isinstance(cognitive_value, dict) else {}
    )
    harmonic_summary: Dict[str, Any] = (
        harmonic_value if isinstance(harmonic_value, dict) else {}
    )
    if not any((bridge_summary, guardian_summary, cognitive_summary, harmonic_summary)):
        return ""

    lines = [
        "AUREON UNIFIED COGNITIVE SYSTEM CONTEXT",
        f"ollama_bridge_status={bridge.get('status', 'unknown')}",
        f"resolved_model={bridge_summary.get('resolved_model', '')}",
        f"hnc_auris_ready={bridge_summary.get('hnc_auris_ready', guardian_summary.get('hnc_auris_ready', 'unknown'))}",
        f"metacognitive_ready={bridge_summary.get('metacognitive_ready', guardian_summary.get('metacognitive_ready', 'unknown'))}",
        f"role_contracts_ready={bridge_summary.get('role_contracts_ready', guardian_summary.get('who_what_where_when_how_act_ready', 'unknown'))}",
        f"runtime_action_mode={cognitive_summary.get('action_mode', 'unknown')}",
        f"harmonic_affect_phase={harmonic_summary.get('affect_phase', 'unknown')}",
        "authority=no live trading, payment, official filing, credential reveal, or destructive OS bypass",
        "identity=Aureon uses Ollama as its local language cortex and Aureon cognition as memory, guards, evidence, and fallback",
    ]
    return "\n".join(lines)

# ─────────────────────────────────────────────────────────────────────────────
# Response types
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class ToolCall:
    """A tool invocation requested by the model."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    arguments: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    """Unified response from any adapter."""

    text: str = ""
    tool_calls: List[ToolCall] = field(default_factory=list)
    stop_reason: str = "end_turn"  # end_turn | tool_use | max_tokens
    usage: Dict[str, int] = field(default_factory=dict)
    model: str = ""
    raw: Any = None  # adapter-specific raw response

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


@dataclass
class StreamChunk:
    """A single chunk during streaming."""

    text: str = ""
    tool_call: Optional[ToolCall] = None
    done: bool = False
    stop_reason: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# Base adapter
# ─────────────────────────────────────────────────────────────────────────────


class LLMAdapter(ABC):
    """
    Abstract base for all LLM backends.
    Every adapter must implement prompt() and stream().
    """

    @abstractmethod
    def prompt(
        self,
        messages: List[Dict[str, Any]],
        system: str = "",
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs,
    ) -> LLMResponse:
        """Send a prompt and return the complete response."""

    @abstractmethod
    def stream(
        self,
        messages: List[Dict[str, Any]],
        system: str = "",
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs,
    ) -> Generator[StreamChunk, None, None]:
        """Stream response token-by-token."""

    def health_check(self) -> bool:
        """Return True if the backend is reachable."""
        return True


# ─────────────────────────────────────────────────────────────────────────────
# AureonLocalAdapter — self-hosted model server
# ─────────────────────────────────────────────────────────────────────────────


class AureonLocalAdapter(LLMAdapter):
    """
    Connects to a self-hosted LLM server via HTTP.

    Supported backends (all expose an OpenAI-compatible /v1/chat/completions):
      - Ollama        (default: http://localhost:11434/v1)
      - vLLM          (default: http://localhost:8000/v1)
      - llama.cpp     (default: http://localhost:8080/v1)
      - HuggingFace TGI (default: http://localhost:8080/v1)
      - LocalAI       (default: http://localhost:8080/v1)

    Environment variables:
      AUREON_LLM_BASE_URL   — override base URL
      AUREON_LLM_MODEL      — override model name
      AUREON_LLM_API_KEY    — optional API key for the local server
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        *,
        strict_loopback_no_redirects: bool = False,
    ):
        if base_url is None and not str(
            os.environ.get("AUREON_LLM_BASE_URL", "") or ""
        ).strip():
            ensure_ollama_runtime_config(explicit_config=api_key is not None)
        configured_base_url = (
            base_url
            or os.environ.get("AUREON_LLM_BASE_URL", "http://localhost:11434/v1")
        )
        self.base_url = (
            resolve_ollama_openai_base_url(configured_base_url)
            if looks_like_ollama_url(configured_base_url)
            else configured_base_url.rstrip("/")
        )
        # Track whether the caller pinned a specific model. If they didn't,
        # the health check is allowed to substitute a working installed model
        # so the voice layer doesn't silently 404 / 500 against a name that
        # isn't actually loadable on this machine.
        env_model = os.environ.get("AUREON_LLM_MODEL")
        self._model_pinned = bool(model or env_model)
        self.model = model or env_model or "llama3"
        self._api_key_explicit = api_key is not None
        self.api_key = (
            resolve_ollama_api_key(api_key)
            if looks_like_ollama_url(self.base_url)
            else (api_key or os.environ.get("AUREON_LLM_API_KEY", ""))
        )
        self._model_verified: bool = False
        self.strict_loopback_no_redirects = False

        # Ollama detection. The OpenAI /v1 shim Ollama ships with silently
        # drops the ``keep_alive`` payload field, so the model unloads every
        # 5 min and every follow-up request hits a cold decode. We detect
        # Ollama by base_url pattern (or env override) and route chat
        # requests through the NATIVE /api/chat endpoint instead, which
        # does honour keep_alive. Non-Ollama backends keep the /v1 path.
        env_prefer = os.environ.get("AUREON_LLM_PREFER_NATIVE", "").lower()
        default_native = ":11434" in self.base_url
        if env_prefer in ("1", "true", "yes"):
            self._prefer_native = True
        elif env_prefer in ("0", "false", "no"):
            self._prefer_native = False
        else:
            self._prefer_native = default_native
        # Derive the native root (strip trailing /v1) for Ollama native calls.
        self._native_root = self.base_url[:-3] if self.base_url.endswith("/v1") else self.base_url

        self._keep_alive = os.environ.get("AUREON_LLM_KEEP_ALIVE", "30m") or None

        self._session: Any = None
        try:
            import requests

            self._session = requests.Session()
            if strict_loopback_no_redirects:
                self.enable_strict_loopback_transport()
        except ImportError:
            self._session = None
            logger.warning("requests not installed — HTTP adapter degraded")

    @staticmethod
    def _literal_loopback_origin(url: str) -> tuple[str, str, int]:
        """Return one literal HTTP loopback origin or fail closed.

        Hostnames are deliberately excluded. Even ``localhost`` can be
        influenced by name-resolution configuration, whereas a literal
        loopback address cannot route off host.
        """

        try:
            parsed = urlsplit(str(url or "").strip())
            host = str(parsed.hostname or "")
            address = ipaddress.ip_address(host)
            port = parsed.port
        except (TypeError, ValueError) as exc:
            raise ValueError("strict_loopback_url_invalid") from exc
        if (
            parsed.scheme != "http"
            or not address.is_loopback
            or port is None
            or parsed.username is not None
            or parsed.password is not None
            or parsed.fragment
        ):
            raise ValueError("strict_loopback_url_invalid")
        return parsed.scheme, address.compressed, port

    def enable_strict_loopback_transport(self) -> None:
        """Disable redirects and ambient proxies for sensitive local prompts."""

        self._literal_loopback_origin(self.base_url)
        if self._session is None:
            raise RuntimeError("strict_loopback_requests_session_unavailable")
        self._session.trust_env = False
        self._session.proxies.clear()
        self.strict_loopback_no_redirects = True

    def _validate_strict_request_url(self, url: str) -> None:
        if not self.strict_loopback_no_redirects:
            return
        if self._literal_loopback_origin(url) != self._literal_loopback_origin(
            self.base_url
        ):
            raise RuntimeError("strict_loopback_origin_mismatch")
        if self._session is None:
            raise RuntimeError("strict_loopback_requests_session_unavailable")
        if self._session.trust_env is not False or self._session.proxies:
            raise RuntimeError("strict_loopback_proxy_state_invalid")

    def _validate_strict_response(self, response: Any) -> None:
        if not self.strict_loopback_no_redirects:
            return
        response_url = str(getattr(response, "url", "") or "")
        if not response_url:
            raise RuntimeError("strict_loopback_response_url_missing")
        self._validate_strict_request_url(response_url)
        status_code = int(getattr(response, "status_code", 0) or 0)
        if (
            300 <= status_code < 400
            or bool(getattr(response, "is_redirect", False))
            or bool(getattr(response, "is_permanent_redirect", False))
            or bool(getattr(response, "history", ()))
        ):
            raise RuntimeError("strict_loopback_redirect_rejected")

    def _http_post(self, url: str, **kwargs: Any) -> Any:
        if self._session is None:
            raise RuntimeError("requests_session_unavailable")
        self._validate_strict_request_url(url)
        if self.strict_loopback_no_redirects:
            if kwargs.get("proxies"):
                raise RuntimeError("strict_loopback_request_proxy_forbidden")
            kwargs["allow_redirects"] = False
            kwargs["proxies"] = {}
        response = self._session.post(url, **kwargs)
        self._validate_strict_response(response)
        return response

    def _http_get(self, url: str, **kwargs: Any) -> Any:
        if self._session is None:
            raise RuntimeError("requests_session_unavailable")
        self._validate_strict_request_url(url)
        if self.strict_loopback_no_redirects:
            if kwargs.get("proxies"):
                raise RuntimeError("strict_loopback_request_proxy_forbidden")
            kwargs["allow_redirects"] = False
            kwargs["proxies"] = {}
        response = self._session.get(url, **kwargs)
        self._validate_strict_response(response)
        return response

    def _headers(self) -> Dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            if looks_like_ollama_url(self.base_url):
                h.update(
                    ollama_authorization_headers(
                        self.base_url,
                        self.api_key if self._api_key_explicit else None,
                    )
                )
            else:
                h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def _build_payload(
        self,
        messages: List[Dict[str, Any]],
        system: str,
        tools: Optional[List[Dict[str, Any]]],
        max_tokens: int,
        temperature: float,
        stream: bool = False,
        stop: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Build an OpenAI-compatible chat completion payload."""
        full_messages = []
        if system:
            full_messages.append({"role": "system", "content": system})

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # Handle tool_result messages → assistant tool response format
            if isinstance(content, list):
                # Check if it's tool results
                tool_results = [
                    c for c in content if isinstance(c, dict) and c.get("type") == "tool_result"
                ]
                if tool_results:
                    for tr in tool_results:
                        full_messages.append({
                            "role": "tool",
                            "tool_call_id": tr.get("tool_use_id", ""),
                            "content": tr.get("content", ""),
                        })
                    continue

                # Extract text from content blocks
                text_parts = []
                for c in content:
                    if isinstance(c, dict):
                        if c.get("type") == "text":
                            text_parts.append(c.get("text", ""))
                        elif hasattr(c, "text"):
                            text_parts.append(c.text)
                    elif isinstance(c, str):
                        text_parts.append(c)
                    elif hasattr(c, "text"):
                        text_parts.append(c.text)
                content = "\n".join(text_parts) if text_parts else str(content)

            full_messages.append({"role": role, "content": content})

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": full_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream,
        }

        # Ollama-specific: pin the model in RAM. The OpenAI shim ignores
        # unknown fields so this is safe against other backends, and
        # makes every follow-up call ~3s warm instead of ~8s cold.
        # Override via AUREON_LLM_KEEP_ALIVE ("5m", "1h", "-1" for forever).
        keep_alive = os.environ.get("AUREON_LLM_KEEP_ALIVE", "30m")
        if keep_alive:
            payload["keep_alive"] = keep_alive

        if is_ollama_cloud_url(self.base_url):
            payload["reasoning_effort"] = resolve_ollama_reasoning_effort()

        if tools:
            payload["tools"] = self._convert_tools(tools)
        if stop:
            payload["stop"] = list(stop)

        return payload

    def _convert_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert Aureon tool defs to OpenAI function-calling format."""
        converted = []
        for t in tools:
            converted.append({
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": t.get("input_schema", {"type": "object", "properties": {}}),
                },
            })
        return converted

    def _build_native_payload(
        self,
        messages: List[Dict[str, Any]],
        system: str,
        max_tokens: int,
        temperature: float,
        stop: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Build an Ollama-native ``/api/chat`` payload. Differences from
        the OpenAI shim:
          - ``options.num_predict`` instead of top-level ``max_tokens``
          - ``options.temperature``
          - top-level ``keep_alive`` is honoured
          - ``stream: false`` for one-shot replies
        """
        full_messages = []
        if system:
            full_messages.append({"role": "system", "content": system})
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            # Normalise list/dict content blocks to a plain string.
            if isinstance(content, list):
                text_parts: List[str] = []
                for c in content:
                    if isinstance(c, dict):
                        if c.get("type") == "text":
                            text_parts.append(str(c.get("text", "")))
                        elif "text" in c:
                            text_parts.append(str(c.get("text", "")))
                    elif isinstance(c, str):
                        text_parts.append(c)
                content = "\n".join(p for p in text_parts if p)
            if role not in ("system", "user", "assistant", "tool"):
                role = "user"
            full_messages.append({"role": role, "content": content})

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": full_messages,
            "stream": False,
            "options": {
                "num_predict": int(max_tokens),
                "temperature": float(temperature),
            },
        }
        if self._keep_alive:
            payload["keep_alive"] = self._keep_alive
        if stop:
            payload["options"]["stop"] = list(stop)
        if is_ollama_cloud_url(self._native_root):
            effort = resolve_ollama_reasoning_effort()
            payload["think"] = False if effort == "none" else effort
        return payload

    def _prompt_via_native(
        self,
        messages: List[Dict[str, Any]],
        system: str,
        max_tokens: int,
        temperature: float,
        stop: Optional[List[str]] = None,
    ) -> LLMResponse:
        """Send a chat request through Ollama's native /api/chat."""
        if _llm_http_disabled():
            return LLMResponse(text="[ERROR] LLM HTTP disabled by audit/offline mode", stop_reason="error")
        payload = self._build_native_payload(
            messages,
            system,
            max_tokens,
            temperature,
            stop,
        )
        url = f"{self._native_root}/api/chat"
        try:
            req_timeout = float(
                os.environ.get("AUREON_LLM_REQUEST_TIMEOUT_S", str(_llm_timeout(60.0, 2.0)))
                or _llm_timeout(60.0, 2.0)
            )
            resp = self._http_post(
                url, json=payload, headers=self._headers(), timeout=max(1.0, req_timeout)
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error("Ollama native request failed: %s", e)
            return LLMResponse(text=f"[ERROR] {e}", stop_reason="error")

        msg = data.get("message") or {}
        text = str(msg.get("content", "") or "")
        done_reason = str(data.get("done_reason", "stop") or "stop")
        stop_reason = "end_turn" if done_reason == "stop" else (
            "max_tokens" if done_reason == "length" else "end_turn"
        )
        usage = {
            "input_tokens": int(data.get("prompt_eval_count", 0) or 0),
            "output_tokens": int(data.get("eval_count", 0) or 0),
        }
        usage["total_tokens"] = usage["input_tokens"] + usage["output_tokens"]
        return LLMResponse(
            text=text,
            tool_calls=[],  # Ollama native /api/chat doesn't emit tool_calls
            stop_reason=stop_reason,
            usage=usage,
            model=str(data.get("model", self.model)),
            raw=data,
        )

    def prompt(
        self,
        messages: List[Dict[str, Any]],
        system: str = "",
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs,
    ) -> LLMResponse:
        if not self._session:
            return LLMResponse(text="[ERROR] requests library not available", stop_reason="error")
        if _llm_http_disabled():
            return LLMResponse(text="[ERROR] LLM HTTP disabled by audit/offline mode", stop_reason="error")

        # Ollama-native fast path: only used when we have no tool defs
        # (the native /api/chat doesn't emit OpenAI-style tool_calls),
        # and when auto-detected or explicitly enabled.
        raw_stop = kwargs.get("stop")
        stop = (
            [str(item) for item in raw_stop]
            if isinstance(raw_stop, (list, tuple))
            else None
        )
        if self._prefer_native and not tools:
            return self._prompt_via_native(
                messages,
                system,
                max_tokens,
                temperature,
                stop,
            )

        payload = self._build_payload(
            messages,
            system,
            tools,
            max_tokens,
            temperature,
            stop=stop,
        )
        url = f"{self.base_url}/chat/completions"

        try:
            req_timeout = float(
                os.environ.get("AUREON_LLM_REQUEST_TIMEOUT_S", str(_llm_timeout(20.0, 2.0)))
                or _llm_timeout(20.0, 2.0)
            )
            resp = self._http_post(
                url, json=payload, headers=self._headers(), timeout=max(1.0, req_timeout)
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error("Local LLM request failed: %s", e)
            return LLMResponse(text=f"[ERROR] {e}", stop_reason="error")

        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})

        tool_calls = []
        for tc in message.get("tool_calls", []):
            func = tc.get("function", {})
            args = func.get("arguments", "{}")
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {"raw": args}
            tool_calls.append(ToolCall(
                id=tc.get("id", str(uuid.uuid4())),
                name=func.get("name", ""),
                arguments=args,
            ))

        stop_reason = "tool_use" if tool_calls else "end_turn"
        if choice.get("finish_reason") == "length":
            stop_reason = "max_tokens"

        return LLMResponse(
            text=message.get("content", "") or "",
            tool_calls=tool_calls,
            stop_reason=stop_reason,
            usage=data.get("usage", {}),
            model=data.get("model", self.model),
            raw=data,
        )

    def stream(
        self,
        messages: List[Dict[str, Any]],
        system: str = "",
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs,
    ) -> Generator[StreamChunk, None, None]:
        if not self._session:
            yield StreamChunk(text="[ERROR] requests library not available", done=True)
            return
        if _llm_http_disabled():
            yield StreamChunk(
                text="[ERROR] LLM HTTP disabled by audit/offline mode",
                done=True,
                stop_reason="error",
            )
            return

        payload = self._build_payload(messages, system, tools, max_tokens, temperature, stream=True)
        url = f"{self.base_url}/chat/completions"

        try:
            resp = self._http_post(
                url,
                json=payload,
                headers=self._headers(),
                stream=True,
                timeout=_llm_timeout(300.0, 5.0),
            )
            resp.raise_for_status()
        except Exception as e:
            logger.error("Local LLM stream failed: %s", e)
            yield StreamChunk(text=f"[ERROR] {e}", done=True)
            return

        pending_tool: Optional[Dict[str, Any]] = None

        for line in resp.iter_lines():
            if not line:
                continue
            decoded = line.decode("utf-8", errors="replace").strip()
            if not decoded.startswith("data: "):
                continue
            data_str = decoded[6:]
            if data_str == "[DONE]":
                if pending_tool:
                    args_str = pending_tool.get("arguments_buffer", "")
                    try:
                        args = json.loads(args_str)
                    except json.JSONDecodeError:
                        args = {"raw": args_str}
                    yield StreamChunk(
                        tool_call=ToolCall(
                            id=pending_tool.get("id", str(uuid.uuid4())),
                            name=pending_tool.get("name", ""),
                            arguments=args,
                        ),
                        done=False,
                    )
                yield StreamChunk(done=True, stop_reason="end_turn")
                return

            try:
                chunk_data = json.loads(data_str)
            except json.JSONDecodeError:
                continue

            delta = chunk_data.get("choices", [{}])[0].get("delta", {})
            finish = chunk_data.get("choices", [{}])[0].get("finish_reason")

            # Handle tool call deltas
            if delta.get("tool_calls"):
                tc_delta = delta["tool_calls"][0]
                if tc_delta.get("function", {}).get("name"):
                    if pending_tool:
                        args_str = pending_tool.get("arguments_buffer", "")
                        try:
                            args = json.loads(args_str)
                        except json.JSONDecodeError:
                            args = {"raw": args_str}
                        yield StreamChunk(
                            tool_call=ToolCall(
                                id=pending_tool.get("id", str(uuid.uuid4())),
                                name=pending_tool.get("name", ""),
                                arguments=args,
                            ),
                        )
                    pending_tool = {
                        "id": tc_delta.get("id", str(uuid.uuid4())),
                        "name": tc_delta["function"]["name"],
                        "arguments_buffer": tc_delta.get("function", {}).get("arguments", ""),
                    }
                elif pending_tool:
                    pending_tool["arguments_buffer"] += tc_delta.get("function", {}).get("arguments", "")
                continue

            content = delta.get("content", "")
            if content:
                yield StreamChunk(text=content)

            if finish:
                if pending_tool:
                    args_str = pending_tool.get("arguments_buffer", "")
                    try:
                        args = json.loads(args_str)
                    except json.JSONDecodeError:
                        args = {"raw": args_str}
                    yield StreamChunk(
                        tool_call=ToolCall(
                            id=pending_tool.get("id", str(uuid.uuid4())),
                            name=pending_tool.get("name", ""),
                            arguments=args,
                        ),
                    )
                yield StreamChunk(done=True, stop_reason=finish)
                return

    def health_check(self) -> bool:
        """
        Verify the backend is reachable AND that ``self.model`` actually
        runs on this machine.

        Ollama / vLLM / llama.cpp will all happily return 200 from
        ``/v1/models`` even when the configured model is missing or too big
        to load (the real failure surfaces later as a 404 / 500 from
        ``/v1/chat/completions``). That's how the voice layer ended up
        thinking it had a working LLM while every utterance silently
        errored out.

        Behaviour:
          1. Reach ``/v1/models`` and read the listing.
          2. If the configured model isn't in the listing, and the caller
             didn't pin a specific model, pick the smallest installed model
             whose name shares a family prefix with the requested one
             (else just the smallest installed model).
          3. Probe the resolved model with a 1-token chat completion. If
             it 500s (typically OOM), drop it and try the next candidate.
          4. Cache the verified model and return True; otherwise False.
        """
        if _llm_http_disabled():
            return False
        if not self._session:
            return False
        if self._model_verified:
            return True
        try:
            timeout_s = float(
                os.environ.get("AUREON_LLM_HEALTH_TIMEOUT_S", str(_llm_timeout(2.0, 0.5)))
                or _llm_timeout(2.0, 0.5)
            )
            resp = self._http_get(
                f"{self.base_url}/models",
                headers=self._headers(),
                timeout=max(0.1, timeout_s),
            )
            if resp.status_code != 200:
                return False
            listing = resp.json() or {}
        except Exception:
            return False

        installed: List[str] = []
        for entry in listing.get("data", []) or []:
            mid = (entry or {}).get("id") if isinstance(entry, dict) else None
            if mid:
                installed.append(str(mid))
        if not installed:
            return False

        # Build the ordered list of candidates we'll actually probe.
        candidates: List[str] = []
        if self.model in installed:
            candidates.append(self.model)

        if not self._model_pinned:
            family = self.model.split(":")[0].split(".")[0].lower()  # "llama3" → "llama"
            same_family = [m for m in installed if family and family in m.lower()]
            others = [m for m in installed if m not in same_family]
            for m in self._sort_by_size(same_family) + self._sort_by_size(others):
                if m not in candidates:
                    candidates.append(m)

        # Ollama on CPU can spend a long time evaluating even a 1-token probe.
        # If the requested model is present, trust the listing by default and
        # let the real small-packet request be the proof. Operators can set
        # AUREON_LLM_SKIP_PROBE=0 to restore strict probe-before-use behavior.
        skip_probe_raw = os.environ.get("AUREON_LLM_SKIP_PROBE", "1" if self._prefer_native else "0")
        if candidates and skip_probe_raw.strip().lower() in {"1", "true", "yes", "on"}:
            self.model = candidates[0]
            self._model_verified = True
            return True

        for candidate in candidates:
            if self._probe_model(candidate):
                if candidate != self.model:
                    logger.info(
                        "Local LLM model %r unavailable — using installed model %r instead",
                        self.model,
                        candidate,
                    )
                self.model = candidate
                self._model_verified = True
                return True

        return False

    @staticmethod
    def _sort_by_size(models: List[str]) -> List[str]:
        """Order model ids cheapest-first by parsing the size hint in the name."""
        import re

        def size_key(name: str) -> float:
            match = re.search(r"(\d+(?:\.\d+)?)\s*([bm])\b", name.lower())
            if not match:
                return float("inf")
            val = float(match.group(1))
            if match.group(2) == "m":
                val /= 1000.0
            return val

        return sorted(models, key=size_key)

    def _probe_model(self, model_id: str) -> bool:
        """Send a 1-token chat completion to confirm the model actually loads."""
        if _llm_http_disabled():
            return False
        try:
            probe_timeout = float(
                os.environ.get("AUREON_LLM_PROBE_TIMEOUT_S", str(_llm_timeout(30.0, 1.0)))
                or _llm_timeout(30.0, 1.0)
            )
            resp = self._http_post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": model_id,
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 1,
                    "temperature": 0.0,
                    "stream": False,
                },
                headers=self._headers(),
                timeout=max(1.0, probe_timeout),
            )
        except Exception as e:
            logger.debug("LLM probe %s failed: %s", model_id, e)
            return False
        if resp.status_code != 200:
            logger.debug("LLM probe %s rejected: %s %s", model_id, resp.status_code, resp.text[:200])
            return False
        return True


# ─────────────────────────────────────────────────────────────────────────────
# AureonBrainAdapter — use existing AureonBrain as reasoning engine
# ─────────────────────────────────────────────────────────────────────────────


class AureonBrainAdapter(LLMAdapter):
    """
    Uses the existing AureonBrain intelligence layer as a reasoning backend.

    Instead of an external LLM, this adapter:
      1. Parses the user message to extract intent (symbol, action, context)
      2. Runs AureonBrain.decide() with market data
      3. Formats the Brain's BrainDecision as an LLM-like response

    This is the fully in-house, zero-external-dependency reasoning path.
    """

    # Class-level caches so the "Brain not available" warning only fires
    # once per process regardless of how many adapter instances we spin up.
    _brain_load_attempted: bool = False
    _brain_load_succeeded: bool = False

    def __init__(self):
        self._brain = None
        self._brain_loaded = False
        self._load_brain()

    def _load_brain(self):
        try:
            from aureon.intelligence.aureon_brain import AureonBrain
            self._brain = AureonBrain()
            self._brain_loaded = True
            if not AureonBrainAdapter._brain_load_succeeded:
                logger.info("AureonBrain loaded as reasoning backend")
            AureonBrainAdapter._brain_load_succeeded = True
        except Exception as e:
            # Only log the warning the FIRST time — subsequent adapter
            # instances in the same process silently fall back.
            if not AureonBrainAdapter._brain_load_attempted:
                logger.info(
                    "AureonBrain not available: %s — falling back to rule engine",
                    e,
                )
            self._brain_loaded = False
        finally:
            AureonBrainAdapter._brain_load_attempted = True

    @staticmethod
    def _operator_message_from_wrapped_query(text: str) -> str:
        value = str(text or "")
        match = re.search(
            r"(?is)\bOperator message:\s*(.*?)\n\s*Redacted dashboard context:",
            value,
        )
        if match:
            return match.group(1).strip()
        match = re.search(
            r"(?is)\bOperator message:\s*(.*?)\n\s*Compact Phi/Ollama/Aureon status:",
            value,
        )
        if match:
            return match.group(1).strip()
        return value.strip()

    def _extract_context(self, messages: List[Dict[str, Any]], system: str) -> Dict[str, Any]:
        """Extract actionable context from conversation messages."""
        context: Dict[str, Any] = {"system": system, "query": "", "symbols": [], "action": None}

        for msg in messages:
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, list):
                    parts = []
                    for c in content:
                        if isinstance(c, dict) and c.get("type") == "text":
                            parts.append(c["text"])
                        elif isinstance(c, str):
                            parts.append(c)
                    content = " ".join(parts)
                context["query"] = self._operator_message_from_wrapped_query(str(content))

        # Extract symbols mentioned
        text = context["query"].upper()
        common_symbols = {
            "BTC": "BTCUSDT",
            "ETH": "ETHUSDT",
            "XRP": "XRPUSDT",
            "SOL": "SOLUSDT",
            "ADA": "ADAUSDT",
            "DOGE": "DOGEUSDT",
            "AVAX": "AVAXUSDT",
            "DOT": "DOTUSDT",
            "MATIC": "MATICUSDT",
            "LINK": "LINKUSDT",
        }
        for base, sym in common_symbols.items():
            if re.search(rf"\b{sym}\b", text) or re.search(rf"\b{base}\b", text):
                context["symbols"].append(sym)

        # Detect action intent
        lower = context["query"].lower()
        if any(w in lower for w in ["buy", "long", "enter", "open"]):
            context["action"] = "BUY"
        elif any(w in lower for w in ["sell", "short", "exit", "close"]):
            context["action"] = "SELL"
        elif any(w in lower for w in ["analyse", "analyze", "signal", "status", "check"]):
            context["action"] = "ANALYSE"

        return context

    @staticmethod
    def _is_market_context(context: Dict[str, Any]) -> bool:
        if context.get("symbols"):
            return True
        lower = str(context.get("query") or "").lower()
        market_terms = (
            "trade",
            "trading",
            "market",
            "signal",
            "buy",
            "sell",
            "long",
            "short",
            "position",
            "price",
            "coin",
            "crypto",
            "ticker",
            "exchange",
            "portfolio",
        )
        return any(re.search(rf"\b{re.escape(term)}\b", lower) for term in market_terms)

    def _operator_chat_reason(self, context: Dict[str, Any]) -> str:
        query = str(context.get("query") or "").strip()
        lowered = query.lower()
        if any(
            phrase in lowered
            for phrase in (
                "what can you do",
                "what can aureon do",
                "what are your capabilities",
                "what can u do",
                "capabilitys",
                "capabilities",
            )
        ):
            return (
                "I can run Aureon as a local client-job organism: talk with you through Phi chat, scope coding jobs, "
                "recruit the right internal roles, make safe code and UI changes, build local media artifacts, run tests "
                "and browser proof, publish evidence, and hold weak work behind the quality gate. I still keep live trading, "
                "payments, official filings, credential reveal, and destructive OS actions behind their existing gates."
            )
        if "what can you see" in lowered and any(token in lowered for token in ("cockpit", "dashboard", "console")):
            return (
                "I can see this as a Phi chat request attached to the local Aureon cockpit. I can use the redacted dashboard "
                "context, route coding and UI jobs through the organism, publish proof, and report blockers. I will not claim "
                "a file changed, test passed, trade executed, payment moved, filing submitted, or credential was handled unless "
                "the evidence path proves it."
            )
        name_match = re.search(r"\bmy name is\s+([a-zA-Z][a-zA-Z .'-]{1,80})", query, flags=re.I)
        name = name_match.group(1).strip().rstrip(".") if name_match else ""
        greeting = f"Hello {name}." if name else "Hello."
        return (
            f"{greeting} I hear you through Aureon's local brain fallback, and I am treating this as operator chat, "
            "not a trading signal. I can help route coding jobs, UI work, media builds, research, and system-health checks "
            "through the local Aureon organism while keeping live trading, payments, filings, credentials, and destructive OS actions behind their gates."
        )

    def _brain_reason(self, context: Dict[str, Any]) -> str:
        """Use AureonBrain to generate a reasoning response."""
        if not self._is_market_context(context):
            return self._operator_chat_reason(context)
        if not self._brain_loaded or not self._brain:
            return self._rule_engine_reason(context)

        try:
            symbol, base_score, features, population_scores = self._brain_inputs(context)

            # If brain has a decide method, use it
            if hasattr(self._brain, "decide"):
                decision = self._brain.decide(
                    symbol=symbol,
                    base_score=base_score,
                    features=features,
                    population_scores=population_scores,
                    now=time.time(),
                )
                if decision and hasattr(decision, "__dict__"):
                    side = str(getattr(decision, "side", "neutral") or "neutral")
                    return json.dumps({
                        "signal": side.upper(),
                        "symbol": getattr(decision, "symbol", symbol),
                        "score": getattr(decision, "score", base_score),
                        "coherence": getattr(decision, "coherence", 0.5),
                        "reasoning": "AureonBrain coherence and gate checks produced a candidate decision.",
                        "source": "AureonBrain",
                    }, indent=2)
                return json.dumps({
                    "signal": "NEUTRAL",
                    "symbol": symbol,
                    "score": base_score,
                    "coherence": self._brain.coherence(features) if hasattr(self._brain, "coherence") else 0.5,
                    "reasoning": "AureonBrain gates did not authorise an actionable decision from this prompt context.",
                    "source": "AureonBrain",
                }, indent=2)

            # Fallback to any available method
            if hasattr(self._brain, "analyse"):
                return str(self._brain.analyse(features))
            if hasattr(self._brain, "predict"):
                return str(self._brain.predict(features))

        except Exception as e:
            logger.warning("AureonBrain reasoning failed: %s", e)

        return self._rule_engine_reason(context)

    def _brain_inputs(self, context: Dict[str, Any]):
        """Translate prompt context into the current AureonBrain.decide contract."""
        action = str(context.get("action") or "ANALYSE").upper()
        symbols = list(context.get("symbols") or [])
        symbol = str(symbols[0] if symbols else "AUREON").upper()

        if action == "BUY":
            base_score = 0.8
            rsi = 58.0
            momentum = 0.42
            trend = 0.64
        elif action == "SELL":
            base_score = -0.8
            rsi = 42.0
            momentum = -0.42
            trend = 0.64
        else:
            base_score = 0.05
            rsi = 50.0
            momentum = 0.0
            trend = 0.45

        features = {
            "rsi": rsi,
            "momentum": momentum,
            "volatility": 0.25,
            "trend_strength": trend,
            "query_length": float(len(str(context.get("query") or ""))),
            "timestamp": time.time(),
        }
        population_scores = [-0.65, -0.4, -0.2, 0.0, 0.2, 0.4, 0.65]
        return symbol, base_score, features, population_scores

    def _rule_engine_reason(self, context: Dict[str, Any]) -> str:
        """Deterministic rule-based reasoning when Brain is unavailable."""
        query = context.get("query", "")
        action = context.get("action", "ANALYSE")
        symbols = context.get("symbols", [])

        response_parts = []
        response_parts.append(f"Aureon In-House Analysis — {time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        response_parts.append(f"Query: {query}")

        if symbols:
            response_parts.append(f"Symbols detected: {', '.join(symbols)}")

        if action == "BUY":
            response_parts.append(
                "Signal: NEUTRAL — Requires live market data + coherence gate (Gamma > 0.945) "
                "before confirming BUY. Run through full pillar consensus."
            )
        elif action == "SELL":
            response_parts.append(
                "Signal: NEUTRAL — SELL signals require Auris 9-node consensus. "
                "Check stop-loss levels and current position state."
            )
        else:
            response_parts.append(
                "Signal: NEUTRAL — System is in analysis mode. "
                "All 6 pillar agents should be consulted for a full signal."
            )

        return "\n".join(response_parts)

    def prompt(
        self,
        messages: List[Dict[str, Any]],
        system: str = "",
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs,
    ) -> LLMResponse:
        context = self._extract_context(messages, system)
        response_text = self._brain_reason(context)

        # If tools are available and action is detected, generate tool calls
        tool_calls = []
        if tools and context.get("action"):
            for tool in tools:
                tool_name = tool.get("name", "")
                # Auto-invoke relevant tools based on context
                if context["action"] == "ANALYSE" and "read" in tool_name.lower():
                    tool_calls.append(ToolCall(
                        name=tool_name,
                        arguments=self._auto_tool_args(tool, context),
                    ))
                    break
                if context["action"] in ("BUY", "SELL") and "position" in tool_name.lower():
                    tool_calls.append(ToolCall(
                        name=tool_name,
                        arguments=self._auto_tool_args(tool, context),
                    ))
                    break

        return LLMResponse(
            text=response_text,
            tool_calls=tool_calls,
            stop_reason="tool_use" if tool_calls else "end_turn",
            model="aureon-brain-v1",
        )

    def _auto_tool_args(self, tool: Dict, context: Dict) -> Dict[str, Any]:
        """Generate sensible default arguments for a tool."""
        schema = tool.get("input_schema", {})
        props = schema.get("properties", {})
        args = {}
        for key, prop in props.items():
            ptype = prop.get("type", "string")
            if ptype == "string":
                if "symbol" in key.lower():
                    args[key] = context.get("symbols", ["BTCUSDT"])[0] if context.get("symbols") else "all"
                elif "exchange" in key.lower():
                    args[key] = "all"
                elif "format" in key.lower():
                    args[key] = "json"
                else:
                    args[key] = "default"
            elif ptype == "integer":
                args[key] = 10
            elif ptype == "number":
                args[key] = 0.945
            elif ptype == "boolean":
                args[key] = True
        return args

    def stream(
        self,
        messages: List[Dict[str, Any]],
        system: str = "",
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs,
    ) -> Generator[StreamChunk, None, None]:
        # Brain responses are fast — simulate streaming by chunking the response
        response = self.prompt(messages, system, tools, max_tokens, temperature, **kwargs)

        # Stream tool calls first
        for tc in response.tool_calls:
            yield StreamChunk(tool_call=tc)

        # Stream text in word-sized chunks
        words = response.text.split(" ")
        for i, word in enumerate(words):
            suffix = " " if i < len(words) - 1 else ""
            yield StreamChunk(text=word + suffix)

        yield StreamChunk(done=True, stop_reason=response.stop_reason)

    def health_check(self) -> bool:
        return self._brain_loaded


# ─────────────────────────────────────────────────────────────────────────────
# AureonHybridAdapter — local LLM + AureonBrain combined
# ─────────────────────────────────────────────────────────────────────────────


class AureonHybridAdapter(LLMAdapter):
    """
    Chains AureonLocalAdapter (for language generation) with AureonBrainAdapter
    (for market-specific reasoning). The Brain enriches the system prompt with
    live intelligence before the local LLM generates the final response.

    Fallback chain:
      1. Try local LLM with Brain-enriched context
      2. If local LLM is down → fall back to Brain-only
      3. If Brain is down → fall back to local LLM alone
      4. If both are down → rule engine
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.local = AureonLocalAdapter(base_url=base_url, model=model, api_key=api_key)
        self.brain = AureonBrainAdapter()
        self.model = f"aureon-ollama-hybrid:{self.local.model}"
        self.last_weaver_trace: Dict[str, Any] = {}
        self.last_dynamic_prompt_filter: Dict[str, Any] = {}

    def _enrich_system(self, system: str, messages: List[Dict[str, Any]]) -> str:
        """Prepend Brain intelligence to the system prompt."""
        parts = [str(system or "").strip()]
        cognitive_context = _aureon_cognitive_context_summary()
        if cognitive_context:
            parts.append(cognitive_context)
        if self.brain.health_check():
            context = self.brain._extract_context(messages, system)
            brain_intel = self.brain._brain_reason(context)
            parts.append(f"AUREON BRAIN INTELLIGENCE\n{brain_intel}\nEND AUREON BRAIN INTELLIGENCE")
        return "\n\n".join(part for part in parts if part)

    @staticmethod
    def _clip(value: Any, limit: int) -> str:
        text = str(value or "")
        if len(text) <= limit:
            return text
        return text[: max(0, limit - 20)].rstrip() + "\n[clipped]"

    @classmethod
    def _message_text(cls, msg: Dict[str, Any]) -> str:
        content = msg.get("content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: List[str] = []
            for item in content:
                if isinstance(item, dict):
                    parts.append(str(item.get("text") or item.get("content") or ""))
                else:
                    parts.append(str(item))
            return "\n".join(part for part in parts if part)
        if isinstance(content, dict):
            return str(content.get("text") or content.get("content") or content)
        return str(content)

    @classmethod
    def _flatten_messages_for_weaver(cls, messages: List[Dict[str, Any]]) -> str:
        lines: List[str] = []
        for msg in messages or []:
            role = str(msg.get("role") or "user")
            text = cls._message_text(msg)
            if text.strip():
                lines.append(f"{role}: {cls._clip(text, 1800)}")
        return "\n\n".join(lines)

    def _context_weaver_enabled(
        self,
        tools: Optional[List[Dict[str, Any]]],
        max_tokens: int,
        kwargs: Dict[str, Any],
    ) -> bool:
        if tools:
            return False
        if bool(kwargs.get("disable_context_weaver")):
            return False
        raw = os.environ.get("AUREON_OLLAMA_CONTEXT_WEAVER")
        if raw is not None:
            return raw.strip().lower() not in {"0", "false", "no", "off"}
        # Default the weaver for short operator chat. Longer authoring calls can
        # still use the normal local model unless the env var explicitly opts in.
        return max_tokens <= 800

    def _build_dynamic_filter(
        self,
        messages: List[Dict[str, Any]],
        system: str,
        kwargs: Dict[str, Any],
    ) -> Dict[str, Any]:
        if bool(kwargs.get("disable_dynamic_prompt_filter")):
            return {}
        try:
            from aureon.autonomous.aureon_dynamic_prompt_filter import build_dynamic_prompt_filter

            report = build_dynamic_prompt_filter(
                messages,
                system=system,
                lane_hint=str(kwargs.get("dynamic_prompt_lane") or ""),
                publish=True,
            )
            self.last_dynamic_prompt_filter = report
            return report
        except Exception as exc:
            report = {
                "schema_version": "aureon-dynamic-prompt-filter-v1",
                "ok": False,
                "status": "dynamic_prompt_filter_error",
                "error": str(exc),
            }
            self.last_dynamic_prompt_filter = report
            return report

    def _system_with_dynamic_filter(self, system: str, filter_report: Dict[str, Any]) -> str:
        if not filter_report:
            return system
        try:
            from aureon.autonomous.aureon_dynamic_prompt_filter import render_filter_prompt_block

            filter_block = render_filter_prompt_block(filter_report)
            return "\n\n".join(part for part in [str(system or "").strip(), filter_block] if part)
        except Exception:
            return system

    def _finalize_dynamic_response(
        self,
        response: LLMResponse,
        filter_report: Dict[str, Any],
        *,
        reply_source: str,
    ) -> LLMResponse:
        if not filter_report:
            return response
        try:
            from aureon.autonomous.aureon_dynamic_prompt_filter import apply_dynamic_response_filter

            text, final_report = apply_dynamic_response_filter(
                response.text,
                filter_report,
                reply_source=reply_source,
                publish=True,
            )
            response.text = text
            if isinstance(response.raw, dict):
                raw = dict(response.raw)
            elif response.raw is None:
                raw = {}
            else:
                raw = {"upstream_raw": response.raw}
            raw["dynamic_prompt_filter"] = final_report
            response.raw = raw
            self.last_dynamic_prompt_filter = final_report
        except Exception as exc:
            if isinstance(response.raw, dict):
                raw = dict(response.raw)
            elif response.raw is None:
                raw = {}
            else:
                raw = {"upstream_raw": response.raw}
            raw["dynamic_prompt_filter"] = {
                "schema_version": "aureon-dynamic-prompt-filter-v1",
                "ok": False,
                "status": "dynamic_prompt_filter_finalize_error",
                "error": str(exc),
            }
            response.raw = raw
        return response

    def _weaver_shard_plan(
        self,
        user_context: str,
        enriched_system: str,
        filter_report: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, str]]:
        compact_system = self._clip(enriched_system, int(os.environ.get("AUREON_OLLAMA_WEAVER_SYSTEM_CHARS", "1600") or "1600"))
        compact_user = self._clip(user_context, int(os.environ.get("AUREON_OLLAMA_WEAVER_INPUT_CHARS", "2200") or "2200"))
        plan = [
            {
                "name": "intent_scope",
                "system": "You are a small Ollama worker. Extract only intent. Be concise.",
                "prompt": (
                    "Aureon will compose the final answer. Summarize the operator intent, requested action, "
                    "and any missing scope in <= 70 words.\n\n"
                    f"Context:\n{compact_user}"
                ),
            },
            {
                "name": "evidence_state",
                "system": "You are a small Ollama worker. Extract only evidence and blockers. Be concise.",
                "prompt": (
                    "Aureon will compose the final answer. From this system/dashboard evidence, list only the "
                    "status, blockers, and proof that matter in <= 90 words. Do not invent evidence.\n\n"
                    f"System evidence:\n{compact_system}\n\nOperator context:\n{compact_user}"
                ),
            },
            {
                "name": "answer_draft",
                "system": "You are a small Ollama worker. Draft only the answer. Aureon will verify and compose.",
                "prompt": (
                    "Draft a direct first-person Aureon reply in <= 130 words. Use the evidence, avoid claims "
                    "not proved, and mention existing safety gates when relevant.\n\n"
                    f"System evidence:\n{self._clip(compact_system, 900)}\n\nOperator context:\n{compact_user}"
                ),
            },
        ]
        if filter_report:
            try:
                from aureon.autonomous.aureon_dynamic_prompt_filter import augment_weaver_shard_plan

                plan = augment_weaver_shard_plan(plan, filter_report)
            except Exception:
                pass
        try:
            default_limit = "3" if str(os.environ.get("AUREON_OLLAMA_WEAVER_MODEL") or "").strip() else "2"
            limit = int(os.environ.get("AUREON_OLLAMA_WEAVER_SHARD_LIMIT", default_limit) or default_limit)
        except Exception:
            limit = len(plan)
        return plan[: max(1, min(len(plan), limit))]

    def _run_weaver_shards(
        self,
        messages: List[Dict[str, Any]],
        enriched_system: str,
        temperature: float,
        filter_report: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        user_context = self._flatten_messages_for_weaver(messages)
        shard_tokens = int(os.environ.get("AUREON_OLLAMA_WEAVER_SHARD_TOKENS", "90") or "90")
        weaver_model = str(os.environ.get("AUREON_OLLAMA_WEAVER_MODEL") or "").strip()
        results: List[Dict[str, Any]] = []
        for shard in self._weaver_shard_plan(user_context, enriched_system, filter_report):
            started = time.time()
            old_model = self.local.model
            if weaver_model:
                self.local.model = weaver_model
            try:
                response = self.local.prompt(
                    [{"role": "user", "content": shard["prompt"]}],
                    system=shard["system"],
                    tools=None,
                    max_tokens=max(16, shard_tokens),
                    temperature=min(float(temperature), 0.3),
                )
            finally:
                if weaver_model:
                    self.local.model = old_model
            results.append(
                {
                    "name": shard["name"],
                    "ok": response.stop_reason != "error" and bool((response.text or "").strip()),
                    "text": self._clip(response.text, 900).strip(),
                    "model": response.model or self.local.model,
                    "stop_reason": response.stop_reason,
                    "latency_ms": int((time.time() - started) * 1000),
                    "usage": response.usage or {},
                }
            )
        return results

    @classmethod
    def _latest_user_prompt(cls, messages: List[Dict[str, Any]]) -> str:
        for msg in reversed(messages or []):
            if str(msg.get("role") or "").lower() == "user":
                return cls._message_text(msg)
        return cls._message_text(messages[-1]) if messages else ""

    @staticmethod
    def _clean_weaver_text(text: str) -> str:
        cleaned = str(text or "").strip()
        cleaned = re.sub(r"(?im)^\s*(intent|evidence|draft)\s+packet\s*:\s*", "", cleaned)
        cleaned = re.sub(r"(?im)^\s*I am using the context-weaver path:.*$", "", cleaned)
        cleaned = re.sub(r"(?im)^\s*Aureon will compose the final answer\.?\s*$", "", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip(" \n\t-")

    @staticmethod
    def _trim_incomplete_sentence(text: str) -> str:
        candidate = str(text or "").strip()
        if not candidate:
            return ""
        match = re.search(r"^(.+[.!?])(?:\s+[^.!?]*)?$", candidate, flags=re.S)
        if match:
            return match.group(1).strip()
        return candidate

    @staticmethod
    def _is_capability_question(prompt: str) -> bool:
        lowered = str(prompt or "").lower()
        return any(
            phrase in lowered
            for phrase in (
                "what can you do",
                "what are your capabilities",
                "what can aureon do",
                "what can u do",
                "capabilitys",
                "capabilities",
            )
        )

    @staticmethod
    def _is_cockpit_status_question(prompt: str) -> bool:
        lowered = str(prompt or "").lower()
        return "what can you see" in lowered and any(
            token in lowered for token in ("coding cockpit", "cockpit", "dashboard", "console")
        )

    @staticmethod
    def _is_bad_weaver_draft(text: str) -> bool:
        lowered = str(text or "").strip().lower()
        if not lowered:
            return True
        boilerplate = (
            "aureon will verify and compose",
            "aureon will compose the final answer",
            "i will verify and compose",
            "will verify and compose",
        )
        if any(phrase in lowered for phrase in boilerplate) and len(lowered) < 160:
            return True
        if lowered in {"ok", "ready", "done", "yes"}:
            return True
        return False

    @staticmethod
    def _next_action_for_task(task_family: str) -> str:
        if task_family == "coding":
            return "Give me the coding job and I will scope it, recruit the workers, patch through safe routes, test it, and hold handover until proof passes."
        if task_family == "media":
            return "Give me the artifact brief and I will build local previews, playback/render proof, quality score, snags, and regeneration attempts before handover."
        if task_family == "ui":
            return "Give me the screen or workflow and I will wire the cockpit evidence, build the UI surface, run build/smoke proof, and show approval state."
        if task_family == "research":
            return "Give me the research question and I will use local source packets first, add approved web evidence when needed, then return proof and blockers."
        return "Give me the job in the cockpit or terminal and I will route it through the right Aureon lane with proof and blockers visible."

    def _capability_reply(self, filter_report: Optional[Dict[str, Any]]) -> str:
        return "\n".join(
            [
                "I can run Aureon as a local client-job organism: talk with you through Phi chat, scope coding jobs, recruit the right internal roles, make safe code/UI changes, build local media artifacts, run tests and browser proof, publish evidence, and hold weak work behind the quality gate.",
                "",
                "Proof: this reply is coming through the Ollama context-weaver plus Aureon's dynamic prompt filter, so Ollama shards stay as evidence while Aureon compiles the final human answer.",
                "Blockers: I still keep live trading, payments, official filings, credential reveal, and destructive OS actions behind the existing gates.",
                "Next action: give me a job in the cockpit or terminal and I will scope it, route the crew, do the work through safe local paths, prove it, and show the handover only when the gate passes.",
            ]
        )

    def _cockpit_status_reply(self, evidence: str) -> str:
        cleaned_evidence = self._trim_incomplete_sentence(self._clean_weaver_text(evidence))
        parts = [
            "I can see the coding cockpit through the live Phi chat lane, the Ollama context-weaver, and Aureon's dynamic prompt filter.",
        ]
        if cleaned_evidence:
            parts.append(f"Proof/blockers: {cleaned_evidence}")
        else:
            parts.append("Proof/blockers: the hub is reachable, but the evidence shard did not return a useful summary, so I am not inventing extra status.")
        parts.append(
            "Next action: send a coding job from the cockpit or terminal and I will scope it, recruit the crew, run the safe local route, test it, and hold handover until proof passes."
        )
        return "\n\n".join(parts)

    def _compile_weaver_reply(
        self,
        messages: List[Dict[str, Any]],
        intent: str,
        evidence: str,
        draft: str,
        draft_stop: str,
        filter_report: Optional[Dict[str, Any]],
    ) -> str:
        prompt = self._latest_user_prompt(messages)
        if self._is_capability_question(prompt):
            return self._capability_reply(filter_report)
        if self._is_cockpit_status_question(prompt):
            return self._cockpit_status_reply(evidence)

        cleaned_draft = self._clean_weaver_text(draft)
        if cleaned_draft and not self._is_bad_weaver_draft(cleaned_draft):
            if draft_stop == "max_tokens":
                cleaned_draft = self._trim_incomplete_sentence(cleaned_draft)
            if cleaned_draft:
                return cleaned_draft

        cleaned_intent = self._trim_incomplete_sentence(self._clean_weaver_text(intent))
        cleaned_evidence = self._trim_incomplete_sentence(self._clean_weaver_text(evidence))
        task_family = str((filter_report or {}).get("task_family") or "conversation")
        parts = ["I can help with that."]
        if cleaned_intent:
            parts.append(f"I read the job as: {cleaned_intent}")
        if cleaned_evidence:
            parts.append(f"Current proof/blockers: {cleaned_evidence}")
        parts.append(f"Next action: {self._next_action_for_task(task_family)}")
        return "\n\n".join(parts)

    def _compose_weaver_response(
        self,
        messages: List[Dict[str, Any]],
        shard_results: List[Dict[str, Any]],
        filter_report: Optional[Dict[str, Any]] = None,
    ) -> LLMResponse:
        by_name = {str(item.get("name")): item for item in shard_results}
        intent = str(by_name.get("intent_scope", {}).get("text") or "").strip()
        evidence = str(by_name.get("evidence_state", {}).get("text") or "").strip()
        draft = str(by_name.get("answer_draft", {}).get("text") or "").strip()
        draft_stop = str(by_name.get("answer_draft", {}).get("stop_reason") or "")
        success_count = sum(1 for item in shard_results if item.get("ok"))

        final = self._compile_weaver_reply(messages, intent, evidence, draft, draft_stop, filter_report)

        shard_model = str(os.environ.get("AUREON_OLLAMA_WEAVER_MODEL") or self.local.model)
        raw_trace = {
            "weaver": True,
            "composer": "AureonHybridAdapter",
            "policy": "small_ollama_shards_then_aureon_recomposition",
            "shards": shard_results,
            "primary_model": self.local.model,
            "shard_model": shard_model,
            "source_message_count": len(messages or []),
        }
        if filter_report:
            raw_trace["dynamic_prompt_filter"] = filter_report
        self.last_weaver_trace = raw_trace
        return LLMResponse(
            text=self._clip(final, 1600).strip(),
            stop_reason="end_turn",
            usage={
                "weaver_shards": len(shard_results),
                "successful_shards": success_count,
                "total_tokens": sum(int((item.get("usage") or {}).get("total_tokens", 0) or 0) for item in shard_results),
            },
            model=f"aureon-ollama-weaver:{shard_model}",
            raw=raw_trace,
        )

    def prompt(
        self,
        messages: List[Dict[str, Any]],
        system: str = "",
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs,
    ) -> LLMResponse:
        dynamic_filter = self._build_dynamic_filter(messages, system, kwargs)
        filtered_system = self._system_with_dynamic_filter(system, dynamic_filter)
        direct_reply = ""
        try:
            meaning = dynamic_filter.get("meaning_resolver") if isinstance(dynamic_filter, dict) else {}
            direct_reply = str((meaning or {}).get("direct_reply") or "")
        except Exception:
            direct_reply = ""
        if direct_reply and not tools:
            response = LLMResponse(
                text=direct_reply,
                stop_reason="end_turn",
                usage={"dynamic_prompt_filter": 1},
                model="aureon-dynamic-prompt-filter",
                raw={"dynamic_prompt_filter": dynamic_filter},
            )
            return self._finalize_dynamic_response(
                response,
                dynamic_filter,
                reply_source="aureon_dynamic_prompt_filter_direct",
            )

        enriched_system = self._enrich_system(filtered_system, messages)

        # Try local LLM first
        if not _llm_http_disabled() and self.local.health_check():
            self.model = f"aureon-ollama-hybrid:{self.local.model}"
            if self._context_weaver_enabled(tools, max_tokens, kwargs):
                try:
                    shard_results = self._run_weaver_shards(messages, enriched_system, temperature, dynamic_filter)
                    if any(item.get("ok") for item in shard_results):
                        response = self._compose_weaver_response(messages, shard_results, dynamic_filter)
                        return self._finalize_dynamic_response(
                            response,
                            dynamic_filter,
                            reply_source="ollama_cognitive_weaver",
                        )
                except Exception as exc:
                    logger.warning("Ollama context weaver failed; falling back to single local prompt: %s", exc)
            response = self.local.prompt(
                messages, enriched_system, tools, max_tokens, temperature, **kwargs
            )
            if response.stop_reason != "error":
                return self._finalize_dynamic_response(
                    response,
                    dynamic_filter,
                    reply_source="ollama_cognitive_hybrid",
                )

        # Fallback to brain-only
        logger.info("Local LLM unavailable — falling back to AureonBrain")
        response = self.brain.prompt(messages, filtered_system, tools, max_tokens, temperature, **kwargs)
        return self._finalize_dynamic_response(
            response,
            dynamic_filter,
            reply_source="aureon_brain_fallback",
        )

    def stream(
        self,
        messages: List[Dict[str, Any]],
        system: str = "",
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs,
    ) -> Generator[StreamChunk, None, None]:
        dynamic_filter = self._build_dynamic_filter(messages, system, kwargs)
        filtered_system = self._system_with_dynamic_filter(system, dynamic_filter)
        enriched_system = self._enrich_system(filtered_system, messages)

        if not _llm_http_disabled() and self.local.health_check():
            self.model = f"aureon-ollama-hybrid:{self.local.model}"
            yield from self.local.stream(
                messages, enriched_system, tools, max_tokens, temperature, **kwargs
            )
        else:
            yield from self.brain.stream(
                messages, filtered_system, tools, max_tokens, temperature, **kwargs
            )

    def health_check(self) -> bool:
        if _llm_http_disabled():
            return self.brain.health_check()
        return self.local.health_check() or self.brain.health_check()


# -----------------------------------------------------------------------------
# Optional adapters for interactive conversation (Vault UI)
# -----------------------------------------------------------------------------


class AureonStubAdapter(LLMAdapter):
    """
    A fast, offline-safe adapter used when no real LLM backend is configured.

    This exists so interactive layers (Vault UI voices) never silently fall back
    to the market-rule engine and never hang on long HTTP timeouts.
    """

    def __init__(self, message: str, *, model: str = "aureon-stub"):
        self._message = str(message or "").strip() or "[AUREON] No backend configured."
        self._model = model

    def prompt(
        self,
        messages: List[Dict[str, Any]],
        system: str = "",
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs,
    ) -> LLMResponse:
        return LLMResponse(
            text=self._message,
            stop_reason="end_turn",
            usage={},
            model=self._model,
            raw=None,
        )

    def stream(
        self,
        messages: List[Dict[str, Any]],
        system: str = "",
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs,
    ) -> Generator[StreamChunk, None, None]:
        yield StreamChunk(text=self._message)
        yield StreamChunk(done=True, stop_reason="end_turn")

    def health_check(self) -> bool:
        return True


class AureonAnthropicAdapter(LLMAdapter):
    """
    Optional external adapter (Anthropic Messages API).

    Only used when ANTHROPIC_API_KEY is present. This keeps the default path
    "in-house", but allows the Vault UI to actually converse when the local LLM
    server is not running.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.model = model or os.environ.get("AUREON_ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")
        self._client = None

        if not self.api_key:
            return
        try:
            from anthropic import Anthropic  # type: ignore
            self._client = Anthropic(api_key=self.api_key)
        except Exception as e:
            logger.debug("Anthropic SDK unavailable: %s", e)
            self._client = None

    @staticmethod
    def _coerce_text(content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: List[str] = []
            for c in content:
                if isinstance(c, dict):
                    if c.get("type") == "text":
                        parts.append(str(c.get("text", "")))
                    elif "text" in c:
                        parts.append(str(c.get("text", "")))
                elif hasattr(c, "text"):
                    parts.append(str(getattr(c, "text")))
                elif isinstance(c, str):
                    parts.append(c)
            return "\n".join(p for p in parts if p).strip()
        if isinstance(content, dict) and "text" in content:
            return str(content.get("text", ""))
        return str(content)

    def prompt(
        self,
        messages: List[Dict[str, Any]],
        system: str = "",
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs,
    ) -> LLMResponse:
        if not self._client:
            return LLMResponse(
                text="[ERROR] Anthropic adapter not configured (missing ANTHROPIC_API_KEY or SDK).",
                stop_reason="error",
                model="anthropic",
            )

        # Anthropic supports system as a top-level param and messages as role/content.
        coerced: List[Dict[str, str]] = []
        for m in messages or []:
            role = str(m.get("role", "user") or "user")
            if role not in ("user", "assistant"):
                role = "user"
            coerced.append({"role": role, "content": self._coerce_text(m.get("content", ""))})

        try:
            resp = self._client.messages.create(
                model=self.model,
                max_tokens=int(max_tokens),
                temperature=float(temperature),
                system=str(system or "") or None,
                messages=coerced,
            )
        except Exception as e:
            return LLMResponse(text=f"[ERROR] {e}", stop_reason="error", model=self.model, raw=None)

        # Extract text blocks
        text_parts: List[str] = []
        try:
            for b in getattr(resp, "content", []) or []:
                # SDK returns content blocks with .type and .text
                if getattr(b, "type", "") == "text":
                    text_parts.append(str(getattr(b, "text", "")))
        except Exception:
            pass
        text = "\n".join([t for t in text_parts if t]).strip()

        usage: Dict[str, int] = {}
        try:
            u = getattr(resp, "usage", None)
            if u is not None:
                in_tok = int(getattr(u, "input_tokens", 0) or 0)
                out_tok = int(getattr(u, "output_tokens", 0) or 0)
                usage = {"input_tokens": in_tok, "output_tokens": out_tok, "total_tokens": in_tok + out_tok}
        except Exception:
            usage = {}

        stop = "end_turn"
        try:
            sr = str(getattr(resp, "stop_reason", "") or "")
            if sr == "max_tokens":
                stop = "max_tokens"
        except Exception:
            stop = "end_turn"

        return LLMResponse(
            text=text,
            tool_calls=[],
            stop_reason=stop,
            usage=usage,
            model=str(getattr(resp, "model", "") or self.model),
            raw=resp,
        )

    def stream(
        self,
        messages: List[Dict[str, Any]],
        system: str = "",
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs,
    ) -> Generator[StreamChunk, None, None]:
        # Minimal streaming wrapper for callers that expect stream()
        response = self.prompt(messages, system, tools, max_tokens, temperature, **kwargs)
        for word in (response.text or "").split(" "):
            if word:
                yield StreamChunk(text=word + " ")
        yield StreamChunk(done=True, stop_reason=response.stop_reason)

    def health_check(self) -> bool:
        return bool(self._client)


def build_voice_adapter(lane: str = "general") -> LLMAdapter:
    """
    Build a safe default adapter for the Vault Voice layer.

    Priority:
      1. AureonHybridAdapter (configured Ollama local/cloud plus AureonBrain) if reachable
      2. Explicit external backends only when requested
      3. Stub adapter with actionable configuration instructions

    Override with AUREON_VOICE_BACKEND:
      - local | ollama | ollama_hybrid | anthropic | brain
    """
    backend = (os.environ.get("AUREON_VOICE_BACKEND", "") or "").strip().lower()

    if backend in ("brain", "aureonbrain", "rule", "rules"):
        return AureonBrainAdapter()

    if backend in ("hybrid", "ollama_hybrid", "cognitive", "cognitive_ollama", "aureon_hybrid"):
        try:
            from aureon.integrations.ollama import OllamaModelSwitchboard

            adapter, _selection = OllamaModelSwitchboard().hybrid_adapter_for(lane)
            return adapter
        except Exception:
            return AureonHybridAdapter()

    if backend in ("ollama", "native_ollama", "ollama_native"):
        try:
            from aureon.integrations.ollama import OllamaModelSwitchboard

            adapter, _selection = OllamaModelSwitchboard().adapter_for(lane)
            if adapter.health_check():
                return adapter
        except Exception as exc:
            return AureonStubAdapter(
                "Ollama backend could not be initialized.\n"
                f"Reason: {exc}\n"
                "Start Ollama, install a model, then set AUREON_VOICE_BACKEND=ollama_hybrid for Aureon cognitive chat.",
                model="ollama-unavailable",
            )
        return AureonStubAdapter(
            "Ollama is not reachable or has no usable chat model.\n"
            "Run: ollama serve\n"
            "Then: ollama pull qwen2.5:0.5b\n"
            "Then set: AUREON_VOICE_BACKEND=ollama_hybrid and AUREON_LLM_MODEL=qwen2.5:0.5b",
            model="ollama-unavailable",
        )

    if backend in ("anthropic", "claude"):
        if os.environ.get("ANTHROPIC_API_KEY"):
            a = AureonAnthropicAdapter()
            if a.health_check():
                return a
        fallback = AureonHybridAdapter()
        if not _llm_http_disabled() and fallback.local.health_check():
            return fallback
        return AureonStubAdapter(
            "No Anthropic or configured Ollama fallback backend is reachable.",
            model="anthropic-unconfigured",
        )

    if backend in ("", "auto", "local", "aureon_ollama", "unified_cognitive"):
        try:
            from aureon.integrations.ollama import OllamaModelSwitchboard

            hybrid, _selection = OllamaModelSwitchboard().hybrid_adapter_for(lane)
        except Exception:
            hybrid = AureonHybridAdapter()
        if not _llm_http_disabled() and hybrid.local.health_check():
            hybrid.model = f"aureon-ollama-hybrid:{hybrid.local.model}"
            return hybrid
        if backend in ("", "auto") and hybrid.brain.health_check():
            return hybrid

    if backend in ("plain_local", "local_only"):
        try:
            from aureon.integrations.ollama import OllamaModelSwitchboard

            local, _selection = OllamaModelSwitchboard().compatible_adapter_for(lane)
        except Exception:
            local = AureonLocalAdapter()
        if local.health_check():
            return local

    # Offline-safe final fallback. When the configured Ollama endpoint is cloud,
    # the hybrid branch above is the explicit repo-wide external fallback.
    return AureonStubAdapter(
        "No LLM backend is reachable.\n"
        "To enable real conversation for Vault voices:\n"
        "  1) Start Ollama and install a local chat model.\n"
        "  2) Set AUREON_VOICE_BACKEND=ollama_hybrid and AUREON_LLM_ALLOW_HTTP_IN_AUDIT=1.\n"
        "  3) Set AUREON_LLM_MODEL to a local model such as llama3:latest for deeper replies.\n",
        model="no-backend",
    )
