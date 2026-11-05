"""Receipt 5: provider deploy read-back, or an honest skip when auth is absent.

The skip test does not call a provider. The measured cases use a stand-in
client and a stand-in gcloud. Neither case claims the system is alive.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/validation/go_live_receipt5.py"
PIN = "34864ff0547d2cff03e707414743a3b0cc8770b5"
STARTED_FROM = "bb04503119681adcf832f3c3e9b0cbf09fc7a938"
TOKEN = "hf_testtokenvalue123456"
PROJECT = "receipt5-probe"
IMAGE = "us-docker.pkg.dev/receipt5-probe/app/hnc:v1"
SECRET_URL = "https://receipt5-secret.a.run.app/private"


def _load():
    spec = importlib.util.spec_from_file_location("go_live_receipt5", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


receipt5 = _load()


def _schema_ok(receipt: dict) -> None:
    try:
        import jsonschema
    except ImportError:
        return
    schema = json.loads((ROOT / receipt5.SCHEMA_PATH).read_text(encoding="utf-8"))
    jsonschema.validate(receipt, schema)


def _produce(tmp_path: Path, **kwargs):
    kwargs.setdefault("environ", {})
    kwargs.setdefault("home", tmp_path)
    kwargs.setdefault("which", lambda _name: None)
    kwargs.setdefault("gcloud_lister", lambda: None)
    kwargs.setdefault("now", lambda: "2026-11-05T20:31:00Z")
    return receipt5.produce(ROOT, **kwargs)


def test_empty_machine_is_a_hold_skip(tmp_path: Path) -> None:
    calls = {"network": 0}

    def blocked(*_args, **_kwargs):
        calls["network"] += 1
        raise AssertionError("provider call")

    receipt = _produce(tmp_path, gcloud_runner=blocked, hf_client=blocked)
    assert calls["network"] == 0
    assert receipt["outcome"] == "skip"
    assert receipt["receipt_5_complete"] is False
    assert receipt["go_live_clear"] is False
    assert receipt["system_alive_claimed"] is False
    assert receipt["decision"] == "HOLD"
    assert receipt["release_boundary"] == "HOLD"
    assert receipt["orange_badge"] == "unchanged"
    assert receipt["provider"] is None
    assert receipt["provider_readback"] is None
    assert receipt["provider_readback_digest"] is None
    assert receipt["provider_api_called"] is False
    assert receipt["deploy_attempted"] is False
    assert receipt["orders_placed"] is False
    assert receipt["live_trading"] is False
    assert receipt["tunnels_opened"] is False
    assert receipt["mcp_stages_3_and_4_opened"] is False
    assert receipt["installers_switched_on"] is False
    assert receipt["receipts_1_to_4_reverified"] is False
    assert receipt["pin"] == PIN
    assert receipt["pin_changed"] is False
    assert receipt["started_from"] == STARTED_FROM
    assert "No provider read-back was fabricated." in receipt["blocker"]
    assert "env:HF_TOKEN" in receipt["missing_provider_auth"]
    assert "command:gcloud" in receipt["missing_provider_auth"]
    assert receipt["unused_provider_auth"] == []
    assert receipt5.validate_receipt(receipt) == []
    _schema_ok(receipt)
    assert "not a claim that the system is alive" in receipt5.render_markdown(receipt)


def test_whitespace_token_file_is_absent(tmp_path: Path) -> None:
    path = tmp_path / ".cache/huggingface/token"
    path.parent.mkdir(parents=True)
    path.write_text("  \n", encoding="utf-8")
    probe = receipt5.probe_auth(environ={}, home=tmp_path, which=lambda _name: None, gcloud_lister=lambda: None)
    assert probe["hf_token_present"] is False
    assert "file:~/.cache/huggingface/token" in probe["missing_provider_auth"]


def test_unreadable_token_does_not_become_a_skip(tmp_path: Path) -> None:
    path = tmp_path / ".cache/huggingface/token"
    path.mkdir(parents=True)
    receipt = _produce(tmp_path)
    assert receipt["outcome"] == "fail"
    assert receipt["receipt_5_complete"] is False
    assert receipt["provider_readback"] is None
    assert "unreadable" in receipt["blocker"]
    assert receipt5.validate_receipt(receipt) == []


def test_active_gcloud_without_spend_flag_does_not_deploy(tmp_path: Path) -> None:
    def runner(*_args, **_kwargs):
        raise AssertionError("gcloud was invoked")

    receipt = _produce(
        tmp_path,
        which=lambda name: "/usr/bin/gcloud" if name == "gcloud" else None,
        gcloud_lister=lambda: True,
        gcloud_runner=runner,
    )
    assert receipt["outcome"] == "skip"
    assert receipt["provider_api_called"] is False
    assert receipt["deploy_attempted"] is False
    assert "gcloud:active-account" in receipt["unused_provider_auth"]
    assert "command:gcloud" not in receipt["missing_provider_auth"]
    assert "AUREON_RECEIPT5_ALLOW_CLOUD_RUN_DEPLOY=1" in receipt["blocker"]
    assert receipt5.validate_receipt(receipt) == []


def test_huggingface_readback_is_redacted_and_not_a_go_live(tmp_path: Path) -> None:
    calls: list[str] = []

    class Client:
        def whoami(self):
            calls.append("whoami")
            return {
                "name": "example-user",
                "email": "person@example.invalid",
                "auth": {"type": "access_token", "accessToken": TOKEN},
            }

        def create_repo(self, repo_id, **kwargs):
            calls.append("create")
            assert repo_id == "example-user/aureon-os-receipt5-hnc-field"
            assert kwargs["private"] is True
            assert kwargs["space_hardware"] == "cpu-basic"
            assert kwargs["repo_type"] == "space"
            return "https://huggingface.co/spaces/" + repo_id

        def upload_folder(self, **kwargs):
            calls.append("upload")
            assert kwargs["folder_path"].endswith("huggingface/hnc-field")
            return {"oid": "abc123", "commit_url": "https://user:token@huggingface.co/commit/abc123"}

        def get_space_runtime(self, repo_id):
            calls.append("runtime")
            assert repo_id == "example-user/aureon-os-receipt5-hnc-field"
            return {
                "stage": "BUILDING",
                "hardware": "cpu-basic",
                "requested_hardware": "cpu-basic",
                "errorMessage": f"see {TOKEN}",
                "token": TOKEN,
            }

        def repo_info(self, repo_id, **_kwargs):
            calls.append("info")
            return {
                "id": repo_id,
                "sha": "abc123",
                "lastModified": "2026-11-05T20:40:00Z",
                "private": True,
                "email": "person@example.invalid",
            }

    receipt = _produce(
        tmp_path,
        environ={"HF_TOKEN": TOKEN},
        hf_client=Client(),
    )
    text = json.dumps(receipt)
    assert calls == ["whoami", "create", "upload", "runtime", "info"]
    assert receipt["outcome"] == "measured"
    assert receipt["receipt_5_complete"] is True
    assert receipt["go_live_clear"] is False
    assert receipt["system_alive_claimed"] is False
    assert receipt["decision"] == "HOLD"
    assert receipt["orange_badge"] == "unchanged"
    assert receipt["provider"] == "huggingface"
    assert receipt["auth_method"] == "env:HF_TOKEN"
    assert receipt["provider_api"] == "https://huggingface.co/api"
    assert receipt["deploy_timestamp"] == "2026-11-05T20:40:00Z"
    assert receipt["deploy_timestamp_source"] == "provider"
    assert receipt["healthy"] is False
    assert receipt["provider_status"]["stage"] == "BUILDING"
    assert receipt["provider_readback_digest"] == receipt5.digest(receipt["provider_readback"])
    assert receipt["provider_readback"]["runtime"]["errorMessage"] == "see [redacted]"
    assert "token" not in receipt["provider_readback"]["runtime"]
    assert "person@example.invalid" not in text
    assert TOKEN not in text
    assert "user:token@" not in text
    assert receipt["orders_placed"] is False
    assert receipt5.validate_receipt(receipt) == []
    _schema_ok(receipt)


def test_non_cpu_hardware_does_not_call_the_provider(tmp_path: Path) -> None:
    class Client:
        def whoami(self):
            raise AssertionError("whoami")

    receipt = _produce(
        tmp_path,
        environ={"HF_TOKEN": TOKEN, "AUREON_RECEIPT5_HF_HARDWARE": "t4-small"},
        hf_client=Client(),
    )
    assert receipt["outcome"] == "fail"
    assert receipt["deploy_attempted"] is False
    assert receipt["provider_api_called"] is False
    assert receipt["provider_readback"] is None
    assert "cpu-basic" in receipt["blocker"]
    assert TOKEN not in json.dumps(receipt)
    assert receipt5.validate_receipt(receipt) == []


def test_cloud_run_describe_is_the_readback_and_ids_are_redacted(tmp_path: Path) -> None:
    argv_log: list[list[str]] = []

    def runner(argv, **_kwargs):
        argv_log.append(list(argv))
        if argv[1:3] == ["run", "deploy"]:
            return subprocess.CompletedProcess(argv, 0, stdout="{}", stderr="")
        body = {
            "apiVersion": "serving.knative.dev/v1",
            "kind": "Service",
            "metadata": {
                "name": "receipt5",
                "namespace": PROJECT,
                "uid": "secret-uid-value",
                "generation": 3,
            },
            "spec": {"template": {"spec": {"containers": [{"env": [{"name": "KEY", "value": TOKEN}]}]}}},
            "status": {
                "conditions": [{"type": "Ready", "status": "True", "reason": "ok"}],
                "url": SECRET_URL,
                "latestReadyRevisionName": "receipt5-00001",
                "observedGeneration": 3,
            },
        }
        return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(body), stderr="")

    receipt = _produce(
        tmp_path,
        environ={
            "AUREON_RECEIPT5_ALLOW_CLOUD_RUN_DEPLOY": "1",
            "AUREON_RECEIPT5_CLOUD_RUN_SERVICE": "receipt5",
            "AUREON_RECEIPT5_GCP_PROJECT": PROJECT,
            "AUREON_RECEIPT5_CLOUD_RUN_REGION": "us-central1",
            "AUREON_RECEIPT5_CLOUD_RUN_IMAGE": IMAGE,
        },
        which=lambda name: "/usr/bin/gcloud" if name == "gcloud" else None,
        gcloud_lister=lambda: True,
        gcloud_runner=runner,
    )
    text = json.dumps(receipt)
    assert receipt["outcome"] == "measured"
    assert receipt["provider"] == "google-cloud-run"
    assert receipt["auth_method"] == "gcloud:active-account"
    assert receipt["resource_id"] == "receipt5"
    assert receipt["provider_api"] == "https://run.googleapis.com"
    assert receipt["healthy"] is True
    assert receipt["go_live_clear"] is False
    assert receipt["provider_readback_digest"] == receipt5.digest(receipt["provider_readback"])
    assert receipt["provider_readback"]["project_sha256"] == receipt5.sha256(PROJECT.encode())
    assert receipt["provider_readback"]["url_present"] is True
    assert PROJECT not in text
    assert IMAGE not in text
    assert SECRET_URL not in text
    assert "secret-uid-value" not in text
    assert TOKEN not in text
    assert "--no-allow-unauthenticated" in argv_log[0]
    assert "--set-env-vars" not in " ".join(argv_log[0])
    assert argv_log[1][1:4] == ["run", "services", "describe"]
    assert receipt5.validate_receipt(receipt) == []
    _schema_ok(receipt)


def test_cloud_run_failure_keeps_the_digest_null(tmp_path: Path) -> None:
    def runner(argv, **_kwargs):
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="denied")

    receipt = _produce(
        tmp_path,
        environ={
            "AUREON_RECEIPT5_ALLOW_CLOUD_RUN_DEPLOY": "1",
            "AUREON_RECEIPT5_CLOUD_RUN_SERVICE": "receipt5",
            "AUREON_RECEIPT5_GCP_PROJECT": PROJECT,
            "AUREON_RECEIPT5_CLOUD_RUN_REGION": "us-central1",
            "AUREON_RECEIPT5_CLOUD_RUN_IMAGE": IMAGE,
        },
        which=lambda name: "/usr/bin/gcloud" if name == "gcloud" else None,
        gcloud_lister=lambda: True,
        gcloud_runner=runner,
    )
    assert receipt["outcome"] == "fail"
    assert receipt["receipt_5_complete"] is False
    assert receipt["provider_readback"] is None
    assert receipt["provider_readback_digest"] is None
    assert receipt["deploy_performed"] is False
    assert "exited 1" in receipt["blocker"]
    assert receipt5.validate_receipt(receipt) == []


def test_localhost_is_not_a_provider_readback() -> None:
    assert receipt5.provider_host_ok("https://huggingface.co/api") is True
    assert receipt5.provider_host_ok("https://run.googleapis.com") is True
    assert receipt5.provider_host_ok("http://127.0.0.1:8080/health") is False
    assert receipt5.provider_host_ok("http://localhost/health") is False
    receipt = {
        "schema": receipt5.SCHEMA,
        "stage": 10,
        "receipt": 5,
        "title": receipt5.TITLE,
        "decision": "HOLD",
        "outcome": "measured",
        "receipt_5_complete": True,
        "go_live_clear": False,
        "system_alive_claimed": False,
        "release_boundary": "HOLD",
        "orange_badge": "unchanged",
        "badge_flip": receipt5.BADGE_FLIP,
        "pin": PIN,
        "pin_changed": False,
        "pin_measured_at": STARTED_FROM,
        "pin_source": receipt5.PIN_SOURCE,
        "started_from": STARTED_FROM,
        "git_head_at_measurement": STARTED_FROM,
        "worktree_dirty_at_measurement": False,
        "provider": "huggingface",
        "auth_method": "env:HF_TOKEN",
        "missing_provider_auth": [],
        "unused_provider_auth": [],
        "blocker": None,
        "deploy_attempted": True,
        "deploy_performed": True,
        "deploy_timestamp": "2026-11-05T20:40:00Z",
        "deploy_timestamp_source": "local-clock",
        "resource_id": "example/space",
        "provider_api": "http://127.0.0.1/health",
        "provider_api_called": True,
        "provider_status": {"healthy": True},
        "provider_readback": {"api": "http://127.0.0.1/health"},
        "provider_readback_digest": receipt5.digest({"api": "http://127.0.0.1/health"}),
        "healthy": True,
        "localhost_substituted_for_provider": False,
        "live_trading": False,
        "orders_placed": False,
        "market_data_fetched": False,
        "tunnels_opened": False,
        "secrets_recorded": False,
        "mcp_stages_3_and_4_opened": False,
        "installers_switched_on": False,
        "receipts_1_to_4_reverified": False,
        "scaffold": None,
        "spend_guard": receipt5.SPEND_GUARD,
        "auth_probe": {},
        "runner": receipt5.RUNNER,
        "measured_at": "2026-11-05T20:31:00Z",
        "measurement_note": receipt5.MEASUREMENT_NOTE,
    }
    errors = receipt5.validate_receipt(receipt)
    assert any("local" in error for error in errors)


def test_committed_skip_matches_schema_pin_and_check() -> None:
    receipt = json.loads((ROOT / receipt5.JSON_PATH).read_text(encoding="utf-8"))
    markdown = (ROOT / receipt5.MARKDOWN_PATH).read_text(encoding="utf-8")
    anchor = json.loads((ROOT / "evidence/output/hnc_head_anchor.json").read_text(encoding="utf-8"))
    assert anchor["public_require_pin"] == PIN
    assert receipt["pin"] == anchor["public_require_pin"]
    assert receipt["started_from"] == STARTED_FROM
    assert receipt["git_head_at_measurement"] == STARTED_FROM
    assert receipt["outcome"] == "skip"
    assert receipt["receipt_5_complete"] is False
    assert receipt["provider_readback_digest"] is None
    assert receipt5.validate_receipt(receipt) == []
    assert markdown == receipt5.render_markdown(receipt)
    schema = json.loads((ROOT / receipt5.SCHEMA_PATH).read_text(encoding="utf-8"))
    assert set(schema["required"]) == set(receipt)
    errors = receipt5.check(ROOT)
    assert errors == []
    _schema_ok(receipt)
    assert set(schema["required"]) == set(receipt)


def test_readme_badge_is_still_hold() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "https://img.shields.io/badge/release%20boundary-HOLD-orange.svg" in readme


def test_runbook_cites_the_skip_and_leaves_the_badge() -> None:
    text = (ROOT / "docs/runbooks/GO_LIVE_HARDENING.md").read_text(encoding="utf-8")
    assert "reports/measured/go_live_receipt5_deployment.json" in text
    assert "stage 11" in text
    assert "Receipt 5 is not complete" in text
    assert "go_live_clear: true" not in text
