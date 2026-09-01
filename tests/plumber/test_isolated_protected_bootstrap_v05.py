from __future__ import annotations

import ast
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "bootstrap" / "protected_bootstrap_v05.py"


def _run(*arguments: str, cwd: Path | None = None, env: dict[str, str] | None = None):
    return subprocess.run(
        [sys.executable, "-I", "-S", "-B", str(SCRIPT), *arguments],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        check=False,
    )


def test_isolated_bootstrap_source_imports_only_the_standard_library() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.partition(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module.partition(".")[0])

    assert imported <= sys.stdlib_module_names | {"__future__"}
    assert "aureon" not in imported
    assert "subprocess" not in imported
    assert "socket" not in imported


def test_isolated_bootstrap_ignores_sitecustomize_and_holds_without_side_effects(
    tmp_path: Path,
) -> None:
    canary = tmp_path / "sitecustomize-ran.txt"
    (tmp_path / "sitecustomize.py").write_text(
        f"from pathlib import Path\nPath({str(canary)!r}).write_text('ran')\n",
        encoding="utf-8",
    )
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(tmp_path)

    result = _run("--target-id", "windows-wake", cwd=tmp_path, env=environment)

    assert result.returncode == 1, result.stderr
    receipt = json.loads(result.stdout)
    assert receipt["decision"] == "HOLD"
    assert receipt["target_registered"] is True
    assert receipt["repo_root_derived_from_bootstrap_path"] is True
    assert receipt["bootstrap_path_bound"] is True
    assert receipt["bootstrap_source_sha256"] == hashlib.sha256(
        SCRIPT.read_bytes()
    ).hexdigest()
    assert receipt["caller_controlled_root_accepted"] is False
    assert receipt["source_scope_schema"] == (
        "aureon.plumber.isolated-perimeter-source-scope.v05"
    )
    assert receipt["source_scope_measured"] is True
    assert receipt["source_scope_stable"] is True
    assert receipt["source_scope_file_count"] >= 50
    assert receipt["source_scope_total_bytes"] > 0
    assert len(receipt["source_scope_sha256"]) == 64
    assert receipt["target_source_measured"] is True
    assert receipt["target_source_in_source_scope"] is True
    assert receipt["target_source_sha256"] == hashlib.sha256(
        (ROOT / "scripts" / "launchers" / "AUREON_WAKE_UP_FULL_AUTONOMOUS.ps1").read_bytes()
    ).hexdigest()
    assert receipt["target_argument_policy"] == "empty-arguments-v1"
    assert receipt["target_argument_policy_attested"] is True
    assert receipt["target_imported"] is False
    assert receipt["target_called"] is False
    assert receipt["child_process_started"] is False
    assert receipt["bootstrap_subprocess_started"] is False
    assert receipt["git_invoked"] is False
    assert receipt["network_accessed"] is False
    assert receipt["file_written"] is False
    assert receipt["process_start_authorized"] is False
    assert canary.exists() is False


def test_isolated_bootstrap_emits_target_hold_in_minimal_image_layout(
    tmp_path: Path,
) -> None:
    image_script = (
        tmp_path / "app" / "scripts" / "bootstrap" / "protected_bootstrap_v05.py"
    )
    image_script.parent.mkdir(parents=True)
    image_script.write_bytes(SCRIPT.read_bytes())

    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-S",
            "-B",
            str(image_script),
            "--target-id",
            "operator-wsgi",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        check=False,
    )

    assert result.returncode == 1, result.stderr
    receipt = json.loads(result.stdout)
    assert receipt["decision"] == "HOLD"
    assert receipt["target_id"] == "operator-wsgi"
    assert receipt["target_registered"] is True
    assert receipt["bootstrap_path_bound"] is True
    assert receipt["bootstrap_source_sha256"] == hashlib.sha256(
        image_script.read_bytes()
    ).hexdigest()


def test_isolated_bootstrap_rejects_caller_controlled_root() -> None:
    result = _run(
        "--target-id",
        "operator",
        "--",
        "--root",
        str(ROOT),
    )

    assert result.returncode == 2, result.stderr
    receipt = json.loads(result.stdout)
    assert receipt["decision"] == "HOLD"
    assert receipt["reason"] == "exact_isolated_bootstrap_request_required"
    assert receipt["process_start_authorized"] is False


def test_isolated_bootstrap_unknown_target_is_a_visible_hold() -> None:
    result = _run("--target-id", "not-registered")

    assert result.returncode == 1, result.stderr
    receipt = json.loads(result.stdout)
    assert receipt["decision"] == "HOLD"
    assert receipt["target_registered"] is False
    assert "fixed_bootstrap_target" in receipt["failed_checks"]
    assert receipt["target_entrypoint_commitment"] == "0" * 64


def test_isolated_bootstrap_measures_every_registered_perimeter_source() -> None:
    namespace = __import__("runpy").run_path(str(SCRIPT))
    root = ROOT.resolve()
    measurements: dict[str, tuple[str, int]] = {}
    summary, measurements = namespace["_measure_source_scope"](root)

    assert summary["schema"] == "aureon.plumber.isolated-perimeter-source-scope.v05"
    assert summary["file_count"] == len(measurements)
    assert summary["file_count"] >= len(namespace["_TARGETS"])
    assert summary["total_bytes"] == sum(size for _, size in measurements.values())
    assert len(summary["sha256"]) == 64
    for runtime_kind, entrypoint in namespace["_TARGETS"].values():
        relative = namespace["_target_source_relative"](
            runtime_kind,
            entrypoint,
            root,
        )
        assert relative in measurements

    assert namespace["_TARGETS"]["master-launcher"] == (
        "python",
        "aureon.autonomous.aureon_master_launcher",
    )


def test_nonempty_arguments_remain_unattested_and_cannot_start_target() -> None:
    result = _run("--target-id", "operator", "--", "--example")

    assert result.returncode == 1, result.stderr
    receipt = json.loads(result.stdout)
    assert receipt["decision"] == "HOLD"
    assert receipt["target_source_measured"] is True
    assert receipt["target_argument_policy_attested"] is False
    assert "target_argument_policy" in receipt["failed_checks"]
    assert receipt["target_imported"] is False
    assert receipt["target_called"] is False
    assert receipt["process_start_authorized"] is False
