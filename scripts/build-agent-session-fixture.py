#!/usr/bin/env python3
"""Extract a bounded, real agent-session slice into a long-context diagnosis fixture.

Reuses a local OMP session transcript; no bespoke data is invented. The slice is
trimmed to keep the fixture realistic but bounded, and a hidden answer key is
written alongside for objective scoring.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

DEFAULT_SRC = Path.home() / ".omp/agent/sessions/-.omp-work/2026-08-27T16-23-13-522Z_01a04408-5b72-7000-ae44-5b401c7fc459.jsonl"


def text_of(record: dict) -> str:
    message = record.get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if not isinstance(item, dict):
                continue
            if item.get("text"):
                parts.append(item["text"])
            elif item.get("name"):
                parts.append(f"[tool:{item['name']}]")
            elif item.get("type") == "tool_result":
                parts.append("[tool_result]")
        return " ".join(parts)
    return ""


def load_rows(src: Path) -> list[tuple[str, str]]:
    rows = []
    for line in src.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("type") != "message":
            continue
        message = record.get("message") or {}
        body = text_of(record).strip()
        if body:
            rows.append((message.get("role", "?"), body))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", type=Path, default=DEFAULT_SRC)
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--end", type=int, required=True)
    parser.add_argument("--max-chars-per-row", type=int, default=1800)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    rows = load_rows(args.src)
    slice_rows = []
    for index in range(args.start, min(args.end, len(rows))):
        role, body = rows[index]
        if len(body) > args.max_chars_per_row:
            body = body[: args.max_chars_per_row] + " …[truncated]"
        slice_rows.append((index, role, body))

    lines = [
        "# Long-context diagnosis fixture",
        "",
        "The following is a real agent session transcript (trimmed). Read it and answer.",
        "",
        f"Source: {args.src.name} rows {args.start}-{args.end}",
        "",
    ]
    for index, role, body in slice_rows:
        lines.append(f"### [{index}] {role}")
        lines.append("```")
        lines.append(body)
        lines.append("```")
        lines.append("")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines), encoding="utf-8")

    total = sum(len(body) for _, _, body in slice_rows)
    print(f"wrote {args.out} rows={len(slice_rows)} chars={total} approx_tokens={total // 4}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
