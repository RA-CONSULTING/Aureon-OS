"""Build and inspect an Aureon wheel. This script does not upload.

Public PyPI is refused here. TestPyPI upload lives in
``packaging/upload_testpypi.py`` and runs only from the gated Actions job.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path


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
CONSOLE_SOURCE = ROOT / metadata.CONSOLE_MODULE
HOLD_KEYS = (
    "decision",
    "production_ready",
    "target_imported",
    "child_process_started",
    "network_accessed",
    "file_written",
)


def _fail(message: str) -> int:
    print(message, file=sys.stderr)
    return 2


def refuse_upload(argv: list[str]) -> str | None:
    for arg in argv:
        lowered = arg.lower()
        if lowered in {"--upload", "--publish", "upload", "publish"} or "pypi" in lowered:
            return (
                "This script only builds and inspects a wheel. It does not upload. "
                "TestPyPI upload is packaging/upload_testpypi.py inside the gated "
                "GitHub Actions job. Public PyPI is refused."
            )
    return None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _prepare_outdir() -> None:
    if OUTDIR.relative_to(ROOT).parts != ("dist", "python-wheel"):
        raise RuntimeError("refusing to write outside dist/python-wheel")
    if OUTDIR.exists():
        shutil.rmtree(OUTDIR)
    OUTDIR.mkdir(parents=True)


def _run_quiet(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> None:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        sys.stderr.write(completed.stdout)
        sys.stderr.write(completed.stderr)
        raise RuntimeError(f"command failed ({completed.returncode}): {command[0:4]}")


def _build() -> None:
    command = [
        sys.executable,
        "-m",
        "build",
        "--sdist",
        "--wheel",
        "--outdir",
        str(OUTDIR),
        str(ROOT),
    ]
    _run_quiet(command, cwd=ROOT)


def _artifacts() -> tuple[Path, Path]:
    wheels = sorted(OUTDIR.glob("aureon-*.whl"))
    sdists = sorted(OUTDIR.glob("aureon-*.tar.gz"))
    extras = [
        path.name
        for path in OUTDIR.iterdir()
        if path not in wheels and path not in sdists
    ]
    if len(wheels) != 1 or len(sdists) != 1 or extras:
        raise RuntimeError(
            f"expected one wheel and one sdist, found wheels={wheels} "
            f"sdists={sdists} extras={extras}"
        )
    return wheels[0], sdists[0]


def _check_wheel(wheel: Path) -> None:
    with zipfile.ZipFile(wheel) as archive:
        errors = metadata.inspect_wheel(archive)
        packaged = archive.read(metadata.CONSOLE_MODULE)
    if packaged.replace(b"\r\n", b"\n") != CONSOLE_SOURCE.read_bytes().replace(b"\r\n", b"\n"):
        errors.append("inert console module does not match the checkout")
    if errors:
        raise RuntimeError("; ".join(errors))


def _check_sdist(sdist: Path) -> None:
    with tarfile.open(sdist, "r:gz") as archive:
        names = archive.getnames()
    required = (
        "pyproject.toml",
        "PKG-INFO",
        metadata.CONSOLE_MODULE,
        "aureon/__init__.py",
        "LICENSE",
    )
    missing = [name for name in required if not any(item.endswith("/" + name) or item.endswith(name) for item in names)]
    if missing:
        raise RuntimeError(f"sdist is missing {missing}")
    roots: set[str] = set()
    for name in names:
        parts = name.split("/")
        if len(parts) >= 2 and parts[1]:
            roots.add(parts[1])
    forbidden = roots.intersection({"aureon_fusion", "frontend", ".github", ".env"})
    if forbidden:
        raise RuntimeError(f"sdist includes a tree outside the wheel: {sorted(forbidden)}")


def _twine_check(wheel: Path, sdist: Path) -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "twine", "check", str(wheel), str(sdist)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        sys.stderr.write(completed.stdout)
        sys.stderr.write(completed.stderr)
        raise RuntimeError("twine check failed")


def _hold_probe(wheel: Path) -> dict[str, str]:
    """Install the wheel in a throwaway venv and run each console script."""
    results: dict[str, str] = {}
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    with tempfile.TemporaryDirectory(prefix="aureon-wheel-") as temporary:
        venv = Path(temporary) / "venv"
        _run_quiet(
            [sys.executable, "-m", "venv", "--copies", str(venv)],
            cwd=venv.parent,
        )
        bindir = venv / ("Scripts" if os.name == "nt" else "bin")
        python = bindir / ("python.exe" if os.name == "nt" else "python")
        _run_quiet(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-input",
                str(wheel),
            ],
            cwd=venv,
            env=env,
        )
        version = subprocess.run(
            [
                str(python),
                "-c",
                "import importlib.metadata as metadata; print(metadata.version('aureon'))",
            ],
            cwd=venv,
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )
        if version.returncode != 0 or version.stdout.strip() != metadata.DISTRIBUTION_VERSION:
            raise RuntimeError(
                "installed distribution version is "
                f"{version.stdout.strip()!r} stderr={version.stderr.strip()!r}"
            )
        for name in metadata.EXPECTED_SCRIPTS:
            script = bindir / (f"{name}.exe" if os.name == "nt" else name)
            completed = subprocess.run(
                [str(script)],
                cwd=venv,
                env=env,
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if completed.returncode != 1:
                raise RuntimeError(
                    f"{name} exited {completed.returncode}, expected HOLD exit 1; "
                    f"stderr={completed.stderr.strip()!r}"
                )
            receipt = json.loads(completed.stdout)
            if receipt.get("decision") != "HOLD":
                raise RuntimeError(f"{name} decision is {receipt.get('decision')!r}")
            if receipt.get("production_ready") is not False:
                raise RuntimeError(f"{name} readiness flag is not false")
            for key in HOLD_KEYS:
                if key not in receipt:
                    raise RuntimeError(f"{name} receipt is missing {key}")
            if receipt.get("target_imported") is not False:
                raise RuntimeError(f"{name} imported a target")
            results[name] = "HOLD"
    return results


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    refused = refuse_upload(arguments)
    if refused is not None:
        return _fail(refused)
    if arguments:
        return _fail(
            "This script takes no options. It writes dist/python-wheel and stops."
        )
    try:
        _prepare_outdir()
        _build()
        wheel, sdist = _artifacts()
        _check_wheel(wheel)
        _check_sdist(sdist)
        _twine_check(wheel, sdist)
        scripts = _hold_probe(wheel)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError, tarfile.TarError, zipfile.BadZipFile) as exc:
        return _fail(str(exc))
    report = {
        "schema": "aureon.python-wheel-dry-run.v1",
        "decision": "HOLD",
        "go_live": "HOLD",
        "uploaded": False,
        "public_pypi": False,
        "distribution": metadata.DISTRIBUTION_NAME,
        "version": metadata.DISTRIBUTION_VERSION,
        "wheel": wheel.name,
        "wheel_sha256": _sha256(wheel),
        "sdist": sdist.name,
        "sdist_sha256": _sha256(sdist),
        "console_scripts": scripts,
        "production_ready": False,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
