from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


URI = (
    "matias-context://source/context-routing/"
    "document/published-source-catalog"
)
VERSIONED_CATALOG = Path("static/context-data/v1/sources.json")
COMPATIBILITY_ALIAS = Path("static/context-data/sources.json")


def _fail(message: str) -> None:
    raise RuntimeError(message)


def _producer_commit(root: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--producer-root", required=True)
    parser.add_argument("--expected-commit", required=True)
    args = parser.parse_args()

    root = Path(args.producer_root).resolve(strict=True)
    actual_commit = _producer_commit(root)
    if actual_commit != args.expected_commit:
        _fail(
            "Context Routing checkout does not match the pinned producer commit: "
            f"expected {args.expected_commit}, got {actual_commit}"
        )

    catalog_path = root / VERSIONED_CATALOG
    raw = catalog_path.read_bytes()
    producer_catalog = json.loads(raw.decode("utf-8"))

    if producer_catalog.get("schema_id") != "context_catalog":
        _fail("Producer catalog schema_id is not context_catalog")
    if producer_catalog.get("schema_version") != "1":
        _fail("Producer catalog schema_version is not 1")
    sources = producer_catalog.get("sources")
    if not isinstance(sources, list):
        _fail("Producer catalog sources is not a list")
    if producer_catalog.get("count") != len(sources):
        _fail("Producer catalog count does not match source list")

    alias_path = root / COMPATIBILITY_ALIAS
    if alias_path.exists() and alias_path.read_bytes() != raw:
        _fail("Context Routing compatibility alias differs from v1 catalog bytes")

    result = subprocess.run(
        ["mctx", "read", URI],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        _fail(f"MCP read failed with exit code {result.returncode}")

    gateway = json.loads(result.stdout)
    resource = gateway.get("resource", {})
    gateway_catalog = gateway.get("data", {}).get("json")
    expected_sha256 = hashlib.sha256(raw).hexdigest()

    expected_resource = {
        "source_id": "context-routing",
        "logical_id": "published-source-catalog",
        "authority": "routing",
        "content_media_type": "application/json",
        "sha256": expected_sha256,
    }
    for key, expected in expected_resource.items():
        if resource.get(key) != expected:
            _fail(
                f"Gateway resource {key} mismatch: "
                f"expected {expected!r}, got {resource.get(key)!r}"
            )

    if gateway_catalog != producer_catalog:
        _fail(
            "Gateway normalized catalog differs from the pinned producer public catalog"
        )

    summary = {
        "status": "PASS",
        "producer_repository": "matuteiglesias/context-routing",
        "producer_commit": actual_commit,
        "artifact": VERSIONED_CATALOG.as_posix(),
        "artifact_sha256": expected_sha256,
        "contract": "context_catalog@1",
        "source_count": len(sources),
        "gateway_uri": URI,
        "transport": "MCP stdio via mctx",
        "compatibility_alias_byte_identical": alias_path.exists(),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
