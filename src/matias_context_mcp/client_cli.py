"""Everyday command-line client for governed MCP resources and bootstrap packets."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Sequence

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.shared.exceptions import McpError
from pydantic import ValidationError

BOOTSTRAP_CONTRACT = "mctx.bootstrap@1"
PORTFOLIO_CONTRACT = "mctx.portfolio@1"
PROJECTS_SOURCE_URI = "matias-context://source/projects"
AGENDA_INDEX_URI = "matias-context://source/projects/document/agenda-index"
STAFF_URI = "matias-context://source/projects/document/staff-operating-model"
AGENDA_URI_TEMPLATE = "matias-context://source/projects/document/{agenda_id}"
_AGENDA_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ValueError(message)


@dataclass(frozen=True, slots=True)
class BootstrapError(Exception):
    error_code: str
    message: str
    details: dict[str, Any]


def _as_of(value: str) -> str:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "--as-of must be an ISO date in YYYY-MM-DD form."
        ) from exc
    return parsed.isoformat()


def _agenda_id(value: str) -> str:
    if not _AGENDA_ID.fullmatch(value):
        raise argparse.ArgumentTypeError(
            "agenda must be a lowercase hyphenated Agenda ID."
        )
    return value


def _arguments(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = _ArgumentParser(prog="mctx")
    commands = parser.add_subparsers(dest="operation", required=True)
    commands.add_parser("list")
    commands.add_parser("templates")
    read = commands.add_parser("read")
    read.add_argument("uri")
    bootstrap = commands.add_parser("bootstrap")
    bootstrap.add_argument("agenda_id", type=_agenda_id)
    bootstrap.add_argument(
        "--as-of",
        required=True,
        type=_as_of,
        help="Explicit orientation date (YYYY-MM-DD).",
    )
    portfolio = commands.add_parser("portfolio")
    portfolio.add_argument(
        "--as-of",
        required=True,
        type=_as_of,
        help="Explicit orientation date (YYYY-MM-DD).",
    )
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


async def _read_json(
    session: ClientSession,
    uri: str,
) -> dict[str, Any]:
    result = await session.read_resource(uri)
    if len(result.contents) != 1 or not hasattr(result.contents[0], "text"):
        raise RuntimeError(
            "The server returned an unsupported resource response."
        )
    return json.loads(result.contents[0].text)


def _bootstrap_error(
    error_code: str,
    message: str,
    **details: Any,
) -> BootstrapError:
    return BootstrapError(
        error_code=error_code,
        message=message,
        details=details,
    )


def _mcp_error_code(error: McpError) -> str | None:
    data = error.error.data
    if isinstance(data, dict):
        value = data.get("error_code")
        if isinstance(value, str):
            return value
    return None


def _orientation(
    record: dict[str, Any],
    *,
    agenda_id: str,
    as_of: str,
) -> tuple[str, str, date, int]:
    declared = record.get("declared_freshness")
    due_value = record.get("review_due_on")
    try:
        due = date.fromisoformat(str(due_value))
        observed = date.fromisoformat(as_of)
    except ValueError as exc:
        raise _bootstrap_error(
            "invalid_agenda_freshness",
            "Agenda review metadata is not a valid ISO date.",
            agenda_id=agenda_id,
        ) from exc

    if declared == "STALE":
        orientation_state = "refresh-needed"
        reason = "declared-stale"
    elif observed >= due:
        orientation_state = "refresh-needed"
        reason = "review-due"
    else:
        orientation_state = "orientation-ready"
        reason = "within-review-window"

    return orientation_state, reason, due, (observed - due).days


async def _bootstrap(
    session: ClientSession,
    *,
    agenda_id: str,
    as_of: str,
) -> dict[str, Any]:
    try:
        source = await _read_json(
            session,
            PROJECTS_SOURCE_URI,
        )
    except McpError as exc:
        if _mcp_error_code(exc) == "unknown_source":
            raise _bootstrap_error(
                "bootstrap_requires_v02",
                "Bootstrap requires the explicit estate-orientation v0.2 profile.",
                required_source="projects",
            ) from exc
        raise

    index = await _read_json(session, AGENDA_INDEX_URI)

    source_data = source.get("data")
    if (
        not isinstance(source_data, dict)
        or source_data.get("source_id") != "projects"
    ):
        raise _bootstrap_error(
            "invalid_bootstrap_source",
            "Projects source descriptor is incompatible with bootstrap.",
        )

    index_payload = index.get("data", {}).get("json")
    if not isinstance(index_payload, dict):
        raise _bootstrap_error(
            "invalid_agenda_index",
            "Projects Agenda index is missing normalized JSON.",
        )

    agendas = index_payload.get("agendas")
    if not isinstance(agendas, dict):
        raise _bootstrap_error(
            "invalid_agenda_index",
            "Projects Agenda index does not contain an agendas mapping.",
        )

    record = agendas.get(agenda_id)
    if not isinstance(record, dict):
        raise _bootstrap_error(
            "unknown_agenda",
            "Requested Agenda is not present in the Projects Agenda index.",
            agenda_id=agenda_id,
        )

    agenda_uri = AGENDA_URI_TEMPLATE.format(
        agenda_id=agenda_id
    )
    agenda = await _read_json(session, agenda_uri)
    staff = await _read_json(session, STAFF_URI)

    agenda_resource = agenda.get("resource")
    if not isinstance(agenda_resource, dict):
        raise _bootstrap_error(
            "invalid_agenda_resource",
            "Agenda resource is missing provenance metadata.",
            agenda_id=agenda_id,
        )

    actual_sha = agenda_resource.get("sha256")
    expected_sha = record.get("source_sha256")
    if (
        not isinstance(actual_sha, str)
        or not isinstance(expected_sha, str)
        or actual_sha != expected_sha
    ):
        raise _bootstrap_error(
            "agenda_index_mismatch",
            "Agenda resource SHA-256 does not match the Projects Agenda index.",
            agenda_id=agenda_id,
            expected_sha256=expected_sha,
            actual_sha256=actual_sha,
        )

    if agenda_resource.get("logical_id") != agenda_id:
        raise _bootstrap_error(
            "agenda_identity_mismatch",
            "Agenda resource logical ID does not match the requested Agenda.",
            agenda_id=agenda_id,
        )

    declared = record.get("declared_freshness")
    orientation_state, reason, due, _ = _orientation(
        record,
        agenda_id=agenda_id,
        as_of=as_of,
    )

    identity = source_data.get("identity")
    if not isinstance(identity, dict):
        raise _bootstrap_error(
            "invalid_bootstrap_source",
            "Projects source descriptor is missing verified identity.",
        )

    agenda_text = agenda.get("data", {}).get("text")
    staff_text = staff.get("data", {}).get("text")
    if not isinstance(agenda_text, str) or not isinstance(staff_text, str):
        raise _bootstrap_error(
            "invalid_bootstrap_document",
            "Bootstrap documents are not normalized Markdown resources.",
            agenda_id=agenda_id,
        )

    warnings: list[dict[str, Any]] = []
    if orientation_state == "refresh-needed":
        warnings.append(
            {
                "code": reason,
                "message": (
                    "Refresh this Agenda before treating its frontier "
                    "as current execution guidance."
                ),
            }
        )

    return {
        "contract": BOOTSTRAP_CONTRACT,
        "agenda_id": agenda_id,
        "as_of": as_of,
        "orientation_state": orientation_state,
        "freshness": {
            "declared_freshness": declared,
            "last_material_refresh": record.get(
                "last_material_refresh"
            ),
            "review_after_days": record.get(
                "review_after_days"
            ),
            "review_due_on": due.isoformat(),
            "reason": reason,
        },
        "agenda": {
            "metadata": record,
            "text": agenda_text,
        },
        "staff": {
            "text": staff_text,
        },
        "source": {
            "source_id": "projects",
            "identity": identity,
        },
        "provenance": {
            "agenda_index_matches_resource": True,
            "resources": [
                {
                    "uri": PROJECTS_SOURCE_URI,
                    "kind": "source_descriptor",
                    "declaration_sha256": identity.get(
                        "declaration_sha256"
                    ),
                },
                {
                    "uri": AGENDA_INDEX_URI,
                    "kind": "agenda_index",
                    "sha256": index.get(
                        "resource", {}
                    ).get("sha256"),
                },
                {
                    "uri": agenda_uri,
                    "kind": "agenda",
                    "sha256": actual_sha,
                },
                {
                    "uri": STAFF_URI,
                    "kind": "staff_operating_model",
                    "sha256": staff.get(
                        "resource", {}
                    ).get("sha256"),
                },
            ],
        },
        "warnings": warnings,
    }


async def _portfolio(
    session: ClientSession,
    *,
    as_of: str,
) -> dict[str, Any]:
    try:
        source = await _read_json(
            session,
            PROJECTS_SOURCE_URI,
        )
    except McpError as exc:
        if _mcp_error_code(exc) == "unknown_source":
            raise _bootstrap_error(
                "portfolio_requires_v02",
                "Portfolio requires the explicit estate-orientation v0.2 profile.",
                required_source="projects",
            ) from exc
        raise

    index = await _read_json(session, AGENDA_INDEX_URI)

    source_data = source.get("data")
    if (
        not isinstance(source_data, dict)
        or source_data.get("source_id") != "projects"
    ):
        raise _bootstrap_error(
            "invalid_portfolio_source",
            "Projects source descriptor is incompatible with portfolio.",
        )

    index_payload = index.get("data", {}).get("json")
    if not isinstance(index_payload, dict):
        raise _bootstrap_error(
            "invalid_agenda_index",
            "Projects Agenda index is missing normalized JSON.",
        )

    agendas = index_payload.get("agendas")
    if not isinstance(agendas, dict):
        raise _bootstrap_error(
            "invalid_agenda_index",
            "Projects Agenda index does not contain an agendas mapping.",
        )

    identity = source_data.get("identity")
    if not isinstance(identity, dict):
        raise _bootstrap_error(
            "invalid_portfolio_source",
            "Projects source descriptor is missing verified identity.",
        )

    rows: list[dict[str, Any]] = []
    for agenda_id, record in agendas.items():
        if (
            not isinstance(agenda_id, str)
            or not _AGENDA_ID.fullmatch(agenda_id)
            or not isinstance(record, dict)
        ):
            raise _bootstrap_error(
                "invalid_agenda_index",
                "Projects Agenda index contains an invalid Agenda record.",
            )

        orientation_state, reason, due, delta_days = _orientation(
            record,
            agenda_id=agenda_id,
            as_of=as_of,
        )
        rows.append(
            {
                "agenda_id": agenda_id,
                "title": record.get("title"),
                "posture": record.get("posture"),
                "declared_freshness": record.get("declared_freshness"),
                "last_material_refresh": record.get("last_material_refresh"),
                "review_due_on": due.isoformat(),
                "review_delta_days": delta_days,
                "orientation_state": orientation_state,
                "reason": reason,
                "source_sha256": record.get("source_sha256"),
            }
        )

    reason_rank = {
        "declared-stale": 0,
        "review-due": 1,
        "within-review-window": 2,
    }
    rows.sort(
        key=lambda item: (
            0 if item["orientation_state"] == "refresh-needed" else 1,
            reason_rank[item["reason"]],
            item["review_due_on"],
            item["agenda_id"],
        )
    )

    refresh_needed = sum(
        item["orientation_state"] == "refresh-needed"
        for item in rows
    )
    orientation_ready = len(rows) - refresh_needed

    return {
        "contract": PORTFOLIO_CONTRACT,
        "as_of": as_of,
        "summary": {
            "total": len(rows),
            "refresh_needed": refresh_needed,
            "orientation_ready": orientation_ready,
        },
        "ordering": {
            "basis": "freshness-attention",
            "project_priority": False,
        },
        "agendas": rows,
        "source": {
            "source_id": "projects",
            "identity": identity,
        },
        "provenance": {
            "resources": [
                {
                    "uri": PROJECTS_SOURCE_URI,
                    "kind": "source_descriptor",
                    "declaration_sha256": identity.get(
                        "declaration_sha256"
                    ),
                },
                {
                    "uri": AGENDA_INDEX_URI,
                    "kind": "agenda_index",
                    "sha256": index.get(
                        "resource", {}
                    ).get("sha256"),
                },
            ],
        },
    }


async def _run(args: argparse.Namespace) -> Any:
    async with stdio_client(
        _server_parameters(),
        errlog=sys.stderr,
    ) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            if args.operation == "list":
                return _model(await session.list_resources())
            if args.operation == "templates":
                return _model(
                    await session.list_resource_templates()
                )
            if args.operation == "bootstrap":
                return await _bootstrap(
                    session,
                    agenda_id=args.agenda_id,
                    as_of=args.as_of,
                )
            if args.operation == "portfolio":
                return await _portfolio(
                    session,
                    as_of=args.as_of,
                )
            return await _read_json(session, args.uri)


def _error_payload(error: McpError) -> dict[str, Any]:
    data = error.error.data
    if (
        isinstance(data, dict)
        and isinstance(data.get("error_code"), str)
    ):
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


def _contains(
    error: BaseException,
    expected: type[BaseException],
) -> bool:
    if isinstance(error, expected):
        return True
    return isinstance(error, BaseExceptionGroup) and any(
        _contains(nested, expected)
        for nested in error.exceptions
    )


def _bootstrap_exception(
    error: BaseException,
) -> BootstrapError | None:
    if isinstance(error, BootstrapError):
        return error
    if isinstance(error, BaseExceptionGroup):
        for nested in error.exceptions:
            found = _bootstrap_exception(nested)
            if found is not None:
                return found
    return None


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = _arguments(argv)
    except (ValueError, SystemExit):
        sys.stderr.write(
            _error_json(
                {
                    "error_code": "invalid_invocation",
                    "message": (
                        "Use: mctx list | mctx templates | "
                        "mctx read URI | "
                        "mctx bootstrap AGENDA --as-of YYYY-MM-DD | "
                        "mctx portfolio --as-of YYYY-MM-DD"
                    ),
                    "details": {},
                }
            )
        )
        return 64

    try:
        output = asyncio.run(_run(args))
    except (json.JSONDecodeError, RuntimeError):
        sys.stderr.write(
            _error_json(
                {
                    "error_code": "invalid_mcp_response",
                    "message": (
                        "The MCP server returned an invalid "
                        "resource response."
                    ),
                    "details": {},
                }
            )
        )
        return 1
    except Exception as exc:
        bootstrap_error = _bootstrap_exception(exc)
        if bootstrap_error is not None:
            payload = {
                "error_code": bootstrap_error.error_code,
                "message": bootstrap_error.message,
                "details": bootstrap_error.details,
            }
        else:
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
