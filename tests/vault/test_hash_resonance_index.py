"""Pure hash tests and fail-closed runtime-index tests."""

from __future__ import annotations

from typing import Any, Callable

import pytest

from aureon.vault.voice.hash_resonance_index import (
    HASH_RESONANCE_RELEASE_HOLD,
    BondRecord,
    HashResonanceIndex,
    _bonding_fingerprint,
    _normalise_payload,
    bond_strength,
)


class _Trap:
    def __getattribute__(self, _name: str) -> Any:
        raise AssertionError("release-held hash index touched an effect owner")


def test_hash_normalisation_and_strength_remain_pure() -> None:
    normalised = _normalise_payload({"ts": 1, "value": 1.23456, "name": "x"})
    assert normalised == {"name": "x", "value": 1.235}
    left = _bonding_fingerprint(
        persona="engineer", intent_phrase="build", payload={"ts": 1, "x": 2},
        source_topic="goal", category="intent",
    )
    right = _bonding_fingerprint(
        persona="engineer", intent_phrase="build", payload={"ts": 99, "x": 2},
        source_topic="goal", category="intent",
    )
    assert left == right
    assert bond_strength(1) == 0.0
    assert bond_strength(8) > bond_strength(2)
    assert HASH_RESONANCE_RELEASE_HOLD.startswith("hash_resonance_index_hold:")


def test_constructor_is_inert_and_empty_queries_are_local() -> None:
    index = HashResonanceIndex(vault=_Trap(), thought_bus=_Trap())
    assert index._subscribed is False
    assert index.summary()["total_cards"] == 0
    assert index.strongest_bonds() == []
    assert index.bond_count("missing") == 0
    assert index.fingerprint_for_content("missing") is None


@pytest.mark.parametrize(
    "factory",
    [
        lambda index, bond: index.start(),
        lambda index, bond: index.rebuild_from_vault(),
        lambda index, bond: index._on_vault_card_added(_Trap()),
        lambda index, bond: index._index_card(_Trap(), _publish=True),
        lambda index, bond: index._publish_bond(bond, 3),
    ],
)
def test_indexing_subscription_and_publish_paths_are_held(
    factory: Callable[[HashResonanceIndex, BondRecord], Any],
) -> None:
    index = HashResonanceIndex(vault=_Trap(), thought_bus=_Trap())
    bond = BondRecord("fp")
    with pytest.raises(RuntimeError, match="hash_resonance_index_hold"):
        factory(index, bond)
    assert index._subscribed is False
    assert index.summary()["total_cards"] == 0
