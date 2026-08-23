# Local LLM Lab

A measured guide to the local AI models available on this Apple Silicon Mac.

- Live guide: [local-llm-lab.vercel.app](https://local-llm-lab.vercel.app)
- Complete historical results: [overall-leaderboard.md](./overall-leaderboard.md)
- Raw benchmark data: [output/benchmarks](./output/benchmarks)

![The current installed-model guide](./output/playwright/model-guide-20260730/hero-desktop.png)

## What this repository answers

The repository keeps the information needed to choose a local model in one place:

- which exact builds are installed now
- what each model is best used for
- whether it accepts text, images, or audio
- whether the local build supports tools, reasoning mode, or code completion
- context length, model-file size, quantization, and runtime
- measured local task quality, generation speed, and peak memory
- which tested models were removed or failed to load
- which tuned Ollama names reuse the same underlying weights

The public site reads a generated inventory snapshot rather than presenting every historical benchmark row as currently installed.

## Current machine

| Item | Current value |
|---|---|
| Hardware | Apple M5 Pro, 48 GB unified memory, 15 CPU cores, 16 GPU cores |
| Installed exact builds | 24 |
| Fully comparable installed builds | 14 |
| Tuned aliases | 7 |
| Local model data represented | 320.8 GB in decimal file sizes |
| Current free disk space | About 187 GiB |
| Available runtimes | Direct MLX, Ollama, MLX audio/vision, and Apple Foundation Models through `apfel` |

The inventory was refreshed on 23 August 2026 from the live Hugging Face cache, Ollama manifests, and `apfel --model-info`.

## Recommended models

| Job | Exact build | Why |
|---|---|---|
| Coding default | `lmstudio-community/Qwen3-Coder-30B-A3B-Instruct-MLX-4bit` | Local rank 1; 98.3 work-fit, 98.8 task quality, and about 98.8 generated tokens per second |
| Broad text and image work | `mlx-community/Qwen3.6-35B-A3B-4bit` | Local rank 2; almost tied on quality, with image input and very fast sparse generation |
| Small high-quality helper | `lmstudio-community/gemma-4-E4B-it-MLX-4bit` | Local rank 3 from a 6.9 GB model file |
| Strongest current dense Qwen | `mlx-community/Qwen3.8-27B-4bit` | Local rank 5; tied the leaders at 98.8 task quality while using 16.4 GB peak memory, but generated only 17.7 tokens per second |
| Very fast comparison | `lmstudio-community/NVIDIA-Nemotron-3-Nano-30B-A3B-MLX-4bit` | About 103 generated tokens per second, but less reliable than the leading Qwen builds |
| Open WebUI helper | `qwen3.5:9b` through Ollama | The strongest convenient Ollama helper in the comparable local suite |
| Speech transcription | `mlx-community/whisper-large-v3-turbo` | Local audio transcription and speech-to-English translation |

Different runtime builds of the same base model remain separate. Quantization and inference software materially change speed, memory use, and output reliability.

## Recently removed model files

The following Hugging Face caches were removed on 30 July 2026, recovering 47.5 GB:

| Removed exact build | Historical local rank | Reason |
|---|---:|---|
| `lmstudio-community/GLM-4.7-Flash-MLX-4bit` | 12 | Lower quality than the retained sparse Qwen and Nemotron builds |
| `mlx-community/Qwen3.5-9B-4bit` | 14 | The retained Ollama build performed much better, and Gemma 4 E4B is the stronger small MLX model |
| `mlx-community/gpt-oss-20b-MXFP4-Q4` | 15 | Low local task quality |
| `lmstudio-community/LFM2-24B-A2B-MLX-4bit` | 17 | Very fast but unreliable on important structured and factual tasks |

Their raw benchmark evidence remains checked in. The site lists them under “Previously tested, not installed.”

## Qwen3 Coder Next warning

The 4-bit Qwen3 Coder Next download is roughly 44.9 GB. Disk space is available, but its weights would consume almost all of this Mac’s 48 GB unified memory before context data, macOS, Codex, or other applications are counted. Removing cached model files creates disk space; it does not create more runtime memory.

Keep the proven Qwen3 Coder 30B A3B build until Coder Next has loaded successfully and completed the same benchmark.

## Refresh the current-model guide

The metadata file records model capabilities and exact source links. The generator checks the local caches and joins installed builds with the historical leaderboard.

```bash
python3 ./scripts/generate-current-model-guide.py
```

Inputs:

- [config/model-guide-metadata.json](./config/model-guide-metadata.json)
- [output/leaderboard/overall-leaderboard.json](./output/leaderboard/overall-leaderboard.json)
- the local Hugging Face cache
- the local Ollama manifest directory
- `apfel --model-info`

Generated outputs:

- [output/inventory/current-models.json](./output/inventory/current-models.json)
- [site/src/current-models.json](./site/src/current-models.json)

After installing or removing a model, rerun the generator and review the resulting inventory before publishing the site.

## Benchmark method

The comparable suite tests:

- shell scripting
- structured JSON changes
- classification
- concise summaries
- text transformation
- translation
- refusal when information is unknown
- exact harmless instruction following

The work-fit score is:

- 80% weighted task quality
- 15% response-time usefulness
- 5% successful invocations

MLX text speed comes from three trials using a 512-token prompt and a 128-token completion. Vision-model speed is measured from end-to-end capability requests, so the two speed types should not be compared directly.

Run or regenerate the benchmark data with:

```bash
python3 ./scripts/benchmark-recommended-models.py --models qwen3_coder_30b_a3b_mlx4
python3 ./scripts/generate-overall-leaderboard.py
./scripts/generate-benchmark-charts.py
```

## Quick start

### Ollama and Open WebUI

```bash
./scripts/start-ollama.sh
./scripts/start-openwebui.sh
./scripts/setup-agent-offload-models.sh
```

Run a model directly:

```bash
ollama run qwen3.5:9b
```

### Direct MLX

```bash
mlx_lm.generate \
  --model mlx-community/Qwen3.6-35B-A3B-4bit \
  --prompt "Summarise this repository"
```

### Apple system model

```bash
apfel --model-info
apfel "Summarise this text"
```

## Tuned Ollama names

These names reuse existing weights with deterministic settings and a narrower purpose:

| Alias | Base model | Intended use |
|---|---|---|
| `local-helper-fast` | `qwen3.5:9b` | Fast context compression and classification |
| `local-coder-helper` | `qwen2.5-coder:14b` | Diffs, APIs, and code-aware extraction |
| `local-thinker-clean` | `qwen2.5:14b` | Broader synthesis without visible reasoning by default |
| `local-helper-safe` | `phi4:latest` | Conservative summaries and checklists |
| `local-helper-heavy` | `mistral-small:22b` | Heavier general synthesis |
| `local-reasoner-clean` | `gpt-oss:20b` | Cleaner reasoning-style output |
| `llama3.2:3b-cpu` | `llama3.2:3b` | CPU fallback testing |

## Private Open WebUI access

Check the active local addresses with:

```bash
./scripts/status.sh
```

The normal entry points are:

- OrbStack: `http://open-webui-lab.orb.local`
- localhost: `http://localhost:3001`
- private remote access: enable with `./scripts/enable-tailscale-openwebui.sh`

The remote link is intended for devices signed into the same private Tailscale network. Disable it with:

```bash
./scripts/disable-tailscale-openwebui.sh
```

## Repository map

| Path | Purpose |
|---|---|
| `config/model-guide-metadata.json` | Curated capabilities, contexts, cautions, and source links |
| `config/recommended-mlx-models.json` | Revision-pinned benchmark targets, including historical builds |
| `scripts/generate-current-model-guide.py` | Detect installed builds and generate the public guide data |
| `scripts/benchmark-recommended-models.py` | Install and benchmark exact MLX revisions |
| `scripts/generate-overall-leaderboard.py` | Merge all benchmark evidence into the historical leaderboard |
| `output/inventory/` | Current installed-model snapshot |
| `output/benchmarks/` | Raw benchmark results and runtime logs |
| `output/leaderboard/` | Historical JSON and CSV leaderboard |
| `output/acceptance/` | Human-readable proof summaries |
| `output/playwright/` | Browser screenshots and proof artifacts |
| `modelfiles/` | Tuned Ollama aliases |
| `site/` | React/Vite public guide |

## Validate and deploy

```bash
cd site
pnpm install --frozen-lockfile
pnpm build
pnpm test:smoke
```

The Vercel project is linked from `site/.vercel/project.json`. Production deployment is performed only after the inventory, build, browser tests, screenshots, and repository checks pass.
