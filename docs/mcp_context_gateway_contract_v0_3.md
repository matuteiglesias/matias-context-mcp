# MCP context gateway v0.3 — evidence composition

## Status

Explicit opt-in additive profile for manifest-bound selected-evidence body reads.

`mcp-context-gateway.v0.1 + mvp-four-sources` remains exact. `mcp-context-gateway.v0.2 + estate-orientation-v0.2` remains exact. v0.3 keeps the same five source identities as v0.2 and adds one capability only to the existing KB Artifacts source.

## New resource

`matias-context://selected/kb-artifacts/{selection_id}`

The resource exposes only the canonical `selected.jsonl` belonging to a known KB Artifacts run. It is not arbitrary file access.

Read acceptance is fail-closed. The sibling selection manifest must:

- be a valid existing KB Artifacts manifest;
- come from a named corpus (`selection_request.corpus`);
- declare `selected.jsonl` as an output;
- contain `output_checksums.selected.jsonl` as a lowercase SHA-256;
- have `counts.selected` equal to the parsed selected-record count.

The selected body must match that checksum exactly. Every record must carry logical `corpus:` partition provenance. Physical input paths are rejected by the body contract and never returned.

## Everyday client

`mctx evidence SELECTION_ID`

The client performs one MCP selected-evidence read and returns `mctx.evidence@1` with the records, original selection request/counts, manifest/body integrity metadata and content-addressed selected-evidence identity.

## Why this exists

Media Monitor dogfood demonstrated the need. Media owns `producer-local:media-monitor.evidence-jsonl@1`; KB Artifacts selects a topic/date slice through its ordinary generic JSONL reader and named corpus; the legacy MCP manifest read proved provenance but could not expose what selected summaries said. v0.3 closes only that read gap.

## Non-goals

v0.3 does not:

- run Media Monitor or Knowledge Inspect;
- generate summaries;
- execute KB Artifacts selection/query logic;
- accept client filesystem paths or globs;
- expose `selected.csv`, `artifact.md`, or arbitrary run files;
- promote/publish evidence;
- add MCP tools/prompts/writes;
- perform research synthesis inside the server;
- change v0.1 or v0.2 behavior.

Reasoning remains client-side. The gateway transports already-governed, already-selected evidence with a cryptographic manifest/body join.
