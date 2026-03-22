# Open WebUI Acceptance Proof

- Target flow: Open Open WebUI, select a local Ollama model, enter a prompt, and verify a real response comes back in the browser.
- Runtime used: Docker `ollama-lab` on `http://localhost:11434` plus Docker `open-webui-lab` on `http://localhost:3001`.
- Browser evidence:
  - Snapshot after successful response: `/Users/rajeev/Code/tools/local-llm-lab/.playwright-cli/page-2026-03-22T00-09-45-797Z.yml`
  - The response text includes `LOCAL OLLAMA OK` from model `llama3.2:3b`.
- Server evidence:
  - Ollama process list showed `llama3.2:3b` loaded during the run via `GET /api/ps`.
  - Docker Ollama logs show `POST "/api/chat"` returning `200` at `2026-03-22 00:09:34`.
- Result: Pass for Open WebUI with a useful smaller local model (`llama3.2:3b`).
- Known follow-up issue:
  - `qwen3:30b` fails in Docker because the Ollama container only sees about `15.7 GiB` of RAM.
  - The Homebrew Ollama runtime currently fails earlier with a local Metal backend compile error, including for `llama3.2:3b` and `qwen3:30b`.
