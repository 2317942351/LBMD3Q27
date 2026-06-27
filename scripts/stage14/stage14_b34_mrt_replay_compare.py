#!/usr/bin/env python3
"""Compare B33 replay momentum delta against the B34 MRT algebra expectation.

For the current generated MRT formula, the low-order momentum rows use
Omega=1, so local algebra predicts:

    ReplayMomentumDeltaG ~= 0.5 * ReplayMF

where ReplayMF is F_total/rho_eff after MomentumClosureProbeMode scaling.
This script reads B33 argmax traces and reports whether the replay fields are
consistent with that local algebra at the selected first-bad nodes.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def as_vec(value: Any) -> list[float] | None:
    if not isinstance(value, list) or len(value) != 3:
        return None
    try:
        out = [float(x) for x in value]
    except (TypeError, ValueError):
        return None
    if not all(math.isfinite(x) for x in out):
        return None
    return out


def norm(vec: list[float]) -> float:
    return math.sqrt(sum(x * x for x in vec))


def compare_record(record: dict[str, Any]) -> dict[str, Any] | None:
    colocated = record.get("colocated")
    if not isinstance(colocated, dict):
        return None
    mf = as_vec(colocated.get("ReplayMF"))
    delta = as_vec(colocated.get("ReplayMomentumDeltaG"))
    after = as_vec(colocated.get("ReplayMomentumAfterG"))
    m0 = as_vec(colocated.get("ReplayM0"))
    if mf is None or delta is None:
        return None
    expected = [0.5 * x for x in mf]
    diff = [delta[i] - expected[i] for i in range(3)]
    row = {
        "case": record.get("case"),
        "step": record.get("step"),
        "mask": record.get("mask"),
        "field": record.get("field"),
        "flat_index": record.get("flat_index"),
        "ijk": record.get("ijk"),
        "ReplayMF": mf,
        "ReplayMomentumDeltaG": delta,
        "expected_delta_half_mf": expected,
        "delta_minus_expected": diff,
        "max_abs_diff": max(abs(x) for x in diff),
        "mf_norm": norm(mf),
        "delta_norm": norm(delta),
        "delta_over_mf_norm": norm(delta) / (norm(mf) + 1.0e-300),
    }
    if after is not None:
        row["ReplayMomentumAfterG"] = after
    if m0 is not None:
        row["ReplayM0"] = m0
    return row


def load_records(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"expected list in {path}")
    return [row for row in data if isinstance(row, dict)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", type=Path, nargs="+", help="b33_argmax_trace.json paths")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--atol", type=float, default=1.0e-8)
    args = parser.parse_args()

    comparisons: list[dict[str, Any]] = []
    for path in args.paths:
        for record in load_records(path):
            row = compare_record(record)
            if row is None:
                continue
            row["source"] = str(path)
            row["pass"] = row["max_abs_diff"] <= args.atol
            comparisons.append(row)
    summary = {
        "claim_limit": "local replay algebra comparison only; not runtime validation",
        "atol": args.atol,
        "record_count": len(comparisons),
        "pass_count": sum(1 for row in comparisons if row["pass"]),
        "fail_count": sum(1 for row in comparisons if not row["pass"]),
        "max_abs_diff": max((row["max_abs_diff"] for row in comparisons), default=None),
        "comparisons": comparisons,
    }
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "comparisons"}, indent=2, sort_keys=True))
    return 0 if summary["fail_count"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
