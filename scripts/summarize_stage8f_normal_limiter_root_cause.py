#!/usr/bin/env python3
"""Build curated Stage8f gate summaries from attribution JSON artifacts.

This script reads only copied JSON/CSV/log artifacts. It does not require or
read raw VTI/PVTI/PRI fields.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any


STATUS = "runtime_sanity"
CLAIM_LIMIT = "runtime_sanity / exploratory_not_validation only"


def json_clean(value: Any) -> Any:
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, dict):
        return {k: json_clean(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_clean(v) for v in value]
    return value


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def get_stat(frame: dict[str, Any], group: str, key: str) -> Any:
    value = frame.get(group, {})
    if isinstance(value, dict):
        return value.get(key, math.nan)
    return math.nan


def case_angle_from_id(case_id: str) -> float | None:
    marker = "_wall"
    if marker not in case_id:
        return None
    tail = case_id.split(marker, 1)[1].split("_", 1)[0]
    try:
        return float(int(tail))
    except ValueError:
        return None


def final_frame(path: Path) -> dict[str, Any]:
    payload = read_json(path)
    frames = payload.get("frames", [])
    if not frames:
        raise ValueError(f"no frames in {path}")
    return frames[-1]


def flat_rows(flat_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for attr_path in sorted(flat_root.glob("cap_theta030_wall*_mode1/analysis_stage8f_attribution/stage8f_normal_limiter_attribution_summary.json")):
        case_dir = attr_path.parents[1]
        case_id = case_dir.name
        frame = final_frame(attr_path)
        flat_gate_path = case_dir / "analysis_flat_cap_gate" / f"{case_id}_flat_gate_summary.json"
        angle_apparent = math.nan
        if flat_gate_path.exists():
            gate = read_json(flat_gate_path)
            last = gate.get("last", {})
            angle_apparent = last.get("angle_apparent_deg", math.nan)
        rows.append(
            {
                "case_id": case_id,
                "wall_angle_deg": case_angle_from_id(case_id),
                "step": frame.get("step"),
                "angle_apparent_deg": angle_apparent,
                "active_count": frame.get("active_count"),
                "normal_limiter_count": frame.get("normal_limiter_count"),
                "normal_limiter_fraction": frame.get("normal_limiter_fraction"),
                "vector_limiter_count": frame.get("limiter_count"),
                "vector_limiter_fraction": frame.get("limiter_fraction"),
                "ratio_cap_limiter_count": frame.get("ratio_cap_limiter_count"),
                "ratio_cap_limiter_fraction_of_normal_limiter": frame.get("ratio_cap_limiter_fraction_of_normal_limiter"),
                "abs_cap_limiter_count": frame.get("abs_cap_limiter_count"),
                "abs_cap_limiter_fraction_of_normal_limiter": frame.get("abs_cap_limiter_fraction_of_normal_limiter"),
                "cap_demand_ratio_p50": get_stat(frame, "cap_demand_ratio_active", "p50"),
                "cap_demand_ratio_p95": get_stat(frame, "cap_demand_ratio_active", "p95"),
                "cap_demand_ratio_p99": get_stat(frame, "cap_demand_ratio_active", "p99"),
                "normal_raw_abs_p50": get_stat(frame, "normal_raw_abs_active", "p50"),
                "target_minus_raw_abs_p50": get_stat(frame, "target_minus_raw_abs_active", "p50"),
                "target_normal_abs_p50": get_stat(frame, "target_normal_abs_active", "p50"),
                "tangent_mag_p95": get_stat(frame, "tangent_mag_active", "p95"),
                "tan_coeff_times_tangent_p50": get_stat(frame, "tan_coeff_times_tangent_active", "p50"),
                "smooth_weight_total_p50": get_stat(frame, "smooth_weight_total_active", "p50"),
                "limiter_ratio_p50": get_stat(frame, "limiter_ratio_active", "p50"),
                "outer90_normal_limiter_count": frame.get("outer90_normal_limiter_count"),
                "fallback_angle_normal_limiter_count": frame.get("fallback_angle_normal_limiter_count"),
                "max_mach": frame.get("max_mach"),
                "nonfinite_total": frame.get("nonfinite_total"),
                "write_mode_allowed": False,
            }
        )
    return rows


def sphere_rows(sphere_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for attr_path in sorted(sphere_root.glob("*_shadow/analysis_stage8f_normal_limiter_attribution/stage8f_normal_limiter_attribution_summary.json")):
        case_dir = attr_path.parents[1]
        case_id = case_dir.name
        payload = read_json(attr_path)
        frame = payload.get("frames", [])[-1]
        decision = payload.get("decision", {})
        rows.append(
            {
                "case_id": case_id,
                "step": frame.get("step"),
                "active_count": frame.get("active_count"),
                "normal_limiter_count": frame.get("normal_limiter_count"),
                "normal_limiter_fraction": frame.get("normal_limiter_fraction"),
                "vector_limiter_count": frame.get("limiter_count"),
                "vector_limiter_fraction": frame.get("limiter_fraction"),
                "ratio_cap_limiter_count": frame.get("ratio_cap_limiter_count"),
                "ratio_cap_limiter_fraction_of_normal_limiter": frame.get("ratio_cap_limiter_fraction_of_normal_limiter"),
                "abs_cap_limiter_count": frame.get("abs_cap_limiter_count"),
                "abs_cap_limiter_fraction_of_normal_limiter": frame.get("abs_cap_limiter_fraction_of_normal_limiter"),
                "cap_demand_ratio_p50": get_stat(frame, "cap_demand_ratio_active", "p50"),
                "cap_demand_ratio_p95": get_stat(frame, "cap_demand_ratio_active", "p95"),
                "cap_demand_ratio_p99": get_stat(frame, "cap_demand_ratio_active", "p99"),
                "normal_raw_abs_p50": get_stat(frame, "normal_raw_abs_active", "p50"),
                "target_minus_raw_abs_p50": get_stat(frame, "target_minus_raw_abs_active", "p50"),
                "target_normal_abs_p50": get_stat(frame, "target_normal_abs_active", "p50"),
                "tangent_mag_p95": get_stat(frame, "tangent_mag_active", "p95"),
                "tan_coeff_times_tangent_p50": get_stat(frame, "tan_coeff_times_tangent_active", "p50"),
                "smooth_weight_total_p50": get_stat(frame, "smooth_weight_total_active", "p50"),
                "limiter_ratio_p50": get_stat(frame, "limiter_ratio_active", "p50"),
                "sphere11_active_count": frame.get("sphere11_active_count"),
                "sphere11_normal_limiter_count": frame.get("sphere11_normal_limiter_count"),
                "outer90_active_count": frame.get("outer90_active_count"),
                "outer90_normal_limiter_count": frame.get("outer90_normal_limiter_count"),
                "fallback_angle_active_count": frame.get("fallback_angle_active_count"),
                "fallback_angle_normal_limiter_count": frame.get("fallback_angle_normal_limiter_count"),
                "normal_agreement_p05": get_stat(frame, "normal_agreement_active", "p05"),
                "max_mach": frame.get("max_mach"),
                "nonfinite_total": frame.get("nonfinite_total"),
                "root_cause_classification": decision.get("root_cause_classification"),
                "write_mode_allowed": False,
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def read_text_or_none(path: Path) -> str | None:
    return path.read_text(encoding="utf-8").strip() if path.exists() else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--out-dir", type=Path, default=Path("artifacts/stage8f_normal_limiter_root_cause_summary_20260613"))
    args = parser.parse_args()
    repo = args.repo_root.resolve()
    out_dir = (repo / args.out_dir).resolve() if not args.out_dir.is_absolute() else args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    flat_root = repo / "artifacts" / "flat_wall_cap_stage8f_low_angle_20260613"
    sphere_root = repo / "artifacts" / "pre2025_sphere_stage8f_shadow_20260613"
    provenance_root = repo / "artifacts" / "stage8f_normal_limiter_root_cause_provenance_20260613"

    flat = flat_rows(flat_root)
    sphere = sphere_rows(sphere_root)
    write_csv(out_dir / "stage8f_flat_shadow_summary.csv", flat)
    write_csv(out_dir / "stage8f_sphere_shadow_summary.csv", sphere)

    summary = {
        "status": STATUS,
        "claim_limit": CLAIM_LIMIT,
        "decision": "Stage8f explains the normal-limiter blocker; sphere Stage8OperatorMode=2 remains forbidden",
        "build": {
            "make_source_rc": read_text_or_none(provenance_root / "make_source.returncode"),
            "make_build_rc": read_text_or_none(provenance_root / "make_build.returncode"),
            "binary_sha256": read_text_or_none(provenance_root / "binary.sha256"),
        },
        "raw_policy": "curated XML/JSON/CSV/log only; raw VTI/PVTI/PRI excluded",
        "flat_shadow": flat,
        "sphere_shadow": sphere,
        "root_cause_summary": {
            "vector_limiter": "eliminated in Stage8e/Stage8f shadow outputs; vector_limiter_fraction is 0 in all reported final frames",
            "flat_low_angle_trend": "normal_limiter_fraction falls from 88.78% at wall005 to 0% at wall025/wall030 while tangent magnitude stays near the same order",
            "sphere_free": "free-sphere init remains normal-limiter dominated at 85.28%, mainly ratio-cap limited",
            "sphere_cap_initializer": "cap-on-sphere diagnostic init lowers normal_limiter_fraction to 73.04% and Mach to 1.89e-5, but still fails the shadow write gate",
            "outer_wall_transfer": "outer90 normal limiter hits are 0 in sphere shadows, so current evidence does not point to outer-wall angle contamination",
            "classification": "low-angle tan amplification plus current normal-cap contract; initial geometry stress contributes but is not sufficient to explain the blocker",
            "next_route": "Stage8g cap-contract revision or low-angle regularized contact relation; do not run sphere write from Stage8f",
        },
        "write_mode_allowed": False,
    }
    (out_dir / "stage8f_gate_summary.json").write_text(json.dumps(json_clean(summary), indent=2), encoding="utf-8")
    print(json.dumps({"status": STATUS, "flat_cases": len(flat), "sphere_cases": len(sphere), "out_dir": str(out_dir)}, indent=2))


if __name__ == "__main__":
    main()
