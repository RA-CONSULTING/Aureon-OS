"""End-to-end tool loop: model asks for ``execute_shell``, the command really runs.

The only test double here is the language model (``_ScriptedShellModel``): on
its first call it asks for one ``execute_shell`` call, on its second it
returns final text. The runner, the registry, the operator toolbelt and the
subprocess are all real, and the evidence is a marker file written to
``tmp_path`` by the child process.

These are pinning tests. On main at the time of writing they pass, because
``AgentRunner`` + ``execute_shell`` already work when governance and HNC
coherence are explicitly off. They fail if the handler is replaced by a
HOLD / no-op. The governed case pins that, without an authorization, the same
call is held and nothing is written.
"""

from __future__ import annotations

import json
import shlex
import sys
from typing import Any, Dict, Generator, List

from aureon.inhouse_ai.agent_runner import AgentRunner
from aureon.inhouse_ai.llm_adapter import LLMAdapter, LLMResponse, StreamChunk, ToolCall
from aureon.inhouse_ai.tool_registry import ToolRegistry
from aureon.operator.tools import build_operator_tools

MARKER_TEXT = "aureon-loop-ok"
FINAL_TEXT = "shell step finished"


def _write_marker_command(path) -> str:
    # Inline ``python -c`` is refused. The child is a script file, and the
    # assertions below still require that process to write the marker.
    script_path = path.parent / "write_marker.py"
    script_path.write_text(
        "import pathlib, sys\n"
        "pathlib.Path(sys.argv[1]).write_text(sys.argv[2])\n"
        "print(sys.argv[2])\n",
        encoding="utf-8",
    )
    return " ".join([
        shlex.quote(sys.executable),
        shlex.quote(str(script_path)),
        shlex.quote(str(path)),
        shlex.quote(MARKER_TEXT),
    ])


class _ScriptedShellModel(LLMAdapter):
    """Test double for the LLM only: one execute_shell call, then final text."""

    def __init__(self, command: str) -> None:
        self.command = command
        self.calls: List[Dict[str, Any]] = []

    def prompt(self, messages, system="", tools=None, max_tokens=4096, **kwargs) -> LLMResponse:
        self.calls.append({"messages": json.loads(json.dumps(messages, default=str)), "tools": tools})
        if len(self.calls) == 1:
            return LLMResponse(
                text="",
                tool_calls=[ToolCall(id="call-shell-1", name="execute_shell",
                                     arguments={"command": self.command})],
                stop_reason="tool_use",
                model="scripted-test-double",
            )
        return LLMResponse(text=FINAL_TEXT, stop_reason="end_turn", model="scripted-test-double")

    def stream(self, messages, system="", tools=None, max_tokens=4096, **kwargs) -> Generator[StreamChunk, None, None]:
        resp = self.prompt(messages, system=system, tools=tools, max_tokens=max_tokens)
        if resp.text:
            yield StreamChunk(text=resp.text)
        for tc in resp.tool_calls:
            yield StreamChunk(tool_call=tc)
        yield StreamChunk(done=True, stop_reason=resp.stop_reason)


def _tool_result_in_transcript(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    for msg in messages:
        content = msg.get("content")
        if msg.get("role") == "user" and isinstance(content, list):
            for block in content:
                if block.get("type") == "tool_result" and block.get("tool_use_id") == "call-shell-1":
                    return json.loads(block["content"])
    raise AssertionError(f"no execute_shell tool_result in transcript: {messages}")


def _run(registry, tmp_path, *, stream: bool = False):
    marker = tmp_path / "marker.txt"
    model = _ScriptedShellModel(_write_marker_command(marker))
    runner = AgentRunner(model, registry, system_prompt="test", max_turns=4)
    if stream:
        text = "".join(c.text for c in runner.stream_turn("run the shell step"))
    else:
        text = runner.turn("run the shell step")
    return marker, model, runner, text


def _assert_executed(marker, model, runner, text):
    assert text == FINAL_TEXT
    assert len(model.calls) == 2
    assert marker.read_text() == MARKER_TEXT
    result = _tool_result_in_transcript(runner._messages)
    assert result.get("returncode") == 0, result
    assert MARKER_TEXT in result.get("stdout", ""), result
    # The second model call saw the real tool output.
    assert MARKER_TEXT in json.dumps(model.calls[1]["messages"])


def test_agent_runner_builtin_registry_runs_shell_end_to_end(tmp_path):
    reg = ToolRegistry(include_builtins=True, hnc_coherence_required=False)
    _assert_executed(*_run(reg, tmp_path))


def test_agent_runner_operator_toolbelt_runs_shell_end_to_end(tmp_path):
    reg = build_operator_tools(allow_writes=False, allow_shell=True, hnc_coherence_required=False)
    marker, model, runner, text = _run(reg, tmp_path)
    _assert_executed(marker, model, runner, text)
    # execute_shell was offered to the model in the tool list.
    assert "execute_shell" in {t["name"] for t in model.calls[0]["tools"]}


def test_agent_runner_stream_turn_runs_shell_end_to_end(tmp_path):
    reg = ToolRegistry(include_builtins=True, hnc_coherence_required=False)
    _assert_executed(*_run(reg, tmp_path, stream=True))


def test_governed_toolbelt_without_authorization_holds_and_writes_nothing(tmp_path):
    # Default operator toolbelt: HNC coherence required, no verifier, no context.
    reg = build_operator_tools(allow_writes=False, allow_shell=True)
    marker, model, runner, text = _run(reg, tmp_path)
    assert text == FINAL_TEXT
    assert not marker.exists()
    result = _tool_result_in_transcript(runner._messages)
    assert result.get("blocked") is True, result
    assert "returncode" not in result
