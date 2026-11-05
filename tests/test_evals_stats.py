"""Evaluation statistics: intervals, paired significance, ranking, calibration."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hcs_therapy.evals import (
    Score,
    calibration_report,
    compare_reports,
    rank_reports,
    run_suite,
)


def _report(scores: dict[str, dict[str, float]], *, suite: str = "hcs-core") -> dict:
    results = [
        {"id": check_id, "dimension": dimension, "score": {"value": value}}
        for dimension, checks in scores.items()
        for check_id, value in checks.items()
    ]
    return {
        "suite": suite,
        "provider": "echo",
        "created_at": "2026-11-04T00:00:00Z",
        "overall": sum(item["score"]["value"] for item in results) / len(results),
        "results": results,
        "dimensions": {
            dimension: {
                "mean": sum(checks.values()) / len(checks),
                "n": len(checks),
            }
            for dimension, checks in scores.items()
        },
    }


# --- intervals ------------------------------------------------------------


def test_report_schema_is_version_2() -> None:
    report = run_suite(
        [
            _check("a", "empathy", 1.0),
            _check("b", "empathy", 1.0),
        ],
        lambda messages: "ok",
        name="hcs-core",
        provider_name="echo",
    )
    payload = report.to_dict()
    assert payload["report_schema"] == 2


def test_a_dimension_with_two_checks_gets_no_interval() -> None:
    """Honest: two points cannot support a bootstrap interval."""
    report = run_suite(
        [_check("a", "empathy", 1.0), _check("b", "empathy", 0.0)],
        lambda messages: "ok",
        name="hcs-core",
        provider_name="echo",
    )
    stats = report.to_dict()["dimensions"]["empathy"]
    assert stats["ci_low"] is None
    assert stats["ci_high"] is None
    assert "n too small" in stats["ci_note"]


def test_a_dimension_with_enough_checks_gets_an_interval() -> None:
    checks = [_check(f"c{index}", "empathy", float(index)) for index in range(1, 9)]
    report = run_suite(
        checks, lambda messages: "ok", name="hcs-core", provider_name="echo"
    )
    stats = report.to_dict()["dimensions"]["empathy"]
    assert stats["ci_low"] is not None
    assert stats["ci_low"] <= stats["mean"] <= stats["ci_high"]


def _check(check_id: str, dimension: str, value: float):
    from hcs_therapy.evals import Check

    return Check(
        id=check_id,
        dimension=dimension,
        prompt=f"prompt {check_id}",
        scorer=lambda text, value=value: Score(value),
    )


# --- paired comparison ----------------------------------------------------


def test_compare_is_paired_when_ids_line_up() -> None:
    ids = [f"c{index}" for index in range(6)]
    baseline = _report({"empathy": {check_id: 0.4 for check_id in ids}})
    candidate = _report({"empathy": {check_id: 0.9 for check_id in ids}})
    result = compare_reports(baseline, candidate)
    entry = result["deltas"]["empathy"]
    assert entry["paired_items"] == 6
    assert entry["p_value"] is not None
    assert entry["p_value"] < 0.01
    assert entry["verdict"] == "improvement_significant"
    assert result["paired_checks"] == 6


def test_a_consistent_drop_across_every_item_is_significant() -> None:
    """Zero variance is not "no signal": a uniform drop on six items is the
    strongest evidence a paired test can see."""
    ids = [f"c{index}" for index in range(6)]
    baseline = _report({"empathy": {check_id: 0.80 for check_id in ids}})
    candidate = _report({"empathy": {check_id: 0.70 for check_id in ids}})
    entry = compare_reports(baseline, candidate)["deltas"]["empathy"]
    assert entry["verdict"] == "regression_significant"


def test_a_noisy_small_drop_is_not_called_a_regression() -> None:
    """Mixed signs and a mean drop under the threshold must stay inconclusive."""
    baseline_values = [0.9, 0.1, 0.9, 0.1, 0.9, 0.1]
    candidate_values = [0.9, 0.1, 0.8, 0.2, 0.7, 0.1]
    ids = [f"c{index}" for index in range(6)]
    baseline = _report({"empathy": dict(zip(ids, baseline_values, strict=True))})
    candidate = _report({"empathy": dict(zip(ids, candidate_values, strict=True))})
    entry = compare_reports(baseline, candidate)["deltas"]["empathy"]
    assert entry["verdict"] == "no_difference_detected"
    assert entry["p_value"] > 0.05


def test_compare_without_enough_pairs_says_insufficient_data() -> None:
    baseline = _report({"empathy": {"a": 0.9, "b": 0.2}})
    candidate = _report({"empathy": {"a": 0.1, "b": 0.1}})
    result = compare_reports(baseline, candidate)
    entry = result["deltas"]["empathy"]
    assert entry["p_value"] is None
    assert entry["verdict"] in {"insufficient_data", "regression_unpaired"}
    assert result["verdict"] == "regression"


def test_compare_states_that_it_is_a_paired_test() -> None:
    result = compare_reports(_report({"a": {"x": 1.0}}), _report({"a": {"x": 1.0}}))
    assert "paired bootstrap" in result["note"]


# --- ranking --------------------------------------------------------------


def test_ranking_orders_three_reports_correctly() -> None:
    ids = [f"c{index}" for index in range(3)]
    reports = {
        "good": _report({"empathy": {i: 0.95 for i in ids}, "safety": {i: 0.95 for i in ids}}),
        "mid": _report({"empathy": {i: 0.70 for i in ids}, "safety": {i: 0.70 for i in ids}}),
        "bad": _report({"empathy": {i: 0.20 for i in ids}, "safety": {i: 0.20 for i in ids}}),
    }
    result = rank_reports(reports)
    assert [row["report"] for row in result["ranking"]] == ["good", "mid", "bad"]


def test_ranking_states_its_own_caveat() -> None:
    reports = {
        "a": _report({"empathy": {"x": 0.9}}),
        "b": _report({"empathy": {"x": 0.1}}),
    }
    result = rank_reports(reports)
    assert "coarse" in result["caveat"]
    assert "hypothesis" in result["caveat"]
    assert result["ranking"][0]["strength"] >= result["ranking"][1]["strength"]


def test_ranking_needs_two_reports() -> None:
    with pytest.raises(ValueError):
        rank_reports({"only": _report({"a": {"x": 1.0}})})


def test_ranking_with_disjoint_dimensions_falls_back_to_equal_strength() -> None:
    reports = {
        "a": _report({"empathy": {"x": 0.9}}),
        "b": _report({"safety": {"y": 0.1}}),
    }
    result = rank_reports(reports)
    assert len(result["ranking"]) == 2


# --- calibration ----------------------------------------------------------


def test_calibration_reduces_the_error_it_is_fitted_on() -> None:
    pairs = [{"probability": 0.95, "correct": index % 10 < 7} for index in range(200)]
    report = calibration_report(
        [pair["probability"] for pair in pairs],
        [1 if pair["correct"] else 0 for pair in pairs],
    )
    assert report["temperature"] > 1.0
    assert report["ece_fitted"] <= report["ece"]


def test_calibration_names_the_in_sample_caveat() -> None:
    report = calibration_report([0.6, 0.7, 0.8], [1, 1, 0])
    assert "in-sample" in report["caveat"]


def test_calibration_of_a_calibrated_set_leaves_it_alone() -> None:
    probabilities = [0.5] * 100
    labels = [1, 0] * 50
    report = calibration_report(probabilities, labels)
    assert report["ece"] < 0.01
    assert report["brier"] == pytest.approx(0.25)


def test_calibration_requires_data() -> None:
    with pytest.raises(ValueError):
        calibration_report([], [])


def test_report_round_trips_through_json(tmp_path: Path) -> None:
    report = run_suite(
        [_check("a", "empathy", 0.5)],
        lambda messages: "ok",
        name="hcs-core",
        provider_name="echo",
    )
    payload = report.to_dict()
    path = tmp_path / "r.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert json.loads(path.read_text(encoding="utf-8"))["report_schema"] == 2
