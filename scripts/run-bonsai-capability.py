#!/usr/bin/env python3
"""Run the EXISTING Local LLM Lab capability tasks against a llama.cpp server.

Reuses scripts/benchmark-capabilities.py TASKS and evaluators verbatim so the
Bonsai numbers are directly comparable with the published leaderboard rows.
Adds only a llama.cpp/OpenAI-server runner; no new task definitions.
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import platform
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_base():
    import sys
    spec = importlib.util.spec_from_file_location("cap", ROOT / "scripts" / "benchmark-capabilities.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["cap"] = mod
    spec.loader.exec_module(mod)
    return mod


def post(url, body, timeout=600):
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--slug", default="bonsai2_27b_llamacpp")
    ap.add_argument("--label", default="Ternary Bonsai 2 27B (PQ2_0 GGUF, llama.cpp)")
    args = ap.parse_args()
    cap = load_base()

    results = {
        "schema_version": 1,
        "benchmark_protocol": {"name": "bonsai-capability-v1", "seed": cap.SEED, "max_tokens": 512},
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "environment": {
            "machine": platform.machine(), "platform": platform.platform(),
            "macos_version": platform.mac_ver()[0], "hardware": "Apple M5 Pro, 48 GB unified memory",
        },
        "models": [{"slug": args.slug, "label": args.label, "kind": "llamacpp",
                    "model_name": "Ternary-Bonsai-2-27B-PQ2_0.gguf"}],
        "tasks": [{"slug": t.slug, "label": t.label, "category": t.category} for t in cap.TASKS],
        "results": {args.slug: {}},
        "runtime_status": {args.slug: {"status": "passed"}},
    }

    for task in cap.TASKS:
        body = {"model": "local", "messages": [{"role": "user", "content": task.prompt}],
                "temperature": 0, "seed": cap.SEED, "max_tokens": 512, "stream": False,
                "chat_template_kwargs": {"enable_thinking": False}}
        started = time.perf_counter()
        try:
            payload = post(f"{args.base_url}/v1/chat/completions", body)
            elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
            message = (payload.get("choices") or [{}])[0].get("message") or {}
            content = message.get("content") or ""
            usage = payload.get("usage") or {}
            evaluation = cap.EVALUATORS[task.slug](content)
            results["results"][args.slug][task.slug] = {
                "content": content, "elapsed_ms": elapsed_ms, "ok": True, "error": None,
                "usage": usage, "evaluation": evaluation,
                "wall_tokens_per_second": round(usage.get("completion_tokens", 0) / (elapsed_ms / 1000), 3)
                if usage.get("completion_tokens") and elapsed_ms else None,
            }
            print(f"  {task.slug}: score={evaluation.get('score')} {elapsed_ms} ms", flush=True)
        except Exception as exc:
            results["results"][args.slug][task.slug] = {
                "content": "", "ok": False, "error": str(exc),
                "evaluation": {"score": 0.0, "summary": "Invocation failed"},
            }
            print(f"  {task.slug}: FAILED {exc}", flush=True)

    scores = [v["evaluation"].get("score") or 0 for v in results["results"][args.slug].values()]
    results["summary"] = {
        "tasks": len(scores), "mean_score": round(sum(scores) / len(scores), 3),
        "median_latency_ms": round(sorted(v["elapsed_ms"] for v in results["results"][args.slug].values()
                                          if "elapsed_ms" in v)[len(scores) // 2], 1),
    }
    out = ROOT / "output" / "benchmarks" / f"capability-benchmark-bonsai-{args.slug}.json"
    out.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print("wrote", out)
    print("summary:", results["summary"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
