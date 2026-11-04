"""Model and licence manifest schemas.

A manifest is the only way an artifact enters the build. Validation is strict on
purpose: an unpinned revision, a missing licence, a non-HTTPS source or an
unhashed file is a hard error, not a warning.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
ALLOWED_KINDS = {"model", "dataset", "runtime", "encoder", "tokenizer", "benchmark", "python-dependency"}
ALLOWED_LICENSES = {
    "Apache-2.0",
    "MIT",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "CC0-1.0",
    "CC-BY-4.0",
    "CC-BY-SA-4.0",
    "ISC",
    "Unlicense",
}
#: Licences we refuse for a default release (see RESEARCH-AND-ROADMAP.md §2).
REJECTED_LICENSE_PREFIXES = (
    "CC-BY-NC",
    "CC-BY-ND",
    "GPL",
    "AGPL",
    "OpenRAIL",
    "proprietary",
    "unknown",
)


class ManifestError(ValueError):
    """A manifest is structurally invalid or violates the licence policy."""


@dataclass
class ManifestFile:
    name: str
    url: str
    sha256: str
    size_bytes: int | None = None

    def validate(self) -> list[str]:
        problems: list[str] = []
        if not self.name or "/" in self.name or "\\" in self.name:
            problems.append(f"file name must be a plain name, got {self.name!r}")
        if not self.url.lower().startswith("https://"):
            problems.append(f"{self.name}: url must be https")
        if not SHA256_RE.match(self.sha256.lower()):
            problems.append(f"{self.name}: sha256 must be 64 hex characters")
        if self.size_bytes is not None and self.size_bytes <= 0:
            problems.append(f"{self.name}: size_bytes must be positive")
        return problems


@dataclass
class Geometry:
    n_layers: int
    n_kv_heads: int
    head_dim: int
    n_params: int | None = None


@dataclass
class ModelManifest:
    id: str
    kind: str
    name: str
    publisher: str
    source_url: str
    revision: str
    license_spdx: str
    license_url: str
    files: list[ManifestFile] = field(default_factory=list)
    geometry: Geometry | None = None
    chat_template: str | None = None
    quantisation: str | None = None
    upstream_notice_required: bool = True
    redistribution: str = "permitted_subject_to_license"
    commercial_use: str = "permitted_subject_to_license"
    modification: str = "permitted_subject_to_license"
    components: list[str] = field(default_factory=list)
    approved: bool = False
    reviewed_by: str | None = None
    reviewed_at: str | None = None
    notes: str | None = None
    #: local path once installed (filled by the store, not by the manifest file)
    installed_path: str | None = None

    @property
    def total_size_bytes(self) -> int:
        return sum(f.size_bytes or 0 for f in self.files)

    def validate(self) -> list[str]:
        problems: list[str] = []
        if not re.match(r"^[a-z0-9][a-z0-9._-]{2,80}$", self.id):
            problems.append(f"id {self.id!r} must be lowercase [a-z0-9._-] and 3-80 chars")
        if self.kind not in ALLOWED_KINDS:
            problems.append(f"kind {self.kind!r} not in {sorted(ALLOWED_KINDS)}")
        if not self.license_spdx:
            problems.append("license_spdx is required")
        elif not any(
            self.license_spdx.startswith(ok) for ok in ALLOWED_LICENSES
        ):
            problems.append(f"license_spdx {self.license_spdx!r} is not on the default allow-list")
        for prefix in REJECTED_LICENSE_PREFIXES:
            if self.license_spdx.upper().startswith(prefix.upper()):
                problems.append(f"license {self.license_spdx!r} is rejected for the default release")
        if not self.license_url.lower().startswith("https://"):
            problems.append("license_url must be https")
        if not self.source_url.lower().startswith("https://"):
            problems.append("source_url must be https")
        if not REVISION_RE.match(self.revision.lower()):
            problems.append(
                "revision must be a pinned 40-character commit SHA "
                f"(got {self.revision!r}); branches such as 'main' are not reproducible"
            )
        if not self.files:
            problems.append("at least one file entry is required")
        for entry in self.files:
            problems.extend(entry.validate())
            if self.revision.lower() not in entry.url.lower():
                problems.append(
                    f"{entry.name}: url must reference the pinned revision {self.revision[:8]}"
                )
        if self.approved and not self.reviewed_by:
            problems.append("approved=true requires reviewed_by")
        if self.approved and not self.reviewed_at:
            problems.append("approved=true requires reviewed_at")
        return problems


def _geometry(raw: Any) -> Geometry | None:
    if not raw:
        return None
    return Geometry(
        n_layers=int(raw["n_layers"]),
        n_kv_heads=int(raw["n_kv_heads"]),
        head_dim=int(raw["head_dim"]),
        n_params=int(raw["n_params"]) if raw.get("n_params") else None,
    )


def parse_manifest(raw: dict[str, Any]) -> ModelManifest:
    try:
        files = [
            ManifestFile(
                name=entry["name"],
                url=entry["url"],
                sha256=str(entry["sha256"]).lower(),
                size_bytes=entry.get("size_bytes"),
            )
            for entry in raw.get("files", [])
        ]
        return ModelManifest(
            id=raw["id"],
            kind=raw.get("kind", "model"),
            name=raw["name"],
            publisher=raw["publisher"],
            source_url=raw["source_url"],
            revision=str(raw["revision"]),
            license_spdx=raw["license_spdx"],
            license_url=raw["license_url"],
            files=files,
            geometry=_geometry(raw.get("geometry")),
            chat_template=raw.get("chat_template"),
            quantisation=raw.get("quantisation"),
            upstream_notice_required=bool(raw.get("upstream_notice_required", True)),
            redistribution=raw.get("redistribution", "permitted_subject_to_license"),
            commercial_use=raw.get("commercial_use", "permitted_subject_to_license"),
            modification=raw.get("modification", "permitted_subject_to_license"),
            components=list(raw.get("components") or []),
            approved=bool(raw.get("approved", False)),
            reviewed_by=raw.get("reviewed_by"),
            reviewed_at=raw.get("reviewed_at"),
            notes=raw.get("notes"),
        )
    except KeyError as exc:
        raise ManifestError(f"manifest is missing required field {exc.args[0]!r}") from exc


def load_manifest_file(path: Path) -> ModelManifest:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ManifestError(f"{path}: invalid YAML: {exc}") from exc
    if not isinstance(raw, dict):
        raise ManifestError(f"{path}: manifest must be a mapping")
    manifest = parse_manifest(raw)
    problems = manifest.validate()
    if problems:
        raise ManifestError(f"{path}: " + "; ".join(problems))
    return manifest


def load_manifests(directory: Path) -> list[ModelManifest]:
    """Load every ``*.yaml``/``*.yml`` manifest in a directory tree."""
    manifests: list[ModelManifest] = []
    seen: dict[str, Path] = {}
    for pattern in ("*.yaml", "*.yml"):
        for path in sorted(directory.rglob(pattern)):
            manifest = load_manifest_file(path)
            if manifest.id in seen:
                raise ManifestError(
                    f"duplicate manifest id {manifest.id!r} in {path} and {seen[manifest.id]}"
                )
            seen[manifest.id] = path
            manifests.append(manifest)
    return manifests


@dataclass
class LicenseEntry:
    """One row of ``licenses/manifest.yaml``."""

    id: str
    kind: str
    name: str
    publisher: str
    source_url: str
    revision: str
    license_spdx: str
    license_url: str
    sha256: str | None = None
    redistribution: str = "unknown"
    commercial_use: str = "unknown"
    modification: str = "unknown"
    upstream_notice_required: bool = True
    components: list[str] = field(default_factory=list)
    approved: bool = False
    reviewed_by: str | None = None
    reviewed_at: str | None = None
    notes: str | None = None

    def validate(self) -> list[str]:
        problems = []
        if self.revision and not REVISION_RE.match(self.revision.lower()):
            problems.append("revision must be a pinned 40-character commit SHA")
        if self.sha256 and not SHA256_RE.match(self.sha256.lower()):
            problems.append("sha256 must be 64 hex characters")
        if not any(self.license_spdx.startswith(ok) for ok in ALLOWED_LICENSES) and self.approved:
            problems.append(f"{self.id}: approved entry uses non-allow-listed licence {self.license_spdx}")
        if self.approved and not (self.reviewed_by and self.reviewed_at):
            problems.append(f"{self.id}: approved entry needs reviewed_by and reviewed_at")
        if self.approved and not self.sha256:
            problems.append(f"{self.id}: approved entry needs a recorded sha256")
        return problems


def load_license_manifest(path: Path) -> list[LicenseEntry]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or "assets" not in raw:
        raise ManifestError(f"{path}: licence manifest must contain an 'assets' list")
    entries: list[LicenseEntry] = []
    problems: list[str] = []
    for item in raw["assets"]:
        entry = LicenseEntry(
            id=item["id"],
            kind=item.get("kind", "model"),
            name=item.get("name", item["id"]),
            publisher=item.get("publisher", ""),
            source_url=item.get("source_url", ""),
            revision=str(item.get("revision", "")),
            license_spdx=item.get("license_spdx", "unknown"),
            license_url=item.get("license_url", ""),
            sha256=item.get("sha256"),
            redistribution=item.get("redistribution", "unknown"),
            commercial_use=item.get("commercial_use", "unknown"),
            modification=item.get("modification", "unknown"),
            upstream_notice_required=bool(item.get("upstream_notice_required", True)),
            components=list(item.get("components") or []),
            approved=bool(item.get("approved", False)),
            reviewed_by=item.get("reviewed_by"),
            reviewed_at=item.get("reviewed_at"),
            notes=item.get("notes"),
        )
        problems.extend(entry.validate())
        entries.append(entry)
    if problems:
        raise ManifestError(f"{path}: " + "; ".join(problems))
    return entries


def blocking_manifests(manifests: Iterable[ModelManifest]) -> list[ModelManifest]:
    """Manifests that must not be installed without an explicit override."""
    return [m for m in manifests if not m.approved]
