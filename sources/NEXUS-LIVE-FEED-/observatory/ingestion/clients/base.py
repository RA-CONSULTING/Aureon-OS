"""Connector interfaces for pulling lawful, public market and macro data.

Implementations should:
- Authenticate only with API keys or OAuth tokens tied to provider accounts
- Fetch data into pandas/Polars DataFrames with explicit schemas
- Avoid storing secrets in code; rely on environment variables or secret managers
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterable

import pandas as pd


@dataclass
class FetchRequest:
    """Parameters describing a pull against a public provider."""

    dataset: str
    symbols: Iterable[str]
    start: str
    end: str
    interval: str | None = None


class DataConnector(ABC):
    """Abstract base class for connectors.

    Concrete implementations are free to use REST, CSV downloads, or other
    lawful public interfaces, but must adhere to the schema contracts defined
    in the architecture specification.
    """

    @abstractmethod
    def fetch(self, request: FetchRequest) -> pd.DataFrame:
        """Return a DataFrame matching the expected schema."""


class NullConnector(DataConnector):
    """Default connector used for documentation and dry-runs."""

    def fetch(self, request: FetchRequest) -> pd.DataFrame:  # pragma: no cover - example only
        columns = ["date_time", "symbol", "open", "high", "low", "close", "volume"]
        return pd.DataFrame(columns=columns)
