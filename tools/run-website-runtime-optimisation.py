"""Isolated, package-free trust bootstrap for website runtime optimisation.

The caller must authenticate this launcher before invoking it and supply the
reviewed planner SHA-256.  The launcher then reads that exact planner through a
bound handle and executes the authenticated bytes as ``__main__`` without
importing ``aureon`` or either package initializer.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import stat
import sys
from pathlib import Path

PLANNER_PATH = Path("aureon/operator/website_runtime_optimisation.py")
MAX_PLANNER_BYTES = 2 * 1024 * 1024
_SHA256 = re.compile(r"[A-F0-9]{64}\Z")


class TrustedLauncherError(RuntimeError):
    """The isolated launcher or reviewed planner binding is unsafe."""


def _is_link_or_reparse(path: Path) -> bool:
    details = path.lstat()
    attributes = int(getattr(details, "st_file_attributes", 0) or 0)
    reparse = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400) or 0x400)
    return stat.S_ISLNK(details.st_mode) or bool(attributes & reparse)


def _ordinary_file(path: Path, *, label: str) -> Path:
    lexical = Path(os.path.abspath(path))
    for component in (lexical, *lexical.parents):
        if (component.exists() or component.is_symlink()) and _is_link_or_reparse(component):
            raise TrustedLauncherError(f"{label} may not cross a link or reparse point.")
    if not lexical.is_file() or int(lexical.stat().st_nlink) != 1:
        raise TrustedLauncherError(f"{label} must be an ordinary single-link file.")
    return lexical


def _same_identity(left: os.stat_result, right: os.stat_result) -> bool:
    return (
        stat.S_IFMT(left.st_mode) == stat.S_IFMT(right.st_mode)
        and int(left.st_dev) == int(right.st_dev)
        and int(left.st_ino) == int(right.st_ino)
    )


def _read_exact_source(path: Path, expected_sha256: str, *, label: str) -> bytes:
    source = _ordinary_file(path, label=label)
    before = source.lstat()
    if int(before.st_size) > MAX_PLANNER_BYTES:
        raise TrustedLauncherError(f"{label} exceeds the launcher byte bound.")
    with source.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        if not _same_identity(before, opened):
            raise TrustedLauncherError(f"{label} changed before its handle opened.")
        payload = stream.read(MAX_PLANNER_BYTES + 1)
    after = source.lstat()
    observed = hashlib.sha256(payload).hexdigest().upper()
    if (
        len(payload) > MAX_PLANNER_BYTES
        or int(after.st_size) != len(payload)
        or not _same_identity(opened, after)
        or observed != expected_sha256
    ):
        raise TrustedLauncherError(f"{label} bytes do not match the supplied source pin.")
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="run-website-runtime-optimisation")
    parser.add_argument("--expected-launcher-sha256", required=True)
    parser.add_argument("--expected-planner-sha256", required=True)
    parser.add_argument("planner_args", nargs=argparse.REMAINDER)
    return parser


def main(argv: list[str] | None = None) -> int:
    if not (sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode):
        raise TrustedLauncherError("Launcher requires python -I -S -B.")
    args = build_parser().parse_args(argv)
    expected_launcher = args.expected_launcher_sha256
    expected_planner = args.expected_planner_sha256
    if _SHA256.fullmatch(expected_launcher) is None or _SHA256.fullmatch(expected_planner) is None:
        raise TrustedLauncherError("Expected SHA-256 values must be 64 uppercase hexadecimal digits.")
    launcher = _ordinary_file(Path(__file__), label="Trusted runtime-optimisation launcher")
    _read_exact_source(
        launcher,
        expected_launcher,
        label="Trusted runtime-optimisation launcher",
    )
    root = launcher.parent.parent
    planner = root / PLANNER_PATH
    payload = _read_exact_source(
        planner,
        expected_planner,
        label="Reviewed runtime-optimisation planner",
    )
    forwarded = list(args.planner_args)
    if forwarded[:1] == ["--"]:
        forwarded = forwarded[1:]
    sys.argv = [str(planner), *forwarded]
    scope = {
        "__builtins__": __builtins__,
        "__cached__": None,
        "__file__": str(planner),
        "__name__": "__main__",
        "__package__": None,
        "__aureon_runtime_optimisation_launcher_attestation__": {
            "launcher_path": str(launcher),
            "launcher_sha256": expected_launcher,
            "planner_path": str(planner),
            "planner_sha256": expected_planner,
            "isolated": True,
            "no_site": True,
            "dont_write_bytecode": True,
        },
    }
    exec(compile(payload, str(planner), "exec", dont_inherit=True), scope)  # noqa: S102
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except TrustedLauncherError as exc:
        print(f"blocked: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
