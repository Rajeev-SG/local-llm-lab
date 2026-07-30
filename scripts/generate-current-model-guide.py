#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
METADATA_FILE = ROOT / "config" / "model-guide-metadata.json"
LEADERBOARD_FILE = ROOT / "output" / "leaderboard" / "overall-leaderboard.json"
OUTPUT_FILE = ROOT / "output" / "inventory" / "current-models.json"
SITE_FILE = ROOT / "site" / "src" / "current-models.json"
HF_CACHE = Path.home() / ".cache" / "huggingface" / "hub"
OLLAMA_MANIFESTS = Path.home() / ".ollama" / "models" / "manifests"


def is_installed(model: dict[str, Any]) -> bool:
    runtime = model["runtime"]
    if runtime.startswith("mlx"):
        repo = model["cache_repo"].replace("/", "--")
        return (HF_CACHE / f"models--{repo}").exists()
    if runtime == "ollama":
        return (OLLAMA_MANIFESTS / model["manifest_path"]).exists()
    if runtime == "apfel":
        executable = shutil.which("apfel")
        if not executable:
            return False
        result = subprocess.run(
            [executable, "--model-info"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        return result.returncode == 0 and "available:  yes" in result.stdout
    return False


def benchmark_index(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = (payload.get("ranked") or []) + (payload.get("unranked") or [])
    return {row["build_id"]: row for row in rows}


def benchmark_summary(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "rank": row.get("rank"),
        "status": row.get("status"),
        "work_fit_score": row.get("work_fit_score"),
        "quality_score": row.get("quality_score"),
        "generation_tokens_per_second": row.get("generation_tokens_per_second"),
        "generation_speed_basis": row.get("generation_speed_basis"),
        "peak_memory_gb": row.get("peak_memory_gb"),
        "successful_tasks": row.get("successful_tasks"),
        "task_count": row.get("task_count"),
        "artifact": row.get("artifact"),
    }


def main() -> int:
    metadata = json.loads(METADATA_FILE.read_text(encoding="utf-8"))
    leaderboard = json.loads(LEADERBOARD_FILE.read_text(encoding="utf-8"))
    benchmark_rows = benchmark_index(leaderboard)

    installed = []
    configured_ids = set()
    for model in metadata["models"]:
        configured_ids.add(model["build_id"])
        if not is_installed(model):
            continue
        installed.append(
            {
                **model,
                "installed": True,
                "benchmark": benchmark_summary(benchmark_rows.get(model["build_id"])),
            }
        )

    installed.sort(
        key=lambda model: (
            (model.get("benchmark") or {}).get("rank") is None,
            (model.get("benchmark") or {}).get("rank") or 10_000,
            model["label"].lower(),
            model["runtime"],
        )
    )

    installed_ids = {model["build_id"] for model in installed}
    previously_tested = []
    for row in (leaderboard.get("ranked") or []) + (leaderboard.get("unranked") or []):
        if row["build_id"] in installed_ids:
            continue
        previously_tested.append(
            {
                "build_id": row["build_id"],
                "label": row["label"],
                "runtime": row["runtime"],
                "status": row["status"],
                "rank": row.get("rank"),
                "work_fit_score": row.get("work_fit_score"),
                "quality_score": row.get("quality_score"),
                "artifact": row.get("artifact"),
                "known_metadata": row["build_id"] in configured_ids,
            }
        )

    aliases = [
        {"alias": alias, "base_model": model["model_name"], "runtime": model["runtime"]}
        for model in installed
        for alias in model.get("aliases", [])
    ]
    ranked_installed = [
        model for model in installed if (model.get("benchmark") or {}).get("rank") is not None
    ]
    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "machine": metadata["machine"],
        "summary": {
            "installed_builds": len(installed),
            "ranked_installed_builds": len(ranked_installed),
            "aliases": len(aliases),
            "runtimes": sorted({model["runtime"] for model in installed}),
            "installed_storage_gb": round(
                sum(model.get("size_gb") or 0 for model in installed), 1
            ),
            "top_model": ranked_installed[0]["label"] if ranked_installed else None,
        },
        "installed_models": installed,
        "aliases": aliases,
        "previously_tested": previously_tested,
        "score_definition": leaderboard["score_definition"],
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(payload, indent=2) + "\n"
    OUTPUT_FILE.write_text(rendered, encoding="utf-8")
    SITE_FILE.write_text(rendered, encoding="utf-8")
    print(f"Wrote {OUTPUT_FILE}")
    print(f"Wrote {SITE_FILE}")
    print(
        f"Recorded {len(installed)} installed builds, "
        f"{len(aliases)} aliases, and {len(previously_tested)} historical builds."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
