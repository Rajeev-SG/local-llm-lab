# Apfel Benchmark 2026-04-09

- Goal: Benchmark `apfel` against the current local LLM lab models on the six tasks claimed on the apfel site: shell scripting, text transformation, classification, short summaries, JSON restructuring, and translation. Also test whether the model refuses unknown facts instead of hallucinating, and whether that makes it a good fit for agentic coding workflows.
- Machine: `Apple M5 Pro`, `macOS 26.3.1 (a)`.
- apfel version: `0.9.6`.
- Ollama version: `0.18.2`.
- Benchmark summary: `/Users/rajeev/Code/tools/local-llm-lab/benchmark-results.md`
- Raw benchmark JSON: `/Users/rajeev/Code/tools/local-llm-lab/output/benchmarks/capability-benchmark-20260409T173011Z.json`
- Gemma 4 blocked-run artifact: `/Users/rajeev/Code/tools/local-llm-lab/output/benchmarks/capability-benchmark-20260409T175237Z.json`

## Important Runtime Note

The first benchmark attempt accidentally hit a stray host `ollama` process on `127.0.0.1:11434`, which reproduced the earlier Metal-runtime failures already documented in this repo. I stopped the host process, restarted the Docker `ollama-lab` container, confirmed `OrbStack` was the only listener on `11434`, and then reran the benchmark from the correct Docker-backed endpoint.

## Gemma 4 Addendum

I attempted to add `gemma4:e4b` after Google announced Gemma 4 on April 2, 2026. The local lab's default Ollama runtime (`0.18.2`) was too old to pull it, so I downloaded the latest official Ollama release (`v0.20.4`, published April 7, 2026) into `/tmp/ollama-0.20.4` and ran temporary servers on separate ports to avoid changing the default lab setup.

What happened:

- `gemma4:e4b` pulled successfully on the temporary `v0.20.4` runtime.
- The scored benchmark could not be completed because every inference attempt failed before first token with `model failed to load`.
- Temporary runners at `127.0.0.1:11435`, `127.0.0.1:11436`, and `127.0.0.1:11437` all reproduced the failure.
- Server logs showed a Gemma 4 runner crash in the Metal backend during kernel compilation rather than a prompt-quality problem.
- I also tried disabling flash attention and forcing more conservative backend flags, but the failure remained.

Practical conclusion: I do not have a fair Gemma 4 quality score for this machine yet. What I do have is a reproducible compatibility finding: as of this run, Gemma 4 is not usable in this local lab through Ollama on this Mac, even though the model can now be downloaded with a newer runtime.

## Results

Claimed capability average from the benchmark table:

- `apfel`: `0.65`
- `qwen3.5:9b`: `0.94`
- `phi4`: `0.85`
- `qwen2.5:14b`: `0.93`
- `qwen2.5-coder:14b`: `0.93`
- `mistral-small:22b`: `0.86`

Median task latency from the same run:

- `apfel`: `1.16 s`
- `qwen3.5:9b`: `12.55 s`
- `phi4`: `13.44 s`
- `qwen2.5:14b`: `12.75 s`
- `qwen2.5-coder:14b`: `15.55 s`
- `mistral-small:22b`: `28.85 s`

Task-level verdict on `apfel`:

- `short summaries`: strong
- `translation`: decent
- `text transformation`: decent
- `classification`: usable but behind the best local models
- `JSON restructuring`: weak on schema fidelity
- `shell scripting`: weak in this benchmark

## What Was True

- The site claim that `apfel` is good at short summaries is supported by the benchmark. It scored `1.00` on the summary task and answered much faster than the Ollama baselines.
- The claim that it is useful for text transformation and translation is partly supported. It was competent, but not best-in-lab.
- The claim that it is good at shell scripting and JSON restructuring is not supported by this benchmark. It chose the wrong log fields for the shell task and drifted away from the requested schema in the JSON task.

## Refusal vs Hallucination

- The synthetic unknown-fact test supports the narrow version of the claim that `apfel` prefers refusal over hallucination. It declined to invent a changelog for a made-up package.
- That behavior is not unique in this lab. All compared Ollama models also refused the same unknown-fact prompt instead of fabricating release details.
- apfel appears more eager to refuse or soften harmless instructions than the Ollama baselines. In the exact-output diagnostic, every compared Ollama model returned `OK` exactly; `apfel` returned `OK.` with extra punctuation and missed the strict formatting request.

Additional spot checks outside the scored benchmark were even more concerning:

- `apfel 'Respond with exactly the single token OK and nothing else.'` refused the request instead of answering.
- `printf 'Reply with exactly APFEL_OK\n' | apfel --permissive` hallucinated that `APFEL_OK` was an offensive German term and refused on that basis.

That means the practical answer is: yes, apfel leans conservative, but not in a uniquely useful way, and sometimes in a way that adds friction or invents a bogus safety rationale.

## Workflow Recommendation

Recommended uses:

- tiny offline summaries
- lightweight text cleanup
- quick local translation
- very small context offload where privacy and latency matter more than perfect structure

Not recommended as a primary engine for:

- shell-command generation in coding loops
- structured JSON transformation pipelines
- tool-heavy agent orchestration
- browser-operator style tasks
- primary coding or refactoring assistance

Additional note for Gemma 4:

- I would not attempt to route agentic coding workflows through local `gemma4:e4b` in this lab yet, because the current blocker is more basic than quality: local execution is not stable enough to benchmark honestly.

My current opinion: keep `apfel` around as a fast private side tool, not as a serious replacement for the better Ollama helpers in the lab and not as the core model in an agentic coding workflow.
