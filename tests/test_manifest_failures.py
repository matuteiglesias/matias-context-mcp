from __future__ import annotations

import json
from pathlib import Path

import pytest

from matias_context_mcp.errors import (
    MalformedJSONError,
    MalformedManifestError,
    OutsideAllowedRootError,
    ResourceNotFoundError,
    ResourceTooLargeError,
    UnknownProducerError,
)
from matias_context_mcp.kernel import ResourceKernel
from matias_context_mcp.models import (
    ManifestProfile,
    SourceSpec,
)
from matias_context_mcp.profile import HARD_MAX_BYTES
from matias_context_mcp.registry import SourceRegistry


def _knowledge_inspect_kernel(
    root: Path,
) -> ResourceKernel:
    source = SourceSpec(
        source_id="knowledge-inspect",
        display_name="Knowledge Inspect",
        role="canonical_artifact_producer",
        authority="operational",
        root=root.resolve(),
        documents=(),
        maximum_bytes=HARD_MAX_BYTES,
        allowed_extensions=frozenset({
            ".md",
            ".json",
        }),
        manifest_profile=ManifestProfile(
            producer_id="knowledge-inspect",
            manifest_producer_id="kb",
            locator=(
                "artifacts/manifests/"
                "{manifest_id}.manifest.json"
            ),
            media_type="application/json",
            codec="knowledge_inspect_manifest",
        ),
    )

    return ResourceKernel(
        SourceRegistry([source])
    )


def _kb_artifacts_kernel(
    root: Path,
) -> ResourceKernel:
    source = SourceSpec(
        source_id="kb-artifacts",
        display_name="KB Artifacts",
        role="governed_evidence_selector",
        authority="derived",
        root=root.resolve(),
        documents=(),
        maximum_bytes=HARD_MAX_BYTES,
        allowed_extensions=frozenset({
            ".md",
            ".json",
        }),
        manifest_profile=ManifestProfile(
            producer_id="kb-artifacts",
            locator=(
                "artifacts/runs/"
                "{manifest_id}/manifest.json"
            ),
            media_type="application/json",
            codec="kb_artifacts_manifest",
        ),
    )

    return ResourceKernel(
        SourceRegistry([source])
    )


def _ki_manifest_path(
    root: Path,
    manifest_id: str,
) -> Path:
    path = (
        root
        / "artifacts"
        / "manifests"
        / f"{manifest_id}.manifest.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def test_unknown_producer_is_explicit(
    tmp_path: Path,
) -> None:
    root = tmp_path / "root"
    root.mkdir()

    kernel = _knowledge_inspect_kernel(root)

    with pytest.raises(UnknownProducerError):
        kernel.read_envelope(
            "matias-context://manifest/"
            "not-real/run-1"
        )


def test_unknown_run_is_not_found(
    tmp_path: Path,
) -> None:
    root = tmp_path / "root"
    root.mkdir()

    kernel = _knowledge_inspect_kernel(root)

    with pytest.raises(ResourceNotFoundError):
        kernel.read_envelope(
            "matias-context://manifest/"
            "knowledge-inspect/run-1"
        )


def test_invalid_manifest_json_is_rejected(
    tmp_path: Path,
) -> None:
    root = tmp_path / "root"
    root.mkdir()

    _ki_manifest_path(
        root,
        "run-1",
    ).write_text(
        "{not-json",
        encoding="utf-8",
    )

    kernel = _knowledge_inspect_kernel(root)

    with pytest.raises(MalformedJSONError):
        kernel.read_envelope(
            "matias-context://manifest/"
            "knowledge-inspect/run-1"
        )


def test_missing_manifest_fields_are_rejected(
    tmp_path: Path,
) -> None:
    root = tmp_path / "root"
    root.mkdir()

    _ki_manifest_path(
        root,
        "run-1",
    ).write_text(
        json.dumps({
            "run_id": "run-1",
        }),
        encoding="utf-8",
    )

    kernel = _knowledge_inspect_kernel(root)

    with pytest.raises(MalformedManifestError):
        kernel.read_envelope(
            "matias-context://manifest/"
            "knowledge-inspect/run-1"
        )


def test_manifest_symlink_escape_is_rejected(
    tmp_path: Path,
) -> None:
    root = tmp_path / "root"
    root.mkdir()

    outside = tmp_path / "outside.manifest.json"
    outside.write_text(
        json.dumps({
            "run_id": "run-1",
            "status": "succeeded",
        }),
        encoding="utf-8",
    )

    link = _ki_manifest_path(root, "run-1")

    try:
        link.unlink(missing_ok=True)
        link.symlink_to(outside)
    except OSError:
        pytest.skip(
            "Symlinks unavailable in this environment."
        )

    kernel = _knowledge_inspect_kernel(root)

    with pytest.raises(OutsideAllowedRootError):
        kernel.read_envelope(
            "matias-context://manifest/"
            "knowledge-inspect/run-1"
        )


def test_oversized_manifest_is_rejected(
    tmp_path: Path,
) -> None:
    root = tmp_path / "root"
    root.mkdir()

    _ki_manifest_path(
        root,
        "run-1",
    ).write_bytes(
        b"x" * (HARD_MAX_BYTES + 1)
    )

    kernel = _knowledge_inspect_kernel(root)

    with pytest.raises(ResourceTooLargeError):
        kernel.read_envelope(
            "matias-context://manifest/"
            "knowledge-inspect/run-1"
        )


def test_valid_manifest_adds_summary(
    tmp_path: Path,
) -> None:
    root = tmp_path / "root"
    root.mkdir()

    _ki_manifest_path(
        root,
        "run-1",
    ).write_text(
        json.dumps({
            "schema_version": "run-record.v1",
            "producer": {"id": "kb"},
            "run_id": "run-1",
            "status": "succeeded",
            "started_at": "2026-07-27T18:00:00Z",
            "completed_at": "2026-07-27T18:10:00Z",
            "inputs": [],
            "outputs": [],
            "checksums": {},
        }),
        encoding="utf-8",
    )

    kernel = _knowledge_inspect_kernel(root)

    envelope = kernel.read_envelope(
        "matias-context://manifest/"
        "knowledge-inspect/run-1"
    )

    summary = envelope["data"]["manifest_summary"]

    assert summary["producer_id"] == (
        "knowledge-inspect"
    )
    assert summary["manifest_id"] == "run-1"
    assert summary["run_id"] == "run-1"
    assert summary["status"] == "succeeded"


def test_kb_artifacts_requires_manifest_output(
    tmp_path: Path,
) -> None:
    root = tmp_path / "root"
    root.mkdir()

    path = (
        root
        / "artifacts"
        / "runs"
        / "selection-1"
        / "manifest.json"
    )
    path.parent.mkdir(parents=True)

    path.write_text(
        json.dumps({
            "selection_request": {},
            "generated_at": "2026-07-27T18:00:00Z",
            "matched_partitions": [],
            "counts": {},
            "outputs": [
                "selected.jsonl",
            ],
        }),
        encoding="utf-8",
    )

    kernel = _kb_artifacts_kernel(root)

    with pytest.raises(MalformedManifestError):
        kernel.read_envelope(
            "matias-context://manifest/"
            "kb-artifacts/selection-1"
        )


def test_manifest_id_preserves_uppercase_in_locator(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    manifest_id = "2026-07-27T180000Z"
    fixture = (
        Path(__file__).parent / "fixtures" / "manifests"
        / "knowledge-inspect" / f"{manifest_id}.manifest.json"
    )
    path = _ki_manifest_path(root, manifest_id)
    path.write_bytes(fixture.read_bytes())

    envelope = _knowledge_inspect_kernel(root).read_envelope(
        "matias-context://manifest/knowledge-inspect/" + manifest_id
    )

    assert envelope["resource"]["logical_id"] == manifest_id
    assert envelope["data"]["json"]["run_id"] == manifest_id


def test_knowledge_inspect_producer_identity_is_exact(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    path = _ki_manifest_path(root, "run-1")
    path.write_text(json.dumps({
        "producer": "knowledge-inspect",
        "run_id": "run-1",
        "status": "succeeded",
    }), encoding="utf-8")

    with pytest.raises(MalformedManifestError):
        _knowledge_inspect_kernel(root).read_envelope(
            "matias-context://manifest/knowledge-inspect/run-1"
        )


def test_representative_kb_artifacts_fixture_uses_production_codec(
    tmp_path: Path,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    manifest_id = "selection-2026-07-27T180000Z"
    fixture = (
        Path(__file__).parent / "fixtures" / "manifests"
        / "kb-artifacts" / f"{manifest_id}.manifest.json"
    )
    target = root / "artifacts" / "runs" / manifest_id / "manifest.json"
    target.parent.mkdir(parents=True)
    target.write_bytes(fixture.read_bytes())

    envelope = _kb_artifacts_kernel(root).read_envelope(
        "matias-context://manifest/kb-artifacts/" + manifest_id
    )

    assert envelope["data"]["json"]["counts"]["selected"] == 1
