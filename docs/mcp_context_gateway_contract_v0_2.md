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
| `estate-sensing-observability` | `estate/agendas/estate-sensing-observability.md` |
| `office-execution-loop` | `estate/agendas/office-execution-loop.md` |
| `context-discovery-mcp` | `estate/agendas/context-discovery-mcp.md` |
| `knowledge-evidence-fabric` | `estate/agendas/knowledge-evidence-fabric.md` |
| `youtube-following-product` | `estate/agendas/youtube-following-product.md` |
| `public-professional-publishing` | `estate/agendas/public-professional-publishing.md` |
| `census-query-product` | `estate/agendas/census-query-product.md` |
| `rxdb-census-extraction` | `estate/agendas/rxdb-census-extraction.md` |
| `census-sampling-alignment` | `estate/agendas/census-sampling-alignment.md` |
| `price-basket-science` | `estate/agendas/price-basket-science.md` |
| `engho-consumption-research` | `estate/agendas/engho-consumption-research.md` |
| `eph-labor-state` | `estate/agendas/eph-labor-state.md` |
| `argentina-geography` | `estate/agendas/argentina-geography.md` |
| `electoral-data` | `estate/agendas/electoral-data.md` |
| `economic-scaling-research` | `estate/agendas/economic-scaling-research.md` |
| `teaching-tools` | `estate/agendas/teaching-tools.md` |
| `lcd-knowledge-corpus` | `estate/agendas/lcd-knowledge-corpus.md` |
| `site-factory-workflow` | `estate/agendas/site-factory-workflow.md` |
| `political-knowledge-sources` | `estate/agendas/political-knowledge-sources.md` |

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

A missing Projects checkout, wrong Projects identity, missing/malformed Agenda
index, unsupported Agenda-index contract identity, or missing mapped Agenda file
prevents v0.2 startup. It has no degraded four-source fallback.

Startup validates the Agenda index's producer contract identity, record shape,
repo-relative source path and SHA-256 syntax. It does not compare each recorded
source hash with the concurrently mounted Agenda page. That cross-resource
consistency check remains a producer/client integrity responsibility and is
intended for the later deterministic bootstrap composition.

## Agenda semantics

`generated/project-agenda-index.json` is producer-owned
`context:project-agendas@1`.

The gateway exposes it as bounded JSON validated against the producer contract
identity and does not reinterpret its freshness model. In particular, MCP v0.2
does not:

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

## Expanded Projects Agenda allowlist — October 2026

This is an additive set of 19 reviewed **logical document mappings** for the
`projects` source, matching the 27-record Projects Agenda index proposed in
[Projects PR #63](https://github.com/matuteiglesias/projects/pull/63).
The gateway continues using exactly the same v0.2 resource URI family and five
source identities; v0.1 retains its four-source profile unchanged. v0.3 shares
the v0.2 Projects mapping and preserves its selected-evidence boundary.

**Deployment sequence:** first merge Projects PR #63, refresh the operator's
`PROJECTS_ROOT` checkout to that Projects main commit, and verify
`make agenda-check`. Only then upgrade the installed MCP package to this
mapping set; startup fails closed if any mapped Agenda document is missing.

New Agenda files are documentation-seeded orientation, not guaranteed live
project status. Their `front_ids` remain unmapped until Control Tower identity
reconciliation. A `mctx bootstrap` result is not authority to execute.
