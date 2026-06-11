#!/usr/bin/env python3
"""Replay stage7 signed-wall-ghost formulas on saved TCLB VTI fields.

This is an offline diagnostic. It reads existing VTI wall fields and compares
the old raw geometric prediction, the current profile/unified prediction, and a
candidate signed logit wall ghost without running TCLB.
"""

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


STATUS = "runtime_sanity / exploratory_not_validation"
STEP_RE = re.compile(r"_VTK_P\d+_(\d{8})\.vti$")


def step_from_path(path: Path) -> int:
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


def scalar(arrays: dict[str, np.ndarray], name: str, n: int, default: float = 0.0) -> np.ndarray:
    values = arrays.get(name)
    if values is None:
        return np.full(n, default, dtype=float)
    out = np.asarray(values, dtype=float)
    if out.ndim > 1:
        out = out[:, 0]
    return out.reshape(-1)


def vector(arrays: dict[str, np.ndarray], name: str, n: int) -> np.ndarray:
    values = arrays.get(name)
    if values is None:
        return np.zeros((n, 3), dtype=float)
    out = np.asarray(values, dtype=float)
    if out.ndim == 1:
        out = out.reshape(-1, 1)
    if out.shape[1] < 3:
        padded = np.zeros((out.shape[0], 3), dtype=float)
        padded[:, : out.shape[1]] = out
        out = padded
    return out[:, :3]


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


def summarize_mask(name: str, values: np.ndarray, mask: np.ndarray) -> dict[str, Any]:
    selected = np.asarray(values, dtype=float)[mask]
    return {
        f"{name}_nonfinite_count": int(np.count_nonzero(~np.isfinite(selected))),
        f"{name}_gt_1_count": int(np.count_nonzero(selected > 1.0 + 1e-8)),
        f"{name}_lt_0_count": int(np.count_nonzero(selected < -1e-8)),
        f"{name}_stats": finite_stats(selected),
    }


def replay_file(
    path: Path,
    *,
    rad_angle_deg: float,
    phase_l: float,
    phase_h: float,
    min_gradient: float,
) -> dict[str, Any]:
    dims, arrays = read_vti(path)
    n_cells = math.prod(dims)
    phi = scalar(arrays, "PhaseField", n_cells)
    boundary = scalar(arrays, "BOUNDARY", n_cells, default=0.0)
    wall_bc_path = np.rint(scalar(arrays, "WallBCPath", n_cells, default=0.0)).astype(int)
    wall_mask = np.isfinite(boundary) & (boundary != 0.0)
    normal_mask = wall_mask & (wall_bc_path == 5)

    raw_pred = scalar(arrays, "WallPhasePred", n_cells)
    profile_pred = scalar(
        arrays,
        "WallPhaseUnifiedProfilePred",
        n_cells,
        default=np.nan,
    )
    if not np.isfinite(profile_pred).any():
        profile_pred = scalar(arrays, "WallPhaseProfilePred", n_cells)
    pf_f = scalar(arrays, "WallPfF", n_cells)
    h = scalar(arrays, "WallH", n_cells)
    grad1 = vector(arrays, "WallGrad1", n_cells)
    tangent = vector(arrays, "WallGradTangentVec", n_cells)
    wall_normal = vector(arrays, "WallGeomNormal", n_cells)

    wall_normal_mag = np.linalg.norm(wall_normal, axis=1)
    unit_wall = np.zeros_like(wall_normal)
    valid_normal = wall_normal_mag > 1e-12
    unit_wall[valid_normal] = wall_normal[valid_normal] / wall_normal_mag[valid_normal, None]

    grad_mag = np.linalg.norm(grad1, axis=1)
    tangent_mag = np.linalg.norm(tangent, axis=1)
    signed_normal_grad = np.einsum("ij,ij->i", grad1, unit_wall)

    rad_angle = math.radians(rad_angle_deg)
    tan_coeff = math.tan(math.pi / 2.0 - rad_angle)
    target_normal_grad = -tan_coeff * tangent_mag
    target_cos = -math.cos(rad_angle)

    actual_cos = np.zeros(n_cells, dtype=float)
    valid_grad = grad_mag > min_gradient
    actual_cos[valid_grad] = signed_normal_grad[valid_grad] / grad_mag[valid_grad]
    contact_residual = actual_cos - target_cos

    phase_range = phase_h - phase_l
    eps = 1e-12
    c = (pf_f - phase_l) / phase_range
    c = np.clip(c, eps, 1.0 - eps)
    signed_delta_phi = -2.0 * h * target_normal_grad
    signed_delta_q = signed_delta_phi / (phase_range * c * (1.0 - c))
    q = np.log(c / (1.0 - c)) + signed_delta_q
    q_clipped = np.clip(q, -60.0, 60.0)
    signed_pred = phase_l + phase_range / (1.0 + np.exp(-q_clipped))
    q_clip_mask = np.isfinite(q) & ((q > 60.0) | (q < -60.0))

    rows: dict[str, Any] = {
        "status": STATUS,
        "step": step_from_path(path),
        "file": str(path),
        "dims": list(dims),
        "cell_count": int(n_cells),
        "wall_count": int(np.count_nonzero(wall_mask)),
        "normal_path_count": int(np.count_nonzero(normal_mask)),
        "rad_angle_deg": rad_angle_deg,
        "tan_coeff": tan_coeff,
        "target_cos": target_cos,
        "q_clip_count_normal": int(np.count_nonzero(normal_mask & q_clip_mask)),
        "nonfinite_total_normal": int(
            sum(
                np.count_nonzero(~np.isfinite(arr[normal_mask]))
                for arr in [
                    raw_pred,
                    profile_pred,
                    signed_pred,
                    signed_delta_q,
                    signed_normal_grad,
                    tangent_mag,
                    contact_residual,
                ]
            )
        ),
        "signed_minus_profile": finite_stats((signed_pred - profile_pred)[normal_mask]),
        "signed_minus_raw": finite_stats((signed_pred - raw_pred)[normal_mask]),
        "actual_minus_signed": finite_stats((phi - signed_pred)[normal_mask]),
        "contact_residual": finite_stats(contact_residual[normal_mask & valid_grad]),
        "signed_normal_grad": finite_stats(signed_normal_grad[normal_mask]),
        "target_normal_grad": finite_stats(target_normal_grad[normal_mask]),
        "tangent_grad_mag": finite_stats(tangent_mag[normal_mask]),
        "signed_delta_q": finite_stats(signed_delta_q[normal_mask]),
    }
    for prefix, values in [
        ("raw_pred", raw_pred),
        ("profile_pred", profile_pred),
        ("signed_pred", signed_pred),
        ("actual_phase", phi),
    ]:
        rows.update(summarize_mask(prefix, values, normal_mask))
    return rows


def flatten_row(row: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in row.items():
        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                out[f"{key}_{sub_key}"] = sub_value
        elif isinstance(value, list):
            out[key] = "x".join(str(v) for v in value)
        else:
            out[key] = value
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-root", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--rad-angle-deg", type=float, required=True)
    parser.add_argument("--phase-l", type=float, default=0.0)
    parser.add_argument("--phase-h", type=float, default=1.0)
    parser.add_argument("--min-gradient", type=float, default=1e-8)
    parser.add_argument("--steps", default="")
    args = parser.parse_args()

    output = args.case_root / "output"
    steps = {int(item) for item in args.steps.split(",") if item.strip()} if args.steps else None
    files = sorted(output.glob("*.vti"), key=step_from_path)
    if steps is not None:
        files = [path for path in files if step_from_path(path) in steps]
    if not files:
        raise SystemExit(f"no VTI files found in {output}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    rows = [
        replay_file(
            path,
            rad_angle_deg=args.rad_angle_deg,
            phase_l=args.phase_l,
            phase_h=args.phase_h,
            min_gradient=args.min_gradient,
        )
        for path in files
    ]
    flat_rows = [flatten_row(row) for row in rows]
    fieldnames = sorted({key for row in flat_rows for key in row})
    metrics_csv = args.out_dir / "stage7_signed_wall_ghost_replay_metrics.csv"
    with metrics_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(flat_rows)

    summary = {
        "status": STATUS,
        "case_root": str(args.case_root),
        "rad_angle_deg": args.rad_angle_deg,
        "steps": [row["step"] for row in rows],
        "pass_gate1": all(
            row["nonfinite_total_normal"] == 0
            and row["signed_pred_nonfinite_count"] == 0
            and row["normal_path_count"] > 0
            for row in rows
        ),
        "rows": rows,
    }
    summary_json = args.out_dir / "stage7_signed_wall_ghost_replay_summary.json"
    summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
