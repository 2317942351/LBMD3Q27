#!/usr/bin/env python3
"""Postprocess TCLB wall geometric wetting diagnostic VTI output."""

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
CASE_RE = re.compile(r"^(flat|curved)_theta(\d{3})$")
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


def reshape_scalar(values: np.ndarray, dims: tuple[int, int, int]) -> np.ndarray:
    nx, ny, nz = dims
    return np.asarray(values, dtype=float).reshape((nz, ny, nx)).transpose(2, 1, 0)


def finite_stats(values: np.ndarray) -> dict[str, float | int]:
    values = np.asarray(values, dtype=float)
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return {
            "count": 0,
            "min": math.nan,
            "p01": math.nan,
            "p05": math.nan,
            "mean": math.nan,
            "p50": math.nan,
            "p95": math.nan,
            "p99": math.nan,
            "max": math.nan,
        }
    return {
        "count": int(finite.size),
        "min": float(np.min(finite)),
        "p01": float(np.percentile(finite, 1)),
        "p05": float(np.percentile(finite, 5)),
        "mean": float(np.mean(finite)),
        "p50": float(np.percentile(finite, 50)),
        "p95": float(np.percentile(finite, 95)),
        "p99": float(np.percentile(finite, 99)),
        "max": float(np.max(finite)),
    }


def frame_summary(path: Path, case_id: str, geometry: str, theta: int) -> tuple[dict[str, Any], dict[str, np.ndarray], tuple[int, int, int]]:
    dims, arrays = read_vti(path)
    flat: dict[str, np.ndarray] = {}
    for name in [
        "PhaseField",
        "BOUNDARY",
        "IsItBoundary",
        "SpecialBoundaryPoint",
        "WallPfF",
        "WallGradTangent",
        "WallTanCoeff",
        "WallPhasePred",
        "WallPhaseBoundedPred",
        "WallClampDelta",
        "WallPhaseProfilePred",
        "WallProfileDelta",
        "WallBCPath",
    ]:
        arr = scalar(arrays.get(name))
        if arr is not None:
            flat[name] = arr
    u_mag = vector_mag(arrays.get("U"))
    if u_mag is not None:
        flat["UMag"] = u_mag

    phi = flat["PhaseField"]
    boundary = flat.get("BOUNDARY")
    if boundary is None:
        boundary = flat.get("IsItBoundary", np.zeros_like(phi))
    wall_mask = np.isfinite(boundary) & (boundary != 0.0)
    fluid_mask = ~wall_mask
    phase_pred = flat.get("WallPhasePred", np.zeros_like(phi))
    phase_bounded_pred = flat.get("WallPhaseBoundedPred", phase_pred)
    clamp_delta = flat.get("WallClampDelta", np.zeros_like(phi))
    phase_profile_pred = flat.get("WallPhaseProfilePred", phase_pred)
    profile_delta = flat.get("WallProfileDelta", np.zeros_like(phi))
    grad_tangent = flat.get("WallGradTangent", np.zeros_like(phi))
    pf_f = flat.get("WallPfF", np.zeros_like(phi))
    tan_coeff = flat.get("WallTanCoeff", np.zeros_like(phi))
    path_code = np.rint(flat.get("WallBCPath", np.zeros_like(phi))).astype(int)
    special = flat.get("SpecialBoundaryPoint", np.zeros_like(phi))

    by_path: dict[str, dict[str, Any]] = {}
    for code in sorted(int(v) for v in np.unique(path_code[wall_mask]) if np.isfinite(v)):
        mask = wall_mask & (path_code == code)
        by_path[str(code)] = {
            "count": int(np.count_nonzero(mask)),
            "phase_field": finite_stats(phi[mask]),
            "wall_phase_pred": finite_stats(phase_pred[mask]),
            "wall_phase_bounded_pred": finite_stats(phase_bounded_pred[mask]),
            "wall_clamp_delta": finite_stats(clamp_delta[mask]),
            "wall_phase_profile_pred": finite_stats(phase_profile_pred[mask]),
            "wall_profile_delta": finite_stats(profile_delta[mask]),
            "wall_pf_f": finite_stats(pf_f[mask]),
            "wall_grad_tangent": finite_stats(grad_tangent[mask]),
            "wall_tan_coeff": finite_stats(tan_coeff[mask]),
            "phase_pred_gt_1_count": int(np.count_nonzero(mask & (phase_pred > 1.0 + 1e-8))),
            "phase_bounded_pred_gt_1_count": int(np.count_nonzero(mask & (phase_bounded_pred > 1.0 + 1e-8))),
            "clamp_delta_nonzero_count": int(np.count_nonzero(mask & (np.abs(clamp_delta) > 1e-12))),
            "phase_profile_pred_gt_1_count": int(np.count_nonzero(mask & (phase_profile_pred > 1.0 + 1e-8))),
            "profile_delta_nonzero_count": int(np.count_nonzero(mask & (np.abs(profile_delta) > 1e-12))),
            "phase_field_gt_1_count": int(np.count_nonzero(mask & (phi > 1.0 + 1e-8))),
        }

    summary = {
        "status": STATUS,
        "case_id": case_id,
        "geometry": geometry,
        "theta_deg": theta,
        "step": step_of(path),
        "file": str(path),
        "dims": list(dims),
        "cell_count": int(phi.size),
        "nonfinite_count": int(sum(np.count_nonzero(~np.isfinite(v)) for v in flat.values())),
        "wall_count": int(np.count_nonzero(wall_mask)),
        "fluid_count": int(np.count_nonzero(fluid_mask)),
        "phase_all": finite_stats(phi),
        "phase_wall": finite_stats(phi[wall_mask]),
        "phase_fluid": finite_stats(phi[fluid_mask]),
        "wall_phase_pred": finite_stats(phase_pred[wall_mask]),
        "wall_phase_bounded_pred": finite_stats(phase_bounded_pred[wall_mask]),
        "wall_clamp_delta": finite_stats(clamp_delta[wall_mask]),
        "wall_phase_profile_pred": finite_stats(phase_profile_pred[wall_mask]),
        "wall_profile_delta": finite_stats(profile_delta[wall_mask]),
        "wall_pf_f": finite_stats(pf_f[wall_mask]),
        "wall_grad_tangent": finite_stats(grad_tangent[wall_mask]),
        "wall_tan_coeff": finite_stats(tan_coeff[wall_mask]),
        "special_boundary_point": finite_stats(special[wall_mask]),
        "wall_phase_pred_gt_1_count": int(np.count_nonzero(wall_mask & (phase_pred > 1.0 + 1e-8))),
        "wall_phase_bounded_pred_gt_1_count": int(np.count_nonzero(wall_mask & (phase_bounded_pred > 1.0 + 1e-8))),
        "wall_phase_profile_pred_gt_1_count": int(np.count_nonzero(wall_mask & (phase_profile_pred > 1.0 + 1e-8))),
        "wall_phase_pred_lt_0_count": int(np.count_nonzero(wall_mask & (phase_pred < -1.0e-8))),
        "wall_clamp_delta_nonzero_count": int(np.count_nonzero(wall_mask & (np.abs(clamp_delta) > 1e-12))),
        "wall_profile_delta_nonzero_count": int(np.count_nonzero(wall_mask & (np.abs(profile_delta) > 1e-12))),
        "wall_phase_field_gt_1_count": int(np.count_nonzero(wall_mask & (phi > 1.0 + 1e-8))),
        "fluid_phase_field_gt_1_count": int(np.count_nonzero(fluid_mask & (phi > 1.0 + 1e-8))),
        "fluid_phase_sum": float(np.nansum(phi[fluid_mask])),
        "wall_phase_sum": float(np.nansum(phi[wall_mask])),
        "max_velocity": float(np.nanmax(flat["UMag"])) if "UMag" in flat else math.nan,
        "max_mach": float(np.nanmax(flat["UMag"]) / CS) if "UMag" in flat else math.nan,
        "by_wall_bc_path": by_path,
    }
    return summary, flat, dims


def write_frame_plots(
    flat: dict[str, np.ndarray],
    dims: tuple[int, int, int],
    summary: dict[str, Any],
    out_dir: Path,
) -> None:
    phi = reshape_scalar(flat["PhaseField"], dims)
    phase_pred = reshape_scalar(flat.get("WallPhasePred", np.zeros_like(flat["PhaseField"])), dims)
    phase_bounded_source = flat.get("WallPhaseBoundedPred", flat.get("WallPhasePred", np.zeros_like(flat["PhaseField"])))
    phase_bounded_pred = reshape_scalar(phase_bounded_source, dims)
    clamp_delta = reshape_scalar(flat.get("WallClampDelta", np.zeros_like(flat["PhaseField"])), dims)
    phase_profile_source = flat.get("WallPhaseProfilePred", phase_bounded_source)
    phase_profile_pred = reshape_scalar(phase_profile_source, dims)
    profile_delta = reshape_scalar(flat.get("WallProfileDelta", np.zeros_like(flat["PhaseField"])), dims)
    path_code = reshape_scalar(flat.get("WallBCPath", np.zeros_like(flat["PhaseField"])), dims)
    boundary = flat.get("BOUNDARY")
    if boundary is None:
        boundary = flat.get("IsItBoundary", np.zeros_like(flat["PhaseField"]))
    wall = reshape_scalar(boundary, dims) != 0.0
    x_mid = dims[0] // 2
    y_mid = dims[1] // 2

    out_dir.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 3, figsize=(13, 8))
    panels = [
        (phi[x_mid, :, :].T, "PhaseField x-mid", 0.0, 1.2),
        (phase_pred[x_mid, :, :].T, "WallPhasePred x-mid", 0.0, 1.5),
        (phase_profile_pred[x_mid, :, :].T, "WallPhaseProfilePred x-mid", 0.0, 1.2),
        (phi[:, y_mid, :].T, "PhaseField y-mid", 0.0, 1.2),
        ((clamp_delta + profile_delta)[:, y_mid, :].T, "WallDelta y-mid", -0.5, 0.5),
        (path_code[:, y_mid, :].T, "WallBCPath y-mid", 0.0, 5.0),
    ]
    for ax, (arr, title, vmin, vmax) in zip(axes.ravel(), panels):
        im = ax.imshow(arr, origin="lower", cmap="viridis", vmin=vmin, vmax=vmax, aspect="equal")
        ax.set_title(title)
        ax.set_xlabel("index")
        ax.set_ylabel("z")
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.suptitle(
        f"{summary['case_id']} step={summary['step']} "
        f"pred>1={summary['wall_phase_pred_gt_1_count']} "
        f"adjusted={summary['wall_clamp_delta_nonzero_count'] + summary['wall_profile_delta_nonzero_count']} "
        f"fluid_phi>1={summary['fluid_phase_field_gt_1_count']}"
    )
    fig.tight_layout()
    fig.savefig(out_dir / f"{summary['case_id']}_step{summary['step']:08d}_diagnostics.png", dpi=170)
    plt.close(fig)

    wall_mask = np.isfinite(boundary) & (boundary != 0.0)
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.6))
    data = [
        (flat.get("WallPfF", np.zeros_like(flat["PhaseField"]))[wall_mask], "WallPfF"),
        (flat.get("WallGradTangent", np.zeros_like(flat["PhaseField"]))[wall_mask], "WallGradTangent"),
        (flat.get("WallPhasePred", np.zeros_like(flat["PhaseField"]))[wall_mask], "WallPhasePred"),
        (flat.get("WallClampDelta", flat.get("WallProfileDelta", np.zeros_like(flat["PhaseField"])))[wall_mask], "WallDelta"),
    ]
    if len(data) != len(axes):
        plt.close(fig)
        fig, axes = plt.subplots(2, 2, figsize=(12, 7.2))
        axes = axes.ravel()
    for ax, (values, title) in zip(axes, data):
        values = values[np.isfinite(values)]
        if values.size:
            ax.hist(values, bins=80, color="#2f6f8f", alpha=0.85)
        ax.set_title(title)
        ax.grid(True, alpha=0.25)
    fig.suptitle(f"{summary['case_id']} wall diagnostic histograms")
    fig.tight_layout()
    fig.savefig(out_dir / f"{summary['case_id']}_step{summary['step']:08d}_histograms.png", dpi=170)
    plt.close(fig)


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    fields = [
        "case_id",
        "geometry",
        "theta_deg",
        "step",
        "wall_count",
        "fluid_count",
        "wall_phase_pred_gt_1_count",
        "wall_phase_field_gt_1_count",
        "fluid_phase_field_gt_1_count",
        "wall_phase_bounded_pred_gt_1_count",
        "wall_clamp_delta_nonzero_count",
        "wall_phase_profile_pred_gt_1_count",
        "wall_profile_delta_nonzero_count",
        "wall_pf_f_min",
        "wall_pf_f_max",
        "wall_grad_tangent_max",
        "wall_tan_coeff_mean",
        "wall_phase_pred_min",
        "wall_phase_pred_max",
        "wall_phase_bounded_pred_max",
        "wall_clamp_delta_min",
        "wall_clamp_delta_max",
        "wall_phase_profile_pred_max",
        "wall_profile_delta_min",
        "wall_profile_delta_max",
        "phase_wall_max",
        "phase_fluid_max",
        "max_mach",
        "nonfinite_count",
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "case_id": row["case_id"],
                    "geometry": row["geometry"],
                    "theta_deg": row["theta_deg"],
                    "step": row["step"],
                    "wall_count": row["wall_count"],
                    "fluid_count": row["fluid_count"],
                    "wall_phase_pred_gt_1_count": row["wall_phase_pred_gt_1_count"],
                    "wall_phase_field_gt_1_count": row["wall_phase_field_gt_1_count"],
                    "fluid_phase_field_gt_1_count": row["fluid_phase_field_gt_1_count"],
                    "wall_phase_bounded_pred_gt_1_count": row["wall_phase_bounded_pred_gt_1_count"],
                    "wall_clamp_delta_nonzero_count": row["wall_clamp_delta_nonzero_count"],
                    "wall_phase_profile_pred_gt_1_count": row["wall_phase_profile_pred_gt_1_count"],
                    "wall_profile_delta_nonzero_count": row["wall_profile_delta_nonzero_count"],
                    "wall_pf_f_min": row["wall_pf_f"]["min"],
                    "wall_pf_f_max": row["wall_pf_f"]["max"],
                    "wall_grad_tangent_max": row["wall_grad_tangent"]["max"],
                    "wall_tan_coeff_mean": row["wall_tan_coeff"]["mean"],
                    "wall_phase_pred_min": row["wall_phase_pred"]["min"],
                    "wall_phase_pred_max": row["wall_phase_pred"]["max"],
                    "wall_phase_bounded_pred_max": row["wall_phase_bounded_pred"]["max"],
                    "wall_clamp_delta_min": row["wall_clamp_delta"]["min"],
                    "wall_clamp_delta_max": row["wall_clamp_delta"]["max"],
                    "wall_phase_profile_pred_max": row["wall_phase_profile_pred"]["max"],
                    "wall_profile_delta_min": row["wall_profile_delta"]["min"],
                    "wall_profile_delta_max": row["wall_profile_delta"]["max"],
                    "phase_wall_max": row["phase_wall"]["max"],
                    "phase_fluid_max": row["phase_fluid"]["max"],
                    "max_mach": row["max_mach"],
                    "nonfinite_count": row["nonfinite_count"],
                }
            )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--plot", action="store_true")
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    summaries = []
    for case_dir in sorted(p for p in args.run_root.iterdir() if p.is_dir()):
        match = CASE_RE.match(case_dir.name)
        if not match:
            continue
        geometry = match.group(1)
        theta = int(match.group(2))
        frames = sorted((case_dir / "output").glob("*_VTK_P00_*.vti"), key=step_of)
        for frame in frames:
            summary, flat, dims = frame_summary(frame, case_dir.name, geometry, theta)
            summaries.append(summary)
            if args.plot:
                write_frame_plots(flat, dims, summary, args.out_dir / "figures")

    payload = {
        "status": STATUS,
        "run_root": str(args.run_root),
        "frame_count": len(summaries),
        "summaries": summaries,
    }
    (args.out_dir / "wall_geom_diag_summary.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    write_csv(summaries, args.out_dir / "wall_geom_diag_summary.csv")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
