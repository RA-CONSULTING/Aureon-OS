"""
OllamaBridge — Native Ollama Client for the Aureon Vault
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Thin, native client for the Ollama REST API (docs:
https://github.com/ollama/ollama/blob/main/docs/api.md).

Unlike the existing AureonLocalAdapter, which speaks Ollama's
OpenAI-compat surface (/v1/chat/completions), this bridge uses the
tool's first-class endpoints so the vault can do everything Ollama
exposes:

    chat          → POST /api/chat
    generate      → POST /api/generate
    embed         → POST /api/embed   (with /api/embeddings fallback)
    list_models   → GET  /api/tags
    show_model    → POST /api/show
    pull_model    → POST /api/pull    (streamed progress)
    ps            → GET  /api/ps
    version       → GET  /api/version
    health_check  → wraps /api/version

Environment overrides:

    AUREON_OLLAMA_BASE_URL   — default http://localhost:11434
    AUREON_OLLAMA_MODEL      — default llama3
    AUREON_OLLAMA_EMBED_MODEL — default nomic-embed-text
    AUREON_OLLAMA_KEEP_ALIVE — default 5m

Graceful degradation: if the `requests` library is not installed, or
Ollama is not reachable, every method returns a well-formed fallback
instead of raising, so the cognitive loops keep ticking even when the
LLM stack is offline.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generator, List, Optional

from aureon.ollama_config import (
    DEFAULT_OLLAMA_NATIVE_BASE_URL,
    ensure_ollama_runtime_config,
    is_ollama_cloud_url,
    ollama_authorization_headers,
    resolve_ollama_api_key,
    resolve_ollama_native_base_url,
    resolve_ollama_reasoning_effort,
)

logger = logging.getLogger("aureon.integrations.ollama")

# Default values — all overridable via env
DEFAULT_BASE_URL = DEFAULT_OLLAMA_NATIVE_BASE_URL
DEFAULT_CHAT_MODEL = "llama3"
DEFAULT_EMBED_MODEL = "nomic-embed-text"
DEFAULT_KEEP_ALIVE = "5m"
DEFAULT_TIMEOUT_S = 120


class OllamaBridgeError(RuntimeError):
    """Raised only when a caller explicitly requests strict mode."""


@dataclass
class OllamaModel:
    """One entry from /api/tags."""

    name: str = ""
    model: str = ""
    size_bytes: int = 0
    digest: str = ""
    modified_at: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_api(cls, d: Dict[str, Any]) -> "OllamaModel":
        return cls(
            name=str(d.get("name", "")),
            model=str(d.get("model", d.get("name", ""))),
            size_bytes=int(d.get("size", 0) or 0),
            digest=str(d.get("digest", "")),
            modified_at=str(d.get("modified_at", "")),
            details=dict(d.get("details", {}) or {}),
        )


@dataclass
class OllamaPsEntry:
    """One entry from /api/ps (a currently running model)."""

    name: str = ""
    model: str = ""
    size_bytes: int = 0
    size_vram_bytes: int = 0
    expires_at: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_api(cls, d: Dict[str, Any]) -> "OllamaPsEntry":
        return cls(
            name=str(d.get("name", "")),
            model=str(d.get("model", d.get("name", ""))),
            size_bytes=int(d.get("size", 0) or 0),
            size_vram_bytes=int(d.get("size_vram", 0) or 0),
            expires_at=str(d.get("expires_at", "")),
            details=dict(d.get("details", {}) or {}),
        )


class OllamaBridge:
    """
    Native Ollama client. Thread-safe at the HTTP-session level.

    Example:
        bridge = OllamaBridge()
        if bridge.health_check():
            reply = bridge.chat(
                model="llama3",
                messages=[{"role": "user", "content": "hello"}],
            )
            print(reply["message"]["content"])

            vec = bridge.embed("hello world")
            print(len(vec))
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        chat_model: Optional[str] = None,
        embed_model: Optional[str] = None,
        keep_alive: Optional[str] = None,
        timeout_s: Optional[float] = None,
        api_key: Optional[str] = None,
    ):
        ensure_ollama_runtime_config(
            explicit_config=base_url is not None or api_key is not None,
        )
        self.base_url = resolve_ollama_native_base_url(base_url)
        self.api_key = resolve_ollama_api_key(api_key)
        self._authorization_headers = ollama_authorization_headers(
            base_url=self.base_url,
            api_key=api_key,
        )
        self.chat_model = chat_model or os.environ.get(
            "AUREON_OLLAMA_MODEL", DEFAULT_CHAT_MODEL
        )
        self.embed_model = embed_model or os.environ.get(
            "AUREON_OLLAMA_EMBED_MODEL", DEFAULT_EMBED_MODEL
        )
        self.keep_alive = keep_alive or os.environ.get(
            "AUREON_OLLAMA_KEEP_ALIVE", DEFAULT_KEEP_ALIVE
        )
        self.timeout_s = float(timeout_s or DEFAULT_TIMEOUT_S)

        self._session: Any = None
        self._requests_available = False
        try:
            import requests  # type: ignore

            self._session = requests.Session()
            self._requests_available = True
        except Exception:
            logger.debug("requests not installed — OllamaBridge degraded")

        # Cached introspection
        self._last_health: Optional[bool] = None
        self._last_health_at: float = 0.0
        self._last_version: str = ""

    # ─────────────────────────────────────────────────────────────────────
    # Generic HTTP helpers
    # ─────────────────────────────────────────────────────────────────────

    def _get(self, path: str, timeout: Optional[float] = None) -> Any:
        if not self._requests_available:
            raise OllamaBridgeError("requests library not available")
        resp = self._session.get(
            f"{self.base_url}{path}",
            headers=self._authorization_headers,
            timeout=timeout or self.timeout_s,
        )
        resp.raise_for_status()
        return resp.json()

    def _post(
        self,
        path: str,
        body: Dict[str, Any],
        timeout: Optional[float] = None,
    ) -> Any:
        if not self._requests_available:
            raise OllamaBridgeError("requests library not available")
        resp = self._session.post(
            f"{self.base_url}{path}",
            json=body,
            headers=self._authorization_headers,
            timeout=timeout or self.timeout_s,
        )
        resp.raise_for_status()
        return resp.json()

    def _post_stream(
        self,
        path: str,
        body: Dict[str, Any],
        timeout: Optional[float] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        if not self._requests_available:
            raise OllamaBridgeError("requests library not available")
        resp = self._session.post(
            f"{self.base_url}{path}",
            json=body,
            headers=self._authorization_headers,
            stream=True,
            timeout=timeout or self.timeout_s,
        )
        resp.raise_for_status()
        for raw in resp.iter_lines():
            if not raw:
                continue
            try:
                yield json.loads(raw.decode("utf-8", errors="replace"))
            except json.JSONDecodeError:
                continue

    # ─────────────────────────────────────────────────────────────────────
    # Health + introspection
    # ─────────────────────────────────────────────────────────────────────

    def version(self) -> str:
        """Return Ollama server version (empty string if unreachable)."""
        try:
            data = self._get("/api/version", timeout=5)
            self._last_version = str(data.get("version", ""))
            return self._last_version
        except Exception as e:
            logger.debug("ollama version fetch failed: %s", e)
            return ""

    def health_check(self, max_age_s: float = 5.0) -> bool:
        """
        Return True if the Ollama server is reachable.
        Caches the result for `max_age_s` seconds so the self-feedback
        loop can call this on every tick cheaply.
        """
        now = time.time()
        if (
            self._last_health is not None
            and (now - self._last_health_at) < max_age_s
        ):
            return self._last_health
        ok = bool(self.version())
        self._last_health = ok
        self._last_health_at = now
        return ok

    def list_models(self) -> List[OllamaModel]:
        """GET /api/tags — the local model library."""
        try:
            data = self._get("/api/tags")
            return [OllamaModel.from_api(m) for m in (data.get("models") or [])]
        except Exception as e:
            logger.debug("ollama list_models failed: %s", e)
            return []

    def ps(self) -> List[OllamaPsEntry]:
        """GET /api/ps — models currently loaded in memory."""
        try:
            data = self._get("/api/ps")
            return [OllamaPsEntry.from_api(m) for m in (data.get("models") or [])]
        except Exception as e:
            logger.debug("ollama ps failed: %s", e)
            return []

    def show_model(self, model: str) -> Dict[str, Any]:
        """POST /api/show — full model metadata (license, params, template)."""
        try:
            return self._post("/api/show", {"model": model})
        except Exception as e:
            logger.debug("ollama show_model(%s) failed: %s", model, e)
            return {}

    # ─────────────────────────────────────────────────────────────────────
    # Model download
    # ─────────────────────────────────────────────────────────────────────

    def pull_model(
        self,
        model: str,
        on_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> bool:
        """
        POST /api/pull — download a model. Streams progress chunks to
        `on_progress` (if given). Returns True once the stream ends
        cleanly with a 'success' status.
        """
        body = {"model": model, "stream": True}
        last_status = ""
        try:
            for chunk in self._post_stream("/api/pull", body, timeout=None):
                last_status = str(chunk.get("status", ""))
                if on_progress is not None:
                    try:
                        on_progress(chunk)
                    except Exception:
                        pass
            return "success" in last_status.lower() or last_status == ""
        except Exception as e:
            logger.debug("ollama pull_model(%s) failed: %s", model, e)
            return False

    # ─────────────────────────────────────────────────────────────────────
    # Chat / generate
    # ─────────────────────────────────────────────────────────────────────

    def chat(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        system: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        options: Optional[Dict[str, Any]] = None,
        format: Optional[Any] = None,
        think: Optional[Any] = None,
        keep_alive: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        POST /api/chat — non-streaming. Returns the raw Ollama response
        dict (with a `message` field). On failure returns a degraded dict
        carrying `error` so the voice layer can still make an utterance.
        """
        body: Dict[str, Any] = {
            "model": model or self.chat_model,
            "messages": self._prepend_system(messages, system),
            "stream": False,
            "keep_alive": keep_alive or self.keep_alive,
        }
        if tools:
            body["tools"] = tools
        if options:
            body["options"] = options
        if format is not None:
            body["format"] = format
        if think is None and is_ollama_cloud_url(self.base_url):
            effort = resolve_ollama_reasoning_effort()
            think = False if effort == "none" else effort
        if think is not None:
            body["think"] = think

        try:
            return self._post("/api/chat", body)
        except Exception as e:
            logger.debug("ollama chat failed: %s", e)
            return {
                "model": body["model"],
                "message": {"role": "assistant", "content": ""},
                "done": True,
                "done_reason": "error",
                "error": str(e),
            }

    def chat_stream(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        system: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        options: Optional[Dict[str, Any]] = None,
        format: Optional[Any] = None,
        think: Optional[Any] = None,
        keep_alive: Optional[str] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """POST /api/chat — streaming variant. Yields raw Ollama chunks."""
        body: Dict[str, Any] = {
            "model": model or self.chat_model,
            "messages": self._prepend_system(messages, system),
            "stream": True,
            "keep_alive": keep_alive or self.keep_alive,
        }
        if tools:
            body["tools"] = tools
        if options:
            body["options"] = options
        if format is not None:
            body["format"] = format
        if think is None and is_ollama_cloud_url(self.base_url):
            effort = resolve_ollama_reasoning_effort()
            think = False if effort == "none" else effort
        if think is not None:
            body["think"] = think
        try:
            yield from self._post_stream("/api/chat", body, timeout=None)
        except Exception as e:
            logger.debug("ollama chat_stream failed: %s", e)
            yield {"done": True, "error": str(e)}

    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        format: Optional[Any] = None,
        keep_alive: Optional[str] = None,
        think: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """POST /api/generate — single-shot prompt completion."""
        body: Dict[str, Any] = {
            "model": model or self.chat_model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": keep_alive or self.keep_alive,
        }
        if system:
            body["system"] = system
        if options:
            body["options"] = options
        if format is not None:
            body["format"] = format
        if think is None and is_ollama_cloud_url(self.base_url):
            effort = resolve_ollama_reasoning_effort()
            think = False if effort == "none" else effort
        if think is not None:
            body["think"] = think
        try:
            return self._post("/api/generate", body)
        except Exception as e:
            logger.debug("ollama generate failed: %s", e)
            return {
                "model": body["model"],
                "response": "",
                "done": True,
                "error": str(e),
            }

    # ─────────────────────────────────────────────────────────────────────
    # Embeddings
    # ─────────────────────────────────────────────────────────────────────

    def embed(
        self,
        text: Any,
        model: Optional[str] = None,
    ) -> List[List[float]]:
        """
        POST /api/embed — return a list of embedding vectors. `text` may
        be a string (→ 1 vector) or a list of strings (→ N vectors).

        Falls back to /api/embeddings (the older singular endpoint) if
        /api/embed is not available on this Ollama version.
        """
        inputs = [text] if isinstance(text, str) else list(text)
        mdl = model or self.embed_model
        # Try /api/embed first
        try:
            data = self._post("/api/embed", {"model": mdl, "input": inputs})
            vectors = data.get("embeddings") or []
            if vectors:
                return [[float(x) for x in v] for v in vectors]
        except Exception as e:
            logger.debug("ollama /api/embed failed (%s) — trying legacy", e)

        # Fallback: /api/embeddings (takes a single `prompt`, not `input`)
        out: List[List[float]] = []
        for item in inputs:
            try:
                data = self._post(
                    "/api/embeddings", {"model": mdl, "prompt": str(item)}
                )
                vec = data.get("embedding") or []
                out.append([float(x) for x in vec])
            except Exception as e:
                logger.debug("ollama /api/embeddings failed: %s", e)
                out.append([])
        return out

    # ─────────────────────────────────────────────────────────────────────
    # Internals
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _prepend_system(
        messages: List[Dict[str, Any]],
        system: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Ollama's /api/chat expects a system msg as role='system' inline."""
        if not system:
            return list(messages)
        has_system = any((m.get("role") == "system") for m in messages)
        if has_system:
            return list(messages)
        return [{"role": "system", "content": system}] + list(messages)

    # ─────────────────────────────────────────────────────────────────────
    # Snapshot (for the audit trail)
    # ─────────────────────────────────────────────────────────────────────

    def snapshot(self) -> Dict[str, Any]:
        """Return a shallow snapshot for telemetry / audit trail / vault cards."""
        reachable = self.health_check()
        snap: Dict[str, Any] = {
            "reachable": reachable,
            "base_url": self.base_url,
            "chat_model": self.chat_model,
            "embed_model": self.embed_model,
            "version": self._last_version,
            "requests_installed": self._requests_available,
            "cloud": is_ollama_cloud_url(self.base_url),
            "auth_required": is_ollama_cloud_url(self.base_url),
            "api_key_configured": bool(self.api_key),
            "authorization_header_enabled": bool(self._authorization_headers),
            "models": [],
            "running": [],
        }
        if reachable:
            snap["models"] = [m.name for m in self.list_models()][:50]
            snap["running"] = [m.name for m in self.ps()]
        return snap
