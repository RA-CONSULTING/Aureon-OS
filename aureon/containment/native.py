"""Build a cold-boot command whose default network namespace has no route.

``unshare --net`` is the same native mechanism the benchmark harness uses
for model-written code. Here it is the default for a contained process,
not an opt-in around an interpreter patch. The public MCP sweep guard
remains an in-process ``socket.socket`` replacement and is not invoked.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

PIN = "34864ff0547d2cff03e707414743a3b0cc8770b5"
STARTED_FROM = "c68a89d2a184d99582bb24310b91e024323a212c"

_WRAPPER = Path(__file__).with_name("_child_wrapper.py")
_ACTOR = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 .:_/-]{0,79}$")
_REASON = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 .:_/-]{11,199}$")


class ContainmentUnavailable(RuntimeError):
    """``unshare`` is not on PATH, so no namespace was claimed."""


class ContainmentRefused(ValueError):
    """The allow grant is missing, forged, or not the audited allow."""


@dataclass(frozen=True)
class NetworkAllowGrant:
    """One explicit permission to share the parent network namespace.

    Construct this with ``authorize_network_allow``. A hand-built instance
    whose ``grant_id`` is not the hash of ``audit`` is refused.
    """

    grant_id: str
    audit: Mapping[str, str]


@dataclass(frozen=True)
class PreparedLaunch:
    """Argv and env for one contained process. The env is not the parent env."""

    argv: tuple[str, ...]
    env: Mapping[str, str]
    sidecar: Path
    status_path: Path
    deny_network: bool
    drop_caps: bool
    grant_id: str | None


def _canonical(value: Mapping[str, str]) -> bytes:
    return json.dumps(dict(value), sort_keys=True, separators=(",", ":")).encode("utf-8")


def _grant_id(audit: Mapping[str, str]) -> str:
    return hashlib.sha256(_canonical(audit)).hexdigest()


def authorize_network_allow(
    reason: str,
    actor: str,
    *,
    issued_at: str | None = None,
) -> NetworkAllowGrant:
    """Return a grant that omits ``unshare --net``.

    ``reason`` and ``actor`` are stored in the audit. They are not passed
    to the child. No environment variable calls this function.
    """

    from datetime import UTC, datetime

    if _REASON.fullmatch(reason) is None:
        raise ContainmentRefused("allow reason must be 12 to 200 visible characters")
    if _ACTOR.fullmatch(actor) is None:
        raise ContainmentRefused("allow actor must be 1 to 80 visible characters")
    stamp = issued_at or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", stamp):
        raise ContainmentRefused("allow timestamp is not UTC Z")
    audit = {
        "actor": actor,
        "effect": "share-parent-netns",
        "issued_at": stamp,
        "policy": "allow",
        "reason": reason,
        "schema": "aureon.containment.network-allow.v1",
    }
    return NetworkAllowGrant(grant_id=_grant_id(audit), audit=audit)


def verify_grant(grant: object) -> NetworkAllowGrant:
    """Refuse anything that is not a hash-bound allow grant."""

    if not isinstance(grant, NetworkAllowGrant):
        raise ContainmentRefused("network allow requires authorize_network_allow")
    audit = grant.audit
    if not isinstance(audit, Mapping):
        raise ContainmentRefused("allow audit is missing")
    expected_keys = {"actor", "effect", "issued_at", "policy", "reason", "schema"}
    if set(audit) != expected_keys or any(not isinstance(value, str) for value in audit.values()):
        raise ContainmentRefused("allow audit shape is wrong")
    if audit["policy"] != "allow" or audit["effect"] != "share-parent-netns":
        raise ContainmentRefused("allow audit is not the network share")
    if audit["schema"] != "aureon.containment.network-allow.v1":
        raise ContainmentRefused("allow audit schema is wrong")
    if _grant_id({str(key): str(audit[key]) for key in audit}) != grant.grant_id:
        raise ContainmentRefused("allow grant id does not match the audit")
    return grant


def scrubbed_child_env(home: Path) -> dict[str, str]:
    """A new environment. The parent process environment is not copied."""

    exe_dir = str(Path(sys.executable).resolve().parent)
    return {
        "HOME": str(home),
        "LANG": "C",
        "LC_ALL": "C",
        "PATH": f"{exe_dir}:/usr/bin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONUNBUFFERED": "1",
    }


def unshare_path() -> str | None:
    found = shutil.which("unshare")
    return found if found else None


def prepare_launch(
    work: Path,
    payload: Sequence[str],
    *,
    grant: NetworkAllowGrant | None = None,
    drop_caps: bool | None = None,
) -> PreparedLaunch:
    """Write the sidecar and return the ``unshare`` command.

    ``grant is None`` keeps ``--net``. A verified grant omits ``--net``.
    ``os.environ`` is not consulted. ``drop_caps`` defaults to true on the
    deny path and false on the allow path. The gap measurement passes
    ``drop_caps=False`` with no grant, which still keeps ``--net``.
    """

    if any(not isinstance(item, str) or item == "" for item in payload):
        raise ContainmentRefused("payload argv must be non-empty strings")
    if not os.path.isabs(payload[0]):
        raise ContainmentRefused("payload argv0 must be absolute")
    unshare = unshare_path()
    if unshare is None:
        raise ContainmentUnavailable("unshare is not on PATH")
    verified: NetworkAllowGrant | None
    if grant is None:
        verified = None
        deny_network = True
    else:
        verified = verify_grant(grant)
        deny_network = False
    if drop_caps is None:
        drop_caps = deny_network
    work.mkdir(parents=True, exist_ok=True)
    sidecar = work / "sidecar.json"
    status_path = work / "wrapper-status.json"
    spec: dict[str, Any] = {
        "argv": list(payload),
        "deny_network": deny_network,
        "drop_caps": drop_caps,
        "schema": "aureon.containment.launch.v1",
        "status_path": str(status_path),
    }
    grant_id = None
    if verified is not None:
        grant_id = verified.grant_id
        spec["grant_id"] = grant_id
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
    argv = [*flags, sys.executable, "-I", str(_WRAPPER.resolve()), str(sidecar.resolve())]
    return PreparedLaunch(
        argv=tuple(argv),
        env=scrubbed_child_env(work),
        sidecar=sidecar,
        status_path=status_path,
        deny_network=deny_network,
        drop_caps=drop_caps,
        grant_id=grant_id,
    )
