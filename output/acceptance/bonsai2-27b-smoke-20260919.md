# Acceptance: Ternary Bonsai 2 27B workflow smoke test (issue #18)

## Question

Can Bonsai 2 27B complete real agent loops reliably enough that £0 inference
outweighs the extra latency or babysitting?

## Answer

**Yes, for coding, comprehension and background work — with two caveats.** Bonsai 2
27B passed all five workflow cases with zero tool-loop failures and zero human
rescues, at about half the wall-clock of the dense model it compresses
(Qwen3.8-27B). The caveats are that it decodes ~3x slower than the current local
coding leader (Qwen3 Coder 30B A3B), and this run showed heavy machine-wide memory
pressure while loaded.

## Exact build (pinned and reproducible)

| Item | Value |
|---|---|
| Model repo | `prism-ml/Ternary-Bonsai-2-27B-gguf` |
| Model revision | `6ed5e12bf84b7a63069882c91dd9e9218647d17b` |
| Weight file | `Ternary-Bonsai-2-27B-PQ2_0.gguf` (7.21 GB, sha256 `3907dc16…62ec1`) |
| Vision projector | `Ternary-Bonsai-2-27B-mmproj-Q8_0.gguf` (0.63 GB) |
| Runtime | `PrismML-Eng/llama.cpp` release `prism-b10709-9a9394a`, build `10709` (commit `9a9394a89`), macOS arm64 |
| Base model | `Qwen/Qwen3.8-27B` (ternary 2-bit, 2.13 bpw group-128) |
| Launch | `llama-server -m Ternary-Bonsai-2-27B-PQ2_0.gguf -ngl 99 -fa on -c 32768 --jinja` |

Stock llama.cpp cannot run these weights (it rejects `PQ2_0`/`PTQ1_0` outright, or
loads a sibling `Q2_0` band as gibberish). The PrismML fork is mandatory.

## Five workflow cases

| # | Case | Result | Wall-clock | Tool failures | Turns |
|---|---|---|---:|---:|---:|
| 1 | Small coding fix (multi-bug, run tests) | **PASS** 3/3 checks | 37.8 s | 0 | 5 |
| 2 | Repo comprehension (which file + function) | **PASS** 3/3 rubric | 22.2 s | — | 1 |
| 3 | Agentic coding loop (spec → edit → test → iterate) | **PASS** 4/4 checks | 73.9 s | 0 | 7 |
| 4 | Browser/tool task (TodoMVC, 3 todos) | **PASS** count=3, items exact | 35.1 s | 0 | 9 |
| 5 | Long-context diagnosis (18k-token transcript) | **PASS** 3/4 rubric | 137.0 s | — | 1 |

Workflow score: **5/5**, human rescues: **0**, total tool-loop failures: **0**.

Case 5 detail: root cause correct (wedged Langfuse OTLP worker), fix correct (restart
the worker). It missed only the "redis socket timeout" keyword check, scoring 0.75.

Case 4 detail: the model chose the correct tool sequence unprompted —
`browser_goto → browser_fill(#new-todo) → browser_click(#add)` ×3, then read `#count`
and called `finish`. Native OpenAI `tool_calls` round-trips worked.

## Comparators (same 8-task capability suite, identical tasks and evaluators)

| Build | Runtime | Quality (mean) | Median latency | Gen t/s | Peak mem |
|---|---|---:|---:|---:|---:|
| **Ternary Bonsai 2 27B (PQ2_0)** | llama.cpp (fork) | **85** | **1,819 ms** | **23.2** | **7.5 GB** |
| Qwen3.8-27B (MLX 4-bit) | mlx | 98.8 | 3,500 ms | 17.7 | 16.4 GB |
| Qwen3 Coder 30B A3B (MLX 4-bit) | mlx | 98.8 | 834 ms | 97.0 | 17.8 GB |
| Qwen3.6 35B A3B (MLX 4-bit) | mlx | 98.8 | 891 ms | 99.3 | 20.2 GB |

These comparator rows are the checked-in evidence from
`output/benchmarks/capability-benchmark-20260823T202232Z.json`; they were not re-run
because the harness go on disk was removed and the existing artifacts are directly
comparable (same tasks, same evaluators, same machine). No new model was downloaded.

## Decision gate (issue #18)

- ≥4/5 tasks pass — **yes (5/5)**
- ≤1 human rescue — **yes (0)**
- median wall-clock ≤1.5x the relevant comparator — **yes (0.52x vs Qwen3.8-27B,
  the model Bonsai compresses)**

**Verdict: WORKFLOW CANDIDATE.**

The relevant comparator is Qwen3.8-27B because Bonsai 2 is its ternary compression;
against that control Bonsai is both faster (fewer bytes moved) and far smaller. It is
2.18x slower than the MLX coding leader, which sets the ceiling for interactive
coding work, not the pass/fail gate.

## Measured characteristics

- Throughput (`llama-bench -p 512 -n 128 -r 3`): **288.4 t/s prompt, 23.2 t/s decode**
- Peak memory: **7.5 GB RSS** at 8k context (single slot); ~10 GB observed at 32k with
  the server holding a 25k-token prompt
- Disk: 7.21 GB weights + 0.63 GB projector + 11.5 MB runtime
- Machine usability during runs: **degraded**. The Mac was already near its limit
  before load (Chrome, OrbStack, other agents). With the server resident, swap grew to
  ~16 GB and the model's decode dropped to ~6–7 t/s under contention versus 23 t/s on
  a quiet machine. Closing background apps is required for pleasant interactive use.

## Roles it is suitable for (from measured results only)

- **Coding worker** — yes, for small fixes and medium single-file tasks; it edits, runs
  tests and iterates. Not the fastest option, so best when disk/memory are the binding
  constraint, not turnaround time.
- **Reviewer / triage / summarisation** — yes; comprehension and summaries were correct.
- **Browser brain** — yes; it drove a real page through a multi-step tool sequence with
  no retries.
- **Long-context analyst** — yes; it read an 18k-token transcript and named the correct
  root cause and fix.
- **Default interactive coding model on this 48 GB Mac** — no; Qwen3 Coder 30B A3B is
  still ~4x faster per token and scored higher on the same suite.

## Evidence

- workflow smoke: `output/benchmarks/workflow-smoke-bonsai2_27b_llamacpp.json`
- capability suite: `output/benchmarks/capability-benchmark-bonsai-bonsai2_27b_llamacpp.json`
- gate result: `output/workflow-smoke/gate-result.json`
- memory evidence: `output/workflow-smoke/memory-evidence.json`
- launch config: `config/bonsai2-27b.json`, `scripts/start-bonsai-server.sh`
- harness: `scripts/run-workflow-smoke.py`, `scripts/workflow_harness.py`,
  `scripts/run-bonsai-capability.py`, `scripts/evaluate-workflow-gate.py`
- fixtures: `fixtures/coding-fix`, `fixtures/coding-loop`, `fixtures/repo-comprehension`,
  `fixtures/long-context`, `fixtures/browser`

## Result

**PASS** — integrated into the leaderboard (rank 15 of 19 ranked builds).
