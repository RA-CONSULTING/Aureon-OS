"""Provision the isolated Aureon VM with its exact runtime identity.

Run this from an authenticated Cloud Shell or workstation. The script creates
network primitives and the dedicated service-account identity, but deliberately
does not grant data-plane IAM roles. ``trading-control/resource_contract.json``
and its commissioning audit own those least-privilege grants.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import Any, Callable


PROJECT = "aureon-trading"
REGION = "europe-west1"
ZONE = "europe-west1-b"
VM = "aureon-sero-20260906"
MACHINE_TYPE = "e2-standard-8"
NETWORK = "aureon-sero-network"
SUBNET = "aureon-sero-europe-west1"
SERVICE_ACCOUNT_ID = "aureon-vm-token-broker"
SERVICE_ACCOUNT = f"{SERVICE_ACCOUNT_ID}@{PROJECT}.iam.gserviceaccount.com"
CLOUD_PLATFORM_SCOPE = "https://www.googleapis.com/auth/cloud-platform"
HERE = Path(__file__).resolve().parent


class ProvisionError(RuntimeError):
    """The existing resource differs from the reviewed VM contract."""


def gc(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["gcloud", *args, "--project=" + PROJECT, "--quiet"],
        check=check,
        text=True,
        capture_output=True,
    )


def exists(*args: str, runner: Callable[..., subprocess.CompletedProcess[str]] = gc) -> Any:
    result = runner(*args, "--format=json", check=False)
    if result.returncode == 0:
        return json.loads(result.stdout)
    if "not found" in result.stderr.lower() or "was not found" in result.stderr.lower():
        return None
    raise ProvisionError(result.stderr.strip() or "gcloud_describe_failed")


def validate_runtime_identity(instance: dict[str, Any]) -> None:
    accounts = instance.get("serviceAccounts")
    if not isinstance(accounts, list) or len(accounts) != 1:
        raise ProvisionError("vm_exactly_one_service_account_required")
    account = accounts[0]
    if account.get("email") != SERVICE_ACCOUNT:
        raise ProvisionError("vm_runtime_service_account_mismatch")
    scopes = account.get("scopes")
    if scopes != [CLOUD_PLATFORM_SCOPE]:
        raise ProvisionError("vm_cloud_platform_scope_mismatch")


def validate_instance(instance: dict[str, Any]) -> None:
    if not str(instance.get("machineType") or "").endswith("/" + MACHINE_TYPE):
        raise ProvisionError("vm_machine_type_mismatch")
    interfaces = instance.get("networkInterfaces")
    if not isinstance(interfaces, list) or len(interfaces) != 1:
        raise ProvisionError("vm_exactly_one_network_interface_required")
    interface = interfaces[0]
    if not str(interface.get("network") or "").endswith("/" + NETWORK):
        raise ProvisionError("vm_network_mismatch")
    if not str(interface.get("subnetwork") or "").endswith("/" + SUBNET):
        raise ProvisionError("vm_subnet_mismatch")
    disks = instance.get("disks")
    if not isinstance(disks, list) or not disks or disks[0].get("autoDelete") is not False:
        raise ProvisionError("vm_persistent_boot_disk_required")
    validate_runtime_identity(instance)


def provision(runner: Callable[..., subprocess.CompletedProcess[str]] = gc) -> dict[str, Any]:
    if exists("compute", "networks", "describe", NETWORK, runner=runner) is None:
        runner("compute", "networks", "create", NETWORK, "--subnet-mode=custom")
    if exists(
        "compute",
        "networks",
        "subnets",
        "describe",
        SUBNET,
        "--region=" + REGION,
        runner=runner,
    ) is None:
        runner(
            "compute",
            "networks",
            "subnets",
            "create",
            SUBNET,
            "--network=" + NETWORK,
            "--region=" + REGION,
            "--range=10.40.0.0/24",
        )
    if exists(
        "compute", "firewall-rules", "describe", "aureon-sero-iap-ssh", runner=runner
    ) is None:
        runner(
            "compute",
            "firewall-rules",
            "create",
            "aureon-sero-iap-ssh",
            "--network=" + NETWORK,
            "--direction=INGRESS",
            "--action=ALLOW",
            "--rules=tcp:22",
            "--source-ranges=35.235.240.0/20",
            "--target-tags=aureon-sero-iap",
        )
    if exists("iam", "service-accounts", "describe", SERVICE_ACCOUNT, runner=runner) is None:
        runner(
            "iam",
            "service-accounts",
            "create",
            SERVICE_ACCOUNT_ID,
            "--display-name=Aureon VM token broker",
            "--description=Metadata identity with impersonation only; no data-plane roles",
        )

    current = exists("compute", "instances", "describe", VM, "--zone=" + ZONE, runner=runner)
    if current is None:
        runner(
            "compute",
            "instances",
            "create",
            VM,
            "--zone=" + ZONE,
            "--machine-type=" + MACHINE_TYPE,
            "--image-family=debian-12",
            "--image-project=debian-cloud",
            "--boot-disk-size=50GB",
            "--boot-disk-type=pd-balanced",
            "--no-boot-disk-auto-delete",
            "--network=" + NETWORK,
            "--subnet=" + SUBNET,
            "--service-account=" + SERVICE_ACCOUNT,
            "--scopes=" + CLOUD_PLATFORM_SCOPE,
            "--tags=aureon-sero-iap",
            "--shielded-secure-boot",
            "--metadata=block-project-ssh-keys=true",
            "--labels=application=aureon-sero,mode=deployment-hold",
            "--metadata-from-file=startup-script=" + str(HERE / "bootstrap-vm.sh"),
        )
        current = exists(
            "compute", "instances", "describe", VM, "--zone=" + ZONE, runner=runner
        )
    if not isinstance(current, dict):
        raise ProvisionError("vm_provider_readback_missing")
    validate_instance(current)

    receipt = {
        "schema": "aureon.gcp.vm-provision-receipt.v2",
        "project": PROJECT,
        "name": VM,
        "zone": ZONE,
        "status": current.get("status"),
        "id": current.get("id"),
        "machine_type": MACHINE_TYPE,
        "disk_gb": current["disks"][0].get("diskSizeGb"),
        "boot_disk_auto_delete": False,
        "service_accounts": [
            {"email": SERVICE_ACCOUNT, "scopes": [CLOUD_PLATFORM_SCOPE]}
        ],
        "network": NETWORK,
        "subnet": SUBNET,
        "ssh_ingress": "Google IAP only",
        "iam_grants": "commission_and_verify_from_resource_contract",
        "console_url": (
            "https://console.cloud.google.com/compute/instancesDetail/zones/"
            f"{ZONE}/instances/{VM}?project={PROJECT}"
        ),
    }
    (HERE / "vm-receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
    )
    return receipt


def main() -> None:
    print(json.dumps(provision(), indent=2))


if __name__ == "__main__":
    main()
