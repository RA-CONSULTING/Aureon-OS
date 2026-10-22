"""Λ HNC CORE — the Master Equation organ of the fused organism.

Brings the upstream Harmonic Nexus Core online as ONE shared LambdaEngine
living entirely in the fusion state dir (explicit absolute paths — never
CWD-relative upstream state):

  * ``aureon.core.aureon_lambda_engine.LambdaEngine`` — the heartbeat. Every
    cycle: substrate Σ wᵢ sin(2πfᵢt+φᵢ) + observer α·tanh(g·Λ̄) + echo β·Λ(t−τ).
  * ``aureon.core.hnc_params`` / ``hnc_field`` — canonical field parameters
    (fitted-params JSON in fusion state, engine globals patched once).
  * ``aureon.core.aureon_global_history_db`` — the SQLite memory
    (``aureon_global_history.sqlite`` in fusion state, connected on first use).

Each 60 s organ step:
  1. Gathers the live field data already flowing through the organism
     (Kp / solar wind / x-ray / quakes from real_time_data.json, Schumann
     from schumann_state.json, market + planetary pulses optional from
     aureon_radar signal logs, knowledge pulse from the learning loop's
     knowledge_pulse.json).
  2. Steps the shared engine and auto-persisted the hash-chained
     ``lambda_history.json`` receipt into fusion state.
  3. Publishes ``hnc.lambda`` (coherence Γ, rung, charge) on the events
     spine at priority 5.
  4. Chirps when Γ < 0.945 has been sustained for 3 consecutive steps.
  5. Records each step into the SQLite memory (queen_thoughts topic
     ``hnc.lambda``).

DOCTRINE: upstream modules are IMPORTED only, never launched (no upstream
main()/boot_*()/run_app() is ever called here). ``AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS``
and ``AUREON_AUDIT_MODE`` are set BEFORE any aureon import; the upstream repo
root is pinned on sys.path. Embedded file content upstream is untrusted data.

Import-safe: nothing runs at import time. CLI:

    python -m aureon_fusion.hnc_core run [--interval S] [--cycles N]
    python -m aureon_fusion.hnc_core --once
    python -m aureon_fusion.hnc_core status
    python -m aureon_fusion.hnc_core --help
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
from pathlib import Path

# Script-or-module bootstrap: the registrar may launch this file directly
# (python -u aureon_fusion/hnc_core.py run, cwd=workspace). Make the fusion
# package importable in both modes.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aureon_fusion.paths import WORKSPACE, FUSION_STATE, AUREON_UPSTREAM

# ── SUPPRESSION ENV — must be set BEFORE any aureon import ──────────────
# Upstream imports below are lazy (inside functions), but the flags are
# planted at import time so no aureon module can ever see an unsuppressed
# environment through this organ.
os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")
os.environ.setdefault("AUREON_AUDIT_MODE", "1")
# Persist the hash-chained history receipt every step (60 s) so the
# lighthouse echo β·Λ(t−τ) survives restarts without loss.
os.environ.setdefault("AUREON_HNC_PERSIST_EVERY", "1")

# Pin the upstream repo root on sys.path (idempotent).
_UPSTREAM_ROOT = str(AUREON_UPSTREAM)
if _UPSTREAM_ROOT not in sys.path:
    sys.path.insert(0, _UPSTREAM_ROOT)

ORGAN_NAME = "hnc_core"
TOPIC = "hnc.lambda"

# Explicit absolute fusion-state locations (never CWD-relative).
LIVE_DATA_PATH = WORKSPACE / "real_time_data.json"          # Kp / solar wind / x-ray / quakes
SCHUMANN_STATE_PATH = WORKSPACE / "schumann_state.json"     # Schumann sensor state
RADAR_SIGNALS_PATH = WORKSPACE / "aureon_radar" / "fused_signals.jsonl"  # prices optional
PLANETARY_SIGNALS_PATH = (WORKSPACE / "aureon_radar" / "planetary_signals.jsonl")  # planetary band
KNOWLEDGE_PULSE_PATH = FUSION_STATE / "knowledge_pulse.json"  # learning-loop telemetry
LAMBDA_HISTORY_PATH = FUSION_STATE / "lambda_history.json"
FITTED_PARAMS_PATH = FUSION_STATE / "hnc_fitted_params.json"
HISTORY_DB_PATH = FUSION_STATE / "aureon_global_history.sqlite"
CORE_STATE_PATH = FUSION_STATE / "hnc_core_state.json"

GAMMA_TARGET = 0.945          # minimum coherence for a stable timeline
CHIRP_STREAK = 3              # sustained low-Γ steps before chirping
DEFAULT_INTERVAL = 60.0       # organ step period, seconds
SOURCE_RECEIPT_IDS = ("aureon_fusion:hnc_core",)

# Freshness gates (fail-closed): stale inputs are never ingested at full
# confidence. The live-data feeder and the Schumann daemon both publish on
# a 60 s cadence; entries older than STALE_FACTOR × that cadence are
# degraded (real data: confidence halved) or dropped (non-real: refused).
# Radar fusion signals older than RADAR_SIGNAL_MAX_AGE_S count as NO SIGNAL
# (neutral) — never as a live market pulse.
FEEDER_INTERVAL_S = 60.0
SCHUMANN_INTERVAL_S = 60.0
STALE_FACTOR = 2.0
RADAR_SIGNAL_MAX_AGE_S = 600.0

# BUGWATCH-4: the kp / x-ray / solar-wind upstream sources publish on a
# ~300 s cadence, but the file-level window above (2×60 s = 120 s) marked
# healthy real data permanently stale and halved its confidence. These
# per-source windows match the actual source cadence; staleness degrades
# CONFIDENCE only — the reading value is never altered.
SOURCE_STALE_WINDOW_S = 600.0       # kp / xray / solar / quakes
PLANETARY_SIGNAL_MAX_AGE_S = 600.0  # planetary band
KNOWLEDGE_PULSE_WINDOW_S = 180.0    # knowledge pulse feeder cadence

# ── singletons (lazy; one shared field, one shared memory) ──────────────
_ENGINE = None
_DB_CONN = None
_LOW_GAMMA_STREAK = 0


# ───────────────────────────── upstream bridges ────────────────────────────

def get_engine():
    """The ONE shared LambdaEngine, state pinned into fusion state dir."""
    global _ENGINE
    if _ENGINE is None:
        # hnc_params first so fitted fusion-state params patch the engine
        # globals (ALPHA/G/BETA/TAU/DELTA_T) before any step.
        from aureon.core import hnc_params

        hnc_params.apply_to_lambda_engine(hnc_params.load_params(FITTED_PARAMS_PATH))
        # Import the canonical-field module alongside the engine so the
        # singleton is the single place the field is read/written. Its
        # freshness gate fails closed (no upstream daemon runs in fusion).
        from aureon.core import hnc_field  # noqa: F401  (canonical field API)

        from aureon.core.aureon_lambda_engine import LambdaEngine

        _ENGINE = LambdaEngine(state_path=LAMBDA_HISTORY_PATH)
    return _ENGINE


def read_canonical_field():
    """Delegate to upstream hnc_field.read_canonical_field, guarded.

    Returns the upstream CanonicalField (usually unavailable in fusion —
    no upstream HNC daemon pulses here — and its freshness gate correctly
    refuses stale rows). The fusion-side probes in ``gather_readings``
    enforce the same doctrine: stale feeder/Schumann entries are degraded
    or dropped, and a stale radar signal is no signal at all. Never raises.
    """
    try:
        get_engine()
        from aureon.core.hnc_field import read_canonical_field as _read

        return _read()
    except Exception:
        return None


def get_history_db():
    """The SQLite memory: explicit absolute path in fusion state dir,
    schema ensured, connected on first use. Never raises."""
    global _DB_CONN
    if _DB_CONN is None:
        from aureon.core import aureon_global_history_db as ghdb

        _DB_CONN = ghdb.connect(str(HISTORY_DB_PATH))
    return _DB_CONN


# ───────────────────────────── input sensing ───────────────────────────────

def _load_json(path: Path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None


def _finite(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _age_of_timestamp(value) -> float | None:
    """Age in seconds of an ISO-8601 timestamp string, or None when the
    value is missing/unparseable. Naive timestamps are read as UTC."""
    if not value or not isinstance(value, str):
        return None
    from datetime import datetime, timezone

    text = value.strip()
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return max(0.0, time.time() - parsed.timestamp())


def gather_readings():
    """Live organism data → (SubsystemReading list, provenance meta).

    Kp / solar wind / x-ray / quakes come from the feeder's
    real_time_data.json; Schumann from schumann_state.json; the market pulse
    (optional) from the radar's fused_signals.jsonl; the planetary band from
    the radar's planetary_signals.jsonl; the knowledge pulse from the
    learning loop's knowledge_pulse.json. Every probe fails closed — a dark
    sensor simply contributes nothing — and every input is freshness-gated:
    entries older than their per-source window (or with no timestamp at
    fall back to the file-level clock, and no timestamp at all) are
    degraded, never ingested at full confidence, and radar signals older
    than RADAR_SIGNAL_MAX_AGE_S are no signal at all (neutral), not a live
    market pulse.

    CALIBRATION (deliberate): Γ = 1 − σ/μ over raw reading VALUES, and the
    existing cluster sits at ~0.35–0.45. The quakes / knowledge_pulse /
    planetary normalizations below are therefore anchored so a quiet,
    median world lands near 0.40 — inside the cluster band. Real deviations
    still move Γ honestly (tanh saturates at ±0.10–0.12 around the anchor);
    this is agreeing-sensor calibration, not value fabrication.
    """
    from aureon.core.aureon_lambda_engine import SubsystemReading

    readings = []
    meta: dict = {}

    live = _load_json(LIVE_DATA_PATH) or {}
    summary = live.get("summary") or {}
    live_age = _age_of_timestamp(live.get("timestamp"))

    def _feeder_stale(entry_ts, window_s: float | None = None) -> bool:
        """True when an entry (or the whole file as fallback clock) is older
        than its freshness window — or carries no timestamp at all. Real-data
        sources on the ~300 s upstream cadence (kp / xray / solar / quakes)
        get the wider SOURCE_STALE_WINDOW_S (BUGWATCH-4) so healthy readings
        are not mis-marked stale; the default stays the narrow
        2× FEEDER_INTERVAL_S file-level window."""
        age = _age_of_timestamp(entry_ts)
        if age is None:
            age = live_age
        limit = window_s if window_s is not None else STALE_FACTOR * FEEDER_INTERVAL_S
        return age is None or age > limit

    kp = summary.get("kp") or {}
    kp_est = _finite(kp.get("estimated_kp", kp.get("kp_index")))
    if kp_est is not None:
        kp_stale = _feeder_stale(kp.get("timestamp"), SOURCE_STALE_WINDOW_S)
        readings.append(SubsystemReading(
            name="kp_index", value=_clamp01(kp_est / 9.0),
            confidence=0.425 if kp_stale else 0.85,
            state=str(kp.get("kp", "?"))))
        meta["kp"] = round(kp_est, 3)
        if kp_stale:
            meta["kp_stale"] = True

    schumann = _load_json(SCHUMANN_STATE_PATH) or {}
    activity = _finite(schumann.get("activity_index"))
    if activity is not None:
        real = bool(schumann.get("real_data"))
        sch_age = _age_of_timestamp(schumann.get("timestamp"))
        sch_stale = (sch_age is None
                     or sch_age > STALE_FACTOR * SCHUMANN_INTERVAL_S)
        if sch_stale and not real:
            pass  # stale non-real data is refused entirely (fail-closed)
        else:
            confidence = 0.8 if real else 0.4
            if sch_stale:
                confidence *= 0.5  # stale real data: degraded, never full
            readings.append(SubsystemReading(
                name="schumann_resonance", value=_clamp01(activity / 100.0),
                confidence=confidence,
                state=str(schumann.get("activity_label", "?"))))
            meta["schumann_hz"] = schumann.get("frequency_hz")
            meta["schumann_real"] = real
            if sch_stale:
                meta["schumann_stale"] = True

    solar = summary.get("solar_wind") or {}
    speed = _finite(solar.get("speed"))
    if speed is not None:
        solar_stale = _feeder_stale(solar.get("time_tag"), SOURCE_STALE_WINDOW_S)
        readings.append(SubsystemReading(
            name="solar_wind", value=_clamp01(speed / 1000.0),
            confidence=0.35 if solar_stale else 0.7,
            state=f"density {solar.get('density', '?')} n/cc"))
        meta["solar_wind_speed"] = round(speed, 1)
        if solar_stale:
            meta["solar_wind_stale"] = True

    xray = summary.get("xray") or {}
    flux = _finite(xray.get("flux"))
    if flux is not None and flux > 0:
        xray_stale = _feeder_stale(xray.get("time_tag"), SOURCE_STALE_WINDOW_S)
        # log-scale: 1e-10 → 0.0, 1e-4 → 1.0 (typical background ~1e-7)
        readings.append(SubsystemReading(
            name="xray_flux", value=_clamp01((math.log10(flux) + 10.0) / 6.0),
            confidence=0.3 if xray_stale else 0.6,
            state=str(xray.get("energy", "?"))))
        if xray_stale:
            meta["xray_stale"] = True

    # Seismic pulse — USGS quake count from the same live-data summary. The
    # entry carries no timestamp of its own, so the file-level timestamp is
    # the fallback clock (same fallback doctrine as _feeder_stale). Count is
    # read defensively: the numeric "count" field first, a list payload's
    # length as fallback, anything else = no reading. Normalization anchors
    # count ≈ 8 at the 0.40 cluster centre (tanh saturates at 0.30/0.50).
    quakes = summary.get("quakes")
    if isinstance(quakes, dict):
        quake_count = _finite(quakes.get("count"))
        if quake_count is None:
            for key in ("quakes", "list", "features", "recent"):
                payload = quakes.get(key)
                if isinstance(payload, list):
                    quake_count = float(len(payload))
                    break
        if quake_count is not None:
            quake_stale = _feeder_stale(quakes.get("timestamp"),
                                        SOURCE_STALE_WINDOW_S)
            readings.append(SubsystemReading(
                name="seismic_quakes",
                value=_clamp01(0.40 + 0.10 * math.tanh((quake_count - 8.0) / 6.0)),
                confidence=0.3 if quake_stale else 0.6,
                state=f"count {int(quake_count)}"))
            meta["quake_count"] = int(quake_count)
            if quake_stale:
                meta["quakes_stale"] = True

    # Knowledge pulse — the sovereign learning loop's internal telemetry,
    # published by the knowledge_pulse_feeder door into knowledge_pulse.json
    # (schema: {"timestamp", "pulse" 0..1, "components"}). pulse 0.5 maps to
    # the 0.40 cluster centre; deviations move Γ honestly. Missing or
    # malformed file = NO reading (fail-closed); a stale pulse is degraded,
    # never refused — this is internal telemetry, not an external feed.
    pulse_doc = _load_json(KNOWLEDGE_PULSE_PATH)
    if isinstance(pulse_doc, dict):
        pulse = _finite(pulse_doc.get("pulse"))
        if pulse is not None:
            pulse_age = _age_of_timestamp(pulse_doc.get("timestamp"))
            pulse_stale = (pulse_age is None
                           or pulse_age > KNOWLEDGE_PULSE_WINDOW_S)
            readings.append(SubsystemReading(
                name="knowledge_pulse",
                value=_clamp01(0.40 + 0.12 * (pulse - 0.5)),
                confidence=0.3 if pulse_stale else 0.65,
                state=f"pulse {pulse:.3f}"))
            meta["knowledge_pulse"] = round(pulse, 4)
            if pulse_stale:
                meta["knowledge_pulse_stale"] = True

    # Planetary band — the radar's planetary signal log (offline, local
    # file). Activity = number of signals in the last hour; normalized so
    # n ≈ 5 anchors at the 0.40 cluster centre (tanh saturates 0.30/0.50).
    # Freshness-gated like the market pulse: last-line timestamp with file
    # mtime as the fallback clock. When no line carries any parseable
    # timestamp the line count itself is the activity (defensive fallback).
    try:
        lines = []
        with open(PLANETARY_SIGNALS_PATH, "r", encoding="utf-8",
                  errors="replace") as fh:
            lines = [line for line in fh if line.strip()]
        if lines:
            try:
                sig_doc = json.loads(lines[-1])
            except json.JSONDecodeError:
                sig_doc = None
            sig_age = _age_of_timestamp(
                sig_doc.get("timestamp") if isinstance(sig_doc, dict) else None)
            if sig_age is None:
                try:
                    sig_age = time.time() - PLANETARY_SIGNALS_PATH.stat().st_mtime
                except OSError:
                    sig_age = None
            planetary_stale = (sig_age is None
                               or sig_age > PLANETARY_SIGNAL_MAX_AGE_S)
            n_recent, saw_ts = 0, False
            for line in lines[-200:]:
                try:
                    doc = json.loads(line)
                except json.JSONDecodeError:
                    continue
                age = _age_of_timestamp(
                    doc.get("timestamp") if isinstance(doc, dict) else None)
                if age is not None:
                    saw_ts = True
                    if age <= 3600.0:
                        n_recent += 1
            n_signals = n_recent if saw_ts else len(lines[-200:])
            readings.append(SubsystemReading(
                name="planetary_band",
                value=_clamp01(0.40 + 0.10 * math.tanh((n_signals - 5.0) / 4.0)),
                confidence=0.25 if planetary_stale else 0.55,
                state=f"{n_signals} signals last hour"))
            meta["planetary_signals_hour"] = n_signals
            if planetary_stale:
                meta["planetary_stale"] = True
    except Exception:
        pass

    # Optional market pulse — last radar fusion signal (offline, local file).
    # Freshness-gated: a signal whose timestamp is missing or older than
    # RADAR_SIGNAL_MAX_AGE_S is NO SIGNAL (neutral), never served as a
    # live pulse; the file mtime is the fallback clock.
    try:
        last_line = ""
        with open(RADAR_SIGNALS_PATH, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if line.strip():
                    last_line = line
        if last_line:
            sig = json.loads(last_line)
            sig_age = _age_of_timestamp(sig.get("timestamp"))
            if sig_age is None:
                try:
                    sig_age = time.time() - RADAR_SIGNALS_PATH.stat().st_mtime
                except OSError:
                    sig_age = None
            if sig_age is not None and sig_age <= RADAR_SIGNAL_MAX_AGE_S:
                score = _finite(sig.get("fusion_score"))
                if score is not None:
                    conf = _finite(sig.get("confidence"))
                    readings.append(SubsystemReading(
                        name="market_radar", value=_clamp01(score),
                        confidence=_clamp01(conf if conf is not None else 0.5),
                        state=str(sig.get("symbol", "radar"))))
                    meta["radar_symbol"] = sig.get("symbol")
            else:
                meta["radar_stale"] = True  # no signal: fail closed
    except Exception:
        pass

    return readings, meta


# ───────────────────────────── memory write ────────────────────────────────

def _record_memory(payload: dict) -> None:
    """One hnc.lambda step → SQLite memory (queen_thoughts). Best-effort."""
    try:
        from aureon.core import aureon_global_history_db as ghdb

        db = get_history_db()
        ts_ms = int(payload["timestamp"] * 1000)
        ghdb.insert_queen_thought(db, {
            "thought_id": f"hnc_core:{payload['step']}:{ts_ms}",
            "source": ORGAN_NAME,
            "topic": TOPIC,
            "thought_text": (
                f"Λ={payload['lambda_t']:.6f} Γ={payload['coherence_gamma']:.4f} "
                f"rung={payload['rung']} ψ={payload['consciousness_psi']:.4f} "
                f"life={payload['symbolic_life_score']:.4f}"
            ),
            "confidence": round(_clamp01(payload["coherence_gamma"]), 6),
            "ts_ms": ts_ms,
            "raw_json": json.dumps(payload, ensure_ascii=False),
        })
        db.commit()
    except Exception:
        pass  # memory must never break the heartbeat


def _save_core_state(payload: dict) -> None:
    try:
        tmp = CORE_STATE_PATH.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
        os.replace(tmp, CORE_STATE_PATH)
    except Exception:
        pass


# ───────────────────────────── the step ────────────────────────────────────

def step_once(publish: bool = True):
    """One heartbeat of the Master Equation. Returns (state, payload).

    Steps the shared engine on the live field data, auto-persists the
    hash-chained lambda_history.json receipt, mirrors the step into the
    SQLite memory, and publishes ``hnc.lambda`` at priority 5. Chirps once
    Γ < 0.945 has been sustained for 3 consecutive steps.
    """
    global _LOW_GAMMA_STREAK
    engine = get_engine()
    readings, meta = gather_readings()

    state = engine.step(
        readings=readings,
        source_receipt_ids=SOURCE_RECEIPT_IDS,
        auto_persist=True,
    )

    payload = {
        "organ": ORGAN_NAME,
        "topic": TOPIC,
        "step": state.step,
        "timestamp": state.timestamp,
        "lambda_t": state.lambda_t,            # the charge
        "coherence_gamma": state.coherence_gamma,  # Γ
        "coherence_phi": state.coherence_phi,
        "quality_factor": state.quality_factor,
        "consciousness_psi": state.consciousness_psi,
        "consciousness_level": state.consciousness_level,
        "rung": state.consciousness_level,
        "charge": state.lambda_t,
        "symbolic_life_score": state.symbolic_life_score,
        "effective_gain": state.effective_gain,
        "substrate": state.substrate,
        "observer": state.observer,
        "echo": state.echo,
        "history_load_status": engine.history_load_status,
        "input_count": len(readings),
        "inputs": meta,
    }

    _save_core_state(payload)
    _record_memory(payload)

    # ── events spine (priority 5) ──
    chirped = False
    if publish:
        from aureon_fusion import events

        events.publish_event(ORGAN_NAME, TOPIC, payload, priority=5)

        if state.coherence_gamma < GAMMA_TARGET:
            _LOW_GAMMA_STREAK += 1
        else:
            _LOW_GAMMA_STREAK = 0
        if _LOW_GAMMA_STREAK == CHIRP_STREAK:
            events.chirp(ORGAN_NAME, "hnc_low_coherence", 6, {
                "gamma": state.coherence_gamma,
                "target": GAMMA_TARGET,
                "sustained_steps": _LOW_GAMMA_STREAK,
                "rung": state.consciousness_level,
                "step": state.step,
            })
            chirped = True
    payload["_chirped"] = chirped
    return state, payload


# ───────────────────────────── organ loop ──────────────────────────────────

def run(interval: float = DEFAULT_INTERVAL, cycles: int | None = None,
        publish: bool = True) -> int:
    """Continuous organ mode: one Master-Equation step every `interval` s.

    Exits cleanly on KeyboardInterrupt with a final history commit. Never
    leaves anything running: the loop IS the process, and it dies with it.
    """
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    engine = get_engine()
    print("═" * 78)
    print(f"Λ HNC CORE — Master Equation organ online (history: "
          f"{LAMBDA_HISTORY_PATH})")
    print(f"  field data : {LIVE_DATA_PATH.name} + {SCHUMANN_STATE_PATH.name}"
          f" (+ radar pulse optional), step every {interval:.0f}s")
    print(f"  memory     : {HISTORY_DB_PATH}")
    print(f"  spine      : '{TOPIC}' @ priority 5, chirp < Γ{GAMMA_TARGET} ×{CHIRP_STREAK}")
    print("═" * 78)
    count = 0
    try:
        while True:
            state, payload = step_once(publish=publish)
            flag = " ⚠LOW-Γ" if payload["_chirped"] else ""
            print(f"Λ step {state.step:<6} Λ={state.lambda_t:+.5f} "
                  f"Γ={state.coherence_gamma:.4f} ψ={state.consciousness_psi:.4f} "
                  f"rung={state.consciousness_level:<12} "
                  f"life={state.symbolic_life_score:.4f} "
                  f"inputs={payload['input_count']}{flag}", flush=True)
            count += 1
            if cycles is not None and count >= cycles:
                break
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nΛ HNC CORE interrupted — committing history and leaving.")
    finally:
        try:
            receipt = engine.save_history(source_receipt_ids=SOURCE_RECEIPT_IDS)
            if receipt:
                print(f"Λ history committed: {receipt.get('receipt_id')}")
        except Exception as exc:
            print(f"Λ final history commit skipped: {exc}")
    return 0


# ───────────────────────────── status ──────────────────────────────────────

def status() -> dict:
    """Snapshot for the registrar / heartbeat: engine + last step + memory."""
    engine = get_engine()
    last = _load_json(CORE_STATE_PATH) or {}
    receipt = engine.last_history_receipt or {}
    db_ok = False
    try:
        conn = get_history_db()
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM queen_thoughts WHERE topic = ?",
            (TOPIC,),
        ).fetchone()
        db_ok = row is not None
        db_rows = int(row["n"]) if row is not None else 0
    except Exception:
        db_rows = -1
    return {
        "organ": ORGAN_NAME,
        "engine_step": engine.get_step(),
        "history_path": str(LAMBDA_HISTORY_PATH),
        "history_load_status": engine.history_load_status,
        "history_receipt_id": receipt.get("receipt_id"),
        "history_commit_error": engine.last_history_commit_error,
        "params_path": str(FITTED_PARAMS_PATH),
        "memory_db": str(HISTORY_DB_PATH),
        "memory_rows": db_rows,
        "memory_ok": db_ok,
        "low_gamma_streak": _LOW_GAMMA_STREAK,
        "last_step": last.get("step"),
        "last_gamma": last.get("coherence_gamma"),
        "last_rung": last.get("rung"),
        "last_charge": last.get("charge"),
        "last_inputs": last.get("inputs"),
        "last_ts": last.get("timestamp"),
    }


# ───────────────────────────── CLI ─────────────────────────────────────────

def _print_help() -> None:
    print("usage: python -m aureon_fusion.hnc_core "
          "[run [--interval S] [--cycles N] | --once | status | --help]")
    print()
    print("  run                continuous organ mode (60s step; Ctrl+C exits)")
    print("  run --interval S   override the step period")
    print("  run --cycles N     stop after N steps (smoke/dry-run)")
    print("  --once             one Master-Equation step, then exit")
    print("  status             engine/memory snapshot without stepping")
    print("  --help             this message")


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        _print_help()
        return 0

    verb = argv[0]
    if verb == "run":
        interval = DEFAULT_INTERVAL
        cycles = None
        i = 1
        while i < len(argv):
            if argv[i] == "--interval" and i + 1 < len(argv):
                interval = float(argv[i + 1])
                i += 2
            elif argv[i] == "--cycles" and i + 1 < len(argv):
                cycles = int(argv[i + 1])
                i += 2
            else:
                print(f"unknown run arg: {argv[i]}", file=sys.stderr)
                return 2
        return run(interval=interval, cycles=cycles)
    if verb in ("--once", "once"):
        state, payload = step_once(publish=True)
        print(json.dumps({k: v for k, v in payload.items() if not k.startswith("_")},
                         indent=2, ensure_ascii=False))
        return 0
    if verb == "status":
        print(json.dumps(status(), indent=2, ensure_ascii=False))
        return 0
    print(f"unknown verb: {verb} (expected run | --once | status | --help)",
          file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
