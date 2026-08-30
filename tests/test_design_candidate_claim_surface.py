"""Focused public-text claim controls for staged design candidates."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from aureon.operator.design_candidate_claim_surface import (
    CLAIM_SURFACE_SCHEMA,
    evaluate_candidate_claim_surface,
    public_text_sha256,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _json_sha256(value: object) -> str:
    return (
        hashlib.sha256(
            json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        )
        .hexdigest()
        .upper()
    )


def _context() -> dict[str, object]:
    capsule = {
        "route_id": "homepage",
        "route": "/",
        "claims": [
            {
                "id": "homepage-claim",
                "claim": "Aureon is an evidence-led test company.",
                "boundary": "This fixture is not evidence of customer adoption or independent validation.",
                "permitted_wording": ["Aureon is an evidence-led test company."],
                "prohibited_inferences": ["customer adoption", "independent validation"],
            }
        ],
    }
    return {
        "id": "homepage",
        "route": "/",
        "allowed_paths": ["index.html", "script.js", "styles.css", "data/copy.json"],
        "claim_capsule": capsule,
        "claim_capsule_sha256": _json_sha256(capsule),
    }


def _preview(baseline: Path, candidate: Path, *, paths: list[str], context: dict[str, object]) -> dict:
    return evaluate_candidate_claim_surface(
        baseline_site=baseline,
        candidate_site=candidate,
        changed_paths=paths,
        context=context,
        manifest=[],
    )


def _manifest_from_preview(preview: dict, *, kinds: dict[str, tuple[str, str]]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for row in preview["new_surfaces"]:
        kind, claim_id = kinds[row["text_sha256"]]
        rationale = {
            "permitted-wording": "route-permitted-wording",
            "boundary": "route-claim-boundary",
            "non-claim": "interface-label",
        }[kind]
        result.append(
            {
                "path": row["path"],
                "kind": kind,
                "claim_id": claim_id,
                "text_sha256": row["text_sha256"],
                "surface_sha256": row["surface_sha256"],
                "rationale": rationale,
            }
        )
    return result


def test_exact_permitted_wording_and_negative_boundary_pass_without_echoing_copy(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    _write(baseline / "index.html", "<title>Aureon</title><main><p>Existing record.</p></main>")
    permitted = "Aureon is an evidence-led test company."
    boundary = "This fixture is not evidence of customer adoption or independent validation."
    _write(
        candidate / "index.html",
        f"<title>Aureon</title><main><p>{permitted}</p><p>{boundary}</p></main>",
    )
    context = _context()
    preview = _preview(baseline, candidate, paths=["index.html"], context=context)
    manifest = _manifest_from_preview(
        preview,
        kinds={
            public_text_sha256(permitted): ("permitted-wording", "homepage-claim"),
            public_text_sha256(boundary): ("boundary", "homepage-claim"),
        },
    )

    result = evaluate_candidate_claim_surface(
        baseline_site=baseline,
        candidate_site=candidate,
        changed_paths=["index.html"],
        context=context,
        manifest=manifest,
    )

    assert result["schema"] == CLAIM_SURFACE_SCHEMA
    assert result["passed"] is True
    assert result["state"] == "pass"
    assert result["release_eligible"] is False
    serialised = json.dumps(result)
    assert permitted not in serialised
    assert boundary not in serialised


def test_unsupported_customer_adoption_copy_cannot_be_disguised_as_non_claim(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    _write(baseline / "index.html", "<title>Aureon</title><main><p>Existing record.</p></main>")
    unsafe = "Aureon has customer adoption in regulated sectors."
    _write(candidate / "index.html", f"<title>Aureon</title><main><p>{unsafe}</p></main>")
    context = _context()
    preview = _preview(baseline, candidate, paths=["index.html"], context=context)
    manifest = _manifest_from_preview(
        preview,
        kinds={public_text_sha256(unsafe): ("non-claim", "")},
    )

    result = evaluate_candidate_claim_surface(
        baseline_site=baseline,
        candidate_site=candidate,
        changed_paths=["index.html"],
        context=context,
        manifest=manifest,
    )

    assert result["passed"] is False
    check = next(item for item in result["checks"] if item["id"] == "route-permitted-wording-and-boundaries")
    assert check["passed"] is False
    assert unsafe not in json.dumps(result)


def test_commercial_wedge_copy_cannot_be_disguised_as_non_claim(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    _write(baseline / "index.html", "<title>Aureon</title><main><p>Existing record.</p></main>")
    unsafe = "Evidence OS is the first wedge."
    _write(candidate / "index.html", f"<title>Aureon</title><main><p>{unsafe}</p></main>")
    context = _context()
    preview = _preview(baseline, candidate, paths=["index.html"], context=context)
    manifest = _manifest_from_preview(
        preview,
        kinds={public_text_sha256(unsafe): ("non-claim", "")},
    )

    result = evaluate_candidate_claim_surface(
        baseline_site=baseline,
        candidate_site=candidate,
        changed_paths=["index.html"],
        context=context,
        manifest=manifest,
    )

    assert result["passed"] is False
    check = next(item for item in result["checks"] if item["id"] == "route-permitted-wording-and-boundaries")
    assert check["passed"] is False
    assert check["evidence"]["unsafe_non_claim_surface_count"] == 1
    assert unsafe not in json.dumps(result)


def test_existing_route_boundary_cannot_be_removed_from_changed_surface(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    boundary = "This fixture is not evidence of customer adoption or independent validation."
    _write(
        baseline / "index.html",
        f"<title>Aureon</title><main><p>Existing record.</p><p>{boundary}</p></main>",
    )
    label = "Read the source record."
    _write(
        candidate / "index.html",
        f"<title>Aureon</title><main><p>Existing record.</p><a>{label}</a></main>",
    )
    context = _context()
    preview = _preview(baseline, candidate, paths=["index.html"], context=context)
    manifest = _manifest_from_preview(
        preview,
        kinds={public_text_sha256(label): ("non-claim", "")},
    )

    result = evaluate_candidate_claim_surface(
        baseline_site=baseline,
        candidate_site=candidate,
        changed_paths=["index.html"],
        context=context,
        manifest=manifest,
    )

    assert result["passed"] is False
    check = next(item for item in result["checks"] if item["id"] == "existing-route-boundary-preservation")
    assert check["passed"] is False
    assert check["evidence"]["removed_boundary_count"] == 1
    assert check["evidence"]["affected_claim_count"] == 1
    assert boundary not in json.dumps(result)


def test_missing_duplicate_or_mismatched_manifest_entries_fail_closed(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    _write(baseline / "index.html", "<title>Aureon</title><main>Existing.</main>")
    permitted = "Aureon is an evidence-led test company."
    _write(candidate / "index.html", f"<title>Aureon</title><main>{permitted}</main>")
    context = _context()
    preview = _preview(baseline, candidate, paths=["index.html"], context=context)
    manifest = _manifest_from_preview(
        preview,
        kinds={public_text_sha256(permitted): ("permitted-wording", "homepage-claim")},
    )

    missing = evaluate_candidate_claim_surface(
        baseline_site=baseline,
        candidate_site=candidate,
        changed_paths=["index.html"],
        context=context,
        manifest=[],
    )
    assert missing["passed"] is False

    duplicate = evaluate_candidate_claim_surface(
        baseline_site=baseline,
        candidate_site=candidate,
        changed_paths=["index.html"],
        context=context,
        manifest=manifest + manifest,
    )
    assert duplicate["passed"] is False

    mismatched = [dict(manifest[0])]
    mismatched[0]["claim_id"] = "wrong-route-claim"
    result = evaluate_candidate_claim_surface(
        baseline_site=baseline,
        candidate_site=candidate,
        changed_paths=["index.html"],
        context=context,
        manifest=mismatched,
    )
    assert result["passed"] is False

    unsafe_rationale = "Aureon has customer adoption in regulated sectors."
    raw_rationale = [dict(manifest[0])]
    raw_rationale[0]["rationale"] = unsafe_rationale
    result = evaluate_candidate_claim_surface(
        baseline_site=baseline,
        candidate_site=candidate,
        changed_paths=["index.html"],
        context=context,
        manifest=raw_rationale,
    )
    assert result["passed"] is False
    assert unsafe_rationale not in json.dumps(result)


def test_dynamic_javascript_copy_is_not_silently_accepted(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    _write(baseline / "script.js", "const label = 'Existing label';\n")
    _write(candidate / "script.js", "const label = `Aureon ${status}`;\n")
    result = _preview(baseline, candidate, paths=["script.js"], context=_context())

    assert result["passed"] is False
    check = next(item for item in result["checks"] if item["id"] == "static-public-text-audit")
    assert check["passed"] is False


def test_css_only_candidate_needs_an_explicit_empty_surface_manifest(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    _write(baseline / "styles.css", "body { color: #111; }\n")
    _write(candidate / "styles.css", "body { color: #222; }\n")

    result = evaluate_candidate_claim_surface(
        baseline_site=baseline,
        candidate_site=candidate,
        changed_paths=["styles.css"],
        context=_context(),
        manifest=[],
    )

    assert result["passed"] is True
    assert result["summary"]["new_public_surface_count"] == 0
