"""Static safety contract for the isolated Plumber laboratory workflow."""

from __future__ import annotations

import hashlib
import json
import re
import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "plumber-contract.yml"
PYPROJECT = ROOT / "pyproject.toml"
BASELINE_MANIFEST = ROOT / "docs" / "security" / "PLUMBER_BASELINE_MANIFEST_20260831.json"


def _load_workflow() -> tuple[str, dict[str, object]]:
    source = WORKFLOW.read_text(encoding="utf-8")
    workflow = yaml.load(source, Loader=yaml.BaseLoader)
    assert isinstance(workflow, dict)
    return source, workflow


def test_plumber_workflow_is_read_only_offline_and_fail_closed() -> None:
    source, workflow = _load_workflow()

    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["concurrency"]["cancel-in-progress"] == "true"
    assert "pull_request_target" not in workflow["on"]

    expected_env = {
        "CI": "true",
        "AUREON_AUDIT_MODE": "1",
        "AUREON_LIVE": "0",
        "LIVE": "0",
        "AUREON_DRY_RUN": "1",
        "DRY_RUN": "1",
        "AUREON_OFFLINE": "1",
        "AUREON_LIVE_TRADING": "0",
        "AUREON_DISABLE_REAL_ORDERS": "1",
        "AUREON_DISABLE_EXCHANGE_MUTATIONS": "1",
        "AUREON_LLM_OFFLINE": "1",
        "AUREON_DISABLE_LLM_HTTP": "1",
        "AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS": "1",
        "AUREON_LOCAL_ACTIONS_ARMED": "0",
        "AUREON_SOUL_ACT": "0",
        "AUREON_AUTONOMY": "0",
        "AUREON_CODE_AUTO_APPROVE": "0",
        "AUREON_ALLOW_PAID_PROVIDERS": "false",
        "AUREON_PROVIDER_MODE": "offline",
        "BINANCE_DRY_RUN": "true",
        "KRAKEN_DRY_RUN": "true",
        "ALPACA_DRY_RUN": "true",
        "CAPITAL_DEMO": "true",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
    }
    assert expected_env.items() <= workflow["env"].items()

    forbidden = (
        "continue-on-error",
        "pull_request_target",
        "${{ secrets.",
        "|| true",
        "--execute",
        "trade:real",
        "curl ",
        "wget ",
        "docker push",
        "wrangler deploy",
        "supabase functions deploy",
        "doctl ",
        "gh ",
    )
    lowered = source.lower()
    assert all(token not in lowered for token in forbidden)

    assert set(workflow["jobs"]) == {"plumber-contract"}
    job = workflow["jobs"]["plumber-contract"]
    assert int(job["timeout-minutes"]) <= 20

    actions = [step["uses"] for step in job["steps"] if "uses" in step]
    assert actions == [
        "actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803",
        "actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1",
    ]
    assert all(re.fullmatch(r"actions/[a-z-]+@[0-9a-f]{40}", action) for action in actions)
    checkout = next(step for step in job["steps"] if step.get("uses") == actions[0])
    assert checkout["with"]["persist-credentials"] == "false"
    assert set(job["strategy"]["matrix"]["os"]) == {"ubuntu-latest", "windows-latest"}


def test_plumber_workflow_gates_the_complete_surface_and_baseline() -> None:
    source, workflow = _load_workflow()

    required_paths = {
        "aureon/plumber/**",
        "tests/plumber/**",
        "tests/test_plumber_ci_workflow_contract.py",
        "aureon/harmonic/hnc_quantum_packet_crypto.py",
        "aureon/harmonic/hnc_symbolic_route_seal.py",
        "aureon/harmonic/rainbow_reference.py",
        "aureon/core/hnc_field.py",
        "aureon/observer/harmonic_observer.py",
        "aureon/operator/coherence_gate.py",
        "aureon/operator/heart.py",
        "aureon/operator/assimilation.py",
        "aureon/queen/queen_conscience.py",
        "aureon/governance/tool_route_authority.py",
        "aureon/saas/domains.py",
        "pyproject.toml",
        ".github/workflows/plumber-contract.yml",
    }
    for event in ("push", "pull_request"):
        assert required_paths <= set(workflow["on"][event]["paths"])

    required_commands = (
        "python -m pip install --only-binary=:all:",
        "cryptography==46.0.3",
        "pytest==9.0.2",
        "pytest-socket==0.8.0",
        "ruff==0.15.21",
        "mypy==2.3.0",
        "PyYAML==6.0.3",
        "python -m compileall -q aureon/plumber aureon/saas/domains.py tests/plumber",
        "ruff check aureon/plumber aureon/saas/domains.py tests/plumber tests/test_plumber_ci_workflow_contract.py",
        "mypy --strict aureon/plumber",
        "--disable-socket",
        "-p no:cacheprovider",
        "-o filterwarnings=error",
    )
    assert all(command in source for command in required_commands)

    for test_path in (
        "tests/plumber",
        "tests/test_plumber_ci_workflow_contract.py",
        "tests/test_hnc_quantum_packet_crypto.py",
        "tests/test_hnc_symbolic_route_seal.py",
        "tests/test_hnc_field_freshness.py",
        "tests/test_coherence_gate.py",
        "tests/test_heart.py",
        "tests/test_unified_contract.py",
        "tests/test_saas_catalog.py",
        "tests/test_saas_coverage.py",
    ):
        assert test_path in source


def test_plumber_extra_is_reviewed_and_adds_no_cli() -> None:
    project = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]

    assert project["optional-dependencies"]["plumber"] == ["cryptography>=46"]
    assert "aureon-plumber" not in project["scripts"]


def test_retained_baseline_manifest_matches_normalized_source_bytes() -> None:
    manifest = json.loads(BASELINE_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["repository"]["branch_parent"] == (
        "2359e25460d5eaf0864d39fea7912c7b96e7b921"
    )
    assert len(manifest["baseline_modules"]) == 8
    for record in manifest["baseline_modules"]:
        path = ROOT / record["path"]
        normalized_crlf = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        normalized_crlf = normalized_crlf.replace(b"\n", b"\r\n")
        assert len(normalized_crlf) == record["size_bytes"]
        assert hashlib.sha256(normalized_crlf).hexdigest() == record["sha256"]


def test_plumber_documents_keep_the_local_lab_hold_boundary() -> None:
    documents = {
        ROOT / "docs" / "security" / "PLUMBER_SECURITY_CHARTER.md": (
            "local laboratory",
            "No key, no plaintext",
            "Missing live canonical HNC evidence produces HOLD",
            "Missing hardware-rooted source evidence produces HOLD",
        ),
        ROOT / "docs" / "security" / "PLUMBER_THREAT_MODEL.md": (
            "local laboratory",
            "not a production security certification",
            "HOLD without provider",
            "A positive fake-provider test",
        ),
        ROOT / "docs" / "runbooks" / "PLUMBER_MAGIC_STAR_V02.md": (
            "experimental local laboratory only",
            "Production decryption/release: unavailable",
            "HOLD_MISSING_LIVE_EVIDENCE",
            "HOLD_MISSING_HARDWARE_EVIDENCE",
        ),
    }

    for path, required_phrases in documents.items():
        text = path.read_text(encoding="utf-8")
        assert all(phrase in text for phrase in required_phrases)
        assert "AUREON_LIVE='1'" not in text
        assert "AUREON_LOCAL_ACTIONS_ARMED='1'" not in text
