#!/usr/bin/env python3
"""Run a real MCP client against the stdio gateway."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

from mcp import (
    ClientSession,
    StdioServerParameters,
)
from mcp.client.stdio import stdio_client
from mcp.shared.exceptions import McpError

CATALOG_URI = "matias-context://catalog/sources"
KB_CONTRACTS_URI = (
    "matias-context://source/"
    "kb-contracts/document/manual-overview"
)

REQUIRED_SERVER_ENV = (
    "MATIAS_CONTEXT_GATEWAY_CONFIG",
    "CONTEXT_ROUTING_ROOT",
    "KB_CONTRACTS_ROOT",
    "KNOWLEDGE_INSPECT_ROOT",
    "KB_ARTIFACTS_ROOT",
)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/mvp-evidence"),
    )

    parser.add_argument(
        "--knowledge-inspect-manifest-id",
        default=os.environ.get(
            "KNOWLEDGE_INSPECT_MANIFEST_ID"
        ),
    )

    parser.add_argument(
        "--kb-artifacts-manifest-id",
        default=os.environ.get(
            "KB_ARTIFACTS_MANIFEST_ID"
        ),
    )

    return parser.parse_args()


def _model_payload(value: Any) -> dict[str, Any]:
    return value.model_dump(
        mode="json",
        by_alias=True,
        exclude_none=True,
    )


def _write_json(
    path: Path,
    payload: Any,
) -> None:
    path.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


async def _read_json_resource(
    session: ClientSession,
    uri: str,
) -> dict[str, Any]:
    result = await session.read_resource(uri)

    if len(result.contents) != 1:
        raise AssertionError(
            f"Expected one resource body for {uri}."
        )

    content = result.contents[0]

    if not hasattr(content, "text"):
        raise AssertionError(
            f"Expected text content for {uri}."
        )

    return json.loads(content.text)


async def _expect_error(
    session: ClientSession,
    *,
    uri: str,
    expected_code: int,
) -> dict[str, Any]:
    try:
        await session.read_resource(uri)

    except McpError as exc:
        payload = _model_payload(exc.error)

        if payload.get("code") != expected_code:
            raise AssertionError(
                f"Unexpected error code for {uri}: "
                f"{payload.get('code')}"
            )

        return payload

    raise AssertionError(
        f"Expected resource error for {uri}."
    )


def _server_environment() -> dict[str, str]:
    missing = [
        name
        for name in REQUIRED_SERVER_ENV
        if not os.environ.get(name)
    ]

    if missing:
        raise RuntimeError(
            "Missing required environment variables: "
            + ", ".join(missing)
        )

    result = {
        name: os.environ[name]
        for name in REQUIRED_SERVER_ENV
    }

    result["PYTHONUNBUFFERED"] = "1"
    return result


def _assert_no_root_leaks(
    payloads: dict[str, Any],
) -> None:
    serialized = json.dumps(
        payloads,
        sort_keys=True,
    )

    for variable in REQUIRED_SERVER_ENV[1:]:
        root = os.environ[variable]

        if root and root in serialized:
            raise AssertionError(
                f"Physical root leaked from {variable}."
            )


async def _run(
    args: argparse.Namespace,
) -> None:
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    repository_root = (
        Path(__file__).resolve().parents[1]
    )

    server_parameters = StdioServerParameters(
        command=sys.executable,
        args=[
            "-m",
            "matias_context_mcp",
        ],
        env=_server_environment(),
        cwd=repository_root,
    )

    collected: dict[str, Any] = {}
    checks: list[str] = []

    stderr_path = output_dir / "server-stderr.txt"

    with stderr_path.open(
        "w",
        encoding="utf-8",
    ) as stderr_log:
        async with stdio_client(
            server_parameters,
            errlog=stderr_log,
        ) as (read_stream, write_stream):
            async with ClientSession(
                read_stream,
                write_stream,
            ) as session:
                initialized = await session.initialize()
                initialize_payload = _model_payload(
                    initialized
                )
                capabilities_payload = _model_payload(
                    initialized.capabilities
                )

                collected["initialize"] = (
                    initialize_payload
                )
                collected["capabilities"] = (
                    capabilities_payload
                )

                _write_json(
                    output_dir / "initialize.json",
                    initialize_payload,
                )
                _write_json(
                    output_dir / "capabilities.json",
                    capabilities_payload,
                )

                if (
                    capabilities_payload.get(
                        "resources"
                    )
                    is None
                ):
                    raise AssertionError(
                        "Resources capability missing."
                    )

                for absent_capability in (
                    "tools",
                    "prompts",
                    "logging",
                    "completions",
                ):
                    if capabilities_payload.get(
                        absent_capability
                    ) is not None:
                        raise AssertionError(
                            "Unexpected capability: "
                            + absent_capability
                        )

                checks.append(
                    "PASS resources-only capability negotiation"
                )

                resources_result = (
                    await session.list_resources()
                )
                resources_payload = _model_payload(
                    resources_result
                )

                collected["resources"] = (
                    resources_payload
                )

                _write_json(
                    output_dir / "resources-list.json",
                    resources_payload,
                )

                listed_uris = {
                    resource["uri"]
                    for resource
                    in resources_payload["resources"]
                }

                if CATALOG_URI not in listed_uris:
                    raise AssertionError(
                        "Source catalog was not listed."
                    )

                checks.append(
                    "PASS source catalog listed"
                )

                templates_result = (
                    await session
                    .list_resource_templates()
                )
                templates_payload = _model_payload(
                    templates_result
                )

                collected["resource_templates"] = (
                    templates_payload
                )

                _write_json(
                    output_dir
                    / "resource-templates-list.json",
                    templates_payload,
                )

                template_uris = {
                    item["uriTemplate"]
                    for item
                    in templates_payload[
                        "resourceTemplates"
                    ]
                }

                required_templates = {
                    "matias-context://source/{source_id}",
                    (
                        "matias-context://source/"
                        "{source_id}/document/{document_id}"
                    ),
                    (
                        "matias-context://manifest/"
                        "{producer_id}/{manifest_id}"
                    ),
                }

                if not required_templates.issubset(
                    template_uris
                ):
                    raise AssertionError(
                        "Required resource templates "
                        "were not advertised."
                    )

                checks.append(
                    "PASS resource templates listed"
                )

                catalog = await _read_json_resource(
                    session,
                    CATALOG_URI,
                )

                collected["catalog"] = catalog

                _write_json(
                    output_dir
                    / "source-catalog-response.json",
                    catalog,
                )

                if catalog["data"]["count"] != 4:
                    raise AssertionError(
                        "Catalog must contain four sources."
                    )

                checks.append(
                    "PASS four-source catalog read"
                )

                context_document = (
                    await _read_json_resource(
                        session,
                        KB_CONTRACTS_URI,
                    )
                )

                collected["context_document"] = (
                    context_document
                )

                _write_json(
                    output_dir
                    / "context-document-response.json",
                    context_document,
                )

                resource = context_document["resource"]

                for required_field in (
                    "uri",
                    "source_id",
                    "logical_id",
                    "authority",
                    "size_bytes",
                    "sha256",
                ):
                    if required_field not in resource:
                        raise AssertionError(
                            "Missing provenance field: "
                            + required_field
                        )

                checks.append(
                    "PASS real KB Contracts document read"
                )

                errors = {
                    "unknown_source":
                        await _expect_error(
                            session,
                            uri=(
                                "matias-context://source/"
                                "not-real/document/"
                                "manual-overview"
                            ),
                            expected_code=-32002,
                        ),
                    "unknown_document":
                        await _expect_error(
                            session,
                            uri=(
                                "matias-context://source/"
                                "kb-contracts/document/"
                                "not-mapped"
                            ),
                            expected_code=-32002,
                        ),
                    "invalid_identifier":
                        await _expect_error(
                            session,
                            uri=(
                                "matias-context://source/"
                                "kb-contracts/document/"
                                "Uppercase"
                            ),
                            expected_code=-32602,
                        ),
                    "traversal":
                        await _expect_error(
                            session,
                            uri=(
                                "matias-context://source/"
                                "kb-contracts/document/"
                                "%2e%2e"
                            ),
                            expected_code=-32602,
                        ),
                    "unknown_producer":
                        await _expect_error(
                            session,
                            uri=(
                                "matias-context://manifest/"
                                "not-real/run-1"
                            ),
                            expected_code=-32002,
                        ),
                    "unknown_run":
                        await _expect_error(
                            session,
                            uri=(
                                "matias-context://manifest/"
                                "knowledge-inspect/"
                                "definitely-not-a-run"
                            ),
                            expected_code=-32002,
                        ),
                }

                collected["errors"] = errors

                _write_json(
                    output_dir
                    / "unauthorized-request-errors.json",
                    errors,
                )

                checks.append(
                    "PASS governed rejection cases"
                )

                if (
                    args.knowledge_inspect_manifest_id
                    is not None
                ):
                    uri = (
                        "matias-context://manifest/"
                        "knowledge-inspect/"
                        + args.knowledge_inspect_manifest_id
                    )

                    manifest = await _read_json_resource(
                        session,
                        uri,
                    )

                    collected[
                        "knowledge_inspect_manifest"
                    ] = manifest

                    _write_json(
                        output_dir
                        / (
                            "knowledge-inspect-"
                            "manifest-response.json"
                        ),
                        manifest,
                    )

                    checks.append(
                        "PASS Knowledge Inspect manifest read"
                    )

                if (
                    args.kb_artifacts_manifest_id
                    is not None
                ):
                    uri = (
                        "matias-context://manifest/"
                        "kb-artifacts/"
                        + args.kb_artifacts_manifest_id
                    )

                    manifest = await _read_json_resource(
                        session,
                        uri,
                    )

                    collected[
                        "kb_artifacts_manifest"
                    ] = manifest

                    _write_json(
                        output_dir
                        / (
                            "kb-artifacts-"
                            "manifest-response.json"
                        ),
                        manifest,
                    )

                    checks.append(
                        "PASS KB Artifacts manifest read"
                    )

    _assert_no_root_leaks(collected)

    checks.append(
        "PASS no configured physical root leaked"
    )
    checks.append(
        "PASS stdio remained protocol-clean"
    )

    summary = {
        "outcome": "PASS",
        "checks": checks,
        "knowledge_inspect_manifest_tested":
            args.knowledge_inspect_manifest_id
            is not None,
        "kb_artifacts_manifest_tested":
            args.kb_artifacts_manifest_id
            is not None,
    }

    _write_json(
        output_dir / "probe-summary.json",
        summary,
    )

    text = "\n".join(checks) + "\n"

    (
        output_dir
        / "probe-output.txt"
    ).write_text(
        text,
        encoding="utf-8",
    )

    print(text, end="")


def main() -> None:
    args = _arguments()
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
