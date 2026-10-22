"""Batch job that lands daily OHLCV candles into the raw lake.

The job reads universes from `configs/universes.yaml`, fetches data using
configured connectors, writes Parquet files to the raw zone, and triggers
Great Expectations validations before promotion.
"""

from __future__ import annotations

import pathlib
from datetime import datetime, timedelta

from observatory.ingestion.clients.base import FetchRequest
from observatory.ingestion.clients.yahoo import YahooConnector
from observatory.storage.lake import RawLakeWriter
from observatory.storage.validation import DataQualityGate


def run_daily_prices_job(execution_date: datetime | None = None) -> None:
    """Entry point for Airflow/Prefect."""

    execution_date = execution_date or datetime.utcnow() - timedelta(days=1)
    target_date = execution_date.date().isoformat()

    connector = YahooConnector()
    request = FetchRequest(
        dataset="prices_daily",
        symbols=["SPY", "QQQ"],
        start=target_date,
        end=target_date,
    )
    frame = connector.fetch(request)

    raw_writer = RawLakeWriter(root=pathlib.Path("/lake/raw"))
    raw_path = raw_writer.write(dataset="prices_daily", data=frame, execution_date=execution_date)

    dq = DataQualityGate(expectation_suite="prices_daily")
    dq.validate(raw_path)

    # Promotion to cleaned/validated zones handled downstream by orchestration.
