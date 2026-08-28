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


def _fail(message: str) -> None:
    raise RuntimeError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture-root", required=True)
    parser.add_argument("--provenance", required=True)
    args = parser.parse_args()

    root = Path(args.fixture_root).resolve(strict=True)
    provenance_path = Path(args.provenance).resolve(strict=True)
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))

    expected_repository = "matuteiglesias/context-routing"
    expected_contract = "context_catalog@1"
    if provenance.get("source_repository") != expected_repository:
        _fail("Fixture provenance points to an unexpected producer repository")
    if provenance.get("contract") != expected_contract:
        _fail("Fixture provenance points to an unexpected contract")
    if provenance.get("consumer_uri") != URI:
        _fail("Fixture provenance consumer URI does not match the proof URI")

    relative_path = provenance.get("source_path")
    if relative_path != "static/context-data/v1/sources.json":
        _fail("Fixture provenance does not pin the versioned v1 catalog path")

    catalog_path = root / relative_path
    raw = catalog_path.read_bytes()
    actual_sha256 = hashlib.sha256(raw).hexdigest()
    expected_sha256 = provenance.get("source_sha256")
    if actual_sha256 != expected_sha256:
        _fail(
            "Frozen public fixture SHA-256 does not match provenance: "
            f"expected {expected_sha256}, got {actual_sha256}"
        )
    if len(raw) != provenance.get("source_size_bytes"):
        _fail("Frozen public fixture size does not match provenance")

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
            "Gateway normalized catalog differs from the provenance-pinned "
            "producer public catalog"
        )

    summary = {
        "status": "PASS",
        "producer_repository": expected_repository,
        "producer_commit": provenance.get("source_commit"),
        "producer_git_blob_sha1": provenance.get("source_git_blob_sha1"),
        "artifact": relative_path,
        "artifact_sha256": expected_sha256,
        "contract": expected_contract,
        "source_count": len(sources),
        "gateway_uri": URI,
        "transport": "MCP stdio via mctx",
        "evidence_mode": "exact public fixture with pinned private-repo provenance",
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
