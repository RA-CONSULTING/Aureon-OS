"""Opt-in seccomp and landlock on the contained cold boot.

Kernels without landlock must still pass: the report says the layer was
not applied, and that result is a gap rather than a pass.
"""

from __future__ import annotations

import ast
import errno
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from aureon.containment.hardening import (
    FILTER_DENY,
    PUBLISHED_PIN,
    SECCOMP_RET_ALLOW,
    STARTED_FROM,
    build_seccomp_program,
    fs_handled_access,
    judge_hardening,
    measure,
    prepare_hardened_launch,
    published_pin,
    repo_root,
    run_filter,
)
from aureon.containment.native import prepare_launch

ROOT = Path(__file__).resolve().parents[1]
MEASURED = ROOT / "reports" / "measured" / "containment_hardening.json"
BASE = "0726a325ac934ed2e8d2d18d5c69c31fbfafc666"
SECRET = "super-secret-kraken"
_UNTOUCHED = (
    "aureon/containment/__init__.py",
    "aureon/containment/__main__.py",
    "aureon/containment/_child_probe.py",
    "aureon/containment/_child_wrapper.py",
    "aureon/containment/cold_boot.py",
    "aureon/containment/native.py",
    "docs/runbooks/GO_LIVE_HARDENING.md",
    "reports/measured/native_process_containment.json",
    "reports/measured/native_process_containment.md",
    "mcp/aureon_public/guard_loader.py",
)


def _denied_probe(err: int = errno.EPERM) -> dict[str, object]:
    return {"ok": False, "errno": err, "error": errno.errorcode.get(err, str(err)), "contents_recorded": False}


def _readable() -> dict[str, object]:
    return {"ok": True, "readable": True, "errno": None, "error": None, "contents_recorded": False}


def _unreadable(err: int = errno.EACCES) -> dict[str, object]:
    return {
        "ok": False,
        "readable": False,
        "errno": err,
        "error": errno.errorcode.get(err, str(err)),
        "contents_recorded": False,
    }


def _holding_probes() -> dict[str, dict[str, object]]:
    return {
        "ptrace": _denied_probe(),
        "mount": _denied_probe(),
        "kexec_load": _denied_probe(),
        "bpf": _denied_probe(),
        "raw_socket": {**_denied_probe(), "sent": False},
        "stream_socket": {"ok": True, "errno": None, "error": None, "sent": False},
        "read_checkout": _readable(),
        "write_temp": {"ok": True, "errno": None, "error": None},
        "read_etc_passwd": _unreadable(),
        "read_outside": _unreadable(),
        "read_proc": _unreadable(),
    }


def _applied_seccomp() -> dict[str, object]:
    return {
        "applied": True,
        "gap": False,
        "proc_seccomp": "2",
        "deny_raw_socket": True,
        "reason": None,
        "denied": ["ptrace", "mount", "kexec_load", "bpf"],
    }


def _applied_landlock() -> dict[str, object]:
    return {"applied": True, "gap": False, "abi": 6, "scoped": "not handled", "reason": None}


def test_filter_denies_the_named_syscalls_and_only_raw_sockets() -> None:
    program = build_seccomp_program("x86_64", deny_raw_socket=True)
    assert program is not None
    assert program.arch_name == "AUDIT_ARCH_X86_64"
    for name in ("ptrace", "mount", "umount2", "pivot_root", "kexec_load", "kexec_file_load", "bpf", "mount_setattr"):
        assert name in program.denied
        assert run_filter(program, arch=program.audit_arch, nr=program.probe_syscalls.get(name, _nr(name))) == FILTER_DENY
    assert "socket" not in program.denied
    assert run_filter(program, arch=program.audit_arch, nr=41, arg1=3) == FILTER_DENY
    assert run_filter(program, arch=program.audit_arch, nr=41, arg1=3 | 0x80000) == FILTER_DENY
    assert run_filter(program, arch=program.audit_arch, nr=41, arg1=1) == SECCOMP_RET_ALLOW
    assert run_filter(program, arch=program.audit_arch, nr=41, arg1=2) == SECCOMP_RET_ALLOW
    assert run_filter(program, arch=program.audit_arch, nr=0) == SECCOMP_RET_ALLOW
    assert run_filter(program, arch=0x40000003, nr=101) == FILTER_DENY
    open_net = build_seccomp_program("x86_64", deny_raw_socket=False)
    assert open_net is not None
    assert open_net.deny_raw_socket is False
    assert run_filter(open_net, arch=open_net.audit_arch, nr=41, arg1=3) == SECCOMP_RET_ALLOW
    assert run_filter(open_net, arch=open_net.audit_arch, nr=101) == FILTER_DENY


def _nr(name: str) -> int:
    numbers = {
        "ptrace": 101,
        "mount": 165,
        "umount2": 166,
        "pivot_root": 155,
        "kexec_load": 246,
        "kexec_file_load": 320,
        "bpf": 321,
        "mount_setattr": 442,
    }
    return numbers[name]


def test_aarch64_table_is_explicit_and_unknown_machines_do_not_guess() -> None:
    program = build_seccomp_program("aarch64", deny_raw_socket=True)
    assert program is not None
    assert program.audit_arch == 0xC00000B7
    assert run_filter(program, arch=program.audit_arch, nr=117) == FILTER_DENY
    assert run_filter(program, arch=program.audit_arch, nr=198, arg1=3) == FILTER_DENY
    assert run_filter(program, arch=program.audit_arch, nr=198, arg1=1) == SECCOMP_RET_ALLOW
    assert build_seccomp_program("mips64", deny_raw_socket=True) is None


def test_landlock_mask_follows_the_reported_abi() -> None:
    assert fs_handled_access(0) == 0
    abi1 = fs_handled_access(1)
    assert abi1 & (1 << 14) == 0
    assert abi1 & (1 << 15) == 0
    assert fs_handled_access(3) & (1 << 14)
    assert fs_handled_access(6) & (1 << 15)
    assert fs_handled_access(6) & (1 << 1)


def test_kernel_without_landlock_is_a_gap_not_a_pass() -> None:
    judged = judge_hardening(
        {
            "seccomp": _applied_seccomp(),
            "landlock": {
                "applied": False,
                "gap": True,
                "errno": errno.ENOSYS,
                "error": "ENOSYS",
                "reason": "kernel does not implement landlock",
            },
            "probes": {
                **_holding_probes(),
                "read_etc_passwd": _readable(),
                "read_outside": _readable(),
                "read_proc": _readable(),
            },
        }
    )
    assert judged["seccomp_applied"] is True
    assert judged["landlock_applied"] is False
    assert judged["fs_isolation"] is False
    assert judged["verdict"] == "gap"
    assert judged["verdict"] != "pass"
    assert any(item["layer"] == "landlock" for item in judged["gaps"])
    assert any(item["layer"] == "fs_isolation" for item in judged["gaps"])
    assert judged["probes"]["read_etc_passwd"]["blocked_by_filter"] is False
    assert judged["probes"]["ptrace"]["blocked_by_filter"] is True
    assert judged["failures"] == []


def test_eperm_without_seccomp_is_not_a_filter_pass() -> None:
    judged = judge_hardening(
        {
            "seccomp": {
                "applied": False,
                "gap": True,
                "errno": errno.ENOSYS,
                "error": "ENOSYS",
                "reason": "kernel does not implement seccomp",
                "deny_raw_socket": True,
            },
            "landlock": {
                "applied": False,
                "gap": True,
                "errno": errno.EOPNOTSUPP,
                "error": "EOPNOTSUPP",
                "reason": "kernel has landlock disabled",
            },
            "probes": _holding_probes(),
        }
    )
    assert judged["seccomp_applied"] is False
    assert judged["landlock_applied"] is False
    assert judged["fs_isolation"] is False
    assert judged["verdict"] == "gap"
    assert judged["probes"]["ptrace"]["blocked_by_filter"] is False
    assert judged["probes"]["read_etc_passwd"]["blocked_by_filter"] is False


def test_a_violation_that_succeeds_is_a_failure() -> None:
    probes = _holding_probes()
    probes["ptrace"] = {"ok": True, "errno": None, "error": None}
    judged = judge_hardening({"seccomp": _applied_seccomp(), "landlock": _applied_landlock(), "probes": probes})
    assert judged["verdict"] == "fail"
    assert judged["seccomp_applied"] is True
    assert any("ptrace" in item for item in judged["failures"])


def test_landlock_without_a_boundary_is_not_isolation() -> None:
    probes = _holding_probes()
    probes["read_etc_passwd"] = _readable()
    judged = judge_hardening({"seccomp": _applied_seccomp(), "landlock": _applied_landlock(), "probes": probes})
    assert judged["landlock_applied"] is True
    assert judged["fs_isolation"] is False
    assert judged["verdict"] == "fail"
    assert judged["probes"]["read_etc_passwd"]["blocked_by_filter"] is False


def test_both_layers_and_the_boundary_are_a_pass() -> None:
    judged = judge_hardening(
        {"seccomp": _applied_seccomp(), "landlock": _applied_landlock(), "probes": _holding_probes()}
    )
    assert judged["verdict"] == "pass"
    assert judged["seccomp_applied"] is True
    assert judged["landlock_applied"] is True
    assert judged["fs_isolation"] is True
    assert judged["failures"] == []
    assert judged["gaps"] == []
    assert judged["residuals"]
    assert judged["probes"]["stream_socket"]["blocked_by_filter"] is False
    assert judged["probes"]["raw_socket"]["blocked_by_filter"] is True


def test_child_entry_does_not_import_aureon() -> None:
    child = (ROOT / "aureon" / "containment" / "_harden_child.py").read_text(encoding="utf-8")
    source = (ROOT / "aureon" / "containment" / "hardening.py").read_text(encoding="utf-8")
    assert "import aureon" not in child
    assert "from aureon" not in child
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("aureon"):
            raise AssertionError(node.module)
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("aureon")
    assert '"go_live_clear": False' in source
    assert '"go_live_clear": True' not in source
    assert "go_live_clear\": true" not in source
    assert f'PUBLISHED_PIN = "{PUBLISHED_PIN}"' in source


def test_prepare_matches_the_cold_boot_namespace_and_drops_the_parent_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    if shutil.which("unshare") is None:
        pytest.skip("unshare is not on PATH")
    monkeypatch.setenv("AUREON_CONTAINMENT_ALLOW_NETWORK", "1")
    monkeypatch.setenv("KRAKEN_API_SECRET", SECRET)
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    (checkout / "README.md").write_text("readme", encoding="utf-8")
    temp = tmp_path / "temp"
    temp.mkdir()
    outside = tmp_path / "outside"
    outside.write_bytes(b"x")
    cold = prepare_launch(tmp_path / "cold", [sys.executable, "-I", "-c", "pass"])
    hardened = prepare_hardened_launch(
        tmp_path / "launch",
        checkout=checkout,
        temp=temp,
        outside_probe=outside,
    )
    assert hardened.argv[: hardened.argv.index(sys.executable)] == cold.argv[: cold.argv.index(sys.executable)]
    assert "--net" in hardened.argv
    assert str(ROOT / "aureon" / "containment" / "_harden_child.py") in hardened.argv
    assert "_child_wrapper.py" not in " ".join(hardened.argv)
    assert hardened.drop_caps is False
    assert "KRAKEN_API_SECRET" not in hardened.env
    assert SECRET not in hardened.env.values()
    assert all(not name.startswith("AUREON_") for name in hardened.env)
    sidecar = json.loads(hardened.sidecar.read_text(encoding="utf-8"))
    assert sidecar["deny_network"] is True
    assert sidecar["filter"]["deny_raw_socket"] is True
    assert "ptrace" in sidecar["filter"]["denied"]


def test_receipt_1_pin_and_runbook_are_untouched() -> None:
    guard = (ROOT / "mcp" / "aureon_public" / "guard_loader.py").read_text(encoding="utf-8")
    assert f'PINNED_COMMIT = "{PUBLISHED_PIN}"' in guard
    assert published_pin(ROOT) == PUBLISHED_PIN
    assert STARTED_FROM == BASE
    status = subprocess.run(
        ["git", "status", "--porcelain", "--", *_UNTOUCHED, "reports/measured/baseline", "docs/runbooks/GO_LIVE_HARDENING.md"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert status.stdout.strip() == ""
    for rel in _UNTOUCHED:
        recorded = subprocess.run(["git", "show", f"{BASE}:{rel}"], cwd=ROOT, capture_output=True, check=False)
        assert recorded.returncode == 0
        assert (ROOT / rel).read_bytes() == recorded.stdout


def test_live_report_matches_what_the_kernel_applied(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KRAKEN_API_SECRET", SECRET)
    monkeypatch.setenv("AUREON_CONTAINMENT_ALLOW_NETWORK", "1")
    if shutil.which("unshare") is None or sys.platform != "linux":
        pytest.skip("unshare cold boot is not available")
    receipt = measure(repo_root())
    blob = json.dumps(receipt)
    assert SECRET not in blob
    assert receipt["schema"] == "aureon.measured.containment-hardening.v1"
    assert receipt["go_live_clear"] is False
    assert receipt["pin"] == PUBLISHED_PIN
    assert receipt["pin_changed"] is False
    assert receipt["release_boundary"] == "HOLD"
    assert receipt["live_trading"] is False
    assert receipt["orders_placed"] is False
    assert receipt["market_data_fetched"] is False
    assert receipt["rewrites_receipt_1"] is False
    assert receipt["opt_in"] is True
    assert receipt["optional_dependency"] is None
    assert receipt["cold_boot_argv_has_net"] is True
    assert receipt["seccomp_applied"] is (receipt.get("seccomp") or {}).get("applied")
    assert receipt["landlock_applied"] is (receipt.get("landlock") or {}).get("applied")
    if receipt["verdict"] == "skip":
        pytest.skip("; ".join(item["statement"] for item in receipt["gaps"]))
    if not receipt["seccomp_applied"]:
        assert receipt["verdict"] != "pass"
        assert any(item["layer"] == "seccomp" for item in receipt["gaps"])
        assert receipt["probes"]["ptrace"]["blocked_by_filter"] is False
    else:
        for name in ("ptrace", "mount", "kexec_load", "bpf", "raw_socket"):
            assert receipt["probes"][name]["ok"] is False
            assert receipt["probes"][name]["errno"] == errno.EPERM
            assert receipt["probes"][name]["blocked_by_filter"] is True
        assert receipt["probes"]["stream_socket"]["ok"] is True
        assert receipt["probes"]["raw_socket"]["sent"] is False
        caps = receipt.get("caps_before_landlock") or {}
        assert caps.get("CapEff") not in {None, "0000000000000000"}
    if not receipt["landlock_applied"]:
        assert receipt["fs_isolation"] is False
        assert receipt["verdict"] != "pass"
        assert any(item["layer"] == "landlock" for item in receipt["gaps"])
        assert any(item["layer"] == "fs_isolation" for item in receipt["gaps"])
        assert receipt["probes"]["read_etc_passwd"]["blocked_by_filter"] is False
    else:
        assert receipt["fs_isolation"] is True
        assert receipt["probes"]["read_checkout"]["readable"] is True
        assert receipt["probes"]["read_checkout"]["contents_recorded"] is False
        assert receipt["probes"]["write_temp"]["ok"] is True
        assert receipt["probes"]["read_etc_passwd"]["readable"] is False
        assert receipt["probes"]["read_etc_passwd"]["errno"] == errno.EACCES
        assert receipt["probes"]["read_outside"]["readable"] is False
        assert receipt["probes"]["read_proc"]["readable"] is False
        assert receipt["landlock"]["checkout_access"] == (1 | 4 | 8)
        assert receipt["landlock"]["temp_access"] & (1 << 1)
    if receipt["seccomp_applied"] and receipt["landlock_applied"]:
        assert receipt["verdict"] == "pass"
        assert receipt["fs_isolation"] is True
        assert receipt["failures"] == []


def test_committed_hardening_report_is_honest() -> None:
    if not MEASURED.is_file():
        pytest.fail("containment hardening measurement was not written")
    receipt = json.loads(MEASURED.read_text(encoding="utf-8"))
    text = MEASURED.read_text(encoding="utf-8")
    assert SECRET not in text
    assert "go_live_clear\": true" not in text
    assert receipt["schema"] == "aureon.measured.containment-hardening.v1"
    assert receipt["go_live_clear"] is False
    assert receipt["pin"] == PUBLISHED_PIN
    assert receipt["pin_changed"] is False
    assert receipt["release_boundary"] == "HOLD"
    assert receipt["orders_placed"] is False
    assert receipt["live_trading"] is False
    assert receipt["market_data_fetched"] is False
    assert receipt["rewrites_receipt_1"] is False
    assert receipt["started_from"] == STARTED_FROM
    assert receipt["verdict"] in {"pass", "gap", "fail", "skip"}
    if not receipt["landlock_applied"]:
        assert receipt["fs_isolation"] is False
        assert receipt["verdict"] != "pass"
        assert any(item["layer"] == "landlock" for item in receipt["gaps"])
    if not receipt["seccomp_applied"]:
        assert receipt["verdict"] != "pass"
        assert any(item["layer"] == "seccomp" for item in receipt["gaps"])
    if receipt["seccomp_applied"] and receipt["landlock_applied"]:
        assert receipt["fs_isolation"] is True
        assert receipt["verdict"] == "pass"
    for name, digest in receipt["source_sha256"].items():
        assert _sha256(ROOT / name) == digest
    assert (ROOT / "docs" / "runbooks" / "GO_LIVE_HARDENING.md").read_text(encoding="utf-8")
    assert "native_process_containment.json" in (ROOT / "docs" / "runbooks" / "GO_LIVE_HARDENING.md").read_text(
        encoding="utf-8"
    )


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()
