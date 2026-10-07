# M7 knowledge composition proof

M7 closes one narrow composition seam:

```text
Knowledge Inspect governed summary_bus
    -> producer-owned generic evidence JSONL adapter
    -> KB Artifacts generic selector
    -> selected-evidence run + safe operational manifest
    -> existing MCP KB Artifacts manifest resource
```

No new MCP capability is introduced.

## Authority chain

Knowledge Inspect owns:

- its native `summary_bus / chunk_set_summary` meaning;
- `producer-local:knowledge-inspect.evidence-jsonl@1`;
- deterministic projection of that source-specific artifact into generic JSONL.

KB Artifacts owns:

- generic JSONL normalization;
- deterministic selection;
- selected-evidence artifact identity;
- selection manifests and promotion mechanics.

MCP owns only:

- bounded read-only transport of the already-produced KB Artifacts manifest.

Projects owns the cross-repository graph projection, not this runtime flow.

## Acceptance proof

The cross-repository CI proof pins exact producer and selector commits. It:

1. executes the real Knowledge Inspect adapter against the producer-owned
   sanitized summary fixture;
2. consumes the emitted JSONL through KB Artifacts' existing generic reader;
3. selects through a named corpus profile so provenance uses logical corpus
   aliases;
4. verifies adapter-output SHA-256 equals the KB Artifacts manifest input
   SHA-256;
5. verifies one content-addressed selected-evidence artifact;
6. mounts the real producer and selector checkouts into the existing v0.1 MCP
   gateway;
7. reads
   `matias-context://manifest/kb-artifacts/m7-knowledge-inspect-fixture`;
8. verifies MCP returns the same safe manifest and leaks no physical producer
   roots.

## Privacy boundary

The Knowledge Inspect adapter strips source-local physical paths.

The KB Artifacts proof uses a named corpus profile. That is mandatory for this
composition path because direct globs would retain filesystem paths in the
legacy operational manifest, while a named corpus profile records logical
source IDs instead.

MCP does not add a second sanitizer. It accepts only the already-safe manifest
produced by the proven composition path.

## Non-goals

M7 does not:

- promote or publish selected evidence;
- add an MCP selected-evidence body endpoint;
- expose arbitrary JSONL or artifact directories;
- make Knowledge Inspect responsible for selection;
- make KB Artifacts responsible for Inspect-native parsing;
- introduce a shared KB Contracts schema prematurely;
- claim this one adapter is a universal knowledge interchange format.
