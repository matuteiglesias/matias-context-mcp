"""Validated registry of configured source roots."""

from __future__ import annotations

from collections.abc import Iterable

from .errors import (
    ConfigurationError,
    UnknownProducerError,
    UnknownSourceError,
)
from .models import SourceSpec


class SourceRegistry:
    def __init__(self, sources: Iterable[SourceSpec]) -> None:
        self._sources = tuple(sources)

        source_map: dict[str, SourceSpec] = {}
        producer_map: dict[str, SourceSpec] = {}

        for source in self._sources:
            if source.source_id in source_map:
                raise ConfigurationError(
                    "Duplicate source ID in registry."
                )

            source_map[source.source_id] = source

            profile = source.manifest_profile
            if profile is not None:
                if profile.producer_id in producer_map:
                    raise ConfigurationError(
                        "Duplicate producer ID in registry."
                    )
                producer_map[profile.producer_id] = source

        self._source_map = source_map
        self._producer_map = producer_map

    def list_sources(self) -> tuple[SourceSpec, ...]:
        return self._sources

    def get_source(
        self,
        source_id: str,
        *,
        resource_uri: str | None = None,
    ) -> SourceSpec:
        try:
            return self._source_map[source_id]
        except KeyError as exc:
            raise UnknownSourceError(
                "Unknown configured source.",
                resource_uri=resource_uri,
            ) from exc

    def get_producer(
        self,
        producer_id: str,
        *,
        resource_uri: str | None = None,
    ) -> SourceSpec:
        try:
            return self._producer_map[producer_id]
        except KeyError as exc:
            raise UnknownProducerError(
                "Unknown configured manifest producer.",
                resource_uri=resource_uri,
            ) from exc
