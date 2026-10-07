from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

from matias_context_mcp.profile import (
    GatewayProfile,
    V01_PROFILE,
)

PROJECT_AGENDA_FIXTURES = {
    "accounting-family": {
        "title": "Accounting + Family Strategy",
        "posture": "CONVERGE",
        "front_ids": ["fr_0036", "fr_0064", "fr_0147"],
        "last_material_refresh": "2026-09-17",
        "review_after_days": 30,
        "review_due_on": "2026-10-17",
        "declared_freshness": "CURRENT",
    },
    "base-de-datos-2c-2026": {
        "title": "Base de Datos 2C 2026",
        "posture": "DELIVER",
        "front_ids": ["fr_0148", "fr_0145", "fr_0038"],
        "last_material_refresh": "2026-09-17",
        "review_after_days": 7,
        "review_due_on": "2026-09-24",
        "declared_freshness": "CURRENT",
    },
    "fcv-research": {
        "title": "FCV Research",
        "posture": "WAITING_EXTERNAL",
        "front_ids": ["fr_0046", "fr_0047", "fr_0140", "fr_0141"],
        "last_material_refresh": "2026-09-17",
        "review_after_days": 30,
        "review_due_on": "2026-10-17",
        "declared_freshness": "CURRENT",
    },
    "job-search": {
        "title": "Job Search",
        "posture": "HARVEST",
        "front_ids": ["fr_0034"],
        "last_material_refresh": "2026-09-17",
        "review_after_days": 14,
        "review_due_on": "2026-10-01",
        "declared_freshness": "CURRENT",
    },
    "lcd-institutional-surfaces": {
        "title": "LCD Institutional Surfaces",
        "posture": "HARVEST",
        "front_ids": ["fr_0040", "fr_0041", "fr_0044", "fr_0144"],
        "last_material_refresh": "2026-09-17",
        "review_after_days": 30,
        "review_due_on": "2026-10-17",
        "declared_freshness": "CURRENT",
    },
    "media-monitor": {
        "title": "Media Monitor",
        "posture": "REPAIR",
        "front_ids": ["fr_0023", "fr_0024", "fr_0025", "fr_0026"],
        "last_material_refresh": "2026-09-17",
        "review_after_days": 14,
        "review_due_on": "2026-10-01",
        "declared_freshness": "CURRENT",
    },
    "poverty-ecosystem": {
        "title": "Argentina Poverty Ecosystem",
        "posture": "CONVERGE",
        "front_ids": [
            "fr_0087",
            "fr_0088",
            "fr_0090",
            "fr_0091",
            "fr_0092",
            "fr_0093",
            "fr_0094",
            "fr_0095",
            "fr_0099",
        ],
        "last_material_refresh": "2026-09-17",
        "review_after_days": 21,
        "review_due_on": "2026-10-08",
        "declared_freshness": "CURRENT",
    },
    "relationships-opportunities": {
        "title": "Relationships & Opportunities",
        "posture": "HARVEST",
        "front_ids": ["fr_0052", "fr_0058"],
        "last_material_refresh": "2026-09-17",
        "review_after_days": 21,
        "review_due_on": "2026-10-08",
        "declared_freshness": "CURRENT",
    },
}


def _write_projects_index(root: Path) -> None:
    agendas: dict[str, dict[str, object]] = {}
    for agenda_id, metadata in PROJECT_AGENDA_FIXTURES.items():
        path = root / "estate" / "agendas" / f"{agenda_id}.md"
        record = dict(metadata)
        record["source_path"] = (
            f"estate/agendas/{agenda_id}.md"
        )
        record["source_sha256"] = hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        agendas[agenda_id] = record

    index = root / "generated" / "project-agenda-index.json"
    index.write_text(
        json.dumps(
            {
                "contract": "context:project-agendas@1",
                "agenda_schema_version": 2,
                "agendas": agendas,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def provision_profile(
    tmp_path: Path,
    profile: GatewayProfile = V01_PROFILE,
) -> tuple[
    dict[str, str],
    dict[str, Path],
    list[dict[str, str]],
]:
    environment: dict[str, str] = {}
    roots: dict[str, Path] = {}
    mounts: list[dict[str, str]] = []

    for source in profile.sources:
        root = tmp_path / source.source_id
        root.mkdir()
        roots[source.source_id] = root
        environment[source.root_env] = str(root)
        mounts.append(
            {
                "source_id": source.source_id,
                "root_env": source.root_env,
            }
        )

        expected = source.identity
        (root / "SYSTEM.yaml").write_text(
            yaml.safe_dump(
                {
                    "schema_version": expected.schema_version,
                    "id": expected.declaration_id,
                    "repository": {
                        "id": expected.repository_id,
                        "github": expected.github,
                    },
                    "system": expected.system,
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )

        for document in source.documents:
            path = root / document.relative_path
            path.parent.mkdir(parents=True, exist_ok=True)

            if (
                document.codec
                == "context_routing_public_catalog"
            ):
                path.write_text(
                    json.dumps(
                        {
                            "schema_id": "context_catalog",
                            "schema_version": "1",
                            "generated_at": (
                                "2026-10-07T00:00:00Z"
                            ),
                            "count": 0,
                            "sources": [],
                        }
                    ),
                    encoding="utf-8",
                )
            elif document.document_id == "agenda-index":
                path.write_text(
                    json.dumps(
                        {
                            "contract": (
                                "context:project-agendas@1"
                            ),
                            "agenda_schema_version": 2,
                            "agendas": {},
                        }
                    )
                    + "\n",
                    encoding="utf-8",
                )
            elif document.media_type == "application/json":
                path.write_text(
                    "{}\n",
                    encoding="utf-8",
                )
            else:
                path.write_text(
                    f"# Fixture: {document.document_id}\n",
                    encoding="utf-8",
                )

        if source.source_id == "projects":
            _write_projects_index(root)

    return environment, roots, mounts
