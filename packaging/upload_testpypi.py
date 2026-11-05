"""Upload an already built Aureon wheel to TestPyPI. Public PyPI is refused.

The job runs only when all of these are true:

- the process is GitHub Actions
- the event is ``workflow_dispatch``
- ``AUREON_PUBLISH_CONFIRM`` is ``publish-testpypi``
- ``AUREON_ALLOW_TESTPYPI`` is ``gary-yes``
- ``TWINE_PASSWORD`` is the TestPyPI token

This file does not contain a token. A laptop shell cannot pass the Actions
gate. Go-live stays HOLD either way.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import urlparse


def _load_metadata():
    path = Path(__file__).with_name("wheel_metadata.py")
    spec = importlib.util.spec_from_file_location("aureon_wheel_metadata", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("missing wheel_metadata.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


metadata = _load_metadata()

ROOT = Path(__file__).resolve().parents[1]
OUTDIR = ROOT / "dist" / "python-wheel"
TESTPYPI_LEGACY = "https://test.pypi.org/legacy/"
CONFIRM = "publish-testpypi"
GARY_YES = "gary-yes"


def blocked_reason(environ: dict[str, str]) -> str | None:
    if environ.get("GITHUB_ACTIONS") != "true":
        return "upload is refused outside GitHub Actions"
    if environ.get("GITHUB_EVENT_NAME") != "workflow_dispatch":
        return "upload is refused except on manual workflow_dispatch"
    if environ.get("AUREON_PUBLISH_CONFIRM") != CONFIRM:
        return "confirm gate is closed"
    if environ.get("AUREON_ALLOW_TESTPYPI") != GARY_YES:
        return "Gary yes gate is closed"
    password = environ.get("TWINE_PASSWORD", "")
    if password == "":
        return "TestPyPI token is unset"
    if password.strip() != password or any(character in password for character in "\r\n\x00"):
        return "TestPyPI token is malformed"
    return destination_error(TESTPYPI_LEGACY)


def destination_error(url: str) -> str | None:
    if url != TESTPYPI_LEGACY:
        return "refusing a destination other than TestPyPI"
    host = urlparse(url).hostname
    if host != "test.pypi.org":
        return "refusing a host other than test.pypi.org"
    if "upload.pypi.org" in url or url.startswith("https://pypi.org"):
        return "public PyPI is refused"
    return None


ISOLATED_CONFIG = """\
[distutils]
index-servers =
    testpypi

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
"""


def write_config(path: Path) -> None:
    """Write a twine config with no public-index section and no token."""
    if destination_error(TESTPYPI_LEGACY):
        raise RuntimeError("public PyPI is refused")
    if "[pypi]" in ISOLATED_CONFIG.lower():
        raise RuntimeError("public PyPI is refused")
    path.write_text(ISOLATED_CONFIG, encoding="utf-8")


def twine_command(files: list[Path], config_file: Path) -> list[str]:
    # Twine's default repository is the public index. Pin the URL and a config
    # that has no public-index section so a home .pypirc cannot redirect this.
    command = [
        sys.executable,
        "-m",
        "twine",
        "upload",
        "--repository-url",
        TESTPYPI_LEGACY,
        "--config-file",
        str(config_file),
        "--non-interactive",
        "--disable-progress-bar",
        *[str(path) for path in files],
    ]
    for argument in command:
        if argument.startswith("https://") and destination_error(argument):
            raise RuntimeError(destination_error(argument))
        if "upload.pypi.org" in argument or "https://pypi.org" in argument:
            raise RuntimeError("public PyPI is refused")
    return command


def select_artifacts(directory: Path) -> list[Path]:
    if not directory.is_dir():
        raise RuntimeError(f"missing artifact directory {directory}")
    selected: list[Path] = []
    for path in sorted(directory.iterdir()):
        if not path.is_file():
            raise RuntimeError(f"unexpected artifact path {path.name}")
        name = path.name
        if not name.startswith("aureon-"):
            raise RuntimeError(f"unexpected artifact name {name}")
        if name.endswith(".whl") or name.endswith(".tar.gz"):
            selected.append(path)
            continue
        raise RuntimeError(f"unexpected artifact type {name}")
    wheels = [path for path in selected if path.suffix == ".whl"]
    sdists = [path for path in selected if path.name.endswith(".tar.gz")]
    if len(wheels) != 1 or len(sdists) != 1:
        raise RuntimeError("expected one wheel and one sdist")
    return selected


def inspect_artifacts(files: list[Path]) -> None:
    wheel = next(path for path in files if path.suffix == ".whl")
    with zipfile.ZipFile(wheel) as archive:
        errors = metadata.inspect_wheel(archive)
    if errors:
        raise RuntimeError("; ".join(errors))


def main() -> int:
    reason = blocked_reason(dict(os.environ))
    if reason is not None:
        print(reason, file=sys.stderr)
        print(
            "No package was uploaded. Public PyPI is refused. Go-live stays HOLD.",
            file=sys.stderr,
        )
        return 2
    config_path: Path | None = None
    try:
        files = select_artifacts(OUTDIR)
        inspect_artifacts(files)
        handle, config_name = tempfile.mkstemp(prefix="aureon-testpypi-", suffix=".cfg")
        os.close(handle)
        config_path = Path(config_name)
        write_config(config_path)
        command = twine_command(files, config_path)
    except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
        if config_path is not None:
            config_path.unlink(missing_ok=True)
        print(str(exc), file=sys.stderr)
        print("No package was uploaded. Public PyPI is refused.", file=sys.stderr)
        return 2
    env = os.environ.copy()
    env["TWINE_USERNAME"] = "__token__"
    env["TWINE_REPOSITORY_URL"] = TESTPYPI_LEGACY
    env.pop("TWINE_REPOSITORY", None)
    try:
        completed = subprocess.run(command, cwd=ROOT, env=env, check=False)
    finally:
        config_path.unlink(missing_ok=True)
    if completed.returncode != 0:
        print("TestPyPI upload failed. Public PyPI was not used.", file=sys.stderr)
        return completed.returncode
    print("Uploaded the inspected artifacts to TestPyPI. Public PyPI was not used.")
    print("Go-live stays HOLD.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
