# Observatory Technical Architecture

This document packages the production-grade blueprint for the Observatory — an open, ethical market telemetry stack that ingests lawful public data and ships replicable metrics.

## Logical flow

```
[Public Data Feeds] --> [Ingestion Layer] --> [Raw Lake]
                                   |--> [Quality & Governance]
[Jobs Scheduler] ------------------'            |
                                                v
                                   [Feature & Metrics Engine] --> [Validated Mart]
                                                |           \--> [Model Registry]
                                                v
                                          [API Gateway]
                                                |
                    -------------------------------------------------
                    |                    |                          |
             [Explorer UI]        [Research Notebooks]         [Exports/Downloads]
```

## Components

### Data sources
- Markets: Yahoo/AlphaVantage/Tiingo/Polygon, official exchange bulk.
- Macro: FRED, IMF, World Bank, OECD.
- Space weather/resonance (optional): NOAA SWPC, Schumann proxies, GWOSC.
- News meta (optional): GDELT/NewsAPI headlines.

### Ingestion & storage
- Batch orchestration via Airflow (`observatory/infrastructure/airflow_observatory_dag.py`) or Prefect (`observatory/infrastructure/prefect_flow.py`).
- Optional Kafka topics for intraday streaming (`prices.ticks`, `prices.1m`, `events.macro`).
- Parquet layout across raw/clean/validated zones described in `observatory/storage/README.md`.
- Governance through OpenMetadata/DataHub and Great Expectations (wrapped in `observatory/storage/validation.py`).

### Metrics
- Implementation of Integrity (Dₜ), CCI, Polaris ΔCₜ, Choerance Φₜ, Ping–Pong Pₜ, Grav reflection Gₜ, Unity Uₜ, Inercha 𝓘ₜ, and the Coherence Index lives in `observatory/metrics/engine.py`.
- Runs are versioned via the lightweight registry in `observatory/metrics/registry.py`, referencing declarative hyper-parameters in `observatory/configs/metrics.yaml`.

### Serving & experience
- Public FastAPI gateway (`observatory/ui/api_gateway.py`) exposes read-only endpoints for metrics and downloads.
- Streamlit Prism (`observatory/ui/prism_app.py`) renders dashboards with formulas, explainers, and export controls.
- Research notebooks are organized in `observatory/notebooks/` with reproducibility checklists.

### Operations
- Quality gates defined in `observatory/configs/quality_gates.yaml` enforce freshness, completeness, and anomaly bounds.
- SLOs and monitoring integrate via Prometheus/Grafana (hooks left to implement in infrastructure layer).
- Deployment options span OSS-first (MinIO, Postgres/Timescale, MLflow) or cloud-managed (AWS-native).

### Rollout roadmap
1. Sprint 1: lake bootstrap, daily OHLCV ingestion, Integrity metrics, Prism MVP.
2. Sprint 2: CCI, validation gating, public downloads.
3. Sprint 3: Polaris & Choerance metrics with compass views.
4. Sprint 4: Ping–Pong resonance overlay with disclaimers.
5. Sprint 5: Unity/Inercha gauges and monthly reproducible packs.
6. Sprint 6: Hardening (SLOs, caching, documentation, contributor guide).

All code in `observatory/` is vendor-agnostic; swap connectors, orchestration engines, or storage backends by replacing the corresponding modules while preserving interfaces.
