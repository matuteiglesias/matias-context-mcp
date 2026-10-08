"""Static exposure profiles for MCP context gateway contracts v0.1 and v0.2."""

from __future__ import annotations

from dataclasses import dataclass

from .models import DocumentSpec, ManifestProfile, SelectedEvidenceProfile

V01_CONFIG_VERSION = "mcp-context-gateway.v0.1"
V01_PROFILE_ID = "mvp-four-sources"
V02_CONFIG_VERSION = "mcp-context-gateway.v0.2"
V02_PROFILE_ID = "estate-orientation-v0.2"
V03_CONFIG_VERSION = "mcp-context-gateway.v0.3"
V03_PROFILE_ID = "evidence-composition-v0.3"

HARD_MAX_BYTES = 262_144
SYSTEM_DECLARATION_MAX_BYTES = 65_536
SUPPORTED_EXTENSIONS = frozenset({".md", ".json", ".jsonl"})


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
    selected_evidence_profile: SelectedEvidenceProfile | None = None


@dataclass(frozen=True, slots=True)
class GatewayProfile:
    config_version: str
    profile_id: str
    sources: tuple[ProfileSource, ...]

    @property
    def by_source(self) -> dict[str, ProfileSource]:
        return {
            source.source_id: source
            for source in self.sources
        }


V01_SOURCES: tuple[ProfileSource, ...] = (
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

KB_ARTIFACTS_V03_SOURCE = ProfileSource(
    source_id=V01_SOURCES[3].source_id,
    display_name=V01_SOURCES[3].display_name,
    role=V01_SOURCES[3].role,
    authority=V01_SOURCES[3].authority,
    root_env=V01_SOURCES[3].root_env,
    identity=V01_SOURCES[3].identity,
    documents=V01_SOURCES[3].documents,
    manifest_profile=V01_SOURCES[3].manifest_profile,
    selected_evidence_profile=SelectedEvidenceProfile(
        producer_id="kb-artifacts",
        locator="artifacts/runs/{manifest_id}/selected.jsonl",
        media_type="application/x-ndjson",
        codec="kb_selected_evidence",
    ),
)


PROJECTS_SOURCE = ProfileSource(
    source_id="projects",
    display_name="Projects",
    role="estate_orientation",
    authority="control-plane",
    root_env="PROJECTS_ROOT",
    identity=SourceIdentityExpectation(
        schema_version=1,
        declaration_id="portfolio.github-estate.registry",
        repository_id="repo.projects",
        github="matuteiglesias/projects",
        system="portfolio.github-estate",
    ),
    documents=(
        DocumentSpec(
            "staff-operating-model",
            "STAFF.md",
            "text/markdown",
            "markdown",
        ),
        DocumentSpec(
            "agenda-guide",
            "estate/agendas/README.md",
            "text/markdown",
            "markdown",
        ),
        DocumentSpec(
            "agenda-freshness-contract",
            "docs/project-agenda-freshness.md",
            "text/markdown",
            "markdown",
        ),
        DocumentSpec(
            "agenda-index",
            "generated/project-agenda-index.json",
            "application/json",
            "project_agenda_index",
        ),
        DocumentSpec(
            "accounting-family",
            "estate/agendas/accounting-family.md",
            "text/markdown",
            "markdown",
        ),
        DocumentSpec(
            "base-de-datos-2c-2026",
            "estate/agendas/base-de-datos-2c-2026.md",
            "text/markdown",
            "markdown",
        ),
        DocumentSpec(
            "fcv-research",
            "estate/agendas/fcv-research.md",
            "text/markdown",
            "markdown",
        ),
        DocumentSpec(
            "job-search",
            "estate/agendas/job-search.md",
            "text/markdown",
            "markdown",
        ),
        DocumentSpec(
            "lcd-institutional-surfaces",
            "estate/agendas/lcd-institutional-surfaces.md",
            "text/markdown",
            "markdown",
        ),
        DocumentSpec(
            "media-monitor",
            "estate/agendas/media-monitor.md",
            "text/markdown",
            "markdown",
        ),
        DocumentSpec(
            "poverty-ecosystem",
            "estate/agendas/poverty-ecosystem.md",
            "text/markdown",
            "markdown",
        ),
        DocumentSpec(
            "relationships-opportunities",
            "estate/agendas/relationships-opportunities.md",
            "text/markdown",
            "markdown",
        ),
        DocumentSpec(
            "estate-sensing-observability",
            "estate/agendas/estate-sensing-observability.md",
            "text/markdown",
            "markdown",
        ),
        DocumentSpec(
            "office-execution-loop",
            "estate/agendas/office-execution-loop.md",
            "text/markdown",
            "markdown",
        ),
        DocumentSpec(
            "context-discovery-mcp",
            "estate/agendas/context-discovery-mcp.md",
            "text/markdown",
            "markdown",
        ),
        DocumentSpec(
            "knowledge-evidence-fabric",
            "estate/agendas/knowledge-evidence-fabric.md",
            "text/markdown",
            "markdown",
        ),
        DocumentSpec(
            "youtube-following-product",
            "estate/agendas/youtube-following-product.md",
            "text/markdown",
            "markdown",
        ),
        DocumentSpec(
            "public-professional-publishing",
            "estate/agendas/public-professional-publishing.md",
            "text/markdown",
            "markdown",
        ),
        DocumentSpec(
            "census-query-product",
            "estate/agendas/census-query-product.md",
            "text/markdown",
            "markdown",
        ),
        DocumentSpec(
            "rxdb-census-extraction",
            "estate/agendas/rxdb-census-extraction.md",
            "text/markdown",
            "markdown",
        ),
        DocumentSpec(
            "census-sampling-alignment",
            "estate/agendas/census-sampling-alignment.md",
            "text/markdown",
            "markdown",
        ),
        DocumentSpec(
            "price-basket-science",
            "estate/agendas/price-basket-science.md",
            "text/markdown",
            "markdown",
        ),
        DocumentSpec(
            "engho-consumption-research",
            "estate/agendas/engho-consumption-research.md",
            "text/markdown",
            "markdown",
        ),
        DocumentSpec(
            "eph-labor-state",
            "estate/agendas/eph-labor-state.md",
            "text/markdown",
            "markdown",
        ),
        DocumentSpec(
            "argentina-geography",
            "estate/agendas/argentina-geography.md",
            "text/markdown",
            "markdown",
        ),
        DocumentSpec(
            "electoral-data",
            "estate/agendas/electoral-data.md",
            "text/markdown",
            "markdown",
        ),
        DocumentSpec(
            "economic-scaling-research",
            "estate/agendas/economic-scaling-research.md",
            "text/markdown",
            "markdown",
        ),
        DocumentSpec(
            "teaching-tools",
            "estate/agendas/teaching-tools.md",
            "text/markdown",
            "markdown",
        ),
        DocumentSpec(
            "lcd-knowledge-corpus",
            "estate/agendas/lcd-knowledge-corpus.md",
            "text/markdown",
            "markdown",
        ),
        DocumentSpec(
            "site-factory-workflow",
            "estate/agendas/site-factory-workflow.md",
            "text/markdown",
            "markdown",
        ),
        DocumentSpec(
            "political-knowledge-sources",
            "estate/agendas/political-knowledge-sources.md",
            "text/markdown",
            "markdown",
        ),
    ),
)

V01_PROFILE = GatewayProfile(
    config_version=V01_CONFIG_VERSION,
    profile_id=V01_PROFILE_ID,
    sources=V01_SOURCES,
)
V02_PROFILE = GatewayProfile(
    config_version=V02_CONFIG_VERSION,
    profile_id=V02_PROFILE_ID,
    sources=V01_SOURCES + (PROJECTS_SOURCE,),
)
V03_PROFILE = GatewayProfile(
    config_version=V03_CONFIG_VERSION,
    profile_id=V03_PROFILE_ID,
    sources=V01_SOURCES[:3] + (KB_ARTIFACTS_V03_SOURCE, PROJECTS_SOURCE),
)

PROFILE_REGISTRY: dict[tuple[str, str], GatewayProfile] = {
    (profile.config_version, profile.profile_id): profile
    for profile in (V01_PROFILE, V02_PROFILE, V03_PROFILE)
}


def get_profile(
    config_version: str,
    profile_id: str,
) -> GatewayProfile | None:
    return PROFILE_REGISTRY.get(
        (config_version, profile_id)
    )


# Compatibility aliases intentionally remain pinned to exact v0.1 semantics.
CONFIG_VERSION = V01_CONFIG_VERSION
PROFILE_ID = V01_PROFILE_ID
FROZEN_PROFILE = V01_PROFILE.sources
PROFILE_BY_SOURCE = V01_PROFILE.by_source
