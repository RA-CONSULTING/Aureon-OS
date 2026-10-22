"""Lake IO helpers implementing the raw/clean/validated layout."""

from __future__ import annotations

import pathlib
from datetime import datetime

import pandas as pd


class RawLakeWriter:
    """Write immutable Parquet files into the raw zone."""

    def __init__(self, root: pathlib.Path | None = None) -> None:
        self.root = root or pathlib.Path("/lake/raw")

    def write(self, dataset: str, data: pd.DataFrame, execution_date: datetime) -> pathlib.Path:
        partition = execution_date.strftime("%Y/%m/%d")
        path = self.root / dataset / partition / f"{dataset}.parquet"
        path.parent.mkdir(parents=True, exist_ok=True)
        data.to_parquet(path, index=False)
        return path
