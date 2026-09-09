# Secure Open WebUI Setup

This repository uses `compose.openwebui.yaml` with digest-pinned Open WebUI 0.11.1 and Open Terminal images. The named `open-webui-data` and `open-terminal-data` volumes survive recreation; setup never uses `down -v`.

## Setup

1. Copy `config/openwebui.env.example` to `.env.local` if you want overrides. The setup script creates stable `WEBUI_SECRET_KEY` and `OPEN_TERMINAL_API_KEY` values in that ignored, mode-0600 file when absent. Set `OPENAI_API_KEYS` only in the environment that runs Docker. `OPENROUTER_API_KEY` may be used by the bridge, but is never written by repository code.
2. Start Ollama: `./scripts/start-ollama.sh`.
3. Run `./scripts/setup-openwebui.sh`.
4. Run `./scripts/doctor.sh` and open the URL printed by the setup script.

The OpenRouter endpoint is OpenAI-compatible at `https://openrouter.ai/api/v1`. Open WebUI will show local Ollama models and cloud models only when the corresponding credential is present. Do not put keys in Compose, scripts, screenshots, browser state, or Git. A stable `WEBUI_SECRET_KEY` is mandatory because Open WebUI encrypts persisted OAuth/MCP connection data with it.

## Approved capability boundary

`python3 scripts/bridge.py discover` lists the fixed host API operations, approved runbooks, and loopback MCP endpoints. The host bridge has no arbitrary shell operation, no Keychain access, no token-cache access, no browser-profile access, and no path argument.

Open Terminal provides shell, file, and common CLI tools inside its own resource-limited container. It has no Docker socket and no host home mount. Only the durable Codex docs tree and this repository's Open WebUI runbooks are mounted read-only. Connect it in Admin Settings → Integrations with URL `http://open-terminal:8000`; keep its generated API key server-side. Tool outputs or runbook excerpts used with an OpenRouter model are sent to that external model provider as chat context.

The published Open Terminal image currently cannot enforce
`OPEN_TERMINAL_ALLOWED_DOMAINS` reliably under Docker Desktop, so this setup
does not enable that broken firewall switch. The terminal has outbound network
access from its isolated container, but still has no Docker socket, host home,
or writable runbook mount. Re-enable an egress allowlist only after the upstream
iptables/capability issue is fixed and verified against the pinned image.

Native MCP connections are limited to audited Streamable HTTP servers. Do not proxy raw Agent Mail, Keychain-backed credential helpers, browser profiles, generic filesystem MCP, or arbitrary stdio servers into Open WebUI.

The approved connection inventory is `config/bridge-allowlist.json`. From inside the Open WebUI container, host ToolHive endpoints use `host.docker.internal`, not `localhost`. The default set is Fetch, Context7, isolated Playwright, OpenAI Developer Docs, and draw.io. Authenticated or write-capable MCPs such as Linear, analytics, Coolify, Google Workspace, and Agent Mail stay out of the ambient model toolset; add one only for a named workflow with the narrowest access grants.

## Proof

For deterministic browser support, use an isolated Playwright session:

```bash
playwright-cli -s=openwebui-proof open http://localhost:3001
playwright-cli -s=openwebui-proof snapshot
playwright-cli -s=openwebui-proof screenshot
```

Complete one chat in the UI and capture a fresh screenshot after the response. Do not use a real logged-in browser profile for this proof.

## Restore models

Ollama model blobs live outside this repository and are not deleted by Open WebUI recreation. Verify them with `ollama list`, then run `./scripts/restore-ollama-models.sh` to pull every Ollama model named in `output/inventory/current-models.json`. Run `./scripts/test-models.sh` afterward. Do not silently substitute a different model.
