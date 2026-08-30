from __future__ import annotations

import hashlib
import io

from PIL import Image

from aureon.autonomous.aureon_agent_core import AureonAgentCore
from aureon.autonomous.aureon_governed_desktop_gateway import GovernedDesktopGateway, WindowInfo


class _Backend:
    def __init__(self) -> None:
        self.window = WindowInfo(7, "Fixture Browser", 99, 5, 5, 790, 590)
        self.actions: list[tuple] = []
        self.frame = 0
        self.cursor = (0, 0)
        self.image_bytes = self._png((20, 40, 60, 255))

    @staticmethod
    def _png(color: tuple[int, int, int, int]) -> bytes:
        image = Image.new("RGBA", (800, 600), color)
        output = io.BytesIO()
        image.save(output, format="PNG")
        return output.getvalue()

    def _changed(self) -> None:
        self.frame += 1
        self.image_bytes = self._png((20 + self.frame, 40, 60, 255))

    def capture_screen(self) -> bytes:
        return self.image_bytes

    def screen_size(self):
        return 800, 600

    def foreground_window(self):
        return self.window

    def pointer_position(self):
        return self.cursor

    def move(self, x, y, duration=0.0):
        self.actions.append(("move", x, y, duration))
        self.cursor = (x, y)
        self._changed()

    def click(self, x, y, button="left", clicks=1):
        self.actions.append(("click", x, y, button, clicks))
        self.cursor = (x, y)
        self._changed()

    def scroll(self, amount, x, y):
        self.actions.append(("scroll", amount, x, y))
        self.cursor = (x, y)
        self._changed()

    def type_text(self, text, interval=0.02):
        self.actions.append(("type", text, interval))
        self._changed()

    def press(self, key):
        self.actions.append(("press", key))
        self._changed()

    def hotkey(self, keys):
        self.actions.append(("hotkey", tuple(keys)))
        self._changed()


class _DriftingBackend(_Backend):
    def __init__(self) -> None:
        super().__init__()
        self.capture_count = 0

    def capture_screen(self) -> bytes:
        self.capture_count += 1
        if self.capture_count == 2:
            self._changed()
        return self.image_bytes


def test_agent_core_has_no_raw_laptop_fallback() -> None:
    core = AureonAgentCore()

    result = core.execute("mouse_scroll", {"clicks": -3})

    assert result["success"] is False
    assert result["tool_used"] is None
    assert "Unknown intent" in result["error"]


def test_agent_core_routes_click_through_dry_run_gateway(tmp_path) -> None:
    backend = _Backend()
    gateway = GovernedDesktopGateway(
        backend=backend,
        evidence_path=tmp_path / "gateway.jsonl",
        min_action_interval_seconds=0.0,
    )
    core = AureonAgentCore()
    core._desktop = gateway
    binding = gateway.bind_target_window("Fixture Browser")

    result = core.click(10, 20, target_binding_id=binding.binding_id)

    assert result["success"] is True
    assert result["dry_run"] is True
    assert result["expected_before_sha256"] == result["before_sha256"]
    assert len(result["expected_before_sha256"]) == 64
    assert result["expected_before_sha256"] != hashlib.sha256(backend.image_bytes).hexdigest()
    assert result["source_observation_action_id"]
    assert backend.actions == []


def test_agent_core_live_click_requires_lease_and_exact_window_binding(tmp_path) -> None:
    backend = _Backend()
    gateway = GovernedDesktopGateway(
        backend=backend,
        evidence_path=tmp_path / "gateway.jsonl",
        min_action_interval_seconds=0.0,
    )
    core = AureonAgentCore()
    core._desktop = gateway
    arm = core.desktop_arm_live(
        "a" * 32,
        ttl_seconds=60,
        subject="synthetic-course-benchmark",
        allowed_actions=["click"],
    )
    binding = core.desktop_bind_window("Fixture Browser")

    result = core.click(10, 20, target_binding_id=binding["binding_id"])

    assert arm["success"] is True
    assert result["success"] is True
    assert result["dry_run"] is False
    assert result["expected_before_sha256"] == result["before_sha256"]
    assert len(result["expected_before_sha256"]) == 64
    assert result["source_observation_action_id"]
    assert backend.actions == [("click", 10, 20, "left", 1)]


def test_agent_core_rejects_live_click_when_bound_source_frame_drifts(tmp_path) -> None:
    backend = _DriftingBackend()
    gateway = GovernedDesktopGateway(
        backend=backend,
        evidence_path=tmp_path / "gateway.jsonl",
        min_action_interval_seconds=0.0,
    )
    core = AureonAgentCore()
    core._desktop = gateway
    arm = core.desktop_arm_live(
        "b" * 32,
        ttl_seconds=60,
        subject="synthetic-course-benchmark",
        allowed_actions=["click"],
    )
    binding = core.desktop_bind_window("Fixture Browser")

    result = core.click(10, 20, target_binding_id=binding["binding_id"])

    assert arm["success"] is True
    assert result["success"] is False
    assert result["reason"] == "stale_source_frame"
    assert result["expected_before_sha256"] != result["before_sha256"]
    assert backend.actions == []


def test_environment_flags_cannot_auto_arm_agent_core(monkeypatch) -> None:
    monkeypatch.setenv("AUREON_SOVEREIGN_MODE", "1")
    monkeypatch.setenv("AUREON_DESKTOP_LIVE", "1")
    monkeypatch.setenv("AUREON_DESKTOP_AUTO_ARM", "1")

    status = AureonAgentCore().desktop_status()

    assert status["success"] is True
    assert status["result"]["live_armed"] is False
    assert status["result"]["dry_run"] is True
