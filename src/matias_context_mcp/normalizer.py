"""Decode, validate, and normalize resource content."""

from __future__ import annotations

import json
from pathlib import PurePosixPath
from typing import Any

from .errors import (
    MalformedJSONError,
    MalformedManifestError,
    UnsupportedFormatError,
)
from .models import RawResource, ResourceDocument

_CONTEXT_ALLOWED_FIELDS = (
    "source_id",
    "source_name",
    "publish_mode",
    "publish_status",
    "published_slug",
    "exposure_level",
    "is_agent_ready",
    "page_url",
    "artifact_url",
    "snapshot_url",
)


def normalize(
    raw: RawResource,
) -> ResourceDocument:
    authorized = raw.authorized

    if b"\x00" in raw.content:
        raise UnsupportedFormatError(
            "Binary resource bodies are not supported.",
            resource_uri=authorized.requested_uri,
        )

    try:
        text = raw.content.decode(
            "utf-8",
            errors="strict",
        )
    except UnicodeDecodeError as exc:
        raise UnsupportedFormatError(
            "Resource is not valid UTF-8 text.",
            resource_uri=authorized.requested_uri,
        ) from exc

    if authorized.content_media_type == "text/markdown":
        data = {"text": text}

    elif authorized.content_media_type == "application/json":
        parsed = _parse_json(
            text,
            uri=authorized.requested_uri,
        )

        data = {
            "json": _apply_codec(
                parsed,
                raw,
            )
        }

    else:
        raise UnsupportedFormatError(
            "Resource media type is not supported.",
            resource_uri=authorized.requested_uri,
        )

    return ResourceDocument(
        uri=authorized.requested_uri,
        family=authorized.resource_family,
        source_id=authorized.source_id,
        logical_id=authorized.logical_id,
        authority=authorized.authority,
        content_media_type=authorized.content_media_type,
        size_bytes=raw.size_bytes,
        sha256=raw.sha256,
        modified_at=raw.modified_at,
        data=data,
        producer_id=authorized.producer_id,
    )


def _parse_json(
    text: str,
    *,
    uri: str,
) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise MalformedJSONError(
            "Resource is not valid JSON.",
            resource_uri=uri,
        ) from exc


def _apply_codec(
    parsed: Any,
    raw: RawResource,
) -> Any:
    codec = raw.authorized.codec

    if codec == "json":
        return parsed

    if codec == "context_routing_public_catalog":
        return _project_context_catalog(
            parsed,
            uri=raw.authorized.requested_uri,
        )

    if codec == "knowledge_inspect_manifest":
        _validate_knowledge_inspect_manifest(
            parsed,
            raw,
        )
        return parsed

    if codec == "kb_artifacts_manifest":
        _validate_kb_artifacts_manifest(
            parsed,
            raw,
        )
        return parsed

    raise UnsupportedFormatError(
        "Configured resource codec is not supported.",
        resource_uri=raw.authorized.requested_uri,
    )


def _project_context_catalog(
    parsed: Any,
    *,
    uri: str,
) -> dict[str, Any]:
    entries = (
        parsed.get("sources")
        if isinstance(parsed, dict)
        else parsed
    )

    if not isinstance(entries, list):
        raise MalformedJSONError(
            "Context Routing catalog must "
            "contain a source list.",
            resource_uri=uri,
        )

    projected: list[dict[str, Any]] = []

    for entry in entries:
        if not isinstance(entry, dict):
            continue

        if entry.get("publish_status") not in {
            "ready",
            "published",
        }:
            continue

        if entry.get("exposure_level") not in {
            "public",
            "private_safe",
        }:
            continue

        projected.append(
            {
                key: entry[key]
                for key in _CONTEXT_ALLOWED_FIELDS
                if key in entry
            }
        )

    return {
        "schema_version":
            "context-routing.public-source-catalog.v0.1",
        "count": len(projected),
        "sources": projected,
    }


def _validate_knowledge_inspect_manifest(
    parsed: Any,
    raw: RawResource,
) -> None:
    uri = raw.authorized.requested_uri

    if not isinstance(parsed, dict):
        raise MalformedManifestError(
            "Manifest must be a JSON object.",
            resource_uri=uri,
        )

    run_id = parsed.get("run_id")

    if run_id != raw.authorized.logical_id:
        raise MalformedManifestError(
            "Manifest run_id does not match "
            "the requested manifest ID.",
            resource_uri=uri,
        )

    if "status" not in parsed:
        raise MalformedManifestError(
            "Manifest status is missing.",
            resource_uri=uri,
        )

    if (
        "producer" in parsed
        and not _producer_matches(
            parsed["producer"],
            raw.authorized.manifest_producer_id,
        )
    ):
        raise MalformedManifestError(
            "Manifest producer identity is incompatible.",
            resource_uri=uri,
        )


def _validate_kb_artifacts_manifest(
    parsed: Any,
    raw: RawResource,
) -> None:
    uri = raw.authorized.requested_uri

    if not isinstance(parsed, dict):
        raise MalformedManifestError(
            "Manifest must be a JSON object.",
            resource_uri=uri,
        )

    required = {
        "selection_request",
        "generated_at",
        "matched_partitions",
        "counts",
        "outputs",
    }

    missing = sorted(required - set(parsed))

    if missing:
        raise MalformedManifestError(
            "Selection manifest is missing required fields.",
            resource_uri=uri,
            details={"missing": missing},
        )

    if not _contains_manifest_json(parsed["outputs"]):
        raise MalformedManifestError(
            "Selection manifest outputs do not "
            "identify manifest.json.",
            resource_uri=uri,
        )


def _producer_matches(
    value: Any,
    expected: str | None,
) -> bool:
    if expected is None:
        return True

    if isinstance(value, str):
        return value == expected

    if isinstance(value, dict):
        candidates = [
            value.get(key)
            for key in (
                "id",
                "name",
                "producer_id",
                "module",
            )
        ]

        return any(
            candidate == expected
            for candidate in candidates
            if candidate is not None
        )

    return False


def _contains_manifest_json(
    value: Any,
) -> bool:
    if isinstance(value, str):
        return (
            PurePosixPath(value).name
            == "manifest.json"
        )

    if isinstance(value, list):
        return any(
            _contains_manifest_json(item)
            for item in value
        )

    if isinstance(value, dict):
        return any(
            (
                PurePosixPath(str(key)).name
                == "manifest.json"
            )
            or _contains_manifest_json(item)
            for key, item in value.items()
        )

    return False
