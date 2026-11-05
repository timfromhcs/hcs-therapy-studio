"""The TypeScript SDK must build, typecheck, pack, and stay browser-safe.

The package is the last piece of the M10 packaging contract. A package that only
"exists in the folder" is not a package: it has to compile with declarations, pack
to a tarball with the right files, and not smuggle a Node built-in into a
browser-safe API.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SDK = ROOT / "packages" / "sdk-ts"
NPM = shutil.which("npm.cmd") or shutil.which("npm")


def _run(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
    )


pytestmark = pytest.mark.skipif(NPM is None, reason="npm is not on PATH")


def _tsc_present() -> bool:
    return any((SDK / "node_modules" / ".bin" / name).exists() for name in ("tsc", "tsc.cmd"))


@pytest.fixture(scope="module", autouse=True)
def _installed_toolchain() -> None:
    """Install the dev dependency in a fresh checkout.

    The first CI runs failed with "'tsc' is not recognized", because the test
    assumed the local `node_modules` that only exists after someone ran
    `npm install` here. A test that passes only on the machine that wrote it is
    not a test, so the install is part of the fixture and the failure message
    says what the directory actually contains.
    """
    if _tsc_present():
        return
    result = _run(NPM, "ci", "--no-audit", "--no-fund", cwd=SDK)
    if _tsc_present():
        return
    modules = SDK / "node_modules"
    listing = sorted(p.name for p in modules.iterdir())[:30] if modules.is_dir() else []
    bin_dir = modules / ".bin"
    bin_listing = sorted(p.name for p in bin_dir.iterdir())[:30] if bin_dir.is_dir() else []
    raise AssertionError(
        f"npm ci returned {result.returncode} and still produced no tsc\n"
        f"node_modules={listing}\n"
        f".bin={bin_listing}\n"
        f"stdout={result.stdout[-800:]}\n"
        f"stderr={result.stderr[-800:]}"
    )


def test_package_manifest_is_a_publishable_esm_package() -> None:
    manifest = json.loads((SDK / "package.json").read_text(encoding="utf-8"))
    assert manifest["name"] == "@hcsmedia/therapy-sdk"
    assert manifest["license"] == "Apache-2.0"
    assert manifest["type"] == "module"
    assert manifest["exports"]["."]["types"] == "./dist/index.d.ts"
    assert manifest["exports"]["."]["import"] == "./dist/index.js"
    assert manifest["files"] == ["dist", "README.md"]
    assert manifest.get("private") is False
    # No runtime dependencies: a wire-format package that pulls a dependency tree
    # into every consumer is a supply-chain surface for nothing.
    assert "dependencies" not in manifest


def test_typescript_build_emits_declarations() -> None:
    result = _run(NPM, "run", "build", cwd=SDK)
    assert result.returncode == 0, result.stderr[-2000:]
    for name in ("index.js", "index.d.ts", "client.js", "client.d.ts", "types.d.ts"):
        assert (SDK / "dist" / name).is_file(), name


def test_the_source_imports_no_node_builtin() -> None:
    """The package claims to be browser-safe; that claim has to be checkable."""
    forbidden = ('"node:', "'node:", "require(", "process.", "Buffer.")
    for path in (SDK / "src").glob("*.ts"):
        body = path.read_text(encoding="utf-8")
        for needle in forbidden:
            assert needle not in body, f"{path.name} uses {needle!r}, which is not browser-safe"


def test_the_tarball_contains_dist_and_the_readme_only() -> None:
    result = _run(NPM, "pack", "--dry-run", "--json", cwd=SDK)
    assert result.returncode == 0, result.stderr[-2000:]
    start = result.stdout.find("[")
    payload = json.loads(result.stdout[start:])
    files = {entry["path"] for entry in payload[0]["files"]}
    assert "dist/index.js" in files
    assert "dist/index.d.ts" in files
    assert "README.md" in files
    assert "package.json" in files
    leaked = {name for name in files if name.startswith(("src/", "node_modules/", "dist/../"))}
    assert not leaked, f"the tarball leaks sources or dependencies: {leaked}"
    assert not any(name.endswith((".tgz", ".log")) for name in files)


def test_the_tarball_is_small_enough_to_be_a_client() -> None:
    result = _run(NPM, "pack", "--dry-run", "--json", cwd=SDK)
    start = result.stdout.find("[")
    payload = json.loads(result.stdout[start:])
    unpacked = payload[0]["unpackedSize"]
    assert unpacked < 300_000, f"unpacked size {unpacked} bytes is too large for a typed client"
    assert payload[0]["entryCount"] <= 20


def test_the_readme_documents_the_confirmation_contract() -> None:
    """A client whose writes silently need a flag will be misused."""
    body = (SDK / "README.md").read_text(encoding="utf-8")
    assert "confirmed: true" in body
    assert "vector_index" in body
    assert "HcsApiError" in body
