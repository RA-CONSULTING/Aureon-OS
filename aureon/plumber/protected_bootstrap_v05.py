"""Fixed-target, fail-closed bootstrap boundary for Aureon runtimes.

This module is deliberately import-inert: importing it never installs an audit
hook, imports a registered target, starts a process, or writes a receipt.  An
evaluation may call its supplied evidence probes; the default source-scope
probe invokes Git.  No bootstrap-process-absence claim is therefore made.  The
v0.5 reference makes the current system-level gap executable and unambiguous:
every official runtime target must pass one exact source-bound OS protection
decision before target import.  While the target-byte, argument-policy, root,
v0.4 Python guard, and durable HNC evidence gaps remain, every target stays on
HOLD.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Final

from aureon.autonomous.aureon_full_live_release import (
    compute_source_scope_digest,
    run_os_protection_audit,
    validate_os_protection_summary,
)

from .runtime_guard_v04 import HNCRuntimeViolationRecorderV04, RuntimeAuditGuardV04

BOOTSTRAP_SCHEMA: Final = "aureon.plumber.protected-bootstrap.v05"
BOOTSTRAP_TARGET_SCHEMA: Final = "aureon.plumber.protected-bootstrap-target.v05"
_TARGET_ID_RE: Final = re.compile(r"^[a-z][a-z0-9-]{0,63}$")
_MAX_TARGET_ARGUMENTS: Final = 64
_MAX_TARGET_ARGUMENT_BYTES: Final = 4096
_MAX_TARGET_ARGUMENT_AGGREGATE_BYTES: Final = 64 * 1024
_ZERO_SHA256: Final = "0" * 64
_MODULE_ROOT: Final = Path(__file__).resolve().parents[2]


def _target_id(value: object) -> str:
    if type(value) is not str or _TARGET_ID_RE.fullmatch(value) is None:
        raise ValueError("exact_bootstrap_target_id_required")
    return value


@dataclass(frozen=True, slots=True)
class ProtectedBootstrapTargetV05:
    target_id: str
    runtime_kind: str
    entrypoint: str

    def __post_init__(self) -> None:
        _target_id(self.target_id)
        if self.runtime_kind not in {"python", "node", "powershell", "native", "shell"}:
            raise ValueError("recognized_bootstrap_runtime_kind_required")
        if (
            type(self.entrypoint) is not str
            or not self.entrypoint
            or len(self.entrypoint.encode("utf-8")) > 512
            or "\x00" in self.entrypoint
        ):
            raise ValueError("bounded_bootstrap_entrypoint_required")

    @property
    def commitment(self) -> str:
        return _sha256(
            {
                "schema": BOOTSTRAP_TARGET_SCHEMA,
                "target_id": self.target_id,
                "runtime_kind": self.runtime_kind,
                "entrypoint": self.entrypoint,
            }
        )


def _target(target_id: str, runtime_kind: str, entrypoint: str) -> ProtectedBootstrapTargetV05:
    return ProtectedBootstrapTargetV05(target_id, runtime_kind, entrypoint)


# The registry is intentionally fixed in source.  CLI input can select an ID;
# it can never supply a module, path, callable, interpreter, or shell command.
PROTECTED_BOOTSTRAP_TARGETS_V05: Final[Mapping[str, ProtectedBootstrapTargetV05]] = (
    MappingProxyType(
        {
            item.target_id: item
            for item in (
                _target("full-live-release", "python", "aureon.autonomous.aureon_full_live_release"),
                _target(
                    "cloud-autonomous-worker",
                    "python",
                    "aureon.autonomous.aureon_autonomous_worker",
                ),
                _target(
                    "cloud-command-center",
                    "python",
                    "aureon.command_centers.aureon_command_center_ui",
                ),
                _target(
                    "cloud-kraken-cache",
                    "python",
                    "aureon.exchanges.kraken_cache_feeder",
                ),
                _target(
                    "cloud-market-cache",
                    "python",
                    "aureon.data_feeds.unified_market_cache",
                ),
                _target("cloud-orca", "python", "aureon.bots.orca_complete_kill_cycle"),
                _target(
                    "cloud-pro-dashboard",
                    "python",
                    "aureon.monitors.aureon_pro_dashboard",
                ),
                _target(
                    "cloud-queen-redistribution",
                    "python",
                    "aureon.queen.queen_power_redistribution",
                ),
                _target("capability-demo", "python", "aureon.saas.capability_demo"),
                _target(
                    "canonical-cloud-organism",
                    "python",
                    "scripts.operations.run_canonical_cloud_organism",
                ),
                _target(
                    "druidic-live-calibration",
                    "python",
                    "scripts.operations.run_live_druidic_calibration",
                ),
                _target("ws-market-data-feeder", "python", "aureon.data_feeds.ws_market_data_feeder"),
                _target("ignition", "python", "scripts/aureon_ignition.py"),
                _target("unified-market-status", "python", "aureon.exchanges.unified_market_status_server"),
                _target("unified-market-trader", "python", "aureon.exchanges.unified_market_trader"),
                _target("parallel-strategy-unity", "python", "aureon.trading.parallel_strategy_unity"),
                _target(
                    "parallel-strategy-audit",
                    "python",
                    "aureon.autonomous.aureon_parallel_strategy_unity_stress_audit",
                ),
                _target("mind-hub", "python", "aureon.autonomous.aureon_mind_thought_action_hub"),
                _target("self-questioning", "python", "aureon.autonomous.aureon_self_questioning_ai"),
                _target("scorm-benchmark", "python", "aureon.operator.scorm_cloud_runner"),
                _target(
                    "organism-observer",
                    "python",
                    "aureon.autonomous.aureon_organism_runtime_observer",
                ),
                _target(
                    "autonomous-self-run",
                    "python",
                    "aureon.autonomous.aureon_autonomous_self_run_loop",
                ),
                _target("saas-system-inventory", "python", "aureon.autonomous.aureon_saas_system_inventory"),
                _target(
                    "frontend-unification-plan",
                    "python",
                    "aureon.autonomous.aureon_frontend_unification_plan",
                ),
                _target(
                    "frontend-evolution-queue",
                    "python",
                    "aureon.autonomous.aureon_frontend_evolution_queue",
                ),
                _target(
                    "autonomous-capability-switchboard",
                    "python",
                    "aureon.autonomous.aureon_autonomous_capability_switchboard",
                ),
                _target("unified-ui-builder", "python", "aureon.autonomous.aureon_unified_ui_builder"),
                _target(
                    "trading-intelligence-checklist",
                    "python",
                    "aureon.autonomous.aureon_trading_intelligence_checklist",
                ),
                _target(
                    "exchange-monitoring-checklist",
                    "python",
                    "aureon.autonomous.aureon_exchange_monitoring_checklist",
                ),
                _target(
                    "exchange-data-capability-matrix",
                    "python",
                    "aureon.autonomous.aureon_exchange_data_capability_matrix",
                ),
                _target(
                    "global-financial-coverage-map",
                    "python",
                    "aureon.autonomous.aureon_global_financial_coverage_map",
                ),
                _target("data-ocean", "python", "aureon.autonomous.aureon_data_ocean"),
                _target("kraken-asset-registry", "python", "aureon.exchanges.kraken_asset_registry"),
                _target("capital-asset-registry", "python", "aureon.exchanges.capital_asset_registry"),
                _target("ingest-global-memory", "python", "scripts/python/ingest_global_memory.py"),
                _target("operator", "python", "aureon.operator.operator_server"),
                _target("operator-wsgi", "python", "aureon.operator.wsgi"),
                _target("organism", "python", "aureon.core.organism_daemon"),
                _target("hnc", "python", "aureon.core.hnc_live_daemon"),
                _target("local-gui", "python", "aureon.operator.local_gui_organism"),
                _target("website", "python", "aureon.operator.website_operator"),
                _target("docker-runtime", "native", "Dockerfile"),
                _target("ephemeris-pipeline", "native", "Dockerfile.ephemeris"),
                _target("linux-supervisor", "native", "deploy/supervisord.linux.conf"),
                _target(
                    "master-launcher",
                    "python",
                    "aureon.autonomous.aureon_master_launcher",
                ),
                _target(
                    "queen-eternal-machine",
                    "python",
                    "aureon.queen.queen_eternal_machine",
                ),
                _target(
                    "queen-web-dashboard",
                    "python",
                    "aureon.queen.queen_web_dashboard",
                ),
                _target(
                    "power-redistribution-engine",
                    "python",
                    "aureon.utils.aureon_power_redistribution_engine",
                ),
                _target("frontend-vite", "node", "frontend:vite"),
                _target("flameborn-runtime", "node", "flameborn:runtime"),
                _target("windows-wake", "powershell", "scripts/launchers/AUREON_WAKE_UP_FULL_AUTONOMOUS.ps1"),
                _target("cloud-supervisor", "native", "deploy/supervisord.conf"),
                _target("production-supervisor", "native", "production/supervisord.conf"),
            )
        }
    )
)


@dataclass(frozen=True, slots=True)
class ProtectedBootstrapRequestV05:
    target_id: str
    target_arguments: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _target_id(self.target_id)
        if type(self.target_arguments) is not tuple or len(self.target_arguments) > _MAX_TARGET_ARGUMENTS:
            raise ValueError("bounded_bootstrap_target_arguments_required")
        aggregate = 0
        for argument in self.target_arguments:
            if type(argument) is not str or "\x00" in argument:
                raise ValueError("exact_bootstrap_target_argument_required")
            size = len(argument.encode("utf-8"))
            if size > _MAX_TARGET_ARGUMENT_BYTES:
                raise ValueError("bounded_bootstrap_target_argument_required")
            aggregate += size
        if aggregate > _MAX_TARGET_ARGUMENT_AGGREGATE_BYTES:
            raise ValueError("bounded_bootstrap_target_argument_aggregate_required")


@dataclass(frozen=True, slots=True)
class ProtectedBootstrapResultV05:
    decision: str
    receipt: Mapping[str, Any]


SourceScopeDigestFn = Callable[[Path], str]
OSProtectionAuditFn = Callable[[Path], Mapping[str, Any]]


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _sha256(value: Mapping[str, Any] | Sequence[str] | str) -> str:
    if isinstance(value, Mapping):
        raw = _canonical_bytes(value)
    elif isinstance(value, str):
        raw = value.encode("utf-8")
    else:
        raw = json.dumps(
            list(value),
            sort_keys=False,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _digest(value: object, code: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(code)
    return value


def _failed_os_summary(reason: str) -> dict[str, Any]:
    return {
        "ok": False,
        "reason": reason,
        "schema": "aureon.os-protection-boundary-census.v1",
        "source_files_scanned": 0,
        "detected_count": 0,
        "classified_count": 0,
        "blocker_count": 0,
        "protected_count": 0,
        "explicit_hold_count": 0,
        "parse_error_count": 1,
        "inventory_sha256": _ZERO_SHA256,
        "certified_full_os_protection": False,
    }


def _runtime_guard_facts() -> dict[str, Any]:
    return {
        "guard_type": "RuntimeAuditGuardV04",
        "guard_production_ready": RuntimeAuditGuardV04.production_ready is True,
        "hnc_recorder_production_ready": HNCRuntimeViolationRecorderV04.production_ready is True,
        "target_import_after_install_attested": False,
        "native_outer_boundary_attested": False,
        "node_boundary_attested": False,
        "powershell_boundary_attested": False,
        "durable_hnc_evidence_attested": False,
        "restart_replay_attested": False,
        "external_head_anchor_attested": False,
    }


def _invalid_request_receipt(*, checked_at: float) -> dict[str, Any]:
    causal = {
        "schema": BOOTSTRAP_SCHEMA,
        "decision": "HOLD",
        "reason": "exact_protected_bootstrap_request_required",
        "failed_checks": ["bootstrap_request"],
        "target_id": "",
        "target_registered": False,
        "target_runtime_kind": "",
        "target_entrypoint_commitment": _ZERO_SHA256,
        "target_source_sha256": _ZERO_SHA256,
        "target_source_bytes_attested": False,
        "target_argument_count": 0,
        "target_arguments_sha256": _sha256(()),
        "target_argument_bounds_validated": False,
        "target_argument_policy_attested": False,
        "measurement_root_module_bound": False,
        "target_import_root_bound": False,
        "source_scope_before": _ZERO_SHA256,
        "source_scope_after": _ZERO_SHA256,
        "source_scope_stable": False,
        "full_os_protection": _failed_os_summary("os_protection_not_evaluated"),
        "runtime_guard": _runtime_guard_facts(),
        "target_imported": False,
        "target_called": False,
        "target_subprocess_started": False,
        "bootstrap_subprocess_absence_attested": False,
        "hnc_denial_recorded": False,
        "durable_hnc_denial_recorded": False,
        "process_start_authorized": False,
        "action_eligible": False,
        "economic_eligible": False,
        "operational_eligible": False,
        "production_ready": False,
        "checked_at": checked_at,
    }
    return {**causal, "receipt_id": f"bootstrap:v05:{_sha256(causal)}"}


def evaluate_protected_bootstrap_v05(
    *,
    root: Path,
    request: ProtectedBootstrapRequestV05,
    source_scope_digest_fn: SourceScopeDigestFn = compute_source_scope_digest,
    os_protection_audit_fn: OSProtectionAuditFn = run_os_protection_audit,
    now: float | None = None,
) -> ProtectedBootstrapResultV05:
    """Evaluate one fixed target without importing or starting it."""

    if type(request) is not ProtectedBootstrapRequestV05:
        raise ValueError("exact_protected_bootstrap_request_required")
    resolved = root.resolve()
    checked_at = float(time.time() if now is None else now)
    failures: list[str] = []
    target = PROTECTED_BOOTSTRAP_TARGETS_V05.get(request.target_id)
    if target is None:
        failures.append("fixed_bootstrap_target")

    measurement_root_module_bound = resolved == _MODULE_ROOT
    if not measurement_root_module_bound:
        failures.append("module_bound_measurement_root")

    # The registry currently binds an entrypoint descriptor, not the bytes that
    # an eventual import/exec would load.  Arbitrary bounded argv is likewise
    # committed but has no per-target policy.  Both remain explicit HOLDs.
    failures.extend(
        (
            "bootstrap_subprocess_absence",
            "target_argument_policy",
            "target_import_root_binding",
            "target_source_attestation",
        )
    )

    try:
        source_before = _digest(
            source_scope_digest_fn(resolved),
            "bootstrap_source_scope_digest_required",
        )
    except Exception:  # noqa: BLE001 - source boundary becomes a fixed HOLD
        source_before = _ZERO_SHA256
        failures.append("source_scope")

    try:
        os_protection = validate_os_protection_summary(
            os_protection_audit_fn(resolved)
        )
    except Exception:  # noqa: BLE001 - audit boundary becomes a fixed HOLD
        os_protection = _failed_os_summary("os_protection_audit_failed")
    if os_protection.get("ok") is not True:
        failures.append("full_os_protection")

    try:
        source_after = _digest(
            source_scope_digest_fn(resolved),
            "bootstrap_source_scope_digest_required",
        )
    except Exception:  # noqa: BLE001 - source boundary becomes a fixed HOLD
        source_after = _ZERO_SHA256
        failures.append("source_scope")
    source_stable = source_before != _ZERO_SHA256 and source_before == source_after
    if not source_stable:
        failures.append("source_scope_stability")

    guard = _runtime_guard_facts()
    if guard["guard_production_ready"] is not True:
        failures.append("runtime_guard_production_readiness")
    if guard["hnc_recorder_production_ready"] is not True:
        failures.append("hnc_evidence_production_readiness")
    if guard["target_import_after_install_attested"] is not True:
        failures.append("sealed_target_import")
    if guard["durable_hnc_evidence_attested"] is not True:
        failures.append("durable_hnc_evidence")
    if target is not None and target.runtime_kind != "python":
        failures.append(f"{target.runtime_kind}_outer_boundary")

    failed_checks = sorted(set(failures))
    target_id = target.target_id if target is not None else request.target_id
    causal = {
        "schema": BOOTSTRAP_SCHEMA,
        "decision": "HOLD",
        "reason": "complete_protected_bootstrap_evidence_required",
        "failed_checks": failed_checks,
        "target_id": target_id,
        "target_registered": target is not None,
        "target_runtime_kind": "" if target is None else target.runtime_kind,
        "target_entrypoint_commitment": _ZERO_SHA256 if target is None else target.commitment,
        "target_source_sha256": _ZERO_SHA256,
        "target_source_bytes_attested": False,
        "target_argument_count": len(request.target_arguments),
        "target_arguments_sha256": _sha256(request.target_arguments),
        "target_argument_bounds_validated": True,
        "target_argument_policy_attested": False,
        "measurement_root_module_bound": measurement_root_module_bound,
        "target_import_root_bound": False,
        "source_scope_before": source_before,
        "source_scope_after": source_after,
        "source_scope_stable": source_stable,
        "full_os_protection": os_protection,
        "runtime_guard": guard,
        "target_imported": False,
        "target_called": False,
        "target_subprocess_started": False,
        "bootstrap_subprocess_absence_attested": False,
        "hnc_denial_recorded": False,
        "durable_hnc_denial_recorded": False,
        "process_start_authorized": False,
        "action_eligible": False,
        "economic_eligible": False,
        "operational_eligible": False,
        "production_ready": False,
        "checked_at": checked_at,
    }
    receipt = {**causal, "receipt_id": f"bootstrap:v05:{_sha256(causal)}"}
    return ProtectedBootstrapResultV05(decision="HOLD", receipt=receipt)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-id", required=True)
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("target_arguments", nargs=argparse.REMAINDER)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    target_arguments = tuple(args.target_arguments)
    if target_arguments[:1] == ("--",):
        target_arguments = target_arguments[1:]
    try:
        request = ProtectedBootstrapRequestV05(
            target_id=args.target_id,
            target_arguments=target_arguments,
        )
        result = evaluate_protected_bootstrap_v05(
            root=_MODULE_ROOT,
            request=request,
        )
        receipt = result.receipt
        exit_code = 1
    except (OSError, TypeError, ValueError):
        receipt = _invalid_request_receipt(checked_at=time.time())
        exit_code = 2
    print(
        json.dumps(
            receipt,
            sort_keys=True,
            indent=2 if args.pretty else None,
            separators=None if args.pretty else (",", ":"),
        )
    )
    return exit_code


def _console_target_main(target_id: str) -> int:
    return main(["--target-id", target_id, "--", *sys.argv[1:]])


def operator_main() -> int:
    return _console_target_main("operator")


def organism_main() -> int:
    return _console_target_main("organism")


def hnc_main() -> int:
    return _console_target_main("hnc")


def local_gui_main() -> int:
    return _console_target_main("local-gui")


def website_main() -> int:
    return _console_target_main("website")


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "BOOTSTRAP_SCHEMA",
    "BOOTSTRAP_TARGET_SCHEMA",
    "PROTECTED_BOOTSTRAP_TARGETS_V05",
    "ProtectedBootstrapRequestV05",
    "ProtectedBootstrapResultV05",
    "ProtectedBootstrapTargetV05",
    "evaluate_protected_bootstrap_v05",
    "hnc_main",
    "local_gui_main",
    "main",
    "operator_main",
    "organism_main",
    "website_main",
]
