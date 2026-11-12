"""Opt-in seccomp and landlock for one contained cold boot.

The default stage-7 cold boot does not install these layers. Receipt 1 is
not rewritten here, and this measurement does not close receipt 1 or the
source boundary. This module is a separate opt-in launch: the same
``unshare`` user, mount, pid, and network namespace, then two best-effort
layers installed in the child with ``ctypes`` and the kernel syscalls.
An opted-in run that cannot apply a layer reports it missing and exits
non-zero. It does not continue as a successful hardened boot.

The seccomp layer is a default-allow classic BPF filter. It returns
``EPERM`` for ``ptrace``, ``mount`` and the sibling mount syscalls that
would bypass it, ``kexec_load`` and ``kexec_file_load``, and ``bpf``.
When the network namespace has no route, it also denies ``socket`` with
``SOCK_RAW`` (including ``SOCK_CLOEXEC``). Stream and datagram sockets
stay allowed.

The landlock layer allows the checkout read-only and one temp directory
read-write. It is installed only when ``landlock_create_ruleset`` reports
an ABI. A kernel that does not implement a layer is reported as not
applied. That is a gap, not a pass. ``fs_isolation`` is true only when
landlock applied and the probes showed the boundary.

No third-party package is imported. ``libseccomp`` is not required.
``go_live_clear`` stays false. The live published pin is not written.
"""

from __future__ import annotations

import ctypes
import errno
import hashlib
import json
import os
import re
import signal
import socket
import subprocess
import sys
import tempfile
import traceback
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

STARTED_FROM = "821c8f83123d25ab5b0fbb395d4c76c6a5000e54"
# Pin expected at this module's last measurement. Historical. Not the live
# published pin. pin_changed is true when the live guard-loader pin differs.
EXPECTED_PIN = "bb04503119681adcf832f3c3e9b0cbf09fc7a938"

_CHILD = Path(__file__).with_name("_harden_child.py")
_PIN_RE = re.compile(r'^PINNED_COMMIT = "([0-9a-f]{40})"', re.MULTILINE)
_SOURCE_FILES = (
    "aureon/containment/_harden_child.py",
    "aureon/containment/hardening.py",
)

# linux/filter.h and linux/seccomp.h. Classic BPF, not eBPF.
_BPF_LD = 0x00
_BPF_ALU = 0x04
_BPF_JMP = 0x05
_BPF_RET = 0x06
_BPF_W = 0x00
_BPF_ABS = 0x20
_BPF_JEQ = 0x10
_BPF_K = 0x00
_BPF_AND = 0x50
_LD_W_ABS = _BPF_LD | _BPF_W | _BPF_ABS
_JMP_JEQ = _BPF_JMP | _BPF_JEQ | _BPF_K
_ALU_AND = _BPF_ALU | _BPF_AND | _BPF_K
_RET_K = _BPF_RET | _BPF_K

SECCOMP_RET_ALLOW = 0x7FFF0000
SECCOMP_RET_ERRNO = 0x00050000
FILTER_DENY = SECCOMP_RET_ERRNO | errno.EPERM
_SECCOMP_SET_MODE_FILTER = 1
_SECCOMP_FILTER_FLAG_TSYNC = 1
_PR_SET_NO_NEW_PRIVS = 38
_PR_CAPBSET_DROP = 24
_CAPABILITY_VERSION_3 = 0x20080522

# linux/landlock.h. ABI 6 adds scope, which is not a filesystem bit.
_LANDLOCK_CREATE_RULESET_VERSION = 1
_LANDLOCK_RULE_PATH_BENEATH = 1
_FS_EXECUTE = 1 << 0
_FS_WRITE_FILE = 1 << 1
_FS_READ_FILE = 1 << 2
_FS_READ_DIR = 1 << 3
_FS_ABI1 = 0x1FFF
_FS_REFER = 1 << 13
_FS_TRUNCATE = 1 << 14
_FS_IOCTL_DEV = 1 << 15
_CHECKOUT_ACCESS = _FS_EXECUTE | _FS_READ_FILE | _FS_READ_DIR
_SOCK_RAW = 3
_SOCK_TYPE_MASK = 0xF
_SOCK_CLOEXEC = 0x80000

# Names the filter always denies. mount_setattr, umount2, and pivot_root
# are the same filesystem-namespace hazard as mount. kexec_file_load is
# the same hazard as kexec_load. socket is not in this list: only SOCK_RAW
# is denied, and only when the caller asked for it.
_DENY_NAMES = (
    "ptrace",
    "mount",
    "umount2",
    "pivot_root",
    "mount_setattr",
    "kexec_load",
    "kexec_file_load",
    "bpf",
)
_PROBE_SYSCALLS = ("ptrace", "mount", "kexec_load", "bpf")
_AUDIT_ARCH_X86_64 = 0xC000003E
_AUDIT_ARCH_AARCH64 = 0xC00000B7

_Instruction = list[int]


@dataclass(frozen=True)
class _Arch:
    machine: str
    audit_name: str
    audit: int
    seccomp_nr: int
    landlock_create: int
    landlock_add: int
    landlock_restrict: int
    syscalls: Mapping[str, int]


# Numbers from asm/unistd_64.h and asm-generic/unistd.h (aarch64).
_X86_64 = _Arch(
    machine="x86_64",
    audit_name="AUDIT_ARCH_X86_64",
    audit=_AUDIT_ARCH_X86_64,
    seccomp_nr=317,
    landlock_create=444,
    landlock_add=445,
    landlock_restrict=446,
    syscalls={
        "socket": 41,
        "ptrace": 101,
        "pivot_root": 155,
        "mount": 165,
        "umount2": 166,
        "kexec_load": 246,
        "kexec_file_load": 320,
        "bpf": 321,
        "mount_setattr": 442,
    },
)
_AARCH64 = _Arch(
    machine="aarch64",
    audit_name="AUDIT_ARCH_AARCH64",
    audit=_AUDIT_ARCH_AARCH64,
    seccomp_nr=277,
    landlock_create=444,
    landlock_add=445,
    landlock_restrict=446,
    syscalls={
        "socket": 198,
        "umount2": 39,
        "mount": 40,
        "pivot_root": 41,
        "kexec_load": 104,
        "ptrace": 117,
        "bpf": 280,
        "kexec_file_load": 294,
        "mount_setattr": 442,
    },
)
_ARCH_BY_MACHINE = {
    "x86_64": _X86_64,
    "amd64": _X86_64,
    "aarch64": _AARCH64,
    "arm64": _AARCH64,
}

_LIBC: ctypes.CDLL | None = None


@dataclass(frozen=True)
class SeccompProgram:
    """One installable default-allow filter. Instructions are ``(code, jt, jf, k)``."""

    machine: str
    arch_name: str
    audit_arch: int
    seccomp_nr: int
    instructions: tuple[tuple[int, int, int, int], ...]
    denied: tuple[str, ...]
    deny_raw_socket: bool
    landlock_syscalls: Mapping[str, int]
    probe_syscalls: Mapping[str, int]


@dataclass(frozen=True)
class PreparedHardening:
    """Argv for one opt-in hardened cold boot. The env is not the parent env."""

    argv: tuple[str, ...]
    env: Mapping[str, str]
    sidecar: Path
    status_path: Path
    deny_network: bool
    drop_caps: bool
    checkout: Path
    temp: Path


class _SockFilter(ctypes.Structure):
    _fields_ = [
        ("code", ctypes.c_uint16),
        ("jt", ctypes.c_uint8),
        ("jf", ctypes.c_uint8),
        ("k", ctypes.c_uint32),
    ]


class _SockFprog(ctypes.Structure):
    # Natural alignment puts 6 bytes of padding after ``len`` on 64-bit,
    # which is the kernel's ``struct sock_fprog`` layout. Do not pack this.
    _fields_ = [
        ("len", ctypes.c_uint16),
        ("filter", ctypes.POINTER(_SockFilter)),
    ]


class _LandlockAttr(ctypes.Structure):
    _fields_ = [("handled_access_fs", ctypes.c_uint64)]


class _LandlockPath(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("allowed_access", ctypes.c_uint64),
        ("parent_fd", ctypes.c_int32),
    ]


class _CapHeader(ctypes.Structure):
    _fields_ = [("version", ctypes.c_uint32), ("pid", ctypes.c_int)]


class _CapData(ctypes.Structure):
    _fields_ = [
        ("effective", ctypes.c_uint32),
        ("permitted", ctypes.c_uint32),
        ("inheritable", ctypes.c_uint32),
    ]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def published_pin(root: Path | None = None) -> str:
    """The pin in the public guard loader. This function does not write it."""

    text = ((root or repo_root()) / "mcp" / "aureon_public" / "guard_loader.py").read_text(encoding="utf-8")
    match = _PIN_RE.search(text)
    if match is None:
        raise RuntimeError("PINNED_COMMIT is missing from the public guard loader")
    return match.group(1)


def _libc() -> ctypes.CDLL:
    global _LIBC
    if _LIBC is None:
        libc = ctypes.CDLL(None, use_errno=True)
        libc.syscall.restype = ctypes.c_long
        _LIBC = libc
    return _LIBC


def _error_name(err: int | None) -> str | None:
    if err is None:
        return None
    return errno.errorcode.get(err, str(err))


def _os_result(exc: OSError, **extra: Any) -> dict[str, Any]:
    return {
        "ok": False,
        "errno": exc.errno,
        "error": _error_name(exc.errno),
        **extra,
    }


def _unsupported(layer: Mapping[str, Any]) -> bool:
    """True when the layer was not applied because the kernel cannot do it."""

    if layer.get("gap") is True:
        return True
    if layer.get("error") in {"ENOSYS", "EOPNOTSUPP", "ENOTSUP"}:
        return True
    err = layer.get("errno")
    if err in {getattr(errno, "ENOSYS", 38), getattr(errno, "EOPNOTSUPP", 95)}:
        return True
    reason = str(layer.get("reason") or "").lower()
    markers = (
        "does not implement",
        "not supported",
        "disabled",
        "no syscall table",
        "unsupported",
        "not available",
    )
    return any(item in reason for item in markers)


def _ld(offset: int) -> _Instruction:
    return [_LD_W_ABS, 0, 0, offset]


def _jeq(value: int) -> _Instruction:
    return [_JMP_JEQ, 0, 0, value]


def _ret(value: int) -> _Instruction:
    return [_RET_K, 0, 0, value]


def _land(value: int) -> _Instruction:
    return [_ALU_AND, 0, 0, value]


def _link(ins: _Instruction, index: int, target: int, *, taken: bool) -> None:
    offset = target - (index + 1)
    if not 0 <= offset <= 255:
        raise ValueError(f"seccomp jump {index}->{target} does not fit in one byte")
    if taken:
        ins[1] = offset
    else:
        ins[2] = offset


def run_filter(program: SeccompProgram, *, arch: int, nr: int, arg1: int = 0) -> int:
    """Execute the subset of classic BPF this builder emits.

    The kernel runs the same instructions. This interpreter is how tests
    check the deny list without installing a filter in-process.
    """

    words = {0: nr & 0xFFFFFFFF, 4: arch & 0xFFFFFFFF, 24: arg1 & 0xFFFFFFFF}
    acc = 0
    pc = 0
    ins = program.instructions
    for _step in range(64):
        if pc < 0 or pc >= len(ins):
            raise ValueError(f"seccomp program counter left the filter at {pc}")
        code, jt, jf, k = ins[pc]
        klass = code & 0x07
        if klass == _BPF_LD:
            acc = words.get(k, 0)
            pc += 1
        elif klass == _BPF_ALU:
            acc &= k
            pc += 1
        elif klass == _BPF_JMP:
            pc = pc + 1 + (jt if acc == k else jf)
        elif klass == _BPF_RET:
            return k
        else:
            raise ValueError(f"seccomp opcode {code:#x} is not in this filter")
    raise ValueError("seccomp program did not return")


def _self_check(program: SeccompProgram, arch: _Arch) -> None:
    for name in _DENY_NAMES:
        if run_filter(program, arch=arch.audit, nr=arch.syscalls[name]) != FILTER_DENY:
            raise RuntimeError(f"seccomp filter does not deny {name}")
    socket_nr = arch.syscalls["socket"]
    raw = run_filter(program, arch=arch.audit, nr=socket_nr, arg1=_SOCK_RAW)
    cloexec = run_filter(program, arch=arch.audit, nr=socket_nr, arg1=_SOCK_RAW | _SOCK_CLOEXEC)
    stream = run_filter(program, arch=arch.audit, nr=socket_nr, arg1=socket.SOCK_STREAM)
    if program.deny_raw_socket:
        if raw != FILTER_DENY or cloexec != FILTER_DENY or stream != SECCOMP_RET_ALLOW:
            raise RuntimeError("seccomp raw-socket clause is wrong")
    elif raw != SECCOMP_RET_ALLOW:
        raise RuntimeError("seccomp denied a raw socket without being asked")
    for allowed in (0, 1, 257):
        if run_filter(program, arch=arch.audit, nr=allowed) != SECCOMP_RET_ALLOW:
            raise RuntimeError(f"seccomp filter is not default-allow (nr {allowed})")
    foreign = run_filter(program, arch=0x40000003, nr=arch.syscalls["ptrace"])
    if foreign != FILTER_DENY:
        raise RuntimeError("seccomp filter allowed a foreign audit architecture")


def build_seccomp_program(machine: str, *, deny_raw_socket: bool) -> SeccompProgram | None:
    """Return a filter for ``machine``, or ``None`` when no table exists.

    ``None`` is an honest gap. This function does not guess syscall numbers.
    """

    arch = _ARCH_BY_MACHINE.get(machine)
    if arch is None:
        return None
    program: list[_Instruction] = [_ld(4)]
    arch_jump = _jeq(arch.audit)
    arch_at = len(program)
    program.append(arch_jump)
    program.append(_ld(0))
    deny_at_index: list[int] = []
    for name in _DENY_NAMES:
        deny_at_index.append(len(program))
        program.append(_jeq(arch.syscalls[name]))
    raw_at = None
    if deny_raw_socket:
        raw_at = len(program)
        program.append(_jeq(arch.syscalls["socket"]))
    allow_at = len(program)
    program.append(_ret(SECCOMP_RET_ALLOW))
    raw_type_at = None
    if deny_raw_socket:
        program.append(_ld(24))
        program.append(_land(_SOCK_TYPE_MASK))
        raw_type_at = len(program)
        program.append(_jeq(_SOCK_RAW))
        program.append(_ret(SECCOMP_RET_ALLOW))
    deny_return = len(program)
    program.append(_ret(FILTER_DENY))
    arch_deny = len(program)
    program.append(_ret(FILTER_DENY))
    _link(program[arch_at], arch_at, arch_deny, taken=False)
    for index in deny_at_index:
        _link(program[index], index, deny_return, taken=True)
    if raw_at is not None and raw_type_at is not None:
        _link(program[raw_at], raw_at, raw_at + 1, taken=False)
        # The socket jump's taken path is the word load of argument 1,
        # which sits just after the default allow return.
        _link(program[raw_at], raw_at, allow_at + 1, taken=True)
        _link(program[raw_type_at], raw_type_at, deny_return, taken=True)
    frozen = tuple(tuple(item) for item in program)
    built = SeccompProgram(
        machine=arch.machine,
        arch_name=arch.audit_name,
        audit_arch=arch.audit,
        seccomp_nr=arch.seccomp_nr,
        instructions=frozen,
        denied=_DENY_NAMES,
        deny_raw_socket=deny_raw_socket,
        landlock_syscalls={
            "create": arch.landlock_create,
            "add": arch.landlock_add,
            "restrict": arch.landlock_restrict,
        },
        probe_syscalls={name: arch.syscalls[name] for name in _PROBE_SYSCALLS},
    )
    _self_check(built, arch)
    return built


def fs_handled_access(abi: int) -> int:
    """Filesystem rights this process knows how to handle for ``abi``.

    Unhandled rights stay allowed by the kernel. Callers record the ABI
    so a newer right is visible instead of being reported as covered.
    """

    if abi < 1:
        return 0
    mask = _FS_ABI1
    if abi >= 2:
        mask |= _FS_REFER
    if abi >= 3:
        mask |= _FS_TRUNCATE
    if abi >= 5:
        mask |= _FS_IOCTL_DEV
    return mask


def opt_in_decision(seccomp: object, landlock: object) -> dict[str, Any]:
    """Refuse an opted-in run unless every requested layer actually applied.

    A missing layer is named. ``continued_without_layer`` stays false: the
    run does not proceed as a successful hardened boot without that layer.
    """

    missing: list[str] = []
    if not isinstance(seccomp, Mapping) or seccomp.get("applied") is not True:
        missing.append("seccomp")
    if not isinstance(landlock, Mapping) or landlock.get("applied") is not True:
        missing.append("landlock")
    return {
        "refused": bool(missing),
        "missing_layers": missing,
        "continued_without_layer": False,
        "exit_code": 0 if not missing else 3,
    }


def judge_hardening(child: Mapping[str, Any]) -> dict[str, Any]:
    """Turn one child report into applied flags, probes, gaps, and a verdict.

    A layer the kernel did not apply is a gap. ``fs_isolation`` stays false
    in that case, including when ``/etc/passwd`` happens to be unreadable
    for some other reason. ``EPERM`` from a missing capability is not a
    seccomp pass.
    """

    seccomp = child.get("seccomp") if isinstance(child.get("seccomp"), Mapping) else {}
    landlock = child.get("landlock") if isinstance(child.get("landlock"), Mapping) else {}
    raw_probes = child.get("probes") if isinstance(child.get("probes"), Mapping) else {}
    seccomp_applied = seccomp.get("applied") is True
    landlock_applied = landlock.get("applied") is True
    deny_raw = seccomp.get("deny_raw_socket") is True
    gaps: list[dict[str, str]] = []
    failures: list[str] = []
    residuals: list[str] = []
    probes = {
        name: _annotate_probe(
            str(name),
            probe,
            seccomp_applied=seccomp_applied,
            landlock_applied=landlock_applied,
            deny_raw=deny_raw,
        )
        for name, probe in raw_probes.items()
    }

    if not seccomp_applied:
        statement = str(seccomp.get("reason") or "seccomp filter was not applied")
        if _unsupported(seccomp):
            gaps.append({"layer": "seccomp", "tag": "measured", "statement": statement})
        else:
            failures.append(f"seccomp was not applied: {statement}")
    else:
        for name in ("ptrace", "mount", "kexec_load", "bpf"):
            _expect_eperm(probes.get(name), name, failures)
        if deny_raw:
            _expect_eperm(probes.get("raw_socket"), "raw_socket", failures)
        stream = probes.get("stream_socket")
        if not isinstance(stream, Mapping) or stream.get("ok") is not True:
            failures.append("stream socket was denied; the filter is broader than raw sockets")

    fs_isolation = False
    if not landlock_applied:
        statement = str(landlock.get("reason") or "landlock was not applied")
        if _unsupported(landlock):
            gaps.append({"layer": "landlock", "tag": "measured", "statement": statement})
            gaps.append(
                {
                    "layer": "fs_isolation",
                    "tag": "measured",
                    "statement": (
                        "Filesystem isolation was not established. Landlock did not "
                        "apply, so a path outside the checkout staying readable is a "
                        "gap, not a pass."
                    ),
                }
            )
        else:
            failures.append(f"landlock was not applied: {statement}")
            failures.append("filesystem isolation was not established")
    else:
        fs_isolation = _filesystem_isolated(probes, failures)
        abi = landlock.get("abi")
        if isinstance(abi, int) and abi > 6:
            residuals.append(
                f"Landlock ABI {abi} is newer than the filesystem rights this ruleset names. "
                "Rights this build does not set stay allowed by the kernel."
            )
        if landlock.get("scoped") == "not handled":
            residuals.append(
                "Landlock scope controls are not installed. The ruleset is the "
                "filesystem restriction that was requested."
            )

    for probe in probes.values():
        if isinstance(probe, Mapping) and probe.get("contents_recorded") is True:
            failures.append("a filesystem probe recorded file contents")

    if failures:
        verdict = "fail"
    elif gaps:
        verdict = "gap"
    elif seccomp_applied and landlock_applied and fs_isolation:
        verdict = "pass"
    else:
        verdict = "fail"
        failures.append("hardening result was not a pass and not a documented gap")
    return {
        "seccomp_applied": seccomp_applied,
        "landlock_applied": landlock_applied,
        "fs_isolation": fs_isolation,
        "verdict": verdict,
        "failures": failures,
        "gaps": gaps,
        "residuals": residuals,
        "probes": probes,
    }


def _annotate_probe(
    name: str,
    probe: object,
    *,
    seccomp_applied: bool,
    landlock_applied: bool,
    deny_raw: bool,
) -> dict[str, Any]:
    item = dict(probe) if isinstance(probe, Mapping) else {"ok": False, "missing": True}
    syscall_denied = name in {"ptrace", "mount", "kexec_load", "bpf"} or (name == "raw_socket" and deny_raw)
    fs_denied = name in {"read_etc_passwd", "read_outside", "read_proc"}
    if syscall_denied:
        item["blocked_by_filter"] = bool(
            seccomp_applied and item.get("ok") is False and item.get("errno") == errno.EPERM
        )
    elif fs_denied:
        item["blocked_by_filter"] = bool(
            landlock_applied
            and item.get("readable") is False
            and item.get("errno") in {errno.EACCES, errno.EPERM}
        )
    else:
        item["blocked_by_filter"] = False
    return item


def _expect_eperm(probe: object, name: str, failures: list[str]) -> None:
    if not isinstance(probe, Mapping):
        failures.append(f"{name} probe is missing")
        return
    if probe.get("ok") is True or probe.get("errno") != errno.EPERM:
        failures.append(
            f"{name} was not denied with EPERM (ok={probe.get('ok')} errno={probe.get('errno')})"
        )


def _filesystem_isolated(probes: Mapping[str, Any], failures: list[str]) -> bool:
    checkout = probes.get("read_checkout") if isinstance(probes.get("read_checkout"), Mapping) else {}
    temp = probes.get("write_temp") if isinstance(probes.get("write_temp"), Mapping) else {}
    passwd = probes.get("read_etc_passwd") if isinstance(probes.get("read_etc_passwd"), Mapping) else {}
    outside = probes.get("read_outside") if isinstance(probes.get("read_outside"), Mapping) else {}
    proc = probes.get("read_proc") if isinstance(probes.get("read_proc"), Mapping) else {}
    checkout_ok = checkout.get("readable") is True
    temp_ok = temp.get("ok") is True
    passwd_denied = passwd.get("readable") is False and passwd.get("errno") in {errno.EACCES, errno.EPERM}
    outside_denied = outside.get("readable") is False and outside.get("errno") in {errno.EACCES, errno.EPERM}
    proc_denied = proc.get("readable") is False and proc.get("errno") in {errno.EACCES, errno.EPERM}
    if checkout_ok and temp_ok and passwd_denied and outside_denied and proc_denied:
        return True
    failures.append(
        "landlock applied but the filesystem probes do not show isolation "
        "to the checkout and the temp dir"
    )
    return False


def _syscall(nr: int, argtypes: Sequence[type], args: Sequence[Any]) -> tuple[int, int]:
    libc = _libc()
    libc.syscall.argtypes = [ctypes.c_long, *argtypes]
    ctypes.set_errno(0)
    rc = int(libc.syscall(nr, *args))
    return rc, ctypes.get_errno()


def _layer_error(rc: int, err: int) -> dict[str, Any]:
    failed = rc < 0
    return {
        "errno": err if failed else None,
        "error": _error_name(err) if failed else None,
    }


class ContainmentInProcessRefused(RuntimeError):
    """Seccomp and landlock cannot be cleared. They are not installed in pytest."""


def _require_hardened_child() -> None:
    """Refuse to install an irreversible layer in the pytest process.

    A worker that installs seccomp or landlock keeps it for every later
    test. The contained child is a separate process and does not import pytest.
    """

    if "pytest" in sys.modules:
        raise ContainmentInProcessRefused(
            "seccomp and landlock must be applied in a child process, not the pytest process"
        )


def apply_no_new_privs() -> dict[str, Any]:
    _require_hardened_child()
    libc = _libc()
    libc.prctl.argtypes = [ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong]
    libc.prctl.restype = ctypes.c_int
    ctypes.set_errno(0)
    rc = libc.prctl(_PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0)
    err = ctypes.get_errno()
    return {
        "ok": rc == 0,
        "errno": None if rc == 0 else err,
        "error": None if rc == 0 else _error_name(err),
    }


def _proc_status() -> dict[str, str]:
    try:
        lines = Path("/proc/self/status").read_text(encoding="ascii").splitlines()
    except OSError as exc:
        return {"error": _error_name(exc.errno) or type(exc).__name__}
    found: dict[str, str] = {}
    for line in lines:
        if line.startswith(("Cap", "Seccomp", "NoNewPrivs")):
            key, value = line.split(":", 1)
            found[key] = value.strip()
    return found


def apply_seccomp(spec: object) -> dict[str, Any]:
    """Install the sidecar filter in this process. Does not install a guess."""

    _require_hardened_child()
    if not isinstance(spec, Mapping):
        return {
            "applied": False,
            "installed": False,
            "gap": True,
            "reason": "no syscall table for this machine",
            "errno": None,
            "error": None,
            "implementation": "ctypes-seccomp-syscall",
        }
    instructions = spec.get("instructions")
    seccomp_nr = spec.get("seccomp_nr")
    base = {
        "applied": False,
        "installed": False,
        "gap": False,
        "arch": spec.get("arch_name"),
        "denied": list(spec.get("denied") or []),
        "deny_raw_socket": bool(spec.get("deny_raw_socket")),
        "action": "SECCOMP_RET_ERRNO|EPERM",
        "implementation": "ctypes-seccomp-syscall",
        "instruction_count": len(instructions) if isinstance(instructions, list) else 0,
    }
    if not isinstance(seccomp_nr, int) or not isinstance(instructions, list) or not instructions:
        base["gap"] = True
        base["reason"] = "no syscall table for this machine"
        return base
    if ctypes.sizeof(ctypes.c_void_p) == 8 and ctypes.sizeof(_SockFprog) != 16:
        base["reason"] = "sock_fprog layout is not the kernel layout"
        return base
    if ctypes.sizeof(ctypes.c_void_p) == 4 and ctypes.sizeof(_SockFprog) != 8:
        base["reason"] = "sock_fprog layout is not the kernel layout"
        return base
    filters = (_SockFilter * len(instructions))()
    for index, item in enumerate(instructions):
        if not isinstance(item, list) or len(item) != 4:
            base["reason"] = "seccomp instruction was not four integers"
            return base
        code, jt, jf, k = item
        filters[index] = _SockFilter(int(code), int(jt), int(jf), int(k) & 0xFFFFFFFF)
    prog = _SockFprog(len(instructions), filters)
    rc, err = _syscall(
        seccomp_nr,
        [ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p],
        [_SECCOMP_SET_MODE_FILTER, _SECCOMP_FILTER_FLAG_TSYNC, ctypes.byref(prog)],
    )
    if rc < 0:
        rc, err = _syscall(
            seccomp_nr,
            [ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p],
            [_SECCOMP_SET_MODE_FILTER, 0, ctypes.byref(prog)],
        )
    base.update(_layer_error(rc, err))
    if rc < 0:
        base["gap"] = err in {getattr(errno, "ENOSYS", 38), getattr(errno, "EOPNOTSUPP", 95)}
        base["reason"] = (
            "kernel does not implement seccomp"
            if base["gap"]
            else f"seccomp install failed: {base['error']}"
        )
        return base
    base["installed"] = True
    return base


def _confirm_seccomp(layer: dict[str, Any], status: Mapping[str, str]) -> dict[str, Any]:
    proc = status.get("Seccomp")
    layer["proc_seccomp"] = proc
    if layer.get("installed") is True and proc == "2":
        layer["applied"] = True
        layer["gap"] = False
        layer["reason"] = None
        return layer
    if layer.get("installed") is True:
        layer["applied"] = False
        layer["gap"] = False
        layer["reason"] = "seccomp syscall returned success but /proc/self/status Seccomp was not 2"
    return layer


def apply_landlock(spec: Mapping[str, Any]) -> dict[str, Any]:
    """Restrict this process to the checkout and the temp dir, when the ABI exists."""

    _require_hardened_child()
    numbers = spec.get("landlock_syscalls")
    checkout = str(spec.get("checkout") or "")
    temp = str(spec.get("temp") or "")
    base: dict[str, Any] = {
        "applied": False,
        "gap": False,
        "abi": None,
        "errno": None,
        "error": None,
        "reason": None,
        "checkout": checkout,
        "temp": temp,
        "scoped": "not handled",
        "implementation": "ctypes-landlock-syscall",
    }
    if not isinstance(numbers, Mapping):
        base["gap"] = True
        base["reason"] = "no syscall table for this machine"
        return base
    try:
        create_nr = int(numbers["create"])
        add_nr = int(numbers["add"])
        restrict_nr = int(numbers["restrict"])
    except (KeyError, TypeError, ValueError):
        base["gap"] = True
        base["reason"] = "no syscall table for this machine"
        return base
    abi, err = _syscall(
        create_nr,
        [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint],
        [None, 0, _LANDLOCK_CREATE_RULESET_VERSION],
    )
    if abi < 1:
        base.update(_layer_error(abi, err))
        base["gap"] = err in {getattr(errno, "ENOSYS", 38), getattr(errno, "EOPNOTSUPP", 95)}
        base["reason"] = (
            "kernel does not implement landlock"
            if err == getattr(errno, "ENOSYS", 38)
            else "kernel has landlock disabled"
            if err == getattr(errno, "EOPNOTSUPP", 95)
            else f"landlock ABI query failed: {_error_name(err)}"
        )
        return base
    handled = fs_handled_access(abi)
    base["abi"] = abi
    base["handled_access_fs"] = handled
    if handled == 0:
        base["reason"] = "landlock ABI did not yield a filesystem mask"
        return base
    if not Path(checkout).is_dir() or not Path(temp).is_dir():
        base["reason"] = "checkout or temp path is not a directory"
        return base
    checkout_access = _CHECKOUT_ACCESS & handled
    if checkout_access == 0:
        base["reason"] = "checkout access mask was empty"
        return base
    attr = _LandlockAttr(handled)
    ruleset, err = _syscall(
        create_nr,
        [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint],
        [ctypes.byref(attr), ctypes.sizeof(attr), 0],
    )
    if ruleset < 0:
        base.update(_layer_error(ruleset, err))
        base["gap"] = err in {getattr(errno, "ENOSYS", 38), getattr(errno, "EOPNOTSUPP", 95)}
        base["reason"] = (
            "kernel does not implement landlock" if base["gap"] else f"landlock_create_ruleset failed: {_error_name(err)}"
        )
        return base
    added: list[dict[str, Any]] = []
    try:
        for role, path, access in (
            ("checkout", checkout, checkout_access),
            ("temp", temp, handled),
        ):
            try:
                parent = os.open(path, os.O_PATH | os.O_CLOEXEC)
            except OSError as exc:
                base.update({"errno": exc.errno, "error": _error_name(exc.errno)})
                base["reason"] = f"{role} path could not be opened"
                return base
            rule = _LandlockPath(access, parent)
            try:
                rc, add_err = _syscall(
                    add_nr,
                    [ctypes.c_int, ctypes.c_int, ctypes.c_void_p, ctypes.c_uint],
                    [ruleset, _LANDLOCK_RULE_PATH_BENEATH, ctypes.byref(rule), 0],
                )
            finally:
                os.close(parent)
            added.append({"role": role, "access": access, "rc": rc, "errno": None if rc == 0 else add_err})
            if rc < 0:
                base["errno"] = add_err
                base["error"] = _error_name(add_err)
                base["reason"] = f"landlock_add_rule failed for {role}: {_error_name(add_err)}"
                base["rules"] = added
                return base
        rc, restrict_err = _syscall(restrict_nr, [ctypes.c_int, ctypes.c_uint], [ruleset, 0])
    finally:
        os.close(ruleset)
    base["rules"] = added
    base["checkout_access"] = checkout_access
    base["temp_access"] = handled
    if rc < 0:
        base.update(_layer_error(rc, restrict_err))
        base["reason"] = f"landlock_restrict_self failed: {_error_name(restrict_err)}"
        base["gap"] = restrict_err in {getattr(errno, "ENOSYS", 38), getattr(errno, "EOPNOTSUPP", 95)}
        return base
    base["applied"] = True
    base["gap"] = False
    base["reason"] = None
    return base


def drop_caps() -> dict[str, Any]:
    """Drop the capability bounding set and the effective set. Best effort."""

    libc = _libc()
    libc.prctl.argtypes = [ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong]
    libc.prctl.restype = ctypes.c_int
    dropped = 0
    invalid = 0
    for cap in range(64):
        ctypes.set_errno(0)
        rc = libc.prctl(_PR_CAPBSET_DROP, cap, 0, 0, 0)
        if rc == 0:
            dropped += 1
        elif ctypes.get_errno() == errno.EINVAL:
            invalid += 1
        else:
            err = ctypes.get_errno()
            return {
                "ok": False,
                "errno": err,
                "error": _error_name(err),
                "dropped": dropped,
            }
    header = _CapHeader(_CAPABILITY_VERSION_3, 0)
    data = (_CapData * 2)()
    libc.capset.argtypes = [ctypes.POINTER(_CapHeader), ctypes.c_void_p]
    libc.capset.restype = ctypes.c_int
    ctypes.set_errno(0)
    rc = libc.capset(ctypes.byref(header), ctypes.cast(data, ctypes.c_void_p))
    err = ctypes.get_errno()
    return {
        "ok": rc == 0,
        "errno": None if rc == 0 else err,
        "error": None if rc == 0 else _error_name(err),
        "dropped": dropped,
        "invalid_cap_numbers": invalid,
    }


def _probe_ptrace(nr: int) -> dict[str, Any]:
    pid = os.fork()
    if pid == 0:
        try:
            rc, err = _syscall(
                nr,
                [ctypes.c_long, ctypes.c_long, ctypes.c_long, ctypes.c_long],
                [0, 0, 0, 0],
            )
        except Exception:
            os._exit(124)
        if rc >= 0:
            os._exit(0)
        os._exit(err if 0 < err < 125 else 124)
    try:
        _wpid, status = os.waitpid(pid, 0)
    except OSError as exc:
        return _os_result(exc, request="PTRACE_TRACEME")
    if os.WIFEXITED(status):
        code = os.WEXITSTATUS(status)
        if code == 0:
            return {"ok": True, "errno": None, "error": None, "request": "PTRACE_TRACEME"}
        return {
            "ok": False,
            "errno": code,
            "error": _error_name(code),
            "request": "PTRACE_TRACEME",
        }
    if os.WIFSTOPPED(status):
        os.kill(pid, signal.SIGKILL)
        os.waitpid(pid, 0)
        return {
            "ok": True,
            "errno": None,
            "error": None,
            "request": "PTRACE_TRACEME",
            "stopped": True,
        }
    return {"ok": False, "errno": None, "error": "signaled", "request": "PTRACE_TRACEME"}


def _probe_mount(target: str) -> dict[str, Any]:
    libc = _libc()
    libc.mount.argtypes = [
        ctypes.c_char_p,
        ctypes.c_char_p,
        ctypes.c_char_p,
        ctypes.c_ulong,
        ctypes.c_void_p,
    ]
    libc.mount.restype = ctypes.c_int
    ctypes.set_errno(0)
    rc = libc.mount(b"none", os.fsencode(target), b"tmpfs", 0, None)
    err = ctypes.get_errno()
    if rc == 0:
        libc.umount2.argtypes = [ctypes.c_char_p, ctypes.c_int]
        libc.umount2.restype = ctypes.c_int
        libc.umount2(os.fsencode(target), 0)
    return {
        "ok": rc == 0,
        "errno": None if rc == 0 else err,
        "error": None if rc == 0 else _error_name(err),
        "fstype": "tmpfs",
    }


def _probe_kexec(nr: int) -> dict[str, Any]:
    rc, err = _syscall(
        nr,
        [ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong],
        [0, 0, 0, 0],
    )
    return {
        "ok": rc >= 0,
        "errno": None if rc >= 0 else err,
        "error": None if rc >= 0 else _error_name(err),
        "segments": 0,
    }


def _probe_bpf(nr: int) -> dict[str, Any]:
    rc, err = _syscall(nr, [ctypes.c_int, ctypes.c_void_p, ctypes.c_uint], [5, None, 0])
    return {
        "ok": rc >= 0,
        "errno": None if rc >= 0 else err,
        "error": None if rc >= 0 else _error_name(err),
        "cmd": "BPF_PROG_LOAD",
        "loaded": False,
    }


def _probe_socket(kind: str) -> dict[str, Any]:
    try:
        if kind == "raw":
            sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
        else:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except OSError as exc:
        return _os_result(exc, sent=False)
    sock.close()
    return {"ok": True, "errno": None, "error": None, "sent": False}


def _probe_read(path: str) -> dict[str, Any]:
    try:
        fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC)
    except OSError as exc:
        return _os_result(exc, readable=False, contents_recorded=False)
    try:
        os.read(fd, 1)
    finally:
        os.close(fd)
    return {
        "ok": True,
        "readable": True,
        "errno": None,
        "error": None,
        "contents_recorded": False,
    }


def _probe_write(path: str) -> dict[str, Any]:
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, 0o600)
    except OSError as exc:
        return _os_result(exc)
    try:
        os.write(fd, b"x")
    finally:
        os.close(fd)
    return {"ok": True, "errno": None, "error": None}


def _run_probes(spec: Mapping[str, Any], mount_point: str) -> dict[str, Any]:
    numbers = spec.get("probe_syscalls") if isinstance(spec.get("probe_syscalls"), Mapping) else {}

    def need(name: str) -> int | None:
        value = numbers.get(name)
        return value if isinstance(value, int) else None

    probes: dict[str, Any] = {}
    ptrace_nr = need("ptrace")
    probes["ptrace"] = (
        _probe_ptrace(ptrace_nr)
        if ptrace_nr is not None
        else {"ok": False, "errno": None, "error": "no syscall number", "request": "PTRACE_TRACEME"}
    )
    probes["mount"] = _probe_mount(mount_point) if mount_point else {"ok": False, "errno": None, "error": "no mount point"}
    kexec_nr = need("kexec_load")
    probes["kexec_load"] = (
        _probe_kexec(kexec_nr) if kexec_nr is not None else {"ok": False, "errno": None, "error": "no syscall number"}
    )
    bpf_nr = need("bpf")
    probes["bpf"] = _probe_bpf(bpf_nr) if bpf_nr is not None else {"ok": False, "errno": None, "error": "no syscall number"}
    probes["raw_socket"] = _probe_socket("raw")
    probes["stream_socket"] = _probe_socket("stream")
    checkout_probe = str(spec.get("checkout_probe") or "")
    outside_probe = str(spec.get("outside_probe") or "")
    temp = str(spec.get("temp") or "")
    probes["read_checkout"] = _probe_read(checkout_probe) if checkout_probe else {"ok": False, "readable": False}
    probes["write_temp"] = _probe_write(str(Path(temp) / "isolation-write")) if temp else {"ok": False}
    probes["read_etc_passwd"] = _probe_read("/etc/passwd")
    probes["read_outside"] = _probe_read(outside_probe) if outside_probe else {"ok": False, "readable": False}
    probes["read_proc"] = _probe_read("/proc/self/status")
    return probes


def execute(spec: Mapping[str, Any]) -> dict[str, Any]:
    """Install the sidecar policy in this process, then probe it.

    Call this only in the contained child. The filters stay installed
    for the rest of the process. A pytest process is refused before any
    irreversible call.
    """

    _require_hardened_child()
    temp = str(spec.get("temp") or "")
    mount_point = str(Path(temp) / "mount-probe") if temp else ""
    if mount_point:
        os.makedirs(mount_point, exist_ok=True)
    no_new = apply_no_new_privs()
    seccomp = apply_seccomp(spec.get("filter"))
    status = _proc_status()
    seccomp = _confirm_seccomp(seccomp, status)
    # Landlock closes /proc. Read Seccomp before restricting the filesystem.
    landlock = apply_landlock(spec)
    probes = _run_probes(spec, mount_point)
    if spec.get("drop_caps") is True:
        cap_drop = drop_caps()
        cap_drop["before_probes"] = False
    else:
        cap_drop = {"ok": False, "skipped": True, "before_probes": False}
    decision = opt_in_decision(seccomp, landlock)
    return {
        "schema": "aureon.containment.hardening-probe.v1",
        "no_new_privs": no_new,
        "seccomp": seccomp,
        "landlock": landlock,
        "cap_drop": cap_drop,
        "caps_before_landlock": {key: status.get(key) for key in ("CapEff", "CapPrm", "CapBnd", "NoNewPrivs")},
        "euid": os.geteuid(),
        "probes": probes,
        "refused": decision["refused"],
        "missing_layers": decision["missing_layers"],
        "continued_without_layer": False,
        "exit_code": decision["exit_code"],
    }


def child_main() -> int:
    if len(sys.argv) != 2:
        sys.stderr.write("hardening child expects the sidecar path\n")
        return 2
    sidecar = sys.argv[1]
    try:
        spec = json.loads(Path(sidecar).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"sidecar unreadable: {type(exc).__name__}\n")
        return 2
    if not isinstance(spec, dict):
        sys.stderr.write("sidecar is not an object\n")
        return 2
    try:
        report = execute(spec)
    except Exception as exc:
        traceback.print_exc()
        report = {
            "schema": "aureon.containment.hardening-probe.v1",
            "seccomp": {
                "applied": False,
                "gap": False,
                "reason": f"child failed before a report: {type(exc).__name__}",
            },
            "landlock": {
                "applied": False,
                "gap": False,
                "reason": f"child failed before a report: {type(exc).__name__}",
            },
            "probes": {},
            "refused": True,
            "missing_layers": ["seccomp", "landlock"],
            "continued_without_layer": False,
            "exit_code": 1,
        }
    payload = json.dumps(report, sort_keys=True)
    sys.stdout.write(payload)
    status_path = spec.get("status_path")
    if isinstance(status_path, str) and status_path:
        try:
            Path(status_path).write_text(payload, encoding="utf-8")
        except OSError:
            pass
    return int(report.get("exit_code") or 0)


def _machine() -> str:
    return os.uname().machine if hasattr(os, "uname") else ""


def prepare_hardened_launch(
    work: Path,
    *,
    checkout: Path,
    temp: Path | None = None,
    deny_network: bool = True,
    drop_caps: bool = False,
    checkout_probe: Path | None = None,
    outside_probe: Path | None = None,
) -> PreparedHardening:
    """Write the sidecar and return the ``unshare`` command.

    ``os.environ`` is not consulted. An environment variable cannot turn
    the network namespace off or on. ``drop_caps`` defaults to false so a
    measurement can attribute ``EPERM`` to the filter. The capability drop
    runs after the probes when it is requested.
    """

    from aureon.containment.native import ContainmentUnavailable, scrubbed_child_env, unshare_path

    unshare = unshare_path()
    if unshare is None:
        raise ContainmentUnavailable("unshare is not on PATH")
    checkout = checkout.resolve()
    temp_dir = (temp or work).resolve()
    probe = (checkout_probe or (checkout / "README.md")).resolve()
    if outside_probe is None:
        raise ValueError("outside_probe is required")
    outside = outside_probe.resolve()
    if not checkout.is_dir():
        raise ValueError("checkout is not a directory")
    if not probe.is_relative_to(checkout):
        raise ValueError("checkout probe is outside the checkout")
    if outside.is_relative_to(checkout) or outside.is_relative_to(temp_dir):
        raise ValueError("outside probe must sit outside the checkout and the temp dir")
    temp_dir.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    program = build_seccomp_program(_machine(), deny_raw_socket=deny_network)
    sidecar = work / "sidecar.json"
    status_path = temp_dir / "status.json"
    spec: dict[str, Any] = {
        "schema": "aureon.containment.harden-launch.v1",
        "checkout": str(checkout),
        "temp": str(temp_dir),
        "checkout_probe": str(probe),
        "outside_probe": str(outside),
        "deny_network": deny_network,
        "drop_caps": drop_caps,
        "status_path": str(status_path),
        "filter": None
        if program is None
        else {
            "arch_name": program.arch_name,
            "audit_arch": program.audit_arch,
            "seccomp_nr": program.seccomp_nr,
            "instructions": [list(item) for item in program.instructions],
            "denied": list(program.denied),
            "deny_raw_socket": program.deny_raw_socket,
        },
        "landlock_syscalls": None if program is None else dict(program.landlock_syscalls),
        "probe_syscalls": None if program is None else dict(program.probe_syscalls),
    }
    sidecar.write_text(json.dumps(spec, sort_keys=True), encoding="utf-8")
    flags = [
        unshare,
        "--user",
        "--map-root-user",
        "--mount",
        "--propagation",
        "private",
        "--pid",
        "--fork",
        "--mount-proc",
    ]
    if deny_network:
        flags.append("--net")
    argv = [*flags, sys.executable, "-I", str(_CHILD.resolve()), str(sidecar.resolve())]
    return PreparedHardening(
        argv=tuple(argv),
        env=scrubbed_child_env(temp_dir),
        sidecar=sidecar,
        status_path=status_path,
        deny_network=deny_network,
        drop_caps=drop_caps,
        checkout=checkout,
        temp=temp_dir,
    )


def _git_head(root: Path) -> str | None:
    try:
        done = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if done.returncode != 0:
        return None
    text = done.stdout.strip()
    return text if len(text) == 40 else None


def _worktree_dirty(root: Path) -> bool | None:
    try:
        done = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if done.returncode != 0:
        return None
    return bool(done.stdout.strip())


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _file_hashes(root: Path) -> dict[str, str]:
    return {name: _sha256(root / name) for name in _SOURCE_FILES}


def _envelope(root: Path, started: str) -> dict[str, Any]:
    pin = published_pin(root)
    return {
        "schema": "aureon.measured.containment-hardening.v1",
        "title": "opt-in seccomp and landlock on the contained cold boot",
        "opt_in": True,
        "default_boot_hardened": False,
        "closes_receipt_1": False,
        "closes_source_boundary": False,
        "rewrites_receipt_1": False,
        "kernel_release": os.uname().release if hasattr(os, "uname") else None,
        "go_live_clear": False,
        "pin": pin,
        "pin_changed": pin != EXPECTED_PIN,
        "published_pin_expected": EXPECTED_PIN,
        "release_boundary": "HOLD",
        "orange_badge": "unchanged",
        "live_trading": False,
        "orders_placed": False,
        "market_data_fetched": False,
        "implementation": "ctypes",
        "optional_dependency": None,
        "started_from": STARTED_FROM,
        "git_head_at_measurement": _git_head(root),
        "worktree_dirty_at_measurement": _worktree_dirty(root),
        "source_sha256": _file_hashes(root),
        "kernel": " ".join(os.uname()) if hasattr(os, "uname") else sys.platform,
        "python": sys.version.split()[0],
        "started_at": started,
        "capability_drop_before_probes": False,
        "capability_drop_note": (
            "This measurement leaves capabilities in place so EPERM from ptrace, "
            "mount, kexec_load, bpf, or a raw socket is the seccomp filter. "
            "Receipt 1 already measured the capability drop. drop_caps is "
            "optional and, when requested, runs after the probes."
        ),
        "measurement_note": (
            "This is opt-in and was measured on one VM kernel. "
            "The default stage-7 cold boot does not install these layers. "
            "seccomp_applied and landlock_applied are what this child installed. "
            "fs_isolation is true only when landlock applied and the probes showed "
            "the checkout and temp dir usable and a path outside them denied. "
            "A kernel that does not support a layer is reported missing and the "
            "opted-in run refuses. It is not a pass. "
            "This file does not rewrite receipt 1, does not close receipt 1, "
            "and does not close the source boundary. "
            "go_live_clear stays false. The published pin is not moved. "
            "The UTC stamps are this machine's clock."
        ),
    }


def _skip(env: dict[str, Any], reason: str, finished: str) -> dict[str, Any]:
    env["verdict"] = "skip"
    env["seccomp_applied"] = False
    env["landlock_applied"] = False
    env["landlock_abi"] = None
    env["fs_isolation"] = False
    env["refused"] = True
    env["missing_layers"] = ["seccomp", "landlock"]
    env["continued_without_layer"] = False
    env["failures"] = []
    env["residuals"] = []
    env["probes"] = {}
    env["gaps"] = [
        {"layer": "seccomp", "tag": "skip", "statement": reason},
        {"layer": "landlock", "tag": "skip", "statement": reason},
        {
            "layer": "fs_isolation",
            "tag": "skip",
            "statement": "Filesystem isolation was not measured. This is not a pass.",
        },
    ]
    env["finished_at"] = finished
    return env


def _decode(data: bytes | None, limit: int = 800) -> str:
    if not data:
        return ""
    return data.decode("utf-8", "replace")[:limit]


def _run(prepared: PreparedHardening, timeout: float) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            list(prepared.argv),
            cwd=prepared.temp,
            env=dict(prepared.env),
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "started": False,
            "error": "timeout",
            "stderr": _decode(exc.stderr if isinstance(exc.stderr, bytes) else None),
            "stdout": _decode(exc.stdout if isinstance(exc.stdout, bytes) else None),
        }
    except OSError as exc:
        return {"started": False, "error": type(exc).__name__, "errno": exc.errno}
    stdout = completed.stdout.decode("utf-8", "replace").strip()
    report = None
    if stdout:
        try:
            report = json.loads(stdout)
        except json.JSONDecodeError:
            report = None
    return {
        "started": isinstance(report, dict) and completed.returncode == 0,
        "returncode": completed.returncode,
        "argv": list(prepared.argv),
        "report": report,
        "stderr": _decode(completed.stderr),
        "stdout_prefix": stdout[:240],
    }


def _missing_child(reason: str) -> dict[str, Any]:
    layer = {"applied": False, "gap": False, "reason": reason}
    return {
        "seccomp": dict(layer),
        "landlock": dict(layer),
        "probes": {},
        "refused": True,
        "missing_layers": ["seccomp", "landlock"],
        "continued_without_layer": False,
        "exit_code": 3,
    }


def measure(root: Path | None = None, *, timeout: float = 20) -> dict[str, Any]:
    """Run the opt-in hardened cold boot and return the measurement.

    Does not write it. Does not rewrite receipt 1. Does not place an order
    or open a network connection from the measurer.
    """

    root = (root or repo_root()).resolve()
    started = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    env = _envelope(root, started)
    finished = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    if sys.platform != "linux":
        return _skip(env, "not linux", finished)
    try:
        from aureon.containment.native import ContainmentUnavailable, unshare_path
    except OSError as exc:
        return _skip(env, str(exc), datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"))
    if unshare_path() is None:
        return _skip(env, "unshare is not on PATH", datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"))
    with tempfile.TemporaryDirectory(prefix="aureon-harden-") as directory:
        work = Path(directory)
        temp = work / "temp"
        temp.mkdir()
        outside_dir = work / "outside"
        outside_dir.mkdir()
        outside = outside_dir / "probe"
        outside.write_bytes(b"x")
        try:
            prepared = prepare_hardened_launch(
                work / "launch",
                checkout=root,
                temp=temp,
                deny_network=True,
                drop_caps=False,
                checkout_probe=root / "README.md",
                outside_probe=outside,
            )
        except ContainmentUnavailable as exc:
            return _skip(env, str(exc), datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"))
        except ValueError as exc:
            return _skip(env, str(exc), datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"))
        ran = _run(prepared, timeout)
        env["cold_boot_argv"] = list(prepared.argv)
        env["cold_boot_argv_has_net"] = "--net" in prepared.argv
        env["deny_network"] = prepared.deny_network
        env["drop_caps"] = prepared.drop_caps
        env["child_env_names"] = sorted(prepared.env)
    child = ran.get("report") if isinstance(ran.get("report"), dict) else None
    if child is None:
        child = _missing_child(str(ran.get("error") or "contained child did not return a report"))
        judged = judge_hardening(child)
        if judged["verdict"] == "gap":
            judged["verdict"] = "fail"
            judged["failures"] = [*judged["failures"], "contained child did not return a report"]
        elif "contained child did not return a report" not in " ".join(judged["failures"]):
            judged["failures"] = [*judged["failures"], "contained child did not return a report"]
            judged["verdict"] = "fail"
    else:
        judged = judge_hardening(child)
    env.update(judged)
    landlock = child.get("landlock") if isinstance(child.get("landlock"), Mapping) else {}
    abi = landlock.get("abi")
    env["landlock_abi"] = abi if isinstance(abi, int) else None
    env["refused"] = child.get("refused")
    env["missing_layers"] = child.get("missing_layers")
    env["continued_without_layer"] = False
    if env["verdict"] == "pass" and env["refused"] is True:
        env["verdict"] = "fail"
        env["failures"] = [*env["failures"], "opted-in run refused and was not a pass"]
    env["seccomp"] = child.get("seccomp")
    env["landlock"] = child.get("landlock")
    env["no_new_privs"] = child.get("no_new_privs")
    env["cap_drop"] = child.get("cap_drop")
    env["caps_before_landlock"] = child.get("caps_before_landlock")
    env["child_returncode"] = ran.get("returncode")
    env["stderr"] = ran.get("stderr") or ""
    env["finished_at"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    return env


def write_measurement(receipt: Mapping[str, Any], json_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    tmp = json_path.with_suffix(json_path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, json_path)


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Measure opt-in containment hardening. Does not place orders.")
    parser.add_argument("--no-write", action="store_true", help="print the JSON and do not write reports/measured")
    parser.add_argument("--receipt-json", type=Path, default=None)
    args = parser.parse_args(argv)
    receipt = measure(repo_root())
    if args.no_write:
        sys.stdout.write(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    else:
        json_path = args.receipt_json or (repo_root() / "reports" / "measured" / "containment_hardening.json")
        write_measurement(receipt, json_path)
        sys.stdout.write(
            f"{receipt['verdict']} seccomp_applied={receipt['seccomp_applied']} "
            f"landlock_applied={receipt['landlock_applied']} "
            f"fs_isolation={receipt['fs_isolation']} {json_path}\n"
        )
    return {"pass": 0, "gap": 3, "skip": 2, "fail": 1}.get(str(receipt["verdict"]), 1)


if __name__ == "__main__":
    raise SystemExit(main())
