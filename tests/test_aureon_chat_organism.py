from training.aureon_chat_server import _with_gears, completion_body, format_prompt


def _snapshot():
    return {
        "schema": "aureon.hnc-llm-organism.v1",
        "all_turned": True,
        "all_engaged": True,
        "phase": "pre_inference",
        "authority": "evidence_only",
        "gears": [
            {
                "name": "field",
                "turned": True,
                "engaged": True,
                "receipt_id": "hnc:live_field:before-generation",
            },
            {
                "name": "auris",
                "turned": True,
                "engaged": True,
                "grounded_inputs": 3,
                "total_inputs": 7,
            },
            {
                "name": "qgita",
                "turned": True,
                "engaged": True,
                "receipt_id": "hnc:lambda_history:before-generation",
                "global_R": 0.65,
            },
        ],
    }


def test_prompt_contains_precaptured_organism_state_before_user_text():
    prompt = format_prompt(
        [{"role": "user", "content": "Explain the current structural state."}],
        organism=_snapshot(),
    )

    assert prompt.startswith("system: [AUREON_ORGANISM_STATE]")
    assert "untrusted software state" in prompt
    assert "hnc:live_field:before-generation" in prompt
    assert "hnc:lambda_history:before-generation" in prompt
    assert prompt.index("before-generation") < prompt.index("Explain the current")
    assert prompt.endswith("assistant:")


def test_response_reuses_prompt_snapshot_and_preserves_reply():
    body = completion_body('{"verdict":"supported"}', 10, 2, "aureon-7b-v65k")
    out = _with_gears(
        body,
        '{"verdict":"supported"}',
        organism=_snapshot(),
    )

    assert out["choices"][0]["message"]["content"] == '{"verdict":"supported"}'
    assert out["hnc_gears"]["parsed"] is True
    assert out["hnc_gears"]["gears"][1]["receipt_id"] == (
        "hnc:live_field:before-generation"
    )
    assert out["hnc_gears"]["gears"][3]["receipt_id"] == (
        "hnc:lambda_history:before-generation"
    )
