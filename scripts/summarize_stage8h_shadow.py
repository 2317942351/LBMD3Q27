#!/usr/bin/env python3
"""Build curated Stage8h shadow gate summaries from attribution artifacts."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any


STATUS = "runtime_sanity"


def clean(value: Any) -> Any:
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, list):
        return [clean(v) for v in value]
    return value


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def stat(frame: dict[str, Any], group: str, key: str) -> Any:
    value = frame.get(group, {})
    return value.get(key, math.nan) if isinstance(value, dict) else math.nan


def final_rows(root: Path, pattern: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(root.glob(pattern)):
        case_dir = path.parents[1]
        payload = read_json(path)
        frames = payload.get("frames", [])
        if not frames:
            continue
        frame = frames[-1]
        decision = payload.get("decision", {})
        rows.append(
            {
                "case_id": case_dir.name,
                "step": frame.get("step"),
                "stage8g_mode": frame.get("stage8g_mode"),
                "stage8h_mode": frame.get("stage8h_mode"),
                "active_count": frame.get("active_count"),
                "normal_limiter_count": frame.get("normal_limiter_count"),
                "normal_limiter_fraction": frame.get("normal_limiter_fraction"),
                "stage8h_limiter_equivalent_count": frame.get("stage8h_limiter_equivalent_count"),
                "stage8h_limiter_equivalent_fraction": frame.get("stage8h_limiter_equivalent_fraction"),
                "vector_limiter_fraction": frame.get("limiter_fraction"),
                "limiter_ratio_p50": stat(frame, "limiter_ratio_active", "p50"),
                "cap_demand_ratio_p50": stat(frame, "cap_demand_ratio_active", "p50"),
                "cap_demand_ratio_p95": stat(frame, "cap_demand_ratio_active", "p95"),
                "stage8h_candidate_demand_ratio_p50": stat(frame, "stage8h_candidate_demand_ratio_active", "p50"),
                "stage8h_candidate_demand_ratio_p95": stat(frame, "stage8h_candidate_demand_ratio_active", "p95"),
                "stage8h_candidate_demand_ratio_p99": stat(frame, "stage8h_candidate_demand_ratio_active", "p99"),
                "stage8h_beta_relaxation_p50": stat(frame, "stage8h_beta_relaxation_active", "p50"),
                "stage8h_profile_consistency_weight_p50": stat(frame, "stage8h_profile_consistency_weight_active", "p50"),
                "stage8h_cos_to_tan_ratio_p50": stat(frame, "stage8h_cos_to_tan_ratio_active", "p50"),
                "stage8h_residual_cos_p50": stat(frame, "stage8h_residual_cos_active", "p50"),
                "stage8h_dn_relaxed_p50": stat(frame, "stage8h_dn_relaxed_active", "p50"),
                "raw_normal_scale_limiter_count": frame.get("raw_normal_scale_limiter_count"),
                "target_scale_limiter_count": frame.get("target_scale_limiter_count"),
                "tangent_scale_limiter_count": frame.get("tangent_scale_limiter_count"),
                "floor_scale_limiter_count": frame.get("floor_scale_limiter_count"),
                "tan_raw_p50": stat(frame, "stage8g_tan_raw_active", "p50"),
                "tan_eff_p50": stat(frame, "stage8g_tan_eff_active", "p50"),
                "regularization_ratio_p50": stat(frame, "stage8g_regularization_ratio_active", "p50"),
                "profile_mismatch_p50": stat(frame, "stage8g_profile_target_mismatch_active", "p50"),
                "stage8h_profile_mismatch_p50": stat(frame, "stage8h_profile_target_mismatch_active", "p50"),
                "profile_conflict_p50": stat(frame, "wall_profile_conflict_active", "p50"),
                "outer90_normal_limiter_count": frame.get("outer90_normal_limiter_count"),
                "outer90_stage8h_limiter_equivalent_count": frame.get("outer90_stage8h_limiter_equivalent_count"),
                "fallback_angle_normal_limiter_count": frame.get("fallback_angle_normal_limiter_count"),
                "fallback_angle_stage8h_limiter_equivalent_count": frame.get("fallback_angle_stage8h_limiter_equivalent_count"),
                "max_mach": frame.get("max_mach"),
                "nonfinite_total": frame.get("nonfinite_total"),
                "shadow_gate_passed_for_planning": decision.get("shadow_gate_passed_for_planning"),
                "root_cause_classification": decision.get("root_cause_classification"),
                "write_mode_allowed": decision.get("write_mode_allowed", False),
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


def mode_decisions(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for mode in [0, 1, 2, 3, 4]:
        subset = []
        for row in rows:
            value = row.get("stage8h_mode")
            if value is None or value == "":
                continue
            if int(float(value)) == mode:
                subset.append(row)
        if not subset:
            continue
        out.append(
            {
                "stage8h_mode": mode,
                "case_count": len(subset),
                "all_nonfinite_zero": all((r.get("nonfinite_total") or 0) == 0 for r in subset),
                "all_vector_limiter_zero": all((r.get("vector_limiter_fraction") or 0) == 0 for r in subset),
                "max_normal_limiter_fraction": max(float(r.get("normal_limiter_fraction") or 0) for r in subset),
                "max_stage8h_limiter_equivalent_fraction": max(float(r.get("stage8h_limiter_equivalent_fraction") or 0) for r in subset),
                "min_limiter_ratio_p50": min(float(r.get("limiter_ratio_p50") or 1) for r in subset),
                "max_cap_demand_ratio_p50": max(float(r.get("cap_demand_ratio_p50") or 0) for r in subset),
                "max_stage8h_candidate_demand_ratio_p50": max(float(r.get("stage8h_candidate_demand_ratio_p50") or 0) for r in subset),
                "max_stage8h_candidate_demand_ratio_p95": max(float(r.get("stage8h_candidate_demand_ratio_p95") or 0) for r in subset),
                "outer90_limiter_total": sum(int(r.get("outer90_stage8h_limiter_equivalent_count") or 0) for r in subset),
                "fallback_limiter_total": sum(int(r.get("fallback_angle_stage8h_limiter_equivalent_count") or 0) for r in subset),
                "any_shadow_gate_passed": any(bool(r.get("shadow_gate_passed_for_planning")) for r in subset),
            }
        )
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--out-dir", type=Path, default=Path("artifacts/stage8h_contact_relation_profile_summary_20260613"))
    args = parser.parse_args()
    repo = args.repo_root.resolve()
    out_dir = args.out_dir if args.out_dir.is_absolute() else repo / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    flat_root = repo / "artifacts" / "flat_wall_cap_stage8h_contact_relation_20260613"
    sphere_root = repo / "artifacts" / "pre2025_sphere_stage8h_shadow_20260613"
    flat = final_rows(flat_root, "*/analysis_stage8h_attribution/stage8h_shadow_attribution_summary.json")
    sphere = final_rows(sphere_root, "*/analysis_stage8h_attribution/stage8h_shadow_attribution_summary.json")
    write_csv(out_dir / "stage8h_flat_shadow_summary.csv", flat)
    write_csv(out_dir / "stage8h_sphere_shadow_summary.csv", sphere)
    summary = {
        "status": STATUS,
        "claim_limit": "runtime_sanity / exploratory_not_validation only",
        "decision": "Stage8h is shadow-only; sphere Stage8OperatorMode=2 remains forbidden",
        "flat_mode_decisions": mode_decisions(flat),
        "sphere_mode_decisions": mode_decisions(sphere),
        "flat_shadow": flat,
        "sphere_shadow": sphere,
        "write_mode_allowed": False,
    }
    (out_dir / "stage8h_gate_summary.json").write_text(json.dumps(clean(summary), indent=2), encoding="utf-8")
    print(json.dumps({"status": STATUS, "flat_cases": len(flat), "sphere_cases": len(sphere), "out_dir": str(out_dir)}, indent=2))


if __name__ == "__main__":
    main()
