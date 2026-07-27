"""Transport-independent orchestration for all gateway resources."""

from __future__ import annotations

from typing import Any

from .adapters.filesystem import FilesystemAdapter
from .generated import (
    build_source_catalog,
    build_source_descriptor,
)
from .manifest_summary import build_manifest_summary
from .models import (
    ResourceDocument,
    ResourceRef,
)
from .normalizer import normalize
from .policy import ReadPolicy
from .registry import SourceRegistry
from .resolver import parse_resource_uri


class ResourceKernel:
    def __init__(
        self,
        registry: SourceRegistry,
        *,
        filesystem: FilesystemAdapter | None = None,
    ) -> None:
        self.registry = registry
        self._policy = ReadPolicy(registry)
        self._filesystem = (
            filesystem
            or FilesystemAdapter()
        )

    def read(
        self,
        uri: str,
    ) -> ResourceDocument:
        """Read a filesystem-backed resource."""

        ref = parse_resource_uri(uri)
        return self._read_ref(ref)

    def read_envelope(
        self,
        uri: str,
    ) -> dict[str, Any]:
        """Read any generated or filesystem-backed resource."""

        ref = parse_resource_uri(uri)

        if ref.resource_family == "source_catalog":
            return build_source_catalog(
                self.registry,
                uri=ref.uri,
            )

        if ref.resource_family == "source_descriptor":
            assert ref.source_id is not None

            return build_source_descriptor(
                self.registry,
                source_id=ref.source_id,
                uri=ref.uri,
            )

        document = self._read_ref(ref)
        envelope = document.to_envelope()

        if ref.resource_family == "manifest":
            manifest = envelope["data"].get("json")

            envelope["data"]["manifest_summary"] = (
                build_manifest_summary(
                    manifest,
                    producer_id=(
                        document.producer_id
                        or document.source_id
                    ),
                    manifest_id=document.logical_id,
                )
            )

        return envelope

    def _read_ref(
        self,
        ref: ResourceRef,
    ) -> ResourceDocument:
        authorized = self._policy.authorize(ref)
        raw = self._filesystem.read(authorized)
        return normalize(raw)
