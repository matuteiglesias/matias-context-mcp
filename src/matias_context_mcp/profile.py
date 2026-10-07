"""Frozen public exposure profile for contract v0.1."""

from __future__ import annotations

from dataclasses import dataclass

from .models import DocumentSpec, ManifestProfile

CONFIG_VERSION = "mcp-context-gateway.v0.1"
PROFILE_ID = "mvp-four-sources"

HARD_MAX_BYTES = 262_144
SYSTEM_DECLARATION_MAX_BYTES = 65_536
SUPPORTED_EXTENSIONS = frozenset({".md", ".json"})


@dataclass(frozen=True, slots=True)
class SourceIdentityExpectation:
    schema_version: int
    declaration_id: str
    repository_id: str
    github: str
    system: str


@dataclass(frozen=True, slots=True)
class ProfileSource:
    source_id: str
    display_name: str
    role: str
    authority: str
    root_env: str
    identity: SourceIdentityExpectation
    documents: tuple[DocumentSpec, ...]
    manifest_profile: ManifestProfile | None = None


FROZEN_PROFILE: tuple[ProfileSource, ...] = (
    ProfileSource(
        source_id="context-routing",
        display_name="Context Routing",
        role="routing_projection",
        authority="routing",
        root_env="CONTEXT_ROUTING_ROOT",
        identity=SourceIdentityExpectation(
            schema_version=1,
            declaration_id="kb.context-routing.catalog",
            repository_id="repo.context",
            github="matuteiglesias/context-routing",
            system="kb.context-routing",
        ),
        documents=(
            DocumentSpec(
                "routing-overview",
                "README.md",
                "text/markdown",
                "markdown",
            ),
            DocumentSpec(
                "published-source-catalog",
                "static/context-data/v1/sources.json",
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
        identity=SourceIdentityExpectation(
            schema_version=1,
            declaration_id="kb.contracts.registry",
            repository_id="repo.kb-contracts",
            github="matuteiglesias/kb-contracts",
            system="kb.contracts",
        ),
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
        identity=SourceIdentityExpectation(
            schema_version=1,
            declaration_id="kb.inspect.runtime",
            repository_id="repo.knowledge-inspect",
            github="matuteiglesias/knowledge-inspect",
            system="kb.inspect",
        ),
        documents=(
            DocumentSpec(
                "module-definition",
                "docs/modules/kb-module-definition.md",
                "text/markdown",
                "markdown",
            ),
            DocumentSpec(
                "architecture-freeze",
                "docs/architecture/knowledge-inspect-architecture-freeze.md",
                "text/markdown",
                "markdown",
            ),
            DocumentSpec(
                "operator-runbook",
                "runbooks/kb_module_runbook.md",
                "text/markdown",
                "markdown",
            ),
        ),
        manifest_profile=ManifestProfile(
            producer_id="knowledge-inspect",
            manifest_producer_id="kb",
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
        identity=SourceIdentityExpectation(
            schema_version=1,
            declaration_id="kb.artifacts.selector",
            repository_id="repo.gpt-digests",
            github="matuteiglesias/kb-artifacts",
            system="kb.artifacts",
        ),
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
            manifest_producer_id=None,
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
