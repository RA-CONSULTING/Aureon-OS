"""🔬 RESEARCH INGESTER — communion-routed port of the upstream WorldDataIngester
fetch patterns for the Queen's research faculty.

Ported from the READ-ONLY upstream reference
aureon-os-upstream/aureon/integrations/world_data/world_data_ingester.py
(keyless public feeds: Hacker News, Reddit JSON, Yahoo Finance, Wikipedia,
USGS earthquakes, Open-Meteo, arXiv, CoinGecko).

Doctrine:
  • ALL HTTP flows through aureon_fusion.api_communion (get_json / get_text)
    — cache, per-host rate limit, backoff, circuit breaker, stale marking
    are communion's job, never reimplemented here. NO raw urllib/requests.
  • No API keys. Public endpoints only.
  • NEVER raises: every fetcher returns [] / None on any failure. Callers
    decide what absence means.
  • Normalized ResearchItem: {source, topic, title, text, url, summary,
    fetched_at, category, raw} with attribute access (the upstream
    SelfResearchLoop reads item.source/.title/.text/.category) and
    to_dict() for JSON surfaces.
  • Wikipedia reuses aureon_fusion.open_sources (opensearch / summary)
    where it fits — one query-building port, not two.

CLI:
  python -m aureon_fusion.research_ingester probe   # one keyless item per
                                                     # source (incl. gdelt /
                                                     # open_library / wikidata /
                                                     # pubmed / rss), JSON report
"""

from __future__ import annotations

import math
import os
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import quote

os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")
os.environ.setdefault("AUREON_AUDIT_MODE", "1")

from . import api_communion
from . import open_sources

logger_src = "research_ingester"

# Freshness windows (communion TTLs). Trending lists rotate fast; reference
# cards (wiki summaries) are near-static.
TTL_TRENDING_S = 900.0
TTL_QUOTE_S = 600.0
TTL_WEATHER_S = 1800.0
TTL_WIKI_SUMMARY_S = 24 * 3600.0


# ─────────────────────────────────────────────────────────────────────────────
# Normalized item
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class ResearchItem:
    """One normalized external observation.

    Field-for-field compatible with what the upstream SelfResearchLoop and
    stash-pocket flow read off a WorldDataItem (source/title/text/url/
    category), plus explicit provenance (fetched_at) and the normalized
    `summary` the fusion faculty reports on."""

    source: str
    topic: str
    title: str
    text: str
    url: str = ""
    summary: str = ""
    fetched_at: float = field(default_factory=time.time)
    category: str = "knowledge"
    raw: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────


def _unwrap(body: Any):
    """Unwrap a communion stale envelope around a non-dict payload.

    Communion serves stale list bodies as {"stale": true, "body": [...]}.
    Returns (payload, stale: bool)."""
    if isinstance(body, dict) and body.get("stale") is True:
        return body.get("body"), True
    return body, False


def _iso(ts: float) -> str:
    try:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(float(ts)))
    except Exception:
        return ""


def _s(value: Any, limit: int = 0) -> str:
    """Defensively coerce to a clean single-line string."""
    try:
        out = " ".join(str(value or "").split())
        return out[:limit] if limit > 0 else out
    except Exception:
        return ""


class ResearchIngester:
    """Communion-routed replacement for the upstream WorldDataIngester.

    Same public fetch surface the upstream SelfResearchLoop calls
    (answer_question / fetch_hacker_news / fetch_reddit /
    fetch_yahoo_quote / ingest_to_vault), backed entirely by
    api_communion. ingest_to_vault is a counted no-op: the fusion organism
    has no upstream vault — crystallization happens through the research
    faculty's stash-pocket adapter into knowledge_dataset.json."""

    USER_AGENT = "AureonFusion-ResearchIngester/1.0 (SENSE-layer; communion-routed)"

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
        self.stats: Dict[str, Any] = {
            "items_pulled": 0,
            "vault_ingests": 0,
            "errors": 0,
        }
        # value-string -> ResearchItem, so the faculty's stash-pocket adapter
        # can recover full provenance (url + fetched_at) for every dump the
        # research loop makes (it passes f"{item.title}: {item.text}").
        self._by_value: Dict[str, ResearchItem] = {}

    # ── registration / provenance recovery ─────────────────────────────
    def _register(self, item: ResearchItem) -> ResearchItem:
        try:
            self._by_value[f"{item.title}: {item.text}"] = item
            while len(self._by_value) > 500:
                self._by_value.pop(next(iter(self._by_value)))
            self.stats["items_pulled"] += 1
        except Exception:
            pass
        return item

    def provenance_for(self, value: str) -> Optional[ResearchItem]:
        """Recover the ResearchItem behind a loop dump value, if known."""
        try:
            return self._by_value.get(str(value or ""))
        except Exception:
            return None

    # ── vault stand-in (fusion has none — count honestly) ──────────────
    def ingest_to_vault(self, items: List[Any]) -> int:
        """The fusion organism persists research via knowledge_dataset
        crystallization, not the upstream vault. Counts the batch so the
        flow stays observable; returns the number of items seen."""
        try:
            n = len(list(items or []))
            self.stats["vault_ingests"] += 1
            return n
        except Exception:
            return 0

    # ─────────────────────────────────────────────────────────────────
    # Hacker News (no key)
    # ─────────────────────────────────────────────────────────────────
    def fetch_hacker_news(self, n: int = 5) -> List[ResearchItem]:
        """Top stories from Hacker News."""
        try:
            ids, _ = _unwrap(api_communion.get_json(
                "https://hacker-news.firebaseio.com/v0/topstories.json",
                ttl_s=TTL_TRENDING_S, timeout=self.timeout))
            if not isinstance(ids, list) or not ids:
                return []
            items: List[ResearchItem] = []
            for sid in ids[: max(1, int(n))]:
                try:
                    story, _ = _unwrap(api_communion.get_json(
                        f"https://hacker-news.firebaseio.com/v0/item/{sid}.json",
                        ttl_s=TTL_TRENDING_S, timeout=self.timeout))
                    if not isinstance(story, dict) or not story.get("title"):
                        continue
                    title = _s(story.get("title"))
                    items.append(self._register(ResearchItem(
                        source="hacker_news",
                        topic="top",
                        title=title,
                        text=f"{title} — {story.get('score', 0)} points",
                        url=_s(story.get("url")) or
                            f"https://news.ycombinator.com/item?id={sid}",
                        summary=f"Hacker News top story: {title}",
                        category="knowledge",
                        raw={"score": story.get("score", 0),
                             "by": _s(story.get("by"))},
                    )))
                except Exception:
                    self.stats["errors"] += 1
                    continue
            return items
        except Exception:
            self.stats["errors"] += 1
            return []

    # Browser-like identity for hosts that 403/429 the communion UA
    # (reddit is the known case — the JSON API demands a real UA).
    BROWSER_HEADERS = {
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/126.0.0.0 Safari/537.36"),
        "Accept": "application/json",
    }
    BROWSER_HEADERS_XML = {
        "User-Agent": BROWSER_HEADERS["User-Agent"],
        "Accept": "application/rss+xml, text/xml, */*",
    }

    # ─────────────────────────────────────────────────────────────────
    # Reddit JSON (no key) — 3-deep graceful degradation
    # ─────────────────────────────────────────────────────────────────
    def _reddit_category(self, sub: str) -> str:
        sub_lower = _s(sub).lower()
        if any(w in sub_lower for w in ("news", "politic", "geopolitic")):
            return "user_input"          # external world events
        if any(w in sub_lower for w in ("crypto", "bitcoin", "market")):
            return "market"
        return "knowledge"

    def _reddit_from_children(self, children: Any, sub: str, n: int,
                              via: str) -> List[ResearchItem]:
        """Normalize listing JSON children into items (shared by tiers 1-2)."""
        items: List[ResearchItem] = []
        category = self._reddit_category(sub)
        if not isinstance(children, list):
            return items
        for c in children[: max(1, int(n))]:
            try:
                post = (c or {}).get("data", {}) if isinstance(c, dict) else {}
                title = _s(post.get("title"))
                if not title:
                    continue
                permalink = _s(post.get("permalink"))
                items.append(self._register(ResearchItem(
                    source=f"reddit_r/{sub}",
                    topic=sub,
                    title=title,
                    text=f"{title} — {_s(post.get('selftext'), 300)}",
                    url=f"https://reddit.com{permalink}" if permalink else "",
                    summary=f"r/{sub}: {title}",
                    category=category,
                    raw={"score": post.get("score", 0),
                         "num_comments": post.get("num_comments", 0),
                         "via": via},
                )))
            except Exception:
                self.stats["errors"] += 1
                continue
        return items

    def _reddit_from_rss(self, body: Any, sub: str, n: int) -> List[ResearchItem]:
        """Tier 3: parse an RSS document into items (title/link/description)."""
        items: List[ResearchItem] = []
        if isinstance(body, dict):              # communion stale envelope
            body = body.get("body")
        if not isinstance(body, str) or "<item" not in body:
            return items
        import re as _re
        category = self._reddit_category(sub)
        blocks = _re.findall(r"<item[^>]*>(.*?)</item>", body,
                             _re.DOTALL | _re.IGNORECASE)

        def _field(block: str, tag: str) -> str:
            m = _re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", block,
                           _re.DOTALL | _re.IGNORECASE)
            if not m:
                return ""
            val = _re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", m.group(1),
                          flags=_re.DOTALL)
            val = _re.sub(r"<[^>]+>", " ", val)
            return _s(val, 400)

        for block in blocks[: max(1, int(n))]:
            try:
                title = _field(block, "title")
                if not title:
                    continue
                link = _field(block, "link")
                desc = _field(block, "description")
                items.append(self._register(ResearchItem(
                    source=f"reddit_r/{sub}",
                    topic=sub,
                    title=title,
                    text=f"{title} — {desc}" if desc else title,
                    url=link,
                    summary=f"r/{sub} (rss): {title}",
                    category=category,
                    raw={"via": "rss"},
                )))
            except Exception:
                self.stats["errors"] += 1
                continue
        return items

    def fetch_reddit(self, subreddit: str = "worldnews", n: int = 5,
                     sort: str = "top") -> List[ResearchItem]:
        """Top posts from a subreddit (worldnews / geopolitics / …).

        Graceful degradation, 3 deep — every tier is isolated, one dead
        endpoint never sinks the rest:
          1. www.reddit.com/r/<sub>/<sort>.json with a browser-like UA
             (the plain communion UA is 403'd by the JSON API);
          2. old.reddit.com/r/<sub>/.json (the legacy host, same shape);
          3. www.reddit.com/r/<sub>/.rss via get_text + item regex
             (the feed ignores client identity)."""
        try:
            sub = _s(subreddit) or "worldnews"
            sort = _s(sort) or "top"
            limit = max(1, int(n))

            # Tier 1 — modern JSON with browser identity
            try:
                data, _ = _unwrap(api_communion.get_json(
                    f"https://www.reddit.com/r/{quote(sub)}/{quote(sort)}.json"
                    f"?limit={limit}&t=day",
                    ttl_s=TTL_TRENDING_S, timeout=self.timeout,
                    headers=self.BROWSER_HEADERS))
                children = (data or {}).get("data", {}).get("children", []) \
                    if isinstance(data, dict) else []
                items = self._reddit_from_children(children, sub, limit,
                                                   via="json")
                if items:
                    return items
            except Exception:
                self.stats["errors"] += 1

            # Tier 2 — legacy host JSON (top listing only; it has no ?t=)
            try:
                data, _ = _unwrap(api_communion.get_json(
                    f"https://old.reddit.com/r/{quote(sub)}/.json?limit={limit}",
                    ttl_s=TTL_TRENDING_S, timeout=self.timeout,
                    headers=self.BROWSER_HEADERS))
                children = (data or {}).get("data", {}).get("children", []) \
                    if isinstance(data, dict) else []
                items = self._reddit_from_children(children, sub, limit,
                                                   via="old_json")
                if items:
                    return items
            except Exception:
                self.stats["errors"] += 1

            # Tier 3 — public RSS feed, regex-parsed
            try:
                body = api_communion.get_text(
                    f"https://www.reddit.com/r/{quote(sub)}/.rss",
                    ttl_s=TTL_TRENDING_S, timeout=self.timeout,
                    headers=self.BROWSER_HEADERS_XML)
                return self._reddit_from_rss(body, sub, limit)
            except Exception:
                self.stats["errors"] += 1
                return []
        except Exception:
            self.stats["errors"] += 1
            return []

    # ─────────────────────────────────────────────────────────────────
    # Yahoo Finance (no key — public chart endpoint)
    # ─────────────────────────────────────────────────────────────────
    def fetch_yahoo_quote(self, symbol: str) -> Optional[ResearchItem]:
        """Latest price for a symbol (BTC-USD, ETH-USD, AAPL, ^GSPC…)."""
        try:
            sym = _s(symbol) or "BTC-USD"
            data, _ = _unwrap(api_communion.get_json(
                f"https://query1.finance.yahoo.com/v8/finance/chart/"
                f"{quote(sym)}?interval=1d&range=5d",
                ttl_s=TTL_QUOTE_S, timeout=self.timeout))
            chart = (data or {}).get("chart", {}).get("result", []) \
                if isinstance(data, dict) else []
            if not chart:
                return None
            meta = chart[0].get("meta", {}) or {}
            price = meta.get("regularMarketPrice")
            prev_close = meta.get("previousClose", price)
            if price is None:
                return None
            price = float(price)
            prev_close = float(prev_close) if prev_close else price
            if not (math.isfinite(price) and math.isfinite(prev_close)):
                return None
            currency = _s(meta.get("currency")) or "USD"
            change_pct = ((price - prev_close) / prev_close * 100.0) \
                if prev_close else 0.0
            text = (f"{sym} {currency} {price:.2f} "
                    f"({'+' if change_pct >= 0 else ''}{change_pct:.2f}%) "
                    f"prev_close={prev_close:.2f}")
            return self._register(ResearchItem(
                source="yahoo_finance",
                topic=sym,
                title=f"{sym} {currency}",
                text=text,
                url=f"https://finance.yahoo.com/quote/{quote(sym)}",
                summary=f"Yahoo Finance quote: {text}",
                category="market",
                raw={"price": price, "prev_close": prev_close,
                     "change_pct": change_pct},
            ))
        except Exception:
            self.stats["errors"] += 1
            return None

    # ─────────────────────────────────────────────────────────────────
    # Wikipedia (no key — reuses open_sources where it fits)
    # ─────────────────────────────────────────────────────────────────
    def fetch_wikipedia(self, topic: str) -> Optional[ResearchItem]:
        """REST summary card for a Wikipedia topic."""
        try:
            t = _s(topic)
            if not t:
                return None
            body = open_sources.wiki_summary(t)
            if not isinstance(body, dict) or not body:
                return None
            extract = _s(body.get("extract"), 1500)
            if not extract:
                return None
            title = _s(body.get("title")) or t
            return self._register(ResearchItem(
                source="wikipedia",
                topic=t,
                title=title,
                text=extract,
                url=_s((body.get("content_urls") or {})
                       .get("desktop", {}).get("page")),
                summary=f"Wikipedia ({title}): {extract[:240]}",
                category="knowledge",
                raw={"description": _s(body.get("description"))},
            ))
        except Exception:
            self.stats["errors"] += 1
            return None

    def search_wikipedia(self, query: str, n: int = 3) -> List[ResearchItem]:
        """Opensearch titles for a query → up to n summary cards."""
        try:
            q = _s(query)
            if not q:
                return []
            items: List[ResearchItem] = []
            for title in open_sources.wiki_opensearch(q, limit=max(1, int(n))):
                item = self.fetch_wikipedia(title)
                if item:
                    items.append(item)
            return items
        except Exception:
            self.stats["errors"] += 1
            return []

    # ─────────────────────────────────────────────────────────────────
    # USGS earthquakes (no key)
    # ─────────────────────────────────────────────────────────────────
    def fetch_usgs_quakes(self, n: int = 5,
                          period: str = "day") -> List[ResearchItem]:
        """Recent significant earthquakes (hour/day/week/month).

        (Upstream's fetch_usgs_earthquakes passes a bogus `timestamp=`
        kwarg its dataclass rejects, silently yielding [] — this port
        fixes that and records the event time in `raw`.)"""
        try:
            period = period if period in ("hour", "day", "week", "month") \
                else "day"
            data, _ = _unwrap(api_communion.get_json(
                "https://earthquake.usgs.gov/earthquakes/feed/v1.0/"
                f"summary/significant_{period}.geojson",
                ttl_s=TTL_TRENDING_S, timeout=self.timeout))
            features = (data or {}).get("features", []) \
                if isinstance(data, dict) else []
            items: List[ResearchItem] = []
            for feat in features[: max(1, int(n))]:
                try:
                    props = (feat or {}).get("properties", {}) or {}
                    place = _s(props.get("place"))
                    try:
                        mag = float(props.get("mag") or 0.0)
                    except (TypeError, ValueError):
                        mag = 0.0
                    time_ms = props.get("time") or 0
                    text = f"Magnitude {mag} earthquake — {place}"
                    items.append(self._register(ResearchItem(
                        source="usgs",
                        topic=f"M{mag}",
                        title=f"M{mag} {place}".strip(),
                        text=text,
                        url=_s(props.get("url")),
                        summary=f"USGS significant ({period}): {text}",
                        category="temporal",
                        raw={"mag": mag, "place": place, "time_ms": time_ms},
                    )))
                except Exception:
                    self.stats["errors"] += 1
                    continue
            return items
        except Exception:
            self.stats["errors"] += 1
            return []

    # upstream name alias — same fixed behavior
    fetch_usgs_earthquakes = fetch_usgs_quakes

    # ─────────────────────────────────────────────────────────────────
    # Open-Meteo (no key — weather)
    # ─────────────────────────────────────────────────────────────────
    def fetch_open_meteo(self, lat: float = 51.5074,
                         lon: float = -0.1278) -> Optional[ResearchItem]:
        """Current weather for a lat/lon. Defaults to London."""
        try:
            lat_f = float(lat)
            lon_f = float(lon)
            data, _ = _unwrap(api_communion.get_json(
                "https://api.open-meteo.com/v1/forecast"
                f"?latitude={lat_f}&longitude={lon_f}"
                "&current_weather=true&timezone=UTC",
                ttl_s=TTL_WEATHER_S, timeout=self.timeout))
            cw = (data or {}).get("current_weather", {}) \
                if isinstance(data, dict) else {}
            if not cw:
                return None
            temp = cw.get("temperature", "?")
            wind = cw.get("windspeed", "?")
            code = cw.get("weathercode", "?")
            text = (f"Weather at ({lat_f:.2f}, {lon_f:.2f}): {temp}°C "
                    f"wind={wind}km/h code={code}")
            return self._register(ResearchItem(
                source="open_meteo",
                topic=f"{lat_f},{lon_f}",
                title=f"Weather ({lat_f:.2f},{lon_f:.2f})",
                text=text,
                url="https://open-meteo.com",
                summary=f"Open-Meteo: {text}",
                category="temporal",
                raw=dict(cw),
            ))
        except Exception:
            self.stats["errors"] += 1
            return None

    # ─────────────────────────────────────────────────────────────────
    # arXiv (no key — Atom XML via get_text + light regex)
    # ─────────────────────────────────────────────────────────────────
    def fetch_arxiv(self, query: str, n: int = 3) -> List[ResearchItem]:
        """Recent arXiv papers matching a query (submittedDate desc)."""
        try:
            import re as _re
            q = _s(query)
            if not q:
                return []
            body = api_communion.get_text(
                "http://export.arxiv.org/api/query"
                f"?search_query=all:{quote(q)}"
                f"&start=0&max_results={max(1, int(n))}"
                "&sortBy=submittedDate&sortOrder=descending",
                ttl_s=TTL_TRENDING_S, timeout=self.timeout)
            if not isinstance(body, str) or not body:
                return []
            entries = _re.findall(r"<entry>(.*?)</entry>", body, _re.DOTALL)
            items: List[ResearchItem] = []
            for ent in entries[: max(1, int(n))]:
                try:
                    title_m = _re.search(r"<title>(.*?)</title>", ent, _re.DOTALL)
                    summary_m = _re.search(r"<summary>(.*?)</summary>", ent,
                                           _re.DOTALL)
                    link_m = _re.search(r"<id>(.*?)</id>", ent)
                    if not title_m:
                        continue
                    title = _s(title_m.group(1), 200)
                    abstract = _s(summary_m.group(1), 500) if summary_m else ""
                    items.append(self._register(ResearchItem(
                        source="arxiv",
                        topic=q,
                        title=title,
                        text=abstract or title,
                        url=_s(link_m.group(1)) if link_m else "",
                        summary=f"arXiv ({q}): {title}",
                        category="knowledge",
                        raw={},
                    )))
                except Exception:
                    self.stats["errors"] += 1
                    continue
            return items
        except Exception:
            self.stats["errors"] += 1
            return []

    # ─────────────────────────────────────────────────────────────────
    # Hacker News search (no key — Algolia public search mirror)
    # ─────────────────────────────────────────────────────────────────
    def fetch_hn_search(self, query: str, n: int = 3) -> List[ResearchItem]:
        """HN stories matching a query (topic-corroboration source)."""
        try:
            q = _s(query)
            if not q:
                return []
            data, _ = _unwrap(api_communion.get_json(
                f"https://hn.algolia.com/api/v1/search?query={quote(q)}"
                f"&tags=story&hitsPerPage={max(1, int(n))}",
                ttl_s=TTL_TRENDING_S, timeout=self.timeout))
            hits = (data or {}).get("hits", []) \
                if isinstance(data, dict) else []
            items: List[ResearchItem] = []
            for hit in hits[: max(1, int(n))]:
                try:
                    title = _s((hit or {}).get("title"))
                    if not title:
                        continue
                    oid = _s((hit or {}).get("objectID"))
                    url = _s((hit or {}).get("url")) or \
                        (f"https://news.ycombinator.com/item?id={oid}" if oid
                         else "")
                    items.append(self._register(ResearchItem(
                        source="hn_search",
                        topic=q,
                        title=title,
                        text=f"{title} — {_s(hit.get('author'))} "
                             f"{hit.get('points', 0)} points",
                        url=url,
                        summary=f"HN search ({q}): {title}",
                        category="knowledge",
                        raw={"points": hit.get("points", 0),
                             "num_comments": hit.get("num_comments", 0)},
                    )))
                except Exception:
                    self.stats["errors"] += 1
                    continue
            return items
        except Exception:
            self.stats["errors"] += 1
            return []

    # ─────────────────────────────────────────────────────────────────
    # GDELT 2 (no key — global news article list)
    # ─────────────────────────────────────────────────────────────────
    def fetch_gdelt(self, query: str, n: int = 10) -> List[ResearchItem]:
        """Recent worldwide news articles matching a query (GDELT doc API)."""
        try:
            q = _s(query)
            if not q:
                return []
            data, _ = _unwrap(api_communion.get_json(
                "https://api.gdeltproject.org/api/v2/doc/doc"
                f"?query={quote(q)}&mode=artlist&format=json"
                f"&maxrecords={max(1, min(50, int(n)))}",
                ttl_s=TTL_TRENDING_S,
                timeout=max(self.timeout, 20.0)))   # GDELT is slow to answer
            articles = (data or {}).get("articles", []) \
                if isinstance(data, dict) else []
            items: List[ResearchItem] = []
            for art in articles[: max(1, int(n))]:
                try:
                    title = _s((art or {}).get("title"))
                    if not title:
                        continue
                    domain = _s((art or {}).get("domain"))
                    items.append(self._register(ResearchItem(
                        source="gdelt",
                        topic=q,
                        title=title,
                        text=(f"{title} — {domain}" if domain else title),
                        url=_s((art or {}).get("url")) or
                            _s((art or {}).get("url_mobile")),
                        summary=f"GDELT ({q}): {title}",
                        category="user_input",   # external world events
                        raw={"domain": domain,
                             "seendate": _s((art or {}).get("seendate")),
                             "country": _s((art or {}).get("sourcecountry"))},
                    )))
                except Exception:
                    self.stats["errors"] += 1
                    continue
            return items
        except Exception:
            self.stats["errors"] += 1
            return []

    # ─────────────────────────────────────────────────────────────────
    # Open Library (no key — book search)
    # ─────────────────────────────────────────────────────────────────
    def fetch_open_library(self, query: str, n: int = 5) -> List[ResearchItem]:
        """Books matching a query (title / authors / first publish year)."""
        try:
            q = _s(query)
            if not q:
                return []
            data, _ = _unwrap(api_communion.get_json(
                f"https://openlibrary.org/search.json?q={quote(q)}"
                f"&limit={max(1, int(n))}",
                ttl_s=TTL_WIKI_SUMMARY_S, timeout=self.timeout))
            docs = (data or {}).get("docs", []) \
                if isinstance(data, dict) else []
            items: List[ResearchItem] = []
            for doc in docs[: max(1, int(n))]:
                try:
                    title = _s((doc or {}).get("title"))
                    if not title:
                        continue
                    authors = ", ".join(
                        _s(a) for a in ((doc or {}).get("author_name") or [])[:3]
                        if _s(a))
                    year = (doc or {}).get("first_publish_year")
                    key = _s((doc or {}).get("key"))
                    text = f"{title}" + (f" — {authors}" if authors else "") \
                        + (f" ({year})" if year else "")
                    items.append(self._register(ResearchItem(
                        source="open_library",
                        topic=q,
                        title=title,
                        text=text,
                        url=f"https://openlibrary.org{key}" if key else "",
                        summary=f"Open Library ({q}): {text}",
                        category="knowledge",
                        raw={"authors": authors, "first_publish_year": year},
                    )))
                except Exception:
                    self.stats["errors"] += 1
                    continue
            return items
        except Exception:
            self.stats["errors"] += 1
            return []

    # ─────────────────────────────────────────────────────────────────
    # Wikidata (no key — entity search)
    # ─────────────────────────────────────────────────────────────────
    def fetch_wikidata(self, query: str, n: int = 5) -> List[ResearchItem]:
        """Wikidata entities matching a query (label + description)."""
        try:
            q = _s(query)
            if not q:
                return []
            data, _ = _unwrap(api_communion.get_json(
                "https://www.wikidata.org/w/api.php"
                "?action=wbsearchentities&format=json&language=en"
                f"&search={quote(q)}&limit={max(1, int(n))}",
                ttl_s=TTL_WIKI_SUMMARY_S, timeout=self.timeout))
            results = (data or {}).get("search", []) \
                if isinstance(data, dict) else []
            items: List[ResearchItem] = []
            for ent in results[: max(1, int(n))]:
                try:
                    label = _s((ent or {}).get("label"))
                    if not label:
                        continue
                    qid = _s((ent or {}).get("id"))
                    desc = _s((ent or {}).get("description"))
                    text = f"{label}" + (f" — {desc}" if desc else "")
                    items.append(self._register(ResearchItem(
                        source="wikidata",
                        topic=q,
                        title=label,
                        text=text,
                        url=_s((ent or {}).get("url")) or
                            (f"https://www.wikidata.org/wiki/{qid}" if qid
                             else ""),
                        summary=f"Wikidata ({q}): {text}",
                        category="knowledge",
                        raw={"id": qid, "description": desc},
                    )))
                except Exception:
                    self.stats["errors"] += 1
                    continue
            return items
        except Exception:
            self.stats["errors"] += 1
            return []

    # ─────────────────────────────────────────────────────────────────
    # PubMed (no key — NCBI E-utilities: esearch → esummary)
    # ─────────────────────────────────────────────────────────────────
    def fetch_pubmed(self, query: str, n: int = 5) -> List[ResearchItem]:
        """Recent PubMed papers matching a query (esearch then esummary)."""
        try:
            q = _s(query)
            if not q:
                return []
            count = max(1, min(20, int(n)))
            found, _ = _unwrap(api_communion.get_json(
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
                f"esearch.fcgi?db=pubmed&retmode=json&retmax={count}"
                f"&term={quote(q)}",
                ttl_s=TTL_TRENDING_S, timeout=self.timeout))
            idlist = ((found or {}).get("esearchresult", {}) or {}).get(
                "idlist", []) if isinstance(found, dict) else []
            if not idlist:
                return []
            ids = ",".join(_s(i) for i in idlist[:count] if _s(i))
            if not ids:
                return []
            data, _ = _unwrap(api_communion.get_json(
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
                f"esummary.fcgi?db=pubmed&retmode=json&id={ids}",
                ttl_s=TTL_TRENDING_S, timeout=self.timeout))
            result = (data or {}).get("result", {}) \
                if isinstance(data, dict) else {}
            items: List[ResearchItem] = []
            for uid in result.get("uids", [])[:count]:
                try:
                    rec = result.get(str(uid), {}) or {}
                    title = _s(rec.get("title"))
                    if not title:
                        continue
                    journal = _s(rec.get("fulljournalname")) or \
                        _s(rec.get("source"))
                    pubdate = _s(rec.get("pubdate"))
                    text = f"{title}" \
                        + (f" — {journal}" if journal else "") \
                        + (f" ({pubdate})" if pubdate else "")
                    items.append(self._register(ResearchItem(
                        source="pubmed",
                        topic=q,
                        title=title,
                        text=text,
                        url=f"https://pubmed.ncbi.nlm.nih.gov/{uid}/",
                        summary=f"PubMed ({q}): {text}",
                        category="knowledge",
                        raw={"journal": journal, "pubdate": pubdate},
                    )))
                except Exception:
                    self.stats["errors"] += 1
                    continue
            return items
        except Exception:
            self.stats["errors"] += 1
            return []

    # ─────────────────────────────────────────────────────────────────
    # Generic RSS (no key — get_text + item regex; CDATA-safe)
    # ─────────────────────────────────────────────────────────────────
    def fetch_rss(self, feed_url: str, n: int = 5,
                  source: str = "") -> List[ResearchItem]:
        """Items from any RSS feed (title/link/description per <item>)."""
        try:
            url_in = _s(feed_url)
            if not url_in:
                return []
            body = api_communion.get_text(
                url_in, ttl_s=TTL_TRENDING_S, timeout=self.timeout,
                headers=self.BROWSER_HEADERS_XML)
            if isinstance(body, dict):              # communion stale envelope
                body = body.get("body")
            if not isinstance(body, str) or "<item" not in body:
                return []
            import re as _re
            src = _s(source) or _s(feed_url.split("//")[-1].split("/")[0]) \
                or "rss"
            blocks = _re.findall(r"<item[^>]*>(.*?)</item>", body,
                                 _re.DOTALL | _re.IGNORECASE)

            def _field(block: str, tag: str) -> str:
                m = _re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", block,
                               _re.DOTALL | _re.IGNORECASE)
                if not m:
                    return ""
                val = _re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", m.group(1),
                              flags=_re.DOTALL)
                val = _re.sub(r"<[^>]+>", " ", val)
                return _s(val, 400)

            items: List[ResearchItem] = []
            for block in blocks[: max(1, int(n))]:
                try:
                    title = _field(block, "title")
                    if not title:
                        continue
                    link = _field(block, "link")
                    desc = _field(block, "description")
                    items.append(self._register(ResearchItem(
                        source=f"rss_{src}",
                        topic=src,
                        title=title,
                        text=f"{title} — {desc}" if desc else title,
                        url=link,
                        summary=f"{src}: {title}",
                        category="knowledge",
                        raw={},
                    )))
                except Exception:
                    self.stats["errors"] += 1
                    continue
            return items
        except Exception:
            self.stats["errors"] += 1
            return []

    # ─────────────────────────────────────────────────────────────────
    # CoinGecko (free, no key)
    # ─────────────────────────────────────────────────────────────────
    def fetch_coingecko(self, coin_id: str = "bitcoin") -> Optional[ResearchItem]:
        """Market data for a coin from CoinGecko."""
        try:
            cid = _s(coin_id) or "bitcoin"
            data, _ = _unwrap(api_communion.get_json(
                f"https://api.coingecko.com/api/v3/coins/{quote(cid)}"
                "?localization=false&tickers=false&market_data=true"
                "&community_data=false&developer_data=false",
                ttl_s=TTL_QUOTE_S, timeout=self.timeout))
            if not isinstance(data, dict) or not data:
                return None
            market = data.get("market_data", {}) or {}
            values = {
                "price": (market.get("current_price", {}) or {}).get("usd"),
                "change_24h": market.get("price_change_percentage_24h"),
                "mcap": (market.get("market_cap", {}) or {}).get("usd"),
                "volume": (market.get("total_volume", {}) or {}).get("usd"),
            }
            numeric = {}
            for key, value in values.items():
                if value is None:
                    return None
                numeric[key] = float(value)
            if not all(math.isfinite(v) for v in numeric.values()):
                return None
            if any(numeric[k] < 0 for k in ("price", "mcap", "volume")):
                return None
            price = numeric["price"]
            change = numeric["change_24h"]
            text = (f"{cid} ${price:,.2f} "
                    f"({'+' if change >= 0 else ''}{change:.2f}% 24h) "
                    f"mcap=${numeric['mcap']/1e9:.1f}B "
                    f"vol=${numeric['volume']/1e9:.1f}B")
            return self._register(ResearchItem(
                source="coingecko",
                topic=cid,
                title=_s(data.get("name")) or cid,
                text=text,
                url=f"https://www.coingecko.com/en/coins/{quote(cid)}",
                summary=f"CoinGecko: {text}",
                category="market",
                raw=numeric,
            ))
        except Exception:
            self.stats["errors"] += 1
            return None

    # ─────────────────────────────────────────────────────────────────
    # Universal search — port of upstream answer_question()
    # ─────────────────────────────────────────────────────────────────
    def answer_question(self, question: str,
                        n_per_source: int = 2) -> List[ResearchItem]:
        """Aggregate WorldDataItems-style answers from many free sources.

        Mirrors the upstream routing (news/world → reddit+rss hints,
        geopolitics → sources, markets → yahoo+coingecko) minus feeds this
        port does not expose. Every sub-fetch is isolated — one dead source
        never sinks the rest."""
        results: List[ResearchItem] = []
        try:
            q = _s(question)
            if not q:
                return []
            lower = q.lower()

            def _extend(fn):
                try:
                    results.extend(fn() or [])
                except Exception:
                    self.stats["errors"] += 1

            def _maybe(fn):
                """Extend with the single item of an Optional-fetcher."""
                def _run():
                    try:
                        item = fn()
                        return [item] if item else []
                    except Exception:
                        self.stats["errors"] += 1
                        return []
                _extend(_run)

            # 1. Wikipedia — always try for facts
            _extend(lambda: self.search_wikipedia(q, n=n_per_source))

            # 2. World / news / events
            if any(w in lower for w in (
                    "news", "world", "politic", "election", "war",
                    "crisis", "event", "today")):
                _extend(lambda: self.fetch_reddit("worldnews", n=n_per_source))

            # 3. Science
            if any(w in lower for w in (
                    "paper", "research", "study", "arxiv", "science",
                    "physics", "quantum")):
                _extend(lambda: self.fetch_arxiv(q, n=n_per_source))

            # 4. Markets
            if any(w in lower for w in (
                    "price", "market", "stock", "trade", "btc", "eth",
                    "bitcoin", "ethereum", "economy", "gdp", "inflation",
                    "rate")):
                symbols = []
                coin_ids = []
                if "btc" in lower or "bitcoin" in lower:
                    symbols.append("BTC-USD")
                    coin_ids.append("bitcoin")
                if "eth" in lower or "ethereum" in lower:
                    symbols.append("ETH-USD")
                    coin_ids.append("ethereum")
                if not symbols:
                    symbols.append("BTC-USD")
                for sym in symbols[:2]:
                    _maybe(lambda s=sym: self.fetch_yahoo_quote(s))
                for cid in coin_ids[:2]:
                    _maybe(lambda c=cid: self.fetch_coingecko(c))

            # 5. Nature / environment
            if any(w in lower for w in (
                    "earthquake", "quake", "seismic", "weather", "climate",
                    "storm", "temperature")):
                _extend(lambda: self.fetch_usgs_quakes(n=n_per_source))
                _maybe(self.fetch_open_meteo)
        except Exception:
            self.stats["errors"] += 1
        return results

    def get_stats(self) -> Dict[str, Any]:
        try:
            return dict(self.stats)
        except Exception:
            return {}


# ─────────────────────────────────────────────────────────────────────────────
# CLI — probe one item per source (all offline-safe on failure)
# ─────────────────────────────────────────────────────────────────────────────


def _emit(payload: Dict[str, Any]) -> None:
    try:
        import json
        import sys
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    except Exception:
        pass


def main(argv=None) -> int:
    import sys
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print("usage: python -m aureon_fusion.research_ingester probe")
        return 0
    if argv[0] == "probe":
        ing = ResearchIngester()

        def _one(fn):
            try:
                item = fn()
                return item.to_dict() if item else None
            except Exception:
                return None

        report = {
            "hacker_news": [i.to_dict() for i in ing.fetch_hacker_news(n=1)],
            "hn_search": [i.to_dict()
                          for i in ing.fetch_hn_search("fusion", n=1)],
            "reddit_worldnews": [i.to_dict()
                                 for i in ing.fetch_reddit("worldnews", n=1)],
            "yahoo_quote": _one(lambda: ing.fetch_yahoo_quote("BTC-USD")),
            "wikipedia": _one(lambda: ing.fetch_wikipedia("Solar wind")),
            "usgs_quakes": [i.to_dict() for i in ing.fetch_usgs_quakes(n=1)],
            "open_meteo": _one(ing.fetch_open_meteo),
            "arxiv": [i.to_dict() for i in ing.fetch_arxiv("coherence", n=1)],
            "coingecko": _one(lambda: ing.fetch_coingecko("bitcoin")),
            "gdelt": [i.to_dict() for i in ing.fetch_gdelt("science", n=1)],
            "open_library": [i.to_dict()
                             for i in ing.fetch_open_library("solar wind",
                                                             n=1)],
            "wikidata": [i.to_dict()
                         for i in ing.fetch_wikidata("solar wind", n=1)],
            "pubmed": [i.to_dict()
                       for i in ing.fetch_pubmed("solar wind", n=1)],
            "rss": [i.to_dict() for i in ing.fetch_rss(
                "https://feeds.bbci.co.uk/news/world/rss.xml", n=1,
                source="bbc_world")],
            "stats": ing.get_stats(),
        }
        _emit(report)
        return 0
    print(f"unknown command: {argv[0]}")
    return 1


if __name__ == "__main__":
    import sys as _sys
    _sys.exit(main())
