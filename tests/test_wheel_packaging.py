"""Contracts for the wheel dry-run and the closed TestPyPI gate."""

from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "python-wheel.yml"
PYPROJECT = ROOT / "pyproject.toml"
DOC = ROOT / "packaging" / "PIP_INSTALL.md"
README = ROOT / "README.md"

FORBIDDEN_DOC_PHRASES = ("production ready", "validated")
FORBIDDEN_WORKFLOW_SNIPPETS = (
    "upload.pypi.org",
    "https://pypi.org",
    "gh-action-pypi-publish",
    "id-token",
    "pull_request_target",
    "secrets.PYPI",
)


def _load(name: str, filename: str):
    path = ROOT / "packaging" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


metadata = _load("aureon_wheel_metadata", "wheel_metadata.py")
uploader = _load("aureon_upload_testpypi", "upload_testpypi.py")


def _workflow() -> tuple[str, dict[str, object]]:
    source = WORKFLOW.read_text(encoding="utf-8")
    loaded = yaml.load(source, Loader=yaml.BaseLoader)
    assert isinstance(loaded, dict)
    return source, loaded


def _metadata(**overrides: str) -> dict[str, list[str]]:
    headers = {
        "Name": ["aureon"],
        "Version": ["2.1.0"],
        "Requires-Python": [">=3.11"],
        "License-Expression": ["MIT"],
        "Summary": ["Supported runtime launch stays on go-live HOLD."],
        "Project-URL": ["Repository, https://github.com/RA-CONSULTING/Aureon-OS"],
        "Classifier": ["Development Status :: 3 - Alpha"],
    }
    for key, value in overrides.items():
        headers[key] = [value]
    return headers


def test_pyproject_metadata_is_explicit_and_does_not_sweep_fusion() -> None:
    project = __import__("tomllib").loads(PYPROJECT.read_text(encoding="utf-8"))
    core = project["project"]
    assert core["name"] == "aureon"
    assert core["version"] == "2.1.0"
    assert core["requires-python"] == ">=3.11"
    assert core["license"] == "MIT"
    assert core["license-files"] == ["LICENSE"]
    assert "go-live HOLD" in core["description"]
    assert core["urls"]["Repository"] == "https://github.com/RA-CONSULTING/Aureon-OS"
    assert all("Production/Stable" not in item for item in core["classifiers"])
    assert core["scripts"] == metadata.EXPECTED_SCRIPTS
    find = project["tool"]["setuptools"]["packages"]["find"]
    assert find["include"] == ["aureon", "aureon.*"]
    assert find["exclude"] == ["aureon_fusion*"]
    assert project["tool"]["setuptools"]["py-modules"] == [
        "protected_console_bootstrap_v05"
    ]


def test_build_script_refuses_upload_without_building() -> None:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "packaging" / "build_wheel.py"), "--upload"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 2
    assert "does not upload" in completed.stderr
    assert "Public PyPI is refused" in completed.stderr


def test_metadata_accepts_the_hold_wheel_shape() -> None:
    assert metadata.metadata_errors(_metadata()) == []
    assert metadata.entry_point_errors(metadata.EXPECTED_SCRIPTS) == []


def test_metadata_rejects_public_readiness_and_fusion() -> None:
    headers = _metadata()
    headers["Classifier"] = ["Development Status :: 5 - Production/Stable"]
    assert any("overclaims" in error for error in metadata.metadata_errors(headers))
    errors = metadata.wheel_member_errors(
        [
            "aureon/__init__.py",
            "aureon_fusion/__init__.py",
            "protected_console_bootstrap_v05.py",
            "aureon-2.1.0.dist-info/METADATA",
        ]
    )
    assert any("aureon_fusion" in error for error in errors)


def test_inspect_wheel_reads_a_minimal_archive() -> None:
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        archive.writestr(
            "aureon-2.1.0.dist-info/METADATA",
            "\n".join(
                [
                    "Metadata-Version: 2.4",
                    "Name: aureon",
                    "Version: 2.1.0",
                    "Requires-Python: >=3.11",
                    "License-Expression: MIT",
                    "Summary: Supported runtime launch stays on go-live HOLD.",
                    "Project-URL: Repository, https://github.com/RA-CONSULTING/Aureon-OS",
                    "Classifier: Development Status :: 3 - Alpha",
                    "",
                    "body",
                ]
            ),
        )
        scripts = ["[console_scripts]"]
        scripts.extend(f"{name} = {target}" for name, target in metadata.EXPECTED_SCRIPTS.items())
        archive.writestr(
            "aureon-2.1.0.dist-info/entry_points.txt",
            "\n".join(scripts) + "\n",
        )
        archive.writestr("aureon/__init__.py", "")
        archive.writestr("protected_console_bootstrap_v05.py", "")
    with zipfile.ZipFile(io.BytesIO(payload.getvalue())) as archive:
        assert metadata.inspect_wheel(archive) == []


def test_upload_gate_stays_closed_and_hides_the_token() -> None:
    canary = "testpypi-token-canary-not-a-real-secret"
    reason = uploader.blocked_reason({"TWINE_PASSWORD": canary})
    assert reason == "upload is refused outside GitHub Actions"
    armed = {
        "GITHUB_ACTIONS": "true",
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "AUREON_PUBLISH_CONFIRM": "publish-testpypi",
        "AUREON_ALLOW_TESTPYPI": "gary-yes",
        "TWINE_PASSWORD": canary,
    }
    assert uploader.blocked_reason(armed) is None
    assert uploader.destination_error("https://upload.pypi.org/legacy/")
    assert uploader.destination_error("https://test.pypi.org/legacy/") is None
    command = uploader.twine_command(
        [Path("aureon-2.1.0-py3-none-any.whl")],
        Path("testpypi.cfg"),
    )
    assert "https://upload.pypi.org/legacy/" not in command
    assert command[command.index("--repository-url") + 1] == "https://test.pypi.org/legacy/"
    assert "--repository" not in command
    assert "[pypi]" not in uploader.ISOLATED_CONFIG.lower()
    completed = subprocess.run(
        [sys.executable, str(ROOT / "packaging" / "upload_testpypi.py")],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        env={"PATH": __import__("os").environ["PATH"], "TWINE_PASSWORD": canary},
    )
    assert completed.returncode == 2
    assert canary not in completed.stdout
    assert canary not in completed.stderr
    assert "No package was uploaded" in completed.stderr


def test_workflow_publishes_only_through_the_testpypi_gate() -> None:
    source, workflow = _workflow()
    assert workflow["permissions"] == {"contents": "read"}
    assert "pull_request_target" not in workflow["on"]
    dispatch = workflow["on"]["workflow_dispatch"]["inputs"]
    assert dispatch["publish_target"]["default"] == "none"
    assert "testpypi" in dispatch["publish_target"]["options"]
    jobs = workflow["jobs"]
    assert set(jobs) == {"dry-run", "publish-testpypi"}
    dry = jobs["dry-run"]
    assert "secrets." not in json.dumps(dry)
    assert all("upload_testpypi.py" not in step.get("run", "") for step in dry["steps"])
    publish = jobs["publish-testpypi"]
    condition = publish["if"]
    assert "github.event_name == 'workflow_dispatch'" in condition
    assert "github.event.inputs.publish_target == 'testpypi'" in condition
    assert "github.event.inputs.confirm == 'publish-testpypi'" in condition
    assert "vars.AUREON_ALLOW_TESTPYPI == 'gary-yes'" in condition
    assert publish["environment"] == "testpypi"
    assert publish["permissions"] == {"contents": "read"}
    assert "python packaging/upload_testpypi.py" in source
    assert source.count("secrets.") == 1
    assert "secrets.TESTPYPI_API_TOKEN" in source
    for snippet in FORBIDDEN_WORKFLOW_SNIPPETS:
        assert snippet not in source


def test_install_doc_keeps_the_hold_and_names_both_install_paths() -> None:
    text = DOC.read_text(encoding="utf-8")
    lowered = text.lower()
    for phrase in FORBIDDEN_DOC_PHRASES:
        assert phrase not in lowered
    assert "go-live stays" in lowered
    assert "HOLD" in text
    assert "aureon[operator] @ git+https://github.com/RA-CONSULTING/Aureon-OS.git" in text
    assert "https://test.pypi.org/simple/" in text
    assert "https://test.pypi.org/legacy/" in text
    assert "upload.pypi.org" not in text
    assert "AUREON_ALLOW_TESTPYPI" in text
    assert "gary-yes" in text
    readme = README.read_text(encoding="utf-8")
    assert "packaging/PIP_INSTALL.md" in readme
    for phrase in FORBIDDEN_DOC_PHRASES:
        assert phrase not in readme.lower()
