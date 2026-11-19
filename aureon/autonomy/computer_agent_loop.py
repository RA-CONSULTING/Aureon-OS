"""Observe, ask for one OpenAI-style tool call, act, repeat.

The model sees a fresh screenshot, then either returns tool_calls or final
text. Each tool call is executed on ``ComputerUse`` and the result is appended
to the dialogue. The human stop file is checked before the screenshot and
again before every tool call.
"""

from __future__ import annotations

import json
from typing import Any, Mapping

from aureon.autonomy.computer_use import ComputerUse, computer_use_stop_file_active, openai_computer_tools


class ComputerAgentLoop:
    def __init__(self, computer: ComputerUse, adapter: Any, *, max_steps: int = 8) -> None:
        if max_steps < 1:
            raise ValueError("max_steps_invalid")
        self.computer = computer
        self.adapter = adapter
        self.max_steps = int(max_steps)
        self.tools = openai_computer_tools()

    def run(self, goal: str) -> dict[str, Any]:
        messages: list[dict[str, Any]] = [{"role": "user", "content": str(goal or "")}]
        steps: list[dict[str, Any]] = []
        final_text = ""
        for _step in range(self.max_steps):
            if computer_use_stop_file_active(self.computer.stop_path):
                receipt = self.computer._finish(
                    "loop",
                    {"goal": goal},
                    ok=False,
                    status="stopped",
                    error="computer_use_stop_file",
                )
                steps.append({"action": "loop", "result": receipt})
                return {"ok": False, "stopped": True, "text": "", "steps": steps, "max_steps": False}
            shot = self.computer.screenshot()
            steps.append({"action": "screenshot", "result": shot})
            if shot.get("status") == "stopped":
                return {"ok": False, "stopped": True, "text": "", "steps": steps, "max_steps": False}
            messages.append({"role": "user", "content": json.dumps({"screenshot": shot}, default=str)})
            response = self.adapter.prompt(messages, tools=self.tools)
            tool_calls = list(getattr(response, "tool_calls", None) or [])
            final_text = str(getattr(response, "text", "") or "")
            if not tool_calls:
                return {"ok": True, "stopped": False, "text": final_text, "steps": steps, "max_steps": False}
            messages.append(_assistant_tool_message(final_text, tool_calls))
            for call in tool_calls:
                name = str(getattr(call, "name", "") or "")
                arguments = getattr(call, "arguments", None) or {}
                if not isinstance(arguments, Mapping):
                    arguments = {}
                if computer_use_stop_file_active(self.computer.stop_path):
                    result = self.computer._finish(
                        name or "tool",
                        dict(arguments),
                        ok=False,
                        status="stopped",
                        error="computer_use_stop_file",
                    )
                    steps.append({"action": name, "result": result})
                    messages.append(_tool_result_message(call, result))
                    return {"ok": False, "stopped": True, "text": "", "steps": steps, "max_steps": False}
                result = self.computer.dispatch(name, arguments)
                steps.append({"action": name, "result": result})
                messages.append(_tool_result_message(call, result))
        return {"ok": False, "stopped": False, "text": final_text, "steps": steps, "max_steps": True}


def _assistant_tool_message(text: str, tool_calls: list[Any]) -> dict[str, Any]:
    encoded = []
    for call in tool_calls:
        arguments = getattr(call, "arguments", None) or {}
        encoded.append(
            {
                "id": str(getattr(call, "id", "") or ""),
                "type": "function",
                "function": {
                    "name": str(getattr(call, "name", "") or ""),
                    "arguments": json.dumps(arguments, default=str),
                },
            }
        )
    return {"role": "assistant", "content": text, "tool_calls": encoded}


def _tool_result_message(call: Any, result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "role": "tool",
        "tool_call_id": str(getattr(call, "id", "") or ""),
        "content": json.dumps(dict(result), default=str),
    }
