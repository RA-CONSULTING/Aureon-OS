"""Lightweight wrapper around data quality tooling (Great Expectations)."""

from __future__ import annotations

import pathlib


class DataQualityGate:
    def __init__(self, expectation_suite: str) -> None:
        self.expectation_suite = expectation_suite

    def validate(self, path: pathlib.Path) -> None:  # pragma: no cover - stub
        # Integrate Great Expectations or Soda here.
        # For the starter layout we simply log intent.
        print(f"Validating {path} with suite {self.expectation_suite}")
