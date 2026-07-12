"""
Aureon Operator — the recorded ("self") model adapter.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

When there is no live API key and no local server, the model can still be a real
flagship model — the one running this session. This adapter lets that model
*act as* a switchboard line: its genuine generations are recorded once to a JSONL
fixture, and the adapter serves them back so the operator chain runs
automatically, deterministically, and reproducibly.

It is an ``LLMAdapter`` like any other, so the moment a real
OpenAI/Grok/Gemini/Anthropic key is present the operator swaps to that line with
zero code change. The recorded adapter exists so the design can be *seen working
end-to-end through the entire repo* in a keyless sandbox — the benchmark's
"raw vs Aureon" outputs are real model text, captured, not stubbed.

Fixture format — one JSON object per line:
    {"prompt": "...", "mode": "baseline"|"aureon", "persona": "", "answer": "..."}

Lookup key is (normalised_prompt, mode, persona), with a fall-back to persona="".
Unknown prompts return a loud, obviously-missing marker so gaps can't masquerade
as answers.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from aureon.inhouse_ai.llm_adapter import LLMAdapter, LLMResponse, StreamChunk

logger = logging.getLogger("aureon.operator.self_adapter")

_MISSING_PREFIX = "[NO_RECORDING]"


def normalise_prompt(text: str) -> str:
    """Stable key: lowercase, collapse whitespace, strip trailing punctuation."""
    t = re.sub(r"\s+", " ", str(text or "").strip().lower())
    return t.rstrip(" ?.!")


def _latest_user_text(messages: List[Dict[str, Any]]) -> str:
    for msg in reversed(messages or []):
        if str(msg.get("role") or "user").lower() == "user":
            content = msg.get("content", "")
            if isinstance(content, list):
                parts = [
                    str(c.get("text", "")) if isinstance(c, dict) else str(c)
                    for c in content
                ]
                return "\n".join(p for p in parts if p)
            return str(content)
    return ""


class RecordedAdapter(LLMAdapter):
    """Serves recorded generations for a given mode (and optional persona)."""

    def __init__(
        self,
        fixture_path: str | Path,
        mode: str,
        persona: str = "",
        model: str = "fable-5-recorded",
    ):
        self.fixture_path = Path(fixture_path)
        self.mode = mode
        self.persona = persona
        self.model = f"{model}:{mode}" + (f":{persona}" if persona else "")
        self._index: Dict[tuple, str] = {}
        self.misses: List[str] = []
        self._load()

    def _load(self) -> None:
        if not self.fixture_path.exists():
            logger.warning("recording fixture missing: %s", self.fixture_path)
            return
        for line in self.fixture_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            key = (normalise_prompt(rec.get("prompt", "")), rec.get("mode", ""), rec.get("persona", ""))
            self._index[key] = str(rec.get("answer", ""))

    def _lookup(self, prompt: str) -> Optional[str]:
        norm = normalise_prompt(prompt)
        for persona in (self.persona, ""):
            hit = self._index.get((norm, self.mode, persona))
            if hit is not None:
                return hit
        return None

    def prompt(
        self,
        messages: List[Dict[str, Any]],
        system: str = "",
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs,
    ) -> LLMResponse:
        user_text = _latest_user_text(messages)
        answer = self._lookup(user_text)
        if answer is None:
            self.misses.append(user_text)
            return LLMResponse(
                text=f"{_MISSING_PREFIX} mode={self.mode} persona={self.persona!r} prompt={user_text[:80]!r}",
                stop_reason="end_turn",
                model=self.model,
            )
        return LLMResponse(text=answer, stop_reason="end_turn", model=self.model)

    def stream(
        self,
        messages: List[Dict[str, Any]],
        system: str = "",
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs,
    ) -> Generator[StreamChunk, None, None]:
        resp = self.prompt(messages, system, tools, max_tokens, temperature, **kwargs)
        for word in resp.text.split(" "):
            yield StreamChunk(text=word + " ")
        yield StreamChunk(done=True, stop_reason="end_turn")

    def health_check(self) -> bool:
        return bool(self._index)


def is_missing(text: str) -> bool:
    return str(text or "").startswith(_MISSING_PREFIX)


__all__ = ["RecordedAdapter", "normalise_prompt", "is_missing"]
