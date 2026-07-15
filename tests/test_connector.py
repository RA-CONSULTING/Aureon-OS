"""Unit tests for the phenolic-fingerprint connector."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

import connector
import phenolic_fingerprint as pf

FIXTURES = Path(__file__).parent / "fixtures"

_NATIVE_CSV = (
    "molecule,peak_value,unit,rel_intensity,source\n"
    "chlorogenic acid,1603,cm^-1,s,doi:cga\n"
    "chlorogenic acid,1632,cm^-1,m,doi:cga\n"
    "chlorogenic acid,1160,cm^-1,w,doi:cga\n"
    "luteolin,1624,cm^-1,vs,doi:lut\n"
    "luteolin,1607,cm^-1,vw,doi:lut\n"
    "luteolin,1594,cm^-1,m,doi:lut\n"
)


def _write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


# --------------------------------------------------------------------------
# Format auto-detection
# --------------------------------------------------------------------------


def test_detect_native_format():
    headers = ["molecule", "peak_value", "unit", "rel_intensity", "source"]
    assert connector.detect_format(headers).name == "native"


def test_detect_codex_spectral_map():
    headers = [
        "molecule", "plant", "peak_value", "peak_value_hi", "unit",
        "rel_intensity", "assignment", "method", "phase", "solvent", "source",
    ]
    assert connector.detect_format(headers).name == "codex_spectral_map"


def test_detect_codex_conversion_table():
    headers = [
        "molecule", "peak_value", "unit", "assignment", "method", "source_key",
        "molecular_frequency_thz", "selected_octaves", "downconversion",
        "modulation_frequency_hz",
    ]
    assert connector.detect_format(headers).name == "codex_conversion_table"


def test_detect_codex_generic():
    headers = ["molecule", "peak_value", "peak_value_hi", "unit", "doi_or_pmid", "method"]
    assert connector.detect_format(headers).name == "codex_generic"


def test_detect_unknown_format_raises():
    with pytest.raises(connector.UnknownFormatError):
        connector.detect_format(["foo", "bar", "baz"])


def test_detect_generic_with_alternate_source_column():
    # a generic export whose source lives in a 'doi' column
    assert connector.detect_format(["molecule", "peak_value", "unit", "doi"]).name == "codex_generic"


def test_generic_resolves_alternate_source(tmp_path):
    text = "molecule,peak_value,unit,doi\nx,1600,cm^-1,10.1/abc\n"
    path = _write(tmp_path, "gen.csv", text)
    rows, fmt = connector.ingest(path)
    assert fmt == ["codex_generic"]
    assert rows[0].source == "10.1/abc"


def test_ingest_many_merges_sources(tmp_path):
    a = _write(tmp_path, "a.csv", _NATIVE_CSV)
    b = _write(tmp_path, "b.csv",
               "molecule,peak_value,unit,rel_intensity,source\n"
               "caffeic acid,1450,cm^-1,m,doi:cga2\n")
    rows, formats = connector.ingest_many([a, b])
    assert formats == ["native", "native"]
    assert len(rows) == 7  # 6 + 1


def test_computed_provenance_stays_separable(tmp_path):
    """Computed (theoretical) data must only appear when its file is included."""
    exp = _write(tmp_path, "exp.csv", _NATIVE_CSV)
    computed = _write(
        tmp_path, "computed.csv",
        "molecule,peak_value,unit,rel_intensity,source\n"
        + "".join(f"luteolin,{v},cm^-1,,COMPUTED GFN2-xTB (theoretical, non-experimental)\n"
                 for v in (1620, 1640, 1660, 1680, 1700, 1720))
    )
    exp_only = connector.run_analysis([exp], nulls=50, seed=0)
    assert not any("COMPUTED" in s for c in exp_only.compounds.values() for s in c.sources)
    with_computed = connector.run_analysis([exp, computed], nulls=50, seed=0)
    assert any("COMPUTED" in s for s in with_computed.compounds["luteolin"].sources)


def test_run_analysis_multi_source_merges_provenance(tmp_path):
    a = _write(tmp_path, "a.csv", _NATIVE_CSV)
    b = _write(tmp_path, "b.csv",
               "molecule,peak_value,unit,rel_intensity,source\n"
               "chlorogenic acid,1700,cm^-1,m,doi:cga-second\n")
    result = connector.run_analysis([a, b], nulls=60, seed=0)
    assert result.valid is True
    # chlorogenic acid now carries two distinct provenance sources
    assert set(result.compounds["chlorogenic acid"].sources) == {"doi:cga", "doi:cga-second"}


# --------------------------------------------------------------------------
# Validation gate
# --------------------------------------------------------------------------


def test_valid_native_file_passes(tmp_path):
    path = _write(tmp_path, "native.csv", _NATIVE_CSV)
    result = connector.run_analysis(path, nulls=80, seed=0)
    assert result.valid is True
    assert result.formats == ["native"]
    assert set(result.compounds) == {"chlorogenic acid", "luteolin"}
    assert result.validation_report.accepted == 6
    assert result.validation_report.rejected == 0
    # Provenance flows through to the result.
    assert result.compounds["luteolin"].sources == ["doi:lut"]


def test_no_source_row_is_rejected(tmp_path):
    text = _NATIVE_CSV + "orphan,1500,cm^-1,m,\n"
    path = _write(tmp_path, "orphan.csv", text)
    rows, _ = connector.ingest(path)
    accepted, report = connector.validate(rows)
    assert report.rejected == 1
    assert report.rejections.get("missing source/DOI/PMID") == 1
    assert all(row.molecule != "orphan" for row in accepted)


def test_low_wavenumber_is_rejected(tmp_path):
    text = _NATIVE_CSV + "tiny,42,cm^-1,m,doi:z\n"
    path = _write(tmp_path, "tiny.csv", text)
    _, report = connector.validate(connector.ingest(path)[0])
    assert any("cm^-1" in reason for reason in report.rejections)


def test_unparseable_peak_is_rejected(tmp_path):
    text = _NATIVE_CSV + "junk,NODATA,cm^-1,m,doi:z\n".replace("NODATA", "abc")
    path = _write(tmp_path, "junk.csv", text)
    _, report = connector.validate(connector.ingest(path)[0])
    assert report.rejections.get("unparseable peak_value") == 1


def test_nm_rows_are_set_aside_not_rejected():
    rows, _ = connector.ingest(FIXTURES / "weed_phenolic_spectral_map_codex.csv")
    _, report = connector.validate(rows)
    assert report.set_aside > 0
    assert any("nm" in reason for reason in report.set_asides)
    # Set-aside rows are not counted as rejections.
    assert report.accepted + report.rejected + report.set_aside == report.total


def test_range_midpoint_is_taken_and_noted():
    # The spectral-map fixture has peak_value_hi ranges (e.g. 766/767 -> 766.5).
    rows, _ = connector.ingest(FIXTURES / "weed_phenolic_spectral_map_codex.csv")
    accepted, report = connector.validate(rows)
    assert any("midpoint" in note for note in report.notes)
    assert 766.5 in {row.peak_value for row in accepted}


def test_rel_intensity_normalization():
    rows = [
        connector.RawRow("m1", "1600", "", "cm^-1", "vs", "doi:a", "native"),
        connector.RawRow("m1", "1610", "", "cm^-1", "0.35", "doi:a", "native"),
        connector.RawRow("m1", "1620", "", "cm^-1", "NO DATA", "doi:a", "native"),
    ]
    accepted, _ = connector.validate(rows)
    values = [row.rel_intensity for row in accepted]
    assert values == [1.0, 0.35, None]


# --------------------------------------------------------------------------
# Ingest: zip + Codex CSV
# --------------------------------------------------------------------------


def test_ingest_codex_spectral_map_fixture():
    rows, formats = connector.ingest(FIXTURES / "weed_phenolic_spectral_map_codex.csv")
    assert formats == ["codex_spectral_map"]
    assert len(rows) > 400
    assert rows[0].fmt == "codex_spectral_map"


def test_ingest_zip_reads_conversion_tables(tmp_path):
    zip_path = tmp_path / "pkg.zip"
    conv = (
        "molecule,peak_value,unit,assignment,method,source_key,"
        "molecular_frequency_thz,selected_octaves,downconversion,modulation_frequency_hz\n"
        "chlorogenic acid,1603,cm^-1,C=C,raman,cga_2025,48.05,35,/2^35,1398.6\n"
        "chicoric acid,330,nm,UV,uv_vis,cca_2013,908.4,39,/2^39,1652.4\n"
    )
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("hnc_conversion_table_v02.csv", conv)
        zf.writestr("readme.txt", "not a table")
    rows, formats = connector.ingest(zip_path)
    assert len(rows) == 2
    assert formats[0].startswith("codex_conversion_table:")
    # source_key becomes the native source.
    assert rows[0].source == "cga_2025"


def test_ingest_zip_without_conversion_table_raises(tmp_path):
    zip_path = tmp_path / "empty.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("notes.txt", "nothing here")
    with pytest.raises(connector.IngestError):
        connector.ingest(zip_path)


def test_missing_input_path_raises():
    with pytest.raises(connector.IngestError):
        connector.ingest("/nonexistent/path/to/data.csv")


# --------------------------------------------------------------------------
# Orchestration + invalid-run propagation
# --------------------------------------------------------------------------


def test_controls_fail_suppresses_results(tmp_path, monkeypatch):
    path = _write(tmp_path, "native.csv", _NATIVE_CSV)

    def _fake_run(peaks, *, nulls, seed):
        return pf.RunResult(
            valid=False,
            alpha=pf.ALPHA,
            n_nulls=nulls,
            seed=seed,
            controls={
                "positive": pf.ControlResult("positive", False, {}),
                "negative": pf.ControlResult("negative", True, {}),
            },
            compounds={},
            reason="control(s) failed: positive",
        )

    monkeypatch.setattr(pf, "run", _fake_run)
    result = connector.run_analysis(path, nulls=50, seed=0)
    assert result.valid is False
    assert result.compounds == {}
    assert "positive" in result.reason
    # The validation report is still available even on an invalid run.
    assert result.validation_report.accepted == 6


def test_run_analysis_is_deterministic(tmp_path):
    path = _write(tmp_path, "native.csv", _NATIVE_CSV)
    r1 = connector.run_analysis(path, nulls=80, seed=0)
    r2 = connector.run_analysis(path, nulls=80, seed=0)
    assert r1.to_dict() == r2.to_dict()


def test_to_json_roundtrip(tmp_path):
    import json

    path = _write(tmp_path, "native.csv", _NATIVE_CSV)
    result = connector.run_analysis(path, nulls=50, seed=0)
    out = tmp_path / "out.json"
    result.to_json(out)
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["valid"] is True
    assert "compounds" in loaded


def test_main_cli_smoke(tmp_path, capsys):
    path = _write(tmp_path, "native.csv", _NATIVE_CSV)
    out = tmp_path / "cli.json"
    code = connector.main([str(path), "--nulls", "50", "--seed", "0", "--json", str(out)])
    assert code == 0
    captured = capsys.readouterr()
    assert "Validation:" in captured.out
    assert out.exists()


def test_main_cli_bad_path_returns_error(capsys):
    code = connector.main(["/nonexistent/data.csv"])
    assert code == 2
    assert "error:" in capsys.readouterr().err
