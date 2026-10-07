"""Transport-independent orchestration for all gateway resources."""

from __future__ import annotations

from typing import Any

from .adapters.filesystem import FilesystemAdapter
from .generated import (
    build_source_catalog,
    build_source_descriptor,
)
from .manifest_summary import build_manifest_summary
from .errors import InvalidURIError, MalformedManifestError, ResourceIntegrityError
from .models import (
    ResourceDocument,
    ResourceRef,
)
from .normalizer import normalize
from .policy import ReadPolicy
from .profile import V01_CONFIG_VERSION, V01_PROFILE_ID, V03_CONFIG_VERSION, V03_PROFILE_ID
from .registry import SourceRegistry
from .resolver import parse_resource_uri


class ResourceKernel:
    def __init__(
        self,
        registry: SourceRegistry,
        *,
        contract_version: str = V01_CONFIG_VERSION,
        profile_id: str = V01_PROFILE_ID,
        filesystem: FilesystemAdapter | None = None,
    ) -> None:
        self.registry = registry
        self.contract_version = contract_version
        self.profile_id = profile_id
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
                contract_version=self.contract_version,
                profile_id=self.profile_id,
            )

        if ref.resource_family == "source_descriptor":
            assert ref.source_id is not None

            return build_source_descriptor(
                self.registry,
                source_id=ref.source_id,
                uri=ref.uri,
                contract_version=self.contract_version,
                profile_id=self.profile_id,
            )

        document = self._read_ref(ref)
        envelope = document.to_envelope(self.contract_version)

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
        if ref.resource_family == "selected_evidence":
            if (
                self.contract_version != V03_CONFIG_VERSION
                or self.profile_id != V03_PROFILE_ID
            ):
                raise InvalidURIError(
                    "Invalid resource URI.",
                    resource_uri=ref.uri,
                )
            return self._read_selected_evidence(ref)

        authorized = self._policy.authorize(ref)
        raw = self._filesystem.read(authorized)
        return normalize(raw)

    def _read_selected_evidence(
        self,
        ref: ResourceRef,
    ) -> ResourceDocument:
        assert ref.producer_id is not None
        assert ref.manifest_id is not None

        authorized = self._policy.authorize(ref)
        raw = self._filesystem.read(authorized)

        manifest_uri = (
            "matias-context://manifest/"
            f"{ref.producer_id}/{ref.manifest_id}"
        )
        manifest = self._read_ref(
            ResourceRef(
                uri=manifest_uri,
                resource_family="manifest",
                producer_id=ref.producer_id,
                manifest_id=ref.manifest_id,
            )
        )
        payload = manifest.data.get("json")
        if not isinstance(payload, dict):
            raise MalformedManifestError(
                "Selection manifest is missing normalized JSON.",
                resource_uri=manifest_uri,
            )
        checksums = payload.get("output_checksums")
        expected = (
            checksums.get("selected.jsonl")
            if isinstance(checksums, dict)
            else None
        )
        if (
            not isinstance(expected, str)
            or len(expected) != 64
            or any(character not in "0123456789abcdef" for character in expected)
        ):
            raise MalformedManifestError(
                "Selection manifest does not bind selected.jsonl.",
                resource_uri=manifest_uri,
            )
        if raw.sha256 != expected:
            raise ResourceIntegrityError(
                "Selected evidence does not match its selection manifest.",
                resource_uri=ref.uri,
                details={
                    "manifest_id": ref.manifest_id,
                    "expected_sha256": expected,
                    "actual_sha256": raw.sha256,
                },
            )

        document = normalize(raw)
        document.data["integrity"] = {
            "manifest_uri": manifest_uri,
            "manifest_sha256": manifest.sha256,
            "selected_sha256": raw.sha256,
            "verified": True,
        }
        return document
