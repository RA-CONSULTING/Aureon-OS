"""Git-blob check for a file loaded from the checkout beside a pinned aureon.

Every checkout load goes through ``load_pinned_source``. That helper requires
the expected blob, reads the file once, and executes those same bytes.
``guard_loader`` is the only ``spec_from_file_location`` call, and it loads
``huggingface/hnc-field/guard.py`` rather than an aureon module.
"""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from importlib.abc import Loader
from pathlib import Path
from types import ModuleType

PINNED_PHENOLIC_BLOB = "325484e9299eecb427cf0063590b0a1d17c16f31"
PHENOLIC_MISMATCH = "checkout phenolic_fingerprint differs from pin a00f744d"


def git_blob_sha1(data: bytes) -> str:
    """SHA-1 of a git blob: the header ``blob <len>\\0`` plus the file bytes."""

    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def pinned_blob_refusal(path: Path, expected: str, mismatch: str) -> str | None:
    """Return mismatch text when path is not the pinned blob. None when it matches."""

    if not path.is_file():
        return f"{path.name} is not in this checkout"
    digest = git_blob_sha1(path.read_bytes())
    if digest != expected:
        return mismatch
    return None


class _SameBytesLoader(Loader):
    """Execute the bytes already hashed. Does not read the path again."""

    def __init__(self, data: bytes, origin: str) -> None:
        self._data = data
        self._origin = origin

    def create_module(self, spec: object) -> None:
        return None

    def exec_module(self, module: ModuleType) -> None:
        code = compile(self._data, self._origin, "exec")
        exec(code, module.__dict__)


def expected_pin_blob(path: Path, root: Path, commit: str) -> tuple[str | None, str | None]:
    """Return the blob hash recorded at ``commit`` for ``path``.

    This reads git, not the working-tree file. ``(None, None)`` means the
    path is outside the checkout.
    """

    try:
        relative = path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return None, None
    import subprocess

    try:
        pin_blob = subprocess.check_output(
            ["git", "rev-parse", f"{commit}:{relative}"],
            cwd=root,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None, f"{relative} is not in pin {commit[:12]}"
    if not pin_blob:
        return None, "expected blob is required"
    return pin_blob, None


def load_pinned_source(module_name: str, path: Path, expected_blob: str, mismatch: str) -> str | None:
    """Read ``path`` once. Refuse unless those bytes are ``expected_blob``. Exec them.

    Returns None when the module is ready. A refusal string means it was not
    executed. An empty ``expected_blob`` is a refusal and does not read the file.
    """

    if not expected_blob:
        return "expected blob is required"
    try:
        data = path.read_bytes()
    except OSError:
        return f"{path.name} is not in this checkout"
    if git_blob_sha1(data) != expected_blob:
        return mismatch
    if module_name in sys.modules:
        return None
    loader = _SameBytesLoader(data, str(path))
    spec = importlib.util.spec_from_loader(module_name, loader, origin=str(path))
    if spec is None:
        return f"{path.name} could not be loaded"
    module = importlib.util.module_from_spec(spec)
    parent_name, _, child = module_name.rpartition(".")
    module.__package__ = parent_name
    sys.modules[module_name] = module
    try:
        loader.exec_module(module)
    except Exception as exc:
        sys.modules.pop(module_name, None)
        return f"{type(exc).__name__}: {exc}"[:240]
    parent = sys.modules.get(parent_name) if parent_name else None
    if parent is not None:
        setattr(parent, child, module)
    return None


def load_checkout_module(module_name: str, path: Path, root: Path, commit: str) -> tuple[ModuleType | None, str | None]:
    """Load a checkout module and its checkout parents through ``load_pinned_source``."""

    parts = module_name.split(".")
    for index in range(1, len(parts)):
        parent_name = ".".join(parts[:index])
        if parent_name in sys.modules:
            continue
        parent_path = root.joinpath(*parts[:index], "__init__.py")
        expected, error = expected_pin_blob(parent_path, root, commit)
        if error or not expected:
            return None, error or "expected blob is required"
        refusal = load_pinned_source(
            parent_name,
            parent_path,
            expected,
            f"checkout {parent_path.relative_to(root).as_posix()} differs from pin {commit[:12]}",
        )
        if refusal:
            return None, refusal
    expected, error = expected_pin_blob(path, root, commit)
    if error or not expected:
        return None, error or "expected blob is required"
    try:
        relative = path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        relative = path.name
    refusal = load_pinned_source(
        module_name,
        path,
        expected,
        f"checkout {relative} differs from pin {commit[:12]}",
    )
    if refusal:
        return None, refusal
    loaded = sys.modules.get(module_name)
    if loaded is None:
        return None, f"{path.name} could not be loaded"
    return loaded, None


def checkout_blob_refusal(path: Path, root: Path, commit: str) -> str | None:
    """Refuse a checkout file whose git blob is not the blob at ``commit``.

    Returns None when the bytes match. A missing pin path is a refusal.
    The caller skips this when the import comes from an installed copy
    outside the checkout.
    """

    if not path.is_file():
        return f"{path} is not in this checkout"
    expected, error = expected_pin_blob(path, root, commit)
    if error:
        return error
    if not expected:
        return None
    try:
        relative = path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return None
    try:
        data = path.read_bytes()
    except OSError:
        return f"{path.name} is not in this checkout"
    if git_blob_sha1(data) != expected:
        return f"checkout {relative} differs from pin {commit[:12]}"
    return None
