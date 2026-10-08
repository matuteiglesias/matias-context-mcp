from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from matias_context_mcp.profile import V02_PROFILE, V03_PROFILE
from tests.helpers import provision_profile


RUN_ID = "media-inflation-three-day"


def _environment(tmp_path: Path, profile) -> tuple[dict[str, str], dict[str, Path]]:
    env = dict(os.environ)
    profile_env, roots, mounts = provision_profile(tmp_path, profile)
    env.update(profile_env)
    config = tmp_path / f"{profile.profile_id}.json"
    config.write_text(
        json.dumps({
            "config_version": profile.config_version,
            "profile": profile.profile_id,
            "sources": mounts,
        }),
        encoding="utf-8",
    )
    env["MATIAS_CONTEXT_GATEWAY_CONFIG"] = str(config.resolve())
    env["PYTHONPATH"] = str(Path(__file__).parents[1] / "src")
    return env, roots


def _write_selection(root: Path) -> None:
    run = root / "artifacts" / "runs" / RUN_ID
    run.mkdir(parents=True)
    rows = [
        {
            "record_id": "media-summary:a",
            "source_kind": "chunk",
            "title": "Canal A",
            "summary": "La inflación desacelera mientras la actividad sigue débil.",
            "annotations": {
                "source_id": "el-destape-youtube",
                "key_points": ["Inflación desacelera", "Actividad débil"],
            },
            "tags": ["media-monitor", "youtube"],
            "timestamp": "2026-10-06T10:00:00+00:00",
            "provenance": {
                "source_ref": "media-summary:a",
                "partition": "corpus:media-monitor/chunk:1",
                "line_number": 1,
                "text_sha256": "a" * 64,
            },
            "selection_reasons": ["from:2026-10-05", "to:2026-10-07", "text_match"],
            "artifact_family": None,
            "artifact_maturity": None,
        },
        {
            "record_id": "media-summary:b",
            "source_kind": "chunk",
            "title": "Canal B",
            "summary": "También se señala que la inflación desacelera, con consumo débil.",
            "annotations": {
                "source_id": "futurock-youtube",
                "key_points": ["Inflación desacelera", "Consumo débil"],
            },
            "tags": ["media-monitor", "youtube"],
            "timestamp": "2026-10-06T11:00:00+00:00",
            "provenance": {
                "source_ref": "media-summary:b",
                "partition": "corpus:media-monitor/chunk:1",
                "line_number": 2,
                "text_sha256": "b" * 64,
            },
            "selection_reasons": ["from:2026-10-05", "to:2026-10-07", "text_match"],
            "artifact_family": None,
            "artifact_maturity": None,
        },
    ]
    body = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
    (run / "selected.jsonl").write_text(body, encoding="utf-8")
    manifest = {
        "selection_request": {
            "corpus": "media-monitor",
            "from": "2026-10-05",
            "to": "2026-10-07",
            "text_pattern": "inflaci[oó]n",
        },
        "generated_at": "2026-10-07T23:50:00+00:00",
        "matched_partitions": [
            {"source_kind": "chunk", "source_id": "chunk:1", "sha256": "c" * 64}
        ],
        "counts": {"scanned": 2, "invalid": 0, "deduplicated": 0, "selected": 2},
        "outputs": ["selected.jsonl", "selected.csv", "artifact.md", "manifest.json"],
        "output_checksums": {
            "selected.jsonl": hashlib.sha256(body.encode("utf-8")).hexdigest()
        },
    }
    (run / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def _mctx(env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "matias_context_mcp.client_cli", *args],
        cwd=Path(__file__).parents[1],
        env=env,
        text=True,
        capture_output=True,
        timeout=15,
        check=False,
    )


def test_evidence_command_returns_one_validated_synthesis_packet(tmp_path: Path) -> None:
    env, roots = _environment(tmp_path, V03_PROFILE)
    _write_selection(roots["kb-artifacts"])

    result = _mctx(env, "evidence", RUN_ID)

    assert result.returncode == 0, result.stderr
    packet = json.loads(result.stdout)
    assert packet["contract"] == "mctx.evidence@1"
    assert packet["selection_id"] == RUN_ID
    assert packet["record_count"] == 2
    assert packet["selection"]["selection_request"]["text_pattern"] == "inflaci[oó]n"
    assert packet["integrity"]["verified"] is True
    assert packet["integrity"]["selected_evidence_artifact_id"].startswith(
        "selected-evidence.sha256."
    )
    assert {row["annotations"]["source_id"] for row in packet["records"]} == {
        "el-destape-youtube",
        "futurock-youtube",
    }
    assert all(str(root) not in result.stdout + result.stderr for root in roots.values())


def test_evidence_command_requires_v03(tmp_path: Path) -> None:
    env, roots = _environment(tmp_path, V02_PROFILE)
    _write_selection(roots["kb-artifacts"])

    result = _mctx(env, "evidence", RUN_ID)

    assert result.returncode != 0
    failure = json.loads(result.stderr.splitlines()[-1])
    assert failure["error_code"] == "evidence_requires_v03"


@pytest.mark.parametrize("selection_id", ["..", "bad/id", "a..b"])
def test_evidence_command_rejects_unsafe_selection_ids(tmp_path: Path, selection_id: str) -> None:
    env, _ = _environment(tmp_path, V03_PROFILE)
    result = _mctx(env, "evidence", selection_id)
    assert result.returncode == 64
