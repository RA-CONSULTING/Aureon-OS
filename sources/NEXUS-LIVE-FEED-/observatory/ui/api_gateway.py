"""FastAPI gateway exposing Observatory metrics."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import io

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

app = FastAPI(title="Observatory API", version="0.1.0")

METRICS_PATH = Path("/lake/marts/market_observatory_daily.parquet")


def _load_metrics() -> pd.DataFrame:
    if not METRICS_PATH.exists():
        raise HTTPException(status_code=503, detail="Metrics not available yet")
    return pd.read_parquet(METRICS_PATH)


@app.get("/v1/markets/cci")
def get_cci(symbol: str, start: date, end: date):
    frame = _load_metrics()
    subset = frame[(frame["symbol"] == symbol) & (frame["date"] >= pd.Timestamp(start)) & (frame["date"] <= pd.Timestamp(end))]
    return subset[["date", "symbol", "CCI", "cci_state"]].to_dict(orient="records")


@app.get("/v1/observatory/coherence")
def get_coherence(date: date):
    frame = _load_metrics()
    subset = frame[frame["date"] == pd.Timestamp(date)]
    if subset.empty:
        raise HTTPException(status_code=404, detail="Date not found")
    row = subset.iloc[0]
    return {
        "date": row["date"].date().isoformat(),
        "coherence_score": float(row["coherence_score"]),
        "unity": float(row["unity_index"]),
        "inercha": float(row["inercha_speed"]),
    }


@app.get("/v1/downloads/integrity_daily.parquet")
def download_integrity():
    frame = _load_metrics()
    output = frame[["date", "symbol", "integrity_perturbation"]]
    buffer = io.BytesIO()
    output.to_parquet(buffer, index=False)
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/octet-stream",
        headers={"Content-Disposition": "attachment; filename=integrity_daily.parquet"},
    )
