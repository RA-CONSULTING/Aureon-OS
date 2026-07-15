#!/usr/bin/env python3
"""Connector — heterogeneous ingest + validation + orchestration for the
Phenolic Fingerprint System.

This module is the integration layer around the falsifiable analysis engine in
``phenolic_fingerprint.py``. It does three things and nothing more:

1. **Ingest** heterogeneous phenolic-spectra inputs and normalize them into the
   engine's native schema (``molecule, peak_value, unit, rel_intensity,
   source``). Formats are auto-detected by inspecting CSV headers:

   * native-schema CSV;
   * Codex spectral-map export (``peak_value_hi, plant, assignment, method,
     phase, solvent, source``);
   * Codex conversion-table CSVs (``source_key, molecular_frequency_thz,
     modulation_frequency_hz``) — including those packaged inside
     ``HNC_BioMolecule_White_Paper_Data_Package_v1.zip``;
   * a generic Codex export with differently named columns
     (``peak_value_hi, doi_or_pmid, method, assignment``).

2. **Validate** against the protocol's hard rules (source required, minimum
   wavenumber, unit filtering, range midpoints, relative-intensity
   normalization) and emit a :class:`ValidationReport` that counts every
   accepted, rejected and set-aside row *with reasons* — nothing is dropped
   silently.

3. **Orchestrate** the engine on the cleaned data and return a structured
   :class:`AnalysisResult` that preserves each compound's source/DOI provenance.
   If the engine's controls fail, the invalid-run state is propagated and **no
   compound results are returned**.

The engine's pre-registered logic and thresholds are never modified here.

Pure standard library + numpy + the engine. No network access. Deterministic
given a seed. No global state.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import tempfile
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Final

import phenolic_fingerprint as engine

__all__ = [
    "ConnectorError",
    "UnknownFormatError",
    "IngestError",
    "RawRow",
    "ValidationReport",
    "CompoundResult",
    "AnalysisResult",
    "detect_format",
    "ingest",
    "validate",
    "run_analysis",
    "main",
]


# ============================================================================
# EXCEPTIONS
# ============================================================================


class ConnectorError(Exception):
    """Base class for connector failures (raised loudly, never swallowed)."""


class UnknownFormatError(ConnectorError):
    """Raised when a CSV header matches no known input format."""


class IngestError(ConnectorError):
    """Raised when a file/zip cannot be read or contains no usable table."""


# ============================================================================
# NORMALIZATION HELPERS
# ============================================================================

# Tokens (lower-cased) that mean "no value present" across the Codex exports.
_MISSING_TOKENS: Final[frozenset[str]] = frozenset(
    {"", "no data", "nan", "none", "null", "n/a", "na"}
)

# Qualitative relative-intensity ladder -> numeric.
_REL_INTENSITY_MAP: Final[dict[str, float]] = {
    "vs": 1.0,
    "s": 0.8,
    "m": 0.6,
    "w": 0.4,
    "vw": 0.2,
}

_UNIT_ALIASES: Final[dict[str, str]] = {
    "cm^-1": "cm^-1",
    "cm-1": "cm^-1",
    "cm^{-1}": "cm^-1",
    "1/cm": "cm^-1",
    "wavenumber": "cm^-1",
    "nm": "nm",
    "nanometer": "nm",
    "nanometre": "nm",
}


def _is_missing(value: str | None) -> bool:
    """True when a raw cell is empty or one of the Codex 'no value' sentinels."""
    return value is None or value.strip().lower() in _MISSING_TOKENS


def _normalize_unit(value: str | None) -> str:
    """Canonicalize a unit string; unknown/blank units return '' (unset)."""
    if _is_missing(value):
        return ""
    key = value.strip().lower()  # type: ignore[union-attr]
    return _UNIT_ALIASES.get(key, value.strip())  # type: ignore[union-attr]


def _parse_peak_value(raw: str) -> float:
    """Parse a wavenumber/wavelength, stripping ``±`` uncertainty (e.g. ``1443 ± 1``)."""
    text = raw.strip()
    for sep in ("±", "+/-", "+-"):
        if sep in text:
            text = text.split(sep, 1)[0].strip()
            break
    return float(text)


def _normalize_rel_intensity(raw: str | None) -> str | float | None:
    """Map ``vs/s/m/w/vw`` to numeric; pass numeric through; else ``None``/original."""
    if _is_missing(raw):
        return None
    token = raw.strip()  # type: ignore[union-attr]
    if token.lower() in _REL_INTENSITY_MAP:
        return _REL_INTENSITY_MAP[token.lower()]
    try:
        return float(token)
    except ValueError:
        return token


# ============================================================================
# FORMAT DETECTION + MAPPING
# ============================================================================


@dataclass(frozen=True)
class RawRow:
    """A row mapped to the native fields, still carrying raw (unvalidated) strings."""

    molecule: str
    peak_value: str
    peak_value_hi: str
    unit: str
    rel_intensity: str
    source: str
    fmt: str
    extras: dict[str, str] = field(default_factory=dict)


# Alternate column names that may carry a citable source across exports.
_SOURCE_ALIASES: Final[tuple[str, ...]] = (
    "source", "source_key", "doi_or_pmid", "doi", "pmid", "url", "reference", "citation",
)


@dataclass(frozen=True)
class _Mapper:
    """A header-driven mapping from one input format to the native fields."""

    name: str
    required: frozenset[str]
    veto: frozenset[str]
    bonus: frozenset[str]
    source_cols: tuple[str, ...]
    source_any: frozenset[str] = frozenset()

    def score(self, headers: set[str]) -> int:
        """Return a match score, or ``-1`` when this mapper cannot apply."""
        if not self.required <= headers:
            return -1
        if self.veto & headers:
            return -1
        if self.source_any and not (self.source_any & headers):
            return -1
        return len(self.bonus & headers)

    def _resolve_source(self, row: dict[str, str]) -> str:
        """First non-empty source across this mapper's declared source columns."""
        candidates = list(self.source_cols) + sorted(self.source_any & set(row))
        for col in candidates:
            value = (row.get(col) or "").strip()
            if value:
                return value
        return ""

    def to_native(self, row: dict[str, str]) -> RawRow:
        """Project a raw CSV row onto :class:`RawRow` using this format's columns."""
        extras = {
            col: (row.get(col) or "")
            for col in ("plant", "assignment", "method", "phase", "solvent")
            if col in row and (row.get(col) or "").strip()
        }
        return RawRow(
            molecule=(row.get("molecule") or "").strip(),
            peak_value=(row.get("peak_value") or "").strip(),
            peak_value_hi=(row.get("peak_value_hi") or "").strip(),
            unit=(row.get("unit") or "").strip(),
            rel_intensity=(row.get("rel_intensity") or "").strip(),
            source=self._resolve_source(row),
            fmt=self.name,
            extras=extras,
        )


# Ordered registry — first mapper wins ties. Distinctive required/veto columns
# keep the native format from matching the richer Codex exports and vice versa.
_MAPPERS: Final[tuple[_Mapper, ...]] = (
    _Mapper(
        name="native",
        required=frozenset({"molecule", "peak_value", "unit", "source"}),
        veto=frozenset({"peak_value_hi", "source_key", "doi_or_pmid", "molecular_frequency_thz"}),
        bonus=frozenset({"rel_intensity"}),
        source_cols=("source",),
    ),
    _Mapper(
        name="codex_conversion_table",
        required=frozenset({"molecule", "peak_value", "unit", "source_key"}),
        veto=frozenset(),
        bonus=frozenset(
            {"molecular_frequency_thz", "selected_octaves", "modulation_frequency_hz",
             "method", "assignment"}
        ),
        source_cols=("source_key",),
    ),
    _Mapper(
        name="codex_spectral_map",
        required=frozenset({"molecule", "peak_value", "unit", "peak_value_hi"}),
        veto=frozenset({"source_key", "doi_or_pmid"}),
        bonus=frozenset(
            {"plant", "assignment", "method", "phase", "solvent", "rel_intensity", "source"}
        ),
        source_cols=("source",),
    ),
    _Mapper(
        name="codex_generic",
        required=frozenset({"molecule", "peak_value"}),
        veto=frozenset({"source_key"}),
        bonus=frozenset({"peak_value_hi", "method", "assignment", "unit", "rel_intensity"}),
        source_cols=(),
        source_any=frozenset({"doi_or_pmid", "doi", "pmid", "url", "reference", "citation"}),
    ),
)


def detect_format(headers: list[str] | None) -> _Mapper:
    """Return the best-matching :class:`_Mapper` for a header row.

    Raises :class:`UnknownFormatError` if no mapper's required columns are met.
    """
    if not headers:
        raise UnknownFormatError("CSV has no header row")
    header_set = {h.strip() for h in headers}
    best: _Mapper | None = None
    best_score = -1
    for mapper in _MAPPERS:
        score = mapper.score(header_set)
        if score > best_score:
            best, best_score = mapper, score
    if best is None or best_score < 0:
        raise UnknownFormatError(
            f"No known format matches headers {sorted(header_set)}"
        )
    return best


def _read_csv_rows(text: str) -> tuple[_Mapper, list[RawRow]]:
    """Parse CSV text into mapped :class:`RawRow` objects using the detected format."""
    reader = csv.DictReader(text.splitlines())
    mapper = detect_format(reader.fieldnames)
    return mapper, [mapper.to_native(row) for row in reader]


def ingest(source: str | Path) -> tuple[list[RawRow], list[str]]:
    """Ingest a CSV file or a data-package zip into mapped :class:`RawRow` objects.

    For ``.zip`` inputs, every ``*conversion_table*.csv`` member is read (the
    conversion tables inside ``HNC_BioMolecule_White_Paper_Data_Package_v1.zip``).
    Returns the rows and the list of format names that were detected.
    """
    path = Path(source)
    if not path.exists():
        raise IngestError(f"Input path does not exist: {path}")

    if path.suffix.lower() == ".zip":
        return _ingest_zip(path)

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise IngestError(f"Could not read {path}: {exc}") from exc
    mapper, rows = _read_csv_rows(text)
    if not rows:
        raise IngestError(f"{path} contained a header but no data rows")
    return rows, [mapper.name]


def _ingest_zip(path: Path) -> tuple[list[RawRow], list[str]]:
    """Read the conversion-table CSVs inside a data-package zip."""
    try:
        archive = zipfile.ZipFile(path)
    except zipfile.BadZipFile as exc:
        raise IngestError(f"{path} is not a valid zip archive") from exc

    with archive:
        members = [
            name
            for name in archive.namelist()
            if name.lower().endswith(".csv") and "conversion_table" in Path(name).name.lower()
        ]
        if not members:
            raise IngestError(
                f"{path} contains no '*conversion_table*.csv' members to ingest"
            )
        rows: list[RawRow] = []
        formats: list[str] = []
        for member in sorted(members):
            text = archive.read(member).decode("utf-8")
            mapper, member_rows = _read_csv_rows(text)
            rows.extend(member_rows)
            formats.append(f"{mapper.name}:{Path(member).name}")
    if not rows:
        raise IngestError(f"{path} conversion tables contained no data rows")
    return rows, formats


def ingest_many(sources: list[str | Path]) -> tuple[list[RawRow], list[str]]:
    """Ingest and concatenate several CSV/zip sources into one row set.

    Used to merge heterogeneous datasets (e.g. the original Codex export plus
    fetcher-derived NIST peaks plus a curated CSV) before a single analysis.
    Each source is auto-detected independently. Raises :class:`IngestError` if
    the list is empty.
    """
    if not sources:
        raise IngestError("ingest_many requires at least one source")
    all_rows: list[RawRow] = []
    formats: list[str] = []
    for src in sources:
        rows, fmts = ingest(src)
        all_rows.extend(rows)
        formats.extend(fmts)
    return all_rows, formats


# ============================================================================
# VALIDATION GATE
# ============================================================================


@dataclass(frozen=True)
class ValidationReport:
    """Counts of accepted / rejected / set-aside rows, each with reasons."""

    total: int
    accepted: int
    rejected: int
    set_aside: int
    rejections: dict[str, int] = field(default_factory=dict)
    set_asides: dict[str, int] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class _NativeRow:
    """A fully validated native-schema row ready for the engine."""

    molecule: str
    peak_value: float
    unit: str
    rel_intensity: str | float | None
    source: str


def _bump(counter: dict[str, int], reason: str) -> None:
    counter[reason] = counter.get(reason, 0) + 1


def validate(rows: list[RawRow]) -> tuple[list[_NativeRow], ValidationReport]:
    """Apply the protocol's hard validation rules and produce a report.

    Rules (in order): a non-empty source/DOI/PMID is mandatory; peak values must
    parse (ranges collapse to their midpoint); non ``cm^-1`` rows (e.g. UV/nm)
    are set aside, not rejected; ``cm^-1`` peaks below ``MIN_PEAK_CM1`` are
    rejected. Nothing is discarded without being counted.
    """
    accepted: list[_NativeRow] = []
    rejections: dict[str, int] = {}
    set_asides: dict[str, int] = {}
    notes: list[str] = []
    n_midpoints = 0

    for row in rows:
        # 1. Source / DOI / PMID is mandatory.
        if _is_missing(row.source):
            _bump(rejections, "missing source/DOI/PMID")
            continue

        # 2. Peak value must parse; ranges collapse to a noted midpoint.
        try:
            if not _is_missing(row.peak_value_hi):
                lo = _parse_peak_value(row.peak_value)
                hi = _parse_peak_value(row.peak_value_hi)
                peak_value = (lo + hi) / 2.0
                n_midpoints += 1
            else:
                if _is_missing(row.peak_value):
                    raise ValueError("empty")
                peak_value = _parse_peak_value(row.peak_value)
        except ValueError:
            _bump(rejections, "unparseable peak_value")
            continue

        # 3. Unit filter — keep only cm^-1; set aside everything else (UV/nm).
        unit = _normalize_unit(row.unit)
        if unit != "cm^-1":
            label = unit if unit else "unspecified"
            _bump(set_asides, f"unit not cm^-1 ({label})")
            continue

        # 4. Minimum wavenumber.
        if peak_value < engine.MIN_PEAK_CM1:
            _bump(rejections, f"peak_value < {engine.MIN_PEAK_CM1:g} cm^-1")
            continue

        # 5. Relative-intensity normalization.
        accepted.append(
            _NativeRow(
                molecule=row.molecule,
                peak_value=peak_value,
                unit=unit,
                rel_intensity=_normalize_rel_intensity(row.rel_intensity),
                source=row.source,
            )
        )

    if n_midpoints:
        notes.append(f"{n_midpoints} range row(s) collapsed to midpoint (peak_value_hi present)")
    set_aside_total = sum(set_asides.values())
    if set_aside_total:
        notes.append(f"{set_aside_total} row(s) set aside (non cm^-1 units retained separately)")

    report = ValidationReport(
        total=len(rows),
        accepted=len(accepted),
        rejected=sum(rejections.values()),
        set_aside=set_aside_total,
        rejections=rejections,
        set_asides=set_asides,
        notes=notes,
    )
    return accepted, report


# ============================================================================
# ORCHESTRATION
# ============================================================================


@dataclass(frozen=True)
class CompoundResult:
    """Per-compound engine scores plus source provenance."""

    test_A_p: float | None
    test_B_p: float | None
    separable: bool
    n_peaks: int
    sources: list[str]
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AnalysisResult:
    """Structured, provenance-preserving result of a full connector run."""

    valid: bool
    source_path: str
    formats: list[str]
    alpha: float
    n_nulls: int
    seed: int
    controls: dict[str, Any]
    validation_report: ValidationReport
    compounds: dict[str, CompoundResult]
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "source_path": self.source_path,
            "formats": self.formats,
            "alpha": self.alpha,
            "n_nulls": self.n_nulls,
            "seed": self.seed,
            "reason": self.reason,
            "controls": self.controls,
            "validation_report": self.validation_report.to_dict(),
            "compounds": {k: v.to_dict() for k, v in self.compounds.items()},
        }

    def to_json(self, path: str | Path) -> None:
        """Write the result to ``path`` as indented JSON."""
        Path(path).write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")


def _write_native_csv(rows: list[_NativeRow], path: Path) -> None:
    """Write validated rows out in the engine's native schema."""
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(engine.NATIVE_FIELDS))
        writer.writeheader()
        for row in rows:
            rel = row.rel_intensity
            writer.writerow(
                {
                    "molecule": row.molecule,
                    "peak_value": row.peak_value,
                    "unit": row.unit,
                    "rel_intensity": "" if rel is None else rel,
                    "source": row.source,
                }
            )


def _provenance(rows: list[_NativeRow]) -> dict[str, list[str]]:
    """Map each compound to its sorted, de-duplicated list of source strings."""
    prov: dict[str, set[str]] = {}
    for row in rows:
        prov.setdefault(row.molecule, set()).add(row.source)
    return {name: sorted(sources) for name, sources in prov.items()}


def run_analysis(
    source: str | Path | list[str | Path], *, nulls: int = 500, seed: int = 0
) -> AnalysisResult:
    """Ingest ``source``, validate, run the engine, and return an :class:`AnalysisResult`.

    ``source`` is a path to a native/Codex CSV, the HNC data-package zip, or a
    *list* of such paths (merged into one analysis — e.g. the Codex export plus
    fetcher-derived NIST peaks plus a curated CSV). The run is deterministic
    given ``seed``. If the engine's controls fail, the result's ``valid`` flag
    is ``False`` and ``compounds`` is empty — compound scores are never emitted
    from an invalid run.
    """
    if isinstance(source, (list, tuple)):
        raw_rows, formats = ingest_many(list(source))
        source_label = ", ".join(str(s) for s in source)
    else:
        raw_rows, formats = ingest(source)
        source_label = str(source)
    accepted, report = validate(raw_rows)
    provenance = _provenance(accepted)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_csv = Path(tmp) / "native_schema.csv"
        _write_native_csv(accepted, tmp_csv)
        peaks = engine.load_peaks(tmp_csv)
        run_result = engine.run(peaks, nulls=nulls, seed=seed)

    controls = {name: ctrl.to_dict() for name, ctrl in run_result.controls.items()}

    if not run_result.valid:
        # Propagate the engine's invalid-run state: never surface compound results.
        return AnalysisResult(
            valid=False,
            source_path=source_label,
            formats=formats,
            alpha=run_result.alpha,
            n_nulls=run_result.n_nulls,
            seed=run_result.seed,
            controls=controls,
            validation_report=report,
            compounds={},
            reason=run_result.reason,
        )

    compounds: dict[str, CompoundResult] = {}
    for name, scores in run_result.compounds.items():
        compounds[name] = CompoundResult(
            test_A_p=scores.get("test_A_p"),
            test_B_p=scores.get("test_B_p"),
            separable=bool(scores.get("separable", False)),
            n_peaks=int(scores.get("n_peaks", 0)),
            sources=provenance.get(name, []),
            note=scores.get("note"),
        )

    return AnalysisResult(
        valid=True,
        source_path=source_label,
        formats=formats,
        alpha=run_result.alpha,
        n_nulls=run_result.n_nulls,
        seed=run_result.seed,
        controls=controls,
        validation_report=report,
        compounds=compounds,
        reason=None,
    )


# ============================================================================
# CLI
# ============================================================================


def _format_summary(result: AnalysisResult) -> str:
    """Render a plain-text summary of an :class:`AnalysisResult`."""
    report = result.validation_report
    lines = [
        f"Source: {result.source_path}",
        f"Formats detected: {', '.join(result.formats)}",
        "",
        "Validation:",
        f"  total={report.total}  accepted={report.accepted}  "
        f"rejected={report.rejected}  set_aside={report.set_aside}",
    ]
    for reason, count in sorted(report.rejections.items()):
        lines.append(f"    rejected: {reason} x{count}")
    for reason, count in sorted(report.set_asides.items()):
        lines.append(f"    set aside: {reason} x{count}")
    for note in report.notes:
        lines.append(f"    note: {note}")

    lines.append("")
    lines.append(f"Controls (alpha={result.alpha}, nulls={result.n_nulls}, seed={result.seed}):")
    for name, ctrl in result.controls.items():
        lines.append(f"  {name}: {'PASS' if ctrl['passed'] else 'FAIL'}")

    lines.append("")
    if not result.valid:
        lines.append(f"RUN INVALID — {result.reason}")
        lines.append("No compound results are reported from an invalid run.")
        return "\n".join(lines)

    lines.append("Compounds:")
    for name, comp in result.compounds.items():
        pa = "n/a" if comp.test_A_p is None else f"{comp.test_A_p:.4f}"
        pb = "n/a" if comp.test_B_p is None else f"{comp.test_B_p:.4f}"
        flag = "SEPARABLE" if comp.separable else "not separable"
        lines.append(
            f"  {name}: A_p={pa} B_p={pb} n_peaks={comp.n_peaks} [{flag}]"
        )
        lines.append(f"      sources: {', '.join(comp.sources) or '(none)'}")
        if comp.note:
            lines.append(f"      note: {comp.note}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: ``connector.py <path-or-zip> [--nulls N] [--seed S] [--json out]``."""
    parser = argparse.ArgumentParser(
        description="Ingest, validate and analyze phenolic spectral data via the "
        "Phenolic Fingerprint engine."
    )
    parser.add_argument("source", help="Path to a native/Codex CSV or the HNC data-package zip")
    parser.add_argument("--nulls", type=int, default=engine.DEFAULT_NULLS,
                        help=f"Number of null permutations (default {engine.DEFAULT_NULLS})")
    parser.add_argument("--seed", type=int, default=0, help="Random seed (default 0)")
    parser.add_argument("--json", dest="json_out", default=None,
                        help="Optional path to write the full result as JSON")
    args = parser.parse_args(argv)

    try:
        result = run_analysis(args.source, nulls=args.nulls, seed=args.seed)
    except ConnectorError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(_format_summary(result))
    if args.json_out:
        result.to_json(args.json_out)
        print(f"\nWrote JSON result to {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
