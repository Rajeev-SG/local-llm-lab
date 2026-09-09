# Magnitude (llama.cpp) evaluation - 2026-09-09

- Goal: Profile this Mac with the Magnitude CLI, audit real memory pressure, and
  establish a speed/intelligence/memory Pareto frontier for the GGUF/llama.cpp runtime.
- Tool: [Magnitude](https://github.com/magnitudedev/magnitude) v0.0.14
  (Apache-2.0; Rust engine over llama.cpp; loopback service on
  `127.0.0.1:10100` with OpenAI- and Anthropic-compatible endpoints).
- Hardware assessment: 59 catalog models ranked against this machine.
- Models installed and kept: `gemma-4-26b-a4b-it-qat:gguf:q4` (15.4 GB),
  `gemma-4-e2b-it-qat:gguf:q4` (3.6 GB).
- Benchmark method: Magnitude service + OpenAI Chat Completions endpoint,
  256-300-token generations, temperature 0.2, agent-style prompts. First
  request after a model load pays load time; cold numbers are discarded.

**Speed basis warning (same rule as the README leaderboard): these are
llama.cpp/GGUF numbers and must not be compared with the MLX numbers in
`overall-leaderboard.md`.** For scale, on this same machine the MLX 4-bit
builds measured far faster (Qwen3.6 35B A3B MLX: 99.3 gen tok/s vs Magnitude's
28-37 tok/s predicted for the GGUF Q5 build). Magnitude's value is automated
configuration and memory guarding, not peak throughput; MLX remains the speed
runtime on Apple silicon.

## Legend

- measured = run in this session against this machine
- predicted = Magnitude's hardware-profiled estimate (not benchmarked)
- Int = Artificial Analysis Intelligence Index, a model-level score (same
  across quants; not a probability)

## 1. Actual memory state (measured with the normal stack running)

Normal stack = Chrome, OrbStack, VS Code, Codex, OMP sessions, dolt, node.

| Signal | Value | Meaning |
|---|---|---|
| Chrome RSS | 23.8 GB | Half of total RAM in one app |
| Other heavy apps | node 2.8, omp 1.6, Codex 1.4, VS Code 0.9, OrbStack 0.9, dolt 0.8 GB | |
| Swap at baseline | 19.7 GB used (of 20 GB) | Already swapping before any model ran |
| Swap after running the 17.8 GB model | 31.3 GB used (macOS grew swapfiles to 32 GB) | 17 GB+ model + normal stack = real thrash |
| Free pages at trough | 0.1 GB | Zero headroom |
| Swap-in rate (60 s sample) | 285 MB/min | Active page-in churn |
| Compressor churn (60 s sample) | ~55 GB/min compress + decompress | CPU burning on memory management |
| Magnitude memory guard (measured) | Refused the 26B load: needs 19.1 GB, had 17.3 GB; loaded on retry when available fluctuated to 20.9 GB | Guard works; load success is fluctuation-dependent |

### Safe allocation verdict

- Normal stack running: <=12 GB comfortable, <=7 GB truly safe (E2B-tier).
  The 17.8 GB Gemma 26B loads only when Chrome temporarily sheds memory, and
  while running it pushed swap to 31 GB - the Mac gets unpleasant.
- Chrome closed (~24 GB freed, swap compacts): 24-26 GB models safe with
  ~6 GB headroom; 29.9 GB (Qwen3.6 35B Q5) workable but tight.
- Disk: the Data volume had only ~20 GiB free at evaluation time (the README
  inventory of 23 Aug still said ~187 GiB). The 35B model (28.5 GB download)
  needs ~9 GB freed first.
- The 19.7 GB baseline swap predates any model work; a reboot or Chrome
  session cleanup improves every number here.

## 2. Pareto frontier (GGUF/llama.cpp basis)

| Point | Model + config | Int | Speed | Memory | Context | Coexists with normal stack? |
|---|---|---|---|---|---|---|
| Max speed | Gemma 4 E2B (Q4 QAT) measured | 10% | 93-97 tok/s measured (66-91 predicted) | 4.7 GB | 64K | Yes, trivially |
| Fast + smarter-small | Qwen3.5 4B Q5 predicted | 20% | ~27-36 tok/s | 7 GB | 64K | Yes |
| Best balanced | Gemma 4 26B-A4B (Q4 QAT) measured | 26% | 42-48 tok/s measured warm (31-42 predicted) | 17.8 GB | 100K | No - close Chrome |
| Speed-intelligence MoE ceiling | Qwen3.6 35B-A3B Q5 predicted | 32% | ~28-37 tok/s | 29.9 GB | 100K | No - everything closed; free disk first |
| Max intelligence (theoretical) | Qwen3.8 27B Q4 (dense) predicted | 52% | ~7-8 tok/s | 24.1 GB | 100K | No - and unusable in agent loops |

### Benchmark evidence

| Model | Test | Prompt tok | Decode tok/s | Note |
|---|---|---|---|---|
| Gemma 4 E2B Q4 QAT | decode-256 | 32 | 9.7 cold, 93-97 warm | Cold run dominated by model load |
| Gemma 4 E2B Q4 QAT | agentish ~500 ptok | 573 | 87.7 | |
| Gemma 4 26B-A4B Q4 QAT | decode (cold) | 32 | 6.3-12.5 | Weights still paging in / pressure |
| Gemma 4 26B-A4B Q4 QAT | decode (warm x3) | 32 | 42.3 / 44.8 / 47.5 | Above predicted range top (31-42) |
| Gemma 4 26B-A4B Q4 QAT | agentish ~500 ptok | 573 | 43.8 | |
| Gemma 4 26B-A4B Q4 QAT | 4K-prompt agentish | 4030 | 29.4 decode, 395 prefill | |
| Gemma 4 26B-A4B Q4 QAT | 8K-prompt log analysis | 8033 | 13.3 decode, 427 prefill | Single noisy sample under memory pressure; long-context agent runs likely need Chrome closed |
| Liquid LFM2.5 2.6B Q4 | decode-256 / agentish | 25 / 507 | 52.3 / 56.5 | Dominated by E2B (same Int tier, slower) - removed |

Not benchmarked (did not fit disk at the time): Qwen3.6 35B-A3B Q4/Q5,
Qwen3.8 27B Q4, Nemotron 3.5 Lightning 30B Q4, Muse Glimmer 30B Q4. Those
rows are Magnitude predictions. The dense 52%-intelligence Qwen3.8 27B fails
the agent-loop usability test at ~7-8 tok/s regardless of measurement.

Coding-agent relevance:

- All frontier picks support tools + structured output; the Gemma family adds
  vision. Nemotron Lightning lacks vision.
- Quantization accuracy: QAT/Q5 variants rated "High" by Magnitude; plain Q4
  "Medium". Gemma 4 is quantization-aware-trained, so Q4 QAT holds accuracy.
- Magnitude configures speculative decoding automatically (E2B: none;
  LFM/Qwen MoE: DSpark/DFlash). Agent prefills measured 395-427 tok/s on the
  26B - decode is the bottleneck, not prefill.

## 3. Three practical choices (llama.cpp basis)

| | Pick | Exact model ID | Speed | Coexistence |
|---|---|---|---|---|
| Fast everyday | Gemma 4 E2B (Q4 QAT) | `gemma-4-e2b-it-qat:gguf:q4` | ~95 tok/s measured | Runs alongside everything, always |
| Best balanced | Gemma 4 26B-A4B (Q4 QAT) | `gemma-4-26b-a4b-it-qat:gguf:q4` | 42-48 tok/s measured | Close Chrome first (VS Code + Codex alone are fine) |
| Maximum intelligence | Qwen3.6 35B-A3B Q5 | `qwen3.6-35b-a3b:gguf:q5` | ~28-37 tok/s predicted | Close Chrome; free ~9 GB disk, then pull |

Cross-reference with the MLX leaderboard: for raw speed and the coding
default, the existing MLX builds (Qwen3 Coder 30B A3B at ~97 tok/s,
Qwen3.6 35B A3B at ~99 tok/s) remain faster than anything in this GGUF
frontier; Magnitude's tier wins on automated setup, harness wiring, and
memory guarding.

Wiring into coding agents (OMP / OpenCode supported natively):

```bash
magnitude connections add oh-my-pi --set-model gemma-4-26b-a4b-it-qat:gguf:q4
magnitude connections add opencode --set-model gemma-4-26b-a4b-it-qat:gguf:q4
```

To fetch the max-intelligence pick once disk allows:

```bash
magnitude catalog pull qwen3.6-35b-a3b:gguf:q5
```

## Caveats

- Magnitude is v0.0.14 alpha; catalog is curated GGUF/llama.cpp only (no MLX).
- Speed predictions are hardware-aware estimates, not benchmarks; measured
  numbers came from single-session runs under live memory pressure. No user
  apps were closed during the evaluation.
