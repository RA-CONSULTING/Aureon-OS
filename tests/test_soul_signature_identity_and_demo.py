"""The 528.422 Hz soul signature is configured identity, not a measurement,
and the queen_soul_reader demo printout survives None readings.

No network and no randomness.
"""
from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
READER = REPO / "aureon" / "queen" / "queen_soul_reader.py"


def _load_daemon(tmp_path, monkeypatch):
    monkeypatch.setenv("SERO_WORKSPACE", str(tmp_path))
    monkeypatch.delenv("AUREON_ALLOW_SIM_FALLBACK", raising=False)
    monkeypatch.chdir(tmp_path)
    sys.modules.pop("aureon_fusion.paths", None)
    spec = importlib.util.spec_from_file_location("spd_signature", REPO / "soul_protection_daemon.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    sys.modules.pop("aureon_fusion.paths", None)
    return mod


def _reader_shape(coherence=None):
    # Shape of QueenSoulReader.read_soul()['soul'] with the configured signature.
    return {"soul": {"name": "Gary", "frequency": 528.422,
                     "frequency_source": "configured_identity",
                     "coherence": coherence}}


def test_configured_signature_is_not_measured_frequency(tmp_path, monkeypatch):
    mod = _load_daemon(tmp_path, monkeypatch)
    daemon = mod.SoulProtectionDaemon()

    class Reader:
        def read_soul(self):
            return _reader_shape()

    daemon._soul_reader = Reader()
    soul = daemon._scan_soul_state()
    assert soul["frequency"] is None
    assert soul["signature_hz"] == 528.422
    assert soul["signature_kind"] == "configured_identity"
    assert soul["status"] == "no_reading"


def test_unmarked_nested_frequency_is_not_trusted(tmp_path, monkeypatch):
    mod = _load_daemon(tmp_path, monkeypatch)
    daemon = mod.SoulProtectionDaemon()

    class Reader:
        def read_soul(self):
            return {"soul": {"frequency": 528.422, "coherence": 0.4}}

    daemon._soul_reader = Reader()
    soul = daemon._scan_soul_state()
    assert soul["frequency"] is None
    assert soul["coherence"] == 0.4
    assert soul["status"] == "partial"


def test_marked_measured_frequency_passes_through(tmp_path, monkeypatch):
    mod = _load_daemon(tmp_path, monkeypatch)
    daemon = mod.SoulProtectionDaemon()

    class Reader:
        def read_soul(self):
            return {"soul": {"frequency": 527.9, "frequency_source": "measured"}}

    daemon._soul_reader = Reader()
    assert daemon._scan_soul_state()["frequency"] == 527.9


def test_reader_marks_signature_as_configured_identity():
    src = READER.read_text(encoding="utf-8")
    assert "'frequency_source': 'configured_identity'" in src


def _demo_fmt():
    tree = ast.parse(READER.read_text(encoding="utf-8"))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_demo_fmt")
    ns: dict = {}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(READER), "exec"), ns)
    return ns["_demo_fmt"]


def test_demo_formatter_handles_none():
    fmt = _demo_fmt()
    assert fmt(None, ".1%") == "no reading"
    assert fmt(True, ".1%") == "no reading"
    assert fmt(0.5, ".1%") == "50.0%"
    assert fmt(7.83, ".3f", " Hz") == "7.830 Hz"


def test_demo_main_has_no_raw_numeric_format_specs():
    tree = ast.parse(READER.read_text(encoding="utf-8"))
    main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    raw = [n for n in ast.walk(main) if isinstance(n, ast.FormattedValue) and n.format_spec is not None]
    assert raw == [], f"main() formats readings directly at lines {[n.lineno for n in raw]}"
