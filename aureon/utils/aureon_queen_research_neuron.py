#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                          ║
║     👑📰🔬 QUEEN RESEARCH NEURON - News & Knowledge Intelligence System 🔬📰👑           ║
║                                                                                          ║
║     "The Queen gathers wisdom from the world's news streams and knowledge bases"         ║
║                                                                                          ║
║     SOURCES:                                                                             ║
║       • 📰 World News API - Real-time global news sentiment                              ║
║       • 📚 Wikipedia API - Historical context & knowledge                                ║
║       • 📊 RSS Feeds - Financial news streams (Yahoo, Reuters, Bloomberg)                ║
║       • 🐦 Social Pulse - Aggregated social sentiment                                    ║
║                                                                                          ║
║     CAPABILITIES:                                                                        ║
║       • Real-time market sentiment analysis                                              ║
║       • Historical context research for trading decisions                                ║
║       • Event-driven news alerting                                                       ║
║       • Knowledge graph building for market entities                                     ║
║                                                                                          ║
║     Gary Leckey & Tina Brown | January 2026                                              ║
║     "Knowledge is power. Real-time knowledge is LIBERATION."                             ║
║                                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations
from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)

import sys
import os
import json
import asyncio
import aiohttp
import time
import logging
import hashlib
import re
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple
from collections import deque
from enum import Enum
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════
# WINDOWS UTF-8 FIX
# ═══════════════════════════════════════════════════════════════════════════
if sys.platform == 'win32' and sys.stdout is sys.__stdout__ and sys.stdout.isatty():
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        import io
        def _is_utf8_wrapper(stream):
            return (isinstance(stream, io.TextIOWrapper) and 
                    hasattr(stream, 'encoding') and stream.encoding and
                    stream.encoding.lower().replace('-', '') == 'utf8')
        if hasattr(sys.stdout, 'buffer') and not _is_utf8_wrapper(sys.stdout):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        # Skip stderr wrapping (causes Windows exit errors)
    except Exception:
        pass

# ═══════════════════════════════════════════════════════════════════════════
# IMPORTS - ThoughtBus Integration
# ═══════════════════════════════════════════════════════════════════════════
try:
    from aureon.core.aureon_thought_bus import ThoughtBus, Thought
    THOUGHT_BUS_AVAILABLE = True
except ImportError:
    ThoughtBus = None
    Thought = None
    THOUGHT_BUS_AVAILABLE = False

# Existing News Feed integration
try:
    from aureon.data_feeds.aureon_news_feed import NewsFeed, NewsFeedConfig, NewsArticle, create_news_feed
    NEWS_FEED_AVAILABLE = True
except ImportError:
    NewsFeed = None
    NewsFeedConfig = None
    NewsArticle = None
    create_news_feed = None
    NEWS_FEED_AVAILABLE = False

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS - Sacred Research Frequencies
# ═══════════════════════════════════════════════════════════════════════════
PHI = (1 + 5 ** 0.5) / 2  # Golden Ratio
RESEARCH_FREQUENCY_HZ = 741.0  # Awakening intuition (Solfeggio SOL)
KNOWLEDGE_FREQUENCY_HZ = 852.0  # Third eye (Solfeggio LA)

# Wikipedia API endpoints
WIKIPEDIA_API_BASE = "https://en.wikipedia.org/api/rest_v1"
WIKIPEDIA_SEARCH_API = "https://en.wikipedia.org/w/api.php"

# RSS Feed sources for financial news
RSS_FEEDS = {
    "yahoo_finance": "https://finance.yahoo.com/news/rssindex",
    "reuters_business": "https://www.rss.reuters.com/news/businessNews",
    "coindesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "cointelegraph": "https://cointelegraph.com/rss",
    "seeking_alpha": "https://seekingalpha.com/market_currents.xml",
}

# Market-relevant Wikipedia topics for background research
MARKET_WIKI_TOPICS = {
    "crypto": [
        "Bitcoin", "Ethereum", "Cryptocurrency", "Blockchain",
        "Decentralized_finance", "Cryptocurrency_exchange", "Stablecoin"
    ],
    "finance": [
        "Stock_market", "Federal_Reserve", "Interest_rate",
        "Inflation", "Quantitative_easing", "Market_manipulation"
    ],
    "trading": [
        "Algorithmic_trading", "High-frequency_trading", "Market_maker",
        "Technical_analysis", "Fundamental_analysis"
    ],
    "entities": [
        "BlackRock", "Vanguard_Group", "Jane_Street_Capital",
        "Citadel_LLC", "MicroStrategy", "Grayscale_Investments"
    ]
}


# ═══════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════

class ResearchType(Enum):
    """Types of research the Queen can conduct."""
    NEWS_SENTIMENT = "news_sentiment"
    WIKI_CONTEXT = "wiki_context"
    RSS_SCAN = "rss_scan"
    ENTITY_RESEARCH = "entity_research"
    EVENT_ANALYSIS = "event_analysis"
    TREND_ANALYSIS = "trend_analysis"


@dataclass
class WikipediaArticle:
    """Structured Wikipedia article data."""
    title: str
    extract: str  # Plain text summary
    page_id: int
    url: str
    categories: List[str] = field(default_factory=list)
    links: List[str] = field(default_factory=list)
    last_modified: str = ""
    word_count: int = 0
    
    @property
    def summary(self) -> str:
        """First 500 chars of extract."""
        return self.extract[:500] + "..." if len(self.extract) > 500 else self.extract
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RSSNewsItem:
    """RSS news item structure."""
    title: str
    link: str
    description: str
    published: str
    source: str
    guid: str = ""
    
    @property
    def age_hours(self) -> float:
        """Approximate age in hours."""
        try:
            # Try common RSS date formats
            for fmt in ["%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%dT%H:%M:%S%z"]:
                try:
                    pub_dt = datetime.strptime(self.published, fmt)
                    return (datetime.now(pub_dt.tzinfo) - pub_dt).total_seconds() / 3600
                except:
                    continue
            return 24.0  # Default to 24h if parse fails
        except:
            return 24.0


@dataclass
class ResearchResult:
    """Result from Queen's research operations."""
    research_type: ResearchType
    query: str
    timestamp: float
    success: bool
    data: Dict[str, Any]
    sentiment_score: float = 0.0  # -1 to 1
    confidence: float = 0.0  # 0 to 1
    relevance_score: float = 0.0  # 0 to 1
    sources_used: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "research_type": self.research_type.value,
            "query": self.query,
            "timestamp": self.timestamp,
            "success": self.success,
            "data": self.data,
            "sentiment_score": self.sentiment_score,
            "confidence": self.confidence,
            "relevance_score": self.relevance_score,
            "sources_used": self.sources_used,
            "error_message": self.error_message
        }


@dataclass
class MarketInsight:
    """Actionable insight derived from research."""
    timestamp: float
    insight_type: str  # 'bullish', 'bearish', 'neutral', 'alert', 'context'
    symbol: Optional[str]
    headline: str
    summary: str
    confidence: float
    source: str
    supporting_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════
# WIKIPEDIA RESEARCH CLIENT
# ═══════════════════════════════════════════════════════════════════════════

class WikipediaResearcher:
    """
    🔬📚 Wikipedia Research Client
    
    Provides the Queen with historical context and background knowledge
    for market entities, events, and concepts.
    """
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.cache: Dict[str, WikipediaArticle] = {}
        self.cache_ttl_hours: int = 24  # Cache articles for 24 hours
        self.cache_timestamps: Dict[str, float] = {}
        
        # User-Agent required by Wikipedia API
        self.headers = {
            "User-Agent": "AureonQueenResearch/1.0 (https://github.com/RA-CONSULTING/aureon-trading; research@aureon.ai) aiohttp/3.x",
            "Accept": "application/json"
        }
        
        # Metrics
        self.metrics = {
            "api_calls": 0,
            "cache_hits": 0,
            "errors": 0,
            "articles_fetched": 0
        }
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers=self.headers)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def _is_cache_valid(self, title: str) -> bool:
        """Check if cached article is still valid."""
        if title not in self.cache_timestamps:
            return False
        age_hours = (time.time() - self.cache_timestamps[title]) / 3600
        return age_hours < self.cache_ttl_hours
    
    async def _ensure_session(self):
        """Ensure aiohttp session exists."""
        if self.session is None:
            self.session = aiohttp.ClientSession(headers=self.headers)
    
    async def search(self, query: str, limit: int = 5) -> List[str]:
        """
        Search Wikipedia for articles matching query.
        
        Returns list of article titles.
        """
        await self._ensure_session()
        
        params = {
            "action": "opensearch",
            "search": query,
            "limit": limit,
            "namespace": 0,
            "format": "json"
        }
        
        try:
            async with self.session.get(WIKIPEDIA_SEARCH_API, params=params) as resp:
                self.metrics["api_calls"] += 1
                if resp.status == 200:
                    data = await resp.json()
                    return data[1] if len(data) > 1 else []
                else:
                    self.metrics["errors"] += 1
                    return []
        except Exception as e:
            logger.error(f"Wikipedia search error: {e}")
            self.metrics["errors"] += 1
            return []
    
    async def get_article(self, title: str) -> Optional[WikipediaArticle]:
        """
        Fetch Wikipedia article by title.
        
        Uses REST API for cleaner extracts.
        """
        # Check cache first
        cache_key = title.lower().replace(" ", "_")
        if cache_key in self.cache and self._is_cache_valid(cache_key):
            self.metrics["cache_hits"] += 1
            return self.cache[cache_key]
        
        await self._ensure_session()
        
        # URL-encode the title
        encoded_title = title.replace(" ", "_")
        url = f"{WIKIPEDIA_API_BASE}/page/summary/{encoded_title}"
        
        try:
            async with self.session.get(url) as resp:
                self.metrics["api_calls"] += 1
                
                if resp.status == 200:
                    data = await resp.json()
                    
                    article = WikipediaArticle(
                        title=data.get("title", title),
                        extract=data.get("extract", ""),
                        page_id=data.get("pageid", 0),
                        url=data.get("content_urls", {}).get("desktop", {}).get("page", ""),
                        last_modified=data.get("timestamp", ""),
                        word_count=len(data.get("extract", "").split())
                    )
                    
                    # Cache the article
                    self.cache[cache_key] = article
                    self.cache_timestamps[cache_key] = time.time()
                    self.metrics["articles_fetched"] += 1
                    
                    return article
                elif resp.status == 404:
                    logger.debug(f"Wikipedia article not found: {title}")
                    return None
                else:
                    self.metrics["errors"] += 1
                    return None
                    
        except Exception as e:
            logger.error(f"Wikipedia article fetch error: {e}")
            self.metrics["errors"] += 1
            return None
    
    async def get_article_full(self, title: str) -> Optional[Dict[str, Any]]:
        """
        Fetch full Wikipedia article with categories and links.
        
        Uses MediaWiki API for more detailed data.
        """
        await self._ensure_session()
        
        params = {
            "action": "query",
            "titles": title,
            "prop": "extracts|categories|links|info",
            "exintro": True,
            "explaintext": True,
            "cllimit": 20,
            "pllimit": 20,
            "format": "json"
        }
        
        try:
            async with self.session.get(WIKIPEDIA_SEARCH_API, params=params) as resp:
                self.metrics["api_calls"] += 1
                
                if resp.status == 200:
                    data = await resp.json()
                    pages = data.get("query", {}).get("pages", {})
                    
                    for page_id, page_data in pages.items():
                        if page_id == "-1":
                            return None
                        
                        return {
                            "title": page_data.get("title", title),
                            "page_id": int(page_id),
                            "extract": page_data.get("extract", ""),
                            "categories": [c["title"].replace("Category:", "") 
                                         for c in page_data.get("categories", [])],
                            "links": [l["title"] for l in page_data.get("links", [])],
                            "last_modified": page_data.get("touched", ""),
                            "url": f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
                        }
                    
                    return None
                else:
                    self.metrics["errors"] += 1
                    return None
                    
        except Exception as e:
            logger.error(f"Wikipedia full article fetch error: {e}")
            self.metrics["errors"] += 1
            return None
    
    async def research_entity(self, entity_name: str) -> Dict[str, Any]:
        """
        Research a market entity (company, person, concept).
        
        Returns comprehensive background information.
        """
        result = {
            "entity": entity_name,
            "found": False,
            "summary": "",
            "categories": [],
            "related_articles": [],
            "key_facts": []
        }
        
        # Search for the entity
        search_results = await self.search(entity_name, limit=3)
        
        if not search_results:
            return result
        
        # Get the most relevant article
        article = await self.get_article(search_results[0])
        
        if article:
            result["found"] = True
            result["summary"] = article.extract
            result["url"] = article.url
            
            # Get full article for more details
            full_data = await self.get_article_full(search_results[0])
            if full_data:
                result["categories"] = full_data.get("categories", [])[:10]
                result["related_articles"] = full_data.get("links", [])[:10]
        
        # Also search for related terms
        for term in search_results[1:]:
            related = await self.get_article(term)
            if related:
                result["related_articles"].append({
                    "title": related.title,
                    "summary": related.summary[:200]
                })
        
        return result
    
    async def get_market_context(self, symbol: str) -> Dict[str, Any]:
        """
        Get Wikipedia context relevant to a trading symbol.
        
        Maps symbols to relevant Wikipedia articles.
        """
        # Symbol to Wikipedia topic mapping
        symbol_map = {
            "BTC": ["Bitcoin", "Cryptocurrency"],
            "ETH": ["Ethereum", "Smart_contract"],
            "SOL": ["Solana_(blockchain)"],
            "XRP": ["Ripple_(payment_protocol)", "XRP"],
            "ADA": ["Cardano_(blockchain)"],
            "DOGE": ["Dogecoin"],
            "AAPL": ["Apple_Inc."],
            "MSFT": ["Microsoft"],
            "GOOGL": ["Google", "Alphabet_Inc."],
            "AMZN": ["Amazon_(company)"],
            "TSLA": ["Tesla,_Inc."],
            "NVDA": ["Nvidia"],
        }
        
        # Extract base symbol
        base_symbol = symbol.upper().replace("/USD", "").replace("USDT", "").replace("USD", "")
        
        topics = symbol_map.get(base_symbol, [])
        
        context = {
            "symbol": symbol,
            "topics": [],
            "summary": "",
            "related_concepts": []
        }
        
        for topic in topics[:2]:  # Limit to 2 articles
            article = await self.get_article(topic)
            if article:
                context["topics"].append({
                    "title": article.title,
                    "summary": article.summary,
                    "url": article.url
                })
        
        if context["topics"]:
            context["summary"] = context["topics"][0]["summary"]
        
        return context


# ═══════════════════════════════════════════════════════════════════════════
# RSS FEED SCANNER
# ═══════════════════════════════════════════════════════════════════════════

class RSSFeedScanner:
    """
    📰 RSS Feed Scanner
    
    Monitors financial news RSS feeds for market-moving events.
    """
    
    def __init__(self, feeds: Dict[str, str] = None):
        self.feeds = feeds or RSS_FEEDS
        self.session: Optional[aiohttp.ClientSession] = None
        self.seen_guids: set = set()  # Track seen items to avoid duplicates
        self.max_seen_history: int = 1000
        
        # Metrics
        self.metrics = {
            "feeds_checked": 0,
            "items_fetched": 0,
            "errors": 0
        }
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _ensure_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()
    
    def _parse_rss_xml(self, xml_text: str, source: str) -> List[RSSNewsItem]:
        """Parse RSS XML into news items."""
        items = []
        
        try:
            # Simple regex-based parsing (avoids XML library dependencies)
            item_pattern = r'<item>(.*?)</item>'
            title_pattern = r'<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>'
            link_pattern = r'<link>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</link>'
            desc_pattern = r'<description>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</description>'
            pub_pattern = r'<pubDate>(.*?)</pubDate>'
            guid_pattern = r'<guid[^>]*>(.*?)</guid>'
            
            for item_match in re.finditer(item_pattern, xml_text, re.DOTALL):
                item_text = item_match.group(1)
                
                title_match = re.search(title_pattern, item_text, re.DOTALL)
                link_match = re.search(link_pattern, item_text, re.DOTALL)
                desc_match = re.search(desc_pattern, item_text, re.DOTALL)
                pub_match = re.search(pub_pattern, item_text, re.DOTALL)
                guid_match = re.search(guid_pattern, item_text, re.DOTALL)
                
                title = title_match.group(1).strip() if title_match else ""
                link = link_match.group(1).strip() if link_match else ""
                description = desc_match.group(1).strip() if desc_match else ""
                published = pub_match.group(1).strip() if pub_match else ""
                guid = guid_match.group(1).strip() if guid_match else link
                
                # Clean HTML from description
                description = re.sub(r'<[^>]+>', '', description)
                
                if title and guid not in self.seen_guids:
                    items.append(RSSNewsItem(
                        title=title,
                        link=link,
                        description=description[:500],
                        published=published,
                        source=source,
                        guid=guid
                    ))
                    self.seen_guids.add(guid)
                    
                    # Limit seen history
                    if len(self.seen_guids) > self.max_seen_history:
                        self.seen_guids = set(list(self.seen_guids)[-500:])
            
        except Exception as e:
            logger.error(f"RSS parse error: {e}")
        
        return items
    
    async def fetch_feed(self, feed_name: str, feed_url: str) -> List[RSSNewsItem]:
        """Fetch and parse a single RSS feed."""
        await self._ensure_session()
        
        try:
            headers = {
                "User-Agent": "AureonQueenResearch/1.0"
            }
            async with self.session.get(feed_url, headers=headers, timeout=10) as resp:
                self.metrics["feeds_checked"] += 1
                
                if resp.status == 200:
                    text = await resp.text()
                    items = self._parse_rss_xml(text, feed_name)
                    self.metrics["items_fetched"] += len(items)
                    return items
                else:
                    self.metrics["errors"] += 1
                    return []
                    
        except Exception as e:
            logger.debug(f"RSS feed error ({feed_name}): {e}")
            self.metrics["errors"] += 1
            return []
    
    async def scan_all_feeds(self) -> List[RSSNewsItem]:
        """Scan all configured RSS feeds."""
        all_items = []
        
        tasks = [
            self.fetch_feed(name, url) 
            for name, url in self.feeds.items()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                all_items.extend(result)
        
        # Sort by published date (newest first)
        all_items.sort(key=lambda x: x.published, reverse=True)
        
        return all_items
    
    def filter_by_keywords(self, items: List[RSSNewsItem], keywords: List[str]) -> List[RSSNewsItem]:
        """Filter RSS items by keywords."""
        filtered = []
        keywords_lower = [k.lower() for k in keywords]
        
        for item in items:
            text_lower = (item.title + " " + item.description).lower()
            if any(kw in text_lower for kw in keywords_lower):
                filtered.append(item)
        
        return filtered


# ═══════════════════════════════════════════════════════════════════════════
# QUEEN RESEARCH NEURON - Main Intelligence System
# ═══════════════════════════════════════════════════════════════════════════

class QueenResearchNeuron:
    """
    👑📰🔬 QUEEN RESEARCH NEURON
    
    The Queen's comprehensive research and intelligence gathering system.
    Combines multiple data sources to provide market insights.
    
    Sources:
    - News APIs (World News, RSS feeds)
    - Knowledge bases (Wikipedia)
    - Sentiment analysis
    - Entity research
    """
    
    def __init__(
        self,
        news_api_key: Optional[str] = None,
        thought_bus: Optional['ThoughtBus'] = None,
        state_file: str = "queen_research_state.json"
    ):
        """
        Initialize the Research Neuron.
        
        Args:
            news_api_key: API key for World News API (optional)
            thought_bus: ThoughtBus for publishing insights
            state_file: Path to persist research state
        """
        self.news_api_key = news_api_key or os.environ.get("WORLD_NEWS_API_KEY", "")
        self.thought_bus = thought_bus
        self.state_file = state_file
        
        # Initialize sub-systems
        self.wiki_researcher = WikipediaResearcher()
        self.rss_scanner = RSSFeedScanner()
        self.news_feed: Optional[NewsFeed] = None
        
        # Initialize news feed if available
        if NEWS_FEED_AVAILABLE and self.news_api_key:
            config = NewsFeedConfig(api_key=self.news_api_key)
            self.news_feed = NewsFeed(config, thought_bus)
        
        # State
        self.research_cache: Dict[str, ResearchResult] = {}
        self.insights_history: deque = deque(maxlen=100)
        self.last_research_time: Dict[str, float] = {}
        
        # Configuration
        self.cache_ttl_minutes: int = 30
        self.min_research_interval_seconds: int = 60
        
        # Market-relevant keywords for filtering
        self.market_keywords = [
            "bitcoin", "ethereum", "cryptocurrency", "crypto",
            "stock market", "federal reserve", "fed", "interest rate",
            "inflation", "recession", "trading", "market",
            "blackrock", "grayscale", "etf", "sec"
        ]
        
        # Sentiment keywords for scoring
        self.bullish_keywords = [
            "surge", "rally", "soar", "gain", "bullish", "optimistic",
            "growth", "record high", "buy", "accumulate", "moon"
        ]
        self.bearish_keywords = [
            "crash", "plunge", "dump", "sell-off", "bearish", "pessimistic",
            "decline", "drop", "fear", "panic", "collapse", "warning"
        ]
        
        # Metrics
        self.metrics = {
            "total_researches": 0,
            "news_queries": 0,
            "wiki_queries": 0,
            "rss_scans": 0,
            "insights_generated": 0,
            "errors": 0
        }
        
        # Load state
        self._load_state()
        
        logger.info("👑📰🔬 QueenResearchNeuron initialized")
    
    def _load_state(self):
        """Load persisted state."""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    self.metrics.update(state.get("metrics", {}))
                    logger.debug(f"Loaded research state from {self.state_file}")
        except Exception as e:
            logger.warning(f"Could not load research state: {e}")
    
    def _save_state(self):
        """Persist state to file."""
        try:
            state = {
                "metrics": self.metrics,
                "last_save": datetime.now().isoformat()
            }
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save research state: {e}")
    
    def _publish_thought(self, topic: str, payload: Dict[str, Any], meta: Optional[Dict] = None):
        """Publish a thought to the ThoughtBus."""
        if self.thought_bus and THOUGHT_BUS_AVAILABLE and Thought:
            thought = Thought(
                source="queen_research_neuron",
                topic=topic,
                payload=payload,
                meta=meta or {}
            )
            self.thought_bus.publish(thought)
            return thought.id
        return None
    
    def _calculate_sentiment(self, text: str) -> float:
        """
        Calculate sentiment score from text.
        
        Returns:
            Score from -1 (bearish) to 1 (bullish)
        """
        text_lower = text.lower()
        
        bullish_count = sum(1 for kw in self.bullish_keywords if kw in text_lower)
        bearish_count = sum(1 for kw in self.bearish_keywords if kw in text_lower)
        
        total = bullish_count + bearish_count
        if total == 0:
            return 0.0
        
        return (bullish_count - bearish_count) / total
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is still valid."""
        if cache_key not in self.research_cache:
            return False
        cached = self.research_cache[cache_key]
        age_minutes = (time.time() - cached.timestamp) / 60
        return age_minutes < self.cache_ttl_minutes
    
    # ═══════════════════════════════════════════════════════════════════════
    # NEWS RESEARCH METHODS
    # ═══════════════════════════════════════════════════════════════════════
    
    async def research_news(self, query: Optional[str] = None) -> ResearchResult:
        """
        Research current news sentiment.
        
        Args:
            query: Optional specific query (default: market keywords)
        
        Returns:
            ResearchResult with news analysis
        """
        cache_key = f"news:{query or 'market'}"
        
        if self._is_cache_valid(cache_key):
            return self.research_cache[cache_key]
        
        self.metrics["news_queries"] += 1
        self.metrics["total_researches"] += 1
        
        result_data = {
            "articles": [],
            "sentiment_analysis": {},
            "signals": {},
            "top_headlines": []
        }
        
        sources_used = []
        overall_sentiment = 0.0
        confidence = 0.0
        
        try:
            # Use World News API if available
            if self.news_feed:
                async with aiohttp.ClientSession():
                    articles = await self.news_feed.fetch_market_news()
                    
                    if articles:
                        sentiment_analysis = self.news_feed.analyze_sentiment_aggregate(articles)
                        signals = self.news_feed.extract_market_signals(articles)
                        
                        result_data["articles"] = len(articles)
                        result_data["sentiment_analysis"] = sentiment_analysis
                        result_data["signals"] = signals
                        result_data["top_headlines"] = [
                            {"title": a.title[:100], "sentiment": a.sentiment}
                            for a in sorted(articles, key=lambda x: abs(x.sentiment), reverse=True)[:5]
                        ]
                        
                        overall_sentiment = sentiment_analysis.get("average_sentiment", 0.0)
                        confidence = sentiment_analysis.get("confidence", 0.0)
                        sources_used.append("world_news_api")
            
            # Also scan RSS feeds
            async with self.rss_scanner:
                rss_items = await self.rss_scanner.scan_all_feeds()
                
                if rss_items:
                    # Filter to market-relevant items
                    filtered = self.rss_scanner.filter_by_keywords(
                        rss_items, 
                        self.market_keywords
                    )
                    
                    if filtered:
                        # Calculate RSS sentiment
                        rss_sentiments = [self._calculate_sentiment(item.title + " " + item.description) 
                                         for item in filtered[:20]]
                        rss_avg_sentiment = sum(rss_sentiments) / len(rss_sentiments) if rss_sentiments else 0
                        
                        result_data["rss_items"] = len(filtered)
                        result_data["rss_sentiment"] = rss_avg_sentiment
                        result_data["rss_headlines"] = [
                            {"title": item.title[:100], "source": item.source}
                            for item in filtered[:5]
                        ]
                        
                        # Blend sentiments if we have both sources
                        if sources_used:
                            overall_sentiment = (overall_sentiment + rss_avg_sentiment) / 2
                        else:
                            overall_sentiment = rss_avg_sentiment
                            confidence = min(1.0, len(filtered) / 10)
                        
                        sources_used.append("rss_feeds")
            
            result = ResearchResult(
                research_type=ResearchType.NEWS_SENTIMENT,
                query=query or "market_news",
                timestamp=time.time(),
                success=True,
                data=result_data,
                sentiment_score=overall_sentiment,
                confidence=confidence,
                relevance_score=0.8 if sources_used else 0.0,
                sources_used=sources_used
            )
            
        except Exception as e:
            logger.error(f"News research error: {e}")
            self.metrics["errors"] += 1
            result = ResearchResult(
                research_type=ResearchType.NEWS_SENTIMENT,
                query=query or "market_news",
                timestamp=time.time(),
                success=False,
                data={},
                error_message=str(e)
            )
        
        # Cache result
        self.research_cache[cache_key] = result
        
        # Publish thought
        if result.success:
            articles_count = result_data.get("articles", 0)
            if isinstance(articles_count, list):
                articles_count = len(articles_count)
            rss_count = result_data.get("rss_items", 0)
            if isinstance(rss_count, list):
                rss_count = len(rss_count)
            
            self._publish_thought("research.news", {
                "sentiment": overall_sentiment,
                "confidence": confidence,
                "sources": sources_used,
                "articles_analyzed": articles_count + rss_count
            })
        
        return result
    
    # ═══════════════════════════════════════════════════════════════════════
    # WIKIPEDIA RESEARCH METHODS
    # ═══════════════════════════════════════════════════════════════════════
    
    async def research_topic(self, topic: str) -> ResearchResult:
        """
        Research a topic using Wikipedia.
        
        Args:
            topic: Topic to research
        
        Returns:
            ResearchResult with Wikipedia data
        """
        cache_key = f"wiki:{topic.lower()}"
        
        if self._is_cache_valid(cache_key):
            return self.research_cache[cache_key]
        
        self.metrics["wiki_queries"] += 1
        self.metrics["total_researches"] += 1
        
        try:
            async with self.wiki_researcher:
                # Search for the topic
                search_results = await self.wiki_researcher.search(topic, limit=3)
                
                if not search_results:
                    return ResearchResult(
                        research_type=ResearchType.WIKI_CONTEXT,
                        query=topic,
                        timestamp=time.time(),
                        success=False,
                        data={"message": "No Wikipedia articles found"},
                        error_message="No results found"
                    )
                
                # Get the main article
                article = await self.wiki_researcher.get_article(search_results[0])
                
                if not article:
                    return ResearchResult(
                        research_type=ResearchType.WIKI_CONTEXT,
                        query=topic,
                        timestamp=time.time(),
                        success=False,
                        data={"message": "Could not fetch article"},
                        error_message="Article fetch failed"
                    )
                
                # Get related articles
                related = []
                for title in search_results[1:3]:
                    rel_article = await self.wiki_researcher.get_article(title)
                    if rel_article:
                        related.append({
                            "title": rel_article.title,
                            "summary": rel_article.summary
                        })
                
                result_data = {
                    "title": article.title,
                    "summary": article.extract,
                    "url": article.url,
                    "word_count": article.word_count,
                    "related_articles": related,
                    "search_results": search_results
                }
                
                result = ResearchResult(
                    research_type=ResearchType.WIKI_CONTEXT,
                    query=topic,
                    timestamp=time.time(),
                    success=True,
                    data=result_data,
                    confidence=0.9,
                    relevance_score=1.0 if article.word_count > 100 else 0.5,
                    sources_used=["wikipedia"]
                )
                
                # Cache result
                self.research_cache[cache_key] = result
                
                # Publish thought
                self._publish_thought("research.wiki", {
                    "topic": topic,
                    "title": article.title,
                    "summary": article.summary[:200]
                })
                
                return result
                
        except Exception as e:
            logger.error(f"Wikipedia research error: {e}")
            self.metrics["errors"] += 1
            return ResearchResult(
                research_type=ResearchType.WIKI_CONTEXT,
                query=topic,
                timestamp=time.time(),
                success=False,
                data={},
                error_message=str(e)
            )
    
    async def research_entity(self, entity_name: str) -> ResearchResult:
        """
        Research a market entity (company, person, etc.).
        
        Args:
            entity_name: Name of entity to research
        
        Returns:
            ResearchResult with entity information
        """
        cache_key = f"entity:{entity_name.lower()}"
        
        if self._is_cache_valid(cache_key):
            return self.research_cache[cache_key]
        
        self.metrics["wiki_queries"] += 1
        self.metrics["total_researches"] += 1
        
        try:
            async with self.wiki_researcher:
                entity_data = await self.wiki_researcher.research_entity(entity_name)
                
                result = ResearchResult(
                    research_type=ResearchType.ENTITY_RESEARCH,
                    query=entity_name,
                    timestamp=time.time(),
                    success=entity_data.get("found", False),
                    data=entity_data,
                    confidence=0.85 if entity_data.get("found") else 0.0,
                    relevance_score=1.0 if entity_data.get("found") else 0.0,
                    sources_used=["wikipedia"] if entity_data.get("found") else []
                )
                
                # Cache result
                self.research_cache[cache_key] = result
                
                return result
                
        except Exception as e:
            logger.error(f"Entity research error: {e}")
            self.metrics["errors"] += 1
            return ResearchResult(
                research_type=ResearchType.ENTITY_RESEARCH,
                query=entity_name,
                timestamp=time.time(),
                success=False,
                data={},
                error_message=str(e)
            )
    
    async def get_symbol_context(self, symbol: str) -> ResearchResult:
        """
        Get background context for a trading symbol.
        
        Args:
            symbol: Trading symbol (e.g., 'BTC/USD', 'AAPL')
        
        Returns:
            ResearchResult with symbol context
        """
        cache_key = f"symbol:{symbol.upper()}"
        
        if self._is_cache_valid(cache_key):
            return self.research_cache[cache_key]
        
        self.metrics["wiki_queries"] += 1
        self.metrics["total_researches"] += 1
        
        try:
            async with self.wiki_researcher:
                context = await self.wiki_researcher.get_market_context(symbol)
                
                result = ResearchResult(
                    research_type=ResearchType.WIKI_CONTEXT,
                    query=symbol,
                    timestamp=time.time(),
                    success=bool(context.get("topics")),
                    data=context,
                    confidence=0.8 if context.get("topics") else 0.0,
                    relevance_score=1.0 if context.get("topics") else 0.0,
                    sources_used=["wikipedia"] if context.get("topics") else []
                )
                
                # Cache result
                self.research_cache[cache_key] = result
                
                return result
                
        except Exception as e:
            logger.error(f"Symbol context error: {e}")
            self.metrics["errors"] += 1
            return ResearchResult(
                research_type=ResearchType.WIKI_CONTEXT,
                query=symbol,
                timestamp=time.time(),
                success=False,
                data={},
                error_message=str(e)
            )
    
    # ═══════════════════════════════════════════════════════════════════════
    # COMPREHENSIVE RESEARCH
    # ═══════════════════════════════════════════════════════════════════════
    
    async def comprehensive_research(
        self, 
        symbol: Optional[str] = None,
        include_news: bool = True,
        include_wiki: bool = True,
        include_rss: bool = True
    ) -> Dict[str, Any]:
        """
        Conduct comprehensive research combining all sources.
        
        Args:
            symbol: Optional trading symbol for context
            include_news: Include news API research
            include_wiki: Include Wikipedia research
            include_rss: Include RSS feed scanning
        
        Returns:
            Comprehensive research report
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "news_sentiment": None,
            "wiki_context": None,
            "rss_headlines": None,
            "overall_sentiment": 0.0,
            "confidence": 0.0,
            "insights": [],
            "recommended_action": "HOLD"
        }
        
        tasks = []
        
        # News research
        if include_news:
            tasks.append(("news", self.research_news()))
        
        # Wikipedia context for symbol
        if include_wiki and symbol:
            tasks.append(("wiki", self.get_symbol_context(symbol)))
        
        # Execute tasks
        results = {}
        for name, task in tasks:
            try:
                results[name] = await task
            except Exception as e:
                logger.error(f"Research task '{name}' failed: {e}")
        
        # Process news results
        if "news" in results and results["news"].success:
            news_result = results["news"]
            report["news_sentiment"] = {
                "score": news_result.sentiment_score,
                "confidence": news_result.confidence,
                "data": news_result.data
            }
            
            # Generate insight from news
            if abs(news_result.sentiment_score) >= 0.3:
                insight_type = "bullish" if news_result.sentiment_score > 0 else "bearish"
                report["insights"].append(MarketInsight(
                    timestamp=time.time(),
                    insight_type=insight_type,
                    symbol=symbol,
                    headline=f"News sentiment is {insight_type.upper()}",
                    summary=f"Aggregate news sentiment: {news_result.sentiment_score:.2f}",
                    confidence=news_result.confidence,
                    source="news_analysis"
                ).to_dict())
        
        # Process Wikipedia results
        if "wiki" in results and results["wiki"].success:
            wiki_result = results["wiki"]
            report["wiki_context"] = wiki_result.data
        
        # Calculate overall sentiment
        sentiment_scores = []
        confidences = []
        
        if report["news_sentiment"]:
            sentiment_scores.append(report["news_sentiment"]["score"])
            confidences.append(report["news_sentiment"]["confidence"])
        
        if sentiment_scores:
            report["overall_sentiment"] = sum(sentiment_scores) / len(sentiment_scores)
            report["confidence"] = sum(confidences) / len(confidences)
        
        # Determine recommended action
        if report["overall_sentiment"] >= 0.3 and report["confidence"] >= 0.5:
            report["recommended_action"] = "BUY"
        elif report["overall_sentiment"] <= -0.3 and report["confidence"] >= 0.5:
            report["recommended_action"] = "SELL"
        else:
            report["recommended_action"] = "HOLD"
        
        # Publish comprehensive thought
        self._publish_thought("research.comprehensive", {
            "symbol": symbol,
            "overall_sentiment": report["overall_sentiment"],
            "confidence": report["confidence"],
            "recommended_action": report["recommended_action"],
            "insights_count": len(report["insights"])
        })
        
        # Save state
        self._save_state()
        
        return report
    
    # ═══════════════════════════════════════════════════════════════════════
    # QUICK RESEARCH METHODS (For Queen's fast decisions)
    # ═══════════════════════════════════════════════════════════════════════
    
    async def quick_sentiment_check(self) -> Dict[str, Any]:
        """
        Quick sentiment check for the Queen's fast decision making.
        
        Returns:
            Simple sentiment summary
        """
        result = await self.research_news()
        
        return {
            "sentiment": result.sentiment_score,
            "label": "bullish" if result.sentiment_score > 0.2 else ("bearish" if result.sentiment_score < -0.2 else "neutral"),
            "confidence": result.confidence,
            "success": result.success
        }
    
    async def quick_wiki_lookup(self, topic: str) -> str:
        """
        Quick Wikipedia summary lookup.
        
        Returns:
            Summary text or empty string
        """
        result = await self.research_topic(topic)
        
        if result.success:
            return result.data.get("summary", "")[:500]
        return ""
    
    def get_status(self) -> Dict[str, Any]:
        """Get neuron status and metrics."""
        return {
            "neuron": "QueenResearchNeuron",
            "status": "active",
            "metrics": self.metrics.copy(),
            "cache_size": len(self.research_cache),
            "insights_history_size": len(self.insights_history),
            "news_feed_available": self.news_feed is not None,
            "thought_bus_connected": self.thought_bus is not None
        }


# ═══════════════════════════════════════════════════════════════════════════
# FACTORY FUNCTION
# ═══════════════════════════════════════════════════════════════════════════

def create_queen_research_neuron(
    news_api_key: Optional[str] = None,
    thought_bus: Optional['ThoughtBus'] = None
) -> QueenResearchNeuron:
    """
    Create a QueenResearchNeuron instance.
    
    Args:
        news_api_key: Optional World News API key
        thought_bus: Optional ThoughtBus for integration
    
    Returns:
        Configured QueenResearchNeuron
    """
    return QueenResearchNeuron(
        news_api_key=news_api_key,
        thought_bus=thought_bus
    )


# ═══════════════════════════════════════════════════════════════════════════
# DEMO & TESTING
# ═══════════════════════════════════════════════════════════════════════════

async def demo():
    """Demo the Queen Research Neuron."""
    print("=" * 70)
    print("👑📰🔬 QUEEN RESEARCH NEURON DEMO 🔬📰👑")
    print("=" * 70)
    
    neuron = create_queen_research_neuron()
    
    # 1. Wikipedia Research
    print("\n[1] 📚 Wikipedia Research: Bitcoin")
    print("-" * 40)
    wiki_result = await neuron.research_topic("Bitcoin")
    if wiki_result.success:
        print(f"    Title: {wiki_result.data.get('title', 'N/A')}")
        print(f"    Summary: {wiki_result.data.get('summary', '')[:200]}...")
        print(f"    Related: {wiki_result.data.get('search_results', [])}")
    else:
        print(f"    Error: {wiki_result.error_message}")
    
    # 2. Entity Research
    print("\n[2] 🏢 Entity Research: BlackRock")
    print("-" * 40)
    entity_result = await neuron.research_entity("BlackRock")
    if entity_result.success:
        print(f"    Found: {entity_result.data.get('found', False)}")
        print(f"    Summary: {entity_result.data.get('summary', '')[:200]}...")
        print(f"    Categories: {entity_result.data.get('categories', [])[:5]}")
    else:
        print(f"    Error: {entity_result.error_message}")
    
    # 3. Symbol Context
    print("\n[3] 📊 Symbol Context: BTC/USD")
    print("-" * 40)
    symbol_result = await neuron.get_symbol_context("BTC/USD")
    if symbol_result.success:
        topics = symbol_result.data.get("topics", [])
        for topic in topics[:2]:
            print(f"    Topic: {topic.get('title', 'N/A')}")
            print(f"    Summary: {topic.get('summary', '')[:150]}...")
    else:
        print(f"    No context found")
    
    # 4. News Research (RSS feeds)
    print("\n[4] 📰 News Sentiment Research")
    print("-" * 40)
    news_result = await neuron.research_news()
    if news_result.success:
        print(f"    Sentiment: {news_result.sentiment_score:.4f}")
        print(f"    Confidence: {news_result.confidence:.4f}")
        print(f"    Sources: {news_result.sources_used}")
        if news_result.data.get("rss_headlines"):
            print("    Recent Headlines:")
            for h in news_result.data["rss_headlines"][:3]:
                print(f"      • [{h['source']}] {h['title'][:50]}...")
    else:
        print(f"    Error: {news_result.error_message}")
    
    # 5. Comprehensive Research
    print("\n[5] 🔬 Comprehensive Research: ETH")
    print("-" * 40)
    report = await neuron.comprehensive_research(symbol="ETH/USD")
    print(f"    Overall Sentiment: {report['overall_sentiment']:.4f}")
    print(f"    Confidence: {report['confidence']:.4f}")
    print(f"    Recommended Action: {report['recommended_action']}")
    print(f"    Insights: {len(report['insights'])}")
    
    # 6. Status
    print("\n[6] 📊 Neuron Status")
    print("-" * 40)
    status = neuron.get_status()
    print(f"    Total Researches: {status['metrics']['total_researches']}")
    print(f"    Wiki Queries: {status['metrics']['wiki_queries']}")
    print(f"    News Queries: {status['metrics']['news_queries']}")
    print(f"    RSS Scans: {status['metrics']['rss_scans']}")
    print(f"    Errors: {status['metrics']['errors']}")
    print(f"    Cache Size: {status['cache_size']}")
    
    print("\n" + "=" * 70)
    print("Demo complete! 👑")


if __name__ == "__main__":
    asyncio.run(demo())
