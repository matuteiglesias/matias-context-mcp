---
title: MCP Context Gateway Contract
contract_id: mcp-context-gateway
contract_version: "0.1"
status: frozen-for-mvp
owner: Matías Iglesias
date_frozen: 2026-07-27
change_policy: "Changes require an explicit version bump or an approved contract amendment."
---

# MCP Context Gateway Contract v0.1

## 1. Contract status

This document freezes the architecture and external behavior of the first MCP Context Gateway MVP.

The implementation may choose ordinary internal details such as function names or file organization, but it must not silently change:

- the system boundary;
- the four configured source roles;
- the logical URI namespace;
- the read-only authorization model;
- the supported resource families;
- the response envelope;
- the limits;
- the domain error semantics;
- the explicitly prohibited operations.

A material change requires either:

- a documented amendment to `v0.1`, before implementation depends on it; or
- a new contract version.

## 2. Purpose

The gateway exposes a small, governed subset of Matías's knowledge-management ecosystem to MCP clients.

It provides:

- source discovery;
- source descriptors;
- mapped context documents;
- producer manifests.

It does not provide generic filesystem access and does not execute the underlying systems.

## 3. System boundary

```text
MCP client
    |
    | MCP over stdio
    v
Thin MCP facade
    |
    v
Context Resource Kernel
    |- Registry
    |- URI Resolver
    |- Policy Gate
    |- Filesystem Adapter
    |- Normalizer
    |
    v
Four configured source roots
```

### 3.1 MCP facade responsibilities

The facade may:

- initialize the MCP server;
- declare implemented capabilities;
- register fixed resources and resource templates;
- translate MCP requests into kernel calls;
- translate kernel results into MCP resource contents;
- translate domain errors into JSON-RPC errors;
- emit structured logs to `stderr`.

The facade must not:

- open files directly;
- resolve physical paths;
- implement source-specific authorization;
- contain manifest locator rules;
- duplicate document mappings;
- mutate any source.

### 3.2 Kernel responsibilities

The kernel owns:

- source registration;
- logical URI parsing;
- identity validation;
- authorization;
- logical-document resolution;
- manifest resolution;
- path canonicalization;
- boundary enforcement;
- bounded reads;
- parsing and normalization;
- provenance construction.

The kernel must not import MCP SDK types.

## 4. Integrated sources

The gateway contains exactly four source definitions in the initial profile.

### 4.1 Source IDs

| `source_id` | Display name | Ecosystem role | Authority |
|---|---|---|---|
| `context-routing` | Context Routing | discovery and routing projection | routing authority |
| `kb-contracts` | KB Contracts | decision registry and contract catalog | ecosystem contract authority |
| `knowledge-inspect` | Knowledge Inspect | canonical ingest/analyze producer | source-local operational authority |
| `kb-artifacts` | KB Artifacts | governed read-only evidence selector | source-local selection authority |

Source IDs are stable logical identities. They are not repository paths.

### 4.2 Authority precedence

When interpreting ecosystem behavior:

1. `kb-contracts` governs shared integration rules.
2. source-local public contracts govern a producer's public surface.
3. runtime manifests govern facts about a particular run.
4. `context-routing` governs published routing metadata.
5. gateway configuration governs only local mounting and exposure.

The gateway must not merge conflicting claims automatically.

## 5. MCP protocol profile

### 5.1 Transport

The MVP uses local `stdio`.

### 5.2 Capabilities

The server implements and declares only:

- `resources`, with neither `subscribe` nor `listChanged`.

The server does not implement or declare:

- MCP protocol `logging`;
- tools;
- prompts;
- completions;
- sampling;
- elicitation;
- subscriptions;
- resource list-change notifications;
- experimental capabilities.

Structured operational logs written to `stderr` are process logging, not the MCP logging capability. The gateway must not register a `logging/setLevel` handler or send MCP log-message notifications in `v0.1`.

### 5.3 Lifecycle

The MCP SDK owns:

- initialization;
- protocol version negotiation;
- capability negotiation;
- normal operation;
- shutdown.

The gateway must not hard-code or reimplement JSON-RPC lifecycle messages.

### 5.4 Standard output discipline

Because `stdout` carries the `stdio` protocol:

- protocol traffic is the only permitted `stdout` output;
- logs, diagnostics, and tracebacks go to `stderr`;
- imported modules must not print during startup.

## 6. Resource namespace

The gateway uses one custom URI scheme:

```text
matias-context
```

All URIs must conform to RFC 3986 syntax.

### 6.1 Fixed resources

#### Gateway source catalog

```text
matias-context://catalog/sources
```

Returns exactly the four configured source descriptors.

### 6.2 Resource templates

#### Source descriptor

```text
matias-context://source/{source_id}
```

#### Context document

```text
matias-context://source/{source_id}/document/{document_id}
```

#### Producer manifest

```text
matias-context://manifest/{producer_id}/{manifest_id}
```

### 6.3 URI design rules

1. URIs identify logical resources, never physical files.
2. URI components are case-sensitive and use lowercase identifiers.
3. Identifiers may contain letters, digits, `.`, `_`, and `-`.
4. Identifiers must begin with a letter or digit.
5. Each identifier is limited to 128 characters.
6. `/`, `\`, `%2f`, `%5c`, `..`, empty segments, and control characters are rejected.
7. Query strings and fragments are not supported in `v0.1`.
8. Unknown URI shapes are rejected as `invalid_uri`.
9. A URI is never converted to a path by simple string concatenation.

## 7. Gateway configuration

### 7.1 Configuration entrypoint

The server reads one configuration file selected by:

```text
MATIAS_CONTEXT_GATEWAY_CONFIG
```

The environment variable contains an absolute path to a local JSON configuration file.

The configuration file may name root environment variables but should not require absolute roots to be committed to the repository.

The configuration binds local checkouts to the frozen `v0.1` exposure profile. It must not silently add, remove, or redefine source IDs, roles, authorities, document IDs, document paths, producer IDs, manifest locators, supported extensions, or hard limits. An implementation may store the frozen profile in package code or serialize it in the configuration file, but startup validation must enforce exact agreement with this contract.

### 7.2 Root environment variables

The initial profile uses:

```text
CONTEXT_ROUTING_ROOT
KB_CONTRACTS_ROOT
KNOWLEDGE_INSPECT_ROOT
KB_ARTIFACTS_ROOT
```

Roots are supplied by the operator. They are not MCP client roots and are not negotiable by the client.

### 7.3 Startup validation

Startup fails before the server enters operation if:

- configuration is missing;
- configuration version is unsupported;
- a source ID is duplicated;
- the configured source-ID set is not exactly `context-routing`, `kb-contracts`, `knowledge-inspect`, and `kb-artifacts`;
- the configured producer-ID set is not exactly `knowledge-inspect` and `kb-artifacts`;
- any configured role, authority, document mapping, producer mapping, manifest locator, extension, or hard limit differs from the frozen `v0.1` profile;
- a source root environment variable is missing;
- a configured root does not exist or is not a directory;
- a mapped document is absolute;
- a mapped document escapes its root;
- a manifest locator is absolute;
- a producer ID is duplicated;
- a configured extension is unsupported.

Failure at startup is preferable to a partially authorized server.

## 8. Initial source profile

### 8.1 Context Routing

```yaml
source_id: context-routing
root_env: CONTEXT_ROUTING_ROOT
role: routing_projection
authority: routing
documents:
  routing-overview: README.md
  published-source-catalog: static/context-data/sources.json
```

Special behavior:

- `published-source-catalog` is a normalized projection, not a byte-for-byte return of `sources.json`.
- The projection includes only entries whose `publish_status` is `ready` or `published` and whose `exposure_level` is `public` or `private_safe`.
- The projection omits `origin_location`, local relative paths, hidden entries, sensitive entries, and private-redacted entries.
- Permitted projected fields are `source_id`, `source_name`, `publish_mode`, `publish_status`, `published_slug`, `exposure_level`, `is_agent_ready`, `page_url`, `artifact_url`, and `snapshot_url`.
- The projection is published source metadata, not an access-control list.
- Entries in the broader catalog do not become gateway sources.
- The gateway source catalog still contains only the four sources in this contract.
- Local roots or sensitive source bodies referenced by Context Routing remain inaccessible.

### 8.2 KB Contracts

```yaml
source_id: kb-contracts
root_env: KB_CONTRACTS_ROOT
role: contract_registry
authority: authoritative
documents:
  manual-overview: README.md
```

Special behavior:

- The repository is authoritative for shared integration semantics.
- Additional contract pages may be mapped later by configuration amendment.
- The MVP must not recursively expose the Docusaurus docs tree.

### 8.3 Knowledge Inspect

```yaml
source_id: knowledge-inspect
root_env: KNOWLEDGE_INSPECT_ROOT
role: canonical_artifact_producer
authority: operational
documents:
  module-overview: README.md
  module-definition: docs/modules/kb-module-definition.md
  artifact-surface: kb_artifact_surface.md
  health-contract: kb_health_contract.md
manifest_profile:
  producer_id: knowledge-inspect
  locator: artifacts/manifests/{manifest_id}.manifest.json
  media_type: application/json
```

Special behavior:

The following are outside the public gateway boundary:

- embedding cache databases;
- Chroma or vector-store directories;
- processed-file state;
- parser internals;
- private helper modules;
- arbitrary `artifacts/` traversal;
- pipeline execution.

### 8.4 KB Artifacts

```yaml
source_id: kb-artifacts
root_env: KB_ARTIFACTS_ROOT
role: governed_evidence_selector
authority: derived
documents:
  selector-overview: README.md
  operator-guide: docs/index.md
manifest_profile:
  producer_id: kb-artifacts
  locator: artifacts/runs/{manifest_id}/manifest.json
  media_type: application/json
```

Special behavior:

- only selection runs under the configured `artifacts/runs/` root are addressable;
- source JSONL buses are not exposed in the MVP;
- `selected.jsonl`, `selected.csv`, and `artifact.md` are not exposed in the MVP;
- the gateway does not execute `kb-artifact select`;
- selection logic remains owned by KB Artifacts.

## 9. Core data types

The implementation must preserve these conceptual states, whether represented by dataclasses, Pydantic models, or equivalent immutable structures.

### 9.1 `SourceSpec`

Required fields:

```text
source_id
display_name
role
authority
root
documents
maximum_bytes
allowed_extensions
manifest_profile?
```

### 9.2 `ResourceRef`

Represents a parsed but unauthorized request.

Required fields:

```text
uri
resource_family
source_id?
document_id?
producer_id?
manifest_id?
```

### 9.3 `AuthorizedRead`

Represents one specific read after policy approval.

Required fields:

```text
requested_uri
source_id
canonical_path
content_media_type
maximum_bytes
logical_id
authority
```

Only the filesystem adapter may receive `canonical_path`.

### 9.4 `ResourceEnvelope`

Represents the normalized successful response.

Its schema is defined in Section 13.

## 10. Request-processing contract

Every context-document or manifest read follows this order:

```text
1. Parse URI
2. Validate URI shape and identifiers
3. Look up source or producer in registry
4. Resolve an explicit document mapping or fixed manifest locator
5. Build candidate path under configured root
6. Canonicalize root and candidate
7. Verify containment after symlink resolution
8. Verify regular-file status
9. Verify extension
10. Verify size bound
11. Produce AuthorizedRead
12. Read bounded content
13. Parse or decode
14. Build checksum and provenance
15. Return ResourceEnvelope
```

No step may be skipped.

### 10.1 Complete mediation

All filesystem reads must pass through the policy gate. A convenience path that bypasses the policy gate is a contract violation even when used only by one handler.

### 10.2 Fail-closed behavior

Any ambiguity produces an error. There is no fallback to:

- another root;
- recursive search;
- fuzzy identifier matching;
- the current working directory;
- a raw path;
- a similarly named file.

## 11. Read-only property

Read-only is structural.

The MVP package must not contain source-facing functions for:

- write;
- append;
- delete;
- rename;
- move;
- chmod;
- repository commit;
- shell execution;
- pipeline execution.

The filesystem adapter opens files only in binary read mode.

Temporary files are not needed for resource reads. If the SDK creates its own transport state, that state must remain outside source roots.

## 12. Supported inputs and normalization

### 12.1 Supported source extensions

The MVP supports:

- `.md`
- `.json`

All other extensions are rejected as `unsupported_format`.

### 12.2 Markdown

Markdown is:

- decoded as strict UTF-8;
- returned as text under the response envelope;
- not rendered;
- not executed;
- not expanded through includes.

### 12.3 JSON

JSON is:

- decoded as strict UTF-8;
- parsed as JSON;
- required to have exactly one top-level value;
- returned as structured data under the response envelope.

Malformed JSON is rejected.

### 12.4 Manifest identity checks

#### Knowledge Inspect profile

A Knowledge Inspect manifest must:

- be a JSON object;
- include `run_id`;
- have `run_id` equal to `manifest_id`;
- include a status field;
- include producer identity compatible with the Knowledge Inspect contract when that field is present.

The gateway does not perform full schema validation in the resource-only MVP.

#### KB Artifacts profile

A KB Artifacts manifest must:

- be a JSON object;
- include `selection_request`;
- include `generated_at`;
- include `matched_partitions`;
- include `counts`;
- include `outputs`;
- identify `manifest.json` in `outputs`.

The gateway does not recompute input partition hashes or rerun selection.

## 13. Successful response contract

All successful resources are returned as JSON text with MCP MIME type:

```text
application/json
```

The payload follows:

```json
{
  "contract_version": "mcp-context-gateway.v0.1",
  "resource": {
    "uri": "matias-context://source/kb-contracts/document/manual-overview",
    "family": "context_document",
    "source_id": "kb-contracts",
    "logical_id": "manual-overview",
    "authority": "authoritative",
    "read_only": true,
    "content_media_type": "text/markdown",
    "size_bytes": 1234,
    "sha256": "hex-encoded-sha256",
    "modified_at": "2026-07-27T18:00:00Z"
  },
  "data": {
    "text": "# KB Manual\n..."
  }
}
```

### 13.1 Resource families

Permitted `family` values:

```text
source_catalog
source_descriptor
context_document
manifest
```

### 13.2 Catalog response

`matias-context://catalog/sources` returns:

```json
{
  "contract_version": "mcp-context-gateway.v0.1",
  "resource": {
    "uri": "matias-context://catalog/sources",
    "family": "source_catalog",
    "read_only": true
  },
  "data": {
    "count": 4,
    "sources": []
  }
}
```

Each source descriptor contains:

```text
source_id
display_name
role
authority
available_documents
manifest_producer
```

It must not contain:

- absolute roots;
- service-account paths;
- secrets;
- unconfigured Context Routing entries;
- canonical filesystem paths.

### 13.3 Source descriptor response

A source descriptor contains:

```text
source_id
display_name
role
authority
read_only
available_documents
manifest_profile summary, when present
```

The manifest profile summary may expose `producer_id`, but not its physical locator.

### 13.4 Provenance requirements

Every document and manifest response includes:

- logical URI;
- source ID or producer ID;
- logical document or manifest ID;
- authority;
- content media type;
- size in bytes;
- SHA-256;
- modification timestamp when available.

Physical paths are never returned.

### 13.5 Generated-resource provenance

The source catalog and source descriptors are synthesized from the frozen gateway profile rather than read from one source file. Their provenance consists of:

- logical URI;
- resource family;
- contract version;
- `read_only: true`;
- the fixed profile identity `mcp-context-gateway.v0.1`.

They do not claim a file checksum, file size, or modification timestamp. The full provenance fields in Section 13.4 are required only for filesystem-backed context documents and manifests.

## 14. Limits

### 14.1 Content limits

```text
default maximum resource body: 262,144 bytes
hard maximum resource body: 262,144 bytes
maximum source catalog entries: 4
maximum mapped documents per source: 32
maximum identifier length: 128 characters
maximum URI length: 1,024 characters
```

The adapter must not read the entire file before enforcing the hard limit.

A permitted approach is:

1. inspect file size;
2. reject if above limit;
3. read at most `limit + 1` bytes;
4. reject if more bytes are observed.

### 14.2 No pagination in MVP

The fixed four-source catalog does not require pagination.

Manifest and document resources return one item.

Pagination is deferred until a resource family genuinely requires it.

## 15. Filesystem authorization rules

### 15.1 Root ownership

Roots are configured by the server operator.

A client cannot:

- add roots;
- replace roots;
- request a root;
- submit a path relative to a root.

### 15.2 Explicit document allowlist

Context documents are resolved only through:

```text
source_id + document_id -> configured relative path
```

A valid-looking unmapped document ID is still rejected.

### 15.3 Manifest locator

Manifest paths are resolved only through a producer-specific fixed template and a validated single-segment `manifest_id`.

### 15.4 Containment

After resolving symlinks:

```text
canonical_candidate must be a descendant of canonical_root
```

Equality with the root is not a valid file resource.

### 15.5 File type

The target must be a regular file.

Directories, devices, sockets, FIFOs, and broken symlinks are rejected.

## 16. Error contract

Domain errors are stable and machine-readable.

### 16.1 Error payload

```json
{
  "error_code": "unknown_source",
  "message": "Unknown configured source.",
  "resource_uri": "matias-context://source/not-real",
  "details": {}
}
```

Messages must not reveal absolute paths.

### 16.2 Domain errors

Configuration failures detected before MCP initialization produce no JSON-RPC response. The process must emit a sanitized `configuration_error` event to `stderr`, emit nothing to `stdout`, and exit non-zero.

A traversal-shaped client identifier such as `..`, an encoded separator, a backslash, or an extra URI segment fails during URI validation as `invalid_uri`, before registry lookup or filesystem access. A configured mapping or symlink that resolves outside its root fails as `outside_allowed_root`.

| Domain error | Meaning | JSON-RPC mapping |
|---|---|---:|
| `invalid_uri` | unsupported scheme, shape, or identifier | `-32602` |
| `unknown_source` | source ID not registered | `-32002` |
| `unknown_producer` | manifest producer not registered | `-32002` |
| `resource_not_found` | mapped resource does not exist | `-32002` |
| `unknown_document` | document ID not mapped | `-32002` |
| `outside_allowed_root` | canonical path escapes root | `-32010` |
| `unsupported_format` | extension or media type not allowed | `-32011` |
| `resource_too_large` | body exceeds 262,144 bytes | `-32012` |
| `malformed_json` | JSON cannot be decoded or parsed | `-32013` |
| `malformed_manifest` | producer identity checks fail | `-32014` |
| `configuration_error` | invalid server-owned configuration | startup failure: no JSON-RPC response; non-zero exit |
| `internal_error` | unexpected server failure | `-32603` |

Policy errors must not be disguised as not-found errors in local development evidence. The operator should be able to distinguish boundary rejection from absence.

## 17. Logging contract

Logs are written to `stderr`.

Each log event should contain, where applicable:

```text
timestamp
level
event
resource_family
source_id or producer_id
logical_id
outcome
duration_ms
error_code
```

Logs must not contain:

- resource bodies;
- secrets;
- service-account JSON;
- absolute roots in normal INFO output;
- arbitrary exception locals.

Debug logs may contain canonical paths only when explicitly enabled by the local operator.

## 18. Prohibited operations

The following are contract violations in `v0.1`:

- accepting raw filesystem paths from a client;
- exposing arbitrary files under a configured root;
- recursive directory browsing;
- shell execution;
- subprocess execution;
- Python evaluation;
- arbitrary SQL;
- reading SQLite or Chroma stores;
- network crawling;
- fetching arbitrary URLs;
- repository modification;
- manifest repair;
- checksum rewriting;
- running ingestion or selection pipelines;
- following a symlink outside a root;
- returning an absolute physical path;
- reading `private/`, `.env`, credentials, keys, or service-account files;
- implementing tools before the resource MVP closes.

## 19. Minimal implementation boundaries

A conforming implementation should fit approximately within:

```text
models and errors       80-120 lines
configuration/registry  100-150 lines
URI resolver             60-100 lines
policy gate             100-160 lines
filesystem adapter       60-100 lines
normalizer               60-100 lines
MCP facade/resources     80-140 lines
contract probe           50-100 lines
```

The line budget is a design signal, not a contest. Exceeding approximately 1,000 source lines requires an architecture review before adding more code.

The MVP does not require:

- abstract base classes;
- dependency-injection frameworks;
- plugin loading;
- persistence;
- caches;
- background workers;
- a database.

## 20. Executable contract probes

A single script such as:

```text
scripts/probe_contract.py
```

must demonstrate:

```text
PASS server initializes over stdio
PASS only `resources` is announced and MCP logging is absent
PASS source catalog contains exactly four sources
PASS mapped Context Routing document is readable
PASS mapped KB Contracts document is readable
PASS mapped Knowledge Inspect document is readable
PASS mapped KB Artifacts document is readable
PASS Knowledge Inspect manifest is readable
PASS KB Artifacts manifest is readable
PASS unknown source is rejected
PASS unknown document is rejected
PASS traversal-shaped identifier is rejected
PASS symlink escape is rejected
PASS oversized resource is rejected
PASS no physical path appears in a response
PASS invalid startup configuration exits non-zero with clean `stdout`
```

This probe is mandatory even though a comprehensive test suite is deferred.

## 21. MVP evidence bundle

The implementation sprint should preserve:

```text
artifacts/mvp-evidence/
  initialize.json
  capabilities.json
  resources-list.json
  resource-templates-list.json
  source-catalog-response.json
  context-document-response.json
  knowledge-inspect-manifest-response.json
  kb-artifacts-manifest-response.json
  unauthorized-request-error.json
  probe-output.txt
```

Screenshots may supplement the bundle but do not replace machine-readable transcripts.

## 22. Definition of Done

The resource-only MVP is complete when:

1. this contract is implemented without unresolved architecture decisions;
2. the server starts over `stdio`;
3. initialization and capability negotiation succeed;
4. the source catalog returns exactly four configured sources;
5. at least one real mapped document from each source is readable;
6. one Knowledge Inspect manifest is readable;
7. one KB Artifacts manifest is readable;
8. every filesystem-backed body is bounded and includes the full provenance fields in Section 13.4; generated catalog and descriptor resources include the profile provenance in Section 13.5;
9. invalid and unauthorized requests fail deterministically;
10. source roots and physical paths are absent from client responses;
11. the contract probe passes;
12. the implementation remains approximately below 1,000 source lines;
13. no tools or write-capable code paths have been introduced.

### 22.1 Gate 0 exit decisions

| Case | Required behavior |
|---|---|
| Valid context resource | Parse the logical URI, resolve an explicit mapping, authorize and canonicalize the target, enforce format and size limits, perform a bounded read, and return the Section 13 envelope as `application/json`. |
| Unknown source | Return `unknown_source` mapped to `-32002`; do not resolve a path or touch the filesystem. |
| Traversal-shaped request | Return `invalid_uri` mapped to `-32602` before registry lookup. A mapping or symlink escape discovered after resolution returns `outside_allowed_root` mapped to `-32010`. |
| Oversized file | Return `resource_too_large` mapped to `-32012` before returning any resource body. |
| Provenance | Filesystem-backed documents and manifests return logical identity, authority, media type, byte size, SHA-256, and modification time when available. Generated catalog and descriptor resources return the profile provenance defined in Section 13.5. |
| Kernel versus MCP | The MCP facade owns protocol lifecycle, resource registration, request/result translation, and `stderr` logging. The kernel owns parsing, registry lookup, authorization, resolution, canonicalization, bounded I/O, normalization, and provenance, and imports no MCP SDK types. |

## 22.2 Identifier and producer-identity amendment

The v0.1 URI grammar uses distinct identifier classes. Source IDs,
producer IDs, and document IDs remain lowercase. A manifest ID is a
producer-native, case-preserving, single URI segment of at most 128
characters containing only ASCII letters, digits, `.`, `_`, and `-`;
`..` remains forbidden. The gateway must apply its exact case to the
fixed producer locator.

The gateway producer ID and a manifest's source-local producer identity
are separate contract values. For Knowledge Inspect, the gateway
producer ID is `knowledge-inspect`, while the only accepted manifest
producer identity is the stable module ID `kb`. Producer identity is
matched exactly; fuzzy matching and case normalization are forbidden.

## 23. Deferred work

The following may begin only after the MVP closes:

- artifact and evidence-packet resource families;
- metadata-search tool;
- manifest-validation tool;
- governed evidence-selection tool;
- JSONL and CSV resource bodies;
- manifest indexes and pagination;
- client roots evaluation;
- Streamable HTTP;
- authentication;
- S3, GitHub, or database adapters;
- OpenTelemetry;
- comprehensive test suite and CI;
- remote deployment.

## 24. Grounding references

### Internal repositories

- Context Routing: `https://github.com/matuteiglesias/context`
- KB Contracts: `https://github.com/matuteiglesias/kb-contracts`
- Knowledge Inspect: `https://github.com/matuteiglesias/knowledge-inspect`
- KB Artifacts: `https://github.com/matuteiglesias/gpt-digests`

### MCP primary documentation

- MCP resources specification: `https://modelcontextprotocol.io/specification/2025-11-25/server/resources`
- MCP lifecycle: `https://modelcontextprotocol.io/specification/2025-06-18/basic/lifecycle`
- MCP Python SDK server guide: `https://py.sdk.modelcontextprotocol.io/server/`
- MCP Python SDK client guide: `https://py.sdk.modelcontextprotocol.io/client/`
