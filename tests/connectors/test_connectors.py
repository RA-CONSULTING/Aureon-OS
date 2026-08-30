"""The access layer: absent by default, honest when blocked, incapable of sending.

Every test here is hermetic. No network, no credential, no ``os.environ`` — each
connector is handed an explicit ``env`` mapping and, where a response is needed,
a FAKE transport injected through the constructor. The Google client stack is
not installed in this environment and these tests must pass whether it is or
not, so anything that depends on its presence monkeypatches the probe rather
than assuming an answer.

Three properties are load-bearing and each has a test that fails loudly if it
ever stops holding:

1. An unconfigured connector **reports** absence — it never raises, and it never
   returns an empty list that a caller could mistake for "nothing found".
2. A blocker never carries credential material.
3. :class:`GmailConnector` has no send path, and cannot grow one without this
   suite going red.
"""

from __future__ import annotations

import base64
import re

import pytest

from aureon.connectors import (
    Connector,
    ConnectorResult,
    ConnectorStatus,
    DriveConnector,
    DriveContent,
    DriveFile,
    GmailConnector,
    GmailThread,
    missing_dependency,
    resolve_credential,
)
from aureon.connectors import base as base_module
from aureon.connectors import gmail as gmail_module
from aureon.connectors.base import CREDENTIAL_ENV_VARS, INSTALL_HINT, SUBJECT_ENV_VAR
from aureon.connectors.gmail import NO_WRITE_VERBS
from aureon.connectors.google_drive import EXPORT_FORMATS, escape_query
from aureon.gates.switchboard import is_human_held

# A mailbox and a key path that do not exist. If a connector ever produced a
# result for these, it would be talking to something it was not given.
FAKE_MAILBOX = "nobody@example.invalid"
EMPTY_ENV: dict[str, str] = {}


# --------------------------------------------------------------------------
# Fake transports — the shape googleapiclient's discovery resources present.
# --------------------------------------------------------------------------


class _Exec:
    """A pending request. ``execute()`` returns a canned result or raises."""

    def __init__(self, result=None, error: BaseException | None = None) -> None:
        self._result = result
        self._error = error

    def execute(self, **_kwargs):
        if self._error is not None:
            raise self._error
        return self._result


class FakeDriveFiles:
    def __init__(self, *, listing=None, meta=None, media=None, exports=None, error=None) -> None:
        self._listing = listing
        self._meta = meta or {}
        self._media = media or {}
        self._exports = exports or {}
        self._error = error
        self.calls: list[tuple[str, dict]] = []

    def list(self, **kwargs):
        self.calls.append(("list", kwargs))
        return _Exec(self._listing, self._error)

    def get(self, **kwargs):
        self.calls.append(("get", kwargs))
        return _Exec(self._meta.get(kwargs.get("fileId")), self._error)

    def get_media(self, **kwargs):
        self.calls.append(("get_media", kwargs))
        return _Exec(self._media.get(kwargs.get("fileId")), self._error)

    def export_media(self, **kwargs):
        self.calls.append(("export_media", kwargs))
        return _Exec(self._exports.get((kwargs.get("fileId"), kwargs.get("mimeType"))), self._error)


class FakeDriveService:
    def __init__(self, files: FakeDriveFiles) -> None:
        self._files = files

    def files(self):
        return self._files


class FakeThreadsResource:
    def __init__(self, *, listing=None, threads=None, error=None) -> None:
        self._listing = listing
        self._threads = threads or {}
        self._error = error
        self.calls: list[tuple[str, dict]] = []

    def list(self, **kwargs):
        self.calls.append(("list", kwargs))
        return _Exec(self._listing, self._error)

    def get(self, **kwargs):
        self.calls.append(("get", kwargs))
        return _Exec(self._threads.get(kwargs.get("id")), self._error)


class FakeGmailService:
    def __init__(self, threads: FakeThreadsResource) -> None:
        self._threads = threads

    def users(self):
        return self

    def threads(self):
        return self._threads


def _b64(text: str) -> str:
    """Gmail's base64url encoding, padding stripped exactly as the API does."""
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii").rstrip("=")


# --------------------------------------------------------------------------
# 1. Absence is reported, never thrown
# --------------------------------------------------------------------------


def test_unconfigured_connectors_construct_without_raising():
    """Construction must not touch credentials, the filesystem, or the network."""
    drive = DriveConnector(env=EMPTY_ENV)
    mail = GmailConnector(env=EMPTY_ENV)
    assert drive.name == "google_drive"
    assert mail.name == "gmail"
    # Nothing resolved yet: the client is built on first use, not on construction.
    assert drive._resolved is None
    assert mail._resolved is None


def test_missing_credential_reports_unavailable_with_a_blocker(monkeypatch):
    """No credential -> available False and a blocker naming the variables to set."""
    # Pin the dependency probe so this test exercises the credential path on any
    # machine, installed stack or not.
    monkeypatch.setattr(base_module, "missing_dependency", lambda: None)

    status = DriveConnector(env=EMPTY_ENV).status()
    assert status.available is False
    assert status.blocker
    for var in CREDENTIAL_ENV_VARS:
        assert var in status.blocker


def test_missing_dependency_blocker_names_the_pip_line(monkeypatch):
    monkeypatch.setattr(
        base_module, "missing_dependency", lambda: f"google client library not installed — {INSTALL_HINT}"
    )
    status = DriveConnector(env=dict.fromkeys(CREDENTIAL_ENV_VARS, "x")).status()
    assert status.available is False
    assert INSTALL_HINT in (status.blocker or "")


def test_real_dependency_probe_is_honest_about_this_environment():
    """Whatever the probe says, it says it in a form an operator can act on."""
    blocker = missing_dependency()
    if blocker is not None:
        assert INSTALL_HINT in blocker


@pytest.mark.parametrize(
    "call",
    [
        lambda c: c.search("war room"),
        lambda c: c.list_recent(),
        lambda c: c.read("some-file-id"),
    ],
    ids=["search", "list_recent", "read"],
)
def test_every_drive_method_returns_a_blocked_result_when_unconfigured(call):
    result = call(DriveConnector(env=EMPTY_ENV))
    assert isinstance(result, ConnectorResult)
    assert isinstance(result, ConnectorStatus)  # the result IS a status
    assert result.available is False
    assert result.blocker
    assert result.records == ()


@pytest.mark.parametrize(
    "call",
    [lambda c: c.search_threads("newer_than:7d"), lambda c: c.read_thread("t1")],
    ids=["search_threads", "read_thread"],
)
def test_every_gmail_method_returns_a_blocked_result_when_unconfigured(call):
    result = call(GmailConnector(env=EMPTY_ENV))
    assert result.available is False
    assert result.blocker
    assert result.records == ()


def test_gmail_without_a_delegated_mailbox_says_so_precisely():
    """A service account has no mailbox; the blocker must name the fix."""
    status = GmailConnector(env=EMPTY_ENV).status()
    assert status.available is False
    assert SUBJECT_ENV_VAR in (status.blocker or "")
    assert GmailConnector(env=EMPTY_ENV).mailbox is None


def test_connectors_satisfy_the_connector_protocol():
    assert isinstance(DriveConnector(env=EMPTY_ENV), Connector)
    assert isinstance(GmailConnector(env=EMPTY_ENV), Connector)


# --------------------------------------------------------------------------
# 2. Credentials: a path, never an inline secret, never echoed
# --------------------------------------------------------------------------


def test_resolve_credential_with_nothing_set_lists_every_reason():
    source = resolve_credential(EMPTY_ENV)
    assert source.found is False
    assert source.path is None
    for var in CREDENTIAL_ENV_VARS:
        assert f"{var} is not set" in (source.blocker or "")


def test_resolve_credential_prefers_the_google_standard_variable(tmp_path):
    first = tmp_path / "standard.json"
    second = tmp_path / "aureon.json"
    first.write_text("{}", encoding="utf-8")
    second.write_text("{}", encoding="utf-8")
    source = resolve_credential(
        {"GOOGLE_APPLICATION_CREDENTIALS": str(first), "AUREON_GOOGLE_SERVICE_ACCOUNT_JSON": str(second)}
    )
    assert source.found is True
    assert source.env_var == "GOOGLE_APPLICATION_CREDENTIALS"
    assert source.path == first


def test_resolve_credential_falls_through_to_the_aureon_variable(tmp_path):
    key = tmp_path / "aureon.json"
    key.write_text("{}", encoding="utf-8")
    source = resolve_credential(
        {"GOOGLE_APPLICATION_CREDENTIALS": str(tmp_path / "absent.json"),
         "AUREON_GOOGLE_SERVICE_ACCOUNT_JSON": str(key)}
    )
    assert source.found is True
    assert source.env_var == "AUREON_GOOGLE_SERVICE_ACCOUNT_JSON"


def test_inline_json_credential_is_refused_and_never_echoed():
    """A pasted key is a leak. It is rejected, and its content is not repeated."""
    secret = '{"private_key": "-----BEGIN PRIVATE KEY-----SENTINEL-----"}'
    source = resolve_credential({"AUREON_GOOGLE_SERVICE_ACCOUNT_JSON": secret})
    assert source.found is False
    assert "inline JSON" in (source.blocker or "")
    assert "SENTINEL" not in (source.blocker or "")
    assert "BEGIN PRIVATE KEY" not in (source.blocker or "")


def test_missing_credential_file_blocker_names_the_variable_and_the_path(tmp_path):
    absent = tmp_path / "no-such-key.json"
    source = resolve_credential({"GOOGLE_APPLICATION_CREDENTIALS": str(absent)})
    assert source.found is False
    assert "GOOGLE_APPLICATION_CREDENTIALS" in (source.blocker or "")
    assert str(absent) in (source.blocker or "")


def test_a_directory_is_not_a_key_file(tmp_path):
    source = resolve_credential({"GOOGLE_APPLICATION_CREDENTIALS": str(tmp_path)})
    assert source.found is False
    assert "directory" in (source.blocker or "")


def test_a_failed_client_build_never_leaks_the_key_file_contents(tmp_path, monkeypatch):
    """The build fails (no google stack here). The blocker must not quote the key."""
    key = tmp_path / "key.json"
    key.write_text('{"private_key": "SENTINEL-KEY-MATERIAL", "client_email": "x@y.iam"}', encoding="utf-8")
    monkeypatch.setattr(base_module, "missing_dependency", lambda: None)

    service, status = base_module.build_google_service(
        "drive", "v3", ("scope",), env={"GOOGLE_APPLICATION_CREDENTIALS": str(key)}
    )
    assert service is None
    assert status.available is False
    assert "SENTINEL-KEY-MATERIAL" not in (status.blocker or "")
    assert "x@y.iam" not in (status.blocker or "")
    # Still actionable: it names the variable and the exception type.
    assert "GOOGLE_APPLICATION_CREDENTIALS" in (status.blocker or "")


# --------------------------------------------------------------------------
# 3. Gmail cannot send. This is structural, not a policy flag.
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "forbidden",
    ["send", "send_message", "send_email", "draft", "create_draft", "reply", "forward",
     "trash", "delete", "modify", "insert", "compose"],
)
def test_gmail_connector_has_no_write_method(forbidden):
    assert not hasattr(GmailConnector, forbidden)
    assert not hasattr(GmailConnector(env=EMPTY_ENV), forbidden)


def _public_names(obj) -> set[str]:
    return {n for n in dir(obj) if not n.startswith("_")}


def _tokens(name: str) -> set[str]:
    return {t for t in re.split(r"[^a-z0-9]+", name.lower()) if t}


def test_no_public_gmail_attribute_names_a_write_verb():
    """The whole surface is scanned, so adding ``send_reply`` later fails here."""
    for name in _public_names(GmailConnector):
        overlap = _tokens(name) & NO_WRITE_VERBS
        assert not overlap, f"GmailConnector.{name} exposes a write verb: {sorted(overlap)}"


def test_no_public_connector_attribute_names_a_human_held_action():
    """Cross-checked against the switchboard's own vocabulary of held verbs.

    ``aureon.gates.switchboard.HUMAN_HELD`` is the repo's statement about which
    actions have no automatic executor — submit, file, lodge, pay, transfer,
    withdraw, wire. No connector may quietly become one of those hands.
    """
    for cls in (GmailConnector, DriveConnector):
        for name in _public_names(cls):
            assert not is_human_held(name), f"{cls.__name__}.{name} names a human-held action"


def test_gmail_exposes_only_the_two_documented_reads():
    surface = _public_names(GmailConnector) - {"name", "status", "mailbox"}
    assert surface == {"search_threads", "read_thread"}


def test_drive_exposes_only_reads():
    surface = _public_names(DriveConnector) - {"name", "status", "delegated_user"}
    assert surface == {"search", "list_recent", "read"}


# --------------------------------------------------------------------------
# 4. ConnectorStatus cannot be constructed dishonestly
# --------------------------------------------------------------------------


def test_available_status_cannot_carry_a_blocker():
    with pytest.raises(ValueError):
        ConnectorStatus(available=True, blocker="something")


def test_unavailable_status_must_state_a_blocker():
    with pytest.raises(ValueError):
        ConnectorStatus(available=False)


def test_result_is_a_status_and_reports_its_records():
    result = ConnectorResult(available=True, source="injected transport", records=(DriveFile(id="a"),))
    assert isinstance(result, ConnectorStatus)
    assert result.record.id == "a"
    assert result.to_dict()["record_count"] == 1
    assert ConnectorResult(available=True, source="x").record is None


# --------------------------------------------------------------------------
# 5. A fake response parses correctly — Drive
# --------------------------------------------------------------------------


def _drive(files: FakeDriveFiles) -> DriveConnector:
    return DriveConnector(service=FakeDriveService(files), env=EMPTY_ENV)


def test_injected_transport_is_available_and_says_where_it_came_from():
    connector = _drive(FakeDriveFiles(listing={"files": []}))
    status = connector.status()
    assert status.available is True
    assert status.blocker is None
    assert status.source == "injected transport"


def test_drive_search_parses_a_fake_response():
    files = FakeDriveFiles(
        listing={
            "files": [
                {
                    "id": "1abc",
                    "name": "Aureon Grant War Room",
                    "mimeType": "application/vnd.google-apps.spreadsheet",
                    "modifiedTime": "2026-07-31T00:00:44.000Z",
                    "webViewLink": "https://drive.example.invalid/1abc",
                },
                {"id": "2def", "name": "notes.txt", "mimeType": "text/plain", "size": "4096"},
            ]
        }
    )
    result = _drive(files).search("war room")

    assert result.available is True
    assert result.blocker is None
    assert [f.id for f in result.records] == ["1abc", "2def"]

    sheet, note = result.records
    assert sheet.name == "Aureon Grant War Room"
    assert sheet.is_google_native is True
    # Drive reports no size for a native Google file. That is unknown, not zero.
    assert sheet.size is None
    assert note.size == 4096
    assert note.is_google_native is False

    method, kwargs = files.calls[0]
    assert method == "list"
    assert kwargs["q"] == "fullText contains 'war room' and trashed = false"


def test_drive_search_escapes_apostrophes_instead_of_breaking_the_query():
    files = FakeDriveFiles(listing={"files": []})
    _drive(files).search("Gary's notes")
    assert files.calls[0][1]["q"] == "fullText contains 'Gary\\'s notes' and trashed = false"
    assert escape_query("a\\b'c") == "a\\\\b\\'c"


def test_drive_raw_query_is_passed_through_verbatim():
    files = FakeDriveFiles(listing={"files": []})
    _drive(files).search("mimeType = 'application/pdf'", raw=True)
    assert files.calls[0][1]["q"] == "mimeType = 'application/pdf'"


def test_drive_empty_search_is_refused_rather_than_listing_everything():
    files = FakeDriveFiles(listing={"files": [{"id": "x"}]})
    result = _drive(files).search("   ")
    assert result.available is False
    assert "empty" in (result.blocker or "")
    assert files.calls == []  # nothing was asked of the transport


def test_drive_list_recent_orders_by_modified_time():
    files = FakeDriveFiles(listing={"files": [{"id": "x", "name": "recent"}]})
    result = _drive(files).list_recent(limit=5)
    assert result.available is True
    assert result.records[0].name == "recent"
    _, kwargs = files.calls[0]
    assert kwargs["orderBy"] == "modifiedTime desc"
    assert kwargs["pageSize"] == 5
    assert kwargs["q"] == "trashed = false"


def test_drive_empty_result_is_available_and_empty_not_blocked():
    """Nothing found is a real answer and must not look like a failure."""
    result = _drive(FakeDriveFiles(listing={"files": []})).search("nothing matches this")
    assert result.available is True
    assert result.records == ()
    assert result.blocker is None


def test_drive_unrecognised_response_shape_is_a_blocker_not_zero_results():
    result = _drive(FakeDriveFiles(listing={"unexpected": True})).search("x")
    assert result.available is False
    assert "not understood" in (result.blocker or "")


def test_drive_api_error_becomes_a_blocker_never_an_exception():
    files = FakeDriveFiles(error=RuntimeError("403 insufficient scope"))
    result = _drive(files).search("x")
    assert result.available is False
    assert "RuntimeError" in (result.blocker or "")
    assert "403 insufficient scope" in (result.blocker or "")


def test_drive_reads_a_plain_text_file():
    files = FakeDriveFiles(
        meta={"2def": {"id": "2def", "name": "notes.txt", "mimeType": "text/plain", "size": "11"}},
        media={"2def": b"hello world"},
    )
    result = _drive(files).read("2def")

    assert result.available is True
    content = result.record
    assert isinstance(content, DriveContent)
    assert content.text == "hello world"
    assert content.byte_length == 11
    assert content.truncated is False
    assert content.decode_error is None
    assert content.exported_as is None


def test_drive_exports_a_native_google_sheet_as_csv():
    """The war-room sheet has no bytes of its own; it must be exported."""
    export_mime = EXPORT_FORMATS["application/vnd.google-apps.spreadsheet"]
    assert export_mime == "text/csv"
    files = FakeDriveFiles(
        meta={"1abc": {"id": "1abc", "name": "War Room",
                       "mimeType": "application/vnd.google-apps.spreadsheet"}},
        exports={("1abc", export_mime): b"Rank,Opportunity\n1,Compliance blocker\n"},
    )
    result = _drive(files).read("1abc")

    content = result.record
    assert result.available is True
    assert content.text.startswith("Rank,Opportunity")
    assert content.exported_as == "text/csv"
    assert ("export_media", {"fileId": "1abc", "mimeType": "text/csv"}) in files.calls


def test_drive_refuses_a_google_type_with_no_text_export():
    files = FakeDriveFiles(
        meta={"draw": {"id": "draw", "name": "diagram",
                       "mimeType": "application/vnd.google-apps.drawing"}}
    )
    result = _drive(files).read("draw")
    assert result.available is False
    assert "no text export" in (result.blocker or "")


def test_drive_non_utf8_bytes_yield_no_text_rather_than_mojibake():
    files = FakeDriveFiles(
        meta={"pdf": {"id": "pdf", "name": "scan.pdf", "mimeType": "application/pdf"}},
        media={"pdf": b"%PDF-1.4\xff\xfe\x00binary"},
    )
    content = _drive(files).read("pdf").record
    assert content.text is None
    assert "not UTF-8" in (content.decode_error or "")
    assert content.byte_length == len(b"%PDF-1.4\xff\xfe\x00binary")


def test_drive_truncates_a_huge_file_and_says_so(monkeypatch):
    from aureon.connectors import google_drive as drive_module

    monkeypatch.setattr(drive_module, "MAX_TEXT_CHARS", 10)
    files = FakeDriveFiles(
        meta={"big": {"id": "big", "name": "big.txt", "mimeType": "text/plain"}},
        media={"big": b"x" * 50},
    )
    content = _drive(files).read("big").record
    assert content.truncated is True
    assert len(content.text) == 10
    assert content.byte_length == 50  # the true size, not the truncated one


def test_drive_read_without_an_id_is_refused():
    files = FakeDriveFiles()
    result = _drive(files).read("")
    assert result.available is False
    assert files.calls == []


def test_drive_file_rows_without_an_id_are_dropped_not_invented():
    assert DriveFile.from_api({"name": "orphan"}) is None
    assert DriveFile.from_api("not a dict") is None
    # A boolean size is not 1 byte, and an unparsable one is unknown.
    assert DriveFile.from_api({"id": "a", "size": True}).size is None
    assert DriveFile.from_api({"id": "a", "size": "not-a-number"}).size is None
    assert DriveFile.from_api({"id": "a", "name": "   "}).name is None


# --------------------------------------------------------------------------
# 6. A fake response parses correctly — Gmail
# --------------------------------------------------------------------------


def _mail(threads: FakeThreadsResource) -> GmailConnector:
    return GmailConnector(service=FakeGmailService(threads), subject=FAKE_MAILBOX, env=EMPTY_ENV)


def test_gmail_search_returns_stubs_without_inventing_subjects():
    """threads.list reports no subject and no count. Neither may be guessed."""
    threads = FakeThreadsResource(
        listing={"threads": [{"id": "t1", "snippet": "Re: your application"},
                             {"id": "t2", "snippet": "Deadline extended"}]}
    )
    result = _mail(threads).search_threads("from:funder.example newer_than:7d")

    assert result.available is True
    assert [t.id for t in result.records] == ["t1", "t2"]
    first: GmailThread = result.records[0]
    assert first.snippet == "Re: your application"
    assert first.subject is None
    assert first.message_count is None
    assert first.messages == ()

    _, kwargs = threads.calls[0]
    assert kwargs["q"] == "from:funder.example newer_than:7d"
    assert kwargs["userId"] == "me"


def test_gmail_no_matches_is_an_empty_available_result():
    """Gmail omits the key entirely when nothing matches — a real empty answer."""
    result = _mail(FakeThreadsResource(listing={})).search_threads("subject:nothing")
    assert result.available is True
    assert result.records == ()
    assert result.blocker is None


def test_gmail_empty_query_is_refused():
    threads = FakeThreadsResource(listing={"threads": [{"id": "t1"}]})
    result = _mail(threads).search_threads("")
    assert result.available is False
    assert threads.calls == []


def test_gmail_reads_a_thread_and_prefers_plain_text_over_html():
    """The HTML part comes FIRST in this tree; text/plain must still win."""
    thread = {
        "id": "t1",
        "snippet": "Re: AUR-GRANT-003",
        "messages": [
            {
                "id": "m1",
                "threadId": "t1",
                "snippet": "Thanks for your application",
                "payload": {
                    "mimeType": "multipart/mixed",
                    "headers": [
                        {"name": "From", "value": "Assessor <assessor@funder.invalid>"},
                        {"name": "To", "value": FAKE_MAILBOX},
                        {"name": "Subject", "value": "Re: AUR-GRANT-003"},
                        {"name": "Date", "value": "Fri, 31 Jul 2026 09:14:00 +0100"},
                    ],
                    "parts": [
                        {
                            "mimeType": "multipart/alternative",
                            "parts": [
                                {"mimeType": "text/html",
                                 "body": {"data": _b64("<p>markup</p>")}},
                                {"mimeType": "text/plain; charset=UTF-8",
                                 "body": {"data": _b64("the real text")}},
                            ],
                        },
                        {"mimeType": "application/pdf", "body": {"attachmentId": "a1"}},
                    ],
                },
            },
            {
                "id": "m2",
                "threadId": "t1",
                "payload": {
                    "mimeType": "text/plain",
                    "headers": [{"name": "from", "value": "gary@example.invalid"}],
                    "body": {"data": _b64("our reply")},
                },
            },
        ],
    }
    result = _mail(FakeThreadsResource(threads={"t1": thread})).read_thread("t1")

    assert result.available is True
    conversation: GmailThread = result.record
    assert conversation.id == "t1"
    assert conversation.message_count == 2
    assert conversation.subject == "Re: AUR-GRANT-003"

    first, second = conversation.messages
    assert first.sender == "Assessor <assessor@funder.invalid>"
    assert first.recipient == FAKE_MAILBOX
    assert first.date == "Fri, 31 Jul 2026 09:14:00 +0100"
    assert first.body_text == "the real text"
    assert first.body_mime == "text/plain"
    # Lower-cased header name still found; no plain part means no subject.
    assert second.sender == "gary@example.invalid"
    assert second.subject is None
    assert second.body_text == "our reply"


def test_gmail_html_only_body_is_returned_labelled_as_html():
    thread = {
        "id": "t2",
        "messages": [
            {
                "id": "m1",
                "payload": {
                    "mimeType": "text/html",
                    "headers": [{"name": "Subject", "value": "HTML only"}],
                    "body": {"data": _b64("<p>only markup here</p>")},
                },
            }
        ],
    }
    message = _mail(FakeThreadsResource(threads={"t2": thread})).read_thread("t2").record.messages[0]
    assert message.body_mime == "text/html"
    assert "only markup here" in message.body_text


def test_gmail_message_with_no_decodable_body_reports_none():
    thread = {"id": "t3", "messages": [{"id": "m1", "payload": {"mimeType": "multipart/mixed",
                                                                "parts": [{"mimeType": "image/png",
                                                                           "body": {"attachmentId": "a"}}]}}]}
    message = _mail(FakeThreadsResource(threads={"t3": thread})).read_thread("t3").record.messages[0]
    assert message.body_text is None
    assert message.body_mime is None


def test_gmail_thread_with_no_messages_key_leaves_the_count_unknown():
    """"Not returned" and "zero messages" are different answers."""
    result = _mail(FakeThreadsResource(threads={"t4": {"id": "t4"}})).read_thread("t4")
    conversation = result.record
    assert conversation.message_count is None
    assert conversation.messages == ()
    assert conversation.subject is None


def test_gmail_api_error_becomes_a_blocker_never_an_exception():
    threads = FakeThreadsResource(error=RuntimeError("404 thread not found"))
    result = _mail(threads).read_thread("missing")
    assert result.available is False
    assert "RuntimeError" in (result.blocker or "")


def test_gmail_body_decoder_survives_malformed_base64():
    assert gmail_module._decode_b64("!!!not base64!!!") is None
    assert gmail_module._decode_b64("") is None
    assert gmail_module._decode_b64(None) is None
    # Gmail strips padding; the decoder restores it.
    assert gmail_module._decode_b64(_b64("padded?")) == "padded?"


def test_gmail_body_walk_cannot_spin_on_a_cyclic_tree():
    """A malformed tree must terminate, not hang the daemon."""
    part: dict = {"mimeType": "multipart/mixed", "parts": []}
    part["parts"].append(part)  # self-referential
    found: dict[str, str] = {}
    gmail_module._collect(part, found)
    assert found == {}
