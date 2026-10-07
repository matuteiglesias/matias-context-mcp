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

**resource-only v0.1 MVP: CLOSED**

**estate-orientation v0.2 profile: explicit opt-in**

v0.1 remains the four-source compatibility profile. v0.2 adds one statically
governed Projects source for estate orientation without changing the MCP
capability surface.

Working:

* Python MCP server over local `stdio`;
* MCP initialization and capability negotiation;
* resources capability only;
* exact four-source v0.1 catalog backed by verified mounted producer identities;
* explicit five-source v0.2 catalog adding the Projects orientation source;
* deterministic `mctx bootstrap` orientation packets with Agenda/index SHA reconciliation;
* deterministic `mctx portfolio` freshness-attention packets over the Agenda index;
* source descriptors with declaration provenance;
* fail-closed startup preflight of every mapped static document;
* governed context-document reads;
* explicit logical-document mappings;
* canonical root-containment checks;
* symlink-escape rejection;
* bounded UTF-8 Markdown and JSON reads;
* SHA-256, size, authority and modification metadata;
* deterministic domain errors;
* real read from KB Contracts;
* everyday and acceptance-probe MCP clients over real `stdio` sessions;
* no tools, prompts, writes or arbitrary filesystem access.

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
| Projects          | Estate / Project Agenda orientation   |

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

export CONTEXT_ROUTING_ROOT="$HOME/repos/context-routing"
export KB_CONTRACTS_ROOT="$HOME/repos/kb-contracts"
export KNOWLEDGE_INSPECT_ROOT="$HOME/repos/knowledge-inspect"
export KB_ARTIFACTS_ROOT="$HOME/repos/kb-artifacts"
```

That remains the exact v0.1 configuration. To opt into the five-source v0.2
profile instead:

```bash
export MATIAS_CONTEXT_GATEWAY_CONFIG="$PWD/config/sources.v0.2.example.json"
export PROJECTS_ROOT="$HOME/repos/projects"
```

The v0.2 contract is documented in
[`docs/mcp_context_gateway_contract_v0_2.md`](docs/mcp_context_gateway_contract_v0_2.md).

These roots are operator configuration. They are not MCP client roots and cannot be changed by a client.

Each root must present the exact governed `SYSTEM.yaml` identity pinned by the
selected static profile. Startup reads that declaration with a 64 KiB bound, verifies the
stable estate repository ID, current GitHub name, declaration ID, system ID and
schema version, then preflights every advertised static document through the same
resource kernel used for client reads. A wrong/swapped root, missing declaration,
missing document, unsafe symlink, invalid UTF-8/JSON, codec mismatch or oversized
resource prevents startup; v0.1 does not advertise a partially healthy catalog.

The current document mapping and startup rules are recorded in the
[trusted-source-preflight v0.1 amendment](docs/amendments/trusted-source-preflight-2026-10-07.md).

## Run the server

```bash
python3 -m matias_context_mcp
```

The server uses MCP over `stdio`. Protocol traffic is the only permitted output on `stdout`; operational diagnostics go to `stderr`.

## Read resources from the shell

`mctx` is the everyday client. Each command starts the configured server, initializes a real MCP session, performs one resource operation, and prints formatted JSON to `stdout`:

```bash
mctx list
mctx templates

# Catalog and source descriptor
mctx read 'matias-context://catalog/sources'
mctx read 'matias-context://source/kb-contracts'

# Governed context document
mctx read \
  'matias-context://source/knowledge-inspect/document/architecture-freeze'

# Producer manifests (replace IDs with configured, existing run IDs)
mctx read \
  'matias-context://manifest/knowledge-inspect/2026-07-27T180000Z'
mctx read \
  'matias-context://manifest/kb-artifacts/selection-2026-07-27T180000Z'

# Extract the normalized document body
mctx read \
  'matias-context://source/knowledge-inspect/document/architecture-freeze' \
  | jq -r '.data.text'

# Deterministic estate orientation (v0.2 profile only)
mctx bootstrap media-monitor --as-of 2026-10-07
mctx bootstrap poverty-ecosystem --as-of 2026-10-07
mctx portfolio --as-of 2026-10-07

# Ordinary shell redirection remains available to the operator
mctx read 'matias-context://catalog/sources' > catalog.json
```

`mctx bootstrap` performs four ordinary resource reads inside one MCP stdio
session: the Projects source descriptor, Agenda index, requested Agenda, and
`STAFF.md`. It verifies the Agenda resource SHA-256 against the producer-owned
index before composing `mctx.bootstrap@1`.

`--as-of` is mandatory. This keeps freshness evaluation explicit and
reproducible rather than depending on the machine clock. A review-due Agenda
returns `orientation_state: refresh-needed`; the command does not rewrite the
producer's semantic freshness declaration.

See [the bootstrap contract](docs/mctx_bootstrap_contract_v1.md).

`mctx portfolio` reads only the verified Projects source descriptor and Agenda
index. It derives the same review-due semantics for every Agenda and orders the
result for freshness attention; this is explicitly not a project-priority
ranking. Expand an individual room with `mctx bootstrap` only when the portfolio
packet shows it deserves attention. See
[the portfolio contract](docs/mctx_portfolio_contract_v1.md).

Successful resource envelopes go to `stdout`; diagnostics, server logs, and structured failures go to `stderr`. The client itself does not create output files—the final example uses shell redirection explicitly.

## Diagnostic and acceptance clients

The three command surfaces have deliberately different purposes:

```text
scripts/read_resource.py
    direct kernel diagnostic

mctx
    everyday real-MCP client

scripts/probe_mcp.py
    full acceptance and evidence probe
```

For a direct kernel diagnostic:

```bash
python3 scripts/read_resource.py \
  'matias-context://catalog/sources'

python3 scripts/read_resource.py \
  'matias-context://source/kb-contracts/document/manual-overview'
```

For the acceptance and evidence probe:

```bash
python3 scripts/probe_mcp.py \
  --output-dir artifacts/mvp-evidence
```

The probe records machine-readable initialization, capabilities, listed resources, templates, successful reads and rejection evidence.

## Verification

```bash
make test
make check
make bootstrap-test
make smoke
make smoke-v02
make adoption-experiment
```

`make smoke` remains the exact four-source v0.1 acceptance path.
`make smoke-v02` separately proves the five-source profile and reads the
Projects Agenda index through a real MCP stdio session. Neither requires live
producer credentials or enumerates producer run histories.


## Adoption experiment

The bounded M6 experiment compares manual reconstruction against `mctx bootstrap`
for two representative Agenda IDs, one review-due and one within-window. Both
paths read the same four governed MCP resources and must return equivalent
orientation/provenance facts.

The passing CI result is deliberately narrow:

* CLI invocations per case: **4 -> 1**;
* MCP stdio sessions per case: **4 -> 1**;
* MCP resource reads per case: **4 -> 4**.

That is a 75% reduction in client/session orchestration, not a claim of fewer
source reads, universal latency improvement, or better LLM reasoning. See
[`docs/m6_adoption_experiment_2026-10-07.md`](docs/m6_adoption_experiment_2026-10-07.md).

## Knowledge composition proof

M7 validates one producer-to-selector-to-gateway path without expanding the MCP
protocol surface:

```text
Knowledge Inspect governed summary
→ producer-owned generic evidence JSONL
→ KB Artifacts generic named-corpus selection
→ selected-evidence run / path-safe manifest
→ matias-context://manifest/kb-artifacts/<run-id>
```

The pinned CI proof preserves the producer adapter checksum into the selection
manifest, creates one content-addressed selected-evidence identity, and confirms
the MCP response leaks no producer checkout roots.

The gateway does not expose the selected evidence body and does not perform
selection or promotion. See
[`docs/m7_knowledge_composition_2026-10-07.md`](docs/m7_knowledge_composition_2026-10-07.md).

## Architecture

```text
Thin MCP facade
    |
    v
Resource kernel
    ├── explicit static exposure profile
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
* explicit versioned profiles before dynamic discovery;
* exact v0.1 compatibility before additive v0.2 exposure;
* deterministic client composition before new server capabilities;
* producer-owned manifests before a universal gateway schema;
* bounded reads before broad format support;
* fail closed rather than guess;
* thin adapter rather than a new knowledge platform.

## Related systems

* Context Routing: [https://github.com/matuteiglesias/context-routing](https://github.com/matuteiglesias/context-routing)
* KB Contracts: [https://github.com/matuteiglesias/kb-contracts](https://github.com/matuteiglesias/kb-contracts)
* Knowledge Inspect: [https://github.com/matuteiglesias/knowledge-inspect](https://github.com/matuteiglesias/knowledge-inspect)
* KB Artifacts: [https://github.com/matuteiglesias/kb-artifacts](https://github.com/matuteiglesias/kb-artifacts)
* Projects: [https://github.com/matuteiglesias/projects](https://github.com/matuteiglesias/projects)

## Portfolio summary

> Designed and implemented a read-only MCP gateway over an existing ecosystem of governed context sources and producer manifests. The gateway uses logical resource URIs, explicit allowlists, canonical path containment, bounded reads, provenance-rich responses and a transport-independent kernel. It is validated end to end with a real MCP client over local stdio, including capability negotiation and unauthorized-access rejection.
