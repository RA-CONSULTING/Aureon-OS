"""
ApprovalQueue + ApprovalEmail — the director's desk: prepare → propose → (human)
decide → record. The load-bearing property under test: it RECORDS the human decision
and NEVER executes the live move.

Offline + hermetic: an isolated trace dir and a stub email transport (no network).
Proves proposing enqueues a pending item (deduped, bounded), deciding folds to the
latest status, nothing executes, and the email loop notifies only the owner and
records replies without ever firing anything.
"""

from __future__ import annotations

import pytest

from aureon.core.approval_queue import ApprovalQueue


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("AUREON_BUS_TRACE_DIR", str(tmp_path))
    import aureon.core.approval_queue as aq
    import aureon.operator.approval_email as ae

    monkeypatch.setattr(aq, "_queue", None, raising=False)
    monkeypatch.setattr(ae, "_email", None, raising=False)
    return tmp_path


# ── propose / decide: records, never executes ────────────────────────────────

def test_propose_enqueues_pending():
    q = ApprovalQueue()
    i = q.propose("trade", "buy 0.1 BTC at market", {"symbol": "BTC"}, "soul")
    assert i and len(q.pending()) == 1
    item = q.get(i)
    assert item["status"] == "pending" and item["kind"] == "trade" and item["requires_human"] is True


def test_propose_dedupes_open_items():
    q = ApprovalQueue()
    a = q.propose("trade", "buy 0.1 BTC", {}, "soul")
    b = q.propose("trade", "buy 0.1 BTC", {}, "soul")
    assert a and b is None and len(q.pending()) == 1


def test_decide_folds_to_latest_status():
    q = ApprovalQueue()
    i = q.propose("payment", "wire 500 to supplier", {}, "soul")
    out = q.decide(i, "approve", "gary", "ok")
    assert out["status"] == "approved" and not q.pending()
    # already-decided → no re-decide
    assert q.decide(i, "reject", "gary") is None
    assert q.get(i)["status"] == "approved"


def test_reject_records_rejection():
    q = ApprovalQueue()
    i = q.propose("grant", "submit the Innovate grant", {}, "soul")
    assert q.decide(i, "reject", "gary")["status"] == "rejected"


def test_bad_decision_and_unknown_id_are_noops():
    q = ApprovalQueue()
    i = q.propose("trade", "x", {}, "soul")
    assert q.decide(i, "maybe", "gary") is None
    assert q.decide("nope", "approve", "gary") is None
    assert q.get(i)["status"] == "pending"


def test_backlog_and_backpressure(monkeypatch):
    monkeypatch.setenv("AUREON_APPROVAL_MAX_PENDING", "3")
    q = ApprovalQueue()
    assert q.is_backpressured() is False
    for n in range(3):
        q.propose("trade", f"buy token {n}", {}, "soul")
    b = q.backlog()
    assert b["pending_count"] == 3 and b["max_pending"] == 3 and b["blocked"] is True
    assert q.is_backpressured() is True
    # clearing the desk lifts the backpressure
    for it in list(q.pending()):
        q.decide(it["id"], "reject", "gary")
    assert q.is_backpressured() is False


def test_no_execution_side_effects(tmp_path):
    # the ONLY artifact is the approvals log; deciding writes no order/payment/email
    q = ApprovalQueue()
    i = q.propose("trade", "buy BTC", {}, "soul")
    q.decide(i, "approve", "gary")
    files = {p.name for p in tmp_path.iterdir()}
    assert files == {"approvals.jsonl"}, f"unexpected side-effect files: {files}"


# ── the email loop: owner-only, records only ─────────────────────────────────

class _StubTransport:
    def __init__(self):
        self.sent = []
        self.replies = []

    def send(self, to, subject, body):
        self.sent.append({"to": to, "subject": subject, "body": body})
        return True

    def fetch_replies(self):
        return self.replies


def _email(monkeypatch, transport):
    monkeypatch.setenv("AUREON_APPROVAL_EMAIL", "1")
    monkeypatch.setenv("AUREON_OWNER_EMAIL", "gary@aureon.test")
    from aureon.operator.approval_email import ApprovalEmail

    return ApprovalEmail(transport=transport, owner_email="gary@aureon.test")


def test_email_notifies_only_the_owner(monkeypatch):
    q = ApprovalQueue()
    q.propose("trade", "buy 0.1 BTC", {}, "soul")
    t = _StubTransport()
    n = _email(monkeypatch, t).notify_pending()
    assert n == 1 and len(t.sent) == 1
    assert t.sent[0]["to"] == "gary@aureon.test"          # owner only
    assert "[AUREON approval" in t.sent[0]["subject"]      # tagged with the id


def test_email_reply_records_decision(monkeypatch):
    q = ApprovalQueue()
    i = q.propose("trade", "buy 0.1 BTC", {}, "soul")
    t = _StubTransport()
    ae = _email(monkeypatch, t)
    ae.notify_pending()
    t.replies = [{"subject": t.sent[0]["subject"], "body": "approve\n\n> your message"}]
    applied = ae.ingest_replies()
    assert applied and applied[0]["decision"] == "approve"
    assert q.get(i)["status"] == "approved"               # recorded, not executed


def test_ambiguous_reply_left_pending(monkeypatch):
    q = ApprovalQueue()
    i = q.propose("payment", "wire 500", {}, "soul")
    t = _StubTransport()
    ae = _email(monkeypatch, t)
    ae.notify_pending()
    t.replies = [{"subject": t.sent[0]["subject"], "body": "hmm, let me think about it"}]
    assert ae.ingest_replies() == []
    assert q.get(i)["status"] == "pending"


def test_email_is_noop_without_optin():
    # no AUREON_APPROVAL_EMAIL / no creds → disabled, sends nothing
    from aureon.operator.approval_email import ApprovalEmail

    ae = ApprovalEmail(transport=_StubTransport(), owner_email="")
    assert ae.enabled is False and ae.notify_pending() == 0 and ae.ingest_replies() == []
