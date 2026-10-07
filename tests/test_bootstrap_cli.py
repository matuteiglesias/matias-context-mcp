from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from matias_context_mcp.profile import (
    V01_PROFILE,
    V02_PROFILE,
)
from tests.helpers import provision_profile


def _environment(
    tmp_path: Path,
    profile,
) -> tuple[dict[str, str], dict[str, Path]]:
    environment = dict(os.environ)
    profile_environment, roots, mounts = provision_profile(
        tmp_path,
        profile,
    )
    environment.update(profile_environment)

    config = tmp_path / f"{profile.profile_id}.json"
    config.write_text(
        json.dumps(
            {
                "config_version": profile.config_version,
                "profile": profile.profile_id,
                "sources": mounts,
            }
        ),
        encoding="utf-8",
    )
    environment["MATIAS_CONTEXT_GATEWAY_CONFIG"] = str(
        config.resolve()
    )
    environment["PYTHONPATH"] = str(
        Path(__file__).parents[1] / "src"
    )
    return environment, roots


def _mctx(
    environment: dict[str, str],
    *args: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "matias_context_mcp.client_cli",
            *args,
        ],
        cwd=Path(__file__).parents[1],
        env=environment,
        text=True,
        capture_output=True,
        timeout=15,
        check=False,
    )


def _success(
    result: subprocess.CompletedProcess[str],
) -> dict[str, Any]:
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def _failure(
    result: subprocess.CompletedProcess[str],
) -> dict[str, Any]:
    assert result.returncode != 0
    assert result.stdout == ""
    return json.loads(result.stderr.splitlines()[-1])


@pytest.fixture()
def v02_environment(
    tmp_path: Path,
) -> tuple[dict[str, str], dict[str, Path]]:
    return _environment(tmp_path, V02_PROFILE)


def test_media_bootstrap_is_refresh_due_on_2026_10_07(
    v02_environment: tuple[
        dict[str, str],
        dict[str, Path],
    ],
) -> None:
    environment, roots = v02_environment
    result = _mctx(
        environment,
        "bootstrap",
        "media-monitor",
        "--as-of",
        "2026-10-07",
    )
    packet = _success(result)

    assert packet["contract"] == "mctx.bootstrap@1"
    assert packet["agenda_id"] == "media-monitor"
    assert packet["as_of"] == "2026-10-07"
    assert packet["orientation_state"] == "refresh-needed"
    assert packet["freshness"]["declared_freshness"] == "CURRENT"
    assert packet["freshness"]["review_due_on"] == "2026-10-01"
    assert packet["freshness"]["reason"] == "review-due"
    assert packet["agenda"]["metadata"]["posture"] == "FIXTURE"
    assert packet["provenance"][
        "agenda_index_matches_resource"
    ] is True
    assert packet["warnings"][0]["code"] == "review-due"
    output = result.stdout + result.stderr
    assert all(
        str(root) not in output
        for root in roots.values()
    )


def test_poverty_bootstrap_is_ready_on_2026_10_07(
    v02_environment: tuple[
        dict[str, str],
        dict[str, Path],
    ],
) -> None:
    environment, _ = v02_environment
    packet = _success(
        _mctx(
            environment,
            "bootstrap",
            "poverty-ecosystem",
            "--as-of",
            "2026-10-07",
        )
    )

    assert packet["orientation_state"] == "orientation-ready"
    assert packet["freshness"]["review_due_on"] == "2026-10-08"
    assert packet["freshness"]["reason"] == "within-review-window"
    assert packet["agenda"]["metadata"]["posture"] == "FIXTURE"
    assert packet["warnings"] == []


def test_review_due_date_itself_requires_refresh(
    v02_environment: tuple[
        dict[str, str],
        dict[str, Path],
    ],
) -> None:
    environment, _ = v02_environment
    packet = _success(
        _mctx(
            environment,
            "bootstrap",
            "poverty-ecosystem",
            "--as-of",
            "2026-10-08",
        )
    )
    assert packet["orientation_state"] == "refresh-needed"
    assert packet["freshness"]["reason"] == "review-due"


def test_bootstrap_joins_four_ordinary_mcp_resources(
    v02_environment: tuple[
        dict[str, str],
        dict[str, Path],
    ],
) -> None:
    environment, _ = v02_environment
    packet = _success(
        _mctx(
            environment,
            "bootstrap",
            "poverty-ecosystem",
            "--as-of",
            "2026-10-07",
        )
    )

    resources = packet["provenance"]["resources"]
    assert [item["kind"] for item in resources] == [
        "source_descriptor",
        "agenda_index",
        "agenda",
        "staff_operating_model",
    ]
    assert all(
        item.get("sha256")
        or item.get("declaration_sha256")
        for item in resources
    )
    assert packet["agenda"]["text"].startswith(
        "# Fixture: poverty-ecosystem"
    )
    assert packet["staff"]["text"].startswith(
        "# Fixture: staff-operating-model"
    )


def test_bootstrap_fails_closed_on_index_resource_hash_mismatch(
    v02_environment: tuple[
        dict[str, str],
        dict[str, Path],
    ],
) -> None:
    environment, roots = v02_environment
    index_path = (
        roots["projects"]
        / "generated"
        / "project-agenda-index.json"
    )
    payload = json.loads(
        index_path.read_text(encoding="utf-8")
    )
    payload["agendas"]["poverty-ecosystem"][
        "source_sha256"
    ] = "0" * 64
    index_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    failure = _failure(
        _mctx(
            environment,
            "bootstrap",
            "poverty-ecosystem",
            "--as-of",
            "2026-10-07",
        )
    )
    assert failure["error_code"] == "agenda_index_mismatch"
    assert failure["details"]["agenda_id"] == "poverty-ecosystem"


def test_unknown_agenda_is_client_side_bootstrap_error(
    v02_environment: tuple[
        dict[str, str],
        dict[str, Path],
    ],
) -> None:
    environment, _ = v02_environment
    failure = _failure(
        _mctx(
            environment,
            "bootstrap",
            "not-an-agenda",
            "--as-of",
            "2026-10-07",
        )
    )
    assert failure["error_code"] == "unknown_agenda"


def test_portfolio_summarizes_all_agendas_without_expanding_documents(
    v02_environment: tuple[
        dict[str, str],
        dict[str, Path],
    ],
) -> None:
    environment, roots = v02_environment
    packet = _success(
        _mctx(
            environment,
            "portfolio",
            "--as-of",
            "2026-10-07",
        )
    )

    assert packet["contract"] == "mctx.portfolio@1"
    assert packet["as_of"] == "2026-10-07"
    assert packet["summary"] == {
        "total": 8,
        "refresh_needed": 1,
        "orientation_ready": 7,
    }
    assert packet["ordering"] == {
        "basis": "freshness-attention",
        "project_priority": False,
    }
    assert packet["agendas"][0]["agenda_id"] == "media-monitor"
    assert packet["agendas"][0]["reason"] == "review-due"
    assert packet["agendas"][0]["review_delta_days"] == 6
    assert packet["agendas"][1]["agenda_id"] == "poverty-ecosystem"
    assert packet["agendas"][1]["review_delta_days"] == -1
    assert [item["kind"] for item in packet["provenance"]["resources"]] == [
        "source_descriptor",
        "agenda_index",
    ]
    output = result_output = json.dumps(packet)
    assert all(
        str(root) not in result_output
        for root in roots.values()
    )


def test_portfolio_due_date_boundary_expands_refresh_set(
    v02_environment: tuple[
        dict[str, str],
        dict[str, Path],
    ],
) -> None:
    environment, _ = v02_environment
    packet = _success(
        _mctx(
            environment,
            "portfolio",
            "--as-of",
            "2026-10-08",
        )
    )

    assert packet["summary"]["refresh_needed"] == 2
    assert [
        item["agenda_id"]
        for item in packet["agendas"][:2]
    ] == [
        "media-monitor",
        "poverty-ecosystem",
    ]


def test_portfolio_declared_stale_sorts_before_review_due(
    v02_environment: tuple[
        dict[str, str],
        dict[str, Path],
    ],
) -> None:
    environment, roots = v02_environment
    index_path = (
        roots["projects"]
        / "generated"
        / "project-agenda-index.json"
    )
    payload = json.loads(
        index_path.read_text(encoding="utf-8")
    )
    payload["agendas"]["accounting-family"][
        "declared_freshness"
    ] = "STALE"
    index_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    packet = _success(
        _mctx(
            environment,
            "portfolio",
            "--as-of",
            "2026-10-07",
        )
    )

    assert packet["summary"]["refresh_needed"] == 2
    assert packet["agendas"][0]["agenda_id"] == "accounting-family"
    assert packet["agendas"][0]["reason"] == "declared-stale"
    assert packet["agendas"][1]["agenda_id"] == "media-monitor"


def test_portfolio_requires_explicit_v02_profile(
    tmp_path: Path,
) -> None:
    environment, _ = _environment(
        tmp_path,
        V01_PROFILE,
    )
    failure = _failure(
        _mctx(
            environment,
            "portfolio",
            "--as-of",
            "2026-10-07",
        )
    )
    assert failure["error_code"] == "portfolio_requires_v02"


def test_bootstrap_requires_explicit_v02_profile(
    tmp_path: Path,
) -> None:
    environment, _ = _environment(
        tmp_path,
        V01_PROFILE,
    )
    failure = _failure(
        _mctx(
            environment,
            "bootstrap",
            "media-monitor",
            "--as-of",
            "2026-10-07",
        )
    )
    assert failure["error_code"] == "bootstrap_requires_v02"


@pytest.mark.parametrize(
    "as_of",
    ["2026/10/07", "today", "2026-13-01"],
)
def test_bootstrap_requires_explicit_iso_as_of(
    v02_environment: tuple[
        dict[str, str],
        dict[str, Path],
    ],
    as_of: str,
) -> None:
    environment, _ = v02_environment
    result = _mctx(
        environment,
        "bootstrap",
        "media-monitor",
        "--as-of",
        as_of,
    )
    assert result.returncode == 64
    assert _failure(result)["error_code"] == "invalid_invocation"
