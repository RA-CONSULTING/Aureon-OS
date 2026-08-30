from __future__ import annotations

import ast
import json
import os
from pathlib import Path
from typing import Any

import pytest

from aureon.operator import design_motion_performance_budget as budget
from aureon.operator import secure_immutable_artifact
from aureon.operator.design_motion_performance_budget import (
    AUTHORITY,
    CONFIG_SCHEMA,
    DesignMotionPerformanceBudgetError,
    audit_motion_performance_budget,
    snapshot_static_tree,
    validate_motion_performance_receipt,
)

_IMPLEMENTATION_SOURCE = Path(budget.__file__).resolve()
_SECURE_WRITER_SOURCE = Path(str(secure_immutable_artifact.__file__)).resolve()


def _write(path: Path, value: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, bytes):
        path.write_bytes(value)
    else:
        path.write_text(value, encoding="utf-8", newline="\n")


def _thresholds() -> dict[str, int]:
    return {
        "max_total_bytes": 1_000_000,
        "max_html_bytes": 200_000,
        "max_css_bytes": 200_000,
        "max_javascript_bytes": 200_000,
        "max_image_bytes": 500_000,
        "max_font_bytes": 500_000,
        "max_media_bytes": 0,
        "max_other_bytes": 100_000,
        "max_single_asset_bytes": 300_000,
        "max_animation_duration_ms": 800,
        "min_transition_duration_ms": 80,
        "max_transition_duration_ms": 500,
        "max_reduced_motion_duration_ms": 1,
        "max_animation_declarations": 20,
        "max_transition_declarations": 40,
        "max_remote_resource_references": 0,
        "max_embedded_data_bytes": 0,
    }


def _policy() -> dict[str, str]:
    return {
        "autoplay_media": "forbid",
        "infinite_animation": "forbid",
        "dynamic_motion": "forbid",
        "reduced_motion_override": "required",
        "undeclared_remote_origins": "forbid",
    }


def _make_repo(
    tmp_path: Path,
    *,
    source_relative: str = "website",
    html: str | None = None,
    css: str | None = None,
    javascript: str | None = None,
) -> tuple[Path, Path]:
    root = tmp_path / "repo"
    _write(root / "pyproject.toml", "[project]\nname='motion-budget-test'\n")
    _write(root / "aureon/__init__.py", "")
    _write(root / "aureon/operator/__init__.py", "")
    implementation = _IMPLEMENTATION_SOURCE.read_bytes()
    _write(root / budget.MODULE_PATH, implementation)
    budget.__file__ = str(root / budget.MODULE_PATH)
    secure_writer = _SECURE_WRITER_SOURCE.read_bytes()
    _write(root / budget.SECURE_WRITER_PATH, secure_writer)
    secure_immutable_artifact.__file__ = str(root / budget.SECURE_WRITER_PATH)
    doctrine_source = (
        Path(__file__).resolve().parents[1]
        / "skills/aureon-harmonic-design-suite/references/design-doctrine.md"
    )
    _write(root / budget.DOCTRINE_PATH, doctrine_source.read_bytes())
    source = root / source_relative
    _write(
        source / "index.html",
        html
        or """<!doctype html>
<html lang="en"><head>
<link rel="stylesheet" href="styles.css">
<title>Evidence</title></head><body><main class="hero card">Evidence</main></body></html>
""",
    )
    _write(
        source / "styles.css",
        css
        or """@keyframes reveal { from { opacity: 0; } to { opacity: 1; } }
.hero { animation: reveal 700ms ease-out 1; }
.card { transition: opacity 200ms ease; }
@media (prefers-reduced-motion: reduce) {
  .hero { animation: none; }
  .card { transition: none; }
}
""",
    )
    if javascript is not None:
        _write(source / "app.js", javascript)
    return root, source


def _write_config(
    root: Path,
    source: Path,
    *,
    thresholds: dict[str, int] | None = None,
    allowed_origins: list[str] | None = None,
    allow_data_urls: bool = False,
    source_kind: str | None = None,
) -> Path:
    binding = snapshot_static_tree(source, repo_root=root)
    doctrine_sha = budget._bytes_sha256((root / budget.DOCTRINE_PATH).read_bytes())
    relative_source = source.relative_to(root).as_posix()
    config = {
        "schema": CONFIG_SCHEMA,
        "source": {
            "kind": source_kind or str(binding["kind"]),
            "root": relative_source,
            "tree_sha256": binding["tree_sha256"],
        },
        "doctrine": {
            "path": budget.DOCTRINE_PATH,
            "sha256": doctrine_sha,
        },
        "thresholds": thresholds or _thresholds(),
        "remote_origins": {
            "allowed": allowed_origins or [],
            "allow_data_urls": allow_data_urls,
        },
        "policy": _policy(),
    }
    path = root / "data/website_operator/motion-budget.v1.json"
    _write(path, json.dumps(config, indent=2, sort_keys=True) + "\n")
    return path


def _write_receipt(root: Path, receipt: dict[str, Any], name: str = "receipt.json") -> Path:
    path = root / "artifacts/website-operator/motion-performance-budget" / name
    _write(path, budget._canonical_json_bytes(receipt))
    return path


def _codes(receipt: dict[str, Any]) -> set[str]:
    return {str(item["code"]) for item in receipt["findings"]}


def test_passing_audit_is_deterministic_local_and_exactly_replayable(tmp_path: Path) -> None:
    root, source = _make_repo(tmp_path)
    config = _write_config(root, source)
    before = snapshot_static_tree(source, repo_root=root)

    first = audit_motion_performance_budget(config, repo_root=root)
    second = audit_motion_performance_budget(config, repo_root=root)

    assert first == second
    assert first["decision"] == {
        "status": "pass",
        "blocker_count": 0,
        "finding_set_sha256": budget._json_sha256([]),
        "eligible_for_next_local_gate": True,
        "audit_evidence_only": True,
    }
    assert first["authority"] == AUTHORITY
    assert first["authority"]["network_access"] == "none"
    assert first["authority"]["package_authority"] == "none"
    assert first["authority"]["deployment_authority"] == "none"
    assert first["limitations"] == list(budget.STATIC_LIMITATIONS)
    assert first["measurements"]["motion"]["animation_durations"]["maximum_ms"] == 700
    assert first["measurements"]["motion"]["transition_durations"]["maximum_ms"] == 200
    assert first["source"]["expected_tree_sha256"] == before["tree_sha256"]
    assert first["source"]["observed_tree_sha256"] == before["tree_sha256"]
    assert snapshot_static_tree(source, repo_root=root) == before

    output = Path("artifacts/website-operator/motion-performance-budget/pass.json")
    written = audit_motion_performance_budget(
        config,
        repo_root=root,
        output_path=output,
    )
    assert written == first
    assert validate_motion_performance_receipt(output, repo_root=root) == first
    assert snapshot_static_tree(source, repo_root=root) == before


def test_implementation_binding_rejects_repo_copy_that_is_not_loaded_bytes(
    tmp_path: Path,
) -> None:
    root, source = _make_repo(tmp_path)
    config = _write_config(root, source)
    module_path = root / budget.MODULE_PATH
    _write(module_path, module_path.read_bytes() + b"\n# altered after load\n")

    with pytest.raises(
        DesignMotionPerformanceBudgetError,
        match="differ from the source bytes loaded",
    ):
        audit_motion_performance_budget(config, repo_root=root)


def test_implementation_binding_rejects_immutable_writer_drift(tmp_path: Path) -> None:
    root, source = _make_repo(tmp_path)
    config = _write_config(root, source)
    writer_path = root / budget.SECURE_WRITER_PATH
    _write(writer_path, writer_path.read_bytes() + b"\n# altered after load\n")

    with pytest.raises(
        DesignMotionPerformanceBudgetError,
        match="immutable-artifact writer bytes differ",
    ):
        audit_motion_performance_budget(config, repo_root=root)


def test_module_exposes_no_network_subprocess_or_credential_reader() -> None:
    source = _IMPLEMENTATION_SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)

    assert not imported & {
        "http.client",
        "requests",
        "socket",
        "subprocess",
        "urllib.request",
    }
    assert "os.environ" not in source
    assert "os.getenv" not in source


def test_valid_vendor_property_is_inspectable_and_malformed_property_still_fails(
    tmp_path: Path,
) -> None:
    css = """button { -webkit-tap-highlight-color: transparent; }
.card { transition: opacity 200ms ease; }
@media (prefers-reduced-motion: reduce) { .card { transition: none; } }"""
    root, source = _make_repo(tmp_path, css=css)
    config = _write_config(root, source)
    assert audit_motion_performance_budget(config, repo_root=root)["decision"]["status"] == "pass"

    root_bad, source_bad = _make_repo(
        tmp_path / "bad",
        css=".bad { ?invalid-property: 1; }",
    )
    config_bad = _write_config(root_bad, source_bad)
    with pytest.raises(DesignMotionPerformanceBudgetError, match="malformed property"):
        audit_motion_performance_budget(config_bad, repo_root=root_bad)


def test_negated_reduced_motion_query_cannot_satisfy_override(tmp_path: Path) -> None:
    css = """.x { animation: pulse 200ms linear; }
@media not (prefers-reduced-motion: reduce) { .x { animation: none; } }"""
    root, source = _make_repo(tmp_path, css=css)
    config = _write_config(root, source)

    receipt = audit_motion_performance_budget(config, repo_root=root)

    assert "reduced-motion-override-missing" in _codes(receipt)
    assert receipt["decision"]["status"] == "blocked"


def test_inline_computed_autoplay_is_blocked_but_json_data_is_not_executed(
    tmp_path: Path,
) -> None:
    html = """<!doctype html><html><body>
<video oncanplay="this['play']()"></video>
</body></html>"""
    root, source = _make_repo(tmp_path, html=html, css="")
    config = _write_config(root, source)
    receipt = audit_motion_performance_budget(config, repo_root=root)
    assert "dynamic-motion-uninspectable" in _codes(receipt)

    data_html = """<!doctype html><html><body>
<script type="application/ld+json">{"action": "play", "src": "descriptive-only"}</script>
</body></html>"""
    data_root, data_source = _make_repo(tmp_path / "data", html=data_html, css="")
    data_config = _write_config(data_root, data_source)
    assert audit_motion_performance_budget(data_config, repo_root=data_root)["decision"]["status"] == "pass"


def test_scripted_remote_assignment_is_audited_and_dynamic_assignment_blocks(
    tmp_path: Path,
) -> None:
    javascript = """const pixel = new Image();
pixel.src = 'https://undeclared.example/animated.gif';"""
    root, source = _make_repo(tmp_path, javascript=javascript)
    config = _write_config(root, source)
    receipt = audit_motion_performance_budget(config, repo_root=root)
    assert "undeclared-remote-origin" in _codes(receipt)
    assert receipt["measurements"]["resources"]["remote_reference_count"] == 1

    allowed_root, allowed_source = _make_repo(
        tmp_path / "allowed",
        javascript="const pixel = new Image(); pixel.src = 'https://cdn.example/pixel.png';",
    )
    allowed_thresholds = _thresholds()
    allowed_thresholds["max_remote_resource_references"] = 1
    allowed_config = _write_config(
        allowed_root,
        allowed_source,
        thresholds=allowed_thresholds,
        allowed_origins=["https://cdn.example"],
    )
    assert (
        audit_motion_performance_budget(allowed_config, repo_root=allowed_root)["decision"]["status"]
        == "pass"
    )

    dynamic_root, dynamic_source = _make_repo(
        tmp_path / "dynamic",
        javascript="const pixel = new Image(); pixel.src = resolvePixelUrl();",
    )
    dynamic_config = _write_config(dynamic_root, dynamic_source)
    dynamic_receipt = audit_motion_performance_budget(dynamic_config, repo_root=dynamic_root)
    assert "dynamic-resource-uninspectable" in _codes(dynamic_receipt)


def test_staged_tree_path_is_supported_but_arbitrary_and_escape_paths_are_rejected(
    tmp_path: Path,
) -> None:
    root, source = _make_repo(
        tmp_path,
        source_relative="artifacts/website-candidates/run-001/website",
    )
    config = _write_config(root, source)
    receipt = audit_motion_performance_budget(config, repo_root=root)
    assert receipt["source"]["kind"] == "staged-static-tree"

    malformed = json.loads(config.read_text(encoding="utf-8"))
    malformed["source"]["root"] = "../outside"
    _write(config, json.dumps(malformed))
    with pytest.raises(DesignMotionPerformanceBudgetError, match="normalised|relative"):
        audit_motion_performance_budget(config, repo_root=root)

    malformed["source"]["root"] = "public"
    malformed["source"]["kind"] = "canonical-static-tree"
    (root / "public").mkdir()
    _write(config, json.dumps(malformed))
    with pytest.raises(DesignMotionPerformanceBudgetError, match="exactly website"):
        audit_motion_performance_budget(config, repo_root=root)


def test_motion_autoplay_remote_and_byte_vetoes_are_quantified(tmp_path: Path) -> None:
    html = """<!doctype html><html><head>
<link rel="stylesheet" href="styles.css">
<script src="https://tracker.example/app.js"></script>
</head><body><video autoplay src="film.mp4"></video>
<script>requestAnimationFrame(() => document.body.style.transform = "scale(1)")</script>
</body></html>"""
    css = """.pulse {
  animation: pulse 900ms linear infinite;
  transition: all 50ms linear;
  transform: translateX(2px);
}"""
    root, source = _make_repo(tmp_path, html=html, css=css)
    _write(source / "film.mp4", b"video")
    _write(source / "large.png", b"x" * 32)
    thresholds = _thresholds()
    thresholds.update(
        {
            "max_total_bytes": 100,
            "max_html_bytes": 100,
            "max_css_bytes": 40,
            "max_image_bytes": 10,
            "max_media_bytes": 2,
            "max_single_asset_bytes": 10,
        }
    )
    config = _write_config(root, source, thresholds=thresholds)

    receipt = audit_motion_performance_budget(config, repo_root=root)
    codes = _codes(receipt)

    assert receipt["decision"]["status"] == "blocked"
    assert {
        "autoplay-media",
        "infinite-animation",
        "animation-duration-budget-exceeded",
        "transition-duration-budget-underrun",
        "reduced-motion-override-missing",
        "dynamic-motion-uninspectable",
        "undeclared-remote-origin",
        "resource-byte-budget-exceeded",
        "single-asset-budget-exceeded",
    } <= codes
    assert receipt["measurements"]["motion"]["animation_durations"]["maximum_ms"] == 900
    assert receipt["measurements"]["motion"]["transition_durations"]["minimum_ms"] == 50
    assert receipt["measurements"]["resources"]["remote_reference_count"] == 1
    remote_findings = [item for item in receipt["findings"] if item["code"] == "undeclared-remote-origin"]
    assert remote_findings
    assert all("tracker.example" not in json.dumps(item) for item in remote_findings)


def test_declared_remote_origin_is_counted_without_network_or_release_authority(
    tmp_path: Path,
) -> None:
    html = """<!doctype html><html><head>
<script src="https://cdn.example/app.js"></script>
</head><body>Static</body></html>"""
    root, source = _make_repo(tmp_path, html=html, css="")
    thresholds = _thresholds()
    thresholds["max_remote_resource_references"] = 1
    config = _write_config(
        root,
        source,
        thresholds=thresholds,
        allowed_origins=["https://cdn.example"],
    )

    receipt = audit_motion_performance_budget(config, repo_root=root)

    assert receipt["decision"]["status"] == "pass"
    assert receipt["measurements"]["resources"]["remote_reference_count"] == 1
    assert receipt["authority"]["network_access"] == "none"
    assert receipt["authority"]["release_authority"] == "none"


def test_malformed_css_and_html_fail_closed(tmp_path: Path) -> None:
    root, source = _make_repo(tmp_path, css=".broken { transition: opacity 200ms;")
    config = _write_config(root, source)
    with pytest.raises(DesignMotionPerformanceBudgetError, match="unmatched opening brace"):
        audit_motion_performance_budget(config, repo_root=root)

    root_two, source_two = _make_repo(
        tmp_path / "html",
        html="<html><head><style>.x { color: red; }</head><body></body></html>",
        css="",
    )
    config_two = _write_config(root_two, source_two)
    receipt = audit_motion_performance_budget(config_two, repo_root=root_two)
    assert receipt["decision"]["status"] == "blocked"
    assert "malformed-html" in _codes(receipt)


def test_dynamic_css_javascript_and_template_motion_are_blockers(tmp_path: Path) -> None:
    css = """.x { animation: reveal var(--duration); }
@media (prefers-reduced-motion: reduce) { .x { animation: none; } }"""
    root, source = _make_repo(
        tmp_path,
        html="<html><body>{{ runtime_component }}</body></html>",
        css=css,
        javascript="const tick = () => requestAnimationFrame(tick); tick();",
    )
    config = _write_config(root, source)

    receipt = audit_motion_performance_budget(config, repo_root=root)
    dynamic = [item for item in receipt["findings"] if item["code"] == "dynamic-motion-uninspectable"]

    assert receipt["decision"]["status"] == "blocked"
    assert len(dynamic) >= 3
    assert all("runtime_component" not in json.dumps(item) for item in dynamic)


def test_local_resource_escape_missing_resource_and_data_url_fail_closed(tmp_path: Path) -> None:
    html = """<!doctype html><html><body>
<img src="../../private.png">
<img src="missing.png">
<img src="data:image/png;base64,eA==">
</body></html>"""
    root, source = _make_repo(tmp_path, html=html, css="")
    config = _write_config(root, source)

    receipt = audit_motion_performance_budget(config, repo_root=root)

    assert "local-resource-unresolved" in _codes(receipt)
    assert "embedded-resource-not-allowed" in _codes(receipt)
    reasons = {
        item["evidence"].get("reason")
        for item in receipt["findings"]
        if item["code"] == "local-resource-unresolved"
    }
    assert {"path-escape", "missing"} <= reasons


def test_svg_motion_and_embedded_remote_resource_are_not_opaque(tmp_path: Path) -> None:
    root, source = _make_repo(tmp_path, css="")
    _write(
        source / "motion.svg",
        """<svg xmlns="http://www.w3.org/2000/svg">
<image href="https://images.example/plot.png"/>
<animate attributeName="opacity" dur="2s" repeatCount="indefinite"/>
</svg>""",
    )
    config = _write_config(root, source)

    receipt = audit_motion_performance_budget(config, repo_root=root)

    assert {
        "dynamic-motion-uninspectable",
        "infinite-animation",
        "undeclared-remote-origin",
    } <= _codes(receipt)


def test_stale_source_and_doctrine_hashes_refuse_to_issue_receipt(tmp_path: Path) -> None:
    root, source = _make_repo(tmp_path)
    config = _write_config(root, source)
    _write(source / "index.html", "<html><body>changed</body></html>")
    with pytest.raises(DesignMotionPerformanceBudgetError, match="source tree hash is stale"):
        audit_motion_performance_budget(config, repo_root=root)

    root_two, source_two = _make_repo(tmp_path / "doctrine")
    config_two = _write_config(root_two, source_two)
    _write(root_two / budget.DOCTRINE_PATH, "# altered doctrine\n")
    with pytest.raises(DesignMotionPerformanceBudgetError, match="doctrine hash is stale"):
        audit_motion_performance_budget(config_two, repo_root=root_two)


def test_duplicate_json_keys_are_rejected_in_config_and_receipt(tmp_path: Path) -> None:
    root, source = _make_repo(tmp_path)
    config = _write_config(root, source)
    original = config.read_text(encoding="utf-8")
    duplicate = original.replace(
        "{\n",
        '{\n  "schema": "aureon.design-motion-performance-budget-config.v1",\n',
        1,
    )
    _write(config, duplicate)
    with pytest.raises(DesignMotionPerformanceBudgetError, match="duplicate object key"):
        audit_motion_performance_budget(config, repo_root=root)

    config = _write_config(root, source)
    receipt = audit_motion_performance_budget(config, repo_root=root)
    receipt_path = _write_receipt(root, receipt)
    receipt_text = receipt_path.read_text(encoding="utf-8")
    duplicate_receipt = receipt_text.replace(
        "{",
        '{"schema":"aureon.design-motion-performance-budget.v1",',
        1,
    )
    _write(receipt_path, duplicate_receipt)
    with pytest.raises(DesignMotionPerformanceBudgetError, match="duplicate object key"):
        validate_motion_performance_receipt(receipt_path, repo_root=root)


def test_authority_smuggling_is_rejected_even_with_recomputed_self_hash(tmp_path: Path) -> None:
    root, source = _make_repo(tmp_path)
    config = _write_config(root, source)
    receipt = audit_motion_performance_budget(config, repo_root=root)
    receipt["authority"] = dict(receipt["authority"])
    receipt["authority"]["release_authority"] = "granted"
    unsigned = dict(receipt)
    del unsigned["receipt_sha256"]
    receipt["receipt_sha256"] = budget._json_sha256(unsigned)
    receipt_path = _write_receipt(root, receipt)

    with pytest.raises(DesignMotionPerformanceBudgetError, match="authority boundary"):
        validate_motion_performance_receipt(receipt_path, repo_root=root)

    honest = audit_motion_performance_budget(config, repo_root=root)
    honest["limitations"] = []
    unsigned_limitations = dict(honest)
    del unsigned_limitations["receipt_sha256"]
    honest["receipt_sha256"] = budget._json_sha256(unsigned_limitations)
    limitation_path = _write_receipt(root, honest, name="limitation-smuggling.json")
    with pytest.raises(DesignMotionPerformanceBudgetError, match="limitations"):
        validate_motion_performance_receipt(limitation_path, repo_root=root)

    config_value = json.loads(config.read_text(encoding="utf-8"))
    config_value["release_authority"] = "granted"
    _write(config, json.dumps(config_value))
    with pytest.raises(DesignMotionPerformanceBudgetError, match="keys are not exact"):
        audit_motion_performance_budget(config, repo_root=root)


def test_receipt_replay_rejects_stale_source_config_and_noncanonical_encoding(
    tmp_path: Path,
) -> None:
    root, source = _make_repo(tmp_path)
    config = _write_config(root, source)
    receipt = audit_motion_performance_budget(config, repo_root=root)
    receipt_path = _write_receipt(root, receipt)

    _write(source / "extra.txt", "drift")
    with pytest.raises(DesignMotionPerformanceBudgetError, match="source tree hash is stale"):
        validate_motion_performance_receipt(receipt_path, repo_root=root)

    root_two, source_two = _make_repo(tmp_path / "encoding")
    config_two = _write_config(root_two, source_two)
    receipt_two = audit_motion_performance_budget(config_two, repo_root=root_two)
    pretty = root_two / "artifacts/website-operator/motion-performance-budget/pretty.json"
    _write(pretty, json.dumps(receipt_two, indent=2, sort_keys=True) + "\n")
    with pytest.raises(DesignMotionPerformanceBudgetError, match="canonical deterministic"):
        validate_motion_performance_receipt(pretty, repo_root=root_two)


def test_thresholds_cannot_weaken_doctrine_and_source_kind_is_exact(tmp_path: Path) -> None:
    root, source = _make_repo(tmp_path)
    thresholds = _thresholds()
    thresholds["max_animation_duration_ms"] = 801
    config = _write_config(root, source, thresholds=thresholds)
    with pytest.raises(DesignMotionPerformanceBudgetError, match="800ms"):
        audit_motion_performance_budget(config, repo_root=root)

    config = _write_config(root, source, source_kind="staged-static-tree")
    with pytest.raises(DesignMotionPerformanceBudgetError, match="kind does not match"):
        audit_motion_performance_budget(config, repo_root=root)


def test_source_symlink_or_reparse_point_is_rejected_where_supported(
    tmp_path: Path,
) -> None:
    root, source = _make_repo(tmp_path)
    target = root / "outside.css"
    _write(target, ".x {}")
    link = source / "linked.css"
    try:
        link.symlink_to(target)
    except OSError as exc:
        pytest.skip(f"File symlinks are unavailable on this host: {exc}")
    with pytest.raises(DesignMotionPerformanceBudgetError, match="symbolic link|reparse"):
        snapshot_static_tree(source, repo_root=root)


def test_source_hard_link_is_rejected_where_supported(tmp_path: Path) -> None:
    root, source = _make_repo(tmp_path)
    linked = source / "styles-copy.css"
    try:
        os.link(source / "styles.css", linked)
    except OSError as exc:
        pytest.skip(f"Hard links are unavailable on this host: {exc}")
    with pytest.raises(DesignMotionPerformanceBudgetError, match="single-link"):
        snapshot_static_tree(source, repo_root=root)


def test_reparse_detection_is_fail_closed_without_needing_host_reparse_support(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, source = _make_repo(tmp_path)
    original = budget._is_link_or_reparse

    def mark_styles(path: Path) -> bool:
        return path.name == "styles.css" or original(path)

    monkeypatch.setattr(budget, "_is_link_or_reparse", mark_styles)
    with pytest.raises(DesignMotionPerformanceBudgetError, match="reparse"):
        snapshot_static_tree(source, repo_root=root)


def test_receipt_output_cannot_escape_artifacts_or_overwrite_existing_evidence(
    tmp_path: Path,
) -> None:
    root, source = _make_repo(tmp_path)
    config = _write_config(root, source)
    with pytest.raises(DesignMotionPerformanceBudgetError, match="must stay below"):
        audit_motion_performance_budget(
            config,
            repo_root=root,
            output_path=Path("website/audit.json"),
        )

    output = Path("artifacts/website-operator/motion-performance-budget/immutable.json")
    audit_motion_performance_budget(config, repo_root=root, output_path=output)
    with pytest.raises(DesignMotionPerformanceBudgetError, match="must not already exist"):
        audit_motion_performance_budget(config, repo_root=root, output_path=output)


@pytest.mark.skipif(os.name != "nt", reason="NTFS alternate data streams are Windows-specific")
def test_output_and_receipt_verifier_reject_ntfs_alternate_stream_paths(
    tmp_path: Path,
) -> None:
    root, source = _make_repo(tmp_path)
    config = _write_config(root, source)
    base = root / "artifacts/website-operator/motion-performance-budget/receipt.json"
    receipt = audit_motion_performance_budget(config, repo_root=root)
    _write(base, budget._canonical_json_bytes(receipt))

    with pytest.raises(
        DesignMotionPerformanceBudgetError,
        match="alternate data stream",
    ):
        audit_motion_performance_budget(
            config,
            repo_root=root,
            output_path=Path(f"{base}:worker"),
        )
    with pytest.raises(
        DesignMotionPerformanceBudgetError,
        match="alternate data stream",
    ):
        validate_motion_performance_receipt(
            Path(f"{base}:worker"),
            repo_root=root,
        )
