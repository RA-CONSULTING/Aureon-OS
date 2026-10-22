"""Extended Temporal Aura Scan Engine with birth date and temporal ID support."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import datetime as dt
import json
import os

from temporal_aura_scan import (
    BASELINE_FREQUENCY_HZ,
    PLOTS_SUBDIR_NAME,
    SCANS_DIR,
    _derive_status,
    _plot_frequency_series,
    _sanitize_for_filename,
    compute_imperial_light_reading,
    compute_temporal_vector,
    generate_quantum_seal,
    load_schumann_data,
)


_DEFAULT_ZIP_CANDIDATES = [
    Path(os.environ.get("AURIS_EARTH_ZIP", "")),
    Path("/mnt/data/earth-live-data (7).zip"),
    Path("data/earth-live-data.zip"),
]


def resolve_default_zip_path() -> Path:
    """Resolve the preferred Schumann resonance ZIP path."""

    explicit = os.environ.get("AURIS_EARTH_ZIP")
    if explicit:
        return Path(explicit)
    for candidate in _DEFAULT_ZIP_CANDIDATES[1:]:
        if candidate.exists():
            return candidate
    return _DEFAULT_ZIP_CANDIDATES[-1]


EARTH_ZIP = resolve_default_zip_path()


@dataclass
class ExtendedAuraReport:
    """Structured representation for an aura scan with temporal metadata."""

    operator: str
    location: Optional[str]
    birth_date: Optional[str]
    temporal_id: Optional[str]
    timestamp_utc: str
    mean_frequency_hz: float
    std_frequency_hz: float
    coherence: float
    phase_lock: float
    quantum_alignment: float
    imperial_light_reading: float
    seal_hash: str
    seal_payload: Dict[str, object]
    plots: Dict[str, Optional[str]]
    status: str

    def to_json(self) -> Dict[str, object]:
        return {
            "operator": self.operator,
            "location": self.location,
            "birth_date": self.birth_date,
            "temporal_id": self.temporal_id,
            "timestamp_utc": self.timestamp_utc,
            "mean_frequency_hz": self.mean_frequency_hz,
            "std_frequency_hz": self.std_frequency_hz,
            "coherence": self.coherence,
            "phase_lock": self.phase_lock,
            "quantum_alignment": self.quantum_alignment,
            "imperial_light_reading": self.imperial_light_reading,
            "seal_hash": self.seal_hash,
            "seal_payload": self.seal_payload,
            "plots": self.plots,
            "status": self.status,
        }


def _store_report(report: ExtendedAuraReport, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = report.timestamp_utc.replace(":", "-")
    tag = _sanitize_for_filename(report.operator)
    filename = directory / f"{timestamp}_{tag}.json"
    with filename.open("w", encoding="utf-8") as fp:
        json.dump(report.to_json(), fp, indent=2)
    return filename


def run_temporal_aura_scan(
    name: str,
    location: Optional[str],
    zip_path: str | os.PathLike[str],
    birth_date: Optional[str] = None,
    temporal_id: Optional[str] = None,
    output_dir: Path | None = None,
) -> Dict[str, object]:
    """Execute a temporal aura scan including birth date and temporal ID."""

    aggregate = load_schumann_data(zip_path)
    coherence, phase_lock, quantum_alignment = compute_temporal_vector(
        aggregate.mean_hz, aggregate.std_hz
    )

    timestamp = dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc).isoformat()
    normalized_temporal_id = temporal_id or birth_date

    plots_dir = (output_dir or SCANS_DIR) / PLOTS_SUBDIR_NAME
    operator_tag = _sanitize_for_filename(name or "operator")
    plots = _plot_frequency_series(aggregate.samples, plots_dir, operator_tag, BASELINE_FREQUENCY_HZ)

    imperial_light_reading = round(
        compute_imperial_light_reading(aggregate.samples, BASELINE_FREQUENCY_HZ), 6
    )

    seal_payload = {
        "operator": name,
        "location": location,
        "birth_date": birth_date,
        "temporal_id": normalized_temporal_id,
        "timestamp_utc": timestamp,
        "coherence": round(coherence, 6),
        "phase_lock": round(phase_lock, 6),
        "quantum_alignment": round(quantum_alignment, 6),
        "imperial_light_reading": imperial_light_reading,
    }
    seal_hash = generate_quantum_seal(seal_payload)

    status = _derive_status(coherence)

    report = ExtendedAuraReport(
        operator=name,
        location=location,
        birth_date=birth_date,
        temporal_id=normalized_temporal_id,
        timestamp_utc=timestamp,
        mean_frequency_hz=round(aggregate.mean_hz, 6),
        std_frequency_hz=round(aggregate.std_hz, 6),
        coherence=round(coherence, 6),
        phase_lock=round(phase_lock, 6),
        quantum_alignment=round(quantum_alignment, 6),
        imperial_light_reading=imperial_light_reading,
        seal_hash=seal_hash,
        seal_payload=seal_payload,
        plots=plots,
        status=status,
    )

    reports_dir = output_dir or SCANS_DIR
    stored_path = _store_report(report, reports_dir)

    result = report.to_json()
    result["report_path"] = str(stored_path)
    return result


def batch_run_temporal_scans(
    users: Iterable[Dict[str, object]],
    zip_path: str | os.PathLike[str],
    output_dir: Path | None = None,
) -> List[Dict[str, object]]:
    """Run scans for multiple users sequentially."""

    results: List[Dict[str, object]] = []
    for entry in users:
        name = str(entry.get("name", "Unknown Operator"))
        location = entry.get("location")
        birth_date = entry.get("birth_date")
        temporal_id = entry.get("temporal_id")
        report = run_temporal_aura_scan(
            name,
            location,
            zip_path,
            birth_date=birth_date,
            temporal_id=temporal_id,
            output_dir=output_dir,
        )
        results.append(report)
    return results


__all__ = [
    "EARTH_ZIP",
    "ExtendedAuraReport",
    "batch_run_temporal_scans",
    "resolve_default_zip_path",
    "run_temporal_aura_scan",
]
