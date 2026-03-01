from state_renormalization.contracts import AskStatus, DecisionEffect


def test_decision_effect_uses_generic_names_on_dump() -> None:
    eff = DecisionEffect(
        evaluates_decision_id="dec:1",
        decision_episode_id="ep:1",
        evaluated_in_episode_id="ep:2",
        response_captured=True,
        status=AskStatus.OK,  # <- generic name
        had_user_utterance=True,
        user_utterance_chars=3,
        elapsed_s=1.25,  # <- generic name
        notes={},
        hypothesis_eval=None,
    )
    d = eff.model_dump(mode="json")

    assert "status" in d
    assert "elapsed_s" in d
    assert "ha_status" not in d
    assert "satellite_elapsed_s" not in d
