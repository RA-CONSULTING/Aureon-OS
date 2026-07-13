"""
aureon/integrations/world_data/world_data_ingester.py

WorldDataIngester — pulls live external data into the Aureon vault from
FREE APIs that require NO keys:

  - Wikipedia REST API   (wiki articles for any topic)
  - Yahoo Finance        (live prices, market data)
  - CoinGecko            (free crypto market data)
  - Hacker News          (tech / world headlines)
  - Reddit JSON          (worldnews / geopolitics / locality subreddits)
  - GDELT                (geopolitical event database)

Architecture:
  fetch_*() methods → list of WorldDataItem
  ingest_* methods → publish to ThoughtBus + write to vault as cards
  search(query) → universal cross-source search

Each item becomes a vault card with a category (so the interpreter
classifies it correctly) and ends up in the knowledge dataset via the
normal stash pocket / interpretation flow.

Pure stdlib: urllib + json. No aiohttp, no requests. No API keys.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("aureon.integrations.world_data")


# ─────────────────────────────────────────────────────────────────────────────
# Data structure
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class WorldDataItem:
    """One item pulled from any external API."""
    source: str            # "wikipedia" / "yahoo_finance" / "coingecko" / ...
    topic: str             # query / symbol / subreddit / term
    title: str
    text: str
    url: str = ""
    timestamp: float = field(default_factory=time.time)
    raw: Dict[str, Any] = field(default_factory=dict)
    category: str = "knowledge"   # for the interpreter

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ─────────────────────────────────────────────────────────────────────────────
# WorldDataIngester
# ─────────────────────────────────────────────────────────────────────────────


class WorldDataIngester:
    """
    Pulls external knowledge from free no-key APIs.
    Thread-safe singleton.
    """

    USER_AGENT = "Aureon-ICS/1.0 (research; +https://github.com/RA-CONSULTING/aureon-trading)"

    def __init__(
        self,
        vault: Any = None,
        thought_bus: Any = None,
        timeout: float = 8.0,
    ):
        self.vault = vault
        self.thought_bus = thought_bus
        self.timeout = timeout
        self._lock = threading.RLock()
        self._stats = {
            "wikipedia_calls": 0,
            "yahoo_calls": 0,
            "coingecko_calls": 0,
            "hackernews_calls": 0,
            "reddit_calls": 0,
            "gdelt_calls": 0,
            "open_meteo_calls": 0,
            "rest_countries_calls": 0,
            "usgs_calls": 0,
            "arxiv_calls": 0,
            "world_bank_calls": 0,
            "fred_calls": 0,
            "noaa_cdo_calls": 0,
            "usgs_water_calls": 0,
            "open_library_calls": 0,
            "wikidata_calls": 0,
            "duckduckgo_calls": 0,
            "pubmed_calls": 0,
            "rss_calls": 0,
            "items_ingested": 0,
            "errors": 0,
        }

    # ─────────────────────────────────────────────────────────────────────
    # HTTP helper
    # ─────────────────────────────────────────────────────────────────────
    def _http_get(self, url: str) -> Optional[Any]:
        """Plain stdlib HTTP GET → parsed JSON. Returns None on any error."""
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": self.USER_AGENT, "Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = resp.read()
                return json.loads(data.decode("utf-8"))
        except Exception as exc:
            logger.debug("HTTP GET failed (%s): %s", url, exc)
            with self._lock:
                self._stats["errors"] += 1
            return None

    def _http_get_headers(self, url: str, headers: Dict[str, str]) -> Optional[Any]:
        """Like ``_http_get`` but with caller-supplied headers (API-key auth).

        Used by the keyed feeds (NOAA CDO ``token``, USGS Water ``X-Api-Key``).
        Returns None on any error — never raises into the daemon loop.
        """
        try:
            merged = {"User-Agent": self.USER_AGENT, "Accept": "application/json"}
            merged.update(headers)
            req = urllib.request.Request(url, headers=merged)
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            logger.debug("HTTP GET (headers) failed (%s): %s", url, exc)
            with self._lock:
                self._stats["errors"] += 1
            return None

    # ─────────────────────────────────────────────────────────────────────
    # NOAA NCEI — Climate Data Online (keyed: header `token` = NOAA_API_KEY)
    # ─────────────────────────────────────────────────────────────────────
    def fetch_noaa_climate(self, limit: int = 5) -> Optional[WorldDataItem]:
        """NCEI Climate Data Online dataset catalogue (a keyed reachability read).

        Keyed feed: reads ``NOAA_API_KEY`` lazily from the environment (the
        bootstrap populates it). The ``/datasets`` endpoint needs only the token
        (the ``/data`` endpoint requires a station + date range), so it is the
        reliable "is the CDO key live" signal for the HNC field. Returns None —
        a clean keyless-skip — when the key is absent, so a keyless deploy boots.
        """
        with self._lock:
            self._stats["noaa_cdo_calls"] += 1
        token = os.environ.get("NOAA_API_KEY", "").strip()
        if not token:
            return None
        url = f"https://www.ncei.noaa.gov/cdo-web/api/v2/datasets?limit={int(limit)}"
        data = self._http_get_headers(url, {"token": token})
        if not data:
            return None
        results = data.get("results", []) if isinstance(data, dict) else []
        if not results:
            return None
        first = results[0]
        name = first.get("name") or first.get("id", "")
        return WorldDataItem(
            source="noaa_cdo",
            topic="datasets",
            title=f"NOAA CDO {name}",
            text=f"NOAA Climate Data Online: {len(results)} datasets (top: {name})",
            url="https://www.ncei.noaa.gov/cdo-web/",
            raw={"count": len(results), "first": first},
            category="environmental",
        )

    # ─────────────────────────────────────────────────────────────────────
    # USGS — Water Data OGC API (keyed: header `X-Api-Key` = USGS_API_KEY)
    # ─────────────────────────────────────────────────────────────────────
    def fetch_usgs_water(self, limit: int = 5) -> Optional[WorldDataItem]:
        """USGS Water Data collections snapshot.

        Keyed feed: reads ``USGS_API_KEY`` lazily from the environment. Returns
        None (keyless-skip) when the key is absent.
        """
        with self._lock:
            self._stats["usgs_water_calls"] += 1
        key = os.environ.get("USGS_API_KEY", "").strip()
        if not key:
            return None
        url = (
            "https://api.waterdata.usgs.gov/ogcapi/v0/collections"
            f"?limit={int(limit)}"
        )
        data = self._http_get_headers(url, {"X-Api-Key": key})
        if not data:
            return None
        collections = data.get("collections", []) if isinstance(data, dict) else []
        if not collections:
            return None
        first = collections[0]
        title = first.get("title") or first.get("id", "")
        return WorldDataItem(
            source="usgs_water",
            topic="collections",
            title=f"USGS Water {title}",
            text=f"USGS Water Data: {len(collections)} collections (top: {title})",
            url="https://api.waterdata.usgs.gov/ogcapi/v0/",
            raw={"count": len(collections), "first": first},
            category="environmental",
        )

    # ─────────────────────────────────────────────────────────────────────
    # Wikipedia REST API (no key)
    # ─────────────────────────────────────────────────────────────────────
    def fetch_wikipedia(self, topic: str) -> Optional[WorldDataItem]:
        """Fetch the summary card for a Wikipedia topic."""
        with self._lock:
            self._stats["wikipedia_calls"] += 1
        # URL-encode the topic
        safe = urllib.parse.quote(topic.replace(" ", "_"))
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{safe}"
        data = self._http_get(url)
        if not data or "extract" not in data:
            return None
        return WorldDataItem(
            source="wikipedia",
            topic=topic,
            title=data.get("title", topic),
            text=data.get("extract", "")[:1500],
            url=data.get("content_urls", {}).get("desktop", {}).get("page", ""),
            raw={"description": data.get("description", "")},
            category="knowledge",
        )

    def search_wikipedia(self, query: str, n: int = 3) -> List[WorldDataItem]:
        """Search Wikipedia for a query, return top n summaries."""
        with self._lock:
            self._stats["wikipedia_calls"] += 1
        safe = urllib.parse.quote(query)
        url = (
            f"https://en.wikipedia.org/w/api.php?action=opensearch"
            f"&search={safe}&limit={n}&namespace=0&format=json"
        )
        data = self._http_get(url)
        if not data or len(data) < 4:
            return []
        titles = data[1]
        items: List[WorldDataItem] = []
        for title in titles[:n]:
            item = self.fetch_wikipedia(title)
            if item:
                items.append(item)
        return items

    # ─────────────────────────────────────────────────────────────────────
    # Yahoo Finance (no key — public chart endpoint)
    # ─────────────────────────────────────────────────────────────────────
    def fetch_yahoo_quote(self, symbol: str) -> Optional[WorldDataItem]:
        """
        Fetch the latest price for a symbol from Yahoo Finance public endpoint.
        Examples: "BTC-USD", "ETH-USD", "AAPL", "^GSPC"
        """
        with self._lock:
            self._stats["yahoo_calls"] += 1
        safe = urllib.parse.quote(symbol)
        url = (
            f"https://query1.finance.yahoo.com/v8/finance/chart/{safe}"
            f"?interval=1d&range=5d"
        )
        data = self._http_get(url)
        if not data:
            return None
        try:
            chart = data.get("chart", {}).get("result", [])
            if not chart:
                return None
            result = chart[0]
            meta = result.get("meta", {})
            price = meta.get("regularMarketPrice")
            currency = meta.get("currency", "USD")
            prev_close = meta.get("previousClose", price)
            change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0
            text = (
                f"{symbol} {currency} {price:.2f} "
                f"({'+' if change_pct >= 0 else ''}{change_pct:.2f}%) "
                f"prev_close={prev_close:.2f}"
            )
            return WorldDataItem(
                source="yahoo_finance",
                topic=symbol,
                title=f"{symbol} {currency}",
                text=text,
                url=f"https://finance.yahoo.com/quote/{safe}",
                raw={"price": price, "prev_close": prev_close, "change_pct": change_pct},
                category="market",
            )
        except Exception as exc:
            logger.debug("Yahoo parse failed: %s", exc)
            return None

    # ─────────────────────────────────────────────────────────────────────
    # CoinGecko (free, no key)
    # ─────────────────────────────────────────────────────────────────────
    def fetch_coingecko(self, coin_id: str = "bitcoin") -> Optional[WorldDataItem]:
        """Fetch market data for a coin from CoinGecko."""
        with self._lock:
            self._stats["coingecko_calls"] += 1
        url = (
            f"https://api.coingecko.com/api/v3/coins/{coin_id}"
            f"?localization=false&tickers=false&market_data=true"
            f"&community_data=false&developer_data=false"
        )
        data = self._http_get(url)
        if not data:
            return None
        try:
            market = data.get("market_data", {})
            price = market.get("current_price", {}).get("usd", 0)
            change_24h = market.get("price_change_percentage_24h", 0)
            mcap = market.get("market_cap", {}).get("usd", 0)
            vol = market.get("total_volume", {}).get("usd", 0)
            text = (
                f"{coin_id} ${price:,.2f} "
                f"({'+' if change_24h >= 0 else ''}{change_24h:.2f}% 24h) "
                f"mcap=${mcap/1e9:.1f}B vol=${vol/1e9:.1f}B"
            )
            return WorldDataItem(
                source="coingecko",
                topic=coin_id,
                title=data.get("name", coin_id),
                text=text,
                url=f"https://www.coingecko.com/en/coins/{coin_id}",
                raw={"price": price, "change_24h": change_24h, "mcap": mcap, "volume": vol},
                category="market",
            )
        except Exception as exc:
            logger.debug("CoinGecko parse failed: %s", exc)
            return None

    # ─────────────────────────────────────────────────────────────────────
    # Hacker News (no key)
    # ─────────────────────────────────────────────────────────────────────
    def fetch_hacker_news(self, n: int = 5) -> List[WorldDataItem]:
        """Fetch top stories from Hacker News."""
        with self._lock:
            self._stats["hackernews_calls"] += 1
        ids = self._http_get("https://hacker-news.firebaseio.com/v0/topstories.json")
        if not ids:
            return []
        items: List[WorldDataItem] = []
        for sid in ids[:n]:
            story = self._http_get(
                f"https://hacker-news.firebaseio.com/v0/item/{sid}.json"
            )
            if not story or "title" not in story:
                continue
            items.append(WorldDataItem(
                source="hacker_news",
                topic="top",
                title=story.get("title", ""),
                text=story.get("title", "") + " — " + str(story.get("score", 0)) + " points",
                url=story.get("url", f"https://news.ycombinator.com/item?id={sid}"),
                raw={"score": story.get("score", 0), "by": story.get("by", "")},
                category="knowledge",
            ))
        return items

    # ─────────────────────────────────────────────────────────────────────
    # Reddit JSON (no key)
    # ─────────────────────────────────────────────────────────────────────
    def fetch_reddit(
        self,
        subreddit: str = "worldnews",
        n: int = 5,
        sort: str = "top",
    ) -> List[WorldDataItem]:
        """Fetch top posts from a subreddit (worldnews / geopolitics / etc)."""
        with self._lock:
            self._stats["reddit_calls"] += 1
        url = f"https://www.reddit.com/r/{subreddit}/{sort}.json?limit={n}&t=day"
        data = self._http_get(url)
        if not data:
            return []
        items: List[WorldDataItem] = []
        try:
            children = data.get("data", {}).get("children", [])
            for c in children[:n]:
                post = c.get("data", {})
                title = post.get("title", "")
                if not title:
                    continue
                # Categorise based on subreddit
                cat = "knowledge"
                sub_lower = subreddit.lower()
                if "news" in sub_lower or "politics" in sub_lower or "geopolitic" in sub_lower:
                    cat = "user_input"  # external world events
                elif "crypto" in sub_lower or "bitcoin" in sub_lower:
                    cat = "market"
                items.append(WorldDataItem(
                    source=f"reddit_r/{subreddit}",
                    topic=subreddit,
                    title=title,
                    text=f"{title} — {post.get('selftext', '')[:300]}",
                    url=f"https://reddit.com{post.get('permalink', '')}",
                    raw={"score": post.get("score", 0), "ups": post.get("ups", 0),
                         "num_comments": post.get("num_comments", 0)},
                    category=cat,
                ))
        except Exception as exc:
            logger.debug("Reddit parse failed: %s", exc)
        return items

    # ─────────────────────────────────────────────────────────────────────
    # GDELT (no key — geopolitical event database)
    # ─────────────────────────────────────────────────────────────────────
    def fetch_gdelt(self, query: str, n: int = 5) -> List[WorldDataItem]:
        """Search GDELT for geopolitical events related to a query."""
        with self._lock:
            self._stats["gdelt_calls"] += 1
        safe = urllib.parse.quote(query)
        url = (
            f"https://api.gdeltproject.org/api/v2/doc/doc"
            f"?query={safe}&mode=ArtList&maxrecords={n}&format=json"
        )
        data = self._http_get(url)
        if not data:
            return []
        items: List[WorldDataItem] = []
        try:
            articles = data.get("articles", [])
            for art in articles[:n]:
                title = art.get("title", "")
                if not title:
                    continue
                items.append(WorldDataItem(
                    source="gdelt",
                    topic=query,
                    title=title,
                    text=f"{title} — {art.get('domain', '')} ({art.get('language', '')})",
                    url=art.get("url", ""),
                    raw={"domain": art.get("domain", ""), "seendate": art.get("seendate", "")},
                    category="user_input",  # geopolitical world event
                ))
        except Exception as exc:
            logger.debug("GDELT parse failed: %s", exc)
        return items

    # ─────────────────────────────────────────────────────────────────────
    # Open-Meteo (free, no key — weather)
    # ─────────────────────────────────────────────────────────────────────
    def fetch_open_meteo(self, lat: float = 51.5074, lon: float = -0.1278) -> Optional[WorldDataItem]:
        """Fetch current weather for a lat/lon. Defaults to London."""
        with self._lock:
            self._stats["open_meteo_calls"] += 1
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&current_weather=true&timezone=UTC"
        )
        data = self._http_get(url)
        if not data:
            return None
        try:
            cw = data.get("current_weather", {})
            temp = cw.get("temperature", "?")
            wind = cw.get("windspeed", "?")
            code = cw.get("weathercode", "?")
            text = f"Weather at ({lat:.2f}, {lon:.2f}): {temp}°C wind={wind}km/h code={code}"
            return WorldDataItem(
                source="open_meteo",
                topic=f"{lat},{lon}",
                title=f"Weather ({lat:.2f},{lon:.2f})",
                text=text,
                url="https://open-meteo.com",
                raw=cw,
                category="temporal",
            )
        except Exception:
            return None

    # ─────────────────────────────────────────────────────────────────────
    # REST Countries (free, no key — country facts)
    # ─────────────────────────────────────────────────────────────────────
    def fetch_rest_countries(self, name: str) -> Optional[WorldDataItem]:
        """Fetch country facts (population, capital, region, currencies)."""
        with self._lock:
            self._stats["rest_countries_calls"] += 1
        safe = urllib.parse.quote(name)
        url = f"https://restcountries.com/v3.1/name/{safe}?fields=name,capital,region,population,currencies,languages"
        data = self._http_get(url)
        if not data or not isinstance(data, list) or not data:
            return None
        try:
            c = data[0]
            cname = c.get("name", {}).get("common", name)
            capital = ", ".join(c.get("capital", []))
            region = c.get("region", "")
            pop = c.get("population", 0)
            currencies = list(c.get("currencies", {}).keys())
            text = (
                f"{cname}: capital={capital} region={region} "
                f"population={pop:,} currencies={currencies}"
            )
            return WorldDataItem(
                source="rest_countries",
                topic=name,
                title=cname,
                text=text,
                url=f"https://en.wikipedia.org/wiki/{cname.replace(' ', '_')}",
                raw=c,
                category="user_input",
            )
        except Exception:
            return None

    # ─────────────────────────────────────────────────────────────────────
    # USGS Earthquakes (free, no key)
    # ─────────────────────────────────────────────────────────────────────
    def fetch_usgs_earthquakes(self, n: int = 5, period: str = "day") -> List[WorldDataItem]:
        """Fetch recent significant earthquakes (past hour/day/week)."""
        with self._lock:
            self._stats["usgs_calls"] += 1
        period = period if period in ("hour", "day", "week", "month") else "day"
        url = f"https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_{period}.geojson"
        data = self._http_get(url)
        if not data:
            return []
        items: List[WorldDataItem] = []
        try:
            for feat in data.get("features", [])[:n]:
                props = feat.get("properties", {})
                place = props.get("place", "")
                mag = props.get("mag", 0)
                time_ms = props.get("time", 0)
                ts = time_ms / 1000.0 if time_ms else time.time()
                text = f"Magnitude {mag} earthquake — {place}"
                items.append(WorldDataItem(
                    source="usgs",
                    topic=f"M{mag}",
                    title=f"M{mag} {place}",
                    text=text,
                    url=props.get("url", ""),
                    timestamp=ts,
                    raw={"mag": mag, "place": place, "time_ms": time_ms},
                    category="temporal",
                ))
        except Exception:
            pass
        return items

    # ─────────────────────────────────────────────────────────────────────
    # arXiv (free, no key — scientific papers)
    # ─────────────────────────────────────────────────────────────────────
    def fetch_arxiv(self, query: str, n: int = 3) -> List[WorldDataItem]:
        """Search arXiv for recent papers matching a query."""
        with self._lock:
            self._stats["arxiv_calls"] += 1
        safe = urllib.parse.quote(query)
        url = (
            f"http://export.arxiv.org/api/query?search_query=all:{safe}"
            f"&start=0&max_results={n}&sortBy=submittedDate&sortOrder=descending"
        )
        # arXiv returns Atom XML, not JSON — parse with regex (light touch)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": self.USER_AGENT})
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8")
        except Exception:
            with self._lock:
                self._stats["errors"] += 1
            return []
        import re as _re
        entries = _re.findall(r"<entry>(.*?)</entry>", body, _re.DOTALL)
        items: List[WorldDataItem] = []
        for ent in entries[:n]:
            title_m = _re.search(r"<title>(.*?)</title>", ent, _re.DOTALL)
            summary_m = _re.search(r"<summary>(.*?)</summary>", ent, _re.DOTALL)
            link_m = _re.search(r"<id>(.*?)</id>", ent)
            if not title_m:
                continue
            items.append(WorldDataItem(
                source="arxiv",
                topic=query,
                title=title_m.group(1).strip()[:200],
                text=(summary_m.group(1).strip() if summary_m else "")[:500],
                url=link_m.group(1).strip() if link_m else "",
                raw={},
                category="knowledge",
            ))
        return items

    # ─────────────────────────────────────────────────────────────────────
    # World Bank (free, no key — economic indicators)
    # ─────────────────────────────────────────────────────────────────────
    def fetch_world_bank(self, country: str = "US", indicator: str = "NY.GDP.MKTP.CD") -> Optional[WorldDataItem]:
        """Fetch an economic indicator for a country. Defaults to US GDP."""
        with self._lock:
            self._stats["world_bank_calls"] += 1
        url = (
            f"https://api.worldbank.org/v2/country/{country}/indicator/{indicator}"
            f"?format=json&per_page=1"
        )
        data = self._http_get(url)
        if not data or not isinstance(data, list) or len(data) < 2:
            return None
        try:
            records = data[1]
            if not records:
                return None
            rec = records[0]
            value = rec.get("value", "?")
            year = rec.get("date", "?")
            ind_name = rec.get("indicator", {}).get("value", indicator)
            ctry_name = rec.get("country", {}).get("value", country)
            text = f"{ctry_name} {ind_name} {year}: {value}"
            return WorldDataItem(
                source="world_bank",
                topic=f"{country}/{indicator}",
                title=f"{ctry_name} {ind_name}",
                text=text,
                url="https://data.worldbank.org",
                raw=rec,
                category="market",
            )
        except Exception:
            return None

    # ─────────────────────────────────────────────────────────────────────
    # FRED (free, limited — Federal Reserve economic data)
    # ─────────────────────────────────────────────────────────────────────
    def fetch_fred(self, series_id: str = "GDP") -> Optional[WorldDataItem]:
        """Fetch latest value for a FRED series (no key needed for public endpoint)."""
        with self._lock:
            self._stats["fred_calls"] += 1
        # FRED's free CSV endpoint doesn't need a key for a single series download
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}&cosd=2023-01-01"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": self.USER_AGENT})
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8")
        except Exception:
            with self._lock:
                self._stats["errors"] += 1
            return None
        # Parse CSV — take last non-empty row
        lines = [ln for ln in body.strip().split("\n") if ln]
        if len(lines) < 2:
            return None
        last = lines[-1].split(",")
        if len(last) < 2:
            return None
        date = last[0]
        value = last[1]
        return WorldDataItem(
            source="fred",
            topic=series_id,
            title=f"FRED {series_id}",
            text=f"{series_id} on {date}: {value}",
            url=f"https://fred.stlouisfed.org/series/{series_id}",
            raw={"date": date, "value": value},
            category="market",
        )

    # ─────────────────────────────────────────────────────────────────────
    # Open Library (free, no key — books)
    # ─────────────────────────────────────────────────────────────────────
    def fetch_open_library(self, query: str, n: int = 3) -> List[WorldDataItem]:
        """Search Open Library for books matching a query."""
        with self._lock:
            self._stats["open_library_calls"] += 1
        safe = urllib.parse.quote(query)
        url = f"https://openlibrary.org/search.json?q={safe}&limit={n}"
        data = self._http_get(url)
        if not data:
            return []
        items: List[WorldDataItem] = []
        try:
            for doc in data.get("docs", [])[:n]:
                title = doc.get("title", "")
                authors = ", ".join(doc.get("author_name", [])[:3])
                first_pub = doc.get("first_publish_year", "")
                if not title:
                    continue
                items.append(WorldDataItem(
                    source="open_library",
                    topic=query,
                    title=title,
                    text=f"{title} by {authors} ({first_pub})",
                    url=f"https://openlibrary.org{doc.get('key', '')}",
                    raw={"authors": doc.get("author_name", []), "year": first_pub},
                    category="knowledge",
                ))
        except Exception:
            pass
        return items

    # ─────────────────────────────────────────────────────────────────────
    # Wikidata (free, no key — structured semantic data)
    # ─────────────────────────────────────────────────────────────────────
    def fetch_wikidata(self, query: str, n: int = 3) -> List[WorldDataItem]:
        """Search Wikidata for entities matching a query."""
        with self._lock:
            self._stats["wikidata_calls"] += 1
        safe = urllib.parse.quote(query)
        url = (
            f"https://www.wikidata.org/w/api.php?action=wbsearchentities"
            f"&search={safe}&language=en&format=json&limit={n}"
        )
        data = self._http_get(url)
        if not data:
            return []
        items: List[WorldDataItem] = []
        try:
            for ent in data.get("search", [])[:n]:
                label = ent.get("label", "")
                desc = ent.get("description", "")
                qid = ent.get("id", "")
                if not label:
                    continue
                items.append(WorldDataItem(
                    source="wikidata",
                    topic=query,
                    title=label,
                    text=f"{label}: {desc}",
                    url=f"https://www.wikidata.org/wiki/{qid}",
                    raw={"qid": qid, "desc": desc},
                    category="knowledge",
                ))
        except Exception:
            pass
        return items

    # ─────────────────────────────────────────────────────────────────────
    # DuckDuckGo Instant Answer (free, no key)
    # ─────────────────────────────────────────────────────────────────────
    def fetch_duckduckgo(self, query: str) -> Optional[WorldDataItem]:
        """Fetch DuckDuckGo instant answer for a query."""
        with self._lock:
            self._stats["duckduckgo_calls"] += 1
        safe = urllib.parse.quote(query)
        url = f"https://api.duckduckgo.com/?q={safe}&format=json&no_html=1&skip_disambig=1"
        data = self._http_get(url)
        if not data:
            return None
        abstract = data.get("AbstractText", "") or data.get("Abstract", "")
        if not abstract:
            return None
        return WorldDataItem(
            source="duckduckgo",
            topic=query,
            title=data.get("Heading", query),
            text=abstract[:800],
            url=data.get("AbstractURL", ""),
            raw={"type": data.get("Type", "")},
            category="knowledge",
        )

    # ─────────────────────────────────────────────────────────────────────
    # PubMed (free, no key — biomedical papers)
    # ─────────────────────────────────────────────────────────────────────
    def fetch_pubmed(self, query: str, n: int = 3) -> List[WorldDataItem]:
        """Search PubMed/NCBI for recent biomedical papers."""
        with self._lock:
            self._stats["pubmed_calls"] += 1
        safe = urllib.parse.quote(query)
        url = (
            f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            f"?db=pubmed&term={safe}&retmax={n}&retmode=json"
        )
        data = self._http_get(url)
        if not data:
            return []
        items: List[WorldDataItem] = []
        try:
            ids = data.get("esearchresult", {}).get("idlist", [])
            for pid in ids[:n]:
                items.append(WorldDataItem(
                    source="pubmed",
                    topic=query,
                    title=f"PubMed {pid}",
                    text=f"PubMed paper id {pid} matching query '{query}'",
                    url=f"https://pubmed.ncbi.nlm.nih.gov/{pid}/",
                    raw={"pubmed_id": pid},
                    category="knowledge",
                ))
        except Exception:
            pass
        return items

    # ─────────────────────────────────────────────────────────────────────
    # RSS (free, no key — BBC / Reuters / AP news)
    # ─────────────────────────────────────────────────────────────────────
    def fetch_rss(self, feed_url: str = "http://feeds.bbci.co.uk/news/world/rss.xml", n: int = 5) -> List[WorldDataItem]:
        """Fetch items from an RSS feed (BBC World News by default)."""
        with self._lock:
            self._stats["rss_calls"] += 1
        try:
            req = urllib.request.Request(feed_url, headers={"User-Agent": self.USER_AGENT})
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8", errors="replace")
        except Exception:
            with self._lock:
                self._stats["errors"] += 1
            return []
        import re as _re
        items: List[WorldDataItem] = []
        # Simple RSS 2.0 parsing
        entries = _re.findall(r"<item>(.*?)</item>", body, _re.DOTALL)
        for ent in entries[:n]:
            title_m = _re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", ent, _re.DOTALL)
            desc_m = _re.search(r"<description>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</description>", ent, _re.DOTALL)
            link_m = _re.search(r"<link>(.*?)</link>", ent, _re.DOTALL)
            if not title_m:
                continue
            title = title_m.group(1).strip()
            desc = (desc_m.group(1).strip() if desc_m else "")[:300]
            items.append(WorldDataItem(
                source="rss",
                topic=feed_url,
                title=title,
                text=f"{title} — {desc}",
                url=link_m.group(1).strip() if link_m else feed_url,
                raw={"feed": feed_url},
                category="user_input",
            ))
        return items

    # ─────────────────────────────────────────────────────────────────────
    # Universal search — answers a question from multiple sources
    # ─────────────────────────────────────────────────────────────────────
    def answer_question(self, question: str, n_per_source: int = 2) -> List[WorldDataItem]:
        """
        Try to answer a question by searching many free open-source APIs.
        Returns aggregated WorldDataItems — more sources = richer answer.
        """
        results: List[WorldDataItem] = []
        lower = question.lower()

        # 1. Wikipedia — always try for facts
        try:
            results.extend(self.search_wikipedia(question, n=n_per_source))
        except Exception:
            pass

        # 2. Wikidata — structured semantic data
        try:
            results.extend(self.fetch_wikidata(question, n=n_per_source))
        except Exception:
            pass

        # 3. DuckDuckGo — instant answers
        try:
            ddg = self.fetch_duckduckgo(question)
            if ddg:
                results.append(ddg)
        except Exception:
            pass

        # 4. News / world / politics
        if any(w in lower for w in ["news", "world", "politic", "election", "war",
                                      "crisis", "event", "today"]):
            try:
                results.extend(self.fetch_reddit("worldnews", n=n_per_source))
            except Exception:
                pass
            try:
                results.extend(self.fetch_rss(n=n_per_source))
            except Exception:
                pass

        # 5. Geopolitics — GDELT + REST Countries
        if any(w in lower for w in ["politic", "geopolit", "country", "war",
                                      "diplom", "treaty", "nation"]):
            try:
                results.extend(self.fetch_gdelt(question, n=n_per_source))
            except Exception:
                pass
            # Extract a country name heuristically
            country_hints = ["united states", "china", "russia", "uk", "france",
                             "germany", "japan", "india", "brazil", "canada"]
            for hint in country_hints:
                if hint in lower:
                    c = self.fetch_rest_countries(hint)
                    if c:
                        results.append(c)
                    break

        # 6. Markets — Yahoo + CoinGecko + World Bank + FRED
        if any(w in lower for w in ["price", "market", "stock", "trade", "btc",
                                      "eth", "bitcoin", "ethereum", "economy",
                                      "gdp", "inflation", "rate"]):
            symbols = []
            coin_ids = []
            if "btc" in lower or "bitcoin" in lower:
                symbols.append("BTC-USD")
                coin_ids.append("bitcoin")
            if "eth" in lower or "ethereum" in lower:
                symbols.append("ETH-USD")
                coin_ids.append("ethereum")
            for sym in symbols[:n_per_source]:
                item = self.fetch_yahoo_quote(sym)
                if item:
                    results.append(item)
            for cid in coin_ids[:n_per_source]:
                item = self.fetch_coingecko(cid)
                if item:
                    results.append(item)
            if any(w in lower for w in ["gdp", "economy", "indicator"]):
                wb = self.fetch_world_bank("US", "NY.GDP.MKTP.CD")
                if wb:
                    results.append(wb)

        # 7. Science / research — arXiv + PubMed + Open Library
        if any(w in lower for w in ["research", "paper", "study", "science",
                                      "journal", "academic", "theory"]):
            try:
                results.extend(self.fetch_arxiv(question, n=n_per_source))
            except Exception:
                pass
            if any(w in lower for w in ["medical", "health", "disease", "drug", "bio"]):
                try:
                    results.extend(self.fetch_pubmed(question, n=n_per_source))
                except Exception:
                    pass
            if any(w in lower for w in ["book", "author", "novel", "literature"]):
                try:
                    results.extend(self.fetch_open_library(question, n=n_per_source))
                except Exception:
                    pass

        # 8. Weather / location
        if any(w in lower for w in ["weather", "temperature", "climate", "forecast"]):
            try:
                w = self.fetch_open_meteo()
                if w:
                    results.append(w)
            except Exception:
                pass

        # 9. Natural events
        if any(w in lower for w in ["earthquake", "seismic", "quake"]):
            try:
                results.extend(self.fetch_usgs_earthquakes(n=n_per_source))
            except Exception:
                pass

        return results

    # ─────────────────────────────────────────────────────────────────────
    # Vault ingestion + ThoughtBus publishing
    # ─────────────────────────────────────────────────────────────────────
    def ingest_to_vault(self, items: List[WorldDataItem]) -> int:
        """Write items as cards into the vault and publish to ThoughtBus."""
        if not items:
            return 0
        ingested = 0
        for item in items:
            try:
                if self.vault is not None:
                    self.vault.ingest(
                        topic=f"world_data.{item.source}",
                        payload={
                            "title": item.title,
                            "text": item.text,
                            "url": item.url,
                            "topic": item.topic,
                            "category": item.category,
                            "raw": item.raw,
                        },
                        category=item.category,
                    )
                if self.thought_bus is not None:
                    try:
                        self.thought_bus.publish(
                            f"world_data.{item.source}",
                            {
                                "title": item.title,
                                "text": item.text[:200],
                                "url": item.url,
                                "topic": item.topic,
                            },
                            source="world_data_ingester",
                        )
                    except Exception:
                        pass
                ingested += 1
            except Exception as exc:
                logger.debug("ingest failed: %s", exc)
        with self._lock:
            self._stats["items_ingested"] += ingested
        return ingested

    # ─────────────────────────────────────────────────────────────────────
    # Status
    # ─────────────────────────────────────────────────────────────────────
    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._stats)


# ─────────────────────────────────────────────────────────────────────────────
# Singleton
# ─────────────────────────────────────────────────────────────────────────────

_singleton: Optional[WorldDataIngester] = None
_singleton_lock = threading.Lock()


def get_world_data_ingester(**kwargs) -> WorldDataIngester:
    global _singleton
    with _singleton_lock:
        if _singleton is None:
            _singleton = WorldDataIngester(**kwargs)
        return _singleton


def reset_world_data_ingester() -> None:
    global _singleton
    with _singleton_lock:
        _singleton = None
