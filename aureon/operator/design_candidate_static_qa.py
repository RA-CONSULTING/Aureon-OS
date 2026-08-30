"""Deterministic, read-only static QA for sealed website design candidates.

The trusted command surface is intentionally tiny::

    python -I aureon/operator/design_candidate_static_qa.py \
        --mode website-operator-static \
        --candidate-root <absolute artifacts/website-candidates/<run-id>/website>

The module never writes a report, starts a process, opens a network connection,
or accepts an output/policy/configuration path.  It reads the fixed
``website_operator.defaults.json`` beside this file, projects its ``website/``
claim inputs into the staged candidate in memory, and emits one privacy-
minimised canonical JSON object on stdout.
"""

from __future__ import annotations

import ast
import hashlib
import json
import math
import re
import stat
import sys
import unicodedata
import xml.etree.ElementTree as ET
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import unquote_to_bytes, urlsplit

SCHEMA = "aureon.design-candidate-static-qa.v1"
CONFIG_SCHEMA = "aureon.website-operator.config.v1"
MODES = (
    "website-operator-static",
    "v28-design-system-static",
    "v28-metadata-ethos-static",
)
MODE_CHECKS = {
    "website-operator-static": (
        "source.configuration-binding",
        "source.utf8-and-json",
        "website.required-files",
        "website.claim-inputs",
        "website.budgets",
        "website.secret-patterns",
        "source.tree-stable",
    ),
    "v28-design-system-static": (
        "source.configuration-binding",
        "source.utf8-and-json",
        "design.html-structure",
        "design.local-references",
        "design.active-resources",
        "design.accessibility-basics",
        "design.executable-javascript",
        "design.reduced-motion",
        "design.asset-versioning",
        "source.tree-stable",
    ),
    "v28-metadata-ethos-static": (
        "source.configuration-binding",
        "source.utf8-and-json",
        "metadata.route-contract",
        "metadata.social-contract",
        "metadata.jsonld",
        "metadata.webmanifest",
        "ethos.public-boundaries",
        "ethos.claim-inputs",
        "source.tree-stable",
    ),
}
TEXT_EXTENSIONS = frozenset({".css", ".html", ".htm", ".js", ".json", ".svg", ".txt", ".webmanifest", ".xml"})
JSON_EXTENSIONS = frozenset({".json", ".webmanifest"})
REVIEWED_EXECUTABLE_JS_PATHS = (
    "script.js",
    "funding/funding-status.js",
    "live/live.js",
)
AUTHORITY = {
    "canonical_website_mutation": "none",
    "candidate_mutation": "none",
    "credential_access": "none",
    "deployment_authority": "none",
    "package_authority": "none",
    "release_eligible": False,
    "release_authority": "WebsiteOperator owner gate only",
}
LIMITATIONS = [
    "static-analysis-only",
    "javascript-syntax-is-a-separate-candidate.javascript-syntax.v1-command",
    "browser-rendering-and-human-pixel-review-not-performed",
    "v28-composite-visual-release-gate-not-satisfied",
    "endpoint-tree-stability-is-not-a-continuous-filesystem-sandbox",
]
_RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
_URI = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*://")
_REDUCED_MOTION = re.compile(
    r"@media\s*\(\s*prefers-reduced-motion\s*:\s*reduce\s*\)\s*\{",
    re.IGNORECASE,
)
_JS_REDUCED_MOTION_GATE = re.compile(
    r"\bif\s*\(\s*(?:window\s*\.\s*)?matchMedia\s*\(\s*['\"]"
    r"\(prefers-reduced-motion:\s*reduce\)['\"]\s*\)\s*\.\s*matches\s*\)",
    re.IGNORECASE,
)
_REDUCED_MOTION_EFFECT = re.compile(
    r"(?:^|[;{])\s*(?:"
    r"(?:animation|animation-name|transition|transform)\s*:\s*none\b"
    r"|animation-play-state\s*:\s*paused\b"
    r"|(?:animation-duration|transition-duration)\s*:\s*"
    r"(?:0(?:\.0+)?(?:ms|s)?|0?\.0*1ms)\b"
    r"|scroll-behavior\s*:\s*auto\b"
    r")",
    re.IGNORECASE,
)
_CSS_CONDITIONAL_AT_RULE = re.compile(
    r"\s*(?P<at>@(?:container|document|media|supports)\b)",
    re.IGNORECASE,
)
_JAVASCRIPT_CONTROL_START = re.compile(
    r"\b(?P<kind>if|while|for)\s*\(",
    re.IGNORECASE,
)
_JAVASCRIPT_NUMBER_COMPARISON = re.compile(
    r"(?P<left>[+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*"
    r"(?P<operator><=|>=|={2,3}|!={1,2}|<|>)\s*"
    r"(?P<right>[+-]?(?:\d+(?:\.\d*)?|\.\d+))"
)
_CSS_URL = re.compile(r"url\s*\(\s*(?P<quote>['\"]?)(?P<url>.*?)(?P=quote)\s*\)", re.IGNORECASE)
_CSS_IMPORT = re.compile(
    r"@import\s+(?:url\(\s*(?P<url_quote>['\"]?)(?P<url>.*?)(?P=url_quote)\s*\)|"
    r"(?P<quote>['\"])(?P<string>.*?)(?P=quote))",
    re.IGNORECASE,
)
_CSS_IMAGE_SET_START = re.compile(
    r"(?:-webkit-)?image-set\s*\(",
    re.IGNORECASE,
)
_CSS_MAX_NESTING = 256
_CSS_MAX_BLOCKS = 20_000
_CSS_MAX_SELECTOR_MATCH_OPERATIONS = 2_000_000
_JAVASCRIPT_MAX_CONTROL_NODES = 4_096
_JAVASCRIPT_MAX_CONSTANT_EXPRESSION = 512
_HTML_TEXT_RE = re.compile(r"<[^>]+>")
_SPACE = re.compile(r"\s+")
_REPARSE_POINT = 0x400
_EXECUTABLE_RESOURCE_SUFFIXES = frozenset(
    {
        ".asp",
        ".aspx",
        ".bat",
        ".cgi",
        ".cjs",
        ".cmd",
        ".com",
        ".exe",
        ".hta",
        ".js",
        ".mjs",
        ".php",
        ".pl",
        ".ps1",
        ".psd1",
        ".psm1",
        ".py",
        ".sh",
    }
)
_VOID_HTML_ELEMENTS = frozenset(
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
_NONRENDERED_CONTAINERS = frozenset(
    {
        "canvas",
        "datalist",
        "iframe",
        "math",
        "noembed",
        "object",
        "plaintext",
        "script",
        "select",
        "style",
        "svg",
        "textarea",
        "title",
        "xmp",
    }
)
_PARSER_DIFFERENTIAL_ELEMENTS = frozenset(
    {
        "iframe",
        "noembed",
        "noframes",
        "plaintext",
        "textarea",
        "xmp",
    }
)


class CandidateStaticQABoundaryError(ValueError):
    """A staged root, trusted input, or filesystem boundary is invalid."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass
class _CssBlockFrame:
    kind: str
    prelude: str
    content_start: int
    boundary: int
    selector_context: str | None = None


@dataclass(frozen=True)
class _CssRenderedElement:
    tag: str
    attributes: Mapping[str, str]
    ancestors: tuple[tuple[str, Mapping[str, str]], ...]
    ancestor_indices: tuple[int, ...]


class _DuplicateJsonKey(ValueError):
    pass


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _json_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest().upper()


def _bytes_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _reject_constant(_: str) -> object:
    raise ValueError("non-finite")


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJsonKey(key)
        result[key] = value
    return result


def _strict_json_bytes(data: bytes, *, code: str) -> object:
    if data.startswith(b"\xef\xbb\xbf") or b"\x00" in data:
        raise CandidateStaticQABoundaryError(code)
    try:
        text = data.decode("utf-8", errors="strict")
        value = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, _DuplicateJsonKey, ValueError) as exc:
        raise CandidateStaticQABoundaryError(code) from exc
    _assert_finite(value, code=code)
    return value


def _assert_finite(value: object, *, code: str) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise CandidateStaticQABoundaryError(code)
    if isinstance(value, Mapping):
        for child in value.values():
            _assert_finite(child, code=code)
    elif isinstance(value, list):
        for child in value:
            _assert_finite(child, code=code)


def _repo_root_from_file() -> Path:
    path = Path(__file__)
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise CandidateStaticQABoundaryError("trusted-tool-unresolvable") from exc
    root = resolved.parents[2]
    if not (root / "pyproject.toml").is_file() or not (root / "aureon" / "operator").is_dir():
        raise CandidateStaticQABoundaryError("trusted-repository-layout-invalid")
    return root


def _is_link_or_reparse(path: Path) -> bool:
    try:
        details = path.lstat()
    except OSError as exc:
        raise CandidateStaticQABoundaryError("filesystem-entry-unreadable") from exc
    attributes = int(getattr(details, "st_file_attributes", 0))
    return stat.S_ISLNK(details.st_mode) or bool(attributes & _REPARSE_POINT)


def _validate_candidate_root(raw: object, *, repo_root: Path) -> Path:
    if not isinstance(raw, str) or not raw or "\x00" in raw:
        raise CandidateStaticQABoundaryError("candidate-root-invalid")
    if _URI.match(raw) or raw.startswith(("\\\\", "//")):
        raise CandidateStaticQABoundaryError("candidate-root-uri-or-unc")
    lexical = Path(raw)
    if not lexical.is_absolute():
        raise CandidateStaticQABoundaryError("candidate-root-not-absolute")
    try:
        resolved = lexical.resolve(strict=True)
        repo = repo_root.resolve(strict=True)
        relative = resolved.relative_to(repo / "artifacts" / "website-candidates")
    except (OSError, ValueError) as exc:
        raise CandidateStaticQABoundaryError("candidate-root-outside-staging") from exc
    if (
        len(relative.parts) != 2
        or relative.parts[1] != "website"
        or relative.parts[0] == "work-orders"
        or _RUN_ID.fullmatch(relative.parts[0]) is None
    ):
        raise CandidateStaticQABoundaryError("candidate-root-layout-invalid")
    canonical = (repo / "website").resolve()
    if resolved == canonical:
        raise CandidateStaticQABoundaryError("canonical-website-root-rejected")
    run_root = resolved.parent
    for path in (repo / "artifacts", repo / "artifacts" / "website-candidates", run_root, resolved):
        if _is_link_or_reparse(path) or not path.is_dir():
            raise CandidateStaticQABoundaryError("candidate-root-link-or-reparse")
    return resolved


def _bounded_files(root: Path) -> list[Path]:
    if _is_link_or_reparse(root) or not root.is_dir():
        raise CandidateStaticQABoundaryError("candidate-root-link-or-reparse")
    real_root = root.resolve(strict=True)
    directories = [root]
    files: list[Path] = []
    casefold_paths: dict[str, str] = {}
    while directories:
        directory = directories.pop()
        try:
            entries = sorted(directory.iterdir(), key=lambda item: item.name)
        except OSError as exc:
            raise CandidateStaticQABoundaryError("candidate-tree-unreadable") from exc
        sibling_names: set[str] = set()
        for path in entries:
            if (
                path.name != unicodedata.normalize("NFC", path.name)
                or path.name.strip() != path.name
                or any(ord(character) < 32 or ord(character) == 127 for character in path.name)
                or "\\" in path.name
            ):
                raise CandidateStaticQABoundaryError("candidate-tree-path-name-invalid")
            folded_name = path.name.casefold()
            if folded_name in sibling_names:
                raise CandidateStaticQABoundaryError("candidate-tree-casefold-collision")
            sibling_names.add(folded_name)
            if _is_link_or_reparse(path):
                raise CandidateStaticQABoundaryError("candidate-tree-link-or-reparse")
            try:
                path.resolve(strict=True).relative_to(real_root)
                details = path.lstat()
            except (OSError, ValueError) as exc:
                raise CandidateStaticQABoundaryError("candidate-tree-path-escape") from exc
            relative = path.relative_to(root).as_posix()
            folded = relative.casefold()
            previous = casefold_paths.get(folded)
            if previous is not None and previous != relative:
                raise CandidateStaticQABoundaryError("candidate-tree-casefold-collision")
            casefold_paths[folded] = relative
            if stat.S_ISDIR(details.st_mode):
                directories.append(path)
            elif stat.S_ISREG(details.st_mode):
                if int(details.st_nlink) != 1:
                    raise CandidateStaticQABoundaryError("candidate-tree-hardlink")
                files.append(path)
            else:
                raise CandidateStaticQABoundaryError("candidate-tree-special-file")
    return sorted(files, key=lambda item: item.relative_to(root).as_posix())


def _snapshot_tree(root: Path) -> dict[str, Any]:
    rows: list[dict[str, object]] = []
    for path in _bounded_files(root):
        before = path.stat()
        digest = _sha256_file(path)
        after = path.stat()
        if (
            before.st_size != after.st_size
            or before.st_mtime_ns != after.st_mtime_ns
            or before.st_ino != after.st_ino
        ):
            raise CandidateStaticQABoundaryError("candidate-tree-mutated-during-read")
        rows.append(
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": digest,
                "bytes": int(after.st_size),
            }
        )
    rows.sort(key=lambda item: str(item["path"]))
    return {
        "tree_sha256": _json_sha256(rows),
        "file_count": len(rows),
        "total_bytes": sum(int(str(row["bytes"])) for row in rows),
        "files": rows,
    }


def _read_trusted_config(repo_root: Path) -> tuple[dict[str, Any], str]:
    path = repo_root / "aureon" / "operator" / "website_operator.defaults.json"
    if _is_link_or_reparse(path) or not path.is_file() or int(path.stat().st_nlink) != 1:
        raise CandidateStaticQABoundaryError("trusted-config-file-invalid")
    before = path.read_bytes()
    value = _strict_json_bytes(before, code="trusted-config-json-invalid")
    after = path.read_bytes()
    if before != after:
        raise CandidateStaticQABoundaryError("trusted-config-mutated-during-read")
    if not isinstance(value, Mapping) or value.get("schema") != CONFIG_SCHEMA:
        raise CandidateStaticQABoundaryError("trusted-config-schema-invalid")
    config = dict(value)
    for key in ("site", "ethos", "budgets", "checks", "packaging"):
        if not isinstance(config.get(key), Mapping):
            raise CandidateStaticQABoundaryError("trusted-config-shape-invalid")
    return config, _bytes_sha256(before)


def _decode_text(path: Path, *, code: str = "candidate-text-invalid-utf8") -> str:
    try:
        data = path.read_bytes()
        if data.startswith(b"\xef\xbb\xbf") or b"\x00" in data:
            raise CandidateStaticQABoundaryError(code)
        return data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise CandidateStaticQABoundaryError(code) from exc


def _line_for_offset(text: str, offset: int) -> int:
    return text.count("\n", 0, max(0, offset)) + 1


def _strip_c_style_comments(text: str, *, line_comments: bool) -> str:
    output = list(text)
    index = 0
    quote = ""
    while index < len(text):
        current = text[index]
        following = text[index + 1] if index + 1 < len(text) else ""
        if quote:
            if current == "\\":
                index += 2
                continue
            if current == quote:
                quote = ""
            index += 1
            continue
        if current in {"'", '"', "`"}:
            quote = current
            index += 1
            continue
        if current == "/" and following == "*":
            output[index] = " "
            output[index + 1] = " "
            index += 2
            while index < len(text):
                output[index] = "\n" if text[index] == "\n" else " "
                if text[index] == "*" and index + 1 < len(text) and text[index + 1] == "/":
                    output[index + 1] = " "
                    index += 2
                    break
                index += 1
            continue
        if line_comments and current == "/" and following == "/":
            output[index] = " "
            output[index + 1] = " "
            index += 2
            while index < len(text) and text[index] not in "\r\n":
                output[index] = " "
                index += 1
            continue
        index += 1
    return "".join(output)


def _strip_css_comments_compact(text: str) -> str:
    output: list[str] = []
    index = 0
    quote = ""
    while index < len(text):
        current = text[index]
        following = text[index + 1] if index + 1 < len(text) else ""
        if quote:
            output.append(current)
            if current == "\\" and index + 1 < len(text):
                output.append(text[index + 1])
                index += 2
                continue
            if current == quote:
                quote = ""
            index += 1
            continue
        if current in {"'", '"'}:
            quote = current
            output.append(current)
            index += 1
            continue
        if current == "/" and following == "*":
            index += 2
            while index < len(text):
                if text[index] in "\r\n":
                    output.append(text[index])
                if text[index] == "*" and index + 1 < len(text) and text[index + 1] == "/":
                    index += 2
                    break
                index += 1
            continue
        output.append(current)
        index += 1
    return "".join(output)


def _decode_css_escape(text: str, index: int) -> tuple[str, int]:
    if index + 1 >= len(text):
        return "", index + 1
    following = text[index + 1]
    if following in "\r\n\f":
        next_index = index + 2
        if following == "\r" and next_index < len(text) and text[next_index] == "\n":
            next_index += 1
        return "", next_index
    if following.casefold() in "0123456789abcdef":
        end = index + 1
        while end < len(text) and end < index + 7 and text[end].casefold() in "0123456789abcdef":
            end += 1
        codepoint = int(text[index + 1 : end], 16)
        if end < len(text) and text[end].isspace():
            end += 1
        if codepoint == 0 or codepoint > 0x10FFFF:
            return "\ufffd", end
        return chr(codepoint), end
    return following, index + 2


def _decode_css_identifier_escapes(text: str) -> str:
    output: list[str] = []
    index = 0
    quote = ""
    while index < len(text):
        current = text[index]
        if quote:
            output.append(current)
            if current == "\\" and index + 1 < len(text):
                output.append(text[index + 1])
                index += 2
                continue
            if current == quote:
                quote = ""
            index += 1
            continue
        if current in {"'", '"'}:
            quote = current
            output.append(current)
            index += 1
            continue
        if current == "\\":
            decoded, index = _decode_css_escape(text, index)
            output.append(decoded)
            continue
        output.append(current)
        index += 1
    return "".join(output)


def _decode_css_value_escapes(text: str) -> str:
    output: list[str] = []
    index = 0
    while index < len(text):
        if text[index] == "\\":
            decoded, index = _decode_css_escape(text, index)
            output.append(decoded)
        else:
            output.append(text[index])
            index += 1
    return "".join(output)


def _offset_is_outside_string(text: str, offset: int) -> bool:
    index = 0
    quote = ""
    while index < min(offset, len(text)):
        current = text[index]
        if quote:
            if current == "\\":
                index += 2
                continue
            if current == quote:
                quote = ""
        elif current in {"'", '"', "`"}:
            quote = current
        index += 1
    return not quote


def _css_at_rule_offset_is_structural(text: str, offset: int) -> bool:
    if not _offset_is_outside_string(text, offset):
        return False
    prefix = text[:offset]
    boundary = max(prefix.rfind("{"), prefix.rfind("}"), prefix.rfind(";"))
    return not prefix[boundary + 1 :].strip()


def _css_selector_subject(selector: str) -> str:
    """Return the final top-level compound selector without regex backtracking."""

    boundary = 0
    parentheses = 0
    brackets = 0
    quote = ""
    index = 0
    while index < len(selector):
        current = selector[index]
        if quote:
            if current == "\\":
                index += 2
                continue
            if current == quote:
                quote = ""
        elif current in {"'", '"', "`"}:
            quote = current
        elif current == "(":
            parentheses += 1
        elif current == ")" and parentheses:
            parentheses -= 1
        elif current == "[":
            brackets += 1
        elif current == "]" and brackets:
            brackets -= 1
        elif not parentheses and not brackets and (current in {">", "+", "~"} or current.isspace()):
            boundary = index + 1
        index += 1
    return selector[boundary:].strip()


def _css_subject_definitely_names_tag(subject: str, tag: str) -> bool:
    compact = re.sub(r"\s+", "", subject.casefold())
    if "::" in compact:
        return False
    escaped = re.escape(tag.casefold())
    if re.match(
        rf"^(?:[a-z_][a-z0-9_-]*\|)?{escaped}(?=$|[.#:\[])",
        compact,
    ):
        return True
    return (
        re.fullmatch(
            rf"(?:\*)?:(?:is|where)\(\s*{escaped}\s*\)",
            compact,
        )
        is not None
    )


def _css_compound_positive_tokens(subject: str) -> tuple[set[str], set[str]]:
    if "::" in subject:
        # A pseudo-element rule hides the generated box, not the originating
        # semantic element.  Treating `.hero::before` as `.hero` made every
        # V44 page hero disappear from the static inventory.
        return set(), set()
    classes: set[str] = set()
    identifiers: set[str] = set()
    parentheses = 0
    brackets = 0
    quote = ""
    index = 0
    while index < len(subject):
        current = subject[index]
        if quote:
            if current == "\\":
                index += 2
                continue
            if current == quote:
                quote = ""
        elif current in {"'", '"', "`"}:
            quote = current
        elif current == "(":
            parentheses += 1
        elif current == ")" and parentheses:
            parentheses -= 1
        elif current == "[":
            brackets += 1
        elif current == "]" and brackets:
            brackets -= 1
        elif not parentheses and not brackets and current in {"#", "."}:
            match = re.match(r"[A-Za-z_][A-Za-z0-9_-]*", subject[index + 1 :])
            if match is not None:
                target = identifiers if current == "#" else classes
                target.add(match.group(0).casefold())
                index += len(match.group(0))
        index += 1
    return classes, identifiers


def _css_attribute_positive_tokens(subject: str) -> tuple[set[str], set[str]]:
    classes: set[str] = set()
    identifiers: set[str] = set()
    if "::" in subject:
        return classes, identifiers
    for match in re.finditer(
        r"\[\s*(?P<name>class|id)\s*(?P<operator>~=|\|=|\^=|\$=|\*=|=)\s*"
        r"(?P<quote>['\"]?)(?P<value>[A-Za-z_][A-Za-z0-9_-]*)"
        r"(?P=quote)\s*(?:[iIsS]\s*)?\]",
        subject,
        re.IGNORECASE,
    ):
        name = match.group("name").casefold()
        operator = match.group("operator")
        value = match.group("value").casefold()
        if name == "id" and operator == "=":
            identifiers.add(value)
        elif name == "class" and operator in {"=", "~="}:
            classes.add(value)
    return classes, identifiers


def _css_selector_list_pseudo_arguments(subject: str) -> Iterator[str]:
    if "::" in subject:
        return
    lowered = subject.casefold()
    for match in re.finditer(r":(?:is|where)\s*\(", lowered):
        closing = _matching_closing_parenthesis(subject, match.end() - 1)
        if closing is None:
            raise CandidateStaticQABoundaryError("candidate-css-structure-invalid")
        yield subject[match.end() : closing]


def _css_subject_positive_tokens(
    subject: str,
    *,
    depth: int = 0,
) -> tuple[set[str], set[str], set[str]]:
    """Return selectors that positively match the rule's subject element.

    This is deliberately one-way.  Negative and relational pseudos are not
    interpreted, while `:is()` and `:where()` alternatives are recursively
    inspected because each positive alternative can select a hidden semantic
    element.
    """

    if depth > 8:
        raise CandidateStaticQABoundaryError("candidate-css-complexity-limit")
    compact = re.sub(r"\s+", "", subject.casefold())
    if "::" in compact:
        return set(), set(), set()
    classes, identifiers = _css_compound_positive_tokens(subject)
    attribute_classes, attribute_ids = _css_attribute_positive_tokens(subject)
    classes.update(attribute_classes)
    identifiers.update(attribute_ids)
    tags = {
        semantic_tag
        for semantic_tag in ("body", "h1", "main")
        if _css_subject_definitely_names_tag(subject, semantic_tag)
    }
    if compact in {"*", "*|*"}:
        tags.update({"body", "h1", "main"})
    for arguments in _css_selector_list_pseudo_arguments(subject):
        for alternative in _css_split_top_level(arguments, ","):
            nested_classes, nested_ids, nested_tags = _css_subject_positive_tokens(
                alternative,
                depth=depth + 1,
            )
            classes.update(nested_classes)
            identifiers.update(nested_ids)
            tags.update(nested_tags)
    return classes, identifiers, tags


def _css_attribute_selectors(subject: str) -> Iterator[tuple[str, str, str, str]]:
    for match in re.finditer(
        r"\[\s*(?P<name>[A-Za-z_][A-Za-z0-9_:-]*)\s*"
        r"(?:(?P<operator>~=|\|=|\^=|\$=|\*=|=)\s*"
        r"(?P<quote>['\"]?)(?P<value>[^'\"\]\s]+)(?P=quote))?"
        r"\s*(?P<flag>[iIsS]?)\s*\]",
        subject,
    ):
        yield (
            match.group("name").casefold(),
            match.group("operator") or "",
            match.group("value") or "",
            match.group("flag").casefold(),
        )


def _css_attribute_selector_matches(
    attributes: Mapping[str, str],
    *,
    name: str,
    operator: str,
    expected: str,
    flag: str,
) -> bool:
    if name not in attributes:
        return False
    if not operator:
        return True
    observed = attributes[name]
    if flag == "i":
        observed = observed.casefold()
        expected = expected.casefold()
    if operator == "=":
        return observed == expected
    if operator == "~=":
        return expected in observed.split()
    if operator == "|=":
        return observed == expected or observed.startswith(expected + "-")
    if operator == "^=":
        return observed.startswith(expected)
    if operator == "$=":
        return observed.endswith(expected)
    if operator == "*=":
        return expected in observed
    return True


def _css_simple_compound_matches(
    subject: str,
    *,
    tag: str,
    attributes: Mapping[str, str],
) -> bool:
    compact = re.sub(r"\s+", "", subject.casefold())
    if not compact or any(character in compact for character in "() >+~"):
        return False
    explicit_tag = re.match(
        r"^(?:(?:[a-z_][a-z0-9_-]*|\*)\|)?(?P<tag>[a-z_][a-z0-9_-]*|\*)",
        compact,
    )
    if explicit_tag is not None and explicit_tag.group("tag") not in {"*", tag}:
        return False
    classes, identifiers = _css_compound_positive_tokens(subject)
    class_tokens = {token.casefold() for token in attributes.get("class", "").split() if token}
    if not classes.issubset(class_tokens):
        return False
    element_id = attributes.get("id", "").casefold()
    if identifiers and element_id not in identifiers:
        return False
    return all(
        _css_attribute_selector_matches(
            attributes,
            name=name,
            operator=operator,
            expected=expected,
            flag=flag,
        )
        for name, operator, expected, flag in _css_attribute_selectors(subject)
    )


def _css_compound_could_match_element(
    subject: str,
    *,
    tag: str,
    attributes: Mapping[str, str],
    depth: int = 0,
) -> bool:
    if depth > 8 or "::" in subject:
        return False
    compact = re.sub(r"\s+", "", subject.casefold())
    if ":root" in compact and tag != "html":
        return False
    explicit_tag = re.match(
        r"^(?:(?:[a-z_][a-z0-9_-]*|\*)\|)?(?P<tag>[a-z_][a-z0-9_-]*|\*)",
        compact,
    )
    if explicit_tag is not None and explicit_tag.group("tag") not in {"*", tag}:
        return False
    classes, identifiers = _css_compound_positive_tokens(subject)
    class_tokens = {token.casefold() for token in attributes.get("class", "").split() if token}
    if not classes.issubset(class_tokens):
        return False
    element_id = attributes.get("id", "").casefold()
    if identifiers and element_id not in identifiers:
        return False
    if not all(
        _css_attribute_selector_matches(
            attributes,
            name=name,
            operator=operator,
            expected=expected,
            flag=flag,
        )
        for name, operator, expected, flag in _css_attribute_selectors(subject)
    ):
        return False

    lowered = subject.casefold()
    for match in re.finditer(r":(?P<kind>is|where|not)\s*\(", lowered):
        closing = _matching_closing_parenthesis(subject, match.end() - 1)
        if closing is None:
            raise CandidateStaticQABoundaryError("candidate-css-structure-invalid")
        alternatives = _css_split_top_level(subject[match.end() : closing], ",")
        kind = match.group("kind")
        if kind in {"is", "where"} and not any(
            _css_compound_could_match_element(
                alternative,
                tag=tag,
                attributes=attributes,
                depth=depth + 1,
            )
            for alternative in alternatives
        ):
            return False
        if kind == "not" and any(
            _css_simple_compound_matches(
                alternative,
                tag=tag,
                attributes=attributes,
            )
            for alternative in alternatives
        ):
            return False
    return True


def _css_selector_compound_chain(
    selector: str,
) -> tuple[list[str], list[str]] | None:
    """Return top-level compounds and the combinator joining each pair.

    Sibling combinators require sibling identity that the visibility tree does
    not retain.  They therefore stay on the conservative fallback path.  Child
    and descendant combinators are retained exactly so an unrelated wrapper
    cannot satisfy a direct-parent constraint.
    """

    compounds: list[str] = []
    combinators: list[str] = []
    current: list[str] = []
    pending_combinator: str | None = None
    parentheses = 0
    brackets = 0
    quote = ""
    index = 0
    while index < len(selector):
        character = selector[index]
        if quote:
            current.append(character)
            if character == "\\":
                if index + 1 < len(selector):
                    current.append(selector[index + 1])
                index += 2
                continue
            if character == quote:
                quote = ""
        elif character in {"'", '"'}:
            quote = character
            current.append(character)
        elif character == "(":
            parentheses += 1
            current.append(character)
        elif character == ")" and parentheses:
            parentheses -= 1
            current.append(character)
        elif character == "[":
            brackets += 1
            current.append(character)
        elif character == "]" and brackets:
            brackets -= 1
            current.append(character)
        elif not parentheses and not brackets and character in {"+", "~"}:
            return None
        elif not parentheses and not brackets and (character == ">" or character.isspace()):
            compound = "".join(current).strip()
            if compound:
                if compounds:
                    combinators.append(pending_combinator or " ")
                compounds.append(compound)
                current = []
                pending_combinator = " "
            if character == ">":
                pending_combinator = ">"
        else:
            if not current and compounds and pending_combinator is None:
                pending_combinator = " "
            current.append(character)
        index += 1
    compound = "".join(current).strip()
    if compound:
        if compounds:
            combinators.append(pending_combinator or " ")
        compounds.append(compound)
    if len(combinators) != max(0, len(compounds) - 1):
        raise CandidateStaticQABoundaryError("candidate-css-structure-invalid")
    return compounds, combinators


def _css_ancestor_constraints_could_match(
    selector: str,
    *,
    subject: str,
    ancestors: Sequence[tuple[str, Mapping[str, str]]],
) -> bool:
    chain = _css_selector_compound_chain(selector)
    if chain is None:
        return True
    compounds, combinators = chain
    if len(compounds) <= 1:
        return True
    if compounds[-1].strip().casefold() != subject.strip().casefold():
        return True
    descendant_position = len(ancestors)
    for compound_index in range(len(compounds) - 2, -1, -1):
        combinator = combinators[compound_index]
        matching: int | None
        if combinator == ">":
            matching = descendant_position - 1
            if matching < 0 or not _css_compound_could_match_element(
                compounds[compound_index],
                tag=ancestors[matching][0],
                attributes=ancestors[matching][1],
            ):
                return False
        else:
            matching = next(
                (
                    index
                    for index in range(descendant_position - 1, -1, -1)
                    if _css_compound_could_match_element(
                        compounds[compound_index],
                        tag=ancestors[index][0],
                        attributes=ancestors[index][1],
                    )
                ),
                None,
            )
            if matching is None:
                return False
        if matching is None:
            return False
        descendant_position = matching
    return True


def _css_selector_direct_critical_indices(
    selector: str,
    critical_elements: Sequence[_CssRenderedElement],
) -> set[int]:
    subject = _css_selector_subject(selector)
    if "::" in subject:
        return set()
    return {
        index
        for index, element in enumerate(critical_elements)
        if _css_compound_could_match_element(
            subject,
            tag=element.tag,
            attributes=element.attributes,
        )
        and _css_ancestor_constraints_could_match(
            selector,
            subject=subject,
            ancestors=element.ancestors,
        )
    }


def _css_combine_nested_selectors(parent: str, nested: str) -> str:
    combined: list[str] = []
    for parent_selector in _css_split_top_level(parent, ","):
        for nested_selector in _css_split_top_level(nested, ","):
            parent_part = parent_selector.strip()
            nested_part = nested_selector.strip()
            if not parent_part or not nested_part:
                continue
            combined.append(
                nested_part.replace("&", parent_part)
                if "&" in nested_part
                else f"{parent_part} {nested_part}"
            )
    if not combined:
        raise CandidateStaticQABoundaryError("candidate-css-structure-invalid")
    return ",".join(combined)


def _css_split_top_level(text: str, delimiter: str) -> list[str]:
    parts: list[str] = []
    boundary = 0
    parentheses = 0
    brackets = 0
    quote = ""
    index = 0
    while index < len(text):
        current = text[index]
        if quote:
            if current == "\\":
                index += 2
                continue
            if current == quote:
                quote = ""
        elif current in {"'", '"'}:
            quote = current
        elif current == "(":
            parentheses += 1
        elif current == ")":
            if not parentheses:
                raise CandidateStaticQABoundaryError("candidate-css-structure-invalid")
            parentheses -= 1
        elif current == "[":
            brackets += 1
        elif current == "]":
            if not brackets:
                raise CandidateStaticQABoundaryError("candidate-css-structure-invalid")
            brackets -= 1
        elif not parentheses and not brackets and current == delimiter:
            parts.append(text[boundary:index])
            boundary = index + 1
        index += 1
    if quote or parentheses or brackets:
        raise CandidateStaticQABoundaryError("candidate-css-structure-invalid")
    parts.append(text[boundary:])
    return parts


def _css_declarations(body: str) -> Iterator[tuple[str, str]]:
    for raw_declaration in _css_split_top_level(body, ";"):
        declaration = raw_declaration.strip()
        if not declaration:
            continue
        parts = _css_split_top_level(declaration, ":")
        if len(parts) < 2:
            continue
        name = parts[0].strip().casefold()
        value = ":".join(parts[1:]).strip()
        if name:
            yield name, value


def _css_constant_number(value: str) -> float | None:
    candidate = value.strip().casefold()
    if candidate.startswith("calc("):
        closing = _matching_closing_parenthesis(candidate, 4)
        if closing != len(candidate) - 1:
            return None
        candidate = candidate[5:closing]
    elif candidate.endswith("%"):
        candidate = candidate[:-1]
    if not candidate or len(candidate) > 128 or re.fullmatch(r"[0-9eE+\-*/%().\s]+", candidate) is None:
        return None
    try:
        parsed = ast.parse(candidate, mode="eval")
    except SyntaxError:
        return None
    nodes = 0

    def evaluate(node: ast.AST) -> float:
        nonlocal nodes
        nodes += 1
        if nodes > 64:
            raise ValueError
        if isinstance(node, ast.Expression):
            return evaluate(node.body)
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, (int, float))
            and not isinstance(node.value, bool)
        ):
            return float(node.value)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            operand = evaluate(node.operand)
            return operand if isinstance(node.op, ast.UAdd) else -operand
        if isinstance(node, ast.BinOp):
            left = evaluate(node.left)
            right = evaluate(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                return left / right
            if isinstance(node.op, ast.Mod):
                return left % right
        raise ValueError

    try:
        result = evaluate(parsed)
    except (ValueError, ZeroDivisionError, OverflowError):
        return None
    return result if math.isfinite(result) else None


_CSS_LENGTH_UNITS = frozenset(
    {
        "",
        "%",
        "cap",
        "ch",
        "cm",
        "cqb",
        "cqh",
        "cqi",
        "cqmax",
        "cqmin",
        "cqw",
        "dvb",
        "dvh",
        "dvi",
        "dvw",
        "em",
        "ex",
        "ic",
        "in",
        "lh",
        "lvb",
        "lvh",
        "lvi",
        "lvw",
        "mm",
        "pc",
        "pt",
        "px",
        "q",
        "rem",
        "rlh",
        "svb",
        "svh",
        "svi",
        "svw",
        "vb",
        "vh",
        "vi",
        "vmax",
        "vmin",
        "vw",
    }
)
_CSS_ABSOLUTE_LENGTH_TO_PX = {
    "cm": 96.0 / 2.54,
    "in": 96.0,
    "mm": 96.0 / 25.4,
    "pc": 16.0,
    "pt": 96.0 / 72.0,
    "px": 1.0,
    "q": 96.0 / 101.6,
}
_CSS_DYNAMIC_VALUE = re.compile(r"\b(?:calc|clamp|env|max|min|var)\s*\(", re.IGNORECASE)


def _css_split_top_level_whitespace(text: str) -> list[str]:
    parts: list[str] = []
    boundary: int | None = None
    parentheses = 0
    brackets = 0
    quote = ""
    index = 0
    while index < len(text):
        current = text[index]
        if quote:
            if current == "\\":
                index += 2
                continue
            if current == quote:
                quote = ""
        elif current in {"'", '"'}:
            quote = current
        elif current == "(":
            parentheses += 1
        elif current == ")":
            if not parentheses:
                raise CandidateStaticQABoundaryError("candidate-css-structure-invalid")
            parentheses -= 1
        elif current == "[":
            brackets += 1
        elif current == "]":
            if not brackets:
                raise CandidateStaticQABoundaryError("candidate-css-structure-invalid")
            brackets -= 1
        if not quote and not parentheses and not brackets and current.isspace():
            if boundary is not None:
                parts.append(text[boundary:index])
                boundary = None
        elif boundary is None:
            boundary = index
        index += 1
    if quote or parentheses or brackets:
        raise CandidateStaticQABoundaryError("candidate-css-structure-invalid")
    if boundary is not None:
        parts.append(text[boundary:])
    return parts


def _css_constant_dimension(value: str) -> tuple[float, str] | None:
    match = re.fullmatch(
        r"\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?)"
        r"(%|[a-z]+)?\s*",
        value,
        flags=re.IGNORECASE,
    )
    if match is None:
        return None
    unit = (match.group(2) or "").casefold()
    if unit not in _CSS_LENGTH_UNITS:
        return None
    try:
        number = float(match.group(1))
    except ValueError:
        return None
    return (number, unit) if math.isfinite(number) else None


def _css_comparable_dimension(value: tuple[float, str]) -> tuple[float, str]:
    number, unit = value
    if number == 0:
        return 0.0, "zero"
    if unit in _CSS_ABSOLUTE_LENGTH_TO_PX:
        return number * _CSS_ABSOLUTE_LENGTH_TO_PX[unit], "px"
    return number, unit


def _css_extent_is_empty(
    start: tuple[float, str],
    end: tuple[float, str],
) -> bool:
    start_number, start_unit = _css_comparable_dimension(start)
    end_number, end_unit = _css_comparable_dimension(end)
    if start_unit == "zero":
        start_unit = end_unit
    if end_unit == "zero":
        end_unit = start_unit
    if start_unit != end_unit:
        return False
    scale = max(1.0, abs(start_number), abs(end_number))
    return end_number < start_number or math.isclose(
        end_number,
        start_number,
        rel_tol=1e-12,
        abs_tol=1e-12 * scale,
    )


def _css_square_matrix_is_singular(rows: Sequence[Sequence[float]]) -> bool:
    size = len(rows)
    if size == 0 or any(len(row) != size for row in rows):
        return True
    matrix = [list(row) for row in rows]
    row_scales = [max((abs(value) for value in row), default=0.0) for row in matrix]
    if any(scale == 0 for scale in row_scales):
        return True
    for column in range(size):
        pivot_row = max(
            range(column, size),
            key=lambda row: abs(matrix[row][column]) / row_scales[row],
        )
        pivot_ratio = abs(matrix[pivot_row][column]) / row_scales[pivot_row]
        if pivot_ratio <= 1e-12:
            return True
        if pivot_row != column:
            matrix[column], matrix[pivot_row] = matrix[pivot_row], matrix[column]
            row_scales[column], row_scales[pivot_row] = (
                row_scales[pivot_row],
                row_scales[column],
            )
        pivot = matrix[column][column]
        for row in range(column + 1, size):
            factor = matrix[row][column] / pivot
            for offset in range(column + 1, size):
                matrix[row][offset] -= factor * matrix[column][offset]
            matrix[row][column] = 0.0
    return False


def _css_vectors_have_zero_area(
    first: tuple[float, float, float],
    second: tuple[float, float, float],
) -> bool:
    scale = max(*(abs(value) for value in (*first, *second)), 0.0)
    if scale == 0:
        return True
    first_scaled = tuple(value / scale for value in first)
    second_scaled = tuple(value / scale for value in second)
    cross = (
        first_scaled[1] * second_scaled[2] - first_scaled[2] * second_scaled[1],
        first_scaled[2] * second_scaled[0] - first_scaled[0] * second_scaled[2],
        first_scaled[0] * second_scaled[1] - first_scaled[1] * second_scaled[0],
    )
    return math.fsum(component * component for component in cross) <= 1e-24


def _css_translate_components(arguments: str) -> list[str]:
    comma_parts = [part.strip() for part in _css_split_top_level(arguments, ",")]
    if len(comma_parts) > 1:
        return comma_parts
    return _css_split_top_level_whitespace(arguments)


@dataclass
class _CssGeometryEffect:
    x: dict[str, float]
    y: dict[str, float]
    concealed: bool = False
    z: dict[str, float] = dataclass_field(default_factory=dict)
    matrix: tuple[tuple[float, ...], ...] | None = None


@dataclass
class _CssTransformStep:
    matrix: tuple[tuple[float, ...], ...]
    relative: tuple[dict[str, float], dict[str, float], dict[str, float]]
    concealed: bool = False


def _css_identity_matrix() -> tuple[tuple[float, ...], ...]:
    return tuple(tuple(1.0 if row == column else 0.0 for column in range(4)) for row in range(4))


def _css_matrix_multiply(
    left: Sequence[Sequence[float]],
    right: Sequence[Sequence[float]],
) -> tuple[tuple[float, ...], ...]:
    return tuple(
        tuple(
            math.fsum(left[row][offset] * right[offset][column] for offset in range(4)) for column in range(4)
        )
        for row in range(4)
    )


def _css_numeric_translation_matrix(
    x: float,
    y: float,
    z: float,
) -> tuple[tuple[float, ...], ...]:
    matrix = [list(row) for row in _css_identity_matrix()]
    matrix[0][3] = x
    matrix[1][3] = y
    matrix[2][3] = z
    return tuple(tuple(row) for row in matrix)


def _css_matrix_is_affine(matrix: Sequence[Sequence[float]]) -> bool:
    return all(
        math.isclose(matrix[3][index], expected, rel_tol=1e-12, abs_tol=1e-12)
        for index, expected in enumerate((0.0, 0.0, 0.0, 1.0))
    )


def _css_identity_geometry_effect() -> _CssGeometryEffect:
    return _CssGeometryEffect({}, {}, matrix=_css_identity_matrix())


def _css_compose_geometry_pair(
    left: _CssGeometryEffect,
    right: _CssGeometryEffect,
) -> _CssGeometryEffect:
    """Compose two CSS geometry effects for column-vector evaluation.

    `left` is applied before `right` in CSS declaration order, so the resulting
    point mapping is `left.matrix * right.matrix`.  Relative translations are
    retained by unit and mapped through the numeric left-hand linear portion.
    A projective left-hand transform cannot safely map a symbolic translation,
    so that case fails closed.
    """

    left_matrix = left.matrix or _css_identity_matrix()
    right_matrix = right.matrix or _css_identity_matrix()
    right_symbolic = (right.x, right.y, right.z)
    if any(right_symbolic) and not _css_matrix_is_affine(left_matrix):
        return _CssGeometryEffect({}, {}, concealed=True)
    symbolic: tuple[dict[str, float], dict[str, float], dict[str, float]] = (
        dict(left.x),
        dict(left.y),
        dict(left.z),
    )
    for output in range(3):
        for source in range(3):
            for unit, coefficient in right_symbolic[source].items():
                _css_add_coefficient(
                    symbolic[output],
                    unit,
                    left_matrix[output][source] * coefficient,
                )
    matrix = _css_matrix_multiply(left_matrix, right_matrix)
    projected_concealed, _ = _css_projected_matrix_geometry(matrix)
    return _CssGeometryEffect(
        symbolic[0],
        symbolic[1],
        concealed=left.concealed or right.concealed or projected_concealed,
        z=symbolic[2],
        matrix=matrix,
    )


def _css_dimension_term(value: str, *, axis: str) -> tuple[float, str] | None:
    parsed = _css_constant_dimension(value)
    if parsed is None:
        return None
    number, unit = parsed
    if unit == "":
        return (0.0, "px") if number == 0 else None
    if unit in _CSS_ABSOLUTE_LENGTH_TO_PX:
        return number * _CSS_ABSOLUTE_LENGTH_TO_PX[unit], "px"
    if unit == "%":
        return number, f"%{axis}"
    return number, unit


def _css_scale_number(value: str) -> float | None:
    stripped = value.strip()
    parsed = _css_constant_number(stripped)
    if parsed is None:
        return None
    return parsed / 100.0 if stripped.endswith("%") else parsed


def _css_angle_radians(value: str) -> float | None:
    match = re.fullmatch(
        r"\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?)"
        r"(deg|grad|rad|turn)?\s*",
        value,
        flags=re.IGNORECASE,
    )
    if match is None:
        return None
    number = float(match.group(1))
    unit = (match.group(2) or "").casefold()
    if not math.isfinite(number) or (not unit and number != 0):
        return None
    return {
        "": number,
        "deg": math.radians(number),
        "grad": number * math.pi / 200.0,
        "rad": number,
        "turn": number * math.tau,
    }[unit]


def _css_rotation_matrix(
    x: float,
    y: float,
    z: float,
    angle: float,
) -> tuple[tuple[float, ...], ...]:
    magnitude = math.sqrt(x * x + y * y + z * z)
    if magnitude == 0:
        return _css_identity_matrix()
    x /= magnitude
    y /= magnitude
    z /= magnitude
    cosine = math.cos(angle)
    sine = math.sin(angle)
    complement = 1.0 - cosine
    return (
        (
            complement * x * x + cosine,
            complement * x * y - sine * z,
            complement * x * z + sine * y,
            0.0,
        ),
        (
            complement * x * y + sine * z,
            complement * y * y + cosine,
            complement * y * z - sine * x,
            0.0,
        ),
        (
            complement * x * z - sine * y,
            complement * y * z + sine * x,
            complement * z * z + cosine,
            0.0,
        ),
        (0.0, 0.0, 0.0, 1.0),
    )


def _css_transform_function_list(value: str) -> list[tuple[str, str]] | None:
    lowered = value.strip().casefold()
    if lowered in {"inherit", "initial", "none", "revert", "revert-layer", "unset"}:
        return []
    functions: list[tuple[str, str]] = []
    index = 0
    while index < len(lowered):
        while index < len(lowered) and lowered[index].isspace():
            index += 1
        if index == len(lowered):
            break
        match = re.match(r"([a-z][a-z0-9]*)\s*\(", lowered[index:])
        if match is None:
            return None
        opening = index + match.end() - 1
        closing = _matching_closing_parenthesis(lowered, opening)
        if closing is None:
            raise CandidateStaticQABoundaryError("candidate-css-structure-invalid")
        functions.append((match.group(1), lowered[opening + 1 : closing]))
        if len(functions) > 256:
            raise CandidateStaticQABoundaryError("candidate-css-complexity-limit")
        index = closing + 1
    return functions


def _css_matrix_transform_step(
    function: str,
    arguments: str,
) -> _CssTransformStep:
    expected = 6 if function == "matrix" else 16
    parts = [part.strip() for part in _css_split_top_level(arguments, ",")]
    values = [_css_constant_number(part) for part in parts]
    if len(parts) != expected or any(value is None for value in values):
        return _CssTransformStep(_css_identity_matrix(), ({}, {}, {}), concealed=True)
    constants = [value for value in values if value is not None]
    matrix: tuple[tuple[float, ...], ...]
    if function == "matrix":
        matrix = (
            (constants[0], constants[2], 0.0, constants[4]),
            (constants[1], constants[3], 0.0, constants[5]),
            (0.0, 0.0, 1.0, 0.0),
            (0.0, 0.0, 0.0, 1.0),
        )
    else:
        matrix = tuple(tuple(constants[column * 4 + row] for column in range(4)) for row in range(4))
    return _CssTransformStep(matrix, ({}, {}, {}))


def _css_translation_transform_step(
    function: str,
    arguments: str,
) -> _CssTransformStep:
    components = _css_translate_components(arguments)
    expected = {
        "translate": {1, 2},
        "translate3d": {3},
        "translatex": {1},
        "translatey": {1},
        "translatez": {1},
    }
    if len(components) not in expected[function]:
        return _CssTransformStep(_css_identity_matrix(), ({}, {}, {}), concealed=True)
    values = ["0", "0", "0"]
    if function == "translatex":
        values[0] = components[0]
    elif function == "translatey":
        values[1] = components[0]
    elif function == "translatez":
        values[2] = components[0]
    else:
        values[: len(components)] = components
    numeric = [0.0, 0.0, 0.0]
    relative: tuple[dict[str, float], dict[str, float], dict[str, float]] = ({}, {}, {})
    for index, (component, axis) in enumerate(zip(values, ("x", "y", "z"), strict=True)):
        parsed = _css_dimension_term(component, axis=axis)
        if parsed is None or (axis == "z" and parsed[1].startswith("%")):
            return _CssTransformStep(_css_identity_matrix(), ({}, {}, {}), concealed=True)
        number, unit = parsed
        if unit == "px":
            numeric[index] = number
        elif number:
            relative[index][unit] = number
    return _CssTransformStep(
        _css_numeric_translation_matrix(*numeric),
        relative,
    )


def _css_scale_transform_step(
    function: str,
    arguments: str,
) -> _CssTransformStep:
    components = _css_translate_components(arguments)
    expected = {
        "scale": {1, 2},
        "scale3d": {3},
        "scalex": {1},
        "scaley": {1},
        "scalez": {1},
    }
    if len(components) not in expected[function]:
        return _CssTransformStep(_css_identity_matrix(), ({}, {}, {}), concealed=True)
    parsed = [_css_scale_number(component) for component in components]
    if any(value is None for value in parsed):
        return _CssTransformStep(_css_identity_matrix(), ({}, {}, {}), concealed=True)
    numbers = [value for value in parsed if value is not None]
    x = y = z = 1.0
    if function == "scale":
        x = numbers[0]
        y = numbers[1] if len(numbers) == 2 else x
    elif function == "scale3d":
        x, y, z = numbers
    elif function == "scalex":
        x = numbers[0]
    elif function == "scaley":
        y = numbers[0]
    else:
        z = numbers[0]
    return _CssTransformStep(
        (
            (x, 0.0, 0.0, 0.0),
            (0.0, y, 0.0, 0.0),
            (0.0, 0.0, z, 0.0),
            (0.0, 0.0, 0.0, 1.0),
        ),
        ({}, {}, {}),
    )


def _css_rotation_transform_step(
    function: str,
    arguments: str,
) -> _CssTransformStep:
    components = _css_translate_components(arguments)
    if function == "rotate3d":
        if len(components) != 4:
            return _CssTransformStep(_css_identity_matrix(), ({}, {}, {}), concealed=True)
        axis = [_css_constant_number(component) for component in components[:3]]
        angle = _css_angle_radians(components[3])
        if angle is None or any(value is None for value in axis):
            return _CssTransformStep(_css_identity_matrix(), ({}, {}, {}), concealed=True)
        x, y, z = (value for value in axis if value is not None)
    else:
        if len(components) != 1:
            return _CssTransformStep(_css_identity_matrix(), ({}, {}, {}), concealed=True)
        angle = _css_angle_radians(components[0])
        if angle is None:
            return _CssTransformStep(_css_identity_matrix(), ({}, {}, {}), concealed=True)
        x, y, z = {
            "rotate": (0.0, 0.0, 1.0),
            "rotatex": (1.0, 0.0, 0.0),
            "rotatey": (0.0, 1.0, 0.0),
            "rotatez": (0.0, 0.0, 1.0),
        }[function]
    return _CssTransformStep(
        _css_rotation_matrix(x, y, z, angle),
        ({}, {}, {}),
    )


def _css_skew_transform_step(
    function: str,
    arguments: str,
) -> _CssTransformStep:
    components = _css_translate_components(arguments)
    if function == "skew" and len(components) in {1, 2}:
        x_angle = _css_angle_radians(components[0])
        y_angle = _css_angle_radians(components[1]) if len(components) == 2 else 0.0
    elif function in {"skewx", "skewy"} and len(components) == 1:
        parsed = _css_angle_radians(components[0])
        x_angle = parsed if function == "skewx" else 0.0
        y_angle = parsed if function == "skewy" else 0.0
    else:
        return _CssTransformStep(_css_identity_matrix(), ({}, {}, {}), concealed=True)
    if x_angle is None or y_angle is None:
        return _CssTransformStep(_css_identity_matrix(), ({}, {}, {}), concealed=True)
    return _CssTransformStep(
        (
            (1.0, math.tan(x_angle), 0.0, 0.0),
            (math.tan(y_angle), 1.0, 0.0, 0.0),
            (0.0, 0.0, 1.0, 0.0),
            (0.0, 0.0, 0.0, 1.0),
        ),
        ({}, {}, {}),
    )


def _css_perspective_transform_step(arguments: str) -> _CssTransformStep:
    components = _css_translate_components(arguments)
    if components == ["none"]:
        return _CssTransformStep(_css_identity_matrix(), ({}, {}, {}))
    if len(components) != 1:
        return _CssTransformStep(_css_identity_matrix(), ({}, {}, {}), concealed=True)
    parsed = _css_dimension_term(components[0], axis="z")
    if parsed is None or parsed[1] != "px" or parsed[0] < 0:
        return _CssTransformStep(_css_identity_matrix(), ({}, {}, {}), concealed=True)
    distance = max(1.0, parsed[0])
    matrix = [list(row) for row in _css_identity_matrix()]
    matrix[3][2] = -1.0 / distance
    return _CssTransformStep(tuple(tuple(row) for row in matrix), ({}, {}, {}))


def _css_transform_step(function: str, arguments: str) -> _CssTransformStep:
    if function in {"matrix", "matrix3d"}:
        return _css_matrix_transform_step(function, arguments)
    if function in {"translate", "translate3d", "translatex", "translatey", "translatez"}:
        return _css_translation_transform_step(function, arguments)
    if function in {"scale", "scale3d", "scalex", "scaley", "scalez"}:
        return _css_scale_transform_step(function, arguments)
    if function in {"rotate", "rotate3d", "rotatex", "rotatey", "rotatez"}:
        return _css_rotation_transform_step(function, arguments)
    if function in {"skew", "skewx", "skewy"}:
        return _css_skew_transform_step(function, arguments)
    if function == "perspective":
        return _css_perspective_transform_step(arguments)
    return _CssTransformStep(_css_identity_matrix(), ({}, {}, {}), concealed=True)


def _css_projected_matrix_geometry(
    matrix: Sequence[Sequence[float]],
) -> tuple[bool, tuple[float, float]]:
    if _css_square_matrix_is_singular(matrix):
        return True, (0.0, 0.0)
    points: list[tuple[float, float, float]] = []
    w_scale = max(1.0, *(abs(value) for value in matrix[3]))
    w_epsilon = 1e-9 * w_scale
    for x, y in ((0.0, 0.0), (1.0, 0.0), (0.0, 1.0)):
        vector = (x, y, 0.0, 1.0)
        transformed = tuple(
            math.fsum(matrix[row][column] * vector[column] for column in range(4)) for row in range(4)
        )
        if not all(math.isfinite(value) for value in transformed) or transformed[3] <= w_epsilon:
            return True, (0.0, 0.0)
        points.append(
            (
                transformed[0] / transformed[3],
                transformed[1] / transformed[3],
                transformed[2] / transformed[3],
            )
        )
    first_axis = (
        points[1][0] - points[0][0],
        points[1][1] - points[0][1],
        points[1][2] - points[0][2],
    )
    second_axis = (
        points[2][0] - points[0][0],
        points[2][1] - points[0][1],
        points[2][2] - points[0][2],
    )
    if _css_vectors_have_zero_area(first_axis, second_axis):
        return True, (0.0, 0.0)
    projected_scale = max(
        1.0,
        abs(first_axis[0]),
        abs(first_axis[1]),
        abs(second_axis[0]),
        abs(second_axis[1]),
    )
    projected_area = first_axis[0] * second_axis[1] - first_axis[1] * second_axis[0]
    if abs(projected_area) <= 1e-12 * projected_scale * projected_scale:
        return True, (0.0, 0.0)
    return False, (points[0][0], points[0][1])


def _css_add_coefficient(target: dict[str, float], unit: str, value: float) -> None:
    target[unit] = target.get(unit, 0.0) + value
    if math.isclose(target[unit], 0.0, rel_tol=1e-12, abs_tol=1e-12):
        target.pop(unit)


def _css_axis_is_far_offscreen(axis: Mapping[str, float]) -> bool:
    positive = 0.0
    negative = 0.0
    for unit, value in axis.items():
        threshold = 1000.0 if unit == "px" else 100.0
        if value > 0:
            positive += value / threshold
        elif value < 0:
            negative += -value / threshold
    return positive >= 1.0 or negative >= 1.0


def _css_effect_is_concealing(effect: _CssGeometryEffect) -> bool:
    if effect.concealed:
        return True
    concealed, origin = _css_projected_matrix_geometry(
        effect.matrix or _css_identity_matrix(),
    )
    if concealed:
        return True
    x = dict(effect.x)
    y = dict(effect.y)
    _css_add_coefficient(x, "px", origin[0])
    _css_add_coefficient(y, "px", origin[1])
    return _css_axis_is_far_offscreen(x) or _css_axis_is_far_offscreen(y)


def _css_combine_geometry_effects(
    effects: Sequence[_CssGeometryEffect],
) -> _CssGeometryEffect:
    combined = _css_identity_geometry_effect()
    for effect in effects:
        combined = _css_compose_geometry_pair(combined, effect)
    return combined


def _css_transform_effect(value: str) -> _CssGeometryEffect:
    functions = _css_transform_function_list(value)
    if functions is None:
        return _CssGeometryEffect({}, {}, concealed=True)
    steps = [_css_transform_step(function, arguments) for function, arguments in functions]
    if any(step.concealed for step in steps):
        return _CssGeometryEffect({}, {}, concealed=True)
    has_relative = any(any(axis for axis in step.relative) for step in steps)
    if has_relative and any(not _css_matrix_is_affine(step.matrix) for step in steps):
        return _CssGeometryEffect({}, {}, concealed=True)
    matrix = _css_identity_matrix()
    symbolic: tuple[dict[str, float], dict[str, float], dict[str, float]] = ({}, {}, {})
    for step in steps:
        for output in range(3):
            for source in range(3):
                for unit, coefficient in step.relative[source].items():
                    _css_add_coefficient(
                        symbolic[output],
                        unit,
                        matrix[output][source] * coefficient,
                    )
        matrix = _css_matrix_multiply(matrix, step.matrix)
    concealed, _ = _css_projected_matrix_geometry(matrix)
    return _CssGeometryEffect(
        dict(symbolic[0]),
        dict(symbolic[1]),
        concealed,
        z=dict(symbolic[2]),
        matrix=matrix,
    )


def _css_individual_translate_effect(value: str) -> _CssGeometryEffect:
    lowered = value.strip().casefold()
    if lowered in {"inherit", "initial", "none", "revert", "revert-layer", "unset"}:
        return _css_identity_geometry_effect()
    components = _css_split_top_level_whitespace(lowered)
    if len(components) not in {1, 2, 3}:
        return _CssGeometryEffect({}, {}, concealed=True)
    values = [*components, *(["0"] * (3 - len(components)))]
    effect = _CssGeometryEffect({}, {})
    for index, axis in enumerate(("x", "y", "z")):
        parsed = _css_dimension_term(values[index], axis=axis)
        if parsed is None or (axis == "z" and parsed[1].startswith("%")):
            return _CssGeometryEffect({}, {}, concealed=True)
        number, unit = parsed
        if axis == "x" and number:
            _css_add_coefficient(effect.x, unit, number)
        elif axis == "y" and number:
            _css_add_coefficient(effect.y, unit, number)
        elif axis == "z" and number:
            _css_add_coefficient(effect.z, unit, number)
    return effect


def _css_individual_rotate_effect(value: str) -> _CssGeometryEffect:
    lowered = value.strip().casefold()
    if lowered in {"inherit", "initial", "none", "revert", "revert-layer", "unset"}:
        return _css_identity_geometry_effect()
    components = _css_split_top_level_whitespace(lowered)
    axis: tuple[float, float, float]
    angle_text: str
    if len(components) == 1:
        axis = (0.0, 0.0, 1.0)
        angle_text = components[0]
    elif len(components) == 2 and components[0] in {"x", "y", "z"}:
        axis = {
            "x": (1.0, 0.0, 0.0),
            "y": (0.0, 1.0, 0.0),
            "z": (0.0, 0.0, 1.0),
        }[components[0]]
        angle_text = components[1]
    elif len(components) == 4:
        parsed_axis = [_css_constant_number(component) for component in components[:3]]
        if any(component is None for component in parsed_axis):
            return _CssGeometryEffect({}, {}, concealed=True)
        axis = tuple(component for component in parsed_axis if component is not None)  # type: ignore[assignment]
        angle_text = components[3]
    else:
        return _CssGeometryEffect({}, {}, concealed=True)
    angle = _css_angle_radians(angle_text)
    if angle is None:
        return _CssGeometryEffect({}, {}, concealed=True)
    matrix = _css_rotation_matrix(*axis, angle)
    concealed, _ = _css_projected_matrix_geometry(matrix)
    return _CssGeometryEffect({}, {}, concealed, matrix=matrix)


def _css_individual_scale_effect(value: str) -> _CssGeometryEffect:
    lowered = value.strip().casefold()
    if lowered in {"inherit", "initial", "none", "revert", "revert-layer", "unset"}:
        return _css_identity_geometry_effect()
    components = _css_split_top_level_whitespace(lowered)
    if len(components) not in {1, 2, 3}:
        return _CssGeometryEffect({}, {}, concealed=True)
    parsed = [_css_scale_number(component) for component in components]
    if any(component is None for component in parsed):
        return _CssGeometryEffect({}, {}, concealed=True)
    numbers = [component for component in parsed if component is not None]
    x = numbers[0]
    y = numbers[1] if len(numbers) > 1 else x
    z = numbers[2] if len(numbers) > 2 else 1.0
    matrix = (
        (x, 0.0, 0.0, 0.0),
        (0.0, y, 0.0, 0.0),
        (0.0, 0.0, z, 0.0),
        (0.0, 0.0, 0.0, 1.0),
    )
    concealed, _ = _css_projected_matrix_geometry(matrix)
    return _CssGeometryEffect({}, {}, concealed, matrix=matrix)


def _css_expand_box_shorthand(value: str) -> tuple[str, str, str, str] | None:
    components = _css_split_top_level_whitespace(value)
    if len(components) == 1:
        return (components[0],) * 4
    if len(components) == 2:
        return components[0], components[1], components[0], components[1]
    if len(components) == 3:
        return components[0], components[1], components[2], components[1]
    if len(components) == 4:
        return components[0], components[1], components[2], components[3]
    return None


def _css_expand_axis_shorthand(value: str) -> tuple[str, str] | None:
    components = _css_split_top_level_whitespace(value)
    if len(components) == 1:
        return components[0], components[0]
    if len(components) == 2:
        return components[0], components[1]
    return None


def _css_geometry_declaration_values(
    declarations: Sequence[tuple[str, str]],
) -> dict[str, str]:
    resolved: dict[str, tuple[str, bool]] = {}

    def assign(property_name: str, property_value: str, important: bool) -> None:
        previous = resolved.get(property_name)
        if previous is None or important or not previous[1]:
            resolved[property_name] = property_value, important

    for name, raw_value in declarations:
        important = re.search(r"\s*!important\s*$", raw_value, flags=re.IGNORECASE) is not None
        value = (
            re.sub(
                r"\s*!important\s*$",
                "",
                raw_value,
                flags=re.IGNORECASE,
            )
            .strip()
            .casefold()
        )
        if name in {"rotate", "scale", "transform", "translate"}:
            assign(name, value, important)
        elif name == "inset":
            expanded = _css_expand_box_shorthand(value)
            if expanded is not None:
                for side, component in zip(("top", "right", "bottom", "left"), expanded, strict=True):
                    assign(side, component, important)
        elif name in {"inset-block", "inset-inline"}:
            expanded_axis = _css_expand_axis_shorthand(value)
            if expanded_axis is not None:
                axis = "block" if name == "inset-block" else "inline"
                assign(f"inset-{axis}-start", expanded_axis[0], important)
                assign(f"inset-{axis}-end", expanded_axis[1], important)
        elif name in {
            "bottom",
            "inset-block-end",
            "inset-block-start",
            "inset-inline-end",
            "inset-inline-start",
            "left",
            "right",
            "top",
        }:
            assign(name, value, important)
    return {name: value for name, (value, _) in resolved.items()}


def _css_position_effect(property_name: str, value: str) -> _CssGeometryEffect:
    lowered = value.strip().casefold()
    if lowered in {"auto", "inherit", "initial", "revert", "revert-layer", "unset"}:
        return _CssGeometryEffect({}, {})
    axis = "x" if property_name in {"inset-inline-end", "inset-inline-start", "left", "right"} else "y"
    parsed = _css_dimension_term(lowered, axis=axis)
    if parsed is None:
        return _CssGeometryEffect(
            {},
            {},
            concealed=_CSS_DYNAMIC_VALUE.search(lowered) is not None,
        )
    number, unit = parsed
    sign = -1.0 if property_name in {"bottom", "inset-block-end", "inset-inline-end", "right"} else 1.0
    effect = _CssGeometryEffect({}, {})
    if axis == "x" and number:
        _css_add_coefficient(effect.x, unit, sign * number)
    elif axis == "y" and number:
        _css_add_coefficient(effect.y, unit, sign * number)
    return effect


def _css_body_geometry_effects(body: str) -> dict[str, _CssGeometryEffect]:
    resolved = _css_geometry_declaration_values(list(_css_declarations(body)))
    effects: dict[str, _CssGeometryEffect] = {}
    transform_names = {"rotate", "scale", "transform", "translate"}
    for name in sorted(resolved):
        if name not in transform_names:
            effects[name] = _css_position_effect(name, resolved[name])
    if "translate" in resolved:
        effects["translate"] = _css_individual_translate_effect(resolved["translate"])
    if "rotate" in resolved:
        effects["rotate"] = _css_individual_rotate_effect(resolved["rotate"])
    if "scale" in resolved:
        effects["scale"] = _css_individual_scale_effect(resolved["scale"])
    if "transform" in resolved:
        effects["transform"] = _css_transform_effect(resolved["transform"])
    return effects


def _css_legacy_clip_is_concealing(value: str) -> bool:
    lowered = value.strip().casefold()
    match = re.fullmatch(r"rect\s*\((.*)\)", lowered, flags=re.DOTALL)
    if match is None:
        return False
    arguments = match.group(1)
    comma_parts = [part.strip() for part in _css_split_top_level(arguments, ",")]
    components = comma_parts if len(comma_parts) > 1 else _css_split_top_level_whitespace(arguments)
    if len(components) != 4:
        return _CSS_DYNAMIC_VALUE.search(arguments) is not None
    parsed: list[tuple[float, str] | None] = []
    for index, component in enumerate(components):
        if component == "auto":
            parsed.append((0.0, "") if index in {0, 3} else None)
            continue
        coordinate = _css_constant_dimension(component)
        if coordinate is None:
            return _CSS_DYNAMIC_VALUE.search(arguments) is not None
        parsed.append(coordinate)
    top, right, bottom, left = parsed
    horizontal_empty = left is not None and right is not None and _css_extent_is_empty(left, right)
    vertical_empty = top is not None and bottom is not None and _css_extent_is_empty(top, bottom)
    return horizontal_empty or vertical_empty


def _css_value_has_var_fallback(
    value: str,
    *,
    hidden_tokens: set[str],
    numeric_zero: bool = False,
    depth: int = 0,
) -> bool:
    if depth > 8:
        return True
    lowered = value.casefold()
    for match in re.finditer(r"\bvar\s*\(", lowered):
        closing = _matching_closing_parenthesis(lowered, match.end() - 1)
        if closing is None:
            raise CandidateStaticQABoundaryError("candidate-css-structure-invalid")
        arguments = _css_split_top_level(
            lowered[match.end() : closing],
            ",",
        )
        if len(arguments) < 2:
            continue
        fallback = ",".join(arguments[1:]).strip()
        canonical = re.sub(r"\s+", " ", fallback)
        if canonical in hidden_tokens:
            return True
        if numeric_zero and _css_constant_number(canonical) == 0:
            return True
        if _css_value_has_var_fallback(
            fallback,
            hidden_tokens=hidden_tokens,
            numeric_zero=numeric_zero,
            depth=depth + 1,
        ):
            return True
    return False


def _css_body_has_hidden_declaration(body: str) -> bool:
    declarations = list(_css_declarations(body))
    for name, raw_value in declarations:
        value = re.sub(
            r"\s*!important\s*$",
            "",
            raw_value,
            flags=re.IGNORECASE,
        ).strip()
        lowered = re.sub(r"\s+", " ", value.casefold())
        has_dynamic_value = _CSS_DYNAMIC_VALUE.search(lowered) is not None
        if name == "display" and (
            lowered == "none"
            or "var(" in lowered
            or _css_value_has_var_fallback(value, hidden_tokens={"none"})
        ):
            return True
        if name == "visibility" and (
            lowered in {"collapse", "hidden"}
            or "var(" in lowered
            or _css_value_has_var_fallback(
                value,
                hidden_tokens={"collapse", "hidden"},
            )
        ):
            return True
        if name == "content-visibility" and (
            lowered == "hidden"
            or "var(" in lowered
            or _css_value_has_var_fallback(value, hidden_tokens={"hidden"})
        ):
            return True
        if name == "opacity" and (
            _css_constant_number(value) == 0
            or has_dynamic_value
            or _css_value_has_var_fallback(
                value,
                hidden_tokens=set(),
                numeric_zero=True,
            )
        ):
            return True
        if name in {"-webkit-filter", "filter"}:
            for match in re.finditer(r"\bopacity\s*\(", lowered):
                closing = _matching_closing_parenthesis(lowered, match.end() - 1)
                if closing is None:
                    raise CandidateStaticQABoundaryError("candidate-css-structure-invalid")
                argument = lowered[match.end() : closing].strip()
                if (
                    _css_constant_number(argument) == 0
                    or re.search(r"\b(?:calc|clamp|env|max|min|var)\s*\(", argument) is not None
                ):
                    return True
        if name == "scale":
            arguments = [part for part in re.split(r"[\s,/]+", lowered) if part]
            if any(
                _css_constant_number(argument) == 0 or _CSS_DYNAMIC_VALUE.search(argument) is not None
                for argument in arguments
            ):
                return True
        if name == "clip-path" and lowered != "none":
            return True
        if name == "clip" and _css_legacy_clip_is_concealing(lowered):
            return True
        if name == "text-indent" and re.fullmatch(r"-[1-9]\d{3,}(?:\.\d+)?px", lowered):
            return True
    geometry = _css_combine_geometry_effects(list(_css_body_geometry_effects(body).values()))
    return _css_effect_is_concealing(geometry)


def _css_geometry_affected_indices(
    source_index: int,
    critical_elements: Sequence[_CssRenderedElement],
) -> set[int]:
    return {
        index
        for index, element in enumerate(critical_elements)
        if element.tag in {"body", "h1", "main"}
        and (index == source_index or source_index in element.ancestor_indices)
    }


def _css_geometry_effect_key(effect: _CssGeometryEffect) -> tuple[object, ...]:
    matrix = effect.matrix or _css_identity_matrix()

    def number_key(value: float) -> str:
        return (0.0 if math.isclose(value, 0.0, rel_tol=1e-12, abs_tol=1e-12) else float(value)).hex()

    def coefficients(values: Mapping[str, float]) -> tuple[tuple[str, str], ...]:
        return tuple(
            (unit, number_key(value))
            for unit, value in sorted(values.items())
            if not math.isclose(value, 0.0, rel_tol=1e-12, abs_tol=1e-12)
        )

    return (
        effect.concealed,
        tuple(number_key(value) for row in matrix for value in row),
        coefficients(effect.x),
        coefficients(effect.y),
        coefficients(effect.z),
    )


def _css_deduplicate_geometry_effects(
    effects: Sequence[_CssGeometryEffect],
) -> list[_CssGeometryEffect]:
    unique: dict[tuple[object, ...], _CssGeometryEffect] = {}
    for effect in effects:
        unique.setdefault(_css_geometry_effect_key(effect), effect)
    return list(unique.values())


def _css_source_geometry_alternatives(
    source_index: int,
    slots: Mapping[tuple[int, str], Sequence[_CssGeometryEffect]],
    *,
    state_limit: int,
) -> list[_CssGeometryEffect]:
    source_slots = {
        slot: alternatives
        for (candidate_index, slot), alternatives in slots.items()
        if candidate_index == source_index
    }
    if not source_slots:
        return [_css_identity_geometry_effect()]
    transform_order = {"translate": 0, "rotate": 1, "scale": 2, "transform": 3}
    ordered_slots = sorted(
        source_slots,
        key=lambda slot: (
            1 if slot in transform_order else 0,
            transform_order.get(slot, 0),
            slot,
        ),
    )
    states = [_css_identity_geometry_effect()]
    for slot in ordered_slots:
        options = list(source_slots[slot])
        states = _css_deduplicate_geometry_effects(
            [_css_compose_geometry_pair(state, option) for state in states for option in options]
        )
        if len(states) > state_limit:
            raise CandidateStaticQABoundaryError("candidate-css-complexity-limit")
    return states


def _css_geometry_alternatives_are_concealing(
    slots: Mapping[tuple[int, str], Sequence[_CssGeometryEffect]],
    *,
    target_index: int,
    critical_elements: Sequence[_CssRenderedElement],
) -> bool:
    if any(effect.concealed for alternatives in slots.values() for effect in alternatives):
        return True
    state_limit = 4096
    target = critical_elements[target_index]
    source_indices = [
        *target.ancestor_indices,
        target_index,
    ]
    states = [_css_identity_geometry_effect()]
    for source_index in source_indices:
        source_alternatives = _css_source_geometry_alternatives(
            source_index,
            slots,
            state_limit=state_limit,
        )
        states = _css_deduplicate_geometry_effects(
            [_css_compose_geometry_pair(state, source) for state in states for source in source_alternatives]
        )
        if len(states) > state_limit:
            raise CandidateStaticQABoundaryError("candidate-css-complexity-limit")
    return any(_css_effect_is_concealing(state) for state in states)


def _css_hidden_selectors(
    texts: Sequence[str],
    *,
    critical_elements: Sequence[_CssRenderedElement] | None = None,
) -> tuple[set[str], set[str], set[str]]:
    classes: set[str] = set()
    identifiers: set[str] = set()
    tags: set[str] = set()
    geometry_slots: dict[
        int,
        dict[tuple[int, str], list[_CssGeometryEffect]],
    ] = {}
    selector_match_operations = 0

    def record_geometry(
        source_index: int,
        effects: Mapping[str, _CssGeometryEffect],
    ) -> None:
        if critical_elements is None:
            return
        for target_index in _css_geometry_affected_indices(
            source_index,
            critical_elements,
        ):
            target_slots = geometry_slots.setdefault(target_index, {})
            for slot, effect in effects.items():
                if (
                    not effect.concealed
                    and not effect.x
                    and not effect.y
                    and not effect.z
                    and effect.matrix is None
                ):
                    continue
                target_slots.setdefault((source_index, slot), []).append(effect)

    if critical_elements is not None:
        for source_index, element in enumerate(critical_elements):
            inline_style = element.attributes.get("style", "")
            if not inline_style:
                continue
            inline_effects = _css_body_geometry_effects(inline_style)
            record_geometry(source_index, inline_effects)
            if _css_body_has_hidden_declaration(inline_style):
                tags.update(
                    critical_elements[target_index].tag
                    for target_index in _css_geometry_affected_indices(
                        source_index,
                        critical_elements,
                    )
                    if critical_elements[target_index].tag in {"body", "h1", "main"}
                )
    for text in texts:
        structural = _decode_css_identifier_escapes(_strip_css_comments_compact(text))
        for selectors, body in _css_visibility_leaf_rules(structural):
            body_hidden = _css_body_has_hidden_declaration(body)
            body_effects = _css_body_geometry_effects(body)
            if not body_hidden and not body_effects:
                continue
            for raw_selector in _css_split_top_level(selectors, ","):
                selector = raw_selector.strip().casefold()
                if "::" in selector:
                    continue
                if critical_elements is not None:
                    selector_match_operations += len(critical_elements)
                    if selector_match_operations > _CSS_MAX_SELECTOR_MATCH_OPERATIONS:
                        raise CandidateStaticQABoundaryError("candidate-css-complexity-limit")
                    source_indices = _css_selector_direct_critical_indices(
                        selector,
                        critical_elements,
                    )
                    if body_hidden:
                        target_indices: set[int] = set()
                        for source_index in source_indices:
                            target_indices.update(
                                _css_geometry_affected_indices(
                                    source_index,
                                    critical_elements,
                                )
                            )
                        tags.update(
                            critical_elements[target_index].tag
                            for target_index in target_indices
                            if critical_elements[target_index].tag in {"body", "h1", "main"}
                        )
                    for source_index in source_indices:
                        record_geometry(source_index, body_effects)
                    continue
                if not body_hidden:
                    continue
                class_match = re.fullmatch(r"(?:[a-z][a-z0-9_-]*)?\.([a-z_][a-z0-9_-]*)", selector)
                identifier_match = re.fullmatch(r"#([a-z_][a-z0-9_-]*)", selector)
                tag_match = re.fullmatch(r"[a-z][a-z0-9_-]*", selector)
                if class_match is not None:
                    classes.add(class_match.group(1))
                elif identifier_match is not None:
                    identifiers.add(identifier_match.group(1))
                elif tag_match is not None:
                    tags.add(tag_match.group(0))
                else:
                    subject = _css_selector_subject(selector)
                    subject_classes, subject_ids, subject_tags = _css_subject_positive_tokens(subject)
                    classes.update(subject_classes)
                    identifiers.update(subject_ids)
                    tags.update(subject_tags)
    if critical_elements is not None:
        tags.update(
            critical_elements[target_index].tag
            for target_index, slots in geometry_slots.items()
            if _css_geometry_alternatives_are_concealing(
                slots,
                target_index=target_index,
                critical_elements=critical_elements,
            )
            and critical_elements[target_index].tag in {"body", "h1", "main"}
        )
    return classes, identifiers, tags


def _css_visibility_leaf_rules(
    text: str,
) -> Iterator[tuple[str, str]]:
    """Yield visibility-relevant rules with one bounded iterative pass.

    Rules inside grouping at-rules are included conservatively: a condition can
    match a real user viewport, so it cannot be allowed to hide the only live
    semantic structure.  Declaration-only and animation at-rules remain opaque.
    Explicit depth and block budgets fail closed before adversarial nesting can
    escape the canonical receipt boundary.
    """

    stack = [_CssBlockFrame(kind="root", prelude="", content_start=0, boundary=0)]
    block_count = 0
    quote = ""
    index = 0
    while index < len(text):
        current = text[index]
        if quote:
            if current == "\\":
                index += 2
                continue
            if current == quote:
                quote = ""
            index += 1
            continue
        if current in {"'", '"'}:
            quote = current
            index += 1
            continue
        frame = stack[-1]
        if current == ";" and frame.kind in {"grouping", "root", "style"}:
            frame.boundary = index + 1
            index += 1
            continue
        if current == "{":
            block_count += 1
            if block_count > _CSS_MAX_BLOCKS or len(stack) > _CSS_MAX_NESTING:
                raise CandidateStaticQABoundaryError("candidate-css-complexity-limit")
            prelude = text[frame.boundary : index].strip()
            lowered_prelude = prelude.casefold()
            declaration_only_at_rule = re.match(
                r"@(?:-moz-|-webkit-)?(?:counter-style|font-face|font-feature-values|keyframes|page|property)"
                r"(?:\s|\{|$)",
                lowered_prelude,
            )
            if prelude.startswith("@") and declaration_only_at_rule is None:
                # Conditional and future grouping at-rules are user/viewport
                # reachable.  Unknown groupings therefore remain inspectable
                # instead of becoming an opaque hiding bypass.
                kind = "grouping"
            elif prelude.startswith("@"):
                kind = "opaque"
            elif frame.kind in {"grouping", "root"} and prelude:
                kind = "style"
            elif frame.kind == "style" and prelude:
                # CSS nesting.  A nested selector is independently inspected;
                # a malformed declaration-with-braces is intentionally treated
                # as a selector and can only make the audit more conservative.
                kind = "style"
            else:
                kind = "opaque"
            selector_context: str | None = None
            if kind == "grouping":
                selector_context = frame.selector_context
            elif kind == "style":
                selector_context = (
                    _css_combine_nested_selectors(frame.selector_context, prelude)
                    if frame.selector_context is not None
                    else prelude
                )
            stack.append(
                _CssBlockFrame(
                    kind=kind,
                    prelude=prelude,
                    content_start=index + 1,
                    boundary=index + 1,
                    selector_context=selector_context,
                )
            )
            index += 1
            continue
        if current == "}":
            if len(stack) == 1:
                raise CandidateStaticQABoundaryError("candidate-css-structure-invalid")
            completed = stack.pop()
            if completed.kind in {"grouping", "style"} and completed.selector_context is not None:
                yield completed.selector_context, text[completed.content_start : index]
            stack[-1].boundary = index + 1
        index += 1
    if quote or len(stack) != 1:
        raise CandidateStaticQABoundaryError("candidate-css-structure-invalid")


def _matching_closing_brace(text: str, opening: int) -> int | None:
    if opening < 0 or opening >= len(text) or text[opening] != "{":
        return None
    depth = 0
    quote = ""
    index = opening
    while index < len(text):
        current = text[index]
        if quote:
            if current == "\\":
                index += 2
                continue
            if current == quote:
                quote = ""
        elif current in {"'", '"', "`"}:
            quote = current
        elif current == "{":
            depth += 1
        elif current == "}":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return None


def _javascript_gate_controls_statement(text: str, condition_end: int) -> bool:
    def has_effect(statement: str) -> bool:
        structural = re.sub(
            r"[\s;]+",
            "",
            _javascript_structure_mask(statement),
        ).casefold()
        return (
            bool(structural)
            and re.fullmatch(
                r"(?:void(?:0|\(0\))|[+-]?(?:\d+(?:\.\d*)?|\.\d+)|"
                r"true|false|null|undefined|nan|\[\]|\{\})",
                structural,
            )
            is None
        )

    index = condition_end
    while index < len(text) and text[index].isspace():
        index += 1
    if index >= len(text) or text[index] == ";":
        return False
    if text[index] != "{":
        boundary = re.search(r"[;\r\n]", text[index:])
        statement = text[index : boundary.start() + index] if boundary is not None else text[index:]
        return has_effect(statement)
    closing = _matching_closing_brace(text, index)
    if closing is None:
        return False
    return has_effect(text[index + 1 : closing])


def _javascript_slash_starts_regex(text: str, index: int) -> bool:
    cursor = index - 1
    while cursor >= 0 and text[cursor].isspace():
        cursor -= 1
    if cursor < 0:
        return True
    if text[cursor] in "([{,:;=!?&|+-*%^~<>":
        return True
    end = cursor + 1
    while cursor >= 0 and (text[cursor].isalnum() or text[cursor] in "_$"):
        cursor -= 1
    return text[cursor + 1 : end].casefold() in {
        "await",
        "case",
        "delete",
        "do",
        "else",
        "in",
        "instanceof",
        "new",
        "of",
        "return",
        "throw",
        "typeof",
        "void",
        "yield",
    }


def _javascript_prefix_is_permitted_before_gate(text: str, offset: int) -> bool:
    index = 0
    directive_seen = False
    while index < offset:
        current = text[index]
        following = text[index + 1] if index + 1 < offset else ""
        if current.isspace() or current == ";":
            index += 1
            continue
        if current == "/" and following == "/":
            index += 2
            while index < offset and text[index] not in "\r\n":
                index += 1
            continue
        if current == "/" and following == "*":
            closing = text.find("*/", index + 2, offset)
            if closing < 0:
                return False
            index = closing + 2
            continue
        directive = re.match(r"(['\"])use strict\1\s*;", text[index:offset])
        if directive is not None and not directive_seen:
            directive_seen = True
            index += directive.end()
            continue
        return False
    return True


def _javascript_structure_mask(text: str) -> str:
    output = list(text)
    quote = ""
    template_raw = False
    template_expression_depths: list[int] = []
    index = 0
    while index < len(text):
        current = text[index]
        if template_raw:
            output[index] = " "
            if current == "\\":
                if index + 1 < len(text):
                    output[index + 1] = " "
                index += 2
                continue
            if current == "`":
                template_raw = False
            elif current == "$" and index + 1 < len(text) and text[index + 1] == "{":
                output[index + 1] = "{"
                template_expression_depths.append(1)
                template_raw = False
                index += 2
                continue
            index += 1
            continue
        if quote:
            output[index] = " "
            if current == "\\":
                if index + 1 < len(text):
                    output[index + 1] = " "
                index += 2
                continue
            if current == quote:
                quote = ""
        elif current in {"'", '"'}:
            quote = current
            output[index] = " "
        elif current == "`":
            template_raw = True
            output[index] = " "
        elif current == "/" and index + 1 < len(text) and text[index + 1] in {"*", "/"}:
            line_comment = text[index + 1] == "/"
            output[index] = output[index + 1] = " "
            index += 2
            while index < len(text):
                if line_comment and text[index] in "\r\n":
                    break
                output[index] = " "
                if (
                    not line_comment
                    and text[index] == "*"
                    and index + 1 < len(text)
                    and text[index + 1] == "/"
                ):
                    output[index + 1] = " "
                    index += 2
                    break
                index += 1
            continue
        elif current == "/" and _javascript_slash_starts_regex(text, index):
            output[index] = " "
            index += 1
            character_class = False
            while index < len(text):
                current = text[index]
                output[index] = " "
                if current == "\\":
                    if index + 1 < len(text):
                        output[index + 1] = " "
                    index += 2
                    continue
                if current == "[":
                    character_class = True
                elif current == "]":
                    character_class = False
                elif current == "/" and not character_class:
                    index += 1
                    while index < len(text) and text[index].isalpha():
                        output[index] = " "
                        index += 1
                    break
                elif current in "\r\n":
                    break
                index += 1
            continue
        elif template_expression_depths and current == "{":
            template_expression_depths[-1] += 1
        elif template_expression_depths and current == "}":
            template_expression_depths[-1] -= 1
            if template_expression_depths[-1] == 0:
                template_expression_depths.pop()
                template_raw = True
        index += 1
    if quote or template_raw or template_expression_depths:
        return " " * len(text)
    return "".join(output)


def _matching_mask_delimiter(
    text: str,
    opening: int,
    opening_character: str,
    closing_character: str,
) -> int | None:
    if opening < 0 or opening >= len(text) or text[opening] != opening_character:
        return None
    depth = 0
    for index in range(opening, len(text)):
        current = text[index]
        if current == opening_character:
            depth += 1
        elif current == closing_character:
            depth -= 1
            if depth == 0:
                return index
    return None


def _javascript_split_top_level(expression: str, operator: str) -> list[str]:
    parts: list[str] = []
    boundary = 0
    parentheses = 0
    brackets = 0
    braces = 0
    quote = ""
    index = 0
    while index < len(expression):
        current = expression[index]
        if quote:
            if current == "\\":
                index += 2
                continue
            if current == quote:
                quote = ""
        elif current in {"'", '"', "`"}:
            quote = current
        elif current == "(":
            parentheses += 1
        elif current == ")" and parentheses:
            parentheses -= 1
        elif current == "[":
            brackets += 1
        elif current == "]" and brackets:
            brackets -= 1
        elif current == "{":
            braces += 1
        elif current == "}" and braces:
            braces -= 1
        elif not parentheses and not brackets and not braces and expression.startswith(operator, index):
            parts.append(expression[boundary:index])
            boundary = index + len(operator)
            index += len(operator)
            continue
        index += 1
    parts.append(expression[boundary:])
    return parts


def _javascript_constant_number(expression: str) -> float | None:
    candidate = expression.strip()
    if not candidate or len(candidate) > 128 or re.fullmatch(r"[0-9eE+\-*/%().\s]+", candidate) is None:
        return None
    try:
        parsed = ast.parse(candidate, mode="eval")
    except SyntaxError:
        return None
    nodes = 0

    def evaluate(node: ast.AST) -> float:
        nonlocal nodes
        nodes += 1
        if nodes > 64:
            raise ValueError
        if isinstance(node, ast.Expression):
            return evaluate(node.body)
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, (int, float))
            and not isinstance(node.value, bool)
        ):
            return float(node.value)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            operand = evaluate(node.operand)
            return operand if isinstance(node.op, ast.UAdd) else -operand
        if isinstance(node, ast.BinOp):
            left = evaluate(node.left)
            right = evaluate(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                return left / right
            if isinstance(node.op, ast.Mod):
                return left % right
        raise ValueError

    try:
        result = evaluate(parsed)
    except (ValueError, ZeroDivisionError, OverflowError):
        return None
    return result if math.isfinite(result) else None


def _javascript_constant_truthiness(condition: str, *, depth: int = 0) -> bool | None:
    if depth > 16 or len(condition) > _JAVASCRIPT_MAX_CONSTANT_EXPRESSION:
        return None
    candidate = condition.strip()
    while candidate.startswith("("):
        closing = _matching_closing_parenthesis(candidate, 0)
        if closing != len(candidate) - 1:
            break
        candidate = candidate[1:closing].strip()
    compact = re.sub(r"\s+", "", candidate).casefold()
    if compact in {"false", "nan", "null", "undefined"}:
        return False
    if compact == "true":
        return True
    if compact in {"''", '""', "``"}:
        return False
    if len(compact) >= 2 and compact[0] == compact[-1] and compact[0] in {"'", '"', "`"}:
        return True
    if compact.startswith("boolean(") and compact.endswith(")"):
        return _javascript_constant_truthiness(
            candidate[candidate.find("(") + 1 : -1],
            depth=depth + 1,
        )
    if compact.startswith("!"):
        operand = _javascript_constant_truthiness(candidate[candidate.find("!") + 1 :], depth=depth + 1)
        return None if operand is None else not operand
    disjunction = _javascript_split_top_level(candidate, "||")
    if len(disjunction) > 1:
        values = [_javascript_constant_truthiness(part, depth=depth + 1) for part in disjunction]
        if any(value is True for value in values):
            return True
        return False if all(value is False for value in values) else None
    conjunction = _javascript_split_top_level(candidate, "&&")
    if len(conjunction) > 1:
        values = [_javascript_constant_truthiness(part, depth=depth + 1) for part in conjunction]
        if any(value is False for value in values):
            return False
        return True if all(value is True for value in values) else None
    comparison = _JAVASCRIPT_NUMBER_COMPARISON.fullmatch(compact)
    if comparison is not None:
        left = float(comparison.group("left"))
        right = float(comparison.group("right"))
        operator = comparison.group("operator")
        return {
            "<": left < right,
            "<=": left <= right,
            ">": left > right,
            ">=": left >= right,
            "==": left == right,
            "===": left == right,
            "!=": left != right,
            "!==": left != right,
        }[operator]
    if compact in {"true==false", "true===false", "false==true", "false===true"}:
        return False
    number = _javascript_constant_number(candidate)
    if number is not None:
        return number != 0
    return None


def _javascript_condition_is_statically_false(condition: str) -> bool:
    return _javascript_constant_truthiness(condition) is False


def _javascript_statement_span(mask: str, start: int, limit: int) -> tuple[int, int] | None:
    index = start
    while index < limit and mask[index].isspace():
        index += 1
    if index >= limit:
        return None
    if mask[index] == "{":
        closing = _matching_mask_delimiter(mask, index, "{", "}")
        if closing is None or closing >= limit:
            return None
        return index + 1, closing
    parentheses = 0
    brackets = 0
    braces = 0
    cursor = index
    while cursor < limit:
        current = mask[cursor]
        if current == "(":
            parentheses += 1
        elif current == ")" and parentheses:
            parentheses -= 1
        elif current == "[":
            brackets += 1
        elif current == "]" and brackets:
            brackets -= 1
        elif current == "{":
            braces += 1
        elif current == "}" and braces:
            braces -= 1
        elif not parentheses and not brackets and not braces and current == ";":
            return index, cursor + 1
        cursor += 1
    return index, limit


def _javascript_for_condition(header: str) -> bool | None:
    parts = _javascript_split_top_level(header, ";")
    if len(parts) != 3:
        return None
    condition = parts[1].strip()
    return True if not condition else _javascript_constant_truthiness(condition)


def _javascript_control_allows_offset(
    text: str,
    mask: str,
    offset: int,
    *,
    start: int,
    end: int,
) -> bool:
    control_nodes = 0
    for match in _JAVASCRIPT_CONTROL_START.finditer(mask, start, end):
        control_nodes += 1
        if control_nodes > _JAVASCRIPT_MAX_CONTROL_NODES:
            return False
        condition_end = _matching_mask_delimiter(mask, match.end() - 1, "(", ")")
        if condition_end is None or condition_end >= end:
            return False
        body = _javascript_statement_span(mask, condition_end + 1, end)
        if body is None:
            return False
        kind = match.group("kind").casefold()
        header = text[match.end() : condition_end]
        truth = (
            _javascript_for_condition(header) if kind == "for" else _javascript_constant_truthiness(header)
        )
        if body[0] <= offset < body[1] and truth is not True:
            return False
        if kind != "if":
            continue
        after = body[1] + (1 if body[1] < end and mask[body[1]] == "}" else 0)
        while after < end and mask[after].isspace():
            after += 1
        if not mask.startswith("else", after):
            continue
        else_body = _javascript_statement_span(mask, after + 4, end)
        if else_body is not None and else_body[0] <= offset < else_body[1] and truth is not False:
            return False
    return True


def _javascript_ternary_allows_offset(
    text: str,
    mask: str,
    offset: int,
    *,
    start: int,
) -> bool:
    lower = max(start, offset - 4_096)
    for question in range(lower, offset):
        if mask[question] != "?":
            continue
        previous = mask[question - 1] if question else ""
        following = mask[question + 1] if question + 1 < len(mask) else ""
        if previous == "?" or following in {"?", "."}:
            continue
        parentheses = 0
        brackets = 0
        braces = 0
        nested = 0
        colon: int | None = None
        cursor = question + 1
        while cursor < len(mask):
            current = mask[cursor]
            if current == "(":
                parentheses += 1
            elif current == ")" and parentheses:
                parentheses -= 1
            elif current == "[":
                brackets += 1
            elif current == "]" and brackets:
                brackets -= 1
            elif current == "{":
                braces += 1
            elif current == "}" and braces:
                braces -= 1
            elif not parentheses and not brackets and not braces:
                if current == "?":
                    nested += 1
                elif current == ":":
                    if nested:
                        nested -= 1
                    else:
                        colon = cursor
                        break
                elif current == ";":
                    break
            cursor += 1
        if colon is None:
            continue
        arm_end = colon + 1
        parentheses = brackets = braces = 0
        while arm_end < len(mask):
            current = mask[arm_end]
            if current == "(":
                parentheses += 1
            elif current == ")" and parentheses:
                parentheses -= 1
            elif current == "[":
                brackets += 1
            elif current == "]" and brackets:
                brackets -= 1
            elif current == "{":
                braces += 1
            elif current == "}" and braces:
                braces -= 1
            elif not parentheses and not brackets and not braces and current == ";":
                break
            arm_end += 1
        if not (question < offset < arm_end):
            continue
        boundary = question - 1
        while boundary >= start and mask[boundary] not in ";{}=,:":
            boundary -= 1
        condition = text[boundary + 1 : question].strip()
        condition = re.sub(r"^(?:return|throw)\s+", "", condition)
        truth = _javascript_constant_truthiness(condition)
        if offset < colon and truth is not True:
            return False
        if offset > colon and truth is not False:
            return False
    return True


def _javascript_gate_is_reachable(text: str, offset: int) -> bool:
    """Prove only the deliberately small successor-script gate grammar.

    A gate is accepted when its `if` begins at file scope and is outside every
    string, comment, RegExp literal, block, dead control arm, ternary arm, and
    prior `await` barrier.  Arbitrary function/call-graph reachability is not
    claimed here; the immutable V44 script set has a separate exact-hash
    compatibility capsule in ``reduced_motion``.
    """

    if not _javascript_prefix_is_permitted_before_gate(text, offset):
        return False
    mask = _javascript_structure_mask(text)
    if offset < 0 or offset + 2 > len(mask) or mask[offset : offset + 2].casefold() != "if":
        return False
    braces = 0
    parentheses = 0
    brackets = 0
    for current in mask[:offset]:
        if current == "{":
            braces += 1
        elif current == "}":
            braces -= 1
        elif current == "(":
            parentheses += 1
        elif current == ")":
            parentheses -= 1
        elif current == "[":
            brackets += 1
        elif current == "]":
            brackets -= 1
        if braces < 0 or parentheses < 0 or brackets < 0:
            return False
    if braces or parentheses or brackets:
        return False
    if not _javascript_control_allows_offset(
        text,
        mask,
        offset,
        start=0,
        end=len(mask),
    ):
        return False
    if not _javascript_ternary_allows_offset(
        text,
        mask,
        offset,
        start=0,
    ):
        return False
    return re.search(r"\bawait\b", mask[:offset]) is None


def _css_conditional_ranges(text: str) -> list[tuple[int, int]]:
    """Return structural conditional-block ranges in one bounded pass."""

    ranges: list[tuple[int, int]] = []
    stack: list[tuple[int, int | None]] = []
    boundary = 0
    quote = ""
    parentheses = 0
    brackets = 0
    index = 0
    while index < len(text):
        current = text[index]
        if quote:
            if current == "\\":
                index += 2
                continue
            if current == quote:
                quote = ""
            index += 1
            continue
        if current in {"'", '"'}:
            quote = current
        elif current == "(":
            parentheses += 1
        elif current == ")" and parentheses:
            parentheses -= 1
        elif current == "[":
            brackets += 1
        elif current == "]" and brackets:
            brackets -= 1
        elif not parentheses and not brackets:
            if current == ";":
                boundary = index + 1
            elif current == "{":
                prelude = text[boundary:index]
                match = _CSS_CONDITIONAL_AT_RULE.match(prelude)
                conditional_start = boundary + match.start("at") if match is not None else None
                stack.append((index, conditional_start))
                boundary = index + 1
            elif current == "}":
                if stack:
                    _, conditional_start = stack.pop()
                    if conditional_start is not None:
                        ranges.append((conditional_start, index))
                boundary = index + 1
        index += 1
    return sorted(ranges)


def _css_offset_is_in_conditional_scope(text: str, offset: int) -> bool:
    return any(start < offset < end for start, end in _css_conditional_ranges(text))


def _matching_closing_parenthesis(text: str, opening: int) -> int | None:
    if opening < 0 or opening >= len(text) or text[opening] != "(":
        return None
    depth = 0
    quote = ""
    index = opening
    while index < len(text):
        current = text[index]
        if quote:
            if current == "\\":
                index += 2
                continue
            if current == quote:
                quote = ""
        elif current in {"'", '"', "`"}:
            quote = current
        elif current == "(":
            depth += 1
        elif current == ")":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return None


def _css_top_level_quoted_strings(
    text: str,
    start: int,
    end: int,
) -> list[tuple[str, int]]:
    references: list[tuple[str, int]] = []
    depth = 0
    index = start
    while index < end:
        current = text[index]
        if current == "(":
            depth += 1
            index += 1
            continue
        if current == ")":
            depth = max(0, depth - 1)
            index += 1
            continue
        if current not in {"'", '"'}:
            index += 1
            continue
        quote = current
        quote_start = index
        index += 1
        value_start = index
        while index < end:
            if text[index] == "\\":
                index += 2
                continue
            if text[index] == quote:
                if depth == 0:
                    references.append((text[value_start:index], quote_start))
                index += 1
                break
            index += 1
    return references


def _meta_refresh_reference(content: str) -> str | None:
    raw = unescape(content).strip()
    if ";" not in raw:
        return None
    _, tail = raw.split(";", 1)
    candidate = tail.strip()
    explicit = re.match(r"url\s*=\s*", candidate, re.IGNORECASE)
    if explicit is not None:
        candidate = candidate[explicit.end() :].strip()
    if len(candidate) >= 2 and candidate[0] == candidate[-1] and candidate[0] in {"'", '"'}:
        candidate = candidate[1:-1].strip()
    return candidate


def _robots_suppression_tokens(content: str) -> set[str]:
    lowered = content.casefold()
    tokens = {token for token in re.split(r"[^a-z0-9_:-]+", lowered) if token}
    suppressed = tokens & {
        "noarchive",
        "nocache",
        "nofollow",
        "noimageindex",
        "noindex",
        "none",
        "nositelinkssearchbox",
        "nosnippet",
        "notranslate",
    }
    if re.search(
        r"\b(?:max-(?:snippet|video-preview)\s*:\s*0"
        r"|max-image-preview\s*:\s*none"
        r"|unavailable_after\s*:)",
        lowered,
    ):
        suppressed.add("restricted-preview")
    return suppressed


def _is_crawler_meta_name(value: str) -> bool:
    lowered = value.casefold()
    return (
        lowered == "robots"
        or "bot" in lowered
        or "crawler" in lowered
        or "spider" in lowered
        or lowered in {"slurp", "teoma"}
    )


def _canonical_robots_path(value: str) -> str | None:
    current = value.strip()
    for _ in range(4):
        if re.search(r"%(?![0-9a-f]{2})", current, re.IGNORECASE):
            return None
        try:
            decoded = unquote_to_bytes(current).decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            return None
        if decoded == current:
            break
        current = decoded
    if "%" in current or any(ord(character) < 0x20 or ord(character) == 0x7F for character in current):
        return None
    current = unicodedata.normalize("NFC", current).replace("\\", "/")
    return re.sub(r"/{2,}", "/", current).casefold()


def _robots_pattern_matches(pattern: str, route: str) -> bool:
    candidate = _canonical_robots_path(pattern)
    canonical_route = _canonical_robots_path(route)
    if candidate is None or canonical_route is None:
        return True
    if not candidate:
        return False
    anchored = candidate.endswith("$")
    if anchored:
        candidate = candidate[:-1]
    expression = re.escape(candidate).replace(r"\*", ".*")
    expression = f"^{expression}{'$' if anchored else ''}"
    return re.match(expression, canonical_route) is not None


def _robots_txt_blocks_critical(text: str, critical_routes: Sequence[str]) -> bool:
    active_agents: list[str] = []
    disallows: list[tuple[tuple[str, ...], str]] = []
    group_has_rules = False
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        name, value = (part.strip() for part in line.split(":", 1))
        lowered = name.casefold()
        if lowered == "user-agent":
            if group_has_rules:
                active_agents = []
                group_has_rules = False
            active_agents.append(value.casefold())
        elif lowered == "disallow" and active_agents:
            group_has_rules = True
            if value:
                disallows.append((tuple(active_agents), value))
        elif active_agents:
            group_has_rules = True
    routes: list[str] = []
    for route in critical_routes:
        if route == "index.html":
            routes.extend(("/", "/index.html"))
        elif route.endswith("/index.html"):
            routes.extend((f"/{route.removesuffix('index.html')}", f"/{route}"))
        else:
            routes.append(f"/{route}")
    return any(
        agents and any(_robots_pattern_matches(pattern, route) for route in routes)
        for agents, pattern in disallows
    )


def _apache_value(raw: str) -> str:
    value = raw.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _htaccess_has_indexing_suppression(text: str) -> bool:
    flattened = re.sub(r"\\\s*\r?\n", " ", text)
    lines = [
        line.split("#", 1)[0].strip() for line in flattened.splitlines() if line.split("#", 1)[0].strip()
    ]
    values: dict[str, str] = {}
    for line in lines:
        define = re.match(r"Define\s+([A-Za-z_][A-Za-z0-9_]*)\s+(.+)$", line, re.IGNORECASE)
        if define is not None:
            values[define.group(1).casefold()] = _apache_value(define.group(2))
        set_env = re.match(r"SetEnv\s+([A-Za-z_][A-Za-z0-9_]*)\s+(.+)$", line, re.IGNORECASE)
        if set_env is not None:
            values[set_env.group(1).casefold()] = _apache_value(set_env.group(2))
        if re.match(r"SetEnvIf(?:NoCase|Expr)?\b", line, re.IGNORECASE):
            for assignment in re.finditer(
                r"\b([A-Za-z_][A-Za-z0-9_]*)=(\"[^\"]*\"|'[^']*'|\S+)",
                line,
            ):
                values[assignment.group(1).casefold()] = _apache_value(assignment.group(2))
        for assignment in re.finditer(
            r"\[\s*E=([A-Za-z_][A-Za-z0-9_]*):([^,\]]+)",
            line,
            re.IGNORECASE,
        ):
            values[assignment.group(1).casefold()] = _apache_value(assignment.group(2))

    expansion = re.compile(
        r"\$\{(?P<define>[A-Za-z_][A-Za-z0-9_]*)\}"
        r"|%\{(?:ENV:)?(?P<env>[A-Za-z_][A-Za-z0-9_]*)\}e?",
        re.IGNORECASE,
    )

    def expand(raw: str) -> tuple[str, bool]:
        current = raw
        unresolved = False
        for _ in range(8):
            changed = False

            def replace(match: re.Match[str]) -> str:
                nonlocal changed, unresolved
                name = (match.group("define") or match.group("env") or "").casefold()
                value = values.get(name)
                if value is None:
                    unresolved = True
                    return match.group(0)
                changed = True
                return value

            updated = expansion.sub(replace, current)
            current = updated
            if not changed:
                break
        return current, unresolved or expansion.search(current) is not None

    for line in lines:
        if re.search(r"\bx-robots-tag\b", line, re.IGNORECASE):
            expanded, unresolved = expand(line)
            if unresolved or _robots_suppression_tokens(expanded):
                return True
    return False


class _HtmlInventory(HTMLParser):
    def __init__(
        self,
        *,
        hidden_classes: set[str],
        hidden_ids: set[str],
        hidden_tags: set[str],
    ) -> None:
        super().__init__(convert_charrefs=True)
        self._hidden_classes = hidden_classes
        self._hidden_ids = hidden_ids
        self._hidden_tags = hidden_tags
        self.elements: list[tuple[str, dict[str, str], int]] = []
        self.semantic_elements: list[tuple[str, dict[str, str], int]] = []
        self.nonvoid_self_closing: list[tuple[str, int]] = []
        self.visible_chunks: list[str] = []
        self.jsonld_blocks: list[tuple[str, int]] = []
        self.style_blocks: list[tuple[str, int]] = []
        self.title_blocks: list[tuple[str, int]] = []
        self._blocked_depth = 0
        self._inactive_depth = 0
        self._semantic_blocked_depth = 0
        self._head_depth = 0
        self._jsonld_line: int | None = None
        self._jsonld_chunks: list[str] = []
        self._title_line: int | None = None
        self._title_chunks: list[str] = []
        self._style_line: int | None = None
        self._style_chunks: list[str] = []
        self.parser_differential_elements: list[tuple[str, int]] = []
        self.css_rendered_elements: list[_CssRenderedElement] = []
        self._open_tags: list[
            tuple[
                str,
                bool,
                bool,
                bool,
                bool,
                bool,
                bool,
                bool,
                Mapping[str, str],
                int | None,
            ]
        ] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.casefold()
        if lowered in _PARSER_DIFFERENTIAL_ELEMENTS:
            self.parser_differential_elements.append((lowered, self.getpos()[0]))
        names = [key.casefold() for key, _ in attrs]
        if len(names) != len(set(names)):
            raise CandidateStaticQABoundaryError("candidate-html-duplicate-attribute")
        attributes = {key.casefold(): (value if value is not None else "") for key, value in attrs}
        class_tokens = {value.casefold() for value in attributes.get("class", "").split() if value}
        inline_style_hidden = _css_body_has_hidden_declaration(attributes.get("style", ""))
        enters_inactive = lowered in {"noembed", "noscript", "template"}
        enters_semantic_block = (
            lowered in _NONRENDERED_CONTAINERS
            or lowered in self._hidden_tags
            or attributes.get("id", "").casefold() in self._hidden_ids
            or bool(class_tokens & self._hidden_classes)
            or (lowered == "dialog" and "open" not in attributes)
            or "hidden" in attributes
            or "inert" in attributes
            or inline_style_hidden
        )
        enters_head = lowered == "head"
        active = self._inactive_depth == 0 and not enters_inactive
        semantic_active = (
            active
            and self._semantic_blocked_depth == 0
            and self._head_depth == 0
            and not enters_semantic_block
            and not enters_head
        )
        data_semantic_active = (
            active
            and self._semantic_blocked_depth == 0
            and "hidden" not in attributes
            and "inert" not in attributes
            and not inline_style_hidden
        )
        enters_blocked = lowered in {
            "noembed",
            "plaintext",
            "script",
            "style",
            "template",
            "title",
            "xmp",
        }
        is_void = lowered in _VOID_HTML_ELEMENTS
        css_tree_active = (
            active
            and self._semantic_blocked_depth == 0
            and self._head_depth == 0
            and not enters_head
            and lowered not in _NONRENDERED_CONTAINERS
            and not enters_inactive
            and not (lowered == "dialog" and "open" not in attributes)
            and "hidden" not in attributes
            and "inert" not in attributes
            and not inline_style_hidden
        )
        css_index: int | None = None
        if active:
            self.elements.append((lowered, attributes, self.getpos()[0]))
            if css_tree_active:
                css_index = len(self.css_rendered_elements)
                self.css_rendered_elements.append(
                    _CssRenderedElement(
                        tag=lowered,
                        attributes=attributes,
                        ancestors=tuple((open_tag[0], open_tag[8]) for open_tag in self._open_tags),
                        ancestor_indices=tuple(
                            open_tag[9] for open_tag in self._open_tags if open_tag[9] is not None
                        ),
                    )
                )
        if semantic_active:
            self.semantic_elements.append((lowered, attributes, self.getpos()[0]))
        if enters_blocked:
            self._blocked_depth += 1
        if enters_inactive and not is_void:
            self._inactive_depth += 1
        if enters_semantic_block and not is_void:
            self._semantic_blocked_depth += 1
        if enters_head and not is_void:
            self._head_depth += 1
        starts_jsonld = bool(
            lowered == "script"
            and attributes.get("type", "").casefold().split(";", 1)[0].strip() == "application/ld+json"
            and data_semantic_active
        )
        if starts_jsonld:
            if self._jsonld_line is not None:
                raise CandidateStaticQABoundaryError("candidate-html-jsonld-nesting-invalid")
            self._jsonld_line = self.getpos()[0]
            self._jsonld_chunks = []
        starts_title = lowered == "title" and data_semantic_active
        if starts_title:
            if self._title_line is not None:
                raise CandidateStaticQABoundaryError("candidate-html-title-nesting-invalid")
            self._title_line = self.getpos()[0]
            self._title_chunks = []
        starts_style = lowered == "style" and active
        if starts_style:
            if self._style_line is not None:
                raise CandidateStaticQABoundaryError("candidate-html-style-nesting-invalid")
            self._style_line = self.getpos()[0]
            self._style_chunks = []
        if not is_void:
            self._open_tags.append(
                (
                    lowered,
                    enters_inactive,
                    enters_blocked,
                    enters_semantic_block,
                    enters_head,
                    starts_jsonld,
                    starts_title,
                    starts_style,
                    attributes,
                    css_index,
                )
            )

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.casefold()
        names = [key.casefold() for key, _ in attrs]
        if len(names) != len(set(names)):
            raise CandidateStaticQABoundaryError("candidate-html-duplicate-attribute")
        if lowered not in _VOID_HTML_ELEMENTS:
            self.nonvoid_self_closing.append((lowered, self.getpos()[0]))
            self.handle_starttag(tag, attrs)
            return
        attributes = {key.casefold(): (value if value is not None else "") for key, value in attrs}
        inline_style_hidden = _css_body_has_hidden_declaration(attributes.get("style", ""))
        active = self._inactive_depth == 0
        semantic_active = (
            active
            and self._semantic_blocked_depth == 0
            and self._head_depth == 0
            and "hidden" not in attributes
            and "inert" not in attributes
            and not inline_style_hidden
        )
        css_tree_active = (
            active
            and self._semantic_blocked_depth == 0
            and self._head_depth == 0
            and lowered not in _NONRENDERED_CONTAINERS
            and not (lowered == "dialog" and "open" not in attributes)
            and "hidden" not in attributes
            and "inert" not in attributes
            and not inline_style_hidden
        )
        if active:
            self.elements.append((lowered, attributes, self.getpos()[0]))
            if css_tree_active:
                self.css_rendered_elements.append(
                    _CssRenderedElement(
                        tag=lowered,
                        attributes=attributes,
                        ancestors=tuple((open_tag[0], open_tag[8]) for open_tag in self._open_tags),
                        ancestor_indices=tuple(
                            open_tag[9] for open_tag in self._open_tags if open_tag[9] is not None
                        ),
                    )
                )
        if semantic_active:
            self.semantic_elements.append((lowered, attributes, self.getpos()[0]))
        if (
            lowered == "script"
            and attributes.get("type", "").casefold().split(";", 1)[0].strip() == "application/ld+json"
            and semantic_active
        ):
            self.jsonld_blocks.append(("", self.getpos()[0]))
        if lowered == "title" and active:
            self.title_blocks.append(("", self.getpos()[0]))
        if lowered == "style" and active:
            self.style_blocks.append(("", self.getpos()[0]))

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.casefold()
        matching = next(
            (
                index
                for index in range(len(self._open_tags) - 1, -1, -1)
                if self._open_tags[index][0] == lowered
            ),
            None,
        )
        if matching is None:
            return
        closing = self._open_tags[matching:]
        del self._open_tags[matching:]
        for (
            _,
            entered_inactive,
            entered_blocked,
            entered_semantic_block,
            entered_head,
            started_jsonld,
            started_title,
            started_style,
            _attributes,
            _css_index,
        ) in reversed(closing):
            if started_jsonld and self._jsonld_line is not None:
                self.jsonld_blocks.append(("".join(self._jsonld_chunks), self._jsonld_line))
                self._jsonld_line = None
                self._jsonld_chunks = []
            if started_title and self._title_line is not None:
                self.title_blocks.append(("".join(self._title_chunks), self._title_line))
                self._title_line = None
                self._title_chunks = []
            if started_style and self._style_line is not None:
                self.style_blocks.append(("".join(self._style_chunks), self._style_line))
                self._style_line = None
                self._style_chunks = []
            if entered_inactive and self._inactive_depth:
                self._inactive_depth -= 1
            if entered_blocked and self._blocked_depth:
                self._blocked_depth -= 1
            if entered_semantic_block and self._semantic_blocked_depth:
                self._semantic_blocked_depth -= 1
            if entered_head and self._head_depth:
                self._head_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._jsonld_line is not None and self._inactive_depth == 0:
            self._jsonld_chunks.append(data)
        if self._title_line is not None and self._inactive_depth == 0:
            self._title_chunks.append(data)
        if self._style_line is not None and self._inactive_depth == 0:
            self._style_chunks.append(data)
        if (
            not self._blocked_depth
            and not self._inactive_depth
            and not self._semantic_blocked_depth
            and not self._head_depth
        ):
            self.visible_chunks.append(data)

    @property
    def visible_text(self) -> str:
        return _SPACE.sub(" ", unescape(" ".join(self.visible_chunks))).strip()


def _parse_html(
    text: str,
    *,
    hidden_classes: set[str] | None = None,
    hidden_ids: set[str] | None = None,
    hidden_tags: set[str] | None = None,
) -> _HtmlInventory:
    parser = _HtmlInventory(
        hidden_classes=hidden_classes or set(),
        hidden_ids=hidden_ids or set(),
        hidden_tags=hidden_tags or set(),
    )
    try:
        parser.feed(text)
        parser.close()
        if parser._jsonld_line is not None:
            raise CandidateStaticQABoundaryError("candidate-html-jsonld-unclosed")
        if parser._title_line is not None:
            raise CandidateStaticQABoundaryError("candidate-html-title-unclosed")
        if parser._style_line is not None:
            raise CandidateStaticQABoundaryError("candidate-html-style-unclosed")
    except CandidateStaticQABoundaryError:
        raise
    except (ValueError, AssertionError) as exc:
        raise CandidateStaticQABoundaryError("candidate-html-parser-boundary") from exc
    return parser


class _Audit:
    def __init__(
        self,
        *,
        mode: str,
        root: Path,
        config: Mapping[str, Any],
        snapshot: Mapping[str, Any],
    ) -> None:
        self.mode = mode
        self.root = root
        self.config = config
        self.snapshot = snapshot
        self.rows = [dict(row) for row in snapshot["files"] if isinstance(row, Mapping)]
        self.paths = {str(row["path"]) for row in self.rows}
        self.casefold_paths = {path.casefold(): path for path in self.paths}
        self.text: dict[str, str] = {}
        self.json: dict[str, object] = {}
        self.html: dict[str, _HtmlInventory] = {}
        self.findings: list[dict[str, object]] = []
        self.finding_checks: dict[str, set[str]] = {}

    def add(
        self,
        check_id: str,
        code: str,
        *,
        path: str = ".",
        line: int = 0,
        token: object = "",
        severity: str = "blocker",
    ) -> None:
        relative = path if path in self.paths or path == "." else "."
        evidence = _json_sha256(
            {
                "code": code,
                "line": max(0, int(line)),
                "path": relative,
                "token": token,
            }
        )
        finding = {
            "code": code,
            "severity": severity,
            "path": relative,
            "line": max(0, int(line)),
            "evidence_hash": evidence,
        }
        self.findings.append(finding)
        self.finding_checks.setdefault(check_id, set()).add(code)

    def load_text_and_json(self) -> None:
        packaging = _mapping(self.config.get("packaging"), code="trusted-config-shape-invalid")
        allowed_names = {
            value.casefold()
            for value in _string_list(
                packaging.get("allowed_file_names"),
                code="trusted-config-shape-invalid",
            )
        }
        for row in self.rows:
            relative = str(row["path"])
            suffix = Path(relative).suffix.casefold()
            if suffix not in TEXT_EXTENSIONS and Path(relative).name.casefold() not in allowed_names:
                continue
            path = self.root / relative
            text = _decode_text(path)
            self.text[relative] = text
            if suffix in JSON_EXTENSIONS:
                value = _strict_json_bytes(
                    text.encode("utf-8"),
                    code="candidate-public-json-invalid",
                )
                self.json[relative] = value
        preliminary_html: dict[str, _HtmlInventory] = {}
        for relative, text in sorted(self.text.items()):
            if Path(relative).suffix.casefold() not in {".html", ".htm"}:
                continue
            preliminary_html[relative] = _parse_html(
                text,
                hidden_classes=set(),
                hidden_ids=set(),
                hidden_tags=set(),
            )
        external_styles = [
            text for relative, text in sorted(self.text.items()) if Path(relative).suffix.casefold() == ".css"
        ]
        for relative, preliminary in sorted(preliminary_html.items()):
            try:
                hidden_classes, hidden_ids, hidden_tags = _css_hidden_selectors(
                    [
                        *external_styles,
                        *(style for style, _line in preliminary.style_blocks),
                    ],
                    critical_elements=preliminary.css_rendered_elements,
                )
            except CandidateStaticQABoundaryError as exc:
                if exc.code not in {
                    "candidate-css-complexity-limit",
                    "candidate-css-structure-invalid",
                }:
                    raise
                self.add(
                    "design.html-structure",
                    exc.code,
                    path=relative,
                    token={"scope": "candidate-css"},
                )
                hidden_classes, hidden_ids, hidden_tags = set(), set(), set()
            self.html[relative] = _parse_html(
                self.text[relative],
                hidden_classes=hidden_classes,
                hidden_ids=hidden_ids,
                hidden_tags=hidden_tags,
            )

    def required_files(self) -> None:
        site = _mapping(self.config.get("site"), code="trusted-config-shape-invalid")
        packaging = _mapping(self.config.get("packaging"), code="trusted-config-shape-invalid")
        required = _string_list(site.get("critical_routes"), code="trusted-config-shape-invalid")
        required.extend(
            path
            for path in _string_list(
                packaging.get("required_release_paths"),
                code="trusted-config-shape-invalid",
            )
            if path not in required
        )
        for relative in sorted(required):
            safe = _safe_relative(relative, code="trusted-config-path-invalid")
            if safe not in self.paths:
                self.add("website.required-files", "required-file-missing", path=".", token=safe)

    def claim_inputs(self, check_id: str) -> None:
        ethos = _mapping(self.config.get("ethos"), code="trusted-config-shape-invalid")
        raw_inputs = ethos.get("claim_inputs")
        if not isinstance(raw_inputs, list):
            raise CandidateStaticQABoundaryError("trusted-config-shape-invalid")
        seen: set[str] = set()
        for raw in raw_inputs:
            item = _mapping(raw, code="trusted-config-shape-invalid")
            configured = item.get("path")
            if not isinstance(configured, str) or not configured.startswith("website/"):
                raise CandidateStaticQABoundaryError("trusted-config-claim-path-invalid")
            relative = _safe_relative(
                configured.removeprefix("website/"),
                code="trusted-config-claim-path-invalid",
            )
            if relative in seen:
                raise CandidateStaticQABoundaryError("trusted-config-claim-path-duplicate")
            seen.add(relative)
            required = item.get("required")
            if required not in (True, False, None):
                raise CandidateStaticQABoundaryError("trusted-config-shape-invalid")
            if relative not in self.paths:
                if required is not False:
                    self.add(check_id, "claim-input-missing", token=relative)
                continue
            value = self.json.get(relative)
            if not isinstance(value, Mapping):
                self.add(check_id, "claim-input-not-object", path=relative)
                continue
            expected_schema = item.get("schema")
            if expected_schema is not None and value.get("schema") != expected_schema:
                self.add(check_id, "claim-input-schema-mismatch", path=relative, token=expected_schema)

    def budgets(self) -> None:
        budgets = _mapping(self.config.get("budgets"), code="trusted-config-shape-invalid")
        total_limit = _positive_int(budgets.get("site_total_bytes"))
        count_limit = _positive_int(budgets.get("site_file_count"))
        direct_limit = _positive_int(budgets.get("critical_page_direct_bytes"))
        if int(self.snapshot["total_bytes"]) > total_limit:
            self.add(
                "website.budgets",
                "site-total-byte-budget-exceeded",
                token={"actual": self.snapshot["total_bytes"], "limit": total_limit},
            )
        if int(self.snapshot["file_count"]) > count_limit:
            self.add(
                "website.budgets",
                "site-file-count-budget-exceeded",
                token={"actual": self.snapshot["file_count"], "limit": count_limit},
            )
        per_file = _mapping(budgets.get("per_file_bytes"), code="trusted-config-shape-invalid")
        for row in self.rows:
            relative = str(row["path"])
            suffix = Path(relative).suffix.casefold()
            raw_limit = per_file.get(suffix)
            if raw_limit is None:
                continue
            limit = _positive_int(raw_limit)
            if int(row["bytes"]) > limit:
                self.add(
                    "website.budgets",
                    "per-file-byte-budget-exceeded",
                    path=relative,
                    token={"actual": row["bytes"], "limit": limit},
                )
        site = _mapping(self.config.get("site"), code="trusted-config-shape-invalid")
        for route in _string_list(site.get("critical_routes"), code="trusted-config-shape-invalid"):
            if route not in self.html:
                continue
            direct_paths = {route}
            for reference, _, kind in self._html_references(route):
                if kind not in {"active-fetch", "asset", "script", "stylesheet"}:
                    continue
                target, _, issue = self._resolve_reference(route, reference)
                if issue is None and target in self.paths:
                    direct_paths.add(target)
            direct_bytes = sum(int(row["bytes"]) for row in self.rows if str(row["path"]) in direct_paths)
            if direct_bytes > direct_limit:
                self.add(
                    "website.budgets",
                    "critical-page-direct-byte-budget-exceeded",
                    path=route,
                    token={"actual": direct_bytes, "limit": direct_limit},
                )

    def secrets(self) -> None:
        packaging = _mapping(self.config.get("packaging"), code="trusted-config-shape-invalid")
        blocked_names = {
            value.casefold()
            for value in _string_list(
                packaging.get("blocked_file_names"),
                code="trusted-config-shape-invalid",
            )
        }
        blocked_extensions = {
            value.casefold()
            for value in _string_list(
                packaging.get("blocked_extensions"),
                code="trusted-config-shape-invalid",
            )
        }
        allowed_names = {
            value.casefold()
            for value in _string_list(
                packaging.get("allowed_file_names"),
                code="trusted-config-shape-invalid",
            )
        }
        allowed_extensions = {
            value.casefold()
            for value in _string_list(
                packaging.get("allowed_extensions"),
                code="trusted-config-shape-invalid",
            )
        }
        patterns: list[re.Pattern[str]] = []
        for raw in _string_list(packaging.get("secret_patterns"), code="trusted-config-shape-invalid"):
            try:
                patterns.append(re.compile(raw, re.IGNORECASE))
            except re.error as exc:
                raise CandidateStaticQABoundaryError("trusted-config-secret-pattern-invalid") from exc
        release_members = {
            _safe_relative(value, code="trusted-config-path-invalid")
            for value in _string_list(
                packaging.get("required_release_paths"),
                code="trusted-config-shape-invalid",
            )
        }
        for page in sorted(self.html):
            for reference, _, kind in self._html_references(page):
                if kind == "canonical":
                    continue
                issue = self._reference_policy_issue(reference, kind)
                target: str | None = None
                if issue is None:
                    target, _, issue = self._resolve_reference(page, reference)
                if issue is None and target is not None:
                    release_members.add(target)
        for relative, css in sorted(self.text.items()):
            if Path(relative).suffix.casefold() != ".css":
                continue
            for reference, _, kind in self._css_references(css):
                issue = self._reference_policy_issue(reference, kind)
                target = None
                if issue is None:
                    target, _, issue = self._resolve_reference(relative, reference)
                if issue is None and target is not None:
                    release_members.add(target)
        for reference, kind, _ in self._webmanifest_references():
            issue = self._reference_policy_issue(reference, kind)
            target = None
            if issue is None:
                target, _, issue = self._resolve_reference("site.webmanifest", reference)
            if issue is not None:
                self.add(
                    "website.required-files",
                    "webmanifest-release-reference-rejected",
                    path="site.webmanifest",
                )
                continue
            exact = self.casefold_paths.get(str(target).casefold()) if target is not None else None
            if exact is None:
                self.add(
                    "website.required-files",
                    "webmanifest-release-target-missing",
                    path="site.webmanifest",
                )
                continue
            if exact != target:
                self.add(
                    "website.required-files",
                    "webmanifest-release-target-case-mismatch",
                    path="site.webmanifest",
                )
                continue
            release_members.add(exact)
            if kind == "manifest-executable":
                self.add(
                    "website.secret-patterns",
                    "webmanifest-executable-target-rejected",
                    path="site.webmanifest",
                )
        for relative in sorted(self.paths):
            path = Path(relative)
            name = path.name.casefold()
            suffix = path.suffix.casefold()
            folded_parts = [part.casefold() for part in path.parts]
            if (
                name in blocked_names
                or name == ".env"
                or name.startswith(".env.")
                or suffix in blocked_extensions
                or any(part == ".env" or part.startswith(".env.") for part in folded_parts)
            ):
                self.add("website.secret-patterns", "blocked-public-file", path=relative)
            if relative in release_members and name not in allowed_names and suffix not in allowed_extensions:
                self.add(
                    "website.secret-patterns",
                    "unapproved-public-file-type",
                    path=relative,
                )
            text = self.text.get(relative)
            if text is None:
                text = (self.root / relative).read_bytes().decode("latin-1")
            for ordinal, pattern in enumerate(patterns):
                secret_match = pattern.search(text)
                if secret_match:
                    self.add(
                        "website.secret-patterns",
                        "public-secret-pattern",
                        path=relative,
                        line=_line_for_offset(text, secret_match.start()),
                        token={"pattern": ordinal},
                    )

    def html_structure(self) -> None:
        for relative, parser in sorted(self.html.items()):
            elements = parser.semantic_elements
            for tag, line in parser.parser_differential_elements:
                self.add(
                    "design.html-structure",
                    "parser-differential-html-element-rejected",
                    path=relative,
                    line=line,
                    token=tag,
                )
            for tag, line in parser.nonvoid_self_closing:
                self.add(
                    "design.html-structure",
                    "nonvoid-self-closing-html-tag",
                    path=relative,
                    line=line,
                    token=tag,
                )
            ids = [attrs["id"] for _, attrs, _ in elements if attrs.get("id")]
            duplicates = sorted({value for value in ids if ids.count(value) > 1})
            for value in duplicates:
                self.add(
                    "design.html-structure",
                    "duplicate-html-id",
                    path=relative,
                    token=_bytes_sha256(value.encode("utf-8")),
                )
            counts = {
                "h1": sum(tag == "h1" for tag, _, _ in elements),
                "title": len(parser.title_blocks),
                "canonical": sum(
                    tag == "link" and "canonical" in attrs.get("rel", "").casefold().split()
                    for tag, attrs, _ in parser.elements
                ),
            }
            for name, count in counts.items():
                if count != 1:
                    self.add(
                        "design.html-structure",
                        f"{name}-count-invalid",
                        path=relative,
                        token=count,
                    )

    def accessibility(self) -> None:
        for relative, parser in sorted(self.html.items()):
            elements = parser.semantic_elements
            if not any(tag == "main" for tag, _, _ in elements):
                self.add("design.accessibility-basics", "main-landmark-missing", path=relative)
            for tag, attrs, line in elements:
                if tag == "img" and "alt" not in attrs:
                    self.add(
                        "design.accessibility-basics",
                        "image-alt-missing",
                        path=relative,
                        line=line,
                    )
                if tag == "button" and not attrs.get("type"):
                    self.add(
                        "design.accessibility-basics",
                        "button-type-missing",
                        path=relative,
                        line=line,
                    )
                if tag == "a" and attrs.get("target", "").casefold() == "_blank":
                    rel_tokens = attrs.get("rel", "").casefold().split()
                    if "noopener" not in rel_tokens:
                        self.add(
                            "design.accessibility-basics",
                            "blank-target-noopener-missing",
                            path=relative,
                            line=line,
                        )
                if tag == "iframe" and not attrs.get("title"):
                    self.add(
                        "design.accessibility-basics",
                        "iframe-title-missing",
                        path=relative,
                        line=line,
                    )
                if tag in {"audio", "video"} and "autoplay" in attrs:
                    self.add(
                        "design.accessibility-basics",
                        "autoplay-media",
                        path=relative,
                        line=line,
                    )
                if tag == "marquee":
                    self.add(
                        "design.accessibility-basics",
                        "marquee-element",
                        path=relative,
                        line=line,
                    )

    def executable_javascript(self) -> None:
        reviewed = set(REVIEWED_EXECUTABLE_JS_PATHS)
        tree_scripts = {relative for relative in self.paths if Path(relative).suffix.casefold() == ".js"}
        for relative in sorted(tree_scripts - reviewed):
            self.add(
                "design.executable-javascript",
                "unreviewed-javascript-file",
                path=relative,
            )
        for relative in sorted(reviewed - tree_scripts):
            self.add(
                "design.executable-javascript",
                "reviewed-javascript-file-missing",
                token=relative,
            )
        for page, parser in sorted(self.html.items()):
            for tag, attrs, line in parser.elements:
                if tag == "base":
                    self.add(
                        "design.executable-javascript",
                        "html-base-element-rejected",
                        path=page,
                        line=line,
                    )
                event_attributes = sorted(key for key in attrs if re.fullmatch(r"on[a-z][a-z0-9_-]*", key))
                if event_attributes:
                    self.add(
                        "design.executable-javascript",
                        "inline-event-handler-rejected",
                        path=page,
                        line=line,
                        token=event_attributes,
                    )
                if "srcdoc" in attrs:
                    self.add(
                        "design.executable-javascript",
                        "inline-srcdoc-rejected",
                        path=page,
                        line=line,
                    )
                if tag != "script":
                    continue
                script_type = attrs.get("type", "").casefold().split(";", 1)[0].strip()
                if script_type == "application/ld+json":
                    if attrs.get("src"):
                        self.add(
                            "design.executable-javascript",
                            "external-jsonld-script-rejected",
                            path=page,
                            line=line,
                        )
                    continue
                source = attrs.get("src", "").strip()
                if not source:
                    self.add(
                        "design.executable-javascript",
                        "inline-executable-script-rejected",
                        path=page,
                        line=line,
                    )
                    continue
                try:
                    parsed = urlsplit(unescape(source))
                except ValueError:
                    parsed = None
                if parsed is None:
                    self.add(
                        "design.executable-javascript",
                        "executable-script-source-invalid",
                        path=page,
                        line=line,
                    )
                    continue
                if parsed.scheme or parsed.netloc:
                    self.add(
                        "design.executable-javascript",
                        "remote-executable-script-rejected",
                        path=page,
                        line=line,
                    )
                    continue
                target, _, issue = self._resolve_reference(page, source)
                if issue is not None or target not in reviewed:
                    self.add(
                        "design.executable-javascript",
                        "unreviewed-executable-script-source",
                        path=page,
                        line=line,
                        token=(issue if issue is not None else _bytes_sha256(str(target).encode("utf-8"))),
                    )

    def _html_references(self, relative: str) -> list[tuple[str, int, str]]:
        references: list[tuple[str, int, str]] = []
        for tag, attrs, line in self.html[relative].elements:
            if tag in {"a", "area"} and attrs.get("href"):
                references.append((attrs["href"], line, "link"))
            if tag in {"a", "area"} and attrs.get("ping"):
                for value in attrs["ping"].split():
                    references.append((value, line, "beacon"))
            if tag == "script" and attrs.get("src"):
                references.append((attrs["src"], line, "script"))
            if tag in {"audio", "img", "input", "source", "track", "video"} and attrs.get("src"):
                references.append((attrs["src"], line, "asset"))
            if tag in {"iframe", "embed"} and attrs.get("src"):
                references.append((attrs["src"], line, "active-content"))
            if tag == "object" and attrs.get("data"):
                references.append((attrs["data"], line, "active-content"))
            if tag == "object":
                for name in ("archive", "codebase"):
                    if attrs.get(name):
                        for value in attrs[name].split():
                            references.append((value, line, "active-content"))
            if tag == "video" and attrs.get("poster"):
                references.append((attrs["poster"], line, "asset"))
            if tag in {"body", "table", "td", "th"} and attrs.get("background"):
                references.append((attrs["background"], line, "asset"))
            if tag == "form" and "action" in attrs:
                references.append((attrs["action"], line, "form-action"))
            if tag in {"button", "input"} and "formaction" in attrs:
                references.append((attrs["formaction"], line, "form-action"))
            if tag == "link" and attrs.get("href"):
                relations = set(attrs.get("rel", "").casefold().split())
                if "canonical" in relations:
                    references.append((attrs["href"], line, "canonical"))
                elif "stylesheet" in relations:
                    references.append((attrs["href"], line, "stylesheet"))
                elif relations & {
                    "dns-prefetch",
                    "modulepreload",
                    "preconnect",
                    "prefetch",
                    "preload",
                    "prerender",
                }:
                    references.append((attrs["href"], line, "active-fetch"))
                elif relations & {
                    "apple-touch-icon",
                    "icon",
                    "image_src",
                    "manifest",
                    "mask-icon",
                }:
                    references.append((attrs["href"], line, "asset"))
            if tag in {"feimage", "image", "use"}:
                for name in ("href", "xlink:href"):
                    if attrs.get(name):
                        references.append((attrs[name], line, "asset"))
            if tag == "meta":
                identity = attrs.get("property", attrs.get("name", "")).casefold()
                if identity in {
                    "msapplication-tileimage",
                    "og:image",
                    "og:image:secure_url",
                    "og:image:url",
                    "twitter:image",
                    "twitter:image:src",
                } and attrs.get("content"):
                    references.append((attrs["content"], line, "asset"))
                if attrs.get("http-equiv", "").casefold() == "refresh":
                    refresh = _meta_refresh_reference(attrs.get("content", ""))
                    if refresh is not None:
                        references.append((refresh, line, "automatic-navigation"))
            if tag in {"img", "source"} and attrs.get("srcset"):
                for candidate in attrs["srcset"].split(","):
                    value = candidate.strip().split(maxsplit=1)[0]
                    if value:
                        references.append((value, line, "asset"))
            if tag == "link" and attrs.get("imagesrcset"):
                for candidate in attrs["imagesrcset"].split(","):
                    value = candidate.strip().split(maxsplit=1)[0]
                    if value:
                        references.append((value, line, "asset"))
            if attrs.get("style"):
                references.extend(
                    (value, line, kind) for value, _, kind in self._css_references(attrs["style"])
                )
        for body, line in self.html[relative].style_blocks:
            references.extend(
                (
                    value,
                    line + _line_for_offset(body, offset) - 1,
                    kind,
                )
                for value, offset, kind in self._css_references(body)
            )
        return references

    def _reference_policy_issue(self, reference: str, kind: str) -> str | None:
        raw = unescape(reference).strip()
        if not raw:
            return (
                "active-url-empty"
                if kind
                in {
                    "active-content",
                    "automatic-navigation",
                    "beacon",
                    "form-action",
                    "manifest-asset",
                    "manifest-executable",
                    "manifest-navigation",
                    "manifest-scope",
                    "stylesheet",
                }
                else None
            )
        try:
            parsed = urlsplit(raw)
        except ValueError:
            return "invalid-reference-url"
        scheme = parsed.scheme.casefold()
        if scheme in {"blob", "data", "file", "javascript", "vbscript"}:
            return "active-content-url-rejected"
        if kind == "canonical":
            return None
        if kind == "link":
            if scheme in {"mailto", "tel"}:
                return None
            if scheme and scheme not in {"http", "https"}:
                return "unsupported-reference-scheme"
            return None
        if scheme in {"mailto", "tel"}:
            return "active-content-url-rejected"
        if scheme and scheme not in {"http", "https"}:
            return "unsupported-reference-scheme"
        site = _mapping(self.config.get("site"), code="trusted-config-shape-invalid")
        base_url = _required_string(site.get("base_url"), code="trusted-config-shape-invalid")
        base_host = urlsplit(base_url).netloc.casefold()
        if kind in {
            "active-content",
            "active-fetch",
            "automatic-navigation",
            "beacon",
            "form-action",
            "manifest-asset",
            "manifest-executable",
            "manifest-navigation",
            "manifest-scope",
            "stylesheet",
        }:
            if parsed.scheme or parsed.netloc:
                return "active-content-url-rejected"
        elif kind == "asset" and (parsed.scheme or parsed.netloc) and parsed.netloc.casefold() != base_host:
            return "external-browser-resource-rejected"
        return None

    def _css_references(self, text: str) -> list[tuple[str, int, str]]:
        structural = _decode_css_identifier_escapes(_strip_css_comments_compact(text))
        references: list[tuple[str, int, str]] = []
        imports = list(_CSS_IMPORT.finditer(structural))
        for match in _CSS_URL.finditer(structural):
            if _offset_is_outside_string(structural, match.start()):
                kind = (
                    "stylesheet"
                    if any(item.start() <= match.start() < item.end() for item in imports)
                    else "asset"
                )
                references.append(
                    (
                        _decode_css_value_escapes(match.group("url")),
                        match.start(),
                        kind,
                    )
                )
        for match in imports:
            if match.group("string") is not None and _css_at_rule_offset_is_structural(
                structural, match.start()
            ):
                references.append(
                    (
                        _decode_css_value_escapes(match.group("string")),
                        match.start(),
                        "stylesheet",
                    )
                )
        for match in _CSS_IMAGE_SET_START.finditer(structural):
            if not _offset_is_outside_string(structural, match.start()):
                continue
            closing = _matching_closing_parenthesis(structural, match.end() - 1)
            if closing is None:
                continue
            references.extend(
                (
                    _decode_css_value_escapes(value),
                    offset,
                    "asset",
                )
                for value, offset in _css_top_level_quoted_strings(
                    structural,
                    match.end(),
                    closing,
                )
            )
        return sorted(set(references), key=lambda item: (item[1], item[0], item[2]))

    def _webmanifest_references(self) -> list[tuple[str, str, str]]:
        value = self.json.get("site.webmanifest")
        if not isinstance(value, Mapping):
            return []
        references: list[tuple[str, str, str]] = []

        def collect_assets(raw: object, field: str) -> None:
            if not isinstance(raw, list):
                return
            for item in raw:
                if isinstance(item, Mapping) and isinstance(item.get("src"), str):
                    references.append((str(item["src"]), "manifest-asset", field))

        def collect_field(
            container: Mapping[str, object],
            key: str,
            kind: str,
            field: str,
        ) -> None:
            raw = container.get(key)
            if isinstance(raw, str):
                references.append((raw, kind, field))

        collect_field(value, "start_url", "manifest-navigation", "start_url")
        collect_field(value, "scope", "manifest-scope", "scope")
        collect_assets(value.get("icons"), "icons[].src")
        collect_assets(value.get("screenshots"), "screenshots[].src")
        shortcuts = value.get("shortcuts")
        if isinstance(shortcuts, list):
            for shortcut in shortcuts:
                if isinstance(shortcut, Mapping):
                    collect_field(shortcut, "url", "manifest-navigation", "shortcuts[].url")
                    collect_assets(shortcut.get("icons"), "shortcuts[].icons[].src")
        share_target = value.get("share_target")
        if isinstance(share_target, Mapping):
            collect_field(share_target, "action", "manifest-navigation", "share_target.action")
        note_taking = value.get("note_taking")
        if isinstance(note_taking, Mapping):
            collect_field(
                note_taking,
                "new_note_url",
                "manifest-navigation",
                "note_taking.new_note_url",
            )
        tab_strip = value.get("tab_strip")
        if isinstance(tab_strip, Mapping):
            new_tab_button = tab_strip.get("new_tab_button")
            if isinstance(new_tab_button, Mapping):
                collect_field(
                    new_tab_button,
                    "url",
                    "manifest-navigation",
                    "tab_strip.new_tab_button.url",
                )
        protocol_handlers = value.get("protocol_handlers")
        if isinstance(protocol_handlers, list):
            for handler in protocol_handlers:
                if isinstance(handler, Mapping):
                    collect_field(
                        handler,
                        "url",
                        "manifest-navigation",
                        "protocol_handlers[].url",
                    )
        file_handlers = value.get("file_handlers")
        if isinstance(file_handlers, list):
            for handler in file_handlers:
                if isinstance(handler, Mapping):
                    collect_field(
                        handler,
                        "action",
                        "manifest-navigation",
                        "file_handlers[].action",
                    )
        serviceworker = value.get("serviceworker")
        if isinstance(serviceworker, Mapping):
            collect_field(
                serviceworker,
                "src",
                "manifest-executable",
                "serviceworker.src",
            )
        return references

    def _resolve_reference(self, page: str, reference: str) -> tuple[str | None, str, str | None]:
        raw = unescape(reference).strip()
        if not raw:
            return None, "", None
        lowered = raw.casefold()
        if lowered.startswith(("mailto:", "tel:")):
            return None, "", None
        try:
            parsed = urlsplit(raw)
        except ValueError:
            return None, "", "invalid-reference-url"
        if parsed.scheme.casefold() in {"blob", "data", "file", "javascript", "vbscript"}:
            return None, "", "active-content-url-rejected"
        site = _mapping(self.config.get("site"), code="trusted-config-shape-invalid")
        base_url = _required_string(site.get("base_url"), code="trusted-config-shape-invalid")
        base = urlsplit(base_url)
        if parsed.scheme or parsed.netloc:
            if parsed.scheme.casefold() not in {"http", "https"}:
                return None, "", "unsupported-reference-scheme"
            if parsed.netloc.casefold() != base.netloc.casefold():
                return None, "", None
        try:
            decoded = unquote_to_bytes(parsed.path).decode("utf-8", errors="strict")
            fragment = unquote_to_bytes(parsed.fragment).decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            return None, "", "invalid-reference-encoding"
        decoded = decoded.replace("\\", "/")
        if decoded.startswith("/"):
            parts = decoded.lstrip("/").split("/")
        elif decoded:
            parts = (Path(page).parent / Path(decoded)).as_posix().split("/")
        else:
            parts = page.split("/")
        collapsed: list[str] = []
        for part in parts:
            if part in {"", "."}:
                continue
            if part == "..":
                if not collapsed:
                    return None, fragment, "reference-path-escape"
                collapsed.pop()
            else:
                collapsed.append(part)
        target = "/".join(collapsed)
        if decoded.endswith("/") or target in {
            path.rsplit("/index.html", 1)[0] for path in self.paths if path.endswith("/index.html")
        }:
            target = f"{target.rstrip('/')}/index.html" if target else "index.html"
        return target, fragment, None

    def local_references(self) -> None:
        for page in sorted(self.html):
            for reference, line, kind in self._html_references(page):
                issue = self._reference_policy_issue(reference, kind)
                target: str | None = None
                fragment = ""
                if issue is None:
                    target, fragment, issue = self._resolve_reference(page, reference)
                if issue:
                    self.add(
                        "design.local-references",
                        issue,
                        path=page,
                        line=line,
                        token=kind,
                    )
                    continue
                if target is None or kind == "canonical":
                    continue
                exact = self.casefold_paths.get(target.casefold())
                if exact is None:
                    self.add(
                        "design.local-references",
                        "local-reference-target-missing",
                        path=page,
                        line=line,
                        token={"kind": kind, "target_hash": _bytes_sha256(target.encode("utf-8"))},
                    )
                    continue
                if exact != target:
                    self.add(
                        "design.local-references",
                        "local-reference-case-mismatch",
                        path=page,
                        line=line,
                        token={"kind": kind, "target_hash": _bytes_sha256(target.encode("utf-8"))},
                    )
                    continue
                if kind == "link" and fragment and exact in self.html:
                    ids = {
                        attrs["id"] for _, attrs, _ in self.html[exact].semantic_elements if attrs.get("id")
                    }
                    if fragment not in ids:
                        self.add(
                            "design.local-references",
                            "fragment-target-missing",
                            path=page,
                            line=line,
                            token=_bytes_sha256(fragment.encode("utf-8")),
                        )
        for relative, text in sorted(self.text.items()):
            if Path(relative).suffix.casefold() != ".css":
                continue
            for reference, offset, kind in self._css_references(text):
                issue = self._reference_policy_issue(reference, kind)
                target = None
                if issue is None:
                    target, _, issue = self._resolve_reference(relative, reference)
                if issue:
                    self.add(
                        "design.local-references",
                        issue,
                        path=relative,
                        line=_line_for_offset(text, offset),
                        token="css",
                    )
                elif target is not None:
                    exact = self.casefold_paths.get(target.casefold())
                    code = (
                        "local-reference-target-missing"
                        if exact is None
                        else "local-reference-case-mismatch"
                        if exact != target
                        else ""
                    )
                    if code:
                        self.add(
                            "design.local-references",
                            code,
                            path=relative,
                            line=_line_for_offset(text, offset),
                            token={"kind": "css", "target_hash": _bytes_sha256(target.encode("utf-8"))},
                        )

    def active_resources(self) -> None:
        queued: set[str] = set()
        emitted: set[tuple[str, str]] = set()

        def emit(code: str, relative: str) -> None:
            key = (relative, code)
            if key not in emitted:
                emitted.add(key)
                self.add("design.active-resources", code, path=relative)

        def consider_reference(
            source: str,
            reference: str,
            *,
            policy_kind: str,
            reject_executable: bool,
        ) -> None:
            issue = self._reference_policy_issue(reference, policy_kind)
            target: str | None = None
            if issue is None:
                target, _, issue = self._resolve_reference(source, reference)
            if issue is not None:
                emit("active-resource-url-rejected", source)
                return
            if target is None:
                return
            exact = self.casefold_paths.get(target.casefold())
            if exact is None:
                emit("active-resource-target-missing", source)
                return
            if exact != target:
                emit("active-resource-target-case-mismatch", source)
                return
            suffix = Path(exact).suffix.casefold()
            if reject_executable and suffix in _EXECUTABLE_RESOURCE_SUFFIXES:
                emit("active-resource-executable-target-rejected", source)
            if suffix in {".svg", ".xml"}:
                queued.add(exact)

        for page in sorted(self.html):
            for reference, _, kind in self._html_references(page):
                if kind in {"canonical", "link", "script"}:
                    continue
                consider_reference(
                    page,
                    reference,
                    policy_kind=(
                        "active-content"
                        if kind
                        in {
                            "active-content",
                            "active-fetch",
                            "automatic-navigation",
                            "beacon",
                            "form-action",
                        }
                        else "asset"
                    ),
                    reject_executable=kind
                    in {
                        "active-content",
                        "active-fetch",
                        "automatic-navigation",
                        "beacon",
                        "form-action",
                    },
                )
        for relative, text in sorted(self.text.items()):
            if Path(relative).suffix.casefold() != ".css":
                continue
            for reference, _, kind in self._css_references(text):
                consider_reference(
                    relative,
                    reference,
                    policy_kind=kind,
                    reject_executable=True,
                )
        for reference, kind, _ in self._webmanifest_references():
            if kind != "manifest-asset":
                continue
            consider_reference(
                "site.webmanifest",
                reference,
                policy_kind="manifest-asset",
                reject_executable=True,
            )

        scanned: set[str] = set()
        while queued:
            relative = min(queued)
            queued.remove(relative)
            if relative in scanned:
                continue
            scanned.add(relative)
            resource_text = self.text.get(relative)
            if resource_text is None:
                emit("active-resource-text-unavailable", relative)
                continue
            if re.search(r"<\?xml-stylesheet\b", resource_text, re.IGNORECASE):
                emit("active-resource-xml-stylesheet-rejected", relative)
            if re.search(r"<!\s*(?:doctype|entity)\b", resource_text, re.IGNORECASE):
                emit("active-resource-document-declaration-rejected", relative)
            try:
                root = ET.fromstring(resource_text)
            except ET.ParseError:
                emit("active-resource-xml-invalid", relative)
                continue
            for element in root.iter():
                if not isinstance(element.tag, str):
                    continue
                tag = element.tag.rsplit("}", 1)[-1].casefold()
                if tag == "script":
                    emit("active-resource-script-rejected", relative)
                if tag in {"embed", "foreignobject", "iframe", "object"}:
                    emit("active-resource-container-rejected", relative)
                attribute_name = element.attrib.get("attributeName", "").casefold()
                if tag in {"animate", "animatemotion", "animatetransform", "set"} and attribute_name in {
                    "action",
                    "data",
                    "fill",
                    "filter",
                    "href",
                    "src",
                    "stroke",
                    "xlink:href",
                }:
                    emit("active-resource-smil-url-mutation-rejected", relative)
                    for smil_name in ("from", "to", "values"):
                        raw_value = element.attrib.get(smil_name)
                        if not raw_value:
                            continue
                        for candidate in raw_value.split(";"):
                            css_references = self._css_references(candidate)
                            if css_references:
                                for reference, _, kind in css_references:
                                    consider_reference(
                                        relative,
                                        reference,
                                        policy_kind=("active-content" if kind == "asset" else kind),
                                        reject_executable=True,
                                    )
                            elif attribute_name in {
                                "action",
                                "data",
                                "href",
                                "src",
                                "xlink:href",
                            }:
                                consider_reference(
                                    relative,
                                    candidate,
                                    policy_kind="active-content",
                                    reject_executable=True,
                                )
                for raw_name, value in element.attrib.items():
                    if raw_name.casefold() in {
                        "xml:base",
                        "{http://www.w3.org/xml/1998/namespace}base",
                    }:
                        emit("active-resource-xml-base-rejected", relative)
                        continue
                    name = raw_name.rsplit("}", 1)[-1].split(":")[-1].casefold()
                    if re.fullmatch(r"on[a-z][a-z0-9_-]*", name):
                        emit("active-resource-event-handler-rejected", relative)
                    elif name in {"action", "data", "formaction", "href", "poster", "src"}:
                        consider_reference(
                            relative,
                            value,
                            policy_kind="active-content",
                            reject_executable=True,
                        )
                    elif name in {
                        "clip-path",
                        "cursor",
                        "fill",
                        "filter",
                        "marker-end",
                        "marker-mid",
                        "marker-start",
                        "mask",
                        "stroke",
                        "style",
                    }:
                        for reference, _, kind in self._css_references(value):
                            consider_reference(
                                relative,
                                reference,
                                policy_kind=("active-content" if kind == "asset" else kind),
                                reject_executable=True,
                            )
                if tag == "style" and element.text:
                    for reference, _, kind in self._css_references(element.text):
                        consider_reference(
                            relative,
                            reference,
                            policy_kind=("active-content" if kind == "asset" else kind),
                            reject_executable=True,
                        )

    def reduced_motion(self) -> None:
        checks = _mapping(self.config.get("checks"), code="trusted-config-shape-invalid")
        required = checks.get("require_reduced_motion")
        if required not in (True, False):
            raise CandidateStaticQABoundaryError("trusted-config-shape-invalid")
        if not required:
            return
        css = "\n".join(
            text for path, text in sorted(self.text.items()) if Path(path).suffix.casefold() == ".css"
        )
        css_without_comments = _strip_c_style_comments(css, line_comments=False)
        conditional_ranges = _css_conditional_ranges(css_without_comments)
        structural_conditional_starts = {start for start, _ in conditional_ranges}
        css_matches = [
            match
            for match in _REDUCED_MOTION.finditer(css_without_comments)
            if match.start() in structural_conditional_starts
            and not any(start < match.start() < end for start, end in conditional_ranges)
        ]
        css_effect_found = False
        for media in css_matches:
            closing = _matching_closing_brace(css_without_comments, media.end() - 1)
            if closing is None:
                continue
            body = css_without_comments[media.end() : closing]
            nested_conditional_ranges = _css_conditional_ranges(body)
            if any(
                match
                for match in _REDUCED_MOTION_EFFECT.finditer(body)
                if _offset_is_outside_string(body, match.start())
                and not any(start < match.start() < end for start, end in nested_conditional_ranges)
            ):
                css_effect_found = True
                break
        loaded_scripts: set[str] = set()
        for page, inventory in self.html.items():
            for tag, attributes, _ in inventory.elements:
                if tag != "script" or not attributes.get("src"):
                    continue
                script_type = attributes.get("type", "").casefold().split(";", 1)[0].strip()
                if script_type not in {"", "application/javascript", "module", "text/javascript"}:
                    continue
                target, _, issue = self._resolve_reference(page, attributes["src"])
                if (
                    issue is None
                    and target is not None
                    and Path(target).suffix.casefold() == ".js"
                    and target in self.text
                ):
                    loaded_scripts.add(target)
        javascript_gate_seen = False
        javascript_gate_found = False
        for path in sorted(loaded_scripts):
            source = self.text[path]
            structural = _javascript_structure_mask(source)
            for match in _JS_REDUCED_MOTION_GATE.finditer(source):
                if structural[match.start() : match.start() + 2].casefold() != "if":
                    continue
                if not _javascript_gate_controls_statement(source, match.end()):
                    continue
                javascript_gate_seen = True
                if _javascript_gate_is_reachable(source, match.start()):
                    javascript_gate_found = True
                    break
            if javascript_gate_found:
                break
        if not css_matches:
            self.add("design.reduced-motion", "reduced-motion-css-missing")
        elif not css_effect_found:
            self.add("design.reduced-motion", "reduced-motion-css-effect-missing")
        if not javascript_gate_found:
            self.add(
                "design.reduced-motion",
                (
                    "reduced-motion-javascript-proof-unavailable"
                    if javascript_gate_seen
                    else "reduced-motion-javascript-gate-missing"
                ),
            )

    def asset_versioning(self) -> None:
        site = _mapping(self.config.get("site"), code="trusted-config-shape-invalid")
        critical_routes = set(_string_list(site.get("critical_routes"), code="trusted-config-shape-invalid"))
        route_keys: set[str] = set()
        for relative, parser in sorted(self.html.items()):
            if relative not in critical_routes:
                continue
            current: set[str] = set()
            for tag, attrs, line in parser.elements:
                reference = ""
                if tag == "script":
                    reference = attrs.get("src", "")
                elif tag == "link":
                    reference = attrs.get("href", "")
                if not re.search(r"(?:^|/)(?:styles|tokens|script)\.(?:css|js)(?:[?#]|$)", reference, re.I):
                    continue
                try:
                    query = urlsplit(reference).query
                except ValueError:
                    query = ""
                values = [
                    part.split("=", 1)[1]
                    for part in query.split("&")
                    if part.startswith("v=") and len(part.split("=", 1)) == 2
                ]
                key = values[0] if len(values) == 1 else ""
                if not key:
                    self.add(
                        "design.asset-versioning",
                        "shared-asset-version-missing",
                        path=relative,
                        line=line,
                    )
                else:
                    current.add(key)
                    route_keys.add(key)
            if len(current) > 1:
                self.add(
                    "design.asset-versioning",
                    "route-asset-version-mismatch",
                    path=relative,
                    token=sorted(_bytes_sha256(value.encode("utf-8")) for value in current),
                )
        if len(route_keys) > 1:
            self.add(
                "design.asset-versioning",
                "site-asset-version-mismatch",
                token=sorted(_bytes_sha256(value.encode("utf-8")) for value in route_keys),
            )

    def metadata(self) -> None:
        site = _mapping(self.config.get("site"), code="trusted-config-shape-invalid")
        base_url = _required_string(site.get("base_url"), code="trusted-config-shape-invalid")
        overrides = _mapping(site.get("canonical_overrides"), code="trusted-config-shape-invalid")
        critical_routes = set(_string_list(site.get("critical_routes"), code="trusted-config-shape-invalid"))
        seen_titles: dict[str, str] = {}
        seen_canonicals: dict[str, str] = {}
        htaccess = self.text.get(".htaccess", "")
        if _htaccess_has_indexing_suppression(htaccess):
            self.add(
                "metadata.route-contract",
                "critical-route-htaccess-indexing-suppression",
                path=".htaccess",
            )
        robots_text = self.text.get("robots.txt")
        if robots_text is not None and _robots_txt_blocks_critical(
            robots_text,
            sorted(critical_routes),
        ):
            self.add(
                "metadata.route-contract",
                "critical-route-robots-txt-disallow",
                path="robots.txt",
            )
        for relative, parser in sorted(self.html.items()):
            text = self.text[relative]
            elements = parser.elements
            semantic_elements = parser.semantic_elements
            html_attrs = next((attrs for tag, attrs, _ in elements if tag == "html"), {})
            metas = [attrs for tag, attrs, _ in elements if tag == "meta"]
            links = [attrs for tag, attrs, _ in elements if tag == "link"]
            metadata_identities: list[str] = []
            for attrs in metas:
                selectors = [
                    f"{key}:{attrs[key].casefold()}"
                    for key in ("name", "property", "charset", "http-equiv")
                    if attrs.get(key)
                ]
                if len(selectors) > 1:
                    self.add(
                        "metadata.route-contract",
                        "ambiguous-meta-identity",
                        path=relative,
                        token=sorted(selectors),
                    )
                metadata_identities.extend(selectors)
            for identity in sorted(
                {value for value in metadata_identities if metadata_identities.count(value) > 1}
            ):
                self.add(
                    "metadata.route-contract",
                    "duplicate-meta-identity",
                    path=relative,
                    token=_bytes_sha256(identity.encode("utf-8")),
                )
            robot_controls = [
                attrs.get("content", "")
                for attrs in metas
                if _is_crawler_meta_name(attrs.get("name", ""))
                or attrs.get("http-equiv", "").casefold() == "x-robots-tag"
            ]
            robot_suppressions = set().union(
                *(_robots_suppression_tokens(content) for content in robot_controls)
            )
            is_critical = relative in critical_routes
            has_noindex = bool(robot_suppressions & {"noindex", "none"})
            has_nofollow = bool(robot_suppressions & {"nofollow", "none"})
            if is_critical and has_noindex:
                self.add("metadata.route-contract", "critical-route-noindex", path=relative)
            if is_critical and has_nofollow:
                self.add("metadata.route-contract", "critical-route-nofollow", path=relative)
            if is_critical and robot_suppressions - {"noindex", "nofollow"}:
                self.add(
                    "metadata.route-contract",
                    "critical-route-indexing-suppression",
                    path=relative,
                )
            if has_noindex and not is_critical:
                continue
            titles = parser.title_blocks
            title = _SPACE.sub(" ", unescape(_HTML_TEXT_RE.sub(" ", titles[0][0]))).strip() if titles else ""
            description = _meta_value(metas, "name", "description")
            canonicals = [
                attrs.get("href", "")
                for attrs in links
                if "canonical" in attrs.get("rel", "").casefold().split()
            ]
            canonical = canonicals[0] if len(canonicals) == 1 else ""
            expected = _expected_canonical(relative, base_url, overrides)
            route_issues = [
                ("doctype-missing", not re.match(r"\s*<!doctype html>", text, re.I)),
                ("html-language-invalid", not re.match(r"en(?:-|$)", html_attrs.get("lang", ""), re.I)),
                (
                    "utf8-charset-missing",
                    not any(attrs.get("charset", "").casefold() == "utf-8" for attrs in metas),
                ),
                (
                    "responsive-viewport-missing",
                    "width=device-width" not in _meta_value(metas, "name", "viewport").casefold(),
                ),
                ("title-count-invalid", len(titles) != 1),
                ("title-length-invalid", not 20 <= len(title) <= 70),
                ("description-length-invalid", not 70 <= len(description) <= 180),
                ("canonical-count-invalid", len(canonicals) != 1),
                ("canonical-route-mismatch", canonical != expected),
                (
                    "h1-count-invalid",
                    sum(tag == "h1" for tag, _, _ in semantic_elements) != 1,
                ),
            ]
            for code, failed in route_issues:
                if failed:
                    self.add("metadata.route-contract", code, path=relative)
            if title:
                prior = seen_titles.get(title)
                if prior is not None:
                    self.add(
                        "metadata.route-contract",
                        "duplicate-route-title",
                        path=relative,
                        token=_bytes_sha256(title.encode("utf-8")),
                    )
                else:
                    seen_titles[title] = relative
            if canonical:
                prior = seen_canonicals.get(canonical)
                if prior is not None and expected != canonical:
                    self.add(
                        "metadata.route-contract",
                        "duplicate-canonical",
                        path=relative,
                        token=_bytes_sha256(canonical.encode("utf-8")),
                    )
                else:
                    seen_canonicals[canonical] = relative
            self._social_metadata(
                relative,
                metas,
                canonical,
                require_website_type=relative in critical_routes,
            )
            self._jsonld(relative, parser)

    def _social_metadata(
        self,
        relative: str,
        metas: Sequence[Mapping[str, str]],
        canonical: str,
        *,
        require_website_type: bool,
    ) -> None:
        og = {
            key: _meta_value(metas, "property", f"og:{key}")
            for key in ("type", "site_name", "locale", "title", "description", "url", "image", "image:alt")
        }
        twitter = {
            key: _meta_value(metas, "name", f"twitter:{key}")
            for key in ("card", "title", "description", "image", "image:alt")
        }
        required_og = ("type", "site_name", "locale", "title", "description", "url", "image", "image:alt")
        required_twitter = ("card", "title", "description", "image", "image:alt")
        if any(not og[key] for key in required_og):
            self.add("metadata.social-contract", "open-graph-core-incomplete", path=relative)
        if any(not twitter[key] for key in required_twitter):
            self.add("metadata.social-contract", "twitter-card-incomplete", path=relative)
        if og["url"] and canonical and og["url"] != canonical:
            self.add("metadata.social-contract", "open-graph-url-mismatch", path=relative)
        allowed_types = {"website"} if require_website_type else {"website", "article", "profile"}
        if og["type"] and og["type"] not in allowed_types:
            self.add("metadata.social-contract", "open-graph-type-invalid", path=relative)
        if og["site_name"] and og["site_name"] != "Aureon Zorza Technologies":
            self.add("metadata.social-contract", "open-graph-site-name-invalid", path=relative)
        if og["locale"] and og["locale"] != "en_GB":
            self.add("metadata.social-contract", "open-graph-locale-invalid", path=relative)
        if twitter["card"] and twitter["card"] != "summary_large_image":
            self.add("metadata.social-contract", "twitter-card-type-invalid", path=relative)
        if twitter["image"] and og["image"] and twitter["image"] != og["image"]:
            self.add("metadata.social-contract", "social-image-mismatch", path=relative)
        if og["image"]:
            target, _, issue = self._resolve_reference(relative, og["image"])
            if issue or target is None or target not in self.paths:
                self.add("metadata.social-contract", "social-image-local-file-missing", path=relative)

    def _jsonld(self, relative: str, parser: _HtmlInventory) -> None:
        blocks = parser.jsonld_blocks
        if not blocks:
            self.add("metadata.jsonld", "jsonld-missing", path=relative)
            return
        types: set[str] = set()
        for body, line in blocks:
            try:
                value = _strict_json_bytes(
                    body.encode("utf-8"),
                    code="embedded-jsonld-invalid",
                )
            except CandidateStaticQABoundaryError:
                self.add(
                    "metadata.jsonld",
                    "jsonld-invalid",
                    path=relative,
                    line=line,
                )
                continue
            _collect_schema_types(value, types)
        if relative == "index.html":
            if "Organization" not in types:
                self.add("metadata.jsonld", "homepage-organization-schema-missing", path=relative)
        elif not types.intersection({"WebPage", "AboutPage", "ContactPage", "CollectionPage", "ProfilePage"}):
            self.add("metadata.jsonld", "route-page-schema-missing", path=relative)

    def webmanifest(self) -> None:
        relative = "site.webmanifest"
        value = self.json.get(relative)
        if not isinstance(value, Mapping):
            self.add("metadata.webmanifest", "webmanifest-missing-or-invalid")
            return
        for field in ("name", "short_name", "start_url", "display", "icons"):
            if value.get(field) in (None, "", []):
                self.add(
                    "metadata.webmanifest",
                    "webmanifest-required-field-missing",
                    path=relative,
                    token=field,
                )
        for field in ("start_url", "scope"):
            if field in value and not isinstance(value.get(field), str):
                self.add(
                    "metadata.webmanifest",
                    "webmanifest-url-field-invalid",
                    path=relative,
                    token=field,
                )
        for field in ("icons", "screenshots"):
            raw_items = value.get(field)
            if raw_items is None:
                continue
            if not isinstance(raw_items, list):
                self.add(
                    "metadata.webmanifest",
                    "webmanifest-url-field-invalid",
                    path=relative,
                    token=field,
                )
                continue
            for item in raw_items:
                if not isinstance(item, Mapping) or not isinstance(item.get("src"), str):
                    self.add(
                        "metadata.webmanifest",
                        "webmanifest-url-field-invalid",
                        path=relative,
                        token=f"{field}[].src",
                    )
        collection_fields = {
            "shortcuts": ("url",),
            "protocol_handlers": ("url",),
            "file_handlers": ("action",),
        }
        for field, required_keys in collection_fields.items():
            raw_items = value.get(field)
            if raw_items is None:
                continue
            if not isinstance(raw_items, list):
                self.add(
                    "metadata.webmanifest",
                    "webmanifest-url-field-invalid",
                    path=relative,
                    token=field,
                )
                continue
            for item in raw_items:
                if not isinstance(item, Mapping):
                    self.add(
                        "metadata.webmanifest",
                        "webmanifest-url-field-invalid",
                        path=relative,
                        token=f"{field}[]",
                    )
                    continue
                for key in required_keys:
                    if not isinstance(item.get(key), str) or not str(item.get(key)).strip():
                        self.add(
                            "metadata.webmanifest",
                            "webmanifest-url-field-invalid",
                            path=relative,
                            token=f"{field}[].{key}",
                        )
                if field == "shortcuts" and "icons" in item:
                    icons = item.get("icons")
                    if not isinstance(icons, list) or any(
                        not isinstance(icon, Mapping) or not isinstance(icon.get("src"), str)
                        for icon in icons
                    ):
                        self.add(
                            "metadata.webmanifest",
                            "webmanifest-url-field-invalid",
                            path=relative,
                            token="shortcuts[].icons[].src",
                        )
        for field, key in (
            ("note_taking", "new_note_url"),
            ("share_target", "action"),
            ("serviceworker", "src"),
        ):
            raw = value.get(field)
            if raw is not None and (
                not isinstance(raw, Mapping)
                or not isinstance(raw.get(key), str)
                or not str(raw.get(key)).strip()
            ):
                self.add(
                    "metadata.webmanifest",
                    "webmanifest-url-field-invalid",
                    path=relative,
                    token=f"{field}.{key}",
                )
        tab_strip = value.get("tab_strip")
        if tab_strip is not None:
            new_tab_button = tab_strip.get("new_tab_button") if isinstance(tab_strip, Mapping) else None
            if (
                not isinstance(new_tab_button, Mapping)
                or not isinstance(new_tab_button.get("url"), str)
                or not str(new_tab_button.get("url")).strip()
            ):
                self.add(
                    "metadata.webmanifest",
                    "webmanifest-url-field-invalid",
                    path=relative,
                    token="tab_strip.new_tab_button.url",
                )
        asset_suffixes = frozenset({".avif", ".gif", ".ico", ".jpeg", ".jpg", ".png", ".svg", ".webp"})
        for reference, kind, field in self._webmanifest_references():
            issue = self._reference_policy_issue(reference, kind)
            target: str | None = None
            if issue is None:
                target, _, issue = self._resolve_reference(relative, reference)
            if issue is not None:
                self.add(
                    "metadata.webmanifest",
                    "webmanifest-active-or-remote-url-rejected",
                    path=relative,
                    token=field,
                )
                continue
            exact = self.casefold_paths.get(str(target).casefold()) if target is not None else None
            if exact is None:
                self.add(
                    "metadata.webmanifest",
                    "webmanifest-local-target-missing",
                    path=relative,
                    token=field,
                )
                continue
            if exact != target:
                self.add(
                    "metadata.webmanifest",
                    "webmanifest-local-target-case-mismatch",
                    path=relative,
                    token=field,
                )
                continue
            suffix = Path(exact).suffix.casefold()
            if kind == "manifest-executable":
                self.add(
                    "metadata.webmanifest",
                    "webmanifest-executable-target-rejected",
                    path=relative,
                    token=field,
                )
            elif kind == "manifest-asset" and suffix not in asset_suffixes:
                self.add(
                    "metadata.webmanifest",
                    "webmanifest-asset-target-type-invalid",
                    path=relative,
                    token=field,
                )
            elif kind in {"manifest-navigation", "manifest-scope"} and suffix not in {
                ".htm",
                ".html",
            }:
                self.add(
                    "metadata.webmanifest",
                    "webmanifest-navigation-target-type-invalid",
                    path=relative,
                    token=field,
                )

    def ethos(self) -> None:
        ethos = _mapping(self.config.get("ethos"), code="trusted-config-shape-invalid")
        site = _mapping(self.config.get("site"), code="trusted-config-shape-invalid")
        critical = _string_list(site.get("critical_routes"), code="trusted-config-shape-invalid")
        collective = " ".join(self.html[path].visible_text for path in critical if path in self.html)
        signals = ethos.get("required_site_signals")
        if not isinstance(signals, list):
            raise CandidateStaticQABoundaryError("trusted-config-shape-invalid")
        for raw in signals:
            item = _mapping(raw, code="trusted-config-shape-invalid")
            identifier = _required_string(item.get("id"), code="trusted-config-shape-invalid")
            pattern = _compile_config_pattern(item.get("pattern"))
            if not pattern.search(collective):
                self.add(
                    "ethos.public-boundaries",
                    "required-ethos-signal-missing",
                    token=identifier,
                )
        prohibited = ethos.get("prohibited_claim_patterns")
        if not isinstance(prohibited, list):
            raise CandidateStaticQABoundaryError("trusted-config-shape-invalid")
        for relative, parser in sorted(self.html.items()):
            surface = parser.visible_text
            for raw in prohibited:
                item = _mapping(raw, code="trusted-config-shape-invalid")
                identifier = _required_string(item.get("id"), code="trusted-config-shape-invalid")
                pattern = _compile_config_pattern(item.get("pattern"))
                match = pattern.search(surface)
                if match:
                    severity = "warning" if item.get("severity") == "warning" else "blocker"
                    self.add(
                        "ethos.public-boundaries",
                        "prohibited-public-claim-pattern",
                        path=relative,
                        token=identifier,
                        severity=severity,
                    )
        for relative in critical:
            route_parser = self.html.get(relative)
            if route_parser is None:
                continue
            body = route_parser.visible_text
            if not re.search(r"\b(?:evidence|research|source)\b", body, re.I):
                self.add("ethos.public-boundaries", "route-evidence-ethos-missing", path=relative)
            if not re.search(r"\b(?:boundary|claim|proof|review|human|not|pending)\b", body, re.I):
                self.add("ethos.public-boundaries", "route-authority-boundary-missing", path=relative)

    def run(self) -> None:
        self.load_text_and_json()
        if self.mode == "website-operator-static":
            self.required_files()
            self.claim_inputs("website.claim-inputs")
            self.budgets()
            self.secrets()
        elif self.mode == "v28-design-system-static":
            self.html_structure()
            self.local_references()
            self.active_resources()
            self.accessibility()
            self.executable_javascript()
            self.reduced_motion()
            self.asset_versioning()
        elif self.mode == "v28-metadata-ethos-static":
            self.metadata()
            self.webmanifest()
            self.ethos()
            self.claim_inputs("ethos.claim-inputs")
        else:
            raise CandidateStaticQABoundaryError("mode-invalid")


def _mapping(value: object, *, code: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise CandidateStaticQABoundaryError(code)
    return dict(value)


def _required_string(value: object, *, code: str) -> str:
    if not isinstance(value, str) or not value:
        raise CandidateStaticQABoundaryError(code)
    return value


def _string_list(value: object, *, code: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise CandidateStaticQABoundaryError(code)
    return list(value)


def _positive_int(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise CandidateStaticQABoundaryError("trusted-config-budget-invalid")
    return value


def _safe_relative(value: object, *, code: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise CandidateStaticQABoundaryError(code)
    candidate = Path(value)
    if candidate.is_absolute() or any(part in {"", ".", ".."} for part in candidate.parts):
        raise CandidateStaticQABoundaryError(code)
    return candidate.as_posix()


def _compile_config_pattern(value: object) -> re.Pattern[str]:
    raw = _required_string(value, code="trusted-config-pattern-invalid")
    try:
        return re.compile(raw, re.IGNORECASE)
    except re.error as exc:
        raise CandidateStaticQABoundaryError("trusted-config-pattern-invalid") from exc


def _meta_value(
    metas: Sequence[Mapping[str, str]],
    key: str,
    value: str,
) -> str:
    expected = value.casefold()
    for attrs in metas:
        if attrs.get(key, "").casefold() == expected:
            return attrs.get("content", "")
    return ""


def _expected_canonical(relative: str, base_url: str, overrides: Mapping[str, Any]) -> str:
    override = overrides.get(relative)
    if isinstance(override, str) and override:
        return override
    base = base_url.rstrip("/") + "/"
    if relative == "index.html":
        return base
    if relative.endswith("/index.html"):
        return base + relative.removesuffix("index.html")
    return base + relative


def _collect_schema_types(value: object, output: set[str]) -> None:
    if isinstance(value, list):
        for item in value:
            _collect_schema_types(item, output)
    elif isinstance(value, Mapping):
        current = value.get("@type")
        if isinstance(current, str):
            output.add(current)
        elif isinstance(current, list):
            output.update(str(item) for item in current if isinstance(item, str))
        for child in value.values():
            _collect_schema_types(child, output)


def _normalise_findings(findings: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    unique: dict[tuple[object, ...], dict[str, object]] = {}
    for raw in findings:
        item = dict(raw)
        key = (
            item["code"],
            item["severity"],
            item["path"],
            item["line"],
            item["evidence_hash"],
        )
        unique[key] = item
    return sorted(
        unique.values(),
        key=lambda item: (
            str(item["code"]),
            str(item["path"]),
            int(str(item["line"])),
            str(item["evidence_hash"]),
        ),
    )


def audit_candidate_static(candidate_root: str | Path, *, mode: str) -> dict[str, Any]:
    """Audit one exact staged website tree without modifying it."""

    if mode not in MODES:
        raise CandidateStaticQABoundaryError("mode-invalid")
    repo_root = _repo_root_from_file()
    root = _validate_candidate_root(str(candidate_root), repo_root=repo_root)
    config, config_hash_before = _read_trusted_config(repo_root)
    before = _snapshot_tree(root)
    audit = _Audit(mode=mode, root=root, config=config, snapshot=before)
    audit.run()
    after = _snapshot_tree(root)
    _, config_hash_after = _read_trusted_config(repo_root)
    if before != after:
        raise CandidateStaticQABoundaryError("candidate-tree-mutated-during-audit")
    if config_hash_before != config_hash_after:
        raise CandidateStaticQABoundaryError("trusted-config-mutated-during-audit")
    findings = _normalise_findings(audit.findings)
    checks = []
    for identifier in MODE_CHECKS[mode]:
        codes = sorted(audit.finding_checks.get(identifier, set()))
        checks.append({"id": identifier, "passed": not codes, "blocker_codes": codes})
    decision = {
        "status": "pass" if not findings else "blocked",
        "blocker_count": len(findings),
        "finding_set_sha256": _json_sha256(findings),
    }
    relative_root = root.relative_to(repo_root).as_posix()
    return {
        "schema": SCHEMA,
        "mode": mode,
        "source": {
            "root": relative_root,
            "tree_sha256": before["tree_sha256"],
            "file_count": before["file_count"],
            "total_bytes": before["total_bytes"],
        },
        "checks": checks,
        "findings": findings,
        "decision": decision,
        "limitations": LIMITATIONS,
        "authority": AUTHORITY,
    }


def _invalid_receipt(mode: str, code: str) -> dict[str, Any]:
    finding = {
        "code": code,
        "severity": "boundary",
        "path": ".",
        "line": 0,
        "evidence_hash": _json_sha256({"code": code}),
    }
    findings = [finding]
    return {
        "schema": SCHEMA,
        "mode": mode if mode in MODES else "invalid",
        "source": {
            "root": "",
            "tree_sha256": "",
            "file_count": 0,
            "total_bytes": 0,
        },
        "checks": [],
        "findings": findings,
        "decision": {
            "status": "invalid",
            "blocker_count": 1,
            "finding_set_sha256": _json_sha256(findings),
        },
        "limitations": LIMITATIONS,
        "authority": AUTHORITY,
    }


def _parse_cli(argv: Sequence[str]) -> tuple[str, str]:
    if (
        len(argv) != 4
        or argv[0] != "--mode"
        or argv[2] != "--candidate-root"
        or argv.count("--mode") != 1
        or argv.count("--candidate-root") != 1
    ):
        raise CandidateStaticQABoundaryError("cli-contract-invalid")
    mode = argv[1]
    if mode not in MODES:
        raise CandidateStaticQABoundaryError("mode-invalid")
    return mode, argv[3]


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    mode = arguments[1] if len(arguments) > 1 and arguments[0] == "--mode" else "invalid"
    try:
        mode, candidate_root = _parse_cli(arguments)
        receipt = audit_candidate_static(candidate_root, mode=mode)
    except CandidateStaticQABoundaryError as exc:
        receipt = _invalid_receipt(mode, exc.code)
        sys.stdout.write(_canonical_bytes(receipt).decode("utf-8") + "\n")
        return 3
    except Exception:
        receipt = _invalid_receipt(mode, "unexpected-static-qa-boundary")
        sys.stdout.write(_canonical_bytes(receipt).decode("utf-8") + "\n")
        return 3
    sys.stdout.write(_canonical_bytes(receipt).decode("utf-8") + "\n")
    return 0 if receipt["decision"]["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
