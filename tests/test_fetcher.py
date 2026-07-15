"""Unit tests for the open-source spectral fetcher (offline — no real network)."""

from __future__ import annotations

import io
import urllib.error
from pathlib import Path

import numpy as np
import pytest

import fetcher

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE_JDX = (FIXTURES / "sample_ir.jdx").read_text(encoding="utf-8")


class _FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


class _FakeOpener:
    """Stand-in for a urllib opener that returns canned bytes or raises."""

    def __init__(self, *, body: str | None = None, error: Exception | None = None):
        self._body = body
        self._error = error

    def open(self, request, timeout=None):  # noqa: A003 - mirror urllib API
        if self._error is not None:
            raise self._error
        return _FakeResponse((self._body or "").encode("utf-8"))


# --------------------------------------------------------------------------
# JCAMP parsing
# --------------------------------------------------------------------------


def test_parse_jcamp_reconstructs_axis():
    x, y, headers = fetcher.parse_jcamp_xydata(SAMPLE_JDX)
    assert x.size == 10
    assert x.min() == pytest.approx(100.0)
    assert x.max() == pytest.approx(1000.0)
    assert headers["YUNITS"] == "TRANSMITTANCE"
    # x must be sorted ascending
    assert np.all(np.diff(x) > 0)


def test_parse_jcamp_rejects_non_wavenumber():
    bad = SAMPLE_JDX.replace("##XUNITS=1/CM", "##XUNITS=SECONDS")
    with pytest.raises(fetcher.FetchError):
        fetcher.parse_jcamp_xydata(bad)


# --------------------------------------------------------------------------
# Peak picking
# --------------------------------------------------------------------------


def test_pick_peaks_finds_transmittance_minima():
    x, y, headers = fetcher.parse_jcamp_xydata(SAMPLE_JDX)
    peaks = fetcher.pick_peaks(x, y, yunits=headers["YUNITS"], min_prominence=0.1)
    positions = [p.wavenumber_cm1 for p in peaks]
    # dips at 800 and 400 cm^-1 (deepest) should be recovered
    assert 800.0 in positions
    assert 400.0 in positions


def test_pick_peaks_merges_near_neighbours():
    x = np.arange(1000.0, 1010.0, 1.0)
    # two adjacent minima 1 cm^-1 apart in transmittance
    y = np.ones_like(x)
    y[3] = 0.2
    y[4] = 0.1
    peaks = fetcher.pick_peaks(x, y, yunits="TRANSMITTANCE", min_prominence=0.1,
                               min_separation_cm1=6.0)
    assert len(peaks) == 1  # merged, deepest kept
    assert peaks[0].depth == pytest.approx(1.0)


def test_qualitative_intensity_ladder():
    assert fetcher.SpectrumPeak(1600.0, 0.9).qualitative_intensity() == "vs"
    assert fetcher.SpectrumPeak(1600.0, 0.5).qualitative_intensity() == "s"
    assert fetcher.SpectrumPeak(1600.0, 0.05).qualitative_intensity() == "vw"


# --------------------------------------------------------------------------
# Fetch orchestration (network mocked)
# --------------------------------------------------------------------------


def test_fetch_compound_peaks_native_schema():
    fetcher.NIST_CAS["sample test compound"] = "C000000"
    try:
        opener = _FakeOpener(body=SAMPLE_JDX)
        rows = fetcher.fetch_compound_peaks("sample test compound", _opener=opener)
    finally:
        del fetcher.NIST_CAS["sample test compound"]
    assert rows
    assert set(rows[0]) == {"molecule", "peak_value", "unit", "rel_intensity", "source"}
    assert all(r["unit"] == "cm^-1" for r in rows)
    assert all("NIST WebBook" in r["source"] for r in rows)


def test_fetch_unknown_compound_returns_empty():
    assert fetcher.fetch_compound_peaks("not a real compound name") == []


def test_fetch_404_returns_none():
    err = urllib.error.HTTPError("url", 404, "Not Found", {}, None)
    opener = _FakeOpener(error=err)
    assert fetcher.fetch_nist_ir_jcamp("C999999", _opener=opener, retries=1) is None


def test_fetch_stub_page_returns_none():
    opener = _FakeOpener(body="<html>no spectrum here</html>")
    assert fetcher.fetch_nist_ir_jcamp("C999999", _opener=opener, retries=1) is None


def test_fetched_peaks_ingest_through_connector(tmp_path):
    """The fetcher's output must be ingestable by the connector unchanged."""
    import connector

    fetcher.NIST_CAS["sample test compound"] = "C000000"
    try:
        rows = fetcher.fetch_compound_peaks("sample test compound", _opener=_FakeOpener(body=SAMPLE_JDX))
    finally:
        del fetcher.NIST_CAS["sample test compound"]
    out = tmp_path / "fetched.csv"
    fetcher.write_native_csv(rows, out)
    raw, formats = connector.ingest(out)
    assert formats == ["native"]
    accepted, report = connector.validate(raw)
    assert report.accepted == len(rows)


# --------------------------------------------------------------------------
# Pluggable source adapters
# --------------------------------------------------------------------------


def test_unknown_source_raises():
    with pytest.raises(fetcher.FetchError):
        fetcher.fetch_compound_peaks("caffeic acid", sources=("bogus",))


def test_jcamp_url_adapter_via_fixture():
    adapter = fetcher.JcampUrlAdapter({"widget": "https://example.test/widget.jdx"}, label="Test JCAMP")
    assert adapter.available() is True
    rows = adapter.fetch("widget", _opener=_FakeOpener(body=SAMPLE_JDX))
    assert rows
    assert all(r["unit"] == "cm^-1" for r in rows)
    assert all("Test JCAMP" in r["source"] for r in rows)


def test_jcamp_adapter_unconfigured_is_unavailable():
    assert fetcher.JcampUrlAdapter().available() is False


def test_computed_adapter_availability_flag():
    # Availability must match the actual import state, not raise.
    assert fetcher.ComputedXtbAdapter().available() == fetcher.computed_toolchain_available()


def test_computed_adapter_unknown_smiles_returns_empty():
    assert fetcher.ComputedXtbAdapter().fetch("not-a-real-molecule") == []


def test_computed_rows_carry_theoretical_marker():
    """Computed provenance must be clearly labeled and kept separable."""
    pytest.importorskip("rdkit")
    pytest.importorskip("tblite")
    freqs = fetcher.compute_xtb_frequencies("O", seed=1)  # water: fast
    assert len(freqs) >= 3
    assert all(f > 100 for f in freqs)
    # provenance marker is the theoretical lane, not an experimental source
    assert "COMPUTED" in fetcher.COMPUTED_SOURCE and "theoretical" in fetcher.COMPUTED_SOURCE
