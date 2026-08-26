#!/usr/bin/env python3
"""Small fixed-operation bridge. It is intentionally not a shell or file browser."""
from __future__ import annotations
import argparse, json, os, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWLIST = ROOT / "config" / "bridge-allowlist.json"
RUNBOOKS = {"docs/openwebui-secure-setup.md", "docs/openwebui-rollback.md"}

def request(url: str, payload: dict | None = None, headers: dict | None = None):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", **(headers or {})})
    with urllib.request.urlopen(req, timeout=120) as response:
        return json.load(response)

def main() -> int:
    parser = argparse.ArgumentParser(description="Allowlisted local LLM bridge")
    parser.add_argument("operation", choices=["discover", "local.models", "local.complete", "cloud.models", "cloud.complete", "runbook.list"])
    parser.add_argument("--model")
    parser.add_argument("--prompt")
    args = parser.parse_args()
    allow = json.loads(ALLOWLIST.read_text())
    if args.operation == "discover":
        print(json.dumps({"operations": allow["operations"], "mcp_servers": allow["mcp_servers"]}, indent=2)); return 0
    if args.operation == "runbook.list":
        print(json.dumps(sorted(RUNBOOKS))); return 0
    if args.operation == "local.models":
        print(json.dumps(request(os.environ.get("OLLAMA_HOST", "http://localhost:11434") + "/api/tags"))); return 0
    if args.operation.startswith("cloud.") and not os.environ.get("OPENROUTER_API_KEY"):
        print("OPENROUTER_API_KEY is required for cloud operations", file=sys.stderr); return 2
    if args.operation in {"local.complete", "cloud.complete"} and (not args.model or args.prompt is None):
        print("--model and --prompt are required", file=sys.stderr); return 2
    if args.operation == "cloud.models":
        result = request("https://openrouter.ai/api/v1/models", headers={"Authorization": "Bearer " + os.environ["OPENROUTER_API_KEY"]})
        print(json.dumps(result)); return 0
    if args.operation == "local.complete":
        url = os.environ.get("OLLAMA_HOST", "http://localhost:11434") + "/api/chat"
        print(json.dumps(request(url, {"model": args.model, "messages": [{"role": "user", "content": args.prompt}], "stream": False}))); return 0
    url = "https://openrouter.ai/api/v1/chat/completions"
    result = request(url, {"model": args.model, "messages": [{"role": "user", "content": args.prompt}]}, {"Authorization": "Bearer " + os.environ["OPENROUTER_API_KEY"]})
    print(json.dumps(result)); return 0

if __name__ == "__main__":
    raise SystemExit(main())
