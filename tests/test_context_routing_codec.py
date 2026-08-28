from __future__ import annotations

from matias_context_mcp.normalizer import _project_context_catalog


URI = "matias-context://source/context-routing/document/published-source-catalog"


def test_current_public_context_source_schema_is_accepted() -> None:
    payload = {
        "schema_id": "context_catalog",
        "schema_version": "1",
        "sources": [
            {
                "schema_id": "context_source",
                "schema_version": "1",
                "source_id": "PUBLIC001",
                "display_name": "Public Metadata",
                "slug": "public-metadata",
                "page_url": "/context-routing/sources/public-metadata",
                "publication_kind": "metadata_only",
                "agent_ready": "yes",
                "generated_at": "2026-08-28T00:00:00+00:00",
            }
        ],
    }

    projected = _project_context_catalog(payload, uri=URI)

    assert projected == {
        "schema_version": "context-routing.public-source-catalog.v0.1",
        "count": 1,
        "sources": [
            {
                "source_id": "PUBLIC001",
                "source_name": "Public Metadata",
                "publish_mode": "metadata_only",
                "published_slug": "public-metadata",
                "is_agent_ready": "yes",
                "page_url": "/context-routing/sources/public-metadata",
            }
        ],
    }


def test_legacy_control_plane_catalog_keeps_gateway_side_filtering() -> None:
    payload = {
        "sources": [
            {
                "source_id": "PUBLIC001",
                "source_name": "Public Metadata",
                "publish_mode": "metadata_only",
                "publish_status": "published",
                "published_slug": "public-metadata",
                "exposure_level": "public",
                "is_agent_ready": "yes",
            },
            {
                "source_id": "HIDDEN001",
                "source_name": "Hidden",
                "publish_mode": "metadata_only",
                "publish_status": "hidden",
                "published_slug": "hidden",
                "exposure_level": "public",
                "is_agent_ready": "yes",
            },
            {
                "source_id": "SENSITIVE001",
                "source_name": "Sensitive",
                "publish_mode": "metadata_only",
                "publish_status": "published",
                "published_slug": "sensitive",
                "exposure_level": "sensitive",
                "is_agent_ready": "yes",
            },
        ]
    }

    projected = _project_context_catalog(payload, uri=URI)

    assert projected["count"] == 1
    assert [item["source_id"] for item in projected["sources"]] == ["PUBLIC001"]
