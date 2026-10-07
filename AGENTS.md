

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
* Knowledge Inspect manifests;
* KB Artifacts manifests;
* MCP over local `stdio`;
* resources capability;
* explicit errors;
* executable evidence.

Excluded:

* tools;
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

## Required validation

Run the canonical surfaces:

```bash
make test
make check
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



