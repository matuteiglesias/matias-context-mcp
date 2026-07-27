"""Bounded binary reads for policy-approved resources only."""

from __future__ import annotations

import hashlib
import os
import stat
from datetime import UTC, datetime

from ..errors import (
    ResourceNotFoundError,
    ResourceTooLargeError,
)
from ..models import AuthorizedRead, RawResource


class FilesystemAdapter:
    """Read an AuthorizedRead; never accept a raw path."""

    def read(
        self,
        authorized: AuthorizedRead,
    ) -> RawResource:
        flags = (
            os.O_RDONLY
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0)
        )

        try:
            file_descriptor = os.open(
                authorized.canonical_path,
                flags,
            )
        except OSError as exc:
            raise ResourceNotFoundError(
                "Authorized resource cannot be opened.",
                resource_uri=authorized.requested_uri,
            ) from exc

        try:
            file_stat = os.fstat(file_descriptor)

            if not stat.S_ISREG(file_stat.st_mode):
                raise ResourceNotFoundError(
                    "Authorized resource is not "
                    "a regular file.",
                    resource_uri=authorized.requested_uri,
                )

            if file_stat.st_size > authorized.maximum_bytes:
                raise ResourceTooLargeError(
                    "Resource exceeds the configured "
                    "size limit.",
                    resource_uri=authorized.requested_uri,
                    details={
                        "maximum_bytes":
                            authorized.maximum_bytes,
                    },
                )

            content = _read_at_most(
                file_descriptor,
                authorized.maximum_bytes + 1,
            )

            if len(content) > authorized.maximum_bytes:
                raise ResourceTooLargeError(
                    "Resource exceeds the configured "
                    "size limit.",
                    resource_uri=authorized.requested_uri,
                    details={
                        "maximum_bytes":
                            authorized.maximum_bytes,
                    },
                )
        finally:
            os.close(file_descriptor)

        modified_at = (
            datetime
            .fromtimestamp(file_stat.st_mtime, tz=UTC)
            .isoformat()
            .replace("+00:00", "Z")
        )

        return RawResource(
            authorized=authorized,
            content=content,
            size_bytes=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
            modified_at=modified_at,
        )


def _read_at_most(
    file_descriptor: int,
    maximum_bytes: int,
) -> bytes:
    chunks: list[bytes] = []
    remaining = maximum_bytes

    while remaining > 0:
        chunk = os.read(
            file_descriptor,
            min(65_536, remaining),
        )

        if not chunk:
            break

        chunks.append(chunk)
        remaining -= len(chunk)

    return b"".join(chunks)
