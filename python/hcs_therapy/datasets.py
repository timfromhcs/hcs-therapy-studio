"""Dataset pipeline: manifest validation, provenance, PII scan, dedup, leakage.

The hard rule from the build contract: no training row exists without
provenance, and no evaluation row may appear in a training file. Both are
enforced by code that fails, not by documentation that asks nicely.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .models.manifest import ALLOWED_LICENSES, REVISION_RE, SHA256_RE, ManifestError

REQUIRED_RECORD_FIELDS = ("id", "lang", "source_id", "license", "task", "messages")
ALLOWED_ROLES = {"system", "user", "assistant", "tool"}
REQUIRED_REVIEW_FIELDS = ("status", "reviewer_role")


@dataclass
class RecordProblem:
    line: int
    problem: str


@dataclass
class DatasetScan:
    path: Path
    records: int = 0
    problems: list[RecordProblem] = field(default_factory=list)
    languages: dict[str, int] = field(default_factory=dict)
    sources: dict[str, int] = field(default_factory=dict)
    duplicates: int = 0
    pii_hits: list[tuple[int, str]] = field(default_factory=list)
    unreviewed: int = 0
    review_statuses: dict[str, int] = field(default_factory=dict)
    hashes: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems and not self.pii_hits

    @property
    def trainable(self) -> bool:
        """Only fully reviewed rows may train a promotable model."""
        return (
            self.ok
            and self.unreviewed == 0
            and self.duplicates == 0
            and set(self.review_statuses) == {"reviewed"}
        )

    @property
    def smoke_only(self) -> bool:
        return bool(self.review_statuses) and set(self.review_statuses) <= {"engineering-smoke"}

    def to_dict(self) -> dict:
        return {
            "path": str(self.path),
            "records": self.records,
            "ok": self.ok,
            "trainable": self.trainable,
            "smoke_only": self.smoke_only,
            "duplicates": self.duplicates,
            "unreviewed": self.unreviewed,
            "review_statuses": self.review_statuses,
            "languages": self.languages,
            "sources": self.sources,
            "problems": [{"line": p.line, "problem": p.problem} for p in self.problems],
            "pii_hits": [{"line": line, "kind": kind} for line, kind in self.pii_hits],
        }


PII_PATTERNS = {
    "email": re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]{2,}\b"),
    "phone": re.compile(r"(?:\+49|\+43|\+41|\+1|0)\s?\d{2,5}[\s/-]?\d{3,}"),
    "iban": re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b"),
    "long_digit_run": re.compile(r"\b\d{9,}\b"),
    "address_hint": re.compile(r"\b\d{1,4}\s+[A-ZÄÖÜ][a-zäöüß]+(straße|strasse|weg|gasse|platz)\b"),
}


def _normalise_for_hash(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def record_fingerprint(record: dict[str, Any]) -> str:
    """Hash of the conversational content only, ignoring metadata."""
    parts = []
    for message in record.get("messages") or []:
        if isinstance(message, dict):
            parts.append(f"{message.get('role')}:{message.get('content', '')}")
    return hashlib.sha256(_normalise_for_hash("\n".join(parts)).encode("utf-8")).hexdigest()


def scan_jsonl(path: Path, known_sources: set[str] | None = None) -> DatasetScan:
    scan = DatasetScan(path=path)
    seen: dict[str, int] = {}
    with path.open("r", encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                scan.problems.append(RecordProblem(number, f"invalid JSON: {exc.msg}"))
                continue
            if not isinstance(record, dict):
                scan.problems.append(RecordProblem(number, "record is not a JSON object"))
                continue
            scan.records += 1

            for required in REQUIRED_RECORD_FIELDS:
                if required not in record:
                    scan.problems.append(RecordProblem(number, f"missing field {required!r}"))

            license_name = str(record.get("license", ""))
            if license_name and not any(license_name.startswith(ok) for ok in ALLOWED_LICENSES):
                scan.problems.append(
                    RecordProblem(number, f"licence {license_name!r} is not on the allow-list")
                )

            if known_sources is not None:
                source_id = str(record.get("source_id", ""))
                if source_id and source_id not in known_sources:
                    scan.problems.append(
                        RecordProblem(number, f"source_id {source_id!r} has no manifest entry")
                    )

            messages = record.get("messages")
            if isinstance(messages, list):
                for message in messages:
                    if not isinstance(message, dict):
                        scan.problems.append(RecordProblem(number, "message is not an object"))
                        continue
                    role = message.get("role")
                    if role not in ALLOWED_ROLES:
                        scan.problems.append(RecordProblem(number, f"bad role {role!r}"))
                    content = message.get("content")
                    if not isinstance(content, str) or not content.strip():
                        scan.problems.append(RecordProblem(number, "empty message content"))
                    else:
                        for kind, pattern in PII_PATTERNS.items():
                            if pattern.search(content):
                                scan.pii_hits.append((number, kind))
            elif "messages" in record:
                scan.problems.append(RecordProblem(number, "messages must be a list"))

            review = record.get("review") or {}
            status = "unreviewed"
            if isinstance(review, dict) and review.get("status"):
                status = str(review["status"])
                if status not in ("unreviewed", "pending"):
                    for key in REQUIRED_REVIEW_FIELDS:
                        if key not in review:
                            scan.problems.append(
                                RecordProblem(number, f"review is missing {key!r}")
                            )
            scan.review_statuses[status] = scan.review_statuses.get(status, 0) + 1
            if status in ("unreviewed", "pending", ""):
                scan.unreviewed += 1

            lang = str(record.get("lang", "unknown"))
            scan.languages[lang] = scan.languages.get(lang, 0) + 1
            source = str(record.get("source_id", "unknown"))
            scan.sources[source] = scan.sources.get(source, 0) + 1

            fingerprint = record_fingerprint(record)
            scan.hashes.append(fingerprint)
            if fingerprint in seen:
                scan.duplicates += 1
                scan.problems.append(
                    RecordProblem(number, f"duplicate of line {seen[fingerprint]}")
                )
            else:
                seen[fingerprint] = number
    return scan


@dataclass
class DatasetManifest:
    id: str
    name: str
    version: str
    license_spdx: str
    license_url: str
    source_url: str
    revision: str
    language: str
    schema: dict[str, Any]
    records: int
    sha256: str | None
    privacy_review: str
    reviewer_role: str
    permitted_use: str
    prohibited_use: list[str]
    splits: dict[str, str] = field(default_factory=dict)
    notes: str | None = None

    def validate(self) -> list[str]:
        problems = []
        if not any(self.license_spdx.startswith(ok) for ok in ALLOWED_LICENSES):
            problems.append(f"licence {self.license_spdx!r} is not on the allow-list")
        if self.license_url and not self.license_url.startswith("https://"):
            problems.append("license_url must be https")
        if self.revision and not REVISION_RE.match(self.revision.lower()):
            problems.append("revision must be a pinned 40-character commit SHA")
        if self.sha256 and not SHA256_RE.match(self.sha256.lower()):
            problems.append("sha256 must be 64 hex characters")
        if self.records < 0:
            problems.append("records must be >= 0")
        if not self.privacy_review:
            problems.append("privacy_review is required")
        if not self.reviewer_role:
            problems.append("reviewer_role is required")
        if self.permitted_use in {"", None}:
            problems.append("permitted_use is required")
        if not self.splits:
            problems.append("splits must map split name to file path")
        return problems


def load_dataset_manifests(directory: Path) -> list[DatasetManifest]:
    manifests: list[DatasetManifest] = []
    for pattern in ("*.yaml", "*.yml"):
        for path in sorted(directory.glob(pattern)):
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ManifestError(f"{path}: dataset manifest must be a mapping")
            try:
                manifests.append(
                    DatasetManifest(
                        id=raw["id"],
                        name=raw.get("name", raw["id"]),
                        version=str(raw.get("version", "0")),
                        license_spdx=raw["license_spdx"],
                        license_url=raw.get("license_url", ""),
                        source_url=raw.get("source_url", ""),
                        revision=str(raw.get("revision", "")),
                        language=raw.get("language", "unknown"),
                        schema=raw.get("schema", {}),
                        records=int(raw.get("records", 0)),
                        sha256=raw.get("sha256"),
                        privacy_review=raw.get("privacy_review", ""),
                        reviewer_role=raw.get("reviewer_role", ""),
                        permitted_use=raw.get("permitted_use", ""),
                        prohibited_use=list(raw.get("prohibited_use") or []),
                        splits=dict(raw.get("splits") or {}),
                        notes=raw.get("notes"),
                    )
                )
            except KeyError as exc:
                raise ManifestError(f"{path}: missing field {exc.args[0]!r}") from exc
    return manifests


def check_leakage(train_files: list[Path], eval_files: list[Path]) -> list[str]:
    """Return human-readable overlaps between training and evaluation content."""
    train_hashes: dict[str, Path] = {}
    for path in train_files:
        scan = scan_jsonl(path)
        for digest in scan.hashes:
            train_hashes[digest] = path
    problems: list[str] = []
    for path in eval_files:
        scan = scan_jsonl(path)
        for digest in scan.hashes:
            if digest in train_hashes:
                problems.append(
                    f"evaluation content in {path.name} also appears in {train_hashes[digest].name}"
                )
                break
    return problems


def iter_records(path: Path) -> Iterator[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def validated_training_records(
    directory: Path,
    known_sources: set[str] | None = None,
    *,
    allow_smoke: bool = False,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Only rows that pass every gate may reach a trainer.

    ``allow_smoke`` permits ``engineering-smoke`` rows so the pipeline can be
    exercised end to end. Those rows are tagged ``_smoke_only`` and any run
    trained on them must not be promoted or cited as a quality result.
    """
    accepted: list[dict[str, Any]] = []
    problems: list[str] = []
    for path in sorted(directory.glob("*.jsonl")):
        scan = scan_jsonl(path, known_sources)
        if not scan.ok:
            problems.extend(f"{path.name}:{p.line}: {p.problem}" for p in scan.problems)
            problems.extend(f"{path.name}:{line}: PII {kind}" for line, kind in scan.pii_hits)
            continue
        if scan.unreviewed:
            problems.append(
                f"{path.name}: {scan.unreviewed} unreviewed row(s); not trainable until reviewed"
            )
            continue
        if scan.duplicates:
            problems.append(f"{path.name}: {scan.duplicates} duplicate row(s) must be removed")
            continue
        if scan.smoke_only and not allow_smoke:
            problems.append(
                f"{path.name}: engineering-smoke data is not a training corpus; "
                "pass allow_smoke=True only for a pipeline smoke run"
            )
            continue
        for record in iter_records(path):
            if scan.smoke_only:
                record["_smoke_only"] = True
                record["_source_file"] = path.name
            accepted.append(record)
    return accepted, problems
