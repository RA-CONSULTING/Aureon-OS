"""Prefect deployment mirroring the daily Airflow DAG."""

from __future__ import annotations

from datetime import datetime

from prefect import flow, task

from observatory.ingestion.jobs.daily_prices import run_daily_prices_job
from observatory.ingestion.jobs.daily_macro import run_daily_macro_job
from observatory.metrics.engine import build_daily_metrics


@task
def ingest_prices_task(execution_date: datetime | None = None) -> None:
    run_daily_prices_job(execution_date)


@task
def ingest_macro_task(execution_date: datetime | None = None) -> None:
    run_daily_macro_job(execution_date)


@task
def compute_metrics_task() -> None:
    build_daily_metrics()


@flow(name="observatory-daily")
def observatory_daily_flow(execution_date: datetime | None = None) -> None:
    ingest_prices_task(execution_date)
    ingest_macro_task(execution_date)
    compute_metrics_task()
