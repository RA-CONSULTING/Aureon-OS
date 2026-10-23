"""Lightweight registry that versions metric runs and hyper-parameters."""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict

import pandas as pd

CONFIG_PATH = Path("observatory/configs/metrics.yaml")


@dataclass
class MetricRun:
    run_id: str
    generated_at: datetime
    metrics_path: Path
    row_count: int

    @classmethod
    def from_frame(cls, frame: pd.DataFrame) -> "MetricRun":
        run_id = f"run-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        metrics_path = Path("/lake/marts/market_observatory_daily.parquet")
        frame.to_parquet(metrics_path, index=False)
        return cls(
            run_id=run_id,
            generated_at=datetime.utcnow(),
            metrics_path=metrics_path,
            row_count=len(frame),
        )


class RegistryClient:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load_metric_config(self) -> Dict[str, object]:
        import yaml  # Local import to avoid hard dependency

        if CONFIG_PATH.exists():
            with CONFIG_PATH.open() as fh:
                return yaml.safe_load(fh)
        return {}

    def log_run(self, run: MetricRun) -> None:
        payload = asdict(run)
        payload["generated_at"] = run.generated_at.isoformat()
        payload["metrics_path"] = str(run.metrics_path)

        runs = self._load_runs()
        runs.append(payload)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(runs, indent=2))

    def _load_runs(self) -> list[Dict[str, object]]:
        if not self.path.exists():
            return []
        return json.loads(self.path.read_text())
