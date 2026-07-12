#!/usr/bin/env python3
"""
Aureon Cognition — agentic demo (offline, "the local LLM is me").
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Runs a prompt through the full agentic cognition and prints grounding, each tool
call, the conscience verdict, the mycelium broadcast, and the final answer.

With no API key, a DemoAdapter serves real answers authored by the running model
(me) for a set of cross-domain prompts, and emits a genuine repo_search tool call
for in-repo questions — so the whole loop runs end-to-end offline. Add a real key
(OPENAI/XAI/GEMINI) and the identical loop runs against that flagship model.

    python scripts/run_cognition_demo.py "How does Aureon's operator ground its answers?"   # in-repo
    python scripts/run_cognition_demo.py "<any off-repo question>"                          # general knowledge
    python scripts/run_cognition_demo.py "<a boundary-crossing request>"                    # blocked

The exact demo prompts live in data/research/cognition_demo_recordings.json (JSON,
so the repo index never ingests them and off-repo prompts stay honestly ungrounded).
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import json  # noqa: E402

from aureon.inhouse_ai.llm_adapter import LLMAdapter, LLMResponse, StreamChunk, ToolCall  # noqa: E402
from aureon.operator.cognition import AureonCognition  # noqa: E402
from aureon.operator.self_adapter import normalise_prompt  # noqa: E402

# Authored answers (me, acting as the flagship line), loaded from JSON so the
# repo-wide index never ingests them — off-repo prompts stay honestly ungrounded.
_REC_PATH = _REPO / "data" / "research" / "cognition_demo_recordings.json"
_DEMO = json.loads(_REC_PATH.read_text(encoding="utf-8")).get("answers", {})


class DemoAdapter(LLMAdapter):
    """Serves authored answers; emits a real repo_search tool call for in-repo prompts."""

    model = "fable-5-demo"

    def _entry(self, messages):
        for m in messages:
            if m.get("role") == "user" and isinstance(m.get("content"), str):
                key = normalise_prompt(m["content"])
                if key in _DEMO:
                    return key, _DEMO[key]
        return None, None

    @staticmethod
    def _has_tool_result(messages) -> bool:
        for m in messages:
            c = m.get("content")
            if isinstance(c, list) and any(isinstance(b, dict) and b.get("type") == "tool_result" for b in c):
                return True
        return False

    def prompt(self, messages, system="", tools=None, max_tokens=4096, temperature=0.7, **k) -> LLMResponse:
        key, entry = self._entry(messages)
        if entry and entry["in_repo"] and tools and not self._has_tool_result(messages):
            return LLMResponse(text="Grounding first.",
                               tool_calls=[ToolCall(name="repo_search", arguments={"query": key})],
                               stop_reason="tool_use", model=self.model)
        answer = entry["answer"] if entry else (
            "I can help with that. (No authored demo answer for this exact prompt — "
            "with a live model key this runs the real agentic loop.)"
        )
        return LLMResponse(text=answer, stop_reason="end_turn", model=self.model)

    def stream(self, *a, **k):
        yield StreamChunk(done=True)


def _rule(t: str) -> None:
    print(f"\n\033[35m{'─'*3} {t} {'─'*max(0,56-len(t))}\033[0m")


def main(argv) -> int:
    prompt = " ".join(argv[1:]).strip() or "How does Aureon's operator ground its answers?"
    cog = AureonCognition(adapter=DemoAdapter(), join_mesh=True, max_turns=4)

    print("\033[36m🧠 AUREON COGNITION — agentic mode\033[0m")
    print(f"    tools = {', '.join(cog.tools.names())}")
    print(f"    prompt = {prompt!r}")

    res = cog.reason(prompt)

    _rule("GROUND (repo-wide)")
    g = res.grounding
    print(f"grounded={res.grounded}  sources={len(g.sources) if g else 0}")
    for s in (g.sources if g else [])[:4]:
        print(f"  • {s['path']}")
    if not res.grounded:
        print("  (off-repo topic → answered from general knowledge, no citation)")

    _rule("TOOL CALLS")
    if res.tool_calls:
        for t in res.tool_calls:
            print(f"  → {t.tool}({t.arguments})  {'BLOCKED' if t.blocked else 'ok'}")
    else:
        print("  (none)")

    _rule("VETO")
    print(f"verdict={res.conscience_verdict}  blocked={res.blocked}")
    if res.conscience_message:
        print(f"  🦗 {res.conscience_message}")

    _rule("ANSWER")
    print(res.text)

    _rule("TRACE")
    print(f"trace_id={res.trace_id}  turns={res.turns}  elapsed={res.elapsed_ms:.0f}ms  "
          f"(broadcast to mycelium mesh + thought bus)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
