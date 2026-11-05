#!/usr/bin/env python3
"""Measure a local build of the guarded non-live preflight image.

Builds the root compose image, runs it with no network and no published port,
and writes a receipt only after that build and run succeed as a terminal HOLD.
Does not log in to a registry and does not push. This is not receipt 5, not a
provider read-back, not production ready, and not a validation. Go-live stays
HOLD.

``--check`` performs the same build and run and writes nothing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IMAGE = "aureon-protection-preflight:local"
COMPOSE_FILE = "docker-compose.yml"
CONTAINER = "aureon-public-preflight-measure"
RECEIPT_JSON = ROOT / "reports" / "measured" / "public_container_build.json"
RECEIPT_MD = ROOT / "reports" / "measured" / "public_container_build.md"
SCHEMA = "aureon.measured.public-container-build.v1"
SOURCE_FILES = (
    "Dockerfile",
    "docker-compose.yml",
    ".github/workflows/public-container.yml",
    "docs/deployment/PUBLIC_CONTAINER.md",
    "docs/runbooks/GO_LIVE_HARDENING.md",
    "README.md",
    "scripts/linux/install-linux.sh",
    "scripts/validation/measure_public_container.py",
)
SECRET_RE = re.compile(
    r"(SECRET|TOKEN|PASSWORD|PASSWD|API_KEY|PRIVATE_KEY|CREDENTIAL)",
    re.IGNORECASE,
)
BLOCKED_DOCKER = {"push", "login", "logout", "tag"}


class MeasureError(RuntimeError):
    """The build did not meet the guarded HOLD measurement."""


def refuse_registry_command(args: list[str]) -> None:
    """Reject any docker argv that would log in, tag, push, or publish a port."""

    if not args or args[0] != "docker":
        raise MeasureError("only docker commands are run")
    for index, part in enumerate(args[1:], start=1):
        lowered = part.lower()
        if lowered in BLOCKED_DOCKER or lowered == "--push" or lowered.startswith("ghcr.io"):
            raise MeasureError("refusing registry login, tag, or push")
        if lowered in {"--network=host", "--net=host"} or (
            lowered in {"--network", "--net"}
            and index + 1 < len(args)
            and args[index + 1].lower() == "host"
        ):
            raise MeasureError("refusing host network")
        if lowered in {"-p", "-P", "--publish", "--publish-all"} or lowered.startswith(
            ("--publish=", "-p")
        ):
            raise MeasureError("refusing a published port")


def judge_preflight(body: object) -> list[str]:
    """Return failed predicates for one isolated-bootstrap JSON object."""

    if not isinstance(body, dict):
        return ["preflight_not_object"]
    expected = {
        "decision": "HOLD",
        "target_id": "docker-runtime",
        "target_imported": False,
        "target_called": False,
        "network_accessed": False,
        "file_written": False,
        "child_process_started": False,
        "process_start_authorized": False,
        "production_ready": False,
        "economic_eligible": False,
        "git_invoked": False,
    }
    failures = [
        key for key, value in expected.items() if body.get(key) != value
    ]
    if body.get("schema") != "aureon.plumber.isolated-protected-bootstrap.v05":
        failures.append("schema")
    return failures


def _record_env(env: list[str]) -> list[object]:
    """Keep guarded defaults literal. Omit key-like values; record their sha256."""

    recorded: list[object] = []
    for item in env:
        name, separator, value = item.partition("=")
        if not separator:
            recorded.append(item)
            continue
        if name.endswith("_KEY") or SECRET_RE.search(name):
            recorded.append(
                {
                    "literal_recorded": False,
                    "name": name,
                    "reason": "key-like image environment name; literal omitted",
                    "value_sha256": hashlib.sha256(value.encode("utf-8")).hexdigest(),
                }
            )
            continue
        recorded.append(item)
    return recorded


def _names_a_registry(digest: str) -> bool:
    name = digest.split("@", 1)[0].lower()
    return "/" in name or "." in name


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run(args: list[str], *, timeout: int, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    refuse_registry_command(args)
    return subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _docker(*args: str, timeout: int) -> subprocess.CompletedProcess[str]:
    return _run(["docker", *args], timeout=timeout)


def _require_docker() -> dict[str, str]:
    if shutil.which("docker") is None:
        raise MeasureError("docker is not on PATH; no receipt written")
    version = _docker("version", "--format", "{{json .}}", timeout=30)
    if version.returncode != 0:
        raise MeasureError(version.stderr.strip() or "docker version failed; no receipt written")
    payload = json.loads(version.stdout)
    client = payload.get("Client") or {}
    server = payload.get("Server") or {}
    return {
        "client": str(client.get("Version") or ""),
        "server": str(server.get("Version") or ""),
    }


def _compose_config() -> dict[str, object]:
    rendered = _docker("compose", "-f", COMPOSE_FILE, "config", "--format", "json", timeout=60)
    if rendered.returncode != 0:
        raise MeasureError(rendered.stderr.strip() or "docker compose config failed")
    payload = json.loads(rendered.stdout)
    services = payload.get("services")
    if not isinstance(services, dict) or set(services) != {"protection-preflight"}:
        raise MeasureError("compose service set is not the single preflight")
    service = services["protection-preflight"]
    if not isinstance(service, dict):
        raise MeasureError("compose service is not an object")
    for forbidden in ("environment", "env_file", "ports", "volumes", "secrets"):
        if forbidden in service:
            raise MeasureError(f"compose injects {forbidden}")
    if service.get("network_mode") != "none":
        raise MeasureError("compose network is not none")
    if service.get("image") != IMAGE:
        raise MeasureError("compose image name changed")
    if service.get("read_only") is not True:
        raise MeasureError("compose root is not read-only")
    return payload


def _build() -> int:
    built = _docker("compose", "-f", COMPOSE_FILE, "build", timeout=900)
    if built.returncode != 0:
        detail = (built.stderr or built.stdout).strip()
        raise MeasureError(f"image build failed: {detail[-2000:]}")
    return built.returncode


def _image_record() -> dict[str, object]:
    inspected = _docker("image", "inspect", IMAGE, timeout=60)
    if inspected.returncode != 0:
        raise MeasureError(inspected.stderr.strip() or "image inspect failed")
    image = json.loads(inspected.stdout)[0]
    config = image.get("Config") or {}
    env = _record_env(list(config.get("Env") or []))
    exposed = config.get("ExposedPorts")
    if exposed:
        raise MeasureError("image declares exposed ports")
    entrypoint = list(config.get("Entrypoint") or [])
    if "protected_bootstrap_v05.py" not in " ".join(entrypoint):
        raise MeasureError("image entrypoint is not the isolated bootstrap")
    if "docker-runtime" not in entrypoint:
        raise MeasureError("image entrypoint target is not docker-runtime")
    if config.get("User") != "aureon":
        raise MeasureError("image user is not aureon")
    digests = list(image.get("RepoDigests") or [])
    # A locally built image can carry name@sha256 equal to its id. A registry
    # name has a slash or a dot (ghcr.io/...). Those are a publish, which this
    # measurement refuses.
    registry_digests = [item for item in digests if _names_a_registry(item)]
    if registry_digests:
        raise MeasureError("image names a registry digest; refusing to treat it as unpublished")
    return {
        "id": image.get("Id"),
        "created": image.get("Created"),
        "size": image.get("Size"),
        "os": image.get("Os"),
        "architecture": image.get("Architecture"),
        "repo_tags": list(image.get("RepoTags") or []),
        "repo_digests": digests,
        "registry_repo_digests": registry_digests,
        "user": config.get("User"),
        "entrypoint": entrypoint,
        "cmd": list(config.get("Cmd") or []),
        "env": env,
        "exposed_ports": exposed,
        "labels": config.get("Labels") or {},
    }


def _run_container() -> tuple[dict[str, object], dict[str, object], str]:
    _docker("rm", "-f", CONTAINER, timeout=30)
    run = _docker(
        "run",
        "--name",
        CONTAINER,
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges:true",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=16m",
        "--pull",
        "never",
        IMAGE,
        timeout=60,
    )
    if run.returncode != 1:
        raise MeasureError(
            f"expected HOLD exit 1, got {run.returncode}: {(run.stderr or run.stdout)[-1000:]}"
        )
    try:
        preflight = json.loads(run.stdout)
    except json.JSONDecodeError as exc:
        raise MeasureError(f"preflight stdout was not JSON: {exc}") from exc
    failures = judge_preflight(preflight)
    if failures:
        raise MeasureError("preflight predicates failed: " + ", ".join(failures))
    inspected = _docker("inspect", CONTAINER, timeout=30)
    if inspected.returncode != 0:
        raise MeasureError(inspected.stderr.strip() or "container inspect failed")
    container = json.loads(inspected.stdout)[0]
    host = container.get("HostConfig") or {}
    network = container.get("NetworkSettings") or {}
    if host.get("NetworkMode") != "none":
        raise MeasureError("container network mode was not none")
    if host.get("PortBindings"):
        raise MeasureError("container published ports")
    if network.get("Ports"):
        raise MeasureError("container has port mappings")
    if int((container.get("State") or {}).get("ExitCode", -1)) != 1:
        raise MeasureError("container exit code was not the HOLD exit 1")
    with tempfile.TemporaryDirectory() as tmp:
        copied = _docker(
            "cp",
            f"{CONTAINER}:/app/scripts/bootstrap/protected_bootstrap_v05.py",
            str(Path(tmp) / "bootstrap.py"),
            timeout=30,
        )
        if copied.returncode != 0:
            raise MeasureError(copied.stderr.strip() or "could not read the bootstrap from the image")
        image_bootstrap = _sha256(Path(tmp) / "bootstrap.py")
    host_bootstrap = _sha256(ROOT / "scripts" / "bootstrap" / "protected_bootstrap_v05.py")
    if image_bootstrap != host_bootstrap:
        raise MeasureError("image bootstrap bytes differ from the checkout")
    _docker("rm", "-f", CONTAINER, timeout=30)
    record = {
        "exit_code": run.returncode,
        "network_mode": host.get("NetworkMode"),
        "port_bindings": host.get("PortBindings"),
        "ports": network.get("Ports"),
        "readonly_rootfs": host.get("ReadonlyRootfs"),
        "cap_drop": host.get("CapDrop"),
        "bootstrap_sha256": image_bootstrap,
        "bootstrap_matches_checkout": True,
    }
    return preflight, record, run.stdout


def _git_head() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise MeasureError(result.stderr.strip() or "git rev-parse failed")
    return result.stdout.strip()


def _dirty_paths() -> list[str]:
    result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise MeasureError(result.stderr.strip() or "git status failed")
    paths: list[str] = []
    for line in result.stdout.splitlines():
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        paths.append(path)
    return paths


def _source_hashes() -> dict[str, str]:
    return {name: _sha256(ROOT / name) for name in SOURCE_FILES}


def build_receipt() -> dict[str, object]:
    versions = _require_docker()
    compose = _compose_config()
    _build()
    image = _image_record()
    preflight, run_record, _stdout = _run_container()
    service = compose["services"]["protection-preflight"]
    return {
        "schema": SCHEMA,
        "kind": "local-image-build",
        "verdict": "measured_hold",
        "release_boundary": "HOLD",
        "go_live": "HOLD",
        "receipt_5": "HOLD",
        "this_is_receipt_5": False,
        "provider_readback": False,
        "authenticated_deployment_receipt": False,
        "claims": {
            "production_ready": False,
            "validated": False,
            "cloud_go_live": False,
            "system_alive": False,
            "receipt_5": False,
            "listeners_opened": False,
            "registry_publish": False,
        },
        "orders_placed": False,
        "live_trading": False,
        "market_data_fetched": False,
        "listeners_opened": False,
        "registry": {
            "login_attempted": False,
            "push_attempted": False,
            "public_ghcr_publish": False,
            "repo_digests": image["registry_repo_digests"],
        },
        "docker": versions,
        "image": image,
        "compose": {
            "file": COMPOSE_FILE,
            "service": "protection-preflight",
            "network_mode": service.get("network_mode"),
            "environment_injected": "environment" in service,
            "ports_injected": "ports" in service,
            "secrets_injected": "secrets" in service,
        },
        "run": run_record,
        "preflight": preflight,
        "source_sha256": _source_hashes(),
        "git_head_at_measurement": _git_head(),
        "worktree_dirty_paths": _dirty_paths(),
        "measured_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": (
            "Local image build of the guarded preflight. Not receipt 5. "
            "Not a provider read-back. Not production ready. Not a validation. "
            "Go-live stays HOLD. The image was not pushed."
        ),
    }


def render_markdown(receipt: dict[str, object]) -> str:
    image = receipt["image"]
    run = receipt["run"]
    preflight = receipt["preflight"]
    assert isinstance(image, dict)
    assert isinstance(run, dict)
    assert isinstance(preflight, dict)
    claims = receipt["claims"]
    assert isinstance(claims, dict)
    return "\n".join(
        (
            "# Public container build",
            "",
            "Local build of the root guarded preflight. This is not a claim that a live",
            "Aureon instance exists, and it is not a claim that the system is alive.",
            "",
            f"Verdict: **{receipt['verdict']}**.",
            "Release boundary: **HOLD**. Orange badge: unchanged.",
            "Go-live: **HOLD**.",
            "Production ready: false. Validation claim: none.",
            "Receipt 5 (authenticated deployment receipt and provider-side read-back): **HOLD**.",
            "This file is not receipt 5. Provider read-back: false. Registry publish: false.",
            "",
            "## Image",
            "",
            f"Tag `{IMAGE}` (measured). Id `{image['id']}`.",
            f"Size {image['size']} bytes. Created `{image['created']}`.",
            f"User `{image['user']}`. Exposed ports: {image['exposed_ports']!s}.",
            f"Repo digests: {image['repo_digests']!s}. Login attempted: false. Push attempted: false.",
            "",
            "## Run",
            "",
            "Command was `docker run` with network none, a read-only root, and every capability dropped.",
            f"Exit code {run['exit_code']} (measured). Network mode `{run['network_mode']}`.",
            f"Port bindings {run['port_bindings']!s}. Listeners opened: false.",
            f"Bootstrap sha256 matches the checkout: {run['bootstrap_matches_checkout']}.",
            "",
            "## Preflight",
            "",
            f"decision `{preflight['decision']}`. target_imported {preflight['target_imported']}.",
            (
                f"network_accessed {preflight['network_accessed']}. "
                f"production_ready {preflight['production_ready']}."
            ),
            f"target_id `{preflight['target_id']}`.",
            "",
            "## Still HOLD",
            "",
            "- Receipt 2: exact target-source measurement and immutable release provenance — HOLD",
            "- Receipt 3: durable HNC evidence with an external monotonic head anchor — HOLD",
            "- Receipt 4: complete source-boundary census closure — HOLD",
            "- Receipt 5: authenticated deployment receipt and provider-side read-back — HOLD",
            "",
            "A public GHCR push was not done. It needs Gary's own yes and a token. Neither was used.",
            "Claims recorded here: "
            + ", ".join(f"{key}={value}" for key, value in sorted(claims.items()))
            + ".",
            "",
            f"Git HEAD at measurement: `{receipt['git_head_at_measurement']}`.",
            "The UTC stamp is this machine's clock. It is not receipt 3.",
            "",
        )
    )


def write_receipt(receipt: dict[str, object]) -> None:
    RECEIPT_JSON.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT_JSON.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    RECEIPT_MD.write_text(render_markdown(receipt), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="build and run, then write nothing",
    )
    args = parser.parse_args(argv)
    try:
        receipt = build_receipt()
    except MeasureError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if args.check:
        print(
            json.dumps(
                {
                    "decision": "HOLD",
                    "image_id": receipt["image"]["id"] if isinstance(receipt["image"], dict) else None,
                    "pushed": False,
                    "wrote_receipt": False,
                },
                sort_keys=True,
            )
        )
        return 0
    write_receipt(receipt)
    print(f"wrote {RECEIPT_JSON.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    sys.exit(main())
