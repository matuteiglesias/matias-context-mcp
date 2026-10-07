# mctx bootstrap contract v1

## Status

**Deterministic client-side composition over ordinary MCP resource reads.**

`mctx bootstrap` does not add an MCP tool, prompt, resource family, server-side
join, or server-side freshness calculation. It is an everyday client operation
that composes existing v0.2 resources inside one MCP stdio session.

## Invocation

```bash
mctx bootstrap AGENDA_ID --as-of YYYY-MM-DD
```

`--as-of` is required. The command deliberately has no implicit current-date
fallback so the same resource bytes plus the same explicit date produce the same
bootstrap packet.

The operation requires the explicit v0.2 estate-orientation profile. A v0.1
server has no Projects source and the client returns
`bootstrap_requires_v02`.

## Resource reads

For a known Agenda, the client performs exactly four ordinary MCP reads:

1. `matias-context://source/projects`
2. `matias-context://source/projects/document/agenda-index`
3. `matias-context://source/projects/document/{agenda_id}`
4. `matias-context://source/projects/document/staff-operating-model`

No physical path is used or returned.

The Agenda index is read before the Agenda document. An unknown Agenda therefore
fails from the producer-owned index before the client attempts a document URI.

## Provenance join

The client requires:

```text
Agenda resource.resource.sha256
==
Agenda index.agendas[agenda_id].source_sha256
```

A mismatch fails closed with `agenda_index_mismatch`.

The packet also carries:

- Projects verified source identity and declaration SHA-256;
- Agenda-index resource SHA-256;
- Agenda resource SHA-256;
- STAFF resource SHA-256.

The server remains responsible for source identity and resource preflight. The
client is responsible only for this cross-resource consistency join.

## Orientation state

The client derives one of two states from the producer record and explicit
`as_of` date:

```text
declared_freshness == STALE
    -> refresh-needed / declared-stale

as_of >= review_due_on
    -> refresh-needed / review-due

otherwise
    -> orientation-ready / within-review-window
```

A review-due Agenda is not rewritten to semantic `STALE`. The packet preserves
the producer's declared freshness and adds a warning that the Agenda must be
refreshed before its frontier is treated as current execution guidance.

## Packet

The output contract is `mctx.bootstrap@1`.

It contains:

- `agenda_id`;
- explicit `as_of`;
- `orientation_state`;
- producer freshness metadata and reason;
- exact Agenda index record;
- Agenda Markdown text;
- STAFF operating-model Markdown text;
- verified Projects source identity;
- resource provenance;
- warnings.

The packet is intentionally an orientation handoff, not authority. Repository
local files, runtime evidence, current branches, and repository-local governance
remain mandatory before implementation.

## Non-goals

v1 does not:

- refresh an Agenda;
- mutate Projects or Control Tower state;
- parse Agenda prose into a new semantic model;
- discover repositories dynamically;
- read repository-context or producer-observability surfaces;
- call an LLM;
- execute participating repositories;
- add server capabilities;
- persist bootstrap output automatically.
