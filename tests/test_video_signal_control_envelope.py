"""Offline contract tests for immutable video statistical controls."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from aureon.bio import human_harmonic_proxy as proxy
from aureon.bio import video_signal_adapter as video
from scripts.validation.validate_real_data_contract import scan_text_file


def _assert_non_operational(value) -> None:
    assert value.data_origin == "derived_statistical_control"
    assert value.truth_status == "statistical_control"
    assert value.generated_values is True
    assert value.control_only is True
    assert value.live_data is False
    assert value.provider_observation is False
    assert value.operational_eligible is False
    assert value.action_eligible is False
    assert value.actionable is False
    assert value.accounting_eligible is False
    assert value.learning_eligible is False
    assert value.provider_eligible is False


def test_control_generator_is_frozen_canonical_and_compatibility_safe() -> None:
    control = video.control_video("structured")
    assert isinstance(control, video.VideoControlEnvelope)
    assert control.provenance == "bio.control.video.structured"
    _assert_non_operational(control)

    frames = control.as_frames()
    assert frames.shape == (4000, 4, 4)
    assert frames.flags.writeable is False
    with pytest.raises(ValueError):
        frames[0, 0, 0] = 1.0

    compatibility = video.synthetic_video("noise", seed=7)
    assert isinstance(compatibility, video.VideoControlEnvelope)
    assert compatibility.provenance == "bio.control.video.noise"
    _assert_non_operational(compatibility)


def test_control_cannot_be_relabelled_or_have_its_frame_rate_replaced() -> None:
    control = video.control_video("structured")
    relabelled = replace(
        control,
        provenance="provider.camera.live",
        generated_values=False,
        control_only=False,
        live_data=True,
        provider_observation=True,
        operational_eligible=True,
        action_eligible=True,
        actionable=True,
        learning_eligible=True,
        provider_eligible=True,
    )
    with pytest.raises(ValueError, match="invalid or relabelled"):
        video.VideoSignalAdapter().extract(
            relabelled,
            consent=True,
            provenance="claimed live camera",
        )
    with pytest.raises(ValueError, match="cannot relabel"):
        video.VideoSignalAdapter().extract(
            control,
            consent=True,
            provenance="controlled assay",
            frame_rate_hz=control.frame_rate_hz * 2.0,
        )


def test_unreceipted_arrays_are_control_only_and_caller_text_cannot_promote_them() -> None:
    frame_rate_hz = 128.0
    t = np.arange(256, dtype=float) / frame_rate_hz
    frames = np.repeat(
        np.sin(2.0 * np.pi * 8.0 * t)[:, None, None],
        4,
        axis=1,
    )
    signal = video.VideoSignalAdapter().extract(
        frames,
        consent=True,
        provenance="claimed provider-live video",
        frame_rate_hz=frame_rate_hz,
    )
    assert signal.provenance == "bio.control.video.unverified_input"
    _assert_non_operational(signal)


def test_governed_score_retains_control_classification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        proxy,
        "_get_conscience",
        lambda: SimpleNamespace(
            ask_why=lambda *_args, **_kwargs: SimpleNamespace(
                verdict=SimpleNamespace(name="APPROVED")
            )
        ),
    )
    result = video.score_video(
        video.control_video("structured"),
        consent=True,
        provenance="declared statistical assay",
        nulls=120,
    )
    payload = result.to_dict()
    assert result.valid is True
    assert result.structure_present is True
    assert payload["control_only"] is True
    assert payload["data_origin"] == "derived_statistical_control"
    assert payload["truth_status"] == "statistical_control"
    assert payload["provider_observation"] is False
    assert payload["operational_eligible"] is False
    assert payload["actionable"] is False
    assert payload["accounting_eligible"] is False


def test_exact_hardened_validator_is_clean() -> None:
    target = Path(video.__file__).resolve()
    root = Path(__file__).resolve().parents[1]
    assert scan_text_file(target, root) == []
