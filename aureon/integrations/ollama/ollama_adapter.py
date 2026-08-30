"""
OllamaLLMAdapter — LLMAdapter shim over the native OllamaBridge
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Implements `aureon.inhouse_ai.LLMAdapter` so any voice / agent / team
that accepts an LLMAdapter can be pointed at a real Ollama instance via
its native /api/chat surface (instead of the OpenAI-compat /v1 surface
that AureonLocalAdapter uses).

Why a second adapter?

  • Native API gives us access to Ollama-only knobs: `keep_alive`,
    `think`, `format` (JSON or JSON schema), and Ollama's `options`
    dict (temperature, num_ctx, top_k, top_p, repeat_penalty, seed, …).
  • The voice layer already calls `adapter.prompt(...)` — this adapter
    slots in with zero changes to VaultVoice, SelfDialogueEngine, or
    ThoughtStreamLoop.
  • The bridge degrades gracefully, so if Ollama is offline the adapter
    still returns a well-formed LLMResponse (with stop_reason='error')
    that the vault can ingest as a card.

Typical use:

    from aureon.integrations.ollama import OllamaLLMAdapter
    from aureon.vault.voice import build_all_voices, SelfDialogueEngine

    adapter = OllamaLLMAdapter(model="llama3.1:8b")
    voices = build_all_voices(adapter=adapter)
    engine = SelfDialogueEngine(vault=my_vault, voices=voices, adapter=adapter)
    engine.converse()
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Generator, List, Optional

from aureon.inhouse_ai.llm_adapter import (
    LLMAdapter,
    LLMResponse,
    StreamChunk,
    ToolCall,
)
from aureon.integrations.ollama.ollama_bridge import OllamaBridge

logger = logging.getLogger("aureon.integrations.ollama.adapter")


class OllamaLLMAdapter(LLMAdapter):
    """An `LLMAdapter` backed by the native Ollama REST API."""

    def __init__(
        self,
        bridge: Optional[OllamaBridge] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        keep_alive: Optional[str] = None,
        default_options: Optional[Dict[str, Any]] = None,
    ):
        self.bridge = bridge or OllamaBridge(
            base_url=base_url,
            chat_model=model,
            keep_alive=keep_alive,
            api_key=api_key,
        )
        if model:
            self.bridge.chat_model = model
        self.model = self.bridge.chat_model
        self.default_options: Dict[str, Any] = dict(default_options or {})

    # ─────────────────────────────────────────────────────────────────────
    # LLMAdapter interface
    # ─────────────────────────────────────────────────────────────────────

    def prompt(
        self,
        messages: List[Dict[str, Any]],
        system: str = "",
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs,
    ) -> LLMResponse:
        options = dict(self.default_options)
        if temperature is not None:
            options["temperature"] = float(temperature)
        if max_tokens is not None:
            options["num_predict"] = int(max_tokens)

        converted_tools = self._convert_tools(tools) if tools else None
        format_arg = kwargs.get("format")
        think_arg = kwargs.get("think")

        data = self.bridge.chat(
            messages=self._normalise_messages(messages),
            system=system or None,
            tools=converted_tools,
            options=options or None,
            format=format_arg,
            think=think_arg,
        )

        msg = data.get("message") or {}
        text = msg.get("content") or ""
        stop_reason = "end_turn"
        if data.get("error"):
            stop_reason = "error"
        elif data.get("done_reason") == "length":
            stop_reason = "max_tokens"

        tool_calls: List[ToolCall] = []
        for tc in msg.get("tool_calls") or []:
            func = tc.get("function") or {}
            args = func.get("arguments") or {}
            tool_calls.append(
                ToolCall(name=str(func.get("name", "")), arguments=dict(args))
            )
        if tool_calls:
            stop_reason = "tool_use"

        return LLMResponse(
            text=text,
            tool_calls=tool_calls,
            stop_reason=stop_reason,
            usage={
                "prompt_eval_count": int(data.get("prompt_eval_count", 0) or 0),
                "eval_count": int(data.get("eval_count", 0) or 0),
                "total_tokens": int(data.get("prompt_eval_count", 0) or 0)
                + int(data.get("eval_count", 0) or 0),
            },
            model=str(data.get("model", self.bridge.chat_model)),
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
        options = dict(self.default_options)
        if temperature is not None:
            options["temperature"] = float(temperature)
        if max_tokens is not None:
            options["num_predict"] = int(max_tokens)

        converted_tools = self._convert_tools(tools) if tools else None
        format_arg = kwargs.get("format")
        think_arg = kwargs.get("think")

        for chunk in self.bridge.chat_stream(
            messages=self._normalise_messages(messages),
            system=system or None,
            tools=converted_tools,
            options=options or None,
            format=format_arg,
            think=think_arg,
        ):
            msg = chunk.get("message") or {}
            if msg.get("content"):
                yield StreamChunk(text=msg["content"])
            for tc in msg.get("tool_calls") or []:
                func = tc.get("function") or {}
                yield StreamChunk(
                    tool_call=ToolCall(
                        name=str(func.get("name", "")),
                        arguments=dict(func.get("arguments") or {}),
                    )
                )
            if chunk.get("done"):
                reason = "end_turn"
                if chunk.get("error"):
                    reason = "error"
                elif chunk.get("done_reason") == "length":
                    reason = "max_tokens"
                yield StreamChunk(done=True, stop_reason=reason)
                return

    def health_check(self) -> bool:
        return self.bridge.health_check()

    # ─────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _normalise_messages(
        messages: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Flatten any list-of-content-blocks into plain strings for Ollama."""
        out: List[Dict[str, Any]] = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if isinstance(content, list):
                parts: List[str] = []
                for c in content:
                    if isinstance(c, dict):
                        if c.get("type") == "text":
                            parts.append(str(c.get("text", "")))
                        elif c.get("type") == "tool_result":
                            parts.append(str(c.get("content", "")))
                        elif hasattr(c, "text"):
                            parts.append(str(c.text))
                    elif isinstance(c, str):
                        parts.append(c)
                    elif hasattr(c, "text"):
                        parts.append(str(c.text))
                content = "\n".join(p for p in parts if p)
            out.append({"role": role, "content": str(content)})
        return out

    @staticmethod
    def _convert_tools(
        tools: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Convert Aureon tool defs to Ollama /api/chat tool format."""
        converted: List[Dict[str, Any]] = []
        for t in tools:
            converted.append(
                {
                    "type": "function",
                    "function": {
                        "name": t.get("name", ""),
                        "description": t.get("description", ""),
                        "parameters": t.get(
                            "input_schema", {"type": "object", "properties": {}}
                        ),
                    },
                }
            )
        return converted
