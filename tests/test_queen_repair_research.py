"""Diagnosis records and the opt-in read-only research step of the Queen's repair loop."""

from __future__ import annotations

import json
from pathlib import Path

from aureon.autonomous import queen_repair_research as qr

OUTPUT = """\
=================================== FAILURES ===================================
_________________________________ test_total ___________________________________
tests/test_calc.py:5: in test_total
    assert total(2, 3) == 5
calc.py:2: in total
    return a + bb
E   NameError: name 'bb' is not defined. Did you mean: 'b'?
=========================== short test summary info ============================
FAILED tests/test_calc.py::test_total - NameError: name 'bb' is not defined. Did you mean: 'b'?
1 failed in 0.01s
"""


def _project(tmp_path: Path) -> Path:
    (tmp_path / "tests").mkdir()
    (tmp_path / "calc.py").write_text("def total(a, b):\n    return a + bb\n", encoding="utf-8")
    (tmp_path / ".env").write_text("EXCHANGE_API_SECRET=hunter2secretvalue\n", encoding="utf-8")
    return tmp_path


def test_diagnosis_record_per_failing_test(tmp_path):
    root = _project(tmp_path)
    records = qr.diagnose(root, OUTPUT)
    assert len(records) == 1
    record = records[0]
    assert record["test_id"] == "tests/test_calc.py::test_total"
    assert record["exception"] == "NameError"
    assert "bb" in record["error"]
    assert record["suspected_file"] == "calc.py"
    assert any("NameError" in line for line in record["traceback_tail"])
    path = qr.write_diagnosis(root, records)
    assert json.loads(path.read_text())["failures"] == 1


def test_research_is_off_unless_opted_in(tmp_path, monkeypatch):
    monkeypatch.delenv(qr.WEB_ENV, raising=False)
    calls = []
    found = qr.research(_project(tmp_path), qr.diagnose(tmp_path, OUTPUT), fetch=lambda url: calls.append(url) or {})
    assert found == [] and calls == []
    assert not (tmp_path / qr.RESEARCH_LOG).exists()


def _fake_fetch(calls):
    def fetch(url):
        calls.append(url)
        if url.startswith(qr.SEARCH_URL):
            return {"ok": True, "status": 200, "text": '<a class="result__a" href="https://docs.python.org/3/library/exceptions.html">x</a>'}
        return {"ok": True, "status": 200, "text": "<p>NameError is raised when a local or global name is not found.</p>"}
    return fetch


def test_research_logs_every_fetch_and_reuses_cache(tmp_path, monkeypatch):
    monkeypatch.setenv(qr.WEB_ENV, "1")
    root = _project(tmp_path)
    records = qr.diagnose(root, OUTPUT)
    calls: list[str] = []
    found = qr.research(root, records, fetch=_fake_fetch(calls))
    assert len(calls) == 2
    assert found[0]["sources"][0]["url"] == "https://docs.python.org/3/library/exceptions.html"
    assert "NameError" in found[0]["sources"][0]["summary"]
    rows = [json.loads(line) for line in (root / qr.RESEARCH_LOG).read_text().splitlines()]
    assert {row["url"] for row in rows} == set(calls)
    again: list[str] = []
    qr.research(root, records, fetch=_fake_fetch(again))
    assert again == []  # served from the logged cache, and logged again as cached
    assert len((root / qr.RESEARCH_LOG).read_text().splitlines()) == 4


def test_secrets_never_leave_in_the_request(tmp_path, monkeypatch):
    monkeypatch.setenv(qr.WEB_ENV, "1")
    monkeypatch.setenv("KRAKEN_API_KEY", "envsecret12345")
    root = _project(tmp_path)
    leaky = OUTPUT.replace("Did you mean: 'b'?", "key hunter2secretvalue envsecret12345 /home/box/quarantine_env/x")
    calls: list[str] = []
    qr.research(root, qr.diagnose(root, leaky), fetch=_fake_fetch(calls))
    for url in calls:
        assert "hunter2secretvalue" not in url and "envsecret12345" not in url and "quarantine_env" not in url
    log = (root / qr.RESEARCH_LOG).read_text()
    assert "hunter2secretvalue" not in log and "envsecret12345" not in log


def test_redaction_strips_paths_and_tokens():
    query = qr.redact_query("KeyError at /srv/app/x.py token=AbCdEfGhIjKlMnOpQrStUvWxYz012345 deadbeefdeadbeefdead")
    assert "/srv" not in query and "AbCdEf" not in query and "deadbeef" not in query
    assert "KeyError" in query


def test_get_is_read_only_and_capped(monkeypatch):
    seen = {}

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self, n):
            seen["n"] = n
            return b"x" * n

    def urlopen(request, timeout):
        seen.update(method=request.get_method(), data=request.data, headers=dict(request.header_items()), timeout=timeout)
        return Response()

    monkeypatch.setattr(qr.urllib.request, "urlopen", urlopen)
    got = qr._get("https://example.org/doc")
    assert seen["method"] == "GET" and seen["data"] is None and seen["timeout"] == qr.TIMEOUT_S
    assert set(k.lower() for k in seen["headers"]) <= {"user-agent", "accept"}
    assert seen["n"] == qr.MAX_BYTES + 1 and got["truncated"] and len(got["text"]) == qr.MAX_BYTES
    assert qr._get("file:///etc/passwd") == {"ok": False, "error": "scheme_refused"}


def test_hint_from_error_text_feeds_the_name_repair(tmp_path):
    from aureon.autonomous.aureon_sandbox_self_repair import _name_error_edit

    root = _project(tmp_path)
    (root / "calc.py").write_text("def total(a, b):\n    return a + bxyz\n", encoding="utf-8")
    output = OUTPUT.replace("bb", "bxyz")
    record = qr.diagnose(root, output)[0]
    hints = qr.hinted_names(record, [])
    assert hints == ["b"]
    assert _name_error_edit(root, output) is None  # 'bxyz' is not one edit from 'b'
    assert _name_error_edit(root, output, hints) == ("calc.py", "bxyz", "b")


def test_diagnose_captures_variable_width_headers_and_deep_exception(tmp_path):
    # pytest pads long/parametrised failure headers with a single underscore each side.
    # The capture must still find the section and surface the deepest real exception line,
    # not leave the record with empty error text (owner's call, 11:53).
    from aureon.autonomous import queen_repair_research as R
    output = (
        "=================================== FAILURES ===================================\n"
        "_ test_worker_refuses[core/x.py:bind:governance] _\n"
        "tests/test_stage.py:179: in test_worker_refuses\n"
        "    assert completed.returncode == 0\n"
        "E   AssertionError: subprocess failed\n"
        "E     ImportError: checkout aureon/core/hnc_field.py differs from pin bb0450311968\n"
        "E   assert 1 == 0\n"
        "=========================== short test summary info ============================\n"
        "FAILED tests/test_stage.py::test_worker_refuses[core/x.py:bind:governance]\n"
    )
    records = R.diagnose(tmp_path, output)
    assert len(records) == 1
    rec = records[0]
    assert rec["error"], "error text must not be empty"
    assert "differs from pin" in rec["error"]
    assert rec["exception"] == "ImportError"
