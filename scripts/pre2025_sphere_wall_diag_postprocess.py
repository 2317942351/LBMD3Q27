#!/usr/bin/env python3
"""Postprocess wall diagnostic fields for PRE sphere cases."""

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


def finite_stats(values: np.ndarray) -> dict[str, float | int]:
    values = np.asarray(values, dtype=float)
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return {
            "count": 0,
            "min": math.nan,
            "mean": math.nan,
            "p95": math.nan,
            "p99": math.nan,
            "max": math.nan,
        }
    return {
        "count": int(finite.size),
        "min": float(np.min(finite)),
        "mean": float(np.mean(finite)),
        "p95": float(np.percentile(finite, 95)),
        "p99": float(np.percentile(finite, 99)),
        "max": float(np.max(finite)),
    }


def frame_summary(path: Path) -> tuple[dict[str, Any], dict[str, np.ndarray], tuple[int, int, int]]:
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
    boundary = flat.get("BOUNDARY", flat.get("IsItBoundary", np.zeros_like(phi)))
    wall_mask = np.isfinite(boundary) & (boundary != 0.0)
    fluid_mask = ~wall_mask
    phase_pred = flat.get("WallPhasePred", np.zeros_like(phi))
    phase_profile = flat.get("WallPhaseProfilePred", phase_pred)
    phase_bounded = flat.get("WallPhaseBoundedPred", phase_pred)
    profile_delta = flat.get("WallProfileDelta", np.zeros_like(phi))
    clamp_delta = flat.get("WallClampDelta", np.zeros_like(phi))
    path_code = np.rint(flat.get("WallBCPath", np.zeros_like(phi))).astype(int)

    by_path: dict[str, dict[str, Any]] = {}
    for code in sorted(int(v) for v in np.unique(path_code[wall_mask]) if np.isfinite(v)):
        mask = wall_mask & (path_code == code)
        by_path[str(code)] = {
            "count": int(np.count_nonzero(mask)),
            "phase_field": finite_stats(phi[mask]),
            "wall_phase_pred": finite_stats(phase_pred[mask]),
            "wall_phase_profile_pred": finite_stats(phase_profile[mask]),
            "phase_field_gt_1_count": int(np.count_nonzero(mask & (phi > 1.0 + 1e-8))),
            "wall_phase_pred_gt_1_count": int(np.count_nonzero(mask & (phase_pred > 1.0 + 1e-8))),
            "wall_phase_profile_pred_gt_1_count": int(
                np.count_nonzero(mask & (phase_profile > 1.0 + 1e-8))
            ),
        }

    summary = {
        "status": STATUS,
        "step": step_of(path),
        "file": str(path),
        "dims": list(dims),
        "cell_count": int(phi.size),
        "wall_count": int(np.count_nonzero(wall_mask)),
        "fluid_count": int(np.count_nonzero(fluid_mask)),
        "nonfinite_count": int(sum(np.count_nonzero(~np.isfinite(v)) for v in flat.values())),
        "phase_all": finite_stats(phi),
        "phase_wall": finite_stats(phi[wall_mask]),
        "phase_fluid": finite_stats(phi[fluid_mask]),
        "wall_phase_pred": finite_stats(phase_pred[wall_mask]),
        "wall_phase_profile_pred": finite_stats(phase_profile[wall_mask]),
        "wall_phase_bounded_pred": finite_stats(phase_bounded[wall_mask]),
        "wall_profile_delta": finite_stats(profile_delta[wall_mask]),
        "wall_clamp_delta": finite_stats(clamp_delta[wall_mask]),
        "wall_phase_pred_gt_1_count": int(np.count_nonzero(wall_mask & (phase_pred > 1.0 + 1e-8))),
        "wall_phase_profile_pred_gt_1_count": int(
            np.count_nonzero(wall_mask & (phase_profile > 1.0 + 1e-8))
        ),
        "wall_phase_field_gt_1_count": int(np.count_nonzero(wall_mask & (phi > 1.0 + 1e-8))),
        "fluid_phase_field_gt_1_count": int(np.count_nonzero(fluid_mask & (phi > 1.0 + 1e-8))),
        "wall_profile_delta_nonzero_count": int(np.count_nonzero(wall_mask & (np.abs(profile_delta) > 1e-12))),
        "wall_clamp_delta_nonzero_count": int(np.count_nonzero(wall_mask & (np.abs(clamp_delta) > 1e-12))),
        "max_velocity": float(np.nanmax(flat["UMag"])) if "UMag" in flat else math.nan,
        "max_mach": float(np.nanmax(flat["UMag"]) / CS) if "UMag" in flat else math.nan,
        "by_wall_bc_path": by_path,
    }
    return summary, flat, dims


def write_plots(flat: dict[str, np.ndarray], dims: tuple[int, int, int], summary: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    phi = reshape(flat["PhaseField"], dims)
    pred = reshape(flat.get("WallPhasePred", np.zeros_like(flat["PhaseField"])), dims)
    profile_source = flat.get("WallPhaseProfilePred", flat.get("WallPhasePred", np.zeros_like(flat["PhaseField"])))
    profile = reshape(profile_source, dims)
    delta = reshape(flat.get("WallProfileDelta", flat.get("WallClampDelta", np.zeros_like(flat["PhaseField"]))), dims)
    boundary = flat.get("BOUNDARY", flat.get("IsItBoundary", np.zeros_like(flat["PhaseField"])))
    wall = reshape(boundary, dims) != 0.0
    x_mid = min(40, dims[0] - 1)
    y_mid = min(40, dims[1] - 1)
    panels = [
        (np.ma.array(phi[x_mid, :, :].T, mask=wall[x_mid, :, :].T), "PhaseField x=40", 0.0, 1.2),
        (pred[x_mid, :, :].T, "WallPhasePred x=40", 0.0, 1.6),
        (profile[x_mid, :, :].T, "WallPhaseProfilePred x=40", 0.0, 1.2),
        (np.ma.array(phi[:, y_mid, :].T, mask=wall[:, y_mid, :].T), "PhaseField y=40", 0.0, 1.2),
        (delta[:, y_mid, :].T, "WallDelta y=40", -0.5, 0.8),
        (reshape(flat.get("WallBCPath", np.zeros_like(flat["PhaseField"])), dims)[:, y_mid, :].T, "WallBCPath y=40", 0.0, 5.0),
    ]
    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    for ax, (arr, title, vmin, vmax) in zip(axes.ravel(), panels):
        im = ax.imshow(arr, origin="lower", cmap="viridis", vmin=vmin, vmax=vmax, aspect="equal")
        ax.set_title(title)
        ax.set_xlabel("index")
        ax.set_ylabel("z")
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.suptitle(
        f"PRE sphere wall diagnostics step={summary['step']} "
        f"raw>1={summary['wall_phase_pred_gt_1_count']} "
        f"actual>1={summary['wall_phase_field_gt_1_count']} "
        f"profile>1={summary['wall_phase_profile_pred_gt_1_count']}"
    )
    fig.tight_layout()
    fig.savefig(out_dir / f"pre2025_sphere_wall_diag_step{summary['step']:08d}.png", dpi=170)
    plt.close(fig)


def flatten_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "step": row["step"],
        "wall_count": row["wall_count"],
        "fluid_count": row["fluid_count"],
        "wall_phase_pred_gt_1_count": row["wall_phase_pred_gt_1_count"],
        "wall_phase_profile_pred_gt_1_count": row["wall_phase_profile_pred_gt_1_count"],
        "wall_phase_field_gt_1_count": row["wall_phase_field_gt_1_count"],
        "fluid_phase_field_gt_1_count": row["fluid_phase_field_gt_1_count"],
        "wall_profile_delta_nonzero_count": row["wall_profile_delta_nonzero_count"],
        "wall_clamp_delta_nonzero_count": row["wall_clamp_delta_nonzero_count"],
        "wall_phase_pred_max": row["wall_phase_pred"]["max"],
        "wall_phase_profile_pred_max": row["wall_phase_profile_pred"]["max"],
        "phase_wall_max": row["phase_wall"]["max"],
        "phase_fluid_max": row["phase_fluid"]["max"],
        "max_mach": row["max_mach"],
        "nonfinite_count": row["nonfinite_count"],
    }


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    fields = list(flatten_row(rows[0]).keys())
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(flatten_row(row))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-root", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--plot", action="store_true")
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    frames = sorted((args.case_root / "output").glob("*_VTK_P00_*.vti"), key=step_of)
    if not frames:
        raise SystemExit(f"no VTI frames under {args.case_root / 'output'}")
    rows = []
    for frame in frames:
        summary, flat, dims = frame_summary(frame)
        rows.append(summary)
        if args.plot:
            write_plots(flat, dims, summary, args.out_dir / "figures")
    payload = {
        "status": STATUS,
        "case_root": str(args.case_root),
        "frame_count": len(rows),
        "summaries": rows,
    }
    (args.out_dir / "pre2025_sphere_wall_diag_summary.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    write_csv(rows, args.out_dir / "pre2025_sphere_wall_diag_summary.csv")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
