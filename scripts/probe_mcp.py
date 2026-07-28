#!/usr/bin/env python3
"""Run an MCP stdio probe and always finalize its evidence bundle."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Awaitable, Callable

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.shared.exceptions import McpError

CATALOG_URI = "matias-context://catalog/sources"
DOCUMENT_URI = "matias-context://source/kb-contracts/document/manual-overview"
REQUIRED_ENV = (
    "MATIAS_CONTEXT_GATEWAY_CONFIG", "CONTEXT_ROUTING_ROOT",
    "KB_CONTRACTS_ROOT", "KNOWLEDGE_INSPECT_ROOT", "KB_ARTIFACTS_ROOT",
)


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/mvp-evidence"))
    parser.add_argument("--knowledge-inspect-manifest-id", default=os.getenv("KNOWLEDGE_INSPECT_MANIFEST_ID"))
    parser.add_argument("--kb-artifacts-manifest-id", default=os.getenv("KB_ARTIFACTS_MANIFEST_ID"))
    return parser.parse_args()


def payload(value: Any) -> dict[str, Any]:
    return value.model_dump(mode="json", by_alias=True, exclude_none=True)


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


async def read_json(session: ClientSession, uri: str) -> dict[str, Any]:
    result = await session.read_resource(uri)
    if len(result.contents) != 1 or not hasattr(result.contents[0], "text"):
        raise AssertionError(f"Expected one text resource for {uri}.")
    return json.loads(result.contents[0].text)


async def expect_error(session: ClientSession, uri: str, code: int) -> dict[str, Any]:
    try:
        await session.read_resource(uri)
    except McpError as exc:
        result = payload(exc.error)
        if result.get("code") != code:
            raise AssertionError(f"Expected {code}, got {result.get('code')} for {uri}.")
        return result
    raise AssertionError(f"Expected an MCP error for {uri}.")


class Probe:
    def __init__(self, output: Path) -> None:
        self.output = output
        self.checks: list[dict[str, Any]] = []
        self.collected: dict[str, Any] = {}

    async def check(
        self,
        name: str,
        operation: Callable[[], Awaitable[Any]],
        *,
        required: bool = True,
    ) -> Any | None:
        try:
            result = await operation()
        except Exception as exc:
            self.checks.append({
                "name": name, "required": required,
                "status": "FAIL" if required else "SKIP",
                "detail": f"{type(exc).__name__}: {exc}",
            })
            return None
        self.checks.append({"name": name, "required": required, "status": "PASS"})
        return result

    def skip(self, name: str, detail: str) -> None:
        self.checks.append({"name": name, "required": False, "status": "SKIP", "detail": detail})

    def finalize(self) -> bool:
        summary = {
            "status": "FAIL" if any(c["required"] and c["status"] != "PASS" for c in self.checks) else "PASS",
            "checks": self.checks,
        }
        write_json(self.output / "probe-summary.json", summary)
        (self.output / "probe-output.txt").write_text(
            "\n".join(f"{c['status']} {'required' if c['required'] else 'optional'} {c['name']}" + (f": {c['detail']}" if c.get("detail") else "") for c in self.checks) + "\n",
            encoding="utf-8",
        )
        return summary["status"] == "PASS"


def server_environment() -> dict[str, str]:
    missing = [name for name in REQUIRED_ENV if not os.getenv(name)]
    if missing:
        raise RuntimeError("Missing required environment variables: " + ", ".join(missing))
    repository_src = str(Path(__file__).resolve().parents[1] / "src")
    return {
        **{name: os.environ[name] for name in REQUIRED_ENV},
        "PYTHONUNBUFFERED": "1",
        "PYTHONPATH": repository_src,
    }


async def run_session(args: argparse.Namespace, probe: Probe) -> None:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "matias_context_mcp"],
        env=server_environment(),
        cwd=Path(__file__).resolve().parents[1],
    )
    with (probe.output / "server-stderr.txt").open("w", encoding="utf-8") as errlog:
        async with stdio_client(params, errlog=errlog) as streams:
            async with ClientSession(*streams) as session:
                initialized = await session.initialize()
                init = payload(initialized)
                capabilities = payload(initialized.capabilities)
                write_json(probe.output / "initialize.json", init)
                write_json(probe.output / "capabilities.json", capabilities)

                async def capabilities_check() -> None:
                    if capabilities.get("resources") is None:
                        raise AssertionError("Resources capability missing.")
                    unexpected = [name for name in ("tools", "prompts", "logging", "completions") if capabilities.get(name) is not None]
                    if unexpected:
                        raise AssertionError("Unexpected capabilities: " + ", ".join(unexpected))
                await probe.check("resources-only capability negotiation", capabilities_check)

                resources = payload(await session.list_resources())
                templates = payload(await session.list_resource_templates())
                write_json(probe.output / "resources-list.json", resources)
                write_json(probe.output / "resource-templates-list.json", templates)

                async def discovery_check() -> None:
                    if CATALOG_URI not in {item["uri"] for item in resources["resources"]}:
                        raise AssertionError("Catalog is not listed.")
                    expected = {
                        "matias-context://source/{source_id}",
                        "matias-context://source/{source_id}/document/{document_id}",
                        "matias-context://manifest/{producer_id}/{manifest_id}",
                    }
                    actual = {item["uriTemplate"] for item in templates["resourceTemplates"]}
                    if not expected <= actual:
                        raise AssertionError("Resource templates are incomplete.")
                await probe.check("resource discovery", discovery_check)

                async def catalog_check() -> dict[str, Any]:
                    value = await read_json(session, CATALOG_URI)
                    if value["data"]["count"] != 4:
                        raise AssertionError("Catalog must contain four sources.")
                    write_json(probe.output / "source-catalog-response.json", value)
                    return value
                catalog = await probe.check("four-source catalog read", catalog_check)

                async def document_check() -> dict[str, Any]:
                    value = await read_json(session, DOCUMENT_URI)
                    required = {"uri", "source_id", "logical_id", "authority", "content_media_type", "size_bytes", "sha256", "modified_at"}
                    missing = required - value["resource"].keys()
                    if missing:
                        raise AssertionError("Missing provenance: " + ", ".join(sorted(missing)))
                    write_json(probe.output / "context-document-response.json", value)
                    return value
                document = await probe.check("KB Contracts document read", document_check)

                async def errors_check() -> dict[str, Any]:
                    cases = {
                        "unknown_source": ("matias-context://source/not-real/document/manual-overview", -32002),
                        "unknown_document": ("matias-context://source/kb-contracts/document/not-mapped", -32002),
                        "invalid_manifest_identifier": ("matias-context://manifest/knowledge-inspect/bad%2Fid", -32602),
                        "unknown_producer": ("matias-context://manifest/not-real/run-1", -32002),
                        "unknown_run": ("matias-context://manifest/knowledge-inspect/definitely-not-a-run", -32002),
                    }
                    result = {name: await expect_error(session, uri, code) for name, (uri, code) in cases.items()}
                    write_json(probe.output / "unauthorized-request-errors.json", result)
                    return result
                errors = await probe.check("governed rejection cases", errors_check)

                probe.collected.update(catalog=catalog, context_document=document, errors=errors)
                for producer, manifest_id, filename, key in (
                    ("knowledge-inspect", args.knowledge_inspect_manifest_id, "knowledge-inspect-manifest-response.json", "knowledge_inspect_manifest"),
                    ("kb-artifacts", args.kb_artifacts_manifest_id, "kb-artifacts-manifest-response.json", "kb_artifacts_manifest"),
                ):
                    if not manifest_id:
                        probe.skip(f"{producer} manifest read", "No manifest ID configured.")
                        write_json(probe.output / filename, {"status": "SKIP", "reason": "No manifest ID configured."})
                        continue
                    uri = f"matias-context://manifest/{producer}/{manifest_id}"
                    async def manifest_check(uri: str = uri, filename: str = filename, key: str = key) -> dict[str, Any]:
                        value = await read_json(session, uri)
                        write_json(probe.output / filename, value)
                        probe.collected[key] = value
                        return value
                    await probe.check(f"{producer} manifest read", manifest_check, required=False)

                async def leakage_check() -> None:
                    serialized = json.dumps(probe.collected, sort_keys=True)
                    for variable in REQUIRED_ENV[1:]:
                        if os.environ[variable] in serialized:
                            raise AssertionError(f"Physical root leaked from {variable}.")
                await probe.check("no configured root in client responses", leakage_check)


async def main_async(args: argparse.Namespace, probe: Probe) -> None:
    await probe.check("MCP session", lambda: run_session(args, probe))


def main() -> int:
    args = arguments()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    (output / "server-stderr.txt").touch()
    probe = Probe(output)
    try:
        asyncio.run(main_async(args, probe))
    except BaseException as exc:
        probe.checks.append({"name": "probe finalization", "required": True, "status": "FAIL", "detail": f"{type(exc).__name__}: {exc}"})
    finally:
        passed = probe.finalize()
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
