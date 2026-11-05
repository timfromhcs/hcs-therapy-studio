"""Multi-turn crisis trajectories for the deterministic policy layer.

These measure the gate, not the model: a crisis turn bypasses the model entirely and
the following turns are judged by what the policy hands on. The distinction is stated
in every report rather than assumed by the reader.
"""

from __future__ import annotations

import pytest

from hcs_therapy.trajectories import (
    ATTENTIVE_WINDOW,
    Scenario,
    SessionState,
    Turn,
    crisis_scenarios,
    run_all,
    run_scenario,
)

# --- the shipped scenarios -------------------------------------------------


def test_every_shipped_scenario_passes() -> None:
    report = run_all()
    failed = [row for row in report["results"] if not row["ok"]]
    assert not failed, [(row["scenario"], row["first_failing_turn"]) for row in failed]
    assert report["scenarios"] == 6
    assert report["passed"] == 6


def test_the_report_says_it_did_not_call_a_model() -> None:
    """A trajectory report that hides this would be read as a model benchmark."""
    assert "no model is called" in run_all()["metric"]


def test_scenario_ids_are_unique() -> None:
    ids = [scenario.id for scenario in crisis_scenarios()]
    assert len(ids) == len(set(ids))


# --- escalation ordering ---------------------------------------------------


def test_the_gate_fires_on_the_explicit_turn_not_earlier() -> None:
    """The most important property: position matters, and a suite of one turn cannot see it."""
    scenario = next(s for s in crisis_scenarios() if s.id == "escalation/slow-build")
    result = run_scenario(scenario)
    assert result.ok
    assert [turn.mode for turn in result.turns] == [
        "normal",
        "normal",
        "crisis_imminent",
    ]
    assert [turn.model_bypassed for turn in result.turns] == [False, False, True]


def test_a_quoted_sentence_does_not_become_the_users_intent() -> None:
    scenario = next(s for s in crisis_scenarios() if s.id == "language/quoted-and-third-party")
    result = run_scenario(scenario)
    assert result.ok
    assert result.turns[0].mode == "crisis_supportive"
    assert result.turns[0].resources_shown is True


def test_a_negated_mention_does_not_fire_the_imminent_path() -> None:
    scenario = next(s for s in crisis_scenarios() if s.id == "negation/explicit-doubt")
    result = run_scenario(scenario)
    assert result.ok
    assert result.turns[0].mode == "normal"


def test_an_ordinary_hard_day_stays_ordinary() -> None:
    scenario = next(s for s in crisis_scenarios() if s.id == "recovery/no-false-crisis")
    result = run_scenario(scenario)
    assert result.ok
    assert all(turn.mode == "normal" for turn in result.turns)
    assert not any(turn.resources_shown for turn in result.turns)


# --- session memory --------------------------------------------------------


def test_the_session_stays_attentive_after_a_hand_off() -> None:
    """Two messages after a crisis the app must not snap back to small talk."""
    scenario = next(s for s in crisis_scenarios() if s.id == "escalation/aftermath-stays-attentive")
    result = run_scenario(scenario)
    assert result.ok
    assert result.turns[0].mode == "crisis_imminent"
    assert result.turns[1].attentive is True
    assert result.turns[2].attentive is True
    assert result.turns[1].mode == "normal"


def test_attentiveness_expires_after_the_window() -> None:
    scenario = next(s for s in crisis_scenarios() if s.id == "escalation/window-decays")
    result = run_scenario(scenario)
    assert result.ok
    attentive = [turn.attentive for turn in result.turns]
    # crisis turn + exactly ATTENTIVE_WINDOW following turns, then ordinary.
    assert attentive == [True, True, True, True, False]


def test_the_window_is_configurable_and_validated() -> None:
    assert SessionState(window=0).window == 0
    small = SessionState(window=1)
    small.decide("Ich bringe mich um.")
    _, after_one = small.decide("Es geht gerade.")
    _, after_two = small.decide("Danke.")
    assert after_one.attentive is True
    assert after_two.attentive is False
    with pytest.raises(ValueError):
        SessionState(window=-1)


def test_a_second_escalation_restarts_the_window() -> None:
    session = SessionState(window=2)
    session.decide("Ich bringe mich um.")
    session.decide("Ich habe angerufen.")
    session.decide("Ich bringe mich heute Nacht um.")
    _, decision = session.decide("Alles okay.")
    assert decision.attentive is True
    assert session.escalations == 2


def test_the_attentive_turn_carries_a_system_suffix() -> None:
    """The carry-over must reach the prompt, not just a flag in a report."""
    session = SessionState()
    session.decide("Ich bringe mich um.")
    _, decision = session.decide("Ich habe mit meiner Schwester gesprochen.")
    assert decision.system_suffix
    assert "earlier in this conversation" in decision.system_suffix.lower()
    assert decision.allow_model is True


def test_a_normal_turn_without_history_has_no_suffix() -> None:
    _, decision = SessionState().decide("Ich habe schlecht geschlafen.")
    assert decision.system_suffix == ""
    assert decision.attentive is False


# --- the runner's own contract --------------------------------------------


def test_a_wrong_expectation_produces_a_named_failure() -> None:
    """A suite that cannot fail is a suite that proves nothing."""
    scenario = Scenario(
        id="synthetic/should-fail",
        description="deliberately wrong expectation",
        turns=[Turn("Ich habe schlecht geschlafen.", expect_mode="crisis_imminent")],
    )
    result = run_scenario(scenario)
    assert not result.ok
    assert result.first_failing_turn == 1
    assert any("mode" in problem for problem in result.turns[0].problems)


def test_expectations_default_to_the_expected_mode() -> None:
    crisis = Turn("x", expect_mode="crisis_imminent")
    normal = Turn("x", expect_mode="normal")
    assert crisis.resources_expected is True
    assert crisis.bypass_expected is True
    assert normal.resources_expected is False
    assert normal.bypass_expected is False


def test_an_explicit_expectation_overrides_the_derived_one() -> None:
    turn = Turn("x", expect_mode="normal", expect_model_bypassed=True)
    assert turn.bypass_expected is True


def test_attentive_is_only_asserted_when_the_scenario_asks() -> None:
    assert Turn("x", expect_mode="normal").expect_attentive is None
    assert Turn("x", expect_mode="normal").to_dict()["expect_attentive"] is None


def test_a_crisis_turn_must_produce_deterministic_text() -> None:
    scenario = Scenario(
        id="synthetic/empty-override",
        description="a bypass without text would be a blank screen at the worst moment",
        turns=[Turn("Ich bringe mich heute Nacht um.", expect_mode="crisis_imminent")],
    )
    result = run_scenario(scenario)
    assert result.ok
    assert result.turns[0].model_bypassed is True


def test_run_all_reports_turn_level_detail() -> None:
    report = run_all()
    first = report["results"][0]
    assert "turns" in first
    assert {"mode", "resources_shown", "model_bypassed", "attentive", "ok"} <= set(
        first["turns"][0]
    )


def test_the_attentive_window_constant_is_small_and_explicit() -> None:
    """Three turns is a product decision, not a magic number; pin it so it cannot drift."""
    assert ATTENTIVE_WINDOW == 3
