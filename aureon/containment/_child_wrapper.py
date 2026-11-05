"""Namespace prelude. Run with ``python -I``. Do not import aureon.

The parent decides the network namespace on the ``unshare`` command line.
This prelude remounts sysfs when the launch is a deny, drops capabilities
when asked, and refuses to exec if an environment variable tries to select
network. It cannot add a route the namespace does not have.
"""

from __future__ import annotations

import ctypes
import errno
import json
import os
import re
import sys
from typing import Any

_GRANT_ID = re.compile(r"^[0-9a-f]{64}$")
_PR_CAPBSET_DROP = 24
_PR_SET_NO_NEW_PRIVS = 38
_CAPABILITY_VERSION_3 = 0x20080522


def _names(path: str) -> Any:
    try:
        return sorted(os.listdir(path))
    except OSError as exc:
        return {"errno": exc.errno, "error": errno.errorcode.get(exc.errno, type(exc).__name__)}


def _caps() -> dict[str, str]:
    found: dict[str, str] = {}
    try:
        with open("/proc/self/status", encoding="ascii") as handle:
            lines = handle.read().splitlines()
    except OSError as exc:
        return {"error": errno.errorcode.get(exc.errno, type(exc).__name__)}
    for line in lines:
        if line.startswith("Cap"):
            key, value = line.split(":", 1)
            found[key] = value.strip()
    return found


def _remount_sysfs() -> dict[str, Any]:
    libc = ctypes.CDLL(None, use_errno=True)
    libc.mount.argtypes = [
        ctypes.c_char_p,
        ctypes.c_char_p,
        ctypes.c_char_p,
        ctypes.c_ulong,
        ctypes.c_void_p,
    ]
    libc.mount.restype = ctypes.c_int
    ctypes.set_errno(0)
    rc = libc.mount(b"sysfs", b"/sys", b"sysfs", 0, None)
    err = ctypes.get_errno()
    return {
        "ok": rc == 0,
        "rc": rc,
        "errno": err if rc != 0 else None,
        "error": None if rc == 0 else errno.errorcode.get(err, str(err)),
    }


def _drop_caps() -> dict[str, Any]:
    libc = ctypes.CDLL(None, use_errno=True)
    libc.prctl.argtypes = [
        ctypes.c_int,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_ulong,
    ]
    libc.prctl.restype = ctypes.c_int

    class _Header(ctypes.Structure):
        _fields_ = [("version", ctypes.c_uint32), ("pid", ctypes.c_int)]

    class _Data(ctypes.Structure):
        _fields_ = [
            ("effective", ctypes.c_uint32),
            ("permitted", ctypes.c_uint32),
            ("inheritable", ctypes.c_uint32),
        ]

    ctypes.set_errno(0)
    no_new = libc.prctl(_PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0)
    no_new_err = ctypes.get_errno()
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
            return {
                "ok": False,
                "errno": ctypes.get_errno(),
                "error": errno.errorcode.get(ctypes.get_errno(), "prctl"),
                "dropped": dropped,
            }
    header = _Header(_CAPABILITY_VERSION_3, 0)
    data = (_Data * 2)()
    libc.capset.argtypes = [ctypes.POINTER(_Header), ctypes.c_void_p]
    libc.capset.restype = ctypes.c_int
    ctypes.set_errno(0)
    rc = libc.capset(ctypes.byref(header), ctypes.cast(data, ctypes.c_void_p))
    err = ctypes.get_errno()
    return {
        "ok": rc == 0,
        "rc": rc,
        "errno": None if rc == 0 else err,
        "error": None if rc == 0 else errno.errorcode.get(err, str(err)),
        "dropped": dropped,
        "invalid_cap_numbers": invalid,
        "no_new_privs": no_new == 0,
        "no_new_privs_errno": None if no_new == 0 else no_new_err,
    }


def _refuse(status_path: str, status: dict[str, Any], code: int) -> None:
    status["exec"] = False
    try:
        with open(status_path, "w", encoding="utf-8") as handle:
            json.dump(status, handle, sort_keys=True)
    except OSError:
        pass
    sys.stdout.write(json.dumps({"wrapper_refused": status.get("refused", "refused")}))
    raise SystemExit(code)


def main() -> int:
    if len(sys.argv) != 2:
        sys.stderr.write("containment wrapper expects the sidecar path\n")
        return 2
    sidecar = sys.argv[1]
    try:
        with open(sidecar, encoding="utf-8") as handle:
            spec = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"sidecar unreadable: {type(exc).__name__}\n")
        return 2
    status_path = str(spec.get("status_path") or "")
    status: dict[str, Any] = {"schema": "aureon.containment.wrapper-status.v1"}
    if os.environ.get("AUREON_CONTAINMENT_ALLOW_NETWORK"):
        status["refused"] = "environment variable cannot select network"
        _refuse(status_path, status, 2)
    deny = bool(spec.get("deny_network"))
    status["deny_network"] = deny
    status["sysfs_before"] = _names("/sys/class/net")
    if deny:
        status["sysfs_remount"] = _remount_sysfs()
        status["sysfs_after"] = _names("/sys/class/net")
    else:
        grant_id = str(spec.get("grant_id") or "")
        if _GRANT_ID.fullmatch(grant_id) is None:
            status["refused"] = "allow sidecar has no grant id"
            _refuse(status_path, status, 2)
        status["grant_id"] = grant_id
        status["sysfs_remount"] = {"ok": False, "skipped": True}
        status["sysfs_after"] = status["sysfs_before"]
    status["caps_before"] = _caps()
    if spec.get("drop_caps"):
        status["cap_drop"] = _drop_caps()
    else:
        status["cap_drop"] = {"ok": False, "skipped": True}
    status["caps_after"] = _caps()
    argv = spec.get("argv")
    if not isinstance(argv, list) or not argv or not all(isinstance(item, str) for item in argv):
        status["refused"] = "payload argv is missing"
        _refuse(status_path, status, 2)
    if not os.path.isabs(argv[0]):
        status["refused"] = "payload argv0 is not absolute"
        _refuse(status_path, status, 2)
    status["exec"] = True
    try:
        with open(status_path, "w", encoding="utf-8") as handle:
            json.dump(status, handle, sort_keys=True)
    except OSError as exc:
        sys.stderr.write(f"status write failed: {exc.errno}\n")
        return 2
    os.execv(argv[0], argv)
    return 127


if __name__ == "__main__":
    raise SystemExit(main())
