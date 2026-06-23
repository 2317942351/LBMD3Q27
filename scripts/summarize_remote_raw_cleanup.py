#!/usr/bin/env python3
"""Summarize remote raw-field cleanup candidates by run directory."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import PurePosixPath


def infer_run_dir(path: str) -> str:
    p = PurePosixPath(path)
    parts = p.parts
    try:
        idx = parts.index("runs")
        if idx + 1 < len(parts):
            return str(PurePosixPath(*parts[: idx + 2]))
    except ValueError:
        pass
    return str(p.parent)


def human_bytes(n: int) -> str:
    value = float(n)
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    for unit in units:
        if value < 1024.0 or unit == units[-1]:
            return f"{value:.2f} {unit}"
        value /= 1024.0
    return f"{n} B"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    groups: dict[str, dict[str, object]] = defaultdict(
        lambda: {"count": 0, "bytes": 0, "max_bytes": 0, "max_path": "", "examples": []}
    )
    with open(args.input, newline="", encoding="utf-8") as f:
        sample = f.readline()
        f.seek(0)
        if sample.startswith("classification,"):
            iterable = csv.DictReader(f)
        else:
            iterable = (
                {
                    "classification": row[0],
                    "bytes": row[1],
                    "path": row[2],
                    "reason": row[3] if len(row) > 3 else "",
                }
                for row in csv.reader(f)
                if len(row) >= 3
            )
        for row in iterable:
            if row.get("classification") != "ARCHIVE_OR_DELETE_RAW_CANDIDATE":
                continue
            path = row["path"]
            size = int(row["bytes"])
            run_dir = infer_run_dir(path)
            g = groups[run_dir]
            g["count"] = int(g["count"]) + 1
            g["bytes"] = int(g["bytes"]) + size
            if size > int(g["max_bytes"]):
                g["max_bytes"] = size
                g["max_path"] = path
            examples = g["examples"]
            assert isinstance(examples, list)
            if len(examples) < 3:
                examples.append(path)

    rows = []
    for run_dir, data in groups.items():
        rows.append(
            {
                "classification": "REVIEW_RAW_FIELDS",
                "run_dir": run_dir,
                "raw_file_count": data["count"],
                "bytes": data["bytes"],
                "human": human_bytes(int(data["bytes"])),
                "max_file_bytes": data["max_bytes"],
                "max_file_path": data["max_path"],
                "examples": " | ".join(data["examples"]),
                "approval_status": "NEEDS_USER_APPROVAL",
            }
        )
    rows.sort(key=lambda r: int(r["bytes"]), reverse=True)

    with open(args.output, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "classification",
            "run_dir",
            "raw_file_count",
            "bytes",
            "human",
            "max_file_bytes",
            "max_file_path",
            "examples",
            "approval_status",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    total = sum(int(r["bytes"]) for r in rows)
    print(f"groups={len(rows)} bytes={total} human={human_bytes(total)} output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
