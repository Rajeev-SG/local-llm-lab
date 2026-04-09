#!/usr/bin/env python3
"""Generate GitHub-friendly SVG charts for benchmark results.

This script intentionally uses only the Python standard library so it can run
inside lean local environments without matplotlib.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON = ROOT / "output/benchmarks/capability-benchmark-20260409T173011Z.json"
DEFAULT_GEMMA_JSON = ROOT / "output/benchmarks/capability-benchmark-20260409T175237Z.json"
DEFAULT_OUTPUT_DIR = ROOT / "output/charts/benchmark-20260409"

TASKS = [
    ("shell_scripting", "Shell"),
    ("text_transformation", "Transform"),
    ("classification", "Classify"),
    ("short_summary", "Summary"),
    ("json_restructuring", "JSON"),
    ("translation", "Translate"),
]
GUARDRAILS = [
    ("unknown_refusal", "Unknown refusal"),
    ("harmless_exactness", "Exact harmless"),
]
LATENCY_TASKS = [
    ("shell_scripting", "Shell"),
    ("text_transformation", "Transform"),
    ("classification", "Classify"),
    ("short_summary", "Summary"),
    ("json_restructuring", "JSON"),
    ("translation", "Translate"),
]

MODEL_COLORS = {
    "apfel": "#D97706",
    "qwen35_9b": "#2563EB",
    "phi4": "#16A34A",
    "qwen25_14b": "#7C3AED",
    "qwen25_coder_14b": "#DB2777",
    "mistral_small_22b": "#DC2626",
    "gemma4_e4b": "#6B7280",
}


def compact(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.2f}"


def score_color(value: float | None) -> str:
    if value is None:
        return "#E5E7EB"
    low = (220, 38, 38)
    high = (22, 163, 74)
    r = int(low[0] + (high[0] - low[0]) * value)
    g = int(low[1] + (high[1] - low[1]) * value)
    b = int(low[2] + (high[2] - low[2]) * value)
    return f"#{r:02X}{g:02X}{b:02X}"


def rgba(hex_color: str, alpha: float) -> str:
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha:.3f})"


def svg_header(width: int, height: int, title: str) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        f"<title>{escape(title)}</title>",
        f"<desc>{escape(title)}</desc>",
        "<style>",
        ".bg { fill: #FAFAFB; }",
        ".card { fill: #FFFFFF; stroke: #E5E7EB; stroke-width: 1; }",
        ".axis { stroke: #D1D5DB; stroke-width: 1; }",
        ".grid { stroke: #E5E7EB; stroke-width: 1; stroke-dasharray: 4 4; }",
        ".title { font: 700 28px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; fill: #111827; }",
        ".subtitle { font: 500 14px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; fill: #4B5563; }",
        ".label { font: 600 14px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; fill: #111827; }",
        ".small { font: 500 12px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; fill: #4B5563; }",
        ".tiny { font: 500 11px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; fill: #6B7280; }",
        ".value { font: 700 13px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; fill: #111827; }",
        ".value-light { font: 700 13px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; fill: #FFFFFF; }",
        ".mono { font: 600 12px ui-monospace, SFMono-Regular, Menlo, monospace; fill: #111827; }",
        "</style>",
        f'<rect class="bg" x="0" y="0" width="{width}" height="{height}" rx="24" />',
    ]


def save_svg(path: Path, lines: list[str]) -> None:
    lines.append("</svg>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def average_score(model: dict[str, Any]) -> float | None:
    values = [model["scores"].get(slug) for slug, _ in TASKS]
    if any(value is None for value in values):
        return None
    return round(sum(values) / len(values), 3)


def median_latency(model: dict[str, Any]) -> float | None:
    values = [model["latencies"].get(slug) for slug, _ in LATENCY_TASKS]
    values = [value for value in values if value is not None]
    if not values:
        return None
    return round(statistics.median(values), 1)


def load_models(scored_path: Path, gemma_path: Path) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    scored = json.loads(scored_path.read_text(encoding="utf-8"))
    gemma = json.loads(gemma_path.read_text(encoding="utf-8"))

    models: list[dict[str, Any]] = []
    for model in scored["models"]:
        slug = model["slug"]
        row = scored["results"][slug]
        models.append(
            {
                "slug": slug,
                "label": model["label"],
                "status": "scored",
                "scores": {task: row[task]["evaluation"]["score"] for task, _ in TASKS},
                "guardrails": {task: row[task]["evaluation"]["score"] for task, _ in GUARDRAILS},
                "latencies": {task: row[task]["elapsed_ms"] for task, _ in LATENCY_TASKS},
                "avg": average_score(
                    {
                        "scores": {task: row[task]["evaluation"]["score"] for task, _ in TASKS},
                        "latencies": {task: row[task]["elapsed_ms"] for task, _ in LATENCY_TASKS},
                    }
                ),
                "median_ms": median_latency(
                    {
                        "scores": {task: row[task]["evaluation"]["score"] for task, _ in TASKS},
                        "latencies": {task: row[task]["elapsed_ms"] for task, _ in LATENCY_TASKS},
                    }
                ),
            }
        )

    gemma_error = gemma["results"]["gemma4_e4b"]["shell_scripting"]["error"]
    models.append(
        {
            "slug": "gemma4_e4b",
            "label": "gemma4:e4b",
            "status": "runtime_blocked",
            "scores": {task: None for task, _ in TASKS},
            "guardrails": {task: None for task, _ in GUARDRAILS},
            "latencies": {task: None for task, _ in LATENCY_TASKS},
            "avg": None,
            "median_ms": None,
            "error": gemma_error,
        }
    )
    return scored, gemma, models


def draw_legend(lines: list[str], models: list[dict[str, Any]], x: int, y: int, cols: int = 3) -> None:
    col_width = 220
    row_height = 24
    for index, model in enumerate(models):
        cx = x + (index % cols) * col_width
        cy = y + (index // cols) * row_height
        color = MODEL_COLORS[model["slug"]]
        lines.append(f'<rect x="{cx}" y="{cy - 11}" width="14" height="14" rx="4" fill="{color}" />')
        suffix = " (blocked)" if model["status"] != "scored" else ""
        lines.append(f'<text class="small" x="{cx + 22}" y="{cy}">{escape(model["label"] + suffix)}</text>')


def chart_heatmap(path: Path, models: list[dict[str, Any]], title_suffix: str) -> None:
    width, height = 1360, 560
    lines = svg_header(width, height, "Capability heatmap")
    lines.append('<text class="title" x="56" y="56">Capability Score Heatmap</text>')
    lines.append(f'<text class="subtitle" x="56" y="84">{escape(title_suffix)}</text>')

    left = 220
    top = 140
    cell_w = 130
    cell_h = 54
    headers = [label for _, label in TASKS] + ["Average"]

    for idx, header in enumerate(headers):
        x = left + idx * cell_w
        lines.append(f'<text class="label" x="{x + cell_w / 2:.1f}" y="{top - 20}" text-anchor="middle">{escape(header)}</text>')

    for row_idx, model in enumerate(models):
        y = top + row_idx * cell_h
        lines.append(f'<text class="label" x="56" y="{y + 33}">{escape(model["label"])}</text>')
        if model["status"] != "scored":
            lines.append(f'<text class="tiny" x="56" y="{y + 48}">runtime blocked</text>')
        values = [model["scores"][slug] for slug, _ in TASKS] + [model["avg"]]
        for col_idx, value in enumerate(values):
            x = left + col_idx * cell_w
            fill = score_color(value)
            stroke = "#CBD5E1" if value is None else "#FFFFFF"
            lines.append(f'<rect x="{x}" y="{y}" width="{cell_w - 8}" height="{cell_h - 8}" rx="12" fill="{fill}" stroke="{stroke}" />')
            cls = "value-light" if value is not None and value >= 0.62 else "value"
            lines.append(f'<text class="{cls}" x="{x + (cell_w - 8) / 2:.1f}" y="{y + 30}" text-anchor="middle">{escape(compact(value))}</text>')

    lines.append('<text class="tiny" x="56" y="520">Green is stronger. Gray indicates a model that was part of the comparison set but could not be fairly scored.</text>')
    save_svg(path, lines)


def chart_average_ranking(path: Path, models: list[dict[str, Any]], title_suffix: str) -> None:
    width, height = 1260, 520
    lines = svg_header(width, height, "Average benchmark score ranking")
    lines.append('<text class="title" x="56" y="56">Average Score Ranking</text>')
    lines.append(f'<text class="subtitle" x="56" y="84">{escape(title_suffix)}</text>')

    scored = sorted([m for m in models if m["avg"] is not None], key=lambda item: item["avg"], reverse=True)
    left = 250
    top = 130
    bar_h = 42
    gap = 22
    scale = 720

    for tick in range(0, 11):
        x = left + scale * (tick / 10)
        lines.append(f'<line class="grid" x1="{x}" y1="{top - 8}" x2="{x}" y2="{top + len(scored) * (bar_h + gap) - gap + 8}" />')
        lines.append(f'<text class="tiny" x="{x}" y="{top - 18}" text-anchor="middle">{tick / 10:.1f}</text>')

    for idx, model in enumerate(scored):
        y = top + idx * (bar_h + gap)
        color = MODEL_COLORS[model["slug"]]
        width_px = scale * model["avg"]
        lines.append(f'<text class="label" x="56" y="{y + 28}">{escape(model["label"])}</text>')
        lines.append(f'<rect x="{left}" y="{y}" width="{width_px:.1f}" height="{bar_h}" rx="14" fill="{color}" />')
        lines.append(f'<text class="value-light" x="{left + width_px - 16:.1f}" y="{y + 27}" text-anchor="end">{model["avg"]:.2f}</text>')
        lines.append(
            f'<text class="small" x="{left + width_px + 16:.1f}" y="{y + 27}">median {model["median_ms"] / 1000:.2f}s</text>'
        )

    gemma = next(model for model in models if model["slug"] == "gemma4_e4b")
    lines.append('<rect class="card" x="56" y="430" width="1148" height="54" rx="16" />')
    lines.append(f'<text class="label" x="76" y="462">{escape(gemma["label"])}</text>')
    lines.append('<text class="small" x="230" y="462">not ranked: local runtime failed before first token, so no fair average score exists yet</text>')
    save_svg(path, lines)


def chart_scatter(path: Path, models: list[dict[str, Any]], title_suffix: str) -> None:
    width, height = 1360, 620
    lines = svg_header(width, height, "Quality versus speed")
    lines.append('<text class="title" x="56" y="56">Quality vs Speed</text>')
    lines.append(f'<text class="subtitle" x="56" y="84">{escape(title_suffix)}</text>')

    left, top, chart_w, chart_h = 120, 120, 980, 400
    x_ticks = [1, 2, 5, 10, 20, 40, 80]
    y_ticks = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

    def x_pos(seconds: float) -> float:
        log_min, log_max = math.log10(1), math.log10(80)
        return left + (math.log10(seconds) - log_min) / (log_max - log_min) * chart_w

    def y_pos(score: float) -> float:
        return top + chart_h - (score - 0.5) / 0.5 * chart_h

    lines.append(f'<rect class="card" x="{left - 20}" y="{top - 20}" width="{chart_w + 40}" height="{chart_h + 40}" rx="20" />')
    for tick in x_ticks:
        x = x_pos(float(tick))
        lines.append(f'<line class="grid" x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{top + chart_h}" />')
        lines.append(f'<text class="tiny" x="{x:.1f}" y="{top + chart_h + 26}" text-anchor="middle">{tick}s</text>')
    for tick in y_ticks:
        y = y_pos(tick)
        lines.append(f'<line class="grid" x1="{left}" y1="{y:.1f}" x2="{left + chart_w}" y2="{y:.1f}" />')
        lines.append(f'<text class="tiny" x="{left - 18}" y="{y + 4:.1f}" text-anchor="end">{tick:.1f}</text>')

    lines.append(f'<line class="axis" x1="{left}" y1="{top + chart_h}" x2="{left + chart_w}" y2="{top + chart_h}" />')
    lines.append(f'<line class="axis" x1="{left}" y1="{top}" x2="{left}" y2="{top + chart_h}" />')
    lines.append(f'<text class="small" x="{left + chart_w / 2:.1f}" y="{top + chart_h + 54}" text-anchor="middle">Median latency per model (log scale)</text>')
    lines.append(f'<text class="small" x="{left - 80}" y="{top + chart_h / 2:.1f}" text-anchor="middle" transform="rotate(-90 {left - 80},{top + chart_h / 2:.1f})">Average claimed-task score</text>')

    for model in models:
        if model["avg"] is None or model["median_ms"] is None:
            continue
        x = x_pos(model["median_ms"] / 1000.0)
        y = y_pos(model["avg"])
        r = 12 if model["slug"] == "apfel" else 10
        color = MODEL_COLORS[model["slug"]]
        lines.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{color}" stroke="#111827" stroke-width="2" />')
        align = "end" if model["slug"] == "mistral_small_22b" else "start"
        dx = -16 if align == "end" else 16
        lines.append(f'<text class="label" x="{x + dx:.1f}" y="{y - 12:.1f}" text-anchor="{align}">{escape(model["label"])}</text>')
        lines.append(f'<text class="tiny" x="{x + dx:.1f}" y="{y + 6:.1f}" text-anchor="{align}">{model["avg"]:.2f} avg, {model["median_ms"] / 1000:.2f}s</text>')

    lines.append('<rect class="card" x="1130" y="140" width="180" height="114" rx="18" />')
    lines.append('<text class="label" x="1150" y="170">Read this chart</text>')
    lines.append('<text class="small" x="1150" y="196">Upper-left is better.</text>')
    lines.append('<text class="small" x="1150" y="220">Apfel wins speed.</text>')
    lines.append('<text class="small" x="1150" y="244">Qwen variants win quality.</text>')

    lines.append('<rect class="card" x="1130" y="280" width="180" height="126" rx="18" />')
    lines.append('<text class="label" x="1150" y="310">Blocked model</text>')
    lines.append('<text class="small" x="1150" y="336">Gemma 4 is omitted from the</text>')
    lines.append('<text class="small" x="1150" y="356">scatter because it could not</text>')
    lines.append('<text class="small" x="1150" y="376">complete a single valid run on</text>')
    lines.append('<text class="small" x="1150" y="396">this Mac.</text>')
    save_svg(path, lines)


def chart_latency(path: Path, models: list[dict[str, Any]], title_suffix: str) -> None:
    width, height = 1400, 760
    lines = svg_header(width, height, "Latency by task")
    lines.append('<text class="title" x="56" y="56">Latency by Task</text>')
    lines.append(f'<text class="subtitle" x="56" y="84">{escape(title_suffix)}</text>')

    scored = [model for model in models if model["status"] == "scored"]
    left = 180
    right = 1280
    top = 135
    group_h = 88
    group_gap = 18
    bar_h = 10
    x_ticks = [1, 5, 10, 20, 40, 80]
    chart_w = right - left

    def x_pos(seconds: float) -> float:
        log_min, log_max = math.log10(1), math.log10(80)
        return left + (math.log10(max(seconds, 1)) - log_min) / (log_max - log_min) * chart_w

    for tick in x_ticks:
        x = x_pos(float(tick))
        lines.append(f'<line class="grid" x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{top + len(LATENCY_TASKS) * (group_h + group_gap)}" />')
        lines.append(f'<text class="tiny" x="{x:.1f}" y="{top - 16}" text-anchor="middle">{tick}s</text>')

    draw_legend(lines, scored, 180, 640, cols=3)

    for group_idx, (slug, label) in enumerate(LATENCY_TASKS):
        y = top + group_idx * (group_h + group_gap)
        lines.append(f'<text class="label" x="56" y="{y + 32}">{escape(label)}</text>')
        for model_idx, model in enumerate(scored):
            seconds = model["latencies"][slug] / 1000.0
            x = x_pos(seconds)
            bar_y = y + 8 + model_idx * 12
            color = MODEL_COLORS[model["slug"]]
            lines.append(f'<line x1="{left}" y1="{bar_y}" x2="{x:.1f}" y2="{bar_y}" stroke="{color}" stroke-width="{bar_h}" stroke-linecap="round" />')
            lines.append(f'<text class="tiny" x="{x + 10:.1f}" y="{bar_y + 4:.1f}">{seconds:.1f}s</text>')

    lines.append(f'<text class="small" x="{left + chart_w / 2:.1f}" y="724" text-anchor="middle">Log-scaled seconds per task. Longer bars mean slower answers.</text>')
    save_svg(path, lines)


def chart_guardrails(path: Path, models: list[dict[str, Any]], title_suffix: str) -> None:
    width, height = 900, 420
    lines = svg_header(width, height, "Guardrail diagnostics")
    lines.append('<text class="title" x="56" y="56">Guardrail Diagnostics</text>')
    lines.append(f'<text class="subtitle" x="56" y="84">{escape(title_suffix)}</text>')
    left = 240
    top = 130
    cell_w = 220
    cell_h = 48

    for col_idx, (_, label) in enumerate(GUARDRAILS):
        x = left + col_idx * cell_w
        lines.append(f'<text class="label" x="{x + cell_w / 2:.1f}" y="{top - 22}" text-anchor="middle">{escape(label)}</text>')

    for row_idx, model in enumerate(models):
        y = top + row_idx * cell_h
        lines.append(f'<text class="label" x="56" y="{y + 30}">{escape(model["label"])}</text>')
        values = [model["guardrails"][slug] for slug, _ in GUARDRAILS]
        for col_idx, value in enumerate(values):
            x = left + col_idx * cell_w
            lines.append(f'<rect x="{x}" y="{y}" width="{cell_w - 14}" height="{cell_h - 10}" rx="12" fill="{score_color(value)}" />')
            cls = "value-light" if value is not None and value >= 0.62 else "value"
            lines.append(f'<text class="{cls}" x="{x + (cell_w - 14) / 2:.1f}" y="{y + 29}" text-anchor="middle">{escape(compact(value))}</text>')
    save_svg(path, lines)


def chart_runtime_status(path: Path, gemma_json: dict[str, Any]) -> None:
    width, height = 1320, 420
    lines = svg_header(width, height, "Gemma runtime compatibility")
    lines.append('<text class="title" x="56" y="56">Gemma 4 Runtime Compatibility</text>')
    lines.append('<text class="subtitle" x="56" y="84">A local execution status chart, not a quality chart.</text>')

    stages = [
        ("Default lab runtime", "Ollama 0.18.2", "Pull blocked", "#DC2626"),
        ("Temporary official runtime", "Ollama 0.20.4", "Pull succeeded", "#16A34A"),
        ("Inference on 11435", "api/chat", "Model failed to load", "#DC2626"),
        ("Inference on 11436", "cpu flags", "Model failed to load", "#DC2626"),
        ("Inference on 11437", "Metal flags", "Model failed to load", "#DC2626"),
    ]
    start_x = 60
    y = 180
    box_w = 220
    gap = 30

    for idx, (heading, subheading, status, color) in enumerate(stages):
        x = start_x + idx * (box_w + gap)
        if idx < len(stages) - 1:
            lines.append(f'<line x1="{x + box_w}" y1="{y + 44}" x2="{x + box_w + gap - 10}" y2="{y + 44}" stroke="#9CA3AF" stroke-width="4" stroke-linecap="round" />')
        lines.append(f'<rect class="card" x="{x}" y="{y}" width="{box_w}" height="132" rx="22" />')
        lines.append(f'<circle cx="{x + 30}" cy="{y + 34}" r="10" fill="{color}" />')
        lines.append(f'<text class="label" x="{x + 52}" y="{y + 40}">{escape(heading)}</text>')
        lines.append(f'<text class="small" x="{x + 24}" y="{y + 68}">{escape(subheading)}</text>')
        lines.append(f'<text class="value" x="{x + 24}" y="{y + 102}">{escape(status)}</text>')

    error_text = gemma_json["results"]["gemma4_e4b"]["shell_scripting"]["error"]
    lines.append('<rect class="card" x="60" y="336" width="1200" height="48" rx="16" />')
    lines.append('<text class="mono" x="82" y="366">Observed error: model failed to load before first token; temporary Ollama v0.20.4 runners crashed during Gemma 4 startup on this Mac.</text>')
    lines.append(f'<!-- raw error: {escape(str(error_text))} -->')
    save_svg(path, lines)


def chart_dashboard(path: Path, models: list[dict[str, Any]], title_suffix: str) -> None:
    width, height = 1480, 900
    lines = svg_header(width, height, "Benchmark dashboard")
    lines.append('<text class="title" x="56" y="56">Benchmark Dashboard</text>')
    lines.append(f'<text class="subtitle" x="56" y="84">{escape(title_suffix)}</text>')

    scored = [model for model in models if model["status"] == "scored"]
    ranked = sorted(scored, key=lambda item: item["avg"], reverse=True)
    fastest = min(scored, key=lambda item: item["median_ms"])
    most_reliable = max(scored, key=lambda item: (item["guardrails"]["unknown_refusal"] + item["guardrails"]["harmless_exactness"], item["avg"]))
    apfel = next(model for model in models if model["slug"] == "apfel")

    cards = [
        ("Top score", ranked[0]["label"], f"{ranked[0]['avg']:.2f} avg"),
        ("Fastest median", fastest["label"], f"{fastest['median_ms'] / 1000:.2f}s"),
        ("Best guardrails", most_reliable["label"], "2/2 diagnostics"),
        ("Apfel profile", "Speed-first sidecar", f"{apfel['avg']:.2f} avg, {apfel['median_ms'] / 1000:.2f}s"),
    ]
    for idx, (heading, body, detail) in enumerate(cards):
        x = 56 + idx * 344
        lines.append(f'<rect class="card" x="{x}" y="116" width="320" height="112" rx="24" />')
        lines.append(f'<text class="small" x="{x + 22}" y="148">{escape(heading)}</text>')
        lines.append(f'<text class="label" x="{x + 22}" y="182">{escape(body)}</text>')
        lines.append(f'<text class="value" x="{x + 22}" y="214">{escape(detail)}</text>')

    chart_heatmap_path = path.parent / "_tmp_heatmap.svg"
    chart_scatter_path = path.parent / "_tmp_scatter.svg"
    chart_heatmap(chart_heatmap_path, models, title_suffix)
    chart_scatter(chart_scatter_path, models, title_suffix)
    heatmap_body = chart_heatmap_path.read_text(encoding="utf-8")
    scatter_body = chart_scatter_path.read_text(encoding="utf-8")
    heatmap_inner = heatmap_body.split(">", 1)[1].rsplit("</svg>", 1)[0]
    scatter_inner = scatter_body.split(">", 1)[1].rsplit("</svg>", 1)[0]
    lines.append(f'<g transform="translate(40, 250) scale(0.64)">{heatmap_inner}</g>')
    lines.append(f'<g transform="translate(660, 250) scale(0.58)">{scatter_inner}</g>')
    chart_heatmap_path.unlink(missing_ok=True)
    chart_scatter_path.unlink(missing_ok=True)
    save_svg(path, lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate SVG charts from benchmark results.")
    parser.add_argument("--input", default=str(DEFAULT_JSON), help="Scored benchmark JSON.")
    parser.add_argument("--gemma-input", default=str(DEFAULT_GEMMA_JSON), help="Gemma blocked-run JSON.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Output directory for SVG charts.")
    args = parser.parse_args()

    scored_path = Path(args.input)
    gemma_path = Path(args.gemma_input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    scored_json, gemma_json, models = load_models(scored_path, gemma_path)
    title_suffix = f"Generated from {scored_json['generated_at']} benchmark data with Gemma 4 runtime findings appended"

    chart_dashboard(output_dir / "overview-dashboard.svg", models, title_suffix)
    chart_heatmap(output_dir / "master-capability-heatmap.svg", models, title_suffix)
    chart_average_ranking(output_dir / "master-average-score-ranking.svg", models, title_suffix)
    chart_scatter(output_dir / "master-quality-vs-speed.svg", models, title_suffix)
    chart_latency(output_dir / "master-latency-by-task.svg", models, title_suffix)
    chart_guardrails(output_dir / "master-guardrails.svg", models, title_suffix)
    chart_runtime_status(output_dir / "master-gemma-runtime-status.svg", gemma_json)

    index_lines = [
        "# Benchmark Charts",
        "",
        "- `overview-dashboard.svg`",
        "- `master-capability-heatmap.svg`",
        "- `master-average-score-ranking.svg`",
        "- `master-quality-vs-speed.svg`",
        "- `master-latency-by-task.svg`",
        "- `master-guardrails.svg`",
        "- `master-gemma-runtime-status.svg`",
        "",
        "These charts were generated from the scored Apfel/Ollama benchmark JSON plus the Gemma 4 blocked-run artifact.",
    ]
    (output_dir / "README.md").write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    print(f"Wrote charts to {output_dir}")


if __name__ == "__main__":
    main()
