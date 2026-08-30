from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys, os
if sys.platform == 'win32' and sys.stdout is sys.__stdout__ and sys.stdout.isatty():
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        import io
        def _is_utf8_wrapper(stream):
            """Check if stream is already a UTF-8 TextIOWrapper."""
            return (isinstance(stream, io.TextIOWrapper) and 
                    hasattr(stream, 'encoding') and stream.encoding and
                    stream.encoding.lower().replace('-', '') == 'utf8')
        def _is_buffer_valid(stream):
            """Check if stream buffer is valid and not closed."""
            if not hasattr(stream, 'buffer'):
                return False
            try:
                return stream.buffer is not None and not stream.buffer.closed
            except (ValueError, AttributeError):
                return False
        if _is_buffer_valid(sys.stdout) and not _is_utf8_wrapper(sys.stdout):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        if _is_buffer_valid(sys.stderr) and not _is_utf8_wrapper(sys.stderr):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass

"""
Aureon Dr Auris Throne Chatbot Client - AI Intelligence Augmentation 🧠🤖

Integration with DigitalOcean AI Agents chatbot (Llama 3.3 Instruct 70B)
for Queen decision validation and market intelligence enhancement.

Architecture:
- HTTP client to Dr Auris Throne Chatbot API
- Async query interface for non-blocking integration
- ⚡ HARMONIC COMPRESSED PROMPTS - Minimal tokens to avoid rate limits
- Response parsing with confidence scoring
- Fail-safe: Trading continues if chatbot unavailable

Usage in Queen Gate:
```python
sero = SeroClient()
advice = await sero.ask_trading_decision(
    symbol="BTC/USD",
    side="BUY",
    context={"coherence": 0.85, "queen_confidence": 0.72}
)
if advice and advice.confidence > 0.7:
    # Blend Dr Auris Throne signal into Queen decision
    pass
```
"""

import os
import asyncio
import aiohttp
import logging
import time
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Optional, Dict, Any
from dotenv import load_dotenv

from aureon.ollama_config import (
    ensure_ollama_runtime_config,
    ollama_config_snapshot,
    resolve_external_llm_fallback,
)

load_dotenv()
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# ⚡ HARMONIC HFT COMPRESSION - MINIMAL TOKENS FOR DR. AURIS
# ═══════════════════════════════════════════════════════════════════════════════
# Problem: Rate limited by token count - need to compress prompts to ~50 tokens
# Solution: Use harmonic alphabet shortcodes + numeric encoding
#
# OLD PROMPT: ~200 tokens → Rate Limited!
# NEW PROMPT: ~40 tokens → ✅ Passes!
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SeroAdvice:
    """Structured response from Dr Auris Throne Chatbot."""
    recommendation: str  # "PROCEED", "CAUTION", "ABORT"
    confidence: float  # 0.0-1.0
    reasoning: str
    risk_flags: list
    timestamp: float

class SeroClient:
    """
    Client for Dr Auris Throne Chatbot (Llama 3.3 Instruct 70B) intelligence augmentation.
    
    ⚡ HFT-OPTIMIZED: Uses compressed harmonic prompts to minimize token usage
    
    Provides async interface to query external AI agent for:
    - Trade decision validation
    - Market pattern recognition
    - Risk assessment
    - Anomaly detection
    """
    
    def __init__(self):
        ensure_ollama_runtime_config()
        self.endpoint = os.getenv('AUREON_AGENT_ENDPOINT', '')
        self.agent_id = os.getenv('AUREON_AGENT_ID', '')
        self.chatbot_id = os.getenv('AUREON_CHATBOT_ID', '')
        # DigitalOcean widget uses chatbot_id as API key; allow override via AUREON_AGENT_KEY
        self.api_key = os.getenv('AUREON_AGENT_KEY', '') or self.chatbot_id
        
        self.provider_enabled = bool(self.endpoint and self.api_key and self.agent_id and self.chatbot_id)
        fallback = ollama_config_snapshot()
        self.fallback_enabled = bool(
            resolve_external_llm_fallback() == "ollama"
            and fallback.get("cloud")
            and fallback.get("authorization_header_enabled")
        )
        self.enabled = self.provider_enabled or self.fallback_enabled
        self.route = (
            "digitalocean_agent"
            if self.provider_enabled
            else ("ollama_cloud" if self.fallback_enabled else "disabled")
        )
        self._fallback_adapter = None
        self.timeout = aiohttp.ClientTimeout(total=15.0)  # 15s max
        
        # ⚡ HFT RATE LIMIT TRACKING
        self._last_call_time = 0
        self._rate_limit_until = 0  # Timestamp when rate limit expires
        # Allow override via env to match DigitalOcean rate limits
        self._min_call_interval = float(os.getenv('AUREON_AURIS_MIN_INTERVAL', '15'))  # seconds
        self._calls_this_minute = 0
        self._minute_start = time.time()
        self._max_calls_per_minute = int(os.getenv('AUREON_AURIS_MAX_PER_MIN', '6'))
        
        # ⚡ TOKEN CACHING - Don't request new token every call!
        self._cached_token = None
        self._token_expiry = 0  # Unix timestamp when token expires
        self._token_ttl = 300  # 5 minute token cache TTL
        
        if not self.enabled:
            logger.warning("Dr Auris Throne Chatbot not configured - AI augmentation disabled")
        else:
            logger.info("Dr Auris Throne intelligence enabled: route=%s", self.route)
    
    async def ask_trading_decision(
        self,
        symbol: str,
        side: str,
        context: Dict[str, Any],
        queen_confidence: float
    ) -> Optional[SeroAdvice]:
        """
        Ask Dr Auris Throne to validate a trading decision.
        
        Args:
            symbol: Trading pair (e.g., "BTC/USD")
            side: "BUY" or "SELL"
            context: Dict with coherence, fusion_bias, threat_level, etc.
            queen_confidence: Queen neuron's current confidence (0-1)
        
        Returns:
            Dr Auris Throne advice if successful, None if unavailable/error
        """
        if not self.enabled:
            return None
        
        # Build concise prompt for trading context
        prompt = self._build_trading_prompt(symbol, side, context, queen_confidence)
        
        try:
            response = await self._query_model(prompt)
            if response is None:
                raise Exception("Dr Auris Throne returned no response")
            return self._parse_trading_response(response)
        except Exception as e:
            # Propagate to caller so dual-vote retry logic can backoff and retry
            logger.warning(f"Dr Auris Throne query failed: {type(e).__name__} {repr(e)}")
            raise
    
    async def ask_market_intelligence(self, query: str) -> Optional[str]:
        """
        General-purpose market intelligence query.
        
        Args:
            query: Natural language question about markets/patterns
        
        Returns:
            Response text or None if unavailable
        """
        if not self.enabled:
            return None
        
        try:
            response = await self._query_model(query)
            return self._extract_message_from_response(response)
        except Exception as e:
            logger.warning(f"Dr Auris Throne intelligence query failed: {type(e).__name__} {repr(e)}")
            return None
    
    def _build_trading_prompt(
        self,
        symbol: str,
        side: str,
        context: Dict[str, Any],
        queen_confidence: float
    ) -> str:
        """
        Build COMPRESSED harmonic prompt for trading decision validation.
        
        ⚡ HFT COMPRESSION: Reduces ~200 tokens → ~40 tokens
        Uses harmonic shortcodes to avoid rate limits while preserving meaning.
        
        Harmonic Shortcodes:
        - SYM = Symbol (e.g., BTCUSDT)
        - ACT = Action (BUY/SELL)
        - QC = Queen Confidence (0-1)
        - PNL = Profit/Loss ($ or %)
        - EP = Entry Price
        - CP = Current Price
        """
        # Extract context values with defaults
        pnl = context.get('pnl', 0)
        entry = context.get('entry_price', 0)
        current = context.get('current_price', 0)
        pct = context.get('profit_percent', 0)
        exch = context.get('exchange', 'UNK')[:3].upper()
        
        # ═══════════════════════════════════════════════════════════════
        # ⚡ HARMONIC MICRO-PACKET FORMAT (HFT-Optimized)
        # ═══════════════════════════════════════════════════════════════
        # Format: EXCH:SYM ACT PNL% QC → PROCEED/HOLD?
        # Example: BIN:BNBUSDC SELL +2.5% QC85 → ?
        # 
        # Response expected: PROCEED 0.8 or HOLD 0.6
        # ═══════════════════════════════════════════════════════════════
        
        # Build ultra-compact prompt (~35-45 tokens)
        prompt = f"""{exch}:{symbol} {side} {pct:+.1f}% QC{queen_confidence*100:.0f}
EP{entry:.2f}→CP{current:.2f} PNL${pnl:.2f}
Reply: PROCEED/CAUTION/ABORT + 0.0-1.0 + reason"""
        
        return prompt
    
    async def _query_api(self, prompt: str) -> Optional[Dict[str, Any]]:
        """
        Send query to Dr Auris Throne Chatbot API using DigitalOcean Agents flow.
        
        ⚡ HFT RATE LIMIT AWARE: Tracks call timing, respects rate limits
        
        Args:
            prompt: Text prompt to send (should be pre-compressed)
        
        Returns:
            API response dict or None if failed/rate limited
        """
        if not self.endpoint or not self.agent_id or not self.api_key:
            return None
        
        # ⚡ RATE LIMIT CHECK - Wait if we're still in cooldown from 429
        now = time.time()
        if now < self._rate_limit_until:
            wait_time = self._rate_limit_until - now
            logger.warning(f"Dr Auris rate limited (429 cooldown) - waiting {wait_time:.1f}s")
            await asyncio.sleep(wait_time)
            now = time.time()  # Update after sleep
        
        # ⚡ PER-MINUTE RATE LIMIT - Reset counter each minute
        if now - self._minute_start >= 60:
            self._calls_this_minute = 0
            self._minute_start = now
        
        # ⚡ CHECK IF WE'VE HIT THE PER-MINUTE LIMIT
        if self._calls_this_minute >= self._max_calls_per_minute:
            wait_time = 60 - (now - self._minute_start)
            if wait_time > 0:
                logger.warning(f"Dr Auris per-minute limit ({self._max_calls_per_minute}/min) - waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
                self._calls_this_minute = 0
                self._minute_start = time.time()
                now = time.time()
        
        # ⚡ MINIMUM INTERVAL - Don't hammer the API
        time_since_last = now - self._last_call_time
        if time_since_last < self._min_call_interval:
            await asyncio.sleep(self._min_call_interval - time_since_last)
        
        self._last_call_time = time.time()
        self._calls_this_minute += 1  # Track call count

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            token = await self._get_access_token(session)
            if not token:
                return None

            url = f"{self.endpoint}/api/v1/chat/completions"
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }

            # ⚡ COMPRESSED PAYLOAD - Minimal structure
            payload = {
                'messages': [
                    {
                        'id': f"hft-{int(time.time()*1000)}",
                        'role': 'user',
                        'content': prompt,
                        'sentTime': datetime.now(timezone.utc).isoformat(),
                        'receivedTime': ''
                    }
                ],
                'stream': False,
                'include_functions_info': False,  # ⚡ DISABLED - saves tokens
                'include_retrieval_info': False,  # ⚡ DISABLED - saves tokens
                'include_guardrails_info': False  # ⚡ DISABLED - saves tokens
            }

            try:
                async with session.post(url, json=payload, headers=headers) as resp:
                    if resp.status == 429:
                        # ⚡ RATE LIMITED - Set cooldown and RAISE exception
                        text = await resp.text()
                        retry_after = resp.headers.get('Retry-After')
                        try:
                            cooldown = int(retry_after) if retry_after else 60
                        except ValueError:
                            cooldown = 60
                        logger.error(f"Dr Auris Throne API error: {resp.status} at {url} | {text[:200]}")
                        self._rate_limit_until = time.time() + cooldown
                        raise Exception(f"Rate limit exceeded (429) - waiting {cooldown}s cooldown")
                    if resp.status != 200:
                        text = await resp.text()
                        logger.error(f"Dr Auris Throne API error: {resp.status} at {url} | {text[:200]}")
                        return None
                    try:
                        return await resp.json()
                    except Exception:
                        text = await resp.text()
                        logger.error(f"Dr Auris Throne API non-JSON response: {text[:200]}")
                        return None
            except aiohttp.ClientError as e:
                logger.error(f"Dr Auris Throne API request failed: {e}")
                return None

    async def _query_model(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Use the explicit DigitalOcean agent, else the canonical cloud fallback."""

        if self.provider_enabled:
            return await self._query_api(prompt)
        if not self.fallback_enabled:
            return None
        return await asyncio.to_thread(self._query_ollama_fallback, prompt)

    def _query_ollama_fallback(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Run an advisory-only Sero prompt through the shared Ollama adapter."""

        try:
            from aureon.inhouse_ai.llm_adapter import _llm_http_disabled
            from aureon.integrations.ollama import OllamaModelSwitchboard

            if _llm_http_disabled():
                return None
            if self._fallback_adapter is None:
                self._fallback_adapter, _selection = OllamaModelSwitchboard().compatible_adapter_for("fast")
            response = self._fallback_adapter.prompt(
                [{"role": "user", "content": prompt}],
                system=(
                    "You are Dr Auris, an advisory-only risk reviewer. Reply concisely. "
                    "For trade validation start with PROCEED, CAUTION, or ABORT, then a "
                    "confidence from 0 to 1 and one short evidence-based reason. Never "
                    "claim to execute a trade or bypass an Aureon gate."
                ),
                max_tokens=96,
                temperature=0.1,
            )
            if response.stop_reason == "error" or not str(response.text or "").strip():
                return None
            return {
                "choices": [{"message": {"content": str(response.text)}}],
                "model": str(response.model or ""),
                "route": "ollama_cloud_fallback",
            }
        except Exception as exc:
            logger.warning("Dr Auris Ollama fallback failed: %s", type(exc).__name__)
            return None

    async def _get_access_token(self, session: aiohttp.ClientSession) -> Optional[str]:
        """Issue access token via DigitalOcean Agents auth endpoint.
        
        ⚡ TOKEN CACHING: Reuses cached token for 5 minutes to reduce API calls.
        This is critical for avoiding rate limits!
        """
        # ⚡ CHECK CACHE FIRST - Don't request new token if we have a valid one!
        now = time.time()
        if self._cached_token and now < self._token_expiry:
            logger.debug(f"Using cached token (expires in {self._token_expiry - now:.0f}s)")
            return self._cached_token
        
        url = f"https://cloud.digitalocean.com/gen-ai/auth/agents/{self.agent_id}/token"
        api_keys = []
        if self.chatbot_id:
            api_keys.append(self.chatbot_id)
        if self.api_key and self.api_key != self.chatbot_id:
            api_keys.append(self.api_key)

        for key in api_keys:
            headers = {
                'Content-Type': 'application/json',
                'X-Api-Key': key
            }
            try:
                async with session.post(url, json={}, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        token = data.get('access_token')
                        if token:
                            # ⚡ CACHE THE TOKEN
                            self._cached_token = token
                            self._token_expiry = now + self._token_ttl
                            logger.info(f"New token acquired (cached for {self._token_ttl}s)")
                        return token
                    text = await resp.text()
                    logger.error(f"Token issuance failed: {resp.status} | {text[:200]}")
            except aiohttp.ClientError as e:
                logger.error(f"Token request failed: {e}")
                continue

        return None
    
    def _parse_trading_response(self, response: Optional[Dict[str, Any]]) -> Optional[SeroAdvice]:
        """
        Parse structured trading response from Dr Auris Throne.
        
        ⚡ HARMONIC HFT PARSER: Handles both compressed and verbose responses
        
        Expected formats:
        - Compressed: "PROCEED 0.85 profit locked"
        - Verbose: "RECOMMENDATION: PROCEED\nCONFIDENCE: 0.85\n..."
        
        Args:
            response: Raw API response dict
        
        Returns:
            Dr Auris Throne advice object or None if parsing failed
        """
        if not response:
            return None
        
        try:
            message = self._extract_message_from_response(response)
            if not message:
                return None
            
            message_upper = message.upper().strip()
            
            # ═══════════════════════════════════════════════════════════════
            # ⚡ FAST PARSE: Check for compressed HFT response first
            # Format: "PROCEED 0.85 reason" or "HOLD 0.6 wait for better"
            # ═══════════════════════════════════════════════════════════════
            recommendation = 'CAUTION'
            confidence = 0.5
            reasoning = message.strip()
            risk_flags = []
            
            # Fast check for PROCEED/CAUTION/ABORT/HOLD at start
            for action in ['PROCEED', 'CAUTION', 'ABORT', 'HOLD']:
                if message_upper.startswith(action):
                    recommendation = 'PROCEED' if action == 'PROCEED' else ('ABORT' if action == 'ABORT' else 'CAUTION')
                    
                    # Try to extract confidence number after action word
                    parts = message.split()
                    if len(parts) >= 2:
                        try:
                            # Second token might be confidence (0.0-1.0)
                            conf_str = parts[1].replace(',', '').replace('%', '')
                            conf_val = float(conf_str)
                            if 0 <= conf_val <= 1:
                                confidence = conf_val
                            elif 0 <= conf_val <= 100:
                                confidence = conf_val / 100
                            # Reasoning is everything after confidence
                            if len(parts) > 2:
                                reasoning = ' '.join(parts[2:])
                        except (ValueError, IndexError):
                            # Confidence not a number, reasoning starts at parts[1]
                            reasoning = ' '.join(parts[1:])
                    break
            
            # ═══════════════════════════════════════════════════════════════
            # FALLBACK: Parse verbose format (RECOMMENDATION: X, CONFIDENCE: Y)
            # ═══════════════════════════════════════════════════════════════
            if 'RECOMMENDATION:' in message_upper or 'CONFIDENCE:' in message_upper:
                lines = message.strip().split('\n')
                parsed = {}
                for line in lines:
                    if ':' in line:
                        key, value = line.split(':', 1)
                        parsed[key.strip().upper()] = value.strip()
                
                if 'RECOMMENDATION' in parsed:
                    rec = parsed['RECOMMENDATION'].upper()
                    if rec in ['PROCEED', 'CAUTION', 'ABORT']:
                        recommendation = rec
                
                if 'CONFIDENCE' in parsed:
                    try:
                        confidence = float(parsed['CONFIDENCE'])
                    except:
                        pass
                
                if 'REASONING' in parsed:
                    reasoning = parsed['REASONING']
                
                if 'RISK_FLAGS' in parsed:
                    risk_str = parsed['RISK_FLAGS']
                    if risk_str.lower() != 'none':
                        risk_flags = [f.strip() for f in risk_str.split(',')]
            
            return SeroAdvice(
                recommendation=recommendation,
                confidence=confidence,
                reasoning=reasoning[:200],  # Truncate for sanity
                risk_flags=risk_flags,
                timestamp=time.time()
            )
        
        except Exception as e:
            logger.error(f"Failed to parse Dr Auris Throne response: {e}")
            return None

    def _extract_message_from_response(self, response: Optional[Dict[str, Any]]) -> Optional[str]:
        """Extract assistant message from DO chat completion response."""
        if not response:
            return None
        # OpenAI-like format: { choices: [ { message: { content } } ] }
        choices = response.get('choices') if isinstance(response, dict) else None
        if isinstance(choices, list) and choices:
            choice = choices[0] or {}
            message = choice.get('message') or {}
            content = message.get('content')
            if content:
                return content
        # Fallbacks
        for key in ('message', 'response', 'content'):
            val = response.get(key) if isinstance(response, dict) else None
            if isinstance(val, str) and val.strip():
                return val
        return None


# Global singleton
_sero_client: Optional[SeroClient] = None

def get_sero_client() -> SeroClient:
    """Get or create global Dr Auris Throne client singleton."""
    global _sero_client
    if _sero_client is None:
        _sero_client = SeroClient()
    return _sero_client


# --- Testing / CLI ---
async def test_sero():
    """Test Dr Auris Throne Chatbot connectivity."""
    sero = get_sero_client()
    
    if not sero.enabled:
        print("❌ Dr Auris Throne Chatbot not configured")
        return
    
    print(f"✅ Dr Auris Throne Chatbot configured: {sero.agent_id[:8]}...")
    
    # Test trading decision query
    print("\n📊 Testing trading decision validation...")
    advice = await sero.ask_trading_decision(
        symbol="BTC/USD",
        side="BUY",
        context={
            'coherence': 0.85,
            'fusion_bias': 0.3,
            'threat_level': 0.1
        },
        queen_confidence=0.72
    )
    
    if advice:
        print(f"✅ Dr Auris Throne Advice:")
        print(f"   Recommendation: {advice.recommendation}")
        print(f"   Confidence: {advice.confidence:.2f}")
        print(f"   Reasoning: {advice.reasoning}")
        print(f"   Risk Flags: {advice.risk_flags}")
    else:
        print("❌ No advice received")
    
    # Test general intelligence query
    print("\n🧠 Testing market intelligence query...")
    intel = await sero.ask_market_intelligence(
        "What are key risk factors for crypto trading in current market conditions?"
    )
    
    if intel:
        print(f"✅ Intelligence: {intel[:200]}...")
    else:
        print("❌ No intelligence received")


if __name__ == '__main__':
    asyncio.run(test_sero())
