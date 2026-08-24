<p align="center">
  <img src="https://raw.githubusercontent.com/trustabl/trustabl/main/assets/banner-rules.png" alt="Trustabl detection rules — the reliability and safety ruleset for AI agent SDKs" width="100%">
</p>

The detection rule packs the Trustabl scanner reads at scan time. Apache-2.0,
resolved by the engine on every scan — the engine ships with **no embedded
rules**. Looking for the threat model and rationale behind each rule? That's
[trustabl-rulebook](https://github.com/trustabl/trustabl-rulebook).

Ten packs: Claude Agent SDK, Claude skills, OpenAI Agents SDK, Google ADK, MCP
servers, LangChain / LangGraph, CrewAI, AutoGen, Pydantic AI, and the Vercel AI
SDK — across tool, agent, subagent, skill, and repo scopes.

These packs belong to [**Trustabl**](https://github.com/trustabl/trustabl), the
open-source tool for AI agent reliability — it finds and fixes reliability,
safety, and security defects in agent code. The engine resolves them from this
repository at scan time (cloning to a local cache, with offline fallback), so
rules can be added or changed without rebuilding or redistributing the binary.

Every `.yaml` file in this repo (except the top-level `manifest.yaml`) defines
one or more detection rules. The engine's loader walks this tree recursively,
decodes each file, validates it, and runs the matching rules against the SDKs
it discovers in a scanned project.

## How the engine consumes this repo

```
trustabl scan ./repo              # resolves the latest rules, caches, scans
trustabl rules pull               # download/refresh the cache without scanning
trustabl scan ./repo --rules-ref v1.0.0   # pin a tag/branch
trustabl scan ./repo --no-rules-update     # use the cached pack only (offline)
```

The resolved commit SHA of this repo is recorded on every scan result and
folded into the scan's `ScanID`, so a scan is honest about exactly which rule
pack produced it.

## `manifest.yaml` — the schema gate

`manifest.yaml` declares `schema_version`, the rule-schema contract this pack
targets. The engine refuses a pack whose `schema_version` exceeds what its
build supports, so a newer pack never silently misloads against an older
binary. Bump it in lockstep with any engine change that adds a predicate or
schema field.

## Layout

Rules are grouped by `<category>/<topic>.yaml`:

```
manifest.yaml                         schema_version (metadata, not a rule)
claude_sdk/                           Claude Agent SDK rules (CSDK-NNN)
├── agent_safety.yaml                 CSDK-101..105 (agent, python); CSDK-120..124, CSDK-130, CSDK-131 (agent, typescript)
├── code_execution.yaml               CSDK-107 (python), CSDK-011 (typescript)
├── error_handling.yaml               CSDK-005
├── idempotency.yaml                  CSDK-006 (python), CSDK-016 (typescript)
├── network.yaml                      CSDK-003
├── path_safety.yaml                  CSDK-004 (python), CSDK-012 (typescript fs-write)
├── repo.yaml                         CSDK-201, CSDK-202 (permission bypass), CSDK-204 (max_turns) — repo scope
├── repo_hygiene.yaml                 CSDK-203 (repo scope, CLAUDE.md missing)
├── shell_safety.yaml                 CSDK-108 (python), CSDK-010 (typescript)
├── ssrf.yaml                         CSDK-009 (python), CSDK-013 (typescript)
├── subagent_safety.yaml              CSDK-110..112 (subagent scope)
└── tool_definition.yaml              CSDK-001, CSDK-002, CSDK-007, CSDK-008, CSDK-017, CSDK-018 (python); CSDK-014 (typescript)
openai_sdk/                           OpenAI Agents SDK rules (OAI-NNN)
├── agent_safety.yaml                 OAI-101..104, OAI-109, OAI-110, OAI-112 (agent); OAI-105 (agent, typescript)
├── approvals.yaml                    OAI-014, OAI-111 (needs_approval gates)
├── code_execution.yaml               OAI-013 (python), OAI-017 (typescript)
├── decorator_config.yaml             OAI-003, OAI-004, OAI-015
├── error_handling.yaml               OAI-008
├── idempotency.yaml                  OAI-009 (python), OAI-019 (typescript)
├── mcp_safety.yaml                   OAI-106 (agent scope, MCP-gated)
├── network.yaml                      OAI-005, OAI-011, OAI-018 (python); OAI-016, OAI-024 (typescript)
├── observability.yaml                OAI-010
├── path_safety.yaml                  OAI-006
├── repo_hygiene.yaml                 OAI-202 (repo scope, CLAUDE.md missing)
├── shell_safety.yaml                 OAI-012
├── tool_definition.yaml              OAI-001, OAI-002, OAI-007 (python), OAI-022 (typescript)
└── tracing.yaml                      OAI-201 (repo scope)
google_adk/                           Google ADK rules (ADK-NNN)
├── agent_safety.yaml                 ADK-101..108, ADK-110 (agent); ADK-109 (agent, typescript)
├── builtin_tools.yaml                ADK-008 (BashTool policy gate, agent scope)
├── code_execution.yaml               ADK-011 (python), ADK-015 (typescript)
├── error_handling.yaml               ADK-005
├── idempotency.yaml                  ADK-006
├── network.yaml                      ADK-003
├── path_safety.yaml                  ADK-004
├── repo_hygiene.yaml                 ADK-201 (repo scope, CLAUDE.md missing)
├── shell_safety.yaml                 ADK-010
├── ssrf.yaml                         ADK-012 (python), ADK-016 (typescript)
└── tool_definition.yaml              ADK-001, ADK-002, ADK-007, ADK-009 (python), ADK-013 (typescript)
mcp/                                  Model Context Protocol rules (MCP-NNN)
├── code_execution.yaml               MCP-009, MCP-014
├── error_handling.yaml               MCP-006
├── idempotency.yaml                  MCP-007
├── network.yaml                      MCP-004
├── path_safety.yaml                  MCP-005
├── shell_safety.yaml                 MCP-010, MCP-012
├── ssrf.yaml                         MCP-008, MCP-013
└── tool_definition.yaml              MCP-001..003 (python), MCP-011 (typescript), MCP-015..022 (go, csharp, php, rust)
claude_skill/                         Claude Code skill rules (CSKILL-NNN, all skill scope)
├── skill_quality_text.yaml           CSKILL-080..086
└── skill_safety.yaml                 CSKILL-001..003, 010, 011, 020, 030, 040, 050, 060, 061, 070, 071
langchain/                            LangChain / LangGraph rules (LC-NNN)
├── agent_safety.yaml                 LC-101, LC-102 (agent); LC-111 (agent, typescript)
├── code_execution.yaml               LC-004 (python), LC-012 (typescript)
├── repo_hygiene.yaml                 LC-201 (repo scope, AGENTS.md/CLAUDE.md missing)
├── shell_safety.yaml                 LC-003 (python), LC-011 (typescript)
├── ssrf.yaml                         LC-005 (python), LC-013 (typescript)
├── tool_behavior.yaml                LC-006 (python), LC-014 (typescript)
└── tool_definition.yaml              LC-001, LC-002 (python); LC-010 (typescript)
crewai/                               CrewAI rules (CREW-NNN, all python)
├── agent_safety.yaml                 CREW-101, CREW-102, CREW-104, CREW-110 (agent)
├── code_execution.yaml               CREW-103 (agent), CREW-003 (tool)
├── dangerous_tools.yaml              CREW-106, CREW-107, CREW-109 (agent)
├── idempotency.yaml                  CREW-006
├── repo_hygiene.yaml                 CREW-201 (repo scope, AGENTS.md/CLAUDE.md missing)
├── shell_safety.yaml                 CREW-004
├── ssrf.yaml                         CREW-005
├── tool_behavior.yaml                CREW-108
└── tool_definition.yaml              CREW-001, CREW-002
autogen/                              AutoGen / AG2 rules (AG2-NNN, all python)
├── agent_safety.yaml                 AG2-001, AG2-002, AG2-004..006 (agent)
├── code_execution.yaml               AG2-010
├── network.yaml                      AG2-012
├── repo_hygiene.yaml                 AG2-201 (repo scope, AGENTS.md/CLAUDE.md missing)
├── shell_safety.yaml                 AG2-009
├── ssrf.yaml                         AG2-011
└── tool_definition.yaml              AG2-007, AG2-008
pydantic_ai/                          Pydantic AI rules (PYD-NNN, all python)
├── agent_safety.yaml                 PYD-101..103, PYD-105, PYD-106 (agent)
├── code_execution.yaml               PYD-004
├── idempotency.yaml                  PYD-007
├── network.yaml                      PYD-006
├── repo_hygiene.yaml                 PYD-201 (repo scope, AGENTS.md/CLAUDE.md missing)
├── shell_safety.yaml                 PYD-003
├── ssrf.yaml                         PYD-005
└── tool_definition.yaml              PYD-001, PYD-002
vercel_ai/                            Vercel AI SDK rules (VAI-NNN, all typescript)
├── agent_safety.yaml                 VAI-006..009 (agent)
├── code_execution.yaml               VAI-002
├── network.yaml                      VAI-011
├── repo_hygiene.yaml                 VAI-012 (repo scope, AGENTS.md/CLAUDE.md missing)
├── shell_safety.yaml                 VAI-001
├── ssrf.yaml                         VAI-003
└── tool_definition.yaml              VAI-004, VAI-005
```

ID prefix denotes SDK; `NNN` tool scope, `1NN` agent / subagent scope, `2NN`
repo scope. Two packs predate that convention: `autogen/` numbers its agent
rules AG2-001..006 in the tool range, and `claude_skill/` groups CSKILL-NNN by
topic rather than scope (every rule there is skill scope). The rule count is not written down here — it changes on every rule
ship. `trustabl rules validate` strict-loads the whole pack and is the
authoritative count; counting `.yaml` files undercounts, since one file can
hold several rules.

The category is the first path segment. Group related rules into a topic file;
1–5 rules per file reads best. The loader walks recursively, so a new category
directory just works once the engine recognizes its `category:` value.

> An `openshell/` pack (OSH-001..005, NVIDIA OpenShell sandbox rules) used to
> live here; it moved to a closed-source companion project. Don't author new
> OSH rules in this repo.

## Authoring rules

The rule schema (every accepted field, with annotations) and the predicate
implementations live in the **engine** repository, not here:

- Schema reference: [`internal/rules/schema.yaml`](https://github.com/trustabl/trustabl/blob/main/internal/rules/schema.yaml)
- Schema types (authoritative): [`internal/rules/schema.go`](https://github.com/trustabl/trustabl/blob/main/internal/rules/schema.go)

Read the schema reference before authoring a rule. The full rule-authoring
contract — required fields, ID conventions, per-scope `applies_to` values,
severity/confidence guidance, and the cross-SDK framing discipline — is in
[`CLAUDE.md`](CLAUDE.md) in this repo.

A rule needing a predicate that doesn't exist yet is a change in the **engine**
repo (schema.go + predicates.go + evaluator.go + schema.yaml), not here. Bump
`manifest.yaml`'s `schema_version` in lockstep and tag a release of this repo
that requires the new engine build.
