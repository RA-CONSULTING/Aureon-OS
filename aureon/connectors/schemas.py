"""Record shapes for the connector package.

One rule governs every field here: **a value is what the API returned, or it is
None.** No zeros for unknown sizes, no empty strings for absent subjects, no
"now" for a missing timestamp. The Google list and get endpoints return
genuinely different amounts of information about the same object — a thread from
``threads.list`` has no subject and no message count, while the same thread from
``threads.get`` has both — and these types are built so that difference stays
visible instead of being papered over with defaults.

Timestamps are kept as the raw RFC-3339 strings Google sends. Parsing them into
``datetime`` here would mean inventing a timezone for any value that omits one,
and :mod:`aureon.grants.schemas` already owns the one parser in this repo that
is honest about that (``parse_dt``). A caller that needs datetimes should use it
rather than have this layer guess.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DriveFile:
    """One file's metadata as Drive reported it.

    ``size`` is None for anything Drive does not report a byte count for — which
    includes every native Google Docs/Sheets/Slides file. That is a real absence,
    not a zero-byte file, and the two must not be confused by a caller totalling
    storage.
    """

    id: str
    name: str | None = None
    mime_type: str | None = None
    modified_time: str | None = None
    size: int | None = None
    web_view_link: str | None = None

    @property
    def is_google_native(self) -> bool:
        """True for Docs/Sheets/Slides — files that must be exported, not downloaded."""
        return bool(self.mime_type and self.mime_type.startswith("application/vnd.google-apps."))

    @classmethod
    def from_api(cls, raw: Any) -> DriveFile | None:
        """Build from a ``files.list`` / ``files.get`` entry, or None if it carries no id.

        A response row without an id is not a file this code can do anything
        with, so it yields None rather than a husk with an invented identifier.
        """
        if not isinstance(raw, dict):
            return None
        file_id = str(raw.get("id") or "").strip()
        if not file_id:
            return None
        # Drive sends `size` as a decimal *string*. A value that will not parse
        # is unknown, not zero.
        size: int | None = None
        raw_size = raw.get("size")
        if raw_size is not None and not isinstance(raw_size, bool):
            try:
                size = int(str(raw_size).strip())
            except (TypeError, ValueError):
                size = None
        return cls(
            id=file_id,
            name=text_or_none(raw.get("name")),
            mime_type=text_or_none(raw.get("mimeType")),
            modified_time=text_or_none(raw.get("modifiedTime")),
            size=size,
            web_view_link=text_or_none(raw.get("webViewLink")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "mime_type": self.mime_type,
            "modified_time": self.modified_time,
            "size": self.size,
            "web_view_link": self.web_view_link,
        }


@dataclass(frozen=True)
class DriveContent:
    """One file's bytes, decoded if they are UTF-8 text.

    ``text`` is None when the bytes are not valid UTF-8 — a PDF or an image is
    not text, and returning mojibake from ``errors="replace"`` would hand a
    caller a string that looks like content but carries no meaning.
    ``decode_error`` says which it was. ``byte_length`` is always the real
    downloaded length, even when ``truncated`` is set, so a caller can see how
    much it is *not* looking at.
    """

    file_id: str
    name: str | None = None
    mime_type: str | None = None
    text: str | None = None
    byte_length: int = 0
    truncated: bool = False
    decode_error: str | None = None
    exported_as: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_id": self.file_id,
            "name": self.name,
            "mime_type": self.mime_type,
            "text_length": len(self.text) if self.text is not None else None,
            "byte_length": self.byte_length,
            "truncated": self.truncated,
            "decode_error": self.decode_error,
            "exported_as": self.exported_as,
        }


@dataclass(frozen=True)
class GmailMessage:
    """One message inside a thread. Header fields are None when absent.

    ``body_mime`` says what ``body_text`` actually is. Plenty of real mail —
    funder replies among it — carries no ``text/plain`` part at all, and the
    choice was between dropping those bodies entirely or handing back HTML
    labelled as text. Neither is acceptable, so the body is returned with its
    own mime type attached and the caller decides. ``body_text`` is None only
    when there was genuinely nothing to decode.
    """

    id: str
    thread_id: str | None = None
    sender: str | None = None
    recipient: str | None = None
    subject: str | None = None
    date: str | None = None
    snippet: str | None = None
    body_text: str | None = None
    body_mime: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "thread_id": self.thread_id,
            "sender": self.sender,
            "recipient": self.recipient,
            "subject": self.subject,
            "date": self.date,
            "snippet": self.snippet,
            "body_mime": self.body_mime,
            "body_length": len(self.body_text) if self.body_text is not None else None,
        }


@dataclass(frozen=True)
class GmailThread:
    """A conversation.

    ``message_count`` is None after a ``threads.list`` call and an integer after
    ``threads.get``, because the list endpoint genuinely does not report it.
    Defaulting it to 0, or to ``len(messages)`` when messages were never fetched,
    would turn "not asked" into "none exist".
    """

    id: str
    subject: str | None = None
    snippet: str | None = None
    message_count: int | None = None
    messages: tuple[GmailMessage, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "subject": self.subject,
            "snippet": self.snippet,
            "message_count": self.message_count,
            "messages": [m.to_dict() for m in self.messages],
        }


def text_or_none(value: Any) -> str | None:
    """A non-empty string, or None. Never an empty string standing in for absence.

    Shared by both connectors on purpose: ``""`` and ``None`` mean different
    things throughout this package (a subject that is blank versus a subject the
    API never sent), and one implementation of that distinction is safer than
    two that could drift.
    """
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


__all__ = ["DriveContent", "DriveFile", "GmailMessage", "GmailThread", "text_or_none"]
