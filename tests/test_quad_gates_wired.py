"""The Seer and Lyra trade gates import from where they really live.

They used to import from ``aureon_quadrumvirate``, which was never committed,
so both gates silently fell back to "open". The gates can only veto a trade
(BLIND / SILENCE); with no vision or resonance yet they return True.
"""
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CALLERS = ["aureon/exchanges/capital_cfd_trader.py", "aureon/intelligence/trading_hive_mind.py"]


def test_gate_functions_exist_where_callers_import_them():
    from aureon.intelligence.aureon_seer_integration import seer_should_trade
    from aureon.trading.aureon_lyra_integration import lyra_should_trade
    assert callable(seer_should_trade) and callable(lyra_should_trade)


def test_callers_no_longer_use_the_missing_module():
    for rel in CALLERS:
        text = (REPO / rel).read_text(encoding="utf-8")
        assert "from aureon_quadrumvirate import" not in text, rel
        assert "from aureon.intelligence.aureon_seer_integration import seer_should_trade" in text, rel
        assert "from aureon.trading.aureon_lyra_integration import lyra_should_trade" in text, rel


def test_gates_only_veto_and_start_open(monkeypatch):
    import aureon.intelligence.aureon_seer_integration as si
    import aureon.trading.aureon_lyra_integration as li

    class Blank:
        latest_vision = None
        latest_resonance = None

    monkeypatch.setattr(si, "_get_seer", lambda: Blank())
    monkeypatch.setattr(li, "_get_lyra", lambda: Blank())
    assert si.seer_should_trade() is True
    assert li.lyra_should_trade() is True

    class Blind:
        class latest_vision:
            grade = "BLIND"

    class Silent:
        class latest_resonance:
            grade = "SILENCE"

    monkeypatch.setattr(si, "_get_seer", lambda: Blind())
    monkeypatch.setattr(li, "_get_lyra", lambda: Silent())
    assert si.seer_should_trade() is False
    assert li.lyra_should_trade() is False
