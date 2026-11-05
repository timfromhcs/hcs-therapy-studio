"""Report files are read the way Windows users actually produce them.

PowerShell 5.1 `Out-File -Encoding utf8` writes a BOM. A tool that reads its own
report with `encoding="utf-8"` then fails with "Unexpected UTF-8 BOM" — which is
exactly the command in the README.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from hcs_therapy.cli import main

ROOT = Path(__file__).resolve().parents[1]


def _report(path: Path, value: float) -> Path:
    payload = {
        "report_schema": 2,
        "suite": "hcs-core",
        "provider": "echo",
        "created_at": "2026-11-04T00:00:00Z",
        "overall": value,
        "results": [
            {
                "id": f"c{index}",
                "dimension": "empathy",
                "score": {"value": value},
            }
            for index in range(6)
        ],
        "dimensions": {"empathy": {"mean": value, "n": 6}},
    }
    # Write a BOM on purpose: that is what `Out-File -Encoding utf8` does.
    path.write_text(json.dumps(payload), encoding="utf-8-sig")
    return path


def test_eval_rank_accepts_a_bom_prefixed_report(tmp_path, capsys) -> None:
    first = _report(tmp_path / "a.json", 0.9)
    second = _report(tmp_path / "b.json", 0.4)
    code = main(["--home", str(tmp_path), "eval", "rank", "--reports", str(first), str(second), "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ranking"][0]["report"] == "a"


def test_eval_compare_accepts_bom_prefixed_reports(tmp_path, capsys) -> None:
    baseline = _report(tmp_path / "base.json", 0.4)
    candidate = _report(tmp_path / "cand.json", 0.9)
    code = main(
        [
            "--home",
            str(tmp_path),
            "eval",
            "compare",
            "--baseline",
            str(baseline),
            "--candidate",
            str(candidate),
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["deltas"]["empathy"]["paired_items"] == 6
    assert code in (0, 1)


def test_eval_calibrate_reads_a_report_with_calibration_pairs(tmp_path, capsys) -> None:
    path = tmp_path / "cal.json"
    pairs = [
        {"probability": 0.9, "correct": index % 10 < 7} for index in range(120)
    ]
    path.write_text(
        json.dumps({"suite": "cal", "calibration": pairs}), encoding="utf-8-sig"
    )
    code = main(["--home", str(tmp_path), "eval", "calibrate", "--report", str(path), "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["n"] == 120
    assert "ece" in payload and "temperature" in payload


def test_eval_calibrate_without_pairs_explains_itself(tmp_path, capsys) -> None:
    path = tmp_path / "empty.json"
    path.write_text(json.dumps({"suite": "cal"}), encoding="utf-8")
    code = main(["--home", str(tmp_path), "eval", "calibrate", "--report", str(path), "--json"])
    assert code == 1
    assert "calibration" in capsys.readouterr().err


def test_cli_survives_a_non_unicode_console(tmp_path) -> None:
    """A retrieved note containing an arrow or CJK must not crash the CLI."""
    note = tmp_path / "note.md"
    note.write_text("Vulkan → Beschleunigung. 漢字. ≥ 2 Kerne.", encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "hcs_therapy",
            "--home",
            str(tmp_path / "home"),
            "kb",
            "index",
            str(note),
            "--json",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**__import__("os").environ, "PYTHONIOENCODING": "cp1252"},
        cwd=ROOT,
    )
    assert result.returncode == 0, result.stderr
