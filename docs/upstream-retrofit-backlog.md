# Upstream Retrofit Backlog

This backlog records improvements discovered while integrating the existing ecosystem through MCP.

The gateway must remain a thin adapter. Upstream systems should own their schemas, stable identities and public artifact surfaces.

## Priority model

- **P0:** blocks the real MCP resource path.
- **P1:** reduces ambiguity or integration drift.
- **P2:** improves future reuse but is not needed to close v0.1.

---

# 1. KB Contracts

## P0 — Define producer-native manifest identifier grammar

The current gateway contract assumed lowercase logical identifiers, while real run IDs use uppercase `T` and `Z`.

Add a shared contract that distinguishes:

- lowercase source IDs;
- lowercase producer IDs;
- lowercase document IDs;
- producer-native manifest/run IDs;
- allowed single-segment characters;
- length limits;
- case preservation;
- prohibition of slash, backslash, traversal and control characters.

Acceptance:

- Knowledge Inspect and KB Artifacts example IDs conform;
- the gateway no longer needs undocumented exceptions;
- cross-repo tests include valid and invalid examples.

## P1 — Add an MCP adapter seam contract

Document:

- resources versus tools;
- logical identity versus physical location;
- provenance minimums;
- read-only gateway expectations;
- producer responsibility versus adapter responsibility;
- error ownership;
- rules for exposing public artifacts without exposing directories.

This must remain a contract for adapters, not make MCP the ecosystem's internal architecture.

## P1 — Add cross-repository fixtures

Maintain small sanitized canonical examples for:

- context source descriptor;
- run record;
- Knowledge Inspect manifest;
- KB Artifacts selection manifest;
- provenance envelope.

Consumers should be able to test compatibility without running the producers.

## P2 — Add compatibility matrix

Record which schema versions are emitted and consumed by:

- Context Routing;
- Knowledge Inspect;
- KB Artifacts;
- MCP gateway.

---

# 2. Knowledge Inspect

## P0 — Publish a machine-readable manifest schema

The public artifact documentation defines a manifest minimum contract v2, but consumers need an executable schema or model.

Add:

schemas/
  knowledge_inspect_manifest_v2.schema.json
tests/fixtures/
  manifest_v2.minimal.json
  manifest_v2.complete.json

Minimum fields should agree with the public artifact contract:

* `manifest_version`;
* `run_id`;
* `artifact_family`;
* `artifact_kind`;
* `schema_version_emitted`;
* `producer`;
* `producer_version`;
* `status`;
* `artifacts[]`;
* per-artifact hashes where feasible.

## P0 — Separate repository identity from producer identity

Document explicitly:


repository: knowledge-inspect
gateway producer ID: knowledge-inspect
manifest producer identity: kb

Avoid forcing downstream consumers to infer this relation.

## P1 — Provide a stable manifest index

Add a bounded machine-readable index such as:


artifacts/indexes/manifests.latest.json


It may contain:

* run ID;
* entrypoint;
* status;
* completed timestamp;
* manifest relative pointer;
* schema version.

The MCP v0.1 gateway does not need to expose this index yet, but future discovery should not require directory scanning.

## P1 — Add contract compliance tests

Test:

* run ID and filename agreement;
* producer identity;
* required artifact entries;
* checksums;
* public paths remain under documented artifact roots;
* no cache or vector-store path is emitted as a public artifact.

## P2 — Version legacy manifests explicitly

When old manifests differ from v2, identify them by version rather than accepting them through heuristics.

---

# 3. KB Artifacts / GPT Digests

## P0 — Formalize and version the selection manifest

The documentation currently promises that the manifest records the request, input partition hashes, counts and output names.

Add an executable schema with explicit:

* `manifest_version`;
* `run_id`;
* `producer`;
* `generated_at`;
* `selection_request`;
* `matched_partitions`;
* partition hashes;
* input and selected counts;
* output artifact entries;
* output checksums;
* selection status;
* deterministic empty-selection representation.

## P0 — Add sanitized manifest fixtures

Commit:


tests/fixtures/
  selection_manifest.minimal.json
  selection_manifest.complete.json


Use them both in package tests and gateway compatibility tests.

## P1 — Stabilize run ID generation

Document:

* lexical grammar;
* case sensitivity;
* timestamp format;
* collision behavior;
* relation between output-directory name and manifest `run_id`.

The gateway should preserve the ID exactly rather than reconstruct it.

## P1 — Replace placeholder package metadata

`pyproject.toml` currently contains a placeholder author email.

Replace it with accurate metadata or omit the email.

## P1 — Add CI for package and contract tests

Run:

* installation;
* unit tests;
* manifest-schema validation;
* read-only source invariants;
* deterministic fixture selection.

## P2 — Emit a bounded run index

A future MCP resource can consume a producer-owned index rather than scan `artifacts/runs/`.

---

# 4. Context Routing

## P1 — Add schema version to machine-readable source metadata

`static/context-data/sources.json` should declare:

* schema version;
* generation timestamp;
* generator version;
* record count.

## P1 — Emit an explicitly safe projection

Consider producing:


static/context-data/sources.public.json


with only the fields sanctioned for agent-facing discovery.

This would reduce duplication between the publishing layer and gateway filtering while preserving Context Routing as a pointer layer rather than an authorization system.

## P1 — Define enum contracts

Version the accepted values for:

* publication status;
* publication mode;
* exposure level;
* agent readiness.

## P2 — Add a stable source identity check

Ensure `source_id` is unique, stable and independent of display names or slugs.

## P2 — Add a publication safety test

Assert that the safe projection contains no:

* local roots;
* credentials;
* service-account paths;
* hidden records;
* sensitive records;
* private-redacted bodies.

---

# 5. Cross-repository work

## P1 — Compatibility test repository or fixture package

Avoid introducing another runtime platform.

A small fixture/test package may validate:

* shared ID grammar;
* manifest schemas;
* public artifact paths;
* provenance fields;
* adapter compatibility.

## P1 — Producer/consumer version declaration

Each producer should publish:

* producer ID;
* producer version;
* emitted schema versions;
* public artifact families.

Each consumer should declare accepted versions.

## P2 — MCP-safe indexes

After the explicit-resource MVP closes, evaluate producer-owned bounded indexes for:

* source discovery;
* manifest discovery;
* artifact metadata.

Do not expose directory browsing as a shortcut.

## Explicit non-goals

This retrofit does not require:

* adding MCP SDK dependencies to upstream repositories;
* moving gateway logic upstream;
* making MCP the internal bus;
* adding remote transport;
* creating a new shared database;
* renaming historical runs;
* rewriting legacy artifacts in place.
