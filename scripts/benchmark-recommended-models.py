#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MODEL_CONFIG = ROOT / "config" / "recommended-mlx-models.json"
BASE_BENCHMARK = ROOT / "scripts" / "benchmark-capabilities.py"
OUTPUT_DIR = ROOT / "output" / "benchmarks"
LOG_DIR = OUTPUT_DIR / "logs"
DEFAULT_PORT = 8091
DEFAULT_STARTUP_TIMEOUT = 900


def load_base_benchmark() -> Any:
    spec = importlib.util.spec_from_file_location("local_llm_capability_benchmark", BASE_BENCHMARK)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import {BASE_BENCHMARK}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def executable(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f"Required executable is missing: {name}")
    return path


def hf_cli() -> str:
    server = Path(executable("mlx_lm.server")).resolve()
    sibling = server.parent / "hf"
    if sibling.exists():
        return str(sibling)
    return executable("hf")


def install_model(model: dict[str, Any]) -> Path:
    command = [
        hf_cli(),
        "download",
        model["model"],
        "--revision",
        model["revision"],
        "--quiet",
    ]
    print(f"  Installing exact revision {model['revision'][:12]}...", flush=True)
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "unknown download error"
        raise RuntimeError(message)
    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError("Hugging Face download did not return a snapshot path")
    snapshot = Path(lines[-1])
    if not snapshot.exists():
        raise RuntimeError(f"Downloaded snapshot path does not exist: {snapshot}")
    return snapshot


def request_json(url: str, body: dict[str, Any] | None = None, timeout: int = 30) -> dict[str, Any]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="GET" if data is None else "POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def extract_response_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "".join(extract_response_text(item) for item in value)
    if isinstance(value, dict):
        for key in ("content", "text", "value"):
            if key in value:
                return extract_response_text(value[key])
    return ""


def clean_model_output(text: str) -> str:
    final_marker = "<|channel|>final<|message|>"
    if final_marker in text:
        text = text.rsplit(final_marker, 1)[-1]
    if "</think>" in text:
        text = text.rsplit("</think>", 1)[-1]
    for marker in ("<|end|>", "<|start|>"):
        text = text.split(marker, 1)[0]
    return text.strip()


def wait_for_server(base_url: str, process: subprocess.Popen[str], timeout: int) -> float:
    started = time.perf_counter()
    deadline = started + timeout
    last_error = "server did not answer"
    while time.perf_counter() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"MLX server exited with code {process.returncode}")
        try:
            request_json(f"{base_url}/v1/models", timeout=5)
            return round((time.perf_counter() - started) * 1000, 1)
        except Exception as exc:  # The server is expected to reject connections while loading.
            last_error = str(exc)
            time.sleep(1)
    raise TimeoutError(f"MLX server did not become ready within {timeout}s: {last_error}")


def warm_up_server(base_url: str, model: dict[str, Any], snapshot: Path, timeout: int = 60) -> float:
    started = time.perf_counter()
    body = {
        "model": str(snapshot),
        "messages": [{"role": "user", "content": "Reply with OK."}],
        "temperature": 0,
        "max_tokens": 1,
        "stream": False,
    }
    if model.get("runtime") == "mlx_vlm" and model.get("disable_thinking"):
        body["enable_thinking"] = False
    request_json(
        f"{base_url}/v1/chat/completions",
        body=body,
        timeout=timeout,
    )
    return round((time.perf_counter() - started) * 1000, 1)


def stop_server(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=30)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


def start_server(
    model: dict[str, Any], snapshot: Path, port: int, log_path: Path, startup_timeout: int
) -> tuple[subprocess.Popen[str], Any, float]:
    if model.get("runtime") == "mlx_vlm":
        command = [
            executable("mlx_vlm.server"),
            "--model",
            str(snapshot),
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "INFO",
        ]
    else:
        command = [
            executable("mlx_lm.server"),
            "--model",
            str(snapshot),
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--temp",
            "0",
            "--max-tokens",
            "256",
            "--log-level",
            "INFO",
        ]
        chat_template_args = dict(model.get("chat_template_args") or {})
        if model.get("disable_thinking"):
            chat_template_args["enable_thinking"] = False
        if chat_template_args:
            command.extend(["--chat-template-args", json.dumps(chat_template_args)])

    log_handle = log_path.open("w", encoding="utf-8")
    process = subprocess.Popen(
        command,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )
    try:
        startup_ms = wait_for_server(f"http://127.0.0.1:{port}", process, startup_timeout)
        startup_ms = round(
            startup_ms + warm_up_server(f"http://127.0.0.1:{port}", model, snapshot), 1
        )
    except Exception:
        stop_server(process)
        log_handle.close()
        raise
    return process, log_handle, startup_ms


def run_capability_task(
    model: dict[str, Any], served_model: str, task: Any, evaluator: Any, base_url: str, max_tokens: int
) -> dict[str, Any]:
    body = {
        "model": served_model,
        "messages": [{"role": "user", "content": task.prompt}],
        "temperature": 0,
        "seed": 42,
        "max_tokens": max_tokens,
        "stream": False,
    }
    if model.get("runtime") == "mlx_vlm" and model.get("disable_thinking"):
        body["enable_thinking"] = False
    started = time.perf_counter()
    try:
        payload = request_json(f"{base_url}/v1/chat/completions", body=body, timeout=300)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
        choice = (payload.get("choices") or [{}])[0]
        message = choice.get("message") if isinstance(choice, dict) else choice
        content = clean_model_output(extract_response_text(message))
        evaluation = evaluator(content)
        usage = payload.get("usage") or {}
        completion_tokens = usage.get("completion_tokens")
        wall_tokens_per_second = None
        if isinstance(completion_tokens, int) and elapsed_ms > 0:
            wall_tokens_per_second = round(completion_tokens / (elapsed_ms / 1000), 3)
        return {
            "content": content,
            "elapsed_ms": elapsed_ms,
            "ok": True,
            "error": None,
            "raw": payload,
            "usage": usage,
            "wall_tokens_per_second": wall_tokens_per_second,
            "evaluation": evaluation,
        }
    except urllib.error.HTTPError as exc:
        error = exc.read().decode("utf-8", errors="replace")
    except Exception as exc:
        error = str(exc)
    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
    return {
        "content": "",
        "elapsed_ms": elapsed_ms,
        "ok": False,
        "error": error,
        "raw": None,
        "usage": {},
        "wall_tokens_per_second": None,
        "evaluation": {"score": 0.0, "summary": "Invocation failed", "details": {"error": error}},
    }


def parse_performance_output(output: str) -> dict[str, Any]:
    match = re.search(
        r"Averages:\s+prompt_tps=([0-9.]+),\s+generation_tps=([0-9.]+),\s+peak_memory=([0-9.]+)",
        output,
    )
    trials = []
    for trial in re.finditer(
        r"Trial\s+(\d+):\s+prompt_tps=([0-9.]+),\s+generation_tps=([0-9.]+),"
        r"\s+peak_memory=([0-9.]+),\s+total_time=([0-9.]+)",
        output,
    ):
        trials.append(
            {
                "trial": int(trial.group(1)),
                "prompt_tokens_per_second": float(trial.group(2)),
                "generation_tokens_per_second": float(trial.group(3)),
                "peak_memory_gb": float(trial.group(4)),
                "total_time_seconds": float(trial.group(5)),
            }
        )
    return {
        "ok": match is not None,
        "prompt_tokens_per_second": float(match.group(1)) if match else None,
        "generation_tokens_per_second": float(match.group(2)) if match else None,
        "peak_memory_gb": float(match.group(3)) if match else None,
        "trials": trials,
        "raw_output": output,
    }


def run_performance_benchmark(model_path: Path, protocol: dict[str, Any]) -> dict[str, Any]:
    command = [
        executable("mlx_lm.benchmark"),
        "--model",
        str(model_path),
        "--prompt-tokens",
        str(protocol["performance_prompt_tokens"]),
        "--generation-tokens",
        str(protocol["performance_generation_tokens"]),
        "--num-trials",
        str(protocol["performance_trials"]),
        "--delay",
        "1",
    ]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=900, check=False)
    output = "\n".join(part for part in [completed.stdout.strip(), completed.stderr.strip()] if part)
    parsed = parse_performance_output(output)
    parsed["returncode"] = completed.returncode
    parsed["prompt_tokens"] = protocol["performance_prompt_tokens"]
    parsed["generation_tokens"] = protocol["performance_generation_tokens"]
    parsed["trial_count"] = protocol["performance_trials"]
    if completed.returncode != 0 and not parsed["ok"]:
        parsed["error"] = output[-2000:]
    return parsed


def failed_task(task: Any, error: str) -> dict[str, Any]:
    return {
        "content": "",
        "elapsed_ms": None,
        "ok": False,
        "error": error,
        "raw": None,
        "usage": {},
        "wall_tokens_per_second": None,
        "evaluation": {"score": 0.0, "summary": "Invocation failed", "details": {"error": error}},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Install and benchmark the recommended MLX model builds.")
    parser.add_argument("--models", nargs="+", help="Model slugs to run. Default: every configured model.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--startup-timeout", type=int, default=DEFAULT_STARTUP_TIMEOUT)
    parser.add_argument("--skip-performance", action="store_true")
    args = parser.parse_args()

    base = load_base_benchmark()
    config = json.loads(MODEL_CONFIG.read_text(encoding="utf-8"))
    protocol = config["protocol"]
    configured_models = config["models"]
    requested = set(args.models or [model["slug"] for model in configured_models])
    selected = [model for model in configured_models if model["slug"] in requested]
    unknown = requested - {model["slug"] for model in configured_models}
    if unknown:
        parser.error(f"Unknown model slugs: {', '.join(sorted(unknown))}")

    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    generated_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUTPUT_DIR / f"capability-benchmark-{timestamp}.json"
    results: dict[str, Any] = {
        "schema_version": 2,
        "benchmark_protocol": protocol,
        "generated_at": generated_at,
        "environment": {
            "machine": platform.machine(),
            "platform": platform.platform(),
            "macos_version": platform.mac_ver()[0],
            "python": platform.python_version(),
            "mlx_lm_version": subprocess.run(
                [executable("mlx_lm"), "--version"], capture_output=True, text=True, check=False
            ).stdout.strip(),
            "seed": protocol["seed"],
            "hardware": "Apple M5 Pro, 48 GB unified memory, 15 CPU cores, 16 GPU cores",
        },
        "models": [
            {
                "slug": model["slug"],
                "label": model["label"],
                "kind": model.get("runtime", "mlx"),
                "model_name": model["model"],
                "revision": model["revision"],
                "download_size_gb": model["download_size_gb"],
                "base_model": model["base_model"],
                "note": model["recommended_use"],
            }
            for model in selected
        ],
        "tasks": [{"slug": task.slug, "label": task.label, "category": task.category} for task in base.TASKS],
        "results": {},
        "performance": {},
        "runtime_status": {},
        "json_path": str(json_path),
    }

    for model in selected:
        slug = model["slug"]
        print(f"== {model['label']} ==", flush=True)
        process: subprocess.Popen[str] | None = None
        log_handle = None
        log_path = LOG_DIR / f"{timestamp}-{slug}.log"
        try:
            snapshot = install_model(model)
            print(f"  Snapshot: {snapshot}", flush=True)
            process, log_handle, startup_ms = start_server(
                model, snapshot, args.port, log_path, args.startup_timeout
            )
            results["runtime_status"][slug] = {
                "status": "running",
                "startup_ms": startup_ms,
                "snapshot_path": str(snapshot),
                "log_path": str(log_path.relative_to(ROOT)),
            }
            model_results: dict[str, Any] = {}
            for task in base.TASKS:
                print(f"  - {task.label}", flush=True)
                model_results[task.slug] = run_capability_task(
                    model,
                    str(snapshot),
                    task,
                    base.EVALUATORS[task.slug],
                    f"http://127.0.0.1:{args.port}",
                    protocol["max_tokens"],
                )
            results["results"][slug] = model_results
            successful_tasks = sum(1 for item in model_results.values() if item["ok"])
            if successful_tasks == len(model_results):
                results["runtime_status"][slug]["status"] = "passed"
            elif successful_tasks == 0:
                results["runtime_status"][slug]["status"] = "runtime_failed"
                results["runtime_status"][slug]["error"] = "Every capability invocation failed"
            else:
                results["runtime_status"][slug]["status"] = "partial"
        except Exception as exc:
            error = str(exc)
            print(f"  Runtime failed: {error}", flush=True)
            results["runtime_status"][slug] = {
                "status": "runtime_failed",
                "error": error,
                "log_path": str(log_path.relative_to(ROOT)),
            }
            results["results"][slug] = {task.slug: failed_task(task, error) for task in base.TASKS}
        finally:
            if process is not None:
                stop_server(process)
            if log_handle is not None:
                log_handle.close()

        if (
            not args.skip_performance
            and model.get("runtime", "mlx") == "mlx"
            and results["runtime_status"][slug]["status"] in {"passed", "partial"}
        ):
            snapshot_path = Path(results["runtime_status"][slug]["snapshot_path"])
            print("  - MLX throughput benchmark", flush=True)
            results["performance"][slug] = run_performance_benchmark(snapshot_path, protocol)
        else:
            reason = (
                "MLX-VLM throughput is derived from capability request counters"
                if model.get("runtime") == "mlx_vlm"
                else "Skipped because the runtime did not pass"
            )
            results["performance"][slug] = {"ok": False, "error": reason}

        json_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
        print(f"  Saved checkpoint: {json_path}", flush=True)

    print(f"Wrote raw benchmark data to {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
