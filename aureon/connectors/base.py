"""The shape every outside-world connector must take, and the rule they all obey.

**Why this package exists.** Aureon's Drive and Gmail access has, until now, been
whatever an interactive session happened to have plugged in: MCP tools driven by
a human sitting in front of a chat window. The daemon has no human sitting in
front of it. When ``aureon.grants.daemon`` breathes at 03:00 there is no MCP
transport, no OAuth consent screen and nobody to click one — so the running
system could not read the war-room sheet it is reconciled against, and could not
see a funder's reply. This package is the daemon's own integration, holding its
own credentials, and it shares nothing with the interactive tooling.

**The rule.** An unconfigured connector reports absence; it does not throw. Not
on import, not on first use, not on the tenth call. Every public method returns a
:class:`ConnectorStatus` (or a :class:`ConnectorResult`, which *is* one) carrying
either real records or a blocker that names precisely what is missing. That is
the Owner's Rule applied to I/O: an absent credential produces a stated blocker,
never an empty list dressed up as "no results found". Those two states are
completely different answers and a caller must be able to tell them apart.

**Optional dependency.** The Google client libraries are deliberately *not* in
``pyproject.toml``. The repo must install and its tests must run with no network
and no Google stack present — which is exactly the state this file is being
written in. To enable live access, install them yourself::

    pip install google-api-python-client google-auth

Without them every connector still constructs, still answers ``status()``, and
still returns a blocker naming the missing package and that pip line.

**Credentials.** A path, never an inline secret. ``GOOGLE_APPLICATION_CREDENTIALS``
(the Google standard) is consulted first, then ``AUREON_GOOGLE_SERVICE_ACCOUNT_JSON``.
Both must name a service-account key *file*. A variable holding pasted JSON is
refused rather than parsed — see :func:`resolve_credential`. Nothing in this
module ever reads, logs, or echoes the contents of a key file.
"""

from __future__ import annotations

import importlib.util
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Protocol, runtime_checkable

LOG = logging.getLogger("aureon.connectors")

# The optional Google stack. Both are needed: `googleapiclient` builds the
# service, `google.oauth2` loads the service-account key.
GOOGLE_MODULES: tuple[str, ...] = ("googleapiclient.discovery", "google.oauth2.service_account")
INSTALL_HINT = "pip install google-api-python-client google-auth"

# Credential sources, in the order they are tried. The Google standard variable
# wins so an environment already configured for gcloud needs no Aureon-specific
# setup; the Aureon-specific one exists for a machine that runs several projects.
CREDENTIAL_ENV_VARS: tuple[str, ...] = (
    "GOOGLE_APPLICATION_CREDENTIALS",
    "AUREON_GOOGLE_SERVICE_ACCOUNT_JSON",
)

# The mailbox / Drive account a service account impersonates under domain-wide
# delegation. Gmail *requires* one (a service account has no mailbox of its own);
# Drive uses it only when set.
SUBJECT_ENV_VAR = "AUREON_GOOGLE_DELEGATED_USER"

# Provenance strings for ConnectorStatus.source.
SOURCE_INJECTED = "injected transport"
SOURCE_UNCONFIGURED = "unconfigured"


@dataclass(frozen=True)
class ConnectorStatus:
    """Can this connector reach its source right now, and if not, why not?

    The invariant enforced in ``__post_init__`` is the whole point of the type:
    an ``available`` status may not carry a blocker, and an unavailable one may
    not omit it. That makes "quietly unavailable" unrepresentable — the failure
    mode where a connector returns nothing and the caller reads it as an empty
    result cannot be constructed, let alone returned.

    ``source`` is provenance: which credential variable, or which injected
    transport, produced this answer. It is never the credential itself.
    """

    available: bool
    blocker: str | None = None
    source: str = ""

    def __post_init__(self) -> None:
        if self.available and self.blocker:
            raise ValueError("an available connector cannot also carry a blocker")
        if not self.available and not self.blocker:
            raise ValueError("an unavailable connector must state its blocker")

    @classmethod
    def blocked(cls, blocker: str, *, source: str = SOURCE_UNCONFIGURED) -> ConnectorStatus:
        return cls(available=False, blocker=blocker, source=source)

    @classmethod
    def ready(cls, *, source: str) -> ConnectorStatus:
        return cls(available=True, blocker=None, source=source)

    def to_dict(self) -> dict[str, Any]:
        return {"available": self.available, "blocker": self.blocker, "source": self.source}


@dataclass(frozen=True)
class ConnectorResult(ConnectorStatus):
    """A status that also carries what was actually read.

    Subclassing :class:`ConnectorStatus` rather than wrapping it is deliberate:
    "every method returns a ConnectorStatus" then holds literally, so a caller
    can check ``.available`` / ``.blocker`` on *any* return value without knowing
    which method produced it, and a successful call needs no separate type.

    ``records`` holds whatever that method reads — Drive files, one file's
    content, Gmail threads. It is empty on failure, and empty-with-available is
    a real answer meaning the source returned nothing.
    """

    records: tuple[Any, ...] = ()

    @property
    def record(self) -> Any | None:
        """The single record, for methods that read exactly one thing."""
        return self.records[0] if self.records else None

    def to_dict(self) -> dict[str, Any]:
        out = super().to_dict()
        out["record_count"] = len(self.records)
        out["records"] = [r.to_dict() if hasattr(r, "to_dict") else r for r in self.records]
        return out


@runtime_checkable
class Connector(Protocol):
    """What every connector in this package answers to.

    Deliberately tiny. A connector is not asked to declare what it *can* do —
    the methods it exposes are that declaration, and the methods it does not
    expose are a guarantee (see :mod:`aureon.connectors.gmail`, which has no send
    path because a class that cannot send cannot be argued into sending).
    """

    @property
    def name(self) -> str:
        """Stable identifier, e.g. ``google_drive``."""

    def status(self) -> ConnectorStatus:
        """Reachability right now — never raises, never guesses."""


@dataclass(frozen=True)
class CredentialSource:
    """Where a usable service-account key was found, or why none was."""

    path: Path | None = None
    env_var: str = ""
    blocker: str | None = None

    @property
    def found(self) -> bool:
        return self.path is not None


def resolve_credential(env: Mapping[str, str] | None = None) -> CredentialSource:
    """Find a service-account key file from the environment. Never raises.

    Every variable in :data:`CREDENTIAL_ENV_VARS` is tried in order and the first
    usable one wins. When none is usable the blocker lists what was wrong with
    *each*, because "no credential" is not actionable while "set but pointing at
    a file that does not exist" is.

    Inline JSON is refused rather than parsed. A pasted service-account key in an
    environment variable leaks into process listings, crash dumps and shell
    history, and the refusal message never echoes the value — only the name of
    the variable holding it.
    """
    env = os.environ if env is None else env
    reasons: list[str] = []

    for var in CREDENTIAL_ENV_VARS:
        raw = (env.get(var) or "").strip()
        if not raw:
            reasons.append(f"{var} is not set")
            continue
        if raw.startswith("{"):
            reasons.append(
                f"{var} holds inline JSON, not a path — point it at a key file on disk "
                "(a key in an environment variable leaks into process listings)"
            )
            continue
        try:
            path = Path(raw).expanduser()
            if not path.exists():
                reasons.append(f"{var} points at a file that does not exist: {path}")
                continue
            if not path.is_file():
                reasons.append(f"{var} points at a directory, not a key file: {path}")
                continue
        except (OSError, ValueError) as exc:
            # Windows raises on paths containing characters it cannot represent.
            # The path is echoed but never the file's contents.
            reasons.append(f"{var} is not a usable path ({type(exc).__name__})")
            continue
        return CredentialSource(path=path, env_var=var)

    return CredentialSource(blocker="no Google service-account credential: " + "; ".join(reasons))


def missing_dependency() -> str | None:
    """Name the absent Google client modules, or None when all are importable.

    ``find_spec`` is used rather than a real import so that probing costs nothing
    and cannot execute third-party module code as a side effect. It raises
    ``ModuleNotFoundError`` for a dotted name whose *parent* is missing — which
    is precisely the state on a machine without the stack installed — so the call
    is guarded rather than trusted to return None.
    """
    absent: list[str] = []
    for module in GOOGLE_MODULES:
        try:
            if importlib.util.find_spec(module) is None:
                absent.append(module)
        except (ImportError, ValueError):
            absent.append(module)
    if not absent:
        return None
    return f"google client library not installed ({', '.join(absent)}) — install with: {INSTALL_HINT}"


def build_google_service(
    api: str,
    version: str,
    scopes: Iterable[str],
    *,
    subject: str | None = None,
    env: Mapping[str, str] | None = None,
) -> tuple[Any | None, ConnectorStatus]:
    """Build an authenticated Google API client, or explain why not. Never raises.

    Returns ``(service, status)``. ``service`` is None whenever ``status`` is
    unavailable, and the two are never inconsistent.

    Failures during credential loading report the exception *type* only. The
    message is withheld on purpose: an error raised while parsing a key file is
    the one place a library might quote the material it choked on, and a blocker
    string ends up in logs and on the thought bus. The type plus the variable
    name is enough to act on without that risk.
    """
    blocker = missing_dependency()
    if blocker:
        return None, ConnectorStatus.blocked(blocker)

    credential = resolve_credential(env)
    if not credential.found or credential.path is None:
        return None, ConnectorStatus.blocked(credential.blocker or "no credential resolved")

    source = f"env:{credential.env_var}"
    try:
        from google.oauth2 import service_account  # noqa: PLC0415  (optional dependency)
        from googleapiclient.discovery import build  # noqa: PLC0415

        creds = service_account.Credentials.from_service_account_file(
            str(credential.path), scopes=list(scopes)
        )
        if subject:
            creds = creds.with_subject(subject)
        # cache_discovery=False: the default on-disk discovery cache warns and
        # writes into the working directory, and a daemon should not depend on a
        # cache it did not ask for.
        service = build(api, version, credentials=creds, cache_discovery=False)
    except Exception as exc:  # noqa: BLE001 — an unconfigured connector reports, never throws
        LOG.debug("google %s service build failed", api, exc_info=True)
        return None, ConnectorStatus.blocked(
            f"could not build the {api} client from {credential.env_var} "
            f"({type(exc).__name__}) — check the key file, its scopes, and delegation",
            source=source,
        )

    return service, ConnectorStatus.ready(source=source)


def blocked_result(blocker: str, *, source: str = SOURCE_UNCONFIGURED) -> ConnectorResult:
    """An unavailable result. Shared so both connectors report absence identically."""
    return ConnectorResult(available=False, blocker=blocker, source=source)


def result_from_status(status: ConnectorStatus) -> ConnectorResult:
    """Carry an unavailable status out through a method that returns records."""
    return ConnectorResult(
        available=False,
        blocker=status.blocker or "connector unavailable",
        source=status.source,
    )


def env_subject(env: Mapping[str, str] | None = None) -> str | None:
    """The Workspace user to impersonate, from :data:`SUBJECT_ENV_VAR`, or None."""
    source = os.environ if env is None else env
    value = (source.get(SUBJECT_ENV_VAR) or "").strip()
    return value or None


def describe_api_failure(operation: str, exc: BaseException, *, limit: int = 200) -> str:
    """One-line blocker for a failed API call.

    Unlike credential failures, an API error message is safe to surface and is
    the only thing that distinguishes "403 insufficient scope" from "404 no such
    file" — so it is included, collapsed to one line and truncated.
    """
    text = " ".join(str(exc).split())
    if len(text) > limit:
        text = text[:limit] + "…"
    return f"{operation} failed: {type(exc).__name__}{': ' + text if text else ''}"


__all__ = [
    "Connector",
    "ConnectorResult",
    "ConnectorStatus",
    "CredentialSource",
    "CREDENTIAL_ENV_VARS",
    "GOOGLE_MODULES",
    "INSTALL_HINT",
    "SOURCE_INJECTED",
    "SOURCE_UNCONFIGURED",
    "SUBJECT_ENV_VAR",
    "blocked_result",
    "build_google_service",
    "describe_api_failure",
    "env_subject",
    "missing_dependency",
    "resolve_credential",
    "result_from_status",
]
