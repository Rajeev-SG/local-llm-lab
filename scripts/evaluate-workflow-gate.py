#!/usr/bin/env python3
"""Apply the issue #18 decision gate to a workflow-smoke result JSON.

PASS threshold: a case counts as a full pass only at score >= 0.8 (or an
objective `success: true`). Scores in [0.5, 0.8) are recorded as PARTIAL and do
not count toward the >=4/5 leg; the report distinguishes full and partial
passes so the classification is reproducible.

Gate (from issue #18). Two evidence layers, deliberately separated:

  - Workflow layer (fixtures/coding-fix, coding-loop, browser, repo-comprehension,
    long-context): bespoke fixtures introduced by this PR. They are NEW, so no
    comparator has run them; they contribute pass/fail and rescue counts only, not
    the latency ratio.
  - Latency layer: the shared 8-task capability suite
    (scripts/benchmark-capabilities.py), which the Qwen comparators HAVE run. That
    is the same-task basis for the <=1.5x wall-clock leg.

Gate (from issue #18):
  - Workflow candidate : >=4/5 pass, <=1 human rescue, median wall-clock <=1.5x comparator.
  - Background/helper  : 3/5 pass, or materially slower, but reliable enough for
                         review/triage/summarisation/background loops.
  - Do not integrate   : <=2/5 pass, repeated tool-loop failures, or resource/runtime
                         friction outweighs zero-marginal-cost benefit.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def median(values: list[float]) -> float | None:
    values = sorted(v for v in values if v is not None)
    if not values:
        return None
    mid = len(values) // 2
    return values[mid] if len(values) % 2 else (values[mid - 1] + values[mid]) / 2


PASS_THRESHOLD = 0.8
PARTIAL_THRESHOLD = 0.5


def classify(test: dict) -> str:
    if test.get("success") is True:
        return "pass"
    if test.get("success") is False:
        return "fail"
    score = test.get("evaluation", {}).get("score", 0)
    if score >= PASS_THRESHOLD:
        return "pass"
    if score >= PARTIAL_THRESHOLD:
        return "partial"
    return "fail"


def test_passed(test: dict) -> bool:
    return classify(test) == "pass"


def code_wall(test: dict) -> float | None:
    return test.get("wall_seconds") or test.get("elapsed_seconds")


def evaluate(subject: dict, comparator: dict | None) -> dict:
    """Classify from the workflow fixtures. Latency is added later (same-task suite)."""
    tests = subject["tests"]
    classes = {name: classify(t) for name, t in tests.items()}
    full_passes = sum(1 for c in classes.values() if c == "pass")
    partials = [name for name, c in classes.items() if c == "partial"]
    fails = [name for name, c in classes.items() if c == "fail"]
    tool_failures = sum(t.get("tool_failures", 0) for t in tests.values())
    rescues = subject.get("summary", {}).get("human_rescues", 0)

    return {
        "pass_threshold": PASS_THRESHOLD,
        "tests_run": len(tests),
        "tests_full_passes": full_passes,
        "partial_tests": partials,
        "failed_tests": fails,
        "human_rescues": rescues,
        "tool_failures_total": tool_failures,
        "limbs": {
            "passes_ge_4_of_5": full_passes >= 4,
            "rescue_le_1": rescues <= 1,
        },
        "wall_clock_ratio": None,
        "verdict": ("WORKFLOW_CANDIDATE" if full_passes >= 4 and rescues <= 1
                    else "BACKGROUND_HELPER_ONLY" if full_passes >= 3
                    else "DO_NOT_INTEGRATE"),
    }


def capability_median_ms(artifact: Path, slug: str) -> float | None:
    """Median latency of the shared 8-task capability suite for one build."""
    data = load(artifact)
    results = (data.get("results") or {}).get(slug) or {}
    latencies = sorted(
        float(t["elapsed_ms"]) for t in results.values()
        if isinstance(t.get("elapsed_ms"), (int, float))
    )
    if not latencies:
        return None
    mid = len(latencies) // 2
    return latencies[mid] if len(latencies) % 2 else (latencies[mid - 1] + latencies[mid]) / 2


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("subject", type=Path)
    ap.add_argument("--comparator", type=Path, default=None)
    ap.add_argument("--subject-capability", type=Path, default=None,
                    help="capability artifact for the subject (same-task latency basis)")
    ap.add_argument("--subject-slug", default=None)
    ap.add_argument("--comparator-capability", type=Path, default=None)
    ap.add_argument("--comparator-slug", default=None)
    ap.add_argument("--comparator-label", default=None)
    ap.add_argument("--workflow-only", action="store_true",
                    help="classify from workflow results alone (no latency leg)")
    args = ap.parse_args()
    subject = load(args.subject)
    comparator = load(args.comparator) if args.comparator else None
    result = evaluate(subject, comparator)

    # Same-task latency leg from the shared capability suite.
    if args.subject_capability and args.comparator_capability:
        s_med = capability_median_ms(args.subject_capability, args.subject_slug)
        c_med = capability_median_ms(args.comparator_capability, args.comparator_slug)
        ratio = round(s_med / c_med, 2) if s_med and c_med else None
        result["latency_basis"] = "shared 8-task capability suite (same tasks + evaluators)"
        result["subject_capability_median_ms"] = s_med
        result["comparator_capability_median_ms"] = c_med
        result["comparator_label"] = args.comparator_label
        result["wall_clock_ratio"] = ratio
        within = ratio is not None and ratio <= 1.5
        result["limbs"]["within_1.5x_same_task_comparator"] = within
        if result["tests_full_passes"] >= 4 and result["human_rescues"] <= 1 and within:
            result["verdict"] = "WORKFLOW_CANDIDATE"
        elif result["tests_full_passes"] >= 3:
            result["verdict"] = "BACKGROUND_HELPER_ONLY"
        else:
            result["verdict"] = "DO_NOT_INTEGRATE"
    else:
        result["latency_basis"] = "workflow fixtures only (no same-task comparator; latency leg omitted)"
        result["limbs"]["within_1.5x_same_task_comparator"] = None

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
