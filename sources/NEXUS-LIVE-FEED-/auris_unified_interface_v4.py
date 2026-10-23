"""Auris Unified Interface v4 backend with bioscan ingestion and analytics."""

from __future__ import annotations

import datetime as _dt
import hashlib
import importlib
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Tuple

import numpy as np
from fastapi import FastAPI, Query
from pydantic import BaseModel, Field, root_validator

from lattice_integration import (
    LatticeIntegrationConfig,
    LatticeIntegrator,
    LatticeState,
    SymbolicCompiler,
    UnityTensorField,
)

# WebSocket broadcaster (from auris_ws_patch). Safe fallback if not present.
try:
    from auris_ws_patch import emit_event  # async: await emit_event({...})
except Exception:
    async def emit_event(_evt: dict):
        return  # no-op fallback for environments without WS


APP_TITLE = "AURIS Unified Interface"
APP_VERSION = "4.0"

DATA_DIR = Path("data")
BIOSCAN_DIR = DATA_DIR / "bioscans"
DATA_DIR.mkdir(parents=True, exist_ok=True)
BIOSCAN_DIR.mkdir(parents=True, exist_ok=True)

UNITY_TENSOR_PATH = DATA_DIR / "unity_tensorfield_samples.json"
UNITY_TENSOR_FIELD = UnityTensorField.from_path(UNITY_TENSOR_PATH)

_SYMBOLIC_COMPILER = SymbolicCompiler(
    keyword_map={
        "stabilize": (432.0, 1.05),
        "stabilise": (432.0, 1.05),
        "harmonize": (528.0, 0.95),
        "harmonise": (528.0, 0.95),
        "protect": (396.0, 1.25),
        "free": (639.0, 1.10),
        "will": (741.0, 1.18),
        "balance": (444.0, 1.02),
        "love": (528.0, 0.92),
        "prime": (936.0, 1.40),
        "guardian": (384.0, 1.30),
        "anchor": (672.0, 1.05),
    }
)

_LATTICE_CONFIG = LatticeIntegrationConfig()
LATTICE_INTEGRATOR = LatticeIntegrator(
    compiler=_SYMBOLIC_COMPILER,
    tensor_field=UNITY_TENSOR_FIELD,
    config=_LATTICE_CONFIG,
)

LATTICE_LOG_PATH = DATA_DIR / "lattice_integration_log.jsonl"

_requests_spec = importlib.util.find_spec("requests")
if _requests_spec:
    import requests  # type: ignore
else:  # pragma: no cover - requests is optional at runtime
    requests = None  # type: ignore

MESH_SERVICE_BASE_URL = os.environ.get("MESH_SERVICE_BASE_URL") or os.environ.get(
    "AURIS_MESH_BASE_URL"
) or os.environ.get("AURIS_BACKEND_BASE_URL")


def clip01(value: float) -> float:
    """Return ``value`` clipped to the inclusive ``[0, 1]`` range."""

    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    return float(max(0.0, min(1.0, numeric)))


def _append_lattice_log(entry: Mapping[str, Any]) -> None:
    """Append ``entry`` to the lattice integration audit log."""

    record = dict(entry)
    record.setdefault(
        "timestamp",
        _dt.datetime.utcnow().replace(tzinfo=_dt.timezone.utc).isoformat(),
    )
    try:
        with LATTICE_LOG_PATH.open("a", encoding="utf-8") as handle:
            json.dump(record, handle)
            handle.write("\n")
    except OSError:
        return


class BioScanPayload(BaseModel):
    """Canonical bioscan payload accepted by the unified interface."""

    user: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)
    streams: Dict[str, Any] = Field(default_factory=dict)


class LatticeDriveRequest(BaseModel):
    """Guardian–Anchor lattice drive payload."""

    intent: str = Field(..., description="Intent string interpreted by the symbolic compiler.")
    cp: float = Field(..., alias="C_p", description="Symbolic memory correlation C_p(t).")
    lambda_value: float = Field(..., alias="lambda", description="Instant coherence Λ(t).")
    phi_ga: float = Field(..., alias="Phi_GA", description="Guardian–Anchor phase gap Φ_GA(t).")
    dissonance: float = Field(..., alias="D", description="Dissonance index D(t).")
    x_norm: float = Field(..., description="Current lattice state norm |x|.")
    x_safe: float | None = Field(None, description="Safe lattice state norm |x|_safe.")
    phi: float = Field(..., description="Phase coordinate φ for tensor sampling.")
    kappa: float = Field(..., description="Curvature coordinate κ for tensor sampling.")
    psi: float = Field(..., description="Phase coordinate ψ for tensor sampling.")
    psi_max: float = Field(..., alias="Psi_max", description="Observed Ψ_max envelope.")
    psi_safe: float | None = Field(None, alias="Psi_safe", description="Safe Ψ threshold.")
    previous_drive: float | None = Field(0.0, alias="u_prev", description="Previous drive sample.")
    yield_metric: float | None = Field(None, alias="Y_c", description="Optional cumulative yield Y_c(t).")
    timestamp: str | None = Field(None, description="Client provided timestamp for logging.")

    @root_validator(pre=True)
    def _normalise_aliases(cls, values: Dict[str, Any]) -> Dict[str, Any]:  # type: ignore[override]
        if "Lambda" in values and "lambda" not in values:
            values["lambda"] = values["Lambda"]
        if "Psi" in values and "Psi_max" not in values:
            values["Psi_max"] = values["Psi"]
        if "u_previous" in values and "u_prev" not in values:
            values["u_prev"] = values["u_previous"]
        return values

    class Config:
        allow_population_by_field_name = True
        allow_population_by_alias = True


app = FastAPI(title=APP_TITLE, version=APP_VERSION)


def _coerce_float(value: Any, default: float | None = None) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize(value: float | None, *, lower: float, upper: float, fallback: float) -> float:
    if value is None:
        return fallback
    if upper <= lower:
        return fallback
    scaled = (value - lower) / (upper - lower)
    return clip01(scaled)


def normalize_features(payload: Mapping[str, Any]) -> Dict[str, float]:
    """Extract and normalize the key biometrics from the raw payload."""

    streams = payload.get("streams") or {}

    ecg = ((streams.get("ECG") or {}).get("payload") or {}).get("features") or {}
    hrv_rmssd = _coerce_float(ecg.get("hrv_rmssd_ms"))
    hr_bpm = _coerce_float(ecg.get("hr_bpm"))

    eeg_payload = ((streams.get("EEG") or {}).get("payload") or {})
    eeg_phase_lock = _coerce_float(eeg_payload.get("phase_lock_to_schumann"))
    bands = eeg_payload.get("bands") or {}
    alpha_rel = _coerce_float((bands.get("alpha") or {}).get("rel"))
    gamma_rel = _coerce_float((bands.get("gamma") or {}).get("rel"))

    resp = ((streams.get("RESP") or {}).get("payload") or {})
    resp_bpm = _coerce_float(resp.get("rr_bpm"))

    gsr_payload = ((streams.get("GSR") or {}).get("payload") or {})
    tonic_us = _coerce_float(gsr_payload.get("tonic_us"))
    phasic_events = _coerce_float(gsr_payload.get("phasic_events"), 0.0) or 0.0

    temp_payload = ((streams.get("TEMP") or {}).get("payload") or {})
    temp_values = temp_payload.get("celsius") or []
    temp_c = _coerce_float(temp_values[0] if temp_values else None)

    spo2_payload = ((streams.get("SPO2") or {}).get("payload") or {})
    spo2_values = spo2_payload.get("percent") or []
    spo2_pct = _coerce_float(spo2_values[0] if spo2_values else None)

    bp_payload = ((streams.get("BP") or {}).get("payload") or {})
    map_bp = _coerce_float(bp_payload.get("map"))

    schumann_payload = ((streams.get("SCHUMANN") or {}).get("payload") or {})
    schumann_freqs = schumann_payload.get("freq_hz") or []
    schumann_amp = schumann_payload.get("amplitude") or []
    schumann_drift = _coerce_float(schumann_payload.get("drift_hz"))

    features = {
        "hr_norm": _normalize(hr_bpm, lower=48.0, upper=120.0, fallback=0.72),
        "hrv_norm": _normalize(hrv_rmssd, lower=18.0, upper=130.0, fallback=0.64),
        "phase_lock": clip01(eeg_phase_lock if eeg_phase_lock is not None else 0.55),
        "alpha_rel": clip01(alpha_rel if alpha_rel is not None else 0.35),
        "gamma_rel": clip01(gamma_rel if gamma_rel is not None else 0.12),
        "resp_norm": _normalize(resp_bpm, lower=4.0, upper=16.0, fallback=0.65),
        "gsr_norm": _normalize(tonic_us, lower=1.5, upper=25.0, fallback=0.58),
        "gsr_events": clip01(phasic_events / 6.0),
        "temp_norm": _normalize(temp_c, lower=35.5, upper=37.8, fallback=0.62),
        "spo2_norm": _normalize(spo2_pct, lower=90.0, upper=100.0, fallback=0.94),
        "map_norm": _normalize(map_bp, lower=70.0, upper=105.0, fallback=0.66),
        "schumann_alignment": _normalize(
            float(np.mean(np.abs(np.array(schumann_freqs) - 7.83))) if schumann_freqs else None,
            lower=0.0,
            upper=1.2,
            fallback=0.55,
        ),
        "schumann_amplitude": _normalize(
            float(np.mean(schumann_amp)) if schumann_amp else None,
            lower=0.0,
            upper=1.5,
            fallback=0.60,
        ),
        "schumann_drift": clip01(1.0 - abs(schumann_drift) / 0.2) if schumann_drift is not None else 0.72,
    }

    return features


def layer_scores(features: Mapping[str, float]) -> Tuple[Dict[str, Dict[str, float]], Dict[str, float]]:
    """Compute layer scores and weight priors from normalized features."""

    hr_balance = 1.0 - abs(features["hr_norm"] - 0.7)
    crc_mu = clip01(0.55 * features["hrv_norm"] + 0.35 * hr_balance + 0.10 * features["resp_norm"])
    crc_sigma = 0.08 + 0.05 * (1.0 - features["hrv_norm"])

    nfc_mu = clip01(0.50 * features["phase_lock"] + 0.30 * features["schumann_drift"] + 0.20 * features["schumann_amplitude"])
    nfc_sigma = 0.07 + 0.05 * (1.0 - features["phase_lock"])

    peb_mu = clip01(
        0.40 * features["spo2_norm"]
        + 0.30 * features["temp_norm"]
        + 0.30 * (1.0 - abs(features["map_norm"] - 0.65))
    )
    peb_sigma = 0.06 + 0.06 * (1.0 - features["spo2_norm"])

    bhs_mu = clip01(
        0.50 * features["gsr_norm"] + 0.30 * (1.0 - features["gsr_events"]) + 0.20 * features["resp_norm"]
    )
    bhs_sigma = 0.07 + 0.05 * features["gsr_events"]

    pla_mu = clip01(
        0.45 * features["alpha_rel"] + 0.25 * (1.0 - features["gamma_rel"]) + 0.30 * features["phase_lock"]
    )
    pla_sigma = 0.05 + 0.05 * (1.0 - features["alpha_rel"])

    layer_map = {
        "crc": {"mu": crc_mu, "sigma": crc_sigma},
        "nfc": {"mu": nfc_mu, "sigma": nfc_sigma},
        "peb": {"mu": peb_mu, "sigma": peb_sigma},
        "bhs": {"mu": bhs_mu, "sigma": bhs_sigma},
        "pla": {"mu": pla_mu, "sigma": pla_sigma},
    }

    weight_prior = {
        "crc": 0.24,
        "nfc": 0.22,
        "peb": 0.18,
        "bhs": 0.16,
        "pla": 0.20,
    }

    return layer_map, weight_prior


def compute_bci(
    layers: Mapping[str, Mapping[str, float]],
    weights: Mapping[str, float],
) -> Tuple[float, Tuple[float, float]]:
    """Return the Brain Coherence Index and its 95% confidence interval."""

    total_weight = sum(weights.values()) or 1.0
    weighted_mu = 0.0
    weighted_var = 0.0
    for name, config in layers.items():
        weight = weights.get(name, 0.0)
        mu = float(config.get("mu", 0.0))
        sigma = float(config.get("sigma", 0.1))
        weighted_mu += weight * mu
        weighted_var += (weight ** 2) * (sigma ** 2)
    mu = weighted_mu / total_weight
    sigma = (weighted_var ** 0.5) / max(total_weight, 1e-6)
    ci_delta = 1.96 * sigma / (len(layers) ** 0.5 if layers else 1.0)
    ci_lo = clip01(mu - ci_delta)
    ci_hi = clip01(mu + ci_delta)
    return clip01(mu), (ci_lo, ci_hi)


def seal_record(
    user: Mapping[str, Any],
    context: Mapping[str, Any],
    layers: Mapping[str, Mapping[str, float]],
    bci: float,
    ci: Tuple[float, float],
) -> Dict[str, Any]:
    """Generate a deterministic seal for the bioscan record."""

    timestamp = context.get("timestamp_utc") or _dt.datetime.utcnow().replace(tzinfo=_dt.timezone.utc).isoformat()
    canonical_payload = {
        "user": user,
        "context": {**context, "timestamp_utc": timestamp},
        "layers": {name: dict(values) for name, values in layers.items()},
        "bci": bci,
        "confidence": list(ci),
    }
    serialized = json.dumps(canonical_payload, sort_keys=True, separators=(",", ":"))
    report_hash = hashlib.sha3_256(serialized.encode("utf-8")).hexdigest()
    return {
        "report_hash": report_hash,
        "generated_utc": timestamp,
        "payload_digest": hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
    }


@app.get("/status")
def status() -> Dict[str, Any]:
    """Return the backend status block."""

    return {
        "system": APP_TITLE,
        "version": APP_VERSION,
        "uptime_utc": _dt.datetime.utcnow().replace(tzinfo=_dt.timezone.utc).isoformat(),
        "bioscan_dir": str(BIOSCAN_DIR),
    }


@app.post("/lattice/drive")
async def lattice_drive(payload: LatticeDriveRequest) -> Dict[str, Any]:
    """Compute a lattice drive update and broadcast it to subscribers."""

    config = LATTICE_INTEGRATOR.config
    original_x_safe = config.x_safe
    original_psi_safe = config.psi_safe
    if payload.x_safe is not None:
        config.x_safe = float(payload.x_safe)
    if payload.psi_safe is not None:
        config.psi_safe = float(payload.psi_safe)

    try:
        state = LatticeState(
            intent=payload.intent,
            cp=clip01(payload.cp),
            coherence=max(0.0, float(payload.lambda_value)),
            phi_ga=float(payload.phi_ga),
            dissonance=max(0.0, float(payload.dissonance)),
            x_norm=max(0.0, float(payload.x_norm)),
            phi=float(payload.phi),
            kappa=float(payload.kappa),
            psi=float(payload.psi),
            psi_max=float(payload.psi_max),
            previous_drive=float(payload.previous_drive or 0.0),
            yield_metric=float(payload.yield_metric) if payload.yield_metric is not None else None,
        )
        result = LATTICE_INTEGRATOR.integrate(state)
    finally:
        config.x_safe = original_x_safe
        config.psi_safe = original_psi_safe

    timestamp = payload.timestamp or _dt.datetime.utcnow().replace(tzinfo=_dt.timezone.utc).isoformat()

    message_payload = {
        "timestamp": timestamp,
        "intent": payload.intent,
        "drive": result.drive,
        "waveform": result.waveform,
        "gain": result.gain,
        "tsv": result.tsv,
        "balance": {"value": result.balance_value, "terms": result.balance_terms},
        "sandbox": result.sandbox,
        "yield_metric": result.yield_metric,
        "cp": clip01(payload.cp),
        "lambda": float(payload.lambda_value),
        "phi_ga": float(payload.phi_ga),
        "dissonance": float(payload.dissonance),
    }

    _append_lattice_log(
        {
            "timestamp": timestamp,
            "intent": payload.intent,
            "drive": result.drive,
            "gain": result.gain,
            "tsv": result.tsv,
            "balance": result.balance_value,
            "balance_terms": result.balance_terms,
            "sandbox": result.sandbox,
            "cp": clip01(payload.cp),
            "lambda": float(payload.lambda_value),
            "phi_ga": float(payload.phi_ga),
            "dissonance": float(payload.dissonance),
            "x_norm": float(payload.x_norm),
            "psi_max": float(payload.psi_max),
        }
    )

    message = {"channel": "lattice:drive", "payload": message_payload}
    await emit_event(message)
    return message


@app.post("/bioscan/ingest")
async def ingest_bioscan(
    payload: BioScanPayload,
    mode: str = Query("meditative", enum=["clinical", "meditative", "field"]),
) -> Dict[str, Any]:
    data = payload.model_dump()

    # ---- normalize → layers → BCI (your existing logic) ----
    features = normalize_features(data)
    layers, weight_prior = layer_scores(features)
    bci, (ci_lo, ci_hi) = compute_bci(layers, weight_prior)

    # quality flag (unchanged)
    streams = data.get("streams", {})
    status_flag = "OK"
    for stream in streams.values():
        quality = (stream or {}).get("quality") or {}
        drop_pct = _coerce_float(quality.get("drop_pct"), 0.0) or 0.0
        if drop_pct > 0.2:
            status_flag = "LOW_QUALITY"
            break

    # seals + persistence (unchanged)
    context = data.get("context", {})
    seals = seal_record(data.get("user", {}), context, layers, bci, (ci_lo, ci_hi))
    os.makedirs(BIOSCAN_DIR, exist_ok=True)
    session_id = context.get("session_id") or "sess-" + _dt.datetime.utcnow().strftime("%Y%m%d%H%M%S")
    context = {**context, "session_id": session_id}
    raw_anchor = context.get("anchor_id") or data.get("anchor_id")
    if raw_anchor is None:
        raw_anchor = "gary.leckey"
    anchor_id = str(raw_anchor).strip() or "gary.leckey"
    context["anchor_id"] = anchor_id
    record = {
        "session_id": session_id,
        "mode": mode,
        "bci": bci,
        "bci_ci95": [ci_lo, ci_hi],
        "layer_scores": layers,
        "seals": seals,
        "status": status_flag,
        "user": data.get("user"),
        "context": context,
    }
    mesh_plan: Dict[str, Any]
    if requests is None:
        mesh_plan = {"error": "mesh_requests_unavailable"}
    else:
        mesh_base_url = (context.get("mesh_base_url") or MESH_SERVICE_BASE_URL or "").rstrip("/")
        if not mesh_base_url:
            mesh_plan = {"error": "mesh_service_unconfigured"}
        else:
            mesh_payload = {
                "anchor_id": anchor_id,
                "context": {
                    "bci": bci,
                    "layer_scores": layers,
                    "mode": mode,
                    "timestamp_utc": context.get("timestamp_utc"),
                },
            }
            try:
                response = requests.post(
                    f"{mesh_base_url}/mesh/decide",
                    json=mesh_payload,
                    timeout=5.0,
                )
                response.raise_for_status()
                mesh_plan = response.json()
            except Exception:
                mesh_plan = {"error": "mesh_decide_failed"}
            else:
                try:
                    requests.post(
                        f"{mesh_base_url}/mesh/execute",
                        json={"anchor_id": anchor_id, "plan": mesh_plan},
                        timeout=5.0,
                    )
                except Exception:
                    pass
    record["mesh_plan"] = mesh_plan
    record_path = BIOSCAN_DIR / f"{session_id}.json"
    with record_path.open("w", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2)

    # ---- NEW: broadcast to WebSocket clients (best-effort) ----
    try:
        await emit_event(
            {
                "type": "bioscan",
                "session_id": session_id,
                "mode": mode,
                "ts": context.get("timestamp_utc")
                or _dt.datetime.utcnow().replace(tzinfo=_dt.timezone.utc).isoformat(),
                "bci": bci,
                "crc": layers.get("crc", {}).get("mu"),
                "nfc": layers.get("nfc", {}).get("mu"),
                "peb": layers.get("peb", {}).get("mu"),
                "bhs": layers.get("bhs", {}).get("mu"),
                "pla": layers.get("pla", {}).get("mu"),
            }
        )
    except Exception:
        # don't fail the request if WS isn't available
        pass

    return record


def load_recent_bioscans(limit: int) -> Iterable[Dict[str, Any]]:
    files = sorted(
        [p for p in BIOSCAN_DIR.glob("*.json") if p.is_file()],
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    for path in files[:limit]:
        try:
            with path.open("r", encoding="utf-8") as handle:
                yield json.load(handle)
        except Exception:
            continue


__all__ = [
    "app",
    "BIOSCAN_DIR",
    "clip01",
    "BioScanPayload",
    "normalize_features",
    "layer_scores",
    "compute_bci",
    "seal_record",
    "load_recent_bioscans",
    "emit_event",
]
