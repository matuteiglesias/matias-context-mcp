"""Thin MCP stdio facade over the governed resource kernel."""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from collections.abc import Mapping

import mcp.types as types
from mcp.server.lowlevel import (
    NotificationOptions,
    Server,
)
from mcp.server.lowlevel.helper_types import (
    ReadResourceContents,
)
from mcp.server.stdio import stdio_server
from mcp.shared.exceptions import McpError
from pydantic import AnyUrl

from .config import (
    Settings,
    build_registry,
    load_settings,
)
from .errors import GatewayError
from .kernel import ResourceKernel
from .profile import CONFIG_VERSION

SERVER_NAME = "matias-context-gateway"
SERVER_VERSION = "0.1.0"

CATALOG_URI = "matias-context://catalog/sources"
SOURCE_TEMPLATE = "matias-context://source/{source_id}"
DOCUMENT_TEMPLATE = (
    "matias-context://source/"
    "{source_id}/document/{document_id}"
)
MANIFEST_TEMPLATE = (
    "matias-context://manifest/"
    "{producer_id}/{manifest_id}"
)

INSTRUCTIONS = """
Read-only gateway over governed Matías context documents and
producer manifests.

Clients use logical resource URIs. The server does not expose
physical paths, arbitrary filesystem traversal, tools, prompts,
shell execution, mutations, or unrestricted queries.
""".strip()

logger = logging.getLogger(__name__)


def build_server(
    settings: Settings,
    *,
    environ: Mapping[str, str] | None = None,
) -> Server:
    """Construct the MCP server from validated settings."""

    registry = build_registry(
        settings,
        environ=environ,
    )
    kernel = ResourceKernel(registry)

    server = Server(
        SERVER_NAME,
        version=SERVER_VERSION,
        instructions=INSTRUCTIONS,
    )

    @server.list_resources()
    async def list_resources() -> list[types.Resource]:
        return [
            types.Resource(
                uri=CATALOG_URI,
                name="configured-context-sources",
                title="Configured context sources",
                description=(
                    "The four source identities configured "
                    "for gateway contract v0.1."
                ),
                mimeType="application/json",
            )
        ]

    @server.list_resource_templates()
    async def list_resource_templates(
    ) -> list[types.ResourceTemplate]:
        return [
            types.ResourceTemplate(
                uriTemplate=SOURCE_TEMPLATE,
                name="source-descriptor",
                title="Source descriptor",
                description=(
                    "Role, authority and exposed logical "
                    "documents for one configured source."
                ),
                mimeType="application/json",
            ),
            types.ResourceTemplate(
                uriTemplate=DOCUMENT_TEMPLATE,
                name="context-document",
                title="Governed context document",
                description=(
                    "A specifically mapped context document "
                    "with bounded provenance."
                ),
                mimeType="application/json",
            ),
            types.ResourceTemplate(
                uriTemplate=MANIFEST_TEMPLATE,
                name="producer-manifest",
                title="Governed producer manifest",
                description=(
                    "A known producer manifest addressed by "
                    "a validated logical manifest ID."
                ),
                mimeType="application/json",
            ),
        ]

    @server.read_resource()
    async def read_resource(
        uri: AnyUrl,
    ) -> list[ReadResourceContents]:
        logical_uri = str(uri)

        try:
            envelope = kernel.read_envelope(logical_uri)

        except GatewayError as exc:
            raise _mcp_error(exc) from exc

        except Exception as exc:
            logger.error(
                "Unexpected resource failure for %s",
                logical_uri,
            )

            safe_error = GatewayError(
                "Internal server failure.",
                resource_uri=logical_uri,
            )

            raise _mcp_error(safe_error) from exc

        return [
            ReadResourceContents(
                content=json.dumps(
                    envelope,
                    indent=2,
                    sort_keys=True,
                ),
                mime_type="application/json",
                meta={
                    "contract_version": CONFIG_VERSION,
                    "resource_family":
                        envelope["resource"]["family"],
                },
            )
        ]

    return server


def _mcp_error(
    error: GatewayError,
) -> McpError:
    return McpError(
        types.ErrorData(
            code=error.rpc_code,
            message=error.message,
            data=error.to_payload(),
        )
    )


async def run_stdio() -> None:
    settings = load_settings()
    server = build_server(settings)

    initialization_options = (
        server.create_initialization_options(
            notification_options=NotificationOptions(
                resources_changed=False,
            ),
            experimental_capabilities={},
        )
    )

    async with stdio_server() as (
        read_stream,
        write_stream,
    ):
        await server.run(
            read_stream,
            write_stream,
            initialization_options,
        )


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stderr,
        format=(
            "%(asctime)s "
            "%(levelname)s "
            "%(name)s "
            "%(message)s"
        ),
    )


def _emit_startup_error(
    error: GatewayError,
) -> None:
    payload = {
        "event": "server_startup_failed",
        "outcome": "error",
        **error.to_payload(),
    }

    sys.stderr.write(
        json.dumps(
            payload,
            sort_keys=True,
        )
        + "\n"
    )


def main() -> None:
    _configure_logging()

    try:
        asyncio.run(run_stdio())

    except GatewayError as exc:
        _emit_startup_error(exc)
        raise SystemExit(2) from exc

    except KeyboardInterrupt:
        raise SystemExit(130)

    except Exception:
        sys.stderr.write(
            json.dumps(
                {
                    "event": "server_startup_failed",
                    "outcome": "error",
                    "error_code": "internal_error",
                    "message":
                        "Unexpected server startup failure.",
                },
                sort_keys=True,
            )
            + "\n"
        )
        raise SystemExit(1)


if __name__ == "__main__":
    main()
