from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from matias_context_mcp.config import build_registry, load_settings
from matias_context_mcp.errors import (
    InvalidURIError,
    MalformedJSONError,
    MalformedManifestError,
    ResourceIntegrityError,
)
from matias_context_mcp.kernel import ResourceKernel
from matias_context_mcp.profile import V02_PROFILE, V03_PROFILE
from matias_context_mcp.resolver import parse_resource_uri
from tests.helpers import provision_profile


RUN_ID = "selection-media-fixture"
URI = f"matias-context://selected/kb-artifacts/{RUN_ID}"


def _config(
    tmp_path: Path,
    profile,
    mounts: list[dict[str, str]],
) -> Path:
    path = tmp_path / f"{profile.profile_id}.json"
    path.write_text(
        json.dumps(
            {
                "config_version": profile.config_version,
                "profile": profile.profile_id,
                "sources": mounts,
            }
        ),
        encoding="utf-8",
    )
    return path


def _kernel(
    tmp_path: Path,
    profile=V03_PROFILE,
) -> tuple[ResourceKernel, dict[str, Path]]:
    env, roots, mounts = provision_profile(tmp_path, profile)
    settings = load_settings(
        _config(tmp_path, profile, mounts),
        environ=env,
    )
    registry = build_registry(settings, environ=env)
    return (
        ResourceKernel(
            registry,
            contract_version=settings.config_version,
            profile_id=settings.profile,
        ),
        roots,
    )


def _write_selection(
    root: Path,
    *,
    body: str | None = None,
    include_checksum: bool = True,
) -> tuple[Path, Path]:
    run_root = root / "artifacts" / "runs" / RUN_ID
    run_root.mkdir(parents=True)
    if body is None:
        body = (
            json.dumps(
                {
                    "record_id": "media-summary:fixture",
                    "source_kind": "chunk",
                    "title": "Inflación en dos canales",
                    "summary": "Resumen gobernado sobre inflación.",
                    "annotations": {
                        "source_id": "futurock-youtube",
                        "key_points": [
                            "Inflación desacelera",
                            "Actividad débil",
                        ],
                    },
                    "tags": ["media-monitor"],
                    "timestamp": "2026-08-30T18:30:00+00:00",
                    "provenance": {
                        "partition": "corpus:media-monitor-m7/chunk:1",
                        "line_number": 1,
                        "text_sha256": "0" * 64,
                        "source_ref": "media-summary:fixture",
                    },
                    "selection_reasons": [
                        "from:2026-08-29",
                        "to:2026-08-31",
                        "text_match",
                    ],
                    "artifact_family": None,
                    "artifact_maturity": None,
                },
                sort_keys=True,
            )
            + "\n"
        )
    selected = run_root / "selected.jsonl"
    selected.write_text(body, encoding="utf-8")
    manifest = {
        "selection_request": {
            "corpus": "media-monitor-m7",
            "from": "2026-08-29",
            "to": "2026-08-31",
            "text_pattern": "inflaci[oó]n",
        },
        "generated_at": "2026-10-07T23:00:00Z",
        "matched_partitions": [
            {
                "source_kind": "chunk",
                "source_id": "chunk:1",
                "sha256": "1" * 64,
            }
        ],
        "counts": {
            "scanned": 1,
            "invalid": 0,
            "deduplicated": 0,
            "selected": 1,
        },
        "outputs": [
            "selected.jsonl",
            "selected.csv",
            "artifact.md",
            "manifest.json",
        ],
    }
    if include_checksum:
        manifest["output_checksums"] = {
            "selected.jsonl": hashlib.sha256(
                body.encode("utf-8")
            ).hexdigest()
        }
    manifest_path = run_root / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )
    return selected, manifest_path


def test_v03_selected_evidence_is_manifest_bound_and_path_safe(
    tmp_path: Path,
) -> None:
    kernel, roots = _kernel(tmp_path)
    _write_selection(roots["kb-artifacts"])

    envelope = kernel.read_envelope(URI)

    assert envelope["contract_version"] == V03_PROFILE.config_version
    assert envelope["resource"]["family"] == "selected_evidence"
    assert envelope["resource"]["producer_id"] == "kb-artifacts"
    assert envelope["resource"]["logical_id"] == RUN_ID
    assert envelope["data"]["records"][0]["record_id"] == "media-summary:fixture"
    assert envelope["data"]["records"][0]["annotations"]["key_points"][0] == "Inflación desacelera"
    assert envelope["data"]["integrity"]["verified"] is True
    assert envelope["data"]["selection"]["selection_request"]["corpus"] == "media-monitor-m7"
    assert envelope["data"]["selection"]["counts"]["selected"] == 1
    assert envelope["data"]["integrity"]["selected_evidence_artifact_id"] == (
        "selected-evidence.sha256." + envelope["resource"]["sha256"]
    )
    assert (
        envelope["data"]["integrity"]["selected_sha256"]
        == envelope["resource"]["sha256"]
    )

    serialized = json.dumps(envelope, ensure_ascii=False)
    assert str(roots["kb-artifacts"]) not in serialized


def test_selected_evidence_drift_fails_closed(
    tmp_path: Path,
) -> None:
    kernel, roots = _kernel(tmp_path)
    selected, _ = _write_selection(roots["kb-artifacts"])
    selected.write_text('{"drifted": true}\n', encoding="utf-8")

    with pytest.raises(ResourceIntegrityError):
        kernel.read_envelope(URI)


def test_selected_evidence_requires_manifest_checksum(
    tmp_path: Path,
) -> None:
    kernel, roots = _kernel(tmp_path)
    _write_selection(
        roots["kb-artifacts"],
        include_checksum=False,
    )

    with pytest.raises(MalformedManifestError):
        kernel.read_envelope(URI)


def test_selected_evidence_requires_named_corpus_manifest(
    tmp_path: Path,
) -> None:
    kernel, roots = _kernel(tmp_path)
    _, manifest_path = _write_selection(roots["kb-artifacts"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["selection_request"].pop("corpus")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(MalformedManifestError):
        kernel.read_envelope(URI)


def test_selected_evidence_count_mismatch_fails_closed(
    tmp_path: Path,
) -> None:
    kernel, roots = _kernel(tmp_path)
    _, manifest_path = _write_selection(roots["kb-artifacts"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["counts"]["selected"] = 2
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ResourceIntegrityError):
        kernel.read_envelope(URI)


def test_selected_evidence_malformed_ndjson_fails_after_integrity_check(
    tmp_path: Path,
) -> None:
    kernel, roots = _kernel(tmp_path)
    _write_selection(
        roots["kb-artifacts"],
        body="{not-json}\n",
    )

    with pytest.raises(MalformedJSONError):
        kernel.read_envelope(URI)


def test_v02_does_not_expose_selected_evidence(
    tmp_path: Path,
) -> None:
    kernel, roots = _kernel(tmp_path, V02_PROFILE)
    _write_selection(roots["kb-artifacts"])

    with pytest.raises(InvalidURIError):
        kernel.read_envelope(URI)


@pytest.mark.parametrize(
    "uri",
    [
        "matias-context://selected/kb-artifacts/..",
        "matias-context://selected/kb-artifacts/%2Fetc%2Fpasswd",
        "matias-context://selected/kb-artifacts/C:%5CWindows",
    ],
)
def test_selected_evidence_rejects_traversal_shaped_ids(
    uri: str,
) -> None:
    with pytest.raises(InvalidURIError):
        parse_resource_uri(uri)
