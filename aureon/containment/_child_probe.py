"""Network probe. Run with ``python -I`` inside the containment wrapper.

This file does not replace ``socket.socket``. Connect failures are the
kernel's. Nothing here reads an environment value, a key file, or a market.
"""

from __future__ import annotations

import ctypes
import errno
import fcntl
import importlib
import json
import os
import socket
import struct
import sys
import traceback
from typing import Any


def _guard(fn: Any) -> Any:
    try:
        return fn()
    except Exception as exc:
        return {
            "ok": False,
            "error": type(exc).__name__,
            "message": str(exc)[:180],
        }


def _proc_net_dev() -> list[str]:
    with open("/proc/net/dev", encoding="ascii") as handle:
        lines = handle.read().splitlines()
    names: list[str] = []
    for line in lines[2:]:
        if ":" not in line:
            continue
        names.append(line.split(":", 1)[0].strip())
    return names


def _default_route_ifaces() -> list[str]:
    with open("/proc/net/route", encoding="ascii") as handle:
        text = handle.read()
    found: list[str] = []
    for line in text.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "00000000":
            found.append(parts[0])
    return found


def _caps() -> dict[str, str]:
    found: dict[str, str] = {}
    with open("/proc/self/status", encoding="ascii") as handle:
        lines = handle.readlines()
    for line in lines:
        if line.startswith("Cap"):
            key, value = line.split(":", 1)
            found[key] = value.strip()
    return found


def _tcp(host: str, port: int) -> dict[str, Any]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.settimeout(0.4)
        sock.connect((host, port))
    except OSError as exc:
        return {
            "ok": False,
            "host": host,
            "port": port,
            "errno": exc.errno,
            "error": errno.errorcode.get(exc.errno, type(exc).__name__),
        }
    else:
        return {"ok": True, "host": host, "port": port, "errno": None, "error": None}
    finally:
        sock.close()


def _udp(host: str, port: int) -> dict[str, Any]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.settimeout(0.4)
        sock.sendto(b"\0", (host, port))
    except OSError as exc:
        return {
            "ok": False,
            "host": host,
            "port": port,
            "payload": "single NUL byte, not a DNS query",
            "errno": exc.errno,
            "error": errno.errorcode.get(exc.errno, type(exc).__name__),
        }
    else:
        return {"ok": True, "host": host, "port": port, "errno": None, "error": None}
    finally:
        sock.close()


def _tcp6() -> dict[str, Any]:
    try:
        sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    except OSError as exc:
        return {
            "ok": False,
            "stage": "socket",
            "errno": exc.errno,
            "error": errno.errorcode.get(exc.errno, type(exc).__name__),
        }
    try:
        sock.settimeout(0.4)
        sock.connect(("2001:4860:4860::8888", 53))
    except OSError as exc:
        return {
            "ok": False,
            "host": "2001:4860:4860::8888",
            "port": 53,
            "errno": exc.errno,
            "error": errno.errorcode.get(exc.errno, type(exc).__name__),
        }
    else:
        return {"ok": True, "errno": None, "error": None}
    finally:
        sock.close()


def _libc_connect() -> dict[str, Any]:
    libc = ctypes.CDLL(None, use_errno=True)
    ctypes.set_errno(0)
    fd = libc.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
    if fd < 0:
        err = ctypes.get_errno()
        return {
            "ok": False,
            "stage": "socket",
            "errno": err,
            "error": errno.errorcode.get(err, str(err)),
        }
    address = struct.pack(
        "=HH4s8s",
        socket.AF_INET,
        socket.htons(443),
        socket.inet_aton("1.1.1.1"),
        b"\0" * 8,
    )
    ctypes.set_errno(0)
    rc = libc.connect(fd, address, len(address))
    err = ctypes.get_errno()
    os.close(fd)
    return {
        "ok": rc == 0,
        "rc": rc,
        "errno": None if rc == 0 else err,
        "error": None if rc == 0 else errno.errorcode.get(err, str(err)),
        "note": "libc connect syscall, not socket.socket",
    }


def _raw() -> dict[str, Any]:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
    except OSError as exc:
        return {
            "ok": False,
            "errno": exc.errno,
            "error": errno.errorcode.get(exc.errno, type(exc).__name__),
        }
    sock.close()
    return {"ok": True, "errno": None, "error": None, "sent": False}


def _lo_flags() -> dict[str, Any]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        ifr = struct.pack("16sH14s", b"lo\0", 0, b"")
        got = fcntl.ioctl(sock, 0x8913, ifr)
        flags = struct.unpack("16sH14s", got)[1]
    except OSError as exc:
        return {
            "ok": False,
            "errno": exc.errno,
            "error": errno.errorcode.get(exc.errno, type(exc).__name__),
        }
    else:
        return {"ok": True, "flags": flags, "up": bool(flags & 0x1), "errno": None}
    finally:
        sock.close()


def _set_lo_up() -> dict[str, Any]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        ifr = struct.pack("16sH14s", b"lo\0", 0, b"")
        got = fcntl.ioctl(sock, 0x8913, ifr)
        flags = struct.unpack("16sH14s", got)[1]
        updated = struct.pack("16sH14s", b"lo\0", flags | 0x1, b"")
        fcntl.ioctl(sock, 0x8914, updated)
    except OSError as exc:
        return {
            "ok": False,
            "errno": exc.errno,
            "error": errno.errorcode.get(exc.errno, type(exc).__name__),
        }
    else:
        return {"ok": True, "errno": None, "error": None, "flags_before": flags}
    finally:
        sock.close()


def _marker(path: str | None) -> dict[str, Any]:
    if not path:
        return {"readable": False, "reason": "no marker"}
    try:
        with open(path, "rb") as handle:
            handle.read(1)
    except OSError as exc:
        return {
            "readable": False,
            "errno": exc.errno,
            "error": errno.errorcode.get(exc.errno, type(exc).__name__),
        }
    return {"readable": True, "contents_recorded": False}


def _passwd() -> dict[str, Any]:
    try:
        with open("/etc/passwd", "rb") as handle:
            handle.read(1)
    except OSError as exc:
        return {
            "readable": False,
            "errno": exc.errno,
            "error": errno.errorcode.get(exc.errno, type(exc).__name__),
        }
    return {"readable": True, "contents_recorded": False}


def build() -> dict[str, Any]:
    args = sys.argv[1:]
    marker = None
    if "--marker" in args:
        marker = args[args.index("--marker") + 1]
    attempt = "--attempt-lo-up" in args
    report: dict[str, Any] = {
        "schema": "aureon.containment.probe.v1",
        "socket_monkeypatch": False,
        "socket_module": socket.socket.__module__,
        "euid": os.geteuid(),
        "net_ns": os.readlink("/proc/self/ns/net"),
        "user_ns": os.readlink("/proc/self/ns/user"),
        "interfaces_proc_net_dev": _proc_net_dev(),
        "default_route_ifaces": _default_route_ifaces(),
        "sysfs_net": _guard(lambda: sorted(os.listdir("/sys/class/net"))),
        "caps": _caps(),
        "environ_names": sorted(os.environ),
        "marker": _marker(marker),
        "etc_passwd": _passwd(),
        "lo_before": _guard(_lo_flags),
        "probes": {
            "tcp_1.1.1.1_443": _guard(lambda: _tcp("1.1.1.1", 443)),
            "tcp_127.0.0.1_9": _guard(lambda: _tcp("127.0.0.1", 9)),
            "udp_8.8.8.8_53": _guard(lambda: _udp("8.8.8.8", 53)),
            "libc_connect_1.1.1.1_443": _guard(_libc_connect),
            "tcp6_2001:4860:4860::8888_53": _guard(_tcp6),
            "raw_icmp_create": _guard(_raw),
        },
    }
    importlib.reload(socket)
    report["probes"]["tcp_1.1.1.1_443_after_socket_reload"] = _guard(lambda: _tcp("1.1.1.1", 443))
    report["socket_module_after_reload"] = socket.socket.__module__
    if attempt:
        report["lo_up_attempt"] = _guard(_set_lo_up)
        if report["lo_up_attempt"].get("ok"):
            report["after_lo_up"] = {
                "tcp_127.0.0.1_9": _guard(lambda: _tcp("127.0.0.1", 9)),
                "tcp_1.1.1.1_443": _guard(lambda: _tcp("1.1.1.1", 443)),
                "default_route_ifaces": _default_route_ifaces(),
            }
    else:
        report["lo_up_attempt"] = {"ok": False, "skipped": True}
    return report


def main() -> int:
    try:
        report = build()
    except Exception:
        traceback.print_exc()
        return 1
    sys.stdout.write(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
