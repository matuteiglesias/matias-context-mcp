# Matías Context MCP

A thin, local, read-only MCP gateway over an existing ecosystem of governed context documents and producer manifests.

The gateway exposes logical resources through MCP without granting arbitrary filesystem access or duplicating the source systems' contracts.

## Why this exists

The underlying systems already produce and govern:

- context-source metadata;
- integration contracts;
- run records;
- manifests;
- evidence-selection artifacts;
- provenance and checksums.

Before this gateway, every AI client needed repository-specific path knowledge and custom adapters.

This project adds a narrow MCP interface:

```text
MCP client
→ logical resource URI
→ registry lookup
→ authorization
→ canonical path containment
→ bounded read
→ normalization
→ provenance-rich response
```

The source repositories remain authoritative.

## Current status

The resource-only v0.1 vertical slice is implemented and under final contract hardening.

Working:

* Python MCP server over local `stdio`;
* MCP initialization and capability negotiation;
* resources capability only;
* generated four-source catalog;
* source descriptors;
* governed context-document reads;
* explicit logical-document mappings;
* canonical root-containment checks;
* symlink-escape rejection;
* bounded UTF-8 Markdown and JSON reads;
* SHA-256, size, authority and modification metadata;
* deterministic domain errors;
* real read from KB Contracts;
* real MCP client probe;
* no tools, prompts, writes or arbitrary filesystem access.

Open before declaring the MVP complete:

* align logical `manifest_id` grammar with producer-native run IDs;
* align Knowledge Inspect manifest identity checks with its versioned public contract;
* validate the KB Artifacts codec against a real selection manifest;
* make the probe always emit a final summary on failure;
* review the initial source-line budget.

## Resource namespace

```text
matias-context://catalog/sources
matias-context://source/{source_id}
matias-context://source/{source_id}/document/{document_id}
matias-context://manifest/{producer_id}/{manifest_id}
```

The client never supplies or receives a physical filesystem path.

## Integrated systems

| Source            | Gateway role                         |
| ----------------- | ------------------------------------ |
| Context Routing   | Published routing projection         |
| KB Contracts      | Authoritative integration contracts  |
| Knowledge Inspect | Run and manifest producer            |
| KB Artifacts      | Governed evidence-selection producer |

## Trust boundary

The gateway is structurally read-only.

It does not provide:

* raw path parameters;
* recursive directory browsing;
* arbitrary filesystem reads;
* shell or subprocess execution;
* SQL;
* vector-store access;
* repository mutations;
* manifest repair;
* pipeline execution;
* prompts, tools, sampling or elicitation;
* HTTP transport or cloud deployment.

Every filesystem-backed read passes through:

1. strict URI parsing;
2. registry lookup;
3. explicit logical mapping;
4. canonical path resolution;
5. root-containment validation;
6. regular-file and format checks;
7. size enforcement;
8. bounded binary reading;
9. strict UTF-8 and format normalization.

## Requirements

* Python 3.10+
* MCP Python SDK 1.28.1
* local checkouts of the configured sources

## Installation

```bash
python3 -m pip install -e '.[dev]'
```

## Configuration

The server reads a server-owned JSON mount configuration:

```bash
export MATIAS_CONTEXT_GATEWAY_CONFIG="$PWD/config/sources.example.json"

export CONTEXT_ROUTING_ROOT="$HOME/repos/context"
export KB_CONTRACTS_ROOT="$HOME/repos/kb-contracts"
export KNOWLEDGE_INSPECT_ROOT="$HOME/repos/knowledge-inspect"
export KB_ARTIFACTS_ROOT="$HOME/repos/gpt-digests"
```

These roots are operator configuration. They are not MCP client roots and cannot be changed by a client.

## Run the server

```bash
python3 -m matias_context_mcp
```

The server uses MCP over `stdio`. Protocol traffic is the only permitted output on `stdout`; operational diagnostics go to `stderr`.

## Kernel probe

```bash
python3 scripts/read_resource.py \
  'matias-context://catalog/sources'

python3 scripts/read_resource.py \
  'matias-context://source/kb-contracts/document/manual-overview'
```

## MCP client probe

```bash
python3 scripts/probe_mcp.py \
  --output-dir artifacts/mvp-evidence
```

The probe records machine-readable initialization, capabilities, listed resources, templates, successful reads and rejection evidence.

## Tests

```bash
python3 -m pytest -q
```

## Architecture

```text
Thin MCP facade
    |
    v
Resource kernel
    ├── frozen exposure profile
    ├── source registry
    ├── URI resolver
    ├── policy gate
    ├── bounded filesystem adapter
    └── normalizer
         |
         v
Explicitly mounted source roots
```

The kernel does not import MCP SDK types and can be reused by a CLI or another transport.

## Design choices

* resources before tools;
* local `stdio` before remote transport;
* explicit mappings before dynamic discovery;
* producer-owned manifests before a universal gateway schema;
* bounded reads before broad format support;
* fail closed rather than guess;
* thin adapter rather than a new knowledge platform.

## Related systems

* KB Contracts: [https://github.com/matuteiglesias/kb-contracts](https://github.com/matuteiglesias/kb-contracts)
* Knowledge Inspect: [https://github.com/matuteiglesias/knowledge-inspect](https://github.com/matuteiglesias/knowledge-inspect)
* KB Artifacts: [https://github.com/matuteiglesias/gpt-digests](https://github.com/matuteiglesias/gpt-digests)

## Portfolio summary

> Designed and implemented a read-only MCP gateway over an existing ecosystem of governed context sources and producer manifests. The gateway uses logical resource URIs, explicit allowlists, canonical path containment, bounded reads, provenance-rich responses and a transport-independent kernel. It is validated end to end with a real MCP client over local stdio, including capability negotiation and unauthorized-access rejection.
