"""The held-back imports now point at modules that really exist."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_get_dust_converter_is_a_shared_instance():
    from aureon.conversion.dust_converter import DustConverter, get_dust_converter

    first = get_dust_converter()
    assert isinstance(first, DustConverter)
    assert get_dust_converter() is first


def test_import_lines_point_at_real_modules():
    from aureon.harmonic.earth_resonance_engine import EarthResonanceEngine, get_earth_engine  # noqa: F401

    expect = {
        "aureon/exchanges/kraken_margin_penny_trader.py": "from aureon.harmonic.earth_resonance_engine import EarthResonanceEngine, get_earth_engine",
        "unified_margin_trader/kraken_margin_penny_trader.py": "from aureon.harmonic.earth_resonance_engine import EarthResonanceEngine, get_earth_engine",
        "aureon/utils/aureon_miner.py": "from aureon.harmonic.earth_resonance_engine import EarthResonanceEngine",
        "aureon/utils/aureon_queen_hive_mind.py": "from aureon.conversion.dust_converter import DustConverter, get_dust_converter",
    }
    for rel, line in expect.items():
        text = (ROOT / rel).read_text(encoding="utf-8", errors="replace")
        assert line in text, rel
        assert "aureon.data_feeds.earth_resonance_engine" not in text, rel
        assert "from hnc_earth_resonance" not in text, rel
        assert "from aureon_dust_converter" not in text, rel
