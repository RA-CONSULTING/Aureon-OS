"""Importing the laptop HAL must not create empty state folders."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_import_does_not_create_screenshot_or_camera_dirs() -> None:
    shots = ROOT / "state" / "screenshots"
    camera = ROOT / "state" / "camera"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    proc = subprocess.run(
        [sys.executable, "-c", "import aureon.autonomous.aureon_laptop_control"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert shots.exists() is False
    assert camera.exists() is False


def test_screenshot_and_camera_dirs_are_created_on_first_write(tmp_path: Path, monkeypatch) -> None:
    import aureon.autonomous.aureon_laptop_control as laptop

    shots = tmp_path / "screenshots"
    camera = tmp_path / "camera"
    monkeypatch.setattr(laptop, "_SCREENSHOT_DIR", shots)
    monkeypatch.setattr(laptop, "_CAMERA_DIR", camera)
    monkeypatch.setattr(laptop, "_log_action", lambda *args, **kwargs: None)

    class _Image:
        def save(self, path: str) -> None:
            Path(path).write_bytes(b"png")

    monkeypatch.setattr(laptop, "HAS_PYAUTOGUI", True)
    monkeypatch.setattr(
        laptop,
        "pyautogui",
        type("Pg", (), {"screenshot": staticmethod(lambda region=None: _Image())})(),
    )
    saved = laptop.LaptopControl().screenshot()
    assert saved["success"] is True
    assert shots.is_dir()
    assert camera.exists() is False

    class _Cap:
        def isOpened(self) -> bool:
            return True

        def read(self):
            return True, "frame"

        def release(self) -> None:
            return None

    class _Cv2:
        @staticmethod
        def VideoCapture(_index: int):
            return _Cap()

        @staticmethod
        def imwrite(path: str, _frame) -> bool:
            Path(path).write_bytes(b"jpg")
            return True

    monkeypatch.setattr(laptop, "HAS_CV2", True)
    monkeypatch.setattr(laptop, "cv2", _Cv2)
    captured = laptop.LaptopControl().camera_capture()
    assert captured["success"] is True
    assert camera.is_dir()
