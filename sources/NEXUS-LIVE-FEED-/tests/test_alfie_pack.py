import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from alfie import bootstrap_from_manifest  # noqa: E402
from alfie.loader import LayerLoadError  # noqa: E402
from alfie.manifest import ManifestValidationError, compute_checksum  # noqa: E402

MANIFEST_PATH = PROJECT_ROOT / "alfie_sandbox_manifest.json"


def test_bootstrap_from_manifest() -> None:
    pack = bootstrap_from_manifest(MANIFEST_PATH)

    assert pack.metadata.id == "alfie-evolution-pack"
    assert pack.metadata.version == "1.0.0"
    assert pack.context.state["safeguards"]["free_will_invariant"] is True
    assert "consent-before-action" in pack.context.ethics_registry
    assert pack.context.state["harmonics"]["status"] == "green"
    assert [layer.id for layer in pack.layers] == [
        "foundation.core-alignment",
        "ethics.guardian",
        "harmonics.resonance",
    ]
    assert pack.context.audit_log[-1] == "pack_bootstrapped"


def test_manifest_checksum_guard(tmp_path: Path) -> None:
    tampered = tmp_path / "tampered_manifest.json"
    data = json.loads(MANIFEST_PATH.read_text())
    data["layers"][0]["name"] = "Tampered Core Alignment"
    # Keep the original checksum to trigger validation failure.
    tampered.write_text(json.dumps(data, indent=2))

    with pytest.raises(ManifestValidationError):
        bootstrap_from_manifest(tampered)


def test_dependency_enforcement(tmp_path: Path) -> None:
    reordered = tmp_path / "reordered_manifest.json"
    data = json.loads(MANIFEST_PATH.read_text())
    # Swap the first two layers so dependencies are violated.
    data["layers"] = [data["layers"][1], data["layers"][0], data["layers"][2]]
    data["checksum"] = compute_checksum(
        {
            "schema_version": data["schema_version"],
            "generated_at": data["generated_at"],
            "pack": data["pack"],
            "layers": data["layers"],
        }
    )
    reordered.write_text(json.dumps(data, indent=2))

    with pytest.raises(LayerLoadError):
        bootstrap_from_manifest(reordered)
