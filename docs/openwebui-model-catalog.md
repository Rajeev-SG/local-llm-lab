# Open WebUI Model Catalog

This document describes how local Ollama models are represented in Open WebUI within the Local LLM Lab.

## Model Synchronization

The script `scripts/setup-openwebui-role-models.sh` is responsible for upserting custom model records into Open WebUI. It reads the source of truth from `config/model-guide-metadata.json` and matches it against live models reported by the Ollama API.

## Naming Convention

Display names are normalized for clarity:
- **Prefix**: `Local LLM Lab — ` (em dash)
- **Model Label**: Uses the curated `.label` from metadata.
- **Separator**: ` · ` (middle dot)
- **Parameters**: E.g., `9.7B`.
- **Size**: E.g., `6.6 GB`.

Example: `Local LLM Lab — Qwen3.5 9B · 9.7B · 6.6 GB`

## Memory Constraints and Stability

The synchronization script detects the Ollama runtime memory (e.g., 15.7 GB in Docker/OrbStack or 48 GB natively) and compares it against each model's `size_gb`.

- Models exceeding **70%** of available runtime memory are marked **Needs more RAM** in the picker, described as memory constrained, and tagged with `constrained`.
- A conservative context window cap of **8192** tokens is applied by default (or overridden by `OPENWEBUI_LOCAL_NUM_CTX`) to ensure stability across all models, never exceeding the model's own metadata limit.
- Models within safe memory bounds are tagged as `ready`.

## Role Presets

Aliases defined in `config/model-guide-metadata.json` are also created as custom models in Open WebUI. These aliases often include specific system prompts and parameter overrides (like disabling "thinking" modes for cleaner output).

| Alias | Purpose |
|---|---|
| `local-helper-fast` | Fast compression and classification |
| `local-helper-safe` | Conservative summaries and checklists |
| `local-helper-heavy` | Heavy synthesis and distillation |
| `local-coder-helper` | Code-aware extraction and diffs |
| `local-thinker-clean` | Clean synthesis without visible reasoning |
| `local-reasoner-clean` | Tuned reasoning output |

## Maintenance

After installing or removing a model via `ollama`, run the sync script to update the catalog:

```bash
./scripts/setup-openwebui-role-models.sh
```
