# M8 portfolio dogfood — 2026-10-07

## Purpose

Test whether the estate-orientation MCP surface pays operational rent in real project re-entry / portfolio-review work before expanding the protocol or gateway.

The dogfood target was the smallest new client composition:

```text
mctx portfolio --as-of YYYY-MM-DD
```

It reads only the verified Projects source descriptor plus the producer-owned Agenda index and derives the same explicit review-window semantics already used by `mctx bootstrap`.

## Implementation result

PR #18 added `mctx.portfolio@1` without changing the MCP server capability surface.

- one real MCP stdio session;
- exactly two ordinary resource reads;
- no Agenda prose expansion;
- no GitHub/runtime calls;
- no LLM;
- no project-priority scoring;
- no writes or automatic Agenda refresh.

The first CI run caught an implementation defect in the shared freshness helper before merge. After repair, both the canonical W3 interface/check workflow and the M7 composition workflow passed. This was useful acceptance evidence for keeping portfolio logic in the client rather than weakening existing checks.

## Live dogfood method

The authorized Desktop Commander host was offline during this session, so the locally mounted `mctx` binary could not be exercised against the user's real checkout roots.

Two complementary paths were used instead:

1. repository CI exercised the implemented CLI through the existing fixture-backed real-MCP stdio path;
2. the same deterministic classification rule was evaluated against the live committed `projects/generated/project-agenda-index.json`, then the rooms it identified were checked against their actual owning authorities through GitHub, Google Calendar and ATS 2026.

This proves the portfolio packet logic plus real operating usefulness, but it is **not** a benchmark of local CLI latency or terminal presentation ergonomics.

## Cycle 1 — initial estate orientation

Against the live Projects index on 2026-10-07, the first packet was:

```text
total               8
refresh-needed      3
orientation-ready   5

refresh-needed:
  Base de Datos     review_due 2026-09-24
  Job Search        review_due 2026-10-01
  Media Monitor     review_due 2026-10-01
```

That routing was useful. Media Monitor had materially moved beyond its September stale-publication frontier.

However, Poverty was still inside its declared review window (due 2026-10-08) while fresh repository evidence showed multiple material gates had already closed: the IPC monetary parent had been explicitly approved, income-modeling had activated that exact approved lineage, and the durable basket candidate/consumer handoff had landed.

**Finding:** review-window freshness is not material-change detection.

Response: fix the upstream orientation, not the MCP classifier.

Projects PR #57:

- refreshed Media Monitor around the deployed product loop and narrow summary-reliability defect;
- refreshed Poverty around the consumed monetary gates and remaining Census/basket scientific frontiers;
- shortened both active-convergence review cadences to seven days;
- adopted `mctx portfolio` as the Staff estate-sweep entrypoint while retaining `mctx bootstrap` for a specific room;
- documented that review windows are a backstop, not repository observation.

After that merge, the same portfolio logic converged to **2 refresh-needed / 6 ready**.

## Cycle 2 — route stale rooms to external authorities

The remaining stale rooms were deliberately useful because their current truth did not live in GitHub.

### Base de Datos

The course Calendar showed that the old September exam/correction frontier was over. The live sequence was NoSQL continuation/practice followed by concurrency and recovery/logging blocks.

The Agenda was refreshed from Calendar authority rather than copying Calendar data into MCP.

### Job Search

`ATS 2026` was grounded as the canonical live Sheet. The current shelf included a closed BEON process, TELUS waiting on technical scheduling, two strong ZS rows still `ready_not_applied`, an immediate UNICEF deadline and a Fractal River application ready to execute.

The Agenda was refreshed from ATS authority; Job Search review cadence moved to seven days because its observed operating tempo was much faster than the previous 14-day window.

Projects PR #58 passed the full estate metadata check and merged.

After that merge, the same portfolio logic reached **0 refresh-needed / 8 ready** for 2026-10-07.

## Cycle 3 — audit the opposite failure mode

A green portfolio was not accepted as proof that every room was actually current. Three orientation-ready rooms were sampled against fresh repository evidence.

- FCV Research: no material repository movement was observed since the Agenda refresh; the WAITING_EXTERNAL posture remained credible.
- LCD Institutional Surfaces: no material repository movement was observed since the Agenda refresh; the adoption/institutionalization frontier remained credible.
- Accounting: material movement had occurred inside its 30-day review window. The backend/viewer had converged to a finished/private report library and the remaining issue had narrowed to final human acceptance/private delivery plus the bounded human number audit.

Accounting was therefore another **within-window material-change miss**.

Projects PR #59 refreshed Accounting and shortened its active convergence review cadence from 30 to 14 days. The owning repository checks passed.

## Residual defect investigated

Two real false negatives were observed during one intensive workday: Poverty and Accounting both moved materially before their declared review dates.

Before adding a new MCP feature, the Projects estate was checked for an already-governed activity signal that could be joined safely. Existing estate-observation / repository-context artifacts are topology/readiness observations and are not a fresh material-activity feed. The checked estate-observation summary itself was dated 2026-08-26.

No activity signal was added.

Reasons:

- raw commit count is not semantic material change;
- several important rooms are owned by non-GitHub authorities such as Calendar and ATS;
- the gateway must not become a GitHub sensing system;
- one day's dogfood is insufficient evidence for a new producer/contract;
- shorter review horizons already removed a large part of the observed mismatch at the correct upstream layer.

## What the experiment supports

The useful operating loop is now:

```text
mctx portfolio
    ↓
rooms needing freshness attention
    ↓
mctx bootstrap <room>
    ↓
fresh owning-authority evidence where required
    ↓
refresh Project Agenda only when materially justified
    ↓
mctx portfolio again
```

This loop worked across four materially different contexts:

- GitHub/runtime-heavy media repair;
- multi-repository scientific convergence;
- Calendar-owned live teaching;
- Sheet-owned job/application state;
- plus an orientation-ready Accounting audit that caught the opposite failure mode.

The value is **routing and bounded re-entry**, not live-state omniscience.

## What the experiment does not support

Do not currently describe `mctx portfolio` as:

- a 'what moved today?' detector;
- a project-priority engine;
- a substitute for repository/runtime observation;
- a Calendar/ATS/CRM data layer;
- a material-change classifier;
- an automatic Agenda refresher.

It is a deterministic **review-horizon / orientation-attention packet**.

## Stop decision

No further MCP feature is justified from this dogfood session.

Specifically, do not add:

- direct GitHub queries from the gateway;
- commit-count freshness heuristics;
- an LLM inside `mctx portfolio`;
- automatic Agenda mutation;
- another profile/protocol version;
- selective expansion flags merely because they are easy to implement.

Resume product development only when repeated real sessions expose the same concrete friction.

## Future trigger for a material-change hint

If multiple later sessions show that meaningful within-window changes repeatedly cause rework, commission a **Projects-owned observation artifact** rather than teaching MCP to inspect repositories directly.

A credible future contract would need to:

- map observed repositories/surfaces to Agenda IDs explicitly;
- distinguish activity evidence from semantic staleness;
- preserve non-GitHub owning authorities;
- produce an attention hint, not silently rewrite Agenda freshness;
- have evidence that it reduces real reconstruction work.

That work is deliberately not commissioned by this experiment.

## Remaining local dogfood gap

When the authorized local MCP host is available again, run the actual commands against the mounted v0.2 profile:

```bash
mctx portfolio --as-of 2026-10-07
mctx bootstrap media-monitor --as-of 2026-10-07
mctx bootstrap job-search --as-of 2026-10-07
```

Judge only terminal/operator ergonomics that CI cannot answer: startup feel, JSON readability, whether a compact renderer is genuinely missed, and whether selective expansion would remove repeated friction. Do not pre-build those features.
