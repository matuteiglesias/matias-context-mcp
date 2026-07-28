"""Complete-mediation policy gate for filesystem resources."""

from __future__ import annotations

import stat
from pathlib import Path, PurePosixPath

from .errors import (
    ConfigurationError,
    InvalidURIError,
    OutsideAllowedRootError,
    ResourceNotFoundError,
    ResourceTooLargeError,
    UnknownDocumentError,
    UnsupportedFormatError,
)
from .models import AuthorizedRead, ResourceRef, SourceSpec
from .registry import SourceRegistry


class ReadPolicy:
    def __init__(
        self,
        registry: SourceRegistry,
    ) -> None:
        self._registry = registry

    def authorize(
        self,
        ref: ResourceRef,
    ) -> AuthorizedRead:
        if ref.resource_family == "context_document":
            return self._authorize_document(ref)

        if ref.resource_family == "manifest":
            return self._authorize_manifest(ref)

        raise InvalidURIError(
            "Resource does not resolve "
            "to a filesystem read.",
            resource_uri=ref.uri,
        )

    def _authorize_document(
        self,
        ref: ResourceRef,
    ) -> AuthorizedRead:
        assert ref.source_id is not None
        assert ref.document_id is not None

        source = self._registry.get_source(
            ref.source_id,
            resource_uri=ref.uri,
        )

        document = source.document(ref.document_id)

        if document is None:
            raise UnknownDocumentError(
                "Unknown mapped document.",
                resource_uri=ref.uri,
            )

        return self._authorize_path(
            ref=ref,
            source=source,
            logical_id=document.document_id,
            relative_path=document.relative_path,
            media_type=document.media_type,
            codec=document.codec,
            producer_id=None,
        )

    def _authorize_manifest(
        self,
        ref: ResourceRef,
    ) -> AuthorizedRead:
        assert ref.producer_id is not None
        assert ref.manifest_id is not None

        source = self._registry.get_producer(
            ref.producer_id,
            resource_uri=ref.uri,
        )

        profile = source.manifest_profile

        if profile is None:
            raise ConfigurationError(
                "Registered producer has no "
                "manifest profile."
            )

        relative_path = profile.locator.format(
            manifest_id=ref.manifest_id
        )

        return self._authorize_path(
            ref=ref,
            source=source,
            logical_id=ref.manifest_id,
            relative_path=relative_path,
            media_type=profile.media_type,
            codec=profile.codec,
            producer_id=profile.producer_id,
            manifest_producer_id=profile.manifest_producer_id,
        )

    def _authorize_path(
        self,
        *,
        ref: ResourceRef,
        source: SourceSpec,
        logical_id: str,
        relative_path: str,
        media_type: str,
        codec: str,
        producer_id: str | None,
        manifest_producer_id: str | None = None,
    ) -> AuthorizedRead:
        relative = PurePosixPath(relative_path)

        if (
            relative.is_absolute()
            or ".." in relative.parts
        ):
            raise ConfigurationError(
                "Frozen profile contains "
                "an unsafe relative path."
            )

        root = source.root.resolve(strict=True)

        candidate = (
            root
            .joinpath(*relative.parts)
            .resolve(strict=False)
        )

        if (
            candidate == root
            or not _is_descendant(candidate, root)
        ):
            raise OutsideAllowedRootError(
                "Resolved resource is outside "
                "the allowed source root.",
                resource_uri=ref.uri,
            )

        extension = candidate.suffix.lower()

        if extension not in source.allowed_extensions:
            raise UnsupportedFormatError(
                "Resource format is not allowed.",
                resource_uri=ref.uri,
            )

        try:
            file_stat = candidate.stat()
        except OSError as exc:
            raise ResourceNotFoundError(
                "Mapped resource does not exist.",
                resource_uri=ref.uri,
            ) from exc

        if not stat.S_ISREG(file_stat.st_mode):
            raise ResourceNotFoundError(
                "Mapped resource is not a regular file.",
                resource_uri=ref.uri,
            )

        if file_stat.st_size > source.maximum_bytes:
            raise ResourceTooLargeError(
                "Resource exceeds the configured size limit.",
                resource_uri=ref.uri,
                details={
                    "maximum_bytes": source.maximum_bytes,
                },
            )

        return AuthorizedRead(
            requested_uri=ref.uri,
            resource_family=ref.resource_family,
            source_id=source.source_id,
            logical_id=logical_id,
            canonical_path=candidate,
            content_media_type=media_type,
            maximum_bytes=source.maximum_bytes,
            authority=source.authority,
            codec=codec,
            producer_id=producer_id,
            manifest_producer_id=manifest_producer_id,
        )


def _is_descendant(
    candidate: Path,
    root: Path,
) -> bool:
    try:
        candidate.relative_to(root)
    except ValueError:
        return False

    return True
