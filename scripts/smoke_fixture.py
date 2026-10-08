#!/usr/bin/env python3
"""Run the real MCP acceptance probe against bounded verified fixture mounts."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

from matias_context_mcp.profile import (
    GatewayProfile,
    V01_PROFILE,
    V01_PROFILE_ID,
    V02_PROFILE,
    V02_PROFILE_ID,
    V03_PROFILE,
    V03_PROFILE_ID,
)


def write_source_fixture(source, source_root: Path) -> None:
    source_root.mkdir(parents=True, exist_ok=True)
    identity = source.identity
    (source_root / "SYSTEM.yaml").write_text(
            yaml.safe_dump(
                {
                    "schema_version": identity.schema_version,
                    "id": identity.declaration_id,
                    "repository": {
                        "id": identity.repository_id,
                        "github": identity.github,
                    },
                    "system": identity.system,
                },
                sort_keys=False,
            ),
        encoding="utf-8",
    )

    for document in source.documents:
        path = source_root / document.relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            continue

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
        elif document.document_id == "agenda-index":
            path.write_text(
                json.dumps(
                    {
                        "contract": "context:project-agendas@1",
                        "agenda_schema_version": 2,
                        "agendas": {},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
        elif document.media_type == "application/json":
            path.write_text("{}\n", encoding="utf-8")
        else:
            path.write_text(
                f"# Smoke fixture: {document.document_id}\n",
                encoding="utf-8",
            )


def _write_sources(
    root: Path,
    profile: GatewayProfile,
) -> tuple[dict[str, str], list[dict[str, str]]]:
    environment: dict[str, str] = {}
    mounts: list[dict[str, str]] = []

    for source in profile.sources:
        source_root = root / source.source_id
        write_source_fixture(source, source_root)
        environment[source.root_env] = str(source_root)
        mounts.append(
            {
                "source_id": source.source_id,
                "root_env": source.root_env,
            }
        )

    inspect_id = "2026-10-07T120000Z"
    inspect_manifest = (
        root
        / "knowledge-inspect"
        / "artifacts"
        / "manifests"
        / f"{inspect_id}.manifest.json"
    )
    inspect_manifest.parent.mkdir(parents=True, exist_ok=True)
    inspect_manifest.write_text(
        json.dumps(
            {
                "run_id": inspect_id,
                "status": "success",
                "producer": {"id": "kb"},
            }
        ),
        encoding="utf-8",
    )

    selection_id = "selection-2026-10-07T120000Z"
    selection_root = (
        root
        / "kb-artifacts"
        / "artifacts"
        / "runs"
        / selection_id
    )
    selection_root.mkdir(parents=True, exist_ok=True)
    selected_body = (
        json.dumps(
            {
                "record_id": "fixture:selected:1",
                "source_kind": "chunk",
                "title": "Fixture selected evidence",
                "summary": "Governed fixture summary.",
                "annotations": {"source_id": "fixture-source", "key_points": ["One", "Two"]},
                "tags": ["fixture"],
                "timestamp": "2026-10-07T12:00:00+00:00",
                "provenance": {
                    "partition": "corpus:fixture/chunk:1",
                    "line_number": 1,
                    "text_sha256": "0" * 64,
                    "source_ref": "fixture:selected:1",
                },
                "selection_reasons": ["tag:fixture"],
                "artifact_family": None,
                "artifact_maturity": None,
            },
            sort_keys=True,
        )
        + "\n"
    )
    selected_path = selection_root / "selected.jsonl"
    selected_path.write_text(selected_body, encoding="utf-8")
    import hashlib
    selection_manifest = selection_root / "manifest.json"
    selection_manifest.write_text(
        json.dumps(
            {
                "selection_request": {"tags": ["fixture"]},
                "generated_at": "2026-10-07T12:00:00Z",
                "matched_partitions": [],
                "counts": {"selected": 1},
                "outputs": ["selected.jsonl", "selected.csv", "artifact.md", "manifest.json"],
                "output_checksums": {
                    "selected.jsonl": hashlib.sha256(selected_body.encode("utf-8")).hexdigest()
                },
            }
        ),
        encoding="utf-8",
    )

    environment["KNOWLEDGE_INSPECT_MANIFEST_ID"] = inspect_id
    environment["KB_ARTIFACTS_MANIFEST_ID"] = selection_id
    return environment, mounts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/mvp-evidence"),
    )
    parser.add_argument(
        "--profile",
        choices=(V01_PROFILE_ID, V02_PROFILE_ID, V03_PROFILE_ID),
        default=V01_PROFILE_ID,
    )
    args = parser.parse_args()

    profile = {
        V01_PROFILE_ID: V01_PROFILE,
        V02_PROFILE_ID: V02_PROFILE,
        V03_PROFILE_ID: V03_PROFILE,
    }[args.profile]
    repository = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="mctx-smoke-") as temp:
        root = Path(temp)
        source_environment, mounts = _write_sources(root, profile)
        config = root / "gateway.json"
        config.write_text(
            json.dumps(
                {
                    "config_version": profile.config_version,
                    "profile": profile.profile_id,
                    "sources": mounts,
                }
            ),
            encoding="utf-8",
        )

        environment = dict(os.environ)
        environment.update(source_environment)
        environment["MATIAS_CONTEXT_GATEWAY_CONFIG"] = str(config)
        environment["PYTHONPATH"] = str(repository / "src")

        result = subprocess.run(
            [
                sys.executable,
                str(repository / "scripts" / "probe_mcp.py"),
                "--output-dir",
                str(args.output_dir),
                "--expected-source-count",
                str(len(profile.sources)),
                *(["--expect-selected-evidence"] if profile.profile_id == V03_PROFILE_ID else []),
            ],
            cwd=repository,
            env=environment,
            check=False,
        )
        return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
