"""Opt-in seccomp and landlock on the contained cold boot.

Kernels without landlock must still pass: the report says the layer was
not applied, and that result is a gap rather than a pass.
"""

from __future__ import annotations

import ast
import errno
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from aureon.containment.hardening import (
    EXPECTED_PIN,
    FILTER_DENY,
    SECCOMP_RET_ALLOW,
    STARTED_FROM,
    ContainmentInProcessRefused,
    apply_landlock,
    apply_no_new_privs,
    apply_seccomp,
    build_seccomp_program,
    execute,
    fs_handled_access,
    judge_hardening,
    measure,
    opt_in_decision,
    prepare_hardened_launch,
    published_pin,
    repo_root,
    run_filter,
)
from aureon.containment.native import prepare_launch

from tests.support.receipt_provenance import is_ancestor

ROOT = Path(__file__).resolve().parents[1]
MEASURED = ROOT / "reports" / "measured" / "containment_hardening.json"
BASE = "821c8f83123d25ab5b0fbb395d4c76c6a5000e54"
_STAGE7 = (
    "aureon/containment/__init__.py",
    "aureon/containment/__main__.py",
    "aureon/containment/_child_probe.py",
    "aureon/containment/_child_wrapper.py",
    "aureon/containment/cold_boot.py",
    "aureon/containment/native.py",
    "reports/measured/native_process_containment.json",
    "reports/measured/native_process_containment.md",
)
_BAD_DEFAULT_CLAIMS = (
    "default boot is seccomp-hardened",
    "default boot is landlock-hardened",
    "default cold boot is seccomp",
    "default cold boot is landlock",
    "stage-7 cold boot is seccomp",
    "stage-7 cold boot is landlock",
    "cold boot is seccomp-hardened",
    "cold boot is landlock-hardened",
    "seccomp-hardened by default",
    "landlock-hardened by default",
)
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
    assert f'EXPECTED_PIN = "{EXPECTED_PIN}"' in source


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
    live = published_pin(ROOT)
    assert f'PINNED_COMMIT = "{live}"' in guard
    assert EXPECTED_PIN == "bb04503119681adcf832f3c3e9b0cbf09fc7a938"
    assert live != EXPECTED_PIN
    assert STARTED_FROM == BASE
    status = subprocess.run(
        ["git", "status", "--porcelain", "--", *_UNTOUCHED, "reports/measured/baseline", "docs/runbooks/GO_LIVE_HARDENING.md"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert status.stdout.strip() == ""
    # guard_loader.py moved with the published pin after BASE. native.py is
    # relabelled in this change; the stage-7 receipt is not rewritten.
    allowed_drift = {
        "aureon/containment/native.py",
        "mcp/aureon_public/guard_loader.py",
    }
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    # Skip when BASE is not in this clone (for example a --depth 1 checkout).
    assert is_ancestor(BASE, head)
    for rel in _UNTOUCHED:
        recorded = subprocess.run(["git", "show", f"{BASE}:{rel}"], cwd=ROOT, capture_output=True, check=False)
        assert recorded.returncode == 0
        if rel in allowed_drift:
            assert (ROOT / rel).read_bytes() != recorded.stdout
        else:
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
    assert receipt["pin"] == published_pin(ROOT)
    assert receipt["published_pin_expected"] == EXPECTED_PIN
    assert receipt["pin_changed"] is True
    assert receipt["pin"] != EXPECTED_PIN
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
    assert receipt["continued_without_layer"] is False
    assert receipt["default_boot_hardened"] is False
    assert receipt["closes_receipt_1"] is False
    assert receipt["closes_source_boundary"] is False
    assert receipt["kernel_release"] == os.uname().release
    if receipt["seccomp_applied"] and receipt["landlock_applied"]:
        assert receipt["verdict"] == "pass"
        assert receipt["fs_isolation"] is True
        assert receipt["failures"] == []
        assert receipt["refused"] is False
        assert receipt["missing_layers"] == []
        assert receipt["child_returncode"] == 0
        assert receipt["landlock_abi"] == receipt["landlock"]["abi"]
    else:
        assert receipt["refused"] is True
        assert receipt["child_returncode"] not in {0, None}
        assert receipt["verdict"] != "pass"


def test_committed_hardening_report_is_honest() -> None:
    if not MEASURED.is_file():
        pytest.fail("containment hardening measurement was not written")
    receipt = json.loads(MEASURED.read_text(encoding="utf-8"))
    text = MEASURED.read_text(encoding="utf-8")
    assert SECRET not in text
    assert "go_live_clear\": true" not in text
    assert receipt["schema"] == "aureon.measured.containment-hardening.v1"
    assert receipt["go_live_clear"] is False
    assert receipt["pin"] == EXPECTED_PIN
    assert receipt["published_pin_expected"] == EXPECTED_PIN
    assert receipt["pin_changed"] is False
    assert receipt["release_boundary"] == "HOLD"
    assert receipt["orders_placed"] is False
    assert receipt["live_trading"] is False
    assert receipt["market_data_fetched"] is False
    assert receipt["rewrites_receipt_1"] is False
    assert receipt["closes_receipt_1"] is False
    assert receipt["closes_source_boundary"] is False
    assert receipt["default_boot_hardened"] is False
    assert receipt["opt_in"] is True
    assert receipt["kernel_release"] == "6.12.113+"
    assert "6.12.113+" in receipt["kernel"]
    assert receipt["landlock_abi"] == 6
    assert receipt["landlock"]["abi"] == 6
    note = receipt["measurement_note"]
    assert "opt-in" in note
    assert "one VM kernel" in note
    assert "does not install these layers" in note
    assert "does not close receipt 1" in note
    assert "does not close the source boundary" in note
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
    historical_hardening = "084416f1704f309937945cf1b685c9361d9d3b2e9d80c5e6e6e26d5076ea2bf9"
    assert receipt["source_sha256"]["aureon/containment/hardening.py"] == historical_hardening
    assert _sha256(ROOT / "aureon/containment/hardening.py") != historical_hardening
    for name, digest in receipt["source_sha256"].items():
        if name == "aureon/containment/hardening.py":
            continue
        assert _sha256(ROOT / name) == digest
    assert (ROOT / "docs" / "runbooks" / "GO_LIVE_HARDENING.md").read_text(encoding="utf-8")
    assert "native_process_containment.json" in (ROOT / "docs" / "runbooks" / "GO_LIVE_HARDENING.md").read_text(
        encoding="utf-8"
    )


def test_opted_in_run_refuses_when_the_kernel_lacks_a_layer(tmp_path: Path) -> None:
    missing_seccomp = {"applied": False, "gap": True, "reason": "kernel does not implement seccomp"}
    missing_landlock = {"applied": False, "gap": True, "reason": "kernel does not implement landlock"}
    decision = opt_in_decision(missing_seccomp, missing_landlock)
    assert decision["refused"] is True
    assert decision["exit_code"] != 0
    assert decision["continued_without_layer"] is False
    assert decision["missing_layers"] == ["seccomp", "landlock"]
    only_landlock = opt_in_decision({"applied": True}, missing_landlock)
    assert only_landlock["refused"] is True
    assert only_landlock["missing_layers"] == ["landlock"]
    assert only_landlock["continued_without_layer"] is False
    judged = judge_hardening(
        {"seccomp": missing_seccomp, "landlock": missing_landlock, "probes": _holding_probes(), "refused": True}
    )
    assert judged["verdict"] == "gap"
    assert judged["verdict"] != "pass"
    assert judged["seccomp_applied"] is False
    assert judged["landlock_applied"] is False

    program = build_seccomp_program("x86_64", deny_raw_socket=True)
    assert program is not None
    spec = {
        "temp": str(tmp_path),
        "checkout": str(tmp_path),
        "checkout_probe": str(tmp_path / "README.md"),
        "outside_probe": str(tmp_path / "outside"),
        "drop_caps": False,
        "filter": {
            "arch_name": program.arch_name,
            "seccomp_nr": program.seccomp_nr,
            "instructions": [list(item) for item in program.instructions],
            "denied": list(program.denied),
            "deny_raw_socket": True,
        },
        "landlock_syscalls": dict(program.landlock_syscalls),
        "probe_syscalls": dict(program.probe_syscalls),
    }
    script = (
        "import errno, json, sys\n"
        "import aureon.containment.hardening as hardening\n"
        "hardening._syscall = lambda *_args, **_kwargs: (-1, errno.ENOSYS)\n"
        "report = hardening.execute(json.loads(sys.stdin.read()))\n"
        "sys.stdout.write(json.dumps(report))\n"
    )
    done = subprocess.run(
        [sys.executable, "-c", script],
        input=json.dumps(spec),
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    report = json.loads(done.stdout)
    assert report["seccomp"]["applied"] is False
    assert report["seccomp"]["gap"] is True
    assert "does not implement seccomp" in str(report["seccomp"]["reason"])
    assert report["landlock"]["applied"] is False
    assert report["landlock"]["gap"] is True
    assert "does not implement landlock" in str(report["landlock"]["reason"])
    assert report["refused"] is True
    assert report["continued_without_layer"] is False
    assert report["exit_code"] != 0
    assert report["missing_layers"] == ["seccomp", "landlock"]
    assert judge_hardening(report)["verdict"] != "pass"


def test_stage7_is_byte_identical_to_main_when_the_layer_is_off(tmp_path: Path) -> None:
    if shutil.which("unshare") is not None:
        prepared = prepare_launch(tmp_path, [sys.executable, "-I", "-c", "pass"])
        joined = " ".join(prepared.argv)
        assert "_harden_child.py" not in joined
        assert "hardening.py" not in joined
        assert "--net" in prepared.argv
        sidecar = json.loads(prepared.sidecar.read_text(encoding="utf-8"))
        assert sidecar["schema"] == "aureon.containment.launch.v1"
        assert "filter" not in sidecar
        assert "landlock" not in sidecar
        assert "seccomp" not in sidecar
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    # Skip when BASE is not in this clone (for example a --depth 1 checkout).
    assert is_ancestor(BASE, head)
    for rel in _STAGE7:
        recorded = subprocess.run(["git", "show", f"{BASE}:{rel}"], cwd=ROOT, capture_output=True, check=False)
        assert recorded.returncode == 0, rel
        if rel == "aureon/containment/native.py":
            # Relabel only; the committed stage-7 receipt is not rewritten.
            assert (ROOT / rel).read_bytes() != recorded.stdout, rel
        else:
            assert (ROOT / rel).read_bytes() == recorded.stdout, rel


def test_denied_syscall_returns_eperm_at_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    """The deny list is not the proof. The contained process must see EPERM."""

    monkeypatch.setenv("KRAKEN_API_SECRET", SECRET)
    if shutil.which("unshare") is None or sys.platform != "linux":
        pytest.skip("unshare cold boot is not available")
    receipt = measure(repo_root())
    if receipt["verdict"] == "skip":
        pytest.skip("; ".join(item["statement"] for item in receipt["gaps"]))
    if not receipt["seccomp_applied"]:
        pytest.skip("this kernel did not apply seccomp")
    probe = receipt["probes"]["ptrace"]
    assert "ptrace" in receipt["seccomp"]["denied"]
    assert probe["request"] == "PTRACE_TRACEME"
    assert probe["ok"] is False
    assert probe["errno"] == errno.EPERM
    assert probe["blocked_by_filter"] is True
    assert receipt["probes"]["raw_socket"]["errno"] == errno.EPERM
    assert receipt["probes"]["raw_socket"]["sent"] is False
    assert receipt["probes"]["stream_socket"]["ok"] is True


def test_default_boot_is_not_described_as_hardened() -> None:
    paths = [ROOT / "README.md"]
    paths.extend((ROOT / "docs" / "runbooks").rglob("*.md"))
    paths.extend((ROOT / "reports" / "measured").glob("*.md"))
    paths.extend((ROOT / "reports" / "measured").glob("*.json"))
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="replace").lower()
        for phrase in _BAD_DEFAULT_CLAIMS:
            assert phrase not in text, f"{path} says the default boot is hardened"
    receipt = json.loads(MEASURED.read_text(encoding="utf-8"))
    note = receipt["measurement_note"]
    assert receipt["opt_in"] is True
    assert receipt["default_boot_hardened"] is False
    assert "opt-in" in note
    assert "one VM kernel" in note
    assert "6.12.113+" in receipt["kernel_release"]


def test_pytest_process_cannot_install_the_layer() -> None:
    """Installing the layer here would sandbox every later test on this worker."""

    with pytest.raises(ContainmentInProcessRefused):
        apply_no_new_privs()
    with pytest.raises(ContainmentInProcessRefused):
        apply_seccomp({"seccomp_nr": 317, "instructions": [[6, 0, 0, 0x7FFF0000]], "denied": [], "deny_raw_socket": False})
    with pytest.raises(ContainmentInProcessRefused):
        apply_landlock(
            {
                "checkout": "/tmp",
                "temp": "/tmp",
                "landlock_syscalls": {"create": 444, "add": 445, "restrict": 446},
            }
        )
    with pytest.raises(ContainmentInProcessRefused):
        execute({})
    assert "Seccomp:\t0" in Path("/proc/self/status").read_text(encoding="ascii")


def test_pytest_process_is_unrestricted_after_the_layer_tests() -> None:
    """This test stays last in the module so it runs after the layer tests.

    Seccomp and landlock cannot be cleared. The pytest process must still
    be unrestricted: Seccomp 0, no new privs, and a path outside the
    checkout readable and writable.
    """

    fields: dict[str, str] = {}
    for line in Path("/proc/self/status").read_text(encoding="ascii").splitlines():
        if line.startswith(("Seccomp", "NoNewPrivs")):
            key, value = line.split(":", 1)
            fields[key] = value.strip()
    assert fields.get("Seccomp") == "0"
    assert fields.get("Seccomp_filters", "0") == "0"
    assert fields.get("NoNewPrivs") == "0"
    with open("/etc/passwd", "rb") as handle:
        assert handle.read(1)
    probe = Path("/tmp") / f"aureon-unrestricted-{os.getpid()}"
    probe.write_bytes(b"x")
    try:
        assert probe.read_bytes() == b"x"
    finally:
        probe.unlink()


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()
