# Acceptance: Qwen3.8 27B local benchmark and guide integration

## Expected behavior

- Install the exact `mlx-community/Qwen3.8-27B-4bit` revision.
- Complete the same eight-task capability and three-trial MLX throughput protocol as the two current leaders.
- Regenerate the leaderboard and current installed-model guide.
- Show Qwen3.8 in the 24-build local inventory across desktop, wide, tablet, and mobile layouts.

## Executed steps

1. Added revision `3e6447f082e89cc7f0bc6e5441afd38dfce760ff` to the recommended MLX manifest.
2. Ran one combined benchmark for `qwen38_27b_mlx4`, `qwen36_35b_a3b_mlx4`, and `qwen3_coder_30b_a3b_mlx4`.
3. Regenerated the overall leaderboard and installed-model inventory.
4. Built the Vite site.
5. Confirmed the old 23-build Playwright assertion failed in all four projects.
6. Updated the smoke flow to require 24 builds and a visible `Qwen3.8 27B` inventory heading.
7. Reran the full flow in desktop, wide, tablet, and mobile projects; all four passed.

## Direct comparison

All three models passed every capability invocation and earned 98.8 task quality under the shared protocol.

| Model | Local rank | Work fit | Task quality | Median response | Prompt speed | Generation speed | Peak memory |
|---|---:|---:|---:|---:|---:|---:|---:|
| Qwen3 Coder 30B A3B | 1 | 98.3 | 98.8 | 0.75 s | 1331.7 tok/s | 97.0 tok/s | 17.8 GB |
| Qwen3.6 35B A3B | 2 | 98.3 | 98.8 | 0.78 s | 980.3 tok/s | 99.3 tok/s | 20.2 GB |
| Qwen3.8 27B | 5 | 96.3 | 98.8 | 3.28 s | 364.1 tok/s | 17.7 tok/s | 16.4 GB |

Qwen3.8 matched both leaders on the suite's task-quality checks and used 1.4 GB less peak memory than Qwen3 Coder and 3.8 GB less than Qwen3.6. Its dense architecture generated about 82% more slowly than either sparse leader, so it is retained as the strongest current dense Qwen rather than replacing the fast defaults.

## Evidence

- combined raw benchmark: `output/benchmarks/capability-benchmark-20260823T202232Z.json`
- Qwen3.8 server log: `output/benchmarks/logs/20260823T202232Z-qwen38_27b_mlx4.log`
- Qwen3.6 server log: `output/benchmarks/logs/20260823T202232Z-qwen36_35b_a3b_mlx4.log`
- Qwen3 Coder server log: `output/benchmarks/logs/20260823T202232Z-qwen3_coder_30b_a3b_mlx4.log`
- generated leaderboard: `output/leaderboard/overall-leaderboard.json`
- generated inventory: `output/inventory/current-models.json`
- fresh browser artifacts: `output/playwright/qwen38-benchmark-20260823/`
- desktop full-page proof: `output/playwright/qwen38-benchmark-20260823/landing-the-guide-presents-54d55-t-installed-model-inventory-desktop/model-guide.png`
- mobile full-page proof: `output/playwright/qwen38-benchmark-20260823/landing-the-guide-presents-54d55-t-installed-model-inventory-mobile/model-guide.png`

## Result

PASS

The exact Qwen3.8 revision loads on the M5 Pro, completes the full local benchmark, appears in the regenerated 24-build guide, remains reachable through the image-capable inventory, and the complete filter/reset journey passes at all four tested viewport sizes without console errors.

## Remaining risk

The shared suite is intentionally short and produced a three-way quality tie. It does not yet measure long-context retrieval, vision quality, or multi-step repository-agent success. Qwen3.8 was benchmarked with thinking disabled for comparability. The browser proof used the local production build and preview, not a new Vercel deployment.
