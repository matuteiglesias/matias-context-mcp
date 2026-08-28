from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from matias_context_mcp.errors import MalformedJSONError
from matias_context_mcp.models import AuthorizedRead, RawResource
from matias_context_mcp.normalizer import normalize
from matias_context_mcp.profile import PROFILE_BY_SOURCE


URI = (
    "matias-context://source/context-routing/"
    "document/published-source-catalog"
)


def _raw(payload: object) -> RawResource:
    content = json.dumps(payload, sort_keys=True).encode("utf-8")
    return RawResource(
        authorized=AuthorizedRead(
            requested_uri=URI,
            resource_family="document",
            source_id="context-routing",
            logical_id="published-source-catalog",
            canonical_path=Path("/unused/context-catalog.json"),
            content_media_type="application/json",
            maximum_bytes=262_144,
            authority="routing",
            codec="context_routing_public_catalog",
        ),
        content=content,
        size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        modified_at=None,
    )


def _catalog() -> dict[str, object]:
    return {
        "schema_id": "context_catalog",
        "schema_version": "1",
        "generated_at": "2026-07-28T00:00:00+00:00",
        "count": 1,
        "sources": [
            {
                "schema_id": "context_source",
                "schema_version": "1",
                "source_id": "SRC002",
                "display_name": "Capture Manual",
                "slug": "capture-manual",
                "page_url": "/context-routing/sources/capture-manual",
                "publication_kind": "direct_link",
                "agent_ready": "yes",
                "generated_at": "2026-07-28T00:00:00+00:00",
                "public_origin_url": "https://example.test/capture",
                "future_public_field": "not-yet-approved-by-gateway",
            }
        ],
    }


def test_profile_pins_versioned_context_routing_catalog() -> None:
    source = PROFILE_BY_SOURCE["context-routing"]
    document = source.documents[1]

    assert document.document_id == "published-source-catalog"
    assert document.relative_path == "static/context-data/v1/sources.json"


def test_public_v1_catalog_is_preserved_without_private_refiltering() -> None:
    document = normalize(_raw(_catalog()))
    catalog = document.data["json"]

    assert catalog["schema_id"] == "context_catalog"
    assert catalog["schema_version"] == "1"
    assert catalog["count"] == 1
    assert catalog["sources"][0]["source_id"] == "SRC002"
    assert catalog["sources"][0]["display_name"] == "Capture Manual"
    assert catalog["sources"][0]["public_origin_url"] == "https://example.test/capture"
    assert "future_public_field" not in catalog["sources"][0]
    assert "publish_status" not in catalog["sources"][0]
    assert "exposure_level" not in catalog["sources"][0]


def test_old_private_registry_shape_is_not_mistaken_for_public_v1() -> None:
    old_shape = {
        "count": 1,
        "sources": [
            {
                "source_id": "SRC002",
                "source_name": "Capture Manual",
                "publish_status": "published",
                "exposure_level": "public",
            }
        ],
    }

    with pytest.raises(MalformedJSONError, match="unsupported contract identity"):
        normalize(_raw(old_shape))


def test_catalog_count_must_match_source_list() -> None:
    payload = _catalog()
    payload["count"] = 2

    with pytest.raises(MalformedJSONError, match="count does not match"):
        normalize(_raw(payload))
