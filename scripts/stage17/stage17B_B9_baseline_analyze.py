#!/usr/bin/env python3
"""Analyze Stage17B-B9 baseline-closure dense replay outputs.

The analyzer joins morphology, phase-update, pressure/stress, and force replay
quantities on one timeline. It is diagnostic-only and does not validate a
contact angle.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


SCALAR_FIELDS = [
    "PhaseField",
    "Rho",
    "P",
    "WallGhost",
    "WettingPathId",
    "ReplayPhaseFromH",
    "ReplayLapPhi",
    "ReplayMu",
    "ReplayRho",
    "ReplayTau",
    "ReplayPressureMoment",
    "ReplayHPreSum",
    "ReplayHPostSum",
    "ReplayHeqSum",
    "ReplayHPreMaxAbs",
    "ReplayHPostMaxAbs",
    "ReplayHeqMaxAbs",
    "ReplayFphiSum",
    "ReplayFphiMaxAbs",
    "ReplayTmp1",
    "ReplayTmp1BoundedShadow",
    "ReplayPhaseOutOfBoundsFlag",
    "ReplayPressureInput",
    "ReplayPressureForceScale",
    "ReplayPressurePhysicalInput",
    "ReplayStressXX",
    "ReplayStressYY",
    "ReplayStressZZ",
    "ReplayStressInputXX",
    "ReplayStressInputYY",
    "ReplayStressInputZZ",
    "ReplayStressIter1XX",
    "ReplayStressIter1YY",
    "ReplayStressIter1ZZ",
    "ReplayStressPreForceShadowXX",
    "ReplayStressPreForceShadowYY",
    "ReplayStressPreForceShadowZZ",
    "ReplayStressPostForceShadowXX",
    "ReplayStressPostForceShadowYY",
    "ReplayStressPostForceShadowZZ",
    "ReplayTauUsed",
    "ReplayRhoForForce",
    "ReplayPressureClosureMode",
    "ReplayForceDensityClosureMode",
    "ReplayForceFixedPointMode",
    "ReplayForceRhoRaw",
    "ReplayForceRhoEffective",
    "ForceIterCount",
    "ForceIterResidual",
    "B5SignedDistance",
    "B5NearWallBandFlag",
    "B5ContactLineBandFlag",
    "B5WallGhostConsumedFlag",
    "B5GradPhiNormal",
    "B5FphiNormalProxy",
    "B5PhaseFromHDelta",
]

VECTOR_FIELDS = [
    "U",
    "ReplayGradPhi",
    "ReplayFsurf",
    "ReplayFpressure",
    "ReplayFbody",
    "ReplayFmu",
    "ReplayFtotal",
    "ReplayUPreForce",
    "ReplayUPostForce",
    "ReplayPhaseAdvVelocity",
    "ReplayForceOverRho",
    "ReplayFmuIter1",
    "ReplayFtotalIter1",
    "ReplayUPostIter1",
    "ReplayNormal",
    "ReplayM0",
    "ReplayVelocityHalfForce",
    "ReplayMF",
    "ReplayMomentumAfterG",
    "ReplayMomentumDeltaG",
    "ReplayFpressureNoThird",
    "ReplayFpressurePhysical",
    "ReplayFmuRaw",
    "ReplayFmuDelta",
]


def step_from_case_name(name: str) -> int:
    match = re.search(r"_s(\d+)$", name)
    if not match:
        return -1
    return int(match.group(1))


def load_vti(path: Path) -> tuple[tuple[int, int, int], dict[str, np.ndarray]]:
    import vtk  # type: ignore
    from vtk.util.numpy_support import vtk_to_numpy  # type: ignore

    reader = vtk.vtkXMLImageDataReader()
    reader.SetFileName(str(path))
    reader.Update()
    image = reader.GetOutput()
    dims = tuple(int(v) - 1 for v in image.GetDimensions())
    cell_data = image.GetCellData()
    arrays: dict[str, np.ndarray] = {}
    for idx in range(cell_data.GetNumberOfArrays()):
        arr = cell_data.GetArray(idx)
        if arr is not None:
            arrays[arr.GetName() or f"array_{idx}"] = vtk_to_numpy(arr).copy()
    return dims, arrays


def reshape_scalar(values: np.ndarray, dims: tuple[int, int, int]) -> np.ndarray:
    nx, ny, nz = dims
    return np.asarray(values, dtype=float).reshape((nz, ny, nx))


def scalar_values(arrays: dict[str, np.ndarray], field: str) -> np.ndarray | None:
    arr = arrays.get(field)
    if arr is None:
        return None
    values = np.asarray(arr, dtype=float)
    if values.ndim == 2:
        return np.linalg.norm(values, axis=1)
    return values.ravel()


def stats(values: np.ndarray | None, mask: np.ndarray | None = None) -> dict[str, Any]:
    if values is None:
        return {"present": False}
    vals = np.asarray(values, dtype=float).ravel()
    if mask is not None:
        vals = vals[np.asarray(mask, dtype=bool).ravel()]
    finite = np.isfinite(vals)
    out: dict[str, Any] = {
        "present": True,
        "count": int(vals.size),
        "nonfinite": int(vals.size - np.count_nonzero(finite)),
    }
    vals = vals[finite]
    if vals.size == 0:
        out.update({"min": None, "max": None, "mean": None, "max_abs": None})
        return out
    out.update(
        {
            "min": float(np.min(vals)),
            "max": float(np.max(vals)),
            "mean": float(np.mean(vals)),
            "max_abs": float(np.max(np.abs(vals))),
        }
    )
    return out


def weighted_percentile(values: np.ndarray, weights: np.ndarray, percentile: float) -> float | None:
    vals = np.asarray(values, dtype=float).ravel()
    wts = np.asarray(weights, dtype=float).ravel()
    good = np.isfinite(vals) & np.isfinite(wts) & (wts > 0.0)
    if not np.count_nonzero(good):
        return None
    vals = vals[good]
    wts = wts[good]
    order = np.argsort(vals)
    vals = vals[order]
    wts = wts[order]
    cdf = np.cumsum(wts)
    target = percentile / 100.0 * cdf[-1]
    idx = int(np.searchsorted(cdf, target, side="left"))
    return float(vals[min(max(idx, 0), vals.size - 1)])


def cylinder_geometry(
    dims: tuple[int, int, int],
    meta: dict[str, Any],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    nx, ny, nz = dims
    sx, sy, _sz = [float(v) for v in meta["solid_center"]]
    sr = float(meta["solid_radius"])
    x = np.arange(nx, dtype=float)[None, None, :] + 0.5
    y = np.arange(ny, dtype=float)[None, :, None] + 0.5
    dx = x - sx
    dy = y - sy
    radius = np.sqrt(dx * dx + dy * dy)
    signed_distance = np.broadcast_to(radius - sr, (nz, ny, nx))
    alpha = np.broadcast_to(np.degrees(np.arctan2(dx, dy)), (nz, ny, nx))
    ycoord = np.broadcast_to(y, (nz, ny, nx))
    return signed_distance, alpha, ycoord


def contour_points(phase_2d: np.ndarray, level: float = 0.5) -> np.ndarray:
    pts: list[tuple[float, float]] = []
    values = np.where(np.isfinite(phase_2d), phase_2d, np.nan)
    rows, cols = values.shape
    for row in range(rows):
        for col in range(cols - 1):
            a, b = values[row, col], values[row, col + 1]
            if np.isfinite(a) and np.isfinite(b) and a != b and (a - level) * (b - level) <= 0:
                pts.append((col + 0.5 + (level - a) / (b - a), row + 0.5))
    for col in range(cols):
        for row in range(rows - 1):
            a, b = values[row, col], values[row + 1, col]
            if np.isfinite(a) and np.isfinite(b) and a != b and (a - level) * (b - level) <= 0:
                pts.append((col + 0.5, row + 0.5 + (level - a) / (b - a)))
    return np.asarray(pts, dtype=float) if pts else np.empty((0, 2), dtype=float)


def fit_circle(points: np.ndarray) -> dict[str, float] | None:
    if len(points) < 8:
        return None
    x = points[:, 0]
    y = points[:, 1]
    matrix = np.column_stack([2.0 * x, 2.0 * y, np.ones_like(x)])
    rhs = x * x + y * y
    sol, *_ = np.linalg.lstsq(matrix, rhs, rcond=None)
    cx, cy, c0 = [float(v) for v in sol]
    r2 = c0 + cx * cx + cy * cy
    if r2 <= 0.0:
        return None
    radius = math.sqrt(r2)
    residual = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) - radius
    return {"cx": cx, "cy": cy, "r": radius, "rms": float(np.sqrt(np.mean(residual * residual)))}


def slice_metrics(phase: np.ndarray, boundary: np.ndarray | None, meta: dict[str, Any]) -> dict[str, Any]:
    iz = int(np.clip(round(float(meta.get("slice_index", 48))), 0, phase.shape[0] - 1))
    p2 = phase[iz, :, :]
    b2 = boundary[iz, :, :] if boundary is not None else None
    fluid = np.isfinite(p2)
    if b2 is not None:
        fluid &= b2 <= 0.5
    liquid = fluid & (p2 >= 0.5)
    out: dict[str, Any] = {"slice_index": iz}
    if np.any(liquid):
        rows, cols = np.where(liquid)
        out.update(
            {
                "slice_liquid_area_cells": int(liquid.sum()),
                "slice_footprint_cells": int(cols.max() - cols.min() + 1),
                "slice_height_cells": int(rows.max() - rows.min() + 1),
                "slice_centroid_y": float(np.mean(rows + 0.5)),
                "slice_y_min": float(rows.min() + 0.5),
                "slice_y_max": float(rows.max() + 0.5),
            }
        )
    else:
        out.update(
            {
                "slice_liquid_area_cells": 0,
                "slice_footprint_cells": 0,
                "slice_height_cells": 0,
                "slice_centroid_y": None,
                "slice_y_min": None,
                "slice_y_max": None,
            }
        )
    phase_plot = np.where(b2 > 0.5, np.nan, p2) if b2 is not None else p2
    points = contour_points(phase_plot)
    fit = fit_circle(points)
    out["contour_point_count"] = int(len(points))
    out["circle_fit_radius"] = fit["r"] if fit else None
    out["circle_fit_rms"] = fit["rms"] if fit else None
    return out


def summarize_frame(case_dir: Path) -> dict[str, Any]:
    meta = json.loads((case_dir / "case_metadata.json").read_text(encoding="utf-8"))
    final_step = int(meta["final_step"])
    vti = case_dir / "output" / f"case_VTK_P00_{final_step:08d}.vti"
    if not vti.exists():
        raise FileNotFoundError(vti)
    dims, arrays = load_vti(vti)
    phase = reshape_scalar(arrays["PhaseField"], dims)
    boundary_source = arrays.get("IsItBoundary", arrays.get("BOUNDARY"))
    boundary = reshape_scalar(boundary_source, dims) if boundary_source is not None else None
    sd, alpha, ycoord = cylinder_geometry(dims, meta)
    fluid = np.isfinite(phase)
    if boundary is not None:
        fluid &= boundary <= 0.5
    near = fluid & (sd >= 0.0) & (sd <= 3.0)
    interface = near & (phase > 0.05) & (phase < 0.95)
    liquid = fluid & (phase >= 0.5)
    weights = np.maximum(phase * (1.0 - phase), 0.0)

    frame: dict[str, Any] = {
        "case": case_dir.name,
        "group": meta.get("b9_group"),
        "label": meta.get("b9_label"),
        "tier": meta.get("b9_tier"),
        "step": final_step,
        "vti": str(vti),
        "phase_min": float(np.nanmin(phase)),
        "phase_max": float(np.nanmax(phase)),
        "phase_nonfinite": int(phase.size - np.count_nonzero(np.isfinite(phase))),
        "analytic_near_wall_cells": int(np.count_nonzero(near)),
        "analytic_contact_cells": int(np.count_nonzero(interface)),
        "liquid_volume_cells": int(np.count_nonzero(liquid)),
        "liquid_centroid_y": float(np.mean(ycoord[liquid])) if np.count_nonzero(liquid) else None,
    }
    if np.count_nonzero(interface):
        vals = np.abs(alpha[interface])
        wts = weights[interface]
        frame["contact_half_width_w95_deg"] = weighted_percentile(vals, wts, 95.0)
        frame["contact_y_min"] = float(np.nanmin(ycoord[interface]))
        frame["contact_y_mean"] = float(np.average(ycoord[interface], weights=wts))
    else:
        frame["contact_half_width_w95_deg"] = None
        frame["contact_y_min"] = None
        frame["contact_y_mean"] = None
    frame.update(slice_metrics(phase, boundary, meta))

    flat_near = near.ravel()
    flat_contact = interface.ravel()
    field_stats: dict[str, Any] = {}
    for field in SCALAR_FIELDS + VECTOR_FIELDS:
        values = scalar_values(arrays, field)
        field_stats[field] = {
            "all": stats(values),
            "near": stats(values, flat_near),
            "contact": stats(values, flat_contact),
        }
    frame["field_stats"] = field_stats
    for field in SCALAR_FIELDS + VECTOR_FIELDS:
        near_stats = field_stats[field]["near"]
        contact_stats = field_stats[field]["contact"]
        all_stats = field_stats[field]["all"]
        frame[f"{field}_near_max_abs"] = near_stats.get("max_abs")
        frame[f"{field}_near_mean"] = near_stats.get("mean")
        frame[f"{field}_contact_mean"] = contact_stats.get("mean")
        frame[f"{field}_all_max_abs"] = all_stats.get("max_abs")
        frame[f"{field}_nonfinite"] = all_stats.get("nonfinite")
    return frame


def attach_deltas(frames: list[dict[str, Any]]) -> None:
    by_group: dict[str, dict[str, Any]] = {}
    for frame in sorted(frames, key=lambda item: (str(item.get("group")), int(item["step"]))):
        group = str(frame.get("group"))
        if group not in by_group:
            by_group[group] = frame
        base = by_group[group]
        for key in [
            "contact_half_width_w95_deg",
            "contact_y_min",
            "contact_y_mean",
            "liquid_volume_cells",
            "liquid_centroid_y",
            "slice_liquid_area_cells",
            "slice_footprint_cells",
            "slice_height_cells",
            "slice_centroid_y",
        ]:
            value = frame.get(key)
            base_value = base.get(key)
            frame[f"{key}_delta"] = (
                float(value - base_value)
                if value is not None and base_value is not None
                else None
            )


def compact_frame(frame: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in frame.items() if key != "field_stats"}


def classify(frames: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "status": "classified",
        "claim_limit": "B9 root-cause triage only; not contact-angle validation",
    }
    b_frames = [frame for frame in frames if frame.get("group") == "B"]
    a_frames = [frame for frame in frames if frame.get("group") == "A"]
    selected = b_frames if b_frames else a_frames
    selected = sorted(selected, key=lambda item: int(item["step"]))
    if not selected:
        out["primary_suspect"] = "missing_frames"
        return out

    def field_present(frame: dict[str, Any], field: str) -> bool:
        return bool(
            ((frame.get("field_stats", {}).get(field, {}) or {}).get("all", {}) or {}).get(
                "present", False
            )
        )

    def max_present_scale(frame: dict[str, Any], fields: list[str]) -> float | None:
        values: list[float] = []
        for field in fields:
            if field_present(frame, field):
                value = frame.get(f"{field}_near_max_abs")
                if value is not None and np.isfinite(float(value)):
                    values.append(float(value))
        return max(values) if values else None

    def first_step_where(key: str, predicate) -> int | None:
        for frame in selected:
            value = frame.get(key)
            if value is not None and predicate(float(value)):
                return int(frame["step"])
        return None

    first_drift = None
    for frame in selected:
        delta = frame.get("contact_half_width_w95_deg_delta")
        if delta is not None and abs(delta) > 0.25:
            first_drift = frame["step"]
            break
    out["first_contact_half_width_drift_step"] = first_drift
    out["first_contact_ymin_motion_step"] = first_step_where(
        "contact_y_min_delta", lambda value: abs(value) > 0.25
    )
    out["first_liquid_volume_delta_step"] = first_step_where(
        "liquid_volume_cells_delta", lambda value: abs(value) > 0.5
    )
    out["first_phase_out_of_bounds_step"] = first_step_where(
        "ReplayPhaseOutOfBoundsFlag_near_max_abs", lambda value: value > 0.5
    )
    final = selected[-1]
    candidates = {
        "phase_update": max_present_scale(
            final,
            [
                "ReplayFphiMaxAbs",
                "ReplayTmp1",
                "ReplayHPostMaxAbs",
                "ReplayPhaseFromH",
            ],
        ),
        "pressure_force": max_present_scale(final, ["ReplayFpressure"]),
        "fmu_stress": max_present_scale(
            final,
            [
                "ReplayFmu",
                "ReplayFmuDelta",
                "ReplayStressInputXX",
                "ReplayStressInputYY",
                "ReplayStressInputZZ",
            ],
        ),
        "force_over_rho": max_present_scale(final, ["ReplayForceOverRho"]),
    }
    out["final_nearwall_candidate_scales"] = candidates
    out["available_candidate_fields"] = {
        "phase_update": candidates["phase_update"] is not None,
        "pressure_force": candidates["pressure_force"] is not None,
        "fmu_stress": candidates["fmu_stress"] is not None,
        "force_over_rho": candidates["force_over_rho"] is not None,
    }
    out["tier"] = final.get("tier")
    out["momentum_diagnostic_limit"] = (
        "Momentum fields are absent in the lite tier; pressure/F_mu/force-over-rho "
        "cannot be cleared by this run."
        if not out["available_candidate_fields"]["force_over_rho"]
        else None
    )

    if out["first_phase_out_of_bounds_step"] is not None and (
        first_drift is None or out["first_phase_out_of_bounds_step"] <= first_drift
    ):
        out["primary_suspect"] = "phase_boundedness_or_initialization_release"
    elif out["first_contact_ymin_motion_step"] is not None and (
        first_drift is None or out["first_contact_ymin_motion_step"] < first_drift
    ):
        out["primary_suspect"] = "early_contact_line_geometry_relaxation"
    elif first_drift is not None and first_drift <= 2:
        out["primary_suspect"] = "initialization_discrete_equilibrium_or_metric_threshold"
    elif candidates["force_over_rho"] is not None and candidates["force_over_rho"] > 1.0:
        out["primary_suspect"] = "momentum_force_feedback"
    elif (
        candidates["pressure_force"] is not None
        and candidates["phase_update"] is not None
        and candidates["pressure_force"] > candidates["phase_update"]
        and candidates["pressure_force"] > 1.0e-4
    ):
        out["primary_suspect"] = "pressure_closure_bias"
    elif (
        candidates["fmu_stress"] is not None
        and candidates["phase_update"] is not None
        and candidates["fmu_stress"] > candidates["phase_update"]
        and candidates["fmu_stress"] > 1.0e-4
    ):
        out["primary_suspect"] = "fmu_stress_timelevel_bias"
    else:
        out["primary_suspect"] = "phase_initialization_or_metric_sensitivity"
    return out


def write_csv(path: Path, frames: list[dict[str, Any]]) -> None:
    rows = [compact_frame(frame) for frame in frames]
    fields = sorted({key for row in rows for key in row})
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def draw_timeseries(frames: list[dict[str, Any]], out_png: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(10.0, 7.2), constrained_layout=True)
    for group, group_frames in sorted(
        ((g, [f for f in frames if f.get("group") == g]) for g in sorted({f.get("group") for f in frames})),
        key=lambda item: str(item[0]),
    ):
        group_frames = sorted(group_frames, key=lambda item: int(item["step"]))
        steps = [frame["step"] for frame in group_frames]
        label = str(group)
        axes[0, 0].plot(steps, [frame.get("contact_half_width_w95_deg_delta") for frame in group_frames], marker="o", label=label)
        axes[0, 1].plot(steps, [frame.get("contact_y_min_delta") for frame in group_frames], marker="o", label=label)
        axes[1, 0].plot(steps, [frame.get("ReplayForceOverRho_near_max_abs") for frame in group_frames], marker="o", label=label)
        axes[1, 1].plot(steps, [frame.get("ReplayFphiMaxAbs_near_max_abs") for frame in group_frames], marker="o", label=label)
    axes[0, 0].set_ylabel("contact half-width delta (deg)")
    axes[0, 1].set_ylabel("contact y-min delta (lu)")
    axes[1, 0].set_ylabel("near-wall |F/rho| max")
    axes[1, 1].set_ylabel("near-wall |Fphi| max")
    for ax in axes.ravel():
        ax.set_xlabel("step")
        ax.grid(True, alpha=0.25)
        ax.legend()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=220)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--out-json", type=Path, default=None)
    parser.add_argument("--out-csv", type=Path, default=None)
    parser.add_argument("--out-png", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    case_dirs = sorted(
        [path for path in args.root.iterdir() if path.is_dir() and (path / "case.xml").exists()],
        key=lambda path: (path.name, step_from_case_name(path.name)),
    )
    frames = [summarize_frame(path) for path in case_dirs]
    attach_deltas(frames)
    frames = sorted(frames, key=lambda item: (str(item.get("group")), int(item["step"])))
    classification = classify(frames)
    failures: list[str] = []
    for frame in frames:
        if frame.get("phase_nonfinite", 0):
            failures.append(f"{frame['case']}:phase_nonfinite")
        run_status = (Path(args.root) / frame["case"] / "run.status").read_text(
            encoding="utf-8", errors="replace"
        )
        if "RC=0" not in run_status:
            failures.append(f"{frame['case']}:missing_rc0")
    status = "PASS_STAGE17B_B9_BASELINE_TRIAGE" if not failures else "FAIL_STAGE17B_B9_BASELINE_TRIAGE"
    out_json = args.out_json or (args.root / "stage17B_B9_baseline_analysis.json")
    out_csv = args.out_csv or (args.root / "stage17B_B9_baseline_frames.csv")
    out_png = args.out_png or (args.root / "stage17B_B9_baseline_timeseries.png")
    write_csv(out_csv, frames)
    draw_timeseries(frames, out_png)
    summary = {
        "root": str(args.root),
        "status": status,
        "failures": failures,
        "classification": classification,
        "frames_csv": str(out_csv),
        "timeseries_png": str(out_png),
        "claim_limit": "B9 baseline closure diagnostic only; not contact-angle validation",
        "frames": [compact_frame(frame) for frame in frames],
    }
    out_json.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "frames"}, indent=2, sort_keys=True))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
