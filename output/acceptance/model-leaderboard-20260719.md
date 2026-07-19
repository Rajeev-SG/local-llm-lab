# Acceptance: overall local model leaderboard

## Expected behavior

- Install the recommended MLX models and the strongest additional Hugging Face candidates that fit the 48 GB machine.
- Run every selected build through the same eight capability tasks.
- Run three fixed MLX speed and memory trials for text-only builds.
- Keep older smoke tests and failed loads visible without assigning them invented scores.
- Generate one deduplicated leaderboard for every exact build tested on this machine.

## Executed steps

1. Pinned every selected Hugging Face build to an exact revision.
2. Downloaded and loaded six original recommendations plus five additional Hugging Face candidates.
3. Ran shell, text transformation, classification, summary, JSON restructuring, translation, factual refusal, and exact-output tasks at temperature zero.
4. Ran three 512-token prompt and 128-token generation trials for each text-only MLX build.
5. Used `mlx-vlm` for Gemma 4 and recorded its speed as median end-to-end request throughput rather than mixing it with the isolated text-only trials.
6. Regenerated Markdown, JSON, CSV, and site data from the saved benchmark artifacts.

## Evidence

- Final leaderboard: `overall-leaderboard.md`
- Machine-readable leaderboard: `output/leaderboard/overall-leaderboard.json`
- CSV leaderboard: `output/leaderboard/overall-leaderboard.csv`
- Hugging Face selection record: `huggingface-candidate-search.md`
- Final Qwen3 Coder run: `output/benchmarks/capability-benchmark-20260719T215751Z.json`
- Final Gemma 4 E4B run: `output/benchmarks/capability-benchmark-20260719T213254Z.json`
- Final Gemma 4 26B run: `output/benchmarks/capability-benchmark-20260719T215317Z.json`
- Final Nemotron run: `output/benchmarks/capability-benchmark-20260719T215650Z.json`
- Final LFM2 run: `output/benchmarks/capability-benchmark-20260719T222207Z.json`

## Result

PASS for model installation, benchmark execution, deduplication, and generated leaderboard data.

- Exact builds recorded: 26
- Fully ranked builds: 17
- Tested but not ranked: 9
- First place: Qwen3 Coder 30B A3B, MLX 4-bit
- Best broad model: Qwen3.6 35B A3B, MLX 4-bit
- Best smaller broad helper: Gemma 4 E4B, MLX 4-bit
- Fastest raw generation: LFM2 24B A2B, MLX 4-bit, but its task quality is too low for a default role

## Remaining risk

- The suite is intentionally short and weighted toward the owner's coding, terminal, structured-data, and summary work. A longer coding benchmark may separate the two leading Qwen models more clearly.
- MLX-VLM speed includes the whole request and cannot be compared directly with isolated MLX generation speed.
- Peak unified memory is not yet recorded for MLX-VLM runs.
- The public site view is not covered by this acceptance result. It requires a separate browser and design proof after the saved design direction is available.
