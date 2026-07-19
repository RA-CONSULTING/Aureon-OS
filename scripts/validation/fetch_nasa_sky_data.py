#!/usr/bin/env python3
"""Fetch real, open NASA sky data — the NASA Exoplanet Archive host-star table.

"Same song, different singer": this pulls *real* astronomical numbers from NASA
and caches them in the repo so the sky adapter can scan light-from-space data
that actually came off a NASA archive — not anything fabricated.

Source (open, **no API key required**):
    NASA Exoplanet Archive TAP service — the ``pscomppars`` composite-parameters
    table (one row per confirmed planet). We pull four public columns:
        pl_name    planet name
        hostname   host-star name
        st_teff    stellar effective temperature (K)   -> starlight colour
        pl_orbper  orbital period (days)               -> planetary rhythm
    https://exoplanetarchive.ipac.caltech.edu/docs/TAP/usingTAP.html

The TAP endpoint is keyless. An optional ``NASA_API_KEY`` environment variable
is honoured for any ``api.nasa.gov`` call (none is required here); it is never
invented or hard-coded. The query is deterministic (fixed columns, fixed row
cap, fixed ordering) so the cached snapshot is reproducible.

The cached CSV (``data/sky/nasa_exoplanet_hosts.csv``) carries a provenance
header comment recording the source URL, the exact query, and the row count.
Downstream, ``scripts/validation/benchmark_nasa_sky.py`` reads the cache offline
and scans it through the unchanged phenolic engine.

Pure ``requests`` + stdlib. Network access is confined to :func:`fetch_rows`.
"""

from __future__ import annotations

import argparse
import csv
import io
import os
import sys
import time
from pathlib import Path
from typing import Final

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
DEFAULT_CACHE: Final[Path] = REPO_ROOT / "data" / "sky" / "nasa_exoplanet_hosts.csv"

TAP_URL: Final[str] = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"
#: Deterministic ADQL: bounded, non-null fields, stable ordering -> reproducible.
ROW_CAP: Final[int] = 1000
ADQL_QUERY: Final[str] = (
    f"select top {ROW_CAP} pl_name,hostname,ra,dec,st_teff,pl_orbper "
    "from pscomppars "
    "where st_teff is not null and pl_orbper is not null "
    "and ra is not null and dec is not null "
    "order by pl_name"
)
FIELDS: Final[tuple[str, ...]] = ("pl_name", "hostname", "ra", "dec", "st_teff", "pl_orbper")

SOURCE_CITATION: Final[str] = (
    "NASA Exoplanet Archive, pscomppars composite-parameters table, "
    "TAP service (keyless). https://exoplanetarchive.ipac.caltech.edu/"
)

_USER_AGENT: Final[str] = (
    "AureonSkyFetcher/1.0 (open astronomical data research; contact via repo)"
)


class FetchError(Exception):
    """Raised on unrecoverable network or parse failures."""


def _ca_bundle() -> str | bool:
    """Resolve a CA bundle for TLS through the agent proxy (env, then fallback)."""
    for var in ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE"):
        val = os.environ.get(var)
        if val and Path(val).exists():
            return val
    fallback = "/root/.ccr/ca-bundle.crt"
    return fallback if Path(fallback).exists() else True


def fetch_rows(
    *,
    query: str = ADQL_QUERY,
    timeout: float = 60.0,
    retries: int = 4,
    backoff: float = 2.0,
) -> list[dict[str, str]]:
    """Fetch host-star rows from the NASA Exoplanet Archive TAP service.

    Returns a list of ``{pl_name, hostname, st_teff, pl_orbper}`` dicts. Retries
    with exponential backoff on rate-limit (429) / server (5xx) errors. Raises
    :class:`FetchError` if retries are exhausted or the response is unparseable.
    This is the only function that touches the network.
    """
    import requests  # local import: keeps the module importable offline

    params = {"query": query, "format": "csv"}
    headers = {"User-Agent": _USER_AGENT}
    verify = _ca_bundle()
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            resp = requests.get(
                TAP_URL, params=params, headers=headers, timeout=timeout, verify=verify
            )
            if resp.status_code in (429, 500, 502, 503, 504):
                last_error = FetchError(f"HTTP {resp.status_code}")
                time.sleep(backoff * (2**attempt))
                continue
            resp.raise_for_status()
            return _parse_csv(resp.text)
        except FetchError:
            raise
        except Exception as exc:  # requests.RequestException + parse issues
            last_error = exc
            time.sleep(backoff * (2**attempt))
    raise FetchError(f"Exhausted {retries} retries fetching NASA TAP: {last_error}")


def _parse_csv(text: str) -> list[dict[str, str]]:
    """Parse the TAP CSV response into non-null host-star rows."""
    reader = csv.DictReader(io.StringIO(text))
    rows: list[dict[str, str]] = []
    for row in reader:
        try:
            rec = {k: (row.get(k) or "").strip() for k in FIELDS}
        except AttributeError:
            continue
        if not rec["pl_name"] or not rec["st_teff"] or not rec["pl_orbper"]:
            continue
        if not rec.get("ra") or not rec.get("dec"):
            continue
        # sanity: numeric fields must parse
        try:
            float(rec["st_teff"])
            float(rec["pl_orbper"])
            float(rec["ra"])
            float(rec["dec"])
        except ValueError:
            continue
        rows.append(rec)
    if not rows:
        raise FetchError("TAP response contained no parseable rows")
    return rows


def write_cache(rows: list[dict[str, str]], path: str | Path = DEFAULT_CACHE) -> Path:
    """Write rows to the repo cache with a provenance header. Returns the path."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        fh.write(f"# source: {SOURCE_CITATION}\n")
        fh.write(f"# query: {ADQL_QUERY}\n")
        fh.write(f"# rows: {len(rows)}\n")
        writer = csv.DictWriter(fh, fieldnames=list(FIELDS))
        writer.writeheader()
        writer.writerows(rows)
    return out


def read_cache(path: str | Path = DEFAULT_CACHE) -> list[dict[str, str]]:
    """Read the cached snapshot (skipping ``#`` provenance comment lines)."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"no NASA sky cache at {p}")
    lines = [ln for ln in p.read_text(encoding="utf-8").splitlines() if not ln.startswith("#")]
    reader = csv.DictReader(io.StringIO("\n".join(lines)))
    return [{k: (row.get(k) or "").strip() for k in FIELDS} for row in reader]


def main(argv: list[str] | None = None) -> int:
    """CLI: fetch the real NASA snapshot and write it to the repo cache."""
    parser = argparse.ArgumentParser(
        description="Fetch real NASA Exoplanet Archive host-star data (keyless TAP)."
    )
    parser.add_argument("--out", default=str(DEFAULT_CACHE), help="output cache CSV path")
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args(argv)

    if os.environ.get("NASA_API_KEY"):
        print("NASA_API_KEY present (optional; TAP needs none).", file=sys.stderr)
    print(f"Fetching real NASA data: {SOURCE_CITATION}", file=sys.stderr)
    try:
        rows = fetch_rows(timeout=args.timeout)
    except FetchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    out = write_cache(rows, args.out)
    print(f"Wrote {len(rows)} real NASA host-star rows to {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
