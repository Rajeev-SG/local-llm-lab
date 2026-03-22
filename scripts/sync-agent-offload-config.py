#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "agent-offload.toml"


def load_config() -> dict:
    return tomllib.loads(CONFIG_PATH.read_text())


def parse_exported_env(env_path: Path) -> dict[str, str]:
    exports: dict[str, str] = {}
    export_re = re.compile(r"^\s*export\s+([A-Z0-9_]+)=(.*)\s*$")
    for line in env_path.read_text().splitlines():
        match = export_re.match(line)
        if not match:
            continue
        key, raw_value = match.groups()
        value = raw_value.strip()
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
        exports[key] = value
    return exports


def update_env_exports(path: Path, replacements: dict[str, str]) -> None:
    lines = path.read_text().splitlines()
    updated: list[str] = []
    keys_seen: set[str] = set()
    pattern = re.compile(r"^\s*export\s+([A-Z0-9_]+)=")

    for line in lines:
        match = pattern.match(line)
        if match and match.group(1) in replacements:
            key = match.group(1)
            updated.append(f'export {key}="{replacements[key]}"')
            keys_seen.add(key)
        else:
            updated.append(line)

    for key, value in replacements.items():
        if key not in keys_seen:
            updated.append(f'export {key}="{value}"')

    path.write_text("\n".join(updated) + "\n")


def ensure_agent_offload_codex(config_path: Path, command: str, args: list[str]) -> None:
    existing = config_path.read_text()
    block = (
        '\n[mcp_servers.agent_offload]\n'
        f'command = "{command}"\n'
        f'args = [{", ".join(json.dumps(arg) for arg in args)}]\n'
        'enabled = true\n'
    )
    if "[mcp_servers.agent_offload]" in existing:
        existing = re.sub(
            r"\n\[mcp_servers\.agent_offload\]\n(?:.+\n)+?(?=\n\[mcp_servers\.|\Z)",
            block,
            existing,
            flags=re.MULTILINE,
        )
    else:
        existing = existing.rstrip() + "\n" + block
    config_path.write_text(existing)


def ensure_mcp_server_json(path: Path, key: str, entry: dict) -> None:
    data = json.loads(path.read_text())
    container_key = "mcpServers"
    if container_key not in data:
        container_key = "mcp_servers"
    data.setdefault(container_key, {})
    data[container_key][key] = entry
    path.write_text(json.dumps(data, indent=2) + "\n")


def ensure_droid_models(path: Path, api_key: str, roles: dict[str, dict]) -> None:
    data = json.loads(path.read_text())
    models = data.setdefault("custom_models", [])
    desired = {
        "OR: Offload Worker (Grok 4.1 Fast)": roles["default_worker"]["model"],
        "OR: Long Context (Gemini 3 Flash Preview)": roles["long_context_escalator"]["model"],
        "OR: Mid-Cost Harder Worker (MiniMax M2.5)": roles["harder_mid_cost_worker"]["model"],
        "OR: Coding Specialist (GLM-5)": roles["coding_specialist"]["model"],
    }

    existing_by_name = {item.get("model_display_name"): item for item in models}
    for display_name, model in desired.items():
        entry = {
            "model_display_name": display_name,
            "model": model,
            "base_url": "https://openrouter.ai/api/v1",
            "api_key": api_key,
            "provider": "openai",
        }
        if display_name in existing_by_name:
            existing_by_name[display_name].update(entry)
        else:
            models.append(entry)

    data["custom_models"] = models
    path.write_text(json.dumps(data, indent=2) + "\n")


def main() -> int:
    cfg = load_config()
    env_path = Path(cfg["openrouter"]["env_file"])
    exports = parse_exported_env(env_path)
    api_key = exports["OPENROUTER_API_KEY"]

    server_command = "uv"
    server_args = [
        "run",
        "--with",
        "fastmcp",
        "python",
        str(ROOT / "broker" / "agent_offload.py"),
    ]

    mcp_stdio_entry = {
        "command": server_command,
        "args": server_args,
        "env": {},
    }
    mcp_stdio_entry_claude = {
        "type": "stdio",
        "command": server_command,
        "args": server_args,
        "env": {},
    }

    update_env_exports(
        env_path,
        {
            "OPENROUTER_MODEL_DEFAULT": cfg["roles"]["default_worker"]["model"],
            "OPENROUTER_MODEL_OPUS": cfg["roles"]["long_context_escalator"]["model"],
            "OPENROUTER_MODEL_SONNET": cfg["roles"]["harder_mid_cost_worker"]["model"],
            "OPENROUTER_MODEL_HAIKU": cfg["roles"]["default_worker"]["model"],
            "OPENROUTER_MODEL_SMALL_FAST": cfg["roles"]["default_worker"]["model"],
            "OPENROUTER_MODEL_SUBAGENT": cfg["roles"]["default_worker"]["model"],
            "ANTHROPIC_CUSTOM_MODEL_OPTION": cfg["roles"]["coding_specialist"]["model"],
            "ANTHROPIC_CUSTOM_MODEL_OPTION_NAME": "GLM-5 Coding Specialist",
            "ANTHROPIC_CUSTOM_MODEL_OPTION_DESCRIPTION": "OpenRouter custom model: z-ai/glm-5",
        },
    )

    cc_settings_path = Path("/Users/rajeev/.cc-mirror/cc-openrouter/config/settings.json")
    cc_settings = json.loads(cc_settings_path.read_text())
    cc_settings["model"] = cfg["roles"]["default_worker"]["model"]
    cc_settings["env"]["ANTHROPIC_DEFAULT_SONNET_MODEL"] = cfg["roles"]["harder_mid_cost_worker"]["model"]
    cc_settings["env"]["ANTHROPIC_DEFAULT_OPUS_MODEL"] = cfg["roles"]["long_context_escalator"]["model"]
    cc_settings["env"]["ANTHROPIC_DEFAULT_HAIKU_MODEL"] = cfg["roles"]["default_worker"]["model"]
    cc_settings["env"]["ANTHROPIC_MODEL"] = cfg["roles"]["default_worker"]["model"]
    cc_settings["env"]["ANTHROPIC_SMALL_FAST_MODEL"] = cfg["roles"]["default_worker"]["model"]
    cc_settings["env"]["CLAUDE_CODE_SUBAGENT_MODEL"] = cfg["roles"]["default_worker"]["model"]
    cc_settings_path.write_text(json.dumps(cc_settings, indent=2) + "\n")

    ensure_agent_offload_codex(Path("/Users/rajeev/.codex/config.toml"), server_command, server_args)
    ensure_mcp_server_json(Path("/Users/rajeev/.claude.json"), "agent_offload", mcp_stdio_entry_claude)
    ensure_mcp_server_json(Path("/Users/rajeev/.claude/settings.json"), "agent_offload", mcp_stdio_entry)
    ensure_mcp_server_json(Path("/Users/rajeev/.cc-mirror/cc-openrouter/config/.claude.json"), "agent_offload", mcp_stdio_entry_claude)
    ensure_mcp_server_json(Path("/Users/rajeev/.codeium/windsurf/mcp_config.json"), "agent_offload", mcp_stdio_entry)
    ensure_droid_models(Path("/Users/rajeev/.factory/config.json"), api_key, cfg["roles"])

    print("Synced shared agent offload broker into global configs.")
    print(f"Source of truth: {CONFIG_PATH}")
    print(f"Broker: {ROOT / 'broker' / 'agent_offload.py'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

