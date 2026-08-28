from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from matias_context_mcp.config import load_registry
from matias_context_mcp.kernel import ResourceKernel
from matias_context_mcp.profile import PROFILE_BY_SOURCE, PROFILE_ID


PRODUCER_COMMIT = "aa8ffbd5d3c90b4819b27ba6e039b30a21ef38a2"
GENERATED_AT = "2026-08-28T00:00:00+00:00"
RESOURCE_URI = (
    "matias-context://source/context-routing/"
    "document/published-source-catalog"
)


def _gateway_config(tmp_path: Path) -> Path:
    path = tmp_path / "gateway.json"
    path.write_text(
        json.dumps(
            {
                "config_version": "mcp-context-gateway.v0.1",
                "profile": PROFILE_ID,
                "sources": [
                    {
                        "source_id": source.source_id,
                        "root_env": source.root_env,
                    }
                    for source in PROFILE_BY_SOURCE.values()
                ],
            }
        ),
        encoding="utf-8",
    )
    return path.resolve()


def test_generated_context_routing_catalog_crosses_gateway_boundary(
    tmp_path: Path,
) -> None:
    producer_root_value = os.environ.get("CONTEXT_ROUTING_W3_ROOT")
    if not producer_root_value:
        pytest.skip("W3 producer checkout not mounted")

    producer_root = Path(producer_root_value).resolve(strict=True)
    catalog_path = producer_root / "static/context-data/sources.json"
    assert catalog_path.is_file()

    env: dict[str, str] = {}
    for source in PROFILE_BY_SOURCE.values():
        if source.source_id == "context-routing":
            root = producer_root
        else:
            root = tmp_path / source.source_id
            root.mkdir()
        env[source.root_env] = str(root)

    registry = load_registry(_gateway_config(tmp_path), environ=env)
    envelope = ResourceKernel(registry).read_envelope(RESOURCE_URI)

    expected_sha = hashlib.sha256(catalog_path.read_bytes()).hexdigest()
    payload = envelope["data"]["json"]

    assert envelope["contract_version"] == "mcp-context-gateway.v0.1"
    assert envelope["resource"]["uri"] == RESOURCE_URI
    assert envelope["resource"]["source_id"] == "context-routing"
    assert envelope["resource"]["logical_id"] == "published-source-catalog"
    assert envelope["resource"]["authority"] == "routing"
    assert envelope["resource"]["content_media_type"] == "application/json"
    assert envelope["resource"]["sha256"] == expected_sha
    assert envelope["resource"]["size_bytes"] == catalog_path.stat().st_size

    assert payload["schema_id"] == "context_catalog"
    assert payload["schema_version"] == "1"
    assert payload["generated_at"] == GENERATED_AT
    assert payload["count"] == 1
    assert [item["source_id"] for item in payload["sources"]] == ["PUBLIC001"]

    serialized = json.dumps(envelope)
    assert "INTERNAL_ORIGIN_SENTINEL" not in serialized
    assert "HIDDEN_SENTINEL" not in serialized
    assert "SENSITIVE_SENTINEL" not in serialized
    assert str(producer_root) not in serialized
