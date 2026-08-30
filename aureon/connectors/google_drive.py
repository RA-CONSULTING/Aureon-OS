"""Read-only Google Drive access the daemon can hold its own credentials for.

The war room this organism is reconciled against lives in Drive — the
"Aureon Grant War Room" spreadsheet that ``data/research/grants/RECONCILIATION_*.md``
compares the local ledger to. Every one of those reconciliations so far has been
performed by a human driving MCP tools in a chat window. The running system
could not open the sheet itself, so it could only ever be told what the sheet
said, second-hand and out of date. This connector is the daemon's own eye on it.

**Read-only, by scope and by surface.** The OAuth scope requested is
``drive.readonly``; there is no create, update, delete, or upload method on this
class. A caller who wants to write to Drive will not find a way to ask.

**Optional dependency.** The Google client stack is not a project dependency —
the repo installs and its tests pass with none of it present. To enable live
access::

    pip install google-api-python-client google-auth

and point ``GOOGLE_APPLICATION_CREDENTIALS`` (or ``AUREON_GOOGLE_SERVICE_ACCOUNT_JSON``)
at a service-account key *file*. Optionally set ``AUREON_GOOGLE_DELEGATED_USER``
to impersonate a Workspace user under domain-wide delegation; without it the
connector sees only the service account's own Drive and files explicitly shared
with it, which is a real and frequently surprising limitation — so
:meth:`DriveConnector.status` reports which of the two it is operating as.

With the stack absent or the credential missing, every method returns a
:class:`~aureon.connectors.base.ConnectorResult` whose ``available`` is False and
whose ``blocker`` names exactly what to fix. Nothing here raises, at import or at
first use.
"""

from __future__ import annotations

import logging
from typing import Any, Mapping

from aureon.connectors.base import (
    SOURCE_INJECTED,
    ConnectorResult,
    ConnectorStatus,
    blocked_result,
    build_google_service,
    describe_api_failure,
    env_subject,
    result_from_status,
)
from aureon.connectors.schemas import DriveContent, DriveFile

LOG = logging.getLogger("aureon.connectors.google_drive")

API_NAME = "drive"
API_VERSION = "v3"
SCOPES: tuple[str, ...] = ("https://www.googleapis.com/auth/drive.readonly",)

# The metadata actually asked for. Requesting a narrow field list is not an
# optimisation here so much as a discipline: the connector can only report what
# it asked for, and DriveFile has a field for each of these and no others.
FILE_FIELDS = "id,name,mimeType,modifiedTime,size,webViewLink"
LIST_FIELDS = f"files({FILE_FIELDS})"

DEFAULT_LIMIT = 25
MAX_LIMIT = 1000  # Drive's own pageSize ceiling.

# Text read out of a file is capped so one enormous document cannot exhaust the
# daemon's memory. The cap is on the decoded text; byte_length always reports the
# true downloaded size, so a truncated read is visibly truncated.
MAX_TEXT_CHARS = 200_000

# Native Google formats have no bytes to download — they must be exported. Only
# formats with a faithful *text* export are listed; a Google Drawing or Form has
# none, and gets a blocker rather than a silently empty string.
EXPORT_FORMATS: dict[str, str] = {
    "application/vnd.google-apps.document": "text/plain",
    "application/vnd.google-apps.spreadsheet": "text/csv",
    "application/vnd.google-apps.presentation": "text/plain",
    "application/vnd.google-apps.script": "application/vnd.google-apps.script+json",
}


def escape_query(term: str) -> str:
    """Escape a term for interpolation into a Drive ``q`` expression.

    Drive's query language quotes literals with single quotes and escapes with
    backslashes. Without this, a perfectly ordinary search — ``Gary's notes``, or
    a Windows path — produces a malformed query and a 400, which reads to a
    caller as "the connector is broken" rather than "the term needed quoting".
    """
    return term.replace("\\", "\\\\").replace("'", "\\'")


class DriveConnector:
    """Search, list and read Drive files. Never writes; never raises.

    ``service`` injects a transport (the real ``googleapiclient`` resource, or a
    fake in tests). Injection is taken at face value: a caller passing a
    transport is asserting it is already authenticated, so no credential lookup
    happens and ``status().source`` says the answer came from an injected
    transport rather than from an environment variable. That is what keeps the
    test suite hermetic without adding a "test mode" flag that could be left on.
    """

    name = "google_drive"

    def __init__(
        self,
        *,
        service: Any | None = None,
        subject: str | None = None,
        env: Mapping[str, str] | None = None,
    ) -> None:
        self._injected = service
        self._env = env
        # An explicit subject beats the environment; both may legitimately be
        # absent, in which case the service account acts as itself.
        self._subject = subject if subject is not None else env_subject(env)
        self._resolved: tuple[Any | None, ConnectorStatus] | None = None

    # ---- availability -------------------------------------------------

    def status(self) -> ConnectorStatus:
        """Reachability now. Builds the client on first call and caches it."""
        return self._resolve()[1]

    @property
    def delegated_user(self) -> str | None:
        """The Workspace user being impersonated, or None (service account as itself)."""
        return self._subject

    def _resolve(self) -> tuple[Any | None, ConnectorStatus]:
        if self._injected is not None:
            return self._injected, ConnectorStatus.ready(source=SOURCE_INJECTED)
        if self._resolved is None:
            self._resolved = build_google_service(
                API_NAME, API_VERSION, SCOPES, subject=self._subject, env=self._env
            )
        return self._resolved

    # ---- reads --------------------------------------------------------

    def search(self, query: str, *, limit: int = DEFAULT_LIMIT, raw: bool = False) -> ConnectorResult:
        """Find files whose full text or name matches ``query``.

        ``raw=True`` passes ``query`` through as a Drive ``q`` expression
        verbatim, for callers that need the real query language (mime-type
        filters, parent folders). The default wraps the term in a ``fullText``
        match, which is what "search" ordinarily means and which also matches on
        file names.

        An empty query returns a blocker rather than every file in the account:
        listing the whole Drive is what :meth:`list_recent` is for, and silently
        substituting one for the other hides a caller's bug.
        """
        term = (query or "").strip()
        if not term:
            return blocked_result("search query is empty — use list_recent() to browse instead")
        expression = term if raw else f"fullText contains '{escape_query(term)}' and trashed = false"
        return self._list(expression, limit=limit, operation="Drive files.list (search)")

    def list_recent(self, *, limit: int = DEFAULT_LIMIT) -> ConnectorResult:
        """The most recently modified files this credential can see."""
        return self._list(
            "trashed = false",
            limit=limit,
            operation="Drive files.list (recent)",
            order_by="modifiedTime desc",
        )

    def read(self, file_id: str) -> ConnectorResult:
        """Read one file's metadata and its text, when it has any.

        Two hops on purpose: the metadata call establishes the mime type, and the
        mime type decides between ``export_media`` (native Google formats, which
        have no bytes of their own) and ``get_media`` (everything else). Guessing
        one path without the other would fail on exactly the files this organism
        most needs — the war-room spreadsheet is a native Google Sheet.
        """
        identifier = (file_id or "").strip()
        if not identifier:
            return blocked_result("no file id given")

        service, status = self._resolve()
        if service is None:
            return result_from_status(status)

        try:
            meta = service.files().get(fileId=identifier, fields=FILE_FIELDS).execute()
        except Exception as exc:  # noqa: BLE001
            LOG.debug("drive files.get failed", exc_info=True)
            return blocked_result(describe_api_failure("Drive files.get", exc), source=status.source)

        descriptor = DriveFile.from_api(meta)
        mime = (descriptor.mime_type if descriptor else None) or ""
        exported_as: str | None = None

        try:
            if mime.startswith("application/vnd.google-apps."):
                export_mime = EXPORT_FORMATS.get(mime)
                if export_mime is None:
                    return blocked_result(
                        f"no text export exists for {mime} — this file type cannot be read as text",
                        source=status.source,
                    )
                exported_as = export_mime
                payload = service.files().export_media(fileId=identifier, mimeType=export_mime).execute()
            else:
                payload = service.files().get_media(fileId=identifier).execute()
        except Exception as exc:  # noqa: BLE001
            LOG.debug("drive media read failed", exc_info=True)
            return blocked_result(describe_api_failure("Drive media read", exc), source=status.source)

        content = _decode(payload, descriptor, identifier, exported_as)
        return ConnectorResult(available=True, source=status.source, records=(content,))

    # ---- shared list path ---------------------------------------------

    def _list(
        self,
        expression: str,
        *,
        limit: int,
        operation: str,
        order_by: str | None = None,
    ) -> ConnectorResult:
        service, status = self._resolve()
        if service is None:
            return result_from_status(status)

        page_size = max(1, min(int(limit), MAX_LIMIT))
        kwargs: dict[str, Any] = {"q": expression, "pageSize": page_size, "fields": LIST_FIELDS}
        if order_by:
            kwargs["orderBy"] = order_by

        try:
            response = service.files().list(**kwargs).execute()
        except Exception as exc:  # noqa: BLE001
            LOG.debug("drive files.list failed", exc_info=True)
            return blocked_result(describe_api_failure(operation, exc), source=status.source)

        rows = response.get("files") if isinstance(response, dict) else None
        if not isinstance(rows, list):
            # A response without a `files` list is not an empty Drive; it is a
            # response this code did not understand, and saying so beats
            # reporting zero results that were never counted.
            return blocked_result(
                f"{operation} returned no 'files' list — response shape not understood",
                source=status.source,
            )

        files = tuple(f for f in (DriveFile.from_api(r) for r in rows) if f is not None)
        return ConnectorResult(available=True, source=status.source, records=files)


# ---- helpers ----------------------------------------------------------


def _decode(payload: Any, descriptor: DriveFile | None, file_id: str, exported_as: str | None) -> DriveContent:
    """Turn downloaded bytes into :class:`DriveContent`, honestly.

    Strict UTF-8 on purpose. ``errors="replace"`` would always "succeed" and hand
    back a string of replacement characters for a PDF — content-shaped output
    carrying no content. A file that is not UTF-8 text gets ``text=None`` and a
    ``decode_error`` saying so, which a caller can act on.
    """
    raw = payload if isinstance(payload, (bytes, bytearray)) else None
    if raw is None and isinstance(payload, str):
        # Some transports hand back an already-decoded string.
        text, byte_length, decode_error = payload, len(payload.encode("utf-8")), None
    elif raw is None:
        text, byte_length = None, 0
        decode_error = f"media download returned {type(payload).__name__}, not bytes"
    else:
        byte_length = len(raw)
        try:
            text, decode_error = bytes(raw).decode("utf-8"), None
        except UnicodeDecodeError as exc:
            text, decode_error = None, f"not UTF-8 text ({exc.reason})"

    truncated = False
    if text is not None and len(text) > MAX_TEXT_CHARS:
        text, truncated = text[:MAX_TEXT_CHARS], True

    return DriveContent(
        file_id=file_id,
        name=descriptor.name if descriptor else None,
        mime_type=descriptor.mime_type if descriptor else None,
        text=text,
        byte_length=byte_length,
        truncated=truncated,
        decode_error=decode_error,
        exported_as=exported_as,
    )


__all__ = ["DriveConnector", "API_NAME", "API_VERSION", "SCOPES", "EXPORT_FORMATS", "escape_query"]
