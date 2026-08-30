"""Deterministic statistical-null sequences for bio calibration.

These values are methodological controls, never provider observations. They
are derived reproducibly from a declared seed and are not permitted to enter
live telemetry. A low-discrepancy sequence gives stable envelope coverage
without runtime random-data generation.
"""

from __future__ import annotations

import hashlib
import math
from statistics import NormalDist
from typing import Sequence

import numpy as np


class DerivedNullGenerator:
    """Small NumPy-generator-compatible deterministic null source."""

    truth_status = "statistical_null"

    def __init__(self, seed_parts: int | Sequence[int]):
        if isinstance(seed_parts, int):
            parts = (seed_parts,)
        else:
            parts = tuple(int(value) for value in seed_parts)
        digest = hashlib.sha256(",".join(map(str, parts)).encode("utf-8")).digest()
        self._offset = int.from_bytes(digest[:8], "big") / float(2**64)
        self._cursor = 0

    @staticmethod
    def _shape(size: int | tuple[int, ...] | None) -> tuple[int, ...]:
        if size is None:
            return ()
        if isinstance(size, int):
            return (size,)
        return tuple(int(value) for value in size)

    def _unit(self, size: int | tuple[int, ...] | None):
        shape = self._shape(size)
        count = int(np.prod(shape)) if shape else 1
        start = self._cursor + 1
        self._cursor += count
        indices = np.arange(start, start + count, dtype=float)
        # Golden-ratio conjugate: deterministic low-discrepancy coverage [0, 1).
        values = np.mod(self._offset + indices * ((math.sqrt(5.0) - 1.0) / 2.0), 1.0)
        if not shape:
            return float(values[0])
        return values.reshape(shape)

    def uniform(self, low=0.0, high=1.0, size=None):
        unit = self._unit(size)
        return float(low) + (float(high) - float(low)) * unit

    def standard_normal(self, size=None):
        unit = self._unit(size)
        eps = np.finfo(float).eps
        clipped = np.clip(unit, eps, 1.0 - eps)
        inverse = np.vectorize(NormalDist().inv_cdf, otypes=[float])
        values = inverse(clipped)
        if size is None:
            return float(values)
        return values

    def normal(self, loc=0.0, scale=1.0, size=None):
        return float(loc) + float(scale) * self.standard_normal(size)


def derived_null_generator(*seed_parts: int) -> DerivedNullGenerator:
    """Create an explicitly labeled deterministic statistical-null stream."""

    return DerivedNullGenerator(seed_parts)
