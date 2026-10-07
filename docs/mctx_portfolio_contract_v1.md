# mctx portfolio contract v1

## Status

**Deterministic client-side portfolio orientation over ordinary MCP resource reads.**

`mctx portfolio` does not add an MCP tool, prompt, resource family, server-side
join, ranking model, or dynamic repository discovery. It composes the existing
Projects source descriptor and producer-owned Agenda index inside one MCP stdio
session.

## Invocation

```bash
mctx portfolio --as-of YYYY-MM-DD
```

`--as-of` is required. The same resource bytes plus the same explicit date must
produce the same packet.

The operation requires the explicit v0.2 estate-orientation profile. A v0.1
server returns `portfolio_requires_v02`.

## Resource reads

The client performs exactly two ordinary MCP reads:

1. `matias-context://source/projects`
2. `matias-context://source/projects/document/agenda-index`

It deliberately does not read individual Agenda documents or `STAFF.md`.
Those remain the job of `mctx bootstrap AGENDA_ID --as-of ...` after the
portfolio packet identifies a room that deserves attention.

## Orientation state

Each Agenda record uses the same deterministic freshness rule as bootstrap:

```text
declared_freshness == STALE
    -> refresh-needed / declared-stale

as_of >= review_due_on
    -> refresh-needed / review-due

otherwise
    -> orientation-ready / within-review-window
```

`review_delta_days` is `as_of - review_due_on` in whole days. Positive values
mean overdue, zero is the due-date boundary, and negative values mean days
remaining.

## Ordering

The packet is ordered for **freshness attention only**:

1. `refresh-needed` before `orientation-ready`;
2. semantic `declared-stale` before ordinary `review-due`;
3. earlier `review_due_on` first;
4. `agenda_id` as the stable tie-breaker.

This ordering is explicitly **not project priority**. It does not claim value,
urgency, payoff, execution order, or portfolio ranking.

## Packet

The output contract is `mctx.portfolio@1`.

It contains:

- explicit `as_of`;
- total / refresh-needed / orientation-ready counts;
- one bounded row per indexed Agenda;
- producer posture and freshness metadata already present in the index;
- derived orientation state, reason and review delta;
- exact Agenda source SHA-256 from the producer-owned index;
- verified Projects source identity;
- provenance for the two MCP resources used.

The packet does not include Agenda prose.

## Non-goals

v1 does not:

- refresh an Agenda;
- infer material change from GitHub activity;
- rank projects by payoff or urgency;
- query repositories, workflows, issues or runtime systems;
- parse Agenda prose;
- expand selected Agendas automatically;
- call an LLM;
- mutate Projects or Control Tower state;
- replace `mctx bootstrap`.

The intended dogfood loop is:

```text
mctx portfolio
    -> choose rooms whose orientation needs attention
    -> mctx bootstrap only those rooms
    -> inspect fresh authority/runtime evidence where required
    -> refresh upstream Agenda truth when materially justified
    -> rerun portfolio
```
