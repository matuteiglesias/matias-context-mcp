from __future__ import annotations

from pathlib import Path

import mcp.types as types
from mcp.server.lowlevel import NotificationOptions

from matias_context_mcp.config import (
    Settings,
    SourceMount,
)
from matias_context_mcp.profile import (
    CONFIG_VERSION,
    FROZEN_PROFILE,
    PROFILE_ID,
)
from matias_context_mcp.server import build_server


def _settings_and_environment(
    tmp_path: Path,
) -> tuple[Settings, dict[str, str]]:
    mounts: list[SourceMount] = []
    environment: dict[str, str] = {}

    for profile_source in FROZEN_PROFILE:
        root = tmp_path / profile_source.source_id
        root.mkdir()

        mounts.append(
            SourceMount(
                source_id=profile_source.source_id,
                root_env=profile_source.root_env,
            )
        )
        environment[profile_source.root_env] = str(root)

    settings = Settings(
        config_path=tmp_path / "unused.json",
        config_version=CONFIG_VERSION,
        profile=PROFILE_ID,
        sources=tuple(mounts),
    )

    return settings, environment


def test_server_announces_only_resources(
    tmp_path: Path,
) -> None:
    settings, environment = (
        _settings_and_environment(tmp_path)
    )

    server = build_server(
        settings,
        environ=environment,
    )

    capabilities = server.get_capabilities(
        NotificationOptions(
            resources_changed=False,
        ),
        {},
    )

    assert capabilities.resources is not None
    assert capabilities.resources.subscribe is False
    assert capabilities.resources.listChanged is False

    assert capabilities.tools is None
    assert capabilities.prompts is None
    assert capabilities.logging is None
    assert capabilities.completions is None


def test_server_registers_only_resource_handlers(
    tmp_path: Path,
) -> None:
    settings, environment = (
        _settings_and_environment(tmp_path)
    )

    server = build_server(
        settings,
        environ=environment,
    )

    assert (
        types.ListResourcesRequest
        in server.request_handlers
    )
    assert (
        types.ListResourceTemplatesRequest
        in server.request_handlers
    )
    assert (
        types.ReadResourceRequest
        in server.request_handlers
    )

    assert (
        types.ListToolsRequest
        not in server.request_handlers
    )
    assert (
        types.ListPromptsRequest
        not in server.request_handlers
    )
    assert (
        types.SetLevelRequest
        not in server.request_handlers
    )
