#!/usr/bin/env python3
"""Compare B33 replay momentum delta against the B34 MRT algebra expectation.

For the current generated MRT formula, the low-order momentum rows are built
from the half-force velocity and then receive the explicit force moment:

    U = m0[1:4] + 0.5 * F/rho_eff
    m[1:4] = U + 0.5 * F/rho_eff

so local algebra predicts:

    ReplayMomentumDeltaG ~= ReplayMF

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


def compare_record(record: dict[str, Any], expected_scale: float) -> dict[str, Any] | None:
    colocated = record.get("colocated")
    if not isinstance(colocated, dict):
        return None
    mf = as_vec(colocated.get("ReplayMF"))
    delta = as_vec(colocated.get("ReplayMomentumDeltaG"))
    after = as_vec(colocated.get("ReplayMomentumAfterG"))
    m0 = as_vec(colocated.get("ReplayM0"))
    if mf is None or delta is None:
        return None
    expected = [expected_scale * x for x in mf]
    expected_half = [0.5 * x for x in mf]
    expected_full = list(mf)
    diff = [delta[i] - expected[i] for i in range(3)]
    half_diff = [delta[i] - expected_half[i] for i in range(3)]
    full_diff = [delta[i] - expected_full[i] for i in range(3)]
    row = {
        "case": record.get("case"),
        "step": record.get("step"),
        "mask": record.get("mask"),
        "field": record.get("field"),
        "flat_index": record.get("flat_index"),
        "ijk": record.get("ijk"),
        "ReplayMF": mf,
        "ReplayMomentumDeltaG": delta,
        "expected_scale": expected_scale,
        "expected_delta": expected,
        "expected_delta_half_mf": expected_half,
        "expected_delta_full_mf": expected_full,
        "delta_minus_expected": diff,
        "delta_minus_half_mf": half_diff,
        "delta_minus_full_mf": full_diff,
        "max_abs_diff": max(abs(x) for x in diff),
        "max_abs_half_diff": max(abs(x) for x in half_diff),
        "max_abs_full_diff": max(abs(x) for x in full_diff),
        "mf_norm": norm(mf),
        "delta_norm": norm(delta),
        "delta_over_mf_norm": norm(delta) / (norm(mf) + 1.0e-300),
    }
    row["relative_diff"] = row["max_abs_diff"] / max(row["mf_norm"], row["delta_norm"], 1.0)
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
    parser.add_argument("--rtol", type=float, default=1.0e-9)
    parser.add_argument(
        "--expected-scale",
        type=float,
        default=1.0,
        help="Expected ReplayMomentumDeltaG scale relative to ReplayMF. Generated Stage14 MRT uses 1.0.",
    )
    parser.add_argument("--max-step", type=int, help="Drop records after this step before pass/fail aggregation.")
    parser.add_argument(
        "--max-mf-norm",
        type=float,
        help="Drop records with ||ReplayMF|| above this value before pass/fail aggregation.",
    )
    parser.add_argument(
        "--max-delta-norm",
        type=float,
        help="Drop records with ||ReplayMomentumDeltaG|| above this value before pass/fail aggregation.",
    )
    args = parser.parse_args()

    comparisons: list[dict[str, Any]] = []
    raw_count = 0
    dropped: dict[str, int] = {"step": 0, "mf_norm": 0, "delta_norm": 0}
    for path in args.paths:
        for record in load_records(path):
            row = compare_record(record, args.expected_scale)
            if row is None:
                continue
            raw_count += 1
            if args.max_step is not None and row.get("step") is not None and int(row["step"]) > args.max_step:
                dropped["step"] += 1
                continue
            if args.max_mf_norm is not None and row["mf_norm"] > args.max_mf_norm:
                dropped["mf_norm"] += 1
                continue
            if args.max_delta_norm is not None and row["delta_norm"] > args.max_delta_norm:
                dropped["delta_norm"] += 1
                continue
            row["source"] = str(path)
            row["pass"] = row["max_abs_diff"] <= args.atol or row["relative_diff"] <= args.rtol
            comparisons.append(row)
    summary = {
        "claim_limit": "local replay algebra comparison only; not runtime validation",
        "atol": args.atol,
        "rtol": args.rtol,
        "expected_scale": args.expected_scale,
        "raw_record_count": raw_count,
        "dropped_record_count": raw_count - len(comparisons),
        "dropped_by_filter": dropped,
        "filters": {
            "max_step": args.max_step,
            "max_mf_norm": args.max_mf_norm,
            "max_delta_norm": args.max_delta_norm,
        },
        "record_count": len(comparisons),
        "pass_count": sum(1 for row in comparisons if row["pass"]),
        "fail_count": sum(1 for row in comparisons if not row["pass"]),
        "max_abs_diff": max((row["max_abs_diff"] for row in comparisons), default=None),
        "max_abs_half_diff": max((row["max_abs_half_diff"] for row in comparisons), default=None),
        "max_abs_full_diff": max((row["max_abs_full_diff"] for row in comparisons), default=None),
        "comparisons": comparisons,
    }
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "comparisons"}, indent=2, sort_keys=True))
    return 0 if summary["fail_count"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
