# Local Model Sweep - 2026-03-22

- Goal: Research the strongest useful Ollama models likely to fit this machine's current Docker runtime, then prove which ones actually run.
- Runtime used: Docker `ollama-lab` on `http://localhost:11434` and Docker `open-webui-lab` on `http://localhost:3001`.
- Key runtime constraint: Docker Ollama reports about `15.7 GiB` visible system memory, so larger 30B+ loads are still expected to fail.

## Passing CLI tests

- `mistral-small:22b`
  - Prompt: `Reply with exactly: MISTRAL22 OK`
  - Result: Pass
- `phi4`
  - Prompt: `Reply with exactly: PHI4 OK`
  - Result: Pass
- `gemma3:12b`
  - Prompt: `Reply with exactly: GEMMA12 OK`
  - Result: Pass
- `qwen2.5:14b`
  - Prompt: `Reply with exactly: QWEN14 OK`
  - Result: Pass
- `qwen2.5-coder:14b`
  - Prompt: `Reply with exactly: QWENCODER14 OK`
  - Result: Pass
- `qwen3.5:9b`
  - Prompt: `Reply with exactly: QWEN35_9B OK`
  - Result: Pass, but it exposed reasoning text before the final answer
- `ServiceNow-AI/Apriel-1.6-15b-Thinker:Q4_K_M`
  - Prompt: `Reply with exactly: APRIEL15 OK`
  - Result: Pass, but it exposed reasoning text before the final answer
- `gpt-oss:20b`
  - Prompt: `Reply with exactly: GPTOSS20 OK`
  - Result: Pass, but it exposed reasoning text before the final answer

## Browser proof

- Strongest passing model: `mistral-small:22b`
- Browser flow: Open Open WebUI, keep `mistral-small:22b` selected, enter a prompt, submit it, and verify the response in the chat transcript.
- Prompt entered: `In one sentence, say the currently selected model is working and end with the exact words BROWSER MISTRAL OK.`
- Result: Pass
- Evidence:
  - Response snapshot: `/Users/rajeev/Code/tools/local-llm-lab/.playwright-cli/page-2026-03-22T00-44-59-270Z.yml`
  - Network log: `/Users/rajeev/Code/tools/local-llm-lab/.playwright-cli/network-2026-03-22T00-44-59-254Z.log`
  - Ollama log evidence: Docker logs show `POST "/api/chat"` returning `200` at `2026-03-22 00:44:50`

## Earlier larger-model failures

- `qwen2.5:72b`
  - Failed because required memory exceeded what the runtime had available.
- `qwen3:30b`
  - Failed because the llama runner was killed during load.
- `qwen3-coder:30b`
  - Failed because the llama runner was killed during load.
- `deepseek-r1:32b`
  - Failed because the llama runner was killed during load.

## Current answer

- Biggest model proven working locally right now: `mistral-small:22b`
- Best tested coding-focused option in the proven-working set: `qwen2.5-coder:14b`
- Best tested mid-size general alternatives: `phi4`, `qwen2.5:14b`, `gemma3:12b`, and `qwen3.5:9b`
- Worth testing from the screenshot and now confirmed runnable: `qwen3.5:9b`, `ServiceNow-AI/Apriel-1.6-15b-Thinker:Q4_K_M`, and `gpt-oss:20b`
- Caveat on the additional screenshot models: they run on this hardware, but all three leaked reasoning during a simple exact-string test, so I would rank them below `mistral-small:22b`, `phi4`, `qwen2.5:14b`, and `qwen2.5-coder:14b` for clean day-to-day local use

## Screenshot follow-up recommendation

- Worth testing and now validated:
  - `qwen3.5:9b`
  - `ServiceNow-AI/Apriel-1.6-15b-Thinker:Q4_K_M`
  - `gpt-oss:20b`
- Not worth testing on the current Docker runtime:
  - `qwen3.5:27b`
  - `qwen3.5 35B A3B`
  - other screenshot entries above the proven 20B to 22B class unless the Ollama memory ceiling changes
- Practical recommendation:
  - If you want the strongest clean local general model, use `mistral-small:22b`
  - If you want a strong coding model, use `qwen2.5-coder:14b`
  - If you want to experiment with reasoning-heavy models from the screenshot, `gpt-oss:20b` and `Apriel-1.6-15b-Thinker` are both runnable here, but expect visible reasoning output unless you tune prompts or generation settings around it
