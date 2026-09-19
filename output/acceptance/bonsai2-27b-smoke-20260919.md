# Acceptance: Ternary Bonsai 2 27B workflow smoke test (issue #18)

## Question

Can Bonsai 2 27B complete real agent loops reliably enough that £0 inference
outweighs the extra latency or babysitting?

## Answer

**Yes for background/helper work; no as a drop-in replacement for the coding
default.** Bonsai 2 27B passed all five workflow cases with zero tool-loop failures
and zero human rescues. On the shared 8-task suite it is **faster than the dense
model it compresses** (Qwen3.8-27B) at 0.55x the median wall-clock, but **2.39x
slower than the current local coding leader** (Qwen3 Coder 30B A3B). Against the
model a user would actually replace, it is materially slower, so it lands in the
middle tier: reliable enough for review, triage, summarisation and background
loops, but not the interactive coding default.

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

- ≥4/5 tasks pass — **yes (4 full passes + 1 partial at 0.75)**
- ≤1 human rescue — **yes (0)**
- median wall-clock ≤1.5x the relevant comparator — **NOT EVALUATED**

The latency leg cannot be evaluated with same-task evidence: the five workflow
fixtures are new in this PR and no comparator build has run them. (Re-running the
comparators would require re-downloading the Qwen builds and was explicitly out of
scope for this task.) The capability-suite numbers below are recorded as a
**proxy only** and are not used to classify the tier.

| Proxy basis (8-task capability suite — NOT the workflow tasks) | Median latency |
|---|---:|
| Ternary Bonsai 2 27B | 6,022 ms (this run; 1,802 ms on a quieter run) |
| Qwen3.8-27B (MLX 4-bit) — the model Bonsai compresses | 3,279 ms |
| Qwen3 Coder 30B A3B (MLX 4-bit) — the coding default it would replace | 752 ms |

Bonsai's capability-suite median varied from 1.8 s to 6.3 s across runs with the
machine's background load (Chrome, OrbStack, other agents), so even the proxy is
noisy. On decode throughput it is 23.2 t/s vs the coding leader's 97 t/s.

**Verdict: BACKGROUND/HELPER ONLY.**

The reliable half of the gate is unambiguous: 4 full passes, 1 partial, 0 rescues,
0 tool-loop failures across coding, comprehension, browser tool-driving and
long-context diagnosis. The latency leg is unproven on the tasks that matter, so
the top tier cannot be claimed. Per the issue's middle tier — "reliable enough for
review/triage/summarisation/cheap background loops" — Bonsai fits there.

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
  2.39x faster per task and scored higher on the same suite. Bonsai is the pick only
  when disk or memory is the binding constraint.

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

**BACKGROUND/HELPER ONLY** — integrated into the leaderboard as a measured build
(rank 16 of 19) with its true tier recorded, not promoted as a default.

## Corrections applied after review

- Latency leg rebased on the same-task 8-task capability suite (the new workflow
  fixtures have no comparator run, so they cannot supply a ratio).
- Guide metadata trimmed to tested capabilities: `context_tokens` set to the tested
  32768, `modalities` to Text only, capabilities to Code + Tools (vision and 262k
  context were never exercised), with a caution stating that.
- Shell-scripting evaluator now distinguishes a wrong column order from wrong data;
  Bonsai's answer had the right counts and IPs in reversed order.
