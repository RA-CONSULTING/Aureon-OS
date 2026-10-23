"""FastAPI network interface for the Temporal Aura Scan Engine."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import datetime as dt
import json
import os

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
import uvicorn

from temporal_aura_scan import (
    SCANS_DIR,
    batch_run_temporal_scans,
    generate_quantum_seal,
    run_temporal_aura_scan,
)


APP_TITLE = "AURIS Temporal Aura Network Interface"
APP_VERSION = "3.1"

_DEFAULT_ZIP_CANDIDATES = [
    Path(os.environ.get("AURIS_EARTH_ZIP", "")),
    Path("/mnt/data/earth-live-data (7).zip"),
    Path("data/earth-live-data.zip"),
]


def _resolve_zip_path() -> Path:
    explicit = os.environ.get("AURIS_EARTH_ZIP")
    if explicit:
        return Path(explicit)
    for candidate in _DEFAULT_ZIP_CANDIDATES[1:]:
        if candidate.exists():
            return candidate
    return _DEFAULT_ZIP_CANDIDATES[1]


EARTH_ZIP = _resolve_zip_path()

app = FastAPI(title=APP_TITLE, version=APP_VERSION)


class UserScan(BaseModel):
    name: str = Field(..., description="Operator or participant name")
    location: Optional[str] = Field(None, description="Geographic location of the operator")
    birthdate: Optional[str] = Field(None, description="Optional birthdate metadata")
    coordinates: Optional[str] = Field(None, description="Optional coordinates reference")


class SealPayload(BaseModel):
    operator: str
    location: Optional[str]
    timestamp_utc: str
    coherence: float
    phase_lock: float
    quantum_alignment: float


@app.get("/status")
def status() -> Dict[str, object]:
    return {
        "system": f"AURIS v{APP_VERSION}",
        "uptime_utc": dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc).isoformat(),
        "baseline_freq_hz": 7.83,
        "coherence_reference": 0.9813,
        "engine": "temporal_aura_scan.py",
        "earth_zip": str(EARTH_ZIP),
    }


@app.post("/scan")
def scan_user(user: UserScan) -> Dict[str, object]:
    if not user.name.strip():
        raise HTTPException(status_code=400, detail="Name is required for a scan.")
    report = run_temporal_aura_scan(
        operator_name=user.name,
        location=user.location,
        zip_path=str(EARTH_ZIP),
    )
    return report


@app.post("/batch")
def batch_scan(users: List[UserScan]) -> Dict[str, object]:
    if not users:
        raise HTTPException(status_code=400, detail="Provide at least one user for batch scanning.")
    payload = [user.model_dump(exclude_none=True) for user in users]
    reports = batch_run_temporal_scans(payload, str(EARTH_ZIP))
    return {"status": "Batch Complete", "results": reports}


@app.get("/seal/verify")
def verify_seal(hash: str = Query(..., description="SHA3-512 seal hash to verify")) -> Dict[str, object]:
    records = _load_scan_records(SCANS_DIR)
    matches = []
    for record, path in records:
        if record.get("seal_hash") != hash:
            continue
        payload = record.get("seal_payload")
        recomputed = generate_quantum_seal(payload) if payload else None
        matches.append(
            {
                "record_path": str(path),
                "record": record,
                "integrity": recomputed == hash if recomputed else False,
            }
        )

    if matches:
        return {
            "verified": any(match["integrity"] for match in matches),
            "matches_found": len(matches),
            "records": matches,
            "message": "Quantum Seal verified." if any(match["integrity"] for match in matches) else "Seal located but integrity mismatch.",
        }
    return {
        "verified": False,
        "matches_found": 0,
        "records": [],
        "message": "Seal hash not found.",
    }


@app.post("/seal/recompute")
def recompute_seal(payload: SealPayload) -> Dict[str, object]:
    canonical_payload = payload.model_dump()
    seal = generate_quantum_seal(canonical_payload)
    return {
        "payload": canonical_payload,
        "seal_hash": seal,
        "message": "Seal recomputed for provided payload.",
    }


def _load_scan_records(scans_dir: Path) -> List[tuple[Dict[str, object], Path]]:
    if not scans_dir.exists():
        return []
    records: List[tuple[Dict[str, object], Path]] = []
    for file_path in sorted(scans_dir.glob("*.json")):
        try:
            with file_path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (json.JSONDecodeError, OSError):
            continue
        records.append((data, file_path))
    return records


if __name__ == "__main__":
    host = os.environ.get("AURIS_HOST", "0.0.0.0")
    port = int(os.environ.get("AURIS_PORT", "8080"))
    uvicorn.run("auris_network_interface:app", host=host, port=port, reload=False)
