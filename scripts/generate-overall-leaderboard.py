#!/usr/bin/env python3
from __future__ import annotations

import csv
import datetime as dt
import json
import math
import statistics
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_DIR = ROOT / "output" / "benchmarks"
OUTPUT_DIR = ROOT / "output" / "leaderboard"
HISTORY_FILE = ROOT / "config" / "model-test-history.json"
SITE_DATA = ROOT / "site" / "src" / "leaderboard.json"

TASK_WEIGHTS = {
    "shell_scripting": 0.22,
    "json_restructuring": 0.20,
    "classification": 0.16,
    "short_summary": 0.14,
    "text_transformation": 0.12,
    "translation": 0.06,
    "unknown_refusal": 0.05,
    "harmless_exactness": 0.05,
}
CLAIMED_TASKS = {
    "shell_scripting",
    "json_restructuring",
    "classification",
    "short_summary",
    "text_transformation",
    "translation",
}


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT))


def exact_build_id(kind: str, model_name: str) -> str:
    return f"{kind}:{model_name}"


def task_score(task: dict[str, Any]) -> float:
    return float((task.get("evaluation") or {}).get("score") or 0.0)


def derive_ollama_generation_tps(model_results: dict[str, Any]) -> float | None:
    values = []
    for result in model_results.values():
        raw = result.get("raw") or {}
        if not isinstance(raw, dict):
            continue
        count = raw.get("eval_count")
        duration = raw.get("eval_duration")
        if isinstance(count, (int, float)) and isinstance(duration, (int, float)) and duration > 0:
            values.append(count / (duration / 1_000_000_000))
    return round(statistics.median(values), 3) if values else None


def derive_request_generation_tps(model_results: dict[str, Any]) -> float | None:
    values = [
        float(result["wall_tokens_per_second"])
        for result in model_results.values()
        if result.get("ok") and isinstance(result.get("wall_tokens_per_second"), (int, float))
    ]
    return round(statistics.median(values), 3) if values else None


def score_candidate(
    data: dict[str, Any], model: dict[str, Any], artifact: Path
) -> dict[str, Any]:
    slug = model["slug"]
    model_results = (data.get("results") or {}).get(slug) or {}
    successful = [task for task in model_results.values() if task.get("ok")]
    successful_claimed = sum(1 for name in CLAIMED_TASKS if (model_results.get(name) or {}).get("ok"))
    elapsed = [
        float(task["elapsed_ms"])
        for task in model_results.values()
        if task.get("ok") and isinstance(task.get("elapsed_ms"), (int, float))
    ]
    median_latency_ms = round(statistics.median(elapsed), 1) if elapsed else None
    quality = sum(task_score(model_results.get(name) or {}) * weight for name, weight in TASK_WEIGHTS.items())
    reliability = len(successful) / len(TASK_WEIGHTS)
    latency_utility = 0.0 if median_latency_ms is None else 1 / (1 + median_latency_ms / 15_000)
    work_fit_score = round(100 * (0.80 * quality + 0.15 * latency_utility + 0.05 * reliability), 1)

    performance = (data.get("performance") or {}).get(slug) or {}
    generation_tps = performance.get("generation_tokens_per_second")
    prompt_tps = performance.get("prompt_tokens_per_second")
    peak_memory_gb = performance.get("peak_memory_gb")
    generation_speed_basis = "isolated MLX trial" if generation_tps is not None else None
    if generation_tps is None and model.get("kind") == "ollama":
        generation_tps = derive_ollama_generation_tps(model_results)
        generation_speed_basis = "median Ollama generation counter"
    if generation_tps is None and model.get("kind") == "mlx_vlm":
        generation_tps = derive_request_generation_tps(model_results)
        generation_speed_basis = "median end-to-end capability request"

    runtime = model.get("kind") or "unknown"
    model_name = model.get("model_name") or model.get("label") or slug
    runtime_status = (data.get("runtime_status") or {}).get(slug) or {}
    status = runtime_status.get("status")
    if not status:
        if successful_claimed == len(CLAIMED_TASKS):
            status = "benchmarked"
        elif successful:
            status = "partial"
        else:
            status = "runtime_failed"

    return {
        "build_id": exact_build_id(runtime, model_name),
        "label": model.get("label") or model_name,
        "runtime": runtime,
        "model_name": model_name,
        "base_model": model.get("base_model"),
        "revision": model.get("revision"),
        "download_size_gb": model.get("download_size_gb"),
        "status": status,
        "test_level": "capability",
        "generated_at": data.get("generated_at"),
        "artifact": relative(artifact),
        "successful_tasks": len(successful),
        "successful_claimed_tasks": successful_claimed,
        "task_count": len(model_results),
        "quality_score": round(quality * 100, 1),
        "work_fit_score": work_fit_score,
        "median_latency_ms": median_latency_ms,
        "generation_tokens_per_second": generation_tps,
        "generation_speed_basis": generation_speed_basis,
        "prompt_tokens_per_second": prompt_tps,
        "peak_memory_gb": peak_memory_gb,
        "recommended_use": model.get("note"),
        "runtime_error": runtime_status.get("error"),
        "task_scores": {name: task_score(model_results.get(name) or {}) for name in TASK_WEIGHTS},
    }


def candidate_order(row: dict[str, Any]) -> tuple[int, int, str]:
    return (
        int(row.get("successful_claimed_tasks") or 0),
        int(row.get("successful_tasks") or 0),
        str(row.get("generated_at") or ""),
    )


def load_benchmark_rows() -> dict[str, dict[str, Any]]:
    chosen: dict[str, dict[str, Any]] = {}
    for artifact in sorted(BENCHMARK_DIR.glob("capability-benchmark-*.json")):
        try:
            data = json.loads(artifact.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        for model in data.get("models") or []:
            row = score_candidate(data, model, artifact)
            current = chosen.get(row["build_id"])
            if current is None or candidate_order(row) > candidate_order(current):
                chosen[row["build_id"]] = row
    return chosen


def merge_history(rows: dict[str, dict[str, Any]]) -> None:
    history = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    for item in history["models"]:
        if item["build_id"] in rows:
            continue
        rows[item["build_id"]] = {
            **item,
            "generated_at": item.get("tested_at"),
            "artifact": item.get("evidence"),
            "successful_tasks": None,
            "successful_claimed_tasks": None,
            "task_count": None,
            "quality_score": None,
            "work_fit_score": None,
            "median_latency_ms": None,
            "generation_tokens_per_second": None,
            "prompt_tokens_per_second": None,
            "peak_memory_gb": None,
            "task_scores": {},
        }


def display_number(value: Any, digits: int = 1) -> str:
    if not isinstance(value, (int, float)) or not math.isfinite(value):
        return "n/a"
    return f"{value:.{digits}f}"


def display_metric(value: Any, unit: str, digits: int = 1) -> str:
    number = display_number(value, digits)
    return number if number == "n/a" else f"{number} {unit}"


def markdown_report(payload: dict[str, Any]) -> str:
    ranked = payload["ranked"]
    unranked = payload["unranked"]
    lines = [
        "# Overall Local Model Leaderboard",
        "",
        f"- Generated: `{payload['generated_at']}`",
        f"- Machine: `{payload['machine']}`",
        f"- Exact model builds recorded: `{payload['summary']['total_builds']}`",
        f"- Fully capability-benchmarked builds: `{payload['summary']['ranked_builds']}`",
        "",
        "## Ranked Models",
        "",
        "The work-fit score puts most weight on structured coding-adjacent tasks, then response time and runtime reliability. Models are only ranked after completing the shared eight-task suite.",
        "",
        "| Rank | Exact build | Runtime | Work fit | Task quality | Median response | Generation speed | Peak memory |",
        "|---:|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in ranked:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["rank"]),
                    row["label"],
                    row["runtime"],
                    display_number(row["work_fit_score"]),
                    display_number(row["quality_score"]),
                    display_metric(row['median_latency_ms'] / 1000 if row['median_latency_ms'] else None, "s", 2),
                    display_metric(row['generation_tokens_per_second'], "tok/s"),
                    display_metric(row['peak_memory_gb'], "GB"),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Tested but not ranked",
            "",
            "These builds have real local evidence but did not complete the shared capability suite, so they are listed without an invented score.",
            "",
            "| Exact build | Runtime | Status | Strongest evidence | Note |",
            "|---|---|---|---|---|",
        ]
    )
    for row in unranked:
        note = row.get("note") or row.get("runtime_error") or "No additional note recorded."
        lines.append(
            f"| {row['label']} | {row['runtime']} | {row['status']} | `{row.get('artifact') or 'n/a'}` | {note} |"
        )

    lines.extend(
        [
            "",
            "## Scoring method",
            "",
            "- Task quality is weighted toward shell work, structured JSON, classification, concise synthesis, and instruction following because those match the coding-agent work recorded on this machine.",
            "- Work fit is 80% weighted task quality, 15% median response-time utility, and 5% successful invocation rate.",
            "- Generation speed and peak memory come from three MLX trials with a 512-token prompt and 128-token completion when available. Older Ollama speed is derived from its recorded generation counters.",
            "- MLX-VLM generation speed is median end-to-end throughput from the capability requests, so its speed is not directly comparable with the isolated text-only MLX trials.",
            "- Different runtime builds of the same base model remain separate because quantization and inference software materially change local speed and reliability.",
            "- Smoke tests and failed load attempts remain visible, but they are not ranked against full benchmark runs.",
            "",
            "## Source artifacts",
            "",
        ]
    )
    for artifact in payload["source_artifacts"]:
        lines.append(f"- `{artifact}`")
    return "\n".join(lines) + "\n"


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    fields = [
        "rank",
        "label",
        "runtime",
        "model_name",
        "status",
        "work_fit_score",
        "quality_score",
        "median_latency_ms",
        "generation_tokens_per_second",
        "generation_speed_basis",
        "prompt_tokens_per_second",
        "peak_memory_gb",
        "artifact",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    rows = load_benchmark_rows()
    merge_history(rows)
    ranked = [
        row
        for row in rows.values()
        if row.get("successful_claimed_tasks") == len(CLAIMED_TASKS)
        and isinstance(row.get("work_fit_score"), (int, float))
    ]
    ranked.sort(
        key=lambda row: (
            row["work_fit_score"],
            row.get("quality_score") or 0,
            -(row.get("median_latency_ms") or 10**9),
        ),
        reverse=True,
    )
    for index, row in enumerate(ranked, start=1):
        row["rank"] = index

    ranked_ids = {row["build_id"] for row in ranked}
    unranked = [row for row in rows.values() if row["build_id"] not in ranked_ids]
    unranked.sort(key=lambda row: (row.get("status") != "runtime_failed", row["label"].lower()), reverse=True)
    source_artifacts = sorted({row["artifact"] for row in rows.values() if row.get("artifact")})
    generated_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    payload = {
        "schema_version": 1,
        "generated_at": generated_at,
        "machine": "Apple M5 Pro, 48 GB unified memory, 15 CPU cores, 16 GPU cores",
        "score_definition": {
            "task_weights": TASK_WEIGHTS,
            "work_fit": "80% task quality + 15% median response-time utility + 5% invocation reliability",
        },
        "summary": {
            "total_builds": len(rows),
            "ranked_builds": len(ranked),
            "unranked_builds": len(unranked),
            "best_model": ranked[0]["label"] if ranked else None,
        },
        "ranked": ranked,
        "unranked": unranked,
        "source_artifacts": source_artifacts,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUTPUT_DIR / "overall-leaderboard.json"
    markdown_path = ROOT / "overall-leaderboard.md"
    csv_path = OUTPUT_DIR / "overall-leaderboard.csv"
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(markdown_report(payload), encoding="utf-8")
    write_csv(ranked + unranked, csv_path)
    SITE_DATA.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {markdown_path}")
    print(f"Wrote {json_path}")
    print(f"Wrote {csv_path}")
    print(f"Wrote {SITE_DATA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
