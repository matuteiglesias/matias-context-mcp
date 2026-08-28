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

_CONTEXT_CATALOG_SCHEMA_ID = "context_catalog"
_CONTEXT_CATALOG_SCHEMA_VERSION = "1"
_CONTEXT_SOURCE_SCHEMA_ID = "context_source"
_CONTEXT_SOURCE_SCHEMA_VERSION = "1"
_CONTEXT_REQUIRED_SOURCE_FIELDS = (
    "schema_id",
    "schema_version",
    "source_id",
    "display_name",
    "slug",
    "page_url",
    "publication_kind",
    "agent_ready",
    "generated_at",
)
_CONTEXT_ALLOWED_FIELDS = (
    *_CONTEXT_REQUIRED_SOURCE_FIELDS,
    "public_origin_url",
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
    """Validate and re-project Context Routing's public v1 catalog.

    Context Routing owns publication eligibility and emits an already-safe public
    allow-list. The gateway therefore validates the public contract identity and
    applies its own final field allow-list, but it must not re-run the producer's
    private publication policy using fields that are intentionally absent from
    the public artifact.
    """

    if not isinstance(parsed, dict):
        raise MalformedJSONError(
            "Context Routing catalog must be a JSON object.",
            resource_uri=uri,
        )

    if (
        parsed.get("schema_id") != _CONTEXT_CATALOG_SCHEMA_ID
        or parsed.get("schema_version")
        != _CONTEXT_CATALOG_SCHEMA_VERSION
    ):
        raise MalformedJSONError(
            "Context Routing catalog has an unsupported contract identity.",
            resource_uri=uri,
        )

    entries = parsed.get("sources")
    declared_count = parsed.get("count")

    if not isinstance(entries, list):
        raise MalformedJSONError(
            "Context Routing catalog must contain a source list.",
            resource_uri=uri,
        )

    if (
        not isinstance(declared_count, int)
        or declared_count != len(entries)
    ):
        raise MalformedJSONError(
            "Context Routing catalog count does not match its source list.",
            resource_uri=uri,
        )

    projected: list[dict[str, Any]] = []

    for entry in entries:
        if not isinstance(entry, dict):
            raise MalformedJSONError(
                "Context Routing source entries must be JSON objects.",
                resource_uri=uri,
            )

        if (
            entry.get("schema_id") != _CONTEXT_SOURCE_SCHEMA_ID
            or entry.get("schema_version")
            != _CONTEXT_SOURCE_SCHEMA_VERSION
        ):
            raise MalformedJSONError(
                "Context Routing source entry has an unsupported contract identity.",
                resource_uri=uri,
            )

        if any(
            key not in entry
            or not isinstance(entry[key], str)
            for key in _CONTEXT_REQUIRED_SOURCE_FIELDS
        ):
            raise MalformedJSONError(
                "Context Routing source entry is missing required public fields.",
                resource_uri=uri,
            )

        for optional in (
            "public_origin_url",
            "artifact_url",
            "snapshot_url",
        ):
            if optional in entry and not isinstance(entry[optional], str):
                raise MalformedJSONError(
                    "Context Routing source entry has an invalid public URL field.",
                    resource_uri=uri,
                )

        projected.append(
            {
                key: entry[key]
                for key in _CONTEXT_ALLOWED_FIELDS
                if key in entry
            }
        )

    result: dict[str, Any] = {
        "schema_id": _CONTEXT_CATALOG_SCHEMA_ID,
        "schema_version": _CONTEXT_CATALOG_SCHEMA_VERSION,
        "count": len(projected),
        "sources": projected,
    }

    generated_at = parsed.get("generated_at")
    if isinstance(generated_at, str):
        result["generated_at"] = generated_at

    return result


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
