"""Filesystem layout for local, per-user data.

Nothing here touches the network, the registry, or another user's profile.
Resolution order:

1. ``HCS_THERAPY_HOME`` environment variable (tests, portable installs, USB).
2. ``%LOCALAPPDATA%\\HCS\\TherapyStudio`` on Windows.
3. ``$XDG_DATA_HOME/hcs-therapy-studio`` or ``~/.local/share/hcs-therapy-studio``.

The root is created lazily with ``ensure()`` so that read-only commands such as
``doctor`` still work on a fresh machine without writing anything.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ENV_HOME = "HCS_THERAPY_HOME"


def default_home() -> Path:
    override = os.environ.get(ENV_HOME)
    if override:
        return Path(override).expanduser().resolve()
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")
        return Path(base) / "HCS" / "TherapyStudio"
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg) if xdg else (Path.home() / ".local" / "share")
    return base / "hcs-therapy-studio"


@dataclass(frozen=True)
class Paths:
    """Every writable location the application may use."""

    root: Path

    @property
    def models(self) -> Path:
        return self.root / "models"

    @property
    def models_downloads(self) -> Path:
        """Partial download files live here until a checksum passes."""
        return self.models / ".downloads"

    @property
    def adapters(self) -> Path:
        return self.root / "adapters"

    @property
    def checkpoints(self) -> Path:
        return self.root / "checkpoints"

    @property
    def runs(self) -> Path:
        return self.root / "runs"

    @property
    def db_path(self) -> Path:
        return self.root / "studio.sqlite"

    @property
    def logs(self) -> Path:
        return self.root / "logs"

    @property
    def cache(self) -> Path:
        return self.root / "cache"

    @property
    def reports(self) -> Path:
        return self.root / "reports"

    @property
    def runtime(self) -> Path:
        return self.root / "runtime"

    @property
    def exports(self) -> Path:
        return self.root / "exports"

    def ensure(self) -> Paths:
        for path in (
            self.root,
            self.models,
            self.models_downloads,
            self.adapters,
            self.checkpoints,
            self.runs,
            self.logs,
            self.cache,
            self.reports,
            self.runtime,
            self.exports,
        ):
            path.mkdir(parents=True, exist_ok=True)
        return self

    def as_dict(self) -> dict[str, str]:
        return {
            "root": str(self.root),
            "models": str(self.models),
            "adapters": str(self.adapters),
            "checkpoints": str(self.checkpoints),
            "runs": str(self.runs),
            "database": str(self.db_path),
            "logs": str(self.logs),
            "reports": str(self.reports),
            "runtime": str(self.runtime),
            "exports": str(self.exports),
        }


def paths(root: Path | str | None = None) -> Paths:
    return Paths(Path(root).expanduser().resolve() if root else default_home())


def repo_root() -> Path:
    """Locate the source checkout (used by dev scripts, never at runtime)."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").is_file():
            return parent
    return here.parents[2]
