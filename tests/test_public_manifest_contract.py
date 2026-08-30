from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "public" / "manifest.json"


def test_public_manifest_is_one_complete_json_document() -> None:
    raw = MANIFEST_PATH.read_text(encoding="utf-8")

    manifest = json.loads(raw)

    assert raw.strip().endswith("}")
    assert set(manifest) == {"name", "version", "modules"}


def test_public_manifest_retains_the_complete_hnc_object() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    assert manifest["name"] == "Harmonic Nexus Core"
    assert manifest["version"] == "2.1.0"
    assert set(manifest["modules"]) == {
        "HarmonicNexusCore",
        "SchumannFeed",
        "BiofieldStream",
        "PrimeLattice",
    }
    assert manifest["modules"]["HarmonicNexusCore"]["id"] == "hnc-core"
    assert manifest["modules"]["SchumannFeed"]["frequency"] == "7.83Hz"
