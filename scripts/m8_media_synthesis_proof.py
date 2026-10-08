#!/usr/bin/env python3
"""Media Monitor -> KB Artifacts -> MCP selected evidence -> recurrence proof."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any

from matias_context_mcp.profile import V03_PROFILE
from smoke_fixture import write_source_fixture

RUN_ID = "m7-media-monitor-fixture"


def _run(command: list[str], *, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, timeout=120, check=False)


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def _gateway_environment(root: Path, kb_root: Path) -> dict[str, str]:
    env = dict(os.environ)
    mounts = []
    for source in V03_PROFILE.sources:
        if source.source_id == "kb-artifacts":
            source_root = kb_root
        else:
            source_root = root / source.source_id
            write_source_fixture(source, source_root)
        env[source.root_env] = str(source_root)
        mounts.append({"source_id": source.source_id, "root_env": source.root_env})
    config = root / "gateway.json"
    config.write_text(json.dumps({
        "config_version": V03_PROFILE.config_version,
        "profile": V03_PROFILE.profile_id,
        "sources": mounts,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    env["MATIAS_CONTEXT_GATEWAY_CONFIG"] = str(config.resolve())
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    return env


def prove(*, media_root: Path, kb_root: Path, evidence_output: Path) -> dict[str, Any]:
    repository = Path(__file__).resolve().parents[1]
    media_root = media_root.resolve()
    kb_root = kb_root.resolve()
    run_root = kb_root / "artifacts" / "runs" / RUN_ID
    if run_root.exists():
        raise RuntimeError(f"KB Artifacts proof run already exists: {run_root}")

    env = dict(os.environ)
    env["PYTHONPATH"] = str(kb_root / "src")
    proof = _run([
        sys.executable,
        str(kb_root / "tools" / "verify_media_monitor_adapter.py"),
        "--producer-root", str(media_root),
        "--output-root", str(run_root),
    ], cwd=kb_root, env=env)
    if proof.returncode != 0:
        raise RuntimeError("KB Media proof failed: " + (proof.stderr.strip() or proof.stdout.strip()))

    kb_receipt = _load(run_root / "m7-media-proof-receipt.json")
    manifest = _load(run_root / "manifest.json")
    selected_sha = manifest.get("output_checksums", {}).get("selected.jsonl")
    if not isinstance(selected_sha, str):
        raise RuntimeError("named-corpus manifest did not bind selected.jsonl")

    with tempfile.TemporaryDirectory(prefix="m8-media-mcp-") as temp:
        gateway_env = _gateway_environment(Path(temp), kb_root)
        result = _run([
            sys.executable, "-m", "matias_context_mcp.client_cli",
            "evidence", RUN_ID,
        ], cwd=repository, env=gateway_env)
        if result.returncode != 0:
            raise RuntimeError("mctx evidence failed: " + (result.stderr.strip() or result.stdout.strip()))
        packet = json.loads(result.stdout)

    if packet.get("contract") != "mctx.evidence@1":
        raise RuntimeError("unexpected mctx evidence contract")
    if packet.get("record_count") != 2:
        raise RuntimeError("expected two selected media records")
    if packet.get("integrity", {}).get("selected_sha256") != selected_sha:
        raise RuntimeError("MCP selected-body checksum disagrees with KB manifest")

    claims: dict[str, dict[str, Any]] = {}
    channels_by_claim: dict[str, set[str]] = defaultdict(set)
    label_by_claim: dict[str, str] = {}
    for record in packet["records"]:
        annotations = record.get("annotations") or {}
        source_id = annotations.get("source_id")
        if not isinstance(source_id, str):
            raise RuntimeError("media evidence lost source identity")
        for point in annotations.get("key_points") or []:
            if not isinstance(point, str) or not point.strip():
                continue
            key = " ".join(point.casefold().split())
            label_by_claim.setdefault(key, point)
            channels_by_claim[key].add(source_id)
    for key in sorted(channels_by_claim):
        channels = sorted(channels_by_claim[key])
        if len(channels) >= 2:
            claims[key] = {
                "claim": label_by_claim[key],
                "channels": channels,
                "channel_count": len(channels),
            }

    recurring = list(claims.values())
    if recurring != [{
        "claim": "Inflación desacelera",
        "channels": ["el-destape-youtube", "futurock-youtube"],
        "channel_count": 2,
    }]:
        raise RuntimeError(f"unexpected recurring-claim projection: {recurring}")

    serialized = json.dumps(packet, ensure_ascii=False, sort_keys=True)
    for forbidden in (str(media_root), str(kb_root)):
        if forbidden in serialized:
            raise RuntimeError("MCP synthesis packet leaked a physical root")

    report = {
        "contract": "m8.media-evidence-mcp-synthesis-proof@1",
        "selection_id": RUN_ID,
        "producer_adapter_contract": kb_receipt["producer_adapter_contract"],
        "selection_window": kb_receipt["selection_window"],
        "topic_pattern": kb_receipt["topic_pattern"],
        "selected_channels": kb_receipt["selected_channels"],
        "selected_count": packet["record_count"],
        "selected_evidence_artifact_id": packet["integrity"]["selected_evidence_artifact_id"],
        "recurring_claims": recurring,
        "checks": {
            "media_owned_adapter": True,
            "generic_named_corpus_selection": True,
            "manifest_body_checksum_join": True,
            "mcp_body_round_trip": True,
            "two_channel_recurrence_reconstructable": True,
            "physical_root_leakage": False,
        },
    }
    evidence_output.parent.mkdir(parents=True, exist_ok=True)
    evidence_output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--media-monitor-root", type=Path, required=True)
    parser.add_argument("--kb-artifacts-root", type=Path, required=True)
    parser.add_argument("--evidence-output", type=Path, default=Path("artifacts/m8-media-synthesis/report.json"))
    args = parser.parse_args()
    try:
        report = prove(media_root=args.media_monitor_root, kb_root=args.kb_artifacts_root, evidence_output=args.evidence_output)
    except Exception as exc:
        sys.stderr.write(json.dumps({"error_code": "m8_media_synthesis_failed", "message": str(exc)}, sort_keys=True) + "\n")
        return 1
    sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
