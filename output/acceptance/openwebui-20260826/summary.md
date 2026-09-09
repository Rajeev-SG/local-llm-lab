# Open WebUI acceptance proof — 2026-08-26

## Result

PASS with a documented hardware boundary. Open WebUI 0.11.1 exposes all 21
installed Ollama models under clean `Local LLM Lab — …` display names, exposes
the configured OpenRouter catalogue, and has five verified MCP connections plus
the isolated Open Terminal connection.

## User-level checks

- Opened the model picker and searched for `Local LLM Lab`.
- Confirmed all 21 local model records through the authenticated Open WebUI API.
- Confirmed every local display name includes the curated model name, parameter
  size, and installed disk size; zero display names contain `:latest`.
- Sent a real chat through `llama3.2:3b-cpu` and received `LOCAL_UI_OK`.
- Sent a real chat through OpenRouter's `Z.ai: GLM 5.3 Flash` and received
  `OPENROUTER_UI_OK`.
- Verified Fetch, Context7, Isolated Playwright, OpenAI Developer Docs, and
  draw.io MCP connections, plus the isolated terminal connection.

## Capacity boundary

Docker currently has 16.8 GB decimal (15.7 GiB) of memory. Thirteen local
models fit the configured runtime budget. Eight installed models are still
listed but are explicitly labelled `Needs more RAM`; loading them would exceed
the current Docker allocation. Raising OrbStack's global memory limit requires
a runtime restart and can interrupt the other running containers, so it was not
performed implicitly.

## Evidence

- `local-llm-lab-model-catalog.png`: clean Local LLM Lab model picker.
- `local-ui-ok.png`: successful local Ollama chat through Open WebUI.
- `openrouter-ui-ok.png`: successful OpenRouter chat through Open WebUI.
