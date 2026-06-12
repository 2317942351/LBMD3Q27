#!/usr/bin/env python3
"""Audit Stage8c local wall-angle/normal transfer on the z48 sphere case."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

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
    arr = np.asarray(values, dtype=float)
    if arr.ndim > 1:
        arr = arr[:, 0]
    return arr


def vector(values: np.ndarray | None) -> np.ndarray | None:
    if values is None:
        return None
    arr = np.asarray(values, dtype=float)
    if arr.ndim == 1:
        return arr.reshape((-1, 1))
    return arr[:, :3]


def vector_mag(values: np.ndarray | None) -> np.ndarray | None:
    arr = vector(values)
    if arr is None:
        return None
    return np.linalg.norm(arr, axis=1)


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
                "p01": float(np.percentile(x, 1)),
                "p05": float(np.percentile(x, 5)),
                "p50": float(np.percentile(x, 50)),
                "p95": float(np.percentile(x, 95)),
                "p99": float(np.percentile(x, 99)),
                "max": float(np.max(x)),
                "sum": float(np.sum(x)),
            }
        )
    return out


def parse_config_radangles(config_xml: Path) -> list[dict[str, str]]:
    if not config_xml.exists():
        return []
    root = ET.parse(config_xml).getroot()
    return [
        {
            "value": param.attrib.get("value", ""),
            "zone": param.attrib.get("zone", "DefaultZone"),
        }
        for param in root.findall(".//Param[@name='radAngle']")
    ]


def geometry_arrays(
    dims: tuple[int, int, int],
    physical_dims: tuple[int, int, int],
    solid_center: tuple[float, float, float],
) -> dict[str, np.ndarray]:
    nx, ny, nz = dims
    px, py, pz = physical_dims
    idx = np.arange(nx * ny * nz)
    x = idx % nx
    y = (idx // nx) % ny
    z = idx // (nx * ny)
    physical = (x < px) & (y < py) & (z < pz)
    cx, cy, cz = solid_center
    rx = x + 0.5 - cx
    ry = y + 0.5 - cy
    rz = z + 0.5 - cz
    rr = np.sqrt(rx * rx + ry * ry + rz * rz)
    radial = np.zeros((idx.size, 3), dtype=float)
    finite = rr > 1.0e-12
    radial[finite, 0] = rx[finite] / rr[finite]
    radial[finite, 1] = ry[finite] / rr[finite]
    radial[finite, 2] = rz[finite] / rr[finite]
    return {
        "x": x,
        "y": y,
        "z": z,
        "physical": physical,
        "rr": rr,
        "radial": radial,
    }


def masks_for(
    dims: tuple[int, int, int],
    arrays: dict[str, np.ndarray],
    args: argparse.Namespace,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    geom = geometry_arrays(
        dims,
        (args.physical_nx, args.physical_ny, args.physical_nz),
        (args.solid_center_x, args.solid_center_y, args.solid_center_z),
    )
    physical = geom["physical"]
    x = geom["x"]
    y = geom["y"]
    z = geom["z"]
    rr = geom["rr"]
    px, py, pz = args.physical_nx, args.physical_ny, args.physical_nz
    boundary = scalar(arrays.get("BOUNDARY"))
    if boundary is None:
        boundary = scalar(arrays.get("IsItBoundary"))
    wall = np.zeros_like(physical, dtype=bool) if boundary is None else np.isfinite(boundary) & (boundary != 0.0)
    fluid = physical & (~wall)
    outer = physical & (
        (x == 0)
        | (x == px - 1)
        | (y == 0)
        | (y == py - 1)
        | (z == 0)
        | (z == pz - 1)
    )
    sphere_shell = physical & (np.abs(rr - args.solid_radius) <= args.sphere_shell_width)
    near_sphere_fluid = fluid & (rr >= args.solid_radius) & (rr <= args.solid_radius + args.fluid_shell_width)
    lower_hemi = near_sphere_fluid & (z + 0.5 < args.solid_center_z)
    upper_hemi = near_sphere_fluid & (z + 0.5 >= args.solid_center_z)
    data_count = scalar(arrays.get("WallStage8FluidWallDataCount"))
    if data_count is None:
        data_mask = np.zeros_like(fluid, dtype=bool)
    else:
        data_mask = fluid & np.isfinite(data_count) & (data_count > 0.0)
    active = scalar(arrays.get("WallStage8ActiveWeight"))
    if active is None:
        active_mask = np.zeros_like(fluid, dtype=bool)
    else:
        active_mask = fluid & np.isfinite(active) & (active > 0.0)
    masks = {
        "all": np.ones_like(physical, dtype=bool),
        "physical": physical,
        "wall": wall,
        "fluid": fluid,
        "outer_geom": outer,
        "wall_outer_geom": wall & outer,
        "wall_sphere_shell": wall & sphere_shell,
        "wall_sphere_inside": wall & physical & (rr <= args.solid_radius),
        "fluid_near_sphere": near_sphere_fluid,
        "fluid_near_sphere_data": near_sphere_fluid & data_mask,
        "fluid_near_sphere_active": near_sphere_fluid & active_mask,
        "fluid_lower_hemi_data": lower_hemi & data_mask,
        "fluid_upper_hemi_data": upper_hemi & data_mask,
        "fluid_outer_data": fluid & outer & data_mask,
        "fluid_data": data_mask,
        "fluid_active": active_mask,
    }
    return masks, geom


def angle_match_counts(values: np.ndarray | None, mask: np.ndarray, expected: float, tol: float) -> dict[str, int]:
    if values is None:
        return {"count": int(np.count_nonzero(mask)), "finite": 0, "near_expected": 0}
    arr = np.asarray(values, dtype=float)
    finite = mask & np.isfinite(arr)
    near = finite & (np.abs(arr - expected) <= tol)
    return {
        "count": int(np.count_nonzero(mask)),
        "finite": int(np.count_nonzero(finite)),
        "near_expected": int(np.count_nonzero(near)),
    }


def dot_with_radial(vec_values: np.ndarray | None, radial: np.ndarray) -> np.ndarray | None:
    vec = vector(vec_values)
    if vec is None:
        return None
    mag = np.linalg.norm(vec, axis=1)
    out = np.full(vec.shape[0], np.nan, dtype=float)
    finite = np.isfinite(vec).all(axis=1) & (mag > 1.0e-12)
    out[finite] = np.sum((vec[finite] / mag[finite, None]) * radial[finite], axis=1)
    return out


def summarize_frame(path: Path, args: argparse.Namespace) -> dict[str, Any]:
    dims, arrays = read_vti(path)
    masks, geom = masks_for(dims, arrays, args)
    fields: dict[str, np.ndarray] = {}
    for name in [
        "PhaseField",
        "Rho",
        "WallBCPath",
        "SpecialBoundaryPoint",
        "WallStage8GradMode",
        "WallStage8ActiveWeight",
        "WallStage8NormalGradRaw",
        "WallStage8NormalGradTarget",
        "WallStage8ContactResidual",
        "WallStage8TangentGradMag",
        "WallStage8TargetCos",
        "WallStage8GradWriteDeltaMag",
        "WallStage8LimiterReason",
        "WallStage8LocalWallAngle",
        "WallStage8FluidWallAngle",
        "WallStage8FluidWallDataCount",
        "WallStage8GradCandidateUse",
        "WallStage8NormalAgreement",
        "WallStage8UsedGeomNormal",
    ]:
        arr = scalar(arrays.get(name))
        if arr is not None:
            fields[name] = arr
    for name in [
        "WallStage8LocalWallNormal",
        "WallStage8FluidWallNormal",
        "WallStage8GradCandidate",
        "U",
    ]:
        mag = vector_mag(arrays.get(name))
        if mag is not None:
            fields[f"{name}Mag"] = mag
    u_mag = fields.get("UMag", vector_mag(arrays.get("U")))
    if u_mag is not None:
        fields["UMag"] = u_mag

    raw_nonfinite_total = int(sum(np.count_nonzero(~np.isfinite(v)) for v in fields.values()))

    local_angle = fields.get("WallStage8LocalWallAngle")
    fluid_angle = fields.get("WallStage8FluidWallAngle")
    local_norm_dot = dot_with_radial(arrays.get("WallStage8LocalWallNormal"), geom["radial"])
    fluid_norm_dot = dot_with_radial(arrays.get("WallStage8FluidWallNormal"), geom["radial"])
    if local_norm_dot is not None:
        fields["WallStage8LocalWallNormalDotRadial"] = local_norm_dot
    if fluid_norm_dot is not None:
        fields["WallStage8FluidWallNormalDotRadial"] = fluid_norm_dot

    limiter = fields.get("WallStage8LimiterReason")
    active = fields.get("WallStage8ActiveWeight")
    data_count = fields.get("WallStage8FluidWallDataCount")
    finite_fluid = masks["fluid"] & np.isfinite(fields.get("PhaseField", np.zeros(next(iter(masks.values())).shape)))
    limiter_nonzero = np.zeros_like(finite_fluid)
    delta_limited = np.zeros_like(finite_fluid)
    missing_wall_data = np.zeros_like(finite_fluid)
    normal_low = np.zeros_like(finite_fluid)
    if limiter is not None:
        limiter_nonzero = finite_fluid & np.isfinite(limiter) & (limiter != 0.0)
        delta_limited = finite_fluid & np.isfinite(limiter) & (np.floor(limiter / 128.0).astype(int) % 2 == 1)
    if data_count is not None:
        missing_wall_data = finite_fluid & np.isfinite(data_count) & (data_count < 0.5)
    normal_agreement = fields.get("WallStage8NormalAgreement")
    if normal_agreement is not None:
        normal_low = finite_fluid & np.isfinite(normal_agreement) & (normal_agreement > 0.0) & (
            normal_agreement < args.normal_dot_min
        )

    derived_nonapplicable_total = 0
    if local_norm_dot is not None:
        derived_nonapplicable_total += int(np.count_nonzero(~np.isfinite(local_norm_dot)))
    if fluid_norm_dot is not None:
        derived_nonapplicable_total += int(np.count_nonzero(~np.isfinite(fluid_norm_dot)))

    rec: dict[str, Any] = {
        "status": STATUS,
        "step": step_of(path),
        "file": str(path),
        "dims": list(dims),
        "mask_counts": {name: int(np.count_nonzero(mask)) for name, mask in masks.items()},
        "nonfinite_total": raw_nonfinite_total,
        "derived_nonapplicable_nan_total": derived_nonapplicable_total,
        "angle_checks": {
            "wall_sphere_shell_local_angle": angle_match_counts(
                local_angle,
                masks["wall_sphere_shell"],
                math.radians(args.sphere_rad_angle_deg),
                args.angle_tolerance_rad,
            ),
            "wall_outer_local_angle": angle_match_counts(
                local_angle,
                masks["wall_outer_geom"],
                math.radians(args.outer_rad_angle_deg),
                args.angle_tolerance_rad,
            ),
            "fluid_near_sphere_data_angle": angle_match_counts(
                fluid_angle,
                masks["fluid_near_sphere_data"],
                math.radians(args.sphere_rad_angle_deg),
                args.angle_tolerance_rad,
            ),
            "fluid_outer_data_angle": angle_match_counts(
                fluid_angle,
                masks["fluid_outer_data"],
                math.radians(args.outer_rad_angle_deg),
                args.angle_tolerance_rad,
            ),
        },
        "limiter_counts": {
            "fluid_count": int(np.count_nonzero(finite_fluid)),
            "limiter_nonzero_count": int(np.count_nonzero(limiter_nonzero)),
            "delta_limiter_count": int(np.count_nonzero(delta_limited)),
            "missing_wall_data_count": int(np.count_nonzero(missing_wall_data)),
            "normal_low_agreement_count": int(np.count_nonzero(normal_low)),
            "active_count": int(np.count_nonzero(masks["fluid_active"])),
            "data_count": int(np.count_nonzero(masks["fluid_data"])),
        },
        "field_stats": {},
    }
    for name, values in fields.items():
        rec["field_stats"][name] = {
            mask_name: stats(values, mask)
            for mask_name, mask in masks.items()
            if mask_name
            in {
                "wall",
                "wall_outer_geom",
                "wall_sphere_shell",
                "fluid",
                "fluid_data",
                "fluid_active",
                "fluid_near_sphere_data",
                "fluid_near_sphere_active",
                "fluid_lower_hemi_data",
                "fluid_upper_hemi_data",
                "fluid_outer_data",
            }
        }
    if "UMag" in fields:
        rec["max_mach"] = float(np.nanmax(fields["UMag"][masks["fluid"]]) / CS)
    else:
        rec["max_mach"] = math.nan
    return rec


def flat_row(rec: dict[str, Any]) -> dict[str, Any]:
    def s(field: str, mask: str, key: str) -> Any:
        return rec.get("field_stats", {}).get(field, {}).get(mask, {}).get(key, math.nan)

    return {
        "step": rec["step"],
        "nonfinite_total": rec["nonfinite_total"],
        "derived_nonapplicable_nan_total": rec.get("derived_nonapplicable_nan_total", math.nan),
        "max_mach": rec["max_mach"],
        "wall_sphere_shell_count": rec["mask_counts"].get("wall_sphere_shell", 0),
        "wall_outer_count": rec["mask_counts"].get("wall_outer_geom", 0),
        "fluid_near_sphere_data_count": rec["mask_counts"].get("fluid_near_sphere_data", 0),
        "fluid_outer_data_count": rec["mask_counts"].get("fluid_outer_data", 0),
        "active_count": rec["limiter_counts"]["active_count"],
        "limiter_nonzero_count": rec["limiter_counts"]["limiter_nonzero_count"],
        "delta_limiter_count": rec["limiter_counts"]["delta_limiter_count"],
        "missing_wall_data_count": rec["limiter_counts"]["missing_wall_data_count"],
        "normal_low_agreement_count": rec["limiter_counts"]["normal_low_agreement_count"],
        "wall_sphere_local_angle_p50": s("WallStage8LocalWallAngle", "wall_sphere_shell", "p50"),
        "wall_outer_local_angle_p50": s("WallStage8LocalWallAngle", "wall_outer_geom", "p50"),
        "fluid_near_sphere_angle_p50": s("WallStage8FluidWallAngle", "fluid_near_sphere_data", "p50"),
        "fluid_outer_angle_p50": s("WallStage8FluidWallAngle", "fluid_outer_data", "p50"),
        "fluid_near_sphere_data_count_p50": s(
            "WallStage8FluidWallDataCount", "fluid_near_sphere_data", "p50"
        ),
        "fluid_near_sphere_normal_agreement_p05": s(
            "WallStage8NormalAgreement", "fluid_near_sphere_data", "p05"
        ),
        "fluid_near_sphere_used_geom_sum": s(
            "WallStage8UsedGeomNormal", "fluid_near_sphere_data", "sum"
        ),
        "wall_sphere_local_normal_dot_radial_p50": s(
            "WallStage8LocalWallNormalDotRadial", "wall_sphere_shell", "p50"
        ),
        "fluid_near_sphere_normal_dot_radial_p50": s(
            "WallStage8FluidWallNormalDotRadial", "fluid_near_sphere_data", "p50"
        ),
        "fluid_lower_hemi_angle_p50": s("WallStage8FluidWallAngle", "fluid_lower_hemi_data", "p50"),
        "fluid_upper_hemi_angle_p50": s("WallStage8FluidWallAngle", "fluid_upper_hemi_data", "p50"),
        "contact_residual_active_p50": s("WallStage8ContactResidual", "fluid_near_sphere_active", "p50"),
        "grad_delta_active_p99": s("WallStage8GradWriteDeltaMag", "fluid_near_sphere_active", "p99"),
        "grad_candidate_use_active_sum": s(
            "WallStage8GradCandidateUse", "fluid_near_sphere_active", "sum"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-root", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--physical-nx", type=int, default=80)
    parser.add_argument("--physical-ny", type=int, default=80)
    parser.add_argument("--physical-nz", type=int, default=180)
    parser.add_argument("--solid-center-x", type=float, default=40.0)
    parser.add_argument("--solid-center-y", type=float, default=40.0)
    parser.add_argument("--solid-center-z", type=float, default=48.0)
    parser.add_argument("--solid-radius", type=float, default=24.0)
    parser.add_argument("--sphere-shell-width", type=float, default=2.0)
    parser.add_argument("--fluid-shell-width", type=float, default=2.5)
    parser.add_argument("--sphere-rad-angle-deg", type=float, default=11.0)
    parser.add_argument("--outer-rad-angle-deg", type=float, default=90.0)
    parser.add_argument("--angle-tolerance-rad", type=float, default=1.0e-6)
    parser.add_argument("--normal-dot-min", type=float, default=0.25)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    frames = sorted((args.case_root / "output").glob("*_VTK_P00_*.vti"), key=step_of)
    if not frames:
        raise SystemExit(f"no VTI frames under {args.case_root / 'output'}")
    rows = [summarize_frame(frame, args) for frame in frames]
    payload = {
        "status": STATUS,
        "claim_limit": "runtime_sanity / exploratory_not_validation only",
        "case_root": str(args.case_root),
        "config_radangles": parse_config_radangles(
            args.case_root / "output" / "case_config_P00_00000000.xml"
        ),
        "expected": {
            "sphere_rad_angle_deg": args.sphere_rad_angle_deg,
            "sphere_rad_angle_rad": math.radians(args.sphere_rad_angle_deg),
            "outer_rad_angle_deg": args.outer_rad_angle_deg,
            "outer_rad_angle_rad": math.radians(args.outer_rad_angle_deg),
        },
        "frames": rows,
    }
    (args.out_dir / "stage8c_sphere_local_transfer_summary.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    flat = [flat_row(row) for row in rows]
    with (args.out_dir / "stage8c_sphere_local_transfer_summary.csv").open(
        "w", newline="", encoding="utf-8"
    ) as fh:
        writer = csv.DictWriter(fh, fieldnames=list(flat[0].keys()))
        writer.writeheader()
        writer.writerows(flat)
    print(json.dumps({"status": STATUS, "rows": flat, "out_dir": str(args.out_dir)}, indent=2))


if __name__ == "__main__":
    main()
