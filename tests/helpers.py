from __future__ import annotations

import json
from pathlib import Path

import yaml

from matias_context_mcp.profile import FROZEN_PROFILE


def provision_profile(
    tmp_path: Path,
) -> tuple[dict[str, str], dict[str, Path], list[dict[str, str]]]:
    environment: dict[str, str] = {}
    roots: dict[str, Path] = {}
    mounts: list[dict[str, str]] = []

    for source in FROZEN_PROFILE:
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

            if document.codec == "context_routing_public_catalog":
                path.write_text(
                    json.dumps(
                        {
                            "schema_id": "context_catalog",
                            "schema_version": "1",
                            "generated_at": "2026-10-07T00:00:00Z",
                            "count": 0,
                            "sources": [],
                        }
                    ),
                    encoding="utf-8",
                )
            elif document.media_type == "application/json":
                path.write_text("{}\n", encoding="utf-8")
            else:
                path.write_text(
                    f"# Fixture: {document.document_id}\n",
                    encoding="utf-8",
                )

    return environment, roots, mounts
