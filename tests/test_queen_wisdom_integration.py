"""Hermetic Queen/Wisdom collaborator contract for the Micro Profit Labyrinth."""

from __future__ import annotations

from dataclasses import asdict

from aureon.trading.micro_profit_labyrinth import MicroOpportunity, MicroProfitLabyrinth


class _QueenVoice:
    def speak_from_heart(self, moment: str) -> str:
        return f"queen:{moment}"

    def evaluate_trading_opportunity(self, _opportunity: dict) -> dict:
        return {"score": 0.9, "confidence": 0.95, "wisdom": "hold the evidence line"}


class _WisdomVoice:
    def analyze_trading_decision(self, _decision: dict) -> dict:
        return {"score": 0.85, "civilization": "Celtic", "pattern": "triad"}


def test_queen_wisdom_integration_contract_is_side_effect_free() -> None:
    """The Labyrinth accepts both voices without booting exchanges or background sync."""
    labyrinth = MicroProfitLabyrinth.__new__(MicroProfitLabyrinth)
    labyrinth.queen = _QueenVoice()
    labyrinth.wisdom_engine = _WisdomVoice()

    queen = labyrinth.queen.evaluate_trading_opportunity({"symbol": "BTC/ETH"})
    wisdom = labyrinth.wisdom_engine.analyze_trading_decision({"side": "HOLD"})

    assert labyrinth.queen.speak_from_heart("greeting") == "queen:greeting"
    assert queen == {
        "score": 0.9,
        "confidence": 0.95,
        "wisdom": "hold the evidence line",
    }
    assert wisdom == {"score": 0.85, "civilization": "Celtic", "pattern": "triad"}

    opportunity = MicroOpportunity(
        timestamp=1.0,
        from_asset="BTC",
        to_asset="ETH",
        from_amount=0.01,
        from_value_usd=400.0,
        v14_score=8.5,
        hub_score=0.85,
        commando_score=0.8,
        combined_score=0.82,
        expected_pnl_usd=0.05,
        expected_pnl_pct=0.01,
        queen_guidance_score=queen["score"],
        queen_wisdom=queen["wisdom"],
        queen_confidence=queen["confidence"],
        wisdom_engine_score=wisdom["score"],
        civilization_insight=wisdom["civilization"],
        wisdom_pattern=wisdom["pattern"],
    )
    payload = asdict(opportunity)
    assert payload["queen_guidance_score"] == 0.9
    assert payload["queen_confidence"] == 0.95
    assert payload["civilization_insight"] == "Celtic"
    assert payload["wisdom_pattern"] == "triad"
