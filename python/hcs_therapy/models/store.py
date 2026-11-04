"""Local model store: install, verify, list, remove.

The store is deliberately dumb about compute: it only ever answers "which
verified files exist on disk". Runtime decisions live in ``hcs_therapy.runtime``.
"""

from __future__ import annotations

import json
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path

from ..paths import Paths, repo_root
from .downloader import DownloadResult, ProgressFn, download_file, sha256_file
from .manifest import ModelManifest, load_manifests


class StoreError(RuntimeError):
    """Install/verify/removal failure with a user-facing message."""


@dataclass
class FileState:
    name: str
    path: str
    sha256: str
    size_bytes: int


@dataclass
class InstalledModel:
    id: str
    name: str
    files: list[FileState]
    installed_at: str
    license_spdx: str
    manifest_revision: str

    def primary_path(self) -> Path:
        # The largest file is the weight blob in every pack we ship.
        biggest = max(self.files, key=lambda f: f.size_bytes)
        return Path(biggest.path)


@dataclass
class VerificationResult:
    model_id: str
    ok: bool
    checked: int
    problems: list[str] = field(default_factory=list)


def manifest_directories(explicit: list[Path] | None = None) -> list[Path]:
    if explicit:
        return explicit
    dirs = [repo_root() / "models" / "manifests"]
    return [d for d in dirs if d.is_dir()]


class ModelStore:
    def __init__(self, paths: Paths, manifests: list[Path] | None = None) -> None:
        self.paths = paths
        self._manifest_dirs = manifest_directories(manifests)
        self._cache: list[ModelManifest] | None = None

    # -- manifests ---------------------------------------------------------
    def manifests(self) -> list[ModelManifest]:
        if self._cache is None:
            found: list[ModelManifest] = []
            for directory in self._manifest_dirs:
                found.extend(load_manifests(directory))
            self._cache = found
        return list(self._cache)

    def manifest(self, model_id: str) -> ModelManifest:
        for manifest in self.manifests():
            if manifest.id == model_id:
                return manifest
        raise StoreError(f"unknown model id {model_id!r}; run 'hcs-therapy models list'")

    # -- installed state ---------------------------------------------------
    @property
    def _state_path(self) -> Path:
        return self.paths.models / "installed.json"

    def _read_state(self) -> dict[str, dict]:
        if not self._state_path.is_file():
            return {}
        try:
            return json.loads(self._state_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            # A corrupt state file must not brick the app; re-derive from disk.
            return {}

    def _write_state(self, state: dict[str, dict]) -> None:
        self.paths.models.mkdir(parents=True, exist_ok=True)
        tmp = self._state_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(self._state_path)

    def installed(self) -> list[InstalledModel]:
        state = self._read_state()
        result: list[InstalledModel] = []
        for model_id, raw in state.items():
            result.append(
                InstalledModel(
                    id=model_id,
                    name=raw.get("name", model_id),
                    files=[FileState(**f) for f in raw.get("files", [])],
                    installed_at=raw.get("installed_at", ""),
                    license_spdx=raw.get("license_spdx", "unknown"),
                    manifest_revision=raw.get("manifest_revision", ""),
                )
            )
        return sorted(result, key=lambda m: m.id)

    def get_installed(self, model_id: str) -> InstalledModel | None:
        return next((m for m in self.installed() if m.id == model_id), None)

    def is_installed(self, model_id: str) -> bool:
        model = self.get_installed(model_id)
        return bool(model and all(Path(f.path).is_file() for f in model.files))

    # -- lifecycle ---------------------------------------------------------
    def install(
        self,
        model_id: str,
        *,
        accept_license: bool = False,
        allow_unapproved: bool = False,
        progress: ProgressFn | None = None,
    ) -> list[DownloadResult]:
        manifest = self.manifest(model_id)
        if not manifest.approved and not allow_unapproved:
            raise StoreError(
                f"{model_id} has not completed licence review (approved: false). "
                "Re-run with --allow-unapproved only after recording provenance in "
                "licenses/manifest.yaml."
            )
        if not accept_license:
            raise StoreError(
                f"installing {model_id} requires accepting {manifest.license_spdx}. "
                "Pass --accept-license after reading the licence at "
                f"{manifest.license_url}."
            )

        target_dir = self.paths.models / model_id
        target_dir.mkdir(parents=True, exist_ok=True)
        results: list[DownloadResult] = []
        for entry in manifest.files:
            destination = target_dir / entry.name
            results.append(
                download_file(
                    entry.url,
                    destination,
                    expected_sha256=entry.sha256,
                    expected_size=entry.size_bytes,
                    progress=progress,
                )
            )

        state = self._read_state()
        state[model_id] = {
            "name": manifest.name,
            "installed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "license_spdx": manifest.license_spdx,
            "manifest_revision": manifest.revision,
            "files": [
                {
                    "name": entry.name,
                    "path": str((target_dir / entry.name).resolve()),
                    "sha256": entry.sha256,
                    "size_bytes": entry.size_bytes
                    or (target_dir / entry.name).stat().st_size,
                }
                for entry in manifest.files
            ],
        }
        self._write_state(state)
        return results

    def verify(self, model_id: str, *, deep: bool = True) -> VerificationResult:
        """Check every recorded file. ``deep`` re-hashes the bytes."""
        model = self.get_installed(model_id)
        if model is None:
            return VerificationResult(model_id, False, 0, ["model is not installed"])
        problems: list[str] = []
        for entry in model.files:
            path = Path(entry.path)
            if not path.is_file():
                problems.append(f"{entry.name}: missing at {path}")
                continue
            actual_size = path.stat().st_size
            if actual_size != entry.size_bytes:
                problems.append(
                    f"{entry.name}: size {actual_size} != recorded {entry.size_bytes}"
                )
                continue
            if deep:
                digest = sha256_file(path)
                if digest != entry.sha256:
                    problems.append(f"{entry.name}: sha256 mismatch")
        return VerificationResult(model_id, not problems, len(model.files), problems)

    def remove(self, model_id: str, *, delete_files: bool = True) -> None:
        model = self.get_installed(model_id)
        if model is None:
            raise StoreError(f"{model_id} is not installed")
        if delete_files:
            target_dir = self.paths.models / model_id
            if target_dir.exists():
                shutil.rmtree(target_dir)
        state = self._read_state()
        state.pop(model_id, None)
        self._write_state(state)

    def primary_path(self, model_id: str) -> Path:
        model = self.get_installed(model_id)
        if model is None:
            raise StoreError(f"{model_id} is not installed")
        return model.primary_path()

    def disk_usage(self) -> dict[str, int]:
        total = 0
        for model in self.installed():
            total += sum(f.size_bytes for f in model.files)
        return {"models_bytes": total, "models_count": len(self.installed())}
