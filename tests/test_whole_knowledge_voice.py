"""Pure translation tests and fail-closed whole-knowledge execution tests."""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from aureon.vault.voice.whole_knowledge_voice import (
    WHOLE_KNOWLEDGE_VOICE_RELEASE_HOLD,
    build_expression_profile,
    compose_voice_artifact,
    _default_source_paths,
    _extract_docx_paragraphs,
    _read_source_text,
    translate_runtime_state,
)


def test_runtime_state_translation_uses_senses_and_redacts() -> None:
    translated = translate_runtime_state(
        {
            "runtime_state": {
                "mood": "FOCUSED",
                "coherence": 0.84,
                "resonance_frequency_hz": 528,
                "hot_topic": "market pulse",
                "n_tools": 49,
                "runtime_stale": True,
            },
            "API_SECRET": "do-not-emit",
        }
    )
    assert "market pulse" in translated.senses["see"]
    assert "528.00 Hz" in translated.senses["hear"]
    assert "runtime_stale" in translated.blockers
    assert translated.redaction_applied
    assert "do-not-emit" not in json.dumps(translated.to_dict())


def test_runtime_translation_redacts_nested_credential_values_recursively() -> None:
    secrets = [
        "sk-proj-FAKESECRET000000000000",
        "ghp_FAKESECRET000000000000",
        "AKIAFAKESECRET0000",
        "FAKESECRETXYZ",
        "BearerSuffixFAKE000",
    ]
    translated = translate_runtime_state(
        {
            "runtime_state": {
                "mood": secrets[0],
                "action": f"Bearer {secrets[4]}",
                "hot_topic": secrets[1],
                "blockers": [
                    f"password={secrets[3]}",
                    secrets[2],
                    {"token": "nested-FAKESECRET"},
                ],
            },
            "API_SECRET": "top-level-FAKESECRET",
        }
    )
    dumped = json.dumps(translated.to_dict(), sort_keys=True)
    for secret in secrets:
        assert secret not in dumped
    assert "nested-FAKESECRET" not in dumped
    assert "top-level-FAKESECRET" not in dumped
    assert translated.redaction_applied is True
    assert translated.blockers


def test_public_execution_defaults_are_non_publishing() -> None:
    assert inspect.signature(build_expression_profile).parameters["publish"].default is False
    assert inspect.signature(compose_voice_artifact).parameters["publish"].default is False
    assert WHOLE_KNOWLEDGE_VOICE_RELEASE_HOLD.startswith("whole_knowledge_voice_hold:")


@pytest.mark.parametrize("entrypoint", ["profile", "artifact"])
def test_profile_and_artifact_hold_before_read_or_write(
    entrypoint: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        Path,
        "exists",
        lambda *_args, **_kwargs: pytest.fail("held voice path must not probe sources"),
    )
    monkeypatch.setattr(
        Path,
        "mkdir",
        lambda *_args, **_kwargs: pytest.fail("held voice path must not create directories"),
    )
    calls = {
        "profile": lambda: build_expression_profile(
            root=tmp_path,
            source_paths=[tmp_path / "secret.md"],
            evidence_dir=tmp_path,
            publish=True,
        ),
        "artifact": lambda: compose_voice_artifact(
            "speak", root=tmp_path, evidence_dir=tmp_path, publish=True,
        ),
    }
    with pytest.raises(RuntimeError, match="whole_knowledge_voice_hold"):
        calls[entrypoint]()
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("entrypoint", ["discover", "text", "docx"])
def test_direct_source_readers_hold_before_filesystem_or_zip_access(
    entrypoint: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def _fail(*_args, **_kwargs):
        pytest.fail("held source reader touched the filesystem")

    for name in ("exists", "resolve", "glob", "read_text"):
        monkeypatch.setattr(Path, name, _fail)
    monkeypatch.setattr(
        "aureon.vault.voice.whole_knowledge_voice.ZipFile",
        _fail,
    )
    path = tmp_path / "private.docx"
    calls = {
        "discover": lambda: _default_source_paths(tmp_path, max_sources=10),
        "text": lambda: _read_source_text(path, max_chars=100),
        "docx": lambda: _extract_docx_paragraphs(path, max_paragraphs=10),
    }
    with pytest.raises(RuntimeError, match="whole_knowledge_voice_hold"):
        calls[entrypoint]()
