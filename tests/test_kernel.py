from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from matias_context_mcp.adapters.filesystem import (
    FilesystemAdapter,
)
from matias_context_mcp.config import (
    load_registry,
    load_settings,
)
from matias_context_mcp.errors import (
    ConfigurationError,
    InvalidURIError,
    OutsideAllowedRootError,
    ResourceTooLargeError,
    UnknownDocumentError,
    UnknownSourceError,
    UnsupportedFormatError,
)
from matias_context_mcp.models import (
    DocumentSpec,
    SourceSpec,
)
from matias_context_mcp.normalizer import normalize
from matias_context_mcp.policy import ReadPolicy
from matias_context_mcp.profile import (
    HARD_MAX_BYTES,
    PROFILE_BY_SOURCE,
    PROFILE_ID,
)
from matias_context_mcp.registry import SourceRegistry
from matias_context_mcp.resolver import (
    parse_resource_uri,
)


def _mounts() -> list[dict[str, str]]:
    return [
        {
            "source_id": source.source_id,
            "root_env": source.root_env,
        }
        for source in PROFILE_BY_SOURCE.values()
    ]


def _write_config(
    tmp_path: Path,
    mounts: list[dict[str, str]] | None = None,
) -> Path:
    path = tmp_path / "gateway.json"

    path.write_text(
        json.dumps(
            {
                "config_version":
                    "mcp-context-gateway.v0.1",
                "profile": PROFILE_ID,
                "sources":
                    mounts
                    if mounts is not None
                    else _mounts(),
            }
        ),
        encoding="utf-8",
    )

    return path.resolve()


def _environment(
    tmp_path: Path,
) -> tuple[dict[str, str], dict[str, Path]]:
    env: dict[str, str] = {}
    roots: dict[str, Path] = {}

    for source in PROFILE_BY_SOURCE.values():
        root = tmp_path / source.source_id
        root.mkdir()

        env[source.root_env] = str(root)
        roots[source.source_id] = root

    return env, roots


def _registry(
    tmp_path: Path,
) -> tuple[SourceRegistry, dict[str, Path]]:
    env, roots = _environment(tmp_path)
    config_path = _write_config(tmp_path)

    return (
        load_registry(
            config_path,
            environ=env,
        ),
        roots,
    )


def test_valid_registry_loads_and_specs_are_immutable(
    tmp_path: Path,
) -> None:
    registry, _ = _registry(tmp_path)

    assert [
        source.source_id
        for source in registry.list_sources()
    ] == [
        "context-routing",
        "kb-contracts",
        "knowledge-inspect",
        "kb-artifacts",
    ]

    spec = registry.get_source("kb-contracts")

    assert isinstance(spec.documents, tuple)
    assert isinstance(spec.allowed_extensions, frozenset)

    with pytest.raises(FrozenInstanceError):
        spec.source_id = "changed"  # type: ignore[misc]


def test_duplicate_source_ids_fail_explicitly(
    tmp_path: Path,
) -> None:
    mounts = _mounts()
    mounts[-1] = dict(mounts[0])

    config_path = _write_config(
        tmp_path,
        mounts,
    )

    with pytest.raises(ConfigurationError) as failure:
        load_settings(
            config_path,
            environ={},
        )

    assert (
        failure.value.error_code
        == "configuration_error"
    )
    assert "Duplicate source ID" in failure.value.message


def test_nonexistent_root_fails_at_registry_build(
    tmp_path: Path,
) -> None:
    env, _ = _environment(tmp_path)
    env["KB_CONTRACTS_ROOT"] = str(
        tmp_path / "missing"
    )

    config_path = _write_config(tmp_path)

    with pytest.raises(ConfigurationError) as failure:
        load_registry(
            config_path,
            environ=env,
        )

    assert (
        failure.value.error_code
        == "configuration_error"
    )


@pytest.mark.parametrize(
    "uri",
    [
        "file://catalog/sources",
        (
            "matias-context://source/"
            "kb-contracts/document/.."
        ),
        (
            "matias-context://source/"
            "kb-contracts/document/a..b"
        ),
        (
            "matias-context://source/"
            "kb-contracts/document/%2Fetc%2Fpasswd"
        ),
        (
            "matias-context://source/"
            "kb-contracts/document/C:%5CWindows"
        ),
        (
            "matias-context://source/"
            "kb-contracts/document/"
            "manual-overview?raw=1"
        ),
    ],
)
def test_invalid_and_traversal_shaped_uris_are_rejected(
    uri: str,
) -> None:
    with pytest.raises(InvalidURIError):
        parse_resource_uri(uri)


def test_unknown_source_and_document_are_distinct(
    tmp_path: Path,
) -> None:
    registry, _ = _registry(tmp_path)
    policy = ReadPolicy(registry)

    unknown_source = parse_resource_uri(
        "matias-context://source/"
        "not-real/document/manual-overview"
    )

    with pytest.raises(UnknownSourceError):
        policy.authorize(unknown_source)

    unknown_document = parse_resource_uri(
        "matias-context://source/"
        "kb-contracts/document/not-mapped"
    )

    with pytest.raises(UnknownDocumentError):
        policy.authorize(unknown_document)


def test_outside_root_mapping_is_rejected(
    tmp_path: Path,
) -> None:
    root = tmp_path / "root"
    root.mkdir()

    outside = tmp_path / "outside.md"
    outside.write_text(
        "outside",
        encoding="utf-8",
    )

    spec = SourceSpec(
        source_id="custom",
        display_name="Custom",
        role="test",
        authority="test",
        root=root.resolve(),
        documents=(
            DocumentSpec(
                "escape",
                "../outside.md",
                "text/markdown",
                "markdown",
            ),
        ),
        maximum_bytes=HARD_MAX_BYTES,
        allowed_extensions=frozenset({
            ".md",
            ".json",
        }),
    )

    policy = ReadPolicy(
        SourceRegistry([spec])
    )

    ref = parse_resource_uri(
        "matias-context://source/"
        "custom/document/escape"
    )

    with pytest.raises(ConfigurationError):
        policy.authorize(ref)


def test_symlink_escape_is_rejected(
    tmp_path: Path,
) -> None:
    registry, roots = _registry(tmp_path)

    outside = tmp_path / "outside.md"
    outside.write_text(
        "outside",
        encoding="utf-8",
    )

    link = roots["kb-contracts"] / "README.md"

    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip(
            "symlinks are unavailable "
            "in this environment"
        )

    ref = parse_resource_uri(
        "matias-context://source/"
        "kb-contracts/document/manual-overview"
    )

    with pytest.raises(OutsideAllowedRootError):
        ReadPolicy(registry).authorize(ref)


def test_unsupported_extension_is_rejected(
    tmp_path: Path,
) -> None:
    root = tmp_path / "root"
    root.mkdir()

    (root / "bad.txt").write_text(
        "not supported",
        encoding="utf-8",
    )

    spec = SourceSpec(
        source_id="custom",
        display_name="Custom",
        role="test",
        authority="test",
        root=root.resolve(),
        documents=(
            DocumentSpec(
                "bad",
                "bad.txt",
                "text/plain",
                "markdown",
            ),
        ),
        maximum_bytes=HARD_MAX_BYTES,
        allowed_extensions=frozenset({
            ".md",
            ".json",
        }),
    )

    ref = parse_resource_uri(
        "matias-context://source/"
        "custom/document/bad"
    )

    with pytest.raises(UnsupportedFormatError):
        ReadPolicy(
            SourceRegistry([spec])
        ).authorize(ref)


def test_bounded_read_and_provenance(
    tmp_path: Path,
) -> None:
    registry, roots = _registry(tmp_path)

    content = (
        b"# Contract\n\n"
        b"Governed content.\n"
    )

    (
        roots["kb-contracts"]
        / "README.md"
    ).write_bytes(content)

    ref = parse_resource_uri(
        "matias-context://source/"
        "kb-contracts/document/manual-overview"
    )

    authorized = ReadPolicy(
        registry
    ).authorize(ref)

    raw = FilesystemAdapter().read(authorized)
    document = normalize(raw)
    envelope = document.to_envelope()
    serialized = json.dumps(envelope)

    assert (
        envelope["resource"]["size_bytes"]
        == len(content)
    )
    assert len(
        envelope["resource"]["sha256"]
    ) == 64
    assert (
        envelope["resource"]["authority"]
        == "authoritative"
    )
    assert (
        envelope["resource"]["uri"]
        == ref.uri
    )
    assert envelope["data"]["text"].startswith(
        "# Contract"
    )

    assert "canonical_path" not in serialized
    assert (
        str(roots["kb-contracts"])
        not in serialized
    )


def test_policy_rejects_oversized_resource(
    tmp_path: Path,
) -> None:
    registry, roots = _registry(tmp_path)

    (
        roots["kb-contracts"]
        / "README.md"
    ).write_bytes(
        b"x" * (HARD_MAX_BYTES + 1)
    )

    ref = parse_resource_uri(
        "matias-context://source/"
        "kb-contracts/document/manual-overview"
    )

    with pytest.raises(ResourceTooLargeError):
        ReadPolicy(registry).authorize(ref)


def test_adapter_rechecks_limit_after_authorization(
    tmp_path: Path,
) -> None:
    registry, roots = _registry(tmp_path)

    path = (
        roots["kb-contracts"]
        / "README.md"
    )
    path.write_text(
        "small",
        encoding="utf-8",
    )

    ref = parse_resource_uri(
        "matias-context://source/"
        "kb-contracts/document/manual-overview"
    )

    authorized = ReadPolicy(
        registry
    ).authorize(ref)

    path.write_bytes(
        b"x" * (HARD_MAX_BYTES + 1)
    )

    with pytest.raises(ResourceTooLargeError):
        FilesystemAdapter().read(authorized)


def test_binary_markdown_is_rejected(
    tmp_path: Path,
) -> None:
    registry, roots = _registry(tmp_path)

    (
        roots["kb-contracts"]
        / "README.md"
    ).write_bytes(
        b"text\x00binary"
    )

    ref = parse_resource_uri(
        "matias-context://source/"
        "kb-contracts/document/manual-overview"
    )

    authorized = ReadPolicy(
        registry
    ).authorize(ref)

    raw = FilesystemAdapter().read(authorized)

    with pytest.raises(UnsupportedFormatError):
        normalize(raw)


def test_valid_knowledge_inspect_manifest_is_normalized(
    tmp_path: Path,
) -> None:
    registry, roots = _registry(tmp_path)

    manifest_id = "run-20260727"

    manifest_path = (
        roots["knowledge-inspect"]
        / "artifacts"
        / "manifests"
        / f"{manifest_id}.manifest.json"
    )

    manifest_path.parent.mkdir(parents=True)

    manifest_path.write_text(
        json.dumps(
            {
                "run_id": manifest_id,
                "status": "succeeded",
                "producer": "knowledge-inspect",
            }
        ),
        encoding="utf-8",
    )

    ref = parse_resource_uri(
        "matias-context://manifest/"
        f"knowledge-inspect/{manifest_id}"
    )

    authorized = ReadPolicy(
        registry
    ).authorize(ref)

    document = normalize(
        FilesystemAdapter().read(authorized)
    )

    assert (
        document.producer_id
        == "knowledge-inspect"
    )
    assert (
        document.data["json"]["run_id"]
        == manifest_id
    )
