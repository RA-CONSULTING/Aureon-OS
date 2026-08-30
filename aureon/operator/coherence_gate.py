"""
The Coherence Gate — the living membrane on agent capability.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The hard authority boundary is the OUTER WALL: trade, payment, credentials,
filing, safety-gate bypass refuse early and absolutely. This module is the
INNER MEMBRANE — soft, continuous, and driven by the hive field, not the
individual unit: the live Auris/HNC state (measured Γ, the cosmic advisory,
the lighthouse) decides how far an agent's reach extends THIS turn.

The aperture is not allow/deny — it scales, by NAME:

* ``full``        — the field is clear: all guarded tools, skills, network
* ``reduced``     — coherence is soft: network reach withdrawn, local
                    tools + skills + live state remain
* ``skills_only`` — coherence is low or the advisory is closed: repo
                    reading and skill listing only, nothing that acts
* ``local_only``  — low coherence AND a closed advisory: no tool runs;
                    the agent answers from what it already holds,
                    honestly labeled
* ``refuse``      — every signal is against (Γ below the refuse floor AND
                    the advisory closed AND the lighthouse severe): the
                    turn's expansion is refused outright, with the reasons
                    named on the envelope — never a silent stall

DOCTRINE (the b46 rule, applied to capability): the membrane may only
TIGHTEN on a LIVE field signal. A dark field — no fresh canonical Γ —
restricts nothing and grants nothing new; the hard wall still stands, and
the darkness is recorded on the envelope, never invented around. Individual
agents do not self-authorize; the field decides, and when the field is
silent the aperture simply is not the field's to narrow.

Enforcement sits in the guarded tool registry AFTER the hard boundary:
a tool outside the current aperture is refused with a named coherence-gate
reason, lands on the blocked ledger, parks in the actualization record, and
surfaces in the acquisition outcome — the whole Film-Reel sees the truth.

Gary Leckey · Aureon Institute
"""

from __future__ import annotations

from typing import Any, Dict, Set

__all__ = [
    "APERTURES",
    "EVOLUTION_FLOWS",
    "GAMMA_FULL",
    "GAMMA_REDUCED",
    "GAMMA_REFUSE",
    "compute_aperture",
    "compute_evolution_flow",
    "reach_for",
]

#: aperture levels, widest to narrowest — a level exists by NAME
APERTURES = ("full", "reduced", "skills_only", "local_only", "refuse")
#: Internal self-evolution never has a closed state. Coherence changes pace,
#: patch size, and proof depth while introspection/repair/rollback remain alive.
EVOLUTION_FLOWS = ("expand", "steady", "observe", "repair")
#: Γ at or above this → the field is clear, full reach
GAMMA_FULL = 0.6
#: Γ below this → skills-only reach
GAMMA_REDUCED = 0.3
#: Γ below this, with the advisory closed AND the lighthouse severe → refuse
GAMMA_REFUSE = 0.15
#: lighthouse severities that close the membrane to introspective reach
_SEVERE = {"critical", "emergency", "severe"}

#: what each aperture may touch — ``None`` means unrestricted
_INTROSPECTIVE_TOOLS = frozenset({"repo_search", "read_repo_file",
                                  "list_repo", "list_skills"})
_NETWORK_TOOLS = frozenset({"web_search", "web_fetch"})


def _severe_lighthouse(value: Any) -> bool:
    """Accept both named and numeric Lighthouse severities."""
    if isinstance(value, (int, float)):
        return float(value) >= 0.8
    return str(value or "").lower() in _SEVERE


def compute_aperture(gamma: Any, advisory_open: Any,
                     lighthouse_severity: Any) -> Dict[str, Any]:
    """The membrane's decision for one turn, from the live field state.

    ``gamma`` — the canonical coherence Γ, or ``None`` when the field is
    DARK (no fresh reading). ``advisory_open`` — the cosmic advisory gate
    (``None`` = unknown). ``lighthouse_severity`` — the latest lighthouse
    event severity (``None`` = none). Pure and deterministic.
    """
    if gamma is None:
        return {"aperture": "full", "field_status": "canonical_dark",
                "gamma": None,
                "reasons": ["the field is dark — the membrane only tightens "
                            "on a LIVE signal (tighten-only doctrine); the "
                            "hard boundary still stands"]}

    g = float(gamma)
    reasons = []
    aperture = "full"
    if g < GAMMA_FULL:
        aperture = "reduced"
        reasons.append(f"Γ={g:.3f} < {GAMMA_FULL} — network reach withdrawn")
    if g < GAMMA_REDUCED:
        aperture = "skills_only"
        reasons.append(f"Γ={g:.3f} < {GAMMA_REDUCED} — skills-only reach")
    severe = _severe_lighthouse(lighthouse_severity)
    closed_advisory = advisory_open is False or severe
    if closed_advisory:
        if aperture in ("full", "reduced"):
            aperture = "skills_only"
        reasons.append("the advisory/lighthouse holds the membrane at "
                       f"skills-only reach (advisory_open={advisory_open}, "
                       f"lighthouse={lighthouse_severity})")
    if g < GAMMA_REDUCED and closed_advisory:
        aperture = "local_only"
        reasons.append("low coherence AND a closed advisory — no tool runs; "
                       "the agent answers from what it already holds")
    if g < GAMMA_REFUSE and advisory_open is False and severe:
        aperture = "refuse"
        reasons.append(f"every signal is against (Γ={g:.3f} < {GAMMA_REFUSE}, "
                       "advisory closed, lighthouse severe) — the turn's "
                       "expansion is refused, named, never silent")
    return {"aperture": aperture, "field_status": "live", "gamma": round(g, 6),
            "advisory_open": advisory_open,
            "lighthouse": lighthouse_severity,
            "reasons": reasons or [f"Γ={g:.3f} — the field is clear, full reach"]}


def compute_evolution_flow(
    gamma: Any,
    advisory_open: Any,
    lighthouse_severity: Any,
    *,
    auris_confidence: Any = None,
    beta: Any = None,
) -> Dict[str, Any]:
    """Translate HNC/Auris state into a non-blocking self-evolution rhythm.

    This is the organism-facing counterpart to :func:`compute_aperture`.
    External actions still meet the outer authority wall, but no field state
    can remove the internal abilities to observe, reason, propose a patch,
    validate it, roll it back, and try again. Lower coherence narrows the
    batch and strengthens proof instead of creating a dead end.
    """

    def number(value: Any) -> float | None:
        try:
            return None if value is None else float(value)
        except (TypeError, ValueError):
            return None

    g = number(gamma)
    auris = number(auris_confidence)
    beta_value = number(beta)
    severe = _severe_lighthouse(lighthouse_severity)
    closed_advisory = advisory_open is False or severe
    reasons: list[str] = []

    if g is None:
        flow = "observe"
        field_status = "canonical_dark"
        reasons.append(
            "the canonical field is dark; keep introspection and repair alive "
            "while gathering a fresh HNC/Auris reading"
        )
    else:
        g = max(0.0, min(1.0, g))
        field_status = "live"
        if g >= GAMMA_FULL and not closed_advisory and (auris is None or auris >= GAMMA_FULL):
            flow = "expand"
            reasons.append(f"gamma={g:.3f} supports a wider validated change batch")
        elif g >= GAMMA_REDUCED and not severe:
            flow = "steady"
            reasons.append(f"gamma={g:.3f} calls for a measured change batch")
        else:
            flow = "repair"
            reasons.append(f"gamma={g:.3f} turns the cycle toward diagnosis and repair")

    if auris is not None:
        auris = max(0.0, min(1.0, auris))
        if auris < GAMMA_REDUCED and flow != "repair":
            flow = "repair"
            reasons.append(f"Auris confidence={auris:.3f} deepens proof and narrows the batch")
        elif auris < GAMMA_FULL and flow == "expand":
            flow = "steady"
            reasons.append(f"Auris confidence={auris:.3f} tempers expansion")

    if closed_advisory and flow != "repair":
        flow = "repair"
        reasons.append(
            "the Auris advisory/Lighthouse signal redirects expansion into repair; "
            "internal reasoning remains open"
        )

    if beta_value is not None and not 0.6 <= beta_value <= 1.1:
        flow = "repair"
        reasons.append(
            f"HNC beta={beta_value:.3f} is outside the documented 0.6-1.1 stability regime"
        )

    profiles = {
        "expand": {
            "patch_batch_limit": 3,
            "required_test_layers": ["focused", "integration", "regression"],
            "minimum_review_cycles": 1,
        },
        "steady": {
            "patch_batch_limit": 2,
            "required_test_layers": ["focused", "integration", "regression"],
            "minimum_review_cycles": 1,
        },
        "observe": {
            "patch_batch_limit": 1,
            "required_test_layers": ["focused", "integration", "regression"],
            "minimum_review_cycles": 2,
        },
        "repair": {
            "patch_batch_limit": 1,
            "required_test_layers": ["focused", "integration", "regression", "rollback"],
            "minimum_review_cycles": 2,
        },
    }
    return {
        "flow": flow,
        "field_status": field_status,
        "gamma": None if g is None else round(g, 6),
        "auris_confidence": None if auris is None else round(auris, 6),
        "beta": beta_value,
        "advisory_open": advisory_open,
        "lighthouse": lighthouse_severity,
        "reasons": reasons,
        "capabilities": {
            "observe": True,
            "reason": True,
            "use_native_aureon_systems": True,
            "use_external_llm": True,
            "propose_patch": True,
            "validate": True,
            "rollback": True,
            "retry": True,
        },
        "outer_authority_boundary_preserved": True,
        **profiles[flow],
    }


def reach_for(aperture: str, all_tools: Set[str]) -> Set[str] | None:
    """The tool names the aperture admits — ``None`` means unrestricted."""
    if aperture == "full":
        return None
    if aperture == "reduced":
        return set(all_tools) - set(_NETWORK_TOOLS)
    if aperture == "skills_only":
        return set(all_tools) & set(_INTROSPECTIVE_TOOLS)
    if aperture in ("local_only", "refuse"):
        return set()
    raise ValueError(f"unknown aperture '{aperture}' — apertures exist by "
                     f"name: {', '.join(APERTURES)}")
