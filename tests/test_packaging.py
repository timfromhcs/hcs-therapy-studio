"""Declared dependencies must cover what the package actually imports.

Found by building the wheel and installing it into a clean venv: `numpy` was
imported by `numerics.sampling`, pulled in by `knowledge.py`, and declared nowhere.
The wheel installed cleanly and then `hcs-therapy kb index` died with
`ModuleNotFoundError: No module named 'numpy'`.

That is not a bug a unit test on the source tree can catch, because the dev venv
happens to have numpy. This test catches it statically, and the wheel check in
`scripts/verify/wheel_install.ps1` catches it for real.
"""

from __future__ import annotations

import ast
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "python" / "hcs_therapy"

# Modules that are allowed to be imported lazily and belong to an optional extra.
TRAINING_MODULES = {"torch", "transformers", "peft", "trl", "datasets", "accelerate", "safetensors"}

# Import name -> distribution name, where they differ.
IMPORT_TO_DISTRIBUTION = {
    "yaml": "pyyaml",
    "pil": "pillow",
    "cv2": "opencv-python",
    "sklearn": "scikit-learn",
    "bs4": "beautifulsoup4",
    "dotenv": "python-dotenv",
    "dateutil": "python-dateutil",
    "google": "protobuf",
}


def _dist(name: str) -> str:
    return IMPORT_TO_DISTRIBUTION.get(name.lower(), name.lower())


def _declared() -> dict[str, set[str]]:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = data["project"]
    core = {
        spec.split(">")[0].split("=")[0].split("<")[0].split("[")[0].strip().lower()
        for spec in project.get("dependencies", [])
    }
    extras: dict[str, set[str]] = {}
    for name, specs in project.get("optional-dependencies", {}).items():
        extras[name] = {
            spec.split(">")[0].split("=")[0].split("<")[0].split("[")[0].strip().lower()
            for spec in specs
        }
    return {"core": core, **extras}


def _imported() -> dict[str, set[str]]:
    """Top-level third-party module -> the files that import it."""
    stdlib = set(sys.stdlib_module_names)
    local = {path.stem for path in PACKAGE.rglob("*.py")}
    local |= {"hcs_therapy"}
    found: dict[str, set[str]] = {}
    for path in PACKAGE.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module.split(".")[0]]
            for name in names:
                if name in stdlib or name in local or name.startswith("_"):
                    continue
                found.setdefault(name, set()).add(str(path.relative_to(ROOT)))
    return found


def test_every_third_party_import_is_declared_somewhere() -> None:
    declared = _declared()
    allowed = set().union(*declared.values())
    imported = _imported()
    undeclared = sorted(name for name in imported if _dist(name) not in allowed)
    assert not undeclared, (
        "imported but declared in no dependency group: "
        + ", ".join(f"{name} (from {sorted(imported[name])[0]})" for name in undeclared)
    )


def test_the_core_runtime_does_not_need_a_training_extra() -> None:
    """A plain `pip install hcs-therapy-core` must not pull torch to start the CLI."""
    declared = _declared()
    imported = _imported()
    core_only = declared["core"]
    offenders = {
        name: files
        for name, files in imported.items()
        if _dist(name) not in core_only and name not in TRAINING_MODULES
    }
    assert not offenders, f"core import needs a non-core dependency: {offenders}"


def test_training_only_imports_stay_behind_the_extra() -> None:
    declared = _declared()
    imported = _imported()
    train_extra = declared.get("train", set())
    for name in TRAINING_MODULES & set(imported):
        assert name in train_extra, f"{name} is imported but missing from the [train] extra"


def test_numpy_is_declared_core_because_the_knowledge_base_needs_it() -> None:
    """The specific defect a clean-venv install found.

    ``knowledge.py`` imports ``numerics``, and ``numerics/__init__.py`` imports
    ``sampling``, which imports numpy at module level. That chain is why numpy must
    be a core dependency rather than a training extra.
    """
    assert "numpy" in _declared()["core"]
    imported = _imported()
    assert any("numerics" in path for path in imported["numpy"])
    knowledge = (PACKAGE / "knowledge.py").read_text(encoding="utf-8")
    assert "from .numerics.retrieval import" in knowledge
    init = (PACKAGE / "numerics" / "__init__.py").read_text(encoding="utf-8")
    assert "from .sampling import" in init


def test_pyproject_declares_the_entry_points_documented_in_the_readme() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    scripts = data["project"]["scripts"]
    assert "hcs-therapy" in scripts
    assert "hcs-therapy-mcp" in scripts
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "hcs-therapy serve" in readme
    assert "hcs-therapy kb" in readme


def test_the_wheel_builder_targets_the_package_directory() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    wheel = data["tool"]["hatch"]["build"]["targets"]["wheel"]
    assert wheel["packages"] == ["python/hcs_therapy"]
    assert (ROOT / "python" / "hcs_therapy" / "__init__.py").is_file()
