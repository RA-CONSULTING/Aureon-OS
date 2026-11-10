"""Diagnosis records and opt-in read-only web research for the Queen's repair loop.

diagnose() turns the suite output into one record per failing test: test id,
error line, traceback tail and the suspected implementation file. The records
go to state/queen_repair_diagnosis.json and into the repair report, which the
trader's loop relays on the bus.

research() is off unless AUREON_QUEEN_REPAIR_WEB=1. It sends a GET for each
failure's exception text (paths, long tokens and any secret value removed) to a
public search page, fetches the top results with a timeout and a size cap, and
logs every URL to state/queen_repair_research.jsonl. That log is also the
cache. It never sends headers beyond a user agent, never sends a body, never
reads /home/box/quarantine_env, and drops any query or URL that contains a
secret value from the environment or the repo's .env.
"""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable

WEB_ENV = "AUREON_QUEEN_REPAIR_WEB"
DIAGNOSIS_PATH = Path("state/queen_repair_diagnosis.json")
RESEARCH_LOG = Path("state/queen_repair_research.jsonl")
MAX_BYTES = 256 * 1024
TIMEOUT_S = 10.0
MAX_FAILURES = 5
MAX_PAGES = 2
CACHE_TTL_S = 24 * 3600
USER_AGENT = "Aureon-Queen-Repair-Research/1.0 (read-only)"
SEARCH_URL = "https://html.duckduckgo.com/html/?q="
# Fallback when the search page answers with a bot check: Stack Overflow's public read API.
STACK_URL = ("https://api.stackexchange.com/2.3/search/advanced?order=desc&sort=relevance"
             "&site=stackoverflow&pagesize=3&q=")
STACK_ANSWERS = ("https://api.stackexchange.com/2.3/questions/{}/answers?order=desc&sort=votes"
                 "&site=stackoverflow&filter=withbody&pagesize=2")
_SECRET_NAME = re.compile(r"KEY|SECRET|TOKEN|PASS|PRIVATE|CREDENTIAL|AUTH|COOKIE|SESSION", re.I)


def web_enabled() -> bool:
    return os.environ.get(WEB_ENV, "").strip() == "1"


# ---------------------------------------------------------------- diagnosis
def _sections(output: str) -> dict[str, list[str]]:
    """Split pytest's FAILURES/ERRORS body into per-test sections.

    pytest pads a failure header with a variable number of underscores
    (``____ name ____`` and, when the name is long or the terminal narrow,
    ``_ name _``). Match one or more underscores on each side so a
    parametrised or long test id is captured, not dropped.
    """
    sections: dict[str, list[str]] = {}
    current: list[str] | None = None
    for line in output.splitlines():
        head = re.match(r"^_+ (.+?) _+$", line.rstrip())
        if head and set(line.strip()) - set("_ "):  # a real header, not a rule of underscores
            current = sections.setdefault(head.group(1).strip(), [])
            continue
        if re.match(r"^={5,}", line):
            current = None
            continue
        if current is not None:
            current.append(line)
    return sections


def _suspect(root: Path, lines: list[str]) -> str:
    paths = []
    for line in lines:
        match = re.match(r"^(?:E\s+)?(?:File \")?([^\s\"]+?\.py)\"?(?::|, line )\d+", line.strip())
        if match:
            paths.append(match.group(1))
    root = root.resolve()
    for raw in reversed(paths):
        candidate = Path(raw) if Path(raw).is_absolute() else root / raw
        try:
            rel = candidate.resolve().relative_to(root).as_posix()
        except (ValueError, OSError):
            continue
        name = Path(rel).name
        if not (name.startswith("test_") or rel.startswith("tests/") or name == "conftest.py"):
            return rel
    return paths[-1] if paths else ""


def diagnose(root: Path, output: str) -> list[dict[str, Any]]:
    """One record per FAILED/ERROR line in pytest's short summary."""
    summary = re.findall(r"^(FAILED|ERROR)\s+(\S+)(?:\s+-\s+(.*))?$", output or "", re.MULTILINE)
    sections = _sections(output or "")
    records = []
    for outcome, nodeid, message in summary:
        tail_name = nodeid.split("::")[-1]
        lines: list[str] = []
        for title, body in sections.items():
            if title == tail_name or title.endswith("." + tail_name) or (outcome == "ERROR" and nodeid.split("::")[0] in title):
                lines = body
                break
        errors = [ln[1:].strip() for ln in lines if ln.startswith("E ")]
        exc_lines = [e for e in errors if re.match(r"^[A-Za-z_][\w.]*(?:Error|Exception|Exit)\b", e)]
        nonblank = [ln.strip() for ln in lines if ln.strip()]
        error = (
            (message or "").strip()
            or (exc_lines[-1] if exc_lines else "")
            or (errors[-1] if errors else "")
            or (nonblank[-1] if nonblank else "")
        )
        exc = re.match(r"^([A-Za-z_][\w.]*(?:Error|Exception|Exit|Warning|Interrupt))\b", error)
        records.append({
            "test_id": nodeid,
            "outcome": outcome.lower(),
            "error": error[:500],
            "exception": exc.group(1) if exc else ("AssertionError" if error.startswith("assert") else ""),
            "traceback_tail": [ln[:300] for ln in lines[-15:]],
            "suspected_file": _suspect(root, lines),
        })
    return records


def write_diagnosis(root: Path, records: list[dict[str, Any]], research: list[dict[str, Any]] | None = None) -> Path:
    path = root / DIAGNOSIS_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"ts": time.time(), "failures": len(records), "records": records,
               "web_research": web_enabled(), "research": research or []}
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=1, default=str), encoding="utf-8")
    os.replace(tmp, path)
    return path


def compact(records: list[dict[str, Any]], limit: int = 8) -> list[dict[str, str]]:
    return [{"test": r["test_id"][:160], "error": r["error"][:160], "file": r["suspected_file"]} for r in records[:limit]]


# ---------------------------------------------------------------- secrets
def _secret_values(root: Path) -> list[str]:
    values = [v for k, v in os.environ.items() if _SECRET_NAME.search(k) and len(v or "") >= 6]
    env_file = root / ".env"
    try:
        for line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                value = line.split("=", 1)[1].strip().strip("'\"")
                if len(value) >= 6:
                    values.append(value)
    except OSError:
        pass
    return values


def redact_query(text: str) -> str:
    text = re.sub(r"(?:[A-Za-z]:)?(?:/[\w.\-]+)+/?", " ", text or "")       # paths
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"\S+@\S+", " ", text)                                      # emails
    text = re.sub(r"\b[0-9a-fA-F]{16,}\b", " ", text)                         # hashes, ids
    text = re.sub(r"[A-Za-z0-9+/_\-]{24,}={0,2}", " ", text)                  # token-like strings
    text = re.sub(r"\b0x[0-9a-fA-F]+\b", " ", text)
    return re.sub(r"\s+", " ", text).strip()[:180]


def is_safe(text: str, secrets: list[str]) -> bool:
    if "quarantine_env" in text:
        return False
    return not any(secret in text for secret in secrets)


# ---------------------------------------------------------------- fetching
def _get(url: str) -> dict[str, Any]:
    if urllib.parse.urlparse(url).scheme not in {"http", "https"}:
        return {"ok": False, "error": "scheme_refused"}
    request = urllib.request.Request(url, method="GET", headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*"})
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
            body = response.read(MAX_BYTES + 1)
            if body[:2] == b"\x1f\x8b":  # the Stack Exchange API always gzips
                import zlib
                body = zlib.decompressobj(16 + zlib.MAX_WBITS).decompress(body, MAX_BYTES + 1)
            status = getattr(response, "status", 200)
            return {"ok": status == 200, "status": status, "truncated": len(body) > MAX_BYTES,
                    "text": body[:MAX_BYTES].decode("utf-8", errors="replace"),
                    "ms": round((time.time() - started) * 1000)}
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"[:200], "ms": round((time.time() - started) * 1000)}


def _visible_text(markup: str) -> str:
    if markup.lstrip().startswith("{"):  # Stack Exchange API answers
        try:
            markup = " ".join(str(item.get("body", "")) for item in json.loads(markup).get("items", []))
        except ValueError:
            pass
    try:  # reuse the research-cinema extractor when bs4 is there
        from aureon.search.online_research_cinema import _extract_visible_text
        return _extract_visible_text(markup)["text"]
    except Exception:
        markup = re.sub(r"(?is)<(script|style).*?</\1>", " ", markup)
        return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", markup))).strip()


def _summary(text: str, topic: str) -> str:
    try:
        from aureon.search.online_research_cinema import summarize_text
        return summarize_text(text, topic)[:600]
    except Exception:
        return text[:600]


def _result_urls(markup: str, limit: int) -> list[str]:
    urls = []
    for href in re.findall(r'class="result__a"[^>]*href="([^"]+)"|href="([^"]+)"[^>]*class="result__a"', markup):
        href = html.unescape(href[0] or href[1])
        if "duckduckgo.com/l/" in href:
            href = urllib.parse.parse_qs(urllib.parse.urlparse(href).query).get("uddg", [""])[0]
        if href.startswith("http") and "duckduckgo.com" not in href and href not in urls:
            urls.append(href)
        if len(urls) >= limit:
            break
    return urls


def _stack_urls(text: str, limit: int) -> list[str]:
    try:
        items = json.loads(text).get("items", [])
    except ValueError:
        return []
    # stackoverflow.com pages refuse scripted reads, so read the top-voted answers through the same API
    return [STACK_ANSWERS.format(int(item["question_id"])) for item in items if item.get("question_id")][:limit]


def _cached(log: Path) -> dict[str, dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    try:
        for line in log.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if row.get("ok") and time.time() - float(row.get("ts", 0)) < CACHE_TTL_S:
                seen[row["url"]] = row
    except (OSError, ValueError):
        pass
    return seen


def research(root: Path, records: list[dict[str, Any]], *, fetch: Callable[[str], dict[str, Any]] | None = None
             ) -> list[dict[str, Any]]:
    """Read-only lookups for each failure. Returns findings; [] when not opted in."""
    if not web_enabled() or not records:
        return []
    fetch = fetch or _get
    log = root / RESEARCH_LOG
    log.parent.mkdir(parents=True, exist_ok=True)
    cache = _cached(log)
    secrets = _secret_values(root)
    findings = []
    asked: set[str] = set()

    def logged(url: str, test_id: str, kind: str, post: Callable[[str], dict[str, Any]]) -> dict[str, Any]:
        if url in cache:
            row = dict(cache[url], cached=True, test_id=test_id, ts=time.time())
        else:
            got = fetch(url)
            text = got.get("text", "")
            row = {"ts": time.time(), "test_id": test_id, "kind": kind, "url": url, "ok": bool(got.get("ok")),
                   "status": got.get("status"), "bytes": len(text), "truncated": got.get("truncated", False),
                   "error": got.get("error"), "sha256": hashlib.sha256(text.encode()).hexdigest() if text else None,
                   "cached": False, **(post(text) if got.get("ok") else {})}
            cache[url] = row
        with log.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, default=str) + "\n")
        return row

    for record in records[:MAX_FAILURES]:
        query = redact_query(f"python {record.get('error') or record.get('exception')}")
        if not query or query in asked:
            continue
        asked.add(query)
        search_url = SEARCH_URL + urllib.parse.quote_plus(query)
        if not is_safe(query, secrets) or not is_safe(search_url, secrets):
            with log.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({"ts": time.time(), "test_id": record["test_id"], "kind": "search",
                                     "url": None, "ok": False, "error": "blocked_secret_in_query"}) + "\n")
            continue
        search = logged(search_url, record["test_id"], "search", lambda text: {"results": _result_urls(text, MAX_PAGES)})
        results = search.get("results") or []
        if not results:
            stack_url = STACK_URL + urllib.parse.quote_plus(query)
            results = logged(stack_url, record["test_id"], "search",
                             lambda text: {"results": _stack_urls(text, MAX_PAGES)}).get("results") or []
        sources = []
        for url in results:
            if not is_safe(url, secrets):
                continue
            page = logged(url, record["test_id"], "page",
                          lambda text: {"summary": _summary(_visible_text(text), query)})
            sources.append({"url": url, "ok": page.get("ok"), "summary": page.get("summary", "")})
        findings.append({"test_id": record["test_id"], "query": query, "sources": sources})
    return findings


def hinted_names(record: dict[str, Any], findings: list[dict[str, Any]]) -> list[str]:
    """Identifiers the error text or the research names as the intended one ("Did you mean: 'x'?")."""
    texts = [record.get("error", ""), *record.get("traceback_tail", [])]
    texts += [s.get("summary", "") for f in findings if f.get("test_id") == record.get("test_id") for s in f.get("sources", [])]
    names: list[str] = []
    for text in texts:
        for name in re.findall(r"[Dd]id you mean:? '([A-Za-z_]\w*)'", text or ""):
            if name not in names:
                names.append(name)
    return names
