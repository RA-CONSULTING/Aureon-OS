import json

from aureon.core import aureon_baton_link as bl


def _capture(monkeypatch):
    seen = []
    monkeypatch.setattr(bl, "relay_state", lambda m, k, p=None: seen.append((k, p)))
    monkeypatch.setattr(bl.os, "execv", lambda *a: seen.append(("EXECV", a)))
    return seen


def test_unverified_repair_never_reboots(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AUREON_QUEEN_SELF_REBOOT", "1")
    seen = _capture(monkeypatch)
    bl._adopt_repair_and_reboot({"status": "repaired", "commit": "abc", "gate": {"verified": False}})
    assert seen == [("not_doing", {"reboot": "held_unverified", "commit": "abc"})]


def test_reboot_off_queues_push_for_owner(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("AUREON_QUEEN_SELF_REBOOT", raising=False)
    seen = _capture(monkeypatch)
    bl._adopt_repair_and_reboot({"status": "repaired", "commit": "abc", "gate": {"verified": True}})
    row = json.loads((tmp_path / "state" / "queen_pending_push.jsonl").read_text().strip())
    assert row["commit"] == "abc" and row["push"] == "awaiting_owner_yes"
    assert ("EXECV",) not in [s[:1] for s in seen] and seen[-1][1]["reboot"] == "off"


def test_unproven_repair_is_never_pushed(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AUREON_QUEEN_AUTO_PUSH", "1")
    monkeypatch.delenv("AUREON_QUEEN_SELF_REBOOT", raising=False)
    _capture(monkeypatch)
    pushed = []
    monkeypatch.setattr(bl, "_push_proven_repair", lambda c, g: pushed.append(c))
    bl._adopt_repair_and_reboot({"status": "repaired", "commit": "abc", "gate": {}})
    assert pushed == []
    bl._adopt_repair_and_reboot({"status": "repaired", "commit": "def", "gate": {"verified": True}})
    assert pushed == ["def"]
