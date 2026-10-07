

# AGENTS.md — Matías Context MCP

## Mission

Maintain the resource-only MCP gateway with exact v0.1 compatibility and an explicit, additive v0.2 estate-orientation profile, without expanding it into a larger platform.

The required path is:


MCP client
 logical URI
 registry
 policy authorization
 bounded filesystem read
 normalized provenance-rich response


## Authoritative documents

Read before modifying architecture:

* `docs/problem_brief.md`, when present;
* `docs/mcp_context_gateway_contract_v0_1.md`, when present;
* `README.md`;
* this file.

When implementation and contract disagree, report the disagreement. Do not silently change externally visible behavior.

## Scope

Included:

* explicit static v0.1/v0.2 profile selection;
* source catalog;
* source descriptors;
* mapped context documents;
* Projects / Project Agenda orientation documents in v0.2 only;
* deterministic `mctx bootstrap` composition over those ordinary resources;
* Knowledge Inspect manifests;
* KB Artifacts manifests;
* MCP over local `stdio`;
* resources capability;
* explicit errors;
* executable evidence.

Excluded:

* tools;
* server-side bootstrap tools or prompts;
* prompts;
* sampling;
* elicitation;
* HTTP;
* authentication;
* cloud deployment;
* writes;
* shell execution;
* dynamic repository discovery;
* semantic search;
* new databases;
* arbitrary filesystem access.

## Architectural invariants

1. Clients never submit physical filesystem paths.
2. Client responses never reveal physical filesystem paths.
3. Every filesystem read passes through the policy gate.
4. Only explicit source and document mappings are addressable.
5. Manifest locators are producer-specific and fixed.
6. The filesystem adapter accepts only `AuthorizedRead`.
7. The kernel does not import MCP SDK types.
8. Files are opened read-only and read with a hard byte limit.
9. Ambiguous or unsupported requests fail closed.
10. Do not add a second manifest-reading path.
11. Do not announce capabilities without registered behavior.
12. Do not normalize producer IDs by lowercasing physical run IDs.

## Profile compatibility rule

`mcp-context-gateway.v0.1 + mvp-four-sources` remains the exact four-source
compatibility profile. It must never require `PROJECTS_ROOT`, advertise Projects,
or emit v0.2 contract provenance.

`mcp-context-gateway.v0.2 + estate-orientation-v0.2` is an explicit opt-in
profile. It is exactly v0.1's four source definitions plus the bounded Projects
orientation source declared in `docs/mcp_context_gateway_contract_v0_2.md`.

Do not add dynamic profile discovery or silently map one config/profile pair to
another.

## Current trusted v0.1 state

As of 2026-10-07, the resource-only v0.1 trust boundary is closed and was
validated in PR #9.

Verified behavior:

* only the MCP resources capability is announced;
* all four mounted roots must present the exact expected `SYSTEM.yaml` identity;
* stable estate repository IDs are verified separately from current GitHub names;
* the exact verified declaration bytes are SHA-256 recorded for provenance;
* every advertised static document passes fail-closed startup preflight through
  the ordinary policy/filesystem/normalizer path;
* manifest locator containment is preflighted without enumerating run histories;
* the repaired Knowledge Inspect document mappings point only to current
  producer-owned documents;
* the catalog and source descriptors expose verified identity without physical
  roots;
* `make check` passes in CI;
* `make smoke` passes through a real fixture-backed MCP stdio session;
* the provenance-pinned Context Routing consumer proof passes through real MCP
  stdio;
* issues #4 and #5 are closed.

The normative source-profile and preflight changes are recorded in
`docs/amendments/trusted-source-preflight-2026-10-07.md`.

Do not resurrect the historical retrofit defect list as active work. New defects
belong in current reproducible issues with bounded acceptance criteria.

## Current v0.2 state

As of 2026-10-07, PR #11 proves the explicit five-source profile without
replacing v0.1:

* v0.2 is selected only by its exact config/profile pair;
* its first four source definitions are exactly the v0.1 source tuple;
* Projects is the only additional source;
* Projects exposes only STAFF, the Agenda guide/freshness contract, the
  deterministic Agenda index, and the eight current Agenda pages;
* the Agenda index is validated for producer-contract identity, record shape,
  repo-relative source path, and SHA-256 syntax;
* `make smoke-v02` performs a real stdio read of the Projects Agenda index;
* `make smoke` independently remains the four-source v0.1 acceptance path;
* no dynamic profile discovery or degraded v0.2 fallback exists.

Cross-resource comparison of Agenda page SHA-256 values to the index is not an
MCP-server responsibility. It is implemented by `mctx bootstrap` according to
`docs/mctx_bootstrap_contract_v1.md`.

## Bootstrap invariants

1. `mctx bootstrap` uses ordinary MCP resource reads only.
2. `--as-of` is explicit; do not introduce an implicit wall-clock fallback.
3. The client must verify Agenda resource SHA-256 against the producer-owned
   Agenda index before returning orientation.
4. REVIEW_DUE is a client orientation state, not a rewrite of producer semantic
   freshness.
5. A bootstrap packet is orientation evidence, not permission to bypass
   repository-local governance or runtime verification.

## Current bootstrap/adoption state

As of 2026-10-07:

* PR #13 proves `mctx.bootstrap@1` through the real CLI and MCP stdio path;
* the command performs four ordinary resource reads inside one session;
* it fails closed when the Agenda SHA-256 disagrees with the producer-owned
  Agenda index;
* explicit `--as-of` controls the REVIEW_DUE decision;
* PR #15's Media/Poverty experiment passes both refresh-needed and
  orientation-ready branches;
* the experiment shows 4 -> 1 CLI invocations and 4 -> 1 stdio sessions per
  case, while correctly remaining 4 -> 4 MCP reads;
* the experiment is an orchestration/adoption proof, not an LLM-quality or
  latency benchmark;
* Projects Staff now adopts bootstrap as the preferred cross-repository
  orientation entrypoint when the v0.2 profile is available.

## Current portfolio dogfood state

As of 2026-10-07:

* PR #18 adds `mctx.portfolio@1` as a two-read, client-side freshness-attention packet; it does not expand the MCP server;
* real estate dogfood routed review-due Media, Base de Datos and Job Search to the right refresh work;
* fresh authority checks exposed two within-window material-change misses (Poverty and Accounting), which were repaired upstream in Projects rather than hidden in MCP;
* Projects PRs #57–#59 refreshed those Agendas, adopted portfolio for estate sweeps, and tightened active review cadences where the observed operating tempo justified it;
* Calendar and ATS were successfully used as owning authorities without being copied into the gateway;
* FCV and LCD ready-room samples did not show material repository movement;
* no governed fresh material-activity artifact currently exists in Projects, so no commit-count/activity heuristic was added;
* the supported claim is **review-horizon / orientation attention**, not “what moved today?” detection or project priority;
* further portfolio features are paused until repeated real use exposes a concrete recurring friction.

See `docs/m8_portfolio_dogfood_2026-10-07.md`.

## Current M7 knowledge-composition state

As of 2026-10-07, the pinned cross-repository proof establishes one bounded
composition seam:

```text
Knowledge Inspect summary_bus
  -> producer-local:knowledge-inspect.evidence-jsonl@1
  -> KB Artifacts generic named-corpus selection
  -> path-safe selection manifest
  -> existing MCP KB Artifacts manifest resource
```

Invariants:

1. MCP does not parse Inspect-native artifacts or execute selection.
2. The Inspect adapter must strip producer-local physical paths.
3. The KB Artifacts composition path must use a named corpus profile so its
   operational manifest contains logical source aliases rather than direct input
   paths.
4. Adapter-output SHA-256 must equal the selector manifest input SHA-256.
5. MCP must return the already-safe manifest unchanged; do not add a second
   sanitizer to compensate for an unsafe producer path.
6. This proof covers `summary_bus/chunk_set_summary` only.
7. Promotion/publication and selected-evidence body transport remain outside the
   M7 proof.

## Required validation

Run the canonical surfaces:

```bash
make test
make check
make bootstrap-test
make adoption-experiment
make smoke
make smoke-v02
```

Verify:

```bash
git ls-files | grep -E '(^|/)(__pycache__/|.*\.py[co]$)'
```

returns nothing.

Verify no configured root occurs in any client response.

## Evidence contract

Preserve:

artifacts/mvp-evidence/
  initialize.json
  capabilities.json
  resources-list.json
  resource-templates-list.json
  source-catalog-response.json
  context-document-response.json
  knowledge-inspect-manifest-response.json
  kb-artifacts-manifest-response.json
  unauthorized-request-errors.json
  probe-summary.json
  probe-output.txt
  server-stderr.txt

artifacts/v02-evidence/
  source-catalog-response.json
  projects-agenda-index-response.json
  probe-summary.json
  probe-output.txt
  server-stderr.txt

artifacts/m6-adoption/
  report.json

Do not commit evidence containing physical roots or secrets.

## Completion report

Return:

1. files changed;
2. contract amendments;
3. commands run;
4. test results;
5. probe results;
6. exact evidence paths;
7. unresolved debt;
8. whether the resource-only MVP Definition of Done is met.



