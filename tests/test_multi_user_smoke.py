"""Stage 9: contained multi-user smoke. Offline judge plus one measured launch."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from aureon.containment.multi_user_smoke import (
    PIN,
    STARTED_FROM,
    contained_child_env,
    judge,
    public_pin,
    receipt_names_are_safe,
    redact_text,
    repo_root,
)
from aureon.containment.native import prepare_launch, scrubbed_child_env

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "reports" / "measured" / "multi_user_smoke.json"
RECEIPT_MD = ROOT / "reports" / "measured" / "multi_user_smoke.md"
SECRET = "super-secret-kraken"


def _child(**overrides: object) -> dict:
    found = dict.fromkeys(
        (
            "canary_control",
            "canary_prompt_a",
            "canary_prompt_b_absent",
            "canary_prompt_b",
            "canary_prompt_a_revoked",
            "canary_prompt_b_still",
            "canary_tenant_a",
            "canary_tenant_b",
            "canary_signer",
            "canary_operator",
        ),
        False,
    )
    control_found = dict(found)
    control_found["canary_control"] = True
    env_found = dict(found)
    env_found["canary_signer"] = True
    env_found["canary_operator"] = True
    base = {
        "ok": True,
        "go_live_clear": False,
        "orders_placed": False,
        "live_trading": False,
        "market_data_fetched": False,
        "listener_bound": False,
        "production_ready": False,
        "magic_star_release": False,
        "report_contained_secret": False,
        "net_ns": "net:[2]",
        "tcp_1_1_1_1_443": {"ok": False, "errno": 101, "error": "ENETUNREACH", "bytes_read": 0},
        "plaintext_key_in_store": False,
        "cross_tenant_key_visible": False,
        "environ_has_tenant_key": False,
        "provider_write_a": 200,
        "provider_write_b": 200,
        "tenant_me_status": 200,
        "admin_pulse_status": 200,
        "admin_pulse_secret": False,
        "reason_a": {"status": 200, "tenant_no_key": False, "tool_names": [], "secret_in_body": True},
        "reason_b_keyless": {"status": 200, "tenant_no_key": True, "tool_names": [], "secret_in_body": True},
        "reason_b": {"status": 200, "tenant_no_key": False, "tool_names": ["code_validate"], "secret_in_body": True},
        "reason_a_revoked": {"status": 200, "tenant_no_key": True, "tool_names": [], "secret_in_body": True},
        "reason_b_still": {"status": 200, "tenant_no_key": False, "tool_names": [], "secret_in_body": True},
        "default_deny": [
            {"method": "GET", "path": "/api/pulse", "mounted": True, "status": 403, "secret_in_body": False},
            {"method": "GET", "path": "/api/switchboard", "mounted": True, "status": 403, "secret_in_body": False},
            {"method": "GET", "path": "/api/terminal-state", "mounted": True, "status": 403, "secret_in_body": False},
        ],
        "surfaces": {
            "thought_bus_recent": {"scanned_items": 1, "found": control_found},
            "thoughts_jsonl": {"bytes": 10, "truncated": False, "found": control_found},
            "os_environ_values": {"names_scanned": 4, "found": env_found},
            "dev_shm_new": {
                "readable": True,
                "preexisting_count": 3,
                "preexisting_read": False,
                "new_names": [],
                "new_bytes_scanned": 0,
                "read_errors": 0,
                "found": found,
            },
            "home_files": {
                "files": 2,
                "bytes": 10,
                "read_errors": 0,
                "truncated": False,
                "paths": {
                    label: (["thoughts.jsonl"] if label == "canary_control" else [])
                    for label in found
                },
            },
        },
    }
    base.update(overrides)
    return base


def test_judge_passes_a_measured_isolation_report() -> None:
    judged = judge(_child(), started=True, parent_net_ns="net:[1]", argv_has_net=True)
    assert judged["verdict"] == "pass", judged
    assert judged["failures"] == []


def test_judge_fails_when_the_scanner_misses_the_control() -> None:
    child = _child()
    child["surfaces"]["thought_bus_recent"]["found"]["canary_control"] = False
    child["surfaces"]["home_files"]["paths"] = {}
    judged = judge(child, started=True, parent_net_ns="net:[1]", argv_has_net=True)
    assert judged["verdict"] == "fail"
    assert any("control" in item for item in judged["failures"])


def test_judge_fails_when_a_prompt_lands_on_the_shared_bus() -> None:
    child = _child()
    child["surfaces"]["thought_bus_recent"]["found"]["canary_prompt_a"] = True
    judged = judge(child, started=True, parent_net_ns="net:[1]", argv_has_net=True)
    assert judged["verdict"] == "fail"
    assert any("canary_prompt_a found on thought_bus_recent" in item for item in judged["failures"])


def test_judge_fails_when_a_key_is_in_a_contained_file(child_path: str = "tenants/v_stage9-user-b/provider_keys.json.enc") -> None:
    child = _child()
    child["surfaces"]["home_files"]["paths"] = {
        "canary_control": ["thoughts.jsonl"],
        "canary_tenant_a": [child_path],
    }
    judged = judge(child, started=True, parent_net_ns="net:[1]", argv_has_net=True)
    assert judged["verdict"] == "fail"
    assert any("canary_tenant_a found in contained files" in item for item in judged["failures"])


def test_judge_fails_when_default_deny_lets_a_tenant_through() -> None:
    child = _child()
    child["default_deny"][0]["status"] = 200
    judged = judge(child, started=True, parent_net_ns="net:[1]", argv_has_net=True)
    assert judged["verdict"] == "fail"
    assert any("/api/pulse returned 200" in item for item in judged["failures"])


def test_judge_holds_when_the_required_route_is_unmounted() -> None:
    child = _child()
    child["default_deny"][0]["mounted"] = False
    child["default_deny"][0]["status"] = None
    judged = judge(child, started=True, parent_net_ns="net:[1]", argv_has_net=True)
    assert judged["verdict"] == "hold"
    assert any("/api/pulse" in item for item in judged["holds"])


def test_incomplete_or_missing_scans_cannot_pass() -> None:
    """A missing map, a partial map, a read error, or truncation is not a pass."""

    missing_env = _child()
    del missing_env["surfaces"]["os_environ_values"]

    missing_shm = _child()
    del missing_shm["surfaces"]["dev_shm_new"]

    missing_bus = _child()
    del missing_bus["surfaces"]["thought_bus_recent"]

    missing_found = _child()
    del missing_found["surfaces"]["thought_bus_recent"]["found"]

    missing_surfaces = _child()
    del missing_surfaces["surfaces"]

    partial = _child()
    del partial["surfaces"]["os_environ_values"]["found"]["canary_tenant_a"]

    read_error = _child()
    read_error["surfaces"]["dev_shm_new"]["read_errors"] = 1

    home_read_error = _child()
    home_read_error["surfaces"]["home_files"]["read_errors"] = 2

    truncated = _child()
    truncated["surfaces"]["thoughts_jsonl"]["truncated"] = True

    home_truncated = _child()
    home_truncated["surfaces"]["home_files"]["truncated"] = True

    unreported = _child()
    del unreported["surfaces"]["thoughts_jsonl"]["truncated"]

    unreadable = _child()
    unreadable["surfaces"]["dev_shm_new"]["readable"] = False

    for child in (
        missing_env,
        missing_shm,
        missing_bus,
        missing_found,
        missing_surfaces,
        partial,
        read_error,
        home_read_error,
        truncated,
        home_truncated,
        unreported,
        unreadable,
    ):
        judged = judge(child, started=True, parent_net_ns="net:[1]", argv_has_net=True)
        assert judged["verdict"] in {"fail", "hold"}, judged
        assert judged["verdict"] != "pass"


def test_truncation_does_not_hide_a_measured_leak() -> None:
    child = _child()
    child["surfaces"]["thoughts_jsonl"]["truncated"] = True
    child["surfaces"]["thought_bus_recent"]["found"]["canary_prompt_a"] = True
    judged = judge(child, started=True, parent_net_ns="net:[1]", argv_has_net=True)
    assert judged["verdict"] == "fail", judged


def test_judge_does_not_treat_an_unmounted_optional_route_as_a_pass_blocker() -> None:
    child = _child()
    child["default_deny"].append(
        {"method": "GET", "path": "/api/trades", "mounted": False, "status": None}
    )
    judged = judge(child, started=True, parent_net_ns="net:[1]", argv_has_net=True)
    assert judged["verdict"] == "pass", judged
    assert any("/api/trades" in item for item in judged["gaps"])


def test_redact_text_strips_generated_canaries() -> None:
    raw = "sk-stage9a-" + ("ab" * 8) + "AAAA stage9-prompt-a-" + ("cd" * 8)
    cleaned = redact_text(raw)
    assert "sk-stage9a-" not in cleaned
    assert "stage9-prompt-a-" not in cleaned
    assert "[redacted]" in cleaned


def test_contained_env_does_not_copy_the_parent(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    pytest.importorskip("flask")
    monkeypatch.setenv("KRAKEN_API_SECRET", SECRET)
    monkeypatch.setenv("AUREON_SUPABASE_JWT_SECRET", SECRET)
    if shutil.which("unshare") is None:
        pytest.skip("unshare is not on PATH")
    prepared = prepare_launch(tmp_path, ["/usr/bin/python3", "-c", "pass"])
    env = contained_child_env(prepared.env, tmp_path, ROOT)
    assert SECRET not in env.values()
    assert "KRAKEN_API_SECRET" not in env
    assert "AUREON_SUPABASE_JWT_SECRET" not in env
    assert env["AUREON_LLM_OFFLINE"] == "1"
    assert env["AUREON_OPERATOR_ENV"] == "test"
    assert str(tmp_path / "thoughts.jsonl") == env["AUREON_THOUGHT_BUS_PATH"]
    assert scrubbed_child_env(tmp_path)["HOME"] == str(tmp_path)


def test_committed_receipt_keeps_the_release_hold() -> None:
    if not RECEIPT.is_file() or not RECEIPT_MD.is_file():
        pytest.fail("multi-user smoke receipt was not written")
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    text = RECEIPT.read_text(encoding="utf-8")
    assert SECRET not in text
    assert "sk-stage9" not in text
    assert receipt_names_are_safe(text) == []
    digests = receipt["child"]["canary_sha256"]
    assert set(digests) == {
        "canary_control_sha256",
        "canary_prompt_a_sha256",
        "canary_prompt_b_absent_sha256",
        "canary_prompt_b_sha256",
        "canary_prompt_a_revoked_sha256",
        "canary_prompt_b_still_sha256",
        "canary_tenant_a_sha256",
        "canary_tenant_b_sha256",
        "canary_signer_sha256",
        "canary_operator_sha256",
    }
    assert all(len(value) == 64 and set(value) <= set("0123456789abcdef") for value in digests.values())
    assert receipt["schema"] == "aureon.measured.multi-user-smoke.v1"
    assert receipt["stage"] == 9
    assert receipt["verdict"] in {"pass", "hold", "skip", "fail"}
    assert receipt["go_live_clear"] is False
    assert receipt["go_live_receipt"] is None
    assert receipt["release_boundary"] == "HOLD"
    assert receipt["pin"] == public_pin(ROOT)
    assert receipt["pin_changed"] is False
    assert receipt["containment_pin"] == PIN
    assert receipt["orders_placed"] is False
    assert receipt["live_trading"] is False
    assert receipt["listener_bound"] is False
    assert receipt["started_from"] == STARTED_FROM
    assert receipt["cold_boot_command"] == "python -m aureon.containment.multi_user_smoke"
    memory = receipt["shared_memory"]
    assert memory["dev_shm_preexisting_read"] is False
    assert "No universal shared-memory-leak claim" in memory["claim"]
    for name, digest in receipt["source_sha256"].items():
        assert _sha256(ROOT / name) == digest
    for name, digest in receipt["unchanged_sha256"].items():
        assert _sha256(ROOT / name) == digest
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    parent = subprocess.run(
        ["git", "rev-parse", "HEAD^"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    allowed = {head}
    if parent.returncode == 0:
        allowed.add(parent.stdout.strip())
    assert receipt["git_head_at_measurement"] in allowed
    markdown = RECEIPT_MD.read_text(encoding="utf-8")
    assert f"**{receipt['verdict']}**" in markdown
    assert "not a supported public runtime" in markdown
    assert "go_live_clear" in markdown
    runbook = (ROOT / "docs" / "runbooks" / "GO_LIVE_HARDENING.md").read_text(encoding="utf-8")
    assert "Receipts 2–5 remain HOLD" in runbook or "Receipts 2, 3, 4, and 5 remain HOLD" in runbook
    assert "release%20boundary-HOLD-orange" in (ROOT / "README.md").read_text(encoding="utf-8")


def test_live_contained_smoke_matches_the_committed_receipt(monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("flask")
    monkeypatch.setenv("KRAKEN_API_SECRET", SECRET)
    monkeypatch.setenv("AUREON_CONTAINMENT_ALLOW_NETWORK", "1")
    if shutil.which("unshare") is None:
        pytest.skip("unshare is not on PATH")
    if not RECEIPT.is_file():
        pytest.fail("multi-user smoke receipt was not written")
    committed = json.loads(RECEIPT.read_text(encoding="utf-8"))
    if committed["verdict"] == "skip":
        pytest.skip("; ".join(committed["failures"]))
    from aureon.containment.multi_user_smoke import measure

    fresh = measure(repo_root(), timeout=180)
    blob = json.dumps(fresh)
    assert SECRET not in blob
    assert "sk-stage9" not in blob
    assert fresh["verdict"] == committed["verdict"]
    assert fresh["go_live_clear"] is False
    assert fresh["pin_changed"] is False
    assert fresh["cold_boot_argv_has_net"] is True
    assert fresh["orders_placed"] is False
    child_ns = fresh["child_net_ns"]
    assert child_ns and child_ns != fresh["parent_net_ns"]


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()
