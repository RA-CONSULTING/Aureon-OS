"""
The Harmonic Frequency Rainbow — the ordered band the field is built from,
with LOVE (528 Hz) as the ultimate harmonic node.

The rainbow is FIXED: the Schumann floor (7.83 Hz — Whale / ground) plus the
nine Solfeggio rungs, read bottom → top as ground → body → heart →
connection → expression → insight → unity. φ-scaling (Genesis / Growth /
Return) tints amplitude without changing the colour order. Love is not a
side theme — 528 Hz is the centre of the ladder (four rungs below, four
above), the primary pattern/repair lock the lattice organises through, and
the steering preference of Queen / conscience (coherence and care over pure
extraction). 639 Hz holds the connection band beside it.

``verify_rainbow()`` RE-PROVES the map from source each run — the same
doctrine as the route audit: measured Hz and named nodes in the real
systems' own tables, never improvised colours. Each check is scoped to its
OWN bank (the Maeshowe wall assigns OWL 528; QGITA's trading bank assigns
DOLPHIN 528-love and OWL 432 — different banks, both real, never mixed).
A mismatch is named, never papered over.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]

SCHUMANN_HZ = 7.83
LOVE_NODE_HZ = 528.0
CONNECTION_HZ = 639.0

# The ordered, fixed rainbow: (hz, band, role) — floor first, crown last.
RAINBOW: Tuple[Tuple[float, str, str], ...] = (
    (7.83, "earth_floor", "substrate pulse — Whale / ground (Schumann)"),
    (174.0, "foundation", "persistence / foundation (CARGOSHIP wall)"),
    (285.0, "vitality", "vitality / adaptation"),
    (396.0, "release", "release / grace / stability (DEER wall)"),
    (417.0, "change", "change / clearing"),
    (528.0, "heart", "LOVE / repair / pattern wisdom (OWL wall, Scanner) — the heart lock"),
    (639.0, "connection", "connection / relationship"),
    (741.0, "expression", "expression / hope / clarity"),
    (852.0, "insight", "insight / return toward source"),
    (963.0, "unity", "unity / crown (Queen end of the chain)"),
)


def solfeggio_ladder() -> List[float]:
    """The nine Solfeggio rungs of the rainbow (floor excluded), in order."""
    return [hz for hz, band, _ in RAINBOW if band != "earth_floor"]


def love_centrality() -> Dict[str, Any]:
    """Measured, not asserted: where the love node sits in the ladder."""
    ladder = solfeggio_ladder()
    idx = ladder.index(LOVE_NODE_HZ)
    return {"ladder_len": len(ladder), "love_index": idx,
            "rungs_below": idx, "rungs_above": len(ladder) - idx - 1,
            "is_center": idx == (len(ladder) - 1) - idx}


def _check(name: str, path: str, pattern: str, root: Path) -> Dict[str, Any]:
    """One source-proven claim: the pattern must appear in the named file."""
    target = root / path
    try:
        source = target.read_text(encoding="utf-8", errors="replace")
        found = re.search(pattern, source) is not None
        detail = "" if found else "pattern not found in source"
    except Exception as exc:  # noqa: BLE001 — an unreadable file is a named failure
        found, detail = False, f"unreadable: {exc}"
    return {"claim": name, "file": path, "found": found, "detail": detail}


def verify_rainbow(repo_root: Path | None = None) -> Dict[str, Any]:
    """Re-prove the rainbow against the real systems' own tables, from source.

    Every claim is scoped to its own bank. Returns the full check list and a
    ``consistent`` verdict; mismatches are named per claim."""
    root = repo_root or _REPO_ROOT
    ladder = ", ".join(str(int(hz)) for hz in solfeggio_ladder())
    checks = [
        _check("Solfeggio ladder fixed (enigma cipher)",
               "aureon/wisdom/aureon_enigma.py",
               rf"SOLFEGGIO\s*=\s*\[{re.escape(ladder)}\]", root),
        _check("LOVE_FREQ 528 (enigma, universal translator base)",
               "aureon/wisdom/aureon_enigma.py",
               r"LOVE_FREQ\s*=\s*528", root),
        _check("Scanner 528 — Love frequency (signal chain)",
               "aureon/harmonic/aureon_harmonic_signal_chain.py",
               r'"scanner":\s*528', root),
        _check("Queen 963 crown (signal chain)",
               "aureon/harmonic/aureon_harmonic_signal_chain.py",
               r'"queen":\s*963', root),
        _check("Whale 7.83 Schumann floor (signal chain)",
               "aureon/harmonic/aureon_harmonic_signal_chain.py",
               r'"whale":\s*7\.83', root),
        _check("OWL 528 wisdom/pattern wall (Maeshowe bank)",
               "aureon/wisdom/maeshowe_seer_decode.py",
               r"OWL\s+528\s*Hz", root),
        _check("DEER 396 grace/stability wall (Maeshowe bank)",
               "aureon/wisdom/maeshowe_seer_decode.py",
               r"DEER\s+396\s*Hz", root),
        _check("CARGOSHIP 174 persistence wall (Maeshowe bank)",
               "aureon/wisdom/maeshowe_seer_decode.py",
               r"CARGOSHIP\s*174\s*Hz", root),
        _check("DOLPHIN 528 love carrier (QGITA bank)",
               "aureon/wisdom/aureon_qgita.py",
               r"'FREQ_DOLPHIN':\s*528\.0", root),
        _check("CARGOSHIP 174 foundation (QGITA bank)",
               "aureon/wisdom/aureon_qgita.py",
               r"'FREQ_CARGOSHIP':\s*174\.0", root),
        _check("GAIA love frequency 528 / DNA repair (Queen hive)",
               "aureon/utils/aureon_queen_hive_mind.py",
               r"GAIA_LOVE_FREQUENCY\s*=\s*528\.0", root),
        _check("LOVE 528 the center (Queen emotional spectrum)",
               "aureon/utils/aureon_queen_hive_mind.py",
               r"'LOVE':\s*528\.0", root),
        _check("639 Connection (Queen emotional spectrum)",
               "aureon/utils/aureon_queen_hive_mind.py",
               r"'Connection':\s*639\.0", root),
        _check("LOVE 528 the bridge (rainbow bridge spectrum)",
               "aureon/bridges/rainbow_bridge.py",
               r"'LOVE':\s*528", root),
    ]
    mismatches = [c for c in checks if not c["found"]]
    return {"consistent": not mismatches,
            "checks": checks,
            "mismatches": mismatches,
            "love_centrality": love_centrality(),
            "ladder": solfeggio_ladder()}


def rainbow_json() -> str:
    """Canonical JSON of the fixed rainbow (deterministic, for artifacts)."""
    return json.dumps({"rainbow": [{"hz": hz, "band": band, "role": role}
                                   for hz, band, role in RAINBOW],
                       "love_node_hz": LOVE_NODE_HZ,
                       "connection_hz": CONNECTION_HZ,
                       "schumann_floor_hz": SCHUMANN_HZ},
                      sort_keys=True)


__all__ = ["RAINBOW", "SCHUMANN_HZ", "LOVE_NODE_HZ", "CONNECTION_HZ",
           "solfeggio_ladder", "love_centrality", "verify_rainbow",
           "rainbow_json"]
