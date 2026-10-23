"""The synchronicity decoder loads with trading and must use the canonical table."""

from aureon.trading.aureon_auris_trader import CANONICAL_AURIS_HZ
from aureon.wisdom.synchronicity_decoder import NODE_MAPPING


def test_synchronicity_decoder_tiger_and_clownfish_match_canonical_table():
    tiger = NODE_MAPPING[4]
    clownfish = NODE_MAPPING[7]
    assert tiger["node"] == "Tiger"
    assert clownfish["node"] == "Clownfish"
    assert tiger["frequency"] == CANONICAL_AURIS_HZ["Tiger"] == 220.0
    assert clownfish["frequency"] == CANONICAL_AURIS_HZ["Clownfish"] == 963.0
    assert tiger["frequency"] != 741.0
    assert clownfish["frequency"] != 639.0
