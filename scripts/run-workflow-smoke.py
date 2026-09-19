#!/usr/bin/env python3
"""Five-workflow smoke test for a local model (issue #18).

Runs the five real workflow cases from the issue against an OpenAI-compatible
server and writes a machine-readable result under output/benchmarks/, matching the
existing artifact conventions. Extends the existing harness; no new framework.

    python3 scripts/run-workflow-smoke.py --model <slug> --base-url http://127.0.0.1:8091
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import workflow_harness as H  # noqa: E402

ROOT = H.ROOT
FIXTURES = ROOT / "fixtures"
WORKDIR = ROOT / "output" / "workflow-smoke" / "work"
OUT_DIR = ROOT / "output" / "benchmarks"


def _serve_browser_fixture() -> tuple[subprocess.Popen, str]:
    port = 8123
    proc = subprocess.Popen(
        [sys.executable, str(FIXTURES / "browser" / "serve.py"), str(port)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}"
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            H.http_json(f"{url}/health", timeout=2)
            break
        except Exception:
            try:
                import urllib.request
                urllib.request.urlopen(url, timeout=2)
                break
            except Exception:
                time.sleep(0.5)
    return proc, url


BROWSER_TOOLS = [
    {"type": "function", "function": {"name": "browser_goto", "description": "Navigate to a URL.",
        "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}}},
    {"type": "function", "function": {"name": "browser_fill", "description": "Type text into an input by CSS selector.",
        "parameters": {"type": "object", "properties": {"selector": {"type": "string"}, "text": {"type": "string"}}, "required": ["selector", "text"]}}},
    {"type": "function", "function": {"name": "browser_click", "description": "Click an element by CSS selector.",
        "parameters": {"type": "object", "properties": {"selector": {"type": "string"}}, "required": ["selector"]}}},
    {"type": "function", "function": {"name": "browser_read_text", "description": "Read the visible text of an element by CSS selector.",
        "parameters": {"type": "object", "properties": {"selector": {"type": "string"}}, "required": ["selector"]}}},
    {"type": "function", "function": {"name": "finish", "description": "Declare the browser task done.",
        "parameters": {"type": "object", "properties": {"summary": {"type": "string"}}}}},
]


def run_browser_task(server: "H.Server", url: str) -> dict:
    from playwright.sync_api import sync_playwright

    instruction = (
        f"Open {url} in the browser. Add three todos: 'alpha', 'beta', 'gamma'. "
        "Use browser_fill on #new-todo and browser_click on #add for each. Then read #count "
        "to confirm it shows 3, and call finish."
    )
    messages = [
        {"role": "system", "content": "You drive a browser with the provided tools. Act, do not explain."},
        {"role": "user", "content": instruction},
    ]
    tool_failures = 0
    turns = 0
    transcript = []
    started = time.perf_counter()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            for _ in range(15):
                turns += 1
                payload = server.chat(messages, tools=BROWSER_TOOLS, max_tokens=512)
                server.sample()
                choice = (payload.get("choices") or [{}])[0]
                message = choice.get("message") or {}
                extracted = H._extract_tool_call(message)
                name, args, call_id = extracted if extracted else (None, {}, None)
                transcript.append({"role": "assistant", "tool": name, "args": args,
                                   "content": message.get("content")})
                if name is None:
                    tool_failures += 1
                    messages.append({"role": "user",
                                     "content": 'Reply with one JSON tool call: {"tool":"browser_goto","args":{"url":"..."}}'})
                    continue
                if name == "finish":
                    break
                try:
                    if name == "browser_goto":
                        page.goto(args["url"]); result = f"at {page.url}"
                    elif name == "browser_fill":
                        page.fill(args["selector"], args["text"]); result = "filled"
                    elif name == "browser_click":
                        page.click(args["selector"]); result = "clicked"
                    elif name == "browser_read_text":
                        result = page.inner_text(args["selector"])
                    else:
                        raise ValueError(f"unknown tool {name}")
                except Exception as exc:
                    tool_failures += 1
                    result = f"ERROR: {exc}"
                # Preserve native tool_calls in the assistant turn.
                if message.get("tool_calls"):
                    messages.append({"role": "assistant", "content": message.get("content") or "",
                                     "tool_calls": message["tool_calls"]})
                else:
                    messages.append({"role": "assistant", "content": json.dumps({"tool": name})})
                tool_msg = {"role": "tool", "content": str(result)[:2000]}
                if call_id:
                    tool_msg["tool_call_id"] = call_id
                messages.append(tool_msg)

            count = page.inner_text("#count") if page.locator("#count").count() else ""
            items = page.eval_on_selector_all("#list li", "els => els.map(e => e.textContent)")
        finally:
            browser.close()

    success = str(count).strip() == "3" and sorted(items) == ["alpha", "beta", "gamma"]
    return {
        "success": success,
        "expected": {"count": "3", "items": ["alpha", "beta", "gamma"]},
        "observed": {"count": count, "items": items},
        "turns": turns,
        "tool_failures": tool_failures,
        "wall_seconds": round(time.perf_counter() - started, 1),
        "transcript": transcript,
    }


def run_text_task(server: "H.Server", prompt: str, max_tokens: int = 1500,
                  thinking_budget: int | None = None) -> dict:
    started = time.perf_counter()
    try:
        payload = server.chat([{"role": "user", "content": prompt}], max_tokens=max_tokens,
                              extra={"thinking_budget_tokens": thinking_budget} if thinking_budget else None)
        server.sample()
        content = (payload.get("choices") or [{}])[0].get("message", {}).get("content") or ""
        usage = payload.get("usage") or {}
        elapsed = round(time.perf_counter() - started, 1)
        toks = usage.get("completion_tokens")
        return {
            "ok": True,
            "content": content,
            "elapsed_seconds": elapsed,
            "completion_tokens": toks,
            "tokens_per_second": round(toks / elapsed, 2) if toks and elapsed else None,
        }
    except Exception as exc:
        return {"ok": False, "content": "", "error": str(exc),
                "elapsed_seconds": round(time.perf_counter() - started, 1)}


def score_comprehension(text: str) -> dict:
    low = text.lower()
    checks = {
        "file": "generate-overall-leaderboard.py" in low,
        "function": "load_benchmark_rows" in low,
        "why": ("guide" in low or "current-model-guide" in low or "chart" in low
                or "benchmark-capabilities" in low),
    }
    return {"score": sum(checks.values()) / len(checks), "checks": checks}


def score_long_context(text: str) -> dict:
    low = text.lower()
    checks = {
        "root_cause": ("langfuse" in low) and ("worker" in low or "queue" in low or "consumer" in low),
        "stuck_job": ("active" in low or "stuck" in low or "wedged" in low or "otlp" in low or "otel" in low),
        "redis_timeout": ("redis" in low and ("socket timeout" in low or "timeout" in low)),
        "fix": ("restart" in low),
    }
    return {"score": sum(checks.values()) / len(checks), "checks": checks}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="model slug/label for the artifact")
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--runtime", default="llama.cpp")
    ap.add_argument("--revision", default=None)
    ap.add_argument("--gate", default="full", choices=["fast", "full"])
    ap.add_argument("--pgrep", default="llama-server", help="pattern to sample server RSS via pgrep")
    args = ap.parse_args()

    server = H.Server(
        args.model, [], 0, OUT_DIR / "logs" / f"{args.model}-smoke.log",
        external_url=args.base_url, external_pgrep=args.pgrep,
    )

    WORKDIR.mkdir(parents=True, exist_ok=True)
    results: dict = {
        "schema_version": 1,
        "workflow": "bonsai-smoke-v1",
        "model": args.model,
        "runtime": args.runtime,
        "revision": args.revision,
        "base_url": args.base_url,
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "tests": {},
    }

    def guard(name, fn):
        try:
            return fn()
        except Exception as exc:  # keep partial results if one case breaks
            return {"ok": False, "success": False, "error": f"{type(exc).__name__}: {exc}"}

    browser_proc = None
    try:
        # 1. Small coding fix
        def _t1():
            d = H.fresh_dir(FIXTURES / "coding-fix", WORKDIR / "coding-fix")
            return H.run_agent(
                server, d,
                "The file orders.py has bugs. Fix line_total, order_subtotal and apply_discount so "
                "python3 test_orders.py passes. Run the tests after editing.",
                "python3 test_orders.py",
            )
        results["tests"]["1_small_coding_fix"] = guard("1", _t1)

        # 2. Repo comprehension
        def _t2():
            prompt = (FIXTURES / "repo-comprehension" / "PROMPT.md").read_text()
            out = run_text_task(server, prompt)
            out["evaluation"] = score_comprehension(out.get("content", ""))
            return out
        results["tests"]["2_repo_comprehension"] = guard("2", _t2)

        # 3. Agentic coding loop
        def _t3():
            d = H.fresh_dir(FIXTURES / "coding-loop", WORKDIR / "coding-loop")
            return H.run_agent(
                server, d,
                "Read inventory_spec.md. Implement remove_sku and average_unit_cost in inventory.py. "
                "Run python3 run_checks.py until all checks pass.",
                "python3 run_checks.py",
            )
        results["tests"]["3_agentic_coding_loop"] = guard("3", _t3)

        # 4. Browser/tool task
        def _t4():
            proc, url = _serve_browser_fixture()
            results.setdefault("_browser_proc", None)
            results["_browser_proc"] = proc
            return run_browser_task(server, url)
        results["tests"]["4_browser_tool_task"] = guard("4", _t4)
        browser_proc = results.pop("_browser_proc", None)

        # 5. Long-context diagnosis
        def _t5():
            slice_text = (FIXTURES / "long-context" / "session-slice.md").read_text()
            question = (FIXTURES / "long-context" / "QUESTION.md").read_text().split("## Hidden answer key")[0]
            out = run_text_task(server, f"{question}\n\n{slice_text}", max_tokens=6000,
                                thinking_budget=1500)
            out["evaluation"] = score_long_context(out.get("content", ""))
            return out
        results["tests"]["5_long_context_diagnosis"] = guard("5", _t5)
    finally:
        if browser_proc:
            browser_proc.terminate()

    # Gate summary
    passed = sum(1 for t in results["tests"].values() if t.get("success") or t.get("evaluation", {}).get("score", 0) >= 0.5)
    rescues = 0  # recorded manually in the acceptance report
    results["summary"] = {"tests_run": len(results["tests"]), "tests_passed": passed,
                          "human_rescues": rescues, "runtime": args.runtime}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"workflow-smoke-{args.model}.json"
    path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {path}")
    print(f"passed {passed}/{len(results['tests'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
