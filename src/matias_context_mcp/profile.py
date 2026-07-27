"""Frozen public exposure profile for contract v0.1."""

from __future__ import annotations

from dataclasses import dataclass

from .models import DocumentSpec, ManifestProfile

CONFIG_VERSION = "mcp-context-gateway.v0.1"
PROFILE_ID = "mvp-four-sources"

HARD_MAX_BYTES = 262_144
SUPPORTED_EXTENSIONS = frozenset({".md", ".json"})


@dataclass(frozen=True, slots=True)
class ProfileSource:
    source_id: str
    display_name: str
    role: str
    authority: str
    root_env: str
    documents: tuple[DocumentSpec, ...]
    manifest_profile: ManifestProfile | None = None


FROZEN_PROFILE: tuple[ProfileSource, ...] = (
    ProfileSource(
        source_id="context-routing",
        display_name="Context Routing",
        role="routing_projection",
        authority="routing",
        root_env="CONTEXT_ROUTING_ROOT",
        documents=(
            DocumentSpec(
                "routing-overview",
                "README.md",
                "text/markdown",
                "markdown",
            ),
            DocumentSpec(
                "published-source-catalog",
                "static/context-data/sources.json",
                "application/json",
                "context_routing_public_catalog",
            ),
        ),
    ),
    ProfileSource(
        source_id="kb-contracts",
        display_name="KB Contracts",
        role="contract_registry",
        authority="authoritative",
        root_env="KB_CONTRACTS_ROOT",
        documents=(
            DocumentSpec(
                "manual-overview",
                "README.md",
                "text/markdown",
                "markdown",
            ),
        ),
    ),
    ProfileSource(
        source_id="knowledge-inspect",
        display_name="Knowledge Inspect",
        role="canonical_artifact_producer",
        authority="operational",
        root_env="KNOWLEDGE_INSPECT_ROOT",
        documents=(
            DocumentSpec(
                "module-overview",
                "README.md",
                "text/markdown",
                "markdown",
            ),
            DocumentSpec(
                "module-definition",
                "docs/modules/kb-module-definition.md",
                "text/markdown",
                "markdown",
            ),
            DocumentSpec(
                "artifact-surface",
                "kb_artifact_surface.md",
                "text/markdown",
                "markdown",
            ),
            DocumentSpec(
                "health-contract",
                "kb_health_contract.md",
                "text/markdown",
                "markdown",
            ),
        ),
        manifest_profile=ManifestProfile(
            producer_id="knowledge-inspect",
            locator="artifacts/manifests/{manifest_id}.manifest.json",
            media_type="application/json",
            codec="knowledge_inspect_manifest",
        ),
    ),
    ProfileSource(
        source_id="kb-artifacts",
        display_name="KB Artifacts",
        role="governed_evidence_selector",
        authority="derived",
        root_env="KB_ARTIFACTS_ROOT",
        documents=(
            DocumentSpec(
                "selector-overview",
                "README.md",
                "text/markdown",
                "markdown",
            ),
            DocumentSpec(
                "operator-guide",
                "docs/index.md",
                "text/markdown",
                "markdown",
            ),
        ),
        manifest_profile=ManifestProfile(
            producer_id="kb-artifacts",
            locator="artifacts/runs/{manifest_id}/manifest.json",
            media_type="application/json",
            codec="kb_artifacts_manifest",
        ),
    ),
)

PROFILE_BY_SOURCE = {
    source.source_id: source
    for source in FROZEN_PROFILE
}
