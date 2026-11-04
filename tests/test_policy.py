"""Turn policy and the output guard."""

from __future__ import annotations

import pytest

from hcs_therapy.safety import policy, resources
from hcs_therapy.safety.crisis import assess


def test_normal_turn_allows_tools_and_model() -> None:
    decision = policy.decide(assess("Ich hatte einen anstrengenden Tag."))
    assert decision.mode == policy.PolicyMode.NORMAL
    assert decision.allow_model is True
    assert decision.allow_tools is True
    assert decision.override_text is None


def test_imminent_turn_bypasses_the_model_entirely() -> None:
    decision = policy.decide(
        assess("I want to kill myself tonight, I have the pills ready"), region="DE"
    )
    assert decision.mode == policy.PolicyMode.CRISIS_IMMINENT
    assert decision.allow_model is False
    assert decision.allow_tools is False
    assert decision.override_text
    assert "0800 111 0 111" in decision.override_text
    assert "112" in decision.override_text


def test_elevated_turn_is_supportive_with_resources() -> None:
    decision = policy.decide(assess("Ich will nicht mehr leben"), region="DE")
    assert decision.mode == policy.PolicyMode.CRISIS_SUPPORTIVE
    assert decision.override_text
    assert decision.show_resources is True


def test_english_locale_uses_english_template() -> None:
    decision = policy.decide(
        assess("I want to kill myself tonight, I have the pills ready"),
        locale="en",
        region="UK",
    )
    text = decision.override_text or ""
    assert "116 123" in text
    assert "call your local emergency number" in text
    assert "Notruf" not in text


def test_unknown_region_never_invents_a_hotline() -> None:
    decision = policy.decide(
        assess("I want to kill myself"), locale="en", region="nowhere"
    )
    text = decision.override_text or ""
    assert "local emergency number" in text.lower()
    assert "988" not in text


def test_every_shipped_number_is_verified() -> None:
    for region, pack in resources.PACKS.items():
        assert pack.emergency.verified or region == "UNKNOWN"
        for line in pack.lines:
            assert line.source_url.startswith("https://"), region
            assert line.verified, f"{region}/{line.name} is shown but unverified"


def test_no_fictional_numbers_in_pack() -> None:
    allowed = resources.all_numbers()
    assert "112" in allowed
    assert "08001110111" in allowed
    assert "1979" not in allowed


def test_system_prompt_contains_hard_boundaries() -> None:
    prompt = policy.system_prompt("de")
    for phrase in ("Never diagnose", "medication", "crisis service", "agency"):
        assert phrase.lower() in prompt.lower()


# ---------------------------------------------------------------------------
# output guard
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "You have depression and should start treatment.",
        "Du hast eine Depression.",
        "Your diagnosis is PTSD.",
        "Meine Diagnose lautet ADHS.",
    ],
)
def test_diagnosis_claims_are_flagged(text: str) -> None:
    result = policy.scan_output(text)
    assert result.ok is False
    assert "diagnosis_claim" in result.categories


@pytest.mark.parametrize(
    "text",
    [
        "Take 20 mg of your medication twice a day.",
        "Setz die Tabletten einfach ab.",
        "Reduce your dose to half.",
    ],
)
def test_medication_advice_is_flagged(text: str) -> None:
    result = policy.scan_output(text)
    assert result.ok is False
    assert "medication_advice" in result.categories


def test_dependence_language_is_flagged() -> None:
    assert policy.scan_output("You only need me, don't talk to your friends.").ok is False
    assert policy.scan_output("Ich bin der einzige, der dich versteht.").ok is False


def test_invented_hotline_is_flagged() -> None:
    result = policy.scan_output("Call 0800 999 888 777 instead.")
    assert result.ok is False
    assert "invented_hotline" in result.categories


def test_verified_numbers_pass() -> None:
    result = policy.scan_output(
        "Bitte ruf die Telefonseelsorge an: 0800 111 0 111 oder 116 123. Im Notfall 112."
    )
    assert result.ok is True


def test_benign_numbers_are_not_flagged() -> None:
    assert policy.scan_output("Es ist 14:30 Uhr und 3 Grad kalt.").ok is True


def test_empty_output_is_ok() -> None:
    assert policy.scan_output("").ok is True


def test_fallback_text_is_respectful_and_not_clinical() -> None:
    for locale in ("de", "en"):
        text = policy.fallback_after_scan(locale)
        assert "diagnos" in text.lower()
        assert len(text) > 40


def test_region_alias_resolution() -> None:
    assert resources.resolve("germany").region == "DE"
    assert resources.resolve("DE").region == "DE"
    assert resources.resolve("uk").region == "UK"
    assert resources.resolve(None).region == "UNKNOWN"
    assert resources.resolve("atlantis").region == "UNKNOWN"


def test_rendered_block_is_plain_text_and_non_graphic() -> None:
    text = resources.render("DE", "de")
    assert "Telefonseelsorge" in text
    assert "kein Krisendienst" in text
    assert "112" in text
