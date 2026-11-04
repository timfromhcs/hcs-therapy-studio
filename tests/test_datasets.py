"""Dataset gating: provenance, PII, duplicates, review status, leakage."""

from __future__ import annotations

import json
from pathlib import Path

from hcs_therapy.datasets import (
    check_leakage,
    load_dataset_manifests,
    record_fingerprint,
    scan_jsonl,
    validated_training_records,
)


def _record(**overrides):
    base = {
        "id": "ex-1",
        "lang": "de",
        "source_id": "hcs-synthetic-seed",
        "license": "Apache-2.0",
        "task": "support_turn",
        "messages": [
            {"role": "user", "content": "Mir geht es heute schwer."},
            {"role": "assistant", "content": "Das klingt belastend. Magst du erzählen, was passiert ist?"},
        ],
        "review": {"status": "reviewed", "reviewer_role": "unlicensed-internal"},
    }
    base.update(overrides)
    return base


def _write(path: Path, records: list[dict]) -> Path:
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n", encoding="utf-8")
    return path


def test_clean_record_passes(tmp_path: Path) -> None:
    scan = scan_jsonl(_write(tmp_path / "a.jsonl", [_record()]))
    assert scan.ok
    assert scan.trainable
    assert scan.records == 1


def test_missing_provenance_is_rejected(tmp_path: Path) -> None:
    bad = _record()
    del bad["source_id"]
    scan = scan_jsonl(_write(tmp_path / "b.jsonl", [bad]))
    assert not scan.ok
    assert any("source_id" in p.problem for p in scan.problems)


def test_unknown_source_is_rejected(tmp_path: Path) -> None:
    scan = scan_jsonl(
        _write(tmp_path / "c.jsonl", [_record(source_id="ghost")]),
        known_sources={"hcs-synthetic-seed"},
    )
    assert any("no manifest entry" in p.problem for p in scan.problems)


def test_non_permissive_licence_is_rejected(tmp_path: Path) -> None:
    scan = scan_jsonl(_write(tmp_path / "d.jsonl", [_record(license="CC-BY-NC-4.0")]))
    assert any("allow-list" in p.problem for p in scan.problems)


def test_pii_is_detected(tmp_path: Path) -> None:
    record = _record()
    record["messages"][0]["content"] = "Schreib an max.mustermann@example.com oder 0171 1234567."
    scan = scan_jsonl(_write(tmp_path / "e.jsonl", [record]))
    kinds = {kind for _line, kind in scan.pii_hits}
    assert "email" in kinds
    assert scan.ok is False


def test_duplicates_are_detected(tmp_path: Path) -> None:
    scan = scan_jsonl(_write(tmp_path / "f.jsonl", [_record(), _record(id="ex-2")]))
    assert scan.duplicates == 1
    assert not scan.trainable


def test_unreviewed_content_is_not_trainable(tmp_path: Path) -> None:
    record = _record()
    record["review"] = {"status": "unreviewed"}
    scan = scan_jsonl(_write(tmp_path / "g.jsonl", [record]))
    assert scan.unreviewed == 1
    assert scan.trainable is False


def test_invalid_json_is_reported_with_line(tmp_path: Path) -> None:
    path = tmp_path / "h.jsonl"
    path.write_text('{"id": "x"}\nnot json\n', encoding="utf-8")
    scan = scan_jsonl(path)
    assert any(p.line == 2 for p in scan.problems)


def test_bad_role_is_rejected(tmp_path: Path) -> None:
    record = _record()
    record["messages"][0]["role"] = "root"
    scan = scan_jsonl(_write(tmp_path / "i.jsonl", [record]))
    assert any("bad role" in p.problem for p in scan.problems)


def test_empty_message_is_rejected(tmp_path: Path) -> None:
    record = _record()
    record["messages"][1]["content"] = "   "
    scan = scan_jsonl(_write(tmp_path / "j.jsonl", [record]))
    assert any("empty message" in p.problem for p in scan.problems)


def test_leakage_between_train_and_eval_is_detected(tmp_path: Path) -> None:
    train = _write(tmp_path / "train.jsonl", [_record()])
    holdout = _write(tmp_path / "holdout.jsonl", [_record(id="eval-1")])
    problems = check_leakage([train], [holdout])
    assert problems


def test_no_leakage_when_disjoint(tmp_path: Path) -> None:
    train = _write(tmp_path / "train.jsonl", [_record()])
    other = _record(id="eval-2")
    other["messages"] = [
        {"role": "user", "content": "Ganz anderer Text."},
        {"role": "assistant", "content": "Antwort."},
    ]
    holdout = _write(tmp_path / "holdout.jsonl", [other])
    assert check_leakage([train], [holdout]) == []


def test_fingerprint_ignores_metadata() -> None:
    a = _record(id="a")
    b = _record(id="b", lang="en")
    assert record_fingerprint(a) == record_fingerprint(b)


def test_validated_records_refuse_unreviewed_files(tmp_path: Path) -> None:
    record = _record()
    record["review"] = {"status": "unreviewed"}
    _write(tmp_path / "k.jsonl", [record])
    accepted, problems = validated_training_records(tmp_path)
    assert accepted == []
    assert any("unreviewed" in p for p in problems)


def test_validated_records_accept_clean_files(tmp_path: Path) -> None:
    _write(tmp_path / "l.jsonl", [_record()])
    accepted, problems = validated_training_records(tmp_path)
    assert len(accepted) == 1
    assert problems == []


def test_dataset_manifest_validation(tmp_path: Path) -> None:
    import yaml

    (tmp_path / "ds.yaml").write_text(
        yaml.safe_dump(
            {
                "id": "hcs-synthetic-seed",
                "name": "HCS synthetic bilingual seed",
                "version": "1",
                "license_spdx": "Apache-2.0",
                "license_url": "https://www.apache.org/licenses/LICENSE-2.0",
                "source_url": "https://example.invalid/dataset",
                "revision": "c" * 40,
                "language": "de,en",
                "schema": {"format": "jsonl"},
                "records": 12,
                "sha256": None,
                "privacy_review": "synthetic only, no personal data",
                "reviewer_role": "internal",
                "permitted_use": "evaluation and pipeline testing",
                "prohibited_use": ["clinical claims"],
                "splits": {"train": "datasets/train/seed.jsonl"},
            }
        ),
        encoding="utf-8",
    )
    manifests = load_dataset_manifests(tmp_path)
    assert len(manifests) == 1
    assert manifests[0].validate() == []


def test_dataset_manifest_rejects_nc_licence(tmp_path: Path) -> None:
    import yaml

    (tmp_path / "ds.yaml").write_text(
        yaml.safe_dump(
            {
                "id": "nc",
                "license_spdx": "CC-BY-NC-4.0",
                "privacy_review": "x",
                "reviewer_role": "y",
                "permitted_use": "z",
                "splits": {"train": "x"},
            }
        ),
        encoding="utf-8",
    )
    manifest = load_dataset_manifests(tmp_path)[0]
    assert any("allow-list" in p for p in manifest.validate())
