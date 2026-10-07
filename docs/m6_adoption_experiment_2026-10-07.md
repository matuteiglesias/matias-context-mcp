# M6 bootstrap adoption experiment — 2026-10-07

## Purpose

Test whether `mctx bootstrap` materially simplifies governed estate
orientation without changing the underlying source reads or freshness
semantics.

This is a bounded transport/orchestration adoption proof. It is not an LLM
quality benchmark.

## Cases

The experiment uses two already-declared Agenda IDs:

- `media-monitor` — fixture state is review-due on the experiment date;
- `poverty-ecosystem` — fixture state remains within its review window.

The public fixture intentionally contains synthetic posture/front metadata.
Private Projects operating metadata is not copied into this repository.

The experiment date is fixed at:

```text
2026-10-07
```

## Control

The control reconstructs one orientation packet using four separate ordinary
client invocations:

```text
mctx read matias-context://source/projects
mctx read matias-context://source/projects/document/agenda-index
mctx read matias-context://source/projects/document/<agenda>
mctx read matias-context://source/projects/document/staff-operating-model
```

Each `mctx read` starts and initializes its own MCP stdio session.

The control then manually performs the same two joins required for safe
orientation:

1. compare Agenda resource SHA-256 with the Agenda-index `source_sha256`;
2. compare the explicit `as_of` date with `review_due_on` while preserving
   the producer's declared semantic freshness.

## Treatment

The treatment runs:

```text
mctx bootstrap <agenda> --as-of 2026-10-07
```

It starts one MCP stdio session and performs the same four ordinary MCP resource
reads internally.

## Required equivalence

For each case, control and treatment must agree on:

- Agenda ID;
- orientation state;
- freshness reason;
- review due date;
- declared freshness;
- Agenda/index SHA consistency;
- verified Projects repository identity;
- presence of the STAFF authority-boundary warning.

The expected treatment states are:

```text
media-monitor       -> refresh-needed
poverty-ecosystem   -> orientation-ready
```

## Metrics

The experiment records, per Agenda:

| Metric | Control | Bootstrap |
|---|---:|---:|
| CLI invocations | 4 | 1 |
| MCP stdio sessions | 4 | 1 |
| MCP resource reads | 4 | 4 |
| manual provenance/freshness join outside client | yes | no |

So a passing result demonstrates a 75% reduction in client invocations and
stdio-session setup, with no claim that the underlying governed resource-read
count is reduced.

## Execution

```bash
make adoption-experiment
```

The deterministic report is written to:

```text
artifacts/m6-adoption/report.json
```

CI executes this target after the independent v0.1 and v0.2 stdio smoke tests.

## Interpretation boundary

A PASS means the new client surface eliminates repeated orientation
orchestration while preserving governed source identity, freshness semantics,
the STAFF authority boundary, and cross-resource SHA consistency.

It does **not** establish:

- faster wall-clock latency on every machine;
- improved LLM reasoning quality;
- fewer MCP resource reads;
- permission to execute a review-due Agenda;
- permission to bypass repository-local `AGENTS.md`, `SYSTEM.yaml`, current
  branches, tests, or runtime evidence.

A review-due result remains a refresh signal. An orientation-ready result is
still only the starting point for repository-local inspection.
