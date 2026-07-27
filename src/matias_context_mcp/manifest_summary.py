"""Small producer-neutral projection over validated manifests."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def build_manifest_summary(
    content: Any,
    *,
    producer_id: str,
    manifest_id: str,
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "producer_id": producer_id,
        "manifest_id": manifest_id,
    }

    if not isinstance(content, Mapping):
        return summary

    schema_version = (
        content.get("schema_version")
        or content.get("version")
    )

    if schema_version is not None:
        summary["schema_version"] = schema_version

    fields = (
        "producer",
        "run_id",
        "status",
        "started_at",
        "completed_at",
        "generated_at",
        "inputs",
        "outputs",
        "checksums",
    )

    for field in fields:
        if field in content:
            summary[field] = content[field]

    return summary
