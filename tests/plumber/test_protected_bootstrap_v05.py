from __future__ import annotations

import json
import subprocess
import sys
import textwrap
import tomllib
from pathlib import Path
from typing import Any

import pytest

from aureon.plumber.protected_bootstrap_v05 import (
    PROTECTED_BOOTSTRAP_TARGETS_V05,
    ProtectedBootstrapRequestV05,
    evaluate_protected_bootstrap_v05,
)
from aureon.plumber.runtime_guard_v04 import (
    HNCRuntimeViolationRecorderV04,
    RuntimeAuditGuardV04,
)

SCOPE = "a" * 64
EXPECTED_TARGET_IDS = {
    "autonomous-capability-switchboard",
    "autonomous-self-run",
    "capital-asset-registry",
    "capability-demo",
    "canonical-cloud-organism",
    "cloud-autonomous-worker",
    "cloud-command-center",
    "cloud-kraken-cache",
    "cloud-market-cache",
    "cloud-orca",
    "cloud-pro-dashboard",
    "cloud-queen-redistribution",
    "cloud-supervisor",
    "data-ocean",
    "druidic-live-calibration",
    "docker-runtime",
    "ephemeris-pipeline",
    "exchange-data-capability-matrix",
    "exchange-monitoring-checklist",
    "flameborn-runtime",
    "frontend-evolution-queue",
    "frontend-unification-plan",
    "frontend-vite",
    "full-live-release",
    "global-financial-coverage-map",
    "hnc",
    "ignition",
    "ingest-global-memory",
    "kraken-asset-registry",
    "linux-supervisor",
    "local-gui",
    "master-launcher",
    "mind-hub",
    "operator",
    "operator-wsgi",
    "organism",
    "organism-observer",
    "parallel-strategy-audit",
    "parallel-strategy-unity",
    "production-supervisor",
    "power-redistribution-engine",
    "queen-eternal-machine",
    "queen-web-dashboard",
    "saas-system-inventory",
    "self-questioning",
    "scorm-benchmark",
    "trading-intelligence-checklist",
    "unified-market-status",
    "unified-market-trader",
    "unified-ui-builder",
    "website",
    "windows-wake",
    "ws-market-data-feeder",
}


def _os_protection_ok(_root: Path) -> dict[str, Any]:
    return {
        "ok": True,
        "reason": "full_os_protection_certified",
        "schema": "aureon.os-protection-boundary-census.v1",
        "source_files_scanned": 5113,
        "detected_count": 6850,
        "classified_count": 6850,
        "blocker_count": 0,
        "protected_count": 6850,
        "explicit_hold_count": 0,
        "parse_error_count": 0,
        "inventory_sha256": "5" * 64,
        "certified_full_os_protection": True,
    }


def _evaluate(
    tmp_path: Path,
    *,
    target_id: str = "unified-market-trader",
    os_protection=_os_protection_ok,
    source_scope=lambda _root: SCOPE,
):
    return evaluate_protected_bootstrap_v05(
        root=tmp_path,
        request=ProtectedBootstrapRequestV05(
            target_id=target_id,
            target_arguments=("--example", "bounded"),
        ),
        source_scope_digest_fn=source_scope,
        os_protection_audit_fn=os_protection,
        now=1_787_100_000.0,
    )


def test_protected_bootstrap_registry_is_fixed_and_exact() -> None:
    assert set(PROTECTED_BOOTSTRAP_TARGETS_V05) == EXPECTED_TARGET_IDS
    assert all(key == value.target_id for key, value in PROTECTED_BOOTSTRAP_TARGETS_V05.items())
    with pytest.raises(TypeError):
        PROTECTED_BOOTSTRAP_TARGETS_V05["injected"] = PROTECTED_BOOTSTRAP_TARGETS_V05[
            "operator"
        ]  # type: ignore[index]
    assert (
        PROTECTED_BOOTSTRAP_TARGETS_V05["master-launcher"].entrypoint
        == "aureon.autonomous.aureon_master_launcher"
    )


def test_declared_console_commands_route_only_to_inert_bootstrap() -> None:
    root = Path(__file__).resolve().parents[2]
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))

    assert project["project"]["scripts"] == {
        "aureon-operator": "protected_console_bootstrap_v05:operator_main",
        "aureon-organism": "protected_console_bootstrap_v05:organism_main",
        "aureon-hnc": "protected_console_bootstrap_v05:hnc_main",
        "aureon-local-gui": "protected_console_bootstrap_v05:local_gui_main",
        "aureon-website": "protected_console_bootstrap_v05:website_main",
    }
    assert project["tool"]["setuptools"]["py-modules"] == [
        "protected_console_bootstrap_v05"
    ]


def test_full_evidence_cannot_override_current_guard_hold(tmp_path: Path) -> None:
    module_name = "aureon.exchanges.unified_market_trader"
    assert module_name not in sys.modules

    result = _evaluate(tmp_path)

    assert result.decision == "HOLD"
    assert result.receipt["target_registered"] is True
    assert result.receipt["target_imported"] is False
    assert result.receipt["target_called"] is False
    assert result.receipt["target_subprocess_started"] is False
    assert result.receipt["bootstrap_subprocess_absence_attested"] is False
    assert result.receipt["target_source_sha256"] == "0" * 64
    assert result.receipt["target_source_bytes_attested"] is False
    assert result.receipt["target_argument_bounds_validated"] is True
    assert result.receipt["target_argument_policy_attested"] is False
    assert result.receipt["measurement_root_module_bound"] is False
    assert result.receipt["target_import_root_bound"] is False
    assert result.receipt["process_start_authorized"] is False
    assert result.receipt["production_ready"] is False
    assert result.receipt["runtime_guard"]["guard_production_ready"] is False
    assert "runtime_guard_production_readiness" in result.receipt["failed_checks"]
    assert "sealed_target_import" in result.receipt["failed_checks"]
    assert "durable_hnc_evidence" in result.receipt["failed_checks"]
    assert "bootstrap_subprocess_absence" in result.receipt["failed_checks"]
    assert "module_bound_measurement_root" in result.receipt["failed_checks"]
    assert "target_argument_policy" in result.receipt["failed_checks"]
    assert "target_import_root_binding" in result.receipt["failed_checks"]
    assert "target_source_attestation" in result.receipt["failed_checks"]
    assert module_name not in sys.modules


def test_unknown_target_and_unsupported_runtime_hold_without_passthrough(tmp_path: Path) -> None:
    unknown = _evaluate(tmp_path, target_id="not-registered")
    node = _evaluate(tmp_path, target_id="frontend-vite")

    assert unknown.receipt["target_registered"] is False
    assert "fixed_bootstrap_target" in unknown.receipt["failed_checks"]
    assert unknown.receipt["target_entrypoint_commitment"] == "0" * 64
    assert node.receipt["target_runtime_kind"] == "node"
    assert "node_outer_boundary" in node.receipt["failed_checks"]
    assert node.receipt["process_start_authorized"] is False


def test_forged_os_protection_decision_is_reduced_to_audit_failure(tmp_path: Path) -> None:
    def forged(root: Path) -> dict[str, Any]:
        payload = _os_protection_ok(root)
        payload["blocker_count"] = 1
        payload["protected_count"] = 6849
        return payload

    result = _evaluate(tmp_path, os_protection=forged)

    assert result.receipt["full_os_protection"]["ok"] is False
    assert result.receipt["full_os_protection"]["reason"] == "os_protection_audit_failed"
    assert "full_os_protection" in result.receipt["failed_checks"]


def test_source_scope_drift_holds_before_target_import(tmp_path: Path) -> None:
    values = iter(("1" * 64, "2" * 64))
    result = _evaluate(tmp_path, source_scope=lambda _root: next(values))

    assert result.receipt["source_scope_stable"] is False
    assert "source_scope_stability" in result.receipt["failed_checks"]
    assert result.receipt["target_imported"] is False


def test_v04_cannot_be_misrepresented_as_boot_ready() -> None:
    assert RuntimeAuditGuardV04.production_ready is False
    assert HNCRuntimeViolationRecorderV04.production_ready is False


def test_protected_bootstrap_import_is_inert() -> None:
    child = textwrap.dedent(
        r"""
        import json
        import sys

        events = []
        banned = {
            "os.system",
            "subprocess.Popen",
            "socket.connect",
            "socket.bind",
            "socket.getaddrinfo",
            "sys.addaudithook",
        }

        def hook(event, args):
            if event in banned:
                events.append(event)
            if event == "open" and len(args) >= 2:
                mode = args[1]
                if isinstance(mode, str) and any(flag in mode for flag in "wax+"):
                    events.append("open-write")

        sys.addaudithook(hook)
        import aureon.plumber.protected_bootstrap_v05 as bootstrap
        print(json.dumps({"events": events, "targets": len(bootstrap.PROTECTED_BOOTSTRAP_TARGETS_V05)}))
        """
    )
    result = subprocess.run(
        [sys.executable, "-B", "-c", child],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"events": [], "targets": len(EXPECTED_TARGET_IDS)}


def test_cli_holds_before_using_target_arguments(tmp_path: Path) -> None:
    canary = tmp_path / "must-not-exist.txt"
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "aureon.plumber.protected_bootstrap_v05",
            "--target-id",
            "ignition",
            "--",
            "--write-canary",
            str(canary),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        check=False,
    )

    assert result.returncode == 1
    receipt = json.loads(result.stdout)
    assert receipt["decision"] == "HOLD"
    assert receipt["measurement_root_module_bound"] is True
    assert receipt["target_import_root_bound"] is False
    assert receipt["target_argument_policy_attested"] is False
    assert receipt["target_source_bytes_attested"] is False
    assert receipt["target_imported"] is False
    assert receipt["target_subprocess_started"] is False
    assert receipt["bootstrap_subprocess_absence_attested"] is False
    assert canary.exists() is False


def test_cli_rejects_caller_controlled_measurement_root(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "aureon.plumber.protected_bootstrap_v05",
            "--root",
            str(tmp_path),
            "--target-id",
            "operator",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        check=False,
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert "error:" in result.stderr
    assert "--target-id" in result.stderr
