from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shutil
import string
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree


REPO_ROOT = Path(__file__).resolve().parents[4]
GRANTS = REPO_ROOT / "data" / "research" / "grants"
APPLICATIONS_DIR = GRANTS / "applications"
PIPELINES_DIR = GRANTS / "pipelines"
PIPELINE_JSON = GRANTS / "pipeline.json"
AUTOPILOT_JSON = GRANTS / "autopilot_status.json"
ACTIVITY_LOG = GRANTS / "activity.log"

RESULT = "GARY_AUREON_METADATA_AND_RESEARCH_GATHERED"

ALLOWED_EXTENSIONS = {
    ".bib",
    ".csv",
    ".docx",
    ".json",
    ".jsonl",
    ".jpeg",
    ".jpg",
    ".md",
    ".pdf",
    ".png",
    ".pptx",
    ".ris",
    ".txt",
    ".webp",
    ".xlsx",
    ".yaml",
    ".yml",
}
TEXT_EXTENSIONS = {".bib", ".csv", ".json", ".jsonl", ".md", ".ris", ".txt", ".yaml", ".yml"}
OFFICE_TEXT_EXTENSIONS = {".docx", ".pptx", ".xlsx"}

MAX_FILE_SIZE_BYTES = 90 * 1024 * 1024
MAX_TEXT_SCAN_BYTES = 4 * 1024 * 1024
MAX_SNIPPET_CHARS = 2400
MAX_COPY_COUNT = 10000
MAX_COPY_BYTES = 950 * 1024 * 1024

CONTENT_SCAN_ROOT_FRAGMENTS = {
    "/users/user/aureonresearch/",
    "/users/user/aureon_work_hub_20260705/",
    "/users/user/aureonobsidianvault/",
    "/users/user/queen_research/",
    "/users/user/aureon-trading/data/research/grants/",
}

PRIMARY_SOURCE_ROOT_FRAGMENTS = {
    "/users/user/aureonresearch/",
    "/users/user/aureon_work_hub_20260705/",
    "/users/user/aureonobsidianvault/",
    "/users/user/queen_research/",
    "/users/user/aureon-trading/data/research/grants/",
}

GENERIC_CONTEXT_FRAGMENTS = [
    "/users/user/aureon-trading-integrated-main-20260508/",
    "/users/user/aureon-trading-github-latest-20260701/",
    "/users/user/aureon-trading-latest/",
    "/users/user/aureon-trading-clean/",
    "/users/user/aureon-trading-publish-",
    "/users/user/aureon-trading/",
    "/data/research/grants/",
    "/applications/",
    "/pipelines/",
    "/scripts/",
    "/reports/",
    "/evidence/",
]

RG_ALLOWED_GLOBS = [f"*{extension}" for extension in sorted(ALLOWED_EXTENSIONS)]
RG_EXCLUDED_GLOBS = [
    "!$Recycle.Bin/**",
    "!Program Files/**",
    "!Program Files (x86)/**",
    "!ProgramData/**",
    "!Recovery/**",
    "!System Volume Information/**",
    "!$WinREAgent/**",
    "!c/**",
    "!mnt/**",
    "!Users/user/.aureon_grant_private/**",
    "!Users/user/.claude/**",
    "!Users/user/.codex/**",
    "!Users/user/.kimi_openclaw/**",
    "!Users/user/.openclaw/**",
    "!Users/user/.vscode/**",
    "!Users/user/.vscode-insiders/**",
    "!Users/user/AppData/**",
    "!Users/user/aureon-trading-clean/**",
    "!Users/user/aureon-trading-github-latest-20260701/**",
    "!Users/user/aureon-trading-integrated-main-20260508/**",
    "!Users/user/aureon-trading-latest/**",
    "!Users/user/aureon-trading-publish-*/**",
    "!Users/user/aureon-update-preservation-20260508/**",
    "!Windows/**",
    "!.kimi_openclaw/**",
    "!.openclaw/**",
    "!**/.cache/**",
    "!**/.claude/**",
    "!**/.git/**",
    "!**/.hg/**",
    "!**/.mypy_cache/**",
    "!**/.next/**",
    "!**/.pytest_cache/**",
    "!**/.ruff_cache/**",
    "!**/.svn/**",
    "!**/.venv/**",
    "!**/__pycache__/**",
    "!**/build/**",
    "!**/cache/**",
    "!**/coverage/**",
    "!**/dist/**",
    "!**/env/**",
    "!**/logs/**",
    "!**/node_modules/**",
    "!**/temp/**",
    "!**/tmp/**",
    "!**/venv/**",
]

EXCLUDED_DIR_NAMES = {
    "$recycle.bin",
    ".cache",
    ".codex",
    ".git",
    ".hg",
    ".mypy_cache",
    ".next",
    ".pytest_cache",
    ".ruff_cache",
    ".svn",
    ".venv",
    "__pycache__",
    "appdata",
    "build",
    "cache",
    "coverage",
    "dist",
    "env",
    "harmonic_cache",
    "intel",
    "logs",
    "node_modules",
    "nvidia",
    "onedrivetemp",
    "perflogs",
    "program files",
    "program files (x86)",
    "programdata",
    "recovery",
    "system volume information",
    "temp",
    "tmp",
    "venv",
    "windows",
    "ws_cache",
}

EXCLUDED_PATH_FRAGMENTS = {
    "/.aureon_grant_private/",
    "/.gnupg/",
    "/.ssh/",
    "/appdata/",
    "/credentials/",
    "/credential/",
    "/private_keys/",
}

EXCLUDED_PATH_TERMS = {
    "accounting",
    "accountant",
    "accounts pack",
    "affidavit",
    "aureon-trading-publish-",
    "case no.",
    "companies_house_accounts",
    "court orders",
    "ct600",
    "ct_financial",
    "curriculum vitae",
    "directors_report",
    "environment_variables",
    "expense",
    "expenses",
    "financial_year",
    "fibrus",
    "fibrus networks",
    "full accounts",
    "full_accounts",
    "gary_aureon_metadata_research_evidence_",
    "gary_aureon_metadata_research_inventory_",
    "gary leckey cv",
    "gareth leckey cv",
    "injunction",
    "judgment",
    "litigation",
    "local_research_hub_file_manifest",
    "local_research_paper_inventory",
    "local_research_source_to_hub_manifest",
    "motion to dismiss",
    "profit and loss",
    "profit_and_loss",
    "plaintiff",
    "pleadings",
    "reconciliation",
    "revolut",
    "resume",
    "solicitor",
    "source_reconciliation",
    "statement of claim",
    "summary judgment",
    "sumup",
    "transaction_classification",
    "writ -",
    "zempler",
}

EXCLUDED_NAME_TERMS = {
    ".env",
    ".key",
    ".pem",
    ".pfx",
    "access_token",
    "account_statement",
    "api_key",
    "auth_token",
    "bank",
    "bearer",
    "client_secret",
    "cookie",
    "affidavit",
    "credential",
    "credentials",
    "court",
    "fibrus",
    "invoice",
    "injunction",
    "jwt",
    "judgment",
    "litigation",
    "oauth",
    "password",
    "payroll",
    "plaintiff",
    "pnl",
    "p&l",
    "private_key",
    "refresh_token",
    "secret",
    "session",
    "solicitor",
    "ssh_key",
    "tax",
    "token",
    "trial_balance",
    "vat",
}

IDENTITY_TERMS = {
    "aureon": 9,
    "aureon institute": 12,
    "gary": 6,
    "gary anthony leckey": 14,
    "gary leckey": 13,
    "gaxlec": 9,
    "leckey": 10,
    "r&a consulting": 12,
    "r & a consulting": 12,
    "r and a consulting": 12,
    "ra consulting": 8,
}

RESEARCH_TERMS = {
    "academia": 4,
    "alfie": 5,
    "antarctic": 4,
    "architecture": 4,
    "arctic": 4,
    "article": 5,
    "audit": 4,
    "bibliography": 5,
    "coherence": 5,
    "druid": 7,
    "empirical": 6,
    "epas": 7,
    "evidence os": 8,
    "framework": 4,
    "grant ready": 5,
    "harmonic": 5,
    "hnc": 8,
    "journal": 6,
    "lidar": 5,
    "lumina": 6,
    "metadata": 8,
    "meta data": 8,
    "orcid": 6,
    "paper": 7,
    "preprint": 7,
    "profile": 3,
    "publication": 7,
    "research": 8,
    "researchgate": 6,
    "systechdev": 6,
    "technical report": 7,
    "thesis": 7,
    "validation": 7,
    "verification": 6,
    "white paper": 9,
    "whitepaper": 9,
}

SECRET_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----", re.IGNORECASE),
    re.compile(r"(?i)\b(api[_-]?key|client[_-]?secret|access[_-]?token|refresh[_-]?token|auth[_-]?token)\b\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{12,}"),
    re.compile(r"(?i)\b(password|passwd|pwd)\b\s*[:=]\s*['\"]?[^'\"\s]{8,}"),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9_./+=-]{20,}"),
]

SENSITIVE_CONTENT_PATTERNS = [
    re.compile(r"fibrus networks", re.IGNORECASE),
    re.compile(r"high court of justice", re.IGNORECASE),
    re.compile(r"king'?s bench", re.IGNORECASE),
    re.compile(r"\bplaintiff\b", re.IGNORECASE),
    re.compile(r"\bdefendant\b", re.IGNORECASE),
    re.compile(r"affidavit of", re.IGNORECASE),
    re.compile(r"statement of claim", re.IGNORECASE),
    re.compile(r"summary judgment", re.IGNORECASE),
    re.compile(r"\binjunction\b", re.IGNORECASE),
    re.compile(r"professional profile.{0,300}career summary", re.IGNORECASE | re.DOTALL),
]

FINANCE_CONTENT_PATTERNS = [
    re.compile(r"\baccountant\b", re.IGNORECASE),
    re.compile(r"\baccountancy\b", re.IGNORECASE),
    re.compile(r"\bprofit\s+and\s+loss\b", re.IGNORECASE),
    re.compile(r"\bfull\s+accounts\b", re.IGNORECASE),
    re.compile(r"\bcompanies\s+house\s+accounts\b", re.IGNORECASE),
    re.compile(r"\btransaction\s+classification\b", re.IGNORECASE),
    re.compile(r"\bsource\s+reconciliation\b", re.IGNORECASE),
    re.compile(r"\bsumup\b", re.IGNORECASE),
    re.compile(r"\bzempler\b", re.IGNORECASE),
    re.compile(r"\brevolut\b", re.IGNORECASE),
    re.compile(r"\bct600\b", re.IGNORECASE),
    re.compile(r"\bfinancial\s+year\b", re.IGNORECASE),
]


def now_local() -> datetime:
    return datetime.now().astimezone()


def fixed_drive_roots() -> list[Path]:
    roots: list[Path] = []
    if os.name == "nt":
        for letter in string.ascii_uppercase:
            root = Path(f"{letter}:\\")
            if root.exists():
                roots.append(root)
    else:
        roots.append(Path("/"))
    return roots


def enumerate_allowed_files(scan_roots: list[Path]) -> tuple[list[Path], dict[str, Any]]:
    rg_path = shutil.which("rg")
    paths: list[Path] = []
    stats: dict[str, Any] = {"method": "rg --files", "roots": {}, "errors": []}
    if not rg_path:
        stats["method"] = "python os.walk fallback"
        for root in scan_roots:
            root_count = 0
            for dirpath, dirnames, filenames in os.walk(root, topdown=True):
                current = Path(dirpath)
                if excluded_dir(current):
                    dirnames[:] = []
                    continue
                dirnames[:] = [name for name in dirnames if not excluded_dir(current / name)]
                for filename in filenames:
                    path = current / filename
                    if path.suffix.lower() in ALLOWED_EXTENSIONS:
                        paths.append(path)
                        root_count += 1
            stats["roots"][str(root)] = root_count
        return paths, stats

    for root in scan_roots:
        if not root.exists():
            continue
        command = [rg_path, "--files", "--hidden", "--no-ignore", "--no-messages"]
        for glob in RG_ALLOWED_GLOBS:
            command.extend(["--glob", glob])
        for glob in RG_EXCLUDED_GLOBS:
            command.extend(["--glob", glob])
        try:
            completed = subprocess.run(
                command,
                cwd=str(root),
                check=False,
                capture_output=True,
                text=True,
                timeout=420,
            )
        except subprocess.TimeoutExpired:
            stats["errors"].append({"root": str(root), "error": "rg_timeout"})
            continue
        if completed.returncode not in (0, 1):
            stats["errors"].append({"root": str(root), "error": completed.stderr[-1200:]})
        root_paths: list[Path] = []
        for line in completed.stdout.splitlines():
            if not line.strip():
                continue
            root_paths.append((root / line).resolve())
        paths.extend(root_paths)
        stats["roots"][str(root)] = len(root_paths)
    return paths, stats


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def rel_grants(path: Path) -> str:
    try:
        return path.resolve().relative_to(GRANTS.resolve()).as_posix()
    except ValueError:
        return str(path)


def stable_slug(path: Path, digest: str, max_len: int = 88) -> str:
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", path.stem).strip("._-")
    stem = stem[:max_len] or "gary_aureon_evidence"
    return f"{stem}_{digest[:10]}{path.suffix.lower()}"


def lowered_path(path: Path) -> str:
    return path.as_posix().replace("\\", "/").lower()


def meaningful_path_text(path: Path) -> str:
    text = lowered_path(path)
    for fragment in GENERIC_CONTEXT_FRAGMENTS:
        text = text.replace(fragment, "/")
    return text


def in_primary_source_root(path_text: str) -> bool:
    return any(fragment in path_text for fragment in PRIMARY_SOURCE_ROOT_FRAGMENTS)


def excluded_dir(path: Path) -> bool:
    parts = {part.lower() for part in path.parts}
    if parts & EXCLUDED_DIR_NAMES:
        return True
    normalized = f"/{lowered_path(path).strip('/')}/"
    return any(fragment in normalized for fragment in EXCLUDED_PATH_FRAGMENTS)


def excluded_path(path: Path) -> tuple[bool, str | None]:
    if excluded_dir(path):
        return True, "excluded_directory"
    name = path.name.lower()
    if any(term in name for term in EXCLUDED_NAME_TERMS):
        return True, "excluded_name_term"
    normalized = f"/{lowered_path(path).strip('/')}/"
    if any(fragment in normalized for fragment in EXCLUDED_PATH_FRAGMENTS):
        return True, "excluded_path_fragment"
    if any(term in normalized for term in EXCLUDED_PATH_TERMS):
        return True, "excluded_path_term"
    cv_like_name = name.endswith(" cv.docx") or name.endswith(" cv.pdf") or "_cv" in name or "-cv" in name
    if cv_like_name:
        return True, "excluded_cv_like_name"
    return False, None


def term_matches(text: str, terms: dict[str, int]) -> list[str]:
    return sorted(term for term in terms if term in text)


def read_text_snippet(path: Path, limit_chars: int = MAX_SNIPPET_CHARS) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:limit_chars]
    except Exception as exc:
        return f"[text unavailable: {exc.__class__.__name__}]"


def read_docx_text(path: Path, limit_chars: int = MAX_SNIPPET_CHARS) -> str:
    try:
        with zipfile.ZipFile(path) as archive:
            raw = archive.read("word/document.xml")
        root = ElementTree.fromstring(raw)
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        paragraphs: list[str] = []
        for paragraph in root.findall(".//w:p", ns):
            line = "".join(node.text or "" for node in paragraph.findall(".//w:t", ns)).strip()
            if line:
                paragraphs.append(line)
            if sum(len(item) for item in paragraphs) >= limit_chars:
                break
        return "\n".join(paragraphs)[:limit_chars]
    except Exception as exc:
        return f"[docx text unavailable: {exc.__class__.__name__}]"


def read_pptx_text(path: Path, limit_chars: int = MAX_SNIPPET_CHARS) -> str:
    try:
        chunks: list[str] = []
        with zipfile.ZipFile(path) as archive:
            for name in sorted(archive.namelist()):
                if not name.startswith("ppt/slides/slide") or not name.endswith(".xml"):
                    continue
                root = ElementTree.fromstring(archive.read(name))
                for node in root.iter():
                    if node.tag.endswith("}t") and node.text:
                        chunks.append(node.text)
                if sum(len(item) for item in chunks) >= limit_chars:
                    break
        return "\n".join(chunks)[:limit_chars] if chunks else "[pptx slide text empty]"
    except Exception as exc:
        return f"[pptx text unavailable: {exc.__class__.__name__}]"


def read_xlsx_text(path: Path, limit_chars: int = MAX_SNIPPET_CHARS) -> str:
    try:
        chunks: list[str] = []
        with zipfile.ZipFile(path) as archive:
            shared = []
            if "xl/sharedStrings.xml" in archive.namelist():
                root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
                for node in root.iter():
                    if node.tag.endswith("}t") and node.text:
                        shared.append(node.text)
            chunks.extend(shared[:200])
        return "\n".join(chunks)[:limit_chars] if chunks else "[xlsx shared strings empty]"
    except Exception as exc:
        return f"[xlsx text unavailable: {exc.__class__.__name__}]"


def read_pdf_metadata(path: Path) -> dict[str, Any]:
    metadata: dict[str, Any] = {"text_snippet": "[pdf text extraction not performed]"}
    for module_name in ("pypdf", "PyPDF2"):
        try:
            module = __import__(module_name)
            reader = module.PdfReader(str(path))
            metadata["pages"] = len(reader.pages)
            info = reader.metadata or {}
            metadata["pdf_metadata"] = {str(k): str(v) for k, v in dict(info).items()}
            if reader.pages:
                text = reader.pages[0].extract_text() or ""
                metadata["text_snippet"] = text[:MAX_SNIPPET_CHARS] if text else "[first page text empty]"
            metadata["pdf_parser"] = module_name
            return metadata
        except Exception:
            continue
    return metadata


def extract_metadata(path: Path, force_text: bool) -> dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix in TEXT_EXTENSIONS and (force_text or path.stat().st_size <= MAX_TEXT_SCAN_BYTES):
        return {"text_snippet": read_text_snippet(path)}
    if suffix == ".docx" and force_text:
        return {"text_snippet": read_docx_text(path)}
    if suffix == ".pptx" and force_text:
        return {"text_snippet": read_pptx_text(path)}
    if suffix == ".xlsx" and force_text:
        return {"text_snippet": read_xlsx_text(path)}
    if suffix == ".pdf" and force_text:
        return read_pdf_metadata(path)
    if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
        return {"text_snippet": "[image evidence; text extraction not performed]"}
    return {"text_snippet": "[path-only candidate; content extraction deferred]"}


def has_secret_material(text: str) -> bool:
    return any(pattern.search(text) for pattern in SECRET_PATTERNS)


def has_sensitive_material(text: str) -> bool:
    return any(pattern.search(text) for pattern in SENSITIVE_CONTENT_PATTERNS)


def has_finance_material(text: str) -> bool:
    return any(pattern.search(text) for pattern in FINANCE_CONTENT_PATTERNS)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def score_candidate(path: Path, text_blob: str) -> tuple[int, list[str], list[str], str]:
    identity = term_matches(text_blob, IDENTITY_TERMS)
    research = term_matches(text_blob, RESEARCH_TERMS)
    score = sum(IDENTITY_TERMS[term] for term in identity) + sum(RESEARCH_TERMS[term] for term in research)
    score += {
        ".pdf": 8,
        ".docx": 7,
        ".pptx": 6,
        ".xlsx": 5,
        ".md": 5,
        ".json": 5,
        ".jsonl": 5,
        ".csv": 4,
        ".txt": 3,
        ".bib": 6,
        ".ris": 6,
        ".png": 3,
        ".jpg": 3,
        ".jpeg": 3,
        ".webp": 3,
    }.get(path.suffix.lower(), 0)
    normalized = lowered_path(path)
    if "/aureonresearch/" in normalized or "/aureon_work_hub_20260705/" in normalized:
        score += 10
    if "/aureonobsidianvault/" in normalized or "/queen_research/" in normalized:
        score += 8
    if "/aureon-trading/data/research/grants/" in normalized:
        score += 6
    if identity and research:
        priority = "P0"
    elif identity or (score >= 28 and research):
        priority = "P1"
    else:
        priority = "P2"
    return score, identity, research, priority


def classify_theme(path: Path, identity_terms: list[str], research_terms: list[str]) -> str:
    text = " ".join([path.name.lower(), *identity_terms, *research_terms])
    if any(term in text for term in ("orcid", "researchgate", "academia", "profile", "gary", "leckey")):
        return "gary_profile_and_public_metadata"
    if any(term in text for term in ("metadata", "meta data", "grant ready")):
        return "company_metadata_and_grant_readiness"
    if any(term in text for term in ("validation", "verification", "empirical", "audit")):
        return "validation_and_verification"
    if any(term in text for term in ("hnc", "harmonic", "coherence", "quantum")):
        return "hnc_harmonic_coherence"
    if any(term in text for term in ("epas", "druid", "alfie", "systechdev", "evidence os")):
        return "evidence_os_system_architecture"
    if any(term in text for term in ("lumina", "antarctic", "arctic", "lidar")):
        return "geospatial_and_lumina_research"
    return "supporting_company_research"


def should_try_content_scan(path: Path, stat_size: int, path_text: str, signal_text: str) -> bool:
    has_path_signal = any(term in signal_text for term in [*IDENTITY_TERMS, *RESEARCH_TERMS])
    in_content_root = any(fragment in path_text for fragment in CONTENT_SCAN_ROOT_FRAGMENTS)
    filename_signal = any(term in path.name.lower() for term in [*IDENTITY_TERMS, *RESEARCH_TERMS])
    if path.suffix.lower() in TEXT_EXTENSIONS and stat_size <= MAX_TEXT_SCAN_BYTES:
        return has_path_signal or in_content_root
    if not has_path_signal and not in_content_root:
        return False
    if path.suffix.lower() in {".docx", ".pptx", ".xlsx"}:
        return filename_signal
    if path.suffix.lower() == ".pdf":
        return filename_signal
    return False


def iter_candidate_items(scan_roots: list[Path]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    raw_items: list[dict[str, Any]] = []
    skipped: dict[str, int] = {}
    seen_paths: set[str] = set()
    allowed_paths, enumeration_stats = enumerate_allowed_files(scan_roots)
    files_seen = len(allowed_paths)
    allowed_files_seen = 0

    for path in allowed_paths:
        suffix = path.suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            continue
        allowed_files_seen += 1
        is_excluded, reason = excluded_path(path)
        if is_excluded:
            skipped[reason or "excluded"] = skipped.get(reason or "excluded", 0) + 1
            continue
        try:
            stat = path.stat()
        except OSError:
            skipped["stat_failed"] = skipped.get("stat_failed", 0) + 1
            continue
        if stat.st_size <= 0 or stat.st_size > MAX_FILE_SIZE_BYTES:
            skipped["size_guard"] = skipped.get("size_guard", 0) + 1
            continue
        try:
            resolved = str(path.resolve()).lower()
        except OSError:
            skipped["resolve_failed"] = skipped.get("resolve_failed", 0) + 1
            continue
        if resolved in seen_paths:
            skipped["duplicate_path"] = skipped.get("duplicate_path", 0) + 1
            continue
        seen_paths.add(resolved)

        path_text = lowered_path(path)
        signal_text = meaningful_path_text(path)
        path_terms = term_matches(signal_text, {**IDENTITY_TERMS, **RESEARCH_TERMS})
        force_text = should_try_content_scan(path, stat.st_size, path_text, signal_text)
        if not path_terms and not force_text and not in_primary_source_root(path_text):
            skipped["no_path_or_text_match"] = skipped.get("no_path_or_text_match", 0) + 1
            continue

        metadata = extract_metadata(path, force_text)
        snippet = str(metadata.get("text_snippet", ""))
        text_blob = f"{signal_text}\n{snippet}".lower()
        score, identity, research, priority = score_candidate(path, text_blob)
        if not identity and not research:
            skipped["no_identity_or_research_match"] = skipped.get("no_identity_or_research_match", 0) + 1
            continue
        normalized = lowered_path(path)
        if normalized.startswith(lowered_path(REPO_ROOT)) and identity == ["aureon"] and not research:
            skipped["repo_name_only_match"] = skipped.get("repo_name_only_match", 0) + 1
            continue
        if not identity and score < 20:
            skipped["weak_non_identity_match"] = skipped.get("weak_non_identity_match", 0) + 1
            continue
        guard_text = snippet
        if suffix in TEXT_EXTENSIONS:
            guard_text = read_text_snippet(path, MAX_TEXT_SCAN_BYTES)
        if has_secret_material(guard_text):
            skipped["secret_pattern"] = skipped.get("secret_pattern", 0) + 1
            continue
        if has_sensitive_material(guard_text):
            skipped["sensitive_content_pattern"] = skipped.get("sensitive_content_pattern", 0) + 1
            continue
        if has_finance_material(guard_text):
            skipped["finance_content_pattern"] = skipped.get("finance_content_pattern", 0) + 1
            continue

        try:
            file_hash = sha256_file(path)
        except OSError:
            skipped["hash_failed"] = skipped.get("hash_failed", 0) + 1
            continue

        raw_items.append(
            {
                "source_path": str(path),
                "file_name": path.name,
                "extension": suffix,
                "size_bytes": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(),
                "sha256": file_hash,
                "score": score,
                "priority": priority,
                "identity_terms": identity,
                "research_terms": research,
                "theme": classify_theme(path, identity, research),
                "claim_control": "Use as Gary/Aureon local metadata or research-output evidence only; do not present as independent validation, finance, legal, credential, partner, or award evidence without separate source checks.",
                **metadata,
            }
        )

    best_by_hash: dict[str, dict[str, Any]] = {}
    duplicates: dict[str, list[str]] = {}
    for item in sorted(raw_items, key=lambda row: (-row["score"], row["source_path"].lower())):
        if item["sha256"] not in best_by_hash:
            best_by_hash[item["sha256"]] = item
        else:
            duplicates.setdefault(item["sha256"], [best_by_hash[item["sha256"]]["source_path"]]).append(item["source_path"])

    inventory = sorted(best_by_hash.values(), key=lambda row: (-row["score"], row["priority"], row["theme"], row["file_name"].lower()))
    scan_stats = {
        "files_seen": files_seen,
        "allowed_files_seen": allowed_files_seen,
        "raw_candidate_files": len(raw_items),
        "unique_candidate_files": len(inventory),
        "duplicate_hashes": len(duplicates),
        "duplicate_paths": sum(len(paths) - 1 for paths in duplicates.values()),
        "duplicates": duplicates,
        "skipped": skipped,
        "enumeration": enumeration_stats,
    }
    return inventory, scan_stats


def copy_selected(inventory: list[dict[str, Any]], evidence_dir: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    copied: list[dict[str, Any]] = []
    not_copied: list[dict[str, Any]] = []
    used_names: set[str] = set()
    total_bytes = 0

    for item in inventory:
        if len(copied) >= MAX_COPY_COUNT:
            not_copied.append({"source_path": item["source_path"], "reason": "copy_count_limit", "sha256": item["sha256"]})
            continue
        if total_bytes + int(item["size_bytes"]) > MAX_COPY_BYTES:
            not_copied.append({"source_path": item["source_path"], "reason": "copy_byte_limit", "sha256": item["sha256"]})
            continue
        source = Path(item["source_path"])
        target_name = stable_slug(source, item["sha256"])
        if target_name.lower() in used_names:
            target_name = f"{source.stem}_{item['sha256'][:16]}{source.suffix.lower()}"
        used_names.add(target_name.lower())
        target = evidence_dir / target_name
        shutil.copy2(source, target)
        total_bytes += int(item["size_bytes"])
        copied.append(
            {
                "source_path": item["source_path"],
                "evidence_copy": rel_grants(target),
                "sha256": item["sha256"],
                "priority": item["priority"],
                "theme": item["theme"],
                "file_name": item["file_name"],
                "size_bytes": item["size_bytes"],
            }
        )
    return copied, not_copied


def render_markdown(receipt: dict[str, Any]) -> str:
    lines = [
        "# Gary/Aureon Metadata and Research Inventory",
        "",
        f"- Generated: {receipt['generated_at']}",
        f"- Result: {receipt['result']}",
        f"- Scan roots: {', '.join(receipt['scan_roots'])}",
        f"- Files seen: {receipt['summary']['files_seen']}",
        f"- Allowed files seen: {receipt['summary']['allowed_files_seen']}",
        f"- Unique candidate files: {receipt['summary']['unique_candidate_files']}",
        f"- Evidence copies created: {receipt['summary']['evidence_copies_created']}",
        f"- Duplicate hashes: {receipt['summary']['duplicate_hashes']}",
        f"- Secret-pattern files copied: {str(receipt['summary']['secret_pattern_files_copied']).lower()}",
        f"- Financial/accounting/credential-named files copied: {str(receipt['summary']['high_risk_named_files_copied']).lower()}",
        "",
        "## Theme Counts",
        "",
    ]
    for theme, count in sorted(receipt["theme_counts"].items()):
        lines.append(f"- {theme}: {count}")
    lines.extend(["", "## Priority Counts", ""])
    for priority, count in sorted(receipt["priority_counts"].items()):
        lines.append(f"- {priority}: {count}")
    lines.extend(["", "## Top Indexed Evidence", ""])
    for item in receipt["inventory"][:80]:
        lines.extend(
            [
                f"### {item['file_name']}",
                f"- Priority: {item['priority']} | Theme: {item['theme']} | Score: {item['score']}",
                f"- Source: {item['source_path']}",
                f"- SHA-256: {item['sha256']}",
                f"- Identity terms: {', '.join(item['identity_terms'])}",
                f"- Research terms: {', '.join(item['research_terms'])}",
                f"- Claim control: {item['claim_control']}",
                "",
            ]
        )
    lines.extend(["## Controls", ""])
    for control in receipt["controls"]:
        lines.append(f"- {control}")
    lines.append("")
    return "\n".join(lines)


def write_csv(path: Path, inventory: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "priority",
        "theme",
        "score",
        "file_name",
        "extension",
        "size_bytes",
        "modified_at",
        "sha256",
        "source_path",
        "identity_terms",
        "research_terms",
        "claim_control",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in inventory:
            row = {field: item.get(field) for field in fields}
            row["identity_terms"] = ";".join(item.get("identity_terms", []))
            row["research_terms"] = ";".join(item.get("research_terms", []))
            writer.writerow(row)


def copied_secret_scan(copied: list[dict[str, Any]]) -> list[str]:
    hits: list[str] = []
    for item in copied:
        path = GRANTS / item["evidence_copy"]
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")[:MAX_TEXT_SCAN_BYTES]
        except OSError:
            continue
        if has_secret_material(text):
            hits.append(item["evidence_copy"])
    return hits


def copied_sensitive_scan(copied: list[dict[str, Any]]) -> list[str]:
    hits: list[str] = []
    for item in copied:
        path = GRANTS / item["evidence_copy"]
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")[:MAX_TEXT_SCAN_BYTES]
        except OSError:
            continue
        if has_sensitive_material(text):
            hits.append(item["evidence_copy"])
    return hits


def copied_finance_scan(copied: list[dict[str, Any]]) -> list[str]:
    hits: list[str] = []
    for item in copied:
        path = GRANTS / item["evidence_copy"]
        if has_finance_material(str(path)):
            hits.append(item["evidence_copy"])
            continue
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")[:MAX_TEXT_SCAN_BYTES]
        except OSError:
            continue
        if has_finance_material(text):
            hits.append(item["evidence_copy"])
    return hits


def high_risk_name_hits(copied: list[dict[str, Any]]) -> list[str]:
    hits: list[str] = []
    for item in copied:
        name = Path(item["evidence_copy"]).name.lower()
        if any(term in name for term in EXCLUDED_NAME_TERMS):
            hits.append(item["evidence_copy"])
    return hits


def main() -> None:
    run_time = now_local()
    date_prefix = run_time.strftime("%Y%m%d")
    run_stamp = run_time.strftime("%Y%m%d_%H%M%S")
    scan_roots = fixed_drive_roots()
    evidence_dir = APPLICATIONS_DIR / f"gary_aureon_metadata_research_evidence_{date_prefix}_{run_stamp}"

    inventory, scan_stats = iter_candidate_items(scan_roots)
    copied, not_copied = copy_selected(inventory, evidence_dir)
    secret_hits = copied_secret_scan(copied)
    sensitive_hits = copied_sensitive_scan(copied)
    finance_hits = copied_finance_scan(copied)
    high_risk_hits = high_risk_name_hits(copied)

    theme_counts: dict[str, int] = {}
    priority_counts: dict[str, int] = {}
    for item in inventory:
        theme_counts[item["theme"]] = theme_counts.get(item["theme"], 0) + 1
        priority_counts[item["priority"]] = priority_counts.get(item["priority"], 0) + 1

    artifact_rel = f"applications/GARY_AUREON_METADATA_RESEARCH_INVENTORY_{date_prefix}_{run_stamp}.json"
    md_rel = f"applications/GARY_AUREON_METADATA_RESEARCH_INVENTORY_{date_prefix}_{run_stamp}.md"
    csv_rel = f"applications/GARY_AUREON_METADATA_RESEARCH_INVENTORY_{date_prefix}_{run_stamp}.csv"
    report_rel = f"pipelines/pipeline_report_{date_prefix}_{run_stamp}_gary_aureon_metadata_research_inventory.json"
    copy_manifest_rel = f"applications/gary_aureon_metadata_research_evidence_{date_prefix}_{run_stamp}/COPY_MANIFEST.json"

    summary = {
        "scan_roots_found": len(scan_roots),
        "files_seen": scan_stats["files_seen"],
        "allowed_files_seen": scan_stats["allowed_files_seen"],
        "raw_candidate_files": scan_stats["raw_candidate_files"],
        "unique_candidate_files": scan_stats["unique_candidate_files"],
        "evidence_copies_created": len(copied),
        "evidence_copy_bytes": sum(int(item["size_bytes"]) for item in copied),
        "not_copied_due_to_limits": len(not_copied),
        "duplicate_hashes": scan_stats["duplicate_hashes"],
        "duplicate_paths": scan_stats["duplicate_paths"],
        "secret_pattern_files_copied": bool(secret_hits),
        "sensitive_pattern_files_copied": bool(sensitive_hits),
        "finance_pattern_files_copied": bool(finance_hits),
        "high_risk_named_files_copied": bool(high_risk_hits),
        "external_submission_performed": False,
        "email_sent": False,
        "portal_changed": False,
    }

    receipt = {
        "schema_version": "aureon-gary-metadata-research-inventory-v1",
        "generated_at": run_time.isoformat(),
        "operator": "Aureon",
        "mode": "LOCAL_DISK_GARY_AUREON_METADATA_RESEARCH_GATHERING",
        "event": "gary_aureon_metadata_research_inventory",
        "result": RESULT,
        "scan_roots": [str(path) for path in scan_roots],
        "evidence_copy_dir": rel_grants(evidence_dir),
        "inventory": inventory,
        "copied_evidence": copied,
        "not_copied": not_copied,
        "scan_stats": scan_stats,
        "theme_counts": theme_counts,
        "priority_counts": priority_counts,
        "summary": summary,
        "validation": {
            "secret_pattern_hits_in_copied_text_files": secret_hits,
            "sensitive_pattern_hits_in_copied_text_files": sensitive_hits,
            "finance_pattern_hits_in_copied_text_files": finance_hits,
            "high_risk_name_hits_in_copied_files": high_risk_hits,
        },
        "controls": [
            "All fixed local filesystem roots were considered; system, cache, dependency, credential, and private key locations were pruned.",
            "Financial, accounting, credential, token, password, env-style, legal/court, and personal CV/resume-like files were excluded from copying.",
            "Copied files are evidence copies for Gary/Aureon company metadata and research packaging; original files were not moved or modified.",
            "Local research and metadata artifacts are claim-supporting material only and need separate verification before use as independent validation, legal, finance, partner, or award evidence.",
            "No email, portal mutation, provider bypass, live grant submission, or external filing action was performed.",
        ],
    }

    write_json(GRANTS / artifact_rel, receipt)
    write_text(GRANTS / md_rel, render_markdown(receipt))
    write_csv(GRANTS / csv_rel, inventory)
    write_json(GRANTS / copy_manifest_rel, copied)

    report = {
        "schema_version": "aureon-pipeline-report-v1",
        "generated_at": run_time.isoformat(),
        "operator": "Aureon",
        "mode": "LOCAL_DISK_GARY_AUREON_METADATA_RESEARCH_GATHERING",
        "event": "gary_aureon_metadata_research_inventory",
        "artifact": artifact_rel,
        "markdown": md_rel,
        "csv": csv_rel,
        "copy_manifest": copy_manifest_rel,
        "evidence_copy_dir": rel_grants(evidence_dir),
        "report": report_rel,
        "result": RESULT,
        **summary,
        "theme_counts": theme_counts,
        "priority_counts": priority_counts,
    }
    write_json(GRANTS / report_rel, report)

    update = {
        "last_gary_aureon_metadata_research_inventory_at": run_time.isoformat(),
        "last_gary_aureon_metadata_research_inventory_artifact": artifact_rel,
        "last_gary_aureon_metadata_research_inventory_result": RESULT,
        "gary_aureon_metadata_research_unique_latest": len(inventory),
        "gary_aureon_metadata_research_evidence_copies_latest": len(copied),
        "gary_aureon_metadata_research_duplicate_hashes_latest": scan_stats["duplicate_hashes"],
    }
    pipeline = load_json(PIPELINE_JSON, {})
    autopilot = load_json(AUTOPILOT_JSON, {})
    pipeline["last_gary_aureon_metadata_research_inventory"] = report
    pipeline.update(update)
    pipeline.setdefault("summary", {}).update(update)
    pipeline["last_updated"] = run_time.isoformat()
    pipeline["generated_at"] = run_time.isoformat()
    write_json(PIPELINE_JSON, pipeline)

    autopilot["last_gary_aureon_metadata_research_inventory"] = report
    autopilot.update(update)
    autopilot["updated_at"] = run_time.isoformat()
    write_json(AUTOPILOT_JSON, autopilot)

    activity = {
        "timestamp": run_time.isoformat(),
        "event": "gary_aureon_metadata_research_inventory",
        "result": RESULT,
        "artifact": artifact_rel,
        "markdown": md_rel,
        "csv": csv_rel,
        "pipeline_report": report_rel,
        **summary,
    }
    with ACTIVITY_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(activity, ensure_ascii=True) + "\n")

    validation = {
        "artifact_exists": (GRANTS / artifact_rel).exists(),
        "markdown_exists": (GRANTS / md_rel).exists(),
        "csv_exists": (GRANTS / csv_rel).exists(),
        "copy_manifest_exists": (GRANTS / copy_manifest_rel).exists(),
        "copied_files_exist": all((GRANTS / item["evidence_copy"]).exists() for item in copied),
        "pipeline_result": load_json(PIPELINE_JSON, {}).get("summary", {}).get("last_gary_aureon_metadata_research_inventory_result"),
        "autopilot_result": load_json(AUTOPILOT_JSON, {}).get("last_gary_aureon_metadata_research_inventory_result"),
        "secret_pattern_hits_in_copied_text_files": secret_hits,
        "sensitive_pattern_hits_in_copied_text_files": sensitive_hits,
        "finance_pattern_hits_in_copied_text_files": finance_hits,
        "high_risk_name_hits_in_copied_files": high_risk_hits,
        "unique_candidate_files": len(inventory),
        "evidence_copies_created": len(copied),
    }
    print(json.dumps({"report": report, "validation": validation}, indent=2))


if __name__ == "__main__":
    main()
