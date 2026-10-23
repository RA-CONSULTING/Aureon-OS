"""One explicitly selected registry organ per systemd cgroup, under proven HOLD."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import threading

from cloud_http_runtime import (
    CLOUD_CREDENTIAL_ISOLATION_ENV,
    CLOUD_EXCHANGE_CREDENTIALS_PINNED_ENV,
    CLOUD_EXCHANGE_CREDENTIAL_ENV_VARS,
    CLOUD_EXCHANGE_MODE_ENV_VARS,
    CLOUD_ENV_LOADER_CONTROL_VARS,
    CLOUD_OPERATOR_SAFE_MODE_ENV,
    CloudHTTPError,
    OWNER_PROVIDER_KEYS,
    PINNED_PROVIDER_ENV_VARS_ENV,
    install_cloud_environment_guard,
    load_cloud_owner_provider_config,
    validate_owner_provider_config,
)
from release_update import (
    HOLDS,
    PROVIDER_CONFIG_ORGANS,
    READ_ORGANS,
    RETAIN_ONLY,
    ReleaseError,
)


def configure(registry, gate, name: str, environment: dict[str, str],
              provider_config: dict[str, str] | None = None) -> None:
    if name not in READ_ORGANS | RETAIN_ONLY or name not in registry.ORGANS:
        raise ReleaseError("organ_outside_selected_cloud_profile")
    if any(environment.get(key) != value for key, value in HOLDS.items()):
        raise ReleaseError("all_cloud_action_holds_required")
    # Verify the actual gate implementation, not just the environment label.
    if gate.release_authorized() or registry._release_granted():
        raise ReleaseError("restored_approval_can_release_host")
    for action in ("trading_execution:execute_live_trades", "external_communication:send_message",
                   "process_control:execute", "code_generation:execute_code", "network_access:scan_network"):
        verdict = gate._check_verdict(action)
        if verdict.get("allowed") is not False or verdict.get("deployment_hold") is not True:
            raise ReleaseError("deployment_hold_contract_not_enforced")
    if name in PROVIDER_CONFIG_ORGANS:
        if provider_config is None:
            raise ReleaseError("owner_provider_config_required_for_selected_organ")
        try:
            provider_config = validate_owner_provider_config(
                json.dumps(provider_config, sort_keys=True, separators=(",", ":")).encode("utf-8")
            )
        except CloudHTTPError as exc:
            raise ReleaseError(str(exc)) from None
        except (TypeError, ValueError):
            raise ReleaseError("cloud_owner_provider_payload_invalid") from None
    elif provider_config is not None:
        raise ReleaseError("owner_provider_config_outside_selected_organ")
    original = registry.ORGANS[name]
    # Change only this runner's in-memory selected launch specification. Nothing
    # is persisted to approvals, dormancy state, source or any other organ spec.
    child_environment = dict(original.get("env") or environment)
    # Values from a service manager, shell profile or restored dotenv can never
    # bypass the pinned Secret Manager bundle or reach an unselected organ.
    for key in (
        set(OWNER_PROVIDER_KEYS)
        | set(CLOUD_EXCHANGE_CREDENTIAL_ENV_VARS)
        | set(CLOUD_EXCHANGE_MODE_ENV_VARS)
        | set(CLOUD_ENV_LOADER_CONTROL_VARS)
    ):
        child_environment.pop(key, None)
    child_environment.update(CLOUD_OPERATOR_SAFE_MODE_ENV)
    child_environment[CLOUD_CREDENTIAL_ISOLATION_ENV] = "1"
    child_environment[CLOUD_EXCHANGE_CREDENTIALS_PINNED_ENV] = "1"
    child_environment["PYTHON_DOTENV_DISABLED"] = "1"
    boundary_path = str(Path(__file__).resolve().parent)
    python_path = child_environment.get("PYTHONPATH", "")
    path_parts = [part for part in python_path.split(os.pathsep) if part]
    child_environment["PYTHONPATH"] = os.pathsep.join(
        [boundary_path, *(part for part in path_parts if part != boundary_path)]
    )
    if provider_config is not None:
        child_environment.update(provider_config)
        child_environment[PINNED_PROVIDER_ENV_VARS_ENV] = ",".join(OWNER_PROVIDER_KEYS)
    child_environment.update(HOLDS)
    registry.ORGANS[name] = {**original, "env": child_environment}


def owner_provider_config(name: str, project: str, secret: str, version: str,
                          loader=load_cloud_owner_provider_config) -> dict[str, str] | None:
    supplied = bool(project or secret or version)
    if name not in PROVIDER_CONFIG_ORGANS:
        if supplied:
            raise ReleaseError("owner_provider_reference_outside_selected_organ")
        return None
    if not (project and secret and version):
        raise ReleaseError("owner_provider_reference_required_for_selected_organ")
    try:
        return loader(project, secret, version)
    except CloudHTTPError as exc:
        raise ReleaseError(str(exc)) from None
    except Exception:
        # Loader internals and upstream response details never reach journald.
        raise ReleaseError("cloud_owner_provider_load_failed") from None


def cgroup(pid: int) -> bytes:
    return Path(f"/proc/{pid}/cgroup").read_bytes()


def start_owned(registry, name, process_factory, cgroup_reader=cgroup):
    result = registry.start(name)
    if result.get("state") != "started" or result.get("ok") is False:
        # Existing or dormant owners are never adopted or terminated by this unit.
        raise ReleaseError("registry_did_not_start_new_owned_process")
    process = process_factory(result["pid"])
    created = process.create_time()
    if cgroup_reader(process.pid) != cgroup_reader(os.getpid()):
        raise ReleaseError("started_process_not_in_owned_systemd_cgroup")
    return process, created


def stop_owned(registry, name, process, created, cgroup_reader=cgroup):
    # Serialize the owner comparison with the registry's existing launch lock.
    with registry._registry_lock() as held:
        if not held:
            return
        entry = registry._load_registry().get("organs", {}).get(name, {})
        if entry.get("pid") != process.pid:
            return
        try:
            same_process = process.is_running() and process.create_time() == created
            same_group = cgroup_reader(process.pid) == cgroup_reader(os.getpid())
        except Exception:
            return
        if same_process and same_group:
            registry.stop(name)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name")
    parser.add_argument("--project", default="")
    parser.add_argument("--provider-secret", default="")
    parser.add_argument("--provider-secret-version", default="")
    args = parser.parse_args(argv)
    if os.name != "posix":
        raise ReleaseError("linux_selected_organ_required")
    name = args.name
    if any(os.environ.get(key) != value for key, value in HOLDS.items()):
        raise ReleaseError("all_cloud_action_holds_required")
    # Direct invocations receive the same permanent boundary as systemd's
    # early sitecustomize hook before importing the registry/application graph.
    install_cloud_environment_guard()
    provider_config = owner_provider_config(
        name, args.project, args.provider_secret, args.provider_secret_version
    )
    import psutil
    from aureon_fusion import capability_gate as gate, organ_registry as registry
    configure(registry, gate, name, dict(os.environ), provider_config)
    stopped = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stopped.set())
    process, created = start_owned(registry, name, psutil.Process)
    print("Owned registry process started under cloud deployment HOLD", flush=True)
    try:
        while not stopped.wait(3):
            if not process.is_running() or process.create_time() != created or process.status() == psutil.STATUS_ZOMBIE:
                return 1
    finally:
        stop_owned(registry, name, process, created)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReleaseError as error:
        print(str(error), flush=True)
        raise SystemExit(2)
