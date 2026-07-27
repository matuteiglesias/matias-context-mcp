"""Transport-independent resource-kernel types."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class DocumentSpec:
    document_id: str
    relative_path: str
    media_type: str
    codec: str


@dataclass(frozen=True, slots=True)
class ManifestProfile:
    producer_id: str
    locator: str
    media_type: str
    codec: str


@dataclass(frozen=True, slots=True)
class SourceSpec:
    source_id: str
    display_name: str
    role: str
    authority: str
    root: Path
    documents: tuple[DocumentSpec, ...]
    maximum_bytes: int
    allowed_extensions: frozenset[str]
    manifest_profile: ManifestProfile | None = None

    def document(self, document_id: str) -> DocumentSpec | None:
        return next(
            (
                document
                for document in self.documents
                if document.document_id == document_id
            ),
            None,
        )


@dataclass(frozen=True, slots=True)
class ResourceRef:
    uri: str
    resource_family: str
    source_id: str | None = None
    document_id: str | None = None
    producer_id: str | None = None
    manifest_id: str | None = None


@dataclass(frozen=True, slots=True)
class AuthorizedRead:
    requested_uri: str
    resource_family: str
    source_id: str
    logical_id: str
    canonical_path: Path
    content_media_type: str
    maximum_bytes: int
    authority: str
    codec: str
    producer_id: str | None = None


@dataclass(frozen=True, slots=True)
class RawResource:
    authorized: AuthorizedRead
    content: bytes
    size_bytes: int
    sha256: str
    modified_at: str | None


@dataclass(frozen=True, slots=True)
class ResourceDocument:
    uri: str
    family: str
    source_id: str
    logical_id: str
    authority: str
    content_media_type: str
    size_bytes: int
    sha256: str
    modified_at: str | None
    data: dict[str, Any]
    producer_id: str | None = None

    def to_envelope(self) -> dict[str, Any]:
        resource: dict[str, Any] = {
            "uri": self.uri,
            "family": self.family,
            "source_id": self.source_id,
            "logical_id": self.logical_id,
            "authority": self.authority,
            "read_only": True,
            "content_media_type": self.content_media_type,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
        }

        if self.producer_id is not None:
            resource["producer_id"] = self.producer_id

        if self.modified_at is not None:
            resource["modified_at"] = self.modified_at

        return {
            "contract_version": "mcp-context-gateway.v0.1",
            "resource": resource,
            "data": self.data,
        }
