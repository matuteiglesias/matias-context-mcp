"""Strict loading and trusted startup preflight for static gateway profiles."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from .adapters.filesystem import FilesystemAdapter
from .errors import ConfigurationError, GatewayError
from .kernel import ResourceKernel
from .models import AuthorizedRead, SourceSpec, VerifiedSourceIdentity
from .profile import (
    HARD_MAX_BYTES,
    SUPPORTED_EXTENSIONS,
    SYSTEM_DECLARATION_MAX_BYTES,
    GatewayProfile,
    ProfileSource,
    get_profile,
)
from .registry import SourceRegistry

CONFIG_ENV = "MATIAS_CONTEXT_GATEWAY_CONFIG"


@dataclass(frozen=True, slots=True)
class SourceMount:
    source_id: str
    root_env: str


@dataclass(frozen=True, slots=True)
class Settings:
    config_path: Path
    config_version: str
    profile: str
    sources: tuple[SourceMount, ...]


def _strict_object(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}

    for key, value in pairs:
        if key in result:
            raise ConfigurationError(
                f"Duplicate JSON key: {key}"
            )
        result[key] = value

    return result


def _read_json(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigurationError(
            "Configuration file cannot be read."
        ) from exc

    try:
        value = json.loads(
            raw,
            object_pairs_hook=_strict_object,
        )
    except ConfigurationError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ConfigurationError(
            "Configuration file is not valid UTF-8 JSON."
        ) from exc

    if not isinstance(value, dict):
        raise ConfigurationError(
            "Configuration must contain one JSON object."
        )

    return value


def _selected_profile(
    config_version: object,
    profile_id: object,
) -> GatewayProfile:
    if (
        not isinstance(config_version, str)
        or not isinstance(profile_id, str)
    ):
        raise ConfigurationError(
            "Configuration version and profile must be strings."
        )

    selected = get_profile(
        config_version,
        profile_id,
    )
    if selected is None:
        raise ConfigurationError(
            "Unsupported configuration/profile combination."
        )
    return selected


def load_settings(
    config_path: str | Path | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> Settings:
    env = os.environ if environ is None else environ
    selected = config_path or env.get(CONFIG_ENV)

    if not selected:
        raise ConfigurationError(
            f"{CONFIG_ENV} is not configured."
        )

    path = Path(selected).expanduser()

    if not path.is_absolute():
        raise ConfigurationError(
            "Configuration path must be absolute."
        )

    path = path.resolve(strict=False)

    if not path.is_file():
        raise ConfigurationError(
            "Configuration file does not exist."
        )

    payload = _read_json(path)

    unknown_top_level = set(payload) - {
        "config_version",
        "profile",
        "sources",
    }
    if unknown_top_level:
        raise ConfigurationError(
            "Configuration contains unsupported fields."
        )

    profile = _selected_profile(
        payload.get("config_version"),
        payload.get("profile"),
    )

    raw_sources = payload.get("sources")
    if not isinstance(raw_sources, list):
        raise ConfigurationError(
            "Configuration sources must be a list."
        )

    mounts: list[SourceMount] = []
    seen: set[str] = set()

    for item in raw_sources:
        if (
            not isinstance(item, dict)
            or set(item) != {"source_id", "root_env"}
        ):
            raise ConfigurationError(
                "Each source mount must contain "
                "source_id and root_env."
            )

        source_id = item.get("source_id")
        root_env = item.get("root_env")

        if (
            not isinstance(source_id, str)
            or not isinstance(root_env, str)
        ):
            raise ConfigurationError(
                "Source mount values must be strings."
            )

        if source_id in seen:
            raise ConfigurationError(
                "Duplicate source ID in configuration."
            )

        seen.add(source_id)
        mounts.append(
            SourceMount(
                source_id=source_id,
                root_env=root_env,
            )
        )

    expected_by_source = profile.by_source
    expected_ids = set(expected_by_source)
    if seen != expected_ids:
        raise ConfigurationError(
            "Configuration must mount exactly "
            "the selected static exposure profile."
        )

    for mount in mounts:
        expected = expected_by_source[mount.source_id]

        if mount.root_env != expected.root_env:
            raise ConfigurationError(
                "Configuration cannot redefine "
                "a source root variable."
            )

    return Settings(
        config_path=path,
        config_version=profile.config_version,
        profile=profile.profile_id,
        sources=tuple(mounts),
    )


def _validate_relative_path(
    value: str,
    *,
    label: str,
) -> None:
    path = PurePosixPath(value)

    if (
        path.is_absolute()
        or ".." in path.parts
        or not path.parts
    ):
        raise ConfigurationError(
            f"Invalid relative path in frozen profile: {label}"
        )

    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ConfigurationError(
            f"Unsupported extension in frozen profile: {label}"
        )


def _is_descendant(candidate: Path, root: Path) -> bool:
    try:
        candidate.relative_to(root)
    except ValueError:
        return False
    return True


def _read_source_identity(
    root: Path,
    source: ProfileSource,
) -> VerifiedSourceIdentity:
    declaration = root / "SYSTEM.yaml"
    authorized = AuthorizedRead(
        requested_uri=f"startup://identity/{source.source_id}",
        resource_family="source_identity",
        source_id=source.source_id,
        logical_id="SYSTEM.yaml",
        canonical_path=declaration,
        content_media_type="application/yaml",
        maximum_bytes=SYSTEM_DECLARATION_MAX_BYTES,
        authority="configuration",
        codec="yaml",
    )

    try:
        raw = FilesystemAdapter().read(authorized)
    except GatewayError as exc:
        raise ConfigurationError(
            "Source identity declaration cannot be read.",
            details={
                "source_id": source.source_id,
                "cause": exc.error_code,
            },
        ) from exc

    try:
        decoded = raw.content.decode("utf-8")
        payload = yaml.safe_load(decoded)
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise ConfigurationError(
            "Source identity declaration is not valid UTF-8 YAML.",
            details={"source_id": source.source_id},
        ) from exc

    if not isinstance(payload, dict):
        raise ConfigurationError(
            "Source identity declaration must be one mapping.",
            details={"source_id": source.source_id},
        )

    repository = payload.get("repository")
    if not isinstance(repository, dict):
        repository = {}

    expected = source.identity
    actual = {
        "schema_version": payload.get("schema_version"),
        "declaration_id": payload.get("id"),
        "repository_id": repository.get("id"),
        "github": repository.get("github"),
        "system": payload.get("system"),
    }
    required = {
        "schema_version": expected.schema_version,
        "declaration_id": expected.declaration_id,
        "repository_id": expected.repository_id,
        "github": expected.github,
        "system": expected.system,
    }

    mismatches = sorted(
        key
        for key, expected_value in required.items()
        if actual.get(key) != expected_value
    )

    if mismatches:
        raise ConfigurationError(
            "Mounted source identity does not match "
            "the selected static profile.",
            details={
                "source_id": source.source_id,
                "mismatched_fields": mismatches,
            },
        )

    return VerifiedSourceIdentity(
        schema_version=expected.schema_version,
        declaration_id=expected.declaration_id,
        repository_id=expected.repository_id,
        github=expected.github,
        system=expected.system,
        declaration_sha256=raw.sha256,
    )


def _preflight_manifest_locator(source: SourceSpec) -> None:
    profile = source.manifest_profile
    if profile is None:
        return

    probe = profile.locator.replace(
        "{manifest_id}",
        "preflight",
    )
    candidate = (
        source.root
        .joinpath(*PurePosixPath(probe).parts)
        .resolve(strict=False)
    )

    if (
        candidate == source.root
        or not _is_descendant(candidate, source.root)
    ):
        raise ConfigurationError(
            "Manifest locator resolves outside its source root.",
            details={"source_id": source.source_id},
        )

    if candidate.suffix.lower() not in source.allowed_extensions:
        raise ConfigurationError(
            "Manifest locator uses an unsupported extension.",
            details={"source_id": source.source_id},
        )


def _preflight_documents(
    registry: SourceRegistry,
    *,
    contract_version: str,
    profile_id: str,
) -> None:
    kernel = ResourceKernel(
        registry,
        contract_version=contract_version,
        profile_id=profile_id,
    )

    for source in registry.list_sources():
        _preflight_manifest_locator(source)

        for document in source.documents:
            uri = (
                "matias-context://source/"
                f"{source.source_id}/document/{document.document_id}"
            )
            try:
                kernel.read(uri)
            except GatewayError as exc:
                raise ConfigurationError(
                    "Mapped startup resource failed preflight.",
                    details={
                        "source_id": source.source_id,
                        "document_id": document.document_id,
                        "cause": exc.error_code,
                    },
                ) from exc


def build_registry(
    settings: Settings,
    *,
    environ: Mapping[str, str] | None = None,
) -> SourceRegistry:
    env = os.environ if environ is None else environ
    selected_profile = _selected_profile(
        settings.config_version,
        settings.profile,
    )
    mount_by_id = {
        mount.source_id: mount
        for mount in settings.sources
    }

    specs: list[SourceSpec] = []

    for profile_source in selected_profile.sources:
        mount = mount_by_id[profile_source.source_id]
        root_value = env.get(mount.root_env)

        if not root_value:
            raise ConfigurationError(
                "A required source root "
                "environment variable is missing."
            )

        root = (
            Path(root_value)
            .expanduser()
            .resolve(strict=False)
        )

        if not root.exists() or not root.is_dir():
            raise ConfigurationError(
                "A configured source root does not "
                "exist or is not a directory."
            )

        root = root.resolve(strict=True)
        identity = _read_source_identity(
            root,
            profile_source,
        )

        document_ids: set[str] = set()

        for document in profile_source.documents:
            if document.document_id in document_ids:
                raise ConfigurationError(
                    "Duplicate document ID in selected profile."
                )

            document_ids.add(document.document_id)

            _validate_relative_path(
                document.relative_path,
                label=(
                    f"{profile_source.source_id}/"
                    f"{document.document_id}"
                ),
            )

        manifest_profile = profile_source.manifest_profile

        if manifest_profile is not None:
            locator_probe = manifest_profile.locator.replace(
                "{manifest_id}",
                "probe",
            )

            _validate_relative_path(
                locator_probe,
                label=(
                    f"{profile_source.source_id}/"
                    f"{manifest_profile.producer_id}"
                ),
            )

            if (
                manifest_profile.locator.count(
                    "{manifest_id}"
                )
                != 1
            ):
                raise ConfigurationError(
                    "Manifest locator must contain exactly "
                    "one manifest_id slot."
                )

        specs.append(
            SourceSpec(
                source_id=profile_source.source_id,
                display_name=profile_source.display_name,
                role=profile_source.role,
                authority=profile_source.authority,
                root=root,
                documents=profile_source.documents,
                maximum_bytes=HARD_MAX_BYTES,
                allowed_extensions=SUPPORTED_EXTENSIONS,
                manifest_profile=manifest_profile,
                identity=identity,
            )
        )

    registry = SourceRegistry(specs)
    _preflight_documents(
        registry,
        contract_version=selected_profile.config_version,
        profile_id=selected_profile.profile_id,
    )
    return registry


def load_registry(
    config_path: str | Path | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> SourceRegistry:
    settings = load_settings(
        config_path,
        environ=environ,
    )

    return build_registry(
        settings,
        environ=environ,
    )
