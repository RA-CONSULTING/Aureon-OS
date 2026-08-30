from __future__ import annotations

import ctypes
import ctypes.wintypes
import hashlib
import io
import json
import sys
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from aureon.autonomous.aureon_governed_desktop_gateway import (
    MAX_LEASE_SECONDS,
    AuthorizationError,
    DesktopBackendError,
    DesktopGatewayError,
    GovernedDesktopGateway,
    LazyPyAutoGUIBackend,
    PostconditionResult,
    WindowInfo,
)


class FakeClock:
    def __init__(self) -> None:
        self.current = datetime(2026, 8, 16, 12, 0, tzinfo=UTC)
        self.tick = 1000.0

    def now(self) -> datetime:
        return self.current

    def monotonic(self) -> float:
        return self.tick

    def advance(self, seconds: float) -> None:
        self.current += timedelta(seconds=seconds)
        self.tick += seconds


class FakeBackend:
    def __init__(self) -> None:
        self.window = WindowInfo(
            handle=77,
            title="Course Browser",
            process_id=4242,
            left=10,
            top=10,
            width=790,
            height=590,
        )
        self.width = 1024
        self.height = 768
        self.frame = 0
        self.cursor = (5, 7)
        self.actions: list[tuple] = []
        self.image_bytes = self._png((20, 40, 60, 255))
        self.dpi: tuple[float, float] | None = (96.0, 96.0)

    def _png(self, color: tuple[int, int, int, int]) -> bytes:
        image = Image.new("RGBA", (self.width, self.height), color)
        output = io.BytesIO()
        image.save(output, format="PNG")
        return output.getvalue()

    def _changed(self) -> None:
        self.frame += 1
        self.image_bytes = self._png((20 + self.frame, 40, 60, 255))

    def capture_screen(self) -> bytes:
        return self.image_bytes

    def screen_size(self) -> tuple[int, int]:
        return self.width, self.height

    def foreground_window(self) -> WindowInfo:
        return self.window

    def window_dpi(self, window: WindowInfo) -> tuple[float, float] | None:
        assert window.handle == self.window.handle
        return self.dpi

    def pointer_position(self) -> tuple[int, int]:
        return self.cursor

    def move(self, x: int, y: int, duration: float = 0.0) -> None:
        self.actions.append(("move", x, y, duration))
        self.cursor = (x, y)
        self._changed()

    def click(self, x: int, y: int, button: str = "left", clicks: int = 1) -> None:
        self.actions.append(("click", x, y, button, clicks))
        self.cursor = (x, y)
        self._changed()

    def scroll(self, amount: int, x: int, y: int) -> None:
        self.actions.append(("scroll", amount, x, y))
        self.cursor = (x, y)
        self._changed()

    def type_text(self, text: str, interval: float = 0.02) -> None:
        self.actions.append(("type", text, interval))
        self._changed()

    def press(self, key: str) -> None:
        self.actions.append(("press", key))
        self._changed()

    def hotkey(self, keys: list[str]) -> None:
        self.actions.append(("hotkey", tuple(keys)))
        self._changed()


class PixelBackend(FakeBackend):
    def __init__(self) -> None:
        super().__init__()
        self.width = 6
        self.height = 4
        self.window = WindowInfo(
            handle=77,
            title="Course Browser",
            process_id=4242,
            left=2,
            top=1,
            width=3,
            height=2,
        )
        image = Image.new("RGBA", (self.width, self.height))
        for y in range(self.height):
            for x in range(self.width):
                image.putpixel((x, y), (10 + x, 20 + y, 30 + x + y, 255))
        output = io.BytesIO()
        image.save(output, format="PNG")
        self.raw_png = output.getvalue()

    def capture_screen(self) -> bytes:
        return self.raw_png


class DriftAtDispatchLinearizationBackend(PixelBackend):
    def __init__(self) -> None:
        super().__init__()
        self.capture_calls = 0
        self.drift_enabled = True

    def capture_screen(self) -> bytes:
        self.capture_calls += 1
        if self.drift_enabled and self.capture_calls == 3:
            with Image.open(io.BytesIO(self.raw_png)) as source:
                changed = source.convert("RGBA")
                changed.putpixel((3, 2), (250, 1, 2, 255))
                output = io.BytesIO()
                changed.save(output, format="PNG")
                self.raw_png = output.getvalue()
        return self.raw_png


def bound_frame_sha256(gateway: GovernedDesktopGateway, binding_id: str) -> str:
    observation = gateway.observe(target_binding_id=binding_id)
    assert observation.ok is True
    assert observation.after is not None
    return observation.after.sha256


class UnstableTitlePixelBackend(PixelBackend):
    def __init__(self) -> None:
        super().__init__()
        self.foreground_calls = 0

    def foreground_window(self) -> WindowInfo:
        self.foreground_calls += 1
        if self.foreground_calls >= 3:
            return replace(self.window, title="Changed During Capture")
        return self.window


class UnstableDPIBackend(FakeBackend):
    def __init__(self) -> None:
        super().__init__()
        self.dpi_calls = 0

    def window_dpi(self, window: WindowInfo) -> tuple[float, float]:
        assert window.handle == self.window.handle
        self.dpi_calls += 1
        dpi = 96.0 if self.dpi_calls == 1 else 144.0
        return dpi, dpi


def make_gateway(
    tmp_path: Path,
    *,
    backend: FakeBackend | None = None,
    clock: FakeClock | None = None,
    max_actions: int = 100,
    min_action_interval: float = 0.0,
) -> tuple[GovernedDesktopGateway, FakeBackend, FakeClock, Path]:
    fake_backend = backend or FakeBackend()
    fake_clock = clock or FakeClock()
    evidence = tmp_path / "desktop_evidence.jsonl"
    gateway = GovernedDesktopGateway(
        backend=fake_backend,
        evidence_path=evidence,
        max_actions_per_window=max_actions,
        min_action_interval_seconds=min_action_interval,
        utc_now=fake_clock.now,
        monotonic=fake_clock.monotonic,
    )
    return gateway, fake_backend, fake_clock, evidence


def evidence_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_dry_run_is_default_and_never_dispatches(tmp_path: Path) -> None:
    gateway, backend, _clock, evidence = make_gateway(tmp_path)
    assert gateway.status()["dry_run"] is True
    assert gateway.status()["live_armed"] is False

    binding = gateway.bind_target_window("Course Browser", expected_process_id=4242)
    result = gateway.execute(
        "click",
        {"x": 100, "y": 120},
        target_binding_id=binding.binding_id,
    )

    assert result.ok is True
    assert result.dry_run is True
    assert result.reason == "dry_run"
    assert backend.actions == []
    assert len(result.before_sha256) == 64
    assert len(result.after_sha256) == 64

    rows = evidence_rows(evidence)
    assert [row["event"] for row in rows] == [
        "target_window_bound",
        "action_started",
        "action_completed",
    ]
    assert rows[-1]["before_sha256"] == result.before_sha256
    assert rows[-1]["after"]["sha256"] == result.after_sha256


def test_live_lease_is_capped_token_is_one_time_and_text_is_redacted(tmp_path: Path) -> None:
    gateway, backend, clock, evidence = make_gateway(tmp_path)
    binding = gateway.bind_target_window("Course Browser")
    token = "one-time-capability-token-abcdefghijklmnopqrstuvwxyz"
    secret_text = "private course response 9f2d"

    lease = gateway.authorize_live(
        token,
        ttl_seconds=MAX_LEASE_SECONDS * 3,
        subject="local-benchmark-operator",
        allowed_actions=["type"],
    )
    assert lease.expires_at - lease.issued_at == timedelta(seconds=MAX_LEASE_SECONDS)
    assert gateway.status()["live_armed"] is True

    result = gateway.execute(
        "type",
        {"text": secret_text, "interval": 0.0},
        target_binding_id=binding.binding_id,
        expected_before_sha256=bound_frame_sha256(gateway, binding.binding_id),
    )
    assert result.ok is True
    assert result.dry_run is False
    assert backend.actions == [("type", secret_text, 0.0)]

    raw_evidence = evidence.read_text(encoding="utf-8")
    assert token not in raw_evidence
    assert secret_text not in raw_evidence
    assert hashlib.sha256(secret_text.encode()).hexdigest() in raw_evidence
    assert f'"text_length":{len(secret_text)}' in raw_evidence

    gateway.disarm()
    with pytest.raises(AuthorizationError, match="already_consumed"):
        gateway.authorize_live(token, ttl_seconds=60, subject="reuse-attempt")

    clock.advance(MAX_LEASE_SECONDS + 1)


def test_disarm_invalidates_bindings_before_a_new_lease(tmp_path: Path) -> None:
    gateway, backend, _clock, evidence = make_gateway(tmp_path)
    binding = gateway.bind_target_window("Course Browser")
    gateway.authorize_live(
        "first-disarm-token-abcdefghijklmnopqrstuvwxyz",
        ttl_seconds=300,
        subject="first-operator",
        allowed_actions=["click"],
    )

    gateway.disarm("lease_finished")

    status = gateway.status()
    assert status["dry_run"] is True
    assert status["lease"] is None
    assert status["binding_count"] == 0
    disarm_event = evidence_rows(evidence)[-1]
    assert disarm_event["event"] == "disarmed"
    assert disarm_event["invalidated_binding_count"] == 1

    gateway.authorize_live(
        "second-disarm-token-abcdefghijklmnopqrstuvwxyz",
        ttl_seconds=300,
        subject="second-operator",
        allowed_actions=["click"],
    )
    stale_binding = gateway.execute(
        "click",
        {"x": 100, "y": 100},
        target_binding_id=binding.binding_id,
    )
    assert stale_binding.ok is False
    assert stale_binding.reason.startswith("valid_target_window_binding_required")
    assert backend.actions == []

    fresh_binding = gateway.bind_target_window("Course Browser")
    accepted = gateway.execute(
        "click",
        {"x": 100, "y": 100},
        target_binding_id=fresh_binding.binding_id,
        expected_before_sha256=bound_frame_sha256(gateway, fresh_binding.binding_id),
    )
    assert accepted.ok is True
    assert backend.actions == [("click", 100, 100, "left", 1)]


def test_lease_only_revoke_preserves_externally_owned_window_binding(tmp_path: Path) -> None:
    gateway, _backend, _clock, evidence = make_gateway(tmp_path)
    binding = gateway.bind_target_window("Course Browser")
    gateway.authorize_live(
        "scorm-session-lease-token-abcdefghijklmnopqrstuvwxyz",
        ttl_seconds=300,
        subject="scorm-organism",
        allowed_actions=["click"],
    )

    gateway.revoke_live_authorization("scorm_runtime_finished")

    status = gateway.status()
    assert status["dry_run"] is True
    assert status["lease"] is None
    assert status["binding_count"] == 1
    assert gateway.require_single_target_binding_id() == binding.binding_id
    event = evidence_rows(evidence)[-1]
    assert event["event"] == "live_authorization_revoked"
    assert event["preserved_binding_count"] == 1


def test_gateway_distinguishes_post_dispatch_window_handoff_from_pre_dispatch_failure(
    tmp_path: Path,
) -> None:
    class HandoffAfterClickBackend(FakeBackend):
        def click(self, x: int, y: int, button: str = "left", clicks: int = 1) -> None:
            super().click(x, y, button, clicks)
            self.window = replace(
                self.window,
                handle=self.window.handle + 1,
                title="Course Child Window",
            )

    backend = HandoffAfterClickBackend()
    gateway, _backend, _clock, _evidence = make_gateway(tmp_path, backend=backend)
    binding = gateway.bind_target_window("Course Browser")
    gateway.authorize_live(
        "scorm-handoff-token-abcdefghijklmnopqrstuvwxyz",
        ttl_seconds=300,
        subject="scorm-organism",
        allowed_actions=["click"],
    )

    result = gateway.execute(
        "click",
        {"x": 100, "y": 120},
        target_binding_id=binding.binding_id,
        expected_before_sha256=bound_frame_sha256(gateway, binding.binding_id),
    )

    assert result.ok is False
    assert result.reason == "target_window_changed_after_action_handoff_required"
    assert backend.actions == [("click", 100, 120, "left", 1)]


def test_disarm_clears_bindings_even_if_its_evidence_write_fails(tmp_path: Path) -> None:
    gateway, _backend, _clock, _evidence = make_gateway(tmp_path)
    gateway.bind_target_window("Course Browser")
    gateway.authorize_live(
        "disarm-evidence-failure-token-abcdefghijklmnopqrstuvwxyz",
        ttl_seconds=300,
        subject="operator",
        allowed_actions=["click"],
    )
    directory_instead_of_file = tmp_path / "disarm-cannot-append"
    directory_instead_of_file.mkdir()
    gateway.evidence_path = directory_instead_of_file

    gateway.disarm()

    status = gateway.status()
    assert status["dry_run"] is True
    assert status["lease"] is None
    assert status["binding_count"] == 0


def test_emergency_epoch_invalidates_lease_binding_and_token(tmp_path: Path) -> None:
    gateway, _backend, _clock, _evidence = make_gateway(tmp_path)
    token = "emergency-lease-token-abcdefghijklmnopqrstuvwxyz"
    binding = gateway.bind_target_window("Course Browser")
    lease = gateway.authorize_live(token, ttl_seconds=3600, subject="operator")
    assert lease.epoch == 0

    epoch = gateway.emergency_stop()
    assert epoch == 1
    status = gateway.status()
    assert status["emergency_stopped"] is True
    assert status["lease"] is None
    assert status["binding_count"] == 0

    gateway.clear_emergency_stop()
    rejected = gateway.execute(
        "click",
        {"x": 100, "y": 100},
        target_binding_id=binding.binding_id,
    )
    assert rejected.ok is False
    assert rejected.reason.startswith("valid_target_window_binding_required")

    with pytest.raises(AuthorizationError, match="already_consumed"):
        gateway.authorize_live(token, ttl_seconds=60, subject="stale-token")

    fresh_binding = gateway.bind_target_window("Course Browser")
    gateway.authorize_live(
        "fresh-emergency-token-abcdefghijklmnopqrstuvwxyz",
        ttl_seconds=60,
        subject="operator",
        allowed_actions=["click"],
    )
    accepted = gateway.execute(
        "click",
        {"x": 100, "y": 100},
        target_binding_id=fresh_binding.binding_id,
        expected_before_sha256=bound_frame_sha256(gateway, fresh_binding.binding_id),
    )
    assert accepted.ok is True


def test_lease_expiry_and_action_scope_fail_closed(tmp_path: Path) -> None:
    gateway, backend, clock, _evidence = make_gateway(tmp_path)
    binding = gateway.bind_target_window("Course Browser")

    with pytest.raises(AuthorizationError, match="invalid_lease_action_scope"):
        gateway.authorize_live(
            "empty-scope-token-abcdefghijklmnopqrstuvwxyz",
            ttl_seconds=60,
            subject="operator",
            allowed_actions=[],
        )

    gateway.authorize_live(
        "short-scope-token-abcdefghijklmnopqrstuvwxyz",
        ttl_seconds=1,
        subject="operator",
        allowed_actions=["click"],
    )
    outside_scope = gateway.execute(
        "type",
        {"text": "must not be typed"},
        target_binding_id=binding.binding_id,
    )
    assert outside_scope.ok is False
    assert outside_scope.reason.startswith("action_outside_lease_scope")

    clock.advance(2)
    expired = gateway.execute(
        "click",
        {"x": 100, "y": 100},
        target_binding_id=binding.binding_id,
    )
    assert expired.ok is False
    assert expired.reason.startswith("active_authorization_lease_required")
    assert gateway.status()["live_armed"] is False
    assert backend.actions == []


def test_target_window_and_coordinate_gates_fail_before_dispatch(tmp_path: Path) -> None:
    gateway, backend, _clock, _evidence = make_gateway(tmp_path)
    binding = gateway.bind_target_window("Course Browser")
    gateway.authorize_live(
        "window-binding-token-abcdefghijklmnopqrstuvwxyz",
        ttl_seconds=300,
        subject="operator",
        allowed_actions=["click"],
    )
    expected_before_sha256 = bound_frame_sha256(gateway, binding.binding_id)

    original = backend.window
    backend.window = WindowInfo(
        handle=88,
        title="Unexpected Window",
        process_id=5000,
        left=0,
        top=0,
        width=1024,
        height=768,
    )
    wrong_window = gateway.execute(
        "click",
        {"x": 100, "y": 100},
        target_binding_id=binding.binding_id,
        expected_before_sha256=expected_before_sha256,
    )
    assert wrong_window.ok is False
    assert wrong_window.reason.startswith("target_window_mismatch")
    assert backend.actions == []

    backend.window = original
    off_screen = gateway.execute(
        "click",
        {"x": 2048, "y": 100},
        target_binding_id=binding.binding_id,
        expected_before_sha256=expected_before_sha256,
    )
    assert off_screen.ok is False
    assert off_screen.reason.startswith("coordinates_outside_screen")
    assert backend.actions == []

    outside_bound_window = gateway.execute(
        "click",
        {"x": 900, "y": 700},
        target_binding_id=binding.binding_id,
        expected_before_sha256=expected_before_sha256,
    )
    assert outside_bound_window.ok is False
    assert outside_bound_window.reason.startswith("coordinates_outside_target_window")
    assert backend.actions == []


def test_bound_observation_masks_every_pixel_outside_target_and_hashes_mask(
    tmp_path: Path,
) -> None:
    backend = PixelBackend()
    gateway, _backend, _clock, evidence = make_gateway(tmp_path, backend=backend)
    binding = gateway.bind_target_window("Course Browser")
    raw_sha256 = hashlib.sha256(backend.raw_png).hexdigest()

    result = gateway.observe(target_binding_id=binding.binding_id)

    assert result.ok is True
    assert result.before is not None
    assert result.after is not None
    assert (result.after.cursor_x, result.after.cursor_y) == backend.cursor
    assert (result.after.dpi_x, result.after.dpi_y) == (96.0, 96.0)
    assert result.before_sha256 == result.after_sha256
    assert result.after_sha256 == hashlib.sha256(result.after.image_bytes).hexdigest()
    assert result.after_sha256 != raw_sha256
    with Image.open(io.BytesIO(result.after.image_bytes)) as masked:
        assert masked.mode == "RGBA"
        assert masked.size == (backend.width, backend.height)
        with Image.open(io.BytesIO(backend.raw_png)) as original:
            for y in range(backend.height):
                for x in range(backend.width):
                    if 2 <= x < 5 and 1 <= y < 3:
                        assert masked.getpixel((x, y)) == original.getpixel((x, y))
                    else:
                        assert masked.getpixel((x, y)) == (0, 0, 0, 255)

    raw_evidence = evidence.read_text(encoding="utf-8")
    assert result.after_sha256 in raw_evidence
    assert raw_sha256 not in raw_evidence
    rows = evidence_rows(evidence)
    assert rows[-2]["observation_scope"] == "target_window_masked"
    assert rows[-1]["observation_scope"] == "target_window_masked"
    assert rows[-2]["before"]["cursor"] == {"x": 5, "y": 7}
    assert rows[-1]["after"]["cursor"] == {"x": 5, "y": 7}
    assert rows[-2]["before"]["dpi"] == {"x": 96.0, "y": 96.0}
    assert rows[-1]["after"]["dpi"] == {"x": 96.0, "y": 96.0}


def test_observation_allows_a_legacy_backend_without_dpi_telemetry(
    tmp_path: Path,
) -> None:
    backend = FakeBackend()
    backend.window_dpi = None  # type: ignore[method-assign]
    gateway, _backend, _clock, _evidence = make_gateway(tmp_path, backend=backend)
    binding = gateway.bind_target_window("Course Browser")

    result = gateway.observe(target_binding_id=binding.binding_id)

    assert result.ok is True
    assert result.after is not None
    assert (result.after.dpi_x, result.after.dpi_y) == (None, None)
    assert "dpi" not in result.after.audit_dict()


def test_observation_rejects_invalid_or_changed_window_dpi(tmp_path: Path) -> None:
    invalid = FakeBackend()
    invalid.dpi = (0.0, 96.0)
    invalid_gateway, _backend, _clock, _evidence = make_gateway(
        tmp_path / "invalid",
        backend=invalid,
    )
    invalid_binding = invalid_gateway.bind_target_window("Course Browser")

    invalid_result = invalid_gateway.observe(
        target_binding_id=invalid_binding.binding_id,
    )

    assert invalid_result.ok is False
    assert invalid_result.reason == "invalid_window_dpi"

    unstable = UnstableDPIBackend()
    unstable_gateway, _backend, _clock, _evidence = make_gateway(
        tmp_path / "unstable",
        backend=unstable,
    )
    unstable_binding = unstable_gateway.bind_target_window("Course Browser")

    unstable_result = unstable_gateway.observe(
        target_binding_id=unstable_binding.binding_id,
    )

    assert unstable_result.ok is False
    assert unstable_result.reason == "foreground_window_dpi_changed_during_capture"


def test_bound_mutation_hashes_only_masked_source_and_records_cursor(tmp_path: Path) -> None:
    backend = PixelBackend()
    gateway, _backend, _clock, evidence = make_gateway(tmp_path, backend=backend)
    binding = gateway.bind_target_window("Course Browser")
    gateway.authorize_live(
        "masked-mutation-token-abcdefghijklmnopqrstuvwxyz",
        ttl_seconds=300,
        subject="operator",
        allowed_actions=["click"],
    )
    expected = bound_frame_sha256(gateway, binding.binding_id)
    raw_sha256 = hashlib.sha256(backend.raw_png).hexdigest()

    result = gateway.execute(
        "click",
        {"x": 3, "y": 2},
        target_binding_id=binding.binding_id,
        expected_before_sha256=expected,
    )

    assert result.ok is True
    assert result.expected_before_sha256 == expected
    assert result.before_sha256 == expected
    assert result.after is not None
    assert result.after_sha256 == hashlib.sha256(result.after.image_bytes).hexdigest()
    assert result.after_sha256 != raw_sha256
    assert (result.after.cursor_x, result.after.cursor_y) == (3, 2)
    with Image.open(io.BytesIO(result.after.image_bytes)) as masked:
        assert masked.getpixel((0, 0)) == (0, 0, 0, 255)
        assert masked.getpixel((3, 2)) != (0, 0, 0, 255)

    rows = evidence_rows(evidence)
    started, completed = rows[-2:]
    assert started["expected_before_sha256"] == expected
    assert started["before"]["sha256"] == expected
    assert started["observation_scope"] == "target_window_masked"
    assert completed["expected_before_sha256"] == expected
    assert completed["after"]["cursor"] == {"x": 3, "y": 2}
    assert raw_sha256 not in json.dumps((started, completed), sort_keys=True)


def test_stale_source_frame_rejects_before_dispatch(tmp_path: Path) -> None:
    backend = PixelBackend()
    gateway, _backend, _clock, evidence = make_gateway(tmp_path, backend=backend)
    binding = gateway.bind_target_window("Course Browser")
    gateway.authorize_live(
        "stale-frame-token-abcdefghijklmnopqrstuvwxyz",
        ttl_seconds=300,
        subject="operator",
        allowed_actions=["click"],
    )
    expected = bound_frame_sha256(gateway, binding.binding_id)
    with Image.open(io.BytesIO(backend.raw_png)) as source:
        changed = source.convert("RGBA")
        changed.putpixel((3, 2), (250, 1, 2, 255))
        output = io.BytesIO()
        changed.save(output, format="PNG")
        backend.raw_png = output.getvalue()

    result = gateway.execute(
        "click",
        {"x": 3, "y": 2},
        target_binding_id=binding.binding_id,
        expected_before_sha256=expected,
    )

    assert result.ok is False
    assert result.reason == "stale_source_frame"
    assert result.before_sha256 != expected
    assert backend.actions == []
    rejected = evidence_rows(evidence)[-1]
    assert rejected["event"] == "action_rejected"
    assert rejected["expected_before_sha256"] == expected
    assert rejected["before_sha256"] == result.before_sha256


def test_dispatch_linearization_recapture_rejects_raced_frame_without_rate_slot(
    tmp_path: Path,
) -> None:
    backend = DriftAtDispatchLinearizationBackend()
    gateway, _backend, _clock, evidence = make_gateway(
        tmp_path,
        backend=backend,
        max_actions=1,
    )
    binding = gateway.bind_target_window("Course Browser")
    gateway.authorize_live(
        "linearization-race-token-abcdefghijklmnopqrstuvwxyz",
        ttl_seconds=300,
        subject="operator",
        allowed_actions=["click"],
    )
    expected = bound_frame_sha256(gateway, binding.binding_id)

    stale = gateway.execute(
        "click",
        {"x": 3, "y": 2},
        target_binding_id=binding.binding_id,
        expected_before_sha256=expected,
    )

    assert stale.ok is False
    assert stale.reason == "stale_source_frame"
    assert stale.before_sha256 != expected
    assert backend.actions == []
    assert backend.capture_calls == 4
    stale_completed = evidence_rows(evidence)[-1]
    assert stale_completed["event"] == "action_completed"
    assert stale_completed["reason"] == "stale_source_frame"

    backend.drift_enabled = False
    current = bound_frame_sha256(gateway, binding.binding_id)
    executed = gateway.execute(
        "click",
        {"x": 3, "y": 2},
        target_binding_id=binding.binding_id,
        expected_before_sha256=current,
    )

    assert executed.ok is True
    assert executed.reason == "executed"
    assert backend.actions == [("click", 3, 2, "left", 1)]


@pytest.mark.parametrize("invalid_hash", ["A" * 64, "abc", "private-not-a-hash"])
def test_expected_source_hash_must_be_exact_lowercase_sha_without_echo(
    tmp_path: Path,
    invalid_hash: str,
) -> None:
    gateway, backend, _clock, evidence = make_gateway(tmp_path)
    binding = gateway.bind_target_window("Course Browser")
    gateway.authorize_live(
        "invalid-source-hash-token-abcdefghijklmnopqrstuvwxyz",
        ttl_seconds=300,
        subject="operator",
        allowed_actions=["click"],
    )

    result = gateway.execute(
        "click",
        {"x": 100, "y": 100},
        target_binding_id=binding.binding_id,
        expected_before_sha256=invalid_hash,
    )

    assert result.ok is False
    assert result.reason == "expected_before_sha256_invalid"
    assert backend.actions == []
    assert invalid_hash not in evidence.read_text(encoding="utf-8")


def test_live_mutation_requires_source_hash_before_capture_or_dispatch(tmp_path: Path) -> None:
    gateway, backend, _clock, _evidence = make_gateway(tmp_path)
    binding = gateway.bind_target_window("Course Browser")
    gateway.authorize_live(
        "missing-source-hash-token-abcdefghijklmnopqrstuvwxyz",
        ttl_seconds=300,
        subject="operator",
        allowed_actions=["click"],
    )

    result = gateway.execute(
        "click",
        {"x": 100, "y": 100},
        target_binding_id=binding.binding_id,
    )

    assert result.ok is False
    assert result.reason == "expected_before_sha256_required"
    assert result.before is None
    assert backend.actions == []


@pytest.mark.parametrize("changed_field", ["title", "handle", "process_id"])
def test_bound_observation_rejects_exact_binding_mismatch_without_returning_frame(
    tmp_path: Path,
    changed_field: str,
) -> None:
    backend = PixelBackend()
    gateway, _backend, _clock, evidence = make_gateway(tmp_path, backend=backend)
    binding = gateway.bind_target_window("Course Browser")
    changes: dict[str, object] = {
        "title": "Another Window",
        "handle": 88,
        "process_id": 5252,
    }
    backend.window = replace(backend.window, **{changed_field: changes[changed_field]})
    raw_sha256 = hashlib.sha256(backend.raw_png).hexdigest()

    result = gateway.observe(target_binding_id=binding.binding_id)

    assert result.ok is False
    assert result.reason == "target_window_mismatch"
    assert result.before is None
    assert result.after is None
    assert result.before_sha256 == ""
    assert raw_sha256 not in evidence.read_text(encoding="utf-8")


def test_bound_observation_rejects_title_change_during_capture(tmp_path: Path) -> None:
    backend = UnstableTitlePixelBackend()
    gateway, _backend, _clock, _evidence = make_gateway(tmp_path, backend=backend)
    binding = gateway.bind_target_window("Course Browser")

    result = gateway.observe(target_binding_id=binding.binding_id)

    assert result.ok is False
    assert result.reason == "foreground_window_changed_during_capture"
    assert result.before is None
    assert result.after is None


def test_observations_do_not_consume_or_fail_on_mutation_rate_slots(tmp_path: Path) -> None:
    gateway, backend, _clock, _evidence = make_gateway(tmp_path, max_actions=2)
    binding = gateway.bind_target_window("Course Browser")

    assert gateway.observe().ok is True
    assert gateway.observe().ok is True
    assert gateway.observe().ok is True

    first = gateway.execute("click", {"x": 100, "y": 100}, target_binding_id=binding.binding_id)
    second = gateway.execute("click", {"x": 100, "y": 100}, target_binding_id=binding.binding_id)
    limited = gateway.execute("click", {"x": 100, "y": 100}, target_binding_id=binding.binding_id)
    assert first.ok is True
    assert second.ok is True
    assert limited.ok is False
    assert limited.reason.startswith("action_rate_window_exceeded")
    assert gateway.observe().ok is True

    unknown = gateway.execute("click", {"x": 10, "y": 10, "button": "left"})
    assert unknown.ok is False
    assert unknown.reason.startswith("unknown_action_parameter")
    assert backend.actions == []


def test_observations_bypass_mutation_minimum_interval(tmp_path: Path) -> None:
    gateway, backend, _clock, _evidence = make_gateway(
        tmp_path,
        min_action_interval=60.0,
    )
    binding = gateway.bind_target_window("Course Browser")

    first = gateway.execute("click", {"x": 100, "y": 100}, target_binding_id=binding.binding_id)
    assert first.ok is True
    assert gateway.observe().ok is True

    too_soon = gateway.execute("click", {"x": 100, "y": 100}, target_binding_id=binding.binding_id)
    assert too_soon.ok is False
    assert too_soon.reason.startswith("action_rate_min_interval")
    assert gateway.observe().ok is True
    assert backend.actions == []


def test_postcondition_can_veto_an_executed_action_without_logging_detail(tmp_path: Path) -> None:
    gateway, backend, _clock, evidence = make_gateway(tmp_path)
    binding = gateway.bind_target_window("Course Browser")
    gateway.authorize_live(
        "postcondition-token-abcdefghijklmnopqrstuvwxyz",
        ttl_seconds=300,
        subject="operator",
        allowed_actions=["click"],
    )
    evaluator_detail = "private evaluator observation"

    result = gateway.execute(
        "click",
        {"x": 100, "y": 100},
        target_binding_id=binding.binding_id,
        expected_before_sha256=bound_frame_sha256(gateway, binding.binding_id),
        evaluator=lambda before, after, context: PostconditionResult(False, evaluator_detail),
    )

    assert backend.actions == [("click", 100, 100, "left", 1)]
    assert result.ok is False
    assert result.reason == "postcondition_failed"
    assert result.postcondition == PostconditionResult(False, evaluator_detail)
    raw_evidence = evidence.read_text(encoding="utf-8")
    assert evaluator_detail not in raw_evidence
    assert hashlib.sha256(evaluator_detail.encode()).hexdigest() in raw_evidence


def test_evidence_start_failure_prevents_live_dispatch(tmp_path: Path) -> None:
    gateway, backend, _clock, _evidence = make_gateway(tmp_path)
    binding = gateway.bind_target_window("Course Browser")
    gateway.authorize_live(
        "evidence-preflight-token-abcdefghijklmnopqrstuvwxyz",
        ttl_seconds=300,
        subject="operator",
        allowed_actions=["click"],
    )

    directory_instead_of_file = tmp_path / "cannot-append-directory"
    directory_instead_of_file.mkdir()
    expected_before_sha256 = bound_frame_sha256(gateway, binding.binding_id)
    gateway.evidence_path = directory_instead_of_file

    result = gateway.execute(
        "click",
        {"x": 100, "y": 100},
        target_binding_id=binding.binding_id,
        expected_before_sha256=expected_before_sha256,
    )
    assert result.ok is False
    assert result.reason == "evidence_start_write_failed"
    assert backend.actions == []


def test_lazy_local_backend_reasserts_pyautogui_failsafe(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_pyautogui = SimpleNamespace(
        FAILSAFE=False,
        PAUSE=0.0,
        size=lambda: (800, 600),
        position=lambda: (123, 456),
    )
    monkeypatch.setitem(sys.modules, "pyautogui", fake_pyautogui)

    backend = LazyPyAutoGUIBackend(pause_seconds=0.125)
    assert backend.screen_size() == (800, 600)
    assert backend.pointer_position() == (123, 456)
    assert fake_pyautogui.FAILSAFE is True
    assert fake_pyautogui.PAUSE == 0.125


def test_lazy_local_backend_reads_exact_window_dpi_with_pointer_safe_signature(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[int] = []

    class FakeGetDpiForWindow:
        argtypes: object = None
        restype: object = None

        def __call__(self, handle: ctypes.wintypes.HWND) -> int:
            calls.append(int(handle.value))
            return 144

    get_dpi_for_window = FakeGetDpiForWindow()
    fake_user32 = SimpleNamespace(GetDpiForWindow=get_dpi_for_window)
    monkeypatch.setattr(
        ctypes,
        "windll",
        SimpleNamespace(user32=fake_user32),
        raising=False,
    )
    backend = LazyPyAutoGUIBackend(pause_seconds=0.0, platform_name="win32")
    window = WindowInfo(
        handle=0x123456789,
        title="Course Browser",
        process_id=4242,
        left=0,
        top=0,
        width=800,
        height=600,
    )

    assert backend.window_dpi(window) == (144.0, 144.0)
    assert calls == [window.handle]
    assert get_dpi_for_window.argtypes == [ctypes.wintypes.HWND]
    assert get_dpi_for_window.restype is ctypes.wintypes.UINT


@pytest.mark.parametrize(
    ("platform_name", "logical_amount", "native_amount"),
    [
        ("win32", -7, -840),
        ("linux", -7, -7),
        ("darwin", 7, 7),
    ],
)
def test_lazy_local_backend_converts_only_win32_scroll_units(
    monkeypatch: pytest.MonkeyPatch,
    platform_name: str,
    logical_amount: int,
    native_amount: int,
) -> None:
    calls: list[tuple] = []
    fake_pyautogui = SimpleNamespace(
        FAILSAFE=False,
        PAUSE=0.0,
        moveTo=lambda x, y, duration: calls.append(("move", x, y, duration)),
        scroll=lambda amount: calls.append(("scroll", amount)),
    )
    monkeypatch.setitem(sys.modules, "pyautogui", fake_pyautogui)

    backend = LazyPyAutoGUIBackend(pause_seconds=0.0, platform_name=platform_name)
    backend.scroll(logical_amount, 321, 456)

    assert calls == [
        ("move", 321, 456, 0.0),
        ("scroll", native_amount),
    ]


def test_lazy_local_backend_bounds_scroll_before_pyautogui_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple] = []
    fake_pyautogui = SimpleNamespace(
        FAILSAFE=False,
        PAUSE=0.0,
        moveTo=lambda *args, **kwargs: calls.append(("move", args, kwargs)),
        scroll=lambda amount: calls.append(("scroll", amount)),
    )
    monkeypatch.setitem(sys.modules, "pyautogui", fake_pyautogui)
    backend = LazyPyAutoGUIBackend(pause_seconds=0.0, platform_name="win32")

    with pytest.raises(DesktopBackendError, match="scroll_amount_out_of_range"):
        backend.scroll(-101, 321, 456)

    assert calls == []


def test_bind_requires_exact_foreground_title(tmp_path: Path) -> None:
    gateway, _backend, _clock, _evidence = make_gateway(tmp_path)
    with pytest.raises(DesktopGatewayError, match="title_mismatch"):
        gateway.bind_target_window("Different Browser")
