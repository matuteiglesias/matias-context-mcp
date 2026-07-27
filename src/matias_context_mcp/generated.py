"""Generated catalog and source-descriptor resources."""

from __future__ import annotations

from typing import Any

from .profile import CONFIG_VERSION, PROFILE_ID
from .registry import SourceRegistry


def build_source_catalog(
    registry: SourceRegistry,
    *,
    uri: str,
) -> dict[str, Any]:
    sources = [
        _catalog_source(source)
        for source in registry.list_sources()
    ]

    return {
        "contract_version": CONFIG_VERSION,
        "resource": {
            "uri": uri,
            "family": "source_catalog",
            "read_only": True,
            "provenance": {
                "kind": "generated",
                "profile_id": PROFILE_ID,
            },
        },
        "data": {
            "count": len(sources),
            "sources": sources,
        },
    }


def build_source_descriptor(
    registry: SourceRegistry,
    *,
    source_id: str,
    uri: str,
) -> dict[str, Any]:
    source = registry.get_source(
        source_id,
        resource_uri=uri,
    )

    manifest_summary: dict[str, Any] | None = None

    if source.manifest_profile is not None:
        manifest_summary = {
            "producer_id":
                source.manifest_profile.producer_id,
            "content_media_type":
                source.manifest_profile.media_type,
        }

    return {
        "contract_version": CONFIG_VERSION,
        "resource": {
            "uri": uri,
            "family": "source_descriptor",
            "source_id": source.source_id,
            "authority": source.authority,
            "read_only": True,
            "provenance": {
                "kind": "generated",
                "profile_id": PROFILE_ID,
            },
        },
        "data": {
            "source_id": source.source_id,
            "display_name": source.display_name,
            "role": source.role,
            "authority": source.authority,
            "read_only": True,
            "available_documents": [
                {
                    "document_id": document.document_id,
                    "content_media_type":
                        document.media_type,
                }
                for document in source.documents
            ],
            "manifest_profile": manifest_summary,
        },
    }


def _catalog_source(source: Any) -> dict[str, Any]:
    manifest_producer = None

    if source.manifest_profile is not None:
        manifest_producer = (
            source.manifest_profile.producer_id
        )

    return {
        "source_id": source.source_id,
        "display_name": source.display_name,
        "role": source.role,
        "authority": source.authority,
        "read_only": True,
        "available_documents": [
            document.document_id
            for document in source.documents
        ],
        "manifest_producer": manifest_producer,
    }
