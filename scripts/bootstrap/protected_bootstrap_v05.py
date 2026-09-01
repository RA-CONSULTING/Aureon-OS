"""Minimal isolated HOLD boundary before any Aureon package or target import.

Run this file directly with ``python -I -S -B``.  It imports only the Python
standard library, derives the repository root from its own fixed location, and
never imports Aureon, invokes Git, starts a child, writes a file, or accepts an
arbitrary entrypoint.  Until a production guard and durable HNC sink exist, its
only valid decision is HOLD.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from pathlib import Path
from types import MappingProxyType

SCHEMA = "aureon.plumber.isolated-protected-bootstrap.v05"
_TARGET_RE = re.compile(r"^[a-z][a-z0-9-]{0,63}$")
_MAX_ARGUMENTS = 64
_MAX_ARGUMENT_BYTES = 4096
_MAX_ARGUMENT_AGGREGATE_BYTES = 64 * 1024
_ZERO_SHA256 = "0" * 64
_SOURCE_SCOPE_SCHEMA = "aureon.plumber.isolated-perimeter-source-scope.v05"
_MAX_SOURCE_FILES = 256
_MAX_SOURCE_BYTES = 512 * 1024 * 1024
_MAX_SINGLE_SOURCE_BYTES = 128 * 1024 * 1024
_PROTECTION_SOURCE_PATHS = frozenset(
    {
        "aureon/autonomous/aureon_intrusion_protection_bridge.py",
        "aureon/autonomous/aureon_runtime_protection_proposal_vault_v05.py",
        "aureon/plumber/authorization_chain_v02.py",
        "aureon/plumber/magic_star_v02.py",
        "aureon/plumber/os_protection.py",
        "aureon/plumber/production_release_broker_v03.py",
        "aureon/plumber/protected_bootstrap_v05.py",
        "aureon/plumber/release_boundary_v02.py",
        "aureon/plumber/runtime_guard_v04.py",
        "aureon/plumber/runtime_intrusion_ledger_v04.py",
        "aureon/plumber/star_custody_v02.py",
        "protected_console_bootstrap_v05.py",
        "pyproject.toml",
        "scripts/bootstrap/protected_bootstrap_v05.py",
        "scripts/validation/audit_economic_mutation_boundaries.py",
        "scripts/validation/audit_os_protection_boundaries.py",
    }
)
_NODE_TARGET_SOURCES = MappingProxyType(
    {
        "flameborn:runtime": "flameborn/runtime/server.mjs",
        "frontend:vite": "frontend/package.json",
    }
)

# Only perimeter IDs are needed here.  Inner fixed Python targets remain in the
# package registry, but cannot be reached until this outer boundary is ready.
_TARGETS = MappingProxyType(
    {
        "cloud-autonomous-worker": (
            "python",
            "aureon.autonomous.aureon_autonomous_worker",
        ),
        "cloud-command-center": (
            "python",
            "aureon.command_centers.aureon_command_center_ui",
        ),
        "cloud-kraken-cache": (
            "python",
            "aureon.exchanges.kraken_cache_feeder",
        ),
        "cloud-market-cache": (
            "python",
            "aureon.data_feeds.unified_market_cache",
        ),
        "cloud-orca": ("python", "aureon.bots.orca_complete_kill_cycle"),
        "cloud-pro-dashboard": (
            "python",
            "aureon.monitors.aureon_pro_dashboard",
        ),
        "cloud-queen-redistribution": (
            "python",
            "aureon.queen.queen_power_redistribution",
        ),
        "cloud-supervisor": ("native", "deploy/supervisord.conf"),
        "capability-demo": ("python", "aureon.saas.capability_demo"),
        "canonical-cloud-organism": (
            "python",
            "scripts.operations.run_canonical_cloud_organism",
        ),
        "data-ocean": ("python", "aureon.autonomous.aureon_data_ocean"),
        "druidic-live-calibration": (
            "python",
            "scripts.operations.run_live_druidic_calibration",
        ),
        "docker-runtime": ("native", "Dockerfile"),
        "ephemeris-pipeline": ("native", "Dockerfile.ephemeris"),
        "flameborn-runtime": ("node", "flameborn:runtime"),
        "frontend-vite": ("node", "frontend:vite"),
        "hnc": ("python", "aureon.core.hnc_live_daemon"),
        "ignition": ("python", "scripts/aureon_ignition.py"),
        "linux-supervisor": ("native", "deploy/supervisord.linux.conf"),
        "local-gui": ("python", "aureon.operator.local_gui_organism"),
        "master-launcher": (
            "python",
            "aureon.autonomous.aureon_master_launcher",
        ),
        "mind-hub": (
            "python",
            "aureon.autonomous.aureon_mind_thought_action_hub",
        ),
        "operator": ("python", "aureon.operator.operator_server"),
        "operator-wsgi": ("python", "aureon.operator.wsgi"),
        "organism": ("python", "aureon.core.organism_daemon"),
        "organism-observer": (
            "python",
            "aureon.autonomous.aureon_organism_runtime_observer",
        ),
        "parallel-strategy-unity": (
            "python",
            "aureon.trading.parallel_strategy_unity",
        ),
        "production-supervisor": ("native", "production/supervisord.conf"),
        "queen-eternal-machine": (
            "python",
            "aureon.queen.queen_eternal_machine",
        ),
        "queen-web-dashboard": (
            "python",
            "aureon.queen.queen_web_dashboard",
        ),
        "power-redistribution-engine": (
            "python",
            "aureon.utils.aureon_power_redistribution_engine",
        ),
        "self-questioning": (
            "python",
            "aureon.autonomous.aureon_self_questioning_ai",
        ),
        "scorm-benchmark": (
            "python",
            "aureon.operator.scorm_cloud_runner",
        ),
        "autonomous-self-run": (
            "python",
            "aureon.autonomous.aureon_autonomous_self_run_loop",
        ),
        "unified-market-status": (
            "python",
            "aureon.exchanges.unified_market_status_server",
        ),
        "unified-market-trader": (
            "python",
            "aureon.exchanges.unified_market_trader",
        ),
        "website": ("python", "aureon.operator.website_operator"),
        "windows-wake": (
            "powershell",
            "scripts/launchers/AUREON_WAKE_UP_FULL_AUTONOMOUS.ps1",
        ),
        "ws-market-data-feeder": (
            "python",
            "aureon.data_feeds.ws_market_data_feeder",
        ),
    }
)


def _canonical_bytes(value: dict[str, object]) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _target_commitment(target_id: str, runtime_kind: str, entrypoint: str) -> str:
    return _sha256_bytes(
        _canonical_bytes(
            {
                "entrypoint": entrypoint,
                "runtime_kind": runtime_kind,
                "schema": "aureon.plumber.isolated-bootstrap-target.v05",
                "target_id": target_id,
            }
        )
    )


def _bounded_arguments(values: list[str]) -> tuple[str, ...]:
    if values[:1] == ["--"]:
        values = values[1:]
    if len(values) > _MAX_ARGUMENTS:
        raise ValueError("bounded_bootstrap_target_arguments_required")
    aggregate = 0
    for value in values:
        if type(value) is not str or "\x00" in value:
            raise ValueError("exact_bootstrap_target_argument_required")
        if value == "--root" or value.startswith("--root="):
            raise ValueError("caller_controlled_bootstrap_root_forbidden")
        size = len(value.encode("utf-8"))
        if size > _MAX_ARGUMENT_BYTES:
            raise ValueError("bounded_bootstrap_target_argument_required")
        aggregate += size
    if aggregate > _MAX_ARGUMENT_AGGREGATE_BYTES:
        raise ValueError("bounded_bootstrap_target_argument_aggregate_required")
    return tuple(values)


def _repo_root() -> Path:
    script = Path(__file__).resolve()
    root = script.parents[2]
    expected = (root / "scripts" / "bootstrap" / "protected_bootstrap_v05.py").resolve()
    if script != expected or not expected.is_file():
        raise ValueError("fixed_bootstrap_path_invalid")
    return root


def _bootstrap_source_sha256() -> str:
    try:
        return _sha256_bytes(Path(__file__).resolve().read_bytes())
    except OSError:
        return _ZERO_SHA256


def _runtime_guard_source_sha256(root: Path) -> str:
    path = root / "aureon" / "plumber" / "runtime_guard_v04.py"
    try:
        return _sha256_bytes(path.read_bytes())
    except OSError:
        return _ZERO_SHA256


def _safe_source_path(root: Path, relative: str) -> Path:
    candidate_relative = Path(relative.replace("\\", "/"))
    if (
        not relative
        or candidate_relative.is_absolute()
        or any(part in {"", ".", ".."} for part in candidate_relative.parts)
    ):
        raise ValueError("bounded_bootstrap_source_path_required")
    root_resolved = root.resolve(strict=True)
    candidate = root_resolved.joinpath(candidate_relative)
    current = root_resolved
    for part in candidate_relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("bootstrap_source_symlink_forbidden")
    resolved = candidate.resolve(strict=True)
    try:
        resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise ValueError("bootstrap_source_path_escape") from exc
    if not resolved.is_file():
        raise ValueError("bootstrap_source_file_required")
    return resolved


def _stable_file_measurement(path: Path) -> tuple[str, int]:
    before = path.stat()
    if before.st_size < 0 or before.st_size > _MAX_SINGLE_SOURCE_BYTES:
        raise ValueError("bounded_bootstrap_source_file_required")
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > _MAX_SINGLE_SOURCE_BYTES:
                raise ValueError("bounded_bootstrap_source_file_required")
            digest.update(chunk)
    after = path.stat()
    identity_before = (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
    )
    identity_after = (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    )
    if identity_before != identity_after or size != after.st_size:
        raise ValueError("bootstrap_source_changed_during_measurement")
    return digest.hexdigest(), size


def _source_files(root: Path) -> tuple[tuple[str, Path], ...]:
    root_resolved = root.resolve(strict=True)
    relative_paths = set(_PROTECTION_SOURCE_PATHS)
    for runtime_kind, entrypoint in _TARGETS.values():
        relative_paths.add(
            _target_source_relative(runtime_kind, entrypoint, root_resolved)
        )
    if len(relative_paths) > _MAX_SOURCE_FILES:
        raise ValueError("bootstrap_source_file_capacity_exceeded")
    return tuple(
        (relative, _safe_source_path(root_resolved, relative))
        for relative in sorted(relative_paths, key=lambda item: item.encode("utf-8"))
    )


def _measure_source_scope(root: Path) -> tuple[dict[str, object], dict[str, tuple[str, int]]]:
    files = _source_files(root)
    aggregate = hashlib.sha256()
    aggregate.update((_SOURCE_SCOPE_SCHEMA + "\n").encode("ascii"))
    measurements: dict[str, tuple[str, int]] = {}
    total_bytes = 0
    for relative, path in files:
        digest, size = _stable_file_measurement(path)
        total_bytes += size
        if total_bytes > _MAX_SOURCE_BYTES:
            raise ValueError("bootstrap_source_byte_capacity_exceeded")
        measurements[relative] = (digest, size)
        aggregate.update(
            _canonical_bytes(
                {
                    "path": relative,
                    "sha256": digest,
                    "size": size,
                }
            )
        )
        aggregate.update(b"\n")
    if not measurements:
        raise ValueError("bootstrap_source_inventory_required")
    return (
        {
            "schema": _SOURCE_SCOPE_SCHEMA,
            "sha256": aggregate.hexdigest(),
            "file_count": len(measurements),
            "total_bytes": total_bytes,
        },
        measurements,
    )


def _target_source_relative(runtime_kind: str, entrypoint: str, root: Path) -> str:
    if runtime_kind == "node":
        relative = _NODE_TARGET_SOURCES.get(entrypoint)
        if relative is None:
            raise ValueError("fixed_node_target_source_required")
        return relative
    if runtime_kind in {"native", "powershell", "shell"}:
        return entrypoint.replace("\\", "/")
    if runtime_kind != "python":
        raise ValueError("recognized_bootstrap_runtime_kind_required")
    if entrypoint.casefold().endswith(".py") or "/" in entrypoint or "\\" in entrypoint:
        return entrypoint.replace("\\", "/")
    base = entrypoint.replace(".", "/")
    candidates = (f"{base}.py", f"{base}/__init__.py")
    present = [item for item in candidates if (root / item).is_file()]
    if len(present) != 1:
        raise ValueError("exact_python_target_source_required")
    return present[0]


def _receipt(
    *,
    target_id: str,
    arguments: tuple[str, ...],
    checked_at: float,
) -> dict[str, object]:
    root = _repo_root()
    target = _TARGETS.get(target_id)
    registered = target is not None
    runtime_kind = "" if target is None else target[0]
    entrypoint = "" if target is None else target[1]
    failures = {
        "durable_hnc_evidence",
        "full_os_protection",
        "native_outer_boundary",
        "runtime_guard_production_readiness",
    }
    if not registered:
        failures.add("fixed_bootstrap_target")
    if runtime_kind and runtime_kind != "python":
        failures.add(f"{runtime_kind}_outer_boundary")
    source_scope: dict[str, object] = {
        "schema": _SOURCE_SCOPE_SCHEMA,
        "sha256": _ZERO_SHA256,
        "file_count": 0,
        "total_bytes": 0,
    }
    source_scope_stable = False
    source_measurements: dict[str, tuple[str, int]] = {}
    try:
        first_scope, first_measurements = _measure_source_scope(root)
        second_scope, second_measurements = _measure_source_scope(root)
        source_scope_stable = (
            first_scope == second_scope
            and first_measurements == second_measurements
        )
        if not source_scope_stable:
            raise ValueError("bootstrap_source_scope_changed_during_measurement")
        source_scope = second_scope
        source_measurements = second_measurements
    except (OSError, ValueError):
        failures.add("source_scope_measurement")

    target_source_sha256 = _ZERO_SHA256
    target_source_size = 0
    target_source_measured = False
    target_source_in_scope = False
    if target is not None:
        try:
            target_relative = _target_source_relative(runtime_kind, entrypoint, root)
            target_path = _safe_source_path(root, target_relative)
            target_source_sha256, target_source_size = _stable_file_measurement(
                target_path
            )
            recorded = source_measurements.get(target_relative)
            target_source_in_scope = recorded == (
                target_source_sha256,
                target_source_size,
            )
            target_source_measured = target_source_in_scope
        except (OSError, ValueError):
            target_source_measured = False
    if not target_source_measured:
        failures.add("target_source_measurement")

    argument_policy_attested = len(arguments) == 0
    if not argument_policy_attested:
        failures.add("target_argument_policy")
    causal: dict[str, object] = {
        "schema": SCHEMA,
        "decision": "HOLD",
        "reason": "complete_isolated_protected_bootstrap_required",
        "failed_checks": sorted(failures),
        "target_id": target_id,
        "target_registered": registered,
        "target_runtime_kind": runtime_kind,
        "target_entrypoint_commitment": (
            _ZERO_SHA256
            if target is None
            else _target_commitment(target_id, runtime_kind, entrypoint)
        ),
        "target_argument_count": len(arguments),
        "target_arguments_sha256": _sha256_bytes(
            json.dumps(list(arguments), separators=(",", ":"), ensure_ascii=True).encode(
                "utf-8"
            )
        ),
        "repo_root_sha256": _sha256_bytes(str(root).casefold().encode("utf-8")),
        "repo_root_derived_from_bootstrap_path": True,
        "bootstrap_path_bound": True,
        "bootstrap_source_sha256": _bootstrap_source_sha256(),
        "caller_controlled_root_accepted": False,
        "source_scope_schema": source_scope["schema"],
        "source_scope_sha256": source_scope["sha256"],
        "source_scope_file_count": source_scope["file_count"],
        "source_scope_total_bytes": source_scope["total_bytes"],
        "source_scope_measured": source_scope_stable,
        "source_scope_stable": source_scope_stable,
        "target_source_sha256": target_source_sha256,
        "target_source_size": target_source_size,
        "target_source_measured": target_source_measured,
        "target_source_in_source_scope": target_source_in_scope,
        "target_argument_policy": "empty-arguments-v1",
        "target_argument_policy_attested": argument_policy_attested,
        "runtime_guard_source_sha256": _runtime_guard_source_sha256(root),
        "runtime_guard_production_ready": False,
        "full_os_protection_evaluated": False,
        "durable_hnc_evidence_attested": False,
        "magic_star_durable_custody_attested": False,
        "external_head_anchor_attested": False,
        "target_imported": False,
        "target_called": False,
        "child_process_started": False,
        "bootstrap_subprocess_started": False,
        "git_invoked": False,
        "network_accessed": False,
        "file_written": False,
        "hnc_denial_recorded": False,
        "durable_hnc_denial_recorded": False,
        "process_start_authorized": False,
        "action_eligible": False,
        "economic_eligible": False,
        "operational_eligible": False,
        "production_ready": False,
        "checked_at": checked_at,
    }
    return {
        **causal,
        "receipt_id": f"bootstrap:isolated-v05:{_sha256_bytes(_canonical_bytes(causal))}",
    }


def _invalid_receipt(*, checked_at: float) -> dict[str, object]:
    causal: dict[str, object] = {
        "schema": SCHEMA,
        "decision": "HOLD",
        "reason": "exact_isolated_bootstrap_request_required",
        "failed_checks": ["bootstrap_request"],
        "target_id": "",
        "target_imported": False,
        "target_called": False,
        "child_process_started": False,
        "bootstrap_subprocess_started": False,
        "git_invoked": False,
        "network_accessed": False,
        "file_written": False,
        "process_start_authorized": False,
        "production_ready": False,
        "checked_at": checked_at,
    }
    return {
        **causal,
        "receipt_id": f"bootstrap:isolated-v05:{_sha256_bytes(_canonical_bytes(causal))}",
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-id", required=True)
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("target_arguments", nargs=argparse.REMAINDER)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    checked_at = time.time()
    try:
        if type(args.target_id) is not str or _TARGET_RE.fullmatch(args.target_id) is None:
            raise ValueError("exact_bootstrap_target_id_required")
        arguments = _bounded_arguments(args.target_arguments)
        receipt = _receipt(
            target_id=args.target_id,
            arguments=arguments,
            checked_at=checked_at,
        )
        exit_code = 1
    except (OSError, TypeError, ValueError):
        receipt = _invalid_receipt(checked_at=checked_at)
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


if __name__ == "__main__":
    raise SystemExit(main())
