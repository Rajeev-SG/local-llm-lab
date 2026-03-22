# Coding Agent Context Offload Setup Recommendation

> Historical note: this document preserves an earlier local-first offload recommendation. The current shared system of record for live agent routing on this machine is `/Users/rajeev/Code/tools/local-llm-lab/config/agent-offload.toml`, which routes paid agent roles through configurable OpenRouter models and keeps these local helpers as optional preprocessing tools.

## Summary

Best setup on this machine is a two-tier system, not a full local-agent swap.

Keep the main coding agent on the strong frontier model for planning, edits, and judgment. Add a local Ollama helper tier that only handles bounded, context-heavy subroutines through strict JSON schemas. In practice, that means: search and retrieval first, then local compression, then the main agent decides. Do not make the 3-12B model a free-form agent with shell or tool access of its own.

This recommendation is based on the actual local environment:

- `ollama`, `codex`, and `claude` are installed locally
- the machine is an Apple Silicon MacBook Pro with an M5 Pro and 48 GB unified memory

## Recommended Model Roles

### Fast helper

Use `local-helper-fast` backed by `qwen3.5:9b` with `think=false` as the default helper for context compression, clustering, and extraction.

### Safer helper

Use `local-helper-safe` backed by `phi4` when summaries get lossy or when you want a slightly more conservative helper for checklist-style output.

### Occasional heavier local fallback

Use `local-helper-heavy` backed by `mistral-small:22b` for harder local summarization or code-aware distillation when a smaller helper is not enough.

### Code-aware helper

Use `local-coder-helper` backed by `qwen2.5-coder:14b` when API surfaces, diffs, and contract extraction need stronger code structure awareness.

### Clean reasoning fallback

Use `local-reasoner-clean` backed by `gpt-oss:20b` with `think=low` only as an optional heavier reasoning-style fallback in Open WebUI or API callers that can set `think` explicitly.

### Clean synthesis fallback

Use `local-thinker-clean` backed by `qwen2.5:14b` when you want broader local synthesis without visible reasoning traces.

## Why This Architecture Wins

The biggest token savings do not come from replacing the main agent with a weaker local model. They come from turning repetitive context digestion into a local, deterministic RPC layer so the expensive main model only sees compressed, high-signal artifacts.

That means:

1. Use retrieval and search to narrow the candidate context.
2. Offload only context digestion to a small local model.
3. Keep final reasoning, edits, and judgments in the main agent.

## Best Architecture

### 1. Retrieval layer

Use narrow, high-confidence tools first:

- `rg`
- `probe`
- `qmd`
- `context7`

This is the cheapest token win and should happen before any LLM offload.

### 2. Local offload layer

Expose a small local MCP server backed by Ollama. Give it only a handful of tools with fixed schemas:

- `summarize_repo_slice`
- `compress_logs`
- `cluster_search_hits`
- `extract_contracts`
- `distill_docs`
- `draft_handoff`

### 3. Main agent layer

Let Codex or Claude call those tools when context is large, but keep the main agent as the only planner, editor, and test runner.

## Why Not Just Use `codex --oss`

Pointing Codex entirely at `--oss` changes the whole brain. It does not provide selective offload.

That is useful for:

- fully local sessions
- privacy-sensitive work
- experiments with all-local agent runs

But it is not the best default path for token efficiency when the goal is to preserve strong planning quality while shedding context-heavy digestion.

## Concrete Setup

### Step 1: Create deterministic helper model aliases

Create fixed helper wrappers rather than sending raw prompts to generic base models. Use deterministic settings and a narrow system prompt.

Example helper Modelfile:

```text
FROM qwen3.5:9b
PARAMETER num_ctx 32768
PARAMETER temperature 0
PARAMETER top_p 0.2
SYSTEM You are a deterministic context compressor. Return only valid JSON matching the requested schema. Never invent facts. Never reveal chain-of-thought. If unsure, say unknown.
```

Create matching wrappers for the tested models that actually behave well on this machine.

Suggested helper aliases:

- `local-helper-fast`
- `local-helper-safe`
- `local-helper-heavy`
- `local-coder-helper`
- `local-reasoner-clean`
- `local-thinker-clean`

Important: thinking-capable Ollama models need client-side `think` control. Per the Ollama thinking docs, Qwen 3 accepts `think=true/false` and GPT-OSS accepts `think=low|medium|high`; GPT-OSS traces cannot be fully disabled. That means pure Modelfile aliases are not enough for the cleanest behavior on those bases. Use one of these two paths:

- Open WebUI workspace model presets with `think` set in Advanced Params
- an offload server or API caller that sends `think=false` for Qwen 3 and `think=low` for GPT-OSS

In this lab, the Open WebUI setup script overrides the exact role model ids, including `:latest`, so the tuned params apply to the same selector entries you already use in chat.

### Step 2: Build a tiny local MCP server

Use a simple Python server launched with `uv`. The server should:

- accept bounded input only
- send prompts to Ollama
- require a schema for every request
- validate outputs with Pydantic
- retry once on invalid JSON
- return `confidence` and `unknowns`
- cache by `sha256(model + prompt + input)`

Do not give this helper server shell, network, or repo mutation authority.

### Step 3: Register the MCP server in Codex

Add a local MCP server entry to the authoritative Codex config:

- `/Users/rajeev/.codex/config.toml`

Example shape:

```toml
[mcp_servers.ollama_offload]
command = "uv"
args = ["run", "/Users/rajeev/.codex/tools/ollama-offload/server.py"]
enabled = true
```

### Step 4: Reuse the same helper layer from Claude if desired

The same helper server can be shared across Codex and Claude so that offload behavior stays consistent across both coding harnesses.

## What To Offload

Good offload targets:

- large grep or probe result sets
- multi-file API surface summaries
- long logs and test failures
- external docs distilled into checklists
- PR or diff compression
- handoff note drafting

These are exactly the kinds of tasks that burn frontier-model context without needing frontier-level judgment.

## What Not To Offload

Bad offload targets:

- final root-cause decisions
- patch generation you actually need to trust
- broad architectural choices
- anything requiring tool use, repo mutation, or nuanced judgment

If the task is decision-heavy rather than digestion-heavy, keep it in the main agent.

## Guardrails

### Schema-bound outputs only

Every tool should return structured JSON, never free-form prose.

### Deterministic generation

Use:

- `temperature = 0`
- short output budgets
- fixed schemas
- one retry on parse failure

### Confidence and abstention

Every response should include:

- `confidence`
- `unknowns`
- an explicit abstain path when the input is insufficient

### Caching

Cache by content hash so repeat summarization and log compression do not hit the local model again.

### Hard thresholds in the caller

Add simple policies such as:

- if raw input exceeds 25 KB, offload first
- if more than 5 files are involved, offload first
- if logs exceed 500 lines, offload first

## Practical Tuning On This Machine

Start with:

- `local-helper-fast` on `qwen3.5:9b` with `think=false`
- `32k` context

Move to `local-helper-safe` on `phi4` if the fast helper becomes too lossy.

Use `local-coder-helper` on `qwen2.5-coder:14b` when code structure matters.

Keep `local-helper-heavy` on `mistral-small:22b` as the heavier local fallback. On the current Docker runtime it is the biggest model we have actually proven cleanly through both CLI and Open WebUI.

Keep `local-reasoner-clean` on `gpt-oss:20b` as an opt-in Open WebUI or API preset rather than a plain terminal alias. On this machine, `think=low` is much cleaner in Open WebUI than the raw default behavior, but it still remains a reasoning-style fallback rather than the default helper tier.

Warm the active helper and inspect `ollama ps`. If the model starts CPU offloading or latency rises too far, reduce context length before changing the architecture.

## What I Would Not Do

- I would not make a 3B model an autonomous sub-agent
- I would not let the helper read the whole repo by default
- I would not rely on prompt discipline alone without schema validation and caching

## Why This Is The Sweet Spot Here

On this 48 GB Apple Silicon machine, a 9B to 14B helper tier is the best default tradeoff for:

- reliability
- speed
- lower memory pressure
- strong enough summarization quality

It preserves the high-quality main-agent workflow while dramatically reducing how much raw context needs to be sent upstream. When more local reasoning is useful, the tested 20B to 22B presets are workable, but they should stay opt-in rather than becoming the default helper tier.

## Sources

- Ollama Codex integration: <https://docs.ollama.com/integrations/codex>
- Ollama Anthropic compatibility: <https://docs.ollama.com/api/anthropic-compatibility>
- Ollama OpenAI compatibility: <https://docs.ollama.com/api/openai-compatibility>
- Ollama structured outputs: <https://docs.ollama.com/capabilities/structured-outputs>
- Ollama context length guidance: <https://docs.ollama.com/context-length>

## Optional Next Step

If implementing this setup, the next practical move is to build the first version of the local MCP helper under `/Users/rajeev/.codex/` with:

- helper model aliases
- schema validation
- caching
- Codex config registration
- a small initial tool set

This lab now includes the alias Modelfiles and setup script under `/Users/rajeev/Code/tools/local-llm-lab/` so the model-role layer can be recreated before the MCP server itself exists.
