"""The team's access layer — the daemon's own hands on Drive and Gmail.

Everything Aureon knows about the outside world it has been *told*, by a human
in an interactive session driving MCP tools. Those tools are not available to
the running system: no chat window at 03:00, no consent screen, no one to click
it. So the grant organ could read its own ledger but not the war-room sheet that
ledger is reconciled against, and could see a deadline but never the reply that
moved it.

This package closes that gap with its own integration:

- :mod:`aureon.connectors.base` — the :class:`Connector` protocol and
  :class:`ConnectorStatus`, whose invariant makes "quietly unavailable"
  unrepresentable: available means no blocker, unavailable means a stated one.
- :mod:`aureon.connectors.google_drive` — search / read / list_recent, scoped
  ``drive.readonly``.
- :mod:`aureon.connectors.gmail` — search_threads / read_thread, scoped
  ``gmail.readonly``, **with no send or draft method at all**. That absence is
  the enforcement of the war room's own rule: no email send without Gary's
  approval. A class that cannot send cannot be argued into sending.

Both connectors are read-only, both construct without credentials, and neither
raises — on import, on first use, or ever. Absent configuration produces a
blocker naming exactly what is missing.

The Google client stack is an **optional** dependency, deliberately absent from
``pyproject.toml`` so the repo installs and its tests run offline::

    pip install google-api-python-client google-auth

Nothing here writes, sends, files, or pays. Those verbs have no executor in this
repository — see :data:`aureon.gates.switchboard.HUMAN_HELD` — and this package
does not give them one.
"""

from aureon.connectors.base import (
    Connector,
    ConnectorResult,
    ConnectorStatus,
    CredentialSource,
    missing_dependency,
    resolve_credential,
)
from aureon.connectors.gmail import GmailConnector
from aureon.connectors.google_drive import DriveConnector
from aureon.connectors.schemas import DriveContent, DriveFile, GmailMessage, GmailThread

__all__ = [
    "Connector",
    "ConnectorResult",
    "ConnectorStatus",
    "CredentialSource",
    "DriveConnector",
    "DriveContent",
    "DriveFile",
    "GmailConnector",
    "GmailMessage",
    "GmailThread",
    "missing_dependency",
    "resolve_credential",
]
