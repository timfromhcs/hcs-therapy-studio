"""Attribution and SBOM generation from the licence manifests.

These files are generated from data, never hand-written, so a shipped notice
cannot drift away from what is actually installed.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

from .models.manifest import LicenseEntry, ModelManifest, load_license_manifest, load_manifests

PRODUCT = "HCS Therapy Studio"
CREDIT = "Made with love by hcsmedia and timfromhcs"


@dataclass
class AttributionBundle:
    notice: str
    third_party: str
    model_attribution: str
    dataset_attribution: str
    sbom: dict


def _row(entry: LicenseEntry) -> str:
    return (
        f"| `{entry.id}` | {entry.name} | {entry.publisher} | {entry.license_spdx} | "
        f"`{entry.revision[:12] or 'unpinned'}` | {entry.source_url} |"
    )


def build_bundle(
    license_entries: list[LicenseEntry],
    models: list[ModelManifest],
    *,
    datasets: list[dict] | None = None,
) -> AttributionBundle:
    datasets = datasets or []
    generated = time.strftime("%Y-%m-%d", time.gmtime())

    notice = (
        f"{PRODUCT}\n"
        f"Copyright (c) 2026 hcsmedia and timfromhcs\n\n"
        "This product includes software and model weights developed by third parties.\\n"
        "See THIRD_PARTY_NOTICES.md and MODEL_ATTRIBUTION.md.\n\n"
        f"{CREDIT}\n"
        f"Notices generated {generated} from licenses/manifest.yaml\n"
    )

    header = (
        "# Third-party notices\n\n"
        f"Generated {generated} from `licenses/manifest.yaml`.\n"
        "Every component below is audited before it may be bundled. Entries with\n"
        "`approved: false` are shortlisted but **not** shipped.\n\n"
        "| id | name | publisher | licence | revision | source |\n"
        "|---|---|---|---|---|---|\n"
    )
    rows = "\n".join(
        _row(entry) + ("" if entry.approved else " *(not approved — not shipped)*")
        for entry in license_entries
    )
    unavailable = (
        "\n\n## Deliberately not used\n\n"
        "| id | reason |\n|---|---|\n"
        "| `esconv` | upstream is academic-research-only and CC BY-NC 4.0 |\n"
        "| `cbt-bench` | CC BY-NC 4.0: evaluation only where permitted, never bundled |\n"
        "| `pixart-sigma` | OpenRAIL++-M does not pass the strict permissive filter |\n"
        "| `janus-pro` | DeepSeek Model Licence has use-based conditions |\n"
        "| `sana-*` | depends on Gemma-2 text encoder with separate terms |\n"
        "| `qwen-image-edit` | 20B parameters, exceeds the target device budget |\n"
    )
    third_party = header + rows + unavailable

    model_lines = ["# Model attribution", "", f"Generated {generated}.", ""]
    if not models:
        model_lines.append("No model manifests are present in this checkout.")
    for manifest in models:
        model_lines.extend(
            [
                f"## {manifest.name}",
                "",
                f"- **Manifest id:** `{manifest.id}`",
                f"- **Kind:** {manifest.kind}",
                f"- **Upstream publisher:** {manifest.publisher}",
                f"- **Source:** {manifest.source_url}",
                f"- **Pinned revision:** `{manifest.revision}`",
                f"- **Licence:** {manifest.license_spdx} ({manifest.license_url})",
                f"- **Quantisation:** {manifest.quantisation or 'n/a'}",
                f"- **Redistribution:** {manifest.redistribution}",
                f"- **Commercial use:** {manifest.commercial_use}",
                f"- **Modification:** {manifest.modification}",
                f"- **Files:** {', '.join(f.name for f in manifest.files) or 'none'}",
                f"- **Licence review:** {'approved by ' + str(manifest.reviewed_by) + ' on ' + str(manifest.reviewed_at) if manifest.approved else 'NOT APPROVED — must not ship'}",
                "",
                "This project is not endorsed by or affiliated with the upstream "
                "publisher. The weights are used under their own licence.",
                "",
            ]
        )
        if manifest.components:
            model_lines.append(
                "- **Bundled components:** " + ", ".join(manifest.components)
            )
            model_lines.append("")
    model_attribution = "\n".join(model_lines)

    dataset_lines = ["# Dataset attribution", "", f"Generated {generated}.", ""]
    if not datasets:
        dataset_lines.append("No dataset manifests are present in this checkout.")
    for dataset in datasets:
        dataset_lines.extend(
            [
                f"## {dataset.get('name', dataset.get('id'))}",
                "",
                f"- **id:** `{dataset.get('id')}`",
                f"- **version:** {dataset.get('version')}",
                f"- **licence:** {dataset.get('license_spdx')}",
                f"- **source:** {dataset.get('source_url')}",
                f"- **records:** {dataset.get('records')}",
                f"- **privacy review:** {dataset.get('privacy_review')}",
                f"- **permitted use:** {dataset.get('permitted_use')}",
                f"- **prohibited use:** {', '.join(dataset.get('prohibited_use') or []) or 'n/a'}",
                "",
            ]
        )
    dataset_attribution = "\n".join(dataset_lines)

    sbom = {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": f"{PRODUCT} component manifest",
        "documentNamespace": f"https://hcsmedia.example/spdx/hcs-therapy-studio-{generated}",
        "creationInfo": {
            "created": f"{generated}T00:00:00Z",
            "creators": ["Tool: hcs-therapy licensing"],
        },
        "packages": [
            {
                "SPDXID": f"SPDXRef-Package-{index}",
                "name": entry.name,
                "versionInfo": entry.revision[:12] or "unpinned",
                "supplier": f"Organization: {entry.publisher}" if entry.publisher else "NOASSERTION",
                "downloadLocation": entry.source_url or "NOASSERTION",
                "licenseConcluded": entry.license_spdx,
                "licenseDeclared": entry.license_spdx,
                "filesAnalyzed": False,
                "externalRefs": (
                    [{"referenceCategory": "SECURITY", "referenceType": "checksum", "referenceLocator": entry.sha256}]
                    if entry.sha256
                    else []
                ),
            }
            for index, entry in enumerate(license_entries, start=1)
        ],
    }

    return AttributionBundle(
        notice=notice,
        third_party=third_party,
        model_attribution=model_attribution,
        dataset_attribution=dataset_attribution,
        sbom=sbom,
    )


def write_bundle(bundle: AttributionBundle, root: Path) -> list[Path]:
    written: list[Path] = []
    files = {
        "NOTICE": bundle.notice,
        "THIRD_PARTY_NOTICES.md": bundle.third_party,
        "MODEL_ATTRIBUTION.md": bundle.model_attribution,
        "DATASET_ATTRIBUTION.md": bundle.dataset_attribution,
        "SBOM.spdx.json": json.dumps(bundle.sbom, indent=2, ensure_ascii=False) + "\n",
    }
    for name, content in files.items():
        path = root / name
        path.write_text(content, encoding="utf-8")
        written.append(path)
    return written


def generate(root: Path) -> list[Path]:
    entries = load_license_manifest(root / "licenses" / "manifest.yaml")
    model_dir = root / "models" / "manifests"
    models = load_manifests(model_dir) if model_dir.is_dir() else []
    from .datasets import load_dataset_manifests

    dataset_dir = root / "datasets" / "manifests"
    datasets = []
    if dataset_dir.is_dir():
        datasets = [
            {
                "id": m.id,
                "name": m.name,
                "version": m.version,
                "license_spdx": m.license_spdx,
                "source_url": m.source_url,
                "records": m.records,
                "privacy_review": m.privacy_review,
                "permitted_use": m.permitted_use,
                "prohibited_use": m.prohibited_use,
            }
            for m in load_dataset_manifests(dataset_dir)
        ]
    return write_bundle(build_bundle(entries, models, datasets=datasets), root)
