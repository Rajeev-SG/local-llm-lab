# Workflow smoke artifacts (issue #18)

Snapshots produced by `scripts/run-workflow-smoke.py`, not canonical fixtures.

- `gate-result.json` — the decision-gate output (latency leg on the shared 8-task
  suite; the workflow fixtures themselves supply pass/fail only).
- `gate-result-vs-coder.json` — same, against the coding leader.
- `memory-evidence.json` — peak RSS and machine memory-pressure capture.
- `work/` — **the model's edited files, kept only as evidence of what it changed.**
  The canonical, deliberately-broken fixtures live in `fixtures/`. Files here will
  drift from `fixtures/` by design and must not be edited directly.
