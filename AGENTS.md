

# AGENTS.md — Matías Context MCP

## Mission

Conclude the resource-only MCP v0.1 vertical slice without expanding it into a larger platform.

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

* source catalog;
* source descriptors;
* mapped context documents;
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

## Current validated state

* 30 tests pass.
* Server starts with clean `stdout`.
* MCP initialization succeeds.
* Only resources capability is announced.
* Source catalog works.
* KB Contracts real document read works.
* Basic rejection evidence works.

## Current P0 defects

### P0-1 — Manifest identifier grammar

Real producer IDs include uppercase timestamp separators:

The current identifier grammar rejects them.

Implement separate identifier classes:

* source IDs: lowercase;
* producer IDs: lowercase;
* document IDs: lowercase;
* manifest IDs: producer-native case, single segment, bounded, and restricted to letters, digits, `.`, `_`, and `-`.

Preserve manifest ID case exactly when applying the fixed locator.

Update the contract or add an explicit v0.1 amendment. Do not silently diverge from documentation.

### P0-2 — Knowledge Inspect producer identity

Do not assume the repository name is the manifest's internal producer identity.

Inspect:

The public contract identifies the stable module producer as `kb`.

Represent separately:

* gateway producer ID: `knowledge-inspect`;
* accepted source-local manifest producer identity: `kb`.

Do not use fuzzy name matching.

### P0-3 — Real manifest fixtures

Copy sanitized representative manifests into test fixtures:


Fixtures must not include local physical paths, secrets, user data or large bodies.

Tests must use the same codecs as production.

### P0-4 — Probe finalization

`scripts/probe_mcp.py` must always produce:

probe-summary.json
probe-output.txt
server-stderr.txt

even when one check fails.

Requirements:

* catch expected MCP errors per check;
* record `PASS`, `FAIL`, or `SKIP`;
* finish all independent checks where safe;
* write the summary in a `finally` path;
* return nonzero when a required check fails;
* avoid an unhandled `ExceptionGroup`;
* clearly distinguish required checks from optional checks.

### P0-5 — Real manifest path

Demonstrate both:

matias-context://manifest/knowledge-inspect/{real_id}
matias-context://manifest/kb-artifacts/{real_id}

Evidence must include:

* logical URI;
* producer ID;
* manifest ID;
* authority;
* content media type;
* byte size;
* SHA-256;
* modification timestamp;
* normalized summary;
* original parsed manifest body.

## P1 defects

### P1-1 — Static write scan false positives

The existing shell check must detect actual write-capable calls, not words such as `str.replace`.

Use a narrow pattern such as:

\.(write_text|write_bytes|unlink|rename|rmdir|mkdir|chmod)\(
subprocess\.
os\.system\(

It is only a supporting check. Tests and code review remain authoritative.

### P1-2 — Pytest asyncio warning

Set the fixture loop scope explicitly under `[tool.pytest.ini_options]` when `pytest-asyncio` is present:

asyncio_default_fixture_loop_scope = "function"

Do not add async test infrastructure unless needed.

### P1-3 — Source-line review

The runtime package is currently above the approximate v0.1 budget.

Before reducing it:

1. report line counts by module;
2. identify duplication and overly verbose validation;
3. distinguish necessary security logic from accidental ceremony;
4. avoid compressed or clever code that weakens auditability.

Prefer removing duplicated representations or unused abstraction. Do not optimize only for a numeric target.

### P1-4 — Error evidence

Add end-to-end evidence for:

* unknown source;
* unknown document;
* invalid manifest identifier;
* unknown producer;
* unknown run;
* malformed JSON;
* malformed manifest;
* symlink escape;
* oversized document;
* oversized manifest.

## Required validation

Run:

python3 -m compileall -q src scripts tests
python3 -m pytest -q
python3 scripts/probe_mcp.py --output-dir artifacts/mvp-evidence
git diff --check

Verify:

git ls-files | grep -E '(^|/)(__pycache__/|.*\.py[co]$)'

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



