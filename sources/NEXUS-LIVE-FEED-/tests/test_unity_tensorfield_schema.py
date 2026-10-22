import json
import sys
from pathlib import Path

import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lattice_integration import UnityTensorField


def test_tensor_field_from_path_supports_metadata(tmp_path: Path) -> None:
    dataset = {
        "version": "1.1",
        "schema": {
            "phi": "float (radians, [-pi, pi])",
            "kappa": "float (radians, [-pi, pi])",
            "psi": "float (0..1)",
            "TSV": "float (tensor scalar value)",
        },
        "derived_metrics": {
            "gamma_projection": "1 - std(TSV)/abs(mean(TSV))",
            "mirror_lock": "mean(TSV) < 0 → invert phase for Γ⁺",
        },
        "validation": {
            "min_rows": 2,
            "required_fields": ["phi", "kappa", "psi", "TSV"],
        },
        "samples": [
            {"phi": 0.0, "kappa": 0.0, "psi": 0.2, "TSV": 0.6},
            {"phi": 0.1, "kappa": 0.1, "psi": 0.3, "TSV": 0.8},
            {"phi": 0.2, "kappa": -0.1, "psi": 0.4, "TSV": 0.4},
        ],
    }
    path = tmp_path / "unity_field.json"
    path.write_text(json.dumps(dataset))

    field = UnityTensorField.from_path(path)

    assert field.version == "1.1"
    assert field.schema is not None
    assert field.derived_metric_definitions is not None
    assert len(field.samples) == 3
    assert pytest.approx(field.sample(0.1, 0.1, 0.3)) == 0.8

    # gamma_projection = 1 - std/abs(mean)
    tsv_values = np.array([0.6, 0.8, 0.4], dtype=float)
    mean_value = float(np.mean(tsv_values))
    std_value = float(np.std(tsv_values))
    expected_gamma = 1.0 - std_value / abs(mean_value)
    assert field.gamma_projection == pytest.approx(expected_gamma)
    assert field.mirror_lock is False
    assert field.derived_metrics["mirror_lock"] is False


def test_tensor_field_detects_mirror_lock() -> None:
    field = UnityTensorField(
        samples=[
            {"phi": 0.0, "kappa": 0.0, "psi": 0.0, "TSV": -0.5},
            {"phi": 0.1, "kappa": 0.1, "psi": 0.1, "TSV": -0.2},
        ]
    )

    assert field.mirror_lock is True
    assert field.gamma_projection == pytest.approx(1.0 - 0.15 / 0.35)
    assert all("TSV" not in sample for sample in field.samples)
