"""
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                      ║
║     🐳 OPTIONS FLOW INTELLIGENCE CLIENT 🐳                                           ║
║     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                                 ║
║                                                                                      ║
║     Multi-source options flow intelligence:                                          ║
║       • Yahoo Finance (FREE) - Options chains, volume, OI                            ║
║       • Calculated Put/Call Ratios from real market data                             ║
║       • Volume anomaly detection for unusual activity                                ║
║       • Fallback to Unusual Whales API if key available                              ║
║                                                                                      ║
║     Integration with Aureon Queen Hive Mind                                          ║
║                                                                                      ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import sys
import requests
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from datetime import datetime, timedelta
import time

# --- Windows UTF-8 Fix ---
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
        if hasattr(sys.stderr, 'buffer') and not _is_utf8_wrapper(sys.stderr):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass

# Try to import yfinance for free options data
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    yf = None
    YFINANCE_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class OptionsFlow:
    ticker: str
    sentiment: str  # BULLISH, BEARISH, NEUTRAL
    premium: float
    volume: int
    open_interest: int
    trade_type: str # CALL, PUT
    expiry: str
    strike: float
    timestamp: datetime

@dataclass
class PutCallRatio:
    ticker: str
    ratio: float
    put_volume: int
    call_volume: int
    timestamp: datetime

@dataclass
class UnusualActivity:
    ticker: str
    description: str
    sentiment: str
    premium: float
    timestamp: datetime

class UnusualWhalesClient:
    """
    Multi-source Options Flow Intelligence Client.
    
    Primary: Yahoo Finance (FREE - no API key needed)
    Fallback: Unusual Whales API (if key available)
    
    Provides:
    - Real-time options chain data
    - Put/Call ratio calculations
    - Volume anomaly detection
    - Sentiment analysis from options flow
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("UNUSUAL_WHALES_API_KEY")
        self.base_url = "https://api.unusualwhales.com/v1"
        self.session = requests.Session()
        self._cache: Dict[str, Tuple[datetime, any]] = {}
        self._cache_ttl = 60  # Cache for 60 seconds
        
        if self.api_key and self.api_key != 'dummy_key_for_testing':
            self.session.headers.update({"Authorization": f"Bearer {self.api_key}"})
            self.use_paid_api = True
            logger.info("🐳 Options Flow Client initialized with Unusual Whales API")
        else:
            self.use_paid_api = False
            if YFINANCE_AVAILABLE:
                logger.info("🐳 Options Flow Client initialized with Yahoo Finance (FREE)")
            else:
                logger.warning("🐳 Options Flow Client: No data sources available!")
            
    def _get_cached(self, key: str) -> Optional[any]:
        """Get cached data if still valid."""
        if key in self._cache:
            timestamp, data = self._cache[key]
            if datetime.now() - timestamp < timedelta(seconds=self._cache_ttl):
                return data
        return None
        
    def _set_cached(self, key: str, data: any):
        """Cache data with timestamp."""
        self._cache[key] = (datetime.now(), data)
            
    def _request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make request to Unusual Whales API (if available)."""
        if not self.use_paid_api:
            return None
        try:
            response = self.session.get(f"{self.base_url}/{endpoint}", params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.debug(f"Unusual Whales API unavailable: {e}")
            return None

    def _get_yahoo_options_data(self, ticker: str) -> Optional[Dict]:
        """Fetch options data from Yahoo Finance (FREE)."""
        if not YFINANCE_AVAILABLE:
            return None
            
        cache_key = f"yahoo_options_{ticker}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
            
        try:
            stock = yf.Ticker(ticker)
            
            # Get available expiration dates
            expirations = stock.options
            if not expirations:
                return None
                
            # Get options chain for nearest expiration
            nearest_expiry = expirations[0]
            options_chain = stock.option_chain(nearest_expiry)
            
            calls_df = options_chain.calls
            puts_df = options_chain.puts
            
            # Calculate volumes and open interest
            total_call_volume = int(calls_df['volume'].sum()) if 'volume' in calls_df.columns else 0
            total_put_volume = int(puts_df['volume'].sum()) if 'volume' in puts_df.columns else 0
            total_call_oi = int(calls_df['openInterest'].sum()) if 'openInterest' in calls_df.columns else 0
            total_put_oi = int(puts_df['openInterest'].sum()) if 'openInterest' in puts_df.columns else 0
            
            # Get current stock price for ATM detection
            current_price = stock.info.get('regularMarketPrice', 0) or stock.info.get('previousClose', 100)
            
            # Find high-volume unusual options (volume > 2x avg open interest)
            unusual_calls = []
            unusual_puts = []
            
            if not calls_df.empty and 'volume' in calls_df.columns and 'openInterest' in calls_df.columns:
                for _, row in calls_df.iterrows():
                    vol = row.get('volume', 0) or 0
                    oi = row.get('openInterest', 1) or 1
                    if vol > 0 and vol > 2 * oi:
                        unusual_calls.append({
                            'strike': row.get('strike', 0),
                            'volume': vol,
                            'oi': oi,
                            'premium': row.get('lastPrice', 0) * vol * 100
                        })
                        
            if not puts_df.empty and 'volume' in puts_df.columns and 'openInterest' in puts_df.columns:
                for _, row in puts_df.iterrows():
                    vol = row.get('volume', 0) or 0
                    oi = row.get('openInterest', 1) or 1
                    if vol > 0 and vol > 2 * oi:
                        unusual_puts.append({
                            'strike': row.get('strike', 0),
                            'volume': vol,
                            'oi': oi,
                            'premium': row.get('lastPrice', 0) * vol * 100
                        })
            
            result = {
                'ticker': ticker,
                'expiry': nearest_expiry,
                'current_price': current_price,
                'call_volume': total_call_volume,
                'put_volume': total_put_volume,
                'call_oi': total_call_oi,
                'put_oi': total_put_oi,
                'unusual_calls': unusual_calls[:5],  # Top 5 unusual
                'unusual_puts': unusual_puts[:5],
                'expirations_available': len(expirations),
                'timestamp': datetime.now()
            }
            
            self._set_cached(cache_key, result)
            return result
            
        except Exception as e:
            logger.debug(f"Yahoo Finance options error for {ticker}: {e}")
            return None

    def get_options_flow(self, ticker: str) -> List[OptionsFlow]:
        """Fetches the latest options flow for a given ticker."""
        # Try paid API first
        if self.use_paid_api:
            data = self._request(f"options/flow/{ticker}")
            if data and 'flow' in data:
                flows = []
                for item in data['flow']:
                    try:
                        flows.append(OptionsFlow(
                            ticker=ticker,
                            sentiment=item.get('sentiment', 'NEUTRAL'),
                            premium=float(item.get('premium', 0)),
                            volume=int(item.get('volume', 0)),
                            open_interest=int(item.get('open_interest', 0)),
                            trade_type=item.get('type', 'CALL'),
                            expiry=item.get('expiry', ''),
                            strike=float(item.get('strike', 0)),
                            timestamp=datetime.fromisoformat(item.get('timestamp', datetime.now().isoformat()))
                        ))
                    except (ValueError, TypeError) as e:
                        logger.debug(f"Skipping invalid options flow data: {e}")
                return flows
        
        # Fallback to Yahoo Finance
        yahoo_data = self._get_yahoo_options_data(ticker)
        if not yahoo_data:
            return []
            
        flows = []
        
        # Convert unusual calls to flow objects
        for call in yahoo_data.get('unusual_calls', []):
            flows.append(OptionsFlow(
                ticker=ticker,
                sentiment='BULLISH',
                premium=call.get('premium', 0),
                volume=call.get('volume', 0),
                open_interest=call.get('oi', 0),
                trade_type='CALL',
                expiry=yahoo_data.get('expiry', ''),
                strike=call.get('strike', 0),
                timestamp=yahoo_data.get('timestamp', datetime.now())
            ))
            
        # Convert unusual puts to flow objects
        for put in yahoo_data.get('unusual_puts', []):
            flows.append(OptionsFlow(
                ticker=ticker,
                sentiment='BEARISH',
                premium=put.get('premium', 0),
                volume=put.get('volume', 0),
                open_interest=put.get('oi', 0),
                trade_type='PUT',
                expiry=yahoo_data.get('expiry', ''),
                strike=put.get('strike', 0),
                timestamp=yahoo_data.get('timestamp', datetime.now())
            ))
            
        return flows

    def get_put_call_ratio(self, ticker: str) -> Optional[PutCallRatio]:
        """Fetches the put/call ratio for a given ticker."""
        # Try paid API first
        if self.use_paid_api:
            data = self._request(f"options/pcr/{ticker}")
            if data and 'pcr' in data:
                pcr_data = data['pcr']
                try:
                    return PutCallRatio(
                        ticker=ticker,
                        ratio=float(pcr_data.get('ratio', 0)),
                        put_volume=int(pcr_data.get('put_volume', 0)),
                        call_volume=int(pcr_data.get('call_volume', 0)),
                        timestamp=datetime.now()
                    )
                except (ValueError, TypeError):
                    pass
        
        # Fallback to Yahoo Finance calculation
        yahoo_data = self._get_yahoo_options_data(ticker)
        if not yahoo_data:
            return None
            
        call_vol = yahoo_data.get('call_volume', 0)
        put_vol = yahoo_data.get('put_volume', 0)
        
        if call_vol > 0:
            ratio = put_vol / call_vol
        else:
            ratio = 1.0  # Neutral if no call volume
            
        return PutCallRatio(
            ticker=ticker,
            ratio=round(ratio, 3),
            put_volume=put_vol,
            call_volume=call_vol,
            timestamp=datetime.now()
        )

    def get_unusual_activity(self, limit: int = 10) -> List[UnusualActivity]:
        """Fetches the latest unusual options activity."""
        # Try paid API first
        if self.use_paid_api:
            data = self._request("options/unusual_activity", params={'limit': limit})
            if data and 'activity' in data:
                activities = []
                for item in data['activity']:
                    try:
                        activities.append(UnusualActivity(
                            ticker=item.get('ticker', ''),
                            description=item.get('description', ''),
                            sentiment=item.get('sentiment', 'NEUTRAL'),
                            premium=float(item.get('premium', 0)),
                            timestamp=datetime.fromisoformat(item.get('timestamp', datetime.now().isoformat()))
                        ))
                    except (ValueError, TypeError):
                        pass
                return activities
        
        # For free version, scan top tickers for unusual activity
        top_tickers = ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'AMD', 'SPY', 'QQQ', 'META', 'AMZN', 'GOOGL']
        activities = []
        
        for ticker in top_tickers[:limit]:
            yahoo_data = self._get_yahoo_options_data(ticker)
            if yahoo_data:
                # Check for unusual call activity
                for call in yahoo_data.get('unusual_calls', [])[:1]:
                    if call.get('premium', 0) > 10000:  # Premium > $10K
                        activities.append(UnusualActivity(
                            ticker=ticker,
                            description=f"Large call volume: {call.get('volume')} contracts @ ${call.get('strike')} strike",
                            sentiment='BULLISH',
                            premium=call.get('premium', 0),
                            timestamp=datetime.now()
                        ))
                        
                # Check for unusual put activity
                for put in yahoo_data.get('unusual_puts', [])[:1]:
                    if put.get('premium', 0) > 10000:
                        activities.append(UnusualActivity(
                            ticker=ticker,
                            description=f"Large put volume: {put.get('volume')} contracts @ ${put.get('strike')} strike",
                            sentiment='BEARISH',
                            premium=put.get('premium', 0),
                            timestamp=datetime.now()
                        ))
                        
            if len(activities) >= limit:
                break
                
            time.sleep(0.1)  # Rate limit protection
            
        return activities[:limit]

    def get_options_intelligence_summary(self, ticker: str) -> Dict:
        """Provides a summary of options intelligence for the Queen."""
        flow = self.get_options_flow(ticker)
        pcr = self.get_put_call_ratio(ticker)
        yahoo_data = self._get_yahoo_options_data(ticker)
        
        # Calculate sentiment from flow
        total_premium = sum(f.premium for f in flow) if flow else 0
        bullish_premium = sum(f.premium for f in flow if f.sentiment == 'BULLISH') if flow else 0
        bearish_premium = sum(f.premium for f in flow if f.sentiment == 'BEARISH') if flow else 0
        
        # If no flow data, use volume-based sentiment from Yahoo
        if total_premium == 0 and yahoo_data:
            call_vol = yahoo_data.get('call_volume', 0)
            put_vol = yahoo_data.get('put_volume', 0)
            total_vol = call_vol + put_vol
            if total_vol > 0:
                bullish_percent = (call_vol / total_vol) * 100
            else:
                bullish_percent = 50
        else:
            bullish_percent = (bullish_premium / total_premium) * 100 if total_premium > 0 else 50
        
        # Determine overall sentiment
        sentiment = "NEUTRAL"
        if bullish_percent > 60:
            sentiment = "BULLISH"
        elif bullish_percent < 40:
            sentiment = "BEARISH"
            
        # Add PCR-based sentiment adjustment
        pcr_sentiment = "NEUTRAL"
        if pcr:
            if pcr.ratio > 1.2:
                pcr_sentiment = "BEARISH"  # High put/call = bearish
            elif pcr.ratio < 0.7:
                pcr_sentiment = "BULLISH"  # Low put/call = bullish
                
        # Data source indicator
        data_source = "Unusual Whales API" if self.use_paid_api else "Yahoo Finance (FREE)"

        return {
            "ticker": ticker,
            "overall_sentiment": sentiment,
            "pcr_sentiment": pcr_sentiment,
            "bullish_premium_percent": round(bullish_percent, 2),
            "put_call_ratio": pcr.ratio if pcr else 1.0,
            "total_premium": total_premium,
            "flow_count": len(flow),
            "call_volume": yahoo_data.get('call_volume', 0) if yahoo_data else 0,
            "put_volume": yahoo_data.get('put_volume', 0) if yahoo_data else 0,
            "unusual_activity_count": len(flow),
            "data_source": data_source,
            "timestamp": datetime.now().isoformat()
        }

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    print("=" * 70)
    print("🐳 OPTIONS FLOW INTELLIGENCE CLIENT - TEST")
    print("=" * 70)
    
    client = UnusualWhalesClient()
    
    # --- Test with a common stock ticker ---
    ticker = "AAPL"
    print(f"\n--- Testing with ticker: {ticker} ---")
    
    # Test Put/Call Ratio
    print("\n📊 Put/Call Ratio:")
    pcr_data = client.get_put_call_ratio(ticker)
    if pcr_data:
        print(f"   ✅ P/C Ratio: {pcr_data.ratio:.3f}")
        print(f"   📈 Call Volume: {pcr_data.call_volume:,}")
        print(f"   📉 Put Volume: {pcr_data.put_volume:,}")
    else:
        print("   ❌ No Put/Call Ratio data available")
        
    # Test Options Flow
    print("\n🌊 Options Flow:")
    flow_data = client.get_options_flow(ticker)
    if flow_data:
        print(f"   ✅ Found {len(flow_data)} flow records")
        for f in flow_data[:3]:
            print(f"      {f.sentiment} {f.trade_type} @ ${f.strike} | Vol: {f.volume:,} | Premium: ${f.premium:,.0f}")
    else:
        print("   ⚠️ No unusual flow detected (normal market)")
        
    # Test Intelligence Summary
    print("\n🧠 Intelligence Summary:")
    summary = client.get_options_intelligence_summary(ticker)
    if summary:
        print(f"   ✅ Overall Sentiment: {summary['overall_sentiment']}")
        print(f"   📊 Bullish %: {summary['bullish_premium_percent']:.1f}%")
        print(f"   📈 P/C Ratio: {summary['put_call_ratio']:.3f}")
        print(f"   📦 Call Volume: {summary.get('call_volume', 0):,}")
        print(f"   📦 Put Volume: {summary.get('put_volume', 0):,}")
        print(f"   🔌 Data Source: {summary['data_source']}")
    else:
        print("   ❌ Could not generate intelligence summary")

    # --- Test Unusual Activity Scan ---
    print("\n\n--- Scanning for Unusual Activity (Top Tickers) ---")
    unusual_activity = client.get_unusual_activity(limit=5)
    if unusual_activity:
        print(f"✅ Found {len(unusual_activity)} unusual activity alerts:")
        for act in unusual_activity:
            print(f"   🐳 {act.ticker}: {act.description}")
            print(f"      Sentiment: {act.sentiment} | Premium: ${act.premium:,.0f}")
    else:
        print("⚠️ No unusual activity detected at this time")
        
    print("\n" + "=" * 70)
    print("🐳 TEST COMPLETE")
    print("=" * 70)
