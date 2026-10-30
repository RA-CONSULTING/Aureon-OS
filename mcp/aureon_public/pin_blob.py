"""Git-blob check for a file loaded from the checkout beside a pinned aureon.

Every checkout load goes through ``load_pinned_source`` or the pinned finder.
Those helpers require the expected blob, read the file once, and execute
those same bytes. ``huggingface/hnc-field/guard.py`` is checked the same way.
Nothing under ``mcp/`` uses ``spec_from_file_location``.
"""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from importlib.abc import Loader
from pathlib import Path
from types import ModuleType

PINNED_PHENOLIC_BLOB = "325484e9299eecb427cf0063590b0a1d17c16f31"
PHENOLIC_MISMATCH = "checkout phenolic_fingerprint differs from pin 8aa6a2d9"


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
        module.__file__ = self._origin
        origin = Path(self._origin)
        if origin.name == "__init__.py":
            module.__path__ = [str(origin.parent)]
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


class PinnedAureonFinder:
    """Blob-check every ``aureon`` import against the pin. A mismatch raises."""

    def __init__(self, root: Path, commit: str) -> None:
        self.root = root
        self.commit = commit

    def find_spec(self, fullname: str, path: object, target: object = None) -> object:
        del path, target
        if fullname != "aureon" and not fullname.startswith("aureon."):
            return None
        relative = self._relative(fullname)
        if relative is None:
            raise ImportError(f"{fullname} is not an aureon module path")
        expected, error = expected_pin_blob(self.root / relative, self.root, self.commit)
        if error or not expected:
            raise ImportError(error or "expected blob is required")
        for candidate in self._files(fullname, relative):
            try:
                data = candidate.read_bytes()
            except OSError:
                continue
            if git_blob_sha1(data) != expected:
                continue
            return self._spec(fullname, data, candidate)
        raise ImportError(f"checkout {relative} differs from pin {self.commit[:12]}")

    def _relative(self, fullname: str) -> str | None:
        parts = fullname.split(".")
        py_file = Path(*parts).with_suffix(".py")
        init_file = Path(*parts) / "__init__.py"
        for relative in (py_file, init_file):
            expected, _error = expected_pin_blob(self.root / relative, self.root, self.commit)
            if expected:
                return relative.as_posix()
        return None

    def _files(self, fullname: str, relative: str) -> list[Path]:
        files: list[Path] = []
        checkout = self.root / relative
        if checkout.is_file():
            files.append(checkout)
        installed = self._installed_origin(fullname)
        if installed is not None and installed not in files:
            files.append(installed)
        return files

    def _installed_origin(self, fullname: str) -> Path | None:
        removed = [finder for finder in sys.meta_path if isinstance(finder, PinnedAureonFinder)]
        for finder in removed:
            sys.meta_path.remove(finder)
        try:
            spec = importlib.util.find_spec(fullname)
        finally:
            for finder in reversed(removed):
                sys.meta_path.insert(0, finder)
        origin = getattr(spec, "origin", None) if spec is not None else None
        if not origin or origin == "namespace":
            return None
        path = Path(origin)
        return path if path.is_file() else None

    def _spec(self, fullname: str, data: bytes, path: Path) -> object:
        loader = _SameBytesLoader(data, str(path))
        spec = importlib.util.spec_from_loader(fullname, loader, origin=str(path))
        if spec is None:
            raise ImportError(f"{fullname} could not be loaded")
        spec.has_location = True
        if path.name == "__init__.py":
            spec.submodule_search_locations = [str(path.parent)]
        return spec


def _loaded_by_finder(module: object) -> bool:
    loader = getattr(getattr(module, "__spec__", None), "loader", None)
    return isinstance(loader, _SameBytesLoader)


def refuse_preseeded_aureon() -> None:
    """Raise when an ``aureon`` module is already loaded by another loader.

    ``import`` returns a ``sys.modules`` hit without calling the finder.
    A guard or a caller that plants a fake module first would skip the blob check.
    """

    for name, module in list(sys.modules.items()):
        if module is None:
            continue
        if name != "aureon" and not name.startswith("aureon."):
            continue
        if not _loaded_by_finder(module):
            raise ImportError(f"{name} was not loaded through the pinned finder")


def import_through_finder(dotted: str) -> ModuleType:
    """Import ``dotted`` and each parent through ``PinnedAureonFinder``.

    ``find_spec`` on the full name is not used. That call imports parent
    packages before any blob check. A parent already in ``sys.modules`` from
    another loader is refused rather than reused.
    """

    if dotted != "aureon" and not dotted.startswith("aureon."):
        raise ImportError("only an aureon module can be loaded")
    install_pinned_aureon_finder()
    parts = dotted.split(".")
    for index in range(1, len(parts) + 1):
        name = ".".join(parts[:index])
        existing = sys.modules.get(name)
        if existing is not None:
            if not _loaded_by_finder(existing):
                raise ImportError(f"{name} was not loaded through the pinned finder")
            continue
        importlib.import_module(name)
        loaded = sys.modules.get(name)
        if loaded is None or not _loaded_by_finder(loaded):
            raise ImportError(f"{name} was not loaded through the pinned finder")
    module = sys.modules.get(dotted)
    if module is None:
        raise ImportError(f"{dotted} could not be loaded")
    return module


def install_pinned_aureon_finder(root: Path | None = None, commit: str | None = None) -> PinnedAureonFinder:
    """Install the finder once. Later aureon imports fail closed on a blob mismatch."""

    from aureon_public.guard_loader import PINNED_COMMIT
    from aureon_public.paths import repo_root

    base = repo_root() if root is None else root
    pin = PINNED_COMMIT if commit is None else commit
    for finder in sys.meta_path:
        if isinstance(finder, PinnedAureonFinder):
            return finder
    finder = PinnedAureonFinder(base, pin)
    sys.meta_path.insert(0, finder)
    return finder


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
    spec.has_location = True
    if path.name == "__init__.py":
        spec.submodule_search_locations = [str(path.parent)]
    module = importlib.util.module_from_spec(spec)
    module.__file__ = str(path)
    if path.name == "__init__.py":
        module.__path__ = [str(path.parent)]
    parent_name, _, child = module_name.rpartition(".")
    module.__package__ = parent_name if parent_name else module_name
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
    try:
        relative = path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return "path is outside the checkout"
    expected, error = expected_pin_blob(path, root, commit)
    if error:
        return error
    if not expected:
        return "expected blob is required"
    try:
        data = path.read_bytes()
    except OSError:
        return f"{path.name} is not in this checkout"
    if git_blob_sha1(data) != expected:
        return f"checkout {relative} differs from pin {commit[:12]}"
    return None
