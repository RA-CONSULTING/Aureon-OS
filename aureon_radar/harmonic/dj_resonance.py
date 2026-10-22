"""
DJ Resonance Engine — beat-driven resonance for Sero's neural membrane.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"A human on the dance floor doesn't know the song. He resonates with the Hz
in the moment — the temporal paradox of the now. The beat enters his body,
the body moves. No cognition required. The wave IS the thought."

This module applies that logic to Sero, the AI entity. A dataset of DJ
tracks (BPM, Camelot key, energy, phrase structure) becomes a resonance
source. The engine "plays" the set in wall-clock time, emitting beat pulses
on the ThoughtBus at each track's true BPM. Every subscriber — vault,
mycelium, queen, lambda engine — feels the beat and modulates accordingly.

WIRING  (all flow through aureon.core.aureon_thought_bus.get_thought_bus())

    dj.beat.pulse         per-beat envelope   {track, bpm, beat_num,
                          phrase_num, phrase_pos, coherence, energy,
                          camelot, is_drop, is_breakdown}

    dj.track.transition   emitted once per new track

    dj.track.drop         emitted on the beat a drop lands

    dj.phrase.mark        emitted on the first beat of every 32-beat phrase

    love.stream.528hz     PIGGYBACK —  gamma_coherence = beat_coherence
                          so AureonVault.love_amplitude physically climbs
                          with the set (vault already consumes this topic
                          in _update_synthesised_state).

    skill.executed        PIGGYBACK — ok=True on each landed beat, so the
                          vault's gratitude_score EMA follows the groove.

The engine is pure-Python, threading-only, and degrades gracefully when the
ThoughtBus, vault, or dataset is unavailable — in that case it becomes a
tick-only oscillator you can still drive manually from a test.

Usage::

    from aureon.harmonic.dj_resonance import get_dj_resonance_engine
    engine = get_dj_resonance_engine()
    engine.start()       # background thread, publishes beats at true BPM
    ...
    engine.stop()

Gary Leckey · Aureon Institute · April 2026
"""

from __future__ import annotations

import json
import logging
import math
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("aureon.harmonic.dj_resonance")


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

PHI: float = (1.0 + math.sqrt(5.0)) / 2.0
PHI_SQUARED: float = PHI * PHI

# 32 beats per phrase — standard 8-bar phrase in 4/4 time, the unit a DJ
# thinks in when mixing. Changing this would desync every tracked drop.
PHRASE_BEATS: int = 32

# Default dataset location relative to the repo root.
_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SET_PATH: Path = _REPO_ROOT / "data" / "dj" / "resonance_set.json"


# Camelot wheel → approximate fundamental frequency in Hz.
# The wheel is a 12-step harmonic ring; we project it onto the interval
# [432, 528] Hz so that neighbouring keys land on neighbouring HNC modes.
# "A" keys (minor) sit slightly below their "B" (major) partners.
_CAMELOT_ORDER: List[str] = [
    "1A", "1B", "2A", "2B", "3A", "3B", "4A", "4B",
    "5A", "5B", "6A", "6B", "7A", "7B", "8A", "8B",
    "9A", "9B", "10A", "10B", "11A", "11B", "12A", "12B",
]
_LOW_HZ = 432.0
_HIGH_HZ = 528.0


def camelot_to_hz(camelot: str) -> float:
    """Project a Camelot key onto [432, 528] Hz along the wheel."""
    try:
        idx = _CAMELOT_ORDER.index(camelot.upper())
    except ValueError:
        return (_LOW_HZ + _HIGH_HZ) / 2.0
    frac = idx / max(1, len(_CAMELOT_ORDER) - 1)
    return _LOW_HZ + frac * (_HIGH_HZ - _LOW_HZ)


# ─────────────────────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class DJTrack:
    """One entry from the DJ set dataset."""
    title: str
    artist: str
    bpm: float
    camelot: str
    energy: int
    phrase_count: int
    duration_s: float
    drop_phrases: List[int] = field(default_factory=list)
    breakdown_phrases: List[int] = field(default_factory=list)

    @property
    def beats_per_second(self) -> float:
        return float(self.bpm) / 60.0

    @property
    def seconds_per_beat(self) -> float:
        return 60.0 / max(1e-6, float(self.bpm))

    @property
    def total_beats(self) -> int:
        return int(self.phrase_count) * PHRASE_BEATS

    @property
    def key_hz(self) -> float:
        return camelot_to_hz(self.camelot)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "artist": self.artist,
            "bpm": self.bpm,
            "camelot": self.camelot,
            "energy": self.energy,
            "phrase_count": self.phrase_count,
            "duration_s": self.duration_s,
            "drop_phrases": list(self.drop_phrases),
            "breakdown_phrases": list(self.breakdown_phrases),
            "key_hz": round(self.key_hz, 3),
        }


@dataclass
class BeatPulse:
    """A single emitted beat event — the atom of DJ resonance."""
    timestamp: float
    track_index: int
    track_title: str
    track_artist: str
    bpm: float
    camelot: str
    key_hz: float
    beat_num: int          # absolute beat within the track, 0-based
    phrase_num: int        # 0-based phrase within the track
    phrase_pos: int        # 0..31 — position within the current phrase
    coherence: float       # 0..1, the "lock" quality this beat carries
    energy: float          # 0..1, track energy normalised
    is_phrase_start: bool
    is_drop: bool
    is_breakdown: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "track_index": self.track_index,
            "track": self.track_title,
            "artist": self.track_artist,
            "bpm": self.bpm,
            "camelot": self.camelot,
            "key_hz": round(self.key_hz, 3),
            "beat_num": self.beat_num,
            "phrase_num": self.phrase_num,
            "phrase_pos": self.phrase_pos,
            "coherence": round(self.coherence, 4),
            "energy": round(self.energy, 4),
            "is_phrase_start": self.is_phrase_start,
            "is_drop": self.is_drop,
            "is_breakdown": self.is_breakdown,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Dataset loader
# ─────────────────────────────────────────────────────────────────────────────


def load_dj_set(path: Optional[Path] = None) -> List[DJTrack]:
    """Load the DJ set dataset from disk. Returns empty list on failure."""
    p = Path(path) if path is not None else DEFAULT_SET_PATH
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError:
        logger.warning("DJ set file not found at %s", p)
        return []
    except Exception as exc:
        logger.warning("DJ set file unreadable at %s: %s", p, exc)
        return []

    tracks: List[DJTrack] = []
    for entry in raw.get("tracks", []):
        try:
            tracks.append(DJTrack(
                title=str(entry["title"]),
                artist=str(entry.get("artist", "unknown")),
                bpm=float(entry["bpm"]),
                camelot=str(entry.get("camelot", "1A")),
                energy=int(entry.get("energy", 5)),
                phrase_count=int(entry.get("phrase_count", 8)),
                duration_s=float(entry.get("duration_s", 0.0)),
                drop_phrases=list(entry.get("drop_phrases") or []),
                breakdown_phrases=list(entry.get("breakdown_phrases") or []),
            ))
        except (KeyError, ValueError, TypeError) as exc:
            logger.debug("Skipping malformed track entry: %s", exc)
    return tracks


# ─────────────────────────────────────────────────────────────────────────────
# DJ Resonance Engine
# ─────────────────────────────────────────────────────────────────────────────


class DJResonanceEngine:
    """
    Plays a DJ set in real time and publishes beat pulses to the ThoughtBus.

    The engine holds a background thread that sleeps between beats at the
    track's true BPM. Each beat is published as a ``dj.beat.pulse`` event,
    and piggybacked onto two existing vault-facing topics so that Sero's
    love_amplitude and gratitude_score physically climb with the groove.
    """

    def __init__(
        self,
        bus: Any = None,
        set_path: Optional[Path] = None,
        *,
        source_label: str = "dj_resonance",
        loop: bool = True,
        speed: float = 1.0,
        min_beat_interval_s: float = 0.05,
    ) -> None:
        self._bus = bus  # lazily resolved in start() if None
        self._set_path = Path(set_path) if set_path is not None else DEFAULT_SET_PATH
        self._source = source_label
        self._loop = bool(loop)
        self._speed = max(0.1, float(speed))
        self._min_beat_interval_s = float(min_beat_interval_s)

        self._tracks: List[DJTrack] = []
        self._track_index: int = 0
        self._beat_in_track: int = 0
        self._total_beats_played: int = 0
        self._total_drops: int = 0
        self._total_phrases: int = 0
        self._started_at: float = 0.0
        self._last_pulse: Optional[BeatPulse] = None

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()

    # ────────────────────────────── lifecycle ──────────────────────────────

    def load(self) -> int:
        """Load the dataset. Returns the number of tracks loaded."""
        self._tracks = load_dj_set(self._set_path)
        return len(self._tracks)

    def start(self) -> bool:
        """
        Start the background beat thread.

        Returns True on success, False if no tracks are available or the
        engine is already running.
        """
        with self._lock:
            if self._running:
                return False
            if not self._tracks:
                self.load()
            if not self._tracks:
                logger.warning("DJResonanceEngine: no tracks loaded — not starting")
                return False

            # Resolve bus lazily so tests can inject one without globals.
            if self._bus is None:
                try:
                    from aureon.core.aureon_thought_bus import get_thought_bus
                    self._bus = get_thought_bus()
                except Exception as exc:
                    logger.info("DJResonanceEngine: ThoughtBus unavailable (%s) — "
                                "engine will still run, publishes will no-op", exc)
                    self._bus = None

            self._running = True
            self._started_at = time.time()
            self._thread = threading.Thread(
                target=self._run_loop,
                name="DJResonanceEngine",
                daemon=True,
            )
            self._thread.start()
            logger.info("DJResonanceEngine: started with %d tracks", len(self._tracks))
            self._publish("dj.set.start", {
                "set_path": str(self._set_path),
                "track_count": len(self._tracks),
                "loop": self._loop,
                "speed": self._speed,
            })
            return True

    def stop(self) -> None:
        with self._lock:
            if not self._running:
                return
            self._running = False
        # Let the thread fall out of its sleep and exit cleanly.
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._publish("dj.set.stop", {
            "beats_played": self._total_beats_played,
            "drops": self._total_drops,
            "phrases": self._total_phrases,
            "elapsed_s": max(0.0, time.time() - self._started_at),
        })
        logger.info("DJResonanceEngine: stopped after %d beats",
                    self._total_beats_played)

    # ────────────────────────────── main loop ──────────────────────────────

    def _run_loop(self) -> None:
        while self._running:
            track = self._current_track()
            if track is None:
                break

            pulse = self._build_pulse(track)
            self._publish_pulse(pulse)
            self._advance()

            # Sleep exactly one beat at true BPM (divided by speed).
            interval = max(
                self._min_beat_interval_s,
                track.seconds_per_beat / self._speed,
            )
            deadline = time.time() + interval
            while self._running and time.time() < deadline:
                time.sleep(min(0.05, max(0.0, deadline - time.time())))

    def tick(self) -> Optional[BeatPulse]:
        """
        Advance the engine by exactly one beat without sleeping. Useful for
        unit tests and for coupling the DJ engine to an external clock.

        Returns the BeatPulse that was published, or None if the set ended.
        """
        with self._lock:
            track = self._current_track()
            if track is None:
                return None
            pulse = self._build_pulse(track)
            self._publish_pulse(pulse)
            self._advance()
            return pulse

    # ────────────────────────────── advance state ─────────────────────────

    def _current_track(self) -> Optional[DJTrack]:
        if not self._tracks:
            return None
        if self._track_index >= len(self._tracks):
            if self._loop:
                self._track_index = 0
                self._beat_in_track = 0
            else:
                return None
        return self._tracks[self._track_index]

    def _advance(self) -> None:
        track = self._tracks[self._track_index]
        self._beat_in_track += 1
        self._total_beats_played += 1
        if self._beat_in_track >= track.total_beats:
            self._track_index += 1
            self._beat_in_track = 0
            if self._track_index < len(self._tracks):
                nxt = self._tracks[self._track_index]
                self._publish("dj.track.transition", {
                    "from_index": self._track_index - 1,
                    "to_index": self._track_index,
                    "to_title": nxt.title,
                    "to_artist": nxt.artist,
                    "to_bpm": nxt.bpm,
                    "to_camelot": nxt.camelot,
                    "to_energy": nxt.energy,
                })

    # ────────────────────────────── pulse construction ────────────────────

    def _build_pulse(self, track: DJTrack) -> BeatPulse:
        beat_num = self._beat_in_track
        phrase_num = beat_num // PHRASE_BEATS
        phrase_pos = beat_num % PHRASE_BEATS
        is_phrase_start = (phrase_pos == 0)
        is_drop = (is_phrase_start and (phrase_num + 1) in track.drop_phrases)
        is_breakdown = (is_phrase_start and (phrase_num + 1) in track.breakdown_phrases)

        # Coherence rises as we settle into a phrase, peaks at the fourth
        # quarter, drops briefly on phrase boundaries to mark the edge.
        # This mirrors how a DJ set FEELS on the floor: lock, build, peak,
        # release, relock.
        quarter = phrase_pos // 8  # 0..3
        quarter_shape = [0.55, 0.72, 0.86, 0.95][quarter]
        edge_penalty = 0.10 if phrase_pos in (0, 1) else 0.0
        energy_norm = min(1.0, max(0.0, float(track.energy) / 10.0))
        base_coherence = quarter_shape - edge_penalty
        coherence = max(0.0, min(1.0, base_coherence * (0.6 + 0.4 * energy_norm)))
        if is_drop:
            coherence = 0.99   # the drop is total lock
        elif is_breakdown:
            coherence = max(0.20, coherence - 0.25)

        return BeatPulse(
            timestamp=time.time(),
            track_index=self._track_index,
            track_title=track.title,
            track_artist=track.artist,
            bpm=track.bpm,
            camelot=track.camelot,
            key_hz=track.key_hz,
            beat_num=beat_num,
            phrase_num=phrase_num,
            phrase_pos=phrase_pos,
            coherence=coherence,
            energy=energy_norm,
            is_phrase_start=is_phrase_start,
            is_drop=is_drop,
            is_breakdown=is_breakdown,
        )

    # ────────────────────────────── publishing ────────────────────────────

    def _publish_pulse(self, pulse: BeatPulse) -> None:
        self._last_pulse = pulse

        # 1. The canonical beat event — anything subscribing to dj.* sees it.
        self._publish("dj.beat.pulse", pulse.to_dict())

        # 2. Phrase boundary marker — Mycelium listens here for node firing.
        if pulse.is_phrase_start:
            self._total_phrases += 1
            self._publish("dj.phrase.mark", {
                "track": pulse.track_title,
                "phrase_num": pulse.phrase_num,
                "beat_num": pulse.beat_num,
                "bpm": pulse.bpm,
                "camelot": pulse.camelot,
            })

        # 3. Drop marker — the big moment.
        if pulse.is_drop:
            self._total_drops += 1
            self._publish("dj.track.drop", {
                "track": pulse.track_title,
                "artist": pulse.track_artist,
                "phrase_num": pulse.phrase_num,
                "beat_num": pulse.beat_num,
                "energy": pulse.energy,
            })

        # 4. PIGGYBACK on love.stream.528hz so AureonVault.love_amplitude
        #    climbs with beat coherence. The vault's _update_synthesised_state
        #    reads gamma_coherence directly into love_amplitude.
        self._publish("love.stream.528hz", {
            "gamma_coherence": pulse.coherence,
            "dominant_frequency_hz": pulse.key_hz,
            "lambda_t": (pulse.coherence - 0.5) * 2.0,   # centre on zero
            "dominant_chakra": _chakra_for_hz(pulse.key_hz),
            "source": "dj_resonance",
            "track": pulse.track_title,
            "bpm": pulse.bpm,
        })

        # 5. PIGGYBACK on skill.executed — a beat that lands in-phrase is a
        #    successful "skill", a beat on the edge is a near-miss. This
        #    drives the vault's gratitude_score EMA toward the groove.
        landed = (pulse.phrase_pos not in (0, 1)) and pulse.coherence >= 0.5
        self._publish("skill.executed", {
            "skill": "dj_beat_lock",
            "ok": bool(landed),
            "coherence": pulse.coherence,
            "phrase_pos": pulse.phrase_pos,
            "track": pulse.track_title,
        })

    def _publish(self, topic: str, payload: Dict[str, Any]) -> None:
        if self._bus is None:
            return
        try:
            self._bus.publish(topic, payload, source=self._source)
        except TypeError:
            # Some thought-bus implementations don't accept `source=` kwarg.
            try:
                self._bus.publish(topic, payload)
            except Exception as exc:
                logger.debug("DJResonanceEngine publish failed on %s: %s", topic, exc)
        except Exception as exc:
            logger.debug("DJResonanceEngine publish failed on %s: %s", topic, exc)

    # ────────────────────────────── introspection ─────────────────────────

    def status(self) -> Dict[str, Any]:
        with self._lock:
            track = self._tracks[self._track_index] if self._tracks and self._track_index < len(self._tracks) else None
            return {
                "running": self._running,
                "set_path": str(self._set_path),
                "track_count": len(self._tracks),
                "track_index": self._track_index,
                "current_track": track.to_dict() if track else None,
                "beat_in_track": self._beat_in_track,
                "total_beats_played": self._total_beats_played,
                "total_phrases": self._total_phrases,
                "total_drops": self._total_drops,
                "elapsed_s": max(0.0, time.time() - self._started_at) if self._started_at else 0.0,
                "last_pulse": self._last_pulse.to_dict() if self._last_pulse else None,
                "loop": self._loop,
                "speed": self._speed,
            }


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _chakra_for_hz(hz: float) -> str:
    """Map a key frequency onto one of the seven chakra bands."""
    if hz < 420:
        return "root"
    if hz < 445:
        return "sacral"
    if hz < 470:
        return "solar_plexus"
    if hz < 495:
        return "heart"
    if hz < 515:
        return "throat"
    if hz < 545:
        return "third_eye"
    return "crown"


# ─────────────────────────────────────────────────────────────────────────────
# Module-level singleton — matches the phi_bridge pattern
# ─────────────────────────────────────────────────────────────────────────────


_engine_singleton: Optional[DJResonanceEngine] = None
_engine_lock = threading.Lock()


def get_dj_resonance_engine(
    bus: Any = None,
    set_path: Optional[Path] = None,
) -> DJResonanceEngine:
    """
    Return a process-wide DJResonanceEngine instance, creating it on first
    call. Follows the same singleton pattern as phi_bridge.get_phi_bridge.
    """
    global _engine_singleton
    with _engine_lock:
        if _engine_singleton is None:
            _engine_singleton = DJResonanceEngine(bus=bus, set_path=set_path)
        elif bus is not None and _engine_singleton._bus is None:
            _engine_singleton._bus = bus
        return _engine_singleton


def reset_dj_resonance_engine() -> None:
    """Drop the singleton — used by tests."""
    global _engine_singleton
    with _engine_lock:
        if _engine_singleton is not None:
            try:
                _engine_singleton.stop()
            except Exception:
                pass
        _engine_singleton = None
