"""
Universal Prompt Router — one door, every prompt classified, the complex councilled.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Every prompt that enters Aureon's mind — chat, API, coding, research — passes
through the same Operator/Cognition entry point (the route audit proves there
are no side doors). This module is the classification-and-council stage of
that one door:

* **classify** — the prompt is read against the goal-capability map
  (:func:`aureon.autonomous.aureon_goal_capability_map.recommend_goal_routes`),
  the same descriptive rulebook the autonomous organism uses, so a request is
  named by the capability families it touches (trading, accounting, research,
  contracts, …). An unreachable map is a NAMED blocker, never a guess.
* **council** — a prompt spanning ≥2 capability families is *complex*: a
  temporary, Fleadh-style swarm council convenes — one cluster per family
  (each ≥2 agents; a task is never owned by a single agent), the context
  vector derived deterministically from the prompt itself (hash-seeded, no
  RNG), the Queen gate deciding which family LEADS with measured Γ. The
  council is a coordination instrument over the REAL prompt; it fabricates
  nothing and the whole march is reproducible bit-for-bit.
* **envelope** — the response envelope (sources or "general knowledge, no
  repo hit", coherence, conscience verdict, trace id, ok/honest_unavailable/
  fault status) is enforced on :class:`CognitionResult` in
  ``aureon/operator/schemas.py``; this module supplies the capability and
  council blocks it carries.

Gary Leckey · Aureon Institute
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any, Dict, List

logger = logging.getLogger("aureon.operator.prompt_router")

__all__ = ["COUNCIL_MIN_FAMILIES", "COUNCIL_STEPS", "classify_prompt", "swarm_council"]

#: the two always-recommended low-risk routes — present for EVERY goal, so they
#: carry no classification signal and never count toward complexity
_DEFAULT_ROUTES = frozenset({"memory_and_state", "organism_wiring"})
#: a prompt touching this many specific capability families is complex
COUNCIL_MIN_FAMILIES = 2
#: council ticks — enough for the Γ window to warm and the Queen to gate
COUNCIL_STEPS = 12
_DIM = 8


def classify_prompt(prompt: str) -> Dict[str, Any]:
    """Name the capability families a prompt touches, via the goal-capability map.

    Returns ``{status, families, complex, routes, blockers}``. The two
    always-present low-risk routes are excluded from ``families`` — they are
    recommended for every goal and carry no signal. An unreachable map is an
    honest ``status="unavailable"`` with a named blocker, never a fabricated
    classification.
    """
    try:
        from aureon.autonomous.aureon_goal_capability_map import recommend_goal_routes

        routes = recommend_goal_routes(prompt)
    except Exception as exc:  # noqa: BLE001 — a dark map is a named blocker
        logger.debug("capability map unreachable: %s", exc)
        return {"status": "unavailable", "families": [], "complex": False,
                "routes": [],
                "blockers": [f"goal-capability map unreachable: {exc}"]}
    families = [str(r.get("route")) for r in routes
                if r.get("route") and str(r.get("route")) not in _DEFAULT_ROUTES]
    return {
        "status": "ok",
        "families": families,
        "complex": len(families) >= COUNCIL_MIN_FAMILIES,
        "routes": [{"route": str(r.get("route", "")), "risk": str(r.get("risk", "")),
                    "requires_human": bool(r.get("requires_human", False)),
                    "reason": str(r.get("reason", ""))[:200],
                    "systems": [str(s) for s in list(r.get("systems", []))[:6]]}
                   for r in routes],
        "blockers": [],
    }


def _prompt_context(prompt: str) -> List[float]:
    """Deterministic context vector derived from the REAL prompt — sha256-seeded,
    no RNG, so the same prompt always convenes the same council."""
    from aureon.swarm.agent import _seed_vector

    digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    return _seed_vector(f"prompt:{digest}", _DIM)


def swarm_council(prompt: str, families: List[str]) -> Dict[str, Any] | None:
    """Convene a temporary Fleadh-style council over a complex prompt.

    One cluster per capability family (each ≥2 agents), the shared action set
    is the family list itself (the council decides which family LEADS), and
    the Queen gates each cluster's soft mass with measured Γ. Deterministic:
    same prompt + families → identical march. Any failure returns ``None`` —
    the council advises routing, it must never break answering.
    """
    if len(families) < COUNCIL_MIN_FAMILIES:
        return None
    try:
        from aureon.swarm.agent import SwarmAgent, _seed_vector
        from aureon.swarm.company import Cluster, Company

        fams = sorted(set(families))
        clusters = [
            Cluster(fam, [
                SwarmAgent(f"{fam}:a{i}", fam, list(fams),
                           freq=1.0 + 0.1 * i, phase=0.3 * i)
                for i in range(2)
            ], beta=0.9)
            for fam in fams
        ]
        company = Company(clusters, tau=2, gamma_crit=0.5)
        context = _prompt_context(prompt)
        action_vectors = {fam: _seed_vector(f"family:{fam}", _DIM) for fam in fams}
        for t in range(COUNCIL_STEPS):
            company.step(t, context, action_vectors)

        last = company.ledger[-1]["outcomes"]
        # the lead family: total soft mass across clusters, deterministic tie-break
        total = {fam: sum(out["tick"]["joint_mass"][fam] for out in last.values())
                 for fam in fams}
        lead = min(total, key=lambda fam: (-total[fam], fam))
        report = company.report()
        return {
            "families": fams,
            "steps": report["steps"],
            "clusters": {name: out["tick"]["gamma"] for name, out in last.items()},
            "decisions_total": report["decisions_total"],
            "decisions_actualized": report["decisions_actualized"],
            "lead": lead,
            "boundary": ("a temporary routing council over the real prompt — "
                         "hash-seeded, deterministic, advisory only; it "
                         "fabricates nothing and never blocks answering"),
        }
    except Exception as exc:  # noqa: BLE001 — an advisory council never breaks the answer
        logger.debug("swarm council failed: %s", exc)
        return None
