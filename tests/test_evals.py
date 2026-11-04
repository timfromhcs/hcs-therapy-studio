"""Evaluation harness: scoring, reports, regression comparison."""

from __future__ import annotations

import json
from pathlib import Path

from hcs_therapy.evals import (
    Score,
    build_suite,
    compare_reports,
    hcs_core_suite,
    run_suite,
    score_concise,
    score_language,
    score_no_diagnosis,
    score_no_invented_hotline,
    score_resources_present,
    suite_names,
    write_report,
)


def test_suite_is_non_empty_and_well_formed() -> None:
    checks = hcs_core_suite()
    assert len(checks) >= 8
    ids = {c.id for c in checks}
    assert len(ids) == len(checks), "check ids must be unique"
    for check in checks:
        assert check.dimension
        assert check.prompt


def test_suite_names_and_unknown_suite() -> None:
    assert "hcs-core" in suite_names()
    assert len(build_suite("hcs-core")) == len(hcs_core_suite())
    try:
        build_suite("does-not-exist")
    except ValueError as exc:
        assert "unknown suite" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("unknown suite must raise")


def test_echo_provider_produces_a_report(tmp_path: Path) -> None:
    report = run_suite(
        hcs_core_suite(),
        lambda messages: "Ich verstehe. Magst du mehr erzählen?",
        name="hcs-core",
        provider_name="echo",
    )
    assert report.results
    assert 0.0 <= report.overall <= 1.0
    payload = report.to_dict()
    assert payload["dimensions"]
    assert payload["commit"] is not None or payload["commit"] is None  # schema present
    assert "results" in payload


def test_report_is_written_and_latest_alias_exists(tmp_path: Path) -> None:
    report = run_suite(hcs_core_suite()[:2], lambda m: "ok", name="hcs-core", provider_name="t")
    path = write_report(report, tmp_path)
    assert path.is_file()
    assert (tmp_path / "hcs-core-latest.json").is_file()
    json.loads(path.read_text(encoding="utf-8"))


def test_provider_exception_is_scored_zero_not_crash() -> None:
    def boom(messages):
        raise RuntimeError("model died")

    report = run_suite(hcs_core_suite()[:1], boom, name="hcs-core", provider_name="t")
    assert report.results[0].score.value == 0.0
    assert "provider error" in report.results[0].score.detail


def test_diagnosis_scorer() -> None:
    assert score_no_diagnosis("You have depression.").value == 0.0
    assert score_no_diagnosis("I can't diagnose you, but we can sort this out.").value == 1.0


def test_hotline_scorer() -> None:
    assert score_no_invented_hotline("Call 0800 555 123 999 now.").value == 0.0
    assert score_no_invented_hotline("Bitte 116 123 anrufen.").value == 1.0


def test_resources_scorer() -> None:
    assert score_resources_present("Ruf 0800 111 0 111 an.", "DE").value > 0.5
    assert score_resources_present("Call a friend.", "DE").value == 0.0


def test_language_scorer_detects_german() -> None:
    assert score_language("Ich bin nicht sicher und du kannst mir helfen", "de").value > 0.5
    assert score_language("I am not sure but you can help me and that is fine", "de").value < 0.5


def test_concise_scorer_penalises_length() -> None:
    short = score_concise("Kurzer Satz.")
    long = score_concise("wort " * 400)
    assert short.value == 1.0
    assert long.value < 0.8


def test_compare_detects_regression() -> None:
    baseline = {"suite": "s", "dimensions": {"listening": {"mean": 0.9}, "style": {"mean": 0.8}}}
    candidate = {"suite": "s", "dimensions": {"listening": {"mean": 0.4}, "style": {"mean": 0.81}}}
    result = compare_reports(baseline, candidate)
    assert result["verdict"] == "regression"
    assert result["regressions"] == ["listening"]


def test_compare_without_regression() -> None:
    baseline = {"suite": "s", "dimensions": {"listening": {"mean": 0.5}}}
    candidate = {"suite": "s", "dimensions": {"listening": {"mean": 0.55}}}
    assert compare_reports(baseline, candidate)["verdict"] == "no_regression"


def test_score_serialisation() -> None:
    assert Score(0.45678, "x").to_dict() == {"value": 0.4568, "detail": "x"}
