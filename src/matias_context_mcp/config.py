"""Strict loading of the server-owned v0.1 mount configuration."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from .errors import ConfigurationError
from .models import SourceSpec
from .profile import (
    CONFIG_VERSION,
    FROZEN_PROFILE,
    HARD_MAX_BYTES,
    PROFILE_BY_SOURCE,
    PROFILE_ID,
    SUPPORTED_EXTENSIONS,
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

    if payload.get("config_version") != CONFIG_VERSION:
        raise ConfigurationError(
            "Unsupported configuration version."
        )

    if payload.get("profile") != PROFILE_ID:
        raise ConfigurationError(
            "Unsupported source exposure profile."
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

    expected_ids = set(PROFILE_BY_SOURCE)
    if seen != expected_ids:
        raise ConfigurationError(
            "Configuration must mount exactly "
            "the frozen four-source profile."
        )

    for mount in mounts:
        expected = PROFILE_BY_SOURCE[mount.source_id]

        if mount.root_env != expected.root_env:
            raise ConfigurationError(
                "Configuration cannot redefine "
                "a source root variable."
            )

    return Settings(
        config_path=path,
        config_version=CONFIG_VERSION,
        profile=PROFILE_ID,
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


def build_registry(
    settings: Settings,
    *,
    environ: Mapping[str, str] | None = None,
) -> SourceRegistry:
    env = os.environ if environ is None else environ
    mount_by_id = {
        mount.source_id: mount
        for mount in settings.sources
    }

    specs: list[SourceSpec] = []

    for profile_source in FROZEN_PROFILE:
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

        document_ids: set[str] = set()

        for document in profile_source.documents:
            if document.document_id in document_ids:
                raise ConfigurationError(
                    "Duplicate document ID in frozen profile."
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
            )
        )

    return SourceRegistry(specs)


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
