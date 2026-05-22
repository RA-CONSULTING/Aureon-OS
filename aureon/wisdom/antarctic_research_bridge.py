#!/usr/bin/env python3
"""
Antarctic research bridge for Seer and Lyra.

The local "Antarctic research" bundle contains the Harmonic Nexus Core
research maps: phi-graded sphere, rune meridian, 13-sign zodiac, Samhain
anchor, Ogham/Futhork wheels, chamber-wall projection, and visual evidence.

This module turns that research into a small, deterministic context packet
that Seer and Lyra can attach to their summaries.  It is context and
coherence evidence only; it never places orders and never overrides trading,
risk, lifecycle, or broker gates.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

PHI = (1.0 + math.sqrt(5.0)) / 2.0
GOLDEN_ANGLE_DEG = 360.0 / (PHI ** 2)
SAMHAIN_MONTH = 11
SAMHAIN_DAY = 1

YOUNGER_FUTHORK: List[Dict[str, str]] = [
    {"name": "Fe", "meaning": "wealth, movable value", "bias": "BUY_BIAS"},
    {"name": "Ur", "meaning": "strength, raw force", "bias": "BUY_BIAS"},
    {"name": "Thurs", "meaning": "disruption, resistance", "bias": "DEFEND"},
    {"name": "Oss", "meaning": "signal, breath, speech", "bias": "HOLD"},
    {"name": "Reid", "meaning": "road, motion, routing", "bias": "BUY_BIAS"},
    {"name": "Kaun", "meaning": "torch, exposure, reveal", "bias": "HOLD"},
    {"name": "Hagall", "meaning": "shock, hail, disorder", "bias": "DEFEND"},
    {"name": "Naud", "meaning": "constraint, pressure", "bias": "DEFEND"},
    {"name": "Is", "meaning": "ice, stillness, hold", "bias": "HOLD"},
    {"name": "Ar", "meaning": "harvest, timing", "bias": "BUY_BIAS"},
    {"name": "Sol", "meaning": "sun, visibility", "bias": "BUY_BIAS"},
    {"name": "Tyr", "meaning": "justice, directional courage", "bias": "BUY_BIAS"},
    {"name": "Bjarkan", "meaning": "growth, renewal", "bias": "BUY_BIAS"},
    {"name": "Madr", "meaning": "human pattern, consensus", "bias": "HOLD"},
    {"name": "Logr", "meaning": "water, liquidity, flow", "bias": "HOLD"},
    {"name": "Yr", "meaning": "bow, caution, reversal risk", "bias": "DEFEND"},
]

OGHAM_WHEEL: List[Dict[str, str]] = [
    {"name": "Beith", "tree": "Birch"},
    {"name": "Luis", "tree": "Rowan"},
    {"name": "Fearn", "tree": "Alder"},
    {"name": "Sail", "tree": "Willow"},
    {"name": "Nion", "tree": "Ash"},
    {"name": "Huath", "tree": "Hawthorn"},
    {"name": "Duir", "tree": "Oak"},
    {"name": "Tinne", "tree": "Holly"},
    {"name": "Coll", "tree": "Hazel"},
    {"name": "Quert", "tree": "Apple"},
    {"name": "Muin", "tree": "Vine"},
    {"name": "Gort", "tree": "Ivy"},
    {"name": "Ngetal", "tree": "Reed"},
    {"name": "Straif", "tree": "Blackthorn"},
    {"name": "Ruis", "tree": "Elder"},
    {"name": "Ailm", "tree": "Pine"},
    {"name": "Onn", "tree": "Gorse"},
    {"name": "Ur", "tree": "Heather"},
    {"name": "Eadhadh", "tree": "Aspen"},
    {"name": "Iodhadh", "tree": "Yew"},
    {"name": "Eabhadh", "tree": "Grove"},
    {"name": "Oir", "tree": "Spindle"},
    {"name": "Uilleann", "tree": "Honeysuckle"},
    {"name": "Ifin", "tree": "Gooseberry"},
    {"name": "Eamhancholl", "tree": "Twin hazel"},
]

# Approximate 13-sign ecliptic crossing windows, including Ophiuchus.
ZODIAC_13 = [
    ("Capricorn", (1, 20), (2, 16)),
    ("Aquarius", (2, 16), (3, 11)),
    ("Pisces", (3, 11), (4, 18)),
    ("Aries", (4, 18), (5, 13)),
    ("Taurus", (5, 13), (6, 21)),
    ("Gemini", (6, 21), (7, 20)),
    ("Cancer", (7, 20), (8, 10)),
    ("Leo", (8, 10), (9, 16)),
    ("Virgo", (9, 16), (10, 30)),
    ("Libra", (10, 30), (11, 23)),
    ("Scorpio", (11, 23), (11, 29)),
    ("Ophiuchus", (11, 29), (12, 17)),
    ("Sagittarius", (12, 17), (1, 20)),
]

CHAMBER_WALLS = [
    ("NE", 45.0, "shadow wall / arrival"),
    ("SE", 135.0, "phi-squared diagonal"),
    ("SW", 225.0, "source / seed bank"),
    ("NW", 315.0, "threshold / treasure pointer"),
]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _research_root(root: Optional[Path] = None) -> Path:
    base = (root or _repo_root()).resolve()
    return base / "Antarctic research"


def _days_since_samhain(at: datetime) -> float:
    anchor = datetime(at.year, SAMHAIN_MONTH, SAMHAIN_DAY, tzinfo=timezone.utc)
    if at < anchor:
        anchor = datetime(at.year - 1, SAMHAIN_MONTH, SAMHAIN_DAY, tzinfo=timezone.utc)
    return (at - anchor).total_seconds() / 86400.0


def _date_in_range(at: datetime, start: tuple[int, int], end: tuple[int, int]) -> bool:
    md = (at.month, at.day)
    if start <= end:
        return start <= md < end
    return md >= start or md < end


def _zodiac_sign(at: datetime) -> str:
    for name, start, end in ZODIAC_13:
        if _date_in_range(at, start, end):
            return name
    return "Unknown"


def _nearest_wall(angle: float) -> Dict[str, Any]:
    def distance(target: float) -> float:
        diff = abs((angle - target + 180.0) % 360.0 - 180.0)
        return diff

    name, bearing, role = min(CHAMBER_WALLS, key=lambda row: distance(row[1]))
    return {
        "wall": name,
        "bearing_deg": bearing,
        "role": role,
        "offset_deg": round(distance(bearing), 3),
    }


def _wheel_position(angle: float, items: List[Dict[str, str]]) -> Dict[str, Any]:
    sector = 360.0 / len(items)
    index = int(angle // sector) % len(items)
    item = dict(items[index])
    item.update({
        "index": index,
        "sector_size_deg": round(sector, 4),
        "sector_angle_deg": round(index * sector, 4),
    })
    return item


def _manifest(root: Optional[Path] = None) -> Dict[str, Any]:
    rr = _research_root(root)
    extracted = rr / "_extracted" / "pattern_report" / "word" / "media"
    media = []
    if extracted.exists():
        media = [str(p.relative_to(_repo_root())) for p in sorted(extracted.glob("*")) if p.is_file()]
    source_names = [
        "Pattern_Recognition_Archaeology_Report_v1.docx",
        "HNC_White_Paper_v3.docx",
        "HNC_White_Paper_v3-1.pdf",
        "HNC_Empirical_Audit_v3-1.pptx",
        "HNC_Empirical_Audit_v3-1.pdf",
        "aureon_poster-1.html",
        "aureon_poster-2.html",
        "aureon_poster-3.html",
        "antarctic_true_shape_replay_report.md",
    ]
    sources = []
    for name in source_names:
        path = rr / name
        sources.append({
            "name": name,
            "path": str(path.relative_to(_repo_root())) if path.exists() else str(path),
            "present": path.exists(),
        })
    return {
        "research_root": str(rr.relative_to(_repo_root())) if rr.exists() else str(rr),
        "source_count": sum(1 for s in sources if s["present"]),
        "sources": sources,
        "visual_media": media,
    }


def build_research_context(at: Optional[datetime] = None, *, root: Optional[Path] = None) -> Dict[str, Any]:
    """Build the shared Seer/Lyra map packet."""
    if at is None:
        at = datetime.now(timezone.utc)
    elif at.tzinfo is None:
        at = at.replace(tzinfo=timezone.utc)
    at = at.astimezone(timezone.utc)

    days = _days_since_samhain(at)
    seasonal_angle = (days / 365.2425 * 360.0) % 360.0
    futhork = _wheel_position(seasonal_angle, YOUNGER_FUTHORK)
    ogham = _wheel_position(seasonal_angle, OGHAM_WHEEL)
    zodiac = _zodiac_sign(at)
    wall = _nearest_wall(seasonal_angle)

    # How close the seasonal angle is to a golden-angle phyllotaxis step.
    phi_step = round(seasonal_angle / GOLDEN_ANGLE_DEG)
    phi_target = (phi_step * GOLDEN_ANGLE_DEG) % 360.0
    phi_error = abs((seasonal_angle - phi_target + 180.0) % 360.0 - 180.0)
    phi_alignment = max(0.0, 1.0 - min(phi_error / (GOLDEN_ANGLE_DEG / 2.0), 1.0))

    bias = futhork.get("bias", "HOLD")
    if bias == "BUY_BIAS":
        modifier = 1.0 + 0.04 * phi_alignment
    elif bias == "DEFEND":
        modifier = 1.0 - 0.05 * max(0.25, phi_alignment)
    else:
        modifier = 0.98 + 0.03 * phi_alignment

    score = 0.50 + 0.20 * phi_alignment
    if zodiac == "Ophiuchus":
        score += 0.04
    score = max(0.0, min(1.0, score))

    shared = {
        "generated_at": at.isoformat(),
        "research_key": "seer_reads_stars_lyra_reads_emotions",
        "execution_command": "none",
        "influence": "context_modifier_only",
        "seasonal_angle_deg": round(seasonal_angle, 4),
        "samhain_anchor": f"{SAMHAIN_MONTH:02d}-{SAMHAIN_DAY:02d}",
        "golden_angle_deg": round(GOLDEN_ANGLE_DEG, 6),
        "phi_alignment": round(phi_alignment, 4),
        "phi_target_angle_deg": round(phi_target, 4),
        "phi_error_deg": round(phi_error, 4),
        "zodiac_13_sign": zodiac,
        "younger_futhork": futhork,
        "ogham": ogham,
        "chamber_wall": wall,
        "source_manifest": _manifest(root),
    }

    seer = {
        "role": "seer_reads_stars",
        "map": "phi_graded_sphere_rune_meridian_13_sign_zodiac",
        "score": round(score, 4),
        "confidence_modifier": round(modifier, 4),
        "action_bias": bias,
        "dominant_rune": futhork["name"],
        "dominant_ogham": ogham["name"],
        "zodiac_13_sign": zodiac,
        "wall": wall["wall"],
        "logic": [
            "Read the star/rune geometry as timing and coherence context.",
            "Fold rune and Ogham wheels from the Samhain anchor.",
            "Use Ophiuchus and the phi-graded sphere as research context, not standalone trade proof.",
        ],
    }

    lyra = {
        "role": "lyra_reads_emotions",
        "map": "emotion_frequency_folded_onto_phi_rune_lattice",
        "score": round(max(0.0, min(1.0, 0.48 + 0.22 * phi_alignment)), 4),
        "confidence_modifier": round(0.99 + 0.02 * phi_alignment, 4),
        "dominant_rune_emotion": futhork["meaning"],
        "dominant_ogham_emotion": ogham["tree"],
        "emotional_instruction": _emotion_instruction(bias),
        "logic": [
            "Feel market emotion through shadow, balance, and prime frequency zones.",
            "Use rune meaning as an emotional texture for caution, expansion, or holding.",
            "Let emotional resonance alter confidence only inside existing risk gates.",
        ],
    }

    return {
        "schema_version": "aureon-antarctic-research-seer-lyra-bridge-v1",
        "status": "research_bridge_ready",
        "shared_map": shared,
        "seer": seer,
        "lyra": lyra,
    }


def _emotion_instruction(bias: str) -> str:
    if bias == "BUY_BIAS":
        return "expansion_allowed_only_if_market_emotion_and_live_gates_confirm"
    if bias == "DEFEND":
        return "protect_capital_and_lower_confidence_until_signal_quality_improves"
    return "hold_emotional_balance_until_price_and_lifecycle_proof_agree"


def apply_to_seer_summary(summary: Dict[str, Any], *, root: Optional[Path] = None) -> Dict[str, Any]:
    """Attach the Antarctic research star map to a Seer summary."""
    if not isinstance(summary, dict):
        return summary
    out = dict(summary)
    ctx = build_research_context(root=root)
    out["antarctic_research"] = {
        "shared_map": ctx["shared_map"],
        "seer": ctx["seer"],
    }
    out["research_context_score"] = ctx["seer"]["score"]
    out["research_context_modifier"] = ctx["seer"]["confidence_modifier"]
    return out


def apply_to_lyra_summary(summary: Dict[str, Any], *, root: Optional[Path] = None) -> Dict[str, Any]:
    """Attach the Antarctic research emotion map to a Lyra summary."""
    if not isinstance(summary, dict):
        return summary
    out = dict(summary)
    ctx = build_research_context(root=root)
    lyra = dict(ctx["lyra"])
    freq = summary.get("emotional_frequency")
    zone = summary.get("emotional_zone")
    if freq is not None:
        lyra["current_emotional_frequency"] = freq
    if zone:
        lyra["current_emotional_zone"] = zone
    out["antarctic_research"] = {
        "shared_map": ctx["shared_map"],
        "lyra": lyra,
    }
    out["research_context_score"] = lyra["score"]
    out["research_context_modifier"] = lyra["confidence_modifier"]
    return out
