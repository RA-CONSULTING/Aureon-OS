#!/usr/bin/env python3
"""UPE signal adapter — ingest *real* ultraweak-photon-emission data.

This is the legitimate "field extraction" path: it scores **genuine UPE
measurements** — an emission spectrum (wavelength nm + intensity) or a photon-count
time-series — through the same governed phenolic pipeline. It does **not** accept a
photograph as UPE (a photo records reflected light, not biophotons), and it makes
**no** claim about any subject's health, state, emotion, relationships, or identity.

The honest anchor (see :mod:`aureon.bio.upe_reference`): a broadband, featureless
UPE spectrum has no discrete harmonic structure and therefore scores
**non-separable**. This adapter reproduces that — it reports structure only when the
data genuinely contains it (e.g. planted narrow emission lines), never by fiat.

Pure numpy + stdlib + the bio modules + engine. No import-time side effects.
"""

from __future__ import annotations

import csv
import hashlib
import math
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

import numpy as np

import phenolic_fingerprint as engine
from aureon.bio import upe_reference as upe
from aureon.bio.human_harmonic_proxy import (
    HumanSignal,
    ProxyResult,
    fold_to_band,
    score_signal,
)
from aureon.bio.image_signal_adapter import _wavelength_nm_to_hz

__all__ = [
    "UPEInput",
    "UPEHumanSignal",
    "UPEProxyResult",
    "UPESignalAdapter",
    "build_live_upe_input",
    "control_upe",
    "score_upe",
    "synthetic_upe",
    "upe_data_sha256",
]

PHI: float = float(engine.PHI)
MAX_RECEIPT_AGE_SECONDS: float = 300.0
FUTURE_SKEW_SECONDS: float = 5.0
_REAL_TRUTH_STATUSES = frozenset({"real_observed", "real_derived"})
_CONTROL_PREFIX = "bio.control.upe."


@dataclass(frozen=True, slots=True)
class _ReceiptEvidence:
    """Immutable provider or gate receipt after strict normalization."""

    receipt_id: str
    source_id: str
    source_timestamp: float
    received_at: float
    freshness_ttl_sec: float
    truth_status: str
    generated_values: bool
    receipt_type: str
    eligible_for_action: bool
    eligible_for_accounting: bool
    eligible_for_learning: bool
    kind: str | None = None
    data_sha256: str | None = None
    sample_rate_hz: float | None = None
    input_receipt_ids: tuple[str, ...] = ()
    coherence: float | None = None
    gate_open: bool | None = None


@dataclass(frozen=True, slots=True)
class UPEInput:
    """Frozen UPE samples plus their non-relabelable evidence classification."""

    samples: tuple[tuple[float, ...], ...]
    kind: str
    provenance: str
    data_origin: str
    truth_status: str
    generated_values: bool
    control_only: bool
    live_data: bool
    provider_observation: bool
    operational_eligible: bool
    action_eligible: bool
    actionable: bool
    accounting_eligible: bool
    learning_eligible: bool
    provider_eligible: bool
    sample_rate_hz: float | None = None
    measurement_receipt: _ReceiptEvidence | None = None
    hnc_receipt: _ReceiptEvidence | None = None
    auris_receipt: _ReceiptEvidence | None = None

    def as_array(self) -> np.ndarray:
        """Return a read-only array view without exposing mutable stored samples."""
        shaped = np.asarray(self.samples, dtype="<f8")
        frozen = np.frombuffer(shaped.tobytes(order="C"), dtype="<f8").reshape(shaped.shape)
        return frozen[:, 0] if self.kind == "timeseries" else frozen

    @property
    def receipt_ids(self) -> tuple[str, ...]:
        return tuple(
            receipt.receipt_id
            for receipt in (self.measurement_receipt, self.hnc_receipt, self.auris_receipt)
            if receipt is not None
        )


@dataclass(frozen=True)
class UPEHumanSignal(HumanSignal):
    """HumanSignal with the UPE evidence decision preserved for gated consumers."""

    data_origin: str = "derived_statistical_control"
    truth_status: str = "statistical_control"
    generated_values: bool = True
    live_data: bool = False
    provider_observation: bool = False
    operational_eligible: bool = False
    action_eligible: bool = False
    actionable: bool = False
    accounting_eligible: bool = False
    learning_eligible: bool = False
    provider_eligible: bool = False
    receipt_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class UPEProxyResult(ProxyResult):
    """Governed score with its validated UPE evidence route preserved."""

    input_data_origin: str = "derived_statistical_control"
    input_truth_status: str = "statistical_control"
    input_generated_values: bool = True
    input_live_data: bool = False
    input_provider_observation: bool = False
    input_operational_eligible: bool = False
    input_action_eligible: bool = False
    input_learning_eligible: bool = False
    input_provider_eligible: bool = False
    input_receipt_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        ready = bool(
            self.valid
            and not self.blocked
            and not self.control_only
            and self.input_generated_values is False
            and self.input_live_data is True
            and self.input_provider_observation is True
            and self.input_operational_eligible is True
            and self.input_learning_eligible is True
            and self.input_provider_eligible is True
            and len(self.input_receipt_ids) == 3
        )
        action_ready = bool(
            ready
            and self.input_action_eligible is True
            and self.structure_present
        )
        payload.update(
            {
                "data_origin": (
                    "provider_derived_upe_analysis"
                    if ready
                    else self.input_data_origin
                ),
                "truth_status": "real_derived" if ready else self.input_truth_status,
                "generated_values": self.input_generated_values,
                "live_data": self.input_live_data if ready else False,
                "provider_observation": False,
                "input_provider_observation": (
                    self.input_provider_observation if ready else False
                ),
                "operational_eligible": ready,
                "action_eligible": action_ready,
                "actionable": action_ready,
                "eligible_for_action": action_ready,
                "accounting_eligible": False,
                "eligible_for_accounting": False,
                "learning_eligible": ready,
                "eligible_for_learning": ready,
                "provider_eligible": ready,
                "input_receipt_ids": list(self.input_receipt_ids) if ready else [],
            }
        )
        return payload


def _finite_number(value: Any, label: str, *, positive: bool = False) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a finite number")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{label} must be a finite number") from exc
    if not math.isfinite(number) or (positive and number <= 0.0):
        qualifier = "finite positive" if positive else "finite"
        raise ValueError(f"{label} must be {qualifier}")
    return number


def _timestamp(value: Any, label: str) -> float:
    if isinstance(value, str):
        text = value.strip()
        if not text:
            raise ValueError(f"{label} is required")
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"{label} must be ISO-8601 or epoch seconds") from exc
        if parsed.tzinfo is None:
            raise ValueError(f"{label} must include a timezone")
        value = parsed.timestamp()
    return _finite_number(value, label)


def _now_seconds(now: Any | None) -> float:
    return time.time() if now is None else _timestamp(now, "now")


def _freeze_samples(spec: Any, *, kind: str) -> tuple[tuple[float, ...], ...]:
    if kind == "spectrum":
        nm, intensity = _load_spectrum(spec)
        array = np.column_stack([nm, intensity]).astype(float, copy=False)
        if array.shape[0] < 3:
            raise ValueError("spectrum requires at least three complete samples")
        if np.any(array[:, 0] <= 0.0) or np.any(array[:, 1] < 0.0):
            raise ValueError("spectrum wavelengths must be positive and intensities non-negative")
    elif kind == "timeseries":
        array = (
            np.loadtxt(spec, delimiter=",")
            if isinstance(spec, (str, Path))
            else np.asarray(spec, dtype=float)
        )
        array = np.asarray(array, dtype=float).ravel()
        if array.size < 4:
            raise ValueError("timeseries requires at least four complete samples")
        array = array[:, None]
    else:
        raise ValueError(f"unknown UPE kind {kind!r}; expected 'spectrum' or 'timeseries'")
    if not np.all(np.isfinite(array)):
        raise ValueError("UPE samples must be complete finite numbers")
    return tuple(tuple(float(value) for value in row) for row in array)


def _array_from_samples(
    samples: tuple[tuple[float, ...], ...],
    *,
    kind: str,
) -> np.ndarray:
    array = np.asarray(samples, dtype="<f8")
    return array[:, 0] if kind == "timeseries" else array


def _hash_samples(samples: tuple[tuple[float, ...], ...], *, kind: str) -> str:
    array = np.ascontiguousarray(_array_from_samples(samples, kind=kind), dtype="<f8")
    digest = hashlib.sha256()
    digest.update(f"upe-v1|{kind}|{array.shape}".encode("ascii"))
    digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def upe_data_sha256(spec: Any, *, kind: str = "spectrum") -> str:
    """Return the canonical content hash a measurement receipt must bind."""
    if isinstance(spec, UPEInput):
        if spec.kind != kind:
            raise ValueError("UPE input kind does not match requested hash kind")
        samples = spec.samples
    else:
        samples = _freeze_samples(spec, kind=kind)
    return _hash_samples(samples, kind=kind)


def _check_fresh(receipt: _ReceiptEvidence, *, now: float) -> None:
    source_timestamp = _finite_number(
        receipt.source_timestamp,
        f"{receipt.source_id}.source_timestamp",
    )
    received_at = _finite_number(receipt.received_at, f"{receipt.source_id}.received_at")
    receipt_ttl = _finite_number(
        receipt.freshness_ttl_sec,
        f"{receipt.source_id}.freshness_ttl_sec",
        positive=True,
    )
    ttl = min(receipt_ttl, MAX_RECEIPT_AGE_SECONDS)
    if source_timestamp > received_at + FUTURE_SKEW_SECONDS:
        raise ValueError(f"{receipt.source_id} receipt predates its source observation")
    if received_at > now + FUTURE_SKEW_SECONDS:
        raise ValueError(f"{receipt.source_id} receipt is future-dated")
    if now - source_timestamp > ttl + FUTURE_SKEW_SECONDS:
        raise ValueError(f"{receipt.source_id} receipt is stale")
    if now - received_at > ttl + FUTURE_SKEW_SECONDS:
        raise ValueError(f"{receipt.source_id} read-back is stale")


def _parse_receipt(
    raw: Mapping[str, Any],
    *,
    role: str,
    now: float,
    kind: str | None = None,
    data_sha256: str | None = None,
    sample_rate_hz: float | None = None,
) -> _ReceiptEvidence:
    if not isinstance(raw, Mapping):
        raise ValueError(f"{role} receipt must be a mapping")
    required = {
        "receipt_id",
        "source_id",
        "source_timestamp",
        "received_at",
        "freshness_ttl_sec",
        "truth_status",
        "generated_values",
        "receipt_type",
        "eligible_for_action",
        "eligible_for_accounting",
        "eligible_for_learning",
    }
    missing = sorted(key for key in required if key not in raw)
    if missing:
        raise ValueError(f"{role} receipt missing fields: {', '.join(missing)}")
    receipt_id = str(raw["receipt_id"]).strip()
    source_id = str(raw["source_id"]).strip()
    if not receipt_id or not source_id:
        raise ValueError(f"{role} receipt identifiers are required")
    if source_id.lower().startswith(_CONTROL_PREFIX):
        raise ValueError(f"{role} receipt cannot use control provenance")
    truth_status = str(raw["truth_status"]).strip().lower()
    expected_status = "real_observed" if role == "measurement" else "real_derived"
    if truth_status != expected_status:
        raise ValueError(f"{role} receipt truth_status must be {expected_status}")
    if raw["generated_values"] is not False:
        raise ValueError(f"{role} receipt must declare generated_values=false")
    expected_type = {
        "measurement": "upe_measurement",
        "hnc": "hnc_coherence",
        "auris": "auris_coherence",
    }[role]
    receipt_type = str(raw["receipt_type"]).strip().lower()
    if receipt_type != expected_type:
        raise ValueError(f"{role} receipt_type must be {expected_type}")
    if (
        raw["eligible_for_action"] is not True
        or raw["eligible_for_accounting"] is not False
        or raw["eligible_for_learning"] is not True
    ):
        raise ValueError(f"{role} receipt eligibility fields are incomplete")
    raw_links = raw.get("input_receipt_ids")
    if raw_links is None:
        links: tuple[str, ...] = ()
    elif isinstance(raw_links, (list, tuple)):
        links = tuple(str(value).strip() for value in raw_links)
        if (
            not links
            or any(not value for value in links)
            or len(links) != len(set(links))
        ):
            raise ValueError(f"{role} input_receipt_ids must be complete and unique")
    else:
        raise ValueError(f"{role} input_receipt_ids must be a sequence")
    coherence = (
        _finite_number(raw.get("coherence"), f"{role}.coherence")
        if raw.get("coherence") is not None
        else None
    )
    receipt = _ReceiptEvidence(
        receipt_id=receipt_id,
        source_id=source_id,
        source_timestamp=_timestamp(raw["source_timestamp"], f"{role}.source_timestamp"),
        received_at=_timestamp(raw["received_at"], f"{role}.received_at"),
        freshness_ttl_sec=_finite_number(
            raw["freshness_ttl_sec"],
            f"{role}.freshness_ttl_sec",
            positive=True,
        ),
        truth_status=truth_status,
        generated_values=False,
        receipt_type=receipt_type,
        eligible_for_action=True,
        eligible_for_accounting=False,
        eligible_for_learning=True,
        kind=str(raw.get("kind")).strip().lower() if raw.get("kind") is not None else None,
        data_sha256=(
            str(raw.get("data_sha256")).strip().lower()
            if raw.get("data_sha256") is not None
            else None
        ),
        sample_rate_hz=(
            _finite_number(raw.get("sample_rate_hz"), f"{role}.sample_rate_hz", positive=True)
            if raw.get("sample_rate_hz") is not None
            else None
        ),
        input_receipt_ids=links,
        coherence=coherence,
        gate_open=raw.get("gate_open"),
    )
    _check_fresh(receipt, now=now)
    if role == "measurement":
        if receipt.input_receipt_ids:
            raise ValueError("measurement receipt cannot claim derived inputs")
        if receipt.kind != kind:
            raise ValueError("measurement receipt kind does not match UPE samples")
        if receipt.data_sha256 != data_sha256:
            raise ValueError("measurement receipt does not bind the supplied UPE samples")
        if kind == "timeseries":
            if sample_rate_hz is None or receipt.sample_rate_hz != sample_rate_hz:
                raise ValueError("measurement receipt must bind the exact sample rate")
        elif receipt.sample_rate_hz is not None:
            raise ValueError("spectrum receipt must not declare a sample rate")
    else:
        if (
            receipt.coherence is None
            or not 0.0 <= receipt.coherence <= 1.0
            or receipt.gate_open is not True
        ):
            raise ValueError(f"{role} receipt must explicitly pass the {role.upper()} gate")
    return receipt


def _canonical_live_provenance(
    measurement: _ReceiptEvidence,
    hnc: _ReceiptEvidence,
    auris: _ReceiptEvidence,
) -> str:
    return (
        f"{measurement.source_id}#{measurement.receipt_id};"
        f"hnc#{hnc.receipt_id};auris#{auris.receipt_id}"
    )


def build_live_upe_input(
    spec: Any,
    *,
    measurement_receipt: Mapping[str, Any],
    hnc_receipt: Mapping[str, Any],
    auris_receipt: Mapping[str, Any],
    kind: str = "spectrum",
    sample_rate_hz: float | None = None,
    now: Any | None = None,
) -> UPEInput:
    """Bind runtime samples to fresh source, HNC, and Auris receipts.

    This is the sole constructor for action-eligible UPE input. All three receipts
    are linked and rechecked when the adapter extracts the signal.
    """
    samples = _freeze_samples(spec, kind=kind)
    array = _array_from_samples(samples, kind=kind)
    if kind == "timeseries":
        if np.any(array < 0.0):
            raise ValueError("live photon counts must be non-negative")
        sample_rate = _finite_number(
            sample_rate_hz,
            "sample_rate_hz",
            positive=True,
        )
    else:
        if sample_rate_hz is not None:
            raise ValueError("sample_rate_hz is only valid for photon-count timeseries")
        sample_rate = None
    current = _now_seconds(now)
    data_hash = _hash_samples(samples, kind=kind)
    measurement = _parse_receipt(
        measurement_receipt,
        role="measurement",
        now=current,
        kind=kind,
        data_sha256=data_hash,
        sample_rate_hz=sample_rate,
    )
    hnc = _parse_receipt(
        hnc_receipt,
        role="hnc",
        now=current,
    )
    auris = _parse_receipt(
        auris_receipt,
        role="auris",
        now=current,
    )
    receipt_ids = {measurement.receipt_id, hnc.receipt_id, auris.receipt_id}
    if len(receipt_ids) != 3:
        raise ValueError("measurement, HNC, and Auris receipt IDs must be distinct")
    if hnc.input_receipt_ids != (measurement.receipt_id,):
        raise ValueError("HNC receipt must link exactly the measurement receipt")
    if set(auris.input_receipt_ids) != {measurement.receipt_id, hnc.receipt_id}:
        raise ValueError("Auris receipt must link the measurement and HNC receipts")
    if not (
        measurement.source_timestamp <= hnc.source_timestamp <= auris.source_timestamp
        and measurement.received_at <= hnc.received_at <= auris.received_at
    ):
        raise ValueError("measurement, HNC, and Auris receipts must form a monotonic chain")
    return UPEInput(
        samples=samples,
        kind=kind,
        provenance=_canonical_live_provenance(measurement, hnc, auris),
        data_origin="provider_observation",
        truth_status=measurement.truth_status,
        generated_values=False,
        control_only=False,
        live_data=True,
        provider_observation=True,
        operational_eligible=True,
        action_eligible=True,
        actionable=True,
        accounting_eligible=False,
        learning_eligible=True,
        provider_eligible=True,
        sample_rate_hz=sample_rate,
        measurement_receipt=measurement,
        hnc_receipt=hnc,
        auris_receipt=auris,
    )


def _control_input(
    spec: Any,
    *,
    kind: str,
    provenance: str,
    sample_rate_hz: float | None = None,
) -> UPEInput:
    if not provenance.startswith(_CONTROL_PREFIX):
        raise ValueError("control provenance must use the immutable bio.control.upe namespace")
    samples = _freeze_samples(spec, kind=kind)
    sample_rate = (
        _finite_number(sample_rate_hz, "sample_rate_hz", positive=True)
        if kind == "timeseries"
        else None
    )
    return UPEInput(
        samples=samples,
        kind=kind,
        provenance=provenance,
        data_origin="derived_statistical_control",
        truth_status="statistical_control",
        generated_values=True,
        control_only=True,
        live_data=False,
        provider_observation=False,
        operational_eligible=False,
        action_eligible=False,
        actionable=False,
        accounting_eligible=False,
        learning_eligible=False,
        provider_eligible=False,
        sample_rate_hz=sample_rate,
    )


def _validate_control_input(value: UPEInput) -> None:
    false_fields = (
        value.live_data,
        value.provider_observation,
        value.operational_eligible,
        value.action_eligible,
        value.actionable,
        value.accounting_eligible,
        value.learning_eligible,
        value.provider_eligible,
    )
    if (
        not value.provenance.startswith(_CONTROL_PREFIX)
        or value.data_origin != "derived_statistical_control"
        or value.truth_status != "statistical_control"
        or value.generated_values is not True
        or value.control_only is not True
        or any(field is not False for field in false_fields)
        or any(
            receipt is not None
            for receipt in (value.measurement_receipt, value.hnc_receipt, value.auris_receipt)
        )
    ):
        raise ValueError("invalid or relabelled UPE control envelope")
    if value.kind not in {"spectrum", "timeseries"}:
        raise ValueError("invalid UPE control kind")
    array = _array_from_samples(value.samples, kind=value.kind)
    if not np.all(np.isfinite(array)):
        raise ValueError("UPE control samples must be complete finite numbers")
    if value.kind == "spectrum":
        if (
            array.ndim != 2
            or array.shape[0] < 3
            or array.shape[1] != 2
            or np.any(array[:, 0] <= 0.0)
            or np.any(array[:, 1] < 0.0)
            or value.sample_rate_hz is not None
        ):
            raise ValueError("invalid UPE spectrum control")
    elif (
        array.ndim != 1
        or array.size < 4
        or _finite_number(value.sample_rate_hz, "sample_rate_hz", positive=True)
        != value.sample_rate_hz
    ):
        raise ValueError("invalid UPE timeseries control")


def _validate_live_input(value: UPEInput, *, now: float) -> None:
    measurement = value.measurement_receipt
    hnc = value.hnc_receipt
    auris = value.auris_receipt
    if measurement is None or hnc is None or auris is None:
        raise ValueError("live UPE input requires measurement, HNC, and Auris receipts")
    expected_provenance = _canonical_live_provenance(measurement, hnc, auris)
    if (
        value.provenance != expected_provenance
        or value.data_origin != "provider_observation"
        or value.truth_status != "real_observed"
        or value.generated_values is not False
        or value.control_only is not False
        or value.live_data is not True
        or value.provider_observation is not True
        or value.operational_eligible is not True
        or value.action_eligible is not True
        or value.actionable is not True
        or value.accounting_eligible is not False
        or value.learning_eligible is not True
        or value.provider_eligible is not True
    ):
        raise ValueError("invalid or relabelled live UPE envelope")
    if len(set(value.receipt_ids)) != 3:
        raise ValueError("live UPE receipt IDs must be distinct")
    array = _array_from_samples(value.samples, kind=value.kind)
    if not np.all(np.isfinite(array)):
        raise ValueError("live UPE samples must remain finite")
    if value.kind == "timeseries":
        if np.any(array < 0.0):
            raise ValueError("live photon counts must be non-negative")
        sample_rate = _finite_number(value.sample_rate_hz, "sample_rate_hz", positive=True)
    else:
        sample_rate = None
        if value.sample_rate_hz is not None:
            raise ValueError("spectrum envelope cannot carry a sample rate")
    if (
        measurement.kind != value.kind
        or measurement.data_sha256 != _hash_samples(value.samples, kind=value.kind)
        or measurement.sample_rate_hz != sample_rate
        or measurement.input_receipt_ids
    ):
        raise ValueError("measurement receipt no longer binds the UPE input")
    expected_receipt = {
        "measurement": ("upe_measurement", "real_observed"),
        "hnc": ("hnc_coherence", "real_derived"),
        "auris": ("auris_coherence", "real_derived"),
    }
    for role, receipt in (("measurement", measurement), ("hnc", hnc), ("auris", auris)):
        receipt_type, truth_status = expected_receipt[role]
        if (
            not receipt.receipt_id
            or not receipt.source_id
            or receipt.source_id.lower().startswith(_CONTROL_PREFIX)
            or receipt.receipt_type != receipt_type
            or receipt.truth_status != truth_status
            or receipt.generated_values is not False
            or receipt.eligible_for_action is not True
            or receipt.eligible_for_accounting is not False
            or receipt.eligible_for_learning is not True
        ):
            raise ValueError(f"{role} receipt is not provider-authentic")
        _check_fresh(receipt, now=now)
    for role, gate in (("hnc", hnc), ("auris", auris)):
        if (
            gate.coherence is None
            or not 0.0 <= gate.coherence <= 1.0
            or gate.gate_open is not True
        ):
            raise ValueError(f"{role} gate is not complete and open")
    if hnc.input_receipt_ids != (measurement.receipt_id,):
        raise ValueError("HNC gate is not causally linked to the measurement")
    if set(auris.input_receipt_ids) != {measurement.receipt_id, hnc.receipt_id}:
        raise ValueError("Auris gate is not causally linked to measurement and HNC")
    if not (
        measurement.source_timestamp <= hnc.source_timestamp <= auris.source_timestamp
        and measurement.received_at <= hnc.received_at <= auris.received_at
    ):
        raise ValueError("live UPE receipt chain is not monotonic")


# ---------------------------------------------------------------------------
# emission-spectrum peak picking (nm / intensity; peaks are local maxima)
# ---------------------------------------------------------------------------


def _pick_emission_peaks(
    nm: np.ndarray,
    intensity: np.ndarray,
    *,
    min_prominence: float = 0.05,
    min_separation_nm: float = 1.0,
    max_peaks: int = 24,
) -> list[float]:
    """Return wavelengths (nm) of emission lines — strict local maxima of intensity.

    Intensity is normalised 0-1; a peak must rise at least ``min_prominence`` above
    the baseline. Peaks closer than ``min_separation_nm`` are merged (brighter kept).
    A flat/broadband spectrum yields no peaks — the honest non-structure result.
    """
    nm = np.asarray(nm, dtype=float)
    y = np.asarray(intensity, dtype=float)
    if nm.size < 3 or y.size != nm.size:
        return []
    lo, hi = float(np.min(y)), float(np.max(y))
    span = hi - lo
    if span <= 0:
        return []
    norm = (y - lo) / span

    cands: list[tuple[float, float]] = []  # (nm, height)
    for i in range(1, norm.size - 1):
        if norm[i] > norm[i - 1] and norm[i] >= norm[i + 1] and norm[i] >= min_prominence:
            cands.append((float(nm[i]), float(norm[i])))
    if not cands:
        return []
    cands.sort(key=lambda c: -c[1])  # brightest first
    kept: list[tuple[float, float]] = []
    for wl, ht in cands:
        if all(abs(wl - k[0]) >= min_separation_nm for k in kept):
            kept.append((wl, ht))
        if len(kept) >= max_peaks:
            break
    return sorted(wl for wl, _ in kept)


def _dominant_timeseries_hz(
    counts: np.ndarray,
    *,
    sample_rate_hz: float,
    min_prominence: float = 0.05,
    max_peaks: int = 24,
) -> list[float]:
    """Dominant temporal frequencies (Hz) of a photon-count series via real FFT."""
    x = np.asarray(counts, dtype=float)
    if x.size < 4 or sample_rate_hz <= 0:
        return []
    x = x - float(np.mean(x))
    freqs = np.fft.rfftfreq(x.size, d=1.0 / float(sample_rate_hz))
    power = np.abs(np.fft.rfft(x)) ** 2
    if freqs.size < 3 or float(np.max(power)) <= 0:
        return []
    norm = power / float(np.max(power))
    picks: list[tuple[float, float]] = []
    for i in range(1, norm.size - 1):
        if norm[i] > norm[i - 1] and norm[i] >= norm[i + 1] and norm[i] >= min_prominence and freqs[i] > 0:
            picks.append((float(freqs[i]), float(norm[i])))
    picks.sort(key=lambda p: -p[1])
    return sorted(f for f, _ in picks[:max_peaks])


# ---------------------------------------------------------------------------
# loading real UPE data
# ---------------------------------------------------------------------------


def _load_spectrum(spec: Any) -> tuple[np.ndarray, np.ndarray]:
    """Load (wavelength_nm, intensity) from a CSV path / 2-col array / list of tuples."""
    if isinstance(spec, (str, Path)):
        nm_vals: list[float] = []
        iv: list[float] = []
        with Path(spec).open("r", newline="", encoding="utf-8") as fh:
            reader = csv.reader(fh)
            for row in reader:
                if len(row) < 2:
                    continue
                try:
                    a, b = float(row[0]), float(row[1])
                except ValueError:
                    continue  # header / comment line
                nm_vals.append(a)
                iv.append(b)
        return np.array(nm_vals), np.array(iv)
    arr = np.asarray(spec, dtype=float)
    if arr.ndim != 2 or arr.shape[1] < 2:
        raise ValueError("spectrum must be an (N,2) array of (wavelength_nm, intensity)")
    return arr[:, 0], arr[:, 1]


# ---------------------------------------------------------------------------
# adapter
# ---------------------------------------------------------------------------


def _resolve_upe_input(
    spec: Any,
    *,
    kind: str,
    sample_rate_hz: float | None,
    measurement_receipt: Mapping[str, Any] | None,
    hnc_receipt: Mapping[str, Any] | None,
    auris_receipt: Mapping[str, Any] | None,
    now: Any | None,
) -> UPEInput:
    current = _now_seconds(now)
    receipts = (measurement_receipt, hnc_receipt, auris_receipt)
    if isinstance(spec, UPEInput):
        if any(receipt is not None for receipt in receipts):
            raise ValueError("a frozen UPE envelope cannot be relabelled with new receipts")
        if spec.kind != kind:
            raise ValueError("UPE envelope kind does not match the requested extraction kind")
        if spec.control_only:
            _validate_control_input(spec)
        else:
            _validate_live_input(spec, now=current)
        if kind == "timeseries":
            requested_rate = (
                spec.sample_rate_hz
                if sample_rate_hz is None
                else _finite_number(sample_rate_hz, "sample_rate_hz", positive=True)
            )
            if requested_rate != spec.sample_rate_hz:
                raise ValueError("sample_rate_hz does not match the frozen UPE envelope")
        elif sample_rate_hz is not None:
            raise ValueError("sample_rate_hz is only valid for photon-count timeseries")
        return spec

    supplied = tuple(receipt is not None for receipt in receipts)
    if any(supplied):
        if not all(supplied):
            raise ValueError("measurement, HNC, and Auris receipts are all required")
        return build_live_upe_input(
            spec,
            measurement_receipt=measurement_receipt,
            hnc_receipt=hnc_receipt,
            auris_receipt=auris_receipt,
            kind=kind,
            sample_rate_hz=sample_rate_hz,
            now=current,
        )
    return _control_input(
        spec,
        kind=kind,
        provenance=f"{_CONTROL_PREFIX}unverified_input",
        sample_rate_hz=sample_rate_hz,
    )


class UPESignalAdapter:
    """Extract a derived signal from UPE spectrum or photon-count evidence.

    Implements the :class:`aureon.bio.human_harmonic_proxy.SignalAdapter` seam.
    Bare arrays remain quarantined controls. Only complete linked measurement,
    HNC, and Auris receipts create an operationally eligible signal.
    """

    modality: str = "upe"

    def extract(
        self,
        spec: Any,
        *,
        consent: bool,
        provenance: str,
        kind: str = "spectrum",
        sample_rate_hz: float | None = None,
        max_peaks: int = 24,
        measurement_receipt: Mapping[str, Any] | None = None,
        hnc_receipt: Mapping[str, Any] | None = None,
        auris_receipt: Mapping[str, Any] | None = None,
        now: Any | None = None,
    ) -> UPEHumanSignal:
        """Return folded tones while preserving the evidence eligibility decision."""
        if isinstance(max_peaks, bool) or int(max_peaks) <= 0:
            raise ValueError("max_peaks must be a positive integer")
        evidence = _resolve_upe_input(
            spec,
            kind=kind,
            sample_rate_hz=sample_rate_hz,
            measurement_receipt=measurement_receipt,
            hnc_receipt=hnc_receipt,
            auris_receipt=auris_receipt,
            now=now,
        )
        array = evidence.as_array()
        if kind == "spectrum":
            wavelengths = _pick_emission_peaks(
                array[:, 0],
                array[:, 1],
                max_peaks=int(max_peaks),
            )
            raw_hz = [_wavelength_nm_to_hz(wl) for wl in wavelengths]
            note = f"{len(wavelengths)} UPE emission line(s)"
        elif kind == "timeseries":
            rate = _finite_number(
                evidence.sample_rate_hz,
                "sample_rate_hz",
                positive=True,
            )
            raw_hz = _dominant_timeseries_hz(
                array,
                sample_rate_hz=rate,
                max_peaks=int(max_peaks),
            )
            note = f"{len(raw_hz)} dominant photon-count mode(s)"
        else:  # pragma: no cover - _resolve_upe_input guards this
            raise AssertionError("unreachable UPE kind")

        tones = tuple(sorted(f for f in (fold_to_band(v) for v in raw_hz) if f is not None))
        declared = bool(str(provenance).strip())
        return UPEHumanSignal(
            label=f"upe:{kind}",
            frequencies_hz=tones,
            provenance=evidence.provenance,
            consent=consent is True and declared,
            modality=self.modality,
            notes=f"{note}; derived-signal structure within the scientific boundary",
            control_only=evidence.control_only,
            data_origin=evidence.data_origin,
            truth_status=evidence.truth_status,
            generated_values=evidence.generated_values,
            live_data=evidence.live_data,
            provider_observation=evidence.provider_observation,
            operational_eligible=evidence.operational_eligible,
            action_eligible=evidence.action_eligible,
            actionable=evidence.actionable,
            accounting_eligible=evidence.accounting_eligible,
            learning_eligible=evidence.learning_eligible,
            provider_eligible=evidence.provider_eligible,
            receipt_ids=evidence.receipt_ids,
        )


def score_upe(
    spec: Any,
    *,
    consent: bool,
    provenance: str,
    kind: str = "spectrum",
    sample_rate_hz: float | None = None,
    nulls: int = engine.DEFAULT_NULLS,
    seed: int = 0,
    max_peaks: int = 24,
    measurement_receipt: Mapping[str, Any] | None = None,
    hnc_receipt: Mapping[str, Any] | None = None,
    auris_receipt: Mapping[str, Any] | None = None,
    now: Any | None = None,
) -> UPEProxyResult:
    """Extract UPE evidence and score it through the unchanged governed pipeline."""
    signal = UPESignalAdapter().extract(
        spec,
        consent=consent,
        provenance=provenance,
        kind=kind,
        sample_rate_hz=sample_rate_hz,
        max_peaks=max_peaks,
        measurement_receipt=measurement_receipt,
        hnc_receipt=hnc_receipt,
        auris_receipt=auris_receipt,
        now=now,
    )
    result = score_signal(signal, nulls=nulls, seed=seed)
    return UPEProxyResult(
        valid=result.valid,
        structure_present=result.structure_present,
        test_A_p=result.test_A_p,
        test_B_p=result.test_B_p,
        n_tones=result.n_tones,
        controls=result.controls,
        provenance=result.provenance,
        consent=result.consent,
        modality=result.modality,
        label=result.label,
        blocked=result.blocked,
        reason=result.reason,
        boundary=result.boundary,
        control_only=result.control_only,
        input_data_origin=signal.data_origin,
        input_truth_status=signal.truth_status,
        input_generated_values=signal.generated_values,
        input_live_data=signal.live_data,
        input_provider_observation=signal.provider_observation,
        input_operational_eligible=signal.operational_eligible,
        input_action_eligible=signal.action_eligible,
        input_learning_eligible=signal.learning_eligible,
        input_provider_eligible=signal.provider_eligible,
        input_receipt_ids=signal.receipt_ids,
    )


# ---------------------------------------------------------------------------
# deterministic scientific controls
# ---------------------------------------------------------------------------


def _fold_band_vec(f_hz: np.ndarray) -> np.ndarray:
    """Vectorised octave-fold of positive Hz into ``TARGET_BAND_HZ`` [1000, 2000)."""
    k = np.floor(np.log2(f_hz / 1000.0))
    return f_hz / (2.0 ** k)


def _wavelengths_for_tones(targets: list[float]) -> list[float]:
    """Find UPE-band wavelengths (nm) that octave-fold to the given modulation tones.

    The nm->Hz->fold transform is many-to-one, so for each target modulation tone a
    wavelength in [200, 800] nm exists whose folded frequency matches it. A fine grid
    search returns the closest wavelength per target for a declared structured
    statistical control whose folded tones equal a known-separable set.
    """
    low, high = upe.UPE_BAND_NM
    grid = np.linspace(low, high, 400_001)
    f = (engine.NM_TO_THZ_NUMERATOR / grid) * engine.THZ_TO_HZ
    folded = _fold_band_vec(f)
    return [float(grid[int(np.argmin(np.abs(folded - t)))]) for t in targets]


def control_upe(kind: str = "broadband", *, seed: int = 0, n: int = 241) -> UPEInput:
    """Return a frozen, non-operational UPE statistical-control envelope."""
    _finite_number(seed, "seed")
    base = np.array(upe.reference_spectrum(n), dtype=float)
    if kind == "broadband":
        values = base
    elif kind == "structured":
        centers = 1100.0 * np.array([1.0, PHI])
        offsets = np.array([-8.0, 0.0, 8.0])
        target_tones = list((centers[:, None] + offsets[None, :]).ravel())
        line_nm = _wavelengths_for_tones(target_tones)
        nm = np.linspace(upe.UPE_BAND_NM[0], upe.UPE_BAND_NM[1], 4000)
        y = np.interp(nm, base[:, 0], base[:, 1])
        for c in line_nm:
            y = y + 0.9 * np.exp(-((nm - c) ** 2) / (2.0 * 0.4 ** 2))
        values = np.column_stack([nm, y])
    else:
        raise ValueError(f"unknown UPE control kind {kind!r}")
    return _control_input(
        values,
        kind="spectrum",
        provenance=f"{_CONTROL_PREFIX}{kind}",
    )


def synthetic_upe(kind: str = "broadband", *, seed: int = 0, n: int = 241) -> UPEInput:
    return control_upe(kind=kind, seed=seed, n=n)
