"""
Agent — Sovereign AI Agent
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The core agent unit.  Each Agent has:
  - run()      : execute a task to completion (agentic loop)
  - prompt()   : single-turn prompt, return response
  - stream()   : stream response token-by-token

Agents are configured via AgentConfig and backed by any LLMAdapter.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generator, List, Optional

from aureon.inhouse_ai.llm_adapter import LLMAdapter, LLMResponse, StreamChunk
from aureon.inhouse_ai.tool_registry import ToolRegistry

logger = logging.getLogger("aureon.inhouse_ai.agent")

# ─────────────────────────────────────────────────────────────────────────────
# Agent configuration
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class AgentConfig:
    """Configuration for an Agent."""

    name: str = "Agent"
    system_prompt: str = ""
    max_turns: int = 8
    max_tokens: int = 4096
    temperature: float = 0.7
    tools_enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# Agent
# ─────────────────────────────────────────────────────────────────────────────


class Agent:
    """
    A sovereign AI agent backed by an in-house LLM adapter.

    Usage:
        adapter = AureonLocalAdapter()
        registry = ToolRegistry()
        agent = Agent(adapter, config=AgentConfig(name="Nexus"), tools=registry)
        result = agent.run("Analyse the current market state")
    """

    def __init__(
        self,
        adapter: LLMAdapter,
        config: Optional[AgentConfig] = None,
        tools: Optional[ToolRegistry] = None,
    ):
        self.adapter = adapter
        self.config = config or AgentConfig()
        # An explicitly empty registry is a deliberate no-tool capability
        # boundary. Only None requests the default builtin tool belt.
        self.tools = tools if tools is not None else ToolRegistry(include_builtins=True)
        self.id = str(uuid.uuid4())

        # State
        self._running = False
        self._turn_count = 0
        self._last_response: Optional[LLMResponse] = None
        self._history: List[Dict[str, Any]] = []

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def is_running(self) -> bool:
        return self._running

    def prompt(
        self,
        message: str,
        system_override: Optional[str] = None,
        tools_override: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        """Single-turn prompt — send message, get response."""
        messages = [{"role": "user", "content": message}]

        tool_defs = tools_override
        if tool_defs is None and self.config.tools_enabled:
            tool_defs = self.tools.list_tools() if self.tools else None

        response = self.adapter.prompt(
            messages=messages,
            system=system_override or self.config.system_prompt,
            tools=tool_defs,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
        )
        self._last_response = response
        return response

    def stream(
        self,
        message: str,
        system_override: Optional[str] = None,
    ) -> Generator[StreamChunk, None, None]:
        """Stream response token-by-token."""
        messages = [{"role": "user", "content": message}]

        tool_defs = self.tools.list_tools() if (self.tools and self.config.tools_enabled) else None

        yield from self.adapter.stream(
            messages=messages,
            system=system_override or self.config.system_prompt,
            tools=tool_defs,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
        )

    def run(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        on_tool_call: Optional[Callable[[str, Dict], None]] = None,
    ) -> str:
        """
        Run the agent in an agentic loop until it produces a final response
        or hits max_turns.  Tool calls are automatically dispatched.

        Args:
            task: The task/question for the agent
            context: Optional context dict (appended to the task)
            on_tool_call: Optional callback when a tool is called (name, args)

        Returns:
            The agent's final text response.
        """
        self._running = True
        self._turn_count = 0

        # Build initial message
        if context:
            full_task = f"{task}\n\nContext:\n{json.dumps(context, indent=2)}"
        else:
            full_task = task

        messages: List[Dict[str, Any]] = [{"role": "user", "content": full_task}]
        tool_defs = self.tools.list_tools() if (self.tools and self.config.tools_enabled) else None

        try:
            for turn in range(self.config.max_turns):
                self._turn_count = turn + 1

                response = self.adapter.prompt(
                    messages=messages,
                    system=self.config.system_prompt,
                    tools=tool_defs,
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                )
                self._last_response = response

                # Append assistant response to history
                assistant_content = self._build_assistant_content(response)
                messages.append({"role": "assistant", "content": assistant_content})

                # If no tool calls → we have a final answer
                if not response.has_tool_calls:
                    self._history.append({
                        "task": task,
                        "response": response.text,
                        "turns": self._turn_count,
                        "timestamp": time.time(),
                    })
                    return response.text

                # Dispatch tool calls
                tool_results = []
                for tc in response.tool_calls:
                    if on_tool_call:
                        on_tool_call(tc.name, tc.arguments)

                    logger.info("[%s] Tool call: %s(%s)", self.name, tc.name, tc.arguments)
                    result_str = self.tools.execute(tc.name, tc.arguments)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tc.id,
                        "content": result_str,
                    })

                messages.append({"role": "user", "content": tool_results})

            # Max turns exhausted
            final_text = response.text if response else "Max turns reached."
            self._history.append({
                "task": task,
                "response": final_text,
                "turns": self._turn_count,
                "max_turns_hit": True,
                "timestamp": time.time(),
            })
            return final_text

        finally:
            self._running = False

    def _build_assistant_content(self, response: LLMResponse) -> Any:
        """Build the assistant message content for conversation history."""
        if not response.has_tool_calls:
            return response.text

        # Build content blocks matching the expected format
        content = []
        if response.text:
            content.append({"type": "text", "text": response.text})
        for tc in response.tool_calls:
            content.append({
                "type": "tool_use",
                "id": tc.id,
                "name": tc.name,
                "input": tc.arguments,
            })
        return content

    def get_status(self) -> Dict[str, Any]:
        """Return agent status."""
        return {
            "id": self.id,
            "name": self.name,
            "running": self._running,
            "turn_count": self._turn_count,
            "history_count": len(self._history),
            "adapter_healthy": self.adapter.health_check(),
            "tools_count": len(self.tools) if self.tools else 0,
        }

    def reset(self):
        """Reset agent state."""
        self._running = False
        self._turn_count = 0
        self._last_response = None
        self._history.clear()
