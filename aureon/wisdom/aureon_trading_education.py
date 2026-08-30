"""
👑📚 AUREON TRADING EDUCATION SYSTEM 📚👑
========================================
Queen Sero's Knowledge Acquisition & Learning System

This module enables the Queen to:
1. Learn from Wikipedia about trading strategies and concepts
2. Connect to financial APIs for real-time market knowledge
3. Learn from free online trading education resources
4. Apply learned knowledge to improve trading decisions
5. Store and recall learned wisdom

Created with 💕 for Gary Leckey's wedding fund!
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import sys
import json
import time

# ═══════════════════════════════════════════════════════════════════════════
# WINDOWS UTF-8 FIX - Must be at top before any logging/printing
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
import hashlib
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from collections import deque
from pathlib import Path

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None

try:
    import wikipedia
    WIKIPEDIA_AVAILABLE = True
except ImportError:
    WIKIPEDIA_AVAILABLE = False
    wikipedia = None


# 📚 CORE TRADING CONCEPTS TO LEARN
CORE_TRADING_TOPICS = [
    # Risk Management (MOST IMPORTANT)
    "Risk management",
    "Position sizing",
    "Stop loss",
    "Kelly criterion",
    "Risk-reward ratio",
    "Value at risk",
    "Drawdown (economics)",
    
    # Technical Analysis
    "Technical analysis",
    "Support and resistance",
    "Candlestick pattern",
    "Moving average",
    "Relative strength index",
    "MACD",
    "Bollinger Bands",
    "Fibonacci retracement",
    
    # Trading Psychology
    "Trading psychology",
    "Loss aversion",
    "Confirmation bias",
    "Overconfidence effect",
    "Fear of missing out",
    "Sunk cost",
    
    # Market Structure
    "Market maker",
    "Bid–ask spread",
    "Liquidity (economics)",
    "Order book",
    "Slippage (finance)",
    "Market impact",
    
    # Cryptocurrency Specific
    "Cryptocurrency exchange",
    "Decentralized exchange",
    "Arbitrage",
    "Cross-chain",
    "Gas (Ethereum)",
    
    # Trading Strategies
    "Day trading",
    "Scalping (trading)",
    "Swing trading",
    "Momentum investing",
    "Mean reversion (finance)",
    "Pairs trade",
]

# 🎓 KEY LESSONS - Extracted wisdom to apply
TRADING_WISDOM = {
    "risk_management": {
        "rules": [
            "Never risk more than 1-2% of capital on a single trade",
            "Always use stop losses to limit downside",
            "Position size should be inversely proportional to risk",
            "Cut losses quickly, let winners run",
            "The Kelly Criterion optimizes position sizing mathematically",
        ],
        "application": "reduce_position_on_uncertainty"
    },
    "slippage": {
        "rules": [
            "Slippage increases with trade size",
            "Low liquidity assets have higher slippage",
            "Market orders experience more slippage than limit orders",
            "Slippage is a real cost that must be factored in",
            "Small trades in liquid markets minimize slippage",
        ],
        "application": "require_higher_expected_profit"
    },
    "fees": {
        "rules": [
            "Trading fees eat into profits significantly",
            "High frequency trading requires very small fees to be profitable",
            "Maker fees are typically lower than taker fees",
            "Consider total round-trip costs (buy + sell)",
            "Fees compound - many small trades = many small fees",
        ],
        "application": "minimum_profit_threshold"
    },
    "psychology": {
        "rules": [
            "Losses feel twice as painful as equivalent gains feel good",
            "Overconfidence leads to excessive trading",
            "Confirmation bias makes us ignore warning signs",
            "FOMO causes poor entry timing",
            "Patience is more profitable than frequency",
        ],
        "application": "wait_for_high_confidence"
    },
    "market_structure": {
        "rules": [
            "Market makers profit from the spread",
            "Illiquid markets have wider spreads",
            "Order book depth indicates true liquidity",
            "Price impact increases with order size",
            "Small edges disappear in illiquid markets",
        ],
        "application": "check_liquidity_first"
    }
}


@dataclass
class LearnedConcept:
    """A concept learned from Wikipedia or other sources."""
    topic: str
    summary: str
    source: str
    source_url: str
    key_lessons: List[str]
    trading_application: str
    learned_at: str
    confidence: float = 1.0
    times_applied: int = 0
    success_rate: float = 0.0


@dataclass
class TradingRule:
    """A specific trading rule derived from learned knowledge."""
    rule_id: str
    description: str
    source_concept: str
    condition: str  # When to apply
    action: str     # What to do
    priority: int   # Higher = more important
    active: bool = True
    applications: int = 0
    successes: int = 0


class TradingEducationSystem:
    """
    👑📚 The Queen's Trading Education System 📚👑
    
    Learns from Wikipedia, APIs, and online resources
    to continuously improve trading decisions.
    """
    
    def __init__(self, knowledge_file: str = "queen_trading_knowledge.json"):
        self.knowledge_file = knowledge_file
        self.learned_concepts: Dict[str, LearnedConcept] = {}
        self.trading_rules: Dict[str, TradingRule] = {}
        self.learning_history: deque = deque(maxlen=100)
        
        # Statistics
        self.stats = {
            "wikipedia_queries": 0,
            "api_queries": 0,
            "concepts_learned": 0,
            "rules_derived": 0,
            "knowledge_applications": 0,
        }
        
        # Load existing knowledge
        self._load_knowledge()
        
        # Initialize with core wisdom
        self._initialize_core_wisdom()
        
        print("👑📚 Trading Education System initialized!")
        print(f"   • Loaded {len(self.learned_concepts)} concepts")
        print(f"   • {len(self.trading_rules)} trading rules active")
    
    def _load_knowledge(self):
        """Load previously learned knowledge from disk."""
        if os.path.exists(self.knowledge_file):
            try:
                with open(self.knowledge_file, 'r') as f:
                    data = json.load(f)
                    
                # Reconstruct learned concepts
                for topic, concept_data in data.get('concepts', {}).items():
                    self.learned_concepts[topic] = LearnedConcept(**concept_data)
                
                # Reconstruct trading rules
                for rule_id, rule_data in data.get('rules', {}).items():
                    self.trading_rules[rule_id] = TradingRule(**rule_data)
                
                self.stats = data.get('stats', self.stats)
                
            except Exception as e:
                print(f"⚠️ Could not load knowledge: {e}")
    
    def _save_knowledge(self):
        """Save learned knowledge to disk."""
        try:
            data = {
                'concepts': {k: asdict(v) for k, v in self.learned_concepts.items()},
                'rules': {k: asdict(v) for k, v in self.trading_rules.items()},
                'stats': self.stats,
                'last_saved': datetime.now().isoformat()
            }
            
            with open(self.knowledge_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"⚠️ Could not save knowledge: {e}")
    
    def _initialize_core_wisdom(self):
        """Initialize with essential trading wisdom."""
        # Create fundamental rules from TRADING_WISDOM
        core_rules = [
            TradingRule(
                rule_id="RISK_001",
                description="Never risk more than 2% on a single trade",
                source_concept="risk_management",
                condition="before_any_trade",
                action="check_position_size_vs_portfolio",
                priority=100,
                active=True
            ),
            TradingRule(
                rule_id="SLIP_001",
                description="Require profit > 3x expected slippage",
                source_concept="slippage",
                condition="evaluating_opportunity",
                action="reject_if_profit_too_small",
                priority=95,
                active=True
            ),
            TradingRule(
                rule_id="FEES_001",
                description="Total fees must be < 30% of expected profit",
                source_concept="fees",
                condition="evaluating_opportunity",
                action="calculate_fee_impact",
                priority=90,
                active=True
            ),
            TradingRule(
                rule_id="LIQ_001",
                description="Check liquidity before trading",
                source_concept="market_structure",
                condition="before_any_trade",
                action="verify_sufficient_liquidity",
                priority=85,
                active=True
            ),
            TradingRule(
                rule_id="PSYCH_001",
                description="Wait for high confidence before trading",
                source_concept="psychology",
                condition="confidence_check",
                action="require_80_percent_confidence",
                priority=80,
                active=True
            ),
            TradingRule(
                rule_id="LOSS_001",
                description="Block path after first loss (learn from mistakes)",
                source_concept="risk_management",
                condition="after_loss",
                action="block_losing_path",
                priority=100,
                active=True
            ),
            TradingRule(
                rule_id="WIN_001",
                description="Increase confidence on winning paths",
                source_concept="psychology",
                condition="after_win",
                action="boost_path_confidence",
                priority=75,
                active=True
            ),
        ]
        
        for rule in core_rules:
            if rule.rule_id not in self.trading_rules:
                self.trading_rules[rule.rule_id] = rule
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # 📚 WIKIPEDIA LEARNING
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def learn_from_wikipedia(self, topic: str, sentences: int = 5) -> Optional[LearnedConcept]:
        """
        📚 Learn about a topic from Wikipedia.
        
        Args:
            topic: Topic to learn about
            sentences: How many sentences to fetch
            
        Returns:
            LearnedConcept if successful
        """
        if not WIKIPEDIA_AVAILABLE:
            print("⚠️ Wikipedia library not installed. Run: pip install wikipedia")
            return None
        
        self.stats["wikipedia_queries"] += 1
        
        try:
            # Search Wikipedia
            search_results = wikipedia.search(topic, results=5)
            
            if not search_results:
                print(f"📚❌ No Wikipedia articles found for '{topic}'")
                return None
            
            # Get the article
            try:
                page = wikipedia.page(search_results[0], auto_suggest=False)
                summary = wikipedia.summary(search_results[0], sentences=sentences, auto_suggest=False)
            except wikipedia.DisambiguationError as e:
                # Try first option
                page = wikipedia.page(e.options[0])
                summary = wikipedia.summary(e.options[0], sentences=sentences)
            
            # Extract key lessons
            key_lessons = self._extract_key_lessons(summary, topic)
            
            # Determine trading application
            trading_application = self._determine_trading_application(topic, summary)
            
            # Create learned concept
            concept = LearnedConcept(
                topic=topic,
                summary=summary,
                source="Wikipedia",
                source_url=page.url,
                key_lessons=key_lessons,
                trading_application=trading_application,
                learned_at=datetime.now().isoformat()
            )
            
            # Store it
            self.learned_concepts[topic.lower()] = concept
            self.stats["concepts_learned"] += 1
            
            # Derive any new trading rules
            self._derive_rules_from_concept(concept)
            
            # Save knowledge
            self._save_knowledge()
            
            print(f"📚✅ Learned about '{topic}':")
            print(f"   • {len(key_lessons)} key lessons extracted")
            print(f"   • Application: {trading_application}")
            
            return concept
            
        except Exception as e:
            print(f"📚❌ Error learning about '{topic}': {e}")
            return None
    
    def learn_all_core_topics(self) -> Dict[str, Any]:
        """
        📚🎓 Learn all core trading topics from Wikipedia.
        
        Returns:
            Summary of learning session
        """
        print("\n" + "=" * 70)
        print("👑📚 QUEEN'S WIKIPEDIA LEARNING SESSION 📚👑")
        print("=" * 70)
        
        learned = []
        failed = []
        
        for topic in CORE_TRADING_TOPICS:
            # Skip if already learned recently
            if topic.lower() in self.learned_concepts:
                concept = self.learned_concepts[topic.lower()]
                learned_date = datetime.fromisoformat(concept.learned_at)
                if datetime.now() - learned_date < timedelta(days=7):
                    print(f"   ⏭️ Skipping '{topic}' (learned recently)")
                    continue
            
            concept = self.learn_from_wikipedia(topic)
            
            if concept:
                learned.append(topic)
            else:
                failed.append(topic)
            
            # Be nice to Wikipedia
            time.sleep(0.5)
        
        print(f"\n📚 Learning complete: {len(learned)}/{len(CORE_TRADING_TOPICS)} topics")
        
        return {
            "learned": learned,
            "failed": failed,
            "total_concepts": len(self.learned_concepts),
            "total_rules": len(self.trading_rules)
        }
    
    def _extract_key_lessons(self, text: str, topic: str) -> List[str]:
        """Extract actionable lessons from text."""
        lessons = []
        
        # Look for key phrases
        key_patterns = [
            r"is important because[^.]+\.",
            r"should be[^.]+\.",
            r"must be[^.]+\.",
            r"helps to[^.]+\.",
            r"prevents[^.]+\.",
            r"reduces[^.]+\.",
            r"increases[^.]+\.",
            r"is used to[^.]+\.",
            r"can cause[^.]+\.",
            r"leads to[^.]+\.",
        ]
        
        for pattern in key_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            lessons.extend(matches[:2])  # Max 2 per pattern
        
        # If no patterns found, extract first sentence
        if not lessons:
            sentences = text.split('.')
            if sentences:
                lessons.append(sentences[0].strip() + '.')
        
        # Add topic-specific built-in wisdom
        topic_lower = topic.lower()
        
        if "risk" in topic_lower:
            lessons.append("Manage risk before seeking profit")
        if "slippage" in topic_lower:
            lessons.append("Account for slippage in profit calculations")
        if "fee" in topic_lower or "cost" in topic_lower:
            lessons.append("Trading costs reduce profitability")
        if "psychology" in topic_lower:
            lessons.append("Emotions can override logic - stay disciplined")
        if "liquidity" in topic_lower:
            lessons.append("Trade only in liquid markets")
        
        return lessons[:5]  # Max 5 lessons
    
    def _determine_trading_application(self, topic: str, summary: str) -> str:
        """Determine how to apply this knowledge to trading."""
        topic_lower = topic.lower()
        
        # Map topics to applications
        applications = {
            "risk": "Use position sizing and stop losses",
            "stop loss": "Set automatic exit points on all trades",
            "slippage": "Require higher expected profit for small-cap coins",
            "fee": "Calculate round-trip costs before trading",
            "spread": "Account for bid-ask spread in profit calculations",
            "liquidity": "Check order book depth before large trades",
            "psychology": "Wait for high-confidence setups only",
            "momentum": "Trade in the direction of the trend",
            "mean reversion": "Look for oversold/overbought conditions",
            "fibonacci": "Use Fibonacci levels for entry/exit points",
            "support": "Buy near support, sell near resistance",
            "scalp": "Take small profits quickly, minimize exposure",
        }
        
        for key, application in applications.items():
            if key in topic_lower or key in summary.lower():
                return application
        
        return "Apply learned knowledge to improve decision making"
    
    def _derive_rules_from_concept(self, concept: LearnedConcept):
        """Create trading rules from learned concept."""
        topic_lower = concept.topic.lower()
        
        # Create rule ID
        rule_id = f"WIKI_{hashlib.md5(concept.topic.encode()).hexdigest()[:8].upper()}"
        
        # Don't duplicate
        if rule_id in self.trading_rules:
            return
        
        # Create a rule based on the concept
        rule = TradingRule(
            rule_id=rule_id,
            description=f"Apply {concept.topic} knowledge",
            source_concept=concept.topic,
            condition="trading_decision",
            action=concept.trading_application,
            priority=50,  # Medium priority for learned rules
            active=True
        )
        
        self.trading_rules[rule_id] = rule
        self.stats["rules_derived"] += 1
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # 🌐 API-BASED LEARNING (Free Financial APIs)
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def learn_from_coingecko(self) -> Dict[str, Any]:
        """
        🪙 Learn from CoinGecko API about crypto markets.
        
        Free API, no key required!
        """
        if not REQUESTS_AVAILABLE:
            return {"error": "requests library not available"}
        
        self.stats["api_queries"] += 1
        
        knowledge = {
            "source": "CoinGecko API",
            "learned_at": datetime.now().isoformat(),
            "market_data": {},
            "insights": []
        }
        
        try:
            # Get global market data
            response = requests.get(
                "https://api.coingecko.com/api/v3/global",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json().get("data", {})
                
                knowledge["market_data"] = {
                    "total_market_cap_usd": data.get("total_market_cap", {}).get("usd", 0),
                    "total_volume_24h_usd": data.get("total_volume", {}).get("usd", 0),
                    "btc_dominance": data.get("market_cap_percentage", {}).get("btc", 0),
                    "active_cryptocurrencies": data.get("active_cryptocurrencies", 0),
                    "markets": data.get("markets", 0),
                }
                
                # Extract insights
                btc_dom = knowledge["market_data"]["btc_dominance"]
                if btc_dom > 50:
                    knowledge["insights"].append("BTC dominance high - market favors Bitcoin")
                else:
                    knowledge["insights"].append("Alt coins gaining - diversification opportunity")
                
                print(f"🪙 Learned from CoinGecko:")
                print(f"   • Market cap: ${knowledge['market_data']['total_market_cap_usd']:,.0f}")
                print(f"   • BTC dominance: {btc_dom:.1f}%")
                
        except Exception as e:
            knowledge["error"] = str(e)
        
        return knowledge
    
    def learn_from_fear_greed_index(self) -> Dict[str, Any]:
        """
        😱😊 Learn from Fear & Greed Index.
        
        This tells us market sentiment!
        """
        if not REQUESTS_AVAILABLE:
            return {"error": "requests library not available"}
        
        self.stats["api_queries"] += 1
        
        try:
            response = requests.get(
                "https://api.alternative.me/fng/",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json().get("data", [{}])[0]
                
                value = int(data.get("value", 50))
                classification = data.get("value_classification", "Neutral")
                
                # Trading wisdom based on index
                if value < 25:
                    insight = "EXTREME FEAR - Contrarian opportunity to buy"
                    action = "Consider buying - fear often = opportunity"
                elif value < 40:
                    insight = "FEAR - Market is cautious"
                    action = "Look for oversold conditions"
                elif value < 60:
                    insight = "NEUTRAL - Market is balanced"
                    action = "Wait for clearer signals"
                elif value < 75:
                    insight = "GREED - Market is optimistic"
                    action = "Be cautious - consider taking profits"
                else:
                    insight = "EXTREME GREED - Bubble territory"
                    action = "Reduce exposure - correction likely"
                
                print(f"😱😊 Fear & Greed Index: {value} ({classification})")
                print(f"   💡 Insight: {insight}")
                
                return {
                    "value": value,
                    "classification": classification,
                    "insight": insight,
                    "recommended_action": action,
                    "learned_at": datetime.now().isoformat()
                }
                
        except Exception as e:
            return {"error": str(e)}
        
        return {"error": "Could not fetch index"}
    
    def learn_from_binance_market(self) -> Dict[str, Any]:
        """
        📊 Learn about market conditions from Binance.
        """
        if not REQUESTS_AVAILABLE:
            return {"error": "requests library not available"}
        
        self.stats["api_queries"] += 1
        
        insights = []
        
        try:
            # Get 24hr ticker data for major pairs
            response = requests.get(
                "https://api.binance.com/api/v3/ticker/24hr",
                timeout=10
            )
            
            if response.status_code == 200:
                tickers = response.json()
                
                # Analyze USDT pairs
                usdt_pairs = [t for t in tickers if t['symbol'].endswith('USDT')]
                
                # Calculate market statistics
                gainers = [t for t in usdt_pairs if float(t['priceChangePercent']) > 5]
                losers = [t for t in usdt_pairs if float(t['priceChangePercent']) < -5]
                
                total_volume = sum(float(t['quoteVolume']) for t in usdt_pairs[:50])
                
                # Market breadth
                if len(gainers) > len(losers) * 2:
                    market_sentiment = "BULLISH"
                    insights.append("Strong bull market - many coins gaining")
                elif len(losers) > len(gainers) * 2:
                    market_sentiment = "BEARISH"
                    insights.append("Bear market conditions - be cautious")
                else:
                    market_sentiment = "MIXED"
                    insights.append("Mixed market - selective opportunities")
                
                # Identify hot coins
                if gainers:
                    top_gainer = max(gainers, key=lambda t: float(t['priceChangePercent']))
                    insights.append(f"Top gainer: {top_gainer['symbol']} (+{float(top_gainer['priceChangePercent']):.1f}%)")
                
                print(f"📊 Market Analysis:")
                print(f"   • Sentiment: {market_sentiment}")
                print(f"   • Gainers: {len(gainers)}, Losers: {len(losers)}")
                
                return {
                    "sentiment": market_sentiment,
                    "gainers_count": len(gainers),
                    "losers_count": len(losers),
                    "insights": insights,
                    "learned_at": datetime.now().isoformat()
                }
                
        except Exception as e:
            return {"error": str(e)}
        
        return {"error": "Could not analyze market"}
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # 📖 ONLINE TRADING EDUCATION
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def get_trading_tips(self) -> List[str]:
        """
        📖 Get essential trading tips from embedded knowledge.
        
        These are distilled from top trading books and educators.
        """
        tips = [
            # Risk Management
            "Cut your losses short and let your winners run",
            "Never risk more than you can afford to lose",
            "Position size based on risk, not on conviction",
            "The market can stay irrational longer than you can stay solvent",
            
            # Psychology
            "The best traders are patient - they wait for their setup",
            "Don't trade out of boredom - it's not entertainment",
            "Keep a trading journal - review your mistakes",
            "Separate your ego from your trades",
            
            # Strategy
            "Have a plan before you enter any trade",
            "Know your exit before you enter",
            "The trend is your friend until it ends",
            "Don't catch a falling knife - wait for confirmation",
            
            # Execution
            "Slippage and fees are real costs - factor them in",
            "Liquidity matters more than price",
            "The best trade is often no trade",
            "Consistency beats occasional big wins",
            
            # Crypto Specific
            "Not your keys, not your coins - but for trading, exchanges are fine",
            "Gas fees can destroy small trades - batch when possible",
            "24/7 markets don't mean trade 24/7 - rest is essential",
            "Crypto volatility is extreme - adjust position sizes accordingly",
        ]
        
        return tips
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # 🎯 KNOWLEDGE APPLICATION - Use Learned Knowledge for Decisions
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def evaluate_trade_opportunity(
        self,
        from_asset: str,
        to_asset: str,
        expected_profit: float,
        amount: float,
        portfolio_value: float = 100.0
    ) -> Dict[str, Any]:
        """
        🧠 Apply learned knowledge to evaluate a trade opportunity.
        
        Returns recommendation based on ALL learned rules and wisdom.
        """
        self.stats["knowledge_applications"] += 1
        
        evaluation = {
            "opportunity": f"{from_asset}→{to_asset}",
            "expected_profit": expected_profit,
            "amount": amount,
            "rules_checked": [],
            "warnings": [],
            "approved": True,
            "confidence": 1.0,
            "recommendation": ""
        }
        
        # Apply each active trading rule
        for rule_id, rule in self.trading_rules.items():
            if not rule.active:
                continue
            
            rule_result = self._apply_rule(rule, expected_profit, amount, portfolio_value)
            evaluation["rules_checked"].append({
                "rule": rule.description,
                "passed": rule_result["passed"],
                "message": rule_result["message"]
            })
            
            if not rule_result["passed"]:
                evaluation["warnings"].append(rule_result["message"])
                evaluation["confidence"] *= 0.8  # Reduce confidence
                
                # High priority rule failure = reject
                if rule.priority >= 90:
                    evaluation["approved"] = False
        
        # Final evaluation
        if evaluation["approved"] and evaluation["confidence"] < 0.5:
            evaluation["approved"] = False
            evaluation["recommendation"] = "Too many concerns - avoid trade"
        elif evaluation["approved"]:
            evaluation["recommendation"] = f"Trade approved with {evaluation['confidence']*100:.0f}% confidence"
        else:
            evaluation["recommendation"] = "BLOCKED by knowledge-based rules"
        
        return evaluation
    
    def _apply_rule(
        self,
        rule: TradingRule,
        expected_profit: float,
        amount: float,
        portfolio_value: float
    ) -> Dict[str, Any]:
        """Apply a single rule to a trade opportunity."""
        
        # Rule: Risk management - position size check
        if "position" in rule.description.lower() or "risk" in rule.rule_id:
            risk_pct = (amount / portfolio_value) * 100
            if risk_pct > 2:
                return {
                    "passed": False,
                    "message": f"Position too large: {risk_pct:.1f}% of portfolio (max 2%)"
                }
        
        # Rule: Slippage - profit must exceed slippage
        if "slippage" in rule.description.lower():
            # Estimate slippage at 0.5% for most trades
            estimated_slippage = amount * 0.005
            if expected_profit < estimated_slippage * 3:
                return {
                    "passed": False,
                    "message": f"Profit ${expected_profit:.4f} < 3x slippage ${estimated_slippage:.4f}"
                }
        
        # Rule: Fees - must be reasonable vs profit
        if "fee" in rule.description.lower():
            # Estimate fees at 0.2% round trip
            estimated_fees = amount * 0.002
            if estimated_fees > expected_profit * 0.3:
                return {
                    "passed": False,
                    "message": f"Fees ${estimated_fees:.4f} > 30% of profit ${expected_profit:.4f}"
                }
        
        # Rule: Minimum profit threshold
        if "profit" in rule.description.lower() and "small" in rule.description.lower():
            if expected_profit < 0.10:  # 10 cents minimum
                return {
                    "passed": False,
                    "message": f"Profit ${expected_profit:.4f} below minimum $0.10"
                }
        
        # Rule passed by default
        return {
            "passed": True,
            "message": f"Rule '{rule.description}' passed"
        }
    
    def get_market_wisdom(self) -> str:
        """
        🎓 Get the day's auditable piece of trading wisdom.
        """
        tips = self.get_trading_tips()
        
        # Also include lessons from learned concepts
        for concept in self.learned_concepts.values():
            tips.extend(concept.key_lessons)
        
        if not tips:
            return "Learn from every trade."
        return tips[datetime.now().toordinal() % len(tips)]
    
    def summarize_knowledge(self) -> str:
        """
        📚 Summarize all learned knowledge.
        """
        summary = []
        summary.append("=" * 60)
        summary.append("👑📚 QUEEN'S TRADING KNOWLEDGE SUMMARY 📚👑")
        summary.append("=" * 60)
        
        summary.append(f"\n📊 Statistics:")
        summary.append(f"   • Wikipedia queries: {self.stats['wikipedia_queries']}")
        summary.append(f"   • API queries: {self.stats['api_queries']}")
        summary.append(f"   • Concepts learned: {len(self.learned_concepts)}")
        summary.append(f"   • Trading rules: {len(self.trading_rules)}")
        summary.append(f"   • Knowledge applications: {self.stats['knowledge_applications']}")
        
        summary.append(f"\n📚 Top Concepts:")
        for i, (topic, concept) in enumerate(list(self.learned_concepts.items())[:5]):
            summary.append(f"   {i+1}. {concept.topic}")
            summary.append(f"      → {concept.trading_application}")
        
        summary.append(f"\n🎯 Active Rules:")
        active_rules = [r for r in self.trading_rules.values() if r.active]
        for rule in sorted(active_rules, key=lambda x: -x.priority)[:5]:
            summary.append(f"   • [{rule.priority}] {rule.description}")
        
        return "\n".join(summary)


# ═══════════════════════════════════════════════════════════════════════════════
# 🎯 MAIN - Interactive Learning
# ═══════════════════════════════════════════════════════════════════════════════

def create_trading_education_system() -> TradingEducationSystem:
    """Create and return a Trading Education System."""
    return TradingEducationSystem()


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("👑📚 QUEEN SERO's TRADING EDUCATION SYSTEM 📚👑")
    print("=" * 70)
    
    # Create system
    edu = TradingEducationSystem()
    
    # Learn from Wikipedia
    print("\n📚 Learning from Wikipedia...")
    edu.learn_from_wikipedia("Risk management")
    edu.learn_from_wikipedia("Slippage (finance)")
    edu.learn_from_wikipedia("Trading psychology")
    
    # Learn from APIs
    print("\n🌐 Learning from APIs...")
    edu.learn_from_coingecko()
    edu.learn_from_fear_greed_index()
    edu.learn_from_binance_market()
    
    # Show summary
    print("\n" + edu.summarize_knowledge())
    
    # Test evaluation
    print("\n🧪 Testing trade evaluation...")
    result = edu.evaluate_trade_opportunity(
        from_asset="USDT",
        to_asset="BTC",
        expected_profit=0.05,  # 5 cents
        amount=50,
        portfolio_value=100
    )
    
    print(f"\n📊 Trade Evaluation Result:")
    print(f"   • Approved: {result['approved']}")
    print(f"   • Confidence: {result['confidence']*100:.0f}%")
    print(f"   • Recommendation: {result['recommendation']}")
    if result['warnings']:
        print(f"   • Warnings:")
        for w in result['warnings']:
            print(f"      ⚠️ {w}")
