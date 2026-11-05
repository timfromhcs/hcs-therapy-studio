"""German address register: detection, anchoring, and the mixed-register flag."""

from __future__ import annotations

from hcs_therapy.safety.register import (
    Register,
    analyse,
    anchor_instruction,
    is_mixed,
)

# --- detection ------------------------------------------------------------


def test_informal_reply_is_recognised() -> None:
    report = analyse(
        "Das klingt anstrengend. Du hast dir viel vorgenommen, und deine Sorge ist verständlich."
    )
    assert report.register is Register.DU
    assert report.du_forms >= 3
    assert report.sie_forms == 0
    assert not report.mixed


def test_formal_reply_is_recognised() -> None:
    """A sentence-initial ``Sie`` is ambiguous; the mid-sentence forms decide."""
    report = analyse(
        "Das klingt anstrengend. Sie haben sich viel vorgenommen, "
        "und ich verstehe Ihre Sorge. Wenn Sie mögen, schauen wir es uns an."
    )
    assert report.register is Register.SIE
    assert report.sie_forms >= 2
    assert report.du_forms == 0
    assert not report.mixed


def test_lowercase_sie_is_not_formal_address() -> None:
    """Lowercase ``sie`` means she/they. Treating it as formal you is the classic bug."""
    report = analyse("Sie hat lange geschwiegen. Dann sagte sie, dass es ihr besser geht.")
    assert report.sie_forms == 0
    assert report.register is Register.NEUTRAL
    # "Sie hat" is 3rd person singular, so it is positively *not* formal address —
    # better than calling it ambiguous.
    assert report.examples.get("third_person") == ["Sie"]


def test_sentence_initial_sie_with_a_plural_verb_is_formal() -> None:
    """Formal "Sie" takes the 3rd-person plural: "Sie können", never "Sie kann"."""
    report = analyse("Sie können das jederzeit langsamer angehen.")
    assert report.register is Register.SIE
    assert report.sie_forms == 1


def test_sentence_initial_sie_with_a_singular_verb_is_not_address() -> None:
    report = analyse("Sie kann heute nicht kommen.")
    assert report.register is Register.NEUTRAL
    assert report.sie_forms == 0


def test_irregular_auxiliaries_are_resolved() -> None:
    """Morphology alone cannot do "sind"/"ist", so the auxiliaries are explicit."""
    assert analyse("Sie sind nicht allein damit.").register is Register.SIE
    assert analyse("Sie ist nicht allein damit.").register is Register.NEUTRAL
    assert analyse("Sie haben viel geschafft.").register is Register.SIE
    assert analyse("Sie hat viel geschafft.").register is Register.NEUTRAL


def test_an_unresolvable_sentence_initial_sie_stays_ambiguous() -> None:
    """A following noun or adjective gives no verb form, so no verdict is invented."""
    report = analyse("Sie, die Ärztin, war freundlich.")
    assert report.register is Register.NEUTRAL
    assert report.sie_forms == 0


def test_mixed_register_is_detected() -> None:
    report = analyse("Du hast recht. Wenn Sie möchten, schauen wir uns das gemeinsam an.")
    assert report.mixed
    assert report.du_forms == 1
    assert report.sie_forms >= 1


def test_mixed_register_exposes_the_offending_forms() -> None:
    report = analyse("Du hast recht. Wenn Sie möchten, schicken Sie mir bitte Ihre Notizen.")
    payload = report.to_dict()
    assert payload["mixed"] is True
    assert "du" in payload["examples"]
    assert "sie" in payload["examples"]
    assert "Anredebruch" in str(payload["advice"])


def test_ihen_is_unambiguous_formal_address() -> None:
    report = analyse("Ich schreibe Ihnen, weil wir das gemeinsam anschauen können.")
    assert report.register is Register.SIE
    assert report.sie_forms >= 1


def test_neutral_text_without_address_forms() -> None:
    report = analyse("Schlafhygiene bedeutet feste Zeiten und ein kühles Zimmer.")
    assert report.register is Register.NEUTRAL
    assert report.total == 0
    assert not report.mixed


def test_empty_text_is_neutral() -> None:
    for value in ("", "   ", "\n\n"):
        report = analyse(value)
        assert report.register is Register.NEUTRAL
        assert report.to_dict()["advice"] is None


def test_du_plural_forms_are_not_confused_with_du() -> None:
    """``euch``/``euer`` are plural informal; they must not count as ``du``."""
    report = analyse("Habt ihr das schon besprochen? Euer Plan klingt gut.")
    assert report.du_forms == 0


def test_du_forms_are_case_insensitive_at_sentence_start() -> None:
    report = analyse("Du kannst das langsam angehen. Dir hilft vielleicht eine Pause.")
    assert report.register is Register.DU
    assert report.du_forms == 2


def test_mixed_verdict_prefers_the_dominant_register() -> None:
    text = "Du kannst das. Du musst nichts beweisen. Dir hilft eine Pause. Wenn Sie möchten, reden wir."
    report = analyse(text)
    assert report.mixed
    assert report.register is Register.DU  # 3 informal vs 1 formal


def test_is_mixed_shortcut() -> None:
    assert is_mixed("Du hast recht, aber wenn Sie möchten, warten wir.")
    assert not is_mixed("Du hast recht.")
    assert not is_mixed("Sie haben recht.")


# --- anchoring ------------------------------------------------------------


def test_anchor_asks_for_du_when_the_user_writes_du() -> None:
    instruction = anchor_instruction("Ich weiss nicht, ob ich das schaffe. Kannst du mir helfen?")
    assert instruction is not None
    assert '"du"' in instruction
    assert 'kein "Sie"' in instruction
    assert "Die Person duzt dich" in instruction


def test_anchor_asks_for_sie_when_the_user_writes_sie() -> None:
    instruction = anchor_instruction("Können Sie mir sagen, wie ich das angehen soll?")
    assert instruction is not None
    assert '"Sie"' in instruction
    assert 'kein "du"' in instruction
    assert "Die Person siezt dich" in instruction


def test_anchor_falls_back_to_the_apps_own_register() -> None:
    """No signal in the message: use the form the interface itself uses."""
    instruction = anchor_instruction("Ich habe schlecht geschlafen und mache mir Sorgen.")
    assert instruction is not None
    assert '"du"' in instruction
    assert "keine Anrede" in instruction


def test_the_default_can_be_disabled_to_leave_the_model_free() -> None:
    assert anchor_instruction("Ich habe schlecht geschlafen.", default=None) is None


def test_the_default_can_be_switched_to_formal() -> None:
    instruction = anchor_instruction("Ich habe schlecht geschlafen.", default="sie")
    assert instruction is not None
    assert '"Sie"' in instruction


def test_anchor_is_silent_for_english() -> None:
    assert anchor_instruction("I slept badly and I am worried.", locale="en") is None


def test_a_mixed_user_message_uses_the_default_rather_than_guessing() -> None:
    """Mixed input is ambiguous, so the product's own voice breaks the tie."""
    message = "Du hast recht. Können Sie mir trotzdem helfen?"
    instruction = anchor_instruction(message)
    assert instruction is not None
    assert '"du"' in instruction


def test_an_explicit_register_still_wins_over_the_default() -> None:
    assert '"Sie"' in str(anchor_instruction("Können Sie mir helfen?", default="du"))


def test_instruction_for_is_explicit_about_the_target() -> None:
    from hcs_therapy.safety.register import instruction_for

    assert '"du"' in str(instruction_for(Register.DU))
    assert '"Sie"' in str(instruction_for(Register.SIE))
    assert instruction_for(Register.NEUTRAL) is None


def test_anchor_is_idempotent_and_side_effect_free() -> None:
    message = "Kannst du mir helfen?"
    first = anchor_instruction(message)
    second = anchor_instruction(message)
    assert first == second
    assert "du" in message  # the input is unchanged
