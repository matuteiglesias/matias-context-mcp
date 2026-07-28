"""Strict parser for the logical resource URI namespace."""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from .errors import InvalidURIError
from .models import ResourceRef

_SCHEME = "matias-context"
_LOWERCASE_IDENTIFIER = re.compile(
    r"^[a-z0-9][a-z0-9._-]{0,127}$"
)
_MANIFEST_IDENTIFIER = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$"
)
_MAX_URI_LENGTH = 1024


def _invalid(
    uri: str,
    message: str = "Invalid resource URI.",
) -> InvalidURIError:
    return InvalidURIError(
        message,
        resource_uri=uri,
    )


def _validate_identifier(
    identifier: str,
    *,
    uri: str,
) -> str:
    if (
        ".." in identifier
        or not _LOWERCASE_IDENTIFIER.fullmatch(identifier)
    ):
        raise _invalid(
            uri,
            "Invalid logical identifier.",
        )

    return identifier


def _validate_manifest_identifier(
    identifier: str,
    *,
    uri: str,
) -> str:
    """Validate a producer-native, case-preserving single segment."""
    if (
        ".." in identifier
        or not _MANIFEST_IDENTIFIER.fullmatch(identifier)
    ):
        raise _invalid(uri, "Invalid manifest identifier.")
    return identifier


def parse_resource_uri(uri: str) -> ResourceRef:
    if (
        not isinstance(uri, str)
        or not uri
        or len(uri) > _MAX_URI_LENGTH
    ):
        raise _invalid(str(uri))

    try:
        parsed = urlsplit(uri)
        _ = parsed.port
    except ValueError as exc:
        raise _invalid(uri) from exc

    if parsed.scheme != _SCHEME:
        raise _invalid(
            uri,
            "Unsupported resource URI scheme.",
        )

    if parsed.query or parsed.fragment:
        raise _invalid(
            uri,
            "Query strings and fragments are not supported.",
        )

    if (
        parsed.username is not None
        or parsed.password is not None
        or parsed.port is not None
    ):
        raise _invalid(uri)

    if (
        not parsed.netloc
        or not parsed.path.startswith("/")
    ):
        raise _invalid(uri)

    segments = parsed.path[1:].split("/")

    if (
        not segments
        or any(segment == "" for segment in segments)
    ):
        raise _invalid(uri)

    if (
        parsed.netloc == "catalog"
        and segments == ["sources"]
    ):
        return ResourceRef(
            uri=uri,
            resource_family="source_catalog",
        )

    if parsed.netloc == "source":
        if len(segments) == 1:
            source_id = _validate_identifier(
                segments[0],
                uri=uri,
            )
            return ResourceRef(
                uri=uri,
                resource_family="source_descriptor",
                source_id=source_id,
            )

        if (
            len(segments) == 3
            and segments[1] == "document"
        ):
            source_id = _validate_identifier(
                segments[0],
                uri=uri,
            )
            document_id = _validate_identifier(
                segments[2],
                uri=uri,
            )

            return ResourceRef(
                uri=uri,
                resource_family="context_document",
                source_id=source_id,
                document_id=document_id,
            )

        raise _invalid(uri)

    if (
        parsed.netloc == "manifest"
        and len(segments) == 2
    ):
        producer_id = _validate_identifier(
            segments[0],
            uri=uri,
        )
        manifest_id = _validate_manifest_identifier(
            segments[1],
            uri=uri,
        )

        return ResourceRef(
            uri=uri,
            resource_family="manifest",
            producer_id=producer_id,
            manifest_id=manifest_id,
        )

    raise _invalid(uri)
