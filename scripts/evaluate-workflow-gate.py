#!/usr/bin/env python3
"""Apply the issue #18 decision gate to a workflow-smoke result JSON.

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


def test_passed(test: dict) -> bool:
    if "success" in test:
        return bool(test["success"])
    return test.get("evaluation", {}).get("score", 0) >= 0.5


def code_wall(test: dict) -> float | None:
    return test.get("wall_seconds") or test.get("elapsed_seconds")


def evaluate(subject: dict, comparator: dict | None) -> dict:
    tests = subject["tests"]
    passed = sum(1 for t in tests.values() if test_passed(t))
    n = len(tests)
    coding = [t for name, t in tests.items() if name.startswith(("1_", "3_"))]
    tool_failures = sum(t.get("tool_failures", 0) for t in tests.values())
    fails = [name for name, t in tests.items() if not test_passed(t)]

    subject_wall = median([code_wall(t) for t in coding])
    comparator_wall = None
    if comparator:
        comp_tests = comparator.get("tests", {})
        comp_coding = [comp_tests[name] for name in comp_tests
                       if name.startswith(("1_", "3_")) and code_wall(comp_tests[name]) is not None]
        comparator_wall = median([code_wall(t) for t in comp_coding])

    ratio = None
    if subject_wall and comparator_wall:
        ratio = round(subject_wall / comparator_wall, 2)

    if passed >= 4 and tool_failures == 0 and (ratio is None or ratio <= 1.5):
        verdict = "WORKFLOW_CANDIDATE"
    elif passed >= 3:
        verdict = "BACKGROUND_HELPER_ONLY"
    else:
        verdict = "DO_NOT_INTEGRATE"

    return {
        "tests_run": n,
        "tests_passed": passed,
        "failed_tests": fails,
        "tool_failures_total": tool_failures,
        "subject_median_coding_wall_s": subject_wall,
        "comparator_median_coding_wall_s": comparator_wall,
        "wall_clock_ratio": ratio,
        "verdict": verdict,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("subject", type=Path)
    ap.add_argument("--comparator", type=Path, default=None)
    args = ap.parse_args()
    subject = load(args.subject)
    comparator = load(args.comparator) if args.comparator else None
    result = evaluate(subject, comparator)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
