from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from matias_context_mcp.profile import FROZEN_PROFILE, PROFILE_ID


@pytest.fixture()
def client_environment(tmp_path: Path) -> tuple[dict[str, str], dict[str, Path]]:
    environment = dict(os.environ)
    roots: dict[str, Path] = {}
    mounts = []

    for source in FROZEN_PROFILE:
        root = tmp_path / source.source_id
        root.mkdir()
        roots[source.source_id] = root
        environment[source.root_env] = str(root)
        mounts.append({"source_id": source.source_id, "root_env": source.root_env})

    (roots["kb-contracts"] / "README.md").write_text("# Governed contract\n", encoding="utf-8")
    (roots["knowledge-inspect"] / "artifacts/manifests").mkdir(parents=True)
    (roots["knowledge-inspect"] / "artifacts/manifests/2026-07-27T180000Z.manifest.json").write_text(
        (Path(__file__).parent / "fixtures/manifests/knowledge-inspect/2026-07-27T180000Z.manifest.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (roots["kb-artifacts"] / "artifacts/runs/selection-2026-07-27T180000Z").mkdir(parents=True)
    (roots["kb-artifacts"] / "artifacts/runs/selection-2026-07-27T180000Z/manifest.json").write_text(
        (Path(__file__).parent / "fixtures/manifests/kb-artifacts/selection-2026-07-27T180000Z.manifest.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    config = tmp_path / "gateway.json"
    config.write_text(json.dumps({
        "config_version": "mcp-context-gateway.v0.1",
        "profile": PROFILE_ID,
        "sources": mounts,
    }), encoding="utf-8")
    environment["MATIAS_CONTEXT_GATEWAY_CONFIG"] = str(config)
    environment["PYTHONPATH"] = str(Path(__file__).parents[1] / "src")
    return environment, roots


def _mctx(environment: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "matias_context_mcp.client_cli", *args],
        cwd=Path(__file__).parents[1],
        env=environment,
        text=True,
        capture_output=True,
        timeout=15,
        check=False,
    )


def _success(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def _failure(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    return json.loads(result.stderr.splitlines()[-1])


def test_list_and_templates_use_the_frozen_real_mcp_surface(
    client_environment: tuple[dict[str, str], dict[str, Path]],
) -> None:
    environment, _ = client_environment
    listed = _success(_mctx(environment, "list"))
    templates = _success(_mctx(environment, "templates"))

    assert [resource["uri"] for resource in listed["resources"]] == [
        "matias-context://catalog/sources"
    ]
    assert len(templates["resourceTemplates"]) == 3
    serialized = json.dumps((listed, templates))
    assert "tools" not in serialized
    assert "prompts" not in serialized


@pytest.mark.parametrize(
    ("uri", "family"),
    [
        ("matias-context://catalog/sources", "source_catalog"),
        ("matias-context://source/kb-contracts/document/manual-overview", "context_document"),
        ("matias-context://manifest/knowledge-inspect/2026-07-27T180000Z", "manifest"),
        ("matias-context://manifest/kb-artifacts/selection-2026-07-27T180000Z", "manifest"),
    ],
)
def test_read_returns_gateway_envelopes_over_mcp(
    client_environment: tuple[dict[str, str], dict[str, Path]],
    uri: str,
    family: str,
) -> None:
    environment, roots = client_environment
    result = _mctx(environment, "read", uri)
    envelope = _success(result)

    assert envelope["resource"]["family"] == family
    output = result.stdout + result.stderr
    assert all(str(root) not in output for root in roots.values())


@pytest.mark.parametrize(
    "uri",
    [
        "not-a-matias-context-uri",
        "matias-context://source/not-real",
    ],
)
def test_read_failure_is_structured_and_does_not_leak_roots(
    client_environment: tuple[dict[str, str], dict[str, Path]],
    uri: str,
) -> None:
    environment, roots = client_environment
    result = _mctx(environment, "read", uri)

    assert result.returncode != 0
    assert result.stdout == ""
    failure = _failure(result)
    assert failure["error_code"] in {"invalid_uri", "unknown_source"}
    assert all(str(root) not in result.stderr for root in roots.values())


def test_invalid_invocation_is_usage_error(
    client_environment: tuple[dict[str, str], dict[str, Path]],
) -> None:
    environment, _ = client_environment
    result = _mctx(environment, "read")

    assert result.returncode == 64
    assert result.stdout == ""
    assert _failure(result)["error_code"] == "invalid_invocation"


def test_client_does_not_write_files(
    client_environment: tuple[dict[str, str], dict[str, Path]],
    tmp_path: Path,
) -> None:
    environment, _ = client_environment
    before = {path.relative_to(tmp_path) for path in tmp_path.rglob("*")}
    _success(_mctx(environment, "list"))
    after = {path.relative_to(tmp_path) for path in tmp_path.rglob("*")}

    assert after == before
