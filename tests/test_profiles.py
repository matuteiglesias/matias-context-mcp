from __future__ import annotations

import json
from pathlib import Path

import pytest

from matias_context_mcp.config import (
    build_registry,
    load_settings,
)
from matias_context_mcp.errors import ConfigurationError
from matias_context_mcp.kernel import ResourceKernel
from matias_context_mcp.profile import (
    V01_CONFIG_VERSION,
    V01_PROFILE,
    V01_PROFILE_ID,
    V02_CONFIG_VERSION,
    V02_PROFILE,
    V02_PROFILE_ID,
    V03_CONFIG_VERSION,
    V03_PROFILE,
    V03_PROFILE_ID,
)
from tests.helpers import provision_profile


def _write_config(
    tmp_path: Path,
    *,
    config_version: str,
    profile_id: str,
    mounts: list[dict[str, str]],
    name: str,
) -> Path:
    path = tmp_path / name
    path.write_text(
        json.dumps(
            {
                "config_version": config_version,
                "profile": profile_id,
                "sources": mounts,
            }
        ),
        encoding="utf-8",
    )
    return path.resolve()


def _load_profile(tmp_path: Path, profile):
    environment, roots, mounts = provision_profile(
        tmp_path,
        profile,
    )
    config = _write_config(
        tmp_path,
        config_version=profile.config_version,
        profile_id=profile.profile_id,
        mounts=mounts,
        name=f"{profile.profile_id}.json",
    )
    settings = load_settings(config, environ=environment)
    registry = build_registry(settings, environ=environment)
    kernel = ResourceKernel(
        registry,
        contract_version=settings.config_version,
        profile_id=settings.profile,
    )
    return settings, kernel, environment, roots, mounts


def test_v01_profile_remains_exact_four_source_surface(
    tmp_path: Path,
) -> None:
    settings, kernel, _, _, _ = _load_profile(
        tmp_path,
        V01_PROFILE,
    )
    catalog = kernel.read_envelope(
        "matias-context://catalog/sources"
    )

    assert settings.config_version == V01_CONFIG_VERSION
    assert settings.profile == V01_PROFILE_ID
    assert catalog["contract_version"] == V01_CONFIG_VERSION
    assert catalog["resource"]["provenance"]["profile_id"] == V01_PROFILE_ID
    assert catalog["data"]["count"] == 4
    assert [
        source["source_id"]
        for source in catalog["data"]["sources"]
    ] == [
        "context-routing",
        "kb-contracts",
        "knowledge-inspect",
        "kb-artifacts",
    ]


def test_v02_extends_v01_with_projects_only(
    tmp_path: Path,
) -> None:
    assert V02_PROFILE.sources[:4] == V01_PROFILE.sources
    assert [
        source.source_id
        for source in V02_PROFILE.sources[4:]
    ] == ["projects"]

    settings, kernel, _, _, _ = _load_profile(
        tmp_path,
        V02_PROFILE,
    )
    catalog = kernel.read_envelope(
        "matias-context://catalog/sources"
    )

    assert settings.config_version == V02_CONFIG_VERSION
    assert settings.profile == V02_PROFILE_ID
    assert catalog["contract_version"] == V02_CONFIG_VERSION
    assert catalog["resource"]["provenance"]["profile_id"] == V02_PROFILE_ID
    assert catalog["data"]["count"] == 5
    assert catalog["data"]["sources"][-1]["source_id"] == "projects"
    assert catalog["data"]["sources"][-1]["identity"]["repository_id"] == "repo.projects"


def test_v02_projects_descriptor_is_bounded_orientation_surface(
    tmp_path: Path,
) -> None:
    _, kernel, _, _, _ = _load_profile(
        tmp_path,
        V02_PROFILE,
    )
    descriptor = kernel.read_envelope(
        "matias-context://source/projects"
    )
    documents = {
        item["document_id"]
        for item in descriptor["data"]["available_documents"]
    }

    assert descriptor["contract_version"] == V02_CONFIG_VERSION
    assert documents == {
        "staff-operating-model",
        "agenda-guide",
        "agenda-freshness-contract",
        "agenda-index",
        "accounting-family",
        "base-de-datos-2c-2026",
        "fcv-research",
        "job-search",
        "lcd-institutional-surfaces",
        "media-monitor",
        "poverty-ecosystem",
        "relationships-opportunities",
        "estate-sensing-observability",
        "office-execution-loop",
        "context-discovery-mcp",
        "knowledge-evidence-fabric",
        "youtube-following-product",
        "public-professional-publishing",
        "census-query-product",
        "rxdb-census-extraction",
        "census-sampling-alignment",
        "price-basket-science",
        "engho-consumption-research",
        "eph-labor-state",
        "argentina-geography",
        "electoral-data",
        "economic-scaling-research",
        "teaching-tools",
        "lcd-knowledge-corpus",
        "site-factory-workflow",
        "political-knowledge-sources",
    }
    assert descriptor["data"]["manifest_profile"] is None


def test_v02_reads_projects_agenda_index_as_generic_json(
    tmp_path: Path,
) -> None:
    _, kernel, _, _, _ = _load_profile(
        tmp_path,
        V02_PROFILE,
    )
    envelope = kernel.read_envelope(
        "matias-context://source/projects/document/agenda-index"
    )

    assert envelope["contract_version"] == V02_CONFIG_VERSION
    assert envelope["resource"]["source_id"] == "projects"
    assert envelope["data"]["json"]["contract"] == "context:project-agendas@1"


def test_profile_version_pairs_cannot_be_mixed(
    tmp_path: Path,
) -> None:
    environment, _, mounts = provision_profile(
        tmp_path,
        V01_PROFILE,
    )
    config = _write_config(
        tmp_path,
        config_version=V01_CONFIG_VERSION,
        profile_id=V02_PROFILE_ID,
        mounts=mounts,
        name="mixed.json",
    )

    with pytest.raises(ConfigurationError):
        load_settings(config, environ=environment)


def test_v02_requires_projects_mount(
    tmp_path: Path,
) -> None:
    environment, _, mounts = provision_profile(
        tmp_path,
        V02_PROFILE,
    )
    mounts = [
        mount
        for mount in mounts
        if mount["source_id"] != "projects"
    ]
    config = _write_config(
        tmp_path,
        config_version=V02_CONFIG_VERSION,
        profile_id=V02_PROFILE_ID,
        mounts=mounts,
        name="missing-projects.json",
    )

    with pytest.raises(ConfigurationError):
        load_settings(config, environ=environment)


def test_v02_rejects_wrong_projects_agenda_index_contract(
    tmp_path: Path,
) -> None:
    environment, roots, mounts = provision_profile(
        tmp_path,
        V02_PROFILE,
    )
    (
        roots["projects"]
        / "generated"
        / "project-agenda-index.json"
    ).write_text(
        json.dumps(
            {
                "contract": "not-project-agendas",
                "agenda_schema_version": 2,
                "agendas": {},
            }
        ),
        encoding="utf-8",
    )
    config = _write_config(
        tmp_path,
        config_version=V02_CONFIG_VERSION,
        profile_id=V02_PROFILE_ID,
        mounts=mounts,
        name="wrong-agenda-index.json",
    )
    settings = load_settings(config, environ=environment)

    with pytest.raises(ConfigurationError) as failure:
        build_registry(settings, environ=environment)

    assert failure.value.details["source_id"] == "projects"
    assert failure.value.details["document_id"] == "agenda-index"
    assert failure.value.details["cause"] == "malformed_json"


def test_v03_extends_v02_only_with_selected_evidence_capability(
    tmp_path: Path,
) -> None:
    assert [
        source.source_id
        for source in V03_PROFILE.sources
    ] == [
        source.source_id
        for source in V02_PROFILE.sources
    ]
    assert V03_PROFILE.sources[:3] == V02_PROFILE.sources[:3]
    assert V03_PROFILE.sources[4] == V02_PROFILE.sources[4]
    assert V02_PROFILE.sources[3].selected_evidence_profile is None
    assert (
        V03_PROFILE.sources[3].selected_evidence_profile
        is not None
    )

    settings, kernel, _, _, _ = _load_profile(
        tmp_path,
        V03_PROFILE,
    )
    catalog = kernel.read_envelope(
        "matias-context://catalog/sources"
    )
    assert settings.config_version == V03_CONFIG_VERSION
    assert settings.profile == V03_PROFILE_ID
    assert catalog["data"]["count"] == 5
    assert [
        item["source_id"]
        for item in catalog["data"]["sources"]
    ] == [
        "context-routing",
        "kb-contracts",
        "knowledge-inspect",
        "kb-artifacts",
        "projects",
    ]
