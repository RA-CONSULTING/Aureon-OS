"""Locate the checkout that vendors the Space replays. Does not write."""

from __future__ import annotations

from pathlib import Path

_MARKER = Path("huggingface") / "hnc-field" / "guard.py"
_AUREON = Path("aureon") / "core" / "hnc_field.py"


def repo_root() -> Path:
    """Directory that contains both the Space guard and the aureon package.

    Raises FileNotFoundError when this process is not inside that checkout.
    The server needs the checkout, the same as the earlier public server.
    """

    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / _MARKER).is_file() and (parent / _AUREON).is_file():
            return parent
    raise FileNotFoundError("huggingface/hnc-field/guard.py was not found above the server")


def brain_json() -> Path:
    return repo_root() / "huggingface" / "hnc-field" / "replay" / "brain.json"


def qgita_json() -> Path:
    return repo_root() / "huggingface" / "qgita-snr" / "replay" / "qgita_snr.json"


def qgita_series() -> Path:
    return repo_root() / "huggingface" / "qgita-snr" / "data" / "de440_timeseries.csv"


def organism_json() -> Path:
    return repo_root() / "huggingface" / "organism-replay" / "replay" / "organism.json"


def auris_json() -> Path:
    return repo_root() / "huggingface" / "fixed-seed-reproducible-runs" / "auris_nodes.json"


def holds_readme() -> Path:
    return repo_root() / "huggingface" / "README.md"


def space_guard() -> Path:
    return repo_root() / "huggingface" / "hnc-field" / "guard.py"
