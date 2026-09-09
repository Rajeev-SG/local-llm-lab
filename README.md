# Local LLM Lab

A measured guide to the local AI models available on this Apple Silicon Mac.

- Live guide: [local-llm-lab.vercel.app](https://local-llm-lab.vercel.app)
- Full historical results: [overall-leaderboard.md](./overall-leaderboard.md)
- Raw benchmark data: [output/benchmarks](./output/benchmarks)
- Magnitude (llama.cpp) frontier and memory audit, 2026-09-09: [magnitude-llamacpp-evaluation-2026-09-09.md](./magnitude-llamacpp-evaluation-2026-09-09.md)

![The current installed-model guide](./output/playwright/model-guide-20260730/hero-desktop.png)

## What this answers

Everything needed to choose a local model:

- which exact builds are installed now and which were removed
- what each model is best at, plus context length, file size, quantization, and runtime
- whether a build accepts text, images, or audio; supports tools, reasoning, or code completion
- measured task quality, speed, latency, and peak memory
- which tuned Ollama names reuse the same underlying weights

## Current machine

| Item | Value |
|---|---|
| Hardware | Apple M5 Pro, 48 GB unified memory, 15 CPU / 16 GPU cores |
| Installed builds / tuned aliases | 24 installed, 14 fully comparable, 7 aliases |
| Model data on disk | 320.8 GB (decimal sizes) |
| Free disk space | about 187 GiB |
| Runtimes | Direct MLX, Ollama, MLX audio/vision, Apple Foundation Models (`apfel`) |

Inventory refreshed 23 Aug 2026 from the Hugging Face cache, Ollama manifests, and `apfel --model-info`.

## Model leaderboard

All 18 ranked builds from [overall-leaderboard.json](./output/leaderboard/overall-leaderboard.json),
joined with [inventory](./output/inventory/current-models.json) for context, modality, and size. An em dash
means the metric is not available for that build (prompt speed and peak memory are only recorded for MLX
text runs, not vision or Ollama runs; context and modality are unknown for removed files).

| Rank | Build | Runtime | Context | Size (GB) | Modality | Capabilities | Work-fit | Quality | Median lat. (ms) | Prompt tok/s | Gen tok/s | Peak mem (GB) | Success | Status | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Qwen3 Coder 30B A3B (MLX 4-bit) | mlx | 262,144 | 17.2 | Text | Code, Tools, Long context | 98.3 | 98.8 | 752.2 | 1331.7 | 97.0 | 17.8 | 8/8 | passed |  |
| 2 | Qwen3.6 35B A3B (MLX 4-bit) | mlx | 262,144 | 20.4 | Text,Image | Vision, Tools, Thinking, Long context | 98.3 | 98.8 | 782.9 | 980.3 | 99.3 | 20.2 | 8/8 | passed |  |
| 3 | Gemma 4 E4B (MLX 4-bit) | mlx_vlm | 131,072 | 6.9 | Text,Image | Vision, Code, Long context | 97.2 | 97.6 | 893 | — | 47.0 | — | 8/8 | passed |  |
| 4 | Gemma 4 26B A4B QAT (MLX 4-bit) | mlx_vlm | 262,144 | 15.6 | Text,Image | Vision, Code, Long context | 96.7 | 96.8 | 815.6 | — | 51.6 | — | 8/8 | passed |  |
| 5 | Qwen3.8 27B (MLX 4-bit) | mlx | 262,144 | 16.1 | Text,Image | Vision, Code, Tools, Thinking, Long context | 96.3 | 98.8 | 3279.4 | 364.1 | 17.7 | 16.4 | 8/8 | passed |  |
| 6 | Qwen3.6 27B (MLX 4-bit) | mlx | 262,144 | 16.1 | Text,Image | Vision, Tools, Thinking, Long context | 95.6 | 98.8 | 4515.3 | 269.5 | 13.5 | 16.4 | 8/8 | passed |  |
| 7 | qwen3.5:9b | ollama | 262,144 | 6.6 | Text,Image | Vision, Tools, Thinking, Long context | 91.1 | 96.8 | 10973.4 | — | 8.0 | — | 8/8 | benchmarked |  |
| 8 | qwen2.5-coder:14b | ollama | 32,768 | 9 | Text | Code, Tools, Fill-in-the-middle | 89.9 | 96 | 12940.6 | — | 8.7 | — | 8/8 | benchmarked |  |
| 9 | Devstral Small 2 24B (MLX 4-bit) | mlx | 393,216 | 15.1 | Text,Image | Code, Vision, Tools, Long context | 89.9 | 92 | 4843.1 | 304.0 | 14.1 | 14.7 | 8/8 | passed |  |
| 10 | Nemotron 3 Nano 30B A3B (MLX 4-bit) | mlx | 262,144 | 17.8 | Text | Code, Tools, Thinking, Long context | 89 | 87.2 | 850.7 | 1138.2 | 103.2 | 19.6 | 8/8 | passed |  |
| 11 | qwen2.5:14b | ollama | 32,768 | 9 | Text | Tools | 88.4 | 93.8 | 11853.3 | — | 9.8 | — | 8/8 | benchmarked |  |
| 12 | phi4 | ollama | 16,384 | 9.1 | Text | Completion | 86.2 | 90.8 | 11309.7 | — | 10.3 | — | 8/8 | benchmarked |  |
| 13 | GLM-4.7-Flash (MLX 4-bit) | mlx | — | 16.9 | — | — | 86 | 84 | 1297.8 | 1148.2 | 69.7 | 17.5 | 8/8 | passed | removed |
| 14 | mistral-small:22b | ollama | 131,072 | 12.6 | Text | Tools, Long context | 82.6 | 90 | 25128 | — | 5.8 | — | 8/8 | benchmarked |  |
| 15 | Qwen3.5 9B (MLX 4-bit) | mlx | — | 6 | — | — | 78.6 | 74.8 | 1298.4 | 1044.9 | 53.4 | 5.9 | 8/8 | passed | removed |
| 16 | gpt-oss-20b (MLX MXFP4/Q4) | mlx | — | 11.2 | — | — | 70.6 | 65.8 | 2425.1 | 1804.7 | 98.4 | 11.7 | 8/8 | passed | removed |
| 17 | apfel | apfel | 4,096 | — | Text | System on-device | 63.7 | 55.8 | 961.4 | — | — | — | 8/8 | benchmarked |  |
| 18 | LFM2 24B A2B (MLX 4-bit) | mlx | — | 13.4 | — | — | 63.3 | 54.8 | 532.9 | 1879.1 | 139.2 | 13.8 | 8/8 | passed | removed |

**Notes**

- **Speed basis differs by runtime.** Gen tok/s is measured three ways: *isolated MLX trial* (512-token
  prompt, 128-token completion), *median end-to-end capability request* (vision), and *median Ollama
  generation counter*. Compare only within the same basis — see [overall-leaderboard.md](./overall-leaderboard.md).
- **Removed** rows (ranks 13, 15, 16, 18 and others marked "removed") no longer have installed files; their
  raw evidence stays in [output/benchmarks](./output/benchmarks). The site lists them as "Previously tested,
  not installed."
- **Success** is successful tasks / total tasks in the linked benchmark artifact; it is 8/8 for every
  ranked row that ran.
- Some metrics in the artifacts have **no value for certain runs** (for example `prompt_tokens_per_second`
  is missing for vision/Ollama rows, and `peak_memory_gb` is missing for `mlx_vlm`/Ollama). This README
  shows an em dash rather than a fabricated number. There is no per-variant "download size by variant",
  no "success count keyed by individual issue", and no per-run "prompt speed" in these JSON sources.

### Metrics that are not in the JSON

If you need a value this leaderboard does not show, it is not present in
[overall-leaderboard.json](./output/leaderboard/overall-leaderboard.json) or
[inventory](./output/inventory/current-models.json). It would have to be regenerated by the benchmark
runbook (`./scripts/benchmark-recommended-models.py`) with added instrumentation, then merged by
`./scripts/generate-overall-leaderboard.py`. This README does not invent missing values.

## Previously installed, now removed

Removed 30 Jul 2026, recovering 47.5 GB. Raw evidence stays in `output/benchmarks`.

| Removed build | Reason |
|---|---|
| `GLM-4.7-Flash-MLX-4bit` | Lower quality than retained sparse Qwen / Nemotron builds |
| `Qwen3.5-9B-MLX-4bit` | Retained Ollama build scored better; Gemma 4 E4B is the stronger small MLX model |
| `gpt-oss-20b-MXFP4-Q4` | Low local task quality |
| `LFM2-24B-A2B-MLX-4bit` | Very fast but unreliable on structured / factual tasks |

## Qwen3 Coder Next caution

The 4-bit Coder Next download is ~44.9 GB. Disk space is available, but its weights would consume almost
all of this Mac's 48 GB unified memory before context, macOS, Codex, or other apps. Removing cached model
files frees disk, not memory. Keep the proven Coder 30B A3B build until Coder Next loads and passes the
same benchmark.

## Recommended picks

| Job | Build | Why |
|---|---|---|
| Coding default | Qwen3 Coder 30B A3B (MLX 4-bit) | Rank 1: 98.3 work-fit, 98.8 quality, ~97 tok/s |
| Broad text + image | Qwen3.6 35B A3B (MLX 4-bit) | Rank 2, near tie on quality, image input, very fast sparse |
| Small high-quality helper | Gemma 4 E4B (MLX 4-bit) | Rank 3 from a 7 GB file |
| Dense text focus | Qwen3.8 27B (MLX 4-bit) | Tied at 98.8 quality but slow (~18 tok/s) |
| Very fast comparison | Nemotron 3 Nano 30B A3B (MLX 4-bit) | ~103 tok/s, less reliable than leading Qwen |
| Open WebUI helper | `qwen3.5:9b` via Ollama | Strongest convenient Ollama helper in the suite |
| Speech-to-text | `mlx-community/whisper-large-v3-turbo` | Local audio to text + speech-to-English |

Different runtimes of the same base model are separate builds: quantization and inference software
materially change speed, memory, and reliability.

## Install or remove a model

```bash
# add a model via Ollama
ollama pull qwen3.5:9b
# then refresh the guide and review the result
python3 ./scripts/generate-current-model-guide.py
```

The guide reads [config/model-guide-metadata.json](./config/model-guide-metadata.json),
[overall-leaderboard.json](./output/leaderboard/overall-leaderboard.json), the local HuggingFace cache,
Ollama manifests, and `apfel --model-info`. After a change, review the re-generated
`output/inventory/current-models.json` and `site/src/current-models.json` before publishing.

## Benchmark method

The comparable suite tests shell scripting, structured JSON changes, classification, concise summaries,
text transformation, translation, unknown-information refusal, and exact harmless instruction following.

Fit = 80% × task quality + 15% × response utility + 5% × invocation reliability.

Speed for MLX text comes from three trials (512-token prompt, 128-token completion); vision speeds come
from end-to-end capability requests, and Ollama from its generation counter — compare only within the
same basis.

Regenerate the leaderboard and charts:

```bash
python3 ./scripts/benchmark-recommended-models.py --models qwen3_coder_30b_a3b_mlx4
python3 ./scripts/generate-overall-leaderboard.py
./scripts/generate-benchmark-charts.py
```

## Quick start

### Ollama / Open WebUI

```bash
./scripts/start-ollama.sh
./scripts/start-openwebui.sh
./scripts/setup-openwebui-role-models.sh
ollama run qwen3.5:9b
```

The `setup-openwebui-role-models.sh` script synchronizes the installed Ollama models with Open WebUI, applying clean labels and role presets. Models are displayed as:
`Local LLM Lab — <Label> · <Param Size> · <Disk Size> GB`

The script automatically detects the Ollama runtime memory (e.g. 15.7 GB when containerized in Docker/OrbStack) and labels models exceeding 70% of that memory as `Needs more RAM`. A default context cap of 8192 is applied to improve stability, unless overridden via `OPENWEBUI_LOCAL_NUM_CTX`. Registry syntax and `:latest` tags are omitted from display names for clarity.

For a reproducible Open WebUI deployment, use the pinned Compose setup. It
recreates only the named container and preserves `open-webui-data`:

```bash
cp config/openwebui.env.example .env.local
./scripts/start-ollama.sh
./scripts/setup-openwebui.sh
./scripts/restore-ollama-models.sh
./scripts/doctor.sh
```

Set `OPENROUTER_API_KEY` in the invoking environment, or set
`OPENAI_API_KEYS` in the ignored `.env.local`, to enable the OpenAI-compatible
OpenRouter connection. Never commit either value. Use
`./scripts/rollback-openwebui.sh <known-good-version-or-digest>` to change the
image without deleting the volume. The constrained bridge and isolated browser
proof flow are documented in [docs/openwebui-secure-setup.md](./docs/openwebui-secure-setup.md).

### Direct MLX

```bash
mlx_lm.generate --model mlx-community/Qwen3.6-35B-A3B-4bit --prompt "Summarise this repository"
```

### Apple foundational model

```bash
apfel --model-info
apfel "Summarise this text"
```

## Tuned Ollama names

Aliases reuse existing weights with narrower targets:

| Alias | Base model | Use |
|---|---|---|
| `local-helper-fast` | `qwen3.5:9b` | Fast compression / classification |
| `local-coder-helper` | `qwen2.5-coder:14b` | Diffs, APIs, code-aware extraction |
| `local-thinker-clean` | `qwen2.5:14b` | Broader synthesis, no visible reasoning |
| `local-helper-safe` | `phi4:latest` | Conservative summaries, checklists |
| `local-helper-heavy` | `mistral-small:22b` | Heavier general synthesis |
| `local-reasoner-clean` | `gpt-oss:20b` | Cleaner reasoning-style output |
| `llama3.2:3b-cpu` | `llama3.2:3b` | CPU fallback testing |

## Private Open WebUI access

```bash
./scripts/status.sh
```

- OrbStack: `http://open-webui-lab.orb.local`
- localhost: `http://localhost:3001`
- remote: enable with `./scripts/enable-tailscale-openwebui.sh` (same Tailscale device only), disable with
  `./scripts/disable-tailscale-openwebui.sh`

## Repository map

| Path | Purpose |
|---|---|
| `config/model-guide-metadata.json` | Curated capabilities, contexts, cautions, sources |
| `config/recommended-mlx-models.json` | Revision-pinned benchmark targets |
| `scripts/generate-current-model-guide.py` | Detect installed builds; generate guide data |
| `scripts/benchmark-recommended-models.py` | Install + benchmark exact MLX revisions |
| `scripts/generate-overall-leaderboard.py` | Merge evidence into historical leaderboard |
| `output/inventory/` | Current installed-model snapshot |
| `output/benchmarks/` | Raw benchmark results and runtime logs |
| `output/leaderboard/` | Historical JSON/CSV leaderboard |
| `output/acceptance/` | Human-readable proof summaries |
| `output/playwright/` | Browser screenshots / proof |
| `modelfiles/` | Tuned Ollama aliases |
| `site/` | React/Vite public guide |

## Validate and deploy

```bash
cd site
pnpm install --frozen-lockfile
pnpm build
pnpm test:smoke
```

Production is deployed only after the inventory, build, browser tests, screenshots, and repository checks
pass.
