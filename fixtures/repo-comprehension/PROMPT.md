# Repo comprehension fixture

You are given a trimmed slice of the `local-llm-lab` repo (a local-model benchmark lab).
Read it and answer the question below.

## Question

A user reports: "A newly benchmarked model has a results row in the leaderboard JSON, but
its five-workflow smoke report never shows up in the published guide / leaderboard."

Identify **the single file** where the fix belongs, and name **the function** that
decides which benchmark artifacts and builds get included in the published leaderboard.
Then, in one sentence, say why the two most plausible alternative files are the wrong
home for that fix.

Return your answer as three labelled lines: `FILE:`, `FUNCTION:`, `WHY:`. No code fences.

## Repo slice (key excerpts)

### scripts/generate-overall-leaderboard.py  (excerpt)
```python
BENCHMARK_DIR = ROOT / "output" / "benchmarks"
HISTORY_FILE = ROOT / "config" / "model-test-history.json"

def score_candidate(data, model, artifact):      # turns one bench file row into a leaderboard row
    ...
def candidate_order(row):                         # ranking key used to pick one row per build
    return (int(row.get("successful_claimed_tasks") or 0),
            int(row.get("successful_tasks") or 0),
            str(row.get("generated_at") or ""))

def load_benchmark_rows():                        # <-- decides what gets INCLUDED
    chosen = {}
    for artifact in sorted(BENCHMARK_DIR.glob("capability-benchmark-*.json")):
        data = json.loads(artifact.read_text())
        for model in data.get("models") or []:
            row = score_candidate(data, model, artifact)
            current = chosen.get(row["build_id"])
            if current is None or candidate_order(row) > candidate_order(current):
                chosen[row["build_id"]] = row
    return chosen

def merge_history(rows):                          # folds in historical rows from config
    ...
def markdown_report(payload):                     # renders the table
    ...
```

### scripts/generate-current-model-guide.py  (excerpt)
```python
# Reads the already-selected leaderboard rows and renders the site guide.
# It does not decide inclusion; it renders what the leaderboard produced.
```

### scripts/benchmark-capabilities.py  (excerpt)
```python
# Runs models and writes output/benchmarks/capability-benchmark-<ts>.json.
# It only produces raw results; it never decides what is published.
```

### scripts/generate-benchmark-charts.py  (excerpt)
```python
# Draws SVG charts from already-selected rows. No inclusion logic.
```
