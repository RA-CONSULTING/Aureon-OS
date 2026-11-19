"""Importing the laptop HAL must not create empty state folders."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _listing(path: Path) -> tuple[bool, tuple[str, ...]]:
    if not path.exists():
        return False, ()
    return True, tuple(sorted(child.name for child in path.iterdir()))


def test_import_does_not_create_screenshot_or_camera_dirs() -> None:
    shots = ROOT / "state" / "screenshots"
    camera = ROOT / "state" / "camera"
    before = (_listing(shots), _listing(camera))
    env = os.environ.copy()
    env.pop("DISPLAY", None)
    env.pop("WAYLAND_DISPLAY", None)
    env["PYTHONPATH"] = str(ROOT)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    script = (
        "import pathlib\n"
        "_orig = pathlib.Path.mkdir\n"
        "calls = []\n"
        "def spy(self, *args, **kwargs):\n"
        "    calls.append(self.name)\n"
        "    return _orig(self, *args, **kwargs)\n"
        "pathlib.Path.mkdir = spy\n"
        "import aureon.autonomous.aureon_laptop_control\n"
        "bad = [name for name in calls if name in {'screenshots', 'camera'}]\n"
        "print('BAD', len(bad))\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    after = (_listing(shots), _listing(camera))
    assert proc.returncode == 0, proc.stderr
    assert after == before
    assert "BAD 0" in proc.stdout


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

    monkeypatch.setattr(laptop, "_PYAUTOGUI_LOADED", True)
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
