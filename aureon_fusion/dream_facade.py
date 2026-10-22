"""🌙 DREAM FACADE — fusion-side repair of the Queen's dream faculty (W5).

The upstream dream path is broken: DreamScheduler.run() calls
``dream_engine.run_rem_dream_cycle()``, a method that does not exist on
EnigmaDreamer — the AttributeError was swallowed by queen_mind's dream
guard, so the dreams counter climbed while ``enigma_dream_memory.json``
was never created and no dream was ever generated.

This facade is the fusion-side adapter (upstream stays untouched). It
calls only REAL upstream EnigmaDreamer methods — ``dream_now()`` (the
general REM dream from collected patterns) and ``_rem_dream()`` (the
historical-trade REM replay) — applies the same quiet-hours + volatility
guard queen_mind used at its old dream pass, persists the dream memory to
DREAM_MEMORY_PATH, and reports honestly: ``dreamed`` is True only when a
dream was actually generated and the memory file written.

Contract:
    run_rem_pass(dreamer, *, quiet_hours, volatility, scheduler=None,
                 memory_path=None) -> dict:
        {"dreamed": bool, "memory_path": str | None,
         "summary": str | None, "quiet_hours": bool}

Import-safe: no upstream import at module level (the dreamer object is
passed in, already constructed under queen_mind's guards). No network, no
threads, no process spawns. Fail-closed: this module NEVER raises —
every failure path returns an honest dreamed=False result.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

# Script-or-module bootstrap: the registrar may launch this file directly.
if __package__ in (None, ""):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aureon_fusion.paths import FUSION_STATE

ORGAN_NAME = "queen_mind"
# The same absolute fusion-state location queen_mind pins (queen_mind.py:
# DREAM_MEMORY_PATH) — the upstream CWD-relative default is overridden here.
DEFAULT_DREAM_MEMORY_PATH = FUSION_STATE / ORGAN_NAME / "enigma_dream_memory.json"


def _dream_count(dreamer) -> int:
    memory = getattr(dreamer, "memory", None)
    dreams = getattr(memory, "dreams", None)
    try:
        return len(dreams or [])
    except TypeError:
        return 0


def run_rem_pass(dreamer, *, quiet_hours: bool, volatility: float,
                 scheduler=None, memory_path: str | None = None) -> dict:
    """Run one guarded REM dream pass against a live EnigmaDreamer.

    Guards (mirroring queen_mind's original dream pass):
      * quiet hours only — awake cycles notify the scheduler and skip;
      * volatility below the scheduler threshold (the queen derives it as
        1 - trading_pulse);
      * scheduler idle threshold respected when a scheduler is passed
        (after a dream the scheduler is notified, so the next dream waits
        at least idle_threshold_seconds of quiet).
    Only real upstream methods are invoked. Dream memory is persisted to
    ``memory_path`` (default: the fusion-state DREAM_MEMORY_PATH).
    """
    target = str(memory_path or DEFAULT_DREAM_MEMORY_PATH)
    result = {"dreamed": False, "memory_path": None, "summary": None,
              "quiet_hours": bool(quiet_hours)}

    if dreamer is None:
        result["summary"] = "dream engine unavailable"
        return result

    if not quiet_hours:
        result["summary"] = "awake hours — no dream"
        try:
            notify = getattr(scheduler, "notify_activity", None)
            if callable(notify):
                notify()
        except Exception:
            pass
        return result

    try:
        threshold = float(getattr(scheduler, "volatility_threshold", 0.5)) \
            if scheduler is not None else 0.5
    except Exception:
        threshold = 0.5
    if volatility >= threshold:
        result["summary"] = (f"volatility {volatility:.2f} at/above "
                             f"threshold {threshold:.2f} — held awake")
        return result

    if scheduler is not None:
        try:
            last_activity = float(
                getattr(scheduler, "last_activity_timestamp", 0.0) or 0.0)
            idle_needed = float(
                getattr(scheduler, "idle_threshold_seconds", 300.0) or 0.0)
            idle_for = time.time() - last_activity
            if idle_for < idle_needed:
                result["summary"] = (f"not idle long enough "
                                     f"({idle_for:.0f}s < {idle_needed:.0f}s)")
                return result
        except Exception:
            pass  # idle state unreadable — the volatility guard already passed

    before = _dream_count(dreamer)
    try:
        # Collect wisdom first (guarded — upstream history files may be
        # absent; both dream methods no-op without collected_wisdom).
        if not getattr(dreamer, "collected_wisdom", None):
            collector = getattr(dreamer, "wisdom_collector", None)
            collect = getattr(collector, "collect_all_wisdom", None)
            if callable(collect):
                dreamer.collected_wisdom = collect()
        # The REM pass itself: replay + recombination of what the organism
        # has lived (adds a dream when trade history exists), then the
        # general pattern dream — both upstream methods, unmodified.
        rem = getattr(dreamer, "_rem_dream", None)  # noqa: SLF001 (upstream API)
        if callable(rem):
            rem()
        dream_now = getattr(dreamer, "dream_now", None)
        dream = dream_now() if callable(dream_now) else None
    except Exception as exc:
        result["summary"] = f"dream pass raised: {exc.__class__.__name__}"
        return result

    after = _dream_count(dreamer)
    if after <= before and dream is None:
        result["summary"] = "dream engine produced nothing"
        return result

    # Persist the dream memory to the pinned fusion-state path.
    try:
        memory = getattr(dreamer, "memory", None)
        if memory is not None:
            memory.memory_file = target
            save = getattr(memory, "save", None)
            if callable(save):
                save()
    except Exception as exc:
        result["summary"] = f"dream memory persist failed: {exc.__class__.__name__}"
        return result

    if not os.path.exists(target):
        result["summary"] = "dream memory file missing after save"
        return result

    try:
        notify = getattr(scheduler, "notify_activity", None)
        if callable(notify):
            notify()   # prevent immediate re-dreaming
    except Exception:
        pass

    if dream is not None:
        summary = (f"{getattr(dream, 'dream_type', 'REM')}: "
                   f"{getattr(dream, 'content', '')} — "
                   f"{getattr(dream, 'insight', '')}")
    else:
        summary = f"REM replay consolidated {after - before} dream(s)"
    result.update({"dreamed": True, "memory_path": target,
                   "summary": summary[:240]})
    return result
