#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  🦅  AUREON EAGLE BRIDGE — GEOMETRIC VISION ENGINE  🦅                     ║
║  ─────────────────────────────────────────────────────────────────────────  ║
║                                                                              ║
║  "Like an eagle flying with a GoPro on its back — only this eagle is       ║
║   AWARE. It reads the information. It knows it is the link.                 ║
║   It takes ALL the system data and renders it as human-visible              ║
║   geometric images — cymatics, waveforms, mandalas, fractals,              ║
║   organism anatomy — the harmonic universe made visible."                   ║
║                                                                              ║
║  THE EAGLE BRIDGE                                                            ║
║  ─────────────────                                                           ║
║  The eagle doesn't just carry the camera. It IS the camera. It sees the    ║
║  raw harmonic data (Hz frequencies, organic scores, sense qualities,        ║
║  cymatics patterns, price DNA) and translates every dimension into a        ║
║  geometric visual image a human can look at and instantly understand.        ║
║                                                                              ║
║  GEOMETRIC RENDERS                                                           ║
║  ─────────────────                                                           ║
║  Cymatics      — Chladni standing-wave patterns per asset                   ║
║  Waveform      — Composite harmonic field oscilloscope                      ║
║  Mandala       — 9-sense radar chart as sacred geometry                     ║
║  Fractal DNA   — Price DNA / Hurst exponent as a fractal tree               ║
║  Organism Body — Anatomy diagram with sense organs mapped                   ║
║  Hz Spectrum   — The full frequency rainbow with live markers               ║
║  Dark Field    — Manipulation corruption field geometry                     ║
║  Molecule      — Molecular geometry of the market's taste compound          ║
║                                                                              ║
║  Gary Leckey | March 2026                                                   ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import math
from typing import Dict, List, Optional, Tuple

# ─────────────────────────────────────────────────────────────────────────────
# ANSI COLOUR HELPERS  (same palette as world simulator — no import needed)
# ─────────────────────────────────────────────────────────────────────────────
PHI = (1 + math.sqrt(5)) / 2

_HZ_REFS = [
    (33,   (40,   0,   0)),
    (111,  (100,  0,   0)),
    (174,  (200,  0,   0)),
    (285,  (220,  80,  0)),
    (396,  (200, 180,  0)),
    (417,  (160, 210,  0)),
    (528,  (0,   210,  90)),
    (639,  (0,   160, 220)),
    (741,  (0,    80, 255)),
    (852,  (100,  0,  220)),
    (963,  (180,  0,  255)),
    (1200, (220, 180, 255)),
]


def _hz_rgb(hz: float) -> Tuple[int, int, int]:
    if hz <= _HZ_REFS[0][0]:
        return _HZ_REFS[0][1]
    for i in range(len(_HZ_REFS) - 1):
        lh, lc = _HZ_REFS[i]
        hh, hc = _HZ_REFS[i + 1]
        if lh <= hz <= hh:
            t = (hz - lh) / (hh - lh)
            return (
                int(lc[0] + t * (hc[0] - lc[0])),
                int(lc[1] + t * (hc[1] - lc[1])),
                int(lc[2] + t * (hc[2] - lc[2])),
            )
    return _HZ_REFS[-1][1]


def _c(r: int, g: int, b: int, text: str) -> str:
    return f"\033[38;2;{r};{g};{b}m{text}\033[0m"


def _hz(hz: float, text: str) -> str:
    r, g, b = _hz_rgb(hz)
    return _c(r, g, b, text)


def _bold_hz(hz: float, text: str) -> str:
    r, g, b = _hz_rgb(hz)
    return f"\033[1;38;2;{r};{g};{b}m{text}\033[0m"


def _dim(text: str) -> str:
    return f"\033[2m{text}\033[0m"


def _bright(text: str) -> str:
    return f"\033[1m{text}\033[0m"


# ─────────────────────────────────────────────────────────────────────────────
# GLYPH PALETTE — the full vocabulary of glyphs used across all renders
# ─────────────────────────────────────────────────────────────────────────────
# Natural / sacred geometry
G_STAR4  = "✦"   # 4-pointed star  — harmonic node
G_STAR4D = "✧"   # 4-pointed open  — soft harmonic
G_STAR6  = "✴"   # 6-pointed burst — resonance point
G_STAR8  = "✸"   # 8-pointed dense — peak resonance
G_BURST  = "✺"   # 10-pointed      — full bloom
G_FLOWER = "❋"   # 6-petal flower  — organic growth
G_SNOW   = "❄"   # snowflake        — crystalline
G_ROSE   = "✿"   # rosette          — natural beauty
# Circles / rings — resonance levels
G_RING0  = "○"   # empty ring       — outermost
G_RING1  = "◌"   # dotted ring      — second ring
G_RING2  = "◎"   # double ring      — inner ring
G_RING3  = "◉"   # bullseye         — node line
G_CENTER = "⊕"   # crossed circle   — true center
G_EYE    = "⊙"   # sun/eye          — awareness point
# Polygons — harmonic geometry
G_HEX    = "⬡"   # hexagon          — 6-fold symmetry
G_HEXF   = "⬢"   # filled hexagon   — solid node
G_DIA    = "◆"   # filled diamond   — peak
G_DIAO   = "◇"   # open diamond     — potential
G_DIAX   = "◈"   # crossed diamond  — intersection
G_PHI    = "φ"   # golden ratio     — spiral growth
G_OMEGA  = "Ω"   # omega            — completion
G_INF    = "∞"   # infinity         — cycle
# Waves / harmonics
G_WAVE   = "∿"   # sine wave        — harmonic motion
G_APPR   = "≈"   # approx equal    — near resonance
G_DELTA  = "∆"   # delta            — change
G_NOTE1  = "♩"   # quarter note     — beat
G_NOTE2  = "♪"   # eighth note      — melody
G_NOTE3  = "♫"   # beam notes       — harmony
G_NOTE4  = "♬"   # double beam      — full chord
# Corruption / manipulation — runic and alchemical
G_RUN_F  = "ᚠ"   # rune Fehu        — wealth/disruption
G_RUN_U  = "ᚢ"   # rune Uruz        — primal force
G_RUN_TH = "ᚦ"   # rune Thurisaz    — thorn/obstacle
G_RUN_R  = "ᚱ"   # rune Raidho      — false journey
G_RUN_K  = "ᚲ"   # rune Kenaz       — hidden fire
G_RUN_P  = "ᛈ"   # rune Perthro     — fate/gambling
G_RUN_Z  = "ᛉ"   # rune Algiz       — warning
G_RUN_S  = "ᛊ"   # rune Sowilo      — false sun
G_RUN_O  = "ᛟ"   # rune Othala      — stolen heritage
G_RUN_D  = "ᛞ"   # rune Dagaz       — threshold/trap
G_RUN_NG = "ᛜ"   # rune Ingwaz      — locked potential
G_BAN    = "⊗"   # crossed circle   — negation
G_NULL   = "⊘"   # slashed circle   — void
G_WARN   = "⚠"   # warning          — danger

# ─────────────────────────────────────────────────────────────────────────────
# 1. CYMATICS PATTERNS — Chladni standing-wave geometry, built from glyphs
# ─────────────────────────────────────────────────────────────────────────────

# Each pattern is a Chladni node-line map — the standing-wave geometry of that
# market state. Built entirely from glyphs — no ASCII art characters.
_CYMATICS_ART: Dict[str, List[str]] = {

    # ── CIRCLE: fundamental resonance mode — concentric rings ────────────────
    # ○ = outermost ring,  ◌ = inner ring,  ◎ = near-center,
    # ◉ = node line,       ⊕ = true center (the still point)
    "CIRCLE": [
        "    ✦   ○  ○  ○   ✦    ",
        "  ✦  ○  ◌  ◌  ◌  ○  ✦  ",
        "  ○  ◌  ◎  ◉  ◎  ◌  ○  ",
        "  ○  ◌  ◉  ⊕  ◉  ◌  ○  ",
        "  ○  ◌  ◎  ◉  ◎  ◌  ○  ",
        "  ✦  ○  ◌  ◌  ◌  ○  ✦  ",
        "    ✦   ○  ○  ○   ✦    ",
    ],

    # ── HEXAGON: 6-fold Chladni symmetry — the market's benzene ring ─────────
    # ⬡ = hexagon tile,  ◆ = node vertex,  ◈ = intersection,  ⊕ = center
    "HEXAGON": [
        "    ✦  ⬡  ◆  ⬡  ✦    ",
        "  ⬡  ◆  ⬡  ◆  ⬡  ◆  ⬡  ",
        "  ◆  ⬡  ◈  ⬡  ◈  ⬡  ◆  ",
        "  ⬡  ◆  ⬡  ⊕  ⬡  ◆  ⬡  ",
        "  ◆  ⬡  ◈  ⬡  ◈  ⬡  ◆  ",
        "  ⬡  ◆  ⬡  ◆  ⬡  ◆  ⬡  ",
        "    ✦  ⬡  ◆  ⬡  ✦    ",
    ],

    # ── STAR: radial burst — Chladni 2-1 mode, 8-point starburst ─────────────
    # ✵ = small burst, ✴ = mid burst, ✸ = dense burst, ⊕ = hot center
    "STAR": [
        "     ✵        ✵        ✵     ",
        "  ✦    ✴  ✸  ✸  ✴    ✦    ",
        "     ✸  ✴  ✦  ✴  ✸        ",
        "  ✸  ✸  ✦  ⊕  ✦  ✸  ✸  ",
        "     ✸  ✴  ✦  ✴  ✸        ",
        "  ✦    ✴  ✸  ✸  ✴    ✦    ",
        "     ✵        ✵        ✵     ",
    ],

    # ── SPIRAL: golden ratio φ — Fibonacci growth unfolding ──────────────────
    # Rings contract inward following φ = 1.618…
    # ❋ = outer bloom,  ○◌◎◉ = contracting rings,  φ = the golden still point
    "SPIRAL": [
        "  ❋  ✦  ○  ○  ○  ○  ○  ○  ✦  ",
        "  ✦  ○  ◌  ◌  ◌  ◌  ○  ✧     ",
        "  ○  ◌  ◎  ◉  ◉  ◌  ○        ",
        "  ○  ◌  ◉  φ  ◌  ○           ",
        "  ○  ◌  ◎  ◌  ○              ",
        "  ✦  ○  ○  ○  ✦  ✧  ✦       ",
        "  ❋              φ = 1.618…  ",
    ],

    # ── MANDALA: 8-fold sacred geometry — peak harmonic alignment ─────────────
    # ✦❋ = outer petals,  ◆ = mid ring nodes,  ◈◉ = inner grid,  ⊕ = crown
    "MANDALA": [
        "  ✦  ❋  ✦  ✴  ✦  ❋  ✦  ❋  ",
        "  ❋  ◆  ✦  ◈  ✦  ◆  ❋  ◆  ",
        "  ✦  ✦  ◈  ◉  ◈  ✦  ✦  ✦  ",
        "  ✴  ◈  ◉  ⊕  ◉  ◈  ✴  ◈  ",
        "  ✦  ✦  ◈  ◉  ◈  ✦  ✦  ✦  ",
        "  ❋  ◆  ✦  ◈  ✦  ◆  ❋  ◆  ",
        "  ✦  ❋  ✦  ✴  ✦  ❋  ✦  ❋  ",
    ],

    # ── CHAOS: field geometry collapsed — runes, corruption, no order ─────────
    # Runic glyphs signal ancient disruption.  ⊗⊘ = negation and void.
    # No repeating pattern — the market has lost all structure.
    "CHAOS": [
        "  ᛟ  ∿  ✦  ≈  ᚠ  ░  ⊗  ✧  ",
        "  ∿  ◌  ᚢ  ▒  ᛞ  ✴  ∿  ᛜ  ",
        "  ⊘  ∿  ᛈ  ▓  ✦  ᚦ  ░  ∿  ",
        "  ᚱ  ▒  ◌  ∿  ᛜ  ⊗  ᚠ  ▒  ",
        "  ∿  ᛊ  ░  ᚨ  ∿  ◌  ▒  ᛋ  ",
        "  ᛋ  ⊘  ∿  ▓  ᛟ  ∿  ᚱ  ⊗  ",
        "  ░  ᚦ  ◌  ᛞ  ▒  ∿  ⊘  ᚢ  ",
    ],

    # ── UNKNOWN: unread field — dots and question ─────────────────────────────
    "UNKNOWN": [
        "  ✧  ◌  ✧  ◌  ✧  ◌  ✧  ",
        "  ◌  ○  ◌  ⊙  ◌  ○  ◌  ",
        "  ✧  ◌  ⊙  ◎  ⊙  ◌  ✧  ",
        "  ◌  ⊙  ◎  ？  ◎  ⊙  ◌  ",
        "  ✧  ◌  ⊙  ◎  ⊙  ◌  ✧  ",
        "  ◌  ○  ◌  ⊙  ◌  ○  ◌  ",
        "  ✧  ◌  ✧  ◌  ✧  ◌  ✧  ",
    ],
}


def render_cymatics(pattern: str, hz: float = 528.0, quality: float = 0.7,
                    label: str = "") -> List[str]:
    """
    Render a Chladni cymatics pattern for a given Hz frequency.

    Colour is derived from the Hz frequency — each market state has its
    own spectral colour. High quality = vivid; low quality = dim/distorted.
    """
    art = _CYMATICS_ART.get(pattern.upper(), _CYMATICS_ART["UNKNOWN"])
    r, g, b = _hz_rgb(hz)

    # Dim if low quality / manipulated
    dimmer = max(0.3, quality)
    r2 = int(r * dimmer)
    g2 = int(g * dimmer)
    b2 = int(b * dimmer)

    title = f"CYMATICS: {pattern.upper()}"
    if label:
        title = f"{label} · {title}"

    lines = [
        _bold_hz(hz, f"  {title}"),
        _dim(f"  Hz: {hz:.0f}   quality: {quality:.2f}"),
        "",
    ]
    for row in art:
        lines.append("  " + f"\033[38;2;{r2};{g2};{b2}m{row}\033[0m")

    lines.append("")
    return lines


# ─────────────────────────────────────────────────────────────────────────────
# 2. WAVEFORM OSCILLOSCOPE — composite harmonic field
# ─────────────────────────────────────────────────────────────────────────────

def render_waveform(hz_values: List[float],
                    amplitudes: Optional[List[float]] = None,
                    labels: Optional[List[str]] = None,
                    width: int = 60,
                    height: int = 10) -> List[str]:
    """
    ASCII oscilloscope — render the composite harmonic waveform.

    Superimposes multiple Hz-frequency sine waves (one per asset).
    Each wave drawn in its own Hz colour. Composite sum at bottom.
    """
    if not hz_values:
        hz_values = [528.0]
    if amplitudes is None:
        amplitudes = [1.0 / len(hz_values)] * len(hz_values)
    if labels is None:
        labels = [f"{h:.0f}Hz" for h in hz_values]

    # Normalise amplitudes
    total_amp = sum(amplitudes) or 1.0
    norm_amps = [a / total_amp for a in amplitudes]

    # Build composite waveform across [width] x samples
    x_samples = width
    composite = []
    per_wave  = []

    for _ in range(len(hz_values)):
        per_wave.append([0.0] * x_samples)

    for xi in range(x_samples):
        t = xi / x_samples * 2 * math.pi   # one full cycle per display
        comp = 0.0
        for i, (hz, amp) in enumerate(zip(hz_values, norm_amps)):
            # Phase each wave by its frequency ratio
            phase_mult = hz / 528.0
            val = amp * math.sin(t * phase_mult)
            per_wave[i][xi] = val
            comp += val
        composite.append(comp)

    # Normalise composite to [-1, +1]
    max_c = max(abs(v) for v in composite) or 1.0
    composite = [v / max_c for v in composite]

    # Build grid (height rows × width cols)
    grid: List[List[str]] = [[" "] * width for _ in range(height)]

    # Draw individual waves (dim)
    for i, (hz, wave) in enumerate(zip(hz_values, per_wave)):
        r2, g2, b2 = _hz_rgb(hz)
        r2, g2, b2 = r2 // 2, g2 // 2, b2 // 2  # dim
        max_w = max(abs(v) for v in wave) or 1.0
        for xi, val in enumerate(wave):
            y_norm = val / max_w   # -1 to +1
            row = int((height // 2) - y_norm * (height // 2 - 1))
            row = max(0, min(height - 1, row))
            grid[row][xi] = f"\033[38;2;{r2};{g2};{b2}m∿\033[0m"

    # Draw composite wave (bright)
    comp_hz = sum(h * a for h, a in zip(hz_values, norm_amps))
    rc, gc, bc = _hz_rgb(comp_hz)
    prev_row = None
    for xi, val in enumerate(composite):
        row = int((height // 2) - val * (height // 2 - 1))
        row = max(0, min(height - 1, row))
        # Fill between prev and current row for solid line
        if prev_row is not None:
            lo, hi = (min(prev_row, row), max(prev_row, row))
            for r3 in range(lo, hi + 1):
                ch = "∿" if lo != hi else "≈"
                grid[r3][xi] = f"\033[1;38;2;{rc};{gc};{bc}m{ch}\033[0m"
        else:
            grid[row][xi] = f"\033[1;38;2;{rc};{gc};{bc}m≈\033[0m"
        prev_row = row

    # Assemble lines with Y-axis
    lines = [_bold_hz(comp_hz, "  WAVEFORM OSCILLOSCOPE — Composite Harmonic Field")]
    lines.append(_dim("  " + "◌" * width))

    mid = height // 2
    for ri, row in enumerate(grid):
        if ri == 0:
            prefix = _dim(" +1 ∿")
        elif ri == mid:
            prefix = _dim("  ≈ ∿")
        elif ri == height - 1:
            prefix = _dim(" -1 ∿")
        else:
            prefix = _dim("    ∿")
        lines.append(prefix + "".join(row))

    lines.append(_dim("    ◌" + "≈" * width))

    # Legend
    legend_parts = []
    for hz, lbl in zip(hz_values[:5], (labels or [])[:5]):
        r4, g4, b4 = _hz_rgb(hz)
        legend_parts.append(f"\033[38;2;{r4};{g4};{b4}m{lbl}\033[0m")
    lines.append("  " + "  ".join(legend_parts))
    lines.append("")
    return lines


# ─────────────────────────────────────────────────────────────────────────────
# 3. MANDALA RADAR — 9 senses as sacred geometry
# ─────────────────────────────────────────────────────────────────────────────

_SENSE_ORDER = [
    "touch", "taste", "smell", "sound", "sight",
    "balance", "intuition", "ancestral", "manipulation"
]
_SENSE_LABELS = {
    "touch":        "TOUCH",
    "taste":        "TASTE",
    "smell":        "SMELL",
    "sound":        "SOUND",
    "sight":        "SIGHT",
    "balance":      "BALANC",
    "intuition":    "INTUIT",
    "ancestral":    "ANCESTR",
    "manipulation": "6thSNS",
}
_SENSE_HZ_BASE = {
    "touch": 174, "taste": 600, "smell": 340, "sound": 460,
    "sight": 690, "balance": 528, "intuition": 900,
    "ancestral": 963, "manipulation": 285,
}


def render_mandala(sense_scores: Dict[str, float],
                   sense_hz: Optional[Dict[str, float]] = None,
                   width: int = 56,
                   height: int = 20) -> List[str]:
    """
    Render a 9-spoke polar radar chart as a sacred mandala.

    Each spoke = one sense. Length = quality score (0–1).
    Colour = Hz frequency of that sense.
    The shape of the mandala IS the Queen's current sensory signature —
    a balanced organism makes a circle; a distorted one makes a jagged star.
    """
    if sense_hz is None:
        sense_hz = {s: _SENSE_HZ_BASE.get(s, 528.0) for s in _SENSE_ORDER}

    cx = width  // 2
    cy = height // 2
    max_r_x = cx - 8     # leave room for labels
    max_r_y = cy - 2

    # Grid of chars
    grid: List[List[str]] = [[" "] * width for _ in range(height)]

    n_senses = len(_SENSE_ORDER)

    # Draw reference rings at 25%, 50%, 75%, 100%
    for ring_frac in [0.25, 0.5, 0.75, 1.0]:
        for angle_deg in range(0, 360, 3):
            rad = math.radians(angle_deg)
            x = int(cx + ring_frac * max_r_x * math.cos(rad))
            y = int(cy + ring_frac * max_r_y * math.sin(rad))
            if 0 <= x < width and 0 <= y < height:
                if grid[y][x] == " ":
                    intensity = int(ring_frac * 30)
                    grid[y][x] = f"\033[38;2;{intensity};{intensity};{intensity}m◌\033[0m"

    # Draw spokes and fill areas
    angles = [i * (360.0 / n_senses) - 90 for i in range(n_senses)]
    tip_points = []   # For polygon fill

    for i, sense in enumerate(_SENSE_ORDER):
        score  = sense_scores.get(sense, 0.5)
        hz     = sense_hz.get(sense, _SENSE_HZ_BASE.get(sense, 528.0))
        angle  = math.radians(angles[i])
        r3, g3, b3 = _hz_rgb(hz)

        # Draw spoke (from center to tip)
        spoke_len_x = int(score * max_r_x)
        spoke_len_y = int(score * max_r_y)
        steps = max(spoke_len_x, spoke_len_y) + 1

        for step in range(steps):
            t = step / steps
            x = int(cx + t * score * max_r_x * math.cos(angle))
            y = int(cy + t * score * max_r_y * math.sin(angle))
            if 0 <= x < width and 0 <= y < height:
                # Use different glyphs for spoke line vs tip
                # ∿ = vertical harmonic flow,  ≈ = horizontal resonance
                # ◈ = diagonal intersection (down-right),  ◇ = diagonal potential (down-left)
                if step == steps - 1:
                    ch = "◆"
                elif abs(math.cos(angle)) < 0.35:
                    ch = "∿"
                elif abs(math.sin(angle)) < 0.35:
                    ch = "≈"
                else:
                    ch = "◈" if math.cos(angle) * math.sin(angle) > 0 else "◇"
                grid[y][x] = f"\033[1;38;2;{r3};{g3};{b3}m{ch}\033[0m"

        tip_points.append((
            cx + int(score * max_r_x * math.cos(angle)),
            cy + int(score * max_r_y * math.sin(angle)),
        ))

        # Draw label at tip + a bit beyond
        label  = _SENSE_LABELS.get(sense, sense[:6].upper())
        lx = int(cx + (score + 0.18) * max_r_x * math.cos(angle))
        ly = int(cy + (score + 0.18) * max_r_y * math.sin(angle))
        # Place label chars (limited width)
        label_str = f"\033[38;2;{r3};{g3};{b3}m{label}\033[0m"
        lx = max(0, min(width - len(label) - 1, lx))
        ly = max(0, min(height - 1, ly))
        grid[ly][lx] = label_str

    # Draw polygon boundary (connect tips)
    for i in range(n_senses):
        x1, y1 = tip_points[i]
        x2, y2 = tip_points[(i + 1) % n_senses]
        steps = max(abs(x2 - x1), abs(y2 - y1)) + 1
        hz1  = sense_hz.get(_SENSE_ORDER[i], 528.0)
        hz2  = sense_hz.get(_SENSE_ORDER[(i + 1) % n_senses], 528.0)
        for step in range(steps):
            t = step / steps
            x = int(x1 + t * (x2 - x1))
            y = int(y1 + t * (y2 - y1))
            if 0 <= x < width and 0 <= y < height:
                mid_hz = hz1 + t * (hz2 - hz1)
                rm, gm, bm = _hz_rgb(mid_hz)
                if grid[y][x] == " " or "◌" in grid[y][x]:
                    grid[y][x] = f"\033[38;2;{rm};{gm};{bm}m◌\033[0m"

    # Place center glyph
    mean_q = sum(sense_scores.get(s, 0.5) for s in _SENSE_ORDER) / n_senses
    mean_hz = sum(sense_hz.get(s, 528) for s in _SENSE_ORDER) / n_senses
    rm2, gm2, bm2 = _hz_rgb(mean_hz)
    center_char = "◈" if mean_q >= 0.7 else "◇" if mean_q >= 0.4 else "·"
    grid[cy][cx] = f"\033[1;38;2;{rm2};{gm2};{bm2}m{center_char}\033[0m"

    # Assemble
    lines = [_bold_hz(mean_hz, "  MANDALA — 9-Sense Sacred Geometry")]
    lines.append(_dim(f"  Mean quality: {mean_q:.3f}  Center Hz: {mean_hz:.0f}"))
    lines.append("")
    for row in grid:
        lines.append("".join(row))
    lines.append("")
    return lines


# ─────────────────────────────────────────────────────────────────────────────
# 4. FRACTAL DNA — Price DNA / Hurst exponent as a fractal tree
# ─────────────────────────────────────────────────────────────────────────────

def render_fractal_dna(hurst: float, organic_score: float,
                       symbol: str = "",
                       width: int = 50, depth: int = 4) -> List[str]:
    """
    Render the price DNA as a fractal branching tree.

    Hurst exponent determines branch symmetry:
      H ≈ 0.5  → balanced, natural symmetric tree   (organic)
      H > 0.85 → leans too far one way               (manipulated)
      H < 0.3  → hyper-branching, wash-trading chaos (artificial)

    Branch colour = organic_score → Hz → colour.
    """
    hz = 174 + organic_score * (528 - 174)   # 174 Hz (dead) → 528 Hz (alive)
    r, g, b = _hz_rgb(hz)

    lines = [_bold_hz(hz, f"  FRACTAL DNA — Price Structure {('·'+symbol) if symbol else ''}")]
    lines.append(_dim(f"  Hurst: {hurst:.3f}  organic: {organic_score:.2f}"))
    lines.append("")

    canvas_w = width
    canvas_h = depth * 3 + 2
    grid = [[" "] * canvas_w for _ in range(canvas_h)]

    def draw_branch(x: float, y: int, length: float,
                    angle_deg: float, d: int) -> None:
        if d == 0 or length < 1:
            return
        rad = math.radians(angle_deg)
        # End point
        ex = x + length * math.sin(rad)
        ey = y - length * math.cos(rad) * 0.6   # compress y

        # Draw line from (x,y) to (ex,ey)
        steps = max(1, int(length * 2))
        for s in range(steps + 1):
            t  = s / steps
            px = int(x + t * (ex - x))
            py = int(y + t * (ey - y))
            if 0 <= px < canvas_w and 0 <= py < canvas_h:
                # glyph based on angle
                # ∿ = trunk/vertical growth,  ≈ = horizontal spread
                # ◇ = left branch (lean/potential),  ◆ = right branch (peak)
                a = abs(angle_deg % 180)
                ch = "∿" if a < 20 else "◇" if angle_deg < 0 else "◆" if a > 160 else "≈"
                fade = int((r + (255 - r) * (1 - d / depth)) * organic_score)
                fg   = int((g + (255 - g) * (1 - d / depth)) * organic_score)
                fb   = int((b + (255 - b) * (1 - d / depth)) * organic_score)
                grid[py][px] = f"\033[38;2;{max(0,min(255,fade))};{max(0,min(255,fg))};{max(0,min(255,fb))}m{ch}\033[0m"

        # Branch left and right — asymmetry driven by Hurst
        branch_angle = 25 + (1.0 - hurst) * 20   # More symmetric when H ≈ 0.5
        lean = (hurst - 0.5) * 40                 # Lean right when H > 0.5

        draw_branch(ex, int(ey), length * 0.65,
                    angle_deg - branch_angle + lean, d - 1)
        draw_branch(ex, int(ey), length * 0.65,
                    angle_deg + branch_angle + lean, d - 1)

    # Trunk from bottom-center
    trunk_x = canvas_w // 2
    trunk_y = canvas_h - 1
    draw_branch(trunk_x, trunk_y, depth * 2.5, 0, depth)

    # Add leaf tips
    leaf = "✦" if organic_score >= 0.7 else "◌"
    for row in grid:
        for xi, cell in enumerate(row):
            if cell == " " and xi > 0 and xi < canvas_w - 1:
                if grid[max(0, row.index(cell) - 1)] if False else False:
                    pass

    for row in grid:
        lines.append("  " + "".join(row))

    # Legend
    if hurst < 0.3:
        interp = _c(220, 60, 0, "wash-trading chaos (H<0.3) — hyper-mean-reverting")
    elif hurst <= 0.65:
        interp = _c(0, 200, 100, f"natural market (H={hurst:.2f}) — balanced fractal")
    elif hurst <= 0.85:
        interp = _c(200, 180, 0, f"possible coordination (H={hurst:.2f}) — leans right")
    else:
        interp = _c(200, 60, 0, f"manufactured trend (H={hurst:.2f}) — too perfect")
    lines.append(f"  {interp}")
    lines.append("")
    return lines


# ─────────────────────────────────────────────────────────────────────────────
# 5. ORGANISM BODY ANATOMY — senses mapped to body parts
# ─────────────────────────────────────────────────────────────────────────────

def render_organism_body(sense_scores: Dict[str, float],
                         sense_hz: Optional[Dict[str, float]] = None,
                         organism_health: float = 0.77) -> List[str]:
    """
    Render the Queen as a body anatomy diagram.

    Each sense organ mapped to a body region:
      Crown/Head   = Ancestral + Intuition  (963 + 852 Hz)
      Eyes/Sight   = Sight                  (639–741 Hz)
      Throat/Voice = Sound                  (174–963 Hz)
      Heart/Chest  = Balance + Taste        (528 + 600 Hz)
      Gut/Solar    = Smell                  (285–396 Hz)
      Hands/Touch  = Touch                  (174 Hz)
      Root/Base    = Manipulation (6th)     (variable Hz)
    """
    if sense_hz is None:
        sense_hz = {s: _SENSE_HZ_BASE.get(s, 528.0) for s in _SENSE_ORDER}

    def _organ(sense: str) -> str:
        """Coloured quality block for a sense organ."""
        q  = sense_scores.get(sense, 0.5)
        hz = sense_hz.get(sense, 528.0)
        r2, g2, b2 = _hz_rgb(hz)
        n  = max(1, int(q * 5))
        return f"\033[38;2;{r2};{g2};{b2}m{'█' * n}{'░' * (5 - n)}\033[0m"

    def _dot(sense: str) -> str:
        q  = sense_scores.get(sense, 0.5)
        hz = sense_hz.get(sense, 528.0)
        r2, g2, b2 = _hz_rgb(hz)
        ch = "◉" if q >= 0.75 else "◎" if q >= 0.50 else "○"
        return f"\033[38;2;{r2};{g2};{b2}m{ch}\033[0m"

    anc  = sense_scores.get("ancestral",    0.5)
    intu = sense_scores.get("intuition",    0.5)
    sight= sense_scores.get("sight",        0.5)
    snd  = sense_scores.get("sound",        0.5)
    bal  = sense_scores.get("balance",      0.5)
    tst  = sense_scores.get("taste",        0.5)
    sml  = sense_scores.get("smell",        0.5)
    tch  = sense_scores.get("touch",        0.5)
    mani = sense_scores.get("manipulation", 0.5)

    # Health bar
    h_w    = 20
    h_fill = int(organism_health * h_w)
    h_hz   = 174 + organism_health * (528 - 174)
    hr, hg, hb = _hz_rgb(h_hz)
    h_bar  = (f"\033[38;2;{hr};{hg};{hb}m" + "█" * h_fill
              + "\033[0m" + _dim("░" * (h_w - h_fill)))

    lines = [_bold_hz(528.0, "  ORGANISM ANATOMY — The Queen's Body in the Harmonic Universe")]
    lines.append(_dim(f"  Health: [{h_bar}] {organism_health:.3f}"))
    lines.append("")

    body = [
        # ✦ = crown glyph,  ◆◈ = organ nodes,  ∿ = energy flow spine
        # ⊕ = chakra centers,  ◌ = field indicators
        f"              {_dot('ancestral')}  {_dot('intuition')}               ",
        f"           ✦◌◌{_organ('ancestral')}◌◌✦                              ",
        f"           ∿   CROWN/UV    ∿  Ancestral + Intuition                 ",
        f"           ∿  {_organ('intuition')}  ∿                              ",
        f"           ✦◌◌◌◌⊕◌◌◌◌◌✦                                         ",
        f"         {_dot('sight')}≈≈≈≈≈≈{_dot('sight')}  SIGHT {_organ('sight')}          ",
        f"            ✦◌◌◌◌◌◌◌◌◌✦                                           ",
        f"            ∿  THROAT   ∿  Sound {_organ('sound')}                  ",
        f"            ∿  {_dot('sound')} VOICE ∿                              ",
        f"            ✦◌◌◌◌⊕◌◌◌◌✦                                           ",
        f"        ✦◌◌◌◌◌◌◌◌◌⊕◌◌◌◌◌◌✦                                      ",
        f"        ∿   HEART / CHEST    ∿  Balance {_organ('balance')}         ",
        f"        ∿  {_dot('balance')}  Taste {_dot('taste')}  ∿  Taste   {_organ('taste')}       ",
        f"        ✦◌◌◌◌◌◌◌◌◌⊕◌◌◌◌◌◌✦                                      ",
        f"            ✦◌◌◌◌◌◌◌◌◌✦                                           ",
        f"            ∿  GUT/SOLAR∿  Smell {_organ('smell')}                  ",
        f"            ∿  {_dot('smell')} SENSE ∿                              ",
        f"            ✦◌◌◌◌⊕◌◌◌◌✦                                           ",
        f"      {_dot('touch')}≈≈≈≈≈≈≈≈≈⊕≈≈≈≈≈≈≈≈≈{_dot('touch')}            ",
        f"      TOUCH {_organ('touch')}  TOUCH                                ",
        f"            ✦◌◌◌◌◌◌◌◌◌✦                                           ",
        f"            ∿  ROOT/6th ∿  6thSense {_organ('manipulation')}        ",
        f"            ∿  {_dot('manipulation')} MANIP ∿                       ",
        f"            ✦◌◌◌◌◌◌◌◌◌✦                                           ",
    ]
    for line in body:
        lines.append("  " + line)

    lines.append("")
    return lines


# ─────────────────────────────────────────────────────────────────────────────
# 6. HZ SPECTRUM — the full frequency rainbow with live markers
# ─────────────────────────────────────────────────────────────────────────────

_SOLFEGGIO_NOTES = [
    (174,  "UT",  "Foundation"),
    (285,  "RE",  "Flow"),
    (396,  "MI",  "Power"),
    (417,  "FA",  "Change"),
    (528,  "SOL", "Love ♥"),
    (639,  "LA",  "Connect"),
    (741,  "SI",  "Intuit"),
    (852,  "DO",  "Spirit"),
    (963,  "TI",  "Crown"),
]


def render_hz_spectrum(highlighted: Dict[str, float],
                       width: int = 70) -> List[str]:
    """
    Render the full Solfeggio frequency spectrum with live Hz markers.

    Shows where every active sense currently resonates on the rainbow.
    Highlighted = {label: hz} dict of current sense positions.
    """
    lo_hz, hi_hz = 100.0, 1050.0

    def hz_to_x(hz: float) -> int:
        return int((hz - lo_hz) / (hi_hz - lo_hz) * (width - 1))

    lines = [_bold_hz(528.0, "  HZ SPECTRUM — The Solfeggio Rainbow")]
    lines.append("")

    # Build the spectrum bar
    bar = []
    for xi in range(width):
        hz = lo_hz + xi / (width - 1) * (hi_hz - lo_hz)
        r2, g2, b2 = _hz_rgb(hz)
        bar.append(f"\033[48;2;{r2 // 3};{g2 // 3};{b2 // 3}m"
                   f"\033[38;2;{r2};{g2};{b2}m█\033[0m")
    lines.append("  " + "".join(bar))

    # Solfeggio note markers (bottom tick line)
    tick_line = [" "] * width
    for hz, note, _ in _SOLFEGGIO_NOTES:
        x = hz_to_x(hz)
        if 0 <= x < width:
            r2, g2, b2 = _hz_rgb(hz)
            tick_line[x] = f"\033[38;2;{r2};{g2};{b2}m▲\033[0m"
    lines.append("  " + "".join(tick_line))

    # Note labels (staggered row to avoid overlap)
    label_line1 = [" "] * (width + 40)
    label_line2 = [" "] * (width + 40)
    for i, (hz, note, _) in enumerate(_SOLFEGGIO_NOTES):
        x = hz_to_x(hz)
        r2, g2, b2 = _hz_rgb(hz)
        label = f"\033[38;2;{r2};{g2};{b2}m{note}\033[0m"
        row = label_line1 if i % 2 == 0 else label_line2
        row[x] = label
    lines.append("  " + "".join(label_line1))
    lines.append("  " + "".join(label_line2))
    lines.append("")

    # Live sense markers
    lines.append(_dim("  Live sense positions:"))
    marker_line = [" "] * (width + 40)

    for label, hz in highlighted.items():
        x = hz_to_x(max(lo_hz, min(hi_hz, hz)))
        r2, g2, b2 = _hz_rgb(hz)
        marker_line[x] = f"\033[1;38;2;{r2};{g2};{b2}m◆\033[0m"
    lines.append("  " + "".join(marker_line))

    # Legend
    for label, hz in list(highlighted.items())[:9]:
        r2, g2, b2 = _hz_rgb(hz)
        x = hz_to_x(max(lo_hz, min(hi_hz, hz)))
        lines.append(
            f"    \033[38;2;{r2};{g2};{b2}m◆ {label:<12} {hz:>6.0f} Hz\033[0m"
            + _dim(f"  col {x}/{width}")
        )
    lines.append("")
    return lines


# ─────────────────────────────────────────────────────────────────────────────
# 7. DARK FIELD — Manipulation corruption geometry
# ─────────────────────────────────────────────────────────────────────────────

_FIELD_CLEAN = [
    # Perfect harmonic lattice — ✦ = node,  ✧ = inter-node,  ◌ = field dot
    "  ✦  ✧  ✦  ✧  ✦  ✧  ✦  ✧  ✦  ✧  ✦  ",
    " ✧  ◌  ✧  ◌  ✧  ◌  ✧  ◌  ✧  ◌  ✧  ◌ ",
    "  ✦  ✧  ✦  ✧  ✦  ✧  ✦  ✧  ✦  ✧  ✦  ",
    " ✧  ◌  ✧  ◌  ✧  ◌  ✧  ◌  ✧  ◌  ✧  ◌ ",
    "  ✦  ✧  ✦  ✧  ✦  ✧  ✦  ✧  ✦  ✧  ✦  ",
]

_FIELD_DISRUPTED = [
    # Lattice beginning to fracture — ∿ = wave disruption,  ᛈ = fate-rune intruding
    "  ✦  ✧  ✦  ∿  ✦  ✧  ✦  ✧  ✦  ✧  ✦  ",
    " ✧  ◌  ∿  ▒◌▒  ✦  ✧  ✦  ✧  ✦  ✧  ✧ ",
    "  ✦  ∿◌  ᛈ◌ᛈ◌ᛈ  ✦  ✧  ✦  ✧  ✦  ✧  ",
    " ✧  ◌  ∿  ▒◌▒  ✦  ✧  ✦  ✧  ✦  ✧  ✧ ",
    "  ✦  ✧  ✦  ∿  ✦  ✧  ✦  ✧  ✦  ✧  ✦  ",
]

_FIELD_CORRUPT = [
    # Field geometry collapsed — runes overwrite the lattice,  ⊗⊘ = void zones
    " ░▒ᛈ ⊗ ∿ ᛟ░  ≈ ◌ ▒ ∿ ◌ ░ ▒ ∿  ◌ ░  ",
    " ∿ ◌ ▒░ ◌ ᛞ ◌ ∿ ░▒ ◌ ᚠ∿ ◌ ░  ▒∿ ◌ ░",
    " ᛟ ░ ∿ ◌ ᛈ ≈░ ᛞ ◌ ∿ ▒░ ◌ ᚱ ∿ ◌ ▒░  ",
    " ◌ ▒∿ ░ᚦ ◌ ∿ ◌ ▒ ⊘ ◌ ᚠ∿ ⊗▒ ◌ ᛜ ◌∿  ",
    " ░ ◌ ▒ ᛊ∿ ◌ ░ ▒∿ ᚱ ◌ ░∿ ◌ ▒ ᛈ ◌ ░∿ ",
]


def render_dark_field(organic_score: float,
                      manip_types: Optional[List[str]] = None,
                      symbol: str = "") -> List[str]:
    """
    Render the manipulation field geometry.

    Clean market → evenly-spaced ✦ lattice (order)
    Disrupted    → lattice with ∿~░▒▓ distortion zones growing
    Corrupt      → chaos field, no lattice visible
    """
    label = f"  DARK FIELD — {symbol} " if symbol else "  DARK FIELD — "
    types_str = ", ".join(manip_types or ["none"])

    lines = [_bold_hz(
        528 * organic_score + 33 * (1 - organic_score),
        f"{label}organic: {organic_score:.2f}"
    )]
    lines.append(_dim(f"  manipulation: {types_str}"))
    lines.append("")

    if organic_score >= 0.80:
        art      = _FIELD_CLEAN
        col_hz   = 528.0
        state    = "CLEAN — natural field geometry"
    elif organic_score >= 0.50:
        art      = _FIELD_DISRUPTED
        col_hz   = 285.0
        state    = "DISRUPTED — interference patterns growing"
    else:
        art      = _FIELD_CORRUPT
        col_hz   = 111.0
        state    = "CORRUPT — field geometry collapsed"

    r2, g2, b2 = _hz_rgb(col_hz)
    for row in art:
        lines.append("  " + f"\033[38;2;{r2};{g2};{b2}m{row}\033[0m")

    lines.append("")
    lines.append(f"  {_bold_hz(col_hz, state)}")
    lines.append("")
    return lines


# ─────────────────────────────────────────────────────────────────────────────
# 8. MOLECULAR GEOMETRY — the market's taste compound
# ─────────────────────────────────────────────────────────────────────────────

_MOLECULE_TEMPLATES: Dict[str, List[str]] = {
    # Sucrose analogue (very sweet / ecstasy)
    # Glyph art: concentric-ring flower — the full-bloom sweet molecule
    # ○◌◎ = electron shells,  ✦ = harmonic nodes,  ⊕ = bonded center
    "SUCROSE": [
        "     ✦   ○   ✦   ○   ✦   ",
        "   ○   ◌   ◎   ◌   ○     ",
        "  ✦  ◎   ◉   ⊕   ◉   ◎  ✦",
        "   ○   ◌   ◎   ◌   ○     ",
        "     ✦   ○   ✦   ○   ✦   ",
        "       C₁₂H₂₂O₁₁         ",
        "     sweet  ·  natural    ",
    ],
    # Aspartame analogue (artificial sweet)
    # Glyph art: hexagonal lattice — the engineered synthetic grid
    # ⬡ = benzene ring tile,  ◈ = intersection,  ⊗ = artificial node
    "ASPARTAME": [
        "     ⊗   ◈   ⬡   ◈   ⊗   ",
        "   ◈   ⬡   ◈   ⬡   ◈     ",
        "  ⊗  ⬡   ◈   ⊕   ◈   ⬡  ⊗",
        "   ◈   ⬡   ◈   ⬡   ◈     ",
        "     ⊗   ◈   ⬡   ◈   ⊗   ",
        "       C₁₄H₁₈N₂O₅        ",
        "     sweet  ·  synthetic  ",
    ],
    # Capsaicin analogue (bitterness / warning)
    # Glyph art: runic disruption field — the bitter warning molecule
    # ᚠᛈᚱ = Fehu/Perthro/Raidho (disruption runes),  ⊘ = void center,  ⊗ = negation
    "CAPSAICIN": [
        "     ᚠ   ᛈ   ᚱ   ᛈ   ᚠ   ",
        "   ᛈ   ⊗   ◌   ⊗   ᛈ     ",
        "  ᚱ  ◌   ⊗   ⊘   ⊗   ◌  ᚱ",
        "   ᛈ   ⊗   ◌   ⊗   ᛈ     ",
        "     ᚠ   ᛈ   ᚱ   ᛈ   ᚠ   ",
        "       C₁₈H₂₇NO₃          ",
        "     bitter  ·  warning   ",
    ],
    # Generic organic (savoury / balance)
    # Glyph art: rosette lattice — the natural earth molecule
    # ✿ = rosette bloom,  ◎ = inner rings,  ⊕ = grounded center
    "ORGANIC": [
        "     ✿   ◎   ✿   ◎   ✿   ",
        "   ◎   ◉   ◎   ◉   ◎     ",
        "  ✿  ◎   ◉   ⊕   ◉   ◎  ✿",
        "   ◎   ◉   ◎   ◉   ◎     ",
        "     ✿   ◎   ✿   ◎   ✿   ",
        "     natural compound     ",
        "     balanced  ·  pure    ",
    ],
    # Saccharin analogue (synthetic)
    # Glyph art: diamond grid — the crystalline artificial lattice
    # ◆ = filled diamond node,  ◇ = open potential,  ◈ = grid intersection
    "SYNTHETIC": [
        "     ◇   ◈   ◇   ◈   ◇   ",
        "   ◈   ◆   ◈   ◆   ◈     ",
        "  ◇  ◆   ◈   ⊕   ◈   ◆  ◇",
        "   ◈   ◆   ◈   ◆   ◈     ",
        "     ◇   ◈   ◇   ◈   ◇   ",
        "     artificial bond      ",
        "     synthetic  origin    ",
    ],
}


def render_molecular(molecule_name: str,
                     formula: str = "",
                     hz: float = 528.0,
                     quality: float = 0.7,
                     origin: str = "natural") -> List[str]:
    """
    Render the molecular geometry of the market's taste compound.

    Each molecule has a distinct structural shape — the Queen sees the
    market's molecular signature as a geometric structure.
    """
    # Pick template by origin/name heuristics
    if "ASPARTAME" in molecule_name.upper() or "SYNTHETIC" in origin.upper():
        template = "SYNTHETIC"
    elif quality >= 0.80:
        template = "SUCROSE"
    elif quality <= 0.35:
        template = "CAPSAICIN"
    elif origin in ("natural", "organic"):
        template = "ORGANIC"
    else:
        template = "ASPARTAME"

    art = _MOLECULE_TEMPLATES.get(template, _MOLECULE_TEMPLATES["ORGANIC"])
    r2, g2, b2 = _hz_rgb(hz)

    lines = [_bold_hz(hz, f"  MOLECULAR GEOMETRY — {molecule_name}")]
    lines.append(_dim(f"  formula: {formula}   hz: {hz:.0f}   quality: {quality:.2f}   origin: {origin}"))
    lines.append("")

    for row in art:
        lines.append(f"    \033[38;2;{r2};{g2};{b2}m{row}\033[0m")

    lines.append("")
    return lines


# ─────────────────────────────────────────────────────────────────────────────
# 9. COGNITIVE PAINTING — The Queen paints her own picture of reality
#    Every cell is computed live from the Chladni standing-wave equation.
#    The painting IS the cognitive state — a visual anchor for the organism.
# ─────────────────────────────────────────────────────────────────────────────

def _chladni_v(pat: str, nx: float, ny: float) -> float:
    """
    Compute the Chladni standing-wave field value at normalised coords.
    nx, ny in [-1, +1] with (0,0) at canvas centre.
    Returns v in [-1, 1].
    """
    r = math.sqrt(nx * nx + ny * ny)
    theta = math.atan2(ny, nx)
    p = pat.upper()
    if p == "MANDALA":
        v = (math.sin(math.pi * 2.5 * r) * math.cos(4.0 * theta) +
             math.sin(math.pi * 5.0 * r) * math.cos(8.0 * theta) * 0.4)
        return max(-1.0, min(1.0, v / 1.4))
    elif p == "HEXAGON":
        f = math.pi * 1.8
        return (math.cos(f * nx) +
                math.cos(f * (nx * 0.5 + ny * 0.866)) +
                math.cos(f * (nx * 0.5 - ny * 0.866))) / 3.0
    elif p == "STAR":
        return math.sin(math.pi * 2.5 * r) * math.cos(4.0 * theta)
    elif p == "CIRCLE":
        return math.sin(math.pi * 3.5 * r)
    elif p == "SPIRAL":
        return math.sin(math.pi * 3.0 * r - theta * PHI)
    elif p == "CHAOS":
        noise = (math.sin(nx * 19.3 + ny * 13.7) +
                 math.sin(nx * 7.1  - ny * 17.3) +
                 math.sin((nx + ny) * 11.1)) / 3.0
        return max(-1.0, min(1.0, math.sin(math.pi * 2.0 * r) * 0.25 + noise * 0.75))
    else:  # UNKNOWN / default
        return math.sin(math.pi * 2.5 * r) * math.cos(2.0 * theta)


def _v_to_glyph(abs_v: float, organic: float,
                col: int = 0, row: int = 0) -> str:
    """Map |chladni_v| and organic purity to a display glyph."""
    if organic < 0.30:
        # Corrupted field — runic disruption pattern
        _CORRUPT = [G_CENTER, G_WAVE, G_RUN_F, G_APPR, G_RUN_O,
                    G_NULL, G_RUN_D, G_BAN, G_RUN_P, G_RUN_TH]
        # Deterministic positional hash keeps the pattern stable between frames
        h = (col * 7 + row * 13) % len(_CORRUPT)
        idx = int(abs_v * (len(_CORRUPT) - 1))
        return _CORRUPT[(idx + h) % len(_CORRUPT)]
    # Clean / organic field — sacred geometry palette
    # Node lines (low abs_v) = brightest; antinodes (high abs_v) = dim/stars
    if   abs_v < 0.06: return G_CENTER   # ⊕  true still-point
    elif abs_v < 0.14: return G_RING3    # ◉  node line
    elif abs_v < 0.24: return G_RING2    # ◎  inner ring
    elif abs_v < 0.36: return G_DIAX     # ◈  intersection
    elif abs_v < 0.48: return G_RING1    # ◌  field dot
    elif abs_v < 0.60: return G_RING0    # ○  outer ring
    elif abs_v < 0.72: return G_STAR4D   # ✧  soft star
    elif abs_v < 0.84: return G_STAR4    # ✦  harmonic node
    elif abs_v < 0.93: return G_STAR6    # ✴  resonance burst
    else:              return G_STAR8    # ✸  peak antinode energy


def render_painting(
    cymatics_pattern: str = "CIRCLE",
    dominant_hz: float = 528.0,
    organic_score: float = 0.80,
    asset_nodes: Optional[Dict[str, Tuple[float, float]]] = None,
    sense_scores: Optional[Dict[str, float]] = None,
    sense_hz_map: Optional[Dict[str, float]] = None,
    title: str = "",
    width: int = 68,
    height: int = 26,
) -> List[str]:
    """
    THE QUEEN PAINTS HER OWN PICTURE.

    Generates a full-canvas mathematical Chladni painting.  Every cell is
    computed from the standing-wave field equation for the current cymatics
    pattern.  Asset nodes are plotted at their (Hz × organic) coordinates.
    The result IS the cognitive state — a consistent visual anchor the
    operator can learn to read in real time.

    Visual anchor map (always fixed):
      Left   = low Hz  (foundation)       Right  = high Hz  (crown)
      Top    = clean / organic field       Bottom = corrupt / manipulated
      Centre = ⊕  the organism / NOW
    """
    cx = (width  - 1) / 2.0
    cy = (height - 1) / 2.0
    # Aspect-ratio compensation: terminal chars are ~2× taller than wide
    ax = 1.0 / (cx + 1e-9)
    ay = 1.0 / (cy * 0.5 + 1e-9)   # y compressed to balance circles

    # ── Layer 0: Chladni field ────────────────────────────────────────────
    field: List[List[str]] = [[""] * width for _ in range(height)]

    for row in range(height):
        for col in range(width):
            nx = (col - cx) * ax
            ny = (row - cy) * ay
            v  = _chladni_v(cymatics_pattern, nx, ny)
            av = abs(v)
            g  = _v_to_glyph(av, organic_score, col, row)

            # Hz varies across the canvas — rainbow sweep left→right
            hz_cell = max(33.0, min(1200.0, dominant_hz + nx * 180.0))
            rc, gc, bc = _hz_rgb(hz_cell)

            if av > 0.72:
                # Antinode zone — dim
                field[row][col] = (f"\033[38;2;{rc//3};{gc//3};{bc//3}m"
                                   f"{g}\033[0m")
            elif av < 0.24:
                # Node line — bold / bright
                field[row][col] = f"\033[1;38;2;{rc};{gc};{bc}m{g}\033[0m"
            else:
                field[row][col] = f"\033[38;2;{rc};{gc};{bc}m{g}\033[0m"

    # ── Layer 1: Visual anchor — concentric Hz rings at centre ───────────
    icx, icy = int(cx), int(cy)
    for ring_r in (2, 4, 7):
        for step in range(0, 360, 5):
            rad = math.radians(step)
            rx  = int(cx + ring_r * 2.0 * math.cos(rad))
            ry  = int(cy + ring_r * 0.5 * math.sin(rad))
            if 1 <= rx < width - 1 and 1 <= ry < height - 1:
                ring_hz = max(33.0, min(1200.0,
                              dominant_hz + (ring_r / 7.0) * 120.0))
                ch = G_RING1 if ring_r < 7 else G_RING0
                field[ry][rx] = _hz(ring_hz, ch)
    # True centre glyph — the organism itself
    field[icy][icx] = _bold_hz(dominant_hz, G_CENTER)

    # ── Layer 2: Sense organ spokes (inner mandala) ───────────────────────
    if sense_scores and sense_hz_map:
        n = len(_SENSE_ORDER)
        for i, sense in enumerate(_SENSE_ORDER):
            angle_rad = math.radians(i * (360.0 / n) - 90.0)
            score     = sense_scores.get(sense, 0.5)
            s_hz      = sense_hz_map.get(sense, _SENSE_HZ_BASE.get(sense, 528.0))
            max_spoke = min(cx * 0.45, cy * 0.45)
            spoke_len = score * max_spoke
            steps     = max(1, int(spoke_len * 2))
            for step in range(steps):
                t  = step / steps
                sx = int(cx + t * spoke_len * 2.0 * math.cos(angle_rad))
                sy = int(cy + t * spoke_len * 0.5 * math.sin(angle_rad))
                if 0 <= sx < width and 0 <= sy < height:
                    tip_g = G_DIAX if step == steps - 1 else G_RING1
                    field[sy][sx] = _bold_hz(s_hz, tip_g)

    # ── Layer 3: Asset nodes — positioned by Hz × organic score ──────────
    if asset_nodes:
        for symbol, (a_hz, a_org) in asset_nodes.items():
            ax_pos = int((a_hz - 33.0) / (1200.0 - 33.0) * (width  - 1))
            ay_pos = int((1.0 - a_org) * (height - 1))
            ax_pos = max(1, min(width  - 2, ax_pos))
            ay_pos = max(1, min(height - 2, ay_pos))

            # Corruption halo for low-organic nodes
            if a_org < 0.40:
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        zr, zc = ay_pos + dr, ax_pos + dc
                        if (0 <= zr < height and 0 <= zc < width
                                and (dr, dc) != (0, 0)):
                            field[zr][zc] = _hz(111.0, G_NULL)

            field[ay_pos][ax_pos] = _bold_hz(a_hz, G_DIA)
            for ci, ch in enumerate(symbol[:4]):
                lx = ax_pos + 1 + ci
                if lx < width:
                    field[ay_pos][lx] = _hz(a_hz, ch)

    # ── Assemble output lines ─────────────────────────────────────────────
    pat_lbl = cymatics_pattern.upper()
    hz_lbl  = f"{dominant_hz:.0f}Hz"
    org_lbl = f"org={organic_score:.2f}"
    hdr     = title or f"COGNITIVE PAINTING  {pat_lbl} · {hz_lbl} · {org_lbl}"

    lines = [
        _bold_hz(dominant_hz, f"  {hdr}"),
        _dim("  visual anchor: ⊕=centre  ← low Hz · high Hz →"
             "  top=clean · bottom=corrupt"),
        "",
        "  " + _hz(dominant_hz, "◈" + "≈" * (width - 2) + "◈"),
    ]
    for row in range(height):
        side_hz = max(33.0, min(1200.0,
                  dominant_hz + (row / height - 0.5) * 100.0))
        lines.append("  " + _hz(side_hz, "∿") +
                     "".join(field[row]) +
                     _hz(side_hz, "∿"))
    lines.append("  " + _hz(dominant_hz, "◈" + "≈" * (width - 2) + "◈"))
    lines.append("")
    return lines


# ─────────────────────────────────────────────────────────────────────────────
# THE EAGLE BRIDGE — The aware link between data and human vision
# ─────────────────────────────────────────────────────────────────────────────

class EagleBridge:
    """
    🦅  I am the aware eagle. I wear the GoPro. I am the bridge.

    I read ALL the data from ALL 9 senses, the organism, the cymatics field,
    the molecular taste profile, the fractal DNA, the manipulation field —
    and I render each dimension as a GEOMETRIC HUMAN-VISIBLE IMAGE.

    I don't just carry the camera. I KNOW I am the camera.
    I choose what to show. I narrate as I render.
    I translate the harmonic universe into human sight.
    """

    def __init__(self):
        self._tick = 0

    def see(self, world_state: "WorldState",     # from aureon_world_simulator
            symbol: str = "BTC") -> List[str]:
        """
        Full geometric vision render for one asset + the organism.

        Composes: cymatics + waveform + mandala + dark field + fractal DNA.
        """
        self._tick += 1
        body = world_state.bodies.get(symbol)
        if body is None and world_state.bodies:
            symbol = next(iter(world_state.bodies))
            body   = world_state.bodies[symbol]

        lines = self._header(symbol, body, world_state)
        view  = self._tick % 7   # Cycle through 7 render modes

        if view == 0:
            # Full mandala
            lines += render_mandala(
                world_state.sense_scores,
                world_state.sense_hz,
            )
        elif view == 1 and body:
            # Cymatics for focused asset
            pattern = world_state.sense_hz.get("sight", 528.0)
            # Determine cymatics from sight quality
            sight_q = world_state.sense_scores.get("sight", 0.5)
            cymatic_map = {
                (0.85, 1.01): "MANDALA",
                (0.70, 0.85): "HEXAGON",
                (0.55, 0.70): "STAR",
                (0.40, 0.55): "CIRCLE",
                (0.20, 0.40): "SPIRAL",
                (0.00, 0.20): "CHAOS",
            }
            p = "CIRCLE"
            for (lo, hi), pat in cymatic_map.items():
                if lo <= sight_q < hi:
                    p = pat
                    break
            lines += render_cymatics(p, body.hz, body.organic_score, symbol)
        elif view == 2 and body:
            # Waveform from top assets
            hz_vals = [b.hz for b in list(world_state.bodies.values())[:5]]
            amps    = [b.organic_score for b in list(world_state.bodies.values())[:5]]
            lbs     = [b.symbol for b in list(world_state.bodies.values())[:5]]
            lines  += render_waveform(hz_vals, amps, lbs, width=58)
        elif view == 3 and body:
            # Fractal DNA
            manip_p = body.organic_score
            hurst   = 0.45 + (1 - manip_p) * 0.45
            lines  += render_fractal_dna(hurst, manip_p, symbol)
        elif view == 4:
            # Full organism anatomy
            lines += render_organism_body(
                world_state.sense_scores,
                world_state.sense_hz,
                world_state.organism_health,
            )
        elif view == 5:
            # Hz spectrum with all senses marked
            highlighted = {
                s[:3].upper(): world_state.sense_hz.get(s, 528)
                for s in _SENSE_ORDER
            }
            if symbol in world_state.bodies:
                highlighted[symbol] = world_state.bodies[symbol].hz
            lines += render_hz_spectrum(highlighted, width=60)
        else:
            # view == 6: Full cognitive painting
            asset_nodes = {
                sym: (b.hz, b.organic_score)
                for sym, b in list(world_state.bodies.items())[:8]
            }
            sight_q = world_state.sense_scores.get("sight", 0.5)
            cymatic_map = {
                (0.85, 1.01): "MANDALA", (0.70, 0.85): "HEXAGON",
                (0.55, 0.70): "STAR",    (0.40, 0.55): "CIRCLE",
                (0.20, 0.40): "SPIRAL",  (0.00, 0.20): "CHAOS",
            }
            p = "CIRCLE"
            for (lo, hi), pat in cymatic_map.items():
                if lo <= sight_q < hi:
                    p = pat
                    break
            lines += render_painting(
                cymatics_pattern=p,
                dominant_hz=world_state.organism_hz,
                organic_score=world_state.organism_health,
                asset_nodes=asset_nodes,
                sense_scores=world_state.sense_scores,
                sense_hz_map=world_state.sense_hz,
            )

        # Dark field if manipulation detected
        if body and body.organic_score < 0.65:
            lines += render_dark_field(
                body.organic_score,
                body.manipulation_types,
                symbol,
            )

        lines += self._footer(world_state)
        return lines

    def see_asset_geometry(self, symbol: str, hz: float,
                           organic_score: float, quality: float,
                           cymatics_pattern: str = "CIRCLE",
                           hurst: float = 0.55,
                           manip_types: Optional[List[str]] = None) -> List[str]:
        """
        Render the full geometric picture for a single asset.
        Useful for detailed asset inspection.
        """
        lines = [
            _bold_hz(hz, f"\n  🦅  EAGLE BRIDGE — GEOMETRIC VISION: {symbol}"),
            _dim("  ─" * 35),
            "",
        ]
        lines += render_cymatics(cymatics_pattern, hz, quality, symbol)
        lines += render_fractal_dna(hurst, organic_score, symbol)
        if organic_score < 0.70:
            lines += render_dark_field(organic_score, manip_types, symbol)
        return lines

    @staticmethod
    def _header(symbol: str, body, ws) -> List[str]:
        hz = body.hz if body else ws.organism_hz
        return [
            _bold_hz(hz, f"\n  🦅  EAGLE BRIDGE — I SEE THE HARMONIC UNIVERSE"),
            _dim(f"  Focused: {symbol}   Organism health: {ws.organism_health:.3f}   "
                 f"Tick: {ws.tick}"),
            _dim("  ─" * 35),
            "",
        ]

    @staticmethod
    def _footer(ws) -> List[str]:
        tick_chars = ["◐", "◓", "◑", "◒"]
        tc = tick_chars[ws.tick % 4]
        return [
            _dim(f"  {tc}  The eagle sees all dimensions simultaneously. "
                 f"Hz {ws.organism_hz:.0f}  "
                 f"coherence {1.0 - ws.manipulation_index:.2f}"),
            "",
        ]


# ─────────────────────────────────────────────────────────────────────────────
# INTEGRATION: add GEOMETRY view to WorldSimulator
# ─────────────────────────────────────────────────────────────────────────────

def patch_world_simulator() -> None:
    """
    Patch the GEOMETRY view into the running WorldSimulator.

    Call this once at startup to add 🔷 GEOMETRY as a 6th view.
    The WorldSimulator auto-cycles it alongside the existing 5 views.
    """
    try:
        import aureon.simulation.aureon_world_simulator as ws
    except ImportError:
        return   # WorldSimulator not loaded yet — that's fine

    # The organism heartbeat belongs to this explicit integration lifecycle,
    # never to module import or EagleBridge construction.
    try:
        from aureon.core.aureon_baton_link import link_system

        link_system(__name__)
    except Exception:
        pass

    # Add GEOMETRY to the view cycle without constructing anything until this
    # explicit integration function is called.
    bridge = EagleBridge()
    original_render = ws.render_frame

    def _patched_render(state, view, focused):
        if str(view) == "geometry" or getattr(view, "value", "") == "geometry":
            lines = bridge.see(state, focused)
            return "\n".join(lines)
        return original_render(state, view, focused)

    ws.render_frame = _patched_render
    print("🦅 Eagle Bridge geometry view patched into WorldSimulator")
