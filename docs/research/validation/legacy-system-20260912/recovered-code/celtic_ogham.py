#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║   ᚑ  CELTIC OGHAM DECODER — Newgrange Solstice Archive  ᚑ                  ║
║   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ║
║                                                                              ║
║   Decoded through the Aureon HNC Architecture                                ║
║   Aureon Institute · R&A Consulting and Brokerage Services Ltd.             ║
║                                                                              ║
║   Sources:                                                                   ║
║     McMann, J. (1993) Loughcrew: The Cairns                                 ║
║     O'Kelly, M.J. (1982) Newgrange: Archaeology, Art and Legend             ║
║     Stifter, D. (2006) Sengoídelc — Old Irish for Beginners                ║
║     MacAlister, R.A.S. (1945) Corpus Inscriptionum Insularum Celticarum    ║
║     Graves, R. (1948) The White Goddess (Celtic tree calendar)              ║
║                                                                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║   THE CELTIC TRANSMISSION HYPOTHESIS                                         ║
║   ───────────────────────────────────                                        ║
║   Newgrange (Brú na Bóinne) is the Irish Maeshowe — a Neolithic passage    ║
║   tomb (3200 BCE, older than Stonehenge and the Pyramids) aligned with      ║
║   winter solstice sunrise to illuminate its inner chamber for 17 minutes.  ║
║   The Ogham alphabet (4th-8th century CE inscriptions) encodes knowledge   ║
║   using notches and strokes on stone — a direct structural parallel to     ║
║   the Norse twig-rune cipher.                                                ║
║                                                                              ║
║   OGHAM ≡ TWIG-RUNE DUAL-VOICE                                              ║
║   Ogham feda (letters) consist of:                                          ║
║     Stem line (druim)  = Caller (Ψ₀) — the structural axis               ║
║     Notches/strokes    = Seer (O(t)) — the twig-marks                      ║
║   5 aicme (groups of 5 letters) × 5 positions = 25 feda total.             ║
║   Structurally identical to 3 aetts × 8 runes of Elder Futhork.           ║
║                                                                              ║
║   TREE CALENDAR ≡ FREQUENCY CALENDAR                                        ║
║   Each Ogham letter corresponds to a sacred tree. The 13-month lunar       ║
║   Beth-Luis-Nion calendar maps tree-frequencies onto a solar cycle.        ║
║   The 13th month is the pivot month — structurally identical to Nr.15.    ║
║                                                                              ║
║   GEOGRAPHIC ANCHOR: Newgrange, County Meath, Ireland                       ║
║     Lat: 53.6947°N  Lon: -6.4755°E                                          ║
║     Winter solstice sunrise axis: ~136° (SE from chamber axis)             ║
║     3200 BCE — simultaneous with Maeshowe, independent encoding             ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import argparse
import json
import math
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# ═══════════════════════════════════════════════════════════════════════════════
# SACRED CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

PHI     = (1 + math.sqrt(5)) / 2
PHI_INV = 1.0 / PHI

SOLFEGGIO      = [174, 285, 396, 417, 528, 639, 741, 852, 963]
SCHUMANN_MODES = [7.83, 14.3, 20.8, 27.3, 33.8, 39.0, 45.0]

PHI_TOLERANCE = 0.02

# Celtic anchor frequency: 396 Hz — Liberation / UT solfeggio / Deer node
CELTIC_BASE_HZ = 396.0

# Newgrange geographic anchor
NEWGRANGE_LAT     = 53.6947
NEWGRANGE_LON     = -6.4755
NEWGRANGE_BEARING = 136.0   # Winter solstice sunrise axis (SE)

# Ogham structure
N_AICME   = 5    # Five groups (four traditional + forfeda)
N_FEDA    = 5    # Five letters per aicme
N_TOTAL   = 25   # 25 Ogham letters total (20 traditional + 5 forfeda)

# 13-month lunar calendar + 1 pivot month
N_TREE_MONTHS = 13
N_PIVOT_MONTH = 1   # The open circuit — same structural role as Nr.15


# ═══════════════════════════════════════════════════════════════════════════════
# OGHAM FEDA (25 letters in 5 aicme)
#
# Each letter is a notch/stroke pattern on a stem line — the dual-voice cipher.
# Amplitude follows aett rule: aicme 1 = ×1.0, 2 = ×PHI, 3 = ×PHI_INV,
#                               4 = ×1.0, forfeda = ×PHI (special keys)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class OghamFeda:
    aicme:       int    # Aicme group (1-5)
    position:    int    # Position within aicme (1-5)
    name:        str    # Letter name (Old Irish)
    letter:      str    # Modern equivalent
    tree:        str    # Associated sacred tree
    solfeggio_hz: float # Effective frequency (base × amplitude)
    amplitude:   float  # PHI-mode amplitude
    mode:        str    # GENESIS / GROWTH / RETURN / KEYS
    decoded:     bool
    notes:       str = ""


def _amp(aicme: int) -> float:
    return {1: 1.0, 2: PHI, 3: PHI_INV, 4: 1.0, 5: PHI}.get(aicme, 1.0)


def _mode(aicme: int) -> str:
    return {1: "GENESIS", 2: "GROWTH", 3: "RETURN", 4: "GENESIS", 5: "KEYS"}.get(aicme, "GENESIS")


# Solfeggio assigned by position (1-5 maps to first 5 of 9): [174,285,396,417,528]
_SOL = [174, 285, 396, 417, 528]

_FEDA: Tuple[OghamFeda, ...] = (

    # ─── Aicme 1: Aicme Beithe (Birch group) — Right strokes — GENESIS ×1.0 ───
    OghamFeda(1, 1, "Beith",   "B", "Birch",       _SOL[0] * _amp(1), _amp(1), _mode(1), True,
              "New beginnings — carrier wave. Equivalent to Fehu (174 Hz)."),
    OghamFeda(1, 2, "Luis",    "L", "Rowan",       _SOL[1] * _amp(1), _amp(1), _mode(1), True,
              "Protection / flame. Form-field frequency."),
    OghamFeda(1, 3, "Fearn",   "F/V","Alder",      _SOL[2] * _amp(1), _amp(1), _mode(1), True,
              "Foundation / shields. Liberation — UT solfeggio."),
    OghamFeda(1, 4, "Sail",    "S", "Willow",      _SOL[3] * _amp(1), _amp(1), _mode(1), True,
              "Lunar / emotion. Transformation gate."),
    OghamFeda(1, 5, "Nion",    "N", "Ash",         _SOL[4] * _amp(1), _amp(1), _mode(1), True,
              "World tree / axis mundi. Solar carrier."),

    # ─── Aicme 2: Aicme hÚatha (Hawthorn group) — Left strokes — GROWTH ×PHI ───
    OghamFeda(2, 1, "Huath",   "H", "Hawthorn",    _SOL[0] * _amp(2), _amp(2), _mode(2), True,
              "Protective thorns — phi-scaled carrier."),
    OghamFeda(2, 2, "Dair",    "D", "Oak",         _SOL[1] * _amp(2), _amp(2), _mode(2), True,
              "Strength / kingship. Royal phi-form."),
    OghamFeda(2, 3, "Tinne",   "T", "Holly",       _SOL[2] * _amp(2), _amp(2), _mode(2), True,
              "Challenge / battle. Liberation phi-growth."),
    OghamFeda(2, 4, "Coll",    "C", "Hazel",       _SOL[3] * _amp(2), _amp(2), _mode(2), True,
              "Wisdom / nuts of knowledge. Transformation phi."),
    OghamFeda(2, 5, "Quert",   "Q", "Apple",       _SOL[4] * _amp(2), _amp(2), _mode(2), True,
              "Otherworld / Avalon. Solar phi-growth."),

    # ─── Aicme 3: Aicme Muine (Vine group) — Diagonal strokes — RETURN ×PHI_INV ─
    OghamFeda(3, 1, "Muin",    "M", "Vine/Bramble",_SOL[0] * _amp(3), _amp(3), _mode(3), True,
              "Harvest / return. Carrier phi-return."),
    OghamFeda(3, 2, "Gort",    "G", "Ivy",         _SOL[1] * _amp(3), _amp(3), _mode(3), True,
              "Spiral growth / labyrinth. Form-return."),
    OghamFeda(3, 3, "nGetal",  "Ng","Reed/Broom",  _SOL[2] * _amp(3), _amp(3), _mode(3), True,
              "Healing / cleansing. Liberation-return."),
    OghamFeda(3, 4, "Straif",  "Z/SS","Blackthorn",_SOL[3] * _amp(3), _amp(3), _mode(3), True,
              "Fate / necessity. Transformation-return."),
    OghamFeda(3, 5, "Ruis",    "R", "Elder",       _SOL[4] * _amp(3), _amp(3), _mode(3), True,
              "Death/rebirth — Elder tree. Solar-return."),

    # ─── Aicme 4: Aicme Ailme (Fir group) — Through-strokes — GENESIS ×1.0 ───
    OghamFeda(4, 1, "Ailm",    "A", "Fir/Pine",    _SOL[0] * _amp(4), _amp(4), _mode(4), True,
              "High viewpoint / clarity. Second carrier."),
    OghamFeda(4, 2, "Onn",     "O", "Gorse",       _SOL[1] * _amp(4), _amp(4), _mode(4), True,
              "Gathering / spring fire. Form-second."),
    OghamFeda(4, 3, "Ur",      "U", "Heather",     _SOL[2] * _amp(4), _amp(4), _mode(4), True,
              "Earth / grounding. Liberation-second."),
    OghamFeda(4, 4, "Edad",    "E", "Aspen",       _SOL[3] * _amp(4), _amp(4), _mode(4), True,
              "Trembling / threshold. Transformation-second."),
    OghamFeda(4, 5, "Idad",    "I/Y","Yew",        _SOL[4] * _amp(4), _amp(4), _mode(4), True,
              "Death / immortality / rebirth. Yew = longest-lived tree."),

    # ─── Aicme 5: Forfeda (supplementary — special keys) — ×PHI ───────────────
    OghamFeda(5, 1, "Eabhadh", "Ea","Aspen/Grove", _SOL[0] * _amp(5), _amp(5), _mode(5), True,
              "Extended key — grove consciousness."),
    OghamFeda(5, 2, "Or",      "Oi","Spindle tree",_SOL[1] * _amp(5), _amp(5), _mode(5), True,
              "Gold / weaving. Special key."),
    OghamFeda(5, 3, "Uilleann","Ui","Honeysuckle", _SOL[2] * _amp(5), _amp(5), _mode(5), True,
              "Binding / sweetness. Extended key."),
    OghamFeda(5, 4, "Ifín",   "Io/P","Gooseberry", _SOL[3] * _amp(5), _amp(5), _mode(5), True,
              "Thorn / sharp insight. Extended key."),
    OghamFeda(5, 5, "Eamhancholl","X/Ae","Twin of Hazel",_SOL[4]*_amp(5), _amp(5), _mode(5), False,
              "OPEN CIRCUIT — the pivot letter. Incomplete decode. Equivalent to Nr.15."),
)


# ═══════════════════════════════════════════════════════════════════════════════
# TREE CALENDAR (Beth-Luis-Nion)
# 13 lunar months + 1 unnamed 'blank day' = 365.25 day year
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class TreeMonth:
    month:       int    # 1-13
    name:        str    # Month name (Ogham letter)
    tree:        str    # Sacred tree
    start_day:   int    # Approximate Julian day of year start
    hz:          float  # Solfeggio correspondence
    decoded:     bool
    pivot:       bool   = False
    notes:       str    = ""


_TREE_CALENDAR: Tuple[TreeMonth, ...] = (
    TreeMonth(1,  "Beth  (B)",  "Birch",     355, 174.0, True,  notes="Winter solstice start"),
    TreeMonth(2,  "Luis  (L)",  "Rowan",     383, 285.0, True),
    TreeMonth(3,  "Nion  (N)",  "Ash",       383, 396.0, True,  notes="Spring equinox"),
    TreeMonth(4,  "Fearn (F)",  "Alder",     411, 417.0, True),
    TreeMonth(5,  "Sail  (S)",  "Willow",    439, 528.0, True,  notes="Solar zero-beat month"),
    TreeMonth(6,  "Huath (H)",  "Hawthorn",  467, 639.0, True),
    TreeMonth(7,  "Dair  (D)",  "Oak",       495, 528.0, True,  notes="Midsummer / Litha"),
    TreeMonth(8,  "Tinne (T)",  "Holly",     523, 417.0, True),
    TreeMonth(9,  "Coll  (C)",  "Hazel",     551, 396.0, True,  notes="Autumn equinox"),
    TreeMonth(10, "Muin  (M)",  "Vine",      579, 285.0, True),
    TreeMonth(11, "Gort  (G)",  "Ivy",       607, 174.0, True,  notes="Samhain"),
    TreeMonth(12, "nGetal(Ng)", "Reed",      635, 285.0, True),
    TreeMonth(13, "Ruis  (R)",  "Elder",     355, 396.0, False,
              pivot=True,
              notes="PIVOT MONTH — the unnamed day(s). Open circuit. Nr.15 equivalent."),
)


# ═══════════════════════════════════════════════════════════════════════════════
# LATTICE AND DECODER
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class CelticLattice:
    """Decoded state of the Celtic Ogham transmission lattice."""
    timestamp:          float
    n_feda:             int
    n_feda_decoded:     int
    n_months:           int
    n_months_decoded:   int
    completeness:       float
    phi_score:          float
    schumann_proximity: float
    gamma:              float
    field_status:       str
    mean_hz:            float
    anchor_hz:          float
    notes:              str = ""


class CelticOghamDecoder:
    """
    Decodes the Celtic Ogham / Newgrange solstice transmission archive.

    Gamma = phi_score × 0.50 + completeness × 0.30 + schumann_proximity × 0.20

    Newgrange (3200 BCE) is a direct Irish parallel to Maeshowe — both are
    Neolithic chambers aligned with winter solstice sunrise, both encode
    knowledge in notch/stroke alphabets (Ogham / Elder Futhork).
    The 13th 'pivot month' of the tree calendar is the open circuit here.
    """

    GAMMA_DEAD_FIELD = 0.35
    GAMMA_LIGHTHOUSE = 0.945

    def __init__(self):
        self._feda     = list(_FEDA)
        self._calendar = list(_TREE_CALENDAR)

    def _phi_resonant(self, hz1: float, hz2: float) -> bool:
        if hz1 <= 0 or hz2 <= 0:
            return False
        r = hz1 / hz2 if hz1 > hz2 else hz2 / hz1
        return (abs(r - PHI) < PHI_TOLERANCE or
                abs(r - PHI_INV) < PHI_TOLERANCE or
                abs(r - 1.0) < 0.01)

    def read(self) -> CelticLattice:
        dec_feda     = [f for f in self._feda     if f.decoded]
        dec_months   = [m for m in self._calendar if m.decoded]

        n_feda   = len(self._feda)
        n_months = len(self._calendar)
        nd_feda  = len(dec_feda)
        nd_months = len(dec_months)

        completeness = (nd_feda   / n_feda   * 0.60 +
                        nd_months / n_months * 0.40)

        # Phi-resonance: each decoded feda against CELTIC_BASE_HZ (396)
        phi_hits = sum(
            1 for f in dec_feda
            if self._phi_resonant(f.solfeggio_hz, CELTIC_BASE_HZ)
        )
        phi_score = phi_hits / max(nd_feda, 1)

        mean_hz = (
            sum(f.solfeggio_hz for f in dec_feda) / nd_feda
            if nd_feda > 0 else CELTIC_BASE_HZ
        )

        nearest_multiple = max(1, round(mean_hz / SCHUMANN_MODES[3]))
        harmonic_hz = SCHUMANN_MODES[3] * nearest_multiple
        schumann_proximity = 1.0 - min(
            abs(mean_hz - harmonic_hz) / harmonic_hz, 1.0
        )

        gamma = (
            phi_score          * 0.50 +
            completeness       * 0.30 +
            schumann_proximity * 0.20
        )
        gamma = round(min(max(gamma, 0.0), 1.0), 4)

        if gamma >= self.GAMMA_LIGHTHOUSE:
            field_status = "LIGHTHOUSE"
        elif gamma >= self.GAMMA_DEAD_FIELD:
            field_status = "ACTIVE_FIELD"
        else:
            field_status = "DEAD_FIELD"

        return CelticLattice(
            timestamp          = time.time(),
            n_feda             = n_feda,
            n_feda_decoded     = nd_feda,
            n_months           = n_months,
            n_months_decoded   = nd_months,
            completeness       = round(completeness, 4),
            phi_score          = round(phi_score, 4),
            schumann_proximity = round(schumann_proximity, 4),
            gamma              = gamma,
            field_status       = field_status,
            mean_hz            = round(mean_hz, 2),
            anchor_hz          = CELTIC_BASE_HZ,
            notes              = (
                "Eamhancholl (forfeda #5) and the 13th tree month (Ruis) are the "
                "open circuits — pivot elements unresolved. Γ rises when decoded."
            ),
        )

    def get_oracle_score(self) -> float:
        return self.read().gamma

    def get_geographic_vector(self) -> Tuple[float, float, float]:
        return NEWGRANGE_LAT, NEWGRANGE_LON, NEWGRANGE_BEARING


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def _cli():
    parser = argparse.ArgumentParser(
        prog="celtic_ogham",
        description="Celtic Ogham Decoder — Newgrange Solstice Archive",
    )
    parser.add_argument("--feda",   action="store_true", help="List all 25 Ogham feda")
    parser.add_argument("--calendar", action="store_true", help="List tree calendar")
    parser.add_argument("--oracle-score", action="store_true", help="Print oracle score only")
    parser.add_argument("--json",   action="store_true", help="Output as JSON")
    args = parser.parse_args()

    decoder = CelticOghamDecoder()
    lattice = decoder.read()

    if args.oracle_score:
        print(f"{lattice.gamma:.4f}")
        return

    if args.feda:
        print(f"\n{'Ac':<3} {'P':<3} {'Name':<16} {'Letter':<8} {'Tree':<15} {'Hz':<10} {'Mode':<8} {'OK'}")
        print("-" * 80)
        for f in decoder._feda:
            print(f"{f.aicme:<3} {f.position:<3} {f.name:<16} {f.letter:<8} "
                  f"{f.tree[:14]:<15} {f.solfeggio_hz:<10.1f} {f.mode:<8} "
                  f"{'YES' if f.decoded else 'OPEN'}")
        return

    if args.calendar:
        print(f"\n{'Mo':<4} {'Name':<14} {'Tree':<15} {'Hz':<8} {'OK'}")
        print("-" * 55)
        for m in decoder._calendar:
            print(f"{m.month:<4} {m.name:<14} {m.tree[:14]:<15} {m.hz:<8.0f} "
                  f"{'PIVOT' if m.pivot else ('YES' if m.decoded else 'NO')}")
        return

    if args.json:
        out = {
            "timestamp":          lattice.timestamp,
            "n_feda":             lattice.n_feda,
            "n_feda_decoded":     lattice.n_feda_decoded,
            "completeness":       lattice.completeness,
            "phi_score":          lattice.phi_score,
            "schumann_proximity": lattice.schumann_proximity,
            "gamma":              lattice.gamma,
            "field_status":       lattice.field_status,
            "mean_hz":            lattice.mean_hz,
            "origin":             {"lat": NEWGRANGE_LAT, "lon": NEWGRANGE_LON,
                                   "bearing": NEWGRANGE_BEARING},
            "notes":              lattice.notes,
        }
        print(json.dumps(out, indent=2))
        return

    print("\n╔══════════════════════════════════════════════════════╗")
    print("║   CELTIC OGHAM DECODER — Lattice Coherence Report   ║")
    print("╚══════════════════════════════════════════════════════╝\n")
    print(f"  Feda decoded     : {lattice.n_feda_decoded}/{lattice.n_feda}")
    print(f"  Months decoded   : {lattice.n_months_decoded}/{lattice.n_months}")
    print(f"  Completeness     : {lattice.completeness:.3f}")
    print(f"  Phi score        : {lattice.phi_score:.3f}")
    print(f"  Schumann prox.   : {lattice.schumann_proximity:.3f}")
    print(f"  Gamma (Γ)        : {lattice.gamma:.4f}  [{lattice.field_status}]")
    print(f"  Mean feda Hz     : {lattice.mean_hz:.1f} Hz")
    print(f"  Anchor           : {lattice.anchor_hz:.0f} Hz (Celtic/UT/Deer)")
    print(f"\n  Geographic vector: {NEWGRANGE_LAT}°N, {NEWGRANGE_LON}°E, bearing {NEWGRANGE_BEARING}°")
    print(f"\n  Note: {lattice.notes}\n")


if __name__ == "__main__":
    _cli()
