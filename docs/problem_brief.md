---
title: MCP Context Gateway — Problem Brief
document_version: "0.1"
status: approved-for-mvp
owner: Matías Iglesias
date: 2026-07-27
gate: "Gate 0 — Problem definition and contract"
---

# MCP Context Gateway — Problem Brief

## 1. Decision summary

Build a small, local, read-only MCP gateway over four existing knowledge-management systems:

1. **Context Routing**
2. **KB Contracts**
3. **Knowledge Inspect**
4. **KB Artifacts**

The gateway will not create a new knowledge platform or duplicate the four systems. It will provide a narrow, standard interface through which an MCP client can discover governed sources and read selected context documents and manifests without receiving arbitrary filesystem access.

The first MVP will expose only **resources**. Tools, evidence selection, semantic search, remote transport, authentication, and cloud deployment are deferred.

## 2. Problem statement

Matías already has a functioning knowledge ecosystem with:

- a published source-routing layer;
- an authoritative contract and decision registry;
- ingestion and analysis pipelines that emit run records and manifests;
- a governed read-only evidence selector.

However, a client or agent currently needs source-specific knowledge to use those systems:

- which repository contains the desired information;
- which files are public contracts and which are internals;
- how each repository names artifacts;
- where manifests are written;
- which paths are safe to read;
- which source is authoritative when two surfaces overlap.

This creates several problems:

1. **Ad hoc integration**  
   Every new client requires custom path knowledge or a bespoke adapter.

2. **Boundary erosion**  
   A convenient integration may bypass documented seams and read internal caches, vector stores, temporary directories, or raw upstream files.

3. **Infrastructure leakage**  
   Consumers may become coupled to local absolute paths and repository layouts rather than stable logical identities.

4. **Inconsistent provenance**  
   Sources expose useful provenance, but consumers do not receive it through one consistent response contract.

5. **No standard AI-facing interface**  
   The ecosystem already contains tool-like and resource-like capabilities, but they are not exposed through MCP.

## 3. Why this project now

MCP has become a recurring requirement in AI engineering, agentic-system, and internal-AI-platform roles. The gap in Matías's portfolio is not a lack of underlying systems thinking. The existing ecosystem already implements contracts, provenance, run records, bounded artifacts, adapters, human-facing outputs, and operational seams.

The high-return move is therefore not to build a toy MCP server. It is to place a thin standard adapter over real systems and make the existing engineering legible through a recognized protocol.

## 4. The four core systems

### 4.1 Context Routing

**Repository:** `matuteiglesias/context`

**Current role:** discovery and routing surface.

The repository:

- reads a Google Sheet registry through a read-only service account;
- normalizes source rows;
- generates human-browsable routing pages;
- emits machine-readable source metadata under `static/context-data/`;
- links to curated artifacts and snapshots;
- distinguishes publication mode, publication status, exposure level, and agent readiness.

It is intentionally a pointer and publishing layer. It is **not** the full context spine and must not be treated as the authority for the internal contracts of every system it points to.

**Role in the gateway:**

- supplies the model for source discovery and exposure metadata;
- provides an initial real JSON resource through a filtered gateway projection;
- does not expose raw `origin_location` values, hidden entries, or sensitive entries from the broader catalog;
- does not authorize arbitrary access to every source listed in its broader registry;
- does not become the gateway's filesystem allowlist automatically.

### 4.2 KB Contracts

**Repository:** `matuteiglesias/kb-contracts`

**Current role:** authoritative decision registry and contract catalog.

The repository defines:

- stable seams between repositories;
- bus contracts;
- schema and naming conventions;
- manifest and run-record rules;
- error taxonomy and stop rules;
- publishing and consumer contracts;
- adapter policy;
- the rule that consumers must not bypass public seams by reading raw upstream inputs.

**Role in the gateway:**

- acts as the highest-authority source for integration semantics;
- supplies canonical context documents;
- constrains how the gateway may connect the other repositories;
- is read through explicit logical document mappings, never directory traversal.

### 4.3 Knowledge Inspect

**Repository:** `matuteiglesias/knowledge-inspect`

**Current role:** contract-facing ingestion and analysis module.

The repository includes sanctioned seams for chat ingestion, chat analysis, and paper/GROBID processing. Canonical runs emit:

- run records;
- manifests;
- module-local observability indexes;
- chunk sets;
- summaries;
- analysis exports.

Its public artifact surface is explicitly separated from non-contract internals such as embedding caches, Chroma storage, processed-file state, parsers, and private helper modules.

Knowledge Inspect defines a stable run-record shape with fields such as:

- version;
- project and entrypoint;
- timestamps;
- status;
- stages;
- schema versions;
- warnings and errors;
- safe environment metadata;
- counters;
- structured inputs and outputs.

Its manifest contract includes producer metadata, artifact identity, schema information, output entries, and checksums where feasible.

**Role in the gateway:**

- supplies canonical runtime manifests;
- supplies public contract documents;
- must be accessed through its public artifact surface;
- must not expose vector stores, SQLite caches, parser internals, or processed-file state.

### 4.4 KB Artifacts

**Repository:** `matuteiglesias/gpt-digests`  
**Package name:** `kb-artifacts`

**Current role:** governed read-only evidence selection.

The package:

- scans chunk and summary JSONL buses without modifying sources;
- applies explicit, deterministic filters;
- preserves record identity and provenance;
- emits `selected.jsonl`, `selected.csv`, `artifact.md`, and `manifest.json`;
- records the selection request, matched input partitions and hashes, counts, and output names.

**Role in the gateway:**

- supplies selection-run manifests;
- supplies operator and selector documentation as context;
- remains the owner of evidence-selection logic;
- is not invoked as a tool in the first MVP;
- does not allow the gateway to implement a second selection engine.

## 5. Authority model

The gateway must preserve the following precedence:

1. **KB Contracts** — authoritative for ecosystem integration rules and shared contracts.
2. **Source-local public contracts** — authoritative for how a specific producer exposes its public surfaces.
3. **Runtime manifests and run records** — authoritative evidence of a particular execution.
4. **Context Routing** — authoritative for routing metadata it publishes, but not for the internal semantics of the target systems.
5. **Gateway configuration** — authoritative only for local root binding and selection of the frozen `v0.1` exposure profile. It may not add sources, documents, producers, or locator rules without a contract amendment.

The gateway must not silently resolve disagreements. If two authorities conflict, it should expose the conflict or fail closed rather than invent a merged interpretation.

## 6. Primary user

The initial user is Matías operating a local MCP client.

The client needs to:

- discover the four configured sources;
- understand each source's role and authority;
- read a small set of explicitly mapped context documents;
- read a known manifest produced by Knowledge Inspect;
- read a known selection manifest produced by KB Artifacts;
- receive provenance and bounded metadata with every response;
- receive an explicit rejection for invalid or unauthorized requests.

## 7. Core user stories

### US-01 — Discover configured sources

As an MCP client, I can read a source catalog that lists exactly the four configured gateway sources and their roles without revealing local root paths.

### US-02 — Read a source descriptor

As an MCP client, I can read the descriptor for one configured source and understand its authority, role, exposure policy, and available logical documents.

### US-03 — Read a governed context document

As an MCP client, I can request a logical document such as `kb-contracts/manual-overview` and receive its content, checksum, size, modification timestamp, and source identity.

### US-04 — Read a Knowledge Inspect manifest

As an MCP client, I can request a known Knowledge Inspect manifest by logical manifest ID and receive parsed JSON plus provenance without browsing the run directory.

### US-05 — Read a KB Artifacts manifest

As an MCP client, I can request a known selection manifest from a configured `artifacts/runs/` location and receive its selection request, partition hashes, counts, and output names.

### US-06 — Reject an unauthorized request

As an operator, I can demonstrate that an unknown source, path traversal attempt, symlink escape, unsupported file type, or oversized resource is rejected before file content is returned.

## 8. Desired system property

The central property is:

> A client asks for a logical resource. It never supplies or receives a physical filesystem path.

The expected path is:

```text
MCP client
  -> logical URI
  -> URI resolver
  -> source registry
  -> policy gate
  -> authorized read
  -> bounded filesystem adapter
  -> normalized provenance-rich response
```

## 9. MVP scope

### Included

- one local Python package or repository;
- one versioned problem brief and frozen contract;
- one transport-independent read-only resource kernel;
- explicit source registry for the four systems;
- explicit logical-document mappings;
- local `stdio` MCP transport;
- resource capability;
- structured operational logging to `stderr`, without declaring the MCP logging capability;
- source catalog resource;
- source descriptor resource;
- context document resource;
- manifest resource;
- JSON and Markdown input formats only;
- bounded reads;
- SHA-256 checksums;
- explicit domain errors;
- one real context document from each core source;
- one real or locally generated manifest from each manifest-producing source;
- one client-to-server transcript;
- one executable contract probe script.

### Excluded

- MCP tools;
- prompts, sampling, elicitation, completions, and subscriptions;
- `resources/list_changed`;
- MCP client roots;
- Streamable HTTP;
- remote authentication or authorization;
- shell execution;
- arbitrary filesystem reads;
- arbitrary SQL;
- repository writes;
- ledger or knowledge-base mutations;
- semantic search;
- vector retrieval;
- running Knowledge Inspect pipelines;
- running KB Artifacts selection;
- evidence packet generation;
- binary files;
- PDF, CSV, or JSONL resource bodies;
- cloud deployment;
- database or cache;
- dynamic plugin system;
- comprehensive automated test suite.

## 10. Engineering constraints

1. The implementation should remain below approximately **1,000 source lines** for the MVP.
2. The MCP facade must remain thin and must not own source semantics.
3. No raw client string may be passed directly to `open()`.
4. All configured roots are server-owned configuration, not client-provided roots.
5. No source is accessible unless explicitly registered.
6. No document is accessible unless explicitly mapped.
7. Manifest location patterns must be fixed per producer.
8. Responses must be bounded and fail closed.
9. The gateway must not duplicate source content or manifest schemas.
10. A full test suite is deferred, but executable boundary probes are mandatory.

## 11. Success criteria

The MVP is successful when a real MCP client can:

1. initialize a `stdio` session;
2. observe only the `resources` capability, with no tools, prompts, subscriptions, list-change notifications, or MCP logging capability;
3. list or discover the gateway resources and templates;
4. read the four-source gateway catalog;
5. read at least one mapped context document from each source;
6. read one Knowledge Inspect manifest;
7. read one KB Artifacts manifest;
8. observe full content provenance on every filesystem-backed document and manifest response, and logical profile provenance on generated catalog and descriptor responses;
9. receive a deterministic error for an invalid URI;
10. receive a deterministic rejection for an out-of-bound request.

The operator must be able to reproduce the demo from a clean local checkout using documented commands.

## 12. Non-functional goals

### Security

- least authority;
- complete mediation;
- fail-closed behavior;
- no secret disclosure;
- no path disclosure;
- no write-capable code path.

### Maintainability

- one narrow resource kernel;
- one registry;
- one resolver;
- one policy gate;
- one filesystem adapter;
- source-specific behavior expressed as configuration or small codecs.

### Portability

The kernel must not import MCP types. A future CLI, HTTP facade, GitHub adapter, or S3 adapter should be able to reuse the same logical-resource model.

### Explainability

The complete system should be explainable with:

- the four source roles;
- one request pipeline;
- one resource namespace;
- one response envelope;
- one error model.

## 13. Main risks and mitigations

| Risk | Consequence | MVP mitigation |
|---|---|---|
| Gateway becomes another knowledge platform | duplicated authority and drift | adapter-only scope; no new store |
| Raw path access leaks through | arbitrary filesystem exposure | logical IDs, explicit mappings, policy gate |
| Context Routing catalog is mistaken for an access allowlist | sensitive sources become reachable | separate gateway registry with exactly four sources |
| Source internals are exposed | cross-repo coupling and security risk | only mapped public documents and manifest surfaces |
| Manifest schemas differ | brittle universal validator | producer-specific identity checks; full validation deferred |
| MCP concerns leak into core | protocol lock-in | transport-independent kernel |
| Early test suite becomes larger than implementation | development friction | one probe script; full suite deferred |
| Scope expands into tools and retrieval | MVP does not close | resource-only contract; deferred list is explicit |

## 14. Gate 0 deliverables

Gate 0 is complete when these files exist and agree:

- `docs/problem_brief.md`
- `docs/mcp_context_gateway_contract_v0_1.md`

The contract must resolve the following without further architecture decisions:

- source identities and roles;
- resource URIs;
- configured roots;
- logical document mappings;
- manifest locator rules;
- supported formats;
- response envelope;
- size limits;
- authorization flow;
- error semantics;
- prohibited operations;
- MVP acceptance probes.

## 15. Next implementation gate

After Gate 0:

1. create the package scaffold;
2. implement models, registry, and configuration loading;
3. implement URI parsing and policy authorization;
4. implement bounded filesystem reads and normalization;
5. start the MCP server over `stdio`;
6. expose context resources;
7. expose manifest resources;
8. run the client and contract probes;
9. save the evidence transcript.

No tools should be added before the resource-only MVP closes.
