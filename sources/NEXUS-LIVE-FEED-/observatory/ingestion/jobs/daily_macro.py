"""Macro ingestion job for FRED/World Bank/OECD public data."""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from observatory.storage.lake import RawLakeWriter
from observatory.storage.validation import DataQualityGate


SERIES = [
    {"id": "DGS10", "provider": "FRED"},
    {"id": "GDP", "provider": "WorldBank"},
]


def run_daily_macro_job(execution_date: datetime | None = None) -> None:
    execution_date = execution_date or datetime.utcnow()
    # Placeholder frame; replace with provider-specific client fetches.
    frame = pd.DataFrame(SERIES)

    writer = RawLakeWriter()
    raw_path = writer.write(dataset="macro_daily", data=frame, execution_date=execution_date)

    dq = DataQualityGate(expectation_suite="macro_daily")
    dq.validate(raw_path)
