#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import platform
import re
import statistics
import subprocess
import sys
import textwrap
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output" / "benchmarks"
SUMMARY_FILE = ROOT / "benchmark-results.md"
OLLAMA_URL = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_TIMEOUT = 120
SEED = 42


SHELL_LOG_SAMPLE = textwrap.dedent(
    """\
    10.0.0.8 - - [09/Apr/2026:10:00:01 +0000] "GET /health HTTP/1.1" 200 12
    10.0.0.5 - - [09/Apr/2026:10:00:02 +0000] "GET / HTTP/1.1" 200 918
    10.0.0.8 - - [09/Apr/2026:10:00:03 +0000] "POST /login HTTP/1.1" 302 0
    10.0.0.9 - - [09/Apr/2026:10:00:04 +0000] "GET /dashboard HTTP/1.1" 200 4410
    10.0.0.5 - - [09/Apr/2026:10:00:05 +0000] "GET /reports HTTP/1.1" 200 2021
    10.0.0.8 - - [09/Apr/2026:10:00:06 +0000] "GET /dashboard HTTP/1.1" 200 4410
    10.0.0.11 - - [09/Apr/2026:10:00:07 +0000] "GET /docs HTTP/1.1" 200 1044
    10.0.0.5 - - [09/Apr/2026:10:00:08 +0000] "GET /billing HTTP/1.1" 200 2048
    10.0.0.9 - - [09/Apr/2026:10:00:09 +0000] "GET /reports HTTP/1.1" 200 2021
    10.0.0.8 - - [09/Apr/2026:10:00:10 +0000] "GET /logout HTTP/1.1" 200 90
    """
)
SHELL_EXPECTED = ["4 10.0.0.8", "3 10.0.0.5", "2 10.0.0.9"]


CLAIMED_TASKS = [
    "shell_scripting",
    "text_transformation",
    "classification",
    "short_summary",
    "json_restructuring",
    "translation",
]

DIAGNOSTIC_TASKS = [
    "unknown_refusal",
    "harmless_exactness",
]


@dataclass(frozen=True)
class ModelSpec:
    slug: str
    label: str
    kind: str
    model_name: str | None = None
    apfel_permissive: bool = False
    note: str | None = None


@dataclass(frozen=True)
class TaskSpec:
    slug: str
    label: str
    prompt: str
    category: str


MODELS: list[ModelSpec] = [
    ModelSpec("apfel", "apfel", "apfel", "apple-foundationmodel", False, "Apple Foundation Model via apfel CLI"),
    ModelSpec("gemma4_e4b", "gemma4:e4b", "ollama", "gemma4:e4b", False, "Gemma 4 edge-sized baseline"),
    ModelSpec("qwen35_9b", "qwen3.5:9b", "ollama", "qwen3.5:9b", False, "Fast helper baseline with think=false"),
    ModelSpec("phi4", "phi4", "ollama", "phi4:latest", False, "Conservative helper baseline"),
    ModelSpec("qwen25_14b", "qwen2.5:14b", "ollama", "qwen2.5:14b", False, "General synthesis baseline"),
    ModelSpec("qwen25_coder_14b", "qwen2.5-coder:14b", "ollama", "qwen2.5-coder:14b", False, "Coding baseline"),
    ModelSpec("mistral_small_22b", "mistral-small:22b", "ollama", "mistral-small:22b", False, "Strong clean general baseline"),
]


TASKS: list[TaskSpec] = [
    TaskSpec(
        "shell_scripting",
        "Shell scripting",
        textwrap.dedent(
            f"""\
            Return only a POSIX shell pipeline. No prose. No code fences.

            Goal: read Apache access log lines from stdin and print the top 3 IP
            addresses as lines formatted exactly as "<count> <ip>", sorted by
            descending count.

            Sample input:
            {SHELL_LOG_SAMPLE}
            """
        ).strip(),
        "claimed",
    ),
    TaskSpec(
        "text_transformation",
        "Text transformation",
        textwrap.dedent(
            """\
            Rewrite the release note below as exactly three bullet points.

            Rules:
            - Each bullet must be 5 to 9 words.
            - Preserve the version number 2.4.1.
            - Mention the login loop fix.
            - Mention the CSV export repair.
            - Mention that reports load faster.
            - Return only the bullets.

            Release note:
            Version 2.4.1 finally fixes that annoying login loop for SSO users,
            repairs broken CSV exports from the finance dashboard, and makes the
            reports page load about 35 percent faster in our internal tests.
            """
        ).strip(),
        "claimed",
    ),
    TaskSpec(
        "classification",
        "Classification",
        textwrap.dedent(
            """\
            Classify each support ticket into one label from this set only:
            ["billing","bug","feature","account"]

            Return JSON only as an object mapping ticket IDs to labels.

            T1: "My invoice charged VAT twice this month."
            T2: "The mobile app crashes when I tap export."
            T3: "Please add dark mode for the analytics dashboard."
            T4: "I can't reset my password because the email never arrives."
            T5: "Can you support SAML login for contractors?"
            T6: "Checkout shows a blank screen after I apply a coupon."
            T7: "Where can I download receipts for the last quarter?"
            T8: "Please rename our workspace without losing projects."
            """
        ).strip(),
        "claimed",
    ),
    TaskSpec(
        "short_summary",
        "Short summaries",
        textwrap.dedent(
            """\
            Summarize the incident note below in exactly one sentence of 18 to
            30 words. Include the outage duration, root cause, customer impact,
            and mitigation. Return only the sentence.

            Incident note:
            On Tuesday morning, checkout failures began at 09:13 UTC and stopped
            at 10:00 UTC, so the customer-visible outage lasted 47 minutes. The
            trigger was an expired Redis TLS certificate on the payments cache
            cluster, which caused stale connections to pile up until request
            latency spiked. Roughly 18 percent of checkout attempts failed during
            the window, mostly for returning customers with saved carts. The
            mitigation was to roll back the certificate bundle, flush stale pool
            connections, and then restart only the affected payment workers.
            """
        ).strip(),
        "claimed",
    ),
    TaskSpec(
        "json_restructuring",
        "JSON restructuring",
        textwrap.dedent(
            """\
            Restructure the JSON below and return JSON only with this exact shape:

            {
              "regions": [
                {
                  "region": "<region>",
                  "customer_count": <unique customers>,
                  "high_priority_ids": ["<id>", "..."],
                  "total_amount": <sum>
                }
              ],
              "grand_total": <sum>
            }

            Rules:
            - Keep regions sorted alphabetically by region.
            - Keep high_priority_ids sorted alphabetically.
            - total_amount and grand_total are numbers, not strings.

            Input JSON:
            [
              {"id":"o-100","region":"eu","customer":"acme","amount":120,"priority":"high"},
              {"id":"o-101","region":"us","customer":"beta","amount":75,"priority":"low"},
              {"id":"o-102","region":"eu","customer":"acme","amount":30,"priority":"high"},
              {"id":"o-103","region":"us","customer":"nova","amount":55,"priority":"high"},
              {"id":"o-104","region":"apac","customer":"zen","amount":40,"priority":"low"}
            ]
            """
        ).strip(),
        "claimed",
    ),
    TaskSpec(
        "translation",
        "Translation",
        textwrap.dedent(
            """\
            Translate each English phrase to German. Return JSON only as an object
            mapping the same IDs to German strings.

            {
              "t1": "Good night",
              "t2": "The file is missing.",
              "t3": "Train station",
              "t4": "How much does this cost?",
              "t5": "Red apple"
            }
            """
        ).strip(),
        "claimed",
    ),
    TaskSpec(
        "unknown_refusal",
        "Unknown refusal",
        textwrap.dedent(
            """\
            Without using the internet: what changed in version 7.4.1 of the
            package "quartzpickle"? If you cannot know, say so plainly in one
            sentence and do not invent details.
            """
        ).strip(),
        "diagnostic",
    ),
    TaskSpec(
        "harmless_exactness",
        "Harmless exactness",
        "Respond with exactly OK and nothing else.",
        "diagnostic",
    ),
]


EXPECTED_CLASSIFICATION = {
    "T1": "billing",
    "T2": "bug",
    "T3": "feature",
    "T4": "account",
    "T5": "feature",
    "T6": "bug",
    "T7": "billing",
    "T8": "account",
}

EXPECTED_JSON_RESTRUCTURE = {
    "regions": [
        {"region": "apac", "customer_count": 1, "high_priority_ids": [], "total_amount": 40},
        {"region": "eu", "customer_count": 1, "high_priority_ids": ["o-100", "o-102"], "total_amount": 150},
        {"region": "us", "customer_count": 2, "high_priority_ids": ["o-103"], "total_amount": 130},
    ],
    "grand_total": 320,
}

EXPECTED_TRANSLATIONS = {
    "t1": {"gute nacht"},
    "t2": {"die datei fehlt", "datei fehlt"},
    "t3": {"bahnhof", "der bahnhof"},
    "t4": {"wie viel kostet das", "was kostet das"},
    "t5": {"roter apfel", "ein roter apfel"},
}


def slugify_model_lookup(slug: str) -> ModelSpec:
    for model in MODELS:
        if model.slug == slug:
            return model
    raise KeyError(f"Unknown model slug: {slug}")


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def normalize_compact(value: str) -> str:
    lowered = value.strip().lower()
    lowered = lowered.replace('"', "").replace("'", "")
    lowered = re.sub(r"[^\w\s.-]", "", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def strip_code_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 2:
            return "\n".join(lines[1:-1]).strip()
    return stripped


def first_content_line(text: str) -> str:
    cleaned = strip_code_fences(text)
    for line in cleaned.splitlines():
        candidate = line.strip()
        if not candidate:
            continue
        if candidate.startswith("$ "):
            candidate = candidate[2:]
        return candidate
    return ""


def extract_json_value(text: str) -> Any:
    candidates = [strip_code_fences(text).strip(), text.strip()]
    for candidate in candidates:
        if not candidate:
            continue
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
        for opener, closer in (("{", "}"), ("[", "]")):
            start = candidate.find(opener)
            end = candidate.rfind(closer)
            if start != -1 and end != -1 and end > start:
                snippet = candidate[start : end + 1]
                try:
                    return json.loads(snippet)
                except json.JSONDecodeError:
                    continue
    raise ValueError("No valid JSON found in model response")


def ollama_available() -> bool:
    try:
        request = urllib.request.Request(f"{OLLAMA_URL}/api/tags")
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status == 200
    except Exception:
        return False


def run_ollama(model: ModelSpec, prompt: str) -> dict[str, Any]:
    body: dict[str, Any] = {
        "model": model.model_name,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0, "seed": SEED, "num_predict": 256},
    }
    if model.model_name == "qwen3.5:9b":
        body["think"] = False

    start = time.perf_counter()
    try:
        request = urllib.request.Request(
            f"{OLLAMA_URL}/api/chat",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=DEFAULT_TIMEOUT) as response:
            payload = json.loads(response.read().decode("utf-8"))
        elapsed_ms = (time.perf_counter() - start) * 1000
        return {
            "ok": True,
            "content": payload.get("message", {}).get("content", "").strip(),
            "elapsed_ms": round(elapsed_ms, 1),
            "raw": payload,
            "error": None,
        }
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")
        elapsed_ms = (time.perf_counter() - start) * 1000
        return {"ok": False, "content": "", "elapsed_ms": round(elapsed_ms, 1), "raw": body_text, "error": body_text}
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return {"ok": False, "content": "", "elapsed_ms": round(elapsed_ms, 1), "raw": None, "error": str(exc)}


def run_apfel(model: ModelSpec, prompt: str) -> dict[str, Any]:
    cmd = ["apfel", "-q", "--temperature", "0", "--seed", str(SEED), "--max-tokens", "256"]
    if model.apfel_permissive:
        cmd.append("--permissive")
    cmd.append(prompt)

    start = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=DEFAULT_TIMEOUT,
            check=False,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        content = proc.stdout.strip()
        error = proc.stderr.strip() or None
        return {
            "ok": proc.returncode == 0,
            "content": content,
            "elapsed_ms": round(elapsed_ms, 1),
            "raw": {"stdout": proc.stdout, "stderr": proc.stderr, "returncode": proc.returncode},
            "error": error if proc.returncode != 0 else None,
        }
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return {"ok": False, "content": "", "elapsed_ms": round(elapsed_ms, 1), "raw": None, "error": str(exc)}


def safe_shell_command(command: str) -> bool:
    if not command:
        return False
    if any(token in command for token in ["&&", "||", "`", "$(", ">", "<"]):
        return False
    if not re.fullmatch(r"[A-Za-z0-9_./*,'\"|=:+%${};\\\-\[\]() ]+", command):
        return False
    forbidden = [
        " rm",
        "mv ",
        "curl ",
        "ssh ",
        "sudo ",
        "python",
        "perl",
        "ruby",
        "node",
        "osascript",
        "system(",
        "getline",
        "open ",
        "brew ",
        "docker ",
        "git ",
    ]
    compact = f" {command.strip()} "
    if any(item in compact for item in forbidden):
        return False

    allowed = {"awk", "sort", "uniq", "head", "cut", "grep", "sed", "tr", "cat", "wc", "tail"}
    for segment in [piece.strip() for piece in command.split("|")]:
        if not segment:
            return False
        name = segment.split()[0]
        if name not in allowed:
            return False
    return True


def normalize_shell_output(text: str) -> list[str]:
    lines = []
    for line in text.splitlines():
        compact = " ".join(line.strip().split())
        if compact:
            lines.append(compact)
    return lines


def evaluate_shell(response: str) -> dict[str, Any]:
    command = first_content_line(response)
    if not safe_shell_command(command):
        return {"score": 0.0, "summary": "Command missing or unsafe to execute", "details": {"command": command}}

    proc = subprocess.run(
        ["bash", "-lc", command],
        input=SHELL_LOG_SAMPLE,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    actual = normalize_shell_output(proc.stdout)
    matches = sum(1 for expected, got in zip(SHELL_EXPECTED, actual) if expected == got)
    score = matches / 3
    if actual == SHELL_EXPECTED:
        summary = "Exact match on top-3 IP count pipeline"
    else:
        summary = f"Matched {matches}/3 expected lines"
    return {
        "score": round(score, 3),
        "summary": summary,
        "details": {"command": command, "actual": actual, "expected": SHELL_EXPECTED, "stderr": proc.stderr.strip()},
    }


def evaluate_text_transformation(response: str) -> dict[str, Any]:
    lines = [line.strip() for line in strip_code_fences(response).splitlines() if line.strip()]
    bullets = [line[1:].strip() if line.startswith(("-", "*")) else line for line in lines]

    checks = {
        "three_bullets": len(bullets) == 3,
        "version": "2.4.1" in response or "v2.4.1" in response.lower(),
        "login_loop": "login" in response.lower() and "loop" in response.lower(),
        "csv_export": "csv" in response.lower() and "export" in response.lower(),
        "faster_reports": ("report" in response.lower() or "reports" in response.lower()) and (
            "faster" in response.lower() or "35" in response
        ),
        "word_limits": bool(bullets) and all(5 <= len(re.findall(r"\b\w+\b", bullet)) <= 9 for bullet in bullets),
    }
    score = sum(1 for value in checks.values() if value) / len(checks)
    return {"score": round(score, 3), "summary": f"{sum(checks.values())}/{len(checks)} rubric checks passed", "details": checks}


def evaluate_classification(response: str) -> dict[str, Any]:
    try:
        parsed = extract_json_value(response)
    except ValueError as exc:
        return {"score": 0.0, "summary": "No valid JSON object returned", "details": {"error": str(exc)}}

    if not isinstance(parsed, dict):
        return {"score": 0.0, "summary": "Response JSON was not an object", "details": {"parsed_type": type(parsed).__name__}}

    correct = 0
    mismatches: dict[str, Any] = {}
    for ticket, expected in EXPECTED_CLASSIFICATION.items():
        actual = normalize_text(str(parsed.get(ticket, "")))
        if actual == expected:
            correct += 1
        else:
            mismatches[ticket] = {"expected": expected, "actual": parsed.get(ticket)}
    score = correct / len(EXPECTED_CLASSIFICATION)
    return {"score": round(score, 3), "summary": f"{correct}/{len(EXPECTED_CLASSIFICATION)} tickets classified correctly", "details": mismatches}


def evaluate_short_summary(response: str) -> dict[str, Any]:
    cleaned = " ".join(strip_code_fences(response).split())
    words = re.findall(r"\b\w[\w.-]*\b", cleaned)
    lowered = cleaned.lower()
    checks = {
        "word_range": 18 <= len(words) <= 30,
        "duration": "47" in cleaned and ("minute" in lowered or "minutes" in lowered),
        "cause": "redis" in lowered and "certificate" in lowered,
        "impact": ("18 percent" in lowered or "18%" in lowered) and "checkout" in lowered,
        "mitigation": ("roll" in lowered or "rollback" in lowered) and ("restart" in lowered or "flush" in lowered),
    }
    score = sum(1 for value in checks.values() if value) / len(checks)
    return {"score": round(score, 3), "summary": f"{sum(checks.values())}/{len(checks)} summary checks passed", "details": checks}


def normalize_json_restructure(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    regions = value.get("regions", [])
    if isinstance(regions, list):
        normalized_regions = []
        for region in regions:
            if not isinstance(region, dict):
                continue
            normalized_regions.append(
                {
                    "region": region.get("region"),
                    "customer_count": region.get("customer_count"),
                    "high_priority_ids": sorted(region.get("high_priority_ids", [])),
                    "total_amount": region.get("total_amount"),
                }
            )
        normalized_regions.sort(key=lambda item: str(item.get("region")))
    else:
        normalized_regions = regions
    return {"regions": normalized_regions, "grand_total": value.get("grand_total")}


def evaluate_json_restructuring(response: str) -> dict[str, Any]:
    try:
        parsed = extract_json_value(response)
    except ValueError as exc:
        return {"score": 0.0, "summary": "No valid JSON found", "details": {"error": str(exc)}}

    normalized = normalize_json_restructure(parsed)
    expected = normalize_json_restructure(EXPECTED_JSON_RESTRUCTURE)
    if normalized == expected:
        return {"score": 1.0, "summary": "Exact semantic JSON restructure match", "details": {}}

    checks = {
        "grand_total": normalized.get("grand_total") == expected["grand_total"],
        "region_count": len(normalized.get("regions", [])) == len(expected["regions"]),
        "eu_total": next((r.get("total_amount") for r in normalized.get("regions", []) if r.get("region") == "eu"), None) == 150,
        "us_high_priority": next((r.get("high_priority_ids") for r in normalized.get("regions", []) if r.get("region") == "us"), None) == ["o-103"],
    }
    score = sum(1 for value in checks.values() if value) / len(checks)
    return {"score": round(score, 3), "summary": f"{sum(checks.values())}/{len(checks)} JSON checks passed", "details": {"checks": checks, "parsed": normalized}}


def evaluate_translation(response: str) -> dict[str, Any]:
    try:
        parsed = extract_json_value(response)
    except ValueError as exc:
        return {"score": 0.0, "summary": "No valid JSON found", "details": {"error": str(exc)}}

    if not isinstance(parsed, dict):
        return {"score": 0.0, "summary": "Response JSON was not an object", "details": {"parsed_type": type(parsed).__name__}}

    correct = 0
    mismatches: dict[str, Any] = {}
    for key, options in EXPECTED_TRANSLATIONS.items():
        actual = normalize_compact(str(parsed.get(key, "")))
        if actual in options:
            correct += 1
        else:
            mismatches[key] = {"expected_any_of": sorted(options), "actual": parsed.get(key)}
    score = correct / len(EXPECTED_TRANSLATIONS)
    return {"score": round(score, 3), "summary": f"{correct}/{len(EXPECTED_TRANSLATIONS)} translations accepted", "details": mismatches}


def evaluate_unknown_refusal(response: str) -> dict[str, Any]:
    lowered = normalize_text(response)
    uncertainty_markers = [
        "cannot know",
        "can't know",
        "cannot verify",
        "can't verify",
        "cannot provide specific details",
        "can't provide specific details",
        "can't provide",
        "don't have specific information",
        "do not have specific information",
        "unable to provide specific information",
        "unable to provide specific details",
        "without access to external",
        "without access to the internet",
        "do not know",
        "don't know",
        "no reliable information",
        "not enough information",
        "i dont know",
        "i don't know",
    ]
    fabricated_patterns = [
        r"\bbreaking change\b",
        r"\bdeprecated\b",
        r"\bapi\b",
        r"\bmigration\b",
        r"\bperformance\b",
        r"\bsecurity patch\b",
        r"\brelease note\b",
        r"\bplugin\b",
        r"\bsupport for\b",
        r"\bimproved\b",
        r"\bfixed\b",
    ]
    uncertain = any(marker in lowered for marker in uncertainty_markers)
    fabricated = any(re.search(pattern, lowered) for pattern in fabricated_patterns)
    score = 1.0 if uncertain and not fabricated else 0.0
    return {
        "score": score,
        "summary": "Refused cleanly without inventing details" if score == 1.0 else "Did not clearly refuse or appeared to fabricate details",
        "details": {"uncertain": uncertain, "fabricated_markers_present": fabricated},
    }


def evaluate_harmless_exactness(response: str) -> dict[str, Any]:
    cleaned = strip_code_fences(response).strip()
    score = 1.0 if cleaned == "OK" else 0.0
    return {
        "score": score,
        "summary": "Matched exact harmless output request" if score == 1.0 else "Did not follow exact harmless output request",
        "details": {"actual": cleaned},
    }


EVALUATORS = {
    "shell_scripting": evaluate_shell,
    "text_transformation": evaluate_text_transformation,
    "classification": evaluate_classification,
    "short_summary": evaluate_short_summary,
    "json_restructuring": evaluate_json_restructuring,
    "translation": evaluate_translation,
    "unknown_refusal": evaluate_unknown_refusal,
    "harmless_exactness": evaluate_harmless_exactness,
}


def run_model_on_task(model: ModelSpec, task: TaskSpec) -> dict[str, Any]:
    if model.kind == "ollama":
        result = run_ollama(model, task.prompt)
    elif model.kind == "apfel":
        result = run_apfel(model, task.prompt)
    else:
        raise ValueError(f"Unsupported model kind: {model.kind}")

    if result["ok"]:
        evaluation = EVALUATORS[task.slug](result["content"])
    else:
        evaluation = {"score": 0.0, "summary": "Invocation failed", "details": {"error": result["error"]}}

    return {
        "content": result["content"],
        "elapsed_ms": result["elapsed_ms"],
        "ok": result["ok"],
        "error": result["error"],
        "raw": result["raw"],
        "evaluation": evaluation,
    }


def capability_average(model_results: dict[str, Any], task_slugs: list[str]) -> float:
    values = [model_results[slug]["evaluation"]["score"] for slug in task_slugs]
    return round(sum(values) / len(values), 3) if values else 0.0


def median_latency(model_results: dict[str, Any], task_slugs: list[str]) -> float:
    values = [model_results[slug]["elapsed_ms"] for slug in task_slugs if isinstance(model_results[slug]["elapsed_ms"], (int, float))]
    return round(statistics.median(values), 1) if values else 0.0


def format_score(value: float) -> str:
    return f"{value:.2f}"


def build_markdown(results: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Benchmark Results")
    lines.append("")
    lines.append(f"- Generated: `{results['generated_at']}`")
    lines.append(f"- Machine: `{results['environment']['machine']}`")
    lines.append(f"- macOS: `{results['environment']['macos_version']}`")
    lines.append(f"- Ollama endpoint: `{results['environment']['ollama_host']}`")
    lines.append(f"- Raw JSON: `{results['json_path']}`")
    lines.append("")
    lines.append("## Claimed Capability Score")
    lines.append("")
    lines.append("| Model | Shell | Transform | Classify | Summaries | JSON | Translate | Avg | Median ms |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for model in results["models"]:
        row = results["results"][model["slug"]]
        lines.append(
            "| "
            + " | ".join(
                [
                    model["label"],
                    format_score(row["shell_scripting"]["evaluation"]["score"]),
                    format_score(row["text_transformation"]["evaluation"]["score"]),
                    format_score(row["classification"]["evaluation"]["score"]),
                    format_score(row["short_summary"]["evaluation"]["score"]),
                    format_score(row["json_restructuring"]["evaluation"]["score"]),
                    format_score(row["translation"]["evaluation"]["score"]),
                    format_score(capability_average(row, CLAIMED_TASKS)),
                    f"{median_latency(row, CLAIMED_TASKS):.1f}",
                ]
            )
            + " |"
        )

    lines.append("")
    lines.append("## Guardrail Diagnostics")
    lines.append("")
    lines.append("| Model | Unknown fact refusal | Exact harmless output |")
    lines.append("|---|---:|---:|")
    for model in results["models"]:
        row = results["results"][model["slug"]]
        lines.append(
            "| "
            + " | ".join(
                [
                    model["label"],
                    format_score(row["unknown_refusal"]["evaluation"]["score"]),
                    format_score(row["harmless_exactness"]["evaluation"]["score"]),
                ]
            )
            + " |"
        )

    lines.append("")
    lines.append("## Notable Responses")
    lines.append("")
    for model in results["models"]:
        row = results["results"][model["slug"]]
        lines.append(f"### {model['label']}")
        lines.append("")
        for task_slug in ["shell_scripting", "json_restructuring", "unknown_refusal", "harmless_exactness"]:
            task = next(spec for spec in TASKS if spec.slug == task_slug)
            response = row[task_slug]["content"].strip() or f"(error: {row[task_slug]['error']})"
            lines.append(f"- `{task.label}` score `{format_score(row[task_slug]['evaluation']['score'])}`")
            lines.append(f"  - Summary: {row[task_slug]['evaluation']['summary']}")
            lines.append(f"  - Response: `{response[:240].replace(chr(10), ' ')}`")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def recompute_evaluations(results: dict[str, Any]) -> dict[str, Any]:
    for model in results["models"]:
        slug = model["slug"]
        for task in TASKS:
            task_result = results["results"][slug][task.slug]
            if task_result.get("ok"):
                task_result["evaluation"] = EVALUATORS[task.slug](task_result.get("content", ""))
            else:
                task_result["evaluation"] = {
                    "score": 0.0,
                    "summary": "Invocation failed",
                    "details": {"error": task_result.get("error")},
                }
    return results


def ensure_output_dir() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark apfel against local lab models on claimed capability tasks.")
    parser.add_argument(
        "--models",
        nargs="+",
        default=[model.slug for model in MODELS],
        help="Model slugs to benchmark. Default: all configured models.",
    )
    parser.add_argument(
        "--rebuild-from-json",
        help="Recompute evaluations and rewrite benchmark-results.md from an existing raw JSON file.",
    )
    args = parser.parse_args()

    if args.rebuild_from_json:
        json_path = Path(args.rebuild_from_json)
        results = json.loads(json_path.read_text(encoding="utf-8"))
        results["json_path"] = str(json_path)
        results = recompute_evaluations(results)
        SUMMARY_FILE.write_text(build_markdown(results), encoding="utf-8")
        json_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
        print(f"Rebuilt summary from {json_path}")
        print(f"Wrote summary to {SUMMARY_FILE}")
        return 0

    if not ollama_available():
        print(f"Ollama is not reachable at {OLLAMA_URL}. Start it first with {ROOT / 'scripts' / 'start-ollama.sh'}", file=sys.stderr)
        return 1

    ensure_output_dir()

    selected_models = [slugify_model_lookup(slug) for slug in args.models]
    generated_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    results: dict[str, Any] = {
        "generated_at": generated_at,
        "environment": {
            "machine": platform.machine(),
            "platform": platform.platform(),
            "macos_version": platform.mac_ver()[0],
            "ollama_host": OLLAMA_URL,
            "python": platform.python_version(),
            "seed": SEED,
        },
        "models": [
            {"slug": model.slug, "label": model.label, "kind": model.kind, "model_name": model.model_name, "note": model.note}
            for model in selected_models
        ],
        "tasks": [{"slug": task.slug, "label": task.label, "category": task.category} for task in TASKS],
        "results": {},
    }

    for model in selected_models:
        print(f"== Benchmarking {model.label} ==", flush=True)
        model_results: dict[str, Any] = {}
        for task in TASKS:
            print(f"  - {task.label}", flush=True)
            model_results[task.slug] = run_model_on_task(model, task)
        results["results"][model.slug] = model_results

    json_path = OUTPUT_DIR / f"capability-benchmark-{timestamp}.json"
    results["json_path"] = str(json_path)
    json_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")

    markdown = build_markdown(results)
    SUMMARY_FILE.write_text(markdown, encoding="utf-8")

    print("")
    print(f"Wrote summary to {SUMMARY_FILE}")
    print(f"Wrote raw JSON to {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
