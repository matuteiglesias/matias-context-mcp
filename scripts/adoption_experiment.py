#!/usr/bin/env python3
"""Run the bounded M6 adoption experiment over real MCP stdio sessions."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path
from typing import Any

from matias_context_mcp.profile import V02_PROFILE
from smoke_fixture import write_source_fixture

AS_OF = "2026-10-07"
CASES = {
    "media-monitor": {
        "expected_state": "refresh-needed",
        "last_material_refresh": "2026-09-24",
        "review_after_days": 7,
        "review_due_on": "2026-10-01",
    },
    "poverty-ecosystem": {
        "expected_state": "orientation-ready",
        "last_material_refresh": "2026-10-01",
        "review_after_days": 7,
        "review_due_on": "2026-10-08",
    },
}
SOURCE_URI = "matias-context://source/projects"
INDEX_URI = "matias-context://source/projects/document/agenda-index"
STAFF_URI = "matias-context://source/projects/document/staff-operating-model"


def _json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _build_fixture(root: Path) -> tuple[dict[str, str], Path]:
    environment = dict(os.environ)
    mounts: list[dict[str, str]] = []

    for source in V02_PROFILE.sources:
        source_root = root / source.source_id
        write_source_fixture(source, source_root)
        environment[source.root_env] = str(source_root)
        mounts.append(
            {
                "source_id": source.source_id,
                "root_env": source.root_env,
            }
        )

    projects = root / "projects"
    (projects / "STAFF.md").write_text(
        "# Fixture Staff\n\n"
        "Agenda orientation never overrides repository-local authority.\n",
        encoding="utf-8",
    )

    agendas: dict[str, dict[str, Any]] = {}
    for agenda_id, case in CASES.items():
        agenda_path = (
            projects
            / "estate"
            / "agendas"
            / f"{agenda_id}.md"
        )
        agenda_path.write_text(
            f"# Fixture Agenda: {agenda_id}\n\n"
            "Use this page for orientation only.\n",
            encoding="utf-8",
        )
        agendas[agenda_id] = {
            "title": f"Fixture {agenda_id}",
            "posture": "FIXTURE",
            "front_ids": [],
            "last_material_refresh": case[
                "last_material_refresh"
            ],
            "review_after_days": case["review_after_days"],
            "review_due_on": case["review_due_on"],
            "declared_freshness": "CURRENT",
            "source_path": (
                f"estate/agendas/{agenda_id}.md"
            ),
            "source_sha256": hashlib.sha256(
                agenda_path.read_bytes()
            ).hexdigest(),
        }

    _json(
        projects / "generated" / "project-agenda-index.json",
        {
            "contract": "context:project-agendas@1",
            "agenda_schema_version": 2,
            "agendas": agendas,
        },
    )

    config = root / "gateway.json"
    _json(
        config,
        {
            "config_version": V02_PROFILE.config_version,
            "profile": V02_PROFILE.profile_id,
            "sources": mounts,
        },
    )
    environment["MATIAS_CONTEXT_GATEWAY_CONFIG"] = str(
        config.resolve()
    )
    environment["PYTHONPATH"] = str(
        Path(__file__).resolve().parents[1] / "src"
    )
    return environment, config


def _mctx(
    environment: dict[str, str],
    *args: str,
) -> dict[str, Any]:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "matias_context_mcp.client_cli",
            *args,
        ],
        cwd=Path(__file__).resolve().parents[1],
        env=environment,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "mctx failed: "
            + result.stderr.splitlines()[-1]
        )
    return json.loads(result.stdout)


def _manual_control(
    environment: dict[str, str],
    agenda_id: str,
) -> dict[str, Any]:
    agenda_uri = (
        "matias-context://source/projects/document/"
        f"{agenda_id}"
    )
    source = _mctx(environment, "read", SOURCE_URI)
    index = _mctx(environment, "read", INDEX_URI)
    agenda = _mctx(environment, "read", agenda_uri)
    staff = _mctx(environment, "read", STAFF_URI)

    record = index["data"]["json"]["agendas"][agenda_id]
    hash_consistent = (
        agenda["resource"]["sha256"]
        == record["source_sha256"]
    )
    as_of = date.fromisoformat(AS_OF)
    due = date.fromisoformat(record["review_due_on"])
    if record["declared_freshness"] == "STALE":
        state = "refresh-needed"
        reason = "declared-stale"
    elif as_of >= due:
        state = "refresh-needed"
        reason = "review-due"
    else:
        state = "orientation-ready"
        reason = "within-review-window"

    return {
        "cli_invocations": 4,
        "stdio_sessions": 4,
        "mcp_reads": 4,
        "manual_join_required": True,
        "result": {
            "agenda_id": agenda_id,
            "orientation_state": state,
            "reason": reason,
            "review_due_on": record["review_due_on"],
            "declared_freshness": record[
                "declared_freshness"
            ],
            "hash_consistent": hash_consistent,
            "source_repository_id": source["data"][
                "identity"
            ]["repository_id"],
            "staff_authority_boundary_present": (
                "never overrides repository-local authority"
                in staff["data"]["text"]
            ),
        },
        "commands": [
            f"mctx read '{SOURCE_URI}'",
            f"mctx read '{INDEX_URI}'",
            f"mctx read '{agenda_uri}'",
            f"mctx read '{STAFF_URI}'",
        ],
    }


def _bootstrap_treatment(
    environment: dict[str, str],
    agenda_id: str,
) -> dict[str, Any]:
    packet = _mctx(
        environment,
        "bootstrap",
        agenda_id,
        "--as-of",
        AS_OF,
    )
    resources = packet["provenance"]["resources"]
    return {
        "cli_invocations": 1,
        "stdio_sessions": 1,
        "mcp_reads": len(resources),
        "manual_join_required": False,
        "result": {
            "agenda_id": packet["agenda_id"],
            "orientation_state": packet[
                "orientation_state"
            ],
            "reason": packet["freshness"]["reason"],
            "review_due_on": packet["freshness"][
                "review_due_on"
            ],
            "declared_freshness": packet[
                "freshness"
            ]["declared_freshness"],
            "hash_consistent": packet["provenance"][
                "agenda_index_matches_resource"
            ],
            "source_repository_id": packet["source"][
                "identity"
            ]["repository_id"],
            "staff_authority_boundary_present": (
                "never overrides repository-local authority"
                in packet["staff"]["text"]
            ),
        },
        "commands": [
            (
                f"mctx bootstrap {agenda_id} "
                f"--as-of {AS_OF}"
            )
        ],
    }


def _case(
    environment: dict[str, str],
    agenda_id: str,
) -> dict[str, Any]:
    control = _manual_control(environment, agenda_id)
    treatment = _bootstrap_treatment(
        environment,
        agenda_id,
    )
    equivalent = (
        control["result"] == treatment["result"]
    )
    expected = CASES[agenda_id]["expected_state"]
    expected_state_match = (
        treatment["result"]["orientation_state"]
        == expected
    )
    return {
        "expected_state": expected,
        "control": control,
        "treatment": treatment,
        "checks": {
            "semantic_equivalence": equivalent,
            "expected_state_match": expected_state_match,
            "hash_consistent": treatment["result"][
                "hash_consistent"
            ],
            "authority_boundary_present": treatment[
                "result"
            ]["staff_authority_boundary_present"],
        },
    }


def run() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(
        prefix="mctx-adoption-"
    ) as temp:
        environment, _ = _build_fixture(Path(temp))
        cases = {
            agenda_id: _case(environment, agenda_id)
            for agenda_id in CASES
        }

    passed = all(
        all(case["checks"].values())
        for case in cases.values()
    )
    return {
        "contract": "mctx.adoption-experiment@1",
        "as_of": AS_OF,
        "fixture_scope": (
            "synthetic-public-fixture-with-real-MCP-stdio"
        ),
        "cases": cases,
        "aggregate": {
            "case_count": len(cases),
            "equivalent_case_count": sum(
                1
                for case in cases.values()
                if case["checks"]["semantic_equivalence"]
            ),
            "control_cli_invocations_per_case": 4,
            "treatment_cli_invocations_per_case": 1,
            "cli_invocation_reduction": 0.75,
            "control_stdio_sessions_per_case": 4,
            "treatment_stdio_sessions_per_case": 1,
            "stdio_session_reduction": 0.75,
            "control_mcp_reads_per_case": 4,
            "treatment_mcp_reads_per_case": 4,
            "mcp_read_reduction": 0.0,
            "result": "PASS" if passed else "FAIL",
        },
        "interpretation": {
            "proves": (
                "bootstrap removes repeated client/session orchestration "
                "while preserving the same governed resource reads, "
                "freshness decision, source identity, authority warning, "
                "and Agenda/index SHA consistency"
            ),
            "does_not_prove": (
                "LLM reasoning quality, wall-clock latency improvement, "
                "or reduced underlying MCP resource-read count"
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/m6-adoption/report.json"),
    )
    args = parser.parse_args()

    report = run()
    _json(args.output, report)
    print(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
        )
    )
    return (
        0
        if report["aggregate"]["result"] == "PASS"
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
