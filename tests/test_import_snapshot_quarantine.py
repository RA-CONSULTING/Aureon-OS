"""Keep historical imported checkouts outside every canonical runtime path."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
IMPORTS = ROOT / "imports"
ARCHIVE = ROOT / "archive"
SNAPSHOT = IMPORTS / "Kimi_Agent_Aureon_20260408" / "aureon-trading-main-snapshot"
SNAPSHOT_PREFIX = "imports/Kimi_Agent_Aureon_20260408/aureon-trading-main-snapshot/"

CANONICAL_NAVIGATION_SOURCES = (
    "CAPABILITIES.md",
    "QUICK_START.md",
    "RUNNING.md",
    "docs/REPO_SITEMAP.md",
    "docs/SAAS_INTEGRATION_READINESS.md",
    "scripts/validation/generate_saas_integration_manifest.py",
    "docs/end_user_access_map.json",
    "frontend/public/aureon_end_user_access_map.json",
    "docs/repo_sitemap.json",
    "frontend/public/aureon_repo_sitemap.json",
)

TEXT_CONTROL_SUFFIXES = {
    ".cmd",
    ".conf",
    ".dockerfile",
    ".json",
    ".mjs",
    ".ps1",
    ".py",
    ".sh",
    ".toml",
    ".yaml",
    ".yml",
}

WALK_EXCLUSIONS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "archive",
    "imports",
    "node_modules",
    "venv",
}

FORBIDDEN_QUARANTINE_PATH = re.compile(
    r"(?i)(?<![a-z0-9_])(?:\.\.?/)*?(?:imports|archive)(?:/|$)"
)
FORBIDDEN_QUARANTINE_IMPORT = re.compile(
    r"(?im)^\s*(?:from|import)\s+(?:imports|archive)(?:\.|\s|$)"
)
FORBIDDEN_QUARANTINE_SELECTOR = re.compile(
    r"""(?im)
    (?:
        \b(?:context|cwd|workdir|working_dir|source_dir)\b\s*[:=]
        | ^\s*(?:copy|add|cd|pushd)\b
        | \bsys\.path\b
        | \bpythonpath\b
    )
    [^\n\#]*
    (?<![a-z0-9_])(?:imports|archive)(?:/|(?=[\"'\s,)}\]]|$))
    """,
    re.VERBOSE,
)


def _normalized_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace").replace("\\", "/")


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _has_quarantined_runtime_reference(text: str) -> bool:
    normalized = text.replace("\\", "/")
    return bool(
        FORBIDDEN_QUARANTINE_PATH.search(normalized)
        or FORBIDDEN_QUARANTINE_IMPORT.search(normalized)
        or FORBIDDEN_QUARANTINE_SELECTOR.search(normalized)
    )


def _active_files() -> list[Path]:
    files: list[Path] = []
    for directory, child_dirs, child_files in os.walk(ROOT):
        child_dirs[:] = [name for name in child_dirs if name not in WALK_EXCLUSIONS]
        base = Path(directory)
        files.extend(base / name for name in child_files)
    return files


def _runtime_control_files() -> list[Path]:
    files: set[Path] = set()
    for path in _active_files():
        relative = path.relative_to(ROOT)
        normalized = str(relative).replace("\\", "/")
        name_lower = path.name.lower()
        suffix = path.suffix.lower()
        in_control_tree = normalized.startswith(
            (
                ".do/",
                ".github/workflows/",
                "deploy/",
                "packaging/",
                "scripts/launchers/",
                "scripts/runners/",
            )
        )
        is_launcher = (
            "launcher" in name_lower
            and suffix in {".cmd", ".ps1", ".py", ".sh"}
            and not normalized.startswith(("docs/", "tests/"))
        )
        is_packaging_control = (
            name_lower.startswith("dockerfile")
            or suffix == ".dockerfile"
            or (
                name_lower.startswith("docker-compose")
                and suffix in {".yaml", ".yml"}
            )
            or (name_lower.startswith("supervisord") and suffix == ".conf")
            or name_lower == "package.json"
        )
        is_root_control = (
            relative.parent == Path(".")
            and path.name in {"Procfile", "app.yaml", "package.json", "pyproject.toml"}
        )
        if (
            is_packaging_control
            or is_root_control
            or is_launcher
            or (
                in_control_tree
                and (suffix in TEXT_CONTROL_SUFFIXES or path.name == "Procfile")
            )
        ):
            files.add(path)
    return sorted(files)


def _compose_files() -> list[Path]:
    return sorted(
        path
        for path in _active_files()
        if path.name.lower().startswith("docker-compose")
        and path.suffix.lower() in {".yaml", ".yml"}
    )


def test_root_docker_contexts_exclude_historical_trees() -> None:
    rules = {
        line.strip().replace("\\", "/").strip("/")
        for line in (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    assert {"imports", "archive"} <= rules

    contexts: list[tuple[Path, Path]] = []
    for compose_path in _compose_files():
        document = yaml.safe_load(compose_path.read_text(encoding="utf-8")) or {}
        for service_name, service in (document.get("services") or {}).items():
            build = service.get("build") if isinstance(service, dict) else None
            if not build:
                continue
            raw_context = build if isinstance(build, str) else build.get("context", ".")
            context = (compose_path.parent / str(raw_context)).resolve()
            contexts.append((compose_path, context))
            assert context.is_dir(), f"{compose_path}:{service_name} has a missing build context"

    for app_spec in (ROOT / "app.yaml", ROOT / ".do" / "app.yaml"):
        document = yaml.safe_load(app_spec.read_text(encoding="utf-8")) or {}
        for service in document.get("services") or []:
            if not isinstance(service, dict) or not service.get("dockerfile_path"):
                continue
            raw_source = str(service.get("source_dir", "."))
            context = (
                ROOT.resolve()
                if raw_source in {".", "/"}
                else (ROOT / raw_source.lstrip("/")).resolve()
            )
            contexts.append((app_spec, context))
            assert context.is_dir(), f"{app_spec} has a missing source_dir {raw_source!r}"

    assert contexts, "expected canonical Compose build contexts"
    for compose_path, context in contexts:
        for quarantined in (IMPORTS.resolve(), ARCHIVE.resolve()):
            if _is_relative_to(quarantined, context):
                assert context == ROOT.resolve(), (
                    f"{compose_path} uses a context containing {quarantined} without the "
                    "repository-root quarantine boundary"
                )


def test_runtime_controls_never_select_quarantined_source() -> None:
    findings: list[str] = []

    controls = _runtime_control_files()
    assert controls
    for path in controls:
        text = _normalized_text(path)
        if _has_quarantined_runtime_reference(text):
            findings.append(str(path.relative_to(ROOT)).replace("\\", "/"))

    assert findings == [], (
        "canonical runtime controls reference quarantined source; documentation and audit "
        f"references are allowed, executable controls are not: {findings}"
    )


def test_runtime_reference_detector_rejects_nested_build_and_launch_paths() -> None:
    adversarial_controls = (
        "services:\n  app:\n    build:\n      context: imports/Kimi_Agent_Aureon_20260408",
        "COPY archive/release-candidate /app",
        "sys.path.insert(0, str(ROOT / 'imports' / 'Kimi_Agent_Aureon_20260408'))",
        "working_dir: ./imports/Kimi_Agent_Aureon_20260408",
        "PYTHONPATH=C:\\repo\\imports\\Kimi_Agent_Aureon_20260408",
        "from imports.Kimi_Agent_Aureon_20260408 import launcher",
    )
    assert all(_has_quarantined_runtime_reference(text) for text in adversarial_controls)

    controls = set(_runtime_control_files())
    evidence_doc = ROOT / "docs" / "REPO_SITEMAP.md"
    assert evidence_doc not in controls
    assert "imports/" in _normalized_text(evidence_doc)


def test_production_commands_have_no_quarantined_working_directory() -> None:
    assignment = re.compile(
        r"(?i)\b(?:cwd|workdir|working_dir|source_dir)\b\s*[:=]\s*[^\n#]*(?:imports|archive)(?:[/\s]|$)"
    )
    shell_change = re.compile(r"(?im)^\s*(?:cd|pushd)\s+[^\n]*(?:imports|archive)(?:/|\s|$)")
    findings: list[str] = []
    for path in _runtime_control_files():
        text = _normalized_text(path)
        if assignment.search(text) or shell_change.search(text):
            findings.append(str(path.relative_to(ROOT)).replace("\\", "/"))
    assert findings == [], f"production controls enter a quarantined working directory: {findings}"


def test_snapshot_launchers_are_absent_from_canonical_navigation() -> None:
    assert SNAPSHOT.is_dir()
    nested_controls = [
        path
        for path in SNAPSHOT.rglob("*")
        if path.is_file()
        and (
            path.name.startswith("Dockerfile")
            or path.name in {"Procfile", "package.json"}
            or path.suffix.lower() in {".cmd", ".ps1", ".sh"}
            or "launcher" in path.name.lower()
        )
    ]
    assert nested_controls, "the runnable historical checkout was not found"

    source_texts = {
        relative: _normalized_text(ROOT / relative)
        for relative in CANONICAL_NAVIGATION_SOURCES
    }
    exact_nested_paths = {
        SNAPSHOT_PREFIX + str(path.relative_to(SNAPSHOT)).replace("\\", "/")
        for path in nested_controls
    }
    selected = {
        f"{source}:{nested}"
        for source, text in source_texts.items()
        for nested in exact_nested_paths
        if nested.lower() in text.lower()
    }
    assert selected == set()

    from scripts.validation import validate_repo_navigation_contract as navigation

    assert tuple(CANONICAL_NAVIGATION_SOURCES) == navigation.LAUNCHER_NAVIGATION_SOURCES
    for launcher in navigation.CANONICAL_LAUNCHER_PATHS:
        resolved = (ROOT / launcher).resolve()
        assert resolved.is_file()
        assert _is_relative_to(resolved, (ROOT / "scripts" / "launchers").resolve())
        assert not _is_relative_to(resolved, IMPORTS.resolve())


def test_quarantine_policy_is_explicit_and_snapshot_is_not_a_package_script() -> None:
    policy = _normalized_text(IMPORTS / "README_QUARANTINED.md").lower()
    for required in (
        "evidence only",
        "not part of the canonical aureon runtime",
        "do not run",
        "pythonpath",
        "working directory",
        "does not by itself reclassify its economic-mutation sites",
    ):
        assert required in policy

    root_package = ROOT / "package.json"
    if root_package.is_file():
        scripts = json.loads(root_package.read_text(encoding="utf-8")).get("scripts", {})
        assert SNAPSHOT_PREFIX.lower() not in json.dumps(scripts).replace("\\", "/").lower()
