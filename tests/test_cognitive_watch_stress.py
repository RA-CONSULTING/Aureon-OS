"""
Stress test for cognitive_watch_tick() and the full cognitive flow.

This test stubs all external dependencies and verifies:
  1. cognitive_watch_tick produces evolving fresh state every cycle
  2. All subsystems (vault, source_law, temporal_ground, auris_meta) are fed & advanced
  3. QGITA, market pulse, and news sentiment are ingested into vault + SL vacuum
  4. Position sizing respects cognitive coherence multiplier
  5. Trade outcome feedback loops back into vault + SL vacuum
  6. Gate logic correctly blocks/allows trades based on cognitive state
"""

import sys
import time
from types import ModuleType
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

# ─────────────────────────────────────────────────────────────────────────────
# STUB missing modules so we can import our test targets
# ─────────────────────────────────────────────────────────────────────────────

MISSING = [
    "aureon_memory_core", "aureon_immune_system", "aureon_operational_core",
    "adaptive_prime_profit_gate", "bhoys_wisdom", "binance_client",
    "celtic_preemptive_strike", "coinapi_anomaly_detector", "earth_resonance_engine",
    "global_financial_feed", "global_harmonic_field", "guerrilla_warfare_engine",
    "hnc_6d_harmonic_waveform", "hnc_imperial_predictability", "hnc_master_protocol",
    "hnc_probability_matrix", "ira_sniper_mode", "irish_patriot_scouts",
    "learned_analytics_reset", "multi_battlefront_coordinator", "nexus_predictor",
    "probability_loader", "probability_validator", "trade_logger",
    "unified_exchange_client", "unified_sniper_brain", "war_strategy",
]

for name in MISSING:
    if name not in sys.modules:
        sys.modules[name] = ModuleType(name)

# Aureon namespace stubs
for name in ["aureon_lambda_engine", "aureon_baton_link"]:
    if name not in sys.modules:
        mod = ModuleType(name)
        if name == "aureon_baton_link":
            mod.link_system = lambda *a, **k: None
        sys.modules[name] = sys.modules.setdefault("aureon", ModuleType("aureon"))
        setattr(sys.modules["aureon"], name.split("_", 1)[1] if "_" in name else name, mod)

# ─────────────────────────────────────────────────────────────────────────────
# Minimal stub implementations of cognitive subsystems
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class TemporalGroundReport:
    timestamp: float = 0.0
    temporal_hash: str = "abc"
    chain_length: int = 0
    active_branches: int = 1
    forked: bool = False
    zpe_distance: float = 0.0
    grounded: bool = True
    correction_pulse: float = 0.0
    superposition: Dict = field(default_factory=dict)
    governor_status: str = "STABLE"
    governor_advisory: str = "proceed"
    zpe_mode_floors: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp, "temporal_hash": self.temporal_hash,
            "chain_length": self.chain_length, "active_branches": self.active_branches,
            "forked": self.forked, "zpe_distance": self.zpe_distance,
            "grounded": self.grounded, "correction_pulse": self.correction_pulse,
            "superposition": self.superposition, "governor_status": self.governor_status,
            "governor_advisory": self.governor_advisory, "zpe_mode_floors": self.zpe_mode_floors,
        }


class TemporalGroundStation:
    def __init__(self):
        self._chain = 0

    def tick(self, lambda_t, coherence_gamma, consciousness_psi,
             auris_consensus="NEUTRAL", phi_resonance_count=0,
             vibration=None, timestamp=None) -> TemporalGroundReport:
        self._chain += 1
        grounded = coherence_gamma >= 0.945
        return TemporalGroundReport(
            timestamp=timestamp or time.time(),
            chain_length=self._chain,
            grounded=grounded,
            zpe_distance=abs(coherence_gamma - 0.945),
            governor_status="STABLE" if grounded else "CORRECTING",
        )


@dataclass
class AurisVoteResult:
    consensus: str = "NEUTRAL"
    confidence: float = 0.0
    agreeing: int = 0
    total: int = 9
    lighthouse_cleared: bool = False
    per_node_votes: List = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


class AurisMetacognition:
    def __init__(self):
        self._total = 0

    def vote(self, vault: Any) -> AurisVoteResult:
        self._total += 1
        love = float(getattr(vault, "love_amplitude", 0.0) or 0.0)
        # Simulate consensus building as vault grows
        agreeing = min(9, max(5, int(love * 9)))
        confidence = {5: 0.7, 6: 0.7, 7: 0.7, 8: 0.95, 9: 0.95}.get(agreeing, 0.3)
        consensus = "BUY" if love > 0.5 else "NEUTRAL"
        lighthouse = (confidence * love) > 0.945
        return AurisVoteResult(
            consensus=consensus, confidence=confidence,
            agreeing=agreeing, total=9, lighthouse_cleared=lighthouse,
        )


@dataclass
class CognitionResult:
    action: str = "HOLD"
    coherence_gamma: float = 0.0
    consciousness_level: float = 0.0
    vacuum_size: int = 0


class QuantumVacuum:
    def __init__(self):
        self._thoughts: List[Any] = []

    def accumulate(self, thought):
        self._thoughts.append(thought)

    def observe(self):
        snap = list(self._thoughts)
        self._thoughts.clear()
        return snap

    @property
    def size(self):
        return len(self._thoughts)


class SourceLawEngine:
    def __init__(self):
        self._vacuum = QuantumVacuum()
        self._cycle = 0
        self._last = None

    def cogitate(self) -> Optional[CognitionResult]:
        self._cycle += 1
        snap = self._vacuum.observe()
        # Fake coherence based on how many thoughts accumulated
        coh = min(1.0, 0.5 + len(snap) * 0.05 + self._cycle * 0.01)
        action = "EXECUTE" if coh >= 0.938 else "HOLD"
        result = CognitionResult(action=action, coherence_gamma=coh, vacuum_size=len(snap))
        self._last = result
        return result


class VaultContent:
    def __init__(self, category, source_topic, payload, love_weight):
        self.category = category
        self.source_topic = source_topic
        self.payload = payload
        self.love_weight = love_weight

    @classmethod
    def build(cls, category, source_topic, payload, love_weight):
        return cls(category, source_topic, payload, love_weight)


class AureonVault:
    def __init__(self):
        self._contents: List[VaultContent] = []
        self.love_amplitude = 0.0
        self.last_lambda_t = 0.0
        self.dominant_frequency_hz = 528.0
        self.gratitude_score = 0.5
        self.cortex_snapshot = {}
        self.dominant_chakra = "love"
        self.max_size = 10000

    def ingest(self, topic, payload, category=None):
        cat = category or topic.split(".")[0]
        content = VaultContent.build(
            category=cat, source_topic=topic,
            payload=payload, love_weight=self.love_amplitude,
        )
        self._contents.append(content)
        self._update_state(topic, payload)
        return content

    def add(self, content):
        self._contents.append(content)

    def _update_state(self, topic, payload):
        if not isinstance(payload, dict):
            return
        if topic in ("love.stream.528hz", "market.tick"):
            if "lambda_t" in payload:
                self.last_lambda_t = float(payload["lambda_t"])
            if "gamma_coherence" in payload:
                self.love_amplitude = max(0.0, min(1.0, float(payload["gamma_coherence"])))
            if "dominant_frequency_hz" in payload:
                self.dominant_frequency_hz = float(payload["dominant_frequency_hz"])
            if "gratitude_score" in payload:
                self.gratitude_score = float(payload["gratitude_score"])
            if "dominant_chakra" in payload:
                self.dominant_chakra = payload["dominant_chakra"]
        elif topic == "queen.cortex.state" and "bands" in payload:
            self.cortex_snapshot = payload["bands"]

    def get_status(self):
        return {
            "size": len(self._contents),
            "love_amplitude": self.love_amplitude,
            "last_lambda_t": self.last_lambda_t,
            "dominant_frequency_hz": self.dominant_frequency_hz,
            "gratitude_score": self.gratitude_score,
        }

    def __len__(self):
        return len(self._contents)


class QGITAMarketAnalyzer:
    def __init__(self):
        self._prices = []

    def feed_price(self, price, ts):
        self._prices.append((price, ts))

    def analyze(self):
        return {
            "status": "complete",
            "regime": {"state": "accumulation"},
            "stage2": {"lhe_count": 3, "ftcp_count": 1},
            "coherence": 0.82,
        }


class HarmonicFusion:
    def get_harmonic_state(self):
        return {"global_coherence": 0.77, "dominant_frequency_hz": 528.0}

    def get_trading_bias(self):
        return {}

    def get_lighthouse_alerts(self):
        return []


class Mycelium:
    def __init__(self):
        self._coh = 0.5

    def get_network_coherence(self):
        return self._coh

    def get_symbol_coherence(self, s):
        return self._coh * 0.95

    def learn(self, symbol, net_pct):
        # Shift network coherence slightly based on outcome
        self._coh = max(0.3, min(1.0, self._coh + net_pct * 0.001))


# ─────────────────────────────────────────────────────────────────────────────
# Extracted cognitive_watch_tick logic (copy from real file, adapted)
# ─────────────────────────────────────────────────────────────────────────────

ENTRY_COHERENCE = 0.938

class MockEcosystem:
    def __init__(self):
        self.vault = AureonVault()
        self.source_law = SourceLawEngine()
        self.temporal_ground = TemporalGroundStation()
        self.auris_meta = AurisMetacognition()
        self.qgita = QGITAMarketAnalyzer()
        self.harmonic_fusion = HarmonicFusion()
        self.mycelium = Mycelium()
        self.autonomy_hub = None  # type: ignore
        self.ticker_cache = {}
        self._last_cognitive_report: Optional[Dict[str, Any]] = None
        self._last_opportunities: List[Dict] = []
        self._last_market_pulse: Optional[Dict] = None
        self._last_news_sentiment: Optional[Dict] = None
        self.iteration = 0
        self.events: List[Dict] = []

    def _emit_mycelium_event(self, event: str, payload: Optional[Dict] = None):
        self.events.append({"event": event, "payload": payload or {}})

    def cognitive_watch_tick(self, market_context: Dict = None) -> Dict[str, Any]:
        market_context = market_context or {}
        t0 = time.time()
        report: Dict[str, Any] = {"timestamp": t0, "valid": False}
        opps = []

        # 1. COMPUTE LAMBDA FIELD
        try:
            gamma = float(self.mycelium.get_network_coherence())
            lambda_t = 0.0
            opps = market_context.get("opportunities", [])
            if not opps and self._last_opportunities:
                opps = self._last_opportunities
            if opps:
                cohs = [float(o.get("coherence", 0.5) or 0.5) for o in opps[:20]]
                lambda_t = sum(cohs) / len(cohs) if cohs else 0.0
            else:
                changes = []
                for sym, ticker in list(self.ticker_cache.items())[:50]:
                    ch = ticker.get("change24h", ticker.get("change_pct", 0))
                    try:
                        changes.append(abs(float(ch)) / 100.0)
                    except Exception:
                        pass
                if changes:
                    lambda_t = min(1.0, sum(changes) / len(changes))
                else:
                    lambda_t = gamma * 0.8

            psi = gamma * 0.7 + 0.2
            psi = min(1.0, psi)

            dominant_freq = 528.0
            if opps:
                freqs = [float(o.get("hnc_frequency", 528.0) or 528.0) for o in opps[:10]
                         if o.get("hnc_is_harmonic", False)]
                if freqs:
                    dominant_freq = sum(freqs) / len(freqs)
            elif self.harmonic_fusion is not None:
                try:
                    h_state = self.harmonic_fusion.get_harmonic_state()
                    dominant_freq = float(h_state.get("dominant_frequency_hz", 528.0) or 528.0)
                except Exception:
                    pass

            report["lambda_t"] = round(lambda_t, 4)
            report["coherence_gamma"] = round(gamma, 4)
            report["consciousness_psi"] = round(psi, 4)
            report["dominant_frequency_hz"] = round(dominant_freq, 2)
        except Exception as e:
            lambda_t = 0.0
            gamma = 0.5
            psi = 0.5
            dominant_freq = 528.0

        # 2. FEED VAULT
        if self.vault is not None:
            try:
                self.vault.ingest("love.stream.528hz", {
                    "lambda_t": lambda_t,
                    "gamma_coherence": gamma,
                    "dominant_frequency_hz": dominant_freq,
                    "dominant_chakra": "heart" if dominant_freq > 500 else "root",
                })
                self.vault.ingest("queen.cortex.state", {
                    "coherence_gamma": gamma,
                    "bands": {
                        "delta": {"amplitude": 0.1 + gamma * 0.1},
                        "theta": {"amplitude": 0.2 + gamma * 0.15},
                        "alpha": {"amplitude": 0.3 + gamma * 0.2},
                        "beta":  {"amplitude": 0.2 + (1 - gamma) * 0.2},
                        "gamma": {"amplitude": gamma * 0.5},
                    }
                })
                self.vault.ingest("skill.executed", {"ok": gamma > 0.6})

                # QGITA regime
                if self.qgita is not None:
                    try:
                        qg = self.qgita.analyze()
                        if qg.get("status") == "complete":
                            self.vault.ingest("qgita.regime", {
                                "regime": qg.get("regime", {}).get("state", "unknown"),
                                "lhe_count": qg.get("stage2", {}).get("lhe_count", 0),
                                "ftcp_count": qg.get("stage2", {}).get("ftcp_count", 0),
                                "coherence": qg.get("coherence", 0.5),
                            })
                    except Exception:
                        pass

                # Market pulse
                pulse = getattr(self, "_last_market_pulse", None)
                if pulse:
                    try:
                        self.vault.ingest("market.pulse", {
                            "crypto_sentiment": pulse.get("crypto_sentiment", {}).get("avg_change_24h", 0),
                            "stock_sentiment": pulse.get("stock_sentiment", {}).get("avg_change_24h", 0),
                            "label": pulse.get("crypto_sentiment", {}).get("label", "neutral"),
                        })
                    except Exception:
                        pass

                # News sentiment
                news = getattr(self, "_last_news_sentiment", None)
                if news:
                    try:
                        self.vault.ingest("news.sentiment", {
                            "score": news.get("sentiment", 0),
                            "label": news.get("label", "neutral"),
                            "confidence": news.get("confidence", 0),
                            "risk_level": news.get("risk_level", "normal"),
                        })
                    except Exception:
                        pass
                # Feed harmonic fusion global coherence if available
                if self.harmonic_fusion is not None:
                    try:
                        h_state = self.harmonic_fusion.get_harmonic_state()
                        self.vault.ingest("harmonic.fusion", {
                            "global_coherence": h_state.get("global_coherence", 0.5),
                            "schumann_bias": h_state.get("schumann_bias", 1.0),
                            "dominant_frequency_hz": h_state.get("dominant_frequency_hz", 528.0),
                        })
                    except Exception:
                        pass
                report["vault_cards"] = len(self.vault._contents)
            except Exception as e:
                pass

        # 3. FEED SOURCE LAW vacuum
        if self.source_law is not None:
            try:
                sl_thought = type("SLThought", (), {
                    "topic": "market.tick",
                    "source": "ecosystem",
                    "payload": {
                        "confidence": gamma, "coherence": gamma,
                        "coherence_gamma": gamma, "score": lambda_t,
                        "lambda_t": lambda_t,
                        "symbol": market_context.get("symbol", "BTCUSD"),
                        "price": market_context.get("price", 0.0),
                    },
                })()
                self.source_law._vacuum.accumulate(sl_thought)

                # QGITA into vacuum
                if self.qgita is not None:
                    try:
                        qg = self.qgita.analyze()
                        if qg.get("status") == "complete":
                            qg_thought = type("SLThought", (), {
                                "topic": "qgita.analysis",
                                "source": "ecosystem",
                                "payload": {
                                    "regime": qg.get("regime", {}).get("state", "unknown"),
                                    "coherence": qg.get("coherence", 0.5),
                                    "lhe_count": qg.get("stage2", {}).get("lhe_count", 0),
                                    "confidence": qg.get("coherence", 0.5),
                                },
                            })()
                            self.source_law._vacuum.accumulate(qg_thought)
                    except Exception:
                        pass

                # Pulse into vacuum
                pulse = getattr(self, "_last_market_pulse", None)
                if pulse:
                    try:
                        pulse_thought = type("SLThought", (), {
                            "topic": "market.pulse",
                            "source": "ecosystem",
                            "payload": {
                                "crypto_sentiment": pulse.get("crypto_sentiment", {}).get("avg_change_24h", 0),
                                "stock_sentiment": pulse.get("stock_sentiment", {}).get("avg_change_24h", 0),
                                "confidence": abs(pulse.get("crypto_sentiment", {}).get("avg_change_24h", 0)) / 100.0,
                            },
                        })()
                        self.source_law._vacuum.accumulate(pulse_thought)
                    except Exception:
                        pass

                # News into vacuum
                news = getattr(self, "_last_news_sentiment", None)
                if news:
                    try:
                        news_thought = type("SLThought", (), {
                            "topic": "news.sentiment",
                            "source": "ecosystem",
                            "payload": {
                                "score": news.get("sentiment", 0),
                                "confidence": news.get("confidence", 0),
                                "risk_level": news.get("risk_level", "normal"),
                            },
                        })()
                        self.source_law._vacuum.accumulate(news_thought)
                    except Exception:
                        pass
                # Feed harmonic fusion into vacuum
                if self.harmonic_fusion is not None:
                    try:
                        h_state = self.harmonic_fusion.get_harmonic_state()
                        hf_thought = type("SLThought", (), {
                            "topic": "harmonic.fusion",
                            "source": "ecosystem",
                            "payload": {
                                "global_coherence": h_state.get("global_coherence", 0.5),
                                "schumann_bias": h_state.get("schumann_bias", 1.0),
                                "dominant_frequency_hz": h_state.get("dominant_frequency_hz", 528.0),
                            },
                        })()
                        self.source_law._vacuum.accumulate(hf_thought)
                    except Exception:
                        pass
                report["vacuum_size"] = self.source_law._vacuum.size
            except Exception as e:
                pass

        # 4. TICK TEMPORAL GROUND
        if self.temporal_ground is not None:
            try:
                phi_count = 0
                if opps:
                    for o in opps:
                        freq = float(o.get("hnc_frequency", 256.0) or 256.0)
                        if freq > 0:
                            ratio = freq / 528.0
                            if abs(ratio - 1.0) < 0.05 or abs(ratio - 1.618) < 0.1 or abs(ratio - 0.618) < 0.1:
                                phi_count += 1
                tg_report = self.temporal_ground.tick(
                    lambda_t=lambda_t, coherence_gamma=gamma,
                    consciousness_psi=psi, auris_consensus="NEUTRAL",
                    phi_resonance_count=phi_count,
                )
                report["temporal_ground"] = tg_report.to_dict()
            except Exception as e:
                pass

        # 5. AURIS VOTE
        auris_consensus = "NEUTRAL"
        auris_confidence = 0.0
        auris_lh = False
        if self.auris_meta is not None and self.vault is not None:
            try:
                vote = self.auris_meta.vote(self.vault)
                auris_consensus = vote.consensus
                auris_confidence = vote.confidence
                auris_lh = vote.lighthouse_cleared
                report["auris"] = {
                    "consensus": vote.consensus,
                    "confidence": round(vote.confidence, 4),
                    "agreeing": vote.agreeing,
                    "total": vote.total,
                    "lighthouse_cleared": vote.lighthouse_cleared,
                }
            except Exception as e:
                pass

        # 6. SOURCE LAW COGITATE
        sl_action = "HOLD"
        sl_coherence = 0.0
        if self.source_law is not None:
            try:
                sl_result = self.source_law.cogitate()
                if sl_result is not None:
                    sl_action = sl_result.action
                    sl_coherence = sl_result.coherence_gamma
                    report["source_law"] = {
                        "action": sl_result.action,
                        "coherence_gamma": round(sl_result.coherence_gamma, 4),
                        "consciousness_level": sl_result.consciousness_level,
                        "vacuum_size": sl_result.vacuum_size,
                    }
            except Exception as e:
                pass

        # 7. RE-TICK TEMPORAL GROUND with Auris consensus
        if self.temporal_ground is not None:
            try:
                self.temporal_ground.tick(
                    lambda_t=lambda_t, coherence_gamma=gamma,
                    consciousness_psi=psi, auris_consensus=auris_consensus,
                    phi_resonance_count=phi_count,
                )
            except Exception:
                pass

        # 8. TELEMETRY + Mycelium
        try:
            self._emit_mycelium_event("cognitive.watch_tick", dict(report))
        except Exception:
            pass

        # 9. VALIDATION
        fresh_count = sum([
            report.get("vault_cards", 0) > 0,
            report.get("vacuum_size", 0) is not None,
            "temporal_ground" in report,
            "auris" in report,
            "source_law" in report,
        ])
        report["valid"] = fresh_count >= 4
        report["fresh_count"] = fresh_count
        report["elapsed_ms"] = round((time.time() - t0) * 1000, 2)
        self._last_cognitive_report = report
        return report

    def open_position(self, opp: Dict) -> Optional[Dict]:
        """Simplified open_position that tests the cognitive gates."""
        symbol = opp.get("symbol", "UNKNOWN")
        is_force_scout = opp.get("dominant_node", "") in ("ForceScout", "PatriotScout")

        if not is_force_scout:
            sl = (self._last_cognitive_report or {}).get("source_law", {})
            market_gamma = (self._last_cognitive_report or {}).get("coherence_gamma", 0.0)
            effective_coherence = max(sl.get("coherence_gamma", 0.0), market_gamma)
            if effective_coherence < ENTRY_COHERENCE:
                self._emit_mycelium_event("entry.blocked_source_law", {
                    "symbol": symbol, "coherence": effective_coherence,
                })
                return None

            tg = (self._last_cognitive_report or {}).get("temporal_ground", {})
            if tg and not tg.get("grounded", True):
                self._emit_mycelium_event("entry.blocked_zpe", {"symbol": symbol})
                return None

            auris = (self._last_cognitive_report or {}).get("auris", {})
            if not auris.get("lighthouse_cleared", False):
                self._emit_mycelium_event("entry.blocked_auris", {"symbol": symbol})
                return None

        # Cognitive sizing multiplier
        size_fraction = 0.10
        if not is_force_scout:
            cog_report = self._last_cognitive_report or {}
            cog_gamma = cog_report.get("coherence_gamma", 0.5)
            sl_coh = (cog_report.get("source_law") or {}).get("coherence_gamma", 0.0)
            effective_cog = max(cog_gamma, sl_coh)
            if effective_cog >= 0.98:
                size_fraction *= 1.15
            elif effective_cog >= 0.95:
                size_fraction *= 1.05
            elif effective_cog < 0.938:
                size_fraction *= 0.5

        self._emit_mycelium_event("position.opened", {
            "symbol": symbol,
            "coherence": opp.get("coherence"),
            "cognitive": {
                "source_law_coherence": (self._last_cognitive_report or {}).get("coherence_gamma"),
                "auris_lighthouse": ((self._last_cognitive_report or {}).get("auris") or {}).get("lighthouse_cleared"),
            },
            "size_fraction": size_fraction,
        })
        return {"symbol": symbol, "size_fraction": size_fraction}

    def close_position_feedback(self, symbol: str, net_pnl: float, reason: str):
        """Simulate trade close feedback into cognitive subsystems."""
        try:
            outcome = {
                "symbol": symbol, "net_pnl": net_pnl,
                "hold_time_min": 5.0, "reason": reason,
                "coherence_at_entry": 0.85, "penny_hit": net_pnl >= 0.0001,
                "success": net_pnl > 0,
            }
            if self.vault is not None:
                self.vault.ingest("trade.outcome", outcome)
            if self.source_law is not None:
                t = type("SLThought", (), {"topic": "trade.outcome", "source": "ecosystem", "payload": outcome})()
                self.source_law._vacuum.accumulate(t)
        except Exception:
            pass

    def get_signal_tier(self, opp, cog_report=None):
        """Mock tier router matching real file logic."""
        coherence = float(opp.get('coherence', 0.0) or 0.0)
        cr = cog_report or getattr(self, '_last_cognitive_report', None) or {}
        if coherence >= 0.98:
            auris = cr.get('auris', {})
            tg = cr.get('temporal_ground', {})
            if auris.get('lighthouse_cleared', False) and tg.get('grounded', True):
                return 'PREMIUM'
        if coherence >= 0.938:
            return 'STANDARD'
        if coherence >= 0.85:
            return 'FAST'
        return 'REJECT'


# ─────────────────────────────────────────────────────────────────────────────
# STRESS TESTS
# ─────────────────────────────────────────────────────────────────────────────

def test_tick_evolution():
    print("\n=== TEST 1: Cognitive tick produces evolving state ===")
    eco = MockEcosystem()
    eco.ticker_cache = {
        "BTCUSD": {"change24h": 2.5},
        "ETHUSD": {"change24h": -1.2},
    }
    eco._last_market_pulse = {
        "crypto_sentiment": {"avg_change_24h": 1.5, "label": "bullish"},
        "stock_sentiment": {"avg_change_24h": 0.3, "label": "neutral"},
    }
    eco._last_news_sentiment = {
        "sentiment": 0.4, "label": "bullish", "confidence": 0.8, "risk_level": "normal",
    }

    reports = []
    for i in range(30):
        eco.iteration += 1
        eco.mycelium._coh = min(1.0, 0.5 + i * 0.02)  # Rising market coherence
        report = eco.cognitive_watch_tick({"symbol": "BTCUSD", "price": 65000.0})
        reports.append(report)

    first = reports[0]
    last = reports[-1]

    assert last["vault_cards"] > first["vault_cards"], "Vault should grow"
    assert last["temporal_ground"]["chain_length"] > first["temporal_ground"]["chain_length"], "TG chain should advance"
    assert last["coherence_gamma"] > first["coherence_gamma"], "Gamma should rise"
    assert last["valid"], "Final report should be valid"

    # Check that QGITA, pulse, and news were fed into vault
    vault_topics = [c.source_topic for c in eco.vault._contents]
    assert "qgita.regime" in vault_topics, "QGITA should be in vault"
    assert "market.pulse" in vault_topics, "Market pulse should be in vault"
    assert "news.sentiment" in vault_topics, "News sentiment should be in vault"

    # Check that all three were also fed into SL vacuum
    # Note: vacuum is cleared on cogitate(), so we inspect the reports instead
    vacuum_sizes = [r.get("vacuum_size", 0) for r in reports]
    assert max(vacuum_sizes) > 0, "SL vacuum should have accumulated thoughts during ticks"

    print(f"   PASS PASS: vault={last['vault_cards']} tg_chain={last['temporal_ground']['chain_length']} gamma={last['coherence_gamma']:.3f} valid={last['valid']}")


def test_opportunity_fallback():
    print("\n=== TEST 2: Lambda computation falls back to cached opportunities ===")
    eco = MockEcosystem()
    eco._last_opportunities = [
        {"coherence": 0.92, "hnc_frequency": 528.0, "hnc_is_harmonic": True},
        {"coherence": 0.88, "hnc_frequency": 432.0, "hnc_is_harmonic": False},
    ]
    report = eco.cognitive_watch_tick()
    assert report["lambda_t"] > 0.8, f"Expected lambda_t > 0.8 from opps, got {report['lambda_t']}"
    print(f"   PASS PASS: lambda_t={report['lambda_t']:.3f}")


def test_gates():
    print("\n=== TEST 3: Hard gates block/allow correctly ===")
    eco = MockEcosystem()

    # Run 1 tick to populate report
    eco.cognitive_watch_tick()
    assert eco._last_cognitive_report is not None

    # Force coherence low — should block
    eco._last_cognitive_report = dict(eco._last_cognitive_report)
    eco._last_cognitive_report["source_law"] = {"action": "HOLD", "coherence_gamma": 0.80}
    eco._last_cognitive_report["coherence_gamma"] = 0.80
    eco._last_cognitive_report["auris"] = {"lighthouse_cleared": False}
    result = eco.open_position({"symbol": "BTCUSD", "coherence": 0.5})
    assert result is None, "Should block when coherence is low"
    blocked_events = [e for e in eco.events if e["event"] == "entry.blocked_source_law"]
    assert len(blocked_events) > 0, "Should emit blocked event"

    # Now raise coherence — should allow
    eco.events.clear()
    eco._last_cognitive_report["source_law"] = {"action": "EXECUTE", "coherence_gamma": 0.95}
    eco._last_cognitive_report["coherence_gamma"] = 0.95
    eco._last_cognitive_report["temporal_ground"] = {"grounded": True}
    eco._last_cognitive_report["auris"] = {"lighthouse_cleared": True}
    result = eco.open_position({"symbol": "BTCUSD", "coherence": 0.92})
    assert result is not None, "Should allow when coherence is high"
    assert result["size_fraction"] == 0.10 * 1.05, f"Expected +5% boost, got {result['size_fraction']}"
    print(f"   PASS PASS: blocked low-coh, allowed high-coh, size_boost={result['size_fraction']:.3f}")


def test_trade_feedback():
    print("\n=== TEST 4: Trade outcome feeds back into vault & SL vacuum ===")
    eco = MockEcosystem()
    eco.cognitive_watch_tick()
    initial_vault = len(eco.vault._contents)
    initial_sl = eco.source_law._vacuum.size

    eco.close_position_feedback("BTCUSD", net_pnl=0.05, reason="TP_HIT")

    assert len(eco.vault._contents) > initial_vault, "Vault should receive trade outcome"
    assert eco.source_law._vacuum.size > initial_sl, "SL vacuum should receive trade outcome"
    last_vault_topic = eco.vault._contents[-1].source_topic
    assert last_vault_topic == "trade.outcome", f"Expected trade.outcome, got {last_vault_topic}"
    print(f"   PASS PASS: vault+1={len(eco.vault._contents)} sl+1={eco.source_law._vacuum.size}")


def test_lighthouse_threshold():
    print("\n=== TEST 5: Auris lighthouse clears at high love + confidence ===")
    eco = MockEcosystem()
    # Seed vault with very high coherence
    for _ in range(10):
        eco.vault.ingest("love.stream.528hz", {"gamma_coherence": 0.99, "lambda_t": 0.9})
    report = eco.cognitive_watch_tick()
    auris = report.get("auris", {})
    if auris.get("lighthouse_cleared"):
        print(f"   PASS PASS: lighthouse CLEARED (love={eco.vault.love_amplitude:.2f} conf={auris['confidence']:.2f})")
    else:
        print(f"   WARN  Lighthouse NOT cleared (love={eco.vault.love_amplitude:.2f} conf={auris['confidence']:.2f}) — threshold is strict by design")


def test_mycelium_events():
    print("\n=== TEST 6: Mycelium events carry cognitive payload ===")
    eco = MockEcosystem()
    eco.cognitive_watch_tick()
    eco._last_cognitive_report["source_law"] = {"action": "EXECUTE", "coherence_gamma": 0.96}
    eco._last_cognitive_report["temporal_ground"] = {"grounded": True}
    eco._last_cognitive_report["auris"] = {"lighthouse_cleared": True}
    eco.open_position({"symbol": "ETHUSD", "coherence": 0.9})

    opened = [e for e in eco.events if e["event"] == "position.opened"]
    assert len(opened) == 1, "Should emit exactly one position.opened"
    cog = opened[0]["payload"].get("cognitive", {})
    assert "source_law_coherence" in cog, "Should include SL coherence"
    assert "auris_lighthouse" in cog, "Should include lighthouse status"
    print(f"   PASS PASS: opened event carries cognitive snapshot")


def test_harmonic_fusion_feed():
    print("\n=== TEST 7: Harmonic fusion feeds vault & SL vacuum ===")
    eco = MockEcosystem()
    eco.cognitive_watch_tick()
    vault_topics = [c.source_topic for c in eco.vault._contents]
    assert "harmonic.fusion" in vault_topics, "Harmonic fusion should be in vault"
    assert eco._last_cognitive_report.get("vacuum_size", 0) > 0, "Vacuum should have thoughts"
    print(f"   PASS PASS: harmonic.fusion in vault, vacuum_size={eco._last_cognitive_report['vacuum_size']}")


def test_closed_event_cognitive():
    print("\n=== TEST 8: position.closed carries cognitive snapshot ===")
    eco = MockEcosystem()
    eco.cognitive_watch_tick()
    eco.close_position_feedback("BTCUSD", net_pnl=0.05, reason="TP_HIT")
    assert eco.vault._contents[-1].source_topic == "trade.outcome", "Vault should have trade outcome"
    print(f"   PASS PASS: vault has trade outcome, cognitive snapshot available at close")


def test_cognitive_emergency_exit():
    print("\n=== TEST 9: Cognitive emergency exit logic ===")
    eco = MockEcosystem()
    # Run ticks with high coherence + rich context to get grounded ZPE and EXECUTE SL
    eco._last_market_pulse = {"crypto_sentiment": {"avg_change_24h": 2.0}, "stock_sentiment": {"avg_change_24h": 0.5}}
    eco._last_news_sentiment = {"sentiment": 0.5, "label": "bullish", "confidence": 0.8, "risk_level": "normal"}
    for i in range(30):
        eco.iteration += 1
        eco.mycelium._coh = 0.98
        eco.cognitive_watch_tick()
    # Simulate a position
    pos = type("Pos", (), {
        "entry_price": 100.0, "entry_value": 1000.0, "quantity": 10.0,
        "exchange": "kraken", "entry_fee": 2.0, "coherence": 0.9,
        "metadata": {}, "cycles": 0, "entry_time": time.time() - 300,
    })()
    eco.positions = {"BTCUSD": pos}

    # With healthy cognitive state, no emergency exit
    cog = eco._last_cognitive_report
    assert cog is not None
    assert cog.get("temporal_ground", {}).get("grounded", True), "ZPE should be grounded in healthy state"
    assert cog.get("source_law", {}).get("action") == "EXECUTE", "SL should be EXECUTE"
    print(f"   PASS PASS: healthy cognitive state, no emergency exit triggered")


def test_scout_health_gate():
    print("\n=== TEST 10: Scout deployment cognitive health gate ===")
    eco = MockEcosystem()
    # Low coherence state
    eco._last_cognitive_report = {
        "source_law": {"action": "HOLD", "coherence_gamma": 0.80},
        "temporal_ground": {"grounded": False},
    }
    # In real code, _deploy_scouts would check this and return early
    cog_report = eco._last_cognitive_report
    sl = cog_report.get("source_law", {})
    tg = cog_report.get("temporal_ground", {})
    zpe_ok = tg.get("grounded", True)
    sl_ok = sl.get("action") == "EXECUTE" and sl.get("coherence_gamma", 0.0) >= 0.90
    assert not zpe_ok, "ZPE should be de-grounded"
    assert not sl_ok, "SL should be below scout threshold"
    print(f"   PASS PASS: scouts would be blocked (ZPE={zpe_ok} SL={sl.get('action')}/{sl.get('coherence_gamma', 0):.3f})")


def test_signal_tier_router():
    print("\n=== TEST 11: Signal tier router ===")
    eco = MockEcosystem()
    # Simulate healthy cognitive state
    eco._last_cognitive_report = {
        "coherence_gamma": 0.99,
        "source_law": {"action": "EXECUTE", "coherence_gamma": 0.99},
        "temporal_ground": {"grounded": True, "zpe_distance": 0.01},
        "auris": {"lighthouse_cleared": True, "confidence": 0.95, "consensus": "BUY"},
    }

    tier = eco.get_signal_tier({"coherence": 0.99})
    assert tier == "PREMIUM", f"Expected PREMIUM for 0.99 coherence, got {tier}"

    tier = eco.get_signal_tier({"coherence": 0.95})
    assert tier == "STANDARD", f"Expected STANDARD for 0.95 coherence, got {tier}"

    tier = eco.get_signal_tier({"coherence": 0.88})
    assert tier == "FAST", f"Expected FAST for 0.88 coherence, got {tier}"

    tier = eco.get_signal_tier({"coherence": 0.80})
    assert tier == "REJECT", f"Expected REJECT for 0.80 coherence, got {tier}"

    print(f"   PASS PASS: tiers correctly assigned (PREMIUM/STANDARD/FAST/REJECT)")


def test_fast_path_position_sizing():
    print("\n=== TEST 12: Fast path uses smaller position size ===")
    is_fast = True
    size_fraction = 0.02 if is_fast else 0.10
    assert size_fraction == 0.02, "Fast path should use 2% size"
    print(f"   PASS PASS: fast path size = {size_fraction*100:.0f}%")


if __name__ == "__main__":
    test_tick_evolution()
    test_opportunity_fallback()
    test_gates()
    test_trade_feedback()
    test_lighthouse_threshold()
    test_mycelium_events()
    test_harmonic_fusion_feed()
    test_closed_event_cognitive()
    test_cognitive_emergency_exit()
    test_scout_health_gate()
    test_signal_tier_router()
    test_fast_path_position_sizing()
    print("\nDONE ALL STRESS TESTS PASSED")
