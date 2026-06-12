#!/usr/bin/env python3
"""Postprocess Stage8d sphere shadow limiter attribution VTI frames."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from pathlib import Path
from typing import Any

import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy


STATUS = "runtime_sanity"
STEP_RE = re.compile(r"_VTK_P\d+_(\d{8})\.vti$")
CS = math.sqrt(1.0 / 3.0)

REGION_LABELS = {
    0: "none_or_unknown",
    1: "sphere_upper",
    2: "sphere_lower90",
    3: "sphere_bottom120",
    4: "outer_or_other_wall",
}
CBIN_LABELS = {
    1: "c_0_0p05",
    2: "c_0p05_0p10",
    3: "c_0p10_0p30",
    4: "c_0p30_0p70",
    5: "c_0p70_0p90",
    6: "c_0p90_0p95",
    7: "c_0p95_1",
}
TANGENT_BINS = [
    ("t_0_0p005", 0.0, 0.005),
    ("t_0p005_0p01", 0.005, 0.01),
    ("t_0p01_0p025", 0.01, 0.025),
    ("t_0p025_0p05", 0.025, 0.05),
    ("t_0p05_0p10", 0.05, 0.10),
    ("t_0p10_inf", 0.10, math.inf),
]
NORMAL_AGREEMENT_BINS = [
    ("normal_0_0p5", 0.0, 0.5),
    ("normal_0p5_0p9", 0.5, 0.9),
    ("normal_0p9_0p99", 0.9, 0.99),
    ("normal_0p99_1p01", 0.99, 1.01),
]

REQUIRED_FIELDS = [
    "PhaseField",
    "Rho",
    "U",
    "BOUNDARY",
    "WallStage8ActiveWeight",
    "WallStage8LimiterReason",
    "WallStage8FluidWallAngle",
    "WallStage8NormalAgreement",
    "WallStage8VectorLimiterHit",
    "WallStage8NormalLimiterHit",
    "WallStage8LimiterRatio",
    "WallStage8VectorDeltaRawMag",
    "WallStage8VectorDeltaLimitedMag",
    "WallStage8NormalDeltaRaw",
    "WallStage8NormalDeltaLimited",
    "WallStage8TangentGradRaw",
    "WallStage8PhaseC",
    "WallStage8RegionTag",
    "WallStage8ContactBandTag",
    "WallStage8TanCoeffLocal",
    "WallStage8SphereRadialDot",
]


def step_of(path: Path) -> int:
    match = STEP_RE.search(path.name)
    return int(match.group(1)) if match else -1


def read_vti(path: Path) -> tuple[tuple[int, int, int], dict[str, np.ndarray]]:
    reader = vtk.vtkXMLImageDataReader()
    reader.SetFileName(str(path))
    reader.Update()
    image = reader.GetOutput()
    dims = tuple(int(v) - 1 for v in image.GetDimensions())
    arrays: dict[str, np.ndarray] = {}
    cell_data = image.GetCellData()
    for i in range(cell_data.GetNumberOfArrays()):
        arr = cell_data.GetArray(i)
        if arr is not None:
            arrays[arr.GetName() or f"array{i}"] = vtk_to_numpy(arr)
    return dims, arrays


def scalar(values: np.ndarray | None) -> np.ndarray | None:
    if values is None:
        return None
    arr = np.asarray(values, dtype=float)
    if arr.ndim > 1:
        arr = arr[:, 0]
    return arr


def vector_mag(values: np.ndarray | None) -> np.ndarray | None:
    if values is None:
        return None
    arr = np.asarray(values, dtype=float)
    if arr.ndim == 1:
        arr = arr.reshape((-1, 1))
    return np.linalg.norm(arr[:, :3], axis=1)


def stats(values: np.ndarray, mask: np.ndarray | None = None) -> dict[str, float | int]:
    arr = np.asarray(values, dtype=float)
    if mask is not None:
        arr = arr[mask]
    if arr.size == 0:
        return {"count": 0, "nonfinite": 0}
    finite = np.isfinite(arr)
    out: dict[str, float | int] = {
        "count": int(arr.size),
        "nonfinite": int(arr.size - np.count_nonzero(finite)),
    }
    if np.any(finite):
        x = arr[finite]
        out.update(
            {
                "min": float(np.min(x)),
                "mean": float(np.mean(x)),
                "p05": float(np.percentile(x, 5)),
                "p10": float(np.percentile(x, 10)),
                "p50": float(np.percentile(x, 50)),
                "p90": float(np.percentile(x, 90)),
                "p95": float(np.percentile(x, 95)),
                "p99": float(np.percentile(x, 99)),
                "max": float(np.max(x)),
                "sum": float(np.sum(x)),
            }
        )
    return out


def finite_nonfinite_total(fields: dict[str, np.ndarray]) -> int:
    return int(sum(np.count_nonzero(~np.isfinite(v)) for v in fields.values()))


def bin_rows(
    *,
    step: int,
    group_name: str,
    labels: list[tuple[str, np.ndarray]],
    active: np.ndarray,
    limiter: np.ndarray,
    raw_delta: np.ndarray,
    ratio: np.ndarray,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for label, mask in labels:
        m = active & mask
        count = int(np.count_nonzero(m))
        hit = int(np.count_nonzero(m & limiter))
        rows.append(
            {
                "step": step,
                "group": group_name,
                "bin": label,
                "active_count": count,
                "limiter_count": hit,
                "limiter_fraction": hit / count if count else math.nan,
                "raw_delta_p95": stats(raw_delta, m).get("p95", math.nan),
                "raw_delta_p99": stats(raw_delta, m).get("p99", math.nan),
                "limiter_ratio_p50": stats(ratio, m).get("p50", math.nan),
            }
        )
    return rows


def summarize_frame(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    dims, arrays = read_vti(path)
    missing = [name for name in REQUIRED_FIELDS if name not in arrays]
    fields = {name: scalar(arrays.get(name)) for name in REQUIRED_FIELDS if scalar(arrays.get(name)) is not None}
    u_mag = vector_mag(arrays.get("U"))
    if u_mag is not None:
        fields["UMag"] = u_mag
    step = step_of(path)
    phase = fields["PhaseField"]
    boundary = fields["BOUNDARY"]
    fluid = np.isfinite(boundary) & (boundary == 0.0)
    active = fluid & np.isfinite(fields["WallStage8ActiveWeight"]) & (fields["WallStage8ActiveWeight"] > 0.0)
    limiter = active & np.isfinite(fields["WallStage8VectorLimiterHit"]) & (fields["WallStage8VectorLimiterHit"] > 0.5)
    normal_limiter = active & np.isfinite(fields["WallStage8NormalLimiterHit"]) & (fields["WallStage8NormalLimiterHit"] > 0.5)
    raw_delta = fields["WallStage8VectorDeltaRawMag"]
    limited_delta = fields["WallStage8VectorDeltaLimitedMag"]
    ratio = fields["WallStage8LimiterRatio"]
    tangent = fields["WallStage8TangentGradRaw"]
    c = fields["WallStage8PhaseC"]
    region = np.rint(fields["WallStage8RegionTag"]).astype(int)
    contact_band = np.rint(fields["WallStage8ContactBandTag"]).astype(int)
    angle = fields["WallStage8FluidWallAngle"]
    normal_agree = fields["WallStage8NormalAgreement"]
    tan_coeff = fields["WallStage8TanCoeffLocal"]
    max_mach = float(np.nanmax(u_mag[fluid]) / CS) if u_mag is not None and np.any(fluid) else math.nan

    active_count = int(np.count_nonzero(active))
    limiter_count = int(np.count_nonzero(limiter))
    normal_limiter_count = int(np.count_nonzero(normal_limiter))
    sphere11 = active & np.isfinite(angle) & (np.abs(angle - math.radians(11.0)) < 1e-6)
    outer90 = active & np.isfinite(angle) & (np.abs(angle - math.radians(90.0)) < 1e-6)
    fallback = active & (~sphere11) & (~outer90)
    summary: dict[str, Any] = {
        "status": STATUS,
        "step": step,
        "file": str(path),
        "dims": list(dims),
        "missing_required_fields": missing,
        "nonfinite_total": finite_nonfinite_total(fields),
        "fluid_count": int(np.count_nonzero(fluid)),
        "active_count": active_count,
        "limiter_count": limiter_count,
        "limiter_fraction": limiter_count / active_count if active_count else math.nan,
        "normal_limiter_count": normal_limiter_count,
        "normal_limiter_fraction": normal_limiter_count / active_count if active_count else math.nan,
        "sphere11_active_count": int(np.count_nonzero(sphere11)),
        "sphere11_limiter_count": int(np.count_nonzero(sphere11 & limiter)),
        "outer90_active_count": int(np.count_nonzero(outer90)),
        "outer90_limiter_count": int(np.count_nonzero(outer90 & limiter)),
        "fallback_angle_active_count": int(np.count_nonzero(fallback)),
        "fallback_angle_limiter_count": int(np.count_nonzero(fallback & limiter)),
        "max_mach": max_mach,
        "phase_fluid_min": float(np.nanmin(phase[fluid])) if np.any(fluid) else math.nan,
        "phase_fluid_max": float(np.nanmax(phase[fluid])) if np.any(fluid) else math.nan,
        "raw_delta_active": stats(raw_delta, active),
        "limited_delta_active": stats(limited_delta, active),
        "limiter_ratio_active": stats(ratio, active),
        "normal_delta_raw_active": stats(fields["WallStage8NormalDeltaRaw"], active),
        "normal_delta_limited_active": stats(fields["WallStage8NormalDeltaLimited"], active),
        "tangent_mag_active": stats(tangent, active),
        "phase_c_active": stats(c, active),
        "normal_agreement_active": stats(normal_agree, active),
        "tan_coeff_active": stats(tan_coeff, active),
    }

    rows: list[dict[str, Any]] = []
    rows += bin_rows(
        step=step,
        group_name="region",
        labels=[(REGION_LABELS.get(i, str(i)), region == i) for i in sorted(REGION_LABELS)],
        active=active,
        limiter=limiter,
        raw_delta=raw_delta,
        ratio=ratio,
    )
    rows += bin_rows(
        step=step,
        group_name="theta_zone",
        labels=[("sphere11", sphere11), ("outer90", outer90), ("fallback", fallback)],
        active=active,
        limiter=limiter,
        raw_delta=raw_delta,
        ratio=ratio,
    )
    rows += bin_rows(
        step=step,
        group_name="c_bin",
        labels=[(CBIN_LABELS.get(i, str(i)), contact_band == i) for i in sorted(CBIN_LABELS)],
        active=active,
        limiter=limiter,
        raw_delta=raw_delta,
        ratio=ratio,
    )
    rows += bin_rows(
        step=step,
        group_name="tangent_bin",
        labels=[(label, (tangent >= lo) & (tangent < hi)) for label, lo, hi in TANGENT_BINS],
        active=active,
        limiter=limiter,
        raw_delta=raw_delta,
        ratio=ratio,
    )
    rows += bin_rows(
        step=step,
        group_name="normal_agreement_bin",
        labels=[
            (label, (normal_agree >= lo) & (normal_agree < hi))
            for label, lo, hi in NORMAL_AGREEMENT_BINS
        ],
        active=active,
        limiter=limiter,
        raw_delta=raw_delta,
        ratio=ratio,
    )
    for c_label, c_mask in [(CBIN_LABELS.get(i, str(i)), contact_band == i) for i in sorted(CBIN_LABELS)]:
        for t_label, lo, hi in TANGENT_BINS:
            mask = c_mask & (tangent >= lo) & (tangent < hi)
            rows += bin_rows(
                step=step,
                group_name=f"c_x_tangent:{c_label}",
                labels=[(t_label, mask)],
                active=active,
                limiter=limiter,
                raw_delta=raw_delta,
                ratio=ratio,
            )
    return summary, rows


def flatten_summary(row: dict[str, Any]) -> dict[str, Any]:
    def s(group: str, key: str) -> Any:
        value = row.get(group, {})
        return value.get(key, math.nan) if isinstance(value, dict) else math.nan

    return {
        "step": row["step"],
        "nonfinite_total": row["nonfinite_total"],
        "max_mach": row["max_mach"],
        "active_count": row["active_count"],
        "limiter_count": row["limiter_count"],
        "limiter_fraction": row["limiter_fraction"],
        "normal_limiter_count": row["normal_limiter_count"],
        "normal_limiter_fraction": row["normal_limiter_fraction"],
        "sphere11_active_count": row["sphere11_active_count"],
        "sphere11_limiter_count": row["sphere11_limiter_count"],
        "outer90_active_count": row["outer90_active_count"],
        "outer90_limiter_count": row["outer90_limiter_count"],
        "fallback_angle_active_count": row["fallback_angle_active_count"],
        "fallback_angle_limiter_count": row["fallback_angle_limiter_count"],
        "raw_delta_p50": s("raw_delta_active", "p50"),
        "raw_delta_p95": s("raw_delta_active", "p95"),
        "raw_delta_p99": s("raw_delta_active", "p99"),
        "raw_delta_max": s("raw_delta_active", "max"),
        "limited_delta_p99": s("limited_delta_active", "p99"),
        "limiter_ratio_p05": s("limiter_ratio_active", "p05"),
        "limiter_ratio_p10": s("limiter_ratio_active", "p10"),
        "limiter_ratio_p50": s("limiter_ratio_active", "p50"),
        "limiter_ratio_p95": s("limiter_ratio_active", "p95"),
        "normal_delta_raw_p99": s("normal_delta_raw_active", "p99"),
        "tangent_mag_p95": s("tangent_mag_active", "p95"),
        "tangent_mag_p99": s("tangent_mag_active", "p99"),
        "phase_c_p50": s("phase_c_active", "p50"),
        "normal_agreement_p05": s("normal_agreement_active", "p05"),
        "tan_coeff_p50": s("tan_coeff_active", "p50"),
    }


def decision(rows: list[dict[str, Any]]) -> dict[str, Any]:
    final = rows[-1] if rows else {}
    limiter_fraction = final.get("limiter_fraction", math.nan)
    outer90_limiter = final.get("outer90_limiter_count", math.nan)
    ratio_p50 = final.get("limiter_ratio_active", {}).get("p50", math.nan)
    ratio_p10 = final.get("limiter_ratio_active", {}).get("p10", math.nan)
    raw_delta_p99 = final.get("raw_delta_active", {}).get("p99", math.nan)
    blocked = (
        not np.isfinite(limiter_fraction)
        or limiter_fraction > 0.05
        or (np.isfinite(outer90_limiter) and outer90_limiter > 0)
        or (np.isfinite(ratio_p50) and ratio_p50 < 0.9)
    )
    root_cause = "undetermined_shadow_only"
    if rows:
        sphere_hits = final.get("sphere11_limiter_count", 0)
        total_hits = final.get("limiter_count", 0)
        outer_hits = final.get("outer90_limiter_count", 0)
        if total_hits and sphere_hits / total_hits > 0.9 and outer_hits == 0:
            root_cause = "sphere11_low_angle_candidate_dominated"
        if np.isfinite(raw_delta_p99) and raw_delta_p99 > 0.25:
            root_cause += "_raw_delta_exceeds_cap"
    return {
        "status": STATUS,
        "claim_limit": "runtime_sanity / exploratory_not_validation only",
        "write_mode_allowed": False,
        "write_mode_blocked": bool(blocked),
        "block_reason": "Stage8d is attribution-only; Stage8OperatorMode=2 remains forbidden",
        "root_cause_classification": root_cause,
        "final_limiter_fraction": limiter_fraction,
        "final_limiter_ratio_p50": ratio_p50,
        "final_limiter_ratio_p10": ratio_p10,
        "final_outer90_limiter_count": outer90_limiter,
        "final_raw_delta_p99": raw_delta_p99,
    }


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-root", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    frames = sorted((args.case_root / "output").glob("*_VTK_P00_*.vti"), key=step_of)
    if not frames:
        raise SystemExit(f"no VTI frames under {args.case_root / 'output'}")
    summaries: list[dict[str, Any]] = []
    bin_rows_all: list[dict[str, Any]] = []
    for frame in frames:
        summary, bin_rows = summarize_frame(frame)
        summaries.append(summary)
        bin_rows_all.extend(bin_rows)
    payload = {
        "status": STATUS,
        "claim_limit": "runtime_sanity / exploratory_not_validation only",
        "case_root": str(args.case_root),
        "decision": decision(summaries),
        "frames": summaries,
    }
    (args.out_dir / "stage8d_limiter_attribution_summary.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    write_csv(args.out_dir / "stage8d_limiter_attribution_summary.csv", [flatten_summary(r) for r in summaries])
    write_csv(args.out_dir / "stage8d_limiter_attribution_bins.csv", bin_rows_all)
    print(json.dumps({"status": STATUS, "decision": payload["decision"], "frames": [r["step"] for r in summaries]}, indent=2))


if __name__ == "__main__":
    main()
