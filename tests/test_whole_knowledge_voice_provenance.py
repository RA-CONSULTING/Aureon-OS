from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "aureon"
    / "vault"
    / "voice"
    / "whole_knowledge_voice.py"
)


def _load_module():
    module_name = "whole_knowledge_voice_provenance_under_test"
    spec = importlib.util.spec_from_file_location(module_name, MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _assert_control_boundary(value) -> None:
    assert value.content_class == "generated_voice_control_content"
    assert value.operational_eligible is False
    assert value.accounting_eligible is False
    assert value.learning_eligible is False
    assert value.provider_verified is False
    assert value.requires_operator_review is True

    try:
        value.operational_eligible = True
    except AttributeError:
        pass
    else:
        raise AssertionError("generated control content must not be promotable by assignment")

    payload = value.to_dict()
    assert payload["operational_eligible"] is False
    assert payload["accounting_eligible"] is False
    assert payload["learning_eligible"] is False
    assert payload["provider_verified"] is False
    assert payload["forbidden_evidence_uses"] == ["action", "accounting", "learning"]


def test_generated_voice_outputs_remain_control_content(tmp_path: Path) -> None:
    voice = _load_module()
    source_path = tmp_path / "operator_note.txt"
    source_path.write_text(
        "A verified operator note can inform presentation, but generated prose is not a provider receipt.",
        encoding="utf-8",
    )
    artifact_dir = tmp_path / "artifacts"

    profile = voice.build_expression_profile(
        root=tmp_path,
        source_paths=[source_path],
        evidence_dir=artifact_dir,
        publish=True,
    )
    translation = voice.translate_runtime_state(
        {"state": {"mood": "steady", "action": "observe", "topic": "operator review"}}
    )
    artifact = voice.compose_voice_artifact(
        "explain the current state",
        evidence={"state": {"mood": "steady", "action": "observe"}},
        profile=profile,
        root=tmp_path,
        evidence_dir=artifact_dir,
        publish=True,
    )

    _assert_control_boundary(profile.sources[0])
    _assert_control_boundary(profile)
    _assert_control_boundary(translation)
    _assert_control_boundary(artifact)

    profile_payload = json.loads((artifact_dir / "aureon_expression_profile.json").read_text(encoding="utf-8"))
    artifact_payload = json.loads((artifact_dir / "aureon_voice_last_run.json").read_text(encoding="utf-8"))
    assert profile_payload["operational_eligible"] is False
    assert profile_payload["sources"][0]["learning_eligible"] is False
    assert artifact_payload["operational_eligible"] is False
    assert artifact_payload["runtime_translation"]["accounting_eligible"] is False
    assert "internally computed state" in artifact_payload["runtime_translation"]["summary"]
