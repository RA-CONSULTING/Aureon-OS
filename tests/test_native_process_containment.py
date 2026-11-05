"""Stage 7: native cold boot defaults to a network namespace with no route."""

from __future__ import annotations

import errno
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from aureon.containment.cold_boot import judge_default, measure, repo_root
from aureon.containment.native import (
    PIN,
    STARTED_FROM,
    ContainmentRefused,
    NetworkAllowGrant,
    authorize_network_allow,
    prepare_launch,
    scrubbed_child_env,
    verify_grant,
)

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "reports" / "measured" / "native_process_containment.json"
RECEIPT_MD = ROOT / "reports" / "measured" / "native_process_containment.md"
SECRET = "super-secret-kraken"


def test_public_pin_and_orange_badge_stay() -> None:
    guard = (ROOT / "mcp" / "aureon_public" / "guard_loader.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    installer = (ROOT / "scripts" / "linux" / "install-linux.sh").read_text(encoding="utf-8")
    assert f'PINNED_COMMIT = "{PIN}"' in guard
    assert "release%20boundary-HOLD-orange" in readme
    assert "protected_bootstrap_v05.py" in installer
    assert "aureon.containment" not in installer
    assert STARTED_FROM == "c68a89d2a184d99582bb24310b91e024323a212c"


def test_deny_argv_keeps_net_even_if_the_environment_asks(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AUREON_CONTAINMENT_ALLOW_NETWORK", "1")
    monkeypatch.setenv("KRAKEN_API_SECRET", SECRET)
    if shutil.which("unshare") is None:
        pytest.skip("unshare is not on PATH")
    prepared = prepare_launch(tmp_path, ["/usr/bin/python3", "-I", "-c", "pass"])
    assert "--net" in prepared.argv
    assert prepared.deny_network is True
    assert prepared.drop_caps is True
    assert "KRAKEN_API_SECRET" not in prepared.env
    assert SECRET not in prepared.env.values()
    assert all(not name.startswith("AUREON_") for name in prepared.env)


def test_allow_grant_omits_net_and_rejects_a_forged_id(tmp_path: Path) -> None:
    if shutil.which("unshare") is None:
        pytest.skip("unshare is not on PATH")
    grant = authorize_network_allow(
        "unit test of the audited allow path",
        "stage7-test",
        issued_at="2026-11-05T00:00:00Z",
    )
    prepared = prepare_launch(tmp_path, ["/usr/bin/python3", "-c", "pass"], grant=grant)
    assert "--net" not in prepared.argv
    assert "--user" in prepared.argv
    assert prepared.grant_id == grant.grant_id
    assert prepared.drop_caps is False
    forged = NetworkAllowGrant(grant_id="0" * 64, audit=dict(grant.audit))
    with pytest.raises(ContainmentRefused):
        verify_grant(forged)
    with pytest.raises(ContainmentRefused):
        authorize_network_allow("short", "stage7-test")
    with pytest.raises(ContainmentRefused):
        authorize_network_allow("unit test of the audited allow path\n", "stage7-test")


def test_scrubbed_env_is_not_the_parent(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("BINANCE_API_KEY", SECRET)
    env = scrubbed_child_env(tmp_path)
    assert "BINANCE_API_KEY" not in env
    assert env["HOME"] == str(tmp_path)


def test_judge_fails_closed_when_the_namespace_is_missing() -> None:
    judged = judge_default({"started": False, "probe": None}, "net:[1]")
    assert judged["verdict"] == "fail"
    assert judged["allowed_at_default"] == "unproven"


def test_judge_fails_when_outbound_connect_succeeds() -> None:
    probe = _passing_probe()
    probe["probes"]["tcp_1.1.1.1_443"] = {"ok": True, "errno": None}
    judged = judge_default({"started": True, "probe": probe, "wrapper": _wrapper()}, "net:[1]")
    assert judged["verdict"] == "fail"
    assert any("tcp_1.1.1.1_443" in item for item in judged["failures"])


def test_judge_passes_a_zero_route_probe() -> None:
    judged = judge_default(
        {"started": True, "probe": _passing_probe(), "wrapper": _wrapper()},
        "net:[1]",
    )
    assert judged["verdict"] == "pass"
    assert judged["allowed_at_default"] == "none"
    assert judged["failures"] == []


def test_allow_probe_source_does_not_connect() -> None:
    from aureon.containment.cold_boot import _ALLOW_PROBE

    assert "socket" not in _ALLOW_PROBE
    assert '"connect_attempted": False' in _ALLOW_PROBE


def test_wrapper_refuses_an_environment_allow(tmp_path: Path) -> None:
    wrapper = ROOT / "aureon" / "containment" / "_child_wrapper.py"
    sidecar = tmp_path / "sidecar.json"
    status = tmp_path / "status.json"
    marker = tmp_path / "ran"
    payload = tmp_path / "payload.py"
    payload.write_text(f"open({str(marker)!r}, 'w').write('ran')\n", encoding="utf-8")
    sidecar.write_text(
        json.dumps(
            {
                "argv": ["/usr/bin/python3", str(payload)],
                "deny_network": True,
                "drop_caps": False,
                "status_path": str(status),
            }
        ),
        encoding="utf-8",
    )
    done = subprocess.run(
        ["/usr/bin/python3", "-I", str(wrapper), str(sidecar)],
        cwd=tmp_path,
        env={"AUREON_CONTAINMENT_ALLOW_NETWORK": "1", "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert done.returncode == 2
    assert not marker.exists()
    assert "environment variable cannot select network" in done.stdout


def test_live_cold_boot_defaults_to_no_route(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KRAKEN_API_SECRET", SECRET)
    monkeypatch.setenv("AUREON_CONTAINMENT_ALLOW_NETWORK", "1")
    if shutil.which("unshare") is None:
        pytest.skip("unshare is not on PATH")
    receipt = measure(repo_root())
    blob = json.dumps(receipt)
    assert SECRET not in blob
    if receipt["verdict"] == "skip":
        pytest.skip("; ".join(receipt["failures"]))
    assert receipt["verdict"] == "pass", receipt["failures"]
    assert receipt["allowed_at_default"] == "none"
    assert receipt["cold_boot_argv_has_net"] is True
    assert receipt["orders_placed"] is False
    assert receipt["live_trading"] is False
    assert receipt["market_data_fetched"] is False
    assert receipt["pin_changed"] is False
    assert receipt["pin"] == PIN
    assert receipt["release_boundary"] == "HOLD"
    assert receipt["allow_path"]["taken_for_default_boot"] is False
    assert receipt["allow_path"]["probe_connect_attempted"] is False
    assert receipt["allow_path"]["probe_net_ns_equals_parent"] is True
    assert receipt["allow_path"]["argv_omits_net"] is True
    child = receipt["default_child"]["probe"]
    assert child["net_ns"] != receipt["parent_net_ns"]
    assert child["probes"]["tcp_1.1.1.1_443"]["errno"] == errno.ENETUNREACH
    assert child["probes"]["tcp_127.0.0.1_9"]["errno"] == errno.ENETUNREACH
    assert [item["id"] for item in receipt["holds_remaining"]] == [2, 3, 4, 5]


def test_committed_receipt_matches_this_tree() -> None:
    if not RECEIPT.is_file() or not RECEIPT_MD.is_file():
        pytest.fail("cold-boot receipt was not written")
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    text = RECEIPT.read_text(encoding="utf-8")
    assert SECRET not in text
    assert receipt["schema"] == "aureon.measured.native-process-containment.v1"
    assert receipt["stage"] == 7
    assert receipt["receipt"] == 1
    assert receipt["verdict"] in {"pass", "skip", "fail"}
    assert receipt["pin"] == PIN
    assert receipt["pin_changed"] is False
    assert receipt["orders_placed"] is False
    assert receipt["live_trading"] is False
    assert receipt["started_from"] == STARTED_FROM
    assert receipt["cold_boot_command"] == "python -m aureon.containment.cold_boot"
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
    allowed_heads = {head}
    if parent.returncode == 0:
        allowed_heads.add(parent.stdout.strip())
    assert receipt["git_head_at_measurement"] in allowed_heads
    if receipt["verdict"] == "pass":
        assert receipt["allowed_at_default"] == "none"
        assert receipt["cold_boot_argv_has_net"] is True
        assert "--net" in receipt["cold_boot_argv"]
    md = RECEIPT_MD.read_text(encoding="utf-8")
    assert "not a claim that the system is alive" in md
    assert f"**{receipt['verdict']}**" in md
    runbook = (ROOT / "docs" / "runbooks" / "GO_LIVE_HARDENING.md").read_text(encoding="utf-8")
    assert "native_process_containment.json" in runbook
    assert "Receipts 2–5 remain HOLD" in runbook or "Receipts 2, 3, 4, and 5 remain HOLD" in runbook
    assert "release%20boundary-HOLD-orange" in (ROOT / "README.md").read_text(encoding="utf-8")


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _blocked(name: str = "tcp") -> dict[str, object]:
    return {"ok": False, "errno": errno.ENETUNREACH, "error": "ENETUNREACH", "host": name}


def _passing_probe() -> dict[str, object]:
    return {
        "socket_monkeypatch": False,
        "socket_module": "socket",
        "net_ns": "net:[2]",
        "interfaces_proc_net_dev": ["lo"],
        "default_route_ifaces": [],
        "sysfs_net": ["lo"],
        "lo_before": {"ok": True, "up": False, "flags": 8},
        "caps": {"CapEff": "0000000000000000"},
        "lo_up_attempt": {"ok": False, "errno": errno.EPERM, "error": "EPERM"},
        "probes": {
            "tcp_1.1.1.1_443": _blocked(),
            "tcp_127.0.0.1_9": _blocked(),
            "udp_8.8.8.8_53": _blocked(),
            "libc_connect_1.1.1.1_443": _blocked(),
            "tcp_1.1.1.1_443_after_socket_reload": _blocked(),
            "tcp6_2001:4860:4860::8888_53": _blocked(),
            "raw_icmp_create": {"ok": False, "errno": errno.EPERM, "error": "EPERM"},
        },
    }


def _wrapper() -> dict[str, object]:
    return {"sysfs_remount": {"ok": True}, "sysfs_before": ["lo", "eth0"]}
