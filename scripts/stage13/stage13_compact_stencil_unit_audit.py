#!/usr/bin/env python3
"""Run the C1b-unit compact-stencil audit from the Stage13 script namespace."""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path


def load_tool(repo_root: Path):
    tool_path = repo_root / "tools" / "geometry_preprocess" / "compact_stencil_audit.py"
    spec = importlib.util.spec_from_file_location("compact_stencil_audit", tool_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {tool_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="default: <repo>/artifacts/stage13_compact_stencil_unit_audit_20260616",
    )
    parser.add_argument("--max-l", type=int, default=3)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    tool = load_tool(repo_root)
    out_dir = args.out_dir or (repo_root / "artifacts" / "stage13_compact_stencil_unit_audit_20260616")
    summary = tool.run_audit(out_dir, max_l=args.max_l)
    print(tool.json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["status"].startswith("PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())
