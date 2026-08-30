"""
The Acquisition Loop — find what is missing, under control.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The Borg clause of the replicator contract: when the local knowledge (repo
packets + skills + model weights) is not enough to bake the order, the agent
does not stop and it does NOT fill the gap with invention — it goes out
through the guarded tools (repo search, web search/fetch, skills, state
reads), evaluates what it finds, and uses it for THIS task.

This module supplies the two measured pieces of that loop:

* **the gap signal** — deterministic surface checks that name when a draft
  admits insufficiency ("I don't know", "no information", …) or when a
  domain-classified ask was answered with no repo packet and no tool
  consulted. A named gap triggers exactly ONE acquisition pass; no gap, no
  churn.
* **the acquisition instruction** — the single go-find-it turn: use the
  tools to locate the missing knowledge, evaluate it, cite it — and if the
  tools are unavailable (offline, blocked), SAY SO plainly. Never invent.

The outcome is measured, not self-reported: new unblocked tool calls during
the acquisition pass mean knowledge was reached for; blocked network tools
mean the acquisition was honestly unavailable. Both land on the envelope.

Gary Leckey · Aureon Institute
"""

from __future__ import annotations

from typing import Any, Dict, List

__all__ = ["ACQUISITION_MARKERS", "acquisition_outcome", "acquisition_prompt",
           "find_gaps"]

#: draft phrases that ADMIT a knowledge gap — surface heuristics, named as such
ACQUISITION_MARKERS = (
    "i don't know", "i do not know", "i'm not sure", "i am not sure",
    "no information", "cannot find", "can't find", "i don't have",
    "i do not have", "unable to determine", "insufficient information",
)


def find_gaps(prompt: str, res: Any) -> List[str]:
    """Name the measured signals that the local knowledge was not enough.

    Deterministic surface checks only — an admission marker in the draft, or
    a capability-classified ask answered with neither a repo packet nor a
    tool consultation. Never a semantic judgment.
    """
    gaps: List[str] = []
    low = (res.text or "").lower()
    for marker in ACQUISITION_MARKERS:
        if marker in low:
            gaps.append(f'draft admits a gap ("{marker}")')
            break
    cap = res.capability or {}
    if (cap.get("families") and not res.grounded
            and not any(not t.blocked for t in res.tool_calls)):
        gaps.append("capability families named but neither a repo packet nor "
                    "a tool was consulted")
    return gaps


def acquisition_prompt(prompt: str, draft: str, gaps: List[str]) -> str:
    """The single go-find-it instruction: acquire, evaluate, use — or say
    plainly what is missing. Never invent."""
    return (
        "Your draft answer shows a knowledge gap "
        f"({'; '.join(gaps)}).\n\n"
        f"The user's request was:\n{prompt}\n\n"
        f"Your draft was:\n{draft}\n\n"
        "Do NOT fill the gap with invention. Use your tools to FIND the "
        "missing knowledge now: repo_search for anything Aureon-related, "
        "list_skills for validated procedures the organism already knows, "
        "web_search/web_fetch for open-source and internet knowledge, "
        "read_state/read_prices for live trading state. Evaluate what you "
        "find, use it, and cite it in the final answer. If a tool is "
        "unavailable or returns nothing, state plainly what is missing and "
        "what you could not reach — an honest gap beats a confident guess."
    )


def acquisition_outcome(tools_before: int, res: Any) -> Dict[str, Any]:
    """Measured verdict on the acquisition pass: what was actually reached.

    ``acquired``     — at least one NEW unblocked tool call ran;
    ``unavailable``  — new tool calls were attempted but every one was
                       blocked (offline / guarded), named per tool;
    ``declined``     — the model made no new tool call at all.
    """
    new_calls = res.tool_calls[tools_before:]
    ran = [t.tool for t in new_calls if not t.blocked]
    blocked = [t.tool for t in new_calls if t.blocked]
    if ran:
        return {"outcome": "acquired", "tools_consulted": sorted(set(ran)),
                "tools_blocked": sorted(set(blocked))}
    if blocked:
        return {"outcome": "unavailable",
                "tools_consulted": [], "tools_blocked": sorted(set(blocked)),
                "blocker": ("every acquisition tool was blocked "
                            f"({', '.join(sorted(set(blocked)))}) — offline or "
                            "guarded; the gap stays named, never invented")}
    return {"outcome": "declined", "tools_consulted": [], "tools_blocked": [],
            "blocker": "the model made no tool call on the acquisition pass"}
