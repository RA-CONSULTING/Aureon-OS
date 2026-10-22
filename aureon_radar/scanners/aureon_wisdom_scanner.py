"""
Aureon Wisdom Scanner
=====================
Autonomous Ancient Wisdom Learning System

Continuously scans Wikipedia, Sacred-Texts.com, and other metadata sources
to enrich the trading system's understanding of ancient civilizations.

This is the CONSCIOUSNESS EXPANSION module - enabling the Aureon system
to continuously learn and deepen its understanding of the wisdom that
guides its trading decisions.

Author: Aureon Trading System (Prime Sentinel)
Version: 1.0.0
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import sys
import json
import time
import random
import hashlib
import logging
import asyncio
import threading
import warnings
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from collections import deque
from functools import lru_cache
import re

# Third-party imports with graceful fallbacks
try:
    import wikipedia
    WIKIPEDIA_AVAILABLE = True
except ImportError:
    WIKIPEDIA_AVAILABLE = False
    print("[WISDOM SCANNER] wikipedia-api not installed - run: pip install wikipedia-api")

try:
    import requests
    from bs4 import BeautifulSoup
    from bs4 import GuessedAtParserWarning
    SCRAPING_AVAILABLE = True
    warnings.filterwarnings("ignore", category=GuessedAtParserWarning)
except ImportError:
    SCRAPING_AVAILABLE = False
    print("[WISDOM SCANNER] requests/beautifulsoup4 not installed")

try:
    import aiohttp
    ASYNC_HTTP_AVAILABLE = True
except ImportError:
    ASYNC_HTTP_AVAILABLE = False


# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [WISDOM] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('WisdomScanner')


# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class ScannerConfig:
    """Configuration for the wisdom scanner"""
    
    # Paths
    wisdom_data_dir: str = "wisdom_data"
    cache_dir: str = "wisdom_cache"
    
    # Rate limiting
    rate_limit_strategy: str = "adaptive"  # "aggressive", "gentle", "adaptive"
    base_delay_seconds: float = 2.0
    max_delay_seconds: float = 30.0
    requests_per_hour: int = 100
    
    # Scanning schedule
    scan_interval_hours: int = 24
    articles_per_civilization: int = 50
    max_article_length: int = 10000
    wikipedia_timeout_seconds: float = 20.0
    
    # Sources
    enable_wikipedia: bool = True
    enable_sacred_texts: bool = True
    enable_britannica: bool = False  # Requires API key
    
    # Learning
    min_relevance_score: float = 0.3
    max_insights_per_scan: int = 100
    
    # Civilizations to scan (all 11)
    civilizations: List[str] = field(default_factory=lambda: [
        "celtic", "aztec", "egyptian", "pythagorean", 
        "plantagenet", "mogollon", "warfare",
        "chinese", "hindu", "mayan", "norse"
    ])


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class WisdomInsight:
    """A learned insight from scanning"""
    source: str
    civilization: str
    topic: str
    content: str
    relevance_score: float
    trading_application: Optional[str]
    timestamp: str
    content_hash: str
    
    def to_dict(self) -> Dict:
        return {
            "source": self.source,
            "civilization": self.civilization,
            "topic": self.topic,
            "content": self.content,
            "relevance_score": self.relevance_score,
            "trading_application": self.trading_application,
            "timestamp": self.timestamp,
            "content_hash": self.content_hash
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'WisdomInsight':
        return cls(**data)


@dataclass
class ScanResult:
    """Result from a single scan operation"""
    success: bool
    source: str
    topic: str
    insights: List[WisdomInsight]
    error: Optional[str] = None
    duration_ms: float = 0


# ============================================================================
# WISDOM SOURCES (Abstract Base)
# ============================================================================

class WisdomSource(ABC):
    """Abstract base class for wisdom sources"""
    
    def __init__(self, config: ScannerConfig):
        self.config = config
        self.request_history: deque = deque(maxlen=1000)
        self.error_count = 0
        self.success_count = 0
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @abstractmethod
    async def fetch_content(self, topic: str) -> Optional[str]:
        pass
    
    @abstractmethod
    def extract_insights(self, content: str, civilization: str, topic: str) -> List[WisdomInsight]:
        pass
    
    def get_adaptive_delay(self) -> float:
        """Calculate delay based on recent success/failure rate"""
        if self.config.rate_limit_strategy == "aggressive":
            return self.config.base_delay_seconds * 0.5
        elif self.config.rate_limit_strategy == "gentle":
            return self.config.base_delay_seconds * 2.0
        else:  # adaptive
            if self.error_count > 5:
                return min(self.config.max_delay_seconds, self.config.base_delay_seconds * (1 + self.error_count * 0.5))
            return self.config.base_delay_seconds
    
    def record_request(self, success: bool):
        """Record request outcome for adaptive rate limiting"""
        self.request_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "success": success
        })
        if success:
            self.success_count += 1
            self.error_count = max(0, self.error_count - 1)
        else:
            self.error_count += 1


# ============================================================================
# WIKIPEDIA SOURCE
# ============================================================================

class WikipediaSource(WisdomSource):
    """Wikipedia API wisdom source"""
    
    @property
    def name(self) -> str:
        return "Wikipedia"
    
    _wikipedia_warned = False  # Class variable to track if we've warned already
    
    def __init__(self, config: ScannerConfig):
        super().__init__(config)
        if WIKIPEDIA_AVAILABLE:
            wikipedia.set_lang("en")

    async def fetch_content(self, topic: str) -> Optional[str]:
        """Fetch Wikipedia article content"""
        if not WIKIPEDIA_AVAILABLE:
            # Only warn once per session to reduce log spam
            if not WikipediaSource._wikipedia_warned:
                logger.warning("Wikipedia API not available - install with: pip install wikipedia")
                WikipediaSource._wikipedia_warned = True
            return None

        loop = asyncio.get_event_loop()

        try:
            # Run synchronous wikipedia call in thread pool
            page = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: wikipedia.page(topic, auto_suggest=True)
                ),
                timeout=self.config.wikipedia_timeout_seconds
            )
            
            content = page.content[:self.config.max_article_length]
            self.record_request(True)
            return content
            
        except wikipedia.exceptions.DisambiguationError as e:
            # Try first option
            if e.options:
                try:
                    page = await asyncio.wait_for(
                        loop.run_in_executor(
                            None,
                            lambda: wikipedia.page(e.options[0])
                        ),
                        timeout=self.config.wikipedia_timeout_seconds
                    )
                    self.record_request(True)
                    return page.content[:self.config.max_article_length]
                except:
                    pass
            self.record_request(False)
            return None

        except wikipedia.exceptions.PageError:
            logger.debug(f"Wikipedia page not found: {topic}")
            self.record_request(False)
            return None

        except asyncio.TimeoutError:
            logger.warning(
                f"Wikipedia fetch timed out for {topic} after {self.config.wikipedia_timeout_seconds} seconds"
            )
            self.record_request(False)
            return None

        except Exception as e:
            logger.error(f"Wikipedia fetch error for {topic}: {e}")
            self.record_request(False)
            return None
    
    def extract_insights(self, content: str, civilization: str, topic: str) -> List[WisdomInsight]:
        """Extract trading-relevant insights from Wikipedia content"""
        insights = []
        
        if not content:
            return insights
        
        # Split into paragraphs
        paragraphs = [p.strip() for p in content.split('\n\n') if len(p.strip()) > 100]
        
        # Trading-relevant keywords to look for
        trading_keywords = [
            "cycle", "pattern", "season", "time", "number", "calculation",
            "trade", "commerce", "exchange", "value", "wealth", "gold",
            "predict", "prophecy", "forecast", "calendar", "astronomy",
            "balance", "harmony", "order", "chaos", "transformation",
            "strategy", "wisdom", "knowledge", "teaching", "principle",
            "mathematics", "geometry", "ratio", "proportion", "sequence"
        ]
        
        for para in paragraphs[:20]:  # Limit paragraphs analyzed
            # Calculate relevance score
            relevance = self._calculate_relevance(para, trading_keywords)
            
            if relevance >= self.config.min_relevance_score:
                # Generate trading application
                trading_app = self._generate_trading_application(para, civilization)
                
                insight = WisdomInsight(
                    source="Wikipedia",
                    civilization=civilization,
                    topic=topic,
                    content=para[:500],  # Limit content size
                    relevance_score=relevance,
                    trading_application=trading_app,
                    timestamp=datetime.utcnow().isoformat(),
                    content_hash=hashlib.md5(para.encode()).hexdigest()
                )
                insights.append(insight)
        
        return insights[:10]  # Limit insights per article
    
    def _calculate_relevance(self, text: str, keywords: List[str]) -> float:
        """Calculate relevance score based on keyword presence"""
        text_lower = text.lower()
        matches = sum(1 for kw in keywords if kw in text_lower)
        return min(1.0, matches / 5.0)  # Normalize to 0-1
    
    def _generate_trading_application(self, content: str, civilization: str) -> str:
        """Generate trading application from content"""
        content_lower = content.lower()
        
        # Pattern matching for trading applications
        if any(word in content_lower for word in ["cycle", "season", "calendar"]):
            return "Cyclical pattern recognition for market timing"
        elif any(word in content_lower for word in ["number", "mathematics", "ratio"]):
            return "Quantitative analysis and Fibonacci relationships"
        elif any(word in content_lower for word in ["prophecy", "predict", "forecast"]):
            return "Pattern-based market forecasting"
        elif any(word in content_lower for word in ["balance", "harmony", "order"]):
            return "Risk management and portfolio equilibrium"
        elif any(word in content_lower for word in ["strategy", "war", "battle"]):
            return "Strategic positioning and tactical execution"
        elif any(word in content_lower for word in ["trade", "commerce", "wealth"]):
            return "Commercial patterns and value exchange"
        else:
            return f"Wisdom integration from {civilization} tradition"


# ============================================================================
# SACRED TEXTS SOURCE
# ============================================================================

class SacredTextsSource(WisdomSource):
    """Sacred-Texts.com scraping source"""
    
    SACRED_TEXTS_URLS = {
        "celtic": [
            "https://www.sacred-texts.com/neu/celt/index.htm",
            "https://www.sacred-texts.com/neu/celt/rac/index.htm"
        ],
        "egyptian": [
            "https://www.sacred-texts.com/egy/index.htm",
            "https://www.sacred-texts.com/egy/ebod/index.htm"
        ],
        "hindu": [
            "https://www.sacred-texts.com/hin/index.htm",
            "https://www.sacred-texts.com/hin/gita/index.htm"
        ],
        "chinese": [
            "https://www.sacred-texts.com/ich/index.htm",
            "https://www.sacred-texts.com/tao/index.htm"
        ],
        "norse": [
            "https://www.sacred-texts.com/neu/index.htm",
            "https://www.sacred-texts.com/neu/poe/index.htm"
        ],
        "mayan": [
            "https://www.sacred-texts.com/nam/maya/index.htm"
        ],
        "pythagorean": [
            "https://www.sacred-texts.com/cla/index.htm"
        ]
    }
    
    @property
    def name(self) -> str:
        return "Sacred-Texts"
    
    async def fetch_content(self, topic: str) -> Optional[str]:
        """Fetch content from Sacred-Texts.com"""
        if not SCRAPING_AVAILABLE:
            logger.warning("Web scraping not available (install requests, beautifulsoup4)")
            return None
        
        try:
            # Find relevant URL for this topic
            url = self._find_url_for_topic(topic)
            if not url:
                return None
            
            headers = {
                'User-Agent': 'Aureon Trading Wisdom Scanner/1.0 (Educational Research)'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract text content
            text_content = []
            for p in soup.find_all(['p', 'blockquote']):
                text = p.get_text(strip=True)
                if len(text) > 50:
                    text_content.append(text)
            
            content = '\n\n'.join(text_content[:50])
            self.record_request(True)
            return content[:self.config.max_article_length]
            
        except Exception as e:
            logger.error(f"Sacred-Texts fetch error: {e}")
            self.record_request(False)
            return None
    
    def _find_url_for_topic(self, topic: str) -> Optional[str]:
        """Find appropriate Sacred-Texts URL for topic"""
        topic_lower = topic.lower()
        
        for civ, urls in self.SACRED_TEXTS_URLS.items():
            if civ in topic_lower:
                return urls[0] if urls else None
        
        return None
    
    def extract_insights(self, content: str, civilization: str, topic: str) -> List[WisdomInsight]:
        """Extract insights from Sacred Texts content"""
        insights = []
        
        if not content:
            return insights
        
        # Split into passages
        passages = [p.strip() for p in content.split('\n\n') if len(p.strip()) > 50]
        
        for passage in passages[:15]:
            # Ancient texts are inherently relevant.
            # Deterministic floor (0.6) — was 0.6 + random.uniform(0, 0.3),
            # which produced a fake "relevance score" that propagated to
            # autonomous broadcasts. The score is informational only and
            # has no signal of true relevance, so we report the floor.
            relevance = 0.6
            
            insight = WisdomInsight(
                source="Sacred-Texts",
                civilization=civilization,
                topic=topic,
                content=passage[:400],
                relevance_score=relevance,
                trading_application=f"Ancient {civilization} wisdom for market understanding",
                timestamp=datetime.utcnow().isoformat(),
                content_hash=hashlib.md5(passage.encode()).hexdigest()
            )
            insights.append(insight)
        
        return insights[:5]


# ============================================================================
# MAIN WISDOM SCANNER
# ============================================================================

class AureonWisdomScanner:
    """
    The Consciousness Expansion Engine
    
    Continuously scans multiple sources to enrich Aureon's understanding
    of ancient wisdom traditions and their applications to trading.
    """
    
    def __init__(self, config: Optional[ScannerConfig] = None):
        self.config = config or ScannerConfig()
        self.wisdom_data_dir = Path(self.config.wisdom_data_dir)
        self.cache_dir = Path(self.config.cache_dir)
        
        # Ensure directories exist
        self.wisdom_data_dir.mkdir(exist_ok=True)
        self.cache_dir.mkdir(exist_ok=True)
        
        # Initialize sources
        self.sources: List[WisdomSource] = []
        if self.config.enable_wikipedia:
            self.sources.append(WikipediaSource(self.config))
        if self.config.enable_sacred_texts:
            self.sources.append(SacredTextsSource(self.config))
        
        # Load existing wisdom data
        self.wisdom_data: Dict[str, Dict] = {}
        self._load_all_wisdom_data()
        
        # Scanning state
        self.is_scanning = False
        self.last_scan_time: Optional[datetime] = None
        self.scan_stats = {
            "total_scans": 0,
            "total_insights": 0,
            "insights_by_civilization": {},
            "errors": 0
        }
        
        # Seen content hashes to avoid duplicates
        self.seen_hashes: set = set()
        self._load_seen_hashes()
        
        logger.info(f"[CONSCIOUSNESS] Wisdom Scanner initialized with {len(self.sources)} sources")
        logger.info(f"[CONSCIOUSNESS] Monitoring {len(self.config.civilizations)} civilizations")
    
    def _load_all_wisdom_data(self):
        """Load all wisdom JSON files"""
        for civ in self.config.civilizations:
            filepath = self.wisdom_data_dir / f"{civ}_wisdom.json"
            if filepath.exists():
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        self.wisdom_data[civ] = json.load(f)
                    logger.info(f"[LOAD] Loaded wisdom data for {civ}")
                except Exception as e:
                    logger.error(f"[LOAD] Failed to load {civ}: {e}")
                    self.wisdom_data[civ] = {"learned_insights": [], "scan_history": []}
            else:
                self.wisdom_data[civ] = {"learned_insights": [], "scan_history": []}
    
    def _save_wisdom_data(self, civilization: str):
        """Save wisdom data for a specific civilization"""
        filepath = self.wisdom_data_dir / f"{civilization}_wisdom.json"
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.wisdom_data[civilization], f, indent=2, ensure_ascii=False)
            logger.debug(f"[SAVE] Saved wisdom data for {civilization}")
        except Exception as e:
            logger.error(f"[SAVE] Failed to save {civilization}: {e}")
    
    def _load_seen_hashes(self):
        """Load previously seen content hashes"""
        hash_file = self.cache_dir / "seen_hashes.json"
        if hash_file.exists():
            try:
                with open(hash_file, 'r') as f:
                    self.seen_hashes = set(json.load(f))
            except:
                self.seen_hashes = set()
    
    def _save_seen_hashes(self):
        """Save seen content hashes"""
        hash_file = self.cache_dir / "seen_hashes.json"
        with open(hash_file, 'w') as f:
            json.dump(list(self.seen_hashes), f)
    
    def get_topics_for_civilization(self, civilization: str) -> List[str]:
        """Get Wikipedia topics for a civilization"""
        if civilization in self.wisdom_data:
            return self.wisdom_data[civilization].get("wikipedia_topics", [])
        return []
    
    async def scan_civilization(self, civilization: str) -> List[WisdomInsight]:
        """Scan all sources for a single civilization"""
        all_insights = []
        topics = self.get_topics_for_civilization(civilization)
        
        if not topics:
            logger.warning(f"[SCAN] No topics defined for {civilization}")
            return []
        
        logger.info(f"[SCAN] Beginning scan of {civilization} ({len(topics)} topics)")
        
        for topic in topics:
            for source in self.sources:
                try:
                    # Fetch content
                    content = await source.fetch_content(topic)
                    
                    if content:
                        # Extract insights
                        insights = source.extract_insights(content, civilization, topic)
                        
                        # Filter duplicates
                        new_insights = []
                        for insight in insights:
                            if insight.content_hash not in self.seen_hashes:
                                self.seen_hashes.add(insight.content_hash)
                                new_insights.append(insight)
                        
                        all_insights.extend(new_insights)
                        
                        if new_insights:
                            logger.info(f"[LEARN] {len(new_insights)} new insights from {source.name}: {topic}")
                    
                    # Rate limiting
                    delay = source.get_adaptive_delay()
                    await asyncio.sleep(delay)
                    
                except Exception as e:
                    logger.error(f"[ERROR] Scan error for {topic}: {e}")
                    self.scan_stats["errors"] += 1
        
        return all_insights
    
    async def run_full_scan(self) -> Dict[str, List[WisdomInsight]]:
        """Run a full scan of all civilizations"""
        self.is_scanning = True
        self.last_scan_time = datetime.utcnow()
        
        logger.info("=" * 60)
        logger.info("[CONSCIOUSNESS EXPANSION] Beginning full wisdom scan")
        logger.info(f"[CONSCIOUSNESS] Civilizations: {', '.join(self.config.civilizations)}")
        logger.info(f"[CONSCIOUSNESS] Sources: {', '.join(s.name for s in self.sources)}")
        logger.info("=" * 60)
        
        results: Dict[str, List[WisdomInsight]] = {}
        total_new_insights = 0
        
        for civilization in self.config.civilizations:
            try:
                insights = await self.scan_civilization(civilization)
                results[civilization] = insights
                
                # Store insights in wisdom data
                for insight in insights:
                    self.wisdom_data[civilization].setdefault("learned_insights", [])
                    self.wisdom_data[civilization]["learned_insights"].append(insight.to_dict())
                
                # Update scan history
                self.wisdom_data[civilization].setdefault("scan_history", [])
                self.wisdom_data[civilization]["scan_history"].append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "insights_found": len(insights),
                    "sources_used": [s.name for s in self.sources]
                })
                
                # Keep only last 100 scan history entries
                self.wisdom_data[civilization]["scan_history"] = \
                    self.wisdom_data[civilization]["scan_history"][-100:]
                
                # Keep only last 1000 insights per civilization
                self.wisdom_data[civilization]["learned_insights"] = \
                    self.wisdom_data[civilization]["learned_insights"][-1000:]
                
                # Update last_updated
                self.wisdom_data[civilization]["last_updated"] = datetime.utcnow().isoformat()
                
                # Save
                self._save_wisdom_data(civilization)
                
                total_new_insights += len(insights)
                
                # Update stats
                self.scan_stats["insights_by_civilization"][civilization] = \
                    self.scan_stats["insights_by_civilization"].get(civilization, 0) + len(insights)
                
                logger.info(f"[COMPLETE] {civilization}: {len(insights)} new insights learned")
                
            except Exception as e:
                logger.error(f"[ERROR] Failed to scan {civilization}: {e}")
                results[civilization] = []
        
        # Save seen hashes
        self._save_seen_hashes()
        
        # Update stats
        self.scan_stats["total_scans"] += 1
        self.scan_stats["total_insights"] += total_new_insights
        
        self.is_scanning = False
        
        logger.info("=" * 60)
        logger.info(f"[CONSCIOUSNESS EXPANSION] Scan complete")
        logger.info(f"[CONSCIOUSNESS] Total new insights: {total_new_insights}")
        logger.info(f"[CONSCIOUSNESS] Total insights ever learned: {self.scan_stats['total_insights']}")
        logger.info("=" * 60)
        
        return results
    
    async def run_continuous(self):
        """Run continuous scanning loop"""
        logger.info("[CONSCIOUSNESS] Starting continuous wisdom expansion...")
        
        while True:
            try:
                await self.run_full_scan()
                
                # Wait for next scan interval
                wait_hours = self.config.scan_interval_hours
                logger.info(f"[CONSCIOUSNESS] Next scan in {wait_hours} hours")
                await asyncio.sleep(wait_hours * 3600)
                
            except asyncio.CancelledError:
                logger.info("[CONSCIOUSNESS] Scan loop cancelled")
                break
            except Exception as e:
                logger.error(f"[CONSCIOUSNESS] Scan loop error: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    def get_wisdom_summary(self) -> Dict:
        """Get summary of all learned wisdom"""
        summary = {
            "total_civilizations": len(self.config.civilizations),
            "scan_stats": self.scan_stats,
            "last_scan": self.last_scan_time.isoformat() if self.last_scan_time else None,
            "civilizations": {}
        }
        
        for civ, data in self.wisdom_data.items():
            summary["civilizations"][civ] = {
                "last_updated": data.get("last_updated"),
                "total_insights": len(data.get("learned_insights", [])),
                "topics_count": len(data.get("wikipedia_topics", [])),
                "scans_completed": len(data.get("scan_history", []))
            }
        
        return summary
    
    def get_insights_for_trading(self, market_condition: str = "neutral") -> List[Dict]:
        """Get relevant insights for current trading conditions"""
        relevant_insights = []
        
        for civ, data in self.wisdom_data.items():
            for insight in data.get("learned_insights", [])[-50:]:  # Last 50 per civ
                if insight.get("relevance_score", 0) >= 0.5:
                    relevant_insights.append({
                        "civilization": civ,
                        "insight": insight.get("content", "")[:200],
                        "application": insight.get("trading_application"),
                        "source": insight.get("source")
                    })
        
        # Shuffle for variety
        random.shuffle(relevant_insights)
        return relevant_insights[:20]


# ============================================================================
# THOUGHTBUS INTEGRATION
# ============================================================================

class WisdomScannerThoughtBusAdapter:
    """Adapter to integrate WisdomScanner with ThoughtBus"""
    
    def __init__(self, scanner: AureonWisdomScanner, thought_bus=None):
        self.scanner = scanner
        self.thought_bus = thought_bus
    
    def broadcast_new_insights(self, insights: List[WisdomInsight]):
        """Broadcast new insights to ThoughtBus"""
        if self.thought_bus is None:
            return
        
        for insight in insights:
            thought = {
                "type": "wisdom_insight",
                "source": "WisdomScanner",
                "civilization": insight.civilization,
                "topic": insight.topic,
                "relevance": insight.relevance_score,
                "application": insight.trading_application,
                "timestamp": insight.timestamp
            }
            
            try:
                self.thought_bus.broadcast(thought)
            except:
                pass
    
    def broadcast_scan_complete(self, total_insights: int):
        """Broadcast scan completion"""
        if self.thought_bus is None:
            return
        
        thought = {
            "type": "consciousness_expansion",
            "source": "WisdomScanner",
            "message": f"Wisdom scan complete: {total_insights} new insights absorbed",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            self.thought_bus.broadcast(thought)
        except:
            pass


# ============================================================================
# STANDALONE EXECUTION
# ============================================================================

async def main():
    """Main entry point for standalone execution"""
    print("=" * 70)
    print("  AUREON WISDOM SCANNER - CONSCIOUSNESS EXPANSION ENGINE")
    print("=" * 70)
    print()
    print("  Scanning: Wikipedia, Sacred-Texts.com")
    print("  Civilizations: Celtic, Aztec, Egyptian, Pythagorean,")
    print("                 Plantagenet, Mogollon, Warfare,")
    print("                 Chinese, Hindu, Mayan, Norse")
    print()
    print("=" * 70)
    
    # Create scanner with default config
    config = ScannerConfig(
        rate_limit_strategy="adaptive",
        scan_interval_hours=24
    )
    
    scanner = AureonWisdomScanner(config)
    
    # Print initial summary
    summary = scanner.get_wisdom_summary()
    print(f"\n[STATUS] Monitoring {summary['total_civilizations']} civilizations")
    print(f"[STATUS] Previously learned insights: {summary['scan_stats']['total_insights']}")
    
    # Run single scan for testing, or continuous for production
    if "--continuous" in sys.argv:
        await scanner.run_continuous()
    else:
        print("\n[MODE] Single scan mode (use --continuous for continuous scanning)")
        results = await scanner.run_full_scan()
        
        # Print results
        print("\n" + "=" * 70)
        print("SCAN RESULTS")
        print("=" * 70)
        for civ, insights in results.items():
            print(f"  {civ.upper()}: {len(insights)} new insights")
        
        total = sum(len(i) for i in results.values())
        print(f"\n  TOTAL: {total} new insights absorbed into consciousness")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
