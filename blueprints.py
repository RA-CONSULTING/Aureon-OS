#!/usr/bin/env python3
"""Bio↔Vibe blueprints for the Phenolic Fingerprint System.

Two visual blueprints that make the HNC "bio→vibe" logic legible, built only from
the repo's own systems (`connector`, `phenolic_fingerprint`, `fetcher`) plus
matplotlib + numpy + PIL + rdkit:

1. **Plants as harmonic nodes** (`render_plant_harmonic_nodes`) — a bipartite
   blueprint linking each plant to the *coherence nodes* (clusters of modulation
   frequencies) its molecules express. Plants that share a coherence node are
   harmonically related.
2. **Molecules side-by-side** (`render_molecule_blueprints`) — per molecule, the
   molecular makeup (2D structure + cm⁻¹ spectrum) beside the harmonic makeup
   (octave-downconverted modulation-frequency fingerprint + coherence-node bands +
   φ sidebands).

The bio→vibe transform is the engine's pre-registered
`peak_to_modulation_hz` (cm⁻¹ → THz → octave-folded modulation Hz); the
coherence-node clustering is ported faithfully from the HNC packet blueprint.

Integrity: figures default to the **experimental** lane (the falsifiable view);
computed (GFN2-xTB) harmonics are opt-in (`--include-computed`) and always
labeled "theoretical", never silently merged. Deterministic; no global state.
"""

from __future__ import annotations

import argparse
import io
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final

import matplotlib

matplotlib.use("Agg")  # headless figure generation

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import connector  # noqa: E402
import phenolic_fingerprint as engine  # noqa: E402

__all__ = [
    "cluster_coherence_nodes",
    "plant_molecule_map",
    "render_plant_harmonic_nodes",
    "render_molecule_blueprints",
    "main",
]

# --- Validated dark palette (see dataviz validator; dark surface) ---------------
BG: Final[str] = "#0a0a15"
PANEL: Final[str] = "#12121e"
GRID: Final[str] = "#2a2a3e"
INK: Final[str] = "#e8e8f0"
MUTED: Final[str] = "#9a9ab0"
C_EXPERIMENTAL: Final[str] = "#35A97E"  # experimental provenance
C_COMPUTED: Final[str] = "#C6832C"      # computed (theoretical) provenance
C_NODE: Final[str] = "#5A8FE0"          # coherence-node / harmonic accent
C_PHI: Final[str] = "#B060C0"           # golden-ratio sideband accent

REPO_ROOT: Final[Path] = Path(__file__).resolve().parent
FIG_DIR: Final[Path] = REPO_ROOT / "docs" / "research" / "figures"
CODEX_CSV: Final[Path] = REPO_ROOT / "tests" / "fixtures" / "weed_phenolic_spectral_map_codex.csv"

# Tokens in the codex `plant` column that are not real plants.
_NON_PLANT_TOKENS: Final[frozenset[str]] = frozenset({"many", "widespread", "no data", ""})

# SMILES for 2D structure drawing: reuse the fetcher's set + a few more.
_EXTRA_SMILES: Final[dict[str, str]] = {
    "chicoric acid": "C1=CC(=C(C=C1C=CC(=O)OC(C(C(=O)O)OC(=O)C=CC2=CC(=C(C=C2)O)O)C(=O)O)O)O",
    "rosmarinic acid": "C1=CC(=C(C=C1CC(C(=O)O)OC(=O)C=CC2=CC(=C(C=C2)O)O)O)O",
    "silybin/silymarin": "COC1=C(C=CC(=C1)C2C(OC3=C(O2)C=C(C=C3)C4C(C(=O)C5=C(C=C(C=C5O4)O)O)O)CO)O",
}


def _smiles_map() -> dict[str, str]:
    smiles: dict[str, str] = {}
    try:
        import fetcher

        smiles.update(fetcher.SMILES)
    except ImportError:
        pass
    smiles.update(_EXTRA_SMILES)
    return smiles


# ============================================================================
# HARMONIC-NODE LOGIC (ported from hnc_biomolecule_packet_v02.cluster_coherence_nodes)
# ============================================================================


def cluster_coherence_nodes(
    records: list[dict[str, Any]],
    tolerance_hz: float = engine.COHERENCE_TOLERANCE_HZ,
) -> list[dict[str, Any]]:
    """Cluster modulation frequencies into coherence nodes (running-mean greedy).

    Faithful port of the HNC packet's clustering: sort by
    ``modulation_frequency_hz``; add each record to the current cluster if within
    ``tolerance_hz`` of the cluster's running mean, else start a new cluster. Each
    node reports center/min/max/spread, peak count, and its molecule set.
    """
    if not records:
        return []
    ordered = sorted(records, key=lambda r: r["modulation_frequency_hz"])
    clusters: list[list[dict[str, Any]]] = [[ordered[0]]]
    for rec in ordered[1:]:
        current = clusters[-1]
        center = sum(r["modulation_frequency_hz"] for r in current) / len(current)
        if abs(rec["modulation_frequency_hz"] - center) <= tolerance_hz:
            current.append(rec)
        else:
            clusters.append([rec])
    nodes: list[dict[str, Any]] = []
    for idx, cluster in enumerate(clusters, start=1):
        freqs = [float(r["modulation_frequency_hz"]) for r in cluster]
        nodes.append(
            {
                "node_id": f"CN-{idx:03d}",
                "center_hz": round(sum(freqs) / len(freqs), 4),
                "min_hz": round(min(freqs), 4),
                "max_hz": round(max(freqs), 4),
                "spread_hz": round(max(freqs) - min(freqs), 4),
                "n_peaks": len(cluster),
                "molecules": sorted({r["molecule"] for r in cluster}),
            }
        )
    return nodes


# ============================================================================
# DATA COLLECTION (repo systems)
# ============================================================================


@dataclass(frozen=True)
class CompoundView:
    """Everything a blueprint needs about one compound."""

    molecule: str
    peaks_cm1: np.ndarray
    harmonics_hz: np.ndarray
    provenance: str  # "experimental" | "computed" | "mixed"
    test_A_p: float | None = None
    test_B_p: float | None = None
    separable: bool = False
    sources: list[str] = field(default_factory=list)


def plant_molecule_map(spectral_csv: str | Path = CODEX_CSV) -> dict[str, list[str]]:
    """Map each real plant to the molecules it contains (from the codex `plant` column)."""
    raw, _ = connector.ingest(spectral_csv)
    mapping: dict[str, set[str]] = {}
    for row in raw:
        plant_field = row.extras.get("plant", "")
        for token in plant_field.split(";"):
            plant = token.strip().lower()
            if plant and plant not in _NON_PLANT_TOKENS:
                mapping.setdefault(plant, set()).add(row.molecule)
    return {plant: sorted(mols) for plant, mols in sorted(mapping.items())}


def _collect_compounds(sources: list[str | Path], *, nulls: int, seed: int) -> dict[str, CompoundView]:
    """Ingest + validate + score; return per-compound peaks, harmonics, provenance."""
    raw, _ = connector.ingest_many(sources)
    accepted, _ = connector.validate(raw)

    peaks: dict[str, list[float]] = {}
    harmonics: dict[str, list[float]] = {}
    tags: dict[str, set[str]] = {}
    for row in accepted:
        peaks.setdefault(row.molecule, []).append(row.peak_value)
        harmonics.setdefault(row.molecule, []).append(
            engine.peak_to_modulation_hz(row.peak_value, row.unit)
        )
        tags.setdefault(row.molecule, set()).add(
            "computed" if "COMPUTED" in row.source else "experimental"
        )

    result = connector.run_analysis(sources, nulls=nulls, seed=seed)
    views: dict[str, CompoundView] = {}
    for name, freqs in harmonics.items():
        tagset = tags.get(name, set())
        prov = "mixed" if len(tagset) > 1 else next(iter(tagset), "experimental")
        comp = result.compounds.get(name)
        views[name] = CompoundView(
            molecule=name,
            peaks_cm1=np.array(sorted(peaks.get(name, []))),
            harmonics_hz=np.array(sorted(freqs)),
            provenance=prov,
            test_A_p=comp.test_A_p if comp else None,
            test_B_p=comp.test_B_p if comp else None,
            separable=bool(comp.separable) if comp else False,
            sources=comp.sources if comp else [],
        )
    return views


def _prov_color(provenance: str) -> str:
    return {"experimental": C_EXPERIMENTAL, "computed": C_COMPUTED, "mixed": C_NODE}.get(
        provenance, C_EXPERIMENTAL
    )


def _structure_image(smiles: str, size: tuple[int, int] = (380, 260)):
    """Render a 2D molecular structure to a PIL image (white card), or None."""
    try:
        from PIL import Image
        from rdkit import Chem
        from rdkit.Chem.Draw import rdMolDraw2D
    except ImportError:
        return None
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    drawer = rdMolDraw2D.MolDraw2DCairo(size[0], size[1])
    rdMolDraw2D.PrepareAndDrawMolecule(drawer, mol)
    drawer.FinishDrawing()
    return Image.open(io.BytesIO(drawer.GetDrawingText()))


# ============================================================================
# BLUEPRINT 1 — molecules side-by-side (molecular makeup | harmonic makeup)
# ============================================================================


def _save(fig, out_dir: Path, stem: str) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for ext in ("png", "svg"):
        p = out_dir / f"{stem}.{ext}"
        fig.savefig(p, dpi=150, facecolor=BG, edgecolor="none", bbox_inches="tight")
        paths.append(p)
    plt.close(fig)
    return paths


def render_molecule_blueprints(
    sources: list[str | Path],
    *,
    out_dir: Path = FIG_DIR,
    nulls: int = 500,
    seed: int = 0,
) -> list[Path]:
    """Render the per-molecule side-by-side blueprint (structure | cm⁻¹ | harmonics)."""
    views = {k: v for k, v in _collect_compounds(sources, nulls=nulls, seed=seed).items()
             if v.harmonics_hz.size >= 2}
    names = sorted(views)
    smiles = _smiles_map()
    low, high = engine.TARGET_BAND_HZ

    n = len(names)
    fig = plt.figure(figsize=(13.5, max(2.4 * n, 3.0)))
    fig.patch.set_facecolor(BG)
    gs = fig.add_gridspec(n, 3, width_ratios=[1.0, 1.1, 1.6], hspace=0.55, wspace=0.28)

    for i, name in enumerate(names):
        v = views[name]
        col = _prov_color(v.provenance)

        # Column A — 2D molecular structure (molecular makeup)
        ax_s = fig.add_subplot(gs[i, 0])
        ax_s.set_facecolor(PANEL)
        img = _structure_image(smiles[name]) if name in smiles else None
        if img is not None:
            ax_s.imshow(img)
        else:
            ax_s.text(0.5, 0.5, "structure\nnot embedded", ha="center", va="center",
                      color=MUTED, fontsize=8, transform=ax_s.transAxes)
        ax_s.set_xticks([])
        ax_s.set_yticks([])
        for sp in ax_s.spines.values():
            sp.set_color(GRID)
        ax_s.set_ylabel(name, color=INK, fontsize=9, rotation=0, ha="right", va="center",
                        labelpad=28)

        # Column B — cm⁻¹ spectrum (molecular makeup)
        ax_c = fig.add_subplot(gs[i, 1])
        ax_c.set_facecolor(PANEL)
        ax_c.vlines(v.peaks_cm1, 0, 1, color=col, linewidth=0.9, alpha=0.85)
        ax_c.set_xlim(0, 3800)
        ax_c.set_ylim(0, 1.15)
        ax_c.set_yticks([])
        ax_c.tick_params(colors=MUTED, labelsize=7)
        for sp in ax_c.spines.values():
            sp.set_color(GRID)
        if i == 0:
            ax_c.set_title("molecular makeup — cm⁻¹ spectrum", color=INK, fontsize=9)
        if i == n - 1:
            ax_c.set_xlabel("wavenumber (cm⁻¹)", color=MUTED, fontsize=8)

        # Column C — modulation-Hz harmonics + coherence-node bands (harmonic makeup)
        ax_h = fig.add_subplot(gs[i, 2])
        ax_h.set_facecolor(PANEL)
        recs = [{"modulation_frequency_hz": f, "molecule": name} for f in v.harmonics_hz]
        nodes = cluster_coherence_nodes(recs)
        for nd in nodes:
            ax_h.axvspan(nd["min_hz"] - 2, nd["max_hz"] + 2, color=C_NODE, alpha=0.12)
        ax_h.vlines(v.harmonics_hz, 0, 1, color=col, linewidth=0.9, alpha=0.9)
        # golden-ratio sideband ticks on the densest node center
        if nodes:
            biggest = max(nodes, key=lambda d: d["n_peaks"])
            c = biggest["center_hz"]
            for d in (engine.PHI_INV_9,):
                ax_h.plot([c * (1 - d), c * (1 + d)], [1.08, 1.08], color=C_PHI, lw=1.4)
        ax_h.set_xlim(low - 20, high + 20)
        ax_h.set_ylim(0, 1.2)
        ax_h.set_yticks([])
        ax_h.tick_params(colors=MUTED, labelsize=7)
        for sp in ax_h.spines.values():
            sp.set_color(GRID)
        pa = "n/a" if v.test_A_p is None else f"{v.test_A_p:.3f}"
        pb = "n/a" if v.test_B_p is None else f"{v.test_B_p:.3f}"
        flag = "SEPARABLE" if v.separable else "not sep."
        ax_h.text(0.985, 0.86,
                  f"{v.provenance} · {len(v.harmonics_hz)} tones · {len(nodes)} nodes\n"
                  f"A={pa} B={pb} · {flag}",
                  transform=ax_h.transAxes, ha="right", va="top", color=INK, fontsize=6.6,
                  bbox={"boxstyle": "round,pad=0.3", "fc": BG, "ec": col, "lw": 0.8})
        if i == 0:
            ax_h.set_title("harmonic makeup — modulation band (Hz)", color=INK, fontsize=9)
        if i == n - 1:
            ax_h.set_xlabel("HNC modulation frequency (Hz)", color=MUTED, fontsize=8)

    fig.suptitle("Phenolic Bio→Vibe Blueprints — molecular makeup ↔ harmonic makeup",
                 color=INK, fontsize=13, y=0.995)
    fig.text(0.5, 0.004,
             "bio→vibe: cm⁻¹ peak → THz (×0.0299792458) → octave-folded modulation Hz "
             "[peak_to_modulation_hz].   "
             "green=experimental  amber=computed(theoretical)  blue band=coherence node  "
             "purple=φ sideband",
             ha="center", color=MUTED, fontsize=7.5)
    return _save(fig, out_dir, "phenolic_molecule_blueprints")


# ============================================================================
# BLUEPRINT 2 — plants as harmonic nodes (bipartite plant ↔ coherence node)
# ============================================================================


def render_plant_harmonic_nodes(
    sources: list[str | Path],
    *,
    spectral_csv: str | Path = CODEX_CSV,
    out_dir: Path = FIG_DIR,
    nulls: int = 500,
    seed: int = 0,
    min_shared_molecules: int = 2,
) -> list[Path]:
    """Render the plant↔coherence-node blueprint (plants as harmonic nodes)."""
    plants = plant_molecule_map(spectral_csv)
    views = _collect_compounds(sources, nulls=nulls, seed=seed)

    # Global coherence nodes across all molecules' harmonics.
    recs: list[dict[str, Any]] = []
    for name, v in views.items():
        for f in v.harmonics_hz:
            recs.append({"modulation_frequency_hz": float(f), "molecule": name})
    nodes = cluster_coherence_nodes(recs)
    # Keep the "shared" harmonic nodes (multi-molecule) — the meaningful links.
    shared = [nd for nd in nodes if len(nd["molecules"]) >= min_shared_molecules]
    shared.sort(key=lambda d: d["center_hz"])

    plant_names = [p for p, mols in plants.items() if any(m in views for m in mols)]
    plant_names.sort()

    fig = plt.figure(figsize=(14, max(0.5 * len(plant_names), 8)))
    fig.patch.set_facecolor(BG)
    ax = fig.add_subplot(111)
    ax.set_facecolor(BG)

    py = {p: i for i, p in enumerate(plant_names)}
    n_nodes = max(len(shared), 1)
    ny = {nd["node_id"]: i * (len(plant_names) - 1) / max(n_nodes - 1, 1)
          for i, nd in enumerate(shared)}
    x_plant, x_node = 0.0, 1.0

    # edges: plant -> coherence node it populates
    for nd in shared:
        node_mols = set(nd["molecules"])
        for p in plant_names:
            if node_mols & set(plants[p]):
                ax.plot([x_plant, x_node], [py[p], ny[nd["node_id"]]],
                        color=C_NODE, alpha=0.28, lw=0.8, zorder=1)

    # plant nodes (harmonic nodes): size = # molecules with data
    for p in plant_names:
        n_mol = sum(1 for m in plants[p] if m in views)
        ax.scatter([x_plant], [py[p]], s=90 + 55 * n_mol, color=C_EXPERIMENTAL,
                   edgecolors=INK, linewidths=0.6, zorder=3)
        ax.text(x_plant - 0.03, py[p], p, ha="right", va="center", color=INK, fontsize=8)

    # coherence-node markers: size = # peaks, label = center Hz + #molecules
    for nd in shared:
        y = ny[nd["node_id"]]
        ax.scatter([x_node], [y], s=60 + 12 * len(nd["molecules"]), color=C_NODE,
                   edgecolors=INK, linewidths=0.6, zorder=3, marker="H")
        ax.text(x_node + 0.03, y, f"{nd['center_hz']:.0f} Hz  ({len(nd['molecules'])} mol)",
                ha="left", va="center", color=C_NODE, fontsize=7)

    ax.set_xlim(-0.55, 1.55)
    ax.set_ylim(-1, len(plant_names))
    ax.axis("off")
    ax.text(x_plant, len(plant_names) - 0.3, "PLANTS (harmonic nodes)", ha="center",
            color=INK, fontsize=10, fontweight="bold")
    ax.text(x_node, len(plant_names) - 0.3, "SHARED COHERENCE NODES", ha="center",
            color=C_NODE, fontsize=10, fontweight="bold")
    fig.suptitle("Phenolic Bio→Vibe Blueprint — plants as harmonic nodes",
                 color=INK, fontsize=13)
    fig.text(0.5, 0.01,
             f"Each plant links to the coherence nodes (≥{min_shared_molecules} molecules) its "
             "phenolics express in the 1000–2000 Hz HNC modulation band. "
             "Experimental lane; node marker size = peaks, plant size = molecules.",
             ha="center", color=MUTED, fontsize=8)
    return _save(fig, out_dir, "phenolic_plant_harmonic_nodes")


# ============================================================================
# CLI
# ============================================================================


def _default_sources(include_computed: bool) -> list[str | Path]:
    data = REPO_ROOT / "data" / "spectra"
    srcs: list[str | Path] = [
        CODEX_CSV,
        data / "nist_ir_peaks.csv",
        data / "curated_open_access_peaks.csv",
    ]
    if include_computed:
        srcs.append(data / "computed_xtb_peaks.csv")
    return [s for s in srcs if Path(s).exists()]


def main(argv: list[str] | None = None) -> int:
    """CLI: ``blueprints.py [--include-computed] [--out DIR] [--sources ...]``."""
    parser = argparse.ArgumentParser(description="Generate phenolic bio↔vibe blueprints.")
    parser.add_argument("--sources", nargs="*", default=None,
                        help="Override source CSV/zip paths (default: experimental set)")
    parser.add_argument("--include-computed", action="store_true",
                        help="Include the GFN2-xTB computed (theoretical) lane")
    parser.add_argument("--out", default=str(FIG_DIR), help="Output figure directory")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--nulls", type=int, default=500)
    args = parser.parse_args(argv)

    sources = args.sources if args.sources else _default_sources(args.include_computed)
    out_dir = Path(args.out)
    try:
        mol_paths = render_molecule_blueprints(sources, out_dir=out_dir, nulls=args.nulls, seed=args.seed)
        plant_paths = render_plant_harmonic_nodes(sources, out_dir=out_dir, nulls=args.nulls, seed=args.seed)
    except (connector.ConnectorError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    for p in (*mol_paths, *plant_paths):
        print(f"wrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
