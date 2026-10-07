# MCP Context Gateway Contract v0.2

## Status

**Explicit opt-in estate-orientation profile.**

v0.2 extends the trusted resource-only gateway with one additional governed
source: `projects`. It does not replace or silently upgrade v0.1.

The original configuration pair remains valid and unchanged:

```text
mcp-context-gateway.v0.1 + mvp-four-sources
```

The new profile is selected only by:

```text
mcp-context-gateway.v0.2 + estate-orientation-v0.2
```

Configuration/profile pairs are exact and cannot be mixed.

## Source set

v0.2 contains the exact four v0.1 sources, in the same order and with the same
document and manifest mappings, plus:

```text
source_id: projects
root_env: PROJECTS_ROOT
repository.id: repo.projects
repository.github: matuteiglesias/projects
declaration_id: portfolio.github-estate.registry
system: portfolio.github-estate
role: estate_orientation
authority: control-plane
```

The Projects source exposes only this allowlist:

| document_id | producer path |
|---|---|
| `staff-operating-model` | `STAFF.md` |
| `agenda-guide` | `estate/agendas/README.md` |
| `agenda-freshness-contract` | `docs/project-agenda-freshness.md` |
| `agenda-index` | `generated/project-agenda-index.json` |
| `accounting-family` | `estate/agendas/accounting-family.md` |
| `base-de-datos-2c-2026` | `estate/agendas/base-de-datos-2c-2026.md` |
| `fcv-research` | `estate/agendas/fcv-research.md` |
| `job-search` | `estate/agendas/job-search.md` |
| `lcd-institutional-surfaces` | `estate/agendas/lcd-institutional-surfaces.md` |
| `media-monitor` | `estate/agendas/media-monitor.md` |
| `poverty-ecosystem` | `estate/agendas/poverty-ecosystem.md` |
| `relationships-opportunities` | `estate/agendas/relationships-opportunities.md` |

Projects has no gateway manifest profile.

## Trust and preflight

The trusted-source requirements introduced by the v0.1 amendment remain
normative for every v0.2 source.

Before MCP startup, the gateway:

1. verifies the exact expected `SYSTEM.yaml` semantic identity;
2. records the exact declaration SHA-256;
3. constructs the selected static registry;
4. preflights every mapped static document through the normal
   policy/filesystem/normalizer path;
5. validates fixed manifest locator containment for the existing manifest
   producers without enumerating run histories.

A missing Projects checkout, wrong Projects identity, stale/missing Agenda index,
or missing mapped Agenda file prevents v0.2 startup. It has no degraded
four-source fallback.

## Agenda semantics

`generated/project-agenda-index.json` is producer-owned
`context:project-agendas@1`.

The gateway exposes it as bounded generic JSON and does not reinterpret its
freshness model. In particular, MCP v0.2 does not:

- calculate a current `as_of` date;
- turn `review_due_on` into semantic staleness;
- refresh an Agenda;
- mutate Control Tower or repository state;
- compose a bootstrap packet.

Those are consumer/client concerns. Deterministic bootstrap composition is a
separate later phase.

## MCP surface

v0.2 keeps the v0.1 logical resource namespace:

```text
matias-context://catalog/sources
matias-context://source/{source_id}
matias-context://source/{source_id}/document/{document_id}
matias-context://manifest/{producer_id}/{manifest_id}
```

Only the resources capability is announced. No tools, prompts, writes, HTTP,
sampling, elicitation, shell execution, recursive browsing, dynamic repository
discovery, vector search, or source mutation are added.

## v0.1 compatibility

When the v0.1 configuration is selected:

- `PROJECTS_ROOT` is not required;
- the catalog still contains exactly four sources;
- the catalog provenance remains `mvp-four-sources`;
- resource envelopes still report `mcp-context-gateway.v0.1`;
- Projects is not addressable;
- the existing v0.1 smoke remains the default `make smoke`.

The separate `make smoke-v02` acceptance path proves the five-source profile.
