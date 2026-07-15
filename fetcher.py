#!/usr/bin/env python3
"""Fetcher — network-capable ingest of open-source vibrational spectra.

This is the companion to ``connector.py``. The connector is deliberately
network-free (local files only); this module is where network access lives, so
the two concerns stay separated. It pulls infrared spectra for phenolic
compounds from the **NIST Chemistry WebBook** (JCAMP-DX, Coblentz Society
collection — U.S. government hosted, citable), peak-picks the digitized curve,
and emits rows in the connector's native schema
(``molecule, peak_value, unit, rel_intensity, source``). The output CSV is then
ingested by ``connector.py`` exactly like any other local file.

Only open, citable sources are used, and every emitted peak carries a real
source string (the NIST URL + Coblentz reference), so it passes the connector's
"source required" validation gate.

Design constraints:
* Standard library (``urllib``) + numpy only.
* Polite and robust: descriptive User-Agent, ret/backoff on 429/5xx, graceful
  ``None`` on 404 (compound has no IR spectrum on NIST).
* Deterministic peak-picking; no global state.
* Offline-testable: :func:`parse_jcamp_xydata` and :func:`pick_peaks` are pure
  and exercised against a bundled fixture; only :func:`fetch_nist_ir_jcamp`
  touches the network.
"""

from __future__ import annotations

import argparse
import csv
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import numpy as np

__all__ = [
    "FetchError",
    "SpectrumPeak",
    "NIST_CAS",
    "SMILES",
    "COMPUTED_SOURCE",
    "nist_ir_url",
    "fetch_nist_ir_jcamp",
    "parse_jcamp_xydata",
    "pick_peaks",
    "computed_toolchain_available",
    "compute_xtb_frequencies",
    "SourceAdapter",
    "NISTWebBookAdapter",
    "JcampUrlAdapter",
    "ComputedXtbAdapter",
    "fetch_compound_peaks",
    "write_native_csv",
    "main",
]

NIST_BASE: Final[str] = "https://webbook.nist.gov/cgi/cbook.cgi"
_USER_AGENT: Final[str] = "AureonPhenolicFetcher/1.0 (open-source spectral research; contact via repo)"

# NIST WebBook IDs (C + CAS number, no dashes) for the phenolic panel. Only a
# subset actually carry IR spectra on NIST; the rest return 404 and are skipped.
NIST_CAS: Final[dict[str, str]] = {
    "caffeic acid": "C331395",
    "ferulic acid": "C1135246",
    "rutin": "C153184",
    "chlorogenic acid": "C327979",
    "quercetin": "C117395",
    "kaempferol": "C520183",
    "luteolin": "C491703",
    "apigenin": "C520365",
    "aucubin": "C479981",
}

# Qualitative intensity ladder from fractional band depth (transmittance dip).
_INTENSITY_BANDS: Final[tuple[tuple[float, str], ...]] = (
    (0.66, "vs"),
    (0.40, "s"),
    (0.20, "m"),
    (0.08, "w"),
    (0.0, "vw"),
)


class FetchError(Exception):
    """Raised on unrecoverable network or parse failures."""


@dataclass(frozen=True)
class SpectrumPeak:
    """A peak-picked band: wavenumber (cm^-1) and normalized depth in [0, 1]."""

    wavenumber_cm1: float
    depth: float

    def qualitative_intensity(self) -> str:
        """Map fractional band depth onto the vs/s/m/w/vw ladder."""
        for threshold, label in _INTENSITY_BANDS:
            if self.depth >= threshold:
                return label
        return "vw"


# ============================================================================
# NETWORK
# ============================================================================


def nist_ir_url(nist_id: str, index: int = 0) -> str:
    """Return the JCAMP-DX download URL for a NIST WebBook IR spectrum."""
    return f"{NIST_BASE}?JCAMP={nist_id}&Type=IR&Index={index}"


def _build_opener() -> urllib.request.OpenerDirector:
    """Opener that honours the environment proxy and the agent CA bundle."""
    ca_bundle = os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE")
    if not ca_bundle:
        for candidate in ("/root/.ccr/ca-bundle.crt",):
            if Path(candidate).exists():
                ca_bundle = candidate
                break
    context = ssl.create_default_context(cafile=ca_bundle) if ca_bundle else ssl.create_default_context()
    handlers: list[urllib.request.BaseHandler] = [
        urllib.request.ProxyHandler(urllib.request.getproxies()),
        urllib.request.HTTPSHandler(context=context),
    ]
    return urllib.request.build_opener(*handlers)


def fetch_nist_ir_jcamp(
    nist_id: str,
    *,
    index: int = 0,
    timeout: float = 30.0,
    retries: int = 4,
    backoff: float = 2.0,
    _opener: urllib.request.OpenerDirector | None = None,
) -> str | None:
    """Download a NIST WebBook IR JCAMP-DX record.

    Returns the raw JCAMP text, or ``None`` if NIST has no such spectrum (404).
    Retries with exponential backoff on rate-limit (429) and server (5xx)
    errors. Raises :class:`FetchError` if retries are exhausted.
    """
    opener = _opener or _build_opener()
    url = nist_ir_url(nist_id, index)
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            with opener.open(request, timeout=timeout) as response:
                text = response.read().decode("utf-8", errors="replace")
            if "##TITLE" not in text or "##XYDATA" not in text:
                return None  # NIST returns a stub page when no spectrum exists
            return text
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            if exc.code in (429, 500, 502, 503, 504):
                last_error = exc
                time.sleep(backoff * (2**attempt))
                continue
            raise FetchError(f"HTTP {exc.code} fetching {url}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            time.sleep(backoff * (2**attempt))
    raise FetchError(f"Exhausted {retries} retries fetching {url}: {last_error}")


# ============================================================================
# JCAMP-DX PARSING
# ============================================================================


def _parse_headers(text: str) -> dict[str, str]:
    headers: dict[str, str] = {}
    for line in text.splitlines():
        if line.startswith("##") and "=" in line:
            key, _, value = line[2:].partition("=")
            headers[key.strip().upper()] = value.strip()
    return headers


def parse_jcamp_xydata(text: str) -> tuple[np.ndarray, np.ndarray, dict[str, str]]:
    """Parse a JCAMP-DX ``(X++(Y..Y))`` record into (x_cm^-1, y, headers).

    Handles the plain-ASCII affine form used by the NIST/Coblentz IR records:
    each data line begins with its starting X, followed by evenly spaced Y
    values. ``XFACTOR``/``YFACTOR`` scaling is applied. Raises
    :class:`FetchError` on a record that is not wavenumber-based XYDATA.
    """
    headers = _parse_headers(text)
    if "XYDATA" not in headers:
        raise FetchError("JCAMP record has no ##XYDATA block")
    xfactor = float(headers.get("XFACTOR", "1"))
    yfactor = float(headers.get("YFACTOR", "1"))
    deltax = float(headers.get("DELTAX", "1"))
    xunits = headers.get("XUNITS", "").upper()
    if "1/CM" not in xunits and "CM-1" not in xunits and "CM^-1" not in xunits:
        raise FetchError(f"Unsupported XUNITS {xunits!r}; expected wavenumber (1/CM)")

    step = -abs(deltax) if float(headers.get("FIRSTX", "0")) > float(headers.get("LASTX", "0")) else abs(deltax)
    xs: list[float] = []
    ys: list[float] = []
    in_data = False
    for line in text.splitlines():
        if line.startswith("##XYDATA"):
            in_data = True
            continue
        if not in_data:
            continue
        if line.startswith("##"):
            break  # end of data block
        tokens = line.replace(",", " ").split()
        if len(tokens) < 2:
            continue
        try:
            x0 = float(tokens[0]) * xfactor
            y_values = [float(tok) * yfactor for tok in tokens[1:]]
        except ValueError:
            continue
        for i, y in enumerate(y_values):
            xs.append(x0 + i * step * xfactor)
            ys.append(y)
    if not xs:
        raise FetchError("JCAMP ##XYDATA block contained no parseable points")
    x = np.array(xs)
    y = np.array(ys)
    order = np.argsort(x)
    return x[order], y[order], headers


# ============================================================================
# PEAK PICKING
# ============================================================================


def pick_peaks(
    x_cm1: np.ndarray,
    y: np.ndarray,
    *,
    yunits: str,
    min_prominence: float = 0.08,
    min_wavenumber: float = 100.0,
    min_separation_cm1: float = 6.0,
    max_peaks: int = 60,
) -> list[SpectrumPeak]:
    """Peak-pick absorption bands from a digitized spectrum.

    For transmittance data, absorption bands are local *minima*; the curve is
    inverted to absorbance-like depth first. A peak is a strict local maximum of
    that depth at least ``min_prominence`` (normalized 0-1) high. Peaks closer
    than ``min_separation_cm1`` are merged, keeping the deeper one, so adjacent
    digitization samples and ripples do not double-count. Returns peaks sorted by
    ascending wavenumber, keeping the ``max_peaks`` most prominent.
    """
    if x_cm1.size < 3:
        return []
    absorb = (1.0 - y) if "TRANSMIT" in yunits.upper() else y
    lo, hi = float(np.min(absorb)), float(np.max(absorb))
    span = hi - lo
    if span <= 0:
        return []
    norm = (absorb - lo) / span  # 0..1 depth

    candidates: list[SpectrumPeak] = []
    for i in range(1, norm.size - 1):
        if norm[i] > norm[i - 1] and norm[i] > norm[i + 1] and norm[i] >= min_prominence:
            wn = float(x_cm1[i])
            if wn >= min_wavenumber:
                candidates.append(SpectrumPeak(wavenumber_cm1=round(wn, 1), depth=round(float(norm[i]), 4)))

    # Merge near-neighbours (keep the deepest within each separation window).
    merged: list[SpectrumPeak] = []
    for peak in sorted(candidates, key=lambda p: p.wavenumber_cm1):
        if merged and (peak.wavenumber_cm1 - merged[-1].wavenumber_cm1) < min_separation_cm1:
            if peak.depth > merged[-1].depth:
                merged[-1] = peak
        else:
            merged.append(peak)

    if len(merged) > max_peaks:
        merged = sorted(merged, key=lambda p: p.depth, reverse=True)[:max_peaks]
    return sorted(merged, key=lambda p: p.wavenumber_cm1)


# ============================================================================
# COMPUTED (THEORETICAL) VIBRATIONAL SPECTRA — GFN2-xTB
# ============================================================================

# Canonical SMILES for the computed channel (public, well-known structures).
# Glycosides / large esters (rutin, chlorogenic, chicoric, rosmarinic, silybin,
# aucubin) are intentionally omitted: their finite-difference Hessians are too
# large to compute cheaply, and they are handled by the experimental channels.
SMILES: Final[dict[str, str]] = {
    "caffeic acid": r"OC(=O)/C=C/c1ccc(O)c(O)c1",
    "ferulic acid": r"COc1cc(/C=C/C(=O)O)ccc1O",
    "apigenin": r"O=c1cc(-c2ccc(O)cc2)oc2cc(O)cc(O)c12",
    "luteolin": r"O=c1cc(-c2ccc(O)c(O)c2)oc2cc(O)cc(O)c12",
    "kaempferol": r"O=c1c(O)c(-c2ccc(O)cc2)oc2cc(O)cc(O)c12",
    "quercetin": r"O=c1c(O)c(-c2ccc(O)c(O)c2)oc2cc(O)cc(O)c12",
    # Glycosides / larger esters (PubChem canonical SMILES). These have many
    # rotatable bonds; the computed fingerprint uses a single embedded conformer
    # and is theoretical only.
    "chlorogenic acid": r"C1C(C(C(CC1(C(=O)O)O)OC(=O)C=CC2=CC(=C(C=C2)O)O)O)O",
    "aucubin": r"C1=COC(C2C1C(C=C2CO)O)OC3C(C(C(C(O3)CO)O)O)O",
    "rutin": r"CC1C(C(C(C(O1)OCC2C(C(C(C(O2)OC3=C(OC4=CC(=CC(=C4C3=O)O)O)C5=CC(=C(C=C5)O)O)O)O)O)O)O)O",
}

_EV_TO_CM1: Final[float] = 8065.544  # 1 eV in cm^-1
COMPUTED_SOURCE: Final[str] = "COMPUTED GFN2-xTB (theoretical, non-experimental)"


def computed_toolchain_available() -> bool:
    """True when rdkit + ase + tblite (GFN2-xTB) can all be imported."""
    try:
        import ase  # noqa: F401
        import tblite.ase  # noqa: F401
        from rdkit import Chem  # noqa: F401
    except ImportError:
        return False
    return True


def compute_xtb_frequencies(
    smiles: str,
    *,
    seed: int = 42,
    fmax: float = 0.05,
    max_opt_steps: int = 300,
    min_wavenumber: float = 100.0,
) -> list[float]:
    """Compute GFN2-xTB vibrational frequencies (cm^-1) for a SMILES string.

    RDKit embeds a 3D conformer (deterministic via ``seed``), tblite/ASE
    optimizes the geometry and builds a finite-difference Hessian. Only real
    modes above ``min_wavenumber`` are returned (imaginary/low modes dropped).
    Raises :class:`FetchError` if the toolchain is unavailable.
    """
    if not computed_toolchain_available():
        raise FetchError("computed toolchain (rdkit+ase+tblite) not available")
    import tempfile

    from ase import Atoms
    from ase.optimize import BFGS
    from ase.vibrations import Vibrations
    from rdkit import Chem
    from rdkit.Chem import AllChem
    from tblite.ase import TBLite

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise FetchError(f"RDKit could not parse SMILES {smiles!r}")
    mol = Chem.AddHs(mol)
    if AllChem.EmbedMolecule(mol, randomSeed=seed) != 0:
        raise FetchError(f"RDKit could not embed a 3D conformer for {smiles!r}")
    AllChem.MMFFOptimizeMolecule(mol)
    conf = mol.GetConformer()
    symbols = [a.GetSymbol() for a in mol.GetAtoms()]
    positions = [list(conf.GetAtomPosition(i)) for i in range(mol.GetNumAtoms())]

    atoms = Atoms(symbols=symbols, positions=positions)
    atoms.calc = TBLite(method="GFN2-xTB", verbosity=0)
    BFGS(atoms, logfile=None).run(fmax=fmax, steps=max_opt_steps)

    with tempfile.TemporaryDirectory() as tmp:
        vib = Vibrations(atoms, name=str(Path(tmp) / "vib"))
        vib.run()
        energies = vib.get_energies()  # eV, complex for imaginary modes
    freqs = []
    for e in energies:
        real = float(e.real) if hasattr(e, "real") else float(e)
        imag = abs(float(e.imag)) if hasattr(e, "imag") else 0.0
        cm = real * _EV_TO_CM1
        if imag < 1e-9 and cm > min_wavenumber:
            freqs.append(round(cm, 1))
    return sorted(freqs)


# ============================================================================
# SOURCE ADAPTERS
# ============================================================================


class SourceAdapter:
    """Base class for a spectral data source. Subclasses set name/kind."""

    name: str = "base"
    kind: str = "experimental"  # or "computed"

    def available(self) -> bool:
        """Whether this adapter can be used at all (toolchain/config present)."""
        return True

    def fetch(
        self,
        molecule: str,
        *,
        min_prominence: float = 0.12,
        timeout: float = 30.0,
        _opener: urllib.request.OpenerDirector | None = None,
    ) -> list[dict[str, str | float]]:
        """Return native-schema rows for ``molecule`` (empty if unavailable)."""
        raise NotImplementedError


def _rows_from_jcamp(text: str, molecule: str, source: str, min_prominence: float) -> list[dict[str, str | float]]:
    x, y, headers = parse_jcamp_xydata(text)
    peaks = pick_peaks(x, y, yunits=headers.get("YUNITS", ""), min_prominence=min_prominence)
    return [
        {
            "molecule": molecule,
            "peak_value": peak.wavenumber_cm1,
            "unit": "cm^-1",
            "rel_intensity": peak.qualitative_intensity(),
            "source": source,
        }
        for peak in peaks
    ]


class NISTWebBookAdapter(SourceAdapter):
    """NIST Chemistry WebBook IR (Coblentz Society) — experimental."""

    name = "nist"
    kind = "experimental"

    def fetch(self, molecule, *, min_prominence=0.12, timeout=30.0, _opener=None):
        key = molecule.strip().lower()
        nist_id = NIST_CAS.get(key)
        if nist_id is None:
            return []
        text = fetch_nist_ir_jcamp(nist_id, timeout=timeout, _opener=_opener)
        if text is None:
            return []
        coblentz = _parse_headers(text).get("SOURCE REFERENCE", "").strip()
        source = f"NIST WebBook IR ({coblentz}); {NIST_BASE}?ID={nist_id}#IR-Spec"
        return _rows_from_jcamp(text, key, source, min_prominence)


class JcampUrlAdapter(SourceAdapter):
    """Generic JCAMP-DX-over-HTTP adapter (e.g. OSDB/ROD) — experimental.

    Configured with a ``{molecule: url}`` map so any open JCAMP source can plug
    in. ``available()`` is True only when a URL map is configured.
    """

    name = "jcamp"
    kind = "experimental"

    def __init__(self, url_map: dict[str, str] | None = None, label: str = "JCAMP source"):
        self.url_map = {k.lower(): v for k, v in (url_map or {}).items()}
        self.label = label

    def available(self) -> bool:
        return bool(self.url_map)

    def fetch(self, molecule, *, min_prominence=0.12, timeout=30.0, _opener=None):
        url = self.url_map.get(molecule.strip().lower())
        if not url:
            return []
        opener = _opener or _build_opener()
        request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
        with opener.open(request, timeout=timeout) as response:
            text = response.read().decode("utf-8", errors="replace")
        return _rows_from_jcamp(text, molecule.strip().lower(), f"{self.label}; {url}", min_prominence)


class ComputedXtbAdapter(SourceAdapter):
    """GFN2-xTB computed vibrational spectra — THEORETICAL (separate lane)."""

    name = "computed"
    kind = "computed"

    def __init__(self, seed: int = 42):
        self.seed = seed

    def available(self) -> bool:
        return computed_toolchain_available()

    def fetch(self, molecule, *, min_prominence=0.12, timeout=30.0, _opener=None):
        key = molecule.strip().lower()
        smiles = SMILES.get(key)
        if smiles is None or not self.available():
            return []
        freqs = compute_xtb_frequencies(smiles, seed=self.seed)
        return [
            {"molecule": key, "peak_value": f, "unit": "cm^-1", "rel_intensity": "", "source": COMPUTED_SOURCE}
            for f in freqs
        ]


_ADAPTERS: Final[dict[str, SourceAdapter]] = {
    "nist": NISTWebBookAdapter(),
    "jcamp": JcampUrlAdapter(),
    "computed": ComputedXtbAdapter(),
}


# ============================================================================
# ORCHESTRATION
# ============================================================================


def fetch_compound_peaks(
    molecule: str,
    *,
    sources: tuple[str, ...] = ("nist",),
    min_prominence: float = 0.12,
    timeout: float = 30.0,
    _opener: urllib.request.OpenerDirector | None = None,
) -> list[dict[str, str | float]]:
    """Fetch native-schema peak rows for ``molecule`` across selected sources.

    ``sources`` names adapters in :data:`_ADAPTERS` (``"nist"``, ``"jcamp"``,
    ``"computed"``, or ``"all"``). Unavailable adapters are skipped. Each row is
    ``{molecule, peak_value, unit, rel_intensity, source}`` ready for
    ``connector.ingest``; computed rows carry the theoretical source marker.
    """
    names = tuple(_ADAPTERS) if "all" in sources else sources
    rows: list[dict[str, str | float]] = []
    for name in names:
        adapter = _ADAPTERS.get(name)
        if adapter is None:
            raise FetchError(f"unknown source {name!r}; known: {sorted(_ADAPTERS)}")
        if not adapter.available():
            continue
        rows.extend(adapter.fetch(molecule, min_prominence=min_prominence, timeout=timeout, _opener=_opener))
    return rows


def write_native_csv(rows: list[dict[str, str | float]], path: str | Path) -> None:
    """Write native-schema rows to ``path`` for the connector to ingest."""
    fields = ["molecule", "peak_value", "unit", "rel_intensity", "source"]
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    """CLI: ``fetcher.py <compound...> [--source nist|jcamp|computed|all] [--out f.csv]``."""
    parser = argparse.ArgumentParser(
        description="Fetch open-source vibrational spectra into the connector's "
        "native schema (experimental: NIST/JCAMP; computed: GFN2-xTB)."
    )
    parser.add_argument("compounds", nargs="*", default=[],
                        help="Compound names (default: all known)")
    parser.add_argument("--source", default="nist",
                        help="Comma-separated adapters: nist,jcamp,computed,all (default nist)")
    parser.add_argument("--out", default=None, help="Output native-schema CSV path")
    parser.add_argument("--min-prominence", type=float, default=0.12,
                        help="Minimum normalized band depth to count as a peak")
    parser.add_argument("--list", action="store_true", help="List known compounds and exit")
    args = parser.parse_args(argv)

    sources = tuple(s.strip() for s in args.source.split(",") if s.strip())
    if args.list:
        print("NIST IR:", ", ".join(sorted(NIST_CAS)))
        print("computed (xTB):", ", ".join(sorted(SMILES)))
        print("computed toolchain available:", computed_toolchain_available())
        return 0

    known = sorted(set(NIST_CAS) | set(SMILES))
    targets = args.compounds or known
    all_rows: list[dict[str, str | float]] = []
    for molecule in targets:
        try:
            rows = fetch_compound_peaks(molecule, sources=sources, min_prominence=args.min_prominence)
        except FetchError as exc:
            print(f"warning: {molecule}: {exc}", file=sys.stderr)
            continue
        print(f"{molecule}: {len(rows)} peaks", file=sys.stderr)
        all_rows.extend(rows)

    if not all_rows:
        print("No peaks fetched.", file=sys.stderr)
        return 1
    if args.out:
        write_native_csv(all_rows, args.out)
        print(f"Wrote {len(all_rows)} peaks to {args.out}", file=sys.stderr)
    else:
        writer = csv.DictWriter(sys.stdout, fieldnames=["molecule", "peak_value", "unit", "rel_intensity", "source"])
        writer.writeheader()
        writer.writerows(all_rows)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:  # downstream pipe (e.g. `| head`) closed early
        sys.exit(0)
