"""
AgentRunner — Conversation Loop + Tool Dispatch
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Manages the full conversation lifecycle for an Agent:
  - Multi-turn conversation with memory
  - Automatic tool dispatch
  - Message history management
  - Event callbacks for monitoring
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generator, List, Mapping

from aureon.inhouse_ai.llm_adapter import LLMAdapter, StreamChunk
from aureon.inhouse_ai.tool_registry import (
    ToolDispatchAuthorization,
    ToolDispatchProposal,
    ToolEffect,
    ToolRegistry,
)

logger = logging.getLogger("aureon.inhouse_ai.runner")

# Bounds on what ONE model response may ask this host to do. These sit here, not in the HTTP layer,
# because tool calls come from the model endpoint — which on the tenant plane is a server the user
# controls — so the request-body cap never applied to them.
_MAX_TOOL_CALLS_PER_RESPONSE = 16
_MAX_TOOL_ARG_BYTES = 64 * 1024


def _oversized_argument(arguments: Dict[str, Any] | None) -> str | None:
    """Name of the first argument whose serialized form exceeds the cap, else None."""
    for key, value in (arguments or {}).items():
        if isinstance(value, str):
            size = len(value.encode("utf-8", "replace"))
        else:
            try:
                size = len(json.dumps(value, default=str).encode("utf-8", "replace"))
            except Exception:  # noqa: BLE001 — unserializable ⇒ treat as oversized, not as a crash
                return str(key)
        if size > _MAX_TOOL_ARG_BYTES:
            return str(key)
    return None


@dataclass
class ConversationMessage:
    """A message in the conversation history."""

    role: str  # user | assistant | tool
    content: Any
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentRunner:
    """
    Manages the conversation loop for an agent.

    The runner maintains conversation state and handles:
      - Multi-turn conversation with automatic tool dispatch
      - Streaming with tool interleaving
      - Conversation history pruning
      - Event callbacks (on_message, on_tool_call, on_error)

    Usage:
        runner = AgentRunner(adapter, registry)
        runner.set_system("You are the Nexus agent...")

        # Single turn
        response = runner.turn("What's the market state?")

        # Continuous loop
        runner.loop(interval=60, task_fn=lambda: "Analyse current signals")
    """

    def __init__(
        self,
        adapter: LLMAdapter,
        tools: ToolRegistry | None = None,
        system_prompt: str = "",
        max_turns: int = 8,
        max_history: int = 50,
        *,
        governance_required: bool = False,
        authorize_tool_dispatch: (
            Callable[[ToolDispatchProposal], ToolDispatchAuthorization | None] | None
        ) = None,
        dispatch_context_provider: Callable[[], Mapping[str, Any]] | None = None,
    ):
        self.adapter = adapter
        # `is not None`, NOT `or`: ToolRegistry defines __len__, so an intentionally empty registry is
        # falsy and `or` would substitute the full built-in belt — a fail-open for any caller that
        # passes a deliberately narrowed toolbelt.
        self.tools = tools if tools is not None else ToolRegistry(include_builtins=True)
        self.system_prompt = system_prompt
        self.max_turns = max_turns
        self.max_history = max_history
        self.governance_required = bool(governance_required)
        self.authorize_tool_dispatch = authorize_tool_dispatch
        self.dispatch_context_provider = dispatch_context_provider

        self._history: List[ConversationMessage] = []
        self._messages: List[Dict[str, Any]] = []
        self._running = False
        self._turn_count = 0

        # Callbacks
        self.on_message: Callable[[str, str], None] | None = None
        self.on_tool_call: Callable[[str, Dict], None] | None = None
        self.on_tool_result: (
            Callable[
                [
                    ToolDispatchProposal | None,
                    ToolDispatchAuthorization | None,
                    str,
                ],
                None,
            ]
            | None
        ) = None
        self.on_error: Callable[[Exception], None] | None = None

    def set_system(self, prompt: str):
        """Update the system prompt."""
        self.system_prompt = prompt

    @staticmethod
    def _blocked_tool_result(tool_call_id: str, reason: str) -> Dict[str, str]:
        return {
            "type": "tool_result",
            "tool_use_id": tool_call_id,
            "content": json.dumps({"blocked": True, "reason": reason}),
        }

    def _dispatch_tool_calls(
        self,
        tool_calls: List[Any],
        *,
        runner_turn_index: int,
        dispatch_mode: str,
    ) -> List[Dict[str, str]]:
        """Bound and dispatch one model response identically for turn and stream."""
        tool_results: List[Dict[str, str]] = []
        governed = self.governance_required or bool(
            getattr(self.tools, "governance_required", False)
        ) or bool(getattr(self.tools, "hnc_coherence_required", False))

        for response_call_index, tc in enumerate(tool_calls):
            # Tool calls arrive in the MODEL's response, not the caller's request, so
            # request-body limits do not protect this host. Enforce the same bounds in
            # both runner paths before callbacks, governance suppliers, or handlers.
            if response_call_index >= _MAX_TOOL_CALLS_PER_RESPONSE:
                tool_results.append(self._blocked_tool_result(
                    tc.id,
                    "too many tool calls in one response "
                    f"(limit {_MAX_TOOL_CALLS_PER_RESPONSE})",
                ))
                continue
            if not isinstance(tc.arguments, dict):
                tool_results.append(self._blocked_tool_result(
                    tc.id,
                    "tool arguments must be a JSON object",
                ))
                continue
            oversized = _oversized_argument(tc.arguments)
            if oversized is not None:
                tool_results.append(self._blocked_tool_result(
                    tc.id,
                    f"argument '{oversized}' exceeds {_MAX_TOOL_ARG_BYTES} bytes",
                ))
                continue

            if self.on_tool_call:
                self.on_tool_call(tc.name, tc.arguments)
            logger.info("Tool dispatch: %s(%s)", tc.name, tc.arguments)

            proposal: ToolDispatchProposal | None = None
            authorization: ToolDispatchAuthorization | None = None
            if governed:
                try:
                    supplied_context = (
                        self.dispatch_context_provider()
                        if self.dispatch_context_provider is not None
                        else {}
                    )
                    if not isinstance(supplied_context, Mapping):
                        raise ValueError("dispatch context provider must return a mapping")
                    context = dict(supplied_context)
                    context["dispatch_mode"] = dispatch_mode
                    proposal = self.tools.build_dispatch_proposal(
                        tool_call_id=tc.id,
                        runner_turn_index=runner_turn_index,
                        response_call_index=response_call_index,
                        name=tc.name,
                        arguments=tc.arguments,
                        context=context,
                    )
                except Exception as exc:  # noqa: BLE001 - malformed proposals hold
                    result_str = json.dumps({
                        "blocked": True,
                        "reason": f"governance: could not build exact tool proposal: {exc}",
                        "tool": tc.name,
                    })
                else:
                    hnc_required = bool(
                        getattr(self.tools, "hnc_coherence_required", False)
                    )
                    hnc_ready = not hnc_required
                    preauthorize = getattr(
                        self.tools,
                        "preauthorize_tool_dispatch",
                        None,
                    )
                    if callable(preauthorize):
                        try:
                            hnc_ready = preauthorize(proposal) is True
                        except Exception as exc:  # noqa: BLE001 - HNC failure holds
                            logger.warning("HNC pre-authorization failed: %s", exc)
                            hnc_ready = False
                    # Unknown effects are never sent to an authority supplier. Known
                    # read-only effects take the registry-recorded bypass. Every other
                    # effect gets exactly one supplier call for this frozen proposal.
                    if hnc_ready and proposal.effect not in {
                        ToolEffect.READ_ONLY.value,
                        ToolEffect.UNKNOWN.value,
                    } and self.authorize_tool_dispatch is not None:
                        try:
                            candidate = self.authorize_tool_dispatch(proposal)
                            if isinstance(candidate, ToolDispatchAuthorization):
                                authorization = candidate
                        except Exception as exc:  # noqa: BLE001 - supplier failure holds
                            logger.warning("tool authorization supplier failed: %s", exc)
                    try:
                        result_str = self.tools.execute(
                            tc.name,
                            tc.arguments,
                            proposal=proposal,
                            authorization=authorization,
                            governance_required=True,
                        )
                    except Exception as exc:  # noqa: BLE001 - never retry ungoverned
                        result_str = json.dumps({
                            "blocked": True,
                            "reason": f"governance: governed registry dispatch failed: {exc}",
                            "tool": tc.name,
                            "proposal_digest": proposal.proposal_digest,
                        })
            else:
                # Compatibility path: existing callers keep the exact two-argument
                # registry API only when governance is explicitly off at both layers.
                result_str = self.tools.execute(tc.name, tc.arguments)

            if self.on_tool_result:
                self.on_tool_result(proposal, authorization, result_str)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tc.id,
                "content": result_str,
            })
        return tool_results

    def turn(self, message: str) -> str:
        """
        Execute a single conversational turn.

        Sends the message, handles any tool calls in an agentic loop,
        and returns the final text response.
        """
        # Add user message
        self._messages.append({"role": "user", "content": message})
        self._history.append(ConversationMessage(role="user", content=message))

        if self.on_message:
            self.on_message("user", message)

        tool_defs = self.tools.list_tools() if self.tools else None

        for _turn_idx in range(self.max_turns):
            self._turn_count += 1

            response = self.adapter.prompt(
                messages=self._messages,
                system=self.system_prompt,
                tools=tool_defs,
                max_tokens=4096,
            )

            # Build assistant content
            if response.has_tool_calls:
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
                self._messages.append({"role": "assistant", "content": content})
            else:
                self._messages.append({"role": "assistant", "content": response.text})

            # No tool calls → final answer
            if not response.has_tool_calls:
                self._history.append(ConversationMessage(
                    role="assistant", content=response.text,
                ))
                if self.on_message:
                    self.on_message("assistant", response.text)
                self._prune_history()
                return response.text

            tool_results = self._dispatch_tool_calls(
                response.tool_calls,
                runner_turn_index=self._turn_count,
                dispatch_mode="turn",
            )

            self._messages.append({"role": "user", "content": tool_results})

        # Max turns hit
        fallback = response.text if response else "Max conversation turns reached."
        self._history.append(ConversationMessage(role="assistant", content=fallback))
        return fallback

    def stream_turn(self, message: str) -> Generator[StreamChunk, None, None]:
        """
        Stream a single turn.  Yields text chunks and tool call events.
        Note: tool dispatch still happens synchronously between stream segments.
        """
        self._messages.append({"role": "user", "content": message})
        tool_defs = self.tools.list_tools() if self.tools else None

        for _turn_idx in range(self.max_turns):
            self._turn_count += 1
            collected_text = ""
            collected_tool_calls = []

            for chunk in self.adapter.stream(
                messages=self._messages,
                system=self.system_prompt,
                tools=tool_defs,
                max_tokens=4096,
            ):
                if chunk.text:
                    collected_text += chunk.text
                    yield chunk

                if chunk.tool_call:
                    collected_tool_calls.append(chunk.tool_call)

                if chunk.done:
                    break

            # If no tool calls → done
            if not collected_tool_calls:
                self._messages.append({"role": "assistant", "content": collected_text})
                yield StreamChunk(done=True, stop_reason="end_turn")
                return

            # Build assistant content with tool calls
            content = []
            if collected_text:
                content.append({"type": "text", "text": collected_text})
            for tc in collected_tool_calls:
                content.append({
                    "type": "tool_use",
                    "id": tc.id,
                    "name": tc.name,
                    "input": tc.arguments,
                })
            self._messages.append({"role": "assistant", "content": content})

            tool_results = self._dispatch_tool_calls(
                collected_tool_calls,
                runner_turn_index=self._turn_count,
                dispatch_mode="stream_turn",
            )
            self._messages.append({"role": "user", "content": tool_results})

        yield StreamChunk(done=True, stop_reason="max_turns")

    def loop(
        self,
        task_fn: Callable[[], str],
        interval: float = 60.0,
        max_iterations: int | None = None,
        on_result: Callable[[str], None] | None = None,
    ):
        """
        Run the agent in a continuous loop.

        Args:
            task_fn: Callable that returns the task/prompt for each iteration
            interval: Seconds between iterations
            max_iterations: Stop after N iterations (None = infinite)
            on_result: Callback with each iteration's result
        """
        self._running = True
        iteration = 0

        try:
            while self._running:
                if max_iterations and iteration >= max_iterations:
                    break

                iteration += 1
                task = task_fn()

                try:
                    result = self.turn(task)
                    if on_result:
                        on_result(result)
                except Exception as e:
                    logger.error("Loop iteration %d failed: %s", iteration, e)
                    if self.on_error:
                        self.on_error(e)

                if self._running and (max_iterations is None or iteration < max_iterations):
                    time.sleep(interval)
        finally:
            self._running = False

    def stop(self):
        """Stop the conversation loop."""
        self._running = False

    def clear_history(self):
        """Clear conversation history."""
        self._messages.clear()
        self._history.clear()
        self._turn_count = 0

    def _prune_history(self):
        """Keep history within max_history limit."""
        if len(self._messages) > self.max_history * 2:
            # Keep system-relevant first message and last N messages
            self._messages = self._messages[:1] + self._messages[-(self.max_history * 2 - 1):]

    def get_history(self) -> List[Dict[str, Any]]:
        """Return conversation history."""
        return [
            {
                "role": m.role,
                "content": m.content if isinstance(m.content, str) else str(m.content),
                "timestamp": m.timestamp,
            }
            for m in self._history
        ]

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "turn_count": self._turn_count,
            "message_count": len(self._messages),
            "history_count": len(self._history),
        }
