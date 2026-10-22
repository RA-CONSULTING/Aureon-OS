"""FastAPI network interface for the extended Temporal Aura Scan Engine."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import datetime as dt
import json
import os

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
import uvicorn

from temporal_aura_scan import SCANS_DIR, generate_quantum_seal
from temporal_aura_scan_ext import EARTH_ZIP, batch_run_temporal_scans, run_temporal_aura_scan


APP_TITLE = "AURIS Temporal Aura Network Interface"
APP_VERSION = "3.2"


app = FastAPI(title=APP_TITLE, version=APP_VERSION)


def _resolve_zip_path() -> Path:
    return EARTH_ZIP


class UserScan(BaseModel):
    name: str = Field(..., description="Operator or participant name")
    location: Optional[str] = Field(
        None, description="Geographic location of the operator"
    )
    birth_date: Optional[str] = Field(
        None, description="Birth date in YYYY-MM-DD format"
    )
    temporal_id: Optional[str] = Field(
        None, description="Temporal ID in YYYY-MM-DD format"
    )

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Name is required for a scan.")
        return cleaned

    @staticmethod
    def _validate_iso_date(value: Optional[str], field_name: str) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        try:
            dt.datetime.strptime(cleaned, "%Y-%m-%d")
        except ValueError as exc:  # noqa: PERF203 - explicit error message for clarity
            raise ValueError(f"{field_name} must be in YYYY-MM-DD format.") from exc
        return cleaned

    @field_validator("birth_date")
    @classmethod
    def _validate_birth_date(cls, value: Optional[str]) -> Optional[str]:
        return cls._validate_iso_date(value, "Birth date")

    @field_validator("temporal_id")
    @classmethod
    def _validate_temporal_id(cls, value: Optional[str]) -> Optional[str]:
        return cls._validate_iso_date(value, "Temporal ID")


class SealPayload(BaseModel):
    operator: str
    location: Optional[str]
    birth_date: Optional[str]
    temporal_id: Optional[str]
    timestamp_utc: str
    coherence: float
    phase_lock: float
    quantum_alignment: float


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = []
    for error in exc.errors():
        location = error.get("loc", [])
        field = location[-1] if location else "payload"
        errors.append({"field": field, "message": error.get("msg", "Invalid value.")})
    return JSONResponse(status_code=422, content={"detail": errors})


@app.get("/status")
def status() -> Dict[str, object]:
    return {
        "system": f"AURIS v{APP_VERSION}",
        "uptime_utc": dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc).isoformat(),
        "baseline_freq_hz": 7.83,
        "coherence_reference": 0.9813,
        "engine": "temporal_aura_scan_ext.py",
        "earth_zip": str(_resolve_zip_path()),
    }


@app.post("/scan")
def scan_user(user: UserScan) -> Dict[str, object]:
    report = run_temporal_aura_scan(
        name=user.name,
        location=user.location,
        birth_date=user.birth_date,
        temporal_id=user.temporal_id,
        zip_path=str(_resolve_zip_path()),
    )
    return report


@app.post("/batch")
def batch_scan(users: List[UserScan]) -> Dict[str, object]:
    if not users:
        raise HTTPException(
            status_code=400, detail="Provide at least one user for batch scanning."
        )
    payload = [user.model_dump(exclude_none=True) for user in users]
    reports = batch_run_temporal_scans(payload, str(_resolve_zip_path()))
    return {"status": "Batch Complete", "results": reports}


@app.get("/seal/verify")
def verify_seal(
    hash: str = Query(..., description="SHA3-512 seal hash to verify")
) -> Dict[str, object]:
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
            "message": "Quantum Seal verified."
            if any(match["integrity"] for match in matches)
            else "Seal located but integrity mismatch.",
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
    uvicorn.run(
        "auris_network_interface_v3_2:app", host=host, port=port, reload=False
    )
