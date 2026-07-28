"""Everyday command-line client for the gateway's MCP resources."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Sequence

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.shared.exceptions import McpError
from pydantic import ValidationError


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ValueError(message)


def _arguments(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = _ArgumentParser(prog="mctx")
    commands = parser.add_subparsers(dest="operation", required=True)
    commands.add_parser("list")
    commands.add_parser("templates")
    read = commands.add_parser("read")
    read.add_argument("uri")
    return parser.parse_args(argv)


def _json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def _error_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True) + "\n"


def _model(value: Any) -> dict[str, Any]:
    return value.model_dump(mode="json", by_alias=True, exclude_none=True)


def _server_parameters() -> StdioServerParameters:
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "matias_context_mcp"],
        env=dict(os.environ),
        cwd=Path.cwd(),
    )


async def _run(args: argparse.Namespace) -> Any:
    async with stdio_client(_server_parameters(), errlog=sys.stderr) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            if args.operation == "list":
                return _model(await session.list_resources())
            if args.operation == "templates":
                return _model(await session.list_resource_templates())

            result = await session.read_resource(args.uri)
            if len(result.contents) != 1 or not hasattr(result.contents[0], "text"):
                raise RuntimeError("The server returned an unsupported resource response.")
            return json.loads(result.contents[0].text)


def _error_payload(error: McpError) -> dict[str, Any]:
    data = error.error.data
    if isinstance(data, dict) and isinstance(data.get("error_code"), str):
        return data
    return {
        "error_code": "mcp_error",
        "message": str(error.error.message)[:512],
        "details": {"rpc_code": error.error.code},
    }


def _mcp_error(error: BaseException) -> McpError | None:
    if isinstance(error, McpError):
        return error
    if isinstance(error, BaseExceptionGroup):
        for nested in error.exceptions:
            found = _mcp_error(nested)
            if found is not None:
                return found
    return None


def _contains(error: BaseException, expected: type[BaseException]) -> bool:
    if isinstance(error, expected):
        return True
    return isinstance(error, BaseExceptionGroup) and any(
        _contains(nested, expected) for nested in error.exceptions
    )


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = _arguments(argv)
    except (ValueError, SystemExit):
        sys.stderr.write(_error_json({
            "error_code": "invalid_invocation",
            "message": "Use: mctx list | mctx templates | mctx read URI",
            "details": {},
        }))
        return 64

    try:
        output = asyncio.run(_run(args))
    except (json.JSONDecodeError, RuntimeError):
        sys.stderr.write(_error_json({
            "error_code": "invalid_mcp_response",
            "message": "The MCP server returned an invalid resource response.",
            "details": {},
        }))
        return 1
    except Exception as exc:
        error = _mcp_error(exc)
        if error is not None:
            payload = _error_payload(error)
        elif _contains(exc, ValidationError):
            payload = {
                "error_code": "invalid_uri",
                "message": "The resource URI is invalid.",
                "details": {},
            }
        else:
            payload = {
                "error_code": "mcp_session_failed",
                "message": "The MCP stdio session failed.",
                "details": {},
            }
        sys.stderr.write(_error_json(payload))
        return 1

    sys.stdout.write(_json(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
