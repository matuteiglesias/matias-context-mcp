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
        "review_due_on": "2026-10-20",
    },
    "base-de-datos-2c-2026": {
        "review_due_on": "2026-10-20",
    },
    "fcv-research": {
        "review_due_on": "2026-10-20",
    },
    "job-search": {
        "review_due_on": "2026-10-20",
    },
    "lcd-institutional-surfaces": {
        "review_due_on": "2026-10-20",
    },
    "media-monitor": {
        "review_due_on": "2026-10-01",
    },
    "poverty-ecosystem": {
        "review_due_on": "2026-10-08",
    },
    "relationships-opportunities": {
        "review_due_on": "2026-10-20",
    },
}



def _write_projects_index(root: Path) -> None:
    agendas: dict[str, dict[str, object]] = {}
    for agenda_id, metadata in PROJECT_AGENDA_FIXTURES.items():
        path = root / "estate" / "agendas" / f"{agenda_id}.md"
        record = {
            "title": f"Fixture {agenda_id}",
            "posture": "FIXTURE",
            "front_ids": [],
            "last_material_refresh": "2026-10-01",
            "review_after_days": 7,
            "review_due_on": metadata["review_due_on"],
            "declared_freshness": "CURRENT",
            "source_path": f"estate/agendas/{agenda_id}.md",
            "source_sha256": hashlib.sha256(
                path.read_bytes()
            ).hexdigest(),
        }
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
