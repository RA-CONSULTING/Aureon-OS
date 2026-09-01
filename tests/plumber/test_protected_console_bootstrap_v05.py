from __future__ import annotations

import ast
import hashlib
import json
import runpy
import subprocess
import sys
import textwrap
import tomllib
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "protected_console_bootstrap_v05.py"
ISOLATED_SCRIPT = ROOT / "scripts" / "bootstrap" / "protected_bootstrap_v05.py"
PYPROJECT = ROOT / "pyproject.toml"

ENTRY_POINTS = {
    "aureon-hnc": "protected_console_bootstrap_v05:hnc_main",
    "aureon-local-gui": "protected_console_bootstrap_v05:local_gui_main",
    "aureon-operator": "protected_console_bootstrap_v05:operator_main",
    "aureon-organism": "protected_console_bootstrap_v05:organism_main",
    "aureon-website": "protected_console_bootstrap_v05:website_main",
}

_FRESH_INTERPRETER = textwrap.dedent(
    r"""
    import builtins
    import contextlib
    import importlib.metadata
    import io
    import json
    import os
    import socket
    import subprocess
    import sys

    root, entry_name, entry_value, *target_arguments = sys.argv[1:]
    sys.path.insert(0, root)
    sys.dont_write_bytecode = True
    audited_actions = []
    write_flags = os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_TRUNC

    def audit(event, arguments):
        if event == "open" and len(arguments) >= 3:
            mode = arguments[1]
            flags = arguments[2]
            write_mode = isinstance(mode, str) and any(item in mode for item in "wax+")
            write_flag = isinstance(flags, int) and bool(flags & write_flags)
            if write_mode or write_flag:
                audited_actions.append(event)
        elif event.startswith("socket.") or event in {
            "os.exec",
            "os.fork",
            "os.forkpty",
            "os.posix_spawn",
            "os.spawn",
            "os.system",
            "subprocess.Popen",
        }:
            audited_actions.append(event)

    sys.addaudithook(audit)
    entry_point = importlib.metadata.EntryPoint(
        name=entry_name,
        value=entry_value,
        group="console_scripts",
    )
    function = entry_point.load()

    blocked_actions = []

    def forbidden(label):
        def reject(*_args, **_kwargs):
            blocked_actions.append(label)
            raise AssertionError(label)
        return reject

    builtins.open = forbidden("builtins.open")
    io.open = forbidden("io.open")
    os.open = forbidden("os.open")
    os.mkdir = forbidden("os.mkdir")
    os.remove = forbidden("os.remove")
    os.rename = forbidden("os.rename")
    os.replace = forbidden("os.replace")
    os.system = forbidden("os.system")
    socket.socket = forbidden("socket.socket")
    subprocess.Popen = forbidden("subprocess.Popen")
    subprocess.run = forbidden("subprocess.run")

    sys.argv = [entry_name, *target_arguments]
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        exit_code = function()
    receipt = json.loads(output.getvalue())
    aureon_modules = sorted(
        name for name in sys.modules if name.casefold().startswith("aureon")
    )
    print(json.dumps({
        "audited_actions": audited_actions,
        "blocked_actions": blocked_actions,
        "aureon_modules": aureon_modules,
        "exit_code": exit_code,
        "receipt": receipt,
    }, sort_keys=True, separators=(",", ":")))
    """
)


def _imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.partition(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module.partition(".")[0])
    return imported


def _run_entry(
    entry_name: str,
    entry_value: str,
    *target_arguments: str,
) -> dict[str, Any]:
    completed = subprocess.run(
        [
            sys.executable,
            "-I",
            "-S",
            "-B",
            "-c",
            _FRESH_INTERPRETER,
            str(ROOT),
            entry_name,
            entry_value,
            *target_arguments,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert isinstance(result, dict)
    return result


def test_console_bootstrap_source_is_top_level_and_stdlib_only() -> None:
    assert MODULE.parent == ROOT
    assert MODULE.name == "protected_console_bootstrap_v05.py"
    assert _imported_roots(MODULE) <= sys.stdlib_module_names | {"__future__"}
    assert "aureon" not in _imported_roots(MODULE)


def test_console_registry_and_bounds_match_the_isolated_bootstrap() -> None:
    console = runpy.run_path(str(MODULE))
    isolated = runpy.run_path(str(ISOLATED_SCRIPT))
    expected_targets = {
        target_id: isolated["_TARGETS"][target_id]
        for target_id in ("hnc", "local-gui", "operator", "organism", "website")
    }

    assert dict(console["_TARGETS"]) == expected_targets
    assert console["_MAX_ARGUMENTS"] == isolated["_MAX_ARGUMENTS"]
    assert console["_MAX_ARGUMENT_BYTES"] == isolated["_MAX_ARGUMENT_BYTES"]
    assert (
        console["_MAX_ARGUMENT_AGGREGATE_BYTES"]
        == isolated["_MAX_ARGUMENT_AGGREGATE_BYTES"]
    )


def test_project_scripts_route_only_to_the_inert_top_level_module() -> None:
    project = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))

    assert project["project"]["scripts"] == ENTRY_POINTS
    assert project["tool"]["setuptools"]["py-modules"] == [
        "protected_console_bootstrap_v05"
    ]
    assert all(
        value.startswith("protected_console_bootstrap_v05:")
        for value in project["project"]["scripts"].values()
    )


@pytest.mark.parametrize(("entry_name", "entry_value"), ENTRY_POINTS.items())
def test_each_console_entry_loads_without_aureon_and_emits_only_hold(
    entry_name: str,
    entry_value: str,
) -> None:
    result = _run_entry(entry_name, entry_value)
    receipt = result["receipt"]
    assert result["exit_code"] == 1
    assert result["aureon_modules"] == []
    assert result["audited_actions"] == []
    assert result["blocked_actions"] == []
    assert receipt["decision"] == "HOLD"
    assert receipt["target_registered"] is True
    assert receipt["bootstrap_module"] == "protected_console_bootstrap_v05"
    assert receipt["bootstrap_root_derived_from_module_path"] is True
    assert receipt["bootstrap_root_sha256"] == hashlib.sha256(
        str(ROOT.resolve()).casefold().encode("utf-8")
    ).hexdigest()
    assert receipt["caller_controlled_root_accepted"] is False
    assert receipt["target_imported"] is False
    assert receipt["target_called"] is False
    assert receipt["child_process_started"] is False
    assert receipt["bootstrap_subprocess_started"] is False
    assert receipt["git_invoked"] is False
    assert receipt["network_accessed"] is False
    assert receipt["file_written"] is False
    assert receipt["process_start_authorized"] is False
    assert receipt["action_eligible"] is False
    assert receipt["economic_eligible"] is False
    assert receipt["operational_eligible"] is False
    assert receipt["production_ready"] is False


def test_console_entry_rejects_caller_controlled_root_without_action() -> None:
    result = _run_entry(
        "aureon-operator",
        ENTRY_POINTS["aureon-operator"],
        "--root",
        str(ROOT.parent),
    )
    receipt = result["receipt"]

    assert result["exit_code"] == 2
    assert result["aureon_modules"] == []
    assert result["audited_actions"] == []
    assert result["blocked_actions"] == []
    assert receipt["decision"] == "HOLD"
    assert receipt["reason"] == "exact_isolated_bootstrap_request_required"
    assert receipt["target_id"] == "operator"
    assert receipt["target_registered"] is True
    assert receipt["caller_controlled_root_accepted"] is False
    assert receipt["target_imported"] is False
    assert receipt["target_called"] is False
    assert receipt["child_process_started"] is False
    assert receipt["network_accessed"] is False
    assert receipt["file_written"] is False
    assert receipt["process_start_authorized"] is False
    assert receipt["action_eligible"] is False
    assert receipt["economic_eligible"] is False
    assert receipt["operational_eligible"] is False
    assert receipt["production_ready"] is False
