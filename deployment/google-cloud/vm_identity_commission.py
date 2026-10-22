"""Plan or apply the existing Aureon VM token-broker identity attachment.

The default command is read-only. ``apply`` requires the exact provider-bound
plan hash and an explicit interruption acknowledgement, then performs only a
stop, service-account replacement, start and exact provider readback.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
from typing import Any, Mapping, Protocol


SCHEMA = "aureon.gcp.vm-identity-commission-plan.v1"
RECEIPT_SCHEMA = "aureon.gcp.vm-identity-commission-receipt.v1"
PROGRESS_SCHEMA = "aureon.gcp.vm-identity-commission-progress.v1"
CONTRACT_SCHEMA = "aureon.cloud-trading-authority-resources.v3"
_HEX64 = re.compile(r"[0-9a-f]{64}")
_OPERATIONS = ("stop", "set-service-account", "start")
_TRANSIENT_STATUSES = {"PROVISIONING", "STAGING", "STOPPING"}
_MAX_OPERATION_ATTEMPTS = 2
_MAX_READBACK_POLLS = 6


class IdentityCommissionError(RuntimeError):
    """Stable identity commissioning failure without provider response data."""


class Runner(Protocol):
    def describe(self, instance: str, zone: str) -> Mapping[str, Any]: ...
    def apply(self, *args: str) -> None: ...


class Gcloud:
    def __init__(self, executable: str, project: str):
        self.executable = executable
        self.project = project

    def _run(self, args: list[str], *, expect_json: bool) -> Any:
        try:
            result = subprocess.run(
                [
                    self.executable,
                    *args,
                    "--project=" + self.project,
                    "--quiet",
                    *( ["--format=json"] if expect_json else [] ),
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=900,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise IdentityCommissionError("gcloud_identity_operation_failed") from exc
        if result.returncode:
            raise IdentityCommissionError("gcloud_identity_operation_failed")
        if not expect_json:
            return None
        try:
            return json.loads(result.stdout)
        except (ValueError, TypeError, UnicodeError) as exc:
            raise IdentityCommissionError("vm_provider_readback_invalid") from exc

    def describe(self, instance: str, zone: str) -> Mapping[str, Any]:
        value = self._run(
            ["compute", "instances", "describe", instance, "--zone=" + zone],
            expect_json=True,
        )
        if not isinstance(value, Mapping):
            raise IdentityCommissionError("vm_provider_readback_invalid")
        return value

    def apply(self, *args: str) -> None:
        self._run(list(args), expect_json=False)


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("ascii")


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_contract(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_bytes())
    except (OSError, ValueError, TypeError, UnicodeError) as exc:
        raise IdentityCommissionError("resource_contract_invalid") from exc
    if not isinstance(value, dict) or value.get("schema") != CONTRACT_SCHEMA:
        raise IdentityCommissionError("resource_contract_invalid")
    return value


def snapshot(contract: Mapping[str, Any], value: Mapping[str, Any]) -> dict[str, Any]:
    vm = contract["vm_workload_identity"]
    accounts = value.get("serviceAccounts")
    if not isinstance(accounts, list) or len(accounts) != 1:
        raise IdentityCommissionError("vm_provider_readback_invalid")
    account = accounts[0]
    if not isinstance(account, Mapping):
        raise IdentityCommissionError("vm_provider_readback_invalid")
    scopes = account.get("scopes")
    if not isinstance(scopes, list) or any(not isinstance(item, str) for item in scopes):
        raise IdentityCommissionError("vm_provider_readback_invalid")
    machine = str(value.get("machineType") or "").rsplit("/", 1)[-1]
    result = {
        "name": value.get("name"),
        "zone": str(value.get("zone") or "").rsplit("/", 1)[-1],
        "status": value.get("status"),
        "machine_type": machine,
        "service_account": account.get("email"),
        "scopes": sorted(scopes),
    }
    if (
        result["name"] != vm["instance"]
        or result["zone"] != contract["zone"]
        or not result["machine_type"]
        or not isinstance(result["service_account"], str)
    ):
        raise IdentityCommissionError("vm_provider_readback_invalid")
    return result


def build_plan(contract: Mapping[str, Any], current: Mapping[str, Any]) -> dict[str, Any]:
    vm = contract["vm_workload_identity"]
    desired = {
        "service_account": vm["attached_service_account"],
        "scopes": sorted(vm["attached_oauth_scopes"]),
    }
    return {
        "schema": SCHEMA,
        "project": contract["project"],
        "zone": contract["zone"],
        "instance": vm["instance"],
        "current": dict(current),
        "desired": desired,
        "identity_change_required": (
            current.get("service_account") != desired["service_account"]
            or current.get("scopes") != desired["scopes"]
        ),
        "operations": ["stop", "set-service-account", "start"],
        "data_plane_roles_granted": False,
        "release_authority": False,
        "mutation_authority": False,
    }


def write_json(path: Path, value: Mapping[str, Any]) -> str:
    if not path.is_absolute() or path.is_symlink():
        raise IdentityCommissionError("absolute_receipt_path_required")
    raw = json.dumps(dict(value), sort_keys=True, indent=2).encode("ascii") + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".vm-identity-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
        if os.name == "posix":
            directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
    return sha256(canonical(value))


def load_commission_plan(
    path: Path | None, contract: Mapping[str, Any], ack: str | None
) -> tuple[dict[str, Any], str]:
    """Load an acknowledged plan without requiring its old provider state now."""

    if path is None or not path.is_absolute() or not path.is_file() or path.is_symlink():
        raise IdentityCommissionError("absolute_identity_plan_required")
    try:
        value = json.loads(path.read_bytes())
    except (OSError, ValueError, TypeError, UnicodeError) as exc:
        raise IdentityCommissionError("identity_plan_invalid") from exc
    if not isinstance(value, dict) or not isinstance(value.get("current"), Mapping):
        raise IdentityCommissionError("identity_plan_invalid")
    current = value["current"]
    vm = contract["vm_workload_identity"]
    scopes = current.get("scopes")
    if (
        set(current)
        != {"name", "zone", "status", "machine_type", "service_account", "scopes"}
        or current.get("name") != vm["instance"]
        or current.get("zone") != contract["zone"]
        or current.get("status") != "RUNNING"
        or not isinstance(current.get("machine_type"), str)
        or not current["machine_type"]
        or not isinstance(current.get("service_account"), str)
        or not current["service_account"]
        or not isinstance(scopes, list)
        or any(not isinstance(item, str) or not item for item in scopes)
        or scopes != sorted(set(scopes))
    ):
        raise IdentityCommissionError("identity_plan_invalid")
    expected = build_plan(contract, current)
    if value != expected:
        raise IdentityCommissionError("identity_plan_invalid")
    plan_hash = sha256(canonical(value))
    if _HEX64.fullmatch(ack or "") is None or ack != plan_hash:
        raise IdentityCommissionError("exact_identity_plan_acknowledgement_required")
    return value, plan_hash


def progress_path(receipt: Path) -> Path:
    suffix = receipt.suffix or ".json"
    return receipt.with_name(receipt.stem + ".progress" + suffix)


def _identity_matches(value: Mapping[str, Any], identity: Mapping[str, Any]) -> bool:
    return (
        value.get("service_account") == identity.get("service_account")
        and value.get("scopes") == sorted(identity.get("scopes", []))
    )


def _provider_phase(plan: Mapping[str, Any], observed: Mapping[str, Any]) -> str:
    if observed.get("machine_type") != plan["current"].get("machine_type"):
        raise IdentityCommissionError("vm_identity_provider_state_conflict")
    original = {
        "service_account": plan["current"]["service_account"],
        "scopes": plan["current"]["scopes"],
    }
    desired = plan["desired"]
    if _identity_matches(observed, original):
        identity = "original"
    elif _identity_matches(observed, desired):
        identity = "desired"
    else:
        raise IdentityCommissionError("vm_identity_provider_state_conflict")
    status = observed.get("status")
    if status not in {"RUNNING", "TERMINATED", *_TRANSIENT_STATUSES}:
        raise IdentityCommissionError("vm_identity_provider_status_unsupported")
    return identity + ":" + str(status).lower()


def _completed_operations(phase: str) -> list[str]:
    if phase in {
        "original:running",
        "original:provisioning",
        "original:staging",
        "original:stopping",
    }:
        return []
    if phase == "original:terminated":
        return ["stop"]
    if phase in {
        "desired:terminated",
        "desired:stopping",
        "desired:provisioning",
        "desired:staging",
    }:
        return ["stop", "set-service-account"]
    if phase == "desired:running":
        return list(_OPERATIONS)
    raise IdentityCommissionError("vm_identity_provider_state_conflict")


def _load_progress_history(
    path: Path, contract: Mapping[str, Any], plan_hash: str
) -> dict[str, Any]:
    result = {
        "attempted_operations": [],
        "uncertain_operations": [],
        "recovery_operations": [],
        "resume_count": 0,
    }
    if not path.exists():
        return result
    if not path.is_file() or path.is_symlink():
        raise IdentityCommissionError("identity_progress_receipt_invalid")
    try:
        value = json.loads(path.read_bytes())
    except (OSError, ValueError, TypeError, UnicodeError) as exc:
        raise IdentityCommissionError("identity_progress_receipt_invalid") from exc
    if not isinstance(value, Mapping):
        raise IdentityCommissionError("identity_progress_receipt_invalid")
    vm = contract["vm_workload_identity"]
    attempts = value.get("attempted_operations")
    uncertain = value.get("uncertain_operations")
    recoveries = value.get("recovery_operations")
    if (
        value.get("schema") != PROGRESS_SCHEMA
        or value.get("project") != contract["project"]
        or value.get("zone") != contract["zone"]
        or value.get("instance") != vm["instance"]
        or value.get("plan_sha256") != plan_hash
        or not isinstance(attempts, list)
        or any(item not in _OPERATIONS for item in attempts)
        or not isinstance(uncertain, list)
        or any(item not in _OPERATIONS for item in uncertain)
        or not isinstance(recoveries, list)
        or any(item != "start" for item in recoveries)
        or not isinstance(value.get("resume_count"), int)
        or isinstance(value.get("resume_count"), bool)
        or value.get("resume_count", -1) < 0
    ):
        raise IdentityCommissionError("identity_progress_receipt_invalid")
    result["attempted_operations"] = list(attempts)
    result["uncertain_operations"] = list(uncertain)
    result["recovery_operations"] = list(recoveries)
    result["resume_count"] = value["resume_count"] + 1
    return result


def _write_progress(
    path: Path,
    contract: Mapping[str, Any],
    plan_hash: str,
    history: Mapping[str, Any],
    *,
    status: str,
    phase: str,
    completed: list[str],
    observed: Mapping[str, Any] | None,
    error_code: str | None = None,
) -> str:
    vm = contract["vm_workload_identity"]
    desired = {
        "service_account": vm["attached_service_account"],
        "scopes": sorted(vm["attached_oauth_scopes"]),
    }
    provider_readback = dict(observed) if observed is not None else None
    value = {
        "schema": PROGRESS_SCHEMA,
        "status": status,
        "phase": phase,
        "recorded_at": datetime.now(UTC).isoformat(),
        "project": contract["project"],
        "zone": contract["zone"],
        "instance": vm["instance"],
        "plan_sha256": plan_hash,
        "attempted_operations": list(history["attempted_operations"]),
        "uncertain_operations": list(history["uncertain_operations"]),
        "completed_operations": list(completed),
        "recovery_operations": list(history["recovery_operations"]),
        "resume_count": history["resume_count"],
        "provider_state_known": observed is not None,
        "provider_readback": provider_readback,
        "vm_running": observed.get("status") == "RUNNING" if observed else None,
        "desired_identity_observed": (
            _identity_matches(observed, desired)
            if observed is not None
            else False
        ),
        "last_error_code": error_code,
        "data_plane_roles_granted": False,
        "secret_values_recorded": False,
        "release_authority": False,
        "mutation_authority": False,
    }
    return write_json(path, value)


def _describe(contract: Mapping[str, Any], runner: Runner) -> dict[str, Any]:
    vm = contract["vm_workload_identity"]
    return snapshot(contract, runner.describe(vm["instance"], contract["zone"]))


def _operation_args(
    contract: Mapping[str, Any], operation: str
) -> tuple[str, ...]:
    vm = contract["vm_workload_identity"]
    prefix = ("compute", "instances", operation, vm["instance"], "--zone=" + contract["zone"])
    if operation != "set-service-account":
        return prefix
    return (
        *prefix,
        "--service-account=" + vm["attached_service_account"],
        "--scopes=" + ",".join(vm["attached_oauth_scopes"]),
    )


def _recover_running(
    contract: Mapping[str, Any],
    runner: Runner,
    plan: Mapping[str, Any],
    plan_hash: str,
    path: Path,
    history: dict[str, Any],
    observed: Mapping[str, Any] | None,
    *,
    error_code: str,
) -> dict[str, Any] | None:
    """Attempt one idempotent start and durably record whether recovery worked."""

    completed: list[str] = []
    if observed is not None:
        try:
            phase = _provider_phase(plan, observed)
            completed = _completed_operations(phase)
        except IdentityCommissionError:
            phase = "provider-state-conflict"
        if observed.get("status") == "RUNNING":
            _write_progress(
                path,
                contract,
                plan_hash,
                history,
                status="recovered_running",
                phase=phase,
                completed=completed,
                observed=observed,
                error_code=error_code,
            )
            return dict(observed)
    history["recovery_operations"].append("start")
    _write_progress(
        path,
        contract,
        plan_hash,
        history,
        status="recovery_in_progress",
        phase="recovery_start_requested",
        completed=completed,
        observed=observed,
        error_code=error_code,
    )
    try:
        runner.apply(*_operation_args(contract, "start"))
    except IdentityCommissionError:
        history["uncertain_operations"].append("start")
    try:
        recovered = _describe(contract, runner)
    except IdentityCommissionError:
        recovered = None
        recovered_phase = "provider-readback-unavailable"
    else:
        try:
            recovered_phase = _provider_phase(plan, recovered)
            completed = _completed_operations(recovered_phase)
        except IdentityCommissionError:
            recovered_phase = "provider-state-conflict"
    recovered_running = recovered is not None and recovered.get("status") == "RUNNING"
    _write_progress(
        path,
        contract,
        plan_hash,
        history,
        status="recovered_running" if recovered_running else "recovery_required",
        phase=recovered_phase,
        completed=completed,
        observed=recovered,
        error_code=error_code,
    )
    return recovered


def apply_identity_resumable(
    contract: Mapping[str, Any],
    runner: Runner,
    plan: Mapping[str, Any],
    plan_hash: str,
    receipt: Path,
    *,
    sleeper=time.sleep,
) -> tuple[list[str], dict[str, Any]]:
    """Resume the acknowledged identity transaction solely from provider state."""

    path = progress_path(receipt)
    history = _load_progress_history(path, contract, plan_hash)
    try:
        observed = _describe(contract, runner)
    except IdentityCommissionError as exc:
        _write_progress(
            path,
            contract,
            plan_hash,
            history,
            status="recovery_required",
            phase="preflight_provider_readback_failed",
            completed=[],
            observed=None,
            error_code=str(exc),
        )
        raise
    try:
        phase = _provider_phase(plan, observed)
    except IdentityCommissionError as exc:
        _write_progress(
            path,
            contract,
            plan_hash,
            history,
            status="recovery_required",
            phase="preflight_provider_state_conflict",
            completed=[],
            observed=observed,
            error_code=str(exc),
        )
        raise

    if not plan["identity_change_required"]:
        if observed != plan["current"]:
            _write_progress(
                path,
                contract,
                plan_hash,
                history,
                status="recovery_required",
                phase=phase,
                completed=[],
                observed=observed,
                error_code="identity_noop_provider_state_changed",
            )
            raise IdentityCommissionError("identity_noop_provider_state_changed")
        _write_progress(
            path,
            contract,
            plan_hash,
            history,
            status="passed",
            phase="complete",
            completed=[],
            observed=observed,
        )
        return [], observed

    _write_progress(
        path,
        contract,
        plan_hash,
        history,
        status="in_progress",
        phase=phase,
        completed=_completed_operations(phase),
        observed=observed,
    )
    attempts: dict[str, int] = {operation: 0 for operation in _OPERATIONS}
    transition_polls = 0
    for _step in range(24):
        phase = _provider_phase(plan, observed)
        completed = _completed_operations(phase)
        if phase == "desired:running":
            _write_progress(
                path,
                contract,
                plan_hash,
                history,
                status="passed",
                phase="complete",
                completed=list(_OPERATIONS),
                observed=observed,
            )
            return list(_OPERATIONS), observed
        if phase.rsplit(":", 1)[-1].upper() in _TRANSIENT_STATUSES:
            transition_polls += 1
            if transition_polls > _MAX_READBACK_POLLS:
                _write_progress(
                    path,
                    contract,
                    plan_hash,
                    history,
                    status="recovery_required",
                    phase=phase,
                    completed=completed,
                    observed=observed,
                    error_code="vm_identity_provider_transition_incomplete",
                )
                raise IdentityCommissionError(
                    "vm_identity_provider_transition_incomplete"
                )
            _write_progress(
                path,
                contract,
                plan_hash,
                history,
                status="in_progress",
                phase=phase,
                completed=completed,
                observed=observed,
            )
            sleeper(1)
            try:
                observed = _describe(contract, runner)
            except IdentityCommissionError as exc:
                recovered = _recover_running(
                    contract,
                    runner,
                    plan,
                    plan_hash,
                    path,
                    history,
                    None,
                    error_code=str(exc),
                )
                if recovered is not None:
                    try:
                        if _provider_phase(plan, recovered) == "desired:running":
                            observed = recovered
                            continue
                    except IdentityCommissionError:
                        pass
                if recovered is not None and recovered.get("status") == "RUNNING":
                    raise IdentityCommissionError(
                        "vm_identity_transition_readback_failed_vm_recovered_running"
                    ) from exc
                raise IdentityCommissionError(
                    "vm_identity_transition_readback_failed_recovery_required"
                ) from exc
            continue
        transition_polls = 0
        if phase == "original:running":
            operation = "stop"
        elif phase == "original:terminated":
            operation = "set-service-account"
        elif phase == "desired:terminated":
            operation = "start"
        else:
            raise IdentityCommissionError("vm_identity_provider_state_conflict")

        attempts[operation] += 1
        history["attempted_operations"].append(operation)
        _write_progress(
            path,
            contract,
            plan_hash,
            history,
            status="in_progress",
            phase=operation + "_requested",
            completed=completed,
            observed=observed,
        )
        operation_uncertain = False
        try:
            runner.apply(*_operation_args(contract, operation))
        except IdentityCommissionError:
            operation_uncertain = True
            history["uncertain_operations"].append(operation)
        try:
            next_observed = _describe(contract, runner)
        except IdentityCommissionError as exc:
            recovered = _recover_running(
                contract,
                runner,
                plan,
                plan_hash,
                path,
                history,
                None,
                error_code=str(exc),
            )
            if recovered is not None:
                try:
                    if _provider_phase(plan, recovered) == "desired:running":
                        observed = recovered
                        continue
                except IdentityCommissionError:
                    pass
            if recovered is not None and recovered.get("status") == "RUNNING":
                raise IdentityCommissionError(
                    "vm_identity_provider_readback_failed_vm_recovered_running"
                ) from exc
            raise IdentityCommissionError(
                "vm_identity_provider_readback_failed_recovery_required"
            ) from exc
        try:
            next_phase = _provider_phase(plan, next_observed)
        except IdentityCommissionError as exc:
            _write_progress(
                path,
                contract,
                plan_hash,
                history,
                status="recovery_required",
                phase="provider_state_conflict_after_" + operation,
                completed=completed,
                observed=next_observed,
                error_code=str(exc),
            )
            raise

        if next_phase != phase:
            observed = next_observed
            _write_progress(
                path,
                contract,
                plan_hash,
                history,
                status="in_progress",
                phase=next_phase,
                completed=_completed_operations(next_phase),
                observed=observed,
                error_code=(
                    "gcloud_identity_operation_failed_but_effect_observed"
                    if operation_uncertain
                    else None
                ),
            )
            continue
        if attempts[operation] < _MAX_OPERATION_ATTEMPTS:
            observed = next_observed
            continue

        error_code = "vm_identity_" + operation.replace("-", "_") + "_failed"
        recovered = _recover_running(
            contract,
            runner,
            plan,
            plan_hash,
            path,
            history,
            next_observed,
            error_code=error_code,
        )
        if recovered is not None and _provider_phase(plan, recovered) == "desired:running":
            observed = recovered
            continue
        if recovered is not None and recovered.get("status") == "RUNNING":
            raise IdentityCommissionError(error_code + "_vm_recovered_running")
        raise IdentityCommissionError(error_code + "_recovery_required")
    _write_progress(
        path,
        contract,
        plan_hash,
        history,
        status="recovery_required",
        phase=_provider_phase(plan, observed),
        completed=_completed_operations(_provider_phase(plan, observed)),
        observed=observed,
        error_code="vm_identity_commission_step_limit",
    )
    raise IdentityCommissionError("vm_identity_commission_step_limit")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "apply"), nargs="?", default="plan")
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--acknowledge-plan-sha256")
    parser.add_argument("--acknowledge-interruption")
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--gcloud", default="gcloud")
    args = parser.parse_args(argv)
    try:
        contract = load_contract(args.contract)
        vm = contract["vm_workload_identity"]
        runner = Gcloud(args.gcloud, contract["project"])
        if args.command == "plan":
            current = _describe(contract, runner)
            plan = build_plan(contract, current)
            plan_hash = write_json(args.receipt, plan)
            print(json.dumps({"schema": SCHEMA, "plan_sha256": plan_hash}, sort_keys=True))
            return 0
        if (
            args.plan is not None
            and args.receipt.is_absolute()
            and args.plan.resolve() == args.receipt.resolve()
        ):
            raise IdentityCommissionError("identity_plan_and_receipt_must_differ")
        plan, plan_hash = load_commission_plan(
            args.plan, contract, args.acknowledge_plan_sha256
        )
        if (
            plan["identity_change_required"]
            and args.acknowledge_interruption
            != "stop-set-service-account-start:" + vm["instance"]
        ):
            raise IdentityCommissionError("exact_vm_interruption_acknowledgement_required")
        operations, observed = apply_identity_resumable(
            contract,
            runner,
            plan,
            plan_hash,
            args.receipt,
        )
        if observed != {
            **plan["current"],
            "status": "RUNNING",
            "service_account": vm["attached_service_account"],
            "scopes": sorted(vm["attached_oauth_scopes"]),
        }:
            raise IdentityCommissionError("vm_identity_provider_readback_not_exact")
        receipt = {
            "schema": RECEIPT_SCHEMA,
            "status": "passed",
            "recorded_at": datetime.now(UTC).isoformat(),
            "project": contract["project"],
            "zone": contract["zone"],
            "instance": vm["instance"],
            "plan_sha256": plan_hash,
            "operations": operations,
            "provider_readback": observed,
            "data_plane_roles_granted": False,
            "secret_values_recorded": False,
            "release_authority": False,
            "mutation_authority": False,
        }
        write_json(args.receipt, receipt)
        print(json.dumps({"schema": RECEIPT_SCHEMA, "status": "passed"}, sort_keys=True))
        return 0
    except IdentityCommissionError as exc:
        progress = progress_path(args.receipt)
        if args.command == "apply" and progress.is_file() and not progress.is_symlink():
            try:
                progress_raw = progress.read_bytes()
                progress_value = json.loads(progress_raw)
                progress_status = progress_value.get("status")
            except (OSError, ValueError, TypeError, UnicodeError, AttributeError):
                progress_raw = b""
                progress_status = "recovery_required"
            result = {
                "schema": PROGRESS_SCHEMA,
                "status": progress_status,
                "error_code": str(exc),
                "progress_receipt": str(progress),
            }
            if progress_raw:
                result["progress_receipt_sha256"] = sha256(progress_raw)
            print(
                json.dumps(
                    result,
                    sort_keys=True,
                )
            )
        else:
            print(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
