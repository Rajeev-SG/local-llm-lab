# Local LLM Lab

A proof-backed local AI workstation for Apple Silicon: MLX, Ollama, Open WebUI, tuned helper roles, and measured evidence of what actually works.

Live site: [local-llm-lab.vercel.app](https://local-llm-lab.vercel.app)

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
| Best coding and terminal model | `Qwen3 Coder 30B A3B`, MLX 4-bit |
| Best broad local model | `Qwen3.6 35B A3B`, MLX 4-bit |
| Best smaller broad helper | `Gemma 4 E4B`, MLX 4-bit |
| Fastest measured model | `LFM2 24B A2B`, MLX 4-bit, but its task quality is too low for the default role |
| Best conservative helper | `phi4` |
| Exact model builds recorded | 26 |
| Fully comparable benchmark rows | 17 |
| Browser validation | Real Open WebUI prompt-response path verified with Playwright |

The strongest current proof artifacts are:

- [benchmark-results.md](./benchmark-results.md)
- [overall-leaderboard.md](./overall-leaderboard.md)
- [huggingface-candidate-search.md](./huggingface-candidate-search.md)
- [model-sweep-20260322.md](./output/acceptance/model-sweep-20260322.md)
- [agent-offload-role-proof-20260322.md](./output/acceptance/agent-offload-role-proof-20260322.md)
- [desktop-final.png](./output/playwright/agent-offload-role-proof-20260322/desktop-final.png)

Latest benchmark takeaway:

- `Qwen3 Coder 30B A3B` ranks first for the coding-heavy workload at 98.3 work-fit, 98.8 task quality, 98.8 generated tokens per second, and 17.8 GB peak memory.
- `Qwen3.6 35B A3B` is nearly tied at 98.2 work-fit and remains the better broad default when image input matters.
- `Gemma 4 E4B` ranks third despite a 6.86 GB download, making it the best smaller broad helper found in the Hugging Face search.
- `LFM2 24B A2B` is fastest at 139.2 generated tokens per second, but it ranks 17th because it failed important shell, classification, structured-data, and factual-reliability checks.

## Benchmark Graphs

The current chart set is generated from the scored benchmark JSON plus the Gemma 4 blocked-run artifact:

- [chart index](./output/charts/benchmark-20260409/README.md)

### Overview dashboard

![Benchmark dashboard](./output/charts/benchmark-20260409/overview-dashboard.svg)

### Master comparison charts

![Capability heatmap](./output/charts/benchmark-20260409/master-capability-heatmap.svg)

![Average score ranking](./output/charts/benchmark-20260409/master-average-score-ranking.svg)

![Quality vs speed](./output/charts/benchmark-20260409/master-quality-vs-speed.svg)

![Latency by task](./output/charts/benchmark-20260409/master-latency-by-task.svg)

![Guardrail diagnostics](./output/charts/benchmark-20260409/master-guardrails.svg)

![Gemma runtime status](./output/charts/benchmark-20260409/master-gemma-runtime-status.svg)

## Practical hardware takeaway

This lab was tuned on a `48 GB` Apple Silicon machine. The Docker Ollama runtime exposes about `15.7 GiB` to its model runner, while direct MLX runs can use the host's unified memory. That creates two practical limits:

- `9B` to `14B` models remain the safest range inside the current Docker Ollama setup.
- Direct 4-bit MLX builds around `30B` total parameters run cleanly with measured peaks around `18` to `20 GB`.
- A model near `45 GB` before context memory is still unsuitable because the operating system and working applications need the same unified memory.

That honesty matters. A useful local AI lab should explain the limits as clearly as the wins.

## Model roles

### Direct MLX recommendations

| Role | Exact build | Best use |
|------|-------------|----------|
| Coding default | `lmstudio-community/Qwen3-Coder-30B-A3B-Instruct-MLX-4bit` | Repository work, shell tasks, structured extraction, and classification |
| Broad default | `mlx-community/Qwen3.6-35B-A3B-4bit` | General technical work and image-aware tasks |
| Smaller broad helper | `lmstudio-community/gemma-4-E4B-it-MLX-4bit` | Fast summaries, extraction, and routine technical work |
| Careful dense comparison | `mlx-community/Qwen3.6-27B-4bit` | Difficult review when slower output is acceptable |

### Ollama roles

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

### 5. Enable private remote access on your own devices

```bash
./scripts/enable-tailscale-openwebui.sh
```

This does not publish Open WebUI to the open internet. It exposes the UI over Tailscale Serve so only devices signed into the same tailnet can reach it. Use this when you want your phone, tablet, or another laptop to reach the lab safely.

## Day-to-day commands

### Core services

```bash
./scripts/start-ollama.sh
./scripts/stop-ollama.sh
./scripts/start-openwebui.sh
./scripts/stop-openwebui.sh
./scripts/enable-tailscale-openwebui.sh
./scripts/disable-tailscale-openwebui.sh
```

### Model setup and testing

```bash
./scripts/setup-agent-offload-models.sh
./scripts/test-models.sh
./scripts/benchmark-model.sh mistral-small:22b
python3 ./scripts/benchmark-recommended-models.py --models qwen3_coder_30b_a3b_mlx4
python3 ./scripts/generate-overall-leaderboard.py
./scripts/generate-benchmark-charts.py
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

That architecture is documented in [agent-offload-setup-recommendation.md](./agent-offload-setup-recommendation.md).

## Repo layout

| Path | Purpose |
|------|---------|
| `scripts/` | Service control, model setup, tuning, and test scripts |
| `modelfiles/` | Deterministic helper model wrappers |
| `config/agent-offload.toml` | Shared broker configuration |
| `broker/agent_offload.py` | Role-aware offload broker |
| `output/charts/` | Generated benchmark comparison charts |
| `output/benchmarks/` | Raw, revision-pinned benchmark results and runtime logs |
| `output/leaderboard/` | Generated JSON and CSV leaderboard data |
| `output/acceptance/` | Human-readable proof notes |
| `output/playwright/` | Browser-level acceptance artifacts |
| `site/` | Public landing page for the lab |

## Current recommendation

Use this lab for:

- local AI experimentation that is grounded in real runtime evidence
- role-based helper design for coding agents
- Apple Silicon model selection without guesswork
- Open WebUI setups that need actual browser proof

## Safe remote access

If you want access away from the Mac without broadly exposing your laptop to the public internet, the recommended path is Tailscale Serve.

- enable it with `./scripts/enable-tailscale-openwebui.sh`
- inspect the current private URL with `./scripts/status.sh`
- disable it with `./scripts/disable-tailscale-openwebui.sh`

This gives you HTTPS access on devices signed into the same Tailscale tailnet. That is a much safer default than putting Open WebUI directly on the public internet and relying only on the app login screen.

Do not use this repo as if it were a claim that all large models fit comfortably on this hardware. The value here is that the repo distinguishes clean wins from constrained experiments.

## Security and publishing note

This repo is meant to be publishable. Temporary auth state, local browser cookies, transient WebUI database files, and temp caches are intentionally excluded from version control.
