#!/usr/bin/env python3
"""Classify Stage17B-B8 neutral drift isolation outputs.

This script intentionally reuses the existing B5/B6 metrics and adds only the
cross-case verdict logic needed for B8. It does not validate a contact angle.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def load_case_metadata(case_dir: Path) -> dict[str, Any]:
    path = case_dir / "case_metadata.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def final_b6_case(b6: dict[str, Any], case_name: str) -> dict[str, Any] | None:
    for case in b6.get("cases", []):
        if case.get("case") == case_name:
            return case
    return None


def final_b5_case(b5: dict[str, Any], case_name: str) -> dict[str, Any] | None:
    for case in b5.get("cases", []):
        if case.get("case") == case_name:
            return case
    return None


def final_shadow_case(shadow: dict[str, Any] | None, case_name: str) -> dict[str, Any] | None:
    if not shadow:
        return None
    for case in shadow.get("cases", []):
        if case.get("case") == case_name:
            return case
    return None


def read_run_status(case_dir: Path) -> str:
    path = case_dir / "run.status"
    return path.read_text(encoding="utf-8", errors="replace").strip() if path.exists() else ""


def run_log_has_nan(case_dir: Path) -> bool:
    path = case_dir / "run.log"
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    return "NaN" in text or "Nan value" in text or "Stopping due to Nan" in text


def path_cells_from_b5(final_frame: dict[str, Any]) -> dict[str, int]:
    # B5 analyzer does not summarize WettingPathId. B8 keeps this separate in
    # shadow/B5 outputs where available; missing values are not fatal.
    return {}


def case_summary(
    root: Path,
    b5: dict[str, Any],
    b6: dict[str, Any],
    shadow: dict[str, Any] | None,
    case_dir: Path,
) -> dict[str, Any]:
    meta = load_case_metadata(case_dir)
    case_name = case_dir.name
    b6_case = final_b6_case(b6, case_name)
    b5_case = final_b5_case(b5, case_name)
    shadow_case = final_shadow_case(shadow, case_name)
    final_b6 = (b6_case or {}).get("frames", [{}])[-1] if (b6_case or {}).get("frames") else {}
    final_b5 = (b5_case or {}).get("final", {})
    final_shadow = (
        (shadow_case or {}).get("frames", [{}])[-1]
        if (shadow_case or {}).get("frames")
        else {}
    )
    response = (b6_case or {}).get("response_verdict", {})
    b5_final = final_b5 or {}
    b5_stats = {
        "consumed_fraction_contact": b5_final.get("consumed_fraction_contact"),
        "B5WallGhostMinusCenter_mean": (
            b5_final.get("B5WallGhostMinusCenter_contact", {}) or {}
        ).get("mean"),
        "B5WallGhostMinusFluidProbe_mean": (
            b5_final.get("B5WallGhostMinusFluidProbe_contact", {}) or {}
        ).get("mean"),
        "B5GradPhiNormal_mean": (b5_final.get("B5GradPhiNormal_contact", {}) or {}).get("mean"),
        "B5FphiNormalProxy_mean": (
            b5_final.get("B5FphiNormalProxy_contact", {}) or {}
        ).get("mean"),
        "B5PhaseFromHDelta_mean": (
            b5_final.get("B5PhaseFromHDelta_contact", {}) or {}
        ).get("mean"),
        "ReplayMu_max_abs": (b5_final.get("ReplayMu_contact", {}) or {}).get("max_abs"),
        "ReplayLapPhi_max_abs": (b5_final.get("ReplayLapPhi_contact", {}) or {}).get("max_abs"),
    }
    run_status = read_run_status(case_dir)
    failures: list[str] = []
    if "RC=0" not in run_status:
        failures.append("missing_rc0")
    if run_log_has_nan(case_dir):
        failures.append("runtime_log_nan")
    if not b6_case:
        failures.append("missing_b6_case")
    if not b5_case:
        failures.append("missing_b5_case")
    if final_b6.get("phase_nonfinite", 0):
        failures.append("phase_nonfinite")
    group = meta.get("b8_group")
    path_failures: list[str] = []
    if group == "C":
        applied = int(final_shadow.get("write_applied_cells") or 0)
        path170 = int(final_shadow.get("wetting_path_170_cells") or 0)
        mismatch = int(final_shadow.get("wallghost_psi_mismatch_cells_applied") or 0)
        if applied <= 0:
            path_failures.append("group_C_no_controlled_write")
        if applied != path170:
            path_failures.append("group_C_not_all_path170")
        if mismatch != 0:
            path_failures.append("group_C_wallghost_not_equal_psi")
    elif group == "D":
        applied = int(final_shadow.get("write_applied_cells") or 0)
        path170 = int(final_shadow.get("wetting_path_170_cells") or 0)
        applied_without_170 = int(final_shadow.get("applied_without_path170_cells") or 0)
        if applied <= 0:
            path_failures.append("group_D_no_controlled_write")
        if path170 != 0:
            path_failures.append("group_D_unexpected_path170")
        if applied_without_170 != applied:
            path_failures.append("group_D_not_all_non170")
    elif group in {"A", "B"}:
        applied = int(final_shadow.get("write_applied_cells") or 0)
        if applied != 0:
            path_failures.append(f"group_{group}_unexpected_controlled_write")
    failures.extend(path_failures)
    return {
        "case": case_name,
        "group": meta.get("b8_group"),
        "label": meta.get("b8_label"),
        "metadata": meta,
        "run_status": run_status,
        "failures": failures,
        "status": "pass" if not failures else "fail",
        "response": response,
        "contact_half_width_delta_deg": response.get("contact_half_width_delta_deg"),
        "direction_by_contact_half_width": response.get("direction_by_contact_half_width"),
        "final_phase_min": final_b6.get("phase_min"),
        "final_phase_max": final_b6.get("phase_max"),
        "final_phase_nonfinite": final_b6.get("phase_nonfinite"),
        "final_phase_mean_abs_near_wall_delta": (
            final_b6.get("delta_from_initial", {}) or {}
        ).get("phase_mean_abs_near_wall"),
        "slice_angle_obtuse_delta_deg": (
            final_b6.get("delta_from_initial", {}) or {}
        ).get("slice_angle_obtuse_deg"),
        "slice_footprint_delta": (
            final_b6.get("delta_from_initial", {}) or {}
        ).get("slice_footprint_cells"),
        "b5": b5_stats | path_cells_from_b5(b5_final),
        "write_path": {
            "write_allowed_cells": final_shadow.get("write_allowed_cells"),
            "write_applied_cells": final_shadow.get("write_applied_cells"),
            "wetting_path_170_cells": final_shadow.get("wetting_path_170_cells"),
            "applied_without_path170_cells": final_shadow.get("applied_without_path170_cells"),
            "wallghost_psi_max_abs_diff_applied": final_shadow.get(
                "wallghost_psi_max_abs_diff_applied"
            ),
            "wallghost_psi_mismatch_cells_applied": final_shadow.get(
                "wallghost_psi_mismatch_cells_applied"
            ),
            "wetting_path_min": (
                final_shadow.get("stats", {}).get("WettingPathId", {}) or {}
            ).get("min"),
            "wetting_path_max": (
                final_shadow.get("stats", {}).get("WettingPathId", {}) or {}
            ).get("max"),
        },
    }


def abs_or_inf(value: Any) -> float:
    return abs(float(value)) if value is not None else float("inf")


def classify(cases: list[dict[str, Any]], neutral_tolerance_deg: float) -> dict[str, Any]:
    by_group = {case.get("group"): case for case in cases}
    missing = [group for group in ["A", "B", "C", "D"] if group not in by_group]
    if missing:
        return {
            "status": "insufficient_cases",
            "missing_groups": missing,
            "primary_suspect": "unknown",
        }
    drift = {
        group: by_group[group].get("contact_half_width_delta_deg")
        for group in ["A", "B", "C", "D"]
    }
    stable = {group: abs_or_inf(value) <= neutral_tolerance_deg for group, value in drift.items()}
    primary = "undetermined"
    if not stable["A"]:
        primary = "baseline_phase_force_initialization_bias"
    elif stable["A"] and stable["B"] and not stable["C"] and stable["D"]:
        primary = "controlled_psiwallghost_neutral_formula_bias"
    elif stable["A"] and stable["B"] and not stable["C"] and not stable["D"]:
        primary = "controlled_write_gate_or_stencil_consumption_bias"
    elif stable["A"] and not stable["B"]:
        primary = "shadow_only_side_effect_or_metric_sensitivity"
    elif all(stable.values()):
        primary = "neutral_drift_not_reproduced_within_tolerance"
    return {
        "status": "classified",
        "neutral_tolerance_deg": neutral_tolerance_deg,
        "drift_by_group_deg": drift,
        "stable_by_group": stable,
        "primary_suspect": primary,
        "interpretation": {
            "A": "legacy baseline write-off",
            "B": "Stage17B shadow-only write-off",
            "C": "controlled PsiWallGhost write",
            "D": "controlled legacy analytic WallGhost write",
        },
        "claim_limit": "B8 root-cause classification only; not contact-angle validation",
    }


def write_rows(path: Path, cases: list[dict[str, Any]]) -> None:
    rows: list[dict[str, Any]] = []
    for case in cases:
        row = {
            "case": case["case"],
            "group": case.get("group"),
            "label": case.get("label"),
            "status": case.get("status"),
            "contact_half_width_delta_deg": case.get("contact_half_width_delta_deg"),
            "direction_by_contact_half_width": case.get("direction_by_contact_half_width"),
            "slice_angle_obtuse_delta_deg": case.get("slice_angle_obtuse_delta_deg"),
            "slice_footprint_delta": case.get("slice_footprint_delta"),
            "final_phase_min": case.get("final_phase_min"),
            "final_phase_max": case.get("final_phase_max"),
            "final_phase_nonfinite": case.get("final_phase_nonfinite"),
            "final_phase_mean_abs_near_wall_delta": case.get(
                "final_phase_mean_abs_near_wall_delta"
            ),
        }
        for key, value in case.get("b5", {}).items():
            row[f"b5_{key}"] = value
        for key, value in case.get("write_path", {}).items():
            row[f"write_path_{key}"] = value
        rows.append(row)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--b5-json", type=Path, default=None)
    parser.add_argument("--b6-json", type=Path, default=None)
    parser.add_argument("--shadow-json", type=Path, default=None)
    parser.add_argument("--out-json", type=Path, default=None)
    parser.add_argument("--out-csv", type=Path, default=None)
    parser.add_argument("--neutral-tolerance-deg", type=float, default=1.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    b5_path = args.b5_json or (args.root / "stage17B_B5_consumption_analysis.json")
    b6_path = args.b6_json or (
        args.root / "post" / "B6_contactline_lag" / "stage17B_B6_contactline_lag_analysis.json"
    )
    b5 = load_json(b5_path)
    b6 = load_json(b6_path)
    shadow_path = args.shadow_json or (args.root / "stage17B_shadow_analysis.json")
    shadow = load_json(shadow_path) if shadow_path.exists() else None
    case_dirs = sorted(
        path for path in args.root.iterdir() if path.is_dir() and (path / "case.xml").exists()
    )
    cases = [case_summary(args.root, b5, b6, shadow, case_dir) for case_dir in case_dirs]
    failures = {case["case"]: case["failures"] for case in cases if case["failures"]}
    classification = classify(cases, args.neutral_tolerance_deg)
    status = "PASS_STAGE17B_B8_NEUTRAL_CLASSIFICATION" if not failures else "FAIL"
    summary = {
        "root": str(args.root),
        "status": status,
        "failures": failures,
        "classification": classification,
        "cases": cases,
        "claim_limit": "B8 neutral drift root-cause diagnostic only; not contact-angle validation",
    }
    out_json = args.out_json or (args.root / "stage17B_B8_neutral_analysis.json")
    out_csv = args.out_csv or (args.root / "stage17B_B8_neutral_summary.csv")
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    write_rows(out_csv, cases)
    print(json.dumps({k: v for k, v in summary.items() if k != "cases"}, indent=2, sort_keys=True))
    return 0 if status.startswith("PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())
