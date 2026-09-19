#!/usr/bin/env python3
"""Shared harness for the five-workflow smoke test.

Reuses the repo's existing conventions (OpenAI-compatible /v1/chat/completions,
output/benchmarks JSON artifacts, config/*.json model manifests). It adds only
what the workflow test needs: a server supervisor, a small tool-using agent loop,
and unified-memory sampling.
"""
from __future__ import annotations

import json
import os
import shutil
import signal
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def http_json(url: str, body: dict[str, Any] | None = None, timeout: float = 600) -> dict[str, Any]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="GET" if data is None else "POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex(("127.0.0.1", port)) != 0


def rss_mb(pid: int) -> float:
    """Resident set size of a process tree root, in MB (unified-memory proxy)."""
    try:
        out = subprocess.run(
            ["ps", "-o", "rss=", "-p", str(pid)], capture_output=True, text=True, check=False
        ).stdout.strip()
        return round(int(out) / 1024, 1) if out else 0.0
    except (ValueError, OSError):
        return 0.0


class Server:
    """Supervises one OpenAI-compatible inference server and samples its memory."""

    def __init__(self, name: str, command: list[str], port: int, log_path: Path,
                 env: dict | None = None, external_url: str | None = None,
                 external_pgrep: str | None = None):
        self.name = name
        self.command = command
        self.port = port
        self.log_path = log_path
        self.env = {**os.environ, **(env or {})}
        self.process: subprocess.Popen | None = None
        self.external_url = external_url
        self.external_pgrep = external_pgrep
        self.peak_mb = 0.0
        self.samples: list[float] = []
        self.startup_seconds: float | None = None

    @property
    def base_url(self) -> str:
        if self.external_url:
            return self.external_url
        return f"http://127.0.0.1:{self.port}"

    def sample(self) -> None:
        pid = None
        if self.process and self.process.poll() is None:
            pid = self.process.pid
        elif self.external_pgrep:
            try:
                out = subprocess.run(["pgrep", "-f", self.external_pgrep],
                                     capture_output=True, text=True, check=False).stdout.split()
                pid = int(out[0]) if out else None
            except (ValueError, IndexError):
                pid = None
        if pid:
            value = rss_mb(pid)
            if value:
                self.samples.append(value)
                self.peak_mb = max(self.peak_mb, value)

    def start(self, timeout: float = 600) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.log_path.open("w")
        started = time.perf_counter()
        self.process = subprocess.Popen(
            self.command, stdout=handle, stderr=subprocess.STDOUT, env=self.env,
            preexec_fn=os.setsid,
        )
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.process.poll() is not None:
                tail = self.log_path.read_text(errors="replace")[-2000:]
                raise RuntimeError(f"{self.name} exited early (rc={self.process.returncode}):\n{tail}")
            try:
                http_json(f"{self.base_url}/v1/models", timeout=3)
                self.startup_seconds = round(time.perf_counter() - started, 1)
                return
            except Exception:
                self.sample()
                time.sleep(1.0)
        tail = self.log_path.read_text(errors="replace")[-2000:]
        raise TimeoutError(f"{self.name} did not become ready in {timeout}s:\n{tail}")

    def stop(self) -> None:
        if self.process and self.process.poll() is None:
            try:
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                self.process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass
        self.process = None

    def chat(self, messages: list[dict], tools: list[dict] | None = None,
             max_tokens: int = 1024, temperature: float = 0.0, timeout: float = 600,
             extra: dict | None = None) -> dict:
        body: dict[str, Any] = {
            "model": "local",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        if tools:
            body["tools"] = tools
        if extra:
            body.update({k: v for k, v in extra.items() if v is not None})
        return http_json(f"{self.base_url}/v1/chat/completions", body=body, timeout=timeout)


# ---------------------------------------------------------------------------
# Tool-using agent loop
# ---------------------------------------------------------------------------

AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file in the working directory.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Overwrite a file in the working directory with new content.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Run a shell command in the working directory and see its output.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finish",
            "description": "Declare the task complete.",
            "parameters": {"type": "object", "properties": {"summary": {"type": "string"}}},
        },
    },
]


def _extract_tool_call(message: dict):
    """Return (name, args, call_id) from a native tool_call or a fallback JSON block."""
    calls = message.get("tool_calls") or []
    for call in calls:
        fn = call.get("function") or {}
        name = fn.get("name")
        if not name:
            continue
        raw = fn.get("arguments")
        try:
            args = json.loads(raw) if isinstance(raw, str) else (raw or {})
        except json.JSONDecodeError:
            args = {}
        return name, args, call.get("id")
    # Fallback: parse a JSON object from the text content.
    text = message.get("content") or ""
    if isinstance(text, list):
        text = " ".join(part.get("text", "") for part in text if isinstance(part, dict))
    for opener, closer in (("{", "}"),):
        start, end = text.find(opener), text.rfind(closer)
        if start != -1 and end > start:
            try:
                candidate = json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue
            if isinstance(candidate, dict) and candidate.get("tool"):
                return candidate["tool"], candidate.get("args") or candidate.get("arguments") or {}, None
    return None


def run_agent(
    server: Server,
    workdir: Path,
    instruction: str,
    check_command: str,
    max_turns: int = 12,
) -> dict[str, Any]:
    """Run a bounded tool-using loop against `workdir` and score with `check_command`.

    Returns success (objective test result), human rescues, tool failures, turns,
    wall-clock seconds and the full transcript.
    """
    system = (
        "You are a coding agent working in a directory. Fix the task by editing files. "
        "Use the tools. Do not explain; act. When the tests pass, call finish.\n"
        "Always run the test command after editing to confirm your change."
    )
    messages: list[dict] = [
        {"role": "system", "content": system},
        {"role": "user", "content": instruction},
    ]
    tool_failures = 0
    turns = 0
    started = time.perf_counter()
    transcript: list[dict] = []

    for _ in range(max_turns):
        turns += 1
        try:
            payload = server.chat(messages, tools=AGENT_TOOLS, max_tokens=1024)
            server.sample()
        except Exception as exc:  # transport failure counts as a tool-level failure
            tool_failures += 1
            transcript.append({"role": "error", "content": str(exc)})
            break

        choice = (payload.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        extracted = _extract_tool_call(message)
        name, args, call_id = extracted if extracted else (None, {}, None)
        assistant_text = message.get("content")
        if isinstance(assistant_text, list):
            assistant_text = " ".join(p.get("text", "") for p in assistant_text if isinstance(p, dict))
        transcript.append({"role": "assistant", "content": assistant_text, "tool": name, "args": args})

        if name is None:
            tool_failures += 1
            messages.append({"role": "assistant", "content": assistant_text or ""})
            messages.append({
                "role": "user",
                "content": 'No tool call detected. Reply with one JSON tool call, e.g. '
                           '{"tool":"run_command","args":{"command":"python3 run_checks.py"}}.',
            })
            continue

        # Echo the assistant turn preserving native tool_calls so the model keeps context.
        if message.get("tool_calls"):
            messages.append({"role": "assistant", "content": assistant_text or "", "tool_calls": message["tool_calls"]})
        else:
            messages.append({"role": "assistant", "content": assistant_text or json.dumps({"tool": name})})
        try:
            if name == "finish":
                break
            result = _apply_tool(workdir, name, args)
        except Exception as exc:
            tool_failures += 1
            result = f"ERROR: {exc}"
        transcript.append({"role": "tool", "name": name, "result": result[:2000]})
        tool_msg = {"role": "tool", "content": result[:4000]}
        if call_id:
            tool_msg["tool_call_id"] = call_id
        messages.append(tool_msg)

    # Objective acceptance: run the check command.
    check = subprocess.run(
        ["bash", "-lc", check_command], cwd=str(workdir),
        capture_output=True, text=True, timeout=120, check=False,
    )
    elapsed = round(time.perf_counter() - started, 1)
    return {
        "success": check.returncode == 0,
        "check_command": check_command,
        "check_returncode": check.returncode,
        "check_output": (check.stdout + check.stderr)[-4000:],
        "turns": turns,
        "tool_failures": tool_failures,
        "wall_seconds": elapsed,
        "transcript": transcript,
    }


def _apply_tool(workdir: Path, name: str, args: dict) -> str:
    if name == "read_file":
        path = workdir / args["path"]
        return path.read_text(errors="replace")[:6000]
    if name == "write_file":
        path = workdir / args["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(args.get("content", ""), encoding="utf-8")
        return f"wrote {path.name} ({len(args.get('content',''))} bytes)"
    if name == "run_command":
        proc = subprocess.run(
            ["bash", "-lc", args["command"]], cwd=str(workdir),
            capture_output=True, text=True, timeout=120, check=False,
        )
        return (proc.stdout + proc.stderr)[-4000:] or f"(no output, rc={proc.returncode})"
    raise ValueError(f"unknown tool: {name}")


def fresh_dir(src: Path, dst: Path) -> Path:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    return dst
