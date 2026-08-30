"""
The Bake Cycle — nothing half-formed leaves the door.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The replicator contract's last clause: any text in, a FULLY BAKED result out —
complete, self-contained, sourced or honestly labeled. This module is the
completeness signal that enforces it: a set of MEASURED, deterministic
heuristics (no model call, no fabrication) that read the draft answer and
name what looks unfinished, so the cognition loop can run exactly one
refinement pass before release — or say honestly that it cannot.

The signal never second-guesses honesty: an ``[ERROR]``/offline reply is an
honest status, not a draft to churn — refining it would add no knowledge and
risk inventing some. Blocked answers are never refined either; the veto is
the final word.

Every check below is a HEURISTIC and says so — it measures surface shape
(emptiness, unclosed code fences, mid-sentence endings, thinness against a
multi-part ask), never semantic truth. The reasons ride the envelope so the
user sees exactly why a second pass ran.

Gary Leckey · Aureon Institute
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

__all__ = ["assess_completeness", "refinement_prompt"]

#: characters an intentionally finished text plausibly ends with
_TERMINALS = ".!?:;)]}\"'`”…。"
#: a prompt with numbered items / several questions is a multi-part ask
_MULTIPART = re.compile(r"(?m)^\s*(?:\d+[.)]|[-*•])\s+\S")


def assess_completeness(prompt: str, text: str) -> Dict[str, Any]:
    """Measured surface-shape heuristics: is this draft plausibly complete?

    Returns ``{complete, reasons}`` — ``reasons`` names every failed check.
    Deterministic, no model call; a clean pass means "no surface signal of
    truncation", never a semantic quality claim.
    """
    reasons: List[str] = []
    t = (text or "").strip()
    if not t:
        reasons.append("empty answer")
        return {"complete": False, "reasons": reasons}

    if t.count("```") % 2 == 1:
        reasons.append("unclosed code fence")

    last = t[-1]
    if last.isalnum() or last in ",-—&":
        reasons.append("ends mid-sentence (no terminal punctuation)")

    multipart = bool(_MULTIPART.search(prompt)) or prompt.count("?") >= 2
    if multipart and len(t) < 80:
        reasons.append("thin relative to a multi-part ask")

    return {"complete": not reasons, "reasons": reasons}


def refinement_prompt(prompt: str, draft: str, reasons: List[str]) -> str:
    """The single bake-again instruction: complete the draft, don't restart."""
    return (
        "Your previous draft answer to the user's request looks incomplete "
        f"({'; '.join(reasons)}).\n\n"
        f"The user's request was:\n{prompt}\n\n"
        f"Your draft was:\n{draft}\n\n"
        "Produce the COMPLETE, self-contained final answer now — finish any "
        "truncated sections, close any open code blocks, and address every "
        "part of the ask. Return the full answer, not a diff."
    )
