# Workflow smoke artifacts (issue #18)

Snapshots produced by `scripts/run-workflow-smoke.py`, not canonical fixtures.

- `gate-result.json` — the decision-gate output (latency leg on the shared 8-task
  suite; the workflow fixtures themselves supply pass/fail only).
- `gate-result-vs-coder.json` — same, against the coding leader.
- `memory-evidence.json` — peak RSS and machine memory-pressure capture.
- `work/` — **the model's edited files, kept only as evidence of what it changed.**
  The canonical, deliberately-broken fixtures live in `fixtures/`. Files here will
  drift from `fixtures/` by design and must not be edited directly.

## Provenance

`site/src/current-models.json` is the same payload as `output/inventory/current-models.json`;
both are produced by `scripts/generate-current-model-guide.py`. This snapshot's Bonsai
entry was added by hand because regenerating the full inventory would reap ~22 models
that are in the 9 Sep snapshot but no longer on this Mac (unrelated drift), which would
misrepresent the guide. If you regenerate, expect those removals.
