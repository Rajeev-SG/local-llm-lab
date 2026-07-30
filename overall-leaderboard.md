# Overall Local Model Leaderboard

- Generated: `2026-07-19T22:27:48+00:00`
- Machine: `Apple M5 Pro, 48 GB unified memory, 15 CPU cores, 16 GPU cores`
- Exact model builds recorded: `26`
- Fully capability-benchmarked builds: `17`

## Ranked Models

The work-fit score puts most weight on structured coding-adjacent tasks, then response time and runtime reliability. Models are only ranked after completing the shared eight-task suite.

| Rank | Exact build | Runtime | Work fit | Task quality | Median response | Generation speed | Peak memory |
|---:|---|---|---:|---:|---:|---:|---:|
| 1 | Qwen3 Coder 30B A3B (MLX 4-bit) | mlx | 98.3 | 98.8 | 0.74 s | 98.8 tok/s | 17.8 GB |
| 2 | Qwen3.6 35B A3B (MLX 4-bit) | mlx | 98.2 | 98.8 | 0.89 s | 94.0 tok/s | 20.2 GB |
| 3 | Gemma 4 E4B (MLX 4-bit) | mlx_vlm | 97.2 | 97.6 | 0.89 s | 47.0 tok/s | n/a |
| 4 | Gemma 4 26B A4B QAT (MLX 4-bit) | mlx_vlm | 96.7 | 96.8 | 0.82 s | 51.6 tok/s | n/a |
| 5 | Qwen3.6 27B (MLX 4-bit) | mlx | 95.6 | 98.8 | 4.52 s | 13.5 tok/s | 16.4 GB |
| 6 | qwen3.5:9b | ollama | 91.1 | 96.8 | 10.97 s | 8.0 tok/s | n/a |
| 7 | qwen2.5-coder:14b | ollama | 89.9 | 96.0 | 12.94 s | 8.7 tok/s | n/a |
| 8 | Devstral Small 2 24B (MLX 4-bit) | mlx | 89.9 | 92.0 | 4.84 s | 14.1 tok/s | 14.7 GB |
| 9 | Nemotron 3 Nano 30B A3B (MLX 4-bit) | mlx | 89.0 | 87.2 | 0.85 s | 103.2 tok/s | 19.6 GB |
| 10 | qwen2.5:14b | ollama | 88.4 | 93.8 | 11.85 s | 9.8 tok/s | n/a |
| 11 | phi4 | ollama | 86.2 | 90.8 | 11.31 s | 10.3 tok/s | n/a |
| 12 | GLM-4.7-Flash (MLX 4-bit) | mlx | 86.0 | 84.0 | 1.30 s | 69.7 tok/s | 17.5 GB |
| 13 | mistral-small:22b | ollama | 82.6 | 90.0 | 25.13 s | 5.8 tok/s | n/a |
| 14 | Qwen3.5 9B (MLX 4-bit) | mlx | 78.6 | 74.8 | 1.30 s | 53.4 tok/s | 5.9 GB |
| 15 | gpt-oss-20b (MLX MXFP4/Q4) | mlx | 70.6 | 65.8 | 2.43 s | 98.4 tok/s | 11.7 GB |
| 16 | apfel | apfel | 63.7 | 55.8 | 0.96 s | n/a | n/a |
| 17 | LFM2 24B A2B (MLX 4-bit) | mlx | 63.3 | 54.8 | 0.53 s | 139.2 tok/s | 13.8 GB |

## Tested but not ranked

These builds have real local evidence but did not complete the shared capability suite, so they are listed without an invented score.

| Exact build | Runtime | Status | Strongest evidence | Note |
|---|---|---|---|---|
| llama3.2:3b | ollama | passed | `output/acceptance/openwebui-proof-20260322.md` | Returned the required text through Open WebUI. |
| gpt-oss:20b | ollama | passed_with_notes | `output/acceptance/model-sweep-20260322.md` | Ran successfully but exposed reasoning text during the exact-response test. |
| gemma3:12b | ollama | passed | `output/acceptance/model-sweep-20260322.md` | Passed the exact-response command-line smoke test. |
| Apriel 1.6 15B Thinker (Q4_K_M) | ollama | passed_with_notes | `output/acceptance/model-sweep-20260322.md` | Ran successfully but exposed reasoning text during the exact-response test. |
| qwen3:30b | ollama | runtime_failed | `output/acceptance/model-sweep-20260322.md` | The runner stopped during model load in the constrained Docker runtime. |
| qwen3-coder:30b | ollama | runtime_failed | `output/acceptance/model-sweep-20260322.md` | The runner stopped during model load in the constrained Docker runtime. |
| qwen2.5:72b | ollama | runtime_failed | `output/acceptance/model-sweep-20260322.md` | Required more memory than the Docker runtime exposed. |
| gemma4:e4b | ollama | runtime_failed | `output/benchmarks/capability-benchmark-20260409T175237Z.json` | No additional note recorded. |
| deepseek-r1:32b | ollama | runtime_failed | `output/acceptance/model-sweep-20260322.md` | The runner stopped during model load in the constrained Docker runtime. |

## Scoring method

- Task quality is weighted toward shell work, structured JSON, classification, concise synthesis, and instruction following because those match the coding-agent work recorded on this machine.
- Work fit is 80% weighted task quality, 15% median response-time utility, and 5% successful invocation rate.
- Generation speed and peak memory come from three MLX trials with a 512-token prompt and 128-token completion when available. Older Ollama speed is derived from its recorded generation counters.
- MLX-VLM generation speed is median end-to-end throughput from the capability requests, so its speed is not directly comparable with the isolated text-only MLX trials.
- Different runtime builds of the same base model remain separate because quantization and inference software materially change local speed and reliability.
- Smoke tests and failed load attempts remain visible, but they are not ranked against full benchmark runs.

## Source artifacts

- `output/acceptance/model-sweep-20260322.md`
- `output/acceptance/openwebui-proof-20260322.md`
- `output/benchmarks/capability-benchmark-20260409T173011Z.json`
- `output/benchmarks/capability-benchmark-20260409T175237Z.json`
- `output/benchmarks/capability-benchmark-20260719T202746Z.json`
- `output/benchmarks/capability-benchmark-20260719T203015Z.json`
- `output/benchmarks/capability-benchmark-20260719T204036Z.json`
- `output/benchmarks/capability-benchmark-20260719T204241Z.json`
- `output/benchmarks/capability-benchmark-20260719T205001Z.json`
- `output/benchmarks/capability-benchmark-20260719T205311Z.json`
- `output/benchmarks/capability-benchmark-20260719T213254Z.json`
- `output/benchmarks/capability-benchmark-20260719T215317Z.json`
- `output/benchmarks/capability-benchmark-20260719T215650Z.json`
- `output/benchmarks/capability-benchmark-20260719T215751Z.json`
- `output/benchmarks/capability-benchmark-20260719T222207Z.json`
