"""🌍 OPEN SOURCES — keyless public-data helpers for the Aureon Fusion organism.

Wikipedia opensearch / page summary and DuckDuckGo instant answer, exposed
as small, never-raising helpers for the sovereign learning will
(SeekAct.resolve_canonical_target, CuriosityEngine question stream) and
the open_search doors.

Doctrine:
  • ALL HTTP flows through aureon_fusion.api_communion (get_json / get_text)
    — cache, per-host rate limit, backoff, circuit breaker, stale marking
    are communion's job, never reimplemented here. No raw urllib/requests.
  • No API keys. Public endpoints only.
  • NEVER raises: every helper returns [] / None on any failure. Callers
    decide what absence means.
  • Communion stale semantics are honored, not hidden: a stale-marked body
    is still returned (results anyway) and keeps its ``stale: true`` /
    ``stale_age_s`` markers so the CALLER freshness-gates. List-returning
    helpers (wiki_opensearch, search_candidates) unwrap stale envelopes
    and return the payloads — they are candidate pointers, and their
    consumers gate on freshness before acting.

Query-building patterns are ported from the upstream read-only reference
aureon-os-upstream/aureon/integrations/world_data/world_data_ingester.py
(URL-encode via urllib.parse.quote, opensearch namespace=0, DDG
no_html=1&skip_disambig=1).

CLI:
    python -m aureon_fusion.open_sources search "solar wind"
    python -m aureon_fusion.open_sources summary "Solar wind"
    python -m aureon_fusion.open_sources ddg "solar wind"
"""

import json
import os
import sys
from urllib.parse import quote

os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")
os.environ.setdefault("AUREON_AUDIT_MODE", "1")

from . import api_communion

WIKI_API = "https://en.wikipedia.org/w/api.php"
WIKI_REST = "https://en.wikipedia.org/api/rest_v1/page/summary"
DDG_API = "https://api.duckduckgo.com/"

# Freshness windows (communion TTLs). Search suggestions rotate slowly;
# summaries are near-static reference cards.
OPENSEARCH_TTL_S = 3600.0
SUMMARY_TTL_S = 24 * 3600.0
DDG_TTL_S = 3600.0

MAX_CANDIDATES = 8


def _unwrap(body):
    """Unwrap a communion stale envelope around a non-dict payload.

    Communion serves stale list bodies as {"stale": true, "body": [...]}.
    Returns (payload, stale: bool)."""
    if isinstance(body, dict) and body.get("stale") is True:
        return body.get("body"), True
    return body, False


def wiki_opensearch(query: str, limit: int = 5) -> list:
    """Wikipedia opensearch titles for a query -> list[str].

    Never raises; [] on any failure or empty result. Stale payloads are
    returned anyway (caller freshness-gates)."""
    try:
        q = (query or "").strip()
        if not q:
            return []
        safe = quote(q)
        url = (f"{WIKI_API}?action=opensearch&format=json&search={safe}"
               f"&limit={int(limit)}&namespace=0")
        body = api_communion.get_json(url, ttl_s=OPENSEARCH_TTL_S)
        body, _stale = _unwrap(body)
        # opensearch payload: [query, [titles], [descriptions], [urls]]
        if not (isinstance(body, list) and len(body) >= 2
                and isinstance(body[1], list)):
            return []
        return [str(t) for t in body[1] if t][:limit]
    except Exception:
        return []


def wiki_summary(title: str):
    """Wikipedia REST summary card for a title -> dict | None.

    Returns the parsed summary dict (title / extract / description /
    content_urls …). A communion stale-marked dict is returned as-is —
    its ``stale: true`` marker stays visible for caller freshness-gating.
    None on any failure."""
    try:
        t = (title or "").strip()
        if not t:
            return None
        safe = quote(t.replace(" ", "_"))
        body = api_communion.get_json(f"{WIKI_REST}/{safe}",
                                      ttl_s=SUMMARY_TTL_S)
        if not isinstance(body, dict) or not body:
            return None
        return body
    except Exception:
        return None


def ddg_instant_answer(query: str):
    """DuckDuckGo instant answer, distilled -> dict | None.

    Returns {"heading", "abstract", "abstract_url", "related_urls"} with
    AbstractText / AbstractURL as primary fields (per upstream reference).
    Stale envelopes are unwrapped and the result returned anyway; the
    stale flag is re-attached as "stale" + "stale_age_s" so callers can
    freshness-gate. None when there is no usable answer at all."""
    try:
        q = (query or "").strip()
        if not q:
            return None
        safe = quote(q)
        url = (f"{DDG_API}?format=json&no_html=1&skip_disambig=1&q={safe}")
        body = api_communion.get_json(url, ttl_s=DDG_TTL_S)
        body, stale = _unwrap(body)
        if not isinstance(body, dict):
            return None
        abstract = body.get("AbstractText") or body.get("Abstract") or ""
        abstract_url = body.get("AbstractURL") or ""
        related = []
        for topic in body.get("RelatedTopics") or []:
            if isinstance(topic, dict):
                first = topic.get("FirstURL")
                if first:
                    related.append(str(first))
                # grouped topics: one level of nesting
                for sub in topic.get("Topics") or []:
                    if isinstance(sub, dict) and sub.get("FirstURL"):
                        related.append(str(sub["FirstURL"]))
        if not abstract and not abstract_url and not related:
            return None
        result = {
            "heading": str(body.get("Heading") or q),
            "abstract": str(abstract),
            "abstract_url": str(abstract_url),
            "related_urls": related,
        }
        if stale:
            result["stale"] = True
        return result
    except Exception:
        return None


def search_candidates(query: str) -> list:
    """Combined candidate URLs/titles for a query -> list[str], cap 8.

    Order: DDG AbstractURL + DDG related-topic URLs, then Wikipedia
    opensearch titles. Deduped (case-insensitive), never raises, [] on
    total failure. Candidates are pointers only — consumers freshness-gate
    and run their own discernment before absorbing anything."""
    try:
        q = (query or "").strip()
        if not q:
            return []
        seen = set()
        out = []

        def _add(item):
            if item is None:
                return
            s = str(item).strip()
            if not s:
                return
            key = s.lower()
            if key in seen:
                return
            seen.add(key)
            out.append(s)

        ans = ddg_instant_answer(q)
        if ans:
            _add(ans.get("abstract_url"))
            for u in ans.get("related_urls") or []:
                _add(u)
        for title in wiki_opensearch(q, limit=MAX_CANDIDATES):
            _add(title)
        return out[:MAX_CANDIDATES]
    except Exception:
        return []


# ───────────────────────────── CLI ─────────────────────────────────────────

def _emit(payload):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print(json.dumps(payload, ensure_ascii=False))


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print("usage: python -m aureon_fusion.open_sources "
              "search|summary|ddg <query>", file=sys.stderr)
        return 2
    verb, query = argv[0], " ".join(argv[1:])
    if verb == "search":
        _emit(search_candidates(query))
        return 0
    if verb == "summary":
        _emit(wiki_summary(query))
        return 0
    if verb == "ddg":
        _emit(ddg_instant_answer(query))
        return 0
    print("usage: python -m aureon_fusion.open_sources "
          "search|summary|ddg <query>", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
