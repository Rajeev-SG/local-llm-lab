# Local LLM Lab

A proof-backed local AI workstation for Apple Silicon: Ollama, Open WebUI, tuned helper roles, and browser-validated evidence of what actually works.

Live site: [site-iota-brown-59.vercel.app](https://site-iota-brown-59.vercel.app)

GitHub repo: [Rajeev-SG/local-llm-lab](https://github.com/Rajeev-SG/local-llm-lab)

![Open WebUI proof](site/public/assets/openwebui-proof.png)

## Why this repo exists

Most “local AI setup” repos stop at install instructions. This one is built around a more useful question:

> Which local models are actually worth running on this machine, in this runtime, with this UI, and how do we prove it?

Local LLM Lab answers that with:

- a working Ollama + Open WebUI stack
- role-tuned helper aliases instead of one vague default model
- explicit notes about what passed, what failed, and why
- real browser proof using Playwright, not only shell smoke tests
- a practical agent-offload workflow for coding and research tasks

## What is proven right now

| Area | Current answer |
|------|----------------|
| Best clean general local model | `mistral-small:22b` |
| Best clean coding-focused local model | `qwen2.5-coder:14b` |
| Best fast helper | `qwen3.5:9b` with `think=false` |
| Best conservative helper | `phi4` |
| Largest model proven through Open WebUI | `mistral-small:22b` |
| Browser validation | Real Open WebUI prompt-response path verified with Playwright |

The strongest current proof artifacts are:

- [model-sweep-20260322.md](/Users/rajeev/Code/tools/local-llm-lab/output/acceptance/model-sweep-20260322.md)
- [agent-offload-role-proof-20260322.md](/Users/rajeev/Code/tools/local-llm-lab/output/acceptance/agent-offload-role-proof-20260322.md)
- [desktop-final.png](/Users/rajeev/Code/tools/local-llm-lab/output/playwright/agent-offload-role-proof-20260322/desktop-final.png)

## Practical hardware takeaway

This lab was tuned on a `48 GB` Apple Silicon machine, but the currently reliable Docker Ollama runtime only exposes about `15.7 GiB` to the model runner. That changes the real model envelope:

- `9B` to `14B` models are the sweet spot
- `mistral-small:22b` is the heaviest model proven cleanly working end-to-end
- `30B+` models are still documented as constrained or failing under the current runtime ceiling

That honesty matters. A useful local AI lab should explain the limits as clearly as the wins.

## Model roles

| Role | Alias | Base model | Best use |
|------|-------|------------|----------|
| Fast helper | `local-helper-fast` | `qwen3.5:9b` | Context compression, clustering, cheap first-pass digestion |
| Safe helper | `local-helper-safe` | `phi4` | Conservative summaries, checklists, lower-loss extraction |
| Code helper | `local-coder-helper` | `qwen2.5-coder:14b` | API surfaces, diffs, code-aware distillation |
| Heavy helper | `local-helper-heavy` | `mistral-small:22b` | Harder local synthesis and stronger general chat |
| Reasoning fallback | `local-reasoner-clean` | `gpt-oss:20b` | Optional heavier reasoning-style fallback |
| Synthesis fallback | `local-thinker-clean` | `qwen2.5:14b` | Broader local synthesis without visible reasoning by default |

## Quick start

### 1. Start the runtime

```bash
./scripts/start-ollama.sh
./scripts/start-openwebui.sh
```

### 2. Create role-tuned helper aliases

```bash
./scripts/setup-agent-offload-models.sh
```

### 3. Create tuned Open WebUI role presets

```bash
OPENWEBUI_PASSWORD='<your-openwebui-password>' ./scripts/setup-openwebui-role-models.sh
```

### 4. Check status

```bash
./scripts/status.sh
```

## Day-to-day commands

### Core services

```bash
./scripts/start-ollama.sh
./scripts/stop-ollama.sh
./scripts/start-openwebui.sh
./scripts/stop-openwebui.sh
```

### Model setup and testing

```bash
./scripts/setup-agent-offload-models.sh
./scripts/test-models.sh
./scripts/benchmark-model.sh mistral-small:22b
```

### Agent offload workflow

```bash
agent-offload-sync
./scripts/test-agent-offload.sh
agent-offload audit-codex
```

### Raw Ollama

```bash
ollama list
ollama run mistral-small:22b
ollama show qwen2.5-coder:14b
```

## How the architecture works

This repo recommends a two-tier system rather than a full local-agent swap:

1. Retrieve narrowly with tools like `rg`, `probe`, `qmd`, and `context7`.
2. Offload repetitive context digestion to a tuned local helper role.
3. Keep final judgment, edits, and planning in the stronger main coding agent.
4. Validate outcomes with real acceptance proof.

That architecture is documented in [agent-offload-setup-recommendation.md](/Users/rajeev/Code/tools/local-llm-lab/agent-offload-setup-recommendation.md).

## Repo layout

| Path | Purpose |
|------|---------|
| `scripts/` | Service control, model setup, tuning, and test scripts |
| `modelfiles/` | Deterministic helper model wrappers |
| `config/agent-offload.toml` | Shared broker configuration |
| `broker/agent_offload.py` | Role-aware offload broker |
| `output/acceptance/` | Human-readable proof notes |
| `output/playwright/` | Browser-level acceptance artifacts |
| `site/` | Public landing page for the lab |

## Current recommendation

Use this lab for:

- local AI experimentation that is grounded in real runtime evidence
- role-based helper design for coding agents
- Apple Silicon model selection without guesswork
- Open WebUI setups that need actual browser proof

Do not use this repo as if it were a claim that all large models fit comfortably on this hardware. The value here is that the repo distinguishes clean wins from constrained experiments.

## Security and publishing note

This repo is meant to be publishable. Temporary auth state, local browser cookies, transient WebUI database files, and temp caches are intentionally excluded from version control.
