from __future__ import annotations

import json
from pathlib import Path

from matias_context_mcp.kernel import ResourceKernel
from matias_context_mcp.models import SourceSpec
from matias_context_mcp.profile import (
    FROZEN_PROFILE,
    HARD_MAX_BYTES,
    SUPPORTED_EXTENSIONS,
)
from matias_context_mcp.registry import SourceRegistry


def _registry(
    tmp_path: Path,
) -> SourceRegistry:
    sources: list[SourceSpec] = []

    for profile_source in FROZEN_PROFILE:
        root = tmp_path / profile_source.source_id
        root.mkdir()

        sources.append(
            SourceSpec(
                source_id=profile_source.source_id,
                display_name=profile_source.display_name,
                role=profile_source.role,
                authority=profile_source.authority,
                root=root.resolve(),
                documents=profile_source.documents,
                maximum_bytes=HARD_MAX_BYTES,
                allowed_extensions=SUPPORTED_EXTENSIONS,
                manifest_profile=(
                    profile_source.manifest_profile
                ),
            )
        )

    return SourceRegistry(sources)


def test_catalog_contains_four_sources_without_paths(
    tmp_path: Path,
) -> None:
    kernel = ResourceKernel(_registry(tmp_path))

    envelope = kernel.read_envelope(
        "matias-context://catalog/sources"
    )

    assert envelope["resource"]["family"] == (
        "source_catalog"
    )
    assert envelope["data"]["count"] == 4

    serialized = json.dumps(envelope)

    assert str(tmp_path) not in serialized
    assert "canonical_path" not in serialized


def test_source_descriptor_exposes_logical_documents(
    tmp_path: Path,
) -> None:
    kernel = ResourceKernel(_registry(tmp_path))

    envelope = kernel.read_envelope(
        "matias-context://source/kb-contracts"
    )

    assert envelope["resource"]["family"] == (
        "source_descriptor"
    )
    assert envelope["data"]["source_id"] == (
        "kb-contracts"
    )
    assert envelope["data"]["authority"] == (
        "authoritative"
    )
    assert envelope["data"]["available_documents"] == [
        {
            "document_id": "manual-overview",
            "content_media_type": "text/markdown",
        }
    ]

    assert str(tmp_path) not in json.dumps(envelope)
