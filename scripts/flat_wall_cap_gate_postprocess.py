#!/usr/bin/env python3
"""Postprocess flat-wall spherical-cap gate runs.

This intentionally combines only gate-level metrics: finiteness, phase/mass
drift, apparent contact angle, and wall reconstruction diagnostics. It is not a
publication or validation postprocessor.
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
import vtk
from vtk.util.numpy_support import vtk_to_numpy


STATUS = "runtime_sanity"
STEP_RE = re.compile(r"_VTK_P\d+_(\d{8})\.vti$")
CS = math.sqrt(1.0 / 3.0)


def step_of(path: Path) -> int:
    match = STEP_RE.search(path.name)
    return int(match.group(1)) if match else -1


def read_vti(path: Path) -> tuple[tuple[int, int, int], dict[str, np.ndarray]]:
    reader = vtk.vtkXMLImageDataReader()
    reader.SetFileName(str(path))
    reader.Update()
    image = reader.GetOutput()
    dims = tuple(int(value) - 1 for value in image.GetDimensions())
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
    out = np.asarray(values, dtype=float)
    if out.ndim > 1:
        out = out[:, 0]
    return out


def vector_mag(values: np.ndarray | None) -> np.ndarray | None:
    if values is None:
        return None
    out = np.asarray(values, dtype=float)
    if out.ndim == 1:
        return np.abs(out)
    return np.linalg.norm(out[:, :3], axis=1)


def reshape(values: np.ndarray, dims: tuple[int, int, int]) -> np.ndarray:
    nx, ny, nz = dims
    return np.asarray(values, dtype=float).reshape((nz, ny, nx)).transpose(2, 1, 0)


def stats(values: np.ndarray, mask: np.ndarray | None = None) -> dict[str, float | int]:
    arr = np.asarray(values, dtype=float)
    if mask is not None:
        arr = arr[mask]
    out: dict[str, float | int] = {
        "count": int(arr.size),
        "nonfinite": int(np.count_nonzero(~np.isfinite(arr))),
    }
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        return out
    nonzero = finite != 0.0
    out.update(
        {
            "min": float(np.min(finite)),
            "mean": float(np.mean(finite)),
            "p01": float(np.percentile(finite, 1)),
            "p50": float(np.percentile(finite, 50)),
            "p99": float(np.percentile(finite, 99)),
            "max": float(np.max(finite)),
            "sum": float(np.sum(finite)),
            "nonzero_count": int(np.count_nonzero(nonzero)),
            "positive_count": int(np.count_nonzero(finite > 0.0)),
            "negative_count": int(np.count_nonzero(finite < 0.0)),
        }
    )
    return out


def circle_fit(points: np.ndarray) -> tuple[float, float, float]:
    x = points[:, 0]
    y = points[:, 1]
    a = np.column_stack((2.0 * x, 2.0 * y, np.ones_like(x)))
    b = x * x + y * y
    cx, cy, c = np.linalg.lstsq(a, b, rcond=None)[0]
    radius = math.sqrt(max(c + cx * cx + cy * cy, 0.0))
    return float(cx), float(cy), float(radius)


def contour_points(section: np.ndarray, threshold: float, min_y: float) -> np.ndarray:
    fig, ax = plt.subplots()
    contour = ax.contour(section, levels=[threshold])
    plt.close(fig)
    pts: list[np.ndarray] = []
    collections = getattr(contour, "collections", None)
    if collections is not None:
        for collection in collections:
            for path in collection.get_paths():
                if path.vertices.size:
                    pts.append(path.vertices)
    else:
        for level_segments in getattr(contour, "allsegs", []):
            for vertices in level_segments:
                if vertices.size:
                    pts.append(vertices)
    if not pts:
        return np.empty((0, 2))
    points = np.vstack(pts)
    return points[points[:, 1] >= min_y]


def angle_from_fit(fit: tuple[float, float, float], wall_y: float) -> float:
    # Contour coordinates are (normal y, tangential z) because the section is
    # phase[x_mid, y, z].T.  Use the fitted center's normal coordinate.
    cy, _cz, radius = fit
    if radius <= 0.0:
        return math.nan
    value = (wall_y - cy) / radius
    value = max(-1.0, min(1.0, value))
    return math.degrees(math.acos(value))


def summarize_frame(
    path: Path,
    *,
    case_id: str,
    case_params: dict[str, Any],
    threshold: float,
    min_wall_distance: float,
) -> tuple[dict[str, Any], dict[str, np.ndarray], tuple[int, int, int], np.ndarray, np.ndarray, tuple[float, float, float] | None]:
    dims, arrays = read_vti(path)
    phase = scalar(arrays.get("PhaseField"))
    if phase is None:
        raise RuntimeError(f"{path} has no PhaseField")
    boundary = scalar(arrays.get("BOUNDARY"))
    if boundary is None:
        boundary = scalar(arrays.get("IsItBoundary"))
    if boundary is None:
        boundary = scalar(arrays.get("BoundaryMask"))
    if boundary is None:
        wall_mask = np.zeros_like(phase, dtype=bool)
    else:
        wall_mask = np.isfinite(boundary) & (boundary != 0.0)
    fluid_mask = ~wall_mask
    y0_mask = np.zeros_like(phase, dtype=bool)
    idx = np.arange(phase.size)
    nx, ny, _nz = dims
    y = (idx // nx) % ny
    y0_mask = y == 0
    lower_wall_mask = wall_mask & y0_mask

    fields: dict[str, np.ndarray] = {"PhaseField": phase}
    for name in [
        "Rho",
        "WallPfF",
        "WallGradTangent",
        "WallTanCoeff",
        "WallPhasePred",
        "WallPhaseProfilePred",
        "WallProfileDelta",
        "WallPhaseSignedProfilePred",
        "WallSignedProfileDelta",
        "WallSignedLogitShift",
        "WallFluidSampleCount",
        "WallFluidSampleH",
        "WallPhaseRawPred",
        "WallPhaseSignedPred",
        "WallContactResidual",
        "WallSignedNormalGrad",
        "WallTangentGradMag",
        "WallSignedDeltaQ",
        "WallSignedQClipped",
        "BoundaryMask",
        "WallStage7Mode",
        "WallStage7ActiveWeight",
        "WallStage7DeltaQRaw",
        "WallStage7DeltaQLimited",
        "WallStage7Denom",
        "WallStage7LimiterReason",
        "WallStage7GradMag",
        "WallStage7ActualCos",
        "WallStage7TargetCos",
        "WallStage7WriteCandidate",
        "WallStage7WriteMinusProfile",
        "WallH",
        "WallNormalCoeff1",
        "WallNormalCoeff2",
        "WallActualMinusProfile",
        "WallActualMinusRaw",
        "WallBCPath",
        "SpecialBoundaryPoint",
    ]:
        arr = scalar(arrays.get(name))
        if arr is not None:
            fields[name] = arr
    for name in ["WallGeomNormal", "WallGrad1", "WallGrad2", "WallGradTangentVec"]:
        mag = vector_mag(arrays.get(name))
        if mag is not None:
            fields[f"{name}Mag"] = mag
    u_mag = vector_mag(arrays.get("U"))
    if u_mag is not None:
        fields["UMag"] = u_mag

    phase_arr = reshape(phase, dims)
    x_mid = dims[0] // 2
    section = phase_arr[x_mid, :, :].T
    points = contour_points(section, threshold, min_wall_distance)
    fit = circle_fit(points) if points.shape[0] >= 12 else None
    apparent = angle_from_fit(fit, 0.0) if fit is not None else math.nan

    path_code = fields.get("WallBCPath")
    path_counts: dict[str, int] = {}
    if path_code is not None:
        codes = np.rint(path_code[wall_mask][np.isfinite(path_code[wall_mask])]).astype(int)
        for code in sorted(np.unique(codes)):
            path_counts[str(int(code))] = int(np.count_nonzero(codes == code))

    rec: dict[str, Any] = {
        "status": STATUS,
        "case_id": case_id,
        "step": step_of(path),
        "file": str(path),
        "dims": list(dims),
        "case_params": case_params,
        "cell_count": int(phase.size),
        "wall_count": int(np.count_nonzero(wall_mask)),
        "fluid_count": int(np.count_nonzero(fluid_mask)),
        "lower_wall_count": int(np.count_nonzero(lower_wall_mask)),
        "nonfinite_total": int(sum(np.count_nonzero(~np.isfinite(v)) for v in fields.values())),
        "angle_apparent_deg": apparent,
        "angle_error_vs_init_deg": apparent - float(case_params.get("init_theta_deg", math.nan)),
        "angle_error_vs_wall_rad_deg": apparent - float(case_params.get("wall_rad_angle_deg", math.nan)),
        "fit_point_count": int(points.shape[0]),
        "fit_circle": list(fit) if fit is not None else None,
        "wall_bc_path_counts": path_counts,
        "field_stats": {},
    }
    for name, values in fields.items():
        rec["field_stats"][name] = {
            "all": stats(values),
            "fluid": stats(values, fluid_mask),
            "wall": stats(values, wall_mask),
            "lower_wall": stats(values, lower_wall_mask),
        }
    limiter = fields.get("WallStage7LimiterReason")
    active = fields.get("WallStage7ActiveWeight")
    path = fields.get("WallBCPath")
    if limiter is not None and active is not None:
        limiter_arr = np.asarray(limiter, dtype=float)
        active_arr = np.asarray(active, dtype=float)
        normal_path = np.isfinite(active_arr) & (active_arr > 0.0)
        if path is not None:
            path_arr = np.asarray(path, dtype=float)
            normal_path = np.isfinite(path_arr) & (np.rint(path_arr).astype(int) == 5)
        active_path = normal_path & np.isfinite(active_arr) & (active_arr > 0.0)
        limiter_nonzero = np.isfinite(limiter_arr) & (limiter_arr != 0.0)
        rec["stage7b_limiter_counts"] = {
            "normal_path_count": int(np.count_nonzero(normal_path)),
            "normal_limiter_count": int(np.count_nonzero(normal_path & limiter_nonzero)),
            "active_path_count": int(np.count_nonzero(active_path)),
            "active_limiter_count": int(np.count_nonzero(active_path & limiter_nonzero)),
        }
    else:
        rec["stage7b_limiter_counts"] = {
            "normal_path_count": 0,
            "normal_limiter_count": 0,
            "active_path_count": 0,
            "active_limiter_count": 0,
        }
    if "UMag" in fields:
        rec["max_mach"] = float(np.nanmax(fields["UMag"][fluid_mask]) / CS)
    else:
        rec["max_mach"] = math.nan
    return rec, fields, dims, section, points, fit


def plot_frame(
    out_dir: Path,
    rec: dict[str, Any],
    fields: dict[str, np.ndarray],
    dims: tuple[int, int, int],
    section: np.ndarray,
    points: np.ndarray,
    fit: tuple[float, float, float] | None,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    x_mid = dims[0] // 2
    phase = reshape(fields["PhaseField"], dims)
    pred_name = "WallPhaseRawPred" if "WallPhaseRawPred" in fields else "WallPhasePred"
    signed_name = (
        "WallPhaseSignedPred"
        if "WallPhaseSignedPred" in fields
        else "WallPhaseSignedProfilePred"
    )
    pred = reshape(fields.get(pred_name, np.zeros_like(fields["PhaseField"])), dims)
    profile = reshape(fields.get("WallPhaseProfilePred", np.zeros_like(fields["PhaseField"])), dims)
    signed = reshape(fields.get(signed_name, np.zeros_like(fields["PhaseField"])), dims)
    residual = reshape(fields.get("WallContactResidual", np.zeros_like(fields["PhaseField"])), dims)
    path_code = reshape(fields.get("WallBCPath", np.zeros_like(fields["PhaseField"])), dims)

    fig, axes = plt.subplots(2, 3, figsize=(13, 8), dpi=160)
    panels = [
        (section, "PhaseField x-mid", 0.0, 1.0),
        (pred[x_mid, :, :].T, pred_name, 0.0, 1.5),
        (profile[x_mid, :, :].T, "WallPhaseProfilePred", 0.0, 1.0),
        (signed[x_mid, :, :].T, signed_name, 0.0, 1.0),
        (residual[x_mid, :, :].T, "WallContactResidual", -0.5, 0.5),
        (path_code[x_mid, :, :].T, "WallBCPath", 0.0, 5.0),
    ]
    for ax, (arr, title, vmin, vmax) in zip(axes.ravel(), panels):
        im = ax.imshow(arr, origin="lower", vmin=vmin, vmax=vmax, cmap="viridis", aspect="equal")
        ax.set_title(title)
        ax.set_xticks([])
        ax.set_yticks([])
        fig.colorbar(im, ax=ax, fraction=0.045, pad=0.03)
    if points.size:
        axes[0, 0].plot(points[:, 0], points[:, 1], "w.", markersize=1.0)
    if fit is not None:
        cx, cy, radius = fit
        t = np.linspace(0.0, 2.0 * math.pi, 500)
        axes[0, 0].plot(cx + radius * np.cos(t), cy + radius * np.sin(t), "r-", linewidth=0.8)
    fig.suptitle(
        f"{rec['case_id']} step={rec['step']} theta={rec['angle_apparent_deg']:.2f} "
        f"mass fluid={rec['field_stats']['PhaseField']['fluid']['sum']:.6g} "
        f"Mach={rec['max_mach']:.3e}"
    )
    fig.tight_layout()
    fig.savefig(out_dir / f"{rec['case_id']}_step{rec['step']:08d}_flat_gate.png")
    plt.close(fig)


def row_from_rec(rec: dict[str, Any], baseline: dict[str, float]) -> dict[str, Any]:
    phase_fluid = rec["field_stats"]["PhaseField"]["fluid"]
    rho_fluid = rec["field_stats"].get("Rho", {}).get("fluid", {})
    wall_pred = rec["field_stats"].get("WallPhasePred", {}).get("wall", {})
    wall_raw = rec["field_stats"].get("WallPhaseRawPred", {}).get("wall", {})
    wall_profile = rec["field_stats"].get("WallPhaseProfilePred", {}).get("wall", {})
    wall_signed_profile = rec["field_stats"].get("WallPhaseSignedProfilePred", {}).get("wall", {})
    wall_signed = rec["field_stats"].get("WallPhaseSignedPred", {}).get("wall", {})
    wall_shift = rec["field_stats"].get("WallSignedLogitShift", {}).get("wall", {})
    wall_residual = rec["field_stats"].get("WallContactResidual", {}).get("wall", {})
    wall_signed_grad = rec["field_stats"].get("WallSignedNormalGrad", {}).get("wall", {})
    wall_tangent_grad = rec["field_stats"].get("WallTangentGradMag", {}).get("wall", {})
    wall_delta_q = rec["field_stats"].get("WallSignedDeltaQ", {}).get("wall", {})
    wall_q_clipped = rec["field_stats"].get("WallSignedQClipped", {}).get("wall", {})
    wall_stage7_active = rec["field_stats"].get("WallStage7ActiveWeight", {}).get("wall", {})
    wall_stage7_dq_raw = rec["field_stats"].get("WallStage7DeltaQRaw", {}).get("wall", {})
    wall_stage7_dq_limited = rec["field_stats"].get("WallStage7DeltaQLimited", {}).get("wall", {})
    wall_stage7_denom = rec["field_stats"].get("WallStage7Denom", {}).get("wall", {})
    wall_stage7_limiter = rec["field_stats"].get("WallStage7LimiterReason", {}).get("wall", {})
    wall_stage7_actual_cos = rec["field_stats"].get("WallStage7ActualCos", {}).get("wall", {})
    wall_stage7_target_cos = rec["field_stats"].get("WallStage7TargetCos", {}).get("wall", {})
    wall_stage7_candidate = rec["field_stats"].get("WallStage7WriteCandidate", {}).get("wall", {})
    wall_stage7_minus_profile = rec["field_stats"].get("WallStage7WriteMinusProfile", {}).get("wall", {})
    limiter_counts = rec.get("stage7b_limiter_counts", {})
    phase_sum = float(phase_fluid.get("sum", math.nan))
    rho_sum = float(rho_fluid.get("sum", math.nan))
    phase_rel = (
        (phase_sum - baseline["phase_fluid_sum"]) / baseline["phase_fluid_sum"]
        if baseline.get("phase_fluid_sum", 0.0)
        else math.nan
    )
    rho_rel = (
        (rho_sum - baseline["rho_fluid_sum"]) / baseline["rho_fluid_sum"]
        if baseline.get("rho_fluid_sum", 0.0)
        else math.nan
    )
    return {
        "case_id": rec["case_id"],
        "step": rec["step"],
        "init_theta_deg": rec["case_params"].get("init_theta_deg"),
        "wall_rad_angle_deg": rec["case_params"].get("wall_rad_angle_deg"),
        "angle_apparent_deg": rec["angle_apparent_deg"],
        "angle_error_vs_init_deg": rec["angle_error_vs_init_deg"],
        "angle_error_vs_wall_rad_deg": rec["angle_error_vs_wall_rad_deg"],
        "fit_point_count": rec["fit_point_count"],
        "phase_fluid_sum": phase_sum,
        "phase_fluid_rel_change": phase_rel,
        "rho_fluid_sum": rho_sum,
        "rho_fluid_rel_change": rho_rel,
        "phase_fluid_min": phase_fluid.get("min", math.nan),
        "phase_fluid_max": phase_fluid.get("max", math.nan),
        "wall_phase_pred_min": wall_pred.get("min", math.nan),
        "wall_phase_pred_max": wall_pred.get("max", math.nan),
        "wall_phase_raw_min": wall_raw.get("min", math.nan),
        "wall_phase_raw_max": wall_raw.get("max", math.nan),
        "wall_phase_profile_max": wall_profile.get("max", math.nan),
        "wall_phase_signed_profile_max": wall_signed_profile.get("max", math.nan),
        "wall_phase_signed_min": wall_signed.get("min", math.nan),
        "wall_phase_signed_max": wall_signed.get("max", math.nan),
        "wall_signed_logit_shift_max": wall_shift.get("max", math.nan),
        "wall_contact_residual_mean": wall_residual.get("mean", math.nan),
        "wall_contact_residual_min": wall_residual.get("min", math.nan),
        "wall_contact_residual_max": wall_residual.get("max", math.nan),
        "wall_signed_normal_grad_mean": wall_signed_grad.get("mean", math.nan),
        "wall_tangent_grad_mag_mean": wall_tangent_grad.get("mean", math.nan),
        "wall_signed_delta_q_min": wall_delta_q.get("min", math.nan),
        "wall_signed_delta_q_max": wall_delta_q.get("max", math.nan),
        "wall_signed_q_clipped_sum": wall_q_clipped.get("sum", math.nan),
        "wall_stage7_active_weight_sum": wall_stage7_active.get("sum", math.nan),
        "wall_stage7_active_weight_mean": wall_stage7_active.get("mean", math.nan),
        "wall_stage7_delta_q_raw_p50": wall_stage7_dq_raw.get("p50", math.nan),
        "wall_stage7_delta_q_raw_p99": wall_stage7_dq_raw.get("p99", math.nan),
        "wall_stage7_delta_q_raw_max": wall_stage7_dq_raw.get("max", math.nan),
        "wall_stage7_delta_q_limited_p50": wall_stage7_dq_limited.get("p50", math.nan),
        "wall_stage7_delta_q_limited_p99": wall_stage7_dq_limited.get("p99", math.nan),
        "wall_stage7_delta_q_limited_max": wall_stage7_dq_limited.get("max", math.nan),
        "wall_stage7_denom_min": wall_stage7_denom.get("min", math.nan),
        "wall_stage7_denom_p50": wall_stage7_denom.get("p50", math.nan),
        "wall_stage7_limiter_reason_sum": wall_stage7_limiter.get("sum", math.nan),
        "wall_stage7_limiter_reason_max": wall_stage7_limiter.get("max", math.nan),
        "wall_stage7_normal_path_count": limiter_counts.get("normal_path_count", 0),
        "wall_stage7_normal_limiter_count": limiter_counts.get("normal_limiter_count", 0),
        "wall_stage7_active_path_count": limiter_counts.get("active_path_count", 0),
        "wall_stage7_active_limiter_count": limiter_counts.get("active_limiter_count", 0),
        "wall_stage7_actual_cos_p50": wall_stage7_actual_cos.get("p50", math.nan),
        "wall_stage7_target_cos_p50": wall_stage7_target_cos.get("p50", math.nan),
        "wall_stage7_write_candidate_min": wall_stage7_candidate.get("min", math.nan),
        "wall_stage7_write_candidate_max": wall_stage7_candidate.get("max", math.nan),
        "wall_stage7_write_minus_profile_min": wall_stage7_minus_profile.get("min", math.nan),
        "wall_stage7_write_minus_profile_max": wall_stage7_minus_profile.get("max", math.nan),
        "max_mach": rec["max_mach"],
        "nonfinite_total": rec["nonfinite_total"],
        "path_counts": json.dumps(rec["wall_bc_path_counts"], sort_keys=True),
    }


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def process_case(case_dir: Path, out_dir: Path, args: argparse.Namespace) -> dict[str, Any]:
    params_path = case_dir / "case_params.json"
    params: dict[str, Any] = {}
    if params_path.exists():
        params = json.loads(params_path.read_text(encoding="utf-8"))
    frames = sorted((case_dir / "output").glob(args.glob), key=step_of)
    if not frames:
        raise SystemExit(f"no VTI files matched {case_dir / 'output' / args.glob}")
    case_id = case_dir.name
    recs: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    baseline: dict[str, float] | None = None
    for frame in frames:
        rec, fields, dims, section, points, fit = summarize_frame(
            frame,
            case_id=case_id,
            case_params=params,
            threshold=args.threshold,
            min_wall_distance=args.min_wall_distance,
        )
        if baseline is None:
            baseline = {
                "phase_fluid_sum": float(rec["field_stats"]["PhaseField"]["fluid"].get("sum", math.nan)),
                "rho_fluid_sum": float(rec["field_stats"].get("Rho", {}).get("fluid", {}).get("sum", math.nan)),
            }
        recs.append(rec)
        rows.append(row_from_rec(rec, baseline))
        if args.plot:
            plot_frame(out_dir / "figures", rec, fields, dims, section, points, fit)
    write_csv(rows, out_dir / f"{case_id}_flat_gate_metrics.csv")
    payload = {
        "status": STATUS if all(r["nonfinite_total"] == 0 for r in recs) else "failed_negative_evidence",
        "case_id": case_id,
        "case_dir": str(case_dir),
        "case_params": params,
        "frame_count": len(recs),
        "last": recs[-1],
        "rows": rows,
        "claim_limit": "flat-wall runtime sanity/contact-response diagnostic only",
    }
    (out_dir / f"{case_id}_flat_gate_summary.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--case-root", type=Path)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--glob", default="*VTK_P00_*.vti")
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--min-wall-distance", type=float, default=2.0)
    parser.add_argument("--plot", action="store_true")
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    if args.case_root:
        case_dirs = [args.case_root]
    else:
        case_dirs = sorted(
            p
            for p in args.run_root.iterdir()
            if p.is_dir() and (p / "case_params.json").is_file() and (p / "output").is_dir()
        )
    payloads = [process_case(case_dir, args.out_dir, args) for case_dir in case_dirs if case_dir is not None]
    rows = [row for payload in payloads for row in payload["rows"]]
    write_csv(rows, args.out_dir / "flat_wall_cap_gate_metrics.csv")
    combined = {
        "status": STATUS if all(p["status"] == STATUS for p in payloads) else "failed_negative_evidence",
        "run_root": str(args.run_root),
        "case_count": len(payloads),
        "summaries": payloads,
        "claim_limit": "flat-wall runtime sanity/contact-response diagnostic only",
    }
    (args.out_dir / "flat_wall_cap_gate_summary.json").write_text(
        json.dumps(combined, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(combined, indent=2))


if __name__ == "__main__":
    main()
