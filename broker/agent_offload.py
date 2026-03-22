#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import textwrap
import tomllib
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from fastmcp import FastMCP


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = Path(os.environ.get("AGENT_OFFLOAD_CONFIG", ROOT / "config" / "agent-offload.toml"))
CACHE_DIR = ROOT / "tmp" / "agent-offload-cache"
USAGE_LOG = ROOT / "output" / "agent-offload" / "usage.jsonl"

CODE_TASK_KINDS = {
    "api_surface",
    "code_contracts",
    "code_review",
    "diff_summary",
    "extract_contracts",
}

HARD_TASK_KINDS = {
    "architecture_compare",
    "cross_doc_synthesis",
    "decision_memo",
    "hard_synthesis",
    "root_cause_prep",
}


@dataclass
class RoleConfig:
    name: str
    label: str
    model: str
    temperature: float
    max_output_tokens: int
    price_prompt_per_million: float
    price_completion_per_million: float
    reasoning: str
    description: str
    provider: dict[str, Any]


@dataclass
class BrokerConfig:
    openrouter: dict[str, Any]
    budgets: dict[str, Any]
    thresholds: dict[str, Any]
    routing: dict[str, Any]
    roles: dict[str, RoleConfig]


def load_shell_exports(env_file: Path) -> dict[str, str]:
    exports: dict[str, str] = {}
    if not env_file.exists():
        return exports

    export_re = re.compile(r"^\s*export\s+([A-Z0-9_]+)=(.*)\s*$")
    for line in env_file.read_text().splitlines():
        match = export_re.match(line)
        if not match:
            continue
        key, raw_value = match.groups()
        value = raw_value.strip()
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
        exports[key] = value
    return exports


def load_config() -> BrokerConfig:
    data = tomllib.loads(CONFIG_PATH.read_text())
    roles = {
        name: RoleConfig(
            name=name,
            label=role_data["label"],
            model=role_data["model"],
            temperature=float(role_data["temperature"]),
            max_output_tokens=int(role_data["max_output_tokens"]),
            price_prompt_per_million=float(role_data["price_prompt_per_million"]),
            price_completion_per_million=float(role_data["price_completion_per_million"]),
            reasoning=str(role_data.get("reasoning", "off")),
            description=role_data["description"],
            provider=dict(role_data.get("provider", {})),
        )
        for name, role_data in data["roles"].items()
    }
    return BrokerConfig(
        openrouter=dict(data["openrouter"]),
        budgets=dict(data["budgets"]),
        thresholds=dict(data["thresholds"]),
        routing=dict(data["routing"]),
        roles=roles,
    )


def load_openrouter_api_key(config: BrokerConfig) -> str:
    direct = os.environ.get("OPENROUTER_API_KEY")
    if direct:
        return direct

    env_file = Path(config.openrouter["env_file"])
    exports = load_shell_exports(env_file)
    api_key = exports.get("OPENROUTER_API_KEY")
    if api_key:
        return api_key

    raise RuntimeError(f"OPENROUTER_API_KEY not found in env or {env_file}")


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def estimate_cost(role: RoleConfig, prompt_tokens: int, completion_tokens: int) -> float:
    prompt_cost = role.price_prompt_per_million * (prompt_tokens / 1_000_000)
    completion_cost = role.price_completion_per_million * (completion_tokens / 1_000_000)
    return round(prompt_cost + completion_cost, 6)


def route_role(
    config: BrokerConfig,
    task_kind: str,
    input_text: str,
    preferred_role: str,
) -> tuple[RoleConfig, dict[str, Any]]:
    input_chars = len(input_text)
    threshold = config.thresholds
    chosen_role = preferred_role.strip() if preferred_role else "auto"

    if chosen_role and chosen_role != "auto":
        if chosen_role not in config.roles:
            raise ValueError(f"Unknown role: {chosen_role}")
        role = config.roles[chosen_role]
        reason = "explicit role override"
    elif task_kind in CODE_TASK_KINDS:
        role = config.roles[config.routing["coding_role"]]
        reason = "code-focused task"
    elif input_chars >= int(threshold["long_context_min_chars"]):
        role = config.roles[config.routing["long_context_role"]]
        reason = "large context input"
    elif task_kind in HARD_TASK_KINDS or input_chars >= int(threshold["hard_task_min_chars"]):
        role = config.roles[config.routing["hard_task_role"]]
        reason = "hard synthesis task"
    else:
        role = config.roles[config.routing["default_role"]]
        reason = "default worker"

    meta = {
        "input_chars": input_chars,
        "estimated_input_tokens": estimate_tokens(input_text),
        "route_reason": reason,
        "warn_large_input": input_chars >= int(threshold["large_input_warn_chars"]),
        "refuse_input": input_chars > int(threshold["max_input_chars"]),
    }
    return role, meta


def build_messages(task_kind: str, goal: str, input_text: str, output_format: str) -> list[dict[str, str]]:
    system_prompt = textwrap.dedent(
        """
        You are a bounded context-offload worker helping a stronger coding agent.
        Your job is to reduce token load while preserving high-signal facts and next actions.
        Never ask follow-up questions.
        Never include preambles or markdown fences.
        Prefer compact output.
        Return strict JSON with these keys:
        summary: string
        key_points: string[]
        risks: string[]
        unknowns: string[]
        next_step: string
        """
    ).strip()

    user_prompt = {
        "task_kind": task_kind,
        "goal": goal,
        "output_format": output_format,
        "input_text": input_text,
    }
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(user_prompt, ensure_ascii=True)},
    ]


def cache_key(role: RoleConfig, task_kind: str, goal: str, input_text: str, output_format: str) -> str:
    payload = json.dumps(
        {
            "model": role.model,
            "task_kind": task_kind,
            "goal": goal,
            "input_text": input_text,
            "output_format": output_format,
        },
        sort_keys=True,
        ensure_ascii=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def read_cache(key: str) -> dict[str, Any] | None:
    cache_path = CACHE_DIR / f"{key}.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text())
    return None


def write_cache(key: str, payload: dict[str, Any]) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (CACHE_DIR / f"{key}.json").write_text(json.dumps(payload, indent=2))


def log_usage(entry: dict[str, Any]) -> None:
    USAGE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with USAGE_LOG.open("a") as handle:
        handle.write(json.dumps(entry, ensure_ascii=True) + "\n")


def normalize_json_output(raw_text: str) -> dict[str, Any]:
    raw_text = raw_text.strip()
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Model did not return valid JSON: {exc}") from exc

    if isinstance(payload, list):
        string_items = [item for item in payload if isinstance(item, str)]
        dict_items = [item for item in payload if isinstance(item, dict)]
        if dict_items and isinstance(dict_items[0], dict):
            payload = dict_items[0]
        else:
            payload = {
                "summary": " ".join(string_items[:2]).strip(),
                "key_points": string_items,
                "risks": [],
                "unknowns": [],
                "next_step": "",
            }
    elif not isinstance(payload, dict):
        payload = {
            "summary": str(payload),
            "key_points": [],
            "risks": [],
            "unknowns": [],
            "next_step": "",
        }

    for key in ("summary", "key_points", "risks", "unknowns", "next_step"):
        payload.setdefault(key, [] if key in {"key_points", "risks", "unknowns"} else "")
    return payload


def post_openrouter(config: BrokerConfig, role: RoleConfig, messages: list[dict[str, str]]) -> dict[str, Any]:
    api_key = load_openrouter_api_key(config)
    role_prompt_price = role.price_prompt_per_million
    role_completion_price = role.price_completion_per_million

    payload: dict[str, Any] = {
        "model": role.model,
        "messages": messages,
        "temperature": role.temperature,
        "max_tokens": role.max_output_tokens,
        "response_format": {"type": "json_object"},
        "provider": {
            **role.provider,
            "max_price": {
                "prompt": round(role_prompt_price * 1.25, 3),
                "completion": round(role_completion_price * 1.25, 3),
            },
        },
    }

    if role.reasoning == "off":
        payload["reasoning"] = {"enabled": False}
    elif role.reasoning == "minimal":
        payload["reasoning"] = {"max_tokens": 256, "exclude": True}

    request = urllib.request.Request(
        config.openrouter["api_base"],
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": config.openrouter.get("site_url", "https://local-llm-lab.local"),
            "X-Title": config.openrouter.get("app_name", "local-llm-lab-agent-offload"),
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenRouter HTTP {exc.code}: {details}") from exc


def run_offload_task(
    goal: str,
    input_text: str,
    task_kind: str = "summarize_tool_output",
    preferred_role: str = "auto",
    output_format: str = "json",
    use_cache: bool = True,
) -> dict[str, Any]:
    config = load_config()
    role, route_meta = route_role(config, task_kind, input_text, preferred_role)
    if route_meta["refuse_input"]:
        raise RuntimeError(
            f"Input too large for safe offload ({route_meta['input_chars']} chars > {config.thresholds['max_input_chars']})."
        )

    messages = build_messages(task_kind=task_kind, goal=goal, input_text=input_text, output_format=output_format)
    key = cache_key(role, task_kind, goal, input_text, output_format)
    if use_cache:
        cached = read_cache(key)
        if cached:
            cached["cached"] = True
            return cached

    prompt_tokens = estimate_tokens(json.dumps(messages, ensure_ascii=True))
    estimated_cost = estimate_cost(role, prompt_tokens, role.max_output_tokens)
    if estimated_cost > float(config.budgets["per_call_soft_limit_usd"]):
        raise RuntimeError(
            f"Estimated offload cost ${estimated_cost:.4f} exceeds soft limit ${config.budgets['per_call_soft_limit_usd']:.2f}."
        )

    response = post_openrouter(config, role, messages)
    content = response["choices"][0]["message"]["content"]
    if isinstance(content, list):
        content = "".join(part.get("text", "") for part in content if isinstance(part, dict))

    parsed = normalize_json_output(content)
    usage = response.get("usage", {})
    prompt_used = int(usage.get("prompt_tokens", prompt_tokens))
    completion_used = int(usage.get("completion_tokens", role.max_output_tokens))
    actual_cost = estimate_cost(role, prompt_used, completion_used)

    result = {
        "role": role.name,
        "role_label": role.label,
        "model": role.model,
        "task_kind": task_kind,
        "goal": goal,
        "route_reason": route_meta["route_reason"],
        "cached": False,
        "input_chars": route_meta["input_chars"],
        "estimated_input_tokens": route_meta["estimated_input_tokens"],
        "usage": {
            "prompt_tokens": prompt_used,
            "completion_tokens": completion_used,
            "estimated_cost_usd": actual_cost,
        },
        "result": parsed,
    }

    write_cache(key, result)
    log_usage(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "role": role.name,
            "model": role.model,
            "task_kind": task_kind,
            "input_chars": route_meta["input_chars"],
            "prompt_tokens": prompt_used,
            "completion_tokens": completion_used,
            "estimated_cost_usd": actual_cost,
        }
    )
    return result


def estimate_offload(
    goal: str,
    input_text: str,
    task_kind: str = "summarize_tool_output",
    preferred_role: str = "auto",
) -> dict[str, Any]:
    config = load_config()
    role, route_meta = route_role(config, task_kind, input_text, preferred_role)
    prompt_tokens = estimate_tokens(input_text) + estimate_tokens(goal) + 300
    completion_tokens = role.max_output_tokens
    return {
        "role": role.name,
        "role_label": role.label,
        "model": role.model,
        "task_kind": task_kind,
        "route_reason": route_meta["route_reason"],
        "input_chars": route_meta["input_chars"],
        "estimated_input_tokens": prompt_tokens,
        "estimated_output_tokens": completion_tokens,
        "estimated_cost_usd": estimate_cost(role, prompt_tokens, completion_tokens),
        "warn_large_input": route_meta["warn_large_input"],
    }


def audit_codex_sessions(limit: int = 5, sessions_root: str = "/Users/rajeev/.codex/sessions") -> dict[str, Any]:
    root = Path(sessions_root)
    files = sorted(root.rglob("rollout-*.jsonl"), key=lambda path: path.stat().st_mtime, reverse=True)[:limit]
    session_rows: list[dict[str, Any]] = []

    for path in files:
        stats = {
            "path": str(path),
            "tool_output_chars": 0,
            "assistant_chars": 0,
            "agent_update_chars": 0,
            "user_chars": 0,
            "reasoning_chars": 0,
            "instruction_chars": 0,
        }
        with path.open() as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                entry_type = entry.get("type")
                payload = entry.get("payload", {})
                if entry_type == "session_meta":
                    stats["instruction_chars"] += len(payload.get("base_instructions", {}).get("text", ""))
                elif entry_type == "event_msg":
                    msg_type = payload.get("type")
                    if msg_type == "user_message":
                        stats["user_chars"] += len(payload.get("message", ""))
                    elif msg_type == "agent_message":
                        stats["agent_update_chars"] += len(payload.get("message", ""))
                elif entry_type == "response_item":
                    payload_type = payload.get("type")
                    if payload_type == "function_call_output":
                        stats["tool_output_chars"] += len(payload.get("output", ""))
                    elif payload_type == "message":
                        text = ""
                        content = payload.get("content", [])
                        if content and isinstance(content[0], dict):
                            text = content[0].get("text", "")
                        stats["assistant_chars"] += len(text)
                    elif payload_type == "reasoning":
                        stats["reasoning_chars"] += len(payload.get("encrypted_content", "") or "")
        total_chars = sum(value for key, value in stats.items() if key.endswith("_chars"))
        stats["tool_output_share"] = round(stats["tool_output_chars"] / total_chars, 3) if total_chars else 0
        session_rows.append(stats)

    totals = {
        "sessions_analyzed": len(session_rows),
        "tool_output_chars": sum(row["tool_output_chars"] for row in session_rows),
        "reasoning_chars": sum(row["reasoning_chars"] for row in session_rows),
        "user_chars": sum(row["user_chars"] for row in session_rows),
        "instruction_chars": sum(row["instruction_chars"] for row in session_rows),
    }
    totals["estimated_main_agent_tokens_saved_if_tool_output_cut_85pct"] = int((totals["tool_output_chars"] * 0.85) / 4)
    return {"totals": totals, "sessions": session_rows}


def compare_cost_scenario(raw_chars: int, compressed_chars: int, main_model_prompt_per_million: float = 1.25) -> dict[str, Any]:
    raw_tokens = estimate_tokens("x" * raw_chars)
    compressed_tokens = estimate_tokens("x" * compressed_chars)
    delta_tokens = max(0, raw_tokens - compressed_tokens)
    main_model_savings = round(main_model_prompt_per_million * (delta_tokens / 1_000_000), 6)
    return {
        "raw_chars": raw_chars,
        "compressed_chars": compressed_chars,
        "raw_tokens_estimate": raw_tokens,
        "compressed_tokens_estimate": compressed_tokens,
        "delta_tokens_estimate": delta_tokens,
        "prompt_cost_saved_at_main_model_usd": main_model_savings,
    }


mcp = FastMCP("agent-offload")


@mcp.tool
def offload_summarize(
    goal: str,
    input_text: str,
    task_kind: str = "summarize_tool_output",
    preferred_role: str = "auto",
    output_format: str = "json",
    use_cache: bool = True,
) -> dict[str, Any]:
    """Compress large text into a compact structured summary using the shared OpenRouter broker."""
    return run_offload_task(
        goal=goal,
        input_text=input_text,
        task_kind=task_kind,
        preferred_role=preferred_role,
        output_format=output_format,
        use_cache=use_cache,
    )


@mcp.tool
def estimate_offload_route(
    goal: str,
    input_text: str,
    task_kind: str = "summarize_tool_output",
    preferred_role: str = "auto",
) -> dict[str, Any]:
    """Estimate which role/model the broker will use and the rough cost before making a paid call."""
    return estimate_offload(goal=goal, input_text=input_text, task_kind=task_kind, preferred_role=preferred_role)


@mcp.tool
def codex_efficiency_audit(limit: int = 5) -> dict[str, Any]:
    """Inspect recent Codex sessions and quantify where transcript bulk is coming from."""
    return audit_codex_sessions(limit=limit)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Shared OpenRouter offload broker")
    subparsers = parser.add_subparsers(dest="command")

    estimate_parser = subparsers.add_parser("estimate", help="Estimate route and cost")
    estimate_parser.add_argument("--goal", required=True)
    estimate_parser.add_argument("--task-kind", default="summarize_tool_output")
    estimate_parser.add_argument("--preferred-role", default="auto")
    estimate_parser.add_argument("--input-file", required=True)

    run_parser = subparsers.add_parser("run-task", help="Run a paid offload task")
    run_parser.add_argument("--goal", required=True)
    run_parser.add_argument("--task-kind", default="summarize_tool_output")
    run_parser.add_argument("--preferred-role", default="auto")
    run_parser.add_argument("--output-format", default="json")
    run_parser.add_argument("--input-file", required=True)
    run_parser.add_argument("--no-cache", action="store_true")

    subparsers.add_parser("audit-codex", help="Summarize recent Codex transcript bloat")

    compare_parser = subparsers.add_parser("compare-scenario", help="Compare raw vs compressed prompt cost")
    compare_parser.add_argument("--raw-chars", type=int, required=True)
    compare_parser.add_argument("--compressed-chars", type=int, required=True)
    compare_parser.add_argument("--main-model-prompt-per-million", type=float, default=1.25)

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        mcp.run()
        return 0

    args = parse_args(argv)
    if args.command == "estimate":
        input_text = Path(args.input_file).read_text()
        print(
            json.dumps(
                estimate_offload(
                    goal=args.goal,
                    input_text=input_text,
                    task_kind=args.task_kind,
                    preferred_role=args.preferred_role,
                ),
                indent=2,
            )
        )
        return 0
    if args.command == "run-task":
        input_text = Path(args.input_file).read_text()
        print(
            json.dumps(
                run_offload_task(
                    goal=args.goal,
                    input_text=input_text,
                    task_kind=args.task_kind,
                    preferred_role=args.preferred_role,
                    output_format=args.output_format,
                    use_cache=not args.no_cache,
                ),
                indent=2,
            )
        )
        return 0
    if args.command == "audit-codex":
        print(json.dumps(audit_codex_sessions(), indent=2))
        return 0
    if args.command == "compare-scenario":
        print(
            json.dumps(
                compare_cost_scenario(
                    raw_chars=args.raw_chars,
                    compressed_chars=args.compressed_chars,
                    main_model_prompt_per_million=args.main_model_prompt_per_million,
                ),
                indent=2,
            )
        )
        return 0

    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
