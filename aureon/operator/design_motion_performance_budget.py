"""Deterministic local motion and resource-budget evidence for Aureon websites.

This control inspects one exact canonical or staged static website tree.  It
does not open a network connection, execute website code, mutate either source
tree, create a candidate, package a release, access credentials, or deploy.

The audit deliberately fails closed when CSS, HTML, SVG, or JavaScript motion
cannot be inspected statically.  A passing receipt is one local design-council
input only; browser performance, interaction parity, human visual review,
package closure, backup, owner approval, deployment, and live read-back remain
separate gates.

This generic configuration interface is not the staged-candidate policy gate.
Candidate orchestration must use the fixed candidate motion-policy compiler;
a worker-selected generic configuration cannot satisfy that gate.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import os
import re
import stat
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any, Final, Mapping, NoReturn, Sequence
from urllib.parse import unquote_to_bytes, urlsplit

from aureon.operator import secure_immutable_artifact

CONFIG_SCHEMA: Final = "aureon.design-motion-performance-budget-config.v1"
RECEIPT_SCHEMA: Final = "aureon.design-motion-performance-budget.v1"
TREE_ALGORITHM: Final = "sha256(canonical-json([{path,bytes,sha256}]), paths sorted)"
CANDIDATE_TREE_ALGORITHM: Final = (
    "sha256(canonical-json-without-trailing-newline([{path,bytes,sha256}]), paths sorted)"
)
DOCTRINE_PATH: Final = "skills/aureon-harmonic-design-suite/references/design-doctrine.md"
MODULE_PATH: Final = "aureon/operator/design_motion_performance_budget.py"
SECURE_WRITER_PATH: Final = "aureon/operator/secure_immutable_artifact.py"

AUTHORITY: Final[Mapping[str, object]] = MappingProxyType(
    {
        "scope": "deterministic local static-tree motion and resource-budget evidence only",
        "audit_evidence_only": True,
        "candidate_authority": "none",
        "canonical_mutation_authority": "none",
        "package_authority": "none",
        "release_authority": "none",
        "deployment_authority": "none",
        "credential_access": "none",
        "network_access": "none",
        "human_visual_acceptance": "still required for material visual changes",
        "browser_performance_evidence": "still required",
    }
)
STATIC_LIMITATIONS: Final[tuple[str, ...]] = (
    "static-source-analysis-not-browser-execution",
    "css-cascade-computed-style-and-frame-timing-not-proven",
    "javascript-coverage-is-conservative-pattern-analysis-not-general-program-proof",
    "remote-response-bytes-availability-and-runtime-effects-not-fetched-or-proven",
    "pointer-keyboard-history-resize-and-viewport-parity-not-proven",
    "visual-purpose-quality-and-human-acceptance-not-proven",
    "gif-and-apng-autoplay-classification-is-extension-conservative",
    "svg-finding-line-attribution-is-file-level",
)

_CONFIG_KEYS: Final = frozenset({"schema", "source", "doctrine", "thresholds", "remote_origins", "policy"})
_SOURCE_KEYS: Final = frozenset({"kind", "root", "tree_sha256"})
_DOCTRINE_KEYS: Final = frozenset({"path", "sha256"})
_THRESHOLD_KEYS: Final = frozenset(
    {
        "max_total_bytes",
        "max_html_bytes",
        "max_css_bytes",
        "max_javascript_bytes",
        "max_image_bytes",
        "max_font_bytes",
        "max_media_bytes",
        "max_other_bytes",
        "max_single_asset_bytes",
        "max_animation_duration_ms",
        "min_transition_duration_ms",
        "max_transition_duration_ms",
        "max_reduced_motion_duration_ms",
        "max_animation_declarations",
        "max_transition_declarations",
        "max_remote_resource_references",
        "max_embedded_data_bytes",
    }
)
_REMOTE_KEYS: Final = frozenset({"allowed", "allow_data_urls"})
_POLICY_KEYS: Final = frozenset(
    {
        "autoplay_media",
        "infinite_animation",
        "dynamic_motion",
        "reduced_motion_override",
        "undeclared_remote_origins",
    }
)
_FIXED_POLICY: Final[Mapping[str, str]] = MappingProxyType(
    {
        "autoplay_media": "forbid",
        "infinite_animation": "forbid",
        "dynamic_motion": "forbid",
        "reduced_motion_override": "required",
        "undeclared_remote_origins": "forbid",
    }
)
_RECEIPT_KEYS: Final = frozenset(
    {
        "schema",
        "implementation",
        "immutable_writer",
        "config",
        "doctrine",
        "source",
        "thresholds_sha256",
        "measurements",
        "checks",
        "findings",
        "decision",
        "authority",
        "limitations",
        "receipt_sha256",
    }
)
_SHA256_RE: Final = re.compile(r"[0-9A-F]{64}")
_CANDIDATE_ROOT_RE: Final = re.compile(r"artifacts/website-candidates/[a-z0-9][a-z0-9._-]{2,80}/website")
_TIME_RE: Final = re.compile(
    r"(?<![\w.-])(?P<number>[+-]?(?:\d+(?:\.\d*)?|\.\d+))(?P<unit>ms|s)\b",
    re.IGNORECASE,
)
_DYNAMIC_CSS_RE: Final = re.compile(r"(?:var|calc|env|attr)\s*\(", re.IGNORECASE)
_TEMPLATE_MARKERS: Final = ("{{", "{%", "<%", "${")
_RESOURCE_URL_RE: Final = re.compile(
    r"url\(\s*(?P<quote>['\"]?)(?P<url>.*?)(?P=quote)\s*\)", re.IGNORECASE | re.DOTALL
)
_IMPORT_URL_RE: Final = re.compile(
    r"@import\s+(?!url\s*\()(?P<quote>['\"])(?P<url>.*?)(?P=quote)",
    re.IGNORECASE | re.DOTALL,
)
_JS_RESOURCE_RE: Final = re.compile(
    r"(?:fetch|import|Worker|SharedWorker|EventSource|WebSocket|Audio)"
    r"\s*\(\s*(?P<quote>['\"])(?P<url>.*?)(?P=quote)",
    re.IGNORECASE,
)
_JS_STATIC_IMPORT_RE: Final = re.compile(
    r"\b(?:import|export)\b(?:[^;\n]*?\bfrom\s*)?(?P<quote>['\"])(?P<url>.*?)(?P=quote)",
    re.IGNORECASE,
)
_JS_MOTION_PATTERNS: Final[tuple[tuple[str, re.Pattern[str]], ...]] = (
    ("request-animation-frame", re.compile(r"\brequestAnimationFrame\s*\(")),
    ("web-animations-api", re.compile(r"(?:\.\s*animate|new\s+Animation)\s*\(")),
    ("scripted-transform", re.compile(r"\.style\.(?:transform|translate|rotate|scale)\s*=")),
    ("scripted-animation", re.compile(r"\.style\.(?:animation|transition)\s*=")),
    ("motion-library", re.compile(r"\b(?:gsap|anime)\s*\.", re.IGNORECASE)),
    (
        "scripted-autoplay-capability",
        re.compile(r"(?:\.\s*play\b|\[\s*['\"]play['\"]\s*\])"),
    ),
    (
        "scripted-autoplay-property",
        re.compile(
            r"(?:\.\s*autoplay\b|\[\s*['\"]autoplay['\"]\s*\])\s*=\s*true\b",
            re.IGNORECASE,
        ),
    ),
    (
        "scripted-autoplay-attribute",
        re.compile(
            r"\.setAttribute\s*\(\s*['\"]autoplay['\"]",
            re.IGNORECASE,
        ),
    ),
)
_JS_URL_ASSIGNMENT_RE: Final = re.compile(
    r"(?:\.\s*(?:src|href|poster)\b|\[\s*['\"](?:src|href|poster)['\"]\s*\])"
    r"\s*=\s*(?P<rhs>[^;\r\n]+)",
    re.IGNORECASE,
)
_JS_STATIC_VALUE_RE: Final = re.compile(r"^\s*(?P<quote>['\"])(?P<url>.*?)(?P=quote)")
_JS_SET_ATTRIBUTE_RE: Final = re.compile(
    r"\.setAttribute\s*\(\s*['\"](?P<attribute>src|href|poster)['\"]\s*,"
    r"\s*(?P<rhs>[^)\r\n]+)\)",
    re.IGNORECASE,
)
_JS_OPEN_RESOURCE_RE: Final = re.compile(
    r"\.open\s*\(\s*['\"][A-Z]+['\"]\s*,\s*(?P<quote>['\"])(?P<url>.*?)(?P=quote)",
    re.IGNORECASE,
)
_VOID_HTML_TAGS: Final = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)
_IMAGE_EXTENSIONS: Final = frozenset(
    {".avif", ".gif", ".ico", ".jpeg", ".jpg", ".png", ".svg", ".webp", ".apng"}
)
_FONT_EXTENSIONS: Final = frozenset({".eot", ".otf", ".ttf", ".woff", ".woff2"})
_MEDIA_EXTENSIONS: Final = frozenset(
    {".m4a", ".mov", ".mp3", ".mp4", ".oga", ".ogg", ".ogv", ".wav", ".webm"}
)
_ANIMATED_IMAGE_EXTENSIONS: Final = frozenset({".gif", ".apng"})
_MAX_FILES: Final = 20_000
_MAX_FILE_BYTES: Final = 64 * 1024 * 1024
_MAX_TREE_BYTES: Final = 512 * 1024 * 1024
_REPARSE_POINT: Final = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
_LOADED_SOURCE_SHA256: Final = hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper()
_LOADED_SECURE_WRITER_SHA256: Final = (
    hashlib.sha256(Path(str(secure_immutable_artifact.__file__)).read_bytes()).hexdigest().upper()
)


class DesignMotionPerformanceBudgetError(ValueError):
    """The source, policy, configuration, receipt, or static syntax is unsafe."""


@dataclass(frozen=True)
class _TreeFile:
    path: str
    size: int
    sha256: str
    content: bytes


@dataclass(frozen=True)
class _TreeSnapshot:
    root: Path
    files: tuple[_TreeFile, ...]
    tree_sha256: str
    total_bytes: int


@dataclass(frozen=True)
class _ResourceReference:
    source_path: str
    line: int
    value: str
    kind: str


@dataclass(frozen=True)
class _MotionRecord:
    source_path: str
    line: int
    selectors: tuple[str, ...]
    kind: str
    durations_ms: tuple[int | float, ...]


def _raise(message: str) -> NoReturn:
    raise DesignMotionPerformanceBudgetError(message)


def _canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )


def _json_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest().upper()


def _bytes_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _raise(f"JSON contains duplicate object key: {key!r}.")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> NoReturn:
    _raise(f"JSON contains a non-finite numeric constant: {value}.")


def _strict_json_from_bytes(value: bytes, *, label: str) -> dict[str, Any]:
    if value.startswith(b"\xef\xbb\xbf"):
        _raise(f"{label} must be UTF-8 without a byte-order mark.")
    try:
        text = value.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DesignMotionPerformanceBudgetError(f"{label} must be valid UTF-8.") from exc
    try:
        decoded = json.loads(
            text,
            object_pairs_hook=_strict_object,
            parse_constant=_reject_json_constant,
        )
    except json.JSONDecodeError as exc:
        raise DesignMotionPerformanceBudgetError(f"{label} is not valid JSON.") from exc
    if not isinstance(decoded, dict):
        _raise(f"{label} must be one JSON object.")
    return decoded


def _exact_keys(value: Mapping[str, Any], expected: frozenset[str], *, label: str) -> None:
    observed = frozenset(value)
    if observed != expected:
        missing = sorted(expected - observed)
        extra = sorted(observed - expected)
        _raise(f"{label} keys are not exact; missing={missing}, extra={extra}.")


def _is_link_or_reparse(path: Path) -> bool:
    try:
        details = path.lstat()
    except OSError:
        return True
    return path.is_symlink() or bool(int(getattr(details, "st_file_attributes", 0)) & _REPARSE_POINT)


def _absolute_without_resolve(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _reject_alternate_stream_path(path: Path, *, label: str) -> None:
    try:
        secure_immutable_artifact.validate_no_alternate_stream_path(path, label=label)
    except secure_immutable_artifact.SecureImmutableArtifactError as exc:
        raise DesignMotionPerformanceBudgetError(str(exc)) from exc


def _repo_root(repo_root: Path | None) -> Path:
    if repo_root is None:
        start = _absolute_without_resolve(Path.cwd())
        candidates = (start, *start.parents)
        selected = next(
            (
                item
                for item in candidates
                if (item / "pyproject.toml").is_file() and (item / "aureon").is_dir()
            ),
            None,
        )
        if selected is None:
            _raise("Could not locate the Aureon repository.")
        root = selected
    else:
        root = _absolute_without_resolve(repo_root)
    if not root.is_dir() or _is_link_or_reparse(root):
        _raise("Repository root must be an existing ordinary directory.")
    return root


def _relative_path(raw: object, *, label: str) -> PurePosixPath:
    if not isinstance(raw, str) or not raw or "\\" in raw or "\x00" in raw:
        _raise(f"{label} must be one non-empty normalised repository-relative POSIX path.")
    path = PurePosixPath(raw)
    if path.is_absolute() or path.as_posix() != raw or any(part in {"", ".", ".."} for part in path.parts):
        _raise(f"{label} must be one normalised repository-relative POSIX path.")
    for part in path.parts:
        if (
            unicodedata.normalize("NFC", part) != part
            or part.endswith((" ", "."))
            or any(ord(character) < 32 or character in '<>:"|?*' for character in part)
        ):
            _raise(f"{label} contains a non-portable or alias-prone path component.")
    return path


def _under_repo(root: Path, raw: object, *, label: str, must_exist: bool = True) -> tuple[Path, str]:
    relative = _relative_path(raw, label=label)
    candidate = root.joinpath(*relative.parts)
    current = root
    for part in relative.parts:
        current = current / part
        if current.exists() or current.is_symlink():
            if _is_link_or_reparse(current):
                _raise(f"{label} may not cross a symbolic link or reparse point.")
        elif must_exist:
            _raise(f"{label} does not exist.")
    if must_exist and not candidate.exists():
        _raise(f"{label} does not exist.")
    return candidate, relative.as_posix()


def _regular_file(root: Path, raw: object, *, label: str) -> tuple[Path, str, bytes]:
    path, relative = _under_repo(root, raw, label=label)
    if not path.is_file() or _is_link_or_reparse(path):
        _raise(f"{label} must be an ordinary file.")
    content = _read_file_stably(path, label=label)
    return path, relative, content


def _implementation_binding(root: Path) -> tuple[str, str]:
    path, relative, content = _regular_file(
        root,
        MODULE_PATH,
        label="Motion budget implementation",
    )
    executing_path = _absolute_without_resolve(Path(__file__))
    if executing_path != path or relative != MODULE_PATH:
        _raise(f"The executing motion-budget module must be the exact repository module at {MODULE_PATH}.")
    current_sha256 = _bytes_sha256(content)
    if current_sha256 != _LOADED_SOURCE_SHA256:
        _raise(
            "The motion-budget implementation bytes differ from the source bytes "
            "loaded by this Python process."
        )
    writer_path, writer_relative, writer_content = _regular_file(
        root,
        SECURE_WRITER_PATH,
        label="Immutable-artifact writer",
    )
    executing_writer_path = _absolute_without_resolve(Path(str(secure_immutable_artifact.__file__)))
    if executing_writer_path != writer_path or writer_relative != SECURE_WRITER_PATH:
        _raise(
            "The loaded immutable-artifact writer must be the exact repository "
            f"module at {SECURE_WRITER_PATH}."
        )
    writer_sha256 = _bytes_sha256(writer_content)
    if writer_sha256 != _LOADED_SECURE_WRITER_SHA256:
        _raise(
            "The immutable-artifact writer bytes differ from the source bytes loaded by this Python process."
        )
    return current_sha256, writer_sha256


def _same_file_identity(left: os.stat_result, right: os.stat_result) -> bool:
    return (
        stat.S_IFMT(left.st_mode) == stat.S_IFMT(right.st_mode)
        and int(left.st_nlink) == int(right.st_nlink)
        and int(left.st_size) == int(right.st_size)
        and int(getattr(left, "st_dev", 0)) == int(getattr(right, "st_dev", 0))
        and int(getattr(left, "st_ino", 0)) == int(getattr(right, "st_ino", 0))
        and int(getattr(left, "st_mtime_ns", 0)) == int(getattr(right, "st_mtime_ns", 0))
    )


def _read_file_stably(path: Path, *, label: str) -> bytes:
    try:
        before = path.lstat()
    except OSError as exc:
        raise DesignMotionPerformanceBudgetError(f"{label} cannot be inspected.") from exc
    if (
        _is_link_or_reparse(path)
        or not stat.S_ISREG(before.st_mode)
        or int(before.st_nlink) != 1
        or int(before.st_size) > _MAX_FILE_BYTES
    ):
        _raise(f"{label} must be a regular, single-link, reparse-free bounded file.")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise DesignMotionPerformanceBudgetError(f"{label} cannot be opened safely.") from exc
    try:
        opened = os.fstat(descriptor)
        if not _same_file_identity(before, opened):
            _raise(f"{label} changed before it could be read.")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            content = stream.read(_MAX_FILE_BYTES + 1)
        if len(content) > _MAX_FILE_BYTES:
            _raise(f"{label} exceeds the absolute inspection safety limit.")
        after_open = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    try:
        after_path = path.lstat()
    except OSError as exc:
        raise DesignMotionPerformanceBudgetError(f"{label} changed while it was read.") from exc
    if (
        not _same_file_identity(opened, after_open)
        or not _same_file_identity(before, after_path)
        or len(content) != int(before.st_size)
        or _is_link_or_reparse(path)
    ):
        _raise(f"{label} changed while it was read.")
    return content


def _source_kind(relative: str) -> str:
    if relative == "website":
        return "canonical-static-tree"
    if _CANDIDATE_ROOT_RE.fullmatch(relative):
        return "staged-static-tree"
    _raise("Source root must be exactly website or artifacts/website-candidates/<run-id>/website.")


def _walk_tree(root: Path, relative_root: str) -> _TreeSnapshot:
    if not root.is_dir() or _is_link_or_reparse(root):
        _raise("Source root must be an ordinary directory.")
    files: list[_TreeFile] = []
    seen_portable: set[str] = set()
    total_bytes = 0

    def visit(directory: Path) -> None:
        nonlocal total_bytes
        try:
            entries = sorted(os.scandir(directory), key=lambda item: item.name)
        except OSError as exc:
            raise DesignMotionPerformanceBudgetError("Source tree cannot be enumerated safely.") from exc
        for entry in entries:
            path = Path(entry.path)
            relative = path.relative_to(root).as_posix()
            _relative_path(relative, label="Source tree path")
            portable = unicodedata.normalize("NFC", relative).casefold()
            if portable in seen_portable:
                _raise("Source tree contains a case-insensitive path collision.")
            seen_portable.add(portable)
            if _is_link_or_reparse(path):
                _raise(f"Source tree contains a symbolic link or reparse point: {relative}.")
            try:
                if entry.is_dir(follow_symlinks=False):
                    visit(path)
                    continue
                if not entry.is_file(follow_symlinks=False):
                    _raise(f"Source tree contains a non-regular filesystem entry: {relative}.")
            except OSError as exc:
                raise DesignMotionPerformanceBudgetError(
                    f"Source tree entry cannot be classified safely: {relative}."
                ) from exc
            content = _read_file_stably(path, label=f"Source file {relative}")
            total_bytes += len(content)
            if len(files) >= _MAX_FILES or total_bytes > _MAX_TREE_BYTES:
                _raise("Source tree exceeds absolute inspection safety limits.")
            files.append(
                _TreeFile(
                    path=relative,
                    size=len(content),
                    sha256=_bytes_sha256(content),
                    content=content,
                )
            )

    visit(root)
    rows = [
        {"path": item.path, "bytes": item.size, "sha256": item.sha256}
        for item in sorted(files, key=lambda item: item.path)
    ]
    return _TreeSnapshot(
        root=root,
        files=tuple(sorted(files, key=lambda item: item.path)),
        tree_sha256=_json_sha256(rows),
        total_bytes=total_bytes,
    )


def snapshot_static_tree(
    source_root: Path,
    *,
    repo_root: Path | None = None,
) -> dict[str, object]:
    """Return a privacy-minimised exact tree binding for an allowed source root."""

    root = _repo_root(repo_root)
    absolute = _absolute_without_resolve(source_root if source_root.is_absolute() else root / source_root)
    try:
        relative = absolute.relative_to(root).as_posix()
    except ValueError as exc:
        raise DesignMotionPerformanceBudgetError("Source root must stay inside the repository.") from exc
    safe_root, safe_relative = _under_repo(root, relative, label="Source root")
    kind = _source_kind(safe_relative)
    snapshot = _walk_tree(safe_root, safe_relative)
    return {
        "kind": kind,
        "root": safe_relative,
        "tree_sha256": snapshot.tree_sha256,
        "file_count": len(snapshot.files),
        "total_bytes": snapshot.total_bytes,
        "algorithm": TREE_ALGORITHM,
    }


def snapshot_static_tree_dual_hash(
    source_root: Path,
    *,
    repo_root: Path | None = None,
) -> dict[str, object]:
    """Derive candidate-control and motion hashes from one captured byte manifest.

    The two historical controls use the same sorted ``path/bytes/sha256`` rows
    but different canonical JSON framing.  Reading the tree once prevents an
    A/B tree from supplying one hash to each algorithm.
    """

    root = _repo_root(repo_root)
    absolute = _absolute_without_resolve(source_root if source_root.is_absolute() else root / source_root)
    try:
        relative = absolute.relative_to(root).as_posix()
    except ValueError as exc:
        raise DesignMotionPerformanceBudgetError("Source root must stay inside the repository.") from exc
    safe_root, safe_relative = _under_repo(root, relative, label="Source root")
    kind = _source_kind(safe_relative)
    snapshot = _walk_tree(safe_root, safe_relative)
    rows = [{"path": item.path, "bytes": item.size, "sha256": item.sha256} for item in snapshot.files]
    candidate_bytes = json.dumps(
        rows,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return {
        "kind": kind,
        "root": safe_relative,
        "candidate_tree_sha256": _bytes_sha256(candidate_bytes),
        "candidate_tree_algorithm": CANDIDATE_TREE_ALGORITHM,
        "motion_tree_sha256": snapshot.tree_sha256,
        "motion_tree_algorithm": TREE_ALGORITHM,
        "captured_manifest_sha256": _bytes_sha256(_canonical_json_bytes(rows)),
        "file_count": len(snapshot.files),
        "total_bytes": snapshot.total_bytes,
    }


def _normalise_origin(value: object, *, label: str) -> str:
    if not isinstance(value, str) or value != value.strip() or not value:
        _raise(f"{label} must be one exact HTTPS origin.")
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path
        or parsed.query
        or parsed.fragment
    ):
        _raise(f"{label} must be one exact HTTPS origin without path, query, fragment, or userinfo.")
    host = parsed.hostname.lower()
    try:
        port = parsed.port
    except ValueError as exc:
        raise DesignMotionPerformanceBudgetError(f"{label} has an invalid port.") from exc
    authority = host if port in (None, 443) else f"{host}:{port}"
    normalised = f"https://{authority}"
    if value != normalised:
        _raise(f"{label} must use its lower-case canonical HTTPS origin form: {normalised}.")
    return normalised


def _validate_config(
    raw: Mapping[str, Any],
    *,
    root: Path,
    config_relative: str,
    config_path: Path,
    config_bytes: bytes,
) -> tuple[dict[str, Any], _TreeSnapshot, str, str]:
    _exact_keys(raw, _CONFIG_KEYS, label="Configuration")
    if raw.get("schema") != CONFIG_SCHEMA:
        _raise(f"Configuration schema must be {CONFIG_SCHEMA!r}.")

    source = raw.get("source")
    doctrine = raw.get("doctrine")
    thresholds = raw.get("thresholds")
    remote = raw.get("remote_origins")
    policy = raw.get("policy")
    if not isinstance(source, Mapping):
        _raise("Configuration source must be a JSON object.")
    if not isinstance(doctrine, Mapping):
        _raise("Configuration doctrine must be a JSON object.")
    if not isinstance(thresholds, Mapping):
        _raise("Configuration thresholds must be a JSON object.")
    if not isinstance(remote, Mapping):
        _raise("Configuration remote_origins must be a JSON object.")
    if not isinstance(policy, Mapping):
        _raise("Configuration sections must all be JSON objects.")
    source_map = dict(source)
    doctrine_map = dict(doctrine)
    threshold_map = dict(thresholds)
    remote_map = dict(remote)
    policy_map = dict(policy)
    _exact_keys(source_map, _SOURCE_KEYS, label="Configuration source")
    _exact_keys(doctrine_map, _DOCTRINE_KEYS, label="Configuration doctrine")
    _exact_keys(threshold_map, _THRESHOLD_KEYS, label="Configuration thresholds")
    _exact_keys(remote_map, _REMOTE_KEYS, label="Configuration remote_origins")
    _exact_keys(policy_map, _POLICY_KEYS, label="Configuration policy")

    source_path, source_relative = _under_repo(root, source_map.get("root"), label="Configured source root")
    kind = _source_kind(source_relative)
    if source_map.get("kind") != kind:
        _raise("Configured source kind does not match the exact configured path.")
    expected_tree = source_map.get("tree_sha256")
    if not isinstance(expected_tree, str) or not _SHA256_RE.fullmatch(expected_tree):
        _raise("Configured source tree_sha256 must be one upper-case SHA-256.")
    try:
        config_path.relative_to(source_path)
    except ValueError:
        pass
    else:
        _raise("Configuration must stay outside the audited public source tree.")

    doctrine_path, doctrine_relative, doctrine_bytes = _regular_file(
        root, doctrine_map.get("path"), label="Configured design doctrine"
    )
    if doctrine_relative != DOCTRINE_PATH:
        _raise(f"Configured doctrine path must be exactly {DOCTRINE_PATH}.")
    doctrine_sha = _bytes_sha256(doctrine_bytes)
    if doctrine_map.get("sha256") != doctrine_sha:
        _raise("Configured design-doctrine hash is stale or incorrect.")

    for key, value in threshold_map.items():
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            _raise(f"Threshold {key!r} must be a non-negative integer.")
    if threshold_map["max_transition_duration_ms"] < threshold_map["min_transition_duration_ms"]:
        _raise("Maximum transition duration must be greater than or equal to the minimum.")
    if threshold_map["max_reduced_motion_duration_ms"] > 10:
        _raise("Reduced-motion disabling duration may not exceed 10ms.")
    if threshold_map["max_animation_duration_ms"] > 800:
        _raise("Animation budget may not weaken the doctrine's 800ms maximum.")
    if threshold_map["max_transition_duration_ms"] > 500:
        _raise("Transition budget may not weaken the doctrine's 500ms maximum.")
    if threshold_map["min_transition_duration_ms"] < 80:
        _raise("Transition budget may not weaken the doctrine's normal 80ms minimum.")

    allowed = remote_map.get("allowed")
    if not isinstance(allowed, list) or not all(isinstance(item, str) for item in allowed):
        _raise("remote_origins.allowed must be a JSON array of exact HTTPS origins.")
    normalised_allowed = [_normalise_origin(value, label="Allowed remote origin") for value in allowed]
    if normalised_allowed != sorted(set(normalised_allowed)):
        _raise("Allowed remote origins must be unique and sorted.")
    if not isinstance(remote_map.get("allow_data_urls"), bool):
        _raise("remote_origins.allow_data_urls must be Boolean.")
    if policy_map != _FIXED_POLICY:
        _raise("Motion/performance policy is fixed and may not be weakened or extended.")

    snapshot = _walk_tree(source_path, source_relative)
    if snapshot.tree_sha256 != expected_tree:
        _raise("Configured source tree hash is stale; no audit receipt was issued.")
    if _read_file_stably(config_path, label="Configuration") != config_bytes:
        _raise("Configuration changed while the audit was being prepared.")
    if _read_file_stably(doctrine_path, label="Configured design doctrine") != doctrine_bytes:
        _raise("Design doctrine changed while the audit was being prepared.")
    config_sha = _bytes_sha256(config_bytes)
    return (
        {
            "schema": CONFIG_SCHEMA,
            "source": source_map,
            "doctrine": doctrine_map,
            "thresholds": threshold_map,
            "remote_origins": {
                "allowed": normalised_allowed,
                "allow_data_urls": remote_map["allow_data_urls"],
            },
            "policy": policy_map,
        },
        snapshot,
        doctrine_sha,
        config_sha,
    )


def _decode_text(content: bytes, *, path: str) -> str:
    if content.startswith(b"\xef\xbb\xbf"):
        _raise(f"Inspectable source must be UTF-8 without a byte-order mark: {path}.")
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DesignMotionPerformanceBudgetError(f"Inspectable source is not valid UTF-8: {path}.") from exc
    if "\x00" in text:
        _raise(f"Inspectable source contains a NUL byte: {path}.")
    return text


def _hash_text(value: str) -> str:
    return _bytes_sha256(value.encode("utf-8"))


def _finding(
    findings: list[dict[str, Any]],
    code: str,
    path: str,
    line: int,
    **evidence: object,
) -> None:
    findings.append(
        {
            "code": code,
            "severity": "blocker",
            "path": path,
            "line": max(1, int(line)),
            "evidence": evidence,
        }
    )


def _normalised_number(value: Decimal) -> int | float:
    rounded = value.quantize(Decimal("0.001"))
    if rounded == rounded.to_integral_value():
        return int(rounded)
    return float(rounded)


def _duration_values(value: str, *, shorthand: bool) -> tuple[int | float, ...]:
    groups = _split_top_level(value, ",") if shorthand else (value,)
    result: list[int | float] = []
    for group in groups:
        matches = list(_TIME_RE.finditer(group))
        if shorthand and matches:
            matches = matches[:1]
        for match in matches:
            try:
                numeric = Decimal(match.group("number"))
            except InvalidOperation:
                continue
            if numeric < 0:
                continue
            milliseconds = numeric * (Decimal(1000) if match.group("unit").lower() == "s" else 1)
            result.append(_normalised_number(milliseconds))
    return tuple(result)


def _split_top_level(value: str, delimiter: str) -> tuple[str, ...]:
    result: list[str] = []
    start = 0
    quote = ""
    escaped = False
    depth = 0
    for index, character in enumerate(value):
        if quote:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = ""
            continue
        if character in {'"', "'"}:
            quote = character
        elif character in "([":
            depth += 1
        elif character in ")]":
            depth = max(0, depth - 1)
        elif character == delimiter and depth == 0:
            result.append(value[start:index].strip())
            start = index + 1
    result.append(value[start:].strip())
    return tuple(item for item in result if item)


def _strip_css_comments(text: str, *, path: str) -> str:
    output = list(text)
    index = 0
    quote = ""
    escaped = False
    while index < len(text):
        character = text[index]
        if quote:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = ""
            index += 1
            continue
        if character in {'"', "'"}:
            quote = character
            index += 1
            continue
        if text.startswith("/*", index):
            end = text.find("*/", index + 2)
            if end < 0:
                _raise(f"CSS contains an unterminated comment: {path}.")
            for cursor in range(index, end + 2):
                if output[cursor] != "\n":
                    output[cursor] = " "
            index = end + 2
            continue
        index += 1
    if quote:
        _raise(f"CSS contains an unterminated string: {path}.")
    return "".join(output)


def _matching_brace(text: str, opening: int, *, path: str) -> int:
    depth = 1
    quote = ""
    escaped = False
    index = opening + 1
    while index < len(text):
        character = text[index]
        if quote:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = ""
        elif character in {'"', "'"}:
            quote = character
        elif character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    _raise(f"CSS contains an unmatched opening brace: {path}.")


def _split_declarations(body: str, *, path: str, base_line: int) -> list[tuple[str, str, int]]:
    if "{" in body or "}" in body:
        _raise(f"CSS nesting is not statically inspectable: {path}.")
    chunks = _split_top_level(body, ";")
    result: list[tuple[str, str, int]] = []
    search_start = 0
    for chunk in chunks:
        index = body.find(chunk, search_start)
        search_start = max(search_start, index + len(chunk))
        if ":" not in chunk:
            if chunk.strip():
                _raise(f"CSS contains a malformed declaration: {path}.")
            continue
        name, value = chunk.split(":", 1)
        property_name = name.strip().casefold()
        if not re.fullmatch(r"(?:--[a-z0-9-]+|-?[a-z][a-z0-9-]*)", property_name):
            _raise(f"CSS contains a malformed property name: {path}.")
        line = base_line + body.count("\n", 0, max(index, 0))
        result.append((property_name, value.strip(), line))
    return result


def _is_positive_reduced_motion_media(prelude: str) -> bool:
    lowered = prelude.casefold()
    if not lowered.startswith("@media"):
        return False
    queries = _split_top_level(lowered.removeprefix("@media").strip(), ",")
    for query in queries:
        if (
            "no-preference" not in query
            and re.search(r"\bnot\b", query) is None
            and re.search(r"\(\s*prefers-reduced-motion\s*:\s*reduce\s*\)", query) is not None
        ):
            return True
    return False


def _motion_selector_covered(
    selector: str,
    kind: str,
    overrides: Mapping[str, set[str]],
) -> bool:
    if kind in overrides.get(selector, set()):
        return True
    pseudo = "::before" if "::before" in selector else "::after" if "::after" in selector else ""
    universal = f"*{pseudo}" if pseudo else "*"
    return kind in overrides.get(universal, set())


def _scan_css(
    text: str,
    *,
    source_path: str,
    base_line: int,
    findings: list[dict[str, Any]],
    motion: list[_MotionRecord],
    overrides: dict[str, set[str]],
    resources: list[_ResourceReference],
    reduced_duration_ms: int,
) -> None:
    if any(marker in text for marker in _TEMPLATE_MARKERS):
        _finding(
            findings,
            "dynamic-motion-uninspectable",
            source_path,
            base_line,
            mechanism="template-css",
        )
    clean = _strip_css_comments(text, path=source_path)
    for match in _RESOURCE_URL_RE.finditer(clean):
        resources.append(
            _ResourceReference(
                source_path,
                base_line + clean.count("\n", 0, match.start()),
                match.group("url").strip(),
                "css-url",
            )
        )
    for match in _IMPORT_URL_RE.finditer(clean):
        resources.append(
            _ResourceReference(
                source_path,
                base_line + clean.count("\n", 0, match.start()),
                match.group("url").strip(),
                "css-import",
            )
        )

    def parse_container(container: str, *, line_offset: int, reduced: bool) -> None:
        start = 0
        index = 0
        quote = ""
        escaped = False
        depth = 0
        while index < len(container):
            character = container[index]
            if quote:
                if escaped:
                    escaped = False
                elif character == "\\":
                    escaped = True
                elif character == quote:
                    quote = ""
                index += 1
                continue
            if character in {'"', "'"}:
                quote = character
            elif character in "([":
                depth += 1
            elif character in ")]":
                depth -= 1
                if depth < 0:
                    _raise(f"CSS contains unmatched punctuation: {source_path}.")
            elif character == "}" and depth == 0:
                _raise(f"CSS contains an unmatched closing brace: {source_path}.")
            elif character == ";" and depth == 0:
                start = index + 1
            elif character == "{" and depth == 0:
                prelude = container[start:index].strip()
                if not prelude:
                    _raise(f"CSS contains a block without a selector or at-rule: {source_path}.")
                closing = _matching_brace(container, index, path=source_path)
                body = container[index + 1 : closing]
                rule_line = line_offset + container.count("\n", 0, index)
                body_line = rule_line + 1
                lowered = prelude.casefold()
                if lowered.startswith("@media"):
                    is_reduced = _is_positive_reduced_motion_media(prelude)
                    parse_container(body, line_offset=body_line, reduced=reduced or is_reduced)
                elif re.match(r"@(?:-webkit-)?keyframes\b", lowered):
                    if any(marker in body for marker in _TEMPLATE_MARKERS):
                        _finding(
                            findings,
                            "dynamic-motion-uninspectable",
                            source_path,
                            rule_line,
                            mechanism="template-keyframes",
                        )
                elif re.match(r"@(?:supports|layer|container|scope|document)\b", lowered):
                    parse_container(body, line_offset=body_line, reduced=reduced)
                elif lowered.startswith("@font-face"):
                    _split_declarations(body, path=source_path, base_line=body_line)
                elif lowered.startswith("@"):
                    _finding(
                        findings,
                        "dynamic-motion-uninspectable",
                        source_path,
                        rule_line,
                        mechanism="uninspectable-css-at-rule",
                        prelude_sha256=_hash_text(prelude),
                    )
                else:
                    selectors = _split_top_level(prelude, ",")
                    if not selectors:
                        _raise(f"CSS contains an empty selector: {source_path}.")
                    declarations = _split_declarations(
                        body,
                        path=source_path,
                        base_line=body_line,
                    )
                    for property_name, raw_value, declaration_line in declarations:
                        value = re.sub(r"\s*!important\s*$", "", raw_value, flags=re.IGNORECASE).strip()
                        dynamic = bool(_DYNAMIC_CSS_RE.search(value))
                        kind = ""
                        durations: tuple[int | float, ...] = ()
                        lowered_value = value.casefold()
                        if property_name.startswith("animation"):
                            kind = "animation"
                            durations = _duration_values(
                                value,
                                shorthand=property_name == "animation",
                            )
                            if "infinite" in re.split(r"[\s,]+", lowered_value):
                                _finding(
                                    findings,
                                    "infinite-animation",
                                    source_path,
                                    declaration_line,
                                    selector_sha256=_hash_text(",".join(selectors)),
                                )
                        elif property_name.startswith("transition"):
                            kind = "transition"
                            durations = _duration_values(
                                value,
                                shorthand=property_name == "transition",
                            )
                        elif property_name == "transform":
                            kind = "transform"
                        elif property_name == "scroll-behavior":
                            kind = "scroll"

                        disabled = False
                        if kind == "animation":
                            disabled = lowered_value == "none" or (
                                property_name in {"animation", "animation-duration"}
                                and bool(durations)
                                and max(float(item) for item in durations) <= reduced_duration_ms
                            )
                        elif kind == "transition":
                            disabled = lowered_value == "none" or (
                                property_name in {"transition", "transition-duration"}
                                and bool(durations)
                                and max(float(item) for item in durations) <= reduced_duration_ms
                            )
                        elif kind == "transform":
                            disabled = lowered_value == "none"
                        elif kind == "scroll":
                            disabled = lowered_value == "auto"

                        if reduced and kind and disabled:
                            for selector in selectors:
                                overrides.setdefault(selector, set()).add(kind)
                            continue
                        if reduced:
                            continue
                        active = bool(kind) and lowered_value not in {"", "none", "initial", "unset"}
                        if active:
                            motion.append(
                                _MotionRecord(
                                    source_path=source_path,
                                    line=declaration_line,
                                    selectors=selectors,
                                    kind=kind,
                                    durations_ms=durations,
                                )
                            )
                            if dynamic:
                                _finding(
                                    findings,
                                    "dynamic-motion-uninspectable",
                                    source_path,
                                    declaration_line,
                                    mechanism="dynamic-css-value",
                                    property_sha256=_hash_text(property_name),
                                )
                start = closing + 1
                index = closing
            index += 1
        if quote or depth != 0:
            _raise(f"CSS contains unmatched punctuation or string syntax: {source_path}.")
        trailing = container[start:].strip()
        if trailing and not trailing.startswith("@"):
            _raise(f"CSS contains trailing unparsed content: {source_path}.")

    parse_container(clean, line_offset=base_line, reduced=False)


class _HTMLScanner(HTMLParser):
    def __init__(
        self,
        *,
        source_path: str,
        findings: list[dict[str, Any]],
        resources: list[_ResourceReference],
    ) -> None:
        super().__init__(convert_charrefs=True)
        self.source_path = source_path
        self.findings = findings
        self.resources = resources
        self.style_chunks: list[tuple[int, str]] = []
        self.script_chunks: list[tuple[int, str, bool]] = []
        self._raw_tag = ""
        self._raw_line = 1
        self._raw_chunks: list[str] = []
        self._raw_script_executable = True
        self._open_raw: dict[str, int] = {"style": 0, "script": 0}

    def _resource(self, value: str, kind: str) -> None:
        self.resources.append(_ResourceReference(self.source_path, self.getpos()[0], value.strip(), kind))

    def _attributes(self, attrs: list[tuple[str, str | None]]) -> dict[str, str]:
        result: dict[str, str] = {}
        for raw_name, raw_value in attrs:
            name = raw_name.casefold()
            if name in result:
                _finding(
                    self.findings,
                    "malformed-html",
                    self.source_path,
                    self.getpos()[0],
                    reason="duplicate-attribute",
                    attribute_sha256=_hash_text(name),
                )
            result[name] = "" if raw_value is None else raw_value
        return result

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.casefold()
        attributes = self._attributes(attrs)
        for attribute, value in attributes.items():
            if attribute.startswith("on") and len(attribute) > 2:
                _finding(
                    self.findings,
                    "dynamic-motion-uninspectable",
                    self.source_path,
                    self.getpos()[0],
                    mechanism="inline-event-handler",
                    attribute_sha256=_hash_text(attribute),
                )
                _scan_javascript(
                    value,
                    source_path=self.source_path,
                    base_line=self.getpos()[0],
                    findings=self.findings,
                    resources=self.resources,
                )
        if lowered in {"video", "audio"} and "autoplay" in attributes:
            _finding(
                self.findings,
                "autoplay-media",
                self.source_path,
                self.getpos()[0],
                media_kind=lowered,
            )
        if lowered in {"animate", "animatemotion", "animatetransform", "set", "marquee"}:
            _finding(
                self.findings,
                "dynamic-motion-uninspectable",
                self.source_path,
                self.getpos()[0],
                mechanism="markup-motion",
            )
            if attributes.get("repeatcount", "").casefold() in {"indefinite", "infinite"}:
                _finding(
                    self.findings,
                    "infinite-animation",
                    self.source_path,
                    self.getpos()[0],
                    selector_sha256=_hash_text(lowered),
                )
        resource_attributes: tuple[tuple[str, str], ...] = ()
        if lowered == "script":
            resource_attributes = (("src", "script-src"),)
        elif lowered == "link":
            rel = set(attributes.get("rel", "").casefold().split())
            if rel & {"stylesheet", "preload", "modulepreload", "icon", "manifest"}:
                resource_attributes = (("href", "link-href"),)
        elif lowered in {"img", "source"}:
            resource_attributes = (("src", f"{lowered}-src"), ("srcset", f"{lowered}-srcset"))
        elif lowered in {"video", "audio"}:
            resource_attributes = (("src", f"{lowered}-src"), ("poster", f"{lowered}-poster"))
        elif lowered in {"iframe", "embed"}:
            resource_attributes = (("src", f"{lowered}-src"),)
        elif lowered == "object":
            resource_attributes = (("data", "object-data"),)
        elif lowered == "input" and attributes.get("type", "").casefold() == "image":
            resource_attributes = (("src", "input-image-src"),)
        for attribute, kind in resource_attributes:
            resource_value = attributes.get(attribute)
            if not resource_value:
                continue
            if attribute == "srcset":
                for candidate in _split_top_level(resource_value, ","):
                    self._resource(candidate.split()[0], kind)
            else:
                self._resource(resource_value, kind)
        if "style" in attributes and attributes["style"].strip():
            self.style_chunks.append((self.getpos()[0], f"__inline__{{{attributes['style']}}}"))
        if lowered in {"style", "script"}:
            self._raw_tag = lowered
            self._raw_line = self.getpos()[0]
            self._raw_chunks = []
            if lowered == "script":
                script_type = attributes.get("type", "").strip().casefold()
                self._raw_script_executable = script_type in {
                    "",
                    "application/ecmascript",
                    "application/javascript",
                    "module",
                    "text/ecmascript",
                    "text/javascript",
                }
            self._open_raw[lowered] += 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag.casefold() not in _VOID_HTML_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.casefold()
        if lowered in {"style", "script"}:
            if self._open_raw[lowered] <= 0 or self._raw_tag != lowered:
                _finding(
                    self.findings,
                    "malformed-html",
                    self.source_path,
                    self.getpos()[0],
                    reason="unbalanced-raw-tag",
                )
                return
            content = "".join(self._raw_chunks)
            if lowered == "style":
                self.style_chunks.append((self._raw_line, content))
            else:
                self.script_chunks.append((self._raw_line, content, self._raw_script_executable))
            self._open_raw[lowered] -= 1
            self._raw_tag = ""
            self._raw_chunks = []

    def handle_data(self, data: str) -> None:
        if self._raw_tag:
            self._raw_chunks.append(data)

    def finish(self) -> None:
        self.close()
        if any(self._open_raw.values()):
            _finding(
                self.findings,
                "malformed-html",
                self.source_path,
                self._raw_line,
                reason="unclosed-raw-tag",
            )


def _scan_javascript(
    text: str,
    *,
    source_path: str,
    base_line: int,
    findings: list[dict[str, Any]],
    resources: list[_ResourceReference],
) -> None:
    if any(marker in text for marker in _TEMPLATE_MARKERS):
        _finding(
            findings,
            "dynamic-motion-uninspectable",
            source_path,
            base_line,
            mechanism="dynamic-javascript-template",
        )
    for mechanism, pattern in _JS_MOTION_PATTERNS:
        for match in pattern.finditer(text):
            _finding(
                findings,
                "dynamic-motion-uninspectable",
                source_path,
                base_line + text.count("\n", 0, match.start()),
                mechanism=mechanism,
            )
    for pattern in (_JS_RESOURCE_RE, _JS_STATIC_IMPORT_RE):
        for match in pattern.finditer(text):
            resources.append(
                _ResourceReference(
                    source_path,
                    base_line + text.count("\n", 0, match.start()),
                    match.group("url").strip(),
                    "javascript-resource",
                )
            )
    for match in _JS_OPEN_RESOURCE_RE.finditer(text):
        resources.append(
            _ResourceReference(
                source_path,
                base_line + text.count("\n", 0, match.start()),
                match.group("url").strip(),
                "javascript-open-resource",
            )
        )
    for match in _JS_URL_ASSIGNMENT_RE.finditer(text):
        value = _JS_STATIC_VALUE_RE.match(match.group("rhs"))
        line = base_line + text.count("\n", 0, match.start())
        if value is None:
            _finding(
                findings,
                "dynamic-resource-uninspectable",
                source_path,
                line,
                mechanism="dynamic-url-property-assignment",
            )
        else:
            resources.append(
                _ResourceReference(
                    source_path,
                    line,
                    value.group("url").strip(),
                    "javascript-url-assignment",
                )
            )
    for match in _JS_SET_ATTRIBUTE_RE.finditer(text):
        value = _JS_STATIC_VALUE_RE.match(match.group("rhs"))
        line = base_line + text.count("\n", 0, match.start())
        if value is None:
            _finding(
                findings,
                "dynamic-resource-uninspectable",
                source_path,
                line,
                mechanism="dynamic-resource-attribute",
                attribute_sha256=_hash_text(match.group("attribute").casefold()),
            )
        else:
            resources.append(
                _ResourceReference(
                    source_path,
                    line,
                    value.group("url").strip(),
                    "javascript-resource-attribute",
                )
            )


def _classify_path(path: str) -> str:
    suffix = PurePosixPath(path).suffix.casefold()
    if suffix in {".html", ".htm"}:
        return "html"
    if suffix == ".css":
        return "css"
    if suffix in {".js", ".mjs", ".cjs"}:
        return "javascript"
    if suffix in _IMAGE_EXTENSIONS:
        return "image"
    if suffix in _FONT_EXTENSIONS:
        return "font"
    if suffix in _MEDIA_EXTENSIONS:
        return "media"
    return "other"


def _origin_from_url(value: str) -> str:
    candidate = value
    if value.startswith("//"):
        candidate = "https:" + value
    parsed = urlsplit(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return ""
    host = parsed.hostname.lower()
    try:
        port = parsed.port
    except ValueError:
        return ""
    default_port = 443 if parsed.scheme == "https" else 80
    authority = host if port in (None, default_port) else f"{host}:{port}"
    return f"{parsed.scheme.lower()}://{authority}"


def _embedded_bytes(value: str) -> int | None:
    if not value.casefold().startswith("data:") or "," not in value:
        return None
    header, payload = value.split(",", 1)
    try:
        if header.casefold().endswith(";base64"):
            return len(base64.b64decode(payload, validate=True))
        return len(unquote_to_bytes(payload))
    except (ValueError, binascii.Error):
        return None


def _resolve_local_resource(
    reference: _ResourceReference,
    *,
    file_map: Mapping[str, _TreeFile],
) -> tuple[str, str]:
    raw = reference.value.strip()
    parsed = urlsplit(raw)
    if parsed.scheme or parsed.netloc:
        return "", "unsupported-scheme"
    try:
        decoded = unquote_to_bytes(parsed.path).decode("utf-8")
    except (UnicodeDecodeError, ValueError):
        return "", "invalid-encoding"
    if not decoded or decoded == "/":
        return "", "not-a-file"
    if "\\" in decoded or "\x00" in decoded:
        return "", "unsafe-path"
    if decoded.startswith("/"):
        parts = list(PurePosixPath(decoded.lstrip("/")).parts)
    else:
        parts = list(PurePosixPath(reference.source_path).parent.parts)
        parts.extend(PurePosixPath(decoded).parts)
    normalised: list[str] = []
    for part in parts:
        if part in {"", "."}:
            continue
        if part == "..":
            if not normalised:
                return "", "path-escape"
            normalised.pop()
        else:
            normalised.append(part)
    candidate = "/".join(normalised)
    if candidate in file_map:
        return candidate, ""
    index_candidate = f"{candidate.rstrip('/')}/index.html"
    if index_candidate in file_map:
        return index_candidate, ""
    return candidate, "missing"


def _resource_measurements(
    references: Sequence[_ResourceReference],
    *,
    file_map: Mapping[str, _TreeFile],
    allowed_origins: set[str],
    allow_data_urls: bool,
    max_embedded_data_bytes: int,
    findings: list[dict[str, Any]],
) -> dict[str, object]:
    local_paths: set[str] = set()
    remote_origins: set[str] = set()
    remote_count = 0
    data_count = 0
    embedded_bytes = 0
    for reference in references:
        value = reference.value.strip()
        if not value or value.startswith("#"):
            continue
        lowered = value.casefold()
        if lowered.startswith("data:"):
            data_count += 1
            decoded_bytes = _embedded_bytes(value)
            if decoded_bytes is None:
                _finding(
                    findings,
                    "malformed-embedded-resource",
                    reference.source_path,
                    reference.line,
                    resource_kind=reference.kind,
                    value_sha256=_hash_text(value),
                )
                continue
            embedded_bytes += decoded_bytes
            if not allow_data_urls:
                _finding(
                    findings,
                    "embedded-resource-not-allowed",
                    reference.source_path,
                    reference.line,
                    resource_kind=reference.kind,
                    value_sha256=_hash_text(value),
                    decoded_bytes=decoded_bytes,
                )
            continue
        if value.startswith("//") or lowered.startswith(("http://", "https://")):
            remote_count += 1
            origin = _origin_from_url(value)
            if not origin:
                _finding(
                    findings,
                    "malformed-remote-origin",
                    reference.source_path,
                    reference.line,
                    resource_kind=reference.kind,
                    value_sha256=_hash_text(value),
                )
                continue
            remote_origins.add(origin)
            if value.startswith("//") or origin not in allowed_origins:
                _finding(
                    findings,
                    "undeclared-remote-origin",
                    reference.source_path,
                    reference.line,
                    resource_kind=reference.kind,
                    origin_sha256=_hash_text(origin),
                    protocol_relative=value.startswith("//"),
                )
            continue
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", value):
            _finding(
                findings,
                "unsupported-resource-scheme",
                reference.source_path,
                reference.line,
                resource_kind=reference.kind,
                scheme_sha256=_hash_text(value.split(":", 1)[0].casefold()),
            )
            continue
        resolved, error = _resolve_local_resource(reference, file_map=file_map)
        if error:
            _finding(
                findings,
                "local-resource-unresolved",
                reference.source_path,
                reference.line,
                resource_kind=reference.kind,
                reason=error,
                target_sha256=_hash_text(value),
            )
        elif resolved:
            local_paths.add(resolved)
    if embedded_bytes > max_embedded_data_bytes:
        _finding(
            findings,
            "embedded-resource-budget-exceeded",
            "<tree>",
            1,
            observed_bytes=embedded_bytes,
            maximum_bytes=max_embedded_data_bytes,
        )
    return {
        "reference_count": len(references),
        "unique_local_resource_count": len(local_paths),
        "unique_local_resource_bytes": sum(file_map[path].size for path in local_paths),
        "remote_reference_count": remote_count,
        "remote_origin_count": len(remote_origins),
        "remote_origin_set_sha256": _json_sha256(sorted(_hash_text(item) for item in remote_origins)),
        "embedded_reference_count": data_count,
        "embedded_decoded_bytes": embedded_bytes,
    }


def _duration_summary(values: Sequence[int | float]) -> dict[str, int | float]:
    if not values:
        return {"count": 0, "minimum_ms": 0, "maximum_ms": 0}
    return {
        "count": len(values),
        "minimum_ms": min(values),
        "maximum_ms": max(values),
    }


def _sorted_findings(findings: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[str, dict[str, Any]] = {}
    for finding in findings:
        identity = _json_sha256(finding)
        unique[identity] = finding
    return sorted(
        unique.values(),
        key=lambda item: (
            str(item["code"]),
            str(item["path"]),
            int(item["line"]),
            _json_sha256(item["evidence"]),
        ),
    )


def _check(
    identifier: str,
    *,
    passed: bool,
    blocker_codes: Sequence[str],
) -> dict[str, object]:
    return {
        "id": identifier,
        "passed": passed,
        "blocker_codes": sorted(blocker_codes),
    }


def _build_receipt(
    *,
    root: Path,
    config: Mapping[str, Any],
    config_relative: str,
    config_sha: str,
    doctrine_sha: str,
    snapshot: _TreeSnapshot,
    expected_implementation_binding: tuple[str, str],
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    resources: list[_ResourceReference] = []
    motion: list[_MotionRecord] = []
    overrides: dict[str, set[str]] = {}
    file_map = {item.path: item for item in snapshot.files}
    thresholds = dict(config["thresholds"])
    categories = {
        "html": 0,
        "css": 0,
        "javascript": 0,
        "image": 0,
        "font": 0,
        "media": 0,
        "other": 0,
    }
    category_counts = dict.fromkeys(categories, 0)

    for item in snapshot.files:
        category = _classify_path(item.path)
        categories[category] += item.size
        category_counts[category] += 1
        if category in {"image", "font", "media", "other"} and item.size > int(
            thresholds["max_single_asset_bytes"]
        ):
            _finding(
                findings,
                "single-asset-budget-exceeded",
                item.path,
                1,
                observed_bytes=item.size,
                maximum_bytes=thresholds["max_single_asset_bytes"],
                asset_category=category,
            )
        if PurePosixPath(item.path).suffix.casefold() in _ANIMATED_IMAGE_EXTENSIONS:
            _finding(
                findings,
                "autoplay-media",
                item.path,
                1,
                media_kind="animated-image",
            )
        if category == "html":
            text = _decode_text(item.content, path=item.path)
            if any(marker in text for marker in _TEMPLATE_MARKERS):
                _finding(
                    findings,
                    "dynamic-motion-uninspectable",
                    item.path,
                    1,
                    mechanism="template-html",
                )
            scanner = _HTMLScanner(
                source_path=item.path,
                findings=findings,
                resources=resources,
            )
            try:
                scanner.feed(text)
                scanner.finish()
            except (AssertionError, ValueError) as exc:
                raise DesignMotionPerformanceBudgetError(
                    f"HTML cannot be inspected deterministically: {item.path}."
                ) from exc
            for line, style_text in scanner.style_chunks:
                _scan_css(
                    style_text,
                    source_path=item.path,
                    base_line=line,
                    findings=findings,
                    motion=motion,
                    overrides=overrides,
                    resources=resources,
                    reduced_duration_ms=int(thresholds["max_reduced_motion_duration_ms"]),
                )
            for line, script_text, executable in scanner.script_chunks:
                if executable:
                    _scan_javascript(
                        script_text,
                        source_path=item.path,
                        base_line=line,
                        findings=findings,
                        resources=resources,
                    )
        elif category == "css":
            _scan_css(
                _decode_text(item.content, path=item.path),
                source_path=item.path,
                base_line=1,
                findings=findings,
                motion=motion,
                overrides=overrides,
                resources=resources,
                reduced_duration_ms=int(thresholds["max_reduced_motion_duration_ms"]),
            )
        elif category == "javascript":
            _scan_javascript(
                _decode_text(item.content, path=item.path),
                source_path=item.path,
                base_line=1,
                findings=findings,
                resources=resources,
            )
        elif PurePosixPath(item.path).suffix.casefold() == ".svg":
            svg = _decode_text(item.content, path=item.path)
            try:
                svg_root = ET.fromstring(svg)
            except ET.ParseError as exc:
                raise DesignMotionPerformanceBudgetError(
                    f"SVG cannot be inspected deterministically: {item.path}."
                ) from exc
            if svg_root.tag.rsplit("}", 1)[-1].casefold() != "svg":
                _raise(f"SVG root element is invalid: {item.path}.")
            for element in svg_root.iter():
                local_tag = element.tag.rsplit("}", 1)[-1].casefold()
                if local_tag in {"animate", "animatemotion", "animatetransform", "set", "script"}:
                    _finding(
                        findings,
                        "dynamic-motion-uninspectable",
                        item.path,
                        1,
                        mechanism="svg-runtime-motion",
                    )
                    if str(element.attrib.get("repeatCount", "")).casefold() in {
                        "indefinite",
                        "infinite",
                    }:
                        _finding(
                            findings,
                            "infinite-animation",
                            item.path,
                            1,
                            selector_sha256=_hash_text(local_tag),
                        )
                for raw_attribute, raw_value in element.attrib.items():
                    attribute = raw_attribute.rsplit("}", 1)[-1].casefold()
                    if attribute in {"href", "src"} and raw_value:
                        resources.append(
                            _ResourceReference(
                                item.path,
                                1,
                                raw_value,
                                f"svg-{attribute}",
                            )
                        )
                    elif attribute == "style" and raw_value.strip():
                        _scan_css(
                            f"__svg_inline__{{{raw_value}}}",
                            source_path=item.path,
                            base_line=1,
                            findings=findings,
                            motion=motion,
                            overrides=overrides,
                            resources=resources,
                            reduced_duration_ms=int(thresholds["max_reduced_motion_duration_ms"]),
                        )
                if local_tag == "style" and element.text:
                    _scan_css(
                        element.text,
                        source_path=item.path,
                        base_line=1,
                        findings=findings,
                        motion=motion,
                        overrides=overrides,
                        resources=resources,
                        reduced_duration_ms=int(thresholds["max_reduced_motion_duration_ms"]),
                    )

    animation_durations: list[int | float] = []
    transition_durations: list[int | float] = []
    animation_count = 0
    transition_count = 0
    for record in motion:
        if record.kind == "animation":
            animation_count += 1
            animation_durations.extend(record.durations_ms)
        elif record.kind == "transition":
            transition_count += 1
            transition_durations.extend(record.durations_ms)
        for selector in record.selectors:
            if not _motion_selector_covered(selector, record.kind, overrides):
                _finding(
                    findings,
                    "reduced-motion-override-missing",
                    record.source_path,
                    record.line,
                    motion_kind=record.kind,
                    selector_sha256=_hash_text(selector),
                )

    for value in animation_durations:
        if float(value) > int(thresholds["max_animation_duration_ms"]):
            _finding(
                findings,
                "animation-duration-budget-exceeded",
                "<tree>",
                1,
                observed_ms=value,
                maximum_ms=thresholds["max_animation_duration_ms"],
            )
    for value in transition_durations:
        if float(value) > int(thresholds["max_transition_duration_ms"]):
            _finding(
                findings,
                "transition-duration-budget-exceeded",
                "<tree>",
                1,
                observed_ms=value,
                maximum_ms=thresholds["max_transition_duration_ms"],
            )
        elif 0 < float(value) < int(thresholds["min_transition_duration_ms"]):
            _finding(
                findings,
                "transition-duration-budget-underrun",
                "<tree>",
                1,
                observed_ms=value,
                minimum_ms=thresholds["min_transition_duration_ms"],
            )
    if animation_count > int(thresholds["max_animation_declarations"]):
        _finding(
            findings,
            "animation-declaration-budget-exceeded",
            "<tree>",
            1,
            observed_count=animation_count,
            maximum_count=thresholds["max_animation_declarations"],
        )
    if transition_count > int(thresholds["max_transition_declarations"]):
        _finding(
            findings,
            "transition-declaration-budget-exceeded",
            "<tree>",
            1,
            observed_count=transition_count,
            maximum_count=thresholds["max_transition_declarations"],
        )

    budget_map = {
        "total": ("max_total_bytes", snapshot.total_bytes),
        "html": ("max_html_bytes", categories["html"]),
        "css": ("max_css_bytes", categories["css"]),
        "javascript": ("max_javascript_bytes", categories["javascript"]),
        "image": ("max_image_bytes", categories["image"]),
        "font": ("max_font_bytes", categories["font"]),
        "media": ("max_media_bytes", categories["media"]),
        "other": ("max_other_bytes", categories["other"]),
    }
    for category, (threshold_name, observed) in budget_map.items():
        maximum = int(thresholds[threshold_name])
        if observed > maximum:
            _finding(
                findings,
                "resource-byte-budget-exceeded",
                "<tree>",
                1,
                resource_category=category,
                observed_bytes=observed,
                maximum_bytes=maximum,
            )

    remote_config = dict(config["remote_origins"])
    resource_measurements = _resource_measurements(
        resources,
        file_map=file_map,
        allowed_origins=set(remote_config["allowed"]),
        allow_data_urls=bool(remote_config["allow_data_urls"]),
        max_embedded_data_bytes=int(thresholds["max_embedded_data_bytes"]),
        findings=findings,
    )
    remote_reference_count = resource_measurements["remote_reference_count"]
    if not isinstance(remote_reference_count, int):
        _raise("Internal resource measurement was not an integer.")
    if remote_reference_count > int(thresholds["max_remote_resource_references"]):
        _finding(
            findings,
            "remote-reference-budget-exceeded",
            "<tree>",
            1,
            observed_count=resource_measurements["remote_reference_count"],
            maximum_count=thresholds["max_remote_resource_references"],
        )

    final_snapshot = _walk_tree(snapshot.root, str(dict(config["source"])["root"]))
    if (
        final_snapshot.tree_sha256 != snapshot.tree_sha256
        or final_snapshot.total_bytes != snapshot.total_bytes
        or len(final_snapshot.files) != len(snapshot.files)
    ):
        _raise("Source tree changed during the audit; no receipt was issued.")

    _, _, current_config = _regular_file(root, config_relative, label="Configuration")
    if _bytes_sha256(current_config) != config_sha:
        _raise("Configuration changed during the audit; no receipt was issued.")
    _, _, current_doctrine = _regular_file(root, DOCTRINE_PATH, label="Configured design doctrine")
    if _bytes_sha256(current_doctrine) != doctrine_sha:
        _raise("Design doctrine changed during the audit; no receipt was issued.")

    ordered_findings = _sorted_findings(findings)
    codes = [str(item["code"]) for item in ordered_findings]
    code_set = set(codes)
    groups = {
        "static_syntax_and_runtime_inspectability": {
            "malformed-html",
            "dynamic-motion-uninspectable",
            "dynamic-resource-uninspectable",
            "malformed-embedded-resource",
            "malformed-remote-origin",
        },
        "autoplay_media": {"autoplay-media"},
        "animation_and_transition_durations": {
            "animation-duration-budget-exceeded",
            "transition-duration-budget-exceeded",
            "transition-duration-budget-underrun",
            "animation-declaration-budget-exceeded",
            "transition-declaration-budget-exceeded",
        },
        "infinite_animation": {"infinite-animation"},
        "reduced_motion_override": {"reduced-motion-override-missing"},
        "resource_and_asset_bytes": {
            "single-asset-budget-exceeded",
            "resource-byte-budget-exceeded",
            "embedded-resource-budget-exceeded",
        },
        "remote_origin_policy": {
            "undeclared-remote-origin",
            "dynamic-resource-uninspectable",
            "unsupported-resource-scheme",
            "remote-reference-budget-exceeded",
            "embedded-resource-not-allowed",
        },
        "local_resource_resolution": {"local-resource-unresolved"},
    }
    checks = [
        _check("source-tree-bound", passed=True, blocker_codes=[]),
        *[
            _check(
                identifier,
                passed=not bool(code_set & group_codes),
                blocker_codes=sorted(code_set & group_codes),
            )
            for identifier, group_codes in groups.items()
        ],
    ]
    decision_status = "pass" if not ordered_findings else "blocked"
    implementation_binding = _implementation_binding(root)
    if implementation_binding != expected_implementation_binding:
        _raise(
            "Motion-budget implementation or immutable writer changed during "
            "the audit; no receipt was issued."
        )
    implementation_sha, secure_writer_sha = implementation_binding
    source_map = dict(config["source"])
    receipt: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "implementation": {
            "path": MODULE_PATH,
            "sha256": implementation_sha,
        },
        "immutable_writer": {
            "path": SECURE_WRITER_PATH,
            "sha256": secure_writer_sha,
        },
        "config": {
            "path": config_relative,
            "sha256": config_sha,
            "schema": CONFIG_SCHEMA,
        },
        "doctrine": {
            "path": DOCTRINE_PATH,
            "sha256": doctrine_sha,
        },
        "source": {
            "kind": source_map["kind"],
            "root": source_map["root"],
            "expected_tree_sha256": source_map["tree_sha256"],
            "observed_tree_sha256": snapshot.tree_sha256,
            "algorithm": TREE_ALGORITHM,
            "file_count": len(snapshot.files),
            "total_bytes": snapshot.total_bytes,
        },
        "thresholds_sha256": _json_sha256(thresholds),
        "measurements": {
            "bytes": {
                "total": snapshot.total_bytes,
                "by_category": categories,
                "file_count_by_category": category_counts,
                "largest_asset_bytes": max(
                    (
                        item.size
                        for item in snapshot.files
                        if _classify_path(item.path) in {"image", "font", "media", "other"}
                    ),
                    default=0,
                ),
            },
            "motion": {
                "animation_declaration_count": animation_count,
                "transition_declaration_count": transition_count,
                "transform_declaration_count": sum(1 for item in motion if item.kind == "transform"),
                "smooth_scroll_declaration_count": sum(1 for item in motion if item.kind == "scroll"),
                "animation_durations": _duration_summary(animation_durations),
                "transition_durations": _duration_summary(transition_durations),
                "reduced_override_selector_count": len(overrides),
            },
            "resources": resource_measurements,
        },
        "checks": checks,
        "findings": ordered_findings,
        "decision": {
            "status": decision_status,
            "blocker_count": len(ordered_findings),
            "finding_set_sha256": _json_sha256(ordered_findings),
            "eligible_for_next_local_gate": decision_status == "pass",
            "audit_evidence_only": True,
        },
        "authority": dict(AUTHORITY),
        "limitations": list(STATIC_LIMITATIONS),
    }
    receipt["receipt_sha256"] = _json_sha256(receipt)
    return receipt


def _load_config(
    config_path: Path,
    *,
    repo_root: Path | None,
) -> tuple[Path, str, dict[str, Any], _TreeSnapshot, str, str, Path]:
    root = _repo_root(repo_root)
    _reject_alternate_stream_path(config_path, label="Configuration path")
    absolute = _absolute_without_resolve(config_path if config_path.is_absolute() else root / config_path)
    try:
        relative = absolute.relative_to(root).as_posix()
    except ValueError as exc:
        raise DesignMotionPerformanceBudgetError(
            "Configuration must stay inside the Aureon repository."
        ) from exc
    safe_path, safe_relative, content = _regular_file(root, relative, label="Configuration")
    raw = _strict_json_from_bytes(content, label="Configuration")
    config, snapshot, doctrine_sha, config_sha = _validate_config(
        raw,
        root=root,
        config_relative=safe_relative,
        config_path=safe_path,
        config_bytes=content,
    )
    return safe_path, safe_relative, config, snapshot, doctrine_sha, config_sha, root


def _write_receipt(root: Path, output_path: Path, receipt: Mapping[str, Any]) -> Path:
    _reject_alternate_stream_path(output_path, label="Receipt output path")
    absolute = _absolute_without_resolve(output_path if output_path.is_absolute() else root / output_path)
    try:
        relative = absolute.relative_to(root).as_posix()
    except ValueError as exc:
        raise DesignMotionPerformanceBudgetError(
            "Receipt output must stay inside the Aureon repository."
        ) from exc
    relative_path = _relative_path(relative, label="Receipt output")
    allowed = PurePosixPath("artifacts/website-operator/motion-performance-budget")
    try:
        relative_path.relative_to(allowed)
    except ValueError as exc:
        raise DesignMotionPerformanceBudgetError(
            "Receipt output must stay below artifacts/website-operator/motion-performance-budget/."
        ) from exc
    if relative_path.suffix != ".json":
        _raise("Receipt output must use a .json suffix.")
    current = root
    for part in allowed.parts:
        current = current / part
        if current.exists() or current.is_symlink():
            if _is_link_or_reparse(current) or not current.is_dir():
                _raise("Receipt output parent crosses an unsafe filesystem entry.")
        else:
            current.mkdir()
    parent_relative = relative_path.parent
    current = root
    for part in parent_relative.parts:
        current = current / part
        if current.exists() or current.is_symlink():
            if _is_link_or_reparse(current) or not current.is_dir():
                _raise("Receipt output parent crosses an unsafe filesystem entry.")
        else:
            current.mkdir()
    if absolute.exists() or absolute.is_symlink():
        _raise("Receipt output is immutable and must not already exist.")
    payload = _canonical_json_bytes(receipt)
    try:
        secure_immutable_artifact.write_new_file(absolute, payload)
    except secure_immutable_artifact.SecureImmutableArtifactError as exc:
        raise DesignMotionPerformanceBudgetError(f"Receipt could not be created safely: {exc}") from exc
    return absolute


def audit_motion_performance_budget(
    config_path: Path,
    *,
    repo_root: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Audit one hash-pinned static tree without executing it or using network."""

    root = _repo_root(repo_root)
    implementation_binding = _implementation_binding(root)
    (
        _,
        config_relative,
        config,
        snapshot,
        doctrine_sha,
        config_sha,
        loaded_root,
    ) = _load_config(config_path, repo_root=root)
    if loaded_root != root:
        _raise("Repository root changed while loading the audit configuration.")
    receipt = _build_receipt(
        root=root,
        config=config,
        config_relative=config_relative,
        config_sha=config_sha,
        doctrine_sha=doctrine_sha,
        snapshot=snapshot,
        expected_implementation_binding=implementation_binding,
    )
    if output_path is not None:
        _write_receipt(root, output_path, receipt)
    return receipt


def _validate_receipt_shape(receipt: Mapping[str, Any]) -> None:
    _exact_keys(receipt, _RECEIPT_KEYS, label="Receipt")
    if receipt.get("schema") != RECEIPT_SCHEMA:
        _raise(f"Receipt schema must be {RECEIPT_SCHEMA!r}.")
    if receipt.get("authority") != dict(AUTHORITY):
        _raise("Receipt authority boundary is missing, altered, or expanded.")
    if receipt.get("limitations") != list(STATIC_LIMITATIONS):
        _raise("Receipt static-analysis limitations are missing, altered, or understated.")
    supplied_hash = receipt.get("receipt_sha256")
    if not isinstance(supplied_hash, str) or not _SHA256_RE.fullmatch(supplied_hash):
        _raise("Receipt hash must be one upper-case SHA-256.")
    unsigned = dict(receipt)
    del unsigned["receipt_sha256"]
    if supplied_hash != _json_sha256(unsigned):
        _raise("Receipt self-hash is stale or incorrect.")
    config = receipt.get("config")
    implementation = receipt.get("implementation")
    immutable_writer = receipt.get("immutable_writer")
    decision = receipt.get("decision")
    findings = receipt.get("findings")
    checks = receipt.get("checks")
    if not isinstance(config, Mapping) or set(config) != {"path", "sha256", "schema"}:
        _raise("Receipt configuration binding is malformed.")
    if config.get("schema") != CONFIG_SCHEMA or not _SHA256_RE.fullmatch(str(config.get("sha256", ""))):
        _raise("Receipt configuration binding is invalid.")
    if (
        not isinstance(implementation, Mapping)
        or set(implementation) != {"path", "sha256"}
        or implementation.get("path") != MODULE_PATH
        or not _SHA256_RE.fullmatch(str(implementation.get("sha256", "")))
    ):
        _raise("Receipt implementation binding is malformed.")
    if (
        not isinstance(immutable_writer, Mapping)
        or set(immutable_writer) != {"path", "sha256"}
        or immutable_writer.get("path") != SECURE_WRITER_PATH
        or not _SHA256_RE.fullmatch(str(immutable_writer.get("sha256", "")))
    ):
        _raise("Receipt immutable-writer binding is malformed.")
    if (
        not isinstance(findings, list)
        or not isinstance(checks, list)
        or not isinstance(decision, Mapping)
        or set(decision)
        != {
            "status",
            "blocker_count",
            "finding_set_sha256",
            "eligible_for_next_local_gate",
            "audit_evidence_only",
        }
    ):
        _raise("Receipt decision, findings, or checks are malformed.")
    status = decision.get("status")
    if status not in {"pass", "blocked"}:
        _raise("Receipt decision status is invalid.")
    if (
        decision.get("blocker_count") != len(findings)
        or decision.get("eligible_for_next_local_gate") != (status == "pass")
        or decision.get("audit_evidence_only") is not True
        or decision.get("finding_set_sha256") != _json_sha256(findings)
        or (status == "pass") != (len(findings) == 0)
    ):
        _raise("Receipt decision does not match its exact finding set.")
    for finding in findings:
        if (
            not isinstance(finding, Mapping)
            or set(finding) != {"code", "severity", "path", "line", "evidence"}
            or finding.get("severity") != "blocker"
            or not isinstance(finding.get("code"), str)
            or not isinstance(finding.get("path"), str)
            or not isinstance(finding.get("line"), int)
            or isinstance(finding.get("line"), bool)
            or not isinstance(finding.get("evidence"), Mapping)
        ):
            _raise("Receipt contains a malformed finding.")


def validate_motion_performance_receipt(
    receipt_path: Path,
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Strictly replay a persisted receipt against current config and source bytes."""

    root = _repo_root(repo_root)
    _reject_alternate_stream_path(receipt_path, label="Receipt path")
    absolute = _absolute_without_resolve(receipt_path if receipt_path.is_absolute() else root / receipt_path)
    try:
        relative = absolute.relative_to(root).as_posix()
    except ValueError as exc:
        raise DesignMotionPerformanceBudgetError("Receipt must stay inside the Aureon repository.") from exc
    _, _, content = _regular_file(root, relative, label="Receipt")
    receipt = _strict_json_from_bytes(content, label="Receipt")
    _validate_receipt_shape(receipt)
    config_binding = dict(receipt["config"])
    replay = audit_motion_performance_budget(
        Path(str(config_binding["path"])),
        repo_root=root,
    )
    if receipt != replay:
        _raise("Receipt does not exactly replay against current implementation, policy, config, and source.")
    if content != _canonical_json_bytes(receipt):
        _raise("Persisted receipt is not in the canonical deterministic JSON encoding.")
    return receipt


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit an exact Aureon static website tree for motion and resource budgets."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    snapshot = subparsers.add_parser("snapshot", help="Print a source binding to pin in config.")
    snapshot.add_argument("--repo-root", type=Path, default=None)
    snapshot.add_argument("--source-root", type=Path, required=True)

    audit = subparsers.add_parser("audit", help="Run the pinned local audit.")
    audit.add_argument("--repo-root", type=Path, default=None)
    audit.add_argument("--config", type=Path, required=True)
    audit.add_argument("--output", type=Path, default=None)

    validate = subparsers.add_parser("validate", help="Replay one immutable receipt.")
    validate.add_argument("--repo-root", type=Path, default=None)
    validate.add_argument("--receipt", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    result: dict[str, Any]
    try:
        if args.command == "snapshot":
            result = snapshot_static_tree(args.source_root, repo_root=args.repo_root)
        elif args.command == "audit":
            result = audit_motion_performance_budget(
                args.config,
                repo_root=args.repo_root,
                output_path=args.output,
            )
        else:
            result = validate_motion_performance_receipt(
                args.receipt,
                repo_root=args.repo_root,
            )
    except DesignMotionPerformanceBudgetError as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, sort_keys=True))
        return 2
    print(_canonical_json_bytes(result).decode("utf-8"), end="")
    if args.command == "audit":
        decision = result.get("decision")
        if not isinstance(decision, Mapping) or decision.get("status") != "pass":
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
