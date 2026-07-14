"""
🫁 AUREON ORGANISM DAEMON — the breath that was never scheduled.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The senses-all organs existed but production never launched them: supervisord
booted only the trading loops. This daemon is the missing [program] — it wakes
the metacognitive layer and keeps it breathing:

  1. ThoughtBus            — the shared nervous system (global singleton)
  2. ConsciousnessModule   — subscribe("*"): every thought in the body is felt
  3. Connectome            — progressive sweep until every module has been
                             touched; a pulse (organism.connectome.pulse) each
                             cycle with honest coverage
  4. Heartbeats            — ConsciousnessModule.heartbeat() each breath

Environment:
  AUREON_CONNECTOME_SWEEP=0        disable the progressive sweep (default on)
  AUREON_CONNECTOME_BATCH=25       modules touched per sweep cycle
  AUREON_CONNECTOME_INTERVAL_S=30  sweep cadence
  AUREON_ORGANISM_BREATH_S=15      heartbeat/pulse cadence

Run under AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS=1 (the supervisord block sets it)
so mass-touching modules can never flip trading env toward live mode.
"""

from __future__ import annotations

import logging
import os
import signal
import time
from typing import Any

logger = logging.getLogger("aureon.core.organism_daemon")


def _env_flag(name: str, default: str = "1") -> bool:
    return str(os.environ.get(name, default) or default) == "1"


def _env_int(name: str, default: int) -> int:
    try:
        return max(1, int(os.environ.get(name, str(default)) or default))
    except ValueError:
        return default


def boot() -> dict[str, Any]:
    """Wake the organs. Each is guarded — a missing organ degrades, never kills."""
    organs: dict[str, Any] = {}

    from aureon.core.aureon_thought_bus import get_thought_bus

    organs["bus"] = get_thought_bus()
    logger.info("🧠 ThoughtBus awake")

    try:
        from aureon.core.aureon_consciousness_module import ConsciousnessModule

        organs["consciousness"] = ConsciousnessModule(bus=organs["bus"])
        logger.info("👁️ ConsciousnessModule awake — sensing all bus traffic")
    except Exception as exc:  # noqa: BLE001
        logger.warning("ConsciousnessModule unavailable: %s", exc)

    from aureon.core.aureon_connectome import get_connectome

    connectome = get_connectome()
    organs["connectome"] = connectome
    if _env_flag("AUREON_CONNECTOME_SWEEP"):
        # weave_batch>0 graduates touched modules to woven (mycelium+Queen) each
        # cycle, so the body doesn't just get felt — it gets connected. Off →
        # touch-only (set AUREON_CONNECTOME_WEAVE=0).
        weave_batch = _env_int("AUREON_CONNECTOME_WEAVE_BATCH", 10) if _env_flag("AUREON_CONNECTOME_WEAVE") else 0
        connectome.start_sweep(
            interval_s=float(_env_int("AUREON_CONNECTOME_INTERVAL_S", 30)),
            batch_size=_env_int("AUREON_CONNECTOME_BATCH", 25),
            weave_batch=weave_batch,
        )
        logger.info("🕸️ Connectome sweep started (weave_batch=%s) — the organism feels AND connects its body", weave_batch)

    # Dr. Auris Throne — the cosmic gate. Its loop publishes
    # auris.throne.cosmic_state, which the grounded-action gate and several Queen
    # systems read. Without it started, get_dr_auris_throne() returns a static
    # fail-open default (gate always open). Guarded; env-toggle to disable.
    if _env_flag("AUREON_AURIS_AUTOSTART"):
        try:
            from aureon.intelligence.dr_auris_throne import get_dr_auris_throne

            throne = get_dr_auris_throne()
            throne.start()
            organs["auris_throne"] = throne
            logger.info("🔭 Dr. Auris Throne started — auris.throne.cosmic_state now flows live")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Dr. Auris Throne not started: %s", exc)

    return organs


def breathe_field(organs: dict[str, Any]) -> dict[str, Any] | None:
    """Breathe the whole-body field: fuse every producer's sub-field (via
    ``blend_field``) with the connectome's body-map health and publish it as one
    first-class event, ``organism.field.consensus``. Until now the blended field
    was pull-only (each reader recomputed it) and the body-map was display-only —
    this makes the organism's coherence a subscribable heartbeat signal. Guarded:
    returns None (a silent breath) when the bus or organs are missing."""
    bus = organs.get("bus")
    if bus is None:
        return None
    try:
        from aureon.core.aureon_thought_bus import Thought
        from aureon.core.hnc_field import blend_field

        blended = blend_field(bus).to_dict()
        body_map: dict[str, Any] = {}
        connectome = organs.get("connectome")
        if connectome is not None:
            snap = connectome.status()
            body_map = {k: snap.get(k) for k in ("coverage_pct", "woven", "failed", "baton_linked")}
        payload = {"blended": blended, "body_map": body_map}
        bus.publish(Thought(source="organism_daemon", topic="organism.field.consensus", payload=payload))
        # Cross-process bridge: the organism daemon breathes here, but the SaaS
        # consumers (/api/organism, /api/cognition) run in the operator process.
        # Mirror the consensus to a dedicated trace so its heartbeat crosses.
        try:
            import time as _t

            from aureon.core.bus_trace import append_trace

            append_trace("organism_consensus", {**payload, "ts": _t.time()}, cap=200)
        except Exception:  # noqa: BLE001
            pass
        return payload
    except Exception as exc:  # noqa: BLE001 — a silent breath is still a breath
        logger.debug("field breath skipped: %s", exc)
        return None


def breathe(organs: dict[str, Any]) -> None:
    """One breath: consciousness heartbeat + connectome pulse + whole-body field."""
    consciousness = organs.get("consciousness")
    if consciousness is not None:
        try:
            consciousness.heartbeat()
        except Exception as exc:  # noqa: BLE001
            logger.debug("heartbeat skipped: %s", exc)
    connectome = organs.get("connectome")
    if connectome is not None:
        try:
            snapshot = connectome.pulse()
            logger.info(
                "🫁 breath — nodes=%s touched=%s woven=%s linked=%s coverage=%s%%",
                snapshot["nodes"], snapshot["touched"], snapshot["woven"],
                snapshot["baton_linked"], snapshot["coverage_pct"],
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("pulse skipped: %s", exc)
    breathe_field(organs)
    # Metacognition: after fusing the whole-body field, the organism reads its
    # OWN signals and scores its self-coherence, then loops that assessment back
    # into the field as a sub-field (the β·Λ(t−τ) self-term at the organism
    # layer). Guarded — a silent breath if the monitor can't read anything.
    try:
        from aureon.core.metacognition_monitor import get_metacognition_monitor

        sa = get_metacognition_monitor().reflect()
        if sa.available:
            logger.info(
                "🧠 metacognition — self_coherence=%.3f psi=%.3f divergence=%s level=%s",
                sa.self_coherence or 0.0, sa.psi or 0.0, sa.divergence, sa.consciousness_level,
            )
    except Exception as exc:  # noqa: BLE001
        logger.debug("metacognition reflect skipped: %s", exc)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    # Belt and braces: even if the supervisord env is edited, mass imports from
    # this process must never flip trading env vars toward live mode.
    os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")

    # Bring every credential into the environment before the organs wake, so any
    # module the sweep touches sees the keys it expects. Presence-only, never fatal.
    try:
        from aureon.core.aureon_env import bootstrap_credentials

        _boot = bootstrap_credentials()
        _keys = " ".join(f"{k.split('_')[0]}={'on' if v else 'off'}" for k, v in _boot["present"].items())
        logger.info("🫁 credentials: %s", _keys)
    except Exception as exc:  # noqa: BLE001
        logger.warning("organism daemon: credential bootstrap skipped (%s)", exc)

    organs = boot()
    breath_s = _env_int("AUREON_ORGANISM_BREATH_S", 15)

    running = {"on": True}

    def _stop(signum: int, frame: Any) -> None:  # noqa: ARG001
        logger.info("organism daemon stopping (signal %s)", signum)
        running["on"] = False

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    logger.info("🫁 Organism daemon breathing every %ss", breath_s)
    while running["on"]:
        breathe(organs)
        time.sleep(breath_s)

    connectome = organs.get("connectome")
    if connectome is not None:
        connectome.stop_sweep()


if __name__ == "__main__":
    main()
