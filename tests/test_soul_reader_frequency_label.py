"""The 528.422 Hz value is a configured identity label, not a measurement.

The reader's start-up header and its verdict text must say so, so nobody
reads it as a live measured frequency.
"""
import contextlib
import io

from aureon.queen import queen_soul_reader as qsr


def _reader():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        reader = qsr.QueenSoulReader()
    return reader, buf.getvalue()


def test_header_labels_frequency_as_configured_not_measured():
    _, out = _reader()
    assert "Personal frequency:" not in out
    assert "Configured identity frequency: 528.422 Hz (set in config, not measured)" in out


def test_source_has_no_unlabelled_personal_frequency_line():
    src = open(qsr.__file__, encoding="utf-8").read()
    assert "Personal frequency:" not in src
    assert src.count("(set in config, not measured)") == 2
