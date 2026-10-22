# Observatory Starter Layout

This starter layout codifies the "Observatory" technical architecture for building an open, ethical market transparency platform. The structure is intentionally modular so teams can replace components with cloud-managed or self-hosted equivalents without rewriting the domain logic.

## Directory guide

- `configs/` — declarative YAML that captures universes, metric hyper-parameters, and quality gates for reproducibility.
- `infrastructure/` — orchestration entry points (Airflow DAG, Prefect flow) and IaC snippets to bootstrap the lake, catalog, and API surface.
- `ingestion/` — reusable connectors and jobs that land public data into the raw lake.
- `metrics/` — feature engineering and score computation pipelines plus the lightweight registry for versioning runs.
- `storage/` — documentation of the lake layout, marts, and governance practices.
- `ui/` — the "Prism" dashboard scaffold (Streamlit MVP) and API client helpers.
- `notebooks/` — reproducible research starter with a template notebook.
- `tests/` — unit tests for connector contracts, data quality rules, and metric definitions.

## Usage

1. Populate secrets (API keys, bucket names) through your chosen secret manager; this layout never stores them in code.
2. Configure `configs/universes.yaml` and `configs/metrics.yaml` to match the markets you want to observe.
3. Deploy the orchestration layer of choice (Airflow or Prefect) using the templates in `infrastructure/`.
4. Point the ingestion jobs at your object store and run; data quality gates will block promotion to the validated mart until expectations pass.
5. Expose metrics through the FastAPI application in `ui/api_gateway.py` and render the Streamlit Prism in `ui/prism_app.py`.

Each component is documented inline so teams can extend or swap technologies without breaking the integrity of the Observatory.
