"""Stage 6 receipts: pin provenance and the public source-boundary census.

The check rereads the pin and tip git objects and rescans the tree. It does
not call a public entry point and it does not publish a reachable count.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PIN = "34864ff0547d2cff03e707414743a3b0cc8770b5"
TIP = "c68a89d2a184d99582bb24310b91e024323a212c"
PIN_AUREON_TREE = "3ba0cab4a5e193b01943e5e6e0be25077ff759f6"
PRIOR_SWEEP_PIN = "ad9be6c3179bba140fb7e88d5733616046110da9"
PRIOR_SWEEP_TREE = "2b89d73db122486e2537047baa9b342f3a0249be"
PIN_INVENTORY_SHA256 = "4bc19ea9b5444a7b8a9abbd3fabf635d083bd25bea6c1b2d6eab2605b4f5716b"

pytestmark = pytest.mark.timeout(180)


def _load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_stage6_receipts_match_the_pin_and_leave_gaps_open() -> None:
    provenance = _load("measured/go_live_stage6_provenance.json")
    census = _load("measured/go_live_stage6_source_census.json")
    markdown = (ROOT / "docs/runbooks/GO_LIVE_STAGE6_SOURCE_CENSUS.md").read_text(encoding="utf-8")

    assert provenance["schema"] == "aureon.go-live.release-provenance.v1"
    assert provenance["receipt"] == 2
    assert provenance["decision"] == "HOLD"
    assert provenance["go_live_clear"] is False
    assert provenance["receipts_not_in_this_stage"] == [1, 3, 5]
    assert provenance["pin"] == PIN
    assert provenance["tip"] == TIP
    assert provenance["pin_aureon_tree"] == PIN_AUREON_TREE
    assert provenance["tip_aureon_tree"] == PIN_AUREON_TREE
    assert provenance["aureon_trees_match"] is True
    assert provenance["pin_move_touches_aureon"] is False
    assert provenance["pin_move_touches_inventory"] is False
    assert provenance["inventory_blobs_match"] is True
    assert provenance["pin_inventory_sha256"] == PIN_INVENTORY_SHA256
    assert len(provenance["pin_move_delta"]) == 32
    assert len(provenance["release_tree_files"]) == provenance["release_tree_file_count"]
    sweep = provenance["measured_call_sweep"]
    assert sweep["pin"] == PRIOR_SWEEP_PIN
    assert sweep["aureon_tree"] == PRIOR_SWEEP_TREE
    assert sweep["repeated_at_pin"] is False
    assert provenance["digest"] in markdown

    assert census["schema"] == "aureon.go-live.source-boundary-census.v1"
    assert census["receipt"] == 4
    assert census["decision"] == "HOLD"
    assert census["go_live_clear"] is False
    assert census["reachable_count"] is None
    assert census["source_boundary_closed"] is True
    assert census["coverage_plan_open_through"] == 2
    assert census["coverage_plan_stages_3_and_4_open"] is False
    assert census["unlisted_in_inventory"] == []
    assert census["missing_from_source"] == []
    assert census["field_drift"] == []
    assert census["removed_since_pin_inventory"] == []
    assert census["pin_inventory_sha256"] == PIN_INVENTORY_SHA256
    assert census["inventory_sha256"] != PIN_INVENTORY_SHA256
    assert census["provenance_digest"] == provenance["digest"]
    assert len(census["added_public_entry_points"]) == 17
    assert all(item["refusal"] == "plan stage 4 is not open" for item in census["added_public_entry_points"])
    assert all(item["plan_stage"] == 4 for item in census["added_public_entry_points"])
    assert census["post_pin_checkout_paths"] == [
        "aureon/evaluation/market_series.py",
        "aureon/evidence/hnc_anchor.py",
    ]
    gaps = {item["id"]: item["text"] for item in census["open_gaps"]}
    assert set(gaps) == {
        "sweep_not_repeated",
        "brain_proof_blob",
        "plan_stages_3_and_4_closed",
        "changed_blobs_not_recalled",
        "receipts_1_and_5_absent",
        "pin_inventory_predates_closure",
        "post_pin_checkout_not_in_closure",
    }
    assert "DigiCert" in gaps["receipts_1_and_5_absent"]
    assert "does not report the system alive" in gaps["receipts_1_and_5_absent"]
    assert "http_get" in gaps["post_pin_checkout_not_in_closure"]
    assert "The pin is not moved." in gaps["post_pin_checkout_not_in_closure"]
    assert "This is not a go-live clear." in markdown
    assert "Decision: `HOLD`." in markdown

    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "go_live_stage6",
        ROOT / "scripts" / "validation" / "go_live_stage6.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.check()
