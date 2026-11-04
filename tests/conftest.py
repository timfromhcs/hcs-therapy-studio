"""Shared fixtures. Every test is hermetic: its own data directory, no network."""

from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the app at a throwaway directory for every single test."""
    home = tmp_path / "hcs-home"
    monkeypatch.setenv("HCS_THERAPY_HOME", str(home))
    home.mkdir(parents=True, exist_ok=True)
    return home


@pytest.fixture
def paths(isolated_home: Path):
    from hcs_therapy.paths import paths as resolve

    return resolve()


@pytest.fixture
def repo_root() -> Path:
    from hcs_therapy.paths import repo_root as resolve

    return resolve()


def pytest_configure(config: pytest.Config) -> None:
    os.environ.setdefault("HCS_TESTING", "1")
