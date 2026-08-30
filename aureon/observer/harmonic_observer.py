"""Theroux-style observer over the live HNC field.

Long-window, low-interpretation. Watches the Λ(t) trace produced by
``aureon/core/hnc_live_daemon.py`` and identifies recurring anchor
features ("rocks") at two time scales — fast (hours) for short-term
gating, slow (days) for regime decisions.

What it does:
  * Maintains two rolling buffers of the live Λ trace.
  * Detects four kinds of rocks: spectral peaks, plateaus, regime
    transitions, dominant frequency bands.
  * Tracks each rock's persistence across observations.
  * Emits ``RockEvent`` envelopes via the ThoughtBus when rocks form,
    strengthen, weaken, or vanish.
  * Exposes a snapshot accessor that the Queen sentience layer, the
    Kelly gate, and the prediction bus all read.

What it explicitly does NOT do:
  * Interpret what a rock means for trading. The whole point of the
    Theroux framing is to *document* recurring features and let
    downstream consumers decide what to do with them.
  * Modify any existing math. It composes existing utilities (FFT,
    coherence, phase-transition curvature, Lighthouse z-score) — see
    the plan file for the explicit reuse map.

Optional dependencies:
  numpy / scipy.signal are required for the full detector. If they're
  unavailable (e.g. the test sandbox), ``HarmonicObserver`` still
  imports and accepts samples; the detector becomes a no-op that returns
  empty rock lists. This keeps imports cheap and the module testable.
"""

from __future__ import annotations

import logging
import math
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, List, Optional, Tuple

from aureon.observer.rock import Rock, RockEvent, RockKind, RockScale

logger = logging.getLogger(__name__)


# Optional heavy deps — guarded. The detector degrades gracefully.
try:
    import numpy as _np  # noqa: F401
    _HAS_NUMPY = True
except Exception:
    _HAS_NUMPY = False

try:
    from scipy.signal import find_peaks as _find_peaks  # noqa: F401
    _HAS_SCIPY = True
except Exception:
    _HAS_SCIPY = False


# ─── Configuration ────────────────────────────────────────────────

# Sampling cadence of the trace (seconds between Λ steps). The HNC live
# daemon ticks every COMPUTE_INTERVAL = 5 s, so this matches.
DEFAULT_TRACE_INTERVAL_S = 5.0

# Window sizes (minutes) — fast and slow Theroux observation scales.
DEFAULT_FAST_WINDOW_MIN = 360       # 6 hours
DEFAULT_SLOW_WINDOW_MIN = 20160     # 14 days

# z-score threshold for declaring a sample "anomalous" — same value the
# Lighthouse uses (aureon/analytics/aureon_lighthouse.py:101).
ANOMALY_Z_THRESHOLD = 2.5

#: publish_field() throttle: one symbolic.life.subfield row per this many
#: seconds, so the daemon's 5 s compute cadence doesn't flood the trace.
_SUBFIELD_MIN_INTERVAL_S = 30.0

# Plateau detection: how flat (max stddev) and how long (samples) a
# region must be to count as a plateau.
PLATEAU_STD_RATIO = 0.05
PLATEAU_MIN_SAMPLES = 24            # 2 minutes at 5 s

# Rock matching tolerance: a new candidate at frequency f is "the same"
# rock as an existing one if their dominant_hz match within this fraction.
ROCK_MATCH_HZ_TOL = 0.10

# A rock vanishes after this many seconds without reaffirmation.
ROCK_TIMEOUT_S = 300.0


def _safe_float(x):
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if v != v:  # NaN
        return None
    return v


def _safe_str(x):
    if x is None:
        return None
    try:
        return str(x)
    except Exception:
        return None


@dataclass
class _ScaleBuffer:
    """Rolling buffer for one observation scale."""
    name: RockScale
    window_min: float
    samples: Deque[Tuple[float, float]]   # (ts, lambda_t)
    last_detect_ts: float = 0.0
    detect_interval_s: float = 30.0       # how often to re-run the detector

    @property
    def n(self) -> int:
        return len(self.samples)


# ─── The observer ──────────────────────────────────────────────────

class HarmonicObserver:
    """Sustained-attention observer over the live HNC field.

    Thread-safe: ``ingest`` may be called from any thread; the read
    accessors (``current_rocks``, ``coherence_score``, ``regime``,
    ``metrics_snapshot``) are safe to call concurrently.

    ThoughtBus emission is fire-and-forget; failures are logged at
    debug-level and never raise into the caller.
    """

    def __init__(
        self,
        fast_window_minutes: float = DEFAULT_FAST_WINDOW_MIN,
        slow_window_minutes: float = DEFAULT_SLOW_WINDOW_MIN,
        trace_interval_s: float = DEFAULT_TRACE_INTERVAL_S,
        publish_to_bus: bool = True,
        bus=None,
    ):
        # RLock so metrics_snapshot() can call regime()/coherence helpers
        # while already inside the snapshot's own ``with self._lock``.
        self._lock = threading.RLock()
        self._publish = publish_to_bus
        self._bus = bus  # late-bound below
        self._last_subfield_ts = 0.0
        # The FFT frequency grid must use the CONFIGURED sampling interval —
        # using the module default regardless of configuration scaled every
        # reported dominant_hz by default/actual (5× off for a 1s trace).
        self._trace_interval_s = float(trace_interval_s) or DEFAULT_TRACE_INTERVAL_S

        # Compute buffer caps from window minutes / interval.
        fast_cap = max(8, int((fast_window_minutes * 60) / trace_interval_s))
        slow_cap = max(8, int((slow_window_minutes * 60) / trace_interval_s))

        self._fast = _ScaleBuffer(
            name="fast",
            window_min=fast_window_minutes,
            samples=deque(maxlen=fast_cap),
            detect_interval_s=30.0,
        )
        self._slow = _ScaleBuffer(
            name="slow",
            window_min=slow_window_minutes,
            samples=deque(maxlen=slow_cap),
            detect_interval_s=600.0,
        )

        # Rock catalogue (per-scale). Keyed by rock id.
        self._rocks: Dict[RockScale, Dict[str, Rock]] = {"fast": {}, "slow": {}}

        # Stats for diagnostics.
        self._n_ingested = 0
        self._n_events_emitted = 0
        self._started_at = time.time()

        # Latest engine-derived fields. Populated by ``ingest_state``;
        # ``ingest`` only fills ``lambda_t`` and ``ts`` (psi / level stay
        # None). The Queen sentience layer reads this via
        # ``latest_field()`` so it can ground its thought generation in
        # the live HNC field without reaching into LambdaEngine
        # directly.
        self._latest_field: Dict = {
            "lambda_t": None,
            "consciousness_psi": None,
            "consciousness_level": None,
            "coherence_gamma": None,
            "ts": None,
        }

    # ─── public ingestion API ──────────────────────────────────

    def ingest(self, ts: float, lambda_t: float) -> None:
        """Feed one (timestamp, Λ_full) sample into the observer.

        ``ts`` is unix seconds; ``lambda_t`` is the field value from a
        ``LambdaState``. Callers can pull these from the live daemon's
        compute loop or by tailing ``state/hnc_live_trace.jsonl``.

        Use ``ingest_state`` instead when you have the full ``LambdaState``
        — it forwards to ``ingest`` and additionally caches psi / level /
        gamma so the Queen sentience layer can read them via
        ``latest_field()``.
        """
        if not isinstance(ts, (int, float)):
            return
        try:
            v = float(lambda_t)
        except (TypeError, ValueError):
            return
        if math.isnan(v) or math.isinf(v):
            return

        with self._lock:
            self._fast.samples.append((float(ts), v))
            self._slow.samples.append((float(ts), v))
            self._n_ingested += 1
            # ingest() alone updates lambda_t / ts only; psi/level stay
            # at whatever the last ingest_state(...) set them to (or
            # None if never called).
            self._latest_field["lambda_t"] = v
            self._latest_field["ts"] = float(ts)

            # Run detection on each scale at its own cadence.
            for buf in (self._fast, self._slow):
                if (ts - buf.last_detect_ts) >= buf.detect_interval_s:
                    buf.last_detect_ts = ts
                    self._detect_and_update(buf, ts)

            # Expire stale rocks across both scales.
            self._expire_stale_rocks(ts)

    def ingest_state(self, state) -> None:
        """Feed a full engine ``LambdaState`` (or any object with ``lambda_t``,
        ``timestamp``, ``consciousness_psi``, ``consciousness_level``,
        ``coherence_gamma`` attributes — duck-typed).

        Equivalent to ``ingest(state.timestamp, state.lambda_t)`` plus
        caching of the engine-derived psi / level / gamma fields so
        downstream consumers (Queen sentience, predictor adapter) can
        read them from the observer rather than the engine directly.
        Safe to call from the daemon's compute loop on every step.
        """
        if state is None:
            return
        ts = getattr(state, "timestamp", None)
        if ts is None:
            ts = time.time()
        lt = getattr(state, "lambda_t", None)
        if lt is None:
            return
        # Defer the buffer + detection update to ingest() — single
        # source of truth for the rolling-buffer logic.
        self.ingest(float(ts), float(lt))
        # Now overlay the richer engine-derived fields. ingest() already
        # took the lock and released it; take it again briefly so the
        # latest_field dict update is atomic w.r.t. latest_field().
        with self._lock:
            self._latest_field.update({
                "lambda_t": float(lt),
                "ts": float(ts),
                "consciousness_psi": _safe_float(getattr(state, "consciousness_psi", None)),
                "consciousness_level": _safe_str(getattr(state, "consciousness_level", None)),
                "coherence_gamma": _safe_float(getattr(state, "coherence_gamma", None)),
            })

    def latest_field(self) -> Dict:
        """Return the most recent engine-derived field state.

        Always returns a dict; keys are populated as data arrives:
            ``lambda_t``, ``ts``                 — from any ``ingest`` call
            ``consciousness_psi``,
            ``consciousness_level``,
            ``coherence_gamma``                  — only from ``ingest_state``

        Missing keys are ``None``. Safe to call before any data has
        arrived (returns a dict of all-None).
        """
        with self._lock:
            return dict(self._latest_field)

    def publish_field(self) -> None:
        """Publish this observer's LOCAL field as a ``symbolic.life.subfield``.

        The observer computes a real local field (rock-stability coherence
        over the Λ(t) trace) yet was pinned in the logic-train audit as a
        producer that never publishes — the whole body could not see it.
        Throttled to one row per _SUBFIELD_MIN_INTERVAL_S; publishes NOTHING
        before data arrives (an unmeasured field is not reported).
        """
        lf = self.latest_field()
        if lf.get("lambda_t") is None:
            return
        now = time.time()
        with self._lock:
            if now - self._last_subfield_ts < _SUBFIELD_MIN_INTERVAL_S:
                return
            self._last_subfield_ts = now
        try:
            from types import SimpleNamespace

            from aureon.core.hnc_field import publish_subfield
            publish_subfield("harmonic_observer", SimpleNamespace(
                symbolic_life_score=self.coherence_score(),
                coherence_gamma=lf.get("coherence_gamma"),
                consciousness_level=lf.get("consciousness_level"),
            ))
        except Exception as exc:  # noqa: BLE001 - telemetry must never break ingest
            logger.debug("harmonic_observer subfield publish failed: %s", exc)

    # ─── public read API ───────────────────────────────────────

    def current_rocks(self, scale: Optional[RockScale] = None) -> List[Rock]:
        """Active rocks. Pass ``scale='fast'`` or ``'slow'`` to filter."""
        with self._lock:
            if scale is None:
                return list(self._rocks["fast"].values()) + list(self._rocks["slow"].values())
            return list(self._rocks[scale].values())

    def coherence_score(self) -> float:
        """0..1 score derived from rock stability.

        High coherence ⇒ a few persistent rocks dominate. Low coherence
        ⇒ either no rocks at all (noise field) or many short-lived rocks
        flickering in and out (chaotic field). Used by the Kelly gate to
        scale ``r_prime_buffer``: low coherence demands a wider safety
        margin.
        """
        with self._lock:
            return self._coherence_score_locked()

    def regime(self) -> str:
        """Coarse regime label derived from the slow-scale rock catalogue.

        Mirrors the spec's QUIET / COUPLED / CHARGED / RESONANT taxonomy
        without committing to specific param thresholds yet (those want
        to be fitted from data — see Stage F).
        """
        with self._lock:
            slow_rocks = list(self._rocks["slow"].values())
            if not self._slow.samples or self._slow.n < 8:
                return "WARMING"            # not enough data yet
            if not slow_rocks:
                return "QUIET"
            n_strong = sum(1 for r in slow_rocks if r.z_score >= ANOMALY_Z_THRESHOLD)
            n_aligned = sum(1 for r in slow_rocks if r.alignment_partners)
            if n_strong >= 3 and n_aligned >= 2:
                return "RESONANT"
            if n_strong >= 1 or n_aligned >= 1:
                return "COUPLED"
            return "CHARGED"

    def metrics_snapshot(self) -> Dict:
        """Everything in one JSON-serialisable dict — used by the Queen
        sentience engine as a context field, by the predictor adapter
        as the basis for ``UnifiedSignal``, and by the runner for stdout.
        """
        with self._lock:
            return {
                "ts": time.time(),
                "n_samples_fast": self._fast.n,
                "n_samples_slow": self._slow.n,
                "n_ingested": self._n_ingested,
                "n_events_emitted": self._n_events_emitted,
                "uptime_s": time.time() - self._started_at,
                "regime": self.regime(),  # uses lock-aware path; re-acquires noop on RLock
                "coherence_score": self._coherence_score_locked(),
                "rocks_fast": [r.to_dict() for r in self._rocks["fast"].values()],
                "rocks_slow": [r.to_dict() for r in self._rocks["slow"].values()],
                "latest_field": dict(self._latest_field),
                "has_numpy": _HAS_NUMPY,
                "has_scipy": _HAS_SCIPY,
            }

    # ─── internal: detection ───────────────────────────────────

    def _detect_and_update(self, buf: _ScaleBuffer, ts: float) -> None:
        """Run the detector on a buffer and reconcile with the rock catalogue.

        Locked by caller.
        """
        if buf.n < 8:
            return  # not enough samples for any meaningful detection

        values = [v for (_, v) in buf.samples]
        candidates = self._compute_rock_candidates(values, buf.name)
        existing = self._rocks[buf.name]

        # Match candidates to existing rocks by frequency proximity. New
        # ones become rocks; matched ones get reaffirmed.
        seen_ids: List[str] = []
        for cand in candidates:
            match = self._match_existing(cand, existing)
            if match is not None:
                # Reaffirm and possibly emit "strengthened" / "weakened".
                old_z = match.z_score
                match.z_score = cand.z_score
                match.amplitude = cand.amplitude
                match.dominant_hz = cand.dominant_hz
                match.reaffirm(ts)
                seen_ids.append(match.id)
                if cand.z_score > old_z * 1.25:
                    self._emit("strengthened", match)
                elif cand.z_score < old_z * 0.75:
                    self._emit("weakened", match)
            else:
                # New rock.
                cand.first_seen = ts
                cand.last_seen = ts
                existing[cand.id] = cand
                seen_ids.append(cand.id)
                self._emit("formed", cand)

        # Compute alignments between currently-active rocks via
        # frequency proximity (a stand-in until the harmonic_seed
        # coherence call is wired in Stage B).
        self._update_alignments_locked(buf.name)

    def _compute_rock_candidates(
        self, values: List[float], scale: RockScale
    ) -> List[Rock]:
        """Identify rock candidates from a values array.

        Without numpy/scipy this is a no-op (returns empty list). With
        them, runs a Hanning-windowed FFT to find the dominant
        frequency (band-rock candidate), then ``scipy.signal.find_peaks``
        for peak rocks, then a stddev-based scan for plateaus.
        """
        if not _HAS_NUMPY:
            return []

        import numpy as np
        arr = np.asarray(values, dtype=float)
        if arr.size < 8:
            return []

        candidates: List[Rock] = []

        # Running noise floor — used to z-score every candidate.
        mu = float(arr.mean())
        sigma = float(arr.std()) or 1e-9

        # ── Band rock — dominant FFT frequency
        try:
            # Demean before windowing: Λ traces carry a large DC offset, and
            # Hanning leakage from that DC component otherwise dominates bin 1
            # and buries the true oscillation (every detection reported the
            # lowest non-DC bin as "dominant").
            windowed = (arr - arr.mean()) * np.hanning(arr.size)
            spec = np.abs(np.fft.rfft(windowed))
            freqs = np.fft.rfftfreq(arr.size, d=self._trace_interval_s)
            # Drop DC.
            if spec.size > 1:
                spec[0] = 0.0
                idx = int(np.argmax(spec))
                amp = float(spec[idx])
                noise = float(spec.mean()) or 1e-9
                z = amp / noise
                if z >= ANOMALY_Z_THRESHOLD and freqs[idx] > 0:
                    candidates.append(Rock(
                        kind="band",
                        scale=scale,
                        dominant_hz=float(freqs[idx]),
                        amplitude=amp,
                        z_score=z,
                        meta={"fft_bin": idx, "noise_floor": noise},
                    ))
        except Exception as exc:
            logger.debug("band detection failed: %s", exc)

        # ── Peak rocks — local maxima in the time series above z-threshold
        if _HAS_SCIPY:
            try:
                from scipy.signal import find_peaks
                peaks, props = find_peaks(arr, prominence=sigma)
                for pi in peaks:
                    val = float(arr[pi])
                    z = (val - mu) / sigma
                    if z < ANOMALY_Z_THRESHOLD:
                        continue
                    candidates.append(Rock(
                        kind="peak",
                        scale=scale,
                        dominant_hz=0.0,
                        amplitude=val,
                        z_score=z,
                        meta={"sample_index": int(pi)},
                    ))
            except Exception as exc:
                logger.debug("peak detection failed: %s", exc)

        # ── Plateau rocks — sustained low-variance segments
        try:
            win = max(PLATEAU_MIN_SAMPLES, arr.size // 12)
            if arr.size >= win:
                # Rolling stddev via cumsum trick (cheap, vectorised).
                cumsum = np.cumsum(arr, dtype=float)
                cumsum2 = np.cumsum(arr * arr, dtype=float)

                def _std(start: int, end: int) -> Tuple[float, float]:
                    n = end - start
                    if n <= 1:
                        return 0.0, 0.0
                    s1 = cumsum[end - 1] - (cumsum[start - 1] if start > 0 else 0.0)
                    s2 = cumsum2[end - 1] - (cumsum2[start - 1] if start > 0 else 0.0)
                    mean = s1 / n
                    var = max(0.0, (s2 / n) - mean * mean)
                    return mean, math.sqrt(var)

                threshold = abs(mu) * PLATEAU_STD_RATIO + 1e-9
                # Walk non-overlapping windows; flag the lowest-std one.
                best = None
                for start in range(0, arr.size - win + 1, max(1, win // 2)):
                    end = start + win
                    m, s = _std(start, end)
                    if s <= threshold:
                        if best is None or s < best[1]:
                            best = (m, s, start, end)
                if best is not None:
                    m, s, start, end = best
                    candidates.append(Rock(
                        kind="plateau",
                        scale=scale,
                        dominant_hz=0.0,
                        amplitude=float(m),
                        z_score=(threshold - s) / threshold,  # 0..1 clamp below
                        meta={"start": int(start), "end": int(end), "std": float(s)},
                    ))
        except Exception as exc:
            logger.debug("plateau detection failed: %s", exc)

        return candidates

    def _match_existing(
        self, cand: Rock, existing: Dict[str, Rock]
    ) -> Optional[Rock]:
        """Find a matching existing rock for a candidate, or None.

        Match rule:
          * same kind
          * for ``band`` / ``peak`` with non-zero hz: dominant_hz within
            ``ROCK_MATCH_HZ_TOL`` fraction of existing hz
          * for ``plateau``: amplitude within 5% of existing
        """
        for r in existing.values():
            if r.kind != cand.kind:
                continue
            if cand.kind in ("band", "peak") and cand.dominant_hz > 0 and r.dominant_hz > 0:
                rel = abs(cand.dominant_hz - r.dominant_hz) / max(r.dominant_hz, 1e-9)
                if rel <= ROCK_MATCH_HZ_TOL:
                    return r
            elif cand.kind == "plateau":
                rel = abs(cand.amplitude - r.amplitude) / max(abs(r.amplitude), 1e-9)
                if rel <= 0.05:
                    return r
        return None

    def _update_alignments_locked(self, scale: RockScale) -> None:
        """Mark rocks that share a frequency partner as aligned."""
        rocks = list(self._rocks[scale].values())
        for r in rocks:
            r.alignment_partners = []
        for i, a in enumerate(rocks):
            if a.dominant_hz <= 0:
                continue
            for b in rocks[i + 1 :]:
                if b.dominant_hz <= 0:
                    continue
                rel = abs(a.dominant_hz - b.dominant_hz) / max(a.dominant_hz, 1e-9)
                if rel <= ROCK_MATCH_HZ_TOL:
                    a.alignment_partners.append(b.id)
                    b.alignment_partners.append(a.id)

    def _expire_stale_rocks(self, now_ts: float) -> None:
        """Drop rocks not reaffirmed within ROCK_TIMEOUT_S; emit 'vanished'."""
        for scale in ("fast", "slow"):
            cat = self._rocks[scale]
            stale = [rid for rid, r in cat.items() if (now_ts - r.last_seen) > ROCK_TIMEOUT_S]
            for rid in stale:
                rock = cat.pop(rid)
                self._emit("vanished", rock)

    # ─── internal: coherence ───────────────────────────────────

    def _coherence_score_locked(self) -> float:
        """Dimensionless 0..1 score combining rock count, persistence, and alignment.

        Rationale: a "rocky" field is one where a small number of strong,
        persistent, aligned features anchor the dynamics. Empty fields
        and chaotic fields both score near zero; a stable resonant field
        scores near one.
        """
        all_rocks = list(self._rocks["fast"].values()) + list(self._rocks["slow"].values())
        if not all_rocks:
            return 0.0
        # Persistence component (saturates at 30 minutes).
        persist = min(1.0, sum(r.persistence_s for r in all_rocks) / (1800.0 * len(all_rocks)))
        # Alignment component.
        align = sum(1.0 for r in all_rocks if r.alignment_partners) / len(all_rocks)
        # Sparsity: prefer few strong rocks over many weak ones.
        n = len(all_rocks)
        sparsity = 1.0 / (1.0 + max(0.0, n - 4) * 0.25)
        score = 0.45 * persist + 0.35 * align + 0.20 * sparsity
        return max(0.0, min(1.0, score))

    # ─── internal: ThoughtBus emission ─────────────────────────

    def _bus_lazy(self):
        """Resolve and cache the ThoughtBus singleton on first publish.

        The publish flag is checked FIRST: publish_to_bus=False must silence
        the observer even when a bus instance was injected at construction —
        the old order let the injected bus bypass the disable switch.
        """
        if not self._publish:
            return None
        if self._bus is not None:
            return self._bus
        try:
            from aureon.core.aureon_thought_bus import get_thought_bus
            self._bus = get_thought_bus()
        except Exception as exc:
            logger.debug("ThoughtBus unavailable; observer running silent: %s", exc)
            self._publish = False
            self._bus = None
        return self._bus

    def _emit(self, event_kind: str, rock: Rock) -> None:
        """Publish a RockEvent envelope. Failures are debug-logged only."""
        ev = RockEvent(event=event_kind, rock=rock)  # type: ignore[arg-type]
        self._n_events_emitted += 1
        bus = self._bus_lazy()
        if bus is None:
            return
        try:
            bus.publish(
                topic="harmonic.observer.rock",
                payload=ev.to_dict(),
                source="harmonic_observer",
            )
        except Exception as exc:
            logger.debug("ThoughtBus publish failed (%s): %s", event_kind, exc)
