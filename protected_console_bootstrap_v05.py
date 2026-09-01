"""Dependency-free, fixed-target HOLD boundary for installed console scripts.

This top-level module deliberately lives outside :mod:`aureon`.  Loading any
declared console entry point therefore imports no Aureon package code before a
future native/runtime guard exists.  Each exported function is permanently
bound to one registered target and can only emit a commitment-only HOLD
receipt.  It never imports or calls a target, starts a child, accesses a
network, writes a file, invokes Git, or accepts a caller-controlled root.

The fixed target registry and argument bounds intentionally mirror
``scripts/bootstrap/protected_bootstrap_v05.py``.  They remain separate so the
direct ``python -I -S -B`` path stays self-contained; focused parity tests keep
the duplicated security contract synchronized.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path
from types import MappingProxyType
from typing import Final

SCHEMA: Final = "aureon.plumber.inert-console-bootstrap.v05"
TARGET_SCHEMA: Final = "aureon.plumber.isolated-bootstrap-target.v05"
MODULE_NAME: Final = "protected_console_bootstrap_v05"
_MAX_ARGUMENTS: Final = 64
_MAX_ARGUMENT_BYTES: Final = 4096
_MAX_ARGUMENT_AGGREGATE_BYTES: Final = 64 * 1024
_ZERO_SHA256: Final = "0" * 64

_TARGETS: Final = MappingProxyType(
    {
        "hnc": ("python", "aureon.core.hnc_live_daemon"),
        "local-gui": ("python", "aureon.operator.local_gui_organism"),
        "operator": ("python", "aureon.operator.operator_server"),
        "organism": ("python", "aureon.core.organism_daemon"),
        "website": ("python", "aureon.operator.website_operator"),
    }
)

_FAILED_CHECKS: Final = (
    "durable_hnc_evidence",
    "full_os_protection",
    "native_outer_boundary",
    "runtime_guard_production_readiness",
    "source_scope_measurement",
    "target_argument_policy",
    "target_source_measurement",
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
                "schema": TARGET_SCHEMA,
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


def _bootstrap_root() -> Path:
    module_path = Path(__file__).resolve(strict=True)
    if module_path.name != f"{MODULE_NAME}.py":
        raise ValueError("fixed_console_bootstrap_module_path_invalid")
    return module_path.parent


def _receipt(
    *,
    target_id: str,
    arguments: tuple[str, ...],
    checked_at: float,
) -> dict[str, object]:
    target = _TARGETS.get(target_id)
    if target is None:
        raise ValueError("fixed_console_bootstrap_target_required")
    root = _bootstrap_root()
    runtime_kind, entrypoint = target
    causal: dict[str, object] = {
        "schema": SCHEMA,
        "decision": "HOLD",
        "reason": "complete_isolated_protected_bootstrap_required",
        "failed_checks": list(_FAILED_CHECKS),
        "target_id": target_id,
        "target_registered": True,
        "target_runtime_kind": runtime_kind,
        "target_entrypoint_commitment": _target_commitment(
            target_id,
            runtime_kind,
            entrypoint,
        ),
        "target_argument_count": len(arguments),
        "target_arguments_sha256": _sha256_bytes(
            json.dumps(
                list(arguments),
                separators=(",", ":"),
                ensure_ascii=True,
            ).encode("utf-8")
        ),
        "bootstrap_module": MODULE_NAME,
        "bootstrap_root_sha256": _sha256_bytes(
            str(root).casefold().encode("utf-8")
        ),
        "bootstrap_root_derived_from_module_path": True,
        "caller_controlled_root_accepted": False,
        "source_scope_measured": False,
        "target_source_measured": False,
        "target_argument_policy_attested": False,
        "runtime_guard_source_sha256": _ZERO_SHA256,
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
        "receipt_id": f"bootstrap:console-v05:{_sha256_bytes(_canonical_bytes(causal))}",
    }


def _invalid_receipt(*, target_id: str, checked_at: float) -> dict[str, object]:
    target = _TARGETS.get(target_id)
    causal: dict[str, object] = {
        "schema": SCHEMA,
        "decision": "HOLD",
        "reason": "exact_isolated_bootstrap_request_required",
        "failed_checks": ["bootstrap_request"],
        "target_id": target_id,
        "target_registered": target is not None,
        "target_runtime_kind": "" if target is None else target[0],
        "target_entrypoint_commitment": (
            _ZERO_SHA256
            if target is None
            else _target_commitment(target_id, target[0], target[1])
        ),
        "bootstrap_module": MODULE_NAME,
        "bootstrap_root_sha256": _ZERO_SHA256,
        "bootstrap_root_derived_from_module_path": False,
        "caller_controlled_root_accepted": False,
        "source_scope_measured": False,
        "target_source_measured": False,
        "target_argument_policy_attested": False,
        "runtime_guard_source_sha256": _ZERO_SHA256,
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
        "receipt_id": f"bootstrap:console-v05:{_sha256_bytes(_canonical_bytes(causal))}",
    }


def _fixed_target_main(target_id: str) -> int:
    checked_at = time.time()
    try:
        arguments = _bounded_arguments(sys.argv[1:])
        receipt = _receipt(
            target_id=target_id,
            arguments=arguments,
            checked_at=checked_at,
        )
        exit_code = 1
    except (OSError, RuntimeError, TypeError, ValueError):
        receipt = _invalid_receipt(target_id=target_id, checked_at=checked_at)
        exit_code = 2
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
    return exit_code


def operator_main() -> int:
    return _fixed_target_main("operator")


def organism_main() -> int:
    return _fixed_target_main("organism")


def hnc_main() -> int:
    return _fixed_target_main("hnc")


def local_gui_main() -> int:
    return _fixed_target_main("local-gui")


def website_main() -> int:
    return _fixed_target_main("website")


__all__ = [
    "hnc_main",
    "local_gui_main",
    "operator_main",
    "organism_main",
    "website_main",
]
