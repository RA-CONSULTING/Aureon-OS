"""Stage the self-host image context without widening the root Docker ignore."""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMAGE = ROOT / "deploy" / "selfhost" / "image"
SOURCES = ("aureon_fusion", "aureon", "organism")


def _ignore(_directory: str, names: list[str]) -> set[str]:
    return {name for name in names if name == "__pycache__" or name.endswith(".pyc")}


def stage() -> Path:
    if IMAGE.exists():
        shutil.rmtree(IMAGE)
    IMAGE.mkdir(parents=True)
    for name in SOURCES:
        shutil.copytree(ROOT / name, IMAGE / name, ignore=_ignore)
    shutil.copy2(ROOT / "deploy" / "selfhost" / "Dockerfile", IMAGE / "Dockerfile")
    shutil.copy2(ROOT / "deploy" / "selfhost" / "error_sink.py", IMAGE / "error_sink.py")
    return IMAGE


if __name__ == "__main__":
    print(stage())
