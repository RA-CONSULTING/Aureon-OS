"""
Aureon News Feed Module
=======================
World News API integration for real-time market news and sentiment analysis.
Publishes news as thoughts to the ThoughtBus for cognitive processing.

API: https://worldnewsapi.com/docs/
"""

from aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import json
import time
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum

# Import ThoughtBus for publishing news thoughts
try:
    from aureon_thought_bus import ThoughtBus, Thought
except ImportError:
    ThoughtBus = None
    Thought = None


class NewsCategory(Enum):
    """World News API categories."""
    POLITICS = "politics"
    SPORTS = "sports"
    BUSINESS = "business"
    TECHNOLOGY = "technology"
    ENTERTAINMENT = "entertainment"
    HEALTH = "health"
    SCIENCE = "science"
    LIFESTYLE = "lifestyle"
    TRAVEL = "travel"
    CULTURE = "culture"
    EDUCATION = "education"
    ENVIRONMENT = "environment"
    OTHER = "other"


@dataclass
class NewsArticle:
    """Structured news article from World News API."""
    id: int
    title: str
    text: str
    summary: str
    url: str
    image: Optional[str]
    video: Optional[str]
    publish_date: str
    authors: List[str]
    category: str
    language: str
    source_country: str
    sentiment: float  # Range [-1, 1]
    
    @property
    def sentiment_label(self) -> str:
        """Human-readable sentiment label."""
        if self.sentiment >= 0.3:
            return "bullish"
        elif self.sentiment <= -0.3:
            return "bearish"
        return "neutral"
    
    @property
    def age_minutes(self) -> float:
        """Age of article in minutes."""
        try:
            pub = datetime.strptime(self.publish_date, "%Y-%m-%d %H:%M:%S")
            return (datetime.utcnow() - pub).total_seconds() / 60
        except:
            return float('inf')


@dataclass
class NewsFeedConfig:
    """Configuration for news feed."""
    api_key: str
    # Search keywords for market-relevant news
    market_keywords: List[str] = field(default_factory=lambda: [
        "cryptocurrency", "bitcoin", "ethereum", "stock market",
        "federal reserve", "inflation", "recession", "trading",
        "forex", "interest rates", "economic"
    ])
    # Categories to monitor
    categories: List[str] = field(default_factory=lambda: [
        "business", "technology", "politics"
    ])
    # Languages
    language: str = "en"
    # How often to poll (seconds)
    poll_interval: int = 300  # 5 minutes
    # Max articles per query
    max_articles: int = 20
    # Sentiment thresholds for alerting
    alert_sentiment_threshold: float = 0.5
    # Only articles newer than this (hours)
    max_age_hours: int = 24


class NewsFeed:
    """
    World News API client that integrates with Aureon's cognitive system.
    Fetches market-relevant news and publishes sentiment analysis to ThoughtBus.
    """
    
    BASE_URL = "https://api.worldnewsapi.com"
    
    def __init__(self, config: NewsFeedConfig, thought_bus: Optional['ThoughtBus'] = None):
        self.config = config
        self.thought_bus = thought_bus
        self.last_poll_time: Optional[datetime] = None
        self.articles_cache: Dict[int, NewsArticle] = {}
        self.session: Optional[aiohttp.ClientSession] = None
        self._running = False
        
        # Metrics
        self.metrics = {
            "total_articles_fetched": 0,
            "api_calls": 0,
            "last_sentiment_avg": 0.0,
            "bullish_count": 0,
            "bearish_count": 0,
            "neutral_count": 0,
            "errors": 0
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    def _publish_thought(self, topic: str, payload: Dict[str, Any], meta: Optional[Dict] = None):
        """Publish a thought to the ThoughtBus if available."""
        if self.thought_bus and Thought:
            thought = Thought(
                source="news_feed",
                topic=topic,
                payload=payload,
                meta=meta or {}
            )
            self.thought_bus.publish(thought)
            return thought.id
        return None
    
    async def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Optional[Dict]:
        """Make an API request."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        url = f"{self.BASE_URL}/{endpoint}"
        headers = {"x-api-key": self.config.api_key}
        
        try:
            async with self.session.get(url, params=params, headers=headers) as resp:
                self.metrics["api_calls"] += 1
                
                if resp.status == 200:
                    data = await resp.json()
                    return data
                else:
                    error_text = await resp.text()
                    print(f"[NewsFeed] API error {resp.status}: {error_text}")
                    self.metrics["errors"] += 1
                    
                    # Publish error thought
                    self._publish_thought("news.error", {
                        "status": resp.status,
                        "error": error_text[:200]
                    })
                    return None
                    
        except Exception as e:
            print(f"[NewsFeed] Request error: {e}")
            self.metrics["errors"] += 1
            return None
    
    async def search_news(
        self,
        text: Optional[str] = None,
        categories: Optional[List[str]] = None,
        min_sentiment: Optional[float] = None,
        max_sentiment: Optional[float] = None,
        earliest_date: Optional[datetime] = None,
        number: int = 10
    ) -> List[NewsArticle]:
        """
        Search for news articles matching criteria.
        
        Args:
            text: Search text (keywords)
            categories: List of categories to filter
            min_sentiment: Minimum sentiment score [-1, 1]
            max_sentiment: Maximum sentiment score [-1, 1]
            earliest_date: Only articles published after this date
            number: Number of articles to return (max 100)
        
        Returns:
            List of NewsArticle objects
        """
        params = {
            "language": self.config.language,
            "number": min(number, 100)
        }
        
        if text:
            params["text"] = text
        
        if categories:
            params["categories"] = ",".join(categories)
        
        if min_sentiment is not None:
            params["min-sentiment"] = min_sentiment
        
        if max_sentiment is not None:
            params["max-sentiment"] = max_sentiment
        
        if earliest_date:
            params["earliest-publish-date"] = earliest_date.strftime("%Y-%m-%d %H:%M:%S")
        else:
            # Default to last 24 hours
            cutoff = datetime.utcnow() - timedelta(hours=self.config.max_age_hours)
            params["earliest-publish-date"] = cutoff.strftime("%Y-%m-%d %H:%M:%S")
        
        params["sort"] = "publish-time"
        params["sort-direction"] = "DESC"
        
        data = await self._make_request("search-news", params)
        
        if not data or "news" not in data:
            return []
        
        articles = []
        for item in data["news"]:
            try:
                article = NewsArticle(
                    id=item.get("id", 0),
                    title=item.get("title", ""),
                    text=item.get("text", ""),
                    summary=item.get("summary", ""),
                    url=item.get("url", ""),
                    image=item.get("image"),
                    video=item.get("video"),
                    publish_date=item.get("publish_date", ""),
                    authors=item.get("authors", []),
                    category=item.get("category", "other"),
                    language=item.get("language", "en"),
                    source_country=item.get("source_country", ""),
                    sentiment=item.get("sentiment", 0.0)
                )
                articles.append(article)
                
                # Cache article
                self.articles_cache[article.id] = article
                
            except Exception as e:
                print(f"[NewsFeed] Error parsing article: {e}")
        
        return articles
    
    async def fetch_market_news(self) -> List[NewsArticle]:
        """
        Fetch market-relevant news using configured keywords and categories.
        Returns aggregated, deduplicated articles.
        """
        all_articles: Dict[int, NewsArticle] = {}
        
        # Fetch by keywords
        for keyword in self.config.market_keywords[:5]:  # Limit to avoid rate limits
            articles = await self.search_news(
                text=keyword,
                number=self.config.max_articles // len(self.config.market_keywords[:5])
            )
            for article in articles:
                all_articles[article.id] = article
        
        # Fetch by categories (business news tends to be most relevant)
        for category in self.config.categories[:2]:
            articles = await self.search_news(
                categories=[category],
                number=10
            )
            for article in articles:
                all_articles[article.id] = article
        
        # Update metrics
        self.metrics["total_articles_fetched"] += len(all_articles)
        
        return list(all_articles.values())
    
    def analyze_sentiment_aggregate(self, articles: List[NewsArticle]) -> Dict[str, Any]:
        """
        Analyze aggregate sentiment from a collection of articles.
        
        Returns:
            Dictionary with sentiment analysis results
        """
        if not articles:
            return {
                "status": "no_data",
                "average_sentiment": 0.0,
                "sentiment_label": "neutral",
                "bullish_ratio": 0.0,
                "bearish_ratio": 0.0,
                "neutral_ratio": 1.0,
                "article_count": 0,
                "confidence": 0.0
            }
        
        sentiments = [a.sentiment for a in articles]
        avg_sentiment = sum(sentiments) / len(sentiments)
        
        bullish = sum(1 for s in sentiments if s >= 0.3)
        bearish = sum(1 for s in sentiments if s <= -0.3)
        neutral = len(sentiments) - bullish - bearish
        
        # Update metrics
        self.metrics["last_sentiment_avg"] = avg_sentiment
        self.metrics["bullish_count"] = bullish
        self.metrics["bearish_count"] = bearish
        self.metrics["neutral_count"] = neutral
        
        # Determine overall label
        if avg_sentiment >= 0.2:
            label = "bullish"
        elif avg_sentiment <= -0.2:
            label = "bearish"
        else:
            label = "neutral"
        
        # Confidence based on article count and sentiment consistency
        sentiment_std = (sum((s - avg_sentiment) ** 2 for s in sentiments) / len(sentiments)) ** 0.5
        consistency = max(0, 1 - sentiment_std)
        confidence = min(1.0, len(articles) / 20) * consistency
        
        return {
            "status": "analyzed",
            "average_sentiment": round(avg_sentiment, 4),
            "sentiment_label": label,
            "bullish_ratio": round(bullish / len(sentiments), 4),
            "bearish_ratio": round(bearish / len(sentiments), 4),
            "neutral_ratio": round(neutral / len(sentiments), 4),
            "article_count": len(articles),
            "confidence": round(confidence, 4),
            "sentiment_std": round(sentiment_std, 4)
        }
    
    def extract_market_signals(self, articles: List[NewsArticle]) -> Dict[str, Any]:
        """
        Extract trading-relevant signals from news articles.
        
        Returns:
            Dictionary with market signals
        """
        signals = {
            "crypto_sentiment": 0.0,
            "stock_sentiment": 0.0,
            "forex_sentiment": 0.0,
            "macro_sentiment": 0.0,
            "risk_level": "normal",
            "key_themes": [],
            "alerts": []
        }
        
        crypto_keywords = ["bitcoin", "ethereum", "crypto", "blockchain", "btc", "eth"]
        stock_keywords = ["stock", "nasdaq", "s&p", "dow", "equity", "shares"]
        forex_keywords = ["dollar", "euro", "forex", "currency", "yen", "pound"]
        macro_keywords = ["fed", "inflation", "interest rate", "gdp", "employment", "recession"]
        
        crypto_articles = []
        stock_articles = []
        forex_articles = []
        macro_articles = []
        
        for article in articles:
            text_lower = (article.title + " " + article.summary).lower()
            
            if any(kw in text_lower for kw in crypto_keywords):
                crypto_articles.append(article)
            if any(kw in text_lower for kw in stock_keywords):
                stock_articles.append(article)
            if any(kw in text_lower for kw in forex_keywords):
                forex_articles.append(article)
            if any(kw in text_lower for kw in macro_keywords):
                macro_articles.append(article)
        
        # Calculate domain-specific sentiments
        if crypto_articles:
            signals["crypto_sentiment"] = round(
                sum(a.sentiment for a in crypto_articles) / len(crypto_articles), 4
            )
        if stock_articles:
            signals["stock_sentiment"] = round(
                sum(a.sentiment for a in stock_articles) / len(stock_articles), 4
            )
        if forex_articles:
            signals["forex_sentiment"] = round(
                sum(a.sentiment for a in forex_articles) / len(forex_articles), 4
            )
        if macro_articles:
            signals["macro_sentiment"] = round(
                sum(a.sentiment for a in macro_articles) / len(macro_articles), 4
            )
        
        # Determine risk level based on extreme sentiments and volume
        extreme_negative = sum(1 for a in articles if a.sentiment <= -0.6)
        if extreme_negative >= 3 or signals["macro_sentiment"] <= -0.4:
            signals["risk_level"] = "elevated"
        if extreme_negative >= 5 or signals["macro_sentiment"] <= -0.6:
            signals["risk_level"] = "high"
        
        # Extract key themes (most mentioned categories)
        categories = {}
        for article in articles:
            cat = article.category
            categories[cat] = categories.get(cat, 0) + 1
        signals["key_themes"] = sorted(categories.keys(), key=lambda x: categories[x], reverse=True)[:3]
        
        # Generate alerts for extreme sentiment articles
        for article in articles:
            if abs(article.sentiment) >= self.config.alert_sentiment_threshold:
                signals["alerts"].append({
                    "title": article.title[:100],
                    "sentiment": article.sentiment,
                    "sentiment_label": article.sentiment_label,
                    "category": article.category,
                    "age_minutes": round(article.age_minutes, 1)
                })
        
        return signals
    
    async def poll_and_publish(self) -> Dict[str, Any]:
        """
        Poll for news and publish thoughts to ThoughtBus.
        
        Returns:
            Summary of polling results
        """
        self.last_poll_time = datetime.utcnow()
        
        # Fetch market news
        articles = await self.fetch_market_news()
        
        if not articles:
            return {"status": "no_articles", "timestamp": self.last_poll_time.isoformat()}
        
        # Analyze sentiment
        sentiment_analysis = self.analyze_sentiment_aggregate(articles)
        
        # Extract signals
        signals = self.extract_market_signals(articles)
        
        # Publish thoughts
        
        # 1. Overall sentiment thought
        self._publish_thought("news.sentiment", {
            "analysis": sentiment_analysis,
            "timestamp": self.last_poll_time.isoformat()
        }, meta={"importance": "high" if sentiment_analysis["confidence"] >= 0.5 else "normal"})
        
        # 2. Market signals thought
        self._publish_thought("news.signals", {
            "signals": signals,
            "timestamp": self.last_poll_time.isoformat()
        }, meta={"risk_level": signals["risk_level"]})
        
        # 3. Individual alert thoughts for extreme sentiment articles
        for alert in signals["alerts"][:5]:  # Limit to top 5 alerts
            self._publish_thought("news.alert", {
                "alert": alert,
                "timestamp": self.last_poll_time.isoformat()
            }, meta={"sentiment_label": alert["sentiment_label"]})
        
        # 4. Headlines digest thought
        headlines = [{"title": a.title[:150], "sentiment": a.sentiment, "category": a.category} 
                    for a in sorted(articles, key=lambda x: x.sentiment, reverse=True)[:10]]
        self._publish_thought("news.headlines", {
            "headlines": headlines,
            "timestamp": self.last_poll_time.isoformat()
        })
        
        # 5. Feed into Autonomy Hub (The Big Wheel)
        try:
            from aureon_autonomy_hub import get_autonomy_hub
            hub = get_autonomy_hub()
            hub.data_bridge.ingest_news_sentiment({
                'crypto_sentiment': signals.get('crypto_sentiment', 0.0),
                'aggregate_sentiment': sentiment_analysis.get('aggregate_sentiment', 0.0),
                'confidence': sentiment_analysis.get('confidence', 0.5),
                'bullish_ratio': sentiment_analysis.get('bullish_ratio', 0.33),
                'bearish_ratio': sentiment_analysis.get('bearish_ratio', 0.33),
                'key_themes': signals.get('key_themes', []),
            })
        except Exception:
            pass  # Hub not available yet

        return {
            "status": "success",
            "timestamp": self.last_poll_time.isoformat(),
            "articles_processed": len(articles),
            "sentiment_analysis": sentiment_analysis,
            "signals": signals,
            "thoughts_published": 3 + min(len(signals["alerts"]), 5)
        }
    
    async def run_continuous(self, stop_event: Optional[asyncio.Event] = None):
        """
        Run continuous news polling loop.
        
        Args:
            stop_event: Optional event to signal stopping
        """
        self._running = True
        print(f"[NewsFeed] Starting continuous polling (interval: {self.config.poll_interval}s)")
        
        while self._running:
            if stop_event and stop_event.is_set():
                break
            
            try:
                result = await self.poll_and_publish()
                print(f"[NewsFeed] Poll complete: {result['status']} - "
                      f"{result.get('articles_processed', 0)} articles, "
                      f"sentiment: {result.get('sentiment_analysis', {}).get('sentiment_label', 'unknown')}")
            except Exception as e:
                print(f"[NewsFeed] Error during poll: {e}")
                self.metrics["errors"] += 1
            
            await asyncio.sleep(self.config.poll_interval)
        
        print("[NewsFeed] Polling stopped")
    
    def stop(self):
        """Stop the continuous polling loop."""
        self._running = False
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status and metrics."""
        return {
            "running": self._running,
            "last_poll": self.last_poll_time.isoformat() if self.last_poll_time else None,
            "cached_articles": len(self.articles_cache),
            "metrics": self.metrics.copy()
        }


# Convenience function for integration
def create_news_feed(api_key: str, thought_bus: Optional['ThoughtBus'] = None) -> NewsFeed:
    """
    Create a NewsFeed instance with default market-focused config.
    
    Args:
        api_key: World News API key
        thought_bus: Optional ThoughtBus for publishing thoughts
    
    Returns:
        Configured NewsFeed instance
    """
    config = NewsFeedConfig(api_key=api_key)
    return NewsFeed(config, thought_bus)


# Demo and testing
async def demo():
    """Demo the news feed functionality."""
    api_key = os.environ.get("WORLD_NEWS_API_KEY", "")
    
    print("=" * 60)
    print("AUREON NEWS FEED DEMO")
    print("=" * 60)
    
    config = NewsFeedConfig(
        api_key=api_key,
        max_articles=20
    )
    
    async with NewsFeed(config) as feed:
        # Search for market news
        print("\n[1] Searching for market news...")
        articles = await feed.fetch_market_news()
        print(f"    Found {len(articles)} articles")
        
        if articles:
            # Show some headlines
            print("\n[2] Sample headlines:")
            for article in articles[:5]:
                print(f"    [{article.sentiment_label:^8}] {article.title[:70]}...")
            
            # Sentiment analysis
            print("\n[3] Sentiment Analysis:")
            analysis = feed.analyze_sentiment_aggregate(articles)
            print(f"    Average sentiment: {analysis['average_sentiment']}")
            print(f"    Overall label: {analysis['sentiment_label']}")
            print(f"    Confidence: {analysis['confidence']}")
            print(f"    Bullish/Bearish/Neutral: {analysis['bullish_ratio']:.0%}/{analysis['bearish_ratio']:.0%}/{analysis['neutral_ratio']:.0%}")
            
            # Market signals
            print("\n[4] Market Signals:")
            signals = feed.extract_market_signals(articles)
            print(f"    Crypto sentiment: {signals['crypto_sentiment']}")
            print(f"    Stock sentiment: {signals['stock_sentiment']}")
            print(f"    Risk level: {signals['risk_level']}")
            print(f"    Key themes: {signals['key_themes']}")
            
            if signals['alerts']:
                print(f"\n[5] Alerts ({len(signals['alerts'])}):")
                for alert in signals['alerts'][:3]:
                    print(f"    • {alert['sentiment_label'].upper()}: {alert['title'][:50]}...")
        
        # Status
        print("\n[6] Feed Status:")
        status = feed.get_status()
        print(f"    API calls: {status['metrics']['api_calls']}")
        print(f"    Total fetched: {status['metrics']['total_articles_fetched']}")
        print(f"    Errors: {status['metrics']['errors']}")
    
    print("\n" + "=" * 60)
    print("Demo complete!")


if __name__ == "__main__":
    asyncio.run(demo())
