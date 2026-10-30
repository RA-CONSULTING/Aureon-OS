"""Remaining stage-1 packages: generated, organism, and swarm.

Calls go through dispatch. Stage 2 is not opened. Defaults are labelled.
No queen, miner, swarm_motion, brain, or network client is imported here.
"""

from __future__ import annotations

import json
from typing import Any

from aureon_public.alignment_layer import label_result
from aureon_public.body import _unavailable, dispatch
from aureon_public.quiet import quiet
from aureon_public.tools import _finite

# Constants copied from tests/test_druidic_council.py.
_COUNCIL_SOURCE = "tests/test_druidic_council.py"
_NOW = 1_786_473_600.0
_PROPOSAL = "a" * 64
_PROMPT = "b" * 64
_HNC = "hnc:live_field:receipt-a"
_AURIS = "auris:cosmic_state:receipt-b"

# Vectors copied from tests/test_swarm_fleadh.py::test_steer_flow_preserves_step_length_exactly.
_STEER_U = [1.0, 2.0, 0.0, 0.5]
_STEER_GRAD = [0.3, -0.8, 0.4, 0.0]

# Full-strength inputs from tests/generated/test_harmonic_nexus_score_model.py.
_FULL_INPUTS = {
    "source_strength": 1.0,
    "coherence_agreement": 1.0,
    "repeatability": 1.0,
    "friction_feasibility": 1.0,
    "contradiction_handling": 1.0,
}
_BOUNDS_INPUTS = {
    "source_strength": 2.0,
    "coherence_agreement": -1.0,
    "repeatability": 0.5,
    "friction_feasibility": 0.5,
    "contradiction_handling": 0.5,
}
_BREAKDOWN_INPUTS = {
    "source_strength": 1.0,
    "coherence_agreement": 0.5,
    "repeatability": 0.25,
    "friction_feasibility": 0.5,
    "contradiction_handling": 1.0,
}

_EXAMPLE = "Fixed example arguments, not a reading."
_DEFAULTS = "These fields are the dataclass defaults, not a reading."


def _call(module: str, symbol: str, arguments: dict[str, Any]) -> str:
    return dispatch(module, symbol, arguments, server="public")


def _seat_arguments() -> dict[str, Any]:
    return {
        "seat": "seer",
        "agent_id": "agent-seer",
        "decision": "ACCEPT",
        "reason": "seer verified its discipline boundary",
        "gamma": 0.90,
        "proposal_digest": _PROPOSAL,
        "prompt_digest": _PROMPT,
        "hnc_receipt_id": _HNC,
        "auris_receipt_id": _AURIS,
        "auris_node_receipt_id": "auris:node:seer:receipt",
        "source_timestamp": _NOW - 5.0,
        "derived_at": _NOW - 1.0,
    }


@quiet
def generated_default_inputs() -> str:
    """build_default_inputs. Provenance: cited.

    The defaults are the function's own conservative inputs from SOURCE_COUNT.
    They are not a live market reading and not a lighthouse reading.

    Args:
        none: This tool takes no inputs. Label: cited, build_default_inputs.
    """

    return label_result(
        _call(
            "generated/research_cinema/harmonic_nexus_score_model.py",
            "build_default_inputs",
            {},
        ),
        "tests/generated/test_harmonic_nexus_score_model.py::test_default_inputs_are_conservative",
        "Fixed fixture from that test. The function builds its own defaults. Not a live reading.",
    )


@quiet
def generated_normalized() -> str:
    """HarmonicNexusScoreInputs.normalized on the bounds fixture. Provenance: cited.

    The five numbers are tests/generated/test_harmonic_nexus_score_model.py
    test_harmonic_nexus_score_bounds_inputs. Not a live reading.

    Args:
        none: The fixture is fixed. Label: cited.
    """

    return label_result(
        _call(
            "generated/research_cinema/harmonic_nexus_score_model.py",
            "HarmonicNexusScoreInputs.normalized",
            {"init": _BOUNDS_INPUTS},
        ),
        "tests/generated/test_harmonic_nexus_score_model.py::test_harmonic_nexus_score_bounds_inputs",
        "Fixed fixture from that test. Not a live reading.",
    )


@quiet
def generated_score() -> str:
    """harmonic_nexus_score on the full-strength fixture. Provenance: cited.

    The five ones are test_harmonic_nexus_score_full_strength_is_100.
    The score is that fixture, not a live reading.

    Args:
        none: The fixture is fixed. Label: cited.
    """

    return label_result(
        _call(
            "generated/research_cinema/harmonic_nexus_score_model.py",
            "harmonic_nexus_score",
            {"inputs": _FULL_INPUTS},
        ),
        "tests/generated/test_harmonic_nexus_score_model.py::test_harmonic_nexus_score_full_strength_is_100",
        "Fixed fixture from that test. Not a live reading.",
    )


@quiet
def generated_breakdown() -> str:
    """score_breakdown on the breakdown fixture. Provenance: cited.

    The inputs are test_harmonic_nexus_breakdown_matches_score. Not a live reading.

    Args:
        none: The fixture is fixed. Label: cited.
    """

    return label_result(
        _call(
            "generated/research_cinema/harmonic_nexus_score_model.py",
            "score_breakdown",
            {"inputs": _BREAKDOWN_INPUTS},
        ),
        "tests/generated/test_harmonic_nexus_score_model.py::test_harmonic_nexus_breakdown_matches_score",
        "Fixed fixture from that test. Not a live reading.",
    )


@quiet
def organism_compose_layers() -> str:
    """compose_repository_layers with no transport. Provenance: cited.

    No field_transport or market_transport is passed, so those call sites do
    not fetch. The joined hold is not a live market or field reading.

    Args:
        none: The function's own default root is used. Label: cited.
    """

    return label_result(
        _call("organism/repository_layers.py", "compose_repository_layers", {}),
        "aureon.organism.repository_layers.compose_repository_layers",
        "No field or market transport was passed. Not a live reading.",
    )


@quiet
def swarm_voice_read(gamma: float = 0.80) -> str:
    """voice_for_gamma. Provenance: cited.

    The default 0.80 is the ACTIVE row in tests/test_druidic_council.py
    test_voice_bands_use_raw_gamma_without_invented_multiplier.
    It is not a live lighthouse reading.

    Args:
        gamma: Coherence passed to voice_for_gamma. Label: cited.
    """

    number = _finite(gamma)
    if number is None:
        return _unavailable("gamma is missing")
    text = _call("swarm/druidic_council.py", "voice_for_gamma", {"gamma": number})
    if number == 0.80:
        return label_result(
            text,
            "tests/test_druidic_council.py::test_voice_bands_use_raw_gamma_without_invented_multiplier",
            "Fixed fixture from that test. Not a live lighthouse reading.",
        )
    return text


@quiet
def swarm_steer_flow(u_json: str = "", grad_json: str = "") -> str:
    """steer_flow. Provenance: cited.

    The default vectors are tests/test_swarm_fleadh.py
    test_steer_flow_preserves_step_length_exactly. Not a live crowd reading.

    Args:
        u_json: JSON list. Empty uses the test vector. Label: cited.
        grad_json: JSON list. Empty uses the test gradient. Label: cited.
    """

    raw_u = u_json.strip() or json.dumps(_STEER_U)
    raw_grad = grad_json.strip() or json.dumps(_STEER_GRAD)
    try:
        flow = json.loads(raw_u)
        grad = json.loads(raw_grad)
    except json.JSONDecodeError:
        return _unavailable("arguments are not JSON")
    if not isinstance(flow, list) or not isinstance(grad, list):
        return _unavailable("u and grad must be lists")
    text = _call("swarm/fleadh.py", "steer_flow", {"u": flow, "grad": grad})
    if flow == _STEER_U and grad == _STEER_GRAD:
        return label_result(
            text,
            "tests/test_swarm_fleadh.py::test_steer_flow_preserves_step_length_exactly",
            "Fixed fixture from that test. Not a live reading.",
        )
    return text


@quiet
def swarm_build_lane(name: str = "fintech") -> str:
    """build_lane. Provenance: cited.

    The default name is the fintech lane in tests/test_swarm_capabilities.py.
    The lane is built from in-process books. It is not a live market reading
    and it does not place an order.

    Args:
        name: Lane name. Label: cited, build_lane.
    """

    if not isinstance(name, str) or not name.strip():
        return _unavailable("name is missing")
    text = _call("swarm/capability_grid.py", "build_lane", {"name": name})
    if name == "fintech":
        return label_result(
            text,
            "tests/test_swarm_capabilities.py::test_every_lane_carries_real_provenance",
            "Fixed lane name from that test. Not a live market reading.",
        )
    return text


@quiet
def swarm_build_seat() -> str:
    """build_seat_receipt for the seer seat in the council test. Provenance: cited.

    The arguments are the seer row of _seat_receipts in tests/test_druidic_council.py.
    The receipt is that fixture, not a live council.

    Args:
        none: The fixture is fixed. Label: cited.
    """

    return label_result(
        _call("swarm/druidic_council.py", "build_seat_receipt", _seat_arguments()),
        _COUNCIL_SOURCE,
        "Fixed fixture from tests/test_druidic_council.py. Not a live council.",
    )


def _agent_init() -> dict[str, Any]:
    return {"agent_id": "stage1", "role": "scout", "actions": ["hold"]}


@quiet
def swarm_agent_substrate() -> str:
    """SwarmAgent.substrate at t 0. Provenance: cited.

    The agent id, role, and action are fixed example arguments. t is 0.
    The value is that call, not a reading.

    Args:
        none: The example is fixed. Label: cited.
    """

    return label_result(
        _call(
            "swarm/agent.py",
            "SwarmAgent.substrate",
            {"init": _agent_init(), "t": 0.0},
        ),
        "aureon.swarm.agent.SwarmAgent.substrate",
        _EXAMPLE,
    )


@quiet
def swarm_agent_to_dict() -> str:
    """SwarmAgent.to_dict on the fixed example agent. Provenance: cited.

    Args:
        none: The example is fixed. Label: cited.
    """

    return label_result(
        _call("swarm/agent.py", "SwarmAgent.to_dict", {"init": _agent_init()}),
        "aureon.swarm.agent.SwarmAgent",
        _EXAMPLE,
    )


@quiet
def swarm_agent_propose() -> str:
    """SwarmAgent.propose with one fixed action vector. Provenance: cited.

    cluster_gamma is omitted as null, which the method treats as not yet measured.
    Not a live coherence reading.

    Args:
        none: The example is fixed. Label: cited.
    """

    return label_result(
        _call(
            "swarm/agent.py",
            "SwarmAgent.propose",
            {
                "init": _agent_init(),
                "action_vectors": {"hold": [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]},
                "cluster_gamma": None,
            },
        ),
        "aureon.swarm.agent.SwarmAgent.propose",
        _EXAMPLE + " cluster_gamma null means the method's own not-yet-measured branch.",
    )


@quiet
def swarm_coherence_gamma() -> str:
    """ClusterCoherence.gamma on an empty window. Provenance: cited.

    The window 8 is the class default. gamma is None while the window is warming.
    That None is the method's own result, not a reading.

    Args:
        none: The example is fixed. Label: cited.
    """

    return label_result(
        _call(
            "swarm/coherence.py",
            "ClusterCoherence.gamma",
            {"init": {"window": 8}},
        ),
        "aureon.swarm.coherence.ClusterCoherence",
        "Window 8 is the class default. An empty window is not a reading.",
    )


@quiet
def swarm_coherence_to_dict() -> str:
    """ClusterCoherence.to_dict on an empty window. Provenance: cited.

    Args:
        none: The example is fixed. Label: cited.
    """

    return label_result(
        _call("swarm/coherence.py", "ClusterCoherence.to_dict", {"init": {"window": 8}}),
        "aureon.swarm.coherence.ClusterCoherence",
        "Window 8 is the class default. Not a reading.",
    )


@quiet
def swarm_echo() -> str:
    """CausalEchoBus.echo on an empty bus. Provenance: cited.

    tau 3 is the class default. step 0 has nothing stored, so the method returns
    None. That None is a dark echo, not a reading.

    Args:
        none: The example is fixed. Label: cited.
    """

    return label_result(
        _call("swarm/memory_bus.py", "CausalEchoBus.echo", {"init": {"tau": 3}, "step": 0}),
        "aureon.swarm.memory_bus.CausalEchoBus.echo",
        "tau 3 is the class default. An empty bus is not a reading.",
    )


@quiet
def swarm_echo_to_dict() -> str:
    """CausalEchoBus.to_dict on an empty bus. Provenance: cited.

    Args:
        none: The example is fixed. Label: cited.
    """

    return label_result(
        _call("swarm/memory_bus.py", "CausalEchoBus.to_dict", {"init": {"tau": 3}}),
        "aureon.swarm.memory_bus.CausalEchoBus",
        "tau 3 is the class default. Not a reading.",
    )


@quiet
def swarm_steer_field() -> str:
    """SteeringField.steer with no heading. Provenance: cited.

    resistance 0.5 is the class default. heading null is the method's
    no-heading branch. Not a live path.

    Args:
        none: The example is fixed. Label: cited.
    """

    return label_result(
        _call(
            "swarm/steering.py",
            "SteeringField.steer",
            {"init": {"resistance": 0.5}, "proposal": [1.0, 0.0, 0.0], "heading": None},
        ),
        "aureon.swarm.steering.SteeringField.steer",
        "resistance 0.5 is the class default. heading null is a fixed example, not a reading.",
    )


@quiet
def swarm_seat_to_dict() -> str:
    """SeatReceipt.to_dict on a fixed example payload. Provenance: cited.

    The payload is one field, not a validated council receipt.

    Args:
        none: The example is fixed. Label: cited.
    """

    return label_result(
        _call(
            "swarm/druidic_council.py",
            "SeatReceipt.to_dict",
            {"init": {"payload": {"seat": "seer"}}},
        ),
        "aureon.swarm.druidic_council.SeatReceipt",
        "Fixed example payload. Not a council reading.",
    )


@quiet
def swarm_council_to_dict() -> str:
    """CouncilReceipt.to_dict on a fixed example payload. Provenance: cited.

    The payload is one field, not a validated council receipt.

    Args:
        none: The example is fixed. Label: cited.
    """

    return label_result(
        _call(
            "swarm/druidic_council.py",
            "CouncilReceipt.to_dict",
            {"init": {"payload": {"schema": "example"}}},
        ),
        "aureon.swarm.druidic_council.CouncilReceipt",
        "Fixed example payload. Not a council reading.",
    )


@quiet
def swarm_actualization_to_dict() -> str:
    """Actualization.to_dict on explicit empty fields. Provenance: cited.

    actualized false, action null, and canonical_status canonical_dark are fixed
    example arguments. They are not a gate reading.

    Args:
        none: The example is fixed. Label: cited.
    """

    return label_result(
        _call(
            "swarm/queen_gate.py",
            "Actualization.to_dict",
            {
                "init": {
                    "actualized": False,
                    "action": None,
                    "gamma_cluster": None,
                    "gamma_effective": None,
                    "canonical_status": "canonical_dark",
                }
            },
        ),
        "aureon.swarm.queen_gate.Actualization",
        "Fixed example fields. canonical_dark is the gate's own dark-field word. Not a reading.",
    )


TOOLS: list[Any] = [
    generated_default_inputs,
    generated_normalized,
    generated_score,
    generated_breakdown,
    organism_compose_layers,
    swarm_voice_read,
    swarm_steer_flow,
    swarm_build_lane,
    swarm_build_seat,
    swarm_agent_substrate,
    swarm_agent_to_dict,
    swarm_agent_propose,
    swarm_coherence_gamma,
    swarm_coherence_to_dict,
    swarm_echo,
    swarm_echo_to_dict,
    swarm_steer_field,
    swarm_seat_to_dict,
    swarm_council_to_dict,
    swarm_actualization_to_dict,
]
