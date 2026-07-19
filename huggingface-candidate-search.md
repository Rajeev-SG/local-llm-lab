# Hugging Face candidate search

Search date: 2026-07-19

Machine: Apple M5 Pro with 48 GB unified memory, 15 CPU cores, and 16 GPU cores.

## How candidates were selected

The search used Hugging Face's current MLX listings sorted by downloads and by trending score. A model was selected when it met all of these conditions:

- instruction-tuned or coding-focused
- an exact MLX 4-bit build from the model publisher, MLX Community, or LM Studio Community
- no more than about 24 GB of downloaded model files, leaving memory for macOS and working applications
- useful as a fast helper, coding helper, or careful general assistant
- meaningfully different from a model already in the shared benchmark

Popularity was used only to find candidates. Local task results determine the final order.

## Selected builds

| Exact build | Revision | Download | Why test it |
|---|---|---:|---|
| [Gemma 4 26B A4B QAT, MLX 4-bit](https://huggingface.co/lmstudio-community/gemma-4-26B-A4B-it-QAT-MLX-4bit) | `f03a4a76828804e3b56758627383fbc7bd32015c` | 15.64 GB | Popular multimodal mixture-of-experts model with a large context window. |
| [Gemma 4 E4B, MLX 4-bit](https://huggingface.co/lmstudio-community/gemma-4-E4B-it-MLX-4bit) | `fa6f15978ba53de9ff3a95ce2821deb0ca4a15f0` | 6.86 GB | Small, fast multimodal helper and the most-downloaded MLX text-capable build found in the search. |
| [LFM2 24B A2B, MLX 4-bit](https://huggingface.co/lmstudio-community/LFM2-24B-A2B-MLX-4bit) | `f86ea2ca24bcee27aa23f3552f199f3f92a48560` | 13.42 GB | On-device mixture-of-experts model with about 2.3B active parameters per token. |
| [NVIDIA Nemotron 3 Nano 30B A3B, MLX 4-bit](https://huggingface.co/lmstudio-community/NVIDIA-Nemotron-3-Nano-30B-A3B-MLX-4bit) | `543873e66e36362182738b0d2863a766728045aa` | 17.79 GB | Efficient coding, reasoning, and tool-use comparison from a separate model family. |
| [Qwen3 Coder 30B A3B, MLX 4-bit](https://huggingface.co/lmstudio-community/Qwen3-Coder-30B-A3B-Instruct-MLX-4bit) | `bbecedefd826819d2c6b6465e88ca7b9b8ad3407` | 17.19 GB | Widely downloaded coding-focused model with 30.5B total and 3.3B active parameters. |

## Not selected

- [Qwen3 Coder Next, MLX 4-bit](https://huggingface.co/lmstudio-community/Qwen3-Coder-Next-MLX-4bit) is 44.86 GB before context memory. It would leave too little of the machine's 48 GB unified memory for the operating system, Codex, Chrome, and the runtime.
- One-bit, two-bit, uncensored, and model-to-model distilled community builds were not added in this pass because their quality claims are harder to compare and the existing 4-bit builds provide a stronger baseline.
- Other bit depths of the same model were not added. The first goal is to compare model families; a later quantization study can compare 4-bit, 6-bit, and 8-bit builds without mixing that question into the model ranking.

## Runtime note

Gemma 4 uses the multimodal `mlx-vlm` loader. The other selected builds use `mlx-lm`. The leaderboard records these as separate runtimes and identifies how each speed value was measured.
