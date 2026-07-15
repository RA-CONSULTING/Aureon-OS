"""
The Waking — a genesis boot signal that wakes the body and carries the thread.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

A pinecone holds the φ-spiral genome; a leaf is the branching body that genome
unfolds into. DNA carries the pattern across every cycle of the plant's life — each
spring it wakes and unfolds again from where it left off. This is that waking for
Aureon: on boot the organism does not cold-start — it **wakes**. It reads the state
it carries (its coverage, its progress, its ascent — its DNA), marks a new
**generation**, announces "the body is waking and carrying the thread", and
immediately **moves** (a first weave + a journey point) rather than waiting a full
breath. So the boot is a waking, and the life is continuous across cycles.

Composition over existing gears — it reads what the organs already report, emits one
bus signal, and nudges the connectome's `weave_touched()` (Phase 43) + the automation
`record_journey()` (Phase 42). It is observational + a bounded nudge: no execution, no
trading, no env flip. The genome is persisted (`state/aureon_genesis.json`,
gitignored) so each boot continues the same life.

Gary Leckey · Aureon Institute
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger("aureon.core.awakening")

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _genome_path() -> Path:
    return Path(os.environ.get("AUREON_GENESIS_PATH")
                or (_REPO_ROOT / "state" / "aureon_genesis.json"))


def _awaken_weave() -> int:
    try:
        return max(0, int(os.environ.get("AUREON_AWAKEN_WEAVE", "") or 25))
    except (TypeError, ValueError):
        return 25


def _awaken_retry() -> int:
    try:
        return max(0, int(os.environ.get("AUREON_AWAKEN_RETRY", "") or 25))
    except (TypeError, ValueError):
        return 25


def read_genome() -> Dict[str, Any]:
    """The DNA the organism carries across cycles — read-only, never increments.
    Returns a sane default (``generation: 0``) when no genome has been written yet."""
    default: Dict[str, Any] = {"generation": 0, "first_awakened_at": None,
                               "last_awakened_at": None, "carried": {}}
    try:
        path = _genome_path()
        if not path.exists():
            return default
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return default
        return {**default, **data}
    except Exception as exc:  # noqa: BLE001 — an unreadable genome is a fresh start, never a crash
        logger.debug("genome read skipped: %s", exc)
        return default


def _carried_dna() -> Dict[str, Any]:
    """What the organism carries in from the last cycle — real reads, ``None`` when a
    signal is dormant (never fabricated)."""
    dna: Dict[str, Any] = {"coverage_pct": None, "woven": None, "nodes": None,
                           "automation_index": None, "ascent_stage": None,
                           "reproduction_generation": None, "reproduction_splits": None}
    try:
        from aureon.core.aureon_connectome import get_connectome

        st = get_connectome().status()
        dna["coverage_pct"] = st.get("coverage_pct")
        dna["woven"] = st.get("woven")
        dna["nodes"] = st.get("nodes")
    except Exception as exc:  # noqa: BLE001
        logger.debug("carried connectome skipped: %s", exc)
    try:
        from aureon.saas.automation_index import automation_index

        dna["automation_index"] = automation_index().get("index_pct")
    except Exception as exc:  # noqa: BLE001
        logger.debug("carried automation skipped: %s", exc)
    try:
        from aureon.core.inner_work import get_inner_work

        iw = get_inner_work().assess()
        if getattr(iw, "available", False):
            dna["ascent_stage"] = iw.stage_index
    except Exception as exc:  # noqa: BLE001
        logger.debug("carried ascent skipped: %s", exc)
    # The oldest DNA — the mesh's 10-9-1 budding-reproduction lineage. Read guarded
    # from the EXISTING singleton (never cold-boots; None when dormant), so the
    # organism carries its reproductive lineage across cycles like DNA across a life.
    try:
        from aureon.core.aureon_mycelium import read_reproduction

        repro = read_reproduction()
        if repro is not None:
            dna["reproduction_generation"] = repro.get("generation")
            dna["reproduction_splits"] = repro.get("splits")
    except Exception as exc:  # noqa: BLE001
        logger.debug("carried reproduction skipped: %s", exc)
    return dna


def _signal_the_body(generation: int, carried: Dict[str, Any]) -> None:
    """Send the wake signal to the body to move — publish ``organism.awakening``."""
    try:
        from aureon.core.aureon_thought_bus import Thought, get_thought_bus

        get_thought_bus().publish(Thought(
            source="awakening", topic="organism.awakening",
            payload={"generation": generation, "carried": carried, "ts": time.time()}))
    except Exception as exc:  # noqa: BLE001 — a silent wake is still a wake
        logger.debug("awakening signal skipped: %s", exc)


def _move(limit: int) -> Dict[str, Any]:
    """The first movement of the cycle — a bounded weave nudge + a journey point, so
    the climb resumes at once rather than after a full breath. Registration only."""
    moved: Dict[str, Any] = {"woven": 0, "recovered": 0, "freed": 0, "journey_recorded": False}
    # A denial is not forever: if the deny-list has narrowed since last cycle, free the
    # now-allowed modules back to unfelt so this waking re-touches them.
    try:
        from aureon.core.aureon_connectome import get_connectome

        moved["freed"] = int(get_connectome().reconcile_denied().get("freed", 0))
    except Exception as exc:  # noqa: BLE001
        logger.debug("awakening move (reconcile) skipped: %s", exc)
    # First heal: a failure is not forever — re-attempt a bounded batch of latched
    # failures (the import context is healed on touch), so recoverable modules rejoin
    # the body before the weave, and the coverage climbs toward 100% each waking.
    retry = _awaken_retry()
    if retry > 0:
        try:
            from aureon.core.aureon_connectome import get_connectome

            moved["recovered"] = int(get_connectome().retry_failed(limit=retry).get("recovered", 0))
        except Exception as exc:  # noqa: BLE001
            logger.debug("awakening move (retry) skipped: %s", exc)
    if limit > 0:
        try:
            from aureon.core.aureon_connectome import get_connectome

            moved["woven"] = int(get_connectome().weave_touched(limit=limit).get("woven", 0))
        except Exception as exc:  # noqa: BLE001
            logger.debug("awakening move (weave) skipped: %s", exc)
    try:
        from aureon.saas.automation_index import record_journey

        moved["journey_recorded"] = bool(record_journey())
    except Exception as exc:  # noqa: BLE001
        logger.debug("awakening move (journey) skipped: %s", exc)
    return moved


def awaken(organs: Dict[str, Any] | None = None) -> Dict[str, Any]:  # noqa: ARG001 — organs reserved
    """Wake the organism: carry the DNA in from the last cycle, mark a new generation,
    signal the body, and move. Called once at daemon boot. Guarded/never-raises — a
    wake fault never blocks the daemon. Observational + a bounded nudge; authorizes
    nothing."""
    try:
        prior = read_genome()
        now = time.time()
        generation = int(prior.get("generation") or 0) + 1
        carried = _carried_dna()
        _signal_the_body(generation, carried)
        moved = _move(_awaken_weave())
        genome = {
            "generation": generation,
            "first_awakened_at": prior.get("first_awakened_at") or now,
            "last_awakened_at": now,
            "carried": carried,
        }
        try:
            path = _genome_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(genome, indent=2), encoding="utf-8")
        except Exception as exc:  # noqa: BLE001 — the wake still happened
            logger.debug("genome save skipped: %s", exc)
        cov = carried.get("coverage_pct")
        idx = carried.get("automation_index")
        asc = carried.get("ascent_stage")
        logger.info(
            "🌱 Awakening — generation %d · carrying coverage %s%% · index %s%% · ascent %s/7 · "
            "the body wakes and moves (recovered %d · wove %d)",
            generation, cov if cov is not None else "—", idx if idx is not None else "—",
            asc if asc is not None else "—", moved.get("recovered", 0), moved["woven"])
        return {"generation": generation, "carried": carried, "moved": moved,
                "ts": now, "truth_status": "real_derived"}
    except Exception as exc:  # noqa: BLE001 — never let a wake fault stop the daemon
        logger.debug("awaken skipped: %s", exc)
        return {"generation": 0, "carried": {}, "moved": {"woven": 0, "journey_recorded": False},
                "ts": time.time(), "truth_status": "no_data"}


__all__ = ["awaken", "read_genome"]
