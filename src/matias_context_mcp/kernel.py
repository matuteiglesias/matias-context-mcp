"""Small orchestration surface reusable by MCP, CLI, or tests."""

from __future__ import annotations

from .adapters.filesystem import FilesystemAdapter
from .models import ResourceDocument
from .normalizer import normalize
from .policy import ReadPolicy
from .registry import SourceRegistry
from .resolver import parse_resource_uri


class ResourceKernel:
    def __init__(
        self,
        registry: SourceRegistry,
        *,
        filesystem: FilesystemAdapter | None = None,
    ) -> None:
        self.registry = registry
        self._policy = ReadPolicy(registry)
        self._filesystem = (
            filesystem
            or FilesystemAdapter()
        )

    def read(
        self,
        uri: str,
    ) -> ResourceDocument:
        ref = parse_resource_uri(uri)
        authorized = self._policy.authorize(ref)
        raw = self._filesystem.read(authorized)
        return normalize(raw)
