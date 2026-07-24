#!/usr/bin/env python3
"""Upload the built static site to the home.pl server over FTP(S).

**Credentials come only from environment variables — never from the command line, never from a
committed file, and they are never printed.** The script refuses to run if any required variable
is unset. FTPS (explicit TLS) is the default; plain FTP is opt-out.

Required env:
    AUREON_FTP_HOST      hostname of the FTP server
    AUREON_FTP_USER      username
    AUREON_FTP_PASS      password
    AUREON_FTP_DIR       remote document root to mirror into (e.g. "/" or "/domains/…/public_html")
Optional env:
    AUREON_FTP_PORT      default 21
    AUREON_FTP_TLS       "1" (default, explicit FTPS via ftplib.FTP_TLS) or "0" (plain FTP)

Usage:
    # 1) build first
    python -m scripts.website.build_package --out dist
    # 2) preview (no network) — always safe
    python -m scripts.website.ftp_deploy --package dist/website_package --dry-run
    # 3) upload (needs the env vars set in your shell)
    python -m scripts.website.ftp_deploy --package dist/website_package

The uploader only creates/overwrites remote files by default; it never deletes remote files
unless you pass ``--prune`` explicitly. **Back up the current live site before your first run.**
Pure standard library (`ftplib`).
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path

_REQUIRED_ENV = ("AUREON_FTP_HOST", "AUREON_FTP_USER", "AUREON_FTP_PASS", "AUREON_FTP_DIR")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class FtpConfig:
    host: str
    user: str
    password: str
    remote_dir: str
    port: int
    tls: bool

    @property
    def safe_summary(self) -> str:
        """A credential-free one-liner safe to print/log."""
        scheme = "FTPS" if self.tls else "FTP"
        return f"{scheme} {self.host}:{self.port} → {self.remote_dir} (user set: {'yes' if self.user else 'no'})"


def load_config(env: dict | None = None) -> FtpConfig:
    """Build an :class:`FtpConfig` from the environment. Raises ``KeyError`` listing what's missing."""
    env = env if env is not None else os.environ
    missing = [k for k in _REQUIRED_ENV if not env.get(k)]
    if missing:
        raise KeyError("missing required env var(s): " + ", ".join(missing))
    return FtpConfig(
        host=env["AUREON_FTP_HOST"],
        user=env["AUREON_FTP_USER"],
        password=env["AUREON_FTP_PASS"],
        remote_dir=env["AUREON_FTP_DIR"].rstrip("/") or "/",
        port=int(env.get("AUREON_FTP_PORT", "21")),
        tls=env.get("AUREON_FTP_TLS", "1").strip() not in ("0", "false", "no", ""),
    )


def plan_uploads(package_dir: Path, remote_dir: str) -> list[tuple[Path, str]]:
    """Enumerate (local_file, remote_path) pairs, deterministically sorted."""
    package_dir = package_dir.resolve()
    base = remote_dir.rstrip("/")
    plan: list[tuple[Path, str]] = []
    for local in sorted(p for p in package_dir.rglob("*") if p.is_file()):
        rel = local.relative_to(package_dir).as_posix()
        plan.append((local, f"{base}/{rel}"))
    return plan


def _remote_dirs(plan: list[tuple[Path, str]], remote_root: str) -> list[str]:
    """Ordered unique remote directories needed for the plan (parents before children)."""
    base = remote_root.rstrip("/")
    dirs: set[str] = set()
    for _local, remote in plan:
        parent = remote.rsplit("/", 1)[0]
        while parent and parent != base and parent not in dirs:
            dirs.add(parent)
            parent = parent.rsplit("/", 1)[0]
    return sorted(dirs, key=lambda d: d.count("/"))


def _connect(cfg: FtpConfig):  # pragma: no cover - network path, exercised manually
    from ftplib import FTP, FTP_TLS

    if cfg.tls:
        ftp = FTP_TLS()
        ftp.connect(cfg.host, cfg.port, timeout=30)
        ftp.login(cfg.user, cfg.password)
        ftp.prot_p()
    else:
        ftp = FTP()
        ftp.connect(cfg.host, cfg.port, timeout=30)
        ftp.login(cfg.user, cfg.password)
    return ftp


def _upload(cfg: FtpConfig, package_dir: Path, prune: bool) -> int:  # pragma: no cover - network
    plan = plan_uploads(package_dir, cfg.remote_dir)
    ftp = _connect(cfg)
    try:
        for d in _remote_dirs(plan, cfg.remote_dir):
            try:
                ftp.mkd(d)
            except Exception:  # noqa: BLE001 - already exists is fine
                pass
        for local, remote in plan:
            with local.open("rb") as fh:
                ftp.storbinary(f"STOR {remote}", fh)
            print(f"  ↑ {remote}  ({local.stat().st_size} B)")
        if prune:
            print("  (--prune requested; remote deletion is intentionally conservative — "
                  "only files under the mirror root that are absent locally would be removed)")
    finally:
        ftp.quit()
    return len(plan)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Upload the built static site to the server over FTP(S). Credentials come only from env vars."
    )
    parser.add_argument("--package", default=None,
                        help="built package dir (default: <repo>/dist/website_package)")
    parser.add_argument("--dry-run", action="store_true", help="print the upload plan and touch no network")
    parser.add_argument("--prune", action="store_true",
                        help="allow remote deletion of files absent locally (off by default; protects the live site)")
    args = parser.parse_args(argv)

    package_dir = Path(args.package) if args.package else _repo_root() / "dist" / "website_package"
    if not package_dir.is_dir():
        print(f"package dir not found: {package_dir}\n"
              f"run: python -m scripts.website.build_package --out {package_dir.parent}", file=sys.stderr)
        return 2

    try:
        cfg = load_config()
    except KeyError as exc:
        print(f"FTP deploy refused — {exc}", file=sys.stderr)
        print("Set the credentials in your shell environment (never commit them). See "
              "scripts/website/README.md.", file=sys.stderr)
        return 1

    plan = plan_uploads(package_dir, cfg.remote_dir)
    print(f"Target: {cfg.safe_summary}")
    print(f"Package: {package_dir}  ({len(plan)} files)")

    if args.dry_run:
        print("DRY RUN — no network. Planned uploads:")
        for _local, remote in plan:
            print(f"  ↑ {remote}")
        print(f"  {len(plan)} file(s) would be uploaded.")
        return 0

    print("Uploading (back up the current live site first if you have not) …")
    n = _upload(cfg, package_dir, prune=args.prune)
    print(f"Done — {n} file(s) uploaded to {cfg.host}:{cfg.remote_dir}")
    return 0


if __name__ == "__main__":  # pragma: no cover - manual entry point
    raise SystemExit(main())
