"""Root layout follows the Sero archive rule.

Unreferenced root notes, one-off scripts, and captures live under
``archive/workspace-root``. Paths the organ registry and ``paths.py`` name
stay where they are declared. Missing engine scripts are not invented.
"""

from __future__ import annotations

from pathlib import Path

from aureon_fusion.organ_registry import ORGANS
from aureon_fusion.paths import (
    HNC_DAEMON,
    PLANETARY_DAEMON,
    REALTIME_FEEDER,
    SCHUMANN_DAEMON,
    SERO_AUTONOMOUS_EXPANSION,
    SERO_MASTER_ORCHESTRATOR,
)

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "archive" / "workspace-root"

ARCHIVED = {
    "notes": (
        "CAPABILITY_REPORT.md",
        "LATENCY_READINESS_PLAN.md",
        "LSSP_preregistration_v1.0.md",
        "PRIVATE_PDFS_PENDING_APPROVAL.md",
        "STRESS_TEST_RESULTS_2026-05-19.md",
        "SYSTEM_PLACEMENT_CHECKLIST.md",
        "XIRX_session_codex.md",
    ),
    "scripts": (
        "aureon_held_transaction_history_capture.py",
        "aureon_location_transfer_batch_operator.py",
        "aureon_location_transfer_hnc_ocr_audit.py",
        "aureon_location_transfer_manifest_builder.py",
        "current_balance_live_preflight.py",
    ),
    "captures": (
        "Aureon_HNC_Celestial_Art_Master_Ledger_v1.xlsx",
        "Aureon_HNC_Master_Ledger_Dashboard_Preview.png",
        "DOC-20261005-WA0007 (1).pdf",
        "DOC-20261005-WA0007.pdf",
        "Grail_White_Paper_v2_2026-10-06.pdf",
        "HNC_Artwork_Gallery.html",
        "Leckey_2026_Evolutionary_Coherence_HNC_Four_Pillar_White_Paper.pdf",
        "Master_Ledger_Threshold_Route_2026-10-05.pdf",
        "f5691962f75c3e4afdc58c1be311527e(2) (1).pdf",
        "hnc_whitepaper_a11y_report_final.json",
    ),
}

KEEPERS = (
    "SELF_REPAIR.md",
    "PRODUCTION_READINESS.md",
    "bot_army_catalog.json",
    "aureon_obsidian_filter.py",
    "current_balance_stock_quantity_enquiry.py",
    "aureon_location_transfer_operator.py",
    "README.md",
    "LAUNCHER_INVENTORY.md",
    "CLAUDE.md",
)


def test_unreferenced_root_files_live_in_the_archive() -> None:
    for folder, names in ARCHIVED.items():
        for name in names:
            assert not (ROOT / name).exists(), name
            archived = ARCHIVE / folder / name
            assert archived.is_file(), archived
            assert ARCHIVE in archived.parents


def test_live_declarations_stay_out_of_the_archive() -> None:
    declared = [
        HNC_DAEMON,
        PLANETARY_DAEMON,
        REALTIME_FEEDER,
        SCHUMANN_DAEMON,
        SERO_AUTONOMOUS_EXPANSION,
        SERO_MASTER_ORCHESTRATOR,
    ]
    for spec in ORGANS.values():
        script = spec.get("script")
        if script:
            declared.append(Path(str(script)))
    archived_names = {name for names in ARCHIVED.values() for name in names}
    for path in declared:
        assert "archive/workspace-root" not in path.as_posix()
        assert path.name not in archived_names
        if path.is_file():
            assert ARCHIVE not in path.resolve().parents
        elif path.is_absolute() and path.parent == ROOT:
            assert not (ARCHIVE / path.name).exists()


def test_root_keepers_stay_at_the_root() -> None:
    for name in KEEPERS:
        assert (ROOT / name).is_file(), name
        assert not (ARCHIVE / "notes" / name).exists()
        assert not (ARCHIVE / "scripts" / name).exists()
