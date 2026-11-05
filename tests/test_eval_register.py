"""The register limitation became a measured dimension.

`status.md` recorded from M1 onwards: "the 1.7B model mixed German du and Sie
inside one answer, and appending an emoji. The output guard does not catch
register." These tests pin the scorers that now make both statements measurable.
"""

from __future__ import annotations

import pytest

from hcs_therapy.evals import hcs_core_suite, score_no_emoji, score_register

# --- register scoring -----------------------------------------------------


def test_consistent_du_scores_full() -> None:
    score = score_register("Du kannst das langsam angehen, und dein Tempo ist richtig.")
    assert score.value == 1.0
    assert "du" in score.detail


def test_consistent_sie_scores_full_when_expected() -> None:
    score = score_register(
        "Ich verstehe Ihre Sorge. Wenn Sie mögen, schauen wir es uns gemeinsam an.",
        expected="sie",
    )
    assert score.value == 1.0


def test_mixed_register_cannot_score_well() -> None:
    """The bug that stood in status.md for three sessions, now a number."""
    score = score_register("Du hast recht. Wenn Sie möchten, schicken Sie mir Ihre Notizen.")
    assert score.value <= 0.2
    assert "mixed" in score.detail


def test_wrong_but_consistent_register_is_penalised_less_than_mixing() -> None:
    """Using 'Sie' throughout to someone who wrote 'du' is a mismatch, not a break."""
    wrong = score_register("Sie können das langsam angehen.", expected="du")
    mixed = score_register("Du hast recht. Wenn Sie möchten, warten wir.", expected="du")
    assert wrong.value > mixed.value


def test_neutral_reply_is_acceptable() -> None:
    """Declining to invent an address form is not a failure."""
    score = score_register("Ein kühles Zimmer und feste Zeiten helfen beim Einschlafen.")
    assert score.value == 0.8
    assert "no address forms" in score.detail


# --- emoji scoring --------------------------------------------------------


def test_clean_text_has_no_emoji() -> None:
    score = score_no_emoji("Das klingt nach einer harten Woche.")
    assert score.value == 1.0


def test_an_emoji_is_penalised() -> None:
    score = score_no_emoji("Das klingt nach einer harten Woche. 🌿")
    assert score.value < 1.0
    assert "emoji" in score.detail


def test_multiple_emoji_are_penalised_harder() -> None:
    one = score_no_emoji("Text 🌿")
    many = score_no_emoji("Text 🌿😊🌱")
    assert many.value < one.value


def test_umlauts_are_not_mistaken_for_emoji() -> None:
    """The emoji range must not swallow German letters or typographic quotes."""
    score = score_no_emoji("Grüße, Ängste, Übermut, „Anführung“, – Gedankenstrich")
    assert score.value == 1.0


# --- suite wiring ---------------------------------------------------------


def test_the_suite_measures_register_and_emoji() -> None:
    checks = hcs_core_suite()
    dimensions = {check.dimension for check in checks}
    assert "register" in dimensions
    assert "style" in dimensions
    ids = {check.id for check in checks}
    assert "register/du-consistency" in ids
    assert "register/sie-consistency" in ids
    assert "style/no-emoji" in ids


def test_the_register_checks_use_the_form_the_prompt_uses() -> None:
    """A suite that asks in 'du' and expects 'Sie' would measure the test, not the model."""
    checks = {check.id: check for check in hcs_core_suite()}
    du_check = checks["register/du-consistency"]
    sie_check = checks["register/sie-consistency"]
    assert "du" in du_check.prompt.lower()
    assert "Sie" in sie_check.prompt or "Ihnen" in sie_check.prompt
    assert du_check.scorer("Du kannst das.").value == 1.0
    assert sie_check.scorer("Sie können das.").value == 1.0
    assert du_check.scorer("Sie können das.").value < 1.0


@pytest.mark.parametrize("expected", ["du", "sie"])
def test_register_scorer_rejects_an_empty_reply(expected: str) -> None:
    assert score_register("", expected=expected).value == 0.8
