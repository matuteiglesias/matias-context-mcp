from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from matias_context_mcp.config import (
    _validate_relative_path,
    load_registry,
)
from matias_context_mcp.errors import ConfigurationError
from matias_context_mcp.kernel import ResourceKernel
from matias_context_mcp.profile import (
    HARD_MAX_BYTES,
    PROFILE_ID,
)
from tests.helpers import provision_profile


def _config(tmp_path: Path, mounts: list[dict[str, str]]) -> Path:
    path = tmp_path / "gateway.json"
    path.write_text(
        json.dumps(
            {
                "config_version": "mcp-context-gateway.v0.1",
                "profile": PROFILE_ID,
                "sources": mounts,
            }
        ),
        encoding="utf-8",
    )
    return path.resolve()


def _load(tmp_path: Path):
    environment, roots, mounts = provision_profile(tmp_path)
    return (
        load_registry(_config(tmp_path, mounts), environ=environment),
        environment,
        roots,
        mounts,
    )


def test_verified_identity_is_exposed_without_physical_paths(
    tmp_path: Path,
) -> None:
    registry, _, roots, _ = _load(tmp_path)
    source = registry.get_source("kb-contracts")
    assert source.identity is not None

    declaration = roots["kb-contracts"] / "SYSTEM.yaml"
    expected_sha = hashlib.sha256(declaration.read_bytes()).hexdigest()
    assert source.identity.repository_id == "repo.kb-contracts"
    assert source.identity.declaration_id == "kb.contracts.registry"
    assert source.identity.system == "kb.contracts"
    assert source.identity.declaration_sha256 == expected_sha

    envelope = ResourceKernel(registry).read_envelope(
        "matias-context://catalog/sources"
    )
    catalog_source = next(
        item
        for item in envelope["data"]["sources"]
        if item["source_id"] == "kb-contracts"
    )
    assert catalog_source["identity"]["verification"] == "verified"
    assert catalog_source["identity"]["repository_id"] == "repo.kb-contracts"
    serialized = json.dumps(envelope)
    assert all(str(root) not in serialized for root in roots.values())


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", 2),
        ("id", "wrong.declaration"),
        ("repository_id", "repo.wrong"),
        ("github", "matuteiglesias/wrong"),
        ("system", "kb.wrong"),
    ],
)
def test_identity_mismatch_fails_closed(
    tmp_path: Path,
    field: str,
    value: object,
) -> None:
    environment, roots, mounts = provision_profile(tmp_path)
    path = roots["kb-contracts"] / "SYSTEM.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))

    if field == "repository_id":
        payload["repository"]["id"] = value
    elif field == "github":
        payload["repository"]["github"] = value
    else:
        payload[field] = value

    path.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError) as failure:
        load_registry(_config(tmp_path, mounts), environ=environment)

    assert failure.value.details["source_id"] == "kb-contracts"
    expected_field = "declaration_id" if field == "id" else field
    assert expected_field in failure.value.details["mismatched_fields"]


def test_swapped_roots_fail_identity_verification(
    tmp_path: Path,
) -> None:
    environment, _, mounts = provision_profile(tmp_path)
    environment["KB_CONTRACTS_ROOT"], environment["KB_ARTIFACTS_ROOT"] = (
        environment["KB_ARTIFACTS_ROOT"],
        environment["KB_CONTRACTS_ROOT"],
    )

    with pytest.raises(ConfigurationError):
        load_registry(_config(tmp_path, mounts), environ=environment)


def test_missing_identity_declaration_fails_closed(
    tmp_path: Path,
) -> None:
    environment, roots, mounts = provision_profile(tmp_path)
    (roots["kb-contracts"] / "SYSTEM.yaml").unlink()

    with pytest.raises(ConfigurationError) as failure:
        load_registry(_config(tmp_path, mounts), environ=environment)

    assert failure.value.details["source_id"] == "kb-contracts"


def test_missing_document_fails_preflight_and_restoration_recovers(
    tmp_path: Path,
) -> None:
    environment, roots, mounts = provision_profile(tmp_path)
    path = roots["kb-contracts"] / "README.md"
    original = path.read_text(encoding="utf-8")
    path.unlink()

    with pytest.raises(ConfigurationError) as failure:
        load_registry(_config(tmp_path, mounts), environ=environment)
    assert failure.value.details["cause"] == "resource_not_found"

    path.write_text(original, encoding="utf-8")
    registry = load_registry(_config(tmp_path, mounts), environ=environment)
    assert registry.get_source("kb-contracts").identity is not None


def test_malformed_json_fails_startup_preflight(
    tmp_path: Path,
) -> None:
    environment, roots, mounts = provision_profile(tmp_path)
    (
        roots["context-routing"]
        / "static/context-data/v1/sources.json"
    ).write_text("{not-json", encoding="utf-8")

    with pytest.raises(ConfigurationError) as failure:
        load_registry(_config(tmp_path, mounts), environ=environment)

    assert failure.value.details["cause"] == "malformed_json"


def test_invalid_utf8_fails_startup_preflight(
    tmp_path: Path,
) -> None:
    environment, roots, mounts = provision_profile(tmp_path)
    (roots["kb-contracts"] / "README.md").write_bytes(b"\xff\xfe")

    with pytest.raises(ConfigurationError) as failure:
        load_registry(_config(tmp_path, mounts), environ=environment)

    assert failure.value.details["cause"] == "unsupported_format"


def test_oversized_document_fails_startup_preflight(
    tmp_path: Path,
) -> None:
    environment, roots, mounts = provision_profile(tmp_path)
    (roots["kb-contracts"] / "README.md").write_bytes(
        b"x" * (HARD_MAX_BYTES + 1)
    )

    with pytest.raises(ConfigurationError) as failure:
        load_registry(_config(tmp_path, mounts), environ=environment)

    assert failure.value.details["cause"] == "resource_too_large"


def test_document_symlink_escape_fails_startup_preflight(
    tmp_path: Path,
) -> None:
    environment, roots, mounts = provision_profile(tmp_path)
    outside = tmp_path / "outside.md"
    outside.write_text("# outside\n", encoding="utf-8")
    path = roots["kb-contracts"] / "README.md"
    path.unlink()
    path.symlink_to(outside)

    with pytest.raises(ConfigurationError) as failure:
        load_registry(_config(tmp_path, mounts), environ=environment)

    assert failure.value.details["cause"] == "outside_allowed_root"


def test_manifest_locator_symlink_escape_fails_preflight(
    tmp_path: Path,
) -> None:
    environment, roots, mounts = provision_profile(tmp_path)
    outside = tmp_path / "outside-artifacts"
    outside.mkdir()
    (roots["knowledge-inspect"] / "artifacts").symlink_to(
        outside,
        target_is_directory=True,
    )

    with pytest.raises(ConfigurationError) as failure:
        load_registry(_config(tmp_path, mounts), environ=environment)

    assert failure.value.details["source_id"] == "knowledge-inspect"


def test_wrong_extension_is_rejected_by_frozen_profile_validation() -> None:
    with pytest.raises(ConfigurationError):
        _validate_relative_path(
            "README.txt",
            label="fixture/wrong-extension",
        )
