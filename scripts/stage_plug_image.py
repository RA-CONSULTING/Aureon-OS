"""Stage a Docker build context for the plug-and-play image.

The root .dockerignore hides the tree from other images. This script copies
the files the local stack imports into deploy/plug/image/, which is gitignored.
"""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMAGE = ROOT / "deploy" / "plug" / "image"
TREES = ("aureon", "mcp", "huggingface", "frontend")


def _ignore(directory: str, names: list[str]) -> set[str]:
    del directory
    skipped = {"node_modules", "__pycache__", ".git", ".venv", "runtime", "image", "dist"}
    return {name for name in names if name in skipped or name.endswith(".pyc")}


def stage() -> Path:
    if IMAGE.exists():
        shutil.rmtree(IMAGE)
    IMAGE.mkdir(parents=True)
    for name in TREES:
        shutil.copytree(ROOT / name, IMAGE / name, ignore=_ignore)
    scripts = IMAGE / "scripts"
    scripts.mkdir()
    shutil.copy2(ROOT / "scripts" / "plug_and_play.py", scripts / "plug_and_play.py")
    data = IMAGE / "data"
    data.mkdir()
    shutil.copy2(ROOT / "data" / "de440_timeseries.csv", data / "de440_timeseries.csv")
    shutil.copy2(ROOT / "requirements-plug.lock", IMAGE / "requirements-plug.lock")
    shutil.copy2(ROOT / "deploy" / "plug" / "Dockerfile", IMAGE / "Dockerfile")
    return IMAGE


if __name__ == "__main__":
    print(stage())
