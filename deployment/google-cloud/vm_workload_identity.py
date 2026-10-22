"""Read a broker-issued Google access token without reaching VM metadata.

Production VM workloads set ``AUREON_VM_TOKEN_BROKER_REQUIRED=1`` and an exact
``AUREON_GOOGLE_TOKEN_FILE`` path.  The small root-owned broker rotates the
file atomically.  Workloads never receive the Compute Engine service account's
metadata token and cannot ask the broker for a different identity.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import stat
import time
from typing import Mapping


TOKEN_SCHEMA = "aureon.gcp.workload-access-token.v1"
TOKEN_FILE_ENV = "AUREON_GOOGLE_TOKEN_FILE"
BROKER_REQUIRED_ENV = "AUREON_VM_TOKEN_BROKER_REQUIRED"
TOKEN_FILE_IDENTITIES = {
    "/run/aureon-cloud-identity/ui/token.json": (
        "aureon-vm-ui@aureon-trading.iam.gserviceaccount.com"
    ),
    "/run/aureon-cloud-identity/operator/token.json": (
        "aureon-vm-operator@aureon-trading.iam.gserviceaccount.com"
    ),
    "/run/aureon-cloud-identity/trade-bridge/token.json": (
        "aureon-vm-trade-bridge@aureon-trading.iam.gserviceaccount.com"
    ),
    "/run/aureon-cloud-identity/provider/token.json": (
        "aureon-vm-provider@aureon-trading.iam.gserviceaccount.com"
    ),
}
ALLOWED_TOKEN_FILES = frozenset(TOKEN_FILE_IDENTITIES)
_BEARER = re.compile(r"[A-Za-z0-9._~-]{20,8192}")


class WorkloadIdentityError(RuntimeError):
    """A stable, credential-free workload identity failure."""


def _decode_token(
    raw: bytes, *, now: float, expected_service_account: str
) -> str:
    if not isinstance(raw, bytes) or not 0 < len(raw) <= 16_384:
        raise WorkloadIdentityError("workload_token_file_invalid")
    try:
        value = json.loads(raw)
    except (ValueError, TypeError, UnicodeError) as exc:
        raise WorkloadIdentityError("workload_token_file_invalid") from exc
    if not isinstance(value, dict) or set(value) != {
        "schema",
        "access_token",
        "token_type",
        "expires_at_epoch",
        "service_account",
    }:
        raise WorkloadIdentityError("workload_token_file_invalid")
    token = value.get("access_token")
    expiry = value.get("expires_at_epoch")
    if (
        value.get("schema") != TOKEN_SCHEMA
        or value.get("token_type") != "Bearer"
        or value.get("service_account") != expected_service_account
        or not isinstance(token, str)
        or _BEARER.fullmatch(token) is None
        or isinstance(expiry, bool)
        or not isinstance(expiry, (int, float))
        or not now + 30 < float(expiry) <= now + 3_700
    ):
        raise WorkloadIdentityError("workload_token_file_invalid")
    return token


def _trusted_file(path: Path) -> bytes:
    try:
        parent = path.parent.stat(follow_symlinks=False)
        before = path.stat(follow_symlinks=False)
    except (OSError, ValueError) as exc:
        raise WorkloadIdentityError("workload_token_file_unavailable") from exc
    if (
        stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or not stat.S_ISDIR(parent.st_mode)
        or before.st_nlink != 1
        or before.st_mode & 0o022
        or parent.st_mode & 0o022
    ):
        raise WorkloadIdentityError("workload_token_file_permissions_invalid")
    if os.name == "posix":
        if before.st_uid != 0 or parent.st_uid != 0:
            raise WorkloadIdentityError("workload_token_file_owner_invalid")
        if before.st_gid not in {0, os.getegid()}:
            raise WorkloadIdentityError("workload_token_file_group_invalid")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
        with os.fdopen(fd, "rb") as handle:
            opened = os.fstat(handle.fileno())
            if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
                raise WorkloadIdentityError("workload_token_file_changed")
            raw = handle.read(16_385)
    except WorkloadIdentityError:
        raise
    except OSError as exc:
        raise WorkloadIdentityError("workload_token_file_unavailable") from exc
    if len(raw) > 16_384:
        raise WorkloadIdentityError("workload_token_file_invalid")
    return raw


def broker_token(
    environ: Mapping[str, str] | None = None,
    *,
    now: float | None = None,
) -> str | None:
    """Return the broker token, or ``None`` only outside required broker mode."""

    env = os.environ if environ is None else environ
    required = str(env.get(BROKER_REQUIRED_ENV) or "") == "1"
    reference = str(env.get(TOKEN_FILE_ENV) or "")
    if not reference:
        if required:
            raise WorkloadIdentityError("workload_token_file_required")
        return None
    if reference not in ALLOWED_TOKEN_FILES:
        raise WorkloadIdentityError("workload_token_file_path_invalid")
    current = time.time() if now is None else float(now)
    if not 0 < current < 10_000_000_000:
        raise WorkloadIdentityError("workload_token_clock_invalid")
    return _decode_token(
        _trusted_file(Path(reference)),
        now=current,
        expected_service_account=TOKEN_FILE_IDENTITIES[reference],
    )


__all__ = [
    "ALLOWED_TOKEN_FILES",
    "BROKER_REQUIRED_ENV",
    "TOKEN_FILE_ENV",
    "TOKEN_FILE_IDENTITIES",
    "TOKEN_SCHEMA",
    "WorkloadIdentityError",
    "broker_token",
]
