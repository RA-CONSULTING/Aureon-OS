"""Public container distribution stays a guarded local HOLD build.

The image may be built locally and in CI. Nothing in this path publishes to
GHCR, opens a listener, claims production readiness, or clears go-live.
"""

from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path

import yaml
from yaml import BaseLoader

from scripts.validation.measure_public_container import (
    MeasureError,
    judge_preflight,
    refuse_registry_command,
)

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "reports" / "measured" / "public_container_build.json"
RECEIPT_MD = ROOT / "reports" / "measured" / "public_container_build.md"
WORKFLOW = ROOT / ".github" / "workflows" / "public-container.yml"


def test_registry_commands_are_refused() -> None:
    for args in (
        ["docker", "push", "ghcr.io/ra-consulting/aureon-os:guarded"],
        ["docker", "login", "ghcr.io"],
        ["docker", "compose", "build", "--push"],
        ["docker", "tag", "aureon-protection-preflight:local", "ghcr.io/example/aureon:guarded"],
        ["docker", "run", "--network", "host", "aureon-protection-preflight:local"],
        ["docker", "run", "-p", "8080:80", "aureon-protection-preflight:local"],
        ["docker", "run", "--publish", "80:80", "aureon-protection-preflight:local"],
    ):
        try:
            refuse_registry_command(args)
        except MeasureError:
            continue
        raise AssertionError(args)


def test_preflight_judge_accepts_only_terminal_hold() -> None:
    body = {
        "schema": "aureon.plumber.isolated-protected-bootstrap.v05",
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
    assert judge_preflight(body) == []
    body["decision"] = "GO"
    assert "decision" in judge_preflight(body)
    body["decision"] = "HOLD"
    body["production_ready"] = True
    assert "production_ready" in judge_preflight(body)
    body["production_ready"] = False
    body["target_imported"] = True
    assert "target_imported" in judge_preflight(body)


def test_dockerfile_is_guarded_non_live_and_has_no_listener() -> None:
    source = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "AUREON_AUTONOMY_MODE=guarded" in source
    assert "AUREON_LIVE_TRADING=0" in source
    assert "AUREON_LLM_OFFLINE=1" in source
    assert "AUREON_DISABLE_REAL_ORDERS=1" in source
    assert "AUREON_DISABLE_EXCHANGE_MUTATIONS=1" in source
    assert "EXPOSE" not in source
    assert "aureon.go-live=\"HOLD\"" in source
    assert "aureon.production-ready=\"false\"" in source
    assert "aureon.validation-claim=\"none\"" in source
    assert "ghcr.io" not in source.lower()
    entrypoint = next(line for line in source.splitlines() if line.startswith("ENTRYPOINT "))
    assert '"--target-id", "docker-runtime"' in entrypoint
    assert '"-I", "-S", "-B"' in entrypoint


def test_compose_injects_no_secret_port_or_environment() -> None:
    source = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    compose = yaml.safe_load(source)
    service = compose["services"]["protection-preflight"]
    assert service["image"] == "aureon-protection-preflight:local"
    assert service["network_mode"] == "none"
    for forbidden in ("environment", "env_file", "ports", "volumes", "secrets"):
        assert forbidden not in service
    assert "ghcr.io" not in source.lower()
    assert "AUREON_" not in source


def test_workflow_builds_locally_and_does_not_publish() -> None:
    source = WORKFLOW.read_text(encoding="utf-8")
    workflow = yaml.load(source, Loader=BaseLoader)
    assert workflow["permissions"] == {"contents": "read"}
    assert "pull_request_target" not in workflow["on"]
    lowered = source.lower()
    for forbidden in (
        "docker push",
        "docker login",
        "ghcr.io",
        "${{ secrets.",
        "packages: write",
        "--network host",
        "--push",
        "0.0.0.0",
    ):
        assert forbidden not in lowered
    assert "measure_public_container.py --check" in source
    assert "Gary" in source
    checkout = workflow["jobs"]["build"]["steps"][0]
    assert checkout["with"]["persist-credentials"] == "false"


def test_docs_keep_go_live_hold_and_the_gary_gate() -> None:
    doc = (ROOT / "docs" / "deployment" / "PUBLIC_CONTAINER.md").read_text(encoding="utf-8")
    runbook = (ROOT / "docs" / "runbooks" / "GO_LIVE_HARDENING.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    installer = (ROOT / "scripts" / "linux" / "install-linux.sh").read_text(encoding="utf-8")
    for text in (doc, runbook, readme):
        assert "Gary" in text
        assert "HOLD" in text
    assert "not production ready" in doc.lower()
    assert "not a validation" in doc.lower()
    assert "receipt 5" in doc.lower()
    assert "does not push" in doc.lower() or "does not push" in readme.lower()
    assert "Receipts 2–5 remain HOLD" in runbook or "Receipts 2, 3, 4, and 5 remain HOLD" in runbook
    assert "release%20boundary-HOLD-orange" in readme
    assert "protected_bootstrap_v05.py" in installer
    assert "--target-id linux-supervisor" in installer
    assert "docker" not in installer.lower()
    assert "aureon.containment" not in installer


def test_measure_script_has_no_publish_call() -> None:
    source = (ROOT / "scripts" / "validation" / "measure_public_container.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    invoked: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.id if isinstance(func, ast.Name) else ""
        if name not in {"_docker", "_run"}:
            continue
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                invoked.append(arg.value)
    assert "push" not in invoked
    assert "login" not in invoked
    assert not any(item.startswith("ghcr.io") for item in invoked)


def test_measured_receipt_matches_the_hold_build() -> None:
    assert RECEIPT.is_file() and RECEIPT_MD.is_file()
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    text = RECEIPT.read_text(encoding="utf-8")
    assert receipt["schema"] == "aureon.measured.public-container-build.v1"
    assert receipt["kind"] == "local-image-build"
    assert receipt["verdict"] == "measured_hold"
    assert receipt["release_boundary"] == "HOLD"
    assert receipt["go_live"] == "HOLD"
    assert receipt["receipt_5"] == "HOLD"
    assert receipt["this_is_receipt_5"] is False
    assert receipt["provider_readback"] is False
    assert receipt["claims"]["production_ready"] is False
    assert receipt["claims"]["validated"] is False
    assert receipt["claims"]["cloud_go_live"] is False
    assert receipt["claims"]["system_alive"] is False
    assert receipt["claims"]["listeners_opened"] is False
    assert receipt["claims"]["registry_publish"] is False
    assert receipt["registry"]["push_attempted"] is False
    assert receipt["registry"]["login_attempted"] is False
    assert receipt["registry"]["public_ghcr_publish"] is False
    assert receipt["registry"]["repo_digests"] == []
    assert receipt["listeners_opened"] is False
    assert receipt["orders_placed"] is False
    assert receipt["live_trading"] is False
    assert receipt["image"]["exposed_ports"] is None
    assert receipt["image"]["user"] == "aureon"
    assert receipt["registry"]["repo_digests"] == []
    assert all("/" not in item.split("@", 1)[0] for item in receipt["image"]["repo_digests"])
    assert all("." not in item.split("@", 1)[0] for item in receipt["image"]["repo_digests"])
    assert "docker-runtime" in receipt["image"]["entrypoint"]
    env = receipt["image"]["env"]
    assert "AUREON_AUTONOMY_MODE=guarded" in env
    assert "AUREON_LIVE_TRADING=0" in env
    assert all(not (isinstance(item, str) and "_KEY=" in item) for item in env)
    redacted = [item for item in env if isinstance(item, dict)]
    assert any(item.get("name") == "GPG_KEY" and item.get("literal_recorded") is False for item in redacted)
    assert receipt["run"]["exit_code"] == 1
    assert receipt["run"]["network_mode"] == "none"
    assert receipt["run"]["bootstrap_matches_checkout"] is True
    assert receipt["compose"]["environment_injected"] is False
    assert receipt["compose"]["ports_injected"] is False
    assert receipt["compose"]["secrets_injected"] is False
    assert judge_preflight(receipt["preflight"]) == []
    # README.md moved on main after the local build. The image was not rebuilt
    # and was not pushed. The receipt keeps the measurement-time digest.
    drifted = {"README.md"}
    for name, digest in receipt["source_sha256"].items():
        current = _sha256(ROOT / name)
        if name in drifted:
            assert current != digest
            continue
        assert current == digest, name
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "release%20boundary-HOLD-orange" in readme
    lowered_readme = readme.lower()
    assert "production-ready" not in lowered_readme
    assert "production ready" not in lowered_readme
    assert "validated" not in lowered_readme
    note = receipt["later_checkout_note"]
    assert note["image_rebuilt"] is False
    assert note["push_attempted"] is False
    assert note["orange_badge"] == "HOLD"
    assert note["go_live_clear"] is False
    assert note["readme_sha256_is_measurement_time"] is True
    assert note["checked_on"] == "9333bfbbeb8de54a4b42be05f9263e536da643a7"
    measured = receipt["git_head_at_measurement"]
    assert measured == "08f04936088689e29b7995d89530b21b425c35f9"
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", measured, "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert ancestor.returncode == 0
    markdown = RECEIPT_MD.read_text(encoding="utf-8")
    assert "not a claim that the system is alive" in markdown
    assert "Receipt 5" in markdown
    assert "**HOLD**" in markdown
    assert "not production ready" in markdown.lower() or "Production ready: false" in markdown
    assert "Push attempted: false" in markdown
    assert receipt["image"]["id"] in markdown
    assert "ghcr.io" not in text
    assert "BEGIN OPENSSH" not in text
    assert "BEGIN PRIVATE" not in text


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()
