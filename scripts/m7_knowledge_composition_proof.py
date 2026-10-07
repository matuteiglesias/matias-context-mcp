#!/usr/bin/env python3
"""M7 end-to-end proof: Knowledge Inspect -> evidence -> KB Artifacts -> MCP."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from matias_context_mcp.profile import V01_PROFILE, PROFILE_BY_SOURCE
from smoke_fixture import write_source_fixture

RUN_ID = "m7-knowledge-inspect-fixture"
MCP_URI = f"matias-context://manifest/kb-artifacts/{RUN_ID}"


def _run(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path.name}")
    return value


def _build_gateway_config(
    root: Path,
    *,
    knowledge_inspect_root: Path,
    kb_artifacts_root: Path,
) -> tuple[Path, dict[str, str]]:
    environment = dict(os.environ)
    mounts: list[dict[str, str]] = []

    for source in V01_PROFILE.sources:
        if source.source_id == "knowledge-inspect":
            source_root = knowledge_inspect_root
        elif source.source_id == "kb-artifacts":
            source_root = kb_artifacts_root
        else:
            source_root = root / source.source_id
            write_source_fixture(source, source_root)

        environment[source.root_env] = str(source_root)
        mounts.append(
            {
                "source_id": source.source_id,
                "root_env": source.root_env,
            }
        )

    config = root / "gateway.json"
    config.write_text(
        json.dumps(
            {
                "config_version": V01_PROFILE.config_version,
                "profile": V01_PROFILE.profile_id,
                "sources": mounts,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    environment["MATIAS_CONTEXT_GATEWAY_CONFIG"] = str(
        config.resolve()
    )
    environment["PYTHONPATH"] = str(
        Path(__file__).resolve().parents[1] / "src"
    )
    return config, environment


def prove(
    *,
    knowledge_inspect_root: Path,
    kb_artifacts_root: Path,
    evidence_output: Path,
) -> dict[str, Any]:
    repository = Path(__file__).resolve().parents[1]
    knowledge_inspect_root = knowledge_inspect_root.resolve()
    kb_artifacts_root = kb_artifacts_root.resolve()
    run_root = (
        kb_artifacts_root
        / "artifacts"
        / "runs"
        / RUN_ID
    )

    if run_root.exists():
        raise RuntimeError(
            f"KB Artifacts proof run already exists: {run_root}"
        )

    consumer_env = dict(os.environ)
    consumer_env["PYTHONPATH"] = str(
        kb_artifacts_root / "src"
    )
    proof = _run(
        [
            sys.executable,
            str(
                kb_artifacts_root
                / "tools"
                / "verify_knowledge_inspect_adapter.py"
            ),
            "--producer-root",
            str(knowledge_inspect_root),
            "--output-root",
            str(run_root),
        ],
        cwd=kb_artifacts_root,
        env=consumer_env,
    )
    if proof.returncode != 0:
        raise RuntimeError(
            "KB Artifacts composition proof failed: "
            + (proof.stderr.strip() or proof.stdout.strip())
        )

    receipt = _load_json(
        run_root / "m7-proof-receipt.json"
    )
    manifest = _load_json(
        run_root / "manifest.json"
    )

    if receipt.get("physical_path_leakage") is not False:
        raise RuntimeError(
            "consumer proof did not establish path privacy"
        )
    if (
        receipt.get("producer_adapter_contract")
        != "producer-local:knowledge-inspect.evidence-jsonl@1"
    ):
        raise RuntimeError(
            "unexpected Knowledge Inspect adapter contract"
        )
    if manifest.get("counts", {}).get("selected") != 1:
        raise RuntimeError(
            "expected one selected evidence record"
        )

    partitions = manifest.get("matched_partitions")
    if (
        not isinstance(partitions, list)
        or len(partitions) != 1
        or not isinstance(partitions[0], dict)
    ):
        raise RuntimeError(
            "expected one logical manifest partition"
        )
    partition = partitions[0]
    if "path" in partition:
        raise RuntimeError(
            "KB Artifacts manifest contains a physical path"
        )
    if partition.get("source_id") != "chunk:1":
        raise RuntimeError(
            "KB Artifacts manifest lost logical source identity"
        )
    if (
        partition.get("sha256")
        != receipt.get("manifest_input_sha256")
        or partition.get("sha256")
        != receipt.get("producer_adapter_output_sha256")
    ):
        raise RuntimeError(
            "Inspect adapter -> Artifacts checksum continuity failed"
        )

    with tempfile.TemporaryDirectory(
        prefix="m7-mcp-"
    ) as temp:
        temp_root = Path(temp)
        _, gateway_env = _build_gateway_config(
            temp_root,
            knowledge_inspect_root=knowledge_inspect_root,
            kb_artifacts_root=kb_artifacts_root,
        )

        mctx = _run(
            [
                sys.executable,
                "-m",
                "matias_context_mcp.client_cli",
                "read",
                MCP_URI,
            ],
            cwd=repository,
            env=gateway_env,
        )
        if mctx.returncode != 0:
            raise RuntimeError(
                "MCP manifest read failed: "
                + (mctx.stderr.strip() or mctx.stdout.strip())
            )
        envelope = json.loads(mctx.stdout)

    mcp_manifest = envelope.get("data", {}).get("json")
    if mcp_manifest != manifest:
        raise RuntimeError(
            "MCP response does not preserve the verified KB Artifacts manifest"
        )
    if envelope.get("resource", {}).get("producer_id") != "kb-artifacts":
        raise RuntimeError(
            "MCP response has unexpected producer identity"
        )
    if envelope.get("resource", {}).get("logical_id") != RUN_ID:
        raise RuntimeError(
            "MCP response has unexpected run identity"
        )

    serialized = json.dumps(
        envelope,
        ensure_ascii=False,
        sort_keys=True,
    )
    for forbidden in (
        str(knowledge_inspect_root),
        str(kb_artifacts_root),
    ):
        if forbidden in serialized:
            raise RuntimeError(
                "MCP response leaked a physical producer root"
            )

    report = {
        "contract": "m7.knowledge-composition-mcp-proof@1",
        "run_id": RUN_ID,
        "mcp_uri": MCP_URI,
        "producer_adapter_contract": receipt[
            "producer_adapter_contract"
        ],
        "producer_adapter_output_sha256": receipt[
            "producer_adapter_output_sha256"
        ],
        "manifest_input_sha256": receipt[
            "manifest_input_sha256"
        ],
        "selected_evidence_artifact_id": receipt[
            "selected_evidence_artifact_id"
        ],
        "selected_count": manifest["counts"]["selected"],
        "logical_partition_source_id": partition[
            "source_id"
        ],
        "mcp_manifest_sha256": envelope["resource"][
            "sha256"
        ],
        "checks": {
            "inspect_to_evidence_checksum_continuity": True,
            "generic_selector_path_only": True,
            "logical_manifest_provenance": True,
            "mcp_manifest_round_trip": True,
            "physical_root_leakage": False,
        },
    }

    evidence_output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    evidence_output.write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--knowledge-inspect-root",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--kb-artifacts-root",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--evidence-output",
        type=Path,
        default=Path(
            "artifacts/m7-knowledge-composition/report.json"
        ),
    )
    args = parser.parse_args()

    try:
        report = prove(
            knowledge_inspect_root=args.knowledge_inspect_root,
            kb_artifacts_root=args.kb_artifacts_root,
            evidence_output=args.evidence_output,
        )
    except Exception as exc:
        sys.stderr.write(
            json.dumps(
                {
                    "error_code": (
                        "m7_knowledge_composition_failed"
                    ),
                    "message": str(exc),
                },
                sort_keys=True,
            )
            + "\n"
        )
        return 1

    sys.stdout.write(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
