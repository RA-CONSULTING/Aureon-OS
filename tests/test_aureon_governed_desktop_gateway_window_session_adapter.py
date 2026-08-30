from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aureon.autonomous.aureon_governed_desktop_gateway import (
    DesktopGatewayError,
    EvidenceWriteError,
    GovernedDesktopGateway,
    WindowInfo,
)


class ExactWindowBackend:
    def __init__(self) -> None:
        self.window = WindowInfo(
            handle=71,
            title="SCORM Cloud - Microsoft Edge",
            process_id=4100,
            left=10,
            top=20,
            width=1200,
            height=800,
        )

    def foreground_window(self) -> WindowInfo:
        return self.window


def make_gateway(tmp_path: Path) -> tuple[GovernedDesktopGateway, ExactWindowBackend, Path]:
    backend = ExactWindowBackend()
    evidence = tmp_path / "gateway.jsonl"
    gateway = GovernedDesktopGateway(
        backend=backend,  # type: ignore[arg-type]
        evidence_path=evidence,
        utc_now=lambda: datetime(2026, 8, 16, 12, 0, tzinfo=UTC),
    )
    return gateway, backend, evidence


def rows(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_exact_replace_commits_evidence_before_one_active_binding(tmp_path: Path) -> None:
    gateway, backend, evidence = make_gateway(tmp_path)

    first = gateway.replace_target_window_binding(
        previous_binding_id=None,
        window=backend.window,
    )

    assert first.window == backend.window
    assert gateway.require_single_target_binding_id() == first.binding_id
    assert [row["event"] for row in rows(evidence)] == ["target_window_binding_replaced"]

    backend.window = replace(backend.window, handle=72, title="Course Player - Microsoft Edge")
    second = gateway.replace_target_window_binding(
        previous_binding_id=first.binding_id,
        window=backend.window,
    )

    assert second.binding_id != first.binding_id
    assert second.window == backend.window
    assert gateway.require_single_target_binding_id() == second.binding_id
    assert rows(evidence)[-1]["previous_binding_id"] == first.binding_id


@pytest.mark.parametrize(
    "changed",
    [
        {"handle": 72},
        {"process_id": 4101},
        {"title": "Different title"},
        {"left": 11},
    ],
)
def test_exact_replace_rejects_any_foreground_identity_mismatch(
    tmp_path: Path,
    changed: dict[str, object],
) -> None:
    gateway, backend, _evidence = make_gateway(tmp_path)
    supplied = replace(backend.window, **changed)

    with pytest.raises(DesktopGatewayError, match="exact_target_window_mismatch"):
        gateway.replace_target_window_binding(previous_binding_id=None, window=supplied)

    assert gateway.status()["binding_count"] == 0


def test_exact_replace_cas_and_multiple_legacy_bindings_fail_closed(tmp_path: Path) -> None:
    gateway, backend, _evidence = make_gateway(tmp_path)
    first = gateway.replace_target_window_binding(previous_binding_id=None, window=backend.window)

    with pytest.raises(DesktopGatewayError, match="compare_and_swap_failed"):
        gateway.replace_target_window_binding(
            previous_binding_id="wrong-binding",
            window=backend.window,
        )
    assert gateway.require_single_target_binding_id() == first.binding_id

    gateway.bind_target_window(backend.window.title, expected_process_id=backend.window.process_id)
    with pytest.raises(DesktopGatewayError, match="multiple_target_window_bindings_active"):
        gateway.replace_target_window_binding(
            previous_binding_id=first.binding_id,
            window=backend.window,
        )


def test_replace_evidence_failure_preserves_previous_binding(tmp_path: Path) -> None:
    gateway, backend, _evidence = make_gateway(tmp_path)
    first = gateway.replace_target_window_binding(previous_binding_id=None, window=backend.window)
    blocked_path = tmp_path / "not-a-ledger"
    blocked_path.mkdir()
    gateway.evidence_path = blocked_path
    backend.window = replace(backend.window, title="Changed - Microsoft Edge")

    with pytest.raises(EvidenceWriteError, match="append_only_evidence_write_failed"):
        gateway.replace_target_window_binding(
            previous_binding_id=first.binding_id,
            window=backend.window,
        )

    assert gateway.require_single_target_binding_id() == first.binding_id


def test_release_removes_binding_even_if_release_evidence_fails(tmp_path: Path) -> None:
    gateway, backend, _evidence = make_gateway(tmp_path)
    first = gateway.replace_target_window_binding(previous_binding_id=None, window=backend.window)
    blocked_path = tmp_path / "not-a-ledger"
    blocked_path.mkdir()
    gateway.evidence_path = blocked_path

    with pytest.raises(EvidenceWriteError, match="append_only_evidence_write_failed"):
        gateway.release_target_window_binding(first.binding_id)

    assert gateway.status()["binding_count"] == 0
    with pytest.raises(DesktopGatewayError, match="release_mismatch"):
        gateway.release_target_window_binding(first.binding_id)
