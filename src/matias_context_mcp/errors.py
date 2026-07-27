"""Stable domain errors for the gateway kernel."""

from __future__ import annotations

from typing import Any, Mapping


class GatewayError(Exception):
    """Base class for machine-readable gateway failures."""

    error_code = "internal_error"
    rpc_code = -32603

    def __init__(
        self,
        message: str,
        *,
        resource_uri: str | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.resource_uri = resource_uri
        self.details = dict(details or {})

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
        }
        if self.resource_uri is not None:
            payload["resource_uri"] = self.resource_uri
        return payload


class InvalidURIError(GatewayError):
    error_code = "invalid_uri"
    rpc_code = -32602


class UnknownSourceError(GatewayError):
    error_code = "unknown_source"
    rpc_code = -32002


class UnknownProducerError(GatewayError):
    error_code = "unknown_producer"
    rpc_code = -32002


class ResourceNotFoundError(GatewayError):
    error_code = "resource_not_found"
    rpc_code = -32002


class UnknownDocumentError(GatewayError):
    error_code = "unknown_document"
    rpc_code = -32002


class OutsideAllowedRootError(GatewayError):
    error_code = "outside_allowed_root"
    rpc_code = -32010


class UnsupportedFormatError(GatewayError):
    error_code = "unsupported_format"
    rpc_code = -32011


class ResourceTooLargeError(GatewayError):
    error_code = "resource_too_large"
    rpc_code = -32012


class MalformedJSONError(GatewayError):
    error_code = "malformed_json"
    rpc_code = -32013


class MalformedManifestError(GatewayError):
    error_code = "malformed_manifest"
    rpc_code = -32014


class ConfigurationError(GatewayError):
    error_code = "configuration_error"
    rpc_code = -32603
