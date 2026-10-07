---
title: MCP Context Gateway v0.1 Amendment — Trusted Source Preflight
contract_id: mcp-context-gateway
contract_version: "0.1"
amendment_id: trusted-source-preflight-2026-10-07
status: approved
effective: 2026-10-07
---

# Trusted source preflight amendment

This amendment repairs source-profile drift and closes the mounted-source trust
boundary without changing the resource-only, local-stdio scope of v0.1.

## 1. Normative source identity

Every configured source root MUST contain a bounded, regular, UTF-8 YAML
`SYSTEM.yaml` declaration. Startup verifies these exact semantic fields before a
source can enter the registry:

| source_id | schema_version | declaration id | repository.id | repository.github | system |
|---|---:|---|---|---|---|
| context-routing | 1 | `kb.context-routing.catalog` | `repo.context` | `matuteiglesias/context-routing` | `kb.context-routing` |
| kb-contracts | 1 | `kb.contracts.registry` | `repo.kb-contracts` | `matuteiglesias/kb-contracts` | `kb.contracts` |
| knowledge-inspect | 1 | `kb.inspect.runtime` | `repo.knowledge-inspect` | `matuteiglesias/knowledge-inspect` | `kb.inspect` |
| kb-artifacts | 1 | `kb.artifacts.selector` | `repo.gpt-digests` | `matuteiglesias/kb-artifacts` | `kb.artifacts` |

GitHub repository renames do not mint new estate repository identities. The
gateway therefore verifies the stable estate IDs while retaining current GitHub
repository names.

The exact bytes of the verified declaration are SHA-256 hashed for provenance.
That hash is not itself semantic producer identity.

## 2. Repaired static document profile

The v0.1 mapped-document allowlist is amended to the following current
producer-owned resources:

### Context Routing

- `routing-overview` -> `README.md`
- `published-source-catalog` -> `static/context-data/v1/sources.json`

### KB Contracts

- `manual-overview` -> `README.md`

### Knowledge Inspect

- `module-definition` -> `docs/modules/kb-module-definition.md`
- `architecture-freeze` -> `docs/architecture/knowledge-inspect-architecture-freeze.md`
- `operator-runbook` -> `runbooks/kb_module_runbook.md`

The former Knowledge Inspect mappings `module-overview`,
`artifact-surface`, and `health-contract` are withdrawn because their mapped
files are no longer present in the current producer repository. The gateway does
not recreate obsolete producer documentation merely to satisfy an old mapping.

### KB Artifacts

- `selector-overview` -> `README.md`
- `operator-guide` -> `docs/index.md`

No recursive documentation browsing is introduced.

## 3. Fail-closed startup preflight

After configuration and source identity verification, startup MUST preflight
every mapped static document through the same resource kernel used for client
reads. A mapped document must therefore pass the existing containment,
regular-file, allowed-format, byte-limit, bounded-read, UTF-8/JSON parsing and
configured codec checks before the catalog can be advertised.

If any required source identity or mapped static document fails, startup fails
before MCP operation. v0.1 does not provide a degraded or partially healthy
catalog.

Manifest families remain request-addressed. Startup MUST validate the fixed
locator shape, allowed extension and resolved containment of a representative
locator without enumerating producer run directories or requiring any run to
exist.

## 4. Catalog and descriptor identity

The source catalog and source descriptors add an `identity` object containing:

- `schema_version`
- `declaration_id`
- `repository_id`
- `github`
- `system`
- `verification: "verified"`
- `declaration_sha256`

No physical root or `SYSTEM.yaml` path is returned.

## 5. Unchanged boundaries

This amendment does not add tools, prompts, writes, HTTP transport, dynamic
repository discovery, recursive browsing, semantic search, shell execution,
authentication, remote attestation, or producer mutation.

Verifying `SYSTEM.yaml` proves that the mounted root presents the exact
governed source declaration expected by the frozen profile. It is not a
cryptographic attestation of GitHub provenance.
