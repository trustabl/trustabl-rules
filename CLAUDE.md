# Instructions for Claude — Trustabl detection rules

These instructions apply to any work on the detection rule packs in this
repository. The packs here are pulled by the
[Trustabl engine](https://github.com/trustabl/trustabl) at scan time; the rule
**schema** and **predicate** implementations, plus the per-rule test harness,
live in that engine repository. Links below labeled "engine repo" point there.

## Engine/rules split — read this first

- **Rules** (the `.yaml` packs) live **here**.
- **Schema, predicates, evaluator, loader, and the per-rule fire/silent test
  table** live in the **engine repo** under `internal/rules/`.
- The engine validates rules against its own copy of these packs at
  `testdata/rules-fixture/` (the test fixture). Until the test harness is
  pointed directly at this repository, **a rule change here must be mirrored
  into the engine's `testdata/rules-fixture/` with its fire/silent test cases**,
  or the engine's `TestPolicyRules_AllRulesCovered` guard will not cover it.
- There is no `go test` to run *in this repo* — it has no Go. Validation runs
  in the engine repo (`go test ./...`).

## Required reading order before editing

1. Schema reference (engine repo): [`internal/rules/schema.yaml`](https://github.com/trustabl/trustabl/blob/main/internal/rules/schema.yaml) — authoritative field reference.
2. [`README.md`](README.md) — conventions in this repo.
3. The closest existing rule to what's being asked for — pattern example.

Do not skip step 1.

## Hard rules

- **Never invent YAML keys.** The schema is closed (`KnownFields(true)`). If a
  field you want does not exist in the engine's
  [`internal/rules/schema.go`](https://github.com/trustabl/trustabl/blob/main/internal/rules/schema.go),
  extending the schema is a four-file change **in the engine repo**
  (schema.go + predicates.go + evaluator.go + schema.yaml), gated by a
  `manifest.yaml` `schema_version` bump here. Make the engine changes in one
  commit.
- **Never change a rule's `id` after it has shipped.** IDs are external
  identifiers; downstream consumers cite them, and the engine folds the
  resolved pack into the scan `ScanID`.
- **Never duplicate a rule ID across files.** The loader rejects this at
  startup.
- **Never widen `applies_to` across SDKs casually.** A rule's `explanation` /
  `fix` text is usually SDK-specific. Adding `openai_tool` to a Claude-SDK rule
  (or vice versa) makes the user-facing text lie. If a cross-SDK pattern is
  genuinely needed, author a separate rule under that SDK's category
  (`<sdk>_sdk/<topic>.yaml`) with framing that matches the target SDK.
- **Never write rules at `info` severity.** Reserved.

## Required fields per rule

Every rule MUST set: `id`, `title`, `severity`, `confidence`, `applies_to`,
`match`, `explanation`, `fix`. The loader refuses to start the scanner if any
are missing — this surfaces as a `scan: ...` error in the CLI.

`language:` is OPTIONAL but state it explicitly — defaults to `python` when
omitted. For TypeScript / JavaScript / Go rules, set it explicitly:
`language: typescript`. Note: only Python tool discovery is plumbed into the
engine today, so non-python rules will load and validate but never fire until
the matching parser ships.

## Per-scope `applies_to` values

The `applies_to` list constrains which discovered entities a rule fires
against. Pick values from the table for the scope you're targeting.

**`scope: tool`** — receives a `ToolDef`; `applies_to` is matched against
`ToolDef.Kind`:

| `applies_to` value   | Matches                                       |
| -------------------- | --------------------------------------------- |
| `openai_tool`        | `@function_tool`-decorated Python function    |
| `claude_sdk_tool`    | `@tool` / `@claude_tool` / `claude_agent_sdk` |
| `mcp_tool`           | `@server.tool`, `@mcp.tool`, `.register_tool` |
| `shell_invocation`   | Bare function that calls `subprocess.*` etc. (no rules currently target this — OSH-* moved to a closed-source project) |
| `langchain_tool`     | `@tool` / `StructuredTool` / `tool(...)` (LangChain, LangGraph) |
| `crewai_tool`        | `@tool` / `BaseTool` subclass (CrewAI)        |
| `pydantic_ai_tool`   | `@agent.tool` / `@agent.tool_plain` / `Tool(...)` (Pydantic AI) |
| `adk_function_tool`  | `FunctionTool(fn)` wrapping a Python function (Google ADK) |
| `vercel_ai_tool`     | `tool({...})` / `dynamicTool({...})` from the `ai` package |
| `autogen_tool`       | `register_function` / `register_for_llm` / `register_for_execution` (AutoGen, AG2) |
| `unknown`            | Fallback kind; rarely useful                  |

**`scope: agent`** — receives an `AgentDef`; `applies_to` is matched against
`AgentDef.Class` + `AgentDef.SDK`:

| `applies_to` value        | Matches                                                       |
| ------------------------- | ------------------------------------------------------------- |
| `openai_agent`            | `Agent(...)` from `openai-agents` SDK                         |
| `openai_sandbox_agent`    | `SandboxAgent(...)` from `openai-agents` SDK                  |
| `claude_agent_definition` | `AgentDefinition(...)` from `claude-agent-sdk`                |
| `claude_query_main`       | `query(...)` main-thread agent from the Claude TS SDK         |
| `adk_llm_agent`           | `LlmAgent(...)` / `Agent(...)` alias from `google-adk`        |
| `adk_sequential_agent`    | `SequentialAgent(...)` from `google-adk`                      |
| `adk_parallel_agent`      | `ParallelAgent(...)` from `google-adk`                        |
| `adk_loop_agent`          | `LoopAgent(...)` from `google-adk`                            |
| `adk_langgraph_agent`     | `LanggraphAgent(...)` from `google-adk`                       |
| `langchain_agent`         | `create_*_agent(...)` from LangChain                          |
| `langchain_agent_executor`| `AgentExecutor(...)` from LangChain                           |
| `langchain_state_graph`   | `StateGraph(...)` from LangGraph                              |
| `crewai_agent`            | `Agent(...)` from `crewai`                                    |
| `pydantic_ai_agent`       | `Agent(...)` from `pydantic-ai`                               |
| `vercel_ai_agent`         | `generateText` / `streamText` / `Agent` from the `ai` package |
| `autogen_conversable_agent` | `ConversableAgent(...)` from AutoGen / AG2                  |
| `autogen_user_proxy_agent`  | `UserProxyAgent(...)` from AutoGen / AG2                    |
| `autogen_assistant_agent`   | `AssistantAgent(...)` from AutoGen / AG2                    |
| `autogen_group_chat_manager`| `GroupChatManager(...)` from AutoGen / AG2                  |
| `autogen_code_executor_agent` | An AutoGen agent configured with a code executor           |

**`scope: repo`** — receives `RepoProfile` + `RepoInventory`. `applies_to` at
this scope is matched against a fixed token list (the loader's
`validAppliesToForScope`); these tokens are *category-like* labels, not the SDK
enum values used by the `repo_has_sdk_in_code` predicate:

| `applies_to` value | Matches repos that use               |
| ------------------ | ------------------------------------ |
| `claude_sdk`       | Claude Agent SDK                     |
| `openai_agents`    | OpenAI Agents SDK                    |
| `openshell`        | NVIDIA OpenShell SDK (no rules currently target this — OSH-* moved to a closed-source project) |
| `mcp`              | Model Context Protocol               |
| `google_adk`       | Google ADK (Python)                  |
| `langchain`        | LangChain / LangGraph                |
| `crewai`           | CrewAI                               |
| `pydantic_ai`      | Pydantic AI                          |
| `vercel_ai`        | Vercel AI SDK                        |
| `autogen`          | AutoGen / AG2                        |

Repo-scope rules typically combine `applies_to` with a `repo_has_sdk_in_code`
predicate to narrow firing to repos that actually use the SDK in code (e.g.
OAI-201's `match: { all: [ repo_has_sdk_in_code: [openai_agents], ... ] }`).
The two tokens look similar but live in different namespaces — `applies_to`
accepts `openai_agents`, and `repo_has_sdk_in_code` also accepts `openai_agents`
(the SDK enum, `models.SDKOpenAIAgents`); for Claude, `applies_to` uses
`claude_sdk` (the category) while `repo_has_sdk_in_code` uses `claude_agent_sdk`
(the SDK enum). Mismatching the two will silently fail the loader's scope
check. The two namespaces agree for `langchain`, `crewai`, `pydantic_ai`,
`vercel_ai`, `autogen`, `google_adk`, and `mcp` — Claude is the only token that
differs between them.

Always set `applies_to` explicitly — the loader does not infer scope from the
category. Omitting it would make a rule fire against every entity of that scope
regardless of SDK, which is almost never correct.

**`scope: subagent`** — receives a `SubagentDef` (one `.claude/agents/*.md`
frontmatter declaration, matched at any path depth). `applies_to` is matched
against a fixed token:

| `applies_to` value | Matches                                                         |
| ------------------ | --------------------------------------------------------------- |
| `claude_subagent`  | A `.claude/agents/*.md` subagent declaration (any path depth)   |

Subagent rules use the `subagent_grants_tool` predicate (true when
`SubagentDef.Tools` contains a listed tool name). They carry **no `language:`
field** — subagents are markdown frontmatter, not code, and the engine's
`subagentRuleDetector.Applies` does not gate on language. The shipped rules are
CSDK-110, CSDK-111, and CSDK-112 in `claude_sdk/subagent_safety.yaml`.

**`scope: skill`** — receives a `SkillDef` (one Claude Code Agent Skill,
`SKILL.md` plus the files bundled beside it). `applies_to` is matched against a
fixed token:

| `applies_to` value | Matches                                              |
| ------------------ | ---------------------------------------------------- |
| `claude_skill`     | A Claude Code Agent Skill (`SKILL.md` + its directory) |

Skill rules use the `skill_*` predicate family — frontmatter checks
(`skill_allows_tool`, `skill_allows_unrestricted_shell`,
`skill_model_invocable`, `skill_has_description`), body checks
(`skill_body_has_dynamic_exec`, `skill_references_external_url`,
`skill_body_has_injection_marker`), and bundled-file checks
(`skill_bundled_script_network_egress`, `skill_bundled_script_reads_secrets`,
`skill_bundled_file_has_hardcoded_secret`). Like subagent rules they carry **no
`language:` field** — a skill is markdown and its bundled scripts, not a parsed
source language. The shipped rules are CSKILL-* in `claude_skill/`.

## "Add a rule for X"

Default sequence:

1. Read the structurally-closest existing rule (e.g. for a new network rule,
   read `claude_sdk/network.yaml`).
2. Decide whether existing predicates cover the case. Existing first; a new
   primitive is an engine-repo change and a real cost.
3. Pick the category subdirectory and topic file. If neither matches, ASK the
   user before creating new ones.
4. Write the rule. Match the explanation/fix tone of nearby rules — a
   paragraph, plain language, names the consequence and the fix concretely.
5. Mirror the rule into the engine's `testdata/rules-fixture/` and add at
   minimum one fire case AND one silent case to `policyRuleCases` in the
   engine's
   [`internal/rules/policies_test.go`](https://github.com/trustabl/trustabl/blob/main/internal/rules/policies_test.go).
   The `TestPolicyRules_AllRulesCovered` guard requires every shipped rule to
   appear in this table.
6. Run `go test ./...` in the engine repo.

## "Remove a rule"

1. Delete the rule entry from its YAML file. If the file is now empty, delete
   the file.
2. In the engine repo, remove the rule from `testdata/rules-fixture/` and all
   matching cases from `policyRuleCases` in `internal/rules/policies_test.go`.
3. Run `go test ./...` in the engine repo.

## "Change a rule's severity / confidence / explanation"

In-place edit here; mirror into the engine's `testdata/rules-fixture/`. No
test-case changes required.

## Output discipline for explanation/fix text

These strings are user-facing — they appear in the CLI's scan summary (and JSON
output) and guide whether a user acts on the finding. Vague text undermines the
product.

- **explanation**: name the consequence, not just the pattern. "Returns
  exceptions to the model as opaque strings, so it can't recover" beats "raises
  exceptions".
- **fix**: prescribe the concrete change. "Pass `timeout=` (5–30s)" beats "add
  error handling".
- Match the tone of the surrounding rules — paragraph, no headers, no bullets.

## What this repo is NOT

- Not a place for ad-hoc YAML files. Every `.yaml` file here (except the
  top-level `manifest.yaml`) is loaded as a policy by the engine. Don't drop
  notes, examples, or work-in-progress `.yaml` files inline — they will fail
  the loader. Markdown docs (`README.md`, `CLAUDE.md`, per-pack READMEs) are
  fine; the loader only reads `.yaml`.
- Not the home of the schema or predicates. Those live in the engine repo.
