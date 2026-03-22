You are on my Apple-silicon MacBook Pro with 48 GB unified memory.

Goal:
Set up a clean, ergonomic local-LLM workstation optimized for:
1) chatting with local models,
2) benchmarking / quickly switching between models,
3) using Claude Code against a local Ollama backend,
4) keeping the setup maintainable and easy to operate.

Use web search as needed, but prefer official docs:
- Ollama docs
- Open WebUI docs
- MLX / MLX-LM official docs or repos
- LM Studio docs only for comparison if useful

Do not ask me unnecessary questions. Inspect the machine and make the best reasonable decisions automatically.

What to install and configure:
1) Ollama as the primary local model runtime
2) Open WebUI as a local browser UI on top of Ollama, if Docker is available and healthy
3) Claude Code configured to use Ollama’s Anthropic-compatible local endpoint for model inference
4) Optional MLX-LM path for Apple-silicon-native experiments, but only if it does not clutter the main workflow

Models to pull/configure in Ollama:
- qwen3:30b
- deepseek-r1:32b
- qwen2.5:72b
- qwen3-coder:30b

What I want you to do:
A) Audit current state first
- Check macOS version
- Check Homebrew
- Check Docker / Docker Desktop availability
- Check whether Ollama is already installed
- Check whether Claude Code is already installed
- Check available disk space
- Check whether any conflicting shell profile settings already exist

B) Install/configure
- Install Ollama if missing
- Ensure Ollama runs correctly on login or is easy to start
- Pull the four target models above
- If Docker is present and working, install/run Open WebUI with persistent storage
- If Docker is absent or broken, skip Open WebUI and document that clearly instead of getting stuck
- Configure Claude Code to target Ollama locally using the official Ollama Anthropic-compatible setup
- Prefer a deterministic manual config over fragile interactive-only steps, but use official launch/config helpers if they simplify things safely

C) Create a small local control surface in my home directory
Create a directory:
~/local-llm-lab

Inside it create:
- README.md
- scripts/start-ollama.sh
- scripts/stop-ollama.sh
- scripts/start-openwebui.sh
- scripts/stop-openwebui.sh
- scripts/test-models.sh
- scripts/benchmark-model.sh
- scripts/use-claude-local-qwen3-coder.sh
- scripts/use-claude-local-qwen3.sh
- scripts/use-claude-local-deepseek.sh
- scripts/use-claude-local-qwen25-72b.sh
- scripts/status.sh

Requirements for those scripts:
- They must be complete, runnable shell scripts
- Use bash with set -euo pipefail
- Be idempotent where sensible
- Print helpful status messages
- Avoid destructive behavior
- Detect and explain common failure modes
- Never assume paths without checking
- If environment variables are needed for Claude Code, set them in wrapper scripts rather than relying only on ad hoc shell state

D) Claude Code local wrappers
For each Claude wrapper script:
- Point Claude Code at Ollama’s Anthropic-compatible API
- Use the relevant local model
- Be easy to launch from terminal
- Avoid mutating my global shell config unless clearly justified
- If global shell config is updated, back it up first and keep changes minimal

E) Benchmarking and verification
Create a benchmark/test script that:
- verifies ollama is reachable
- lists installed models
- runs a short prompt against each target model
- records rough latency and/or tokens-per-second if easily available
- writes results to ~/local-llm-lab/benchmark-results.md

Also verify:
- qwen3:30b works
- deepseek-r1:32b works
- qwen2.5:72b at least loads and responds if memory allows
- qwen3-coder:30b works with Claude Code local backend

F) Documentation
In README.md include:
- what was installed
- how to start/stop everything
- how to chat locally
- how to use Claude Code with each local model
- which model to use for which purpose
- expected tradeoffs on a 48 GB Apple-silicon Mac
- troubleshooting notes
- how to add or remove models later

G) Safety / operational constraints
- Prefer official documentation and stable commands
- Do not leave half-configured junk behind
- Do not use experimental tools unless necessary
- If Docker/Open WebUI is problematic, degrade gracefully and finish the rest
- If qwen2.5:72b is too heavy to be comfortable, still document it as an optional heavy model and ensure the rest of the stack is excellent
- Show me command output for important verification steps
- At the end, give me:
  1. what succeeded
  2. what was skipped and why
  3. exact commands I should use day to day

Acceptance criteria:
- I can run a local chat model easily
- I can use Claude Code against a local Ollama model
- I have clear scripts for start/stop/status/testing
- The setup is documented and maintainable
- The solution is optimized for ergonomics, not just raw possibility

Important:
Do the work, do not just describe it.