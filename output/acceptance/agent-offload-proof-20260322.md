# Agent Offload Proof - 2026-03-22

## Goal

Set up a shared, configurable multi-sub-agent offload broker that:

- keeps expensive main-agent transcripts smaller
- routes bounded compression tasks to cheaper or better-fit OpenRouter models
- integrates across Codex, Claude, Claude OpenRouter, Windsurf, and Droid

## Source Of Truth

- broker config: `/Users/rajeev/Code/tools/local-llm-lab/config/agent-offload.toml`
- broker server: `/Users/rajeev/Code/tools/local-llm-lab/broker/agent_offload.py`
- sync command: `agent-offload-sync`
- CLI entry: `agent-offload`
- MCP server name: `agent_offload`

## Configured Role Map

- default worker: `x-ai/grok-4.1-fast`
- long-context escalator: `google/gemini-3-flash-preview`
- harder mid-cost worker: `minimax/minimax-m2.5`
- coding specialist: `z-ai/glm-5`

## Integration Checks

### Codex

- `codex mcp list` shows `agent_offload` enabled
- codex config updated at `/Users/rajeev/.codex/config.toml`

### Claude OpenRouter

- `claude-openrouter-doctor` confirms:
  - default: `x-ai/grok-4.1-fast`
  - opus alias: `google/gemini-3-flash-preview`
  - sonnet alias: `minimax/minimax-m2.5`
  - custom option: `z-ai/glm-5`
- mirror MCP inventory includes `agent_offload`

### Claude

- base Claude MCP config updated in:
  - `/Users/rajeev/.claude.json`
  - `/Users/rajeev/.claude/settings.json`

### Windsurf

- `/Users/rajeev/.codeium/windsurf/mcp_config.json` includes `agent_offload`
- global review workflow now tells reviews to compress large logs and diffs through the broker

### Droid

- `/Users/rajeev/.factory/config.json` now includes:
  - `OR: Offload Worker (Grok 4.1 Fast)`
  - `OR: Long Context (Gemini 3 Flash Preview)`
  - `OR: Mid-Cost Harder Worker (MiniMax M2.5)`
  - `OR: Coding Specialist (GLM-5)`
- `/Users/rajeev/.factory/AGENTS.md` points Droid to the shared broker for bulky context

## Live Role Tests

### Default worker

- task: `summarize_tool_output`
- routed to: `x-ai/grok-4.1-fast`
- actual usage: `340` prompt tokens, `108` completion tokens
- estimated cost: `$0.000122`
- result quality: clean structured summary with risks and next step

### Long-context escalator

- task: `cross_doc_synthesis`
- routed to: `google/gemini-3-flash-preview`
- input size: `81,601` chars
- actual usage: `15,738` prompt tokens, `213` completion tokens
- estimated cost: `$0.008508`
- result quality: correctly identified repetitive long-context input and summarized the redundancy risk

### Harder mid-cost worker

- task: `hard_synthesis`
- routed to: `minimax/minimax-m2.5`
- actual usage: `180` prompt tokens, `383` completion tokens
- estimated cost: `$0.000484`
- result quality: stronger tradeoff framing and clearer risk list than the cheapest worker

### Coding specialist

- task: `diff_summary`
- routed to: `z-ai/glm-5`
- actual usage: `170` prompt tokens, `287` completion tokens
- estimated cost: `$0.000871`
- result quality: code-focused summary with implementation risks and review next step

## Codex Session Audit

Command used:

```bash
agent-offload audit-codex
```

Observed over the latest five Codex sessions:

- tool output chars: `3,289,523`
- reasoning chars: `1,688,820`
- user chars: `19,804`
- instruction chars: `76,125`
- estimated main-agent tokens saved if tool output is cut by `85%`: `699,023`

Interpretation:

- the dominant token sink is tool output, not the user's prompts
- the broker directly targets the largest source of transcript bloat

## Example Savings Scenario

Command used:

```bash
agent-offload compare-scenario --raw-chars 388722 --compressed-chars 30000 --main-model-prompt-per-million 1.25
```

Result:

- raw estimate: `97,180` tokens
- compressed estimate: `7,500` tokens
- delta: `89,680` tokens
- illustrative prompt-cost saved at the example main-model price: `$0.1121`

Notes:

- this dollar figure is illustrative because it depends on the main agent's actual prompt pricing
- the token delta is the stronger proof

## Why This Is Helpful

- It keeps bulky logs, diffs, and tool chatter out of the main agent thread.
- It uses a cheaper worker by default and only escalates when context size or task type justifies it.
- It is centrally configurable and resynced into harness configs with one command.
- It improves maintainability by removing model-role drift across wrappers and tools.

## Known Limits

- Codex itself still uses its configured primary model for the main conversation; the savings come from broker-assisted compression, not from replacing Codex's core model.
- Droid integration is strongest through shared guidance plus the added OpenRouter model entries; it is not using the broker through MCP unless Droid exposes MCP in your current build.
- The scenario comparison uses a user-supplied example main-model prompt price, so treat the dollar output as directional rather than exact.
