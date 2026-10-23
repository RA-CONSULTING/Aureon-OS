"""Airflow DAG that orchestrates the Observatory daily batch runs.

This DAG follows the architecture brief:
- Ingest public market, macro, and optional resonance feeds
- Apply data quality checks before promoting to the cleaned zone
- Compute feature + metric marts
- Publish artifacts for APIs and downloads

The implementation is idempotent: reruns for the same date overwrite
only the cleaned/validated zones after expectations succeed.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator

from observatory.ingestion.jobs.daily_prices import run_daily_prices_job
from observatory.ingestion.jobs.daily_macro import run_daily_macro_job
from observatory.metrics.engine import build_daily_metrics
from observatory.metrics.registry import register_run


DEFAULT_ARGS = {
    "owner": "observatory",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=15),
}


with DAG(
    dag_id="observatory_daily",
    default_args=DEFAULT_ARGS,
    description="Observatory daily transparency pipeline",
    schedule_interval="0 3 * * *",  # 03:00 UTC daily
    start_date=datetime(2024, 1, 1),
    catchup=True,
    max_active_runs=1,
    tags=["observatory", "transparency"],
) as dag:
    start = EmptyOperator(task_id="start")

    ingest_prices = PythonOperator(
        task_id="ingest_prices",
        python_callable=run_daily_prices_job,
    )

    ingest_macro = PythonOperator(
        task_id="ingest_macro",
        python_callable=run_daily_macro_job,
    )

    compute_metrics = PythonOperator(
        task_id="compute_metrics",
        python_callable=build_daily_metrics,
    )

    finalize_run = PythonOperator(
        task_id="finalize_run",
        python_callable=register_run,
    )

    end = EmptyOperator(task_id="end")

    start >> [ingest_prices, ingest_macro]
    [ingest_prices, ingest_macro] >> compute_metrics >> finalize_run >> end
