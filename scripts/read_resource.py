#!/usr/bin/env python3
"""Exercise the kernel against configured real roots."""

from __future__ import annotations

import json
import sys

from matias_context_mcp.config import load_registry
from matias_context_mcp.errors import GatewayError
from matias_context_mcp.kernel import ResourceKernel


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: read_resource.py <matias-context-uri>",
            file=sys.stderr,
        )
        return 64

    try:
        registry = load_registry()
        kernel = ResourceKernel(registry)
        envelope = kernel.read(
            sys.argv[1]
        ).to_envelope()

    except GatewayError as exc:
        print(
            json.dumps(
                exc.to_payload(),
                indent=2,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2

    print(
        json.dumps(
            envelope,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
